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
from .ai_program_manager import prepare_ai_plans_for_matches
from .game_loop import current_week, recompute_regular_season_standings, simulate_scheduled_match
from .match_orchestration import _choose_next_user_match_after_automation
from .match_orchestration import _apply_command_plan_to_match
from .match_orchestration import resolve_playoff_winners
from .models import CoachPolicy
from .offseason_ceremony import ensure_ai_rosters_playable
from .persistence import (
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_command_history,
    load_completed_match_ids,
    load_latest_weekly_plan_intent,
    load_latest_weekly_plan_orders,
    load_season,
    load_season_outcome,
    load_standings,
    load_weekly_command_plan,
    save_career_state_cursor,
    save_weekly_command_plan,
    set_state,
)
from .playoffs import PLAYOFF_FIELD_SIZE, is_playoff_match_id, playoff_stage_label
from .season_preview import build_season_preview, derive_schedule_facts
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
    if not existing:
        prior_intent = load_latest_weekly_plan_intent(conn, state["season_id"], state["week"], state["player_club_id"])
        plan = build_default_weekly_plan(state, intent=prior_intent or "Balanced")
        # Codex playtest issue 21: dev focus / staff focus are season-spanning
        # decisions — carry them into the fresh week like the intent, instead
        # of silently resetting to Balanced every Monday (a manager re-picked
        # Tactical drills on title week only because they happened to look).
        prior_orders = load_latest_weekly_plan_orders(
            conn, state["season_id"], state["week"], state["player_club_id"]
        )
        if prior_orders:
            carried = dict(plan["department_orders"])
            for key in ("dev_focus", "focus_department"):
                if key in carried and prior_orders.get(key):
                    carried[key] = prior_orders[key]
            plan["department_orders"] = carried
    else:
        plan = existing
    plan = refresh_weekly_plan_context(plan, state)
    plan["briefing"] = _build_plan_briefing(conn, state, plan)
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
        "season_preview": _build_season_preview_payload(conn, state),
        # The career's ruleset, so plan-editing surfaces can disclose
        # announced-only knobs honestly (the official engine does not enforce
        # opening-rush behavior — WT-20). None/absent => legacy generic career.
        "ruleset_selection": get_state(conn, "ruleset_selection"),
    }


SEASON_PREVIEW_SKIP_KEY = "season_preview_skipped"


def _build_season_preview_payload(
    conn: sqlite3.Connection, state: dict[str, Any]
) -> dict[str, Any] | None:
    """Orientation screen for Week 1 only; ``None`` otherwise.

    Shapes schedule length, bye week, playoff cut, top goal, and one
    roster strength/weakness from facts the engine already has. Returns
    ``None`` past Week 1 so the screen never re-appears mid-season.
    """

    if int(state.get("week") or 0) != 1:
        return None
    try:
        season_id = state["season_id"]
        player_club_id = state["player_club_id"]
        season = load_season(conn, season_id)
        clubs = load_clubs(conn)
        regular = regular_season_matches(season)
        regular_weeks = [match.week for match in regular]
        user_match_weeks = [
            match.week
            for match in regular
            if player_club_id in (match.home_club_id, match.away_club_id)
        ]
        facts = derive_schedule_facts(
            regular_weeks=regular_weeks,
            user_match_weeks=user_match_weeks,
        )
        roster_rows = [
            {
                "archetype": getattr(player.archetype, "value", str(player.archetype)),
                "overall": player.overall_skill(),
            }
            for player in state.get("roster", [])
        ]
        skipped = (get_state(conn, SEASON_PREVIEW_SKIP_KEY, "0") or "0") == "1"
        return build_season_preview(
            regular_season_weeks=facts["regular_season_weeks"],
            bye_week=facts["bye_week"],
            playoff_cut=PLAYOFF_FIELD_SIZE,
            total_clubs=len(clubs),
            roster=roster_rows,
            skipped=skipped,
        )
    except Exception:
        return None


def set_season_preview_skipped(conn: sqlite3.Connection, skipped: bool) -> dict[str, Any]:
    """Persist the player's 'skip the W1 preview' preference."""

    set_state(conn, SEASON_PREVIEW_SKIP_KEY, "1" if skipped else "0")
    conn.commit()
    return command_center_payload(conn)


