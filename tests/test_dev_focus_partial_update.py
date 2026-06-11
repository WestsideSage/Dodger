"""Verify POSTing a partial department_orders update preserves other orders."""
import sqlite3
from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema

def test_dev_focus_partial_update_preserves_other_orders():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)

        initial = client.get('/api/command-center').json()
        initial_orders = initial['plan']['department_orders']
        assert 'tactics' in initial_orders

        response = client.post(
            '/api/command-center/plan',
            json={
                'intent': initial['plan']['intent'],
                'department_orders': {'dev_focus': 'YOUTH_ACCELERATION'},
            },
        )
        assert response.status_code == 200
        after = response.json()['plan']['department_orders']

        assert after.get('dev_focus') == 'YOUTH_ACCELERATION'
        for key, value in initial_orders.items():
            if key == 'dev_focus':
                continue
            assert after.get(key) == value, f"department order '{key}' was clobbered"
    finally:
        server.app.dependency_overrides.clear()


def test_dev_and_staff_focus_carry_into_a_fresh_week():
    """Playtest 3 F-2 regression: dev focus and staff focus are season-spanning
    decisions — a fresh week's default plan must carry the latest saved values
    instead of silently resetting to Balanced/tactics every Monday. Pins the
    load (persistence) half: the most recent saved plan before the new week."""
    from dodgeball_sim.persistence import (
        get_state,
        load_latest_weekly_plan_orders,
        save_weekly_command_plan,
    )

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    season_id = get_state(conn, "active_season_id")
    save_weekly_command_plan(conn, {
        "season_id": season_id, "week": 1, "player_club_id": "aurora",
        "intent": "Balanced",
        "department_orders": {
            "dev_focus": "YOUTH_ACCELERATION",
            "focus_department": "training",
        },
    })
    conn.commit()

    carried = load_latest_weekly_plan_orders(conn, season_id, 2, "aurora")
    assert carried.get("dev_focus") == "YOUTH_ACCELERATION"
    assert carried.get("focus_department") == "training"


def test_season_end_dev_focus_is_the_last_saved_plan():
    """Playtest 3 FF-audit B: offseason growth runs on the dev focus of the
    PLAYER's latest saved weekly plan. Under fast-forward no further user
    plans are written, so the last hand-set focus rules — a season-long plan
    survives FF instead of silently reverting to Balanced."""
    from dodgeball_sim.offseason_ceremony import _load_player_dev_focus
    from dodgeball_sim.persistence import get_state, save_weekly_command_plan

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    season_id = get_state(conn, "active_season_id")
    for week, focus in ((1, "YOUTH_ACCELERATION"), (3, "STRENGTH_AND_CONDITIONING")):
        save_weekly_command_plan(conn, {
            "season_id": season_id, "week": week, "player_club_id": "aurora",
            "intent": "Balanced",
            "department_orders": {"dev_focus": focus},
        })
    conn.commit()

    assert _load_player_dev_focus(conn, season_id, "aurora") == "STRENGTH_AND_CONDITIONING"
