# V15 Phase 4b — App Shell (Nav hamburger + Settings hide): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the permanently-disabled Settings nav item (hide it until it has real purpose) and add a collapsible hamburger nav so players can reclaim horizontal space on narrow layouts. Both changes are global shell chrome only — no screen content, no engine changes, no new dependencies.

**Architecture:** Two isolated changes to `frontend/src/App.tsx` + one e2e spec. Task 1 (Settings hide) is a one-liner behind a compile-time flag; Task 2 (hamburger) adds a single boolean state and a `<button>` with full ARIA. Both changes are presentation-only; the engine-health probe is unaffected.

**Tech Stack:** React 19 + TypeScript ~6 + Vite 8, inline `style={{}}` + `dm-*` classNames (no Tailwind utilities), ESLint, root Playwright (`npm run e2e`). **No frontend unit-test runner exists and none may be added** (no new deps) — verification is `npm run build` (tsc gate) + `npm run lint` + `npm run e2e`.

> **Owner decision #1 (planning-report.md §6):** Settings: hide until purposeful. The disabled item is replaced with a conditional render behind `SHOW_SETTINGS_NAV`. Default is `false`. Flipping the constant to `true` re-enables the item with zero further change.

> **Pre-flight:**
> - Branch off `main`: `git checkout -b feat/v15-phase4b-app-shell`. This phase touches only `frontend/src/App.tsx` (+ a new e2e spec). No collision with any other Phase 2–4 plan (each owns a distinct screen/component).
> - Verify green baseline: from `frontend/`, `npm run build && npm run lint` must pass before starting. From repo root, `npm run e2e` must be green.
> - Confirm the exact Settings nav block before editing: lines 158–167 of `frontend/src/App.tsx` (the `<button disabled title="Settings are coming soon">` inside `.left-nav-footer`).

---

## File Structure

| File | Responsibility |
|---|---|
| `frontend/src/App.tsx` | Hide Settings nav item + add hamburger toggle state + render collapsible `<aside>` |
| `tests/e2e/v15-app-shell.spec.ts` | Playwright: nav collapses/expands on hamburger click; Settings disabled item absent |

---

## Task 1: Hide the Settings nav item behind a re-enable flag

**Context:** `App.tsx` lines 158–167 render a `<button disabled title="Settings are coming soon">` in `.left-nav-footer`. Owner decision #1 (planning-report.md §6): hide this until Settings has real purpose, with a clean conditional so it can be trivially re-enabled. The implementation is a module-level constant `SHOW_SETTINGS_NAV = false`; the JSX renders the button only when `true`. No runtime logic, no user-visible setting.

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Read the exact lines to edit**

Open `frontend/src/App.tsx` and locate the Settings button block (around lines 158–167). Confirm the exact surrounding JSX:

```tsx
        <div className="left-nav-footer">
          <button
            className="nav-item"
            disabled
            title="Settings are coming soon"
            style={{ opacity: 0.35, cursor: 'not-allowed' }}
            onClick={() => {}}
          >
            <span className="dot" />
            Settings
          </button>
          {menuButton}
        </div>
```

If the exact text differs, adjust the edit below to match current source precisely.

- [ ] **Step 2: Add the re-enable flag constant near the top of the file (after the imports, before `App()`)**

Insert this constant directly after the `const tabKickers` block (around line 32), before the `tabFromUrl` function:

```tsx
// Owner decision (planning-report.md §6 #1): hide Settings until it has real purpose.
// Flip to `true` to re-enable the nav item with zero further changes.
const SHOW_SETTINGS_NAV = false;
```

- [ ] **Step 3: Replace the Settings button block with a conditional render**

In `frontend/src/App.tsx`, in the `.left-nav-footer` div, replace the unconditional disabled Settings button with:

