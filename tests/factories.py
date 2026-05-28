from __future__ import annotations

from typing import Iterable

from dodgeball_sim.archetype_derivation import derive_archetype
from dodgeball_sim.models import CoachPolicy, MatchSetup, Player, PlayerArchetype, PlayerRatings, PlayerTraits, Team


def make_player(
    player_id: str,
    *,
    name: str | None = None,
    accuracy: float = 60.0,
    power: float = 60.0,
    dodge: float = 60.0,
    catch: float = 60.0,
    stamina: float = 60.0,
    tactical_iq: float = 50.0,
    catch_courage: float = 50.0,
    throw_selection_iq: float = 50.0,
    conditioning_curve: float = 50.0,
    archetype: PlayerArchetype | None = None,
) -> Player:
    ratings = PlayerRatings(
        accuracy=accuracy,
        power=power,
        dodge=dodge,
        catch=catch,
        stamina=stamina,
        tactical_iq=tactical_iq,
        catch_courage=catch_courage,
        throw_selection_iq=throw_selection_iq,
        conditioning_curve=conditioning_curve,
    ).apply_bounds()
    return Player(
        id=player_id,
        name=name or player_id.title(),
        ratings=ratings,
        archetype=archetype or derive_archetype(ratings),
        traits=PlayerTraits(),
    )


def make_team(
    team_id: str,
    players: Iterable[Player],
    *,
    policy: CoachPolicy | None = None,
    chemistry: float = 0.5,
    name: str | None = None,
) -> Team:
    return Team(
        id=team_id,
        name=name or team_id.title(),
        players=tuple(players),
        coach_policy=policy or CoachPolicy(),
        chemistry=chemistry,
    )


def make_match_setup(team_a: Team, team_b: Team, *, config_version: str = "phase1.v1") -> MatchSetup:
    return MatchSetup(team_a=team_a, team_b=team_b, config_version=config_version)


__all__ = ["make_player", "make_team", "make_match_setup"]
