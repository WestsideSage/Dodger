"""End-to-end: an official-ruleset career routes through OfficialEngineAdapter.

Validates that:
- Existing careers without ``ruleset_selection`` keep using ``MatchEngine``.
- Careers initialized with ``ruleset_selection="official_foam"`` produce
  match records with ``config_version`` starting with ``official:``.
"""

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    connect,
    get_state,
    load_clubs,
    load_season,
)
from dodgeball_sim.rulesets import FOAM_OPEN


def _setup_career(ruleset_selection=None):
    conn = connect(":memory:")
    initialize_curated_manager_career(
        conn, "aurora", root_seed=42, ruleset_selection=ruleset_selection,
    )
    return conn


def _simulate_one_match(conn, ruleset_selection):
    from dodgeball_sim.game_loop import simulate_scheduled_match
    season = load_season(conn, get_state(conn, "active_season_id"))
    clubs = load_clubs(conn)
    scheduled = season.matches_for_week(1)[0]
    from dodgeball_sim.persistence import load_club_roster
    rosters = {club_id: load_club_roster(conn, club_id) for club_id in clubs}
    record = simulate_scheduled_match(
        conn,
        scheduled=scheduled,
        clubs=clubs,
        rosters=rosters,
        root_seed=42,
        difficulty="pro",
        record_engine_match=False,
    )
    return record


def test_generic_career_uses_generic_engine():
    conn = _setup_career(ruleset_selection=None)
    record = _simulate_one_match(conn, None)
    # Generic engine writes config_version="phase1.v1" by default
    assert not record.config_version.startswith("official:")


def test_official_career_routes_through_official_engine():
    conn = _setup_career(ruleset_selection="official_foam")
    record = _simulate_one_match(conn, "official_foam")
    assert record.config_version.startswith("official:")
    assert record.config_version == "official:official_foam"


def test_official_career_match_record_has_result():
    conn = _setup_career(ruleset_selection="official_foam")
    record = _simulate_one_match(conn, "official_foam")
    # MatchRecord.result is the in-memory MatchResult
    assert record.result is not None
    assert "teams" in record.result.box_score


def test_official_career_replay_payload_exposes_official_state():
    from dodgeball_sim.game_loop import simulate_scheduled_match
    from dodgeball_sim.persistence import load_club_roster
    from dodgeball_sim.replay_service import match_replay_payload

    conn = _setup_career(ruleset_selection="official_foam")
    season = load_season(conn, get_state(conn, "active_season_id"))
    clubs = load_clubs(conn)
    scheduled = season.matches_for_week(1)[0]
    rosters = {club_id: load_club_roster(conn, club_id) for club_id in clubs}
    record = simulate_scheduled_match(
        conn,
        scheduled=scheduled,
        clubs=clubs,
        rosters=rosters,
        root_seed=42,
        difficulty="pro",
        record_engine_match=True,
    )
    payload = match_replay_payload(conn, record.match_id)
    assert payload["config_version"] == "official:official_foam"
    assert payload["official_state"]["ruleset"] == "foam-open"
    # The replay exposes the final game's clock, which run_autonomous_match caps
    # to the remaining match window (min(game_clock_seconds, remaining)). Assert a
    # sane, positive limit within the profile bound rather than an incidental value.
    game_clock_limit = payload["official_state"]["game_clock"]["limit_seconds"]
    assert 0 < game_clock_limit <= FOAM_OPEN.game_clock_seconds
    assert payload["official_state"]["burden"] is not None
    assert payload["official_state"]["balls"]
    assert payload["official_state"]["teams"]
    assert payload["official_state"]["rule_calls"]
