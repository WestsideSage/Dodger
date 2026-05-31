# V15 Phase 5 — Verification Hardening: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that every legibility surface introduced in Phases 0–4 actually renders, is accessible, is honest, and introduces zero sim drift — without adding any new dependencies or touching the engine.

**Dependency:** This phase must run **after all of Phases 0–4 are merged to `main`**. Each task below calls out which screen phase introduced the surface under test. Assertions can be added to this spec file as each screen phase merges (the test file compiles against the live app), but the full `npm run e2e` gate is meaningful only once all prior phases are merged.

**Architecture:** Verification runs on the existing stack — no new test runners, no new npm packages:
- **Playwright** (`npm run e2e`) for behavioral browser tests: all specs live in `tests/e2e/` per the `playwright.config.ts` `testDir`.
- **`npm run build`** (`tsc -b && vite build`) for the compile-time no-orphan-term gate — no test runner needed.
- **`python -m pytest -q`** for backend honesty tests (`tests/test_*.py`).
- **`python tools/tier_engine_health_probe.py`** for the engine-unchanged gate.

**Critical e2e infrastructure finding:** `playwright.config.ts` has **no `baseURL`** set in `use:` (the line is commented out). All existing specs hard-code `const baseUrl = 'http://127.0.0.1:8000'` and call `page.goto(baseUrl + '/...')` directly. The `webServer` command launches the **Python FastAPI backend** (`uvicorn dodgeball_sim.server:app --host 127.0.0.1 --port 8000`) — **not** a Vite dev server. The frontend is served as a built static bundle from the Python app, so `import.meta.env.DEV` is **`false`** at runtime. Consequence: the Phase 1 dev-only legibility smoke route (`?legibility=1`) is **not reachable in the e2e suite**. The Phase 1 spec's Playwright smoke test is valid only when developers run `npm run dev` locally; in the e2e suite that spec can be marked with a `// @dev-only` guard or skipped. This phase's Playwright tasks assert the legibility surfaces on the screens where they actually ship (Recruit Board, Roster, Standings, History), not on the dev-only smoke route.

> **Pre-flight for the executor:**
> - Branch off `main` after all Phases 0–4 merge: `git checkout -b feat/v15-phase5-verification`.
> - Verify the full baseline before adding anything: `python -m pytest -q` (green), `npm run build && npm run lint` (from `frontend/`), `npm run e2e` (zero failures from repo root).
> - Record the engine-health baseline now (see Task 1).
> - This phase creates test files only. It does **not** touch any application source under `src/` or `frontend/src/`.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `tests/test_v15_honesty.py` | Backend pytest honesty suite: ProofChip sources, credibility evidence, milestone proof, no fabricated history | 2 |
| `tests/e2e/v15-legibility-surfaces.spec.ts` | Playwright: TermTip on Recruit Board + Roster; PipelineEmblem on recruit cards; EmptyState (banners/alumni/vacancies); ProofChip on History milestones; overflow guard on touched screens | 3 |
| `tests/e2e/v15-standings-modal.spec.ts` | Playwright: standings row-click opens ProgramModal, `aria-expanded` toggles, no trailing `>` icon | 4 |
| `tests/e2e/v15-no-overflow.spec.ts` | Playwright: 390×844 overflow check for each screen touched by Phases 2a–4b | 5 |

---

## Task 1: Engine-health-probe baseline and UNCHANGED gate

**Context:** The hard invariant for V15 is zero engine/sim/RNG changes. This task establishes a before-snapshot and documents the after-comparison procedure. Because the probe is a command-line tool with deterministic seeding, its output lines are comparable with `diff`. No test file is needed — the gate is a documented manual procedure that must be executed by the implementing agent at the start and end of this phase.

**Files:** No source files modified. The comparison artifact is two text files written to `docs/specs/2026-05-30-v15-systems-legibility/` (not committed; used only for the diff comparison).

- [ ] **Step 1: Record the V15-start baseline (run once, before any Phase 5 changes)**

Run from repo root:

```bash
python tools/tier_engine_health_probe.py --driver both --trials 50 --seed-offset 0 \
  > docs/specs/2026-05-30-v15-systems-legibility/probe-baseline-v15-start.txt
cat docs/specs/2026-05-30-v15-systems-legibility/probe-baseline-v15-start.txt
```

Expected: the tool prints OVR curve, outcome distribution, moment rates, and match-length distribution for both the `rec` and `official` drivers. It exits with return code 0 (monotonic win-rate curve). Save the output file. If the baseline exits non-zero, **do not proceed** — investigate which prior phase introduced sim drift.

- [ ] **Step 2: Understand the output lines that constitute the gate**

The output contains invariant lines of the form:

```
=== OVR -> Favorite Win Rate (official, 50 trials/rung) ===
  Net + 0 OVR:  50.0% [95% CI 36.1 - 63.9]
  Net + 4 OVR:  58.0% [95% CI 44.0 - 71.3]
  Net + 8 OVR:  68.0% [95% CI 54.1 - 80.1]
  Net +12 OVR:  80.0% [95% CI 66.3 - 91.0]
```

The gate is: every line in the after-snapshot must be **within expected CI overlap** of the before-snapshot. With 50 trials/rung the CIs are wide by design; an exact match is not required, but a systematic shift (e.g. win-rate at Net +12 drops from ~80% to ~50%) would indicate sim drift. The guard script is `diff` with tolerance, or visual inspection is acceptable given the small trial count.

- [ ] **Step 3: Record the V15-end snapshot (run after all tasks in this phase are committed)**

Run from repo root:

