from __future__ import annotations

import dataclasses
import sqlite3
from typing import Any

from .career_state import CareerState, advance as state_advance
from .offseason_ceremony import (
    begin_next_season,
    finalize_season,
    initialize_manager_offseason,
    sign_best_rookie,
    stored_root_seed,
)
from .offseason_presentation import build_beat_response, load_active_beats
from .persistence import (
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_season,
    save_career_state_cursor,
)
from .web_status_service import career_state_payload


OFFSEASON_STATES = {
    CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
    CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
    CareerState.NEXT_SEASON_READY,
}


class OffseasonError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def get_offseason_beat_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = _require_offseason_cursor(conn)
    season_id = get_state(conn, "active_season_id")
    if season_id:
        season = load_season(conn, season_id)
        if season:
            clubs = load_clubs(conn)
            rosters = load_all_rosters(conn)
            finalize_season(conn, season, rosters)
            root_seed = stored_root_seed(conn)
            initialize_manager_offseason(conn, season, clubs, rosters, root_seed)
    return build_beat_response(conn, cursor)


def advance_offseason_beat_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = _require_offseason_cursor(conn)
    active_beats = load_active_beats(conn)
    beat_index = max(0, min(int(cursor.offseason_beat_index or 0), len(active_beats) - 1))
    current_key = active_beats[beat_index]

    if current_key == "schedule_reveal":
        raise OffseasonError(
            "Already at the final beat. Use begin-season to start next season.",
            status_code=409,
        )
    if (
        cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
        and current_key == "recruitment"
    ):
        raise OffseasonError(
            "Cannot advance past recruitment without signing. Use /api/offseason/recruit first.",
            status_code=409,
        )

    next_index = beat_index + 1
    next_key = active_beats[next_index]
    if next_key == "recruitment":
        cursor = state_advance(
            cursor,
            CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            offseason_beat_index=next_index,
        )
    else:
        cursor = dataclasses.replace(cursor, offseason_beat_index=next_index)

    save_career_state_cursor(conn, cursor)
    conn.commit()
    return build_beat_response(conn, cursor)


def recruit_offseason_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING:
        raise OffseasonError(
            f"Not in recruitment state (current: {cursor.state.value})", status_code=409
        )
    signed_player_id = get_state(conn, "offseason_draft_signed_player_id") or ""
    if signed_player_id:
        raise OffseasonError("Already recruited a player this offseason.", status_code=409)
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise OffseasonError("No player club assigned")

    signed = sign_best_rookie(conn, player_club_id, cursor.season_number or 1)

    active_beats = load_active_beats(conn)
    recruitment_index = active_beats.index("recruitment")
    cursor = state_advance(
        cursor,
        CareerState.NEXT_SEASON_READY,
        offseason_beat_index=recruitment_index,
    )
    save_career_state_cursor(conn, cursor)
    conn.commit()
    return {
        **build_beat_response(conn, cursor),
        "signed_player": (
            {
                "id": signed.id,
                "name": signed.name,
                "overall": round(signed.overall(), 1),
                "age": signed.age,
            }
            if signed
            else None
        ),
    }


def begin_next_season_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.NEXT_SEASON_READY:
        raise OffseasonError(f"Not ready to begin next season (current: {cursor.state.value})", status_code=409)
    new_cursor = begin_next_season(conn, cursor, load_clubs(conn))
    return {"status": "success", "state": career_state_payload(new_cursor)}


def _require_offseason_cursor(conn: sqlite3.Connection):
    cursor = load_career_state_cursor(conn)
    if cursor.state not in OFFSEASON_STATES:
        raise OffseasonError(f"Not in an offseason state (current: {cursor.state.value})", status_code=409)
    return cursor
