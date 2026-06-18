"""V27 Phase 3 Step 2 — per-ruleset balance gates (cloth + no-sting).

This is the cloth/no-sting mirror of the foam gate
(``tests/test_archetype_champion_parity.py`` + the V17 liability gates in
``tests/test_official_engine_balance.py``). It locks the three dimensions
Step 1 measured (``tools/ruleset_balance_probe.py``) so a future balance
regression trips loudly instead of shipping silently into the V27 ruleset
invitationals.

WHAT IT ASSERTS (per ruleset, both ``official_cloth`` and ``official_no_sting``):
  1. Parity: >= 3 distinct champion archetypes AND no single archetype's
     share exceeds a CAP derived from that ruleset's measured Wilson-95 upper
     bound, rounded up for modest headroom — exactly how the foam gate set
     0.85 from its recorded 0.820.
  2. Health: the OVR curve has positive slope (favorite win rate rises with
     net OVR edge) AND no displayed core skill (accuracy/power/dodge/catch)
     is a liability (a +12 bump never sits materially below the even-strength
     baseline) — the V17 catch-economy retune's invariant, extended onto the
     cloth/no-sting profiles.
  3. Stability: a broad seeded match sweep under the ruleset crashes zero
     times — the V17 ``to_official_event`` officiating-discretion regression
     guard (a cloth crash, since fixed).

This is a CHARACTERIZATION gate: it pins the current good behavior measured
in Step 1's recorded run. It is green on commit by construction; the "red" is
a FUTURE balance regression (a retune that collapses the league to one
champion shape, inverts a displayed skill into a liability, or reintroduces
the officiating-discretion crash) tripping it. When that happens, re-measure
with ``tools/ruleset_balance_probe.py`` and update the cap + recorded run
AFTER fixing the regression — do not just bump the cap to make it green.

RECORDED STEP-1 RUN (the source of N and every cap — re-derive all before
changing them; the full nightly config is the probe CLI
``tools/ruleset_balance_probe.py --seeds 16 --seasons 2 --clubs 6
--health-trials 150 --attr-trials 150 --stability-matches 500``):

  official_cloth (16 seeds x 2 seasons x 6 clubs, 150 health trials/rung,
  150 attr trials, 500 stability matches):
    Parity: 3 distinct champions; distribution
      {Power Throwers 17 (53.1%), Balanced Rebuild 13 (40.6%),
       Defensive Specialist 2 (6.2%)};
      max_share 0.531, Wilson-95 upper 0.691.
    Health: OVR slope +55.3pp (top floor 99.3%); even baseline 45.3%;
      +12 accuracy 69.3%, power 80.0%, dodge 62.7%, catch 86.7%;
      liability skills: none.
    Stability: 500/500 matches, 0 crashes.
    -> CAP = 0.72 (Wilson-95 upper 0.691 rounded up; ~3pp of headroom over
       the recorded 53.1% max share — benign drift will not trip it, but a
       near-monopoly from a balance change fails).

  official_no_sting (same config):
    Parity: 3 distinct champions; distribution
      {Balanced Rebuild 15 (46.9%), Power Throwers 13 (40.6%),
       Defensive Specialist 4 (12.5%)};
      max_share 0.469, Wilson-95 upper 0.636.
    Health: OVR slope +56.7pp (top floor 99.3%); even baseline 44.7%;
      +12 accuracy 72.0%, power 80.0%, dodge 70.7%, catch 85.3%;
      liability skills: none.
    Stability: 500/500 matches, 0 crashes.
    -> CAP = 0.68 (Wilson-95 upper 0.636 rounded up; ~21pp of headroom over
       the recorded 46.9% max share).

GATE CONFIG (suite-fast): parity pins the recorded N (count=16, seasons=2,
clubs=6) because that is the cap's basis — the same tradeoff the foam gate
makes (its CLI nightly is N=50, the gate pins N=16). Health/stability use
reduced trial counts for the standing test (the caps come from the recorded
full run, NOT the gate's reduced run — a regression big enough to trip the
gate trips at the reduced N too; the full nightly config is the probe CLI).
Runtime target: a few seconds per ruleset.

No retune: Step 1 found no imbalance, so ``rulesets.CLOTH_OPEN`` /
``NO_STING_OPEN`` and every balance constant are untouched. This gate pins
the current good behavior; it does not change it.
"""

