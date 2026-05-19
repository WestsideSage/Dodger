# V4 Architectural Audit — Principal Systems Architect

**Date:** 2026-04-29
**Codename:** Keystone
**Role:** Principal Systems Architect
**Scope:** Structural audit of V4 (Web Architecture Foundation) before V5 (**Tkinter Retirement & Full Web Migration**) feature work begins.
**Predecessor:** `docs/retrospectives/2026-04-29-v3-arch-audit.md`

---

## Project Trajectory

### WHERE WE WERE

V3 (Experience Rebuild) closed 2026-04-29 morning with 330 tests passing + 1 known failure. The three-layer engine/franchise/persistence discipline held. The 4,144-line Tkinter `manager_gui.py` was the only playable client. A V4 web scaffold existed (`server.py`, 257 lines, 4 GET endpoints) but had a frozen-cursor mutation bug in `POST /api/sim/week`, no league/news/scouting/recruitment surface, no match replay, and no HTTP test coverage. The V3 audit (Keystone) catalogued 14 tech debts (TD-01 through TD-14) and recommended five pre-V4 structural refactors.

### WHERE WE ARE

V4 (Web Architecture Foundation) implemented 2026-04-29 evening by the Codex implementation agent. **345 tests pass, 0 fail.** The pre-existing test failure (V3 TD-14) and the frozen-cursor bug (V3 TD-04) are both resolved.

What V4 delivered:

- **Six new endpoints** — `GET /api/standings`, `GET /api/schedule`, `GET /api/news`, `POST /api/tactics`, `POST /api/sim`, `POST /api/sim/week`. `server.py` grew 257 → 329 lines, 4 → 9 routes.
- **`game_loop.py` (202 lines)** — extracted shared orchestration spine. Owns `simulate_scheduled_match`, `persist_match_record`, `recompute_regular_season_standings`, `current_week`. Both `manager_gui.py` and `server.py` now call into it. This partially closes V3 TD-05.
- **Frozen-cursor fix** — `server.py:296` correctly uses `dataclasses.replace(cursor, week=next_week)` instead of mutating the frozen dataclass.
- **React surface** — five components (`Hub.tsx`, `Roster.tsx`, `Tactics.tsx`, `LeagueContext.tsx`, `ui.tsx`) reading the new endpoints; `frontend/src/types.ts` grew to 108 lines covering 6 payload shapes.

Architectural health, the unvarnished read:

- **The strangler fig was inverted.** `server.py:23` now imports `build_schedule_rows`, `build_wire_items`, `normalize_root_seed` directly from `manager_gui.py`. The web stack transitively depends on Tkinter being importable at module-load time. This is the opposite direction the V3 audit recommended and the opposite of what the V4 handoff document committed to ("Maintain the 'Strangler Fig'... Do not delete `manager_gui.py` until the Web UI has 100% feature parity"). The handoff promised additive endpoints; in practice the new endpoints reach back into the GUI.
- **`manager_gui.py` was not decomposed.** It is 4,161 lines (was 4,144). It still owns offseason ceremony orchestration, scouting flow, recruitment flow, and match-result presentation. Every remaining V5 web-parity feature multiplies the cost of leaving it intact.
- **A latent bug shipped.** `server.py:86` calls `load_lineup_default(...)` inside `GET /api/roster`, but `load_lineup_default` is not in the persistence import block (`server.py:11–15`). The first production call to `/api/roster` will raise `NameError`. No test covers this endpoint.
- **Zero HTTP-layer test coverage.** There is no `tests/test_server.py`. None of the 9 endpoints are verified by automation. This is how TD-V4-02 escaped CI.
- **Schema is still v10.** V4 introduced no migrations. The V3 migration test recommendation remains unaddressed.
- **Pydantic typing is half-done.** Request bodies use `BaseModel` (`CoachPolicyUpdate`, `SimCommand`); response shapes are anonymous dicts. OpenAPI schema is degenerate, codegen for `types.ts` is impossible without a refactor.

