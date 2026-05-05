from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .events import MatchEvent
from .models import MatchSetup, Player, Team
from .setup_loader import match_setup_from_dict


@dataclass(frozen=True)
class Lookup:
    team_names: Mapping[str, str]
    player_names: Mapping[str, str]

    def team(self, team_id: str) -> str:
        return self.team_names.get(team_id, team_id)

    def player(self, player_id: str) -> str:
        return self.player_names.get(player_id, player_id)


def build_lookup_from_setup(setup: MatchSetup | Dict[str, Any]) -> Lookup:
    if isinstance(setup, MatchSetup):
        teams = {setup.team_a.id: setup.team_a.name, setup.team_b.id: setup.team_b.name}
        players = _players_from_teams(setup.team_a, setup.team_b)
    else:
        constructed = match_setup_from_dict(setup)
        teams = {constructed.team_a.id: constructed.team_a.name, constructed.team_b.id: constructed.team_b.name}
        players = _players_from_teams(constructed.team_a, constructed.team_b)
    return Lookup(team_names=teams, player_names=players)


def _players_from_teams(team_a: Team, team_b: Team) -> Dict[str, str]:
    names: Dict[str, str] = {}
    for team in (team_a, team_b):
        for player in team.players:
            names[player.id] = player.name
    return names


def narrate_event(event: MatchEvent, lookup: Lookup) -> str:
    tick = event.tick
    if event.event_type == "match_start":
        team_a = lookup.team(event.actors.get("team_a", "team_a"))
        team_b = lookup.team(event.actors.get("team_b", "team_b"))
        return f"Tick {tick}: {team_a} vs {team_b} is underway."
    if event.event_type == "match_end":
        winner = event.outcome.get("winner")
        if winner:
            return f"Tick {tick}: {lookup.team(winner)} wins the match."
        return f"Tick {tick}: Match ends in a draw."
    if event.event_type == "throw":
        offense = lookup.team(event.actors.get("offense_team", ""))
        defense = lookup.team(event.actors.get("defense_team", ""))
        thrower = lookup.player(event.actors.get("thrower", ""))
        target = lookup.player(event.actors.get("target", ""))
        resolution = event.outcome.get("resolution", "unknown")
        if resolution == "hit":
            return f"Tick {tick}: {offense}'s {thrower} drills {target} from {defense}! {target} is OUT."
        if resolution == "dodged":
            return f"Tick {tick}: {target} from {defense} dodges {thrower}'s throw."
        if resolution == "catch":
            return f"Tick {tick}: {target} snares {thrower}'s throw and eliminates {thrower}!"
        if resolution == "failed_catch":
            return f"Tick {tick}: {target} bobbles the catch from {thrower} and is OUT."
        if resolution == "miss":
            return f"Tick {tick}: {thrower} misses wide against {target}."
        return f"Tick {tick}: {thrower} vs {target} resolves with {resolution}."
    return f"Tick {tick}: {event.event_type} event occurred."


__all__ = ["Lookup", "build_lookup_from_setup", "narrate_event"]
