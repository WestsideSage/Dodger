import sqlite3
from fastapi.testclient import TestClient
from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import create_schema
from dodgeball_sim.career_setup import initialize_curated_manager_career

def test_standings_includes_recent_matches():
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
        # Advance the week to generate matches
        client.post("/api/sim", json={"mode": "week"})
        client.post("/api/sim", json={"mode": "week"})
        
        res = client.get('/api/standings')
        data = res.json()
        assert 'recent_matches' in data
        assert type(data['recent_matches']) == list
    finally:
        app.dependency_overrides.clear()
