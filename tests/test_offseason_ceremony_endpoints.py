import sqlite3
from fastapi.testclient import TestClient

from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import create_schema, set_state, save_career_state_cursor, load_career_state_cursor
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState
import dataclasses

def test_offseason_ceremony_payload():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    
    # Put save into offseason state
    cursor = load_career_state_cursor(conn)
    cursor = dataclasses.replace(cursor, state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0)
    save_career_state_cursor(conn, cursor)
    
    # Set dummy offseason JSONs so parsing doesn't fail
    set_state(conn, "offseason_records_json", '[]')
    set_state(conn, "offseason_hof_json", '[]')
    set_state(conn, "offseason_rookie_preview_json", '[]')
    set_state(conn, "offseason_development_json", '[]')
    set_state(conn, "offseason_retirements_json", '[]')
    
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        res = client.get("/api/offseason/beat")
        assert res.status_code == 200
        data = res.json()
        assert "beat_index" in data
        assert "key" in data
        assert "body" in data
    finally:
        app.dependency_overrides.clear()