from __future__ import annotations

import functools

import pytest

from tools.archetype_champion_parity_probe import default_seed_set
from tools.ruleset_balance_probe import run_ruleset_balance

# --- Gate config (locked; see the module docstring before changing) ----------
GATE_SEED_COUNT = 16
GATE_SEASONS = 2
GATE_CLUBS = 6

# Health/stability reduced trial counts for the standing test. The caps come
# from the recorded full run (probe CLI: 150/150/500); a regression large
# enough to flip the verdict at the full run also flips it here.
GATE_HEALTH_TRIALS_PER_RUNG = 60
GATE_ATTR_TRIALS = 60
GATE_STABILITY_MATCHES = 120

# Caps derived from each ruleset's recorded Step-1 Wilson-95 upper bound,
# rounded up for modest headroom (foam: 0.820 -> 0.85). See the recorded run
# in the module docstring for the derivation.
CLOTH_MAX_SHARE_CAP = 0.72       # recorded Wilson-95 upper 0.691, max share 0.531
NO_STING_MAX_SHARE_CAP = 0.68    # recorded Wilson-95 upper 0.636, max share 0.469

MIN_DISTINCT_CHAMPION_ARCHETYPES = 3

_CAPS = {
    "official_cloth": CLOTH_MAX_SHARE_CAP,
    "official_no_sting": NO_STING_MAX_SHARE_CAP,
}


@functools.lru_cache(maxsize=1)
def _gate_reports():
    # Both ruleset sweeps are cached together so the threshold/consistency
    # tests share the runs instead of re-simulating per test. Deterministic,
    # so caching is safe (mirrors the foam gate's _gate_sweep pattern).
    seeds = default_seed_set(count=GATE_SEED_COUNT)
    reports = {}
    for ruleset in ("official_cloth", "official_no_sting"):
        reports[ruleset] = run_ruleset_balance(
            ruleset,
            seeds=seeds,
            seasons=GATE_SEASONS,
            clubs=GATE_CLUBS,
            health_trials_per_rung=GATE_HEALTH_TRIALS_PER_RUNG,
            health_attr_trials=GATE_ATTR_TRIALS,
            stability_matches=GATE_STABILITY_MATCHES,
        )
    return reports


@pytest.fixture(scope="module")
def reports():
    return _gate_reports()


@pytest.fixture(scope="module")
def cloth_report(reports):
    return reports["official_cloth"]


@pytest.fixture(scope="module")
def no_sting_report(reports):
    return reports["official_no_sting"]


# --- Parity gates ------------------------------------------------------------

@pytest.mark.parametrize(
    "ruleset, fixture_name",
    [("official_cloth", "cloth_report"), ("official_no_sting", "no_sting_report")],
)
def test_at_least_three_distinct_champion_archetypes(request, ruleset, fixture_name):
    report = request.getfixturevalue(fixture_name)
    assert report.parity.distinct_champion_archetypes >= MIN_DISTINCT_CHAMPION_ARCHETYPES, (
        f"{ruleset}: champion-archetype diversity collapsed below "
        f"{MIN_DISTINCT_CHAMPION_ARCHETYPES}: {report.parity.distribution}"
    )


@pytest.mark.parametrize(
    "ruleset, fixture_name",
    [("official_cloth", "cloth_report"), ("official_no_sting", "no_sting_report")],
)
def test_no_archetype_exceeds_measured_cap(request, ruleset, fixture_name):
    report = request.getfixturevalue(fixture_name)
    cap = _CAPS[ruleset]
    assert report.parity.max_share <= cap, (
        f"{ruleset}: {report.parity.max_archetype} won "
        f"{report.parity.max_share * 100:.1f}% of titles, over the {cap * 100:.0f}% "
        f"degeneracy cap (measured at the recorded run); "
        f"distribution={report.parity.distribution}"
    )


