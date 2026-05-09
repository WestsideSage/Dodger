import sqlite3
from fastapi.testclient import TestClient

from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import create_schema, set_state
from dodgeball_sim.career_setup import initialize_curated_manager_career

def test_recruiting_verb_scout():
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
        # First verify budget
        resp = client.get("/api/dynasty-office")
        initial_scout = resp.json()["recruiting"]["budget"]["scout"][0]
        
        prospect_id = resp.json()["recruiting"]["prospects"][0]["player_id"]
        
        # Action: Scout
        res = client.post(f"/api/recruiting/scout/{prospect_id}")
        assert res.status_code == 200
        
        # Verify slot deducted
        resp = client.get("/api/dynasty-office")
        assert resp.json()["recruiting"]["budget"]["scout"][0] == initial_scout + 1
    finally:
        app.dependency_overrides.clear()

def test_pitch_angle_season_lock():
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
        # First call: OK
        res = client.post("/api/recruiting/pitch-angle", json={"angle": "Academic Excellence"})
        assert res.status_code == 200
        
        # Second call: 400 (locked)
        res = client.post("/api/recruiting/pitch-angle", json={"angle": "Facilities"})
        assert res.status_code == 400
        assert "already chosen" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()

def test_sign_action_gating():
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
        # Try to sign (not signing_day state)
        res = client.post("/api/recruiting/sign/prospect_1")
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()
