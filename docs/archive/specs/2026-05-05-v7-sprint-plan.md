# V7 Sprint Plan: Watchable Match Proof Loop

Date: 2026-05-05
Milestone transition: V6 Player Identity and Development Loop -> V7 Watchable Match Proof Loop
Prepared by: Lead Technical Project Manager

## Source Inputs

- Read: `docs/specs/MILESTONES.md`
- Read: `docs/specs/AGENTS.md`
- Read: `docs/specs/v6/2026-05-04-v6-player-identity/design.md`
- Read: `docs/specs/v6/2026-05-04-v6-player-identity/sprint-plan.md`
- Read: `docs/retrospectives/v6/2026-05-05-v6-player-identity-handoff.md`
- Read: `docs/learnings/v6/2026-05-05-v6-player-identity-learnings.md`
- Read: `docs/specs/v7_roadmap.md`
- Cross-check source: `docs/specs/long-range-playable-roadmap.md` section "V7: Watchable Match Proof Loop"
- Prior handoff context: `docs/retrospectives/v5/2026-05-02-v5-weekly-command-center-handoff.md`

No standalone V6 Architect, Balance, UI, or QA reports were present before this sprint plan was written. The reports below were generated from current source inspection and targeted verification, then the V6 handoff/learnings docs were added during closeout.

## Generated Agent Report Synthesis

### Architect Report

V6 mechanics are materially present in code and are now formally closed in milestone documentation. `PlayerArchetype` and `tactical_iq` exist in `src/dodgeball_sim/models.py`; lineup liability logic exists in `src/dodgeball_sim/lineup.py`; V6 development focus exists in `src/dodgeball_sim/development.py`; engine liability effects exist in `src/dodgeball_sim/engine.py`; frontend command-center and roster surfaces expose some V6 fields.

Architectural risk: the V7 viewer currently consumes raw persisted match events through `GET /api/matches/{match_id}/replay`, and event context is already rich enough to support proof panels. Do not create a second replay truth source. V7 must derive viewer state, key-play navigation, and evidence summaries from persisted match events plus roster snapshots.

Closed implementation gap: `PlayerMatchStats.minutes_played` is now returned by `src/dodgeball_sim/stats.py`, persisted in schema version 13, included in stat aggregation, and reconstructed by the server. V7 can use reps, fatigue, and development as trusted evidence after the replay-proof view model is added.

### Balance Analyst Report

V6 liability effects are test-covered at the unit level in `tests/test_v6_player_identity.py`: liability warnings, AI lineup avoidance, development focus deltas, and fatigue multiplier behavior pass under Windows Python.

Balance risk: V7 must not tune outcomes. Its job is to expose match truth. New viewer labels may cite probabilities, rolls, fatigue, target selection, rush context, sync context, policy snapshots, and liability context only when those facts exist in event context. Any new engine context added for V7 must be observational unless a separate balance task and golden-log note explicitly approve outcome changes.

Balance blocker: V7 needs stronger tests that liability and tactics evidence appears in event payloads, not only that the underlying mechanic exists. The first V7 backend tasks must add replay-proof view models and tests before UI work.

### UI Engineer Report

The current React match replay is functional but not yet a proof loop. `frontend/src/components/MatchReplay.tsx` shows one event label, a simple detail line, probability/roll debug details, first key-play jump, and the match report. It does not show possession/state, live survivors by side, role/archetype context, fatigue context, target-selection rationale, or a list of key plays.

Closed implementation gap: `frontend/src/components/Roster.tsx` now aligns Role, Archetype, Age, OVR, Potential, Tactical IQ, Accuracy, Power, Dodge, Catch, and Stamina before V7 asks users to trust role/archetype evidence.

UI scope constraint: V7 should improve the existing replay cockpit, not create a new route, cinematic broadcast layer, physics engine, or mid-match coaching surface.

### QA Tester Report

Focused V6 verification command:

`/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_v6_player_identity.py -q`