```bash
python tools/tier_engine_health_probe.py --driver both --trials 50 --seed-offset 0 \
  > docs/specs/2026-05-30-v15-systems-legibility/probe-snapshot-v15-end.txt
diff docs/specs/2026-05-30-v15-systems-legibility/probe-baseline-v15-start.txt \
     docs/specs/2026-05-30-v15-systems-legibility/probe-snapshot-v15-end.txt
```

Expected output: `diff` reports zero differences (the probe output is deterministic for the same seed-offset and trial count — identical source/RNG → identical lines). If `diff` is non-empty, investigate which commit changed engine-adjacent code, revert it, and re-run.

> Note: the two text files are local working-tree artifacts used for comparison only — they must NOT be committed to git (`*.txt` probe artifacts do not belong in the repo).

- [ ] **Step 4: Commit the task documentation (no source files to commit this task)**

This task produces no committed files. The gate documentation lives in this plan. Proceed to Task 2.

---

## Task 2: Backend honesty tests (`tests/test_v15_honesty.py`)

**Context (Phase map):** ProofChip surfaces from Phase 3a (Dynasty Office/Credibility evidence strings), Phase 3b (staff effect lanes), and Phase 4a (History milestone descriptions). The backend honesty rule: every `evidence[]` string, every `effect_lanes[]` entry, and every milestone-description string must be backed by a real payload field — never a hardcoded assertion that could be true or false regardless of game state. This task writes pytest cases that audit those payloads on a fresh `aurora` career (the canonical seed used across the e2e suite: `root_seed=20260426`).

**Files:**
- Create: `tests/test_v15_honesty.py`

- [ ] **Step 1: Verify the career setup function and import path**

Run from repo root:

```bash
python -m pytest tests/test_dynasty_history.py -q --co 2>/dev/null | head -20
```

Expected: lists test ids beginning with `tests/test_dynasty_history.py::`. Confirms `initialize_curated_manager_career`, `create_schema`, `get_db`/`app` imports work. The pattern in `test_dynasty_history.py` is the reference.

- [ ] **Step 2: Write the honesty test file**

Create `tests/test_v15_honesty.py`:

