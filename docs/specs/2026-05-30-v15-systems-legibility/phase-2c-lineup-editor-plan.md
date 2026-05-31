# V15 Phase 2c — Lineup Editor: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Lineup Editor self-evident — no prose reading required. Three concrete outcomes: (1) the active/bench split is visually unambiguous at a glance; (2) ordering controls carry in-context cues about *what order affects*; (3) "Reset to Auto" is restyled as an optimize-to-auto helper with an unambiguous action class, not a destructive reset button.

**Architecture:** Presentation-only edit to `frontend/src/components/lineup/LineupEditor.tsx`. Toolkit imports (`TermTip`) come from `frontend/src/legibility/` (Phase 1 deliverable). One new term key added to `terms.ts` (append-only). One new Playwright spec asserting the affordances are present and keyboard-operable. No engine/resolver/API change — the `commandApi.saveLineup` / `commandApi.clearLineup` calls and the `LineupResolver` canonical fielded-six are untouched.

**Tech Stack:** React 19 + TypeScript ~6, Vite 8 (`tsc -b && vite build`), ESLint, root Playwright (`npm run e2e`). No new npm dependencies.

> **Pre-flight:**
> - Phase 1 toolkit must be merged and available at `frontend/src/legibility/` before this phase starts (see [implementation-index.md](implementation-index.md)).
> - Branch off `main`: `git checkout -b feat/v15-phase2c-lineup-editor`. Only `frontend/src/components/lineup/LineupEditor.tsx`, `frontend/src/legibility/terms.ts`, and one new e2e spec are touched — zero collision with other Phase 2 slices.
> - Verify green baseline: from `frontend/`, `npm run build && npm run lint` must pass before starting.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `frontend/src/legibility/terms.ts` | Add `lineup.slot_order` term (append-only) | 1 |
| `frontend/src/components/lineup/LineupEditor.tsx` | Active/bench visual split, order-context cue, Reset-to-Auto restyle | 2, 3, 4 |
| `tests/e2e/v15-lineup-editor.spec.ts` | Playwright assertions for affordances + keyboard operability | 5 |

---

## Task 1: Seed the lineup term in `terms.ts`

**Context:** `TermTip` requires its `term` prop to match a key in `TERMS`. The Phase 1 registry pre-seeded the known V15 terms; `lineup.slot_order` was not included because it is lineup-screen-specific. Add it now — this is an append-only change to `terms.ts`. The `as const satisfies` gate will fail the build if the key is referenced before it is added.

**Files:**
- Modify: `frontend/src/legibility/terms.ts`

- [ ] **Step 1: Append `lineup.slot_order` to the `TERMS` object**

Open `frontend/src/legibility/terms.ts`. Inside the `TERMS` object, after the last existing entry (before the closing `} as const satisfies ...`), append:

```ts
  // --- Lineup (mechanical: slot order drives role-label assignment) ---
  'lineup.slot_order': {
    label: 'Slot Order',
    plain: 'The sequence of your six starters from Captain (slot 1) through Utility (slot 6).',
    why: 'Each slot carries a role label that summarizes the position. Reorder to put the right archetype in the right slot — swap a bench player in by clicking a slot, then a bench card.',
    kind: 'mechanical',
  },
```

> Do not change any existing key. The `TERMS` map uses `as const satisfies Record<string, TermDef>` — the new key becomes part of the `TermId` closed union automatically, and any `<TermTip term="lineup.slot_order">` reference is compile-verified.

- [ ] **Step 2: Compile gate**

Run (from `frontend/`): `npm run build`
Expected: PASS. The new key joins the closed union; no other file references it yet.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/legibility/terms.ts
git commit -m "feat(v15-p2c): seed lineup.slot_order term for TermTip compile gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Make the active/bench split visually unambiguous

**Context:** The current editor places "Starters (6)" and "Bench (N)" side-by-side in a 2-column grid. Both columns use identical card styles (`background: '#0f172a'`, `border: '1px solid #1e293b'`). At mobile widths (390px) the grid collapses to a single column but the section headers are styled identically with `dm-kicker` only — there is no visual cue that distinguishes a fielded player from a sitter. The fix adds:
1. A section header bar for "Active — Fielded Six" that uses a distinct accent border and a count badge so the six-cap is visible without counting.
2. A section header bar for "Bench" that uses muted styling and a clear label.
3. A thin left-border accent on each active slot card (`#22d3ee`, the dm-* active/selected color) so the column carries its own color signal regardless of selection state.

