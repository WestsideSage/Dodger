from __future__ import annotations

import sqlite3
from typing import Mapping, Sequence

from .franchise import MatchRecord, extract_match_stats, simulate_match
from .league import Club
from .models import MatchSetup, Player, Team
from .persistence import (
    get_state,
    load_completed_match_ids,
    load_lineup_default,
    load_match_lineup_override,
    record_match,
    record_roster_snapshot,
    save_match_result,
    save_player_stats_batch,
    save_standings,
)
from .scheduler import ScheduledMatch
from .season import Season, SeasonResult, compute_standings


def current_week(conn: sqlite3.Connection, season: Season) -> int | None:
    completed = load_completed_match_ids(conn, season.season_id)
    for week in range(1, season.total_weeks() + 1):
        if any(match.match_id not in completed for match in season.matches_for_week(week)):
            return week
    return None


def simulate_scheduled_match(
    conn: sqlite3.Connection,
    *,
    scheduled: ScheduledMatch,
    clubs: Mapping[str, Club],
    rosters: Mapping[str, Sequence[Player]],
    root_seed: int,
    difficulty: str,
    record_engine_match: bool = True,
) -> MatchRecord:
    home_default = load_lineup_default(conn, scheduled.home_club_id)
    away_default = load_lineup_default(conn, scheduled.away_club_id)
    home_override = load_match_lineup_override(conn, scheduled.match_id, scheduled.home_club_id)
    away_override = load_match_lineup_override(conn, scheduled.match_id, scheduled.away_club_id)
    record, _ = simulate_match(
        scheduled=scheduled,
        home_club=clubs[scheduled.home_club_id],
        away_club=clubs[scheduled.away_club_id],
        home_roster=list(rosters[scheduled.home_club_id]),
        away_roster=list(rosters[scheduled.away_club_id]),
        root_seed=root_seed,
        difficulty=difficulty,
        home_lineup_default=home_default,
        away_lineup_default=away_default,
        home_lineup_override=home_override,
        away_lineup_override=away_override,
    )
    persist_match_record(
        conn,
        record,
        clubs=clubs,
        rosters=rosters,
        difficulty=difficulty,
        record_engine_match=record_engine_match,
    )
    return record


def persist_match_record(
    conn: sqlite3.Connection,
    record: MatchRecord,
    *,
    clubs: Mapping[str, Club],
    rosters: Mapping[str, Sequence[Player]],
    difficulty: str | None = None,
    record_engine_match: bool = True,
) -> int | None:
    home_active_ids = record.home_active_player_ids or list(
        record.result.box_score["teams"][record.home_club_id]["players"].keys()
    )
    away_active_ids = record.away_active_player_ids or list(
        record.result.box_score["teams"][record.away_club_id]["players"].keys()
    )
    setup = MatchSetup(
        team_a=_team_snapshot_for_ids(
            clubs[record.home_club_id],
            rosters[record.home_club_id],
            home_active_ids,
        ),
        team_b=_team_snapshot_for_ids(
            clubs[record.away_club_id],
            rosters[record.away_club_id],
            away_active_ids,
        ),
    )
    engine_match_id = None
    if record_engine_match:
        engine_match_id = record_match(
            conn,
            setup=setup,
            result=record.result,
            difficulty=difficulty or get_state(conn, "difficulty", "pro") or "pro",
        )

    box = record.result.box_score["teams"]
    record_roster_snapshot(
        conn,
        match_id=record.match_id,
        club_id=record.home_club_id,
        players=list(rosters[record.home_club_id]),
        active_player_ids=record.home_active_player_ids,
    )
    record_roster_snapshot(
        conn,
        match_id=record.match_id,
        club_id=record.away_club_id,
        players=list(rosters[record.away_club_id]),
        active_player_ids=record.away_active_player_ids,
    )

    save_match_result(
        conn,
        match_id=record.match_id,
        season_id=record.season_id,
        week=record.week,
        home_club_id=record.home_club_id,
        away_club_id=record.away_club_id,
        winner_club_id=record.result.winner_team_id,
        home_survivors=box[record.home_club_id]["totals"]["living"],
        away_survivors=box[record.away_club_id]["totals"]["living"],
        home_roster_hash=record.home_roster_hash,
        away_roster_hash=record.away_roster_hash,
        config_version=record.config_version,
        ruleset_version=record.ruleset_version,
        meta_patch_id=record.meta_patch_id,
        seed=record.seed,
        event_log_hash=record.event_log_hash,
        final_state_hash=record.final_state_hash,
        engine_match_id=engine_match_id,
    )

    stats = extract_match_stats(
        record,
        list(rosters[record.home_club_id]),
        list(rosters[record.away_club_id]),
    )
    player_club_map = {player.id: record.home_club_id for player in rosters[record.home_club_id]}
    player_club_map.update({player.id: record.away_club_id for player in rosters[record.away_club_id]})
    save_player_stats_batch(conn, record.match_id, stats, player_club_map)
    return engine_match_id


def recompute_regular_season_standings(conn: sqlite3.Connection, season: Season) -> None:
    rows = conn.execute(
        "SELECT * FROM match_records WHERE season_id = ?",
        (season.season_id,),
    ).fetchall()
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
        for row in rows
        if not row["match_id"].startswith(f"{season.season_id}_p_")
    ]
    save_standings(conn, season.season_id, compute_standings(results))


def _team_snapshot_for_ids(
    club: Club,
    roster: Sequence[Player],
    ordered_player_ids: Sequence[str],
) -> Team:
    players_by_id = {player.id: player for player in roster}
    players = [
        players_by_id[player_id]
        for player_id in ordered_player_ids
        if player_id in players_by_id
    ]
    return Team(
        id=club.club_id,
        name=club.name,
        players=tuple(players),
        coach_policy=club.coach_policy,
        chemistry=0.5,
    )


__all__ = [
    "current_week",
    "persist_match_record",
    "recompute_regular_season_standings",
    "simulate_scheduled_match",
]
