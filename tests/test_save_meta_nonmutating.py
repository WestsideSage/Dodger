"""WT-15: listing a save (read_save_meta) must be STRICTLY non-mutating.

Merely listing saves must never trigger a schema migration or write a single
byte to the save ``.db``. Migration happens only on an explicit resume/load
through the backed-up path. These tests pin two properties:

1. An older-schema save read via ``read_save_meta`` keeps its ``schema_version``
   and the save ``.db`` is byte-for-byte unchanged (mode=ro guards the database
   file; SQLite may create empty -wal/-shm sidecars on open, never touching the
   save's data).
2. A real, current save created through ``connect()`` (which puts the file in
   WAL mode) still reads its metadata correctly and is NOT silently reported as
   ``incompatible`` -- guarding against a read-only-open regression that the
   metadata reader's broad ``except`` would otherwise hide.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    CURRENT_SCHEMA_VERSION,
    _migrate_v1,
    connect,
    get_schema_version,
    migrate_schema,
)
from dodgeball_sim.save_service import read_save_meta


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _schema_version_of(path: Path) -> int:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        return get_schema_version(conn)
    finally:
        conn.close()


def test_read_save_meta_does_not_migrate_older_schema_save(tmp_path):
    """An older-schema save must keep its schema_version after a meta read."""
    older_version = CURRENT_SCHEMA_VERSION - 1
    assert older_version >= 1

    path = tmp_path / "older.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _migrate_v1(conn)
    migrate_schema(conn, 1, older_version)
    conn.commit()
    conn.close()

    assert _schema_version_of(path) == older_version

    read_save_meta(path)

    assert _schema_version_of(path) == older_version, (
        "read_save_meta migrated an older save just by listing it"
    )


def test_read_save_meta_does_not_change_any_bytes_of_older_save(tmp_path):
    """The strongest form of WT-15: not one byte of the save ``.db`` file may change."""
    older_version = CURRENT_SCHEMA_VERSION - 1
    path = tmp_path / "older_bytes.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _migrate_v1(conn)
    migrate_schema(conn, 1, older_version)
    conn.commit()
    conn.close()

    before = _sha256(path)
    read_save_meta(path)
    after = _sha256(path)

    assert before == after, "read_save_meta mutated the save file on a metadata read"


def test_read_save_meta_reads_real_wal_save_without_false_incompatible(tmp_path):
    """Regression guard: a real save (WAL mode, via connect()) must read its
    metadata. A failed read-only open would be swallowed and reported as
    ``incompatible=True``, hiding the breakage behind the broad except."""
    path = tmp_path / "real_wal.db"
    conn = connect(path)  # connect() forces PRAGMA journal_mode=WAL
    try:
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
        conn.commit()
    finally:
        conn.close()

    meta = read_save_meta(path)

    assert meta["incompatible"] is False
    assert meta["club_id"] == "aurora"
    assert meta["club_name"]


def test_read_save_meta_does_not_change_bytes_of_real_wal_save(tmp_path):
    """Listing a current, WAL-mode save must also leave it byte-for-byte intact."""
    path = tmp_path / "real_wal_bytes.db"
    conn = connect(path)
    try:
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
        conn.commit()
    finally:
        conn.close()

    before = _sha256(path)
    read_save_meta(path)
    after = _sha256(path)

    assert before == after
