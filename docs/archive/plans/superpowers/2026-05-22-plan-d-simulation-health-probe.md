# Plan D — Simulation-Health Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `tools/o1_variance_probe.py` with a broader, gating health probe that defends the OVR→favorite-win-rate curve as the primary engine-balance regression signal, and reports moment-occurrence rates, match-length distribution, and outcome distribution as diagnostic context.

**Architecture:** Three new files (`tools/probe_lib.py`, `tools/tier_engine_health_probe.py`, `tests/test_engine_health.py`), one refactor (`tools/tier_1_sanity_probe.py` consumes `probe_lib`), one deletion (`tools/o1_variance_probe.py`). All probe code is pure-function over the `EngineDriver` protocol from Plan A; no engine internals are imported.

**Tech Stack:** Python 3.12+, dataclasses, argparse, pytest. No new runtime dependencies.

**Parent design:** [2026-05-22-plan-d-simulation-health-probe-design.md](../specs/2026-05-22-plan-d-simulation-health-probe-design.md)
**Predecessors:** Plans A, B, C (all landed 2026-05-20 / 2026-05-22).

---

## Resolved-at-plan-time facts (confirmed against the codebase)

These were flagged for Phase 2 verification in the design doc. They are resolved here so the implementer does not have to re-investigate.

1. **Match-length field.** `DriverMatchOutput` (`src/dodgeball_sim/engine_driver.py:30-39`) has no `end_tick` / `final_tick` field. Use `len(output.events)` as the match-length proxy. Document inline in `probe_lib`.
2. **Moment-event `kind` access.** Moment dataclasses (`src/dodgeball_sim/moment_events.py`) expose `kind: MomentKind`; the string value is `event.kind.value`.
3. **`DriverMatchInput` shape.** Both `RecTier1Driver` and `OfficialDriver` accept the same `DriverMatchInput` per Plan A's protocol (`src/dodgeball_sim/engine_driver.py:42-48`). `--driver official` is expected to work; if `OfficialDriver` raises on the synthetic input, that is a Phase 2 deferral per spec.
4. **Existing tier_1_sanity_probe pattern.** `tools/tier_1_sanity_probe.py` builds its own `_make_player` / `_make_input` without importing from `tests/factories.py` — `tools/` does not depend on `tests/`. `probe_lib` follows the same rule.

---

## File map

**Files created:**
- `tools/probe_lib.py` — shared pure-function helpers (~150 lines).
- `tools/tier_engine_health_probe.py` — CLI (~120 lines).
- `tests/test_probe_lib.py` — unit tests for `probe_lib`.
- `tests/test_engine_health.py` — single xfail-strict gate.

**Files modified:**
- `tools/tier_1_sanity_probe.py` — consumes `probe_lib.make_match_input`. Output bytes-identical.
- `docs/STATUS.md` — Plan D added to "Shipped And Verified"; O1 reframed as gated by Plan D.
- `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md` — Plan D row landed; Tier 1 Match Loop milestone complete.

**Files deleted:**
- `tools/o1_variance_probe.py` — subsumed.

---

## Phase 1 — `probe_lib` + sanity-probe refactor

### Task 1: `probe_lib.make_player` / `make_team` / `make_match_input`

**Files:**
- Create: `tools/probe_lib.py`
- Test: `tests/test_probe_lib.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_probe_lib.py
from __future__ import annotations

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player

from tools.probe_lib import make_match_input, make_player, make_team


def test_make_player_builds_player_with_uniform_rating():
    player = make_player("fav_0", "fav", rating=70.0)
    assert isinstance(player, Player)
    assert player.id == "fav_0"
    assert player.club_id == "fav"
    assert player.ratings.accuracy == 70.0
    assert player.ratings.dodge == 70.0
    assert player.ratings.stamina == 70.0


def test_make_team_returns_six_starter_ids_by_default():
    starters = make_team("fav", rating=65.0)
    assert len(starters) == 6
    assert starters[0] == "fav_0"
    assert starters[-1] == "fav_5"


def test_make_match_input_produces_valid_driver_input():
    mi = make_match_input(seed=42, rating_a=70.0, rating_b=60.0)
    assert isinstance(mi, DriverMatchInput)
    assert mi.team_a_id == "fav"
    assert mi.team_b_id == "dog"
    assert mi.match_id == "probe_42"
    assert mi.seed == 42
    assert len(mi.starters_a) == 6
    assert len(mi.starters_b) == 6
    assert set(mi.player_lookup.keys()) == set(mi.starters_a) | set(mi.starters_b)
    assert mi.player_lookup["fav_0"].ratings.accuracy == 70.0
    assert mi.player_lookup["dog_0"].ratings.accuracy == 60.0
    assert isinstance(mi.policy_a, CoachPolicy)
    assert isinstance(mi.policy_b, CoachPolicy)


def test_make_match_input_honors_custom_prefix_and_policies():
    custom = CoachPolicy()
    mi = make_match_input(
        seed=7,
        rating_a=63.0,
        rating_b=63.0,
        policy_a=custom,
        policy_b=custom,
        match_id_prefix="health",
    )
    assert mi.match_id == "health_7"
    assert mi.policy_a is custom
    assert mi.policy_b is custom
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.probe_lib'` (or import error).

