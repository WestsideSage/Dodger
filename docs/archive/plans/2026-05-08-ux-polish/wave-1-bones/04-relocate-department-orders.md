# Subplan 04: Relocate Department Orders to Dynasty Office

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first. Depends on Subplan 02. Parallel-safe with Subplan 03.

**Goal:** Remove the read-only "Department Orders" tile grid from `MatchWeek.tsx` and surface department orders as an editable "Program Priorities" panel in `DynastyOffice.tsx`.

**Architecture:** Same backend endpoint (`/api/command-center/plan`) handles reads and writes via partial `department_orders` updates. Subplan 03 adds the partial-merge semantics if not already present; Subplan 04 reuses them. Currently the Match Week display is read-only — Subplan 04 makes the Dynasty Office surface fully editable.

**Files:**
- Modify: `frontend/src/components/MatchWeek.tsx` (remove department-orders tile grid + `departmentLabels` constant)
- Modify: `frontend/src/components/DynastyOffice.tsx` (add Program Priorities panel)
- (Backend: no change — relies on Subplan 03's partial-merge if both subplans land. If Subplan 04 lands FIRST, this subplan's Step 3 covers the backend merge change.)
- Add Python test: `tests/test_department_orders_partial_update.py` (skip if Subplan 03 already added an equivalent test — they cover the same merge semantics)

**Verification gates:**
- `cd frontend && npm run build` exits 0
- `python -m pytest -q` exits 0
- Manual smoke: Department orders no longer visible on Match Week pre-sim; Dynasty Office shows them in an editable panel; changes persist.

**Parallel-safety with Subplan 03:** See Subplan 03's note. Both subplans include a final cleanup step for the empty parent grid container.

---

- [ ] **Step 1: Verify Subplan 02 is merged and baseline green**

Run: `git log --oneline -5` (look for "subplan 02")
Run: `cd frontend && npm run build` — must PASS
Run: `python -m pytest -q` — must PASS

- [ ] **Step 2: Check whether Subplan 03 has already landed the partial-merge backend change**

Search for evidence of partial merge in `src/dodgeball_sim/server.py`:

Look at the handler for `/api/command-center/plan`. If it does:
```python
plan.department_orders = {**plan.department_orders, **payload.department_orders}
```
or equivalent, the merge is in place — proceed to Step 4.

If it does a wholesale replacement (`plan.department_orders = payload.department_orders`), continue to Step 3.

- [ ] **Step 3: (Conditional) Make backend merge partial department_orders updates**

Apply the same change as Subplan 03 Step 4. Add the test from Subplan 03 Step 2 if not already present.

Run: `python -m pytest tests/test_dev_focus_partial_update.py -v` — must PASS.

- [ ] **Step 4: Remove the department-orders tile grid from `MatchWeek.tsx`**

In `frontend/src/components/MatchWeek.tsx`, locate the block (originally CommandCenter lines 186-194) that begins:

```tsx
{/* Department orders */}
<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', marginTop: '1rem' }}>
  {Object.entries(plan.department_orders).filter(([key]) => key !== 'dev_focus').map(([key, value]) => (
    <Tile key={key}>
      ...
    </Tile>
  ))}
</div>
```

Delete the entire block (from the comment through the closing `</div>`).

Also delete the `departmentLabels` constant at the top of the file (originally line 8-15):

```ts
const departmentLabels: Record<string, string> = {
  tactics: 'Tactics',
  ...
};
```

Remove `Tile` from the imports if `Tile` is no longer used anywhere in `MatchWeek.tsx`. If it's still used elsewhere in the file, keep it.

- [ ] **Step 5: Add a Program Priorities panel to `DynastyOffice.tsx`**

Read `frontend/src/components/DynastyOffice.tsx` to identify the page layout. After Wave 1 there are no sub-tabs yet (those land in Wave 2 Subplan 08); add the new panel as a top-level panel on the existing page.

Add the panel at the top of `DynastyOffice`'s rendered output (above any existing recruiting / credibility / staff / league memory panels):

