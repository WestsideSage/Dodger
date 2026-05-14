from __future__ import annotations

import dataclasses
import re
import sqlite3
from typing import Any

from .career_state import CareerState, advance
from .command_center import (
    build_command_center_state,
    build_default_weekly_plan,
    refresh_weekly_plan_context,
)
from .game_loop import current_week, recompute_regular_season_standings, simulate_scheduled_match
from .match_orchestration import _choose_next_user_match_after_automation
from .offseason_ceremony import ensure_ai_rosters_playable
from .persistence import (
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_command_history,
    load_completed_match_ids,
    load_season,
    load_season_outcome,
    load_standings,
    load_weekly_command_plan,
    save_career_state_cursor,
    save_weekly_command_plan,
)
from .playoffs import is_playoff_match_id
from .scheduler import ScheduledMatch
from .season import Season, StandingsRow
from .sim_pacing import SimRequest, choose_matches_to_sim
from .view_models import normalize_root_seed


LEGACY_TARGET_EVIDENCE_RE = re.compile(r"^Target evidence: ([A-Za-z0-9_]+) was targeted (\d+) times\.$")
LEGACY_STAR_SETTING_RE = re.compile(r"^Tactical target-stars setting: ([0-9.]+)\.$")
LEGACY_RUSH_SETTING_RE = re.compile(r"^Rush frequency setting: ([0-9.]+)\.$")


class CommandWeekError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def command_center_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    state = build_command_center_state(conn)
    club = state["player_club"]
    existing = load_weekly_command_plan(conn, state["season_id"], state["week"], state["player_club_id"])
    plan = existing or build_default_weekly_plan(state)
    plan = refresh_weekly_plan_context(plan, state)
    history = sanitized_command_history(conn, state["season_id"])
    latest_dashboard = history[-1]["dashboard"] if history else None
    return {
        "season_id": state["season_id"],
        "week": state["week"],
        "player_club_id": state["player_club_id"],
        "player_club_name": club.name,
        "current_objective": "Review the staff plan, accept it, then simulate the week.",
        "plan": plan,
        "latest_dashboard": latest_dashboard,
        "history": history,
    }


def save_command_center_plan_payload(conn: sqlite3.Connection, update: dict[str, Any]) -> dict[str, Any]:
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state, intent=update.get("intent") or "Win Now")

    department_orders = update.get("department_orders")
    if department_orders:
        merged = dict(plan["department_orders"])
        for key, value in department_orders.items():
            if key in merged:
                merged[key] = value
        plan["department_orders"] = merged

    tactics = update.get("tactics")
    if tactics:
        merged_tactics = dict(plan["tactics"])
        for key, value in tactics.items():
            if key in merged_tactics:
                merged_tactics[key] = max(0.0, min(1.0, float(value)))
        plan["tactics"] = merged_tactics

    lineup_player_ids = update.get("lineup_player_ids")
    if lineup_player_ids:
        roster_ids = {player.id for player in state["roster"]}
        selected = [player_id for player_id in lineup_player_ids if player_id in roster_ids]
        if selected:
            players_by_id = {player.id: player for player in state["roster"]}
            plan["lineup"] = {
                "player_ids": selected,
                "players": [
                    {
                        "id": players_by_id[player_id].id,
                        "name": players_by_id[player_id].name,
                        "overall": round(players_by_id[player_id].overall(), 1),
                    }
                    for player_id in selected
                ],
                "summary": "User-adjusted lineup saved for the command plan.",
            }
            from .command_center import _lineup_warnings

            plan["warnings"] = _lineup_warnings(list(state["roster"]), selected, plan["intent"], plan["tactics"])

    save_weekly_command_plan(conn, plan)
    conn.commit()
    return command_center_payload(conn)


def sanitized_command_history(conn: sqlite3.Connection, season_id: str) -> list[dict[str, Any]]:
    rosters = load_all_rosters(conn)
    player_names = {
        player.id: player.name
        for roster in rosters.values()
        for player in roster
    }
    sanitized: list[dict[str, Any]] = []
    for record in load_command_history(conn, season_id):
        next_record = dict(record)
        dashboard = record.get("dashboard")
        if isinstance(dashboard, dict):
            next_record["dashboard"] = sanitize_dashboard_copy(dashboard, player_names)
        sanitized.append(next_record)
    return sanitized


