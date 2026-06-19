"""AI board-coverage probe (V24 Phase 1).

Measures whether whole-world AI recruiting (the V23 end-state-dominance fix in
recruitment._eligible_ai_offer_clubs) gives EVERY division new blood, or starves
some divisions on too small a class.

For each seed: a fresh pyramid takeover career (user 'aurora' in the Premier
League). Seed the prospect class the way the offseason scouting wiring does, run
the AI offseason signing sweep, and tally, per division: AI signings, the number
of distinct clubs that signed, and the mean true OVR of the signed prospects.

A healthy world signs new blood in every division every offseason; a starved one
leaves divisions empty. Prize finding: top divisions (Premier/Circuit) must draw
real talent so the Worlds feeders keep pace with a compounding user.

Usage: python tools/ai_board_coverage_probe.py [--seeds 20] [--start 1]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    get_state,
    load_division_map,
    load_prospect_pool,
    load_recruitment_signings,
    save_prospect_pool,
)
from dodgeball_sim.recruitment import (  # noqa: E402
    generate_prospect_pool,
    run_ai_offseason_signings,
)
from dodgeball_sim.rng import DeterministicRNG, derive_seed  # noqa: E402


def probe_seed(seed: int) -> dict:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    season_id = get_state(conn, "active_season_id")
    digits = "".join(ch for ch in season_id if ch.isdigit())
    class_year = int(digits) if digits else 1
    if not load_prospect_pool(conn, class_year):
        rng = DeterministicRNG(derive_seed(seed, "prospect_gen", str(class_year)))
        save_prospect_pool(conn, generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG))

    prospects = {p.player_id: p for p in load_prospect_pool(conn, class_year)}
    class_size = len(prospects)
    run_ai_offseason_signings(conn, seed, season_id, class_year, "aurora")

    division_map = load_division_map(conn, season_id)
    ai = [s for s in load_recruitment_signings(conn, season_id) if s.source == "ai"]
    by_div: dict[str, dict] = defaultdict(lambda: {"signings": 0, "clubs": set(), "ovrs": [], "name": ""})
    for s in ai:
        seat = division_map.get(s.club_id)
        if seat is None:
            continue
        bucket = by_div[seat.division_id]
        bucket["name"] = seat.division_name
        bucket["signings"] += 1
        bucket["clubs"].add(s.club_id)
        prospect = prospects.get(s.player_id)
        if prospect is not None:
            bucket["ovrs"].append(prospect.true_overall())
    return {
        "seed": seed,
        "class_size": class_size,
        "total_ai_signings": len(ai),
        "by_div": {
            div_id: {
                "name": b["name"],
                "signings": b["signings"],
                "clubs": len(b["clubs"]),
                "mean_ovr": mean(b["ovrs"]) if b["ovrs"] else None,
            }
            for div_id, b in by_div.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--start", type=int, default=1)
    args = parser.parse_args()

    rows = [probe_seed(s) for s in range(args.start, args.start + args.seeds)]
    class_size = rows[0]["class_size"] if rows else 0
    print(f"seeds={len(rows)} class_size={class_size}")
    print(f"mean total AI signings/offseason: {mean(r['total_ai_signings'] for r in rows):.1f}")

    # Aggregate per division across seeds.
    div_names: dict[str, str] = {}
    div_signings: dict[str, list[int]] = defaultdict(list)
    div_covered: dict[str, int] = defaultdict(int)
    div_ovrs: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        seen = set()
        for div_id, d in r["by_div"].items():
            div_names[div_id] = d["name"]
            div_signings[div_id].append(d["signings"])
            div_covered[div_id] += 1 if d["signings"] > 0 else 0
            if d["mean_ovr"] is not None:
                div_ovrs[div_id].append(d["mean_ovr"])
            seen.add(div_id)

    print(f"\n{'division':<22}{'cover%':>8}{'sign/os':>9}{'meanOVR':>9}")
    for div_id in sorted(div_names, key=lambda d: div_names[d]):
        cover = 100 * div_covered[div_id] / len(rows)
        avg_sign = mean(div_signings[div_id]) if div_signings[div_id] else 0.0
        avg_ovr = mean(div_ovrs[div_id]) if div_ovrs[div_id] else float("nan")
        print(f"{div_names[div_id]:<22}{cover:>7.0f}%{avg_sign:>9.1f}{avg_ovr:>9.1f}")

    fully_covered = all(
        div_covered[div_id] == len(rows) for div_id in div_names
    )
    print(f"\nevery division signs new blood every seed: {fully_covered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
