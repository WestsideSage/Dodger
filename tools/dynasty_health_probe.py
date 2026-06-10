"""Dynasty health probe — multi-season retention/balance evidence.

WHAT THIS MEASURES
------------------
A deterministic, seeded N-season sweep of the SHIPPING career loop: a real
curated career (`initialize_curated_manager_career`), each season fast-forwarded
through the canonical `auto_pilot_weeks` path (real weekly plans, real AI plans,
real playoffs), then the real offseason
(`finalize_season` -> `initialize_manager_offseason` -> user picks through the
CONTESTED Signing Day round (`sign_chosen_rookie_contested`, snipes possible)
-> AI Signing Day sweep (`ensure_ai_offseason_signings`) ->
`begin_next_season`). Per season it records:

  * user club rank / record / title, champion + runner-up identity
  * fielded-6 mean OVR for the user club, the best AI club, and the AI mean
    (the snowball curve: does the user's structural recruiting advantage
    compound into a runaway OVR edge?)
  * roster sizes (does the AI league bleed depth toward the 6-player floor
    while the user builds to the 12 cap?)
  * signings actually made (true OVR + stored potential ceiling), user picks
    SNIPED by rival offers, and AI prospect signings (league churn — V16)
  * retirements, ratified records, and Hall of Fame inductions per offseason
    (does the history layer keep producing texture in seasons 5-10, or go
    quiet?)

HONESTY / SCOPE
---------------
The user club is driven by the AUTO-PILOT defaults (Balanced intent, canonical
fielded-6, no scouting actions, no staff hires, no dev-focus orders). That is
the real shipping fast-forward path, so the sweep isolates the STRUCTURAL
asymmetries between the user club and AI clubs:

  * the user attempts up to `--signings` prospect picks per offseason (the
    shipping picker's 3-signing / 12-roster cap) through the contested round
    — a sniped pick costs no slot but signs nobody and the probe moves on,
  * AI clubs are trimmed to 9, refilled from leftovers when below 6
    (`_sign_ai_replacements`), and sign real prospects in the V16 Signing Day
    sweep (1 per club per offseason),
  * AI clubs develop on BALANCED focus with no staff modifier.

It does NOT model an engaged player's tactics/scouting/staff play, so the
measured user edge is a LOWER bound on the structural snowball. `--signings 0`
runs the same sweep with recruiting skipped to isolate recruiting's
contribution.

DETERMINISM
-----------
Fully seeded end to end (the loop reuses the per-match seeded RNG and the
seeded offseason streams). A fixed seed set reproduces the sweep byte-for-byte.

No printing or argparse in the pure functions — the CLI at the bottom composes
them, mirroring `tools/archetype_champion_parity_probe.py`.

Usage:
    python tools/dynasty_health_probe.py [--seeds 6] [--seasons 10]
        [--signings 3] [--club aurora] [--ruleset official_foam]
        [--seed-base 20260600]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "tools"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.offseason_ceremony import (  # noqa: E402
    available_recruitment_choices,
    begin_next_season,
    ensure_ai_offseason_signings,
    finalize_season,
    initialize_manager_offseason,
    sign_chosen_rookie_contested,
)
from dodgeball_sim.offseason_presentation import MAX_USER_ROSTER  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_hall_of_fame,
    load_lineup_default,
    load_season,
    load_season_outcome,
    load_standings,
)
from dodgeball_sim.use_cases import auto_pilot_weeks  # noqa: E402


# The shipping offseason picker allows up to 3 signings per offseason
# (offseason_service.recruit_offseason_payload).
MAX_SIGNINGS_PER_OFFSEASON = 3


@dataclass(frozen=True)
class SeasonSnapshot:
    season_number: int
    season_id: str
    user_rank: int
    user_wins: int
    user_losses: int
    user_draws: int
    user_points: int
    champion_club_id: str
    champion_is_user: bool
    runner_up_club_id: str | None
    user_six_ovr: float
    best_ai_six_ovr: float
    mean_ai_six_ovr: float
    user_roster_size: int
    ai_roster_sizes: tuple[int, ...]
    signings: tuple[dict, ...]          # {player_id, overall, potential}
    user_snipes: int                    # user picks lost to rival offers
    ai_signings: tuple[dict, ...]       # {player_id, club_id} (league churn)
    retirements_total: int
    retirements_user: int
    records_ratified: int
    hof_inducted_total: int             # cumulative size of the hall


@dataclass(frozen=True)
class DynastyRun:
    root_seed: int
    user_club_id: str
    seasons: tuple[SeasonSnapshot, ...]


@dataclass(frozen=True)
class DynastySweep:
    runs: tuple[DynastyRun, ...]
    signings_per_offseason: int
    ruleset: str | None

    def seasons_per_run(self) -> int:
        return len(self.runs[0].seasons) if self.runs else 0


def _fielded_six_ovr(conn: sqlite3.Connection, club_id: str, roster) -> float:
    """Mean OVR of the club's resolved fielded six (lineup default order)."""
    by_id = {player.id: player for player in roster}
    default = load_lineup_default(conn, club_id) or [p.id for p in roster]
    six = [by_id[pid] for pid in default if pid in by_id][:6]
    if not six:
        six = list(roster)[:6]
    if not six:
        return 0.0
    return round(mean(player.overall_skill() for player in six), 2)


