from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from .game_loop import current_week
from .models import CoachPolicy, Player
from .persistence import (
    load_all_rosters,
    load_clubs,
    load_command_history,
    load_completed_match_ids,
    load_department_heads,
    load_lineup_default,
    load_season,
    get_state,
)
from .franchise import MatchRecord
from .matchup_details import build_matchup_details
from .playoffs import playoff_stage_label


INTENTS = ("Balanced", "Win Now", "Develop Youth", "Preserve Health", "Prepare For Playoffs")

DEFAULT_DEPARTMENT_ORDERS = {
    "tactics": "opponent prep",
    "training": "fundamentals",
    "conditioning": "balanced maintenance",
    "medical": "injury prevention",
    "scouting": "next opponent",
    "culture": "pressure management",
    "dev_focus": "BALANCED",
}


def _player_summary(player: Player) -> dict[str, Any]:
    return {
        "id": player.id,
        "name": player.name,
        "overall": round(player.overall_skill(), 1),
        "age": player.age,
        "potential": player.traits.potential,
        "stamina": player.ratings.stamina,
    }


def _lineup_recommendation(roster: list[Player], default_lineup: list[str] | None, intent: str) -> dict[str, Any]:
    players_by_id = {player.id: player for player in roster}
    if default_lineup:
        chosen = [players_by_id[player_id] for player_id in default_lineup if player_id in players_by_id]
    else:
        chosen = []
    if len(chosen) < min(6, len(roster)):
        chosen = sorted(roster, key=lambda player: (-player.overall_skill(), player.id))[: min(6, len(roster))]

    if intent == "Develop Youth":
        prospects = sorted(roster, key=lambda player: (-player.traits.potential, player.age, -player.overall_skill()))
        for prospect in prospects:
            if prospect not in chosen and len(chosen) >= 1:
                chosen[-1] = prospect
                break

    return {
        "player_ids": [player.id for player in chosen],
        "players": [_player_summary(player) for player in chosen],
        "summary": f"{intent} lineup built from the current default starters.",
    }


def _policy_for_intent(policy: CoachPolicy, intent: str) -> dict[str, float]:
    values = policy.as_dict()
    if intent == "Win Now":
        values.update({"target_stars": max(values["target_stars"], 0.75), "catch_bias": max(values["catch_bias"], 0.55)})
    elif intent == "Develop Youth":
        values.update({"risk_tolerance": min(values["risk_tolerance"], 0.45), "tempo": min(values["tempo"], 0.45)})
    elif intent == "Preserve Health":
        values.update({"rush_frequency": min(values["rush_frequency"], 0.25), "tempo": min(values["tempo"], 0.35)})
    elif intent == "Prepare For Playoffs":
        values.update({"sync_throws": max(values["sync_throws"], 0.55), "target_ball_holder": max(values["target_ball_holder"], 0.6)})
    return {key: round(float(value), 2) for key, value in values.items()}


from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.voice_pregame import render_matchup_framing
from typing import Iterable
from typing import Iterable
from typing import Iterable

def build_command_center_state(conn: sqlite3.Connection) -> dict[str, Any]:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    root_seed = get_state(conn, "root_seed") or "1"
    if not season_id or not player_club_id:
        raise ValueError("No active season or player club")

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    completed = load_completed_match_ids(conn, season_id)
    week = current_week(conn, season) or 0
    upcoming = next(
        (
            match
            for match in sorted(season.scheduled_matches, key=lambda item: (item.week, item.match_id))
            if match.match_id not in completed and player_club_id in (match.home_club_id, match.away_club_id)
        ),
        None,
    )
    is_bye = (upcoming is None or upcoming.week > week) if week > 0 else False
    opponent_id = None
    if upcoming is not None and not is_bye:
        opponent_id = upcoming.away_club_id if upcoming.home_club_id == player_club_id else upcoming.home_club_id

    return {
        "season_id": season_id,
        "week": week,
        "root_seed": int(root_seed),
        "player_club_id": player_club_id,
        "player_club": clubs[player_club_id],
        "opponent": clubs.get(opponent_id) if opponent_id else None,
        "upcoming_match": upcoming,
        "is_bye": is_bye,
        "matchup_details": build_matchup_details(conn, season_id=season_id, player_club_id=player_club_id, opponent_id=opponent_id, rosters=rosters, is_bye=is_bye),
        "roster": list(rosters.get(player_club_id, [])),
        "opponent_roster": list(rosters.get(opponent_id, [])) if opponent_id else [],
        "default_lineup": load_lineup_default(conn, player_club_id),
        "department_heads": load_department_heads(conn),
        "history": load_command_history(conn, season_id),
    }


