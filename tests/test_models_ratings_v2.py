from __future__ import annotations

from dataclasses import is_dataclass

import pytest

from dodgeball_sim.models import Player, PlayerRatings


def test_v2_fields_default_to_50():
    ratings = PlayerRatings(accuracy=60, power=60, dodge=60, catch=60)

    assert ratings.catch_courage == 50.0
    assert ratings.throw_selection_iq == 50.0
    assert ratings.conditioning_curve == 50.0


def test_v2_fields_clamp_at_bounds():
    ratings = PlayerRatings(
        accuracy=60,
        power=60,
        dodge=60,
        catch=60,
        catch_courage=150.0,
        throw_selection_iq=-10.0,
        conditioning_curve=200.0,
    ).apply_bounds()

    assert ratings.catch_courage == 100.0
    assert ratings.throw_selection_iq == 0.0
    assert ratings.conditioning_curve == 100.0


def test_apply_bounds_rounds_player_ratings_to_integers():
    ratings = PlayerRatings(
        accuracy=60.4,
        power=60.5,
        dodge=60.6,
        catch=60.49,
        stamina=60.51,
        tactical_iq=49.5,
        catch_courage=72.4,
        throw_selection_iq=33.6,
        conditioning_curve=88.5,
    ).apply_bounds()

    assert ratings.accuracy == 60
    assert ratings.power == 60
    assert ratings.dodge == 61
    assert ratings.catch == 60
    assert ratings.stamina == 61
    assert ratings.tactical_iq == 50
    assert ratings.catch_courage == 72
    assert ratings.throw_selection_iq == 34
    assert ratings.conditioning_curve == 88


def test_v2_fields_explicit_values_preserved():
    ratings = PlayerRatings(
        accuracy=60,
        power=60,
        dodge=60,
        catch=60,
        catch_courage=72.0,
        throw_selection_iq=33.0,
        conditioning_curve=88.0,
    )

    assert ratings.catch_courage == 72.0
    assert ratings.throw_selection_iq == 33.0
    assert ratings.conditioning_curve == 88.0


def _ratings(**kwargs) -> PlayerRatings:
    base = dict(accuracy=60, power=60, dodge=60, catch=60)
    base.update(kwargs)
    return PlayerRatings(**base)


def test_overall_skill_covers_only_five_skill_fields():
    ratings = _ratings(
        stamina=50,
        tactical_iq=100,
        catch_courage=100,
        throw_selection_iq=100,
        conditioning_curve=100,
    )

    expected = (60 + 60 + 60 + 60 + 50) / 5
    assert ratings.overall_skill() == pytest.approx(expected)


def test_overall_old_name_removed():
    ratings = _ratings()

    assert not hasattr(ratings, "overall")
    assert callable(getattr(ratings, "overall_skill", None))


def test_identity_profile_dataclass():
    ratings = _ratings(
        catch_courage=70,
        throw_selection_iq=80,
        conditioning_curve=40,
        tactical_iq=55,
    )

    profile = ratings.identity_profile()

    assert is_dataclass(profile)
    assert profile.catch_courage == 70
    assert profile.throw_selection_iq == 80
    assert profile.conditioning_curve == 40
    assert profile.tactical_iq == 55


def test_player_overall_skill_delegates():
    from dodgeball_sim.models import PlayerArchetype
    ratings = _ratings()
    player = Player(id="p1", name="P", ratings=ratings, archetype=PlayerArchetype.CATCHER)

    assert player.overall_skill() == ratings.overall_skill()


def test_player_requires_explicit_archetype():
    ratings = _ratings()

    with pytest.raises(ValueError, match="archetype"):
        Player(id="p1", name="P", ratings=ratings)


def test_player_rejects_unknown_archetype_string():
    ratings = _ratings()

    with pytest.raises(ValueError, match="Invalid archetype"):
        Player(id="p1", name="P", ratings=ratings, archetype="Tactical")  # type: ignore[arg-type]
