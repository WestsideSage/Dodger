"""Per-driver attribute-consumer truth pins (2026-06-09 audit; V19a inversion).

The player-facing rating sheet shows nine attributes. The 2026-06-09 audit
pinned the dead set per driver; V19a (2026-06-10, owner-greenlit "wire
everything") flipped stamina and tactical_iq LIVE in BOTH drivers, plus two
non-attribute consumers (slot-role fit, rec rush targeting):

* ``RecTier1Driver`` now consumes accuracy, dodge, catch, catch_courage,
  throw_selection_iq, conditioning_curve, **stamina** (fatigue degrades
  performance less for high stamina — fatigue.effectiveness), and
  **tactical_iq** (targeting-read noise). Under the default SPREAD targeting,
  **power remains the one dead attribute** (it enters only THEIR_STARS
  targeting through overall_skill) — disclosed per-ruleset in terms.ts.
* The official engine now consumes accuracy, power, dodge, catch,
  **stamina** (late-match erosion of action stats), and **tactical_iq**
  (targeting-read noise). **catch_courage / throw_selection_iq /
  conditioning_curve stay dead on officials** — wiring the identity traits
  is future work and their pins below still guard the lie.

Same-seed invariance pins guard the remaining dead set; divergence pins
prove every newly-wired consumer actually consumes (a silent revert fails
loudly). Measurement companion: ``tools/decision_impact_probe.py``; V19a
BEFORE/AFTER matrices live in the V19 sprint plan.
"""

from __future__ import annotations

from dataclasses import replace as dc_replace

import pytest

from dodgeball_sim.models import CoachPolicy, OpeningRushTarget, PlayerArchetype
from dodgeball_sim.official_engine import OfficialMatchEngineDriver
from dodgeball_sim.rec_engine import RecTier1Driver
from tools.probe_lib import make_match_input

_SEEDS = range(6)
_BUMP = 30  # 63 -> 93: far outside noise; a live consumer cannot miss it


def _bump_team_a(mi, attr: str):
    lookup = dict(mi.player_lookup)
    for pid in mi.starters_a:
        player = lookup[pid]
        lookup[pid] = dc_replace(
            player, ratings=dc_replace(player.ratings, **{attr: 63 + _BUMP})
        )
    return dc_replace(mi, player_lookup=lookup)


def _swap_archetype(mi, pid: str, archetype: PlayerArchetype):
    lookup = dict(mi.player_lookup)
    lookup[pid] = dc_replace(lookup[pid], archetype=archetype)
    return dc_replace(mi, player_lookup=lookup)


def _rec_fingerprint(out) -> tuple:
    # Raw rec events are dicts; compare the full stream plus the result.
    return (out.winner_team_id, out.final_active_a, out.final_active_b, tuple(
        tuple(sorted((k, repr(v)) for k, v in event.items())) for event in out.events
    ))


def _official_fingerprint(out) -> tuple:
    # OfficialEvent dataclasses support equality; compare stream plus result.
    return (out.winner_team_id, out.final_active_a, out.final_active_b, tuple(out.events))


def _any_divergence(driver, fingerprint, mutate) -> bool:
    return any(
        fingerprint(driver.run(make_match_input(seed=seed)))
        != fingerprint(driver.run(mutate(make_match_input(seed=seed))))
        for seed in _SEEDS
    )


@pytest.mark.parametrize("attr", ["power"])
def test_rec_driver_is_invariant_to_dead_attributes_under_spread(attr):
    """Under the default SPREAD targeting, power never enters any rec-driver
    code path — a +30 bump must replay byte-identical. (stamina and
    tactical_iq left this list in V19a; their divergence pins are below.)"""
    driver = RecTier1Driver()
    for seed in _SEEDS:
        base = make_match_input(seed=seed)
        bumped = _bump_team_a(base, attr)
        assert _rec_fingerprint(driver.run(base)) == _rec_fingerprint(driver.run(bumped)), (
            f"rec driver consumed supposedly-dead attribute {attr!r} (seed {seed}); "
            "update the consumer matrix docs + terms.ts if this was deliberate"
        )


