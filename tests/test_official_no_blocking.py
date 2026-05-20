from dodgeball_sim.no_blocking import (
    NoBlockingBallReset,
    NoBlockingSource,
    NoBlockingState,
    activate_no_blocking,
    resolve_contact_with_held_ball,
)


def test_no_blocking_activation_logs_section_27_and_source():
    state, event = activate_no_blocking(
        source=NoBlockingSource.GAME_TIME_LIMIT,
        ball_reset=NoBlockingBallReset.THREE_PER_SIDE,
        time_limit_seconds=180,
        match_id="m1",
    )
    assert state.active is True
    assert state.source == NoBlockingSource.GAME_TIME_LIMIT
    assert state.ball_reset == NoBlockingBallReset.THREE_PER_SIDE
    assert event.rule_labels() == ("27",)
    assert event.payload["source"] == "game_time_limit"


def test_held_ball_becomes_body_extension_under_no_blocking():
    state = NoBlockingState(active=True, source=NoBlockingSource.GAME_TIME_LIMIT)
    out = resolve_contact_with_held_ball(
        no_blocking=state, held_ball_player_id="p1",
        thrown_ball_alive_after_contact=True,
    )
    assert out is True


def test_held_ball_still_blocks_when_no_blocking_inactive():
    state = NoBlockingState(active=False, source=None)
    out = resolve_contact_with_held_ball(
        no_blocking=state, held_ball_player_id="p1",
        thrown_ball_alive_after_contact=True,
    )
    assert out is False
