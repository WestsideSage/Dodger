# Plan C — Tier 1 Player-Facing Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the V1–V11 8-float `CoachPolicy` with a 5-enum v2 model, wire the rec driver to four pre-match knobs, rewrite the voice modules and Replay UI around Plan A's six moment events using a single rec-league vocabulary register, and prove the loop end-to-end with Playwright — without breaking V11 / USAD behavior or Plan A's sanity probe.

**Architecture:** `CoachPolicy` v2 = 5 enums (Approach, TargetFocus, CatchPosture, OpeningRushCommit, OpeningRushTarget) read by `RecTier1Driver` at four decision points and by `OfficialDriver` through a semantic-intent mapping that preserves USAD tactical heuristics. Voice modules consume `AftermathContext` (match result + moment events + both teams' v2 policy + tier) and route every user-visible string through `voice_register.tier1`. Frontend gets a `PolicyEditor` in Command Center and extends `ReplayTimeline` with inline beat slots, two banners, and a comeback closing card.

**Tech Stack:** Python 3.12+, dataclasses, pytest, React 19 + TypeScript, Playwright. No new runtime dependencies.

**Parent design:** [plan-c-design.md](./plan-c-design.md)
**Predecessors:** [plan-a-hybrid-driver.md](./plan-a-hybrid-driver.md), [plan-b-design.md](./plan-b-design.md)

---

## Pinned design decisions

These resolve the remaining knobs from the design doc. Every later task references these as the source of truth.

### 1. Approach throw-eagerness delta

The rec driver applies a multiplicative bias to the `throw_selection_iq` per-tick gate:

| Approach | Gate multiplier |
|---|---|
| `AGGRESSIVE` | `0.85` (gate lowered ⇒ throw sooner) |
| `MIXED` | `1.00` (Plan A / Plan B baseline) |
| `PATIENT` | `1.20` (gate raised ⇒ hold longer) |

These are the only three numeric constants the `approach` knob introduces. They live in `rec_engine.py` as module-level `APPROACH_GATE_MULT`.

### 2. Target Focus selection weights

`_select_throwers` already picks a target. Plan C replaces the target-score formula with:

| TargetFocus | Score formula on candidate `t` |
|---|---|
| `THEIR_STARS` | `0.7 * t.overall_skill_norm + 0.3 * base_targetability(t)` |
| `BALL_HOLDERS` | `0.7 * (1.0 if t.is_holding_ball else 0.0) + 0.3 * base_targetability(t)` |
| `SPREAD` | `0.7 * (1.0 - recency_weight(t)) + 0.3 * base_targetability(t)` |

`base_targetability` is the current Plan A score (proximity / open angle). `recency_weight(t)` is `1.0` for the most-recently-thrown-at opponent, decaying by `0.5` per subsequent target, floored at `0.0`. All scores are 0..1.

### 3. Catch Posture three-way multipliers

Plan B's three-way response weights (dodge / block / catch) are multiplied per posture:

| CatchPosture | dodge mult | block mult | catch mult |
|---|---|---|---|
| `GO_FOR_CATCHES` | `0.7` | `1.0` | `1.4` |
| `PLAY_SAFE` | `1.4` | `1.0` | `0.7` |
| `OPPORTUNISTIC` | `1.0` | `1.0` | `1.0` (baseline) |

Multipliers apply *after* `catch_courage` produces the base weights, then the three weights are renormalized to sum to 1.0. Trait dominates, policy nudges (Plan C design §"Rec driver wiring").

### 4. Opening Rush — sprinter counts and ball priority

`_opening_rush` is a new method that runs once per match at tick 0. Six starters per side (brief §3.5).

| OpeningRushCommit | Sprinters | Hold-back |
|---|---|---|
| `ALL_IN` | 6 | 0 |
| `BALANCED` | 4 | 2 |
| `HOLD_BACK` | 2 | 4 |

Ball-priority ordering for sprinters:

| OpeningRushTarget | Ordering |
|---|---|
| `NEAREST` | Each sprinter targets the ball closest to their starting position. |
| `STRONGEST_SIDE` | Sprinters fan to the side of the center line with more balls (3 each side at opening — tie breaks toward the side the team is rushing from). |
| `CENTER` | Sprinters all target the center ball(s) first; secondary picks fall to nearest. |

These choices are deterministic given seeded RNG and the fixed starting positions.

### 5. USAD semantic-intent tolerance band

Phase 1's USAD regression test (`tests/test_official_tactics_policy_v2_mapping.py`) re-runs the existing `official_tactics.py` fixtures with v2 policies whose enum values are the documented mapping of the old float thresholds. Acceptance: identical *branch* taken (the same `if/elif` arm of each tactical heuristic) on every fixture. No tolerance band on numeric outputs — the migration is branch-equivalence, not numeric-equivalence. Any fixture that depended on subtle blends (e.g. `risk_tolerance=0.4` vs `0.6` producing different *magnitudes* through the same branch) gets a recorded note in the test docstring and a separate fixture row.

### 6. Verdict headline priority — full ordering

The design pinned the priority order. Tie-break when multiple moments of the same kind fire: pick the one whose `tick` is **latest** (closer to the final outcome reads as more load-bearing). When the winning team has both a `COMEBACK` and a `DRAMATIC_CATCH`, `COMEBACK` wins (already higher priority); the `DRAMATIC_CATCH` is referenced in `voice_aftermath.render_body` instead.

Priority is a module-level constant `HEADLINE_PRIORITY` in `voice_verdict.py`; the test that pins ordering iterates this constant rather than re-listing it.

### 7. Voice register key naming

Keys are lowercase, dot-separated, two-or-three segments:

- `policy.<knob>.<value>.label` — single-word UI label
- `policy.<knob>.<value>.preview` — one-line explanation under the row
- `moment.<kind>.headline` — verdict-line variant
- `moment.<kind>.body` — aftermath-paragraph variant
- `moment.<kind>.beat` — replay inline beat
- `banner.<kind>` — replay banner (LATE_GAME_ESCAPE, ONE_V_ONE_FINALE)
- `card.comeback` — comeback closing card

`tier1(key, **fmt)` does `str.format_map(fmt)` against the resolved template. Missing format keys raise `KeyError` — caller bug, not a silent blank.

### 8. PolicyEditor accessibility contract

Per the `ai-friendly-web-design` skill, the editor must satisfy:

- Each row is `role="radiogroup"` with `aria-labelledby` pointing at the row label.
- Each option button is `role="radio"` with `aria-checked` reflecting state.
- Keyboard: arrow keys move within a row; Tab moves between rows.
- The preview line under the row is `aria-live="polite"` so screen readers announce changes.

The Playwright e2e asserts the aria states transition correctly when policy changes.

---

## File map

**Files modified:**
- `src/dodgeball_sim/models.py` — `CoachPolicy` v2 + 5 enums.
- `src/dodgeball_sim/rec_engine.py` — Four decision points + `_opening_rush`.
- `src/dodgeball_sim/official_tactics.py` — Semantic-intent mapping reads.
- `src/dodgeball_sim/official_engine.py` — Field-read rewrites (no behavior change).
- `src/dodgeball_sim/command_center.py` — `POLICY_KEYS`, `policy_label`, `policy_effect`, `policy_rows` rewritten against v2.
- `src/dodgeball_sim/dynasty_cli.py`, `matchup_details.py`, `replay_proof.py`, `recruitment_domain.py` — Field-read rewrites.
- `src/dodgeball_sim/randomizer.py`, `sample_data.py`, `setup_loader.py` — Generate v2 enum values for seed teams.
- `src/dodgeball_sim/persistence.py` — Loud-fail on legacy float payloads; serialize v2 dict.
- `src/dodgeball_sim/server.py` — Rewrite existing `/api/tactics` contract to v2; optional `/api/match-week/policy` alias only if it calls the same service; `GET /api/voice-register/{tier}`.
- `src/dodgeball_sim/web_status_service.py` — Emit v2 policy in match-week payload.
- `src/dodgeball_sim/match_orchestration.py` — Apply command-center `plan["tactics"]` v2 payloads into `Club.coach_policy`.
- `src/dodgeball_sim/command_week_service.py`, `src/dodgeball_sim/use_cases.py` — Preserve command-center plan save/simulate flow with v2 tactics.
- `src/dodgeball_sim/ai_program_manager.py` — AI weekly-plan tactic generation via v2 `_policy_for_intent`.
- `src/dodgeball_sim/league.py` — `Club.coach_policy` default factory remains v2 centroid.
- `src/dodgeball_sim/official_resolution.py`, `src/dodgeball_sim/official_actions.py` — Ensure official paths accept v2 policies through `official_tactics.py`; update stale float-weighting comments.
- `src/dodgeball_sim/voice_verdict.py` — Moment-aware headline with priority.
- `src/dodgeball_sim/voice_aftermath.py` — Moment + tactic-anchored paragraphs.
- `src/dodgeball_sim/voice_pregame.py` — Policy-aware pre-match line.
- `src/dodgeball_sim/engine.py` — Stop reading old fields; behavior gated behind the existing skip-the-generic-engine path. **No deletion.**
- `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` — Mount `PolicyEditor` above `MatchCard`.
- `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx` — Beat slots + banners + closing card.
- `frontend/src/types.ts` — v2 policy + moment-event types.
- `frontend/src/api/client.ts` — Rewritten tactics save helper + voice-register fetch.
- `docs/STATUS.md` — Mark Plan C landed.
- `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md` — Mark Plan C row landed; Plan D becomes next strict step.

**Files created:**
- `src/dodgeball_sim/voice_register.py` — Rec-league glossary + `tier1` / `for_tier`.
- `src/dodgeball_sim/aftermath_context.py` — `AftermathContext` dataclass.
- `frontend/src/components/match-week/command-center/PolicyEditor.tsx` — Pre-match UI.
- `frontend/src/components/match-week/aftermath/LateGameBanner.tsx` — `LATE_GAME_ESCAPE` banner.
- `frontend/src/components/match-week/aftermath/OneVOneBanner.tsx` — `ONE_V_ONE_FINALE` banner.
- `frontend/src/components/match-week/aftermath/ComebackCard.tsx` — `COMEBACK` closing card.
- `frontend/src/components/match-week/aftermath/ReplaySpeedControl.tsx` — Consolidated speed UI.
- `tests/test_coach_policy_v2.py` — Model + round-trip + loud-fail.
- `tests/test_official_tactics_policy_v2_mapping.py` — USAD branch-equivalence.
- `tests/test_rec_engine_policy_v2.py` — Four decision-point branch tests.
- `tests/test_voice_register.py` — Unknown key + snapshot of consumed keys.
- `tests/test_voice_verdict_priority.py` — Headline priority + no-moment fallback.
- `tests/test_voice_aftermath_moments.py` — Moment + tactic anchoring + no invention.
- `tests/test_policy_api.py` — v2 `/api/tactics` validation, optional alias validation, GET voice register.
- `tests/test_persistence_policy_loud_fail.py` — Legacy float payload raises.
- Existing tests rewritten in-place where they currently assert old float semantics: `tests/test_coach_policy.py`, `tests/test_command_center.py`, `tests/test_server.py`, `tests/test_official_tactics_and_resolution.py`, `tests/test_invariants.py`, `tests/test_regression.py`, `tests/test_voice_verdict.py`, `tests/test_replay_proof.py`, `tests/test_ai_program_manager.py`, and affected persistence/recruitment tests.
- `tests/e2e/tier1_recognition.spec.ts` — Playwright walk.

**Files NOT modified** (Plan C respects these boundaries):
- `src/dodgeball_sim/moment_events.py`, `engine_driver.py`, `flood_throws.py`, `stall_timer.py`, `fatigue.py` — Plan A primitives.
- `src/dodgeball_sim/burden.py`, `discipline.py`, `no_blocking.py`, `catch_queue.py`, `sequence.py`, `official_translator.py` — V11 / USAD core.
- `src/dodgeball_sim/voice_playbyplay.py` — Stays event-driven; out of scope.
- `tools/tier_1_sanity_probe.py` — Used as regression gate, not modified.

---

## Phase 1 — `CoachPolicy` v2 + USAD semantic-intent mapping

Phase 1 lands the data model and the loud-fail boundary without changing rec-driver behavior. The sanity probe must still print OK with all six moment kinds.

### Task 1: Re-grep verification

**Goal:** Confirm the expanded audit table in `plan-c-design.md` is still accurate against `main`.

- [ ] Grep every old field name (`target_stars`, `target_ball_holder`, `risk_tolerance`, `sync_throws`, `rush_frequency`, `rush_proximity`, `tempo`, `catch_bias`) across `src/`, `tests/`, and `frontend/src/`. Diff against the audit table in `plan-c-design.md`.
- [ ] On 2026-05-22, this grep found live old-policy references in `models.py`, `engine.py`, `official_tactics.py`, `official_engine.py`, `official_resolution.py`, `command_center.py`, `match_orchestration.py`, `ai_program_manager.py`, `dynasty_cli.py`, `matchup_details.py`, `replay_proof.py`, `randomizer.py`, `sample_data.py`, `setup_loader.py`, `server.py`, `web_status_service.py`, `frontend/src/types.ts`, `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`, multiple existing tests, and `tests/golden_logs/phase1_baseline.json`. Treat any remaining occurrence outside docs/archive as a Plan C work item unless the phase explicitly proves it is historical-only.
- [ ] If new call sites have appeared, append them to the design doc's table and to this plan's file map before continuing.
- [ ] Record any drift inline in this task's checklist as a comment.

**Verification:** No file outside the expanded audit table references the old field names. After Phase 1, no production file should reference the old field names at all, except historical docs under `docs/archive/`.

### Task 2: `CoachPolicy` v2 model

**Files:** `src/dodgeball_sim/models.py`, `tests/test_coach_policy_v2.py` (new).

- [ ] Write the failing test first: defaults are centroid (`MIXED / SPREAD / OPPORTUNISTIC / BALANCED / CENTER`); `as_dict()` returns string enum values; `from_dict(as_dict)` round-trips; `from_dict({"target_stars": 0.7, ...})` (legacy) raises `ValueError` naming the version; unknown enum string raises `ValueError`.
- [ ] Implement the five enums and the dataclass per design doc §"`CoachPolicy` v2 — exact shape".
- [ ] `as_dict()` and `from_dict()` are total. No silent defaults on missing keys.
- [ ] Delete the old 8-field class. Imports across the codebase will break — that is expected and Phase 1 fixes them all before the phase lands.

**Verification:** `pytest tests/test_coach_policy_v2.py -q` green.

### Task 3: `persistence.py` loud-fail + v2 serialization

**Files:** `src/dodgeball_sim/persistence.py`, `tests/test_persistence_policy_loud_fail.py` (new).

- [ ] Write the failing test: a fixture team save with the legacy 8-float `policy` dict raises `ValueError` with a message naming the legacy fields and pointing at Plan C.
- [ ] Update the save writer to emit the v2 dict shape.
- [ ] Update the load path to delegate to `CoachPolicy.from_dict`, which will raise on legacy payloads.

**Verification:** Loud-fail test green. Any existing pytest fixture that saves a CoachPolicy gets regenerated (one-pass `pytest -q` will surface them).

### Task 4: `randomizer.py`, `sample_data.py`, `setup_loader.py` — v2 seed values

**Files:** as listed.

- [ ] All seed paths construct `CoachPolicy()` (centroid) by default, or roll v2 enum values when the existing logic intends variation.
- [ ] Roll logic: when the old code rolled a uniform float on a field, the new code uses `rng.choice(list(<Enum>))` for the corresponding enum. Document the mapping inline.

**Verification:** Seed-team fixtures load; `pytest -q` does not regress.

### Task 5: `command_center.py` — `policy_label` / `policy_effect` / `policy_rows` rewrite

**Files:** `src/dodgeball_sim/command_center.py`.

- [ ] `POLICY_KEYS` becomes a tuple of `("approach", "target_focus", "catch_posture", "rush_commit", "rush_target")`.
- [ ] `policy_label(key)` returns the row label ("Approach", "Target focus", etc.) — does NOT yet read from `voice_register` (that comes in Phase 3); for now, the rec-league strings live inline with a `# TODO(plan-c-phase-3): route through voice_register.tier1` comment.
- [ ] `policy_effect(policy, key)` returns the currently-selected value's preview string.
- [ ] `policy_rows(policy)` returns one row per knob, each row carrying `{key, label, options: [{value, label, preview, selected}]}`. The frontend consumes this shape.
- [ ] Update the unit tests for `command_center` accordingly.

**Verification:** `pytest tests/test_command_center.py -q` green (or whatever the existing test module name is — `grep -l "policy_label\|policy_rows" tests/` to find it).

### Task 6: USAD semantic-intent mapping in `official_tactics.py` + `official_engine.py`

**Files:** `src/dodgeball_sim/official_tactics.py`, `src/dodgeball_sim/official_engine.py`, `tests/test_official_tactics_policy_v2_mapping.py` (new).

- [ ] Write the failing test first per pinned decision §5: re-run the existing `official_tactics` test fixtures with v2 policies whose enum values match the documented mapping of the old float thresholds. Assert the same `if/elif` branch is taken on every fixture.
- [ ] Implement the mapping in `official_tactics.py`. Every place that read `policy.risk_tolerance > 0.5` becomes `policy.target_focus == TargetFocus.THEIR_STARS` (and similar per the design doc's mapping table). Branch labels stay identical.
- [ ] `official_engine.py` updates are field-rename only; if it currently reads `policy.tempo`, that read becomes `policy.approach == Approach.AGGRESSIVE` (or similar) per the mapping.

**Verification:** New regression test green. **Existing V11 / USAD conformance tests stay green** (this is the Phase 1 acceptance bar — non-negotiable).

### Task 7: Remaining production field-read rewrites

**Files:** `src/dodgeball_sim/dynasty_cli.py`, `matchup_details.py`, `replay_proof.py`, `recruitment_domain.py`, `match_orchestration.py`, `command_week_service.py`, `use_cases.py`, `ai_program_manager.py`, `league.py`, `official_resolution.py`, `official_actions.py`.

- [ ] Each display-only file that reads old fields for cosmetic strings replaces those reads with v2 enum reads, formatted via `command_center.policy_label` / `policy_effect` to stay consistent.
- [ ] Where the display string was templated against a float (e.g. `f"Risk: {policy.risk_tolerance:.0%}"`), the new display reads the enum's preview string.
- [ ] `match_orchestration._apply_command_plan_to_match` applies v2 `plan["tactics"]` payloads into `Club.coach_policy` through `CoachPolicy.from_dict`, not float clamping.
- [ ] `command_week_service` and `use_cases` keep the current command-center save/simulate flow working with v2 tactics.
- [ ] `ai_program_manager.build_ai_weekly_plan` receives v2 tactics from `_policy_for_intent`; existing intent names (`Balanced`, `Win Now`, `Develop Youth`, `Preserve Health`, `Prepare For Playoffs`) map to explicit v2 policies.
- [ ] `league.Club` still defaults to `CoachPolicy()` v2 centroid.
- [ ] `official_resolution.py` / `official_actions.py` compile against v2 `CoachPolicy`; update comments that promise float weighting.

**Verification:** `pytest -q` green across the touched modules' tests, including `tests/test_ai_program_manager.py` and command-center/server tests.

### Task 8: Stop the generic engine from reading old fields

**Files:** `src/dodgeball_sim/engine.py`.

- [ ] Per brief §5 the generic `MatchEngine` is slated for deletion in a separate cleanup task. Plan C scope: stop reading old fields so the module imports cleanly with v2 `CoachPolicy`. Any old-field read either (a) routes through the semantic-intent mapping or (b) becomes a `raise NotImplementedError("generic MatchEngine deprecated — use RecTier1Driver or OfficialDriver")` if the read is on a code path that should already be dead.
- [ ] Confirm no test exercises the dead paths.

**Verification:** Module imports; `pytest -q` green.

### Task 9: Phase 1 gate — Plan A sanity probe

**Files:** none modified.

- [ ] Run `python tools/tier_1_sanity_probe.py`. All six moment kinds must still emit across 25 matches. The rec driver is not yet policy-aware in Phase 1, so the default-centroid policy should produce the same statistics as Plan A.
- [ ] Run the V11 / USAD conformance matrix: `pytest tests/test_official_conformance_matrix.py -q`. Must stay green.
- [ ] Run full pytest: `pytest -q`. Must stay green.

**Verification:** All three checks green. Phase 1 lands as one reviewable change.

---

## Phase 2 — Rec driver policy wiring

Phase 2 makes `RecTier1Driver` consume the four knobs. Plan A's sanity probe must still emit all six moments under *both* default and non-default v2 policies.

### Task 10: `approach` decision point

**Files:** `src/dodgeball_sim/rec_engine.py`, `tests/test_rec_engine_policy_v2.py` (new).

- [ ] Write the failing test first: with ratings + `throw_selection_iq` fixed and seeded RNG, the `AGGRESSIVE` policy produces a throw in a tick where `PATIENT` does not (deterministic, branch-level).
- [ ] Add `APPROACH_GATE_MULT = {Approach.AGGRESSIVE: 0.85, Approach.MIXED: 1.0, Approach.PATIENT: 1.20}` (pinned decision §1).
- [ ] In `_select_throwers`, apply the multiplier to the `throw_selection_iq` gate threshold.

**Verification:** Branch test green. Sanity probe still emits all six moments under default policy.

### Task 11: `target_focus` decision point

**Files:** `src/dodgeball_sim/rec_engine.py`, `tests/test_rec_engine_policy_v2.py`.

- [ ] Write the failing test: with two opponents (one high-OVR, one ball-holder, both equally targetable) and seeded RNG, `THEIR_STARS` selects the high-OVR target; `BALL_HOLDERS` selects the holder; `SPREAD` rotates away from the most-recently-thrown-at opponent.
- [ ] Implement the target-score formula per pinned decision §2. The recency-tracking helper lives in `rec_engine.py` as `_recency_weight(target_id)` and is reset per match.

**Verification:** Branch tests green. Sanity probe still six-out-of-six.

### Task 12: `catch_posture` decision point

**Files:** `src/dodgeball_sim/rec_engine.py`, `tests/test_rec_engine_policy_v2.py`.

- [ ] Write the failing test: with `catch_courage=50` and seeded RNG forcing the three-way boundary, `GO_FOR_CATCHES` chooses catch; `PLAY_SAFE` chooses dodge; `OPPORTUNISTIC` is the Plan B baseline.
- [ ] Implement the per-posture multipliers per pinned decision §3. Apply *after* Plan B's `catch_courage` weighting, then renormalize the three weights to sum to 1.0.

**Verification:** Branch tests green. Sanity probe still six-out-of-six.

### Task 13: `_opening_rush` (rush_commit + rush_target)

**Files:** `src/dodgeball_sim/rec_engine.py`, `tests/test_rec_engine_policy_v2.py`.

- [ ] Write the failing test: with seeded RNG and fixed starter positions, `ALL_IN + CENTER` produces 6 sprinters all targeting center balls; `HOLD_BACK + NEAREST` produces 2 sprinters each targeting their nearest ball.
- [ ] Implement `_opening_rush(policy)` per pinned decision §4. Called once at tick 0 per match. Existing Plan A opening behavior is the `BALANCED + CENTER` case (so default policy = today's behavior, by construction).

**Verification:** Branch tests green. Sanity probe still six-out-of-six under *non-default* policy: `(AGGRESSIVE, THEIR_STARS, GO_FOR_CATCHES, ALL_IN, NEAREST)` for both teams. If any moment kind drops to zero across 25 matches, that's a Phase 2 blocker — file an investigation task before proceeding.

### Task 14: Phase 2 gate

- [ ] `pytest -q` green.
- [ ] `python tools/tier_1_sanity_probe.py` six-out-of-six under default policy.
- [ ] `python tools/tier_1_sanity_probe.py` six-out-of-six under non-default policy (above).
- [ ] V11 / USAD conformance still green.

---

## Phase 3 — Voice modules + register

### Task 15: `voice_register` module

**Files:** `src/dodgeball_sim/voice_register.py` (new), `tests/test_voice_register.py` (new).

- [ ] Write the failing test first: `tier1(unknown_key)` raises `KeyError`. `for_tier(1)` returns the full Tier 1 dict. `tier1("policy.approach.aggressive.label")` returns the documented string. `tier1("moment.dramatic_catch.headline", catcher="Maurice", returning="Sam")` formats correctly. A missing format key raises `KeyError`.
- [ ] Populate `TIER1_REGISTER` with every key the design doc names. Per-knob `label` and `preview` for all 5 enums; per-moment `headline` / `body` / `beat`; banners; comeback card.
- [ ] Snapshot test enumerates every key any consumer might request (built by grepping `tier1(` call sites at the end of Phase 3) and asserts each resolves.

**Verification:** Both tests green.

### Task 16: `AftermathContext` + `voice_verdict` rewrite

**Files:** `src/dodgeball_sim/aftermath_context.py` (new), `src/dodgeball_sim/voice_verdict.py`, `tests/test_voice_verdict_priority.py` (new).

- [ ] Write the failing test first: priority ordering per pinned decision §6 (`HEADLINE_PRIORITY` iterated). A payload with both `Comeback` and `DramaticCatch` returns the comeback headline. A no-moments payload returns the existing margin-aware fallback (this is a regression test for the 2026-05-22 product-coherence fix).
- [ ] Define `AftermathContext` per design doc §"Voice modules — contract".
- [ ] Rewrite `render_headline(ctx: AftermathContext) -> str` to walk `HEADLINE_PRIORITY` and return the first match formatted via `voice_register.tier1`. Fall back to the existing margin-aware copy.

**Verification:** Priority test green. Existing `voice_verdict` tests still green or rewritten.

### Task 17: `voice_aftermath` rewrite

**Files:** `src/dodgeball_sim/voice_aftermath.py`, `tests/test_voice_aftermath_moments.py` (new).

- [ ] Write the failing test first: paragraph count is 2–4; `DRAMATIC_CATCH` + `GO_FOR_CATCHES` payload emits a paragraph naming both; empty moment list ⇒ no moment-anchored paragraphs (no invention); paragraphs only reference moments that exist in the input.
- [ ] Rewrite `render_body(ctx: AftermathContext) -> tuple[str, ...]`. Each paragraph anchors on a moment or a tactic. Tactics paragraphs reference v2 policy values that pair with observed moments.
- [ ] All copy via `voice_register.tier1`.

**Verification:** Tests green.

### Task 18: `voice_pregame` policy-aware line

**Files:** `src/dodgeball_sim/voice_pregame.py`, plus a new or extended pregame test.

- [ ] One pre-match line: "Today we're {approach}, focused on {target_focus}, and {catch_posture}." All three values via `voice_register.tier1`.
- [ ] Test: default centroid produces a specific known string; switching any one knob changes the corresponding placeholder.

**Verification:** Test green.

### Task 19: Route `command_center.policy_label` / `policy_effect` through register

**Files:** `src/dodgeball_sim/command_center.py`.

- [ ] Remove the Phase 1 `# TODO(plan-c-phase-3)` markers. `policy_label(key)` and `policy_effect(policy, key)` both read from `voice_register.tier1`.
- [ ] Tests that previously asserted inline strings now assert via the register.

**Verification:** `pytest -q` green.

### Task 20: API endpoints — v2 tactics save + voice-register GET

**Files:** `src/dodgeball_sim/server.py`, `src/dodgeball_sim/web_status_service.py`, `src/dodgeball_sim/match_orchestration.py`, `tests/test_policy_api.py` (new or merged into `tests/test_server.py`).

- [ ] Write the failing test first: existing `POST /api/tactics` with a valid v2 dict returns 200 and the team's stored policy reflects the change; with a legacy 8-float dict, returns 400 with a clear message; with an unknown enum string, returns 400.
- [ ] `POST /api/command-center/plan` accepts v2 `tactics` payloads and rejects legacy float dicts with HTTP 400. This is required because `PreSimDashboard` currently saves through the command-center plan flow.
- [ ] If the implementation adds `PUT /api/match-week/policy`, test it as an alias that calls the same service as `/api/tactics`; do not create a second persistence path.
- [ ] `GET /api/voice-register/{tier}` returns the dict for that tier (1 supported, others 404).
- [ ] `web_status_service.match_week_payload` includes the current v2 policy for both the user's team and the upcoming opponent.

**Verification:** API tests green.

### Task 21: Phase 3 gate

- [ ] `pytest -q` green.
- [ ] Sanity probe six-out-of-six under default + non-default v2 policies.
- [ ] V11 / USAD conformance still green.

---

## Phase 4 — Frontend (Command Center + Replay)

### Task 22: Frontend types + API wiring

**Files:** `frontend/src/types.ts`, `frontend/src/api/client.ts`.

- [ ] Add TypeScript types for v2 `CoachPolicy` (a string-literal union per knob) and the six `MomentEvent` discriminated-union types matching the backend dataclasses.
- [ ] Add a v2 tactics save helper that uses the rewritten live route (`POST /api/tactics`) and, if present, the `/api/match-week/policy` alias. Add `getVoiceRegister(tier)`.
- [ ] Cache the voice register in React state on first load; provide a `useVoiceRegister()` hook that returns `(key, fmt?) => string`.

**Verification:** `npm run build` and `npm run lint` clean.

### Task 23: `PolicyEditor.tsx`

**Files:** `frontend/src/components/match-week/command-center/PolicyEditor.tsx` (new), `PreSimDashboard.tsx`.

- [ ] Implement the layout in design doc §"Command Center pre-match UI". Five rows (Approach, Target focus, Catch posture, Opening rush — commit, Opening rush — target), grouped visually under one "Opening rush" subhead.
- [ ] Each row is `role="radiogroup"` with proper `aria-labelledby` and per-option `aria-checked`, per pinned decision §8.
- [ ] Optimistic update on click; rollback + visible error on save failure.
- [ ] Preview line under each row reads from the voice register and is `aria-live="polite"`.
- [ ] Mount the editor in `PreSimDashboard` above `MatchCard`. Delete the old policy-pills display.

**Verification:** This frontend currently has no Vitest or component-test script in `frontend/package.json`. Use `npm run build`, `npm run lint`, and the Phase 5 Playwright test as the regression gate unless a frontend test runner is explicitly added in this phase.

### Task 24: `ReplayTimeline` beat slots + speed consolidation

**Files:** `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx`, `ReplaySpeedControl.tsx` (new).

- [ ] Consolidate today's split speed UI into a single `ReplaySpeedControl` with 1x / 2x / 4x / instant. Wire wherever the two duplicate sites are.
- [ ] Add an optional `moment` slot per event row. When the event's tick matches a `DramaticCatch`, `GassedCollapse`, or `FloodThrow` moment, render the corresponding beat (copy from voice register).

**Verification:** `npm run build` clean, plus the Phase 5 Playwright fixture must assert each beat-rendering branch through a fixture or seeded replay route.

### Task 25: Banners + comeback card

**Files:** `LateGameBanner.tsx` (new), `OneVOneBanner.tsx` (new), `ComebackCard.tsx` (new), `ReplayTimeline.tsx`.

- [ ] `LateGameBanner` mounts when a `LateGameEscape` moment is active for the currently-rendered tick range; unmounts when the survivor goes out or wins.
- [ ] `OneVOneBanner` mounts when `OneVOneFinale` fires; renders both names from the register copy.
- [ ] `ComebackCard` renders at the bottom of the replay if any `Comeback` moment is present.

**Verification:** `npm run build` clean, plus the Phase 5 Playwright fixture must cover banner mount/unmount and comeback-card rendering.

### Task 26: Phase 4 gate

- [ ] `npm run build` and `npm run lint` clean.
- [ ] Manual smoke: load a progressed save, open Command Center, change one knob per row, sim a match, watch the replay, read the aftermath. No console errors.

---

## Phase 5 — Playwright e2e + docs

### Task 27: Playwright e2e

**Files:** `tests/e2e/tier1_recognition.spec.ts` (new), plus any test-setup helpers needed.

- [ ] Walk: New career → Tier 1 → Command Center renders `PolicyEditor` → change Approach to Aggressive → change Catch Posture to "Go for catches" → sim match → Match Replay renders at least one inline moment beat → Aftermath references both a moment and a tactic → Headline is non-empty rec-league copy.
- [ ] Accessibility check at the policy editor: arrow-key navigation works within a row, Tab moves between rows, `aria-checked` flips on selection.
- [ ] Run via `npx playwright test`.

**Verification:** Playwright green.

### Task 28: STATUS + roadmap

**Files:** `docs/STATUS.md`, `docs/specs/2026-05-20-post-v11-redesign-brief/tier-1-roadmap.md`.

- [ ] STATUS: add Plan C to "Shipped And Verified" with a one-paragraph summary, the spec link, and the regression-gate confirmations.
- [ ] STATUS: note audit-7.6 resolution (deferred from 2026-05-22 pre-Plan-C knockout) if it was addressed within Plan C scope; otherwise leave it as an explicit follow-up under "Open Work And Known Gaps".
- [ ] Roadmap: mark Plan C row landed; "Plan D becomes the next strict step" in the header.

**Verification:** Markdown lints / renders cleanly.

### Task 29: Final gate

- [ ] `pytest -q` green (~795+ tests).
- [ ] `python tools/tier_1_sanity_probe.py` six-out-of-six under default + non-default v2 policies.
- [ ] `pytest tests/test_official_conformance_matrix.py -q` green.
- [ ] `npm run build` and `npm run lint` clean.
- [ ] `npx playwright test` green.
- [ ] STATUS and roadmap reflect the landing.

---

## Plan C: definition of done

- `CoachPolicy` v2 is the only `CoachPolicy` in the codebase; all 14 files in the audit table compile and pass tests.
- `RecTier1Driver` consumes the four knobs at the four pinned decision points. Per-knob branch tests pass. Sanity probe emits all six moment kinds under default *and* non-default policies.
- `OfficialDriver` accepts v2 policy without breaking USAD conformance. Semantic-intent mapping is pinned by branch-equivalence regression test.
- `voice_verdict` and `voice_aftermath` reference moment events and v2 policy. `voice_pregame` emits one policy-aware line. No invented moments. Priority ordering and no-moment fallback are tested.
- `voice_register.tier1` is the single source of rec-league copy. Unknown keys raise.
- Command Center `PolicyEditor` is the canonical pre-match UI. The old policy-pill display is gone. API accepts v2 strings and rejects legacy float payloads with HTTP 400.
- `ReplayTimeline` surfaces all six moment beats. Banners and closing card render correctly. A single `ReplaySpeedControl` exists.
- Playwright e2e walks the recognition path and asserts beats + voice copy + aria states.
- Full pytest green. V11 / USAD conformance untouched. Frontend build + lint clean.
- `docs/STATUS.md` updated. `tier-1-roadmap.md` Plan C row marked landed. Plan D is the next strict step.

---

## Self-review checklist (run before handing off)

- [ ] Every task's failing test is written *before* the implementation.
- [ ] No task changes more than one phase's worth of surface area; each phase lands as one reviewable change.
- [ ] No task introduces a backwards-compatibility shim for the old 8-field model. Clean break per brief §8.
- [ ] No task touches `moment_events.py`, the `EngineDriver` protocol, or any V11 / USAD core module.
- [ ] `voice_playbyplay.py` is untouched.
- [ ] `tools/o1_variance_probe.py` is untouched. (Plan D replaces it.)
- [ ] No probabilistic "measurably more" assertions in any test. All behavioral tests use seeded RNG with deterministic branch assertions.
- [ ] Audit-7.6 carry-in is either resolved within Plan C scope or explicitly noted as a follow-up.
- [ ] Sanity probe is re-run after every rec-driver task and at every phase gate.

---

## Execution handoff

This plan is task-by-task executable by Gemini under superpowers:subagent-driven-development (or superpowers:executing-plans for a single-session run). Codex review per phase has been the working cadence for Plans A and B; recommend the same shape here.

Phase gates are non-negotiable: do not start Phase N+1 until Phase N's gate is green.

If the sanity probe drops a moment kind under any policy combination during Phase 2, **stop**. Open an investigation task before continuing — Plan C must not silently regress the recognition surface that Plan A established.
