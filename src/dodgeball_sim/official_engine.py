"""Scripted official-engine harness.

This is the orchestration adapter for V11. It does NOT own rules, tactics,
timing, or randomness; it composes the focused modules. Phase 8A only
supports *scripted* actions for use in tests and for building the
:class:`~dodgeball_sim.replay_contracts.OfficialReplayState` shape before
autonomous action selection is added (Phase 8C).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dataclass_replace
from enum import Enum
from typing import List, Tuple

from .rng import derive_seed
from .ball_state import (
    BallState,
    OfficialBall,
    activate_ball,
    initial_balls,
    queue_player_holds_ball_forfeit,
    retrieved_ball_counts_for_burden,
    throw_inactive_ball_marks_thrower_out,
)
from .burden import (
    BurdenState,
    burden_event,
    establish_burden,
)
from .catch_queue import (
    CatchQueueState,
    enqueue_out_player,
    return_player_on_catch,
)
from .match_lifecycle import (
    OfficialGameClock,
    OfficialGameMode,
    OfficialGameResult,
    OfficialGameState,
    OfficialMatchClock,
    decide_cloth_game_by_active_count,
)
from .no_blocking import (
    NoBlockingBallReset,
    NoBlockingSource,
    NoBlockingState,
    activate_no_blocking,
)
from .official_actions import (
    ActionSelector,
    LegalActionGenerator,
    ProactiveKind,
    ThrowAction,
)
from .official_events import OfficialEvent, OfficialEventKind, RuleReference
from .player_state import OfficialPlayerState, OfficialPlayerStatus
from .replay_contracts import (
    OfficialBallView,
    OfficialBurdenView,
    OfficialClockView,
    OfficialGameScoreView,
    OfficialReplayState,
    OfficialRuleCallView,
    OfficialTeamStateView,
)
from .rulesets import BallMaterial, RulesetProfile
from .sequence import (
    SequenceLedger,
    SequenceOfPlay,
    resolve_sequence,
    sequence_event,
)
from .discipline import DisciplineState
from .official_scoring import (
    OfficialGameScore,
    OfficialMatchScore,
    foam_game_points,
    cloth_game_points,
    match_winner_from_points,
)


class ScriptedActionKind(str, Enum):
    ACTIVATE_BALL = "activate_ball"
    VALID_THROW = "valid_throw"
    CATCH = "catch"
    HIT = "hit"
    ADVANCE_CLOCK = "advance_clock"
    DECIDE_CLOTH_GAME = "decide_cloth_game"


@dataclass
class ScriptedOfficialAction:
    kind: ScriptedActionKind
    payload: dict


@dataclass
class OfficialEngineStep:
    action: ScriptedOfficialAction
    events: Tuple[OfficialEvent, ...]


@dataclass
class OfficialEngineResult:
    steps: List[OfficialEngineStep] = field(default_factory=list)
    final_game_result: OfficialGameResult = OfficialGameResult.PENDING

    def all_events(self) -> Tuple[OfficialEvent, ...]:
        out: List[OfficialEvent] = []
        for step in self.steps:
            out.extend(step.events)
        return tuple(out)


def _find_ball(balls: List[OfficialBall], ball_id: str) -> OfficialBall:
    for b in balls:
        if b.ball_id == ball_id:
            return b
    raise KeyError(ball_id)


def run_scripted_game(
    *,
    profile: RulesetProfile,
    match_id: str,
    team_a_id: str,
    team_b_id: str,
    starters_a: Tuple[str, ...],
    starters_b: Tuple[str, ...],
    actions: List[ScriptedOfficialAction],
) -> OfficialEngineResult:
    """Run a scripted official game.

    The harness consumes predetermined actions and emits only
    :class:`OfficialEvent` envelopes. Tests use this to validate that the
    composition of ball/catch/sequence/lifecycle modules works end to end
    without inventing autonomous tactics.
    """

    balls = initial_balls(profile, team_a_id, team_b_id)
    players = {pid: OfficialPlayerState(player_id=pid, team_id=team_a_id,
                                        status=OfficialPlayerStatus.ACTIVE,
                                        is_starter=True) for pid in starters_a}
    players.update({pid: OfficialPlayerState(player_id=pid, team_id=team_b_id,
                                             status=OfficialPlayerStatus.ACTIVE,
                                             is_starter=True) for pid in starters_b})
    queues = {team_a_id: CatchQueueState(team_id=team_a_id),
              team_b_id: CatchQueueState(team_id=team_b_id)}
    ledger = SequenceLedger()
    clock = OfficialGameClock(limit_seconds=profile.game_clock_seconds)
    game_state = OfficialGameState(
        game_number=1,
        profile=profile,
        clock=clock,
        active_count_a=len(starters_a),
        active_count_b=len(starters_b),
    )

    result = OfficialEngineResult()
    seq_counter = 0

    for action in actions:
        events: List[OfficialEvent] = []
        if action.kind == ScriptedActionKind.ACTIVATE_BALL:
            ball = _find_ball(balls, action.payload["ball_id"])
            events.append(activate_ball(ball, player_id=action.payload["player_id"], match_id=match_id))

        elif action.kind == ScriptedActionKind.VALID_THROW:
            seq_counter += 1
            ball = _find_ball(balls, action.payload["ball_id"])
            if not ball.activated:
                events.append(throw_inactive_ball_marks_thrower_out(
                    ball, thrower_id=action.payload["thrower_id"], match_id=match_id
                ))
                # Apply out
                pid = action.payload["thrower_id"]
                player = players[pid]
                player.status = OfficialPlayerStatus.QUEUED
                _decrement_active(game_state, player, team_a_id)
                continue
            ball.state = BallState.LIVE_IN_FLIGHT
            ball.last_thrower_id = action.payload["thrower_id"]
            seq = SequenceOfPlay(
                sequence_id=f"s{seq_counter}",
                match_id=match_id,
                game_id=None,
                thrower_id=action.payload["thrower_id"],
                thrower_team_id=players[action.payload["thrower_id"]].team_id,
                ball_id=ball.ball_id,
                release_time_ms=action.payload.get("release_time_ms", 0),
                material=profile.material,
            )
            ledger.open_sequence(seq)
            # Apply scripted contacts
            for hit_pid in action.payload.get("hits", []):
                seq.add_pending_out(hit_pid, "hit")
            for catcher_pid in action.payload.get("catches", []):
                seq.add_catch(catcher_pid, timestamp_ms=action.payload.get("catch_time_ms", 0))
            ruling = ledger.close_sequence(seq.sequence_id)
            events.append(sequence_event(seq))
            # Apply outs/returns to player state and queues
            for pid in ruling.outs:
                player = players[pid]
                if player.status == OfficialPlayerStatus.ACTIVE:
                    player.status = OfficialPlayerStatus.QUEUED
                    _decrement_active(game_state, player, team_a_id)
                    events.append(enqueue_out_player(
                        queues[player.team_id], player_id=pid,
                        is_starter=player.is_starter, match_id=match_id,
                    ))
            # If catch happened, return a player on the catcher's team
            if ruling.catches:
                catch_team = players[ruling.catches[0].catcher_id].team_id
                ret_event, returning_pid = return_player_on_catch(
                    queues[catch_team], sequence_id=seq.sequence_id, match_id=match_id,
                )
                if ret_event is not None:
                    events.append(ret_event)
                    returning_player = players[returning_pid]
                    returning_player.status = OfficialPlayerStatus.ENTERING
                    if returning_player.team_id == team_a_id:
                        game_state.active_count_a += 1
                    else:
                        game_state.active_count_b += 1
            ball.state = BallState.DEAD

        elif action.kind == ScriptedActionKind.ADVANCE_CLOCK:
            clock.advance(action.payload.get("seconds", 0))

        elif action.kind == ScriptedActionKind.DECIDE_CLOTH_GAME:
            if profile.material != BallMaterial.CLOTH:
                raise ValueError("DECIDE_CLOTH_GAME only valid for cloth")
            game_state.result = decide_cloth_game_by_active_count(game_state)
            result.final_game_result = game_state.result

        result.steps.append(OfficialEngineStep(action=action, events=tuple(events)))

    return result


def _decrement_active(game_state: OfficialGameState, player: OfficialPlayerState, team_a_id: str) -> None:
    if player.team_id == team_a_id:
        game_state.active_count_a = max(0, game_state.active_count_a - 1)
    else:
        game_state.active_count_b = max(0, game_state.active_count_b - 1)


def _ball_controller_teams(
    balls: List[OfficialBall],
    players: dict[str, OfficialPlayerState],
) -> dict[str, str]:
    controller_teams: dict[str, str] = {}
    for ball in balls:
        controller = ball.controller_player_id
        if not controller or controller not in players:
            continue
        if not retrieved_ball_counts_for_burden(ball):
            continue
        controller_teams[ball.ball_id] = players[controller].team_id
    return controller_teams


def _live_player_counts(
    *,
    team_a_id: str,
    team_b_id: str,
    players: dict[str, OfficialPlayerState],
) -> dict[str, int]:
    return {
        team_a_id: sum(
            1 for player in players.values()
            if player.team_id == team_a_id and player.is_live_for_hits()
        ),
        team_b_id: sum(
            1 for player in players.values()
            if player.team_id == team_b_id and player.is_live_for_hits()
        ),
    }


def _team_state_view(
    *,
    team_id: str,
    players: dict[str, OfficialPlayerState],
    queue: CatchQueueState,
) -> OfficialTeamStateView:
    active_ids = tuple(
        player.player_id
        for player in players.values()
        if player.team_id == team_id and player.status == OfficialPlayerStatus.ACTIVE
    )
    unavailable_ids = tuple(dict.fromkeys(queue.nonstarter_ids + queue.discipline_blocked_ids))
    entering_id = queue.entering.player_id if queue.entering is not None else None
    return OfficialTeamStateView(
        team_id=team_id,
        active_ids=active_ids,
        queued_ids=tuple(queue.queued_ids),
        entering_id=entering_id,
        unavailable_ids=unavailable_ids,
    )


def _replay_state_from_live_engine(
    *,
    profile: RulesetProfile,
    team_a_id: str,
    team_b_id: str,
    mode: OfficialGameMode,
    game_clock: OfficialGameClock,
    match_clock: OfficialMatchClock,
    burden_state: BurdenState | None,
    balls: List[OfficialBall],
    players: dict[str, OfficialPlayerState],
    queues: dict[str, CatchQueueState],
    events: List[OfficialEvent],
    winner_team_id: str | None,
) -> OfficialReplayState:
    team_a_games = 1 if winner_team_id == team_a_id else 0
    team_b_games = 1 if winner_team_id == team_b_id else 0
    team_a_ties = 1 if winner_team_id is None else 0
    team_b_ties = 1 if winner_team_id is None else 0
    rule_calls: list[OfficialRuleCallView] = []
    for event in events:
        for label in event.rule_labels():
            rule_calls.append(
                OfficialRuleCallView(rule_label=label, summary=event.replay_summary)
            )
    burden_view = None
    if burden_state is not None:
        burden_view = OfficialBurdenView(
            team_id=burden_state.team_id,
            basis=burden_state.basis.value,
            clock_status=burden_state.clock_status.value,
            seconds_remaining=max(0, (burden_state.expires_at_ms - (game_clock.elapsed_seconds * 1000)) // 1000),
            play_n_count=burden_state.play_n_count,
        )
    return OfficialReplayState(
        ruleset=profile.name,
        match_clock=OfficialClockView(
            limit_seconds=match_clock.limit_seconds,
            elapsed_seconds=match_clock.elapsed_seconds,
        ),
        game_clock=OfficialClockView(
            limit_seconds=game_clock.limit_seconds,
            elapsed_seconds=game_clock.elapsed_seconds,
        ),
        game_score=OfficialGameScoreView(
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            team_a_games=team_a_games,
            team_b_games=team_b_games,
            team_a_ties=team_a_ties,
            team_b_ties=team_b_ties,
            no_point_games=0,
        ),
        mode=mode.value,
        burden=burden_view,
        balls=tuple(
            OfficialBallView(
                ball_id=ball.ball_id,
                state=ball.state.value,
                side=ball.side,
                controller_player_id=ball.controller_player_id,
            )
            for ball in balls
        ),
        teams=(
            _team_state_view(team_id=team_a_id, players=players, queue=queues[team_a_id]),
            _team_state_view(team_id=team_b_id, players=players, queue=queues[team_b_id]),
        ),
        player_statuses={
            player_id: player.status.value
            for player_id, player in players.items()
        },
        rule_calls=tuple(rule_calls),
        events=tuple(events),
    )


def _throw_action_weight(
    action: ThrowAction,
    *,
    player_lookup: dict[str, Player],
    policy: CoachPolicy,
    burden_team_id: str | None,
    team_id: str,
) -> float:
    player = player_lookup[action.actor_id]
    if policy.approach == Approach.AGGRESSIVE:
        rating_weight = (
            player.ratings.normalized_accuracy() * 0.3
            + player.ratings.normalized_power() * 0.7
        )
    elif policy.approach == Approach.PATIENT:
        rating_weight = (
            player.ratings.normalized_accuracy() * 0.75
            + player.ratings.normalized_power() * 0.25
        )
    else:
        rating_weight = (
            player.ratings.normalized_accuracy() * 0.5
            + player.ratings.normalized_power() * 0.5
        )
    burden_weight = 1.25 if burden_team_id == team_id else 1.0
    return max(0.01, rating_weight * burden_weight)


# ---------------------------------------------------------------------------
# Autonomous game loop (Phase 8C+ tactics parity)
# ---------------------------------------------------------------------------

import random as _random

from .models import Approach, CoachPolicy, OpeningRushCommit, OpeningRushTarget, Player


# --- WT-20 opening rush (2026-06-10, sim-design) -------------------------------
# Opening-rush behavior is NOT a sourced USA Dodgeball rule (the primary source
# only defines possession by center-line crossing — see
# docs/specs/2026-06-01-workflow0-primary-source-rule-verification.md). These
# effects are DISCLOSED sim-design: the rush knobs stop being announced-only on
# official careers and instead drive two real, legible levers:
#   * rush_commit -> the opening exchange (the first _OPENING_EXCHANGE_TICKS
#     of each game): an all-in rush releases closer to the line, so its
#     throws are harder to catch — but its rushers are not set, so their own
#     catch attempts on the counter are weaker. Hold-back mirrors (easier to
#     catch from range; camped defenders catch better). A rank-based
#     "initiative" model was tried first and measured as a pure first-mover
#     penalty (hold_back +17pp over all_in — a dominant option, see the V17
#     retro); the symmetric shading replaces it. First offense is a seeded
#     coin flip, which also retires the old hardcoded team-A first-throw
#     asymmetry.
#   * rush_target -> which players secure the designated balls off the rush
#     (NEAREST = slot order, the pre-WT-20 behavior; STRONGEST_SIDE = strongest
#     throwers first; CENTER = best overall players first). Ball-holders are
#     the throw candidates and (post-WT-20) the held-ball blockers, so who
#     holds is a real decision.
_OPENING_EXCHANGE_TICKS = 3
# Defender's own catch readiness during the opening exchange, by their rush.
# Asymmetric on purpose (offense payoff > defense cost for ALL_IN): the first
# symmetric cut (0.85/0.85) still measured all_in at -8pp because the opening
# exchange is ~40% of a post-WT-20 game and the catch economy punishes the
# defense-side factor harder.
_RUSH_CATCH_READINESS = {
    OpeningRushCommit.ALL_IN: 0.92,
    OpeningRushCommit.BALANCED: 1.0,
    OpeningRushCommit.HOLD_BACK: 1.08,
}
# How catchable a team's opening-exchange throws are, by the THROWER's rush.
_RUSH_THROW_PRESSURE = {
    OpeningRushCommit.ALL_IN: 0.80,
    OpeningRushCommit.BALANCED: 1.0,
    OpeningRushCommit.HOLD_BACK: 1.10,
}


def _rush_holder_order(
    starters: Tuple[str, ...], player_lookup: dict, policy: CoachPolicy
) -> List[str]:
    """Order a team's starters for designated-ball assignment (WT-20 rush)."""

    order = list(starters)
    if policy.rush_target == OpeningRushTarget.STRONGEST_SIDE:
        order.sort(
            key=lambda pid: -player_lookup[pid].ratings.normalized_power()
        )
    elif policy.rush_target == OpeningRushTarget.CENTER:
        order.sort(key=lambda pid: -player_lookup[pid].overall_skill())
    return order


