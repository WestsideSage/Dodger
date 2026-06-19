# Floodlight Phase 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Floodlight foundation — design tokens, a primitives library, a frontend test harness, and the data/format consolidations — so later phases can reskin all 73 screens against a single system without regressing the 97-behavior trust contract. **No screen is rewritten in this plan.**

**Architecture:** One token source (`src/styles/tokens.css`) + scoped CSS-Module primitives in `src/ui/`, tested with Vitest + React Testing Library. Existing `components/ui.tsx` primitives are migrated in place to tokens (keeping their a11y behavior). Tailwind is removed in a controlled pass. A token-discipline lint gate guards new code.

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (new), @fontsource self-hosted fonts (new).

**Spec:** [2026-06-19-ui-redesign-design.md](../specs/2026-06-19-ui-redesign-design.md) · **Non-regression contract:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md)

**Branch:** `feature/floodlight-redesign` (already created). All commits land here.

---

## File map (created/modified in this plan)

- Create: `frontend/src/test/setup.ts`, `frontend/src/test/smoke.test.tsx`
- Create: `frontend/src/styles/tokens.css`, `frontend/src/styles/tokens.test.ts`
- Create: `frontend/src/ui/{Truncate,Surface,Grid,ScrollRegion,Tag,RecordCell,Popover,Modal,ActionBar,Table}.tsx` (+ `.module.css` + `.test.tsx` each) and `frontend/src/ui/index.ts`
- Create: `frontend/src/domain/tiers.ts` (+ `tiers.test.ts`)
- Create: `frontend/scripts/check-tokens.mjs`
- Create: `docs/superpowers/plans/floodlight-preservation-checklist.md`
- Modify: `frontend/package.json` (devDeps + scripts), `frontend/vite.config.ts` (vitest config; later tailwind removal), `frontend/src/main.tsx` (import tokens + fonts), `frontend/src/api/client.ts` (wizard endpoints), `frontend/src/components/ui.tsx` (re-point to tokens / re-export Modal), `frontend/src/index.css` (remove tailwind import; convert `@theme`)
- Modify (wizard, data-layer only — NOT a visual reskin): `frontend/src/components/new-game/StaffHiringStep.tsx`, `StartingRecruitmentStep.tsx` (use `saveApi` instead of raw `fetch`)

---

## Phase 0A — Contract capture

### Task 1: Author the preservation checklist (the executable non-regression map)

**Files:**
- Create: `docs/superpowers/plans/floodlight-preservation-checklist.md`

