from __future__ import annotations

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player

from tools.probe_lib import make_match_input, make_player, make_team


def test_make_player_builds_player_with_uniform_rating():
    player = make_player("fav_0", "fav", rating=70.0)
    assert isinstance(player, Player)
    assert player.id == "fav_0"
    assert player.club_id == "fav"
    assert player.ratings.accuracy == 70.0
    assert player.ratings.dodge == 70.0
    assert player.ratings.stamina == 70.0


def test_make_team_returns_six_starter_ids_by_default():
    starters = make_team("fav", rating=65.0)
    assert len(starters) == 6
    assert starters[0] == "fav_0"
    assert starters[-1] == "fav_5"


def test_make_match_input_produces_valid_driver_input():
    mi = make_match_input(seed=42, rating_a=70.0, rating_b=60.0)
    assert isinstance(mi, DriverMatchInput)
    assert mi.team_a_id == "fav"
    assert mi.team_b_id == "dog"
    assert mi.match_id == "probe_42"
    assert mi.seed == 42
    assert len(mi.starters_a) == 6
    assert len(mi.starters_b) == 6
    assert set(mi.player_lookup.keys()) == set(mi.starters_a) | set(mi.starters_b)
    assert mi.player_lookup["fav_0"].ratings.accuracy == 70.0
    assert mi.player_lookup["dog_0"].ratings.accuracy == 60.0
    assert isinstance(mi.policy_a, CoachPolicy)
    assert isinstance(mi.policy_b, CoachPolicy)


def test_make_match_input_honors_custom_prefix_and_policies():
    custom = CoachPolicy()
    mi = make_match_input(
        seed=7,
        rating_a=63.0,
        rating_b=63.0,
        policy_a=custom,
        policy_b=custom,
        match_id_prefix="health",
    )
    assert mi.match_id == "health_7"
    assert mi.policy_a is custom
    assert mi.policy_b is custom


from tools.probe_lib import RungResult, wilson_ci


def test_wilson_ci_known_values():
    # 50 successes in 100 trials: Wilson 95% CI ≈ (0.404, 0.596).
    low, high = wilson_ci(50, 100)
    assert abs(low - 0.4038) < 1e-3
    assert abs(high - 0.5962) < 1e-3


def test_wilson_ci_handles_zero_trials():
    low, high = wilson_ci(0, 0)
    assert low == 0.0
    assert high == 0.0


def test_wilson_ci_handles_perfect_score():
    low, high = wilson_ci(100, 100)
    assert low > 0.9
    assert high >= 0.9999


def test_rung_result_carries_required_fields():
    rr = RungResult(
        net_ovr_edge=24,
        trials=100,
        fav_wins=55,
        win_rate=0.55,
        ci_low=0.45,
        ci_high=0.65,
        outputs=(),
    )
    assert rr.net_ovr_edge == 24
    assert rr.fav_wins == 55


from dodgeball_sim.rec_engine import RecTier1Driver

from tools.probe_lib import run_ovr_curve


def test_run_ovr_curve_returns_one_result_per_rung():
    results = run_ovr_curve(RecTier1Driver(), rungs=(0, 4), trials_per_rung=2)
    assert len(results) == 2
    assert results[0].net_ovr_edge == 0
    assert results[1].net_ovr_edge == 24
    assert results[0].trials == 2
    assert all(0.0 <= r.win_rate <= 1.0 for r in results)


def test_run_ovr_curve_seeds_are_deterministic():
    a = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3)
    b = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3)
    assert a[0].fav_wins == b[0].fav_wins


def test_run_ovr_curve_seed_offset_shifts_results():
    a = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3, seed_offset=0)
    b = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3, seed_offset=500)
    # Different seeds: at least one of the underlying outputs differs.
    a_winners = tuple(out.winner_team_id for out in a[0].outputs)
    b_winners = tuple(out.winner_team_id for out in b[0].outputs)
    assert a_winners != b_winners or a[0].fav_wins != b[0].fav_wins
