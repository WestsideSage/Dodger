from __future__ import annotations

"""V2-A Stateful Scouting Model pure engine module.

This module owns deterministic scouting helpers and data contracts. It has no
SQLite or Tkinter boundary; persistence and UI consume these values from the
outside.
"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Mapping, Optional, Set, Tuple

from .config import ScoutingBalanceConfig
from .rng import derive_seed


class ScoutingTier(str, Enum):
    UNKNOWN = "UNKNOWN"
    GLIMPSED = "GLIMPSED"
    KNOWN = "KNOWN"
    VERIFIED = "VERIFIED"


class ScoutingAxis(str, Enum):
    RATINGS = "ratings"
    ARCHETYPE = "archetype"
    TRAITS = "traits"
    TRAJECTORY = "trajectory"


class Trajectory(str, Enum):
    NORMAL = "NORMAL"
    IMPACT = "IMPACT"
    STAR = "STAR"
    GENERATIONAL = "GENERATIONAL"


class ScoutMode(str, Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class ScoutPriority(str, Enum):
    TOP_PUBLIC_OVR = "TOP_PUBLIC_OVR"
    SPECIALTY_FIT = "SPECIALTY_FIT"
    USER_PINNED = "USER_PINNED"


class TraitSense(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CeilingLabel(str, Enum):
    HIGH_CEILING = "HIGH_CEILING"
    SOLID = "SOLID"
    STANDARD = "STANDARD"


@dataclass(frozen=True)
class Prospect:
    """A prospect carrying hidden truths plus a wide public baseline."""

    player_id: str
    class_year: int
    name: str
    age: int
    hometown: str
    hidden_ratings: Dict[str, float]
    hidden_trajectory: str
    hidden_traits: List[str]
    public_archetype_guess: str
    public_ratings_band: Dict[str, Tuple[int, int]]

    def true_overall(self) -> float:
        return sum(self.hidden_ratings.values()) / len(self.hidden_ratings)

    def true_archetype(self) -> str:
        archetype_map = {
            "accuracy": "Sharpshooter",
            "power": "Enforcer",
            "dodge": "Escape Artist",
            "catch": "Ball Hawk",
            "stamina": "Iron Engine",
        }
        rating_keys = ("accuracy", "power", "dodge", "catch", "stamina")
        present = {key: self.hidden_ratings.get(key, 0.0) for key in rating_keys}
        dominant = max(present, key=present.get)
        return archetype_map[dominant]


@dataclass(frozen=True)
class Scout:
    """A named scout. Static for V2-A."""

    scout_id: str
    name: str
    base_accuracy: float
    archetype_affinities: Tuple[str, ...]
    archetype_weakness: str
    trait_sense: str


@dataclass(frozen=True)
class ScoutingState:
    """Per-prospect scouting state across the four axes."""

    player_id: str
    ratings_tier: str
    archetype_tier: str
    traits_tier: str
    trajectory_tier: str
    scout_points: Dict[str, int]
    last_updated_week: int


@dataclass(frozen=True)
class ScoutAssignment:
    scout_id: str
    player_id: Optional[str]
    started_week: int


@dataclass(frozen=True)
class ScoutStrategyState:
    scout_id: str
    mode: str
    priority: str
    archetype_filter: Tuple[str, ...]
    pinned_prospects: Tuple[str, ...]


@dataclass(frozen=True)
class ScoutContribution:
    scout_id: str
    player_id: str
    season: int
    first_assigned_week: int
    last_active_week: int
    weeks_worked: int
    contributed_scout_points: Dict[str, int]
    last_estimated_ratings_band: Dict[str, Tuple[int, int]]
    last_estimated_archetype: Optional[str]
    last_estimated_traits: Tuple[str, ...]
    last_estimated_ceiling: Optional[str]
    last_estimated_trajectory: Optional[str]


@dataclass(frozen=True)
class SeededScoutProfile:
    """Starter scout profile seeded at career creation."""

    scout_id: str
    name: str
    base_accuracy: float
    archetype_affinities: Tuple[str, ...]
    archetype_weakness: str
    trait_sense: str


DEFAULT_SCOUT_PROFILES: Tuple[SeededScoutProfile, ...] = (
    SeededScoutProfile(
        scout_id="vera",
        name="Vera Khan",
        base_accuracy=1.10,
        archetype_affinities=("Enforcer",),
        archetype_weakness="Escape Artist",
        trait_sense=TraitSense.MEDIUM.value,
    ),
    SeededScoutProfile(
        scout_id="bram",
        name="Bram Tessen",
        base_accuracy=0.90,
        archetype_affinities=("Ball Hawk",),
        archetype_weakness="Iron Engine",
        trait_sense=TraitSense.HIGH.value,
    ),
    SeededScoutProfile(
        scout_id="linnea",
        name="Linnea Voss",
        base_accuracy=1.00,
        archetype_affinities=("Sharpshooter", "Escape Artist"),
        archetype_weakness="Enforcer",
        trait_sense=TraitSense.LOW.value,
    ),
)


@dataclass(frozen=True)
class ScoutingSnapshot:
    """All V2-A runtime scouting state in one pure data bundle."""

    prospects: Mapping[str, Prospect]
    scouting_states: Mapping[str, ScoutingState]
    revealed_traits: Mapping[str, Tuple[str, ...]]
    ceiling_labels: Mapping[str, str]
    scouts: Mapping[str, Scout]
    assignments: Mapping[str, ScoutAssignment]
    strategies: Mapping[str, ScoutStrategyState]
    contributions: Mapping[Tuple[str, str, int], ScoutContribution]


@dataclass(frozen=True)
class ScoutingDomainEvent:
    season: int
    week: int
    event_type: str
    player_id: Optional[str]
    scout_id: Optional[str]
    payload: Dict[str, object]


@dataclass(frozen=True)
class RevealedTraitsUpdate:
    player_id: str
    traits: Tuple[str, ...]
    revealed_at_week: int


@dataclass(frozen=True)
class CeilingLabelUpdate:
    player_id: str
    label: str
    revealed_at_week: int
    revealed_by_scout_id: str


@dataclass(frozen=True)
class ScoutingWeekAdvance:
    assignments_to_save: Tuple[ScoutAssignment, ...]
    states_to_save: Tuple[ScoutingState, ...]
    events: Tuple[ScoutingDomainEvent, ...]
    revealed_traits_to_save: Tuple[RevealedTraitsUpdate, ...]
    ceiling_labels_to_save: Tuple[CeilingLabelUpdate, ...]
    contributions_to_save: Tuple[ScoutContribution, ...]


_TIER_ORDER = (
    ScoutingTier.UNKNOWN.value,
    ScoutingTier.GLIMPSED.value,
    ScoutingTier.KNOWN.value,
    ScoutingTier.VERIFIED.value,
)


def tier_for_points(points: int, config: ScoutingBalanceConfig) -> str:
    """Return the scouting tier for cumulative scout points."""
    if points >= config.tier_thresholds[ScoutingTier.VERIFIED.value]:
        return ScoutingTier.VERIFIED.value
    if points >= config.tier_thresholds[ScoutingTier.KNOWN.value]:
        return ScoutingTier.KNOWN.value
    if points >= config.tier_thresholds[ScoutingTier.GLIMPSED.value]:
        return ScoutingTier.GLIMPSED.value
    return ScoutingTier.UNKNOWN.value


def compute_scout_points_for_axis(
    scout: Scout,
    prospect_archetype: str,
    axis: str,
    jitter: float,
    config: ScoutingBalanceConfig,
) -> int:
    """Compute scout points gained for one scout, prospect, and axis."""
    if prospect_archetype in scout.archetype_affinities:
        archetype_modifier = config.archetype_affinity_multiplier
    elif prospect_archetype == scout.archetype_weakness:
        archetype_modifier = config.archetype_weakness_multiplier
    else:
        archetype_modifier = config.archetype_neutral_multiplier

    if axis in (ScoutingAxis.TRAITS.value, ScoutingAxis.TRAJECTORY.value):
        axis_modifier = config.trait_sense_multipliers[scout.trait_sense]
    else:
        axis_modifier = 1.0

    raw = scout.base_accuracy * archetype_modifier * axis_modifier * jitter
    raw *= config.weekly_scout_point_base
    return int(raw + 0.5)


def advance_scouting_state(
    state: ScoutingState,
    scout: Scout,
    prospect_archetype: str,
    week: int,
    seed: int,
    config: ScoutingBalanceConfig,
) -> Tuple[ScoutingState, List[Dict[str, object]]]:
    """Advance all four scouting axes by one week and emit tier-up events."""
    rng = random.Random(seed)
    jitter = config.jitter_min + (config.jitter_max - config.jitter_min) * rng.random()

    new_points = dict(state.scout_points)
    new_tiers = {
        ScoutingAxis.RATINGS.value: state.ratings_tier,
        ScoutingAxis.ARCHETYPE.value: state.archetype_tier,
        ScoutingAxis.TRAITS.value: state.traits_tier,
        ScoutingAxis.TRAJECTORY.value: state.trajectory_tier,
    }
    events: List[Dict[str, object]] = []

    for axis in (
        ScoutingAxis.RATINGS.value,
        ScoutingAxis.ARCHETYPE.value,
        ScoutingAxis.TRAITS.value,
        ScoutingAxis.TRAJECTORY.value,
    ):
        gained = compute_scout_points_for_axis(scout, prospect_archetype, axis, jitter, config)
        new_total = new_points.get(axis, 0) + gained
        new_points[axis] = new_total
        new_tier = tier_for_points(new_total, config)
        old_tier = new_tiers[axis]
        if new_tier != old_tier:
            events.append(
                {
                    "event_type": f"TIER_UP_{axis.upper()}",
                    "payload": {
                        "player_id": state.player_id,
                        "scout_id": scout.scout_id,
                        "axis": axis,
                        "old_tier": old_tier,
                        "new_tier": new_tier,
                        "scout_points": new_total,
                        "week": week,
                    },
                }
            )
            new_tiers[axis] = new_tier

    return (
        ScoutingState(
            player_id=state.player_id,
            ratings_tier=new_tiers[ScoutingAxis.RATINGS.value],
            archetype_tier=new_tiers[ScoutingAxis.ARCHETYPE.value],
            traits_tier=new_tiers[ScoutingAxis.TRAITS.value],
            trajectory_tier=new_tiers[ScoutingAxis.TRAJECTORY.value],
            scout_points=new_points,
            last_updated_week=week,
        ),
        events,
    )


def ceiling_label_for_trajectory(trajectory: str) -> str:
    """Map hidden trajectory into the coarser CEILING label."""
    if trajectory in (Trajectory.STAR.value, Trajectory.GENERATIONAL.value):
        return CeilingLabel.HIGH_CEILING.value
    if trajectory == Trajectory.IMPACT.value:
        return CeilingLabel.SOLID.value
    if trajectory == Trajectory.NORMAL.value:
        return CeilingLabel.STANDARD.value
    raise ValueError(f"Unknown trajectory: {trajectory!r}")


def ceiling_reveal_eligible(ratings_tier: str, scout_trait_sense: str) -> bool:
    """Return whether CEILING can surface for this ratings tier and scout."""
    if scout_trait_sense == TraitSense.HIGH.value:
        return _TIER_ORDER.index(ratings_tier) >= _TIER_ORDER.index(ScoutingTier.KNOWN.value)
    return ratings_tier == ScoutingTier.VERIFIED.value


def pick_traits_to_reveal(
    player_id: str,
    true_traits: Tuple[str, ...],
    tier: str,
    root_seed: int,
) -> Tuple[str, ...]:
    """Deterministically choose the true traits visible at a scouting tier."""
    if not true_traits or tier == ScoutingTier.UNKNOWN.value:
        return ()

    seed = derive_seed(root_seed, "trait_reveal_pick", player_id)
    rng = random.Random(seed)
    ordered = list(true_traits)
    rng.shuffle(ordered)

    if tier == ScoutingTier.GLIMPSED.value:
        return tuple(ordered[:1])
    if tier == ScoutingTier.KNOWN.value:
        return tuple(ordered[:2])
    if tier == ScoutingTier.VERIFIED.value:
        return tuple(ordered)
    raise ValueError(f"Unknown tier: {tier!r}")


def select_auto_scout_target(
    scout: Scout,
    strategy: ScoutStrategyState,
    prospects: Mapping[str, Prospect],
    already_assigned_player_ids: Set[str],
    week: int,
    root_seed: int,
) -> Optional[str]:
    """Deterministically pick the next Auto-scout target."""
    eligible = {
        player_id: prospect
        for player_id, prospect in prospects.items()
        if player_id not in already_assigned_player_ids
    }
    if not eligible:
        return None

    if strategy.priority == ScoutPriority.SPECIALTY_FIT.value:
        affinities = set(scout.archetype_affinities)
        filtered = {
            player_id: prospect
            for player_id, prospect in eligible.items()
            if prospect.public_archetype_guess in affinities
        }
        if filtered:
            eligible = filtered

    def ovr_mid(prospect: Prospect) -> int:
        low, high = prospect.public_ratings_band["ovr"]
        return (low + high) // 2

    best_score = max(ovr_mid(prospect) for prospect in eligible.values())
    tied = [player_id for player_id, prospect in eligible.items() if ovr_mid(prospect) == best_score]
    if len(tied) == 1:
        return tied[0]

    seed = derive_seed(root_seed, "auto_scout_pick", scout.scout_id, str(week))
    rng = random.Random(seed)
    rng.shuffle(tied)
    return tied[0]


def apply_carry_forward_decay(
    state: ScoutingState,
    config: ScoutingBalanceConfig,
) -> ScoutingState:
    """Drop each scouting axis by one tier and cap points at the new tier."""
    decayed_tiers: Dict[str, str] = {}
    decayed_points: Dict[str, int] = {}

    for axis, tier in (
        (ScoutingAxis.RATINGS.value, state.ratings_tier),
        (ScoutingAxis.ARCHETYPE.value, state.archetype_tier),
        (ScoutingAxis.TRAITS.value, state.traits_tier),
        (ScoutingAxis.TRAJECTORY.value, state.trajectory_tier),
    ):
        if tier == ScoutingTier.VERIFIED.value:
            decayed_tiers[axis] = ScoutingTier.KNOWN.value
            decayed_points[axis] = config.tier_thresholds[ScoutingTier.KNOWN.value]
        elif tier == ScoutingTier.KNOWN.value:
            decayed_tiers[axis] = ScoutingTier.GLIMPSED.value
            decayed_points[axis] = config.tier_thresholds[ScoutingTier.GLIMPSED.value]
        elif tier == ScoutingTier.GLIMPSED.value:
            decayed_tiers[axis] = ScoutingTier.UNKNOWN.value
            decayed_points[axis] = 0
        else:
            decayed_tiers[axis] = ScoutingTier.UNKNOWN.value
            decayed_points[axis] = 0

    return ScoutingState(
        player_id=state.player_id,
        ratings_tier=decayed_tiers[ScoutingAxis.RATINGS.value],
        archetype_tier=decayed_tiers[ScoutingAxis.ARCHETYPE.value],
        traits_tier=decayed_tiers[ScoutingAxis.TRAITS.value],
        trajectory_tier=decayed_tiers[ScoutingAxis.TRAJECTORY.value],
        scout_points=decayed_points,
        last_updated_week=state.last_updated_week,
    )


def advance_scouting_snapshot(
    snapshot: ScoutingSnapshot,
    season: int,
    current_week: int,
    root_seed: int,
    config: ScoutingBalanceConfig,
) -> ScoutingWeekAdvance:
    """Purely advance scouting state and return persistence instructions."""
    scouts = dict(snapshot.scouts)
    assignments = dict(snapshot.assignments)
    prospects = dict(snapshot.prospects)
    states = dict(snapshot.scouting_states)
    contributions = dict(snapshot.contributions)
    existing_ceiling_labels = dict(snapshot.ceiling_labels)

    assignments_to_save: List[ScoutAssignment] = []
    states_to_save: List[ScoutingState] = []
    events_to_save: List[ScoutingDomainEvent] = []
    revealed_traits_to_save: List[RevealedTraitsUpdate] = []
    ceiling_labels_to_save: List[CeilingLabelUpdate] = []
    contributions_to_save: List[ScoutContribution] = []

    assigned_player_ids = {
        assignment.player_id
        for assignment in assignments.values()
        if assignment.player_id is not None
    }
    for scout_id, scout in scouts.items():
        strategy = snapshot.strategies.get(scout_id)
        if strategy is None or strategy.mode != ScoutMode.AUTO.value:
            continue
        current = assignments.get(scout_id)
        if current and current.player_id:
            current_state = states.get(current.player_id)
            if current_state is None or not _state_fully_verified(current_state):
                continue
            assigned_player_ids.discard(current.player_id)

        new_target = select_auto_scout_target(
            scout=scout,
            strategy=strategy,
            prospects=prospects,
            already_assigned_player_ids=assigned_player_ids,
            week=current_week,
            root_seed=root_seed,
        )
        if new_target is not None:
            assignment = ScoutAssignment(scout_id, new_target, current_week)
            assignments[scout_id] = assignment
            assigned_player_ids.add(new_target)
            assignments_to_save.append(assignment)

    for scout_id, assignment in assignments.items():
        if assignment.player_id is None:
            continue
        scout = scouts.get(scout_id)
        prospect = prospects.get(assignment.player_id)
        if scout is None or prospect is None:
            continue

        prior_state = states.get(prospect.player_id) or _empty_scouting_state(prospect.player_id)
        seed = derive_seed(root_seed, "scouting", scout_id, prospect.player_id, str(current_week))
        new_state, events = advance_scouting_state(
            state=prior_state,
            scout=scout,
            prospect_archetype=prospect.public_archetype_guess,
            week=current_week,
            seed=seed,
            config=config,
        )
        states[prospect.player_id] = new_state
        states_to_save.append(new_state)

        for event in events:
            events_to_save.append(
                ScoutingDomainEvent(
                    season=season,
                    week=current_week,
                    event_type=str(event["event_type"]),
                    player_id=prospect.player_id,
                    scout_id=scout_id,
                    payload=dict(event["payload"]),
                )
            )
            if event["event_type"] == "TIER_UP_TRAITS":
                revealed = pick_traits_to_reveal(
                    player_id=prospect.player_id,
                    true_traits=tuple(prospect.hidden_traits),
                    tier=event["payload"]["new_tier"],
                    root_seed=root_seed,
                )
                revealed_traits_to_save.append(
                    RevealedTraitsUpdate(prospect.player_id, revealed, current_week)
                )
                for trait_id in revealed:
                    events_to_save.append(
                        ScoutingDomainEvent(
                            season=season,
                            week=current_week,
                            event_type="TRAIT_REVEALED",
                            player_id=prospect.player_id,
                            scout_id=scout_id,
                            payload={"trait_id": trait_id, "tier": event["payload"]["new_tier"]},
                        )
                    )

        if (
            ceiling_reveal_eligible(new_state.ratings_tier, scout.trait_sense)
            and prospect.player_id not in existing_ceiling_labels
        ):
            label = ceiling_label_for_trajectory(prospect.hidden_trajectory)
            existing_ceiling_labels[prospect.player_id] = label
            ceiling_labels_to_save.append(
                CeilingLabelUpdate(prospect.player_id, label, current_week, scout_id)
            )
            events_to_save.append(
                ScoutingDomainEvent(
                    season=season,
                    week=current_week,
                    event_type="CEILING_REVEALED",
                    player_id=prospect.player_id,
                    scout_id=scout_id,
                    payload={"label": label},
                )
            )

        key = (scout_id, prospect.player_id, season)
        prior_contribution = contributions.get(key)
        increments = {
            axis: new_state.scout_points[axis] - prior_state.scout_points.get(axis, 0)
            for axis in (
                ScoutingAxis.RATINGS.value,
                ScoutingAxis.ARCHETYPE.value,
                ScoutingAxis.TRAITS.value,
                ScoutingAxis.TRAJECTORY.value,
            )
        }
        if prior_contribution is not None:
            increments = {
                axis: prior_contribution.contributed_scout_points.get(axis, 0) + gained
                for axis, gained in increments.items()
            }
            first_week = prior_contribution.first_assigned_week
            weeks_worked = prior_contribution.weeks_worked + 1
            last_traits = prior_contribution.last_estimated_traits
            last_ceiling = prior_contribution.last_estimated_ceiling
            last_trajectory = prior_contribution.last_estimated_trajectory
        else:
            first_week = current_week
            weeks_worked = 1
            last_traits = ()
            last_ceiling = None
            last_trajectory = None

        contribution = ScoutContribution(
            scout_id=scout_id,
            player_id=prospect.player_id,
            season=season,
            first_assigned_week=first_week,
            last_active_week=current_week,
            weeks_worked=weeks_worked,
            contributed_scout_points=increments,
            last_estimated_ratings_band=_estimate_ratings_band_from_state(new_state, prospect),
            last_estimated_archetype=prospect.public_archetype_guess,
            last_estimated_traits=last_traits,
            last_estimated_ceiling=last_ceiling,
            last_estimated_trajectory=last_trajectory,
        )
        contributions[key] = contribution
        contributions_to_save.append(contribution)

    return ScoutingWeekAdvance(
        assignments_to_save=tuple(assignments_to_save),
        states_to_save=tuple(states_to_save),
        events=tuple(events_to_save),
        revealed_traits_to_save=tuple(revealed_traits_to_save),
        ceiling_labels_to_save=tuple(ceiling_labels_to_save),
        contributions_to_save=tuple(contributions_to_save),
    )


def initialize_scouting_for_career(
    conn,
    root_seed: int,
    config: ScoutingBalanceConfig,
    class_year: int = 1,
) -> None:
    """Seed V2-A scouts and a prospect class idempotently."""
    from .persistence import load_prospect_pool, save_prospect_pool, seed_default_scouts
    from .recruitment import generate_prospect_pool
    from .rng import DeterministicRNG

    seed_default_scouts(conn)
    if not load_prospect_pool(conn, class_year=class_year):
        rng = DeterministicRNG(derive_seed(root_seed, "prospect_gen", str(class_year)))
        save_prospect_pool(conn, generate_prospect_pool(class_year, rng, config))


def run_scouting_week_tick(
    conn,
    season: int,
    current_week: int,
    root_seed: int,
    config: ScoutingBalanceConfig,
) -> None:
    """Advance active scouting assignments by one week."""
    from .persistence import (
        append_scouting_domain_event,
        load_all_scout_assignments,
        load_all_scouting_states,
        load_ceiling_label,
        load_prospect_pool,
        load_scout_contributions_for_season,
        load_revealed_traits,
        load_scout_strategy,
        load_scouts,
        save_ceiling_label,
        save_revealed_traits,
        save_scout_assignment,
        save_scouting_state,
        upsert_scout_contribution,
    )

    scouts = {scout.scout_id: scout for scout in load_scouts(conn)}
    assignments = load_all_scout_assignments(conn)
    prospects = {prospect.player_id: prospect for prospect in load_prospect_pool(conn, season)}
    states = load_all_scouting_states(conn)
    strategies = {
        scout_id: strategy
        for scout_id in scouts
        if (strategy := load_scout_strategy(conn, scout_id)) is not None
    }
    contributions = {
        (contribution.scout_id, contribution.player_id, contribution.season): contribution
        for contribution in load_scout_contributions_for_season(conn, season)
    }
    revealed_traits = {
        player_id: load_revealed_traits(conn, player_id)
        for player_id in prospects
    }
    ceiling_labels = {
        player_id: row["label"]
        for player_id in prospects
        if (row := load_ceiling_label(conn, player_id)) is not None
    }
    plan = advance_scouting_snapshot(
        ScoutingSnapshot(
            prospects=prospects,
            scouting_states=states,
            revealed_traits=revealed_traits,
            ceiling_labels=ceiling_labels,
            scouts=scouts,
            assignments=assignments,
            strategies=strategies,
            contributions=contributions,
        ),
        season=season,
        current_week=current_week,
        root_seed=root_seed,
        config=config,
    )

    for assignment in plan.assignments_to_save:
        save_scout_assignment(conn, assignment)
    for state in plan.states_to_save:
        save_scouting_state(conn, state)
    for update in plan.revealed_traits_to_save:
        save_revealed_traits(conn, update.player_id, update.traits, update.revealed_at_week)
    for update in plan.ceiling_labels_to_save:
        save_ceiling_label(
            conn,
            update.player_id,
            update.label,
            update.revealed_at_week,
            update.revealed_by_scout_id,
        )
    for event in plan.events:
        append_scouting_domain_event(
            conn,
            season=event.season,
            week=event.week,
            event_type=event.event_type,
            player_id=event.player_id,
            scout_id=event.scout_id,
            payload=event.payload,
        )
    for contribution in plan.contributions_to_save:
        upsert_scout_contribution(conn, contribution)


def _state_fully_verified(state: ScoutingState) -> bool:
    return (
        state.ratings_tier == ScoutingTier.VERIFIED.value
        and state.archetype_tier == ScoutingTier.VERIFIED.value
        and state.traits_tier == ScoutingTier.VERIFIED.value
        and state.trajectory_tier == ScoutingTier.VERIFIED.value
    )


def _empty_scouting_state(player_id: str) -> ScoutingState:
    return ScoutingState(
        player_id=player_id,
        ratings_tier=ScoutingTier.UNKNOWN.value,
        archetype_tier=ScoutingTier.UNKNOWN.value,
        traits_tier=ScoutingTier.UNKNOWN.value,
        trajectory_tier=ScoutingTier.UNKNOWN.value,
        scout_points={
            ScoutingAxis.RATINGS.value: 0,
            ScoutingAxis.ARCHETYPE.value: 0,
            ScoutingAxis.TRAITS.value: 0,
            ScoutingAxis.TRAJECTORY.value: 0,
        },
        last_updated_week=0,
    )


def _estimate_ratings_band_from_state(
    state: ScoutingState,
    prospect: Prospect,
) -> Dict[str, Tuple[int, int]]:
    true_ovr = int(round(prospect.true_overall()))
    if state.ratings_tier == ScoutingTier.VERIFIED.value:
        return {"ovr": (true_ovr, true_ovr)}
    if state.ratings_tier == ScoutingTier.KNOWN.value:
        return {"ovr": (max(0, true_ovr - 6), min(100, true_ovr + 6))}
    if state.ratings_tier == ScoutingTier.GLIMPSED.value:
        return {"ovr": (max(0, true_ovr - 15), min(100, true_ovr + 15))}
    low, high = prospect.public_ratings_band["ovr"]
    return {"ovr": (low, high)}


__all__ = [
    "CeilingLabel",
    "CeilingLabelUpdate",
    "DEFAULT_SCOUT_PROFILES",
    "Prospect",
    "RevealedTraitsUpdate",
    "Scout",
    "ScoutAssignment",
    "ScoutContribution",
    "ScoutMode",
    "ScoutPriority",
    "ScoutStrategyState",
    "ScoutingAxis",
    "ScoutingDomainEvent",
    "ScoutingSnapshot",
    "ScoutingState",
    "ScoutingTier",
    "ScoutingWeekAdvance",
    "SeededScoutProfile",
    "TraitSense",
    "Trajectory",
    "advance_scouting_snapshot",
    "advance_scouting_state",
    "apply_carry_forward_decay",
    "ceiling_label_for_trajectory",
    "ceiling_reveal_eligible",
    "compute_scout_points_for_axis",
    "initialize_scouting_for_career",
    "pick_traits_to_reveal",
    "run_scouting_week_tick",
    "select_auto_scout_target",
    "tier_for_points",
]
