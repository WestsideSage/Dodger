# V15 Phase 0 — Traceability Bug Pass: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the small, high-trust traceability-bug slice of V15 so the game's own numbers stop lying — without touching engine/sim math.

**Architecture:** Pure presentation/data-boundary fixes. Land the already-written foam-scoreline backend WIP, then three independent fixes: coerce staff ratings to integers at the payload boundary, reconcile the recruit-board filter labels with the card labels, and correct the Season Preview bye-week legend. No schema migration, no engine change, no new dependencies.

**Tech Stack:** Python 3 backend (`src/dodgeball_sim/`), pytest; React + Vite + TypeScript frontend (`frontend/`); `npm run build` / `npm run lint` / `npm run e2e`.

> **Plan location note:** Saved under `docs/specs/2026-05-30-v15-systems-legibility/` (co-located with the planning report) rather than the skill-default `docs/superpowers/plans/`, to follow this repo's `docs/specs/` convention for active specs/plans (AGENTS.md §Documentation Routing).

> **Pre-flight for the executor:**
> - Repo: `C:\GPT5-Projects\Dodgeball Simulator`, branch `main`. The working tree is **dirty** with staged-but-uncommitted WIP (Task 1 lands it) plus a batch of regenerated `playtest_output/*.png` (leave those un-committed; they are generated artifacts).
> - Use a fresh branch off `main`: `git checkout -b fix/v15-phase0-traceability`.
> - Verify the dev environment first: `python -m pytest -q` should be green before you start. If deps are missing, see AGENTS.md (`.venv` + `python -m pip install -e '.[dev]'`, `npm install` in `frontend/`).
> - This plan changes match-adjacent *display* only. The gate `python tools/tier_engine_health_probe.py` must read identically before and after (no sim drift). Do not edit engine/RNG/scoring files.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `src/dodgeball_sim/command_center.py` | Post-week dashboard "Result" lane scoreline (WIP) | 1 |
| `src/dodgeball_sim/command_week_service.py`, `use_cases.py` | Offseason "sim disabled" player-facing copy (WIP) | 1 |
| `src/dodgeball_sim/web_status_service.py` | Bracket payload game-points (WIP) | 1 |
| `tests/test_command_center.py`, `tests/test_server.py` | WIP tests | 1 |
| `src/dodgeball_sim/staff_market.py` | Staff ratings → integers at payload boundary | 2 |
| `tests/test_staff_market.py` (or existing staff test) | Staff int guarantee | 2 |
| `frontend/src/components/DynastyOffice.tsx` | Recruit-board filter labels/thresholds | 3 |
| `frontend/src/components/dynasty/ProspectCard.tsx` | Card fit label (already correct; reference) | 3 |
| `frontend/src/components/match-week/command-center/SeasonPreview.tsx` | Bye-week legend alignment | 4 |

Each task is independently committable and shippable.

---

## Task 1: Land the staged foam-scoreline backend WIP

**Context:** The foam aftermath *hero* is already fixed on `main` (`MatchScoreHero.tsx` + `matchResult.ts`). The working tree already contains the *secondary*-surface mop-up — written, with tests — but uncommitted: the post-week dashboard "Result" lane now reports official **game points** instead of the misleading box-score `living` survivor count (`command_center._result_scoreline`), the offseason "sim disabled" error returns player-facing copy instead of leaking the `season_active_pre_match` enum (`command_week_service.py`, `use_cases.py`), and the bracket payload exposes `scoring_model`/`home_game_points`/`away_game_points` (`web_status_service.py`). This task verifies and lands it as the first isolated commit.

**Files:**
- Modify (already edited in working tree): `src/dodgeball_sim/command_center.py`, `command_week_service.py`, `use_cases.py`, `web_status_service.py`
- Test (already edited in working tree): `tests/test_command_center.py`, `tests/test_server.py`

- [ ] **Step 1: Review the staged diff so you know exactly what you're landing**

