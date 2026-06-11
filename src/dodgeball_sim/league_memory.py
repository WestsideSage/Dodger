from __future__ import annotations

import sqlite3
from typing import Any

from .persistence import load_awards, load_league_records, load_rivalry_records


def build_league_memory_state(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    clubs: dict[str, Any],
) -> dict[str, Any]:
    awards = load_awards(conn, season_id)
    record_items = load_league_records(conn)
    rivalry_items = load_rivalry_records(conn)
    recent_matches = conn.execute(
        """
        SELECT match_id, week, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors, scoring_model,
               home_game_points, away_game_points
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 6
        """,
        (season_id,),
    ).fetchall()
    return {
        "records": {
            "items": [_record_item(item) for item in record_items]
            or [{"status": "limited", "text": "The league record books are currently empty. History begins when the first records are ratified."}],
        },
        "awards": {
            "items": [
                {
                    "award_type": award.award_type,
                    "player_id": award.player_id,
                    "club_name": clubs.get(award.club_id).name if award.club_id in clubs else award.club_id,
                    "score": award.award_score,
                }
                for award in awards
            ]
            or [{"status": "limited", "text": "The trophy cabinet awaits. Season awards will be decided and displayed after the offseason closeout."}],
        },
        "rivalries": {
            "items": [
                {
                    "club_a_name": clubs.get(item["club_a_id"]).name if item["club_a_id"] in clubs else item["club_a_id"],
                    "club_b_name": clubs.get(item["club_b_id"]).name if item["club_b_id"] in clubs else item["club_b_id"],
                    "score": item["rivalry"].get("rivalry_score", 0),
                    "meetings": item["rivalry"].get("total_meetings", 0),
                }
                for item in rivalry_items
            ]
            or [{"status": "limited", "text": "True rivalries require history. Bad blood will build here after repeated, high-stakes match results."}],
        },
        "recent_matches": [recent_match_item(row, clubs) for row in recent_matches],
    }


def _record_item(item: dict[str, Any]) -> dict[str, Any]:
    record = item.get("record", {})
    return {
        "record_type": item["record_type"],
        "holder_id": item["holder_id"],
        "holder_type": item["holder_type"],
        "value": item["record_value"],
        "season_id": item["set_in_season"],
        "text": record.get("detail") or f"{item['holder_id']} leads {item['record_type']}.",
    }


def recent_match_item(row: sqlite3.Row, clubs: dict[str, Any]) -> dict[str, Any]:
    home = clubs.get(row["home_club_id"])
    away = clubs.get(row["away_club_id"])
    winner = clubs.get(row["winner_club_id"]) if row["winner_club_id"] else None
    # V20 §7.3 survivors cleanup: official matches score in GAME POINTS; the
    # survivors columns hold the final game's living counts, which can
    # contradict the recorded result (a 2-1 game-points win whose last game
    # ended 0-3 would have read "0-3" with the LOSER named winner here).
    keys = row.keys() if hasattr(row, "keys") else []
    is_official = (
        "scoring_model" in keys and (row["scoring_model"] or "legacy") != "legacy"
    )
    if is_official:
        home_score = int(row["home_game_points"] or 0)
        away_score = int(row["away_game_points"] or 0)
    else:
        home_score = int(row["home_survivors"] or 0)
        away_score = int(row["away_survivors"] or 0)
    return {
        "match_id": row["match_id"],
        "week": int(row["week"]),
        "summary": (
            f"{home.name if home else row['home_club_id']} {home_score}-"
            f"{away_score} {away.name if away else row['away_club_id']}"
        ),
        # The recorded winner_club_id is the single source of truth; the
        # score comparison is only a fallback for rows recorded as draws by
        # genuinely level scores.
        "winner_name": (
            winner.name
            if winner
            else (
                (home.name if home else row["home_club_id"])
                if home_score > away_score
                else (
                    (away.name if away else row["away_club_id"])
                    if away_score > home_score
                    else "Draw"
                )
            )
        ),
    }


__all__ = ["build_league_memory_state", "recent_match_item"]
