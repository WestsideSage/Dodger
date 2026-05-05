# V3 Architectural Audit — Principal Systems Architect

**Date:** 2026-04-29
**Codename:** Keystone
**Role:** Principal Systems Architect
**Scope:** Structural audit of V3 (Experience Rebuild) before V4 (Web Architecture Foundation) feature work begins.

---

## Project Trajectory

### WHERE WE WERE

V2 (A–F) shipped 2026-04-28 with a three-layer discipline that held through six sub-milestones:

1. **Engine core** — deterministic `MatchEngine.run()` consuming `MatchSetup` + seed, returning `MatchResult`. All randomness through `DeterministicRNG` with SHA256 namespace-isolated seed derivation.
2. **Domain layer** — pure orchestration via `franchise.py` (zero I/O), `season.py`, `scheduler.py`, `playoffs.py`. Scouting (V2-A), recruitment (V2-B), build-a-club (V2-C), expanded coach policy (V2-D), offseason beats (V2-E), and playoffs (V2-F) added ~3,200 lines across 11 modules.
3. **Persistence** — single `persistence.py` (2,927 lines) owning all SQLite I/O. Schema evolved from v1 to v10 through incremental migrations. 49 tables, 80+ functions, raw sqlite3.

The Tkinter `manager_gui.py` (then ~3,500 lines) served as the only playable client. No web surface existed.

### WHERE WE ARE

V3 (Experience Rebuild) implemented 2026-04-29. Manual screenshot review pending before marking Shipped. 330 tests passing (1 pre-existing failure — see TD-14).

V3 added:
- **Roster integrity** — `LineupResolver.active_starters()`, bench/starter separation, active player IDs on `MatchResult`.
- **Match replay** — game-style controls, event detail panel, name resolution (no more raw IDs in primary surfaces).
- **Pacing controls** — bulk sim (Play Next Match, Sim Week, Sim To Milestone), digest formatting.
- **Copy quality** — unresolved-token detection, unique name generation with fallback suffixes.
- **V4 web scaffold** — FastAPI `server.py` (257 lines) with 4 endpoints, React/Vite/TypeScript frontend in `frontend/`, `dodgeball-manager-web` entry point.

`manager_gui.py` grew to 4,144 lines. Both Tkinter and web clients share `dodgeball_sim.db`.

**Architectural health:**
- The three-layer discipline holds in `franchise.py`, `season.py`, `scheduler.py`, `playoffs.py` — clean acyclic dependency chain, pure functions, frozen dataclasses.
- Layer violations exist in `scouting_center.py` and `offseason_beats.py` (domain functions take `sqlite3.Connection`, import persistence inline).
- `manager_gui.py` contains orchestration logic that the web client must duplicate to achieve feature parity.
- `server.py` has a confirmed frozen-cursor mutation bug and no test coverage for its simulation endpoint.

### WHERE WE ARE GOING

V4 targets web feature parity with the V3 Tkinter client:
- Standings, schedule, and news wire endpoints + React views.
- Scouting & recruitment UI (trait revelation, draft/free-agency bidding).
- Match day replay ported from Tkinter Canvas to HTML5 `<canvas>`.

Architectural prerequisites:
1. Domain logic currently locked inside `manager_gui.py` must be extractable by the web client without copy-paste.
2. `persistence.py` must handle concurrent web requests safely.
3. The `scouting_center.py` and `offseason_beats.py` I/O violations must be resolved so the web backend can orchestrate scouting/offseason through pure domain functions.
4. `server.py` must use the career state machine correctly (frozen cursor via `dataclass.replace()`).

---

## Identified Tech Debt

### HIGH Severity

