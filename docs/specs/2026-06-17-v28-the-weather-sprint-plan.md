# V28 — The Weather: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the ecosystem its own weather so the game never fully solves — data-derived league trend journalism on the news ticker, AI programs that drift toward winning tactics (with a contrarian generation that breaks the orthodoxy), and seasonal officiating points of emphasis logged symmetrically — all from real match data, no injected dials, behind `pyramid_world_active` so legacy is byte-identical. Closes the Climb-Era arc (V23–V28).

**Architecture:** Three independent halves. Journalism (`meta_journalism.py`) is read-only over persisted `match_records`/`player_match_stats`/`team_policies`. Emergent meta (`meta_drift.py`) computes winning tactics from real results each offseason and nudges a per-club tactic-tendency overlay consumed by `ai_tactics.get_ai_tactics` (+ a contrarian fraction). Officiating emphasis threads a `SeasonEmphasis` dataclass (separate from the frozen `RulesetProfile`) into the match runner, shifting the EXISTING catch/block sigmoid bias before the EXISTING roll (no new RNG draw → default-zero is byte-identical) and logging `RuleDiscretionEvent`s. `meta.py`/MetaPatch stays retired.

**Tech Stack:** Python 3 (SQLite aggregate queries, `dynasty_state` JSON, `rng.derive_seed`, the `RuleDiscretionEvent`/`OfficialEvent(kind=DISCRETION)` pipeline), pytest; React + TS (no test runner — build/lint + Python guards).

**Spec:** `docs/specs/2026-06-17-v28-the-weather-spec.md`. **Era authority:** `docs/specs/2026-06-12-climb-era-vision.md` § V28. **Branch:** `feature/v24-the-board`.

**Standing rules (hard-won this arc):**
- `python -m pytest -q` to a real exit code; **never pipe pytest to `tail`**.
- New `derive_seed` namespaces only (`v28_meta_drift`, `v28_emphasis`).
- **THE #1 LANDMINE:** do NOT add an RNG draw inside `resolve_throw`/`decide_catch_attempt` — shift the existing bias before the existing roll, or every official-match golden witness breaks. `SeasonEmphasis()` (deltas 0.0) MUST be byte-identical to pre-V28.
- `meta.py`/MetaPatch stays retired (`test_meta_module_has_no_db_boundary_imports`); compute weather from data, never an injected dial.
- `season_id` ordering via `season_sort_key`; exclude playoff match-ids (`LIKE '{season}_p_%'`); use `fetch_season_player_stats` (not the lossy `player_season_stats`); posture trends only from official matches (`team_policies` in `official_score_json`).
- Pyramid-gate everything; verify legacy byte-identical. Prefer the existing ticker + season-preview surfaces over a new offseason beat (avoid another `_MAX_OFFSEASON_BEAT_INDEX` bump).

---

## File Structure

**New files:**
- `src/dodgeball_sim/meta_journalism.py` — `compute_league_trends(conn, season_id)` (pure-ish aggregate query) + `generate_league_bulletin(conn, season_id)` (writes `category='meta_report'` headlines, derivable-from-data).
- `src/dodgeball_sim/meta_drift.py` — `winning_tactics(conn, season_id)` + `apply_meta_drift(conn, season_id, root_seed)` (offseason overlay update + contrarian fraction) + `tactic_drift_for(conn, club_id)` (the overlay read consumed by ai_tactics).
- `src/dodgeball_sim/season_emphasis.py` — `SeasonEmphasis` dataclass, `select_season_emphasis(conn, season_id, root_seed)`, `generate_officiating_bulletin(conn, season_id, root_seed)`, `load_season_emphasis(conn)`.
- `src/dodgeball_sim/config.py` — `WeatherConfig`/`DEFAULT_WEATHER`.
- `tools/meta_journalism_probe.py`, `tools/meta_drift_probe.py`, `tools/emphasis_probe.py`.
- `tests/test_v28_meta_journalism.py`, `test_v28_meta_drift.py`, `test_v28_emphasis.py`.