def _user_standings_row(standings, user_club_id: str):
    ordered = sorted(
        standings, key=lambda row: (-row.points, -row.elimination_differential, row.club_id)
    )
    for index, row in enumerate(ordered, start=1):
        if row.club_id == user_club_id:
            return index, row
    return len(ordered) + 1, None


def run_dynasty_career(
    *,
    root_seed: int,
    seasons: int,
    signings_per_offseason: int,
    user_club_id: str = "aurora",
    ruleset_selection: str | None = "official_foam",
    optimize_user_lineup: bool = False,
) -> DynastyRun:
    """Run one career for `seasons` full seasons through the shipping loop.

    `optimize_user_lineup` models an ENGAGED player who re-optimizes their
    lineup each offseason (one click in the Lineup Editor). The auto-pilot
    default keeps the creation-time order + seats each signing at slot 6, so
    developed bench players never enter the fielded six on their own.
    """
    signings_per_offseason = max(0, min(signings_per_offseason, MAX_SIGNINGS_PER_OFFSEASON))
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        initialize_curated_manager_career(
            conn, user_club_id, root_seed, ruleset_selection=ruleset_selection
        )
        snapshots: list[SeasonSnapshot] = []
        for season_number in range(1, seasons + 1):
            result = auto_pilot_weeks(conn)
            if result["stop_reason"] not in ("season_complete", "already_complete"):
                raise RuntimeError(
                    f"seed {root_seed} season {season_number}: auto-pilot stopped "
                    f"on {result['stop_reason']!r} after {result['weeks_simulated']} weeks"
                )

            season_id = get_state(conn, "active_season_id")
            season = load_season(conn, season_id)
            clubs = load_clubs(conn)
            rosters = load_all_rosters(conn)

            finalize_season(conn, season, rosters)
            initialize_manager_offseason(
                conn, season, clubs, rosters, root_seed=root_seed
            )

            # ---- collect post-season / post-offseason telemetry --------------
            standings = load_standings(conn, season_id)
            rank, row = _user_standings_row(standings, user_club_id)
            outcome = load_season_outcome(conn, season_id)
            champion_id = outcome.champion_club_id if outcome else ""
            runner_up = outcome.runner_up_club_id if outcome else None

            retire_rows = json.loads(
                get_state(conn, "offseason_retirements_json") or "[]"
            )
            record_rows = json.loads(
                get_state(conn, "offseason_records_ratified_json") or "[]"
            )

            # ---- user signings through the shipping CONTESTED picker path ----
            # Mirrors recruit_offseason_payload's auto-pick: best available by
            # PUBLIC estimate, resolved through the contested round. A sniped
            # pick signs nobody (and costs no signing slot in the shipping
            # flow); the probe simply tries the next-best remaining choice.
            signings: list[dict] = []
            user_snipes = 0
            cursor = load_career_state_cursor(conn)
            attempts = 0
            while len(signings) < signings_per_offseason and attempts < (
                signings_per_offseason + 6
            ):
                attempts += 1
                current = load_all_rosters(conn).get(user_club_id, [])
                if len(current) >= MAX_USER_ROSTER:
                    break
                # Distinct names: `season_number` is the outer loop label that
                # SeasonSnapshot records; the cursor's view drives signing.
                cursor_season = cursor.season_number or 1
                choices = available_recruitment_choices(conn, cursor_season)
                if not choices:
                    break
                signed, pick_outcome = sign_chosen_rookie_contested(
                    conn, user_club_id, cursor_season, choices[0]["prospect_id"]
                )
                if signed is None:
                    if pick_outcome is not None and pick_outcome.get("kind") == "sniped":
                        user_snipes += 1
                        continue
                    break
                signings.append(
                    {
                        "player_id": signed.id,
                        "overall": signed.overall_skill(),
                        "potential": int(signed.traits.potential),
                    }
                )

            # ---- AI Signing Day sweep (V16 league churn) ----------------------
            ensure_ai_offseason_signings(conn)
            from dodgeball_sim.persistence import load_recruitment_signings

            ai_signings = tuple(
                {"player_id": s.player_id, "club_id": s.club_id}
                for s in load_recruitment_signings(conn, season_id)
                if s.source == "ai"
            )

            if optimize_user_lineup:
                from dodgeball_sim.lineup import optimize_ai_lineup
                from dodgeball_sim.persistence import save_lineup_default

                refreshed = load_all_rosters(conn).get(user_club_id, [])
                save_lineup_default(conn, user_club_id, optimize_ai_lineup(refreshed))
                conn.commit()

            post_rosters = load_all_rosters(conn)
            user_roster = post_rosters.get(user_club_id, [])
            ai_sizes = tuple(
                sorted(
                    len(post_rosters.get(cid, []))
                    for cid in clubs
                    if cid != user_club_id
                )
            )
            ai_six = [
                _fielded_six_ovr(conn, cid, post_rosters.get(cid, []))
                for cid in sorted(clubs)
                if cid != user_club_id and post_rosters.get(cid)
            ]
            snapshots.append(
                SeasonSnapshot(
                    season_number=season_number,
                    season_id=season_id,
                    user_rank=rank,
                    user_wins=row.wins if row else 0,
                    user_losses=row.losses if row else 0,
                    user_draws=row.draws if row else 0,
                    user_points=row.points if row else 0,
                    champion_club_id=champion_id,
                    champion_is_user=champion_id == user_club_id,
                    runner_up_club_id=runner_up,
                    user_six_ovr=_fielded_six_ovr(conn, user_club_id, user_roster),
                    best_ai_six_ovr=max(ai_six) if ai_six else 0.0,
                    mean_ai_six_ovr=round(mean(ai_six), 2) if ai_six else 0.0,
                    user_roster_size=len(user_roster),
                    ai_roster_sizes=ai_sizes,
                    signings=tuple(signings),
                    user_snipes=user_snipes,
                    ai_signings=ai_signings,
                    retirements_total=len(retire_rows),
                    retirements_user=sum(
                        1 for r in retire_rows if r.get("club_id") == user_club_id
                    ),
                    records_ratified=len(record_rows),
                    hof_inducted_total=len(load_hall_of_fame(conn)),
                )
            )

            cursor = begin_next_season(conn, cursor, clubs)
        return DynastyRun(
            root_seed=root_seed, user_club_id=user_club_id, seasons=tuple(snapshots)
        )
    finally:
        conn.close()


