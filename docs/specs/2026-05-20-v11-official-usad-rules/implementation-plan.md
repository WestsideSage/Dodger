# V11 Official USA Dodgeball Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an official USA Dodgeball 2026.1 rules layer for Dodger with deterministic match/game lifecycle, ball state, player state, burden clocks, catch queues, no-blocking, and replay-visible rule explanations.

**Architecture:** Add focused rules modules beside the current engine, then route official-rules matches through an adapter while preserving the current engine for existing saves and tests. Keep event logs canonical and expose every rule outcome through replay payloads.

**Tech Stack:** Python dataclasses and pure domain helpers, SQLite persistence via existing `persistence.py`, FastAPI use-case integration, React/TypeScript replay and match-week UI, pytest and Playwright.

---

## File Structure

- Create `src/dodgeball_sim/official_events.py`: shared official event envelope, rule references, version fields, and replay summaries.
- Create `src/dodgeball_sim/rule_discretion.py`: deterministic ambiguous-call records used by burden, sequence, catch, and undocumented-rule handling from the start.
- Create `src/dodgeball_sim/rulesets.py`: official ruleset profiles and material/division constants.
- Create `src/dodgeball_sim/match_lifecycle.py`: match/game state machine, timing, scoring, overtime, and no-blocking transitions.
- Create `src/dodgeball_sim/ball_state.py`: ball entities, activation, liveness, ownership, retrieval, replacement, and forfeiture.
- Create `src/dodgeball_sim/player_state.py`: official player state and setup validation.
- Create `src/dodgeball_sim/sequence.py`: sequence-of-play records and finality resolver.
- Create `src/dodgeball_sim/burden.py`: burden establishment and throw-clock enforcement.
- Create `src/dodgeball_sim/catch_queue.py`: FIFO queue, entering-player deadlines, and re-entry restrictions.
- Create `src/dodgeball_sim/no_blocking.py`: no-blocking transition and contact-resolution helpers.
- Create `src/dodgeball_sim/official_actions.py`: proactive action generation/selection for engine ticks and reactive action modeling for sequence/live-ball resolution.
- Create `src/dodgeball_sim/replay_contracts.py`: backend official replay payload contract before frontend work.
- Create `src/dodgeball_sim/discipline.py`: warning and blue-card state, with future hooks for yellow/red persistence.
- Create `src/dodgeball_sim/official_engine.py`: official-rules orchestration adapter.
- Modify `src/dodgeball_sim/engine.py`: expose a stable adapter boundary without changing default behavior.
- Modify `src/dodgeball_sim/events.py` and `src/dodgeball_sim/event_types.py`: add typed official event contexts.
- Modify `src/dodgeball_sim/game_loop.py` and `src/dodgeball_sim/use_cases.py`: select official engine for official ruleset matches only.
- Modify `src/dodgeball_sim/persistence.py`: add schema fields/tables only after state model stabilizes.
- Modify `src/dodgeball_sim/stats.py`, `src/dodgeball_sim/replay_service.py`, and `src/dodgeball_sim/replay_proof.py`: derive official stats and replay proof.
- Modify `frontend/src/types.ts`, `frontend/src/components/MatchReplay.tsx`, and `frontend/src/components/MatchWeek.tsx`: display official state.
- Add tests under `tests/test_official_*.py` plus targeted frontend/e2e tests once payloads exist.

## Conformance Matrix

Every implementation PR must update a rule-to-test matrix. The initial matrix should live in `tests/test_official_conformance_matrix.py` and assert that every V11 must-have or partial/core subset section has at least one named test file.