**Modified files:**
- `src/dodgeball_sim/web_status_service.py` — widen `build_news_payload`'s category filter to admit `meta_report` / `league_bulletin` (additive after V27's `event_news`).
- `src/dodgeball_sim/ai_tactics.py` — `get_ai_tactics` consumes the per-club tactic-drift overlay (precedence: archetype base → intent override → drift bias).
- `src/dodgeball_sim/offseason_ceremony.py` — call `generate_league_bulletin` + `apply_meta_drift` + `select_season_emphasis`/`generate_officiating_bulletin` in the offseason sweep (pyramid+user-world).
- `src/dodgeball_sim/official_resolution.py` / `official_tactics.py` — apply the `SeasonEmphasis` bias shift before the existing catch/block roll + emit the DISCRETION event.
- `src/dodgeball_sim/official_engine.py` (`run_autonomous_match`/`run_autonomous_game`) — thread `SeasonEmphasis` through (default `SeasonEmphasis()`).
- `src/dodgeball_sim/official_conformance_ledger.py` — entries for the new emphasis discretion space.
- `src/dodgeball_sim/command_week_service.py` — inject the officiating bulletin into the season-preview payload.
- `frontend/src/{types.ts, ...news + season-preview components}`.

---

## Phase 1 — Meta journalism (trend reports on the ticker)

### Task 1.1: `compute_league_trends` (TDD)
- [ ] `WeatherConfig` in config.py (trend `notable_delta`, drift rate, contrarian fraction, emphasis bounds).
- [ ] Failing tests (`tests/test_v28_meta_journalism.py`): on a career with persisted official matches, `compute_league_trends` returns catch rate / elimination rate / game-point margin per division (excluding playoff match-ids, via `fetch_season_player_stats`), and posture win-correlation from `team_policies`; every returned number recomputes from the same rows (the derived-from-data fence). Build a small fixture of `match_records` + `player_match_stats` rows.
- [ ] Implement `compute_league_trends`; commit.

### Task 1.2: `generate_league_bulletin` + news-filter widening (TDD)
- [ ] Failing tests: `generate_league_bulletin` writes `category='meta_report'` headlines whose text claims are backed by `compute_league_trends` (a claim recomputes to its headline); idempotent (its own `v28_bulletin_for` guard). A `meta_report` headline is surfaced by `build_news_payload` (today dropped — only `class_wire` passes; V27 adds `event_news`).
- [ ] Widen the filter (additive); implement; call it at the offseason sweep (pyramid). Full suite green; commit `feat(v28): meta journalism — data-derived league trend reports`.

---

## Phase 2 — Emergent meta (ecosystem tactic drift)

### Task 2.1: `winning_tactics` + drift overlay (TDD)
- [ ] Failing tests (`tests/test_v28_meta_drift.py`): `winning_tactics(conn, season_id)` returns, per CoachPolicy dimension, which value won most (from `team_policies` vs `winner_club_id` on official matches); `apply_meta_drift` nudges each AI club's `v28_tactic_drift_json` overlay toward the winners (bounded by `WeatherConfig.drift_rate`); a deterministic **contrarian fraction** (`v28_meta_drift` stream) drifts AWAY; idempotent per season.
- [ ] Implement; commit.

### Task 2.2: Consume the overlay in `get_ai_tactics` (TDD)
- [ ] Failing tests: an AI club with a drift overlay toward, e.g., `go_for_catches` produces a `CoachPolicy` biased that way vs an un-drifted club; precedence is audited (archetype base → intent override → drift bias, no collisions); the user club is never drifted; determinism preserved (the overlay only changes AI policy — a real CoachPolicy the engine already consumes, no special math).
- [ ] Implement; `tools/meta_drift_probe.py` (across N simulated seasons: AI tactics drift toward the prior winners AND a contrarian generation breaks a dominant tactic — anti-solvedness). Full suite green; commit `feat(v28): emergent meta — AI tactic drift toward winning play + a contrarian generation`.

---

## Phase 3 — Officiating points of emphasis (the engine-touching half)

