from __future__ import annotations

import json
import sqlite3
from typing import Any

from .awards import compute_match_mvp
from .career_state import CareerState, advance
from .match_orchestration import _choose_next_user_match_after_automation
from .persistence import (
    fetch_match,
    fetch_roster_snapshot,
    get_state,
    load_career_state_cursor,
    load_clubs,
    load_command_history,
    load_season,
    save_career_state_cursor,
)
from .replay_proof import build_replay_proof, event_detail, event_label
from .stats import PlayerMatchStats
from .web_status_service import career_state_payload


class ReplayError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def match_replay_payload(conn: sqlite3.Connection, match_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM match_records WHERE match_id = ?", (match_id,)).fetchone()
    if row is None:
        raise ReplayError("Match not found", status_code=404)
    if row["engine_match_id"] is None:
        raise ReplayError("Match replay is not available", status_code=409)

    clubs = load_clubs(conn)
    home = clubs.get(row["home_club_id"])
    away = clubs.get(row["away_club_id"])
    if home is None or away is None:
        raise ReplayError("Match club data is damaged", status_code=409)

    try:
        stored = fetch_match(conn, int(row["engine_match_id"]))
    except (KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ReplayError("Match replay data is damaged", status_code=409) from exc

    snapshots = roster_snapshots(conn, match_id, row["home_club_id"], row["away_club_id"])
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
    events = [
        {
            **event,
            "index": index,
            "label": event_label(event, name_map),
            "detail": event_detail(event, name_map),
        }
        for index, event in enumerate(stored["events"])
    ]

    stats = stats_for_match(conn, match_id)
    proof = build_replay_proof(
        stored["events"],
        name_map=name_map,
        roster_snapshots=snapshots,
        home_club_id=row["home_club_id"],
        away_club_id=row["away_club_id"],
        home_survivors=row["home_survivors"],
        away_survivors=row["away_survivors"],
        player_match_stats=stats,
        command_plan=command_plan_for_match(conn, match_id, row["season_id"]),
    )
    top = sorted(stats.items(), key=lambda item: (-score_player(item[1]), item[0]))[:6]
    top_performers = [
        {
            "player_id": player_id,
            "player_name": name_map.get(player_id, player_id),
            "club_name": (clubs.get(player_club_map.get(player_id, "")) or home).name,
            "score": round(score_player(stat), 1),
            "eliminations_by_throw": stat.eliminations_by_throw,
            "catches_made": stat.catches_made,
            "dodges_successful": stat.dodges_successful,
        }
        for player_id, stat in top
        if score_player(stat) > 0
    ]
    mvp_id = compute_match_mvp(stats)
    winner_id = row["winner_club_id"]
    winner_name = clubs[winner_id].name if winner_id in clubs else "Draw"
    report = {
        "winner_name": winner_name,
        "match_mvp_player_id": mvp_id,
        "match_mvp_name": name_map.get(mvp_id, mvp_id) if mvp_id else None,
        "top_performers": top_performers,
        "turning_point": next(
            (
                event["label"]
                for event in events
                if event.get("event_type") == "throw"
                and event.get("outcome", {}).get("resolution") in {"hit", "failed_catch", "catch"}
            ),
            "No high-leverage swing detected.",
        ),
        "evidence_lanes": proof["evidence_report"]["evidence_lanes"],
    }
    return {
        "match_id": match_id,
        "season_id": row["season_id"],
        "week": row["week"],
        "home_club_id": row["home_club_id"],
        "home_club_name": home.name,
        "away_club_id": row["away_club_id"],
        "away_club_name": away.name,
        "winner_club_id": winner_id,
        "winner_name": winner_name,
        "home_survivors": row["home_survivors"],
        "away_survivors": row["away_survivors"],
        "events": events,
        "proof_events": proof["proof_events"],
        "key_play_indices": proof["key_play_indices"],
        "report": report,
    }


def acknowledge_match_payload(conn: sqlite3.Connection, match_id: str) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING or cursor.match_id != match_id:
        raise ReplayError("No matching report is pending", status_code=409)
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise ReplayError("No active season")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    season, chosen, _stop_reason = _choose_next_user_match_after_automation(
        conn,
        season,
        clubs,
        get_state(conn, "player_club_id") or "",
    )
    if chosen:
        cursor = advance(cursor, CareerState.SEASON_ACTIVE_PRE_MATCH, week=chosen[0].week, match_id=None)
    else:
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    save_career_state_cursor(conn, cursor)
    conn.commit()
    return {"status": "success", "state": career_state_payload(cursor)}


def roster_snapshots(conn: sqlite3.Connection, match_id: str, home_club_id: str, away_club_id: str) -> dict[str, list[dict[str, Any]]]:
    try:
        return {
            home_club_id: fetch_roster_snapshot(conn, match_id, home_club_id),
            away_club_id: fetch_roster_snapshot(conn, match_id, away_club_id),
        }
    except (KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ReplayError("Match roster snapshot is damaged.", status_code=409) from exc


def command_plan_for_match(conn: sqlite3.Connection, match_id: str, season_id: str) -> dict[str, Any] | None:
    for record in load_command_history(conn, season_id):
        if record.get("match_id") == match_id:
            plan = record.get("plan")
            return plan if isinstance(plan, dict) else None
    return None


def stats_for_match(conn: sqlite3.Connection, match_id: str) -> dict[str, PlayerMatchStats]:
    rows = conn.execute("SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,)).fetchall()
    return {
        row["player_id"]: PlayerMatchStats(
            throws_attempted=row["throws_attempted"],
            throws_on_target=row["throws_on_target"],
            eliminations_by_throw=row["eliminations_by_throw"],
            catches_attempted=row["catches_attempted"],
            catches_made=row["catches_made"],
            times_targeted=row["times_targeted"],
            dodges_successful=row["dodges_successful"],
            times_hit=row["times_hit"],
            times_eliminated=row["times_eliminated"],
            revivals_caused=row["revivals_caused"],
            clutch_events=row["clutch_events"],
            elimination_plus_minus=row["elimination_plus_minus"],
            minutes_played=row["minutes_played"],
        )
        for row in rows
    }


def score_player(stats: PlayerMatchStats | None) -> float:
    if stats is None:
        return 0.0
    return (
        stats.eliminations_by_throw * 3.0
        + stats.catches_made * 4.0
        + stats.dodges_successful * 1.5
        + stats.revivals_caused * 2.0
        - stats.times_eliminated * 2.0
        + stats.clutch_events
    )
