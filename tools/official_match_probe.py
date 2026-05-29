"""Corrected official-engine balance probe (2026-05-29, throwaway diagnostic).

The shipped probe (tier_engine_health_probe.py) imports `OfficialDriver` from the
wrong module and, even when it loads, measures the SINGLE-GAME stub
(official_driver.py -> run_autonomous_game) rather than the multi-set engine that
real matches ship through (OfficialEngineAdapter.run_generic -> run_autonomous_match).

This script wraps the REAL `run_autonomous_match` as an EngineDriver and runs the
same OVR curve the rec driver uses, so the official OVR-sensitivity is measured on
the engine D4 would actually flip new careers onto. Diagnostic only; deletes-safe.

Usage:
    python tools/official_match_probe.py [--trials 500] [--ruleset official_foam]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "tools"))

from dodgeball_sim.official_engine import OfficialMatchEngineDriver  # noqa: E402

from probe_lib import run_ovr_curve, summarize_match_lengths, summarize_outcomes  # noqa: E402

RUNGS = (0, 4, 8, 12)

# Back-compat alias: the source now owns the shipping-engine driver (it also
# exposes moment_events), so the probe just re-uses it.
RealOfficialMatchDriver = OfficialMatchEngineDriver


def main() -> int:
    ap = argparse.ArgumentParser(description="Corrected official match-engine probe")
    ap.add_argument("--trials", type=int, default=500)
    ap.add_argument("--ruleset", default="official_foam")
    args = ap.parse_args()

    driver = RealOfficialMatchDriver(ruleset=args.ruleset)
    print(f"=== REAL official engine (run_autonomous_match, {args.ruleset}) ===")
    results = run_ovr_curve(driver, rungs=RUNGS, trials_per_rung=args.trials)

    print(f"=== OVR -> Favorite Win Rate ({args.trials} trials/rung) ===")
    for r in results:
        print(
            f"  Net +{r.net_ovr_edge:>2} OVR: {r.win_rate * 100:5.1f}% "
            f"[95% CI {r.ci_low * 100:5.1f} - {r.ci_high * 100:5.1f}]"
        )
    rates = [r.win_rate for r in results]
    slope_pp = (rates[-1] - rates[0]) * 100
    monotonic = all(c >= p - 0.02 for p, c in zip(rates, rates[1:]))
    print(
        f"  Monotonicity: {'PASS' if monotonic else 'FAIL'}   "
        f"Slope: {slope_pp:+.1f}pp (need +10pp -> {'PASS' if slope_pp >= 10 else 'FAIL'})   "
        f"Top floor: {rates[-1] * 100:.1f}% (need 60% -> {'PASS' if rates[-1] >= 0.60 else 'FAIL'})"
    )

    o = summarize_outcomes(results)
    print(
        f"\n=== Outcomes (all rungs) ===\n"
        f"  Favorite: {o['fav']} ({o['fav_pct']}%)   "
        f"Dog: {o['dog']} ({o['dog_pct']}%)   Draw: {o['draw']} ({o['draw_pct']}%)"
    )
    q = summarize_match_lengths(results)
    print(f"\n=== Match Length (events) ===\n  P25 {q['p25']}  P50 {q['p50']}  P75 {q['p75']}  P95 {q['p95']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
