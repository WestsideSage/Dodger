# V4 Web Foundation Chaos Report

Codename: Breakpoint

Date: 2026-04-29
Role: Adversarial QA Tester / Chaos Monkey
Scope: Dodgeball Manager web app foundation before the next milestone

## Project Trajectory

### WHERE WE WERE

V3 made the Tkinter Manager Mode substantially more playable: active-roster integrity, match replay controls, match reports, pacing actions, name cleanup, and digest-style simulation output were implemented and covered by the Python suite. Prior stability work focused on preserving deterministic engine behavior, career-state transitions, lineup correctness, persisted match snapshots, and save/resume safety.

The shipped web foundation is a strangler-style surface over the same domain and persistence layers. It currently exposes a thin hub, roster, tactics, standings, schedule, news, and simulation API.

### WHERE WE ARE

The V4 web app can bootstrap a default career, display core league data, save tactics, and simulate matches through the FastAPI routes. Build, lint, and the Python regression suite pass.

The non-happy-path surface is not yet bulletproof. The biggest issue is parity: `Play Next Match` resolves the match directly but never enters an in-match/replay/report pending state and exposes no match replay/report endpoint. Several server routes also trust state too much: simulation can run while the career cursor is manually placed in offseason, recruitment, next-season, or even invalid fallback states. Tactics input rejects obvious strings and missing fields, but accepts out-of-range numeric values and raw JSON `NaN` tokens. Corrupt roster JSON produces a hard 500.

### WHERE WE ARE GOING

The next V4 milestone needs a web-first stability contract before feature expansion:

- Web `Play Next Match` must preserve the V3 main course: replay and post-match report derived from persisted event logs and roster snapshots.
- Simulation routes must honor `CareerStateCursor` lifecycle rules instead of bypassing state-machine intent.
- API validation must reject non-finite and out-of-range tactics before persistence.
- Corrupt or impossible persistence state should fail with controlled 4xx/diagnostic responses where the user caused the invalid state, and with recoverable 5xx diagnostics where the save is damaged.
- Missing web parity should be explicit in the UI, not silently papered over by generic simulation success messages.

## Critical Failure Points

### CF-1: `Play Next Match` skips replay/report and leaves no active match context

Severity: Critical for V4 parity.

Reproduction:

1. Start from a fresh web career.
2. Call `POST /api/sim` with `{"mode":"user_match"}` or click `Play Next Match`.
3. Observe response: `{"status":"success","simulated_count":1,"stop_reason":"user_match","message":"Simulated 1 matches."}`.
4. Call `GET /api/status`.
5. Observe state remains `season_active_pre_match`, `match_id` is `null`.
6. Try likely detail routes such as `/api/replay/<match_id>`, `/api/match/<match_id>`, or `/api/match-report/<match_id>`.

Observed:

- The match record is persisted.
- Schedule marks the match as played.
- No replay/report state is exposed.
- Candidate API detail routes return the SPA HTML shell with HTTP 200, not a structured 404 or match payload.

Impact:

The web client resolves the user match as a background sim. The player never sees the event log, court replay, turning point, MVP, or report flow that V3 made central.

### CF-2: Simulation runs from illegal lifecycle states

Severity: High.

Reproduction:

1. Manually set `career_state_cursor` in `dynasty_state` to `season_complete_offseason_beat`, `season_complete_recruitment_pending`, or `next_season_ready`.
2. Call `POST /api/sim` with `{"mode":"week"}`.

Observed:

- Offseason beat state: HTTP 200, simulated 2 matches.
- Recruitment pending state: HTTP 200, simulated 3 matches.
- Next season ready state: HTTP 200, simulated 3 matches.
- Invalid state payload falls back to `splash`, then `POST /api/sim` still returns HTTP 200 and simulates 3 matches.

Impact:

The web API can mutate season results while the cursor says the career is not in an active matchday state. This undermines save/resume truth and can desynchronize the web lifecycle from Manager Mode.

### CF-3: Corrupt roster JSON hard-crashes roster loading

Severity: High.

Reproduction:

1. Set the user club row in `club_rosters.players_json` to invalid JSON, e.g. `{not json`.
2. Call `GET /api/roster`.

Observed:

- HTTP 500 `Internal Server Error`.
- `GET /api/status` still returns 200, so the app can partially load while roster-dependent surfaces fail.

