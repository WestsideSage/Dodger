# V15 Phase 3a — Dynasty Office / Credibility: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Dynasty Office's Recruit tab legible — disambiguate Program Credibility from Club Prestige, de-jargon the evidence copy, fix the progress-bar layout, relocate recruiting-budget stats to where they belong, reduce empty space and jargon in Weekly Recruiting, and add tooltips to Program Settings. All work is presentation + light payload-plumbing only; zero engine/sim changes.

**Architecture:** Five focused edits to two frontend files (`CredibilityStrip.tsx`, `DynastyOffice.tsx`) plus one small backend copy reword in `recruiting_office.py` with a matching test update. The legibility toolkit from Phase 1 (`frontend/src/legibility/`) is the only new import family; no other new deps.

**Tech Stack:** React 19 + TypeScript ~6 + Vite 8 (`tsc -b && vite build`), ESLint, root Playwright (`npm run e2e`), pytest.

> **Pre-flight:**
> - Phase 1 (toolkit) must be merged before this branch starts — all imports below are from `frontend/src/legibility/`.
> - Branch off `main` (after Phase 1 merge): `git checkout -b feat/v15-phase3a-dynasty-office`.
> - Verify green baseline: `python -m pytest -q` (backend green) and from `frontend/`, `npm run build && npm run lint` (frontend clean).
> - Read the locked API contract in `implementation-index.md` before touching any import.
> - **Cross-screen note:** `DynastyOffice.tsx` also contains `StaffTab` (Phase 3b target). This plan does **not** touch `StaffTab` or its sub-components. Phase 3b authors must rebase on this branch or coordinate merge order — the files are shared but the touched regions are distinct.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `frontend/src/components/dynasty/CredibilityStrip.tsx` | Credibility disambig, evidence reword, progress-bar layout, relocate budget stats | 1, 2, 3 |
| `frontend/src/components/DynastyOffice.tsx` | Receive relocated budget stats, de-jargon SlotMeter, add Settings tooltips, fix RecruitBoard empty state | 3, 4, 5 |
| `src/dodgeball_sim/recruiting_office.py` | Reword evidence strings for plain language (backend copy) | 2 |
| `tests/test_recruiting_office.py` (or existing recruiting test) | Update evidence string assertions to match reworded copy | 2 |

---

## Task 1: Disambiguate Program Credibility vs Club Prestige + fix grade-label drift + progress-bar layout

**Context:** `CredibilityStrip.tsx` currently shows "Program Credibility" and "Club prestige score 0" (from the third evidence item) with no explanation that these are two separate systems — readers interpret them as contradictory. The progress-bar tick marks (D/C/B/A at fixed 0/33/66/100%) are aesthetic positions that do not align with the real `_grade()` breakpoints in `recruiting_office.py` (F=0–39, D=40–54, C=55–69, B=70–84, A=85+); a score of 50 (backend grade D) renders its marker between the "C" and "B" ticks — contradicting the large letter. The drift risk is that the tick labels are hard-coded independently of the backend's `_grade` function; this task replaces them with positions derived directly from the same thresholds. This task corrects all three issues.

**Decisions (locked):**
- The credibility tier display always reads from `credibility.grade` (the payload field already computed by `_grade(score)` in `recruiting_office.py`) — no independent re-derivation in the component.
- Tick positions align to the actual `_grade()` breakpoints in `recruiting_office.py`: F starts at 0, D at 40, C at 55, B at 70, A at 85. Because the scale is 0–100, tick percentages are: F=0%, D=40%, C=55%, B=70%, A=85%. The track ends at 100 (the score cap), so the final tick sits at 85% — no clipping at the right edge. The old layout used D/C/B/A at 0/33/66/100%, which was incorrect (score 50 = backend grade D, but the marker landed between C and B ticks).
- `TermTip` wraps both "Program Credibility" (term `program.credibility`) and "Club Prestige" (term `program.prestige`) wherever those labels appear in the strip, so a first-time player can tap either term and read the disambiguation.
- The side-column budget stats (Board Size / Reach Remaining / Visit Window) are **removed from `CredibilityStrip`** in Task 3; this task removes only their rendering, and the props they need (`budget`, `prospectCount`, `week`) follow in Task 3.

**Files:**
- Modify: `frontend/src/components/dynasty/CredibilityStrip.tsx`

