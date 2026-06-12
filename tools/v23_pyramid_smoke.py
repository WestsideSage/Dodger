"""V23 dev smoke — run one full pyramid season and print the postseason story.

Throwaway diagnostic (not a gate): founds a D3 club, auto-pilots season 1
through the whole pyramid postseason, then dumps stage matches, the ledger,
and the worlds history.

Usage: python tools/v23_pyramid_smoke.py [--takeover] [--seasons N]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from dodgeball_sim.career_setup import (  # noqa: E402
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.persistence import (  # noqa: E402
    get_state,
    load_division_map,
    load_season,
    load_season_outcome,
    load_standings,
)
from dodgeball_sim.pyramid_postseason import (  # noqa: E402
    load_postseason_ledger,
    load_worlds_history,
)
from dodgeball_sim.use_cases import auto_pilot_weeks  # noqa: E402
from dodgeball_sim.offseason_service import (  # noqa: E402
    OffseasonError,
    advance_offseason_beat_payload,
    begin_next_season_payload,
    get_offseason_beat_payload,
    recruit_offseason_payload,
)


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
    parser.add_argument("--takeover", action="store_true")
    parser.add_argument("--seasons", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260612)
    args = parser.parse_args()

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    if args.takeover:
        initialize_curated_manager_career(
            conn, "aurora", args.seed, ruleset_selection="official_foam", world="pyramid"
        )
        user_club = "aurora"
    else:
        club = build_expansion_club(
            name="Smoke Test FC", primary_color="#101010", secondary_color="#FAFAFA",
            venue_name="The Lab", home_region="Testville", tagline="smoke",
        )
        roster = generate_expansion_roster(club.club_id, args.seed)
        initialize_curated_manager_career(
            conn, club.club_id, args.seed, custom_club=club, custom_roster=roster,
            ruleset_selection="official_foam", world="pyramid",
        )
        user_club = club.club_id

    for season_num in range(1, args.seasons + 1):
        season_id = get_state(conn, "active_season_id")
        t0 = time.time()
        result = auto_pilot_weeks(conn, max_weeks=None)
        elapsed = time.time() - t0
        print(f"\n=== {season_id} (user={user_club}) ===")
        print(f"auto_pilot: {result['weeks_simulated']} weeks, stop={result['stop_reason']}, "
              f"state={result['next_state']}, {elapsed:.1f}s")

        season = load_season(conn, season_id)
        playoff_matches = [
            m for m in season.scheduled_matches if "_p_" in m.match_id
        ]
        completed = {
            row["match_id"]: row
            for row in conn.execute(
                "SELECT match_id, winner_club_id FROM match_records WHERE season_id = ?",
                (season_id,),
            )
        }
        print(f"postseason fixtures ({len(playoff_matches)}):")
        for m in sorted(playoff_matches, key=lambda x: (x.week, x.match_id)):
            row = completed.get(m.match_id)
            winner = row["winner_club_id"] if row else "PENDING"
            print(f"  w{m.week:02d} {m.match_id}: {m.home_club_id} vs {m.away_club_id} -> {winner}")

        outcome = load_season_outcome(conn, season_id)
        print(f"user-division outcome: champion={outcome.champion_club_id if outcome else None} "
              f"runner_up={outcome.runner_up_club_id if outcome else None}")
        ledger = load_postseason_ledger(conn, season_id)
        if ledger:
            print(f"champions: {ledger['champions']}")
            print(f"promoted: {ledger['promoted']}")
            print(f"relegated: {ledger['relegated']}")
            print(f"worlds: {ledger['worlds']['champion_name']} over {ledger['worlds']['runner_up_name']}")
        else:
            print("!! NO POSTSEASON LEDGER")
        division_map = load_division_map(conn, season_id)
        user_div = division_map.get(user_club)
        rows = load_standings(conn, season_id)
        div_rows = [r for r in rows if division_map.get(r.club_id) and division_map[r.club_id].division_id == (user_div.division_id if user_div else "?")]
        div_rows.sort(key=lambda r: (-r.points, r.club_id))
        print(f"user division ({user_div.division_name if user_div else '?'}) table:")
        for r in div_rows:
            tag = " <== YOU" if r.club_id == user_club else ""
            print(f"  {r.club_id:14s} {r.wins}-{r.losses}-{r.draws} pts={r.points}{tag}")

        if season_num < args.seasons:
            walk_offseason(conn)
            from dodgeball_sim.economy import load_season_finances

            finances = load_season_finances(conn)
            if finances:
                print(
                    f"finances: rank {finances['rank']}/{finances['total_clubs']} in "
                    f"{finances.get('division_name')} (x{finances.get('tier_multiplier')}), "
                    f"payout {finances['league_payout_k']}k + bonus {finances['playoff_bonus_k']}k "
                    f"- payroll {finances['staff_payroll_k']}k -> treasury {finances['closing_treasury_k']}k"
                )
            new_season_id = get_state(conn, "active_season_id")
            new_map = load_division_map(conn, new_season_id)
            print(f"next season {new_season_id}: user now in "
                  f"{new_map[user_club].division_name if user_club in new_map else '???'}")
            per_div: dict[str, int] = {}
            for m in new_map.values():
                per_div[m.division_id] = per_div.get(m.division_id, 0) + 1
            print(f"division sizes: {per_div}")

    print(f"\nworlds history: {load_worlds_history(conn)}")


if __name__ == "__main__":
    main()
