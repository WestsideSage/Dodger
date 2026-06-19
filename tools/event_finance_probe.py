"""Event-finance probe (V27 The Calendar).

Proof obligation (the declared-stakes check): every event purse is a MARGIN of
league payout, never its rival — the same squeeze invariant V22 set for the
economy and V26 set for fan income. For each event (Domestic Cup by tier, Cloth
Classic, No-Sting Open, MSI, Founders' Exhibition) this prints the champion
purse vs a league champion's payout (the strongest league money) at each tier
and the ratio, and checks the purse never reaches half of league payout — i.e.
winning the league is always worth materially more than winning an event.

Usage: python tools/event_finance_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.config import DEFAULT_ECONOMY as E, DEFAULT_EVENTS as EV  # noqa: E402
from dodgeball_sim.economy import TIER_PAYOUT_MULTIPLIERS, season_income_k  # noqa: E402

_TIER_NAME = {1: "Premier", 2: "Challenger", 3: "District"}
# A cross-division Domestic Cup over 21 clubs (7 per tier x 3 tiers) is a
# 5-round knockout (16->8->4->2->1 with byes); the champion wins 5 matches.
_CUP_ROUNDS = 5
# The gate: an event's champion earnings must stay below this share of a league
# champion's payout — a clear margin, never a rival. Tuned with headroom: the
# largest event purse (MSI, 100k) sits at ~21% of the smallest league title
# (District champion, 480k), so 50% is a comfortable ceiling that still fails
# loudly if a purse ever rivals league money.
_MAX_RATIO = 0.5


def _league_champion_payout_k(tier: int) -> int:
    """A league champion's payout at this tier (the strongest league money)."""
    base = season_income_k(rank=1, total_clubs=7, playoff_result="champion", config=E)
    mult = TIER_PAYOUT_MULTIPLIERS.get(tier, 1.0)
    return round((base["league_payout_k"] + base["playoff_bonus_k"]) * mult)


def _cup_champion_max_k(tier: int) -> int:
    """The most a cup champion earns: the champion purse + a per-round-win
    participation margin for every round they played."""
    return EV.cup_purse_champion_k.get(tier, 0) + _CUP_ROUNDS * EV.cup_purse_per_win_k.get(tier, 0)


def main() -> int:
    ok = True
    print("Event purses vs league champion payout (the declared-stakes check)\n")
    print(f"{'event':>22} {'tier':>9} {'purse_k':>8} {'league_k':>9} {'ratio':>7}")

    # Domestic Cup: tier-scaled champion purse + per-round wins vs that tier's
    # league champion payout.
    for tier in (1, 2, 3):
        purse = _cup_champion_max_k(tier)
        league = _league_champion_payout_k(tier)
        ratio = purse / league if league else 0.0
        if ratio >= _MAX_RATIO:
            ok = False
        print(f"{'Domestic Cup (max run)':>22} {_TIER_NAME[tier]:>9} {purse:>8} {league:>9} {ratio:>6.0%}")
        # And the bare champion purse (no per-round wins) for the honest floor.
        bare = EV.cup_purse_champion_k.get(tier, 0)
        print(f"{'Domestic Cup (champion)':>22} {_TIER_NAME[tier]:>9} {bare:>8} {league:>9} {bare / league:>6.0%}")

    # Flat purses (invitationals / MSI / Founders): cross-tier by fame, so the
    # strictest comparison is the SMALLEST league title (District champion). Also
    # show Premier for scale.
    flat = [
        ("Cloth Classic", EV.invitational_purse_champion_k),
        ("No-Sting Open", EV.invitational_purse_champion_k),
        ("MSI", EV.msi_purse_champion_k),
        ("Founders' Exhibition", EV.founders_purse_champion_k),
    ]
    for name, purse in flat:
        for tier in (3, 1):
            league = _league_champion_payout_k(tier)
            ratio = purse / league if league else 0.0
            # Gate against the strictest tier (District); Premier is display-only.
            if tier == 3 and ratio >= _MAX_RATIO:
                ok = False
            tag = _TIER_NAME[tier] + (" league" if tier == 3 else "")
            print(f"{name:>22} {tag:>9} {purse:>8} {league:>9} {ratio:>6.0%}")

    # Runner-up purses are smaller by construction; assert they never rival a
    # league champion payout either (the same gate, strictest tier).
    ru = [
        ("Cup runner-up (D3)", EV.cup_purse_runner_up_k.get(3, 0)),
        ("Invitational runner-up", EV.invitational_purse_runner_up_k),
    ]
    league_d3 = _league_champion_payout_k(3)
    for name, purse in ru:
        ratio = purse / league_d3 if league_d3 else 0.0
        if ratio >= _MAX_RATIO:
            ok = False
        print(f"{name:>22} {'District':>9} {purse:>8} {league_d3:>9} {ratio:>6.0%}")

    print(
        f"\nInvariant: every event purse is a margin (<{_MAX_RATIO:.0%}) of a league "
        "champion's payout at every tier — winning the league is always worth "
        "materially more than winning an event."
    )
    print(
        "RESULT:",
        "PASS — events are a declared margin, never a league-payout rival"
        if ok
        else "FAIL — an event purse rivals league payout",
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