- [ ] **Step 1: Read the current file top-to-bottom to confirm line ranges before editing**

  Run: `git grep -n "do-cred\|grade\|prestige\|Tier\|progress\|tick" -- frontend/src/components/dynasty/CredibilityStrip.tsx`

  Expected: confirms lines 22-28 (tier derivation), line 39 (`do-cred-letter`), lines 59-61 (tick marks), and lines 75-93 (`do-cred-side`). If line numbers differ, adjust steps below accordingly.

- [ ] **Step 2: Rewrite `CredibilityStrip.tsx` with disambiguated headers, grade-safe label, correct tick layout, and TermTip wrappers**

  Replace the entire file content with:

  ```tsx
  import { TermTip } from '../../legibility';
  import type { DynastyOfficeResponse } from '../../types';

  type RecruitingCredibility = DynastyOfficeResponse['recruiting']['credibility'];

  // Tick positions aligned to the real _grade() breakpoints in recruiting_office.py:
  // F=0–39, D=40–54, C=55–69, B=70–84, A=85+.
  // Each tick marks where a NEW grade begins. Track width = 100pts so % = breakpoint value.
  const TIER_TICKS: Array<{ label: string; pct: number }> = [
    { label: 'F', pct: 0 },
    { label: 'D', pct: 40 },
    { label: 'C', pct: 55 },
    { label: 'B', pct: 70 },
    { label: 'A', pct: 85 },
  ];

  // Which tier bracket does the score currently sit in?
  // Grade breakpoints (recruiting_office.py _grade): F=0-39, D=40-54, C=55-69, B=70-84, A=85+.
  function tierBracket(score: number): { label: string; prev: number; next: number } {
    if (score >= 85) return { label: 'Tier A · Max reach', prev: 85, next: 100 };
    if (score >= 70) return { label: 'Tier B · Toward A', prev: 70, next: 85 };
    if (score >= 55) return { label: 'Tier C · Toward B', prev: 55, next: 70 };
    if (score >= 40) return { label: 'Tier D · Toward C', prev: 40, next: 55 };
    return { label: 'Tier F · Toward D', prev: 0, next: 40 };
  }

  export function CredibilityStrip({
    credibility,
  }: {
    credibility: RecruitingCredibility;
  }) {
    const score = credibility.score;
    // Grade always read from the payload — no independent re-derivation that could drift.
    const grade = credibility.grade;
    const bracket = tierBracket(score);
    // Fill % is the score's position within the 0-100 track (one-to-one).
    const fillPct = Math.min(100, Math.max(0, score));

    return (
      <div className="do-cred">
        <div className="do-cred-letter" aria-hidden="true">
          <span className="tier">{grade}</span>
          <div className="halo" />
        </div>

        <div className="do-cred-main">
          <span className="dm-kicker">
            <TermTip term="program.credibility">Program Credibility</TermTip>
          </span>
          <h2 className="do-cred-title">
            Tier {grade} · Regional
          </h2>
          <p className="do-cred-blurb">
            Your recruiting reputation. Higher credibility draws better prospects
            and makes closes easier. It rises with wins, youth development, and
            your club's long-term{' '}
            <TermTip term="program.prestige">prestige</TermTip>.
          </p>

          <div className="do-cred-progress" role="group" aria-label={`Program credibility score ${score} of 100`}>
            <div className="do-cred-progress-head">
              <span className="lbl">{bracket.label}</span>
              <span className="val mono">
                <b>{score}</b> <span className="dim">/ 100</span>
              </span>
            </div>
            <div className="do-cred-track" style={{ position: 'relative' }}>
              <div className="do-cred-fill" style={{ width: `${fillPct}%` }}>
                <span className="do-cred-marker" />
              </div>
              {TIER_TICKS.map(({ label, pct }) => (
                <span
                  key={label}
                  className="do-cred-tick"
                  style={{ left: `${pct}%` }}
                  aria-label={`Tier ${label} threshold`}
                >
                  <span className="lbl">{label}</span>
                </span>
              ))}
            </div>
          </div>

          <div className="do-cred-evidence" aria-label="Credibility factors">
            {credibility.evidence.map((item, index) => (
              <div key={`${index}-${item}`} className="item">
                <span className="ix" aria-hidden="true">{String(index + 1).padStart(2, '0')}.{' '}</span>
                <span className="copy">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }
  ```

  **Key changes from the original:**
  - Props narrowed: `budget`, `prospectCount`, and `week` are removed (moved to caller in Task 3); only `credibility` remains.
  - `grade` reads `credibility.grade` (payload) — the backend `_grade()` function is the single authority; no independent frontend re-derivation can drift.
  - Tick labels now match the real `_grade` breakpoints from `recruiting_office.py`: F(0), D(40), C(55), B(70), A(85). The old 0/33/66/100 aesthetic layout was off by one grade — a score of 50 (grade D) would have appeared between "C" and "B" ticks, contradicting its own letter.
  - Fill `%` equals `score` directly (0–100 scale is 1:1) — no clipping past 85%.
  - `TermTip` wraps "Program Credibility" and "prestige" in the blurb.
  - The `do-cred-side` column is gone (budget stats move in Task 3).

