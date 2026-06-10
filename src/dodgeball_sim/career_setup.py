from __future__ import annotations

import sqlite3
from typing import List

import dataclasses
from .career_state import CareerState, CareerStateCursor
from .config import DEFAULT_SCOUTING_CONFIG
from .franchise import create_season
from .models import Player, PlayerRatings, PlayerTraits
from .league import Conference, League, Club
from .lineup import optimize_ai_lineup
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


def _persist_initial_lineup_default(
    conn: sqlite3.Connection, club_id: str, roster: List[Player], *, is_user: bool
) -> None:
    """Persist a club's starting lineup default.

    The user club gets the best-by-role/OVR six (``optimize_ai_lineup``) so the
    fielded-6 is strong from week 1 and the briefing's matchup edge reflects the
    same six the sim activates (D1: one canonical fielded-6). AI clubs keep raw
    roster order — their on-court lineup is governed elsewhere and changing it
    would shift AI-vs-AI sim baselines.
    """
    ordered = optimize_ai_lineup(roster) if is_user else [player.id for player in roster]
    save_lineup_default(conn, club_id, ordered)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _unique_roster_names(rng: DeterministicRNG, count: int) -> List[str]:
    combos = [(first, last) for first in _FIRST_NAMES for last in _LAST_NAMES]
    shuffled = rng.shuffle(combos)
    names: List[str] = []
    used_last_names: set[str] = set()

    for first, last in shuffled:
        if last in used_last_names:
            continue
        names.append(f"{first} {last}")
        used_last_names.add(last)
        if len(names) == count:
            return names

    for first, last in shuffled:
        name = f"{first} {last}"
        if name in names:
            continue
        names.append(name)
        if len(names) == count:
            return names

    return names


def _curated_potential_ceiling(raw_potential: float, ovr: int, age: int) -> int:
    """Map the legacy 10-90 potential draw onto an OVR-scale ceiling.

    `traits.potential` is consumed everywhere as the highest OVR a player can
    reach: development closes the (potential - OVR) headroom gap, the roster
    page renders it as "Ceiling", and potential tiers bucket the absolute
    value. Every other player source already seeds it on that scale
    (recruitment rolls 55-96; prospect conversion floors at 70). This curated
    draw predates that contract, so half a fresh takeover roster used to carry
    a "ceiling" below its current OVR — zero headroom, zero development, and a
    first offseason where every starter moved +0. Read the same deterministic
    draw as growth juice instead: more juice and a younger age mean more room
    above the current OVR, and a low-juice veteran is honestly plateaued
    (ceiling == current OVR).
    """
    juice = _clamp((raw_potential - 10.0) / 80.0, 0.0, 1.0)
    if age <= 21:
        age_scale = 1.0
    elif age <= 25:
        age_scale = 0.6
    elif age <= 29:
        age_scale = 0.3
    else:
        age_scale = 0.1
    headroom = round(20.0 * juice * age_scale)
    return int(_clamp(ovr + headroom, ovr, 95))


