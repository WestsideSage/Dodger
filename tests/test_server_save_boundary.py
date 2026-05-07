"""Save boundary regression tests covering the chaos report 2026-05-07 findings.

The web `saves/load` and `saves/delete` endpoints used to accept any existing
filesystem path. The fixes in `server._resolve_managed_save_path` and
`server._looks_like_dodgeball_save` constrain those endpoints to managed save
files under `SAVES_DIR` plus the legacy `DEFAULT_DB_PATH` for load.

These tests construct a temporary `SAVES_DIR` and `DEFAULT_DB_PATH` so that no
real save file is touched.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema


def _make_real_save(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Redirect SAVES_DIR/DEFAULT_DB_PATH at the temp dir for each test."""
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    legacy = tmp_path / "dodgeball_sim.db"
    monkeypatch.setattr(server, "SAVES_DIR", saves_dir)
    monkeypatch.setattr(server, "DEFAULT_DB_PATH", legacy)
    monkeypatch.setattr(server, "_active_save_path", None)
    yield {"root": tmp_path, "saves": saves_dir, "legacy": legacy}
    monkeypatch.setattr(server, "_active_save_path", None)


def test_load_save_rejects_arbitrary_existing_file(sandbox):
    """Chaos report fix: a non-`.db` path must not be accepted as a save."""
    intruder = sandbox["root"] / "sentinel-not-a-save.txt"
    intruder.write_text("not a save", encoding="utf-8")

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/load", json={"path": str(intruder)})

    assert response.status_code in (400, 403)
    assert server._active_save_path is None

    status = client.get("/api/status")
    assert status.status_code == 503


def test_load_save_rejects_db_outside_managed_directory(sandbox):
    """A real .db file outside SAVES_DIR is still not a managed save."""
    rogue = sandbox["root"] / "rogue.db"
    _make_real_save(rogue)

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/load", json={"path": str(rogue)})

    assert response.status_code == 403
    assert server._active_save_path is None


def test_load_save_accepts_managed_save_and_swaps_active_path(sandbox):
    managed = sandbox["saves"] / "Demo.db"
    _make_real_save(managed)

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/load", json={"path": str(managed)})

    assert response.status_code == 200
    assert server._active_save_path is not None
    assert server._active_save_path.resolve() == managed.resolve()

    status = client.get("/api/status")
    assert status.status_code == 200


def test_load_save_accepts_legacy_db_path(sandbox):
    """The legacy DEFAULT_DB_PATH stays loadable for backwards compatibility."""
    _make_real_save(sandbox["legacy"])

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/load", json={"path": str(sandbox["legacy"])})

    assert response.status_code == 200
    assert server._active_save_path.resolve() == sandbox["legacy"].resolve()


def test_load_save_rejects_save_that_lacks_schema_row(sandbox):
    """A `.db` file under SAVES_DIR that is not a real save must not load."""
    fake = sandbox["saves"] / "Fake.db"
    conn = sqlite3.connect(str(fake), check_same_thread=False)
    conn.execute("CREATE TABLE noise (id INTEGER)")
    conn.commit()
    conn.close()

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/load", json={"path": str(fake)})

    assert response.status_code == 400
    assert server._active_save_path is None


def test_delete_save_refuses_arbitrary_existing_file(sandbox):
    """Chaos report blocker: deletion must be confined to managed saves."""
    victim = sandbox["root"] / "delete-victim.txt"
    victim.write_text("hands off", encoding="utf-8")

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/delete", json={"path": str(victim)})

    assert response.status_code in (400, 403)
    assert victim.exists(), "Path-traversal targets must not be deleted"


def test_delete_save_refuses_legacy_db(sandbox):
    _make_real_save(sandbox["legacy"])

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/delete", json={"path": str(sandbox["legacy"])})

    assert response.status_code == 403
    assert sandbox["legacy"].exists()


def test_delete_save_removes_managed_save_only(sandbox):
    managed = sandbox["saves"] / "ToRemove.db"
    _make_real_save(managed)

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/delete", json={"path": str(managed)})

    assert response.status_code == 200
    assert not managed.exists()


def test_delete_save_clears_active_pointer_when_active_is_removed(sandbox):
    managed = sandbox["saves"] / "Active.db"
    _make_real_save(managed)
    server._active_save_path = managed

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.post("/api/saves/delete", json={"path": str(managed)})

    assert response.status_code == 200
    assert server._active_save_path is None


def test_dynasty_office_corrupt_state_returns_409_not_500(sandbox):
    """Chaos report fix: CorruptSaveError must surface as 409 with detail."""
    managed = sandbox["saves"] / "Corrupt.db"
    _make_real_save(managed)
    server._active_save_path = managed

    conn = sqlite3.connect(str(managed))
    conn.execute(
        "INSERT OR REPLACE INTO dynasty_state (key, value) VALUES (?, ?)",
        ("program_promises_json", "NOT JSON {{{"),
    )
    conn.commit()
    conn.close()

    client = TestClient(server.app, raise_server_exceptions=False)
    response = client.get("/api/dynasty-office")

    assert response.status_code == 409
    assert "Corrupted" in response.json()["detail"] or "corrupt" in response.json()["detail"].lower()


def test_resolve_managed_save_path_rejects_traversal(sandbox):
    """`..` segments must not let the client escape SAVES_DIR."""
    from fastapi import HTTPException

    target = sandbox["root"] / "outside.db"
    _make_real_save(target)
    traversal = sandbox["saves"] / ".." / "outside.db"

    with pytest.raises(HTTPException) as exc:
        server._resolve_managed_save_path(str(traversal), allow_legacy=False)

    assert exc.value.status_code in (400, 403)
