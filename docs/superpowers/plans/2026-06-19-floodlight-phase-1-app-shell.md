# Floodlight Phase 1 — App Shell + SaveMenu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the application shell (boot splash, left-nav rail, broadcast header, workspace) and the SaveMenu (landing + Load/New-Game frame) onto the Floodlight token system using CSS Modules, while keeping the 11 Phase-1 trust behaviors green and **publishing the compile-time contracts** the five concurrent later phases (P2–P7) build against. This is the SOLO first lane of the parallelized 9-phase redesign; it merges to trunk before the concurrent window opens.

**Architecture:** App.tsx and SaveMenu.tsx move from inline-style objects to scoped `*.module.css` files driven by `src/styles/tokens.css`. The five orphan `components/ui.tsx` primitives that SaveMenu/shell consumers need get **signature-identical, token-driven `src/ui` shims** (STEP 1A) so phases re-point imports without touching `ui.tsx`. App.tsx publishes the `MatchWeek` mount-prop interface + `commandReplay` shape + `data-nav-rail` DOM attribute as the consumable contract. P4 `PlayoffBracket` and P5 `ProgramModal` already exist on trunk with stable signatures; Phase 1 freezes those signatures behind compile-time contract tests so P4/P5/P6 can branch safely. All legacy shell/landing/boot `index.css` deletion happens here (Phase 1 is solo, so it owns its own deletions), removing ONLY Phase-1 lines from the shared 720px `@media` block.

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (harness from Phase 0).

**Spec:** [2026-06-19-ui-redesign-design.md](../specs/2026-06-19-ui-redesign-design.md) · **Non-regression contract:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md) §1 (shell/landing/boot screens), §2.A #9/#10, §2.J #82–#89/#91, §3 P1/P2/P3/P5/P10 shell+landing rows · **Checklist:** [floodlight-preservation-checklist.md](floodlight-preservation-checklist.md) Phase 1 rows · **Orchestration contract:** [2026-06-19-floodlight-parallelization-strategy.md](2026-06-19-floodlight-parallelization-strategy.md) GROUP [1] STEP 1 (1A + 1B) · **Foundations + style template:** [2026-06-19-floodlight-phase-0-foundations.md](2026-06-19-floodlight-phase-0-foundations.md)

**Branch:** `feature/floodlight-redesign` (already created; Phase 0 merged at 19/19, trunk green). All Phase-1 commits land here, then merge per strategy STEP 1.

---

## Strategy Phase-1 items honored (orchestration contract checklist)

Every Phase-1 item the strategy assigns is covered by a task below:

- **1A — 5 `src/ui` shims** (`ActionButton, PageHeader, StatusMessage, RatingBar, RadioGroup`), signature-identical token-driven drop-ins + contract vitests + barrel export → **Task 1**.
- **Published compile-time contract** — `MatchWeek` mount props + `commandReplay` shape + `data-nav-rail` attribute name → **Task 2**.
- **P4 PlayoffBracket + P5 ProgramModal prop-stable skeletons on trunk** (already exist; freeze signatures) → **Task 3**.
- **`data-nav-rail` added to the left-nav rail** (P2 rewrites `MatchWeek.tsx:334` to `closest('[data-nav-rail]')`) → **Task 5**.
- **App.tsx reskin to CSS Modules** (boot/nav/header/workspace), router logic verbatim, behaviors #82–#84/#88/#89 → **Tasks 5, 6**.
- **`padStart`→plain Week fix** at `App.tsx:249` → **Task 6**.
- **SaveMenu reskin to CSS Modules**, behaviors #9/#10/#85/#86/#87/#91, wizard-mount/build-state structurally intact for Phase 7 → **Tasks 7, 8**.
- **Delete all 4 `.app-shell` defs + landing/boot regions + dead `.dm-app-shell/.dm-left-nav/.dm-nav-item/.dm-content` family**; remove ONLY Phase-1 lines from the shared 720px `@media` block → **Task 9**.
- **Integrator-owned SCAN_DIRS append** + full Phase-1 gate → **Task 10**.

**Freezes respected (do NOT touch):** `match-week/matchResult.ts` (frozen cross-phase contract — `formatScoreline/survivorDetail/ScorelineFields/MatchScoreline`), `legibility/*` (read-only until P8), `components/ui.tsx` (NO in-place edits — shims only), `index.css` shared globals `command-action-bar`/`command-policy-overlay` (P8-only deletion). Phase 1 DOES rewrite its own `index.css` regions because it is solo (the single-writer rule that defers deletion to STEP 3 applies to the CONCURRENT phases, not the solo P1 lane).

---

## File map (created/modified in this plan)

**Created (STEP 1A shims):**
- `frontend/src/ui/ActionButton.tsx` + `ActionButton.module.css` + `ActionButton.test.tsx`
- `frontend/src/ui/PageHeader.tsx` + `PageHeader.module.css` + `PageHeader.test.tsx`
- `frontend/src/ui/StatusMessage.tsx` + `StatusMessage.module.css` + `StatusMessage.test.tsx`
- `frontend/src/ui/RatingBar.tsx` + `RatingBar.module.css` + `RatingBar.test.tsx`
- `frontend/src/ui/RadioGroup.tsx` + `RadioGroup.module.css` + `RadioGroup.test.tsx`

**Created (contracts + skeleton freeze):**
- `frontend/src/components/shell/appContracts.ts` (the published `MatchWeekMountProps` + `CommandReplayState` + `NAV_RAIL_ATTR` contract)
- `frontend/src/components/shell/appContracts.test.ts` (type-level + value assertions)
- `frontend/src/components/standings/PlayoffBracket.contract.test.tsx` (freeze `{ data: PlayoffBracketResponse }`)
- `frontend/src/components/dynasty/history/ProgramModal.contract.test.tsx` (freeze `{ clubId, clubName, onClose }`)

**Created (shell + SaveMenu modules + tests):**
- `frontend/src/App.module.css`
- `frontend/src/App.test.tsx`
- `frontend/src/components/SaveMenu.module.css`
- `frontend/src/components/SaveMenu.test.tsx`

**Modified:**
- `frontend/src/ui/index.ts` (append the 5 shim exports)
- `frontend/src/App.tsx` (reskin to module CSS + `data-nav-rail` + `padStart` fix; router logic verbatim)
- `frontend/src/components/SaveMenu.tsx` (reskin to module CSS; wizard mounts + build state untouched in structure)
- `frontend/src/index.css` (DELETE the 4 `.app-shell` defs, the legacy `.left-nav*/.nav-item/.workspace/.broadcast-header/.content-area` shell block, the `.landing-*` block, the `.app-boot*` block + keyframes, the dead `.dm-app-shell/.dm-left-nav*/.dm-nav-item*/.dm-nav-dot/.dm-nav-label-short/.dm-workspace/.dm-content` family; remove ONLY Phase-1 lines from the 720px `@media`)
- `frontend/scripts/check-tokens.mjs` (append the migrated dirs to `SCAN_DIRS`)

**Frozen / not touched:** `components/ui.tsx`, `match-week/matchResult.ts`, `legibility/*`, `MatchWeek.tsx` (P2 rewrites line 334 — Phase 1 only ADDS the `data-nav-rail` attribute the rewrite will target), the wizard step components (`new-game/*`), `command-action-bar`/`command-policy-overlay` globals.

---

## Per-task gate

Unless a task says otherwise, every task ends green on:

```bash
cd frontend && npm run test -- <the task's test files> && npm run build && npm run lint && npm run lint:tokens
```

