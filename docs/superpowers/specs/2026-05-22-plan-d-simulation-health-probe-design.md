# Plan D — Simulation-Health Probe (design)

Date: 2026-05-22
Status: Design approved; implementation plan next.
Parent roadmap: [tier-1-roadmap.md](../../specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md)
Predecessors: Plan A, Plan B, Plan C (all landed 2026-05-20 / 2026-05-22).

---

## Goal

Replace `tools/o1_variance_probe.py` with a broader, gating health probe that defends the OVR→win-rate curve as the primary engine-balance regression signal, and that also reports moment-occurrence rates, match-length distribution, and outcome distribution as diagnostic context. Plan D ships measurement only; the actual O1 rebalancing pass is a follow-up.

## Background

The 2026-05-15 product-coherence audit (`docs/archive/playthrough-bug-log.md`, O1 section) found that a +72 net-OVR favorite wins only ~52% of matches in the rec driver. The `tools/o1_variance_probe.py` is a 52-line read-only Monte Carlo that surfaces this finding. Plan A added `tools/tier_1_sanity_probe.py` (110 lines) to gate the six-moment contract. Plan D unifies and extends these into one diagnostic CLI plus one CI gate.

## Pinned design decisions

1. **Primary metric:** OVR→favorite-win-rate curve. Three rules: monotonicity (with ±2pp tolerance for binomial noise at smoke size), minimum slope (`wr[+72] − wr[+0] ≥ 10pp`), and top-rung floor (`wr[+72] ≥ 60%`).
2. **Drivers:** `RecTier1Driver` is gated. `OfficialDriver` is reported-only — the CLI emits its curve when `--driver official` or `--driver both` is passed, but pytest does not assert on it. This boundary holds until USAD-specific tuning lands.
3. **Sample sizes:** smoke 100 trials/rung (pytest gate), full 400 trials/rung (CLI default). The CLI accepts `--trials N` to override.
4. **OVR rungs:** four fixed rungs — per-player edges of `(0, 4, 8, 12)`, giving net edges of `(0, 24, 48, 72)`. Favorite rating = `base_rating + per_player_edge`; dog rating = `base_rating` (default 63.0).
5. **Seeding:** `seed = rung_index * 10_000 + trial_index + seed_offset`. Guarantees no cross-rung collision; smoke and full overlap exactly on the first 100 trials of each rung.
6. **Gate state at landing:** the pytest test is `@pytest.mark.xfail(strict=True)` with a reason citing the O1 ticket. The strict flag means the suite fails the moment a future O1 fix flips the test green, forcing whoever lands the fix to remove the xfail marker and graduate the test to a hard gate.
7. **Refactor scope:** Plan D extracts a shared `tools/probe_lib.py` and refactors `tools/tier_1_sanity_probe.py` to consume it. The sanity probe's external behavior is unchanged.
8. **Deletion:** `tools/o1_variance_probe.py` is deleted in Phase 2 — it is fully subsumed by the new health probe's OVR-curve section.

## Architecture

Three new files, one refactor, one deletion.

**Created:**
- `tools/probe_lib.py` — shared pure-function helpers. Public API:
  - `make_player(pid, club, rating) -> Player`
  - `make_team(team_id, rating, size=6) -> tuple[str, ...]` (returns starter IDs; players live in the lookup dict)
  - `make_match_input(seed, *, rating_a=63.0, rating_b=63.0, policy_a=None, policy_b=None, match_id_prefix="probe") -> DriverMatchInput`
  - `RungResult` dataclass: `net_ovr_edge`, `trials`, `fav_wins`, `win_rate`, `ci_low`, `ci_high`, `outputs`
  - `wilson_ci(successes, trials, z=1.96) -> (low, high)`
  - `run_ovr_curve(driver, *, rungs=(0,4,8,12), trials_per_rung=400, base_rating=63.0, seed_offset=0) -> tuple[RungResult, ...]`
  - `summarize_moments(results) -> dict[str, dict[str, float]]` — keys: moment kind values; sub-keys: `per_match`, `pct_matches_with`, `total`
  - `summarize_match_lengths(results) -> dict[str, int]` — keys: `p25`, `p50`, `p75`, `p95`
  - `summarize_outcomes(results) -> dict[str, int]` — keys: `fav`, `dog`, `draw`, `fav_pct`, `dog_pct`, `draw_pct`
  - No I/O; no `print`; no `argparse`. Caller composes.

