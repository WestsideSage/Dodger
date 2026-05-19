# Command Center CSS Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix typography, density, and panel structure in the Command Center cockpit-grid layout via CSS-only changes to `frontend/src/index.css`.

**Architecture:** Seven targeted edits to existing CSS rules added by a prior session. No JSX changes. No new rules except one override for `h3` size inside cockpit panels.

**Tech Stack:** CSS (plain), Vite (build), TypeScript/React frontend.

---

## Files

- Modify: `frontend/src/index.css` (lines 2402, 2487, 2491, 2492–2496 area, 2527, 2535, 2547)

---

### Task 1: Panel breathing — padding, heading margin, h3 dominance

These three changes work together: if the panels are tighter and headings are small, the content feels like a wall of equal-weight text. Fixing all three at once lets you judge the balance in one build.

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Increase cockpit panel padding**

  In `frontend/src/index.css` at line 2485–2488:

  ```css
  /* before */
  .command-cockpit-panel {
    min-width: 0;
    padding: 0.8rem;
  }

  /* after */
  .command-cockpit-panel {
    min-width: 0;
    padding: 1rem 1.15rem;
  }
  ```

- [ ] **Step 2: Increase panel heading bottom margin**

  At line 2490–2492:

  ```css
  /* before */
  .command-cockpit-panel .command-panel-heading {
    margin-bottom: 0.55rem;
  }

  /* after */
  .command-cockpit-panel .command-panel-heading {
    margin-bottom: 0.9rem;
  }
  ```

- [ ] **Step 3: Add h3 font-size override for cockpit panels**

  The base `.command-panel-heading h3` rule (elsewhere in the file) sets `font-size: 1.18rem`. Cockpit panel headings (`AGGRESSIVE`, `ADJUSTMENT ADVISED`, `READY TO DECIDE`) are the dominant content of each panel and need to be larger. Insert this rule directly after the `.command-cockpit-panel .command-current-plan` block (after line 2496):

  ```css
  .command-cockpit-panel h3 {
    font-size: 1.55rem;
  }
  ```

- [ ] **Step 4: Build and verify**

  Run from `frontend/`:
  ```
  npm run build
  ```
  Expected: build completes with no errors.

  Visual check: in the running dev server, the three panel titles (`AGGRESSIVE` / `ADJUSTMENT ADVISED` / `READY TO DECIDE`) should be noticeably larger than the kicker text above them and the body copy below.

- [ ] **Step 5: Commit**

  ```
  git add frontend/src/index.css
  git commit -m "fix: cockpit panel padding, heading margin, h3 font-size"
  ```

---

### Task 2: Plan editor internal layout — approach buttons and column gap

The Tactical Approach (2×2 buttons) and Tactical Profile (bar meters) columns share a `.command-plan-grid` with no gap, making them flush. The approach buttons are also too short to feel like real selectable tiles.

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add gap to the plan editor two-column grid**

  At line 2526–2528:

  ```css
  /* before */
  .command-plan-grid {
    grid-template-columns: minmax(12rem, 0.95fr) minmax(13rem, 1.05fr);
  }

  /* after */
  .command-plan-grid {
    grid-template-columns: minmax(12rem, 0.95fr) minmax(13rem, 1.05fr);
    gap: 1.1rem;
  }
  ```

- [ ] **Step 2: Increase approach button height**

  At line 2534–2536:

  ```css
  /* before */
  .command-approach-grid button {
    min-height: 2.2rem;
  }

  /* after */
  .command-approach-grid button {
    min-height: 3rem;
  }
  ```

- [ ] **Step 3: Increase tactical profile bar stack gap**

  At line 2545–2548:

  ```css
  /* before */
  .command-meter-stack {
    display: grid;
    gap: 0.45rem;
  }

  /* after */
  .command-meter-stack {
    display: grid;
    gap: 0.7rem;
  }
  ```

- [ ] **Step 4: Build and verify**

  Run from `frontend/`:
  ```
  npm run build
  ```
  Expected: build completes with no errors.

  Visual check: the Tactical Approach button grid and the Tactical Profile bar stack should have clear column separation. The four approach buttons (`BALANCED`, `AGGRESSIVE`, `CONTROL`, `DEFENSIVE`) should feel like selectable tiles, not links.

- [ ] **Step 5: Commit**

  ```
  git add frontend/src/index.css
  git commit -m "fix: plan grid gap, approach button height, meter stack gap"
  ```

---

### Task 3: Secondary rail minimum height

The `.command-dashboard` grid row 3 (the checklist/standings/league tab section) has `minmax(5.5rem, 7rem)` — a maximum of 112px. The checklist content overflows without being visible. Raise the min and max so the tab area actually shows its contents.

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Update secondary rail row height**

  At line 2402:

  ```css
  /* before */
  grid-template-rows: auto minmax(0, 1fr) minmax(5.5rem, 7rem);

  /* after */
  grid-template-rows: auto minmax(0, 1fr) minmax(9rem, 12rem);
  ```

- [ ] **Step 2: Build and verify**

  Run from `frontend/`:
  ```
  npm run build
  ```
  Expected: build completes with no errors.

  Visual check: the Checklist tab at the bottom of the Command Center should show its rows (tactics dept. items, warnings, recommendations). The tab buttons themselves should not be the only visible content.

- [ ] **Step 3: Commit**

  ```
  git add frontend/src/index.css
  git commit -m "fix: secondary rail min-height so checklist content is visible"
  ```

---

## Done

All three tasks complete. Run the full frontend build one final time and do a quick sweep:

- [ ] `npm run build` from `frontend/` — no errors
- [ ] Panel headings (`AGGRESSIVE` etc.) are the dominant text in each panel
- [ ] Approach buttons are tile-height, not link-height
- [ ] Tactical Approach and Tactical Profile columns have clear separation
- [ ] Checklist tab shows content, not just the tab bar
- [ ] No visual regressions on the aftermath screen (navigate to any completed week)
