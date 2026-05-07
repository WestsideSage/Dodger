# V8-V10 Chaos Report

Date: 2026-05-07
Role: Adversarial QA Tester
Worktree / branch: `Dodgeball Simulator.worktrees/codex` / `feature/codex-next-task`

## Scope

PHASE_UNDER_TEST: Post V8-V10 Dynasty Office polish and hardening.

NEXT_PHASE: Merge-ready stabilization on `main`, followed by polish, balance, and integration cleanup.

Read before testing:

- `AGENTS.md`
- `docs/specs/MILESTONES.md`
- `docs/retrospectives/v8-v10/2026-05-06-dynasty-office-blitz-handoff.md`
- `docs/learnings/v8-v10/2026-05-06-dynasty-office-blitz-learnings.md`
- `docs/retrospectives/v7/2026-05-05-v7-playthrough-qa.md`
- `docs/retrospectives/2026-04-30-web-adversarial-qa-report.md`

Authorization: read-only QA/reporting. No implementation code was changed.

Save protection: destructive probes used temporary directories and temporary SQLite files through FastAPI `TestClient`. Browser smoke created and removed `saves/Chaos QA Browser.db` in the Codex worktree. The main user save was not mutated.

## Project Trajectory

### WHERE WE WERE

V7 had a browser-verified replay proof loop, and earlier web chaos work had already exposed stale-save recovery as the main web resilience risk. V8-V10 then shipped a thin Dynasty Office surface for recruiting promises, league memory, and staff market decisions.

The active codebase has moved beyond the initial blitz handoff: promise evaluation, prospect-pool source-of-truth tests, and staff modifier display are already present after the latest `main` merge.

### WHERE WE ARE

The happy path is better than the hardening story. A fresh browser save can open Dynasty Office, save a visible recruiting promise, and hire visible staff without console errors. The API correctly rejects unknown promise types, caps active promises at three, rejects stale staff candidate IDs, and returns a clean `422` for malformed Command Center tactic values.

The save boundary is not stable under malicious input. The save API accepts arbitrary existing paths as loadable saves, can delete arbitrary existing files, and corrupt Dynasty Office JSON still bubbles into generic `500 Internal Server Error` responses.

### WHERE WE ARE GOING

The next phase needs hard save-path boundaries before broader release hardening. Once the save API is fenced to known save files and corrupt JSON becomes a recoverable/diagnostic response, Dynasty Office can move into deeper browser abuse, promise fulfillment playthroughs, mobile layout checks, and season/offseason transition testing.

## Test Matrix

| Area | Method | Result | Evidence |
|---|---|---:|---|
| Loaded-save precondition | `GET /api/status` before loading a save | Pass | `503`, "No save loaded..." |
| Fresh save creation | `POST /api/saves/new` in temp dir | Pass | Created `saves/Chaos QA.db` |
| Dynasty Office initial state | `GET /api/dynasty-office` | Pass | 8 prospects, 6 staff candidates |
| Ghost promise player ID | `POST /api/dynasty-office/promises` with `ghost_player_not_in_pool` | Fail | Accepted with `200` and one active promise |
| Invalid promise type | `POST /api/dynasty-office/promises` with `not_a_real_promise` | Pass | `400`, unknown promise type |
| Promise cap | Four distinct promise attempts after one ghost promise | Pass | Third real/overall fourth promise rejected with `400` |
| Staff hire repeat | Hire first candidate, then repeat stale ID | Pass | First `200`, repeat `400` |
| Corrupt Dynasty Office JSON | Direct DB mutation: `program_promises_json = 'NOT JSON {{{'` | Fail | `GET /api/dynasty-office` returned `500` |
| Load non-DB path | `POST /api/saves/load` with existing `.txt` file | Fail | Accepted with `200`; next `GET /api/status` returned `500` |
| Delete arbitrary path | `POST /api/saves/delete` with existing `.txt` file | Blocker | File was deleted; endpoint returned `200` |
| Save-name traversal | `POST /api/saves/new` with `../outside` | Pass | Sanitized to `saves/outside.db`; no outside file |
| Malformed tactic value | `POST /api/command-center/plan` with `"tempo": "not-a-number"` | Pass | `422` validation response |
| Browser Dynasty Office smoke | Playwright CLI, fresh browser save, `?tab=dynasty` | Pass | Surface rendered; promise and staff hire updated visibly |
| Browser console | Playwright console capture during smoke | Pass | Only React DevTools info message |

## Critical Failure Points

### 1. Save delete can remove an arbitrary existing file

Severity: Blocker

Reproduction:

1. Start the API through `TestClient`.
2. Create any file in the process-accessible filesystem, for example `/tmp/dbm-chaos-.../delete-victim.txt`.
3. Send `POST /api/saves/delete` with body `{"path": "/tmp/dbm-chaos-.../delete-victim.txt"}`.
4. Observe response `200 {"status": "ok"}`.
5. Observe the file no longer exists.

Impact: any browser client or forged request can delete files the process can access, not just managed save files. This must be fixed before treating the web surface as release-hardened.

### 2. Save load accepts non-save files and leaves the app in a 500 state

Severity: High

Reproduction:

1. Create any existing non-SQLite file, for example `/tmp/dbm-chaos-.../sentinel-not-a-save.txt`.
2. Send `POST /api/saves/load` with body `{"path": "/tmp/dbm-chaos-.../sentinel-not-a-save.txt"}`.
3. Observe response `200 {"status": "ok", "path": "...sentinel-not-a-save.txt"}`.
4. Send `GET /api/status`.
5. Observe `500 Internal Server Error`.

Impact: the active save pointer can be set to a non-save file. The user sees a broken app state rather than a clean rejection or recovery path.

### 3. Corrupt Dynasty Office JSON returns a generic 500

Severity: High

Reproduction:

1. Create a valid save.
2. Mutate the save DB directly:
   - `INSERT OR REPLACE INTO dynasty_state (key, value) VALUES ('program_promises_json', 'NOT JSON {{{')`
3. Send `GET /api/dynasty-office`.
4. Observe `500 Internal Server Error`.

Impact: this is a realistic partial-write or manual-save-corruption shape. The domain raises `CorruptSaveError`, but the route does not convert it into a clear `409`/recovery response.

## State Corruptions

- `api_load_save` trusts any existing path. A stale or malicious path can become `_active_save_path` even when it is not a SQLite save.
- `api_delete_save` trusts any existing path except the root legacy DB. It does not restrict deletion to managed files under `saves/` or validate file extension/type before unlinking.
- Dynasty Office JSON keys are validated in the domain, but API handling only catches `ValueError`; `CorruptSaveError` escapes as a generic server failure.
- `save_recruiting_promise` accepts a `player_id` that does not exist in the visible prospect pool or current roster. That promise is persisted and counts against the cap, which can create invisible/unfulfillable promise state from forged requests.

## Edge Case Findings

- Promise cap enforcement is mechanically solid once open promises exist. The ghost promise counted toward the three-promise limit, and subsequent fourth-promise attempts returned `400`.
- Stale staff hire IDs are rejected after the first hire removes the department from the market.
- Save-name traversal through `../outside` is sanitized into `saves/outside.db`; this specific path traversal probe did not escape the saves folder.
- Malformed Command Center tactic input returns structured validation instead of crashing.
- Browser smoke passed for the new Dynasty Office happy path: a fresh save opened directly to the tab, a promise appeared as `OPEN`, a staff hire appeared under Recent staff moves, and the hired department disappeared from candidates.
- Browser coverage did not include mobile/narrow viewport or destructive save-menu clicks because the API path vulnerability was already confirmed and the task was read-only.

## Fix Priority

1. Blocker, owner: Senior Debug & Maintenance Engineer. Restrict save load/delete to canonical managed save files under `saves/` plus explicitly allowed legacy DB behavior. Resolve paths, reject path traversal, reject non-`.db` files, and refuse deletion outside the managed save directory.
2. High, owner: Senior Debug & Maintenance Engineer. Validate loaded save files before setting `_active_save_path`. A failed `connect`/schema/read should return `400` or `409` and leave the current active save unchanged.
3. High, owner: Backend/API. Catch `CorruptSaveError` around Dynasty Office routes and return a clear `409` with the damaged key/state. Add regression coverage for corrupted `program_promises_json` and `staff_market_actions_json`.
4. Medium, owner: Backend/API. Validate promise `player_id` against the visible/persisted prospect pool or current roster before saving. If future design intentionally permits off-board promises, store a source marker and make the UI able to display it.
5. Medium, owner: Adversarial QA Tester. After fixes, rerun this API matrix plus browser save-menu abuse, mobile viewport inspection, and an end-to-end season/offseason promise-evaluation playthrough.

## Verdict

No: the current V8-V10/post-blitz phase is not stable enough to call merge-ready hardening complete.

The Dynasty Office happy path is playable, and several forged action inputs are handled correctly. The save boundary is a release blocker: arbitrary path deletion and arbitrary path loading are too dangerous to ship, and corrupted Dynasty Office state still needs a controlled recovery response.