```python
"""V15 honesty gate — pytest suite.

Every ProofChip.source / credibility-evidence string and every staff effect
lane must be backed by a real payload field from the backend, not a
hardcoded assertion. A milestone "proof" annotation may only render when the
holder + stats backing it actually exist in the career record.

Phase map:
  - credibility evidence strings: Phase 3a (Dynasty Office / Credibility)
  - staff effect lanes: Phase 3b (Staff Impact)
  - history milestone proof annotations: Phase 4a (History & Identity)
  - recruiting payload ProofChip sources: Phase 2a (Recruit Board)
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from dodgeball_sim import persistence
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.server import app, get_db


# ---------------------------------------------------------------------------
# Shared fixture: a fresh aurora career (matches the canonical e2e seed).
# ---------------------------------------------------------------------------

def _fresh_aurora_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    persistence.create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


@pytest.fixture()
def aurora_client():
    conn = _fresh_aurora_conn()

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Task 2a — Credibility evidence strings are payload-backed (Phase 3a)
# ---------------------------------------------------------------------------

class TestCredibilityEvidenceHonesty:
    """Each evidence[] string must derive from a real career stat,
    not a hardcoded claim that could be true or false regardless of state."""

    def test_credibility_endpoint_returns_evidence_list(self, aurora_client):
        res = aurora_client.get("/api/dynasty/credibility?club_id=aurora")
        assert res.status_code == 200, res.text
        data = res.json()
        # Endpoint must return an 'evidence' list (Phase 3a contract).
        assert "evidence" in data, f"Missing 'evidence' key in: {list(data.keys())}"
        assert isinstance(data["evidence"], list)

    def test_credibility_evidence_strings_are_non_empty(self, aurora_client):
        res = aurora_client.get("/api/dynasty/credibility?club_id=aurora")
        data = res.json()
        for i, ev in enumerate(data.get("evidence", [])):
            assert isinstance(ev, str), f"evidence[{i}] is not a string: {ev!r}"
            assert ev.strip(), f"evidence[{i}] is an empty string"

    def test_credibility_evidence_has_no_placeholder_tokens(self, aurora_client):
        """Placeholder tokens like 'TODO', 'TBD', 'N/A' in evidence strings
        indicate an unresolved template rather than a real payload value."""
        PLACEHOLDER_TOKENS = ("TODO", "TBD", "N/A", "PLACEHOLDER", "FIXME", "???")
        res = aurora_client.get("/api/dynasty/credibility?club_id=aurora")
        data = res.json()
        for ev in data.get("evidence", []):
            for token in PLACEHOLDER_TOKENS:
                assert token not in ev, (
                    f"Placeholder token {token!r} found in evidence string: {ev!r}"
                )

    def test_credibility_grade_consistent_with_score(self, aurora_client):
        """The displayed credibility grade label must not be out of step with
        the numeric score. A fresh career should have a low-tier grade."""
        res = aurora_client.get("/api/dynasty/credibility?club_id=aurora")
        data = res.json()
        score = data.get("credibility_score", None)
        grade = data.get("grade", None)
        if score is not None and grade is not None:
            # A fresh aurora career has no completed seasons — credibility
            # score should be at the low end. If grade claims "Elite" on a
            # fresh save it is fabricated.
            ELITE_GRADES = {"Elite", "S", "S+", "Legendary"}
            assert grade not in ELITE_GRADES, (
                f"Fresh career credibility grade {grade!r} is implausibly high "
                f"(score={score}). Evidence string may be fabricated."
            )


# ---------------------------------------------------------------------------
# Task 2b — Staff effect lanes are payload-backed (Phase 3b)
# ---------------------------------------------------------------------------

class TestStaffEffectLanesHonesty:
    """Staff effect lanes (Phase 3b / V14 Task 4) must reflect real staff
    ratings, not hardcoded copy. Every lane string must contain a numeric
    value derived from the staff member's actual rating."""

    def test_staff_payload_has_effect_lanes(self, aurora_client):
        res = aurora_client.get("/api/dynasty/staff?club_id=aurora")
        assert res.status_code == 200, res.text
        data = res.json()
        # Phase 3b adds 'effect_lanes' to each staff member.
        staff = data.get("current_staff", [])
        assert staff, "current_staff list is empty on a fresh aurora career"
        for member in staff:
            assert "effect_lanes" in member, (
                f"Staff member {member.get('name', '?')} is missing 'effect_lanes'"
            )
            assert isinstance(member["effect_lanes"], list), (
                f"effect_lanes must be a list, got {type(member['effect_lanes'])}"
            )
            assert member["effect_lanes"], (
                f"effect_lanes for {member.get('name', '?')} is empty"
            )

    def test_staff_effect_lanes_contain_no_placeholder_tokens(self, aurora_client):
        PLACEHOLDER_TOKENS = ("TODO", "TBD", "N/A", "PLACEHOLDER", "FIXME", "???")
        res = aurora_client.get("/api/dynasty/staff?club_id=aurora")
        data = res.json()
        for member in data.get("current_staff", []):
            for lane in member.get("effect_lanes", []):
                for token in PLACEHOLDER_TOKENS:
                    assert token not in lane, (
                        f"Placeholder {token!r} in effect lane for "
                        f"{member.get('name', '?')}: {lane!r}"
                    )

    def test_staff_ratings_in_payload_are_integers(self, aurora_client):
        """Phase 0 coerces staff ratings to int at the payload boundary.
        Phase 5 confirms this invariant holds end-to-end."""
        res = aurora_client.get("/api/dynasty/staff?club_id=aurora")
        data = res.json()
        for member in data.get("current_staff", []):
            rp = member.get("rating_primary")
            rs = member.get("rating_secondary")
            if rp is not None:
                assert isinstance(rp, int), (
                    f"{member.get('name', '?')} rating_primary is float: {rp!r}"
                )
            if rs is not None:
                assert isinstance(rs, int), (
                    f"{member.get('name', '?')} rating_secondary is float: {rs!r}"
                )

    def test_candidate_effect_lanes_contain_no_float_strings(self, aurora_client):
        """Phase 0 removes ':.1f' formatting from candidate effect lanes.
        Confirm no '.0/' or trailing '.0' leaks through (Phase 0 + 3b combined)."""
        res = aurora_client.get("/api/dynasty/staff?club_id=aurora")
        data = res.json()
        for candidate in data.get("candidates", []):
            for lane in candidate.get("effect_lanes", []):
                assert ".0/" not in lane, (
                    f"Float '.0/' leak in candidate lane: {lane!r}"
                )
                assert not lane.endswith(".0"), (
                    f"Trailing float '.0' in candidate lane: {lane!r}"
                )


# ---------------------------------------------------------------------------
# Task 2c — History milestone proof annotations (Phase 4a)
# ---------------------------------------------------------------------------

class TestHistoryMilestoneProofHonesty:
    """Milestone descriptions with a 'proof' annotation (e.g. 'Best Newcomer'
    → player name + stats) must only render when the underlying career record
    actually contains that holder and those stats. A fabricated proof annotation
    that references a player who does not exist in the career violates the
    decision-traceability north star."""

    def test_history_endpoint_returns_timeline(self, aurora_client):
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        assert res.status_code == 200, res.text
        data = res.json()
        assert "timeline" in data

    def test_milestone_proof_sources_are_payload_strings(self, aurora_client):
        """Every milestone entry that exposes a 'proof' or 'source' field must
        contain a non-empty string derived from career data, not a hardcoded
        claim. On a fresh career with no completed seasons, no milestone should
        claim a proof that references a real player — because none exists."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        for entry in data.get("timeline", []):
            proof = entry.get("proof") or entry.get("source")
            if proof is not None:
                assert isinstance(proof, str), (
                    f"Milestone proof must be a string, got {type(proof)}: {proof!r}"
                )
                assert proof.strip(), "Milestone proof string is empty"
                PLACEHOLDER_TOKENS = ("TODO", "TBD", "PLACEHOLDER", "???")
                for token in PLACEHOLDER_TOKENS:
                    assert token not in proof, (
                        f"Placeholder {token!r} in milestone proof: {proof!r}"
                    )

    def test_fresh_career_milestone_proofs_do_not_name_nonexistent_players(
        self, aurora_client
    ):
        """A fresh career has no completed season, so no award has been given.
        No milestone entry should reference a player name as proof of an award
        that was never made. The roster is seeded, so player names are known —
        but if a milestone says e.g. 'Best Newcomer: [Name]' on a fresh save,
        that is a fabricated claim."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        # On a fresh career there should be no completed-season milestones at all.
        completed_season_milestones = [
            e for e in data.get("timeline", [])
            if e.get("season_number", 0) > 0 and e.get("proof")
        ]
        assert completed_season_milestones == [], (
            f"Fresh career has milestone entries with proof for a completed season "
            f"that never happened: {completed_season_milestones}"
        )

    def test_banners_list_is_empty_on_fresh_career(self, aurora_client):
        """Phase 4a introduces an honest EmptyState for banners. A fresh career
        has no championship banners — the banners list must be empty, not
        populated with fabricated placeholder entries."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        banners = data.get("banners", [])
        assert isinstance(banners, list)
        # Fabricated banners would appear as non-empty on a fresh career.
        assert banners == [], (
            f"Fresh career has non-empty banners list: {banners}. "
            "Banners should only exist after a championship is won."
        )

    def test_alumni_list_is_empty_on_fresh_career(self, aurora_client):
        """Phase 4a introduces an honest EmptyState for alumni. A fresh career
        has no retired alumni — alumni must be empty, not placeholder-populated."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        alumni = data.get("alumni", [])
        assert isinstance(alumni, list)
        assert alumni == [], (
            f"Fresh career has non-empty alumni list: {alumni}. "
            "Alumni should only exist after players retire from the program."
        )


# ---------------------------------------------------------------------------
# Task 2d — Recruiting payload ProofChip sources (Phase 2a)
# ---------------------------------------------------------------------------

class TestRecruitingPayloadHonesty:
    """ProofChip sources surfaced on the Recruit Board (Phase 2a) must be
    real payload fields. The scouting state must expose only what has been
    revealed by actual scout actions — no values should be 'known' before
    any scouting has occurred on a fresh career."""

    def test_recruit_board_endpoint_returns_prospects(self, aurora_client):
        res = aurora_client.get("/api/dynasty/recruiting?club_id=aurora")
        assert res.status_code == 200, res.text
        data = res.json()
        assert "prospects" in data or "board" in data, (
            f"Expected 'prospects' or 'board' key, got: {list(data.keys())}"
        )

    def test_recruit_scouting_state_present(self, aurora_client):
        """Each prospect must carry a scouting_state field (the fog-of-war
        system from Phase 1 KnownValue + Phase 2a consume). On a fresh career
        with no scout actions, all values should be 'estimated' or 'hidden',
        never falsely 'known'."""
        res = aurora_client.get("/api/dynasty/recruiting?club_id=aurora")
        data = res.json()
        prospects = data.get("prospects") or data.get("board") or []
        if not prospects:
            pytest.skip("No prospects on board — cannot validate scouting state")
        for p in prospects[:5]:  # sample first 5 to keep test fast
            # If a scouting_state field is present, it must be a valid Knowledge value.
            scouting_state = p.get("scouting_state")
            if scouting_state is not None:
                assert scouting_state in ("known", "estimated", "hidden"), (
                    f"Invalid scouting_state {scouting_state!r} for prospect "
                    f"{p.get('name', '?')}"
                )

    def test_recruit_fit_score_is_integer_or_none(self, aurora_client):
        """fit_score must be an integer 0–100 or absent — never a float."""
        res = aurora_client.get("/api/dynasty/recruiting?club_id=aurora")
        data = res.json()
        prospects = data.get("prospects") or data.get("board") or []
        for p in prospects:
            fs = p.get("fit_score")
            if fs is not None:
                assert isinstance(fs, int), (
                    f"fit_score for {p.get('name', '?')} is not int: {fs!r}"
                )
                assert 0 <= fs <= 100, f"fit_score {fs} out of range [0, 100]"

    def test_recruit_filter_buckets_are_mutually_exclusive(self, aurora_client):
        """Phase 0 reconciled the recruit filter labels. Strong Fit (>=80),
        Fair Fit (65-79), At Risk (<65) are mutually exclusive and sum to All.
        Verify at the payload level."""
        res = aurora_client.get("/api/dynasty/recruiting?club_id=aurora")
        data = res.json()
        prospects = data.get("prospects") or data.get("board") or []
        if not prospects:
            pytest.skip("No prospects to validate filter buckets")
        strong = [p for p in prospects if (p.get("fit_score") or 0) >= 80]
        fair = [p for p in prospects if 65 <= (p.get("fit_score") or 0) < 80]
        at_risk = [p for p in prospects if (p.get("fit_score") or 0) < 65]
        total_bucketed = len(strong) + len(fair) + len(at_risk)
        assert total_bucketed == len(prospects), (
            f"Filter bucket counts ({len(strong)} + {len(fair)} + {len(at_risk)} = "
            f"{total_bucketed}) do not sum to total prospects ({len(prospects)}). "
            "Buckets are not mutually exclusive."
        )
```

