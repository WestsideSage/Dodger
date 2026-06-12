"""V23 Phases 3+4 gates — the pyramid postseason and the season-to-season world.

Pins, per docs/specs/2026-06-12-v23-the-world-spec.md:

1. One auto-piloted founding season produces the FULL world postseason:
   every division's title bracket, both promotion playoffs, and WORLDS —
   21 postseason fixtures, all resolved, ledger complete.
2. Worlds runs from Season 1 (the history gate).
3. Movement is real and applied: season 2's memberships move champions and
   promotion-playoff winners up, the bottom two of D1/D2 down, divisions
   stay at seven, the Circuit stays closed.
4. The finances ledger pays the user's division rank at the tier multiplier
   and discloses it (D3 = the 1.0× anchor — the V22 squeeze must keep
   holding on the founding path).
5. Season awards on a pyramid save honor the user's division only.
6. The multi-season pyramid loop is deterministic per seed.

The fixture runs ONE real auto-piloted season + offseason on the shipping
loop (official foam), shared module-wide to keep the suite's cost honest.
"""
from __future__ import annotations

import sqlite3

import pytest

from dodgeball_sim.career_setup import (
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.economy import load_season_finances
from dodgeball_sim.offseason_service import (
    OffseasonError,
    advance_offseason_beat_payload,
    begin_next_season_payload,
    get_offseason_beat_payload,
    recruit_offseason_payload,
)
from dodgeball_sim.persistence import (
    get_state,
    load_awards,
    load_division_map,
    load_season,
    load_season_outcome,
)
from dodgeball_sim.pyramid_postseason import (
    load_postseason_ledger,
    load_worlds_history,
    next_season_assignment,
)
from dodgeball_sim.use_cases import auto_pilot_weeks

ROOT_SEED = 20260612


def _run_founding_season(seed: int = ROOT_SEED) -> tuple[sqlite3.Connection, str]:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    club = build_expansion_club(
        name="Gate Test Club",
        primary_color="#101010",
        secondary_color="#FAFAFA",
        venue_name="Gate Gym",
        home_region="Gateview",
        tagline="gate",
    )
    roster = generate_expansion_roster(club.club_id, seed)
    initialize_curated_manager_career(
        conn,
        club.club_id,
        seed,
        custom_club=club,
        custom_roster=roster,
        ruleset_selection="official_foam",
        world="pyramid",
    )
    result = auto_pilot_weeks(conn, max_weeks=None)
    assert result["stop_reason"] == "season_complete", result
    return conn, club.club_id


def _walk_offseason_and_begin_next(conn: sqlite3.Connection) -> None:
    payload = get_offseason_beat_payload(conn)
    for _ in range(24):
        state = payload.get("state")
        if state == "next_season_ready":
            break
        if state == "season_complete_recruitment_pending":
            payload = recruit_offseason_payload(conn, prospect_id="skip")
            continue
        try:
            payload = advance_offseason_beat_payload(conn)
        except OffseasonError:
            break
    begin_next_season_payload(conn)


@pytest.fixture(scope="module")
def founded_world():
    conn, user_club_id = _run_founding_season()
    season_1_ledger = load_postseason_ledger(conn, "season_1")
    outcome = load_season_outcome(conn, "season_1")
    season_1_map = load_division_map(conn, "season_1")
    season_1 = load_season(conn, "season_1")
    assignment_preview = next_season_assignment(conn, "season_1")
    _walk_offseason_and_begin_next(conn)
    # Awards + finances are written by the offseason (finalize_season /
    # apply_season_finances), so they are only readable after the walk.
    awards = load_awards(conn, "season_1")
    finances = load_season_finances(conn)
    return {
        "conn": conn,
        "user_club_id": user_club_id,
        "ledger": season_1_ledger,
        "outcome": outcome,
        "awards": awards,
        "season_1_map": season_1_map,
        "season_1": season_1,
        "assignment_preview": assignment_preview,
        "finances": finances,
    }


class TestWorldPostseason:
    def test_full_postseason_runs_and_resolves(self, founded_world):
        conn = founded_world["conn"]
        season = founded_world["season_1"]
        postseason = [m for m in season.scheduled_matches if "_p_" in m.match_id]
        # 4 title brackets (user legacy ids + 3 div_) ×3, 2 promo ×3, worlds ×3.
        assert len(postseason) == 21
        completed = {
            row["match_id"]: row["winner_club_id"]
            for row in conn.execute(
                "SELECT match_id, winner_club_id FROM match_records WHERE season_id = 'season_1'"
            )
        }
        for match in postseason:
            assert match.match_id in completed, f"unplayed: {match.match_id}"
            assert completed[match.match_id] is not None, f"unresolved: {match.match_id}"

    def test_ledger_is_complete_and_consistent(self, founded_world):
        ledger = founded_world["ledger"]
        season_1_map = founded_world["season_1_map"]
        assert ledger and ledger.get("complete")
        assert set(ledger["champions"]) == {"premier", "challenger", "district", "circuit"}
        # Champions actually belong to the division they were crowned in.
        for division_id, club_id in ledger["champions"].items():
            assert season_1_map[club_id].division_id == division_id
        # The user's division champion matches the celebrated season outcome.
        outcome = founded_world["outcome"]
        assert outcome is not None
        assert ledger["champions"]["district"] == outcome.champion_club_id
        # Promotion playoff winners exist and are not the champions.
        for division_id in ("challenger", "district"):
            promo = ledger["promotion_playoff"][division_id]
            assert promo["winner"]
            assert promo["winner"] != ledger["champions"][division_id]
            assert promo["winner"] in promo["participants"]
        # Two clubs go down from each of D1/D2.
        assert len(ledger["relegated"]["premier"]) == 2
        assert len(ledger["relegated"]["challenger"]) == 2

    def test_worlds_runs_from_season_one(self, founded_world):
        conn = founded_world["conn"]
        history = load_worlds_history(conn)
        assert any(entry["season_id"] == "season_1" for entry in history)
        entry = next(e for e in history if e["season_id"] == "season_1")
        season_1_map = founded_world["season_1_map"]
        # Worlds is contested by the Premier and Circuit tops only.
        assert season_1_map[entry["champion_club_id"]].division_id in ("premier", "circuit")
        assert entry["champion_name"]
        assert entry["runner_up_club_id"]


class TestMovementApplied:
    def test_season_2_memberships_apply_promotion_and_relegation(self, founded_world):
        conn = founded_world["conn"]
        ledger = founded_world["ledger"]
        season_2_id = get_state(conn, "active_season_id")
        assert season_2_id == "season_2"
        new_map = load_division_map(conn, season_2_id)
        old_map = founded_world["season_1_map"]

        sizes: dict[str, int] = {}
        for membership in new_map.values():
            sizes[membership.division_id] = sizes.get(membership.division_id, 0) + 1
        assert sizes == {"premier": 7, "challenger": 7, "district": 7, "circuit": 7}

        # Up: D3 champion + promo winner now sit in the Challenger League.
        for club_id in (ledger["champions"]["district"], ledger["promotion_playoff"]["district"]["winner"]):
            assert new_map[club_id].division_id == "challenger", club_id
        for club_id in (ledger["champions"]["challenger"], ledger["promotion_playoff"]["challenger"]["winner"]):
            assert new_map[club_id].division_id == "premier", club_id
        # Down: the bottom two fall a tier.
        for club_id in ledger["relegated"]["premier"]:
            assert new_map[club_id].division_id == "challenger", club_id
        for club_id in ledger["relegated"]["challenger"]:
            assert new_map[club_id].division_id == "district", club_id
        # The Circuit is closed: identical membership.
        assert {c for c, m in new_map.items() if m.division_id == "circuit"} == {
            c for c, m in old_map.items() if m.division_id == "circuit"
        }

    def test_season_2_schedule_is_intra_division(self, founded_world):
        conn = founded_world["conn"]
        season_2 = load_season(conn, "season_2")
        new_map = load_division_map(conn, "season_2")
        regular = [m for m in season_2.scheduled_matches if "_p_" not in m.match_id]
        assert len(regular) == 4 * 21
        for match in regular:
            assert (
                new_map[match.home_club_id].division_id
                == new_map[match.away_club_id].division_id
            ), match.match_id


class TestEconomyTier:
    def test_finances_pay_division_rank_at_the_district_anchor(self, founded_world):
        finances = founded_world["finances"]
        assert finances is not None
        assert finances["division_name"] == "District League"
        assert finances["tier"] == 3
        assert finances["tier_multiplier"] == 1.0
        assert 1 <= finances["rank"] <= 7
        assert finances["total_clubs"] == 7
        assert "payouts are the pyramid's base scale" in finances["rules"]


class TestAwardScope:
    def test_season_awards_stay_in_the_users_division(self, founded_world):
        awards = founded_world["awards"]
        season_1_map = founded_world["season_1_map"]
        assert awards, "season 1 produced no awards"
        for award in awards:
            assert season_1_map[award.club_id].division_id == "district", (
                award.award_type,
                award.club_id,
            )


class TestDeterminism:
    def test_same_seed_reproduces_the_postseason_ledger(self, founded_world):
        conn_b, _ = _run_founding_season()
        ledger_b = load_postseason_ledger(conn_b, "season_1")
        assert ledger_b == founded_world["ledger"]
