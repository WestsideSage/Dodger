from __future__ import annotations

from pathlib import Path

import pytest

from dodgeball_sim.meta import MetaPatch, RuleSetOverrides


def test_ruleset_overrides_only_emit_explicit_values():
    overrides = RuleSetOverrides(balls_in_play=4)

    assert overrides.explicit_values() == {"balls_in_play": 4}
    assert overrides.has_overrides() is True


def test_ruleset_overrides_apply_without_accidentally_overwriting_null_fields():
    base_ruleset = {
        "catch_revival_enabled": False,
        "balls_in_play": 2,
        "shot_clock_seconds": 24,
        "format_version": "phase5",
    }
    overrides = RuleSetOverrides(shot_clock_seconds=18)

    assert overrides.apply_to(base_ruleset) == {
        "catch_revival_enabled": False,
        "balls_in_play": 2,
        "shot_clock_seconds": 18,
        "format_version": "phase5",
    }


def test_meta_patch_context_payload_is_player_readable_and_typed():
    patch = MetaPatch(
        patch_id="heavy_ball",
        season_id="season_2031",
        name="Heavy Ball",
        description="Power throws drain more stamina and the pace slows down.",
        power_stamina_cost_modifier=0.15,
        fatigue_rate_modifier=0.10,
        ruleset_overrides=RuleSetOverrides(balls_in_play=1, shot_clock_seconds=20),
    )

    assert patch.modifier_summary() == {
        "power_stamina_cost_modifier": 0.15,
        "dodge_penalty_modifier": 0.0,
        "fatigue_rate_modifier": 0.10,
    }
    assert patch.context_payload() == {
        "meta_patch_id": "heavy_ball",
        "meta_patch_name": "Heavy Ball",
        "modifiers": {
            "power_stamina_cost_modifier": 0.15,
            "dodge_penalty_modifier": 0.0,
            "fatigue_rate_modifier": 0.10,
        },
        "ruleset_overrides": {"balls_in_play": 1, "shot_clock_seconds": 20},
    }


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"balls_in_play": 0}, "balls_in_play"),
        ({"shot_clock_seconds": 0}, "shot_clock_seconds"),
    ],
)
def test_ruleset_overrides_validate_ranges(kwargs: dict[str, int], message: str):
    with pytest.raises(ValueError, match=message):
        RuleSetOverrides(**kwargs)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"patch_id": " ", "season_id": "season_1", "name": "Patch", "description": "Desc"}, "patch_id"),
        ({"patch_id": "p1", "season_id": " ", "name": "Patch", "description": "Desc"}, "season_id"),
        ({"patch_id": "p1", "season_id": "season_1", "name": " ", "description": "Desc"}, "name"),
        ({"patch_id": "p1", "season_id": "season_1", "name": "Patch", "description": " "}, "description"),
        (
            {
                "patch_id": "p1",
                "season_id": "season_1",
                "name": "Patch",
                "description": "Desc",
                "power_stamina_cost_modifier": -1.0,
            },
            "power_stamina_cost_modifier",
        ),
    ],
)
def test_meta_patch_validates_required_fields(kwargs: dict[str, object], message: str):
    with pytest.raises(ValueError, match=message):
        MetaPatch(**kwargs)


def test_meta_module_has_no_db_boundary_imports():
    source = Path("src/dodgeball_sim/meta.py").read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "sqlite3" not in source
