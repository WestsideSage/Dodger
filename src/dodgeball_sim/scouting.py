from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import Player, PlayerArchetype
from .rng import DeterministicRNG
import sqlite3
from typing import Any, Dict, List, Optional
import sqlite3
from typing import Any, Dict, List, Optional
import sqlite3
from typing import Any, Dict, List, Optional

BudgetLevel = Literal["low", "medium", "high"]
_RATING_NAMES = ("accuracy", "power", "dodge", "catch", "stamina")

_UNCERTAINTY_BAR_HALO_WIDTHS = {
    "UNKNOWN": 100,
    "GLIMPSED": 30,
    "KNOWN": 12,
    "VERIFIED": 0,
}


def uncertainty_bar_halo_width_for_tier(tier: str) -> int:
    """Map a scouting tier to the total visible uncertainty halo width."""
    return _UNCERTAINTY_BAR_HALO_WIDTHS.get(tier, 100)

_SCOUTING_DISPLAY_NAMES: dict[PlayerArchetype, str] = {
    PlayerArchetype.THROWER: "Cannon Arm",
    PlayerArchetype.CATCHER: "Sticky Hands",
    PlayerArchetype.BALL_HAWK: "Floor General",
    PlayerArchetype.DODGER_ANCHOR: "Brick Wall",
    PlayerArchetype.THROWER_CATCHER: "Swing Player",
    PlayerArchetype.THROWER_DODGER: "Counter-Puncher",
    PlayerArchetype.CATCHER_HAWK: "Roaming Glove",
    PlayerArchetype.HAWK_DODGER: "Stealth Runner",
}


def reveal_archetype(player: Player) -> str:
    return _SCOUTING_DISPLAY_NAMES[player.archetype]


@dataclass(frozen=True)
class ScoutingReport:
    player_id: str
    revealed_archetype: str
    rating_ranges: dict[str, tuple[int, int]]
    exact_ratings: dict[str, int]


def generate_scout_report(
    player: Player,
    budget_level: BudgetLevel | str,
    rng: DeterministicRNG,
) -> ScoutingReport:
    """Return a deterministic scouting report for one player."""
    normalized_budget = _normalize_budget_level(budget_level)
    archetype = reveal_archetype(player)
    exact_ratings = _rounded_ratings(player)

    if normalized_budget == "low":
        return ScoutingReport(
            player_id=player.id,
            revealed_archetype=archetype,
            rating_ranges={},
            exact_ratings={},
        )

    width = 15 if normalized_budget == "medium" else 3
    rating_ranges = {
        rating_name: _estimate_rating_range(exact_ratings[rating_name], width, rng)
        for rating_name in _RATING_NAMES
    }
    if normalized_budget == "medium":
        exact_ratings = {}

    return ScoutingReport(
        player_id=player.id,
        revealed_archetype=archetype,
        rating_ranges=rating_ranges,
        exact_ratings=exact_ratings,
    )


def _estimate_rating_range(
    actual_rating: int,
    width: int,
    rng: DeterministicRNG,
) -> tuple[int, int]:
    low_bias = int(round(rng.roll(0.0, float(width))))
    high_bias = int(round(rng.roll(0.0, float(width))))
    low = _clamp_rating(actual_rating - low_bias)
    high = _clamp_rating(actual_rating + high_bias)
    if low > high:
        low, high = high, low
    if low == high and width > 0:
        high = _clamp_rating(low + 1)
    return low, high

def _rounded_ratings(player: Player) -> dict[str, int]:
    ratings = player.ratings
    return {
        rating_name: int(round(getattr(ratings, rating_name)))
        for rating_name in _RATING_NAMES
    }


def _normalize_budget_level(value: BudgetLevel | str) -> BudgetLevel:
    normalized = str(value).strip().lower()
    if normalized not in {"low", "medium", "high"}:
        raise ValueError(f"Unsupported scouting budget level: {value!r}")
    return normalized


def _clamp_rating(value: int) -> int:
    return max(0, min(100, int(value)))


__all__ = ["BudgetLevel", "ScoutingReport", "generate_scout_report", "reveal_archetype"]


# ----------------------------------------------------------------------
# Prospect board / scouting display helpers (formerly manager_helpers)
# ----------------------------------------------------------------------

def _scout_specialty_blurb(scout) -> str:
    parts: List[str] = []
    if scout.archetype_affinities:
        parts.append(f"{', '.join(scout.archetype_affinities)} specialist")
    if scout.archetype_weakness:
        parts.append(f"weak on {scout.archetype_weakness}")
    if scout.trait_sense == "HIGH":
        parts.append("trait-sharp")
    elif scout.trait_sense == "LOW":
        parts.append("trait-blind")
    return " | ".join(parts)

