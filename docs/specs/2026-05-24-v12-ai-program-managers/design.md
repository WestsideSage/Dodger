# V12 — AI Program Managers And Rival Adaptation Loop (Design)

Date: 2026-05-24
Status: Design, awaiting plan
Predecessors: V11 Official USA Dodgeball Rules (`docs/specs/2026-05-20-v11-official-usad-rules/design.md`); V10 Staff Market thin ship (`docs/archive/retrospectives/v8-v10/2026-05-06-dynasty-office-blitz-handoff.md`); V5 Weekly Command Center (`docs/archive/specs/v5/2026-05-02-v5-weekly-command-center/design.md`); Plan A hybrid driver (`docs/specs/2026-05-20-post-v11-redesign-brief/plan-a-hybrid-driver.md`).

## Relation to Prior Specs

- This is the milestone formerly labeled "V11 / AI Program Managers" in `docs/specs/long-range-playable-roadmap.md`. V11 shipped as Official USA Dodgeball Rules, so this work was re-slotted to **V12** on 2026-05-24. The roadmap section now points here.
- **V5 (Weekly Command Center)** established the user-side weekly loop (`intent → department orders → tactics → lineup → simulate → diagnose`). V12 gives AI clubs an honest version of the same loop. The user-facing spine is unchanged.
- **V10 (Staff Market, thin)** seeded staff entities and per-club effects. V12 consumes staff lanes — `development`, `conditioning`, `scouting`, `tactics`, `recovery`, `culture` — when an AI club decides intent and orders. V12 does **not** rebuild V10's staff model; it reads what V10 already persists.
- **V8/V9 (Recruiting/Promises and Living League Memory, thin)** persist recruiting history, prestige, and rivalries. V12 reads these to shape multi-season program identity (rebuild vs. contend) but does not extend their schemas.
- **Plan A (hybrid driver)** matters for one boundary: V12 produces a weekly plan for each AI club, and `_apply_command_plan_to_match` already converts a plan into the `CoachPolicy` the driver consumes. V12 must continue to round-trip through that path so the engine treats AI policies identically to user policies — no special-cased AI math.
- Original roadmap intent: `docs/specs/long-range-playable-roadmap.md` (V12 section, formerly "Future: AI Program Managers").

## Problem

`src/dodgeball_sim/ai_program_manager.py` is a 103-line scaffold. It:

- Picks one of five intents from a one-line standings heuristic (`choose_ai_intent`).
- Always uses `DEFAULT_DEPARTMENT_ORDERS`.
- Always uses `_policy_for_intent(club.coach_policy, intent)` — i.e., the user's policy-templating function applied to whatever `coach_policy` was set at career creation. No club identity.
- Always uses `optimize_ai_lineup(roster)` — overall-skill top-N. No archetype awareness, no fatigue or development priority.
- Has no memory between weeks. No multi-season state. No adaptation.
- Persists a "plan" row per `(season_id, week, club_id)` only because `prepare_ai_plans_for_matches` needs an idempotency key.

Tests at [tests/test_ai_program_manager.py](tests/test_ai_program_manager.py) cover the five intent branches and the shape of the plan dict. Nothing covers archetype, adaptation, or multi-season behavior.

Consequence: the league reads as 11 user-shaped clones running a single decision tree. The roadmap's V12 thesis — "rebuilds, dynasties, counters, and collapses" — is not visible to a player. Rival programs do not feel like programs.

## Playable Thesis

Opposing programs make believable simplified decisions under mostly the same rules, creating rebuilds, dynasties, counters, and collapses that the player can see in standings, news, recruiting interest, and on-court matchups.

The **user-visible proof** is the deliverable, not the AI sophistication. A V12 ship is only honest if the player can:

1. Open Dynasty Office → Standings and see a rival's multi-season trajectory (e.g., "Year 3 of a development rebuild").
2. Read a post-match report and learn that the opponent leaned into a counter to the user's dominant tactic.
3. See an AI club's offseason recruiting choices reflect its own archetype (a "development factory" prefers raw upside; a "contender" prefers verified ready-now stars).
4. Watch a dynasty rise from honest, visible inputs — staff hires, development focus, recruiting — not hidden boosts.

## Scope

### In scope

