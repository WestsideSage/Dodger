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
    sign_chosen_rookie,
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
    set_state,
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

    # When already in RECRUITMENT_PENDING and advancing past recruitment beat,
    # transition to NEXT_SEASON_READY so begin-season can proceed.
    if (
        cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING
        and current_key == "recruitment"
    ):
        next_index = beat_index + 1
        cursor = state_advance(
            cursor,
            CareerState.NEXT_SEASON_READY,
            offseason_beat_index=next_index,
        )
        save_career_state_cursor(conn, cursor)
        conn.commit()
        return build_beat_response(conn, cursor)

    next_index = beat_index + 1
    next_key = active_beats[next_index]
    if (
        next_key == "recruitment"
        and cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
    ):
        cursor = state_advance(
            cursor,
            CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            offseason_beat_index=next_index,
        )
    else:
        # State already in the right phase (or already past it). Bump index only.
        cursor = dataclasses.replace(cursor, offseason_beat_index=next_index)

    save_career_state_cursor(conn, cursor)
    conn.commit()
    return build_beat_response(conn, cursor)


def recruit_offseason_payload(
    conn: sqlite3.Connection, prospect_id: str | None = None
) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING:
        raise OffseasonError(
            f"Not in recruitment state (current: {cursor.state.value})", status_code=409
        )
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise OffseasonError("No player club assigned")

    active_beats = load_active_beats(conn)
    recruitment_index = active_beats.index("recruitment")

    if prospect_id == "skip":
        cursor = state_advance(
            cursor,
            CareerState.NEXT_SEASON_READY,
            offseason_beat_index=recruitment_index,
        )
        save_career_state_cursor(conn, cursor)
        conn.commit()
        return {
            **build_beat_response(conn, cursor),
            "signed_player": None,
        }

    signed_count_str = get_state(conn, "offseason_draft_signed_count") or "0"
    signed_count = int(signed_count_str)

    rosters = load_all_rosters(conn)
    user_roster = rosters.get(player_club_id, [])

    if len(user_roster) >= 9:
        raise OffseasonError("Roster is full (maximum 9 players).", status_code=409)

    if signed_count >= 3:
        raise OffseasonError("Already recruited 3 players this offseason.", status_code=409)

    season_number = cursor.season_number or 1
    if prospect_id:
        signed = sign_chosen_rookie(conn, player_club_id, season_number, prospect_id)
        if signed is None:
            raise OffseasonError(
                "That prospect is no longer available to sign.", status_code=409
            )
    else:
        signed = sign_best_rookie(conn, player_club_id, season_number)

    signed_count += 1
    set_state(conn, "offseason_draft_signed_count", str(signed_count))
    if signed:
        set_state(conn, "offseason_draft_signed_player_id", signed.id)

    rosters = load_all_rosters(conn)
    user_roster = rosters.get(player_club_id, [])

    if signed_count >= 3 or len(user_roster) >= 9:
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
                "overall": round(signed.overall_skill(), 1),
                "age": signed.age,
            }
            if signed
            else None
        ),
    }


def begin_next_season_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)

    # Self-heal: if the beat index has reached the final schedule-reveal beat
    # but the cursor is still in recruitment-pending (because recruitment was
    # impossible — roster full going in), promote to NEXT_SEASON_READY so the
    # season can start.
    if cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING:
        active_beats = load_active_beats(conn)
        idx = max(0, min(int(cursor.offseason_beat_index or 0), len(active_beats) - 1))
        if (
            "recruitment" in active_beats
            and idx > active_beats.index("recruitment")
        ):
            cursor = state_advance(
                cursor,
                CareerState.NEXT_SEASON_READY,
                offseason_beat_index=idx,
            )
            save_career_state_cursor(conn, cursor)
            conn.commit()

    if cursor.state != CareerState.NEXT_SEASON_READY:
        raise OffseasonError(f"Not ready to begin next season (current: {cursor.state.value})", status_code=409)
    new_cursor = begin_next_season(conn, cursor, load_clubs(conn))
    return {"status": "success", "state": career_state_payload(new_cursor)}


def _require_offseason_cursor(conn: sqlite3.Connection):
    cursor = load_career_state_cursor(conn)
    if cursor.state not in OFFSEASON_STATES:
        raise OffseasonError(f"Not in an offseason state (current: {cursor.state.value})", status_code=409)
    return cursor
