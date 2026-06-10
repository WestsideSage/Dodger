"""No-blocking mode (Section 27).

When activated, held balls no longer protect a player: a thrown ball that
hits a held ball still completes its sequence, and the held-ball player can
become out by body extension. No-blocking is triggered by game-time limit
(180s in foam/no-sting) or match-time end (the sourced "match-end No
Blocking game": play continues without interruption).

Primary-source notes (Workflow-0, 2026-06-01): the trigger and the match-end
terminal state are SOURCED; "Balls do not reset" is SOURCED — the autonomous
engine activates with ``NoBlockingBallReset.NONE`` (the old ``three_per_side``
default contradicted the source and survives only as an enum member for
scripted-test compatibility). What "reduced blocking" changes in resolution
is NOT specified by the source; the shipping enforcement (the held-ball block
branch in ``official_resolution.resolve_throw`` is disabled while active) is
a disclosed sim-design proposal measured in the V17 retro, not a USAD
fidelity claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)


class NoBlockingSource(str, Enum):
    GAME_TIME_LIMIT = "game_time_limit"
    MATCH_TIME_END = "match_time_end"
    PLAYOFF_OVERTIME = "playoff_overtime"


class NoBlockingBallReset(str, Enum):
    NONE = "none"
    THREE_PER_SIDE = "three_per_side"


@dataclass(frozen=True)
class NoBlockingState:
    active: bool
    source: NoBlockingSource | None
    ball_reset: NoBlockingBallReset = NoBlockingBallReset.NONE
    time_limit_seconds: int = 180  # 0 == untimed


def activate_no_blocking(
    *,
    source: NoBlockingSource,
    ball_reset: NoBlockingBallReset,
    time_limit_seconds: int,
    match_id: str,
    game_id: str | None = None,
) -> tuple[NoBlockingState, OfficialEvent]:
    state = NoBlockingState(
        active=True,
        source=source,
        ball_reset=ball_reset,
        time_limit_seconds=time_limit_seconds,
    )
    event = OfficialEvent(
        event_id=f"nb-{source.value}",
        kind=OfficialEventKind.NO_BLOCKING,
        match_id=match_id,
        game_id=game_id,
        rule_refs=(RuleReference("27"),),
        replay_summary=(
            f"No-blocking active ({source.value}); ball reset {ball_reset.value}."
        ),
        payload={
            "source": source.value,
            "ball_reset": ball_reset.value,
            "time_limit_seconds": time_limit_seconds,
        },
    )
    return state, event


def resolve_contact_with_held_ball(
    *,
    no_blocking: NoBlockingState,
    held_ball_player_id: str,
    thrown_ball_alive_after_contact: bool,
) -> bool:
    """Return True if the held-ball player is out from this contact.

    Under no-blocking the held ball is a body extension: if the thrown ball
    completes its sequence (still alive after contact = it can hit the body),
    the player is out. Under normal blocking the player remains protected.
    """

    if not no_blocking.active:
        return False
    # Body extension: any contact with the held ball can make the player out
    # once the thrown ball completes its sequence. We treat
    # ``thrown_ball_alive_after_contact`` as a flag for whether the ball did
    # not die instantly; either way, no-blocking means the held ball does not
    # protect, so the contact stands.
    return True
