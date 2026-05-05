from dodgeball_sim.models import CoachPolicy
from dodgeball_sim import gui, manager_gui
from dodgeball_sim.config import DEFAULT_CONFIG
from dodgeball_sim.engine import MatchEngine, compute_throw_probabilities
from dodgeball_sim.models import MatchSetup, PlayerState
from dodgeball_sim.randomizer import generate_random_setup
from dodgeball_sim.rng import DeterministicRNG
from dodgeball_sim.setup_loader import match_setup_from_dict
from dodgeball_sim.ui_formatters import policy_effect, policy_rows
from tests.factories import make_player, make_team


def _minimal_team(team_id: str) -> dict:
    return {
        "id": team_id,
        "name": team_id.title(),
        "players": [],
        "coach_policy": {
            "target_stars": 0.7,
            "risk_tolerance": 0.4,
            "sync_throws": 0.3,
            "rush_frequency": 0.2,
            "tempo": 0.6,
        },
    }


def test_coach_policy_defaults_and_serialization_include_new_tendencies():
    policy = CoachPolicy(
        target_stars=1.2,
        target_ball_holder=-0.2,
        risk_tolerance=0.4,
        sync_throws=0.3,
        rush_frequency=0.2,
        rush_proximity=1.5,
        tempo=0.6,
        catch_bias=0.75,
    )

    normalized = policy.normalized()

    assert normalized.target_ball_holder == 0.0
    assert normalized.rush_proximity == 1.0
    assert normalized.catch_bias == 0.75
    assert CoachPolicy().target_ball_holder == 0.5
    assert CoachPolicy().rush_proximity == 0.5
    assert CoachPolicy().catch_bias == 0.5
    assert policy.as_dict() == {
        "target_stars": 1.0,
        "target_ball_holder": 0.0,
        "risk_tolerance": 0.4,
        "sync_throws": 0.3,
        "rush_frequency": 0.2,
        "rush_proximity": 1.0,
        "tempo": 0.6,
        "catch_bias": 0.75,
    }


def test_setup_loader_defaults_missing_new_policy_fields_to_neutral():
    setup = match_setup_from_dict(
        {
            "team_a": _minimal_team("alpha"),
            "team_b": _minimal_team("beta"),
        }
    )

    assert setup.team_a.coach_policy.target_ball_holder == 0.5
    assert setup.team_a.coach_policy.rush_proximity == 0.5
    assert setup.team_a.coach_policy.catch_bias == 0.5


def test_randomizer_generates_new_policy_values():
    setup = generate_random_setup(seed=123)

    for team in (setup.team_a, setup.team_b):
        policy = team.coach_policy.as_dict()
        assert 0.0 <= policy["target_ball_holder"] <= 1.0
        assert 0.0 <= policy["rush_proximity"] <= 1.0
        assert 0.0 <= policy["catch_bias"] <= 1.0


def test_policy_rows_render_exact_v2d_order():
    labels = [label for label, _, _ in policy_rows(CoachPolicy())]

    assert labels == [
        "Target Stars",
        "Target Ball Holder",
        "Risk Tolerance",
        "Sync Throws",
        "Rush Frequency",
        "Rush Proximity",
        "Tempo",
        "Catch Bias",
    ]


def test_gui_policy_key_lists_match_v2d_order():
    expected = [
        "target_stars",
        "target_ball_holder",
        "risk_tolerance",
        "sync_throws",
        "rush_frequency",
        "rush_proximity",
        "tempo",
        "catch_bias",
    ]

    assert list(manager_gui.POLICY_KEYS) == expected
    assert gui._POLICY_KEYS == expected


def test_policy_effect_explains_new_tendencies():
    assert policy_effect("target_ball_holder", 0.7) == "High - prioritizes opponents controlling the ball."
    assert policy_effect("rush_proximity", 0.5) == "Balanced - adjusts how close rushes must be before pressure."
    assert policy_effect("catch_bias", 0.2) == "Very Low - changes how willingly defenders try catches."


def test_catch_bias_increases_catch_attempt_willingness_without_changing_probability_model():
    target = PlayerState(make_player("target", dodge=70, catch=50))
    engine = MatchEngine()

    low_attempt, low_meta = engine._should_attempt_catch(target, CoachPolicy(catch_bias=0.0))
    neutral_attempt, neutral_meta = engine._should_attempt_catch(target, CoachPolicy(catch_bias=0.5))
    high_attempt, high_meta = engine._should_attempt_catch(target, CoachPolicy(catch_bias=1.0))

    assert low_attempt is False
    assert neutral_attempt is False
    assert high_attempt is True
    assert low_meta["catch_bias"] == 0.0
    assert neutral_meta["catch_bias"] == 0.5
    assert high_meta["catch_bias"] == 1.0
    assert high_meta["threshold"] < neutral_meta["threshold"] < low_meta["threshold"]

    cfg = DEFAULT_CONFIG
    thrower = make_player("thrower", power=60, accuracy=70)
    calc_low = compute_throw_probabilities(thrower, target.player, cfg, 0.5, 0.5, 0.0, 0.0)
    calc_high = compute_throw_probabilities(thrower, target.player, cfg, 0.5, 0.5, 0.0, 0.0)
    assert calc_low.p_catch == calc_high.p_catch


