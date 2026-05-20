"""Engine driver interface for the hybrid tier-driver architecture.

Plan A of the post-V11 redesign introduces multiple per-tier engine
drivers (rec, official) that compose a shared primitive layer. B/C/D
consume only this module's types — they do not import driver internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol, Tuple


@dataclass(frozen=True)
class DriverMatchInput:
    """Inputs required to run a single match through any tier driver."""

    match_id: str
    team_a_id: str
    team_b_id: str
    starters_a: Tuple[str, ...]
    starters_b: Tuple[str, ...]
    player_lookup: Dict[str, Any]
    policy_a: Any
    policy_b: Any
    seed: int
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DriverMatchOutput:
    """Outputs produced by any tier driver after a single match."""

    events: Tuple[Any, ...]
    winner_team_id: str | None
    final_active_a: int
    final_active_b: int
    moment_events: Tuple[Any, ...] = ()
    replay_state: Any | None = None


class EngineDriver(Protocol):
    """Protocol implemented by per-tier engine drivers."""

    tier_id: str

    def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
        ...


__all__ = ["EngineDriver", "DriverMatchInput", "DriverMatchOutput"]
