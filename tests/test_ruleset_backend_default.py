"""WT-17: new careers default to ``official_foam`` at the backend boundary.

The frontend always defaults a new career to the official foam ruleset, but the
backend request models defaulted ``ruleset_selection`` to ``None`` — so an
API/automation-created career (a ``POST /api/saves/new`` body that omits the
field, or any non-UI caller) silently fell back to the generic engine. The fix
flips the default to ``official_foam`` at the *entry points* (the request models
and the web bootstrap), while still honoring an explicit ``"generic"``/``None``
for legacy/opt-out callers and never migrating or re-initializing existing saves.

These tests cover:

* the request-model defaults themselves (the crux of the flip);
* an end-to-end ``POST /api/saves/new`` that omits the field -> persisted
  ``official_foam``;
* an explicit ``"generic"`` opt-out -> persisted/read ``generic``; and
* a legacy on-disk save that has no ruleset row -> still reads ``generic``
  (no migration, no breakage).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_setup import (
    ensure_default_web_career,
    initialize_curated_manager_career,
)
from dodgeball_sim.persistence import connect, create_schema, get_state
from dodgeball_sim.server import BuildFromScratchRequest, NewSaveRequest


def test_new_save_request_model_defaults_to_official_foam():
    """The default applies only when the field is absent."""
    assert NewSaveRequest(name="My Career").ruleset_selection == "official_foam"


def test_build_from_scratch_request_model_defaults_to_official_foam():
    request = BuildFromScratchRequest(
        save_name="Scratch",
        club_name="Test FC",
        city="Townsville",
        colors="#111111/#222222",
        coach_name="Coach",
        coach_backstory="Backstory",
        roster_player_ids=["p1", "p2", "p3", "p4", "p5", "p6"],
    )
    assert request.ruleset_selection == "official_foam"


def test_explicit_generic_is_honored_by_request_model():
    """A caller can still opt out to generic explicitly."""
    assert NewSaveRequest(name="Legacy", ruleset_selection="generic").ruleset_selection == "generic"


def test_explicit_none_is_honored_by_request_model():
    assert NewSaveRequest(name="Legacy", ruleset_selection=None).ruleset_selection is None


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    saves_dir.mkdir()
    monkeypatch.setattr(server, "SAVES_DIR", saves_dir)
    monkeypatch.setattr(server, "DEFAULT_DB_PATH", tmp_path / "dodgeball_sim.db")
    monkeypatch.setattr(server, "_active_save_path", None)
    return saves_dir


def _read_persisted_ruleset(db_path: Path) -> str | None:
    conn = connect(db_path)
    try:
        return get_state(conn, "ruleset_selection")
    finally:
        conn.close()


def test_api_created_career_defaults_to_official_foam(sandbox):
    """POST /api/saves/new omitting ruleset_selection persists official_foam."""
    client = TestClient(server.app)
    response = client.post("/api/saves/new", json={"name": "Auto Career", "club_id": "aurora"})
    assert response.status_code == 200
    created = Path(response.json()["path"])
    assert _read_persisted_ruleset(created) == "official_foam"


def test_api_created_career_honors_explicit_generic(sandbox):
    """An explicit generic opt-out is persisted and reads as generic."""
    client = TestClient(server.app)
    response = client.post(
        "/api/saves/new",
        json={"name": "Generic Career", "club_id": "aurora", "ruleset_selection": "generic"},
    )
    assert response.status_code == 200
    created = Path(response.json()["path"])
    assert _read_persisted_ruleset(created) == "generic"


def test_legacy_save_without_ruleset_row_still_reads_generic(tmp_path):
    """A pre-existing save (bare primitive, no ruleset) is untouched -> generic.

    This is the legacy-honoring contract: existing on-disk saves never get a
    ruleset row written behind their back, so ``get_state`` returns None and the
    runtime treats the career as generic exactly as before.
    """
    legacy_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(legacy_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        create_schema(conn)
        # No ruleset_selection passed -> the primitive persists nothing.
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
        conn.commit()
    finally:
        conn.close()
    assert _read_persisted_ruleset(legacy_path) is None


def test_web_bootstrap_defaults_to_official_foam(tmp_path):
    """ensure_default_web_career mints a brand-new career as official_foam."""
    db_path = tmp_path / "bootstrap.db"
    conn = connect(db_path)
    try:
        ensure_default_web_career(conn, selected_club_id="aurora", root_seed=20260426)
        conn.commit()
    finally:
        conn.close()
    assert _read_persisted_ruleset(db_path) == "official_foam"
