import math

from dodgeball_sim.fatigue import (
    FatigueState,
    FatigueParams,
    GASSED_THRESHOLD,
    accumulate,
    recover,
    effectiveness,
)


def test_fresh_player_has_zero_fatigue():
    state = FatigueState.fresh()
    assert state.value == 0.0
    assert not state.is_gassed()


def test_accumulate_increases_fatigue():
    params = FatigueParams()
    state = FatigueState.fresh()
    state = accumulate(state, action_cost=0.05, params=params)
    assert state.value > 0.0
    assert state.value <= 1.0


def test_accumulate_caps_at_one():
    params = FatigueParams()
    state = FatigueState(value=0.95)
    state = accumulate(state, action_cost=0.5, params=params)
    assert state.value == 1.0


def test_recover_decreases_fatigue():
    params = FatigueParams()
    state = FatigueState(value=0.5)
    state = recover(state, seconds_idle=10, params=params)
    assert state.value < 0.5
    assert state.value >= 0.0


def test_recover_floors_at_zero():
    params = FatigueParams()
    state = FatigueState(value=0.02)
    state = recover(state, seconds_idle=600, params=params)
    assert state.value == 0.0


def test_gassed_threshold_constant():
    assert GASSED_THRESHOLD == 0.75


def test_is_gassed_at_or_above_threshold():
    assert FatigueState(value=GASSED_THRESHOLD).is_gassed()
    assert FatigueState(value=0.9).is_gassed()
    assert not FatigueState(value=0.74).is_gassed()


def test_effectiveness_drops_with_fatigue():
    fresh_eff = effectiveness(FatigueState(value=0.0))
    gassed_eff = effectiveness(FatigueState(value=0.9))
    assert fresh_eff == 1.0
    assert gassed_eff < 0.6
    assert gassed_eff > 0.0


def test_effectiveness_monotonic_decrease():
    """Effectiveness must not increase as fatigue grows."""
    last = math.inf
    for v in [0.0, 0.25, 0.5, 0.75, 0.9, 1.0]:
        eff = effectiveness(FatigueState(value=v))
        assert eff <= last + 1e-9, f"effectiveness rose at fatigue={v}"
        last = eff


def test_conditioning_curve_slows_accumulation():
    """Higher conditioning_curve attribute should slow fatigue gain."""
    soft_params = FatigueParams(conditioning_curve=20.0)  # poor conditioning
    hard_params = FatigueParams(conditioning_curve=90.0)  # elite conditioning
    soft_state = accumulate(FatigueState.fresh(), action_cost=0.1, params=soft_params)
    hard_state = accumulate(FatigueState.fresh(), action_cost=0.1, params=hard_params)
    assert soft_state.value > hard_state.value
