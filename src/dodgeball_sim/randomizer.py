from __future__ import annotations

import random
from typing import Iterable

from .models import CoachPolicy, MatchSetup, Player, PlayerArchetype, PlayerRatings, PlayerTraits, Team
from .persistence import match_setup_to_dict
from .setup_loader import match_setup_from_dict

_PLAYER_STATS = ("accuracy", "power", "dodge", "catch", "stamina", "tactical_iq")
_TEAM_NAMES = [
    "Aurora", "Lunar", "Nebula", "Vanguard", "Echo", "Solstice", "Ion", "Blaze",
    "Harbor", "Atlas", "Mirage", "Circuit",
    "Apex", "Prism", "Quasar", "Titan", "Comet", "Zephyr", "Vector", "Summit",
    "Bastion", "Radiant", "Nexus", "Fractal",
]
_SUFFIXES = [
    "Pilots", "Jets", "Sentinels", "Shadows", "Storm", "Orbit", "Flux",
    "Surge", "Blades", "Raptors", "Havoc", "Crush", "Volts", "Breach",
    "Raze", "Wraith", "Charge", "Forge", "Hawks", "Lancers", "Comets", "Drift",
]
_FIRST_NAMES = [
    "Rin", "Avery", "Kai", "River", "Mara", "Ezra", "Sloane", "Jules", "Remy", "Quinn",
    "Drew", "Sage", "Blake", "Reese", "Skye", "Morgan", "Bex", "Lex", "Cass", "Wren",
    "Lux", "Soren", "Brin", "Zoe", "Arlo", "Tate", "Fenn", "Lane", "Yuki", "Hana",
    "Sora", "Nori", "Kenji", "Zhen", "Lin", "Cruz", "Lena", "Nico", "Sol", "Vera",
    "Dex", "Nola", "Zara", "Kemi", "Noa", "Ayo", "Amara", "Zuri", "Mira", "Sasha",
    "Orin", "Saga", "Leif", "Lyra", "Cade", "Nex", "Tyne", "Vale", "Zeph", "Arc",
    "Dray", "Pix", "Priya", "Kiran",
]
_LAST_NAMES = [
    "Voss", "Helix", "Turner", "Lark", "Orion", "Vega", "Keene", "Hart", "Rowe", "Slate",
    "Nova", "Crest", "Prism", "Zenith", "Aura", "Apex", "Corona", "Lyric", "Solace", "Meridian",
    "Steel", "Forge", "Colt", "Flint", "Holt", "Drake", "Crane", "Bolt", "Cross", "Braun",
    "Ash", "Moss", "Stone", "Fern", "Brook", "Vale", "Reed", "Shore", "Wilder", "Gale",
    "Fox", "Knox", "Ward", "Dale", "Kade", "Bloom", "March", "Stowe", "Kwan", "Archer",
    "Rayne", "Mercer", "Frost", "Pierce", "Marsh", "Valdez", "Okafor", "Sato", "Dusk", "Mace",
    "Vane", "Hale", "Spire", "Cray",
]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def randomize_setup(setup: MatchSetup, variation: float = 8.0, seed: int | None = None) -> MatchSetup:
    rng = random.Random(seed)
    payload = match_setup_to_dict(setup)
    for key in ("team_a", "team_b"):
        team = payload[key]
        team["chemistry"] = _clamp(team.get("chemistry", 0.5) + rng.uniform(-0.1, 0.1), 0.0, 1.0)
        policy = team.get("coach_policy", {})
        for policy_key, val in list(policy.items()):
            policy[policy_key] = _clamp(val + rng.uniform(-0.15, 0.15), 0.0, 1.0)
        for player in team.get("players", []):
            ratings = player.get("ratings", {})
            for stat in _PLAYER_STATS:
                base = ratings.get(stat, 60.0)
                ratings[stat] = _clamp(base + rng.uniform(-variation, variation), 25.0, 98.0)
            player["ratings"] = ratings
    return match_setup_from_dict(payload)


def generate_random_setup(seed: int | None = None, min_players: int = 3, max_players: int = 5) -> MatchSetup:
    rng = random.Random(seed)
    team_a = _random_team(rng, min_players, max_players)
    team_b = _random_team(rng, min_players, max_players)
    return MatchSetup(team_a=team_a, team_b=team_b, config_version="phase1.v1")


def _random_team(rng: random.Random, min_players: int, max_players: int) -> Team:
    team_name = f"{rng.choice(_TEAM_NAMES)} {rng.choice(_SUFFIXES)}"
    team_id = team_name.lower().replace(" ", "_")
    policy = CoachPolicy(
        target_stars=_clamp(rng.random(), 0.2, 0.9),
        target_ball_holder=_clamp(rng.random(), 0.2, 0.9),
        risk_tolerance=_clamp(rng.random(), 0.2, 0.9),
        sync_throws=_clamp(rng.random(), 0.1, 0.8),
        rush_frequency=_clamp(rng.random(), 0.2, 0.9),
        rush_proximity=_clamp(rng.random(), 0.2, 0.9),
        tempo=_clamp(rng.random(), 0.3, 0.8),
        catch_bias=_clamp(rng.random(), 0.2, 0.9),
    )
    count = rng.randint(min_players, max_players)
    players = []
    for idx in range(count):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        name = f"{first} {last}"
        
        archetype = rng.choice(list(PlayerArchetype))
        if archetype == PlayerArchetype.POWER:
            p_bias, a_bias, c_bias, d_bias, s_bias, t_bias = 75, 60, 60, 55, 65, 55
        elif archetype == PlayerArchetype.AGILITY:
            p_bias, a_bias, c_bias, d_bias, s_bias, t_bias = 55, 60, 70, 75, 65, 55
        elif archetype == PlayerArchetype.PRECISION:
            p_bias, a_bias, c_bias, d_bias, s_bias, t_bias = 60, 75, 65, 60, 60, 60
        elif archetype == PlayerArchetype.DEFENSE:
            p_bias, a_bias, c_bias, d_bias, s_bias, t_bias = 65, 55, 75, 60, 65, 60
        else: # TACTICAL
            p_bias, a_bias, c_bias, d_bias, s_bias, t_bias = 55, 65, 65, 60, 65, 75

        ratings = PlayerRatings(
            power=_clamp(rng.gauss(p_bias, 12), 30, 95),
            accuracy=_clamp(rng.gauss(a_bias, 12), 30, 95),
            catch=_clamp(rng.gauss(c_bias, 12), 30, 95),
            dodge=_clamp(rng.gauss(d_bias, 12), 30, 95),
            stamina=_clamp(rng.gauss(s_bias, 10), 35, 95),
            tactical_iq=_clamp(rng.gauss(t_bias, 12), 30, 95),
        ).apply_bounds()
        
        players.append(
            Player(
                id=f"{team_id}_p{idx+1}",
                name=name,
                ratings=ratings,
                traits=PlayerTraits(),
                archetype=archetype,
            )
        )
    return Team(
        id=team_id,
        name=team_name,
        players=tuple(players),
        coach_policy=policy,
        chemistry=_clamp(rng.uniform(0.3, 0.9), 0.0, 1.0),
    )


__all__ = ["generate_random_setup", "randomize_setup"]