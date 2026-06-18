"""Fan-income probe (V26 The Crowd).

Proof obligation: matchday + merch are a MEANINGFUL margin but never rival prize
money. For each tier and a range of fan counts (the curve a club climbs over a
dynasty), this prints fan income vs a competitive finish's prize money and the
ratio, and checks the income never reaches prize money at any tier.

Usage: python tools/fan_income_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.config import DEFAULT_ECONOMY as E, DEFAULT_FANS as F  # noqa: E402
from dodgeball_sim.economy import TIER_PAYOUT_MULTIPLIERS, season_income_k  # noqa: E402
from dodgeball_sim import fan_economy as fe  # noqa: E402

_TIER_NAME = {3: "District", 2: "Challenger", 1: "Premier"}
_FAN_CURVE = (1500, 5000, 12000, 30000)  # founder -> beloved dynasty


def _prize_k(tier: int) -> int:
    base = season_income_k(rank=2, total_clubs=7, playoff_result="semifinalist", config=E)
    mult = TIER_PAYOUT_MULTIPLIERS.get(tier, 1.0)
    return round((base["league_payout_k"] + base["playoff_bonus_k"]) * mult)


def main() -> int:
    ok = True
    print(f"{'tier':>10} {'fans':>7} {'matchday':>9} {'merch':>6} {'fan_total':>9} {'prize':>6} {'ratio':>6}")
    for tier in (3, 2, 1):
        prize = _prize_k(tier)
        # A built stadium + merch center (the developed end-state) is the stress test.
        cap = fe.stadium_capacity(tier, has_stadium=True)
        for fans in _FAN_CURVE:
            matchday = fe.matchday_income_k(fans, cap)
            merch = fe.merch_income_k(fans, fans // 4, has_merch=True)
            total = matchday + merch
            ratio = total / prize
            if total >= prize:
                ok = False
            print(f"{_TIER_NAME[tier]:>10} {fans:>7} {matchday:>9} {merch:>6} {total:>9} {prize:>6} {ratio:>6.0%}")

    print("\nInvariant: fan income is a margin of prize money at every tier and fan "
          "count, never its rival.")
    print("RESULT:", "PASS — a meaningful margin, never tyranny" if ok else "FAIL — fan income rivals prize money")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