# --- V19a engine consumers (2026-06-10) ----------------------------------------
# Slot-role fit: a starter seated (slot order = the lineup) in one of the four
# preference-bearing court roles whose archetype fits plays slightly above
# their sheet on every action stat — lineup.role_fit_bonuses, shared with the
# rec driver. Bonus-only by design — a mismatched seat costs the foregone
# bonus, never a hidden penalty, so the 2026-06-09 audit's "liability
# fiction" stays dead and the Lineup Editor's fit notes become a real,
# disclosed tradeoff against raw OVR.
#
# Stamina: action stats erode with MATCH progress, scaled by how far the
# player's stamina sits below the cap — "staying power across a long match",
# exactly what the rating tooltip has always claimed. A stamina-100 player
# never erodes; at the career-seed mean (~63) the erosion reaches ~6.7 points
# by full time. Both sides erode together at even stamina, so the
# even-strength baseline holds; the differential is the consumer (probe
# iteration: 0.12 measured +12 stamina at 52.0% vs 49.8% baseline — live but
# inside the CI; 0.18 separates it cleanly without approaching the core-four
# attribute weights).
_STAMINA_EROSION_MAX = 0.18
from .moment_events import (
    Comeback,
    DramaticCatch,
    LateGameEscape,
    MomentEvent,
    OneVOneFinale,
)
from .official_resolution import resolve_throw
from .official_tactics import select_target