Run: `git diff -- src/dodgeball_sim/command_center.py src/dodgeball_sim/command_week_service.py src/dodgeball_sim/use_cases.py src/dodgeball_sim/web_status_service.py tests/test_command_center.py tests/test_server.py`
Expected: a `_result_scoreline()` helper returning `(score, unit)` (game points for official, survivors for legacy); an `_off_phase_sim_message()` helper returning player copy for offseason states; and three new SELECT columns in `build_playoff_bracket_payload`. Confirm there are **no** engine/RNG/scoring edits in the diff.

- [ ] **Step 2: Run the WIP's own tests; verify they pass**

Run: `python -m pytest tests/test_command_center.py tests/test_server.py -q`
Expected: PASS. (The diff added ~42 lines to `test_command_center.py` and ~5 to `test_server.py` covering the foam game-points scoreline and the 409 offseason copy.)

- [ ] **Step 3: Confirm the offseason copy never leaks the enum token**

Run: `git grep -n "season_active_pre_match" -- src/dodgeball_sim/command_week_service.py src/dodgeball_sim/use_cases.py`
Expected: the raw token appears only in *state comparisons* (`cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH`), never inside a user-facing string. The user-facing strings are "The regular season is complete — continue in the offseason…" and "There's no match ready to simulate right now."

- [ ] **Step 4: Full suite + no-sim-drift gate**

Run: `python -m pytest -q`
Expected: green (~1085 tests).
Run: `python tools/tier_engine_health_probe.py --driver official --trials 50`
Expected: runs clean; record the OVR-curve / draw-rate summary to compare against post-Task-4 (must not change across this plan).

- [ ] **Step 5: Commit (only the WIP source + tests; not the generated PNGs)**

```bash
git add src/dodgeball_sim/command_center.py src/dodgeball_sim/command_week_service.py src/dodgeball_sim/use_cases.py src/dodgeball_sim/web_status_service.py tests/test_command_center.py tests/test_server.py
git commit -m "fix(v15-p0): foam scoreline on dashboard + bracket payload + offseason sim copy

Post-week 'Result' lane reports official game points instead of the
box-score living survivor count; bracket payload carries game points so a
foam 0-0 shows the set score; offseason 'sim disabled' returns player copy
instead of leaking the season_active_pre_match enum.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Kill the staff/coach OVR float leak

**Context:** Staff ratings are stored as SQLite `REAL` (`persistence.py:831`) and rendered raw in the frontend (`DynastyOffice.tsx:198, 313, 320, 323-324, 379`), so a `72.0` leaks to the UI. `staff_market.py` also builds candidate ratings via `rng.roll(...)` (floats) and an effect-lane string with `:.1f`. The cleanest fix is one **backend payload-boundary coercion**: round every rating the `staff_market` payload emits to `int`. This fixes all current_staff and candidate display surfaces at once, needs no schema migration, and no frontend change. (Internal rating math elsewhere, e.g. `offseason_ceremony.py`/`matchup_details.py`, keeps full precision — only the *displayed* payload is coerced.)

**Files:**
- Modify: `src/dodgeball_sim/staff_market.py` (`build_staff_market_state`, `_candidate_for_head`, `_staff_effect_lanes`)
- Test: `tests/test_staff_market.py` (create if absent; otherwise add to the existing staff-market test module — confirm with `git ls-files tests | grep -i staff`)

- [ ] **Step 1: Write the failing test**

Create/append `tests/test_staff_market.py`:

```python
import sqlite3

from dodgeball_sim.staff_market import build_staff_market_state


def _seed_minimal(conn: sqlite3.Connection) -> None:
    # Department heads are stored as REAL; seed a fractional rating to prove
    # the payload coerces it to int on the way out. Schema already exists
    # because the connection came from persistence.connect() in the test.
    conn.execute(
        "INSERT INTO department_heads (department, name, rating_primary, rating_secondary, voice)"
        " VALUES (?, ?, ?, ?, ?)",
        ("training", "Sam Reed", 72.4, 61.7, "Reps build the ceiling."),
    )
    conn.commit()


