from __future__ import annotations

from dodgeball_sim.identity import classify_archetype
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits


def _player(archetype: PlayerArchetype, **rating_kwargs) -> Player:
    base = dict(
        accuracy=60,
        power=60,
        dodge=60,
        catch=60,
        stamina=60,
        tactical_iq=60,
        catch_courage=60,
        throw_selection_iq=60,
        conditioning_curve=60,
    )
    base.update(rating_kwargs)
    return Player(
        id="p1",
        name="Test Player",
        ratings=PlayerRatings(**base),
        archetype=archetype,
        traits=PlayerTraits(),
    )


def _raw_value_set() -> set[str]:
    return {member.value for member in PlayerArchetype}


def test_display_name_present_for_every_member():
    for archetype in PlayerArchetype:
        assert archetype.display_name
        assert archetype.display_name != archetype.value


def test_classify_archetype_never_returns_raw_value():
    raw = _raw_value_set()
    for archetype in PlayerArchetype:
        assert classify_archetype(_player(archetype)) not in raw


def test_recruitment_never_returns_raw_value():
    from dodgeball_sim.recruitment import archetype_for_player

    raw = _raw_value_set()
    for archetype in PlayerArchetype:
        assert archetype_for_player(_player(archetype)) not in raw


def test_scouting_never_returns_raw_value():
    from dodgeball_sim.scouting import reveal_archetype

    raw = _raw_value_set()
    for archetype in PlayerArchetype:
        assert reveal_archetype(_player(archetype)) not in raw


def test_recruitment_and_scouting_have_distinct_vocab():
    from dodgeball_sim.recruitment import archetype_for_player
    from dodgeball_sim.scouting import reveal_archetype

    assert (
        archetype_for_player(_player(PlayerArchetype.CATCHER))
        != reveal_archetype(_player(PlayerArchetype.CATCHER))
    )


def test_display_name_is_human_friendly():
    for archetype in PlayerArchetype:
        assert "_" not in archetype.display_name
