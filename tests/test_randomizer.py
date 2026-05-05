from __future__ import annotations

from dodgeball_sim.randomizer import generate_random_setup, randomize_setup

from .factories import make_match_setup, make_player, make_team


def _base_setup():
    team_a = make_team("alpha", [make_player("a1", accuracy=70), make_player("a2", power=65)])
    team_b = make_team("beta", [make_player("b1", dodge=75), make_player("b2", catch=68)])
    return make_match_setup(team_a, team_b)


def test_randomize_setup_changes_values():
    base = _base_setup()
    jittered = randomize_setup(base, variation=15, seed=42)
    assert jittered.team_a.players[0].ratings.accuracy != base.team_a.players[0].ratings.accuracy
    assert jittered.team_b.players[1].ratings.catch != base.team_b.players[1].ratings.catch


def test_generate_random_setup_creates_varied_rosters():
    setup = generate_random_setup(seed=7, min_players=3, max_players=4)
    assert setup.team_a.id != setup.team_b.id
    assert 3 <= len(setup.team_a.players) <= 4
    assert 3 <= len(setup.team_b.players) <= 4
    names = {player.name for player in setup.team_a.players}
    assert len(names) == len(setup.team_a.players)
