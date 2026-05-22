import random

from dodgeball_sim.rec_engine import RecTier1Driver
from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import Player, PlayerRatings, CoachPolicy


def _make_player(pid: str, club: str) -> Player:
    from dodgeball_sim.models import PlayerArchetype
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(
            accuracy=50, power=50, dodge=50, catch=50, stamina=60, tactical_iq=50
        ),
        club_id=club,
        archetype=PlayerArchetype.CATCHER,
    )


def _make_input(seed: int = 42) -> DriverMatchInput:
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
    )


def test_driver_tier_id_is_local_rec_league():
    driver = RecTier1Driver()
    assert driver.tier_id == "local_rec_league"


def test_match_resolves_with_winner_or_draw():
    driver = RecTier1Driver()
    out = driver.run(_make_input(seed=1))
    assert out.winner_team_id in {"a", "b", None}


def test_match_emits_at_least_one_event():
    driver = RecTier1Driver()
    out = driver.run(_make_input(seed=2))
    assert len(out.events) > 0


def test_match_returns_final_active_counts():
    driver = RecTier1Driver()
    out = driver.run(_make_input(seed=3))
    assert out.final_active_a >= 0
    assert out.final_active_b >= 0
    assert out.final_active_a + out.final_active_b > 0  # match shouldn't kill everyone


def test_match_is_deterministic_for_seed():
    driver = RecTier1Driver()
    out1 = driver.run(_make_input(seed=99))
    out2 = driver.run(_make_input(seed=99))
    assert out1.winner_team_id == out2.winner_team_id
    assert out1.final_active_a == out2.final_active_a
    assert out1.final_active_b == out2.final_active_b


def test_different_seeds_produce_different_outcomes_over_many_runs():
    driver = RecTier1Driver()
    winners = {driver.run(_make_input(seed=s)).winner_team_id for s in range(50)}
    # over 50 seeds, both sides should win at least once given equal rosters
    assert "a" in winners
    assert "b" in winners


def test_time_cap_prevents_infinite_matches():
    driver = RecTier1Driver()
    # Run many seeds; none should fail to terminate
    for seed in range(20):
        out = driver.run(_make_input(seed=seed))
        assert out is not None


from dodgeball_sim.moment_events import (
    Comeback,
    DramaticCatch,
    FloodThrow,
    GassedCollapse,
    LateGameEscape,
    OneVOneFinale,
    MomentKind,
)


def _moment_kinds_across_seeds(seeds=range(80)) -> set[MomentKind]:
    driver = RecTier1Driver()
    seen: set[MomentKind] = set()
    for s in seeds:
        out = driver.run(_make_input(seed=s))
        for ev in out.moment_events:
            seen.add(ev.kind)
    return seen


def test_emits_at_least_some_moments_across_runs():
    driver = RecTier1Driver()
    any_emitted = False
    for s in range(20):
        out = driver.run(_make_input(seed=s))
        if out.moment_events:
            any_emitted = True
            break
    assert any_emitted, "no moments emitted across 20 seeds — emission is broken"


def test_dramatic_catch_emits_when_catch_returns_player():
    """Run many seeds; at least one match should produce a dramatic catch."""
    seen = _moment_kinds_across_seeds()
    assert MomentKind.DRAMATIC_CATCH in seen


def test_flood_throw_or_late_escape_emerges_across_seeds():
    """Either flood throws or late-game escapes should appear across enough seeds."""
    seen = _moment_kinds_across_seeds()
    assert seen & {MomentKind.FLOOD_THROW, MomentKind.LATE_GAME_ESCAPE}


def test_one_v_one_finale_emerges_across_seeds():
    seen = _moment_kinds_across_seeds()
    assert MomentKind.ONE_V_ONE_FINALE in seen
