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
from .season_emphasis import SeasonEmphasis
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

# --- Held-ball blocking (WT-20, 2026-06-10) -----------------------------------
# Before WT-20 the official engine modeled no blocking at all, so the No
# Blocking rule (Section 27) had nothing to remove and was activation-logged
# only. A ball-holding defender who declines the catch now puts the held ball
# between themselves and the throw: a successful block kills the thrown ball
# (no out, no catch — the sequence resolves empty). Under No Blocking the
# branch is disabled entirely (the held ball no longer protects; Section 27
# body-extension semantics per no_blocking.resolve_contact_with_held_ball).
# The primary source names the No Blocking trigger and terminal state but
# leaves the reduced-blocking resolution unspecified (see
# docs/specs/2026-06-01-workflow0-primary-source-rule-verification.md), so
# "remove block protection, change nothing else" is a PROPOSED sim-design
# resolution shipped with measurement (owner-ungated 2026-06-10), not a USAD
# fidelity claim. p(block) at even ratings ~= 0.65, keyed on the blocker's
# CATCH (ball control) against the thrower's power: holding a ball is real
# protection in regulation, which is exactly what the No Blocking phase takes
# away.
_BLOCK_SLOPE = 3.0
_BLOCK_THROW_POWER_WEIGHT = 0.6
# p(block) ~= 0.65 at even ratings. A first cut at 0.3 (p ~= 0.74) made the
# held ball close to a wall: targeting any holder measured -10pp (the
# BALL_HOLDERS focus became a trap) and posture economics warped around
# block-fishing; -0.3 (p ~= 0.61) overcorrected the league economy toward
# throwing shapes (Power Throwers 73.8% of matched-OVR titles). -0.1 keeps
# holding a real defensive asset that No Blocking meaningfully strips without
# making holders unattackable.
_BLOCK_BIAS = -0.1

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

# --- V19a performance shades (2026-06-10) -------------------------------------
# A per-player normalized shade applied to that player's ACTION stats for one
# throw resolution: thrower accuracy/power, defender dodge/catch (and the
# block-skill read). Composed by the engine from two disclosed consumers:
#
# * Slot-role fit (+_ROLE_FIT_BONUS in official_engine): a starter seated in a
#   role their archetype fits plays slightly above their sheet — bonus-only,
#   so a mismatched seat costs the foregone bonus, never a hidden penalty
#   (the 2026-06-09 audit's "liability fiction" stays dead).
# * Stamina (late-match erosion in official_engine): action stats erode with
#   MATCH progress, scaled by (1 - normalized stamina) — "staying power
#   across a long match", exactly what the rating tooltip promises. At even
#   stamina both sides erode together, so the even-strength baseline holds.
#
# Shades are small (|shade| <= ~0.12 normalized) and clamped at the eff layer.


# V19a tactical_iq (thrower side): the rating sheet promises "court
# awareness, TIMING, and play reading". The read/awareness half lives in
# official_tactics.select_target (targeting noise scales down with IQ); this
# is the timing half — a high-IQ thrower releases into the right window, a
# low-IQ thrower forces bad moments. Centered at IQ 50 so the league-average
# thrower is unchanged. The targeting read alone could not express in the
# uniform-opponent attribute probe (identical targets = nothing to select),
# which is exactly the uniform-fixture trap the V17 retro flagged. Probe
# iterations: routing timing only into p_on_target could not separate IQ
# from baseline at any sane slope, because an on-target throw is only
# marginally +EV in the V17 catch economy (it can be caught). The honest
# timing channel is CATCHABILITY (_TIQ_TIMING_CATCH below): a well-timed
# throw arrives when the catcher is off-balance, the same defensive-economy
# answer V17 gave accuracy. The on-target component stays small.
_TIQ_TIMING_SLOPE = 0.6
_TIQ_TIMING_CATCH = 1.0


@dataclass(frozen=True)
class ThrowProbabilities:
    p_on_target: float
    p_catch_given_attempt: float


def _shaded(value: float, shade: float) -> float:
    return max(0.0, min(1.0, value + shade))


