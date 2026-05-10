from fastapi.testclient import TestClient
from dodgeball_sim.server import app, get_db
import sqlite3
from dodgeball_sim.persistence import create_schema
from dodgeball_sim.career_setup import initialize_curated_manager_career

def test_dynasty_history_endpoints():
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
        
        # Test my-program
        res = client.get("/api/history/my-program?club_id=aurora")
        assert res.status_code == 200
        data = res.json()
        assert "timeline" in data
        assert "alumni" in data
        assert "banners" in data

        # Test league
        res = client.get("/api/history/league")
        assert res.status_code == 200
        data = res.json()
        assert "directory" in data
        assert "dynasty_rankings" in data
        assert "records" in data
        assert "hof" in data
    finally:
        app.dependency_overrides.clear()
