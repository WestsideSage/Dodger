"""Ball entities, activation, ownership, retrieval, and forfeiture.

Burden, valid throws, and live-ball resolution depend on knowing precisely
whether a ball is inactive, activated, held, live, blocked, dead, retrieved,
forfeited, contaminated, or replaced. Generic Dodger has no ball entities;
V11 introduces them as pure dataclasses with deterministic transitions.

Section 24-core retrieval clauses are handled here: queued players cannot
hold balls; entering players touching a ball before becoming live triggers
a deterministic forfeiture/out event.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from .official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)
from .rulesets import BallMaterial, RulesetProfile


class BallState(str, Enum):
    INACTIVE_CENTER = "inactive_center"  # designated centerline, pre-rush
    ACTIVATED_FREE = "activated_free"    # crossed attack line, no controller
    HELD = "held"                        # in a player's hands, post-activation
    LIVE_IN_FLIGHT = "live_in_flight"
    BLOCKED_LIVE = "blocked_live"
    RICOCHET_LIVE = "ricochet_live"
    DEAD = "dead"
    RETRIEVED = "retrieved"
    FORFEITED = "forfeited"
    CONTAMINATED = "contaminated"
    REPLACED = "replaced"


@dataclass
class OfficialBall:
    ball_id: str
    material: BallMaterial
    side: str | None = None              # team id of the side it spawns on
    state: BallState = BallState.INACTIVE_CENTER
    controller_player_id: str | None = None
    last_thrower_id: str | None = None
    sequence_id: str | None = None
    activated: bool = False
    court_side: str | None = None        # team id of court half it sits on


@dataclass(frozen=True)
class BallActivationPayload:
    ball_id: str
    activating_player_id: str
    method: str  # "crossed_attack_line" | "opening_rush_carry" | etc.


@dataclass(frozen=True)
class BallForfeitPayload:
    ball_id: str
    reason: str
    awarded_to_team_id: str | None = None


@dataclass(frozen=True)
class BallReplacementPayload:
    old_ball_id: str
    new_ball_id: str
    reason: str


def initial_balls(profile: RulesetProfile, team_a_id: str, team_b_id: str) -> List[OfficialBall]:
    """Create the starting ball arrangement for a game.

    Foam/no-sting: 3 designated inactive balls per side (6 total).
    Cloth: 2 designated balls per side + 1 neutral center ball (5 total).
    """

    balls: List[OfficialBall] = []
    if profile.material in (BallMaterial.FOAM, BallMaterial.NO_STING):
        for i in range(3):
            balls.append(OfficialBall(ball_id=f"a{i}", material=profile.material, side=team_a_id))
            balls.append(OfficialBall(ball_id=f"b{i}", material=profile.material, side=team_b_id))
    elif profile.material == BallMaterial.CLOTH:
        for i in range(2):
            balls.append(OfficialBall(ball_id=f"a{i}", material=profile.material, side=team_a_id))
            balls.append(OfficialBall(ball_id=f"b{i}", material=profile.material, side=team_b_id))
        balls.append(OfficialBall(ball_id="c0", material=profile.material, side=None))
    return balls


def activate_ball(ball: OfficialBall, *, player_id: str, match_id: str) -> OfficialEvent:
    """Mark a ball active once it has fully crossed the attack line.

    Section 11 (ball activation). This is a pure state transition and does
    not check geometric position; the caller is responsible for confirming
    the ball crossed the attack line.
    """

    ball.activated = True
    ball.controller_player_id = player_id
    ball.state = BallState.HELD
    return OfficialEvent(
        event_id=f"act-{ball.ball_id}",
        kind=OfficialEventKind.BALL,
        match_id=match_id,
        ball_ids=(ball.ball_id,),
        player_ids=(player_id,),
        rule_refs=(RuleReference("11"),),
        replay_summary=f"Ball {ball.ball_id} activated by {player_id}.",
        payload={"kind": "activation", "method": "crossed_attack_line"},
    )


def throw_inactive_ball_marks_thrower_out(
    ball: OfficialBall, *, thrower_id: str, match_id: str
) -> OfficialEvent:
    """Section 11/17: throwing an inactive ball makes the thrower out and
    leaves the ball inactive (it does not become live)."""

    if ball.activated:
        raise ValueError("Ball is already active; this rule does not apply")
    # Ball remains inactive; thrower is recorded as out via event.
    return OfficialEvent(
        event_id=f"badthrow-{ball.ball_id}-{thrower_id}",
        kind=OfficialEventKind.SEQUENCE,
        match_id=match_id,
        ball_ids=(ball.ball_id,),
        player_ids=(thrower_id,),
        rule_refs=(RuleReference("11"), RuleReference("17")),
        replay_summary=(
            f"{thrower_id} threw inactive ball {ball.ball_id}; thrower is out, "
            "ball remains inactive."
        ),
        payload={"kind": "inactive_throw_out", "thrower_out": True},
    )


def queue_player_holds_ball_forfeit(
    ball: OfficialBall, *, queued_player_id: str, match_id: str, opponent_team_id: str
) -> OfficialEvent:
    """Section 24-core: queued players cannot hold balls.

    Returns a deterministic forfeiture event. The ball is awarded to the
    opponent and marked forfeited.
    """

    ball.state = BallState.FORFEITED
    ball.controller_player_id = None
    ball.side = opponent_team_id
    return OfficialEvent(
        event_id=f"queueball-{ball.ball_id}-{queued_player_id}",
        kind=OfficialEventKind.BALL,
        match_id=match_id,
        ball_ids=(ball.ball_id,),
        player_ids=(queued_player_id,),
        team_ids=(opponent_team_id,),
        rule_refs=(RuleReference("24"),),
        replay_summary=(
            f"Queued player {queued_player_id} held ball {ball.ball_id}; "
            f"ball forfeited to {opponent_team_id}."
        ),
        payload={"kind": "queue_held_ball_forfeit"},
    )


def entering_player_touches_ball_before_live(
    ball: OfficialBall,
    *,
    entering_player_id: str,
    match_id: str,
    opponent_team_id: str,
) -> Tuple[OfficialEvent, OfficialEvent]:
    """Section 24-core: entering players cannot carry, roll, or intentionally
    touch a ball before becoming live. Returns (forfeit-event, out-event)."""

    forfeit_event = OfficialEvent(
        event_id=f"enterball-{ball.ball_id}-{entering_player_id}",
        kind=OfficialEventKind.BALL,
        match_id=match_id,
        ball_ids=(ball.ball_id,),
        player_ids=(entering_player_id,),
        team_ids=(opponent_team_id,),
        rule_refs=(RuleReference("23"), RuleReference("24")),
        replay_summary=(
            f"Entering player {entering_player_id} touched ball {ball.ball_id} "
            "before becoming live; ball forfeited."
        ),
        payload={"kind": "entering_touched_ball_forfeit"},
    )
    out_event = OfficialEvent(
        event_id=f"enterout-{entering_player_id}",
        kind=OfficialEventKind.PLAYER,
        match_id=match_id,
        player_ids=(entering_player_id,),
        rule_refs=(RuleReference("23"), RuleReference("24")),
        replay_summary=(
            f"Entering player {entering_player_id} is out for illegal ball "
            "contact before live status."
        ),
        payload={"kind": "entering_illegal_contact_out"},
    )
    ball.state = BallState.FORFEITED
    ball.controller_player_id = None
    ball.side = opponent_team_id
    return forfeit_event, out_event


def retrieved_ball_counts_for_burden(ball: OfficialBall) -> bool:
    """Retrieved balls count toward burden even while still held by a retriever
    on their way back to the active court (Section 13/24-core)."""

    return ball.state in (BallState.RETRIEVED, BallState.HELD)
