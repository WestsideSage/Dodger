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
