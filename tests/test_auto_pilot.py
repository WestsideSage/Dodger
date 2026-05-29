"""Phase 2 — multi-week auto-pilot (fast-forward) coverage.

Auto-pilot loops the canonical command-center weekly sim with the persisted
plan, so these tests double as a regression guard that the Phase 1 canonical
fielded-6 path survives a full season of skipped weeks.
"""
from __future__ import annotations

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState
from dodgeball_sim.persistence import (
    connect,
    load_career_state_cursor,
    load_standings,
    get_state,
)
from dodgeball_sim.use_cases import SimulateWeekError, auto_pilot_weeks, simulate_week


def _career_conn(tmp_path, name="aurora", seed=20260426):
    # ``name`` only varies the db filename; the curated club is always "aurora".
    db_path = tmp_path / f"{name}.db"
    conn = connect(db_path)
    initialize_curated_manager_career(conn, "aurora", root_seed=seed)
    conn.commit()
    return conn


def test_auto_pilot_runs_to_offseason(tmp_path):
    conn = _career_conn(tmp_path)
    result = auto_pilot_weeks(conn)

    assert result["status"] == "success"
    assert result["stop_reason"] == "season_complete"
    assert result["next_state"] == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT.value
    assert result["weeks_simulated"] >= 1
    # Every simulated week reports a summary row.
    assert len(result["week_summaries"]) == result["weeks_simulated"]
    # Career cursor genuinely advanced to the offseason beat.
    assert load_career_state_cursor(conn).state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT


def test_auto_pilot_respects_max_weeks(tmp_path):
    conn = _career_conn(tmp_path)
    result = auto_pilot_weeks(conn, max_weeks=2)

    assert result["weeks_simulated"] == 2
    assert result["stop_reason"] == "max_weeks"
    # Mid-season, still ready for the next pre-match week.
    assert result["next_state"] == CareerState.SEASON_ACTIVE_PRE_MATCH.value
    assert load_career_state_cursor(conn).state == CareerState.SEASON_ACTIVE_PRE_MATCH


def test_auto_pilot_zero_is_noop(tmp_path):
    conn = _career_conn(tmp_path)
    result = auto_pilot_weeks(conn, max_weeks=0)

    assert result["weeks_simulated"] == 0
    assert result["stop_reason"] == "max_weeks"
    assert load_career_state_cursor(conn).state == CareerState.SEASON_ACTIVE_PRE_MATCH


def test_auto_pilot_is_deterministic_for_same_seed(tmp_path):
    conn_a = _career_conn(tmp_path, name="a", seed=777)
    conn_b = _career_conn(tmp_path, name="b", seed=777)

    res_a = auto_pilot_weeks(conn_a)
    res_b = auto_pilot_weeks(conn_b)

    assert res_a["weeks_simulated"] == res_b["weeks_simulated"]
    assert res_a["week_summaries"] == res_b["week_summaries"]

    season_a = get_state(conn_a, "active_season_id")
    season_b = get_state(conn_b, "active_season_id")
    standings_a = [
        (row.club_id, row.wins, row.losses, row.draws)
        for row in load_standings(conn_a, season_a)
    ]
    standings_b = [
        (row.club_id, row.wins, row.losses, row.draws)
        for row in load_standings(conn_b, season_b)
    ]
    assert standings_a == standings_b


def test_auto_pilot_matches_manual_week_by_week(tmp_path):
    """Auto-pilot and a manual per-week walk must agree for the same seed —
    proving auto-pilot fields the same persisted/canonical lineup a human pass
    would, not a divergent default."""
    conn_auto = _career_conn(tmp_path, name="auto", seed=4242)
    conn_manual = _career_conn(tmp_path, name="manual", seed=4242)

    auto = auto_pilot_weeks(conn_auto)

    manual_summaries = []
    while load_career_state_cursor(conn_manual).state == CareerState.SEASON_ACTIVE_PRE_MATCH:
        res = simulate_week(conn_manual, update=None)
        dash = res.get("dashboard") or {}
        manual_summaries.append(
            {
                "week": dash.get("week"),
                "opponent_name": dash.get("opponent_name"),
                "result": dash.get("result"),
            }
        )
        if res.get("next_state") != CareerState.SEASON_ACTIVE_PRE_MATCH.value:
            break

    assert auto["week_summaries"] == manual_summaries


def test_fast_forward_endpoint(tmp_path):
    import sqlite3

    from fastapi.testclient import TestClient

    from dodgeball_sim import server
    from dodgeball_sim.persistence import create_schema

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).post(
            "/api/command-center/fast-forward", json={"max_weeks": 3}
        )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["weeks_simulated"] == 3
    assert body["stop_reason"] == "max_weeks"
    assert len(body["week_summaries"]) == 3


def test_auto_pilot_rejects_wrong_state(tmp_path):
    conn = _career_conn(tmp_path)
    # Drive to offseason first.
    auto_pilot_weeks(conn)
    # Now in offseason beat — a second call is a graceful no-op, not an error.
    again = auto_pilot_weeks(conn)
    assert again["stop_reason"] == "already_complete"
    assert again["weeks_simulated"] == 0