# Phase 4a moment thresholds (mirror the rec driver's recognition intent).
_LATE_ESCAPE_ATTACKERS = 3
_COMEBACK_MIN_DEFICIT = 2


@dataclass
class AutonomousGameResult:
    winner_team_id: str | None
    events: Tuple[OfficialEvent, ...]
    final_active_a: int
    final_active_b: int
    ticks: int
    replay_state: OfficialReplayState
    moment_events: Tuple[MomentEvent, ...] = ()


def run_autonomous_game(
    *,
    profile: RulesetProfile,
    match_id: str,
    team_a_id: str,
    team_b_id: str,
    starters_a: Tuple[str, ...],
    starters_b: Tuple[str, ...],
    player_lookup: dict,
    policy_a: CoachPolicy,
    policy_b: CoachPolicy,
    seed: int,
    max_ticks: int = 200,
    discipline_state: DisciplineState | None = None,
    game_number: int = 1,
    elapsed_match_seconds: int = 0,
    match_clock_limit: int = 0,
    prep_a: dict | None = None,
    prep_b: dict | None = None,
) -> AutonomousGameResult:
    """Run a full official game with autonomous tactics.

    Each tick the burden-holding side picks a thrower and a target via
    :mod:`official_tactics`, the throw is resolved via :mod:`official_resolution`,
    and the sequence is finalized through the ledger. The loop ends when a
    side has no active players or when ``max_ticks`` is reached.
    """

    rng = _random.Random(seed)
    selector = ActionSelector(rng)
    balls = initial_balls(profile, team_a_id, team_b_id)
    events: List[OfficialEvent] = []
    # WT-20 opening rush: rush_target orders which players secure the
    # designated balls (see _rush_holder_order — disclosed sim-design).
    a_starters = _rush_holder_order(starters_a, player_lookup, policy_a)
    b_starters = _rush_holder_order(starters_b, player_lookup, policy_b)
    a_idx = 0
    b_idx = 0
    for ball in balls:
        if ball.side == team_a_id:
            holder = a_starters[a_idx % len(a_starters)]
            a_idx += 1
        elif ball.side == team_b_id:
            holder = b_starters[b_idx % len(b_starters)]
            b_idx += 1
        else:
            holder = a_starters[0]
        events.append(activate_ball(ball, player_id=holder, match_id=match_id))

    players = {
        pid: OfficialPlayerState(
            player_id=pid,
            team_id=team_a_id,
            status=OfficialPlayerStatus.ACTIVE,
            is_starter=True,
        )
        for pid in starters_a
    }
    players.update(
        {
            pid: OfficialPlayerState(
                player_id=pid,
                team_id=team_b_id,
                status=OfficialPlayerStatus.ACTIVE,
                is_starter=True,
            )
            for pid in starters_b
        }
    )
    queues = {
        team_a_id: CatchQueueState(team_id=team_a_id),
        team_b_id: CatchQueueState(team_id=team_b_id),
    }
    ledger = SequenceLedger()
    game_clock = OfficialGameClock(limit_seconds=profile.game_clock_seconds)
    match_clock = OfficialMatchClock(limit_seconds=match_clock_limit or profile.match_clock_seconds, elapsed_seconds=elapsed_match_seconds)
    game_state = OfficialGameState(
        game_number=game_number,
        profile=profile,
        clock=game_clock,
        active_count_a=len(starters_a),
        active_count_b=len(starters_b),
    )
    active_a = len(starters_a)
    active_b = len(starters_b)
    seq_counter = 0
    # Phase 4a moment recognition state (DRAMATIC_CATCH, LATE_GAME_ESCAPE,
    # ONE_V_ONE_FINALE, COMEBACK; GASSED_COLLAPSE / FLOOD_THROW are deferred —
    # the official loop has no fatigue model nor batch-throw tracker).
    moments: list[MomentEvent] = []
    one_v_one_emitted = False
    late_escape_emitted: dict[str, bool] = {team_a_id: False, team_b_id: False}
    worst_deficit: dict[str, int] = {team_a_id: 0, team_b_id: 0}
    comeback_catches: dict[str, int] = {team_a_id: 0, team_b_id: 0}
    recent_pressure_by_team: dict[str, str | None] = {team_a_id: None, team_b_id: None}
    no_blocking_state = NoBlockingState(active=False, source=None)
    burden_state: BurdenState | None = None
    previous_burden_team_id: str | None = None

    def _live_for(team_id: str) -> list[OfficialPlayerState]:
        return [
            player
            for player in players.values()
            if player.team_id == team_id and player.is_live_for_hits()
        ]

    def _holding_ball(team_id: str) -> list[OfficialPlayerState]:
        living = _live_for(team_id)
        living_ids = {player.player_id for player in living}
        controllers = {
            ball.controller_player_id
            for ball in balls
            if ball.activated and ball.state == BallState.HELD
        }
        return [
            player
            for player in living
            if player.player_id in controllers and player.player_id in living_ids
        ]

    # WT-20: first offense is a seeded coin flip (retires the old hardcoded
    # team-A first-throw asymmetry). rush_commit expresses through the
    # opening-exchange catch shading below, not through initiative — see the
    # _RUSH_CATCH_READINESS / _RUSH_THROW_PRESSURE design note.
    offense_team = team_a_id if rng.random() < 0.5 else team_b_id
    policies = {team_a_id: policy_a, team_b_id: policy_b}
    tick_seconds = 6
    ticks = 0

    # V19a performance shades: role fit (static per game) minus stamina
    # erosion (grows with match progress; the closure reads the live clock).
    # V19b: a club's weekly STAFF FOCUS may carry a disclosed match prep —
    # "conditioning" relieves the stamina erosion (deficit halved), "tactics"
    # sharpens the targeting read (see the select_target call). Symmetric:
    # AI clubs run the same focus system through their weekly plans.
    from .lineup import role_fit_bonuses

    role_fit = role_fit_bonuses((starters_a, starters_b), player_lookup)
    preps = {team_a_id: dict(prep_a or {}), team_b_id: dict(prep_b or {})}
    team_of = {pid: team_a_id for pid in starters_a}
    team_of.update({pid: team_b_id for pid in starters_b})

    def _shade_for(pid: str) -> float:
        progress = min(
            1.0,
            match_clock.elapsed_seconds / max(1, match_clock.limit_seconds),
        )
        stamina_norm = max(0.0, min(1.0, player_lookup[pid].ratings.stamina / 100.0))
        erosion = _STAMINA_EROSION_MAX * progress * (1.0 - stamina_norm)
        relief = float(preps.get(team_of.get(pid, ""), {}).get("stamina_relief", 1.0))
        return role_fit.get(pid, 0.0) - erosion * relief

    def _read_iq_for(pid: str) -> float:
        bonus = float(
            preps.get(team_of.get(pid, ""), {}).get("targeting_read_bonus", 0.0)
        )
        return min(100.0, player_lookup[pid].ratings.tactical_iq + bonus)

    while ticks < max_ticks and active_a > 0 and active_b > 0:
        controller_teams = _ball_controller_teams(balls, players)
        live_counts = _live_player_counts(
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            players=players,
        )
        next_burden, discretion = establish_burden(
            profile,
            ball_controllers=controller_teams,
            live_player_counts=live_counts,
            previous_burden_team_id=previous_burden_team_id,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
        )
        if discretion is not None:
            # WT-20 made this path reachable in autonomous play: the ball
            # lifecycle (forfeiture + next-tick retrieval) can leave a cloth
            # court with equal CONTROLLED balls mid-game, which triggers the
            # equal-ball reachability discretion. Pre-WT-20 every ball stayed
            # controlled forever, so the call (with its missing-event_id
            # latent bug) never executed on this path. Tick-stamped id keeps
            # repeat rulings unique within the game.
            events.append(discretion.to_official_event(
                event_id=f"discretion-t{ticks}",
                match_id=match_id,
                team_ids=(next_burden.team_id,) if next_burden.team_id else (),
            ))
        if (
            burden_state is None
            or burden_state.team_id != next_burden.team_id
            or burden_state.basis != next_burden.basis
        ):
            events.append(burden_event(next_burden, match_id=match_id))
        burden_state = next_burden

        if (
            not no_blocking_state.active
            and profile.material in (BallMaterial.FOAM, BallMaterial.NO_STING)
        ):
            nb_source = None
            if game_state.trigger_no_blocking():
                nb_source = NoBlockingSource.GAME_TIME_LIMIT
            elif match_clock.expired():
                # Sourced (Section 27): if the match clock expires during a
                # game, play continues without interruption and the current
                # game becomes a match-end No Blocking game.
                nb_source = NoBlockingSource.MATCH_TIME_END
            if nb_source is not None:
                no_blocking_state, no_blocking_event = activate_no_blocking(
                    source=nb_source,
                    # Sourced: "Balls do not reset." The pre-WT-20
                    # three_per_side value contradicted the primary source
                    # (Workflow-0 latent-inaccuracy note) and is corrected
                    # here, where No Blocking becomes genuinely enforced.
                    ball_reset=NoBlockingBallReset.NONE,
                    time_limit_seconds=profile.no_blocking_trigger_seconds,
                    match_id=match_id,
                )
                events.append(no_blocking_event)
                game_state.mode = OfficialGameMode.NO_BLOCKING

        # WT-20 ball lifecycle: loose balls re-enter play. Out players forfeit
        # their held balls (Section 24-core) and blocked throws drop on the
        # defense's side; each tick a live player on the ball's side picks one
        # up (non-holders first, slot order). Pre-WT-20 these balls leaked out
        # of circulation — once every ball was stranded on an out player,
        # neither side could throw and the game dead-aired to the tick cap
        # (the no_point stall artifact; see the V17 retro measurement).
        holder_ids = {
            b.controller_player_id
            for b in balls
            if b.activated and b.state == BallState.HELD
        }
        for loose in balls:
            if not loose.activated or loose.state not in (
                BallState.FORFEITED,
                BallState.ACTIVATED_FREE,
            ):
                continue
            side_live = _live_for(loose.side) if loose.side else []
            if not side_live:
                continue
            picker = next(
                (p for p in side_live if p.player_id not in holder_ids),
                side_live[0],
            )
            loose.state = BallState.HELD
            loose.controller_player_id = picker.player_id
            holder_ids.add(picker.player_id)
            events.append(OfficialEvent(
                event_id=f"retr-{loose.ball_id}-t{ticks}",
                kind=OfficialEventKind.BALL,
                match_id=match_id,
                ball_ids=(loose.ball_id,),
                player_ids=(picker.player_id,),
                team_ids=(loose.side,) if loose.side else (),
                rule_refs=(RuleReference("24"),),
                replay_summary=(
                    f"{picker.player_id} retrieves loose ball {loose.ball_id}."
                ),
                payload={"kind": "loose_ball_retrieved"},
            ))

        a_throwers = _holding_ball(team_a_id)
        b_throwers = _holding_ball(team_b_id)
        if a_throwers and not b_throwers:
            offense_team = team_a_id
        elif b_throwers and not a_throwers:
            offense_team = team_b_id
        elif a_throwers and b_throwers:
            offense_team = team_b_id if offense_team == team_a_id else team_a_id
        else:
            ticks += 1
            game_clock.advance(tick_seconds)
            if match_clock.limit_seconds > 0:
                match_clock.elapsed_seconds += tick_seconds
            continue

        legal_actions = [
            action
            for action in LegalActionGenerator(
                players=players,
                balls=balls,
                burden=burden_state,
            ).all_legal()
            if players[action.actor_id].team_id == offense_team
        ]
        throw_actions = [
            action for action in legal_actions if action.kind == ProactiveKind.THROW
        ]
        if not throw_actions:
            ticks += 1
            game_clock.advance(tick_seconds)
            if match_clock.limit_seconds > 0:
                match_clock.elapsed_seconds += tick_seconds
            continue

        weighted_actions = [
            _throw_action_weight(
                action,
                player_lookup=player_lookup,
                policy=policies[offense_team],
                burden_team_id=burden_state.team_id if burden_state is not None else None,
                team_id=offense_team,
            )
            for action in throw_actions
        ]
        chosen_action = selector.select(throw_actions, weights=weighted_actions)
        if not isinstance(chosen_action, ThrowAction):
            raise RuntimeError("Expected ThrowAction from proactive selector")
        thrower_state = players[chosen_action.actor_id]

        defense_team = team_b_id if offense_team == team_a_id else team_a_id
        defenders = _live_for(defense_team)
        if not defenders:
            break
        target_state = select_target(
            defense_states=defenders,
            player_lookup=player_lookup,
            policy=policies[offense_team],
            recent_pressure_player_id=recent_pressure_by_team[offense_team],
            rng=rng,
            # V19a: the thrower's tactical IQ sets their court-read quality;
            # V19b: a "tactics" staff focus week sharpens the read.
            thrower_tactical_iq=_read_iq_for(thrower_state.player_id),
        )
        if target_state is None:
            break

        ball = _find_ball(balls, chosen_action.ball_id)
        seq_counter += 1
        seq = SequenceOfPlay(
            sequence_id=f"s{seq_counter}",
            match_id=match_id,
            game_id=None,
            thrower_id=thrower_state.player_id,
            thrower_team_id=offense_team,
            ball_id=ball.ball_id,
            release_time_ms=ticks * 100,
            material=profile.material,
        )
        ledger.open_sequence(seq)
        ball.state = BallState.LIVE_IN_FLIGHT
        ball.last_thrower_id = thrower_state.player_id

        # WT-20: a ball-holding target may block (regulation only — under No
        # Blocking the held ball no longer protects).
        target_holds_ball = any(
            b.activated
            and b.state == BallState.HELD
            and b.controller_player_id == target_state.player_id
            for b in balls
        )
        # WT-20 opening rush: during the opening exchange the catch economy is
        # shaded by both teams' rush_commit (disclosed sim-design — see the
        # design note above).
        if ticks < _OPENING_EXCHANGE_TICKS:
            opening_catch_factor = _RUSH_CATCH_READINESS.get(
                policies[defense_team].rush_commit, 1.0
            ) * _RUSH_THROW_PRESSURE.get(
                policies[offense_team].rush_commit, 1.0
            )
        else:
            opening_catch_factor = 1.0
        _probs, outcome_label = resolve_throw(
            seq=seq,
            thrower_state=thrower_state,
            target_state=target_state,
            player_lookup=player_lookup,
            # WT-6: the catch decision inside resolve_throw is the TARGET's
            # (defender's) decision, so it must use the DEFENDER's catch posture,
            # not the thrower's. Passing the offense policy inverted tactics —
            # choosing "go for catches" made the *opponent* catch your throws.
            # Target selection above correctly stays on the offense policy.
            policy=policies[target_state.team_id],
            rng=rng,
            target_holds_ball=target_holds_ball,
            no_blocking_active=no_blocking_state.active,
            opening_catch_factor=opening_catch_factor,
            # V19a: role fit + stamina erosion shade each side's action stats.
            thrower_shade=_shade_for(thrower_state.player_id),
            target_shade=_shade_for(target_state.player_id),
            # V19b: a "tactics" focus week raises the thrower's effective IQ
            # on every IQ channel (read noise is handled in select_target).
            thrower_tiq_bonus=float(
                preps.get(offense_team, {}).get("targeting_read_bonus", 0.0)
            ),
        )
        ruling = ledger.close_sequence(seq.sequence_id)
        events.append(sequence_event(seq))

        for pid in ruling.outs:
            player = players[pid]
            if player.status == OfficialPlayerStatus.ACTIVE:
                player.status = OfficialPlayerStatus.QUEUED
                events.append(
                    enqueue_out_player(
                        queues[player.team_id],
                        player_id=pid,
                        is_starter=player.is_starter,
                        match_id=match_id,
                    )
                )
                if player.team_id == team_a_id:
                    active_a -= 1
                else:
                    active_b -= 1
                # WT-20 / Section 24-core: queued players cannot hold balls —
                # every ball still in the out player's hands forfeits to the
                # opponent's side (the retrieval pass re-enters it next tick).
                # Pre-WT-20 these balls stayed stranded on the out player and
                # leaked out of play entirely.
                opponent_id = (
                    team_b_id if player.team_id == team_a_id else team_a_id
                )
                for held in balls:
                    if (
                        held.activated
                        and held.state == BallState.HELD
                        and held.controller_player_id == pid
                    ):
                        events.append(queue_player_holds_ball_forfeit(
                            held,
                            queued_player_id=pid,
                            match_id=match_id,
                            opponent_team_id=opponent_id,
                            event_id_suffix=f"-t{ticks}",
                        ))

        if ruling.catches:
            catcher_id = ruling.catches[0].catcher_id
            ball.controller_player_id = catcher_id
            ball.state = BallState.HELD
            catch_team = players[catcher_id].team_id
            ret_event, returning_pid = return_player_on_catch(
                queues[catch_team],
                sequence_id=seq.sequence_id,
                match_id=match_id,
            )
            if ret_event is not None and returning_pid is not None:
                events.append(ret_event)
                returning_player = players[returning_pid]
                returning_player.status = OfficialPlayerStatus.ACTIVE
                if returning_player.team_id == team_a_id:
                    active_a += 1
                else:
                    active_b += 1
                # DRAMATIC_CATCH: a live-ball catch that returned a teammate.
                catch_own = active_a if catch_team == team_a_id else active_b
                catch_opp = active_b if catch_team == team_a_id else active_a
                # WT-7: a live-ball catch-and-return happens on most on-target
                # throws (~24/match), so emitting a DRAMATIC_CATCH *moment* on
                # every one turns recognition into replay noise. Gate the moment
                # (presentation only) to genuinely clutch catches, deterministically:
                #   * the catching side is even-or-behind in the active count
                #     (catch_own <= catch_opp) — the same condition that feeds
                #     COMEBACK below; or
                #   * a side is down to its last live player
                #     (min active count <= 1) — the lone-survivor endgame the
                #     LATE_GAME_ESCAPE recognizer keys on (its survivor side is 1).
                # This is rate-only: it never changes who is out, who returns, the
                # active counts, or the COMEBACK bookkeeping below.
                is_clutch_catch = catch_own <= catch_opp or min(active_a, active_b) <= 1
                if is_clutch_catch:
                    moments.append(
                        DramaticCatch(
                            match_id=match_id,
                            tick=ticks,
                            catcher_id=catcher_id,
                            catcher_team_id=catch_team,
                            thrower_id=seq.thrower_id,
                            thrower_team_id=offense_team,
                            returning_player_id=returning_pid,
                            active_count_a=active_a,
                            active_count_b=active_b,
                        )
                    )
                # A clutch catch made while still behind feeds COMEBACK detection.
                # This bookkeeping is OUTCOME-relevant and must run on every
                # qualifying catch regardless of the presentation gate above.
                if catch_own <= catch_opp:
                    comeback_catches[catch_team] += 1
        elif outcome_label == "blocked":
            # WT-20: the blocked throw drops dead on the defense's side; the
            # retrieval pass re-enters it next tick.
            ball.state = BallState.ACTIVATED_FREE
            ball.controller_player_id = None
            ball.side = defense_team
        else:
            # The thrown ball lands on the defense's side. Only a defender
            # still standing AFTER the ruling may collect it — the pre-WT-20
            # code could hand it to the player the throw just put out,
            # stranding the ball on a queued player.
            new_holder = next(
                (d for d in defenders if d.is_live_for_hits()), None
            )
            if new_holder is not None:
                ball.state = BallState.HELD
                ball.controller_player_id = new_holder.player_id
                ball.side = defense_team
            else:
                ball.state = BallState.ACTIVATED_FREE
                ball.controller_player_id = None
                ball.side = defense_team

        # --- Phase 4a moment recognition (post-resolution state) ---
        worst_deficit[team_a_id] = max(worst_deficit[team_a_id], active_b - active_a)
        worst_deficit[team_b_id] = max(worst_deficit[team_b_id], active_a - active_b)
        if active_a == 1 and active_b == 1 and not one_v_one_emitted:
            a_live = _live_for(team_a_id)
            b_live = _live_for(team_b_id)
            if a_live and b_live:
                moments.append(
                    OneVOneFinale(
                        match_id=match_id,
                        tick=ticks,
                        player_a_id=a_live[0].player_id,
                        player_b_id=b_live[0].player_id,
                        tick_started=ticks,
                    )
                )
                one_v_one_emitted = True
        if active_a == 1 and active_b >= _LATE_ESCAPE_ATTACKERS and not late_escape_emitted[team_a_id]:
            a_live = _live_for(team_a_id)
            if a_live:
                moments.append(
                    LateGameEscape(
                        match_id=match_id,
                        tick=ticks,
                        survivor_id=a_live[0].player_id,
                        survivor_team_id=team_a_id,
                        attacker_team_id=team_b_id,
                        attacker_count=active_b,
                    )
                )
                late_escape_emitted[team_a_id] = True
        if active_b == 1 and active_a >= _LATE_ESCAPE_ATTACKERS and not late_escape_emitted[team_b_id]:
            b_live = _live_for(team_b_id)
            if b_live:
                moments.append(
                    LateGameEscape(
                        match_id=match_id,
                        tick=ticks,
                        survivor_id=b_live[0].player_id,
                        survivor_team_id=team_b_id,
                        attacker_team_id=team_a_id,
                        attacker_count=active_a,
                    )
                )
                late_escape_emitted[team_b_id] = True

        previous_burden_team_id = burden_state.team_id if burden_state is not None else previous_burden_team_id
        recent_pressure_by_team[defense_team] = target_state.player_id
        ticks += 1
        game_clock.advance(tick_seconds)
        if match_clock.limit_seconds > 0:
            match_clock.elapsed_seconds += tick_seconds

        if profile.material == BallMaterial.CLOTH and game_clock.expired():
            game_state.active_count_a = active_a
            game_state.active_count_b = active_b
            game_state.result = decide_cloth_game_by_active_count(game_state)
            break

    if active_a > 0 and active_b == 0:
        winner = team_a_id
    elif active_b > 0 and active_a == 0:
        winner = team_b_id
    elif game_state.result == OfficialGameResult.TEAM_A_WIN:
        winner = team_a_id
    elif game_state.result == OfficialGameResult.TEAM_B_WIN:
        winner = team_b_id
    else:
        winner = None

    # COMEBACK: the winner clawed back from a multi-player deficit on clutch catches.
    if (
        winner is not None
        and worst_deficit[winner] >= _COMEBACK_MIN_DEFICIT
        and comeback_catches[winner] >= 1
    ):
        moments.append(
            Comeback(
                match_id=match_id,
                tick=ticks,
                team_id=winner,
                deficit_at_low_point=worst_deficit[winner],
                catches_during_comeback=comeback_catches[winner],
            )
        )

    replay_state = _replay_state_from_live_engine(
        profile=profile,
        team_a_id=team_a_id,
        team_b_id=team_b_id,
        mode=game_state.mode,
        game_clock=game_clock,
        match_clock=match_clock,
        burden_state=burden_state,
        balls=balls,
        players=players,
        queues=queues,
        events=events,
        winner_team_id=winner,
    )

    return AutonomousGameResult(
        winner_team_id=winner,
        events=tuple(events),
        final_active_a=active_a,
        final_active_b=active_b,
        ticks=ticks,
        replay_state=replay_state,
        moment_events=tuple(moments),
    )


