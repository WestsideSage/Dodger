# Teardown Report — Save / Resume / Migration Integrity

## Verdict
Career continuity is mostly healthy on the active web path, but migration/resume integrity is uneven. The strongest player-facing loops are covered: disposable reload smoke passed through official-rules save creation, match replay after reopen, fast-forward to offseason, offseason beat progression, recruitment skip, schedule reveal, and Season 2 start. Focused tests also passed. The main risks are not sim determinism; they are trust-boundary issues around legacy save inspection mutating files, corrupt cursor data being silently converted to `splash`, and backend/API ruleset defaults lagging the documented “new careers default official” product state.

## Highest-Signal Findings

### Finding 1
- Severity: High
- Evidence: [save_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/save_service.py:65>) `read_save_meta()` opens a save and calls `create_schema(conn)` at lines 74-79. [persistence.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/persistence.py:1099>) `create_schema()` applies migrations and commits. Disposable probe: v1 schema became schema 17 after `read_save_meta()`, while `looks_like_dodgeball_save()` alone left it at 1.
- Why it matters: Listing or checking save metadata can silently migrate an old save before the player explicitly resumes it and without the backup path used by `migrate_schema(..., db_path=...)`.
- Reproduction / inspection path: Create v1 fixture, call `read_save_meta(path)`, then inspect `schema_version`.
- Suggested fix direction: Split “read metadata” from “upgrade save”. Metadata/list/load validation should be non-mutating; explicit resume should run a migration transaction with backup and user-visible failure if incompatible.
- Regression gate: Add a test that `read_save_meta()` and `/api/saves` do not change `schema_version` or add columns; add a separate explicit migration test that does.

### Finding 2
- Severity: High
- Evidence: [persistence.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/persistence.py:2695>) `load_career_state_cursor()` returns `CareerState.SPLASH` on malformed JSON, invalid state, or missing required keys at lines 2705-2709. [test_career_state.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_career_state.py:96>) explicitly locks this behavior for malformed JSON and invalid enum values.
- Why it matters: A corrupt or partially migrated career cursor is a continuity-critical failure. Returning `splash` can make the app pretend the career is merely at a start state instead of honestly reporting damaged state.
- Reproduction / inspection path: Insert `career_state_cursor = "{not-json"` in `dynasty_state`; call `load_career_state_cursor()`.
- Suggested fix direction: Keep absent cursor as `SPLASH` for fresh DBs, but raise a corruption/incompatible-save error for malformed existing cursor rows.
- Regression gate: Replace the malformed/invalid cursor tests with “raises clear corrupt save error”; add `/api/status` or `/api/save-state` coverage for 409/422 instead of silent splash.

### Finding 3
- Severity: Medium
- Evidence: [docs/STATUS.md](</C:/GPT5-Projects/Dodgeball Simulator/docs/STATUS.md:1>) says new careers default to `official_foam`. Frontend does default that in [SaveMenu.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/SaveMenu.tsx:92>) and sends `ruleset_selection` at lines 170-174/186-195. Backend request models still default `ruleset_selection` to `None` in [server.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/server.py:373>) and [server.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/server.py:380>). [test_official_routing.py](</C:/GPT5-Projects/Dodgeball Simulator/tests/test_official_routing.py:95>) asserts API/domain default has no ruleset.
- Why it matters: UI-created saves preserve the official choice, but direct API clients, old cached frontends, or automation can create new generic-rule careers while docs say the product default flipped.
- Reproduction / inspection path: Call `initialize_curated_manager_career(conn, "aurora", root_seed=1)` or `/api/saves/new` without `ruleset_selection`; inspect `dynasty_state.ruleset_selection`.
- Suggested fix direction: Decide whether the backend default should now be `official_foam`; if yes, update request defaults, `initialize_curated_manager_career()`, and tests while preserving explicit `generic`/`None` for legacy saves only.
- Regression gate: API test for omitted ruleset producing the intended default, plus explicit generic legacy-path test.