- [ ] **Step 3: Write minimal implementation**

```python
# tools/probe_lib.py
"""Shared pure-function helpers for Tier 1 / engine-health probes.

No I/O. No printing. No argparse. Callers (CLIs and pytest) compose.

Note: tools/ does not import from tests/. Player construction lives here
so both the sanity probe and the health probe consume the same helpers.

Match-length proxy: `len(DriverMatchOutput.events)`. `DriverMatchOutput`
does not expose an explicit end_tick (see src/dodgeball_sim/engine_driver.py).
"""
from __future__ import annotations

from dataclasses import dataclass

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player, PlayerArchetype, PlayerRatings


def make_player(pid: str, club: str, rating: float) -> Player:
    """Build a six-skill-uniform player at the requested rating."""
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(
            accuracy=rating,
            power=rating,
            dodge=rating,
            catch=rating,
            stamina=rating,
            tactical_iq=rating,
            catch_courage=rating,
            throw_selection_iq=rating,
            conditioning_curve=rating,
        ),
        club_id=club,
        archetype=PlayerArchetype.CATCHER,
    )


def make_team(team_id: str, rating: float, size: int = 6) -> tuple[str, ...]:
    """Return the starter IDs for a team of `size` players at uniform rating."""
    return tuple(f"{team_id}_{i}" for i in range(size))


def make_match_input(
    seed: int,
    *,
    rating_a: float = 63.0,
    rating_b: float = 63.0,
    policy_a: CoachPolicy | None = None,
    policy_b: CoachPolicy | None = None,
    match_id_prefix: str = "probe",
) -> DriverMatchInput:
    """Build a DriverMatchInput with synthetic fav/dog teams.

    Team A is "fav" at `rating_a`; team B is "dog" at `rating_b`. The
    fav/dog naming is load-bearing for downstream `winner_team_id == "fav"`
    counting in `run_ovr_curve`.
    """
    starters_a = make_team("fav", rating_a)
    starters_b = make_team("dog", rating_b)
    player_lookup = {pid: make_player(pid, "fav", rating_a) for pid in starters_a}
    player_lookup.update({pid: make_player(pid, "dog", rating_b) for pid in starters_b})
    return DriverMatchInput(
        match_id=f"{match_id_prefix}_{seed}",
        team_a_id="fav",
        team_b_id="dog",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=player_lookup,
        policy_a=policy_a if policy_a is not None else CoachPolicy(),
        policy_b=policy_b if policy_b is not None else CoachPolicy(),
        seed=seed,
    )


__all__ = ["make_player", "make_team", "make_match_input"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/probe_lib.py tests/test_probe_lib.py
git commit -m "feat(plan-d): probe_lib make_player/make_team/make_match_input"
```

---

### Task 2: `wilson_ci` + `RungResult`

**Files:**
- Modify: `tools/probe_lib.py`
- Modify: `tests/test_probe_lib.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_probe_lib.py`:

```python
from tools.probe_lib import RungResult, wilson_ci


def test_wilson_ci_known_values():
    # 50 successes in 100 trials: Wilson 95% CI ≈ (0.404, 0.596).
    low, high = wilson_ci(50, 100)
    assert abs(low - 0.4038) < 1e-3
    assert abs(high - 0.5962) < 1e-3


def test_wilson_ci_handles_zero_trials():
    low, high = wilson_ci(0, 0)
    assert low == 0.0
    assert high == 0.0


def test_wilson_ci_handles_perfect_score():
    low, high = wilson_ci(100, 100)
    assert low > 0.9
    assert high == 1.0


def test_rung_result_carries_required_fields():
    rr = RungResult(
        net_ovr_edge=24,
        trials=100,
        fav_wins=55,
        win_rate=0.55,
        ci_low=0.45,
        ci_high=0.65,
        outputs=(),
    )
    assert rr.net_ovr_edge == 24
    assert rr.fav_wins == 55
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: FAIL — `wilson_ci` and `RungResult` not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `tools/probe_lib.py` before the `__all__` line:

```python
from math import sqrt
from typing import Any