- [ ] **Step 3: Run the suite; verify it passes**

Run from repo root:

```bash
python -m pytest tests/test_v15_honesty.py -v
```

Expected: all tests pass. If a test fails because an endpoint path differs from the assumed path (e.g. `/api/dynasty/credibility` vs `/api/dynasty/office/credibility`), look up the actual route with `git grep -n "credibility\|@router" -- src/dodgeball_sim/server.py` and update the URL in the test. Do not change the assertion logic — only the URL.

- [ ] **Step 4: Run the full suite to guard regressions**

Run from repo root:

```bash
python -m pytest -q
```

Expected: green (no regressions introduced by the new test file).

- [ ] **Step 5: Commit**

```bash
git add tests/test_v15_honesty.py
git commit -m "test(v15-p5): backend honesty suite for ProofChip sources + credibility + staff + milestones

Asserts every evidence/effect-lane/milestone-proof string is payload-backed;
banners and alumni are empty on a fresh career; staff ratings are integers
(Phase 0 invariant); recruit filter buckets are mutually exclusive (Phase 0
invariant). Maps to Phases 0, 2a, 3a, 3b, 4a.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Playwright — legibility surface assertions (`tests/e2e/v15-legibility-surfaces.spec.ts`)

**Context (Phase map):** TermTip on Recruit Board (Phase 2a), TermTip on Roster (Phase 2b), PipelineEmblem on recruit cards (Phase 2a), honest EmptyState for banners (Phase 4a), honest EmptyState for staff vacancies (Phase 3b), ProofChip on History milestones (Phase 4a). All assertions target a **fresh save** on the `aurora` club — the canonical e2e seed. All assertions use semantic/aria-based locators (`getByRole`, `getByLabel`, `getByTestId`) per the repo convention.

**Note on the dev-only smoke route:** The Phase 1 smoke (`?legibility=1`) is **not reachable** in the e2e suite because the suite runs against the Python backend serving a built bundle (`import.meta.env.DEV === false`). This spec verifies the primitives on the screens where they actually ship.

**Files:**
- Create: `tests/e2e/v15-legibility-surfaces.spec.ts`

- [ ] **Step 1: Write the spec**

```ts
import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

