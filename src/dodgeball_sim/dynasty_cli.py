from __future__ import annotations

"""Dynasty mode CLI.

Entry point: dynasty_main(conn, difficulty). Manages the full season loop —
create league, sim matchdays, view standings, view season summary.
All I/O flows through persistence.py; pure computation through franchise.py.
"""

import json
import sqlite3
from dataclasses import replace
from typing import Dict, List, Optional, Set, Tuple

from .awards import compute_season_awards
from .development import apply_season_development, should_retire
from .cup import CupBracket, generate_cup_bracket
from .facilities import FACILITY_DEFINITIONS, FacilityType, normalize_facility_selection
from .franchise import MatchRecord, create_season, extract_match_stats, simulate_match, simulate_matchday
from .career import aggregate_career, build_signature_moment, evaluate_hall_of_fame
from .identity import build_identity_profile
from .league import Club, Conference, League
from .meta import MetaPatch, RuleSetOverrides
from .models import CoachPolicy, Player, PlayerRatings, PlayerTraits
from .news import MatchdayResult, generate_matchday_news
from .persistence import (
    fetch_player_career_summary,
    fetch_season_player_stats,
    get_state,
    load_all_rosters,
    load_awards,
    load_club_facilities,
    load_club_prestige,
    load_club_trophies,
    load_clubs,
    load_completed_match_ids,
    load_cup_bracket,
    load_cup_results,
    load_free_agents,
    load_hall_of_fame,
    load_league_records,
    load_meta_patch,
    load_news_headlines,
    load_player_identity,
    load_player_career_stats,
    load_rivalry_records,
    load_signature_moments,
    load_season,
    load_standings,
    save_awards,
    save_club,
    save_club_facilities,
    save_club_prestige,
    save_club_trophy,
    save_cup_bracket,
    save_cup_result,
    save_free_agents,
    save_hall_of_fame_entry,
    save_league_record,
    save_match_result,
    save_meta_patch,
    save_news_headlines,
    save_player_career_stats,
    save_player_identity,
    save_player_season_stats,
    save_player_stats_batch,
    save_retired_player,
    save_rivalry_record,
    save_signature_moment,
    save_season,
    save_standings,
    set_state,
)
from .records import CareerStats as RecordCareerStats, LeagueRecord, TeamRecordStats, UpsetResult, check_records_broken
from .recruitment import generate_rookie_class
from .rivalries import RivalryMatchResult, RivalryRecord, compute_rivalry_score, update_rivalry
from .rng import DeterministicRNG, derive_seed
from .scheduler import ScheduledMatch
from .scouting import BudgetLevel, generate_scout_report
from .season import SeasonResult, compute_standings
from .stats import PlayerMatchStats


# ---------------------------------------------------------------------------
# Club and roster generation
# ---------------------------------------------------------------------------

_CLUB_POOL: List[Tuple[str, str, str, str, int]] = [
    # (club_id, name, colors, region, founded_year)
    ("thunder_wolves",  "Thunder Wolves",  "crimson/black",    "North",    1988),
    ("storm_eagles",    "Storm Eagles",    "blue/silver",      "East",     1992),
    ("iron_foxes",      "Iron Foxes",      "orange/charcoal",  "West",     1979),
    ("neon_sharks",     "Neon Sharks",     "teal/white",       "South",    2001),
    ("blaze_falcons",   "Blaze Falcons",   "red/gold",         "Central",  1985),
    ("frost_jaguars",   "Frost Jaguars",   "ice blue/white",   "Mountain", 1997),
    ("solar_bears",     "Solar Bears",     "amber/black",      "Plains",   1983),
    ("tide_cobras",     "Tide Cobras",     "navy/green",       "Coastal",  2005),
    ("arc_panthers",    "Arc Panthers",    "purple/silver",    "East",     1990),
    ("dust_ravens",     "Dust Ravens",     "tan/slate",        "West",     1976),
    ("volt_tigers",     "Volt Tigers",     "yellow/charcoal",  "South",    2009),
    ("cinder_hawks",    "Cinder Hawks",    "rust/brown",       "North",    1971),
]

_FIRST_NAMES = [
    "Rin", "Avery", "Kai", "River", "Mara", "Ezra", "Sloane", "Jules",
    "Remy", "Quinn", "Niko", "Sable", "Ash", "Lyra", "Zeph", "Cass",
]
_LAST_NAMES = [
    "Voss", "Helix", "Turner", "Lark", "Orion", "Vega", "Keene", "Hart",
    "Rowe", "Slate", "Frost", "Drake", "Munn", "Cole", "Beck", "Thorn",
]


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _generate_club_roster(club_id: str, seed: int, count: int = 5) -> List[Player]:
    rng = DeterministicRNG(seed)
    players: List[Player] = []
    for i in range(count):
        first = _FIRST_NAMES[int(rng.unit() * len(_FIRST_NAMES))]
        last = _LAST_NAMES[int(rng.unit() * len(_LAST_NAMES))]
        age = max(18, min(32, int(rng.gauss(24, 4))))
        players.append(
            Player(
                id=f"{club_id}_p{i + 1}",
                name=f"{first} {last}",
                age=age,
                club_id=club_id,
                newcomer=True,
                ratings=PlayerRatings(
                    accuracy=_clamp(rng.gauss(65, 12), 30, 95),
                    power=_clamp(rng.gauss(65, 12), 30, 95),
                    dodge=_clamp(rng.gauss(65, 12), 30, 95),
                    catch=_clamp(rng.gauss(65, 12), 30, 95),
                    stamina=_clamp(rng.gauss(60, 10), 35, 95),
                ).apply_bounds(),
                traits=PlayerTraits(
                    potential=_clamp(rng.gauss(78, 10), 55, 98),
                    growth_curve=("early", "steady", "late")[int(rng.unit() * 3) % 3],
                    consistency=round(_clamp(rng.gauss(0.55, 0.18), 0.15, 0.95), 4),
                    pressure=round(_clamp(rng.gauss(0.5, 0.2), 0.1, 0.95), 4),
                ),
            )
        )
    return players


def _generate_league_clubs(
    root_seed: int, n: int = 8
) -> Tuple[List[Club], Dict[str, List[Player]]]:
    """Generate n clubs from the pool with seeded rosters. Pure."""
    rng = DeterministicRNG(derive_seed(root_seed, "league_gen"))
    pool = list(_CLUB_POOL)
    chosen_defs = []
    for _ in range(n):
        idx = int(rng.unit() * len(pool))
        chosen_defs.append(pool.pop(idx))

    clubs: List[Club] = []
    rosters: Dict[str, List[Player]] = {}
    for club_id, name, colors, region, founded in chosen_defs:
        policy = CoachPolicy(
            target_stars=_clamp(rng.gauss(0.5, 0.15), 0.2, 0.9),
            risk_tolerance=_clamp(rng.gauss(0.5, 0.15), 0.2, 0.9),
            sync_throws=_clamp(rng.gauss(0.4, 0.15), 0.1, 0.8),
            tempo=_clamp(rng.gauss(0.5, 0.12), 0.3, 0.8),
            rush_frequency=_clamp(rng.gauss(0.5, 0.15), 0.2, 0.9),
        )
        clubs.append(Club(
            club_id=club_id,
            name=name,
            colors=colors,
            home_region=region,
            founded_year=founded,
            coach_policy=policy,
        ))
        roster_seed = derive_seed(root_seed, "roster", club_id)
        rosters[club_id] = _generate_club_roster(club_id, roster_seed)

    return clubs, rosters


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _bar(val: float, max_val: float = 100.0, width: int = 10) -> str:
    filled = int(round(val / max_val * width))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def _print_divider(char: str = "-", width: int = 60) -> None:
    print(char * width)


def _print_standings(standings, clubs: Dict[str, Club]) -> None:
    _print_divider("=")
    print(f"{'#':<4} {'Club':<22} {'W':>3} {'D':>3} {'L':>3} {'Pts':>4} {'Diff':>5}")
    _print_divider()
    for i, row in enumerate(standings, 1):
        name = clubs[row.club_id].name if row.club_id in clubs else row.club_id
        diff_str = f"+{row.elimination_differential}" if row.elimination_differential >= 0 else str(row.elimination_differential)
        print(
            f"{i:<4} {name:<22} {row.wins:>3} {row.draws:>3} {row.losses:>3} "
            f"{row.points:>4} {diff_str:>5}"
        )
    _print_divider("=")


