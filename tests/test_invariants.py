from __future__ import annotations

from collections import Counter
import math
from typing import Dict, Iterable

from dodgeball_sim.config import get_config
from dodgeball_sim.engine import MatchEngine, compute_throw_probabilities
from dodgeball_sim.events import MatchEvent
from dodgeball_sim.models import CoachPolicy, MatchSetup, Player, Team

from .factories import make_match_setup, make_player, make_team


def _swap_structure(value, team_map: Dict[str, str], player_map: Dict[str, str]):
    if isinstance(value, dict):
        swapped = {}
        for key, inner in value.items():
            new_key = _swap_structure(key, team_map, player_map)
            swapped[new_key] = _swap_structure(inner, team_map, player_map)
        return swapped
    if isinstance(value, list):
        return [_swap_structure(item, team_map, player_map) for item in value]
    if isinstance(value, tuple):
        return tuple(_swap_structure(item, team_map, player_map) for item in value)
    if isinstance(value, str):
        if value in team_map:
            return team_map[value]
        if value in player_map:
            return player_map[value]
        return value
    return value


def test_accuracy_monotonicity():
    cfg = get_config()
    target = make_player("target", dodge=55, catch=55)
    low_thrower = make_player("low", accuracy=55, power=60)
    high_thrower = make_player("high", accuracy=80, power=60)

    calc_low = compute_throw_probabilities(low_thrower, target, cfg, 0.5, 0.5, 0.0, 0.0)
    calc_high = compute_throw_probabilities(high_thrower, target, cfg, 0.5, 0.5, 0.0, 0.0)

    assert calc_low.p_on_target < calc_high.p_on_target


def test_dodge_monotonicity():
    cfg = get_config()
    thrower = make_player("thrower", accuracy=70)
    weak_target = make_player("weak", dodge=45)
    strong_target = make_player("strong", dodge=80)

    calc_weak = compute_throw_probabilities(thrower, weak_target, cfg, 0.5, 0.5, 0.0, 0.0)
    calc_strong = compute_throw_probabilities(thrower, strong_target, cfg, 0.5, 0.5, 0.0, 0.0)

    assert calc_weak.p_on_target > calc_strong.p_on_target


def test_catch_monotonicity():
    cfg = get_config()
    thrower = make_player("thrower", power=55, accuracy=65)
    low_catch = make_player("low_catch", catch=40)
    high_catch = make_player("high_catch", catch=80)

    calc_low = compute_throw_probabilities(thrower, low_catch, cfg, 0.5, 0.5, 0.0, 0.0)
    calc_high = compute_throw_probabilities(thrower, high_catch, cfg, 0.5, 0.5, 0.0, 0.0)

    assert calc_low.p_catch < calc_high.p_catch


def test_power_increases_catch_difficulty():
    cfg = get_config()
    target = make_player("target", catch=70)
    weak_thrower = make_player("weak", power=45)
    strong_thrower = make_player("strong", power=85)

    calc_weak = compute_throw_probabilities(weak_thrower, target, cfg, 0.5, 0.5, 0.0, 0.0)
    calc_strong = compute_throw_probabilities(strong_thrower, target, cfg, 0.5, 0.5, 0.0, 0.0)

    assert calc_weak.p_catch > calc_strong.p_catch


def test_seeded_determinism():
    engine = MatchEngine()
    team_a = make_team("alpha", [make_player("a1"), make_player("a2", accuracy=70)])
    team_b = make_team("beta", [make_player("b1"), make_player("b2", dodge=70)])
    setup = make_match_setup(team_a, team_b)

    result_one = engine.run(setup, seed=77)
    result_two = engine.run(setup, seed=77)

    events_one = [evt.to_dict() for evt in result_one.events]
    events_two = [evt.to_dict() for evt in result_two.events]

    assert events_one == events_two
    assert result_one.box_score == result_two.box_score


