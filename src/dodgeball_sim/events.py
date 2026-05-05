from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class MatchEvent:
    event_id: int
    tick: int
    seed: int
    event_type: str
    phase: str
    actors: Dict[str, Any]
    context: Dict[str, Any]
    probabilities: Dict[str, float]
    rolls: Dict[str, float]
    outcome: Dict[str, Any]
    state_diff: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = ["MatchEvent"]