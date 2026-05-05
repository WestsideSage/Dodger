from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .copy_quality import title_label
from .league import Club
from .models import Player


@dataclass(frozen=True)
class ScheduleRow:
    match_id: str
    week: int
    home_club_id: str
    away_club_id: str
    status: str
    is_user_match: bool


@dataclass(frozen=True)
class WireItem:
    tag: str
    text: str
    match_id: Optional[str] = None
    player_id: Optional[str] = None


def normalize_root_seed(value: Any, *, default_on_invalid: bool = False) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        if default_on_invalid:
            return 1
        raise ValueError("root_seed must be an integer") from exc
    if normalized < 0:
        if default_on_invalid:
            return 1
        raise ValueError("root_seed must be a non-negative integer")
    return normalized


def build_schedule_rows(
    season,
    completed_match_ids: Iterable[str],
    user_club_id: Optional[str],
) -> List[ScheduleRow]:
    """Return schedule rows with played/open status and user-match flag."""
    completed = set(completed_match_ids)
    rows: List[ScheduleRow] = []
    for match in season.scheduled_matches:
        rows.append(
            ScheduleRow(
                match_id=match.match_id,
                week=match.week,
                home_club_id=match.home_club_id,
                away_club_id=match.away_club_id,
                status="played" if match.match_id in completed else "open",
                is_user_match=user_club_id in (match.home_club_id, match.away_club_id),
            )
        )
    return rows


def build_wire_items(
    match_rows: Iterable[Mapping[str, Any]] | sqlite3.Connection,
    clubs: Optional[Mapping[str, Club]] = None,
    awards: Iterable[Any] = (),
    rosters: Optional[Mapping[str, List[Player]]] = None,
    season_id: Optional[str] = None,
    current_week: Optional[int] = None,
) -> List[Any]:
    """Build a factual League Wire from saved results and awards."""
    if isinstance(match_rows, sqlite3.Connection):
        conn = match_rows
        season_num = 1
        if season_id and season_id.rsplit("_", 1)[-1].isdigit():
            season_num = int(season_id.rsplit("_", 1)[-1])
        from .persistence import load_prospect_pool, load_scouting_domain_events_for_season

        pool_by_id = {prospect.player_id: prospect for prospect in load_prospect_pool(conn, season_num)}
        items: List[Dict[str, Any]] = []
        for event in load_scouting_domain_events_for_season(conn, season_num):
            if current_week is not None and event["week"] > current_week:
                continue
            if event["event_type"] == "CEILING_REVEALED" and event["payload"].get("label") == "HIGH_CEILING":
                prospect = pool_by_id.get(event["player_id"])
                if prospect:
                    items.append(
                        {
                            "tag": "RECRUITING",
                            "headline": "Scouts in your room are buzzing",
                            "body": f"Word travels - your scouts can't stop talking about {prospect.name}. Draft Day will tell.",
                            "week": event["week"],
                        }
                    )
        return items

    if clubs is None:
        clubs = {}
    player_names = {
        player.id: player.name
        for roster in (rosters or {}).values()
        for player in roster
    }

    def _display_player_name(player_id: str) -> str:
        if player_id in player_names:
            return player_names[player_id]
        return player_id.replace("_", " ").replace("-", " ").title()

    items: List[WireItem] = []
    for row in sorted(match_rows, key=lambda item: (item["week"], item["match_id"]), reverse=True):
        home = clubs[row["home_club_id"]]
        away = clubs[row["away_club_id"]]
        winner_id = row["winner_club_id"]
        if winner_id in clubs:
            winner = clubs[winner_id]
            loser = away if winner_id == home.club_id else home
            tag = "RESULT"
            text = f"Week {row['week']}: {winner.name} beat {loser.name} with {row['home_survivors']}-{row['away_survivors']} survivors."
        else:
            tag = "RESULT"
            text = f"Week {row['week']}: {home.name} and {away.name} finished level."
        items.append(WireItem(tag=tag, text=text, match_id=row["match_id"]))

    for award in awards:
        club_name = clubs[award.club_id].name if award.club_id in clubs else award.club_id
        player_name = _display_player_name(award.player_id)
        items.insert(
            0,
            WireItem(
                tag="AWARD",
                text=f"{title_label(award.award_type)}: {player_name} of {club_name}.",
                player_id=award.player_id,
            ),
        )
    return items


__all__ = [
    "ScheduleRow",
    "WireItem",
    "build_schedule_rows",
    "build_wire_items",
    "normalize_root_seed",
]
