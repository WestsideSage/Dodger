# V11 Official USA Dodgeball Rules Design

## Relation To Prior Specs

V11 follows the post-V10 playable web product described in `docs/specs/MILESTONES.md` and inherits the integrity contract in `docs/specs/AGENTS.md`.

This spec supersedes the current generic match-loop assumptions for future official-rules work only. It does not supersede shipped V1-V10 franchise, scouting, replay, or Dynasty Office behavior. It also does not implement engine changes yet.

V11 uses `docs/specs/usa_dodgeball_2026_extraction_matrix.md` as the source extraction layer after the audit in `docs/rules/usad-2026.1-rule-matrix-audit.md`.

Source precedence for V11 official-rules work is:

1. Official PDF: `docs/sources/USA-Dodgeball-2026-Rulebook.pdf`
2. Audit corrections: `docs/rules/usad-2026.1-rule-matrix-audit.md`
3. Gemini matrix: `docs/specs/usa_dodgeball_2026_extraction_matrix.md`
4. This design and the implementation plan

Historical note: this document preserves the pre-implementation design baseline.
For shipped behavior, verification status, and any narrow post-design adjustments,
prefer `docs/STATUS.md`, `docs/specs/MILESTONES.md`, source, and tests.

## Goal

Integrate official USA Dodgeball 2026.1 rules into Dodger through deterministic, replay-explainable domain models rather than hidden randomness, broad physics guesses, or a single giant rules blob.

## Non-Goals

- Do not implement in this planning pass.
- Do not rewrite the full engine in one PR.
- Do not model every administrative tournament rule in V11.
- Do not add hidden referee bias, hidden AI boosts, or animation-driven outcomes.
- Do not flatten foam, no-sting, and cloth into one generic dodgeball ruleset.

## Source Findings

The matrix covers all numbered sections 1-41 at heading level. It still needs correction before implementation:

- Mixed-division starters must not include four players of one gender.
- Cloth throw-clock penalties need controller tracking and captain/official out selection.
- Hit/catch/out outcomes need sequence finality instead of immediate boolean resolution.
- Ball retrieval and player-entry clauses affect burden, forfeitures, and outs.
- Referee-discretion clauses must be explicit events, not hidden probability.

## Current Repo Reality

The current engine in `src/dodgeball_sim/engine.py` is a deterministic throw-resolution loop. It chooses one thrower, one target, resolves dodge/hit/catch immediately, toggles `is_out`, and ends when one team has no living players or limits are reached.

Useful existing foundations:

- `MatchEngine.run()` already emits canonical `MatchEvent` records.
- `MatchResult.winner_team_id`, box score extraction, replay payloads, and stats are event-derived.
- `CoachPolicy` already carries tactics that can later influence official-rules action selection.
- Persistence already stores match records, events, stats, roster snapshots, standings, playoffs, and career state.

Insufficient abstractions:

- No match-vs-game lifecycle.
- No material/division ruleset config.
- No ball entities or ball ownership.
- No opening rush or activation state.
- No burden or throw clock.
- No sequence-of-play resolver.
- No catch/re-entry queue.
- No no-blocking mode.
- No formal referee-discretion or discipline model.
- No multi-ball simultaneous event model.
- No mixed-division gender constraints in match setup.

## Architecture

V11 should add a rules package beside the current engine and migrate behavior behind explicit seams.

Proposed files:

- `src/dodgeball_sim/official_events.py`: shared official event envelope, rule references, payload versioning, and replay summary fields used by all rules modules.
- `src/dodgeball_sim/rule_discretion.py`: explicit ambiguous-call records with rule reference, default ruling, selected ruling, and replay text. This exists early because burden, sequence, catch, and undocumented-rule handling need it before discipline.
- `src/dodgeball_sim/rulesets.py`: immutable official ruleset profiles for foam, no-sting, cloth, open, women, and mixed.
- `src/dodgeball_sim/match_lifecycle.py`: match, game, overtime, no-blocking, and late-start state transitions.
- `src/dodgeball_sim/ball_state.py`: ball entity, ownership, activation, liveness, retrieval, forfeiture, and replacement.
- `src/dodgeball_sim/player_state.py`: official player statuses, queue status, entry status, and card availability.
- `src/dodgeball_sim/sequence.py`: sequence-of-play ledger and deterministic finality resolver.
- `src/dodgeball_sim/burden.py`: burden establishment, clock state, foam/no-sting reset, cloth play-n-balls enforcement.
- `src/dodgeball_sim/catch_queue.py`: FIFO out queue, catch returns, entering-player windows, same-sequence restrictions.
- `src/dodgeball_sim/official_actions.py`: proactive action generation/selection for engine ticks and reactive action modeling for sequence/live-ball resolution.
- `src/dodgeball_sim/replay_contracts.py`: backend-only official replay payload contract before frontend work begins.
- `src/dodgeball_sim/discipline.py`: warnings, blue/yellow/red card domain records and deterministic effects.
- `src/dodgeball_sim/official_engine.py`: orchestration adapter that composes the above modules.