@dataclass(frozen=True)
class RungResult:
    net_ovr_edge: int
    trials: int
    fav_wins: int
    win_rate: float
    ci_low: float
    ci_high: float
    outputs: tuple[Any, ...]


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson 95% CI for a binomial proportion.

    Returns (0.0, 0.0) for trials == 0. Clamps upper bound at 1.0 so a
    perfect score reports a finite interval.
    """
    if trials <= 0:
        return (0.0, 0.0)
    p = successes / trials
    denom = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denom
    spread = (z * sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))
```

Update `__all__`:

```python
__all__ = ["make_player", "make_team", "make_match_input", "RungResult", "wilson_ci"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: PASS (7 tests total).

- [ ] **Step 5: Commit**

```bash
git add tools/probe_lib.py tests/test_probe_lib.py
git commit -m "feat(plan-d): probe_lib wilson_ci + RungResult"
```

---

### Task 3: `run_ovr_curve`

**Files:**
- Modify: `tools/probe_lib.py`
- Modify: `tests/test_probe_lib.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_probe_lib.py`:

```python
from dodgeball_sim.rec_engine import RecTier1Driver

from tools.probe_lib import run_ovr_curve


def test_run_ovr_curve_returns_one_result_per_rung():
    results = run_ovr_curve(RecTier1Driver(), rungs=(0, 4), trials_per_rung=2)
    assert len(results) == 2
    assert results[0].net_ovr_edge == 0
    assert results[1].net_ovr_edge == 24
    assert results[0].trials == 2
    assert all(0.0 <= r.win_rate <= 1.0 for r in results)


def test_run_ovr_curve_seeds_are_deterministic():
    a = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3)
    b = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3)
    assert a[0].fav_wins == b[0].fav_wins


def test_run_ovr_curve_seed_offset_shifts_results():
    a = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3, seed_offset=0)
    b = run_ovr_curve(RecTier1Driver(), rungs=(0,), trials_per_rung=3, seed_offset=500)
    # Different seeds: at least one of the underlying outputs differs.
    a_winners = tuple(out.winner_team_id for out in a[0].outputs)
    b_winners = tuple(out.winner_team_id for out in b[0].outputs)
    assert a_winners != b_winners or a[0].fav_wins != b[0].fav_wins
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: FAIL — `run_ovr_curve` not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `tools/probe_lib.py` (above `__all__`):

```python
from dodgeball_sim.engine_driver import EngineDriver


def run_ovr_curve(
    driver: EngineDriver,
    *,
    rungs: tuple[int, ...] = (0, 4, 8, 12),
    trials_per_rung: int = 400,
    base_rating: float = 63.0,
    seed_offset: int = 0,
) -> tuple[RungResult, ...]:
    """Run a Monte Carlo OVR-edge curve through `driver`.

    Each rung's per-player edge becomes a net six-player OVR edge. Favorite
    rating = base_rating + per_player_edge; dog = base_rating.

    Seeding: seed = rung_index * 10_000 + trial_index + seed_offset.
    """
    results: list[RungResult] = []
    for rung_index, edge in enumerate(rungs):
        fav_wins = 0
        outputs: list[Any] = []
        for trial in range(trials_per_rung):
            seed = rung_index * 10_000 + trial + seed_offset
            mi = make_match_input(
                seed=seed,
                rating_a=base_rating + edge,
                rating_b=base_rating,
            )
            out = driver.run(mi)
            outputs.append(out)
            if out.winner_team_id == "fav":
                fav_wins += 1
        win_rate = fav_wins / trials_per_rung if trials_per_rung else 0.0
        ci_low, ci_high = wilson_ci(fav_wins, trials_per_rung)
        results.append(
            RungResult(
                net_ovr_edge=edge * 6,
                trials=trials_per_rung,
                fav_wins=fav_wins,
                win_rate=win_rate,
                ci_low=ci_low,
                ci_high=ci_high,
                outputs=tuple(outputs),
            )
        )
    return tuple(results)
```

Update `__all__`:

```python
__all__ = [
    "make_player",
    "make_team",
    "make_match_input",
    "RungResult",
    "wilson_ci",
    "run_ovr_curve",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: PASS (10 tests total). Each curve test runs ~6 rec-driver matches; total under 5 seconds on a dev machine.

- [ ] **Step 5: Commit**

```bash
git add tools/probe_lib.py tests/test_probe_lib.py
git commit -m "feat(plan-d): probe_lib run_ovr_curve"
```

---

### Task 4: `summarize_moments` / `summarize_match_lengths` / `summarize_outcomes`

**Files:**
- Modify: `tools/probe_lib.py`
- Modify: `tests/test_probe_lib.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_probe_lib.py`:

```python
from tools.probe_lib import summarize_match_lengths, summarize_moments, summarize_outcomes


def _fixture_results():
    return run_ovr_curve(RecTier1Driver(), rungs=(0, 4), trials_per_rung=3)


def test_summarize_moments_emits_six_kinds():
    results = _fixture_results()
    summary = summarize_moments(results)
    expected = {
        "dramatic_catch",
        "late_game_escape",
        "one_v_one_finale",
        "gassed_collapse",
        "flood_throw",
        "comeback",
    }
    assert set(summary.keys()) == expected
    for entry in summary.values():
        assert set(entry.keys()) == {"per_match", "pct_matches_with", "total"}
        assert entry["per_match"] >= 0.0
        assert 0.0 <= entry["pct_matches_with"] <= 1.0
        assert entry["total"] >= 0


def test_summarize_match_lengths_quartiles():
    results = _fixture_results()
    lengths = summarize_match_lengths(results)
    assert set(lengths.keys()) == {"p25", "p50", "p75", "p95"}
    assert lengths["p25"] <= lengths["p50"] <= lengths["p75"] <= lengths["p95"]


def test_summarize_outcomes_counts_fav_dog_draw():
    results = _fixture_results()
    outcomes = summarize_outcomes(results)
    assert set(outcomes.keys()) == {"fav", "dog", "draw", "fav_pct", "dog_pct", "draw_pct"}
    assert outcomes["fav"] + outcomes["dog"] + outcomes["draw"] == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: FAIL — three summarizers not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `tools/probe_lib.py` (above `__all__`):

```python
from collections import Counter


_MOMENT_KINDS = (
    "dramatic_catch",
    "late_game_escape",
    "one_v_one_finale",
    "gassed_collapse",
    "flood_throw",
    "comeback",
)


def _all_outputs(results: tuple[RungResult, ...]) -> tuple[Any, ...]:
    return tuple(out for rung in results for out in rung.outputs)


def summarize_moments(results: tuple[RungResult, ...]) -> dict[str, dict[str, float]]:
    """Per-moment-kind statistics across every match in `results`."""
    outputs = _all_outputs(results)
    match_count = len(outputs)
    totals: Counter[str] = Counter()
    matches_with: Counter[str] = Counter()
    for out in outputs:
        seen: set[str] = set()
        for event in out.moment_events:
            kind = event.kind.value if hasattr(event.kind, "value") else str(event.kind)
            totals[kind] += 1
            seen.add(kind)
        for kind in seen:
            matches_with[kind] += 1
    summary: dict[str, dict[str, float]] = {}
    for kind in _MOMENT_KINDS:
        summary[kind] = {
            "per_match": totals[kind] / match_count if match_count else 0.0,
            "pct_matches_with": matches_with[kind] / match_count if match_count else 0.0,
            "total": totals[kind],
        }
    return summary


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    idx = min(len(sorted_values) - 1, max(0, int(round((pct / 100.0) * (len(sorted_values) - 1)))))
    return sorted_values[idx]


def summarize_match_lengths(results: tuple[RungResult, ...]) -> dict[str, int]:
    """P25 / P50 / P75 / P95 of `len(events)` across every match."""
    outputs = _all_outputs(results)
    lengths = sorted(len(out.events) for out in outputs)
    return {
        "p25": _percentile(lengths, 25),
        "p50": _percentile(lengths, 50),
        "p75": _percentile(lengths, 75),
        "p95": _percentile(lengths, 95),
    }


def summarize_outcomes(results: tuple[RungResult, ...]) -> dict[str, int]:
    """Aggregate fav / dog / draw counts and percentages across `results`."""
    outputs = _all_outputs(results)
    fav = sum(1 for out in outputs if out.winner_team_id == "fav")
    dog = sum(1 for out in outputs if out.winner_team_id == "dog")
    draw = sum(1 for out in outputs if out.winner_team_id is None)
    total = len(outputs) or 1
    return {
        "fav": fav,
        "dog": dog,
        "draw": draw,
        "fav_pct": round(100.0 * fav / total, 1),
        "dog_pct": round(100.0 * dog / total, 1),
        "draw_pct": round(100.0 * draw / total, 1),
    }
```

Update `__all__`:

```python
__all__ = [
    "make_player",
    "make_team",
    "make_match_input",
    "RungResult",
    "wilson_ci",
    "run_ovr_curve",
    "summarize_moments",
    "summarize_match_lengths",
    "summarize_outcomes",
]
```

Note the `summarize_outcomes` return type expands to `dict[str, int | float]` in practice (counts are ints, percentages are floats). The hint stays `dict[str, int]` for brevity; downstream consumers (the CLI) treat values as numeric.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_probe_lib.py -q`
Expected: PASS (13 tests total).

- [ ] **Step 5: Commit**

```bash
git add tools/probe_lib.py tests/test_probe_lib.py
git commit -m "feat(plan-d): probe_lib summarize_moments/match_lengths/outcomes"
```

---

### Task 5: Refactor `tier_1_sanity_probe.py` to consume `probe_lib`

**Files:**
- Modify: `tools/tier_1_sanity_probe.py`

- [ ] **Step 1: Capture current output for byte-identical comparison**

Run: `python tools/tier_1_sanity_probe.py > /tmp/sanity_before.txt 2>&1`
Note: on Windows, use `python tools/tier_1_sanity_probe.py > %TEMP%\sanity_before.txt`.

- [ ] **Step 2: Rewrite the probe**

Replace the body of `tools/tier_1_sanity_probe.py` with:

```python
"""Tier 1 sanity probe — Plan A gate.