### Task 3.1: `SeasonEmphasis` + the default-zero byte-identical fence (TDD)
- [ ] Create `season_emphasis.py` (`SeasonEmphasis(catch_delta=0.0, block_delta=0.0, announcement="")`). Thread it as a SEPARATE argument (default `SeasonEmphasis()`) through `run_autonomous_match` → `run_autonomous_game` → `resolve_throw`/`decide_catch_attempt`.
- [ ] **Failing fence test (the #1 obligation):** a seeded official season run with `SeasonEmphasis()` (default) is **byte-identical** to the pre-V28 golden (no extra RNG draw, no shifted constant). Re-capture the existing official-engine golden witnesses and assert identity at delta 0.
- [ ] Implement the threading so default-0 is a no-op; commit.

### Task 3.2: Apply + log the emphasis shift (TDD)
- [ ] Failing tests (`tests/test_v28_emphasis.py`): a non-zero `catch_delta` shifts the EXISTING `_CATCH_BIAS` before the EXISTING catch roll (NO new `rng` call), changing catch outcomes; the shift is applied to BOTH sides equally (symmetry — assert a mirrored scenario flips identically); every sequence the delta changed emits a `RuleDiscretionEvent(selection_basis='emphasis_<season>')` visible in `collect_official_metadata`'s `discretion_events`.
- [ ] Implement in `official_resolution`/`official_tactics`; add conformance-ledger entries for the new discretion space. Commit.

### Task 3.3: The preseason League Bulletin (TDD)
- [ ] Failing tests: `select_season_emphasis(conn, season_id, root_seed)` picks a bounded emphasis on the `v28_emphasis` stream; `generate_officiating_bulletin` persists `v28_season_emphasis_json`, writes a `league_bulletin` news headline, and the match runner reads the active emphasis for that season's official matches. Announced preseason (week 0), symmetric, logged.
- [ ] Implement; wire into the offseason sweep / season start. `tools/emphasis_probe.py` (default byte-identical; active emphasis shifts symmetrically + logs; no RNG drift). Full suite green; commit `feat(v28): officiating points of emphasis (sourced, symmetric, logged; default byte-identical)`.

---

## Phase 4 — Frontend + verification + docs (Climb-Era close-out)

### Task 4.1: Surface the meta report + officiating bulletin (frontend)
- [ ] The `meta_report` + `league_bulletin` headlines render in the news ticker (they already flow once the filter is widened); inject the officiating bulletin into the Week-1 season-preview orientation screen (`build_season_preview` payload + the preview component). `types.ts` additions. No new offseason beat (use the ticker + preview).
- [ ] `npm run build` + `npm run lint` clean; Python guards on the rendered bulletin strings. Commit.

### Task 4.2: Verification + docs + arc close-out
- [ ] `python -m pytest -q` green (real exit code, NOT `| tail`).
- [ ] `tools/{meta_journalism_probe,meta_drift_probe,emphasis_probe}.py` pass (derivable-from-data; drift + contrarian generation; default byte-identical + symmetric + logged).
- [ ] Live prod-server walk: read a league trend report, see a preseason officiating bulletin, observe AI tactics having drifted across seasons. Zero console errors; purge the walk save.
- [ ] Update `docs/STATUS.md` + `docs/specs/MILESTONES.md`; write `docs/retrospectives/2026-XX-XX-v28-the-weather-retrospective.md` AND a Climb-Era arc close-out note (V23–V28). The whole arc is now ready to merge to `main` as a unit.
- [ ] Commit.

---

## Self-Review (spec coverage)

| Spec requirement | Task(s) |
|---|---|
| Emergent meta = data-derived AI tactic drift | 2.1, 2.2 |
| Contrarian generation breaks the orthodoxy | 2.1, 2.2 |
| `MetaPatch` stays retired (no injected dials) | (architecture — meta.py untouched) |
| Meta journalism = derivable-from-data trends on the ticker | 1.1, 1.2 |
| Officiating emphasis: sourced, symmetric, logged | 3.2, 3.3 |
| Emphasis default-zero byte-identical (no new RNG) | 3.1 |
| `SeasonEmphasis` separate from the frozen profile | 3.1 |
| News-filter widening for `meta_report`/`league_bulletin` | 1.2 |
| Pyramid-gated, legacy byte-identical | 1.2, 2.2, 3.1, 4.2 |
| Journalism / symmetry / drift / determinism probes | 1.2, 2.2, 3.3, 4.2 |
| Climb-Era arc close-out | 4.2 |

No placeholder steps remain at the phase-task level; per-phase TDD code is finalized against source at execution (the engine surfaces — `resolve_throw`, `run_autonomous_game`, `get_ai_tactics`, `build_news_payload` — are read live per the verify-before-editing rule, with the no-extra-RNG constraint enforced in Task 3.1's fence).
