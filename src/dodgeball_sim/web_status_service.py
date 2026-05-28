from __future__ import annotations

import dataclasses
import json
import sqlite3
from typing import Any

from .career_state import CareerStateCursor
from .development import calculate_potential_tier
from .league_memory import recent_match_item
from .models import CoachPolicy
from .persistence import (
    CorruptSaveError,
    get_state,
    load_all_rosters,
    load_awards,
    load_career_state_cursor,
    load_club_roster,
    load_clubs,
    load_completed_match_ids,
    load_lineup_default,
    load_playoff_bracket,
    load_season,
    load_season_outcome,
    load_standings,
    load_weekly_command_plan,
    save_club,
    save_lineup_default,
)
from .playoffs import PLAYOFF_FIELD_SIZE, playoff_stage_label
from .view_models import build_schedule_rows, build_wire_items


def player_archetype_label(player) -> str:
    """Expose the same recruiting-facing label used elsewhere in Plan B.

    Keeps roster, recruit-board, and scout-facing copy aligned.
    """
    from .recruitment import archetype_for_player

    return archetype_for_player(player)


def career_state_payload(cursor: CareerStateCursor) -> dict[str, Any]:
    return {
        "state": cursor.state.value,
        "season_number": cursor.season_number,
        "week": cursor.week,
        "offseason_beat_index": cursor.offseason_beat_index,
        "match_id": cursor.match_id,
    }


def build_status_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    clubs = load_clubs(conn) if player_club_id else {}
    player_club = clubs.get(player_club_id) if player_club_id else None
    season = load_season(conn, season_id) if season_id else None
    return {
        "status": "ok",
        "state": career_state_payload(cursor),
        "context": {
            "season_id": season_id,
            "player_club_id": player_club_id,
            "player_club_name": player_club.name if player_club else player_club_id,
            "season_year": season.year if season else None,
            "ruleset_selection": get_state(conn, "ruleset_selection"),
        },
    }


