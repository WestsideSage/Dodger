"""Dynasty progression health — multi-season truth and texture guards.

Pins the 2026-06-09 dynasty/progression pass:

1. Development reps truth: a peak-age full-time starter develops at the full
   headroom rate when appearance counts are provided. The legacy
   ``minutes_played / 1000`` gate never matched either engine's measured
   scale (official starter season ~64-206 "minutes", rec ~10-27), so all
   post-practice development was starved and ceilings were unreachable.
2. Rivalry book is fed by the WEB path: rebuilt from persisted match records
   (previously only the legacy sandbox CLI ever wrote rivalry_records, so the
   Dynasty Office / history / broadcast rivalry surfaces stayed empty forever).
3. Team records (most_titles, longest_unbeaten_run) ratify in the web
   offseason from club trophies + match records.
4. Official draws keep a None winner in the aftermath match card instead of a
   survivor-derived winner that contradicts the result and degrades the panel.
5. Recruitment skip is blocked while the user club cannot field a legal six
   (the user club is exempt from every AI roster-repair path, so repeated
   skips previously bled the roster to 4 with no recovery).
6. The multi-season loop itself is deterministic end to end (dynasty probe).
"""
from __future__ import annotations

import dataclasses
import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.development import apply_season_development
from dodgeball_sim.engine import MatchResult
from dodgeball_sim.game_loop import rebuild_rivalry_records, season_sort_key
from dodgeball_sim.lineup import STARTERS_COUNT
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.offseason_beats import ratify_records
from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS
from dodgeball_sim.offseason_service import OffseasonError, recruit_offseason_payload
from dodgeball_sim.persistence import (
    create_schema,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_rivalry_records,
    save_career_state_cursor,
    save_club,
    save_club_trophy,
    save_match_result,
)
from dodgeball_sim.rng import DeterministicRNG
from dodgeball_sim.stats import PlayerMatchStats
from dodgeball_sim.use_cases import _build_aftermath, auto_pilot_weeks
from dodgeball_sim.postgame_validator import validate_postgame_payload

ROOT_SEED = 20260609


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _flat_player(pid: str, *, ovr: int, potential: int, age: int) -> Player:
    ratings = PlayerRatings(
        accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr,
        tactical_iq=ovr, catch_courage=ovr, throw_selection_iq=ovr,
        conditioning_curve=ovr,
    )
    return Player(
        id=pid,
        name=pid.title(),
        ratings=ratings,
        archetype=PlayerArchetype.THROWER,
        traits=PlayerTraits(potential=potential, growth_curve=50, consistency=50, pressure=50),
        age=age,
        club_id="aurora",
        newcomer=False,
    )


# ---------------------------------------------------------------------------
# 1. Development reps truth
# ---------------------------------------------------------------------------

class TestRepsTruth:
    def _grow(self, *, age: int, minutes: int, matches_played=None, club_matches=None) -> int:
        player = _flat_player("p_reps", ovr=66, potential=88, age=age)
        developed = apply_season_development(
            player,
            PlayerMatchStats(minutes_played=minutes),
            facilities=(),
            rng=DeterministicRNG(11),
            matches_played=matches_played,
            club_matches=club_matches,
        )
        return developed.overall_skill() - player.overall_skill()

    def test_peak_age_starter_develops_with_appearances(self):
        """Cause -> effect: the same 26-year-old starter who is reps-starved on
        the legacy minutes scale develops for real once appearances gate reps.
        steady curve peak window is 25-28, so age 26 is inside the peak."""
        legacy = self._grow(age=26, minutes=120)          # measured official-scale season
        appearance = self._grow(age=26, minutes=120, matches_played=7, club_matches=7)
        assert appearance >= 2, f"full-time peak starter grew only +{appearance}"
        assert appearance > legacy, (
            f"appearance-gated growth (+{appearance}) should beat the starved "
            f"legacy-minutes growth (+{legacy})"
        )

    def test_adult_bench_player_stays_gated(self):
        bench = self._grow(age=26, minutes=0, matches_played=0, club_matches=7)
        assert bench <= 1, f"0-appearance adult grew +{bench}"

    def test_legacy_path_unchanged_without_appearance_counts(self):
        """Callers that do not pass appearance counts keep byte-identical
        behaviour (same RNG stream, same formula)."""
        player = _flat_player("p_legacy", ovr=60, potential=85, age=20)
        a = apply_season_development(
            player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(7)
        )
        b = apply_season_development(
            player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(7)
        )
        assert a.ratings == b.ratings
        assert a.overall_skill() > player.overall_skill()  # youth practice path

    def test_growth_still_capped_at_potential(self):
        player = _flat_player("p_cap", ovr=66, potential=68, age=26)
        developed = apply_season_development(
            player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(11),
            matches_played=7, club_matches=7,
        )
        assert developed.overall_skill() <= 68


