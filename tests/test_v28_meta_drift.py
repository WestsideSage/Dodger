"""V28 The Weather — Phase 2: emergent meta (ecosystem tactic drift).

Per docs/specs/2026-06-17-v28-the-weather-spec.md (Phase 2): AI programs drift
toward the prior season's winning CoachPolicy dimensions (computed from real
match data), with a deterministic contrarian fraction that drifts AWAY (the
anti-solvedness mechanism). The overlay is consumed by
``ai_tactics.get_ai_tactics`` as a learned bias after the intent override
(precedence: archetype base → intent override → drift bias). ``meta.py``/
MetaPatch stays retired. New seed namespace ``v28_meta_drift`` only. Pyramid-
gated; legacy byte-identical. The user club is never drifted.
"""
from __future__ import annotations

import json
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_WEATHER
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_clubs,
    load_division_memberships,
    save_division_memberships,
    save_match_result,
    set_state,
)
from dodgeball_sim.league import DivisionMembership
from dodgeball_sim.rng import derive_seed

_SEED = 20260618


def _fresh_pyramid_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _save_official_match(
    conn,
    *,
    match_id,
    season_id,
    week,
    home_club_id,
    away_club_id,
    winner_club_id,
    home_policy,
    away_policy,
):
    score_json = json.dumps(
        {"team_policies": {home_club_id: home_policy, away_club_id: away_policy}}
    )
    save_match_result(
        conn,
        match_id=match_id,
        season_id=season_id,
        week=week,
        home_club_id=home_club_id,
        away_club_id=away_club_id,
        winner_club_id=winner_club_id,
        home_survivors=3,
        away_survivors=2,
        home_roster_hash="h",
        away_roster_hash="a",
        config_version="v1",
        ruleset_version="v1",
        seed=1,
        event_log_hash="e",
        final_state_hash="f",
        scoring_model="official",
        home_game_points=6,
        away_game_points=3,
        official_score_json=score_json,
    )


def _drift_fixture(contrarian_fraction=0.0):
    """A pyramid save with 4 AI clubs in premier, known match results.

    go_for_catches wins 3/4 matches; play_safe wins 1/4. The user club is
    'aurora' (set as player_club_id). With contrarian_fraction=0.0, all AI
    clubs drift toward go_for_catches. The user club is never drifted.
    """
    conn = _fresh_pyramid_conn()
    season_id = "season_1"
    set_state(conn, "root_seed", str(_SEED))
    ms = load_division_memberships(conn, season_id)
    premier = [m.club_id for m in ms if m.division_id == "premier"][:4]
    # Ensure we have 4 premier clubs; if not, use any 4 non-user clubs.
    if len(premier) < 4:
        all_clubs = [c for c in load_clubs(conn) if c != get_state(conn, "player_club_id")]
        premier = all_clubs[:4]
    user_club = get_state(conn, "player_club_id")
    # Remove user club from premier if it's there; we want AI clubs only.
    premier = [c for c in premier if c != user_club][:4]
    assert len(premier) >= 3, "need at least 3 AI clubs"

    go_for = {
        "approach": "aggressive", "target_focus": "their_stars",
        "catch_posture": "go_for_catches", "rush_commit": "all_in",
        "rush_target": "center",
    }
    play_safe = {
        "approach": "patient", "target_focus": "spread",
        "catch_posture": "play_safe", "rush_commit": "hold_back",
        "rush_target": "nearest",
    }
    c0, c1, c2 = premier[0], premier[1], premier[2]
    # go_for wins 3, play_safe wins 1.
    _save_official_match(conn, match_id="s1_w1_01", season_id=season_id, week=1,
                         home_club_id=c0, away_club_id=c1, winner_club_id=c0,
                         home_policy=go_for, away_policy=play_safe)
    _save_official_match(conn, match_id="s1_w2_02", season_id=season_id, week=2,
                         home_club_id=c1, away_club_id=c0, winner_club_id=c0,
                         home_policy=play_safe, away_policy=go_for)
    _save_official_match(conn, match_id="s1_w3_03", season_id=season_id, week=3,
                         home_club_id=c2, away_club_id=c1, winner_club_id=c2,
                         home_policy=go_for, away_policy=play_safe)
    _save_official_match(conn, match_id="s1_w4_04", season_id=season_id, week=4,
                         home_club_id=c1, away_club_id=c2, winner_club_id=c1,
                         home_policy=play_safe, away_policy=go_for)
    conn.commit()
    return conn, season_id, premier, user_club


