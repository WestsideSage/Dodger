from __future__ import annotations

import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import connect, create_schema


def _career_conn(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_simulate_week_use_case_is_importable():
    from dodgeball_sim.use_cases import simulate_week
    assert callable(simulate_week)


def test_simulate_week_returns_expected_keys(tmp_path):
    from dodgeball_sim.use_cases import simulate_week

    conn = _career_conn(tmp_path)
    result = simulate_week(conn, update=None)

    assert "status" in result
    assert result["status"] == "success"
    assert "plan" in result
    assert "dashboard" in result
    assert "aftermath" in result
    assert "next_state" in result


def test_simulate_week_with_intent_override(tmp_path):
    from dodgeball_sim.use_cases import simulate_week

    conn = _career_conn(tmp_path)
    result = simulate_week(conn, update={"intent": "Develop Youth"})

    assert result["status"] == "success"
    assert result["plan"]["intent"] == "Develop Youth"


def test_simulate_week_advances_bye_without_skipping_league_matches(tmp_path):
    from dodgeball_sim.game_loop import current_week
    from dodgeball_sim.persistence import (
        get_state,
        load_career_state_cursor,
        load_command_history,
        load_completed_match_ids,
        load_season,
    )
    from dodgeball_sim.use_cases import simulate_week

    conn = _career_conn(tmp_path)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    season = load_season(conn, season_id)
    week_one_ids = {match.match_id for match in season.matches_for_week(1)}
    player_week_one_ids = {
        match.match_id
        for match in season.matches_for_week(1)
        if player_club_id in (match.home_club_id, match.away_club_id)
    }
    conn.execute(
        "DELETE FROM scheduled_matches WHERE season_id = ? AND week = 1 AND (home_club_id = ? OR away_club_id = ?)",
        (season_id, player_club_id, player_club_id),
    )
    conn.commit()

    result = simulate_week(conn, update={"intent": "Preserve Health"})

    assert result["status"] == "success"
    assert result["dashboard"]["result"] == "Bye Week"
    assert result["aftermath"]["match_card"] is None
    assert (week_one_ids - player_week_one_ids) <= load_completed_match_ids(conn, season_id)
    assert not (player_week_one_ids & load_completed_match_ids(conn, season_id))
    assert current_week(conn, load_season(conn, season_id)) == 2
    assert load_career_state_cursor(conn).week == 2
    assert load_command_history(conn, season_id) == []


def test_simulate_week_raises_on_empty_db():
    from dodgeball_sim.use_cases import SimulateWeekError, simulate_week

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.commit()

    with pytest.raises(SimulateWeekError):
        simulate_week(conn, update=None)


def test_simulate_week_raises_on_wrong_career_state(tmp_path):
    from dodgeball_sim.career_state import CareerState
    from dodgeball_sim.persistence import load_career_state_cursor, save_career_state_cursor
    from dodgeball_sim.use_cases import SimulateWeekError, simulate_week

    conn = _career_conn(tmp_path)
    cursor = load_career_state_cursor(conn)
    import dataclasses
    wrong_cursor = dataclasses.replace(cursor, state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT)
    save_career_state_cursor(conn, wrong_cursor)
    conn.commit()

    with pytest.raises(SimulateWeekError):
        simulate_week(conn, update=None)
