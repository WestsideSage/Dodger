import sqlite3
from fastapi.testclient import TestClient

from dodgeball_sim.development import calculate_potential_tier
from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import create_schema
from dodgeball_sim.career_setup import initialize_curated_manager_career

def test_potential_tier_mapping():
    # Elite >= 90, High 80-89, Solid 65-79, Limited < 65
    assert calculate_potential_tier(92) == "Elite"
    assert calculate_potential_tier(85) == "High"
    assert calculate_potential_tier(75) == "Solid"
    assert calculate_potential_tier(50) == "Limited"

def test_roster_endpoint_payload_structure():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/api/roster")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    players = data["roster"]
    assert len(players) > 0
    
    for player in players:
        assert "potential_tier" in player
        assert "scouting_confidence" in player
        assert "weekly_ovr_history" in player
        # Verify potential (float) is omitted
        if "traits" in player:
             assert "potential" not in player["traits"]
        assert "potential" not in player
