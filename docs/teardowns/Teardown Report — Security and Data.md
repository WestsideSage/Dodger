# Teardown Report — Security and Data Integrity

## Threat Model
Dodgeball Manager is a local-first, single-player app. The launcher binds both Vite and FastAPI to `127.0.0.1` in [web_cli.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/web_cli.py:212) and [vite.config.ts](C:/GPT5-Projects/Dodgeball%20Simulator/frontend/vite.config.ts:9). There is no authentication, which is reasonable for this product shape, but it means every localhost request is trusted.

Realistic risks are: a local browser page or script hitting localhost while the game is running, malformed API payloads corrupting the current save, accidental exposure of repo/local files through the production SPA server, and bad save creation inputs producing broken SQLite state. User data is mostly local SQLite saves under `saves/` plus legacy `dodgeball_sim.db`, generated WAL files, launch state, screenshots, and playtest artifacts.

## Verdict
Security/data integrity is uneven. The core SQLite style is mostly healthy, save path deletion/loading has meaningful guardrails, and the app correctly treats many corrupted saves as recoverable conflicts. The high-signal problems are around localhost trust and inconsistent backend validation: production static serving has a real path traversal, no-body POST routes are drive-by mutable from a browser form, and build-from-scratch can create a save with duplicate player IDs.

## Highest-signal findings

### 1. Localhost form POSTs can mutate the active career
- Severity: High
- Evidence: State-changing no-body routes include `/api/command-center/scout`, `/api/command-center/confirm-lineup`, `/api/command-center/simulate`, `/api/command-center/fast-forward`, and `/api/saves/unload` in [server.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/server.py:546). An in-memory TestClient form POST with `data={}` returned `200` for scout, confirm-lineup, simulate, unload, and fast-forward; fast-forward advanced a fresh save to `season_complete_offseason_beat`.
- Attack/failure path: User has local server running, visits a hostile webpage, page submits an HTML form to `http://127.0.0.1:<port>/api/command-center/fast-forward`.
- Practical impact: Current save can be advanced, simulated, readiness-gated, or unloaded without player intent. No remote file read is needed.
- Suggested fix direction: Require a launch-scoped CSRF/session token or custom header on all mutation routes, and reject non-JSON/contentless form requests for state-changing endpoints.
- Regression gate: TestClient form POSTs to every mutating endpoint should return `403`/`415`; frontend JSON requests with the token should still pass.

### 2. Production SPA fallback allows path traversal out of `frontend/dist`
- Severity: High
- Evidence: The catch-all route uses `path = frontend_dist / full_path` and serves it when `path.exists()` in [server.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/server.py:1348). Probe confirmed `frontend/dist/../../AGENTS.md` resolves to the repo root and `GET /..%2F..%2FAGENTS.md` returned the markdown file.
- Attack/failure path: Request encoded `..` segments from the production server.
- Practical impact: Local files under the repo root can be exposed through the local web server, including ignored-but-present files if names are guessed.
- Suggested fix direction: Resolve the requested file and require `resolved.relative_to(frontend_dist.resolve())`; otherwise return `index.html` or 404.
- Regression gate: `GET /..%2F..%2FAGENTS.md`, `/%2e%2e/%2e%2e/pyproject.toml`, and encoded variants must not return file contents.

### 3. Build-from-scratch accepts duplicate founding roster IDs
- Severity: High
- Evidence: [save_service.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/save_service.py:269) appends a player for every submitted `roster_player_ids` entry and only checks `len(custom_roster) < 6` at line 301. Probe with the same prospect ID six times created a save with `roster_len=6`, `unique_ids=1`, and six identical player IDs.
- Attack/failure path: Malformed `/api/saves/build-from-scratch` JSON bypasses frontend duplicate prevention.
- Practical impact: Permanent save corruption: one logical player appears multiple times on the roster and can enter simulation/stat paths as repeated roster entries.
- Suggested fix direction: Backend validate `6 <= unique valid roster ids <= roster cap`, reject duplicates/unknown IDs with 400, and preserve frontend-friendly error details.
- Regression gate: Test build-from-scratch duplicate IDs and over/under roster limits; assert no DB file remains after rejected creation.