The good news: `game_loop.py` is genuinely clean. It is the right pattern for V5 to extend. The carry-forward HIGH items from V3 (concurrency, scouting/offseason I/O purification, MatchEngine god object) are exactly where they were — V4 did not regress on them, but it did not advance them either.

### WHERE WE ARE GOING

**V5 scope (per user direction this session): the Tkinter era ends.** The 4,161-line `manager_gui.py` and the 1,303-line legacy `gui.py` are deprecated and removed by the close of V5. The web app becomes the sole playable client. This is not a parity exercise where Tkinter survives as a fallback — it is a one-way migration with explicit deletion as the success criterion.

Concretely V5 must deliver, in order:

1. **Domain extraction.** Every piece of orchestration currently locked inside `manager_gui.py` (offseason ceremony flow, scouting weekly tick orchestration, recruitment round orchestration, match-result presentation, schedule/wire/news formatters, root-seed normalization, build-a-club setup flow) is moved out into presentation-neutral modules — `view_models.py`, expanded `game_loop.py`, and existing domain modules. This is a precondition for everything else.
2. **Web feature parity.** Match replay endpoint + HTML5 `<canvas>` (port `court_renderer.py`); scouting endpoints + UI; recruitment endpoints + UI; offseason ceremony web flow (all 10 beats); build-a-club path on the web; splash/club-picker on the web.
3. **HTTP-layer test coverage.** `tests/test_server.py` covers every endpoint before deletion of the Tkinter parallel.
4. **Tkinter retirement.** Once feature parity is verified by the squad's QA pass, **delete `manager_gui.py`, `gui.py`, `court_renderer.py` (Tkinter-canvas variant), `ui_components.py`, `ui_style.py`, the `dodgeball-manager` and `dodgeball-sim-gui` console scripts, and the `tkinter` import surface from any remaining module.** Update `pyproject.toml` and `AGENTS.md` to reflect the single-client world.

Architectural prerequisites that gate V5 (each elaborated in *Suggested Pre-V5 Refactors* below):

1. **Sever `server.py → manager_gui.py` immediately.** While the import exists, deleting Tkinter is impossible. This is step zero of the retirement.
2. Resolve the latent `/api/roster` NameError and add HTTP test coverage for all 9 existing endpoints before adding more.
3. Purify `scouting_center.py` and `offseason_beats.py` so V5 endpoints don't have to pass raw `sqlite3.Connection` objects.
4. Introduce typed Pydantic response models so `frontend/src/types.ts` can be generated, not hand-maintained.
5. Add SQLite WAL mode + a busy timeout in `connect()`. (Concurrency risk persists even single-client because uvicorn workers + browser tabs can hit the API simultaneously.)
6. Add the v1→v10 migration test (carry-forward from V3 audit) before any v11 schema work.

