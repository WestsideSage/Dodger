"""Backend-only replay payload contract for official-rules matches.

Frontend rendering for the official-rules replay is deferred until Phase 9.
This module exists so backend modules (sequence, burden, catch_queue, etc.)
can agree on a stable payload shape *before* persistence and frontend code
get involved. Phase 9 must consume :class:`OfficialReplayState` rather than
redefine it.

All views are optional from the frontend's perspective: a generic replay
payload with no ``official_state`` still loads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Mapping, Tuple

from .official_events import (
    OFFICIAL_PAYLOAD_VERSION,
    RULEBOOK_VERSION,
    OfficialEvent,
)


@dataclass(frozen=True)
class OfficialClockView:
    limit_seconds: int
    elapsed_seconds: int


@dataclass(frozen=True)
class OfficialGameScoreView:
    team_a_id: str
    team_b_id: str
    team_a_games: int = 0
    team_b_games: int = 0
    team_a_ties: int = 0
    team_b_ties: int = 0
    no_point_games: int = 0


@dataclass(frozen=True)
class OfficialBurdenView:
    team_id: str | None
    basis: str
    clock_status: str
    seconds_remaining: int = 0
    play_n_count: int = 0


@dataclass(frozen=True)
class OfficialBallView:
    ball_id: str
    state: str
    side: str | None = None
    controller_player_id: str | None = None


@dataclass(frozen=True)
class OfficialTeamStateView:
    team_id: str
    active_ids: Tuple[str, ...] = ()
    queued_ids: Tuple[str, ...] = ()
    entering_id: str | None = None
    unavailable_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class OfficialSequenceView:
    sequence_id: str
    thrower_id: str | None
    ball_id: str | None
    pending_outs: Tuple[str, ...] = ()
    pending_saves: Tuple[str, ...] = ()
    final: bool = False


@dataclass(frozen=True)
class OfficialRuleCallView:
    rule_label: str
    summary: str
    timestamp_seconds: int = 0


@dataclass(frozen=True)
class OfficialReplayState:
    """Top-level official replay payload (backend canonical shape)."""

    ruleset: str
    rulebook_version: str = RULEBOOK_VERSION
    official_payload_version: str = OFFICIAL_PAYLOAD_VERSION
    match_clock: OfficialClockView | None = None
    game_clock: OfficialClockView | None = None
    game_score: OfficialGameScoreView | None = None
    mode: str = "standard"
    burden: OfficialBurdenView | None = None
    balls: Tuple[OfficialBallView, ...] = ()
    teams: Tuple[OfficialTeamStateView, ...] = ()
    player_statuses: Mapping[str, str] = field(default_factory=dict)
    active_sequences: Tuple[OfficialSequenceView, ...] = ()
    rule_calls: Tuple[OfficialRuleCallView, ...] = ()
    events: Tuple[OfficialEvent, ...] = ()


def empty_replay_state(ruleset: str) -> OfficialReplayState:
    return OfficialReplayState(ruleset=ruleset)
