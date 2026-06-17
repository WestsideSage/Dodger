from __future__ import annotations

import dataclasses
import sqlite3
from typing import Any

from .career_state import CareerState, advance as state_advance
from .lineup import STARTERS_COUNT
from .offseason_ceremony import (
    available_recruitment_choices,
    begin_next_season,
    ensure_ai_offseason_signings,
    finalize_season,
    initialize_manager_offseason,
    sign_chosen_rookie_contested,
    stored_root_seed,
)
from .offseason_presentation import MAX_USER_ROSTER, build_beat_response, load_active_beats
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

    # V25: advancing past the Transfer Period commits the user's decisions
    # (re-signs/releases resolved through the contested poach logic, accepted
    # buyouts settled). Idempotent — auto-pilot advance commits the safe defaults.
    if current_key == "transfer_period":
        player_club_id = get_state(conn, "player_club_id")
        season_id = get_state(conn, "active_season_id")
        if player_club_id and season_id:
            from .transfer_market import apply_user_transfer_decisions

            apply_user_transfer_decisions(
                conn, season_id, player_club_id, stored_root_seed(conn)
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
        ensure_ai_offseason_signings(conn)
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
    conn: sqlite3.Connection,
    prospect_id: str | None = None,
    release_player_id: str | None = None,
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
        # Roster-floor guard: the user club is exempt from every AI roster
        # repair path (ensure_ai_rosters_playable and the offseason refill both
        # skip it), so repeatedly skipping recruitment lets retirements bleed
        # the roster below the fielded six with no in-season recovery — a
        # measured 10-season auto-pilot sweep ended at 4 players. Block the
        # skip only when the club genuinely cannot field six AND there is
        # someone available to sign; an empty pool still allows the skip.
        user_roster_now = load_all_rosters(conn).get(player_club_id, [])
        if len(user_roster_now) < STARTERS_COUNT and available_recruitment_choices(
            conn, cursor.season_number or 1
        ):
            raise OffseasonError(
                f"Your roster has {len(user_roster_now)} players — at least "
                f"{STARTERS_COUNT} are needed to field a legal six next season. "
                "Sign at least one player before skipping.",
                status_code=409,
            )
        cursor = state_advance(
            cursor,
            CareerState.NEXT_SEASON_READY,
            offseason_beat_index=recruitment_index,
        )
        save_career_state_cursor(conn, cursor)
        conn.commit()
        # Recruitment is closed: the AI clubs make their Signing Day moves now
        # so the class report the player is about to see includes them.
        ensure_ai_offseason_signings(conn)
        return {
            **build_beat_response(conn, cursor),
            "signed_player": None,
            "signing_outcome": None,
        }

    signed_count_str = get_state(conn, "offseason_draft_signed_count") or "0"
    signed_count = int(signed_count_str)

    if signed_count >= 3:
        raise OffseasonError("Already recruited 3 players this offseason.", status_code=409)

    rosters = load_all_rosters(conn)
    user_roster = rosters.get(player_club_id, [])

    swap_required = len(user_roster) >= MAX_USER_ROSTER
    if swap_required:
        # Playtest 3 F-8: a full roster no longer dead-ends Signing Day — the
        # pick goes through by releasing a named player to free agency
        # (sign-over-cut). Without a release choice the request is rejected
        # with the action the player must take, not a silent skip.
        if not release_player_id:
            raise OffseasonError(
                f"Roster is full ({len(user_roster)}/{MAX_USER_ROSTER}). "
                "Pick a player to release to make room, or finish Signing Day.",
                status_code=409,
            )
        # Validate the releasee NOW, but commit the release only after the
        # contested round is WON — a snipe must not cost the released player
        # (transactional honesty: no action loses roster value for nothing).
        if not any(p.id == release_player_id for p in user_roster):
            raise OffseasonError(
                f"Player {release_player_id} is not on your roster.",
                status_code=404,
            )
    elif release_player_id:
        raise OffseasonError(
            "Release-to-sign is only needed when the roster is full.",
            status_code=409,
        )

    season_number = cursor.season_number or 1
    if prospect_id:
        signed, signing_outcome = sign_chosen_rookie_contested(
            conn, player_club_id, season_number, prospect_id
        )
        if signed is None and signing_outcome is None:
            raise OffseasonError(
                "That prospect is no longer available to sign.", status_code=409
            )
    else:
        # Auto-pick: the best available signee by PUBLIC estimate (the same
        # order the picker shows). It goes through the contested round like
        # any other prospect pick — auto-pick is not a snipe-proof back door.
        choices = available_recruitment_choices(conn, season_number)
        if choices:
            signed, signing_outcome = sign_chosen_rookie_contested(
                conn, player_club_id, season_number, choices[0]["prospect_id"]
            )
        else:
            signed, signing_outcome = None, None

    # Faithfulness (BUG #5 / ADR 0002): the signed-count is the single source of
    # truth for "how many you signed" across the whole Signing-Day surface, so it
    # must equal the real number of roster additions. Only bump it when a player
    # was actually signed — a snipe or an empty pool adds nobody, and an
    # un-guarded increment would let "used" exceed the roster delta.
    if signed:
        signed_count += 1
        set_state(conn, "offseason_draft_signed_count", str(signed_count))
        set_state(conn, "offseason_draft_signed_player_id", signed.id)

    # Commit the sign-over-cut release only now that the contested round is
    # WON: the roster sat at cap+1 for the instant between commit and release;
    # a snipe skips the release entirely and the roster is untouched.
    released_outcome = None
    if signed and swap_required and release_player_id:
        from .roster_moves import RosterMoveError, release_player_to_free_agency

        try:
            released_outcome = release_player_to_free_agency(conn, release_player_id)
        except RosterMoveError as exc:  # pre-validated above; defensive only
            raise OffseasonError(exc.detail, status_code=exc.status_code) from exc

    rosters = load_all_rosters(conn)
    user_roster = rosters.get(player_club_id, [])

    # Playtest 3 F-8: a full roster no longer closes the beat — every signing
    # at 12/12 is a release-to-sign swap, so the remaining class slots stay
    # spendable. Only exhausting the slots ends recruitment automatically.
    closed = signed_count >= 3
    if closed:
        cursor = state_advance(
            cursor,
            CareerState.NEXT_SEASON_READY,
            offseason_beat_index=recruitment_index,
        )
        save_career_state_cursor(conn, cursor)

    conn.commit()
    if closed:
        ensure_ai_offseason_signings(conn)
    return {
        **build_beat_response(conn, cursor),
        "signed_player": (
            {
                "id": signed.id,
                "name": signed.name,
                "overall": signed.overall_skill(),
                "age": signed.age,
            }
            if signed
            else None
        ),
        "signing_outcome": signing_outcome,
        "released_player": (released_outcome or {}).get("released_player"),
        "released_broken_promise": (released_outcome or {}).get("broken_promise"),
    }


def transfer_action_payload(
    conn: sqlite3.Connection,
    action: str,
    player_id: str,
    offer_k: int | None = None,
) -> dict[str, Any]:
    """Adjust a Transfer Period decision (re-sign/release an expiring player, or
    accept/refuse an incoming buyout). Mutates only the cached decisions — the
    roster commits when the user advances past the beat."""
    cursor = _require_offseason_cursor(conn)
    active_beats = load_active_beats(conn)
    if "transfer_period" not in active_beats:
        raise OffseasonError("No transfer period this offseason.", status_code=409)
    if get_state(conn, "v25_user_transfer_committed_for") == get_state(conn, "active_season_id"):
        raise OffseasonError("Transfer Period already committed.", status_code=409)

    from .transfer_market import set_buyout_decision, set_expiring_decision

    if action in ("resign", "release"):
        state = set_expiring_decision(conn, player_id, action, offer_k)
    elif action in ("accept_buyout", "refuse_buyout"):
        state = set_buyout_decision(
            conn, player_id, "accept" if action == "accept_buyout" else "refuse"
        )
    else:
        raise OffseasonError(f"Unknown transfer action: {action}", status_code=400)
    if state is None:
        raise OffseasonError("No transfer state to act on.", status_code=409)
    conn.commit()
    return build_beat_response(conn, cursor)


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
