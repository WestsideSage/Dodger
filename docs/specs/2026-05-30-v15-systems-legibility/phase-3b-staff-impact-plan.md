# V15 Phase 3b — Staff Impact: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each staff role's program impact legible using the Phase 1 toolkit. Surface concrete evidence of what the training head actually does (a real mechanical hook), present all other departments honestly as advisory/recommendation surfaces (they have no hidden stat effects), replace the vacancies empty-space with a proper `EmptyState`, and clarify the Pipeline Candidates hire flow. Finishes V14 Task 4.

**Architecture:** Presentation-only changes to `DynastyOffice.tsx` (the `StaffBrief` brief-card at ~line 182 and the full `StaffTab` at ~lines 259–401) and `StaffMarketModal.tsx`. A single backend payload field — `training_modifier_pct` — is added to `build_staff_market_state` in `staff_market.py`; this field is derived from the formula that already exists in `offseason_ceremony.py` and is the only honest number the training role can claim. No engine change. No new dependencies.

**Dependency:** Phase 0 already coerced staff OVR ratings to `int` at the payload boundary (`staff_market.py`). Phase 1 delivered the locked toolkit. Do not repeat either fix.

**Honesty rule (from `staff_market.py` top-of-file comment):**
- `training` department: the `rating_primary` already feeds `staff_development_modifier` in `offseason_ceremony.py` via `(rating_primary - 50) / 50 * max_staff_development_modifier`. This is a real mechanical hook. We CAN show a `ProofChip` backed by a computed `training_modifier_pct` field.
- All other departments (`tactics`, `conditioning`, `medical`, `scouting`, `culture`): no mechanical stat effect exists. They drive recommendation surfaces only. We present them with a `TermTip` role explainer + honest copy. We do NOT invent bonus values.

> **Pre-flight for the executor:**
> - Branch off `main` (or work in a named branch): `git checkout -b feat/v15-phase3b-staff-impact`.
> - Phase 1 must already be merged (imports from `frontend/src/legibility/`). Phase 0 must be merged (staff ratings are already ints).
> - Confirm Phase 1 is present: `ls frontend/src/legibility/` should show `index.ts`, `TermTip.tsx`, `ProofChip.tsx`, `EmptyState.tsx`, etc.
> - Verify green baseline: `python -m pytest -q` and from `frontend/`: `npm run build && npm run lint`.
> - No engine/sim/RNG files may be touched. `python tools/tier_engine_health_probe.py` must read identically before and after.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `src/dodgeball_sim/staff_market.py` | Add `training_modifier_pct` to payload | 1 |
| `frontend/src/legibility/terms.ts` | Append staff role terms (append-only) | 2 |
| `frontend/src/components/DynastyOffice.tsx` | Rework `StaffBrief` + `StaffTab` | 3, 4 |
| `frontend/src/components/dynasty/StaffMarketModal.tsx` | Honest `effect_lanes` display + `TermTip` roles | 5 |

Each task is independently committable.

---

## Task 1: Add `training_modifier_pct` to the staff payload

**Context:** The formula in `offseason_ceremony.py:493-494` computes:
```python
_staff_dev_modifier = (rating_primary - 50.0) / 50.0 * max_staff_development_modifier
```
where `max_staff_development_modifier = 0.15` (from `DEFAULT_CONFIG`). This is the only staff mechanical effect in the engine. Exposing this as a rounded-percentage in the payload gives the frontend a real, audit-traceable number to show in a `ProofChip`.

A training head with `rating_primary = 75` yields modifier = `(75 - 50) / 50 * 0.15 = 0.075`, which we surface as `8%` (rounded). A head at 50 yields `0%` (no bonus); below 50 clamps to `0%` (no penalty applied per `max(0.0, ...)`).

The field is added to the `training` department member's dict in `current_staff`. Other departments get `training_modifier_pct: None` (or the field is absent). The type contract for the current_staff array stays stable — we add one optional field.

**Files:**
- Modify: `src/dodgeball_sim/staff_market.py`
- Test: `tests/test_staff_market.py` (extend existing or create)

