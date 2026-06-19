from __future__ import annotations

import sqlite3
from typing import Sequence

from .command_center import DEFAULT_DEPARTMENT_ORDERS
from .league import Club
from .models import Player
from .season import StandingsRow

from .ai_intent import choose_ai_intent as _choose_ai_intent
from .ai_orders import get_ai_department_orders
from .ai_lineup import optimize_archetype_lineup
from .ai_tactics import get_ai_tactics


def choose_ai_intent(
    row: StandingsRow | None,
    *,
    week: int,
    total_weeks: int,
    club: Club | None = None,
    roster: Sequence[Player] | None = None,
) -> str:
    """Wrapper for choose_ai_intent to support legacy test compatibility when club/roster are omitted."""
    if club is None:
        from .league import Club
        from .models import CoachPolicy
        club = Club(
            club_id="test_club",
            name="Test Club",
            colors=("blue", "red"),
            home_region="Midwest",
            founded_year=2026,
            coach_policy=CoachPolicy(),
            program_archetype="Balanced Rebuild",
        )
    if roster is None:
        roster = []
    return _choose_ai_intent(row, week=week, total_weeks=total_weeks, club=club, roster=roster)


def load_recent_user_win_rate(conn: sqlite3.Connection, player_club_id: str, limit: int = 8) -> float:
    """Queries the database for the rolling user win rate over the last N matches."""
    try:
        cursor = conn.execute(
            """
            SELECT winner_team_id, team_a_id, team_b_id
            FROM matches
            WHERE team_a_id = ? OR team_b_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (player_club_id, player_club_id, limit),
        )
        rows = cursor.fetchall()
        if not rows:
            return 0.0
        wins = sum(1 for r in rows if r["winner_team_id"] == player_club_id)
        return wins / len(rows)
    except sqlite3.OperationalError:
        # Schema may not have matches table yet (e.g. during fresh setup/tests)
        return 0.0


def apply_adaptation_shift(plan: dict, archetype: str) -> None:
    """Applies exactly one bounded adaptation shift to the weekly plan against the user."""
    current_intent = plan["intent"]
    shifted_intent = False

    if archetype in ("Contender", "Power Throwers", "Defensive Specialist"):
        if current_intent in ("Balanced", "Prepare For Playoffs"):
            plan["intent"] = "Win Now"
            shifted_intent = True
    else:  # Rebuilding / development focus
        if current_intent in ("Balanced", "Develop Youth"):
            plan["intent"] = "Preserve Health"
            shifted_intent = True

    if shifted_intent:
        plan["summary"] = f"Opponent adapted to your dominant run by shifting their intent to {plan['intent']}."
    else:
        plan["department_orders"]["tactics"] = "film study"
        plan["summary"] = "Opponent adapted to your dominant run by shifting tactics to study extra film."

    plan["lineup"]["summary"] = plan["summary"]


def build_ai_weekly_plan(
    *,
    season_id: str,
    week: int,
    club: Club,
    roster: Sequence[Player],
    standings_row: StandingsRow | None,
    total_weeks: int,
    adapt_to_user: bool = False,
    conn: sqlite3.Connection | None = None,
) -> dict:
    """Builds a weekly plan for an AI club tailored to its archetype, intent, and roster shape."""
    intent = choose_ai_intent(
        standings_row,
        week=week,
        total_weeks=total_weeks,
        club=club,
        roster=roster,
    )
    lineup_ids = optimize_archetype_lineup(roster, club.program_archetype, intent)
    players_by_id = {player.id: player for player in roster}

    orders = get_ai_department_orders(club.program_archetype, intent)
    # V28 The Weather: consume the per-club tactic-drift overlay (emergent meta).
    # The drift folds in after the intent override in get_ai_tactics. Pyramid-
    # gated; legacy saves return {} (no overlay) so tactics are byte-identical.
    drift = None
    if conn is not None:
        from .meta_drift import tactic_drift_for

        drift = tactic_drift_for(conn, club.club_id) or None
    tactics = get_ai_tactics(club.program_archetype, intent, drift=drift)

    plan = {
        "season_id": season_id,
        "week": week,
        "player_club_id": club.club_id,
        "intent": intent,
        "available_intents": [
            "Balanced",
            "Win Now",
            "Develop Youth",
            "Preserve Health",
            "Prepare For Playoffs",
        ],
        "department_orders": orders,
        "tactics": tactics,
        "lineup": {
            "player_ids": lineup_ids,
            "players": [
                {
                    "id": players_by_id[player_id].id,
                    "name": players_by_id[player_id].name,
                    "overall": players_by_id[player_id].overall_skill(),
                }
                for player_id in lineup_ids
                if player_id in players_by_id
            ],
            "summary": f"{intent} lineup chosen by the AI program staff.",
        },
    }

    if adapt_to_user:
        apply_adaptation_shift(plan, club.program_archetype)

    return plan


def prepare_ai_plans_for_matches(
    conn,
    *,
    season_id: str,
    season,
    matches,
    clubs,
    rosters,
    player_club_id: str,
    standings_rows: Sequence[StandingsRow],
    apply_plan,
    load_plan,
    save_plan,
) -> None:
    """Prepares and saves weekly plans for all AI clubs, adapting to the user if they are dominant."""
    user_win_rate = load_recent_user_win_rate(conn, player_club_id, limit=8)
    user_dominant = user_win_rate >= 0.70

    standings_by_club = {row.club_id: row for row in standings_rows}
    for match in matches:
        for club_id in (match.home_club_id, match.away_club_id):
            if club_id == player_club_id:
                continue
            ai_plan = load_plan(conn, season_id, match.week, club_id)
            if ai_plan is None:
                # Check if playing against the user
                is_against_user = (match.home_club_id == player_club_id or match.away_club_id == player_club_id)
                adapt_to_user = is_against_user and user_dominant

                ai_plan = build_ai_weekly_plan(
                    season_id=season_id,
                    week=match.week,
                    club=clubs[club_id],
                    roster=rosters[club_id],
                    standings_row=standings_by_club.get(club_id),
                    total_weeks=season.total_weeks(),
                    adapt_to_user=adapt_to_user,
                    conn=conn,
                )
                save_plan(conn, ai_plan)
            apply_plan(conn, ai_plan, match.match_id, club_id)


__all__ = ["build_ai_weekly_plan", "choose_ai_intent", "prepare_ai_plans_for_matches"]
