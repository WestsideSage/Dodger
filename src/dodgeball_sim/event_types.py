from __future__ import annotations

from typing import Any, Dict, Optional, Union

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


class MatchStartContext(TypedDict):
    config_version: str
    difficulty: str
    meta_patch: Optional[Dict[str, Any]]
    team_policies: Dict[str, Dict[str, float]]


class MatchEndContext(TypedDict):
    reason: str


class ThrowContext(TypedDict):
    tick: int
    thrower_selection: Dict[str, Any]
    target_selection: Dict[str, Any]
    difficulty: str
    policy_snapshot: Dict[str, float]
    chemistry_delta: float
    meta_patch: Optional[Dict[str, Any]]
    rush_context: Dict[str, Any]
    sync_context: Dict[str, Any]
    calc: Dict[str, Any]
    fatigue: Dict[str, Any]
    catch_decision: Optional[Dict[str, Any]]
    pressure_context: Dict[str, Any]


EventContext = Union[MatchStartContext, MatchEndContext, ThrowContext]

__all__ = [
    "EventContext",
    "MatchEndContext",
    "MatchStartContext",
    "ThrowContext",
]
