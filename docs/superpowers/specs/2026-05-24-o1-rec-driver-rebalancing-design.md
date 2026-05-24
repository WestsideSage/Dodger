# O1 — Rec Driver Rebalancing (Design)

Date: 2026-05-24
Status: Design, awaiting plan
Predecessors: Plan D (`2026-05-22-plan-d-simulation-health-probe-design.md`) installed the probe and the strict-xfail gate. This spec consumes both.

## Relation to Prior Specs

- **Plan D** installed `tools/tier_engine_health_probe.py`, `tools/probe_lib.py`, and `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke` (xfail-strict on the O1 baseline). This spec is the rebalancing pass that flips that gate green and graduates the assertion to a hard regression test.
- **Plan A** (`docs/specs/2026-05-20-post-v11-redesign-brief/plan-a-hybrid-driver.md`) introduced `RecTier1Driver`. Its `_resolve_throw` is the primary surface this spec mutates.
- **Plan B** (`plan-b-player-attribute-v2.md`) is the source of `catch_courage`, `throw_selection_iq`, and `conditioning_curve` — already wired but minimally exercised in the connect/catch contest math. Phase 2 may opportunistically wire them deeper.
- Original O1 write-up: `docs/archive/playthrough-bug-log.md` (lines 256–298). That write-up names `config.py` constants `accuracy_scale=12.0` / `catch_scale=11.0` as the lever — these no longer exist in `RecTier1Driver` (the engine was rewritten under Plan A). This spec supersedes that root-cause hypothesis.

## Problem

Fresh baseline (400 trials/rung, seed offset 0, current `rec_engine.py` on `main` at HEAD):

| Net OVR | Fav win % | 95% CI         |
|---------|-----------|----------------|
| +0      | 40.5%     | 35.8 – 45.4    |
| +24     | 48.5%     | 43.6 – 53.4    |
| +48     | 51.2%     | 46.4 – 56.1    |
| +72     | 54.0%     | 49.1 – 58.8    |

The slope (+13.5pp) and monotonicity assertions in `test_ovr_curve_rec_driver_smoke` pass; the **top-floor (≥60% at +72)** fails. Two separate problems:

1. **0-edge asymmetry (~10pp).** In symmetric matches (rating-63 vs rating-63) the "fav" team wins only 40.5%, not the expected ~45–50% (allowing for draws). This is structural — same RNG, same ratings, same policies. Some part of the runtime favors team B.
2. **Shallow slope.** Even after the asymmetry is removed, the per-rung lift (~4–5pp per +24 net OVR) is too flat. The throw-resolution contest is linear, and a 5% rating-independent headshot floor drains both sides equally.

## Calibration Methodology (locked)

There is no published rec-league dodgeball dataset to calibrate against. The methodology, not the number, is the deliverable.

- **Target band at +72 net OVR: 72 – 78% favorite win rate.** Center 75%. Justified by the Elo win-probability analogy `1 / (1 + 10^(-Δ/400))` under conventional skill-rating mappings (1 OVR ≈ 8–12 Elo), cross-checked against NFL/NBA/chess/ATP heavy-favorite empirics for comparable rating gaps.
- **Moment-event constraint.** In favorite losses, ≥80% must contain at least one moment event (`comeback`, `dramatic_catch`, `gassed_collapse`, `late_game_escape`, or `one_v_one_finale`). This operationalizes "no braindead upsets" — a loss explained by a dramatic moment is real; a loss with no moment is engine noise.
- **Variance ceiling.** At 1,000 trials per rung, the +72 win-rate 95% CI width must be ≤ 6pp. Without this, the calibrated number is not measurable.
- **Smoke gate vs calibration target.** The pytest smoke test (400 trials/rung) asserts the **lower bound** of the band (≥72%) so it does not flake against Monte-Carlo noise at smoke size. The 1,000-trial CLI run is the calibration check (75% ± 3pp).

This spec accepts that ongoing tuning will continue past the first green run — the gate's job is to lock the floor, not to declare the engine "done."

## Approach (three phases)

### Phase 1 — Diagnose and fix the 0-edge asymmetry

Cheap and high-leverage. If symmetric matches are ~45–50% fav-wins instead of 40.5%, every rung rises ~5–10pp and the +72 floor likely clears with no formula change at all. Until this is fixed, any throw-resolution tuning is calibrating on a biased baseline.

**Work:**

1. Add a temporary probe mode (CLI flag or one-off script under `tools/`) that runs the 0-edge rung at 2,000 trials and logs, per match: which team won, match length, who threw first, who held the ball at the terminal tick, draw cause if any. Do not commit the temporary probe — it is investigative.
2. Identify the asymmetry source. Most likely candidates, in order:
   - Turn order in the tick loop (team A always evaluated first).
   - `_select_throwers` / `_select_target_state` iteration order over `mi.starters_a` vs `mi.starters_b`.
   - Recent-target memory (`recent_targets_by_team`) initialized differently for fav vs dog.
   - Draw resolution at match end favoring team B.
3. Fix in place. The fix may be as small as a stable shuffle of evaluation order seeded off `mi.seed`, or a symmetric tie-break in target selection.
4. Re-baseline at 400 trials/rung. Symmetric 0-edge must land in [45%, 55%] before Phase 2 begins.

