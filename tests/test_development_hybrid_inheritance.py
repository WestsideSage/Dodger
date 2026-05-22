from __future__ import annotations

from dodgeball_sim.development import _primary_stats_for_archetype
from dodgeball_sim.models import PlayerArchetype, PlayerRatings


def test_base_thrower_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.THROWER) == (
        ("accuracy", 1.0),
        ("power", 1.0),
    )


def test_base_catcher_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.CATCHER) == (
        ("catch", 1.0),
        ("catch_courage", 1.0),
    )


def test_base_ball_hawk_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.BALL_HAWK) == (
        ("stamina", 1.0),
        ("throw_selection_iq", 1.0),
    )


def test_base_dodger_anchor_primary_stats():
    assert _primary_stats_for_archetype(PlayerArchetype.DODGER_ANCHOR) == (
        ("dodge", 1.0),
        ("tactical_iq", 1.0),
    )


def test_thrower_catcher_hybrid_uses_weighted_union():
    assert _primary_stats_for_archetype(PlayerArchetype.THROWER_CATCHER) == (
        ("accuracy", 0.6),
        ("power", 0.6),
        ("catch", 0.4),
        ("catch_courage", 0.4),
    )


def test_hawk_dodger_hybrid_uses_weighted_union():
    assert _primary_stats_for_archetype(PlayerArchetype.HAWK_DODGER) == (
        ("stamina", 0.6),
        ("throw_selection_iq", 0.6),
        ("dodge", 0.4),
        ("tactical_iq", 0.4),
    )


def test_hybrid_primary_stats_use_higher_scoring_base_when_ratings_are_supplied():
    ratings = PlayerRatings(
        accuracy=70,
        power=70,
        catch=90,
        catch_courage=90,
        dodge=50,
        stamina=50,
        tactical_iq=50,
        throw_selection_iq=50,
        conditioning_curve=50,
    )

    assert _primary_stats_for_archetype(PlayerArchetype.THROWER_CATCHER, ratings) == (
        ("catch", 0.6),
        ("catch_courage", 0.6),
        ("accuracy", 0.4),
        ("power", 0.4),
    )