@pytest.mark.parametrize("attr", ["catch_courage", "throw_selection_iq", "conditioning_curve"])
def test_official_engine_is_invariant_to_identity_traits(attr):
    """The official engine never reads the three identity traits (they are not
    in overall_skill either) — a +30 bump must replay byte-identical."""
    driver = OfficialMatchEngineDriver()
    for seed in _SEEDS:
        base = make_match_input(seed=seed)
        bumped = _bump_team_a(base, attr)
        assert _official_fingerprint(driver.run(base)) == _official_fingerprint(driver.run(bumped)), (
            f"official engine consumed supposedly-dead attribute {attr!r} (seed {seed}); "
            "update the consumer matrix docs + terms.ts if this was deliberate"
        )


# ---------------------------------------------------------------------------
# V19a consumer pins: every newly-wired knob must actually consume.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("attr", ["stamina", "tactical_iq", "accuracy"])
def test_rec_driver_consumes_live_attribute(attr):
    """stamina (fatigue staying power) and tactical_iq (targeting read) are
    LIVE rec consumers as of V19a; accuracy is the legacy sanity anchor."""
    assert _any_divergence(
        RecTier1Driver(), _rec_fingerprint, lambda mi: _bump_team_a(mi, attr)
    ), f"{attr} bump never changed a rec match — the V19a consumer is dead"


@pytest.mark.parametrize("attr", ["stamina", "tactical_iq", "catch"])
def test_official_engine_consumes_live_attribute(attr):
    """stamina (late-match erosion) and tactical_iq (targeting read) are LIVE
    official consumers as of V19a; catch is the legacy sanity anchor."""
    assert _any_divergence(
        OfficialMatchEngineDriver(), _official_fingerprint, lambda mi: _bump_team_a(mi, attr)
    ), f"{attr} bump never changed an official match — the V19a consumer is dead"


@pytest.mark.parametrize(
    "driver_factory, fingerprint",
    [(RecTier1Driver, _rec_fingerprint), (OfficialMatchEngineDriver, _official_fingerprint)],
    ids=["rec", "official"],
)
def test_slot_role_fit_is_consumed(driver_factory, fingerprint):
    """V19a slot-role fit: the probe fixture is all-CATCHER, so slot 1
    (Striker — prefers DODGER_ANCHOR/BALL_HAWK) is a mismatch. Re-typing that
    starter to BALL_HAWK grants the fit bonus and must change the match —
    archetype reaches the engines ONLY through lineup.role_fit_bonuses.
    Wider seed window than the attribute pins: the +0.03 bonus is subtle by
    design, and on the rec driver the first diverging seed is 10."""
    assert any(
        fingerprint(driver_factory().run(make_match_input(seed=seed)))
        != fingerprint(
            driver_factory().run(
                _swap_archetype(
                    make_match_input(seed=seed),
                    make_match_input(seed=seed).starters_a[1],
                    PlayerArchetype.BALL_HAWK,
                )
            )
        )
        for seed in range(12)
    ), "re-seating a fitting archetype never changed a match — role fit is dead"


def test_rec_rush_target_is_consumed():
    """V19a: rush_target orders who SPRINTS (and therefore who may throw on
    the opening tick). With a power-skewed roster, STRONGEST_SIDE picks a
    different sprinter set than NEAREST (slot order) and must diverge."""
    driver = RecTier1Driver()

    def _mutate(mi):
        lookup = dict(mi.player_lookup)
        # Make the LAST slot the power outlier so STRONGEST_SIDE promotes it
        # into the sprinter group that slot order would have left out.
        last = mi.starters_a[-1]
        lookup[last] = dc_replace(
            lookup[last], ratings=dc_replace(lookup[last].ratings, power=95.0)
        )
        return dc_replace(
            mi,
            player_lookup=lookup,
            policy_a=CoachPolicy(rush_target=OpeningRushTarget.STRONGEST_SIDE),
        )

    def _control(mi):
        mutated = _mutate(mi)
        return dc_replace(
            mutated, policy_a=CoachPolicy(rush_target=OpeningRushTarget.NEAREST)
        )

    assert any(
        _rec_fingerprint(driver.run(_control(make_match_input(seed=seed))))
        != _rec_fingerprint(driver.run(_mutate(make_match_input(seed=seed))))
        for seed in _SEEDS
    ), "rush_target never changed a rec match — the sprinter ordering is dead"
