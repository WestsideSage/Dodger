"""V26 The Crowd — bench roles.

One role per non-starter, per season (no weekly micro), persisted in
``dynasty_state``. Three roles, each with a measurable, receipted effect:

- **Mentor** — extra practice growth for paired youngsters, scaled by the
  mentor's identity traits (their first honest consumer).
- **Analyst** — a targeting-read bonus added to the user's match preps, scaled
  by his ``tactical_iq``.
- **Ambassador** — monetizes his personal following into extra fan income.

User-program only (AI clubs are abstracted, like the rest of the V26 economy).
"""
from __future__ import annotations

import json
from typing import Dict, Optional

from .config import DEFAULT_BENCH_ROLES, BenchRoleConfig

_ROLES_KEY = "v26_bench_roles_json"
VALID_ROLES = ("mentor", "analyst", "ambassador")


def assigned_roles(conn) -> Dict[str, str]:
    """{player_id: role} for the user club."""
    from .persistence import get_state

    raw = get_state(conn, _ROLES_KEY)
    try:
        roles = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        roles = {}
    return {k: v for k, v in roles.items() if v in VALID_ROLES}


def _player_with_role(conn, role: str):
    """Return the user-club Player holding ``role``, or None."""
    from .persistence import get_state, load_club_roster

    user = get_state(conn, "player_club_id")
    if not user:
        return None
    holder = next((pid for pid, r in assigned_roles(conn).items() if r == role), None)
    if holder is None:
        return None
    try:
        roster = {p.id: p for p in load_club_roster(conn, user)}
    except KeyError:
        return None
    return roster.get(holder)


def _is_non_starter(conn, player_id: str) -> bool:
    from .lineup import STARTERS_COUNT
    from .persistence import get_state, load_lineup_default

    user = get_state(conn, "player_club_id")
    if not user:
        return False
    order = load_lineup_default(conn, user) or []
    return player_id in order[STARTERS_COUNT:]


def assign_role(conn, player_id: str, role: Optional[str]) -> Dict[str, str]:
    """Assign (or clear, with role None/'none') a bench role. Only a non-starter
    may hold a role; one role per player; a role is unique to one player."""
    from .persistence import set_state

    roles = assigned_roles(conn)
    if not role or role == "none":
        roles.pop(player_id, None)
    else:
        if role not in VALID_ROLES:
            raise ValueError(f"Unknown bench role: {role}")
        if not _is_non_starter(conn, player_id):
            raise ValueError("Only a non-starter can hold a bench role.")
        # A role belongs to one player at a time.
        roles = {pid: r for pid, r in roles.items() if r != role}
        roles[player_id] = role
    set_state(conn, _ROLES_KEY, json.dumps(roles))
    conn.commit()
    return roles


def _mentor_quality(mentor) -> float:
    """0-1 blend of the mentor's four identity traits (the dead-trait consumer)."""
    r = mentor.ratings
    traits = (r.tactical_iq, r.catch_courage, r.throw_selection_iq, r.conditioning_curve)
    return max(0.0, min(1.0, (sum(traits) / len(traits)) / 100.0))


def mentor_dev_bonus_for(conn, player, config: BenchRoleConfig = DEFAULT_BENCH_ROLES) -> float:
    """Extra practice-growth OVR for a youngster when a Mentor is assigned,
    scaled by the mentor's identity traits. 0 for non-youngsters / no mentor."""
    if player.age > config.mentor_youth_age_max:
        return 0.0
    mentor = _player_with_role(conn, "mentor")
    if mentor is None or mentor.id == player.id:
        return 0.0
    return round(config.mentor_base_dev_ovr * _mentor_quality(mentor), 3)


def analyst_targeting_bonus(conn, config: BenchRoleConfig = DEFAULT_BENCH_ROLES) -> float:
    """Targeting-read bonus the assigned Analyst adds to the user's preps,
    scaled by his tactical_iq. 0 when no Analyst is assigned."""
    analyst = _player_with_role(conn, "analyst")
    if analyst is None:
        return 0.0
    return round(config.analyst_base_targeting * (analyst.ratings.tactical_iq / 100.0), 3)


def ambassador_income_k(conn, config: BenchRoleConfig = DEFAULT_BENCH_ROLES) -> int:
    """Extra fan income from the assigned Ambassador's personal following."""
    from . import fan_ledger

    ambassador = _player_with_role(conn, "ambassador")
    if ambassador is None:
        return 0
    followers = fan_ledger.player_followers(conn, ambassador.id)
    return round(followers / 1000.0 * config.ambassador_income_per_1k_followers_k)


__all__ = [
    "VALID_ROLES",
    "assigned_roles",
    "assign_role",
    "mentor_dev_bonus_for",
    "analyst_targeting_bonus",
    "ambassador_income_k",
]
