# V4 Sprint Plan

> Historical closeout note: V4 is now marked shipped in `docs/specs/MILESTONES.md`. This sprint plan is retained as the planning artifact that led into the web foundation work, but its unchecked task boxes and future-tense language should not be treated as current status. For current orientation, use root `AGENTS.md`, `docs/specs/MILESTONES.md`, and later V4 retrospectives.

## Project Trajectory

### WHERE WE WERE
V3 (Experience Rebuild) successfully laid down the essential architectural groundwork for a robust dynasty manager. It enforced proper 6-player active roster limits, rebuilt the match replay presentation, introduced five pacing controls for bulk simulation, and seeded a web client foundation (`frontend/` + `server.py`) using React, Vite, and FastAPI. The simulation remains highly deterministic, utilizing a 10-beat off-season ceremony and a state-machine-driven career progression.

### WHERE WE ARE
Based on the multi-agent audit consensus, V3 is functionally stable and mathematically sound as a foundation, but it carries severe structural and state-corruption risks that currently block a safe expansion of the V4 web architecture. 

**Critical Issues:**
- **State Corruption:** Duplicate prospect signings allow multiple clubs to own the same player (CF-1). Damaged save files (malformed JSON) or forged cursor states cause the game to hard crash rather than recovering cleanly (CF-2, CF-3). 
- **Tech Debt:** The domain orchestration is heavily entangled within the 4,145-line `manager_gui.py` monolith (TD-05). `scouting_center.py` leaks DB connections into its domain logic (TD-02). A frozen-cursor mutation bug outright breaks the existing web simulation endpoint (TD-04).
- **Balance & AI Logic:** AI clubs struggle with multi-season dynasty management, aggressively over-drafting for "need" over "value" and refusing to trim bloated rosters. Rush tactics carry disproportionate fatigue penalties relative to their accuracy bonuses.
- **Content & UI:** The existing React web client suffers from raw UUID display, missing UX feedback on saves, and rendering performance gaps. The copy and naming pools are highly repetitive and lack depth.

### WHERE WE ARE GOING
V4's non-negotiable scope is **Web Architecture Foundation and Feature Parity**. The goal is to bring the React SPA to feature parity with the Tkinter client, establishing a robust, decoupled, and thread-safe architecture that can handle concurrent web requests and richer narrative content. We will not build new deep simulation mechanics until the core web scaffolding is complete and all tech debt prerequisites are paid down.

## Readiness Verdict

**Conditionally Ready.** 
The match engine and basic loops are solid. However, we cannot start building new web features or adding new screens until the structural coupling in `manager_gui.py`, the AI's roster mismanagement, and the chaos-identified state corruptions are resolved.

## Prerequisite Checklist

Before feature work begins, the following must-do fixes are required:

- [ ] Task: Fix duplicate prospect signing (CF-1)
  - Source report: V3 Chaos Report
  - Why required: One player owned by multiple clubs poisons lineup truth and future recruitment.
  - Owner/model: Senior Debug & Maintenance Engineer
  - Acceptance check: `sign_prospect_to_club` checks and enforces `is_signed`, causing duplicate attempts to safely fail.
- [ ] Task: Fix `server.py` frozen-cursor mutation bug (TD-04)
  - Source report: V3 Arch Audit
  - Why required: The existing `POST /api/sim/week` web endpoint is broken and raises `FrozenInstanceError`.
  - Owner/model: Senior Debug & Maintenance Engineer
  - Acceptance check: Replace `cursor.week = next_week` with `dataclasses.replace(cursor, week=next_week)`. Add a test for the endpoint.
- [ ] Task: Fix JSON payload corruption & forged cursor crash paths (CF-2, CF-3)
  - Source report: V3 Chaos Report
  - Why required: Damaged saves crash the client. Forged cursor indices crash the UI.
  - Owner/model: Senior Debug & Maintenance Engineer
  - Acceptance check: Catch JSON load errors and provide a recoverable path or clear validation message. Clamp/reject out-of-range cursor payloads.
- [ ] Task: Add schema migration test (TD-07)
  - Source report: V3 Arch Audit
  - Why required: Prevents migration regressions and guarantees v11 development safety.
  - Owner/model: Principal Systems Architect
  - Acceptance check: A test applies v1→v10 migrations to an in-memory DB and validates the final schema.
- [ ] Task: Extract domain orchestration to `game_loop.py` (TD-05)
  - Source report: V3 Arch Audit
  - Why required: Crucial orchestration logic is trapped in `manager_gui.py`, forcing the web client to copy-paste behavior.
  - Owner/model: Principal Systems Architect
  - Acceptance check: Shared season lifecycle functions live in `src/dodgeball_sim/game_loop.py`. Both clients use it.
