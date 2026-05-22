from __future__ import annotations

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player, PlayerArchetype, PlayerRatings
from dodgeball_sim.rec_engine import RecTier1Driver, _response_branch_for_courage


def test_branch_function_low_courage_picks_dodge():
    assert _response_branch_for_courage(courage=10, response_roll=0.5) == "dodge"


def test_branch_function_mid_courage_picks_block():
    assert _response_branch_for_courage(courage=50, response_roll=0.5) == "block"


def test_branch_function_high_courage_picks_catch():
    assert _response_branch_for_courage(courage=90, response_roll=0.5) == "catch"


def test_branch_function_boundary_checks():
    assert _response_branch_for_courage(courage=50, response_roll=0.0) == "catch"
    assert _response_branch_for_courage(courage=50, response_roll=0.999) == "dodge"


def _player(player_id: str, courage: float) -> Player:
    return Player(
        id=player_id,
        name=player_id,
        ratings=PlayerRatings(
            accuracy=60,
            power=60,
            dodge=60,
            catch=80,
            stamina=60,
            tactical_iq=60,
            catch_courage=courage,
            throw_selection_iq=50,
            conditioning_curve=50,
        ),
        archetype=PlayerArchetype.CATCHER,
    )


def test_high_courage_run_produces_more_catches_than_low():
    high = [_player(f"hi{i}", 95) for i in range(6)]
    low = [_player(f"lo{i}", 5) for i in range(6)]
    opp = [_player(f"opp{i}", 50) for i in range(6)]

    def run(team_a_players, team_b_players, seed: int):
        lookup = {player.id: player for player in team_a_players + team_b_players}
        match_input = DriverMatchInput(
            match_id="m",
            team_a_id="a",
            team_b_id="b",
            starters_a=tuple(player.id for player in team_a_players),
            starters_b=tuple(player.id for player in team_b_players),
            player_lookup=lookup,
            policy_a=CoachPolicy(),
            policy_b=CoachPolicy(),
            seed=seed,
        )
        return RecTier1Driver().run(match_input)

    high_catches = 0
    low_catches = 0
    for seed in range(20):
        high_catches += sum(1 for event in run(high, opp, seed).events if event.get("type") == "catch_return")
        low_catches += sum(1 for event in run(low, opp, seed).events if event.get("type") == "catch_return")

    assert high_catches > low_catches
