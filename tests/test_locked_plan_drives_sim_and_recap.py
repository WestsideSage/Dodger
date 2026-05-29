"""End-to-end: the locked tactical plan must drive the sim and the recap.

Playtest finding: after locking a chosen plan, the post-match recap reported a
different (default) tactic. This exercises the real service flow — save tactics,
lock (intent-only), simulate — and asserts the player's chosen approach reaches
both the applied plan and the recap copy.
"""
import json
import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema
from dodgeball_sim.use_cases import simulate_week


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_locked_tactics_reach_sim_and_recap():
    conn = _career_conn()

    def override_db():
        yield conn

    chosen = {
        "approach": "patient",
        "target_focus": "spread",
        "catch_posture": "play_safe",
        "rush_commit": "hold_back",
        "rush_target": "nearest",
    }

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        intent = client.get("/api/command-center").json()["plan"]["intent"]

        # Edit Game Plan, then Lock (intent only).
        assert client.post("/api/command-center/plan", json={"intent": intent, "tactics": chosen}).status_code == 200
        locked = client.post("/api/command-center/plan", json={"intent": intent})
        assert locked.json()["plan"]["tactics"] == chosen

        # Simulate via the same service the frontend calls.
        result = simulate_week(conn, update={"intent": intent})
    finally:
        server.app.dependency_overrides.clear()

    # The applied plan carried the chosen tactics...
    assert result["plan"]["tactics"] == chosen
    # ...and the recap reflects the chosen approach, not a default.
    blob = json.dumps(result["aftermath"])
    assert "Patient - team waits" in blob
    assert "Aggressive - team throws" not in blob
