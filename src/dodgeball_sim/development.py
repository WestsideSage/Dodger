from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping

from .facilities import apply_facility_effects
from .models import Player, PlayerArchetype, PlayerRatings
from .rng import DeterministicRNG
from .stats import PlayerMatchStats


# Fraction of a player's remaining OVR headroom (potential - current OVR)
# closed per fully-repped growth season (V18). Growth is budgeted directly in
# OVR points and spent on the five OVR skills, so this rate is the honest
# closure dynamic: n full seasons close 1-(1-rate)^n of the gap. The finish
# floor below terminates the geometric tail so the last few points actually
# arrive instead of asymptoting ~10 short of the displayed ceiling (V18
# BEFORE table: full-time starters closed only 20-34% of promised headroom).
# Pace is NOT a snowball knob: 0.40 and 0.35 were both probed on the engaged
# 8x10 sweep and produced the same user-vs-best-AI OVR-edge curve (+4.5 peak)
# and statistically indistinguishable title shares (41% / 49%) — the engaged
# hump is the structural recruiting asymmetry (3 user signings/offseason vs
# AI's 1, roster 12 vs trimmed 9) expressing through delivered ceilings, and
# is dispositioned as an owner item in the V18 sprint plan, not tuned here.
_HEADROOM_CLOSE_RATE = 0.40

# Minimum OVR gain per fully-repped growth season while headroom remains
# (scaled by reps, capped by remaining headroom).
_FINISH_FLOOR_OVR = 3.0

# Trajectory/staff/focus accelerate arrival; they may never teleport a player
# to their ceiling in a single season.
_MAX_CLOSE_RATE = 0.85

# Identity stats (no OVR weight) close their own gap to potential at this
# share of the OVR closure rate — steady, capped growth until V19 wires their
# match consumers.
_IDENTITY_CLOSE_SHARE = 0.5

# Archetype primaries grow ahead of the curve (V6 identity flavor): their
# allocation weight is biased by 1 + _PRIMARY_BIAS x primary_weight. Gap-
# proportional allocation redirects the budget as primaries cap out, so the
# bias shapes the arc without breaking ceiling delivery.
_PRIMARY_BIAS = 0.5

