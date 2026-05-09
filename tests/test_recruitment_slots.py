import sqlite3
from fastapi.testclient import TestClient

from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import create_schema, set_state
from dodgeball_sim.career_setup import initialize_curated_manager_career

def test_slot_economy_budget():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    set_state(conn, "active_season_id", "season_1")
    set_state(conn, "player_club_id", "aurora")
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.get("/api/dynasty-office")
        assert resp.status_code == 200
        data = resp.json()
        assert "recruiting" in data
        
        budget = data["recruiting"].get("budget")
        assert budget is not None
        assert budget["scout"] == [0, 3]
        assert budget["contact"] == [0, 5]
        assert budget["visit"] == [0, 1]
    finally:
        app.dependency_overrides.clear()