def build_default_weekly_plan(state: Mapping[str, Any], intent: str = "Win Now") -> dict[str, Any]:
    if intent not in INTENTS:
        intent = "Win Now"
    club = state["player_club"]
    opponent = state.get("opponent")
    heads = list(state["department_heads"])
    lineup = _lineup_recommendation(list(state["roster"]), state.get("default_lineup"), intent)
    opponent_roster = list(state.get("opponent_roster", []))
    opp_top_six = sorted(opponent_roster, key=lambda p: (-p.overall_skill(), p.id))[:6]
    opponent_lineup = {
        "players": [_player_summary(p) for p in opp_top_six],
    }
    tactics = _policy_for_intent(club.coach_policy, intent)
    warnings = _lineup_warnings(list(state["roster"]), lineup["player_ids"], intent, tactics)
    is_bye = state.get("is_bye", False)
    recommendations = _staff_recommendations(heads, intent, "Bye Week" if is_bye else (opponent.name if opponent else "the next opponent"))
    
    rng = DeterministicRNG(derive_seed(state.get("root_seed", 1), "framing", state["season_id"], str(state["week"])))
    opponent_name = "Bye Week" if is_bye else (opponent.name if opponent else "Season complete")
    matchup_details = {
        "opponent_record": "No record",
        "last_meeting": "None",
        "key_matchup": "No opponent file available.",
        **dict(state.get("matchup_details") or {}),
        "framing_line": render_matchup_framing(club.name, opponent_name, rng),
    }
    
    return {
        "season_id": state["season_id"],
        "week": state["week"],
        "player_club_id": state["player_club_id"],
        "is_bye": is_bye,
        "intent": intent,
        "available_intents": list(INTENTS),
        "opponent": {
            "club_id": opponent.club_id if opponent else None,
            "name": opponent_name,
        },
        "department_heads": heads,
        "department_orders": dict(DEFAULT_DEPARTMENT_ORDERS),
        "recommendations": recommendations,
        "warnings": warnings,
        "lineup": lineup,
        "opponent_lineup": opponent_lineup,
        "tactics": tactics,
        "history_count": len(state.get("history", [])),
        "matchup_details": matchup_details,
    }


def refresh_weekly_plan_context(plan: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    refreshed = dict(plan)
    refreshed["matchup_details"] = {
        **dict(refreshed.get("matchup_details") or {}),
        **dict(state.get("matchup_details") or {}),
    }
    refreshed["is_bye"] = state.get("is_bye", False)
    return refreshed


def _staff_recommendations(heads: list[dict[str, Any]], intent: str, opponent_name: str) -> list[dict[str, str]]:
    by_department = {head["department"]: head for head in heads}
    tactic = by_department.get("tactics", {})
    training = by_department.get("training", {})
    medical = by_department.get("medical", {})
    return [
        {
            "department": "Tactics",
            "voice": tactic.get("voice", "Keep the plan simple."),
            "text": f"Scouting indicates {opponent_name} will challenge our rotations. Align our target plan to exploit their weak side.",
        },
        {
            "department": "Training",
            "voice": training.get("voice", "Reps have to show up on court."),
            "text": "We are prioritizing fundamental drills to build a baseline of consistency across the roster this week.",
        },
        {
            "department": "Medical",
            "voice": medical.get("voice", "Availability is a decision."),
            "text": "Fatigue-risk warnings are elevated for high-workload players. We need to monitor our substitution limits.",
        },
    ]


def _lineup_warnings(roster: list[Player], player_ids: list[str], intent: str, tactics: Mapping[str, float]) -> list[str]:
    from .lineup import check_lineup_liabilities
    starters = set(player_ids)
    warnings: list[str] = []
    
    liabilities = check_lineup_liabilities(roster, player_ids)
    warnings.extend(liabilities)
    
    high_upside_benched = [
        player for player in roster
        if player.id not in starters and player.traits.potential >= 80 and player.overall_skill() >= 55
    ]
    if high_upside_benched and intent != "Win Now":
        warnings.append(f"{high_upside_benched[0].name} has high upside but is outside the recommended reps group.")
    weak_starters = [
        player for player in roster
        if player.id in starters and player.overall_skill() < 55
    ]
    if weak_starters and intent == "Win Now":
        warnings.append(f"{weak_starters[0].name} is a weak starter and may be targeted.")
    if tactics.get("rush_frequency", 0.0) > 0.75:
        warnings.append("Heavy rush pressure is creating extreme fatigue risk. Consider rotating your front line more often.")
    return warnings


def build_post_week_dashboard(conn: sqlite3.Connection, plan: Mapping[str, Any], record: MatchRecord) -> dict[str, Any]:
    from dodgeball_sim.voice_verdict import approach_label_for_intent

    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    player_names = {
        player.id: player.name
        for roster in rosters.values()
        for player in roster
    }
    player_club_id = str(plan["player_club_id"])
    opponent_id = record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
    won = record.result.winner_team_id == player_club_id
    draw = record.result.winner_team_id is None
    box = record.result.box_score["teams"]
    home_survivors = int(box[record.home_club_id]["totals"]["living"])
    away_survivors = int(box[record.away_club_id]["totals"]["living"])
    score = f"{home_survivors}-{away_survivors}"
    stats = _match_stats(conn, record.match_id)
    target_note = _target_note(stats, player_club_id, player_names)
    result = "Draw" if draw else ("Win" if won else "Loss")
    intent = str(plan.get("intent", ""))
    approach_label = approach_label_for_intent(intent)

    return {
        "season_id": record.season_id,
        "week": record.week,
        "match_id": record.match_id,
        "stage": playoff_stage_label(record.season_id, record.match_id),
        "opponent_name": clubs[opponent_id].name if opponent_id in clubs else opponent_id,
        "result": result,
        "lanes": [
            {
                "title": "Result",
                "summary": f"{'Drew' if draw else ('Beat' if won else 'Lost to')} {clubs[opponent_id].name if opponent_id in clubs else opponent_id}, survivors {score}.",
                "items": [f"Approach: {approach_label}", f"Week {record.week} command record saved."],
            },
            {
                "title": "Why it happened",
                "summary": "The clearest tactical read came from who absorbed pressure.",
                "items": [target_note],
            },
            {
                "title": "Roster health",
                "summary": "Roster availability and recovery tracked.",
                "items": [f"Medical order: {plan.get('department_orders', {}).get('medical', 'none')}.", "Staff report no new medical incidents; fitness levels maintained."],
            },
            {
                "title": "Player movement",
                "summary": "Training staff logged their weekly progression observations based on the current command intent.",
                "items": [f"Training order: {plan.get('department_orders', {}).get('training', 'none')}.", "Youth-rep visibility continues to track with recent program trajectory."],
            },
            {
                "title": "Next decisions",
                "summary": "Use the next command plan to respond to this result.",
                "items": [f"Scouting order was {plan.get('department_orders', {}).get('scouting', 'none')}.", "Review warnings before simulating again."],
            },
        ],
    }


def _match_stats(conn: sqlite3.Connection, match_id: str) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,)).fetchall()
    return [dict(row) for row in rows]


