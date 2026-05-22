from __future__ import annotations

from dodgeball_sim.rec_engine import _should_throw_under_iq


def test_low_iq_throws_freely_when_value_low():
    assert _should_throw_under_iq(
        iq=10,
        expected_value=0.1,
        stall_seconds=0.0,
        stall_cap=10.0,
    ) is True


def test_high_iq_skips_low_value_throw_when_clock_is_fresh():
    assert _should_throw_under_iq(
        iq=90,
        expected_value=0.1,
        stall_seconds=0.0,
        stall_cap=10.0,
    ) is False


def test_high_iq_throws_when_value_is_high():
    assert _should_throw_under_iq(
        iq=90,
        expected_value=0.9,
        stall_seconds=0.0,
        stall_cap=10.0,
    ) is True


def test_high_iq_throws_under_late_stall_pressure():
    assert _should_throw_under_iq(
        iq=90,
        expected_value=0.1,
        stall_seconds=8.5,
        stall_cap=10.0,
    ) is True


def test_mid_iq_at_mid_value_throws():
    assert _should_throw_under_iq(
        iq=50,
        expected_value=0.5,
        stall_seconds=0.0,
        stall_cap=10.0,
    ) is True
