from typing import Any, Dict, NotRequired, Optional, TypedDict, Union


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
    pressure_active: bool
    pressure_reason: NotRequired[str]
    pressure_modifier: NotRequired[float]
    catch_decision: NotRequired[Optional[Dict[str, Any]]]


EventContext = Union[MatchStartContext, MatchEndContext, ThrowContext]

__all__ = [
    "EventContext",
    "MatchEndContext",
    "MatchStartContext",
    "ThrowContext",
]
