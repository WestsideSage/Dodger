"""Archetype champion-distribution probe (WT-23).

WHAT THIS MEASURES
------------------
A deterministic, seeded N-season league sweep that tallies which *program
archetype* wins the championship, then reports the champion-archetype
distribution. It is a **diversity / degeneracy guard**, NOT a "parity" claim:
it asserts the league does not collapse to one or two champion archetypes and
that no single archetype monopolizes the title beyond a measured ceiling.

WHY IT EXISTS (the V12 overclaim it replaces)
---------------------------------------------
`docs/STATUS.md` credits V12 with "a 50-season Monte Carlo sweep confirming
excellent archetype championship parity." That sweep
(`scratch/sweep_archetypes.py`) was NOT reproducible as a faithful signal: it
*manually* `UPDATE`-d six fictional archetypes onto the curated clubs, then
measured championships among labels the sim would never actually assign. Under
the REAL archetype derivation (`persistence.classify_club_archetype`), the
stock curated 6-club league only ever instantiates ~2 archetypes (Power
Throwers / Balanced Rebuild), so a faithful stock sweep can never show ">=3
champion archetypes." This probe earns >=3 honestly instead (see below).

THE LEAGUE THIS PROBE SWEEPS (disclosed controlled experiment)
--------------------------------------------------------------
A **matched-mean-OVR, skill-SHAPE-varied** league. Every club's roster is built
at the SAME mean OVR (~64) but with the (accuracy+power) vs (dodge+catch) SKEW
varied, so the real `classify_club_archetype` lands the clubs on three distinct
SHAPE archetypes:

    * (acc+pow) > (dodge+catch) + 2  -> "Power Throwers"
    * (dodge+catch) > (acc+pow) + 2  -> "Defensive Specialist"
    * neither skew                   -> "Balanced Rebuild"

The archetype label is always **DERIVED** by `classify_club_archetype`, never
assigned (that derivation is the bright line vs. the V12 cheat). The only thing
this probe constructs is starting-roster skill *distribution at matched
strength* — the disclosed controlled variable. Strength-defined archetypes
(Contender = avg_ovr >= 67; Development Factory = young+low-OVR; Aging Veterans
= old) are deliberately NOT spanned: an archetype defined as "high OVR" would
win tautologically because the engine rewards OVR, which is not a meaningful
distribution question.

HEADLINE FINDING (ADR 0002)
---------------------------
"Matched OVR" is NOT "matched strength." `PlayerRatings.overall_skill()` is the
unweighted mean of five skills, but every shipping engine (rec + official
foam/cloth) rewards defense (dodge+catch — a catch outs the thrower AND
resurrects a defender) over offense. So at equal OVR the Defensive Specialist
shape dominates championships (~60-75% at this fixture, robust across all three
engines and independent of coach policy). The probe's job is to surface that
the league still produces >=3 distinct champions and that the dominant shape
stays under a measured ceiling — not to claim the shapes are balanced.

RELATIONSHIP TO THE WT-25 RECRUITING-TIER FLIP
----------------------------------------------
WT-23 is the stated safety net for the WT-25 `base_interest` tier flip. The
flip is confined to **user-facing recruiting valuation**
(`recruiting_actions.base_interest`, reached only from the recruit board /
`recruitment` / `recruiting_office`). The AI champion path here never calls
`base_interest`: AI rosters evolve via `offseason_ceremony._sign_ai_replacements`,
a pure OVR-sorted fill from a deterministic rookie/free-agent pool. Therefore
this probe's champion distribution is **invariant** to the WT-25 flip by
construction. That is exactly the safety-net guarantee: it proves the flip did
not perturb AI-archetype championship outcomes (the determinism is the proof).
It does NOT exercise `base_interest` directly — claiming otherwise would be a
new lie.

DETERMINISM
-----------
Fully seeded: roster construction, every regular-season match, the
playoff replay-until-winner loop, the offseason development/draft, and the
season rollover all derive from `root_seed`. A fixed seed set reproduces the
champion sequence byte-for-byte (verified). The pytest gate
(`tests/test_archetype_champion_parity.py`) pins a small, suite-fast seed set;
this CLI defaults to a larger nightly N for a tighter population estimate.

No printing or argparse in the pure functions — the CLI at the bottom composes
them, mirroring `tools/probe_lib.py` / `tools/tier_engine_health_probe.py`.

Usage:
    python tools/archetype_champion_parity_probe.py [--seeds 50] [--seasons 2]
        [--clubs 6] [--ruleset official_foam|official_cloth|generic] [--seed-base 20260000]
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "tools"))

from dodgeball_sim.archetype_derivation import derive_archetype  # noqa: E402
from dodgeball_sim.career_state import CareerState, CareerStateCursor  # noqa: E402
from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG  # noqa: E402
from dodgeball_sim.franchise import create_season  # noqa: E402
from dodgeball_sim.game_loop import (  # noqa: E402
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from dodgeball_sim.league import Club, Conference, League  # noqa: E402
from dodgeball_sim.lineup import optimize_ai_lineup  # noqa: E402
from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings, PlayerTraits  # noqa: E402
from dodgeball_sim.offseason_ceremony import (  # noqa: E402
    begin_next_season,
    finalize_season,
    initialize_manager_offseason,
)
from dodgeball_sim.persistence import (  # noqa: E402
    classify_club_archetype,
    create_schema,
    load_all_rosters,
    load_clubs,
    load_season,
    load_standings,
    save_career_state_cursor,
    save_club,
    save_lineup_default,
    save_playoff_bracket,
    save_season,
    save_season_format,
    save_season_outcome,
    set_state,
)
from dodgeball_sim.playoffs import (  # noqa: E402
    PLAYOFF_FORMAT,
    create_final_match,
    create_semifinal_bracket,
    outcome_from_final,
)
from dodgeball_sim.rng import DeterministicRNG, derive_seed  # noqa: E402
from dodgeball_sim.scouting_center import initialize_scouting_for_career  # noqa: E402

from probe_lib import wilson_ci  # noqa: E402  (reuse the existing Wilson CI helper)


# --- Sentinel: a player_club_id that is NOT a league member -------------------
# initialize_manager_offseason exempts the player's club from AI roster trim and
# _sign_ai_replacements. Pointing player_club_id at a club that does not exist
# makes EVERY real club an AI club, so all clubs get symmetric offseason upkeep
# and none depletes via retirements over a multi-season sweep.
_SENTINEL_PLAYER_CLUB = "__no_user__"

# --- Matched-OVR shape profiles ----------------------------------------------
# Per-role (accuracy, power, dodge, catch) base. stamina is fixed so the
# five-skill mean OVR is matched across shapes; tactical/courage/iq/conditioning
# are held neutral so they do not tilt the (acc+pow) vs (dodge+catch) skew that
# classify_club_archetype reads. Ages sit inside (22.5, 26.5) so the age- and
# OVR-gated archetypes (Aging Veterans / Contender / Development Factory) never
# trigger — only the SHAPE archetypes can be derived.
_SHAPES: dict[str, tuple[int, int, int, int]] = {
    "throw": (74, 74, 54, 54),       # (acc+pow) high  -> Power Throwers
    "catch": (54, 54, 74, 74),       # (dodge+catch) high -> Defensive Specialist
    "balanced": (64, 64, 64, 64),    # flat -> Balanced Rebuild
}
_MATCHED_STAMINA = 64  # makes mean(acc,pow,dodge,catch,stamina) == 64 for every shape
_SHAPED_AGE = 24       # in (22.5, 26.5): blocks Aging Veterans + Development Factory


@dataclass(frozen=True)
class ParityResult:
    """Aggregate champion-archetype distribution across a seeded sweep."""

    distribution: dict[str, int]          # archetype -> championships won
    total_titles: int
    distinct_champion_archetypes: int
    max_archetype: str
    max_share: float                      # 0..1
    wilson95_upper: float                 # Wilson 95% upper bound on max_share
    init_population: dict[str, int]        # frozen init archetype -> club-seasons seen
    per_seed_champions: dict[int, tuple[str, ...]]
    seeds: tuple[int, ...]
    seasons_per_seed: int
    clubs: int
    ruleset: str | None


# ---------------------------------------------------------------------------
# League construction (pure: builds in-memory clubs/rosters, no global I/O)
# ---------------------------------------------------------------------------

def _build_shaped_roster(club_id: str, shape_key: str, seed: int, count: int = 6) -> list[Player]:
    """Six players at matched mean OVR with the requested skill SHAPE.

    A small deterministic Gaussian jitter keeps players non-identical while the
    skew and matched-OVR property hold in expectation. Archetype is DERIVED.
    """
    rng = DeterministicRNG(seed)
    acc, pow_, dod, cat = _SHAPES[shape_key]

    def jit(base: int) -> int:
        return int(round(base + rng.gauss(0, 2)))

    roster: list[Player] = []
    for i in range(1, count + 1):
        ratings = PlayerRatings(
            accuracy=jit(acc),
            power=jit(pow_),
            dodge=jit(dod),
            catch=jit(cat),
            stamina=jit(_MATCHED_STAMINA),
            tactical_iq=jit(60),
            catch_courage=jit(60),
            throw_selection_iq=jit(60),
            conditioning_curve=jit(60),
        ).apply_bounds()
        roster.append(
            Player(
                id=f"{club_id}_{i}",
                name=f"{club_id.upper()} P{i}",
                ratings=ratings,
                archetype=derive_archetype(ratings),
                traits=PlayerTraits(
                    potential=int(round(rng.gauss(50, 6))),
                    growth_curve=50,
                    consistency=50,
                    pressure=50,
                ),
                age=_SHAPED_AGE,
                club_id=club_id,
                newcomer=(i >= 5),
            )
        )
    return roster


# Coach policies are held NEUTRAL and identical across clubs so the experiment
# isolates roster SHAPE. (Shape dominance is robust whether policy is neutral or
# shape-correlated — verified during go/no-go — but neutral policy is the
# cleaner controlled variable.)
def _shape_assignments(n_clubs: int) -> list[tuple[str, str]]:
    keys = list(_SHAPES.keys())
    return [(f"club_{i}_{keys[i % len(keys)]}", keys[i % len(keys)]) for i in range(n_clubs)]


def _init_league(
    conn: sqlite3.Connection,
    *,
    root_seed: int,
    n_clubs: int,
    ruleset_selection: str | None,
) -> CareerStateCursor:
    """Persist a matched-OVR shape-varied league through the real save path."""
    create_schema(conn)
    assignments = _shape_assignments(n_clubs)
    clubs_and_rosters: list[tuple[Club, list[Player]]] = []
    for club_id, shape in assignments:
        roster = _build_shaped_roster(club_id, shape, derive_seed(root_seed, "roster", club_id))
        club = Club(
            club_id=club_id,
            name=club_id.replace("_", " ").title(),
            colors="x/y",
            home_region="Region",
            founded_year=2026,
            coach_policy=CoachPolicy(),  # neutral + identical across clubs
        )
        clubs_and_rosters.append((club, roster))

    for club, roster in clubs_and_rosters:
        # REAL derivation — never assign the archetype by hand.
        archetype = classify_club_archetype(club.club_id, False, roster)
        club = dataclasses.replace(club, program_archetype=archetype)
        save_club(conn, club, roster)
        save_lineup_default(conn, club.club_id, optimize_ai_lineup(roster))

    league = League(
        league_id="parity_league",
        name="Champion Parity League",
        conferences=(Conference("main", "Main", tuple(c.club_id for c, _ in clubs_and_rosters)),),
    )
    season = create_season("season_1", 2026, league, root_seed=root_seed)
    save_season(conn, season)
    save_season_format(conn, season.season_id, PLAYOFF_FORMAT)
    set_state(conn, "root_seed", str(root_seed))
    set_state(conn, "active_season_id", season.season_id)
    set_state(conn, "player_club_id", _SENTINEL_PLAYER_CLUB)
    set_state(conn, "difficulty", "pro")
    if ruleset_selection:
        from dodgeball_sim.rulesets import RulesetSelection

        RulesetSelection(ruleset_selection)  # validate
        set_state(conn, "ruleset_selection", ruleset_selection)
    cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, season_number=1, week=1)
    save_career_state_cursor(conn, cursor)
    initialize_scouting_for_career(conn, root_seed=root_seed, config=DEFAULT_SCOUTING_CONFIG)
    conn.commit()
    return cursor


# ---------------------------------------------------------------------------
# Season + playoff simulation (reuses the shipping game_loop / playoffs paths)
# ---------------------------------------------------------------------------

def _sim_playoff_until_winner(conn, scheduled, clubs, rosters, base_seed: int, *, max_attempts: int = 64):
    """Replay a playoff match with incrementing seed until it is decisive.

    Foam/cloth official games can draw; playoffs must produce a winner. The
    bracket builders raise on an unresolved finalist, so we resolve here by
    re-seeding (deterministic given base_seed).
    """
    attempt = 0
    record = None
    while attempt <= max_attempts:
        record = simulate_scheduled_match(
            conn,
            scheduled=scheduled,
            clubs=clubs,
            rosters=rosters,
            root_seed=base_seed + attempt,
            difficulty="pro",
            record_engine_match=False,
        )
        if record.result.winner_team_id is not None:
            return record
        attempt += 1
    return record  # pragma: no cover - exhausting 64 reseeds is not observed


def run_one_career(
    *,
    root_seed: int,
    n_clubs: int,
    seasons: int,
    ruleset_selection: str | None,
) -> tuple[tuple[str, ...], dict[str, str]]:
    """Simulate `seasons` full seasons (regular + playoffs + offseason) for one seed.

    Returns (champion_archetype_per_season, frozen_init_archetype_by_club).
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        cursor = _init_league(
            conn, root_seed=root_seed, n_clubs=n_clubs, ruleset_selection=ruleset_selection
        )
        init_archetypes = {cid: club.program_archetype for cid, club in load_clubs(conn).items()}
        champions: list[str] = []
        for season_num in range(1, seasons + 1):
            season_id = f"season_{season_num}"
            season = load_season(conn, season_id)
            clubs = load_clubs(conn)
            rosters = load_all_rosters(conn)
            reg_weeks = season.total_weeks()

            for week in range(1, reg_weeks + 1):
                for match in season.matches_for_week(week):
                    simulate_scheduled_match(
                        conn,
                        scheduled=match,
                        clubs=clubs,
                        rosters=rosters,
                        root_seed=root_seed + season_num * 1000 + week,
                        difficulty="pro",
                        record_engine_match=False,
                    )
            recompute_regular_season_standings(conn, season)
            standings = load_standings(conn, season_id)

            bracket, semis = create_semifinal_bracket(season_id, standings, week=reg_weeks + 1)
            save_playoff_bracket(conn, bracket)
            winners: dict[str, str] = {}
            for semi in semis:
                rec = _sim_playoff_until_winner(
                    conn, semi, clubs, rosters, root_seed + season_num * 2000
                )
                winners[semi.match_id] = rec.result.winner_team_id  # type: ignore[assignment]
            bracket, final_match = create_final_match(bracket, winners, week=reg_weeks + 2)
            final_rec = _sim_playoff_until_winner(
                conn, final_match, clubs, rosters, root_seed + season_num * 3000
            )
            outcome = outcome_from_final(
                bracket,
                final_match_id=final_match.match_id,
                home_club_id=final_match.home_club_id,
                away_club_id=final_match.away_club_id,
                winner_club_id=final_rec.result.winner_team_id,  # type: ignore[arg-type]
            )
            save_season_outcome(conn, outcome)
            champions.append(clubs[outcome.champion_club_id].program_archetype)

            finalize_season(conn, season, rosters)
            initialize_manager_offseason(conn, season, clubs, rosters, root_seed=root_seed)
            cursor = begin_next_season(conn, cursor, clubs)
        return tuple(champions), init_archetypes
    finally:
        conn.close()


