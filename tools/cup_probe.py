"""V27 The Calendar — Phase 2 Domestic Cup probe.

Runs the cup end-to-end across a sweep of seeds and asserts:
  1. Every cup resolves to a valid single champion (calendar integrity).
  2. Giant-killing (a lower-tier club beating a higher-tier one) occurs across
     seeds — the cup's whole point is cross-tier drama.
  3. Determinism: the same seed produces the same champion + bracket.

Usage:  python tools/cup_probe.py [--seeds N]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Make the package importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.cup_service import (  # noqa: E402
    detect_giant_killings,
    ensure_domestic_cup,
    resolve_domestic_cup,
)
from dodgeball_sim.economy import set_treasury_k  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    create_schema,
    get_state,
    load_division_map,
)


def _pyramid_career(seed: int):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def run(seeds: int = 20, base_seed: int = 20260617) -> int:
    valid = 0
    giant_kills = 0
    determinism_ok = True
    first_champion = None
    first_bracket = None

    for i in range(seeds):
        seed = base_seed + i
        conn, season_id = _pyramid_career(seed)
        ensure_domestic_cup(conn, season_id, seed)
        result = resolve_domestic_cup(conn, season_id, seed)
        champion = result["champion_club_id"]
        if champion:
            valid += 1
        dmap = load_division_map(conn, season_id)
        kills = detect_giant_killings(result, dmap)
        if kills:
            giant_kills += 1
            k0 = kills[0]
            print(f"  seed {seed}: {len(kills)} giant-killing(s) — "
                  f"{k0['winner_club_id']} (D{k0['winner_tier']}) beat "
                  f"{k0['loser_club_id']} (D{k0['loser_tier']}) in {k0['round']}")

        # Determinism: re-run the same seed, compare champion + bracket.
        conn2, sid2 = _pyramid_career(seed)
        ensure_domestic_cup(conn2, sid2, seed)
        result2 = resolve_domestic_cup(conn2, sid2, seed)
        if result2["champion_club_id"] != champion or result2["bracket"] != result["bracket"]:
            determinism_ok = False
            print(f"  seed {seed}: DETERMINISM BROKEN")
        if first_champion is None:
            first_champion = champion
            first_bracket = result["bracket"]

    print()
    print(f"Valid champions:    {valid}/{seeds}")
    print(f"Giant-killing seeds: {giant_kills}/{seeds} ({giant_kills / seeds:.0%})")
    print(f"Determinism:        {'OK' if determinism_ok else 'BROKEN'}")

    failures = []
    if valid != seeds:
        failures.append("not every seed produced a valid champion")
    if giant_kills == 0:
        failures.append("no giant-killing across the seed sweep — cup is not cross-tier")
    if not determinism_ok:
        failures.append("determinism broken")

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V27 Domestic Cup probe")
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--base-seed", type=int, default=20260617)
    args = parser.parse_args()
    sys.exit(run(seeds=args.seeds, base_seed=args.base_seed))
