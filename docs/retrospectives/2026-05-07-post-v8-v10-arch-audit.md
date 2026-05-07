# Post V8-V10 Architecture Audit — Polish & Hardening Phase

Date: 2026-05-07
Role: Principal Systems Architect
Phase under review: Polish & hardening following the V8-V10 Dynasty Office blitz (2026-05-06)
Schema version: `CURRENT_SCHEMA_VERSION = 13`
Branch: `main`

## Project Trajectory

### WHERE WE WERE
- V1-V7 built a deterministic engine, web foundation, weekly command loop, archetype-first player model, and a watchable replay proof loop.
- V8-V10 shipped *thin* on 2026-05-06 inside a single `Dynasty Office` surface (`src/dodgeball_sim/dynasty_office.py`, `frontend/src/components/DynastyOffice.tsx`, three new endpoints). The blitz traded depth for completeness so the long-range roadmap could be considered "playably reachable" before polish.
- The blitz layer sits on top of existing persistence using JSON-backed `dynasty_state` rows (`program_promises_json`, `staff_market_actions_json`) — no new tables, no schema bump. That was the right call for a thin slice.

### WHERE WE ARE
- Promise evaluation has already been wired into the offseason development beat (commits `5a71e84`, `8b21b18`, `c7578ec`, `f4ab015`, `f749b72`), so V8 is no longer "data-only." The promise-fulfillment hook is honest but narrow.
- A staff development modifier flows from `department_heads` into `apply_season_development` via `BalanceConfig.max_staff_development_modifier` (commits `bf77c62` → `93735f7`). V10 is now a real, tested mechanical effect — modest, but no longer cosmetic.
- A Lead Procedural Content & Narrative Designer pass on 2026-05-07 (commits `fc84bfd`, `3f3ca22`, `042c044`) replaced "future hook"/"this V5 slice" copy with diegetic sports-management language. The honesty boundary is now expressed *in-character* rather than as a developer apology.
- `tests/test_dynasty_office.py` and the `tests/test_server.py` Dynasty Office route exercise the happy paths and a small set of structural rules.
- Adversarial QA on 2026-05-07 (`docs/retrospectives/v8-v10/2026-05-07-v8-v10-chaos-report.md`) identified one **blocker** and three **high/medium** structural defects on the save and Dynasty Office API boundary. These are documented below as Contract Risks and have been fixed in this audit.

### WHERE WE ARE GOING
The next phase is hardening, not feature expansion. Three architectural classes of work matter before V11+:

1. **Save boundary integrity.** Save load/delete must operate on managed paths only and must validate that a path is actually a save before mutating server state.
2. **Persistence error contract on the web boundary.** `CorruptSaveError` and `ValueError` from the domain must map to clear HTTP statuses; no domain corruption should escape as a generic 500.
3. **Legacy desktop GUI deprecation.** `manager_gui.py` (4,039 lines) and `gui.py` (1,303 lines) are still imported by tests and still hold pure helpers (`build_prospect_board_rows`, `build_scout_strip_data`, `build_fuzzy_profile_details`, `build_trajectory_reveal_sweep`, `sign_prospect_to_club`, etc.) that the *web* product depends on through the test suite. They cannot be deleted in one swing — those helpers must move to neutral domain modules first.

## System Map

```
Frontend (React + Vite, frontend/)
    │
    │  HTTP (FastAPI, src/dodgeball_sim/server.py — 1,276 lines)
    │
    ├── /api/saves/*           ── Save lifecycle (create/list/load/delete/unload/state)
    ├── /api/dynasty-office/*  ── Recruiting promises, league memory, staff market
    ├── /api/command-center/*  ── Weekly intent / department orders / tactics
    ├── /api/sim/*             ── Engine simulation requests
    ├── /api/replay/*          ── V7 watchable proof loop
    └── /api/offseason/*       ── 10-beat ceremony orchestration
    │
    ▼
Domain layer
  ├── dynasty_office.py        ── V8/V9/V10 facade (561 lines)
  ├── command_center.py        ── V5 weekly command loop
  ├── offseason_ceremony.py    ── 10-beat ceremony
  ├── offseason_beats.py       ── Per-beat domain logic
  ├── recruitment*.py          ── Recruitment Day + V2-B domain
  ├── scouting*.py             ── V2-A scouting model
  ├── franchise.py             ── Club↔Team bridge
  ├── playoffs.py / season.py  ── Season + bracket
  └── replay_proof.py          ── V7 evidence builder
    │
    ▼
Engine (deterministic, no SQLite or UI)
  ├── engine.py / models.py / events.py / rng.py / config.py
    │
    ▼
Persistence (src/dodgeball_sim/persistence.py — 3,188 lines)
  ├── connect() runs migrations through CURRENT_SCHEMA_VERSION = 13
  ├── dynasty_state JSON KV  (used by V8/V9/V10 thin layer)
  ├── prospect_pool, awards, league_records, rivalry_records, match_records,
      department_heads, club_facilities, command_history, …
  └── CorruptSaveError signals partial-write/manual-corruption at JSON boundaries
```