def sanitize_dashboard_copy(dashboard: dict[str, Any], player_names: dict[str, str]) -> dict[str, Any]:
    next_dashboard = dict(dashboard)
    lanes = []
    for lane in dashboard.get("lanes", []):
        if not isinstance(lane, dict):
            lanes.append(lane)
            continue
        next_lane = dict(lane)
        summary = str(next_lane.get("summary", ""))
        if summary == "Tactical diagnosis correlates execution metrics to the mandated game plan.":
            next_lane["summary"] = "The staff review ties the result to visible pressure, target selection, and late-match execution."
        next_lane["items"] = [
            sanitize_dashboard_item(str(item), player_names)
            for item in next_lane.get("items", [])
        ]
        lanes.append(next_lane)
    next_dashboard["lanes"] = lanes
    return next_dashboard


def sanitize_dashboard_item(text: str, player_names: dict[str, str]) -> str:
    target_match = LEGACY_TARGET_EVIDENCE_RE.match(text)
    if target_match:
        player_id, count = target_match.groups()
        player_name = player_names.get(player_id, "The busiest defender")
        return f"{player_name} absorbed the most pressure, drawing {int(count)} throws."
    star_match = LEGACY_STAR_SETTING_RE.match(text)
    if star_match:
        value = float(star_match.group(1))
        if value >= 0.7:
            return "The plan leaned into star containment and forced their best players to work through traffic."
        if value <= 0.35:
            return "The plan spread attention across the lineup instead of overcommitting to one star matchup."
        return "The plan balanced star containment with broader lineup pressure."
    rush_match = LEGACY_RUSH_SETTING_RE.match(text)
    if rush_match:
        value = float(rush_match.group(1))
        if value >= 0.65:
            return "The team played on the front foot, using frequent pressure to speed up possessions."
        if value <= 0.35:
            return "The team stayed patient, choosing shape and recovery over constant rush pressure."
        return "The team mixed patient possessions with selective rush pressure."
    return text