def build_scout_strip_data(conn: sqlite3.Connection, season: int) -> List[Dict[str, Any]]:
    from .persistence import (
        load_all_scout_assignments,
        load_scout_strategy,
        load_scout_track_records_for_scout,
        load_scouts,
    )

    cards: List[Dict[str, Any]] = []
    assignments = load_all_scout_assignments(conn)
    for scout in load_scouts(conn):
        strategy = load_scout_strategy(conn, scout.scout_id)
        assignment = assignments.get(scout.scout_id)
        track_records = load_scout_track_records_for_scout(conn, scout.scout_id)
        cards.append(
            {
                "scout_id": scout.scout_id,
                "name": scout.name,
                "specialty_blurb": _scout_specialty_blurb(scout),
                "assignment_player_id": assignment.player_id if assignment else None,
                "mode": strategy.mode if strategy else "MANUAL",
                "priority": strategy.priority if strategy else "TOP_PUBLIC_OVR",
                "accuracy_blurb": f"Track record: {len(track_records)} reads" if track_records else "",
            }
        )
    return cards

def build_prospect_board_rows(conn: sqlite3.Connection, class_year: int) -> List[Dict[str, Any]]:
    from .persistence import (
        load_all_scout_assignments,
        load_all_scouting_states,
        load_ceiling_label,
        load_prospect_pool,
        load_revealed_traits,
    )

    pool = load_prospect_pool(conn, class_year)
    states = load_all_scouting_states(conn)
    assignments = load_all_scout_assignments(conn)
    assigned_to = {
        assignment.player_id: scout_id
        for scout_id, assignment in assignments.items()
        if assignment.player_id
    }
    rows: List[Dict[str, Any]] = []
    for prospect in pool:
        state = states.get(prospect.player_id)
        ratings_tier = state.ratings_tier if state else "UNKNOWN"
        archetype_tier = state.archetype_tier if state else "UNKNOWN"
        traits_tier = state.traits_tier if state else "UNKNOWN"
        trajectory_tier = state.trajectory_tier if state else "UNKNOWN"
        true_ovr = int(round(prospect.true_overall()))
        if ratings_tier == "VERIFIED":
            ovr_band = (true_ovr, true_ovr)
        elif ratings_tier == "KNOWN":
            ovr_band = (max(0, true_ovr - 6), min(100, true_ovr + 6))
        elif ratings_tier == "GLIMPSED":
            ovr_band = (max(0, true_ovr - 15), min(100, true_ovr + 15))
        else:
            ovr_band = prospect.public_ratings_band["ovr"]
        ceiling = load_ceiling_label(conn, prospect.player_id)
        rows.append(
            {
                "player_id": prospect.player_id,
                "name": prospect.name,
                "age": prospect.age,
                "hometown": prospect.hometown,
                "archetype_guess": (
                    prospect.true_archetype()
                    if archetype_tier in {"KNOWN", "VERIFIED"}
                    else prospect.public_archetype_guess
                ),
                "ratings_tier": ratings_tier,
                "archetype_tier": archetype_tier,
                "traits_tier": traits_tier,
                "trajectory_tier": trajectory_tier,
                "ovr_band": ovr_band,
                "ovr_mid": (ovr_band[0] + ovr_band[1]) // 2,
                "ceiling_label": ceiling["label"] if ceiling else None,
                "revealed_traits": list(load_revealed_traits(conn, prospect.player_id)),
                "assigned_to_scout_id": assigned_to.get(prospect.player_id),
            }
        )
    return rows