| Rule section | V11 scope | Minimum test home |
|---:|---|---|
| 1 | Must-have | `tests/test_official_rulesets.py` |
| 4 | Must-have | `tests/test_official_rulesets.py` |
| 6 | Must-have | `tests/test_official_match_lifecycle.py` |
| 9 | Must-have | `tests/test_official_match_lifecycle.py` |
| 11 | Must-have | `tests/test_official_ball_state.py` |
| 13 | Must-have | `tests/test_official_burden.py` |
| 14 | Must-have | `tests/test_official_burden.py` |
| 16 | Must-have | `tests/test_official_ball_state.py` |
| 17 | Must-have | `tests/test_official_actions.py` and `tests/test_official_sequence.py` |
| 18 | Must-have | `tests/test_official_sequence.py` |
| 20 | Must-have | `tests/test_official_sequence.py` |
| 21 | Must-have | `tests/test_official_sequence.py` and `tests/test_official_no_blocking.py` |
| 22 | Must-have | `tests/test_official_sequence.py` and `tests/test_official_catch_queue.py` |
| 23 | Must-have | `tests/test_official_catch_queue.py` |
| 24-core | Partial/core subset | `tests/test_official_ball_state.py` and `tests/test_official_catch_queue.py` |
| 25 | Must-have | `tests/test_official_sequence.py` |
| 27 | Must-have | `tests/test_official_no_blocking.py` |

## Phase 1: Shared Events, Discretion, Ruleset Profile, And Setup Validation

**Safe PR slice:** Add shared official event/discretion infrastructure plus official ruleset configuration and setup validation without changing match outcomes.

**Affected files:**

- Create `src/dodgeball_sim/official_events.py`
- Create `src/dodgeball_sim/rule_discretion.py`
- Create `src/dodgeball_sim/rulesets.py`
- Create `src/dodgeball_sim/player_state.py`
- Modify `src/dodgeball_sim/models.py`
- Test `tests/test_official_rulesets.py`
- Test `tests/test_official_events.py`
- Test `tests/test_rule_discretion.py`

**New types/interfaces:**

- `OfficialEvent`
- `OfficialEventKind`
- `RuleReference`
- `OfficialPayloadVersion`
- `RuleDiscretionEvent`
- `BallMaterial`: `FOAM`, `NO_STING`, `CLOTH`
- `DivisionType`: `OPEN`, `WOMEN`, `MIXED`
- `RulesetProfile`
- `CourtProfile`
- `OfficialRosterRule`
- `OfficialSetupValidationError`

**Tests to add:**

- Foam/no-sting profiles instantiate six balls and burden majority threshold four.
- Cloth profile instantiates five balls and burden majority threshold three.
- Mixed starters reject four players of one gender.
- Mixed starters allow 3-2 when only two players of one gender are available.
- Current generic `MatchSetup` remains valid and unchanged.
- `OfficialEvent` includes `ruleset_version`, `rulebook_version`, `official_payload_version`, optional `game_id`, optional `sequence_id`, rule references, payload, and replay summary.
- `RuleDiscretionEvent` serializes as an `OfficialEvent` with deterministic default ruling and selected ruling.

**Migration/save risks:**

- No schema migration in this phase.
- Do not add required fields to existing saved matches.
- Any new setup option must default to the current generic ruleset.
- Version fields must be present from the first official event so later persistence does not need to infer old payload formats.

**Replay/UI requirements:**

- None beyond optional ruleset label plumbing.

**Acceptance criteria:**

- `python -m pytest tests/test_official_rulesets.py -q` passes.
- `python -m pytest tests/test_official_events.py tests/test_rule_discretion.py -q` passes.
- Existing `python -m pytest tests/test_phase3_engine.py tests/test_lineup.py -q` still passes.
- No existing match outcome changes.

## Phase 2: Match And Game Lifecycle

**Safe PR slice:** Introduce match/game state machines and scoring in isolation.

**Affected files:**

- Create `src/dodgeball_sim/match_lifecycle.py`
- Modify `src/dodgeball_sim/scheduler.py`
- Modify `src/dodgeball_sim/playoffs.py`
- Test `tests/test_official_match_lifecycle.py`

**New types/interfaces:**

- `OfficialMatchState`
- `OfficialGameState`
- `OfficialMatchClock`
- `OfficialGameResult`
- `OfficialMatchScore`
- `OfficialRoundType`

**Tests to add:**

- Round-robin foam/no-sting game reaches no-blocking at 180 seconds.
- Round-robin foam/no-sting match-end no-blocking resets balls three per side and awards no point if no winner.
- Cloth game at 180 seconds awards the game to the team with more active players or records a tie.
- Cloth final 90-second game starts when less than 90 seconds remain after a game.
- Bracket round durations are 24, 30, and 40 minutes by round type.

