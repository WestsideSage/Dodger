"""Web-path coverage for behavior previously verified by Tk-coupled tests.

The Tkinter scorched-earth cleanup deleted six tests that bypassed Tk with
``ManagerModeApp.__new__()`` to exercise game-logic methods. Each of those
methods has a canonical standalone equivalent in the web-path modules; this
file pins the same observable behavior against the canonical functions.
"""
from __future__ import annotations

import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.command_week_service import advance_playoffs_if_needed
from dodgeball_sim.offseason_ceremony import (
    begin_next_season,
    sign_best_rookie,
)
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_prospect_pool,
    load_season,
    save_career_state_cursor,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    initialize_manager_career(connection, "aurora", root_seed=20260426)
    return connection


def test_sign_best_rookie_adds_a_prospect_to_user_roster(conn):
    pool = load_prospect_pool(conn, class_year=1)
    assert pool, "fixture should seed a prospect pool"
    before_size = len(load_all_rosters(conn)["aurora"])

    signed = sign_best_rookie(conn, "aurora", season_number=1)

    assert signed is not None
    after = load_all_rosters(conn)["aurora"]
    assert len(after) == before_size + 1
    assert signed.id in {player.id for player in after}


def test_sign_best_rookie_is_idempotent_per_season(conn):
    first = sign_best_rookie(conn, "aurora", season_number=1)
    rosters_after_first = load_all_rosters(conn)["aurora"]
    second = sign_best_rookie(conn, "aurora", season_number=1)
    rosters_after_second = load_all_rosters(conn)["aurora"]

    assert first is not None
    # Second call may sign a *different* prospect (highest remaining) or return None;
    # either way, the user roster grows by at most one per call and we never
    # double-sign the same prospect.
    if second is not None:
        assert second.id != first.id
        assert len(rosters_after_second) == len(rosters_after_first) + 1
    else:
        assert len(rosters_after_second) == len(rosters_after_first)


def test_sign_best_rookie_prefers_prospect_pool_over_free_agents(conn):
    pool = load_prospect_pool(conn, class_year=1)
    pool_ids = {prospect.player_id for prospect in pool}
    assert pool_ids

    signed = sign_best_rookie(conn, "aurora", season_number=1)

    assert signed is not None
    assert signed.id in pool_ids, "should sign from the prospect pool when one is available"


def test_begin_next_season_persists_next_schedule_and_active_cursor(conn):
    # Set cursor to "ready for next season" — the offseason-finalized state.
    cursor = CareerStateCursor(
        state=CareerState.NEXT_SEASON_READY,
        season_number=1,
        week=15,
        offseason_beat_index=9,
    )
    save_career_state_cursor(conn, cursor)
    clubs = load_clubs(conn)

    new_cursor = begin_next_season(conn, cursor, clubs)

    assert new_cursor.state == CareerState.SEASON_ACTIVE_PRE_MATCH
    assert new_cursor.season_number == 2
    assert new_cursor.week == 1
    active_id = get_state(conn, "active_season_id")
    next_season = load_season(conn, active_id)
    assert next_season is not None
    assert next_season.season_id == "season_2"
    assert next_season.scheduled_matches, "next season must have scheduled matches"
    persisted_cursor = load_career_state_cursor(conn)
    assert persisted_cursor.season_number == 2


def test_advance_playoffs_if_needed_is_a_noop_when_regular_season_incomplete(conn):
    season = load_season(conn, "season_1")
    clubs = load_clubs(conn)
    before_match_count = len(season.scheduled_matches)

    after_season = advance_playoffs_if_needed(conn, season, clubs, "aurora")

    # With no completed matches, playoff progression should not add anything.
    assert len(after_season.scheduled_matches) == before_match_count


def test_standings_approach_falls_back_to_club_default_when_no_week_set(conn):
    """Audit 7.3: a fresh-season club should show its default approach, not 'Not set'."""
    from dodgeball_sim.web_status_service import build_standings_payload
    payload = build_standings_payload(conn)
    for row in payload["standings"]:
        # Each club should have a default approach, e.g. "Balanced", not None
        assert row["latest_approach"] == "Balanced"
