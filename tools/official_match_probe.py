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

from dodgeball_sim.engine_driver import DriverMatchInput, DriverMatchOutput  # noqa: E402
from dodgeball_sim.official_engine import run_autonomous_match  # noqa: E402
from dodgeball_sim.rulesets import RulesetSelection  # noqa: E402

from probe_lib import run_ovr_curve, summarize_match_lengths, summarize_outcomes  # noqa: E402

RUNGS = (0, 4, 8, 12)


class RealOfficialMatchDriver:
    """EngineDriver that drives the multi-set run_autonomous_match (the shipping path)."""

    tier_id = "official_match"

    def __init__(self, ruleset: str = "official_foam") -> None:
        self.profile = RulesetSelection(ruleset).to_profile()

    def run(self, mi: DriverMatchInput) -> DriverMatchOutput:
        res = run_autonomous_match(
            profile=self.profile,
            match_id=mi.match_id,
            team_a_id=mi.team_a_id,
            team_b_id=mi.team_b_id,
            starters_a=mi.starters_a,
            starters_b=mi.starters_b,
            player_lookup=mi.player_lookup,
            policy_a=mi.policy_a,
            policy_b=mi.policy_b,
            seed=mi.seed,
        )
        score = res.official_match_score
        return DriverMatchOutput(
            events=res.events,
            winner_team_id=res.winner_team_id,
            final_active_a=getattr(score, "team_a_game_points", 0),
            final_active_b=getattr(score, "team_b_game_points", 0),
            moment_events=(),
            replay_state=res.replay_state,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Corrected official match-engine probe")
    ap.add_argument("--trials", type=int, default=500)
    ap.add_argument("--ruleset", default="official_foam")
    args = ap.parse_args()

    driver = RealOfficialMatchDriver(args.ruleset)
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
