"""Flood-throw detection primitive.

A flood throw is three or more throws released in the same engine tick
from the same team. The primitive accumulates pending throws per tick
and reports a detection when the threshold is met. The existing
``SequenceLedger`` is not modified — the driver opens N sequences in
one tick and feeds this tracker in parallel.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


FLOOD_THRESHOLD: int = 3


@dataclass(frozen=True)
class PendingThrow:
    thrower_id: str
    team_id: str
    tick: int


@dataclass(frozen=True)
class FloodDetection:
    team_id: str
    thrower_ids: Tuple[str, ...]
    tick: int


@dataclass
class FloodThrowTracker:
    """Per-tick accumulator. State is keyed by tick and cleared on read."""

    _by_tick: Dict[int, List[PendingThrow]] = field(default_factory=lambda: defaultdict(list))

    def record(self, throw: PendingThrow) -> None:
        self._by_tick[throw.tick].append(throw)

    def detect_flood(self, *, tick: int) -> FloodDetection | None:
        throws = self._by_tick.get(tick, [])
        if len(throws) < FLOOD_THRESHOLD:
            return None
        # Bucket by team
        by_team: Dict[str, List[PendingThrow]] = defaultdict(list)
        for t in throws:
            by_team[t.team_id].append(t)
        # Pick the team with the most throws this tick
        best_team, best_throws = max(by_team.items(), key=lambda kv: len(kv[1]))
        if len(best_throws) < FLOOD_THRESHOLD:
            return None
        return FloodDetection(
            team_id=best_team,
            thrower_ids=tuple(t.thrower_id for t in best_throws),
            tick=tick,
        )


__all__ = [
    "FLOOD_THRESHOLD",
    "PendingThrow",
    "FloodDetection",
    "FloodThrowTracker",
]
