"""Match orchestration helpers shared between use_cases.py and server.py.

These helpers were extracted from server.py so that use_cases.py can import
them without creating a circular import (server.py -> use_cases.py ->
server.py).

SimulateWeekError is defined here to avoid a further circular dependency
when server.py imports it from use_cases.py.
"""
from __future__ import annotations

import dataclasses
from typing import Any

from dodgeball_sim.game_loop import (
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.offseason_ceremony import ensure_ai_rosters_playable
from dodgeball_sim.persistence import (
    load_clubs,
    load_club_roster,
    load_completed_match_ids,
    load_playoff_bracket,
    load_season,
    load_standings,
    load_all_rosters,
    load_season_outcome,
    save_club,
    save_match_lineup_override,
    save_playoff_bracket,
    save_scheduled_matches,
    save_season_outcome,
    get_state,
)
from dodgeball_sim.playoffs import (
    create_final_match,
    create_semifinal_bracket,
    is_playoff_match_id,
    outcome_from_final,
)
from dodgeball_sim.scheduler import ScheduledMatch
from dodgeball_sim.season import Season, StandingsRow
from dodgeball_sim.view_models import normalize_root_seed


class SimulateWeekError(ValueError):
    """Raised when the simulate-week use case cannot proceed."""


# ---------------------------------------------------------------------------
# Internal helpers (mirror of the private helpers originally in server.py)
# ---------------------------------------------------------------------------

def _regular_season_matches(season: Season) -> list[ScheduledMatch]:
    return [
        match
        for match in season.scheduled_matches
        if not is_playoff_match_id(season.season_id, match.match_id)
    ]


def _standings_with_all_clubs(standings: list[StandingsRow], clubs: dict[str, Any]) -> list[StandingsRow]:
    by_id = {row.club_id: row for row in standings}
    rows = [
        by_id.get(club_id, StandingsRow(club_id, wins=0, losses=0, draws=0, elimination_differential=0, points=0))
        for club_id in clubs
    ]
    rows.sort(key=lambda row: (-row.points, -row.elimination_differential, row.club_id))
    return rows


def _regular_season_complete(conn, season: Season) -> bool:
    completed = load_completed_match_ids(conn, season.season_id)
    return all(match.match_id in completed for match in _regular_season_matches(season))


def _validate_match_rosters(chosen, rosters) -> None:
    for scheduled in chosen:
        for club_id in (scheduled.home_club_id, scheduled.away_club_id):
            if len(rosters.get(club_id, ())) < 1:
                raise SimulateWeekError(
                    f"Club {club_id} does not have a playable roster.",
                )


def _simulate_ai_matches(
    conn,
    matches: list[ScheduledMatch],
    clubs: dict[str, Any],
    player_club_id: str,
    season_id: str,
) -> None:
    if not matches:
        return
    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    _validate_match_rosters(matches, rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"
    for match in matches:
        simulate_scheduled_match(
            conn,
            scheduled=match,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )


def _advance_playoffs_if_needed(conn, season: Season, clubs: dict[str, Any], player_club_id: str) -> Season:
    if load_season_outcome(conn, season.season_id) is not None:
        return season
    if not _regular_season_complete(conn, season):
        return season

    while True:
        bracket = load_playoff_bracket(conn, season.season_id)
        completed = load_completed_match_ids(conn, season.season_id)
        if bracket is None:
            standings = _standings_with_all_clubs(load_standings(conn, season.season_id), clubs)
            next_week = max((match.week for match in _regular_season_matches(season)), default=0) + 1
            bracket, semifinals = create_semifinal_bracket(season.season_id, standings, next_week)
            save_playoff_bracket(conn, bracket)
            save_scheduled_matches(conn, semifinals)
            conn.commit()
            season = load_season(conn, season.season_id)
            continue

        if bracket.status == "semifinals_scheduled":
            semifinal_ids = {f"{season.season_id}_p_r1_m1", f"{season.season_id}_p_r1_m2"}
            semifinal_matches = [match for match in season.scheduled_matches if match.match_id in semifinal_ids]
            pending = [match for match in semifinal_matches if match.match_id not in completed]
            ai_pending = [
                match
                for match in pending
                if player_club_id not in (match.home_club_id, match.away_club_id)
            ]
            if ai_pending:
                _simulate_ai_matches(conn, ai_pending, clubs, player_club_id, season.season_id)
                recompute_regular_season_standings(conn, season)
                conn.commit()
                continue
            if pending:
                return season
            winners = {
                row["match_id"]: row["winner_club_id"]
                for row in conn.execute(
                    "SELECT match_id, winner_club_id FROM match_records WHERE match_id IN (?, ?)",
                    (f"{season.season_id}_p_r1_m1", f"{season.season_id}_p_r1_m2"),
                ).fetchall()
            }
            next_week = max(match.week for match in semifinal_matches) + 1
            bracket, final = create_final_match(bracket, winners, next_week)
            save_playoff_bracket(conn, bracket)
            save_scheduled_matches(conn, [final])
            conn.commit()
            season = load_season(conn, season.season_id)
            continue

        if bracket.status == "final_scheduled":
            final = next(
                (match for match in season.scheduled_matches if match.match_id == f"{season.season_id}_p_final"),
                None,
            )
            if final is None:
                return season
            if final.match_id not in completed:
                if player_club_id in (final.home_club_id, final.away_club_id):
                    return season
                _simulate_ai_matches(conn, [final], clubs, player_club_id, season.season_id)
                recompute_regular_season_standings(conn, season)
                completed = load_completed_match_ids(conn, season.season_id)
            if final.match_id in completed:
                row = conn.execute(
                    "SELECT winner_club_id FROM match_records WHERE match_id = ?",
                    (final.match_id,),
                ).fetchone()
                if row is None or row["winner_club_id"] is None:
                    return season
                save_season_outcome(
                    conn,
                    outcome_from_final(
                        bracket,
                        final_match_id=final.match_id,
                        home_club_id=final.home_club_id,
                        away_club_id=final.away_club_id,
                        winner_club_id=row["winner_club_id"],
                    ),
                )
                save_playoff_bracket(conn, dataclasses.replace(bracket, status="complete"))
                conn.commit()
            return season
        return season


def _choose_user_match(season: Season, completed: set[str], player_club_id: str):
    for match in sorted(season.scheduled_matches, key=lambda item: (item.week, item.match_id)):
        if match.match_id in completed:
            continue
        if player_club_id in (match.home_club_id, match.away_club_id):
            return [match], "user_match"
    return [], "season_complete"


def _choose_next_user_match_after_automation(
    conn,
    season: Season,
    clubs: dict[str, Any],
    player_club_id: str,
) -> tuple[Season, list[ScheduledMatch], str]:
    season = _advance_playoffs_if_needed(conn, season, clubs, player_club_id)
    completed = load_completed_match_ids(conn, season.season_id)
    chosen, stop_reason = _choose_user_match(season, completed, player_club_id)
    if chosen:
        return season, chosen, stop_reason

    ai_regular_pending = [
        match
        for match in _regular_season_matches(season)
        if match.match_id not in completed
        and player_club_id not in (match.home_club_id, match.away_club_id)
    ]
    if ai_regular_pending:
        _simulate_ai_matches(conn, ai_regular_pending, clubs, player_club_id, season.season_id)
        recompute_regular_season_standings(conn, season)
        conn.commit()
        season = load_season(conn, season.season_id)
        season = _advance_playoffs_if_needed(conn, season, clubs, player_club_id)
        completed = load_completed_match_ids(conn, season.season_id)
        chosen, stop_reason = _choose_user_match(season, completed, player_club_id)
    return season, chosen, stop_reason


def _apply_command_plan_to_match(conn, plan: dict[str, Any], match_id: str, club_id: str) -> None:
    clubs = load_clubs(conn)
    club = clubs.get(club_id)
    if club is None:
        raise SimulateWeekError(f"Club {club_id} not found")
    tactics = plan.get("tactics", {})
    policy_values = club.coach_policy.as_dict()
    for key in policy_values:
        if key in tactics:
            policy_values[key] = max(0.0, min(1.0, float(tactics[key])))
    updated_club = dataclasses.replace(club, coach_policy=CoachPolicy(**policy_values))
    save_club(conn, updated_club, load_club_roster(conn, club_id))
    lineup_ids = plan.get("lineup", {}).get("player_ids") or []
    if lineup_ids:
        save_match_lineup_override(conn, match_id, club_id, list(lineup_ids))
