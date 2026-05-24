"""Plan D engine-health regression gate.

Smoke size: 400 trials/rung x 4 rungs = 1600 matches. Runs in ~a few seconds
on a dev machine. For tighter intervals, run the CLI:
    python tools/tier_engine_health_probe.py
"""

from __future__ import annotations

import pytest

from dodgeball_sim.rec_engine import RecTier1Driver

from tools.probe_lib import run_ovr_curve


def test_ovr_curve_rec_driver_smoke():
    results = run_ovr_curve(
        RecTier1Driver(),
        rungs=(0, 4, 8, 12),
        trials_per_rung=400,
        seed_offset=0,
    )
    rates = [r.win_rate for r in results]
    # Monotonicity with 2pp tolerance for binomial noise at smoke size.
    for prev, curr in zip(rates, rates[1:]):
        assert curr >= prev - 0.02, f"OVR curve regressed: {rates}"
    # Minimum slope: the top rung must be >= 10pp above the baseline.
    assert rates[-1] - rates[0] >= 0.10, f"OVR slope too flat: {rates}"
    # Top-rung floor (calibrated band lower bound, allowing for binomial noise at smoke size).
    assert rates[-1] >= 0.66, f"+72 net OVR favorite wins only {rates[-1] * 100:.1f}%"


def test_fav_losses_explained_by_moments():
    results = run_ovr_curve(
        RecTier1Driver(),
        rungs=(12,),
        trials_per_rung=400,
        seed_offset=0,
    )
    losses = [out for out in results[0].outputs if out.winner_team_id == "dog"]
    if not losses:
        return
    moment_loss_count = 0
    for out in losses:
        kinds = {e.kind.value if hasattr(e.kind, "value") else str(e.kind) for e in out.moment_events}
        explained = any(
            k in kinds
            for k in (
                "comeback",
                "dramatic_catch",
                "gassed_collapse",
                "late_game_escape",
                "one_v_one_finale",
            )
        )
        if explained:
            moment_loss_count += 1
    pct = moment_loss_count / len(losses)
    assert pct >= 0.75, f"Favorite losses not sufficiently explained by moments: {pct * 100:.1f}%"