@pytest.mark.parametrize(
    "ruleset, fixture_name",
    [("official_cloth", "cloth_report"), ("official_no_sting", "no_sting_report")],
)
def test_parity_sweep_totals_are_consistent(request, ruleset, fixture_name):
    report = request.getfixturevalue(fixture_name)
    assert sum(report.parity.distribution.values()) == report.parity.total_titles
    assert report.parity.total_titles == GATE_SEED_COUNT * GATE_SEASONS


# --- Health gates ------------------------------------------------------------

@pytest.mark.parametrize(
    "ruleset, fixture_name",
    [("official_cloth", "cloth_report"), ("official_no_sting", "no_sting_report")],
)
def test_ovr_curve_has_positive_slope(request, ruleset, fixture_name):
    report = request.getfixturevalue(fixture_name)
    assert report.health.ovr_slope_pp > 0, (
        f"{ruleset}: OVR curve slope is {report.health.ovr_slope_pp:+.1f}pp — "
        "the favorite no longer wins more as net OVR rises (the engine stopped "
        "rewarding roster strength). See the V17 health probe precedent."
    )


@pytest.mark.parametrize(
    "ruleset, fixture_name",
    [("official_cloth", "cloth_report"), ("official_no_sting", "no_sting_report")],
)
def test_no_displayed_core_skill_is_a_liability(request, ruleset, fixture_name):
    report = request.getfixturevalue(fixture_name)
    assert report.health.liability_skills == (), (
        f"{ruleset}: displayed core skill(s) {report.health.liability_skills} "
        f"sit materially below the even-strength baseline "
        f"({report.health.baseline_win_rate * 100:.1f}%) — the catch economy "
        "has regressed toward throw-EV-negative (see 2026-06-09 audit §3.4 / "
        "the V17 liability gate)."
    )


# --- Stability gate ----------------------------------------------------------

@pytest.mark.parametrize(
    "ruleset, fixture_name",
    [("official_cloth", "cloth_report"), ("official_no_sting", "no_sting_report")],
)
def test_stability_sweep_zero_crashes(request, ruleset, fixture_name):
    report = request.getfixturevalue(fixture_name)
    assert report.stability.crashes == 0, (
        f"{ruleset}: {report.stability.crashes} crash(es) in "
        f"{report.stability.matches_attempted} matches — the V17 "
        "to_official_event officiating-discretion regression returned. "
        f"Samples: {report.stability.crash_samples}"
    )
    assert report.stability.matches_run == report.stability.matches_attempted


# --- Determinism gate (the point of a seeded gate) ---------------------------

@pytest.mark.parametrize("ruleset", ["official_cloth", "official_no_sting"])
def test_sweep_is_deterministic(ruleset):
    # Same seeds -> same champion-archetype distribution. If this ever fails,
    # an unseeded RNG leaked into the season/playoff/offseason path and the
    # gate's numbers are unsafe. Deliberately bypass the cache for a genuine
    # second run (parity-only is enough; health/stability determinism is
    # inherited from the seeded driver and probe_lib).
    seeds = default_seed_set(count=GATE_SEED_COUNT)
    first = run_ruleset_balance(
        ruleset,
        seeds=seeds,
        seasons=GATE_SEASONS,
        clubs=GATE_CLUBS,
        health_trials_per_rung=GATE_HEALTH_TRIALS_PER_RUNG,
        health_attr_trials=GATE_ATTR_TRIALS,
        stability_matches=GATE_STABILITY_MATCHES,
    )
    second = run_ruleset_balance(
        ruleset,
        seeds=seeds,
        seasons=GATE_SEASONS,
        clubs=GATE_CLUBS,
        health_trials_per_rung=GATE_HEALTH_TRIALS_PER_RUNG,
        health_attr_trials=GATE_ATTR_TRIALS,
        stability_matches=GATE_STABILITY_MATCHES,
    )
    assert first.parity.distribution == second.parity.distribution
    assert first.health.ovr_slope_pp == second.health.ovr_slope_pp
    assert first.stability.crashes == second.stability.crashes
