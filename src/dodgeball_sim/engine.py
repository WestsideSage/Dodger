from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from .config import BalanceConfig, DEFAULT_CONFIG, DifficultyProfile, get_config
from .development import fatigue_consistency_modifier, pressure_context
from .events import MatchEvent
from .meta import MetaPatch
from .models import CoachPolicy, MatchSetup, Player, PlayerState, Team, TeamState
from .rng import DeterministicRNG


@dataclass(frozen=True)
class ThrowCalculation:
    accuracy_eff: float
    dodge_eff: float
    catch_eff: float
    power_eff: float
    p_on_target: float
    p_catch: float
    context_terms: Dict[str, float]


@dataclass(frozen=True)
class MatchResult:
    events: Tuple[MatchEvent, ...]
    winner_team_id: str | None
    box_score: Dict[str, Any]
    final_tick: int
    seed: int
    config_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "winner_team_id": self.winner_team_id,
            "box_score": self.box_score,
            "final_tick": self.final_tick,
            "seed": self.seed,
            "config_version": self.config_version,
        }


class MatchEngine:
    """Deterministic dodgeball match simulator."""

    def __init__(self, config: BalanceConfig | None = None):
        self.config = config or DEFAULT_CONFIG

    def run(
        self,
        setup: MatchSetup,
        seed: int,
        difficulty: str = "pro",
        meta_patch: MetaPatch | None = None,
    ) -> MatchResult:
        cfg = get_config(setup.config_version)
        rng = DeterministicRNG(seed + cfg.base_seed_offset)
        difficulty_profile = self._difficulty_profile(cfg, difficulty)
        event_id = 0
        tick = 0
        team_states = {team.id: self._init_team_state(team) for team in (setup.team_a, setup.team_b)}
        possession = setup.team_a.id
        recent_thrower_by_team: Dict[str, str] = {}
        events: List[MatchEvent] = []

        events.append(
            MatchEvent(
                event_id=event_id,
                tick=tick,
                seed=seed,
                event_type="match_start",
                phase="init",
                actors={
                    "team_a": setup.team_a.id,
                    "team_b": setup.team_b.id,
                },
                context={
                    "config_version": cfg.version,
                    "difficulty": difficulty_profile.name,
                    "meta_patch": meta_patch.context_payload() if meta_patch else None,
                    "team_policies": {
                        setup.team_a.id: setup.team_a.coach_policy.as_dict(),
                        setup.team_b.id: setup.team_b.coach_policy.as_dict(),
                    },
                },
                probabilities={},
                rolls={},
                outcome={"message": "Match initialized"},
                state_diff={},
            )
        )

        event_id += 1
        while not self._is_match_over(team_states.values()) and event_id < cfg.max_events and tick < cfg.max_ticks:
            offense = team_states[possession]
            defense = team_states[self._other_team_id(team_states, possession)]
            throw_resolution = self._process_throw(
                cfg=cfg,
                offense=offense,
                defense=defense,
                rng=rng,
                difficulty=difficulty_profile,
                tick=tick,
                event_id=event_id,
                seed=seed,
                meta_patch=meta_patch,
                recent_pressure_player_id=recent_thrower_by_team.get(defense.team.id),
            )
            events.append(throw_resolution)
            tick = throw_resolution.tick
            recent_thrower_by_team[offense.team.id] = str(throw_resolution.actors["thrower"])
            possession = defense.team.id if throw_resolution.outcome.get("possession_change", False) else offense.team.id
            event_id += 1

        winner_id = self._winner_id(team_states.values())
        events.append(
            MatchEvent(
                event_id=event_id,
                tick=tick,
                seed=seed,
                event_type="match_end",
                phase="complete",
                actors={"winner": winner_id},
                context={"reason": self._end_reason(team_states.values(), tick, cfg)},
                probabilities={},
                rolls={},
                outcome={"winner": winner_id},
                state_diff={},
            )
        )

        box_score = self._build_box_score(team_states, winner_id)
        return MatchResult(
            events=tuple(events),
            winner_team_id=winner_id,
            box_score=box_score,
            final_tick=tick,
            seed=seed,
            config_version=cfg.version,
        )

    def _difficulty_profile(self, cfg: BalanceConfig, difficulty: str) -> DifficultyProfile:
        if difficulty not in cfg.difficulty_profiles:
            raise KeyError(f"Unknown difficulty '{difficulty}'")
        return cfg.difficulty_profiles[difficulty]

    def _init_team_state(self, team: Team) -> TeamState:
        roster = [PlayerState(player=p, fatigue=0.0) for p in team.players]
        return TeamState(team=team, roster=roster)

    def _process_throw(
        self,
        cfg: BalanceConfig,
        offense: TeamState,
        defense: TeamState,
        rng: DeterministicRNG,
        difficulty: DifficultyProfile,
        tick: int,
        event_id: int,
        seed: int,
        meta_patch: MetaPatch | None = None,
        recent_pressure_player_id: str | None = None,
    ) -> MatchEvent:
        offense_policy = offense.team.coach_policy.normalized()
        defense_policy = defense.team.coach_policy.normalized()
        thrower, throw_context = self._select_thrower(offense, offense_policy, rng, difficulty)
        target, target_context = self._select_target(
            defense,
            offense_policy,
            rng,
            difficulty,
            recent_pressure_player_id=recent_pressure_player_id,
            thrower_state=thrower,
            offense_team=offense.team,
        )
        rush_context = self._rush_context(cfg, offense_policy, rng)

        is_synced = rng.unit() < offense_policy.sync_throws
        sync_modifier = 0.05 if is_synced else 0.0

        calc = compute_throw_probabilities(
            thrower.player,
            target.player,
            cfg,
            offense.team.chemistry,
            defense.team.chemistry,
            thrower.fatigue,
            target.fatigue,
            pressure_modifier=self._pressure_modifier(thrower, offense, defense),
            rush_modifier=rush_context["proximity_modifier"],
            sync_modifier=sync_modifier,
            dodge_penalty_modifier=0.0 if meta_patch is None else meta_patch.dodge_penalty_modifier,
        )

        roll_on_target = rng.unit()
        on_target = roll_on_target <= calc.p_on_target
        rolls = {"on_target": round(roll_on_target, 6)}
        probabilities = {"p_on_target": round(calc.p_on_target, 6), "p_catch": round(calc.p_catch, 6)}
        actors = {
            "offense_team": offense.team.id,
            "defense_team": defense.team.id,
            "thrower": thrower.player.id,
            "target": target.player.id,
        }
        context = {
            "tick": tick,
            "thrower_selection": throw_context,
            "target_selection": target_context,
            "difficulty": difficulty.name,
            "policy_snapshot": offense_policy.as_dict(),
            "chemistry_delta": round(offense.team.chemistry - defense.team.chemistry, 4),
            "meta_patch": meta_patch.context_payload() if meta_patch else None,
            "rush_context": rush_context,
            "sync_context": {"is_synced": is_synced, "sync_modifier": round(sync_modifier, 4)},
            "calc": {
                "accuracy_eff": round(calc.accuracy_eff, 3),
                "dodge_eff": round(calc.dodge_eff, 3),
                "catch_eff": round(calc.catch_eff, 3),
                "power_eff": round(calc.power_eff, 3),
                "context_terms": calc.context_terms,
            },
            "fatigue": {
                "thrower_fatigue": round(thrower.fatigue, 3),
                "target_fatigue": round(target.fatigue, 3),
                "thrower_consistency_modifier": fatigue_consistency_modifier(thrower.player.traits.consistency),
                "target_consistency_modifier": fatigue_consistency_modifier(target.player.traits.consistency),
            },
        }
        context.update(pressure_context(thrower.player, self._pressure_reason(offense, defense)))

        state_diff: Dict[str, Any] = {}
        outcome: Dict[str, Any] = {}
        possession_change = True

        from .lineup import is_liability
        thrower_liable = is_liability(offense.team.players, thrower.player)
        target_liable = is_liability(defense.team.players, target.player)
        
        thrower.throws_attempted += 1
        self._apply_fatigue(thrower, delta=1.0, meta_patch=meta_patch, is_thrower=True, is_liable=thrower_liable)
        if rush_context["fatigue_delta"]:
            self._apply_fatigue(thrower, delta=rush_context["fatigue_delta"], meta_patch=meta_patch, is_thrower=True, is_liable=thrower_liable)
        self._apply_fatigue(target, delta=0.5, meta_patch=meta_patch, is_thrower=False, is_liable=target_liable)

        if not on_target:
            target.dodges_made += 1
            defense.dodges_made += 1
            outcome.update({"resolution": "dodged"})
        else:
            attempt_catch, catch_meta = self._should_attempt_catch(target, defense_policy)
            context["catch_decision"] = catch_meta
            if attempt_catch:
                roll_catch = rng.unit()
                rolls["catch"] = round(roll_catch, 6)
                if roll_catch <= calc.p_catch:
                    target.catches_made += 1
                    defense.catches_made += 1
                    thrower.is_out = True
                    defense.outs_recorded += 1
                    thrower.caught_throws += 1
                    possession_change = True
                    outcome.update({"resolution": "catch", "player_out": thrower.player.id})
                    state_diff = {"player_out": {"team": offense.team.id, "player_id": thrower.player.id}}
                else:
                    target.is_out = True
                    offense.outs_recorded += 1
                    thrower.hits_landed += 1
                    offense.hits_landed += 1
                    outcome.update({"resolution": "failed_catch", "player_out": target.player.id})
                    state_diff = {"player_out": {"team": defense.team.id, "player_id": target.player.id}}
            else:
                target.is_out = True
                offense.outs_recorded += 1
                thrower.hits_landed += 1
                offense.hits_landed += 1
                outcome.update({"resolution": "hit", "player_out": target.player.id})
                state_diff = {"player_out": {"team": defense.team.id, "player_id": target.player.id}}

        tempo_step = 1 + int(offense_policy.tempo * cfg.tempo_tick_bonus)
        if is_synced:
            tempo_step += 1
        tick += tempo_step
        outcome["tick_advance"] = tempo_step
        outcome["possession_change"] = possession_change

        return MatchEvent(
            event_id=event_id,
            tick=tick,
            seed=seed,
            event_type="throw",
            phase="live",
            actors=actors,
            context=context,
            probabilities=probabilities,
            rolls=rolls,
            outcome=outcome,
            state_diff=state_diff,
        )

    def _apply_fatigue(
        self,
        player_state: PlayerState,
        delta: float,
        meta_patch: MetaPatch | None = None,
        is_thrower: bool = False,
        is_liable: bool = False,
    ) -> None:
        scaled_delta = delta * fatigue_consistency_modifier(player_state.player.traits.consistency)
        if is_liable:
            scaled_delta *= 1.15
        if meta_patch is not None:
            scaled_delta *= 1.0 + meta_patch.fatigue_rate_modifier
            if is_thrower:
                scaled_delta *= 1.0 + (
                    meta_patch.power_stamina_cost_modifier
                    * player_state.player.ratings.normalized_power()
                )
        player_state.fatigue = min(
            player_state.player.ratings.fatigue_ceiling(),
            player_state.fatigue + scaled_delta,
        )

    def _select_thrower(
        self,
        team_state: TeamState,
        policy: CoachPolicy,
        rng: DeterministicRNG,
        difficulty: DifficultyProfile,
    ) -> Tuple[PlayerState, Dict[str, Any]]:
        candidates = team_state.living_players()
        if not candidates:
            raise RuntimeError("No available throwers")
        scores = []
        noise_roll = rng.unit()
        for player_state in candidates:
            ratings = player_state.player.ratings
            base = policy.risk_tolerance * ratings.normalized_power() + (1 - policy.risk_tolerance) * ratings.normalized_accuracy()
            base -= player_state.fatigue * 0.005
            score = (1 - difficulty.decision_noise) * base + difficulty.decision_noise * noise_roll
            scores.append((score, player_state))
        scores.sort(key=lambda item: (item[0], item[1].player.id), reverse=True)
        winner = scores[0][1]
        meta = {
            "scores": [
                {
                    "player_id": ps.player.id,
                    "score": round(sc, 4),
                    "fatigue": round(ps.fatigue, 3),
                }
                for sc, ps in scores
            ],
            "noise_roll": round(noise_roll, 6),
        }
        return winner, meta

    def _select_target(
        self,
        defense: TeamState,
        policy: CoachPolicy,
        rng: DeterministicRNG,
        difficulty: DifficultyProfile,
        recent_pressure_player_id: str | None = None,
        thrower_state: PlayerState | None = None,
        offense_team: Team | None = None,
    ) -> Tuple[PlayerState, Dict[str, Any]]:
        from .lineup import is_liability
        candidates = defense.living_players()
        if not candidates:
            raise RuntimeError("No available targets")
        noise_roll = rng.unit()
        
        tactical_iq_eff = 0.5
        if thrower_state and offense_team:
            tactical_iq = thrower_state.player.ratings.tactical_iq
            if is_liability(offense_team.players, thrower_state.player):
                tactical_iq *= 0.8
            tactical_iq_eff = tactical_iq / 100.0
        player_noise = difficulty.decision_noise * (1.0 - tactical_iq_eff * 0.5)

        scores = []
        for player_state in candidates:
            player = player_state.player
            normalized_overall = player.overall() / 100.0
            vulnerability = 1 - player.ratings.normalized_dodge()
            ball_holder_pressure = (
                (policy.target_ball_holder - 0.5)
                if player.id == recent_pressure_player_id
                else 0.0
            )
            base = (
                policy.target_stars * normalized_overall
                + (1 - policy.target_stars) * vulnerability
                + policy.target_ball_holder * ball_holder_pressure
            )
            score = (1 - player_noise) * base + player_noise * noise_roll
            scores.append((score, player_state, normalized_overall, vulnerability, ball_holder_pressure))
        scores.sort(key=lambda item: (item[0], item[1].player.id), reverse=True)
        winner = scores[0][1]
        meta = {
            "scores": [
                {
                    "player_id": ps.player.id,
                    "score": round(sc, 4),
                    "normalized_overall": round(overall, 4),
                    "vulnerability": round(vulnerability, 4),
                    "ball_holder_pressure": round(ball_holder_pressure, 4),
                    "fatigue": round(ps.fatigue, 3),
                }
                for sc, ps, overall, vulnerability, ball_holder_pressure in scores
            ],
            "recent_pressure_player_id": recent_pressure_player_id,
            "noise_roll": round(noise_roll, 6),
        }
        return winner, meta

    def _should_attempt_catch(self, target: PlayerState, policy: CoachPolicy) -> Tuple[bool, Dict[str, Any]]:
        normalized_catch = target.player.ratings.normalized_catch()
        normalized_dodge = target.player.ratings.normalized_dodge()
        base_threshold = 0.3 + 0.4 * (1 - policy.risk_tolerance)
        catch_bias_adjustment = (0.5 - policy.catch_bias) * 0.4
        threshold = base_threshold + catch_bias_adjustment
        dodge_guard = normalized_dodge - 0.15 + catch_bias_adjustment
        attempt = normalized_catch >= max(threshold, dodge_guard)
        meta = {
            "threshold": round(threshold, 4),
            "base_threshold": round(base_threshold, 4),
            "catch_bias": round(policy.catch_bias, 4),
            "catch_bias_adjustment": round(catch_bias_adjustment, 4),
            "dodge_guard": round(dodge_guard, 4),
            "normalized_catch": round(normalized_catch, 4),
            "normalized_dodge": round(normalized_dodge, 4),
            "attempt": attempt,
        }
        return attempt, meta

    def _rush_context(self, cfg: BalanceConfig, policy: CoachPolicy, rng: DeterministicRNG) -> Dict[str, Any]:
        active = rng.unit() < policy.rush_frequency
        raw_modifier = (policy.rush_proximity - 0.5) * cfg.rush_accuracy_modifier_max if active else 0.0
        fatigue_delta = max(0.0, policy.rush_proximity - 0.5) * cfg.rush_fatigue_cost_max if active else 0.0
        return {
            "active": active,
            "rush_frequency": round(policy.rush_frequency, 4),
            "rush_proximity": round(policy.rush_proximity, 4),
            "proximity_modifier": round(raw_modifier, 4),
            "fatigue_delta": round(fatigue_delta, 4),
            "rng_namespace": None,
        }

    def _winner_id(self, teams: Iterable[TeamState]) -> str | None:
        living_counts = {team.team.id: len(team.living_players()) for team in teams}
        sorted_counts = sorted(living_counts.items(), key=lambda item: item[1], reverse=True)
        if len(sorted_counts) < 2 or sorted_counts[0][1] == sorted_counts[1][1]:
            return None
        return sorted_counts[0][0]

    def _is_match_over(self, teams: Iterable[TeamState]) -> bool:
        return any(len(team.living_players()) == 0 for team in teams)

    def _other_team_id(self, teams: Dict[str, TeamState], team_id: str) -> str:
        for tid in teams.keys():
            if tid != team_id:
                return tid
        raise KeyError("Only one team present in match")

    def _end_reason(self, teams: Iterable[TeamState], tick: int, cfg: BalanceConfig) -> str:
        if any(len(team.living_players()) == 0 for team in teams):
            return "all_opponents_out"
        if tick >= cfg.max_ticks:
            return "max_ticks"
        return "event_limit"

    def _build_box_score(self, teams: Dict[str, TeamState], winner_id: str | None) -> Dict[str, Any]:
        box = {
            "teams": {},
            "winner": winner_id,
        }
        for team_id, state in teams.items():
            players = {}
            for player_state in state.roster:
                players[player_state.player.id] = {
                    "name": player_state.player.name,
                    "throws": player_state.throws_attempted,
                    "hits": player_state.hits_landed,
                    "catches": player_state.catches_made,
                    "dodges": player_state.dodges_made,
                    "caught": player_state.caught_throws,
                    "is_out": player_state.is_out,
                }
            box["teams"][team_id] = {
                "name": state.team.name,
                "totals": {
                    "outs_recorded": state.outs_recorded,
                    "hits": state.hits_landed,
                    "catches": state.catches_made,
                    "dodges": state.dodges_made,
                    "living": len(state.living_players()),
                },
                "players": players,
            }
        return box

    def _pressure_reason(self, offense: TeamState, defense: TeamState) -> str | None:
        if len(offense.living_players()) <= 2:
            return "last_player_alive"
        if len(defense.living_players()) == 1:
            return "final_elimination_opportunity"
        return None

    def _pressure_modifier(self, thrower: PlayerState, offense: TeamState, defense: TeamState) -> float:
        payload = pressure_context(thrower.player, self._pressure_reason(offense, defense))
        if not payload.get("pressure_active", False):
            return 0.0
        return float(payload.get("pressure_modifier", 0.0))