The **Phase-1 merge gate** (Task 10) additionally runs the full FE suite + the root e2e smoke + pytest:

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e
python -m pytest -q
```

> `npm run lint:tokens` only fails on **migrated** dirs (those in `SCAN_DIRS`). `src/ui` is already scanned (Phase 0); `App.module.css` / `SaveMenu.module.css` come into scope only after Task 10 appends them — so token violations in the shell modules are caught at Task 10, and each reskin task (5–8) must pre-empt them by using only `var(--…)` tokens (no raw hex/px beyond `0`/`1px` hairlines) from the start.

---

## Phase 1A — STEP 1A shims (integrator pre-step)

### Task 1: Signature-identical token-driven `src/ui` shims for the 5 orphan primitives

> **Why:** `ActionButton, PageHeader, StatusMessage, RatingBar, RadioGroup` live ONLY in `components/ui.tsx` (no `src/ui` drop-in). The whole-window freeze forbids editing `ui.tsx`, so the concurrent phases need token-driven `src/ui` versions with **identical signatures** to re-point imports against. Per strategy: **no `ActionButton→ActionBar` remap** here (deferred to P8). The shims must preserve every a11y/handler contract: `StatusMessage` derives `role='alert'` for danger/warning and `role='status'` otherwise (and honors an explicit `role`); `ActionButton` forwards `onClick`/`disabled`/`type` (default `'button'`) and keeps the `variant` prop; `RatingBar` keeps the `?`-affordance with `data-testid="rating-explanation"` + `data-explanation-label`; `RadioGroup` keeps `role="radiogroup"`, `role="radio"`+`aria-checked`, roving tabindex, arrow/Home/End keys, and the `renderOption({ option, selected, radioProps })` render-prop API.

**Real signatures captured from `frontend/src/components/ui.tsx` (these are the contract — match them exactly):**

- `ActionButton` (ui.tsx:89-114): `{ children: ReactNode; variant?: 'primary' | 'accent' | 'secondary' | 'danger' | 'ghost'; className?: string } & React.ButtonHTMLAttributes<HTMLButtonElement>`; renders `<button type={type ?? 'button'} className={\`dm-action dm-action-${variant} ${className}\`.trim()} style={style}>`.
- `PageHeader` (ui.tsx:57-87): `{ eyebrow?: string; title: string; description?: string; actions?: ReactNode; stats?: ReactNode }`.
- `StatusMessage` (ui.tsx:136-176): `{ title: string; children?: ReactNode; tone?: Tone; role?: 'status' | 'alert' }`; `resolvedRole = role ?? (tone === 'danger' || tone === 'warning' ? 'alert' : 'status')`; sets `aria-live` (`assertive` for alert, `polite` for status). `Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'`.
- `RatingBar` (ui.tsx:265-365): `{ rating: number; max?: number; label?: string; compact?: boolean; explanation?: string }`.
- `RadioGroup<T extends string>` (ui.tsx:602-703): `{ value: T; onChange: (next: T) => void; options: ReadonlyArray<RadioGroupOption<T>>; label?: string; labelledBy?: string; orientation?: 'vertical' | 'horizontal'; className?: string; style?: React.CSSProperties; renderOption: (args: { option; selected; radioProps }) => ReactNode }` with `RadioGroupOption<T> = { value: T; label: string; children?: ReactNode; disabled?: boolean; 'data-testid'?: string }` and `radioProps = { role: 'radio'; 'aria-checked': boolean; tabIndex: number; disabled?: boolean; onClick: () => void; 'data-testid'?: string }`.

**Files:** the 5 created shim triples + modify `frontend/src/ui/index.ts`.

- [ ] **Step 1: Write the failing contract tests** (one per shim). These assert the load-bearing contract, not pixels.

```tsx
// frontend/src/ui/ActionButton.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ActionButton } from './ActionButton';

describe('ActionButton shim', () => {
  it('defaults type to button and forwards onClick', async () => {
    const onClick = vi.fn();
    render(<ActionButton onClick={onClick}>Go</ActionButton>);
    const btn = screen.getByRole('button', { name: 'Go' });
    expect(btn).toHaveAttribute('type', 'button');
    await userEvent.click(btn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
  it('honors disabled and an explicit submit type', () => {
    render(<ActionButton type="submit" disabled>Save</ActionButton>);
    const btn = screen.getByRole('button', { name: 'Save' });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('type', 'submit');
  });
});
```

```tsx
// frontend/src/ui/PageHeader.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PageHeader } from './PageHeader';

describe('PageHeader shim', () => {
  it('renders title, optional eyebrow/description/actions/stats', () => {
    render(
      <PageHeader
        eyebrow="WAR ROOM"
        title="Command Center"
        description="Plan the week."
        actions={<button>Act</button>}
        stats={<span>3 wins</span>}
      />,
    );
    expect(screen.getByRole('heading', { name: 'Command Center' })).toBeInTheDocument();
    expect(screen.getByText('WAR ROOM')).toBeInTheDocument();
    expect(screen.getByText('Plan the week.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Act' })).toBeInTheDocument();
    expect(screen.getByText('3 wins')).toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/ui/StatusMessage.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusMessage } from './StatusMessage';

describe('StatusMessage shim', () => {
  it('derives role=alert for danger and warning tones', () => {
    const { rerender } = render(<StatusMessage title="Blocked" tone="danger">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveTextContent('Blocked');
    rerender(<StatusMessage title="Careful" tone="warning">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveTextContent('Careful');
  });
  it('derives role=status for calm tones and honors an explicit role', () => {
    const { rerender } = render(<StatusMessage title="Loading" tone="info">x</StatusMessage>);
    expect(screen.getByRole('status')).toHaveTextContent('Loading');
    rerender(<StatusMessage title="Heads up" tone="info" role="alert">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveTextContent('Heads up');
  });
  it('sets aria-live matching the resolved role', () => {
    render(<StatusMessage title="Blocked" tone="danger">x</StatusMessage>);
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive');
  });
});
```

```tsx
// frontend/src/ui/RatingBar.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RatingBar } from './RatingBar';

describe('RatingBar shim', () => {
  it('renders the rounded value and a labelled explanation affordance', () => {
    render(<RatingBar rating={73.4} label="Catch" explanation="How often a catch lands." />);
    expect(screen.getByText('73')).toBeInTheDocument();
    const info = screen.getByTestId('rating-explanation');
    expect(info).toHaveAttribute('data-explanation-label', 'Catch');
    expect(info).toHaveAttribute('aria-label', expect.stringContaining('How often a catch lands.'));
  });
  it('renders without a label (value-left layout) and clamps to 0..100', () => {
    render(<RatingBar rating={150} />);
    expect(screen.getByText('100')).toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/ui/RadioGroup.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { RadioGroup } from './RadioGroup';

const OPTS = [
  { value: 'a', label: 'Alpha', 'data-testid': 'opt-a' },
  { value: 'b', label: 'Bravo', 'data-testid': 'opt-b' },
] as const;

function renderRow({ option, selected, radioProps }: {
  option: { value: string; label: string; 'data-testid'?: string };
  selected: boolean;
  radioProps: Record<string, unknown>;
}) {
  return <div {...radioProps} aria-label={option.label}>{option.label}{selected ? ' ✓' : ''}</div>;
}

describe('RadioGroup shim', () => {
  it('exposes radiogroup + radio roles with aria-checked and roving tabindex', () => {
    render(
      <RadioGroup value="a" onChange={() => {}} options={OPTS} label="Pick" renderOption={renderRow} />,
    );
    expect(screen.getByRole('radiogroup', { name: 'Pick' })).toBeInTheDocument();
    const radios = screen.getAllByRole('radio');
    expect(radios[0]).toHaveAttribute('aria-checked', 'true');
    expect(radios[0]).toHaveAttribute('tabindex', '0');
    expect(radios[1]).toHaveAttribute('tabindex', '-1');
  });
  it('arrow keys move selection (wrapping) and Click selects', async () => {
    const onChange = vi.fn();
    render(
      <RadioGroup value="a" onChange={onChange} options={OPTS} label="Pick" renderOption={renderRow} />,
    );
    const radios = screen.getAllByRole('radio');
    radios[0].focus();
    await userEvent.keyboard('{ArrowDown}');
    expect(onChange).toHaveBeenCalledWith('b');
    await userEvent.click(screen.getByTestId('opt-b'));
    expect(onChange).toHaveBeenLastCalledWith('b');
  });
});
```

- [ ] **Step 2: Run to verify they fail** — `cd frontend && npm run test -- "ui/ActionButton" "ui/PageHeader" "ui/StatusMessage" "ui/RatingBar" "ui/RadioGroup"`. Expected: FAIL (modules unresolved).

- [ ] **Step 3: Implement the 5 shims** — token-driven CSS Modules, signatures copied verbatim from `ui.tsx`. No raw hex/px (the dir is already in `SCAN_DIRS`). Port the proven `RatingBar`/`RadioGroup` interaction logic from `ui.tsx` 1:1 (only the styling substrate changes: inline-style objects → `styles.*` classes + token vars). `ActionButton` keeps the `dm-action dm-action-${variant}` class names on the element (so it still consumes the existing button CSS until P8 reskins it) AND adds a module class for token-driven layout; the visual treatment stays valid because `index.css` `.dm-action` is untouched by Phase 1. Map `Tone`→border/kicker color via CSS-var classes (e.g. `.tone-danger`), not literals.

  Example shape (`StatusMessage` — the role logic is the load-bearing part):

```tsx
// frontend/src/ui/StatusMessage.tsx
import type { ReactNode } from 'react';
import styles from './StatusMessage.module.css';

export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export function StatusMessage({
  title, children, tone = 'info', role,
}: { title: string; children?: ReactNode; tone?: Tone; role?: 'status' | 'alert' }) {
  const resolvedRole: 'status' | 'alert' =
    role ?? (tone === 'danger' || tone === 'warning' ? 'alert' : 'status');
  const ariaLive: 'assertive' | 'polite' = resolvedRole === 'alert' ? 'assertive' : 'polite';
  return (
    <div role={resolvedRole} aria-live={ariaLive} className={`${styles.box} ${styles['tone-' + tone]}`.trim()}>
      <div className={styles.kicker}>{title}</div>
      {children && <div className={styles.body}>{children}</div>}
    </div>
  );
}
```

```css
/* frontend/src/ui/StatusMessage.module.css */
.box { background: var(--raise); border: 1px solid var(--line); border-radius: var(--radius-md); padding: var(--space-5); }
.kicker { font: 600 .62rem var(--font-ui); letter-spacing: .08em; text-transform: uppercase; }
.body { margin-top: var(--space-2); font: 400 .85rem var(--font-ui); color: var(--text2); }
.tone-neutral { border-color: var(--line); } .tone-neutral .kicker { color: var(--muted); }
.tone-accent  { border-color: var(--line2); } .tone-accent  .kicker { color: var(--text); }
.tone-success { border-color: var(--ok-soft); } .tone-success .kicker { color: var(--ok); }
.tone-warning { border-color: var(--gold-soft); } .tone-warning .kicker { color: var(--gold); }
.tone-danger  { border-color: var(--volt-soft); } .tone-danger  .kicker { color: var(--volt2); }
.tone-info    { border-color: var(--line2); } .tone-info    .kicker { color: var(--text2); }
```

  Implement the other four to the same standard (token-only CSS). For `ActionButton`, keep `type={type ?? 'button'}` and the `dm-action dm-action-${variant}` classes; add `style` passthrough; spread `...props`.

- [ ] **Step 4: Run to verify they pass** — `cd frontend && npm run test -- "ui/ActionButton" "ui/PageHeader" "ui/StatusMessage" "ui/RatingBar" "ui/RadioGroup"`. Expected: PASS.

- [ ] **Step 5: Append the shims to the barrel** — in `frontend/src/ui/index.ts` add:

```ts
export { ActionButton } from './ActionButton';
export { PageHeader } from './PageHeader';
export { StatusMessage } from './StatusMessage';
export type { Tone } from './StatusMessage';
export { RatingBar } from './RatingBar';
export { RadioGroup } from './RadioGroup';
export type { RadioGroupOption } from './RadioGroup';
```

- [ ] **Step 6: Gate** — `cd frontend && npm run test -- "ui/" && npm run build && npm run lint && npm run lint:tokens`. Expected: green (`src/ui` already in `SCAN_DIRS`, so token discipline is enforced on the new shims now).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/ui/ActionButton.* frontend/src/ui/PageHeader.* frontend/src/ui/StatusMessage.* frontend/src/ui/RatingBar.* frontend/src/ui/RadioGroup.* frontend/src/ui/index.ts
git commit -m "feat(ui): token-driven src/ui shims for the 5 orphan ui.tsx primitives (STEP 1A)"
```

---

## Phase 1B — Published contracts (consumed by concurrent phases)

### Task 2: Publish the App.tsx mount contract (MatchWeek props + commandReplay shape + data-nav-rail)

> **Why:** Strategy: "App.tsx publishes a compile-time interface for the MatchWeek mount props + `commandReplay` shape that P2 asserts against," plus the `data-nav-rail` attribute name P2 keys its `MatchWeek.tsx:334` rewrite to. Capturing these as a committed, exported module means P2 can branch against a stable import instead of re-reading App.tsx.

**Exact App.tsx prop surface captured (verified in `frontend/src/App.tsx:266-300` + `MatchWeek.tsx:146-165`):** App mounts `MatchWeek` with `onOpenReplay`, `onOffseasonBeatChange`, `persistedResult`, `mode`, `onPlanWeek`, `onSimComplete`, `onAdvanceWeek`. `MatchWeek`'s declared props (the authority) are:

```ts
onOpenReplay?: (matchId: string) => void;
mode: 'pre-sim' | 'post-sim' | 'offseason';            // = MatchWeekMode (MatchWeek.tsx:25)
persistedResult?: CommandCenterSimResponse | null;
onSimComplete?: (result: CommandCenterSimResponse) => void;
onAdvanceWeek?: () => void;
onOffseasonBeatChange?: (title: string | null) => void;
onPlanWeek?: (week: number) => void;
```

The `commandReplay` state is `MatchReplayResponse | null` (App.tsx:48 `useState<MatchReplayResponse | null>`), populated by `commandApi.replay(matchId)`.

**Files:** create `frontend/src/components/shell/appContracts.ts` + `appContracts.test.ts`.

- [ ] **Step 1: Write the failing contract test** — type-level (compile-time) + value assertions.

```ts
// frontend/src/components/shell/appContracts.test.ts
import type { ComponentProps } from 'react';
import { describe, it, expect, expectTypeOf } from 'vitest';
import { NAV_RAIL_ATTR } from './appContracts';
import type { MatchWeekMountProps, CommandReplayState } from './appContracts';
// MatchWeek is a NAMED export (MatchWeek.tsx:146 `export function MatchWeek`).
// Import the live component so the published contract is tied to its REAL prop
// type — not a hardcoded union that could silently diverge if MatchWeek changes.
import { MatchWeek } from '../MatchWeek';
import type { CommandCenterSimResponse, MatchReplayResponse } from '../../types';

type LiveMatchWeekProps = ComponentProps<typeof MatchWeek>;

describe('app shell published contract', () => {
  it('names the nav-rail DOM attribute P2 keys its reveal-skip on', () => {
    expect(NAV_RAIL_ATTR).toBe('data-nav-rail');
  });
  it('MatchWeekMountProps tracks the LIVE MatchWeek prop surface (drift-proof, compile-time)', () => {
    // Tie every published field to MatchWeek's REAL prop type. If MatchWeek.tsx's
    // `mode` (or any other prop) changes, this fails the build — the hardcoded
    // union is gone, so the contract cannot silently drift.
    expectTypeOf<MatchWeekMountProps['mode']>().toEqualTypeOf<LiveMatchWeekProps['mode']>();
    expectTypeOf<MatchWeekMountProps['onOpenReplay']>().toEqualTypeOf<LiveMatchWeekProps['onOpenReplay']>();
    expectTypeOf<MatchWeekMountProps['onSimComplete']>().toEqualTypeOf<LiveMatchWeekProps['onSimComplete']>();
    expectTypeOf<MatchWeekMountProps['onAdvanceWeek']>().toEqualTypeOf<LiveMatchWeekProps['onAdvanceWeek']>();
    expectTypeOf<MatchWeekMountProps['onPlanWeek']>().toEqualTypeOf<LiveMatchWeekProps['onPlanWeek']>();
    expectTypeOf<MatchWeekMountProps['onOffseasonBeatChange']>()
      .toEqualTypeOf<LiveMatchWeekProps['onOffseasonBeatChange']>();
    expectTypeOf<MatchWeekMountProps['persistedResult']>().toEqualTypeOf<LiveMatchWeekProps['persistedResult']>();
  });
  it('the whole MatchWeekMountProps is a valid prop bag for the live MatchWeek (assignable)', () => {
    // Anything declared mountable by the contract must actually mount MatchWeek.
    expectTypeOf<MatchWeekMountProps>().toMatchTypeOf<LiveMatchWeekProps>();
  });
  it('still anchors `mode` to the published string literals (canary on the live type)', () => {
    // A redundant literal anchor so a reviewer can read the expected shape AND so a
    // change that widens MatchWeek's `mode` (e.g. to `string`) is caught here too.
    expectTypeOf<LiveMatchWeekProps['mode']>().toEqualTypeOf<'pre-sim' | 'post-sim' | 'offseason'>();
  });
  it('CommandReplayState is the replay payload or null', () => {
    expectTypeOf<CommandReplayState>().toEqualTypeOf<MatchReplayResponse | null>();
  });
});
```

> **Note (used types):** `CommandCenterSimResponse` is no longer referenced directly in the prop-equality block (the assertions now read through `LiveMatchWeekProps`), so keep the `CommandCenterSimResponse` import ONLY if a remaining assertion needs it — at present only `MatchReplayResponse` is still used by name (`CommandReplayState`). Drop `CommandCenterSimResponse` from the import to avoid an unused-import lint error, or keep it and reference it in an extra `persistedResult` literal anchor if you prefer an explicit shape check. Either is fine; the build/lint gate will tell you.

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "appContracts"`. Expected: FAIL (module unresolved — `./appContracts` does not exist yet; the `../MatchWeek` import resolves). *(`expectTypeOf`/`toMatchTypeOf` ship with Vitest; no new dep.)*

- [ ] **Step 3: Implement the contract module** — it re-uses the live `MatchWeekMode`/response types so it cannot silently drift from `MatchWeek.tsx`. Since `MatchWeekMode` is currently a local (non-exported) alias in `MatchWeek.tsx`, redeclare it here as the published source AND have Task 5 import it back into App so there is one literal.

```ts
// frontend/src/components/shell/appContracts.ts
// Published Phase-1 compile-time contract. P2 imports these to mount MatchWeek
// and to assert the replay state shape without re-reading App.tsx. Keep in lockstep
// with MatchWeek's declared props (MatchWeek.tsx:146-165) and App's commandReplay
// state (App.tsx:48). appContracts.test.ts fails the build if either drifts.
import type { CommandCenterSimResponse, MatchReplayResponse } from '../../types';

/** The mode union MatchWeek switches on (mirrors MatchWeek.tsx MatchWeekMode). */
export type MatchWeekMode = 'pre-sim' | 'post-sim' | 'offseason';

/** Exact props App passes to <MatchWeek/>. P2's PreSimDashboard/aftermath/replay
 *  rebuild must keep MatchWeek mountable with precisely this surface. */
export interface MatchWeekMountProps {
  mode: MatchWeekMode;
  onOpenReplay?: (matchId: string) => void;
  persistedResult?: CommandCenterSimResponse | null;
  onSimComplete?: (result: CommandCenterSimResponse) => void;
  onAdvanceWeek?: () => void;
  onOffseasonBeatChange?: (title: string | null) => void;
  onPlanWeek?: (week: number) => void;
}

/** App's command-center replay overlay state. */
export type CommandReplayState = MatchReplayResponse | null;

/** DOM attribute marking the primary nav rail. P2 rewrites MatchWeek.tsx:334
 *  `closest('.dm-left-nav')` → `closest('[data-nav-rail]')` against THIS name. */
export const NAV_RAIL_ATTR = 'data-nav-rail' as const;
```

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "appContracts"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "appContracts" && npm run build && npm run lint
git add frontend/src/components/shell/appContracts.ts frontend/src/components/shell/appContracts.test.ts
git commit -m "feat(shell): publish MatchWeek mount + commandReplay + data-nav-rail contract (P2 consumes)"
```

---

### Task 3: Freeze the P4 PlayoffBracket + P5 ProgramModal prop-stable skeletons on trunk

> **Why:** Strategy: P4 lands a prop-stable `standings/PlayoffBracket` skeleton and P5 a prop-stable `dynasty/history/ProgramModal` skeleton on trunk in STEP 1, so P6 (which statically imports PlayoffBracket via `ChampionReveal.tsx:4`) and P4-consumes-ProgramModal can branch against frozen signatures. **Both files already exist on trunk with stable public signatures** (verified): `PlayoffBracket({ data }: { data: PlayoffBracketResponse })` (PlayoffBracket.tsx:121) and `ProgramModal({ clubId, clubName, onClose }: { clubId: string; clubName: string; onClose: () => void })` (ProgramModal.tsx:4-10). So Phase 1's job is NOT to create skeletons — it is to **freeze those signatures behind compile-time contract tests** so a later phase cannot silently change the public API the other phase branched against. Implementation bodies remain owned by P4/P5 — only the interface is frozen here.

**Files:** create `frontend/src/components/standings/PlayoffBracket.contract.test.tsx` + `frontend/src/components/dynasty/history/ProgramModal.contract.test.tsx`.

- [ ] **Step 1: Write the failing contract tests**

```tsx
// frontend/src/components/standings/PlayoffBracket.contract.test.tsx
import { describe, it, expectTypeOf } from 'vitest';
import { PlayoffBracket } from './PlayoffBracket';
import type { PlayoffBracketResponse } from '../../types';
import type { ComponentProps } from 'react';

describe('PlayoffBracket public contract (frozen for P6/ChampionReveal)', () => {
  it('accepts exactly { data: PlayoffBracketResponse }', () => {
    expectTypeOf<ComponentProps<typeof PlayoffBracket>>().toEqualTypeOf<{ data: PlayoffBracketResponse }>();
  });
});
```

```tsx
// frontend/src/components/dynasty/history/ProgramModal.contract.test.tsx
import { describe, it, expectTypeOf } from 'vitest';
import { ProgramModal } from './ProgramModal';
import type { ComponentProps } from 'react';

describe('ProgramModal public contract (frozen for P4 consumers)', () => {
  it('accepts exactly { clubId, clubName, onClose }', () => {
    expectTypeOf<ComponentProps<typeof ProgramModal>>()
      .toEqualTypeOf<{ clubId: string; clubName: string; onClose: () => void }>();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "PlayoffBracket.contract" "ProgramModal.contract"`. Expected: **PASS immediately** (the signatures already match). If either FAILS, the on-trunk signature differs from the strategy's stated contract — STOP and reconcile with the controller before proceeding (do not edit P4/P5 source in Phase 1).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/standings/PlayoffBracket.contract.test.tsx frontend/src/components/dynasty/history/ProgramModal.contract.test.tsx
git commit -m "test(shell): freeze PlayoffBracket + ProgramModal public signatures for P4/P5/P6"
```

---

## Phase 1C — App.tsx reskin

### Task 4: App.tsx test scaffolding (router + classification, RED first)

> **Why:** App.tsx has zero component tests today; the reskin must prove behaviors **#82** (router trusts LIVE career state over `next_state`), **#83** (offseason vs in-season classification → screen + header), **#84** (season/week/year fallback precedence; post-sim week priority), **#88** (active-tab persists to `?tab=` only in game/offseason, validated), **#89** (save-state fetch failure → menu, not broken shell) all survive. Author them against the CURRENT (pre-reskin) App so they pass on the existing markup, then the reskin (Tasks 5–6) must keep them green. This is the "lock behavior before changing the substrate" discipline (spec §5.8).

**Audit numbers + test strategy (checklist Phase 1):** #82 vitest (App router) · #83 vitest · #84 vitest · #88 vitest · #89 vitest.

**Files:** create `frontend/src/App.test.tsx`.

- [ ] **Step 1: Write the failing tests** — mock `careerApi`/`commandApi` from `./api/client`; mount `<App/>`; assert behavior via DOM + URL. Mock the heavy child components (`MatchWeek`, `DynastyOffice`, `Standings`, `Roster`, `SaveMenu`, `MatchReplay`) to lightweight stubs so the test exercises App's own routing/classification, not their internals.

```tsx
// frontend/src/App.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('./components/MatchWeek', () => ({ MatchWeek: () => <div data-testid="stub-matchweek" /> }));
vi.mock('./components/DynastyOffice', () => ({ DynastyOffice: () => <div data-testid="stub-dynasty" /> }));
vi.mock('./components/LeagueContext', () => ({ Standings: () => <div data-testid="stub-standings" /> }));
vi.mock('./components/Roster', () => ({ Roster: () => <div data-testid="stub-roster" /> }));
vi.mock('./components/SaveMenu', () => ({ SaveMenu: () => <div data-testid="stub-savemenu" /> }));
vi.mock('./components/MatchReplay', () => ({ default: () => <div data-testid="stub-replay" /> }));

import { careerApi } from './api/client';
import App from './App';

vi.mock('./api/client', () => ({
  careerApi: { saveState: vi.fn(), status: vi.fn(), unloadSave: vi.fn() },
  commandApi: { replay: vi.fn() },
}));

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  vi.clearAllMocks();
});
afterEach(() => vi.restoreAllMocks());

describe('App routing / classification (audit #82-#89)', () => {
  it('#89: a save-state fetch failure falls back to the menu, not a broken shell', async () => {
    vi.mocked(careerApi.saveState).mockRejectedValue(new Error('boom'));
    render(<App />);
    expect(await screen.findByTestId('stub-savemenu')).toBeInTheDocument();
  });

  it('#83 + #84: in-season status renders the game shell with a Season N -- Week NN header', async () => {
    vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
    vi.mocked(careerApi.status).mockResolvedValue({
      state: { state: 'in_season', season_number: 3, week: 7 },
      context: { season_year: 2031 },
    } as never);
    render(<App />);
    expect(await screen.findByTestId('stub-matchweek')).toBeInTheDocument();
    expect(screen.getByText(/Season 3 -- Week 07/)).toBeInTheDocument();
  });

  it('#83: an offseason state renders the offseason header (no Week NN)', async () => {
    vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
    vi.mocked(careerApi.status).mockResolvedValue({
      state: { state: 'season_complete_offseason_beat', season_number: 4, week: 12 },
      context: { season_year: 2032 },
    } as never);
    render(<App />);
    await screen.findByTestId('stub-matchweek');
    expect(screen.getByText(/Season 4 -- Offseason/)).toBeInTheDocument();
    expect(screen.queryByText(/Week/)).not.toBeInTheDocument();
  });

  it('#88: switching tabs persists ?tab= and ignores unknown tabs on load', async () => {
    window.history.replaceState(null, '', '/?tab=bogus');
    vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
    vi.mocked(careerApi.status).mockResolvedValue({
      state: { state: 'in_season', season_number: 1, week: 1 },
      context: { season_year: 2029 },
    } as never);
    render(<App />);
    await screen.findByTestId('stub-matchweek'); // bogus tab → defaults to command
    await userEvent.click(screen.getByRole('button', { name: 'Roster' }));
    expect(await screen.findByTestId('stub-roster')).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get('tab')).toBe('roster');
  });
});
```

> Note for #82 (router trusts LIVE state over `next_state` on advance): that path runs inside `onAdvanceWeek`, which is fired by `MatchWeek`. With `MatchWeek` stubbed it cannot be exercised end-to-end at the App level. Cover #82 by a **focused unit assertion** in the same file that imports nothing new: assert the `OFFSEASON_STATES` set membership logic via a tiny exported helper if one exists, OR document that #82 is covered by the existing root e2e (`tests/e2e/maximized-playthrough-qa.spec.ts` exercises fast-forward→offseason). Prefer adding an exported pure helper `classifyScreen(state: string): 'game' | 'offseason'` to App (used by both the initial load and `onAdvanceWeek`) and unit-test it — this de-duplicates the `OFFSEASON_STATES.has(...)` logic AND makes #82 directly testable. (Implement that extraction in Task 5; reference it here.)

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "App.test"`. Expected: the #83/#84/#88/#89 cases PASS against the current App (markup unchanged), proving the harness is correctly wired. (If a case fails because the current header text differs, fix the assertion to the CURRENT truth — these are guards on existing behavior, not new behavior.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.test.tsx
git commit -m "test(shell): lock App router/classification behaviors (#82-#89) before reskin"
```

---

### Task 5: App.tsx — boot splash + left-nav rail to CSS Modules + data-nav-rail (#88, #82 extraction)

> **Why:** Replace the inline-style boot splash (`App.tsx:90-100`) and the heavily-inlined left-nav rail (`App.tsx:134-236`: collapsed `width:'3rem'`, the box-shadow hamburger, the inline `#1e293b`/`#94a3b8` literals — audit §3 P1 high) with `App.module.css`. Add `data-nav-rail` to the `<aside>` so P2 can rewrite `MatchWeek.tsx:334` `closest('.dm-left-nav')` → `closest('[data-nav-rail]')`. Extract `classifyScreen` so #82's live-state-trust path is unit-testable and de-duplicated. **Router logic stays verbatim** — only the styling substrate and the `data-nav-rail` attribute change.

**Audit numbers + test strategy:** #88 vitest (tab persistence preserved through the reskin) · #82 vitest (the extracted `classifyScreen` is the single source the initial load AND `onAdvanceWeek` use).

**Files:** create `frontend/src/App.module.css`; modify `frontend/src/App.tsx`; extend `frontend/src/App.test.tsx`.

- [ ] **Step 1: Add the #82 + data-nav-rail RED assertions** to `App.test.tsx`:

```tsx
import { classifyScreen } from './App';

describe('classifyScreen (audit #82 — single source of screen truth)', () => {
  it('maps offseason states to "offseason" and everything else to "game"', () => {
    expect(classifyScreen('season_complete_offseason_beat')).toBe('offseason');
    expect(classifyScreen('season_complete_recruitment_pending')).toBe('offseason');
    expect(classifyScreen('next_season_ready')).toBe('offseason');
    expect(classifyScreen('in_season')).toBe('game');
    expect(classifyScreen('')).toBe('game');
  });
});

it('marks the primary nav rail with data-nav-rail (P2 reveal-skip contract)', async () => {
  vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
  vi.mocked(careerApi.status).mockResolvedValue({
    state: { state: 'in_season', season_number: 1, week: 1 },
    context: { season_year: 2029 },
  } as never);
  render(<App />);
  await screen.findByTestId('stub-matchweek');
  expect(document.querySelector('[data-nav-rail]')).not.toBeNull();
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "App.test"`. Expected: FAIL (`classifyScreen` not exported; no `[data-nav-rail]` element yet).

- [ ] **Step 3: Implement**
  - Export `classifyScreen`: `export function classifyScreen(state: string): Screen extends never ? never : 'game' | 'offseason' { return OFFSEASON_STATES.has(state) ? 'offseason' : 'game'; }` (simpler: `export function classifyScreen(state: string): 'game' | 'offseason' { return OFFSEASON_STATES.has(state) ? 'offseason' : 'game'; }`). Use it in `refreshCareerContext` (`setScreen(classifyScreen(state))`) and in `onAdvanceWeek` (replace the `OFFSEASON_STATES.has(nextState) || OFFSEASON_STATES.has(liveState)` branch with `if (classifyScreen(nextState) === 'offseason' || classifyScreen(liveState) === 'offseason')`). **Do not change the routing semantics** — `nextState`/`liveState` precedence and the "trust live state" comment stay.
  - Create `App.module.css` with `.shell`, `.boot`, `.bootKicker`, `.bootBrand`, `.courtPulse` (+ the `app-boot-pulse` keyframes + the reduced-motion override), `.nav`, `.navCollapsed`, `.hamburger`, `.hamburgerIcon`, `.navLogo`, `.navItems`, `.navFooter`, `.navItem`, `.navItemActive`, `.dot` — token-driven, no raw hex/px. The collapsed width becomes a class toggle, not an inline `width:'3rem'`.
  - Reskin the boot splash (`screen === 'loading'`) and the `<aside>`/`<nav>`/footer to `className={styles.*}`. Keep `role="status"`, `aria-label`, `aria-expanded`, `aria-controls="primary-nav"`, `id="primary-nav"`, `aria-label="Primary"`, the hamburger `ref`/focus-return logic, and every `onClick`/`tabIndex`/`title`/`aria-label` exactly. **Add `data-nav-rail` to the `<aside>`** (use `[NAV_RAIL_ATTR]: ''` spread or a literal `data-nav-rail=""`; importing `NAV_RAIL_ATTR` from `./components/shell/appContracts` keeps one source). Keep the `nav-item active` semantics via `styles.navItem`/`styles.navItemActive`. Import `MatchWeekMode` from `appContracts` and replace App's local `Tab`/mode literal where `mode={...}` is computed (the `'offseason' | 'post-sim' | 'pre-sim'` ternary already matches `MatchWeekMode`).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "App.test"`. Expected: PASS (classifyScreen + data-nav-rail + the prior #83/#84/#88/#89 cases stay green).

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "App.test" && npm run build && npm run lint
git add frontend/src/App.tsx frontend/src/App.module.css frontend/src/App.test.tsx
git commit -m "feat(shell): App boot+nav rail to CSS Modules + data-nav-rail; extract classifyScreen (#82,#88)"
```

---

### Task 6: App.tsx — broadcast header + workspace to CSS Modules + padStart→plain Week fix (#83, #84)

> **Why:** Finish the App.tsx reskin: the `.broadcast-header`/`.workspace`/`.content-area` chrome and the inline `padStart` Week format. The strategy calls for the `padStart` fix at `App.tsx:249`: `Week ${String(displayedWeek).padStart(2, '0')}` zero-pads ("Week 07"), which the redesign drops to a plain number ("Week 7"). `displayedWeek = postSimResult?.dashboard?.week ?? currentWeek ?? 1` is the #84 post-sim-week-priority precedence and must be preserved verbatim — only the formatting changes. The header offseason/in-season branch is #83.

**Audit numbers + test strategy:** #84 vitest (post-sim week priority + fallback precedence) · #83 vitest (header classification).

**Files:** modify `frontend/src/App.tsx`, `frontend/src/App.module.css`; extend `frontend/src/App.test.tsx`.

- [ ] **Step 1: Update the header assertion to the new (un-padded) format** — change the Task 4 `#83 + #84` assertion from `Week 07` to `Week 7`, and ADD a precedence case:

```tsx
it('#84: header shows a plain (un-padded) week number', async () => {
  vi.mocked(careerApi.saveState).mockResolvedValue({ loaded: true, active_path: 'p.db' });
  vi.mocked(careerApi.status).mockResolvedValue({
    state: { state: 'in_season', season_number: 2, week: 5 },
    context: { season_year: 2030 },
  } as never);
  render(<App />);
  await screen.findByTestId('stub-matchweek');
  expect(screen.getByText(/Season 2 -- Week 5\b/)).toBeInTheDocument();
  expect(screen.queryByText(/Week 05/)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "App.test"`. Expected: FAIL (current code still renders `Week 05`).

- [ ] **Step 3: Implement**
  - Replace `Week ${String(displayedWeek).padStart(2, '0')}` with `Week ${displayedWeek}` (line ~249). Keep `displayedWeek = postSimResult?.dashboard?.week ?? currentWeek ?? 1` and the full offseason/in-season ternary exactly.
  - Add `.workspace`, `.header`, `.headerKicker`, `.headerTitle`, `.headerMeta`, `.content` classes to `App.module.css` (token-driven; the orange skew `::before` slash from `index.css:7606` can be reproduced as a `.headerTitle::before` module rule using `var(--volt)` if desired — optional polish, not required for green). Reskin `<header className={styles.header}>`, the kicker/title, the `.meta` span, and the `<div className={styles.content}>` content area. Keep the `kicker`/`headerTitle` MATCH DAY swap logic and the `dm-kicker` text content; the loading-replay `<p>` and the `MatchReplay`/`MatchWeek`/tab conditionals stay structurally identical.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "App.test"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "App.test" && npm run build && npm run lint
git add frontend/src/App.tsx frontend/src/App.module.css frontend/src/App.test.tsx
git commit -m "feat(shell): broadcast header + workspace to CSS Modules; Week un-padded (#83,#84)"
```

---

## Phase 1D — SaveMenu reskin

### Task 7: SaveMenu test scaffolding + save-list reskin (#9, #85, #86, #91)

> **Why:** SaveMenu is ~85 inline-style blocks (audit §3 P1 high). The reskin must keep the V20 save-record truth (#9: render `W-L-D` only when `save.wins !== undefined`, never a fabricated `0-0`), the incompatible-save filtering/labeling (#85), the continue-career hero selection (#86), and the launch-token guard (#91 — already in `api/client.ts` + tested in Phase 0's `client.test.ts`; here we only assert SaveMenu surfaces the resulting error, not the guard internals). Move the landing frame, tab bar, error banner, save rows, continue-hero, and the debug/incompatible toggles to `SaveMenu.module.css`.

**Audit numbers + test strategy (checklist Phase 1):** #9 vitest (SaveMenu row) · #85 vitest · #86 vitest · #91 vitest (already green in `client.test.ts`; SaveMenu test asserts the surfaced banner).

**Behavior anchors (verified in `SaveMenu.tsx`):** #9 at :441-445 (continue-hero record) + :519-526 (row record) — both guarded by `save.wins !== undefined`. #85 at :126-129 (`visibleSaves` filter), :488-510 (Incompatible label + non-loadable), :541 (`disabled` when `save.incompatible`), :563-585 (archive toggle). #86 at :138-140 (`continueSave = saves.find(s => !s.incompatible && !isDebugSaveName(s.name))`). #10/#87 covered in Task 8.

**Files:** create `frontend/src/components/SaveMenu.module.css`, `frontend/src/components/SaveMenu.test.tsx`.

- [ ] **Step 1: Write the failing tests** — mock `saveApi` from `../api/client` and the four wizard step components; render `<SaveMenu onSaveLoaded={vi.fn()} />`.

```tsx
// frontend/src/components/SaveMenu.test.tsx
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('./new-game/IdentityStep', () => ({ IdentityStep: () => <div data-testid="stub-identity" /> }));
vi.mock('./new-game/CoachStep', () => ({ CoachStep: () => <div data-testid="stub-coach" /> }));
vi.mock('./new-game/StaffHiringStep', () => ({ StaffHiringStep: () => <div data-testid="stub-staff" /> }));
vi.mock('./new-game/StartingRecruitmentStep', () => ({ StartingRecruitmentStep: () => <div data-testid="stub-roster" /> }));

import { saveApi } from '../api/client';
import { SaveMenu } from './SaveMenu';

vi.mock('../api/client', () => ({
  saveApi: { list: vi.fn(), clubs: vi.fn(), load: vi.fn(), delete: vi.fn(), create: vi.fn(), buildFromScratch: vi.fn() },
}));

const SAVE = (over: Record<string, unknown> = {}) => ({
  path: 'a.db', name: 'My Career', club_id: 'aurora', club_name: 'Aurora Sentinels',
  season_number: 2, week: 4, last_modified: 1_700_000_000, incompatible: false, ...over,
});

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  vi.clearAllMocks();
  vi.mocked(saveApi.clubs).mockResolvedValue({ clubs: [] } as never);
});
afterEach(() => vi.restoreAllMocks());

describe('SaveMenu save list (audit #9,#85,#86,#91)', () => {
  it('#9: a record renders W-L-D only when wins is defined; never a fabricated 0-0', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'w.db', name: 'With Record', wins: 7, losses: 2, draws: 1 }),
              SAVE({ path: 'n.db', name: 'No Record', wins: undefined })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    const withRow = await screen.findByText('With Record');
    expect(within(withRow.closest('[data-testid="save-item"]')!).getByText(/7-2-1/)).toBeInTheDocument();
    const noRow = (await screen.findByText('No Record')).closest('[data-testid="save-item"]')!;
    expect(within(noRow).queryByText(/0-0/)).not.toBeInTheDocument();
  });

  it('#85: incompatible saves are hidden by default, labeled, and non-loadable when shown', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'ok.db', name: 'Good' }),
              SAVE({ path: 'bad.db', name: 'Broken', incompatible: true, wins: undefined })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    await screen.findByText('Good');
    expect(screen.queryByText('Broken')).not.toBeInTheDocument();           // hidden by default
    await userEvent.click(screen.getByTestId('toggle-incompatible'));        // reveal archive
    expect(await screen.findByText('Broken')).toBeInTheDocument();
    expect(screen.getByText('Incompatible')).toBeInTheDocument();            // labeled
    const badRow = screen.getByText('Broken').closest('[data-testid="save-item"]')!;
    expect(within(badRow).getByTestId('load-save-btn')).toBeDisabled();      // non-loadable
  });

  it('#86: the continue hero picks the first non-incompatible, non-debug save', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'inc.db', name: 'Incompatible One', incompatible: true }),
              SAVE({ path: 'real.db', name: 'Real Career' })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    const hero = await screen.findByTestId('continue-career-hero');
    expect(within(hero).getByText('Real Career')).toBeInTheDocument();
  });

  it('#91: a load failure surfaces the error message in the menu (not a broken shell)', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({ active_path: null, saves: [SAVE()] } as never);
    vi.mocked(saveApi.load).mockRejectedValue(new Error('Action blocked — refresh the page and try again.'));
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    const hero = await screen.findByTestId('continue-career-hero');
    await userEvent.click(within(hero).getByRole('button', { name: 'Continue' }));
    expect(await screen.findByText(/Action blocked/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "SaveMenu.test"`. Expected: these PASS against the CURRENT SaveMenu (they guard existing behavior). If an assertion mismatches the current DOM, correct it to the current truth (they are non-regression guards). This establishes the green baseline the reskin must hold.

- [ ] **Step 3: Reskin the save-list surfaces to `SaveMenu.module.css`** — landing frame (`.landing-shell`/`.landing-card`/`.landing-brand` are reproduced as module classes `.shell`/`.card`/`.brand`; the `.landing-save-row`/`.landing-monogram` likewise as `.row`/`.monogram` — the `--mono-hue` custom-prop pattern is preserved), the tab bar, the error banner, the empty state, the continue-hero, the save rows, and the debug/incompatible toggles. **Preserve every `data-testid`** (`save-menu`, `save-list`, `save-item`, `continue-career-hero`, `load-save-btn`, `delete-save-btn`, `toggle-incompatible`, `new-game-tab`) and the `#9` `save.wins !== undefined` guard, the `#85` filter/label/`disabled`, and the `#86` `continueSave` selection — all in `SaveMenu.tsx` logic, untouched; only the `style={{...}}` props become `className={styles.*}`. Keep the `clubMonogram`/`formatTimeAgo` helpers. Token-driven CSS only (no raw hex/px) so Task 10's token gate passes.

- [ ] **Step 4: Run to verify it still passes** — `cd frontend && npm run test -- "SaveMenu.test"`. Expected: PASS (behavior held through the reskin).

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "SaveMenu.test" && npm run build && npm run lint
git add frontend/src/components/SaveMenu.tsx frontend/src/components/SaveMenu.module.css frontend/src/components/SaveMenu.test.tsx
git commit -m "feat(savemenu): save list + landing to CSS Modules; hold #9/#85/#86/#91"
```

---

### Task 8: SaveMenu — new-game frame reskin + ruleset pin (#10, #87); wizard mounts intact for Phase 7

> **Why:** Finish SaveMenu: the New-Game tab (the "How It Plays" standard-ruleset card, the Take Over / Build-from-Scratch choice cards, the takeover form), keeping #10 (`ruleset_selection` hard-pinned to `'official_foam'` at every create path: `handleCreate` :231-233 and `handleBuildFromScratch` :259-261) and #87 (debug/test saves two-gate: `?debug=true` AND opt-in — `isDebugQueryPresent` :119 + `showDebugSaves` + `baseVisible` :122-125). **The wizard mounts (`SaveMenu.tsx:960-963`) and the build state (`buildIdentity`/`buildCoach`/`buildSeed`/`buildStaff`, the `handleBuildFromScratch` flow, the `setView('build_*')` transitions) MUST stay structurally intact** — Phase 7 reskins the wizard steps and depends on this shell handing them their props unchanged. Phase 1 only restyles SaveMenu's OWN markup, not the step components.

**Audit numbers + test strategy:** #10 vitest + python-guard (the Python guard on `ruleset_selection` already lives in the backend suite; the vitest here asserts the create-path call carries `official_foam`) · #87 vitest.

**Files:** modify `frontend/src/components/SaveMenu.tsx`, `frontend/src/components/SaveMenu.module.css`; extend `frontend/src/components/SaveMenu.test.tsx`.

- [ ] **Step 1: Write the failing tests**

```tsx
describe('SaveMenu new-game frame (audit #10,#87) + wizard intact', () => {
  it('#10: takeover create pins ruleset_selection to official_foam', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({ active_path: null, saves: [] } as never);
    vi.mocked(saveApi.create).mockResolvedValue({ status: 'ok', path: 'new.db' } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    await screen.findByTestId('save-list');
    await userEvent.click(screen.getByTestId('new-game-tab'));
    await userEvent.click(screen.getByRole('button', { name: /Take Over a Program/i }));
    await userEvent.type(screen.getByTestId('save-name-input'), 'Fresh');
    await userEvent.click(screen.getByTestId('create-save-btn'));
    await waitFor(() => expect(saveApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ ruleset_selection: 'official_foam' }),
    ));
  });

  it('#87: debug saves stay hidden without ?debug=true even after Show is unavailable', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'real.db', name: 'Real' }), SAVE({ path: 'd.db', name: 'debug-run-1' })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />); // no ?debug=true
    await screen.findByText('Real');
    expect(screen.queryByText('debug-run-1')).not.toBeInTheDocument();
    expect(screen.queryByText(/debug save/)).not.toBeInTheDocument(); // no "Show" affordance offered
  });

  it('#87: with ?debug=true the count + Show appears and reveals debug saves (two-gate)', async () => {
    window.history.replaceState(null, '', '/?debug=true');
    vi.mocked(saveApi.list).mockResolvedValue({
      active_path: null,
      saves: [SAVE({ path: 'real.db', name: 'Real' }), SAVE({ path: 'd.db', name: 'debug-run-1' })],
    } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    await screen.findByText('Real');
    expect(screen.queryByText('debug-run-1')).not.toBeInTheDocument(); // gate 2 not opted-in yet
    await userEvent.click(screen.getByRole('button', { name: 'Show' }));
    expect(await screen.findByText('debug-run-1')).toBeInTheDocument();
  });

  it('wizard mounts are reachable: Build from Scratch opens the Identity step', async () => {
    vi.mocked(saveApi.list).mockResolvedValue({ active_path: null, saves: [] } as never);
    render(<SaveMenu onSaveLoaded={vi.fn()} />);
    await screen.findByTestId('save-list');
    await userEvent.click(screen.getByTestId('new-game-tab'));
    await userEvent.click(screen.getByRole('button', { name: /Build from Scratch/i }));
    expect(await screen.findByTestId('stub-identity')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "SaveMenu.test"`. Expected: PASS against current SaveMenu (guards), establishing the baseline.

- [ ] **Step 3: Reskin the new-game frame** — move the "How It Plays" card (`ruleset-standard-card`, `ruleset-key-rules`, `ruleset-full-breakdown`), the choice buttons (Take Over / Build from Scratch, including the absolute-positioned "Faster Start" badge from :692-706 — audit §3 P1 high "clips" — reproduce it with a module class that does not clip), the takeover `<form>` (`new-game-form`), and the create error banner to `SaveMenu.module.css`. **Do NOT touch:** the `standardRuleset` content object, `handleCreate`/`handleBuildFromScratch` (the `ruleset_selection: 'official_foam'` pins stay verbatim), the `RadioGroup` club picker (it already uses the `./ui` `RadioGroup`; Phase 1 leaves it pointed there — note it could re-point to the new `src/ui` `RadioGroup` shim, but the strategy says phases re-point imports; for SOLO P1 either source is acceptable as long as the test stays green — prefer leaving `./ui` to minimize blast radius, OR re-point to `../ui` shim and keep `RadioGroup.test.tsx` green). Keep all four wizard `setView('build_*')` mounts (`SaveMenu.tsx:960-963`) and the `createError && view.startsWith('build_')` banner byte-for-byte in structure.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "SaveMenu.test"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "SaveMenu.test" && npm run build && npm run lint
git add frontend/src/components/SaveMenu.tsx frontend/src/components/SaveMenu.module.css frontend/src/components/SaveMenu.test.tsx
git commit -m "feat(savemenu): new-game frame to CSS Modules; hold #10/#87; wizard mounts intact for P7"
```

---

## Phase 1E — index.css deletion + gate

### Task 9: Delete the legacy shell / landing / boot index.css regions + dead dm-shell family

> **Why:** With App.tsx and SaveMenu now module-styled, their legacy `index.css` rules are dead weight (and the duplicate `.app-shell` defs are a known footgun — defined 4×). Phase 1 is SOLO, so it deletes its OWN regions now (the single-writer defer-to-STEP-3 rule binds the CONCURRENT phases, not P1). The dead `.dm-app-shell/.dm-left-nav*/.dm-nav-item*/.dm-nav-dot/.dm-nav-label-short/.dm-workspace/.dm-content` family is **unowned dead code** (grep-confirmed: referenced only by `MatchWeek.tsx`'s stale `closest('.dm-left-nav')` no-op, which P2 rewrites) — strategy assigns its deletion to P1. The shared 720px `@media` block mixes P1 selectors with P6 `.fallout-grid` and P2 `.cc-*/.mr-*` — remove ONLY the P1 lines, leaving siblings intact.

**Exact line regions captured from `frontend/src/index.css` (re-verify offsets at edit time — line numbers shift as you delete top-down, so delete BOTTOM-UP):**

| Region | Lines (at plan time) | Selectors |
|---|---|---|
| Light-theme `.app-shell` override | 108-114 | `.app-shell` (paper gradient) |
| Main shell block | 360-476 | `.app-shell`, `.left-nav`, `.left-nav-logo`, `.left-nav-items`, `.left-nav-footer`, `.nav-item` (+ `:hover/.active/.dot/:disabled`), `.workspace`, `.broadcast-header` (+ `h1`/`.meta`), `.content-area` (+ `.max-content`) |
| Dead dm-nav family | 966-1015 | `.dm-nav-item` (+ `:hover`), `.dm-nav-label-short`, `.dm-nav-item-active`, `.dm-nav-dot`, `.dm-nav-item-active .dm-nav-dot` |
| Dead dm-workspace/content | 1190-1204 | `.dm-workspace`, `.dm-content` |
| Dead dm-shell @media (720px, MIXED) | 1283-1411 (block); dm-shell rules at 1284-1340 | **REMOVE** (1284-1340): `.dm-app-shell.flex`, `.dm-left-nav`, `.dm-left-nav-logo`, `.dm-left-nav nav[aria-label="Primary"]` (+ `::-webkit-scrollbar`), `.dm-left-nav > div:last-child`, `.dm-nav-item`, `.dm-nav-item:hover, .dm-nav-item-active`, `.dm-workspace`, `.dm-content`. **KEEP** (1342-1409): `.dm-hub-hero` + `.dm-hub-*`, `.dm-desktop-only`, `.dm-mobile-only`, `.dm-command-report-lane`, `.dm-command-report-items`, `.dm-replay-court`, `.dm-replay-controls`, `.dm-replay-scrubber` (live non-shell dm families) — keep the `@media (max-width:720px){ … }` wrapper braces. (The original table mislabeled this block as ending at 1340; it actually runs to 1411 and is MIXED — see Step 3 for the brace-safe per-rule deletion.) |
| Mixed responsive @media (1180px) | 4984-5061 (block); dm-shell rules at 4985-4996 | **REMOVE** (3 dm-shell rules): `.dm-left-nav` (4985-4987, `width:11rem`), `.dm-nav-item` (4989-4992, `padding`/`font-size`), `.dm-content` (4994-4996, `padding:1.25rem`). **KEEP** every LIVE sibling in the same block: `.command-console-header` (4998), `.command-cockpit-grid` (5002), `.command-overview-grid` (5006), `.command-overview-card:last-child` (5010), `.command-dashboard-main` (5014), `.command-control-tower` (5018), `.command-secondary-grid, .command-plan-grid, .command-squad-grid, .command-intel-grid` (5022-5025), `.command-alert-strip` (5029), `.command-dashboard-metrics` (5033), `.dynasty-recruit-layout` (5038), `.dynasty-staff-room` (5046), `.dynasty-staff-room > .dm-kicker, .dynasty-staff-room > button` (5052-5053 — `.dm-kicker` is a LIVE shared selector, NOT dm-shell: KEEP), `.dynasty-staff-row` (5057). Keep the `@media (max-width:1180px){ … }` wrapper braces (the block must NOT become empty — it has many live siblings). |
| Mixed responsive @media (960px) | 5063-5191 (block); dm-shell rules at 5064-5151 | **REMOVE** (all dm-shell rules): `.dm-app-shell.flex` (5064-5066), `.dm-left-nav` (5068-5073), `.dm-left-nav-logo, .dm-left-nav > div:last-child` (5075-5078), `.dm-left-nav-logo` (5080-5085), `.dm-left-nav nav[aria-label="Primary"]` (5087-5096), `.dm-left-nav nav[aria-label="Primary"]::-webkit-scrollbar` (5098-5100), `.dm-left-nav > div:last-child` (5102-5108), `.dm-left-nav > div:last-child .dm-nav-item` (5110-5112), `.dm-nav-item` (5114-5124), `.dm-nav-item:hover, .dm-nav-item-active` (5126-5130), `.dm-nav-label-full` (5132-5134), `.dm-nav-label-short` (5136-5138), `.dm-broadcast-header` (5140-5143), `.dm-workspace` (5145-5147), `.dm-content` (5149-5151). **KEEP** the LIVE siblings: `.standings-desktop-view` (5153), `.standings-compact-view` (5157), `.command-next-action` (5161), `.command-next-action-buttons` (5165), `.command-next-action-buttons .command-primary-button, … .command-secondary-button` (5170-5171), `.command-dashboard-main` (5176), `.command-control-tower` (5180), `.command-overview-grid` (5184), `.command-overview-card:last-child` (5188). Keep the `@media (max-width:960px){ … }` wrapper braces. |
| Mixed 720px @media (the 5193 block) — dm-shell lines only | 5193-5312 (block); dm-shell rules at 5194-5200 | **REMOVE** only: `.dm-app-shell.flex` (5194-5196, `display:block !important`), `.dm-left-nav-logo` (5198-5200, `padding-bottom:0.55rem`). **KEEP** all `.command-*`, `.dynasty-*`, `.standings-*` siblings AND the non-shell `.dm-replay-controls` (5298 — a LIVE replay selector, NOT dm-shell). Keep the `@media (max-width:720px){ … }` wrapper braces. |
| Court-floor `.app-shell` atmosphere | 7571-7586 | `.app-shell` (broadcast court gradient) |
| Broadcast-header slash | 7600-7614 | `.broadcast-header h1` + `h1::before` |
| Landing block | 7782-7871 | `.landing-shell`, `.landing-brand` (+ children), `.landing-card`, `.landing-save-row` (+ `:hover`), `.landing-monogram` (+ `.is-incompatible`) |
| App-boot block | 8562-8606 | `.app-boot` (+ `.kicker/.brand/.brand em/.court-pulse`), `@keyframes app-boot-pulse`, the `@media (prefers-reduced-motion)` `.app-boot .court-pulse` override |
| Shared 720px `@media` — P1 lines only | 8631-8637 | DELETE ONLY: `.app-shell`, `.left-nav`, `.left-nav-items`, `.left-nav-logo`, `.left-nav-footer`, `.nav-item`, `.nav-item.active` — **KEEP** `.fallout-grid` (8638, P6), `.cc-*` (8639-8645, P2), `.mr-official-panel` (8641, P2) |

> **Mixed-block discipline (the four MIXED @media rows above — 1283, 4984, 5063, 5193):** each interleaves dead `.dm-*` SHELL selectors with LIVE siblings (`.command-*`, `.standings-*`, `.dynasty-*`, the live non-shell dm families `.dm-hub-*`/`.dm-command-report-*`/`.dm-replay-*`/`.dm-kicker`/`.dm-desktop-only`/`.dm-mobile-only`). Remove ONLY the dm-SHELL rules enumerated in each row; never delete the wrapper `@media (…) { }` braces (every one of these blocks still has live siblings, so none becomes empty). Trap to avoid: `.dm-kicker` (4985 block), `.dm-replay-*` (1283 + 5193 blocks), `.dm-hub-*`/`.dm-command-report-*`/`.dm-desktop-only`/`.dm-mobile-only` (1283 block) all START with `.dm-` but are LIVE — do NOT remove them. The dm-SHELL family being deleted is exactly: `.dm-app-shell`, `.dm-left-nav`(+ descendants/`-logo`), `.dm-nav-item`(+ `:hover`/`-active`/`-dot`), `.dm-nav-label-short`, `.dm-nav-label-full`, `.dm-broadcast-header`, `.dm-workspace`, `.dm-content`.

> **NOT deleted (sibling/shared):** Do **not** touch `.app-shell` usages outside the listed regions (there are none after these deletions — confirm with grep in Step 4). `command-action-bar`/`command-policy-overlay` are NOT touched (P8-only). The LIVE `.dm-*` non-shell families listed in the mixed-block note above are NOT touched by Phase 1 (their owner phases reskin them later).

- [ ] **Step 1: Add a guard test that the shell selectors are gone** — create/extend a tiny CSS-presence assertion so the deletion is verifiable (mirrors Phase 0's `tokens.test.ts` pattern):

```ts
// frontend/src/components/shell/legacyShellCss.test.ts
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';

const css = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../index.css'), 'utf8',
);

describe('legacy shell/landing/boot CSS removed (Phase 1)', () => {
  // The FULL dead dm-shell family enumerated in Fix 1 (every dm-shell selector
  // found across the base rules + the four mixed @media blocks: 1283, 4984, 5063,
  // 5193). Substring `includes` is intentional: asserting `.dm-left-nav` absent
  // also proves `.dm-left-nav-logo`/`.dm-left-nav nav[…]` are gone; `.dm-nav-item`
  // also covers `.dm-nav-item:hover`/`.dm-nav-item-active`. The explicit label/
  // header/dot/active entries make the guard self-documenting even so.
  for (const sel of [
    // legacy (non-dm) shell/landing/boot
    '.app-shell', '.left-nav', '.nav-item', '.broadcast-header', '.content-area',
    '.landing-shell', '.landing-card', '.landing-monogram', '.app-boot', '.court-pulse',
    // dead dm-SHELL family (Fix 1 — complete list)
    '.dm-app-shell', '.dm-left-nav', '.dm-left-nav-logo',
    '.dm-nav-item', '.dm-nav-item-active', '.dm-nav-dot',
    '.dm-nav-label-short', '.dm-nav-label-full', '.dm-broadcast-header',
    '.dm-workspace', '.dm-content',
  ]) {
    it(`no longer defines ${sel}`, () => {
      // Selector must not appear as a rule head (allow it inside comments only by
      // requiring a following { on the same logical rule — simplest: absent entirely).
      expect(css.includes(sel)).toBe(false);
    });
  }
  // Guard against over-deletion: the LIVE non-shell dm families that START with
  // `.dm-` but are NOT shell must SURVIVE (they live inside the same mixed @media
  // blocks the dm-shell rules were carved out of). Their owner phases reskin them.
  for (const liveSel of ['.dm-kicker', '.dm-replay-controls', '.dm-hub-hero', '.dm-command-report-lane']) {
    it(`keeps the live non-shell ${liveSel}`, () => {
      expect(css).toContain(liveSel);
    });
  }
  it('keeps the P6/P2 siblings in the 720px breakpoint', () => {
    expect(css).toContain('.fallout-grid');
    expect(css).toContain('.cc-body');
  });
});
```

> **Guard caveat (`.dm-content` substring):** `.dm-content` is NOT a substring of any LIVE selector (`.dm-command-report-lane`/`.dm-command-report-items` diverge at char 6 — `…con t…` vs `…com m…`), and `.dm-nav-item` is NOT a substring of any live `.dm-*` (the live families are `-kicker/-replay-*/-hub-*/-command-report-*/-desktop-only/-mobile-only`), so the absent-substring assertions cannot false-positive against a surviving live rule. The "keeps the live non-shell" loop above pins that invariant explicitly.

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "legacyShellCss"`. Expected: FAIL (selectors still present).

- [ ] **Step 3: Delete the regions BOTTOM-UP** — work from the highest line number down so earlier offsets stay valid. **Deletion order (high→low line):** 8631 shared-720 P1-lines → 8562 app-boot → 7782 landing → 7600 broadcast-slash → 7571 court-floor `.app-shell` → **5193 720px block (remove only `.dm-app-shell.flex` 5194-5196 + `.dm-left-nav-logo` 5198-5200; KEEP `.dm-replay-controls` and all `.command-*`/`.dynasty-*`/`.standings-*`)** → **5063 960px block (remove the dm-shell rules 5064-5151; KEEP `.standings-*`/`.command-*` siblings)** → **4984 1180px block (remove only `.dm-left-nav` 4985-4987, `.dm-nav-item` 4989-4992, `.dm-content` 4994-4996; KEEP `.command-*`/`.dynasty-*` incl. `.dm-kicker`)** → 1190 dm-workspace/content → 1283 720px block (remove dm-shell rules 1284-1340; KEEP `.dm-hub-*`/`.dm-command-report-*`/`.dm-replay-*`/`.dm-desktop-only`/`.dm-mobile-only`) → 966 dm-nav → 360 main shell → 108 light-theme override. For every MIXED `@media` block (1283, 4984, 5063, 5193, plus the 8631 shared block), delete ONLY the dm-SHELL rule lines enumerated in the region table — never the wrapper `@media (…) { }` braces (each block keeps live siblings) — and re-confirm brace balance after each edit. Use a brace-depth sanity check after all deletions:

```bash
cd frontend
node -e "const s=require('fs').readFileSync('src/index.css','utf8');let d=0;for(const c of s){if(c==='{')d++;if(c==='}')d--;if(d<0){console.error('unbalanced');process.exit(1);}}console.log('brace depth',d);"
```
Expected: `brace depth 0`.

- [ ] **Step 4: Confirm no live consumer breaks** — grep that the deleted class names no longer appear in any `.tsx` (App/SaveMenu now use modules; the only remaining `.dm-left-nav` reference is `MatchWeek.tsx:334`, which is a stale no-op P2 rewrites — that line stays as-is in Phase 1, it just stops matching anything, exactly as before since `.dm-left-nav` was never the real class):

```bash
cd frontend && rg -n "className=\"[^\"]*\b(app-shell|left-nav|nav-item|broadcast-header|content-area|landing-shell|landing-card|landing-monogram|app-boot|court-pulse)\b" src/ || echo "no live consumers"
```
Expected: `no live consumers` (App/SaveMenu reference `styles.*` now). The bare `.dm-*` shell classes were already orphaned.

- [ ] **Step 5: Run the guard + build** — `cd frontend && npm run test -- "legacyShellCss" && npm run build`. Expected: guard PASSES; build succeeds (no dangling brace).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/index.css frontend/src/components/shell/legacyShellCss.test.ts
git commit -m "chore(css): delete legacy shell/landing/boot + dead dm-shell family (P1-owned)"
```

---

### Task 10: SCAN_DIRS append + full Phase-1 merge gate

> **Why:** The migrated `App.module.css` and `SaveMenu.module.css` now own their styling and must be held to token discipline. Strategy: the **integrator owns all `SCAN_DIRS` appends**. Then run the complete gate (build + lint + lint:tokens + full vitest + e2e smoke + pytest) before the STEP-1 merge.

**Files:** modify `frontend/scripts/check-tokens.mjs`.

- [ ] **Step 1: Append the migrated dirs** — in `check-tokens.mjs`, extend `SCAN_DIRS` so the shell modules are scanned. The shell CSS Modules live next to their `.tsx` in `src/` and `src/components/`, not a single dir, so add the specific files/dirs that Phase 1 migrated. Simplest correct change: add `'src'` is too broad (would flag un-migrated files); instead scan the two specific module files plus the shell contract dir. Update the walker to also accept explicit file entries:

```js
// SCAN_DIRS may contain dirs (walked) or explicit files (scanned as-is).
const SCAN_DIRS = ['src/ui', 'src/styles', 'src/components/shell'];
const SCAN_FILES = ['src/App.module.css', 'src/components/SaveMenu.module.css'];
```
and after the dir loop, scan `SCAN_FILES` through the same `HEX`/`PX`/`ALLOW` checks. (Keep `ALLOW_FILE`/`ALLOW_LINE` semantics from Phase 0; `.test.` files remain exempt, so `src/components/shell/*.test.ts(x)` are skipped automatically.)

- [ ] **Step 2: Run the token gate** — `cd frontend && npm run lint:tokens`. Expected: PASS (the shell modules use only `var(--…)` tokens + `0`/`1px`). If it flags a real literal in `App.module.css`/`SaveMenu.module.css`, replace it with a token (add a shell-specific semantic token to `src/styles/tokens.css` if no existing token fits — e.g. a nav-rail width var) and re-run. **Note:** the `--mono-hue` runtime club-color custom prop in `SaveMenu.module.css` is set via inline `style` in TSX (not a literal in CSS), so it does not trip the gate; if the monogram `color-mix` fallback hexes (e.g. `#475569`) land in the module CSS, replace them with a `--mono-fallback` token.

- [ ] **Step 3: Prove the gate covers the new dirs** — temporarily add `color: #ff0000;` to `App.module.css`, run `npm run lint:tokens`, confirm EXIT 1 naming the line, then revert and confirm PASS.

- [ ] **Step 4: Run the full Phase-1 merge gate**

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e
python -m pytest -q
```
Expected: all FE tests pass (incl. the 11 behavior cases + shim contracts + appContracts + skeleton freezes + legacyShellCss guard); build clean; eslint clean; token gate clean; root Playwright e2e smoke green; Python suite green (Phase 1 touched no payload contracts — the `#10` python-guard on `ruleset_selection` stays green).

- [ ] **Step 5: Manual smoke** — launch `python -m dodgeball_sim` on port 8010 (NOT 8000 — owner's live game), load an existing save, confirm: boot splash, nav rail (collapse/expand + keyboard), broadcast header (`Week 7` un-padded, offseason label), and the SaveMenu (Load list with a real record, incompatible archive toggle, New-Game tab, Build-from-Scratch → Identity step) all render correctly with the new look and no console errors.

- [ ] **Step 6: Commit + ready for STEP-1 merge**

```bash
git add frontend/scripts/check-tokens.mjs
git commit -m "build(fe): scan App + SaveMenu modules for token discipline (Phase 1 SCAN_DIRS)"
```

The controller performs the STEP-1 merge to trunk and re-gates before opening the concurrent window.

---

## Self-Review

**Behavior coverage — all 11 Phase-1 audit behaviors mapped to a task + test strategy:**

| # | Behavior | Task | Strategy |
|---|---|---|---|
| 9 | Save record W-L-D only when wins defined; never 0-0 | Task 7 | vitest (SaveMenu row) ✓ |
| 10 | `ruleset_selection` pinned `official_foam` at every create path | Task 8 | vitest + python-guard ✓ |
| 82 | Router trusts LIVE career state over post-sim `next_state` | Tasks 4, 5 | vitest (`classifyScreen` extraction unit test) ✓ |
| 83 | Offseason vs in-season classification → screen + header | Tasks 4, 6 | vitest ✓ |
| 84 | Season/week/year fallback precedence; post-sim week priority | Tasks 4, 6 | vitest (+ un-pad fix) ✓ |
| 85 | Incompatible saves hidden by default, non-loadable, labeled | Task 7 | vitest ✓ |
| 86 | Continue-career picks first non-incompatible non-debug save | Task 7 | vitest ✓ |
| 87 | Debug/test saves two-gate (`?debug=true` AND opt-in) | Task 8 | vitest ✓ |
| 88 | Active-tab persists to `?tab=` only in game/offseason, validated | Tasks 4, 5 | vitest ✓ |
| 89 | Save-state fetch failure falls back to menu | Task 4 | vitest ✓ |
| 91 | Launch-token guard surfaced (guard itself in client.ts/Phase-0 test) | Task 7 | vitest (surfaced banner) ✓ |

**Strategy Phase-1 items — all honored:** 5 `src/ui` shims (Task 1) ✓ · `data-nav-rail` (Tasks 2, 5) ✓ · compile-time MatchWeek-prop/`commandReplay` interface (Task 2) ✓ · P4 PlayoffBracket + P5 ProgramModal prop-stable skeletons on trunk — frozen via contract tests since both already exist (Task 3) ✓ · 4 `.app-shell` deletions + the FULL dead dm-shell family (`.dm-app-shell/.dm-left-nav(+-logo)/.dm-nav-item(+:hover/-active/-dot)/.dm-nav-label-short/.dm-nav-label-full/.dm-broadcast-header/.dm-workspace/.dm-content`) across base rules AND the four mixed `@media` blocks (1283, 4984, 5063, 5193) — each with an explicit per-block remove/keep list + bottom-up order + brace-balance check (Task 9) ✓ · `padStart` Week fix (Task 6) ✓ · integrator-owned SCAN_DIRS append (Task 10) ✓ · shared 720px `@media` — remove only P1's lines (Task 9, explicit keep-list) ✓.

**Freezes respected:** `matchResult.ts` not touched (the SaveMenu/shell never import it); `legibility/*` not touched; `components/ui.tsx` not edited (shims are new files in `src/ui`); `command-action-bar`/`command-policy-overlay` not deleted (P8-only); `MatchWeek.tsx:334` only gains a `data-nav-rail` target — P2 rewrites the `closest()`; wizard step components untouched (Phase 7 owns them) ✓.

**Placeholder scan:** none. Every task has runnable test code + concrete edits. The two "judgment-call" notes are correctness guards, not placeholders: (a) Task 4 flags that #82's end-to-end advance path is behind a stubbed `MatchWeek`, and resolves it by extracting + unit-testing `classifyScreen` (the single source both the load path and `onAdvanceWeek` use) — this is a real, testable de-duplication, not a stub; (b) Task 8 leaves the club-picker `RadioGroup` import as `./ui` OR re-points to the `../ui` shim, both acceptable for the solo lane (the test holds either way). Both are stated explicitly.

**Type/name consistency:** shim signatures are quoted verbatim from `ui.tsx` (`ActionButton` variant union `'primary'|'accent'|'secondary'|'danger'|'ghost'`; `StatusMessage` `role?: 'status'|'alert'` with the `danger||warning→alert` derivation; `RatingBar` `{rating,max?,label?,compact?,explanation?}` + `data-testid="rating-explanation"`; `RadioGroup<T extends string>` render-prop with `radioProps`). `MatchWeekMountProps` is asserted field-by-field against the LIVE `ComponentProps<typeof MatchWeek>` (named import from `../MatchWeek`) — plus a whole-bag `toMatchTypeOf` assignability check — so the contract fails the build if `MatchWeek.tsx:146-165` drifts; the only hardcoded literal left is a canary anchoring the live `mode` to `'pre-sim'|'post-sim'|'offseason'`. `CommandReplayState = MatchReplayResponse | null` matches `App.tsx:48`; `NAV_RAIL_ATTR = 'data-nav-rail'` matches the `MatchWeek.tsx:334` rewrite target. `PlayoffBracket` `{ data: PlayoffBracketResponse }` and `ProgramModal` `{ clubId, clubName, onClose }` match the on-trunk sources. Test data-testids (`save-item`, `continue-career-hero`, `load-save-btn`, `toggle-incompatible`, `new-game-tab`, `create-save-btn`, `save-name-input`, `ruleset-standard-card`) are quoted from `SaveMenu.tsx`.

**Gate correctness:** the e2e gate is `npm run e2e` from repo ROOT (root Playwright, per AGENTS.md) — there is no `frontend` e2e script; the plan's merge gate uses the root command. `expectTypeOf`/`toMatchTypeOf` are part of Vitest (no new dep). The `appContracts` drift test ties `MatchWeekMountProps` to the LIVE `ComponentProps<typeof MatchWeek>` (named import from `../MatchWeek`), so the build fails if MatchWeek's prop surface drifts — the contract can no longer pass a hardcoded union that diverged from the component. Token gate scope is widened only via the integrator-owned `SCAN_DIRS`/`SCAN_FILES` append (Task 10), so shell-module token violations surface at the merge gate and each reskin task pre-empts them by using tokens from the start.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-floodlight-phase-1-app-shell.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task (1→10), review between tasks. Task 1 (shims) and Task 9 (CSS deletion) are the highest-blast-radius; gate hard after each.
2. **Inline Execution** — execute tasks in this session with checkpoints. Do NOT merge until Task 10's full gate (incl. root e2e + pytest) is green; the controller owns the STEP-1 merge.
