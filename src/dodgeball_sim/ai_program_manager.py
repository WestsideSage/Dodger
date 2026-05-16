from __future__ import annotations

from typing import Sequence

from .command_center import DEFAULT_DEPARTMENT_ORDERS, _policy_for_intent
from .league import Club
from .lineup import optimize_ai_lineup
from .models import Player
from .season import StandingsRow


def choose_ai_intent(row: StandingsRow | None, *, week: int, total_weeks: int) -> str:
    if row is None:
        return "Balanced"
    games_played = row.wins + row.losses + row.draws
    late_season = week >= max(1, total_weeks - 1)
    if late_season and row.wins > row.losses:
        return "Prepare For Playoffs"
    if games_played >= 3 and row.losses > row.wins:
        return "Develop Youth"
    if row.elimination_differential <= -3:
        return "Preserve Health"
    if row.wins >= row.losses + 1:
        return "Win Now"
    return "Balanced"


def build_ai_weekly_plan(
    *,
    season_id: str,
    week: int,
    club: Club,
    roster: Sequence[Player],
    standings_row: StandingsRow | None,
    total_weeks: int,
) -> dict:
    intent = choose_ai_intent(standings_row, week=week, total_weeks=total_weeks)
    lineup_ids = optimize_ai_lineup(roster)
    players_by_id = {player.id: player for player in roster}
    return {
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
        "department_orders": dict(DEFAULT_DEPARTMENT_ORDERS),
        "tactics": _policy_for_intent(club.coach_policy, intent),
        "lineup": {
            "player_ids": lineup_ids,
            "players": [
                {
                    "id": players_by_id[player_id].id,
                    "name": players_by_id[player_id].name,
                    "overall": round(players_by_id[player_id].overall(), 1),
                }
                for player_id in lineup_ids
                if player_id in players_by_id
            ],
            "summary": f"{intent} lineup chosen by the AI program staff.",
        },
    }


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
    standings_by_club = {row.club_id: row for row in standings_rows}
    for match in matches:
        for club_id in (match.home_club_id, match.away_club_id):
            if club_id == player_club_id:
                continue
            ai_plan = load_plan(conn, season_id, match.week, club_id)
            if ai_plan is None:
                ai_plan = build_ai_weekly_plan(
                    season_id=season_id,
                    week=match.week,
                    club=clubs[club_id],
                    roster=rosters[club_id],
                    standings_row=standings_by_club.get(club_id),
                    total_weeks=season.total_weeks(),
                )
                save_plan(conn, ai_plan)
            apply_plan(conn, ai_plan, match.match_id, club_id)


__all__ = ["build_ai_weekly_plan", "choose_ai_intent", "prepare_ai_plans_for_matches"]