**Files:**
- Modify: `frontend/src/components/lineup/LineupEditor.tsx`

- [ ] **Step 1: Read the current Starters section header to confirm exact surrounding markup**

Read lines 231–272 of `frontend/src/components/lineup/LineupEditor.tsx` (the outer `<div>`, the `dm-kicker` header, and the first starter card). Confirm:
- The outer `<div>` wrapping the starters column starts at line 231.
- The header is `<div className="dm-kicker" style={{ marginBottom: '0.5rem' }}>Starters ({STARTERS_COUNT})</div>`.
- Each starter card is a `<button>` with `background: isSelected ? '#0f4c5c' : '#0f172a'` and a `border` that switches between error/selected/default.

- [ ] **Step 2: Replace the Starters section header with an accented, labeled header**

In `frontend/src/components/lineup/LineupEditor.tsx`, replace:

```tsx
            <div className="dm-kicker" style={{ marginBottom: '0.5rem' }}>
              Starters ({STARTERS_COUNT})
            </div>
```

with:

```tsx
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.5rem',
                paddingBottom: '0.35rem',
                borderBottom: '2px solid #22d3ee',
              }}
            >
              <span className="dm-kicker" style={{ color: '#22d3ee' }}>Active</span>
              <span
                style={{
                  background: '#22d3ee',
                  color: '#0b1220',
                  borderRadius: '3px',
                  fontWeight: 800,
                  fontSize: '0.6rem',
                  padding: '0.05rem 0.35rem',
                  letterSpacing: '0.04em',
                }}
                aria-label="Fielded six — exactly 6 starters"
              >
                {STARTERS_COUNT} fielded
              </span>
            </div>
```

- [ ] **Step 3: Add a left-border accent to each active slot card**

In the same file, inside the `.map((id, idx) => { ... })` for the starters list, find the `<button>` inline style block. It currently sets `border` via:

```tsx
                      border: hasError
                        ? '1px solid #ef4444'
                        : isSelected
                        ? '1px solid #22d3ee'
                        : '1px solid #1e293b',
```

Replace the entire `border` property **and add `borderLeft`** so active cards always carry a cyan left rail even when not selected:

```tsx
                      border: hasError
                        ? '1px solid #ef4444'
                        : isSelected
                        ? '1px solid #22d3ee'
                        : '1px solid #1e293b',
                      borderLeft: hasError
                        ? '3px solid #ef4444'
                        : isSelected
                        ? '3px solid #22d3ee'
                        : '3px solid rgba(34,211,238,0.4)',
```

> This keeps `border` (which sets all four sides) and then `borderLeft` overrides only the left. In CSS, the more-specific shorthand wins; in inline styles React merges left-to-right so `borderLeft` wins over `border`'s left component only when listed after. Verify this renders correctly by running the app after Task 4 and inspecting the left border at 390px.

- [ ] **Step 4: Replace the Bench section header with a clearly muted, labeled header**

Replace:

```tsx
            <div className="dm-kicker" style={{ marginBottom: '0.5rem' }}>
              Bench ({benchPlayers.length})
            </div>
```

with:

```tsx
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                marginBottom: '0.5rem',
                paddingBottom: '0.35rem',
                borderBottom: '1px solid #1e293b',
              }}
            >
              <span className="dm-kicker" style={{ color: '#64748b' }}>Bench</span>
              <span
                style={{
                  background: '#1e293b',
                  color: '#94a3b8',
                  borderRadius: '3px',
                  fontWeight: 700,
                  fontSize: '0.6rem',
                  padding: '0.05rem 0.35rem',
                  letterSpacing: '0.04em',
                }}
                aria-label={`${benchPlayers.length} bench players — not fielded`}
              >
                {benchPlayers.length} not fielded
              </span>
            </div>
```