**Migration/save risks:**

- Persist lifecycle only after official engine is active.
- Existing top-four playoff records stay compatible.
- `scheduler.py` and `playoffs.py` may receive pure helper additions only. Do not change actual schedule generation, playoff creation, seeding, advancement, or persisted behavior until Phase 8D routing explicitly selects the official ruleset path.

**Replay/UI requirements:**

- Payload shape for `match_clock`, `game_clock`, `game_number`, `game_score`, and `mode`.

**Acceptance criteria:**

- Lifecycle tests pass without calling `MatchEngine.run()`.
- Existing playoff tests still pass.
- The plan explicitly leaves full USAD bracket expansion as a later PR if it exceeds V11 scope.

## Phase 3: Replay Contract Draft

**Safe PR slice:** Define the backend official replay payload shape before official engine composition or frontend work.

**Affected files:**

- Create `src/dodgeball_sim/replay_contracts.py`
- Modify `src/dodgeball_sim/official_events.py`
- Test `tests/test_official_replay_contracts.py`

**New types/interfaces:**

- `OfficialReplayState`
- `OfficialClockView`
- `OfficialGameScoreView`
- `OfficialBurdenView`
- `OfficialBallView`
- `OfficialTeamStateView`
- `OfficialSequenceView`
- `OfficialRuleCallView`

**Tests to add:**

- Empty official replay state serializes with `ruleset`, `rulebook_version`, and `official_payload_version`.
- Replay state accepts match clock, game clock, game score, mode, burden, balls, teams, player statuses, active sequences, and rule calls.
- Old generic replay payloads remain valid because official replay state is optional.

**Migration/save risks:**

- No persistence changes.
- This is a contract draft; do not build frontend UI in this phase.

**Replay/UI requirements:**

- Lock backend field names before official events start flowing through persistence.

**Acceptance criteria:**

- `python -m pytest tests/test_official_replay_contracts.py -q` passes.
- Later official modules can reference `OfficialReplayState` without importing frontend-specific types.

## Phase 4: Ball State And Activation

**Safe PR slice:** Add ball entities and activation rules without full throw resolution.

**Affected files:**

- Create `src/dodgeball_sim/ball_state.py`
- Modify `src/dodgeball_sim/rulesets.py`
- Test `tests/test_official_ball_state.py`

**New types/interfaces:**

- `OfficialBall`
- `BallState`
- `BallOwnership`
- `BallActivationPayload`
- `BallForfeitPayload`
- `BallReplacementPayload`

**Tests to add:**

- Foam/no-sting starts with three designated inactive balls per side.
- Cloth starts with two designated balls per side and one neutral center ball.
- A ball becomes active only after fully crossing the attack line.
- Throwing an inactive ball marks the thrower out and keeps the ball inactive.
- Retrieved balls affect burden even while held by retrievers.
- Section 24-core: balls cannot be held in the queue, and entering-player ball contact before live status creates a deterministic forfeiture/out event.

**Migration/save risks:**

- Ball state can live inside official match event payloads first; avoid schema tables until replay persistence needs them.

**Replay/UI requirements:**

- Replay payload includes ball count by state and rule call for inactive-ball throw.

**Acceptance criteria:**

- Ball state tests cover Sections 1, 8, 10, 11, 16, and 24-core at state level.
- No default engine result changes.

## Phase 5: Player State And Catch Queue

**Safe PR slice:** Implement official player lifecycle and queue operations.

**Affected files:**

- Create `src/dodgeball_sim/catch_queue.py`
- Modify `src/dodgeball_sim/player_state.py`
- Modify `src/dodgeball_sim/stats.py`
- Test `tests/test_official_catch_queue.py`

**New types/interfaces:**

- `OfficialPlayerStatus`
- `CatchQueueState`
- `EnteringPlayerState`
- `QueueRuleViolation`

**Tests to add:**