```tsx
        <div className="left-nav-footer">
          {SHOW_SETTINGS_NAV && (
            <button
              className="nav-item"
              disabled
              title="Settings are coming soon"
              style={{ opacity: 0.35, cursor: 'not-allowed' }}
              onClick={() => {}}
            >
              <span className="dot" />
              Settings
            </button>
          )}
          {menuButton}
        </div>
```

- [ ] **Step 4: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. TypeScript must not warn on `SHOW_SETTINGS_NAV` being always `false` (it is a module constant, not unreachable dead code — TSC does not error on `false && <jsx>`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "fix(v15-p4b): hide Settings nav until purposeful (owner decision #1)

Replace permanently-greyed disabled item with a conditional behind
SHOW_SETTINGS_NAV = false; flip to true to re-enable with no further
change. Resolves the 'Settings greyed out forever' legibility note
from planning-report.md Appendix A.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Collapsible hamburger nav

**Context:** The `.left-nav` rail is always fully expanded. On 390×844 (iPhone SE / standard mobile) this consumes ~180 px of the 390 px viewport width — a meaningful penalty for screen content. A hamburger toggle that collapses the rail — hiding the nav and showing only the hamburger — lets players reclaim that space. The implementation:

- A single `navCollapsed` boolean state added to `App()`.
- A `<button>` with `aria-expanded={!navCollapsed}` + `aria-controls="primary-nav"` rendered inside the `<aside>` header area (above the logo).
- When collapsed: the `<aside>` renders at narrow width (3 rem) showing only the hamburger icon; the `<nav id="primary-nav">` and `.left-nav-logo` get `display: none` so they are removed from the accessibility tree entirely — `aria-expanded="false"` is truthful to assistive technology and no hidden item can be reached by keyboard or screen-reader virtual cursor.
- When expanded: full-width rail restored, nav and logo visible and in the accessibility tree.
- The hamburger button itself is always visible and always keyboard-focusable.
- No CSS framework, no new file — inline styles only, consistent with the existing `dm-*` convention.
- No `localStorage` persistence (the state resets per page load — YAGNI; persisting is a future opt-in, not needed now).

**Mobile safety:** At 390 px wide: collapsed rail = 3 rem (48 px), workspace gets 342 px — no horizontal overflow. At 768 px wide: collapsed rail = 3 rem, or expanded at full width. Both states checked in the Playwright spec at 390×844.

**Accessibility contract:**
- The hamburger button has `aria-expanded` (boolean, not string) that reflects the current visual state.
- `aria-controls` points to the `<nav>`'s `id="primary-nav"`.
- `aria-label` is "Toggle navigation" (a stable string screen readers speak).
- When collapsed, the `<nav>` has `display: none` — it is fully absent from the accessibility tree. `tabIndex` gating is belt-and-suspenders but is NOT the primary AT safety mechanism; `display: none` is.
- When expanded, the `<nav>` has its normal display; all items are in the tree and keyboard-reachable.
- The hamburger button receives focus after toggle (managed via `useRef` + `.focus()` in the click handler — keeps keyboard users oriented).

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add `navCollapsed` state and a ref for focus management**

In `App()`, after the existing state declarations (around line 50), add:

```tsx
  const [navCollapsed, setNavCollapsed] = useState(false);
  const hamburgerRef = useRef<HTMLButtonElement>(null);
```

Add `useRef` to the import at line 1:

```tsx
import { useEffect, useRef, useState } from 'react';
```

- [ ] **Step 2: Add the `id` and collapsed style to the `<nav>` element**

In the `.left-nav-items` nav element (line 128), add `id="primary-nav"` and the `display:none` collapsed guard:

```tsx
          <nav id="primary-nav" className="left-nav-items" aria-label="Primary" style={{ display: navCollapsed ? 'none' : undefined }}>
```

`display: none` removes the nav from the accessibility tree when collapsed — screen readers cannot reach items and `aria-expanded="false"` is truthful. The `id="primary-nav"` matches the hamburger's `aria-controls`.

- [ ] **Step 3: Add `tabIndex` gating to nav item buttons when collapsed (belt-and-suspenders)**

This is belt-and-suspenders alongside `display:none` on the `<nav>` (Step 4): `display:none` is the primary AT safety mechanism; `tabIndex=-1` ensures no edge-case where the nav becomes visible but focus is still trapped during the transition.

In the `tabs.map(tab => ...)` block, the rendered `<button>` (line 137), add `tabIndex={navCollapsed ? -1 : 0}`:

```tsx
              <button
                key={tab.id}
                className={`nav-item ${isActive ? 'active' : ''}`}
                aria-label={tab.label}
                aria-disabled={!isAvailable}
                tabIndex={navCollapsed ? -1 : 0}
                title={isAvailable ? tab.label : `${tab.label} — locked during offseason`}
                onClick={() => {
                  if (isAvailable) {
                    setCommandReplay(null);
                    setActiveTab(tab.id);
                  }
                }}
                style={{ opacity: isAvailable ? 1 : 0.35, cursor: isAvailable ? 'pointer' : 'not-allowed', pointerEvents: 'auto' }}
              >
                <span className="dot" />
                {tab.label}
              </button>
```

**`menuButton` — no relocation needed.** `navCollapsed` is a `useState` hook declared at ~line 50 inside `App()`, so it is already in scope at line 96 where `menuButton` is defined. Simply add `tabIndex={navCollapsed ? -1 : 0}` to the existing `menuButton` JSX in place:

```tsx
  const menuButton = (
    <button
      className="nav-item"
      aria-label="Back to save menu"
      tabIndex={navCollapsed ? -1 : 0}
      onClick={() => {
        careerApi.unloadSave()
          .finally(() => window.location.reload());
      }}
      title="Back to Save Menu"
    >
      <span className="dot" />
      Menu
    </button>
  );
```

Do NOT move `menuButton` inside the `return` — `const` declarations are not valid inside JSX markup, and there is no scope reason to move it.

- [ ] **Step 4: Add the hamburger button at the top of the `<aside>`, above the logo; apply `display:none` to nav and logo when collapsed**

In the `<aside className="left-nav">` block, insert the hamburger button as the first child (before the `.left-nav-logo` div). Apply `display: none` to the `<nav>` and `.left-nav-logo` when collapsed — this removes them from the accessibility tree, making `aria-expanded="false"` truthful to screen readers and preventing virtual-cursor traversal of hidden items.

```tsx
      <aside
        className="left-nav"
        style={{ width: navCollapsed ? '3rem' : undefined, overflow: navCollapsed ? 'hidden' : undefined, transition: 'width 0.18s ease' }}
      >
        {/* Hamburger toggle — always visible and keyboard-focusable */}
        <button
          ref={hamburgerRef}
          type="button"
          aria-expanded={!navCollapsed}
          aria-controls="primary-nav"
          aria-label="Toggle navigation"
          onClick={() => {
            setNavCollapsed((v) => !v);
            // Return focus to the hamburger after toggle so keyboard users stay oriented.
            requestAnimationFrame(() => hamburgerRef.current?.focus());
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '2.25rem',
            height: '2.25rem',
            background: 'none',
            border: '1px solid #1e293b',
            borderRadius: '4px',
            color: '#94a3b8',
            cursor: 'pointer',
            margin: '0.5rem auto 0',
            flexShrink: 0,
          }}
          title={navCollapsed ? 'Expand navigation' : 'Collapse navigation'}
        >
          {/* Three-line hamburger icon drawn with box-shadow — no SVG dep */}
          <span
            aria-hidden="true"
            style={{
              display: 'block',
              width: '1rem',
              height: '2px',
              background: '#94a3b8',
              boxShadow: '0 4px 0 #94a3b8, 0 -4px 0 #94a3b8',
              borderRadius: '1px',
            }}
          />
        </button>
        <div
          className="left-nav-logo"
          style={{ display: navCollapsed ? 'none' : undefined }}
        >
          <p className="dm-kicker" style={{ fontSize: '0.62rem' }}>Dodgeball Manager</p>
          <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.125rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: '2px 0 0' }}>{seasonYear ?? ''}</p>
        </div>
        <nav
          id="primary-nav"
          className="left-nav-items"
          aria-label="Primary"
          style={{ display: navCollapsed ? 'none' : undefined }}
        >
          {/* ... existing tabs.map(...) content unchanged ... */}
        </nav>
```

> The `<nav>` previously had no inline `style` prop. Add `style={{ display: navCollapsed ? 'none' : undefined }}` to it. `display: none` removes the element from the accessibility tree entirely — screen readers cannot reach hidden items, and `aria-expanded="false"` on the hamburger is truthful. The `tabIndex` gating in Step 3 is belt-and-suspenders for transition-timing edge cases.

> The `<aside>` itself gains inline `width` and `overflow` overrides when collapsed so no CSS file edit is needed. The existing `.left-nav` CSS class continues to provide the base styles (padding, background, flex layout, etc.) — do not remove it.

> **CSS `!important` caveat:** If the existing `.left-nav` CSS sets a fixed `width` via `!important`, the inline style cannot override it. Check with `git grep -n "left-nav" -- frontend/src` before starting. If `!important` is present, add a `data-collapsed={navCollapsed}` attribute to the `<aside>` and a single CSS rule `[data-collapsed="true"].left-nav { width: 3rem !important; overflow: hidden; }` to `index.css` instead of the inline width override.

- [ ] **Step 5: Hide the `.left-nav-footer` items when collapsed**

When the nav is collapsed the footer items (Menu button, and Settings if ever re-enabled) must not be visible or keyboard-reachable. Apply `display: none` to the footer div's contents using a conditional — the same `display:none` pattern used for the nav and logo, consistent and AT-safe:

```tsx
        <div className="left-nav-footer">
          {!navCollapsed && SHOW_SETTINGS_NAV && (
            <button
              className="nav-item"
              disabled
              title="Settings are coming soon"
              style={{ opacity: 0.35, cursor: 'not-allowed' }}
              onClick={() => {}}
            >
              <span className="dot" />
              Settings
            </button>
          )}
          {!navCollapsed && menuButton}
        </div>
```

> `{!navCollapsed && menuButton}` unmounts the Menu button when collapsed, keeping it out of the accessibility tree and tab order — consistent with the `display:none` treatment on the nav. `menuButton` remains at its current location (lines 96–109), unchanged except for the `tabIndex` prop added in Step 3.

- [ ] **Step 6: Full compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. Confirm no TypeScript errors on `useRef`, `navCollapsed`, or the `aria-expanded` boolean prop.

If `useRef` is new to this import line, ensure the import at line 1 is:

```tsx
import { useEffect, useRef, useState } from 'react';
```

- [ ] **Step 7: Mobile overflow check (manual, 390×844)**

Using browser DevTools or Playwright (below), confirm at 390 px wide:
- Collapsed: `<aside>` is ≤ 48 px wide; workspace fills remaining ~342 px; no horizontal scrollbar.
- Expanded: `<aside>` restores to its full width; no overflow.
- Hamburger is visible and clickable in both states.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(v15-p4b): collapsible hamburger nav with full ARIA

aria-expanded/aria-controls on the toggle button; tabIndex=-1 gates
nav items when collapsed so keyboard users cannot tab into hidden items;
focus returns to hamburger after toggle; width transition 0.18s ease;
mobile-safe at 390x844 (collapsed aside = 3rem, no overflow).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Playwright e2e spec

**Context:** The spec must assert (1) the hamburger button collapses and expands the nav, (2) the Settings disabled item is absent from the DOM, and (3) no horizontal overflow at 390×844. The spec uses a fresh save (same pattern as `v14-legibility.spec.ts`) to ensure a real game shell is rendered, not the save menu.

**Files:**
- Create: `tests/e2e/v15-app-shell.spec.ts`

- [ ] **Step 1: Create the spec**

```ts
import { expect, test } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

test.describe('V15 Phase 4b — App shell: nav hamburger + Settings hidden', () => {
  test.beforeEach(async ({ request }) => {
    // Create a throwaway save so the game shell renders (not the save menu).
    const saveName = `e2e-v15-shell-${Date.now()}`;
    const res = await request.post(`${baseUrl}/api/saves/new`, {
      data: { name: saveName, club_id: 'aurora' },
    });
    expect(res.ok()).toBeTruthy();
  });

  test('Settings disabled item is not rendered', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=command`);
    // Wait for the game shell to load (not the save menu).
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    // The disabled Settings button must not appear in the DOM at all.
    // It should not be found by its accessible name or by its known text.
    await expect(page.getByRole('button', { name: /Settings/i })).toHaveCount(0);

    // The "Settings are coming soon" title must also be absent.
    await expect(page.locator('[title="Settings are coming soon"]')).toHaveCount(0);
  });

  test('hamburger toggles nav collapsed/expanded — keyboard operable', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=command`);
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    const hamburger = page.getByRole('button', { name: /Toggle navigation/i });
    await expect(hamburger).toBeVisible();

    // Initial state: nav is expanded (aria-expanded = true).
    await expect(hamburger).toHaveAttribute('aria-expanded', 'true');
    await expect(hamburger).toHaveAttribute('aria-controls', 'primary-nav');

    // Click to collapse.
    await hamburger.click();
    await expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    // The <nav> has display:none when collapsed (primary AT safety).
    // tabIndex=-1 on items is belt-and-suspenders.
    // toHaveAttribute reads the DOM attribute regardless of display:none,
    // so this assertion works even though the nav is visually hidden.
    const firstNavItem = page.locator('#primary-nav .nav-item').first();
    await expect(firstNavItem).toHaveAttribute('tabindex', '-1');

    // Click to expand.
    await hamburger.click();
    await expect(hamburger).toHaveAttribute('aria-expanded', 'true');

    // Nav items are keyboard-reachable again (tabIndex restored to 0).
    await expect(firstNavItem).toHaveAttribute('tabindex', '0');
  });

  test('hamburger is operable via keyboard (Enter key)', async ({ page }) => {
    await page.goto(`${baseUrl}/?tab=command`);
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    const hamburger = page.getByRole('button', { name: /Toggle navigation/i });

    // Focus the hamburger and press Enter.
    await hamburger.focus();
    await page.keyboard.press('Enter');
    await expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    // Press Enter again to expand.
    await page.keyboard.press('Enter');
    await expect(hamburger).toHaveAttribute('aria-expanded', 'true');
  });

  test('no horizontal overflow at 390x844 in collapsed state', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${baseUrl}/?tab=command`);
    await expect(page.locator('.left-nav')).toBeVisible({ timeout: 10000 });

    // Collapse the nav.
    const hamburger = page.getByRole('button', { name: /Toggle navigation/i });
    await hamburger.click();
    await expect(hamburger).toHaveAttribute('aria-expanded', 'false');

    // Check for horizontal overflow: scrollWidth must not exceed clientWidth.
    const overflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(overflow).toBe(false);

    // And the workspace content area must still be visible.
    await expect(page.locator('.workspace')).toBeVisible();
  });
});
```

- [ ] **Step 2: Run the e2e spec**

Run (from repo root): `npm run e2e -- v15-app-shell`
Expected: all 4 tests PASS.

If the `tabindex` assertion fails because `App.tsx` doesn't set an explicit `tabIndex={0}` on expanded nav items (only `-1` on collapsed), update the expanded check to:

```ts
    // When expanded, tabindex attribute is absent (default 0) or explicitly 0.
    const tabIdx = await firstNavItem.getAttribute('tabindex');
    expect(tabIdx === null || tabIdx === '0').toBe(true);
