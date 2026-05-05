from __future__ import annotations

"""Dynasty lifecycle orchestrator.

franchise.py owns all season state transitions. Every other module is a pure
function called by franchise.py. persistence.py is the only I/O boundary —
franchise.py fetches data in, calls pure functions, and writes results out.

Phase 2 scope: schedule generation → matchday sim → standings → season summary.
Offseason, development, and recruitment are Phase 3 additions.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .awards import SeasonAward, aggregate_season_stats, compute_season_awards
from .engine import MatchEngine, MatchResult
from .league import Club, League
from .lineup import STARTERS_COUNT, LineupResolver
from .meta import MetaPatch
from .models import MatchSetup, Player, Team
from .rng import derive_seed
from .scheduler import ScheduledMatch, generate_round_robin
from .season import Season, SeasonResult, StandingsRow, compute_standings
from .stats import PlayerMatchStats, extract_all_stats


# ---------------------------------------------------------------------------
# Match snapshot helpers
# ---------------------------------------------------------------------------

def build_match_team_snapshot(
    club: Club,
    roster: List[Player],
    lineup: List[str],
) -> Team:
    """Convert a Club + lineup into an immutable Team for MatchEngine.

    This is the only function that bridges Club (dynasty) and Team (engine).
    The incoming lineup may be a full ordered roster; only active starters enter.
    """
    active_ids = LineupResolver().active_starters(lineup)
    by_id = {player.id: player for player in roster}
    players = [by_id[player_id] for player_id in active_ids if player_id in by_id]
    return Team(
        id=club.club_id,
        name=club.name,
        players=tuple(players),
        coach_policy=club.coach_policy,
        chemistry=0.5,  # TODO: derive from roster relationships in Phase 4
    )


def _hash_players(players: List[Player]) -> str:
    payload = json.dumps(
        [{"id": p.id, "age": p.age, "ratings": {
            "accuracy": p.ratings.accuracy,
            "power": p.ratings.power,
            "dodge": p.ratings.dodge,
            "catch": p.ratings.catch,
            "stamina": p.ratings.stamina,
        }} for p in sorted(players, key=lambda p: p.id)],
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _hash_events(result: MatchResult) -> str:
    payload = json.dumps(
        [e.to_dict() for e in result.events],
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Season simulation
# ---------------------------------------------------------------------------

@dataclass
class MatchRecord:
    """Dynasty-layer record of a completed match."""
    match_id: str
    season_id: str
    week: int
    home_club_id: str
    away_club_id: str
    home_roster_hash: str
    away_roster_hash: str
    config_version: str
    ruleset_version: str
    meta_patch_id: str | None
    seed: int
    event_log_hash: str
    final_state_hash: str
    engine_match_id: Optional[int]
    result: MatchResult       # in-memory only; not persisted as a field
    home_active_player_ids: List[str] = field(default_factory=list)
    away_active_player_ids: List[str] = field(default_factory=list)


def simulate_match(
    scheduled: ScheduledMatch,
    home_club: Club,
    away_club: Club,
    home_roster: List[Player],
    away_roster: List[Player],
    root_seed: int,
    config_version: str = "phase1.v1",
    difficulty: str = "pro",
    meta_patch: MetaPatch | None = None,
    home_lineup_default: Optional[List[str]] = None,
    away_lineup_default: Optional[List[str]] = None,
    home_lineup_override: Optional[List[str]] = None,
    away_lineup_override: Optional[List[str]] = None,
) -> Tuple[MatchRecord, SeasonResult]:
    """Run one match and produce a MatchRecord + SeasonResult. Pure computation.

    With no lineup args, resolution produces the previous full-roster order.
    """
    resolver = LineupResolver()
    home_lineup = resolver.resolve(home_roster, home_lineup_default, home_lineup_override)
    away_lineup = resolver.resolve(away_roster, away_lineup_default, away_lineup_override)
    home_active_starters = resolver.active_starters(home_lineup)
    away_active_starters = resolver.active_starters(away_lineup)
    match_seed = derive_seed(root_seed, "match", scheduled.match_id)

    home_team = build_match_team_snapshot(home_club, home_roster, home_active_starters)
    away_team = build_match_team_snapshot(away_club, away_roster, away_active_starters)

    setup = MatchSetup(team_a=home_team, team_b=away_team, config_version=config_version)
    engine = MatchEngine()
    result = engine.run(setup, seed=match_seed, difficulty=difficulty, meta_patch=meta_patch)

    home_hash = _hash_players(home_roster)
    away_hash = _hash_players(away_roster)
    event_hash = _hash_events(result)
    final_hash = hashlib.sha256(
        json.dumps(result.box_score, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()[:16]

    # Determine survivors
    box = result.box_score["teams"]
    home_survivors = box[home_club.club_id]["totals"]["living"]
    away_survivors = box[away_club.club_id]["totals"]["living"]
    winner_club_id = result.winner_team_id  # team_id == club_id by convention

    record = MatchRecord(
        match_id=scheduled.match_id,
        season_id=scheduled.season_id,
        week=scheduled.week,
        home_club_id=scheduled.home_club_id,
        away_club_id=scheduled.away_club_id,
        home_roster_hash=home_hash,
        away_roster_hash=away_hash,
        config_version=config_version,
        ruleset_version="default.v1",
        meta_patch_id=None if meta_patch is None else meta_patch.patch_id,
        seed=match_seed,
        event_log_hash=event_hash,
        final_state_hash=final_hash,
        engine_match_id=None,
        home_active_player_ids=list(home_active_starters),
        away_active_player_ids=list(away_active_starters),
        result=result,
    )

    season_result = SeasonResult(
        match_id=scheduled.match_id,
        season_id=scheduled.season_id,
        week=scheduled.week,
        home_club_id=scheduled.home_club_id,
        away_club_id=scheduled.away_club_id,
        home_survivors=home_survivors,
        away_survivors=away_survivors,
        winner_club_id=winner_club_id,
        seed=match_seed,
    )

    return record, season_result


def simulate_matchday(
    matches: List[ScheduledMatch],
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    root_seed: int,
    config_version: str = "phase1.v1",
    difficulty: str = "pro",
    meta_patch: MetaPatch | None = None,
) -> Tuple[List[MatchRecord], List[SeasonResult]]:
    """Simulate all matches for one matchday. Pure computation."""
    records: List[MatchRecord] = []
    results: List[SeasonResult] = []
    for scheduled in matches:
        record, result = simulate_match(
            scheduled=scheduled,
            home_club=clubs[scheduled.home_club_id],
            away_club=clubs[scheduled.away_club_id],
            home_roster=rosters[scheduled.home_club_id],
            away_roster=rosters[scheduled.away_club_id],
            root_seed=root_seed,
            config_version=config_version,
            difficulty=difficulty,
            meta_patch=meta_patch,
        )
        records.append(record)
        results.append(result)
    return records, results


def simulate_full_season(
    season: Season,
    clubs: Dict[str, Club],
    rosters: Dict[str, List[Player]],
    root_seed: int,
    config_version: str = "phase1.v1",
    difficulty: str = "pro",
    meta_patch: MetaPatch | None = None,
) -> Tuple[List[MatchRecord], List[SeasonResult], List[StandingsRow]]:
    """Simulate every match in a season and return records, results, standings."""
    all_records: List[MatchRecord] = []
    all_results: List[SeasonResult] = []

    for week in range(1, season.total_weeks() + 1):
        week_matches = season.matches_for_week(week)
        records, results = simulate_matchday(
            week_matches, clubs, rosters, root_seed, config_version, difficulty, meta_patch
        )
        all_records.extend(records)
        all_results.extend(results)

    standings = compute_standings(all_results)
    return all_records, all_results, standings


# ---------------------------------------------------------------------------
# Season factory
# ---------------------------------------------------------------------------

def create_season(
    season_id: str,
    year: int,
    league: League,
    root_seed: int,
    config_version: str = "phase1.v1",
    ruleset_version: str = "default.v1",
) -> Season:
    """Generate a Season with a deterministic round-robin schedule. Pure."""
    schedule = generate_round_robin(
        club_ids=league.all_club_ids(),
        root_seed=root_seed,
        season_id=season_id,
        league_id=league.league_id,
    )
    return Season(
        season_id=season_id,
        year=year,
        league_id=league.league_id,
        config_version=config_version,
        ruleset_version=ruleset_version,
        scheduled_matches=tuple(schedule),
    )


# ---------------------------------------------------------------------------
# Stats extraction helper (bridges engine output → stat schema)
# ---------------------------------------------------------------------------

def extract_match_stats(
    record: MatchRecord,
    home_roster: List[Player],
    away_roster: List[Player],
) -> Dict[str, PlayerMatchStats]:
    """Extract PlayerMatchStats for all players from a completed MatchRecord."""
    home_club_id = record.home_club_id
    away_club_id = record.away_club_id
    home_active_player_ids = record.home_active_player_ids or [p.id for p in home_roster]
    away_active_player_ids = record.away_active_player_ids or [p.id for p in away_roster]
    return extract_all_stats(
        events=list(record.result.events),
        team_a_id=home_club_id,
        team_b_id=away_club_id,
        team_a_player_ids=home_active_player_ids,
        team_b_player_ids=away_active_player_ids,
    )


def trim_ai_roster_for_offseason(
    roster: List[Player],
    max_size: int = 9,
) -> Tuple[List[Player], List[Player]]:
    """Release lowest-value bench players until an AI roster reaches max_size."""
    if len(roster) <= max_size:
        return list(roster), []
    protected = list(roster[:STARTERS_COUNT])
    bench = list(roster[STARTERS_COUNT:])
    release_count = min(len(roster) - max_size, len(bench))
    release_ids = {
        player.id
        for player in sorted(bench, key=lambda player: (_ai_retention_score(player), player.id))[:release_count]
    }
    kept = protected + [player for player in bench if player.id not in release_ids]
    released = [player for player in bench if player.id in release_ids]
    return kept, released


def _ai_retention_score(player: Player) -> float:
    potential = float(player.traits.potential)
    overall = player.overall()
    if player.age <= 22:
        score = overall * 0.60 + potential * 0.40
    else:
        score = overall * 0.85 + potential * 0.15
    if player.age >= 30:
        score -= (player.age - 29) * 1.5
    return round(score, 4)


__all__ = [
    "MatchRecord",
    "build_match_team_snapshot",
    "create_season",
    "trim_ai_roster_for_offseason",
    "simulate_match",
    "simulate_matchday",
    "simulate_full_season",
    "extract_match_stats",
]
