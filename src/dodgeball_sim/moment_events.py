"""Six recognition moments — replay/event contract.

These are emitted by tier drivers when state changes match the moment
definition from brief.md §4. Surfacing in the replay UI is Plan C; the
emission contract lives here so B/C/D can build against it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Union


class MomentKind(str, Enum):
    DRAMATIC_CATCH = "dramatic_catch"
    LATE_GAME_ESCAPE = "late_game_escape"
    ONE_V_ONE_FINALE = "one_v_one_finale"
    GASSED_COLLAPSE = "gassed_collapse"
    FLOOD_THROW = "flood_throw"
    COMEBACK = "comeback"


@dataclass(frozen=True)
class DramaticCatch:
    """A live-ball catch that returns a teammate from the queue."""

    match_id: str
    tick: int
    catcher_id: str
    catcher_team_id: str
    thrower_id: str
    thrower_team_id: str
    returning_player_id: str
    active_count_a: int
    active_count_b: int
    kind: MomentKind = MomentKind.DRAMATIC_CATCH
    # Official multi-game matches: which game (1-based) the moment happened in.
    # ``tick`` is the per-game engine tick, so it is only meaningful alongside
    # this. None for single-game engines (rec) and legacy payloads.
    game_number: int | None = None


@dataclass(frozen=True)
class LateGameEscape:
    """A single survivor faces three or more opposing actives."""

    match_id: str
    tick: int
    survivor_id: str
    survivor_team_id: str
    attacker_team_id: str
    attacker_count: int
    kind: MomentKind = MomentKind.LATE_GAME_ESCAPE
    game_number: int | None = None


@dataclass(frozen=True)
class OneVOneFinale:
    """Last two players on court, one per side."""

    match_id: str
    tick: int
    player_a_id: str
    player_b_id: str
    tick_started: int
    kind: MomentKind = MomentKind.ONE_V_ONE_FINALE
    game_number: int | None = None


@dataclass(frozen=True)
class GassedCollapse:
    """A player went out while their fatigue exceeded the gassed threshold."""

    match_id: str
    tick: int
    player_id: str
    team_id: str
    fatigue_pct: float
    kind: MomentKind = MomentKind.GASSED_COLLAPSE
    game_number: int | None = None


@dataclass(frozen=True)
class FloodThrow:
    """Three or more throws released in the same tick from one side."""

    match_id: str
    tick: int
    thrower_team_id: str
    thrower_ids: Tuple[str, ...]
    kind: MomentKind = MomentKind.FLOOD_THROW
    game_number: int | None = None


@dataclass(frozen=True)
class Comeback:
    """A team came back from a multi-player deficit via clutch catches."""

    match_id: str
    tick: int
    team_id: str
    deficit_at_low_point: int
    catches_during_comeback: int
    kind: MomentKind = MomentKind.COMEBACK
    game_number: int | None = None


MomentEvent = Union[
    DramaticCatch,
    LateGameEscape,
    OneVOneFinale,
    GassedCollapse,
    FloodThrow,
    Comeback,
]


__all__ = [
    "MomentKind",
    "MomentEvent",
    "DramaticCatch",
    "LateGameEscape",
    "OneVOneFinale",
    "GassedCollapse",
    "FloodThrow",
    "Comeback",
]