- Catch returns the first eligible queued player.
- Non-starters cannot enter from catches.
- Out-of-order entry sends the player to the back and returns no player from that catch.
- Entering player must enter along the back line within 5 seconds.
- A player involved in the same sequence cannot become the entering player from that sequence.
- Section 24-core: queued players cannot hold balls, and entering players cannot carry, roll, or intentionally touch a ball before becoming live.

**Migration/save risks:**

- Stats currently set `revivals_caused=0`; official catches will change stats once enabled. Gate changes behind official ruleset.

**Replay/UI requirements:**

- Replay and MatchWeek payloads expose active, queued, entering, and unavailable players.

**Acceptance criteria:**

- Catch queue behavior is pure and deterministic.
- Existing stat extraction for generic matches is unchanged.

## Phase 6: Sequence Of Play Resolver

**Safe PR slice:** Resolve hits, catches, delayed outs, and clock-expired throws through event sequences.

**Affected files:**

- Create `src/dodgeball_sim/sequence.py`
- Modify `src/dodgeball_sim/official_events.py`
- Modify `src/dodgeball_sim/events.py`
- Modify `src/dodgeball_sim/event_types.py`
- Modify `src/dodgeball_sim/stats.py`
- Test `tests/test_official_sequence.py`

**New types/interfaces:**

- `SequenceOfPlay`
- `SequenceContact`
- `PendingOut`
- `CatchResolution`
- `SequenceFinalRuling`

**Tests to add:**

- A hit does not become final until the ball completes its sequence.
- A teammate catch of a ricochet saves hit players in foam/no-sting.
- Cloth ricochet catch does not save the hit player when the rule says they are not safe.
- A valid catch after clock expiry still eliminates the thrower and returns a player.
- A player hit by a second ball can become out before the first ball sequence completes.
- Simultaneous catches are resolved deterministically by control timing.

**Migration/save risks:**

- Event payload grows substantially. Store compact event records and derive replay views.
- Golden logs must be updated only when official engine is turned on for default play.

**Replay/UI requirements:**

- Replay shows sequence id, pending rulings, final rulings, and rule references.

**Acceptance criteria:**

- Sequence tests cover Sections 18, 20, 21, 22, 25, and 26.
- No hidden outcome mutation outside sequence finalization.

## Phase 7: Burden And Throw Clock

**Safe PR slice:** Implement burden establishment and clock penalties.

**Affected files:**

- Create `src/dodgeball_sim/burden.py`
- Modify `src/dodgeball_sim/ball_state.py`
- Modify `src/dodgeball_sim/player_state.py`
- Modify `src/dodgeball_sim/rule_discretion.py`
- Test `tests/test_official_burden.py`

**New types/interfaces:**

- `BurdenState`
- `BurdenBasis`
- `ThrowClockState`
- `PlayNBallsCall`
- `ThrowClockPenalty`
- `ClothReachableBallRuling`

**Tests to add:**

- Foam/no-sting burden uses ball majority, then player majority, then previous burden inversion.
- Foam/no-sting valid throw resets burden.
- Foam/no-sting failure at zero forfeits all balls to the opponent.
- Cloth equal-ball burden uses explicit reachable-ball discretion event.
- Cloth "play n balls" calculates `n` as one fewer than controlled balls, capped by live players.
- Cloth failure calls out ball controllers first, then captain-selected additional players.
- Player eliminated before attempting counts controlled balls as thrown for play-n purposes.

**Migration/save risks:**

- Throw-clock state should be event-sourced before any new persistence table.

**Replay/UI requirements:**

- HUD/replay exposes burden holder, countdown, play-n call, thrown count, and penalty reason.

**Acceptance criteria:**

- Burden tests cover Sections 13 and 14 and remain independent of the full engine.
- Referee/captain selections are deterministic or explicit user/AI choices.

## Phase 8A: No-Blocking And Scripted Official Engine

**Safe PR slice:** Add no-blocking resolution and a scripted engine harness that consumes predetermined legal actions. Do not build autonomous action selection yet.

**Affected files:**

- Create `src/dodgeball_sim/no_blocking.py`
- Create `src/dodgeball_sim/official_engine.py`
- Modify `src/dodgeball_sim/official_events.py`
- Test `tests/test_official_no_blocking.py`
- Test `tests/test_official_engine_scripted.py`