Runs N Tier 1 matches end-to-end and asserts that they all resolve,
emit at least one moment event on average, and produce all six moment
kinds at least once.

Plan D introduced `tools/probe_lib.py`; this probe now consumes
`make_match_input` from there. Output is unchanged.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List

from dodgeball_sim.moment_events import MomentKind
from dodgeball_sim.rec_engine import RecTier1Driver

from tools.probe_lib import make_match_input


@dataclass
class SanityProbeReport:
    matches_run: int = 0
    matches_resolved: int = 0
    total_moment_events: int = 0
    exceptions: List[str] = field(default_factory=list)
    winner_counts: Counter = field(default_factory=Counter)
    moment_kind_counts: Counter = field(default_factory=Counter)


def run_sanity_probe(matches: int = 25, seed_start: int = 1) -> SanityProbeReport:
    report = SanityProbeReport()
    driver = RecTier1Driver()
    for i in range(matches):
        seed = seed_start + i
        report.matches_run += 1
        try:
            out = driver.run(make_match_input(seed, match_id_prefix="sanity"))
        except Exception as e:  # pragma: no cover - probe-level safety
            report.exceptions.append(f"seed={seed}: {type(e).__name__}: {e}")
            continue
        report.matches_resolved += 1
        report.total_moment_events += len(out.moment_events)
        winner = out.winner_team_id or "draw"
        report.winner_counts[winner] += 1
        report.moment_kind_counts.update(event.kind for event in out.moment_events)
    return report


