from __future__ import annotations

from typing import Sequence
from .league import Club
from .models import Player
from .season import StandingsRow


def choose_ai_intent(
    row: StandingsRow | None,
    *,
    week: int,
    total_weeks: int,
    club: Club,
    roster: Sequence[Player],
) -> str:
    if row is None:
        return "Balanced"
        
    scores = {
        "Balanced": 10.0,
        "Win Now": 10.0,
        "Develop Youth": 10.0,
        "Preserve Health": 10.0,
        "Prepare For Playoffs": 0.0,
    }
    
    games_played = row.wins + row.losses + row.draws
    win_rate = row.wins / games_played if games_played > 0 else 0.5
    
    if games_played >= 3:
        if win_rate > 0.6:
            scores["Win Now"] += 5.0
        elif win_rate < 0.4:
            scores["Develop Youth"] += 6.0
            scores["Preserve Health"] += 3.0
            
    if row.elimination_differential <= -3:
        scores["Preserve Health"] += 8.0
        scores["Develop Youth"] += 4.0
        
    late_season = week >= max(1, total_weeks - 1)
    if late_season:
        if row.wins > row.losses:
            scores["Prepare For Playoffs"] += 15.0
        else:
            scores["Develop Youth"] += 10.0
            scores["Preserve Health"] += 5.0
            
    archetype = club.program_archetype
    if archetype == "Contender":
        scores["Win Now"] += 8.0
        if late_season and row.wins > row.losses:
            scores["Prepare For Playoffs"] += 10.0
    elif archetype == "Development Factory":
        scores["Develop Youth"] += 12.0
    elif archetype == "Defensive Specialist":
        scores["Balanced"] += 4.0
        scores["Win Now"] += 2.0
    elif archetype == "Power Throwers":
        scores["Win Now"] += 5.0
    elif archetype == "Aging Veterans":
        scores["Win Now"] += 4.0
        scores["Preserve Health"] += 6.0
    elif archetype == "Balanced Rebuild":
        scores["Develop Youth"] += 6.0
        scores["Balanced"] += 4.0
        
    return max(scores.keys(), key=lambda k: scores[k])