- [ ] **Step 1: Create the checklist file** mapping every audit §2 behavior (#1–#97) to the phase that will rebuild its surface and the test strategy that will prove it. Use this exact structure and content:

```markdown
# Floodlight Preservation Checklist (audit §2 → phase → test)

Source of truth: ../specs/2026-06-19-ui-redesign-audit.md §2 (97 behaviors).
Rule: a phase may not be marked done until every behavior assigned to it is green
by its listed test strategy. Test strategy ∈ {python-guard, vitest, e2e, manual-proof}.

## Phase 1 — App shell + SaveMenu
| # | Behavior (short) | Test strategy |
|---|---|---|
| 9 | Save-list record W-L-D only when wins defined; never fabricated 0-0 | vitest (SaveMenu row) |
| 10 | ruleset_selection pinned 'official_foam' at every create path | vitest + python-guard |
| 82 | Router trusts LIVE career state over post-sim next_state | vitest (App router) |
| 83 | Offseason vs in-season classification drives screen + header | vitest |
| 84 | Season/week/year fallback precedence; post-sim week priority | vitest |
| 85 | Incompatible saves hidden by default, non-loadable, labeled | vitest |
| 86 | Continue-career picks first non-incompatible non-debug save | vitest |
| 87 | Debug/test saves two-gate (?debug=true AND opt-in) | vitest |
| 88 | Active-tab persists to ?tab= only in game/offseason, validated | vitest |
| 89 | Save-state fetch failure falls back to menu, not broken shell | vitest |
| 91 | Launch-token guard: stale 403 refresh-retry vs business 403 verbatim | vitest (client.ts) |

## Phase 2 — Command loop + aftermath + replay
| # | Behavior (short) | Test strategy |
|---|---|---|
| 1–8 | V20 scoring-model family (formatScoreline/survivorDetail, wire, hero, strip, standings, bracket, recap) | vitest + python-guard |
| 11–18 | Playoff/draw/outcome truth (decided_by, draw label, verdict fallback, worlds_user, missed_playoffs) | vitest |
| 41–50 | Replay integrity (live-state eliminations, fresh-court, segment reveal, turning point, highlights map) | vitest + e2e |
| 90, 93–95 | Optimistic policy rollback; FALLBACK_BRIEFING; plan alignment; recent-results/stakes | vitest |

## Phases 3–8 — assigned by area (each phase's own plan finalizes per-item test strategy)
- Phase 3 Roster/lineup/player: #36, #51–#58
- Phase 4 Standings/league: #6, #7, #15, #16, #33, #34, #38, #96
- Phase 5 Dynasty/recruiting/history: #19–#28, #30, #59–#66, #97
- Phase 6 Ceremonies/offseason: #17, #18, #29, #31, #32, #35, #67–#75
- Phase 7 New-game wizard: #22, #76–#81
- Phase 8 Sweep (legibility primitives + responsive/a11y): #20, #21, #23–#27, #30, #37, #39, #40
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/plans/floodlight-preservation-checklist.md
git commit -m "docs(plan): Floodlight preservation checklist (audit behaviors -> phase -> test)"
```

---

## Phase 0B — Foundations

### Task 2: Frontend test harness (Vitest + React Testing Library)

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/test/setup.ts`, `frontend/src/test/smoke.test.tsx`

- [ ] **Step 1: Write the smoke test**

```tsx
// frontend/src/test/smoke.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

function Hello() { return <p>floodlight</p>; }

describe('test harness', () => {
  it('renders a component', () => {
    render(<Hello />);
    expect(screen.getByText('floodlight')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run it to verify it fails (no runner yet)**

Run: `cd frontend && npm run test`
Expected: FAIL — `test` script / `vitest` not found.

- [ ] **Step 3: Install deps and wire config**

```bash
cd frontend && npm install -D vitest@^3 jsdom@^25 @testing-library/react@^16 @testing-library/jest-dom@^6 @testing-library/user-event@^14
```

Add to `frontend/package.json` `"scripts"`:
```json
"test": "vitest run",
"test:watch": "vitest"
```

Create `frontend/src/test/setup.ts`:
```ts
import '@testing-library/jest-dom';
```

Replace `frontend/vite.config.ts` with (keeps the existing react+tailwind plugins and proxy; adds the test block; tailwind is removed later in Task 16):
```ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const apiPort = Number(process.env.DODGEBALL_API_PORT ?? 8000)
const appPort = Number(process.env.DODGEBALL_APP_PORT ?? 5173)

export default defineConfig({
  plugins: [tailwindcss(), react()],
  server: {
    host: '127.0.0.1',
    port: appPort,
    strictPort: true,
    proxy: { '/api': `http://127.0.0.1:${apiPort}` },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/test/
git commit -m "test(fe): add Vitest + React Testing Library harness"
```

---

### Task 3: Design tokens + base reset + self-hosted fonts

**Files:**
- Create: `frontend/src/styles/tokens.css`, `frontend/src/styles/tokens.test.ts`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/package.json` (font deps)

- [ ] **Step 1: Write the token-presence test**

```ts
// frontend/src/styles/tokens.test.ts
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';

const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), 'tokens.css'), 'utf8');

describe('floodlight tokens', () => {
  for (const name of [
    '--court', '--raise', '--raise2', '--line', '--line2', '--lit',
    '--text', '--text2', '--muted', '--out',
    '--volt', '--volt2', '--ok', '--gold', '--gold2',
    '--font-disp', '--font-head', '--font-ui', '--font-mono', '--font-serif',
    '--space-3', '--radius-lg',
  ]) {
    it(`defines ${name}`, () => { expect(css).toContain(`${name}:`); });
  }
  it('contains a base reset (box-sizing)', () => { expect(css).toContain('box-sizing'); });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- tokens`
Expected: FAIL — `tokens.css` does not exist.

- [ ] **Step 3: Create `frontend/src/styles/tokens.css`**

```css
:root {
  /* canvas & surfaces (warm graphite) */
  --court: #121110; --raise: #1b1915; --raise2: #211e18;
  --line: rgba(241,236,226,.08); --line2: rgba(241,236,226,.15); --lit: rgba(255,251,242,.16);
  /* text */
  --text: #F1ECE1; --text2: #C3BBAD; --muted: #9A9285; --out: #8E8678;
  /* role colors (the 5-color contract) */
  --volt: #FF4A2B; --volt2: #FF6A48; --volt-soft: rgba(255,74,43,.10);
  --ok: #54B98E; --ok-soft: rgba(84,185,142,.13);
  --gold: #F2B23C; --gold2: #FFD27A; --gold-soft: rgba(242,178,60,.14);
  /* legacy (archive screens only) */
  --legacy-paper: #F3EBD8; --legacy-ink: #211C16; --legacy-brick: #B4452F;
  /* type */
  --font-disp: 'Archivo Expanded','Archivo',system-ui,sans-serif;
  --font-head: 'Archivo',system-ui,sans-serif;
  --font-ui: 'Geist','Segoe UI',system-ui,sans-serif;
  --font-mono: 'Geist Mono','JetBrains Mono',ui-monospace,monospace;
  --font-serif: 'Fraunces',Georgia,serif;
  /* spacing scale */
  --space-1:2px; --space-2:4px; --space-3:8px; --space-4:12px; --space-5:16px;
  --space-6:20px; --space-7:24px; --space-8:32px; --space-9:40px;
  /* radius & elevation */
  --radius-sm:6px; --radius-md:9px; --radius-lg:12px; --radius-xl:16px;
  --shadow-1: 0 10px 28px -16px rgba(0,0,0,.7);
  --shadow-2: 0 24px 50px -28px rgba(0,0,0,.85);
}

/* base reset (replaces Tailwind preflight; removed-Tailwind-safe) */
*, *::before, *::after { box-sizing: border-box; }
html, body, #root { margin: 0; height: 100%; }
body {
  background: var(--court);
  color: var(--text);
  font-family: var(--font-ui);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .001ms !important; transition-duration: .001ms !important; }
}
```

- [ ] **Step 4: Self-host fonts and import tokens**

```bash
cd frontend && npm install @fontsource-variable/archivo @fontsource-variable/fraunces @fontsource/geist-sans @fontsource/geist-mono
# If any package name 404s, confirm with: npm view <name> version  (e.g. geist font may publish as `geist`)
```

Add to the TOP of `frontend/src/main.tsx` (before the existing `import './index.css'`):
```ts
import '@fontsource-variable/archivo';
import '@fontsource-variable/fraunces';
import '@fontsource/geist-sans';
import '@fontsource/geist-mono';
import './styles/tokens.css';
```

- [ ] **Step 5: Run tokens test + build**

Run: `cd frontend && npm run test -- tokens && npm run build`
Expected: tokens tests PASS; build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/styles/ frontend/src/main.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(fe): Floodlight design tokens, base reset, self-hosted fonts"
```

---

### Task 4: `Truncate` primitive

**Files:**
- Create: `frontend/src/ui/Truncate.tsx`, `Truncate.module.css`, `Truncate.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/Truncate.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Truncate } from './Truncate';

describe('Truncate', () => {
  it('renders children and forwards data-* + title', () => {
    render(<Truncate title="full" data-testid="t">A very long club name</Truncate>);
    const el = screen.getByTestId('t');
    expect(el).toHaveTextContent('A very long club name');
    expect(el).toHaveAttribute('title', 'full');
  });
  it('renders as the requested element', () => {
    render(<Truncate as="h3" data-testid="h">Heading</Truncate>);
    expect(screen.getByTestId('h').tagName).toBe('H3');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- Truncate`
Expected: FAIL — cannot resolve `./Truncate`.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/Truncate.module.css */
.truncate { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```
```tsx
// frontend/src/ui/Truncate.tsx
import type { ElementType, HTMLAttributes, ReactNode } from 'react';
import styles from './Truncate.module.css';

interface TruncateProps extends HTMLAttributes<HTMLElement> {
  as?: ElementType;
  children: ReactNode;
}

export function Truncate({ as: Tag = 'span', className = '', children, ...rest }: TruncateProps) {
  return <Tag className={`${styles.truncate} ${className}`.trim()} {...rest}>{children}</Tag>;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- Truncate`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/Truncate.*
git commit -m "feat(ui): Truncate primitive (kills overflow bug pattern P2)"
```

---

### Task 5: `Surface` (+ `Card`) primitive

**Files:**
- Create: `frontend/src/ui/Surface.tsx`, `Surface.module.css`, `Surface.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/Surface.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Surface, Card } from './Surface';

describe('Surface', () => {
  it('applies an elevation class and forwards data-*', () => {
    render(<Surface elevation={2} data-testid="s">x</Surface>);
    expect(screen.getByTestId('s').className).toMatch(/e2/);
  });
  it('Card is a padded surface that forwards role/aria', () => {
    render(<Card role="group" aria-label="card" data-testid="c">x</Card>);
    const el = screen.getByTestId('c');
    expect(el).toHaveAttribute('role', 'group');
    expect(el).toHaveAttribute('aria-label', 'card');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- Surface`
Expected: FAIL — cannot resolve `./Surface`.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/Surface.module.css */
.surface { border: 1px solid var(--line); border-top-color: var(--lit); border-radius: var(--radius-lg); }
.e0 { background: var(--court); }
.e1 { background: var(--raise); box-shadow: var(--shadow-1); }
.e2 { background: var(--raise2); box-shadow: var(--shadow-2); }
.card { padding: var(--space-5); }
```
```tsx
// frontend/src/ui/Surface.tsx
import type { ElementType, HTMLAttributes, ReactNode } from 'react';
import styles from './Surface.module.css';

interface SurfaceProps extends HTMLAttributes<HTMLDivElement> {
  elevation?: 0 | 1 | 2;
  as?: ElementType;
  children: ReactNode;
}

export function Surface({ elevation = 1, as: Tag = 'div', className = '', children, ...rest }: SurfaceProps) {
  return (
    <Tag className={`${styles.surface} ${styles['e' + elevation]} ${className}`.trim()} {...rest}>
      {children}
    </Tag>
  );
}

export function Card({ className = '', children, ...rest }: SurfaceProps) {
  return <Surface className={`${styles.card} ${className}`.trim()} {...rest}>{children}</Surface>;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- Surface`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/Surface.*
git commit -m "feat(ui): Surface/Card primitive (token-driven elevation, kills P1)"
```

---

### Task 6: `Grid` primitive (responsive auto-collapse)

**Files:**
- Create: `frontend/src/ui/Grid.tsx`, `Grid.module.css`, `Grid.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/Grid.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Grid } from './Grid';

describe('Grid', () => {
  it('sets the --grid-min custom property and forwards data-*', () => {
    render(<Grid min="200px" data-testid="g"><span>a</span></Grid>);
    const el = screen.getByTestId('g');
    expect(el.style.getPropertyValue('--grid-min')).toBe('200px');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- Grid`
Expected: FAIL — cannot resolve `./Grid`.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/Grid.module.css */
.grid {
  display: grid;
  /* min() guard => columns never exceed the container => never overflows (kills P3/P10) */
  grid-template-columns: repeat(auto-fill, minmax(min(var(--grid-min, 240px), 100%), 1fr));
  gap: var(--grid-gap, var(--space-4));
}
```
```tsx
// frontend/src/ui/Grid.tsx
import type { CSSProperties, HTMLAttributes, ReactNode } from 'react';
import styles from './Grid.module.css';

interface GridProps extends HTMLAttributes<HTMLDivElement> {
  min?: string;
  gap?: string;
  children: ReactNode;
}

export function Grid({ min = '240px', gap, className = '', style, children, ...rest }: GridProps) {
  const vars = { '--grid-min': min, ...(gap ? { '--grid-gap': gap } : {}) } as CSSProperties;
  return (
    <div className={`${styles.grid} ${className}`.trim()} style={{ ...vars, ...style }} {...rest}>
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- Grid`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/Grid.*
git commit -m "feat(ui): responsive Grid primitive (kills fixed-column overflow P3/P10)"
```

---

### Task 7: `ScrollRegion` primitive

**Files:**
- Create: `frontend/src/ui/ScrollRegion.tsx`, `ScrollRegion.module.css`, `ScrollRegion.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/ScrollRegion.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ScrollRegion } from './ScrollRegion';

describe('ScrollRegion', () => {
  it('applies maxHeight and forwards data-*', () => {
    render(<ScrollRegion maxHeight="200px" data-testid="r"><div>tall</div></ScrollRegion>);
    expect(screen.getByTestId('r').style.maxHeight).toBe('200px');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- ScrollRegion`
Expected: FAIL — cannot resolve `./ScrollRegion`.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/ScrollRegion.module.css */
/* min-height:0 lets a flex child actually scroll instead of overflowing its parent (kills P4). */
.scroll { overflow: auto; min-height: 0; }
```
```tsx
// frontend/src/ui/ScrollRegion.tsx
import type { HTMLAttributes, ReactNode } from 'react';
import styles from './ScrollRegion.module.css';

interface ScrollRegionProps extends HTMLAttributes<HTMLDivElement> {
  /** Constrain height here OR let a flex parent constrain it; never both nested. */
  maxHeight?: string;
  children: ReactNode;
}

export function ScrollRegion({ maxHeight, className = '', style, children, ...rest }: ScrollRegionProps) {
  return (
    <div className={`${styles.scroll} ${className}`.trim()} style={{ maxHeight, ...style }} {...rest}>
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- ScrollRegion`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/ScrollRegion.*
git commit -m "feat(ui): ScrollRegion primitive (kills nested off-screen scroll P4)"
```

---

### Task 8: `Tag` + `RecordCell` primitives

**Files:**
- Create: `frontend/src/ui/Tag.tsx`, `Tag.module.css`, `Tag.test.tsx`
- Create: `frontend/src/ui/RecordCell.tsx`, `RecordCell.module.css`, `RecordCell.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/ui/Tag.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Tag } from './Tag';

describe('Tag', () => {
  it('applies the tone class and forwards data-*', () => {
    render(<Tag tone="verified" data-testid="t">Healthy</Tag>);
    expect(screen.getByTestId('t').className).toMatch(/verified/);
  });
});
```
```tsx
// frontend/src/ui/RecordCell.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecordCell } from './RecordCell';

describe('RecordCell', () => {
  it('renders an atomic W–L record', () => {
    render(<RecordCell wins={7} losses={2} data-testid="r" />);
    expect(screen.getByTestId('r')).toHaveTextContent('7–2');
  });
  it('includes draws when provided', () => {
    render(<RecordCell wins={7} losses={2} draws={1} data-testid="r" />);
    expect(screen.getByTestId('r')).toHaveTextContent('7–2–1');
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd frontend && npm run test -- Tag RecordCell`
Expected: FAIL — modules unresolved.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/Tag.module.css */
.tag { font: 600 .6rem var(--font-ui); padding: 2px 7px; border-radius: var(--radius-sm); white-space: nowrap; }
.live { color: var(--volt2); background: var(--volt-soft); }
.verified { color: var(--ok); background: var(--ok-soft); }
.talent { color: #1a1407; background: linear-gradient(95deg,var(--gold),var(--gold2)); }
.out { color: var(--out); border: 1px solid rgba(142,134,120,.45); }
.neutral { color: var(--text2); background: rgba(255,255,255,.05); }
```
```tsx
// frontend/src/ui/Tag.tsx
import type { HTMLAttributes, ReactNode } from 'react';
import styles from './Tag.module.css';

export type TagTone = 'live' | 'verified' | 'talent' | 'out' | 'neutral';

interface TagProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: TagTone;
  children: ReactNode;
}

export function Tag({ tone = 'neutral', className = '', children, ...rest }: TagProps) {
  return <span className={`${styles.tag} ${styles[tone]} ${className}`.trim()} {...rest}>{children}</span>;
}
```
```css
/* frontend/src/ui/RecordCell.module.css */
.record { font-family: var(--font-mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
```
```tsx
// frontend/src/ui/RecordCell.tsx
import type { HTMLAttributes } from 'react';
import styles from './RecordCell.module.css';

interface RecordCellProps extends HTMLAttributes<HTMLSpanElement> {
  wins: number;
  losses: number;
  draws?: number;
}

export function RecordCell({ wins, losses, draws, className = '', ...rest }: RecordCellProps) {
  const text = draws != null ? `${wins}–${losses}–${draws}` : `${wins}–${losses}`;
  return <span className={`${styles.record} ${className}`.trim()} {...rest}>{text}</span>;
}
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd frontend && npm run test -- Tag RecordCell`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/Tag.* frontend/src/ui/RecordCell.*
git commit -m "feat(ui): Tag + atomic RecordCell primitives"
```

---

### Task 9: `Popover` primitive (portal + edge-flip)

**Files:**
- Create: `frontend/src/ui/Popover.tsx`, `Popover.module.css`, `Popover.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/Popover.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Popover } from './Popover';

describe('Popover', () => {
  it('renders content in a portal when open and forwards data-*/role', () => {
    render(
      <Popover open anchor={<button>open</button>} data-testid="pop" role="tooltip">
        receipt body
      </Popover>,
    );
    const pop = screen.getByTestId('pop');
    expect(pop).toHaveTextContent('receipt body');
    expect(pop).toHaveAttribute('role', 'tooltip');
  });
  it('renders nothing when closed', () => {
    render(<Popover open={false} anchor={<button>open</button>}>hidden</Popover>);
    expect(screen.queryByText('hidden')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- Popover`
Expected: FAIL — cannot resolve `./Popover`.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/Popover.module.css */
.pop {
  position: fixed; z-index: 1200; max-width: min(22rem, calc(100vw - 16px));
  background: var(--raise2); color: var(--text2); border: 1px solid var(--line2);
  border-radius: var(--radius-md); padding: var(--space-4); box-shadow: var(--shadow-2);
  font: 400 .8rem var(--font-ui);
}
```
```tsx
// frontend/src/ui/Popover.tsx
import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { HTMLAttributes, ReactNode } from 'react';
import styles from './Popover.module.css';

interface PopoverProps extends HTMLAttributes<HTMLDivElement> {
  open: boolean;
  anchor: ReactNode;
  children: ReactNode;
}

export function Popover({ open, anchor, className = '', children, ...rest }: PopoverProps) {
  const anchorRef = useRef<HTMLSpanElement>(null);
  const popRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!open || !anchorRef.current || !popRef.current) return;
    const a = anchorRef.current.getBoundingClientRect();
    const p = popRef.current.getBoundingClientRect();
    const margin = 8;
    // default: below + left-aligned; flip up / clamp horizontally if it would overflow
    let top = a.bottom + 6;
    if (top + p.height > window.innerHeight - margin) top = Math.max(margin, a.top - p.height - 6);
    let left = a.left;
    if (left + p.width > window.innerWidth - margin) left = Math.max(margin, window.innerWidth - margin - p.width);
    setPos({ top, left });
  }, [open]);

  return (
    <>
      <span ref={anchorRef} style={{ display: 'inline-flex' }}>{anchor}</span>
      {open && createPortal(
        <div
          ref={popRef}
          className={`${styles.pop} ${className}`.trim()}
          style={{ top: pos.top, left: pos.left }}
          {...rest}
        >
          {children}
        </div>,
        document.body,
      )}
    </>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- Popover`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/Popover.*
git commit -m "feat(ui): portal Popover with edge-flip (kills clipped/off-screen popovers P5)"
```

---

### Task 10: `Modal` primitive (port `Dialog` to tokens, keep focus-trap)

**Files:**
- Create: `frontend/src/ui/Modal.tsx`, `Modal.module.css`, `Modal.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/Modal.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { Modal } from './Modal';

describe('Modal', () => {
  it('renders a labelled dialog and forwards data-testid (anti-strip)', () => {
    render(<Modal onClose={() => {}} label="Settings" data-testid="m"><button>ok</button></Modal>);
    const dlg = screen.getByRole('dialog');
    expect(dlg).toHaveAttribute('aria-label', 'Settings');
    expect(screen.getByTestId('m')).toBeInTheDocument();
  });
  it('closes on Escape', async () => {
    const onClose = vi.fn();
    render(<Modal onClose={onClose} label="x"><button>ok</button></Modal>);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- Modal`
Expected: FAIL — cannot resolve `./Modal`.

- [ ] **Step 3: Implement** — port the proven focus-trap from `components/ui.tsx` `Dialog` (lines 462-574) into a token-styled CSS Module. Forward `data-*` onto the overlay.

```css
/* frontend/src/ui/Modal.module.css */
.overlay {
  position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center;
  padding: var(--space-7); background: rgba(8,7,5,.78); backdrop-filter: blur(4px);
}
.panel {
  background: var(--raise); border: 1px solid var(--line); border-top-color: var(--lit);
  border-radius: var(--radius-xl); width: min(92vw, 34rem); max-height: calc(100vh - 4rem);
  overflow: auto; box-shadow: var(--shadow-2);
}
```
```tsx
// frontend/src/ui/Modal.tsx
import { useEffect, useRef } from 'react';
import type { HTMLAttributes, KeyboardEvent, ReactNode, RefObject } from 'react';
import styles from './Modal.module.css';

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  onClose: () => void;
  children: ReactNode;
  label?: string;
  labelledBy?: string;
  describedBy?: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
  panelClassName?: string;
}

export function Modal({
  onClose, children, label, labelledBy, describedBy, initialFocusRef,
  className = '', panelClassName = '', ...rest
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    const target =
      initialFocusRef?.current ??
      dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE) ??
      dialogRef.current;
    target?.focus?.();
    return () => { previouslyFocused.current?.focus?.(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') { e.stopPropagation(); onClose(); return; }
    if (e.key !== 'Tab') return;
    const f = dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE);
    if (!f || f.length === 0) { e.preventDefault(); dialogRef.current?.focus(); return; }
    const first = f[0], last = f[f.length - 1], active = document.activeElement;
    if (e.shiftKey && active === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
  };

  return (
    <div className={`${styles.overlay} ${className}`.trim()} role="presentation" onClick={onClose} {...rest}>
      <div
        ref={dialogRef}
        className={`${styles.panel} ${panelClassName}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-label={labelledBy ? undefined : label}
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
      >
        {children}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- Modal`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/Modal.*
git commit -m "feat(ui): Modal primitive (tokenized focus-trap dialog, kills P4/P8)"
```

---

### Task 11: `ActionBar` primitive

**Files:**
- Create: `frontend/src/ui/ActionBar.tsx`, `ActionBar.module.css`, `ActionBar.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/ActionBar.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ActionBar } from './ActionBar';

describe('ActionBar', () => {
  it('renders actions and forwards data-*', () => {
    render(<ActionBar data-testid="bar"><button>Next</button></ActionBar>);
    expect(screen.getByTestId('bar')).toHaveTextContent('Next');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- ActionBar`
Expected: FAIL — cannot resolve `./ActionBar`.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/ActionBar.module.css */
.bar {
  position: sticky; bottom: 0; display: flex; flex-wrap: wrap; gap: var(--space-3);
  justify-content: flex-end; align-items: center;
  padding: var(--space-4); padding-bottom: max(var(--space-4), env(safe-area-inset-bottom));
  background: linear-gradient(0deg, var(--court), transparent); border-top: 1px solid var(--line);
}
```
```tsx
// frontend/src/ui/ActionBar.tsx
import type { HTMLAttributes, ReactNode } from 'react';
import styles from './ActionBar.module.css';

interface ActionBarProps extends HTMLAttributes<HTMLDivElement> { children: ReactNode; }

export function ActionBar({ className = '', children, ...rest }: ActionBarProps) {
  return <div className={`${styles.bar} ${className}`.trim()} {...rest}>{children}</div>;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- ActionBar`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/ActionBar.*
git commit -m "feat(ui): sticky ActionBar primitive (kills P5 action-bar variants)"
```

---

### Task 12: `Table` primitive (+ density, tabular, attribute forwarding)

**Files:**
- Create: `frontend/src/ui/Table.tsx`, `Table.module.css`, `Table.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/Table.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Table } from './Table';

describe('Table', () => {
  it('applies density class and forwards data-* (anti-strip)', () => {
    render(
      <Table density="compact" data-testid="tbl">
        <tbody><tr><td>Granite City Hammers</td></tr></tbody>
      </Table>,
    );
    const t = screen.getByTestId('tbl');
    expect(t.tagName).toBe('TABLE');
    expect(t.className).toMatch(/compact/);
    expect(t).toHaveTextContent('Granite City Hammers');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- Table`
Expected: FAIL — cannot resolve `./Table`.

- [ ] **Step 3: Implement**

```css
/* frontend/src/ui/Table.module.css */
.wrap { overflow-x: auto; }
.t { width: 100%; border-collapse: collapse; }
.t :global(th) {
  font: 600 .62rem var(--font-ui); letter-spacing: .06em; text-transform: uppercase;
  color: var(--muted); text-align: left; padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--line2); white-space: nowrap;
}
.t :global(td) {
  padding: var(--space-4); border-bottom: 1px solid var(--line);
  font: 500 .82rem var(--font-ui); color: var(--text2);
}
.t :global(td.num), .t :global(th.num) {
  text-align: right; font-family: var(--font-mono); font-variant-numeric: tabular-nums; color: var(--text);
}
.compact :global(th) { padding: var(--space-2) var(--space-4); }
.compact :global(td) { padding: var(--space-2) var(--space-4); font-size: .79rem; }
```
```tsx
// frontend/src/ui/Table.tsx
import type { HTMLAttributes, ReactNode } from 'react';
import styles from './Table.module.css';

interface TableProps extends HTMLAttributes<HTMLTableElement> {
  density?: 'comfortable' | 'compact';
  children: ReactNode;
}

export function Table({ density = 'comfortable', className = '', children, ...rest }: TableProps) {
  return (
    <div className={styles.wrap}>
      <table className={`${styles.t} ${styles[density]} ${className}`.trim()} {...rest}>{children}</table>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- Table`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/Table.*
git commit -m "feat(ui): Table primitive with density + tabular numerics"
```

---

### Task 13: Barrel export + smoke-mount all primitives

**Files:**
- Create: `frontend/src/ui/index.ts`, `frontend/src/ui/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/index.test.tsx
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import * as UI from './index';
import { Popover } from './index';

describe('ui barrel', () => {
  it('exports every primitive', () => {
    for (const name of ['Truncate','Surface','Card','Grid','ScrollRegion','Tag','RecordCell','Popover','Modal','ActionBar','Table']) {
      expect(UI).toHaveProperty(name);
    }
  });
  it('a representative primitive mounts', () => {
    const { container } = render(<Popover open={false} anchor={<button>x</button>}>y</Popover>);
    expect(container).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- "ui/index"`
Expected: FAIL — cannot resolve `./index`.

- [ ] **Step 3: Implement**

```ts
// frontend/src/ui/index.ts
export { Truncate } from './Truncate';
export { Surface, Card } from './Surface';
export { Grid } from './Grid';
export { ScrollRegion } from './ScrollRegion';
export { Tag } from './Tag';
export type { TagTone } from './Tag';
export { RecordCell } from './RecordCell';
export { Popover } from './Popover';
export { Modal } from './Modal';
export { ActionBar } from './ActionBar';
export { Table } from './Table';
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- "ui/index"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ui/index.*
git commit -m "feat(ui): Floodlight primitives barrel"
```

---

### Task 14: Consolidate wizard `fetch()` into `api/client.ts`

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/new-game/StaffHiringStep.tsx`, `StartingRecruitmentStep.tsx`
- Create: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/api/client.test.ts
import { describe, it, expect, vi, afterEach } from 'vitest';
import { saveApi } from './client';

afterEach(() => vi.restoreAllMocks());

describe('saveApi wizard endpoints', () => {
  it('startingStaff calls the seeded endpoint via the client', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ departments: [] }), { status: 200 }),
    );
    await saveApi.startingStaff(123);
    expect(spy).toHaveBeenCalledWith('/api/saves/starting-staff?seed=123', undefined);
  });
  it('startingProspects calls the seeded endpoint via the client', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ prospects: [] }), { status: 200 }),
    );
    await saveApi.startingProspects(123);
    expect(spy).toHaveBeenCalledWith('/api/saves/starting-prospects?seed=123', undefined);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- "api/client"`
Expected: FAIL — `saveApi.startingStaff` is not a function.

- [ ] **Step 3: Add the methods** to `saveApi` in `frontend/src/api/client.ts` (insert before the closing `};` of the `saveApi` object, after `buildFromScratch`):

```ts
  // V22 wizard data — folded in from raw fetch() so the launch-token guard +
  // error semantics (ApiError) cover them uniformly (audit §2.J #91, §5.7).
  startingStaff: (seed: number) =>
    apiGet<import('../types').StartingStaffResponse>(`/api/saves/starting-staff?seed=${seed}`),
  startingProspects: (seed: number) =>
    apiGet<import('../types').StartingProspectsResponse>(`/api/saves/starting-prospects?seed=${seed}`),
```

If `StartingStaffResponse` / `StartingProspectsResponse` are not yet exported from `types.ts`, replace each with the inline response type the wizard step currently declares for its raw `fetch` (read the exact shape from `StaffHiringStep.tsx` / `StartingRecruitmentStep.tsx` before writing — do not invent fields).

- [ ] **Step 4: Re-point the wizard steps** — in `StaffHiringStep.tsx` and `StartingRecruitmentStep.tsx`, replace the raw `fetch('/api/saves/starting-staff?seed=...')` / `fetch('/api/saves/starting-prospects?seed=...')` calls with `saveApi.startingStaff(seed)` / `saveApi.startingProspects(seed)` (import `saveApi` from `../../api/client`). This is a data-layer swap only — leave the components' markup/styles untouched (they are reskinned in Phase 7).

- [ ] **Step 5: Run tests + build**

Run: `cd frontend && npm run test -- "api/client" && npm run build`
Expected: PASS + build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/client.* frontend/src/components/new-game/StaffHiringStep.tsx frontend/src/components/new-game/StartingRecruitmentStep.tsx
git commit -m "refactor(fe): route wizard staff/prospects through api/client (launch-token guard)"
```

---

### Task 15: Consolidate tier vocabulary into one enum + rank map

**Files:**
- Create: `frontend/src/domain/tiers.ts`, `frontend/src/domain/tiers.test.ts`

> Context (audit §3 P9 + §2.G #57): potential tiers render as Elite/High/Mid/Low/Raw, but the Roster sort map uses Elite/High/Solid/Limited — so Mid/Low/Raw silently fall into one bucket. This task creates the single source; Phase 3 re-points `Roster.tsx` to it.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/domain/tiers.test.ts
import { describe, it, expect } from 'vitest';
import { POTENTIAL_TIERS, potentialRank } from './tiers';

describe('potential tiers', () => {
  it('has a stable, distinct rank for every rendered tier', () => {
    expect(POTENTIAL_TIERS).toEqual(['Elite', 'High', 'Mid', 'Low', 'Raw']);
    const ranks = POTENTIAL_TIERS.map(potentialRank);
    expect(new Set(ranks).size).toBe(POTENTIAL_TIERS.length); // no silent bucket collisions
    expect(potentialRank('Elite')).toBeLessThan(potentialRank('Raw'));
  });
  it('unknown tiers sort last, deterministically', () => {
    expect(potentialRank('Mystery' as never)).toBeGreaterThan(potentialRank('Raw'));
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npm run test -- tiers`
Expected: FAIL — cannot resolve `./tiers`.

- [ ] **Step 3: Implement**

```ts
// frontend/src/domain/tiers.ts
// Single source of truth for potential-tier vocabulary + ordering.
// Replaces the divergent Elite/High/Solid/Limited sort map in Roster.tsx.
export const POTENTIAL_TIERS = ['Elite', 'High', 'Mid', 'Low', 'Raw'] as const;
export type PotentialTier = (typeof POTENTIAL_TIERS)[number];

const RANK: Record<PotentialTier, number> = { Elite: 0, High: 1, Mid: 2, Low: 3, Raw: 4 };

/** Lower = better. Unknown tiers sort after all known ones, deterministically. */
export function potentialRank(tier: PotentialTier | string): number {
  return tier in RANK ? RANK[tier as PotentialTier] : POTENTIAL_TIERS.length;
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npm run test -- tiers`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/domain/tiers.*
git commit -m "feat(fe): single potential-tier enum + rank map (fixes silent sort bucket)"
```

---

### Task 16: Remove Tailwind (controlled pass)

**Files:**
- Modify: `frontend/vite.config.ts`, `frontend/src/index.css`, `frontend/package.json`

- [ ] **Step 1: Inventory Tailwind utility usage**

Run (from repo root): use Grep for `class(Name)?=["'\`][^"'\`]*\b(flex|grid|gap-|p-[0-9]|m-[0-9]|text-|bg-|w-|h-|rounded|border-)\b` across `frontend/src/**/*.tsx`.
- If matches are essentially absent (expected — the audit found inline styles, not utility soup), proceed to full removal (Steps 2-4).
- If there is meaningful utility usage, DO NOT remove yet: instead add a comment banner to `index.css` `/* TAILWIND FROZEN — no new utility classes; migrate to Floodlight tokens */` and stop here, committing only the freeze banner. Record the deferral in the preservation checklist.

- [ ] **Step 2: Convert the `@theme` block to plain CSS** — in `frontend/src/index.css`, change line 1 `@import "tailwindcss";` → delete it, and change the `@theme {` block (line 3) to `:root {` (the custom properties inside remain valid CSS). The Floodlight base reset now lives in `tokens.css` (Task 3), which replaces Tailwind's preflight.

- [ ] **Step 3: Remove the plugin + deps**

In `frontend/vite.config.ts`: remove `import tailwindcss from '@tailwindcss/vite'` and the `tailwindcss()` entry in `plugins` (leaving `[react()]`).
```bash
cd frontend && npm uninstall tailwindcss @tailwindcss/vite
```

- [ ] **Step 4: Verify the app still builds and the harness is green**

Run: `cd frontend && npm run build && npm run test && npm run lint`
Expected: all succeed. (If the build fails on a stray `@apply`/utility, grep for it and replace with the equivalent token-driven CSS, then re-run.)

- [ ] **Step 5: Commit**

```bash
git add frontend/vite.config.ts frontend/src/index.css frontend/package.json frontend/package-lock.json
git commit -m "chore(fe): remove Tailwind; tokens.css owns reset + custom properties"
```

---

### Task 17: Token-discipline lint gate (scoped to new code)

**Files:**
- Create: `frontend/scripts/check-tokens.mjs`
- Modify: `frontend/package.json` (script)

> Scope: scans `src/ui/**` and `src/styles/**` now; each later phase appends its migrated dir to `SCAN_DIRS`. Existing un-migrated files are intentionally out of scope (they are replaced per phase).

- [ ] **Step 1: Write the gate script**

```js
// frontend/scripts/check-tokens.mjs
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const SCAN_DIRS = ['src/ui', 'src/styles'];
const HEX = /#[0-9a-fA-F]{3,8}\b/;
// raw px other than 0/1px hairlines
const PX = /(?<![\w.])(?!0px|1px)\d{1,4}px\b/;
const ALLOW = /(viewBox|tokens\.css|\.test\.|\.svg)/;

function walk(dir) {
  let out = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) out = out.concat(walk(p));
    else if (['.tsx', '.ts', '.css'].includes(extname(p))) out.push(p);
  }
  return out;
}

const violations = [];
for (const dir of SCAN_DIRS) {
  for (const file of walk(dir)) {
    if (ALLOW.test(file)) continue;
    const text = readFileSync(file, 'utf8');
    text.split('\n').forEach((line, i) => {
      if (ALLOW.test(line)) return;
      if (HEX.test(line) || PX.test(line)) violations.push(`${file}:${i + 1}  ${line.trim()}`);
    });
  }
}

if (violations.length) {
  console.error('Token-discipline violations (use tokens, not literals):\n' + violations.join('\n'));
  process.exit(1);
}
console.log(`token-discipline OK (${SCAN_DIRS.join(', ')})`);
```

Add to `frontend/package.json` `"scripts"`: `"lint:tokens": "node scripts/check-tokens.mjs"`.

- [ ] **Step 2: Run the gate against the new primitives**

Run: `cd frontend && npm run lint:tokens`
Expected: PASS — the `.module.css` files use only `var(--…)` and allowed `1px`/`0`; primitives contain no raw hex/px. (If it flags a real literal in a primitive, replace it with a token and re-run.)

- [ ] **Step 3: Prove the gate actually catches a violation**

Temporarily add `color: #ff0000;` to `frontend/src/ui/Tag.module.css`, run `npm run lint:tokens`, confirm it EXITS 1 and names the line, then revert the edit and confirm it passes again.

- [ ] **Step 4: Commit**

```bash
git add frontend/scripts/check-tokens.mjs frontend/package.json
git commit -m "build(fe): token-discipline lint gate (scoped to src/ui + src/styles)"
```

---

### Task 18: Validate-before-delete dead components (batch 1)

**Files:**
- Delete (only after validation): the audit's "likely-dead" list.

- [ ] **Step 1: Build the import graph for each candidate**

For each of: `aftermath/MatchCard`, `aftermath/StandingsShift`, `aftermath/PlayerGrowthBlock`, `aftermath/RecruitReactions`, `aftermath/ReplaySpeedControl`, `dynasty/StaffMarketModal`, `dynasty/history/MilestoneTree`, `standings/RecentMatchesSidebar`, `roster/PlayerCompactRow`, `roster/PlayerTheaterRow`, `roster/PotentialBadge` — Grep the whole `frontend/src` for `import .* <Name>` and `<Name`. Record which have zero references.

- [ ] **Step 2: Delete the zero-reference ones in a small batch, build after**

```bash
cd frontend
# delete ONLY files confirmed zero-reference in Step 1, then:
npm run build && npm run test && npm run lint
```
Expected: all succeed. If the build breaks, the component was reachable — restore it and mark it "preserve until its path is rebuilt" in the preservation checklist (per spec §7: deep-state paths preserved until rebuilt + browser-checked).

- [ ] **Step 3: Remove dead Vite boilerplate**

If `frontend/src/App.css` is imported nowhere (Grep `App.css`), delete it. Re-run `npm run build`.

- [ ] **Step 4: Commit**

```bash
git add -A frontend/src
git commit -m "chore(fe): remove validated dead components + Vite boilerplate"
```

---

### Task 19: Phase 0 gate — full verification

- [ ] **Step 1: Run the complete gate**

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && python -m pytest -q
```
Expected: FE tests pass; build clean; eslint clean; token gate clean; Python suite green (unchanged — we touched no payload contracts).

- [ ] **Step 2: Manual smoke (the app still runs)**

Launch `python -m dodgeball_sim` (or the dev server), confirm the existing app loads on an existing save — Phase 0 added the foundation without rewriting screens, so nothing visual should regress.

- [ ] **Step 3: Commit any fixups, then tag the foundation**

```bash
git commit -am "chore(fe): Phase 0 foundation gate green" --allow-empty
```

---

## Subsequent plans (each authored via writing-plans when reached)

Each later phase gets its own dated plan under `docs/superpowers/plans/`, drawing its preserve-behavior subset + test strategy from the Task 1 checklist, and **expanding `SCAN_DIRS`** in the token gate to cover the dir it migrates:

- `…-floodlight-phase-1-app-shell.md` — shell, nav, broadcast header, SaveMenu, Week-9 fix (behaviors #9,#10,#82–#89,#91)
- `…-phase-2-command-loop.md` — Command Center, aftermath, replay + live match canvas (#1–#8,#11–#18,#41–#50,#90,#93–#95) — highest risk
- `…-phase-3-roster.md` — roster (Comfortable/Compact + gold glow via `CeilingBadge`/`StatBar`), lineup, player detail (#36,#51–#58)
- `…-phase-4-standings.md` (#6,#7,#15,#16,#33,#34,#38,#96)
- `…-phase-5-dynasty.md` incl. Record Room legacy mode (#19–#28,#30,#59–#66,#97)
- `…-phase-6-ceremonies.md` (#17,#18,#29,#31,#32,#35,#67–#75)
- `…-phase-7-new-game.md` (#22,#76–#81)
- `…-phase-8-sweep.md` — legibility primitives reskin, responsive QA (viewport matrix), axe, reduced-motion (#20,#21,#23–#27,#30,#37,#39,#40)

---

## Self-Review

**Spec coverage (Phase 0 scope of the spec):**
- §3.2/3.3/3.4 tokens + scales → Task 3 ✓
- §4 primitives (Truncate, Grid, ScrollRegion, Surface/Card, Table+density, Tag, RecordCell, Modal, Popover, ActionBar) → Tasks 4–13 ✓ (data-viz/SVG primitives — StatBar, CeilingBadge, Court, Sparkline — deferred to their consuming phases per YAGNI; noted in Subsequent-plans)
- §4 migrate `ui.tsx` not duplicate → Modal ports Dialog (Task 10); full re-point of remaining `ui.tsx` primitives to tokens is folded into Phase 1 where its consumers are reskinned (noted; the Modal port + barrel establish the pattern). 
- §5 token discipline + gate → Task 17 ✓; api/client consolidation → Task 14 ✓; tier reconciliation → Task 15 ✓; anti-strip hook forwarding → Tasks 9,10,12 assert `data-*`/`role`/`aria` survive ✓
- §6 harness (Vitest+RTL) + executable contract → Tasks 2, 1 ✓
- §7 validate-before-delete → Task 18 ✓
- §8 Phase 0A/0B → this plan ✓; §11 Tailwind controlled pass → Task 16 ✓
- §9 viewport matrix / accessibility / Week-9 → deferred to Phase 1+ (no screens here); reduced-motion base handling added in tokens (Task 3) ✓

**Gap found + fixed:** `ui.tsx` houses many primitives (Card, Badge, RatingBar, RadioGroup, etc.) still on `dm-*`/literals. Fully migrating all of them in Phase 0 would be building without consumers (YAGNI) and risks visual churn before screens move. Resolution: Phase 0 ports the broadly-shared, screen-agnostic ones (Modal) and establishes tokens+gate; each later phase migrates the `ui.tsx` primitives its screens use and deletes the old variant (spec §4 "no indefinite coexistence" is enforced per-phase, tracked by the token gate's expanding `SCAN_DIRS`). This is called out in Subsequent-plans.

**Placeholder scan:** none — every code step has complete code; the one "read the exact shape before writing" note (Task 14 Step 3) is a correctness guard against inventing API fields, not a logic placeholder.

**Type consistency:** primitive prop names (`elevation`, `tone`, `density`, `min`, `maxHeight`, `wins/losses/draws`, `open/anchor`) are used identically in their tests and the barrel; `potentialRank`/`POTENTIAL_TIERS` match between `tiers.ts` and its test; `saveApi.startingStaff/startingProspects` match between client and `client.test.ts`.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-floodlight-phase-0-foundations.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with checkpoints for review.