_OVR_STATS = ("accuracy", "power", "dodge", "catch", "stamina")
_IDENTITY_STATS = ("tactical_iq", "catch_courage", "throw_selection_iq", "conditioning_curve")

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
    matches_played: int | None = None,
    club_matches: int | None = None,
) -> Player:
    """Apply one offseason of deterministic development to a player.

    V18 growth model: each season closes a fraction of the player's remaining
    OVR headroom (effective potential - current OVR), budgeted directly in OVR
    points and spent on the five OVR skills gap-proportionally, so a full-time
    starter actually reaches the ceiling the UI displays by the end of their
    peak window. Growth is gated by playing time (Reps) and modulated by
    trajectory, dev_focus, and staff.

    Reps signal: when ``matches_played`` and ``club_matches`` are provided, the
    gate is the fraction of the club's recorded matches the player appeared in
    (a year-round starter = 1.0). Otherwise it falls back to the legacy
    ``minutes_played / 1000`` formula — which never matched either engine's
    actual scale (a starter who played EVERY match of a season accrues a
    measured ~64-206 event-tick "minutes" on the official engine and ~10-27 on
    the rec engine), so every player past their practice window developed at
    1-20% of the intended rate and stalled 15-22 OVR short of their displayed
    ceiling. Callers with access to the season's match records should pass the
    appearance counts.
    """
    facility_set = {facility.strip().lower() for facility in facilities}
    base_potential = _clamp(player.traits.potential, 0.0, 100.0)
    potential_floor = _TRAJECTORY_POTENTIAL_FLOOR.get(trajectory)
    potential = max(base_potential, potential_floor) if potential_floor is not None else base_potential
    growth_multiplier = _TRAJECTORY_GROWTH_MULTIPLIER.get(trajectory, 1.00)
    growth_curve = _normalize_growth_curve(player.traits.growth_curve)
    peak_start, peak_end = _peak_window(growth_curve)
    facility_modifiers = apply_facility_effects(player, season_stats, facility_set)

    # 1. OVR headroom, in true (unrounded) OVR points. The "Ceiling" the UI
    # displays is potential on the OVR scale, so growth is budgeted directly
    # in OVR terms and spent on the five OVR skills (V18). The old pool spread
    # 40% of growth across all nine rated stats while OVR averages five, so
    # 18-48% of every season's growth — depending on archetype primaries —
    # never moved OVR, and full-time starters stalled ~10 OVR short of the
    # displayed ceiling.
    ovr_now = sum(float(getattr(player.ratings, stat)) for stat in _OVR_STATS) / float(
        len(_OVR_STATS)
    )
    headroom = max(0.0, potential - ovr_now)

    # Reps gate: young players develop through practice even without match
    # minutes; older players need real playing time to keep improving.
    if player.age < peak_start:
        # Youth always get a full practice season.
        reps_factor = 1.0
    elif matches_played is not None and club_matches is not None and club_matches > 0:
        # Appearance-based gate: fraction of the club's matches the player
        # appeared in. Engine-agnostic, so a regular starter develops at the
        # full headroom rate through their peak window instead of being
        # starved by the legacy minutes scale (see docstring).
        reps_factor = min(1.0, max(0.0, matches_played / club_matches))
    else:
        # Legacy fallback for callers without appearance counts.
        reps_factor = min(1.0, float(season_stats.minutes_played) / 1000.0)

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

    # 4. Allocation. Per-stat noise is rolled in the legacy stat order so the
    # RNG stream feeding the dev-trait upgrade branch is unchanged.
    effective_staff_modifier = max(0.0, staff_development_modifier)
    ratings = player.ratings
    noise = {stat: rng.roll(-0.35, 0.35) for stat in multipliers}
    deltas: dict[str, int] = {}

    if player.age > peak_end:
        # Decline path (unchanged by V18): mitigated by performance, facility,
        # and staff.
        performance = _performance_signal(season_stats)
        decline_years = player.age - peak_end
        for stat in multipliers:
            f_bonus = _facility_bonus(stat, facility_modifiers)
            delta_f = (
                -0.5 * decline_years
                + performance * 0.5
                + f_bonus * 0.5
                + noise[stat] * 0.5
                + (effective_staff_modifier * 2.0)
            )
            delta = int(round(delta_f))
            # Don't let it be positive from mitigation alone unless performance was great
            if delta > 0 and performance < 0.5:
                delta = 0
            deltas[stat] = delta
    else:
        # Growth path (V18): close a fraction of the remaining OVR headroom
        # each season, with an arrival floor so the final points land instead
        # of asymptoting. The budget (in stat points: 1 OVR = 5 points) is
        # split across the five OVR skills proportionally to each stat's own
        # gap to potential — the only allocation that can deliver the ceiling,
        # since every stat caps at potential and OVR is their mean — biased
        # toward archetype primaries while they still have room.
        ovr_gaps = {s: max(0.0, potential - float(getattr(ratings, s))) for s in _OVR_STATS}
        primary_bias = {s: 1.0 for s in multipliers}
        for stat_name, stat_weight in _primary_stats_for_archetype(
            player.archetype, player.ratings
        ):
            primary_bias[stat_name] = 1.0 + _PRIMARY_BIAS * stat_weight
        weights = {
            s: ovr_gaps[s] * multipliers[s] * primary_bias[s] for s in _OVR_STATS
        }
        weight_total = sum(weights.values())
        gap_total = sum(ovr_gaps.values())
        # Focus multipliers scale the season's pace (their uniform part) and
        # shift its distribution (their relative part), preserving the old
        # slice semantics: YOUTH_ACCELERATION speeds the whole season up,
        # STRENGTH_AND_CONDITIONING trades accuracy/dodge/catch pace for
        # power/stamina emphasis.
        focus_scale = (
            sum(ovr_gaps[s] * multipliers[s] for s in _OVR_STATS) / gap_total
            if gap_total > 0
            else 1.0
        )
        close_rate = min(
            _MAX_CLOSE_RATE,
            _HEADROOM_CLOSE_RATE
            * growth_multiplier
            * focus_scale
            * (1.0 + effective_staff_modifier),
        )
        if headroom > 0.0 and weight_total > 0.0:
            target_ovr_gain = (
                min(headroom, max(headroom * close_rate, _FINISH_FLOOR_OVR)) * reps_factor
            )
            budget = target_ovr_gain * len(_OVR_STATS) + effective_staff_modifier * 20.0
        else:
            budget = 0.0
        for stat in _OVR_STATS:
            share = weights[stat] / weight_total if weight_total > 0 else 0.0
            delta = int(
                round(budget * share + _facility_bonus(stat, facility_modifiers) + noise[stat])
            )
            deltas[stat] = max(0, delta)
        # Identity stats (no OVR weight) close their own gap on a parallel
        # track at half pace — capped at potential like everything else.
        for stat in _IDENTITY_STATS:
            gap = max(0.0, potential - float(getattr(ratings, stat)))
            identity_rate = (
                min(
                    _MAX_CLOSE_RATE,
                    _HEADROOM_CLOSE_RATE
                    * multipliers[stat]
                    * primary_bias[stat]
                    * growth_multiplier
                    * (1.0 + effective_staff_modifier),
                )
                * _IDENTITY_CLOSE_SHARE
            )
            delta = int(
                round(
                    gap * identity_rate * reps_factor
                    + _facility_bonus(stat, facility_modifiers)
                    + noise[stat]
                )
            )
            deltas[stat] = max(0, delta)

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
            new_potential = min(100, new_potential + rng.choice((2, 3, 4, 5, 6)))
            
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