def command_history_payload(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise CommandWeekError("No active season")
    return sanitized_command_history(conn, season_id)


def simulation_request(mode: str, weeks: int, milestone: str | None, week: int, season: Season) -> SimRequest:
    if mode == "week":
        return SimRequest(mode="week", current_week=week, include_user_matches=True)
    if mode == "next_user_match":
        return SimRequest(mode="to_next_user_match", include_user_matches=False)
    if mode == "multiple_weeks":
        return SimRequest(mode="multiple_weeks", current_week=week, weeks=max(1, weeks), include_user_matches=False)
    if mode == "milestone":
        target = milestone or "playoffs"
        milestone_week = None
        if target in {"season_end", "recruitment_day", "offseason"}:
            milestone_week = season.total_weeks() + 1
        return SimRequest(mode="milestone", milestone=target, milestone_week=milestone_week, include_user_matches=True)
    if mode == "user_match":
        return SimRequest(mode="user_match", include_user_matches=False)
    raise CommandWeekError(f"Unknown simulation mode: {mode}")


def run_simulation_command(conn: sqlite3.Connection, command: dict[str, Any]) -> dict[str, Any]:
    mode = command.get("mode", "week")
    weeks = int(command.get("weeks", 1) or 1)
    milestone = command.get("milestone")
    player_club_id = get_state(conn, "player_club_id")
    season_id = get_state(conn, "active_season_id")
    if not player_club_id or not season_id:
        raise CommandWeekError("No active season or club")

    season = load_season(conn, season_id)
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH:
        raise CommandWeekError(
            "Simulation requires career state season_active_pre_match.",
            status_code=409,
        )
    clubs = load_clubs(conn)
    week = cursor.week or current_week(conn, season) or 1
    if mode == "user_match":
        season, chosen, stop_reason = _choose_next_user_match_after_automation(conn, season, clubs, player_club_id)
    else:
        season = advance_playoffs_if_needed(conn, season, clubs, player_club_id)
        completed = load_completed_match_ids(conn, season_id)
        chosen, stop = choose_matches_to_sim(
            list(season.scheduled_matches),
            completed,
            player_club_id,
            simulation_request(mode, weeks, milestone, week, season),
        )
        stop_reason = stop.reason

    if not chosen:
        if stop_reason == "season_complete" and cursor.state == CareerState.SEASON_ACTIVE_PRE_MATCH:
            cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
            save_career_state_cursor(conn, cursor)
            conn.commit()
        return {
            "status": "success",
            "message": "No matches simulated.",
            "simulated_count": 0,
            "stop_reason": stop_reason,
            "next_state": cursor.state.value,
        }

    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    validate_match_rosters(chosen, rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"

    records = [
        simulate_scheduled_match(
            conn,
            scheduled=scheduled,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )
        for scheduled in chosen
    ]
    recompute_regular_season_standings(conn, season)
    next_week = current_week(conn, season) or week
    if mode == "user_match" and len(records) == 1:
        in_match = advance(cursor, CareerState.SEASON_ACTIVE_IN_MATCH, week=records[0].week, match_id=records[0].match_id)
        cursor = advance(in_match, CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, match_id=records[0].match_id)
    else:
        cursor = dataclasses.replace(cursor, week=next_week)
    save_career_state_cursor(conn, cursor)
    conn.commit()

    return {
        "status": "success",
        "simulated_count": len(records),
        "stop_reason": stop_reason,
        "message": f"Simulated {len(records)} matches.",
        "match_id": records[0].match_id if mode == "user_match" and records else None,
        "next_state": cursor.state.value,
    }


def validate_match_rosters(chosen, rosters) -> None:
    for scheduled in chosen:
        for club_id in (scheduled.home_club_id, scheduled.away_club_id):
            if len(rosters.get(club_id, ())) < 1:
                raise CommandWeekError(f"Club {club_id} does not have a playable roster.", status_code=409)


def regular_season_matches(season: Season) -> list[ScheduledMatch]:
    return [
        match
        for match in season.scheduled_matches
        if not is_playoff_match_id(season.season_id, match.match_id)
    ]


def standings_with_all_clubs(standings: list[StandingsRow], clubs: dict[str, Any]) -> list[StandingsRow]:
    by_id = {row.club_id: row for row in standings}
    rows = [
        by_id.get(club_id, StandingsRow(club_id, wins=0, losses=0, draws=0, elimination_differential=0, points=0))
        for club_id in clubs
    ]
    rows.sort(key=lambda row: (-row.points, -row.elimination_differential, row.club_id))
    return rows


def regular_season_complete(conn: sqlite3.Connection, season: Season) -> bool:
    completed = load_completed_match_ids(conn, season.season_id)
    return all(match.match_id in completed for match in regular_season_matches(season))


def simulate_ai_playoff_matches(
    conn: sqlite3.Connection,
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
    validate_match_rosters(matches, rosters)
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


def advance_playoffs_if_needed(conn: sqlite3.Connection, season: Season, clubs: dict[str, Any], player_club_id: str) -> Season:
    from .playoffs import create_final_match, create_semifinal_bracket, outcome_from_final
    from .persistence import save_playoff_bracket, save_scheduled_matches, save_season_outcome, load_playoff_bracket

    if load_season_outcome(conn, season.season_id) is not None:
        return season
    if not regular_season_complete(conn, season):
        return season

    while True:
        bracket = load_playoff_bracket(conn, season.season_id)
        completed = load_completed_match_ids(conn, season.season_id)
        if bracket is None:
            standings = standings_with_all_clubs(load_standings(conn, season.season_id), clubs)
            next_week = max((match.week for match in regular_season_matches(season)), default=0) + 1
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
                simulate_ai_playoff_matches(conn, ai_pending, clubs, player_club_id, season.season_id)
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
                simulate_ai_playoff_matches(conn, [final], clubs, player_club_id, season.season_id)
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