def _target_note(stats: list[dict[str, Any]], player_club_id: str, player_names: Mapping[str, str]) -> str:
    club_stats = [row for row in stats if row.get("club_id") == player_club_id]
    if not club_stats:
        return "No player target distribution was available."
    most_targeted = max(club_stats, key=lambda row: (row.get("times_targeted", 0), row.get("player_id", "")))
    player_name = player_names.get(str(most_targeted["player_id"]), "The busiest defender")
    target_count = int(most_targeted.get("times_targeted", 0) or 0)
    if target_count <= 0:
        return "The opponent did not build sustained pressure against one clear defender."
    return f"{player_name} absorbed the most pressure, drawing {target_count} throws."


__all__ = [
    "INTENTS",
    "build_command_center_state",
    "build_default_weekly_plan",
    "build_post_week_dashboard",
]


# ----------------------------------------------------------------------
# Coach policy display helpers (formerly manager_helpers/ui_formatters)
# ----------------------------------------------------------------------

POLICY_KEYS = (
    "target_stars",
    "target_ball_holder",
    "risk_tolerance",
    "sync_throws",
    "rush_frequency",
    "rush_proximity",
    "tempo",
    "catch_bias",
)

def policy_label(value: float) -> str:
    if value >= 0.8:
        return "Very High"
    if value >= 0.65:
        return "High"
    if value >= 0.45:
        return "Balanced"
    if value >= 0.25:
        return "Low"
    return "Very Low"

def policy_effect(key: str, value: float) -> str:
    label = policy_label(value)
    mapping = {
        "target_stars": f"{label} - focuses high-value opponents first.",
        "target_ball_holder": f"{label} - prioritizes opponents controlling the ball.",
        "risk_tolerance": f"{label} - accepts tighter odds for outs.",
        "sync_throws": f"{label} - looks for coordinated volleys and stamina burn.",
        "rush_frequency": f"{label} - changes how often the team forces pressure.",
        "rush_proximity": f"{label} - adjusts how close rushes must be before pressure.",
        "tempo": f"{label} - sets the pace of possessions and resets.",
        "catch_bias": f"{label} - changes how willingly defenders try catches.",
    }
    return mapping.get(key, label)

def policy_rows(policy: CoachPolicy) -> Iterable[tuple[str, float, str]]:
    policy_dict = policy.as_dict()
    for key in (
        "target_stars",
        "target_ball_holder",
        "risk_tolerance",
        "sync_throws",
        "rush_frequency",
        "rush_proximity",
        "tempo",
        "catch_bias",
    ):
        value = policy_dict[key]
        yield key.replace("_", " ").title(), value, policy_effect(key, value)
