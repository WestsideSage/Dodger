from __future__ import annotations

from dataclasses import replace

from dodgeball_sim.identity import (
    _ARCHETYPE_PREFIXES,
    _ARCHETYPE_SUFFIXES,
    build_identity_profile,
    classify_archetype,
    generate_nickname,
)
from dodgeball_sim.models import PlayerTraits
from dodgeball_sim.rng import DeterministicRNG

from .factories import make_player


def test_classify_archetype_detects_accuracy_driven_clutch_player():
    player = replace(
        make_player("ace", name="Rhea Mercer", accuracy=92, power=70, dodge=61, catch=63, stamina=66),
        traits=PlayerTraits(potential=85, growth_curve="steady", consistency=0.61, pressure=0.91),
    )

    assert classify_archetype(player) == "ace sniper"


def test_classify_archetype_detects_catch_specialist():
    player = replace(
        make_player("hawk", name="Noa Barrett", accuracy=62, power=59, dodge=75, catch=94, stamina=64),
        traits=PlayerTraits(potential=80, growth_curve="steady", consistency=0.88, pressure=0.42),
    )

    assert classify_archetype(player) == "ball hawk"


def test_generate_nickname_is_seeded_by_caller_rng():
    player = replace(
        make_player("cannon", name="Jade Holloway", accuracy=68, power=95, dodge=57, catch=55, stamina=82),
        traits=PlayerTraits(potential=87, growth_curve="late", consistency=0.47, pressure=0.54),
    )

    nickname_a = generate_nickname(player, DeterministicRNG(77))
    nickname_b = generate_nickname(player, DeterministicRNG(77))
    nickname_c = generate_nickname(player, DeterministicRNG(78))

    assert nickname_a == nickname_b
    assert nickname_a != nickname_c


def test_build_identity_profile_returns_title_nickname_and_top_attributes():
    player = replace(
        make_player("anchor", name="Tess Calder", accuracy=71, power=73, dodge=66, catch=78, stamina=91),
        traits=PlayerTraits(potential=83, growth_curve="steady", consistency=0.7, pressure=0.51),
    )

    profile = build_identity_profile(player, DeterministicRNG(12))

    assert profile.player_id == "anchor"
    assert profile.full_name == "Tess Calder"
    assert profile.archetype == "iron anchor"
    assert profile.title == "Iron Anchor"
    assert profile.strongest_attribute == "Stamina"
    assert profile.secondary_attribute == "Catch"
    assert profile.nickname


def test_archetype_nickname_pools_have_v4_depth():
    assert all(len(options) >= 8 for options in _ARCHETYPE_PREFIXES.values())
    assert all(len(options) >= 8 for options in _ARCHETYPE_SUFFIXES.values())
