from __future__ import annotations

import sqlite3
from typing import List

import dataclasses
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
    classify_club_archetype,
)
from .playoffs import PLAYOFF_FORMAT
from .randomizer import _FIRST_NAMES, _LAST_NAMES
from .rng import DeterministicRNG, derive_seed
from .sample_data import curated_clubs
from .scouting_center import initialize_scouting_for_career
from .view_models import normalize_root_seed
import re
from typing import Any, Dict
from .models import PlayerRatings, PlayerTraits
from .career_state import CareerState, CareerStateCursor
from .rng import DeterministicRNG, derive_seed
from .sample_data import curated_clubs
from .season import Season
from .league import Conference, League
from .franchise import create_season
from .playoffs import PLAYOFF_FORMAT
from .view_models import normalize_root_seed
import re
from typing import Any, Dict
from .models import PlayerRatings, PlayerTraits
from .career_state import CareerState, CareerStateCursor
from .rng import DeterministicRNG, derive_seed
from .sample_data import curated_clubs
from .season import Season
from .league import Conference, League
from .franchise import create_season
from .playoffs import PLAYOFF_FORMAT
from .view_models import normalize_root_seed
import re
from typing import Any, Dict
from .models import PlayerRatings, PlayerTraits
from .career_state import CareerState, CareerStateCursor
from .rng import DeterministicRNG, derive_seed
from .sample_data import curated_clubs
from .season import Season
from .league import Conference, League
from .franchise import create_season
from .playoffs import PLAYOFF_FORMAT
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
        ratings = PlayerRatings(
            accuracy=accuracy,
            power=power,
            dodge=dodge,
            catch=catch,
            stamina=_clamp(rng.gauss(66, 7), 40, 95),
        ).apply_bounds()
        from .archetype_derivation import derive_archetype
        roster.append(
            Player(
                id=f"{club_id}_{index}",
                name=name,
                ratings=ratings,
                archetype=derive_archetype(ratings),
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
    ruleset_selection: str | None = None,
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
        is_user = (club.club_id == selected_club_id)
        arch = classify_club_archetype(club.club_id, is_user, rosters[club.club_id])
        club = dataclasses.replace(club, program_archetype=arch)
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
    # V11: ruleset selection is set at career creation only and persists
    # for the lifetime of the career. Existing saves stay on generic.
    if ruleset_selection:
        from .rulesets import RulesetSelection
        # Validate by constructing the enum.
        RulesetSelection(ruleset_selection)
        set_state(conn, "ruleset_selection", ruleset_selection)
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


# ----------------------------------------------------------------------
# Manager career bootstrapping (formerly manager_helpers)
# ----------------------------------------------------------------------

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
    from .archetype_derivation import derive_archetype
    for index, (label, base) in enumerate(roles[:count], 1):
        accuracy, power, dodge, catch = (
            _clamp(value + rng.gauss(0, 4), 35, 95) for value in base
        )
        player_id = f"{club.club_id}_{index}"
        ratings = PlayerRatings(
            accuracy=accuracy,
            power=power,
            dodge=dodge,
            catch=catch,
            stamina=_clamp(rng.gauss(66, 7), 40, 95),
        ).apply_bounds()
        roster.append(
            Player(
                id=player_id,
                name=f"{club.name.split()[0]} {label}",
                ratings=ratings,
                archetype=derive_archetype(ratings),
                traits=PlayerTraits(),
                age=18 + int(rng.unit() * 12),
                club_id=club.club_id,
                newcomer=index >= 5,
            )
        )
    return roster

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
    from .archetype_derivation import derive_archetype
    for index, (label, base) in enumerate(roles[:count], 1):
        accuracy, power, dodge, catch, stamina = (
            _clamp(value + rng.gauss(0, 3), 35, 72) for value in base
        )
        ratings = PlayerRatings(
            accuracy=accuracy,
            power=power,
            dodge=dodge,
            catch=catch,
            stamina=stamina,
        ).apply_bounds()
        roster.append(
            Player(
                id=f"{club_id}_{index}",
                name=f"{club_id.removeprefix('exp_').replace('_', ' ').title()} {label}",
                ratings=ratings,
                archetype=derive_archetype(ratings),
                traits=PlayerTraits(),
                age=18 + int(rng.unit() * 10),
                club_id=club_id,
                newcomer=True,
            )
        )
    return roster

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
        is_user = (club.club_id == selected_club_id)
        arch = classify_club_archetype(club.club_id, is_user, rosters[club.club_id])
        club = dataclasses.replace(club, program_archetype=arch)
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
        is_user = (club.club_id == expansion_club.club_id)
        arch = classify_club_archetype(club.club_id, is_user, rosters[club.club_id])
        club = dataclasses.replace(club, program_archetype=arch)
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
