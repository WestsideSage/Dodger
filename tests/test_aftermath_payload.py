import sqlite3
from fastapi.testclient import TestClient

from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import create_schema
from dodgeball_sim.career_setup import initialize_curated_manager_career

def test_aftermath_payload_structure():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        res = client.post('/api/command-center/simulate', json={'intent': 'Win Now'})
        assert res.status_code == 200
        data = res.json()
        print(f"DEBUG KEYS: {list(data.keys())}")
        assert 'aftermath' in data
        assert 'headline' in data['aftermath']
        assert 'player_growth_deltas' in data['aftermath']
        assert 'recruit_reactions' in data['aftermath']
    finally:
        app.dependency_overrides.clear()
