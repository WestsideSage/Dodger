from __future__ import annotations

import sqlite3
from typing import List

from .career_state import CareerState, CareerStateCursor
from .config import DEFAULT_SCOUTING_CONFIG
from .franchise import create_season
from .models import Player, PlayerRatings, PlayerTraits
from .league import Conference, League, Club
from .persistence import (
    create_schema,
    get_state,
    save_career_state_cursor,
    save_club,
    save_lineup_default,
    save_season,
    save_season_format,
    set_state,
)
from .playoffs import PLAYOFF_FORMAT
from .randomizer import _FIRST_NAMES, _LAST_NAMES
from .rng import DeterministicRNG, derive_seed
from .sample_data import curated_clubs
from .scouting_center import initialize_scouting_for_career
from .view_models import normalize_root_seed

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


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_curated_roster(club_id: str, club_name: str, seed: int, count: int = 6) -> List[Player]:
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
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        roster.append(
            Player(
                id=f"{club_id}_{index}",
                name=name,
                ratings=PlayerRatings(
                    accuracy=accuracy,
                    power=power,
                    dodge=dodge,
                    catch=catch,
                    stamina=_clamp(rng.gauss(66, 7), 40, 95),
                ).apply_bounds(),
                traits=PlayerTraits(
                    potential=_clamp(rng.gauss(50, 15), 10, 90),
                    growth_curve=_clamp(rng.gauss(50, 12), 10, 90),
                    consistency=_clamp(rng.gauss(50, 12), 10, 90),
                    pressure=_clamp(rng.gauss(50, 12), 10, 90),
                ),
                age=18 + int(rng.unit() * 12),
                club_id=club_id,
                newcomer=index >= 5,
            )
        )
    return roster


def initialize_curated_manager_career(
    conn: sqlite3.Connection,
    selected_club_id: str,
    root_seed: int,
    custom_club: Club | None = None,
    custom_roster: List[Player] | None = None,
) -> CareerStateCursor:
    """Create a fresh Manager career using the curated league without importing UI code."""
    root_seed = normalize_root_seed(root_seed)
    create_schema(conn)
    for table in MANAGER_TABLES:
        conn.execute(f"DELETE FROM {table}")

    clubs = curated_clubs()
    if custom_club:
        clubs.append(custom_club)

    selected_ids = {club.club_id for club in clubs}
    if selected_club_id not in selected_ids:
        raise ValueError(f"Unknown curated club: {selected_club_id}")

    rosters = {
        club.club_id: build_curated_roster(
            club.club_id,
            club.name,
            derive_seed(root_seed, "roster", club.club_id),
        )
        for club in clubs if club.club_id != selected_club_id or custom_roster is None
    }
    if custom_roster is not None:
        rosters[selected_club_id] = custom_roster

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
    initialize_scouting_for_career(conn, root_seed=root_seed, config=DEFAULT_SCOUTING_CONFIG)
    conn.commit()
    return cursor


def ensure_default_web_career(
    conn: sqlite3.Connection,
    *,
    selected_club_id: str = "aurora",
    root_seed: int = 20260426,
) -> None:
    create_schema(conn)
    if get_state(conn, "active_season_id") and get_state(conn, "player_club_id"):
        return
    initialize_curated_manager_career(conn, selected_club_id, root_seed)


__all__ = [
    "MANAGER_TABLES",
    "build_curated_roster",
    "ensure_default_web_career",
    "initialize_curated_manager_career",
]
