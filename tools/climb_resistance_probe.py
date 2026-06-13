"""Climb-resistance probe — measures the founding path's difficulty curve.

PLAYTEST 4 found the climb collapses: a D3 founder reached Worlds champion by
Season 3 on the back of one-season development explosions (+28 OVR). This
probe runs the SHIPPING auto-pilot founding loop (recruiting skipped — the
explosion is the founders themselves) and prints, per season:

  tier, record, user fielded mean OVR, division rival mean OVR, the biggest
  single-player season delta, and the postseason outcome.

Auto-pilot is the LOWER bound on player strength (no recruiting, no dev
focus, no staff play) — if auto-pilot sweeps divisions, an engaged player
does it faster.

Usage: python tools/climb_resistance_probe.py [--seasons 6] [--seed N]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from statistics import mean

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.career_setup import (  # noqa: E402
    build_expansion_club,
    initialize_curated_manager_career,
)
from dodgeball_sim.archetype_derivation import derive_archetype  # noqa: E402
from dodgeball_sim.development import _TRAJECTORY_POTENTIAL_FLOOR  # noqa: E402
from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits  # noqa: E402
from dodgeball_sim.save_service import _founding_pool  # noqa: E402
from dodgeball_sim.offseason_service import (  # noqa: E402
    OffseasonError,
    advance_offseason_beat_payload,
    begin_next_season_payload,
    get_offseason_beat_payload,
    recruit_offseason_payload,
)
from dodgeball_sim.persistence import (  # noqa: E402
    get_state,
    load_all_rosters,
    load_division_map,
    load_standings,
)
from dodgeball_sim.pyramid_postseason import load_postseason_ledger  # noqa: E402
from dodgeball_sim.use_cases import auto_pilot_weeks  # noqa: E402


def walk_offseason(conn: sqlite3.Connection) -> None:
    payload = get_offseason_beat_payload(conn)
    for _ in range(24):
        state = payload.get("state")
        if state == "next_season_ready":
            break
        if state == "season_complete_recruitment_pending":
            payload = recruit_offseason_payload(conn, prospect_id="skip")
            continue
        try:
            payload = advance_offseason_beat_payload(conn)
        except OffseasonError:
            break
    begin_next_season_payload(conn)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260613)
    args = parser.parse_args()

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    club = build_expansion_club(
        name="Resistance Probe", primary_color="#111111", secondary_color="#EEEEEE",
        venue_name="Probe Hall", home_region="Probetown", tagline="probe",
    )

    # The REAL founding roster path (mirrors save_service.build_from_scratch_save):
    # founding-pool prospects with natural ceilings (best hidden + 8) raised by
    # trajectory arcs — the V22 economy Playtest 4's Pioneer Works drafted from.
    # Pick the best six by effective ceiling, the way an engaged founder does.
    pool = _founding_pool(args.seed)

    def effective_ceiling(prospect) -> float:
        natural = min(100.0, max(prospect.hidden_ratings.values()) + 8.0)
        floor = _TRAJECTORY_POTENTIAL_FLOOR.get(prospect.hidden_trajectory)
        return max(natural, floor) if floor is not None else natural

    picks = sorted(pool, key=lambda p: -effective_ceiling(p))[:6]
    roster = []
    for prospect in picks:
        ratings = PlayerRatings(
            accuracy=prospect.hidden_ratings["accuracy"],
            power=prospect.hidden_ratings["power"],
            dodge=prospect.hidden_ratings["dodge"],
            catch=prospect.hidden_ratings["catch"],
            stamina=prospect.hidden_ratings["stamina"],
            tactical_iq=prospect.hidden_ratings.get("tactical_iq", 50.0),
            catch_courage=prospect.hidden_ratings.get("catch_courage", 50.0),
            throw_selection_iq=prospect.hidden_ratings.get("throw_selection_iq", 50.0),
            conditioning_curve=prospect.hidden_ratings.get("conditioning_curve", 50.0),
        ).apply_bounds()
        roster.append(
            Player(
                id=prospect.player_id, name=prospect.name, age=prospect.age,
                club_id=club.club_id, newcomer=True, ratings=ratings,
                archetype=derive_archetype(ratings),
                traits=PlayerTraits(
                    potential=min(100.0, max(prospect.hidden_ratings.values()) + 8.0),
                    growth_curve=50.0, consistency=0.5, pressure=0.5,
                ),
            )
        )

    initialize_curated_manager_career(
        conn, club.club_id, args.seed, custom_club=club, custom_roster=roster,
        ruleset_selection="official_foam", world="pyramid",
    )
    # Trajectory arcs persist AFTER init (init wipes the table) — exactly as
    # the wizard build does.
    from dodgeball_sim.persistence import save_player_trajectory

    for prospect in picks:
        save_player_trajectory(conn, prospect.player_id, prospect.hidden_trajectory)
    conn.commit()
    user = club.club_id

    print(f"{'S':>2} {'tier':<10} {'record':<8} {'userOVR':>7} {'rivalOVR':>8} "
          f"{'maxJump':>7} outcome")
    prev_ovr: dict[str, float] = {}
    for season_num in range(1, args.seasons + 1):
        season_id = get_state(conn, "active_season_id")
        rosters_before = load_all_rosters(conn)
        prev_ovr = {
            p.id: p.overall_skill() for p in rosters_before.get(user, [])
        }
        auto_pilot_weeks(conn, max_weeks=None)

        division_map = load_division_map(conn, season_id)
        seat = division_map[user]
        rows = [
            r for r in load_standings(conn, season_id)
            if division_map.get(r.club_id)
            and division_map[r.club_id].division_id == seat.division_id
        ]
        me = next(r for r in rows if r.club_id == user)
        rosters_now = load_all_rosters(conn)

        def fielded_mean(club_id: str) -> float:
            players = sorted(
                rosters_now.get(club_id, []),
                key=lambda p: -p.overall_skill(),
            )[:6]
            return mean(p.overall_skill() for p in players) if players else 0.0

        user_ovr = fielded_mean(user)
        rival_ovr = mean(
            fielded_mean(r.club_id) for r in rows if r.club_id != user
        )
        ledger = load_postseason_ledger(conn, season_id) or {}
        champs = ledger.get("champions", {})
        outcome_bits = []
        if champs.get(seat.division_id) == user:
            outcome_bits.append("DIVISION CHAMPION")
        promo = (ledger.get("promotion_playoff") or {}).get(seat.division_id) or {}
        if promo.get("winner") == user:
            outcome_bits.append("promo winner")
        worlds = ledger.get("worlds") or {}
        if worlds.get("champion_club_id") == user:
            outcome_bits.append("WORLDS CHAMPION")

        walk_offseason(conn)
        rosters_after = load_all_rosters(conn)
        max_jump = max(
            (
                p.overall_skill() - prev_ovr[p.id]
                for p in rosters_after.get(user, [])
                if p.id in prev_ovr
            ),
            default=0.0,
        )
        new_map = load_division_map(conn, get_state(conn, "active_season_id"))
        next_seat = new_map.get(user)
        move = ""
        if next_seat and next_seat.division_id != seat.division_id:
            move = f" -> {next_seat.division_name}"
        print(
            f"{season_num:>2} {'D' + str(seat.tier) + ' ' + seat.division_id:<10} "
            f"{me.wins}-{me.losses}-{me.draws:<3} {user_ovr:>7.1f} {rival_ovr:>8.1f} "
            f"{max_jump:>+7.1f} {'; '.join(outcome_bits)}{move}"
        )


if __name__ == "__main__":
    main()
