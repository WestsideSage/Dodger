"""V27 Phase 3 Step 1 — cloth / no-sting balance measurement harness.

For each of ``official_cloth`` and ``official_no_sting`` this composes three
measurements (the same three dimensions the foam gate locks in
``tests/test_archetype_champion_parity.py`` +
``tests/test_official_engine_balance.py``), so Step 2 can set the cloth/no-sting
caps from a real run instead of guessing:

1. **Parity** — reuse ``archetype_champion_parity_probe.run_parity_sweep``
   (matched-OVR, shape-varied league; reports the champion-archetype
   distribution, distinct champion archetypes, max share, and the Wilson-95
   upper bound on the max share). The foam gate's 0.85 cap was the Wilson-95
   upper from its recorded 16x2 run; cloth/no-sting caps must be measured the
   same way before they are locked.

2. **Health** — OVR curve has positive slope (favorite win rate rises with net
   OVR edge) AND no displayed core skill is a liability (a +12 bump in
   accuracy / power / dodge / catch never sits materially *below* the
   even-strength baseline). Reuses ``probe_lib.run_ovr_curve`` and the
   attribute-bump pattern from
   ``tests/test_official_engine_balance.py::_v17_attr_win_rate``.

3. **Stability** — a broad seeded match sweep under the ruleset with varied
   ratings, policies, and seeds, asserting zero crashes/exceptions. This is
   the regression guard for the V17 ``to_official_event`` officiating-discretion
   crash (a cloth crash, since fixed) — it must not return.

This is **measurement only** (Step 1 of 2). It writes NO gates and changes NO
balance constants — the cloth/no-sting ``RulesetProfile`` values
(``rulesets.CLOTH_OPEN`` / ``NO_STING_OPEN``) are the surface Step 2 would
retune if a dimension looks imbalanced. The foam path is untouched.

No printing or argparse in the pure functions — the CLI at the bottom composes
them, mirroring ``tools/probe_lib.py`` / ``tools/tier_engine_health_probe.py``.

Usage:
    python tools/ruleset_balance_probe.py [--seeds 16] [--seasons 2] [--clubs 6]
        [--health-trials 150] [--stability-matches 500]
        [--ruleset official_cloth|official_no_sting|both]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass, replace as dc_replace
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "tools"))

from dodgeball_sim.engine_driver import EngineDriver  # noqa: E402
from dodgeball_sim.models import (  # noqa: E402
    Approach,
    CatchPosture,
    CoachPolicy,
    OpeningRushCommit,
    OpeningRushTarget,
    TargetFocus,
)
from dodgeball_sim.official_engine import OfficialMatchEngineDriver  # noqa: E402

from probe_lib import make_match_input, run_ovr_curve  # noqa: E402

# Reuse the parity sweep + the shared seed set so the cloth/no-sting parity
# numbers are directly comparable to the foam gate's recorded run.
from archetype_champion_parity_probe import (  # noqa: E402
    ParityResult,
    default_seed_set,
    run_parity_sweep,
)

# The four displayed core skills (the five-skill mean OVR the sheet shows). The
# V17 liability gate checks accuracy + dodge; power + catch are reported too so
# a retune that inverts a different skill is visible. stamina / tactical_iq /
# catch_courage / throw_selection_iq / conditioning_curve are the identity /
# engine-consumer skills, not the displayed "core" sheet — they stay out of the
# liability verdict (they have their own V19a consumer gates).
DISPLAYED_CORE_SKILLS: tuple[str, ...] = ("accuracy", "power", "dodge", "catch")

# The V17 liability threshold: a skill is flagged a liability if a +12 bump
# sits more than 5pp BELOW the even-strength baseline. This mirrors
# ``test_v17_no_displayed_core_skill_is_a_liability``'s dodge margin; the gate
# itself is Step 2's call, this is the measurement signal.
LIABILITY_MARGIN = 0.05

ATTR_BUMP = 12.0
BASE_RATING = 63.0

# OVR-curve rungs (net per-player edge -> net six-player OVR edge). Matches the
# health probe so the slope number is comparable across rulesets.
HEALTH_RUNGS: tuple[int, ...] = (0, 4, 8, 12)

# A spread of policies to exercise the stability sweep across the whole coach
# policy surface, not just the default — the to_official_event crash was
# officiating-discretion path-dependent, so varied policies flush it out.
_STABILITY_POLICIES: tuple[CoachPolicy, ...] = (
    CoachPolicy(),
    CoachPolicy(approach=Approach.AGGRESSIVE),
    CoachPolicy(approach=Approach.PATIENT),
    CoachPolicy(catch_posture=CatchPosture.GO_FOR_CATCHES),
    CoachPolicy(catch_posture=CatchPosture.PLAY_SAFE),
    CoachPolicy(target_focus=TargetFocus.THEIR_STARS),
    CoachPolicy(rush_commit=OpeningRushCommit.ALL_IN),
    CoachPolicy(rush_target=OpeningRushTarget.CENTER),
)


@dataclass(frozen=True)
class HealthResult:
    """OVR-curve slope + per-displayed-core-skill win-rate verdict."""

    ruleset: str
    trials_per_rung: int
    ovr_slope_pp: float              # (top rung win rate - bottom rung win rate) * 100
    top_floor: float                 # win rate at the top rung (favorite +72 net OVR)
    baseline_win_rate: float         # even-strength, no bump
    attr_win_rates: dict[str, float]  # displayed core skill -> win rate at +12
    liability_skills: tuple[str, ...]  # skills whose +12 sits > LIABILITY_MARGIN below baseline


@dataclass(frozen=True)
class StabilityResult:
    """Zero-crash regression guard across a broad seeded match sweep."""

    ruleset: str
    matches_attempted: int
    matches_run: int
    crashes: int
    crash_samples: tuple[str, ...]  # up to N (type, message, seed) strings for the report


@dataclass(frozen=True)
class RulesetBalanceReport:
    """The three measurements for one ruleset, composed for the CLI report."""

    ruleset: str
    parity: ParityResult
    health: HealthResult
    stability: StabilityResult


# ---------------------------------------------------------------------------
# Driver construction (pure)
# ---------------------------------------------------------------------------

def _build_driver(ruleset: str) -> EngineDriver:
    """Build the shipping multi-set official driver under the given ruleset.

    Foam path is untouched — ``OfficialMatchEngineDriver(ruleset=...)`` is the
    same constructor the foam probe uses with its default argument.
    """
    return OfficialMatchEngineDriver(ruleset=ruleset)


# ---------------------------------------------------------------------------
# Parity (pure: delegates to the existing sweep)
# ---------------------------------------------------------------------------

def measure_parity(
    ruleset: str,
    *,
    seeds: tuple[int, ...],
    seasons: int,
    clubs: int,
) -> ParityResult:
    """Run the matched-OVR shape-varied champion sweep under `ruleset`."""
    return run_parity_sweep(
        seeds=seeds,
        seasons=seasons,
        n_clubs=clubs,
        ruleset_selection=ruleset,
    )


# ---------------------------------------------------------------------------
# Health (pure: OVR slope + no-liability)
# ---------------------------------------------------------------------------

def _attr_win_rate(driver: EngineDriver, attr: str | None, *, trials: int, seed_base: int) -> float:
    """Win rate for the favorite at even strength, optionally with a +12 bump.

    Mirrors ``tests/test_official_engine_balance.py::_v17_attr_win_rate`` so the
    cloth/no-sting numbers are directly comparable to the foam gate's recorded
    baseline (35.5%) / accuracy (54.2%) / dodge (39.2%) / catch (62.7%) / power
    (48.2%).
    """
    wins = 0
    for trial in range(trials):
        seed = seed_base + trial
        mi = make_match_input(seed=seed, rating_a=BASE_RATING, rating_b=BASE_RATING)
        if attr is not None:
            lookup = dict(mi.player_lookup)
            for pid in mi.starters_a:
                player = lookup[pid]
                bumped = dc_replace(
                    player.ratings, **{attr: int(BASE_RATING + ATTR_BUMP)}
                )
                lookup[pid] = dc_replace(player, ratings=bumped)
            mi = dc_replace(mi, player_lookup=lookup)
        if driver.run(mi).winner_team_id == "fav":
            wins += 1
    return wins / trials if trials else 0.0


def measure_health(ruleset: str, *, trials_per_rung: int, attr_trials: int) -> HealthResult:
    """OVR-curve slope + displayed-core-skill liability check under `ruleset`.

    `trials_per_rung` drives the OVR curve; `attr_trials` drives the per-skill
    bump conditions (kept separate so a tight OVR curve and a wider attr sample
    can be tuned independently, as the V17 gate does).
    """
    driver = _build_driver(ruleset)

    curve = run_ovr_curve(
        driver, rungs=HEALTH_RUNGS, trials_per_rung=trials_per_rung
    )
    rates = [r.win_rate for r in curve]
    ovr_slope_pp = (rates[-1] - rates[0]) * 100.0
    top_floor = rates[-1]

    # Even-strength baseline + per-skill bumps live on a disjoint seed block so
    # they never overlap the OVR-curve seeds (mirror the V17 gate's _SEED_BASE).
    baseline = _attr_win_rate(driver, None, trials=attr_trials, seed_base=64_000_000)
    attr_rates: dict[str, float] = {}
    liabilities: list[str] = []
    for index, attr in enumerate(DISPLAYED_CORE_SKILLS):
        rate = _attr_win_rate(
            driver, attr, trials=attr_trials, seed_base=65_000_000 + index * 1_000_000
        )
        attr_rates[attr] = rate
        if rate < baseline - LIABILITY_MARGIN:
            liabilities.append(attr)

    return HealthResult(
        ruleset=ruleset,
        trials_per_rung=trials_per_rung,
        ovr_slope_pp=ovr_slope_pp,
        top_floor=top_floor,
        baseline_win_rate=baseline,
        attr_win_rates=attr_rates,
        liability_skills=tuple(liabilities),
    )


# ---------------------------------------------------------------------------
# Stability (pure: zero-crash sweep)
# ---------------------------------------------------------------------------

def measure_stability(
    ruleset: str,
    *,
    matches: int,
    seed_base: int,
    crash_sample_limit: int = 8,
) -> StabilityResult:
    """Run `matches` seeded matches under `ruleset` with varied ratings + policies.

    Asserts zero crashes/exceptions — the V17 ``to_official_event``
    officiating-discretion regression guard. Returns the count and a few sample
    failure strings (empty on a clean sweep).
    """
    driver = _build_driver(ruleset)
    crashes = 0
    samples: list[str] = []
    # Vary the favorite edge so the sweep exercises both even and lopsided
    # rosters (the crash was at the officiating-discretion boundary, which
    # edge-sensitive games reach more often).
    edges = (0.0, 6.0, 12.0, 24.0)
    policies = _STABILITY_POLICIES
    run = 0
    for i in range(matches):
        seed = seed_base + i
        edge = edges[i % len(edges)]
        policy = policies[i % len(policies)]
        mi = make_match_input(
            seed=seed,
            rating_a=BASE_RATING + edge,
            rating_b=BASE_RATING,
            policy_a=policy,
            match_id_prefix="stab",
        )
        try:
            driver.run(mi)
            run += 1
        except Exception as exc:  # noqa: BLE001 - measurement harness: count everything
            crashes += 1
            if len(samples) < crash_sample_limit:
                samples.append(f"seed={seed} edge={edge} policy={policy.approach.value}/{policy.catch_posture.value}: {type(exc).__name__}: {exc}")
    return StabilityResult(
        ruleset=ruleset,
        matches_attempted=matches,
        matches_run=run,
        crashes=crashes,
        crash_samples=tuple(samples),
    )


# ---------------------------------------------------------------------------
# Composition (pure)
# ---------------------------------------------------------------------------

def run_ruleset_balance(
    ruleset: str,
    *,
    seeds: tuple[int, ...],
    seasons: int,
    clubs: int,
    health_trials_per_rung: int,
    health_attr_trials: int,
    stability_matches: int,
    stability_seed_base: int = 96_000_000,
) -> RulesetBalanceReport:
    """Compose the parity + health + stability measurements for one ruleset."""
    parity = measure_parity(
        ruleset, seeds=seeds, seasons=seasons, clubs=clubs
    )
    health = measure_health(
        ruleset,
        trials_per_rung=health_trials_per_rung,
        attr_trials=health_attr_trials,
    )
    stability = measure_stability(
        ruleset, matches=stability_matches, seed_base=stability_seed_base
    )
    return RulesetBalanceReport(ruleset=ruleset, parity=parity, health=health, stability=stability)


# ---------------------------------------------------------------------------
# CLI (composition + printing only)
# ---------------------------------------------------------------------------

def _format_parity(report: RulesetBalanceReport) -> list[str]:
    p = report.parity
    lines = [
        f"--- Parity ({report.ruleset}) ---",
        f"  seeds={len(p.seeds)}  clubs={p.clubs}  seasons/seed={p.seasons_per_seed}  "
        f"total titles={p.total_titles}",
        "  Champion-archetype distribution:",
    ]
    for archetype, n in p.distribution.items():
        share = 100.0 * n / p.total_titles if p.total_titles else 0.0
        lines.append(f"    {archetype:<22} {n:>4}  ({share:5.1f}%)")
    lines.append(
        f"  distinct champion archetypes: {p.distinct_champion_archetypes}   "
        f"max: {p.max_archetype} = {p.max_share * 100:.1f}%   "
        f"(Wilson95 upper {p.wilson95_upper:.3f})"
    )
    return lines


def _format_health(report: RulesetBalanceReport) -> list[str]:
    h = report.health
    lines = [
        f"--- Health ({report.ruleset}) ---",
        f"  OVR curve: slope {h.ovr_slope_pp:+.1f}pp over rungs {HEALTH_RUNGS} "
        f"({h.trials_per_rung} trials/rung); top floor {h.top_floor * 100:.1f}%",
        f"  Even-strength baseline: {h.baseline_win_rate * 100:.1f}%",
        "  Displayed core skill value (+12 bump win rate):",
    ]
    for attr in DISPLAYED_CORE_SKILLS:
        rate = h.attr_win_rates[attr]
        delta_pp = (rate - h.baseline_win_rate) * 100.0
        flag = ""
        if attr in h.liability_skills:
            flag = "  <-- LIABILITY (sits > 5pp below baseline)"
        lines.append(f"    {attr:<10} {rate * 100:5.1f}%  (delta {delta_pp:+5.1f}pp vs baseline){flag}")
    if h.liability_skills:
        lines.append(f"  liability skills: {', '.join(h.liability_skills)}")
    else:
        lines.append("  liability skills: none")
    return lines


def _format_stability(report: RulesetBalanceReport) -> list[str]:
    s = report.stability
    lines = [
        f"--- Stability ({report.ruleset}) ---",
        f"  matches attempted: {s.matches_attempted}   run: {s.matches_run}   "
        f"crashes: {s.crashes}",
    ]
    if s.crashes:
        lines.append("  crash samples:")
        for sample in s.crash_samples:
            lines.append(f"    - {sample}")
    return lines


def format_report(report: RulesetBalanceReport) -> str:
    lines = [f"=== Ruleset Balance — {report.ruleset} ==="]
    lines.extend(_format_parity(report))
    lines.extend(_format_health(report))
    lines.extend(_format_stability(report))
    return "\n".join(lines)


RULESET_CHOICES = ("official_cloth", "official_no_sting")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="V27 Phase 3 Step 1 — cloth/no-sting balance measurement harness"
    )
    ap.add_argument("--seeds", type=int, default=16, help="Parity sweep seeds (default 16, the foam gate config)")
    ap.add_argument("--seasons", type=int, default=2, help="Parity seasons per seed (default 2)")
    ap.add_argument("--clubs", type=int, default=6, help="Parity league clubs (default 6)")
    ap.add_argument("--health-trials", type=int, default=150, help="OVR-curve trials per rung (default 150)")
    ap.add_argument("--attr-trials", type=int, default=150, help="Per-skill bump trials (default 150)")
    ap.add_argument("--stability-matches", type=int, default=500, help="Stability sweep matches (default 500)")
    ap.add_argument(
        "--ruleset",
        choices=("both",) + RULESET_CHOICES,
        default="both",
        help="Ruleset to measure (default both)",
    )
    args = ap.parse_args()

    rulesets = RULESET_CHOICES if args.ruleset == "both" else (args.ruleset,)
    seeds = default_seed_set(count=args.seeds)
    for ruleset in rulesets:
        report = run_ruleset_balance(
            ruleset,
            seeds=seeds,
            seasons=args.seasons,
            clubs=args.clubs,
            health_trials_per_rung=args.health_trials,
            health_attr_trials=args.attr_trials,
            stability_matches=args.stability_matches,
        )
        print(format_report(report))
        print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
