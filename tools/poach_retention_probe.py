"""Poach / retention probe (V25 The Market).

The milestone's headline proof obligation: motivation GRADES demonstrably flip
who you keep and who you lose, not just money. Two demonstrations:

1. Retention flip — a star whose dealbreaker is Contender re-signs at a proud
   club and walks at a broke one, on the SAME generous offer. Only the grade
   differs (club prestige), so any flip is the grade's doing.
2. Poach tiebreak — at EQUAL money, a high-fit (loyal) player stays while a
   low-fit (mercenary) player is poached. Money tied, motivations decide.

Usage: python tools/poach_retention_probe.py [--seeds 12]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings  # noqa: E402
from dodgeball_sim.motivations import prospect_motivation_profile  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    create_schema,
    get_state,
    save_club_prestige,
)
from dodgeball_sim import transfer_market as tm  # noqa: E402


def _conn(seed: int) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _star(seed: int) -> Player:
    # A different star id per seed (the profile is id-derived) whose dealbreaker
    # is Contender, so club prestige is decisive.
    for i in range(seed * 17, seed * 17 + 2000):
        pid = f"probe_star_{i}"
        if prospect_motivation_profile(SimpleNamespace(player_id=pid)).dealbreaker == "contender":
            return Player(
                id=pid, name="Star",
                ratings=PlayerRatings(accuracy=86, power=86, dodge=84, catch=84),
                archetype=PlayerArchetype.THROWER, salary_k=30, contract_term=0,
            )
    raise SystemExit("no contender-dealbreaker id found")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--start", type=int, default=20260617)
    args = ap.parse_args()

    retention_flips = 0
    poach_flips = 0
    print(f"{'seed':>10}  {'proud':>8} {'broke':>8}  {'loyal':>6} {'merc':>6}")
    for s in range(args.start, args.start + args.seeds):
        conn = _conn(s)
        season_id = get_state(conn, "active_season_id")
        star = _star(s)
        generous = 10_000

        save_club_prestige(conn, "aurora", 90)
        conn.commit()
        proud = tm.evaluate_retention(conn, "aurora", star, generous, season_id)
        save_club_prestige(conn, "aurora", 1)
        conn.commit()
        broke = tm.evaluate_retention(conn, "aurora", star, generous, season_id)
        if proud.re_signed and not broke.re_signed:
            retention_flips += 1

        # Poach tiebreak at equal money.
        suitors = [tm.PoachSuitor("rival", "Rival", 1, 100, 80, "x")]
        loyal = tm.resolve_poaching(
            player_id="p", user_offer_k=100, expected_salary_k=100, fit=0.95,
            veto=False, dealbreaker_letter="A", suitors=suitors, salary_k=20, term_remaining=2,
        )
        merc = tm.resolve_poaching(
            player_id="p", user_offer_k=100, expected_salary_k=100, fit=0.05,
            veto=False, dealbreaker_letter="D", suitors=suitors, salary_k=20, term_remaining=2,
        )
        if loyal.stayed and not merc.stayed:
            poach_flips += 1

        print(f"{s:>10}  {('signs' if proud.re_signed else 'walks'):>8} "
              f"{('signs' if broke.re_signed else 'walks'):>8}  "
              f"{('stay' if loyal.stayed else 'gone'):>6} "
              f"{('stay' if merc.stayed else 'gone'):>6}")
        conn.close()

    n = args.seeds
    print(f"\nRetention grade-flip: {retention_flips}/{n}  (proud keeps, broke loses, same offer)")
    print(f"Poach grade-flip:     {poach_flips}/{n}  (loyal stays, mercenary poached, equal money)")
    ok = retention_flips == n and poach_flips == n
    print("RESULT:", "PASS — grades flip outcomes" if ok else "MIXED — see rows")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
