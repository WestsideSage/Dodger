"""Official match/game lifecycle state machine.

A USA Dodgeball *match* contains many *games*. Each game has its own clock,
mode, and result. Match-level state includes overtime, no-blocking, and
late-start awarded games. The generic Dodger engine has no equivalent
abstraction; V11 adds these as pure dataclasses and helper functions.

This module deliberately stays away from scheduler.py and playoffs.py until
Phase 8D selects an official engine. Helper functions here can be imported,
but they must not mutate franchise/playoff persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from .rulesets import BallMaterial, RulesetProfile


class OfficialMatchState(str, Enum):
    SCHEDULED = "scheduled"
    PRE_MATCH_VALIDATION = "pre_match_validation"
    SIDE_SELECTION = "side_selection"
    GAME_SETUP = "game_setup"
    OPENING_RUSH = "opening_rush"
    GAME_LIVE = "game_live"
    GAME_STOPPAGE = "game_stoppage"
    NO_BLOCKING = "no_blocking"
    OVERTIME = "overtime"
    SUDDEN_DEATH = "sudden_death"
    MATCH_COMPLETE = "match_complete"


class OfficialGameMode(str, Enum):
    STANDARD = "standard"
    NO_BLOCKING = "no_blocking"
    OVERTIME = "overtime"
    SUDDEN_DEATH = "sudden_death"


class OfficialGameResult(str, Enum):
    PENDING = "pending"
    TEAM_A_WIN = "team_a_win"
    TEAM_B_WIN = "team_b_win"
    TIE = "tie"
    FORFEIT_A = "forfeit_a"
    FORFEIT_B = "forfeit_b"
    NO_POINT = "no_point"


class OfficialRoundType(str, Enum):
    ROUND_ROBIN = "round_robin"
    BRACKET_STANDARD = "bracket_standard"
    BRACKET_SEMIFINAL = "bracket_semifinal"
    BRACKET_FINAL = "bracket_final"


# Bracket round durations in seconds, per USAD 2026.1.
_BRACKET_DURATIONS_SECONDS = {
    OfficialRoundType.BRACKET_STANDARD: 24 * 60,
    OfficialRoundType.BRACKET_SEMIFINAL: 30 * 60,
    OfficialRoundType.BRACKET_FINAL: 40 * 60,
}


def bracket_match_clock_seconds(round_type: OfficialRoundType) -> int:
    """Return the match clock (seconds) for a bracket round.

    Round-robin has no match clock; bracket rounds use 24/30/40 minutes.
    """

    if round_type == OfficialRoundType.ROUND_ROBIN:
        return 0
    return _BRACKET_DURATIONS_SECONDS[round_type]


@dataclass
class OfficialGameClock:
    limit_seconds: int
    elapsed_seconds: int = 0

    def remaining(self) -> int:
        if self.limit_seconds <= 0:
            return 10**9  # untimed sentinel
        return max(0, self.limit_seconds - self.elapsed_seconds)

    def expired(self) -> bool:
        return self.limit_seconds > 0 and self.elapsed_seconds >= self.limit_seconds

    def advance(self, seconds: int) -> None:
        self.elapsed_seconds += max(0, int(seconds))


@dataclass
class OfficialMatchClock:
    limit_seconds: int
    elapsed_seconds: int = 0

    def remaining(self) -> int:
        if self.limit_seconds <= 0:
            return 10**9
        return max(0, self.limit_seconds - self.elapsed_seconds)

    def expired(self) -> bool:
        return self.limit_seconds > 0 and self.elapsed_seconds >= self.limit_seconds


@dataclass
class OfficialGameState:
    game_number: int
    profile: RulesetProfile
    clock: OfficialGameClock
    mode: OfficialGameMode = OfficialGameMode.STANDARD
    result: OfficialGameResult = OfficialGameResult.PENDING
    starting_side_team_id: str | None = None
    active_count_a: int = 0
    active_count_b: int = 0

    def trigger_no_blocking(self) -> bool:
        """Return True when game-clock elapsed crosses the no-blocking line."""

        trigger = self.profile.no_blocking_trigger_seconds
        return trigger > 0 and self.clock.elapsed_seconds >= trigger


@dataclass
class OfficialMatchScore:
    team_a_id: str
    team_b_id: str
    team_a_games: int = 0
    team_b_games: int = 0
    team_a_ties: int = 0
    team_b_ties: int = 0
    no_point_games: int = 0


@dataclass
class OfficialMatch:
    match_id: str
    profile: RulesetProfile
    round_type: OfficialRoundType
    match_clock: OfficialMatchClock
    score: OfficialMatchScore
    state: OfficialMatchState = OfficialMatchState.SCHEDULED
    games: List[OfficialGameState] = field(default_factory=list)
    late_start_awarded_games: Tuple[str, ...] = ()


def decide_cloth_game_by_active_count(game: OfficialGameState) -> OfficialGameResult:
    """At cloth game-clock expiry, the team with more active players wins.

    Equal counts tie. Section 6 (match) + section 9 (beginning of play).
    """

    if game.profile.material != BallMaterial.CLOTH:
        raise ValueError("decide_cloth_game_by_active_count only applies to cloth")
    if game.active_count_a > game.active_count_b:
        return OfficialGameResult.TEAM_A_WIN
    if game.active_count_b > game.active_count_a:
        return OfficialGameResult.TEAM_B_WIN
    return OfficialGameResult.TIE


def cloth_final_game_clock_seconds(remaining_match_seconds: int) -> int:
    """Return the cloth final-game clock when match time is running short.

    If less than 90 seconds remain when a new game would start, the final
    game uses a 90-second clock instead of the standard 180.
    """

    if remaining_match_seconds < 90:
        return 90
    return 180
