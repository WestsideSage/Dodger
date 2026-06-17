"""Squeeze-never-spiral probe (V25 The Market).

Proof obligation: player wages make climbing a *squeeze* (promotion inflates
payroll as it raises prize money) but never a *spiral* — the wage bill must stay
a MODERATE fraction of a tier's income so that climbing raises wages AND income
together and a competitive club stays solvent at every rung (the V23 -217k
precedent rejected an economy that bled a club out over multiple seasons).

This is a STATIC tier-solvency check (cleaner than a noisy weak-auto-pilot run
whose deficit is dominated by V22 staff cost): for each tier it prices a
competitive 9-player squad's wage bill and compares it to that tier's prize
money for a competitive finish. Wages are the V25 layer in isolation — staff
payroll is a separate V22 cost and not counted here.

Usage: python tools/squeeze_probe.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.config import DEFAULT_CONTRACTS, DEFAULT_ECONOMY  # noqa: E402
from dodgeball_sim.contracts import second_contract_salary_k  # noqa: E402
from dodgeball_sim.economy import TIER_PAYOUT_MULTIPLIERS, season_income_k  # noqa: E402

# A representative competitive squad per tier: 9 players, OVR rising with tier.
_SQUAD = 9
_TIER_OVR = {3: 62, 2: 74, 1: 84}
_TIER_NAME = {3: "District", 2: "Challenger", 1: "Premier"}


def _tier_income_k(tier: int, *, rank: int = 2, total: int = 7, playoff: str | None) -> int:
    base = season_income_k(rank=rank, total_clubs=total, playoff_result=playoff, config=DEFAULT_ECONOMY)
    mult = TIER_PAYOUT_MULTIPLIERS.get(tier, 1.0)
    return round((base["league_payout_k"] + base["playoff_bonus_k"]) * mult)


def main() -> int:
    argparse.ArgumentParser().parse_args()

    print(f"{'tier':>10} {'OVR':>4} {'wages':>7} {'income(2nd)':>11} {'income(champ)':>13} {'wage%':>6}")
    ok = True
    prev_wages = -1
    for tier in (3, 2, 1):
        ovr = _TIER_OVR[tier]
        wages = _SQUAD * second_contract_salary_k(ovr, tier, DEFAULT_CONTRACTS)
        income_mid = _tier_income_k(tier, rank=2, playoff="semifinalist")
        income_champ = _tier_income_k(tier, rank=1, playoff="champion")
        frac = wages / income_mid
        # MODERATE: wages are a real bite but a competitive (2nd + semifinal)
        # finish still clears them with room for the rest of the budget.
        moderate = 0.15 <= frac <= 0.55
        climbs = wages > prev_wages  # promotion raises payroll
        prev_wages = wages
        ok = ok and moderate and climbs
        print(f"{_TIER_NAME[tier]:>10} {ovr:>4} {wages:>7} {income_mid:>11} {income_champ:>13} {frac:>6.0%}")

    print("\nInvariant: wages are 15-55% of a competitive finish's prize money at "
          "every tier (squeeze, not tyranny), and promotion raises both together.")
    print("RESULT:", "PASS — squeeze, never a spiral" if ok else "FAIL — wage scale off")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