```

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/v15-app-shell.spec.ts
git commit -m "test(v15-p4b): Playwright spec for nav hamburger + Settings hidden

Asserts: Settings disabled item absent from DOM; hamburger collapses/
expands with correct aria-expanded; keyboard Enter operable; no
horizontal overflow at 390x844 in collapsed state.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 4b Exit Gates

Run all before declaring Phase 4b done:

- [ ] From `frontend/`: `npm run build` (tsc gate — no TypeScript errors on `useRef`, `navCollapsed`, or `aria-expanded`) and `npm run lint` — clean.
- [ ] From repo root: `npm run e2e -- v15-app-shell` — all 4 tests green.
- [ ] From repo root: `npm run e2e` (full suite) — zero regressions in other specs.
- [ ] Manual check at 390×844: collapsed rail is ≤ 48 px wide, no horizontal overflow, hamburger visible, "Settings" text absent, nav items unreachable by Tab when collapsed.
- [ ] `SHOW_SETTINGS_NAV` constant is `false` in committed source; a one-line flip to `true` makes the item render again (verify by temporarily setting `true`, building, reverting).
- [ ] Engine-health probe is not required this phase (frontend-only, zero engine contact), but `python -m pytest -q` must remain green if run.
- [ ] No `playtest_output/*.png` or local `*.db` files committed.

---

## Implementation Notes for the Executor

**Reading current source before editing:** Always read the current `frontend/src/App.tsx` lines before applying edits — do not apply diffs blindly. The line numbers in this plan match the current file at the time of writing; an earlier phase may have shifted them slightly.

**`menuButton` stays in place:** `navCollapsed` is a `useState` hook at ~line 50 inside `App()`, so it is already in scope at line 96 where `menuButton` is defined. No relocation is needed — do not move `menuButton` inside the `return` block. A `const` declaration is not valid inside JSX markup.

**`display:none` is the AT safety mechanism:** `display:none` on the `<nav>` removes it from the accessibility tree. `tabIndex=-1` on individual items is belt-and-suspenders for transition-timing edge cases only. Do not rely on `tabIndex` alone for screen-reader safety — it only blocks tab order, not virtual-cursor reading.

**CSS class `.left-nav`:** This plan does not modify any CSS/SCSS file. All collapsed-state overrides are applied via inline `style` props on the `<aside>`. If the existing `.left-nav` CSS sets a fixed `width` via `!important`, the inline style cannot override it — in that case, add a `data-collapsed={navCollapsed}` attribute to the `<aside>` and add a single CSS rule `[data-collapsed="true"].left-nav { width: 3rem !important; overflow: hidden; }` to `index.css` (or the nearest relevant CSS file). Check the existing `.left-nav` rule with `git grep -n "left-nav" -- frontend/src` before starting.

**`aria-expanded` type:** React expects `aria-expanded` as a boolean (`true`/`false`), not the string `"true"`/`"false"`. The Playwright assertion uses `.toHaveAttribute('aria-expanded', 'true')` which checks the rendered HTML attribute string — React serializes the boolean correctly.

**Scope guard:** This phase is nav/shell chrome ONLY. If during implementation you notice a Standings/History consolidation opportunity (League Wire ticker, Trajectory Log removal, tabs) — that belongs to Phase 2d / Phase 4a. Do not implement it here. Leave a `// TODO(4a): ...` comment and move on.

---

## Out of Scope for Phase 4b

- Standings/History consolidation (League Wire ticker, Trajectory Log, Banner/Alumni tabs) — Phase 2d / Phase 4a.
- Settings page content / Dynasty Office department subpages — deferred spec (planning-report.md §5).
- Program Identity discoverability copy — Phase 4a.
- Any engine/RNG/scoring edit.
- Any new npm dependency.