Result: `4 passed`

WSL Python verification was blocked because `/usr/bin/python3` does not have `pytest` installed. Use Windows Python for the immediate implementation verification path unless the environment is refreshed.

QA risk: There is no dedicated V6 browser playthrough report. V7 implementation can start from this plan, but V7 cannot ship without its own browser playthrough gate.

## Project Trajectory

### WHERE WE WERE

V5 shipped the browser-first weekly loop: command center, staff recommendations, lineup/tactics accountability, post-week dashboard, command history, match replay handoff, and browser-playable offseason ceremony. V6 then added the player-identity layer: archetypes, Tactical IQ, lineup liabilities, AI lineup avoidance, liability engine penalties, and development focus.

### WHERE WE ARE

The current build is V6-closed in documentation and implementation, and V7-ready for feature sequencing. The code contains the V6 core mechanics, real reps persistence is closed, and the roster truth table is fixed. The existing match replay endpoint is a sound V7 foundation because it serves persisted event truth plus roster snapshots; the frontend replay cockpit is playable but too thin to prove tactics, fatigue, roles, and decisions.

Consensus readiness verdict: ready to begin V7 implementation at Task 3, the replay-proof backend view model. Task 1 and Task 2 are complete closeout work.

### WHERE WE ARE GOING

V7 scope is the Watchable Match Proof Loop:

`set plan -> watch/skim match -> inspect key plays -> read report -> adjust tactics/lineup`

Non-negotiable V7 scope:

- The replay viewer must expose simulation truth from persisted match events.
- The user must be able to inspect why key throws happened: target choice, odds, roll result, pressure/rush/sync context, fatigue context, and liability context where present.
- Key-play navigation must support more than the first elimination event.
- Fast result and acknowledge flow must remain available.
- Post-match report evidence must cite tactics, matchup fit, fatigue, and liabilities without inventing causes.
- The viewer must not change match outcomes.

Explicitly out of scope for V7:

- Mid-match coaching.
- Broadcast commentary.
- Camera-heavy presentation polish.
- Physics-heavy arcade behavior.
- New personality, morale, recruiting, promises, or program-credibility systems. These are V8 or later.

## Prerequisite Checklist

- [x] Close V6 documentation status before feature implementation:
  - Updated `docs/specs/MILESTONES.md` so V6 is marked shipped and V7 is the current next milestone.
  - Added `docs/retrospectives/v6/2026-05-05-v6-player-identity-handoff.md`.
  - Added `docs/learnings/v6/2026-05-05-v6-player-identity-learnings.md`.
  - Recorded focused verification and known thin spots in those docs.
- [x] Fix V6 reps persistence before any V7 evidence work:
  - `src/dodgeball_sim/stats.py` must return `minutes_played` from `extract_player_stats`.
  - `src/dodgeball_sim/persistence.py` must persist `minutes_played` in `player_match_stats`.
  - Schema migration and persistence tests must cover existing saves and new saves.
- [x] Fix V6 roster table truth before relying on role/archetype UI:
  - `frontend/src/components/Roster.tsx` headers and cells must align for Role, Archetype, Age, OVR, Potential, Tactical IQ, Accuracy, Power, Dodge, Catch, Stamina.
- [ ] Add a dedicated replay-proof backend view model before changing the frontend:
  - V7 UI must consume stable proof fields rather than parsing arbitrary nested event context in React.
- [ ] Run V6 focused tests and V7 replay tests after each backend task:
  - `/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_v6_player_identity.py tests/test_stats.py tests/test_persistence.py tests/test_server.py -q`
