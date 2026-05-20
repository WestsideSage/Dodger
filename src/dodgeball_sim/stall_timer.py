"""Rec-league stall timer primitive (brief §3.5).

If a side holds every ball for STALL_CAP_SECONDS without a release,
balls are rolled to the opposite side. No cards, no warnings. Used by
the Tier 1 driver only; V11 / USAD uses the formal ``burden`` module.
"""

from __future__ import annotations

from dataclasses import dataclass


STALL_CAP_SECONDS: float = 10.0


@dataclass(frozen=True)
class StallTimerState:
    seconds_holding: float = 0.0

    @classmethod
    def fresh(cls) -> "StallTimerState":
        return cls(seconds_holding=0.0)


def advance_holding(
    state: StallTimerState,
    *,
    seconds: float,
    side_controls_all_balls: bool,
) -> StallTimerState:
    if not side_controls_all_balls:
        return StallTimerState(seconds_holding=0.0)
    return StallTimerState(seconds_holding=state.seconds_holding + seconds)


def reset_on_throw(state: StallTimerState) -> StallTimerState:
    return StallTimerState(seconds_holding=0.0)


def should_reset_balls(state: StallTimerState) -> bool:
    return state.seconds_holding >= STALL_CAP_SECONDS


__all__ = [
    "STALL_CAP_SECONDS",
    "StallTimerState",
    "advance_holding",
    "reset_on_throw",
    "should_reset_balls",
]