def compute_throw_probabilities(
    *,
    thrower: Player,
    target: Player,
    thrower_shade: float = 0.0,
    target_shade: float = 0.0,
    thrower_tiq_bonus: float = 0.0,
    catch_emphasis: float = 0.0,
) -> ThrowProbabilities:
    """Return the on-target and catch probabilities for one throw.

    Tuning constants are intentionally simpler than the generic engine to
    keep the V11 resolution honest about ratings without depending on the
    full ``BalanceConfig`` infrastructure. ``*_shade`` are the V19a
    performance shades (role fit + stamina erosion); defaults keep legacy
    callers byte-identical.
    """

    accuracy_eff = _shaded(thrower.ratings.normalized_accuracy(), thrower_shade)
    dodge_eff = _shaded(target.ratings.normalized_dodge(), target_shade)
    catch_eff = _shaded(target.ratings.normalized_catch(), target_shade)
    power_eff = _shaded(thrower.ratings.normalized_power(), thrower_shade)

    # On-target: accuracy beats dodge; power slightly helps; tactical IQ
    # times the release window (V19a — see _TIQ_TIMING_SLOPE). A V19b
    # "tactics" staff-focus week raises the thrower's effective IQ on every
    # IQ channel (film prep = smarter throws, not just better reads).
    tiq_centered = (
        min(1.0, thrower.ratings.normalized_tactical_iq() + max(0.0, thrower_tiq_bonus) / 100.0)
        - 0.5
    )
    p_on_target = _sigmoid(
        3.0 * (accuracy_eff - dodge_eff)
        + 0.5 * power_eff
        + _TIQ_TIMING_SLOPE * tiq_centered
    )
    # Catch given attempt: catch rating vs throw quality (power AND accuracy),
    # biased down so a catch is no longer the default outcome of an on-target
    # throw (Phase 4a). The steeper catch slope makes a strong catcher's edge
    # over a weak one express more; the throw-quality term (V17) makes an
    # accurate throw harder to catch, so accuracy buys catch-economy defense
    # instead of feeding the opponent's catch counterplay.
    # V28 officiating emphasis: shift the EXISTING catch bias before the roll
    # (no new RNG draw). A positive ``catch_emphasis`` lowers the effective bias,
    # raising the catch rate. ``catch_emphasis == 0.0`` ⇒ ``_CATCH_BIAS - 0.0 ==
    # _CATCH_BIAS`` exactly in IEEE-754, so the default path is byte-identical.
    catch_bias = _CATCH_BIAS - catch_emphasis
    p_catch_given_attempt = _sigmoid(
        _CATCH_SLOPE * (catch_eff - _CATCH_POWER_WEIGHT * power_eff)
        - _CATCH_THROW_QUALITY_SLOPE * accuracy_eff
        - _TIQ_TIMING_CATCH * tiq_centered
        - catch_bias
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
    target_holds_ball: bool = False,
    no_blocking_active: bool = False,
    opening_catch_factor: float = 1.0,
    thrower_shade: float = 0.0,
    target_shade: float = 0.0,
    thrower_tiq_bonus: float = 0.0,
    season_emphasis: SeasonEmphasis = SeasonEmphasis(),
) -> Tuple[ThrowProbabilities, str]:
    """Resolve one throw against one primary target and mutate the sequence.

    Returns ``(probabilities, outcome_label)`` where ``outcome_label`` is one
    of: ``"hit"``, ``"caught"``, ``"dodged"``, ``"blocked"``. The sequence is
    mutated with the appropriate pending outs and catches; sequence finality
    is applied by :func:`dodgeball_sim.sequence.resolve_sequence`.

    ``target_holds_ball`` enables the WT-20 block branch for a defender who
    declines the catch; ``no_blocking_active`` disables that protection
    (Section 27 — the held ball no longer protects).
    ``opening_catch_factor`` shades the catch probability during the opening
    exchange (WT-20 rush: the caller derives it from both teams' rush_commit;
    1.0 outside the opening ticks).
    """

    thrower = player_lookup[thrower_state.player_id]
    target = player_lookup[target_state.player_id]
    probs = compute_throw_probabilities(
        thrower=thrower,
        target=target,
        thrower_shade=thrower_shade,
        target_shade=target_shade,
        thrower_tiq_bonus=thrower_tiq_bonus,
        catch_emphasis=season_emphasis.catch_delta,
    )

    on_target = rng.random() <= probs.p_on_target
    if not on_target:
        seq.add_contact(SequenceContact(kind=SequenceContactKind.OUT_OF_BOUNDS))
        return probs, "dodged"

    # Target decides whether to attempt a catch (holders are choosier — they
    # can block instead; see official_tactics._HOLDER_BLOCK_PREFERENCE).
    decision = decide_catch_attempt(
        target=target_state,
        player_lookup=player_lookup,
        policy=policy,
        holds_ball=target_holds_ball and not no_blocking_active,
    )
    if decision.attempt:
        p_catch = min(0.97, probs.p_catch_given_attempt * opening_catch_factor)
        if rng.random() <= p_catch:
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

    # No catch attempt -> a ball-holding defender blocks before any dodge roll
    # (WT-20). Under No Blocking the held ball no longer protects and the
    # branch is skipped entirely — see the block constants above. Blocking
    # skill keys on CATCH (ball control — "good hands wall it away"), not
    # power: keying it on power double-dipped the throwing shapes (power
    # already shades catchability) and the champion-parity probe measured
    # Power Throwers spiking to 63-74% of matched-OVR titles.
    if target_holds_ball and not no_blocking_active:
        power_thr = _shaded(thrower.ratings.normalized_power(), thrower_shade)
        block_skill = _shaded(target.ratings.normalized_catch(), target_shade)
        # V28 officiating emphasis: shift the EXISTING block bias before the roll
        # (no new RNG draw). ``block_delta == 0.0`` ⇒ ``_BLOCK_BIAS + 0.0 ==
        # _BLOCK_BIAS`` exactly, so the default path is byte-identical.
        block_bias = _BLOCK_BIAS + season_emphasis.block_delta
        p_block = _sigmoid(
            _BLOCK_SLOPE * (block_skill - _BLOCK_THROW_POWER_WEIGHT * power_thr)
            + block_bias
        )
        if rng.random() <= p_block:
            seq.add_contact(SequenceContact(
                kind=SequenceContactKind.BLOCK,
                player_id=target_state.player_id,
            ))
            return probs, "blocked"

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
        _shaded(target.ratings.normalized_dodge(), target_shade)
        - 0.5 * probs.p_on_target
        + evasion_bonus,
    )
    if rng.random() <= p_dodge:
        seq.add_contact(SequenceContact(kind=SequenceContactKind.OUT_OF_BOUNDS))
        return probs, "dodged"

    seq.add_pending_out(target_state.player_id, reason="hit")
    seq.add_contact(SequenceContact(
        kind=SequenceContactKind.HIT, player_id=target_state.player_id,
    ))
    return probs, "hit"