- [ ] **Step 5: Add `aria-label` attributes to the two column wrappers for screen-reader region labeling**

The outer `<div>` for the starters column (line 231, `<div>`) and bench column (line 275, `<div>`) currently have no `role` or `aria-label`. Add `role="group"` and `aria-label` to each:

For the starters column's outer wrapper div (the one containing the header and the `flexDirection: 'column'` list):

```tsx
          <div role="group" aria-label="Active starters — fielded six">
```

For the bench column's outer wrapper div:

```tsx
          <div role="group" aria-label="Bench players — not fielded">
```

- [ ] **Step 6: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS — no new type errors; the inline style `borderLeft` override is valid React CSS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/lineup/LineupEditor.tsx
git commit -m "feat(v15-p2c): active/bench split is visually unambiguous

Accented cyan header + per-card left-border rail marks the fielded six;
muted bench header labels non-fielded players; aria group labels added
for keyboard/screen-reader navigation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Add ordering-context cue with `TermTip`

**Context:** The current subtitle ("Click a starter slot, then click a bench player to swap.") explains the interaction mechanic but not *why order matters*. A player who doesn't know what "Captain" or "Utility" means cannot make a meaningful decision. The fix: wrap the interaction hint in a one-line in-context caption that includes a `TermTip` on "Slot Order" so the player can discover what ordering controls, and adds a short explanatory note under the starters header where it is maximally visible.

**Files:**
- Modify: `frontend/src/components/lineup/LineupEditor.tsx`
- Ensure: `frontend/src/legibility/TermTip.tsx` and `frontend/src/legibility/terms.ts` are imported

- [ ] **Step 1: Add the `TermTip` import**

At the top of `frontend/src/components/lineup/LineupEditor.tsx`, after the existing imports, add:

```tsx
import { TermTip } from '../../legibility';
```

Verify that `frontend/src/legibility/index.ts` re-exports `TermTip` (it does per the Phase 1 barrel). If for any reason the path differs, adjust to `'../../legibility/TermTip'`.

- [ ] **Step 2: Replace the subtitle text with a `TermTip`-wrapped ordering cue**

Locate the existing subtitle div (just below the `<h2>Manual Lineup Editor</h2>`):

```tsx
            <div style={{ marginTop: '0.25rem', color: '#94a3b8', fontSize: '0.875rem' }}>
              Click a starter slot, then click a bench player to swap.
            </div>
```

Replace with:

```tsx
            <div style={{ marginTop: '0.25rem', color: '#94a3b8', fontSize: '0.8rem', lineHeight: 1.5 }}>
              Click a starter slot, then a bench player to swap.{' '}
              <TermTip term="lineup.slot_order">Slot order</TermTip> sets role labels (Captain → Utility).
            </div>
```

This gives the player one tap/hover/focus to learn what ordering does, without requiring them to read prose before interacting.

- [ ] **Step 3: Add a compact role-order legend row beneath the active header**

After the active-section header div (the `<div style={{ borderBottom: '2px solid #22d3ee' ... }}>` from Task 2), add a single-line role legend so the player sees the slot-label sequence before touching any card:

```tsx
            <div
              aria-label="Slot role order: Captain, Striker, Anchor, Runner, Rookie, Utility"
              style={{
                display: 'flex',
                gap: '0.3rem',
                flexWrap: 'wrap',
                marginBottom: '0.5rem',
              }}
            >
              {ROLE_LABELS.map((label, i) => (
                <span
                  key={label}
                  style={{
                    fontSize: '0.55rem',
                    fontWeight: 700,
                    letterSpacing: '0.04em',
                    color: i === 0 ? '#22d3ee' : '#64748b',
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '3px',
                    padding: '0.05rem 0.3rem',
                    textTransform: 'uppercase',
                  }}
                >
                  {i + 1}. {label}
                </span>
              ))}
            </div>
```

The Captain slot (index 0) is highlighted in cyan to anchor the eye; the remaining slots are muted. This is a read-only legend — it carries no interactivity and no extra state.

- [ ] **Step 4: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. The `TermTip` import resolves through the barrel; `'lineup.slot_order'` is in `TERMS` (added in Task 1) so `TermId` accepts it at compile time.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/lineup/LineupEditor.tsx
git commit -m "feat(v15-p2c): slot-order TermTip + role-label legend

