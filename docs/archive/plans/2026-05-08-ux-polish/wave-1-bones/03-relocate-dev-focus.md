# Subplan 03: Relocate Dev Focus to Roster

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first. Depends on Subplan 02. Parallel-safe with Subplan 04 (touches different blocks of `MatchWeek.tsx` and a different second file).

**Goal:** Remove the Dev Focus selector from `MatchWeek.tsx` (pre-sim mode) and surface it as a chip in the Roster header strip, where it conceptually belongs (it's a season-long player-development setting, not a per-match knob).

**Architecture:** Backend `/api/command-center/plan` endpoint is preserved unchanged — Roster's chip POSTs to the same endpoint with only the `dev_focus` field updated, leaving the other plan fields untouched. This avoids any API surface churn during Wave 1.

**Files:**
- Modify: `frontend/src/components/MatchWeek.tsx` (remove Dev Focus `<label>` block)
- Modify: `frontend/src/components/Roster.tsx` (add Dev Focus chip to header strip)
- Modify: `frontend/src/types.ts` if needed (likely no change — `department_orders` already typed)
- Modify: `src/dodgeball_sim/server.py` ONLY if the existing endpoint cannot accept a partial `department_orders` update. If it can (and the merge happens server-side), no backend change.
- Add Python test: `tests/test_dev_focus_partial_update.py` — POSTs `{department_orders: {dev_focus: "YOUTH_ACCELERATION"}}` and asserts other department orders survive untouched.

**Verification gates:**
- `cd frontend && npm run build` exits 0
- `python -m pytest -q` exits 0 (including the new test)
- Manual smoke: Dev Focus no longer appears on Match Week pre-sim; Roster header chip displays current Dev Focus and changing it persists.

**Parallel-safety with Subplan 04:** Subplan 03 touches the Dev Focus `<label>` block (originally CommandCenter.tsx lines 158-183). Subplan 04 touches the department-orders grid (originally lines 186-194) and the Intent select / surrounding container is shared — when both subplans land, the parent grid container becomes empty. Whichever subplan merges *second* must also remove the now-empty parent grid wrapper (the `<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>` at the original line 130). Both subplans include a final cleanup step for this case.

---

- [ ] **Step 1: Verify Subplan 02 is merged and baseline green**

Run: `git log --oneline -5` (look for "subplan 02" / "Match Week shell")
Run: `cd frontend && npm run build` — must PASS
Run: `python -m pytest -q` — must PASS

- [ ] **Step 2: Write the failing Python test for partial dev_focus update**

Create `tests/test_dev_focus_partial_update.py`:

```python
"""Verify POSTing a partial department_orders update preserves other orders."""
from fastapi.testclient import TestClient
from dodgeball_sim.server import app


def test_dev_focus_partial_update_preserves_other_orders():
    client = TestClient(app)
    # Seed a save (the existing test fixtures likely provide a helper — adapt as needed)
    # If the endpoint requires an active save, load one via /api/saves/load first.
    # For this test, focus on the merge semantics: send only dev_focus, verify the
    # rest of department_orders is unchanged in the response.

    # Adapt the seed-save / load-save call here to match existing test patterns.
    # ... (look at existing tests in tests/ for the canonical setup)

    initial = client.get('/api/command-center').json()
    initial_orders = initial['plan']['department_orders']
    assert 'tactics' in initial_orders  # sanity

    response = client.post(
        '/api/command-center/plan',
        json={
            'intent': initial['plan']['intent'],
            'department_orders': {'dev_focus': 'YOUTH_ACCELERATION'},
        },
    )
    assert response.status_code == 200
    after = response.json()['plan']['department_orders']

    assert after.get('dev_focus') == 'YOUTH_ACCELERATION'
    # Critical: every other department order must be untouched
    for key, value in initial_orders.items():
        if key == 'dev_focus':
            continue
        assert after.get(key) == value, f"department order '{key}' was clobbered"
```

(If the existing test suite uses fixtures or factory helpers for session setup, follow those patterns instead of hand-rolling — read `tests/conftest.py` and one existing endpoint test first.)

- [ ] **Step 3: Run the test, see it fail or pass**

Run: `python -m pytest tests/test_dev_focus_partial_update.py -v`

If it PASSES already, the backend already merges partial updates — skip Step 4 and proceed to Step 5.
If it FAILS (because the endpoint clobbers unspecified orders), continue to Step 4.

- [ ] **Step 4: (Conditional) Make the backend merge partial department_orders updates**

In `src/dodgeball_sim/server.py`, find the handler for `/api/command-center/plan` (search for `command-center/plan` or `CoachPolicyUpdate`). Locate where `department_orders` from the request payload replaces the saved value. Change the assignment to a merge:

```python
# Before (illustrative):
plan.department_orders = payload.department_orders

# After:
plan.department_orders = {**plan.department_orders, **payload.department_orders}
```

The exact field path depends on the implementation — read the handler before editing. The principle: incoming `department_orders` keys override existing keys; missing keys preserve their existing values.

Re-run the test from Step 3. It must PASS now.

- [ ] **Step 5: Remove the Dev Focus `<label>` block from `MatchWeek.tsx`**

In `frontend/src/components/MatchWeek.tsx`, locate the block (originally CommandCenter lines 158-183) that begins:

```tsx
<label style={{ display: 'block' }}>
  <span className="dm-kicker" style={{ display: 'block', marginBottom: '0.375rem' }}>Dev Focus</span>
  <select
    aria-label="Development Focus"
    ...
```

Delete the entire `<label>` block (the whole element, opening to closing tag, including the `<select>` and its options).

Also delete:
- The `devFocusOptions` constant at the top of the file (`const devFocusOptions = [...]`)
- The `localDevFocus` state and `selectedDevFocus` derivation (`const [localDevFocus, ...] = useState(...)` and `const selectedDevFocus = localDevFocus ?? ...`)
- Any place `selectedDevFocus` is passed to `savePlan` — replace with `selectedDevFocus` removed from the call site (the `savePlan` signature should now default-fill from existing data; see Step 6).

- [ ] **Step 6: Update `savePlan` in `MatchWeek.tsx` to no longer take dev_focus**

Change the `savePlan` function signature from:

```ts
const savePlan = (intent = selectedIntent, devFocus = selectedDevFocus) => {
  ...
  body: JSON.stringify({ intent, department_orders: { dev_focus: devFocus } }),
```

To:

```ts
const savePlan = (intent = selectedIntent) => {
  ...
  body: JSON.stringify({ intent }),
```

(Send `intent` only. Department orders, including dev_focus, are managed elsewhere.)

Update all callers of `savePlan(...)` in the file accordingly — drop the second argument.

- [ ] **Step 7: Add the Dev Focus chip to `Roster.tsx` header strip**

Read `frontend/src/components/Roster.tsx` to identify where the existing summary header (currently showing "players / starters / avg ovr") is rendered. That's the target.

In the header strip, add a chip element that:
1. Reads the current dev_focus from `data.plan.department_orders.dev_focus` (the Roster endpoint may not currently return this — see Step 8)
2. On click, opens a small dropdown / picker with the four options (`BALANCED`, `YOUTH_ACCELERATION`, `TACTICAL_DRILLS`, `STRENGTH_AND_CONDITIONING`)
3. On selection, POSTs to `/api/command-center/plan` with `{ intent: <current_intent>, department_orders: { dev_focus: <new_value> } }`

A minimal implementation:

```tsx
const DEV_FOCUS_OPTIONS = ['BALANCED', 'YOUTH_ACCELERATION', 'TACTICAL_DRILLS', 'STRENGTH_AND_CONDITIONING'];

function DevFocusChip({
  current,
  intent,
  onUpdated,
}: {
  current: string;
  intent: string;
  onUpdated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const update = (next: string) => {
    fetch('/api/command-center/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent, department_orders: { dev_focus: next } }),
    })
      .then(() => { setOpen(false); onUpdated(); });
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="dm-kicker"
        style={{ padding: '0.5rem 0.75rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: '#22d3ee', fontWeight: 700, cursor: 'pointer' }}
      >
        Dev Focus: {current.replace(/_/g, ' ')}
      </button>
      {open && (
        <div style={{ position: 'absolute', top: '100%', left: 0, marginTop: '0.25rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', zIndex: 10, minWidth: '200px' }}>
          {DEV_FOCUS_OPTIONS.map(opt => (
            <button
              key={opt}
              onClick={() => update(opt)}
              style={{ display: 'block', width: '100%', padding: '0.5rem 0.75rem', background: opt === current ? '#1e293b' : 'transparent', border: 'none', color: '#e2e8f0', textAlign: 'left', cursor: 'pointer', fontFamily: 'var(--font-display)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}
            >
              {opt.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

Place the chip in the existing Roster header strip alongside the player/starters/avg-ovr stats. Wire `current`, `intent`, and `onUpdated` (which should re-fetch Roster data) accordingly.

- [ ] **Step 8: Ensure Roster's data source includes `dev_focus`**

If `Roster.tsx` doesn't already fetch the command-center plan, add a fetch alongside its existing data load. Two options:
- Option A: Roster fetches `/api/command-center` to read the plan (simple, one extra request).
- Option B: Extend the Roster endpoint to include `dev_focus` and `intent` in its response.

For Wave 1, choose Option A — simpler and avoids backend type churn:

In `Roster.tsx`, inside the existing data-loading flow (likely a `useEffect` or `useApiResource` call), add:

```ts
const [planContext, setPlanContext] = useState<{ intent: string; dev_focus: string } | null>(null);
useEffect(() => {
  fetch('/api/command-center')
    .then(r => r.json())
    .then((d: CommandCenterResponse) => setPlanContext({
      intent: d.plan.intent,
      dev_focus: d.plan.department_orders?.dev_focus ?? 'BALANCED',
    }));
}, []);
```

Pass `planContext` into the chip; only render the chip when `planContext` is loaded.

- [ ] **Step 9: Run TypeScript build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 10: Run Python tests**

Run: `python -m pytest -q`
Expected: PASS (including the new partial-update test).

- [ ] **Step 11: Manual smoke test**

- Open Match Week → Pre-sim mode. The "Dev Focus" select is GONE. Intent select still present.
- Open Roster. Header strip now shows a "Dev Focus: BALANCED" (or current value) chip. Clicking opens the picker. Selecting a different option closes the picker and the chip label updates.
- Reload the page. The new Dev Focus value persists.
- Go back to Match Week. Confirm `intent` is still settable and saving (other department orders survived the partial update).

- [ ] **Step 12: Cleanup if Subplan 04 has already merged**

If Subplan 04 has already merged before this step runs, the parent grid container around the now-removed Dev Focus / Department Orders blocks may be empty. Run:

```bash
cd frontend && npm run build
```

If the build flags an unused variable or empty grid, open `MatchWeek.tsx` and remove the now-empty grid wrapper (the outer `<div style={{ display: 'grid', gridTemplateColumns: ... }}>` that previously held both Intent + Dev Focus). Keep the Intent `<label>` — relocate it directly under the parent if needed.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/components/MatchWeek.tsx frontend/src/components/Roster.tsx tests/test_dev_focus_partial_update.py
# If Step 4 ran, also:
# git add src/dodgeball_sim/server.py
git commit -m "feat(ui): relocate Dev Focus from Match Week to Roster header (Wave 1 subplan 03)

Dev Focus is a season-long player-development setting; it belongs near the
players, not on the per-match weekly checklist. Reads/writes go to the same
/api/command-center/plan endpoint via partial department_orders update.

Refs docs/superpowers/plans/2026-05-08-ux-polish/00-MAIN.md"
```
