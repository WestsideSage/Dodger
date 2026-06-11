"""User roster moves — releasing a contracted player to free agency.

Playtest 3 F-8: at a full 12/12 roster the Signing Day went read-only and no
release/cut control existed anywhere, so a successful young core froze the
roster for the rest of the dynasty (one contention window, then permanent
last place while the league developed past it). The release move is the
"refresh" half of the dynasty loop:

* the released player joins the existing free-agent pool (rivals can sign
  them later — releases are real, not deletions);
* the user's lineup default is repaired the same way a retirement repairs it;
* the current week's saved command plan drops the player so a planned six
  never fields someone who is no longer contracted;
* an OPEN promise to the released player BREAKS immediately — cutting someone
  you promised development or playing time is a promise broken by your own
  hand, with the usual credibility cost (a void would be dishonest here).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from typing import Any, Optional

from .lineup import STARTERS_COUNT
from .persistence import (
    add_free_agent,
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_json_state,
    load_lineup_default,
    load_weekly_command_plan,
    save_club,
    save_lineup_default,
    save_weekly_command_plan,
    set_state,
)
from .recruiting_office import PROMISE_STATE_KEY


class RosterMoveError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def release_player_to_free_agency(
    conn: sqlite3.Connection, player_id: str
) -> dict[str, Any]:
    """Release a player from the user's roster into the free-agent pool.

    Returns a fact payload: the released player's line, the new roster size,
    and the broken-promise record when one was open. Raises
    :class:`RosterMoveError` when the move is illegal (unknown player, or the
    roster would drop below the fielded six).
    """
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise RosterMoveError("No player club assigned", status_code=409)

    rosters = load_all_rosters(conn)
    roster = list(rosters.get(player_club_id, []))
    player = next((p for p in roster if p.id == player_id), None)
    if player is None:
        raise RosterMoveError(
            f"Player {player_id} is not on your roster.", status_code=404
        )
    if len(roster) - 1 < STARTERS_COUNT:
        raise RosterMoveError(
            f"Releasing {player.name} would leave {len(roster) - 1} players — "
            f"you need at least {STARTERS_COUNT} to field a legal six.",
            status_code=409,
        )

    next_roster = [p for p in roster if p.id != player_id]
    clubs = load_clubs(conn)
    save_club(conn, clubs[player_club_id], next_roster)

    season_id = get_state(conn, "active_season_id") or "season_1"
    add_free_agent(conn, replace(player, club_id=None), season_id)

    # Lineup default repair: same surviving-order + best-by-role backfill a
    # retirement gets, so the fielded six stays legal without resetting the
    # user's chosen order.
    from .offseason_ceremony import _reconcile_user_lineup_default

    save_lineup_default(
        conn,
        player_club_id,
        _reconcile_user_lineup_default(
            load_lineup_default(conn, player_club_id), next_roster
        ),
    )

    _scrub_current_week_plan_lineup(conn, season_id, player_club_id, player_id)
    broken_promise = _break_open_promise_on_release(conn, season_id, player_id, player.name)

    conn.commit()
    return {
        "released_player": {
            "id": player.id,
            "name": player.name,
            "overall": player.overall_skill(),
            "age": player.age,
        },
        "roster_size": len(next_roster),
        "broken_promise": broken_promise,
    }


def open_promise_player_ids(conn: sqlite3.Connection) -> set[str]:
    """Player ids carrying an OPEN promise — surfaces warn before a release."""
    return {
        str(promise.get("player_id"))
        for promise in load_json_state(conn, PROMISE_STATE_KEY, [])
        if promise.get("status") == "open" and promise.get("player_id")
    }


def _scrub_current_week_plan_lineup(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    player_id: str,
) -> None:
    """Drop the released player from the current week's saved plan lineup.

    The saved plan is applied to the sim as a lineup override; a six that
    names a no-longer-contracted player must not reach the engine.
    """
    cursor = load_career_state_cursor(conn)
    week = cursor.week or 0
    if week <= 0:
        return
    plan = load_weekly_command_plan(conn, season_id, week, player_club_id)
    if not plan:
        return
    lineup = plan.get("lineup") or {}
    player_ids = list(lineup.get("player_ids") or [])
    if player_id not in player_ids:
        return
    lineup = dict(lineup)
    lineup["player_ids"] = [pid for pid in player_ids if pid != player_id]
    lineup["players"] = [
        entry for entry in (lineup.get("players") or []) if entry.get("id") != player_id
    ]
    lineup["summary"] = "Lineup repaired after a roster release."
    plan = dict(plan)
    plan["lineup"] = lineup
    save_weekly_command_plan(conn, plan)


def _break_open_promise_on_release(
    conn: sqlite3.Connection,
    season_id: str,
    player_id: str,
    player_name: str,
) -> Optional[dict[str, Any]]:
    """Break any OPEN promise to the released player, immediately and honestly."""
    promises = list(load_json_state(conn, PROMISE_STATE_KEY, []))
    broken: Optional[dict[str, Any]] = None
    for promise in promises:
        if promise.get("status") != "open" or promise.get("player_id") != player_id:
            continue
        promise["status"] = "broken"
        promise["result"] = "broken"
        promise["result_season_id"] = season_id
        promise["evidence"] = (
            f"Broken — you released {player_name} from the roster with this "
            "promise still open."
        )
        broken = dict(promise)
    if broken is not None:
        set_state(conn, PROMISE_STATE_KEY, json.dumps(promises))
    return broken


__all__ = [
    "RosterMoveError",
    "open_promise_player_ids",
    "release_player_to_free_agency",
]
