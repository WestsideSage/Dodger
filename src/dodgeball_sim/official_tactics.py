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

from .models import Approach, CatchPosture, CoachPolicy, Player, TargetFocus
from .player_state import OfficialPlayerState, OfficialPlayerStatus


def _thrower_base(policy: CoachPolicy, player: Player) -> float:
    ratings = player.ratings
    if policy.approach == Approach.AGGRESSIVE:
        return 0.7 * ratings.normalized_power() + 0.3 * ratings.normalized_accuracy()
    if policy.approach == Approach.PATIENT:
        return 0.25 * ratings.normalized_power() + 0.75 * ratings.normalized_accuracy()
    return 0.5 * ratings.normalized_power() + 0.5 * ratings.normalized_accuracy()


def _target_base(
    policy: CoachPolicy,
    *,
    normalized_overall: float,
    vulnerability: float,
    is_recent_pressure_target: bool,
) -> float:
    if policy.target_focus == TargetFocus.THEIR_STARS:
        return normalized_overall + 0.15 * vulnerability
    if policy.target_focus == TargetFocus.BALL_HOLDERS:
        return (1.0 if is_recent_pressure_target else 0.0) + 0.15 * vulnerability
    return vulnerability + 0.05 * (1.0 - normalized_overall)


def _catch_thresholds(policy: CoachPolicy) -> tuple[float, float]:
    # (threshold, dodge_guard_offset) per posture. A target attempts a catch
    # iff normalized_catch >= max(threshold, normalized_dodge + guard_offset).
    #
    # 2026-06-09 systems audit: PLAY_SAFE previously computed threshold 0.75 —
    # above virtually every real roster's catch band (career seeds cluster
    # ~40-85) — so a play-safe team NEVER attempted a catch. Catches are the
    # official scoring economy (a catch outs the thrower AND resurrects a
    # teammate), so the posture was a measured forfeit: 0 wins in 400 even-
    # strength matches (tools/decision_impact_probe.py). The intended semantic
    # is "attempt only high-percentage catches, prefer evasion", not "opt out
    # of the rules' core counterplay". Threshold 0.65 keeps play-safe genuinely
    # selective (only strong catchers attempt; see the evasion shading in
    # official_resolution._PLAY_SAFE_EVASION_BONUS for the other half of the
    # tradeoff). GO_FOR_CATCHES / OPPORTUNISTIC pairs are numerically unchanged,
    # so every non-play_safe match replays byte-identical.
    # V17/WT-20 retune note: GO_FOR was (0.20, -0.30) under the old economy,
    # where even a weak catcher's attempt beat the brutal no-attempt dodge
    # roll. After the V17 catch retune (weak catchers land ~17-25% of
    # attempts) and WT-20 blocking (holders have real counterplay), that
    # threshold forced terrible attempts and GO_FOR measured as a -15pp trap
    # option. 0.35/-0.25 keeps GO_FOR clearly the most aggressive posture
    # while letting its weakest catchers decline throws they cannot catch.
    if policy.catch_posture == CatchPosture.GO_FOR_CATCHES:
        return 0.35, -0.25
    if policy.catch_posture == CatchPosture.PLAY_SAFE:
        return 0.65, -0.05
    return 0.50, -0.15


def _tempo_level(policy: CoachPolicy) -> float:
    if policy.approach == Approach.AGGRESSIVE:
        return 0.75
    if policy.approach == Approach.PATIENT:
        return 0.3
    return 0.5


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
    """Choose a thrower from live players holding a ball."""

    if not candidates:
        return None
    scored: List[Tuple[float, str, OfficialPlayerState]] = []
    noise = rng.random() * 0.05  # small deterministic jitter
    for state in candidates:
        player = player_lookup[state.player_id]
        base = _thrower_base(policy, player)
        score = base + noise * (rng.random() - 0.5)
        scored.append((score, state.player_id, state))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2]


