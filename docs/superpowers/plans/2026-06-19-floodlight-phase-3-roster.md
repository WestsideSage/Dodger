# Floodlight Phase 3 — Roster + Lineup + Player Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the Roster screen (`components/Roster.tsx`), the Lineup Editor (`components/lineup/LineupEditor.tsx`), and the Player Detail modal (`components/PlayerDetailModal.tsx`) onto the Floodlight token system using CSS Modules, while keeping the 9 Phase-3 trust behaviors (#36, #51–#58, #92) green. The Roster's existing "Detailed/Compact" view toggle is re-expressed as the shared `src/ui` `Table` **density** (`comfortable` = visual cards + stat-bars, `compact` = dense numbers). This phase also **creates the two deferred data-viz primitives** the design §4 names but Phase 0 left for their consuming phase: `src/ui/CeilingBadge` (gold glow scaled by grade — §3.5 ceiling ladder) and `src/ui/StatBar` (glanceable rating, brightness = strength). Finally it re-points the Roster potential sort to the single `src/domain/tiers.ts` enum, fixing the silent Mid/Low/Raw bucket collision (#57).

**Architecture:** The three screens move from inline-style objects (audit §3 P1 "high" rows: `PlayerDetailModal.tsx:75-85`, `LineupEditor.tsx:276-285`, `Roster.tsx:281-310`) to scoped `*.module.css` files driven by `src/styles/tokens.css`. The two new primitives are token-driven CSS-Module components in `src/ui/` with their own RED→GREEN tests and barrel exports — they are scanned by the token gate immediately (`src/ui` is already in `SCAN_DIRS`). `RatingMini`/`Sparkline`/the four glance cells stay functionally intact; only their styling substrate changes. The Roster sort consumes `potentialRank()` from `domain/tiers.ts` (built in Phase 0 Task 15). No engine, payload, or routing behavior changes.

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (harness from Phase 0).

**Spec:** [2026-06-19-ui-redesign-design.md](../specs/2026-06-19-ui-redesign-design.md) §3.5 (talent glow / ceiling ladder), §4 (`<StatBar>`/`<CeilingBadge>`/`<Table>`+density rows) · **Non-regression contract:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md) §1 (Roster + lineup + player detail screens), §2.D #36, §2.G #51–#58, §2.J #92, §3 P1/P2/P3/P4/P6/P9 rows on these screens · **Checklist:** [floodlight-preservation-checklist.md](floodlight-preservation-checklist.md) Phase 3 rows · **Orchestration contract:** [2026-06-19-floodlight-parallelization-strategy.md](2026-06-19-floodlight-parallelization-strategy.md) GROUP [3] (STEP 2 concurrent window) · **Foundations + style template:** [2026-06-19-floodlight-phase-0-foundations.md](2026-06-19-floodlight-phase-0-foundations.md) · **Locked Phase-1 contracts:** [2026-06-19-floodlight-phase-1-app-shell.md](2026-06-19-floodlight-phase-1-app-shell.md) (the 5 `src/ui` shims, `appContracts.ts`, frozen `PlayoffBracket`/`ProgramModal` signatures).

**Branch / worktree:** This is a **MIDDLE phase**. It runs **CONCURRENTLY** in an isolated git worktree branched from the **MERGED post-Phase-1 trunk** (per strategy STEP 2). All Phase-3 commits land on the worktree branch; the controller merges and the serial integrator (STEP 3) does the `index.css` deletion. **This plan contains NO `index.css` deletion tasks.**

---

## Concurrent-window HARD RULES (encoded as task constraints)

This phase executes inside the STEP-2 concurrent window. The following freezes are load-bearing for the 97-behavior trust contract and are repeated as explicit constraints on every task that could touch them:

1. **NO `index.css` edits or deletions.** CREATE `*.module.css` files ONLY. The legacy selector families these screens used (`.rl-*`, `.rl-table`, `.rl-ratings`, `.rl-glance`, etc.) are removed **later** by the serial integrator in STEP 3 — **not in this plan**. The old `index.css` is still present in the worktree during the per-phase gate; that is expected (the reskinned components simply stop referencing the dead `.rl-*` rules; those rules go dark but stay on disk until STEP 3). **Do not add any task that deletes from `index.css`.**
2. **NO edits to `components/ui.tsx`.** Re-point imports of `ActionButton`, `RatingBar`, `StatusMessage`, `Dialog`→`Modal` to the new Phase-1 `src/ui` shims / primitives. **Import-path change ONLY.** Specifically: **NO `ActionButton`→`ActionBar` remap** (that consolidation is deferred to Phase 8). `ActionButton` stays `ActionButton` (now imported from `../ui` / `../../ui`).
3. **FROZEN — consume, never alter:**
   - `components/match-week/matchResult.ts` public API (`formatScoreline`/`survivorDetail`/`ScorelineFields`/`MatchScoreline`). These screens do not import it; do not introduce an import.
   - The `legibility/*` primitives (`TermTip`, `ProofChip`, `getTerm`, `CeilingGrade`, `KnownValue`) are **read-only** — accept their mixed (legacy-styled) look until Phase 8. Keep their `data-*` provenance intact. The new `src/ui/CeilingBadge` is a **distinct** primitive from `legibility/CeilingGrade` (different vocabulary, different axis — see Task 1) and does not modify it.
   - The SHARED globals `command-action-bar` / `command-policy-overlay` (not used by these screens — never delete them anyway).
   - `frontend/scripts/check-tokens.mjs` — the integrator owns `SCAN_DIRS`. **Phases never touch it.** (`src/ui` is already scanned, so the two new primitives are gated now; the migrated `src/components/roster` dir + the screen module files come into scope only when the integrator appends them in STEP 3 — see "Per-phase gate" note.)
