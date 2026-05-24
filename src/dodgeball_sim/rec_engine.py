"""Rec Tier 1 driver — Local Rec League match loop.

Implements EngineDriver against TIER_1_RULES (brief §3.5). Composes:
  - existing primitives: ball_state, catch_queue, sequence, player_state
  - new primitives: fatigue, stall_timer, flood_throws

Does NOT use burden, discipline, or no_blocking — those are V11/USAD only.

Moment-event emission lives in this driver's `_emit_moments` hook
(populated in Task 8). Task 7 produces resolvable matches with events
but no moment_events tuple yet.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .ball_state import BallState, OfficialBall
from .catch_queue import CatchQueueState, enqueue_out_player, return_player_on_catch
from .engine_driver import DriverMatchInput, DriverMatchOutput
from .fatigue import FatigueParams, FatigueState, accumulate, effectiveness, recover
from .flood_throws import FloodThrowTracker, PendingThrow
from .models import (
    Approach,
    CatchPosture,
    CoachPolicy,
    OpeningRushCommit,
    OpeningRushTarget,
    Player,
    PlayerRatings,
    TargetFocus,
)
from .moment_events import (
    Comeback,
    DramaticCatch,
    FloodThrow,
    GassedCollapse,
    LateGameEscape,
    MomentEvent,
    OneVOneFinale,
)
from .player_state import OfficialPlayerState, OfficialPlayerStatus
from .rulesets import BallMaterial
from .stall_timer import (
    StallTimerState,
    advance_holding,
    reset_on_throw,
    should_reset_balls,
)
from .tier_1_rules import TIER_1_RULES, TierRules


TICK_SECONDS: float = 6.0
"""Engine tick in seconds; matches official_engine.py for consistency."""

ON_COURT_EXERTION_COST: float = 0.03
"""Background exertion per tick for active players."""

THROW_EXERTION_COST: float = 0.09
"""Additional exertion for a throw attempt."""

ACTIVE_RECOVERY_SECONDS: float = 0.5
"""Short between-rally recovery for players still on court."""

APPROACH_GATE_MULT = {
    Approach.AGGRESSIVE: 0.85,
    Approach.MIXED: 1.0,
    Approach.PATIENT: 1.20,
}

_POSTURE_MULTIPLIERS = {
    CatchPosture.GO_FOR_CATCHES: {"catch": 1.4, "block": 1.0, "dodge": 0.7},
    CatchPosture.OPPORTUNISTIC: {"catch": 1.0, "block": 1.0, "dodge": 1.0},
    CatchPosture.PLAY_SAFE: {"catch": 0.7, "block": 1.0, "dodge": 1.4},
}

_OPENING_RUSH_SPRINTERS = {
    OpeningRushCommit.ALL_IN: 6,
    OpeningRushCommit.BALANCED: 4,
    OpeningRushCommit.HOLD_BACK: 2,
}

_OPENING_RUSH_THROW_CAP = {
    OpeningRushCommit.ALL_IN: 4,
    OpeningRushCommit.BALANCED: 3,
    OpeningRushCommit.HOLD_BACK: 2,
}


def _fatigue_params_for_ratings(ratings: PlayerRatings) -> FatigueParams:
    return FatigueParams(conditioning_curve=float(ratings.conditioning_curve))


def _response_weights_for_courage(*, courage: float) -> tuple[float, float, float]:
    c = max(0.0, min(100.0, float(courage)))
    catch_share = 0.05 + 0.55 * (c / 100.0)
    block_share = 0.30 - 0.10 * abs(c - 50.0) / 50.0
    dodge_share = max(0.0, 1.0 - catch_share - block_share)
    return catch_share, block_share, dodge_share


def _response_branch_for_courage(*, courage: float, response_roll: float) -> str:
    catch_share, block_share, _dodge_share = _response_weights_for_courage(courage=courage)
    if response_roll < catch_share:
        return "catch"
    if response_roll < catch_share + block_share:
        return "block"
    return "dodge"


def _response_branch_for_policy(*, courage: float, posture: CatchPosture | str, response_roll: float) -> str:
    catch_share, block_share, dodge_share = _response_weights_for_courage(courage=courage)
    posture_value = posture if isinstance(posture, CatchPosture) else CatchPosture(str(posture))
    multipliers = _POSTURE_MULTIPLIERS[posture_value]
    catch_share *= multipliers["catch"]
    block_share *= multipliers["block"]
    dodge_share *= multipliers["dodge"]
    total = catch_share + block_share + dodge_share
    catch_share /= total
    block_share /= total
    if response_roll < catch_share:
        return "catch"
    if response_roll < catch_share + block_share:
        return "block"
    return "dodge"


def _should_throw_under_iq(
    *,
    iq: float,
    expected_value: float,
    stall_seconds: float,
    stall_cap: float,
    gate_multiplier: float = 1.0,
) -> bool:
    iq_norm = max(0.0, min(100.0, float(iq))) / 100.0
    stall_pressure = max(0.0, min(1.0, stall_seconds / max(stall_cap, 0.001)))
    if stall_pressure >= 0.8:
        return True
    threshold = (0.05 + 0.35 * iq_norm) * gate_multiplier * (1.0 - stall_pressure)
    return expected_value >= threshold


@dataclass
class _MatchRuntime:
    """Mutable per-match runtime state held by the driver."""

    rng: random.Random
    rules: TierRules
    match_id: str
    players: Dict[str, OfficialPlayerState]
    balls: List[OfficialBall]
    queues: Dict[str, CatchQueueState]
    fatigue: Dict[str, FatigueState]
    fatigue_params: Dict[str, FatigueParams]
    stall_a: StallTimerState
    stall_b: StallTimerState
    flood_tracker: FloodThrowTracker
    events: List[Any] = field(default_factory=list)
    moment_events: List[MomentEvent] = field(default_factory=list)
    tick: int = 0
    elapsed_seconds: float = 0.0
    late_escape_emitted_for: Dict[str, bool] = field(default_factory=dict)
    one_v_one_emitted: bool = False
    comeback_emitted_for: Dict[str, bool] = field(default_factory=dict)
    low_water_active: Dict[str, int] = field(default_factory=dict)
    comeback_catches: Dict[str, int] = field(default_factory=dict)
    recent_targets_by_team: Dict[str, List[str]] = field(default_factory=dict)
    opening_rush_by_team: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class RecTier1Driver:
    """Local Rec League driver. Implements EngineDriver."""

    tier_id: str = TIER_1_RULES.tier_id

    def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
        rt = self._init_runtime(match_input)
        team_a, team_b = match_input.team_a_id, match_input.team_b_id

        while not self._match_over(rt, team_a, team_b):
            self._tick(rt, match_input, team_a, team_b)
            rt.tick += 1
            rt.elapsed_seconds += TICK_SECONDS
            if rt.elapsed_seconds >= rt.rules.time_cap_seconds:
                break
            if rt.tick > 500:  # hard safety cap
                break

        active_a = sum(
            1
            for p in rt.players.values()
            if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
        )
        active_b = sum(
            1
            for p in rt.players.values()
            if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
        )

        if active_a > 0 and active_b == 0:
            winner = team_a
        elif active_b > 0 and active_a == 0:
            winner = team_b
        elif active_a > active_b:
            winner = team_a
        elif active_b > active_a:
            winner = team_b
        else:
            winner = None  # draw

        return DriverMatchOutput(
            events=tuple(rt.events),
            winner_team_id=winner,
            final_active_a=active_a,
            final_active_b=active_b,
            moment_events=tuple(rt.moment_events),
            replay_state=None,
        )

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def _init_runtime(self, mi: DriverMatchInput) -> _MatchRuntime:
        rng = random.Random(mi.seed)
        rules = TIER_1_RULES

        # Players
        players: Dict[str, OfficialPlayerState] = {}
        for pid in mi.starters_a:
            players[pid] = OfficialPlayerState(
                player_id=pid,
                team_id=mi.team_a_id,
                status=OfficialPlayerStatus.ACTIVE,
                is_starter=True,
            )
        for pid in mi.starters_b:
            players[pid] = OfficialPlayerState(
                player_id=pid,
                team_id=mi.team_b_id,
                status=OfficialPlayerStatus.ACTIVE,
                is_starter=True,
            )

        # Balls — split evenly at opening rush. Tier 1 always uses foam.
        per_side = rules.balls_per_side_at_rush
        balls: List[OfficialBall] = []
        for i in range(per_side):
            balls.append(
                OfficialBall(
                    ball_id=f"ball_a_{i}",
                    material=BallMaterial.FOAM,
                    side=mi.team_a_id,
                )
            )
        for i in range(per_side):
            balls.append(
                OfficialBall(
                    ball_id=f"ball_b_{i}",
                    material=BallMaterial.FOAM,
                    side=mi.team_b_id,
                )
            )

        # Fatigue: sourced from the v2 conditioning_curve field.
        fatigue_params: Dict[str, FatigueParams] = {}
        fatigue: Dict[str, FatigueState] = {}
        for pid in list(mi.starters_a) + list(mi.starters_b):
            fatigue_params[pid] = _fatigue_params_for_ratings(mi.player_lookup[pid].ratings)
            fatigue[pid] = FatigueState.fresh()

        queues = {
            mi.team_a_id: CatchQueueState(team_id=mi.team_a_id),
            mi.team_b_id: CatchQueueState(team_id=mi.team_b_id),
        }

        return _MatchRuntime(
            rng=rng,
            rules=rules,
            match_id=mi.match_id,
            players=players,
            balls=balls,
            queues=queues,
            fatigue=fatigue,
            fatigue_params=fatigue_params,
            stall_a=StallTimerState.fresh(),
            stall_b=StallTimerState.fresh(),
            flood_tracker=FloodThrowTracker(),
            late_escape_emitted_for={mi.team_a_id: False, mi.team_b_id: False},
            comeback_emitted_for={mi.team_a_id: False, mi.team_b_id: False},
            low_water_active={
                mi.team_a_id: len(mi.starters_a),
                mi.team_b_id: len(mi.starters_b),
            },
            comeback_catches={mi.team_a_id: 0, mi.team_b_id: 0},
            recent_targets_by_team={mi.team_a_id: [], mi.team_b_id: []},
            opening_rush_by_team={
                mi.team_a_id: self._opening_rush(
                    team_id=mi.team_a_id,
                    starters=mi.starters_a,
                    policy=self._policy_for_team(mi, mi.team_a_id),
                ),
                mi.team_b_id: self._opening_rush(
                    team_id=mi.team_b_id,
                    starters=mi.starters_b,
                    policy=self._policy_for_team(mi, mi.team_b_id),
                ),
            },
        )

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def _match_over(self, rt: _MatchRuntime, team_a: str, team_b: str) -> bool:
        a_alive = any(
            p.status == OfficialPlayerStatus.ACTIVE and p.team_id == team_a
            for p in rt.players.values()
        )
        b_alive = any(
            p.status == OfficialPlayerStatus.ACTIVE and p.team_id == team_b
            for p in rt.players.values()
        )
        return not (a_alive and b_alive)

    def _tick(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        team_a: str,
        team_b: str,
    ) -> None:
        # Determine team evaluation order for this tick to eliminate 0-edge asymmetry
        first_team = team_a if rt.rng.random() < 0.5 else team_b
        second_team = team_b if first_team == team_a else team_a

        # 1. Choose throwers in randomized order
        throwers_by_team = self._select_throwers(rt, mi, first_team, second_team)

        # 2. Record throws into flood tracker; resolve each in randomized order
        for team_id in (first_team, second_team):
            thrower_ids = throwers_by_team.get(team_id, [])
            is_synced = len(thrower_ids) >= 2
            for thrower_id in thrower_ids:
                rt.flood_tracker.record(
                    PendingThrow(thrower_id=thrower_id, team_id=team_id, tick=rt.tick)
                )
                self._resolve_throw(rt, mi, thrower_id, team_id, team_a, team_b, is_synced=is_synced)

        # 3. Stall handling
        self._update_stall(rt, team_a, team_b, threw_a=bool(throwers_by_team.get(team_a)),
                           threw_b=bool(throwers_by_team.get(team_b)))

        # 4. Fatigue recovery/accumulation
        threw_pids = {
            pid for pids in throwers_by_team.values() for pid in pids
        }
        for pid, state in list(rt.fatigue.items()):
            player_state = rt.players[pid]
            if player_state.status == OfficialPlayerStatus.ACTIVE:
                next_state = accumulate(
                    state,
                    action_cost=ON_COURT_EXERTION_COST,
                    params=rt.fatigue_params[pid],
                )
                if pid in threw_pids:
                    next_state = accumulate(
                        next_state,
                        action_cost=THROW_EXERTION_COST,
                        params=rt.fatigue_params[pid],
                    )
                else:
                    next_state = recover(
                        next_state,
                        seconds_idle=ACTIVE_RECOVERY_SECONDS,
                        params=rt.fatigue_params[pid],
                    )
                rt.fatigue[pid] = next_state
            else:
                rt.fatigue[pid] = recover(
                    state, seconds_idle=TICK_SECONDS, params=rt.fatigue_params[pid]
                )

        # 5. Moment detection: flood, late escape, 1v1, comeback
        flood = rt.flood_tracker.detect_flood(tick=rt.tick)
        if flood is not None:
            rt.moment_events.append(
                FloodThrow(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    thrower_team_id=flood.team_id,
                    thrower_ids=flood.thrower_ids,
                )
            )

        active_a = sum(
            1 for p in rt.players.values()
            if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
        )
        active_b = sum(
            1 for p in rt.players.values()
            if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
        )

        # Late escape
        if active_a == 1 and active_b >= 3 and not rt.late_escape_emitted_for[team_a]:
            survivor = next(
                p for p in rt.players.values()
                if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
            )
            rt.moment_events.append(
                LateGameEscape(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    survivor_id=survivor.player_id,
                    survivor_team_id=team_a,
                    attacker_team_id=team_b,
                    attacker_count=active_b,
                )
            )
            rt.late_escape_emitted_for[team_a] = True
        if active_b == 1 and active_a >= 3 and not rt.late_escape_emitted_for[team_b]:
            survivor = next(
                p for p in rt.players.values()
                if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
            )
            rt.moment_events.append(
                LateGameEscape(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    survivor_id=survivor.player_id,
                    survivor_team_id=team_b,
                    attacker_team_id=team_a,
                    attacker_count=active_a,
                )
            )
            rt.late_escape_emitted_for[team_b] = True

        # 1v1 finale
        if active_a == 1 and active_b == 1 and not rt.one_v_one_emitted:
            a_alive = next(
                p for p in rt.players.values()
                if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
            )
            b_alive = next(
                p for p in rt.players.values()
                if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
            )
            rt.moment_events.append(
                OneVOneFinale(
                    match_id=mi.match_id,
                    tick=rt.tick,
                    player_a_id=a_alive.player_id,
                    player_b_id=b_alive.player_id,
                    tick_started=rt.tick,
                )
            )
            rt.one_v_one_emitted = True

        # Update low-water mark and check comeback
        rt.low_water_active[team_a] = min(rt.low_water_active[team_a], active_a)
        rt.low_water_active[team_b] = min(rt.low_water_active[team_b], active_b)
        for team_id, opp in [(team_a, active_b), (team_b, active_a)]:
            low = rt.low_water_active[team_id]
            my_active = active_a if team_id == team_a else active_b
            other_starters = len(
                mi.starters_b if team_id == team_a else mi.starters_a
            )
            deficit_at_low = other_starters - low
            if (
                deficit_at_low >= 2
                and my_active >= opp - 3
                and not rt.comeback_emitted_for[team_id]
            ):
                rt.moment_events.append(
                    Comeback(
                        match_id=mi.match_id,
                        tick=rt.tick,
                        team_id=team_id,
                        deficit_at_low_point=deficit_at_low,
                        catches_during_comeback=rt.comeback_catches[team_id],
                    )
                )
                rt.comeback_emitted_for[team_id] = True

    def _select_throwers(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        first_team: str,
        second_team: str,
    ) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {first_team: [], second_team: []}
        for team_id in (first_team, second_team):
            active = [
                p for p in rt.players.values()
                if p.team_id == team_id and p.status == OfficialPlayerStatus.ACTIVE
            ]
            if not active:
                continue
            stall_state = rt.stall_a if team_id == mi.team_a_id else rt.stall_b
            policy = self._policy_for_team(mi, team_id)
            gate_multiplier = APPROACH_GATE_MULT[policy.approach]
            opening_rush = rt.opening_rush_by_team.get(team_id, {})
            opening_sprinters = set(opening_rush.get("sprinter_ids", []))
            candidates = []
            for p in active:
                if rt.tick == 0 and policy.rush_commit == OpeningRushCommit.HOLD_BACK and p.player_id not in opening_sprinters:
                    continue
                eff = effectiveness(rt.fatigue[p.player_id])
                player = mi.player_lookup[p.player_id]
                expected_value = (player.ratings.accuracy / 100.0) * eff
                if not _should_throw_under_iq(
                    iq=player.ratings.throw_selection_iq,
                    expected_value=expected_value,
                    stall_seconds=stall_state.seconds_holding,
                    stall_cap=rt.rules.stall_cap_seconds,
                    gate_multiplier=gate_multiplier,
                ):
                    continue
                if rt.rng.random() < 0.4 * eff:
                    candidates.append(p.player_id)
            throw_cap = 3
            if rt.tick == 0:
                throw_cap = _OPENING_RUSH_THROW_CAP[policy.rush_commit]
            result[team_id] = candidates[:throw_cap]
        return result

    def _resolve_throw(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        thrower_id: str,
        thrower_team_id: str,
        team_a: str,
        team_b: str,
        *,
        is_synced: bool,
    ) -> None:
        opp_team = team_b if thrower_team_id == team_a else team_a
        opp_active = [
            p for p in rt.players.values()
            if p.team_id == opp_team and p.status == OfficialPlayerStatus.ACTIVE
        ]
        if not opp_active:
            return

        offense_policy = self._policy_for_team(mi, thrower_team_id)
        thrower = mi.player_lookup[thrower_id]
        target_scores = self._target_scores(
            defense_states=opp_active,
            player_lookup=mi.player_lookup,
            policy=offense_policy,
            ball_holder_ids=self._ball_holder_ids(rt, opp_team),
            recent_targets=rt.recent_targets_by_team.get(opp_team, []),
        )
        target_state = target_scores[0][2]
        target = mi.player_lookup[target_state.player_id]
        rt.recent_targets_by_team.setdefault(opp_team, [])
        rt.recent_targets_by_team[opp_team] = [
            target_state.player_id,
            *[
                player_id
                for player_id in rt.recent_targets_by_team[opp_team]
                if player_id != target_state.player_id
            ],
        ][:6]

        thrower_eff = effectiveness(rt.fatigue[thrower_id])
        target_eff = effectiveness(rt.fatigue[target_state.player_id])
        rush_context = self._rush_context_for_throw(rt, mi, thrower_team_id, thrower_id)
        sync_context = {
            "is_synced": is_synced,
            "sync_modifier": 0.05 if is_synced else 0.0,
        }
        event_base = {
            "tick": rt.tick,
            "thrower": thrower_id,
            "thrower_team": thrower_team_id,
            "target": target_state.player_id,
            "target_team": target_state.team_id,
            "policy_snapshot": offense_policy.as_dict(),
            "target_selection": {
                "scores": [
                    {"player_id": state.player_id, "score": round(score, 4)}
                    for score, _player_id, state in target_scores[:3]
                ],
                "recent_pressure_player_id": (
                    rt.recent_targets_by_team.get(opp_team, [None, None])[1]
                    if len(rt.recent_targets_by_team.get(opp_team, [])) > 1
                    else None
                ),
            },
            "rush_context": rush_context,
            "sync_context": sync_context,
            "fatigue": {
                "thrower_fatigue": round(rt.fatigue[thrower_id].value, 4),
                "target_fatigue": round(rt.fatigue[target_state.player_id].value, 4),
            },
        }

        headshot_prob = max(0.0, 0.08 - 0.05 * (thrower.ratings.throw_selection_iq / 100.0))
        if rt.rng.random() < headshot_prob:
            state_diff = self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
            rt.events.append(
                {
                    **event_base,
                    "type": "headshot_thrower_out",
                    "target": None,
                    "target_team": None,
                    "catch_decision": None,
                    "state_diff": state_diff,
                }
            )
            reset_on_throw_call(rt, thrower_team_id, team_a)
            return

        accuracy = (thrower.ratings.accuracy / 100.0) * thrower_eff
        dodge = (target.ratings.dodge / 100.0) * target_eff
        catch_skill = (target.ratings.catch / 100.0) * target_eff

        connect_roll = rt.rng.random()
        base = accuracy / max(0.0001, accuracy + (1.0 - dodge))
        connect_prob = base ** 0.7
        if connect_roll >= connect_prob:
            rt.events.append(
                {
                    **event_base,
                    "type": "miss",
                    "catch_decision": None,
                    "state_diff": {},
                }
            )
            reset_on_throw_call(rt, thrower_team_id, team_a)
            return

        catch_decision = {
            "attempt": False,
            "catch_posture": self._policy_for_team(mi, opp_team).catch_posture.value,
            "normalized_catch": round(target.ratings.normalized_catch(), 4),
            "normalized_dodge": round(target.ratings.normalized_dodge(), 4),
        }
        branch = _response_branch_for_policy(
            courage=target.ratings.catch_courage,
            posture=self._policy_for_team(mi, opp_team).catch_posture,
            response_roll=rt.rng.random(),
        )
        if branch == "catch":
            catch_decision["attempt"] = True
            if rt.rng.random() < catch_skill:
                state_diff = self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
                catcher_team = target_state.team_id
                ret_event, returning_pid = return_player_on_catch(
                    rt.queues[catcher_team],
                    sequence_id=f"t{rt.tick}",
                    match_id=mi.match_id,
                )
                if ret_event is not None and returning_pid is not None:
                    rt.events.append(
                        {
                            **event_base,
                            "type": "catch_return",
                            "catch_decision": catch_decision,
                            "state_diff": state_diff,
                            "returning_player_id": returning_pid,
                        }
                    )
                    returning = rt.players[returning_pid]
                    returning.status = OfficialPlayerStatus.ACTIVE
                    rt.comeback_catches[catcher_team] = rt.comeback_catches.get(catcher_team, 0) + 1
                    self._emit_dramatic_catch(
                        rt,
                        mi,
                        target_state,
                        thrower_id,
                        thrower_team_id,
                        returning_pid,
                        team_a,
                        team_b,
                    )
                else:
                    rt.events.append(
                        {
                            **event_base,
                            "type": "catch_clean",
                            "catch_decision": catch_decision,
                            "state_diff": state_diff,
                        }
                    )
            else:
                state_diff = self._mark_out(rt, target_state.player_id, target_state.team_id, team_a, team_b)
                rt.events.append(
                    {
                        **event_base,
                        "type": "catch_failed_hit",
                        "catch_decision": catch_decision,
                        "state_diff": state_diff,
                    }
                )
        elif branch == "block":
            rt.events.append(
                {
                    **event_base,
                    "type": "block",
                    "catch_decision": catch_decision,
                    "state_diff": {},
                }
            )
        else:
            if rt.rng.random() < dodge:
                rt.events.append(
                    {
                        **event_base,
                        "type": "dodge",
                        "catch_decision": catch_decision,
                        "state_diff": {},
                    }
                )
            else:
                state_diff = self._mark_out(rt, target_state.player_id, target_state.team_id, team_a, team_b)
                rt.events.append(
                    {
                        **event_base,
                        "type": "hit",
                        "catch_decision": catch_decision,
                        "state_diff": state_diff,
                    }
                )

        reset_on_throw_call(rt, thrower_team_id, team_a)

    def _policy_for_team(self, mi: DriverMatchInput, team_id: str) -> CoachPolicy:
        raw = mi.policy_a if team_id == mi.team_a_id else mi.policy_b
        if isinstance(raw, CoachPolicy):
            return raw
        if isinstance(raw, Mapping):
            return CoachPolicy.from_dict(dict(raw))
        return CoachPolicy()

    def _ball_holder_ids(self, rt: _MatchRuntime, team_id: str) -> set[str]:
        active_players = sorted(
            (
                player.player_id
                for player in rt.players.values()
                if player.team_id == team_id and player.status == OfficialPlayerStatus.ACTIVE
            )
        )
        held_ball_count = sum(1 for ball in rt.balls if ball.side == team_id)
        return set(active_players[:held_ball_count])

    def _recency_weight(self, recent_targets: Sequence[str], target_id: str) -> float:
        for index, recent_target_id in enumerate(recent_targets):
            if recent_target_id != target_id:
                continue
            return max(0.0, 1.0 - 0.5 * index)
        return 0.0

    def _select_target_state(
        self,
        *,
        defense_states: Sequence[OfficialPlayerState],
        player_lookup: Mapping[str, Player],
        policy: CoachPolicy,
        ball_holder_ids: set[str],
        recent_targets: Sequence[str],
    ) -> OfficialPlayerState:
        scored = self._target_scores(
            defense_states=defense_states,
            player_lookup=player_lookup,
            policy=policy,
            ball_holder_ids=ball_holder_ids,
            recent_targets=recent_targets,
        )
        return scored[0][2]

    def _target_scores(
        self,
        *,
        defense_states: Sequence[OfficialPlayerState],
        player_lookup: Mapping[str, Player],
        policy: CoachPolicy,
        ball_holder_ids: set[str],
        recent_targets: Sequence[str],
    ) -> list[tuple[float, str, OfficialPlayerState]]:
        scored: list[tuple[float, str, OfficialPlayerState]] = []
        for state in defense_states:
            player = player_lookup[state.player_id]
            overall = player.overall_skill() / 100.0
            base_targetability = 1.0 - player.ratings.normalized_dodge()
            if policy.target_focus == TargetFocus.THEIR_STARS:
                score = 0.7 * overall + 0.3 * base_targetability
            elif policy.target_focus == TargetFocus.BALL_HOLDERS:
                score = 0.7 * (1.0 if state.player_id in ball_holder_ids else 0.0) + 0.3 * base_targetability
            else:
                score = 0.7 * (1.0 - self._recency_weight(recent_targets, state.player_id)) + 0.3 * base_targetability
            scored.append((score, state.player_id, state))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return scored

    def _opening_rush(
        self,
        *,
        team_id: str,
        starters: Sequence[str],
        policy: CoachPolicy,
    ) -> dict[str, Any]:
        sprinter_count = min(len(starters), _OPENING_RUSH_SPRINTERS[policy.rush_commit])
        sprinter_ids = list(starters[:sprinter_count])
        hold_back_ids = list(starters[sprinter_count:])
        prefix = (team_id or "x").lower()[0]
        if policy.rush_target == OpeningRushTarget.CENTER:
            target_pool = ("ball_center_0", "ball_center_1", "ball_center_2")
            ball_targets = {
                player_id: target_pool[index % len(target_pool)]
                for index, player_id in enumerate(sprinter_ids)
            }
        elif policy.rush_target == OpeningRushTarget.STRONGEST_SIDE:
            target_pool = (f"ball_{prefix}_0", f"ball_{prefix}_1", f"ball_{prefix}_2")
            ball_targets = {
                player_id: target_pool[index % len(target_pool)]
                for index, player_id in enumerate(sprinter_ids)
            }
        else:
            ball_targets = {
                player_id: f"ball_{prefix}_{index}"
                for index, player_id in enumerate(sprinter_ids)
            }
        return {
            "sprinter_ids": sprinter_ids,
            "hold_back_ids": hold_back_ids,
            "ball_targets": ball_targets,
        }

    def _rush_context_for_throw(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        team_id: str,
        thrower_id: str,
    ) -> dict[str, Any]:
        policy = self._policy_for_team(mi, team_id)
        opening = rt.opening_rush_by_team.get(team_id, {})
        is_active_rush = rt.tick == 0 and thrower_id in set(opening.get("sprinter_ids", []))
        proximity_modifier = 0.0
        if is_active_rush:
            if policy.rush_commit == OpeningRushCommit.ALL_IN:
                proximity_modifier = 0.1
            elif policy.rush_commit == OpeningRushCommit.BALANCED:
                proximity_modifier = 0.06
            else:
                proximity_modifier = 0.03
        return {
            "active": is_active_rush,
            "rush_commit": policy.rush_commit.value,
            "rush_target": policy.rush_target.value,
            "ball_target": opening.get("ball_targets", {}).get(thrower_id),
            "proximity_modifier": proximity_modifier,
            "fatigue_delta": 0.04 if is_active_rush else 0.0,
        }

    def _emit_dramatic_catch(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        target_state: OfficialPlayerState,
        thrower_id: str,
        thrower_team_id: str,
        returning_pid: str,
        team_a: str,
        team_b: str,
    ) -> None:
        active_a_now = sum(
            1 for player in rt.players.values()
            if player.team_id == team_a and player.status == OfficialPlayerStatus.ACTIVE
        )
        active_b_now = sum(
            1 for player in rt.players.values()
            if player.team_id == team_b and player.status == OfficialPlayerStatus.ACTIVE
        )
        rt.moment_events.append(
            DramaticCatch(
                match_id=mi.match_id,
                tick=rt.tick,
                catcher_id=target_state.player_id,
                catcher_team_id=target_state.team_id,
                thrower_id=thrower_id,
                thrower_team_id=thrower_team_id,
                returning_player_id=returning_pid,
                active_count_a=active_a_now,
                active_count_b=active_b_now,
            )
        )

    def _mark_out(
        self,
        rt: _MatchRuntime,
        player_id: str,
        team_id: str,
        team_a: str,
        team_b: str,
    ) -> dict[str, Any]:
        player = rt.players.get(player_id)
        if player is None or player.status != OfficialPlayerStatus.ACTIVE:
            return {}
        # Gassed collapse check before status change
        fstate = rt.fatigue.get(player_id)
        if fstate is not None and fstate.is_gassed():
            rt.moment_events.append(
                GassedCollapse(
                    match_id=rt.match_id,
                    tick=rt.tick,
                    player_id=player_id,
                    team_id=team_id,
                    fatigue_pct=fstate.value,
                )
            )
        player.status = OfficialPlayerStatus.QUEUED
        enqueue_out_player(
            rt.queues[team_id],
            player_id=player_id,
            is_starter=player.is_starter,
            match_id=rt.match_id,
        )
        return {"player_out": {"team": team_id, "player_id": player_id}}

    def _update_stall(
        self,
        rt: _MatchRuntime,
        team_a: str,
        team_b: str,
        *,
        threw_a: bool,
        threw_b: bool,
    ) -> None:
        a_controls_all = all(b.side == team_a for b in rt.balls)
        b_controls_all = all(b.side == team_b for b in rt.balls)

        if threw_a:
            rt.stall_a = reset_on_throw(rt.stall_a)
        else:
            rt.stall_a = advance_holding(rt.stall_a, seconds=TICK_SECONDS, side_controls_all_balls=a_controls_all)
        if threw_b:
            rt.stall_b = reset_on_throw(rt.stall_b)
        else:
            rt.stall_b = advance_holding(rt.stall_b, seconds=TICK_SECONDS, side_controls_all_balls=b_controls_all)

        if should_reset_balls(rt.stall_a):
            for b in rt.balls:
                if b.side == team_a:
                    b.side = team_b
            rt.stall_a = StallTimerState.fresh()
            rt.events.append({"type": "stall_reset", "tick": rt.tick, "from": team_a})
        if should_reset_balls(rt.stall_b):
            for b in rt.balls:
                if b.side == team_b:
                    b.side = team_a
            rt.stall_b = StallTimerState.fresh()
            rt.events.append({"type": "stall_reset", "tick": rt.tick, "from": team_b})


def reset_on_throw_call(rt: _MatchRuntime, team_id: str, team_a: str) -> None:
    if team_id == team_a:
        rt.stall_a = reset_on_throw(rt.stall_a)
    else:
        rt.stall_b = reset_on_throw(rt.stall_b)


__all__ = [
    "APPROACH_GATE_MULT",
    "RecTier1Driver",
    "_response_branch_for_policy",
    "_should_throw_under_iq",
]
