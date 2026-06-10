from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema


def test_highlights_endpoint_returns_beats_with_proof_sources() -> None:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    # Seed 20260428, not 20260426: the V19a rec-engine consumers (stamina
    # staying power, tactical_iq timing/read, role fit, rush sprinters)
    # shifted the old seed's week-1 match to a 2-beat reel; this seed's
    # match produces a full >=4-beat reel so the endpoint contract stays
    # strongly exercised.
    initialize_curated_manager_career(conn, "aurora", root_seed=20260428)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        sim = client.post("/api/command-center/simulate", json={"intent": "Win Now"})
        assert sim.status_code == 200
        match_id = sim.json()["dashboard"]["match_id"]

        replay = client.get(f"/api/matches/{match_id}/replay")
        assert replay.status_code == 200
        assert "broadcast_frame" in replay.json()
        assert "commentary_inserts" in replay.json()

        highlights = client.get(f"/api/matches/{match_id}/highlights")
        assert highlights.status_code == 200
        payload = highlights.json()
        assert payload["match_id"] == match_id
        assert len(payload["beats"]) >= 4
        assert all(beat["proof_source"].startswith("event:") for beat in payload["beats"])
        assert all("source_event_id" in beat for beat in payload["beats"])
    finally:
        server.app.dependency_overrides.clear()