- [ ] Run frontend lint/build after each frontend task:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build`

## Atomic Task List

### Task 0: V6 Closeout Documentation

Status: Completed 2026-05-05.

Purpose: Establish a clean milestone boundary before V7 implementation.

Files:

- Modify: `docs/specs/MILESTONES.md`
- Create: `docs/retrospectives/v6/2026-05-05-v6-player-identity-handoff.md`
- Create: `docs/learnings/v6/2026-05-05-v6-player-identity-learnings.md`

Steps:

1. Update the milestone index so V6 is marked according to the accepted implementation status and V7 is the next planned milestone.
2. Write the V6 handoff with: shipped mechanics, verification command/result, closed thin spots, and V7 inheritance notes.
3. Write the V6 learnings with: code paths changed, test coverage added, hidden risks discovered, and guidance for V7 proof work.
4. Verify no implementation files changed in this task.

Acceptance:

- `docs/specs/MILESTONES.md` no longer contradicts the V6 implementation state.
- V6 handoff and learnings docs exist under versioned subfolders.
- `git diff -- src frontend tests` is empty for this task.

### Task 1: Repair V6 Reps Accounting

Status: Completed 2026-05-05.

Purpose: Make `minutes_played` real before V7 displays development or fatigue evidence.

Files:

- Modify: `src/dodgeball_sim/stats.py`
- Modify: `src/dodgeball_sim/persistence.py`
- Modify: `src/dodgeball_sim/server.py`
- Test: `tests/test_stats.py`
- Test: `tests/test_persistence.py`
- Test: `tests/test_server.py`

Steps:

1. Add a failing stats test proving an alive player receives positive `minutes_played` from a match event sequence.
2. Add a failing persistence test proving `player_match_stats.minutes_played` round-trips through schema creation and `save_player_stats_batch`.
3. Add a migration for `minutes_played INTEGER NOT NULL DEFAULT 0` on `player_match_stats`.
4. Include `minutes_played` in `save_player_stats_batch`.
5. Return `minutes_played` from `extract_player_stats`.
6. Update server-side stat reconstruction to read `minutes_played` where `PlayerMatchStats` is rebuilt from SQL rows.
7. Run `/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_stats.py tests/test_persistence.py tests/test_server.py tests/test_v6_player_identity.py -q`.

Acceptance:

- Existing saves migrate without crashing.
- New match stats rows contain positive minutes for active players.
- V6 development no longer relies on fallback practice reps for players who actually played.

### Task 2: Fix Roster Truth Table

Status: Completed 2026-05-05.

Purpose: Remove V6 UI ambiguity before V7 references roles and archetypes in replay evidence.

Files:

- Modify: `frontend/src/components/Roster.tsx`
- Modify: `frontend/src/types.ts`
- Test: verify with frontend lint/build and the V7 browser playthrough gate.

Steps:

1. Align table headers and cells exactly: Name, Role, Archetype, Age, OVR, Potential, Tactical IQ, Accuracy, Power, Dodge, Catch, Stamina.
2. Type the roster role field in `frontend/src/types.ts` so the frontend does not rely on untyped API payload fields.
3. Preserve starter sorting and compact rating bars.
4. Ensure mobile horizontal overflow remains usable through the existing `DataTable` shell.
5. Run `cd frontend && npm run lint`.
6. Run `cd frontend && npm run build`.

Acceptance:

- The roster table no longer labels archetype as age or Tactical IQ as accuracy.
- No new route or screen is introduced.

### Task 3: Backend Replay Proof View Model

Purpose: Provide stable V7 replay proof fields derived from persisted event truth.

Files:

- Create: `src/dodgeball_sim/replay_proof.py`
- Modify: `src/dodgeball_sim/server.py`
- Modify: `frontend/src/types.ts`
- Test: `tests/test_replay_proof.py`
- Test: `tests/test_server.py`

Steps:

1. Create a pure replay proof builder that accepts stored replay events, player name map, and roster snapshots.
2. For each throw event, derive:
   - `sequence_index`
   - `tick`
   - `thrower_id`
   - `thrower_name`
   - `target_id`
   - `target_name`
   - `resolution`
   - `is_key_play`
   - `proof_tags`
   - `summary`
   - `odds`
   - `rolls`
   - `fatigue`
   - `decision_context`
   - `tactic_context`
   - `liability_context`
3. Treat a key play as any throw event with resolution `hit`, `failed_catch`, or `catch`, plus any event that changes `state_diff.player_out`.
4. Do not compute new odds. Use existing event `probabilities`, `rolls`, and `context`.
5. Add a `proof_events` array and `key_play_indices` array to the replay API response.
6. Preserve the existing `events` array for compatibility.
7. Add tests proving proof fields are derived from stored event data and never require rerunning the engine.

Acceptance:

- `GET /api/matches/{match_id}/replay` still returns existing fields.
- New V7 fields are present for completed user matches.
- Tests cover rush context, sync context, fatigue context, and liability context when those keys exist.

### Task 4: Match State Timeline Summary

Purpose: Let the viewer show match state, not just event text.

Files:

- Modify: `src/dodgeball_sim/replay_proof.py`
- Modify: `src/dodgeball_sim/server.py`
- Test: `tests/test_replay_proof.py`

Steps:

1. Build a deterministic timeline reducer from event order and `state_diff.player_out`.
2. Track living player counts for both clubs at each proof event.
3. Track eliminated player ids by club at each proof event.
4. Include `score_state` on each proof event with home living count, away living count, and eliminated player ids.
5. Add tests for hit, catch, failed catch, dodge, and match-end events.

Acceptance:

- The timeline reducer never contradicts final `home_survivors` and `away_survivors`.
- Dodge and miss events do not change survivor counts.

### Task 5: Report Evidence Lanes

Purpose: Upgrade the match report from outcome summary to proof summary.

Files:

- Modify: `src/dodgeball_sim/replay_proof.py`
- Modify: `src/dodgeball_sim/server.py`
- Test: `tests/test_replay_proof.py`
- Test: `tests/test_server.py`

Steps:

1. Add `report.evidence_lanes` to the replay response.
2. Generate lanes for:
   - Result proof
   - Tactics proof
   - Fatigue proof
   - Liability proof
   - Key plays
3. Each lane must contain only facts from `proof_events`, `player_match_stats`, roster snapshots, or the saved command plan when a command history record exists for the match.
4. If a lane lacks evidence, show a plain limitation sentence instead of inventing a cause.
5. Add tests proving empty or missing context yields limitation copy, not fake diagnosis.

Acceptance:

- Match report evidence references concrete event ticks or player names.
- No lane claims a department-order effect unless persisted facts support it.

### Task 6: Frontend Replay Proof Layout

Purpose: Make the current replay cockpit visibly explain autonomous play.

Files:

- Modify: `frontend/src/components/MatchReplay.tsx`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/index.css`

