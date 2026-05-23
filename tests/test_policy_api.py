from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_tactics_endpoint_accepts_v2_payload_and_persists_it():
    conn = _career_conn()

    def override_db():
        yield conn

    payload = {
        "approach": "aggressive",
        "target_focus": "ball_holders",
        "catch_posture": "go_for_catches",
        "rush_commit": "all_in",
        "rush_target": "strongest_side",
    }

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        update = client.post("/api/tactics", json=payload)
        fetched = client.get("/api/tactics")
    finally:
        server.app.dependency_overrides.clear()

    assert update.status_code == 200
    assert fetched.status_code == 200
    assert fetched.json() == payload


def test_command_center_plan_rejects_legacy_tactics_payload():
    conn = _career_conn()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        response = client.post(
            "/api/command-center/plan",
            json={
                "intent": "Win Now",
                "tactics": {
                    "target_stars": 0.7,
                    "target_ball_holder": 0.5,
                    "risk_tolerance": 0.5,
                    "sync_throws": 0.2,
                    "rush_frequency": 0.5,
                    "rush_proximity": 0.5,
                    "tempo": 0.5,
                    "catch_bias": 0.5,
                },
            },
        )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 400


def test_command_center_plan_accepts_v2_tactics_payload():
    conn = _career_conn()

    def override_db():
        yield conn

    payload = {
        "approach": "patient",
        "target_focus": "spread",
        "catch_posture": "play_safe",
        "rush_commit": "hold_back",
        "rush_target": "nearest",
    }

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        response = client.post(
            "/api/command-center/plan",
            json={"intent": "Preserve Health", "tactics": payload},
        )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["plan"]["tactics"] == payload


def test_voice_register_endpoint_returns_tier1_copy():
    conn = _career_conn()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        response = client.get("/api/voice-register/1")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["policy.approach.aggressive.label"] == "Aggressive"
    assert "moment.dramatic_catch.headline" in payload
