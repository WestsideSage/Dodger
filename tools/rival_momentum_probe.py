"""Rival-momentum defensibility probe (V24 Phase 5).

Measures the Phase 5 momentum gate: at EQUAL effort, does an EARLY lead beat a
LATE entry? For each seed we take a fresh pyramid career, pick a leadable focused
prospect (top rival pursuit <= 60), seed a leading interest, and apply ONE
identical contact — once at week 1 (many weeks left) and once at a late week
(none left). Leading the race compounds with the weeks remaining, so the early
contact must end with strictly more interest.

A healthy result: early > late on every seed, with a meaningful average edge.
The edge is the momentum constant (RIVAL_MOMENTUM_PER_WEEK x weeks-left, capped
at RIVAL_MOMENTUM_MAX) made visible.

Usage: python tools/rival_momentum_probe.py [--seeds 12] [--start 1]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from statistics import mean

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.career_state import CareerStateCursor  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    get_state,
    load_career_state_cursor,
    load_prospect_pool,
    save_career_state_cursor,
    set_state,
)
from dodgeball_sim.recruiting_office import (  # noqa: E402
    apply_recruiting_action,
    compute_market_signals,
    toggle_focus,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _seed_leadable(conn, season_id, club_id):
    pool = sorted(load_prospect_pool(conn, 1), key=lambda p: p.public_ratings_band["ovr"][1])
    for prospect in pool[:15]:
        toggle_focus(conn, prospect.player_id)
        sig = compute_market_signals(conn, season_id, club_id, prospect_ids=[prospect.player_id])
        top = sig[prospect.player_id]["top_rival_interest"]
        if top <= 60:
            set_state(
                conn,
                "prospect_recruitment_actions_json",
                json.dumps({prospect.player_id: {"scouted": True, "contacted": True, "interest": top + 6}}),
            )
            return prospect.player_id, top
        toggle_focus(conn, prospect.player_id)
    return None, None


def _contact_at_week(seed: int, week: int) -> int | None:
    conn = _conn()
    initialize_curated_manager_career(conn, "aurora", seed, world="pyramid")
    season_id = get_state(conn, "active_season_id")
    club_id = get_state(conn, "player_club_id")
    pid, _top = _seed_leadable(conn, season_id, club_id)
    if pid is None:
        return None
    cur = load_career_state_cursor(conn)
    save_career_state_cursor(
        conn, CareerStateCursor(state=cur.state, season_number=cur.season_number, week=week)
    )
    result = apply_recruiting_action(
        conn, prospect_id=pid, action="contact", season_id=season_id,
        player_club_id=club_id, root_seed=seed, history=[],
    )
    return int(result["interest_after"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--start", type=int, default=1)
    args = parser.parse_args()

    edges = []
    wins = 0
    measured = 0
    print(f"{'seed':>8} {'early':>6} {'late':>6} {'edge':>6}")
    for seed in range(args.start, args.start + args.seeds):
        early = _contact_at_week(seed, 1)
        late = _contact_at_week(seed, 99)
        if early is None or late is None:
            print(f"{seed:>8} {'--':>6} {'--':>6} {'--':>6}  (no leadable prospect)")
            continue
        measured += 1
        edge = early - late
        edges.append(edge)
        wins += int(early > late)
        print(f"{seed:>8} {early:>6} {late:>6} {edge:>+6}")

    print("-" * 32)
    if measured:
        print(f"early-beats-late: {wins}/{measured} seeds; mean edge +{mean(edges):.1f} interest")
    else:
        print("no leadable scenarios measured")


if __name__ == "__main__":
    main()