**New types/interfaces:**

- `NoBlockingState`
- `ScriptedOfficialAction`
- `OfficialEngineStep`
- `OfficialEngineResult`

**Tests to add:**

- No-blocking treats held balls as body extensions and logs the source rule.
- Scripted foam/no-sting game can process activation, valid throw, catch, and queue return.
- Scripted cloth game can reach game-clock decision by active-player count.
- Scripted engine emits only `OfficialEvent` envelopes.

**Migration/save risks:**

- No route changes and no persistence changes.

**Replay/UI requirements:**

- Scripted results can be converted into `OfficialReplayState` v0 in memory.

**Acceptance criteria:**

- Scripted engine tests pass without importing `game_loop.py` or frontend code.
- No autonomous engine behavior exists in this slice.

## Phase 8B: Official Event Serialization

**Safe PR slice:** Persist and reload official event envelopes for scripted official matches.

**Affected files:**

- Modify `src/dodgeball_sim/persistence.py`
- Modify `src/dodgeball_sim/replay_service.py`
- Modify `src/dodgeball_sim/replay_proof.py`
- Test `tests/test_official_event_persistence.py`
- Test `tests/test_official_replay_payload.py`

**New types/interfaces:**

- `OfficialStoredEvent`
- `OfficialMatchRecordMetadata`

**Tests to add:**

- Official events round-trip with `ruleset_version`, `rulebook_version`, and `official_payload_version`.
- Generic match events still round-trip unchanged.
- Replay service can produce `OfficialReplayState` v0 from stored official events.

**Migration/save risks:**

- Add nullable/optional metadata only.
- Do not require existing match rows to have official fields.

**Replay/UI requirements:**

- Backend replay payload is available before frontend renders it.

**Acceptance criteria:**

- Persistence tests pass for both generic and official events.
- No default career route uses official persistence yet.

## Phase 8C: Proactive And Reactive Actions

**Safe PR slice:** Add proactive action generation/selection and reactive action modeling outside `official_engine.py`.

**Affected files:**

- Create `src/dodgeball_sim/official_actions.py`
- Modify `src/dodgeball_sim/official_engine.py`
- Test `tests/test_official_actions.py`

**New types/interfaces:**

- `OfficialAction`
- `ProactiveAction`
- `ReactiveAction`
- `ThrowAction`
- `RetrieveAction`
- `EnterCourtAction`
- `WaitAction`
- `CatchAttemptAction`
- `DodgeAction`
- `BlockAction`
- `LegalActionGenerator`
- `ActionSelector`

**Tests to add:**

- Legal proactive action generator excludes inactive, queued, suspended, and not-yet-live entering players.
- Burden and throw clock constrain proactive throw/wait actions.
- Reactive catch, dodge, and block actions are requested only during active sequence/live-ball resolution.
- Action selector is deterministic for the same seed and state.
- `CoachPolicy` and player ratings influence selection without hidden boosts.

**Migration/save risks:**

- No persistence changes.

**Replay/UI requirements:**

- Selected proactive actions and resolved reactive actions emit replay summaries through `OfficialEvent`.

**Acceptance criteria:**

- `official_engine.py` delegates proactive action choice and sequence modules resolve reactive actions, so the engine does not become a rules/tactics god object.
- Determinism tests pass.

## Phase 8D: Game Loop Routing And Feature Flag

**Safe PR slice:** Wire the autonomous official path into game simulation behind an explicit ruleset selector or feature flag.

**Affected files:**

- Modify `src/dodgeball_sim/engine.py`
- Modify `src/dodgeball_sim/game_loop.py`
- Modify `src/dodgeball_sim/use_cases.py`
- Modify `src/dodgeball_sim/persistence.py`
- Test `tests/test_official_game_loop_routing.py`

**New types/interfaces:**

- `RulesetSelection`
- `OfficialEngineAdapter`

**Tests to add:**