Impact:

A damaged save is not unreadable at the SQLite level (`PRAGMA quick_check` still reports `ok`), but the web app has no controlled recovery or diagnostic for malformed roster payloads.

## State Corruptions

### SC-1: Empty user roster still simulates a user match

Reproduction:

1. Set the user club roster JSON to `[]`.
2. Keep default lineup IDs pointing at the now-missing players.
3. Call `GET /api/roster`.
4. Call `POST /api/sim` with `{"mode":"user_match"}`.

Observed:

- Roster endpoint returns HTTP 200 with `roster: []` and a stale six-player default lineup.
- User match simulation returns HTTP 200 and simulates 1 match.

Impact:

The API accepts an impossible manager state. This should be rejected before match simulation, because the UI is showing no players while the domain still resolves a match somehow.

### SC-2: Out-of-range tactics are accepted and persisted through clamping side effects

Reproduction:

1. Call `POST /api/tactics` with values such as `-999`, `999999`, `2`, and `-100`.
2. Call `GET /api/tactics`.

Observed:

- The write returns HTTP 200.
- After a huge finite payload, the policy reads back as all `1.0`.
- Raw JSON containing `NaN` is also accepted with HTTP 200.

Impact:

The server relies on model construction/persistence behavior instead of explicit request validation. This hides bad inputs and makes API behavior ambiguous.

### SC-3: SPA catch-all masks missing API routes

Reproduction:

1. After simulating a match, request `/api/replay/<match_id>` or `/api/match-report/<match_id>`.

Observed:

- HTTP 200 with frontend `index.html`.

Impact:

API clients cannot distinguish "route does not exist" from a successful API response unless they inspect content type/body. This can hide integration mistakes and makes automated QA less trustworthy.

## Edge Case Checklist

| Area | Result | Notes |
| --- | --- | --- |
| Fresh web career bootstrap | Pass | `GET /api/status` initializes season 1, week 1, Aurora Pilots. |
| Roster load | Pass | Fresh roster returns 6 players and 6 default lineup IDs. |
| Schedule load | Pass with wording issue | Pending rows are labeled `open`; QA script initially looked for `pending`. |
| Play next user match | Fail | Simulates directly; no replay/report state or match context. |
| Missing replay/report endpoint behavior | Fail | SPA shell returned as HTTP 200 for missing API-like routes. |
| Tactics string injection | Pass | String payload returns 422 validation error. |
| Tactics missing fields | Pass | Missing required fields return 422 validation errors. |
| Tactics negative/out-of-range numeric values | Fail | Accepted with HTTP 200. |
| Tactics raw `NaN` token | Fail | Accepted with HTTP 200. |
| Oversized tactics body | Risk | 200 KB unknown field payload accepted; no size/extra-field rejection observed. |
| Offseason state simulation | Fail | `POST /api/sim` still simulates matches. |
| Recruitment pending simulation | Fail | `POST /api/sim` still simulates matches. |
| Next-season-ready simulation | Fail | `POST /api/sim` still simulates matches. |
| Invalid cursor state | Fail | Status falls back to splash, but sim still mutates season. |
| Empty roster | Fail | Empty user roster plus stale lineup still allows user-match simulation. |
| Corrupt roster JSON | Fail | `GET /api/roster` returns uncontrolled 500. |
| SQLite file integrity after chaos mutations | Pass | `PRAGMA quick_check` returned `ok`; failures are semantic/app-level. |
| Python regression suite | Pass | `python -m pytest -q`: 356 passed, one cache warning. |
| Frontend build | Pass | `npm run build` completed successfully. |
| Frontend lint | Pass | `npm run lint` completed successfully. |

## Evidence Artifacts

- Raw API/state chaos transcript: `output/chaos_api_results.json`
- Database action: no `dodgeball_manager.db` existed to rename; `dodgeball_sim.db` was copied to `dodgeball_sim.chaos-backup.db` before destructive web testing.

## Stability Verdict

V4 is not stable enough to serve as the foundation for V_NEXT if V_NEXT assumes web parity with V3 Manager Mode.

The engine and baseline test suite remain healthy, but the web surface currently behaves like a thin simulator dashboard rather than a complete Manager Mode client. The next work should prioritize replay/report parity, lifecycle-gated simulation routes, explicit API validation, and damaged-save handling before adding new gameplay scope.