def _print_match_report(
    record: MatchRecord,
    clubs: Dict[str, Club],
    stats: Dict,
) -> None:
    home_name = clubs.get(record.home_club_id, Club(record.home_club_id, record.home_club_id, "", "", 0)).name
    away_name = clubs.get(record.away_club_id, Club(record.away_club_id, record.away_club_id, "", "", 0)).name

    box = record.result.box_score["teams"]
    home_box = box.get(record.home_club_id, {})
    away_box = box.get(record.away_club_id, {})
    home_surv = home_box.get("totals", {}).get("living", 0)
    away_surv = away_box.get("totals", {}).get("living", 0)

    winner_id = record.result.winner_team_id
    if winner_id == record.home_club_id:
        result_str = f"{home_name} WIN"
    elif winner_id == record.away_club_id:
        result_str = f"{away_name} WIN"
    else:
        result_str = "DRAW"

    _print_divider("=")
    print(f"  {home_name} vs {away_name}  (Week {record.week})")
    print(f"  Survivors: {home_name} {home_surv} — {away_name} {away_surv}  |  {result_str}")
    _print_divider()

    if stats:
        # Top 3 by eliminations
        elim_ranked = sorted(stats.items(), key=lambda kv: -kv[1].eliminations_by_throw)[:3]
        if elim_ranked:
            print("  Top performers (eliminations):")
            for pid, s in elim_ranked:
                catches = s.catches_made
                print(f"    {pid:<22}  elims={s.eliminations_by_throw}  catches={catches}  dodges={s.dodges_successful}")
    if record.meta_patch_id:
        print(f"  Seasonal patch: {record.meta_patch_id}")
    _print_divider("=")


def _print_roster(conn: sqlite3.Connection, club: Club, roster: List[Player]) -> None:
    _print_divider("=")
    print(f"  Roster: {club.name}")
    _print_divider()
    for player in sorted(roster, key=lambda item: (-item.overall(), item.id)):
        print(
            f"  {player.id:<22} age={player.age:<2} ovr={player.overall():>5.1f} "
            f"ACC={player.ratings.accuracy:>5.1f} POW={player.ratings.power:>5.1f} "
            f"DOD={player.ratings.dodge:>5.1f} CAT={player.ratings.catch:>5.1f} "
            f"{'rookie' if player.newcomer else ''}"
        )
        print(f"    {_identity_summary(conn, player)}")
    _print_divider("=")


def _print_free_agents(players: List[Player]) -> None:
    _print_divider("=")
    print("  Free Agents + Rookie Class")
    _print_divider()
    if not players:
        print("  No free agents available.")
    for player in sorted(players, key=lambda item: (-item.overall(), item.id)):
        print(
            f"  {player.id:<22} age={player.age:<2} ovr={player.overall():>5.1f} "
            f"newcomer={'yes' if player.newcomer else 'no ':<3} name={player.name}"
        )
    _print_divider("=")


def _print_offseason_report(conn: sqlite3.Connection) -> None:
    development_rows = json.loads(get_state(conn, "offseason_development_json", "[]") or "[]")
    retirement_rows = json.loads(get_state(conn, "offseason_retirements_json", "[]") or "[]")

    _print_divider("=")
    print("  Offseason Report")
    _print_divider()
    if development_rows:
        print("  Development:")
        for row in development_rows:
            sign = "+" if row["delta"] >= 0 else ""
            print(
                f"    {row['player_id']:<22} overall {row['before']:.1f} -> "
                f"{row['after']:.1f} ({sign}{row['delta']:.1f})"
            )
    else:
        print("  No development report available yet.")

    if retirement_rows:
        print("  Retirements:")
        for row in retirement_rows:
            print(f"    {row['player_id']:<22} age={row['age']} reason={row['reason']}")
    _print_divider("=")


def _identity_summary(conn: sqlite3.Connection, player: Player) -> str:
    identity = load_player_identity(conn, player.id)
    if not identity:
        return player.name
    return f"{player.name} \"{identity['nickname']}\" [{identity['archetype']}]"


def _print_player_page(
    conn: sqlite3.Connection,
    player: Player,
    club_name: str,
) -> None:
    identity = load_player_identity(conn, player.id)
    career = conn.execute(
        """
        SELECT season_id, club_id, matches, total_eliminations, total_catches_made,
               total_dodges_successful, total_times_eliminated, newcomer
        FROM player_season_stats
        WHERE player_id = ?
        ORDER BY season_id
        """,
        (player.id,),
    ).fetchall()
    moments = load_signature_moments(conn, player.id)
    career_summary = load_player_career_stats(conn, player.id)

    _print_divider("=")
    print(f"  Player Page: {player.name}")
    _print_divider()
    print(f"  Club: {club_name}")
    print(f"  Age: {player.age}  Overall: {player.overall():.1f}")
    if identity:
        print(f"  Nickname: {identity['nickname']}  |  Archetype: {identity['archetype']}")
    print(
        f"  Ratings: ACC={player.ratings.accuracy:.1f} POW={player.ratings.power:.1f} "
        f"DOD={player.ratings.dodge:.1f} CAT={player.ratings.catch:.1f} STA={player.ratings.stamina:.1f}"
    )
    if career_summary:
        print(
            f"  Career: seasons={career_summary.get('seasons_played', 0)} "
            f"elims={career_summary.get('career_eliminations', 0)} "
            f"catches={career_summary.get('career_catches', 0)} "
            f"dodges={career_summary.get('career_dodges', 0)}"
        )
    if career:
        print("  Season history:")
        for row in career:
            print(
                f"    {row['season_id']}: matches={row['matches']} "
                f"elims={row['total_eliminations']} catches={row['total_catches_made']} "
                f"dodges={row['total_dodges_successful']} outs={row['total_times_eliminated']}"
            )
    if moments:
        print("  Signature moments:")
        for moment in moments[-5:]:
            print(f"    {moment['season_id']} {moment['moment_type']}: {moment['description']}")
    _print_divider("=")


def _print_hall_of_fame(conn: sqlite3.Connection) -> None:
    entries = load_hall_of_fame(conn)
    _print_divider("=")
    print("  Hall of Fame")
    _print_divider()
    if not entries:
        print("  No inductees yet.")
    for entry in entries:
        summary = entry["career_summary"]
        print(
            f"  {entry['player_id']:<22} inducted={entry['induction_season']} "
            f"legacy={summary.get('legacy_score', 0)} elims={summary.get('total_eliminations', 0)} "
            f"titles={summary.get('championships', 0)}"
        )
    _print_divider("=")


def _print_league_wire(conn: sqlite3.Connection, season_id: str) -> None:
    headlines = load_news_headlines(conn, season_id)
    _print_divider("=")
    print(f"  League Wire — {season_id}")
    _print_divider()
    if not headlines:
        print("  No headlines yet.")
    for headline in headlines:
        print(f"  Week {headline['week']:<2} [{headline['category']}] {headline['headline_text']}")
    _print_divider("=")


def _print_record_book(conn: sqlite3.Connection) -> None:
    records = load_league_records(conn)
    _print_divider("=")
    print("  Record Book")
    _print_divider()
    if not records:
        print("  No records saved yet.")
    for record in records:
        print(
            f"  {record['record_type']:<28} {record['holder_id']:<20} "
            f"value={record['record_value']} season={record['set_in_season']}"
        )
    _print_divider("=")


def _print_meta_patch(meta_patch: MetaPatch) -> None:
    _print_divider("=")
    print(f"  Seasonal Patch: {meta_patch.name}")
    _print_divider()
    print(f"  {meta_patch.description}")
    modifiers = meta_patch.modifier_summary()
    print(
        "  Modifiers: "
        f"power stamina {modifiers['power_stamina_cost_modifier']:+.2f}, "
        f"dodge penalty {modifiers['dodge_penalty_modifier']:+.2f}, "
        f"fatigue rate {modifiers['fatigue_rate_modifier']:+.2f}"
    )
    overrides = meta_patch.ruleset_overrides.explicit_values()
    if overrides:
        print(f"  Ruleset overrides: {json.dumps(overrides, sort_keys=True)}")
    _print_divider("=")


def _cup_resolve_side(side: Dict[str, object] | None, results: Dict[str, str]) -> str | None:
    if side is None:
        return None
    club_id = side.get("club_id")
    if club_id:
        return str(club_id)
    source_match_id = side.get("source_match_id")
    if source_match_id:
        return results.get(str(source_match_id))
    return None


def _cup_entrant_name(
    side: Dict[str, object] | None,
    clubs: Dict[str, Club],
    results: Dict[str, str],
) -> str:
    club_id = _cup_resolve_side(side, results)
    if club_id is None:
        if side and side.get("source_match_id"):
            return f"winner {side['source_match_id']}"
        return "pending"
    return _club_display_name(clubs, club_id)


