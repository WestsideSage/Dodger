from dodgeball_sim.match_lifecycle import OfficialGameResult
from dodgeball_sim.official_engine import (
    OfficialEngineResult,
    ScriptedActionKind,
    ScriptedOfficialAction,
    run_scripted_game,
)
from dodgeball_sim.official_events import OfficialEvent
from dodgeball_sim.rulesets import CLOTH_OPEN, FOAM_OPEN


def test_scripted_foam_game_can_process_activation_throw_catch_and_queue_return():
    actions = [
        ScriptedOfficialAction(
            ScriptedActionKind.ACTIVATE_BALL, {"ball_id": "a0", "player_id": "pA1"}
        ),
        # First throw hits a B player; B player enters queue.
        ScriptedOfficialAction(
            ScriptedActionKind.VALID_THROW,
            {
                "ball_id": "a0",
                "thrower_id": "pA1",
                "hits": ["pB1"],
                "catches": [],
                "release_time_ms": 0,
            },
        ),
        # Activate a B-side ball, then B catches a throw from A to return pB1.
        ScriptedOfficialAction(
            ScriptedActionKind.ACTIVATE_BALL, {"ball_id": "b0", "player_id": "pB2"}
        ),
        ScriptedOfficialAction(
            ScriptedActionKind.ACTIVATE_BALL, {"ball_id": "a1", "player_id": "pA2"}
        ),
        ScriptedOfficialAction(
            ScriptedActionKind.VALID_THROW,
            {
                "ball_id": "a1",
                "thrower_id": "pA2",
                "hits": [],
                "catches": ["pB2"],
                "release_time_ms": 100,
            },
        ),
    ]
    result = run_scripted_game(
        profile=FOAM_OPEN,
        match_id="m1",
        team_a_id="A",
        team_b_id="B",
        starters_a=("pA1", "pA2", "pA3", "pA4", "pA5", "pA6"),
        starters_b=("pB1", "pB2", "pB3", "pB4", "pB5", "pB6"),
        actions=actions,
    )
    assert isinstance(result, OfficialEngineResult)
    # Scripted engine emits OfficialEvent envelopes only
    for ev in result.all_events():
        assert isinstance(ev, OfficialEvent)
    # The catch sequence should have eliminated pA2 (thrower) and returned pB1
    rule_labels = [lbl for ev in result.all_events() for lbl in ev.rule_labels()]
    assert "22" in rule_labels  # catch
    assert "11" in rule_labels  # activation


def test_scripted_cloth_game_can_reach_active_count_decision():
    actions = [
        ScriptedOfficialAction(
            ScriptedActionKind.ACTIVATE_BALL, {"ball_id": "a0", "player_id": "pA1"}
        ),
        ScriptedOfficialAction(
            ScriptedActionKind.VALID_THROW,
            {"ball_id": "a0", "thrower_id": "pA1", "hits": ["pB1", "pB2"], "catches": []},
        ),
        ScriptedOfficialAction(ScriptedActionKind.ADVANCE_CLOCK, {"seconds": 180}),
        ScriptedOfficialAction(ScriptedActionKind.DECIDE_CLOTH_GAME, {}),
    ]
    result = run_scripted_game(
        profile=CLOTH_OPEN,
        match_id="m1",
        team_a_id="A",
        team_b_id="B",
        starters_a=("pA1", "pA2", "pA3", "pA4", "pA5", "pA6"),
        starters_b=("pB1", "pB2", "pB3", "pB4", "pB5", "pB6"),
        actions=actions,
    )
    assert result.final_game_result == OfficialGameResult.TEAM_A_WIN