Steps:

1. Add a proof timeline panel using `proof_events`.
2. Replace the single `Key Play` jump with a key-play list and next/previous key-play controls.
3. Show current proof event sections:
   - Outcome
   - Odds and rolls
   - Decision context
   - Tactic context
   - Fatigue
   - Liability
4. Show survivor counts from `score_state`.
5. Keep Back, Next, Continue, and fast result flow intact.
6. Add stable CSS dimensions for the proof timeline and key-play list so changing event text does not resize the replay layout.
7. Use compact panels, not a new landing page or broadcast page.
8. Run `cd frontend && npm run lint`.
9. Run `cd frontend && npm run build`.

Acceptance:

- User can inspect multiple key plays without stepping one event at a time.
- The UI distinguishes tracked evidence from unavailable evidence.
- Existing acknowledge flow still works.

### Task 7: Command Center To Replay Continuity

Purpose: Connect V5/V6 decisions to V7 evidence.

Files:

- Modify: `src/dodgeball_sim/command_center.py`
- Modify: `src/dodgeball_sim/server.py`
- Modify: `frontend/src/components/CommandCenter.tsx`
- Modify: `frontend/src/components/MatchReplay.tsx`
- Test: `tests/test_command_center.py`
- Test: `tests/test_server.py`

Steps:

1. Include saved command-plan context in replay evidence when the replayed match belongs to a command-center simulated user week.
2. Show plan intent, dev focus, and tactics settings in the replay report evidence lanes.
3. Link the post-week dashboard match id to the replay view where the current app flow supports it.
4. Ensure bulk-simmed neutral matches do not pretend to have a user command plan.
5. Add tests for a command-center simulated match and a non-command match.

Acceptance:

- V7 closes the loop from selected plan to match proof to next adjustment.
- Replay evidence remains accurate when command history is absent.

### Task 8: Browser Playthrough Gate

Purpose: Verify V7 is playable by a human and by an automated browser agent.

Files:

- Create: `docs/retrospectives/v7/2026-05-05-v7-playthrough-qa.md`
- Modify: `docs/specs/MILESTONES.md` only after all V7 gates pass

Steps:

1. Start the web app in dev mode.
2. In the browser, load a save or fresh career.
3. Set a command-center plan.
4. Simulate a user match.
5. Open replay proof.
6. Navigate at least three key plays.
7. Inspect tactic, fatigue, and liability evidence.
8. Acknowledge the report.
9. Record issues and screenshots or textual observations in the V7 QA doc.
10. Run backend and frontend verification commands listed in the prerequisite checklist.

Acceptance:

- Browser flow completes without external instructions.
- V7 QA doc states pass/fail for Functional, Playable, AI Playthrough, Simulation Honesty, and Documentation gates.
- `docs/specs/MILESTONES.md` is updated to V7 shipped only if all gates pass.

## Scope Creep Prevention

Push to V8:

- Recruiting promises based on proof history.
- Program credibility effects.
- Prospect fit dashboards.
- Personality, morale, leadership chemistry, or player relationship systems.

Push to V9 or later:

- Broadcast commentary.
- Animated camera systems.
- Physics-heavy court simulation.
- Mid-match coaching and tactical substitutions.

Reject for V7 unless separately approved:

- Any outcome-affecting balance change.
- Any second event-log format that competes with persisted `MatchEvent`.
- Any UI claim that cannot cite event context, player stats, roster snapshot, or saved command history.

## Handoff Instructions

Implementation Agent Task 3 prompt:

You are implementing Task 3 from `docs/specs/2026-05-05-v7-sprint-plan.md` in `C:\GPT5-Projects\Dodgeball Simulator`. V6 prerequisite stabilization is complete; do not revisit reps persistence or roster table alignment unless tests fail directly in those areas. Build the backend replay-proof view model first. Read `docs/specs/MILESTONES.md`, `docs/specs/2026-05-05-v7-sprint-plan.md`, `src/dodgeball_sim/server.py`, current replay endpoint tests, and the persisted `MatchEvent` shape. Create `src/dodgeball_sim/replay_proof.py`, add tests in `tests/test_replay_proof.py`, and expose proof fields from `GET /api/matches/{match_id}/replay` without removing the existing `events` payload. Use only stored event context, roster snapshots, player stats, and command history; do not rerun the engine and do not change match outcomes. Verify with Windows Python: `/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_replay_proof.py tests/test_server.py tests/test_v6_player_identity.py -q`.

## Verification Notes

Already run during planning:

- `/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_v6_player_identity.py -q`
- Result: `4 passed`

Run during V6 implementation closeout:

- `/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_stats.py tests/test_persistence.py tests/test_server.py tests/test_command_center.py tests/test_v2a_scouting_persistence.py tests/test_v2b_recruitment_persistence.py tests/test_v6_player_identity.py -q`
- Result: pass
- `npm run lint` from `frontend/` via Windows Node 24.15.0
- Result: pass
- `npm run build` from `frontend/` via Windows Node 24.15.0
- Result: pass

Not run during closeout:

- Full Python suite.
- Browser playthrough.

Those remain assigned to the V7 implementation and closeout gates above.
