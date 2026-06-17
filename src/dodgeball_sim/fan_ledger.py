"""V26 The Crowd — the fan ledger.

Two running totals (``club_fans`` / ``player_fans``) backed by an append-only
receipt log (``fan_ledger``). This is the single mutation home: never bump a
total without writing a receipt row that says how it was earned (no opaque
scalar — the spec explicitly rejects the prestige pattern).
"""
from __future__ import annotations

from typing import Any, List, Optional


def club_fans(conn, club_id: str) -> int:
    row = conn.execute(
        "SELECT fans_count FROM club_fans WHERE club_id = ?", (club_id,)
    ).fetchone()
    return int(row["fans_count"]) if row else 0


def player_followers(conn, player_id: str) -> int:
    row = conn.execute(
        "SELECT followers_count FROM player_fans WHERE player_id = ?", (player_id,)
    ).fetchone()
    return int(row["followers_count"]) if row else 0


def add_fans(
    conn, club_id: str, delta: int, season_id: str, event_type: str, receipt: str
) -> int:
    """Bump a club's fan count and append the receipt. Returns the running total."""
    delta = int(delta)
    total = club_fans(conn, club_id) + delta
    conn.execute(
        "INSERT OR REPLACE INTO club_fans (club_id, fans_count) VALUES (?, ?)",
        (club_id, total),
    )
    _append_receipt(conn, club_id, "club", season_id, event_type, delta, total, receipt)
    return total


def add_followers(
    conn, player_id: str, delta: int, season_id: str, event_type: str, receipt: str
) -> int:
    """Bump a player's follower count and append the receipt."""
    delta = int(delta)
    total = player_followers(conn, player_id) + delta
    conn.execute(
        "INSERT OR REPLACE INTO player_fans (player_id, followers_count) VALUES (?, ?)",
        (player_id, total),
    )
    _append_receipt(conn, player_id, "player", season_id, event_type, delta, total, receipt)
    return total


def _append_receipt(conn, entity_id, entity_type, season_id, event_type, delta, total, receipt) -> None:
    conn.execute(
        "INSERT INTO fan_ledger "
        "(entity_id, entity_type, season_id, event_type, delta, running_total, receipt) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (entity_id, entity_type, season_id, event_type, int(delta), int(total), receipt),
    )


def load_fan_receipts(
    conn,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    season_id: Optional[str] = None,
) -> List[dict[str, Any]]:
    query = (
        "SELECT entity_id, entity_type, season_id, event_type, delta, running_total, receipt "
        "FROM fan_ledger"
    )
    clauses: list[str] = []
    params: list[Any] = []
    if entity_type:
        clauses.append("entity_type = ?"); params.append(entity_type)
    if entity_id:
        clauses.append("entity_id = ?"); params.append(entity_id)
    if season_id:
        clauses.append("season_id = ?"); params.append(season_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY ledger_id"
    return [dict(row) for row in conn.execute(query, params).fetchall()]


__all__ = [
    "club_fans",
    "player_followers",
    "add_fans",
    "add_followers",
    "load_fan_receipts",
]