# ---------------------------------------------------------------------------
# 2. Rivalry book fed from match records (web path)
# ---------------------------------------------------------------------------

def _save_minimal_match(
    conn,
    *,
    match_id: str,
    season_id: str,
    week: int,
    home: str,
    away: str,
    winner: str | None,
    home_survivors: int = 3,
    away_survivors: int = 1,
) -> None:
    save_match_result(
        conn,
        match_id=match_id,
        season_id=season_id,
        week=week,
        home_club_id=home,
        away_club_id=away,
        winner_club_id=winner,
        home_survivors=home_survivors,
        away_survivors=away_survivors,
        home_roster_hash="h",
        away_roster_hash="a",
        config_version="phase1.v1",
        ruleset_version="default.v1",
        seed=1,
        event_log_hash="e",
        final_state_hash="f",
    )


class TestRivalryWebPath:
    def test_rebuild_derives_rivalries_from_match_records(self):
        conn = _make_conn()
        _save_minimal_match(conn, match_id="s1_w1_a_b", season_id="season_1", week=1,
                            home="alpha", away="beta", winner="alpha")
        _save_minimal_match(conn, match_id="s1_w2_b_a", season_id="season_1", week=2,
                            home="beta", away="alpha", winner=None,
                            home_survivors=2, away_survivors=2)
        _save_minimal_match(conn, match_id="season_1_p_final", season_id="season_1", week=7,
                            home="alpha", away="beta", winner="beta")
        rebuild_rivalry_records(conn)

        items = load_rivalry_records(conn)
        assert len(items) == 1
        rivalry = items[0]["rivalry"]
        assert rivalry["total_meetings"] == 3
        assert rivalry["a_wins"] == 1 and rivalry["b_wins"] == 1 and rivalry["draws"] == 1
        assert rivalry["playoff_meetings"] == 1
        assert rivalry["championship_meetings"] == 1
        assert rivalry["last_winner_club_id"] == "beta"

    def test_rebuild_is_idempotent(self):
        conn = _make_conn()
        _save_minimal_match(conn, match_id="s1_w1", season_id="season_1", week=1,
                            home="alpha", away="beta", winner="alpha")
        rebuild_rivalry_records(conn)
        first = load_rivalry_records(conn)
        rebuild_rivalry_records(conn)
        second = load_rivalry_records(conn)
        assert first == second
        assert first[0]["rivalry"]["total_meetings"] == 1

    def test_multi_digit_seasons_order_numerically(self):
        assert season_sort_key("season_2") < season_sort_key("season_10")
        conn = _make_conn()
        _save_minimal_match(conn, match_id="m10", season_id="season_10", week=1,
                            home="alpha", away="beta", winner="alpha")
        _save_minimal_match(conn, match_id="m2", season_id="season_2", week=1,
                            home="alpha", away="beta", winner="beta")
        rebuild_rivalry_records(conn)
        rivalry = load_rivalry_records(conn)[0]["rivalry"]
        assert rivalry["last_meeting_season"] == "season_10"

    def test_web_career_populates_rivalries_after_one_week(self):
        """End-to-end: a real simulated week feeds the rivalry book."""
        conn = _make_conn()
        initialize_curated_manager_career(
            conn, "aurora", ROOT_SEED, ruleset_selection="official_foam"
        )
        auto_pilot_weeks(conn, max_weeks=1)
        items = load_rivalry_records(conn)
        assert items, "one simulated week must produce rivalry records"
        assert all(item["rivalry"]["total_meetings"] >= 1 for item in items)