def test_staff_payload_ratings_are_integers(tmp_path):
    from dodgeball_sim import persistence

    db = tmp_path / "staff.db"
    conn = persistence.connect(str(db))
    _seed_minimal(conn)

    state = build_staff_market_state(
        conn, season_id="season_1", player_club_id="club_user", root_seed=7
    )

    for member in state["current_staff"]:
        assert isinstance(member["rating_primary"], int), member
        assert isinstance(member["rating_secondary"], int), member
    for candidate in state["candidates"]:
        assert isinstance(candidate["rating_primary"], int), candidate
        assert isinstance(candidate["rating_secondary"], int), candidate
        # No ".0" float text leaks into the effect lanes either.
        for lane in candidate["effect_lanes"]:
            assert ".0/" not in lane and not lane.endswith(".0")
            assert ".4" not in lane and ".7" not in lane
```

> Before running, confirm the seed columns/table name match the schema: `git grep -n "CREATE TABLE" -- src/dodgeball_sim/persistence.py | grep -i department`. If the table is named differently or `connect()` needs a path vs connection, adjust the fixture to the repo's existing staff-test pattern (`git grep -n "department_heads\|load_department_heads" -- tests`).

- [ ] **Step 2: Run the test; verify it fails**

Run: `python -m pytest tests/test_staff_market.py::test_staff_payload_ratings_are_integers -v`
Expected: FAIL — `current_staff` ratings are `float` (e.g. `72.4`), candidate lanes contain `.4`/`.0`.

- [ ] **Step 3: Coerce ratings to int at the payload boundary**

In `src/dodgeball_sim/staff_market.py`, in `build_staff_market_state`, round current-staff ratings when building `current_staff`:

```python
    current_staff = [
        {
            **head,
            "rating_primary": round(float(head["rating_primary"])),
            "rating_secondary": round(float(head["rating_secondary"])),
            "effect_summary": staff_effect_summary(head["department"]),
        }
        for head in load_department_heads(conn)
    ]
```

In `_candidate_for_head`, emit integer ratings:

```python
    primary = round(min(99.0, float(head["rating_primary"]) + primary_gain))
    secondary = round(min(99.0, float(head["rating_secondary"]) + secondary_gain))
```

(`primary`/`secondary` are now `int`; keep `primary_gain`/`secondary_gain` as-is — they are only used in this addition.)

In `_staff_effect_lanes`, change the signature to ints and drop the `:.1f`:

```python
def _staff_effect_lanes(department: str, primary: int, secondary: int) -> list[str]:
    return [
        staff_effect_summary(department),
        f"Visible staff ratings would become {primary}/{secondary}.",
    ]
```

- [ ] **Step 4: Run the test; verify it passes**

Run: `python -m pytest tests/test_staff_market.py -v`
Expected: PASS.

- [ ] **Step 5: Guard the regression in the full suite (some existing tests may assert old float strings)**

Run: `python -m pytest -q`
Expected: green. If a pre-existing test asserts a float like `"72.0"` or `rating_primary == 72.0` for a staff payload, update that assertion to the integer form (the float was the bug). Do **not** change non-staff tests.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/staff_market.py tests/test_staff_market.py
git commit -m "fix(v15-p0): staff ratings render as integers (kill float leak)

Coerce staff/candidate ratings to int at the staff_market payload
boundary so the Dynasty Office staff cards stop showing 72.0; no schema
change, internal rating math keeps full precision.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Reconcile the recruit-board filter labels

**Context:** `DynastyOffice.tsx:236-239` counts prospects into chips `Strong Fit (fit_score ≥ 80)` and `Visit-Ready (fit_score ≥ 65)` — overlapping thresholds on one metric, and "Visit-Ready" has nothing to do with the Visit action (it falsely implies visit eligibility). Worse, `ProspectCard.tsx:101` labels the *same* `fit ≥ 65` band "Neutral". The fix makes the filter buckets **mutually exclusive** and **consistently named with the card**: Strong Fit (≥80), Fair Fit (65–79), At Risk (<65) — matching the card's three-tier language (`strong` / `neutral`→"Fair Fit" / `risk`).

**Decision (locked):** rename the card's middle tier from "Neutral" to "Fair Fit" and use the same three mutually-exclusive buckets in the filter. This removes the visit-implying "Visit-Ready" label entirely (visit mechanics are a deferred spec; the board's filter must not imply them).

**Files:**
- Modify: `frontend/src/components/DynastyOffice.tsx:236-239` (filter chips)
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx:101` (card middle-tier label)