Legacy Tk/curses surfaces (`manager_gui.py`, `gui.py`, `manager_gui` is still referenced by `tests/test_manager_gui.py` and `tests/test_game_loop.py`) live alongside the web stack but are no longer entry points (`pyproject.toml` routes both `dodgeball-manager` scripts to `web_cli:main`). The stale `egg-info/entry_points.txt` is a generated-file artifact, not a live wiring problem.

## Identified Tech Debt

### High

1. **Web save boundary trusts arbitrary filesystem paths.** `api_load_save` and `api_delete_save` both accepted any `Path(req.path)` that existed, which the chaos report verified by deleting a non-save `.txt` file and by leaving `_active_save_path` pointed at a non-SQLite file. Architectural fault: the web layer was treating save identity as "absolute path the client sent" rather than "name of a file under `SAVES_DIR`/legacy DB." Evidence: `server.py:1041-1066` (pre-fix). **Fixed in this audit** — see Migration Strategy.
2. **Domain corruption can escape as 500 on the Dynasty Office routes.** `CorruptSaveError` is raised by `_ensure_dynasty_keys` when `program_promises_json` or `staff_market_actions_json` contains malformed JSON, but the route only converted `ValueError`. Evidence: `server.py:545-566` (pre-fix), `dynasty_office.py:41-52`. **Fixed in this audit.**
3. **`save_recruiting_promise` accepted ghost player IDs.** A forged client could persist a promise against any string and consume slots toward the 3-active cap, producing invisible/unfulfillable state. Evidence: `dynasty_office.py:78-104`, chaos report §"State Corruptions". **Fixed in this audit.**

### Medium

4. **`server.py` is 1,276 lines and growing.** It mixes Pydantic models, route handlers, save management, and helper functions. The polish phase should split it into `server/routes_*.py` modules organized by surface (saves, dynasty_office, command_center, sim, replay, offseason) — the natural seams already exist in the imports block. Defer until after the next round of stabilization so we don't bundle structural and security changes in the same merge.
5. **`persistence.py` is 3,188 lines and is the SQLite + migration + reader/writer monolith.** It is internally well-sectioned but is approaching the size where any change requires reading the whole file. Splitting into `persistence/schema.py`, `persistence/state_kv.py`, `persistence/loaders.py`, `persistence/writers.py` would help, but only after V11 starts demanding new schema work; doing it earlier risks merge churn for no visible product gain.
6. **Dynasty Office persistence is JSON-blob shaped.** `program_promises_json` is a list of dicts with no schema enforcement beyond `_ensure_dynasty_keys`, no per-row index, and no per-promise versioning. This was correct for the blitz (V8-V10 design called for thin persistence). It should *not* be the long-term home once promise fulfillment, broken-promise reputation, and recruit memory begin to feed the V8 deeper-loop work the long-range roadmap describes. Future schema work should add `program_promises` and `staff_market_actions` proper tables with the same backfill pattern used at V1-M0.
7. **Legacy desktop GUI modules (`manager_gui.py`, `gui.py`, `dynasty_cli.py`) still hold pure helpers consumed by tests.** They are not entry points anymore. The polish phase should extract pure helpers (`build_prospect_board_rows`, `build_fuzzy_profile_details`, `build_scout_strip_data`, `build_trajectory_reveal_sweep`, `sign_prospect_to_club`, `initialize_manager_career`, `_club_roster`) into neutral modules (`recruitment_views.py`, `manager_career_setup.py`, etc.), then rewrite tests against those modules, then drop the Tk surfaces.

### Low

8. Stale `src/dodgeball_sim.egg-info/entry_points.txt` references the removed `manager_gui:main` and `gui:main` scripts. `pyproject.toml` is the source of truth and is correct. Regenerated on next `pip install -e .`. Not a behavioral defect.
9. `dynasty_office.py` reuses `_class_year_from_season` parsed from the season ID string. This is fine for the blitz but should be replaced with an explicit `Season.class_year` property when the V9 archive deepens.
10. `dynasty_office.evaluate_season_promises` carries a `# Must be called before retirements …` comment as the only contract guard. A small ordering test in `tests/test_offseason_ceremony.py` would lock that invariant in.

## Contract Risks

| # | Contract | Risk | Status |
|---|---|---|---|
| C1 | `_active_save_path` must always point at a managed `.db` save (under `SAVES_DIR`) or the legacy `DEFAULT_DB_PATH` | Pre-fix: any existing path was accepted | **Fixed** |
| C2 | Save deletion must only remove user-managed save files | Pre-fix: any existing path could be deleted | **Fixed (blocker)** |
| C3 | Dynasty Office API must return a recoverable status when `dynasty_state` JSON is corrupt | Pre-fix: leaked as 500 | **Fixed (returns 409)** |
| C4 | A persisted recruiting promise must reference a known prospect or current roster player | Pre-fix: any string accepted | **Fixed** |
| C5 | Save schema migration is governed by `CURRENT_SCHEMA_VERSION` and must remain idempotent across `connect()` cycles | Currently honored; covered by `tests/test_persistence.py` | Stable |
| C6 | Match outcomes are owned by the event log, not by viewers, narration, or Dynasty Office surfaces | Currently honored (Dynasty Office is a read-and-thin-write surface) | Stable |
| C7 | Outcome-affecting RNG flows through `DeterministicRNG` + `derive_seed` | Currently honored — `dynasty_office._candidate_for_head` and prospect fallback both use derived seeds | Stable |

