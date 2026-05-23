from __future__ import annotations

import pytest

from dodgeball_sim.voice_register import for_tier, tier1


def test_tier1_unknown_key_raises():
    with pytest.raises(KeyError):
        tier1("policy.unknown.value.label")


def test_for_tier_returns_full_tier1_register():
    register = for_tier(1)
    assert isinstance(register, dict)
    assert "policy.approach.aggressive.label" in register
    assert "moment.dramatic_catch.headline" in register


def test_tier1_policy_and_moment_templates_render():
    assert tier1("policy.approach.aggressive.label") == "Aggressive"
    assert tier1(
        "moment.dramatic_catch.headline",
        catcher="Maurice",
        returning="Sam",
    ) == "Maurice plucks one clean and Sam is back on."


def test_tier1_missing_format_key_raises():
    with pytest.raises(KeyError):
        tier1("moment.dramatic_catch.headline", catcher="Maurice")