| ID | Module | Issue | Evidence | V4 Impact |
|----|--------|-------|----------|-----------|
| **TD-01** | `engine.py` | **MatchEngine god object** — 18 methods covering throw resolution, target selection, fatigue, possession, scoring, and event recording. Single class owns RNG creation, probability math, mutable state mutation, and event logging. | `engine.py:46-484` | Blocks unit-testable probability extraction, async match simulation, and balance tuning without touching core orchestration. |
| **TD-02** | `scouting_center.py` | **I/O layer violation** — `run_scouting_week_tick()` takes `sqlite3.Connection`, imports 13 persistence functions inline. Domain computation and database I/O interleaved in one 170-line function. | `scouting_center.py:452-479` | Web backend cannot call scouting domain logic without passing a raw connection. Prevents transaction boundary control by the caller. |
| **TD-03** | `persistence.py` | **No thread-safety for web concurrency** — no connection pooling, no mutex, no WAL mode enforcement. Each request creates a fresh `sqlite3.connect()`. Tkinter + web clients sharing one `.db` file compounds contention. | `persistence.py` `connect()` function, `server.py` `get_db()` dependency | Multiple simultaneous web requests risk lock contention and `database is locked` errors. Blocks multi-user or rapid-request V4 usage. |
| **TD-04** | `server.py:235` | **Frozen cursor mutation bug** — `cursor.week = next_week` attempts to mutate a `frozen=True` dataclass. Raises `FrozenInstanceError` at runtime. No test covers `POST /api/sim/week`. | `career_state.py:20` (`frozen=True`), `server.py:235` | Web simulation endpoint is broken. CI does not catch this because no test exercises the endpoint. |
| **TD-05** | `manager_gui.py` | **GUI-locked domain logic** — orchestration patterns (match persistence, season advancement, offseason ceremony flow, sim-week logic) live inside the 4,144-line Tkinter monolith. Web client must copy-paste helpers (already happening: `_persist_record`, `_team_snapshot_for_ids` duplicated into `server.py`). | `server.py:57-93` (copied helpers), `manager_gui.py` throughout | Every V4 feature parity endpoint requires extracting logic from the GUI or duplicating it. Duplication guarantees drift. |

### MEDIUM Severity

| ID | Module | Issue | Evidence | V4 Impact |
|----|--------|-------|----------|-----------|
| **TD-06** | `offseason_beats.py` | **I/O layer violation** — same pattern as TD-02. Beat functions (`ratify_records`, `induct_hall_of_fame`, `preview_rookie_class`) take `conn`, call persistence directly. | `offseason_beats.py` all beat functions | Web offseason flow requires raw connection passing. Less urgent than TD-02 (offseason is lower-frequency). |
| **TD-07** | `persistence.py` | **No migration rollbacks** — `_migrate_v1()` through `_migrate_v10()` are additive only. No down-migration, no test-DB validation before applying to production saves. | `persistence.py:104-719` | Any v11 migration error corrupts user saves with no automated recovery path. |
| **TD-08** | `config.py` | **Global CONFIG_REGISTRY** — `get_config(version)` reads from module-level dict. No dependency injection, no environment-based configuration. | `config.py` registry pattern | Blocks per-request config overrides (e.g., web admin tuning) and complicates testing with alternative configs. |
| **TD-09** | `frontend/src/types.ts` vs `models.py` | **Frontend/backend type drift** — `types.ts` is hand-maintained against Python dataclasses in `models.py`. No codegen, no contract tests. | `frontend/src/types.ts`, `src/dodgeball_sim/models.py` | As V4 adds endpoints, silent type divergence is guaranteed. Runtime errors instead of compile-time catches. |

### LOW Severity