**Exit criterion:** 0-edge fav win rate ∈ [45%, 55%] at 1,000 trials, 95% CI width ≤ 4pp.

### Phase 2 — Skill sensitivity in throw resolution

Mutate `RecTier1Driver._resolve_throw` ([rec_engine.py:527](src/dodgeball_sim/rec_engine.py:527)). Two levers, applied one at a time with probe re-runs between each change.

**Lever 2A — Contest function for connect.** Replace `connect_prob = accuracy * (1 - dodge)` (line 620) with a contest-style function. The two candidates, in order of preference:

- *Logistic contest:* `connect_prob = accuracy / (accuracy + (1 - dodge))`. Stays in (0, 1), is symmetric, and a +12-per-player edge moves probability ~7pp instead of ~4.5pp.
- *Exponent on the linear form:* `connect_prob = (accuracy * (1 - dodge)) ** γ` with γ ≈ 0.7. Sharper at the high end; less symmetric.

Phase 2A starts with the logistic contest. If post-tuning slope is still short, escalate to exponent or compose them.

**Lever 2B — Skill-modulate the rating-independent noise.** The flat 5% headshot self-out ([rec_engine.py:600](src/dodgeball_sim/rec_engine.py:600)) caps how much skill can dominate. Replace the flat `0.05` with `0.08 - 0.05 * (thrower.ratings.throw_selection_iq / 100.0)` (clamps to ~0.03 for elite, ~0.08 for raw). This wires a Plan B attribute that is currently under-exercised, and the lever is honest — high throw_selection_iq players should not headshot themselves.

Re-run the 400-trial probe after each lever. After 2A alone, after 2B alone, after both together. Pick the smallest combination that lands the calibration band.

**Exit criterion:** at 1,000 trials, +72 fav win rate ∈ [72%, 78%], 95% CI width ≤ 6pp, AND ≥80% of fav losses contain at least one moment event. Match-length P50 must remain in [40, 70] events (current 53) — a fix that ends matches in 20 events has broken the moment-event drama.

### Phase 3 — Strip the xfail, regenerate goldens, document

1. Tighten `tests/test_engine_health.py::test_ovr_curve_rec_driver_smoke`:
   - Top-floor assertion: `rates[-1] >= 0.72` (band lower bound).
   - Min-slope assertion: keep at +10pp.
   - Monotonicity: keep with 2pp tolerance.
   - Remove the `@pytest.mark.xfail(strict=True)` marker.
2. Add a second test `test_fav_losses_explained_by_moments`: at smoke size, ≥75% of fav losses at the +72 rung contain at least one moment event. (75% smoke, 80% CLI — same flake-margin pattern.)
3. Regenerate any rec-driver golden logs broken by the formula change. Per AGENTS.md ("If match outcomes intentionally change, update golden logs and document why"), commit the golden regeneration in the same change as the formula tune.
4. Update `docs/STATUS.md`: move O1 out of "Open Work And Known Gaps" into "Shipped And Verified" with the new calibration numbers, methodology link, and a one-line note that further tuning will continue past the green gate.

## Out of Scope

- **OfficialDriver rebalancing.** Plan D's probe runs against `rec` only; the official driver is not on this critical path. Re-baseline it separately after Phase 3.
- **Player attribute reshaping.** `throw_selection_iq` is used by Phase 2B but no new attributes are added.
- **Moment-event tuning.** If Phase 2's exit criterion forces moment rates to move (e.g. `one_v_one_finale` currently fires in only 3% of matches), file a follow-up but do not chase it inside this spec.
- **Frontend, voice modules, save format.** Untouched.
- **AI Program Managers re-slot, Broadcast layer.** Separate next-milestone work.

## Risks

- **Phase 1 yields nothing.** If the 0-edge asymmetry has no single cause (e.g. it's a fair statistical fluke at 400 trials and disappears at 2,000), Phase 2 absorbs the full lift required to clear 72%. The exponent lever 2A-alt exists as the escape hatch.
- **Logistic contest over-rewards skill.** A +72 edge could overshoot to 85%+, killing variance. Mitigated by tuning order (logistic first, headshot floor second) and the 1,000-trial calibration check between levers.
- **Golden-log regeneration churn.** Phase 3 will likely touch every rec-driver golden. Plan A's golden logs are the canonical baseline; checking which goldens are rec-vs-official before Phase 3 is part of the implementation plan, not this design.
- **Moment-event drama collapse.** Faster matches (Phase 2A makes connects more likely) compress fatigue and reduce gassed_collapse / late_game_escape rates. The P50 match-length floor of 40 events catches this; if Phase 2 hits the band but match length drops below 40, back off and re-tune.

## Acceptance Criteria

1. `python -m pytest tests/test_engine_health.py -q` is green with the xfail removed.
2. `python tools/tier_engine_health_probe.py --trials 1000 --driver rec` reports +72 fav win rate in [72%, 78%], 95% CI width ≤ 6pp, monotonic, ≥80% of fav losses with a moment event.
3. Full `python -m pytest -q` is green (golden logs regenerated as part of the same change).
4. `docs/STATUS.md` reflects O1 closure and links this spec.