```tsx
const DEPARTMENT_LABELS: Record<string, string> = {
  tactics: 'Tactics',
  training: 'Training',
  conditioning: 'Conditioning',
  medical: 'Medical',
  scouting: 'Scouting',
  culture: 'Culture',
};

// Inside the DynastyOffice component, after existing data hooks:
const [planContext, setPlanContext] = useState<CommandCenterResponse | null>(null);
useEffect(() => {
  fetch('/api/command-center').then(r => r.json()).then(setPlanContext);
}, []);

const updateDepartmentOrder = (key: string, value: string) => {
  if (!planContext) return;
  fetch('/api/command-center/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      intent: planContext.plan.intent,
      department_orders: { [key]: value },
    }),
  })
    .then(r => r.json())
    .then(setPlanContext);
};

// In the rendered JSX, the panel:
{planContext && (
  <div className="dm-panel">
    <div className="dm-panel-header">
      <p className="dm-kicker">Program Priorities</p>
      <h2 className="dm-panel-title">Department Orders</h2>
      <p className="dm-panel-subtitle">Season-long staff priorities. Adjust rarely.</p>
    </div>
    <div className="dm-section" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
      {Object.entries(planContext.plan.department_orders)
        .filter(([key]) => key !== 'dev_focus')
        .map(([key, value]) => (
          <label key={key} style={{ display: 'block' }}>
            <span className="dm-kicker" style={{ display: 'block', marginBottom: '0.375rem' }}>{DEPARTMENT_LABELS[key] ?? key}</span>
            <input
              type="text"
              value={String(value)}
              onChange={e => updateDepartmentOrder(key, e.target.value)}
              style={{
                width: '100%', background: '#0f172a', border: '1px solid #334155',
                borderRadius: '4px', padding: '0.5rem 0.75rem', color: '#e2e8f0',
                fontFamily: 'var(--font-display)', fontSize: '0.75rem',
              }}
            />
          </label>
      ))}
    </div>
  </div>
)}
```

The text input is acceptable for Wave 1 — Subplan 08 (Wave 2) will replace this with a richer affordance (likely a dropdown if the sim exposes valid options per department, or merge it into the recruiting slot economy).

If the sim already exposes a fixed set of valid values per department, prefer a `<select>` over a text input. Read `src/dodgeball_sim/command_center.py` for canonical option lists; if found, use them.

- [ ] **Step 6: Run TypeScript build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 7: Run Python tests**

Run: `python -m pytest -q`
Expected: PASS.

- [ ] **Step 8: Manual smoke test**

- Open Match Week → Pre-sim mode. The Department Orders tile grid is GONE.
- Open Dynasty Office. The new "Program Priorities" panel is visible at the top with all six departments (excluding dev_focus, which lives on Roster per Subplan 03).
- Edit one department's value. The change persists across page reload.
- Reload Match Week. Intent dropdown still functions; saving intent does not clobber department orders.

- [ ] **Step 9: Cleanup if Subplan 03 has already merged**

If Subplan 03 has already merged, the Match Week pre-sim grid wrapper that previously held both Intent + Dev Focus is now empty after Subplan 04 also removes the department tiles. Run the build and inspect any empty parent containers in `MatchWeek.tsx`. Specifically the original `<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>` (originally CommandCenter line 130) — if this now contains only Intent, simplify it to a single column or remove the grid wrapper entirely, leaving the `<label>` for Intent at its natural width.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/MatchWeek.tsx frontend/src/components/DynastyOffice.tsx
# If Step 3 ran:
# git add src/dodgeball_sim/server.py tests/test_department_orders_partial_update.py
git commit -m "feat(ui): relocate department orders from Match Week to Dynasty Office (Wave 1 subplan 04)

Department orders are program-management settings, not weekly knobs. Moves
the read-only Match Week tile grid to an editable Program Priorities panel
on Dynasty Office. Reads/writes go to the existing /api/command-center/plan
endpoint via partial update.

Refs docs/superpowers/plans/2026-05-08-ux-polish/00-MAIN.md"
```