1. **Program archetypes (4–6 named).** Each AI club has a stable identity persisted on the `Club` row (or a sidecar table) — e.g., `Contender`, `Development Factory`, `Defensive Specialist`, `Power Throwers`, `Balanced Rebuild`, `Aging Veterans`. Identity influences default intent distribution, department-order weighting, lineup preference, and recruiting fit. Identity is observable in the UI.
2. **Weekly intent that reads roster + standings + identity.** Replace the single-line heuristic in `choose_ai_intent` with a small scoring function over (record, fatigue, recent results, archetype, late-season state). Output remains one of the existing five intents — no new user-visible vocabulary unless explicitly tested in the UI.
3. **Department orders driven by archetype + intent.** Replace the static `DEFAULT_DEPARTMENT_ORDERS` with an archetype-weighted distribution. Honest mapping: a `Development Factory` always assigns extra reps to youth even in contender weeks; a `Contender` defaults to film study and conditioning maintenance.
4. **Lineup logic that respects archetype and dev focus.** Replace `optimize_ai_lineup`'s pure-skill top-N with: skill top-N **minus** liability matrix penalties (the V6 liability surface already exists), **plus** an archetype hook — `Development Factory` slots one rookie above a slightly-better veteran in non-must-win weeks; `Aging Veterans` does not.
5. **Tactics policy from archetype, not user template.** AI clubs need their own `CoachPolicy` shaped by archetype, not `_policy_for_intent(club.coach_policy, intent)`. A `Power Throwers` archetype uses `Approach.AGGRESSIVE`, `OpeningRushCommit.HEAVY`; a `Defensive Specialist` uses `Approach.PATIENT`, `CatchPosture.CONFIDENT`. The v2 five-enum policy from Plan C is the only valid output shape.
6. **Multi-season memory: trajectory tags.** Persist one structured "program trajectory" record per club per season summarizing (record, archetype, dominant intent mix, top development bets, recruiting class strength). The Dynasty Office reads the last N seasons to display "Year 3 of a development rebuild" or similar. **No** narrative-text generation in V12 — the trajectory is structured data; rendering is mechanical templating.
7. **Adaptation: rival response to user dominance.** If the user wins ≥70% of league games over a rolling window, AI clubs whose next match is against the user shift one intent or department-order weight toward a counter (extra film study, defensive-tactic emphasis). Bounded: at most one shift per match, no hidden engine bonus. Visible in the AI plan's `summary` field and surfaced in the matchup preview.
8. **AI recruiting plug-in.** AI clubs already participate in recruitment via `recruitment.py`. V12 adds an archetype-aware preference shim so `Development Factory` clubs weight upside, `Contender` clubs weight verified ratings, and `Aging Veterans` clubs over-sign at scarce archetypes. No new recruitment phases.

### Out of scope

- **Per-AI-club user-equivalent UI decision sim.** AI clubs do not run the full Command Center state machine; they call into the same data primitives but skip the staff-recommendation UX layer.
- **Hidden AI rating boosts, scripted parity, comeback code.** Forbidden by the integrity contract (`docs/specs/AGENTS.md`) and the Simulation Honesty pillar.
- **Staff market rewrite.** V10's thin staff model is consumed read-only. If V12 surfaces a missing staff field (e.g., "archetype affinity"), file a follow-up rather than extending here.
- **Difficulty toggle.** No "Hard mode" knob. If difficulty is added later, it must shape AI decision quality or user information — never engine math.
- **News/commentary on archetype changes.** V13 (Broadcast) owns presentation. V12 ships only the structured trajectory data plus the simplest mechanical labels needed for the Dynasty Office to render.
- **OfficialDriver-specific tuning.** V12 must work under both drivers because both are now selectable at career creation; no driver-specific AI code paths.

## Approach (three phases)

### Phase 1 — Persist archetype + trajectory; thread through the existing scaffold

Foundation. No behavior change visible to the user yet; this is the data shape every later phase depends on.

**Work:**

1. Add `program_archetype` to the `Club` row (schema migration via `persistence.connect()`, new `CURRENT_SCHEMA_VERSION`). Backfill: every existing club is assigned a deterministic archetype from current roster shape (overall mean, average age, top-archetype distribution from Plan B). The user's club defaults to `Balanced Rebuild` unless the new-game flow exposes a choice — V12 does **not** add the new-game choice; that's a V12 follow-up.
2. Add a `program_trajectory` table: `(club_id, season_id, archetype, dominant_intent, record_w, record_l, record_d, top_dev_archetype, recruiting_class_strength, notes_json)`. One row per club per season. Written by an offseason-ceremony hook.
3. Thread `program_archetype` through `build_ai_weekly_plan` as an unused parameter. No behavior change yet — Phase 2 consumes it.
4. Add `tests/test_program_archetype_persistence.py`: round-trips an archetype, asserts trajectory rows after a simulated season, asserts schema upgrade is idempotent.

**Exit criterion:** all clubs persist an archetype; one trajectory row per club per finished season; full pytest green.

### Phase 2 — Honest decision functions

The visible behavior change. One module per decision surface so review can land them independently.

**Work:**

