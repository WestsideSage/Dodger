"""V27 The Calendar — Phase 1: the event-result model + idempotent purses +
the per-season event store + event journalism.

Per docs/specs/2026-06-17-v27-the-calendar-spec.md (Phase 1). Events are
PYRAMID-WORLD features (legacy single-league saves are byte-identical — no
events, no purses, no beat). Purses credit the user treasury through an
idempotent per-event guard (the ``FINANCES_APPLIED_KEY`` pattern —
``set_treasury_k`` has no guard of its own, so a double-call must never
double-pay). Event journalism reuses ``news_headlines`` with category
``event_news`` (surfaced by the widened ``build_news_payload`` filter).

Effects are isolated to treasury/fans/prestige/credibility — NEVER match
outcomes, standings, or development (the V26 isolation invariant).

This module is named ``event_calendar`` (not ``events``) to avoid colliding
with the existing engine ``events`` module (``MatchEvent``).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from typing import List, Mapping, Optional, Tuple


# dynasty_state keys. The per-event purse guard is namespaced per event_key so
# two events in the same season each pay once (never reuse finances_applied_for).
_EVENTS_STORE_KEY = "v27_events_json"


def _purse_guard_key(event_key: str) -> str:
    return f"v27_{event_key}_purse_for"


@dataclass(frozen=True)
class EventBracketRow:
    """One row of an event's knockout bracket (a single resolved matchup)."""

    round: str
    home_club_id: str
    away_club_id: str
    winner_club_id: str
    home_club_name: str = ""
    away_club_name: str = ""


@dataclass(frozen=True)
class EventResult:
    """A resolved event: its champion, purse, ruleset, and bracket rows.

    Stored as one entry in the per-season ``v27_events_json`` list. Frozen so a
    result is never mutated in place after being recorded.
    """

    event_key: str
    event_name: str
    season_id: str
    champion_club_id: str
    champion_club_name: str
    ruleset: str
    purse_k: int
    bracket: Tuple[EventBracketRow, ...] = field(default_factory=tuple)
    # Optional per-event metadata (e.g. the MSI Worlds-seeding marker). Additive:
    # empty by default so legacy/other events serialize unchanged.
    meta: Mapping[str, object] = field(default_factory=dict)


def apply_event_purse(
    conn: sqlite3.Connection,
    event_key: str,
    purse_k: int,
    season_id: str,
) -> Optional[dict]:
    """Credit the user club's treasury with an event purse, ONCE per season.

    Idempotent via a per-event guard (``v27_<event>_purse_for`` holding
    ``season_id``), mirroring ``economy.apply_season_finances``'s
    ``FINANCES_APPLIED_KEY`` pattern — ``set_treasury_k`` has no guard of its
    own, so without this a double-call would double-pay. Returns the receipt
    ledger, or the existing one when already applied. Pyramid-only: the caller
    gates on ``player_club_id`` + ``pyramid_world_active``; this helper credits
    whatever treasury exists (the user club's).
    """
    from .economy import set_treasury_k, treasury_k
    from .persistence import get_state, set_state

    guard = _purse_guard_key(event_key)
    if get_state(conn, guard) == season_id:
        # Already applied this season — return the prior receipt (no re-pay).
        raw = get_state(conn, f"v27_{event_key}_purse_json")
        return json.loads(raw) if raw else None

    amount = int(purse_k)
    opening = treasury_k(conn)
    closing = opening + amount
    set_treasury_k(conn, closing)
    set_state(conn, f"v27_{event_key}_purse_json", json.dumps({
        "event_key": event_key,
        "season_id": season_id,
        "purse_k": amount,
        "opening_treasury_k": opening,
        "closing_treasury_k": closing,
    }))
    set_state(conn, guard, season_id)
    conn.commit()
    return {
        "event_key": event_key,
        "season_id": season_id,
        "purse_k": amount,
        "opening_treasury_k": opening,
        "closing_treasury_k": closing,
    }


def _event_to_dict(result: EventResult) -> dict:
    return {
        "event_key": result.event_key,
        "event_name": result.event_name,
        "season_id": result.season_id,
        "champion_club_id": result.champion_club_id,
        "champion_club_name": result.champion_club_name,
        "ruleset": result.ruleset,
        "purse_k": int(result.purse_k),
        "bracket": [asdict(row) for row in result.bracket],
        "meta": dict(result.meta),
    }


def record_event(
    conn: sqlite3.Connection, season_id: str, result: EventResult
) -> None:
    """Append one event result to the per-season ``v27_events_json`` store.

    Append-only within a season (recording the cup, then an invitational, then
    MSI appends each). Idempotent on event_key within the season: re-recording
    the same event replaces its row rather than duplicating (an event resolves
    exactly once per season).
    """
    from .persistence import get_state, set_state

    raw = get_state(conn, _EVENTS_STORE_KEY)
    try:
        rows = json.loads(raw) if raw else []
        if not isinstance(rows, list):
            rows = []
    except (TypeError, ValueError):
        rows = []
    payload = _event_to_dict(result)
    # Replace any existing row for this event_key this season (idempotent record).
    rows = [r for r in rows if r.get("event_key") != result.event_key]
    rows.append(payload)
    set_state(conn, _EVENTS_STORE_KEY, json.dumps(rows))
    conn.commit()


def load_events(conn: sqlite3.Connection, season_id: str) -> List[dict]:
    """Return the event results recorded for this season (empty list if none)."""
    from .persistence import get_state

    raw = get_state(conn, _EVENTS_STORE_KEY)
    if not raw:
        return []
    try:
        rows = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(rows, list):
        return []
    # The store is per-season; filter defensively by season_id.
    return [r for r in rows if r.get("season_id") == season_id]


def emit_event_news(
    conn: sqlite3.Connection, season_id: str, result: EventResult
) -> None:
    """Write an ``event_news`` headline for a resolved event (idempotent).

    Reuses ``news_headlines`` with category ``event_news`` (surfaced by the
    widened ``build_news_payload`` filter). Idempotent on headline_id so a
    re-emit never duplicates.
    """
    from .persistence import save_news_headlines

    headline_id = f"event_{result.event_key}_{season_id}"
    text = f"{result.champion_club_name} win the {result.event_name}!"
    save_news_headlines(conn, season_id, 0, [{
        "headline_id": headline_id,
        "category": "event_news",
        "headline_text": text,
        "entity_ids": [result.champion_club_id],
    }])


__all__ = [
    "EventBracketRow",
    "EventResult",
    "apply_event_purse",
    "record_event",
    "load_events",
    "emit_event_news",
]
