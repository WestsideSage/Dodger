"""Scripted official-engine harness.

This is the orchestration adapter for V11. It does NOT own rules, tactics,
timing, or randomness; it composes the focused modules. Phase 8A only
supports *scripted* actions for use in tests and for building the
:class:`~dodgeball_sim.replay_contracts.OfficialReplayState` shape before
autonomous action selection is added (Phase 8C).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from .ball_state import (
    BallState,
    OfficialBall,
    activate_ball,
    initial_balls,
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
from .official_events import OfficialEvent
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

from .models import Approach, CoachPolicy, Player
from .official_resolution import resolve_throw
from .official_tactics import select_target


@dataclass
class AutonomousGameResult:
    winner_team_id: str | None
    events: Tuple[OfficialEvent, ...]
    final_active_a: int
    final_active_b: int
    ticks: int
    replay_state: OfficialReplayState


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
    a_starters = list(starters_a)
    b_starters = list(starters_b)
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
    match_clock = OfficialMatchClock(limit_seconds=profile.match_clock_seconds)
    game_state = OfficialGameState(
        game_number=1,
        profile=profile,
        clock=game_clock,
        active_count_a=len(starters_a),
        active_count_b=len(starters_b),
    )
    active_a = len(starters_a)
    active_b = len(starters_b)
    seq_counter = 0
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

    offense_team = team_a_id
    policies = {team_a_id: policy_a, team_b_id: policy_b}
    tick_seconds = 6
    ticks = 0

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
            events.append(discretion.to_official_event(match_id=match_id))
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
            and game_state.trigger_no_blocking()
        ):
            no_blocking_state, no_blocking_event = activate_no_blocking(
                source=NoBlockingSource.GAME_TIME_LIMIT,
                ball_reset=NoBlockingBallReset.THREE_PER_SIDE,
                time_limit_seconds=180,
                match_id=match_id,
            )
            events.append(no_blocking_event)
            game_state.mode = OfficialGameMode.NO_BLOCKING

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

        resolve_throw(
            seq=seq,
            thrower_state=thrower_state,
            target_state=target_state,
            player_lookup=player_lookup,
            policy=policies[offense_team],
            rng=rng,
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
        else:
            ball.state = BallState.HELD
            new_holder = defenders[0] if defenders else None
            if new_holder is not None:
                ball.controller_player_id = new_holder.player_id
                ball.side = defense_team

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
    )