Existing files should integrate through small adapters:

- `src/dodgeball_sim/engine.py`: preserve current behavior until the official engine is explicitly selected.
- `src/dodgeball_sim/models.py`: add minimal setup references only if needed; avoid dumping official state into base `Team`.
- `src/dodgeball_sim/game_loop.py`: choose official engine for V11 ruleset matches.
- `src/dodgeball_sim/stats.py`: derive official stats from new event types.
- `src/dodgeball_sim/replay_service.py` and `src/dodgeball_sim/replay_proof.py`: expose official events and rule explanations.
- `frontend/src/types.ts`, `frontend/src/components/MatchReplay.tsx`, `frontend/src/components/MatchWeek.tsx`: show match/game clocks, game score, burden, no-blocking, queue, and rule calls.

## Durable Domain Models

### Shared Official Event Envelope

Every V11 rules module emits through `OfficialEvent` rather than inventing local event shapes.

`OfficialEvent`:

- `event_id`
- `official_payload_version`
- `ruleset_version`
- `rulebook_version`
- `kind`
- `match_id`
- `game_id`
- `sequence_id`
- `ball_ids`
- `player_ids`
- `team_ids`
- `rule_refs`
- `payload`
- `replay_summary`

`RuleReference` stores section and optional clause labels, for example `14.g.4` or `22.b.xiii`. This keeps ball, player, burden, sequence, queue, and discipline modules from drifting into incompatible event payloads.

### Match Vs Game Lifecycle

`OfficialMatchState`:

- `scheduled`
- `pre_match_validation`
- `side_selection`
- `game_setup`
- `opening_rush`
- `game_live`
- `game_stoppage`
- `no_blocking`
- `overtime`
- `sudden_death`
- `match_complete`

`OfficialMatch` owns:

- match clock limit, elapsed match seconds, match score by games/points
- material profile
- round type: round robin, standard bracket, semifinal, final
- ordered `OfficialGame` records
- late-start awarded games

`OfficialGame` owns:

- game number, game clock limit, elapsed game seconds
- starting side, starting players, starting balls
- game result: team win, tie, forfeit, no point
- mode: standard, no-blocking, overtime, sudden death

### Ball States

`BallState`:

- `inactive_center`
- `activated_free`
- `held`
- `live_in_flight`
- `blocked_live`
- `ricochet_live`
- `dead`
- `retrieved`
- `forfeited`
- `contaminated`
- `replaced`

Each ball needs stable `ball_id`, material, side, controller player id, last thrower id, activation status, sequence id, and court side. Burden calculations use ball control and reachable dead balls, not generic possession.

### Player States

`OfficialPlayerState`:

- `active`
- `hit_pending`
- `exiting`
- `queued`
- `entering`
- `inactive_nonstarter`
- `injured`
- `blue_card_queue`
- `yellow_card_removed`
- `red_card_removed`
- `suspended`
- `ejected`

Player state must track whether the player is live for hits, eligible for catches, eligible for re-entry, involved in the current sequence, and holding/controlling balls.

### Sequence Of Play

`SequenceOfPlay` begins with a live valid throw and ends when the involved ball is dead or caught. It records:

- sequence id and parent game id
- thrower, ball id, release time, release validity
- contacts in order
- blocks, ricochets, catches, out-of-bounds, dead-object contact
- pending outs and pending saves
- referee-discretion markers
- final rulings applied atomically

The resolver must apply finality after all active sequences resolve, so official cases like ricochet catches, simultaneous catches, clock-expired catches, and second-ball outs do not collapse into immediate `is_out` toggles.

### Burden And Throw Clock

`BurdenState`:

- team with burden
- basis: ball majority, player majority, prior burden inversion, cloth reachable-ball ruling
- clock status: idle, active, zero_called, stopped
- started_at, expires_at, play_n_count, play_n_called_at
- tracked ball controllers at the call

Foam/no-sting burden resets after every valid throw and forfeits all balls on failure. Cloth burden requires a two-stage clock: 5 seconds to lose ball majority, then "play n balls" with 5 seconds to make enough attempts.

Cloth equal-ball burden is a rule-discretion case and must emit `RuleDiscretionEvent` from the first burden implementation. Discipline can wait; discretion infrastructure cannot.

### Catch/Re-entry Queue

`CatchQueueState` per team:

- ordered queued player ids
- nonstarter ids excluded from re-entry
- entering player id and deadline
- same-sequence blocked ids
- card/suspension blocked slots