- [ ] **Step 3: Update the `CredibilityStrip` call site in `DynastyOffice.tsx` to drop the removed props**

  In `DynastyOffice.tsx`, find the `<CredibilityStrip ...>` invocation (currently around line 466-470):

  ```tsx
  <CredibilityStrip
    credibility={data.recruiting.credibility}
    budget={data.recruiting.budget}
    prospectCount={sortedProspects.length}
    week={data.week}
  />
  ```

  Replace with:

  ```tsx
  <CredibilityStrip
    credibility={data.recruiting.credibility}
  />
  ```

  (The budget, prospectCount, and week values will be used in Task 3 by the new `RecruitingContext` strip.)

- [ ] **Step 4: Compile + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS. TypeScript will confirm the prop removal is consistent across the call site and the component signature. If tsc reports `program.credibility` or `program.prestige` as unknown TermIds, confirm Phase 1 pre-seeded both keys in `terms.ts` (they are in the Phase 1 plan Task 2 seed).

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/dynasty/CredibilityStrip.tsx frontend/src/components/DynastyOffice.tsx
  git commit -m "feat(v15-p3a): credibility strip — disambiguate prestige, fix grade drift, align ticks

  Grade now reads credibility.grade (payload) not an independent ternary so
  it cannot drift out of step with its own score. Tick positions match the
  real D/C/B/A score breakpoints (0/40/55/70/85) eliminating right-edge
  clipping. TermTip wraps 'Program Credibility' and 'prestige' for
  in-context disambiguation of the two separate systems. Budget stats removed
  from strip (relocated in next task).

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 2: De-jargon the credibility evidence copy (backend + test)

**Context:** The three evidence strings in `recruiting_office.py:110-114` are already honest (each is backed by a real computed field: `wins`, `losses`, `youth_weeks`, `prestige`). The problem is jargon: "command-history wins", "youth-development command weeks", and "Club prestige score N" — a first-time player does not know what a "command week" is. This task rewords the strings to plain English without changing the underlying data or computation. Because `prestige` already appears in evidence item 3, the naming-collision disambiguation (TermTip on the frontend) is reinforced by the plain-English copy here.

**Backend copy rules (honesty contract):**
- Each reworded string must still be derived from exactly the same field it was before.
- No new fields, no fabrication.
- "No command history yet" edge case copy is also updated to match the new plain style.

**Files:**
- Modify: `src/dodgeball_sim/recruiting_office.py` (lines 110-116, the `evidence` list)
- Modify: `tests/test_recruiting_office.py` (or whichever test module asserts evidence strings — confirm with `git grep -rn "command-history\|command weeks\|prestige score" -- tests/`)

- [ ] **Step 1: Locate and read the current evidence list and matching tests**

  Run: `git grep -n "career command-history\|youth-development command\|Club prestige score\|No command history" -- src/dodgeball_sim/recruiting_office.py tests/`
  Expected: shows the four strings in `recruiting_office.py:110-116` and any test assertions in `tests/`.

- [ ] **Step 2: Reword the evidence strings in `recruiting_office.py`**

  In `src/dodgeball_sim/recruiting_office.py`, replace lines 110-116 (the `evidence` list and the `if not history` append):

  **Before:**
  ```python
      evidence = [
          f"{wins} career command-history wins and {losses} losses.",
          f"{youth_weeks} youth-development command weeks across your career.",
          f"Club prestige score {prestige}.",
      ]
      if not history:
          evidence.append("No command history yet, so credibility starts from program baseline.")
  ```

  **After:**
  ```python
      evidence = [
          f"{wins} wins and {losses} losses across your career.",
          f"{youth_weeks} week{'' if youth_weeks == 1 else 's'} spent prioritizing youth development.",
          f"Club prestige: {prestige} (a long-term score earned from titles and facilities).",
      ]
      if not history:
          evidence.append("No match history yet — credibility starts from the program baseline.")
  ```

  **Rationale per string:**
  1. "career command-history wins" → "wins across your career" — removes the jargon noun "command-history"; same data (`wins`/`losses`).
  2. "youth-development command weeks" → "weeks spent prioritizing youth development" — same data (`youth_weeks`); "command week" is internal vocabulary.
  3. "Club prestige score N" → "Club prestige: N (a long-term score…)" — same data (`prestige`); the parenthetical distinguishes it from credibility in the evidence list itself, reinforcing the TermTip on the frontend.
  4. Edge case: cleaner phrasing, same meaning.