### 4. Inline simulate lineup update bypasses lineup validation
- Severity: Medium
- Evidence: `/api/lineup` validates via `apply_manual_lineup` in [web_status_service.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/web_status_service.py:224), but `simulate_week` writes `update["lineup_player_ids"]` directly into `plan["lineup"]["player_ids"]` in [use_cases.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/use_cases.py:1005). Probe posted six `not_on_roster` IDs to `/api/command-center/simulate`; response was `200`, and `weekly_command_plans` stored the fake IDs.
- Attack/failure path: Malformed JSON simulation request.
- Practical impact: Saved plan/history can contradict the actual resolved match lineup, undermining replay and decision-trace trust.
- Suggested fix direction: Reuse the same lineup validation path as `/api/lineup`, or ignore inline lineup updates and require the dedicated endpoint.
- Regression gate: `/api/command-center/simulate` with non-roster, duplicate, or wrong-count lineup IDs returns 400 and does not persist a weekly plan.

## Security Findings

| Severity | Attack/failure path | Evidence | Practical impact | Fix direction | Test gate |
|---|---|---|---|---|---|
| High | Browser form POST to localhost mutates save | Mutating no-body routes in [server.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/server.py:546); form probes returned 200 | Drive-by simulation/fast-forward/unload while server runs | CSRF/launch token plus reject form posts on mutations | Form POSTs to mutating routes fail |
| High | Encoded `..` reads files outside `frontend/dist` | [server.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/server.py:1350); probe read `AGENTS.md` | Local repo/ignored files can be exposed | Resolve and enforce `relative_to(frontend_dist)` | Encoded traversal returns 404/index, not file |
| Low | Unknown API route echoes requested path | [server.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/server.py:1337) | Minor route enumeration/noise | Generic 404 detail | Unknown API response omits raw path |

## Data Integrity Findings

| Severity | Attack/failure path | Evidence | Practical impact | Fix direction | Test gate |
|---|---|---|---|---|---|
| High | Duplicate founding roster IDs in build-from-scratch | [save_service.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/save_service.py:269) and probe result | Corrupt save with repeated player identity | Validate unique valid IDs and roster cap before DB creation | Duplicate IDs rejected, no save left behind |
| Medium | Inline simulate lineup update stores fake IDs | [use_cases.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/use_cases.py:1005) vs [web_status_service.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/web_status_service.py:224) | Plan/history can lie about fielded lineup | Reuse lineup validator or remove inline lineup mutation | Bad inline lineup returns 400 and persists nothing |
| Low | Partial save DB can remain if creation fails after `connect(path)` | [save_service.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/save_service.py:304) | Failed create can leave broken/incompatible save file | Create in temp path, commit, atomic rename; cleanup on exception | Forced init failure leaves no `.db` |

## Confirmed Strengths
Save load/delete path traversal is already guarded: `resolve_managed_save_path` enforces `.db`, managed `saves/`, existence, file-ness, and legacy-load-only behavior in [save_service.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/save_service.py:19), with regression coverage in [test_server_save_boundary.py](C:/GPT5-Projects/Dodgeball%20Simulator/tests/test_server_save_boundary.py:67).

SQL injection risk looked low in inspected paths: route IDs and state values use parameterized `?` queries across persistence, and the only f-string `ALTER TABLE` cases use hardcoded column dictionaries in [persistence.py](C:/GPT5-Projects/Dodgeball%20Simulator/src/dodgeball_sim/persistence.py:1021).

Generated DB/secrets handling is mostly sane: `.gitignore` excludes `*.db`, SQLite variants, `.env`, logs, output, and frontend builds in [.gitignore](C:/GPT5-Projects/Dodgeball%20Simulator/.gitignore:17).

## Open Questions
None blocking. The CSRF severity depends on whether you consider “malicious webpage while localhost app is running” in scope; I do, because it is practical and cheap to guard.

## Suggested Next Prompt
Fix the localhost mutation and file-serving issues first: add a launch-scoped mutation token/header check for all POST routes, harden the SPA fallback against traversal, and add regression tests for form POST rejection, encoded traversal, duplicate founding roster IDs, and inline simulate lineup validation.

Verification note: I used static inspection plus disposable in-memory/file probes. A focused pytest run was attempted, but Windows permissions on pytest temp/cache paths caused setup errors/timeouts; no code was modified. Pare MCP was not exposed in this session, so I fell back to normal shell/static inspection.

Goal usage: completed in about 11.5 minutes, with `195418` goal tokens recorded.