# ---------------------------------------------------------------------------
# Task 2.1 — winning_tactics + drift overlay
# ---------------------------------------------------------------------------


class TestWinningTactics:
    def test_returns_winning_value_per_dimension(self):
        from dodgeball_sim.meta_drift import winning_tactics

        conn, season_id, _clubs, _user = _drift_fixture()
        winners = winning_tactics(conn, season_id)
        # go_for_catches won 3/4 matches; play_safe won 1/4.
        assert winners["catch_posture"] == "go_for_catches"
        # aggressive approach won 3/4 (go_for uses aggressive).
        assert winners["approach"] == "aggressive"

    def test_excludes_playoff_matches(self):
        from dodgeball_sim.meta_drift import winning_tactics

        conn, season_id, _clubs, _user = _drift_fixture()
        # Add a playoff match where play_safe wins — must be excluded.
        c0, c1 = _clubs[0], _clubs[1]
        play_safe = {
            "approach": "patient", "target_focus": "spread",
            "catch_posture": "play_safe", "rush_commit": "hold_back",
            "rush_target": "nearest",
        }
        go_for = {
            "approach": "aggressive", "target_focus": "their_stars",
            "catch_posture": "go_for_catches", "rush_commit": "all_in",
            "rush_target": "center",
        }
        _save_official_match(conn, match_id=f"{season_id}_p_1", season_id=season_id,
                             week=99, home_club_id=c1, away_club_id=c0,
                             winner_club_id=c1, home_policy=play_safe, away_policy=go_for)
        conn.commit()
        winners = winning_tactics(conn, season_id)
        # Still go_for_catches (the playoff's play_safe win is excluded).
        assert winners["catch_posture"] == "go_for_catches"

    def test_legacy_save_returns_empty(self):
        from dodgeball_sim.meta_drift import winning_tactics

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        initialize_curated_manager_career(conn, "aurora", _SEED, ruleset_selection="official_foam")
        conn.commit()
        winners = winning_tactics(conn, get_state(conn, "active_season_id"))
        assert winners == {}


class TestApplyMetaDrift:
    def test_nudges_ai_club_overlay_toward_winners(self):
        from dodgeball_sim.meta_drift import apply_meta_drift, tactic_drift_for

        conn, season_id, clubs, user_club = _drift_fixture()
        apply_meta_drift(conn, season_id, _SEED)
        # Each AI club should now have a drift overlay with a bias toward
        # go_for_catches (the winning catch_posture).
        for club_id in clubs:
            overlay = tactic_drift_for(conn, club_id)
            # The overlay's raw bias for go_for_catches should be positive.
            raw = _raw_drift(conn, club_id)
            assert raw["catch_posture"]["go_for_catches"] > 0.0

    def test_user_club_never_drifted(self):
        from dodgeball_sim.meta_drift import apply_meta_drift, tactic_drift_for

        conn, season_id, _clubs, user_club = _drift_fixture()
        apply_meta_drift(conn, season_id, _SEED)
        assert tactic_drift_for(conn, user_club) == {}

    def test_contrarian_fraction_drifts_away(self):
        from dodgeball_sim.meta_drift import apply_meta_drift, tactic_drift_for
        from dodgeball_sim.config import WeatherConfig

        # Use a custom config with contrarian_fraction=1.0 (all clubs contrarian)
        # to make the test deterministic and clear.
        conn, season_id, clubs, user_club = _drift_fixture()
        cfg = WeatherConfig(contrarian_fraction=1.0, drift_rate=0.5)
        apply_meta_drift(conn, season_id, _SEED, config=cfg)
        # All AI clubs should drift AWAY from go_for_catches — contrarians push
        # the runner-up (play_safe) UP, not the winner DOWN.
        for club_id in clubs:
            raw = _raw_drift(conn, club_id)
            # The runner-up (play_safe) should have a positive bias.
            assert raw["catch_posture"]["play_safe"] > 0.0
            # And go_for_catches should NOT be the top value.
            top_val = max(raw["catch_posture"], key=raw["catch_posture"].get)
            assert top_val != "go_for_catches"

    def test_idempotent_per_season(self):
        from dodgeball_sim.meta_drift import apply_meta_drift, tactic_drift_for

        conn, season_id, _clubs, _user = _drift_fixture()
        apply_meta_drift(conn, season_id, _SEED)
        snapshot = _all_raw_drift(conn)
        apply_meta_drift(conn, season_id, _SEED)
        assert _all_raw_drift(conn) == snapshot

    def test_legacy_save_no_drift(self):
        from dodgeball_sim.meta_drift import apply_meta_drift, tactic_drift_for

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        initialize_curated_manager_career(conn, "aurora", _SEED, ruleset_selection="official_foam")
        conn.commit()
        sid = get_state(conn, "active_season_id")
        apply_meta_drift(conn, sid, _SEED)
        # No overlay written for any club.
        for club_id in load_clubs(conn):
            assert tactic_drift_for(conn, club_id) == {}