- [ ] **Step 3: Update test assertions to match the new copy**

  Find the test file asserting evidence strings:

  Run: `git grep -rn "career command-history\|command weeks\|prestige score\|command history yet" -- tests/`

  For each assertion found, replace the old string with the new one from Step 2. For example, if a test does:
  ```python
  assert "career command-history wins" in cred["evidence"][0]
  ```
  Replace with:
  ```python
  assert "wins and" in cred["evidence"][0]
  assert "across your career" in cred["evidence"][0]
  ```
  (Use substring assertions that cover the meaningful changed parts; do not assert the entire formatted string verbatim to avoid fragility from variable interpolation.)

  If no existing test asserts the evidence copy, **add a minimal test** to `tests/test_recruiting_office.py` (create the file if absent).

  > **Before writing the test body:** confirm the exact keyword argument name for match history by running:
  > `git grep -n "def build_recruiting_state" -- src/dodgeball_sim/recruiting_office.py`
  > Expected: `def build_recruiting_state(conn, *, season_id, player_club_id, root_seed, history)` — `history` is a required keyword arg. The test below uses this exact signature.

  ```python
  from dodgeball_sim.recruiting_office import build_recruiting_state


  def _minimal_conn(tmp_path):
      from dodgeball_sim import persistence
      db = tmp_path / "cred.db"
      conn = persistence.connect(str(db))
      return conn


  def test_credibility_evidence_plain_language(tmp_path):
      """Evidence strings use plain language — no internal jargon like 'command week'."""
      conn = _minimal_conn(tmp_path)
      # Pass an empty history so the no-history edge case is also exercised.
      state = build_recruiting_state(
          conn,
          season_id="season_1",
          player_club_id="club_user",
          root_seed=42,
          history=[],
      )
      evidence = state["credibility"]["evidence"]
      # At least one item describes wins/losses in plain terms.
      assert any("wins" in e and "losses" in e for e in evidence)
      # No item leaks the internal "command" jargon.
      assert not any("command" in e.lower() for e in evidence)
      # Prestige item is present and uses the plain label.
      assert any("prestige" in e.lower() for e in evidence)
  ```

- [ ] **Step 4: Run the test suite**

  Run: `python -m pytest -q`
  Expected: green. If a pre-existing test fails because it asserted old copy, fix that assertion (it was testing jargon, not logic). Do not change any non-evidence assertion.