def build_roster_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    try:
        roster = load_club_roster(conn, player_club_id)
    except (CorruptSaveError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CorruptSaveError("roster save data is damaged") from exc
    lineup = load_lineup_default(conn, player_club_id)

    enriched = []
    for player in roster:
        player_dict = dataclasses.asdict(player)
        player_dict["overall"] = int(round(player.overall_skill()))
        player_dict["role"] = player_archetype_label(player)
        player_dict["potential_tier"] = calculate_potential_tier(player.traits.potential)
        player_dict["scouting_confidence"] = 3
        player_dict["weekly_ovr_history"] = [int(round(player.overall_skill()))]
        if "traits" in player_dict:
            player_dict["traits"].pop("potential", None)
        enriched.append(player_dict)

    return {
        "club_id": player_club_id,
        "roster": enriched,
        "default_lineup": lineup,
    }


def build_tactics_payload(conn: sqlite3.Connection) -> dict[str, str]:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    club = load_clubs(conn).get(player_club_id)
    if club is None:
        raise LookupError("Club not found")
    return club.coach_policy.as_dict()


def update_manual_lineup_payload(
    conn: sqlite3.Connection,
    starter_ids: list[str] | None,
) -> dict[str, Any]:
    """Persist a manual lineup override for the player's club.

    ``starter_ids`` of ``None`` clears the override and lets ``LineupResolver``
    fall back to the roster's natural OVR order. Otherwise the starters are
    structurally validated by ``apply_manual_lineup`` and the resolved order
    (starters + OVR-sorted bench) is saved via ``save_lineup_default``.

    Raises ``LineupViolation`` on structural failure; the route maps the
    ``.reason`` tag to a 400 with the same string so the frontend can show an
    inline error keyed to the offending row.
    """
    from types import SimpleNamespace
    from .lineup import apply_manual_lineup, check_lineup_liabilities

    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    if starter_ids is None:
        conn.execute(
            "DELETE FROM lineup_default WHERE club_id = ?",
            (player_club_id,),
        )
        conn.commit()
        return {"status": "cleared", "warnings": []}

    roster = load_club_roster(conn, player_club_id)
    bundle = SimpleNamespace(club_id=player_club_id, roster=roster)
    result = apply_manual_lineup(bundle, starters=starter_ids)
    save_lineup_default(conn, player_club_id, result.ordered_player_ids)
    conn.commit()

    warnings = check_lineup_liabilities(roster, [s.player_id for s in result.starters])
    return {
        "status": "saved",
        "ordered_player_ids": result.ordered_player_ids,
        "warnings": warnings,
    }


def update_tactics_payload(conn: sqlite3.Connection, policy_values: dict[str, Any]) -> dict[str, str]:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    clubs = load_clubs(conn)
    club = clubs.get(player_club_id)
    if club is None:
        raise LookupError("Club not found")

    new_policy = CoachPolicy.from_dict(policy_values)
    updated_club = dataclasses.replace(club, coach_policy=new_policy)
    roster = load_club_roster(conn, player_club_id)
    save_club(conn, updated_club, roster)
    conn.commit()
    return {"status": "success"}


_CLUB_IDENTITY_LABELS = {
    "aurora": "Scouting Tradition",
    "lunar": "Defensive System",
    "northwood": "Power Throwers",
    "harbor": "Catch Wall",
    "granite": "Swarm Pressure",
    "solstice": "Sniper Control",
}


def build_standings_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    from .persistence import load_program_trajectories
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id:
        raise ValueError("No active season")

    cursor = load_career_state_cursor(conn)
    is_offseason = cursor.state.value in (
        "season_complete_offseason_beat",
        "season_complete_recruitment_pending",
        "next_season_ready",
    )

    clubs = load_clubs(conn)
    saved = {row.club_id: row for row in load_standings(conn, season_id)}
    current_week = current_week_number(conn, season_id)
    rows = []
    for club_id, club in clubs.items():
        row = saved.get(club_id)
        latest_plan = latest_visible_plan(conn, season_id, current_week, club_id)
        trajectories = load_program_trajectories(conn, club_id)
        year_num = len(trajectories) + 1
        # Prefer the curated identity label per club so the standings table
        # reads with distinctive flavor instead of every team converging on
        # the same roster-derived archetype after a season or two.
        identity = _CLUB_IDENTITY_LABELS.get(club_id, club.program_archetype)
        # Note: "Yr N" here is the franchise's tenure year, not the league
        # season number — abbreviated to reduce collision with the season label.
        traj_label = f"Yr {year_num} · {identity}"
        rows.append(
            {
                "club_id": club_id,
                "club_name": club.name,
                "wins": row.wins if row else 0,
                "losses": row.losses if row else 0,
                "draws": row.draws if row else 0,
                "points": row.points if row else 0,
                "elimination_differential": row.elimination_differential if row else 0,
                "is_user_club": club_id == player_club_id,
                "latest_approach": latest_plan["intent"] if latest_plan else "Balanced",
                "program_archetype": club.program_archetype,
                "program_trajectory_label": traj_label,
            }
        )
    rows.sort(key=lambda item: (-item["points"], -item["elimination_differential"], item["club_id"]))

    recent = conn.execute(
        """
        SELECT match_id, week, home_club_id, away_club_id, winner_club_id, home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 5
        """,
        (season_id,),
    ).fetchall()

    season = load_season(conn, season_id)
    return {
        "season_id": season_id,
        "standings": rows,
        "recent_matches": [recent_match_item(row, clubs) for row in recent],
        "total_weeks": season.total_weeks(),
        "current_week": current_week or season.total_weeks(),
        "playoff_spots": PLAYOFF_FIELD_SIZE,
        "is_offseason": is_offseason,
    }


def current_week_number(conn: sqlite3.Connection, season_id: str) -> int | None:
    row = conn.execute(
        "SELECT MIN(week) AS week FROM scheduled_matches WHERE season_id = ?",
        (season_id,),
    ).fetchone()
    if row is None:
        return None
    from .persistence import load_season
    from .game_loop import current_week

    season = load_season(conn, season_id)
    return current_week(conn, season) or season.total_weeks()


def latest_visible_plan(
    conn: sqlite3.Connection,
    season_id: str,
    current_week: int | None,
    club_id: str,
) -> dict[str, Any] | None:
    if current_week is None:
        return None
    row = conn.execute(
        """
        SELECT plan_json
        FROM weekly_command_plans
        WHERE season_id = ? AND club_id = ? AND week <= ?
        ORDER BY week DESC
        LIMIT 1
        """,
        (season_id, club_id, current_week),
    ).fetchone()
    return json.loads(row["plan_json"]) if row else None


def build_schedule_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id:
        raise ValueError("No active season")

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    completed = load_completed_match_ids(conn, season_id)
    rows = []
    for row in build_schedule_rows(season, completed, player_club_id):
        home = clubs.get(row.home_club_id)
        away = clubs.get(row.away_club_id)
        rows.append(
            {
                "match_id": row.match_id,
                "week": row.week,
                "home_club_id": row.home_club_id,
                "home_club_name": home.name if home else row.home_club_id,
                "away_club_id": row.away_club_id,
                "away_club_name": away.name if away else row.away_club_id,
                "status": row.status,
                "is_user_match": row.is_user_match,
                "stage": playoff_stage_label(season_id, row.match_id),
            }
        )
    return {"season_id": season_id, "schedule": rows}


def build_playoff_bracket_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    """Expose the current season's playoff bracket: seeds, rounds, results, champion."""
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        return {"active": False}
    bracket = load_playoff_bracket(conn, season_id)
    if bracket is None:
        return {"active": False}

    clubs = load_clubs(conn)
    player_club_id = get_state(conn, "player_club_id")
    standings = {row.club_id: row for row in load_standings(conn, season_id)}

    results: dict[str, dict[str, Any]] = {}
    for row in conn.execute(
        """
        SELECT match_id, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors, decided_by, narrative_note
        FROM match_records
        WHERE season_id = ?
        """,
        (season_id,),
    ).fetchall():
        results[row["match_id"]] = dict(row)

    def club_name(club_id: str | None) -> str | None:
        if club_id is None:
            return None
        club = clubs.get(club_id)
        return club.name if club else club_id

    seeds = []
    for index, club_id in enumerate(bracket.seeds):
        row = standings.get(club_id)
        seeds.append(
            {
                "seed": index + 1,
                "club_id": club_id,
                "club_name": club_name(club_id),
                "wins": row.wins if row else 0,
                "losses": row.losses if row else 0,
                "draws": row.draws if row else 0,
                "is_player_club": club_id == player_club_id,
            }
        )

    rounds = []
    for round_info in bracket.rounds:
        matches = []
        for match in round_info.get("matches", ()):
            result = results.get(match["match_id"])
            matches.append(
                {
                    "match_id": match["match_id"],
                    "home_club_id": match["home"],
                    "home_club_name": club_name(match["home"]),
                    "away_club_id": match["away"],
                    "away_club_name": club_name(match["away"]),
                    "home_survivors": result["home_survivors"] if result else None,
                    "away_survivors": result["away_survivors"] if result else None,
                    "winner_club_id": result["winner_club_id"] if result else None,
                    "status": "played" if result else "scheduled",
                    "decided_by": (result.get("decided_by") if result else None),
                    "narrative_note": (result.get("narrative_note") if result else None),
                }
            )
        rounds.append({"round": round_info.get("round"), "matches": matches})

    outcome = load_season_outcome(conn, season_id)
    champion_club_id = outcome.champion_club_id if outcome else None

    return {
        "active": True,
        "season_id": season_id,
        "format": bracket.format,
        "status": bracket.status,
        "seeds": seeds,
        "rounds": rounds,
        "champion_club_id": champion_club_id,
        "champion_club_name": club_name(champion_club_id),
        "player_club_id": player_club_id,
    }


def build_news_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise ValueError("No active season")

    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    match_rows = conn.execute(
        """
        SELECT match_id, season_id, week, home_club_id, away_club_id,
               winner_club_id, home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 20
        """,
        (season_id,),
    ).fetchall()
    items = build_wire_items(match_rows, clubs, load_awards(conn, season_id), rosters)
    return {
        "season_id": season_id,
        "items": [
            {"tag": item.tag, "text": item.text, "match_id": item.match_id, "player_id": item.player_id}
            for item in items[:20]
        ],
    }
