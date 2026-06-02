"""WT-23 — archetype champion-distribution gate.

This is the safety net for the WT-25 recruiting-tier flip. It does NOT claim the
archetypes are balanced ("parity"); it is a **diversity / degeneracy guard** on
the champion-archetype distribution of a deterministic, seeded league sweep.

What it asserts (the two task-mandated checks):
  1. >= 3 DISTINCT program archetypes win the championship across the sweep.
  2. No single archetype wins more than a CAP measured from the real run.

The league swept is a matched-mean-OVR, skill-SHAPE-varied league (see
``tools/archetype_champion_parity_probe`` for the full rationale). Archetypes are
DERIVED by the real ``classify_club_archetype`` — never assigned — which is the
bright line versus the V12 ``scratch/sweep_archetypes.py`` cheat that manually
``UPDATE``-d fictional archetypes onto clubs (and is why STATUS's "50-season
parity sweep" was unreproducible: the stock curated league only ever derives
~2 archetypes).

RECORDED RUN (the source of N and the cap — re-derive both if you change them):
  config: default_seed_set(count=16), seasons=2, clubs=6, ruleset=official_foam
  -> 32 total titles, 3 distinct champion archetypes,
     {Defensive Specialist: 22 (68.8%), Balanced Rebuild: 8 (25.0%),
      Power Throwers: 2 (6.2%)}, Wilson-95 upper on the max = 0.820.
  CAP = 0.85 (Wilson-95 upper rounded up; a degeneracy ceiling, NOT a parity
  claim). The cap is tied to THIS config — 16x3 already pushes Wilson to 0.851.

Runtime ~8-10s; this is a standing gate (fast enough), and the CLI defaults to a
larger nightly N. Headline finding (ADR 0002): matched OVR != matched strength —
every shipping engine rewards defense over offense, so the Defensive Specialist
shape leads even at equal OVR. The probe's job is to show the league still
produces >= 3 distinct champions under the ceiling, not that the shapes are equal.
"""

from __future__ import annotations

import functools

import pytest

from tools.archetype_champion_parity_probe import (
    default_seed_set,
    run_one_career,
    run_parity_sweep,
)

# --- Gate config (locked; see the module docstring before changing) ----------
GATE_SEED_COUNT = 16
GATE_SEASONS = 2
GATE_CLUBS = 6
GATE_RULESET = "official_foam"

# CAP = Wilson-95 upper bound on the dominant archetype's share at the recorded
# 16x2 run (0.820), rounded up to 0.85. It is a degeneracy ceiling: 0.688 passes
# with ~16pp of headroom (benign drift will not trip it), but a near-monopoly
# (e.g. a balance change that collapses the league to one champion shape) fails.
MAX_ARCHETYPE_SHARE_CAP = 0.85

MIN_DISTINCT_CHAMPION_ARCHETYPES = 3


@functools.lru_cache(maxsize=1)
def _gate_sweep():
    # The full sweep is ~8-10s; cache it so the threshold/consistency tests share
    # one run instead of re-simulating per test. Deterministic, so caching is safe.
    return run_parity_sweep(
        seeds=default_seed_set(count=GATE_SEED_COUNT),
        seasons=GATE_SEASONS,
        n_clubs=GATE_CLUBS,
        ruleset_selection=GATE_RULESET,
    )


@pytest.fixture(scope="module")
def gate_result():
    return _gate_sweep()


def test_at_least_three_distinct_champion_archetypes(gate_result):
    # Task assertion (a): the league must not collapse to <= 2 champion
    # archetypes. Trips only if the rarest shape (Power Throwers) wins zero
    # titles — i.e. a real change that makes offense unable to ever win a
    # championship at matched OVR.
    assert gate_result.distinct_champion_archetypes >= MIN_DISTINCT_CHAMPION_ARCHETYPES, (
        f"Champion-archetype diversity collapsed below "
        f"{MIN_DISTINCT_CHAMPION_ARCHETYPES}: {gate_result.distribution}"
    )


def test_no_archetype_exceeds_measured_cap(gate_result):
    # Task assertion (b): no single archetype monopolizes the title beyond the
    # measured ceiling. ~16pp of headroom over the recorded 68.8%.
    assert gate_result.max_share <= MAX_ARCHETYPE_SHARE_CAP, (
        f"{gate_result.max_archetype} won {gate_result.max_share * 100:.1f}% of titles, "
        f"over the {MAX_ARCHETYPE_SHARE_CAP * 100:.0f}% degeneracy cap "
        f"(measured at this config); distribution={gate_result.distribution}"
    )


def test_sweep_totals_are_consistent(gate_result):
    # The distribution must actually sum to the title count, and every season of
    # every seed must have produced exactly one champion (no dropped/duplicated
    # titles from a bracket bug).
    assert sum(gate_result.distribution.values()) == gate_result.total_titles
    assert gate_result.total_titles == GATE_SEED_COUNT * GATE_SEASONS


def test_sweep_is_deterministic(gate_result):
    # The whole point of a seeded gate: the same seed set reproduces the same
    # champion-archetype distribution. If this ever fails, an unseeded RNG leaked
    # into the season/playoff/offseason path and the gate's numbers are unsafe.
    # Deliberately bypass the cache for a genuine second run.
    rerun = run_parity_sweep(
        seeds=default_seed_set(count=GATE_SEED_COUNT),
        seasons=GATE_SEASONS,
        n_clubs=GATE_CLUBS,
        ruleset_selection=GATE_RULESET,
    )
    assert rerun.distribution == gate_result.distribution


def test_single_career_is_reproducible():
    # Per-seed determinism (cheaper than the full sweep): one career run twice
    # yields the identical champion sequence.
    champ_a, init_a = run_one_career(
        root_seed=20260000, n_clubs=GATE_CLUBS, seasons=GATE_SEASONS,
        ruleset_selection=GATE_RULESET,
    )
    champ_b, init_b = run_one_career(
        root_seed=20260000, n_clubs=GATE_CLUBS, seasons=GATE_SEASONS,
        ruleset_selection=GATE_RULESET,
    )
    assert champ_a == champ_b
    assert init_a == init_b


def test_league_derives_three_shape_archetypes_at_matched_ovr():
    # Faithfulness guard: the league's three archetypes are EARNED by the real
    # classify_club_archetype on matched-OVR rosters, not assigned. This is the
    # line between this probe and the V12 manual-UPDATE cheat. Confirm (1) the
    # init population spans exactly the three SHAPE archetypes, and (2) no
    # strength-defined archetype (Contender/Aging Veterans/Development Factory)
    # leaks in — which would mean the rosters drifted off matched strength.
    _champs, init_archetypes = run_one_career(
        root_seed=20260000, n_clubs=GATE_CLUBS, seasons=1,
        ruleset_selection=GATE_RULESET,
    )
    derived = set(init_archetypes.values())
    assert derived == {"Power Throwers", "Defensive Specialist", "Balanced Rebuild"}, derived