- [ ] **Step 1: Understand the current `build_staff_market_state` signature**

  Run: `grep -n "def build_staff_market_state\|current_staff\|effect_summary" src/dodgeball_sim/staff_market.py`
  Expected: confirms the list-comprehension at lines 36–38 where each `head` dict is spread with an added `effect_summary`.

- [ ] **Step 2: Write the failing test**

  Append to `tests/test_staff_market.py`:

  ```python
  def test_training_staff_exposes_modifier_pct(tmp_path):
      """Training head with rating 75 → modifier_pct ≥ 0 and > 0.
      Rating 50 → modifier_pct == 0. Other departments → no modifier_pct key (or None)."""
      from dodgeball_sim import persistence
      from dodgeball_sim.staff_market import build_staff_market_state

      db = tmp_path / "staff_mod.db"
      conn = persistence.connect(str(db))
      conn.execute(
          "INSERT INTO department_heads (department, name, rating_primary, rating_secondary, voice)"
          " VALUES (?, ?, ?, ?, ?)",
          ("training", "Dev Head", 75, 60, "Reps build the ceiling."),
      )
      conn.execute(
          "INSERT INTO department_heads (department, name, rating_primary, rating_secondary, voice)"
          " VALUES (?, ?, ?, ?, ?)",
          ("tactics", "Tactic Head", 70, 55, "Make every matchup leave evidence."),
      )
      conn.commit()

      state = build_staff_market_state(
          conn, season_id="season_1", player_club_id="club_user", root_seed=7
      )

      training = next(m for m in state["current_staff"] if m["department"] == "training")
      tactics = next(m for m in state["current_staff"] if m["department"] == "tactics")

      assert "training_modifier_pct" in training
      assert isinstance(training["training_modifier_pct"], int)
      assert training["training_modifier_pct"] > 0  # rating 75 → ~8

      # Non-training departments must not claim a modifier.
      assert tactics.get("training_modifier_pct") is None or "training_modifier_pct" not in tactics

  def test_training_modifier_pct_clamps_at_zero_below_baseline(tmp_path):
      """A training head rated exactly 50 → modifier 0% (no bonus, no penalty shown)."""
      from dodgeball_sim import persistence
      from dodgeball_sim.staff_market import build_staff_market_state

      db = tmp_path / "staff_clamp.db"
      conn = persistence.connect(str(db))
      conn.execute(
          "INSERT INTO department_heads (department, name, rating_primary, rating_secondary, voice)"
          " VALUES (?, ?, ?, ?, ?)",
          ("training", "Baseline Coach", 50, 50, "Baseline."),
      )
      conn.commit()

      state = build_staff_market_state(
          conn, season_id="season_1", player_club_id="club_user", root_seed=7
      )
      training = next(m for m in state["current_staff"] if m["department"] == "training")
      assert training["training_modifier_pct"] == 0
  ```

  Run: `python -m pytest tests/test_staff_market.py::test_training_staff_exposes_modifier_pct tests/test_staff_market.py::test_training_modifier_pct_clamps_at_zero_below_baseline -v`
  Expected: FAIL — `training_modifier_pct` not in payload yet.

- [ ] **Step 3: Implement the field in `build_staff_market_state`**

  In `src/dodgeball_sim/staff_market.py`, add the import for `DEFAULT_CONFIG` at the top of the file alongside the other imports:

  ```python
  from .config import DEFAULT_CONFIG
  ```

  Then add two module-level definitions **after** `staff_effect_summary` and **before** `build_staff_market_state` (i.e., at approximately line 28 after the existing helpers):

  ```python
  _MAX_STAFF_DEV_MOD: float = DEFAULT_CONFIG.max_staff_development_modifier


  def _training_modifier_pct(rating_primary: float | int) -> int:
      """Return the rounded-percentage offseason dev modifier for a training head.
      Formula mirrors offseason_ceremony.py:493-494. Clamps at 0 (no penalty exposed)."""
      raw = max(0.0, (float(rating_primary) - 50.0) / 50.0 * _MAX_STAFF_DEV_MOD)
      return round(raw * 100)
  ```

  Then replace the `current_staff` comprehension inside `build_staff_market_state` (currently lines 36–39):

  ```python
  current_staff = [
      {
          **head,
          "effect_summary": staff_effect_summary(head["department"]),
          **(
              {"training_modifier_pct": _training_modifier_pct(head["rating_primary"])}
              if head["department"] == "training"
              else {}
          ),
      }
      for head in load_department_heads(conn)
  ]
  ```