def compute_throw_probabilities(
    thrower: Player,
    target: Player,
    cfg: BalanceConfig,
    offense_chemistry: float,
    defense_chemistry: float,
    thrower_fatigue: float,
    target_fatigue: float,
    pressure_modifier: float = 0.0,
    rush_modifier: float = 0.0,
    sync_modifier: float = 0.0,
    dodge_penalty_modifier: float = 0.0,
) -> ThrowCalculation:
    accuracy_eff = _fatigued_value(thrower.ratings.accuracy, thrower_fatigue, cfg.fatigue_hit_modifier)
    dodge_eff = _fatigued_value(target.ratings.dodge, target_fatigue, cfg.fatigue_dodge_modifier)
    dodge_eff *= max(0.0, 1.0 - dodge_penalty_modifier)
    catch_eff = _fatigued_value(target.ratings.catch, target_fatigue, cfg.fatigue_catch_modifier)
    power_eff = _fatigued_value(thrower.ratings.power, thrower_fatigue, cfg.fatigue_hit_modifier)

    chemistry_term = (offense_chemistry - defense_chemistry) * cfg.chemistry_influence * 100
    context_terms = {
        "chemistry": round(chemistry_term, 4),
        "pressure": round(pressure_modifier, 4),
        "rush": round(rush_modifier, 4),
        "sync": round(sync_modifier, 4),
        "dodge_penalty_modifier": round(dodge_penalty_modifier, 4),
    }

    p_on_target = _sigmoid(
        ((accuracy_eff - dodge_eff) / cfg.accuracy_scale) + chemistry_term + pressure_modifier + rush_modifier + sync_modifier
    )
    p_catch = _sigmoid(((catch_eff - power_eff * cfg.power_to_catch_scale) / cfg.catch_scale) - chemistry_term)

    return ThrowCalculation(
        accuracy_eff=accuracy_eff,
        dodge_eff=dodge_eff,
        catch_eff=catch_eff,
        power_eff=power_eff,
        p_on_target=p_on_target,
        p_catch=p_catch,
        context_terms=context_terms,
    )


def _fatigued_value(value: float, fatigue: float, modifier: float) -> float:
    return max(1.0, value - fatigue * modifier)


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


def run_match(match_setup: MatchSetup, seed: int, difficulty: str = "pro") -> MatchResult:
    engine = MatchEngine()
    return engine.run(match_setup, seed=seed, difficulty=difficulty)


__all__ = [
    "MatchEngine",
    "MatchResult",
    "ThrowCalculation",
    "compute_throw_probabilities",
    "run_match",
]