- `tools/tier_engine_health_probe.py` — CLI. Argparse:
  - `--trials N` (default 400)
  - `--driver {rec,official,both}` (default `rec`)
  - `--seed-offset N` (default 0; for reproducible re-runs)
  - Prints four sections: OVR curve (with Wilson 95% CIs, pass/fail per rule), moment-occurrence rates, match-length distribution, outcome distribution.
  - Exit code 0 unless a probe-level exception fires.

- `tests/test_engine_health.py` — one xfail-strict test, `test_ovr_curve_rec_driver_smoke`. Runs `run_ovr_curve(RecTier1Driver(), trials_per_rung=100)`. Asserts the three rules from pinned decision §1.

**Refactored:**
- `tools/tier_1_sanity_probe.py` — replaces its inline `_make_player` / `_make_input` with `probe_lib.make_match_input`. Output stays bytes-identical so the existing manual workflow (and any operator muscle memory) is preserved.

**Deleted:**
- `tools/o1_variance_probe.py`.

## CLI output shape

```
=== OVR → Favorite Win Rate (rec, 400 trials/rung) ===
  Net +  0 OVR:  50.2% [95% CI 45.3 – 55.1]
  Net +24 OVR:  51.8% [95% CI 46.9 – 56.6]
  Net +48 OVR:  53.5% [95% CI 48.6 – 58.3]
  Net +72 OVR:  54.8% [95% CI 49.9 – 59.6]
  Monotonicity: PASS   Min slope: FAIL (+4.6pp, need +10pp)   Top floor: FAIL (54.8% < 60%)

=== Moment Occurrence ===
                       per-match    matches-with    total
  dramatic_catch          1.04        72%           1664
  late_game_escape        0.56        41%            896
  one_v_one_finale        0.08         8%            128
  gassed_collapse         0.96        65%           1536
  flood_throw             4.32        93%           6912
  comeback                1.80        88%           2880

=== Match Length (ticks) ===
  P25: 142   P50: 198   P75: 261   P95: 372

=== Outcomes (across all rungs) ===
  Team A:  812 (50.8%)   Team B:  773 (48.3%)   Draw:  15 (0.9%)
```

When `--driver both`, the four sections are printed twice (once per driver) under a `=== rec ===` / `=== official ===` divider.

## Phase plan

### Phase 1 — `probe_lib` + sanity-probe refactor

- Write `tools/probe_lib.py` with the API above. Pure functions, fully unit-testable.
- Refactor `tools/tier_1_sanity_probe.py` to import `make_match_input`. Behavior unchanged; line count drops to ~60.
- Add `tests/test_probe_lib.py`: `make_team` builds 6 players at the requested rating; `make_match_input` produces a valid `DriverMatchInput`; `wilson_ci(50, 100)` matches the textbook value within 1e-3; `run_ovr_curve` with `trials_per_rung=2` returns 4 `RungResult`s in seed-deterministic order; `summarize_moments` / `summarize_match_lengths` / `summarize_outcomes` round-trip a fixture.

**Gate:** `pytest -q` green. `python tools/tier_1_sanity_probe.py` exits 0 with all six moment kinds emitting.

### Phase 2 — Health probe CLI + O1 deletion