- [ ] **Step 1: Read the current filter block to confirm exact surrounding markup**

Run: `git grep -n "Strong Fit\|Visit-Ready\|Neutral" -- frontend/src`
Expected: the two filter `<span className="n">` counts in `DynastyOffice.tsx` and the `fitLabel` ternary in `ProspectCard.tsx`. Note the exact JSX wrapper around the two chips so your replacement matches.

- [ ] **Step 2: Update the card middle-tier label to "Fair Fit"**

In `frontend/src/components/dynasty/ProspectCard.tsx`, line 101:

```tsx
  const fitLabel = prospect.fit_score >= 80 ? 'Strong Fit' : prospect.fit_score >= 65 ? 'Fair Fit' : 'At Risk';
```

(Leave `fitTier` on line 100 unchanged — `strong`/`neutral`/`risk` are CSS class keys, not user-facing.)

- [ ] **Step 3: Make the filter buckets mutually exclusive and consistently named**

In `frontend/src/components/DynastyOffice.tsx`, replace the `Strong Fit` / `Visit-Ready` chip pair (lines ~236-239) with three non-overlapping buckets matching the card:

```tsx
            Strong Fit <span className="n">{prospects.filter((prospect) => prospect.fit_score >= 80).length}</span>
          </button>
          <button /* keep whatever button/markup wrapper the existing chips use */>
            Fair Fit <span className="n">{prospects.filter((prospect) => prospect.fit_score >= 65 && prospect.fit_score < 80).length}</span>
          </button>
          <button /* keep wrapper */>
            At Risk <span className="n">{prospects.filter((prospect) => prospect.fit_score < 65).length}</span>
```

> Match the exact element type/handlers/`className` of the existing chips (they may be `<button>` filter toggles with an `onClick` that sets a filter state, or static labels). If they are interactive filters, wire "Fair Fit"/"At Risk" to the same filter mechanism the old chips used, keyed by the same three-tier predicate. Confirm by reading the chip click handler before editing.

- [ ] **Step 4: Build + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: clean. The three bucket counts now sum to the "All" count (mutually exclusive), and no chip says "Visit-Ready".

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DynastyOffice.tsx frontend/src/components/dynasty/ProspectCard.tsx
git commit -m "fix(v15-p0): recruit-board fit filters are exclusive and card-consistent

Replace overlapping Strong Fit (>=80) / Visit-Ready (>=65) chips with
mutually-exclusive Strong Fit / Fair Fit / At Risk buckets that sum to the
All count and match the card labels; drop 'Visit-Ready', which falsely
implied visit eligibility (visit mechanics are a deferred spec).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Correct the Season Preview bye-week legend

**Context:** In `SeasonPreview.tsx`, the colored timeline bar is correctly keyed to its week (`weeks.map`, `isBye = byeWeek === w`, lines 88-101). But the legend row beneath (`:127-135`) is a 3-item flex row — `Week 1` … `{preview.bye_text}` … — whose middle item sits by flex spacing, *not* under the bye bar, so it reads as mislabeled ("Week 2 Bye appeared under the 4th bar"). The fix: stop implying a position for the bye in the legend. Either (a) anchor the bye marker to its actual bar, or (b) make the legend a non-positional caption. Option (b) is lower-risk and mobile-safe.