4. **Consume Phase-1 published contracts where relevant:** `components/shell/appContracts.ts` and the frozen signatures of `standings/PlayoffBracket` + `dynasty/history/ProgramModal`. *(Phase 3's screens do not mount MatchWeek, the bracket, or ProgramModal, so no Phase-1 contract is a direct dependency here. This is noted for completeness; the only Phase-0/1 artifacts Phase 3 consumes are the `src/ui` shims, the `src/ui` primitives, and `domain/tiers.ts`.)*
5. **`data-*` anti-strip vitests are HARD RED preconditions.** Any rebuild MUST keep its truth-provenance hooks. The hooks present on Phase-3 screens are `data-testid="lineup-stale-note"` (LineupEditor #53), `data-testid="release-confirm-strip"` (PlayerDetailModal #54), and `data-testid="release-player-btn"` (PlayerDetailModal #54). These are enumerated and tested in Tasks 6–8 as preconditions before each rebuild. *(The global proof hooks `data-broadcast-proof-source` / `data-player-outcome` live on replay/bracket surfaces, NOT on these screens — confirmed by grep; no need to fabricate them here.)*

---

## File map (created/modified in this plan)

**Created (data-viz primitives — strategy/spec §4 deferred items):**
- `frontend/src/ui/CeilingBadge.tsx` + `CeilingBadge.module.css` + `CeilingBadge.test.tsx`
- `frontend/src/ui/StatBar.tsx` + `StatBar.module.css` + `StatBar.test.tsx`

**Created (screen modules + tests):**
- `frontend/src/components/Roster.module.css`
- `frontend/src/components/Roster.test.tsx`
- `frontend/src/components/lineup/LineupEditor.module.css`
- `frontend/src/components/lineup/LineupEditor.test.tsx`
- `frontend/src/components/PlayerDetailModal.module.css`
- `frontend/src/components/PlayerDetailModal.test.tsx`

**Modified:**
- `frontend/src/ui/index.ts` (append `CeilingBadge` + `StatBar` exports + their grade type)
- `frontend/src/components/Roster.tsx` (reskin to module CSS + `Table` density; re-point sort to `domain/tiers.ts`; nullish-fallback tolerance #92; re-point `StatusMessage` import to `../ui`)
- `frontend/src/components/lineup/LineupEditor.tsx` (reskin to module CSS; re-point `ActionButton`/`Dialog`→`Modal` imports to `../../ui`)
- `frontend/src/components/PlayerDetailModal.tsx` (reskin to module CSS; re-point `RatingBar`/`ActionButton`/`Dialog`→`Modal` imports to `../ui`)
- `frontend/src/components/roster/Sparkline.tsx` (optional, minimal: token the stroke/fallback colors so it passes the gate once the dir is scanned — its honest NO-DATA fallback behavior #36 stays byte-identical)

**Frozen / NOT touched:** `frontend/src/index.css` (integrator owns deletion in STEP 3), `components/ui.tsx` (shims/primitives only), `match-week/matchResult.ts`, `legibility/*` (incl. `CeilingGrade.tsx`), `command-action-bar`/`command-policy-overlay`, `frontend/scripts/check-tokens.mjs` (integrator owns SCAN_DIRS), `roster/PlayerCompactRow.tsx` / `roster/PlayerTheaterRow.tsx` / `roster/PotentialBadge.tsx` (audit §1 marks these DEAD/transitively-dead — Phase 0 Task 18 validated/handled deletion; do NOT resurrect them. If still present, leave untouched — they are not on the live Roster import path: `Roster.tsx` imports only `PlayerDetailModal`, `LineupEditor`, `Sparkline`, `TermTip`).

---

## Per-task gate

Unless a task says otherwise, every task ends green on:

```bash
cd frontend && npm run test -- <the task's test files> && npm run build && npm run lint && npm run lint:tokens
```

The **Phase-3 per-phase merge gate** (Task 9), run in the worktree **with the OLD `index.css` still present**, additionally runs the full FE suite + build + lint + token gate + a smoke e2e:

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e
```

> **Token-gate scope note.** `npm run lint:tokens` only fails on dirs in `SCAN_DIRS` (currently `['src/ui','src/styles']`). The two new primitives live in `src/ui`, so **their token discipline is enforced from Task 1**. The screen modules (`Roster.module.css`, `lineup/LineupEditor.module.css`, `PlayerDetailModal.module.css`) live in `src/components/**`, which is **not yet scanned** — the **integrator** appends `src/components/roster` + the explicit screen-module files to `SCAN_DIRS` in STEP 3 (phases never touch `check-tokens.mjs`). Therefore each reskin task (6–8) MUST pre-empt violations by using only `var(--…)` tokens (no raw hex/px beyond `0`/`1px` hairlines, and SVG `viewBox` coordinates which the gate's `ALLOW_LINE` permits) **from the start**, so that when the integrator widens the scan in STEP 3 the modules are already clean. To self-verify before the integrator does, a task MAY run the gate against a temporary local SCAN_DIRS (do not commit that change).

> **Runtime club-color caveat (strategy residual risk).** If any reskinned surface needs a runtime club color, set it via an inline `style={{ '--xxx': value }}` custom property in the `.tsx` (a CSS *variable assignment*, not a literal in `.module.css`) so the token gate does not trip when the dir is scanned — the same pattern Phase 1 used for `--mono-hue`. Phase 3's screens do not currently read club colors, so this is a guardrail, not a required change.

---

## Phase 3A — Data-viz primitives (deferred from Phase 0; spec §4)

### Task 1: `CeilingBadge` primitive — gold glow scaled by grade (§3.5 ceiling ladder)

> **Why:** Design §4 lists `<CeilingBadge>` ("gold glow scaled by grade") and §3.5 specifies the **ceiling ladder**: glow intensity scales with letter grade — **A+ brightest → A strong → A− lit outline → B+ faint → B/B− neutral → C dims** — with the ladder itself as the reference legend. Phase 0 explicitly **deferred** StatBar/CeilingBadge to "their consuming phase" (Phase 0 Self-Review). Phase 3 is that phase: the Roster potential cell + Player Detail potential block are the gold-talent surfaces. **This is a NEW `src/ui` primitive, distinct from `legibility/CeilingGrade`** — `CeilingGrade` is a 3-token scout-arc vocabulary (`HIGH_CEILING`/`SOLID`/`STANDARD`) on a different axis and is FROZEN; `CeilingBadge` is the gold letter-ladder glow. The primitive accepts a `grade` letter prop (the consumer derives it from a number — see Task 6); it never re-derives from raw payload, so it stays a pure presentational primitive. It uses ONLY `--gold`/`--gold2`/`--gold-soft` tokens for the glow and exposes a static `ladder` legend export.

**Grade vocabulary (the contract — match exactly):** `CeilingGradeLetter = 'A+' | 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C'`. Glow tiers (intensity → CSS class), per §3.5: `A+`→`g5` (brightest: filled gold gradient + outer glow), `A`→`g4` (strong: gold fill, softer glow), `A-`→`g3` (lit outline: gold border + faint inner), `B+`→`g2` (faint: soft gold tint), `B`/`B-`→`g1` (neutral: line border, gold text only), `C`→`g0` (dim: muted/`--out`). The mapping lives in ONE record so the ladder legend and the badge cannot diverge.

**Files:** create `frontend/src/ui/CeilingBadge.tsx` + `CeilingBadge.module.css` + `CeilingBadge.test.tsx`.

- [ ] **Step 1: Write the failing test** — assert the grade→glow-class mapping, the monotonic ladder, token discipline (no inline hex), data-* forwarding, and the ladder legend.

```tsx
// frontend/src/ui/CeilingBadge.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CeilingBadge, CEILING_LADDER } from './CeilingBadge';

describe('CeilingBadge (gold ceiling ladder, §3.5)', () => {
  it('renders the grade text and forwards data-*/aria', () => {
    render(<CeilingBadge grade="A+" data-testid="cb" aria-label="ceiling A plus" />);
    const el = screen.getByTestId('cb');
    expect(el).toHaveTextContent('A+');
    expect(el).toHaveAttribute('aria-label', 'ceiling A plus');
  });
  it('maps brighter grades to higher glow tiers (monotonic ladder)', () => {
    const { rerender } = render(<CeilingBadge grade="A+" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g5/);
    rerender(<CeilingBadge grade="A" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g4/);
    rerender(<CeilingBadge grade="A-" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g3/);
    rerender(<CeilingBadge grade="B+" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g2/);
    rerender(<CeilingBadge grade="B" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g1/);
    rerender(<CeilingBadge grade="B-" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g1/);
    rerender(<CeilingBadge grade="C" data-testid="cb" />);
    expect(screen.getByTestId('cb').className).toMatch(/g0/);
  });
  it('exposes the ladder legend as the single reference key (7 rungs, ordered A+→C)', () => {
    expect(CEILING_LADDER.map((r) => r.grade)).toEqual(['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C']);
    // every rung names a glow tier; tiers never increase as the grade descends
    const tierNums = CEILING_LADDER.map((r) => Number(r.tier.replace('g', '')));
    for (let i = 1; i < tierNums.length; i += 1) {
      expect(tierNums[i]).toBeLessThanOrEqual(tierNums[i - 1]);
    }
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "ui/CeilingBadge"`. Expected: FAIL (module unresolved).

- [ ] **Step 3: Implement** — token-only CSS Module; one source-of-truth ladder record drives both the badge class and the exported legend.

```tsx
// frontend/src/ui/CeilingBadge.tsx
import type { HTMLAttributes } from 'react';
import styles from './CeilingBadge.module.css';

export type CeilingGradeLetter = 'A+' | 'A' | 'A-' | 'B+' | 'B' | 'B-' | 'C';

/** Single source of truth for the §3.5 ceiling ladder: grade → glow tier.
 *  Brighter grade = higher tier (g5 brightest → g0 dimmest). The badge and the
 *  legend both read this so the reference key can never drift from the render. */
export const CEILING_LADDER: ReadonlyArray<{ grade: CeilingGradeLetter; tier: string; note: string }> = [
  { grade: 'A+', tier: 'g5', note: 'brightest — generational ceiling' },
  { grade: 'A',  tier: 'g4', note: 'strong — elite ceiling' },
  { grade: 'A-', tier: 'g3', note: 'lit outline — high ceiling' },
  { grade: 'B+', tier: 'g2', note: 'faint — solid ceiling' },
  { grade: 'B',  tier: 'g1', note: 'neutral — rotation ceiling' },
  { grade: 'B-', tier: 'g1', note: 'neutral — depth ceiling' },
  { grade: 'C',  tier: 'g0', note: 'dim — limited ceiling' },
];

const TIER_BY_GRADE: Record<CeilingGradeLetter, string> = Object.fromEntries(
  CEILING_LADDER.map((r) => [r.grade, r.tier]),
) as Record<CeilingGradeLetter, string>;

interface CeilingBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  grade: CeilingGradeLetter;
}

export function CeilingBadge({ grade, className = '', ...rest }: CeilingBadgeProps) {
  const tier = TIER_BY_GRADE[grade] ?? 'g0';
  return (
    <span className={`${styles.badge} ${styles[tier]} ${className}`.trim()} {...rest}>
      {grade}
    </span>
  );
}
```

```css
/* frontend/src/ui/CeilingBadge.module.css */
.badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: var(--space-7); padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm); border: 1px solid var(--line);
  font: 800 .68rem var(--font-mono); font-variant-numeric: tabular-nums;
  letter-spacing: .02em; white-space: nowrap; color: var(--gold);
}
/* §3.5 ladder — glow intensity scales with grade (gold tokens only) */
.g5 { color: var(--gold-ink); background: linear-gradient(95deg, var(--gold), var(--gold2)); border-color: var(--gold2); box-shadow: 0 0 18px -4px var(--gold); }
.g4 { color: var(--gold-ink); background: var(--gold); border-color: var(--gold2); box-shadow: 0 0 12px -5px var(--gold); }
.g3 { color: var(--gold2); background: var(--gold-soft); border-color: var(--gold); }
.g2 { color: var(--gold); background: var(--gold-soft); border-color: var(--gold-soft); }
.g1 { color: var(--gold); background: transparent; border-color: var(--line2); }
.g0 { color: var(--out); background: transparent; border-color: var(--line); }
```

> **Token note:** The on-gold legible ink uses `var(--gold-ink)` — already defined as `#1a1407` in `tokens.css:11` and already used by `Tag.module.css` `.talent`. No raw hex is acceptable in `src/ui` CSS Modules; the token already exists and the `.g5`/`.g4` rules above use it correctly.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "ui/CeilingBadge"`. Expected: PASS.

- [ ] **Step 5: Gate** — `cd frontend && npm run test -- "ui/CeilingBadge" && npm run build && npm run lint && npm run lint:tokens`. Expected: green (`src/ui` is scanned, so token discipline is enforced now).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ui/CeilingBadge.tsx frontend/src/ui/CeilingBadge.module.css frontend/src/ui/CeilingBadge.test.tsx
git commit -m "feat(ui): CeilingBadge primitive — gold glow ceiling ladder (spec §3.5, §4 deferred)"
```

---

### Task 2: `StatBar` primitive — glanceable rating, brightness = strength (spec §4)

> **Why:** Design §4 lists `<StatBar>` ("glanceable rating; brightness = strength"). Deferred by Phase 0 to its consuming phase. Phase 3's Roster Detailed/Comfortable view (the current inline `RatingMini` with its `tier-elite/good/avg/poor` brightness buckets — `Roster.tsx:208-219`) and the Player Detail rating sheet are the consumers. `StatBar` is the token-driven replacement for the ad-hoc `RatingMini` brightness scale (audit §3 P9 "AgeCurve/RatingMini percentage heights depend on external CSS box dimensions" — fragile inline↔CSS coupling). The bar width encodes the value; the **brightness tier** (a class, not opacity-crush — §3.5 "color-dimmed not opacity-crushed, holds ≥0.85 readability") encodes strength. Values clamp to 0..100; the label/value stay legible at every tier.

**Contract (match exactly):** `StatBar` props `{ label: string; value: number; max?: number /* default 100 */ }` + standard `HTMLAttributes` (forwards `data-*`/`title`). Brightness tiers from the value: `>=85`→`elite`, `>=70`→`good`, `>=55`→`avg`, else `poor` (mirrors the existing `RatingMini` thresholds so the visual reading is preserved). Renders the rounded value and a fill whose width is `clamp(0,value/max,1)*100%`.

**Files:** create `frontend/src/ui/StatBar.tsx` + `StatBar.module.css` + `StatBar.test.tsx`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/ui/StatBar.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatBar } from './StatBar';

describe('StatBar (glanceable rating, brightness = strength)', () => {
  it('renders the rounded value and the label, forwards data-*/title', () => {
    render(<StatBar label="ACC" value={73.4} title="Accuracy" data-testid="sb" />);
    const el = screen.getByTestId('sb');
    expect(el).toHaveTextContent('ACC');
    expect(el).toHaveTextContent('73');
    expect(el).toHaveAttribute('title', 'Accuracy');
  });
  it('assigns brightness tiers by strength', () => {
    const { rerender } = render(<StatBar label="X" value={90} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/elite/);
    rerender(<StatBar label="X" value={72} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/good/);
    rerender(<StatBar label="X" value={60} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/avg/);
    rerender(<StatBar label="X" value={40} data-testid="sb" />);
    expect(screen.getByTestId('sb').className).toMatch(/poor/);
  });
  it('clamps the fill width to 0..100% via a custom property', () => {
    render(<StatBar label="X" value={150} data-testid="sb" />);
    const fill = screen.getByTestId('sb').querySelector('[data-statbar-fill]') as HTMLElement;
    expect(fill.style.getPropertyValue('--fill')).toBe('100%');
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "ui/StatBar"`. Expected: FAIL (module unresolved).

- [ ] **Step 3: Implement** — token-only CSS; fill width via a `--fill` custom property (a variable assignment, not a literal); brightness tiers as classes.

```tsx
// frontend/src/ui/StatBar.tsx
import type { CSSProperties, HTMLAttributes } from 'react';
import styles from './StatBar.module.css';

interface StatBarProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: number;
  max?: number;
}

function tierOf(v: number): 'elite' | 'good' | 'avg' | 'poor' {
  if (v >= 85) return 'elite';
  if (v >= 70) return 'good';
  if (v >= 55) return 'avg';
  return 'poor';
}

export function StatBar({ label, value, max = 100, className = '', ...rest }: StatBarProps) {
  const pct = Math.max(0, Math.min(1, value / max)) * 100;
  const tier = tierOf(value);
  const vars = { '--fill': `${pct}%` } as CSSProperties;
  return (
    <div className={`${styles.row} ${styles[tier]} ${className}`.trim()} {...rest}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{Math.round(value)}</span>
      <div className={styles.track}>
        <div className={styles.fill} data-statbar-fill style={vars} />
      </div>
    </div>
  );
}
```

```css
/* frontend/src/ui/StatBar.module.css */
.row { display: grid; grid-template-columns: var(--space-9) var(--space-8) 1fr; align-items: center; gap: var(--space-3); min-width: 0; }
.label { font: 700 .58rem var(--font-ui); letter-spacing: .06em; color: var(--muted); text-transform: uppercase; }
.value { font: 700 .82rem var(--font-mono); font-variant-numeric: tabular-nums; text-align: right; color: var(--text); }
.track { height: var(--space-2); border-radius: var(--radius-sm); background: var(--line); overflow: hidden; }
.fill { height: 100%; width: var(--fill, 0%); border-radius: var(--radius-sm); }
/* brightness = strength (color-dimmed, not opacity-crushed; label/value stay legible) */
.elite .fill { background: linear-gradient(90deg, var(--gold), var(--gold2)); }
.good  .fill { background: var(--ok); }
.avg   .fill { background: var(--text2); }
.poor  .fill { background: var(--out); }
```

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "ui/StatBar"`. Expected: PASS.

- [ ] **Step 5: Gate** — `cd frontend && npm run test -- "ui/StatBar" && npm run build && npm run lint && npm run lint:tokens`. Expected: green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ui/StatBar.tsx frontend/src/ui/StatBar.module.css frontend/src/ui/StatBar.test.tsx
git commit -m "feat(ui): StatBar primitive — glanceable rating, brightness=strength (spec §4 deferred)"
```

---

### Task 3: Append the two primitives to the `src/ui` barrel

> **Why:** The screens import `CeilingBadge`/`StatBar` from `../ui` / `../../ui`. The barrel is the single import surface (matches the Phase-0/Phase-1 export pattern).

**Files:** modify `frontend/src/ui/index.ts` + extend `frontend/src/ui/index.test.tsx` (the Phase-0 barrel test).

- [ ] **Step 1: Add the failing barrel assertions** — extend the existing `'ui barrel'` "exports every primitive" list in `frontend/src/ui/index.test.tsx` to include the two new names:

```tsx
// in frontend/src/ui/index.test.tsx — add 'CeilingBadge' and 'StatBar' to the existing
// for (const name of [...]) list so the barrel test fails until they are exported.
for (const name of ['Truncate','Surface','Card','Grid','ScrollRegion','Tag','RecordCell','Popover','Modal','ActionBar','Table','CeilingBadge','StatBar']) {
  expect(UI).toHaveProperty(name);
}
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "ui/index"`. Expected: FAIL (`CeilingBadge`/`StatBar` not on the barrel).

- [ ] **Step 3: Append the exports** — in `frontend/src/ui/index.ts` add:

```ts
export { CeilingBadge, CEILING_LADDER } from './CeilingBadge';
export type { CeilingGradeLetter } from './CeilingBadge';
export { StatBar } from './StatBar';
```

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "ui/index"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "ui/index" && npm run build && npm run lint && npm run lint:tokens
git add frontend/src/ui/index.ts frontend/src/ui/index.test.tsx
git commit -m "feat(ui): export CeilingBadge + StatBar from the primitives barrel"
```

---

## Phase 3B — Roster screen

### Task 4: Roster sort → single `domain/tiers.ts` enum (fixes the silent Mid/Low/Raw bucket, #57)

> **Why:** Audit §2.G #57 + §3 P9: the Roster potential sort uses an inline `order` map keyed `{ Elite, High, Solid, Limited }` (`Roster.tsx:242`), but the RENDERED tiers are `Elite/High/Mid/Low/Raw` (`PotentialBlock`, `Roster.tsx:146`). So `Mid`/`Low`/`Raw` all hit the `?? 4` fallback and are silently lumped into one bucket. Phase 0 Task 15 built the single source `domain/tiers.ts` (`POTENTIAL_TIERS = ['Elite','High','Mid','Low','Raw']`, `potentialRank(tier)` — lower = better, unknown sorts last). This task re-points the sort to it. **The behavior #57 contract — explicit tier-rank map with fallback, tie-break by OVR, starters-first for the lineup sort — must hold; only the rank source changes.** This is a pure logic change with no styling, done before the reskin so the sort fix is isolated and provable.

**Audit number + test strategy (checklist Phase 3):** #57 vitest (Roster sort).

**Files:** create `frontend/src/components/Roster.test.tsx`; modify `frontend/src/components/Roster.tsx`.

- [ ] **Step 1: Write the failing test** — mock `useApiResource` (or `rosterApi`) to feed a fixed roster covering all five tiers + a tie, assert the resolved row order under each sort key. Mock the child components so the test exercises Roster's own sort, not their internals.

```tsx
// frontend/src/components/Roster.test.tsx
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock the heavy children so the test exercises Roster's own sort/markup.
vi.mock('./PlayerDetailModal', () => ({ PlayerDetailModal: () => <div data-testid="stub-detail" /> }));
vi.mock('./lineup/LineupEditor', () => ({ LineupEditor: () => <div data-testid="stub-lineup" /> }));
vi.mock('./roster/Sparkline', () => ({ Sparkline: () => <svg data-testid="stub-spark" /> }));

import { useApiResource } from '../hooks/useApiResource';
import { Roster } from './Roster';

vi.mock('../hooks/useApiResource', () => ({ useApiResource: vi.fn() }));

const PLAYER = (over: Record<string, unknown> = {}) => ({
  id: 'p', name: 'Player', age: 24, overall: 70, role: 'Sharpshooter',
  potential_tier: 'Mid', scouting_confidence: 2, potential_ceiling: 80, headroom: 4,
  projected_growth: 'plateauing', ovr_season_trend: null,
  ratings: { accuracy: 70, power: 70, dodge: 70, catch: 70, stamina: 70, tactical_iq: 70 },
  ...over,
});

function mockRoster(roster: Array<ReturnType<typeof PLAYER>>, extra: Record<string, unknown> = {}) {
  vi.mocked(useApiResource).mockReturnValue({
    data: { roster, default_lineup: [], lineup_auto_reorder: true, open_promise_player_ids: [], ...extra },
    loading: false, error: null, setData: vi.fn(), refetch: vi.fn(),
  } as never);
}

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

function rowNames(): string[] {
  return screen.getAllByTestId('roster-row').map((r) => within(r).getByTestId('roster-row-name').textContent ?? '');
}

describe('Roster potential sort (audit #57 — single tier vocabulary, no silent bucket)', () => {
  it('orders ALL five rendered tiers distinctly (Mid/Low/Raw no longer collapse)', async () => {
    mockRoster([
      PLAYER({ id: 'raw',   name: 'Raw One',   potential_tier: 'Raw',   overall: 60 }),
      PLAYER({ id: 'elite', name: 'Elite One', potential_tier: 'Elite', overall: 60 }),
      PLAYER({ id: 'low',   name: 'Low One',   potential_tier: 'Low',   overall: 60 }),
      PLAYER({ id: 'high',  name: 'High One',  potential_tier: 'High',  overall: 60 }),
      PLAYER({ id: 'mid',   name: 'Mid One',   potential_tier: 'Mid',   overall: 60 }),
    ]);
    render(<Roster />);
    await userEvent.selectOptions(screen.getByTestId('roster-sort'), 'potential');
    expect(rowNames()).toEqual(['Elite One', 'High One', 'Mid One', 'Low One', 'Raw One']);
  });
  it('breaks ties within a tier by OVR descending', async () => {
    mockRoster([
      PLAYER({ id: 'midlo', name: 'Mid Lower', potential_tier: 'Mid', overall: 65 }),
      PLAYER({ id: 'midhi', name: 'Mid Higher', potential_tier: 'Mid', overall: 88 }),
    ]);
    render(<Roster />);
    await userEvent.selectOptions(screen.getByTestId('roster-sort'), 'potential');
    expect(rowNames()).toEqual(['Mid Higher', 'Mid Lower']);
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "components/Roster"`. Expected: FAIL — partly because `roster-row` / `roster-row-name` / `roster-sort` testids do not exist yet, and the sort still uses the broken `{Elite,High,Solid,Limited}` map (Mid/Low/Raw collapse). (Adding these testids is part of Step 3; they are stable hooks, not anti-strip provenance.)

- [ ] **Step 3: Implement the sort fix + add the test hooks**
  - Import the enum: `import { potentialRank } from '../domain/tiers';`
  - Replace the inline `order` map block (`Roster.tsx:242-247`) with:

    ```ts
    } else if (sortKey === 'potential') {
      entries.sort(
        (left, right) =>
          potentialRank(left.player.potential_tier) - potentialRank(right.player.potential_tier)
          || right.player.overall - left.player.overall,
      );
    }
    ```
  - Keep the `lineup` (starters-first then OVR), `overall`, and `age` branches **verbatim** (#57 starters-first for lineup sort is unchanged).
  - Add `data-testid="roster-sort"` to the `<select>` (`Roster.tsx:275`), `data-testid="roster-row"` to the `<tr>` (`Roster.tsx:361`), and wrap the player name in `data-testid="roster-row-name"` on the existing `.rl-player-name` span. These are plain test hooks (do NOT remove or rename any existing markup).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "components/Roster"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "components/Roster" && npm run build && npm run lint
git add frontend/src/components/Roster.tsx frontend/src/components/Roster.test.tsx
git commit -m "fix(roster): potential sort reads domain/tiers enum — Mid/Low/Raw no longer collapse (#57)"
```

---

### Task 5: Roster response-field tolerance (#92) + Sparkline NO-DATA fallback (#36)

> **Why:** Audit §2.J #92: response-field tolerance via nullish fallbacks — `default_lineup ?? []` (`Roster.tsx:229`), `lineup_auto_reorder ?? true` (`:517`), `open_promise_player_ids ?? []` (`:495`), and the `data.roster ?? []` map (`:234`). A payload missing any of these must not crash or fabricate. Audit §2.D #36: the OVR Sparkline renders ONLY with `ovr_season_trend != null && length >= 2`; otherwise the honest fallback (currently the static gauge bar). These two truth behaviors must be locked **before** the reskin moves their markup, so the reskin cannot quietly drop a guard. (Both already exist in the current code — these are non-regression guards establishing the green baseline.)

**Audit numbers + test strategy:** #92 vitest (nullish fallbacks) · #36 vitest (Sparkline ≥2-point gate / NO-DATA fallback).

**Files:** extend `frontend/src/components/Roster.test.tsx`.

- [ ] **Step 1: Write the tests** (extend the Task 4 file)

```tsx
describe('Roster response-field tolerance (audit #92) + Sparkline gate (#36)', () => {
  it('#92: tolerates a payload missing default_lineup / lineup_auto_reorder / open_promise_player_ids', () => {
    mockRoster(
      [PLAYER({ id: 'a', name: 'Alpha' })],
      // deliberately omit default_lineup, lineup_auto_reorder, open_promise_player_ids
      { default_lineup: undefined, lineup_auto_reorder: undefined, open_promise_player_ids: undefined },
    );
    expect(() => render(<Roster />)).not.toThrow();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    // no starter pin fabricated when default_lineup is absent
    expect(screen.queryByTestId('roster-row-starter-pin')).not.toBeInTheDocument();
  });
  it('#36: renders the Sparkline only with >=2 trend points', () => {
    mockRoster([PLAYER({ id: 't', name: 'Trend', ovr_season_trend: [70, 72, 75] })]);
    render(<Roster />);
    expect(screen.getByTestId('stub-spark')).toBeInTheDocument();
  });
  it('#36: a null/short trend shows the honest NO-DATA fallback, never a fake sparkline', () => {
    mockRoster([PLAYER({ id: 'n', name: 'NoTrend', ovr_season_trend: null })]);
    render(<Roster />);
    expect(screen.queryByTestId('stub-spark')).not.toBeInTheDocument();
    expect(screen.getByTestId('roster-ovr-nodata')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "components/Roster"`. Expected: the #92 case and the two #36 cases PASS against the current Roster once the test hooks exist; the `roster-row-starter-pin` / `roster-ovr-nodata` hooks are added in Step 3. (If a case fails because a hook is missing, that is expected pre-Step-3.)

- [ ] **Step 3: Add the minimal test hooks (no behavior change)**
  - Add `data-testid="roster-row-starter-pin"` to the existing `.rl-pin` starter span (`Roster.tsx:387`) — it already renders only when `starter` is true, so the #92 assertion (absent when `default_lineup` is missing) holds.
  - Add `data-testid="roster-ovr-nodata"` to the existing fallback `<div className="rl-ovr-spark">` block (`Roster.tsx:443-449`) — the branch that renders when the trend is null/short. Do NOT change the `ovr_season_trend != null && length >= 2` condition.
  - Confirm the four nullish fallbacks remain exactly: `data?.default_lineup ?? []`, `data?.roster ?? []`, `data.lineup_auto_reorder ?? true`, `(data.open_promise_player_ids ?? [])`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "components/Roster"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "components/Roster" && npm run build && npm run lint
git add frontend/src/components/Roster.tsx frontend/src/components/Roster.test.tsx
git commit -m "test(roster): lock #92 nullish-field tolerance + #36 Sparkline NO-DATA gate before reskin"
```

---

### Task 6: Roster reskin → CSS Module + `Table` density (Comfortable cards / Compact numbers); CeilingBadge + StatBar wired

> **Why:** Audit §3 P1/P2/P3/P7 on Roster: pervasive inline styles (the sort-indicator chip `Roster.tsx:292-305`, the `Ceil` literal `#475569` `:427`, `potentialColor` literals `:42-45`), the player-name span has no ellipsis (P2), the inline `rl-ratings` min-width forces horizontal scroll (P3 `index.css:6033`), sub-legible fonts (P7). The reskin moves Roster's OWN markup to `Roster.module.css` (token-only) and expresses the Detailed/Compact toggle through the shared `Table` **density** (`comfortable`/`compact`) per design §4. The **Comfortable** body uses `StatBar` (visual cards) + `CeilingBadge` (gold glow on the potential cell); **Compact** stays dense tabular numbers. **All sort/selection/click logic, the player-name `<button>`, the role TermTip cell (#58), and the four glance cells stay structurally intact** — only the styling substrate changes. The #57 sort (Task 4) and #92/#36 guards (Task 5) must stay green through the reskin.

**Audit numbers + test strategy:** #58 vitest (role TermTip only for the 8 known archetypes; plain badge otherwise) · all prior Roster behaviors (#57, #92, #36) held through the reskin.

**Constraints (window freezes):** module CSS ONLY (no `index.css` edit); re-point `StatusMessage` import from `./ui` → `../ui` shim (Phase-1); `TermTip`/`getTerm` stay from `../legibility` (frozen, mixed look OK); the existing `dm-badge`/`dm-kicker` global classes the archetype badge/glance cells use may stay referenced (they are legacy globals the integrator handles later — do NOT delete them, do NOT depend on changing them); token-only `*.module.css`.

**Files:** create `frontend/src/components/Roster.module.css`; modify `frontend/src/components/Roster.tsx`; extend `frontend/src/components/Roster.test.tsx`.

- [ ] **Step 1: Add the #58 RED assertions** (extend the test file)

```tsx
import { render, screen } from '@testing-library/react';
// (reuse the mocks + mockRoster helper from Tasks 4-5)

describe('Roster role badge (audit #58 — TermTip only for the 8 known archetypes)', () => {
  it('wraps a known archetype role in a TermTip', () => {
    mockRoster([PLAYER({ id: 'k', name: 'Known', role: 'Sharpshooter' })]);
    render(<Roster />);
    // the legibility TermTip renders its term as a button with the term label
    expect(screen.getByText('SHARPSHOOTER')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sharpshooter/i })).toBeInTheDocument();
  });
  it('renders an unknown role as a plain badge (no TermTip button)', () => {
    mockRoster([PLAYER({ id: 'u', name: 'Unknown', role: 'Freelancer' })]);
    render(<Roster />);
    expect(screen.getByText('FREELANCER')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /freelancer/i })).not.toBeInTheDocument();
  });
});

describe('Roster density toggle (design §4 Comfortable/Compact)', () => {
  it('switches the table density class via the existing view toggle', async () => {
    mockRoster([PLAYER({ id: 'd', name: 'Dense' })]);
    render(<Roster />);
    const table = screen.getByTestId('roster-table');
    expect(table.className).toMatch(/comfortable/);
    await userEvent.click(screen.getByRole('button', { name: 'Compact' }));
    expect(screen.getByTestId('roster-table').className).toMatch(/compact/);
  });
});
```

> The TermTip rendering assertion mirrors the live `legibility/TermTip` output (a `<button>` for the term). If the exact accessible name differs at implementation time, adjust the matcher to the real TermTip output — these guard the #58 known-vs-unknown branch, not a specific label string.

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "components/Roster"`. Expected: FAIL (`roster-table` testid + density wiring not present; #58 cases need the post-reskin markup).

- [ ] **Step 3: Implement the reskin**
  - Re-point imports: `import { StatusMessage } from '../ui';` (Phase-1 shim) and add `import { Table, StatBar, CeilingBadge } from '../ui';` and `import type { CeilingGradeLetter } from '../ui';`. Keep `TermTip` from `../legibility`.
  - Replace the `<table className={`rl-table ${view}`}>` (`Roster.tsx:330`) with `<Table density={view === 'detailed' ? 'comfortable' : 'compact'} data-testid="roster-table" className={styles.rosterTable}>` — keep the `<thead>`/`<tbody>` content; the `Table` primitive supplies the wrapper + density. Map the `view` state literal `'detailed' | 'compact'` to `'comfortable' | 'compact'` at the call site (keep the `view` state name and the segment buttons' `Detailed`/`Compact` labels — only the density prop maps).
  - **Comfortable (detailed) body:** replace the inline `RatingMini` row with `StatBar` (`<StatBar label="ACC" value={...} title={RATING_TOOLTIPS.ACC} />` etc.), preserving the six ratings + tooltips. Replace the potential cell's inline `potentialColor`/`Ceil #475569` block with `CeilingBadge` driven by a grade derived from `potential_ceiling` (add a local `ceilingGradeFromCeiling(ceiling: number | null): CeilingGradeLetter | null` helper: `>=92→'A+'`, `>=88→'A'`, `>=84→'A-'`, `>=80→'B+'`, `>=76→'B'`, `>=72→'B-'`, else `'C'`; return `null` when `potential_ceiling == null` and render no badge). Keep the rendered `potential_tier` text + `scouting_confidence` pips (do NOT change the pip count behavior — that is a separate P9 item out of this phase's behavior set).
  - **Compact body:** keep the dense per-column numeric `<td>`s (the existing `tier-elite/good/avg/poor` colorization moves into `Roster.module.css` classes).
  - Move EVERY remaining inline `style={{…}}` (the sort-indicator chip, the `rl-head`, glance cells, footer) into `Roster.module.css` token-driven classes. The four glance components (`LineupSummary`/`ArchetypeMix`/`PotentialBlock`/`AgeCurve`) keep their structure; their inline segment colors (`var(--dm-orange)` etc.) may stay as inline custom-prop assignments if they are runtime values, otherwise move to module classes.
  - Keep the role cell exactly: `ROLE_TERM_ID[player.role] ? <TermTip…>{archetypeBadge}</TermTip> : archetypeBadge` (#58). Keep the player-name `<button>` (WT-21 a11y) and add `min-width:0` + ellipsis to the name span via a module class (fixes P2).
  - Keep all `data-testid` hooks added in Tasks 4–5 (`roster-sort`, `roster-row`, `roster-row-name`, `roster-row-starter-pin`, `roster-ovr-nodata`) + the new `roster-table`.
  - **Token discipline:** `Roster.module.css` uses only `var(--…)` tokens (no raw hex/px beyond `0`/`1px`). The runtime segment colors are inline custom-prop assignments in the `.tsx`, not literals in the CSS.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "components/Roster"`. Expected: PASS (all Roster behaviors — #57, #92, #36, #58 — green through the reskin).

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "components/Roster" && npm run build && npm run lint
git add frontend/src/components/Roster.tsx frontend/src/components/Roster.module.css frontend/src/components/Roster.test.tsx
git commit -m "feat(roster): reskin to CSS Module + Table density; StatBar/CeilingBadge wired; hold #57/#58/#36/#92"
```

---

## Phase 3C — Lineup Editor

### Task 7: LineupEditor reskin → CSS Module + `Modal`/`ActionButton` shims; hold #51, #52, #53, #55

> **Why:** Audit §3 P1/P2/P3/P4 on LineupEditor: built almost entirely from inline-style objects (`:223-232` panel, `:276-285` the fixed `1fr 1fr` two-column grid that does not collapse — P3 "high", `:413-420` the nested `maxHeight:24rem` inner scroll — P4 "medium", slot/bench name spans with no `min-width:0` — P2). The reskin moves LineupEditor's OWN markup to `LineupEditor.module.css` and re-points `Dialog`→`Modal` + `ActionButton` to the Phase-1 `src/ui` shims (import path only — NO API remap). **The four lineup-truth behaviors must hold:** #51 (server is the source of truth for resolved order — `onSaved(result.ordered_player_ids)` splices the server order, never a local array), #52 (auto-reorder OFF flip announced explicitly, only on the first actual change), #53 (persistent computed stale-lineup note — `data-testid="lineup-stale-note"`, an ANTI-STRIP hook), #55 (save errors mapped to plain language, keyed to the offending slot, `role="alert"`).

**Audit numbers + test strategy:** #51 vitest (save splices server order) · #52 vitest (auto-reorder-off announce-once) · #53 vitest (stale note present + the `lineup-stale-note` anti-strip hook) · #55 vitest (mapped error, `role=alert`, offending-slot key).

**Constraints (window freezes):** module CSS ONLY; re-point `import { ActionButton, Dialog } from '../ui'` → `import { ActionButton, Modal } from '../../ui'` and replace `<Dialog …>` with `<Modal …>` (the Phase-0 `Modal` primitive ports the same focus-trap + `panelClassName` API — verify prop parity: `Modal` takes `onClose`/`label`/`labelledBy`/`panelClassName`/`className` + forwards `data-*`; it does NOT take `panelStyle`, so move the inline `panelStyle` sizing into a `panelClassName` module class). `TermTip` stays from `../../legibility` (frozen). `commandApi`/`ApiError` imports unchanged. NO `ActionButton`→`ActionBar` remap.

**Files:** create `frontend/src/components/lineup/LineupEditor.module.css`, `frontend/src/components/lineup/LineupEditor.test.tsx`.

- [ ] **Step 1: Write the failing tests** — mock `commandApi` from `../../api/client`; render with a roster where a benched player out-rates a starter (to trigger #53).

```tsx
// frontend/src/components/lineup/LineupEditor.test.tsx
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { commandApi, ApiError } from '../../api/client';
import { LineupEditor } from './LineupEditor';

vi.mock('../../api/client', async (orig) => {
  const actual = await orig<typeof import('../../api/client')>();
  return {
    ...actual,
    commandApi: { saveLineup: vi.fn(), autoAssignLineup: vi.fn(), setLineupAutoReorder: vi.fn() },
  };
});

const P = (id: string, ovr: number, over: Record<string, unknown> = {}) => ({
  id, name: id, age: 24, overall: ovr, role: 'Sharpshooter',
  potential_tier: 'Mid', scouting_confidence: 2, potential_ceiling: 80, headroom: 4,
  projected_growth: 'plateauing', ovr_season_trend: null,
  ratings: { accuracy: ovr, power: ovr, dodge: ovr, catch: ovr, stamina: ovr, tactical_iq: ovr },
  ...over,
});

// 6 starters + 1 bench player who out-rates the weakest starter -> stale note.
const ROSTER = [P('s1', 80), P('s2', 78), P('s3', 76), P('s4', 74), P('s5', 72), P('s6', 60), P('benchStar', 90)];
const DEFAULT = ['s1', 's2', 's3', 's4', 's5', 's6'];

const props = () => ({
  roster: ROSTER, defaultLineup: DEFAULT, autoReorder: true,
  onClose: vi.fn(), onSaved: vi.fn(), onAutoReorderChange: vi.fn(),
});

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('LineupEditor truth behaviors (#51, #52, #53, #55)', () => {
  it('#53: shows the persistent stale-lineup note via the lineup-stale-note hook (anti-strip)', () => {
    render(<LineupEditor {...props()} />);
    const note = screen.getByTestId('lineup-stale-note');
    expect(note).toHaveTextContent(/benchStar/);
    expect(note).toHaveTextContent(/OVR 90/);
  });

  it('#51: a save splices the SERVER ordered_player_ids, never the local array', async () => {
    const serverOrder = ['benchStar', 's2', 's3', 's4', 's5', 's1'];
    vi.mocked(commandApi.saveLineup).mockResolvedValue({ ordered_player_ids: serverOrder, lineup_auto_reorder: true } as never);
    const p = props();
    render(<LineupEditor {...p} />);
    // select slot 1, then swap in the bench star
    await userEvent.click(screen.getByTestId('lineup-slot-0'));
    await userEvent.click(screen.getByTestId('lineup-bench-benchStar'));
    await waitFor(() => expect(p.onSaved).toHaveBeenCalledWith(serverOrder));
  });

  it('#52: a manual save that flips auto-reorder off announces it once, only on the real change', async () => {
    vi.mocked(commandApi.saveLineup).mockResolvedValue({ ordered_player_ids: DEFAULT, lineup_auto_reorder: false } as never);
    const p = props(); // autoReorder starts true
    render(<LineupEditor {...p} />);
    await userEvent.click(screen.getByTestId('lineup-slot-0'));
    await userEvent.click(screen.getByTestId('lineup-bench-benchStar'));
    expect(await screen.findByText(/Auto-reorder turned off/)).toBeInTheDocument();
    await waitFor(() => expect(p.onAutoReorderChange).toHaveBeenCalledWith(false));
  });

  it('#55: a position_count error maps to plain language with role=alert', async () => {
    vi.mocked(commandApi.saveLineup).mockRejectedValue(new ApiError('position_count', 400));
    render(<LineupEditor {...props()} />);
    await userEvent.click(screen.getByTestId('lineup-slot-0'));
    await userEvent.click(screen.getByTestId('lineup-bench-benchStar'));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/exactly 6 starters/);
  });
});
```

> **ApiError constructor note:** confirm `ApiError`'s real signature in `api/client.ts` before writing (`new ApiError(message, status?)` is the assumed shape from `reasonToMessage(err.message)` usage). If the constructor differs, adjust the test instantiation to the real signature — do not invent it.

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "lineup/LineupEditor"`. Expected: FAIL (the `lineup-slot-0` / `lineup-bench-benchStar` test hooks don't exist; the `Modal` swap not done). The `lineup-stale-note` case should PASS even pre-reskin (the hook already exists at `:486`).

- [ ] **Step 3: Implement the reskin**
  - Re-point imports: `import { ActionButton, Modal } from '../../ui';`. Replace `<Dialog label="Lineup Editor" onClose={onClose} panelClassName="dm-panel" panelStyle={{…}}>` with `<Modal label="Lineup Editor" onClose={onClose} panelClassName={styles.panel}>` and move all `panelStyle` sizing (`maxWidth:52rem`, `maxHeight:90vh`, flex column, overflow) into the `.panel` module class.
  - Move EVERY inline `style={{…}}` block (header `:234-242`, title `:245-255`, the two-column body grid `:276-285`, the slot buttons `:347-371`, the bench buttons `:428-444`, the footer `:460-470`, the auto-reorder label, the Auto-Assign button incl. its `onMouseEnter/onMouseLeave` color swaps — replace those with `:hover` module CSS) into `LineupEditor.module.css` token-driven classes.
  - **Fix the P3/P2/P4 layout bugs as part of the reskin:** the body grid becomes a responsive two-column that collapses (`grid-template-columns: repeat(auto-fit, minmax(min(16rem,100%),1fr))` or the `Grid` primitive) instead of fixed `1fr 1fr`; slot/bench name spans get `min-width:0` + ellipsis (use the `Truncate` primitive or a module class); the bench inner `maxHeight:24rem` nested scroll is replaced by the `ScrollRegion` primitive owning a single scroll (no nested fixed-height scroll) OR a module class with `min-height:0` — do not nest a fixed-height scroll inside the Modal's own scroll.
  - Add test hooks: `data-testid={`lineup-slot-${idx}`}` on each starter slot button (`:347`), `data-testid={`lineup-bench-${player.id}`}` on each bench button (`:428`). Keep the existing `data-testid="lineup-stale-note"` (`:486`) byte-identical (anti-strip).
  - Keep ALL logic verbatim: `commit()`, `handleSlotClick`, `handleBenchClick`, `handleAutoAssign`, `handleToggleAutoReorder`, the `staleNote` memo (#53), the `role={error ? 'alert' : 'status'}` status region (#55), the `errorSlot` red-flash + timer cleanup, the `onSaved(result.ordered_player_ids)` splice (#51), the auto-reorder announce-once branch (#52). Keep the `TermTip` "Slot order" usage.
  - **Token discipline:** `LineupEditor.module.css` uses only `var(--…)` tokens. (The `#22d3ee`/`#0f172a`/`#ef4444`/`#fbbf24` literals throughout map to `--volt2`/`--court`/`--volt`/`--gold` tokens — verify each maps to an existing token; if a needed semantic has no token, add it to `tokens.css`, not `index.css`.)

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "lineup/LineupEditor"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "lineup/LineupEditor" && npm run build && npm run lint
git add frontend/src/components/lineup/LineupEditor.tsx frontend/src/components/lineup/LineupEditor.module.css frontend/src/components/lineup/LineupEditor.test.tsx
git commit -m "feat(lineup): reskin LineupEditor to CSS Module + Modal shim; hold #51/#52/#53/#55"
```

---

## Phase 3D — Player Detail modal

### Task 8: PlayerDetailModal reskin → CSS Module + `Modal`/`RatingBar`/`ActionButton` shims; hold #54, #56

> **Why:** Audit §3 P1/P3 on PlayerDetailModal: entirely inline (`:75-85` the fixed `minmax(0,1.05fr) minmax(0,0.95fr)` two-column modal grid that does not collapse — P3 "high"; literals throughout `:56-291`). The reskin moves the modal's OWN markup to `PlayerDetailModal.module.css` and re-points `Dialog`→`Modal` + `RatingBar`/`ActionButton` to the Phase-1 `src/ui` shims (import path only — NO API remap). **The two player-card truth behaviors must hold:** #54 (release blocked, NOT hidden, at the 6-floor with a visible reason; the confirm strip discloses free-agency + broken-promise — `data-testid="release-confirm-strip"` and `data-testid="release-player-btn"`, both ANTI-STRIP hooks), #56 (conditional bio/growth narrative derived from real numbers; the High-Upside ProofChip only when backed — `growing` + `headroom>=12` + `age<=23`).

**Audit numbers + test strategy:** #54 vitest (release blocked-with-reason + confirm-strip disclosures + the two anti-strip hooks) · #56 vitest (bio/growth narrative branches + ProofChip gated on real numbers).

**Constraints (window freezes):** module CSS ONLY; re-point `import { RatingBar, ActionButton, Dialog } from './ui'` → `import { RatingBar, ActionButton, Modal } from '../ui'` and swap `<Dialog>`→`<Modal>` (move `panelStyle` into a `panelClassName` module class — `Modal` has no `panelStyle`). `TermTip`/`ProofChip`/`getTerm` stay from `../legibility` (frozen, mixed look OK). NO `ActionButton`→`ActionBar` remap. `RatingBar` here is the Phase-1 `src/ui` shim (signature-identical), not `ui.tsx`.

**Files:** create `frontend/src/components/PlayerDetailModal.module.css`, `frontend/src/components/PlayerDetailModal.test.tsx`.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/components/PlayerDetailModal.test.tsx
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PlayerDetailModal } from './PlayerDetailModal';

const P = (over: Record<string, unknown> = {}) => ({
  id: 'p1', name: 'Mara Vex', age: 22, overall: 78, role: 'Sharpshooter',
  potential_tier: 'High', scouting_confidence: 3, potential_ceiling: 92, headroom: 14,
  projected_growth: 'growing', ovr_season_trend: null,
  bio_strongest_attr: 'Accuracy', bio_secondary_attr: 'Power',
  ratings: { accuracy: 80, power: 76, dodge: 70, catch: 68, stamina: 72, tactical_iq: 74 },
  ...over,
});

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('PlayerDetailModal player-card truth (#54, #56)', () => {
  it('#54: release is blocked (not hidden) at the 6-floor with a visible reason', () => {
    render(
      <PlayerDetailModal
        player={P()} onClose={vi.fn()} onRelease={vi.fn().mockResolvedValue(undefined)}
        releaseBlockedReason="Roster is at the 6-player floor — sign someone before releasing." hasOpenPromise={false}
      />,
    );
    const btn = screen.getByTestId('release-player-btn');
    expect(btn).toBeDisabled();                                  // blocked, not hidden
    expect(btn).toHaveAttribute('title', expect.stringContaining('6-player floor'));
  });

  it('#54: the confirm strip discloses free-agency + the broken-promise warning', async () => {
    render(
      <PlayerDetailModal
        player={P()} onClose={vi.fn()} onRelease={vi.fn().mockResolvedValue(undefined)}
        releaseBlockedReason={null} hasOpenPromise
      />,
    );
    await userEvent.click(screen.getByTestId('release-player-btn'));
    const strip = screen.getByTestId('release-confirm-strip');     // anti-strip hook
    expect(within(strip).getByText(/free-agent pool/)).toBeInTheDocument();
    expect(within(strip).getByText(/OPEN promise/)).toBeInTheDocument();
  });

  it('#56: the High-Upside ProofChip shows ONLY when growing + headroom>=12 + age<=23', () => {
    const { rerender } = render(<PlayerDetailModal player={P()} onClose={vi.fn()} />);
    expect(screen.getByText('High Upside')).toBeInTheDocument();
    // break each precondition -> chip gone
    rerender(<PlayerDetailModal player={P({ age: 28 })} onClose={vi.fn()} />);
    expect(screen.queryByText('High Upside')).not.toBeInTheDocument();
    rerender(<PlayerDetailModal player={P({ headroom: 5 })} onClose={vi.fn()} />);
    expect(screen.queryByText('High Upside')).not.toBeInTheDocument();
    rerender(<PlayerDetailModal player={P({ projected_growth: 'plateauing' })} onClose={vi.fn()} />);
    expect(screen.queryByText('High Upside')).not.toBeInTheDocument();
  });

  it('#56: bio narrative reads from real numbers (headroom drives the develop-target line)', () => {
    render(<PlayerDetailModal player={P({ potential_tier: 'High', headroom: 14 })} onClose={vi.fn()} />);
    expect(screen.getByText(/14 OVR of headroom ahead/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "components/PlayerDetailModal"`. Expected: these PASS against the CURRENT modal (the `release-player-btn`/`release-confirm-strip` hooks + the #56 logic already exist). This establishes the green baseline the reskin must hold. (If an assertion mismatches the current DOM, correct it to the current truth — these are non-regression guards.)

- [ ] **Step 3: Implement the reskin**
  - Re-point imports: `import { RatingBar, ActionButton, Modal } from '../ui';`. Replace `<Dialog label=… labelledBy="player-detail-title" onClose=… panelClassName="dm-panel" panelStyle={{…}}>` with `<Modal label=… labelledBy="player-detail-title" onClose=… panelClassName={styles.panel}>` and move the `panelStyle` sizing (`maxWidth:46rem`, `maxHeight:90vh`, flex column, overflow) into `.panel`.
  - **Font token name collision — fix before committing:** `PlayerDetailModal.tsx:59` has `fontFamily: 'var(--font-display)'` (inline style referencing the legacy `index.css` custom property, which resolves to Oswald/Bahnschrift). The Floodlight token system defines `--font-disp` (NOT `--font-display`) in `tokens.css:15` (Archivo Expanded). These are different names; using `--font-display` in the module CSS will silently fall back to the legacy font. Grep `PlayerDetailModal.tsx` for any `--font-display` occurrence before moving the heading style into the module class, and substitute `var(--font-disp)` in all module CSS equivalents. The heading `.playerName` module class should use `font: … var(--font-disp)`.
  - Move EVERY inline `style={{…}}` (header `:56-70`, the two-column body grid `:75-85`, the Bio card `:90-118`, the Potential/Growth cards `:120-176`, the Ratings column `:180-202`, the release confirm strip `:207-264`, the footer `:266-291`) into `PlayerDetailModal.module.css` token classes.
  - **Fix the P3 layout bug:** the body grid becomes a responsive two-column that collapses on narrow widths (`repeat(auto-fit, minmax(min(15rem,100%),1fr))` or the `Grid` primitive) instead of fixed `minmax(0,1.05fr) minmax(0,0.95fr)`.
  - Optionally render the Potential card's ceiling using the new `CeilingBadge` (derive the grade from `potential_ceiling` with the same helper as Task 6) for visual consistency — keep the existing `Ceiling OVR {potential_ceiling}` + headroom text and the `growth.ceiling`/`growth.headroom` TermTips (do NOT change their copy or the #56 branches).
  - Keep ALL logic verbatim: the `confirmingRelease`/`releasing`/`releaseError` state, the `onRelease().catch(...).finally(...)` flow, the `releaseBlockedReason` disabled+title (#54), the `hasOpenPromise` warning (#54), the bio/growth narrative ternaries (#56), the ProofChip gate `growing && headroom>=12 && age<=23` (#56), the `throw_selection_iq`/`catch_courage` conditional RatingBars. Keep `data-testid="release-confirm-strip"` and `data-testid="release-player-btn"` byte-identical (anti-strip).
  - **Token discipline:** module CSS uses only `var(--…)` tokens. The release-strip rose/red literals (`#be123c`, `rgba(244,63,94,…)`, `#fda4af`, etc.) map to `--volt`/`--volt-soft`/`--volt2` (or add a `--danger-*` token to `tokens.css` if the existing volt palette is too orange for the destructive strip — owner-style judgment; volt is the redesign's only-loud color and is the natural destructive cue). Decide at Task 9 token-clean time.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "components/PlayerDetailModal"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "components/PlayerDetailModal" && npm run build && npm run lint
git add frontend/src/components/PlayerDetailModal.tsx frontend/src/components/PlayerDetailModal.module.css frontend/src/components/PlayerDetailModal.test.tsx
git commit -m "feat(player): reskin PlayerDetailModal to CSS Module + Modal shim; hold #54/#56"
```

---

## Phase 3E — Phase gate

### Task 9: Sparkline token pass + full Phase-3 per-phase gate (worktree, old index.css present)

> **Why:** The reskinned screens now own their styling and must be token-clean **before** the integrator widens `SCAN_DIRS` in STEP 3. `roster/Sparkline.tsx` (`#22d3ee` stroke + `#1e293b` fallback fill) lives in `src/components/roster`, the dir the integrator will scan — token it now so the gate is green when scanned. Then run the complete per-phase gate **in the worktree with the OLD `index.css` still present** (build + lint + lint:tokens + full vitest + smoke e2e). The integrator runs the full `tsc --noEmit` + full vitest + the `index.css` deletion + the SCAN_DIRS append later in STEP 3 — **this plan does none of those.**

**Files:** modify `frontend/src/components/roster/Sparkline.tsx` (token the two color literals; keep the `data.length < 2` fallback behavior #36 byte-identical).

- [ ] **Step 1: Token the Sparkline colors** — replace the `stroke="#22d3ee"` with `stroke="var(--volt2)"` (or `--gold` if the OVR trend should read as talent — judgment; the redesign uses volt for live/active accents, so `--volt2` matches the prior cyan accent's role) and the fallback `background: '#1e293b'` with `var(--line)`. **Do NOT change** the `if (data.length < 2) return <fallback/>` guard — #36's honest NO-DATA behavior is the contract. The `viewBox`/`width`/`height` numeric coordinates are allowed by the gate's `ALLOW_LINE` (`viewBox`) — but the `width={60} height={20}` attributes are NOT viewBox; if the gate flags them once scanned, the integrator handles it, OR move the fixed dims to a fluid viewBox per spec §5 (optional polish; not required for the per-phase gate since `src/components/roster` is not yet scanned in the worktree).

- [ ] **Step 2: Self-verify token discipline on the new dirs** — temporarily (do NOT commit) add `'src/components/roster'` + the three screen-module files to a local copy of the `SCAN_DIRS`/`SCAN_FILES` check, run `npm run lint:tokens`, confirm the new modules + Sparkline are clean, then revert the `check-tokens.mjs` change (the integrator owns that append). If it flags a real literal, replace it with a token (or add a token to `tokens.css`) and re-run.

```bash
cd frontend
# scratch self-check only — revert before committing:
node -e "let s=require('fs').readFileSync('scripts/check-tokens.mjs','utf8'); s=s.replace(\"['src/ui', 'src/styles']\", \"['src/ui','src/styles','src/components/roster']\"); require('fs').writeFileSync('scripts/check-tokens.mjs.scratch', s)" \
  && node scripts/check-tokens.mjs.scratch ; rm -f scripts/check-tokens.mjs.scratch
```

- [ ] **Step 3: Run the full Phase-3 per-phase gate**

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e
```

Expected: all FE tests pass (the two new primitives + the three screen suites + the existing Phase-0/1 suites); build clean (`tsc -b` + vite); eslint clean; token gate clean (`src/ui` enforced — the two new primitives are clean); root Playwright e2e smoke green. **The OLD `index.css` is still present and that is correct** — the reskinned components stopped referencing the dead `.rl-*` rules; STEP-3 removes those rules.

- [ ] **Step 4: Manual smoke** — launch `python -m dodgeball_sim` on **port 8010** (NOT 8000 — owner's live game), load an existing save, open the Roster tab: confirm the Comfortable view shows StatBars + the gold CeilingBadge on high-ceiling players; toggle to Compact (dense numbers); sort by Potential and confirm Mid/Low/Raw players are distinctly ordered (#57); open a player card (Modal, responsive two-column, ratings, release-blocked-with-reason at the 6-floor); open the Lineup Editor (slots/bench, stale note when a bench star out-rates a starter, save announces auto-reorder-off). No console errors.

- [ ] **Step 5: Commit + ready for the controller merge**

```bash
git add frontend/src/components/roster/Sparkline.tsx
git commit -m "chore(roster): token Sparkline colors for STEP-3 SCAN_DIRS (keep #36 NO-DATA gate)"
```

The controller merges the Phase-3 worktree branch; the **serial integrator** (STEP 3) then deletes the dead `.rl-*` / lineup / player-modal `index.css` selectors, appends `src/components/roster` + the screen-module files to `SCAN_DIRS`, and re-runs the full `tsc --noEmit` + full vitest + e2e smoke. **None of that is in this plan.**

---

## Self-Review

**Behavior coverage — all 9 Phase-3 audit behaviors mapped to a task + the checklist test strategy:**

| # | Behavior | Task | Strategy |
|---|---|---|---|
| 36 | OVR Sparkline only with >=2 points; else honest NO-DATA fallback | Tasks 5, 9 | vitest (Sparkline gate) + token-preserve ✓ |
| 51 | Server is source of truth for resolved lineup order (splice ordered_player_ids) | Task 7 | vitest (save splices server order) ✓ |
| 52 | Auto-reorder OFF flip announced explicitly, only on first actual change | Task 7 | vitest (announce-once) ✓ |
| 53 | Persistent computed stale-lineup warning (`lineup-stale-note` anti-strip) | Task 7 | vitest (note present + hook) ✓ |
| 54 | Release blocked (not hidden) at 6-floor with reason; confirm strip discloses FA + broken promise | Task 8 | vitest (blocked+title + `release-confirm-strip`/`release-player-btn` hooks) ✓ |
| 55 | Lineup save errors → plain language, keyed to offending slot, `role=alert` | Task 7 | vitest (mapped error, alert) ✓ |
| 56 | Conditional bio/growth narrative from real numbers; High-Upside ProofChip only when backed | Task 8 | vitest (narrative branches + ProofChip gate) ✓ |
| 57 | Potential sort uses explicit tier-rank map (now `domain/tiers.ts`) + tie-break by OVR; starters-first for lineup sort | Task 4 | vitest (Roster sort; Mid/Low/Raw distinct) ✓ |
| 58 | Role/archetype TermTip only for 8 known archetypes, plain badge otherwise | Task 6 | vitest (known-vs-unknown branch) ✓ |
| 92 | Response-field tolerance via nullish fallbacks (`default_lineup ?? []`, `lineup_auto_reorder ?? true`, etc.) | Task 5 | vitest (missing-field payload) ✓ |

**Phase-specific requirements honored:**
- **CeilingBadge primitive (deferred §4 / §3.5 ceiling ladder)** — Task 1: gold-glow ladder A+→C with a single source-of-truth `CEILING_LADDER` legend, token-only CSS (the on-gold ink uses `var(--gold-ink)` — defined in `tokens.css` and used by `Tag.module.css` `.talent`; no raw hex is acceptable in `src/ui`), tests, barrel export (Task 3) ✓.
- **StatBar primitive (deferred §4)** — Task 2: glanceable rating, brightness=strength via class tiers (not opacity-crush), `--fill` custom property, token-only CSS, tests, barrel export (Task 3) ✓.
- **Roster sort re-pointed to `src/domain/tiers.ts`** — Task 4 fixes the silent Mid/Low/Raw bucket (#57) ✓.
- **#92 nullish-fallback tolerance** — Task 5 ✓. **#51 server = source of truth for resolved lineup order** — Task 7 (`onSaved(result.ordered_player_ids)`) ✓.
- **Comfortable visual-cards + Compact dense-numbers via `src/ui` Table density** — Task 6 maps `view` → `Table density` ✓.

**Window freezes encoded as explicit constraints:** NO `index.css` edits/deletions (stated in HARD RULES + every reskin task + Task 9; no deletion task exists) ✓ · NO `ui.tsx` edits — import re-point only, NO ActionButton→ActionBar remap (Tasks 6/7/8 re-point to `../ui`/`../../ui` shims, ActionButton stays ActionButton) ✓ · FROZEN `matchResult.ts` (not imported), `legibility/*` incl. `CeilingGrade` (read-only; new `CeilingBadge` is distinct), shared `command-action-bar`/`command-policy-overlay` (untouched), `check-tokens.mjs` (integrator owns SCAN_DIRS; Task 9 self-checks via a scratch copy then reverts) ✓ · Phase-1 contracts (`appContracts.ts`, `PlayoffBracket`/`ProgramModal`) noted as not-directly-consumed by these screens ✓.

**`data-*` anti-strip vitests as HARD RED preconditions:** the hooks actually present on Phase-3 screens (`lineup-stale-note` #53, `release-confirm-strip` + `release-player-btn` #54) are enumerated in the HARD RULES section and tested in Tasks 7–8 before/through the rebuild. The global proof hooks (`data-broadcast-proof-source`/`data-player-outcome`) were grep-confirmed to live on replay/bracket surfaces, NOT here, so they are not fabricated ✓.

**Per-phase gate runs in the worktree with the old `index.css` present** (Task 9: test + build + lint + lint:tokens + smoke e2e); the integrator's deletion + full tsc/vitest + SCAN_DIRS append is explicitly deferred to STEP 3 ✓.

**Placeholder scan:** none. Every task has runnable test code + concrete edits with exact line anchors from the current source. The two "confirm the real signature before writing" notes (ApiError constructor in Task 7; TermTip accessible-name in Task 6) are correctness guards against inventing an API, not logic placeholders — both name the fallback action.

**Type/name consistency:** `CeilingGradeLetter`/`CEILING_LADDER`/the `g0`–`g5` tier classes are used identically in `CeilingBadge.tsx`, its test, and the barrel; `StatBar` props (`label`/`value`/`max`) + the `elite/good/avg/poor` tiers + the `--fill` custom prop match between component and test; `potentialRank`/`POTENTIAL_TIERS` are consumed from the existing `domain/tiers.ts` (verified present: `['Elite','High','Mid','Low','Raw']`, lower=better, unknown-last). The `Table` `density` union (`'comfortable' | 'compact'`) matches the live primitive (verified `src/ui/Table.tsx`). Player fields referenced (`potential_ceiling`, `potential_tier`, `scouting_confidence`, `ovr_season_trend`, `headroom`, `projected_growth`, `bio_strongest_attr`, `default_lineup`, `lineup_auto_reorder`, `open_promise_player_ids`, `ratings.throw_selection_iq`, `ratings.catch_courage`) are verified against `types.ts`. The `Modal` prop surface (`onClose`/`label`/`labelledBy`/`panelClassName`/`className`, forwards `data-*`; no `panelStyle`) matches the Phase-0 `src/ui/Modal` — the `Dialog`→`Modal` swap moves `panelStyle` into a `panelClassName` module class (called out in Tasks 7/8). The path discrepancy between the audit (`lineup/LineupEditor.tsx`, top-level `PlayerDetailModal.tsx`) and the task brief (`roster/…`) was resolved to the **actual on-disk paths** (verified via glob): `components/lineup/LineupEditor.tsx`, `components/PlayerDetailModal.tsx`, `components/roster/playerDisplay.ts`.

**Note on `playerDisplay.ts`:** the brief names `roster/playerDisplay.ts` in scope. It is the canonical name/role/OVR formatter (`formatPlayerName`/`formatRole`/`formatOverall`) and is consumed by the founding-draft picker for draft/roster parity (#58 "canonical formatters keep draft/roster parity"). The live `Roster.tsx` does NOT currently import it (it renders `player.name`/`player.role`/`player.overall` directly). This phase does not change `playerDisplay.ts` (no styling, pure formatters) and does not force the Roster onto it — doing so is a behavior-neutral refactor out of the reskin's risk budget. If parity-hardening is desired, it belongs in a separate task; this plan leaves the formatters frozen and notes #58's parity is already held by the founding-draft consumer + the shared `ROLE_TERM_ID` map. (Flagged here for the controller rather than silently expanding scope.)

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-floodlight-phase-3-roster.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task (1→9), review between tasks. Tasks 6/7/8 (the three reskins) are the highest blast radius; gate hard after each. Tasks 1–3 (primitives) are prerequisites for Task 6.
2. **Inline Execution** — execute tasks in this session with checkpoints. Do NOT touch `index.css` or `check-tokens.mjs`; the controller merges and the serial integrator (STEP 3) owns the legacy `.rl-*` deletion + SCAN_DIRS append.