- [ ] **Step 5: Commit**

  ```bash
  git add src/dodgeball_sim/recruiting_office.py tests/test_recruiting_office.py
  git commit -m "fix(v15-p3a): credibility evidence copy — plain language, no command-week jargon

  Reword the three evidence strings to plain English without changing any
  underlying field: wins/losses, youth-priority weeks, club prestige. The
  parenthetical on prestige reinforces the frontend TermTip disambiguation.
  Update/add test to assert plain language and no 'command' jargon leak.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 3: Relocate Board Size / Reach Remaining / Visit Window into the Recruit tab

**Context:** These three metrics (prospect count, scout+contact slots remaining, visit slots remaining) are currently in `CredibilityStrip`'s `do-cred-side` column — conceptually they are recruiting-action summaries, not properties of credibility. After Task 1 removes them from `CredibilityStrip`, they need a new home that makes their purpose obvious: a compact `RecruitingContext` strip, inserted between `CredibilityStrip` and the `do-grid-row` row (which contains `SlotMeter` and `StaffBrief`) in the Recruit tab body in `DynastyOffice.tsx`.

**Decision:** Keep the three stats visible (they are genuinely useful week-to-week decision data), but place them inside the recruiting area so they read as "this week's recruiting situation" rather than as credibility attributes.

**Files:**
- Modify: `frontend/src/components/DynastyOffice.tsx`

- [ ] **Step 1: Add a `RecruitingContext` component inside `DynastyOffice.tsx`**

  Add the following component function to `DynastyOffice.tsx`, above the `RecruitBoard` function definition:

  ```tsx
  function RecruitingContext({
    budget,
    prospectCount,
    week,
  }: {
    budget: DynastyOfficeResponse['recruiting']['budget'];
    prospectCount: number;
    week: number;
  }) {
    const scoutRemaining = Math.max(0, budget.scout[1] - budget.scout[0]);
    const contactRemaining = Math.max(0, budget.contact[1] - budget.contact[0]);
    const visitRemaining = Math.max(0, budget.visit[1] - budget.visit[0]);

    return (
      <div
        className="do-recruit-context"
        role="group"
        aria-label="This week's recruiting summary"
        style={{
          display: 'flex',
          gap: '0.75rem',
          flexWrap: 'wrap',
          padding: '0.6rem 0.9rem',
          background: 'rgba(15,23,42,0.55)',
          border: '1px solid #1e293b',
          borderRadius: '6px',
          marginBottom: '0.75rem',
        }}
      >
        <div className="do-cred-rank" style={{ flex: '1 1 8rem', minWidth: '8rem' }}>
          <span className="lbl">Board</span>
          <div className="val"><b>{prospectCount}</b> <span>prospects</span></div>
          <span className="trend dim">Week {String(week).padStart(2, '0')} board</span>
        </div>
        <div className="do-cred-rank" style={{ flex: '1 1 9rem', minWidth: '9rem' }}>
          <span className="lbl">Reach Remaining</span>
          <div className="val"><b>{scoutRemaining + contactRemaining}</b> <span>scout + contact</span></div>
          <span className="trend dim">{scoutRemaining} scout · {contactRemaining} contact</span>
        </div>
        <div className={`do-cred-rank ${visitRemaining === 0 ? 'danger' : ''}`} style={{ flex: '1 1 8rem', minWidth: '8rem' }}>
          <span className="lbl">Visit Slots</span>
          <div className="val"><b>{visitRemaining}</b> <span>remaining</span></div>
          <span className={`trend ${visitRemaining > 0 ? 'dim' : 'warn'}`}>
            {visitRemaining > 0 ? 'Use on best-fit closes' : 'Budget exhausted this week'}
          </span>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 2: Insert `<RecruitingContext>` into the Recruit tab body**

  In `DynastyOffice.tsx`, in the `{activeSubTab === 'recruit' && ...}` block, the current layout is:

  ```tsx
  <CredibilityStrip
    credibility={data.recruiting.credibility}
  />
  <div className="do-grid-row">
    <SlotMeter slots={data.recruiting.budget} />
    <StaffBrief staff={data.staff_market.current_staff} />
  </div>
  <RecruitBoard budget={data.recruiting.budget} prospects={sortedProspects} reload={reload} />
  ```

  (After Task 1 already reduced the `CredibilityStrip` call.) Insert `RecruitingContext` between `CredibilityStrip` and the grid row:

  ```tsx
  <CredibilityStrip
    credibility={data.recruiting.credibility}
  />
  <RecruitingContext
    budget={data.recruiting.budget}
    prospectCount={sortedProspects.length}
    week={data.week}
  />
  <div className="do-grid-row">
    <SlotMeter slots={data.recruiting.budget} />
    <StaffBrief staff={data.staff_market.current_staff} />
  </div>
  <RecruitBoard budget={data.recruiting.budget} prospects={sortedProspects} reload={reload} />
  ```

- [ ] **Step 3: Compile + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS. Confirm no TypeScript error on the `budget` array indexing (the `remaining()` helper from `CredibilityStrip.tsx` is no longer imported; the inline math in `RecruitingContext` replaces it).

- [ ] **Step 4: Verify at 390×844 mobile width**

  The `flexWrap: 'wrap'` on `do-recruit-context` means the three stat cells reflow to two rows on narrow screens rather than overflowing. Confirm no horizontal scroll at 390px. (Use the preview tool or Playwright viewport.)

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/DynastyOffice.tsx
  git commit -m "feat(v15-p3a): relocate Board Size/Reach/Visit into RecruitingContext strip

  These recruiting-action summaries belonged under the Recruit board, not
  inside the Credibility card. New RecruitingContext strip sits between
  CredibilityStrip and the slot meter row; flexWrap keeps it mobile-safe.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 4: De-jargon Weekly Recruiting (SlotMeter) and fix RecruitBoard empty state

**Context:** `SlotMeter` in `DynastyOffice.tsx` (the "Action Slots" panel) is already clear for the three slot types, but the panel kicker ("Weekly Recruiting") and the empty-state inside `RecruitBoard` (a raw `<div>` with inline style) can be improved. The slot help text is already plain; the primary fix here is replacing the `RecruitBoard` inline empty-state with the toolkit `EmptyState` component for visual consistency and honest copy. Note: the planning report item "reduce Weekly Recruiting empty space" refers to the vertical dead space when all slots are used — that layout tightening (e.g. collapsing used-slot rows or reducing padding) is a CSS-only change not planned here; the description text and empty-state are the legibility deliverables for this task. The coordinator may choose to add a CSS tweak in the same commit or defer it.

**Files:**
- Modify: `frontend/src/components/DynastyOffice.tsx`

- [ ] **Step 1: Import `EmptyState` from the legibility toolkit**

  At the top of `DynastyOffice.tsx`, add the import alongside any existing legibility imports:

  ```tsx
  import { EmptyState } from '../legibility';
  ```

  (If Task 1 or 3 already added a legibility import, extend the existing import statement.)

- [ ] **Step 2: Replace the `RecruitBoard` inline empty-state with `EmptyState`**

  In the `RecruitBoard` function, find the current filtered-empty fallback:

  ```tsx
  {filtered.length === 0 && (
    <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
      No prospects match the current filter.
    </div>
  )}
  ```

  Replace with:

  ```tsx
  {filtered.length === 0 && (
    <EmptyState
      title="No prospects match this filter"
      body={
        filter === 'all'
          ? 'The recruit board is empty this week. It refreshes each week as the season progresses.'
          : `Switch to "All" to see every prospect, or try a different filter.`
      }
    />
  )}
  ```

- [ ] **Step 3: Add a plain-language subheading to `SlotMeter` explaining what slots are**

  In the `SlotMeter` function, the current header is:

  ```tsx
  <div className="do-panel-head">
    <span className="dm-kicker">Weekly Recruiting</span>
    <h3>Action Slots</h3>
  </div>
  ```

  Replace with:

  ```tsx
  <div className="do-panel-head">
    <span className="dm-kicker">Weekly Recruiting</span>
    <h3>Action Slots</h3>
    <p style={{ margin: '0.2rem 0 0', color: '#94a3b8', fontSize: '0.72rem', lineHeight: 1.4 }}>
      Each slot is one action you can take this week. Remaining slots reset next week.
    </p>
  </div>
  ```

- [ ] **Step 4: Compile + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS. Verify `EmptyState` is recognized as a valid import (Phase 1 export).

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/DynastyOffice.tsx
  git commit -m "feat(v15-p3a): RecruitBoard EmptyState + SlotMeter plain subheading

  Replace the inline empty div in RecruitBoard with the toolkit EmptyState
  (filter-aware copy). Add a one-line explanation to SlotMeter so 'Action
  Slots' is immediately self-describing.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 5: Add TermTip tooltips and role descriptions to Program Settings modal

**Context:** `SettingsModal` in `DynastyOffice.tsx` presents six department-order selects with no explanation of what each department does or whether its setting is mechanical (affects match outcomes) or flavor. This task adds a `TermTip`-wrapped label for each department so a new player can hover/tap to understand the effect before choosing, plus a brief descriptor line beneath each select explaining the practical impact of the active option.

**Scope — LEGIBILITY ONLY.** This task does not change what the settings do, how they are persisted, or what options are available. It only adds explanatory text.

**Decision:** Department descriptions are hard-coded in this plan (they describe existing engine behavior). If a department's engine behavior changes in a future sprint, the description string here is the update target. Using `TermTip` for department names requires adding six term entries to `terms.ts` (append-only, per the locked contract).

**Files:**
- Modify: `frontend/src/legibility/terms.ts` (append six department terms)
- Modify: `frontend/src/components/DynastyOffice.tsx` (`SettingsModal`)

- [ ] **Step 1: Append department-order terms to `frontend/src/legibility/terms.ts`**

  In `terms.ts`, append the following entries to the `TERMS` object (before the closing `} as const satisfies ...`). These are append-only; do not modify existing keys.

  ```ts
  // --- Department orders (mechanical: each drives a weekly staff focus) ---
  'dept.tactics': {
    label: 'Tactics',
    plain: 'Your staff\'s game-planning focus this week — opponent prep, containment, or tempo.',
    why: 'Tactical orders bias how your team approaches the next match. Mechanical.',
    kind: 'mechanical',
  },
  'dept.training': {
    label: 'Training',
    plain: 'What your training staff emphasizes in practice — fundamentals, throws, or catches.',
    why: 'Training focus shapes which attributes your players develop toward. Mechanical.',
    kind: 'mechanical',
  },
  'dept.conditioning': {
    label: 'Conditioning',
    plain: 'How hard you push the squad physically — recovery emphasis vs. stamina push.',
    why: 'Conditioning order trades short-term edge for long-term freshness. Mechanical.',
    kind: 'mechanical',
  },
  'dept.medical': {
    label: 'Medical',
    plain: 'How aggressively your medical staff manages player minutes and injury risk.',
    why: 'Affects whether injured or tired players are rested or pushed. Mechanical.',
    kind: 'mechanical',
  },
  'dept.scouting': {
    label: 'Scouting',
    plain: 'What your scouts focus on — next opponent, the prospect board, or playoff rivals.',
    why: 'Scouting focus narrows which information you get each week. Mechanical.',
    kind: 'mechanical',
  },
  'dept.culture': {
    label: 'Culture',
    plain: 'The locker-room emphasis this week — youth confidence, veteran leadership, accountability.',
    why: 'Culture orders influence morale and long-term player identity. Mechanical.',
    kind: 'mechanical',
  },
  ```

- [ ] **Step 2: Verify compile gate catches any typos in the new term keys**

  Run (from `frontend/`): `npm run build`
  Expected: PASS. (`as const satisfies` will catch any malformed entry.)

- [ ] **Step 3: Add `TermTip`-wrapped labels and option descriptions to `SettingsModal`**

  In `DynastyOffice.tsx`, add the following import alongside existing legibility imports:

  ```tsx
  import { TermTip } from '../legibility';
  ```

  (Extend the import from Task 4 if already present.)

  Add a description map inside `SettingsModal` (above the `return`), mapping each department key to a plain description of the active order's effect:

  ```tsx
  const DEPARTMENT_DESCRIPTIONS: Record<string, Record<string, string>> = {
    tactics: {
      'opponent prep': 'Study this week\'s opponent. Gives your team a read on their tendencies.',
      'star containment': 'Focus defensive attention on the opponent\'s best player.',
      'possession control': 'Emphasize ball discipline — fewer rushed throws.',
      'pressure tempo': 'Push an aggressive pace to force opponent mistakes.',
    },
    training: {
      fundamentals: 'Balanced development across all skill areas.',
      'throw accuracy': 'Extra reps on throw precision this week.',
      'catch security': 'Focus on reducing missed-catch errors.',
      'scrimmage reps': 'Live game reps — development from match simulation.',
    },
    conditioning: {
      'balanced maintenance': 'Keep everyone fresh without pushing hard.',
      'recovery emphasis': 'Prioritize rest — good after a tough stretch.',
      'stamina push': 'Push physical limits. Short-term edge, long-term cost.',
      'fresh legs': 'Rotate minutes to keep everyone game-ready.',
    },
    medical: {
      'injury prevention': 'Cautious with everyone — reduces injury chance.',
      'minutes restriction': 'Actively limit at-risk players\' exposure.',
      'recovery monitoring': 'Watch and react to player health signals.',
      'play through': 'Play healthy players at full minutes. Higher risk.',
    },
    scouting: {
      'next opponent': 'Scouts focus on this week\'s matchup.',
      'prospect board': 'Scouting time goes to the recruit pool.',
      'playoff threats': 'Watch teams fighting for postseason position.',
      'rival tendencies': 'Build a detailed read on a key rival.',
    },
    culture: {
      'pressure management': 'Help the team handle high-stakes moments.',
      'youth confidence': 'Extra attention on younger players\' development confidence.',
      'veteran leadership': 'Lean on experienced players to set the tone.',
      accountability: 'Hold everyone to standards — sets a focused culture.',
    },
  };

  const DEPT_TERM_IDS: Record<string, import('../legibility').TermId> = {
    tactics: 'dept.tactics',
    training: 'dept.training',
    conditioning: 'dept.conditioning',
    medical: 'dept.medical',
    scouting: 'dept.scouting',
    culture: 'dept.culture',
  };
  ```

  Then in the `departmentEntries.map(...)` return, replace the `<label>` render with:

  ```tsx
  return (
    <label key={key} style={{ display: 'block' }}>
      <span className="dm-kicker">
        {DEPT_TERM_IDS[key] ? (
          <TermTip term={DEPT_TERM_IDS[key]}>{DEPARTMENT_LABELS[key] ?? key}</TermTip>
        ) : (
          DEPARTMENT_LABELS[key] ?? key
        )}
      </span>
      <select
        value={String(value)}
        onChange={(event) => onUpdate(key, event.target.value)}
        style={{ width: '100%', boxSizing: 'border-box', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', padding: '0.55rem 0.65rem', color: '#e2e8f0', marginTop: '0.3rem', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em' }}
      >
        {options.map((option) => (
          <option key={`${key}-${option}`} value={option}>{option.replaceAll('_', ' ')}</option>
        ))}
      </select>
      {DEPARTMENT_DESCRIPTIONS[key]?.[String(value)] && (
        <p style={{ margin: '0.3rem 0 0', color: '#64748b', fontSize: '0.68rem', lineHeight: 1.4 }}>
          {DEPARTMENT_DESCRIPTIONS[key][String(value)]}
        </p>
      )}
    </label>
  );
  ```

  This adds:
  1. A `TermTip`-wrapped department label (hover/tap for the plain + why + mechanical pill).
  2. A one-line description beneath each select showing what the *currently selected* option does, drawn from `DEPARTMENT_DESCRIPTIONS`. If the active option is not in the map (future options), the description line simply does not render (safe fallback).

- [ ] **Step 4: Compile + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS. Confirm `dept.tactics` etc. resolve as valid `TermId` values (they were just added in Step 1). If tsc reports `TermId` mismatch, verify the keys in `terms.ts` exactly match `DEPT_TERM_IDS`.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/legibility/terms.ts frontend/src/components/DynastyOffice.tsx
  git commit -m "feat(v15-p3a): Program Settings — TermTip labels + active-option descriptions

  Wrap each department label in TermTip so hover/tap reveals what the
  department does and that it's mechanical. Add a one-line description
  beneath each select showing what the currently-chosen order does. Six new
  term entries appended to terms.ts (append-only, locked contract).

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Phase 3a Exit Gates

Run all before declaring Phase 3a done:

- [ ] `python -m pytest -q` — green (includes the credibility evidence plain-language test from Task 2).
- [ ] From `frontend/`: `npm run build` — clean (tsc gate catches any orphan TermId or prop mismatch).
- [ ] From `frontend/`: `npm run lint` — clean.
- [ ] From repo root: `npm run e2e` — zero Playwright failures. (The dynasty office e2e spec, if one exists, should still pass; if a spec asserts the old `Visit-Ready` filter or old evidence strings, update those assertions — they were testing jargon, not logic.)
- [ ] `python tools/tier_engine_health_probe.py --driver official --trials 50` — summary **identical** to the Phase 0 Task 1 Step 4 baseline (zero sim drift; this entire phase is presentation-only).
- [ ] Manual check at 390×844 on a live Recruit tab: credibility grade letter matches the Tier label in the heading; evidence strings are plain language; budget stats appear in the new `RecruitingContext` strip above the slot meter row; `TermTip` triggers on "Program Credibility" and "prestige"; no horizontal overflow.
- [ ] Manual check in Program Settings modal: each department label has a dotted underline (TermTip trigger); hovering/tapping shows the plain + why + mechanical pill; the active order has a description line beneath the select.
- [ ] No `playtest_output/*.png` or local `*.db` files committed.
- [ ] No engine/sim/RNG files touched (`git diff HEAD -- src/dodgeball_sim/` shows only `recruiting_office.py`).

---

## Cross-screen overlap notes (for the coordinator)

**Phase 3b (Staff impact) shares `DynastyOffice.tsx`.** Phase 3a touches only these regions:
- `CredibilityStrip.tsx` (fully owned by 3a).
- `SettingsModal` function in `DynastyOffice.tsx`.
- `RecruitBoard` function in `DynastyOffice.tsx` (empty state).
- New `RecruitingContext` function in `DynastyOffice.tsx`.
- `SlotMeter` function in `DynastyOffice.tsx` (subheading only).
- The `{activeSubTab === 'recruit' && ...}` JSX block in `DynastyOffice`.

Phase 3b touches: `StaffTab`, `StaffBrief`, `buildVacancies`, the `{activeSubTab === 'staff' && ...}` block — none of which 3a modifies.

**Recommended merge order:** 3a merges first (smaller, fewer regions). 3b authors rebase on 3a's result to pick up the new import line(s) and avoid a messy conflict on the import block. Alternatively, pre-coordinate the `import { TermTip, EmptyState } from '../legibility'` line so both branches start from an identical import.

**`terms.ts` is the one truly shared file.** Phase 3a appends six `dept.*` keys. If Phase 3b also needs new term keys, they append after the 3a entries. Conflict is trivially resolved (append-only rule from `implementation-index.md §Parallelization rules`).