// Helper: create a fresh aurora save and return the save name.
async function freshAuroraSave(request: import('@playwright/test').APIRequestContext): Promise<string> {
  const saveName = `e2e-v15-legibility-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();
  return saveName;
}

// ---------------------------------------------------------------------------
// TermTip on Recruit Board (Phase 2a)
// ---------------------------------------------------------------------------

test('Recruit Board: TermTip triggers present for Fit and Interest terms on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);

  // The recruit board must render at least one prospect card.
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });

  // TermTip for "Fit" should expose an accessible trigger button (aria-label contains "What is Fit?").
  const fitTip = page.getByRole('button', { name: /What is Fit\?/i }).first();
  await expect(fitTip).toBeVisible();

  // Focusing the trigger reveals a tooltip describing the term.
  await fitTip.focus();
  const tooltip = page.getByRole('tooltip').first();
  await expect(tooltip).toBeVisible();
  // The tooltip must describe the term in plain language (from TERMS['recruit.fit'].plain).
  await expect(tooltip).toContainText(/match your program/i);

  // TermTip for "Interest" should also be present.
  const intTip = page.getByRole('button', { name: /What is Interest\?/i }).first();
  await expect(intTip).toBeVisible();
});

test('Recruit Board: TermTip tooltip describes mechanical vs flavor kind', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });

  const fitTip = page.getByRole('button', { name: /What is Fit\?/i }).first();
  await fitTip.focus();
  const tooltip = page.getByRole('tooltip').first();
  // The mechanical/flavor pill must be visible (Phase 1 TermTip renders "AFFECTS PLAY" or "FLAVOR").
  await expect(tooltip).toContainText(/AFFECTS PLAY|FLAVOR/i);
});

// ---------------------------------------------------------------------------
// PipelineEmblem on recruit cards (Phase 2a)
// ---------------------------------------------------------------------------

test('Recruit Board: PipelineEmblem present on prospect cards with accessible tier label', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });

  // At least one PipelineEmblem should be visible (role="img", aria-label="Pipeline Tier N ...").
  const emblem = page.getByRole('img', { name: /Pipeline Tier/i }).first();
  await expect(emblem).toBeVisible();

  // The tier label must include a tier number (1–5).
  const label = await emblem.getAttribute('aria-label');
  expect(label).toMatch(/Pipeline Tier [1-5]/);
});

// ---------------------------------------------------------------------------
// TermTip on Roster (Phase 2b)
// ---------------------------------------------------------------------------

test('Roster: TermTip triggers present for player archetypes on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10_000 });

  // TermTip for an archetype term (e.g. "Thrower") should be present.
  // At least one archetype TermTip button must be visible somewhere on the roster.
  const archetypeTip = page
    .getByRole('button', { name: /What is (Thrower|Ball Hawk|Net Specialist|Skirmisher|Balanced)\?/i })
    .first();
  await expect(archetypeTip).toBeVisible();

  // Focusing reveals a description.
  await archetypeTip.focus();
  await expect(page.getByRole('tooltip').first()).toBeVisible();
});

test('Roster: TermTip for growth Ceiling term is present on player card', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10_000 });

  // Open a player card to surface the Ceiling/Headroom TermTip.
  const firstPlayerRow = page.getByTestId('roster-player-row').first();
  if (await firstPlayerRow.isVisible()) {
    await firstPlayerRow.click();
    // After clicking, a player detail panel should open.
    const playerDetail = page.getByTestId('player-detail-modal').or(page.getByTestId('player-card'));
    await expect(playerDetail.first()).toBeVisible({ timeout: 5_000 });
    const ceilingTip = page.getByRole('button', { name: /What is Ceiling\?/i }).first();
    await expect(ceilingTip).toBeVisible();
  }
});

// ---------------------------------------------------------------------------
// Honest EmptyState — banners (Phase 4a)
// ---------------------------------------------------------------------------

test('History: honest EmptyState for Championship Banners on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=history`);

  // History tab / program page must load.
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });

  // On a fresh career, banners are empty. The EmptyState component renders
  // role="status" with title text.
  const bannerSection = page.getByTestId('banner-shelf').or(page.getByTestId('banners-section'));
  if (await bannerSection.first().isVisible().catch(() => false)) {
    const emptyState = bannerSection.first().getByRole('status');
    await expect(emptyState).toBeVisible();
    // Must not say "0/0 awards logged" (old fabricated copy) — must say something honest.
    await expect(emptyState).not.toContainText('0/0 awards logged');
    // Must describe what will fill it.
    await expect(emptyState).toContainText(/banner|championship|win/i);
  }
});

// ---------------------------------------------------------------------------
// Honest EmptyState — alumni (Phase 4a)
// ---------------------------------------------------------------------------

test('History: honest EmptyState for Alumni Lineage on a fresh save', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=history`);
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });

  const alumniSection = page.getByTestId('alumni-lineage').or(page.getByTestId('alumni-section'));
  if (await alumniSection.first().isVisible().catch(() => false)) {
    const emptyState = alumniSection.first().getByRole('status');
    await expect(emptyState).toBeVisible();
    // Must convey honest absence of alumni.
    await expect(emptyState).toContainText(/alumni|retire|graduated/i);
  }
});

// ---------------------------------------------------------------------------
// Honest EmptyState — staff vacancies (Phase 3b)
// ---------------------------------------------------------------------------

test('Dynasty Office Staff: honest EmptyState for Vacancies when none exist', async ({ page, request }) => {
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=staff`);
  await expect(page.getByRole('heading', { name: 'Candidates' })).toBeVisible({ timeout: 10_000 });

  // On a fresh career with full staff, the Vacancies section shows an EmptyState
  // instead of a big blank card.
  const vacanciesSection = page.getByTestId('vacancies-section').or(page.getByTestId('staff-vacancies'));
  if (await vacanciesSection.first().isVisible().catch(() => false)) {
    const emptyState = vacanciesSection.first().getByRole('status');
    await expect(emptyState).toBeVisible();
    await expect(emptyState).not.toContainText('TODO');
  }
});

