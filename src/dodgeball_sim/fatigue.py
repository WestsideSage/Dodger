"""In-match fatigue primitive.

Tracks per-player fatigue from 0.0 (fresh) to 1.0 (collapsed). Used by
both the rec and (eventually) official drivers to produce the
gassed-star recognition moment. The ``conditioning_curve`` parameter is
exposed for Plan B to attach a per-player attribute; Plan A uses the
default which produces fatigue effects with the existing
``PlayerRatings.stamina`` field unmodified.
"""

from __future__ import annotations

from dataclasses import dataclass


GASSED_THRESHOLD: float = 0.75
"""Fatigue value at which a player is considered gassed for moment emission."""


@dataclass(frozen=True)
class FatigueParams:
    """Tunable parameters. Plan B may attach per-player conditioning_curve."""

    base_accumulation: float = 1.0
    base_recovery_per_second: float = 0.01
    conditioning_curve: float = 50.0  # 0..100, higher = slower fatigue gain

    def accumulation_multiplier(self) -> float:
        # conditioning_curve 0 -> 1.5x, 50 -> 1.0x, 100 -> 0.5x
        return 1.5 - (self.conditioning_curve / 100.0)


@dataclass(frozen=True)
class FatigueState:
    value: float = 0.0

    @classmethod
    def fresh(cls) -> "FatigueState":
        return cls(value=0.0)

    def is_gassed(self) -> bool:
        return self.value >= GASSED_THRESHOLD


def accumulate(
    state: FatigueState,
    *,
    action_cost: float,
    params: FatigueParams,
) -> FatigueState:
    """Add fatigue from an action. action_cost is in [0, 1]."""
    delta = params.base_accumulation * action_cost * params.accumulation_multiplier()
    new_value = min(1.0, state.value + delta)
    return FatigueState(value=new_value)


def recover(
    state: FatigueState,
    *,
    seconds_idle: float,
    params: FatigueParams,
) -> FatigueState:
    """Reduce fatigue from idle time."""
    delta = params.base_recovery_per_second * seconds_idle
    new_value = max(0.0, state.value - delta)
    return FatigueState(value=new_value)


def effectiveness(state: FatigueState, *, stamina: float = 50.0) -> float:
    """Return an effectiveness multiplier in (0, 1] for throws/dodges.

    Linear-ish curve: fresh = 1.0, fully gassed = ~0.4 at average stamina.

    V19a: ``stamina`` (0-100) governs how much accumulated fatigue actually
    degrades performance — "staying power": a high-stamina player performs
    near their sheet even when gassed, a low-stamina player collapses harder.
    At stamina 50 the curve is exactly the pre-V19a one, so legacy callers
    are unchanged. (Distinct from ``conditioning_curve``, which governs how
    FAST fatigue accumulates — no double-pricing.)
    """
    stamina_norm = max(0.0, min(100.0, float(stamina))) / 100.0
    degradation = 0.6 * (1.4 - 0.8 * stamina_norm)
    return max(0.3, 1.0 - degradation * state.value)


__all__ = [
    "FatigueState",
    "FatigueParams",
    "GASSED_THRESHOLD",
    "accumulate",
    "recover",
    "effectiveness",
]