## Migration Strategy

This audit lands the contract fixes inline. There are no schema changes and no save-format changes; saves on disk remain readable and writable across the fix.

- **C1/C2 — managed save paths.** Save load/delete now route every request through `_resolve_managed_save_path()`, which:
  - Resolves the request path against the project root.
  - Accepts only files whose resolved parent is `SAVES_DIR.resolve()`, plus the legacy `DEFAULT_DB_PATH` for `load` (delete still refuses the legacy DB, matching the prior carve-out).
  - Requires a `.db` suffix.
  - Rejects non-existent paths with `404`, traversal/non-managed paths with `403`, missing-suffix with `400`.
  Existing API call sites that send paths produced by `GET /api/saves` continue to work because that endpoint already returns paths under `SAVES_DIR` or `DEFAULT_DB_PATH`.

- **C1 (continued) — load validation.** `api_load_save` now opens the candidate file through `connect()` and reads the schema row before swapping `_active_save_path`. If the file is not a valid SQLite save (or if the schema migration fails), the active save pointer is left untouched and the route returns `400`.

- **C3 — corrupt JSON contract.** All three Dynasty Office routes (`get_dynasty_office`, `create_recruiting_promise`, `hire_dynasty_staff`) now catch `CorruptSaveError` and return `409` with the offending state key. The frontend can use this to show a "this save's dynasty state is damaged" recovery surface in a future polish slice.

- **C4 — promise player_id validation.** `save_recruiting_promise` now requires that `player_id` either appear in the persisted prospect pool for the implied class year *or* in a current club roster (so that previously promised, now-on-roster players can have their promise marked broken/fulfilled correctly during the offseason evaluation). Unknown IDs return `400`.

No save backfill is required. The fixes are additive at the API boundary, idempotent on existing data, and do not change any persisted column.

## Decoupling Recommendations

These are recommendations for the *next* polish slice, not part of this audit's edits.

1. **Route module split.** Split `server.py` along the existing import boundaries:
   - `server/routes_saves.py`
   - `server/routes_dynasty_office.py`
   - `server/routes_command_center.py`
   - `server/routes_sim.py`
   - `server/routes_replay.py`
   - `server/routes_offseason.py`
   Keep `server.py` as the FastAPI app object + middleware + `_active_save_path` state and `get_db` dependency. Each route module is a thin adapter around an already-pure domain module.

2. **Dynasty Office promise model extraction.** Today `dynasty_office.py` carries data-shape (`PROMISE_OPTIONS`, JSON shape) and orchestration (`evaluate_season_promises`) and surface state (`build_dynasty_office_state`). Pulling promises into `recruitment_promises.py` (data + evaluation) and leaving `dynasty_office.py` as a *facade* that joins recruiting + memory + staff would let V8 deepen without bloating one module.

3. **Pure helpers escape from `manager_gui.py`.** `build_prospect_board_rows`, `build_scout_strip_data`, `build_fuzzy_profile_details`, `build_trajectory_reveal_sweep`, `sign_prospect_to_club`, `_club_roster`, and `initialize_manager_career` should move to neutral modules (likely `recruitment_views.py`, `scouting_views.py`, `manager_career_setup.py`). Tests can then drop the `from dodgeball_sim.manager_gui import …` lines and the Tk surface becomes deletable.

4. **`web_cli.py` should own server lifecycle, not `server.py`.** `_active_save_path` is a process-global today. After the route split, fold the active-save state into a small `SaveSession` object owned by the FastAPI app instance so tests can construct independent sessions instead of mutating `server._active_save_path`.

## Suggested Pre-Next-Phase Refactors

Only the work that materially reduces risk for the next milestone:

1. **(this audit) Save boundary + Dynasty Office error contract fixes.** Done.
2. **(next) Route module split for `server.py`.** Required before adding more endpoints; cheaper now than after V11 lands.
3. **(next) Promise table promotion.** When V8 promise depth grows (multi-promise per recruit, inheritance into next season), promote `program_promises_json` to a real table with a backfill in a new schema migration. This is the moment where the JSON-blob shortcut stops being honest.
4. **(after V11 starts)** Persistence module split. Don't pre-empt the structure until there's real new schema pressure.

## Verification of This Audit's Code Changes

Backend:
- `python -m pytest -q` — see Verification section in the implementation handoff.

The code edits sit only in `server.py`, `dynasty_office.py`, and add `tests/test_server_save_boundary.py` + `tests/test_dynasty_office.py` regression cases. No engine, no persistence schema, no domain logic outside the V8 promise validation gate. Match outcomes, golden logs, and offseason ceremony ordering are untouched.
