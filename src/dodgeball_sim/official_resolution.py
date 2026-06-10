"""Throw resolution for the official engine.

Given a thrower, a target, ratings, and a seeded RNG, produce the
:class:`~dodgeball_sim.sequence.SequenceContact` outcomes (hit / dodge /
catch / block) that the sequence resolver will finalize. Uses sigmoid math
in the same spirit as :mod:`engine`, but produces *pending* outcomes that
feed sequence finality rather than mutating ``is_out`` directly.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Tuple

from .models import CatchPosture, CoachPolicy, Player
from .official_tactics import decide_catch_attempt
from .player_state import OfficialPlayerState
from .sequence import (
    SequenceContact,
    SequenceContactKind,
    SequenceOfPlay,
)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


# --- Catch-balance tuning (Phase 4a, retuned V17) -----------------------------
# The original even-ratings catch rate (~0.65 when attempted, with everyone
# always attempting) made a throw ~2.3x likelier to out the thrower (caught +
# resurrect) than to score a hit. Throwing was net-negative EV, so games rarely
# reached full elimination -> clock expiry -> 0-0 no_point draws -> ~22% draws,
# and OVR could not express in the win curve (measured slope +3.3pp vs a +10pp
# gate, top floor 43.7% vs 60%). Phase 4a pulled the catch rate down and
# sharpened its rating sensitivity. The catch-outs-thrower-and-resurrects rule
# itself is unchanged (faithful to USA Dodgeball).
#
# V17 catch-economy retune (2026-06-10, owner-greenlit): even after Phase 4a,
# p(catch|attempt) at even ratings was ~0.527 — above the 1/3 EV-neutral line
# (a catch is a -2 swing vs +1 for a hit), so an on-target throw stayed
# net-negative EV. Measured consequence (2026-06-09 systems audit §3.4):
# +12 accuracy = MINUS 8pp win rate and +12 dodge = MINUS 10pp at even
# strength — two of the five displayed core skills were liabilities. The fix
# shades catchability by throw quality (_CATCH_THROW_QUALITY_SLOPE: a more
# accurate throw is harder to catch), giving accuracy a defensive-economy
# answer, and rebalances _CATCH_BIAS so the even-strength catch rate sits just
# below EV-neutral. Constants chosen by deterministic grid search against the
# decision-impact probe; see tests/test_official_engine_balance.py for the
# non-negativity gates and docs/specs/2026-06-10-post-v16-greenlit-backlog-
# sequencing-plan.md (V17 Task 1) for the acceptance criteria.
_CATCH_SLOPE = 4.0
_CATCH_POWER_WEIGHT = 0.6
_CATCH_THROW_QUALITY_SLOPE = 2.0
_CATCH_BIAS = 0.7

# --- Play-safe evasion shading (2026-06-09 systems audit; retuned V17) --------
# PLAY_SAFE declines marginal catch attempts (official_tactics._catch_thresholds
# keeps its attempt threshold at 0.65, above the average catch band), so it
# forgoes most of the catch economy. Before this pass the declining target got
# nothing in return — the no-attempt dodge roll (dodge - 0.5 * p_on_target) is
# brutal — and play-safe measured ZERO wins in 400 even-strength matches. The
# bonus below applies ONLY when a play-safe defender declines the catch: the
# posture's promised tradeoff (give up resurrections, evade better) becomes
# real instead of a forfeit. Same RNG draw count, so every match that involves
# no play-safe decliner replays byte-identical.
#
# V17: the bonus was 0.25 under the old economy, where declining a catch
# forfeited the dominant scoring resource. The catch retune made catches
# rarer, so 0.25 overpaid — play_safe measured 50.7% vs go_for 40.2% at even
# strength (a new dominant posture, the same legibility bug in reverse). At
# 0.10 the posture spread is a real tradeoff (measured 250 trials/option:
# default 40.8 / go_for 37.6 / play_safe 39.2); the forfeit floor stays
# pinned by tests/test_official_engine_balance.py::
# test_play_safe_posture_is_not_a_forfeit.
_PLAY_SAFE_EVASION_BONUS = 0.10


@dataclass(frozen=True)
class ThrowProbabilities:
    p_on_target: float
    p_catch_given_attempt: float


def compute_throw_probabilities(
    *, thrower: Player, target: Player
) -> ThrowProbabilities:
    """Return the on-target and catch probabilities for one throw.

    Tuning constants are intentionally simpler than the generic engine to
    keep the V11 resolution honest about ratings without depending on the
    full ``BalanceConfig`` infrastructure.
    """

    accuracy_eff = thrower.ratings.normalized_accuracy()
    dodge_eff = target.ratings.normalized_dodge()
    catch_eff = target.ratings.normalized_catch()
    power_eff = thrower.ratings.normalized_power()

    # On-target: accuracy beats dodge; power slightly helps.
    p_on_target = _sigmoid(3.0 * (accuracy_eff - dodge_eff) + 0.5 * power_eff)
    # Catch given attempt: catch rating vs throw quality (power AND accuracy),
    # biased down so a catch is no longer the default outcome of an on-target
    # throw (Phase 4a). The steeper catch slope makes a strong catcher's edge
    # over a weak one express more; the throw-quality term (V17) makes an
    # accurate throw harder to catch, so accuracy buys catch-economy defense
    # instead of feeding the opponent's catch counterplay.
    p_catch_given_attempt = _sigmoid(
        _CATCH_SLOPE * (catch_eff - _CATCH_POWER_WEIGHT * power_eff)
        - _CATCH_THROW_QUALITY_SLOPE * accuracy_eff
        - _CATCH_BIAS
    )
    return ThrowProbabilities(
        p_on_target=p_on_target,
        p_catch_given_attempt=p_catch_given_attempt,
    )


def resolve_throw(
    *,
    seq: SequenceOfPlay,
    thrower_state: OfficialPlayerState,
    target_state: OfficialPlayerState,
    player_lookup: Dict[str, Player],
    policy: CoachPolicy,
    rng: random.Random,
) -> Tuple[ThrowProbabilities, str]:
    """Resolve one throw against one primary target and mutate the sequence.

    Returns ``(probabilities, outcome_label)`` where ``outcome_label`` is one
    of: ``"hit"``, ``"caught"``, ``"dodged"``. The sequence is mutated with
    the appropriate pending outs and catches; sequence finality is applied
    by :func:`dodgeball_sim.sequence.resolve_sequence`.
    """

    thrower = player_lookup[thrower_state.player_id]
    target = player_lookup[target_state.player_id]
    probs = compute_throw_probabilities(thrower=thrower, target=target)

    on_target = rng.random() <= probs.p_on_target
    if not on_target:
        seq.add_contact(SequenceContact(kind=SequenceContactKind.OUT_OF_BOUNDS))
        return probs, "dodged"

    # Target decides whether to attempt a catch.
    decision = decide_catch_attempt(
        target=target_state, player_lookup=player_lookup, policy=policy
    )
    if decision.attempt:
        if rng.random() <= probs.p_catch_given_attempt:
            seq.add_catch(catcher_id=target_state.player_id, timestamp_ms=seq.release_time_ms + 10)
            seq.add_contact(SequenceContact(
                kind=SequenceContactKind.CATCH,
                player_id=target_state.player_id,
            ))
            return probs, "caught"
        # Failed catch attempt -> the target is hit.
        seq.add_pending_out(target_state.player_id, reason="failed_catch")
        seq.add_contact(SequenceContact(
            kind=SequenceContactKind.HIT, player_id=target_state.player_id,
        ))
        return probs, "hit"

    # No catch attempt -> dodge roll determines hit.
    # Dodge probability scales inversely with how on-target the throw was.
    # A play-safe defender that declined the catch is committed to evasion;
    # see _PLAY_SAFE_EVASION_BONUS above for the design reason and measurement.
    evasion_bonus = (
        _PLAY_SAFE_EVASION_BONUS
        if policy.catch_posture == CatchPosture.PLAY_SAFE
        else 0.0
    )
    p_dodge = max(
        0.0,
        target.ratings.normalized_dodge() - 0.5 * probs.p_on_target + evasion_bonus,
    )
    if rng.random() <= p_dodge:
        seq.add_contact(SequenceContact(kind=SequenceContactKind.OUT_OF_BOUNDS))
        return probs, "dodged"

    seq.add_pending_out(target_state.player_id, reason="hit")
    seq.add_contact(SequenceContact(
        kind=SequenceContactKind.HIT, player_id=target_state.player_id,
    ))
    return probs, "hit"
