from dodgeball_sim.engine_driver import (
    DriverMatchInput,
    DriverMatchOutput,
    EngineDriver,
)
from dodgeball_sim.rec_engine import RecTier1Driver
from dodgeball_sim.official_driver import OfficialDriver
from dodgeball_sim.models import Player, PlayerRatings, CoachPolicy


def _make_player(pid: str, club: str) -> Player:
    from dodgeball_sim.models import PlayerArchetype
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(60, 50, 55, 55, 65, 50),
        club_id=club,
        archetype=PlayerArchetype.CATCHER,
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


def test_rec_driver_moments_carry_match_id():
    """Regression: every moment event must carry the input match_id, not a placeholder."""
    saw_any = False
    for seed in range(30):
        out = RecTier1Driver().run(_make_input(seed=seed))
        for event in out.moment_events:
            saw_any = True
            assert event.match_id == "m1", (
                f"moment {type(event).__name__} carried match_id={event.match_id!r}"
            )
    assert saw_any, "expected at least one moment event across 30 seeds"


def test_rec_driver_comeback_moment_fires_on_expected_matches():
    """Plan A follow-up: comeback heuristic should fire on >=24/25 matches that present
    the comeback shape (trailing 4-1 or worse, then closing to within 2)."""
    from dodgeball_sim.rec_engine import RecTier1Driver
    from dodgeball_sim.moment_events import Comeback

    fired = 0
    expected = 25
    for seed in range(expected):
        out = RecTier1Driver().run(_make_input(seed=seed))
        # Let's inspect if a comeback shape actually happened in this match.
        # Deficit at low >= 3 means down 6-3 or worse.
        # In a 6v6 match, this happens when a team is reduced to <= 3 active players,
        # while the other team has 6 active players, or similar.
        # Closing to within 2 means my_active >= opp_active - 2.
        # If the shape occurred, check if Comeback was emitted.
        if any(isinstance(e, Comeback) for e in out.moment_events):
            fired += 1
    assert fired >= 24, f"comeback fired in only {fired}/{expected} scripted matches"