1. **`ai_intent.py`** — replace `choose_ai_intent` with a scoring function over `(record_pace, fatigue_pressure, recent_form, archetype_preference, late_season_state)`. Pure function. Unit-tested against fixed standings/roster snapshots. Five intents, no new strings.
2. **`ai_orders.py`** — archetype × intent → `department_orders` dict. Static table for V12 (no learning). Unit-tested against archetype matrix.
3. **`ai_lineup.py`** — wrap `optimize_ai_lineup` with a liability-aware filter (V6's `lineup_liabilities`) and an archetype hook (`Development Factory` substitutes one rookie when (a) it's not a must-win week and (b) the rookie's `conditioning_curve` predicts recoverable fatigue). Tests cover: liabilities reduce score, rookie substitution fires under correct conditions, must-win weeks suppress it.
4. **`ai_tactics.py`** — archetype → v2 `CoachPolicy` (the five-enum Plan C model). Tested for every archetype.
5. Rewire `build_ai_weekly_plan` to consume the four modules above. Keep the existing return-shape contract — `command_week_service.py` and `use_cases.py` do not change.
6. Regenerate any goldens whose matches now resolve differently. Per AGENTS.md, golden changes ship in the same commit as the formula change, with the spec link in the message.

**Exit criterion:** AI weekly plans vary by archetype on identical rosters; pytest green; a 50-season Monte-Carlo run shows non-degenerate league movement (no single archetype wins ≥80% of titles).

### Phase 3 — Adaptation, recruiting shim, UI surfacing

Closes the visibility loop.

**Work:**

1. **Adaptation hook.** In `prepare_ai_plans_for_matches`, before saving a plan, query `load_recent_user_match_results` for a rolling 8-game window. If user win rate ≥ 0.70, apply one bounded shift to the AI plan against the user (`intent` may bump one notch toward `Win Now` or `Preserve Health` per archetype; `department_orders` may add 1 to `film_study`). Cap: one shift per plan. Recorded in `plan["summary"]`.
2. **Recruiting shim.** Extend `recruitment.py`'s AI preference function with an archetype-keyed weight overlay. Tests: a `Development Factory` AI selects the higher-upside prospect at parity; a `Contender` AI selects the higher-floor prospect.
3. **Dynasty Office surface.** Standings page renders archetype chip + trajectory hint per club (e.g., "Year 3 — Development Rebuild"). Matchup preview shows the AI plan's `summary` when an adaptation shift fired. Frontend changes in `frontend/src/features/dynasty/` (existing surfaces) — no new routes.
4. **Playwright walk.** `tests/e2e/v12_ai_program_managers.spec.ts`: progress two seasons, assert standings shows ≥3 distinct archetype chips, assert at least one trajectory hint references year 2+, assert a matchup preview surfaces an adaptation summary after a 70%+ user run.

**Exit criterion:** all four user-visible proofs from the Playable Thesis section are reachable in the browser by a fresh user with no documentation; pytest + frontend build green; the rec driver's win-rate distribution across AI archetypes is not flat.

## Out of Scope (reiterated, with rationale)

See "Out of scope" under Scope. Re-stated so review knows what to push back on without re-reading: no hidden boosts, no per-AI Command Center UI, no V10 staff rewrite, no difficulty toggle, no V13 commentary, no driver-specific code paths.

## Risks

- **Archetype assignment from current rosters lies.** A backfilled archetype that doesn't match the roster will produce nonsense plans. Mitigation: backfill from roster shape, not historical record; document that the first season after upgrade has noisy archetype labels.
- **Adaptation reads as cheating.** Even a bounded one-notch shift can feel like a hidden boost if the user can't see why. Mitigation: the shift is always reflected in the visible `summary` string and the matchup preview; no engine math is touched.
- **Goldens churn.** Phase 2 changes every AI plan, so every rec-driver golden involving an AI opponent will regenerate. This is the same risk pattern as O1 Phase 3 — accept the churn in the same commit, audit the regenerated logs for anything surprising.
- **Phase 2 lineup change hides a Plan B bug.** If `conditioning_curve` is mis-read, rookie substitution fires when it shouldn't. Mitigation: explicit unit test reads `conditioning_curve` from a fixture player and asserts the rookie-sub branch.
- **Long-tail of trajectory edge cases.** Expansion clubs, franchise relocations (none today, but the schema must not block them), mid-season identity drift. Mitigation: trajectory is per-season only; archetype changes happen at offseason ceremony in a single bounded hook.

## Acceptance Criteria

1. `python -m pytest -q` is green, including the new test files: `test_program_archetype_persistence.py`, `test_ai_intent.py`, `test_ai_orders.py`, `test_ai_lineup.py`, `test_ai_tactics.py`.
2. `npm run build` and `npm run lint` in `frontend/` are clean.
3. Playwright spec `tests/e2e/v12_ai_program_managers.spec.ts` passes against the local dev server.
4. A 50-season Monte-Carlo league sweep (driven from `tools/` — script lives in the implementation plan, not this spec) shows: ≥3 distinct archetypes win titles; no single archetype exceeds 50% of titles; AI clubs measurably differ in average department-order distribution.
5. `docs/STATUS.md` moves V12 into "Shipped And Verified" with the spec link; `docs/specs/MILESTONES.md` updates V12's status to `Shipped (YYYY-MM-DD)`.
6. The integrity contract holds: zero new hidden randomness, no engine-side AI branch, no comeback code. The diff against `engine.py` and `rec_engine.py` is empty unless the implementation plan justifies and `docs/superpowers/specs/` documents the change.