| ID | Module | Issue | Evidence |
|----|--------|-------|----------|
| **TD-10** | `models.py` | **Hardcoded defaults** — player age (18), rating bounds (0–100), stamina default (50.0), coach policy defaults (0.5), trait defaults (50.0) embedded in dataclass definitions rather than config. | `models.py` field defaults |
| **TD-11** | `persistence.py` | **No connection pooling** — fresh `sqlite3.connect()` per call. Acceptable for Tkinter single-thread; suboptimal for web. | `persistence.py` `connect()` |
| **TD-12** | `persistence.py` | **`dynasty_state` table mixes concerns** — used for both career cursor persistence (`career_state_cursor` key) and offseason beat idempotency caching (per-season keys). Single KV table for unrelated state. | `persistence.py:1954`, offseason beats usage |
| **TD-13** | `config.py` | **Single config version** — only `"phase1.v1"` in registry. No versioning strategy for future balance updates. | `config.py` `CONFIG_REGISTRY` |
| **TD-14** | `tests/test_manager_gui.py` | **Pre-existing test failure** — `test_build_scout_strip_data_three_scouts` saves a scout assignment for season 2 but queries with `season=1`, causing assignment lookup to return `None`. Signals either a test-data setup bug or a `load_all_scout_assignments` filter regression. | `tests/test_manager_gui.py:266` |

---

## Schema Migration Strategy

### Current State (v10)

The v10 schema already provides tables for all V4 read-side feature parity work:

| V4 Feature | Existing Tables | New Schema Needed? |
|-------------|-----------------|-------------------|
| Standings | `season_standings` | No |
| Schedule | `scheduled_matches` | No |
| News Wire | `news_headlines` | No |
| Scouting UI | `prospect_pool`, `scouting_state`, `scout`, `scout_assignment`, `scouting_revealed_traits`, `scouting_ceiling_label` | No |
| Recruitment | `recruitment_board`, `recruitment_round`, `recruitment_offer`, `recruitment_signing` | No |
| Match Replay | `match_events`, `match_records`, `match_roster_snapshots` | No |

**New tables would be required only if V4 introduces:**
- Web session management / authentication
- Async match queueing (match jobs table)
- Multi-user support (user accounts, permissions)

### Migration Pattern Risk

The current migration pattern has structural weaknesses:

1. **No rollback** — migrations are one-way `ALTER TABLE ADD COLUMN` / `CREATE TABLE IF NOT EXISTS`. A botched v11 migration leaves the database in an intermediate state with no automated recovery.
2. **No test-DB validation** — migrations run directly on the user's save database. No dry-run against an in-memory copy first.
3. **No migration checksums** — nothing verifies that the v10 schema matches expectations before applying v11.

### Recommendations

1. **Before any v11 work:** add a migration test that applies all migrations (v1→v10) to an in-memory database, then validates table structure against expected schema. This test costs ~10 lines and prevents future migration regressions.
2. **Adopt backup-before-migrate discipline:** `backup_before_migration()` exists but is not called automatically. Wire it into `migrate_schema()` as a default.
3. **Keep v11 additive:** do not rename or drop columns. Add new tables or columns only. This preserves backward compatibility for users who revert code but keep the database.

---

## Decoupling Recommendations

### 1. Extract Domain Orchestration from `manager_gui.py`

**Problem:** The web client cannot reach season advancement, match persistence, offseason ceremony flow, or sim-week logic without duplicating GUI methods.

**Recommendation:** Create `src/dodgeball_sim/game_loop.py` — a pure orchestration module that extracts the season lifecycle from `manager_gui.py`. Functions like `persist_match_record()`, `advance_season_week()`, `run_offseason_beat()`, and `choose_and_simulate_matches()` should live here. Both `manager_gui.py` and `server.py` become thin callers.

**Reference pattern:** `franchise.py` already demonstrates this — pure functions, no I/O, all state passed in and results returned out. `game_loop.py` would sit one level above, coordinating between franchise and persistence.

### 2. Purify `scouting_center.py`

**Problem:** `run_scouting_week_tick()` interleaves 13 persistence imports with domain computation.

**Recommendation:** Split into two functions:
- `advance_scouting_snapshot(snapshot: ScoutingSnapshot, ...) -> ScoutingSnapshot` — pure computation, takes pre-loaded state, returns updated state.
- Keep `run_scouting_week_tick()` as a thin I/O wrapper: load snapshot → call pure function → persist result.