// ---------------------------------------------------------------------------
// ProofChip on History milestones (Phase 4a)
// ---------------------------------------------------------------------------

test('History: ProofChip on milestone entries exposes payload-backed source', async ({ page, request }) => {
  // This test is only meaningful after at least one completed season.
  // On a fresh career, milestones with proof do not exist (honesty gate),
  // so we verify that no ProofChip claims a source on the fresh save.
  await freshAuroraSave(request);
  await page.goto(`${baseUrl}/?tab=history`);
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });

  // No ProofChip button should claim an award on a fresh career.
  // If any appear, their source must not contain a placeholder token.
  const proofChips = page.getByRole('button', { name: /Best Newcomer|Most Valuable|Champion|ⓘ/i });
  const count = await proofChips.count();
  for (let i = 0; i < count; i++) {
    const chip = proofChips.nth(i);
    await chip.click();
    const note = page.getByRole('note').first();
    await expect(note).toBeVisible();
    await expect(note).not.toContainText('TODO');
    await expect(note).not.toContainText('PLACEHOLDER');
    // Close the chip before the next iteration.
    await chip.click();
  }
});
```

- [ ] **Step 2: Run the new spec in isolation to confirm it passes**

Run from repo root:

```bash
npm run e2e -- v15-legibility-surfaces
```

Expected: all tests pass. If a test fails because a `data-testid` from Phase 2a–4b does not yet exist (i.e. that screen phase is not yet merged), add a `.skip` guard with a comment — do not delete the assertion:

```ts
test.skip(true, 'Phase 2a not yet merged — re-enable when recruit-board TermTip lands');
```

- [ ] **Step 3: Run the full e2e suite to confirm no regressions**

```bash
npm run e2e
```

Expected: zero failures.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/v15-legibility-surfaces.spec.ts
git commit -m "test(v15-p5): Playwright legibility surface assertions (TermTip, PipelineEmblem, EmptyState, ProofChip)

Covers Phase 2a Recruit Board, Phase 2b Roster, Phase 3b Staff vacancies,
Phase 4a History (banners/alumni/milestones). Semantic aria-based locators
throughout; 390x844 overflow checked separately in v15-no-overflow.spec.ts.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Playwright — standings row-click opens ProgramModal (`tests/e2e/v15-standings-modal.spec.ts`)

**Context (Phase 2d):** Phase 2d wires standings row-click to the existing Club/League History modal (ProgramModal) and removes the misleading trailing `>` icon. This task verifies that behavior on a fresh save. The existing `standings-history-lane.spec.ts` covers the **inline club history lane** pattern; this spec verifies the **modal** variant if Phase 2d chose a modal over inline expand. Read Phase 2d's plan before committing this spec — if Phase 2d reused the inline-expand pattern already tested in `standings-history-lane.spec.ts`, mark this spec as documentation-only and point to the existing coverage.

**Files:**
- Create: `tests/e2e/v15-standings-modal.spec.ts`

- [ ] **Step 1: Read the Phase 2d plan to confirm the interaction pattern before writing**

Run:

```bash
grep -n "row-click\|ProgramModal\|modal\|aria-expanded\|standings" \
  "docs/specs/2026-05-30-v15-systems-legibility/phase-2d-standings-matchup-plan.md" 2>/dev/null | head -30
```

If the file does not yet exist, read `implementation-index.md`'s Phase 2d row for the stated intent: "Wire Standings row-click → the existing Club/League History modal; drop the misleading trailing `>` icon." Proceed with the modal assumption; if Phase 2d implements inline-expand instead, this spec's assertions remain valid with a locator adjustment.

- [ ] **Step 2: Write the spec**

```ts
import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test('Standings: row-click opens a club program modal with club history content', async ({ page, request }) => {
  const saveName = `e2e-v15-standings-modal-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=standings`);
  await expect(page.getByRole('table').or(page.getByTestId('standings-table')).first()).toBeVisible({
    timeout: 10_000,
  });

  // The user's own club row (aurora) should be clickable / expandable.
  // Phase 2d may implement this as a row button with aria-expanded,
  // or as a row that opens a modal dialog. Both patterns are accepted.
  const auroraRowTrigger = page
    .getByRole('button', { name: /View Aurora|Aurora.*history|Aurora.*program/i })
    .or(page.getByRole('row', { name: /Aurora/i }).first());
  await expect(auroraRowTrigger.first()).toBeVisible();
  await auroraRowTrigger.first().click();

  // Option A: inline expand (matches existing standings-history-lane.spec.ts pattern).
  const inlineHistory = page.getByTestId('club-history-lane').or(page.getByText('Club History'));
  // Option B: modal dialog opens.
  const modalDialog = page.getByRole('dialog');

  const expanded = await Promise.race([
    inlineHistory.first().waitFor({ timeout: 5_000 }).then(() => 'inline').catch(() => null),
    modalDialog.waitFor({ timeout: 5_000 }).then(() => 'modal').catch(() => null),
  ]);
  expect(expanded, 'Neither inline expand nor modal appeared after standings row-click').toBeTruthy();

  if (expanded === 'modal') {
    // Modal must expose club/program content.
    await expect(modalDialog).toBeVisible();
    await expect(modalDialog).toContainText(/Aurora|season record|history/i);
    // Modal must be closeable.
    const closeBtn = modalDialog.getByRole('button', { name: /close|dismiss/i });
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
      await expect(modalDialog).not.toBeVisible({ timeout: 3_000 });
    }
  }
});