TermTip on 'Slot Order' in the subtitle explains what ordering controls
(Captain → Utility). A compact legend row previews all six role labels
so the player sees the sequence before touching any slot.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Restyle "Reset to Auto" as a secondary optimize-to-auto helper

**Context:** The current "Reset to Auto" button uses `className="dm-btn"` — the same class as an ordinary action button, sitting in the same row as "Done". Its name "Reset" implies destructive/irreversible action (like discarding work). In reality it calls `commandApi.clearLineup()`, which hands control back to the `LineupResolver` auto-fill — an *optimize-to-auto* action that is recoverable (the player can manually re-edit afterward). The fix:
1. Rename the visible label to **"Auto-Pick"** with an accessible `title` / `aria-label` that describes the full action.
2. Give it a utility/secondary style that visually de-emphasizes it relative to "Done" (the primary close action) without hiding it.
3. The `handleReset` handler is NOT changed — only the JSX for this one button.

**Files:**
- Modify: `frontend/src/components/lineup/LineupEditor.tsx`

- [ ] **Step 1: Locate the "Reset to Auto" button**

Find the footer `<div>` (the one with `borderTop: '1px solid #1e293b'`). Inside it, locate:

```tsx
            <button
              className="dm-btn"
              type="button"
              onClick={handleReset}
              disabled={saving}
            >
              Reset to Auto
            </button>
```

- [ ] **Step 2: Replace with the restyled Auto-Pick helper button**

Replace the entire `<button>` element with:

```tsx
            <button
              type="button"
              onClick={handleReset}
              disabled={saving}
              title="Let the lineup resolver pick the best six automatically. You can manually adjust after."
              aria-label="Auto-Pick: let lineup resolver choose the starting six"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                borderRadius: '4px',
                background: 'transparent',
                border: '1px solid #334155',
                color: '#94a3b8',
                fontSize: '0.78rem',
                fontWeight: 600,
                fontFamily: 'inherit',
                cursor: saving ? 'wait' : 'pointer',
                opacity: saving ? 0.6 : 1,
                transition: 'border-color 0.15s, color 0.15s',
              }}
              onMouseEnter={(e) => {
                if (!saving) {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = '#22d3ee';
                  (e.currentTarget as HTMLButtonElement).style.color = '#22d3ee';
                }
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = '#334155';
                (e.currentTarget as HTMLButtonElement).style.color = '#94a3b8';
              }}
            >
              ⚙ Auto-Pick
            </button>
```

**Rationale for each choice:**
- `transparent` background + `#334155` border: utility/secondary tier — clearly below the `ActionButton` ("Done") in visual weight.
- `⚙` glyph: universally recognized as "settings/auto" — signals this is a configuration tool, not a delete/undo.
- `title` + `aria-label`: both surfaces explicitly say "let lineup resolver choose" so the action is unambiguous for hover, assistive tech, and keyboard-only users.
- Hover brightens to `#22d3ee` / cyan border: consistent with the dm-* active-state color, makes the button feel responsive without being aggressive.
- No `className="dm-btn"`: removes the implicit parity with primary action buttons.

> **Note on hover state via inline style event handlers:** The repo's existing components use `onMouseEnter`/`onMouseLeave` for hover effects on inline-styled buttons (confirmed in `ActionButton` and other dm-* components). This approach is consistent with the codebase's no-Tailwind convention.

- [ ] **Step 3: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS. No new types; event handler types are inferred by React.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/lineup/LineupEditor.tsx
git commit -m "feat(v15-p2c): restyle Reset-to-Auto as a secondary Auto-Pick helper

Rename 'Reset to Auto' → '⚙ Auto-Pick'; give it secondary/utility styling
(transparent bg, muted border) so it reads as a configuration helper, not a
destructive reset; aria-label and title make the recoverable action explicit.
Handler is unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Playwright spec — affordances present and keyboard-operable

