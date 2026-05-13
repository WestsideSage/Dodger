from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from .models import Player


def build_matchup_details(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    opponent_id: str | None,
    rosters: Mapping[str, list[Player]],
) -> dict[str, str]:
    if not opponent_id:
        return {
            "opponent_record": "0-0",
            "last_meeting": "None",
            "key_matchup": "Season schedule complete.",
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
        last_meeting = "None"
    else:
        result = "Draw"
        if meeting["winner_club_id"] == player_club_id:
            result = "Win"
        elif meeting["winner_club_id"] == opponent_id:
            result = "Loss"
        last_meeting = f"Week {int(meeting['week'])}: {result} {int(meeting['home_survivors'])}-{int(meeting['away_survivors'])}"

    opponent_roster = list(rosters.get(opponent_id, []))
    if opponent_roster:
        focal_player = max(opponent_roster, key=lambda p: (p.overall(), p.id))
        key_matchup = f"{focal_player.name}, {focal_player.archetype.value}, {round(focal_player.overall())} OVR"
    else:
        key_matchup = "Opponent roster unavailable."

    return {
        "opponent_record": opponent_record,
        "last_meeting": last_meeting,
        "key_matchup": key_matchup,
    }


__all__ = ["build_matchup_details"]
