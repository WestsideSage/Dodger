from __future__ import annotations

"""Career state machine for Manager Mode save/resume behavior."""

from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional, Set, Tuple


class CareerState(str, Enum):
    SPLASH = "splash"
    SEASON_ACTIVE_PRE_MATCH = "season_active_pre_match"
    SEASON_ACTIVE_IN_MATCH = "season_active_in_match"
    SEASON_ACTIVE_MATCH_REPORT_PENDING = "season_active_match_report_pending"
    SEASON_COMPLETE_OFFSEASON_BEAT = "season_complete_offseason_beat"
    SEASON_COMPLETE_RECRUITMENT_PENDING = "season_complete_recruitment_pending"
    NEXT_SEASON_READY = "next_season_ready"


@dataclass(frozen=True)
class CareerStateCursor:
    state: CareerState
    season_number: int = 0
    week: int = 0
    offseason_beat_index: int = 0
    match_id: Optional[str] = None


class InvalidTransitionError(RuntimeError):
    pass


_ALLOWED: Set[Tuple[CareerState, CareerState]] = {
    (CareerState.SPLASH, CareerState.SEASON_ACTIVE_PRE_MATCH),
    (CareerState.SEASON_ACTIVE_PRE_MATCH, CareerState.SEASON_ACTIVE_IN_MATCH),
    (CareerState.SEASON_ACTIVE_IN_MATCH, CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING),
    (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_ACTIVE_PRE_MATCH),
    (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
    (CareerState.SEASON_ACTIVE_PRE_MATCH, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
    (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
    (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING),
    (CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING, CareerState.NEXT_SEASON_READY),
    (CareerState.NEXT_SEASON_READY, CareerState.SEASON_ACTIVE_PRE_MATCH),
}


def can_transition(from_state: CareerState, to_state: CareerState) -> bool:
    return (from_state, to_state) in _ALLOWED


def advance(cursor: CareerStateCursor, to_state: CareerState, **payload_updates) -> CareerStateCursor:
    if not can_transition(cursor.state, to_state):
        raise InvalidTransitionError(
            f"Cannot transition {cursor.state.value} -> {to_state.value}"
        )
    return replace(cursor, state=to_state, **payload_updates)


__all__ = [
    "CareerState",
    "CareerStateCursor",
    "InvalidTransitionError",
    "advance",
    "can_transition",
]
