from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from .broadcast import load_matchup_broadcast_frame
from .dynasty_office import team_overall
from .models import MatchSetup, Player
from .staff_market import staff_effect_summary


def _humanize_policy(value: str) -> str:
    text = value.replace("_", " ")
    return text[:1].upper() + text[1:]


# Departments whose advisory output shapes how the player prepares for and
# reads the upcoming match. Order controls display order. This surfaces the
# EXISTING staff effect summaries against the next opponent — it does not add
# any in-match staff math (see staff_market honesty rule).
_MATCH_DAY_DEPARTMENTS = ("tactics", "conditioning", "medical")


def _build_staff_impact(department_heads: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not department_heads:
        return []
    by_department = {str(head.get("department")): head for head in department_heads}
    impact: list[dict[str, Any]] = []
    for department in _MATCH_DAY_DEPARTMENTS:
        head = by_department.get(department)
        if head is None:
            continue
        impact.append(
            {
                "department": department,
                "name": str(head.get("name", "")),
                "rating_primary": float(head.get("rating_primary", 0.0)),
                "effect": staff_effect_summary(department),
            }
        )
    return impact


def build_matchup_details(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    opponent_id: str | None,
    rosters: Mapping[str, list[Player]],
    match_id: str | None = None,
    week: int = 1,
    is_bye: bool = False,
    department_heads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    staff_impact = _build_staff_impact(department_heads)
    if not opponent_id:
        return {
            "opponent_record": "n/a" if is_bye else "0-0",
            "last_meeting": "None",
            "key_matchup": "Bye week - no opponent." if is_bye else "Season schedule complete.",
            "broadcast_frame": None,
            "framing_line": "Bye week - no opponent." if is_bye else "Season schedule complete.",
            "staff_impact": staff_impact,
        }

    standing = conn.execute(
        """
        SELECT wins, losses, draws
        FROM season_standings
        WHERE season_id = ? AND club_id = ?
        """,
        (season_id, opponent_id),
    ).fetchone()
    if standing is None:
        opponent_record = "0-0"
    else:
        wins = int(standing["wins"])
        losses = int(standing["losses"])
        draws = int(standing["draws"])
        opponent_record = f"{wins}-{losses}" if draws == 0 else f"{wins}-{losses}-{draws}"

    meeting = conn.execute(
        """
        SELECT week, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
          AND (
            (home_club_id = ? AND away_club_id = ?)
            OR (home_club_id = ? AND away_club_id = ?)
          )
        ORDER BY week DESC, match_id DESC
        LIMIT 1
        """,
        (season_id, player_club_id, opponent_id, opponent_id, player_club_id),
    ).fetchone()
    if meeting is None:
        last_meeting = "First meeting - no tape on them yet. Trust your reads."
    else:
        result = "Draw"
        if meeting["winner_club_id"] == player_club_id:
            result = "Win"
        elif meeting["winner_club_id"] == opponent_id:
            result = "Loss"
        home_survivors = int(meeting["home_survivors"])
        away_survivors = int(meeting["away_survivors"])
        if meeting["home_club_id"] == player_club_id:
            player_score, opp_score = home_survivors, away_survivors
        else:
            player_score, opp_score = away_survivors, home_survivors
        last_meeting = (
            f"Week {int(meeting['week'])}: {result} "
            f"{player_score}-{opp_score}"
        )

    opponent_roster = list(rosters.get(opponent_id, []))
    key_threat: dict[str, Any] | None = None
    if opponent_roster:
        focal_player = max(opponent_roster, key=lambda p: (p.overall_skill(), p.id))
        key_matchup = (
            f"{focal_player.name}, {focal_player.archetype.display_name}, "
            f"{focal_player.overall_skill()} OVR"
        )
        key_threat = {
            "name": focal_player.name,
            "archetype": focal_player.archetype.display_name,
            "ovr": focal_player.overall_skill(),
        }
    else:
        key_matchup = "Opponent roster unavailable."

    broadcast_frame = load_matchup_broadcast_frame(
        conn,
        season_id=season_id,
        player_club_id=player_club_id,
        opponent_club_id=opponent_id,
        match_id=match_id,
        week=week,
    )

    adaptation_summary = None
    if opponent_id and week:
        from .persistence import load_weekly_command_plan
        opponent_plan = load_weekly_command_plan(conn, season_id, week, opponent_id)
        if opponent_plan and "summary" in opponent_plan:
            summary = opponent_plan["summary"]
            if "adapted" in summary.lower():
                adaptation_summary = summary

    return {
        "opponent_record": opponent_record,
        "last_meeting": last_meeting,
        "key_matchup": key_matchup,
        "key_threat": key_threat,
        "broadcast_frame": broadcast_frame.to_dict(),
        "framing_line": (
            broadcast_frame.historical_hook.text
            if broadcast_frame.historical_hook is not None
            else broadcast_frame.stakes_tag.label
        ),
        "adaptation_summary": adaptation_summary,
        "staff_impact": staff_impact,
    }


__all__ = ["build_matchup_details"]


# ----------------------------------------------------------------------
# Matchup preview helper (formerly manager_helpers)
# ----------------------------------------------------------------------

def matchup_preview(setup: MatchSetup) -> str:
    team_a = setup.team_a
    team_b = setup.team_b
    a_overall = team_overall(team_a)
    b_overall = team_overall(team_b)
    stronger = team_a if a_overall >= b_overall else team_b
    weaker = team_b if stronger is team_a else team_a
    delta = abs(a_overall - b_overall)
    team_a_approach = _humanize_policy(team_a.coach_policy.approach.value).lower()
    team_b_focus = _humanize_policy(team_b.coach_policy.target_focus.value).lower()
    style_line = (
        f"{team_a.name} {team_a_approach} approach "
        f"vs {team_b.name} {team_b_focus} targets."
    )
    pressure_line = (
        f"{stronger.name} enters with a {delta:.1f} overall edge. "
        f"{weaker.name} needs catches and chemistry swings to flip the script."
    )
    return f"{style_line}\n{pressure_line}"