@dataclass
class AutonomousMatchResult:
    winner_team_id: str | None
    official_match_score: OfficialMatchScore
    events: Tuple[OfficialEvent, ...]
    ticks: int
    replay_state: OfficialReplayState
    moment_events: Tuple[MomentEvent, ...] = ()


def run_autonomous_match(
    *,
    profile: RulesetProfile,
    match_id: str,
    team_a_id: str,
    team_b_id: str,
    starters_a: Tuple[str, ...],
    starters_b: Tuple[str, ...],
    player_lookup: dict,
    policy_a: CoachPolicy,
    policy_b: CoachPolicy,
    seed: int,
    prep_a: dict | None = None,
    prep_b: dict | None = None,
) -> AutonomousMatchResult:
    """Simulate a full official match containing a series of timed games.

    Preserves run_autonomous_game as a single-game primitive by calling it repeatedly.
    ``prep_a``/``prep_b`` are the V19b staff-focus match preps (see
    run_autonomous_game).
    """
    # Order matters: "final" is a substring of "semifinal", so check the
    # narrower label first.
    if "semifinal" in match_id or "_p_r1_" in match_id:
        match_clock_limit = 30 * 60
    elif "final" in match_id:
        match_clock_limit = 40 * 60
    else:
        match_clock_limit = 24 * 60

    elapsed_match_seconds = 0
    game_number = 1
    games_list: List[OfficialGameScore] = []
    all_events: List[OfficialEvent] = []
    all_moments: List[MomentEvent] = []
    total_ticks = 0

    team_a_game_points = 0
    team_b_game_points = 0
    team_a_games_won = 0
    team_b_games_won = 0
    tied_games = 0
    no_point_games = 0

    last_game_res = None

    while elapsed_match_seconds < match_clock_limit:
        remaining = match_clock_limit - elapsed_match_seconds

        # Don't start a game that can't make meaningful progress.
        if remaining < 30:
            break

        # Cap the game clock so a single game can never overshoot the
        # remaining match window.
        game_clock_limit = min(profile.game_clock_seconds, remaining)

        adjusted_profile = profile
        if game_clock_limit != profile.game_clock_seconds:
            adjusted_profile = RulesetProfile(
                name=profile.name,
                material=profile.material,
                division=profile.division,
                ball_count=profile.ball_count,
                burden_majority_threshold=profile.burden_majority_threshold,
                roster_rule=profile.roster_rule,
                court=profile.court,
                game_clock_seconds=game_clock_limit,
                match_clock_seconds=profile.match_clock_seconds,
                throw_clock_seconds=profile.throw_clock_seconds,
                no_blocking_trigger_seconds=profile.no_blocking_trigger_seconds,
            )

        game_seed = derive_seed(seed, "game", str(game_number))

        game_res = run_autonomous_game(
            profile=adjusted_profile,
            match_id=match_id,
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            starters_a=starters_a,
            starters_b=starters_b,
            player_lookup=player_lookup,
            policy_a=policy_a,
            policy_b=policy_b,
            seed=game_seed,
            game_number=game_number,
            elapsed_match_seconds=elapsed_match_seconds,
            match_clock_limit=match_clock_limit,
            prep_a=prep_a,
            prep_b=prep_b,
        )

        last_game_res = game_res
        # Tag each moment with its game so replay surfaces can place it: the
        # moment's ``tick`` is a per-game engine tick and is ambiguous across
        # a multi-game match without this. Presentation metadata only.
        all_moments.extend(
            dataclass_replace(moment, game_number=game_number)
            for moment in game_res.moment_events
        )
        game_elapsed = game_res.replay_state.game_clock.elapsed_seconds
        elapsed_match_seconds += game_elapsed
        total_ticks += game_res.ticks

        g_winner = game_res.winner_team_id

        if profile.material == BallMaterial.CLOTH:
            is_tie = (g_winner is None)
            pts_a, pts_b = cloth_game_points(g_winner, is_tie, team_a_id, team_b_id)
            res_type = "tie" if is_tie else "cloth_active_count" if game_res.final_active_a > 0 and game_res.final_active_b > 0 else "elimination"
        else:
            pts_a, pts_b = foam_game_points(g_winner, team_a_id, team_b_id)
            res_type = "elimination" if g_winner is not None else "no_point"

        team_a_game_points += pts_a
        team_b_game_points += pts_b

        if g_winner == team_a_id:
            team_a_games_won += 1
        elif g_winner == team_b_id:
            team_b_games_won += 1
        elif res_type == "tie":
            tied_games += 1
        elif res_type == "no_point":
            no_point_games += 1

        games_list.append(OfficialGameScore(
            game_number=game_number,
            winner_team_id=g_winner,
            team_a_points=pts_a,
            team_b_points=pts_b,
            result_type=res_type,
            final_active_a=game_res.final_active_a,
            final_active_b=game_res.final_active_b,
            mode=game_res.replay_state.mode,
            elapsed_seconds=game_elapsed,
        ))

        game_events = []
        for ev in game_res.events:
            adjusted_ev = OfficialEvent(
                event_id=f"g{game_number}_{ev.event_id}",
                kind=ev.kind,
                match_id=ev.match_id,
                rule_refs=ev.rule_refs,
                replay_summary=ev.replay_summary,
                payload=ev.payload,
                game_id=f"g{game_number}",
                sequence_id=ev.sequence_id,
                ball_ids=ev.ball_ids,
                player_ids=ev.player_ids,
                team_ids=ev.team_ids,
                official_payload_version=ev.official_payload_version,
                ruleset_version=ev.ruleset_version,
                rulebook_version=ev.rulebook_version,
            )
            game_events.append(adjusted_ev)

        all_events.extend(game_events)
        game_number += 1

    match_winner = match_winner_from_points(
        team_a_game_points,
        team_b_game_points,
        team_a_id,
        team_b_id,
    )

    match_score = OfficialMatchScore(
        team_a_id=team_a_id,
        team_b_id=team_b_id,
        team_a_game_points=team_a_game_points,
        team_b_game_points=team_b_game_points,
        team_a_games_won=team_a_games_won,
        team_b_games_won=team_b_games_won,
        tied_games=tied_games,
        no_point_games=no_point_games,
        games=tuple(games_list),
        winner_team_id=match_winner,
    )

    if last_game_res:
        final_replay = last_game_res.replay_state
        game_score_view = OfficialGameScoreView(
            team_a_id=team_a_id,
            team_b_id=team_b_id,
            team_a_games=team_a_game_points,
            team_b_games=team_b_game_points,
            team_a_ties=tied_games,
            team_b_ties=tied_games,
            no_point_games=no_point_games,
        )
        match_clock_view = OfficialClockView(
            limit_seconds=match_clock_limit,
            elapsed_seconds=elapsed_match_seconds,
        )
        rule_calls = []
        for event in all_events:
            for label in event.rule_labels():
                rule_calls.append(
                    OfficialRuleCallView(rule_label=label, summary=event.replay_summary)
                )

        replay_state = OfficialReplayState(
            ruleset=final_replay.ruleset,
            rulebook_version=final_replay.rulebook_version,
            official_payload_version=final_replay.official_payload_version,
            match_clock=match_clock_view,
            game_clock=final_replay.game_clock,
            game_score=game_score_view,
            mode=final_replay.mode,
            burden=final_replay.burden,
            balls=final_replay.balls,
            teams=final_replay.teams,
            player_statuses=final_replay.player_statuses,
            rule_calls=tuple(rule_calls),
            events=tuple(all_events),
        )
    else:
        # Fallback if no games were simulated
        from .replay_contracts import empty_replay_state
        replay_state = empty_replay_state(profile.name)

    return AutonomousMatchResult(
        winner_team_id=match_winner,
        official_match_score=match_score,
        events=tuple(all_events),
        ticks=total_ticks,
        replay_state=replay_state,
        moment_events=tuple(all_moments),
    )