def test_symmetry_swaps_outcomes():
    engine = MatchEngine()
    team_a_players = [
        make_player("alpha_1", accuracy=75, power=60, dodge=55),
        make_player("alpha_2", accuracy=60, power=65, dodge=50),
    ]
    team_b_players = [
        make_player("beta_1", accuracy=70, power=55, dodge=58),
        make_player("beta_2", accuracy=58, power=62, dodge=52),
    ]
    team_a = make_team("alpha", team_a_players, policy=CoachPolicy(target_stars=0.8))
    team_b = make_team("beta", team_b_players, policy=CoachPolicy(target_stars=0.8))
    setup = make_match_setup(team_a, team_b)
    swapped = make_match_setup(team_b, team_a)

    forward = engine.run(setup, seed=999)
    backward = engine.run(swapped, seed=999)

    team_map = {"alpha": "beta", "beta": "alpha"}
    player_map = {}
    for idx, player in enumerate(team_a_players):
        player_map[player.id] = team_b_players[idx].id
        player_map[team_b_players[idx].id] = player.id

    forward_events = [evt.to_dict() for evt in forward.events]
    backward_events = [_swap_structure(evt.to_dict(), team_map, player_map) for evt in backward.events]

    def _prune(event_dict):
        return {
            "event_type": event_dict["event_type"],
            "actors": event_dict["actors"],
            "outcome": event_dict["outcome"],
            "state_diff": event_dict["state_diff"],
        }

    assert list(map(_prune, forward_events)) == list(map(_prune, backward_events))

    swapped_box = _swap_structure(backward.box_score, team_map, player_map)

    def _box_snapshot(box):
        snapshot = {"winner": box["winner"], "teams": {}}
        for tid, data in box["teams"].items():
            snapshot["teams"][tid] = {
                "totals": data["totals"],
                "players": {
                    pid: {k: v for k, v in stats.items() if k != "name"}
                    for pid, stats in data["players"].items()
                },
            }
        return snapshot

    assert _box_snapshot(forward.box_score) == _box_snapshot(swapped_box)


def test_difficulty_without_stat_buffs():
    engine = MatchEngine()
    team_a = make_team("alpha", [make_player("a1", accuracy=70, power=65)])
    team_b = make_team("beta", [make_player("b1", dodge=60, catch=65)])
    setup = make_match_setup(team_a, team_b)

    rookie = engine.run(setup, seed=2024, difficulty="rookie")
    elite = engine.run(setup, seed=2024, difficulty="elite")

    rookie_probs = [evt.probabilities for evt in rookie.events if evt.event_type == "throw"]
    elite_probs = [evt.probabilities for evt in elite.events if evt.event_type == "throw"]

    assert rookie_probs == elite_probs
    assert rookie.box_score == elite.box_score




def test_coach_policy_targeting_is_legible():
    engine = MatchEngine()
    star_id = "beta_star"
    weak_id = "beta_weak"

    def _make_setup(target_weight: float) -> MatchSetup:
        offense = make_team(
            "alpha",
            [
                make_player("alpha_ace", accuracy=80, power=70),
                make_player("alpha_support", accuracy=62, power=58),
                make_player("alpha_rookie", accuracy=58, power=55),
            ],
            policy=CoachPolicy(target_stars=target_weight, risk_tolerance=0.45),
        )
        defense = make_team(
            "beta",
            [
                make_player(star_id, accuracy=78, dodge=80, catch=82),
                make_player("beta_balanced", accuracy=62, dodge=60, catch=60),
                make_player(weak_id, accuracy=55, dodge=40, catch=35),
            ],
            policy=CoachPolicy(target_stars=0.6),
        )
        return make_match_setup(offense, defense)

    def _target_counts(target_weight: float) -> Counter:
        counts: Counter[str] = Counter()
        for seed in range(700, 705):
            setup = _make_setup(target_weight)
            result = engine.run(setup, seed=seed, difficulty="elite")
            offense_id = setup.team_a.id
            for event in result.events:
                if event.event_type != "throw" or event.actors["offense_team"] != offense_id:
                    continue
                counts[event.actors["target"]] += 1
                snapshot = event.context.get("policy_snapshot", {})
                assert math.isclose(snapshot["target_stars"], target_weight, abs_tol=1e-6)
        return counts

    high_counts = _target_counts(0.9)
    low_counts = _target_counts(0.1)

    assert high_counts[star_id] > low_counts[star_id]
    assert low_counts[weak_id] > high_counts[weak_id]