This mirrors the `franchise.simulate_match()` pattern (pure compute) vs the caller's persistence responsibility.

### 3. Purify `offseason_beats.py`

**Problem:** Same I/O interleaving as scouting_center.

**Recommendation:** Same split pattern. Each beat function should have a pure compute variant that takes loaded data and returns a payload, plus a thin wrapper that handles persistence. Lower priority than scouting (offseason is less frequent in gameplay).

### 4. Decompose `MatchEngine`

**Problem:** 18 methods spanning throw resolution, target selection, probability calculation, fatigue, possession, scoring, and event recording.

**Recommendation:** Extract focused subsystems without changing the public API:
- `ThrowResolver` — probability calculations (`_calculate_throw_success`, `_process_throw` math)
- `TargetSelector` — `_select_thrower`, `_select_target`, policy-aware decision logic
- `FatigueSystem` — `_apply_fatigue`, stamina/consistency interactions

`MatchEngine.run()` becomes a coordinator that delegates to these subsystems. This is a **V4+ refactor** — it improves testability and balance tuning but is not blocking for V4 feature parity.

### 5. Add Frontend/Backend Type Contract

**Problem:** `types.ts` and `models.py` will drift silently as V4 adds endpoints.

**Recommendation (pick one):**
- **Option A:** Generate `types.ts` from Pydantic response models in `server.py` (e.g., `pydantic-to-typescript` or manual script).
- **Option B:** Add a contract test that imports both Python models and TypeScript interfaces, validating field names and types match.

---

## Suggested Pre-V4 Refactors

These are structural changes only — no new features, no UI changes, no balance tuning.

### Priority 1: Fix server.py frozen-cursor bug (TD-04)

Replace `cursor.week = next_week` with `cursor = advance(cursor, ..., week=next_week)` or `cursor = replace(cursor, week=next_week)`. Add a test for `POST /api/sim/week`. This is a one-line fix + one test.

### Priority 2: Extract game loop orchestration (TD-05)

Create `game_loop.py` with shared helpers currently duplicated between `manager_gui.py` and `server.py`. Wire both clients to call the shared module. This unblocks all subsequent V4 endpoint work.

### Priority 3: Purify scouting_center.py (TD-02)

Split `run_scouting_week_tick()` into pure-compute + I/O-wrapper. This unblocks the V4 scouting UI endpoint without raw connection passing.

### Priority 4: Add migration test (TD-07)

One test that applies v1→v10 migrations to in-memory SQLite and validates the resulting schema. Prevents future migration regressions and enables confident v11 development.

### Priority 5: Add SQLite thread-safety (TD-03)

At minimum: enforce WAL mode in `connect()`, add a threading lock around write operations, or introduce a connection pool. Required before V4 handles concurrent web requests.

### Deferred (V4+ timeline)

- MatchEngine decomposition (TD-01) — improves testability but not blocking.
- offseason_beats purification (TD-06) — lower frequency, lower urgency.
- CONFIG_REGISTRY dependency injection (TD-08) — useful for testing, not blocking.
- Frontend type contract (TD-09) — implement when V4 adds its 5th+ endpoint.
- dynasty_state table separation (TD-12) — cosmetic, no functional impact.

### Squad Workflow Note

TD-04 (frozen-cursor mutation bug) and TD-14 (pre-existing test failure) are concrete bugs. Per AGENTS.md §"Required Squad Order Before a New Milestone," these should be routed to the **Senior Debug & Maintenance Engineer** for root-cause analysis and minimal patches.

---

## Verification

```
$ python -m pytest
1 failed, 330 passed in 2.59s
```

**Pre-existing failure:** `test_build_scout_strip_data_three_scouts` — saves a scout assignment for season 2 but queries with `season=1`, causing the assignment lookup to return `None`. This is a test-data setup issue, not a regression from this audit.

No code was modified during this audit. All findings are based on static analysis of the V3 codebase as of 2026-04-29.

---

*— Keystone, Principal Systems Architect*