def _print_cup_bracket(
    conn: sqlite3.Connection,
    season_id: str,
    clubs: Dict[str, Club],
) -> None:
    payload = load_cup_bracket(conn, season_id)
    if payload is None:
        print("  No cup bracket created for this season.")
        return
    results = load_cup_results(conn, season_id)
    bracket = payload["bracket"]
    _print_divider("=")
    print(f"  Midseason Cup - {season_id}")
    _print_divider()
    for round_payload in bracket["rounds"]:
        print(f"  Round {round_payload['round_number']}:")
        for match in round_payload["matches"]:
            side_a = _cup_entrant_name(match["side_a"], clubs, results)
            side_b = "BYE" if match["side_b"] is None else _cup_entrant_name(match["side_b"], clubs, results)
            winner_id = results.get(match["match_id"])
            winner_name = _club_display_name(clubs, winner_id) if winner_id else "pending"
            print(
                f"    {match['match_id']:<12} {side_a:<22} vs {side_b:<22} winner={winner_name}"
            )
    trophies = [
        item
        for item in load_club_trophies(conn)
        if item["season_id"] == season_id and item["trophy_type"] == "cup"
    ]
    if trophies:
        print(f"  Champion: {_club_display_name(clubs, trophies[-1]['club_id'])}")
    _print_divider("=")


def _print_rivalries(conn: sqlite3.Connection, clubs: Dict[str, Club]) -> None:
    rivalries = load_rivalry_records(conn)
    _print_divider("=")
    print("  Rivalries")
    _print_divider()
    if not rivalries:
        print("  No rivalry data yet.")
    for item in rivalries:
        rivalry = item["rivalry"]
        club_a = clubs.get(item["club_a_id"], Club(item["club_a_id"], item["club_a_id"], "", "", 0)).name
        club_b = clubs.get(item["club_b_id"], Club(item["club_b_id"], item["club_b_id"], "", "", 0)).name
        print(
            f"  {club_a} vs {club_b}: {rivalry.get('a_wins', 0)}-{rivalry.get('b_wins', 0)}"
            f"-{rivalry.get('draws', 0)} score={rivalry.get('rivalry_score', 0)}"
        )
    _print_divider("=")


def _print_season_summary(
    season_id: str,
    standings,
    awards,
    clubs: Dict[str, Club],
) -> None:
    _print_divider("=")
    print(f"  SEASON SUMMARY — {season_id}")
    _print_divider("=")

    if standings:
        champ_id = standings[0].club_id
        champ_name = clubs[champ_id].name if champ_id in clubs else champ_id
        print(f"  CHAMPION: {champ_name}")
        print()
    print("  Final Standings:")
    _print_standings(standings, clubs)

    if awards:
        print("  Season Awards:")
        _print_divider()
        for award in awards:
            type_label = award.award_type.replace("_", " ").title()
            club_name = clubs[award.club_id].name if award.club_id in clubs else award.club_id
            print(f"    {type_label:<22}  {award.player_id}  ({club_name})  score={award.award_score}")
    _print_divider("=")


# ---------------------------------------------------------------------------
# Dynasty creation
# ---------------------------------------------------------------------------

