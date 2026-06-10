"""Measure contested Signing Day offer strengths across seeds (V16 Task 3).

For each seed: fresh curated career, enter the offseason recruitment state,
take the TOP prospect by public estimate, and record the strongest rival
(AI) offer on that prospect plus the user's offer at three courtship levels
(uncourted base, contact+visit, max interest). Prints win rates so
CONTESTED_USER_OFFER_BASE / _INTEREST_WEIGHT can be tuned against evidence:
an uncourted star pick should be genuinely losable, a fully-courted one
near-safe.

Usage: python tools/contested_offer_probe.py [--seeds 60] [--start 1]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
for entry in (str(_REPO / "src"), str(_REPO / "tools")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import (
    CONTESTED_USER_OFFER_BASE,
    CONTESTED_USER_OFFER_INTEREST_WEIGHT,
)
from dodgeball_sim.offseason_ceremony import (
    available_recruitment_choices,
    finalize_season,
    initialize_manager_offseason,
)
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_command_history_all_seasons,
    load_recruitment_offers,
    load_season,
    set_state,
)
from dodgeball_sim.recruiting_actions import current_interest
from dodgeball_sim.recruiting_office import _credibility_score
from dodgeball_sim.recruitment import (
    _eligible_ai_offer_clubs,
    _ensure_recruitment_prepared,
)


def probe_seed(root_seed: int) -> dict:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=root_seed)
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    finalize_season(conn, season, rosters)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=root_seed)

    choices = available_recruitment_choices(conn, 1)
    top = next(c for c in choices if c["kind"] == "prospect")
    eligible = _eligible_ai_offer_clubs(conn, season_id, "aurora")
    _ensure_recruitment_prepared(
        conn,
        root_seed,
        season_id,
        1,
        user_club_id="aurora",
        round_number=1,
        eligible_club_ids=eligible,
    )
    offers = load_recruitment_offers(conn, season_id, 1)
    rivals = [o.offer_strength for o in offers if o.player_id == top["prospect_id"]]
    credibility = _credibility_score(
        conn, season_id, "aurora", load_command_history_all_seasons(conn)
    )
    base_interest_value = current_interest(
        {}, pipeline_tier=top["pipeline_tier"], credibility_score=credibility
    )
    courted_interest = min(100, base_interest_value + 32)
    return {
        "seed": root_seed,
        "top": top["prospect_id"],
        "band_mid": (top["public_ovr_band"][0] + top["public_ovr_band"][1]) / 2,
        "rival_max": max(rivals) if rivals else None,
        "rival_count": len(rivals),
        "interest_base": base_interest_value,
        "interest_courted": courted_interest,
    }


def user_offer(interest: int) -> float:
    return CONTESTED_USER_OFFER_BASE + interest * CONTESTED_USER_OFFER_INTEREST_WEIGHT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=60)
    parser.add_argument("--start", type=int, default=1)
    args = parser.parse_args()

    rows = [probe_seed(seed) for seed in range(args.start, args.start + args.seeds)]
    contested = [r for r in rows if r["rival_max"] is not None]
    uncourted_losses = [
        r for r in contested if user_offer(r["interest_base"]) < r["rival_max"]
    ]
    courted_losses = [
        r for r in contested if user_offer(r["interest_courted"]) < r["rival_max"]
    ]
    max_interest_losses = [
        r for r in contested if user_offer(100) < r["rival_max"]
    ]

    print(
        f"config: base={CONTESTED_USER_OFFER_BASE} "
        f"weight={CONTESTED_USER_OFFER_INTEREST_WEIGHT}"
    )
    print(f"seeds probed: {len(rows)}; top pick contested: {len(contested)}")
    if contested:
        rival_values = sorted(r["rival_max"] for r in contested)
        mid = rival_values[len(rival_values) // 2]
        print(
            f"rival max offer on top pick: min={rival_values[0]:.1f} "
            f"median={mid:.1f} max={rival_values[-1]:.1f}"
        )
        bases = sorted(r["interest_base"] for r in contested)
        print(f"uncourted interest: min={bases[0]} median={bases[len(bases)//2]} max={bases[-1]}")
        print(
            f"uncourted top-pick losses: {len(uncourted_losses)}/{len(contested)} "
            f"({100 * len(uncourted_losses) / len(contested):.0f}%)"
        )
        print(
            f"courted (+32) top-pick losses: {len(courted_losses)}/{len(contested)} "
            f"({100 * len(courted_losses) / len(contested):.0f}%)"
        )
        print(
            f"interest-100 top-pick losses: {len(max_interest_losses)}/{len(contested)} "
            f"({100 * len(max_interest_losses) / len(contested):.0f}%)"
        )
        witness = [
            r["seed"]
            for r in contested
            if user_offer(r["interest_base"]) < r["rival_max"]
            and user_offer(r["interest_courted"]) > r["rival_max"]
        ]
        print(f"witness seeds (uncourted loses, courted wins): {witness[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
