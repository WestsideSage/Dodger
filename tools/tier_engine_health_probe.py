"""Tier engine health probe — Plan D regression diagnostic.

Reports the OVR -> favorite-win-rate curve plus moment-occurrence rates,
match-length distribution, and outcome distribution. The OVR curve is the
primary regression signal; the other three are diagnostic.

Replaces tools/o1_variance_probe.py (deleted by Plan D).

Usage:
    python tools/tier_engine_health_probe.py [--trials 400] [--driver rec|official|both] [--seed-offset 0]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "tools"))

from dodgeball_sim.engine_driver import EngineDriver  # noqa: E402

from probe_lib import (  # noqa: E402
    RungResult,
    run_ovr_curve,
    summarize_match_lengths,
    summarize_moments,
    summarize_outcomes,
)

RUNGS: tuple[int, ...] = (0, 4, 8, 12)


def _build_driver(name: str) -> EngineDriver:
    if name == "rec":
        from dodgeball_sim.rec_engine import RecTier1Driver
        return RecTier1Driver()
    if name == "official":
        try:
            from dodgeball_sim.official_engine import OfficialDriver
        except ImportError as e:
            raise RuntimeError(f"OfficialDriver not yet implemented") from e
        return OfficialDriver()
    raise ValueError(f"Unknown driver: {name}")


def _format_ovr_section(label: str, trials: int, results: tuple[RungResult, ...]) -> str:
    lines = [f"=== OVR -> Favorite Win Rate ({label}, {trials} trials/rung) ==="]
    for r in results:
        lines.append(
            f"  Net +{r.net_ovr_edge:>2} OVR: "
            f"{r.win_rate * 100:5.1f}% "
            f"[95% CI {r.ci_low * 100:5.1f} - {r.ci_high * 100:5.1f}]"
        )
    rates = [r.win_rate for r in results]
    monotonic = all(curr >= prev - 0.02 for prev, curr in zip(rates, rates[1:]))
    slope_pp = (rates[-1] - rates[0]) * 100
    top_floor = rates[-1]
    slope_ok = slope_pp >= 10.0
    floor_ok = top_floor >= 0.60
    lines.append(
        f"  Monotonicity: {'PASS' if monotonic else 'FAIL'}   "
        f"Min slope: {'PASS' if slope_ok else 'FAIL'} ({slope_pp:+.1f}pp, need +10pp)   "
        f"Top floor: {'PASS' if floor_ok else 'FAIL'} ({top_floor * 100:.1f}% vs 60%)"
    )
    return "\n".join(lines)


def _format_moment_section(results: tuple[RungResult, ...]) -> str:
    summary = summarize_moments(results)
    lines = ["=== Moment Occurrence ===", "                       per-match    matches-with    total"]
    for kind, entry in summary.items():
        lines.append(
            f"  {kind:<20}    {entry['per_match']:>5.2f}        "
            f"{entry['pct_matches_with'] * 100:>3.0f}%         {int(entry['total']):>6}"
        )
    return "\n".join(lines)


def _format_lengths_section(results: tuple[RungResult, ...]) -> str:
    q = summarize_match_lengths(results)
    return (
        "=== Match Length (events) ===\n"
        f"  P25: {q['p25']:>4}   P50: {q['p50']:>4}   "
        f"P75: {q['p75']:>4}   P95: {q['p95']:>4}"
    )


def _format_outcomes_section(results: tuple[RungResult, ...]) -> str:
    o = summarize_outcomes(results)
    return (
        "=== Outcomes (across all rungs) ===\n"
        f"  Favorite: {o['fav']} ({o['fav_pct']}%)   "
        f"Dog: {o['dog']} ({o['dog_pct']}%)   "
        f"Draw: {o['draw']} ({o['draw_pct']}%)"
    )


def _run_one(driver_name: str, trials: int, seed_offset: int) -> int:
    print(f"=== {driver_name} ===")
    try:
        driver = _build_driver(driver_name)
        results = run_ovr_curve(
            driver,
            rungs=RUNGS,
            trials_per_rung=trials,
            seed_offset=seed_offset,
        )
    except Exception as exc:
        print(f"  Curve aborted: {type(exc).__name__}: {exc}")
        print("  (If driver=official, see Plan D design Section 'Risks'.)")
        return 2
    print(_format_ovr_section(driver_name, trials, results))
    print()
    print(_format_moment_section(results))
    print()
    print(_format_lengths_section(results))
    print()
    print(_format_outcomes_section(results))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier engine health probe (Plan D)")
    parser.add_argument("--trials", type=int, default=400, help="Trials per OVR rung (default 400)")
    parser.add_argument(
        "--driver",
        choices=("rec", "official", "both"),
        default="rec",
        help="Engine driver to probe (default rec)",
    )
    parser.add_argument("--seed-offset", type=int, default=0, help="Seed offset for reproducible re-runs")
    args = parser.parse_args()

    drivers = ("rec", "official") if args.driver == "both" else (args.driver,)
    worst = 0
    for name in drivers:
        rc = _run_one(name, args.trials, args.seed_offset)
        worst = max(worst, rc)
        print()
    return worst


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
