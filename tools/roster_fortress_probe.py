"""Roster-fortress probe (V25 The Market).

Proof obligation: league-wide veteran movement is never zero — when contracts
expire, the AI transfer period churns rosters (re-signs the affordable, releases
the rest to free agency under the tier wage cap). No frozen rosters.

For each seed: a fresh pyramid career, then a realistic expiry wave (a third of
each AI club's squad set to term 0, the way the contract decrement drives them
over a dynasty). Run the AI transfer period and tally movement per tier.

Usage: python tools/roster_fortress_probe.py [--seeds 8]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_division_map,
    save_club,
)
from dodgeball_sim import transfer_market as tm  # noqa: E402
from dataclasses import replace  # noqa: E402


def _conn(seed: int) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _expiry_wave(conn, season_id, keepers=6, expiring=4, ovr=80):
    """Give every AI club a full developed squad — ``keepers`` contracted players
    (at the floor) priced at their tier wage, plus ``expiring`` DISCRETIONARY
    term-0 players above the floor. This is the steady state a dynasty reaches:
    the cap has room only for so many, so the surplus must be released."""
    from dodgeball_sim.config import DEFAULT_CONTRACTS
    from dodgeball_sim.contracts import second_contract_salary_k
    from dodgeball_sim.models import PlayerRatings

    division_map = load_division_map(conn, season_id)
    user = get_state(conn, "player_club_id")
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    ratings = PlayerRatings(accuracy=ovr, power=ovr, dodge=ovr, catch=ovr)
    for club_id, roster in rosters.items():
        if club_id == user or club_id not in division_map:
            continue
        tier = division_map[club_id].tier
        wage = second_contract_salary_k(ovr, tier, DEFAULT_CONTRACTS)
        base = roster or load_clubs(conn)  # fall back to anything to clone from
        squad = []
        for i in range(keepers + expiring):
            src = roster[i % len(roster)] if roster else None
            if src is None:
                continue
            squad.append(replace(
                src, id=f"{club_id}_fz_{i}", ratings=ratings, salary_k=wage,
                contract_term=(3 if i < keepers else 0),
            ))
        save_club(conn, clubs[club_id], squad)
    conn.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--start", type=int, default=20260617)
    args = ap.parse_args()

    all_zero = False
    print(f"{'seed':>10}  {'resigned':>8} {'released':>8} {'moved':>6}")
    totals = Counter()
    for s in range(args.start, args.start + args.seeds):
        conn = _conn(s)
        season_id = get_state(conn, "active_season_id")
        _expiry_wave(conn, season_id)
        summary = tm.run_ai_transfer_period(conn, season_id, s)
        totals.update(summary)
        if summary["moved"] == 0:
            all_zero = True
        print(f"{s:>10}  {summary['resigned']:>8} {summary['released']:>8} {summary['moved']:>6}")
        conn.close()

    print(f"\nTotals over {args.seeds} seeds: "
          f"resigned={totals['resigned']} released={totals['released']} moved={totals['moved']}")
    # The roster-fortress invariant is movement > 0 every offseason (no frozen
    # rosters); releases > 0 is the stronger evidence that the wage cap bites.
    ok = not all_zero
    print("RESULT:", "PASS — no frozen offseason" if ok else "FAIL — a frozen offseason",
          f"(cap-driven releases: {totals['released']})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