def sort_rows_worth_a_look(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def score(row: Dict[str, Any]) -> int:
        confidence_axes = sum(
            1
            for key in ("ratings_tier", "archetype_tier", "traits_tier", "trajectory_tier")
            if row[key] != "UNKNOWN"
        )
        return int(row["ovr_mid"]) - confidence_axes * 5

    return sorted(rows, key=score, reverse=True)

_TIER_UP_TEXT = {
    "TIER_UP_RATINGS": "ratings",
    "TIER_UP_ARCHETYPE": "archetype",
    "TIER_UP_TRAITS": "traits",
    "TIER_UP_TRAJECTORY": "trajectory",
}

def build_reveal_ticker_items(conn: sqlite3.Connection, season: int) -> List[Dict[str, Any]]:
    from .persistence import load_scouting_domain_events_for_season

    items: List[Dict[str, Any]] = []
    for event in load_scouting_domain_events_for_season(conn, season):
        event_type = event["event_type"]
        payload = event["payload"]
        if event_type in _TIER_UP_TEXT:
            text = (
                f"Week {event['week']}: {event['scout_id'] or 'Scouts'} reached "
                f"{payload['new_tier']} on {_TIER_UP_TEXT[event_type]} for {event['player_id']}"
            )
        elif event_type == "TRAIT_REVEALED":
            text = f"Week {event['week']}: {payload['trait_id']} surfaced on {event['player_id']}"
        elif event_type == "CEILING_REVEALED":
            text = f"Week {event['week']}: {payload['label']} revealed on {event['player_id']}"
        else:
            text = f"Week {event['week']}: {event_type} on {event['player_id']}"
        items.append({"week": event["week"], "text": text, "event_type": event_type})
    return items

_CEILING_DISPLAY = {
    "HIGH_CEILING": "HIGH CEILING",
    "SOLID": "SOLID",
    "STANDARD": "STANDARD",
}

def build_fuzzy_profile_details(
    conn: sqlite3.Connection,
    class_year: int,
    player_id: str,
) -> Dict[str, Any]:
    from .persistence import (
        load_ceiling_label,
        load_prospect_pool,
        load_revealed_traits,
        load_scouting_state,
    )
    from .scouting_center import ScoutingState

    prospect = next(
        (item for item in load_prospect_pool(conn, class_year) if item.player_id == player_id),
        None,
    )
    if prospect is None:
        raise ValueError(f"No prospect with player_id={player_id} in class_year={class_year}")

    state = load_scouting_state(conn, player_id) or ScoutingState(
        player_id=player_id,
        ratings_tier="UNKNOWN",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=0,
    )
    ceiling = load_ceiling_label(conn, player_id)
    revealed_traits = load_revealed_traits(conn, player_id)
    archetype_label = (
        prospect.true_archetype()
        if state.archetype_tier in {"KNOWN", "VERIFIED"}
        else prospect.public_archetype_guess
    )
    if state.traits_tier == "UNKNOWN":
        trait_badges: List[str] = []
    else:
        hidden_count = max(0, len(prospect.hidden_traits) - len(revealed_traits))
        trait_badges = list(revealed_traits) + ["?"] * hidden_count

    return {
        "player_id": prospect.player_id,
        "name": prospect.name,
        "age": prospect.age,
        "hometown": prospect.hometown,
        "archetype_label": archetype_label,
        "ratings_tier": state.ratings_tier,
        "archetype_tier": state.archetype_tier,
        "traits_tier": state.traits_tier,
        "trajectory_tier": state.trajectory_tier,
        "rating_rows": [
            {
                "rating_name": rating_name,
                "midpoint": prospect.hidden_ratings.get(rating_name, 0.0),
                "tier": state.ratings_tier,
            }
            for rating_name in _RATING_NAMES
        ],
        "trait_badges": trait_badges,
        "ceiling_label": _CEILING_DISPLAY[ceiling["label"]] if ceiling else "?",
        "trajectory_label": "Hidden (revealed at Draft Day)",
    }

_TRAJECTORY_DISPLAY_WEIGHT = {
    "NORMAL": "standard",
    "IMPACT": "standard",
    "STAR": "elevated",
    "GENERATIONAL": "elevated",
}

def build_trajectory_reveal_sweep(
    conn: sqlite3.Connection,
    class_year: int,
) -> List[Dict[str, Any]]:
    from .persistence import load_all_scouting_states, load_prospect_pool

    states = load_all_scouting_states(conn)
    sweep: List[Dict[str, Any]] = []
    for prospect in load_prospect_pool(conn, class_year):
        state = states.get(prospect.player_id)
        if state and state.trajectory_tier == "VERIFIED":
            sweep.append(
                {
                    "player_id": prospect.player_id,
                    "name": prospect.name,
                    "trajectory": prospect.hidden_trajectory,
                    "display_weight": _TRAJECTORY_DISPLAY_WEIGHT.get(prospect.hidden_trajectory, "standard"),
                }
            )
    return sweep

def build_accuracy_reckoning(
    conn: sqlite3.Connection,
    season: int,
    class_year: int,
) -> List[Dict[str, Any]]:
    from .persistence import (
        load_prospect_pool,
        load_scout_contributions_for_season,
        load_scout_track_records_for_scout,
        save_scout_track_record,
    )
    from .scouting_center import ceiling_label_for_trajectory

    pool_by_id = {prospect.player_id: prospect for prospect in load_prospect_pool(conn, class_year)}
    contributions = load_scout_contributions_for_season(conn, season)
    for contribution in contributions:
        prospect = pool_by_id.get(contribution.player_id)
        if prospect is None:
            continue
        existing = [
            row
            for row in load_scout_track_records_for_scout(conn, contribution.scout_id)
            if row["player_id"] == contribution.player_id and row["season"] == contribution.season
        ]
        if existing:
            continue
        predicted_band = contribution.last_estimated_ratings_band.get("ovr")
        save_scout_track_record(
            conn,
            scout_id=contribution.scout_id,
            player_id=contribution.player_id,
            season=contribution.season,
            predicted_ovr_band=tuple(predicted_band) if predicted_band else None,
            actual_ovr=int(round(prospect.true_overall())),
            predicted_archetype=contribution.last_estimated_archetype,
            actual_archetype=prospect.true_archetype(),
            predicted_trajectory=contribution.last_estimated_trajectory,
            actual_trajectory=prospect.hidden_trajectory,
            predicted_ceiling=contribution.last_estimated_ceiling,
            actual_ceiling=ceiling_label_for_trajectory(prospect.hidden_trajectory),
        )

    summary: Dict[str, Dict[str, Any]] = {}
    for contribution in contributions:
        prospect = pool_by_id.get(contribution.player_id)
        if prospect is None:
            continue
        predicted_band = contribution.last_estimated_ratings_band.get("ovr")
        actual_ovr = int(round(prospect.true_overall()))
        bucket = summary.setdefault(contribution.scout_id, {"scout_id": contribution.scout_id, "rows": []})
        bucket["rows"].append(
            {
                "player_id": contribution.player_id,
                "player_name": prospect.name,
                "predicted_ovr_band": tuple(predicted_band) if predicted_band else None,
                "actual_ovr": actual_ovr,
                "within_5": bool(
                    predicted_band
                    and predicted_band[0] - 5 <= actual_ovr <= predicted_band[1] + 5
                ),
            }
        )
    return list(summary.values())

def has_accuracy_reckoning_data(conn: sqlite3.Connection, season: int) -> bool:
    from .persistence import load_scout_contributions_for_season

    return bool(load_scout_contributions_for_season(conn, season))

def build_hidden_gem_spotlight(
    conn: sqlite3.Connection,
    season: int,
    class_year: int,
) -> Optional[Dict[str, Any]]:
    from .config import DEFAULT_SCOUTING_CONFIG
    from .persistence import load_prospect_pool, load_scouting_domain_events_for_season

    pool_by_id = {prospect.player_id: prospect for prospect in load_prospect_pool(conn, class_year)}
    floor = DEFAULT_SCOUTING_CONFIG.hidden_gem_ovr_floor
    high_ceiling_events = [
        event
        for event in load_scouting_domain_events_for_season(conn, season)
        if event["event_type"] == "CEILING_REVEALED"
        and event["payload"].get("label") == "HIGH_CEILING"
    ]
    for event in reversed(high_ceiling_events):
        prospect = pool_by_id.get(event["player_id"])
        if prospect is None:
            continue
        low, high = prospect.public_ratings_band["ovr"]
        public_mid = (low + high) // 2
        true_ovr = int(round(prospect.true_overall()))
        if public_mid + floor < true_ovr:
            return {
                "player_id": prospect.player_id,
                "name": prospect.name,
                "label": "HIGH_CEILING",
                "public_ovr_mid": public_mid,
                "estimated_ovr_mid": true_ovr,
                "revealed_at_week": event["week"],
            }
    return None

def build_scouting_alerts(
    conn: sqlite3.Connection,
    season: int,
    current_week: int,
    total_weeks: int,
) -> List[Dict[str, Any]]:
    from .persistence import load_all_scout_assignments, load_all_scouting_states, load_scout_strategy, load_scouts

    alerts: List[Dict[str, Any]] = []
    assignments = load_all_scout_assignments(conn)
    unassigned = 0
    for scout in load_scouts(conn):
        strategy = load_scout_strategy(conn, scout.scout_id)
        if strategy and strategy.mode == "MANUAL":
            assignment = assignments.get(scout.scout_id)
            if assignment is None or assignment.player_id is None:
                unassigned += 1
    if unassigned:
        alerts.append(
            {
                "kind": "unassigned_scouts",
                "text": f"{unassigned} unassigned scout{'s' if unassigned != 1 else ''}",
                "click_target": "scouting",
            }
        )

    if current_week >= total_weeks - 1:
        states = load_all_scouting_states(conn)
        verified_count = sum(1 for state in states.values() if state.trajectory_tier == "VERIFIED")
        if verified_count:
            alerts.append(
                {
                    "kind": "trajectory_verified",
                    "text": f"{verified_count} prospect{'s' if verified_count != 1 else ''} trajectory Verified for Draft Day",
                    "click_target": "scouting",
                }
            )
    return alerts
