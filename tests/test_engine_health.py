"""Plan D engine-health regression gate.

xfail-strict on the current O1 baseline. When the rebalancing pass lands
and the assertions begin to hold, pytest will fail the suite to force the
implementer to remove the xfail marker and graduate the test to a hard gate.

Smoke size: 100 trials/rung x 4 rungs = 400 matches. Runs in ~a few seconds
on a dev machine. For tighter intervals, run the CLI:
    python tools/tier_engine_health_probe.py
"""

from __future__ import annotations

import pytest

from dodgeball_sim.rec_engine import RecTier1Driver

from tools.probe_lib import run_ovr_curve


@pytest.mark.xfail(strict=True, reason="O1 baseline - see docs/archive/playthrough-bug-log.md")
def test_ovr_curve_rec_driver_smoke():
    results = run_ovr_curve(
        RecTier1Driver(),
        rungs=(0, 4, 8, 12),
        trials_per_rung=100,
        seed_offset=0,
    )
    rates = [r.win_rate for r in results]
    # Monotonicity with 2pp tolerance for binomial noise at smoke size.
    for prev, curr in zip(rates, rates[1:]):
        assert curr >= prev - 0.02, f"OVR curve regressed: {rates}"
    # Minimum slope: the top rung must be >= 10pp above the baseline.
    assert rates[-1] - rates[0] >= 0.10, f"OVR slope too flat: {rates}"
    # Top-rung floor.
    assert rates[-1] >= 0.60, f"+72 net OVR favorite wins only {rates[-1] * 100:.1f}%"
