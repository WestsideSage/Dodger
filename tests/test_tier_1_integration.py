from dodgeball_sim.engine_driver import (
    DriverMatchInput,
    DriverMatchOutput,
    EngineDriver,
)
from dodgeball_sim.rec_engine import RecTier1Driver
from dodgeball_sim.official_driver import OfficialDriver
from dodgeball_sim.models import Player, PlayerRatings, CoachPolicy


def _make_player(pid: str, club: str) -> Player:
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(60, 50, 55, 55, 65, 50),
        club_id=club,
    )


def _make_input(seed: int = 1, config: dict | None = None) -> DriverMatchInput:
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
        config=config or {},
    )


def test_both_drivers_satisfy_protocol():
    drivers: list[EngineDriver] = [RecTier1Driver(), OfficialDriver()]
    for drv in drivers:
        assert isinstance(drv.tier_id, str)
        out = drv.run(_make_input(seed=11, config={"ruleset": "official_foam"}))
        assert isinstance(out, DriverMatchOutput)


def test_rec_driver_produces_moments_official_does_not():
    rec_out = RecTier1Driver().run(_make_input(seed=7))
    off_out = OfficialDriver().run(_make_input(seed=7, config={"ruleset": "official_foam"}))
    # Official driver doesn't emit moments in Plan A scope
    assert off_out.moment_events == ()
    # Rec driver should emit at least sometimes — verify across a few seeds
    any_moments = False
    for s in range(20):
        if RecTier1Driver().run(_make_input(seed=s)).moment_events:
            any_moments = True
            break
    assert any_moments


def test_match_outcomes_distributed_across_seeds():
    """Across 50 seeds with even rosters, both teams should win some matches in both drivers."""
    for driver_cls, cfg in [(RecTier1Driver, {}), (OfficialDriver, {"ruleset": "official_foam"})]:
        winners = {
            driver_cls().run(_make_input(seed=s, config=cfg)).winner_team_id
            for s in range(50)
        }
        assert "a" in winners
        assert "b" in winners