- [ ] Task: Purify `scouting_center.py` (TD-02)
  - Source report: V3 Arch Audit
  - Why required: Domain logic currently requires a raw sqlite connection, violating the architecture boundary.
  - Owner/model: Principal Systems Architect
  - Acceptance check: Split into a pure-compute `advance_scouting_snapshot` function and a separate I/O wrapper.
- [ ] Task: Rebalance AI Draft Weights & Roster Cuts
  - Source report: V3 Balance Report
  - Why required: Prevents AI clubs from hoarding low-ceiling prospects and building bloated benches over multiple seasons.
  - Owner/model: Lead Game Systems & Balance Analyst
  - Acceptance check: Reduce `need_score` multiplier in `build_recruitment_board()`. Implement AI routine to release worst bench player if roster > 9 during offseason.
- [ ] Task: Rebalance Rush Tactic
  - Source report: V3 Balance Report
  - Why required: Rush fatigue currently outweighs its accuracy bonus, making it mathematically suboptimal.
  - Owner/model: Lead Game Systems & Balance Analyst
  - Acceptance check: Adjust `rush_accuracy_modifier_max` to `0.15` and `rush_fatigue_cost_max` to `0.20`.
- [ ] Task: Fix UI Award Display Bug (BUG-302)
  - Source report: V3 Playthrough QA
  - Why required: Raw UUIDs are exposed in the League Wire instead of display names.
  - Owner/model: Lead Front-End UX Engineer
  - Acceptance check: Awards wire items display properly resolved player names.

## At-Risk Scope

- Feature: V4 Web Async Match Queueing & Multi-User Support
  - Dependency: Thread-safety in `persistence.py` (TD-03).
  - Risk: Simultaneous web requests risk DB lock contention (`database is locked`).
  - Decision: **Defer.** V4 will target single-user local web parity first. Implement WAL mode and basic connection safety before considering broader async concurrency.
- Feature: Tkinter Visual Overhaul & New Screens
  - Dependency: Extracting screens from `manager_gui.py` monolith.
  - Risk: The monolith is already 4,145 lines. Adding more screens directly to it is unsustainable.
  - Decision: **Cut.** Tkinter feature work is halted until `manager_gui.py` is properly decomposed into a `screens/` directory. Web UI gets priority.
- Feature: Random Event Scenarios (Content Update)
  - Dependency: Requires a new event-dispatch infrastructure in the core engine.
  - Risk: Pushes scope too far outside of V4's web parity target.
  - Decision: **Defer.** The scenarios are written and documented for V5.

## Atomic Task List

### Task 1: Pre-V4 Hardening (State & Data Corruptions)
- Owner/model: Senior Debug & Maintenance Engineer
- Files likely touched: `src/dodgeball_sim/recruitment.py`, `src/dodgeball_sim/server.py`, `src/dodgeball_sim/persistence.py`, `src/dodgeball_sim/manager_gui.py`
- Purpose: Knock out the most critical bugs. Fix the duplicate prospect signing exploit, resolve the web server's frozen-cursor mutation bug, and implement defensive save-state loading.
- Inputs: V3 Chaos Report, V3 Arch Audit.
- Implementation notes: Replace `cursor.week = next_week` with `dataclasses.replace`. Validate `is_signed` flag in `sign_prospect_to_club`. Catch `JSONDecodeError` during load paths. Clamp out-of-range beat indices in the GUI routing.
- Tests required: Assert duplicate sign attempts fail. Add test for `POST /api/sim/week`. Assert corrupted JSON loads are handled.
- Done when: CF-1, CF-2, CF-3, and TD-04 are resolved.
- Do not: Start web feature work or architectural refactoring.

### Task 2: Migration Safety & System Purity
- Owner/model: Principal Systems Architect
- Files likely touched: `tests/test_persistence.py`, `src/dodgeball_sim/game_loop.py` (new), `src/dodgeball_sim/manager_gui.py`, `src/dodgeball_sim/server.py`, `src/dodgeball_sim/scouting_center.py`
- Purpose: Eliminate tech debt blocking the web client from sharing domain logic securely.
- Inputs: V3 Arch Audit.
- Implementation notes: Add a migration test spanning v1 to v10. Extract the core season orchestrator logic from `manager_gui.py` into a pure `game_loop.py`. Refactor `scouting_center.py` to separate pure computation from raw SQLite connection passing.
- Tests required: The v1→v10 in-memory migration validation test.
- Done when: Both Tkinter and React server share `game_loop.py` without code duplication, and the migration test passes.
- Do not: Decompose `MatchEngine.run()` yet.

