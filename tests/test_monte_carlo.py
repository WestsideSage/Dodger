from __future__ import annotations

from dodgeball_sim.config import get_config
from dodgeball_sim.engine import compute_throw_probabilities
from dodgeball_sim.rng import DeterministicRNG

from .factories import make_player


def _trial_counts(thrower, target, trials: int, seed: int):
    cfg = get_config()
    rng = DeterministicRNG(seed)
    hits = catches = dodges = 0
    for _ in range(trials):
        calc = compute_throw_probabilities(thrower, target, cfg, 0.5, 0.5, 0.0, 0.0)
        if rng.unit() <= calc.p_on_target:
            if rng.unit() <= calc.p_catch:
                catches += 1
            else:
                hits += 1
        else:
            dodges += 1
    return {"hits": hits, "catches": catches, "dodges": dodges}


def test_accuracy_increases_hit_rate():
    low_accuracy = make_player("low", accuracy=55, power=60)
    high_accuracy = make_player("high", accuracy=80, power=60)
    target = make_player("target", dodge=55, catch=50)

    low_stats = _trial_counts(low_accuracy, target, trials=4000, seed=1)
    high_stats = _trial_counts(high_accuracy, target, trials=4000, seed=1)

    assert high_stats["hits"] > low_stats["hits"]


def test_dodge_reduces_hits():
    thrower = make_player("thrower", accuracy=70, power=60)
    low_dodge = make_player("low_dodge", dodge=40)
    high_dodge = make_player("high_dodge", dodge=80)

    low_stats = _trial_counts(thrower, low_dodge, trials=4000, seed=2)
    high_stats = _trial_counts(thrower, high_dodge, trials=4000, seed=2)

    assert high_stats["dodges"] > low_stats["dodges"]


def test_catch_rating_increases_catches():
    thrower = make_player("thrower", accuracy=70, power=55)
    low_catch = make_player("low_catch", catch=40)
    high_catch = make_player("high_catch", catch=85)

    low_stats = _trial_counts(thrower, low_catch, trials=4000, seed=3)
    high_stats = _trial_counts(thrower, high_catch, trials=4000, seed=3)

    assert high_stats["catches"] > low_stats["catches"]


def test_power_makes_catches_harder():
    low_power = make_player("low_power", power=45, accuracy=70)
    high_power = make_player("high_power", power=85, accuracy=70)
    target = make_player("target", catch=70)

    low_stats = _trial_counts(low_power, target, trials=4000, seed=4)
    high_stats = _trial_counts(high_power, target, trials=4000, seed=4)

    assert high_stats["catches"] < low_stats["catches"]
