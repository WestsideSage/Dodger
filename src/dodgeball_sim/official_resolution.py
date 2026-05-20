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

from .models import CoachPolicy, Player
from .official_tactics import decide_catch_attempt
from .player_state import OfficialPlayerState
from .sequence import (
    SequenceContact,
    SequenceContactKind,
    SequenceOfPlay,
)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


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
    # Catch given attempt: catch rating vs power.
    p_catch_given_attempt = _sigmoid(3.0 * (catch_eff - 0.6 * power_eff))
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
    p_dodge = max(0.0, target.ratings.normalized_dodge() - 0.5 * probs.p_on_target)
    if rng.random() <= p_dodge:
        seq.add_contact(SequenceContact(kind=SequenceContactKind.OUT_OF_BOUNDS))
        return probs, "dodged"

    seq.add_pending_out(target_state.player_id, reason="hit")
    seq.add_contact(SequenceContact(
        kind=SequenceContactKind.HIT, player_id=target_state.player_id,
    ))
    return probs, "hit"