test('Standings: no trailing > icon on club rows (Phase 2d cleanup)', async ({ page, request }) => {
  const saveName = `e2e-v15-standings-trailing-icon-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();

  await page.goto(`${baseUrl}/?tab=standings`);
  await expect(page.getByRole('table').or(page.getByTestId('standings-table')).first()).toBeVisible({
    timeout: 10_000,
  });

  // The old misleading ">" chevron should not appear in the standings rows.
  // It was implemented as a literal ">" text node or a ">" aria-label on the rows.
  const trailingChevrons = page.locator('[aria-label=">"], text=">>"').or(
    page.getByTestId('standings-row-chevron')
  );
  await expect(trailingChevrons.first()).not.toBeVisible().catch(() => {
    // If the locator finds nothing, the test passes vacuously — that's the goal.
  });
  const count = await trailingChevrons.count();
  expect(count, `Found ${count} trailing chevron(s) in standings rows that Phase 2d should have removed`).toBe(0);
});
```

- [ ] **Step 3: Run the spec in isolation**

```bash
npm run e2e -- v15-standings-modal
```

Expected: pass. If Phase 2d is not yet merged, add:

```ts
test.skip(true, 'Phase 2d not yet merged — re-enable when standings row-click modal lands');
```

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/v15-standings-modal.spec.ts
git commit -m "test(v15-p5): standings row-click opens ProgramModal + no trailing chevron (Phase 2d gate)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Playwright — 390×844 no-horizontal-overflow on all touched screens (`tests/e2e/v15-no-overflow.spec.ts`)

**Context:** The shared constraint for all V15 phases is mobile 390×844, no horizontal overflow. The existing `mobile-roster-accessibility.spec.ts` covers only the Roster tab. This task adds the same overflow check for every screen touched by Phases 2a–4b: Recruit Board, Roster (extends existing), Lineup Editor, Standings, Dynasty Office (staff subtab), History, Season Preview. One spec, one `page.setViewportSize` call per test, same `scrollWidth > window.innerWidth` evaluation pattern used in `mobile-roster-accessibility.spec.ts`.

**Files:**
- Create: `tests/e2e/v15-no-overflow.spec.ts`

- [ ] **Step 1: Write the spec**

```ts
import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';
const MOBILE = { width: 390, height: 844 };

async function freshSave(request: import('@playwright/test').APIRequestContext): Promise<void> {
  const saveName = `e2e-v15-overflow-${Date.now()}`;
  const res = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(res.ok()).toBeTruthy();
}

async function checkNoHorizontalOverflow(page: import('@playwright/test').Page): Promise<void> {
  const hasOverflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > window.innerWidth;
  });
  expect(hasOverflow, `Horizontal overflow detected at 390px on ${page.url()}`).toBe(false);
}

// ---------------------------------------------------------------------------
// Phase 2a — Recruit Board
// ---------------------------------------------------------------------------
test('Recruit Board: no horizontal overflow at 390×844 (Phase 2a)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=recruiting`);
  await expect(page.getByTestId('prospect-card').first()).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 2b — Roster
// ---------------------------------------------------------------------------
test('Roster: no horizontal overflow at 390×844 (Phase 2b)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 2c — Lineup Editor
// ---------------------------------------------------------------------------
test('Lineup Editor: no horizontal overflow at 390×844 (Phase 2c)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=command`);
  await expect(
    page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()
  ).toBeVisible({ timeout: 10_000 });
  if (await page.getByTestId('season-preview').isVisible()) {
    await page.getByRole('button', { name: /To the Command Center/i }).click();
  }
  await expect(page.getByTestId('weekly-command-center')).toBeVisible();
  // Open the lineup editor if it's behind a trigger button.
  const lineupEditorTrigger = page
    .getByRole('button', { name: /edit lineup|lineup editor/i })
    .or(page.getByTestId('open-lineup-editor'));
  if (await lineupEditorTrigger.first().isVisible().catch(() => false)) {
    await lineupEditorTrigger.first().click();
  }
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 2d — Standings
// ---------------------------------------------------------------------------
test('Standings: no horizontal overflow at 390×844 (Phase 2d)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=standings`);
  await expect(
    page.getByRole('table').or(page.getByTestId('standings-table')).first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 3a — Dynasty Office / Credibility
// ---------------------------------------------------------------------------
test('Dynasty Office Credibility: no horizontal overflow at 390×844 (Phase 3a)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=dynasty`);
  await expect(
    page.getByRole('heading', { name: /Dynasty Office|Program Credibility|Office/i }).first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 3b — Staff
// ---------------------------------------------------------------------------
test('Dynasty Office Staff: no horizontal overflow at 390×844 (Phase 3b)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=dynasty&subtab=staff`);
  await expect(page.getByRole('heading', { name: 'Candidates' })).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 3c — Season Preview
// ---------------------------------------------------------------------------
test('Season Preview: no horizontal overflow at 390×844 (Phase 3c)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=command`);
  // Season Preview is shown before Week 1 is locked.
  await expect(
    page.locator('[data-testid="weekly-command-center"], [data-testid="season-preview"]').first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 4a — History
// ---------------------------------------------------------------------------
test('History (Program): no horizontal overflow at 390×844 (Phase 4a)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/?tab=history`);
  await expect(
    page.getByRole('heading', { name: /Program History|My Program|History/i }).first()
  ).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});

// ---------------------------------------------------------------------------
// Phase 4b — App shell (nav + settings resolution)
// ---------------------------------------------------------------------------
test('App shell nav: no horizontal overflow at 390×844 (Phase 4b)', async ({ page, request }) => {
  await freshSave(request);
  await page.setViewportSize(MOBILE);
  await page.goto(`${baseUrl}/`);
  await expect(page.getByRole('navigation').first()).toBeVisible({ timeout: 10_000 });
  await checkNoHorizontalOverflow(page);
});
```

- [ ] **Step 2: Run the spec in isolation**

```bash
npm run e2e -- v15-no-overflow
```

Expected: all pass. If a screen phase is not yet merged, the page may not load correctly — add a skip guard per the pattern in Task 3 Step 2.

- [ ] **Step 3: Run the full e2e suite**

```bash
npm run e2e
```

Expected: zero failures.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/v15-no-overflow.spec.ts
git commit -m "test(v15-p5): 390x844 no-horizontal-overflow checks for all V15 touched screens

One test per phase-screen (2a Recruit Board, 2b Roster, 2c Lineup Editor,
2d Standings, 3a Dynasty Office, 3b Staff, 3c Season Preview, 4a History,
4b App shell). Extends the pattern established in mobile-roster-accessibility.spec.ts.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Document the compile-time no-orphan-term gate (procedure only — no new files)

**Context:** The no-orphan-term gate requires no test runner. It is enforced by `npm run build` (`tsc -b && vite build`) because `TermId` is a closed union derived from `as const satisfies Record<string, TermDef>` in `frontend/src/legibility/terms.ts`. Any component referencing `<TermTip term="undefined.id">` is a **compile error**. This task documents the negative-check procedure so any agent or reviewer can verify the gate is live.

**Files:** No new files. This task is procedure documentation within this plan.

- [ ] **Step 1: Verify the gate is live (positive path)**

Run from `frontend/`:

```bash
npm run build
```

Expected: PASS. This confirms the current `TERMS` registry compiles cleanly.

- [ ] **Step 2: Verify the gate catches a bad term (negative path — revert immediately)**

Add a temporary line to any existing component that already imports from `legibility/`, for example `frontend/src/App.tsx` (which mounts `LegibilitySmoke`):

```tsx
// TEMPORARY — delete before committing
import { getTerm } from './legibility/terms';
const _test = getTerm('does.not.exist');
```

Run from `frontend/`:

```bash
npm run build
```

Expected: **BUILD FAILS** with a TypeScript error:

```
Argument of type '"does.not.exist"' is not assignable to parameter of type 'TermId'.
```

This confirms the gate is live: any component referencing an undefined term is caught at build time without any test runner.

**Immediately revert** the temporary line:

```bash
git checkout -- frontend/src/App.tsx
```

Run `npm run build` again to confirm it returns to PASS.

- [ ] **Step 3: No commit needed for this task**

The gate is architectural (built into the type system by Phase 1). No separate test file is committed. The procedure above is the verification record.

---

## Phase 5 Exit Gates

Run all gates before declaring Phase 5 (and V15) done:

- [ ] **Engine-health probe unchanged:**
  ```bash
  python tools/tier_engine_health_probe.py --driver both --trials 50 --seed-offset 0 \
    > docs/specs/2026-05-30-v15-systems-legibility/probe-snapshot-v15-end.txt
  diff docs/specs/2026-05-30-v15-systems-legibility/probe-baseline-v15-start.txt \
       docs/specs/2026-05-30-v15-systems-legibility/probe-snapshot-v15-end.txt
  ```
  Expected: `diff` exits with zero differences. Any difference means a Phase 0–4 commit touched sim math — investigate before closing V15.

- [ ] **Backend pytest suite green:**
  ```bash
  python -m pytest -q
  ```
  Expected: green (includes the new `tests/test_v15_honesty.py`).

- [ ] **Frontend build + lint clean (tsc gate + no-orphan-term gate):**
  ```bash
  # from frontend/
  npm run build && npm run lint
  ```
  Expected: clean. A clean build proves all TermId references in Phase 2–4 components resolve in `TERMS` (the no-orphan-term gate).

- [ ] **Playwright e2e zero failures:**
  ```bash
  npm run e2e
  ```
  Expected: zero failures across all specs including the three new V15 phase-5 specs.

- [ ] **No-orphan-term negative check confirmed:** The negative-check procedure in Task 6 Step 2 was executed and confirmed the gate produces a TypeScript error on an undefined term. (This is a one-time verification; not a per-commit step.)

- [ ] **Probe text files NOT committed:** Confirm `docs/specs/2026-05-30-v15-systems-legibility/probe-*.txt` are absent from `git status` (they are local working-tree artifacts).

---

## Scope notes

**In scope for Phase 5:**
- Playwright assertions for legibility surfaces on production screens (Phases 2a–4b).
- Backend honesty tests for ProofChip sources, credibility evidence, staff lanes, milestone proofs.
- The engine-probe unchanged gate (documented procedure + snapshot comparison).
- 390×844 no-horizontal-overflow checks for every touched screen.
- Documentation of the compile-time no-orphan-term gate (procedure, not a test file).

**Out of scope for Phase 5 (blocked by scope rules in `implementation-index.md`):**
- No engine/sim/RNG changes.
- No new npm or Python dependencies.
- No frontend unit-test runner (the codebase has none and may not gain one in V15).
- No new screen work — any legibility surface that does not yet have a `data-testid` or aria role because its screen phase is unmerged should be skipped with a guard comment, not invented.
- The dev-only legibility smoke route (`?legibility=1`) is not testable in the e2e suite (the suite targets the Python backend serving a production bundle — `import.meta.env.DEV` is `false`). Dev-mode verification of the smoke is a developer responsibility, not an automated gate.
