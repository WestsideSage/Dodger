from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping

from .facilities import apply_facility_effects
from .models import Player, PlayerArchetype, PlayerRatings
from .rng import DeterministicRNG
from .stats import PlayerMatchStats


_TRAJECTORY_GROWTH_MULTIPLIER = {
    None: 1.00,
    "NORMAL": 1.00,
    "IMPACT": 1.20,
    "STAR": 1.45,
    "GENERATIONAL": 1.75,
}

_TRAJECTORY_POTENTIAL_FLOOR = {
    None: None,
    "NORMAL": 72.0,
    "IMPACT": 82.0,
    "STAR": 90.0,
    "GENERATIONAL": 96.0,
}

_BASE_PRIMARY_STATS: dict[PlayerArchetype, tuple[str, ...]] = {
    PlayerArchetype.THROWER: ("accuracy", "power"),
    PlayerArchetype.CATCHER: ("catch", "catch_courage"),
    PlayerArchetype.BALL_HAWK: ("stamina", "throw_selection_iq"),
    PlayerArchetype.DODGER_ANCHOR: ("dodge", "tactical_iq"),
}

_HYBRID_DECOMPOSITION: dict[PlayerArchetype, tuple[PlayerArchetype, PlayerArchetype]] = {
    PlayerArchetype.THROWER_CATCHER: (PlayerArchetype.THROWER, PlayerArchetype.CATCHER),
    PlayerArchetype.THROWER_DODGER: (PlayerArchetype.THROWER, PlayerArchetype.DODGER_ANCHOR),
    PlayerArchetype.CATCHER_HAWK: (PlayerArchetype.CATCHER, PlayerArchetype.BALL_HAWK),
    PlayerArchetype.HAWK_DODGER: (PlayerArchetype.BALL_HAWK, PlayerArchetype.DODGER_ANCHOR),
}

_PRIMARY_WEIGHT = 0.6
_SECONDARY_WEIGHT = 0.4


def _primary_stats_for_archetype(
    archetype: PlayerArchetype, ratings: PlayerRatings | None = None
) -> tuple[tuple[str, float], ...]:
    if archetype in _BASE_PRIMARY_STATS:
        return tuple((stat, 1.0) for stat in _BASE_PRIMARY_STATS[archetype])
    if archetype in _HYBRID_DECOMPOSITION:
        if ratings is not None:
            base1, base2 = _HYBRID_DECOMPOSITION[archetype]
            def get_base_score(base_arc: PlayerArchetype) -> float:
                if base_arc == PlayerArchetype.THROWER:
                    return ratings.accuracy + ratings.power
                if base_arc == PlayerArchetype.CATCHER:
                    return ratings.catch + ratings.catch_courage
                if base_arc == PlayerArchetype.BALL_HAWK:
                    return ratings.stamina + ratings.throw_selection_iq
                if base_arc == PlayerArchetype.DODGER_ANCHOR:
                    return ratings.dodge + ratings.tactical_iq
                return 0.0

            score1 = get_base_score(base1)
            score2 = get_base_score(base2)
            if score1 > score2:
                primary, secondary = base1, base2
            elif score2 > score1:
                primary, secondary = base2, base1
            else:
                if base1.name < base2.name:
                    primary, secondary = base1, base2
                else:
                    primary, secondary = base2, base1
        else:
            primary, secondary = _HYBRID_DECOMPOSITION[archetype]
        return (
            tuple((stat, _PRIMARY_WEIGHT) for stat in _BASE_PRIMARY_STATS[primary])
            + tuple((stat, _SECONDARY_WEIGHT) for stat in _BASE_PRIMARY_STATS[secondary])
        )
    raise ValueError(f"No primary-stat mapping for archetype {archetype!r}")