- Existing generic careers still use `MatchEngine.run()`.
- Official ruleset matches use `OfficialMatchEngine`.
- Existing `MatchEngine.run()` remains the default for non-official setup.
- Feature flag/ruleset selector can be changed only at a safe boundary.

**Migration/save risks:**

- Do not switch existing careers to official engine automatically.
- Existing careers should stay generic unless explicitly opted in at new-season boundary.

**Replay/UI requirements:**

- Official route returns replay payloads matching `OfficialReplayState` v0.

**Acceptance criteria:**

- Focused routing tests pass.
- Full Python suite passes before any default route changes.

## Phase 9: Replay, UI, And Browser Verification

**Safe PR slice:** Make official rules visible and diagnosable in the browser.

**Affected files:**

- Modify `src/dodgeball_sim/replay_service.py`
- Modify `src/dodgeball_sim/replay_proof.py`
- Modify `frontend/src/types.ts`
- Modify `frontend/src/components/MatchReplay.tsx`
- Modify `frontend/src/components/MatchWeek.tsx`
- Add `tests/e2e/official-rules-replay.spec.ts`

**New types/interfaces:**

- Consume `OfficialReplayState` from Phase 3; do not redefine it here.
- `OfficialRuleCallView`
- `OfficialGameScoreView`
- `OfficialQueueView`

**Tests to add:**

- API replay payload includes clocks, game score, burden, queue, ball states, and rule calls for official matches.
- Replay UI renders no-blocking and catch-entry events.
- Browser smoke test navigates through an official match replay without console errors.

**Migration/save risks:**

- Frontend/API views must adapt to the Phase 3 `OfficialReplayState` contract while still accepting old generic replay payloads.

**Replay/UI requirements:**

- No official outcome may appear only as backend data. The replay needs visible rule explanation.

**Acceptance criteria:**

- `npm run build` passes.
- Relevant Playwright smoke passes.
- Generic match replay still renders.

## Phase 10: Discipline

**Safe PR slice:** Add visible warnings and blue cards using the existing official event and discretion infrastructure. Keep yellow/red carryover behind future work unless persistence is ready.

**Affected files:**

- Create `src/dodgeball_sim/discipline.py`
- Modify `src/dodgeball_sim/official_engine.py`
- Modify `src/dodgeball_sim/replay_service.py`
- Test `tests/test_official_discipline.py`

**New types/interfaces:**

- `WarningRecord`
- `BlueCardRecord`
- `DisciplineState`

**Tests to add:**

- Repeated warning for same player/offense upgrades to blue card.
- Blue card moves live player to back of queue.
- Blue card to only remaining live player forfeits the game.
- Same-offense second blue card upgrades to yellow-card placeholder event.
- Card events reuse `OfficialEvent` and existing `RuleReference`.

**Migration/save risks:**

- Yellow/red suspension persistence should be a separate future PR because it touches tournament/career availability.

**Replay/UI requirements:**

- Rule call cards show warning/card type and section reference.

**Acceptance criteria:**

- Discipline behavior is deterministic and visible.
- Future yellow/red persistence is explicitly deferred, not silently ignored.

## Phase 11: Integration Hardening And Scope Lock

**Safe PR slice:** Final verification, documentation, and default-selection decision.

**Affected files:**

- Modify `docs/STATUS.md`
- Modify `docs/specs/MILESTONES.md`
- Add retrospective and learnings only when V11 ships.
- Update `docs/rules/usad-2026.1-rule-matrix-audit.md` if implementation uncovers new rule gaps.

**Tests to add:**

- Full `python -m pytest -q`
- `npm run build`
- `npm run lint`
- Root Playwright smoke checks when official replay UI is active

**Migration/save risks:**

- If official rules become default for new careers, add a save-state compatibility note and a one-way ruleset field migration.
- Existing careers should either remain generic or opt into official rules at a new-season boundary.

**Replay/UI requirements:**

- A user can inspect why each official-rules outcome happened from the match replay without reading the source.

**Acceptance criteria:**

- The official-rules path is tested, visible, deterministic, and opt-in/defaulted by explicit product decision.
- All deferred rules are listed as future advanced realism, administrative/flavor, or not applicable.
- No single giant rules blob exists.
