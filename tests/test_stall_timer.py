from dodgeball_sim.stall_timer import (
    StallTimerState,
    STALL_CAP_SECONDS,
    advance_holding,
    reset_on_throw,
    should_reset_balls,
)


def test_stall_cap_constant():
    assert STALL_CAP_SECONDS == 10


def test_fresh_state_no_reset():
    state = StallTimerState.fresh()
    assert state.seconds_holding == 0.0
    assert not should_reset_balls(state)


def test_advance_below_cap_no_reset():
    state = StallTimerState.fresh()
    state = advance_holding(state, seconds=5.0, side_controls_all_balls=True)
    assert state.seconds_holding == 5.0
    assert not should_reset_balls(state)


def test_advance_past_cap_triggers_reset():
    state = StallTimerState.fresh()
    state = advance_holding(state, seconds=11.0, side_controls_all_balls=True)
    assert state.seconds_holding >= STALL_CAP_SECONDS
    assert should_reset_balls(state)


def test_advance_when_not_holding_clears_timer():
    state = StallTimerState(seconds_holding=8.0)
    state = advance_holding(state, seconds=2.0, side_controls_all_balls=False)
    assert state.seconds_holding == 0.0


def test_reset_on_throw_clears_timer():
    state = StallTimerState(seconds_holding=7.0)
    state = reset_on_throw(state)
    assert state.seconds_holding == 0.0