def apply_season_development(
    player: Player,
    season_stats: PlayerMatchStats,
    facilities: Iterable[str],
    rng: DeterministicRNG,
    trajectory: str | None = None,
    dev_focus: str = "BALANCED",
    staff_development_modifier: float = 0.0,
) -> Player:
    """Apply one offseason of deterministic development to a player using V6 Reps-based formula.

    Growth is driven by `minutes_played` (Reps), modulated by potential and dev_focus.
    """
    facility_set = {facility.strip().lower() for facility in facilities}
    base_potential = _clamp(player.traits.potential, 0.0, 100.0)
    potential_floor = _TRAJECTORY_POTENTIAL_FLOOR.get(trajectory)
    potential = max(base_potential, potential_floor) if potential_floor is not None else base_potential
    growth_multiplier = _TRAJECTORY_GROWTH_MULTIPLIER.get(trajectory, 1.00)
    growth_curve = _normalize_growth_curve(player.traits.growth_curve)
    peak_start, peak_end = _peak_window(growth_curve)
    facility_modifiers = apply_facility_effects(player, season_stats, facility_set)

    # 1. Base Growth based on Reps
    # If the player didn't play but is young, give them a baseline of "practice reps" (equivalent to 200 minutes)
    reps = max(season_stats.minutes_played, 200 if player.age < peak_start else 0)
    base_growth = (reps / 1000.0) * 15.0

    # 2. Potential Modifier
    # Scale aggressively so Elite players grow much faster
    potential_diff = potential - 50.0
    if potential_diff > 0:
        potential_modifier = 1.0 + (potential_diff / 40.0) ** 1.5
    else:
        potential_modifier = max(0.2, 1.0 + (potential_diff / 50.0))

    # 3. Focus Multipliers
    multipliers = {
        "accuracy": 1.0,
        "power": 1.0,
        "dodge": 1.0,
        "catch": 1.0,
        "stamina": 1.0,
        "tactical_iq": 1.0,
        "catch_courage": 1.0,
        "throw_selection_iq": 1.0,
        "conditioning_curve": 1.0,
    }
    
    dev_focus = dev_focus.upper()
    if dev_focus == "YOUTH_ACCELERATION":
        mult = 1.5 if player.age <= 22 else 0.5
        for k in multipliers:
            multipliers[k] = mult
    elif dev_focus == "TACTICAL_DRILLS":
        multipliers["tactical_iq"] = 1.5
        multipliers["power"] = 0.8
        multipliers["dodge"] = 0.8
        multipliers["stamina"] = 0.8
    elif dev_focus == "STRENGTH_AND_CONDITIONING":
        multipliers["power"] = 1.5
        multipliers["stamina"] = 1.5
        multipliers["accuracy"] = 0.8
        multipliers["dodge"] = 0.8
        multipliers["catch"] = 0.8

    # 4. Final Allocation weighting
    pool = base_growth * potential_modifier * growth_multiplier
    effective_staff_modifier = max(0.0, staff_development_modifier)
    flat_bonus = effective_staff_modifier * 20.0
    pool = pool * (1.0 + effective_staff_modifier) + flat_bonus
    
    primary_stats = _primary_stats_for_archetype(player.archetype, player.ratings)
    total_primary_weight = sum(weight for _, weight in primary_stats)
    base_weight = 0.4 / len(multipliers)
    weights = {s: base_weight for s in multipliers}
    for stat_name, stat_weight in primary_stats:
        weights[stat_name] += 0.6 * (stat_weight / max(total_primary_weight, 1e-9))

    ratings = player.ratings
    deltas = {}
    for stat in multipliers:
        slice_amount = pool * weights[stat] * multipliers[stat]
        noise = rng.roll(-0.35, 0.35)
        f_bonus = _facility_bonus(stat, facility_modifiers)
        
        if player.age > peak_end:
            decline_years = player.age - peak_end
            performance = _performance_signal(season_stats)
            # Decline mitigated by performance, facility, and staff
            delta_f = -0.5 * decline_years + performance * 0.5 + f_bonus * 0.5 + noise * 0.5 + (effective_staff_modifier * 2.0)
            delta = int(round(delta_f))
            # Don't let it be positive from mitigation alone unless performance was great
            if delta > 0 and performance < 0.5:
                delta = 0
        else:
            delta_f = slice_amount + f_bonus + noise
            delta = int(round(delta_f))
            
        deltas[stat] = delta

    next_ratings = PlayerRatings(
        accuracy=_apply_delta(ratings.accuracy, deltas["accuracy"], potential),
        power=_apply_delta(ratings.power, deltas["power"], potential),
        dodge=_apply_delta(ratings.dodge, deltas["dodge"], potential),
        catch=_apply_delta(ratings.catch, deltas["catch"], potential),
        stamina=_apply_delta(ratings.stamina, deltas["stamina"], potential),
        tactical_iq=_apply_delta(ratings.tactical_iq, deltas["tactical_iq"], potential),
        catch_courage=_apply_delta(ratings.catch_courage, deltas["catch_courage"], potential),
        throw_selection_iq=_apply_delta(ratings.throw_selection_iq, deltas["throw_selection_iq"], potential),
        conditioning_curve=_apply_delta(ratings.conditioning_curve, deltas["conditioning_curve"], int(potential)),
    ).apply_bounds()
    
    # Dev trait upgrades
    new_potential = int(potential)
    if player.age <= peak_end:
        # Check if they had a great season and good coaching
        performance = _performance_signal(season_stats)
        upgrade_chance = (performance * 0.5) + (effective_staff_modifier * 0.5)
        if upgrade_chance > 0.6 and rng.unit() < upgrade_chance:
            new_potential = min(100, new_potential + rng.randint(2, 6))
            
    next_traits = replace(player.traits, potential=new_potential)
    
    return replace(player, ratings=next_ratings, traits=next_traits, newcomer=False)