def _build_plan_briefing(
    conn: sqlite3.Connection,
    state: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Attach the canonical week briefing (computed, never persisted).

    All inputs come from data the player can verify and the engine actually
    uses; see week_briefing for the honesty contract.
    """
    from .view_models import build_schedule_rows
    from .week_briefing import build_week_briefing

    season_id = state["season_id"]
    player_club_id = state["player_club_id"]
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    completed = load_completed_match_ids(conn, season_id)

    # Same composite tiebreak as week_briefing._build_form / the standings
    # screen (Codex issue 16): officials break on game-point fields, legacy
    # on survivor differential — the inert keys are zero on the other ruleset.
    standings_rows = sorted(
        load_standings(conn, season_id),
        key=lambda r: (
            -r.points,
            -getattr(r, "total_game_points_scored", 0),
            -getattr(r, "game_point_differential", 0),
            -r.elimination_differential,
            r.club_id,
        ),
    )
    leader = clubs.get(standings_rows[0].club_id) if standings_rows else None
    league_leader = leader.name if leader else None

    recent_results = [
        result
        for record in state.get("history", [])[-5:]
        if (result := (record.get("dashboard") or {}).get("result"))
    ]

    schedule_rows = build_schedule_rows(season, completed, player_club_id)
    games_remaining = sum(
        1 for row in schedule_rows if row.is_user_match and row.status != "played"
    )

    upcoming = state.get("upcoming_match")
    is_home = bool(upcoming is not None and upcoming.home_club_id == player_club_id)
    playoff_stage = None
    if upcoming is not None:
        stage = playoff_stage_label(season_id, upcoming.match_id)
        if stage and stage != "Regular Season":
            playoff_stage = stage

    return build_week_briefing(
        plan=plan,
        standings_rows=standings_rows,
        player_club_id=player_club_id,
        league_leader=league_leader,
        recent_results=recent_results,
        games_remaining=games_remaining,
        is_home=is_home,
        playoff_stage=playoff_stage,
    )


def save_command_center_plan_payload(conn: sqlite3.Connection, update: dict[str, Any]) -> dict[str, Any]:
    state = build_command_center_state(conn)

    # Preserve the player's already-saved decisions (tactics, lineup,
    # department orders) across saves that don't restate them — most
    # importantly the plan-lock action, which POSTs the intent only. Only
    # rebuild from the intent default when the intent actually changes (or
    # there is no saved plan yet), since switching intent is meant to reset
    # tactics to that intent's preset. Rebuilding unconditionally silently
    # reverted Policy Editor edits before the sim and recap ever saw them.
    existing = load_weekly_command_plan(
        conn, state["season_id"], state["week"], state["player_club_id"]
    )
    new_intent = update.get("intent") or (existing or {}).get("intent") or "Balanced"
    intent_changed = existing is None or existing.get("intent") != new_intent
    if existing is not None and not intent_changed:
        plan = refresh_weekly_plan_context(dict(existing), state)
        plan["intent"] = new_intent
    else:
        plan = build_default_weekly_plan(state, intent=new_intent)
        # Codex playtest issue 7: switching intent resets TACTICS to that
        # intent's preset — its documented meaning — but it used to also
        # silently wipe the department orders (dev focus, staff focus) and
        # the saved lineup, which are independent decisions. A manager
        # mid-promise ("run focused dev 3+ weeks") lost their dev focus just
        # by touching the intent. Carry both over from the saved plan.
        if existing is not None:
            prior_orders = existing.get("department_orders") or {}
            if prior_orders:
                carried = dict(plan["department_orders"])
                for key, value in prior_orders.items():
                    if key in carried:
                        carried[key] = value
                plan["department_orders"] = carried
            if existing.get("lineup"):
                plan["lineup"] = existing["lineup"]

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
        merged_tactics.update(tactics)
        plan["tactics"] = CoachPolicy.from_dict(merged_tactics).as_dict()

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
                        "overall": players_by_id[player_id].overall_skill(),
                    }
                    for player_id in selected
                ],
                "summary": "User-adjusted lineup saved for the command plan.",
            }
            from .command_center import _lineup_warnings

            plan["warnings"] = _lineup_warnings(list(state["roster"]), selected, plan["intent"], plan["tactics"])
            # Saving an edited lineup IS confirming the six you will field.
            plan["lineup_confirmed"] = True

    # D3: carry the deliberate-action readiness flags forward across in-week
    # saves (tactics tweaks, intent changes) so a scout/confirm action is not
    # silently undone. They reset only when a brand-new weekly plan is built
    # (start of a new week with no saved plan).
    if existing is not None:
        plan["opponent_scouted"] = bool(plan.get("opponent_scouted")) or bool(existing.get("opponent_scouted"))
        plan["lineup_confirmed"] = bool(plan.get("lineup_confirmed")) or bool(existing.get("lineup_confirmed"))

    save_weekly_command_plan(conn, plan)
    conn.commit()
    return command_center_payload(conn)


def _set_plan_readiness_flag(conn: sqlite3.Connection, flag: str) -> dict[str, Any]:
    """Set a deliberate-action readiness flag on the current weekly plan.

    Loads the saved plan (or the default if none yet), flips the flag, and
    persists. Returns the refreshed command-center payload so the readiness
    gate updates in one round trip.
    """
    state = build_command_center_state(conn)
    existing = load_weekly_command_plan(
        conn, state["season_id"], state["week"], state["player_club_id"]
    )
    if existing is not None:
        plan = refresh_weekly_plan_context(dict(existing), state)
    else:
        prior_intent = load_latest_weekly_plan_intent(
            conn, state["season_id"], state["week"], state["player_club_id"]
        )
        plan = build_default_weekly_plan(state, intent=prior_intent or "Balanced")
    plan[flag] = True
    save_weekly_command_plan(conn, plan)
    conn.commit()
    return command_center_payload(conn)


def mark_opponent_scouted(conn: sqlite3.Connection) -> dict[str, Any]:
    """Clear the scout-opponent readiness gate (D3)."""
    return _set_plan_readiness_flag(conn, "opponent_scouted")


def mark_lineup_confirmed(conn: sqlite3.Connection) -> dict[str, Any]:
    """Clear the confirm-lineup readiness gate (D3)."""
    return _set_plan_readiness_flag(conn, "lineup_confirmed")


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
        # Player-facing reason only — never leak the raw lifecycle enum token.
        offseason_states = {
            CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
            CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            CareerState.NEXT_SEASON_READY,
        }
        if cursor.state in offseason_states:
            reason = "The regular season is complete — continue in the offseason to start the next season."
        else:
            reason = "There's no match ready to simulate right now."
        raise CommandWeekError(reason, status_code=409)
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
    prepare_ai_plans_for_matches(
        conn,
        season_id=season_id,
        season=season,
        matches=chosen,
        clubs=clubs,
        rosters=rosters,
        player_club_id=player_club_id,
        standings_rows=load_standings(conn, season_id),
        apply_plan=_apply_command_plan_to_match,
        load_plan=load_weekly_command_plan,
        save_plan=save_weekly_command_plan,
    )

    # Reload clubs so the engine sees the coach policies just persisted by the
    # AI plan applications above. ``prepare_ai_plans_for_matches`` writes updated
    # ``coach_policy`` rows for AI clubs; the ``clubs`` dict loaded earlier is
    # stale, and the engine builds each team's tactics from ``club.coach_policy``.
    # Without this reload the persisted AI archetype tactic never reaches the
    # simulated match — the rival looks adaptive in the data but plays the base
    # policy on court. Mirrors the reload the primary simulate path already does.
    clubs = load_clubs(conn)
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
            winners = resolve_playoff_winners(
                conn,
                bracket=bracket,
                match_ids=(
                    f"{season.season_id}_p_r1_m1",
                    f"{season.season_id}_p_r1_m2",
                ),
                participants_by_match_id={
                    match.match_id: (match.home_club_id, match.away_club_id)
                    for match in semifinal_matches
                },
            )
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
                winners = resolve_playoff_winners(
                    conn,
                    bracket=bracket,
                    match_ids=(final.match_id,),
                    participants_by_match_id={
                        final.match_id: (final.home_club_id, final.away_club_id),
                    },
                )
                final_winner_id = winners.get(final.match_id)
                if final_winner_id is None:
                    return season
                save_season_outcome(
                    conn,
                    outcome_from_final(
                        bracket,
                        final_match_id=final.match_id,
                        home_club_id=final.home_club_id,
                        away_club_id=final.away_club_id,
                        winner_club_id=final_winner_id,
                    ),
                )
                save_playoff_bracket(conn, dataclasses.replace(bracket, status="complete"))
                conn.commit()
            return season
        return season
