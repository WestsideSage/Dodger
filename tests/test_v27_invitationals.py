"""V27 The Calendar — Phase 4: Ruleset Invitationals (Cloth Classic / No-Sting Open).

Per docs/specs/2026-06-17-v27-the-calendar-spec.md (Phase 4). An invitational
runs an auto-simmed knockout under a NON-foam ruleset
(``OfficialEngineAdapter(RulesetSelection.OFFICIAL_CLOTH/_NO_STING)``); invite by
fame (prestige) + standing; champion gets a purse + a one-season prospect-
showcase warmth in the V26 recruiting-credibility channel. Match-ids encode the
round so the engine clock is right (the trap). Pyramid-gated; legacy saves stay
byte-identical (no invitationals, no warmth, no purse).

Architecture guardrails (non-negotiable):
- Non-foam engine only (cloth / no-sting via ``OfficialEngineAdapter``); the
  foam league + Domestic Cup are untouched.
- ``decide_cloth_game_by_active_count`` is NEVER called on a foam match (the
  engine guards it on ``profile.material == CLOTH``).
- New seed namespace ``v27_invitational``; idempotent purses + warmth.
- V26 warmth coexists with a media credibility bonus in the same offseason
  (summed, not clobbered) and both reset next offseason.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_EVENTS
from dodgeball_sim.economy import set_treasury_k, treasury_k
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_prestige,
    load_clubs,
    load_cup_bracket,
    save_club_prestige,
    set_state,
)
from dodgeball_sim.rulesets import RulesetSelection
from dodgeball_sim.rng import derive_seed

_SEED = 20260617


def _pyramid_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _legacy_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _seed_prestige(conn, club_ids, score):
    """Give a set of clubs a prestige score (the fame gate input)."""
    for cid in club_ids:
        save_club_prestige(conn, cid, score)
    conn.commit()


def _some_invitees(conn, n=8):
    """The first n club ids (deterministic invitee set for the pure runner tests)."""
    clubs = list(load_clubs(conn).values())
    return [c.club_id for c in clubs[:n]]


# ---------------------------------------------------------------------------
# Task 4.1 — invitationals.run_invitational (cloth / no-sting knockout)
# ---------------------------------------------------------------------------


class TestRunInvitational:
    def test_cloth_knockout_resolves_to_a_valid_champion(self):
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)

        result = run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_CLOTH, invitees, _SEED
        )

        assert result is not None
        assert result.champion_club_id in invitees
        assert result.ruleset == "official_cloth"
        # The bracket has at least the final + a semifinal round.
        rounds = {row.round for row in result.bracket}
        assert "Final" in rounds
        assert result.bracket  # played matches recorded

    def test_no_sting_knockout_resolves_to_a_valid_champion(self):
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)

        result = run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_NO_STING, invitees, _SEED
        )

        assert result is not None
        assert result.champion_club_id in invitees
        assert result.ruleset == "official_no_sting"

    def test_match_ids_encode_the_round_so_the_engine_clock_is_right(self):
        """The official engine derives the match clock from match_id substrings:
        ``semifinal`` -> 30 min, ``final`` -> 40 min, else 24 min. Knockout
        match-ids must encode the round label so each round gets the right
        clock. Captures the match_ids actually passed to the engine."""
        from dodgeball_sim import invitationals

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)

        captured = []
        real_simulate = invitationals.simulate_match

        def spy(scheduled, *args, **kwargs):
            captured.append(str(scheduled.match_id))
            return real_simulate(scheduled, *args, **kwargs)

        invitationals.simulate_match = spy
        try:
            invitationals.run_invitational(
                conn, season_id, RulesetSelection.OFFICIAL_CLOTH, invitees, _SEED
            )
        finally:
            invitationals.simulate_match = real_simulate

        # An 8-club bracket: round 1 = quarterfinal (24 min, no label match),
        # round 2 = semifinal (30 min), round 3 = final (40 min). At least one
        # semifinal and exactly one final match-id must encode the label so the
        # engine clock resolves correctly.
        assert any("semifinal" in mid for mid in captured), captured
        assert any("final" in mid and "semifinal" not in mid for mid in captured), captured

    def test_foam_league_and_cup_untouched(self):
        """Running an invitational never creates a cup bracket, never adds
        league match_records, and never touches the foam cup state."""
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)
        records_before = conn.execute(
            "SELECT COUNT(*) AS n FROM match_records"
        ).fetchone()["n"]

        run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_CLOTH, invitees, _SEED
        )

        # No cup bracket is created by the invitational.
        assert load_cup_bracket(conn, season_id) is None
        # No league match_records are persisted (the invitational is pure sim;
        # only the event result is recorded).
        records_after = conn.execute(
            "SELECT COUNT(*) AS n FROM match_records"
        ).fetchone()["n"]
        assert records_after == records_before

    def test_decide_cloth_game_never_called_on_a_foam_match(self):
        """``decide_cloth_game_by_active_count`` raises on a non-cloth game and
        the engine guards it on ``profile.material == CLOTH``. A foam match must
        never invoke it. Spy on the engine-bound name and run a foam match."""
        import dodgeball_sim.official_engine as oe
        from dodgeball_sim.franchise import simulate_match
        from dodgeball_sim.scheduler import ScheduledMatch
        from dodgeball_sim.persistence import load_club_roster

        conn, season_id = _pyramid_career()
        clubs = list(load_clubs(conn).values())
        home, away = clubs[0], clubs[1]
        calls = {"n": 0}
        real = oe.decide_cloth_game_by_active_count

        def spy(game):
            calls["n"] += 1
            if game.profile.material.value != "cloth":
                raise AssertionError(
                    "decide_cloth_game_by_active_count called on a non-cloth match"
                )
            return real(game)

        oe.decide_cloth_game_by_active_count = spy
        try:
            scheduled = ScheduledMatch(
                match_id=f"{season_id}_foam_probe_{home.club_id}_vs_{away.club_id}",
                season_id=season_id,
                week=200,
                home_club_id=home.club_id,
                away_club_id=away.club_id,
            )
            simulate_match(
                scheduled=scheduled,
                home_club=home,
                away_club=away,
                home_roster=load_club_roster(conn, home.club_id),
                away_roster=load_club_roster(conn, away.club_id),
                root_seed=_SEED,
                ruleset_selection="official_foam",
            )
        finally:
            oe.decide_cloth_game_by_active_count = real

        assert calls["n"] == 0, "foam match invoked decide_cloth_game_by_active_count"

    def test_decide_cloth_game_never_called_on_a_no_sting_invitational(self):
        """A no-sting invitational runs the full knockout without ever invoking
        the cloth-only game-decision helper."""
        import dodgeball_sim.official_engine as oe
        from dodgeball_sim import invitationals

        conn, season_id = _pyramid_career()
        invitees = _some_invitees(conn, 8)
        calls = {"n": 0}
        real = oe.decide_cloth_game_by_active_count

        def spy(game):
            calls["n"] += 1
            raise AssertionError(
                "decide_cloth_game_by_active_count called during a no-sting invitational"
            )

        oe.decide_cloth_game_by_active_count = spy
        try:
            invitationals.run_invitational(
                conn, season_id, RulesetSelection.OFFICIAL_NO_STING, invitees, _SEED
            )
        finally:
            oe.decide_cloth_game_by_active_count = real

        assert calls["n"] == 0

    def test_determinism_same_seed_same_champion(self):
        from dodgeball_sim.invitationals import run_invitational

        conn1, sid1 = _pyramid_career()
        r1 = run_invitational(
            conn1, sid1, RulesetSelection.OFFICIAL_CLOTH, _some_invitees(conn1, 8), _SEED
        )
        conn2, sid2 = _pyramid_career()
        r2 = run_invitational(
            conn2, sid2, RulesetSelection.OFFICIAL_CLOTH, _some_invitees(conn2, 8), _SEED
        )
        assert r1.champion_club_id == r2.champion_club_id
        assert [b.__dict__ for b in r1.bracket] == [b.__dict__ for b in r2.bracket]

    def test_too_few_invitees_is_a_no_op(self):
        """Fewer than 2 invitees cannot form a bracket — returns None, no event."""
        from dodgeball_sim.invitationals import run_invitational

        conn, season_id = _pyramid_career()
        result = run_invitational(
            conn, season_id, RulesetSelection.OFFICIAL_CLOTH, [], _SEED
        )
        assert result is None