# --- V19a tactical_iq consumer (2026-06-10) -----------------------------------
# Tactical IQ is the thrower's COURT READ: how accurately they assess which
# opponent is actually the right target. A low-IQ thrower's per-candidate
# read carries this much uniform error at IQ 0, scaling linearly to zero at
# IQ 100 — high-IQ players pick the genuinely vulnerable target, low-IQ
# players spray at whoever caught their eye. This wires the rating sheet's
# "court awareness, timing, and play reading" claim into outcomes without
# touching the catch economy (selection quality, not resolution math).
_TARGET_READ_NOISE_MAX = 0.30


def select_target(
    *,
    defense_states: Sequence[OfficialPlayerState],
    player_lookup: Dict[str, Player],
    policy: CoachPolicy,
    recent_pressure_player_id: Optional[str],
    rng: random.Random,
    thrower_tactical_iq: float = 50.0,
) -> Optional[OfficialPlayerState]:
    """Choose an opposing target. Mirrors engine._select_target weighting.

    ``thrower_tactical_iq`` (0-100) scales the per-candidate read error —
    see ``_TARGET_READ_NOISE_MAX``.
    """

    if not defense_states:
        return None
    scored: List[Tuple[float, str, OfficialPlayerState]] = []
    noise = rng.random() * 0.05
    read_noise = _TARGET_READ_NOISE_MAX * (
        1.0 - max(0.0, min(100.0, float(thrower_tactical_iq))) / 100.0
    )
    for state in defense_states:
        player = player_lookup[state.player_id]
        normalized_overall = player.overall_skill() / 100.0
        vulnerability = 1.0 - player.ratings.normalized_dodge()
        base = _target_base(
            policy,
            normalized_overall=normalized_overall,
            vulnerability=vulnerability,
            is_recent_pressure_target=state.player_id == recent_pressure_player_id,
        )
        score = base + noise * (rng.random() - 0.5) + read_noise * (rng.random() - 0.5)
        scored.append((score, state.player_id, state))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scored[0][2]


@dataclass(frozen=True)
class CatchDecision:
    attempt: bool
    threshold: float
    normalized_catch: float
    normalized_dodge: float


# WT-20: a defender holding a ball has the block in their back pocket, so a
# marginal catch attempt is no longer their only counterplay — holders demand
# this much extra catch skill before attempting (added to the BINDING attempt
# bar). Without it, GO_FOR_CATCHES forced weak-catch holders to trade a block
# for a ~17-25% catch and the posture measured as a -15pp trap option
# post-blocking (2026-06-10 probe). 0.12 over-suppressed the catch economy of
# defensive roster shapes (champion-parity probe: Power Throwers spiked to
# 73.8% of matched-OVR titles); 0.06 keeps weak catchers declining while
# capable catchers stay in the catch game.
_HOLDER_BLOCK_PREFERENCE = 0.06


def decide_catch_attempt(
    *,
    target: OfficialPlayerState,
    player_lookup: Dict[str, Player],
    policy: CoachPolicy,
    holds_ball: bool = False,
) -> CatchDecision:
    """Mirrors engine._should_attempt_catch.

    ``holds_ball`` raises the attempt bar (WT-20): a ball-holding defender can
    block instead, so only clearly catchable throws are worth the attempt.
    """

    player = player_lookup[target.player_id]
    normalized_catch = player.ratings.normalized_catch()
    normalized_dodge = player.ratings.normalized_dodge()
    threshold, dodge_guard_offset = _catch_thresholds(policy)
    dodge_guard = normalized_dodge + dodge_guard_offset
    # The holder bump raises the BINDING bar, not just the posture threshold —
    # for the weak-catch/high-dodge players the dodge guard is what binds, and
    # bumping only the threshold left the trap intact (measured 2026-06-10).
    attempt_bar = max(threshold, dodge_guard)
    if holds_ball:
        attempt_bar += _HOLDER_BLOCK_PREFERENCE
    attempt = normalized_catch >= attempt_bar
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
    tempo = _tempo_level(policy)
    power_bias = 0.7 if policy.approach == Approach.AGGRESSIVE else 0.25 if policy.approach == Approach.PATIENT else 0.5
    for kind in legal_kinds:
        if kind == "throw":
            w = 1.0 + tempo * 1.5 + power_bias * 0.5
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
