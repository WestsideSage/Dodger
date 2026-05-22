"""Tactics layer for the official engine.

Picks *who* throws, *who* gets targeted, and *whether* a target attempts a
catch. Mirrors the public weighting model of :mod:`engine` so ``CoachPolicy``
remains honest in official-rules play (no hidden boosts; rating + policy
weights only).

All functions take an injected :class:`random.Random` so determinism is
testable.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .models import CoachPolicy, Player
from .player_state import OfficialPlayerState, OfficialPlayerStatus


def _active_players(
    states: Sequence[OfficialPlayerState], team_id: str
) -> List[OfficialPlayerState]:
    return [s for s in states if s.team_id == team_id and s.is_live_for_hits()]


def select_thrower(
    *,
    candidates: Sequence[OfficialPlayerState],
    player_lookup: Dict[str, Player],
    policy: CoachPolicy,
    rng: random.Random,
) -> Optional[OfficialPlayerState]:
    """Choose a thrower from live players holding a ball.

    Score = risk_tolerance * normalized_power + (1 - risk_tolerance) * normalized_accuracy.
    Ties broken by player_id for determinism.
    """

    if not candidates:
        return None
    scored: List[Tuple[float, str, OfficialPlayerState]] = []
    noise = rng.random() * 0.05  # small deterministic jitter
    for state in candidates:
        player = player_lookup[state.player_id]
        ratings = player.ratings
        base = (
            policy.risk_tolerance * ratings.normalized_power()
            + (1.0 - policy.risk_tolerance) * ratings.normalized_accuracy()
        )
        score = base + noise * (rng.random() - 0.5)
        scored.append((score, state.player_id, state))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2]


def select_target(
    *,
    defense_states: Sequence[OfficialPlayerState],
    player_lookup: Dict[str, Player],
    policy: CoachPolicy,
    recent_pressure_player_id: Optional[str],
    rng: random.Random,
) -> Optional[OfficialPlayerState]:
    """Choose an opposing target. Mirrors engine._select_target weighting."""

    if not defense_states:
        return None
    scored: List[Tuple[float, str, OfficialPlayerState]] = []
    noise = rng.random() * 0.05
    for state in defense_states:
        player = player_lookup[state.player_id]
        normalized_overall = player.overall_skill() / 100.0
        vulnerability = 1.0 - player.ratings.normalized_dodge()
        ball_holder_pressure = (
            (policy.target_ball_holder - 0.5)
            if state.player_id == recent_pressure_player_id
            else 0.0
        )
        base = (
            policy.target_stars * normalized_overall
            + (1.0 - policy.target_stars) * vulnerability
            + policy.target_ball_holder * ball_holder_pressure
        )
        score = base + noise * (rng.random() - 0.5)
        scored.append((score, state.player_id, state))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2]


@dataclass(frozen=True)
class CatchDecision:
    attempt: bool
    threshold: float
    normalized_catch: float
    normalized_dodge: float


def decide_catch_attempt(
    *, target: OfficialPlayerState, player_lookup: Dict[str, Player], policy: CoachPolicy
) -> CatchDecision:
    """Mirrors engine._should_attempt_catch."""

    player = player_lookup[target.player_id]
    normalized_catch = player.ratings.normalized_catch()
    normalized_dodge = player.ratings.normalized_dodge()
    base_threshold = 0.3 + 0.4 * (1.0 - policy.risk_tolerance)
    catch_bias_adjustment = (0.5 - policy.catch_bias) * 0.4
    threshold = base_threshold + catch_bias_adjustment
    dodge_guard = normalized_dodge - 0.15 + catch_bias_adjustment
    attempt = normalized_catch >= max(threshold, dodge_guard)
    return CatchDecision(
        attempt=attempt,
        threshold=threshold,
        normalized_catch=normalized_catch,
        normalized_dodge=normalized_dodge,
    )


def proactive_action_weights(
    *,
    legal_kinds: Sequence[str],
    policy: CoachPolicy,
    has_held_ball: bool,
    burden_on_team: bool,
    clock_pressure: bool,
) -> List[float]:
    """Produce CoachPolicy-aware weights for a list of legal action kinds.

    ``legal_kinds`` are strings from :class:`ProactiveKind`. Weights are
    non-negative; callers should normalize. No hidden boosts: only policy
    knobs nudge weights.
    """

    weights: List[float] = []
    tempo = policy.tempo
    risk = policy.risk_tolerance
    for kind in legal_kinds:
        if kind == "throw":
            # Tempo and risk push toward throwing. Clock pressure forces it.
            w = 1.0 + tempo * 1.5 + risk * 0.5
            if clock_pressure:
                w += 5.0
            weights.append(w)
        elif kind == "retrieve":
            w = 0.5 + (1.0 - tempo) * 0.5
            if burden_on_team:
                w += 1.0  # team needs balls back
            weights.append(w)
        elif kind == "wait":
            w = 0.5 + (1.0 - tempo) * 1.0
            if has_held_ball and burden_on_team:
                w *= 0.3  # don't stall when you have the burden
            weights.append(w)
        elif kind == "enter_court":
            weights.append(10.0)  # always take an enter-court opportunity
        else:
            weights.append(1.0)
    return weights