## Career State Risk Table
| State | Resume risk | Evidence | Missing test | Recommendation |
|---|---|---|---|---|
| Fresh save / pre-match | Low | Disposable smoke resumed `season_active_pre_match`; [career_setup.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/career_setup.py:254>) persists cursor. | API omitted-ruleset default alignment. | Keep, but settle backend ruleset default. |
| Weekly plan / tactics | Low | [command_week_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/command_week_service.py:199>) preserves existing tactics/lineup on intent-only saves; focused tests passed. | None blocking. | Keep gates. |
| Match aftermath / replay | Low | [replay_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/replay_service.py:125>) reads persisted match/event data; disposable replay after reopen returned 240 events. | Full browser reload at aftermath. | Add e2e reload on post-match report. |
| Fast-forward | Low | [use_cases.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/use_cases.py:1174>) loops `simulate_week(update=None)`; `tests/test_auto_pilot.py` passed. | None blocking. | Keep parity test. |
| Playoffs | Medium | [command_week_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/command_week_service.py:550>) advances bracket/outcome; server tests passed. | Reload mid-playoff bracket state. | Add resume-at-semifinal/final pending test. |
| Offseason beats | Low | [offseason_ceremony.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/offseason_ceremony.py:462>) guards `offseason_initialized_for`; beat smoke reached Season 2. | Browser refresh per beat. | Add route-level reload tests for every beat. |
| Corrupt cursor | High | [persistence.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/persistence.py:2705>) falls back to splash. | Test expecting fail-loud. | Fix as Finding 2. |

## Migration Risk Table
| Schema/path | Risk | Evidence | Recommendation |
|---|---|---|---|
| `/api/saves` / `read_save_meta()` | High | Metadata read calls `create_schema()` and commits migrations. | Make save list non-mutating; migrate only on explicit resume with backup. |
| `migrate_schema()` | Low | [persistence.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/persistence.py:1109>) supports backup when `db_path` is passed; focused migration tests passed. | Route live legacy upgrades through this path. |
| v15-v17 additive migrations | Low | Guards column existence in [persistence.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/persistence.py:1021>) through line 1075. | Keep idempotency tests around partial upgrades. |
| Legacy/official ruleset | Medium | Frontend default and backend default disagree. | Resolve product default at backend boundary. |

## Confirmed Strengths
- Focused audit suite passed: `python -m pytest tests/test_persistence.py tests/test_official_backward_compat.py tests/test_server_save_boundary.py tests/test_career_state.py tests/test_auto_pilot.py tests/test_lineup_default_rollover.py tests/test_recruiting_interest_transfer.py tests/test_recruiting_roster_cap.py tests/test_offseason_beats.py tests/test_offseason_ceremony.py tests/test_offseason_ceremony_endpoints.py tests/test_dynasty_office.py tests/test_server.py -q`.
- Disposable DB smoke passed: official save creation, reload replay, fast-forward, offseason progression, recruitment skip, schedule reveal, Season 2 start.
- Save-name collision is guarded at backend and frontend: [save_service.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/save_service.py:181>) and [IdentityStep.tsx](</C:/GPT5-Projects/Dodgeball Simulator/frontend/src/components/new-game/IdentityStep.tsx:78>).
- Manual lineup intent is explicitly preserved across offseason rollover and signings in [offseason_ceremony.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/offseason_ceremony.py:590>) and [offseason_ceremony.py](</C:/GPT5-Projects/Dodgeball Simulator/src/dodgeball_sim/offseason_ceremony.py:682>).

## Open Questions
- Should backend-created careers without `ruleset_selection` now default to `official_foam`, or is frontend-only defaulting intentional for API compatibility?
- Should legacy migration happen automatically on explicit load, or should the save menu require a visible “upgrade save” action?

## Suggested Next Prompt
“Implement the save/resume integrity fixes from the teardown: make save metadata reads non-mutating, fail loudly on corrupt career cursors, and resolve the backend ruleset default contract with regression tests.”

Pare MCP was not available in this session, so I used normal repo searches and shell commands as the AGENTS fallback. Goal usage: 231,591 tokens, about 6m10s elapsed.