def test_target_ball_holder_prioritizes_recent_opposing_thrower():
    recent = make_player("recent_thrower", accuracy=50, power=50, dodge=90, catch=50)
    star = make_player("star", accuracy=95, power=95, dodge=80, catch=70)
    defense = MatchEngine()._init_team_state(make_team("def", [recent, star]))
    difficulty = DEFAULT_CONFIG.difficulty_profiles["elite"]

    target, meta = MatchEngine()._select_target(
        defense,
        CoachPolicy(target_stars=0.0, target_ball_holder=1.0),
        DeterministicRNG(123),
        difficulty,
        recent_pressure_player_id="recent_thrower",
    )

    assert target.player.id == "recent_thrower"
    score = next(row for row in meta["scores"] if row["player_id"] == "recent_thrower")
    assert score["ball_holder_pressure"] > 0


def test_rush_proximity_logs_stronger_context_for_high_policy():
    defense_low = make_team("def_low", [make_player("target_low", dodge=60, catch=60)])
    defense_high = make_team("def_high", [make_player("target_high", dodge=60, catch=60)])
    offense_low = make_team(
        "off_low",
        [make_player("low_thrower", accuracy=70, power=70)],
        policy=CoachPolicy(rush_frequency=1.0, rush_proximity=0.0),
    )
    offense_high = make_team(
        "off_high",
        [make_player("high_thrower", accuracy=70, power=70)],
        policy=CoachPolicy(rush_frequency=1.0, rush_proximity=1.0),
    )

    low_event = next(e for e in MatchEngine().run(MatchSetup(offense_low, defense_low), seed=77).events if e.event_type == "throw")
    high_event = next(e for e in MatchEngine().run(MatchSetup(offense_high, defense_high), seed=77).events if e.event_type == "throw")

    assert low_event.context["rush_context"]["active"] is True
    assert high_event.context["rush_context"]["active"] is True
    assert high_event.context["rush_context"]["proximity_modifier"] > low_event.context["rush_context"]["proximity_modifier"]
    assert high_event.context["calc"]["context_terms"]["rush"] > low_event.context["calc"]["context_terms"]["rush"]


def test_rush_tuning_uses_v4_balance_constants_and_improves_sampled_hit_rate():
    assert DEFAULT_CONFIG.rush_accuracy_modifier_max == 0.15
    assert DEFAULT_CONFIG.rush_fatigue_cost_max == 0.20

    neutral_hits = 0
    rush_hits = 0
    for seed in range(1000, 1060):
        neutral_offense = make_team(
            "neutral",
            [make_player("neutral_thrower", accuracy=68, power=70)],
            policy=CoachPolicy(rush_frequency=0.0, rush_proximity=0.5),
        )
        rush_offense = make_team(
            "rush",
            [make_player("rush_thrower", accuracy=68, power=70)],
            policy=CoachPolicy(rush_frequency=1.0, rush_proximity=1.0),
        )
        neutral_defense = make_team("neutral_def", [make_player("neutral_target", dodge=68, catch=30)])
        rush_defense = make_team("rush_def", [make_player("rush_target", dodge=68, catch=30)])
        neutral_event = next(
            event
            for event in MatchEngine().run(MatchSetup(neutral_offense, neutral_defense), seed=seed).events
            if event.event_type == "throw"
        )
        rush_event = next(
            event
            for event in MatchEngine().run(MatchSetup(rush_offense, rush_defense), seed=seed).events
            if event.event_type == "throw"
        )
        neutral_hits += neutral_event.outcome["resolution"] == "hit"
        rush_hits += rush_event.outcome["resolution"] == "hit"

    assert rush_hits >= neutral_hits


def test_throw_event_logs_v2d_policy_components():
    team_a = make_team(
        "a",
        [make_player("a1", accuracy=80, power=70)],
        policy=CoachPolicy(target_ball_holder=0.7, catch_bias=0.8, rush_frequency=1.0, rush_proximity=0.9),
    )
    team_b = make_team("b", [make_player("b1", dodge=60, catch=60)])
    event = next(e for e in MatchEngine().run(MatchSetup(team_a, team_b), seed=99).events if e.event_type == "throw")

    assert "target_ball_holder" in event.context["policy_snapshot"]
    assert "catch_bias" in event.context["policy_snapshot"]
    assert "rush_proximity" in event.context["policy_snapshot"]
    assert "rush_context" in event.context
    assert "ball_holder_pressure" in event.context["target_selection"]["scores"][0]