**Files:**
- Modify: `frontend/src/components/match-week/command-center/SeasonPreview.tsx` (legend row ~127-135)
- Test: `frontend/` e2e (optional smoke) — primary verification is build + visual

- [ ] **Step 1: First, rule out a real data off-by-one**

Run: `git grep -n "bye_week\|bye_text\|regular_season_weeks" -- src/dodgeball_sim`
Read `build_season_preview` (in `season_preview.py`). Confirm `bye_week` is a 1-based week number consistent with the `weeks = 1..regular_season_weeks` the component renders. If `bye_week` is 0-based or off by one vs the schedule, that is the real bug — fix it in the backend and add a backend unit test asserting `bye_week` matches the schedule's actual bye, then skip to Step 4. If `bye_week` is correct (expected), continue to Step 2 (the defect is purely the legend's visual position).

- [ ] **Step 2: Make the legend non-positional (caption, not a fake axis)**

In `frontend/src/components/match-week/command-center/SeasonPreview.tsx`, replace the 3-item space-between legend row (lines ~127-135 — the `<span>Week 1</span> … {bye_text} … ` row) with start/end axis ticks plus a separate, clearly-captioned bye note that does not pretend to sit under a bar:

```tsx
        {/* Axis endpoints only — the bye is called out in the caption below,
            not implied by horizontal position (which previously misread). */}
        <div className="season-preview-axis" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Week 1</span>
          <span>Week {preview.regular_season_weeks}</span>
        </div>
        <p className="season-preview-bye-note" style={{ color: '#f59e0b', fontWeight: 700, margin: '0.35rem 0 0' }}>
          {preview.bye_text}
        </p>
```

(Keep the existing `stat('Your Bye', preview.bye_text, …)` summary stat — it remains accurate. The amber bar in the timeline still marks the true bye week via its `title`.)

- [ ] **Step 3: Verify in the browser at mobile width**

Use the preview workflow (preview_start, navigate to a fresh career's Season Preview), confirm at 390×844 that the bye is no longer implied under the wrong bar, the amber bar still marks the bye week, and there is no horizontal overflow. Capture a screenshot as proof.

- [ ] **Step 4: Build + lint + commit**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: clean.

```bash
git add frontend/src/components/match-week/command-center/SeasonPreview.tsx
git commit -m "fix(v15-p0): Season Preview bye legend no longer implies wrong bar

The legend row placed bye_text by flex spacing, so it read as sitting
under the wrong week's bar. Replace with non-positional axis endpoints +
an explicit bye caption; the amber timeline bar still marks the true bye.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 0 Exit Gates

Run all before declaring Phase 0 done:

- [ ] `python -m pytest -q` — green.
- [ ] `python tools/tier_engine_health_probe.py --driver official --trials 50` — summary **identical** to the Task 1 Step 4 baseline (proves zero sim drift; this whole phase is display-only).
- [ ] From `frontend/`: `npm run build` && `npm run lint` — clean.
- [ ] From repo root: `npm run e2e` — zero Playwright failures (or, if e2e infra is heavy locally, at minimum the command-center + dynasty specs).
- [ ] Manual sanity at 390×844 on a fresh "Build from Scratch" career: Dynasty Office staff ratings show integers; recruit-board fit chips are exclusive and sum to All; Season Preview bye reads correctly.
- [ ] No `playtest_output/*.png` or local `*.db` files committed.

## Out of Scope for Phase 0 (do NOT do here)
- The legibility toolkit (terms registry, explainer, fog-of-war, proof chip, honest empty-states) — that is **Phase 1**, its own plan.
- Any copy/jargon rewrite (credibility "01/02/03", standings phrasing, history) — Bucket B, later phases.
- The pipeline emblem, archetype tooltips, staff *impact* visibility — later phases.
- Deferred specs: archive tree, office hub, visit mechanic; and the separate sim-balance ticket (foam draw density, catch-lever dominance).
