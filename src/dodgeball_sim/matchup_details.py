from __future__ import annotations

import sqlite3
from typing import Mapping

from .models import Player, MatchSetup
from .dynasty_office import team_overall
from .models import MatchSetup
from .dynasty_office import team_overall


def _policy_label(value: float) -> str:
    if value >= 0.8:
        return "Very High"
    if value >= 0.65:
        return "High"
    if value >= 0.45:
        return "Balanced"
    if value >= 0.25:
        return "Low"
    return "Very Low"


policy_label = _policy_label


def build_matchup_details(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    opponent_id: str | None,
    rosters: Mapping[str, list[Player]],
    is_bye: bool = False,
) -> dict[str, str]:
    if not opponent_id:
        return {
            "opponent_record": "n/a" if is_bye else "0-0",
            "last_meeting": "None",
            "key_matchup": "Bye week — no opponent." if is_bye else "Season schedule complete.",
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
        last_meeting = "First meeting — no tape on them yet. Trust your reads."
    else:
        result = "Draw"
        if meeting["winner_club_id"] == player_club_id:
            result = "Win"
        elif meeting["winner_club_id"] == opponent_id:
            result = "Loss"
        last_meeting = f"Week {int(meeting['week'])}: {result} {int(meeting['home_survivors'])}-{int(meeting['away_survivors'])}"

    opponent_roster = list(rosters.get(opponent_id, []))
    if opponent_roster:
        focal_player = max(opponent_roster, key=lambda p: (p.overall_skill(), p.id))
        key_matchup = (
            f"{focal_player.name}, {focal_player.archetype.display_name}, "
            f"{round(focal_player.overall_skill())} OVR"
        )
    else:
        key_matchup = "Opponent roster unavailable."

    return {
        "opponent_record": opponent_record,
        "last_meeting": last_meeting,
        "key_matchup": key_matchup,
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
    style_line = (
        f"{team_a.name} tempo {policy_label(team_a.coach_policy.tempo)} vs "
        f"{team_b.name} risk {policy_label(team_b.coach_policy.risk_tolerance)}."
    )
    pressure_line = (
        f"{stronger.name} enters with a {delta:.1f} overall edge. "
        f"{weaker.name} needs catches and chemistry swings to flip the script."
    )
    return f"{style_line}\n{pressure_line}"



def _policy_label(value: float) -> str:
    if value >= 0.8:
        return "Very High"
    if value >= 0.65:
        return "High"
    if value >= 0.45:
        return "Balanced"
    if value >= 0.25:
        return "Low"
    return "Very Low"


policy_label = _policy_label