- Write `tools/tier_engine_health_probe.py` per the CLI shape above. Argparse, then `run_ovr_curve` + three `summarize_*` calls + four formatted print sections.
- `--driver official` builds an `OfficialDriver` and runs the curve. If `OfficialDriver` does not accept the same `DriverMatchInput` shape, document the deferral inline in the CLI (`OfficialDriver curve deferred — see Plan D §architecture`) and ship rec-only.
- `--driver both` prints both sections sequentially.
- Verify `DriverMatchOutput` exposes the field used for `summarize_match_lengths`. The design assumes one of `end_tick`, `final_tick`, or `len(events)`; pick the truthful one at implementation time and document the choice in `probe_lib`.
- Delete `tools/o1_variance_probe.py`.

**Gate:** `python tools/tier_engine_health_probe.py --trials 50` runs cleanly under 10 seconds. `pytest -q` still green.

### Phase 3 — Pytest health gate + docs

- Write `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke`:
  ```python
  @pytest.mark.xfail(strict=True, reason="O1 baseline — see docs/archive/playthrough-bug-log.md")
  def test_ovr_curve_rec_driver_smoke():
      results = run_ovr_curve(RecTier1Driver(), trials_per_rung=100, seed_offset=0)
      rates = [r.win_rate for r in results]
      # Monotonicity with 2pp tolerance for binomial noise at smoke size
      for prev, curr in zip(rates, rates[1:]):
          assert curr >= prev - 0.02
      # Minimum slope: top rung at least 10pp above the baseline
      assert rates[-1] - rates[0] >= 0.10
      # Top-rung floor
      assert rates[-1] >= 0.60
  ```
- Update `docs/STATUS.md`: move the O1 entry from "Open Work And Known Gaps" into a "Now measured by `tools/tier_engine_health_probe.py`; pytest gate is xfail-strict until the rebalancing pass lands" framing. Add Plan D to "Shipped And Verified."
- Update `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md`: mark Plan D row landed; declare the Tier 1 Match Loop milestone complete.

**Gate:** `pytest -q` green (xfail counts as expected-fail, suite passes). `python tools/tier_engine_health_probe.py` prints the four sections. `python tools/tier_1_sanity_probe.py` six-out-of-six. `npm run build` and `npm run lint` clean (no frontend touches, but the milestone-close gate runs them anyway).

## Risks and mitigations

- **Binomial noise at smoke size:** 100 trials at a 0.60 true rate has a ±10pp 95% CI. A borderline-passing engine could flake green. Because Plan D ships with the gate xfail-strict on the current (failing) engine, flake direction is "test passes when it shouldn't" not "test fails when it shouldn't." When the O1 fix lands and the gate flips green, the implementer should bump `trials_per_rung` to 200 if flakes appear.
- **Match-length attribute may not exist on `DriverMatchOutput`:** verify in Phase 2; fall back to `len(output.events)` if needed; document the chosen field in `probe_lib`.
- **`OfficialDriver` may not accept the same `DriverMatchInput`:** `--driver official` is reported-only, so a Phase 2 deferral is acceptable. Document explicitly in CLI output and in `probe_lib`'s module docstring.
- **Plan D measuring while O1 is unfixed could look like a regression on landing:** the xfail-strict pattern is exactly what makes this safe — the test is expected to fail today and will graduate when the fix lands.

## Definition of done

- `tools/probe_lib.py` exists with full unit-test coverage.
- `tools/tier_engine_health_probe.py` prints all four sections for `rec`. `official` works or is documented as Phase 2 deferral.
- `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke` is xfail-strict and ready to flip green when O1 is fixed.
- `tools/o1_variance_probe.py` is deleted.
- `tools/tier_1_sanity_probe.py` consumes `probe_lib`; behavior unchanged.
- `docs/STATUS.md` reflects Plan D landed and reframes O1.
- `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md` marks Plan D landed and declares the Tier 1 Match Loop milestone complete.
- Full pytest green. Sanity probe six-out-of-six.

## Out of scope

- The actual O1 rebalancing pass (a follow-up plan).
- USAD-specific tuning of `OfficialDriver`'s OVR curve.
- Adding new moment kinds, new tactics, or new policies.
- Any frontend work.
- Performance optimization of `RecTier1Driver` (smoke runs 400 matches; if that's slow, profile in a follow-up).
