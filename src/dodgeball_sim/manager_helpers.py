from __future__ import annotations

import random
import json
import re
import sqlite3
import tkinter as tk
from dataclasses import dataclass, replace
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from .awards import compute_match_mvp, compute_season_awards
from .career_state import CareerState, CareerStateCursor, advance
from .court_renderer import CourtRenderer
from .development import apply_season_development, should_retire
from .engine import MatchEngine
from .franchise import (
    MatchRecord,
    create_season,
    extract_match_stats,
    simulate_match,
    simulate_matchday,
    trim_ai_roster_for_offseason,
)
from .game_loop import (
    current_week as game_current_week,
    persist_match_record,
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from .league import Club, Conference, League
from .lineup import STARTERS_COUNT, LineupResolver
from .models import MatchSetup, Player, PlayerRatings, PlayerTraits, Team
from .persistence import (
    CorruptSaveError,
    connect,
    create_schema,
    fetch_match,
    fetch_player_career_summary,
    fetch_season_player_stats,
    get_state,
    load_all_rosters,
    load_awards,
    load_career_state_cursor,
    load_clubs,
    load_completed_match_ids,
    load_free_agents,
    load_json_state,
    load_lineup_default,
    load_player_career_stats,
    load_playoff_bracket,
    load_match_lineup_override,
    load_season_format,
    load_season_outcome,
    load_season,
    load_standings,
    save_free_agents,
    record_roster_snapshot,
    record_match,
    save_awards,
    save_career_state_cursor,
    save_club,
    save_lineup_default,
    save_match_result,
    save_player_season_stats,
    save_player_career_stats,
    save_player_stats_batch,
    save_playoff_bracket,
    save_retired_player,
    save_scheduled_matches,
    save_season,
    save_season_format,
    save_season_outcome,
    save_standings,
    set_state,
)
from .playoffs import (
    PLAYOFF_FORMAT,
    create_final_match,
    create_semifinal_bracket,
    is_playoff_match_id,
    outcome_from_final,
    playoff_stage_label,
)
from .offseason_beats import (
    build_rookie_class_preview,
    induct_hall_of_fame,
    ratify_records,
)
from .recruitment import generate_rookie_class
from .rng import DeterministicRNG, derive_seed
from .sample_data import curated_clubs, sample_match_setup
from .scheduler import ScheduledMatch, season_format_summary
from .season import Season, SeasonResult, StandingsRow, compute_standings
from .stats import PlayerMatchStats, extract_all_stats
from .ui_formatters import player_role, policy_effect, team_overall, team_snapshot
from .ui_style import (
    DM_BORDER,
    DM_CHARCOAL,
    DM_CREAM,
    DM_BRICK,
    DM_GYM_BLUE,
    DM_MUSTARD,
    DM_MUTED_CHARCOAL,
    DM_NIGHT,
    DM_OFF_WHITE_LINE,
    DM_PAPER,
    DM_RED,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_MONO,
    SPACE_1,
    SPACE_2,
    SPACE_3,
    apply_theme,
)
from .win_probability import per_event_wp_delta, pre_match_expected_outcome
from .copy_quality import has_unresolved_token, title_label
from .sim_pacing import SimRequest, SimStop, choose_matches_to_sim
from .view_models import (
    ScheduleRow,
    WireItem,
    build_schedule_rows,
    build_wire_items,
    normalize_root_seed,
)

DEFAULT_MANAGER_DB = Path("dodgeball_manager.db")
FRIENDLY_MATCH_ID = "friendly_sample"
FRIENDLY_SEED = 20260426
FRIENDLY_DIFFICULTY = "pro"
POLICY_KEYS = (
    "target_stars",
    "target_ball_holder",
    "risk_tolerance",
    "sync_throws",
    "rush_frequency",
    "rush_proximity",
    "tempo",
    "catch_bias",
)
MANAGER_TABLES = (
    "matches",
    "match_events",
    "match_records",
    "player_match_stats",
    "player_season_stats",
    "season_awards",
    "season_standings",
    "scheduled_matches",
    "seasons",
    "lineup_default",
    "match_lineup_override",
    "club_rosters",
    "clubs",
    "dynasty_state",
    "prospect_pool",
    "scouting_state",
    "scouting_revealed_traits",
    "scouting_ceiling_label",
    "scout",
    "scout_assignment",
    "scout_strategy",
    "scout_prospect_contribution",
    "scout_track_record",
    "scouting_domain_event",
    "club_recruitment_profile",
    "recruitment_board",
    "recruitment_round",
    "recruitment_offer",
    "recruitment_signing",
    "prospect_market_signal",
    "player_trajectory",
    "playoff_brackets",
    "season_outcomes",
    "season_formats",
)


@dataclass(frozen=True)
class LeagueLeader:
    category: str
    player_id: str
    club_id: str
    value: float


@dataclass(frozen=True)
class PlayerProfileDetails:
    title: str
    text: str


@dataclass(frozen=True)
class OffseasonCeremonyBeat:
    key: str
    title: str
    body: str


OFFSEASON_CEREMONY_BEATS = (
    "champion",
    "recap",
    "awards",
    "records_ratified",
    "hof_induction",
    "development",
    "retirements",
    "rookie_class_preview",
    "recruitment",
    "schedule_reveal",
)


def clamp_offseason_beat_index(beat_index: Any) -> int:
    try:
        numeric = int(beat_index)
    except (TypeError, ValueError):
        numeric = 0
    return max(0, min(numeric, len(OFFSEASON_CEREMONY_BEATS) - 1))


def load_offseason_state_rows(conn: sqlite3.Connection, key: str) -> List[Mapping[str, Any]]:
    payload = load_json_state(conn, key, [])
    if not isinstance(payload, list):
        raise CorruptSaveError(f"Corrupt JSON for state {key}: expected list")
    return payload


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _club_roster(club: Club, seed: int, count: int = 6) -> List[Player]:
    rng = DeterministicRNG(seed)
    roles = [
        ("Captain", (76, 72, 62, 58)),
        ("Striker", (70, 78, 58, 52)),
        ("Anchor", (61, 62, 64, 76)),
        ("Runner", (64, 58, 78, 60)),
        ("Rookie", (60, 61, 62, 63)),
        ("Utility", (66, 65, 65, 65)),
    ]
    roster: List[Player] = []
    for index, (label, base) in enumerate(roles[:count], 1):
        accuracy, power, dodge, catch = (
            _clamp(value + rng.gauss(0, 4), 35, 95) for value in base
        )
        player_id = f"{club.club_id}_{index}"
        roster.append(
            Player(
                id=player_id,
                name=f"{club.name.split()[0]} {label}",
                ratings=PlayerRatings(
                    accuracy=accuracy,
                    power=power,
                    dodge=dodge,
                    catch=catch,
                    stamina=_clamp(rng.gauss(66, 7), 40, 95),
                ).apply_bounds(),
                traits=PlayerTraits(),
                age=18 + int(rng.unit() * 12),
                club_id=club.club_id,
                newcomer=index >= 5,
            )
        )
    return roster


def _slugify_club_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "club"


def clean_manager_text(value: str, fallback: str, max_len: int) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        cleaned = fallback
    return cleaned[:max_len]


def normalize_manager_color(value: str, fallback: str) -> str:
    cleaned = str(value or "").strip()
    return cleaned if re.fullmatch(r"#[0-9a-fA-F]{6}", cleaned) else fallback


def stored_root_seed(conn: sqlite3.Connection, default: int = 1) -> int:
    return normalize_root_seed(get_state(conn, "root_seed", str(default)), default_on_invalid=True)


def build_expansion_club(
    *,
    name: str,
    primary_color: str,
    secondary_color: str,
    venue_name: str,
    home_region: str,
    tagline: str,
) -> Club:
    """Build a stable custom expansion club identity for Build a Club careers."""
    cleaned_name = clean_manager_text(name, "Expansion Club", 48)
    primary = normalize_manager_color(primary_color, "#1A365D")
    secondary = normalize_manager_color(secondary_color, "#F6AD55")
    return Club(
        club_id=f"exp_{_slugify_club_name(cleaned_name)}",
        name=cleaned_name,
        colors=f"{primary}/{secondary}",
        home_region=clean_manager_text(home_region, "Independent", 40),
        founded_year=2026,
        primary_color=primary,
        secondary_color=secondary,
        venue_name=clean_manager_text(venue_name, f"{cleaned_name} Gym", 64),
        tagline=clean_manager_text(tagline, "Expansion club", 120),
    )


def generate_expansion_roster(club_id: str, root_seed: int, count: int = 6) -> List[Player]:
    """Generate a legal but intentionally weaker expansion roster."""
    root_seed = normalize_root_seed(root_seed)
    rng = DeterministicRNG(derive_seed(root_seed, "expansion_roster", club_id))
    roles = [
        ("Captain", (55, 54, 50, 49, 55)),
        ("Striker", (52, 58, 48, 46, 53)),
        ("Anchor", (48, 50, 51, 57, 52)),
        ("Runner", (50, 47, 58, 49, 56)),
        ("Rookie", (47, 49, 50, 51, 54)),
        ("Utility", (51, 51, 51, 51, 54)),
    ]
    roster: List[Player] = []
    for index, (label, base) in enumerate(roles[:count], 1):
        accuracy, power, dodge, catch, stamina = (
            _clamp(value + rng.gauss(0, 3), 35, 72) for value in base
        )
        roster.append(
            Player(
                id=f"{club_id}_{index}",
                name=f"{club_id.removeprefix('exp_').replace('_', ' ').title()} {label}",
                ratings=PlayerRatings(
                    accuracy=accuracy,
                    power=power,
                    dodge=dodge,
                    catch=catch,
                    stamina=stamina,
                ).apply_bounds(),
                traits=PlayerTraits(),
                age=18 + int(rng.unit() * 10),
                club_id=club_id,
                newcomer=True,
            )
        )
    return roster


def _standings_with_all_clubs(standings: List[StandingsRow], clubs: Dict[str, Club]) -> List[StandingsRow]:
    by_id = {row.club_id: row for row in standings}
    rows = [
        by_id.get(club_id, StandingsRow(club_id, wins=0, losses=0, draws=0, elimination_differential=0, points=0))
        for club_id in clubs
    ]
    rows.sort(key=lambda row: (-row.points, -row.elimination_differential, row.club_id))
    return rows


def _regular_season_matches(season: Season) -> List[ScheduledMatch]:
    return [
        match for match in season.scheduled_matches
        if not is_playoff_match_id(season.season_id, match.match_id)
    ]


def build_league_leaders(
    player_stats: Mapping[str, PlayerMatchStats],
    player_club_map: Mapping[str, str],
    limit: int = 3,
) -> Dict[str, List[LeagueLeader]]:
    """Build v1 league leader boards from persisted player stats."""
    specs = {
        "Eliminations": lambda stats: float(stats.eliminations_by_throw),
        "Catches": lambda stats: float(stats.catches_made),
        "MVP Score": _score_player,
    }
    leaders: Dict[str, List[LeagueLeader]] = {}
    for category, scorer in specs.items():
        rows = [
            LeagueLeader(category, player_id, player_club_map.get(player_id, ""), scorer(stats))
            for player_id, stats in player_stats.items()
        ]
        rows.sort(key=lambda row: (-row.value, row.player_id))
        leaders[category] = rows[:limit]
    return leaders


def build_player_profile_details(
    player: Player,
    club_name: str,
    season_stats: Optional[PlayerMatchStats] = None,
    matches_played: int = 0,
    career_summary: Optional[Mapping[str, float]] = None,
) -> PlayerProfileDetails:
    """Build display-ready player profile details without touching GUI state."""
    ratings = player.ratings
    status = "Rookie" if player.newcomer else "Veteran"
    lines = [
        f"{player.name}",
        f"Club: {club_name}",
        f"Role: {player_role(player)}",
        f"Age: {player.age} | Status: {status}",
        "",
        "Ratings",
        f"  OVR: {player.overall():.1f}",
        f"  Accuracy: {ratings.accuracy:.1f}",
        f"  Power: {ratings.power:.1f}",
        f"  Dodge: {ratings.dodge:.1f}",
        f"  Catch: {ratings.catch:.1f}",
        f"  Stamina: {ratings.stamina:.1f}",
        "",
        "Current Season",
    ]
    if season_stats is None:
        lines.append("  No persisted season stats yet.")
    else:
        lines.extend(
            [
                f"  Matches: {matches_played}",
                f"  Throws: {season_stats.throws_attempted}",
                f"  Eliminations: {season_stats.eliminations_by_throw}",
                f"  Catches: {season_stats.catches_made}",
                f"  Dodges: {season_stats.dodges_successful}",
                f"  Times Eliminated: {season_stats.times_eliminated}",
                f"  Plus/Minus: {season_stats.elimination_plus_minus:+}",
                f"  MVP Score: {_score_player(season_stats):.1f}",
            ]
        )

    lines.append("")
    lines.append("Career")
    if not career_summary or career_summary.get("seasons_played", 0) <= 0:
        lines.append("  No persisted career totals yet.")
    else:
        lines.extend(
            [
                f"  Seasons: {career_summary.get('seasons_played', 0):.0f}",
                f"  Eliminations: {career_summary.get('total_eliminations', 0):.0f}",
                f"  Catches: {career_summary.get('total_catches_made', 0):.0f}",
                f"  Dodges: {career_summary.get('total_dodges_successful', 0):.0f}",
                f"  Times Eliminated: {career_summary.get('total_times_eliminated', 0):.0f}",
                f"  Recent Eliminations: {career_summary.get('recent_eliminations', 0):.0f}",
            ]
        )
    return PlayerProfileDetails(title=player.name, text="\n".join(lines))


# ---------------------------------------------------------------------------
# V2-A scouting helper builders
# ---------------------------------------------------------------------------

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


_RATING_NAMES = ("accuracy", "power", "dodge", "catch", "stamina")
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


def build_recruitment_day_summary(
    conn: sqlite3.Connection,
    season_id: str,
    class_year: int,
    user_club_id: Optional[str],
) -> Dict[str, int]:
    from .persistence import load_prospect_pool, load_recruitment_signings

    prospects = load_prospect_pool(conn, class_year=class_year)
    signings = load_recruitment_signings(conn, season_id)
    signed_ids = {signing.player_id for signing in signings}
    return {
        "available_prospects": sum(
            1
            for prospect in prospects
            if prospect.player_id not in signed_ids
            and not _is_already_signed(conn, class_year, prospect.player_id)
        ),
        "signed_count": len(signings),
        "sniped_count": sum(1 for signing in signings if user_club_id and signing.club_id != user_club_id),
        "current_round": _next_recruitment_round_number(conn, season_id),
    }


def _default_roster_needs() -> Dict[str, float]:
    return {
        "Sharpshooter": 0.5,
        "Enforcer": 0.5,
        "Escape Artist": 0.5,
        "Ball Hawk": 0.5,
        "Iron Engine": 0.5,
    }


def _ensure_recruitment_prepared(
    conn: sqlite3.Connection,
    root_seed: int,
    season_id: str,
    class_year: int,
    user_club_id: Optional[str] = None,
    round_number: int = 1,
) -> Tuple[Any, ...]:
    from .persistence import (
        load_all_rosters,
        load_club_recruitment_profiles,
        load_prospect_pool,
        load_recruitment_signings,
        load_recruitment_board,
        load_recruitment_offers,
        load_recruitment_round,
        save_club_recruitment_profile,
        save_recruitment_board,
        save_recruitment_offers,
        save_recruitment_round,
    )
    from .recruitment_domain import (
        build_recruitment_board,
        build_recruitment_profile,
        prepare_ai_offers,
    )

    existing_round = load_recruitment_round(conn, season_id, round_number)
    if existing_round is not None:
        return load_recruitment_offers(conn, season_id, round_number)

    already_signed_ids = {signing.player_id for signing in load_recruitment_signings(conn, season_id)}
    prospects = [
        p
        for p in load_prospect_pool(conn, class_year)
        if p.player_id not in already_signed_ids
        and not _is_already_signed(conn, class_year, p.player_id)
    ]
    profiles = load_club_recruitment_profiles(conn)
    rosters = load_all_rosters(conn)
    active_profiles = []
    for club_id in sorted(rosters):
        if user_club_id is not None and club_id == user_club_id:
            continue
        profile = profiles.get(club_id)
        if profile is None:
            profile = build_recruitment_profile(root_seed, club_id)
            save_club_recruitment_profile(conn, profile)
        active_profiles.append(profile)

    boards = {}
    for profile in active_profiles:
        board = build_recruitment_board(
            root_seed=root_seed,
            season_id=season_id,
            profile=profile,
            prospects=prospects,
            roster_needs=_default_roster_needs(),
        )
        save_recruitment_board(conn, season_id, board)
        boards[profile.club_id] = board or load_recruitment_board(conn, season_id, profile.club_id)

    offers = prepare_ai_offers(root_seed, season_id, round_number, active_profiles, boards, already_signed_ids)
    save_recruitment_round(conn, season_id, round_number, "prepared", {"prepared_offer_count": len(offers)})
    save_recruitment_offers(conn, offers)
    return tuple(offers)


def _next_recruitment_round_number(conn: sqlite3.Connection, season_id: str) -> int:
    prepared = conn.execute(
        """
        SELECT round_number
        FROM recruitment_round
        WHERE season_id = ? AND status = 'prepared'
        ORDER BY round_number
        LIMIT 1
        """,
        (season_id,),
    ).fetchone()
    if prepared is not None:
        return int(prepared["round_number"])

    max_round = conn.execute(
        """
        SELECT MAX(round_number) AS max_round
        FROM (
            SELECT round_number FROM recruitment_round WHERE season_id = ?
            UNION ALL
            SELECT round_number FROM recruitment_signing WHERE season_id = ?
        )
        """,
        (season_id, season_id),
    ).fetchone()
    return int(max_round["max_round"] or 0) + 1


def conduct_recruitment_round(
    conn: sqlite3.Connection,
    root_seed: int,
    season_id: str,
    class_year: int,
    user_club_id: str,
    selected_player_id: str,
):
    from .persistence import (
        load_clubs,
        load_prospect_pool,
        load_recruitment_offers,
        save_recruitment_round,
        save_recruitment_signings,
    )
    from .recruitment_domain import RecruitmentOffer, resolve_recruitment_round

    round_number = _next_recruitment_round_number(conn, season_id)
    _ensure_recruitment_prepared(
        conn,
        root_seed,
        season_id,
        class_year,
        user_club_id=user_club_id,
        round_number=round_number,
    )
    prepared_offers = load_recruitment_offers(conn, season_id, round_number)
    prospect = next((p for p in load_prospect_pool(conn, class_year) if p.player_id == selected_player_id), None)
    if prospect is None:
        raise ValueError(f"Unknown prospect: {selected_player_id}")
    user_offer = RecruitmentOffer(
        season_id=season_id,
        round_number=round_number,
        club_id=user_club_id,
        player_id=selected_player_id,
        offer_strength=100.0,
        source="user",
        need_score=5.0,
        playing_time_pitch=0.5,
        prestige=0.5,
        round_order_value=0.5,
        visible_reason="user target; private scouting priority",
    )
    result = resolve_recruitment_round(
        season_id,
        round_number,
        prepared_offers,
        user_offer=user_offer,
        shortlist_player_ids=(selected_player_id,),
    )
    save_recruitment_signings(conn, result.signings)
    save_recruitment_round(
        conn,
        season_id,
        round_number,
        "resolved",
        {"signing_count": len(result.signings), "snipe_count": len(result.snipes)},
    )
    prospects_by_id = {p.player_id: p for p in load_prospect_pool(conn, class_year)}
    clubs = load_clubs(conn)
    for signing in result.signings:
        if signing.club_id not in clubs or _is_already_signed(conn, class_year, signing.player_id):
            continue
        sign_prospect_to_club(conn, prospects_by_id[signing.player_id], signing.club_id, class_year)
    return result


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


def build_offseason_ceremony_beat(
    beat_index: int,
    season: Optional[Season],
    clubs: Mapping[str, Club],
    rosters: Mapping[str, List[Player]],
    standings: Iterable[StandingsRow],
    awards: Iterable[Any],
    player_club_id: Optional[str],
    next_season: Optional[Season] = None,
    development_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    retirement_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    draft_pool: Optional[Iterable[Player]] = None,
    signed_player_id: Optional[str] = None,
    recruitment_available: bool = False,
    recruitment_summary: Optional[Mapping[str, Any]] = None,
    season_outcome: Optional[Any] = None,
    records_payload_json: Optional[str] = None,
    hof_payload_json: Optional[str] = None,
    rookie_preview_payload_json: Optional[str] = None,
) -> OffseasonCeremonyBeat:
    """Build factual v1 offseason ceremony copy from persisted season data."""
    clamped_index = clamp_offseason_beat_index(beat_index)
    key = OFFSEASON_CEREMONY_BEATS[clamped_index]
    ordered_standings = list(standings)
    award_rows = list(awards)
    development = list(development_rows or ())
    retirements = list(retirement_rows or ())
    rookies = list(draft_pool or ())

    def club_name(club_id: str) -> str:
        return clubs[club_id].name if club_id in clubs else club_id

    def player_name(player_id: str) -> str:
        for roster in rosters.values():
            for player in roster:
                if player.id == player_id:
                    return player.name
        return player_id

    if key == "champion":
        if season_outcome is not None:
            seed = None
            for index, row in enumerate(ordered_standings, 1):
                if row.club_id == season_outcome.champion_club_id:
                    seed = index
                    break
            lines = [
                f"Champion: {club_name(season_outcome.champion_club_id)}",
                "Champion source: Playoff final",
            ]
            if season_outcome.runner_up_club_id:
                lines.append(f"Runner-up: {club_name(season_outcome.runner_up_club_id)}")
            if seed is not None:
                lines.append(f"Regular-season seed: {seed}")
            body = "\n".join(lines)
        elif not ordered_standings:
            body = "No completed standings are available for this season."
        else:
            champion = ordered_standings[0]
            body = "\n".join(
                [
                    f"Champion: {club_name(champion.club_id)}",
                    f"Record: {champion.wins}-{champion.losses}-{champion.draws}",
                    f"Points: {champion.points}",
                    f"Elimination differential: {champion.elimination_differential:+}",
                ]
            )
        return OffseasonCeremonyBeat(key, "Champion", body)

    if key == "recap":
        if not ordered_standings:
            body = "No standings rows were recorded."
        else:
            lines = ["Final Table:"]
            for index, row in enumerate(ordered_standings, 1):
                marker = " *" if row.club_id == player_club_id else ""
                lines.append(
                    f"{index:>2}. {club_name(row.club_id):<22} {row.wins}-{row.losses}-{row.draws} "
                    f"pts={row.points} diff={row.elimination_differential:+}{marker}"
                )
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Recap", body)

    if key == "awards":
        if not award_rows:
            body = "No awards were posted for this season."
        else:
            lines = ["Season Awards:"]
            for award in award_rows:
                lines.append(
                    f"{title_label(award.award_type)}: "
                    f"{player_name(award.player_id)} ({club_name(award.club_id)})"
                )
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Awards", body)

    if key == "records_ratified":
        entries = []
        if records_payload_json:
            try:
                entries = list(json.loads(records_payload_json) or [])
            except (TypeError, ValueError):
                entries = []
        if not entries:
            body = "No new records were set this season."
        else:
            lines = ["New league records:"]
            for entry in entries:
                holder = entry.get("holder_name", entry.get("holder_id", "?"))
                prev = float(entry.get("previous_value", 0.0))
                new = float(entry.get("new_value", 0.0))
                detail = entry.get("detail", "")
                lines.append(
                    f"  {title_label(entry.get('record_type', '?'))}: "
                    f"{holder} {prev:g} -> {new:g} ({detail})"
                )
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Records Ratified", body)

    if key == "hof_induction":
        entries = []
        if hof_payload_json:
            try:
                entries = list(json.loads(hof_payload_json) or [])
            except (TypeError, ValueError):
                entries = []
        if not entries:
            body = "No new inductees this off-season."
        else:
            lines = ["Hall of Fame inductees:"]
            for entry in entries:
                reasons = ", ".join(entry.get("reasons", [])) or "qualified by score"
                lines.append(
                    f"  {entry.get('player_name', entry.get('player_id', '?'))}: "
                    f"legacy {float(entry.get('legacy_score', 0.0)):.1f} "
                    f"(threshold {float(entry.get('threshold', 0.0)):.1f})"
                )
                lines.append(
                    f"    {int(entry.get('seasons_played', 0))} seasons, "
                    f"{int(entry.get('championships', 0))} titles, "
                    f"{int(entry.get('awards_won', 0))} awards, "
                    f"{int(entry.get('total_eliminations', 0))} career eliminations"
                )
                lines.append(f"    Reasons: {reasons}")
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Hall of Fame Induction", body)

    if key == "development":
        rows = sorted(development, key=lambda row: (-abs(float(row.get("delta", 0))), str(row.get("player_id", ""))))[:8]
        lines = [f"Development applied to {len(development)} active players."]
        if not rows:
            lines.append("No active development rows were recorded.")
        for row in rows:
            marker = " *" if row.get("club_id") == player_club_id else ""
            lines.append(
                f"  {row.get('player_name', row.get('player_id'))} ({club_name(str(row.get('club_id', '')))}): "
                f"{float(row.get('before', 0)):.1f} -> {float(row.get('after', 0)):.1f} "
                f"({float(row.get('delta', 0)):+.1f}){marker}"
            )
        return OffseasonCeremonyBeat(key, "Development", "\n".join(lines))

    if key == "retirements":
        lines = [f"Retirements processed: {len(retirements)}"]
        if not retirements:
            lines.append("No players retired this off-season.")
        for row in retirements:
            marker = " *" if row.get("club_id") == player_club_id else ""
            lines.append(
                f"  {row.get('player_name', row.get('player_id'))} ({club_name(str(row.get('club_id', '')))}): "
                f"age {row.get('age')} OVR {float(row.get('overall', 0)):.1f}{marker}"
            )
        return OffseasonCeremonyBeat(key, "Retirements", "\n".join(lines))

    if key == "rookie_class_preview":
        payload_dict: Dict[str, Any] = {}
        if rookie_preview_payload_json:
            try:
                payload_dict = dict(json.loads(rookie_preview_payload_json) or {})
            except (TypeError, ValueError):
                payload_dict = {}
        class_size = int(payload_dict.get("class_size", 0))
        archetype_distribution: Dict[str, int] = dict(payload_dict.get("archetype_distribution", {}) or {})
        free_agent_count = int(payload_dict.get("free_agent_count", 0))
        top_band_depth = int(payload_dict.get("top_band_depth", 0))
        storylines = list(payload_dict.get("storylines", []) or [])
        source = str(payload_dict.get("source", "prospect_pool"))

        if class_size == 0 and free_agent_count == 0:
            body = "No incoming class data is available yet."
        else:
            lines = [f"Incoming class size: {class_size}"]
            lines.append(f"Top-band prospects (>= 70 OVR band low): {top_band_depth}")
            lines.append(f"Free-agent count: {free_agent_count}")
            if archetype_distribution:
                ordered = sorted(archetype_distribution.items(), key=lambda item: (-item[1], item[0]))
                lines.append("Archetype distribution: " + ", ".join(f"{name} {count}" for name, count in ordered))
            if storylines:
                lines.append("")
                lines.append("Market storylines:")
                for storyline in storylines:
                    lines.append(f"  - {storyline.get('sentence', '')}")
            if source == "legacy_free_agents":
                lines.append("")
                lines.append("(Legacy save: showing free-agent fallback only.)")
            lines.append("")
            lines.append("Continue to Recruitment Day.")
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Rookie Class Preview", body)

    if key == "recruitment":
        roster_sizes = sorted((club_id, len(list(roster))) for club_id, roster in rosters.items())
        signed = next((player for roster in rosters.values() for player in roster if player.id == signed_player_id), None)
        if recruitment_available:
            summary = dict(recruitment_summary or {})
            lines = ["Recruitment Day is active: compete with AI clubs for this prospect class."]
            lines.append(f"Current round: {int(summary.get('current_round', 1))}")
            lines.append(f"Available prospects: {int(summary.get('available_prospects', 0))}")
            lines.append(f"Signed this recruitment: {int(summary.get('signed_count', 0))}")
            lines.append(f"Snipes recorded: {int(summary.get('sniped_count', 0))}")
            if signed is not None:
                lines.append(f"Your latest signing: {signed.name} ({signed.overall():.1f} OVR)")
            lines.append("")
            lines.append("Current roster sizes:")
            for club_id, size in roster_sizes:
                lines.append(f"  {club_name(club_id)}: {size} players")
            return OffseasonCeremonyBeat(key, "Recruitment Day", "\n".join(lines))
        lines = ["v1 Draft is active: sign one rookie into your roster before beginning next season."]
        if signed is not None:
            lines.append(f"Signed rookie: {signed.name} ({signed.overall():.1f} OVR)")
        else:
            lines.append(f"Available rookies: {len(rookies)}")
            for player in sorted(rookies, key=lambda item: (-item.overall(), item.id))[:5]:
                lines.append(f"  {player.name}: OVR {player.overall():.1f} age {player.age}")
        lines.append("")
        lines.append("Current roster sizes:")
        for club_id, size in roster_sizes:
            lines.append(f"  {club_name(club_id)}: {size} players")
        return OffseasonCeremonyBeat(key, "Draft", "\n".join(lines))

    scheduled = next_season.scheduled_matches if next_season is not None else ()
    season_label = next_season.season_id if next_season is not None else "next season"
    lines = [f"{season_label} schedule is ready to be created."]
    if scheduled:
        lines.append("Opening fixtures:")
        for match in scheduled[: min(6, len(scheduled))]:
            lines.append(
                f"  Week {match.week}: {club_name(match.home_club_id)} vs {club_name(match.away_club_id)}"
            )
    else:
        lines.append("Begin Next Season will generate the next round-robin schedule.")
    return OffseasonCeremonyBeat(key, "Schedule Reveal", "\n".join(lines))


def career_rows_for_player(conn: sqlite3.Connection, player_id: str) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT pss.*,
               CASE
                 WHEN COALESCE(
                    (SELECT champion_club_id FROM season_outcomes WHERE season_id = pss.season_id),
                    (
                        SELECT club_id
                        FROM season_standings
                        WHERE season_id = pss.season_id
                        ORDER BY points DESC, elimination_differential DESC, club_id ASC
                        LIMIT 1
                    )
                 ) = pss.club_id THEN 1 ELSE 0
               END AS champion
        FROM player_season_stats pss
        WHERE pss.player_id = ?
        ORDER BY pss.season_id
        """,
        (player_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def update_manager_career_summaries(
    conn: sqlite3.Connection,
    season: Season,
    rosters: Mapping[str, List[Player]],
    awards: Iterable[Any],
) -> None:
    """Roll finalized season totals into the persisted career summary table."""
    award_rows = list(awards)
    player_lookup = {player.id: player for roster in rosters.values() for player in roster}
    for player_id, player in player_lookup.items():
        rows = career_rows_for_player(conn, player_id)
        if not rows:
            continue
        player_awards = [award for award in award_rows if award.player_id == player_id]
        club_ids = {str(row.get("club_id") or "") for row in rows if row.get("club_id")}
        summary = {
            "player_id": player_id,
            "player_name": player.name,
            "seasons_played": len(rows),
            "championships": sum(1 for row in rows if int(row.get("champion") or 0)),
            "awards_won": len(player_awards),
            "total_matches": sum(int(row.get("matches") or 0) for row in rows),
            "total_eliminations": sum(int(row.get("total_eliminations") or 0) for row in rows),
            "total_catches_made": sum(int(row.get("total_catches_made") or 0) for row in rows),
            "total_dodges_successful": sum(int(row.get("total_dodges_successful") or 0) for row in rows),
            "total_times_eliminated": sum(int(row.get("total_times_eliminated") or 0) for row in rows),
            "peak_eliminations": max((int(row.get("total_eliminations") or 0) for row in rows), default=0),
            "recent_eliminations": int(rows[-1].get("total_eliminations") or 0),
            "career_eliminations": sum(int(row.get("total_eliminations") or 0) for row in rows),
            "career_catches": sum(int(row.get("total_catches_made") or 0) for row in rows),
            "career_dodges": sum(int(row.get("total_dodges_successful") or 0) for row in rows),
            "clubs_served": len(club_ids),
        }
        save_player_career_stats(conn, player_id, summary)


def initialize_manager_offseason(
    conn: sqlite3.Connection,
    season: Season,
    clubs: Mapping[str, Club],
    rosters: Mapping[str, List[Player]],
    root_seed: int,
) -> Dict[str, List[Player]]:
    """Apply v1 off-season roster changes once and persist factual summaries."""
    if get_state(conn, "offseason_initialized_for") == season.season_id:
        return load_all_rosters(conn)

    season_stats = fetch_season_player_stats(conn, season.season_id)
    updated_rosters: Dict[str, List[Player]] = {}
    released_ai_players: List[Player] = []
    development_rows: List[Dict[str, Any]] = []
    retirement_rows: List[Dict[str, Any]] = []

    for club_id, roster in rosters.items():
        next_roster: List[Player] = []
        for player in roster:
            stats = season_stats.get(player.id, PlayerMatchStats())
            from .persistence import load_player_trajectory

            developed = apply_season_development(
                player,
                stats,
                facilities=(),
                rng=DeterministicRNG(derive_seed(root_seed, "manager_development", season.season_id, player.id)),
                trajectory=load_player_trajectory(conn, player.id),
            )
            aged = replace(developed, age=developed.age + 1)
            delta = round(aged.overall() - player.overall(), 2)
            if should_retire(aged, load_player_career_stats(conn, player.id)):
                save_retired_player(conn, aged, season.season_id, "age_decline")
                retirement_rows.append(
                    {
                        "player_id": aged.id,
                        "player_name": aged.name,
                        "club_id": club_id,
                        "age": aged.age,
                        "overall": round(aged.overall(), 1),
                        "reason": "age_decline",
                    }
                )
                continue
            development_rows.append(
                {
                    "player_id": aged.id,
                    "player_name": aged.name,
                    "club_id": club_id,
                    "before": round(player.overall(), 1),
                    "after": round(aged.overall(), 1),
                    "delta": delta,
                }
            )
            next_roster.append(aged)
        if club_id != get_state(conn, "player_club_id") and len(next_roster) > 9:
            next_roster, released = trim_ai_roster_for_offseason(next_roster, max_size=9)
            released_ai_players.extend(replace(player, club_id=None) for player in released)
        updated_rosters[club_id] = next_roster

    next_season_id = f"season_{int(season.season_id.rsplit('_', 1)[-1]) + 1}" if season.season_id.rsplit("_", 1)[-1].isdigit() else f"{season.season_id}_next"
    rookies = generate_rookie_class(
        next_season_id,
        DeterministicRNG(derive_seed(root_seed, "manager_draft", next_season_id)),
        size=12,
    )
    for club_id, club in clubs.items():
        save_club(conn, club, updated_rosters.get(club_id, []))
        save_lineup_default(conn, club_id, [player.id for player in updated_rosters.get(club_id, [])])
    save_free_agents(conn, rookies + released_ai_players, next_season_id)
    set_state(conn, "offseason_development_json", json.dumps(development_rows))
    set_state(conn, "offseason_retirements_json", json.dumps(retirement_rows))
    set_state(conn, "offseason_draft_signed_player_id", "")
    ratify_records(conn, season.season_id)
    induct_hall_of_fame(conn, season.season_id)
    next_class_year = (
        int(season.season_id.rsplit("_", 1)[-1]) + 1
        if season.season_id.rsplit("_", 1)[-1].isdigit()
        else 1
    )
    build_rookie_class_preview(conn, season.season_id, next_class_year)
    set_state(conn, "offseason_initialized_for", season.season_id)
    conn.commit()
    return updated_rosters


def friendly_preview_text(setup: MatchSetup) -> str:
    """Return a compact text preview for the sample friendly matchup."""
    return "\n\n".join((team_snapshot(setup.team_a), team_snapshot(setup.team_b)))


def friendly_match_stats(setup: MatchSetup, events: Iterable[Any]) -> Dict[str, PlayerMatchStats]:
    """Extract in-memory friendly stats without touching persistence."""
    return extract_all_stats(
        list(events),
        setup.team_a.id,
        setup.team_b.id,
        [player.id for player in setup.team_a.players],
        [player.id for player in setup.team_b.players],
    )


def format_bulk_sim_digest(
    *,
    matches_simmed: int,
    first_week: int | None,
    last_week: int | None,
    user_record: str,
    standings_note: str,
    notable_lines: Iterable[str],
    scouting_note: str,
    recruitment_note: str,
    next_action: str,
) -> str:
    """Return the V3 digest first-read after bulk simulation."""
    if first_week is None or last_week is None:
        weeks = "No weeks advanced"
    elif first_week == last_week:
        weeks = f"Week {first_week}"
    else:
        weeks = f"Weeks {first_week}-{last_week}"
    lines = [
        f"{matches_simmed} Matches Simmed",
        weeks,
        f"Your Club: {user_record}",
        "",
        "Standings Movement:",
        standings_note or "No standings movement.",
        "",
        "Notable Performances:",
    ]
    notables = list(notable_lines)
    lines.extend(f"- {line}" for line in notables) if notables else lines.append("- No standout stat lines.")
    lines.extend([
        "",
        "Scouting:",
        scouting_note or "No scouting updates.",
        "",
        "Recruitment:",
        recruitment_note or "No recruitment updates.",
        "",
        f"Next Recommended Action: {next_action}",
    ])
    return "\n".join(lines)


def _team_snapshot_for_ids(club: Club, roster: List[Player], ordered_player_ids: List[str]) -> Team:
    players_by_id = {player.id: player for player in roster}
    players = [players_by_id[player_id] for player_id in ordered_player_ids if player_id in players_by_id]
    return Team(id=club.club_id, name=club.name, players=tuple(players), coach_policy=club.coach_policy, chemistry=0.5)


def initialize_manager_career(
    conn: sqlite3.Connection,
    selected_club_id: str,
    root_seed: int,
) -> CareerStateCursor:
    """Create a fresh v1 Manager Mode career using the curated cast."""
    root_seed = normalize_root_seed(root_seed)
    for table in MANAGER_TABLES:
        conn.execute(f"DELETE FROM {table}")

    clubs = curated_clubs()
    selected_ids = {club.club_id for club in clubs}
    if selected_club_id not in selected_ids:
        raise ValueError(f"Unknown curated club: {selected_club_id}")

    rosters = {
        club.club_id: _club_roster(club, derive_seed(root_seed, "roster", club.club_id))
        for club in clubs
    }
    for club in clubs:
        save_club(conn, club, rosters[club.club_id])
        save_lineup_default(conn, club.club_id, [player.id for player in rosters[club.club_id]])

    league = League(
        league_id="manager_league",
        name="Dodgeball Premier League",
        conferences=(Conference("main", "Premier", tuple(club.club_id for club in clubs)),),
    )
    season = create_season("season_1", 2026, league, root_seed=root_seed)
    save_season(conn, season)
    save_season_format(conn, season.season_id, PLAYOFF_FORMAT)
    set_state(conn, "root_seed", str(root_seed))
    set_state(conn, "active_season_id", season.season_id)
    set_state(conn, "player_club_id", selected_club_id)
    set_state(conn, "difficulty", "pro")
    cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, season_number=1, week=1)
    save_career_state_cursor(conn, cursor)
    from .config import DEFAULT_SCOUTING_CONFIG
    from .scouting_center import initialize_scouting_for_career

    initialize_scouting_for_career(conn, root_seed=root_seed, config=DEFAULT_SCOUTING_CONFIG)
    conn.commit()
    return cursor


def initialize_build_a_club_career(
    conn: sqlite3.Connection,
    *,
    club_name: str,
    primary_color: str,
    secondary_color: str,
    venue_name: str,
    home_region: str,
    tagline: str,
    root_seed: int,
) -> CareerStateCursor:
    """Create a fresh Build a Club career with one expansion club."""
    root_seed = normalize_root_seed(root_seed)
    for table in MANAGER_TABLES:
        conn.execute(f"DELETE FROM {table}")

    expansion_club = build_expansion_club(
        name=club_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        venue_name=venue_name,
        home_region=home_region,
        tagline=tagline,
    )
    clubs = list(curated_clubs()) + [expansion_club]
    rosters: Dict[str, List[Player]] = {
        club.club_id: _club_roster(club, derive_seed(root_seed, "roster", club.club_id))
        for club in curated_clubs()
    }
    rosters[expansion_club.club_id] = generate_expansion_roster(expansion_club.club_id, root_seed)

    for club in clubs:
        save_club(conn, club, rosters[club.club_id])
        save_lineup_default(conn, club.club_id, [player.id for player in rosters[club.club_id]])

    league = League(
        league_id="manager_league",
        name="Dodgeball Premier League",
        conferences=(Conference("main", "Premier", tuple(club.club_id for club in clubs)),),
    )
    season = create_season("season_1", 2026, league, root_seed=root_seed)
    save_season(conn, season)
    save_season_format(conn, season.season_id, PLAYOFF_FORMAT)
    set_state(conn, "root_seed", str(root_seed))
    set_state(conn, "active_season_id", season.season_id)
    set_state(conn, "player_club_id", expansion_club.club_id)
    set_state(conn, "difficulty", "pro")
    set_state(conn, "career_path", "build_club")
    cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, season_number=1, week=1)
    save_career_state_cursor(conn, cursor)

    from .config import DEFAULT_SCOUTING_CONFIG
    from .recruitment_domain import build_recruitment_profile
    from .scouting_center import initialize_scouting_for_career
    from .persistence import save_club_recruitment_profile

    initialize_scouting_for_career(conn, root_seed=root_seed, config=DEFAULT_SCOUTING_CONFIG)
    for club in clubs:
        save_club_recruitment_profile(conn, build_recruitment_profile(root_seed, club.club_id))
    conn.commit()
    return cursor


def sign_prospect_to_club(
    conn: sqlite3.Connection,
    prospect,
    club_id: str,
    season_num: int,
) -> Player:
    from .recruitment import sign_prospect_to_club as sign

    return sign(conn, prospect, club_id, season_num)


def _is_already_signed(conn: sqlite3.Connection, class_year: int, player_id: str) -> bool:
    row = conn.execute(
        "SELECT is_signed FROM prospect_pool WHERE class_year = ? AND player_id = ?",
        (class_year, player_id),
    ).fetchone()
    return bool(row and row["is_signed"])


def apply_scouting_carry_forward_at_transition(
    conn: sqlite3.Connection,
    prior_class_year: int,
) -> None:
    from .config import DEFAULT_SCOUTING_CONFIG
    from .persistence import load_prospect_pool, load_scouting_state, save_scouting_state
    from .scouting_center import apply_carry_forward_decay

    for prospect in load_prospect_pool(conn, prior_class_year):
        if _is_already_signed(conn, prior_class_year, prospect.player_id):
            conn.execute("DELETE FROM scouting_state WHERE player_id = ?", (prospect.player_id,))
            continue
        state = load_scouting_state(conn, prospect.player_id)
        if state is not None:
            save_scouting_state(conn, apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG))
    conn.commit()


def create_next_manager_season(
    clubs: Mapping[str, Club],
    root_seed: int,
    season_number: int,
    year: int,
) -> Season:
    """Create the next Manager Mode season from the active club field."""
    league = League(
        league_id="manager_league",
        name="Dodgeball Premier League",
        conferences=(Conference("main", "Premier", tuple(clubs)),),
    )
    return create_season(f"season_{season_number}", year, league, root_seed=root_seed)


class ManagerModeApp:
    def __init__(self, master: tk.Tk, db_path: Path = DEFAULT_MANAGER_DB):
        self.master = master
        self.style = apply_theme(master)
        self.db_path = db_path
        self.conn = connect(db_path)
        create_schema(self.conn)

        self.clubs: Dict[str, Club] = {}
        self.rosters: Dict[str, List[Player]] = {}
        self.season = None
        self.cursor = load_career_state_cursor(self.conn)
        self.current_record = None
        self.current_stats: Dict[str, PlayerMatchStats] = {}
        self.current_friendly_setup: Optional[MatchSetup] = None
        self.current_engine_match_id: Optional[int] = None
        self.save_error: Optional[str] = None
        self.replay_index = 0
        self.replay_events = []
        self.replay_job: Optional[str] = None
        self.replay_canvas: Optional[tk.Canvas] = None
        self.replay_renderer: Optional[CourtRenderer] = None
        self.replay_setup: Optional[MatchSetup] = None
        self.replay_event_text: Optional[tk.Text] = None
        self.replay_banner_var = tk.StringVar(value="")
        self.replay_score_var = tk.StringVar(value="")
        self.replay_mvp_var = tk.StringVar(value="")
        self.replay_event_detail_var = tk.StringVar(value="")
        self.replay_playing = False
        self.replay_speed_ms = 1.0

        master.title("Dodgeball Manager Mode")
        master.geometry("1280x820")
        master.minsize(1080, 720)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(1, weight=1)

        self._build_shell()
        self._load_state()
        self._route_from_cursor()

    def _build_shell(self) -> None:
        self.topbar = tk.Frame(self.master, bg=DM_NIGHT, padx=SPACE_3, pady=SPACE_2)
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.columnconfigure(1, weight=1)
        self.title_var = tk.StringVar(value="Dodgeball Manager")
        self.context_var = tk.StringVar(value="Manager Mode")
        ttk.Label(self.topbar, textvariable=self.title_var, style="TopbarTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self.topbar, textvariable=self.context_var, style="TopbarMuted.TLabel").grid(row=1, column=0, sticky="w")

        nav = ttk.Frame(self.topbar)
        nav.grid(row=0, column=1, rowspan=2, sticky="e")
        self.nav_buttons: List[ttk.Button] = []
        for label, command in (
            ("Hub", self.show_hub),
            ("Roster", self.show_roster),
            ("Tactics", self.show_tactics),
            ("Scouting", self.show_scouting_center),
            ("League", self.show_league),
            ("Save", self._manual_save),
        ):
            button = ttk.Button(nav, text=label, command=command, style="Secondary.TButton")
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.nav_buttons.append(button)

        self.content = ttk.Frame(self.master, padding=SPACE_2)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

    def _clear(self) -> ttk.Frame:
        for child in self.content.winfo_children():
            child.destroy()
        frame = ttk.Frame(self.content)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        return frame

    def _set_nav_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in self.nav_buttons:
            button.configure(state=state)

    def _load_state(self) -> None:
        self.save_error = None
        try:
            self.clubs = load_clubs(self.conn)
            self.rosters = load_all_rosters(self.conn)
        except CorruptSaveError as exc:
            self.clubs = {}
            self.rosters = {}
            self.season = None
            self.save_error = str(exc)
            return
        season_id = get_state(self.conn, "active_season_id")
        if season_id:
            try:
                self.season = load_season(self.conn, season_id)
            except KeyError:
                self.season = None

    def _route_from_cursor(self) -> None:
        self._load_state()
        if self.save_error:
            self.show_save_recovery()
        elif self.cursor.state == CareerState.SPLASH or not self.clubs:
            self.show_splash()
        elif self.cursor.state == CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING:
            self.show_report(self.cursor.match_id)
        elif self.cursor.state == CareerState.SEASON_ACTIVE_IN_MATCH and self.cursor.match_id:
            match = self._scheduled_match(self.cursor.match_id)
            if match is not None:
                self.show_match_preview(match)
            else:
                self.show_hub()
        elif self.cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT:
            self.show_season_complete()
        else:
            self.show_hub()

    @property
    def player_club_id(self) -> Optional[str]:
        return get_state(self.conn, "player_club_id")

    @property
    def player_club(self) -> Optional[Club]:
        club_id = self.player_club_id
        return self.clubs.get(club_id) if club_id else None

    def show_splash(self) -> None:
        self._set_nav_enabled(False)
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        panel = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_3)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text="Dodgeball Manager", style="Display.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            panel,
            text="Pick a club, play the season, and review every outcome from the engine log.",
            style="Muted.TLabel",
            wraplength=680,
        ).grid(row=1, column=0, sticky="w", pady=(SPACE_1, SPACE_3))
        actions = ttk.Frame(panel)
        actions.grid(row=2, column=0, sticky="w")
        if self.clubs and self.player_club_id:
            ttk.Button(actions, text="Continue Career", command=self._continue_career, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(actions, text="New Career", command=self.show_club_picker, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(actions, text="Build a Club", command=self.show_build_a_club_form, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(actions, text="Friendly Match Sandbox", command=self.show_friendly_preview, style="Secondary.TButton").pack(side=tk.LEFT)

    def show_save_recovery(self) -> None:
        self._set_nav_enabled(False)
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        panel = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_3)
        panel.grid(row=0, column=0, sticky="nsew")
        ttk.Label(panel, text="Save file needs attention", style="Display.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            panel,
            text=f"Manager Mode could not read the current save. {self.save_error or ''}",
            style="Muted.TLabel",
            wraplength=720,
        ).grid(row=1, column=0, sticky="w", pady=(SPACE_1, SPACE_3))
        actions = ttk.Frame(panel)
        actions.grid(row=2, column=0, sticky="w")
        ttk.Button(actions, text="New Career", command=self.show_club_picker, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(actions, text="Build a Club", command=self.show_build_a_club_form, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(actions, text="Friendly Match Sandbox", command=self.show_friendly_preview, style="Secondary.TButton").pack(side=tk.LEFT)

    def _continue_career(self) -> None:
        if self.cursor.state == CareerState.SPLASH:
            self.cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, season_number=1, week=self._current_week() or 1)
            save_career_state_cursor(self.conn, self.cursor)
            self.conn.commit()
        self._route_from_cursor()

    def show_friendly_preview(self) -> None:
        self._set_nav_enabled(False)
        self._stop_replay()
        self.current_record = None
        self.current_stats = {}
        self.current_friendly_setup = sample_match_setup()
        self.title_var.set("Dodgeball Manager")
        self.context_var.set("Friendly Match Sandbox")
        frame = self._clear()
        frame.columnconfigure((0, 1), weight=1)
        ttk.Label(frame, text="Friendly Match", style="Display.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            frame,
            text="Sample matchup. Results stay off your career save.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, SPACE_2))
        for index, team in enumerate((self.current_friendly_setup.team_a, self.current_friendly_setup.team_b)):
            panel = ttk.LabelFrame(frame, text=team.name, style="Panel.TLabelframe", padding=SPACE_2)
            panel.grid(row=2, column=index, sticky="nsew", padx=(0, SPACE_2) if index == 0 else (0, 0))
            panel.columnconfigure(0, weight=1)
            text = self._text(panel, height=12, font=FONT_MONO)
            text.grid(row=0, column=0, sticky="nsew")
            text.insert(tk.END, team_snapshot(team))
            text.configure(state=tk.DISABLED)
        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=2, sticky="e", pady=SPACE_2)
        ttk.Button(actions, text="Back to Splash", command=self.show_splash, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(actions, text="Start Friendly", command=self._play_friendly_match, style="Accent.TButton").pack(side=tk.LEFT)

    def _play_friendly_match(self) -> None:
        setup = self.current_friendly_setup or sample_match_setup()
        result = MatchEngine().run(setup, seed=FRIENDLY_SEED, difficulty=FRIENDLY_DIFFICULTY)
        self.current_friendly_setup = setup
        self.current_record = MatchRecord(
            match_id=FRIENDLY_MATCH_ID,
            season_id="friendly",
            week=0,
            home_club_id=setup.team_a.id,
            away_club_id=setup.team_b.id,
            home_roster_hash="friendly",
            away_roster_hash="friendly",
            config_version=result.config_version,
            ruleset_version="default.v1",
            meta_patch_id=None,
            seed=result.seed,
            event_log_hash="friendly",
            final_state_hash="friendly",
            engine_match_id=None,
            result=result,
        )
        self.current_engine_match_id = None
        self.current_stats = friendly_match_stats(setup, result.events)
        self.replay_events = list(result.events)
        self.replay_index = 0
        self.show_replay_then_report(FRIENDLY_MATCH_ID)

    def show_club_picker(self) -> None:
        self._set_nav_enabled(False)
        frame = self._clear()
        frame.columnconfigure((0, 1, 2), weight=1)
        ttk.Label(frame, text="Take Over a Club", style="Display.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Choose one of the curated v1 clubs.", style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, SPACE_2))
        for index, club in enumerate(curated_clubs()):
            card = tk.Frame(frame, bg=DM_PAPER, highlightbackground=DM_BORDER, highlightthickness=1, padx=14, pady=12)
            card.grid(row=2 + index // 3, column=index % 3, sticky="nsew", padx=8, pady=8)
            card.columnconfigure(0, weight=1)
            swatch = tk.Frame(card, bg=club.primary_color, height=10)
            swatch.grid(row=0, column=0, sticky="ew")
            tk.Label(card, text=club.name, bg=DM_PAPER, fg=DM_CHARCOAL, font=("Segoe UI Semibold", 16)).grid(row=1, column=0, sticky="w", pady=(10, 2))
            tk.Label(card, text=club.venue_name, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(row=2, column=0, sticky="w")
            tk.Label(card, text=club.tagline, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY, wraplength=320, justify="left").grid(row=3, column=0, sticky="w", pady=(8, 12))
            ttk.Button(card, text="Confirm Coach", command=lambda c=club: self._start_new_career(c), style="Accent.TButton").grid(row=4, column=0, sticky="ew")
        footer = ttk.Frame(frame)
        footer.grid(row=4, column=0, columnspan=3, sticky="w", pady=(SPACE_2, 0))
        ttk.Button(footer, text="Build a Club", command=self.show_build_a_club_form, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(footer, text="Back to Splash", command=self.show_splash, style="Secondary.TButton").pack(side=tk.LEFT)

    def show_build_a_club_form(self) -> None:
        self._set_nav_enabled(False)
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Build a Club", style="Display.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            frame,
            text="Create your expansion identity and start directly into season one.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, SPACE_2))
        form = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        form.grid(row=2, column=0, sticky="ew")
        form.columnconfigure(1, weight=1)

        field_defaults = (
            ("Club Name", "Portland Breakers"),
            ("Primary Color", "#1A365D"),
            ("Secondary Color", "#F6AD55"),
            ("Venue", "Breaker Gym"),
            ("Home Region", "Portland"),
            ("Tagline", "Built from the floor up."),
        )
        field_vars: Dict[str, tk.StringVar] = {}
        for row, (label, value) in enumerate(field_defaults):
            ttk.Label(form, text=label, style="CardValue.TLabel").grid(row=row, column=0, sticky="w", pady=(0, SPACE_1))
            var = tk.StringVar(value=value)
            field_vars[label] = var
            ttk.Entry(form, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(SPACE_2, 0), pady=(0, SPACE_1))

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, sticky="e", pady=SPACE_2)
        ttk.Button(actions, text="Back", command=self.show_splash, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(
            actions,
            text="Start Build a Club Career",
            command=lambda: self._start_build_a_club_career(field_vars),
            style="Accent.TButton",
        ).pack(side=tk.LEFT)

    def _start_build_a_club_career(self, fields: Mapping[str, tk.StringVar]) -> None:
        root_seed = random.randint(1, 999_999)
        club_name = fields["Club Name"].get().strip() or "Expansion Club"
        self.cursor = initialize_build_a_club_career(
            self.conn,
            club_name=club_name,
            primary_color=fields["Primary Color"].get().strip() or "#1A365D",
            secondary_color=fields["Secondary Color"].get().strip() or "#F6AD55",
            venue_name=fields["Venue"].get().strip() or f"{club_name} Gym",
            home_region=fields["Home Region"].get().strip() or "Independent",
            tagline=fields["Tagline"].get().strip() or "Expansion club",
            root_seed=root_seed,
        )
        self._load_state()
        self.show_hub()

    def _start_new_career(self, selected: Club) -> None:
        root_seed = random.randint(1, 999_999)
        self.cursor = initialize_manager_career(self.conn, selected.club_id, root_seed)
        self._load_state()
        self.show_hub()

    def _current_week(self) -> Optional[int]:
        if self.season is None:
            return None
        return game_current_week(self.conn, self.season)

    def _playoffs_enabled(self) -> bool:
        return self.season is not None and load_season_format(self.conn, self.season.season_id) == PLAYOFF_FORMAT

    def _regular_season_complete(self) -> bool:
        if self.season is None:
            return False
        completed = load_completed_match_ids(self.conn, self.season.season_id)
        return all(match.match_id in completed for match in _regular_season_matches(self.season))

    def _simulate_ai_matches(self, matches: List[ScheduledMatch]) -> None:
        if not matches:
            return
        records, _ = simulate_matchday(
            matches,
            self.clubs,
            self.rosters,
            stored_root_seed(self.conn),
            difficulty=get_state(self.conn, "difficulty", "pro") or "pro",
        )
        for record in records:
            self._persist_record(record, record.home_club_id, record.away_club_id, None)

    def _advance_playoffs_if_needed(self) -> None:
        if self.season is None or not self._playoffs_enabled():
            return
        if load_season_outcome(self.conn, self.season.season_id) is not None:
            return
        if not self._regular_season_complete():
            return

        while True:
            bracket = load_playoff_bracket(self.conn, self.season.season_id)
            completed = load_completed_match_ids(self.conn, self.season.season_id)
            if bracket is None:
                standings = _standings_with_all_clubs(load_standings(self.conn, self.season.season_id), self.clubs)
                next_week = max((match.week for match in _regular_season_matches(self.season)), default=0) + 1
                bracket, semifinals = create_semifinal_bracket(self.season.season_id, standings, next_week)
                save_playoff_bracket(self.conn, bracket)
                save_scheduled_matches(self.conn, semifinals)
                self.conn.commit()
                self.season = load_season(self.conn, self.season.season_id)
                continue

            if bracket.status == "semifinals_scheduled":
                semifinal_matches = [
                    match for match in self.season.scheduled_matches
                    if match.match_id in {f"{self.season.season_id}_p_r1_m1", f"{self.season.season_id}_p_r1_m2"}
                ]
                pending = [match for match in semifinal_matches if match.match_id not in completed]
                ai_pending = [
                    match for match in pending
                    if self.player_club_id not in (match.home_club_id, match.away_club_id)
                ]
                if ai_pending:
                    self._simulate_ai_matches(ai_pending)
                    self._recompute_standings()
                    continue
                if pending:
                    return
                winners = {
                    row["match_id"]: row["winner_club_id"]
                    for row in self.conn.execute(
                        "SELECT match_id, winner_club_id FROM match_records WHERE match_id IN (?, ?)",
                        (f"{self.season.season_id}_p_r1_m1", f"{self.season.season_id}_p_r1_m2"),
                    ).fetchall()
                }
                next_week = max(match.week for match in semifinal_matches) + 1
                bracket, final = create_final_match(bracket, winners, next_week)
                save_playoff_bracket(self.conn, bracket)
                save_scheduled_matches(self.conn, [final])
                self.conn.commit()
                self.season = load_season(self.conn, self.season.season_id)
                continue

            if bracket.status == "final_scheduled":
                final = next((match for match in self.season.scheduled_matches if match.match_id == f"{self.season.season_id}_p_final"), None)
                if final is None:
                    return
                if final.match_id not in completed:
                    if self.player_club_id in (final.home_club_id, final.away_club_id):
                        return
                    self._simulate_ai_matches([final])
                    self._recompute_standings()
                    completed = load_completed_match_ids(self.conn, self.season.season_id)
                if final.match_id in completed:
                    row = self.conn.execute(
                        "SELECT winner_club_id FROM match_records WHERE match_id = ?",
                        (final.match_id,),
                    ).fetchone()
                    if row is None or row["winner_club_id"] is None:
                        return
                    outcome = outcome_from_final(
                        bracket,
                        final_match_id=final.match_id,
                        home_club_id=final.home_club_id,
                        away_club_id=final.away_club_id,
                        winner_club_id=row["winner_club_id"],
                    )
                    save_season_outcome(self.conn, outcome)
                    save_playoff_bracket(
                        self.conn,
                        replace(bracket, status="complete"),
                    )
                    self.conn.commit()
                return
            return

    def _next_user_match(self) -> Optional[ScheduledMatch]:
        if self.season is None or not self.player_club_id:
            return None
        completed = load_completed_match_ids(self.conn, self.season.season_id)
        for week in range(1, self.season.total_weeks() + 1):
            for match in self.season.matches_for_week(week):
                if match.match_id in completed:
                    continue
                if self.player_club_id in (match.home_club_id, match.away_club_id):
                    return match
        return None

    def _scheduled_match(self, match_id: str) -> Optional[ScheduledMatch]:
        if self.season is None:
            return None
        return next((match for match in self.season.scheduled_matches if match.match_id == match_id), None)

    def _record_for_match(self, match_id: str) -> Optional[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM match_records WHERE match_id = ?", (match_id,)).fetchone()

    def _refresh_header(self) -> None:
        club = self.player_club
        if club is None:
            self.title_var.set("Dodgeball Manager")
            self.context_var.set("Manager Mode")
            return
        standings = _standings_with_all_clubs(load_standings(self.conn, self.season.season_id), self.clubs) if self.season else []
        row = next((item for item in standings if item.club_id == club.club_id), None)
        record = "0-0" if row is None else f"{row.wins}-{row.losses}"
        week = self._current_week()
        week_text = "Season complete" if week is None else f"Week {week} of {self.season.total_weeks()}"
        self.title_var.set(club.name)
        self.context_var.set(f"{record} | Season {self.cursor.season_number or 1} | {week_text} | {club.venue_name}")

    def show_hub(self) -> None:
        self._set_nav_enabled(True)
        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        club = self.player_club
        self._advance_playoffs_if_needed()
        match = self._next_user_match()
        if club is None or self.season is None:
            self.show_splash()
            return
        from .ui_components import PageHeader
        PageHeader(frame, "Season Hub").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_2))
        next_panel = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        next_panel.grid(row=1, column=0, sticky="ew", padx=(0, SPACE_2), pady=(SPACE_1, SPACE_2))
        next_panel.columnconfigure(0, weight=1)
        if match is None:
            ttk.Label(next_panel, text="Regular Season Complete", style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Button(next_panel, text="View Season Recap", command=self.show_season_complete, style="Accent.TButton").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))
        else:
            opponent_id = match.away_club_id if match.home_club_id == club.club_id else match.home_club_id
            opponent = self.clubs[opponent_id]
            ttk.Label(next_panel, text=f"Next Match: {club.name} vs {opponent.name}", style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(next_panel, text=f"{opponent.tagline} | {season_format_summary()['champion_rule'].replace('_', ' ')}", style="Muted.TLabel").grid(row=1, column=0, sticky="w")
            actions = ttk.Frame(next_panel)
            actions.grid(row=2, column=0, sticky="w", pady=(SPACE_1, 0))
            ttk.Button(actions, text="Play Next Match", command=lambda: self.show_match_preview(match), style="Accent.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
            ttk.Button(actions, text="Sim Week", command=self._sim_week).pack(side=tk.LEFT, padx=(0, SPACE_1))
            ttk.Button(actions, text="Sim To Next User Match", command=self._sim_to_next_user_match).pack(side=tk.LEFT, padx=(0, SPACE_1))
            ttk.Button(actions, text="Sim Multiple Weeks", command=self._sim_multiple_weeks).pack(side=tk.LEFT, padx=(0, SPACE_1))
            ttk.Button(actions, text="Sim To Milestone", command=self._sim_to_milestone).pack(side=tk.LEFT)
        standings_panel = ttk.LabelFrame(frame, text="Standings", style="Panel.TLabelframe", padding=SPACE_2)
        standings_panel.grid(row=2, column=0, sticky="nsew", padx=(0, SPACE_2))
        self._fill_standings_tree(standings_panel)
        wire = ttk.LabelFrame(frame, text="League Wire", style="Panel.TLabelframe", padding=SPACE_2)
        wire.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=(SPACE_1, 0))
        wire.columnconfigure(0, weight=1)
        wire.rowconfigure(0, weight=1)
        text = self._text(wire)
        text.grid(row=0, column=0, sticky="nsew")
        text.insert(tk.END, self._hub_wire_text())
        text.configure(state=tk.DISABLED)

    def _simulate_match_for_schedule_row(self, scheduled: ScheduledMatch) -> MatchRecord:
        return simulate_scheduled_match(
            self.conn,
            scheduled=scheduled,
            clubs=self.clubs,
            rosters=self.rosters,
            root_seed=stored_root_seed(self.conn),
            difficulty=get_state(self.conn, "difficulty", "pro") or "pro",
            record_engine_match=False,
        )

    def _show_bulk_sim_digest(self, title: str, records: List[MatchRecord]) -> None:
        if not records:
            messagebox.showinfo("Simulation", "No matches were simulated.")
            self.show_hub()
            return
        wins = losses = draws = 0
        for record in records:
            if self.player_club_id not in (record.home_club_id, record.away_club_id):
                continue
            if record.result.winner_team_id is None:
                draws += 1
            elif record.result.winner_team_id == self.player_club_id:
                wins += 1
            else:
                losses += 1
        first_week = min(record.week for record in records)
        last_week = max(record.week for record in records)
        next_match = self._next_user_match()
        message = format_bulk_sim_digest(
            matches_simmed=len(records),
            first_week=first_week,
            last_week=last_week,
            user_record=f"{wins}-{losses}-{draws}",
            standings_note=self._standings_movement_note(),
            notable_lines=self._bulk_sim_notables(records),
            scouting_note="Scout reveals remain available from the Scouting Center.",
            recruitment_note=self._recruitment_digest_note(),
            next_action="Match Day ready." if next_match is not None else "Regular season complete.",
        )
        messagebox.showinfo(title, message)
        self.show_hub()

    def _standings_movement_note(self) -> str:
        if self.season is None:
            return "Standings unavailable."
        standings = _standings_with_all_clubs(load_standings(self.conn, self.season.season_id), self.clubs)
        if not standings:
            return "No standings movement yet."
        leader = standings[0]
        return f"{self.clubs[leader.club_id].name} leads at {leader.wins}-{leader.losses}-{leader.draws}."

    def _bulk_sim_notables(self, records: List[MatchRecord]) -> List[str]:
        lines: List[str] = []
        for record in records[:3]:
            stats = extract_match_stats(record, self.rosters[record.home_club_id], self.rosters[record.away_club_id])
            mvp_id = compute_match_mvp(stats)
            if mvp_id:
                winner_name = self.clubs[record.result.winner_team_id].name if record.result.winner_team_id in self.clubs else "Draw"
                lines.append(f"{self._player_name_for_wire(mvp_id)} led {winner_name} in {record.match_id}.")
        if len(records) > 3:
            lines.append(f"{len(records) - 3} additional match results were persisted.")
        return lines

    def _recruitment_digest_note(self) -> str:
        if self.cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING:
            return "Recruitment day is ready."
        return "No recruitment decision is pending."

    def _sim_week(self) -> None:
        if self.season is None or not self.player_club_id:
            return
        week = self._current_week()
        if week is None:
            self.show_hub()
            return
        completed = load_completed_match_ids(self.conn, self.season.season_id)
        has_user_match = any(
            self.player_club_id in (m.home_club_id, m.away_club_id)
            for m in self.season.matches_for_week(week)
            if m.match_id not in completed
        )
        include_user = False
        if has_user_match:
            include_user = messagebox.askyesno(
                "Sim Week", "This week includes your match. Sim it automatically?"
            )
        chosen, _stop = choose_matches_to_sim(
            list(self.season.scheduled_matches),
            completed,
            self.player_club_id,
            SimRequest(mode="week", current_week=week, include_user_matches=include_user),
        )
        records = [self._simulate_match_for_schedule_row(m) for m in chosen]
        self._recompute_standings()
        self._advance_playoffs_if_needed()
        next_week = self._current_week() or 0
        self.cursor = CareerStateCursor(
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            season_number=self.cursor.season_number,
            week=next_week,
        )
        save_career_state_cursor(self.conn, self.cursor)
        self.conn.commit()
        self._show_bulk_sim_digest("Week Sim Complete", records)

    def _sim_to_next_user_match(self) -> None:
        if self.season is None or not self.player_club_id:
            return
        completed = load_completed_match_ids(self.conn, self.season.season_id)
        chosen, stop = choose_matches_to_sim(
            list(self.season.scheduled_matches),
            completed,
            self.player_club_id,
            SimRequest(mode="to_next_user_match"),
        )
        if stop.reason == "season_complete" and not chosen:
            messagebox.showinfo("Simulation", "No remaining user matches in this season.")
            self.show_hub()
            return
        records = [self._simulate_match_for_schedule_row(m) for m in chosen]
        self._recompute_standings()
        self._advance_playoffs_if_needed()
        next_week = stop.week or self._current_week() or 0
        self.cursor = CareerStateCursor(
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            season_number=self.cursor.season_number,
            week=next_week,
        )
        save_career_state_cursor(self.conn, self.cursor)
        self.conn.commit()
        self._show_bulk_sim_digest("Simulation Stopped At User Match", records)

    def _sim_multiple_weeks(self) -> None:
        if self.season is None or not self.player_club_id:
            return
        count = simpledialog.askinteger(
            "Sim Multiple Weeks", "How many weeks to simulate?",
            minvalue=1, maxvalue=max(1, self.season.total_weeks()),
        )
        if not count:
            return
        completed = load_completed_match_ids(self.conn, self.season.season_id)
        start_week = self._current_week() or 1
        chosen, stop = choose_matches_to_sim(
            list(self.season.scheduled_matches),
            completed,
            self.player_club_id,
            SimRequest(mode="multiple_weeks", current_week=start_week, weeks=count, include_user_matches=False),
        )
        records = [self._simulate_match_for_schedule_row(m) for m in chosen]
        self._recompute_standings()
        self._advance_playoffs_if_needed()
        self.conn.commit()
        title = "Simulation Stopped At User Match" if stop.reason == "user_match" else "Multi-Week Simulation Complete"
        self._show_bulk_sim_digest(title, records)

    def _sim_to_milestone(self) -> None:
        if self.season is None or not self.player_club_id:
            return

        _options = ["Playoffs", "Season End", "Recruitment Day", "Offseason"]
        _normalized_map = {
            "Playoffs": "playoffs",
            "Season End": "season_end",
            "Recruitment Day": "recruitment_day",
            "Offseason": "offseason",
        }

        chosen_var: list[str] = []

        def _confirm() -> None:
            sel = combo.get()
            if sel in _normalized_map:
                chosen_var.append(_normalized_map[sel])
            dlg.destroy()

        dlg = tk.Toplevel(self.master)
        dlg.title("Sim To Milestone")
        dlg.resizable(False, False)
        dlg.grab_set()
        ttk.Label(dlg, text="Jump to milestone:", style="Body.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 4))
        combo = ttk.Combobox(dlg, values=_options, state="readonly", width=22)
        combo.set(_options[0])
        combo.grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 12))
        ttk.Button(dlg, text="Sim", command=_confirm, style="Accent.TButton").grid(row=2, column=0, sticky="e", padx=(16, 4), pady=(0, 16))
        ttk.Button(dlg, text="Cancel", command=dlg.destroy, style="Secondary.TButton").grid(row=2, column=1, sticky="w", padx=(4, 16), pady=(0, 16))
        self.master.wait_window(dlg)

        if not chosen_var:
            return
        normalized = chosen_var[0]
        completed = load_completed_match_ids(self.conn, self.season.season_id)

        if normalized == "playoffs":
            chosen, stop = choose_matches_to_sim(
                list(self.season.scheduled_matches),
                completed,
                self.player_club_id,
                SimRequest(mode="milestone", milestone="playoffs", include_user_matches=True),
            )
            records = [self._simulate_match_for_schedule_row(m) for m in chosen]
            self._recompute_standings()
            self._advance_playoffs_if_needed()
            self.conn.commit()
            self._show_bulk_sim_digest("Reached Playoffs Milestone", records)
            return

        # For season_end, recruitment_day, offseason: sim all regular-season matches then stop
        regular = _regular_season_matches(self.season)
        last_week = max((m.week for m in regular), default=None)
        milestone_week = (last_week or 0) + 1
        chosen, stop = choose_matches_to_sim(
            list(self.season.scheduled_matches),
            completed,
            self.player_club_id,
            SimRequest(mode="milestone", milestone=normalized, milestone_week=milestone_week, include_user_matches=True),
        )
        records = [self._simulate_match_for_schedule_row(m) for m in chosen]
        self._recompute_standings()
        self._advance_playoffs_if_needed()
        self.conn.commit()
        # Sim playoff matches too for season_end
        if normalized == "season_end":
            while True:
                self._advance_playoffs_if_needed()
                completed_now = load_completed_match_ids(self.conn, self.season.season_id)
                pending = [m for m in self.season.scheduled_matches if m.match_id not in completed_now]
                if not pending:
                    self._recompute_standings()
                    self.conn.commit()
                    self._show_bulk_sim_digest("Reached Season End", records)
                    return
                for m in pending:
                    records.append(self._simulate_match_for_schedule_row(m))
        label = {"recruitment_day": "Ready For Recruitment Day", "offseason": "Reached Offseason"}.get(normalized, "Milestone Reached")
        self._show_bulk_sim_digest(label, records)

    def _hub_wire_text(self) -> str:
        lines = []
        if self.season:
            completed = load_completed_match_ids(self.conn, self.season.season_id)
            lines.append(f"{len(completed)} matches completed.")
            lines.append(f"Format: {season_format_summary()['format'].replace('_', ' ')}.")
        awards = load_awards(self.conn, self.season.season_id) if self.season else []
        if awards:
            lines.append("")
            lines.append("Awards posted:")
            lines.extend(
                f"{title_label(award.award_type)}: {self._player_name_for_wire(award.player_id)}"
                for award in awards
            )
        else:
            lines.append("")
            lines.append("Season headlines will populate after match reports.")
        return "\n".join(lines)

    def _fill_standings_tree(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        tree = ttk.Treeview(parent, columns=("club", "w", "l", "d", "pts", "diff"), show="headings")
        for key, label, width in (("club", "Club", 220), ("w", "W", 48), ("l", "L", 48), ("d", "D", 48), ("pts", "Pts", 60), ("diff", "Diff", 70)):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="center", stretch=key == "club")
        tree.grid(row=0, column=0, sticky="nsew")
        tree.tag_configure("user", background=DM_OFF_WHITE_LINE)
        if self.season:
            for row in _standings_with_all_clubs(load_standings(self.conn, self.season.season_id), self.clubs):
                tags = ("user",) if row.club_id == self.player_club_id else ()
                tree.insert(
                    "",
                    tk.END,
                    values=(self.clubs[row.club_id].name, row.wins, row.losses, row.draws, row.points, row.elimination_differential),
                    tags=tags,
                )

    def show_match_preview(self, match: ScheduledMatch) -> None:
        self.cursor = advance(self.cursor, CareerState.SEASON_ACTIVE_IN_MATCH, week=match.week, match_id=match.match_id)
        save_career_state_cursor(self.conn, self.cursor)
        self.conn.commit()
        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure((0, 1), weight=1)
        ttk.Label(frame, text="Match Preview", style="Display.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        for index, club_id in enumerate((match.home_club_id, match.away_club_id)):
            club = self.clubs[club_id]
            roster = self.rosters[club_id]
            panel = ttk.LabelFrame(frame, text=club.name, style="Panel.TLabelframe", padding=SPACE_2)
            panel.grid(row=1, column=index, sticky="nsew", padx=(0, SPACE_2) if index == 0 else (0, 0), pady=SPACE_2)
            panel.columnconfigure(0, weight=1)
            ttk.Label(panel, text=f"{club.venue_name} | {team_overall(self._team_for_club(club, roster)):.1f} OVR", style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(panel, text=club.tagline, style="Muted.TLabel", wraplength=460).grid(row=1, column=0, sticky="w", pady=(0, SPACE_1))
            text = self._text(panel, height=12)
            text.grid(row=2, column=0, sticky="nsew")
            text.insert(tk.END, self._lineup_text(club_id))
            text.configure(state=tk.DISABLED)
        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, columnspan=2, sticky="e")
        ttk.Button(actions, text="Back to Hub", command=self._return_to_hub_from_preview, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(actions, text="Start Match", command=lambda: self._play_user_week(match), style="Accent.TButton").pack(side=tk.LEFT)

    def _return_to_hub_from_preview(self) -> None:
        if self.cursor.state == CareerState.SEASON_ACTIVE_IN_MATCH:
            self.cursor = CareerStateCursor(
                state=CareerState.SEASON_ACTIVE_PRE_MATCH,
                season_number=self.cursor.season_number,
                week=self.cursor.week,
            )
            save_career_state_cursor(self.conn, self.cursor)
            self.conn.commit()
        self.show_hub()

    def _team_for_club(self, club: Club, roster: List[Player]) -> Team:
        return Team(id=club.club_id, name=club.name, players=tuple(roster), coach_policy=club.coach_policy, chemistry=0.5)

    def _active_team_for_club(self, club: Club, roster: List[Player]) -> Team:
        default = load_lineup_default(self.conn, club.club_id)
        resolver = LineupResolver()
        resolved = resolver.resolve(roster, default, None)
        return _team_snapshot_for_ids(club, roster, resolver.active_starters(resolved))

    def _lineup_text(self, club_id: str) -> str:
        roster = self.rosters[club_id]
        default = load_lineup_default(self.conn, club_id)
        ordered_ids = LineupResolver().resolve(roster, default, None)
        by_id = {player.id: player for player in roster}
        starter_ids = ordered_ids[:STARTERS_COUNT]
        bench_ids = ordered_ids[STARTERS_COUNT:]
        lines = [f"Starters ({len(starter_ids)}/{STARTERS_COUNT})", ""]
        for index, player_id in enumerate(starter_ids, 1):
            player = by_id[player_id]
            lines.append(f"{index}. {player.name} | {player_role(player)} | OVR {player.overall():.1f}")
        lines.extend(["", f"Bench ({len(bench_ids)})", ""])
        for index, player_id in enumerate(bench_ids, 1):
            player = by_id[player_id]
            lines.append(f"{index}. {player.name} | {player_role(player)} | OVR {player.overall():.1f}")
        return "\n".join(lines)

    def _play_user_week(self, user_match: ScheduledMatch) -> None:
        if self.season is None:
            return
        week_matches = [match for match in self.season.matches_for_week(user_match.week) if match.match_id not in load_completed_match_ids(self.conn, self.season.season_id)]
        other_matches = [match for match in week_matches if match.match_id != user_match.match_id]
        if other_matches:
            other_records, _ = simulate_matchday(other_matches, self.clubs, self.rosters, stored_root_seed(self.conn))
            for record in other_records:
                self._persist_record(record, record.home_club_id, record.away_club_id, None)

        home_default = load_lineup_default(self.conn, user_match.home_club_id)
        away_default = load_lineup_default(self.conn, user_match.away_club_id)
        home_override = load_match_lineup_override(self.conn, user_match.match_id, user_match.home_club_id)
        away_override = load_match_lineup_override(self.conn, user_match.match_id, user_match.away_club_id)
        record, _ = simulate_match(
            scheduled=user_match,
            home_club=self.clubs[user_match.home_club_id],
            away_club=self.clubs[user_match.away_club_id],
            home_roster=self.rosters[user_match.home_club_id],
            away_roster=self.rosters[user_match.away_club_id],
            root_seed=stored_root_seed(self.conn),
            difficulty=get_state(self.conn, "difficulty", "pro") or "pro",
            home_lineup_default=home_default,
            away_lineup_default=away_default,
            home_lineup_override=home_override,
            away_lineup_override=away_override,
        )
        engine_match_id = self._persist_record(record, user_match.home_club_id, user_match.away_club_id, record)
        self.current_record = record
        self.current_engine_match_id = engine_match_id
        self.current_stats = extract_match_stats(record, self.rosters[record.home_club_id], self.rosters[record.away_club_id])
        self.replay_events = list(record.result.events)
        self.replay_index = 0
        self._recompute_standings()
        self.cursor = advance(self.cursor, CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, match_id=user_match.match_id)
        save_career_state_cursor(self.conn, self.cursor)
        self.conn.commit()
        self.show_replay_then_report(user_match.match_id)

    def _persist_record(self, record, home_id: str, away_id: str, engine_record) -> Optional[int]:
        engine_match_id = persist_match_record(
            self.conn,
            record,
            clubs=self.clubs,
            rosters=self.rosters,
            difficulty=get_state(self.conn, "difficulty", "pro") or "pro",
            record_engine_match=engine_record is not None,
        )
        self.conn.commit()
        return engine_match_id

    def show_replay_then_report(self, match_id: str) -> None:
        self._stop_replay()
        if self.current_record is None:
            self.show_report(match_id)
            return
        frame = self._clear()
        frame.columnconfigure(0, weight=3)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        from .ui_components import PageHeader
        PageHeader(frame, "Match Replay").grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_2))

        hud = tk.Frame(frame, bg=DM_PAPER, highlightbackground=DM_BORDER, highlightthickness=1, padx=14, pady=10)
        hud.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SPACE_1, 0))
        hud.columnconfigure(1, weight=1)
        tk.Label(hud, textvariable=self.replay_score_var, bg=DM_PAPER, fg=DM_CHARCOAL, font=("Segoe UI Semibold", 15)).grid(row=0, column=0, sticky="w")
        tk.Label(hud, textvariable=self.replay_banner_var, bg=DM_PAPER, fg=DM_BRICK, font=("Bahnschrift SemiBold", 15)).grid(row=0, column=1, sticky="ew")
        tk.Label(hud, textvariable=self.replay_mvp_var, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=FONT_BODY).grid(row=0, column=2, sticky="e")

        self.replay_canvas = tk.Canvas(frame, bg=DM_PAPER, highlightbackground=DM_BORDER, highlightthickness=1, height=430)
        self.replay_canvas.grid(row=2, column=0, sticky="nsew", padx=(0, SPACE_2), pady=SPACE_2)
        self.replay_setup = self._setup_for_current_record()
        self.replay_renderer = CourtRenderer(self.replay_canvas)
        side = ttk.LabelFrame(frame, text="Event Log", style="Panel.TLabelframe", padding=SPACE_2)
        side.grid(row=2, column=1, sticky="nsew", pady=SPACE_2)
        side.rowconfigure(1, weight=1)
        side.columnconfigure(0, weight=1)
        ttk.Label(side, text="Current Event", style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(side, textvariable=self.replay_event_detail_var, style="Muted.TLabel", wraplength=360).grid(row=1, column=0, sticky="ew", pady=(SPACE_1, 0))
        self.replay_event_text = self._text(side, font=FONT_MONO)
        self.replay_event_text.grid(row=2, column=0, sticky="nsew", pady=(SPACE_1, 0))
        controls = ttk.Frame(side)
        controls.grid(row=3, column=0, sticky="ew", pady=(SPACE_1, 0))
        controls.columnconfigure((0, 1, 2, 3), weight=1)
        ttk.Button(controls, text="Back", command=self._replay_prev, style="Secondary.TButton").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(controls, text="Play/Pause", command=self._toggle_replay, style="Accent.TButton").grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(controls, text="Next", command=self._replay_next, style="Secondary.TButton").grid(row=0, column=2, sticky="ew", padx=(4, 4))
        ttk.Button(controls, text="Key Event", command=self._jump_to_key_event, style="Secondary.TButton").grid(row=0, column=3, sticky="ew")
        speed = ttk.Frame(side)
        speed.grid(row=4, column=0, sticky="ew", pady=(SPACE_1, 0))
        ttk.Label(speed, text="Speed", style="Muted.TLabel").pack(side=tk.LEFT)
        ttk.Button(speed, text="0.5x", command=lambda: self._set_replay_speed(2.0), style="Secondary.TButton").pack(side=tk.LEFT, padx=(SPACE_1, 4))
        ttk.Button(speed, text="1x", command=lambda: self._set_replay_speed(1.0), style="Secondary.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(speed, text="2x", command=lambda: self._set_replay_speed(0.5), style="Secondary.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(speed, text="4x", command=lambda: self._set_replay_speed(0.25), style="Secondary.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(side, text="Skip to Final Report", command=lambda: self.show_report(match_id), style="Accent.TButton").grid(row=5, column=0, sticky="ew", pady=(SPACE_1, 0))
        ttk.Button(frame, text="Open Match Report", command=lambda: self.show_report(match_id), style="Accent.TButton").grid(row=3, column=1, sticky="e")

        self.replay_index = 0
        self._render_replay_frame()
        self._start_replay()

    def _replay_colors(self) -> Dict[str, str]:
        if self.current_record is None:
            return {}
        if self.current_record.match_id == FRIENDLY_MATCH_ID:
            return {
                self.current_record.home_club_id: DM_BRICK,
                self.current_record.away_club_id: DM_GYM_BLUE,
            }
        home = self.clubs[self.current_record.home_club_id]
        away = self.clubs[self.current_record.away_club_id]
        return {
            home.club_id: home.primary_color or DM_BRICK,
            away.club_id: away.primary_color or DM_GYM_BLUE,
        }

    def _setup_for_current_record(self) -> MatchSetup:
        if self.current_record is None:
            return sample_match_setup()
        if self.current_record.match_id == FRIENDLY_MATCH_ID and self.current_friendly_setup is not None:
            return self.current_friendly_setup
        home_active_ids = (
            self.current_record.home_active_player_ids
            or list(self.current_record.result.box_score["teams"][self.current_record.home_club_id]["players"].keys())
        )
        away_active_ids = (
            self.current_record.away_active_player_ids
            or list(self.current_record.result.box_score["teams"][self.current_record.away_club_id]["players"].keys())
        )
        return MatchSetup(
            team_a=_team_snapshot_for_ids(
                self.clubs[self.current_record.home_club_id],
                self.rosters[self.current_record.home_club_id],
                home_active_ids,
            ),
            team_b=_team_snapshot_for_ids(
                self.clubs[self.current_record.away_club_id],
                self.rosters[self.current_record.away_club_id],
                away_active_ids,
            ),
        )

    def _render_replay_frame(self) -> None:
        if not self.replay_renderer or not self.replay_setup or self.current_record is None:
            return
        event_index = min(self.replay_index, max(0, len(self.replay_events) - 1))
        self.replay_renderer.render(
            self.replay_setup,
            self.replay_events,
            event_index,
            team_colors=self._replay_colors(),
        )
        _name_map = {p.id: p.name for roster in self.rosters.values() for p in roster}
        raw_label = replay_event_label(self.replay_events[event_index], _name_map) if self.replay_events else "Ready"
        self.replay_banner_var.set(raw_label[:72] + "…" if len(raw_label) > 72 else raw_label)
        box = self.current_record.result.box_score["teams"]
        home = self.replay_setup.team_a
        away = self.replay_setup.team_b
        self.replay_score_var.set(
            f"{home.name} {box[home.id]['totals']['living']}  |  {away.name} {box[away.id]['totals']['living']}"
        )
        mvp_id = compute_match_mvp(self.current_stats)
        self.replay_mvp_var.set(f"MVP pace: {self._player_name_for_wire(mvp_id) if mvp_id else '-'}")
        if self.replay_events:
            self.replay_event_detail_var.set(self._event_detail_text(self.replay_events[event_index]))
        if self.replay_event_text is not None:
            self.replay_event_text.configure(state=tk.NORMAL)
            self.replay_event_text.delete("1.0", tk.END)
            start = max(0, event_index - 8)
            for index, event in enumerate(self.replay_events[start:event_index + 1], start):
                marker = ">" if index == event_index else " "
                self.replay_event_text.insert(tk.END, f"{marker} {event.tick:03d} {replay_event_label(event, _name_map)}\n")
            self.replay_event_text.configure(state=tk.DISABLED)

    def _start_replay(self) -> None:
        self._stop_replay()
        self.replay_playing = True
        self.replay_job = self.master.after(max(60, int(120 * self.replay_speed_ms)), self._replay_step)

    def _stop_replay(self) -> None:
        self.replay_playing = False
        if self.replay_job is not None:
            self.master.after_cancel(self.replay_job)
            self.replay_job = None

    def _replay_step(self) -> None:
        if not self.replay_events:
            self._stop_replay()
            return
        self._render_replay_frame()
        if self.replay_index >= len(self.replay_events) - 1:
            self._show_replay_final_moment()
            self._stop_replay()
            return
        delay = max(50, int(replay_phase_delay(self.replay_events[self.replay_index]) * self.replay_speed_ms))
        self.replay_index += 1
        self.replay_job = self.master.after(delay, self._replay_step)

    def _toggle_replay(self) -> None:
        if self.replay_playing:
            self._stop_replay()
        else:
            self._start_replay()

    def _set_replay_speed(self, multiplier: float) -> None:
        self.replay_speed_ms = multiplier
        if self.replay_playing:
            self._start_replay()

    def _jump_to_key_event(self) -> None:
        if not self.replay_events:
            return
        key_indices = [
            i for i, e in enumerate(self.replay_events)
            if e.event_type == "throw" and e.outcome.get("resolution") in {"hit", "failed_catch", "catch"}
        ]
        if not key_indices:
            self.replay_index = len(self.replay_events) - 1
        else:
            self.replay_index = min(key_indices, key=lambda i: abs(i - self.replay_index) if i >= self.replay_index else 10_000 + self.replay_index - i)
        self._stop_replay()
        self._render_replay_frame()

    def _event_detail_text(self, event) -> str:
        if event.event_type != "throw":
            return f"{title_label(event.event_type)}."
        thrower = self._player_name_for_wire(event.actors.get("thrower"))
        target = self._player_name_for_wire(event.actors.get("target"))
        resolution = str(event.outcome.get("resolution", "throw")).replace("_", " ")
        p_on_target = event.probabilities.get("p_on_target")
        p_catch = event.probabilities.get("p_catch")
        roll_on_target = event.rolls.get("on_target")
        roll_catch = event.rolls.get("catch")
        parts = [f"{thrower} vs {target}: {resolution}."]
        if p_on_target is not None and roll_on_target is not None:
            parts.append(f"On-target {float(p_on_target):.2f} (roll {float(roll_on_target):.2f}).")
        if p_catch is not None and roll_catch is not None:
            parts.append(f"Catch {float(p_catch):.2f} (roll {float(roll_catch):.2f}).")
        return " ".join(parts)

    def _replay_prev(self) -> None:
        self._stop_replay()
        self.replay_index = max(0, self.replay_index - 1)
        self._render_replay_frame()

    def _replay_next(self) -> None:
        self._stop_replay()
        self.replay_index = min(max(0, len(self.replay_events) - 1), self.replay_index + 1)
        self._render_replay_frame()

    def _show_replay_final_moment(self) -> None:
        if self.current_record is None:
            return
        winner_id = self.current_record.result.winner_team_id
        setup = self._setup_for_current_record()
        names = {setup.team_a.id: setup.team_a.name, setup.team_b.id: setup.team_b.name}
        winner_name = names.get(winner_id, self.clubs[winner_id].name if winner_id in self.clubs else "Draw")
        result_line = "Draw" if winner_id is None else f"{winner_name} win"
        mvp_id = compute_match_mvp(self.current_stats)
        self.replay_banner_var.set(f"FINAL: {winner_name}")
        mvp_name = self._player_name_for_wire(mvp_id) if mvp_id else "-"
        self.replay_mvp_var.set(f"Match MVP: {mvp_name}")
        if self.replay_canvas is not None:
            width = max(640, int(self.replay_canvas.winfo_width() or self.replay_canvas.cget("width")))
            self.replay_canvas.create_rectangle(70, 70, width - 70, 170, fill=DM_PAPER, outline=DM_BORDER, width=2)
            self.replay_canvas.create_text(width / 2, 105, text=result_line, fill=DM_BRICK, font=("Bahnschrift SemiBold", 28))
            self.replay_canvas.create_text(width / 2, 145, text=f"Match MVP: {mvp_name if mvp_id else 'No selection'}", fill=DM_CHARCOAL, font=("Segoe UI Semibold", 14))

    def show_report(self, match_id: Optional[str]) -> None:
        self._stop_replay()
        if match_id == FRIENDLY_MATCH_ID:
            self.title_var.set("Dodgeball Manager")
            self.context_var.set("Friendly Match Sandbox")
        else:
            self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=3)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Match Report", style="Display.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        text = self._text(frame, font=FONT_MONO)
        text.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)
        text.insert(tk.END, self._report_text(match_id))
        text.configure(state=tk.DISABLED)
        if match_id and match_id != FRIENDLY_MATCH_ID:
            panel = ttk.LabelFrame(frame, text="Player Links", style="Panel.TLabelframe", padding=SPACE_2)
            panel.grid(row=1, column=1, sticky="nsew", padx=(SPACE_2, 0), pady=SPACE_2)
            panel.columnconfigure(0, weight=1)
            panel.rowconfigure(1, weight=1)
            ttk.Label(panel, text="Double-click a performer.", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
            tree = ttk.Treeview(panel, columns=("player", "score"), show="headings", height=10)
            tree.heading("player", text="Player")
            tree.heading("score", text="Score")
            tree.column("player", width=180, stretch=True)
            tree.column("score", width=70, anchor="center")
            tree.grid(row=1, column=0, sticky="nsew", pady=(SPACE_1, 0))
            for player_id, stat in self._report_top_performers(match_id):
                player = self._find_player(player_id)
                tree.insert("", tk.END, iid=player_id, values=(player.name if player else player_id, f"{_score_player(stat):.1f}"))
            ttk.Button(panel, text="Open Profile", command=lambda: self._open_selected_report_player(tree, match_id), style="Secondary.TButton").grid(row=2, column=0, sticky="e", pady=(SPACE_1, 0))
            tree.bind("<Double-1>", lambda _: self._open_selected_report_player(tree, match_id))
        ttk.Button(frame, text="Back", command=lambda: self._close_report(match_id), style="Accent.TButton").grid(row=2, column=0, columnspan=2, sticky="e")

    def _close_report(self, match_id: Optional[str]) -> None:
        if match_id == FRIENDLY_MATCH_ID:
            self.show_splash()
            return
        if self.cursor.state == CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING and match_id == self.cursor.match_id:
            self._acknowledge_report()
        else:
            self.show_league()

    def _report_text(self, match_id: Optional[str]) -> str:
        if match_id is None:
            return "No report is pending."
        if match_id == FRIENDLY_MATCH_ID:
            return self._friendly_report_text()
        row = self._record_for_match(match_id)
        if row is None:
            return f"Match {match_id} has not been found."
        stats = self._stats_for_match(match_id)
        home = self.clubs[row["home_club_id"]]
        away = self.clubs[row["away_club_id"]]
        winner = self.clubs[row["winner_club_id"]].name if row["winner_club_id"] in self.clubs else "Draw"
        mvp_id = compute_match_mvp(stats)
        mvp_line = (
            f"{self._player_name_for_wire(mvp_id)} ({_score_player(stats.get(mvp_id)):.1f})"
            if mvp_id
            else "None"
        )
        turning_point = ""
        if self.current_record and self.current_record.match_id == match_id:
            deltas = per_event_wp_delta(
                self.current_record.result.events,
                home.club_id,
                away.club_id,
                self.current_record.home_active_player_ids,
                self.current_record.away_active_player_ids,
            )
            if deltas:
                turning_index = max(range(len(deltas)), key=lambda i: abs(deltas[i]))
                event = self.current_record.result.events[turning_index]
                turning_point = f"Turning point: tick {event.tick} - {replay_event_label(event)} ({deltas[turning_index]:+.2f} swing)."
        lines = [
            f"{home.name} vs {away.name}",
            f"Winner: {winner}",
            f"Survivors: {home.name} {row['home_survivors']} | {away.name} {row['away_survivors']}",
            f"Match MVP: {mvp_line}",
            turning_point or "Turning point: no high-leverage swing detected.",
            "",
            "Top Performers:",
        ]
        for player_id, stat in sorted(stats.items(), key=lambda item: (-_score_player(item[1]), item[0]))[:6]:
            lines.append(
                f"  {self._player_name_for_wire(player_id):<24} "
                f"score={_score_player(stat):>5.1f} elims={stat.eliminations_by_throw} "
                f"catches={stat.catches_made} dodges={stat.dodges_successful}"
            )
        if self.current_record and self.current_record.match_id == match_id:
            home_team = self._active_team_for_club(home, self.rosters[home.club_id])
            away_team = self._active_team_for_club(away, self.rosters[away.club_id])
            expected_home = pre_match_expected_outcome(home_team, away_team)
            deltas = per_event_wp_delta(
                self.current_record.result.events,
                home.club_id,
                away.club_id,
                self.current_record.home_active_player_ids,
                self.current_record.away_active_player_ids,
            )
            biggest = max(deltas, key=abs) if deltas else 0.0
            lines.extend(["", "Retrospective Leverage:", f"  Home baseline: {expected_home:.2f}", f"  Biggest event swing: {biggest:+.2f}"])
            if row["winner_club_id"] == away.club_id and expected_home >= 0.65:
                lines.append("  UPSET: result beat the retrospective baseline.")
        return "\n".join(lines)

    def _report_top_performers(self, match_id: str) -> List[tuple[str, PlayerMatchStats]]:
        stats = self._stats_for_match(match_id)
        return sorted(stats.items(), key=lambda item: (-_score_player(item[1]), item[0]))[:10]

    def _open_selected_report_player(self, tree: ttk.Treeview, match_id: str) -> None:
        selection = tree.selection()
        if selection:
            self.show_player_profile(selection[0], lambda: self.show_report(match_id))

    def _friendly_report_text(self) -> str:
        if self.current_record is None or self.current_friendly_setup is None:
            return "No friendly report is pending."
        setup = self.current_friendly_setup
        box = self.current_record.result.box_score["teams"]
        winner_id = self.current_record.result.winner_team_id
        names = {setup.team_a.id: setup.team_a.name, setup.team_b.id: setup.team_b.name}
        winner = names.get(winner_id, "Draw")
        mvp_id = compute_match_mvp(self.current_stats)
        mvp_line = f"{self._player_name_for_wire(mvp_id)} ({_score_player(self.current_stats.get(mvp_id)):.1f})" if mvp_id else "None"
        lines = [
            f"{setup.team_a.name} vs {setup.team_b.name}",
            f"Winner: {winner}",
            f"Survivors: {setup.team_a.name} {box[setup.team_a.id]['totals']['living']} | {setup.team_b.name} {box[setup.team_b.id]['totals']['living']}",
            f"Seed: {FRIENDLY_SEED} | Difficulty: {FRIENDLY_DIFFICULTY}",
            f"Match MVP: {mvp_line}",
            "",
            "Top Performers:",
        ]
        for player_id, stat in sorted(self.current_stats.items(), key=lambda item: (-_score_player(item[1]), item[0]))[:6]:
            lines.append(f"  {self._player_name_for_wire(player_id):<24} score={_score_player(stat):>5.1f} elims={stat.eliminations_by_throw} catches={stat.catches_made} dodges={stat.dodges_successful}")
        lines.extend(["", "Friendly match only. Career save, standings, and schedule are unchanged."])
        return "\n".join(lines)

    def _stats_for_match(self, match_id: str) -> Dict[str, PlayerMatchStats]:
        cursor = self.conn.execute("SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,))
        return {
            row["player_id"]: PlayerMatchStats(
                throws_attempted=row["throws_attempted"],
                throws_on_target=row["throws_on_target"],
                eliminations_by_throw=row["eliminations_by_throw"],
                catches_attempted=row["catches_attempted"],
                catches_made=row["catches_made"],
                times_targeted=row["times_targeted"],
                dodges_successful=row["dodges_successful"],
                times_hit=row["times_hit"],
                times_eliminated=row["times_eliminated"],
                revivals_caused=row["revivals_caused"],
                clutch_events=row["clutch_events"],
                elimination_plus_minus=row["elimination_plus_minus"],
                minutes_played=row["minutes_played"],
            )
            for row in cursor.fetchall()
        }

    def _acknowledge_report(self) -> None:
        self._advance_playoffs_if_needed()
        next_week = self._current_week()
        if next_week is None:
            self._finalize_season()
            self.cursor = advance(self.cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
            save_career_state_cursor(self.conn, self.cursor)
            self.conn.commit()
            self.show_season_complete()
        else:
            self.cursor = advance(self.cursor, CareerState.SEASON_ACTIVE_PRE_MATCH, week=next_week, match_id=None)
            save_career_state_cursor(self.conn, self.cursor)
            from .config import DEFAULT_SCOUTING_CONFIG
            from .scouting_center import run_scouting_week_tick

            run_scouting_week_tick(
                self.conn,
                season=self.cursor.season_number or 1,
                current_week=next_week,
                root_seed=stored_root_seed(self.conn),
                config=DEFAULT_SCOUTING_CONFIG,
            )
            self.conn.commit()
            self.show_hub()

    def _recompute_standings(self) -> None:
        if self.season is None:
            return
        recompute_regular_season_standings(self.conn, self.season)
        self.conn.commit()

    def _finalize_season(self) -> None:
        if self.season is None:
            return
        existing_awards = load_awards(self.conn, self.season.season_id)
        if existing_awards:
            update_manager_career_summaries(self.conn, self.season, self.rosters, existing_awards)
            self.conn.commit()
            return
        season_stats = fetch_season_player_stats(self.conn, self.season.season_id)
        player_club_map = {
            row["player_id"]: row["club_id"]
            for row in self.conn.execute(
                "SELECT DISTINCT player_id, club_id FROM player_match_stats WHERE match_id IN (SELECT match_id FROM match_records WHERE season_id = ?)",
                (self.season.season_id,),
            ).fetchall()
        }
        newcomers = frozenset(player.id for roster in self.rosters.values() for player in roster if player.newcomer)
        awards = compute_season_awards(self.season.season_id, season_stats, player_club_map, newcomers)
        save_awards(self.conn, awards)
        matches_by_player = {
            row["player_id"]: row["matches"]
            for row in self.conn.execute(
                "SELECT player_id, COUNT(*) AS matches FROM player_match_stats WHERE match_id IN (SELECT match_id FROM match_records WHERE season_id = ?) GROUP BY player_id",
                (self.season.season_id,),
            )
        }
        save_player_season_stats(self.conn, self.season.season_id, season_stats, player_club_map, matches_by_player, newcomers)
        update_manager_career_summaries(self.conn, self.season, self.rosters, awards)
        self.conn.commit()

    def show_season_complete(self) -> None:
        if self.season is not None:
            self._finalize_season()
            root_seed = stored_root_seed(self.conn)
            self.rosters = initialize_manager_offseason(self.conn, self.season, self.clubs, self.rosters, root_seed)
        if self.cursor.state != CareerState.SEASON_COMPLETE_OFFSEASON_BEAT:
            self.cursor = CareerStateCursor(
                state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
                season_number=self.cursor.season_number or 1,
                week=0,
                offseason_beat_index=0,
            )
            save_career_state_cursor(self.conn, self.cursor)
            self.conn.commit()
        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        standings = _standings_with_all_clubs(load_standings(self.conn, self.season.season_id), self.clubs) if self.season else []
        awards = load_awards(self.conn, self.season.season_id) if self.season else []
        beat_index = clamp_offseason_beat_index(self.cursor.offseason_beat_index)
        if beat_index != self.cursor.offseason_beat_index:
            self.cursor = replace(self.cursor, offseason_beat_index=beat_index)
            save_career_state_cursor(self.conn, self.cursor)
            self.conn.commit()
        next_preview = self._next_season_preview() if beat_index >= len(OFFSEASON_CEREMONY_BEATS) - 1 else None
        try:
            development_rows = load_offseason_state_rows(self.conn, "offseason_development_json")
            retirement_rows = load_offseason_state_rows(self.conn, "offseason_retirements_json")
        except CorruptSaveError as exc:
            self.save_error = str(exc)
            self.show_save_recovery()
            return
        draft_pool = load_free_agents(self.conn)
        signed_player_id = get_state(self.conn, "offseason_draft_signed_player_id", "") or ""
        if OFFSEASON_CEREMONY_BEATS[beat_index] == "recruitment":
            self.show_offseason_draft_beat()
            return
        beat = build_offseason_ceremony_beat(
            beat_index,
            self.season,
            self.clubs,
            self.rosters,
            standings,
            awards,
            self.player_club_id,
            next_preview,
            development_rows,
            retirement_rows,
            draft_pool,
            signed_player_id,
            season_outcome=load_season_outcome(self.conn, self.season.season_id) if self.season else None,
            records_payload_json=get_state(self.conn, "offseason_records_ratified_json"),
            hof_payload_json=get_state(self.conn, "offseason_hof_inducted_json"),
            rookie_preview_payload_json=get_state(self.conn, "offseason_rookie_preview_json"),
        )
        progress = f"{min(self.cursor.offseason_beat_index + 1, len(OFFSEASON_CEREMONY_BEATS))} of {len(OFFSEASON_CEREMONY_BEATS)}"
        ttk.Label(frame, text=f"Off-season Ceremony: {beat.title}", style="Display.TLabel").grid(row=0, column=0, sticky="w")
        text = self._text(frame, font=FONT_MONO)
        text.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)
        text.insert(tk.END, f"{progress}\n\n{beat.body}\n")
        text.configure(state=tk.DISABLED)
        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, sticky="e")
        if beat.key == "schedule_reveal":
            ttk.Button(actions, text="Begin Next Season", command=self._begin_next_season, style="Accent.TButton").pack(side=tk.LEFT)
        elif beat.key == "recruitment":
            ttk.Button(actions, text="Sign Best Rookie", command=self._sign_best_rookie_and_refresh, style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
            ttk.Button(actions, text="Continue", command=self._advance_offseason_beat, style="Accent.TButton").pack(side=tk.LEFT)
        else:
            ttk.Button(actions, text="Continue", command=self._advance_offseason_beat, style="Accent.TButton").pack(side=tk.LEFT)

    def show_offseason_draft_beat(self) -> None:
        from .persistence import load_prospect_pool

        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        season_num = self.cursor.season_number or 1
        class_year = season_num
        ttk.Label(frame, text="Recruitment Day", style="Display.TLabel").grid(row=0, column=0, sticky="w")

        rows = [
            row
            for row in build_prospect_board_rows(self.conn, class_year)
            if not _is_already_signed(self.conn, class_year, row["player_id"])
        ]
        board_frame = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        board_frame.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)
        board_frame.columnconfigure(0, weight=1)
        board_frame.rowconfigure(0, weight=1)
        self._prospect_board_tree = self._render_prospect_board(board_frame, rows)

        controls = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        sweep = build_trajectory_reveal_sweep(self.conn, class_year)
        if sweep:
            ttk.Button(
                controls,
                text=f"Reveal Trajectories ({len(sweep)})",
                command=lambda: self._show_trajectory_reveal_sweep(sweep),
                style="Secondary.TButton",
            ).grid(row=0, column=0, sticky="w", pady=(0, SPACE_1))

        pool = [
            prospect
            for prospect in load_prospect_pool(self.conn, class_year)
            if not _is_already_signed(self.conn, class_year, prospect.player_id)
        ]
        target_var = tk.StringVar()
        options = [f"{prospect.player_id} | {prospect.name}" for prospect in pool]
        ttk.Combobox(controls, textvariable=target_var, values=options, state="readonly", width=54).grid(row=1, column=0, sticky="w")
        ttk.Button(
            controls,
            text="Sign Selected",
            command=lambda: self._sign_selected_prospect(target_var, class_year),
            style="Accent.TButton",
        ).grid(row=1, column=1, sticky="w", padx=SPACE_1)
        if has_accuracy_reckoning_data(self.conn, season_num):
            ttk.Button(
                controls,
                text="Accuracy Reckoning",
                command=lambda: self._show_accuracy_reckoning(season_num, class_year),
                style="Secondary.TButton",
            ).grid(row=1, column=2, sticky="w", padx=SPACE_1)
        ttk.Button(
            controls,
            text="Continue",
            command=self._advance_offseason_beat,
            style="Accent.TButton",
        ).grid(row=1, column=3, sticky="e", padx=(SPACE_2, 0))

    def _sign_selected_prospect(self, target_var: tk.StringVar, class_year: int) -> None:
        from .persistence import load_prospect_pool

        selected = target_var.get().split(" | ", 1)[0] if target_var.get() else None
        if not selected or not self.player_club_id:
            return
        prospect = next(
            (item for item in load_prospect_pool(self.conn, class_year) if item.player_id == selected),
            None,
        )
        if prospect is None:
            return
        root_seed = stored_root_seed(self.conn)
        result = conduct_recruitment_round(
            self.conn,
            root_seed=root_seed,
            season_id=self.season.season_id if self.season else f"season_{class_year}",
            class_year=class_year,
            user_club_id=self.player_club_id,
            selected_player_id=prospect.player_id,
        )
        user_signing = next(
            (signing for signing in result.signings if signing.club_id == self.player_club_id),
            None,
        )
        set_state(self.conn, "offseason_draft_signed_player_id", user_signing.player_id if user_signing else "")
        self.conn.commit()
        self._load_state()
        self.show_offseason_draft_beat()

    def _show_trajectory_reveal_sweep(self, sweep: List[Dict[str, Any]]) -> None:
        win = tk.Toplevel(self.master)
        win.title("Trajectory Reveals")
        win.configure(bg=DM_PAPER)
        for idx, entry in enumerate(sweep):
            row = ttk.Frame(win, style="Surface.TFrame", padding=SPACE_2, borderwidth=1, relief="solid")
            row.grid(row=idx, column=0, sticky="ew", padx=12, pady=4)
            color = DM_BORDER if entry["display_weight"] == "elevated" else DM_MUTED_CHARCOAL
            tk.Label(row, text=entry["name"], bg=DM_PAPER, fg=DM_BORDER, font=FONT_BODY).grid(row=0, column=0, sticky="w")
            tk.Label(row, text=entry["trajectory"], bg=DM_PAPER, fg=color, font=FONT_BODY).grid(row=0, column=1, sticky="e", padx=(20, 0))
        ttk.Button(win, text="Close", command=win.destroy).grid(row=len(sweep), column=0, sticky="e", padx=12, pady=12)

    def _show_accuracy_reckoning(self, season_num: int, class_year: int) -> None:
        summary = build_accuracy_reckoning(self.conn, season_num, class_year)
        win = tk.Toplevel(self.master)
        win.title("Accuracy Reckoning")
        win.configure(bg=DM_PAPER)
        if not summary:
            ttk.Label(
                win,
                text="No scout accuracy data is available for this season yet.",
                style="Muted.TLabel",
            ).grid(row=0, column=0, sticky="w", padx=12, pady=12)
            ttk.Button(win, text="Close", command=win.destroy).grid(row=1, column=0, sticky="e", padx=12, pady=12)
            return
        for idx, scout_summary in enumerate(summary):
            row = ttk.Frame(win, style="Surface.TFrame", padding=SPACE_2, borderwidth=1, relief="solid")
            row.grid(row=idx, column=0, sticky="ew", padx=12, pady=4)
            ttk.Label(row, text=scout_summary["scout_id"].upper(), style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
            for offset, item in enumerate(scout_summary["rows"], 1):
                marker = "OK" if item["within_5"] else "MISS"
                ttk.Label(
                    row,
                    text=f"{item['player_name']}: predicted {item['predicted_ovr_band']} actual {item['actual_ovr']} {marker}",
                    style="Muted.TLabel",
                ).grid(row=offset, column=0, sticky="w")
        ttk.Button(win, text="Close", command=win.destroy).grid(row=len(summary), column=0, sticky="e", padx=12, pady=12)

    def _advance_offseason_beat(self) -> None:
        beat_index = clamp_offseason_beat_index(self.cursor.offseason_beat_index)
        if (
            OFFSEASON_CEREMONY_BEATS[beat_index] == "recruitment"
            and not (get_state(self.conn, "offseason_draft_signed_player_id", "") or "")
        ):
            self._sign_best_rookie()
        next_index = min(beat_index + 1, len(OFFSEASON_CEREMONY_BEATS) - 1)
        self.cursor = advance(
            self.cursor,
            CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
            offseason_beat_index=next_index,
            week=0,
            match_id=None,
        )
        save_career_state_cursor(self.conn, self.cursor)
        self.conn.commit()
        self.show_season_complete()

    def _sign_best_rookie_and_refresh(self) -> None:
        self._sign_best_rookie()
        self.show_season_complete()

    def _sign_best_rookie(self) -> Optional[Player]:
        if not self.player_club_id or get_state(self.conn, "offseason_draft_signed_player_id", ""):
            return None
        from .persistence import load_prospect_pool

        class_year = self.cursor.season_number or 1
        available_prospects = [
            prospect
            for prospect in load_prospect_pool(self.conn, class_year=class_year)
            if not _is_already_signed(self.conn, class_year, prospect.player_id)
        ]
        if available_prospects:
            selected_prospect = sorted(
                available_prospects,
                key=lambda prospect: (-prospect.true_overall(), prospect.player_id),
            )[0]
            signed_prospect = sign_prospect_to_club(
                self.conn,
                selected_prospect,
                self.player_club_id,
                class_year,
            )
            self.rosters = load_all_rosters(self.conn)
            set_state(self.conn, "offseason_draft_signed_player_id", signed_prospect.id)
            return signed_prospect
        free_agents = load_free_agents(self.conn)
        if not free_agents:
            return None
        selected = sorted(free_agents, key=lambda player: (-player.overall(), player.id))[0]
        remaining = [player for player in free_agents if player.id != selected.id]
        signed = replace(selected, club_id=self.player_club_id, newcomer=True)
        roster = list(self.rosters.get(self.player_club_id, []))
        roster.append(signed)
        self.rosters[self.player_club_id] = roster
        save_club(self.conn, self.clubs[self.player_club_id], roster)
        save_lineup_default(self.conn, self.player_club_id, [player.id for player in roster])
        save_free_agents(self.conn, remaining, f"season_{(self.cursor.season_number or 1) + 1}")
        set_state(self.conn, "offseason_draft_signed_player_id", signed.id)
        self.conn.commit()
        return signed

    def _next_season_preview(self) -> Optional[Season]:
        if self.season is None:
            return None
        next_number = (self.cursor.season_number or 1) + 1
        root_seed = stored_root_seed(self.conn)
        return create_next_manager_season(
            self.clubs,
            root_seed,
            next_number,
            self.season.year + 1,
        )

    def _begin_next_season(self) -> None:
        next_season = self._next_season_preview()
        if next_season is None:
            return
        prior_season_num = self.cursor.season_number or 1
        apply_scouting_carry_forward_at_transition(self.conn, prior_class_year=prior_season_num)
        save_season(self.conn, next_season)
        save_season_format(self.conn, next_season.season_id, PLAYOFF_FORMAT)
        set_state(self.conn, "active_season_id", next_season.season_id)
        self.cursor = CareerStateCursor(
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            season_number=(self.cursor.season_number or 1) + 1,
            week=1,
            offseason_beat_index=0,
            match_id=None,
        )
        save_career_state_cursor(self.conn, self.cursor)
        from .config import DEFAULT_SCOUTING_CONFIG
        from .scouting_center import initialize_scouting_for_career

        root_seed = stored_root_seed(self.conn)
        initialize_scouting_for_career(
            self.conn,
            root_seed=root_seed,
            config=DEFAULT_SCOUTING_CONFIG,
            class_year=self.cursor.season_number or 1,
        )
        self.conn.commit()
        self._load_state()
        self.show_hub()

    def show_scouting_center(self) -> None:
        from .config import DEFAULT_SCOUTING_CONFIG
        from .scouting_center import initialize_scouting_for_career

        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        from .ui_components import PageHeader
        PageHeader(frame, "Scouting").grid(row=0, column=0, sticky="w", pady=(0, SPACE_2))
        if self.season is None:
            return

        season_num = self.cursor.season_number or 1
        root_seed = stored_root_seed(self.conn, default=20260426)
        initialize_scouting_for_career(
            self.conn,
            root_seed=root_seed,
            config=DEFAULT_SCOUTING_CONFIG,
            class_year=season_num,
        )

        strip_frame = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        strip_frame.grid(row=1, column=0, sticky="ew", pady=(SPACE_1, SPACE_2))
        for index in range(3):
            strip_frame.columnconfigure(index, weight=1)
        _scout_mode_labels = {"AUTO": "Auto", "MANUAL": "Manual"}
        _scout_priority_labels = {"TOP_PUBLIC_OVR": "Best OVR", "SPECIALTY_FIT": "Specialty Fit", "USER_PINNED": "Pinned"}
        _prospect_names = {
            row["player_id"]: (row["name"] or row["player_id"])
            for row in self.conn.execute("SELECT player_id, name FROM prospect_pool")
        }
        for col_idx, card_data in enumerate(build_scout_strip_data(self.conn, season=season_num)):
            card = ttk.Frame(strip_frame, style="Surface.TFrame", padding=SPACE_2, borderwidth=1, relief="solid")
            card.grid(row=0, column=col_idx, sticky="ew", padx=(0, SPACE_1) if col_idx < 2 else (0, 0))
            ttk.Label(card, text=card_data["name"].upper(), style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(card, text=card_data["specialty_blurb"], style="Muted.TLabel", wraplength=240).grid(row=1, column=0, sticky="w")
            _pid = card_data["assignment_player_id"]
            assignment = _prospect_names.get(_pid, _pid) if _pid else "Available"
            ttk.Label(card, text=f"Assignment: {assignment}", style="CardCaption.TLabel").grid(row=2, column=0, sticky="w", pady=(SPACE_1, 0))
            _mode = _scout_mode_labels.get(card_data["mode"], card_data["mode"].title())
            _pri = _scout_priority_labels.get(card_data["priority"], card_data["priority"].replace("_", " ").title())
            ttk.Label(card, text=f"{_mode} | {_pri}", style="CardCaption.TLabel").grid(row=3, column=0, sticky="w")
            ttk.Button(
                card,
                text="Manage...",
                command=lambda scout_id=card_data["scout_id"]: self._open_scout_manage_dialog(scout_id),
                style="Secondary.TButton",
            ).grid(row=4, column=0, sticky="ew", pady=(SPACE_1, 0))

        rows = build_prospect_board_rows(self.conn, class_year=season_num)
        board_frame = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        board_frame.grid(row=2, column=0, sticky="nsew", pady=(0, SPACE_2))
        board_frame.columnconfigure(0, weight=1)
        board_frame.rowconfigure(1, weight=1)
        controls = ttk.Frame(board_frame, style="Surface.TFrame")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_1))
        ttk.Button(controls, text="Worth a Look", command=lambda: self._refresh_prospect_board(rows, "worth_a_look"), style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(controls, text="OVR Desc", command=lambda: self._refresh_prospect_board(rows, "ovr_desc"), style="Secondary.TButton").pack(side=tk.LEFT)
        self._prospect_board_tree = self._render_prospect_board(board_frame, rows)

        ticker_frame = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        ticker_frame.grid(row=3, column=0, sticky="ew")
        ttk.Label(ticker_frame, text="Reveal Ticker", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        for idx, item in enumerate(build_reveal_ticker_items(self.conn, season=season_num)[-8:], 1):
            ttk.Label(ticker_frame, text=item["text"], style="Muted.TLabel").grid(row=idx, column=0, sticky="w")

    def _render_prospect_board(self, parent: ttk.Frame, rows: List[Dict[str, Any]]) -> ttk.Treeview:
        cols = ("name", "age", "archetype", "ovr_band", "ratings_tier", "ceiling", "traits", "assigned")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)
        for key, label, width in (
            ("name", "Prospect", 180),
            ("age", "Age", 48),
            ("archetype", "Archetype", 130),
            ("ovr_band", "OVR", 72),
            ("ratings_tier", "Ratings", 92),
            ("ceiling", "Ceiling", 110),
            ("traits", "Traits", 160),
            ("assigned", "Scout", 80),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="w", stretch=key in {"name", "traits"})
        tree.grid(row=1, column=0, sticky="nsew")
        tree.bind("<Double-1>", lambda _event: self._on_prospect_row_double_click(tree))
        self._insert_prospect_board_rows(tree, rows)
        return tree

    def _insert_prospect_board_rows(self, tree: ttk.Treeview, rows: List[Dict[str, Any]]) -> None:
        for row in rows:
            tree.insert(
                "",
                tk.END,
                iid=row["player_id"],
                values=(
                    row["name"],
                    row["age"],
                    row["archetype_guess"],
                    f"{row['ovr_band'][0]}-{row['ovr_band'][1]}",
                    row["ratings_tier"],
                    row["ceiling_label"] or "?",
                    ", ".join(row["revealed_traits"]) if row["revealed_traits"] else "?",
                    row["assigned_to_scout_id"] or "-",
                ),
            )

    def _refresh_prospect_board(self, rows: List[Dict[str, Any]], sort_mode: str) -> None:
        tree = getattr(self, "_prospect_board_tree", None)
        if tree is None:
            return
        sorted_rows = sort_rows_worth_a_look(rows) if sort_mode == "worth_a_look" else sorted(rows, key=lambda row: row["ovr_mid"], reverse=True)
        tree.delete(*tree.get_children())
        self._insert_prospect_board_rows(tree, sorted_rows)

    def _on_prospect_row_double_click(self, tree: ttk.Treeview) -> None:
        selection = tree.selection()
        if selection:
            self.show_player_profile(selection[0], self.show_scouting_center)

    def _open_scout_manage_dialog(self, scout_id: str) -> None:
        from .persistence import (
            load_all_scout_assignments,
            load_prospect_pool,
            load_scout_assignment,
            load_scout_strategy,
            load_scouts,
            save_scout_assignment,
            save_scout_strategy,
        )
        from .scouting_center import ScoutAssignment, ScoutStrategyState

        scouts = {scout.scout_id: scout for scout in load_scouts(self.conn)}
        scout = scouts.get(scout_id)
        if scout is None:
            return
        current_assignment = load_scout_assignment(self.conn, scout_id)
        current_strategy = load_scout_strategy(self.conn, scout_id)
        season_num = self.cursor.season_number or 1
        pool = load_prospect_pool(self.conn, class_year=season_num)

        win = tk.Toplevel(self.master)
        win.title(f"Manage {scout.name}")
        win.configure(bg=DM_PAPER)
        win.columnconfigure(1, weight=1)

        ttk.Label(win, text=scout.name, style="Display.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4))
        ttk.Label(win, text=f"Specialty: {', '.join(scout.archetype_affinities) or 'Generalist'}", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", padx=12)
        ttk.Label(win, text=f"Weakness: {scout.archetype_weakness or 'none'}", style="Muted.TLabel").grid(row=2, column=0, columnspan=2, sticky="w", padx=12)

        mode_var = tk.StringVar(value=current_strategy.mode if current_strategy else "MANUAL")
        ttk.Label(win, text="Mode", style="CardCaption.TLabel").grid(row=3, column=0, sticky="w", padx=12, pady=(8, 0))
        ttk.Radiobutton(win, text="Manual", value="MANUAL", variable=mode_var).grid(row=3, column=1, sticky="w")
        ttk.Radiobutton(win, text="Auto", value="AUTO", variable=mode_var).grid(row=4, column=1, sticky="w")

        priority_var = tk.StringVar(value=current_strategy.priority if current_strategy else "TOP_PUBLIC_OVR")
        ttk.Label(win, text="Auto priority", style="CardCaption.TLabel").grid(row=5, column=0, sticky="w", padx=12, pady=(8, 0))
        ttk.Radiobutton(win, text="Top public OVR", value="TOP_PUBLIC_OVR", variable=priority_var).grid(row=5, column=1, sticky="w")
        ttk.Radiobutton(win, text="Specialty fit", value="SPECIALTY_FIT", variable=priority_var).grid(row=6, column=1, sticky="w")

        ttk.Label(win, text="Manual assignment", style="CardCaption.TLabel").grid(row=7, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))
        other_assignments = {
            assignment.player_id
            for sid, assignment in load_all_scout_assignments(self.conn).items()
            if sid != scout_id and assignment.player_id
        }
        values = [""]
        current_value = ""
        for prospect in pool:
            if prospect.player_id in other_assignments:
                continue
            low, high = prospect.public_ratings_band["ovr"]
            label = f"{prospect.player_id} | {prospect.name} ({prospect.public_archetype_guess}, est OVR {(low + high) // 2})"
            values.append(label)
            if current_assignment and current_assignment.player_id == prospect.player_id:
                current_value = label
        target_var = tk.StringVar(value=current_value)
        combo = ttk.Combobox(win, textvariable=target_var, values=values, state="readonly", width=58)
        combo.grid(row=8, column=0, columnspan=2, sticky="ew", padx=12, pady=4)

        def save_and_close() -> None:
            selection = target_var.get()
            selected_player_id = selection.split(" | ", 1)[0] if selection else None
            save_scout_assignment(
                self.conn,
                ScoutAssignment(scout_id, selected_player_id or None, self.cursor.week or 1),
            )
            save_scout_strategy(
                self.conn,
                ScoutStrategyState(scout_id, mode_var.get(), priority_var.get(), (), ()),
            )
            self.conn.commit()
            win.destroy()
            self.show_scouting_center()

        ttk.Button(win, text="Save", command=save_and_close, style="Accent.TButton").grid(
            row=9, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 12)
        )

    def show_roster(self) -> None:
        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        from .ui_components import PageHeader
        PageHeader(frame, "Roster").grid(row=0, column=0, sticky="w", pady=(0, SPACE_2))
        tree = ttk.Treeview(frame, columns=("name", "role", "ovr", "age", "status"), show="headings")
        for key, label in (("name", "Player"), ("role", "Role"), ("ovr", "OVR"), ("age", "Age"), ("status", "Status")):
            tree.heading(key, text=label)
            tree.column(key, anchor="center", stretch=key == "name")
        tree.tag_configure("bench_sep", background=DM_OFF_WHITE_LINE, foreground=DM_MUTED_CHARCOAL)
        tree.tag_configure("bench", foreground=DM_MUTED_CHARCOAL)
        tree.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)

        club_id = self.player_club_id or ""
        roster = self.rosters.get(club_id, [])
        default = load_lineup_default(self.conn, club_id)
        ordered_ids = LineupResolver().resolve(roster, default, None)
        by_id = {p.id: p for p in roster}

        starters = [by_id[pid] for pid in ordered_ids[:STARTERS_COUNT] if pid in by_id]
        bench = [by_id[pid] for pid in ordered_ids[STARTERS_COUNT:] if pid in by_id]

        for player in starters:
            status = "ROOKIE" if player.newcomer else "STARTER"
            tree.insert("", tk.END, iid=player.id,
                        values=(player.name, player_role(player), f"{player.overall():.1f}", player.age, status))

        if bench:
            tree.insert("", tk.END, iid="__bench_sep__",
                        values=("── Bench ──", "", "", "", ""),
                        tags=("bench_sep",))
            for player in bench:
                status = "ROOKIE" if player.newcomer else "BENCH"
                tree.insert("", tk.END, iid=f"bench_{player.id}",
                            values=(player.name, player_role(player), f"{player.overall():.1f}", player.age, status),
                            tags=("bench",))

        def _on_double_click(_event: Any) -> None:
            sel = tree.selection()
            if not sel or sel[0] in ("__bench_sep__",):
                return
            pid = sel[0][6:] if sel[0].startswith("bench_") else sel[0]
            self.show_player_profile(pid, self.show_roster)

        tree.bind("<Double-1>", _on_double_click)

        btn_frame = ttk.Frame(frame, style="Surface.TFrame")
        btn_frame.grid(row=2, column=0, sticky="w", pady=(0, SPACE_2))

        def _move(delta: int) -> None:
            sel = tree.selection()
            if not sel or sel[0] == "__bench_sep__":
                return
            iid = sel[0]
            pid = iid[6:] if iid.startswith("bench_") else iid
            current_order = list(ordered_ids)
            if pid not in current_order:
                return
            idx = current_order.index(pid)
            new_idx = idx + delta
            if new_idx < 0 or new_idx >= len(current_order):
                return
            current_order[idx], current_order[new_idx] = current_order[new_idx], current_order[idx]
            save_lineup_default(self.conn, club_id, current_order)
            self.conn.commit()
            self.show_roster()

        def _sort_by_ovr() -> None:
            sorted_ids = [p.id for p in sorted(roster, key=lambda p: p.overall(), reverse=True)]
            save_lineup_default(self.conn, club_id, sorted_ids)
            self.conn.commit()
            self.show_roster()

        ttk.Button(btn_frame, text="▲ Move Up", command=lambda: _move(-1), style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(btn_frame, text="▼ Move Down", command=lambda: _move(1), style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
        ttk.Button(btn_frame, text="Sort by OVR", command=_sort_by_ovr, style="Secondary.TButton").pack(side=tk.LEFT)

    def _open_selected_roster_player(self, tree: ttk.Treeview) -> None:
        selection = tree.selection()
        if selection:
            self.show_player_profile(selection[0], self.show_roster)

    def show_player_profile(self, player_id: str, back_command: Optional[Callable[[], None]] = None) -> None:
        self._refresh_header()
        season_num = self.cursor.season_number or 1
        from .persistence import load_prospect_pool

        if any(prospect.player_id == player_id for prospect in load_prospect_pool(self.conn, season_num)):
            self._render_fuzzy_profile(player_id, season_num, back_command or self.show_scouting_center)
            return

        player = self._find_player(player_id)
        if player is None:
            return
        if back_command is None:
            back_command = self.show_roster
        club_id = player.club_id or self._club_id_for_player(player_id)
        club_name = self.clubs[club_id].name if club_id in self.clubs else (club_id or "Free Agent")
        season_stats = fetch_season_player_stats(self.conn, self.season.season_id).get(player_id) if self.season else None
        details = build_player_profile_details(
            player=player,
            club_name=club_name,
            season_stats=season_stats,
            matches_played=self._matches_played_for_player(player_id),
            career_summary=fetch_player_career_summary(self.conn, player_id),
        )
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text=details.title, style="Display.TLabel").grid(row=0, column=0, sticky="w")
        text = self._text(frame, font=FONT_MONO)
        text.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)
        text.insert(tk.END, details.text)
        text.configure(state=tk.DISABLED)
        ttk.Button(frame, text="Back", command=back_command, style="Accent.TButton").grid(row=2, column=0, sticky="e")

    def _render_fuzzy_profile(
        self,
        player_id: str,
        season_num: int,
        back_command: Callable[[], None],
    ) -> None:
        from .ui_components import UncertaintyBar, make_badge

        details = build_fuzzy_profile_details(self.conn, season_num, player_id)
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Prospect Profile", style="Display.TLabel").grid(row=0, column=0, sticky="w")

        header = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        header.grid(row=1, column=0, sticky="ew", pady=(SPACE_1, SPACE_2))
        tk.Label(
            header,
            text=details["name"].upper(),
            bg=DM_MUTED_CHARCOAL,
            fg=DM_PAPER,
            font=FONT_BODY,
            padx=14,
            pady=8,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=f"Age {details['age']} | {details['hometown']} | {details['archetype_label']}",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))

        ratings_frame = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        ratings_frame.grid(row=2, column=0, sticky="ew", pady=(0, SPACE_2))
        ratings_frame.columnconfigure(0, weight=1)
        ttk.Label(ratings_frame, text="Ratings", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        for idx, row in enumerate(details["rating_rows"], 1):
            bar = UncertaintyBar(ratings_frame, label=row["rating_name"].upper())
            bar.grid(row=idx, column=0, sticky="ew", pady=2)
            ratings_frame.update_idletasks()
            bar.set(row["midpoint"], row["tier"])

        traits_frame = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        traits_frame.grid(row=3, column=0, sticky="ew", pady=(0, SPACE_2))
        ttk.Label(traits_frame, text="Traits", style="SectionHeader.TLabel").grid(row=0, column=0, sticky="w")
        if details["trait_badges"]:
            for idx, badge_text in enumerate(details["trait_badges"]):
                make_badge(traits_frame, badge_text).grid(row=1, column=idx, sticky="w", padx=(0, SPACE_1), pady=(SPACE_1, 0))
        else:
            ttk.Label(traits_frame, text="No scouting yet", style="Muted.TLabel").grid(row=1, column=0, sticky="w")

        extras = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_2)
        extras.grid(row=4, column=0, sticky="ew")
        ttk.Label(extras, text=f"Ceiling: {details['ceiling_label']}", style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(extras, text=f"Trajectory: {details['trajectory_label']}", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(SPACE_1, 0))

        ttk.Button(frame, text="Back", command=back_command, style="Accent.TButton").grid(row=5, column=0, sticky="e", pady=SPACE_2)

    def _find_player(self, player_id: str) -> Optional[Player]:
        for roster in self.rosters.values():
            for player in roster:
                if player.id == player_id:
                    return player
        setup = getattr(self, "current_friendly_setup", None)
        if setup is not None:
            for team in (setup.team_a, setup.team_b):
                for player in team.players:
                    if player.id == player_id:
                        return player
        return None

    def _player_name_for_wire(self, player_id: Optional[str]) -> str:
        if not player_id:
            return ""
        player = self._find_player(player_id)
        if player:
            return player.name
        if has_unresolved_token(player_id):
            return "Unknown Player"
        return player_id

    def _club_id_for_player(self, player_id: str) -> Optional[str]:
        for club_id, roster in self.rosters.items():
            if any(player.id == player_id for player in roster):
                return club_id
        return None

    def _matches_played_for_player(self, player_id: str) -> int:
        if self.season is None:
            return 0
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS matches
            FROM player_match_stats
            WHERE player_id = ?
              AND match_id IN (SELECT match_id FROM match_records WHERE season_id = ?)
            """,
            (player_id, self.season.season_id),
        ).fetchone()
        return int(row["matches"] if row else 0)

    def show_tactics(self) -> None:
        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        from .ui_components import PageHeader
        PageHeader(frame, "Tactics").grid(row=0, column=0, sticky="w", pady=(0, SPACE_2))
        club = self.player_club
        if club is None:
            return
        policy = club.coach_policy.as_dict()
        for index, key in enumerate(POLICY_KEYS, 1):
            row = ttk.Frame(frame, style="Surface.TFrame", padding=SPACE_1)
            row.grid(row=index, column=0, sticky="ew", pady=4)
            row.columnconfigure(1, weight=1)
            ttk.Label(row, text=key.replace("_", " ").title(), style="CardValue.TLabel").grid(row=0, column=0, sticky="w")
            bar = ttk.Progressbar(row, maximum=1.0, value=policy[key])
            bar.grid(row=0, column=1, sticky="ew", padx=SPACE_2)
            ttk.Label(row, text=policy_effect(key, policy[key]), style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w")

    def show_league(self) -> None:
        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        from .ui_components import PageHeader
        PageHeader(frame, "League").grid(row=0, column=0, sticky="w", pady=(0, SPACE_2))
        notebook = ttk.Notebook(frame)
        notebook.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)
        standings = ttk.Frame(notebook, padding=SPACE_2)
        schedule = ttk.Frame(notebook, padding=SPACE_2)
        wire = ttk.Frame(notebook, padding=SPACE_2)
        for tab in (standings, schedule, wire):
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(0, weight=1)
        notebook.add(standings, text="Standings")
        notebook.add(schedule, text="Schedule")
        notebook.add(wire, text="Wire")
        self._fill_league_standings(standings)
        self._fill_schedule(schedule)
        self._fill_wire(wire)

    def _fill_league_standings(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        table = ttk.LabelFrame(parent, text="Table", style="Panel.TLabelframe", padding=SPACE_2)
        table.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE_2))
        self._fill_standings_tree(table)

        leaders_panel = ttk.LabelFrame(parent, text="League Leaders", style="Panel.TLabelframe", padding=SPACE_2)
        leaders_panel.grid(row=0, column=1, sticky="nsew")
        leaders_panel.columnconfigure(0, weight=1)
        leaders_panel.rowconfigure(1, weight=1)
        ttk.Label(leaders_panel, text="Double-click a leader for the player profile.", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        tree = ttk.Treeview(leaders_panel, columns=("category", "player", "value", "club"), show="headings")
        for key, label, width in (
            ("category", "Category", 120),
            ("player", "Player", 170),
            ("value", "Value", 70),
            ("club", "Club", 150),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="center", stretch=key in ("player", "club"))
        tree.grid(row=1, column=0, sticky="nsew", pady=(SPACE_1, 0))
        self._fill_league_leaders_tree(tree)
        actions = ttk.Frame(leaders_panel)
        actions.grid(row=2, column=0, sticky="e", pady=(SPACE_1, 0))
        ttk.Button(actions, text="Open Profile", command=lambda: self._open_selected_league_leader(tree), style="Secondary.TButton").pack(side=tk.LEFT)
        tree.bind("<Double-1>", lambda _: self._open_selected_league_leader(tree))

    def _fill_schedule(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        ttk.Label(parent, text="Double-click a played match for its report; double-click an open match for opponent context.", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        tree = ttk.Treeview(parent, columns=("week", "status", "home", "away", "you"), show="headings")
        for key, label, width in (
            ("week", "Week", 70),
            ("status", "Status", 90),
            ("home", "Home", 220),
            ("away", "Away", 220),
            ("you", "Your Match", 90),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="center", stretch=key in ("home", "away"))
        tree.grid(row=1, column=0, sticky="nsew", pady=(SPACE_1, 0))
        tree.tag_configure("user", background=DM_OFF_WHITE_LINE)
        completed = load_completed_match_ids(self.conn, self.season.season_id) if self.season else set()
        if self.season:
            for row in build_schedule_rows(self.season, completed, self.player_club_id):
                tree.insert(
                    "",
                    tk.END,
                    iid=row.match_id,
                    values=(
                        row.week,
                        row.status.upper(),
                        self.clubs[row.home_club_id].name,
                        self.clubs[row.away_club_id].name,
                        "YES" if row.is_user_match else "",
                    ),
                    tags=("user",) if row.is_user_match else (),
                )
        tree.bind("<Double-1>", lambda _: self._open_selected_schedule_match(tree))

    def _fill_wire(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        tree = ttk.Treeview(parent, columns=("tag", "item"), show="headings")
        tree.heading("tag", text="Tag")
        tree.heading("item", text="Wire")
        tree.column("tag", width=110, anchor="center")
        tree.column("item", width=720, stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        self.wire_item_targets: Dict[str, WireItem] = {}
        for index, item in enumerate(self._wire_items()):
            iid = item.match_id or item.player_id or f"wire_{index}"
            if iid in self.wire_item_targets:
                iid = f"{iid}_{index}"
            self.wire_item_targets[iid] = item
            tree.insert("", tk.END, iid=iid, values=(item.tag, item.text))
        tree.bind("<Double-1>", lambda _: self._open_selected_wire_item(tree))

    def _league_leaders_text(self) -> str:
        if self.season is None:
            return "No season loaded."
        leaders = build_league_leaders(
            fetch_season_player_stats(self.conn, self.season.season_id),
            self._player_club_map(),
        )
        if not any(leaders.values()):
            return "Leaders appear once matches are played."
        lines: List[str] = []
        for category, rows in leaders.items():
            lines.append(category)
            if not rows:
                lines.append("  -")
            for leader in rows:
                club_name = self.clubs[leader.club_id].name if leader.club_id in self.clubs else leader.club_id
                marker = " *" if leader.club_id == self.player_club_id else ""
                lines.append(f"  {leader.player_id:<24} {leader.value:>5.1f} {club_name}{marker}")
            lines.append("")
        return "\n".join(lines).strip()

    def _fill_league_leaders_tree(self, tree: ttk.Treeview) -> None:
        if self.season is None:
            return
        leaders = build_league_leaders(
            fetch_season_player_stats(self.conn, self.season.season_id),
            self._player_club_map(),
        )
        for category, rows in leaders.items():
            for leader in rows:
                player = self._find_player(leader.player_id)
                player_name = player.name if player else leader.player_id
                club_name = self.clubs[leader.club_id].name if leader.club_id in self.clubs else leader.club_id
                tree.insert(
                    "",
                    tk.END,
                    iid=f"{category}:{leader.player_id}",
                    values=(category, player_name, f"{leader.value:.1f}", club_name),
                )

    def _player_club_map(self) -> Dict[str, str]:
        if self.season is None:
            return {}
        rows = self.conn.execute(
            """
            SELECT DISTINCT player_id, club_id
            FROM player_match_stats
            WHERE match_id IN (SELECT match_id FROM match_records WHERE season_id = ?)
            """,
            (self.season.season_id,),
        ).fetchall()
        if rows:
            return {row["player_id"]: row["club_id"] for row in rows}
        return {player.id: club_id for club_id, roster in self.rosters.items() for player in roster}

    def _wire_items(self) -> List[WireItem]:
        if self.season is None:
            return []
        match_rows = self.conn.execute(
            "SELECT * FROM match_records WHERE season_id = ? ORDER BY week DESC, match_id DESC",
            (self.season.season_id,),
        ).fetchall()
        return build_wire_items(match_rows, self.clubs, load_awards(self.conn, self.season.season_id), self.rosters)

    def _open_selected_schedule_match(self, tree: ttk.Treeview) -> None:
        selection = tree.selection()
        if selection:
            self._open_league_match(selection[0])

    def _open_selected_league_leader(self, tree: ttk.Treeview) -> None:
        selection = tree.selection()
        if selection:
            _, player_id = selection[0].split(":", 1)
            self.show_player_profile(player_id, self.show_league)

    def _open_selected_wire_item(self, tree: ttk.Treeview) -> None:
        selection = tree.selection()
        if not selection:
            return
        item = getattr(self, "wire_item_targets", {}).get(selection[0])
        if item and item.match_id and self._record_for_match(item.match_id) is not None:
            self.show_report(item.match_id)
        elif item and item.player_id:
            self.show_player_profile(item.player_id, self.show_league)

    def _open_league_match(self, match_id: str) -> None:
        if self._record_for_match(match_id) is not None:
            self.show_report(match_id)
            return
        match = self._scheduled_match(match_id)
        if match is None:
            return
        self._show_future_match_preview(match)

    def _show_future_match_preview(self, match: ScheduledMatch) -> None:
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Upcoming Match", style="Display.TLabel").grid(row=0, column=0, sticky="w")
        text = self._text(frame, font=FONT_MONO)
        text.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)
        home = self.clubs[match.home_club_id]
        away = self.clubs[match.away_club_id]
        home_team = self._team_for_club(home, self.rosters[home.club_id])
        away_team = self._team_for_club(away, self.rosters[away.club_id])
        text.insert(tk.END, f"Week {match.week}: {home.name} vs {away.name}\n\n")
        text.insert(tk.END, f"{home.name}: {home.tagline}\nOVR {team_overall(home_team):.1f}\n\n")
        text.insert(tk.END, f"{away.name}: {away.tagline}\nOVR {team_overall(away_team):.1f}\n\n")
        if self.player_club_id in (home.club_id, away.club_id):
            text.insert(tk.END, "This is one of your upcoming matches. Start it from the Hub when its week arrives.\n")
        else:
            text.insert(tk.END, "Around-the-league match. It will simulate when this week is played.\n")
        text.configure(state=tk.DISABLED)
        ttk.Button(frame, text="Back to League", command=self.show_league, style="Accent.TButton").grid(row=2, column=0, sticky="e")

    def _manual_save(self) -> None:
        save_career_state_cursor(self.conn, self.cursor)
        self.conn.commit()
        messagebox.showinfo("Saved", f"Career saved to {self.db_path}.")

    def _text(self, parent: tk.Misc, height: int = 20, font=FONT_BODY) -> tk.Text:
        return tk.Text(parent, height=height, bg=DM_PAPER, fg=DM_MUTED_CHARCOAL, font=font, wrap="word", relief="solid", bd=1, highlightthickness=0)


def _score_player(stats: Optional[PlayerMatchStats]) -> float:
    if stats is None:
        return 0.0
    return (
        stats.eliminations_by_throw * 3.0
        + stats.catches_made * 4.0
        + stats.dodges_successful * 1.5
        + stats.revivals_caused * 2.0
        - stats.times_eliminated * 2.0
        + stats.clutch_events
    )


def replay_event_label(event, name_map: dict | None = None) -> str:
    """Short broadcast label for an engine event. name_map resolves player IDs to display names."""
    _names = name_map or {}
    if event.event_type == "match_end":
        winner = event.outcome.get("winner")
        return f"Final whistle: {winner or 'draw'}"
    if event.event_type != "throw":
        return title_label(event.event_type)
    resolution = str(event.outcome.get("resolution", "throw"))
    thrower_id = event.actors.get("thrower", "-")
    target_id = event.actors.get("target", "-")
    thrower = _names.get(thrower_id, thrower_id)
    target = _names.get(target_id, target_id)
    if resolution == "hit":
        return f"HIT: {thrower} tags {target}"
    if resolution == "failed_catch":
        return f"DROP: {target} cannot hold {thrower}'s throw"
    if resolution == "catch":
        return f"CATCH: {target} turns over {thrower}"
    if resolution == "dodged":
        return f"DODGE: {target} slips {thrower}"
    if resolution == "miss":
        return f"MISS: {thrower} misses {target}"
    return f"{resolution.upper()}: {thrower} to {target}"


def replay_phase_delay(event) -> int:
    """Milliseconds to hold an event during automatic replay."""
    if event.event_type == "match_end":
        return 1500
    resolution = event.outcome.get("resolution")
    if resolution in ("hit", "failed_catch", "catch"):
        return 900
    if resolution == "dodged":
        return 650
    return 420


def main() -> None:
    root = tk.Tk()
    ManagerModeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