def _create_new_dynasty(conn: sqlite3.Connection, *, root_seed: int) -> None:
    """Interactive: generate clubs, let user choose one, persist to DB."""
    print("\n=== Creating New Dynasty ===")
    clubs, rosters = _generate_league_clubs(root_seed, n=8)

    print("\nAvailable clubs:")
    for i, club in enumerate(clubs, 1):
        avg_rating = sum(
            (p.ratings.accuracy + p.ratings.power + p.ratings.dodge +
             p.ratings.catch + p.ratings.stamina) / 5
            for p in rosters[club.club_id]
        ) / len(rosters[club.club_id])
        print(
            f"  [{i}] {club.name:<22}  {club.colors:<18}  {club.home_region:<10}  "
            f"avg_rating={avg_rating:.1f}"
        )

    while True:
        choice = input("\nChoose your club (1-8): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(clubs):
            player_club = clubs[int(choice) - 1]
            break
        print("Invalid choice.")

    print(f"\nYou are now managing: {player_club.name}")

    # Persist clubs and rosters
    for club in clubs:
        save_club(conn, club, rosters[club.club_id])
        save_club_prestige(conn, club.club_id, max(load_club_prestige(conn, club.club_id), 6))
    conn.commit()
    _ensure_player_identities(conn, rosters, root_seed)

    # Create league and season
    league = League(
        league_id="league_1",
        name="Dodgeball Premier League",
        conferences=(
            Conference(
                conference_id="conf_1",
                name="Division 1",
                club_ids=tuple(c.club_id for c in clubs),
            ),
        ),
    )

    season = create_season(
        season_id="season_2025",
        year=2025,
        league=league,
        root_seed=root_seed,
    )
    save_season(conn, season)
    conn.commit()

    # Persist dynasty state
    set_state(conn, "root_seed", str(root_seed))
    set_state(conn, "active_season_id", season.season_id)
    set_state(conn, "player_club_id", player_club.club_id)
    set_state(conn, "difficulty", "pro")
    conn.commit()

    print(f"League created — {len(clubs)} clubs, {season.total_weeks()} weeks.")
    print(f"Your season begins now. Good luck managing {player_club.name}!\n")


# ---------------------------------------------------------------------------
# Season loop helpers
# ---------------------------------------------------------------------------

def _current_week(season, completed: Set[str]) -> Optional[int]:
    """Return the earliest week that still has unplayed matches, or None if done."""
    for week in range(1, season.total_weeks() + 1):
        week_matches = season.matches_for_week(week)
        if any(m.match_id not in completed for m in week_matches):
            return week
    return None


def _do_sim_matches(
    conn: sqlite3.Connection,
    matches,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    root_seed: int,
    difficulty: str,
    season_id: str,
    meta_patch: MetaPatch | None = None,
) -> List[MatchRecord]:
    """Sim a list of ScheduledMatches, persist results, return records."""
    records, _ = simulate_matchday(
        matches=matches,
        clubs=clubs,
        rosters=rosters,
        root_seed=root_seed,
        difficulty=difficulty,
        meta_patch=meta_patch,
    )

    for record in records:
        box = record.result.box_score.get("teams", {})
        home_surv = box.get(record.home_club_id, {}).get("totals", {}).get("living", 0)
        away_surv = box.get(record.away_club_id, {}).get("totals", {}).get("living", 0)
        save_match_result(
            conn,
            match_id=record.match_id,
            season_id=record.season_id,
            week=record.week,
            home_club_id=record.home_club_id,
            away_club_id=record.away_club_id,
            winner_club_id=record.result.winner_team_id,
            home_survivors=home_surv,
            away_survivors=away_surv,
            home_roster_hash=record.home_roster_hash,
            away_roster_hash=record.away_roster_hash,
            config_version=record.config_version,
            ruleset_version=record.ruleset_version,
            meta_patch_id=record.meta_patch_id,
            seed=record.seed,
            event_log_hash=record.event_log_hash,
            final_state_hash=record.final_state_hash,
        )

        # Save player stats
        home_roster = rosters[record.home_club_id]
        away_roster = rosters[record.away_club_id]
        stats = extract_match_stats(record, home_roster, away_roster)
        player_club_map = {p.id: record.home_club_id for p in home_roster}
        player_club_map.update({p.id: record.away_club_id for p in away_roster})
        save_player_stats_batch(conn, record.match_id, stats, player_club_map)

    conn.commit()
    return records


def _save_all_rosters(
    conn: sqlite3.Connection,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
) -> None:
    for club_id, club in clubs.items():
        save_club(conn, club, rosters.get(club_id, []))
    conn.commit()


def _ensure_player_identities(
    conn: sqlite3.Connection,
    rosters: Dict[str, List[Player]],
    root_seed: int,
) -> None:
    for roster in rosters.values():
        for player in roster:
            if load_player_identity(conn, player.id) is not None:
                continue
            profile = build_identity_profile(
                player,
                DeterministicRNG(derive_seed(root_seed, "nickname", player.id)),
            )
            save_player_identity(conn, player.id, profile.nickname, profile.title)
    conn.commit()


def _club_display_name(clubs: Dict[str, Club], club_id: str) -> str:
    return clubs.get(club_id, Club(club_id, club_id, "", "", 0)).name


def _difficulty_budget_level(difficulty: str) -> BudgetLevel:
    mapping: Dict[str, BudgetLevel] = {
        "rookie": "high",
        "pro": "medium",
        "elite": "low",
    }
    return mapping.get(difficulty, "medium")


def _promote_budget_level(level: BudgetLevel, tiers: int) -> BudgetLevel:
    order: List[BudgetLevel] = ["low", "medium", "high"]
    index = min(order.index(level) + max(0, tiers), len(order) - 1)
    return order[index]


def _effective_scouting_budget(
    conn: sqlite3.Connection,
    player_club_id: str,
    season_id: str,
    difficulty: str,
) -> BudgetLevel:
    base = _difficulty_budget_level(difficulty)
    facilities = load_club_facilities(conn, player_club_id, season_id)
    if "film_room" in facilities:
        base = _promote_budget_level(base, 1)
    if "analytics_dept" in facilities:
        base = "high"
    return base


def _award_prestige_for_season(
    conn: sqlite3.Connection,
    season_id: str,
) -> None:
    if get_state(conn, "prestige_awarded_for") == season_id:
        return
    standings = load_standings(conn, season_id)
    for index, row in enumerate(standings):
        bonus = row.wins + row.draws
        if index == 0:
            bonus += 5
        elif index < 4:
            bonus += 2
        current = load_club_prestige(conn, row.club_id)
        save_club_prestige(conn, row.club_id, current + bonus)
    set_state(conn, "prestige_awarded_for", season_id)
    conn.commit()


def _print_scouting_board(
    conn: sqlite3.Connection,
    clubs: Dict[str, Club],
    player_club_id: str,
    next_season_id: str,
    root_seed: int,
    difficulty: str,
) -> None:
    free_agents = load_free_agents(conn)
    budget = _effective_scouting_budget(conn, player_club_id, next_season_id, difficulty)
    _print_divider("=")
    print(f"  Scouting Board — {budget.title()} Budget")
    _print_divider()
    if not free_agents:
        print("  No scouted players available.")
    for player in sorted(free_agents, key=lambda item: (-item.overall(), item.id)):
        report = generate_scout_report(
            player,
            budget,
            DeterministicRNG(derive_seed(root_seed, "scouting", next_season_id, player.id, player_club_id)),
        )
        line = f"  {player.id:<22} {player.name:<18} archetype={report.revealed_archetype:<14}"
        if report.exact_ratings:
            line += (
                f" exact ACC={report.exact_ratings['accuracy']} POW={report.exact_ratings['power']}"
                f" DOD={report.exact_ratings['dodge']} CAT={report.exact_ratings['catch']}"
            )
        elif report.rating_ranges:
            acc = report.rating_ranges["accuracy"]
            pow_ = report.rating_ranges["power"]
            line += f" ranges ACC={acc[0]}-{acc[1]} POW={pow_[0]}-{pow_[1]}"
        print(line)
    _print_divider("=")


def _configure_facilities(
    conn: sqlite3.Connection,
    player_club_id: str,
    next_season_id: str,
) -> None:
    prestige = load_club_prestige(conn, player_club_id)
    current = load_club_facilities(conn, player_club_id, next_season_id)
    refunded_prestige = prestige + sum(
        FACILITY_DEFINITIONS[FacilityType(item)].prestige_cost for item in current
    )
    _print_divider("=")
    print(f"  Facilities — {next_season_id}")
    _print_divider()
    print(f"  Prestige: {prestige}")
    print(f"  Current: {', '.join(current) if current else 'none'}")
    for facility_type, definition in FACILITY_DEFINITIONS.items():
        print(
            f"  {facility_type.value:<18} cost={definition.prestige_cost} "
            f"category={definition.category} name={definition.display_name}"
        )
    raw = input("  Enter up to 3 facility ids separated by commas (blank to cancel): ").strip()
    if not raw:
        return
    try:
        selected = normalize_facility_selection([item.strip() for item in raw.split(",") if item.strip()])
    except ValueError as exc:
        print(f"  {exc}")
        return
    total_cost = sum(FACILITY_DEFINITIONS[item].prestige_cost for item in selected)
    if total_cost > refunded_prestige:
        print(f"  Not enough prestige. Need {total_cost}, have {refunded_prestige}.")
        return
    save_club_facilities(conn, player_club_id, next_season_id, [item.value for item in selected])
    save_club_prestige(conn, player_club_id, refunded_prestige - total_cost)
    conn.commit()
    print("  Facilities saved.")


def _season_newcomer_ids(rosters: Dict[str, List[Player]]) -> frozenset[str]:
    return frozenset(
        player.id
        for roster in rosters.values()
        for player in roster
        if player.newcomer
    )


def _matches_by_player(conn: sqlite3.Connection, season_id: str) -> Dict[str, int]:
    cursor = conn.execute(
        """
        SELECT player_id, COUNT(*) AS matches
        FROM player_match_stats
        WHERE match_id IN (SELECT match_id FROM match_records WHERE season_id = ?)
        GROUP BY player_id
        """,
        (season_id,),
    )
    return {row["player_id"]: row["matches"] for row in cursor.fetchall()}


def _next_season_identity(season) -> tuple[str, int]:
    next_year = season.year + 1
    return f"season_{next_year}", next_year


def _generate_meta_patch_for_season(season, root_seed: int) -> MetaPatch:
    templates = [
        {
            "patch_id": "heavy_ball",
            "name": "Heavy Ball",
            "description": "League-issued weighted balls make power throws more taxing and dodges tighter.",
            "power_stamina_cost_modifier": 0.18,
            "dodge_penalty_modifier": 0.12,
            "fatigue_rate_modifier": 0.08,
            "ruleset_overrides": RuleSetOverrides(),
        },
        {
            "patch_id": "quick_whistle",
            "name": "Quick Whistle",
            "description": "Officials trim the shot clock and keep the ball live, creating a faster season-wide tempo.",
            "power_stamina_cost_modifier": 0.04,
            "dodge_penalty_modifier": 0.04,
            "fatigue_rate_modifier": -0.05,
            "ruleset_overrides": RuleSetOverrides(shot_clock_seconds=18),
        },
        {
            "patch_id": "no_free_revives",
            "name": "No Free Revives",
            "description": "Catch-and-revive rules are suspended, so every elimination carries extra weight.",
            "power_stamina_cost_modifier": 0.06,
            "dodge_penalty_modifier": 0.08,
            "fatigue_rate_modifier": 0.02,
            "ruleset_overrides": RuleSetOverrides(catch_revival_enabled=False),
        },
        {
            "patch_id": "triple_ball",
            "name": "Triple Ball Showcase",
            "description": "The league experiments with three live balls and asks every roster to manage controlled chaos.",
            "power_stamina_cost_modifier": 0.09,
            "dodge_penalty_modifier": 0.05,
            "fatigue_rate_modifier": 0.12,
            "ruleset_overrides": RuleSetOverrides(balls_in_play=3),
        },
    ]
    template = templates[derive_seed(root_seed, "meta_patch", season.season_id, str(season.year)) % len(templates)]
    return MetaPatch(
        patch_id=str(template["patch_id"]),
        season_id=season.season_id,
        name=str(template["name"]),
        description=str(template["description"]),
        power_stamina_cost_modifier=float(template["power_stamina_cost_modifier"]),
        dodge_penalty_modifier=float(template["dodge_penalty_modifier"]),
        fatigue_rate_modifier=float(template["fatigue_rate_modifier"]),
        ruleset_overrides=template["ruleset_overrides"],
    )


def _meta_patch_from_row(payload: Dict[str, object]) -> MetaPatch:
    modifiers = dict(payload.get("modifiers", {}))
    ruleset_overrides = dict(payload.get("ruleset_overrides", {}))
    return MetaPatch(
        patch_id=str(payload["patch_id"]),
        season_id=str(payload["season_id"]),
        name=str(payload["name"]),
        description=str(payload["description"]),
        power_stamina_cost_modifier=float(modifiers.get("power_stamina_cost_modifier", 0.0)),
        dodge_penalty_modifier=float(modifiers.get("dodge_penalty_modifier", 0.0)),
        fatigue_rate_modifier=float(modifiers.get("fatigue_rate_modifier", 0.0)),
        ruleset_overrides=RuleSetOverrides(
            catch_revival_enabled=ruleset_overrides.get("catch_revival_enabled"),
            balls_in_play=ruleset_overrides.get("balls_in_play"),
            shot_clock_seconds=ruleset_overrides.get("shot_clock_seconds"),
        ),
    )


def _cup_bracket_to_payload(bracket: CupBracket) -> Dict[str, object]:
    return {
        "club_ids": list(bracket.club_ids),
        "rounds": [
            {
                "round_number": round_.round_number,
                "matches": [
                    {
                        "match_id": match.match_id,
                        "round_number": match.round_number,
                        "slot_number": match.slot_number,
                        "side_a": {
                            "club_id": match.side_a.club_id,
                            "source_match_id": match.side_a.source_match_id,
                        },
                        "side_b": None if match.side_b is None else {
                            "club_id": match.side_b.club_id,
                            "source_match_id": match.side_b.source_match_id,
                        },
                        "auto_advance_club_id": match.auto_advance_club_id,
                    }
                    for match in round_.matches
                ],
            }
            for round_ in bracket.rounds
        ],
    }


def _ensure_season_artifacts(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
    root_seed: int,
) -> tuple[MetaPatch, Dict[str, object]]:
    patch_row = load_meta_patch(conn, season.season_id)
    if patch_row is None:
        meta_patch = _generate_meta_patch_for_season(season, root_seed)
        save_meta_patch(
            conn,
            season.season_id,
            meta_patch.patch_id,
            meta_patch.name,
            meta_patch.description,
            meta_patch.modifier_summary(),
            meta_patch.ruleset_overrides.explicit_values(),
        )
    else:
        meta_patch = _meta_patch_from_row(patch_row)

    cup_row = load_cup_bracket(conn, season.season_id)
    if cup_row is None:
        bracket = generate_cup_bracket(
            sorted(clubs.keys()),
            DeterministicRNG(derive_seed(root_seed, "cup", season.season_id)),
        )
        cup_id = f"{season.season_id}_midseason_cup"
        bracket_payload = _cup_bracket_to_payload(bracket)
        save_cup_bracket(conn, cup_id, season.season_id, bracket_payload)
        for round_payload in bracket_payload["rounds"]:
            for match in round_payload["matches"]:
                if match["auto_advance_club_id"]:
                    save_cup_result(
                        conn,
                        cup_id,
                        int(round_payload["round_number"]),
                        str(match["match_id"]),
                        str(match["auto_advance_club_id"]),
                    )
        cup_row = load_cup_bracket(conn, season.season_id)

    conn.commit()
    if cup_row is None:
        raise RuntimeError("Failed to initialize season cup bracket")
    return meta_patch, cup_row


def _pick_cup_winner(
    record: MatchRecord,
    rosters: Dict[str, List[Player]],
) -> tuple[str, str | None]:
    if record.result.winner_team_id is not None:
        return record.result.winner_team_id, None
    home_score = record.result.box_score["teams"][record.home_club_id]["totals"]["living"]
    away_score = record.result.box_score["teams"][record.away_club_id]["totals"]["living"]
    if home_score != away_score:
        return (
            record.home_club_id if home_score > away_score else record.away_club_id,
            "survivor tiebreak",
        )
    home_ovr = sum(player.overall() for player in rosters[record.home_club_id])
    away_ovr = sum(player.overall() for player in rosters[record.away_club_id])
    if home_ovr != away_ovr:
        return (
            record.home_club_id if home_ovr > away_ovr else record.away_club_id,
            "overall tiebreak",
        )
    return min(record.home_club_id, record.away_club_id), "seeded tiebreak"


def _award_cup_champion_if_ready(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
) -> None:
    if get_state(conn, "cup_awarded_for") == season.season_id:
        return
    payload = load_cup_bracket(conn, season.season_id)
    if payload is None:
        return
    final_match_id = payload["bracket"]["rounds"][-1]["matches"][0]["match_id"]
    champion = load_cup_results(conn, season.season_id).get(final_match_id)
    if champion is None:
        return
    save_club_trophy(conn, champion, "cup", season.season_id)
    save_club_prestige(conn, champion, load_club_prestige(conn, champion) + 6)
    save_news_headlines(
        conn,
        season.season_id,
        99,
        [
            {
                "headline_id": f"{season.season_id}_cup_champion",
                "category": "cup",
                "headline_text": f"{_club_display_name(clubs, champion)} captured the {season.year} Midseason Cup.",
                "entity_ids": [champion],
            }
        ],
    )
    set_state(conn, "cup_awarded_for", season.season_id)
    conn.commit()


def _simulate_next_cup_round(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    root_seed: int,
    difficulty: str,
    meta_patch: MetaPatch | None,
) -> bool:
    payload = load_cup_bracket(conn, season.season_id)
    if payload is None:
        print("  No cup bracket exists for this season.")
        return False
    cup_id = payload["cup_id"]
    bracket = payload["bracket"]
    results = load_cup_results(conn, season.season_id)
    next_round = None
    for round_payload in bracket["rounds"]:
        if any(match["match_id"] not in results for match in round_payload["matches"]):
            next_round = round_payload
            break
    if next_round is None:
        _award_cup_champion_if_ready(conn, season, clubs)
        print("  Cup is already complete.")
        return False

    print(f"  Simulating Cup Round {next_round['round_number']}...")
    for match in next_round["matches"]:
        if match["match_id"] in results:
            continue
        if match["auto_advance_club_id"]:
            winner = str(match["auto_advance_club_id"])
            save_cup_result(conn, cup_id, int(next_round["round_number"]), str(match["match_id"]), winner)
            print(f"    {match['match_id']}: {_club_display_name(clubs, winner)} advances on a bye")
            continue
        club_a_id = _cup_resolve_side(match["side_a"], results)
        club_b_id = _cup_resolve_side(match["side_b"], results)
        if club_a_id is None or club_b_id is None:
            continue
        scheduled = ScheduledMatch(
            match_id=f"{season.season_id}_{match['match_id']}_{club_a_id}_vs_{club_b_id}",
            season_id=season.season_id,
            week=90 + int(next_round["round_number"]),
            home_club_id=club_a_id,
            away_club_id=club_b_id,
        )
        record, _ = simulate_match(
            scheduled=scheduled,
            home_club=clubs[club_a_id],
            away_club=clubs[club_b_id],
            home_roster=rosters[club_a_id],
            away_roster=rosters[club_b_id],
            root_seed=derive_seed(root_seed, "cup_round", season.season_id, str(match["match_id"])),
            config_version=season.config_version,
            difficulty=difficulty,
            meta_patch=meta_patch,
        )
        winner_id, tiebreak = _pick_cup_winner(record, rosters)
        save_cup_result(conn, cup_id, int(next_round["round_number"]), str(match["match_id"]), winner_id)
        print(
            f"    {match['match_id']}: {_club_display_name(clubs, winner_id)} advanced"
            + (f" via {tiebreak}" if tiebreak else "")
        )
    conn.commit()
    _award_cup_champion_if_ready(conn, season, clubs)
    return True


def _finish_cup_if_needed(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    root_seed: int,
    difficulty: str,
    meta_patch: MetaPatch | None,
) -> None:
    while _simulate_next_cup_round(conn, season, clubs, rosters, root_seed, difficulty, meta_patch):
        pass


def _league_from_current_clubs(season, clubs: Dict[str, Club]) -> League:
    return League(
        league_id=season.league_id,
        name="Dodgeball Premier League",
        conferences=(
            Conference(
                conference_id="conf_1",
                name="Division 1",
                club_ids=tuple(sorted(clubs.keys())),
            ),
        ),
    )


def _ensure_offseason_initialized(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    root_seed: int,
) -> Dict[str, List[Player]]:
    if get_state(conn, "offseason_initialized_for") == season.season_id:
        return rosters

    _award_prestige_for_season(conn, season.season_id)
    season_stats = fetch_season_player_stats(conn, season.season_id)
    updated_rosters: Dict[str, List[Player]] = {}
    development_rows: List[Dict[str, object]] = []
    retirement_rows: List[Dict[str, object]] = []

    for club_id, roster in rosters.items():
        season_facilities = load_club_facilities(conn, club_id, season.season_id)
        next_roster: List[Player] = []
        for player in roster:
            stats = season_stats.get(player.id, PlayerMatchStats())
            developed = apply_season_development(
                player=player,
                season_stats=stats,
                facilities=season_facilities,
                rng=DeterministicRNG(derive_seed(root_seed, "development", season.season_id, player.id)),
            )
            aged = replace(developed, age=developed.age + 1)
            career_summary = fetch_player_career_summary(conn, player.id)
            if should_retire(aged, career_summary):
                save_retired_player(conn, aged, season.season_id, "age_decline")
                retirement_rows.append(
                    {"player_id": aged.id, "age": aged.age, "reason": "age_decline"}
                )
                continue

            development_rows.append(
                {
                    "player_id": aged.id,
                    "before": round(player.overall(), 2),
                    "after": round(aged.overall(), 2),
                    "delta": round(aged.overall() - player.overall(), 2),
                }
            )
            next_roster.append(aged)
        updated_rosters[club_id] = next_roster

    next_season_id, _ = _next_season_identity(season)
    rookie_class = generate_rookie_class(
        next_season_id,
        DeterministicRNG(derive_seed(root_seed, "draft", next_season_id)),
    )
    free_agents = load_free_agents(conn)
    free_agents.extend(rookie_class)

    _save_all_rosters(conn, clubs, updated_rosters)
    _ensure_player_identities(conn, updated_rosters, root_seed)
    save_free_agents(conn, free_agents, next_season_id)
    set_state(conn, "offseason_initialized_for", season.season_id)
    set_state(conn, "offseason_development_json", json.dumps(development_rows))
    set_state(conn, "offseason_retirements_json", json.dumps(retirement_rows))
    conn.commit()
    return updated_rosters


def _release_player_to_pool(
    conn: sqlite3.Connection,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    player_club_id: str,
    player_id: str,
    season_id: str,
) -> bool:
    roster = rosters[player_club_id]
    if len(roster) <= 1:
        print("  Cannot release your last player.")
        return False
    for index, player in enumerate(roster):
        if player.id != player_id:
            continue
        released = replace(player, club_id=None)
        del roster[index]
        free_agents = load_free_agents(conn)
        free_agents.append(released)
        _save_all_rosters(conn, clubs, rosters)
        save_free_agents(conn, free_agents, season_id)
        conn.commit()
        print(f"  Released {player_id} to free agency.")
        return True
    print(f"  Player '{player_id}' not found on your roster.")
    return False


def _sign_free_agent(
    conn: sqlite3.Connection,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    player_club_id: str,
    player_id: str,
    season_id: str,
) -> bool:
    free_agents = load_free_agents(conn)
    for index, player in enumerate(free_agents):
        if player.id != player_id:
            continue
        signed = replace(player, club_id=player_club_id)
        del free_agents[index]
        rosters[player_club_id].append(signed)
        _save_all_rosters(conn, clubs, rosters)
        save_free_agents(conn, free_agents, season_id)
        conn.commit()
        print(f"  Signed {player_id}.")
        return True
    print(f"  Free agent '{player_id}' not found.")
    return False


def _advance_to_next_season(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    root_seed: int,
    difficulty: str,
    meta_patch: MetaPatch | None,
):
    _finish_cup_if_needed(conn, season, clubs, rosters, root_seed, difficulty, meta_patch)
    next_season_id, next_year = _next_season_identity(season)
    next_season = create_season(
        season_id=next_season_id,
        year=next_year,
        league=_league_from_current_clubs(season, clubs),
        root_seed=root_seed,
        config_version=season.config_version,
        ruleset_version=season.ruleset_version,
    )
    save_season(conn, next_season)
    _save_all_rosters(conn, clubs, rosters)
    set_state(conn, "active_season_id", next_season.season_id)
    set_state(conn, "offseason_initialized_for", "")
    set_state(conn, "cup_awarded_for", "")
    conn.commit()
    print(f"\n  Advanced to {next_season.season_id}. A new schedule is ready.\n")
    return next_season


# ---------------------------------------------------------------------------
# Main dynasty menu loop
# ---------------------------------------------------------------------------

def dynasty_menu_loop(conn: sqlite3.Connection, difficulty: str) -> None:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    root_seed_str = get_state(conn, "root_seed", "12345")
    root_seed = int(root_seed_str)

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    player_club = clubs.get(player_club_id)
    club_display = player_club.name if player_club else player_club_id

    while True:
        meta_patch, _ = _ensure_season_artifacts(conn, season, clubs, root_seed)
        completed = load_completed_match_ids(conn, season_id)
        week = _current_week(season, completed)
        total = season.total_weeks()
        status = f"Week {week}/{total}" if week else "Season Complete"
        if week is None:
            if not load_awards(conn, season_id):
                _finalize_and_save_awards(conn, season, clubs, rosters)
            rosters = _ensure_offseason_initialized(conn, season, clubs, rosters, root_seed)

        print(f"\n=== Dodgeball Manager — Dynasty ===")
        print(f"  Season: {season_id}  |  Club: {club_display}  |  {status}")
        _print_divider()
        if week:
            print("  [s]chedule   [n]ext match   [m]atchday   [t]standings   [sum]mary")
            print("  [cup] bracket   [cup sim] next cup round   [patch] season rules   [q]uit")
            print(f"  (Current: Week {week} — {len([m for m in season.matches_for_week(week) if m.match_id not in completed])} match(es) pending)")
        else:
            print("  [sum]mary   [dev] report   [r]oster   [fa] free agents   [scout]")
            print("  [fac]ilities   [wire] news   [hof]   [rec]ords   [riv]alries")
            print("  [cup] bracket   [cup sim] next cup round   [patch] season rules")
            print("  [p <id>] player page   [rel <id>] release   [sign <id>] sign   [adv]ance season   [q]uit")
        choice = input("  > ").strip().lower()

        if not choice:
            continue

        if choice == "q":
            print("Exiting dynasty. Progress saved.")
            return

        if choice == "s":
            _show_schedule(season, clubs, completed, player_club_id)
            continue

        if choice == "t":
            standings = load_standings(conn, season_id)
            if standings:
                _print_standings(standings, clubs)
            else:
                print("  No standings yet — sim some matches first.")
            continue

        if choice == "sum":
            standings = load_standings(conn, season_id)
            awards = load_awards(conn, season_id)
            if not standings:
                print("  No season data yet.")
            else:
                _print_season_summary(season_id, standings, awards, clubs)
            continue

        if choice == "patch":
            _print_meta_patch(meta_patch)
            continue

        if choice == "cup":
            _print_cup_bracket(conn, season_id, clubs)
            continue

        if choice == "cup sim":
            _simulate_next_cup_round(conn, season, clubs, rosters, root_seed, difficulty, meta_patch)
            continue

        if week is None and choice in ("dev", "report"):
            _print_offseason_report(conn)
            continue

        if week is None and choice == "r":
            _print_roster(conn, clubs[player_club_id], rosters[player_club_id])
            continue

        if week is None and choice == "fa":
            _print_free_agents(load_free_agents(conn))
            continue

        if week is None and choice == "scout":
            next_season_id, _ = _next_season_identity(season)
            _print_scouting_board(conn, clubs, player_club_id, next_season_id, root_seed, difficulty)
            continue

        if week is None and choice == "fac":
            next_season_id, _ = _next_season_identity(season)
            _configure_facilities(conn, player_club_id, next_season_id)
            continue

        if choice in ("wire", "news"):
            _print_league_wire(conn, season_id)
            continue

        if choice in ("hof", "hall"):
            _print_hall_of_fame(conn)
            continue

        if choice in ("rec", "records"):
            _print_record_book(conn)
            continue

        if choice in ("riv", "rivalries"):
            _print_rivalries(conn, clubs)
            continue

        if choice.startswith("p "):
            target_id = choice[2:].strip()
            target_player = next(
                (
                    player
                    for roster in list(rosters.values()) + [load_free_agents(conn)]
                    for player in roster
                    if player.id == target_id
                ),
                None,
            )
            if target_player is None:
                print(f"  Player '{target_id}' not found.")
            else:
                _print_player_page(conn, target_player, _club_display_name(clubs, target_player.club_id or "free_agents"))
            continue

        if week is None and choice.startswith("rel "):
            _release_player_to_pool(conn, clubs, rosters, player_club_id, choice[4:].strip(), season.season_id)
            rosters = load_all_rosters(conn)
            continue

        if week is None and choice.startswith("sign "):
            _sign_free_agent(conn, clubs, rosters, player_club_id, choice[5:].strip(), season.season_id)
            rosters = load_all_rosters(conn)
            continue

        if week is None and choice in ("adv", "advance", "advance season"):
            season = _advance_to_next_season(conn, season, clubs, rosters, root_seed, difficulty, meta_patch)
            season_id = season.season_id
            rosters = load_all_rosters(conn)
            continue

        if choice in ("n", "next match"):
            if week is None:
                print("  Season is already complete.")
                continue
            pending = [
                m for m in season.matches_for_week(week)
                if m.match_id not in completed
            ]
            # Prefer the user's club match; fall back to first pending
            user_match = next(
                (m for m in pending if m.home_club_id == player_club_id or m.away_club_id == player_club_id),
                pending[0] if pending else None,
            )
            if user_match is None:
                print("  Nothing to sim.")
                continue

            records = _do_sim_matches(conn, [user_match], clubs, rosters, root_seed, difficulty, season_id, meta_patch)
            _recompute_and_save_standings(conn, season, season_id, clubs, rosters)
            for record in records:
                home_r = rosters[record.home_club_id]
                away_r = rosters[record.away_club_id]
                stats = extract_match_stats(record, home_r, away_r)
                _print_match_report(record, clubs, stats)

            # Check if season complete after this match
            completed = load_completed_match_ids(conn, season_id)
            if _current_week(season, completed) is None:
                _finalize_and_save_awards(conn, season, clubs, rosters)
            continue

        if choice in ("m", "matchday"):
            if week is None:
                print("  Season is already complete.")
                continue
            pending = [
                m for m in season.matches_for_week(week)
                if m.match_id not in completed
            ]
            if not pending:
                print(f"  Week {week} already complete.")
                continue
            print(f"  Simulating {len(pending)} match(es) for Week {week}...")
            records = _do_sim_matches(conn, pending, clubs, rosters, root_seed, difficulty, season_id, meta_patch)
            _recompute_and_save_standings(conn, season, season_id, clubs, rosters)
            for record in records:
                home_r = rosters[record.home_club_id]
                away_r = rosters[record.away_club_id]
                stats = extract_match_stats(record, home_r, away_r)
                _print_match_report(record, clubs, stats)

            completed = load_completed_match_ids(conn, season_id)
            if _current_week(season, completed) is None:
                _finalize_and_save_awards(conn, season, clubs, rosters)
            continue

        if choice.startswith("v "):
            target_id = choice[2:].strip()
            _show_match_by_id(conn, target_id, clubs, rosters)
            continue

        print("  Unknown option.")


def _recompute_and_save_standings(
    conn: sqlite3.Connection,
    season,
    season_id: str,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
) -> None:
    """Re-derive standings from match_records for this season and persist."""
    cursor = conn.execute(
        """
        SELECT match_id, season_id, week, home_club_id, away_club_id,
               winner_club_id, home_survivors, away_survivors, seed
        FROM match_records WHERE season_id = ?
        """,
        (season_id,),
    )
    results = [
        SeasonResult(
            match_id=row["match_id"],
            season_id=row["season_id"],
            week=row["week"],
            home_club_id=row["home_club_id"],
            away_club_id=row["away_club_id"],
            home_survivors=row["home_survivors"],
            away_survivors=row["away_survivors"],
            winner_club_id=row["winner_club_id"],
            seed=row["seed"],
        )
        for row in cursor.fetchall()
    ]
    standings = compute_standings(results)
    save_standings(conn, season_id, standings)
    conn.commit()


def _career_rows_for_player(conn: sqlite3.Connection, player_id: str) -> List[Dict[str, object]]:
    cursor = conn.execute(
        """
        SELECT pss.*, CASE
            WHEN s.club_id = (
                SELECT club_id FROM season_standings
                WHERE season_id = pss.season_id
                ORDER BY points DESC, elimination_differential DESC, club_id ASC
                LIMIT 1
            ) THEN 1 ELSE 0 END AS champion
        FROM player_season_stats pss
        LEFT JOIN season_standings s
            ON s.season_id = pss.season_id AND s.club_id = pss.club_id
        WHERE pss.player_id = ?
        ORDER BY pss.season_id
        """,
        (player_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def _seasons_at_one_club(rows: List[Dict[str, object]]) -> int:
    counts: Dict[str, int] = {}
    for row in rows:
        club_id = str(row.get("club_id") or "")
        if not club_id:
            continue
        counts[club_id] = counts.get(club_id, 0) + 1
    return max(counts.values(), default=0)


def _update_story_and_history(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
) -> None:
    standings = load_standings(conn, season.season_id)
    awards = load_awards(conn, season.season_id)
    current_records_map = {
        item["record_type"]: LeagueRecord(
            record_type=item["record_type"],
            holder_id=item["holder_id"],
            holder_type=item["holder_type"],
            holder_name=item["record"].get("holder_name", item["holder_id"]),
            value=float(item["record_value"]),
            set_in_season=item["set_in_season"],
            detail=item["record"].get("detail", ""),
        )
        for item in load_league_records(conn)
    }

    player_lookup = {
        player.id: player
        for roster in rosters.values()
        for player in roster
    }

    for player in player_lookup.values():
        _ensure_player_identities(conn, {player.club_id or "free_agents": [player]}, int(get_state(conn, "root_seed", "12345")))

    for award in awards:
        save_signature_moment(
            conn,
            moment_id=f"{season.season_id}_{award.player_id}_{award.award_type}",
            player_id=award.player_id,
            season_id=season.season_id,
            match_id=None,
            moment_type=award.award_type,
            description=f"Won {award.award_type.replace('_', ' ')} for {season.season_id}.",
        )

    champion_id = standings[0].club_id if standings else None
    for player_id, player in player_lookup.items():
        season_rows = _career_rows_for_player(conn, player_id)
        season_awards = [
            {"award_type": award.award_type}
            for award in awards
            if award.player_id == player_id
        ]
        signature_rows = [
            build_signature_moment(
                season_id=moment["season_id"],
                match_id=moment["match_id"] or "season",
                label=moment["moment_type"],
                description=moment["description"],
                leverage=1.5 if moment["moment_type"] == "mvp" else 1.0,
                clutch_bonus=2.0 if moment["moment_type"] == "mvp" else 1.0,
            )
            for moment in load_signature_moments(conn, player_id)
        ]
        summary = aggregate_career(
            player_id=player_id,
            player_name=player.name,
            season_rows=season_rows,
            awards=season_awards,
            signature_moments=signature_rows,
        )
        summary_payload = {
            "player_id": summary.player_id,
            "player_name": summary.player_name,
            "seasons_played": summary.seasons_played,
            "championships": summary.championships,
            "awards_won": summary.awards_won,
            "total_matches": summary.total_matches,
            "total_eliminations": summary.total_eliminations,
            "total_catches_made": summary.total_catches_made,
            "total_dodges_successful": summary.total_dodges_successful,
            "total_times_eliminated": summary.total_times_eliminated,
            "peak_eliminations": summary.peak_eliminations,
            "legacy_score": summary.legacy_score,
            "career_eliminations": summary.total_eliminations,
            "career_catches": summary.total_catches_made,
            "career_dodges": summary.total_dodges_successful,
            "clubs_served": len({row.get('club_id') for row in season_rows if row.get('club_id')}),
        }
        save_player_career_stats(conn, player_id, summary_payload)
        hof_case = evaluate_hall_of_fame(summary)
        if hof_case.inducted:
            save_hall_of_fame_entry(conn, player_id, season.season_id, summary_payload)

    career_stats = [
        RecordCareerStats(
            player_id=player.id,
            player_name=player.name,
            club_id=player.club_id,
            career_eliminations=int((load_player_career_stats(conn, player.id) or {}).get("career_eliminations", 0)),
            career_catches=int((load_player_career_stats(conn, player.id) or {}).get("career_catches", 0)),
            career_dodges=int((load_player_career_stats(conn, player.id) or {}).get("career_dodges", 0)),
            seasons_at_one_club=_seasons_at_one_club(_career_rows_for_player(conn, player.id)),
            championships=int((load_player_career_stats(conn, player.id) or {}).get("championships", 0)),
        )
        for player in player_lookup.values()
        if load_player_career_stats(conn, player.id)
    ]

    team_stats = [
        TeamRecordStats(
            club_id=row.club_id,
            club_name=_club_display_name(clubs, row.club_id),
            titles=1 if row.club_id == champion_id else 0,
            unbeaten_run=row.wins + row.draws,
        )
        for row in standings
    ]

    cursor = conn.execute(
        """
        SELECT home_club_id, away_club_id, winner_club_id, home_survivors, away_survivors, match_id
        FROM match_records
        WHERE season_id = ?
        ORDER BY week, match_id
        """,
        (season.season_id,),
    )
    rivalry_map = {
        frozenset((item["club_a_id"], item["club_b_id"])): RivalryRecord(**item["rivalry"])
        for item in load_rivalry_records(conn)
    }
    matchup_results: List[MatchdayResult] = []
    upset_results: List[UpsetResult] = []

    for row in cursor.fetchall():
        home_roster = rosters[row["home_club_id"]]
        away_roster = rosters[row["away_club_id"]]
        home_ovr = sum(player.overall() for player in home_roster) / max(1, len(home_roster))
        away_ovr = sum(player.overall() for player in away_roster) / max(1, len(away_roster))
        winner_id = row["winner_club_id"] or row["home_club_id"]
        loser_id = row["away_club_id"] if winner_id == row["home_club_id"] else row["home_club_id"]
        winner_score = row["home_survivors"] if winner_id == row["home_club_id"] else row["away_survivors"]
        loser_score = row["away_survivors"] if winner_id == row["home_club_id"] else row["home_survivors"]
        winner_ovr = home_ovr if winner_id == row["home_club_id"] else away_ovr
        loser_ovr = away_ovr if winner_id == row["home_club_id"] else home_ovr
        gap = loser_ovr - winner_ovr
        if gap > 0:
            upset_results.append(
                UpsetResult(
                    match_id=row["match_id"],
                    season_id=season.season_id,
                    winner_club_id=winner_id,
                    winner_club_name=_club_display_name(clubs, winner_id),
                    loser_club_id=loser_id,
                    loser_club_name=_club_display_name(clubs, loser_id),
                    winner_overall=winner_ovr,
                    loser_overall=loser_ovr,
                )
            )
        key = frozenset((row["home_club_id"], row["away_club_id"]))
        record = rivalry_map.get(
            key,
            RivalryRecord(
                club_a_id=min(row["home_club_id"], row["away_club_id"]),
                club_b_id=max(row["home_club_id"], row["away_club_id"]),
            ),
        )
        updated = update_rivalry(
            record,
            RivalryMatchResult(
                match_id=row["match_id"],
                season_id=season.season_id,
                club_a_id=row["home_club_id"],
                club_b_id=row["away_club_id"],
                winner_club_id=row["winner_club_id"],
                score_margin=abs(row["home_survivors"] - row["away_survivors"]),
                notable_moment="title path clash" if champion_id in key else "",
            ),
        )
        rivalry_payload = {
            "club_a_id": updated.club_a_id,
            "club_b_id": updated.club_b_id,
            "a_wins": updated.a_wins,
            "b_wins": updated.b_wins,
            "draws": updated.draws,
            "total_meetings": updated.total_meetings,
            "total_margin": updated.total_margin,
            "playoff_meetings": updated.playoff_meetings,
            "championship_meetings": updated.championship_meetings,
            "last_winner_club_id": updated.last_winner_club_id,
            "last_meeting_season": updated.last_meeting_season,
            "defining_moments": list(updated.defining_moments),
            "rivalry_score": compute_rivalry_score(updated),
        }
        save_rivalry_record(conn, updated.club_a_id, updated.club_b_id, rivalry_payload)
        rivalry_map[key] = updated
        matchup_results.append(
            MatchdayResult(
                match_id=row["match_id"],
                season_id=season.season_id,
                week=0,
                winner_club_id=winner_id,
                winner_club_name=_club_display_name(clubs, winner_id),
                loser_club_id=loser_id,
                loser_club_name=_club_display_name(clubs, loser_id),
                winner_score=winner_score,
                loser_score=loser_score,
                winner_pre_match_overall=winner_ovr,
                loser_pre_match_overall=loser_ovr,
                flashpoint_text="the rivalry score climbed again" if compute_rivalry_score(updated) >= 40 else "",
            )
        )

    broken_records = check_records_broken(
        {
            "season_id": season.season_id,
            "team_stats": team_stats,
            "upset_results": upset_results,
        },
        career_stats,
        current_records_map,
    )
    for record in broken_records:
        save_league_record(
            conn,
            record.record_type,
            record.holder_id,
            record.holder_type,
            record.new_value,
            record.set_in_season,
            {
                "record_type": record.record_type,
                "holder_id": record.holder_id,
                "holder_name": record.holder_name,
                "holder_type": record.holder_type,
                "record_value": record.new_value,
                "set_in_season": record.set_in_season,
                "detail": record.detail,
            },
        )

    headlines = generate_matchday_news(
        matchup_results,
        broken_records,
        rivalry_map.values(),
    )
    save_news_headlines(
        conn,
        season.season_id,
        0,
        [
            {
                "headline_id": f"{season.season_id}_headline_{index}",
                "category": headline.category,
                "headline_text": headline.text,
                "entity_ids": list(headline.entity_ids),
            }
            for index, headline in enumerate(headlines, 1)
        ],
    )
    conn.commit()


def _finalize_and_save_awards(
    conn: sqlite3.Connection,
    season,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
) -> None:
    """Compute and persist season awards when season is complete."""
    season_stats = fetch_season_player_stats(conn, season.season_id)
    if not season_stats:
        return

    # Build player→club map from player_match_stats
    cursor = conn.execute(
        "SELECT DISTINCT player_id, club_id FROM player_match_stats WHERE match_id IN "
        "(SELECT match_id FROM match_records WHERE season_id = ?)",
        (season.season_id,),
    )
    player_club_map = {row["player_id"]: row["club_id"] for row in cursor.fetchall()}

    newcomer_ids = _season_newcomer_ids(rosters)
    matches_by_player = _matches_by_player(conn, season.season_id)

    awards = compute_season_awards(
        season_id=season.season_id,
        player_season_stats=season_stats,
        player_club_map=player_club_map,
        newcomer_player_ids=newcomer_ids,
    )
    save_awards(conn, awards)
    save_player_season_stats(
        conn,
        season.season_id,
        season_stats,
        player_club_map,
        matches_by_player,
        newcomer_ids,
    )
    _update_story_and_history(conn, season, clubs, rosters)
    conn.commit()
    print("\n  Season awards have been saved.")


def _show_schedule(season, clubs: Dict[str, Club], completed: Set[str], player_club_id: str) -> None:
    _print_divider("=")
    print(f"  Season Schedule — {season.season_id}")
    _print_divider()
    for week in range(1, season.total_weeks() + 1):
        print(f"  Week {week}:")
        for m in season.matches_for_week(week):
            home = clubs.get(m.home_club_id, Club(m.home_club_id, m.home_club_id, "", "", 0)).name
            away = clubs.get(m.away_club_id, Club(m.away_club_id, m.away_club_id, "", "", 0)).name
            done = "[DONE]" if m.match_id in completed else "      "
            mine = " *" if player_club_id in (m.home_club_id, m.away_club_id) else "  "
            print(f"  {done}{mine}  {home} vs {away}")
    _print_divider("=")


def _show_match_by_id(
    conn: sqlite3.Connection,
    match_id: str,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
) -> None:
    row = conn.execute(
        "SELECT * FROM match_records WHERE match_id = ?", (match_id,)
    ).fetchone()
    if row is None:
        print(f"  Match '{match_id}' not found or not yet played.")
        return

    home_id = row["home_club_id"]
    away_id = row["away_club_id"]
    home_name = clubs[home_id].name if home_id in clubs else home_id
    away_name = clubs[away_id].name if away_id in clubs else away_id

    # Load stats from DB
    stats_cur = conn.execute(
        "SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,)
    )
    stats: Dict = {}
    for s in stats_cur.fetchall():
        stats[s["player_id"]] = PlayerMatchStats(
            throws_attempted=s["throws_attempted"],
            throws_on_target=s["throws_on_target"],
            eliminations_by_throw=s["eliminations_by_throw"],
            catches_attempted=s["catches_attempted"],
            catches_made=s["catches_made"],
            times_targeted=s["times_targeted"],
            dodges_successful=s["dodges_successful"],
            times_hit=s["times_hit"],
            times_eliminated=s["times_eliminated"],
            revivals_caused=s["revivals_caused"],
            clutch_events=s["clutch_events"],
            elimination_plus_minus=s["elimination_plus_minus"],
            minutes_played=s["minutes_played"],
        )

    _print_divider("=")
    print(f"  Match Report: {match_id}")
    print(f"  {home_name} vs {away_name}  (Week {row['week']})")
    _print_divider()
    if stats:
        print("  Player stats:")
        for pid, s in sorted(stats.items()):
            print(
                f"    {pid:<24}  elims={s.eliminations_by_throw}  catches={s.catches_made}"
                f"  dodges={s.dodges_successful}  hit={s.times_hit}"
            )
    _print_divider("=")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def dynasty_main(conn: sqlite3.Connection, *, difficulty: str = "pro") -> None:
    """Main dynasty entry point. Creates or resumes a dynasty."""
    existing_season = get_state(conn, "active_season_id")

    if existing_season is None:
        import random
        root_seed = random.randint(1, 999_999)
        _create_new_dynasty(conn, root_seed=root_seed)

    dynasty_menu_loop(conn, difficulty)


__all__ = ["dynasty_main"]
