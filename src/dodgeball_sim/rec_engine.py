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
    late_escape_emitted_for: Dict[str, bool] = field(default_factory=dict)
    one_v_one_emitted: bool = False
    comeback_emitted_for: Dict[str, bool] = field(default_factory=dict)
    low_water_active: Dict[str, int] = field(default_factory=dict)
    comeback_catches: Dict[str, int] = field(default_factory=dict)


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
            late_escape_emitted_for={mi.team_a_id: False, mi.team_b_id: False},
            comeback_emitted_for={mi.team_a_id: False, mi.team_b_id: False},
            low_water_active={
                mi.team_a_id: len(mi.starters_a),
                mi.team_b_id: len(mi.starters_b),
            },
            comeback_catches={mi.team_a_id: 0, mi.team_b_id: 0},
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
                deficit_at_low >= 3
                and my_active >= opp
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
                # Count toward comeback
                rt.comeback_catches[catcher_team] = rt.comeback_catches.get(catcher_team, 0) + 1
                # Emit DramaticCatch
                active_a_now = sum(
                    1 for p in rt.players.values()
                    if p.team_id == team_a and p.status == OfficialPlayerStatus.ACTIVE
                )
                active_b_now = sum(
                    1 for p in rt.players.values()
                    if p.team_id == team_b and p.status == OfficialPlayerStatus.ACTIVE
                )
                rt.moment_events.append(
                    DramaticCatch(
                        match_id=mi.match_id,
                        tick=rt.tick,
                        catcher_id=target_state.player_id,
                        catcher_team_id=catcher_team,
                        thrower_id=thrower_id,
                        thrower_team_id=thrower_team_id,
                        returning_player_id=returning_pid,
                        active_count_a=active_a_now,
                        active_count_b=active_b_now,
                    )
                )
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
        # Gassed collapse check before status change
        fstate = rt.fatigue.get(player_id)
        if fstate is not None and fstate.is_gassed():
            rt.moment_events.append(
                GassedCollapse(
                    match_id="rt",
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
