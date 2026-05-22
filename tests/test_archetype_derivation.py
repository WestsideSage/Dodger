from __future__ import annotations

from dodgeball_sim.archetype_derivation import GAP_THRESHOLD, derive_archetype
from dodgeball_sim.models import PlayerArchetype, PlayerRatings


def _ratings(**kwargs) -> PlayerRatings:
    base = dict(
        accuracy=50,
        power=50,
        dodge=50,
        catch=50,
        stamina=50,
        tactical_iq=50,
        catch_courage=50,
        throw_selection_iq=50,
        conditioning_curve=50,
    )
    base.update(kwargs)
    return PlayerRatings(**base)


def test_pure_thrower():
    assert derive_archetype(_ratings(accuracy=95, power=95)) == PlayerArchetype.THROWER


def test_pure_catcher():
    assert derive_archetype(_ratings(catch=95, catch_courage=95)) == PlayerArchetype.CATCHER


def test_pure_ball_hawk():
    assert derive_archetype(_ratings(stamina=95, throw_selection_iq=95)) == PlayerArchetype.BALL_HAWK


def test_pure_dodger_anchor():
    assert derive_archetype(_ratings(dodge=95, tactical_iq=95)) == PlayerArchetype.DODGER_ANCHOR


def test_thrower_catcher_hybrid():
    assert (
        derive_archetype(_ratings(accuracy=90, power=90, catch=85, catch_courage=85))
        == PlayerArchetype.THROWER_CATCHER
    )


def test_thrower_dodger_hybrid():
    assert (
        derive_archetype(_ratings(accuracy=90, power=90, dodge=85, tactical_iq=85))
        == PlayerArchetype.THROWER_DODGER
    )


def test_catcher_hawk_hybrid():
    assert (
        derive_archetype(_ratings(catch=90, catch_courage=90, stamina=85, throw_selection_iq=85))
        == PlayerArchetype.CATCHER_HAWK
    )


def test_hawk_dodger_hybrid():
    assert (
        derive_archetype(_ratings(stamina=90, throw_selection_iq=90, dodge=85, tactical_iq=85))
        == PlayerArchetype.HAWK_DODGER
    )


def test_thrower_hawk_pair_returns_top_base():
    assert (
        derive_archetype(_ratings(accuracy=90, power=90, stamina=85, throw_selection_iq=85))
        == PlayerArchetype.THROWER
    )


def test_catcher_dodger_pair_returns_top_base():
    assert (
        derive_archetype(_ratings(catch=90, catch_courage=90, dodge=85, tactical_iq=85))
        == PlayerArchetype.CATCHER
    )


def test_gap_exactly_at_threshold_is_hybrid():
    assert (
        derive_archetype(_ratings(accuracy=90, power=90, catch=82.5, catch_courage=82.5))
        == PlayerArchetype.THROWER_CATCHER
    )


def test_gap_above_threshold_is_base():
    assert (
        derive_archetype(_ratings(accuracy=90, power=90, catch=82, catch_courage=82))
        == PlayerArchetype.THROWER
    )


def test_gap_threshold_constant():
    assert GAP_THRESHOLD == 15.0


def test_exact_tie_returns_hybrid_when_named_pair_exists():
    assert (
        derive_archetype(_ratings(stamina=100, throw_selection_iq=100, catch=100, catch_courage=100))
        == PlayerArchetype.CATCHER_HAWK
    )


def test_exact_tie_returns_alphabetical_base_when_no_hybrid_exists():
    assert (
        derive_archetype(_ratings(accuracy=100, power=100, stamina=100, throw_selection_iq=100))
        == PlayerArchetype.BALL_HAWK
    )


def test_allow_hybrid_false_forces_base():
    assert (
        derive_archetype(
            _ratings(accuracy=90, power=90, catch=85, catch_courage=85),
            allow_hybrid=False,
        )
        == PlayerArchetype.THROWER
    )


def test_determinism():
    ratings = _ratings(
        accuracy=72,
        power=68,
        dodge=55,
        catch=80,
        catch_courage=63,
        stamina=70,
        throw_selection_iq=58,
        tactical_iq=61,
    )

    assert derive_archetype(ratings) == derive_archetype(ratings) == derive_archetype(ratings)
