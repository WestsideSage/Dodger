from __future__ import annotations

import pytest

from dodgeball_sim import command_center
from dodgeball_sim.command_center import policy_effect, policy_rows
from dodgeball_sim.config import DEFAULT_CONFIG
from dodgeball_sim.engine import MatchEngine, compute_throw_probabilities
from dodgeball_sim.models import CoachPolicy, MatchSetup, PlayerState
from dodgeball_sim.randomizer import generate_random_setup
from dodgeball_sim.rng import DeterministicRNG
from dodgeball_sim.setup_loader import match_setup_from_dict
from tests.factories import make_player, make_team


def _minimal_team(team_id: str) -> dict:
    return {
        "id": team_id,
        "name": team_id.title(),
        "players": [],
        "coach_policy": {
            "approach": "patient",
            "target_focus": "spread",
            "catch_posture": "opportunistic",
            "rush_commit": "balanced",
            "rush_target": "nearest",
        },
    }


def test_setup_loader_accepts_v2_policy_payload():
    setup = match_setup_from_dict(
        {
            "team_a": _minimal_team("alpha"),
            "team_b": _minimal_team("beta"),
        }
    )

    assert setup.team_a.coach_policy.as_dict() == {
        "approach": "patient",
        "target_focus": "spread",
        "catch_posture": "opportunistic",
        "rush_commit": "balanced",
        "rush_target": "nearest",
    }


def test_randomizer_generates_v2_policy_values():
    setup = generate_random_setup(seed=123)
    allowed = {
        "approach": {"aggressive", "mixed", "patient"},
        "target_focus": {"their_stars", "ball_holders", "spread"},
        "catch_posture": {"go_for_catches", "play_safe", "opportunistic"},
        "rush_commit": {"all_in", "balanced", "hold_back"},
        "rush_target": {"nearest", "strongest_side", "center"},
    }

    for team in (setup.team_a, setup.team_b):
        policy = team.coach_policy.as_dict()
        for key, values in allowed.items():
            assert policy[key] in values


def test_policy_rows_render_exact_plan_c_order():
    rows = list(policy_rows(CoachPolicy()))

    assert [row["label"] for row in rows] == [
        "Approach",
        "Target focus",
        "Catch posture",
        "Opening rush: commit",
        "Opening rush: target",
    ]
    assert rows[0]["options"][2]["selected"] is True


def test_gui_policy_key_lists_match_plan_c_order():
    assert list(command_center.POLICY_KEYS) == [
        "approach",
        "target_focus",
        "catch_posture",
        "rush_commit",
        "rush_target",
    ]


def test_policy_effect_explains_selected_tendencies():
    aggressive = CoachPolicy(approach="aggressive")
    safe = CoachPolicy(catch_posture="play_safe")

    assert "throws first" in policy_effect(aggressive, "approach").lower()
    assert "survival first" in policy_effect(safe, "catch_posture").lower()


def test_catch_posture_changes_attempt_threshold_without_changing_probability_model():
    target = PlayerState(make_player("target", dodge=70, catch=50))
    engine = MatchEngine()

    catches_attempt, catches_meta = engine._should_attempt_catch(
        target,
        CoachPolicy(catch_posture="go_for_catches"),
    )
    neutral_attempt, neutral_meta = engine._should_attempt_catch(
        target,
        CoachPolicy(catch_posture="opportunistic"),
    )
    safe_attempt, safe_meta = engine._should_attempt_catch(
        target,
        CoachPolicy(catch_posture="play_safe"),
    )

    assert catches_attempt is True
    assert neutral_attempt is False
    assert safe_attempt is False
    assert catches_meta["threshold"] < neutral_meta["threshold"] < safe_meta["threshold"]

    cfg = DEFAULT_CONFIG
    thrower = make_player("thrower", power=60, accuracy=70)
    calc_a = compute_throw_probabilities(thrower, target.player, cfg, 0.5, 0.5, 0.0, 0.0)
    calc_b = compute_throw_probabilities(thrower, target.player, cfg, 0.5, 0.5, 0.0, 0.0)
    assert calc_a.p_catch == calc_b.p_catch


