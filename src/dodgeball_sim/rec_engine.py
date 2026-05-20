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
from typing import Any, Dict, List, Tuple

from .ball_state import BallState, OfficialBall
from .catch_queue import CatchQueueState, enqueue_out_player, return_player_on_catch
from .engine_driver import DriverMatchInput, DriverMatchOutput
from .fatigue import FatigueParams, FatigueState, accumulate, effectiveness, recover
from .flood_throws import FloodThrowTracker, PendingThrow
from .models import CoachPolicy, Player
from .moment_events import MomentEvent
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


@dataclass
class _MatchRuntime:
    """Mutable per-match runtime state held by the driver."""

    rng: random.Random
    rules: TierRules
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

        # Fatigue: derive params from stamina
        fatigue_params: Dict[str, FatigueParams] = {}
        fatigue: Dict[str, FatigueState] = {}
        for pid in list(mi.starters_a) + list(mi.starters_b):
            stamina = float(mi.player_lookup[pid].ratings.stamina)
            fatigue_params[pid] = FatigueParams(conditioning_curve=stamina)
            fatigue[pid] = FatigueState.fresh()

        queues = {
            mi.team_a_id: CatchQueueState(team_id=mi.team_a_id),
            mi.team_b_id: CatchQueueState(team_id=mi.team_b_id),
        }

        return _MatchRuntime(
            rng=rng,
            rules=rules,
            players=players,
            balls=balls,
            queues=queues,
            fatigue=fatigue,
            fatigue_params=fatigue_params,
            stall_a=StallTimerState.fresh(),
            stall_b=StallTimerState.fresh(),
            flood_tracker=FloodThrowTracker(),
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
        # 1. Choose throwers
        throwers_by_team = self._select_throwers(rt, mi, team_a, team_b)

        # 2. Record throws into flood tracker; resolve each
        for team_id, thrower_ids in throwers_by_team.items():
            for thrower_id in thrower_ids:
                rt.flood_tracker.record(
                    PendingThrow(thrower_id=thrower_id, team_id=team_id, tick=rt.tick)
                )
                self._resolve_throw(rt, mi, thrower_id, team_id, team_a, team_b)

        # 3. Stall handling
        self._update_stall(rt, team_a, team_b, threw_a=bool(throwers_by_team.get(team_a)),
                           threw_b=bool(throwers_by_team.get(team_b)))

        # 4. Fatigue recovery/accumulation
        threw_pids = {
            pid for pids in throwers_by_team.values() for pid in pids
        }
        for pid, state in list(rt.fatigue.items()):
            if pid in threw_pids:
                rt.fatigue[pid] = accumulate(
                    state, action_cost=0.05, params=rt.fatigue_params[pid]
                )
            else:
                rt.fatigue[pid] = recover(
                    state, seconds_idle=TICK_SECONDS, params=rt.fatigue_params[pid]
                )

    def _select_throwers(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        team_a: str,
        team_b: str,
    ) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {team_a: [], team_b: []}
        for team_id in (team_a, team_b):
            active = [
                p for p in rt.players.values()
                if p.team_id == team_id and p.status == OfficialPlayerStatus.ACTIVE
            ]
            if not active:
                continue
            candidates = []
            for p in active:
                eff = effectiveness(rt.fatigue[p.player_id])
                if rt.rng.random() < 0.4 * eff:
                    candidates.append(p.player_id)
            result[team_id] = candidates[:3]
        return result

    def _resolve_throw(
        self,
        rt: _MatchRuntime,
        mi: DriverMatchInput,
        thrower_id: str,
        thrower_team_id: str,
        team_a: str,
        team_b: str,
    ) -> None:
        opp_team = team_b if thrower_team_id == team_a else team_a
        opp_active = [
            p for p in rt.players.values()
            if p.team_id == opp_team and p.status == OfficialPlayerStatus.ACTIVE
        ]
        if not opp_active:
            return

        thrower = mi.player_lookup[thrower_id]
        target_state = rt.rng.choice(opp_active)
        target = mi.player_lookup[target_state.player_id]

        thrower_eff = effectiveness(rt.fatigue[thrower_id])
        target_eff = effectiveness(rt.fatigue[target_state.player_id])

        if rt.rng.random() < 0.05:
            self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
            rt.events.append({"type": "headshot_thrower_out", "thrower": thrower_id})
            reset_on_throw_call(rt, thrower_team_id, team_a)
            return

        accuracy = (thrower.ratings.accuracy / 100.0) * thrower_eff
        dodge = (target.ratings.dodge / 100.0) * target_eff
        catch_skill = (target.ratings.catch / 100.0) * target_eff

        roll = rt.rng.random()
        if roll < catch_skill * 0.4:
            self._mark_out(rt, thrower_id, thrower_team_id, team_a, team_b)
            catcher_team = target_state.team_id
            ret_event, returning_pid = return_player_on_catch(
                rt.queues[catcher_team],
                sequence_id=f"t{rt.tick}",
                match_id=mi.match_id,
            )
            if ret_event is not None and returning_pid is not None:
                rt.events.append({"type": "catch_return", "catcher": target_state.player_id})
                returning = rt.players[returning_pid]
                returning.status = OfficialPlayerStatus.ACTIVE
        elif roll < catch_skill * 0.4 + accuracy * (1.0 - dodge):
            self._mark_out(rt, target_state.player_id, target_state.team_id, team_a, team_b)
            rt.events.append({"type": "hit", "thrower": thrower_id, "target": target_state.player_id})
        else:
            rt.events.append({"type": "miss", "thrower": thrower_id, "target": target_state.player_id})

        reset_on_throw_call(rt, thrower_team_id, team_a)

    def _mark_out(
        self,
        rt: _MatchRuntime,
        player_id: str,
        team_id: str,
        team_a: str,
        team_b: str,
    ) -> None:
        player = rt.players.get(player_id)
        if player is None or player.status != OfficialPlayerStatus.ACTIVE:
            return
        player.status = OfficialPlayerStatus.QUEUED
        enqueue_out_player(
            rt.queues[team_id],
            player_id=player_id,
            is_starter=player.is_starter,
            match_id="rt",
        )

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
            rt.events.append({"type": "stall_reset", "from": team_a})
        if should_reset_balls(rt.stall_b):
            for b in rt.balls:
                if b.side == team_b:
                    b.side = team_a
            rt.stall_b = StallTimerState.fresh()
            rt.events.append({"type": "stall_reset", "from": team_b})


def reset_on_throw_call(rt: _MatchRuntime, team_id: str, team_a: str) -> None:
    if team_id == team_a:
        rt.stall_a = reset_on_throw(rt.stall_a)
    else:
        rt.stall_b = reset_on_throw(rt.stall_b)


__all__ = ["RecTier1Driver"]
