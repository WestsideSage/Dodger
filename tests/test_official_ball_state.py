import pytest

from dodgeball_sim.ball_state import (
    BallState,
    activate_ball,
    entering_player_touches_ball_before_live,
    initial_balls,
    queue_player_holds_ball_forfeit,
    retrieved_ball_counts_for_burden,
    throw_inactive_ball_marks_thrower_out,
)
from dodgeball_sim.rulesets import CLOTH_OPEN, FOAM_OPEN, NO_STING_OPEN


def test_foam_starts_with_three_balls_per_side():
    balls = initial_balls(FOAM_OPEN, "A", "B")
    assert len(balls) == 6
    assert sum(1 for b in balls if b.side == "A") == 3
    assert sum(1 for b in balls if b.side == "B") == 3
    assert all(b.state == BallState.INACTIVE_CENTER for b in balls)


def test_no_sting_starts_with_three_balls_per_side():
    balls = initial_balls(NO_STING_OPEN, "A", "B")
    assert len(balls) == 6


def test_cloth_starts_with_two_per_side_and_one_neutral():
    balls = initial_balls(CLOTH_OPEN, "A", "B")
    assert len(balls) == 5
    assert sum(1 for b in balls if b.side == "A") == 2
    assert sum(1 for b in balls if b.side == "B") == 2
    assert sum(1 for b in balls if b.side is None) == 1


def test_activate_ball_marks_held_and_emits_rule_11_event():
    ball = initial_balls(FOAM_OPEN, "A", "B")[0]
    event = activate_ball(ball, player_id="p1", match_id="m1")
    assert ball.activated is True
    assert ball.state == BallState.HELD
    assert ball.controller_player_id == "p1"
    assert event.rule_labels() == ("11",)


def test_throw_inactive_ball_outs_thrower_and_keeps_ball_inactive():
    ball = initial_balls(FOAM_OPEN, "A", "B")[0]
    assert not ball.activated
    event = throw_inactive_ball_marks_thrower_out(ball, thrower_id="p1", match_id="m1")
    assert ball.activated is False
    assert event.payload["thrower_out"] is True
    assert "11" in event.rule_labels() and "17" in event.rule_labels()


def test_throw_inactive_rejects_if_ball_active():
    ball = initial_balls(FOAM_OPEN, "A", "B")[0]
    activate_ball(ball, player_id="p1", match_id="m1")
    with pytest.raises(ValueError):
        throw_inactive_ball_marks_thrower_out(ball, thrower_id="p2", match_id="m1")


def test_retrieved_ball_counts_for_burden():
    ball = initial_balls(FOAM_OPEN, "A", "B")[0]
    ball.state = BallState.RETRIEVED
    assert retrieved_ball_counts_for_burden(ball)
    ball.state = BallState.HELD
    assert retrieved_ball_counts_for_burden(ball)
    ball.state = BallState.DEAD
    assert not retrieved_ball_counts_for_burden(ball)


def test_queued_player_holding_ball_forfeits_to_opponent():
    ball = initial_balls(FOAM_OPEN, "A", "B")[0]
    event = queue_player_holds_ball_forfeit(
        ball, queued_player_id="q1", match_id="m1", opponent_team_id="B"
    )
    assert ball.state == BallState.FORFEITED
    assert ball.side == "B"
    assert event.rule_labels() == ("24",)


def test_entering_player_touching_ball_pre_live_emits_forfeit_and_out():
    ball = initial_balls(FOAM_OPEN, "A", "B")[0]
    forfeit_event, out_event = entering_player_touches_ball_before_live(
        ball, entering_player_id="e1", match_id="m1", opponent_team_id="B"
    )
    assert ball.state == BallState.FORFEITED
    assert ball.side == "B"
    assert "24" in forfeit_event.rule_labels()
    assert out_event.payload["kind"] == "entering_illegal_contact_out"