# ---------------------------------------------------------------------------
# Task 2.2 — consume drift in get_ai_tactics
# ---------------------------------------------------------------------------


class TestGetAiTacticsDrift:
    def test_drifted_club_biased_toward_overlay(self):
        from dodgeball_sim.ai_tactics import get_ai_tactics

        # An Aging Veterans base uses play_safe; a drift toward go_for_catches
        # should flip catch_posture to go_for_catches.
        drift = {"catch_posture": "go_for_catches"}
        tactics = get_ai_tactics("Aging Veterans", "Balanced", drift=drift)
        assert tactics["catch_posture"] == "go_for_catches"

    def test_undrifted_club_unchanged(self):
        from dodgeball_sim.ai_tactics import get_ai_tactics

        tactics = get_ai_tactics("Aging Veterans", "Balanced", drift=None)
        assert tactics["catch_posture"] == "play_safe"

    def test_precedence_intent_overrides_archetype_then_drift_overrides_intent(self):
        from dodgeball_sim.ai_tactics import get_ai_tactics

        # Contender base: aggressive/go_for_catches/all_in.
        # "Preserve Health" intent: patient/play_safe/hold_back.
        # Drift: go_for_catches should override the intent's play_safe.
        drift = {"catch_posture": "go_for_catches", "approach": "aggressive"}
        tactics = get_ai_tactics("Contender", "Preserve Health", drift=drift)
        assert tactics["catch_posture"] == "go_for_catches"
        assert tactics["approach"] == "aggressive"
        # rush_commit was set by intent (hold_back) and NOT in drift ⇒ stays.
        assert tactics["rush_commit"] == "hold_back"

    def test_no_collisions_in_precedence(self):
        """Drift only overrides dimensions it specifies; others stay as
        archetype+intent determined."""
        from dodgeball_sim.ai_tactics import get_ai_tactics

        drift = {"rush_target": "strongest_side"}
        tactics = get_ai_tactics("Power Throwers", "Win Now", drift=drift)
        assert tactics["rush_target"] == "strongest_side"
        # Everything else is the Power Throwers + Win Now base.
        assert tactics["approach"] == "aggressive"
        assert tactics["rush_commit"] == "all_in"

    def test_determinism_preserved(self):
        from dodgeball_sim.ai_tactics import get_ai_tactics

        drift = {"catch_posture": "go_for_catches", "approach": "patient"}
        t1 = get_ai_tactics("Defensive Specialist", "Balanced", drift=drift)
        t2 = get_ai_tactics("Defensive Specialist", "Balanced", drift=drift)
        assert t1 == t2


# ---------------------------------------------------------------------------
# Helpers — read the raw persisted drift overlay
# ---------------------------------------------------------------------------


def _raw_drift(conn, club_id):
    from dodgeball_sim.meta_drift import _load_drift_store

    store = _load_drift_store(conn)
    return store.get(club_id, {})


def _all_raw_drift(conn):
    from dodgeball_sim.meta_drift import _load_drift_store

    return _load_drift_store(conn)