**Explicit non-goals for V5** (so scope doesn't drift): no multi-user/auth, no cloud saves, no new gameplay systems (trades, contracts, etc.), no balance retuning, no schema v11 unless something in the migration path requires it. V5 is a migration milestone, not a feature milestone. New gameplay belongs in V6+.

---

## Identified Tech Debt

This list supersedes the V3 audit. IDs are renumbered with `TD-V4-*`; carryover items reference their V3 ID.

### HIGH Severity

| ID | Module | Issue | Evidence | V5 Impact |
|----|--------|-------|----------|-----------|
| **TD-V4-01** | `server.py` | **Inverted layering: web → Tkinter.** Web stack imports presentation helpers from `manager_gui.py`. Loading `server.py` at import time imports Tkinter. | `server.py:23` (`from dodgeball_sim.manager_gui import build_schedule_rows, build_wire_items, normalize_root_seed`) | Blocks any Tkinter deprecation. Risks Tkinter import failures crashing the web server in headless environments. Guarantees drift if either client refactors a helper. |
| **TD-V4-02** | `server.py` | **Latent NameError in `/api/roster`.** `load_lineup_default` is referenced but not imported. No test exercises the endpoint, so CI does not catch it. | `server.py:86` (call site) vs `server.py:11–15` (import block); no `tests/test_server.py` | First production GET to `/api/roster` returns 500. Web client roster screen is broken end-to-end. |
| **TD-V4-03** | `tests/` | **Zero HTTP-layer test coverage.** No `tests/test_server.py`. All 9 endpoints unverified by automation. | `tests/` directory listing | Every V5 endpoint addition compounds untested surface. Regressions like TD-V4-02 will keep escaping. |
| **TD-V4-04** | `manager_gui.py`, `gui.py`, `court_renderer.py`, `ui_components.py`, `ui_style.py` | **Tkinter monolith is the V5 deletion target.** `manager_gui.py` is 4,161 lines (was 4,144) and still owns offseason ceremony, scouting flow, recruitment flow, match-result presentation, build-a-club setup, splash flow. Legacy `gui.py` adds another 1,303 lines. Together with `court_renderer.py`, `ui_components.py`, `ui_style.py`, they are ~6,000 lines of code V5 must extract from (then delete). | `wc -l` of each file; `server.py:23` import inversion | This is the central V5 liability. Every line of orchestration left inside Tkinter modules is a line that blocks deletion. |
| **TD-V4-05** | `persistence.py` | **(Carryover V3 TD-03) SQLite concurrency.** `connect()` creates a fresh per-request connection, no WAL pragma, no write lock. Tkinter + web sharing one DB is now a live path because V4 added `POST` endpoints that mutate. | `persistence.py:connect()`, `server.py:get_db()` | `database is locked` errors become possible the moment a user runs Tkinter and web simultaneously, or fires multiple sim requests in quick succession. |

### MEDIUM Severity

| ID | Module | Issue | Evidence | V5 Impact |
|----|--------|-------|----------|-----------|
| **TD-V4-06** | `scouting_center.py` | **(Carryover V3 TD-02) I/O layer violation.** `run_scouting_week_tick()` takes `sqlite3.Connection`, imports persistence inline. | `scouting_center.py` (unchanged from V3) | Blocks V5 scouting endpoints unless we accept passing raw connections through the HTTP layer. |
| **TD-V4-07** | `offseason_beats.py` | **(Carryover V3 TD-06) I/O layer violation.** Same pattern as scouting_center. | `offseason_beats.py` (unchanged from V3) | Blocks V5 offseason ceremony web flow. |
| **TD-V4-08** | `frontend/src/types.ts` vs `models.py` / response dicts | **(Carryover V3 TD-09, worsened) Hand-maintained type contract.** 108 lines now, 6 endpoint payloads tracked. Drift risk increases per endpoint. | `frontend/src/types.ts`, `server.py` GET handlers | V5 will add ~6–10 more endpoints. Manual type sync becomes the dominant frontend bug source. |
| **TD-V4-09** | `server.py` | **Anonymous response shapes.** `CoachPolicyUpdate` and `SimCommand` are typed BaseModels for inputs; outputs are bare dicts. OpenAPI schema is degenerate. | `server.py` GET handlers (lines 56–187) | Without typed responses, codegen for `types.ts` is impossible. Forces TD-V4-08 to stay manual. |
| **TD-V4-10** | `persistence.py` / `tests/` | **(Carryover V3 TD-07) No migration test.** No `test_migrations.py`. V3 recommendation never landed. | `tests/` directory listing | Any v11 migration error corrupts saves with no automated detection. V5 may need v11 if it introduces replay frame caching or async match jobs. |

### LOW Severity

| ID | Module | Issue | Evidence |
|----|--------|-------|----------|
| **TD-V4-11** | `engine.py` | **(Carryover V3 TD-01) `MatchEngine` god object.** 18 methods, single class owns RNG, math, mutation, logging. Unchanged. | `engine.py:46–484` |
| **TD-V4-12** | `config.py` | **(Carryover V3 TD-08) Global `CONFIG_REGISTRY`.** Unchanged. | `config.py` registry pattern |
| **TD-V4-13** | `persistence.py` | **(Carryover V3 TD-12) `dynasty_state` table mixes career-cursor and offseason-beat-idempotency keys.** Unchanged. | `persistence.py:1954` and offseason beats usage |
| **TD-V4-14** | `server.py` | **Inline imports inside function bodies.** `import dataclasses` is repeated at `server.py:211` and `server.py:295`. Cosmetic, but signals the file is drifting toward "stuff just lands wherever." | `server.py:211, 295` |

---

## Schema Migration Strategy

### Current State (v10, unchanged)

V4 added zero migrations. The V3 audit's table mapping still applies. V5 web-parity work requires **no new tables**:

| V5 Feature | Existing Tables | New Schema Needed? |
|-------------|-----------------|-------------------|
| Match Replay | `match_events`, `match_records`, `match_roster_snapshots` | No |
| Scouting UI | `prospect_pool`, `scouting_state`, `scout`, `scout_assignment`, `scouting_revealed_traits`, `scouting_ceiling_label` | No |
| Recruitment UI | `recruitment_board`, `recruitment_round`, `recruitment_offer`, `recruitment_signing` | No |
| Offseason Web Flow | `dynasty_state` (idempotency keys), `awards`, `hall_of_fame`, `season_records` | No |

V11 would only be required if V5 introduces:
- Multi-save support (a `save_slot` table or `save_id` column on most tables).
- Async match queue (a `match_jobs` table).
- Replay frame caching (a `match_replay_frames` table — probably not worth it; reconstruct from `match_events`).
- User accounts / auth (deferred indefinitely per scope).

### Recommendations (carryover from V3, still unaddressed)

1. **Add a v1→v10 migration test against in-memory SQLite before any v11 work.** Apply each migration in sequence, validate the final schema against an expected fingerprint. ~10–20 lines of test code. Gates regressions.
2. **Wire `backup_before_migration()` into `migrate_schema()` by default.** It already exists; it is not called automatically.
3. **Keep migrations additive.** Do not rename or drop columns. Add tables/columns only. Preserves backward compatibility for users who revert code while keeping their database.

### Save Data Preservation Plan

For V5 specifically:
- All existing tables remain untouched.
- If V5 adds a multi-save UI, schema v11 would add a `save_slot` table and a `save_id` foreign key — but defer this unless the user explicitly requests multi-save in V5 scope. The current single-`dodgeball_sim.db` model is sufficient for parity.

---

## Decoupling Recommendations

Specific modules to isolate. No implementation; structural directives only.

### 1. Sever `server.py → manager_gui.py` (addresses TD-V4-01)

**Problem:** Web layer imports presentation helpers from the Tkinter monolith.

**Recommendation:** Create `src/dodgeball_sim/view_models.py` (or extend `game_loop.py` if the helpers are orchestration-shaped). Move `build_schedule_rows`, `build_wire_items`, `normalize_root_seed` there. `manager_gui.py` becomes a consumer of `view_models.py` instead of the owner. Pattern mirrors how `game_loop.py` already serves both clients.

### 2. Promote `game_loop.py` to own offseason / scouting / recruitment orchestration

**Problem:** `game_loop.py` cleanly owns *match* orchestration. The other three V5 surfaces (offseason, scouting, recruitment) currently route through `manager_gui.py` methods.

**Recommendation:** Mirror the match-orchestration pattern for each: `run_scouting_week`, `advance_offseason_beat`, `conduct_recruitment_round` as pure functions in `game_loop.py` (or a sibling `offseason_loop.py` if size grows). Both clients call in.

### 3. Purify `scouting_center.py` and `offseason_beats.py` (addresses TD-V4-06, TD-V4-07)

**Problem:** Both modules interleave persistence imports with domain computation.

**Recommendation:** Two-layer split each module:
- Pure-compute function: takes preloaded snapshot, returns updated snapshot.
- Thin I/O wrapper: load → call pure function → persist.

This mirrors the `franchise.simulate_match()` (pure) vs `game_loop.simulate_scheduled_match()` (I/O) split.

### 4. Introduce typed Pydantic response models in `server.py` (addresses TD-V4-08, TD-V4-09)

**Problem:** Anonymous dict responses block OpenAPI codegen.

**Recommendation:** Define `StatusResponse`, `RosterResponse`, `TacticsResponse`, `StandingsResponse`, `ScheduleResponse`, `NewsResponse`, `SimResponse` as `BaseModel` subclasses. Annotate every handler's return type. Then either (a) hand-write `types.ts` from the OpenAPI schema once per release, or (b) wire `pydantic-to-typescript` into the build.

### 5. Add SQLite write safety in `persistence.connect()` (addresses TD-V4-05)

**Problem:** `connect()` is bare `sqlite3.connect()`. No WAL, no busy timeout, no write serialization.

**Recommendation:** In `connect()`, after opening the connection: `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`. Optionally, gate writes with a module-level `threading.Lock`. This is a 3-line change but unblocks Tkinter+web simultaneous use.

### 6. Carry forward V3 audit recommendations 4–5

- Decompose `MatchEngine` (V3 rec #4 / TD-V4-11) — still deferred.
- Frontend type contract (V3 rec #5 / TD-V4-08) — promoted from "deferred" to "needed for V5" because endpoint count is rising.

---

## Suggested Pre-V5 Refactors

Structural changes only. No new features, no UI tuning, no balance changes. Priority order assumes V5 = web parity + Tkinter port closure.

### Priority 1 — Fix `/api/roster` NameError + add `tests/test_server.py`

**Scope:** One-line import fix at `server.py:11–15`; ~9 happy-path tests (one per endpoint) using FastAPI's `TestClient` against an in-memory or temp-file DB. Estimated 1–2 hours.

**Routing per AGENTS.md:** TD-V4-02 is a concrete bug → **Senior Debug & Maintenance Engineer**. Bundle the test scaffold with the fix so future endpoint regressions are caught.

### Priority 2 — Sever the `server.py → manager_gui.py` import (TD-V4-01)

**Scope:** Create `view_models.py`, move three helpers, update both call sites. One commit. Unblocks every subsequent V5 endpoint and any future Tkinter retirement.

### Priority 3 — Add typed Pydantic response models (TD-V4-09)

**Scope:** ~7 `BaseModel` subclasses in `server.py`. Annotate handlers. Verify OpenAPI schema renders. Sets up codegen for V5 frontend types.

### Priority 4 — Add v1→v10 migration test (TD-V4-10, carryover V3)

**Scope:** One file, `tests/test_migrations.py`. Run all migrations against `sqlite3.connect(":memory:")`, assert table list and key columns. Prevents v11 regressions.

### Priority 5 — Purify `scouting_center.py` (TD-V4-06)

**Scope:** Split `run_scouting_week_tick()` into `advance_scouting_snapshot()` (pure) + I/O wrapper. Required before V5 scouting endpoints. Higher urgency than offseason because scouting endpoints are called weekly during the season.

### Priority 6 — SQLite WAL + busy timeout in `connect()` (TD-V4-05)

**Scope:** 2–3 lines in `persistence.connect()`. Required before V5 increases write concurrency or Tkinter+web simultaneous use is supported.

### Deferred to V5+ Timeline

- `offseason_beats.py` purification (TD-V4-07) — still important, lower frequency, can land alongside V5 offseason web flow.
- `MatchEngine` decomposition (TD-V4-11) — improves testability; not blocking V5 parity.
- `CONFIG_REGISTRY` DI (TD-V4-12) — useful for testing; not blocking.
- `dynasty_state` table separation (TD-V4-13) — cosmetic, no functional impact.
- Inline-import cleanup (TD-V4-14) — cosmetic.

### Tkinter Retirement Sequence (the V5 critical path)

Ordered so that deletion happens *only* after feature parity is verified. Each step leaves the project shippable.

1. **Sever `server.py → manager_gui.py`** (Pri-2 above). After this, the web stack no longer needs Tkinter to import.
2. **Extract domain orchestration from `manager_gui.py` into `game_loop.py` / `view_models.py` / domain modules.** Roughly: offseason ceremony orchestration, scouting weekly tick orchestration, recruitment round orchestration, build-a-club setup, schedule/wire/news formatters. Tkinter callbacks become thin wrappers around these pure functions during the transition.
3. **Build remaining web endpoints + React views** against the now-shared orchestration: scouting, recruitment, offseason ceremony, match replay, build-a-club, splash.
4. **Squad QA pass on the web client** (Chaos Monkey + UX Engineer + Balance Analyst running against the web app exclusively). Sign-off here is the deletion gate.
5. **Delete the Tkinter surface in one commit:** `manager_gui.py`, `gui.py`, `court_renderer.py`, `ui_components.py`, `ui_style.py`, the `dodgeball-manager` and `dodgeball-sim-gui` console-script entries in `pyproject.toml`, any remaining `import tkinter` lines, and the Tkinter-only test files (`tests/test_manager_gui.py` once its assertions are ported into `tests/test_view_models.py` or equivalent).
6. **Update `AGENTS.md` and `CLAUDE.md`** to remove references to Tkinter, Manager Mode GUI, and the strangler-fig posture. The strangler is done — there's nothing left to strangle.
7. **Update `docs/specs/MILESTONES.md`** with V5 marked Shipped and a one-line note: "Tkinter retired."

Tests must be green at every step. Step 5 is reversible only by `git revert`; that is the intended one-way door.

### Squad Workflow Note

Per AGENTS.md "Required Squad Order Before a New Milestone," after this Architect report the next agents are:

1. **Lead Game Systems & Balance Analyst** — long-run sim health on V4 outcomes.
2. **Lead Front-End UX Engineer** — React/Tailwind audit of the new `LeagueContext.tsx`, `Roster.tsx`, `Tactics.tsx`, `Hub.tsx`.
3. **Adversarial QA Tester / Chaos Monkey** — exercise the 9 web endpoints with illegal inputs, sequence breaks, and state-machine abuse. Will likely catch TD-V4-02 organically.
4. **Senior Debug & Maintenance Engineer** — patch TD-V4-02 (NameError) and any concrete bugs the squad turns up. Recommended scope above.
5. **(Skip Content)** — V5 introduces no new name banks or news templates that aren't already covered.
6. **Lead Technical Project Manager** — synthesize all reports into `docs/specs/2026-04-29-v5-sprint-plan.md`.

---

## Verification

```
$ python -m pytest -q
345 passed in <ms>
```

All tests pass. The V3 audit's reported pre-existing failure (TD-14) was fixed during V4. No code was modified during this audit.

File-reference spot checks:
- `server.py:23` — confirmed import from `manager_gui` (TD-V4-01).
- `server.py:86` — confirmed `load_lineup_default` reference, missing from import block at `server.py:11–15` (TD-V4-02).
- `server.py:296` — confirmed `dataclasses.replace(cursor, week=next_week)` (V3 TD-04 fixed).
- `game_loop.py` — confirmed exists, 202 lines, owns match orchestration.
- `persistence.py:25` — confirmed `CURRENT_SCHEMA_VERSION = 10` (no V4 migrations).
- `tests/` — confirmed no `test_server.py` (TD-V4-03).
- `manager_gui.py` — confirmed 4,161 lines (TD-V4-04).

---

*— Keystone, Principal Systems Architect*

*P.S. The strangler fig is a real plant: it grows around the host tree and eventually replaces it. V4 grew the vine through the host instead of around it. V5's job is to finish the job the way the metaphor intended — and then cut the dead tree down.*