def run_parity_sweep(
    *,
    seeds: tuple[int, ...],
    seasons: int = 2,
    n_clubs: int = 6,
    ruleset_selection: str | None = "official_foam",
) -> ParityResult:
    """Run the deterministic champion-archetype sweep and aggregate the result."""
    counter: collections.Counter[str] = collections.Counter()
    init_pop: collections.Counter[str] = collections.Counter()
    per_seed: dict[int, tuple[str, ...]] = {}
    for seed in seeds:
        champions, init_archetypes = run_one_career(
            root_seed=seed,
            n_clubs=n_clubs,
            seasons=seasons,
            ruleset_selection=ruleset_selection,
        )
        counter.update(champions)
        init_pop.update(init_archetypes.values())
        per_seed[seed] = champions

    total = sum(counter.values())
    if total:
        max_archetype, max_titles = counter.most_common(1)[0]
        max_share = max_titles / total
        _lo, wilson_hi = wilson_ci(max_titles, total)
    else:  # pragma: no cover - empty sweep is not a valid call
        max_archetype, max_share, wilson_hi = "", 0.0, 0.0

    return ParityResult(
        distribution=dict(counter.most_common()),
        total_titles=total,
        distinct_champion_archetypes=len(counter),
        max_archetype=max_archetype,
        max_share=max_share,
        wilson95_upper=wilson_hi,
        init_population=dict(init_pop.most_common()),
        per_seed_champions=per_seed,
        seeds=tuple(seeds),
        seasons_per_seed=seasons,
        clubs=n_clubs,
        ruleset=ruleset_selection,
    )