def test_ball_holders_focus_prioritizes_recent_opposing_thrower():
    recent = make_player("recent_thrower", accuracy=50, power=50, dodge=90, catch=50)
    star = make_player("star", accuracy=95, power=95, dodge=80, catch=70)
    defense = MatchEngine()._init_team_state(make_team("def", [recent, star]))
    difficulty = DEFAULT_CONFIG.difficulty_profiles["elite"]

    target, meta = MatchEngine()._select_target(
        defense,
        CoachPolicy(target_focus="ball_holders"),
        DeterministicRNG(123),
        difficulty,
        recent_pressure_player_id="recent_thrower",
    )

    assert target.player.id == "recent_thrower"
    score = next(row for row in meta["scores"] if row["player_id"] == "recent_thrower")
    assert score["ball_holder_pressure"] > 0


def test_strongest_side_rush_logs_higher_pressure_than_nearest():
    defense_nearest = make_team("def_low", [make_player("target_low", dodge=60, catch=60)])
    defense_strong = make_team("def_high", [make_player("target_high", dodge=60, catch=60)])
    offense_nearest = make_team(
        "off_low",
        [make_player("low_thrower", accuracy=70, power=70)],
        policy=CoachPolicy(rush_commit="all_in", rush_target="nearest"),
    )
    offense_strong = make_team(
        "off_high",
        [make_player("high_thrower", accuracy=70, power=70)],
        policy=CoachPolicy(rush_commit="all_in", rush_target="strongest_side"),
    )

    nearest_event = next(
        e
        for e in MatchEngine().run(MatchSetup(offense_nearest, defense_nearest), seed=77).events
        if e.event_type == "throw"
    )
    strong_event = next(
        e
        for e in MatchEngine().run(MatchSetup(offense_strong, defense_strong), seed=77).events
        if e.event_type == "throw"
    )

    assert nearest_event.context["rush_context"]["active"] is True
    assert strong_event.context["rush_context"]["active"] is True
    assert (
        strong_event.context["rush_context"]["proximity_modifier"]
        > nearest_event.context["rush_context"]["proximity_modifier"]
    )
    assert strong_event.context["calc"]["context_terms"]["rush"] > nearest_event.context["calc"]["context_terms"]["rush"]


def test_throw_event_logs_plan_c_policy_components():
    team_a = make_team(
        "a",
        [make_player("a1", accuracy=80, power=70)],
        policy=CoachPolicy(
            target_focus="ball_holders",
            catch_posture="go_for_catches",
            rush_commit="all_in",
            rush_target="strongest_side",
        ),
    )
    team_b = make_team("b", [make_player("b1", dodge=60, catch=60)])
    event = next(
        e
        for e in MatchEngine().run(MatchSetup(team_a, team_b), seed=99).events
        if e.event_type == "throw"
    )

    assert set(event.context["policy_snapshot"]) == {
        "approach",
        "target_focus",
        "catch_posture",
        "rush_commit",
        "rush_target",
    }
    assert event.context["rush_context"]["rush_commit"] == "all_in"
    assert event.context["rush_context"]["rush_target"] == "strongest_side"
    assert "ball_holder_pressure" in event.context["target_selection"]["scores"][0]


def test_setup_loader_rejects_legacy_policy_payloads():
    with pytest.raises(ValueError, match="Legacy CoachPolicy payload"):
        match_setup_from_dict(
            {
                "team_a": {
                    "id": "alpha",
                    "name": "Alpha",
                    "players": [],
                    "coach_policy": {"target_stars": 0.7, "tempo": 0.5},
                },
                "team_b": _minimal_team("beta"),
            }
        )
