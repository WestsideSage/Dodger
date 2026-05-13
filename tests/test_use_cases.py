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
