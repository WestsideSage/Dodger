from __future__ import annotations

import random

from .archetype_derivation import derive_archetype, primary_and_secondary_bases
from .models import (
    Approach,
    CatchPosture,
    CoachPolicy,
    MatchSetup,
    OpeningRushCommit,
    OpeningRushTarget,
    Player,
    PlayerArchetype,
    PlayerRatings,
    PlayerTraits,
    TargetFocus,
    Team,
)
from .persistence import match_setup_to_dict
from .setup_loader import match_setup_from_dict

_PLAYER_STATS = (
    "accuracy",
    "power",
    "dodge",
    "catch",
    "stamina",
    "tactical_iq",
    "catch_courage",
    "throw_selection_iq",
    "conditioning_curve",
)
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
# V22 Phase 1: one wide shared pool for every generated person (names.py).
# The list() copies keep these module attributes list-typed for older callers.
from .names import FIRST_NAMES as _SHARED_FIRST_NAMES
from .names import LAST_NAMES as _SHARED_LAST_NAMES

_FIRST_NAMES = list(_SHARED_FIRST_NAMES)
_LAST_NAMES = list(_SHARED_LAST_NAMES)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _roll_rating(rng: random.Random, *, mean: float = 62.0, spread: float = 12.0) -> float:
    return _clamp(rng.gauss(mean, spread), 30, 95)


def _apply_archetype_shaping(ratings: PlayerRatings, archetype: PlayerArchetype) -> PlayerRatings:
    fields_by_base = {
        PlayerArchetype.THROWER: ("accuracy", "power"),
        PlayerArchetype.CATCHER: ("catch", "catch_courage"),
        PlayerArchetype.BALL_HAWK: ("stamina", "throw_selection_iq"),
        PlayerArchetype.DODGER_ANCHOR: ("dodge", "tactical_iq"),
    }
    primary, secondary = primary_and_secondary_bases(ratings)
    bonuses: dict[PlayerArchetype, float] = {primary: 5.0}
    if archetype not in fields_by_base:
        bonuses[secondary] = 3.0
    updates = {
        "accuracy": ratings.accuracy,
        "power": ratings.power,
        "dodge": ratings.dodge,
        "catch": ratings.catch,
        "stamina": ratings.stamina,
        "tactical_iq": ratings.tactical_iq,
        "catch_courage": ratings.catch_courage,
        "throw_selection_iq": ratings.throw_selection_iq,
        "conditioning_curve": ratings.conditioning_curve,
    }
    for base, bonus in bonuses.items():
        for field_name in fields_by_base[base]:
            updates[field_name] = updates[field_name] + bonus
    return PlayerRatings(**updates).apply_bounds()


def randomize_setup(setup: MatchSetup, variation: float = 8.0, seed: int | None = None) -> MatchSetup:
    rng = random.Random(seed)
    payload = match_setup_to_dict(setup)
    for key in ("team_a", "team_b"):
        team = payload[key]
        team["chemistry"] = _clamp(team.get("chemistry", 0.5) + rng.uniform(-0.1, 0.1), 0.0, 1.0)
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
    team_b = _random_team(rng, min_players, max_players, excluded_team_ids={team_a.id})
    return MatchSetup(team_a=team_a, team_b=team_b, config_version="phase1.v1")


def _random_team(
    rng: random.Random,
    min_players: int,
    max_players: int,
    *,
    excluded_team_ids: set[str] | None = None,
) -> Team:
    excluded = excluded_team_ids or set()
    while True:
        team_name = f"{rng.choice(_TEAM_NAMES)} {rng.choice(_SUFFIXES)}"
        team_id = team_name.lower().replace(" ", "_")
        if team_id not in excluded:
            break
    policy = CoachPolicy(
        approach=rng.choice(list(Approach)),
        target_focus=rng.choice(list(TargetFocus)),
        catch_posture=rng.choice(list(CatchPosture)),
        rush_commit=rng.choice(list(OpeningRushCommit)),
        rush_target=rng.choice(list(OpeningRushTarget)),
    )
    count = rng.randint(min_players, max_players)
    players = []
    for idx in range(count):
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        name = f"{first} {last}"

        ratings = PlayerRatings(
            accuracy=_roll_rating(rng),
            power=_roll_rating(rng),
            dodge=_roll_rating(rng),
            catch=_roll_rating(rng),
            stamina=_roll_rating(rng, mean=63.0, spread=10.0),
            tactical_iq=_roll_rating(rng),
            catch_courage=_roll_rating(rng),
            throw_selection_iq=_roll_rating(rng),
            conditioning_curve=_roll_rating(rng),
        ).apply_bounds()
        archetype = derive_archetype(ratings)
        ratings = _apply_archetype_shaping(ratings, archetype)
        archetype = derive_archetype(ratings)

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