# ---------------------------------------------------------------------------
# 3. Team records ratify in the web offseason
# ---------------------------------------------------------------------------

class TestTeamRecordsRatify:
    def test_titles_and_unbeaten_run_ratify_from_saved_truth(self):
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED)
        save_club_trophy(conn, "aurora", "championship", "season_1")
        # A 3-match unbeaten run (2 wins + 1 draw) for granite.
        _save_minimal_match(conn, match_id="r1", season_id="season_1", week=1,
                            home="granite", away="harbor", winner="granite")
        _save_minimal_match(conn, match_id="r2", season_id="season_1", week=2,
                            home="granite", away="lunar", winner=None,
                            home_survivors=2, away_survivors=2)
        _save_minimal_match(conn, match_id="r3", season_id="season_1", week=3,
                            home="solstice", away="granite", winner="granite")
        conn.commit()

        payload = ratify_records(conn, "season_1")
        by_type = {r.record_type: r for r in payload.new_records}
        assert "most_titles" in by_type, by_type.keys()
        assert by_type["most_titles"].holder_id == "aurora"
        assert by_type["most_titles"].new_value == 1.0
        assert by_type["most_titles"].holder_club_id == "aurora"
        assert "longest_unbeaten_run" in by_type
        assert by_type["longest_unbeaten_run"].holder_id == "granite"
        assert by_type["longest_unbeaten_run"].new_value == 3.0

    def test_team_record_only_breaks_when_exceeded(self):
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED)
        save_club_trophy(conn, "aurora", "championship", "season_1")
        conn.commit()
        first = ratify_records(conn, "season_1")
        assert any(r.record_type == "most_titles" for r in first.new_records)

        # Season 2: no new trophy -> the 1-title record holds, no re-break.
        second = ratify_records(conn, "season_2")
        assert not any(r.record_type == "most_titles" for r in second.new_records)

        # Season 3: second title -> record broken at 2.
        save_club_trophy(conn, "aurora", "championship", "season_3")
        conn.commit()
        third = ratify_records(conn, "season_3")
        titles = [r for r in third.new_records if r.record_type == "most_titles"]
        assert titles and titles[0].new_value == 2.0


# ---------------------------------------------------------------------------
# 4. Official draws keep a None winner in the aftermath card
# ---------------------------------------------------------------------------

def _synthetic_record(*, config_version: str, winner: str | None):
    from dodgeball_sim.franchise import MatchRecord

    box_score = {
        "teams": {
            "aurora": {"totals": {"living": 2}, "players": {}},
            "granite": {"totals": {"living": 0}, "players": {}},
        }
    }
    result = MatchResult(
        events=(),
        winner_team_id=winner,
        box_score=box_score,
        final_tick=100,
        seed=1,
        config_version=config_version,
        official_metadata=None,
    )
    return MatchRecord(
        match_id="m_draw",
        season_id="season_1",
        week=1,
        home_club_id="aurora",
        away_club_id="granite",
        home_roster_hash="h",
        away_roster_hash="a",
        config_version=config_version,
        ruleset_version="default.v1",
        meta_patch_id=None,
        seed=1,
        event_log_hash="e",
        final_state_hash="f",
        engine_match_id=None,
        result=result,
    )


class TestOfficialDrawAftermath:
    def test_official_draw_keeps_none_winner_and_validates(self):
        conn = _make_conn()
        record = _synthetic_record(config_version="official:official_foam", winner=None)
        aftermath = _build_aftermath(
            conn, {"result": "Draw"}, record, "season_1"
        )
        assert aftermath["match_card"]["winner_club_id"] is None
        # The exact contradiction that degraded the panel before the fix:
        validate_postgame_payload(aftermath, record.result)

    def test_legacy_none_winner_also_keeps_result_truth(self):
        """The survivor-derived fallback is gone for BOTH models: whenever it
        fired it contradicted result.winner_team_id and the validator degraded
        the panel (legacy records are already winner-patched upstream in
        franchise.simulate_match, so a None here is a genuine draw)."""
        conn = _make_conn()
        record = _synthetic_record(config_version="phase1.v1", winner=None)
        aftermath = _build_aftermath(
            conn, {"result": "Draw"}, record, "season_1"
        )
        assert aftermath["match_card"]["winner_club_id"] is None
        validate_postgame_payload(aftermath, record.result)