def default_seed_set(*, count: int, seed_base: int = 20260000, stride: int = 137) -> tuple[int, ...]:
    """Deterministic seed set shared by the CLI and the pytest gate.

    The pytest gate pins (count=16, seed_base=20260000, stride=137); reuse this
    helper there so the test and tool never drift on how seeds are generated.
    """
    return tuple(seed_base + i * stride for i in range(count))


# ---------------------------------------------------------------------------
# CLI (composition + printing only)
# ---------------------------------------------------------------------------

def _format_report(result: ParityResult, *, cap: float | None = None) -> str:
    lines = [
        "=== Archetype Champion Distribution (matched-OVR, shape-varied league) ===",
        f"  seeds={len(result.seeds)}  clubs={result.clubs}  "
        f"seasons/seed={result.seasons_per_seed}  ruleset={result.ruleset}  "
        f"total titles={result.total_titles}",
        "  Init-archetype population (frozen identities, derived by classify_club_archetype):",
    ]
    for archetype, n in result.init_population.items():
        lines.append(f"    {archetype:<22} {n:>4}")
    lines.append("  Champion-archetype distribution:")
    for archetype, n in result.distribution.items():
        share = 100.0 * n / result.total_titles if result.total_titles else 0.0
        lines.append(f"    {archetype:<22} {n:>4}  ({share:5.1f}%)")
    lines.append(
        f"  distinct champion archetypes: {result.distinct_champion_archetypes}   "
        f"max: {result.max_archetype} = {result.max_share * 100:.1f}%   "
        f"(Wilson95 upper {result.wilson95_upper:.3f})"
    )
    if cap is not None:
        lines.append(
            f"  Degeneracy gate: distinct>=3 {'PASS' if result.distinct_champion_archetypes >= 3 else 'FAIL'}   "
            f"max<=cap({cap:.2f}) {'PASS' if result.max_share <= cap else 'FAIL'}"
        )
    lines.append(
        "  NOTE: matched OVR != matched strength — the economy always favors some "
        "shape (pre-V17: Defensive ~65%; post-WT-20: Power Throwers ~64%, since "
        "full-length matches express the throw-quality economy). This is a "
        "diversity guard, not a parity claim; shape parity is a V19 design item."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Archetype champion-distribution probe (WT-23)")
    parser.add_argument("--seeds", type=int, default=50, help="Number of seeds (default 50, nightly)")
    parser.add_argument("--seasons", type=int, default=2, help="Seasons simulated per seed (default 2)")
    parser.add_argument("--clubs", type=int, default=6, help="Clubs in the league (default 6; need >=4 for the bracket)")
    parser.add_argument(
        "--ruleset",
        choices=("official_foam", "official_cloth", "generic"),
        default="official_foam",
        help="Ruleset to sweep (default official_foam; 'generic' uses the rec engine)",
    )
    parser.add_argument("--seed-base", type=int, default=20260000, help="First seed (default 20260000)")
    parser.add_argument("--cap", type=float, default=0.85, help="Degeneracy ceiling for the printed gate line (default 0.85)")
    args = parser.parse_args()

    ruleset = None if args.ruleset == "generic" else args.ruleset
    if args.clubs < 4:
        print("ERROR: need at least 4 clubs for the top-4 playoff bracket.", file=sys.stderr)
        return 2
    seeds = default_seed_set(count=args.seeds, seed_base=args.seed_base)
    result = run_parity_sweep(
        seeds=seeds, seasons=args.seasons, n_clubs=args.clubs, ruleset_selection=ruleset
    )
    print(_format_report(result, cap=args.cap))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