**Context:** The repo's Playwright suite hits a live Python server (`http://127.0.0.1:8000`). Tests create a save via the REST API, navigate to the roster screen, and assert DOM state. No `import.meta.env.DEV` guard is needed here — the lineup editor is a normal modal triggered from the Roster screen. The spec asserts: (1) the active/bench split headers are visible; (2) the slot-order `TermTip` trigger is keyboard-focusable and reveals its tooltip; (3) the "Auto-Pick" button carries the correct accessible label; (4) the dialog is keyboard-operable end-to-end.

**Files:**
- Create: `tests/e2e/v15-lineup-editor.spec.ts`

- [ ] **Step 1: Create the spec**

```ts
import { expect, test, type Page, type APIRequestContext } from '@playwright/test';

const baseUrl = 'http://127.0.0.1:8000';

async function openLineupEditor(page: Page, request: APIRequestContext): Promise<void> {
  const saveName = `e2e-v15-lineup-${Date.now()}`;
  const create = await request.post(`${baseUrl}/api/saves/new`, {
    data: { name: saveName, club_id: 'aurora' },
  });
  expect(create.ok()).toBeTruthy();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${baseUrl}/?tab=roster`);
  await expect(page.getByRole('heading', { name: /Team Roster/i })).toBeVisible({ timeout: 10000 });

  // Open the lineup editor from the Roster screen header button.
  await page.getByRole('button', { name: /Lineup Editor/i }).click();
  await expect(page.getByRole('dialog', { name: /Lineup Editor/i })).toBeVisible();
}

test('V15 2c: active/bench split headers are unambiguous', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // Active group carries the cyan "6 fielded" badge.
  const activeGroup = dialog.getByRole('group', { name: /Active starters/i });
  await expect(activeGroup).toBeVisible();
  await expect(activeGroup.getByText(/6 fielded/i)).toBeVisible();

  // Bench group carries the muted "not fielded" badge.
  const benchGroup = dialog.getByRole('group', { name: /Bench players/i });
  await expect(benchGroup).toBeVisible();
  await expect(benchGroup.getByText(/not fielded/i)).toBeVisible();
});

test('V15 2c: slot-order TermTip is keyboard-focusable and reveals tooltip', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // The TermTip wraps "Slot order" as a focusable button with aria-label "What is Slot Order?"
  const termTipTrigger = dialog.getByRole('button', { name: /What is Slot Order\?/i });
  await expect(termTipTrigger).toBeVisible();

  // Focus via keyboard — Tab into the dialog then navigate.
  await termTipTrigger.focus();
  await expect(page.getByRole('tooltip')).toBeVisible();
  await expect(page.getByRole('tooltip')).toContainText(/slot/i);
  await expect(page.getByRole('tooltip')).toContainText(/Captain/i);
});

test('V15 2c: role-label legend shows all six slots', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // All six ROLE_LABELS should be visible in the legend.
  for (const label of ['Captain', 'Striker', 'Anchor', 'Runner', 'Rookie', 'Utility']) {
    await expect(dialog.getByText(new RegExp(label, 'i')).first()).toBeVisible();
  }
});

test('V15 2c: Auto-Pick button has accessible label and secondary style (not destructive)', async ({ page, request }) => {
  await openLineupEditor(page, request);
  const dialog = page.getByRole('dialog', { name: /Lineup Editor/i });

  // Button must be findable by its accessible label.
  const autoPick = dialog.getByRole('button', { name: /Auto-Pick/i });
  await expect(autoPick).toBeVisible();
  await expect(autoPick).toBeEnabled();

  // The button's title must describe the recoverable action.
  const titleAttr = await autoPick.getAttribute('title');
  expect(titleAttr).toMatch(/lineup resolver/i);

  // Confirm "Reset" no longer appears as the button label (old destructive framing gone).
  await expect(dialog.getByRole('button', { name: /^Reset to Auto$/i })).toHaveCount(0);
});

test('V15 2c: dialog has no horizontal overflow at 390px', async ({ page, request }) => {
  await openLineupEditor(page, request);

  const hasHorizontalOverflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth > window.innerWidth;
  });
  expect(hasHorizontalOverflow).toBe(false);
});