# ---------------------------------------------------------------------------
# 5. Recruitment skip is blocked below the fielded-six floor
# ---------------------------------------------------------------------------

class TestRosterFloorSkipGuard:
    def _career_at_recruitment(self):
        from dodgeball_sim.offseason_service import (
            advance_offseason_beat_payload,
            get_offseason_beat_payload,
        )
        from dodgeball_sim.career_state import CareerState

        conn = _make_conn()
        initialize_curated_manager_career(
            conn, "aurora", ROOT_SEED, ruleset_selection="official_foam"
        )
        auto_pilot_weeks(conn)
        get_offseason_beat_payload(conn)  # finalize + initialize offseason
        # Advance through the ceremony until the recruitment beat is pending.
        for _ in range(len(OFFSEASON_CEREMONY_BEATS)):
            cursor = load_career_state_cursor(conn)
            if cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING:
                break
            advance_offseason_beat_payload(conn)
        cursor = load_career_state_cursor(conn)
        assert cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING
        return conn

    def test_skip_blocked_when_roster_below_six(self):
        conn = self._career_at_recruitment()
        clubs = load_clubs(conn)
        roster = load_all_rosters(conn)["aurora"]
        save_club(conn, clubs["aurora"], roster[:4])  # bleed the roster below 6
        conn.commit()

        with pytest.raises(OffseasonError) as exc:
            recruit_offseason_payload(conn, "skip")
        assert exc.value.status_code == 409
        assert "field a legal six" in exc.value.detail

    def test_skip_allowed_at_or_above_six(self):
        conn = self._career_at_recruitment()
        assert len(load_all_rosters(conn)["aurora"]) >= STARTERS_COUNT
        payload = recruit_offseason_payload(conn, "skip")
        assert payload["signed_player"] is None

    def test_signing_up_to_six_then_skip_succeeds(self, monkeypatch):
        conn = self._career_at_recruitment()
        clubs = load_clubs(conn)
        roster = load_all_rosters(conn)["aurora"]
        save_club(conn, clubs["aurora"], roster[:4])
        conn.commit()
        # This test asserts the roster-floor FLOW, not contested-round odds:
        # remove rival bidders so every auto-pick lands by construction,
        # independent of balance constants (snipe odds are pinned in
        # test_contested_offseason.py).
        from dodgeball_sim import recruitment

        monkeypatch.setattr(
            recruitment, "_eligible_ai_offer_clubs", lambda *args, **kwargs: set()
        )

        recruit_offseason_payload(conn, None)  # sign best available (5)
        with pytest.raises(OffseasonError):
            recruit_offseason_payload(conn, "skip")  # still below six
        recruit_offseason_payload(conn, None)  # sign best available (6)
        payload = recruit_offseason_payload(conn, "skip")
        assert payload["signed_player"] is None


# ---------------------------------------------------------------------------
# 6. Multi-season loop determinism (dynasty probe)
# ---------------------------------------------------------------------------

class TestDynastyLoopDeterminism:
    def test_two_runs_reproduce_identical_dynasty(self):
        from tools.dynasty_health_probe import run_dynasty_career

        a = run_dynasty_career(
            root_seed=ROOT_SEED, seasons=2, signings_per_offseason=1
        )
        b = run_dynasty_career(
            root_seed=ROOT_SEED, seasons=2, signings_per_offseason=1
        )
        assert [s.champion_club_id for s in a.seasons] == [
            s.champion_club_id for s in b.seasons
        ]
        assert [s.user_six_ovr for s in a.seasons] == [s.user_six_ovr for s in b.seasons]
        assert [s.signings for s in a.seasons] == [s.signings for s in b.seasons]
        # V16: league-wide AI Signing Day moves and user snipes are part of the
        # same deterministic stream — same seed, same market.
        assert [s.ai_signings for s in a.seasons] == [s.ai_signings for s in b.seasons]
        assert [s.user_snipes for s in a.seasons] == [s.user_snipes for s in b.seasons]
        # Structural floors the dynasty loop must hold.
        for snap in a.seasons:
            assert snap.champion_club_id, "every season must crown a champion"
            assert all(size >= 6 for size in snap.ai_roster_sizes), (
                f"AI club fell below the playable floor: {snap.ai_roster_sizes}"
            )


