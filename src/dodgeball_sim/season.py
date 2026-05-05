from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .scheduler import ScheduledMatch


@dataclass(frozen=True)
class SeasonResult:
    """Outcome of a single match within a season."""
    match_id: str
    season_id: str
    week: int
    home_club_id: str
    away_club_id: str
    home_survivors: int
    away_survivors: int
    winner_club_id: str | None  # None on draw (time limit)
    seed: int


@dataclass(frozen=True)
class StandingsRow:
    club_id: str
    wins: int
    losses: int
    draws: int
    elimination_differential: int  # survivors accumulated - survivors conceded
    points: int                    # 3 per win, 1 per draw, 0 per loss


@dataclass(frozen=True)
class Season:
    season_id: str
    year: int
    league_id: str
    config_version: str
    ruleset_version: str
    scheduled_matches: Tuple[ScheduledMatch, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "scheduled_matches",
            tuple(
                sorted(
                    self.scheduled_matches,
                    key=lambda match: (
                        match.week,
                        match.match_id,
                        match.home_club_id,
                        match.away_club_id,
                    ),
                )
            ),
        )

    def matches_for_week(self, week: int) -> List[ScheduledMatch]:
        return [m for m in self.scheduled_matches if m.week == week]

    def total_weeks(self) -> int:
        if not self.scheduled_matches:
            return 0
        return max(m.week for m in self.scheduled_matches)


def compute_standings(results: List[SeasonResult]) -> List[StandingsRow]:
    """Derive standings from match results. Pure — no I/O."""
    tally: Dict[str, Dict[str, int]] = {}

    def _ensure(club_id: str) -> None:
        if club_id not in tally:
            tally[club_id] = {"wins": 0, "losses": 0, "draws": 0, "diff": 0}

    for result in results:
        _ensure(result.home_club_id)
        _ensure(result.away_club_id)
        home = tally[result.home_club_id]
        away = tally[result.away_club_id]

        home["diff"] += result.home_survivors - result.away_survivors
        away["diff"] += result.away_survivors - result.home_survivors

        if result.winner_club_id == result.home_club_id:
            home["wins"] += 1
            away["losses"] += 1
        elif result.winner_club_id == result.away_club_id:
            away["wins"] += 1
            home["losses"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1

    rows = []
    for club_id, t in tally.items():
        points = t["wins"] * 3 + t["draws"]
        rows.append(
            StandingsRow(
                club_id=club_id,
                wins=t["wins"],
                losses=t["losses"],
                draws=t["draws"],
                elimination_differential=t["diff"],
                points=points,
            )
        )

    # Sort: points desc, then diff desc, then club_id asc (stable tiebreaker)
    rows.sort(key=lambda r: (-r.points, -r.elimination_differential, r.club_id))
    return rows


__all__ = ["Season", "SeasonResult", "StandingsRow", "compute_standings"]
