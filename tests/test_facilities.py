from __future__ import annotations

from pathlib import Path

import pytest

from dodgeball_sim.facilities import (
    FACILITY_DEFINITIONS,
    DevelopmentModifiers,
    FacilityType,
    apply_facility_effects,
    normalize_facility_selection,
)
from dodgeball_sim.stats import PlayerMatchStats

from .factories import make_player


def test_normalize_facility_selection_accepts_strings_and_deduplicates():
    selected = normalize_facility_selection(
        ["Velocity Lab", "reaction_wall", FacilityType.REACTION_WALL]
    )

    assert selected == (FacilityType.VELOCITY_LAB, FacilityType.REACTION_WALL)


def test_normalize_facility_selection_rejects_unknown_facility():
    with pytest.raises(ValueError):
        normalize_facility_selection(["laser dome"])


def test_normalize_facility_selection_enforces_three_facility_cap():
    with pytest.raises(ValueError):
        normalize_facility_selection(
            [
                FacilityType.VELOCITY_LAB,
                FacilityType.REACTION_WALL,
                FacilityType.RECOVERY_SUITE,
                FacilityType.FILM_ROOM,
            ]
        )


def test_apply_facility_effects_returns_typed_modifiers():
    modifiers = apply_facility_effects(
        player=make_player("club_player"),
        season_stats=PlayerMatchStats(throws_attempted=12),
        facilities=[
            FacilityType.VELOCITY_LAB,
            FacilityType.REACTION_WALL,
            FacilityType.CHEMISTRY_LOUNGE,
        ],
    )

    assert isinstance(modifiers, DevelopmentModifiers)
    assert modifiers.power_growth_multiplier == 1.15
    assert modifiers.dodge_growth_multiplier == 1.15
    assert modifiers.catch_growth_multiplier == 1.15
    assert modifiers.stamina_recovery_multiplier == 1.0
    assert modifiers.overuse_injury_risk_delta == 0.05
    assert modifiers.scouting_budget_tier_bonus == 0
    assert modifiers.unlocks_sync_throw is True


def test_apply_facility_effects_information_and_recovery_effects_are_bounded():
    modifiers = apply_facility_effects(
        player=make_player("info_player"),
        season_stats=PlayerMatchStats(),
        facilities=[
            FacilityType.RECOVERY_SUITE,
            FacilityType.FILM_ROOM,
            FacilityType.ANALYTICS_DEPT,
        ],
    )

    assert modifiers.power_growth_multiplier == 1.0
    assert modifiers.stamina_recovery_multiplier == 1.20
    assert modifiers.scouting_budget_tier_bonus == 1
    assert modifiers.scouting_precision_bonus == 3
    assert modifiers.unlocks_sync_throw is False


def test_facility_catalog_covers_all_supported_facilities():
    assert set(FACILITY_DEFINITIONS) == set(FacilityType)


def test_facilities_module_has_no_db_boundary_imports():
    source = Path("src/dodgeball_sim/facilities.py").read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "sqlite3" not in source