One valid catch from one live ball returns one teammate in FIFO order. Simultaneous valid catches can return multiple players. Entry out of order and late entry must be logged as rule events.

### Ball Retrieval Scope

Section 24 is split for V11:

- 24-core: ball ownership for burden, retrieved-ball side assignment, queue ball ban, entering-player ball contact before live status, and deterministic forfeiture/out events.
- 24-advanced: designated retriever staffing, sideline fights, nonparticipant interference, spectator behavior, and retriever-vs-active-player disputes.

The core subset is required because it affects ball state, queue legality, burden, and outs. Advanced retriever realism can ship later behind the same event model.

### No-Blocking

`NoBlockingState`:

- active flag and source: game-time limit, match-time end, playoff overtime
- ball reset policy: none or three-per-side
- time limit: 180 seconds, untimed, or inherited
- held balls treated as body extensions

No-blocking changes contact resolution. A block is not an immediate out, but the held ball no longer protects the player when the thrown ball completes its sequence.

### Disciplinary Cards

`DisciplineState`:

- per-player warning offenses in current match
- per-team warning offenses
- blue-card counts by player and offense
- yellow/red tournament counters
- short-handed slots for current/next games
- suspension counters for bracket matches

V11 can implement warnings and blue cards once queues exist. Yellow/red carryover belongs to a later persistence phase.

Discipline is later than core state machines, but rule discretion is not. Do not delay `rule_discretion.py` until cards.

### Rule-Discretion Events

`RuleDiscretionEvent`:

- `rule_section`
- `trigger`
- `default_ruling`
- `alternative_rulings`
- `selected_ruling`
- `selection_basis`
- `replay_summary`

All ambiguous official calls should use deterministic defaults unless a future user-facing challenge/referee system is designed. Random referee outcomes are out of scope for V11.

### Action Selection

Official rules resolution must be separate from action choice. `official_actions.py` owns proactive action generation/selection for engine ticks and reactive action definitions for sequence/live-ball resolution; rules modules validate and resolve those actions.

`ProactiveAction` types are chosen by the engine tick:

- `ThrowAction`
- `RetrieveAction`
- `EnterCourtAction`
- `WaitAction`

`ReactiveAction` types are resolved inside an active sequence or live-ball interaction:

- `CatchAttemptAction`
- `DodgeAction`
- `BlockAction`

`LegalActionGenerator` receives official match state and returns legal proactive actions. `ActionSelector` chooses among proactive actions using seeded RNG, player ratings, `CoachPolicy`, burden pressure, clock pressure, ball control, and no-blocking mode. Sequence/live-ball modules request reactive actions from the relevant player states when resolving throws, ricochets, blocks, and catches. This prevents `official_engine.py` from mixing rules, tactics, timing, and randomness.

### Replay Contract

`OfficialReplayState` v0 should be drafted before the autonomous official engine is assembled:

- `ruleset`
- `rulebook_version`
- `official_payload_version`
- `match_clock`
- `game_clock`
- `game_score`
- `mode`
- `burden`
- `balls`
- `teams`
- `player_statuses`
- `active_sequences`
- `rule_calls`
- `events`

Frontend implementation can wait, but the backend shape should be stable before persistence and replay harden.

## Rule Classification

V11 must-have:

- Sections 1, 4, 6, 9, 11, 13, 14, 16, 17, 18, 20, 21, 22, 23, 25, 27.

V11 nice-to-have:

- Sections 3, 7, 8, 10, 12, 15, 26, 33, 34, 35.

V11 partial/core subset:

- Section 24 core retrieval and queue-contact clauses.

Future advanced realism:

- Sections 19, 28, 29, 30, 31, 32, 36, 37.

Administrative/flavor only:

- Sections 2, 5, 38, 40, 41.

Not applicable to current game:

- Section 39.

## Replay And UI Direction

V11 replay must show:

- match score and current game score
- match clock and game clock
- ruleset/material
- burden holder and throw-clock state
- live ball count and ball states
- active/out/entering queue per team
- no-blocking indicator and source
- rule call cards with section references
- sequence explanations for catches, delayed outs, and clock-expired throws

The event log remains canon. UI components may explain outcomes but must not decide them.

## Acceptance Criteria

- Every official-rules outcome is traceable to a rule-section event or deterministic resolver.
- Foam/no-sting and cloth produce distinct lifecycle, burden, and scoring behavior.
- Catch returns are queue-based and visible in replay.
- No-blocking changes outcome resolution and is visible in replay.
- Referee-discretion cases are logged explicitly.
- Existing V1-V10 saves and generic matches still load unless the official ruleset is selected.
- The matrix audit remains linked from the milestone so future agents do not recreate extraction work.
