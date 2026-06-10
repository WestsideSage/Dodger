"""Per-driver attribute-consumer truth pins (2026-06-09 systems audit).

The player-facing rating sheet shows nine attributes, but each shipping driver
consumes only a subset in match resolution:

* ``RecTier1Driver`` reads accuracy, dodge, catch, catch_courage,
  throw_selection_iq, conditioning_curve (and overall_skill for THEIR_STARS
  targeting). Under the default SPREAD targeting, **power / stamina /
  tactical_iq have no outcome consumer at all**.
* The official engine (``run_autonomous_match``) reads accuracy, power, dodge,
  catch (and overall_skill for targeting). **catch_courage /
  throw_selection_iq / conditioning_curve have no consumer anywhere** — they
  do not even enter ``overall_skill`` — and stamina enters only through
  OVR-weighted targeting, never resolution.

These same-seed invariance tests pin that truth: bumping a dead attribute must
leave the match byte-identical. If someone wires one of these attributes into
an engine (a deliberate, documented change), the matching pin fails loudly and
should be updated together with the player-facing copy (terms.ts qualifies the
identity-trait claims per ruleset because of this exact matrix). They also
guard the inverse lie: a "dead" knob silently becoming a hidden consumer.

Measurement companion: ``tools/decision_impact_probe.py`` (attribute section).
"""

from __future__ import annotations

from dataclasses import replace as dc_replace

import pytest

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


def _rec_fingerprint(out) -> tuple:
    # Raw rec events are dicts; compare the full stream plus the result.
    return (out.winner_team_id, out.final_active_a, out.final_active_b, tuple(
        tuple(sorted((k, repr(v)) for k, v in event.items())) for event in out.events
    ))


def _official_fingerprint(out) -> tuple:
    # OfficialEvent dataclasses support equality; compare stream plus result.
    return (out.winner_team_id, out.final_active_a, out.final_active_b, tuple(out.events))


@pytest.mark.parametrize("attr", ["power", "stamina", "tactical_iq"])
def test_rec_driver_is_invariant_to_dead_attributes_under_spread(attr):
    """Under the default SPREAD targeting, power/stamina/tactical_iq never
    enter any rec-driver code path — a +30 bump must replay byte-identical."""
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


def test_rec_driver_sanity_live_attribute_diverges():
    """Sanity check that the invariance harness can detect a live consumer:
    accuracy IS consumed by the rec driver, so a +30 bump must diverge on at
    least one seed of the sweep."""
    driver = RecTier1Driver()
    assert any(
        _rec_fingerprint(driver.run(make_match_input(seed=seed)))
        != _rec_fingerprint(driver.run(_bump_team_a(make_match_input(seed=seed), "accuracy")))
        for seed in _SEEDS
    ), "accuracy bump never changed a rec match — the fingerprint harness is broken"


def test_official_engine_sanity_live_attribute_diverges():
    """catch IS consumed by the official engine (it is the dominant attribute,
    +33pp/+12 measured) — a +30 bump must diverge on at least one seed."""
    driver = OfficialMatchEngineDriver()
    assert any(
        _official_fingerprint(driver.run(make_match_input(seed=seed)))
        != _official_fingerprint(driver.run(_bump_team_a(make_match_input(seed=seed), "catch")))
        for seed in _SEEDS
    ), "catch bump never changed an official match — the fingerprint harness is broken"