class OfficialMatchEngineDriver:
    """`EngineDriver` over the shipping multi-set official match engine.

    This is the engine real official-ruleset careers play through
    (``OfficialEngineAdapter.run_generic`` -> ``run_autonomous_match``). Both the
    tier health probe and the OVR-sensitivity gate drive THIS, not the
    single-game ``official_driver.OfficialDriver`` stub (which hardcodes
    ``moment_events=()`` and only ever resolves one game). Phase 4a wires the
    probe + gate onto this driver so the measured OVR curve and moment coverage
    reflect what new careers actually play.
    """

    tier_id = "official_match"

    def __init__(self, profile: "RulesetProfile | None" = None, ruleset: str = "official_foam") -> None:
        if profile is None:
            from .rulesets import RulesetSelection
            profile = RulesetSelection(ruleset).to_profile()
        self.profile = profile

    def run(self, match_input):  # type: ignore[no-untyped-def]
        from .engine_driver import DriverMatchOutput

        res = run_autonomous_match(
            profile=self.profile,
            match_id=match_input.match_id,
            team_a_id=match_input.team_a_id,
            team_b_id=match_input.team_b_id,
            starters_a=match_input.starters_a,
            starters_b=match_input.starters_b,
            player_lookup=match_input.player_lookup,
            policy_a=match_input.policy_a,
            policy_b=match_input.policy_b,
            seed=match_input.seed,
            # V19b staff-focus match preps ride the free-form config channel.
            prep_a=match_input.config.get("prep_a"),
            prep_b=match_input.config.get("prep_b"),
        )
        score = res.official_match_score
        return DriverMatchOutput(
            events=res.events,
            winner_team_id=res.winner_team_id,
            final_active_a=getattr(score, "team_a_game_points", 0),
            final_active_b=getattr(score, "team_b_game_points", 0),
            moment_events=res.moment_events,
            replay_state=res.replay_state,
        )
