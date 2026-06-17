from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .models import Player
from .stats import PlayerMatchStats


class FacilityType(str, Enum):
    VELOCITY_LAB = "velocity_lab"
    REACTION_WALL = "reaction_wall"
    RECOVERY_SUITE = "recovery_suite"
    FILM_ROOM = "film_room"
    ANALYTICS_DEPT = "analytics_dept"
    CHEMISTRY_LOUNGE = "chemistry_lounge"
    # V26 The Crowd — the web facility catalog. Training Hall lifts development;
    # Stadium + Merch Center feed the V26 fan economy (matchday + merch income).
    TRAINING_HALL = "training_hall"
    STADIUM = "stadium"
    MERCH_CENTER = "merch_center"


@dataclass(frozen=True)
class DevelopmentModifiers:
    power_growth_multiplier: float = 1.0
    dodge_growth_multiplier: float = 1.0
    catch_growth_multiplier: float = 1.0
    stamina_recovery_multiplier: float = 1.0
    overuse_injury_risk_delta: float = 0.0


@dataclass(frozen=True)
class FacilityDefinition:
    facility_type: FacilityType
    display_name: str
    category: str
    prestige_cost: int


MAX_ACTIVE_FACILITIES = 3
# V26: the web treats facilities as permanent owned buildings (not the CLI's
# per-season pick-3), so a club may hold more than MAX_ACTIVE_FACILITIES.
MAX_WEB_FACILITIES = 9
FACILITY_DEFINITIONS = {
    FacilityType.VELOCITY_LAB: FacilityDefinition(
        facility_type=FacilityType.VELOCITY_LAB,
        display_name="Velocity Lab",
        category="development",
        prestige_cost=3,
    ),
    FacilityType.REACTION_WALL: FacilityDefinition(
        facility_type=FacilityType.REACTION_WALL,
        display_name="Reaction Wall",
        category="development",
        prestige_cost=3,
    ),
    FacilityType.RECOVERY_SUITE: FacilityDefinition(
        facility_type=FacilityType.RECOVERY_SUITE,
        display_name="Recovery Suite",
        category="recovery",
        prestige_cost=2,
    ),
    FacilityType.FILM_ROOM: FacilityDefinition(
        facility_type=FacilityType.FILM_ROOM,
        display_name="Film Room",
        category="information",
        prestige_cost=2,
    ),
    FacilityType.ANALYTICS_DEPT: FacilityDefinition(
        facility_type=FacilityType.ANALYTICS_DEPT,
        display_name="Analytics Dept",
        category="information",
        prestige_cost=4,
    ),
    FacilityType.CHEMISTRY_LOUNGE: FacilityDefinition(
        facility_type=FacilityType.CHEMISTRY_LOUNGE,
        display_name="Chemistry Lounge",
        category="tactical_unlock",
        prestige_cost=2,
    ),
    FacilityType.TRAINING_HALL: FacilityDefinition(
        facility_type=FacilityType.TRAINING_HALL,
        display_name="Training Hall",
        category="development",
        prestige_cost=3,
    ),
    FacilityType.STADIUM: FacilityDefinition(
        facility_type=FacilityType.STADIUM,
        display_name="Stadium Expansion",
        category="fan_economy",
        prestige_cost=4,
    ),
    FacilityType.MERCH_CENTER: FacilityDefinition(
        facility_type=FacilityType.MERCH_CENTER,
        display_name="Merch Center",
        category="fan_economy",
        prestige_cost=3,
    ),
}


def normalize_facility_selection(
    facilities: Iterable[FacilityType | str],
    *,
    max_active: int = MAX_ACTIVE_FACILITIES,
) -> tuple[FacilityType, ...]:
    normalized: list[FacilityType] = []
    seen: set[FacilityType] = set()
    for facility in facilities:
        facility_type = _normalize_facility_type(facility)
        if facility_type in seen:
            continue
        normalized.append(facility_type)
        seen.add(facility_type)

    if len(normalized) > max_active:
        raise ValueError(f"Only {max_active} facilities may be active at once")
    return tuple(normalized)


def apply_facility_effects(
    player: Player,
    season_stats: PlayerMatchStats,
    facilities: Iterable[FacilityType | str],
) -> DevelopmentModifiers:
    """Return typed non-engine facility modifiers for development systems."""
    del player
    del season_stats
    selected = set(normalize_facility_selection(facilities, max_active=MAX_WEB_FACILITIES))

    return DevelopmentModifiers(
        power_growth_multiplier=1.15 if FacilityType.VELOCITY_LAB in selected else 1.0,
        dodge_growth_multiplier=1.15 if FacilityType.REACTION_WALL in selected else 1.0,
        catch_growth_multiplier=1.15 if FacilityType.REACTION_WALL in selected else 1.0,
        stamina_recovery_multiplier=1.20 if FacilityType.RECOVERY_SUITE in selected else 1.0,
        overuse_injury_risk_delta=0.05 if FacilityType.VELOCITY_LAB in selected else 0.0,
    )


def _normalize_facility_type(value: FacilityType | str) -> FacilityType:
    if isinstance(value, FacilityType):
        return value

    normalized = str(value).strip().lower().replace(" ", "_")
    aliases = {
        "velocity_lab": FacilityType.VELOCITY_LAB,
        "reaction_wall": FacilityType.REACTION_WALL,
        "recovery_suite": FacilityType.RECOVERY_SUITE,
        "film_room": FacilityType.FILM_ROOM,
        "analytics_dept": FacilityType.ANALYTICS_DEPT,
        "analytics_department": FacilityType.ANALYTICS_DEPT,
        "chemistry_lounge": FacilityType.CHEMISTRY_LOUNGE,
        "training_hall": FacilityType.TRAINING_HALL,
        "stadium": FacilityType.STADIUM,
        "merch_center": FacilityType.MERCH_CENTER,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(f"Unknown facility type: {value!r}") from exc


__all__ = [
    "DevelopmentModifiers",
    "FACILITY_DEFINITIONS",
    "MAX_ACTIVE_FACILITIES",
    "MAX_WEB_FACILITIES",
    "FacilityDefinition",
    "FacilityType",
    "apply_facility_effects",
    "normalize_facility_selection",
]