def should_retire(player: Player, career_stats: Mapping[str, float] | None) -> bool:
    """Return whether a player should retire based on age and decline signals."""
    stats = dict(career_stats or {})
    seasons_played = int(stats.get("seasons_played", 0))
    recent_eliminations = float(stats.get("recent_eliminations", stats.get("total_eliminations", 0.0)))
    overall = player.overall_skill()

    if player.age >= 40:
        return True
    if player.age < 34:
        return False
    if player.age >= 38 and overall < 58:
        return True
    if player.age >= 36 and seasons_played >= 8 and recent_eliminations < 4.0:
        return True
    if player.age >= 34 and seasons_played >= 10 and overall < 52:
        return True
    return False


def fatigue_consistency_modifier(consistency: float) -> float:
    """Scale fatigue penalties; higher consistency means smaller penalties."""
    normalized = _normalize_unit(consistency)
    return round(1.0 - ((normalized - 0.5) * 0.4), 4)


def pressure_context(player: Player, reason: str | None) -> dict[str, float | bool | str]:
    """Return the logged pressure modifier payload for a qualifying trigger."""
    if not reason:
        return {"pressure_active": False}
    normalized = _normalize_unit(player.traits.pressure)
    modifier = round((normalized - 0.5) * 0.08, 4)
    return {
        "pressure_active": True,
        "pressure_reason": reason,
        "pressure_modifier": modifier,
    }


def _apply_delta(current_value: int, delta: int, potential: int) -> int:
    if delta >= 0:
        growth_cap = max(current_value, potential)
        return min(growth_cap, current_value + delta)
    return max(1, current_value + delta)


def _performance_signal(season_stats: PlayerMatchStats) -> float:
    positives = (
        season_stats.eliminations_by_throw * 1.2
        + season_stats.catches_made * 1.5
        + season_stats.dodges_successful * 0.8
        + season_stats.elimination_plus_minus * 0.15
    )
    negatives = season_stats.times_eliminated * 0.9
    raw = (positives - negatives) / 20.0
    return _clamp(raw, -1.0, 1.0)


def _facility_bonus(stat_name: str, facility_modifiers) -> float:
    if stat_name == "power":
        return (facility_modifiers.power_growth_multiplier - 1.0) * 1.3
    if stat_name == "dodge":
        return (facility_modifiers.dodge_growth_multiplier - 1.0) * 1.3
    if stat_name == "catch":
        return (facility_modifiers.catch_growth_multiplier - 1.0) * 1.3
    if stat_name == "stamina":
        return (facility_modifiers.stamina_recovery_multiplier - 1.0)
    return 0.0


def _peak_window(growth_curve: str) -> tuple[int, int]:
    if growth_curve == "early":
        return 23, 26
    if growth_curve == "late":
        return 27, 30
    return 25, 28


def _normalize_growth_curve(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"early", "steady", "late"}:
            return normalized
    numeric = float(value)
    if numeric < 33.34:
        return "early"
    if numeric > 66.66:
        return "late"
    return "steady"


def _normalize_unit(value: float) -> float:
    numeric = float(value)
    if numeric > 1.0:
        numeric = numeric / 100.0
    return _clamp(numeric, 0.0, 1.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

def calculate_potential_tier(potential: float) -> str:
    if potential >= 90:
        return "Elite"
    if potential >= 82:
        return "High"
    if potential >= 72:
        return "Mid"
    if potential >= 62:
        return "Low"
    return "Raw"

__all__ = [
    "_primary_stats_for_archetype",
    "apply_season_development",
    "calculate_potential_tier",
    "fatigue_consistency_modifier",
    "pressure_context",
    "should_retire",
]