def run_dynasty_sweep(
    *,
    seeds: tuple[int, ...],
    seasons: int,
    signings_per_offseason: int,
    user_club_id: str = "aurora",
    ruleset_selection: str | None = "official_foam",
    optimize_user_lineup: bool = False,
) -> DynastySweep:
    runs = tuple(
        run_dynasty_career(
            root_seed=seed,
            seasons=seasons,
            signings_per_offseason=signings_per_offseason,
            user_club_id=user_club_id,
            ruleset_selection=ruleset_selection,
            optimize_user_lineup=optimize_user_lineup,
        )
        for seed in seeds
    )
    return DynastySweep(
        runs=runs,
        signings_per_offseason=signings_per_offseason,
        ruleset=ruleset_selection,
    )


def default_seed_set(*, count: int, seed_base: int = 20260600, stride: int = 211) -> tuple[int, ...]:
    return tuple(seed_base + i * stride for i in range(count))


# ---------------------------------------------------------------------------
# CLI (composition + printing only)
# ---------------------------------------------------------------------------

def _format_report(sweep: DynastySweep) -> str:
    runs = sweep.runs
    n_seasons = sweep.seasons_per_run()
    lines = [
        "=== Dynasty Health Sweep (shipping career loop) ===",
        f"  seeds={len(runs)}  seasons/seed={n_seasons}  "
        f"user-signings/offseason={sweep.signings_per_offseason}  ruleset={sweep.ruleset}",
        "",
        "  Per-season aggregates (mean across seeds):",
        "  season | user rank | user W-L-D     | user titles | userOVR | bestAI | meanAI | edge   | rec/hof | retire",
    ]
    for idx in range(n_seasons):
        snaps = [run.seasons[idx] for run in runs]
        titles = sum(1 for s in snaps if s.champion_is_user)
        mean_rank = mean(s.user_rank for s in snaps)
        mean_w = mean(s.user_wins for s in snaps)
        mean_l = mean(s.user_losses for s in snaps)
        mean_d = mean(s.user_draws for s in snaps)
        u_ovr = mean(s.user_six_ovr for s in snaps)
        best_ai = mean(s.best_ai_six_ovr for s in snaps)
        mean_ai = mean(s.mean_ai_six_ovr for s in snaps)
        recs = mean(s.records_ratified for s in snaps)
        hof = mean(s.hof_inducted_total for s in snaps)
        retire = mean(s.retirements_total for s in snaps)
        lines.append(
            f"  S{idx + 1:<5} | {mean_rank:>9.2f} | "
            f"{mean_w:4.1f}-{mean_l:4.1f}-{mean_d:4.1f} | "
            f"{titles:>2}/{len(runs):<8} | {u_ovr:>7.2f} | {best_ai:>6.2f} | {mean_ai:>6.2f} | "
            f"{u_ovr - best_ai:>+6.2f} | {recs:3.1f}/{hof:3.1f} | {retire:5.2f}"
        )

    total_titles = sum(1 for run in runs for s in run.seasons if s.champion_is_user)
    total_seasons = len(runs) * n_seasons
    lines.append("")
    lines.append(
        f"  User titles: {total_titles}/{total_seasons} "
        f"({100.0 * total_titles / max(1, total_seasons):.1f}%)  "
        f"[parity baseline = 1/6 = 16.7% of seasons]"
    )

    champs: dict[str, int] = {}
    for run in runs:
        for snap in run.seasons:
            champs[snap.champion_club_id] = champs.get(snap.champion_club_id, 0) + 1
    lines.append("  Champion distribution (club): " + ", ".join(
        f"{cid}={n}" for cid, n in sorted(champs.items(), key=lambda kv: -kv[1])
    ))

    last = [run.seasons[-1] for run in runs]
    lines.append(
        f"  Final-season roster sizes: user={mean(s.user_roster_size for s in last):.1f}  "
        f"AI={[s.ai_roster_sizes for s in last][0] if last else ()} (first seed shown)"
    )
    signed_pot = [
        s["potential"] for run in runs for snap in run.seasons for s in snap.signings
    ]
    signed_ovr = [
        s["overall"] for run in runs for snap in run.seasons for s in snap.signings
    ]
    if signed_ovr:
        lines.append(
            f"  Signings: n={len(signed_ovr)}  mean OVR={mean(signed_ovr):.1f}  "
            f"mean potential={mean(signed_pot):.1f}"
        )
    total_ai_signings = sum(
        len(snap.ai_signings) for run in runs for snap in run.seasons
    )
    total_user_snipes = sum(
        snap.user_snipes for run in runs for snap in run.seasons
    )
    lines.append(
        f"  League churn: AI prospect signings={total_ai_signings} "
        f"({total_ai_signings / max(1, total_seasons):.1f}/offseason)  "
        f"user picks sniped={total_user_snipes}"
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dynasty health probe (multi-season sweep)")
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--seasons", type=int, default=10)
    parser.add_argument("--signings", type=int, default=3,
                        help="User signings per offseason (0 isolates recruiting; max 3)")
    parser.add_argument("--club", type=str, default="aurora")
    parser.add_argument(
        "--ruleset",
        choices=("official_foam", "official_cloth", "generic"),
        default="official_foam",
    )
    parser.add_argument("--seed-base", type=int, default=20260600)
    parser.add_argument(
        "--optimize-lineup", action="store_true",
        help="Model an engaged player: re-optimize the user lineup each offseason",
    )
    args = parser.parse_args()

    ruleset = None if args.ruleset == "generic" else args.ruleset
    sweep = run_dynasty_sweep(
        seeds=default_seed_set(count=args.seeds, seed_base=args.seed_base),
        seasons=args.seasons,
        signings_per_offseason=args.signings,
        user_club_id=args.club,
        ruleset_selection=ruleset,
        optimize_user_lineup=args.optimize_lineup,
    )
    print(_format_report(sweep))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
