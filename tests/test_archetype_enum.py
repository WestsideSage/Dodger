from __future__ import annotations

import pytest

from dodgeball_sim.models import PlayerArchetype


def test_enum_has_eight_values():
    assert len(list(PlayerArchetype)) == 8


def test_enum_has_expected_members():
    expected = {
        "THROWER",
        "CATCHER",
        "BALL_HAWK",
        "DODGER_ANCHOR",
        "THROWER_CATCHER",
        "THROWER_DODGER",
        "CATCHER_HAWK",
        "HAWK_DODGER",
    }

    assert {member.name for member in PlayerArchetype} == expected


def test_v6_values_are_gone():
    for legacy in ("POWER", "AGILITY", "PRECISION", "DEFENSE", "TACTICAL"):
        with pytest.raises(KeyError):
            PlayerArchetype[legacy]


def test_display_name_per_member():
    expected = {
        PlayerArchetype.THROWER: "Sharpshooter",
        PlayerArchetype.CATCHER: "Net Specialist",
        PlayerArchetype.BALL_HAWK: "Ball Hawk",
        PlayerArchetype.DODGER_ANCHOR: "Iron Anchor",
        PlayerArchetype.THROWER_CATCHER: "Two-Way Threat",
        PlayerArchetype.THROWER_DODGER: "Skirmisher",
        PlayerArchetype.CATCHER_HAWK: "Possession Specialist",
        PlayerArchetype.HAWK_DODGER: "Hit-and-Run",
    }

    for member, name in expected.items():
        assert member.display_name == name


def test_value_strings_are_lowercase_snake():
    assert PlayerArchetype.BALL_HAWK.value == "ball_hawk"
    assert PlayerArchetype.THROWER_CATCHER.value == "thrower_catcher"
