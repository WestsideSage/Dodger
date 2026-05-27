"""Tests for canonical recruiting status derivation and API exposure."""
from __future__ import annotations

import json
import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema, set_state
from dodgeball_sim.recruiting_office import (
    RECRUITING_STATUSES,
    compute_recruiting_status,
)
from dodgeball_sim.server import app, get_db


def test_unscouted_default():
    assert compute_recruiting_status(None) == "UNSCOUTED"
    assert compute_recruiting_status({}) == "UNSCOUTED"


def test_scouted_promotion():
    assert compute_recruiting_status({"scouted": True}) == "SCOUTED"


def test_contacted_overrides_scouted():
    assert compute_recruiting_status({"scouted": True, "contacted": True}) == "CONTACTED"


def test_visited_overrides_contacted():
    assert compute_recruiting_status({
        "scouted": True,
        "contacted": True,
        "visited": True,
    }) == "VISITED"


def test_interested_overrides_visited():
    assert compute_recruiting_status({"visited": True, "interested": True}) == "INTERESTED"


def test_locked_out_overrides_everything():
    assert compute_recruiting_status({
        "scouted": True,
        "contacted": True,
        "visited": True,
        "interested": True,
        "locked_out": True,
    }) == "LOCKED_OUT"


def test_status_values_are_canonical():
    expected = {"UNSCOUTED", "SCOUTED", "CONTACTED", "VISITED", "INTERESTED", "LOCKED_OUT"}
    assert set(RECRUITING_STATUSES) == expected


def _bootstrap_career(conn: sqlite3.Connection) -> None:
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    set_state(conn, "active_season_id", "season_1")
    set_state(conn, "player_club_id", "aurora")
    conn.commit()


def test_api_exposes_recruiting_status_field():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _bootstrap_career(conn)

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.get("/api/dynasty-office")
        assert resp.status_code == 200
        prospects = resp.json()["recruiting"]["prospects"]
        assert prospects, "expected at least one prospect"
        for p in prospects:
            assert "recruiting_status" in p
            assert p["recruiting_status"] in RECRUITING_STATUSES
            assert p["recruiting_status"] == "UNSCOUTED"
    finally:
        app.dependency_overrides.clear()


def test_contact_action_persists_and_status_updates():
    """Reproduces playtest bug #4: Contact/Visit actions must persist
    and be visible via the API as a status change.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _bootstrap_career(conn)

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.get("/api/dynasty-office")
        prospect_id = resp.json()["recruiting"]["prospects"][0]["player_id"]

        # Contact
        res = client.post(f"/api/recruiting/contact/{prospect_id}")
        assert res.status_code == 200

        # Re-fetch and verify status promoted to CONTACTED
        resp2 = client.get("/api/dynasty-office")
        matched = next(
            p for p in resp2.json()["recruiting"]["prospects"]
            if p["player_id"] == prospect_id
        )
        assert matched["recruiting_status"] == "CONTACTED"
        assert matched["contacted"] is True

        # Visit promotes further
        res = client.post(f"/api/recruiting/visit/{prospect_id}")
        assert res.status_code == 200
        resp3 = client.get("/api/dynasty-office")
        matched = next(
            p for p in resp3.json()["recruiting"]["prospects"]
            if p["player_id"] == prospect_id
        )
        assert matched["recruiting_status"] == "VISITED"
    finally:
        app.dependency_overrides.clear()


def test_actions_survive_connection_close_and_reopen(tmp_path):
    """Persistence-across-reload guard: action flags must be on disk, not just
    in process memory.
    """
    db_path = tmp_path / "career.db"
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _bootstrap_career(conn)

    def override_db():
        # Each request gets a fresh connection backed by the same file
        c = sqlite3.connect(db_path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.get("/api/dynasty-office")
        prospect_id = resp.json()["recruiting"]["prospects"][0]["player_id"]

        res = client.post(f"/api/recruiting/contact/{prospect_id}")
        assert res.status_code == 200
    finally:
        app.dependency_overrides.clear()
        conn.close()

    # Reopen a fresh connection (simulates app restart / page reload)
    conn2 = sqlite3.connect(db_path, check_same_thread=False)
    conn2.row_factory = sqlite3.Row

    def override_db2():
        yield conn2

    app.dependency_overrides[get_db] = override_db2
    try:
        client = TestClient(app)
        resp = client.get("/api/dynasty-office")
        matched = next(
            p for p in resp.json()["recruiting"]["prospects"]
            if p["player_id"] == prospect_id
        )
        assert matched["recruiting_status"] == "CONTACTED"
        assert matched["contacted"] is True

        # Spot-check the raw persisted JSON column as a tighter assertion
        row = conn2.execute(
            "SELECT value FROM dynasty_state WHERE key = 'prospect_recruitment_actions_json'"
        ).fetchone()
        assert row is not None
        stored = json.loads(row[0])
        assert stored[prospect_id]["contacted"] is True
    finally:
        app.dependency_overrides.clear()
        conn2.close()
