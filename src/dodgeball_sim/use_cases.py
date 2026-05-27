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
from dodgeball_sim.ai_program_manager import prepare_ai_plans_for_matches
from dodgeball_sim.aftermath_context import AftermathContext, moment_events_from_payload
from dodgeball_sim.game_loop import (
    current_week,
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from dodgeball_sim.match_orchestration import (
    SimulateWeekError,
    _apply_command_plan_to_match,
    _choose_next_user_match_after_automation,
    _validate_match_rosters,
)
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.offseason_ceremony import ensure_ai_rosters_playable
from dodgeball_sim.persistence import (
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_completed_match_ids,
    load_latest_weekly_plan_intent,
    load_season,
    load_standings,
    load_weekly_command_plan,
    save_career_state_cursor,
    save_command_history_record,
    save_weekly_command_plan,
)
from dodgeball_sim.view_models import normalize_root_seed

__all__ = ["SimulateWeekError", "simulate_week"]


_DEV_FOCUS_LABELS = {
    "BALANCED": "Balanced development",
    "YOUTH_ACCELERATION": "Youth acceleration",
    "TACTICAL_DRILLS": "Tactical drills",
    "STRENGTH_AND_CONDITIONING": "Strength and conditioning",
}


def _development_feedback(
    plan: Mapping[str, Any] | None,
    rosters: Mapping[str, list[Any]] | None,
    player_club_id: str | None,
    *,
    is_bye: bool = False,
) -> dict[str, Any]:
    orders = dict((plan or {}).get("department_orders") or {})
    focus = str(orders.get("dev_focus") or "BALANCED")
    focus_label = _DEV_FOCUS_LABELS.get(focus, focus.replace("_", " ").title())
    roster = list((rosters or {}).get(player_club_id or "", []))

    if focus == "YOUTH_ACCELERATION":
        candidates = sorted(roster, key=lambda player: (player.age, -player.traits.potential, player.name))[:3]
        target = "high-upside younger players"
    elif focus == "TACTICAL_DRILLS":
        candidates = sorted(roster, key=lambda player: (player.ratings.tactical_iq, player.name))[:3]
        target = "the lowest tactical-IQ rotation players"
    elif focus == "STRENGTH_AND_CONDITIONING":
        candidates = sorted(roster, key=lambda player: (player.ratings.stamina, player.name))[:3]
        target = "the stamina floor of the roster"
    else:
        candidates = sorted(roster, key=lambda player: (-player.overall_skill(), player.name))[:3]
        target = "the active rotation"

    player_names = [player.name for player in candidates]
    if player_names:
        names = ", ".join(player_names)
        progress = f"+1 training unit toward {focus_label.lower()} for {names}."
    else:
        progress = f"+1 training unit toward {focus_label.lower()}."

    if is_bye:
        summary = f"{focus_label} banked a clean practice week for {target}; rating changes resolve in offseason."
    else:
        summary = f"{focus_label} logged weekly reps for {target}; rating changes resolve in offseason."

    return {
        "focus": focus,
        "focus_label": focus_label,
        "summary": summary,
        "progress": progress,
        "players": player_names,
    }


def _simulate_bye_week(
    conn: sqlite3.Connection,
    *,
    state: Mapping[str, Any],
    plan: dict[str, Any],
    cursor,
) -> dict[str, Any]:
    player_club_id = state["player_club_id"]
    season_id = state["season_id"]
    week = int(state["week"])
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    completed = load_completed_match_ids(conn, season_id)
    week_matches = [
        match
        for match in sorted(season.matches_for_week(week), key=lambda item: item.match_id)
        if match.match_id not in completed
        and player_club_id not in (match.home_club_id, match.away_club_id)
    ]

    records = []
    rosters = load_all_rosters(conn)
    if week_matches:
        root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
        if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
            rosters = load_all_rosters(conn)
        _validate_match_rosters(week_matches, rosters)
        difficulty = get_state(conn, "difficulty", "pro") or "pro"
        prepare_ai_plans_for_matches(
            conn,
            season_id=season_id,
            season=season,
            matches=week_matches,
            clubs=clubs,
            rosters=rosters,
            player_club_id=player_club_id,
            standings_rows=load_standings(conn, season_id),
            apply_plan=_apply_command_plan_to_match,
            load_plan=load_weekly_command_plan,
            save_plan=save_weekly_command_plan,
        )
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
        recompute_regular_season_standings(conn, season)

    season = load_season(conn, season_id)
    season, next_chosen, stop_reason = _choose_next_user_match_after_automation(
        conn, season, clubs, player_club_id
    )
    if next_chosen:
        cursor = dataclasses.replace(
            cursor,
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            week=next_chosen[0].week,
            match_id=None,
        )
    elif stop_reason == "season_complete":
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    else:
        cursor = dataclasses.replace(cursor, week=current_week(conn, season) or week)
    save_career_state_cursor(conn, cursor)
    conn.commit()

    dashboard = {
        "season_id": season_id,
        "week": week,
        "match_id": None,
        "opponent_name": "Bye Week",
        "result": "Bye Week",
        "lanes": [
            {
                "title": "League Calendar",
                "summary": f"Bye week advanced after {len(records)} league matches.",
                "items": [
                    "No opponent was scheduled for your club.",
                    "The league calendar advanced to the next available user match.",
                ],
            }
        ],
    }
    return {
        "status": "success",
        "message": "Bye week advanced.",
        "plan": plan,
        "dashboard": dashboard,
        "next_state": cursor.state.value,
        "aftermath": {
            "headline": "Bye Week Complete",
            "match_card": None,
            "player_growth_deltas": [],
            "development_feedback": _development_feedback(plan, rosters, player_club_id, is_bye=True),
            "bye_recovery": {
                "summary": "No match scheduled; your starters avoided fatigue exposure this week.",
                "players": [player.name for player in rosters.get(player_club_id, [])[:3]],
            },
            "standings_shift": [],
            "recruit_reactions": [],
        },
    }


def _build_aftermath(
    conn,
    dashboard: dict[str, Any],
    record,
    season_id: str,
    standings_before: list | None = None,
    standings_after: list | None = None,
    clubs: dict | None = None,
    plan: Mapping[str, Any] | None = None,
    player_club_id: str | None = None,
) -> dict[str, Any]:
    """Build the aftermath payload for a simulated week."""
    from dodgeball_sim.voice_aftermath import render_body
    from dodgeball_sim.voice_verdict import render_headline, render_verdict

    box = record.result.box_score["teams"]
    home_survivors = int(box[record.home_club_id]["totals"]["living"])
    away_survivors = int(box[record.away_club_id]["totals"]["living"])
    _winner_id = record.result.winner_team_id
    if _winner_id is None and home_survivors != away_survivors:
        _winner_id = (
            record.home_club_id if home_survivors > away_survivors else record.away_club_id
        )
    start_context = record.result.events[0].context if record.result.events else {}
    end_context = record.result.events[-1].context if record.result.events else {}
    team_policies = (
        dict(start_context.get("team_policies", {}))
        if isinstance(start_context, Mapping)
        else {}
    )
    parsed_moments = moment_events_from_payload(
        end_context.get("moment_events", []) if isinstance(end_context, Mapping) else []
    )

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

    verdict: str | None = None
    body: tuple[str, ...] = ()
    if plan is not None and player_club_id is not None and clubs is not None:
        opponent_club_id = record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
        winner = record.result.winner_team_id
        result = "Draw" if winner is None else ("Win" if winner == player_club_id else "Loss")
        club = clubs.get(player_club_id)
        if club is not None and player_club_id in box and opponent_club_id in box:
            base_tactics = club.coach_policy.as_dict()
            player_policy = CoachPolicy.from_dict(
                dict(team_policies.get(player_club_id) or plan.get("tactics") or base_tactics)
            )
            opponent_policy = CoachPolicy.from_dict(
                dict(team_policies.get(opponent_club_id) or CoachPolicy().as_dict())
            )
            voice_ctx = AftermathContext(
                match_result=record.result,
                moment_events=parsed_moments,
                policy_team=player_policy,
                policy_opponent=opponent_policy,
                tier=1,
            )
            headline = render_headline(voice_ctx)
            body = render_body(voice_ctx)
            verdict = render_verdict(
                intent=str(plan.get("intent", "")),
                tactics=dict(plan.get("tactics") or {}),
                base_tactics=base_tactics,
                result=result,
                player_team_box=box[player_club_id],
                opponent_team_box=box[opponent_club_id],
            )
        else:
            headline = dashboard["result"]
    else:
        headline = dashboard["result"]

    try:
        from dodgeball_sim.persistence import roster_snapshots
        from dodgeball_sim.replay_service import stats_for_match, score_player

        _clubs = clubs if clubs is not None else load_clubs(conn)
        snapshots = roster_snapshots(conn, record.match_id, record.home_club_id, record.away_club_id)
        name_map = {
            str(player.get("id", "")): str(player.get("name", player.get("id", "")))
            for players in snapshots.values()
            for player in players
        }
        player_club_map = {
            str(player.get("id", "")): club_id
            for club_id, players in snapshots.items()
            for player in players
        }
        stats = stats_for_match(conn, record.match_id)

        # Weight impact by team outcome so the loser of a shutout can't out-rank
        # the winner. Winners get +50% Impact, losers get -25%, draws unchanged.
        def _weighted(player_id: str, stat) -> float:
            base = score_player(stat)
            club_id = player_club_map.get(player_id, "")
            if _winner_id and club_id == _winner_id:
                return base * 1.5
            if _winner_id and club_id and club_id != _winner_id:
                return base * 0.75
            return base

        top = sorted(stats.items(), key=lambda item: (-_weighted(item[0], item[1]), item[0]))[:6]
        top_performers = [
            {
                "player_id": player_id,
                "player_name": name_map.get(player_id, player_id),
                "club_name": _clubs[player_club_map.get(player_id, "")].name if player_club_map.get(player_id, "") in _clubs else "Unknown",
                "score": round(_weighted(player_id, stat), 1),
                "eliminations_by_throw": stat.eliminations_by_throw,
                "catches_made": stat.catches_made,
                "dodges_successful": stat.dodges_successful,
            }
            for player_id, stat in top
            if _weighted(player_id, stat) > 0
        ]
    except Exception:
        top_performers = []

    scoring_model = "legacy"
    home_game_pts = 0
    away_game_pts = 0
    if record.result.official_metadata:
        meta = record.result.official_metadata
        if "cloth" in record.result.config_version:
            scoring_model = "cloth"
        else:
            scoring_model = "foam"
        home_game_pts = meta.get("team_a_game_points", 0)
        away_game_pts = meta.get("team_b_game_points", 0)

    aftermath: dict[str, Any] = {
        "headline": headline,
        "match_card": {
            "home_club_id": record.home_club_id,
            "away_club_id": record.away_club_id,
            "winner_club_id": _winner_id,
            "home_survivors": home_survivors,
            "away_survivors": away_survivors,
            "scoring_model": scoring_model,
            "home_game_points": home_game_pts,
            "away_game_points": away_game_pts,
        },
        "player_growth_deltas": [],
        "development_feedback": _development_feedback(plan, load_all_rosters(conn), player_club_id),
        "standings_shift": standings_shift,
        "recruit_reactions": [],
        "body": list(body),
        "top_performers": top_performers,
    }
    if verdict is not None:
        aftermath["verdict"] = verdict
    return aftermath


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
    if existing:
        plan = existing
    else:
        prior_intent = load_latest_weekly_plan_intent(conn, state["season_id"], state["week"], state["player_club_id"])
        plan = build_default_weekly_plan(state, intent=intent_override or prior_intent or "Balanced")
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
            policy_values = dict(plan.get("tactics") or {})
            policy_values.update(dict(tactics))
            plan["tactics"] = CoachPolicy.from_dict(policy_values).as_dict()
        lineup_player_ids = update.get("lineup_player_ids")
        if lineup_player_ids:
            plan["lineup"]["player_ids"] = lineup_player_ids

    save_weekly_command_plan(conn, plan)

    if state.get("is_bye"):
        return _simulate_bye_week(conn, state=state, plan=plan, cursor=cursor)

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

    # load_standings already applies the official-vs-legacy sort authoritatively
    # (via match_records.config_version), so reuse its ordering directly.
    standings_before_raw = load_standings(conn, season_id)
    standings_before = list(standings_before_raw)
    prepare_ai_plans_for_matches(
        conn,
        season_id=season_id,
        season=season,
        matches=week_matches,
        clubs=clubs,
        rosters=rosters,
        player_club_id=player_club_id,
        standings_rows=standings_before_raw,
        apply_plan=_apply_command_plan_to_match,
        load_plan=load_weekly_command_plan,
        save_plan=save_weekly_command_plan,
    )

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
    standings_after = list(standings_after_raw)
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
    if not next_chosen:
        # Defensive guard: before going to offseason, scan for any unplayed
        # playoff matches involving the player (catches bracket creation edge cases).
        from dodgeball_sim.playoffs import is_playoff_match_id
        completed_ids = load_completed_match_ids(conn, season_id)
        pending_user_playoff = [
            m for m in season.scheduled_matches
            if is_playoff_match_id(season.season_id, m.match_id)
            and m.match_id not in completed_ids
            and player_club_id in (m.home_club_id, m.away_club_id)
        ]
        if pending_user_playoff:
            next_chosen = pending_user_playoff[:1]
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

    aftermath = _build_aftermath(
        conn,
        dashboard,
        record,
        season_id,
        standings_before,
        standings_after,
        clubs,
        plan=plan,
        player_club_id=player_club_id,
    )

    return {
        "status": "success",
        "message": f"Simulated Week {record.week} command plan.",
        "plan": plan,
        "dashboard": dashboard,
        "next_state": cursor.state.value,
        "aftermath": aftermath,
    }
