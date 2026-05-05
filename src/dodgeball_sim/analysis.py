from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from .events import MatchEvent
from .models import MatchSetup, Team


@dataclass(frozen=True)
class MomentumPoint:
    tick: int
    differential: int  # team_a living - team_b living


@dataclass(frozen=True)
class HeroMoment:
    team_id: str
    player_id: str
    description: str


@dataclass(frozen=True)
class MatchAnalysis:
    momentum: List[MomentumPoint]
    hero: HeroMoment | None


def analyze_match(events: Sequence[MatchEvent], setup: MatchSetup) -> MatchAnalysis:
    team_a = setup.team_a
    team_b = setup.team_b
    living = {team_a.id: len(team_a.players), team_b.id: len(team_b.players)}
    player_to_team = _player_team_map(setup)
    hero_candidate = None
    hero_triggered = False
    timeline: List[MomentumPoint] = []

    for event in events:
        if event.event_type != "throw":
            continue
        player_out = event.outcome.get("player_out")
        if player_out:
            team_id = player_to_team.get(player_out)
            if team_id:
                living[team_id] = max(0, living[team_id] - 1)
        differential = living[team_a.id] - living[team_b.id]
        timeline.append(MomentumPoint(tick=event.tick, differential=differential))
        # track hero: if a team is down to one living player at any time
        for t_id in (team_a.id, team_b.id):
            if living[t_id] == 1 and not hero_triggered:
                survivor = _first_living_player(setup, t_id, events)
                if survivor:
                    hero_candidate = (t_id, survivor)
                    hero_triggered = True

    hero = None
    if hero_candidate:
        team_id, player_id = hero_candidate
        winning_team = _winner_team(events)
        if winning_team == team_id:
            hero = HeroMoment(
                team_id=team_id,
                player_id=player_id,
                description=f"{player_id} stayed alive solo and carried {team_id} to victory!",
            )
    return MatchAnalysis(momentum=timeline, hero=hero)


def _player_team_map(setup: MatchSetup) -> Dict[str, str]:
    mapping = {}
    for team in (setup.team_a, setup.team_b):
        for player in team.players:
            mapping[player.id] = team.id
    return mapping


def _first_living_player(setup: MatchSetup, team_id: str, events: Sequence[MatchEvent]) -> str | None:
    eliminated = set()
    for event in events:
        player_out = event.outcome.get("player_out")
        if player_out:
            eliminated.add(player_out)
    team = setup.team_a if setup.team_a.id == team_id else setup.team_b
    for player in team.players:
        if player.id not in eliminated:
            return player.id
    return None


def _winner_team(events: Sequence[MatchEvent]) -> str | None:
    for event in reversed(events):
        if event.event_type == "match_end":
            return event.outcome.get("winner")
    return None


__all__ = ["MatchAnalysis", "MomentumPoint", "HeroMoment", "analyze_match"]