# ---------------------------------------------------------------------------
# 7. Dynasty-health CI gate (V16 Task 6) — owner-tunable bounds
# ---------------------------------------------------------------------------

# Owner-tunable gate bounds (V16 acceptance + dynasty report scale-downs).
GATE_SEED_COUNT = 4
GATE_SEASONS = 6
# Evidence-based: the PRE-V16 solved-recruiting config measured 41.7% title
# share on this exact sweep (10/24); post-V16 measured 12.5% (3/24). The
# bound sits between them with ~3x headroom over the healthy value, so a
# contested-round revert FAILS this gate instead of slipping under a loose
# ceiling.
GATE_USER_TITLE_SHARE_MAX = 0.35
GATE_AI_ROSTER_FLOOR = 6
GATE_MIN_DISTINCT_CHAMPIONS_PER_RUN = 2  # scale of the report's >=3 per 10
GATE_MIN_AI_SIGNINGS_PER_OFFSEASON = 1   # while the prospect pool is non-empty
# Across 24 probed offseasons the uncourted auto-pick is sniped ~5 times; a
# revert to uncontested signing produces exactly zero snipes, so a floor of 1
# is a direct tripwire on contested-ness itself.
GATE_MIN_TOTAL_USER_SNIPES = 1


class TestDynastyHealthGate:
    """Pins the dynasty probe's small config so the static-league and
    solved-recruiting failures cannot silently return."""

    @pytest.fixture(scope="class")
    def sweep(self):
        from tools.dynasty_health_probe import default_seed_set, run_dynasty_sweep

        return run_dynasty_sweep(
            seeds=default_seed_set(count=GATE_SEED_COUNT),
            seasons=GATE_SEASONS,
            signings_per_offseason=3,
        )

    def test_engaged_user_title_share_is_bounded(self, sweep):
        titles = sum(1 for run in sweep.runs for s in run.seasons if s.champion_is_user)
        total = sum(len(run.seasons) for run in sweep.runs)
        assert titles / total <= GATE_USER_TITLE_SHARE_MAX, (
            f"user title share {titles}/{total} exceeds the snowball bound"
        )

    def test_ai_rosters_never_fall_below_the_floor(self, sweep):
        for run in sweep.runs:
            for snap in run.seasons:
                assert all(size >= GATE_AI_ROSTER_FLOOR for size in snap.ai_roster_sizes), (
                    f"seed {run.root_seed} S{snap.season_number}: {snap.ai_roster_sizes}"
                )

    def test_each_run_crowns_multiple_champions(self, sweep):
        for run in sweep.runs:
            champions = {s.champion_club_id for s in run.seasons}
            assert len(champions) >= GATE_MIN_DISTINCT_CHAMPIONS_PER_RUN, (
                f"seed {run.root_seed}: only {champions} won across "
                f"{len(run.seasons)} seasons — the league looks solved"
            )

    def test_contested_rounds_actually_contest(self, sweep):
        # The user's picks must be genuinely losable: across the sweep at
        # least one auto-pick gets sniped by a rival offer. An uncontested
        # revert (sign_chosen_rookie signing directly) produces zero snipes
        # and fails here even though title share alone might stay bounded.
        total_snipes = sum(
            snap.user_snipes for run in sweep.runs for snap in run.seasons
        )
        assert total_snipes >= GATE_MIN_TOTAL_USER_SNIPES, (
            "no user pick was ever sniped across the sweep — Signing Day "
            "does not look contested"
        )

    def test_league_moves_every_offseason(self, sweep):
        # The class pool (25) comfortably exceeds user picks (<=3) + AI cap
        # (1 per club), so the pool is never empty and every offseason must
        # produce AI churn.
        for run in sweep.runs:
            for snap in run.seasons:
                assert len(snap.ai_signings) >= GATE_MIN_AI_SIGNINGS_PER_OFFSEASON, (
                    f"seed {run.root_seed} S{snap.season_number}: the league "
                    f"did not move (AI signings: {snap.ai_signings})"
                )