- [ ] **Step 4: Run the new tests; verify they pass**

  Run: `python -m pytest tests/test_staff_market.py -v`
  Expected: all PASS including the two new tests and any pre-existing ones.

- [ ] **Step 5: Run the full suite**

  Run: `python -m pytest -q`
  Expected: green.

- [ ] **Step 6: Commit**

  ```bash
  git add src/dodgeball_sim/staff_market.py tests/test_staff_market.py
  git commit -m "feat(v15-p3b): expose training_modifier_pct in staff payload

  The offseason development formula (offseason_ceremony.py:493-494) scales
  the training head's rating_primary into a 0-15% growth modifier. Surface
  this as an honest integer percentage in the staff_market payload so the
  frontend can show a ProofChip backed by a real engine value. Only the
  training department gets this field; other departments have no mechanical
  hook and therefore no comparable number.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 2: Append staff role terms to `terms.ts`

**Context:** Phase 1 pre-seeded `TERMS` with known V15 term ids. Phase 3b needs six staff-department terms (one per role). These are appended to the existing `TERMS` object — append-only, no removal of existing keys.

The terms describe what each department's *role* is. They are `kind: 'flavor'` for pure advisory roles and `kind: 'mechanical'` only for `training` (which has a proven engine hook).

**Files:**
- Modify (append-only): `frontend/src/legibility/terms.ts`

- [ ] **Step 1: Read the current bottom of `TERMS` to find the insertion point**

  Open `frontend/src/legibility/terms.ts` and locate the closing `} as const satisfies Record<string, TermDef>;` line. You will insert new entries immediately before it.

- [ ] **Step 2: Append the six staff role terms**

  Insert the following block as the final entries inside `TERMS` (before the closing `}`):

  ```ts
    // --- Staff roles (Phase 3b) ---
    'staff.training': {
      label: 'Training Staff',
      plain: 'Runs offseason player-development sessions and tracks rep quality.',
      why: 'Higher rating boosts each player\'s offseason OVR growth by up to 15% — the only staff role with a live mechanical hook.',
      kind: 'mechanical',
    },
    'staff.tactics': {
      label: 'Tactics Staff',
      plain: 'Prepares matchup-specific game plans and reviews replay evidence.',
      why: 'Advisory only — surfaces tactical recommendations in the command center; no hidden stat effect.',
      kind: 'flavor',
    },
    'staff.conditioning': {
      label: 'Conditioning Staff',
      plain: 'Monitors fatigue risk and designs recovery schedules.',
      why: 'Advisory only — flags overuse and recovery recommendations; no hidden stat effect.',
      kind: 'flavor',
    },
    'staff.medical': {
      label: 'Medical Staff',
      plain: 'Tracks player availability and warns on overuse risk.',
      why: 'Advisory only — availability warnings; no hidden stat effect.',
      kind: 'flavor',
    },
    'staff.scouting': {
      label: 'Scouting Staff',
      plain: 'Explains fit scores and clarifies the prospect board.',
      why: 'Advisory only — improves recruit board readability; no hidden fit-score modifier.',
      kind: 'flavor',
    },
    'staff.culture': {
      label: 'Culture Staff',
      plain: 'Frames promise risk and monitors command-plan stability.',
      why: 'Advisory only — surfaces promise-risk framing in the office; no hidden morale stat.',
      kind: 'flavor',
    },
  ```

- [ ] **Step 3: Compile gate (proves no orphan terms)**

  Run (from `frontend/`): `npm run build`
  Expected: PASS — `TermId` is still a valid closed union and the new keys compile.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/legibility/terms.ts
  git commit -m "feat(v15-p3b): append staff role terms to TERMS registry

  Six new term ids (staff.training through staff.culture) provide the
  TermTip copy for each department role. Only staff.training is
  kind:'mechanical'; the rest are kind:'flavor' per the honesty rule.
  Append-only — no existing term keys modified.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 3: Rework `StaffBrief` (the inline brief card in the overview tab)

**Context:** `StaffBrief` (DynastyOffice.tsx ~line 182) renders one row per current staff member showing `{department} / {name} / voice / OVR`. After Phase 0 OVR is already an int. This task adds a `TermTip` on the department label and surfaces the `training_modifier_pct` with a `ProofChip` for training staff, while other departments get the honest advisory copy from `effect_summary`.

This brief is rendered in the **Recruit** tab overview alongside the Credibility strip (see Phase 3a overlap note at the end of this plan).

**Files:**
- Modify: `frontend/src/components/DynastyOffice.tsx` (the `StaffBrief` function, lines ~182–206)

- [ ] **Step 1: Confirm current `StaffBrief` markup**

  Read lines 182–206 of `DynastyOffice.tsx` (already read above). The function signature is:
  ```tsx
  function StaffBrief({ staff }: { staff: DynastyOfficeResponse['staff_market']['current_staff'] })
  ```
  and renders a `do-staff-list` with one `do-staff-row` per member, containing `dept / name / voice / rating OVR`.

- [ ] **Step 2: Add toolkit imports at the top of `DynastyOffice.tsx`**

  Near the top of `frontend/src/components/DynastyOffice.tsx`, after the existing React/utility imports, add:

  ```tsx
  import { TermTip, ProofChip, EmptyState } from '../legibility';
  ```

  > Adjust the relative path if the component lives at a different depth (e.g. `../../legibility`). Check by reading the existing import block's relative paths to confirm the correct number of `../` segments.

- [ ] **Step 3: Update `StaffBrief` to use `TermTip` + conditional `ProofChip`**

  Replace the entire `StaffBrief` function body with:

  ```tsx
  function StaffBrief({ staff }: { staff: DynastyOfficeResponse['staff_market']['current_staff'] }) {
    if (staff.length === 0) {
      return (
        <div className="do-staff">
          <div className="do-panel-head">
            <span className="dm-kicker">Staff Room</span>
            <h3>Department Heads</h3>
          </div>
          <EmptyState
            title="No department heads hired"
            body="Use the Staff tab to browse pipeline candidates and hire your first department heads."
          />
        </div>
      );
    }
    return (
      <div className="do-staff">
        <div className="do-panel-head">
          <span className="dm-kicker">Staff Room</span>
          <h3>Department Heads</h3>
        </div>
        <div className="do-staff-list">
          {staff.map((member) => {
            const termId = `staff.${member.department}` as const;
            // Safe cast: the six departments match the pre-seeded staff.* term ids.
            // If a novel department appears with no term, fall back to plain copy.
            const hasTerm = [
              'staff.training', 'staff.tactics', 'staff.conditioning',
              'staff.medical', 'staff.scouting', 'staff.culture',
            ].includes(termId);
            const deptLabel = titleizeDepartment(member.department);
            return (
              <div key={`${member.department}-${member.name}`} className="do-staff-row">
                <div className="do-staff-id">
                  {hasTerm ? (
                    <TermTip term={termId as import('../legibility').TermId}>
                      <span className="dept">{deptLabel}</span>
                    </TermTip>
                  ) : (
                    <span className="dept">{deptLabel}</span>
                  )}
                  <span className="name">{member.name}</span>
                  <span className="voice">"{member.voice || member.effect_summary}"</span>
                </div>
                <div className="do-staff-rating" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.2rem' }}>
                  <span className="num">{member.rating_primary}</span>
                  <span className="lbl">OVR</span>
                  {member.department === 'training' && (member as { training_modifier_pct?: number }).training_modifier_pct !== undefined && (
                    <ProofChip
                      label={`+${(member as { training_modifier_pct?: number }).training_modifier_pct}% dev`}
                      source={`Training OVR ${member.rating_primary} → offseason growth modifier ${(member as { training_modifier_pct?: number }).training_modifier_pct}% (formula: (OVR − 50) / 50 × 15%, clamped at 0).`}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }
  ```

  > The `as { training_modifier_pct?: number }` cast is needed because the TypeScript type for `current_staff` members does not yet include the new field. Task 6 updates the type. For now the cast is explicit and localized to `StaffBrief`.

- [ ] **Step 4: Build + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS. If the `TermId` cast triggers a lint error about `import(...)` inside JSX, switch to a top-of-file `import type { TermId } from '../legibility'` and use `termId as TermId` instead.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/components/DynastyOffice.tsx
  git commit -m "feat(v15-p3b): StaffBrief uses TermTip + ProofChip for training impact

  Department labels are now wrapped in a TermTip (explainer popup). The
  training head shows a ProofChip backed by training_modifier_pct from the
  payload (derived from the real offseason dev formula). All other
  departments show their honest advisory effect_summary with no invented
  stats. Empty staff list now renders an EmptyState instead of nothing.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 4: Rework `StaffTab` (the full Staff sub-tab)

**Context:** The `StaffTab` function (DynastyOffice.tsx ~lines 259–401) contains:
1. A glance bar (4 stat cells) — fine as-is, no changes needed.
2. A `do-staff-grid` of detail cards — currently shows `department`, `name`, OVR, voice, specs badges, a meta `<dl>`, and a `"Season Impact"` slot with `effect_summary`.
3. A `do-vacancy-card` — when no vacancies, shows a plain `<div>` with text instead of an `EmptyState`.
4. A `do-pipeline-card` listing candidates with an "Interview" button that actually calls the hire endpoint.

This task: adds `TermTip` on department in each staff card; surfaces the training `ProofChip` in the "Season Impact" slot; replaces the vacancy fallback `<div>` with `EmptyState`; and clarifies the Pipeline Candidates action label to be honest ("Hire" not "Interview" — the endpoint does `INSERT OR REPLACE` directly, it's a hire, not a two-step interview).

**Files:**
- Modify: `frontend/src/components/DynastyOffice.tsx` (the `StaffTab` function, lines ~259–401)

  > `EmptyState` and `ProofChip` are already imported by Task 3. No new imports needed.

- [ ] **Step 1: Confirm the vacancy fallback and pipeline candidate markup**

  Read lines 336–398 of `DynastyOffice.tsx` (already read above):
  - Vacancy empty fallback is a `<div style=...>` at lines 354–357.
  - Candidate button label is "Interview" at line 387, `normalizedStage` is `'scheduled'` during hiring (line 370).
  - The `handleInterview` callback calls `dynastyApi.hireStaff(candidateId)` (line 274) — confirming this is a direct hire, not a two-step interview.

- [ ] **Step 2: Update the staff card "Season Impact" slot to use `TermTip` + `ProofChip`**

  In the `do-staff-grid` map block (lines ~304–333), replace the bottom `<div className="impact">` section:

  ```tsx
  <div className="impact" style={{ marginTop: '0.5rem' }}>
    <span className="lbl" style={{ fontSize: '0.6rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
      {member.department === 'training' ? 'Development Impact' : 'Program Role'}
    </span>
    <span className="val" style={{ fontSize: '0.72rem', color: '#cbd5e1', lineHeight: 1.4 }}>
      {member.effect_summary}
    </span>
    {member.department === 'training' && (member as { training_modifier_pct?: number }).training_modifier_pct !== undefined && (
      <div style={{ marginTop: '0.35rem' }}>
        <ProofChip
          label={`+${(member as { training_modifier_pct?: number }).training_modifier_pct}% offseason growth`}
          source={`Training OVR ${member.rating_primary} feeds the offseason development formula: modifier = (OVR − 50) / 50 × 15%, clamped at 0. Applied to every player on your roster each offseason.`}
        />
      </div>
    )}
  </div>
  ```

  Also replace the department kicker inside the card head to use `TermTip`:

  ```tsx
  <div className="do-staff-card-head">
    <div>
      {(['staff.training', 'staff.tactics', 'staff.conditioning',
         'staff.medical', 'staff.scouting', 'staff.culture'] as const).includes(
          `staff.${member.department}` as 'staff.training'
        ) ? (
        <TermTip term={`staff.${member.department}` as import('../legibility').TermId}>
          <span className="dm-kicker">{titleizeDepartment(member.department)}</span>
        </TermTip>
      ) : (
        <span className="dm-kicker">{titleizeDepartment(member.department)}</span>
      )}
      <p className="name">{member.name}</p>
    </div>
    <div className="rating">
      <span className="num">{member.rating_primary}</span>
      <span className="lbl">OVR</span>
    </div>
  </div>
  ```

  > The `TermId` cast approach from Task 3 applies here too. If the cast is messy in JSX, extract a small helper: `const staffTermId = (dept: string): TermId | null => { const id = \`staff.${dept}\`; return KNOWN_STAFF_TERMS.includes(id) ? id as TermId : null; }` placed at the top of the component or as a module-level constant.

- [ ] **Step 3: Replace the vacancy empty fallback with `EmptyState`**

  Replace the fallback `<div>` inside the `do-vacancy-card` (when `vacancies.length === 0`) with:

  ```tsx
  ) : (
    <EmptyState
      title="All roles are filled"
      body="All tracked department heads are currently hired. Vacancies appear here when a position opens."
    />
  )}
  ```

- [ ] **Step 4: Rename "Interview" to "Hire" in the Pipeline Candidates panel**

  The endpoint `POST /api/dynasty-office/staff/hire` performs a direct `INSERT OR REPLACE` — it is a hire, not a two-step interview. Rename the button and its loading state to be honest:

  ```tsx
  // Change:
  const normalizedStage = isHiring ? 'scheduled' : 'available';
  // To:
  const normalizedStage = isHiring ? 'hiring' : 'available';

  // Change button label:
  {isHiring ? 'Hiring...' : 'Hire'}
  ```

  Add a short honest note below the pipeline panel header to set expectations:

  ```tsx
  <div className="do-panel-head">
    <span className="dm-kicker">Pipeline</span>
    <h3>Candidates</h3>
  </div>
  <p style={{ fontSize: '0.68rem', color: '#94a3b8', margin: '0 0 0.5rem 0', padding: '0 1.2rem' }}>
    Candidates are generated each offseason. Hiring immediately replaces the current department head.
  </p>
  ```

  > If the candidate list is empty, the existing fallback `<div>` is already reasonably honest; no change required. If the text says "No live staff candidates are on the board this week. Completed interviews appear in recent staff moves." — update "Completed interviews" to "Completed hires" for consistency.

- [ ] **Step 5: Surface candidate role with a `TermTip` in the pipeline list**

  In the candidate map inside `do-pipe-list`, add a `TermTip` around the department label:

  ```tsx
  <div className="do-pipe-id">
    <span className="name">{candidate.name}</span>
    {(['staff.training', 'staff.tactics', 'staff.conditioning',
       'staff.medical', 'staff.scouting', 'staff.culture'] as const).includes(
        `staff.${candidate.department}` as 'staff.training'
      ) ? (
      <TermTip term={`staff.${candidate.department}` as import('../legibility').TermId}>
        <span className="dept">{titleizeDepartment(candidate.department)}</span>
      </TermTip>
    ) : (
      <span className="dept">{titleizeDepartment(candidate.department)}</span>
    )}
    <span className="note">{candidate.effect_lanes[0] || candidate.voice}</span>
  </div>
  ```

  > Only show `effect_lanes[0]` (the role summary), not the full `.join(' · ')` which previously exposed the raw `"ratings would become X.X/Y.Y"` line. After Phase 0's int coercion the second lane reads `"Visible staff ratings would become 82/67."` which is still useful but verbose; showing only the first lane keeps the list compact. The full effect_lanes are available if the player clicks through to hire.

- [ ] **Step 6: Build + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/src/components/DynastyOffice.tsx
  git commit -m "feat(v15-p3b): StaffTab legibility — TermTip roles, training ProofChip, EmptyState vacancies

  - Each staff card's department label is wrapped in a TermTip (hover/tap
    reveals role description + mechanical vs advisory pill).
  - Training head's 'Development Impact' slot shows a ProofChip backed by
    training_modifier_pct (derived from the real offseason dev formula).
  - Advisory departments (tactics/conditioning/medical/scouting/culture)
    show their honest effect_summary with no invented stat bonuses.
  - Vacancies empty-state replaces the raw <div> text.
  - Pipeline Candidates: 'Interview' renamed 'Hire' to match the actual
    endpoint behavior (direct INSERT OR REPLACE). Only the first effect lane
    is shown in the list for readability.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 5: Update `StaffMarketModal.tsx`

**Context:** `StaffMarketModal.tsx` is a secondary modal surface that also renders candidates with their `effect_lanes`. After Phase 0, the second lane reads `"Visible staff ratings would become 82/67."` (integers). This task adds a `TermTip` on the department label and honest role framing.

**Files:**
- Modify: `frontend/src/components/dynasty/StaffMarketModal.tsx`

- [ ] **Step 1: Confirm modal import path depth**

  The modal is at `frontend/src/components/dynasty/StaffMarketModal.tsx`. The legibility barrel is at `frontend/src/legibility/`. The relative import is: `import { TermTip } from '../../legibility';`

- [ ] **Step 2: Update `StaffMarketModal.tsx`**

  Replace the file contents with:

  ```tsx
  import { TermTip } from '../../legibility';
  import type { TermId } from '../../legibility';
  import { ActionButton } from '../ui';
  import type { DynastyOfficeResponse } from '../../types';

  type StaffCandidate = DynastyOfficeResponse['staff_market']['candidates'][number];

  const KNOWN_STAFF_TERM_IDS = [
    'staff.training', 'staff.tactics', 'staff.conditioning',
    'staff.medical', 'staff.scouting', 'staff.culture',
  ] as const;

  function staffTermId(department: string): TermId | null {
    const id = `staff.${department}`;
    return (KNOWN_STAFF_TERM_IDS as readonly string[]).includes(id) ? id as TermId : null;
  }

  export function StaffMarketModal({
    candidates,
    onHire,
    onClose,
  }: {
    candidates: StaffCandidate[];
    onHire: (id: string) => void;
    onClose: () => void;
  }) {
    return (
      <div
        style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        <div className="dm-panel" style={{ width: '600px', maxHeight: '80vh', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <p className="dm-kicker">Program Staff</p>
              <h2 style={{ margin: '0.25rem 0 0', color: '#fff' }}>Staff Market</h2>
            </div>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.25rem' }}
              aria-label="Close staff market"
            >
              X
            </button>
          </div>
          <p style={{ fontSize: '0.68rem', color: '#94a3b8', margin: '0 0 1rem 0' }}>
            Hiring immediately replaces the current department head. Candidates refresh each offseason.
          </p>
          {candidates.map((c) => {
            const tid = staffTermId(c.department);
            const deptLabel = c.department.replace(/^\w/, (ch) => ch.toUpperCase());
            return (
              <div
                key={c.candidate_id}
                style={{ padding: '1rem', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', gap: '1rem' }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>{c.name}</div>
                  <div style={{ fontSize: '0.75rem', color: '#22d3ee', marginBottom: '0.35rem' }}>
                    {tid ? (
                      <TermTip term={tid}>{deptLabel.toUpperCase()}</TermTip>
                    ) : (
                      deptLabel.toUpperCase()
                    )}
                  </div>
                  {c.effect_lanes.map((lane: string) => (
                    <div key={lane} style={{ fontSize: '0.65rem', color: '#94a3b8', lineHeight: 1.35 }}>
                      {lane}
                    </div>
                  ))}
                </div>
                <ActionButton onClick={() => onHire(c.candidate_id)}>Hire</ActionButton>
              </div>
            );
          })}
          {candidates.length === 0 && (
            <div style={{ padding: '1.5rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.84rem' }}>
              No candidates are available this period.
            </div>
          )}
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 3: Build + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS.

- [ ] **Step 4: Commit**

  ```bash
  git add frontend/src/components/dynasty/StaffMarketModal.tsx
  git commit -m "feat(v15-p3b): StaffMarketModal — TermTip roles + honest hire copy

  Department labels in the market modal now use TermTip for the same
  role explainer as StaffTab. 'Interview' button renamed 'Hire' (matches
  the endpoint semantics). Honest header note explains immediate replacement.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Task 6: Update the frontend type for `current_staff` to include `training_modifier_pct`

**Context:** Tasks 3 and 4 used `as { training_modifier_pct?: number }` casts as a temporary measure. Now we formalize the type so future code can access the field without casting.

**Files:**
- Modify: `frontend/src/types.ts` (the `staff_market.current_staff` array type, ~lines 1133–1141)

- [ ] **Step 1: Read the current type definition**

  Confirm the exact lines of the `current_staff` Array shape in `frontend/src/types.ts` (already read above — lines 1134–1141).

- [ ] **Step 2: Add the optional field**

  Replace the `current_staff` array type:

  ```ts
      current_staff: Array<{
          department: string;
          name: string;
          rating_primary: number;
          rating_secondary: number;
          voice: string;
          effect_summary: string;
          /** Offseason growth modifier percentage, present only for the 'training' department. */
          training_modifier_pct?: number;
      }>;
  ```

- [ ] **Step 3: Remove the casts in `DynastyOffice.tsx`**

  Now that the type carries `training_modifier_pct?`, remove the `as { training_modifier_pct?: number }` casts in the `StaffBrief` and `StaffTab` staff card blocks. Access `member.training_modifier_pct` directly.

- [ ] **Step 4: Build + lint**

  Run (from `frontend/`): `npm run build && npm run lint`
  Expected: PASS. No remaining `any` or unsafe cast warnings related to this field.

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/src/types.ts frontend/src/components/DynastyOffice.tsx
  git commit -m "feat(v15-p3b): formalize training_modifier_pct in frontend type

  Remove the temporary casts introduced in Tasks 3-4 now that the
  types.ts DynastyOfficeResponse carries training_modifier_pct? on
  current_staff members.

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  ```

---

## Phase 3b Exit Gates

Run all before declaring Phase 3b done:

- [ ] `python -m pytest -q` — green (the two new `test_staff_market` tests pass; no regressions).
- [ ] `python tools/tier_engine_health_probe.py --driver official --trials 50` — summary **identical** to the Phase 0 baseline (zero sim drift; this phase is display + payload-plumbing only).
- [ ] From `frontend/`: `npm run build` — clean (the tsc gate proves no orphan staff terms; `staff.training` … `staff.culture` all resolve against `TermId`).
- [ ] From `frontend/`: `npm run lint` — clean.
- [ ] From repo root: `npm run e2e` — no Playwright regressions (core dynasty + staff flows).
- [ ] Manual sanity at 390×844 on a save with at least one staff member hired:
  - Staff brief card in the overview: department label has a dotted underline; tapping it shows the TermTip popup with the role description and a `AFFECTS PLAY` or `FLAVOR` pill.
  - Training head: a cyan `ProofChip` reads `+N% dev`; clicking it expands the formula proof string. No percentage shown for any other department.
  - Staff tab vacancy section: if all 6 slots are filled, renders `EmptyState` ("All roles are filled") rather than a blank card.
  - Pipeline Candidates: button reads "Hire" not "Interview"; a contextual note explains immediate replacement.
  - No horizontal overflow at 390px.
- [ ] No `playtest_output/*.png` or local `*.db` files committed.

---

## DynastyOffice.tsx overlap with Phase 3a

Phase 3a ("Dynasty Office / Credibility") also modifies `DynastyOffice.tsx`. The two phases own **distinct functions** within the file:

| Phase | Functions touched |
|---|---|
| **Phase 3a** | `CredibilityStrip` (credibility card, "01/02/03" jargon, budget relocation); the `RecruitBoard` filter block (if not already handled by Phase 0 Task 3); the top-level `DynastyOffice` render tree. |
| **Phase 3b** | `StaffBrief`, `StaffTab`, `StaffMarketModal` (separate file). |

**Merge strategy:** These phases can run in parallel. The only collision risk is if both phases touch the same `import` block at the top of `DynastyOffice.tsx`. The normalizing action: whoever lands second should verify that the `import { TermTip, ProofChip, EmptyState } from '../legibility'` import (added by Phase 3b Task 3 Step 2) is not duplicated by Phase 3a's own import additions — consolidate them into a single import statement. This is a one-line merge resolution and does not require coordination before starting.

## Out of Scope for Phase 3b (do NOT do here)

- Staff economy redesign (contract costs, firing/release mechanics) — Bucket C, own spec.
- Department-hub restructure (office subpages per department) — Bucket C, own spec.
- Any OVR formula change or staff-modifier tuning — engine/balance work, out of V15.
- New npm or Python dependencies.
- Changes to `offseason_ceremony.py`, `development.py`, or any other engine file.
- Routing or auth changes.