test('V15 2c: Escape key closes the dialog', async ({ page, request }) => {
  await openLineupEditor(page, request);
  await expect(page.getByRole('dialog', { name: /Lineup Editor/i })).toBeVisible();

  await page.keyboard.press('Escape');

  // The close handler fires via the overlay onClick; confirm dialog gone.
  // Note: if the close handler does not wire Escape natively, this test
  // documents the gap — do not add Escape handling in this phase (out of scope).
  // The test is written to be a soft-regression: if Escape already works, it passes.
  // If it does not, the dialog stays visible and this test fails, surfacing the gap for Phase 5.
  await expect(page.getByRole('dialog', { name: /Lineup Editor/i })).not.toBeVisible({ timeout: 2000 });
});
```

> **Implementation note on the Escape test:** The current `LineupEditor` attaches `onClick={onClose}` to the overlay backdrop but does not add a `keyDown` / `keyUp` handler for Escape. If the Escape test fails, **do not** add Escape handling in this phase — it is out of scope (presentation-only for the three listed goals). Instead, leave a comment in the test file noting the gap and let Phase 5 (Verification hardening) address it. Do not skip or suppress the failing test — record the gap.

- [ ] **Step 2: Run the suite for this spec only**

Run (from repo root): `npm run e2e -- v15-lineup-editor`
Expected: all tests except possibly the Escape test pass. If the Escape test fails, leave the note in the spec (per the implementation note above) and continue.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/v15-lineup-editor.spec.ts
git commit -m "test(v15-p2c): Playwright spec for lineup editor affordances

Asserts active/bench split headers, TermTip keyboard focus + tooltip,
role-label legend completeness, Auto-Pick accessible label, 390px no
overflow, and Escape-to-close (documents gap if not wired).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2c Exit Gates

Run all before declaring Phase 2c done:

- [ ] From `frontend/`: `npm run build` — clean (the `as const satisfies` gate confirms `lineup.slot_order` is a valid `TermId` and any orphan reference is a compile error).
- [ ] From `frontend/`: `npm run lint` — clean.
- [ ] From repo root: `npm run e2e -- v15-lineup-editor` — passes (note any Escape gap per Task 5 note).
- [ ] From repo root: `npm run e2e` — full suite green (no regression).
- [ ] Manual verification at 390×844 on a fresh "Build from Scratch" career:
  - Roster screen opens → click "Lineup Editor ▸" → dialog opens.
  - Active section has a cyan underline header with "6 fielded" badge; bench section has a muted header with "N not fielded" badge.
  - Six role-label chips (1. Captain … 6. Utility) are visible below the Active header.
  - Clicking "Slot order" in the subtitle opens a TermTip tooltip with slot-order explanation.
  - "⚙ Auto-Pick" button is visually secondary (muted/outline); hovering turns border and text cyan.
  - No horizontal overflow at 390px.
- [ ] Engine-health probe unchanged: `python tools/tier_engine_health_probe.py --driver official --trials 50` — summary identical to Phase 0 baseline (proves zero sim drift; this phase is presentation-only).
- [ ] No `playtest_output/*.png` or `*.db` files committed.

---

## Out of Scope for Phase 2c (do NOT do here)

- **Drag-and-drop reordering:** a real DnD implementation requires a new interaction paradigm and possibly a new dependency (`@dnd-kit`, HTML5 drag API, etc.) — out of scope per constraint "no new deps". The slot-click → bench-click two-step mechanic (already wired) is preserved; this phase only makes it legible. Drag-and-drop can be a future dedicated slice.
- **Engine/resolver changes:** the canonical fielded-six limit and `LineupResolver` auto-fill math are settled. Do not touch `commandApi.saveLineup`, `commandApi.clearLineup`, or any backend file.
- **Archetype tooltip on player name in slots:** archetype TermTips belong to Phase 2b (Roster/Player Card), which owns the player archetype term surface. Phase 2c may not add `TermTip` for archetype terms to avoid double-editing the same terms while Phase 2b is in parallel.
- **Keyboard focus trap in the dialog:** adding a full focus trap (Tab cycles within the dialog, Escape closes) is a Phase 5 verification-hardening task — the Escape test in Task 5 documents the gap without implementing it.
- **Any copy or backend change not listed above.**
