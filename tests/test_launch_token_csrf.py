"""WT-12: per-process launch-token CSRF defense for the local server.

These tests flip ``server._enforce_launch_token`` ON inside their own bodies
(the autouse fixture in ``conftest.py`` keeps it OFF for the rest of the suite).
They prove both halves of the contract:

* a mutating ``/api`` request with a missing or forged token is rejected with
  403 *before* the route body runs (so nothing is mutated); and
* the same request with the valid per-process token is allowed through to the
  normal route handler.

They also confirm GETs are never gated and that the token is discoverable via
``GET /api/launch-token`` (the dev-mode delivery the SPA falls back to).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

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


@contextmanager
def _enforced_client():
    """A TestClient with token enforcement ON and a live in-memory career."""
    conn = _career_conn()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    server.enable_launch_token_guard(True)
    try:
        yield TestClient(server.app)
    finally:
        server.enable_launch_token_guard(False)
        server.app.dependency_overrides.clear()


_VALID_TACTICS = {
    "approach": "aggressive",
    "target_focus": "ball_holders",
    "catch_posture": "go_for_catches",
    "rush_commit": "all_in",
    "rush_target": "strongest_side",
}


def test_mutating_post_without_token_is_rejected():
    """A drive-by POST with no launch token must be blocked with 403."""
    with _enforced_client() as client:
        response = client.post("/api/tactics", json=_VALID_TACTICS)
    assert response.status_code == 403
    assert "launch token" in response.json()["detail"].lower()


def test_mutating_post_with_forged_token_is_rejected():
    """A POST carrying the wrong token is also blocked with 403."""
    with _enforced_client() as client:
        response = client.post(
            "/api/tactics",
            json=_VALID_TACTICS,
            headers={server.LAUNCH_TOKEN_HEADER: "not-the-real-token"},
        )
    assert response.status_code == 403


def test_mutating_post_with_valid_token_is_allowed():
    """The same POST with the valid per-process token reaches the handler."""
    with _enforced_client() as client:
        response = client.post(
            "/api/tactics",
            json=_VALID_TACTICS,
            headers={server.LAUNCH_TOKEN_HEADER: server.LAUNCH_TOKEN},
        )
    # 200 (persisted) — crucially NOT 403, proving the guard let it through.
    assert response.status_code == 200
    assert response.status_code != 403


def test_unload_post_without_token_is_rejected():
    """The unload route (a real CSRF target) is gated like every mutating route."""
    with _enforced_client() as client:
        response = client.post("/api/saves/unload")
    assert response.status_code == 403


def test_get_requests_are_never_gated():
    """Read-only GETs must work without any token even when enforcement is on."""
    with _enforced_client() as client:
        status = client.get("/api/status")
        token = client.get("/api/launch-token")
    assert status.status_code == 200
    assert token.status_code == 200
    assert token.json()["token"] == server.LAUNCH_TOKEN


def test_module_default_enables_enforcement_for_production():
    """The module ships with enforcement ON so a launched server is protected.

    Verified in a fresh subprocess so the pytest autouse fixture (which disables
    enforcement for the rest of the suite) does not mask the real import-time
    default. A False here would mean the CSRF defense is dormant in production.
    """
    import os
    import subprocess
    import sys

    repo_root = Path(server.__file__).resolve().parent.parent.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(repo_root / "src"), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", "import dodgeball_sim.server as s; print(s._enforce_launch_token)"],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


def test_conftest_disables_enforcement_for_in_process_clients():
    """With the autouse fixture active (enforcement OFF), posts are not blocked.

    This is what keeps the ~22 existing TestClient files green without per-file
    token churn — the suite default is OFF via conftest, not via the module.
    """
    conn = _career_conn()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        response = client.post("/api/tactics", json=_VALID_TACTICS)
    finally:
        server.app.dependency_overrides.clear()
    assert response.status_code == 200
