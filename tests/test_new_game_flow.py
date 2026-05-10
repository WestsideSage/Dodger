from fastapi.testclient import TestClient
from dodgeball_sim.server import app, SAVES_DIR, _active_save_path
import shutil
import pytest

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
