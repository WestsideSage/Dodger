"""Phase 4a — official-engine balance + moment-coverage gate.

The shipping official match engine (``run_autonomous_match``, the path real
official careers play through) previously did NOT reward OVR: the favorite at a
+72 net edge won only ~44% with ~22% draws, because a catch (which outs the
thrower AND resurrects a defender) was the default outcome of an on-target
throw, so throwing was net-negative EV and games stalled to clock-expiry draws.
Phase 4a retuned the catch math in ``official_resolution`` so OVR expresses, and
taught the engine to emit recognition moments. This is the graduated gate that
both balance and moment coverage must keep passing before the foam-official
default flips for new careers (Phase 4b).

Smoke size kept modest so the suite stays fast; for tighter intervals run
``python tools/official_match_probe.py --trials 500``.
"""
from __future__ import annotations

from collections import Counter

from dodgeball_sim.official_engine import OfficialMatchEngineDriver
from tools.probe_lib import make_match_input, run_ovr_curve


def test_official_ovr_curve_gate():
    results = run_ovr_curve(
        OfficialMatchEngineDriver(),
        rungs=(0, 4, 8, 12),
        trials_per_rung=250,
        seed_offset=0,
    )
    rates = [r.win_rate for r in results]
    # Monotonic within binomial noise at smoke size.
    for prev, curr in zip(rates, rates[1:]):
        assert curr >= prev - 0.04, f"official OVR curve regressed: {rates}"
    # Slope: the +72 net-OVR favorite must win >= 10pp above the even baseline.
    assert rates[-1] - rates[0] >= 0.10, f"official OVR slope too flat: {rates}"
    # Top-rung floor: a clearly stronger six must be a real favorite (gate 60%;
    # 0.56 lower bound leaves room for binomial noise at 250 trials).
    assert rates[-1] >= 0.56, f"+72 net OVR favorite wins only {rates[-1] * 100:.1f}%"
    # Draws must not swamp the signal at a large edge (coupled to the slope —
    # the old failure was catch-resurrection -> no elimination -> 0-0 draws).
    top = results[-1]
    draw_rate = sum(1 for o in top.outputs if o.winner_team_id is None) / len(top.outputs)
    assert draw_rate <= 0.25, f"+72 draw rate too high: {draw_rate * 100:.1f}%"


def test_official_driver_emits_recognition_moments():
    """The shipping official driver must emit the moment kinds the rec driver
    surfaces and the official loop can detect: DRAMATIC_CATCH, LATE_GAME_ESCAPE,
    ONE_V_ONE_FINALE, COMEBACK. GASSED_COLLAPSE and FLOOD_THROW are intentionally
    deferred (the official loop models no fatigue and no batch-throw tracker)."""
    driver = OfficialMatchEngineDriver()
    kinds: Counter[str] = Counter()
    for trial in range(150):
        mi = make_match_input(seed=trial, rating_a=70.0, rating_b=63.0)
        out = driver.run(mi)
        for moment in out.moment_events:
            kinds[moment.kind.value] += 1

    for required in ("dramatic_catch", "late_game_escape", "one_v_one_finale", "comeback"):
        assert kinds[required] > 0, f"official engine never emitted {required}: {dict(kinds)}"