### Task 3: Simulation & AI Balance Tuning
- Owner/model: Lead Game Systems & Balance Analyst
- Files likely touched: `src/dodgeball_sim/config.py`, `src/dodgeball_sim/recruitment_domain.py`, `src/dodgeball_sim/franchise.py`
- Purpose: Ensure AI clubs manage their rosters competitively over multiple seasons and re-balance the rush mechanic.
- Inputs: V3 Balance Report.
- Implementation notes: Adjust `rush_accuracy_modifier_max` (0.15) and `rush_fatigue_cost_max` (0.20) in `phase1.v1` config. Drop `need_score` multiplier from 10.0 to 4.0 in AI recruitment. Implement a cut mechanism in the offseason beats to drop the worst bench player if an AI roster exceeds 9 total players.
- Tests required: Verify AI cut logic respects `potential` trait over raw `overall` for young players. Check Monte Carlo distribution for the rush tactic.
- Done when: AI actively releases poor bench players, drafts more logically, and the rush tactic is balanced.
- Do not: Apply any hidden AI stat boosts. 

### Task 4: Content Integration & Copy Fixes
- Owner/model: Lead Procedural Content & Narrative Designer / Implementation Engineer
- Files likely touched: `src/dodgeball_sim/randomizer.py`, `src/dodgeball_sim/identity.py`, `src/dodgeball_sim/news.py`, `src/dodgeball_sim/manager_gui.py`
- Purpose: Inject the expanded name pools, nickname components, multi-variant news headlines, and canonical club lore, while fixing BUG-302.
- Inputs: V3 Content Update, V3 Playthrough QA.
- Implementation notes: Replace `_FIRST_NAMES`, `_LAST_NAMES`, `_TEAM_NAMES`, `_SUFFIXES`, `_ARCHETYPE_PREFIXES`, and `_ARCHETYPE_SUFFIXES` with the new expanded arrays. Refactor `news.py` headline generation to select from template variants using `DeterministicRNG`. Add `club_lore.json`. Pass the roster context into `build_wire_items` to fix the raw `player_id` award bug (BUG-302).
- Tests required: Name collision avoidance tests, nickname variation tests, and news template generation tests ensuring no unresolved tokens.
- Done when: Content arrays are updated, news generation is varied and deterministic, and awards display proper names.
- Do not: Wire up the random event scenarios (deferred to V5).

### Task 5: V4 Web UI Polish & Feature Parity (Phase 1)
- Owner/model: Lead Front-End UX Engineer
- Files likely touched: `frontend/src/*`, `src/dodgeball_sim/server.py`
- Purpose: Polish the existing React UI components to remove friction and improve rendering performance.
- Inputs: V3 UI/UX Polish Audit.
- Implementation notes: Embed club display names in `/api/status` to replace raw UUIDs in the Hub. Add save-success feedback to `Tactics.tsx` and an `isDirty` state guard. Optimize the O(n²) `default_lineup.includes` lookup in `Roster.tsx` using `useMemo` and a `Set`. Expose an `OVR` and `Potential` column in the Roster table.
- Tests required: Update frontend tests to match the new endpoints/payloads if applicable.
- Done when: Hub displays correct names, Tactics confirms saves, Roster is performant and shows Potential/OVR.
- Do not: Build entirely new screens yet.

### Task 6: V4 Web UI Feature Parity (Phase 2)
- Owner/model: Lead Front-End UX Engineer
- Files likely touched: `frontend/src/*`, `src/dodgeball_sim/server.py`
- Purpose: Bring the web client up to feature parity with the Tkinter app.
- Inputs: V3 UI/UX Polish Audit.
- Implementation notes: Port the 5 pacing controls (Sim Week, Play Next Match, etc.) to the React Hub. Add League Context screens: Standings, Schedule, and News Wire. Add URL routing via `URLSearchParams` or React Router.
- Tests required: API endpoint tests for the new views (Standings, Schedule, News).
- Done when: The web client has robust pacing controls and basic league-context navigation that matches Tkinter.

## Handoff Instructions

Provide the following prompt to the engineering agent to begin Task 1:

> "You are the Senior Debug & Maintenance Engineer. Your task is to resolve critical data and state corruption bugs identified in the V3 audits. 
> First, fix the duplicate prospect signing bug in `src/dodgeball_sim/recruitment.py` to ensure `sign_prospect_to_club` enforces the `is_signed` flag, rejecting duplicate signatures. 
> Second, fix the `FrozenInstanceError` in `src/dodgeball_sim/server.py` for `POST /api/sim/week` by replacing `cursor.week = next_week` with `dataclasses.replace(cursor, week=next_week)`. 
> Third, add defensive validation to handle malformed JSON loads and clamp out-of-range forged cursor states in `src/dodgeball_sim/persistence.py` and `src/dodgeball_sim/manager_gui.py`. 
> Validate your fixes with new pytest assertions to prove they are resolved."

## Regression Gate

Before V4 is considered fully shipped, the following checks must pass:
- `python -m pytest` must pass all tests with zero failures.
- Physical SQLite integrity must remain `ok` via `PRAGMA integrity_check`.
- Running `python qa_v3_playthrough.py` (or its V4 equivalent) must complete a full season without error.
- All new V4 React components must build successfully via `npm run build`.
