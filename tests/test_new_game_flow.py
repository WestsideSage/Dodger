from fastapi.testclient import TestClient
from dodgeball_sim.server import app, SAVES_DIR, _active_save_path
import shutil
import pytest
import json

from dodgeball_sim.persistence import connect, get_state, load_prospect_pool
from dodgeball_sim.save_service import build_from_scratch_save, starting_prospects_payload

def test_build_from_scratch_endpoints():
    client = TestClient(app)
    
    # Cleanup any old test runs
    from pathlib import Path
    old_save = SAVES_DIR / "test_scratch.db"
    if old_save.exists():
        old_save.unlink()
    
    # 1. Get starting prospects
    res = client.get("/api/saves/starting-prospects")
    assert res.status_code == 200
    prospects = res.json()["prospects"]
    assert len(prospects) >= 20
    
    # Pick 10 player IDs
    chosen_ids = [p["player_id"] for p in prospects[:10]]
    
    payload = {
        "save_name": "test_scratch",
        "club_name": "Test Builders",
        "city": "Testville",
        "colors": "#FF0000,#000000",
        "coach_name": "Test Coach",
        "coach_backstory": "Tactical Mastermind",
        "roster_player_ids": chosen_ids
    }
    
    res = client.post("/api/saves/build-from-scratch", json=payload)
    if res.status_code != 200:
        print(res.json())
    assert res.status_code == 200
    
    # Load it to verify
    res = client.get("/api/status")
    assert res.status_code == 200
    assert res.json()["context"]["player_club_name"] == "Test Builders"
    
    # Check roster size
    res = client.get("/api/roster")
    assert len(res.json()["roster"]) == 10
    
    # Cleanup
    global _active_save_path
    if _active_save_path:
        _active_save_path.unlink(missing_ok=True)
        _active_save_path = None


def test_build_from_scratch_warm_prospects_target_active_pool(tmp_path):
    prospects = starting_prospects_payload()["prospects"]
    chosen_ids = [prospect["player_id"] for prospect in prospects[:10]]
    payload = {
        "save_name": "warm_pool_check",
        "club_name": "Warm Pool Checkers",
        "city": "Testville",
        "colors": "#FF0000,#000000",
        "coach_name": "Test Coach",
        "coach_backstory": "Tactical Mastermind",
        "roster_player_ids": chosen_ids,
        "root_seed": 20260426,
    }

    result = build_from_scratch_save(tmp_path, payload)
    conn = connect(result["path"])
    try:
        active_pool_ids = {prospect.player_id for prospect in load_prospect_pool(conn, 1)}
        actions = json.loads(get_state(conn, "prospect_recruitment_actions_json") or "{}")
    finally:
        conn.close()

    assert actions
    assert set(actions).issubset(active_pool_ids)
    assert all(action == {"scouted": True, "contacted": True} for action in actions.values())
