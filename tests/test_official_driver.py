from dodgeball_sim.official_driver import OfficialDriver
from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import Player, PlayerRatings, CoachPolicy


def _make_player(pid: str, club: str) -> Player:
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(50, 50, 50, 50, 60, 50),
        club_id=club,
    )


def _make_input(seed: int = 1) -> DriverMatchInput:
    starters_a = tuple(f"a{i}" for i in range(6))
    starters_b = tuple(f"b{i}" for i in range(6))
    players = {pid: _make_player(pid, "a") for pid in starters_a}
    players.update({pid: _make_player(pid, "b") for pid in starters_b})
    return DriverMatchInput(
        match_id="m1",
        team_a_id="a",
        team_b_id="b",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=players,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=seed,
        config={"ruleset": "official_foam"},
    )


def test_official_driver_tier_id():
    driver = OfficialDriver()
    assert driver.tier_id == "official"


def test_official_driver_runs_match():
    driver = OfficialDriver()
    out = driver.run(_make_input(seed=7))
    assert out.winner_team_id in {"a", "b", None}
    assert isinstance(out.final_active_a, int)
    assert isinstance(out.final_active_b, int)


def test_official_driver_deterministic_for_seed():
    driver = OfficialDriver()
    out1 = driver.run(_make_input(seed=42))
    out2 = driver.run(_make_input(seed=42))
    assert out1.winner_team_id == out2.winner_team_id
    assert out1.final_active_a == out2.final_active_a
    assert out1.final_active_b == out2.final_active_b


def test_official_driver_supports_ruleset_config():
    driver = OfficialDriver()
    inp = _make_input(seed=5)
    out = driver.run(inp)
    assert out is not None
