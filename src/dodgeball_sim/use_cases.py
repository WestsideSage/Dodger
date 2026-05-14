"""Application use cases — framework-agnostic business logic.

These functions contain the core logic extracted from server.py endpoints so
they can be tested and called without FastAPI.
"""
from __future__ import annotations

import dataclasses
import sqlite3
from typing import Any, Mapping

from dodgeball_sim.career_state import CareerState, advance
from dodgeball_sim.command_center import (
    build_command_center_state,
    build_default_weekly_plan,
    build_post_week_dashboard,
    refresh_weekly_plan_context,
)
from dodgeball_sim.game_loop import (
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from dodgeball_sim.match_orchestration import (
    SimulateWeekError,
    _apply_command_plan_to_match,
    _choose_next_user_match_after_automation,
    _validate_match_rosters,
)
from dodgeball_sim.offseason_ceremony import ensure_ai_rosters_playable
from dodgeball_sim.persistence import (
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_completed_match_ids,
    load_season,
    load_standings,
    load_weekly_command_plan,
    save_career_state_cursor,
    save_command_history_record,
    save_weekly_command_plan,
)
from dodgeball_sim.view_models import normalize_root_seed

__all__ = ["SimulateWeekError", "simulate_week"]


def _build_aftermath(
    conn,
    dashboard: dict[str, Any],
    record,
    season_id: str,
    standings_before: list | None = None,
    standings_after: list | None = None,
    clubs: dict | None = None,
) -> dict[str, Any]:
    """Build the aftermath payload for a simulated week."""
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.voice_aftermath import render_headline

    root_seed_val = get_state(conn, "root_seed") or "1"
    rng = DeterministicRNG(derive_seed(int(root_seed_val), "headline", season_id, str(record.week)))
    headline = render_headline(dashboard["result"], "expected", rng)
    box = record.result.box_score["teams"]
    home_survivors = int(box[record.home_club_id]["totals"]["living"])
    away_survivors = int(box[record.away_club_id]["totals"]["living"])

    standings_shift: list[dict] = []
    if standings_before is not None and standings_after is not None and clubs is not None:
        before_rank = {row.club_id: (i + 1) for i, row in enumerate(standings_before)}
        after_rank = {row.club_id: (i + 1) for i, row in enumerate(standings_after)}
        for club_id, new_rank in after_rank.items():
            old_rank = before_rank.get(club_id, new_rank)
            if old_rank != new_rank:
                club = clubs.get(club_id)
                standings_shift.append({
                    "club_id": club_id,
                    "club_name": club.name if club else club_id,
                    "old_rank": old_rank,
                    "new_rank": new_rank,
                })
        standings_shift.sort(key=lambda item: item["new_rank"])

    return {
        "headline": headline,
        "match_card": {
            "home_club_id": record.home_club_id,
            "away_club_id": record.away_club_id,
            "winner_club_id": record.result.winner_team_id,
            "home_survivors": home_survivors,
            "away_survivors": away_survivors,
        },
        "player_growth_deltas": [],
        "standings_shift": standings_shift,
        "recruit_reactions": [],
    }


def simulate_week(
    conn: sqlite3.Connection,
    *,
    update: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Simulate the next user match in the active command-center week.

    Parameters
    ----------
    conn:
        Open SQLite connection to the career database.
    update:
        Optional dict with keys ``intent``, ``department_orders``,
        ``tactics``, ``lineup_player_ids`` to override the weekly plan.

    Returns
    -------
    dict with keys: status, message, plan, dashboard, next_state, aftermath.

    Raises
    ------
    SimulateWeekError
        If no active season/club, wrong career state, no user match, or
        roster validation fails.
    """
    player_club_id = get_state(conn, "player_club_id")
    season_id = get_state(conn, "active_season_id")
    if not player_club_id or not season_id:
        raise SimulateWeekError("No active season or club")

    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH:
        raise SimulateWeekError(
            "Command center simulation requires season_active_pre_match."
        )

    state = build_command_center_state(conn)
    existing = load_weekly_command_plan(conn, state["season_id"], state["week"], state["player_club_id"])

    intent_override = update.get("intent") if update else None
    plan = existing or build_default_weekly_plan(state, intent=intent_override or "Win Now")
    plan = refresh_weekly_plan_context(plan, state)

    if update is not None:
        intent = update.get("intent")
        if intent and intent != plan.get("intent"):
            plan = build_default_weekly_plan(state, intent=intent)
        department_orders = update.get("department_orders")
        if department_orders:
            plan["department_orders"] = {**plan["department_orders"], **department_orders}
        tactics = update.get("tactics")
        if tactics:
            plan["tactics"] = {
                **plan["tactics"],
                **{
                    key: max(0.0, min(1.0, float(value)))
                    for key, value in tactics.items()
                    if key in plan["tactics"]
                },
            }
        lineup_player_ids = update.get("lineup_player_ids")
        if lineup_player_ids:
            plan["lineup"]["player_ids"] = lineup_player_ids

    save_weekly_command_plan(conn, plan)

    from dodgeball_sim.persistence import load_clubs
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    season, chosen, stop_reason = _choose_next_user_match_after_automation(conn, season, clubs, player_club_id)

    if not chosen:
        if stop_reason == "season_complete":
            cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
            save_career_state_cursor(conn, cursor)
            conn.commit()
            return {
                "status": "success",
                "message": "Season complete. Offseason review is ready.",
                "plan": plan,
                "dashboard": state.get("latest_dashboard")
                or {
                    "season_id": season_id,
                    "week": state["week"],
                    "match_id": None,
                    "opponent_name": "Season complete",
                    "result": "Season Complete",
                    "lanes": [],
                },
                "next_state": cursor.state.value,
                "aftermath": {
                    "headline": "Season Complete",
                    "match_card": None,
                    "player_growth_deltas": [],
                    "standings_shift": [],
                    "recruit_reactions": [],
                },
            }
        raise SimulateWeekError(f"No user match available: {stop_reason}")

    scheduled = chosen[0]
    completed = load_completed_match_ids(conn, season_id)
    week_matches = [
        match
        for match in sorted(season.matches_for_week(scheduled.week), key=lambda item: item.match_id)
        if match.match_id not in completed
    ]
    _apply_command_plan_to_match(conn, plan, scheduled.match_id, player_club_id)
    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    _validate_match_rosters(week_matches, rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"

    standings_before_raw = load_standings(conn, season_id)
    standings_before = sorted(standings_before_raw, key=lambda r: (-r.points, -r.elimination_differential, r.club_id))

    records = [
        simulate_scheduled_match(
            conn,
            scheduled=week_match,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )
        for week_match in week_matches
    ]
    record = next(item for item in records if item.match_id == scheduled.match_id)
    recompute_regular_season_standings(conn, season)
    standings_after_raw = load_standings(conn, season_id)
    standings_after = sorted(standings_after_raw, key=lambda r: (-r.points, -r.elimination_differential, r.club_id))
    dashboard = build_post_week_dashboard(conn, plan, record)
    save_command_history_record(
        conn,
        {
            "season_id": season_id,
            "week": record.week,
            "match_id": record.match_id,
            "opponent_club_id": (
                record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
            ),
            "intent": plan["intent"],
            "plan": plan,
            "dashboard": dashboard,
        },
    )

    season = load_season(conn, season.season_id)
    season, next_chosen, _stop_reason = _choose_next_user_match_after_automation(
        conn, season, clubs, player_club_id
    )
    if next_chosen:
        cursor = dataclasses.replace(
            cursor,
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            week=next_chosen[0].week,
            match_id=None,
        )
    else:
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    save_career_state_cursor(conn, cursor)
    conn.commit()

    aftermath = _build_aftermath(conn, dashboard, record, season_id, standings_before, standings_after, clubs)

    return {
        "status": "success",
        "message": f"Simulated Week {record.week} command plan.",
        "plan": plan,
        "dashboard": dashboard,
        "next_state": cursor.state.value,
        "aftermath": aftermath,
    }