def build_curated_roster(club_id: str, club_name: str, seed: int, count: int = 6) -> List[Player]:
    rng = DeterministicRNG(seed)
    # V18 Task 3 (owner-approved 2026-06-10): each role carries an age band so
    # every curated club seeds the vet / prime / rising / prodigy texture the
    # owner cited from Teamfight Manager 2, instead of the old uniform 18-29
    # draw that left the league with zero retirement-age players until ~S9.
    # The band draw consumes exactly ONE rng.unit() per player — the same
    # count as the old draw — so every other rolled value (names, ratings,
    # traits) is byte-identical to the previous seeding.
    roles = [
        ("Captain", (76, 72, 62, 58), (31, 33)),   # proven veteran leader
        ("Striker", (70, 78, 58, 52), (26, 29)),   # prime scorer
        ("Anchor", (61, 62, 64, 76), (28, 31)),    # late-prime stabilizer
        ("Runner", (64, 58, 78, 60), (22, 25)),    # rising starter
        ("Rookie", (60, 61, 62, 63), (18, 20)),    # prodigy
        ("Utility", (66, 65, 65, 65), (19, 23)),   # young depth
    ]
    roster: List[Player] = []
    names = _unique_roster_names(rng, count)
    for index, (label, base, (age_lo, age_hi)) in enumerate(roles[:count], 1):
        accuracy, power, dodge, catch = (
            _clamp(value + rng.gauss(0, 4), 35, 95) for value in base
        )
        name = names[index - 1]
        ratings = PlayerRatings(
            accuracy=accuracy,
            power=power,
            dodge=dodge,
            catch=catch,
            stamina=_clamp(rng.gauss(66, 7), 40, 95),
            tactical_iq=_clamp(rng.gauss(62, 10), 30, 95),
            catch_courage=_clamp(rng.gauss(62, 10), 30, 95),
            throw_selection_iq=_clamp(rng.gauss(62, 10), 30, 95),
            conditioning_curve=_clamp(rng.gauss(62, 10), 30, 95),
        ).apply_bounds()
        from .archetype_derivation import derive_archetype
        player = Player(
            id=f"{club_id}_{index}",
            name=name,
            ratings=ratings,
            archetype=derive_archetype(ratings),
            traits=PlayerTraits(
                potential=int(round(_clamp(rng.gauss(50, 15), 10, 90))),
                growth_curve=int(round(_clamp(rng.gauss(50, 12), 10, 90))),
                consistency=int(round(_clamp(rng.gauss(50, 12), 10, 90))),
                pressure=int(round(_clamp(rng.gauss(50, 12), 10, 90))),
            ),
            age=age_lo + int(rng.unit() * (age_hi - age_lo + 1)),
            club_id=club_id,
            newcomer=index >= 5,
        )
        # Re-read the raw potential draw as an OVR-scale ceiling (the contract
        # the development engine and roster display consume). Done as a post-hoc
        # replace so the RNG stream — and therefore every other rolled value —
        # is byte-identical to the previous seeding.
        player = dataclasses.replace(
            player,
            traits=dataclasses.replace(
                player.traits,
                potential=_curated_potential_ceiling(
                    float(player.traits.potential),
                    int(round(player.overall_skill())),
                    player.age,
                ),
            ),
        )
        roster.append(player)
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
        _persist_initial_lineup_default(conn, club.club_id, rosters[club.club_id], is_user=is_user)

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

    # V18 Task 3: seeded players carry a synthetic prior-career length
    # consistent with their age (turned pro at 19), under the dedicated
    # `seasons_played_prior` key. Only retirement biology
    # (development.should_retire) reads it — `seasons_played`, HoF cases,
    # records, and every display surface keep the RECORDED sim history, so
    # no fabricated careers ever render. Without this, should_retire's
    # seasons_played >= 8-10 gates are unreachable before sim-season 8 and a
    # seeded 33-year-old cannot retire until age 40 (V18 BEFORE table:
    # first league retirement was season 9 on every probed seed).
    from .persistence import save_player_career_stats

    for roster in rosters.values():
        for player in roster:
            prior_seasons = max(0, int(player.age) - 19)
            if prior_seasons <= 0:
                continue
            save_player_career_stats(
                conn,
                player.id,
                {
                    "player_id": player.id,
                    "player_name": player.name,
                    "club_id": player.club_id or "",
                    "seasons_played": 0,
                    "seasons_played_prior": prior_seasons,
                },
            )

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
    ruleset_selection: str | None = "official_foam",
) -> None:
    # WT-17: when this bootstrap path mints a brand-new career it defaults to
    # the official foam ruleset (matching the frontend / NewSaveRequest), so an
    # automation-created career is not silently generic. Existing saves with an
    # active season are left untouched.
    create_schema(conn)
    if get_state(conn, "active_season_id") and get_state(conn, "player_club_id"):
        return
    initialize_curated_manager_career(
        conn, selected_club_id, root_seed, ruleset_selection=ruleset_selection
    )


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
            tactical_iq=_clamp(rng.gauss(62, 10), 30, 95),
            catch_courage=_clamp(rng.gauss(62, 10), 30, 95),
            throw_selection_iq=_clamp(rng.gauss(62, 10), 30, 95),
            conditioning_curve=_clamp(rng.gauss(62, 10), 30, 95),
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
            tactical_iq=_clamp(rng.gauss(50, 10), 30, 95),
            catch_courage=_clamp(rng.gauss(50, 10), 30, 95),
            throw_selection_iq=_clamp(rng.gauss(50, 10), 30, 95),
            conditioning_curve=_clamp(rng.gauss(50, 10), 30, 95),
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
        _persist_initial_lineup_default(conn, club.club_id, rosters[club.club_id], is_user=is_user)

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
        _persist_initial_lineup_default(conn, club.club_id, rosters[club.club_id], is_user=is_user)

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