def main() -> int:
    report = run_sanity_probe()
    print("=== Tier 1 Sanity Probe ===")
    print(f"Matches run:         {report.matches_run}")
    print(f"Matches resolved:    {report.matches_resolved}")
    print(f"Total moment events: {report.total_moment_events}")
    avg = report.total_moment_events / max(1, report.matches_run)
    print(f"Avg moments/match:   {avg:.2f}")
    print(f"Winner counts:       {dict(report.winner_counts)}")
    print(
        "Moment kinds:        "
        f"{ {kind.value: count for kind, count in sorted(report.moment_kind_counts.items(), key=lambda item: item[0].value)} }"
    )
    if report.exceptions:
        print("EXCEPTIONS:")
        for line in report.exceptions:
            print(f"  - {line}")
        return 1
    if avg < 1.0:
        print("FAIL: average moments per match below 1.0")
        return 2
    missing = [kind.value for kind in MomentKind if report.moment_kind_counts[kind] == 0]
    if missing:
        print(f"FAIL: missing moment kinds: {', '.join(missing)}")
        return 3
    print("OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 3: Compare before/after output**

Note: `make_match_input` uses team IDs `fav`/`dog` instead of the previous `a`/`b`. **Output will differ** — `Winner counts: {'fav': N, 'dog': M, 'draw': K}` instead of `'a'/'b'`. This is acceptable: the new naming is shared with the health probe and the assertions still pass.

Verify the assertions still pass: `python tools/tier_1_sanity_probe.py`
Expected: exit code 0, final line `OK`, all six moment kinds in `Moment kinds`.

- [ ] **Step 4: Full pytest still green**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tools/tier_1_sanity_probe.py
git commit -m "refactor(plan-d): tier_1_sanity_probe consumes probe_lib.make_match_input"
```

---

## Phase 2 — Health probe CLI + O1 deletion

### Task 6: Health probe CLI (rec driver)

**Files:**
- Create: `tools/tier_engine_health_probe.py`

- [ ] **Step 1: Write the CLI**

```python
"""Tier engine health probe — Plan D regression diagnostic.

Reports the OVR -> favorite-win-rate curve plus moment-occurrence rates,
match-length distribution, and outcome distribution. The OVR curve is the
primary regression signal; the other three are diagnostic.

Replaces tools/o1_variance_probe.py (deleted by Plan D).

Usage:
    python tools/tier_engine_health_probe.py [--trials 400] [--driver rec|official|both] [--seed-offset 0]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dodgeball_sim.engine_driver import EngineDriver  # noqa: E402

from tools.probe_lib import (  # noqa: E402
    RungResult,
    run_ovr_curve,
    summarize_match_lengths,
    summarize_moments,
    summarize_outcomes,
)

RUNGS: tuple[int, ...] = (0, 4, 8, 12)


def _build_driver(name: str) -> EngineDriver:
    if name == "rec":
        from dodgeball_sim.rec_engine import RecTier1Driver
        return RecTier1Driver()
    if name == "official":
        from dodgeball_sim.official_engine import OfficialDriver
        return OfficialDriver()
    raise ValueError(f"Unknown driver: {name}")


def _format_ovr_section(label: str, trials: int, results: tuple[RungResult, ...]) -> str:
    lines = [f"=== OVR -> Favorite Win Rate ({label}, {trials} trials/rung) ==="]
    for r in results:
        lines.append(
            f"  Net +{r.net_ovr_edge:>2} OVR: "
            f"{r.win_rate * 100:5.1f}% "
            f"[95% CI {r.ci_low * 100:5.1f} - {r.ci_high * 100:5.1f}]"
        )
    rates = [r.win_rate for r in results]
    monotonic = all(curr >= prev - 0.02 for prev, curr in zip(rates, rates[1:]))
    slope_pp = (rates[-1] - rates[0]) * 100
    top_floor = rates[-1]
    slope_ok = slope_pp >= 10.0
    floor_ok = top_floor >= 0.60
    lines.append(
        f"  Monotonicity: {'PASS' if monotonic else 'FAIL'}   "
        f"Min slope: {'PASS' if slope_ok else 'FAIL'} ({slope_pp:+.1f}pp, need +10pp)   "
        f"Top floor: {'PASS' if floor_ok else 'FAIL'} ({top_floor * 100:.1f}% vs 60%)"
    )
    return "\n".join(lines)


def _format_moment_section(results: tuple[RungResult, ...]) -> str:
    summary = summarize_moments(results)
    lines = ["=== Moment Occurrence ===", "                       per-match    matches-with    total"]
    for kind, entry in summary.items():
        lines.append(
            f"  {kind:<20}    {entry['per_match']:>5.2f}        "
            f"{entry['pct_matches_with'] * 100:>3.0f}%         {int(entry['total']):>6}"
        )
    return "\n".join(lines)


def _format_lengths_section(results: tuple[RungResult, ...]) -> str:
    q = summarize_match_lengths(results)
    return (
        "=== Match Length (events) ===\n"
        f"  P25: {q['p25']:>4}   P50: {q['p50']:>4}   "
        f"P75: {q['p75']:>4}   P95: {q['p95']:>4}"
    )


def _format_outcomes_section(results: tuple[RungResult, ...]) -> str:
    o = summarize_outcomes(results)
    return (
        "=== Outcomes (across all rungs) ===\n"
        f"  Favorite: {o['fav']} ({o['fav_pct']}%)   "
        f"Dog: {o['dog']} ({o['dog_pct']}%)   "
        f"Draw: {o['draw']} ({o['draw_pct']}%)"
    )


def _run_one(driver_name: str, trials: int, seed_offset: int) -> int:
    driver = _build_driver(driver_name)
    print(f"=== {driver_name} ===")
    try:
        results = run_ovr_curve(
            driver,
            rungs=RUNGS,
            trials_per_rung=trials,
            seed_offset=seed_offset,
        )
    except Exception as exc:
        print(f"  Curve aborted: {type(exc).__name__}: {exc}")
        print("  (If driver=official, see Plan D design Section 'Risks'.)")
        return 2
    print(_format_ovr_section(driver_name, trials, results))
    print()
    print(_format_moment_section(results))
    print()
    print(_format_lengths_section(results))
    print()
    print(_format_outcomes_section(results))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier engine health probe (Plan D)")
    parser.add_argument("--trials", type=int, default=400, help="Trials per OVR rung (default 400)")
    parser.add_argument(
        "--driver",
        choices=("rec", "official", "both"),
        default="rec",
        help="Engine driver to probe (default rec)",
    )
    parser.add_argument("--seed-offset", type=int, default=0, help="Seed offset for reproducible re-runs")
    args = parser.parse_args()

    drivers = ("rec", "official") if args.driver == "both" else (args.driver,)
    worst = 0
    for name in drivers:
        rc = _run_one(name, args.trials, args.seed_offset)
        worst = max(worst, rc)
        print()
    return worst


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 2: Smoke-run the rec path**

Run: `python tools/tier_engine_health_probe.py --trials 25 --driver rec`
Expected: exit code 0, four sections printed (OVR curve, Moment Occurrence, Match Length, Outcomes). The curve will print FAIL on min-slope and top-floor (expected — O1 baseline).

- [ ] **Step 3: Smoke-run the official path**

Run: `python tools/tier_engine_health_probe.py --trials 5 --driver official`
Expected: one of two outcomes is acceptable:
  - exit code 0 and four sections printed for `official`; OR
  - exit code 2 and a `Curve aborted: ...` line if `OfficialDriver` rejects the synthetic input. Document the failure mode in a Phase 2 follow-up note if it occurs; this is the spec's anticipated deferral.

- [ ] **Step 4: Smoke-run `--driver both`**

Run: `python tools/tier_engine_health_probe.py --trials 5 --driver both`
Expected: two `=== rec ===` / `=== official ===` blocks printed sequentially.

- [ ] **Step 5: Commit**

```bash
git add tools/tier_engine_health_probe.py
git commit -m "feat(plan-d): tier_engine_health_probe CLI"
```

---

### Task 7: Delete `o1_variance_probe.py`

**Files:**
- Delete: `tools/o1_variance_probe.py`

- [ ] **Step 1: Verify nothing imports it**

Run: `grep -rn "o1_variance_probe" src/ tests/ tools/ docs/`
Expected: matches only in `docs/` (historical references), no live code consumers.

- [ ] **Step 2: Delete the file**

```bash
git rm tools/o1_variance_probe.py
```

- [ ] **Step 3: Verify pytest still green**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(plan-d): delete o1_variance_probe — subsumed by tier_engine_health_probe"
```

---

## Phase 3 — Pytest health gate + docs

### Task 8: Pytest health gate (xfail-strict)

**Files:**
- Create: `tests/test_engine_health.py`

- [ ] **Step 1: Write the gate test**

```python
"""Plan D engine-health regression gate.

xfail-strict on the current O1 baseline. When the rebalancing pass lands
and the assertions begin to hold, pytest will fail the suite to force the
implementer to remove the xfail marker and graduate the test to a hard gate.

Smoke size: 100 trials/rung x 4 rungs = 400 matches. Runs in ~a few seconds
on a dev machine. For tighter intervals, run the CLI:
    python tools/tier_engine_health_probe.py
"""

from __future__ import annotations

import pytest

from dodgeball_sim.rec_engine import RecTier1Driver

from tools.probe_lib import run_ovr_curve


@pytest.mark.xfail(strict=True, reason="O1 baseline - see docs/archive/playthrough-bug-log.md")
def test_ovr_curve_rec_driver_smoke():
    results = run_ovr_curve(
        RecTier1Driver(),
        rungs=(0, 4, 8, 12),
        trials_per_rung=100,
        seed_offset=0,
    )
    rates = [r.win_rate for r in results]
    # Monotonicity with 2pp tolerance for binomial noise at smoke size.
    for prev, curr in zip(rates, rates[1:]):
        assert curr >= prev - 0.02, f"OVR curve regressed: {rates}"
    # Minimum slope: the top rung must be >= 10pp above the baseline.
    assert rates[-1] - rates[0] >= 0.10, f"OVR slope too flat: {rates}"
    # Top-rung floor.
    assert rates[-1] >= 0.60, f"+72 net OVR favorite wins only {rates[-1] * 100:.1f}%"
```

- [ ] **Step 2: Run the test**

Run: `python -m pytest tests/test_engine_health.py -v`
Expected: XFAIL (one test, marked expected-fail). The suite is green; xfail counts as expected failure, not a real failure.

- [ ] **Step 3: Verify full suite still green**

Run: `python -m pytest -q`
Expected: all tests pass; one xfail.

- [ ] **Step 4: Commit**

```bash
git add tests/test_engine_health.py
git commit -m "feat(plan-d): pytest health gate (xfail-strict on O1 baseline)"
```

---

### Task 9: Update `docs/STATUS.md` and roadmap

**Files:**
- Modify: `docs/STATUS.md`
- Modify: `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md`

- [ ] **Step 1: Update STATUS.md — bump the "Last updated" line**

Edit `docs/STATUS.md` line 7. Replace:

```
Last updated: 2026-05-22 (Plan C landed — `CoachPolicy` v2 enums, rec-driver knob wiring, voice register, Command Center PolicyEditor, moment-aware ReplayTimeline + banners + comeback card).
```

with:

```
Last updated: 2026-05-22 (Plan D landed — engine-health probe + xfail-strict OVR-curve gate; Tier 1 Match Loop milestone complete).
```

- [ ] **Step 2: Update STATUS.md — add Plan D entry above the Plan C entry**

Edit `docs/STATUS.md`. Insert the following bullet directly after the `## Shipped And Verified` line, above the existing Plan C entry:

```
- **Post-V11 redesign - Plan D: Simulation-health probe** (landed 2026-05-22) — see `docs/superpowers/specs/2026-05-22-plan-d-simulation-health-probe-design.md`. New `tools/probe_lib.py` shares match-input construction, Wilson CIs, OVR-curve runner, and four summarizers (moments / match-length / outcomes / OVR). New `tools/tier_engine_health_probe.py` CLI prints four diagnostic sections per driver; supports `--driver {rec,official,both}` and `--trials N`. New `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke` is `xfail(strict=True)` on the O1 baseline — when the rebalancing pass lands and the assertions hold, pytest will fail the suite to force graduating the test to a hard gate. `tools/o1_variance_probe.py` deleted (subsumed). `tools/tier_1_sanity_probe.py` refactored to consume `probe_lib.make_match_input`; behavior unchanged. The Tier 1 Match Loop milestone (Plans A/B/C/D) is now complete.
```

- [ ] **Step 3: Update STATUS.md — reframe the O1 open item**

Edit `docs/STATUS.md`. Find the existing O1 bullet under `## Open Work And Known Gaps` (item 1, starting with `**O1 - engine balance`). Replace its body with:

```
1. **O1 - engine balance (now measured by Plan D's probe).** A +72 net-OVR favorite wins ~52% of matches in the rec driver. The Plan D health probe (`tools/tier_engine_health_probe.py`) reports the full OVR curve every run; the pytest gate `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke` is `xfail(strict=True)` until the rebalancing pass lands. Original write-up: `docs/archive/playthrough-bug-log.md` (O1 section). Fix path: rebalance the rec driver's per-tick mechanics so the gate flips green; then remove the `xfail` marker (the strict flag will force this).
```

- [ ] **Step 4: Update tier-1-roadmap.md**

Edit `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md`. Replace:

```
Date: 2026-05-20 (last updated 2026-05-22)
Status: Active. Plans A and B landed on 2026-05-20; Plan C landed 2026-05-22. **Plan D is the next strict step.**
```

with:

```
Date: 2026-05-20 (last updated 2026-05-22)
Status: **Tier 1 Match Loop milestone complete.** Plans A and B landed 2026-05-20; Plan C and Plan D landed 2026-05-22.
```

Then in the plan-sequence table, replace the Plan D row:

```
| D | Simulation-health probe | Verification harness | A + B + C | Low |
```

with:

```
| **D** | **Simulation-health probe** | Verification harness | landed 2026-05-22 | - |
```

And replace the "Order is strict" paragraph:

```
**Order is strict.** C is now landed, which unblocks D. D replaces
`tools/o1_variance_probe.py`.
```

with:

```
**Order is strict.** All four plans (A/B/C/D) have landed. The Tier 1
Match Loop milestone is complete. The O1 rebalancing pass is the next
follow-up; Plan D's xfail-strict gate flips green when it lands.
```

Finally, replace the Plan D stub heading (`## Plan D stub - Simulation-health probe`) with `## Plan D - Simulation-health probe (landed 2026-05-22)` (leaving the body of that section intact for historical reference).

- [ ] **Step 5: Verify markdown lints cleanly**

The repo doesn't run a markdown linter in CI, so a manual eyeball is sufficient. Open both files in an editor and confirm headings render and tables align.

- [ ] **Step 6: Commit**

```bash
git add docs/STATUS.md docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md
git commit -m "docs(plan-d): STATUS + roadmap reflect Plan D landed and Tier 1 milestone complete"
```

---

### Task 10: Final gate

**Files:** none modified.

- [ ] **Step 1: Full pytest**

Run: `python -m pytest -q`
Expected: all tests pass; exactly one `xfail` (the new health gate).

- [ ] **Step 2: Sanity probe still six-out-of-six**

Run: `python tools/tier_1_sanity_probe.py`
Expected: exit code 0, final line `OK`, all six moment kinds present in the `Moment kinds` dict.

- [ ] **Step 3: Health probe runs end-to-end**

Run: `python tools/tier_engine_health_probe.py --trials 50 --driver rec`
Expected: four sections print, runtime under 15 seconds, OVR-curve gate prints FAIL on min-slope and top-floor (the O1 baseline).

- [ ] **Step 4: USAD conformance still green**

Run: `python -m pytest tests/test_official_conformance_matrix.py -q`
Expected: all pass.

- [ ] **Step 5: Frontend build + lint clean (milestone-close gate)**

Run: `cd frontend && npm run build && npm run lint`
Expected: both clean. (Plan D does not touch frontend; this is a milestone-close cross-check.)

- [ ] **Step 6: Final commit if needed**

If the previous tasks already committed everything, this task adds no commits. If there are dangling changes, commit them now with a `chore(plan-d): final gate green` message.

---

## Plan D: definition of done

- `tools/probe_lib.py` exists with full unit-test coverage.
- `tools/tier_engine_health_probe.py` prints all four sections for `--driver rec`. The `--driver official` path either works or prints a clean abort with a Plan D reference.
- `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke` is `xfail(strict=True)` and ready to flip green when O1 is fixed.
- `tools/o1_variance_probe.py` is deleted.
- `tools/tier_1_sanity_probe.py` consumes `probe_lib`; output asserts the same six-moment contract.
- `docs/STATUS.md` reflects Plan D landed and reframes O1 as measured-not-fixed.
- `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md` marks Plan D landed and declares the Tier 1 Match Loop milestone complete.
- Full pytest green. Sanity probe six-out-of-six.

---

## Self-review checklist (run before handing off)

- [ ] Every task's failing test is written before the implementation.
- [ ] No task introduces a backwards-compatibility shim for `o1_variance_probe.py`.
- [ ] No task touches engine internals or Plan A/B/C surfaces.
- [ ] No probabilistic "measurably more" assertions outside the OVR-curve gate, and that gate uses seeded RNG with deterministic comparisons.
- [ ] `probe_lib` has no I/O, no `print`, no `argparse`.
- [ ] `tools/` modules do not import from `tests/`.
