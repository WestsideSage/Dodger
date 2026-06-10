"""Serialization guard: /api/command-center carries the career's ruleset.

The Policy Editor uses ``ruleset_selection`` to disclose that the official
engine does not enforce opening-rush behavior (WT-20 open) — without it the
two rush knobs read as outcome-affecting on official careers, where they are
announced-only.

This is a serialization-layer guard on purpose: the 2026-06-09 UX pass found
``MatchReplayResponse`` silently stripping undeclared fields at the FastAPI
boundary (every official replay rendered a legacy scoreline). Asserting on the
HTTP response (not the payload dict) pins the declared-model contract.
"""

import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema


def _client_for_career(ruleset_selection: str | None) -> tuple[TestClient, sqlite3.Connection]:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", root_seed=20260426, ruleset_selection=ruleset_selection
    )
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    return TestClient(server.app), conn


def test_command_center_serializes_official_ruleset_selection():
    client, _conn = _client_for_career("official_foam")
    try:
        payload = client.get("/api/command-center").json()
        assert payload["ruleset_selection"] == "official_foam"
    finally:
        server.app.dependency_overrides.clear()


def test_command_center_ruleset_selection_none_for_generic_career():
    client, _conn = _client_for_career(None)
    try:
        payload = client.get("/api/command-center").json()
        # Key must be PRESENT (not stripped) and honestly None for legacy
        # generic careers, so the frontend can branch on it without guessing.
        assert "ruleset_selection" in payload
        assert payload["ruleset_selection"] is None
    finally:
        server.app.dependency_overrides.clear()
