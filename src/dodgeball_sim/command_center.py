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


INTENTS = ("Win Now", "Develop Youth", "Preserve Health", "Evaluate Lineup", "Prepare For Playoffs")

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
        "overall": round(player.overall(), 1),
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
        chosen = sorted(roster, key=lambda player: (-player.overall(), player.id))[: min(6, len(roster))]

    if intent == "Develop Youth":
        prospects = sorted(roster, key=lambda player: (-player.traits.potential, player.age, -player.overall()))
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


def build_command_center_state(conn: sqlite3.Connection) -> dict[str, Any]:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
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
    opponent_id = None
    if upcoming is not None:
        opponent_id = upcoming.away_club_id if upcoming.home_club_id == player_club_id else upcoming.home_club_id

    return {
        "season_id": season_id,
        "week": week,
        "player_club_id": player_club_id,
        "player_club": clubs[player_club_id],
        "opponent": clubs.get(opponent_id) if opponent_id else None,
        "upcoming_match": upcoming,
        "roster": list(rosters.get(player_club_id, [])),
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
    tactics = _policy_for_intent(club.coach_policy, intent)
    warnings = _lineup_warnings(list(state["roster"]), lineup["player_ids"], intent, tactics)
    recommendations = _staff_recommendations(heads, intent, opponent.name if opponent else "the next opponent")
    return {
        "season_id": state["season_id"],
        "week": state["week"],
        "player_club_id": state["player_club_id"],
        "intent": intent,
        "available_intents": list(INTENTS),
        "opponent": {
            "club_id": opponent.club_id if opponent else None,
            "name": opponent.name if opponent else "Season complete",
        },
        "department_heads": heads,
        "department_orders": dict(DEFAULT_DEPARTMENT_ORDERS),
        "recommendations": recommendations,
        "warnings": warnings,
        "lineup": lineup,
        "tactics": tactics,
        "history_count": len(state.get("history", [])),
    }


def _staff_recommendations(heads: list[dict[str, Any]], intent: str, opponent_name: str) -> list[dict[str, str]]:
    by_department = {head["department"]: head for head in heads}
    tactic = by_department.get("tactics", {})
    training = by_department.get("training", {})
    medical = by_department.get("medical", {})
    return [
        {
            "department": "Tactics",
            "voice": tactic.get("voice", "Keep the plan simple."),
            "text": f"Prepare for {opponent_name}; {intent.lower()} favors a visible target plan and post-match evidence.",
        },
        {
            "department": "Training",
            "voice": training.get("voice", "Reps have to show up on court."),
            "text": "Fundamentals are the default because they create a real but bounded execution hook in V5.",
        },
        {
            "department": "Medical",
            "voice": medical.get("voice", "Availability is a decision."),
            "text": "Injury prevention is tracked as a fatigue-risk warning, not a full medical model yet.",
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
        if player.id not in starters and player.traits.potential >= 80 and player.overall() >= 55
    ]
    if high_upside_benched and intent != "Win Now":
        warnings.append(f"{high_upside_benched[0].name} has high upside but is outside the recommended reps group.")
    weak_starters = [
        player for player in roster
        if player.id in starters and player.overall() < 55
    ]
    if weak_starters and intent == "Win Now":
        warnings.append(f"{weak_starters[0].name} is a weak starter and may be targeted.")
    if tactics.get("rush_frequency", 0.0) > 0.75:
        warnings.append("High rush frequency can create fatigue pressure; V5 tracks this as a visible risk.")
    if not warnings:
        warnings.append("No obvious lineup or tactics conflict found for this intent.")
    return warnings


def build_post_week_dashboard(conn: sqlite3.Connection, plan: Mapping[str, Any], record: MatchRecord) -> dict[str, Any]:
    clubs = load_clubs(conn)
    player_club_id = str(plan["player_club_id"])
    opponent_id = record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
    won = record.result.winner_team_id == player_club_id
    draw = record.result.winner_team_id is None
    box = record.result.box_score["teams"]
    home_survivors = int(box[record.home_club_id]["totals"]["living"])
    away_survivors = int(box[record.away_club_id]["totals"]["living"])
    score = f"{home_survivors}-{away_survivors}"
    stats = _match_stats(conn, record.match_id)
    target_note = _target_note(stats, player_club_id)
    rush_frequency = float(plan.get("tactics", {}).get("rush_frequency", 0.0))
    fatigue_note = "Conservative rush plan limited fatigue-risk exposure."
    if rush_frequency > 0.65:
        fatigue_note = "Aggressive rush plan raised visible fatigue-risk pressure."
    return {
        "season_id": record.season_id,
        "week": record.week,
        "match_id": record.match_id,
        "opponent_name": clubs[opponent_id].name if opponent_id in clubs else opponent_id,
        "result": "Draw" if draw else ("Win" if won else "Loss"),
        "lanes": [
            {
                "title": "Result",
                "summary": f"{'Drew' if draw else ('Beat' if won else 'Lost to')} {clubs[opponent_id].name if opponent_id in clubs else opponent_id}, survivors {score}.",
                "items": [f"Intent: {plan['intent']}", f"Week {record.week} command record saved."],
            },
            {
                "title": "Why it happened",
                "summary": "Diagnosis is based on the saved plan and match stat tables.",
                "items": [
                    target_note,
                    f"Tactical target-stars setting: {float(plan.get('tactics', {}).get('target_stars', 0.0)):.2f}.",
                    f"Rush frequency setting: {rush_frequency:.2f}.",
                ],
            },
            {
                "title": "Roster health",
                "summary": fatigue_note,
                "items": [f"Medical order: {plan.get('department_orders', {}).get('medical', 'none')}.", "No hidden injury model was applied."],
            },
            {
                "title": "Player movement",
                "summary": "Development effects are reported as intent context in this V5 slice.",
                "items": [f"Training order: {plan.get('department_orders', {}).get('training', 'none')}.", "Youth-rep consequences are preserved in command history."],
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


def _target_note(stats: list[dict[str, Any]], player_club_id: str) -> str:
    club_stats = [row for row in stats if row.get("club_id") == player_club_id]
    if not club_stats:
        return "No player target distribution was available."
    most_targeted = max(club_stats, key=lambda row: (row.get("times_targeted", 0), row.get("player_id", "")))
    return f"Target evidence: {most_targeted['player_id']} was targeted {most_targeted['times_targeted']} times."


__all__ = [
    "INTENTS",
    "build_command_center_state",
    "build_default_weekly_plan",
    "build_post_week_dashboard",
]
