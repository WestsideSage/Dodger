"""Burden to throw and throw clock.

V11 burden is *not* generic possession. It is derived from ball control,
player majority, prior burden inversion, and (for cloth equal-ball cases) a
referee reachability judgment that must surface as a
:class:`~dodgeball_sim.rule_discretion.RuleDiscretionEvent`.

Foam/no-sting (Sections 13, 14):
    burden goes to the team with the ball majority (>= profile threshold),
    or the team with the player majority on a tie, or inverts the previous
    burden if both counts tie. Burden resets after every valid throw and
    forfeits all balls on failure at zero.

Cloth (Sections 13, 14):
    burden uses two stages: a 5-second window to lose ball majority, then a
    "play n balls" call where ``n = controlled_balls - 1`` (capped by live
    players) inside another 5-second window. Failure outs ball controllers
    first, then captain-selected additional players, then official-selected
    fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)
from .rule_discretion import RuleDiscretionEvent
from .rulesets import BallMaterial, RulesetProfile


class BurdenBasis(str, Enum):
    BALL_MAJORITY = "ball_majority"
    PLAYER_MAJORITY = "player_majority"
    PRIOR_BURDEN_INVERSION = "prior_burden_inversion"
    CLOTH_REACHABLE_BALL_RULING = "cloth_reachable_ball_ruling"


class ThrowClockStatus(str, Enum):
    IDLE = "idle"
    ACTIVE = "active"
    ZERO_CALLED = "zero_called"
    PLAY_N_ACTIVE = "play_n_active"
    STOPPED = "stopped"


@dataclass
class BurdenState:
    team_id: Optional[str]
    basis: BurdenBasis
    clock_status: ThrowClockStatus = ThrowClockStatus.IDLE
    started_at_ms: int = 0
    expires_at_ms: int = 0
    play_n_count: int = 0
    play_n_called_at_ms: int = 0
    play_n_attempts: int = 0
    controllers_at_call: Tuple[str, ...] = ()
    previous_burden_team_id: Optional[str] = None


@dataclass(frozen=True)
class PlayNBallsCall:
    team_id: str
    ball_count: int
    n: int  # number of throws required
    deadline_ms: int


@dataclass(frozen=True)
class ThrowClockPenalty:
    team_id: str
    rule_section: str  # "14"
    reason: str
    out_player_ids: Tuple[str, ...]
    forfeited_ball_ids: Tuple[str, ...]
    awarded_to_team_id: str | None


@dataclass(frozen=True)
class ClothReachableBallRuling:
    team_id: str
    rationale: str  # "closer_to_balls" | "previous_burden_inversion" | etc.


def _ball_counts_by_side(controllers: Dict[str, str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for team_id in controllers.values():
        counts[team_id] = counts.get(team_id, 0) + 1
    return counts


def establish_burden(
    profile: RulesetProfile,
    *,
    ball_controllers: Dict[str, str],
    live_player_counts: Dict[str, int],
    previous_burden_team_id: Optional[str],
    team_a_id: str,
    team_b_id: str,
) -> Tuple[BurdenState, Optional[RuleDiscretionEvent]]:
    """Determine which team owns the burden.

    ``ball_controllers`` maps ball_id -> team_id of the controlling side.
    Foam/no-sting cascade: ball majority -> player majority -> prior inversion.
    Cloth equal-ball burden uses an explicit discretion event.
    """

    counts = _ball_counts_by_side(ball_controllers)
    a_balls = counts.get(team_a_id, 0)
    b_balls = counts.get(team_b_id, 0)

    threshold = profile.burden_majority_threshold

    if profile.material in (BallMaterial.FOAM, BallMaterial.NO_STING):
        if a_balls >= threshold and a_balls > b_balls:
            return (
                BurdenState(
                    team_id=team_a_id,
                    basis=BurdenBasis.BALL_MAJORITY,
                    previous_burden_team_id=previous_burden_team_id,
                ),
                None,
            )
        if b_balls >= threshold and b_balls > a_balls:
            return (
                BurdenState(
                    team_id=team_b_id,
                    basis=BurdenBasis.BALL_MAJORITY,
                    previous_burden_team_id=previous_burden_team_id,
                ),
                None,
            )
        # Tied on balls or both below threshold -> player majority
        a_players = live_player_counts.get(team_a_id, 0)
        b_players = live_player_counts.get(team_b_id, 0)
        if a_players > b_players:
            return (
                BurdenState(
                    team_id=team_a_id,
                    basis=BurdenBasis.PLAYER_MAJORITY,
                    previous_burden_team_id=previous_burden_team_id,
                ),
                None,
            )
        if b_players > a_players:
            return (
                BurdenState(
                    team_id=team_b_id,
                    basis=BurdenBasis.PLAYER_MAJORITY,
                    previous_burden_team_id=previous_burden_team_id,
                ),
                None,
            )
        # All tied -> invert previous burden, default to team_a if none
        inverted = team_b_id if previous_burden_team_id == team_a_id else team_a_id
        return (
            BurdenState(
                team_id=inverted,
                basis=BurdenBasis.PRIOR_BURDEN_INVERSION,
                previous_burden_team_id=previous_burden_team_id,
            ),
            None,
        )

    # Cloth
    if a_balls >= threshold and a_balls > b_balls:
        return (
            BurdenState(
                team_id=team_a_id,
                basis=BurdenBasis.BALL_MAJORITY,
                previous_burden_team_id=previous_burden_team_id,
            ),
            None,
        )
    if b_balls >= threshold and b_balls > a_balls:
        return (
            BurdenState(
                team_id=team_b_id,
                basis=BurdenBasis.BALL_MAJORITY,
                previous_burden_team_id=previous_burden_team_id,
            ),
            None,
        )
    # Equal-ball cloth burden -> referee reachability discretion.
    default_team = team_b_id if previous_burden_team_id == team_a_id else team_a_id
    discretion = RuleDiscretionEvent(
        rule_section="13",
        trigger="cloth_equal_ball_burden",
        default_ruling=f"award_to_{default_team}",
        alternative_rulings=(
            f"award_to_{team_a_id}",
            f"award_to_{team_b_id}",
        ),
        selected_ruling=f"award_to_{default_team}",
        selection_basis="default_reachable_side",
        replay_summary=(
            "Equal balls on cloth; burden defaulted to opposite of previous holder."
        ),
    )
    return (
        BurdenState(
            team_id=default_team,
            basis=BurdenBasis.CLOTH_REACHABLE_BALL_RULING,
            previous_burden_team_id=previous_burden_team_id,
        ),
        discretion,
    )


def reset_burden_after_valid_throw(state: BurdenState) -> BurdenState:
    """Foam/no-sting: any valid throw resets the burden clock."""

    return BurdenState(
        team_id=None,
        basis=state.basis,
        clock_status=ThrowClockStatus.IDLE,
        previous_burden_team_id=state.team_id,
    )


def foam_failure_forfeit(
    *,
    burden: BurdenState,
    opponent_team_id: str,
    all_ball_ids: Tuple[str, ...],
) -> ThrowClockPenalty:
    """Section 14: foam/no-sting throw-clock failure at zero forfeits all
    balls to the opponent. No outs."""

    return ThrowClockPenalty(
        team_id=burden.team_id or "",
        rule_section="14",
        reason="throw_clock_zero_no_throw",
        out_player_ids=(),
        forfeited_ball_ids=all_ball_ids,
        awarded_to_team_id=opponent_team_id,
    )


def cloth_play_n_call(
    *,
    team_id: str,
    controlled_ball_ids: Tuple[str, ...],
    live_player_count: int,
    now_ms: int,
    window_ms: int = 5000,
) -> PlayNBallsCall:
    """Compute the cloth "play n balls" call.

    ``n = max(0, controlled - 1)`` capped by ``live_player_count``.
    Live-player cap reflects that each remaining player can attempt at most
    one throw inside the window before being eliminated.
    """

    ball_count = len(controlled_ball_ids)
    n = max(0, ball_count - 1)
    n = min(n, live_player_count)
    return PlayNBallsCall(
        team_id=team_id,
        ball_count=ball_count,
        n=n,
        deadline_ms=now_ms + window_ms,
    )


def cloth_play_n_failure(
    *,
    call: PlayNBallsCall,
    controllers_in_order: Tuple[str, ...],
    captain_selected: Tuple[str, ...],
    attempts_made: int,
    opponent_team_id: str,
    eliminated_before_attempt: Tuple[str, ...] = (),
) -> ThrowClockPenalty:
    """Section 14: cloth "play n balls" failure outs ball controllers first,
    then captain-selected additional outs to reach the ``n - attempts_made``
    shortfall. Eliminated-before-attempt players still count their controlled
    balls as thrown.
    """

    shortfall = max(0, call.n - attempts_made - len(eliminated_before_attempt))
    outs: List[str] = []
    # Controllers (in order at the call)
    for pid in controllers_in_order:
        if shortfall <= 0:
            break
        outs.append(pid)
        shortfall -= 1
    # Captain-selected additional
    for pid in captain_selected:
        if shortfall <= 0:
            break
        if pid in outs:
            continue
        outs.append(pid)
        shortfall -= 1
    return ThrowClockPenalty(
        team_id=call.team_id,
        rule_section="14",
        reason="cloth_play_n_failure",
        out_player_ids=tuple(outs),
        forfeited_ball_ids=(),
        awarded_to_team_id=opponent_team_id,
    )


def burden_event(
    state: BurdenState,
    *,
    match_id: str,
    game_id: str | None = None,
) -> OfficialEvent:
    return OfficialEvent(
        event_id=f"burden-{state.team_id}-{state.basis.value}",
        kind=OfficialEventKind.BURDEN,
        match_id=match_id,
        game_id=game_id,
        team_ids=(state.team_id,) if state.team_id else (),
        rule_refs=(RuleReference("13"),),
        replay_summary=(
            f"Burden -> {state.team_id} via {state.basis.value}."
        ),
        payload={
            "team_id": state.team_id,
            "basis": state.basis.value,
            "clock_status": state.clock_status.value,
        },
    )
