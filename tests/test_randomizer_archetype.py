from __future__ import annotations

import random
from collections import Counter

from dodgeball_sim.models import PlayerArchetype
from dodgeball_sim.randomizer import _random_team


def _generate_many(seed: int, team_count: int = 40) -> list:
    rng = random.Random(seed)
    players = []
    for _ in range(team_count):
        team = _random_team(rng, min_players=5, max_players=5)
        players.extend(team.players)
    return players


def test_random_players_have_v2_archetype():
    for player in _generate_many(seed=42):
        assert isinstance(player.archetype, PlayerArchetype)


def test_random_players_have_v2_ratings():
    for player in _generate_many(seed=42):
        assert 0 <= player.ratings.catch_courage <= 100
        assert 0 <= player.ratings.throw_selection_iq <= 100
        assert 0 <= player.ratings.conditioning_curve <= 100


def test_randomizer_archetype_distribution_is_diverse():
    players = _generate_many(seed=7, team_count=40)
    assert len(players) >= 150
    archetypes = {player.archetype for player in players}
    assert len(archetypes) >= 4
    counts = Counter(player.archetype for player in players)
    assert counts.most_common(1)[0][1] / len(players) < 0.75
