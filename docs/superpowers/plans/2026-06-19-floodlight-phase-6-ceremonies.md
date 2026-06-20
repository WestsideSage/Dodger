# Floodlight Phase 6 — Ceremonies + Offseason Beats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the offseason ceremony + beat surfaces (`ceremonies/*`) onto the Floodlight token system using CSS Modules, while keeping the 16 Phase-6 trust behaviors green (#17, #18, #29, #31, #32, #35, #67–#75) and every truth-provenance `data-*` hook intact. This is one of the **six concurrent worktree lanes** that branch off the merged post-Phase-1 trunk; it creates `*.module.css` only and **defers all `index.css` deletion to the serial integrator (STEP 3)**.

**Architecture:** Each ceremony component moves from inline-style objects + raw hex literals (audit §3 P1/P2/P3 "all ceremony components hardcode hex + ad-hoc gap values") to scoped `*.module.css` driven by `src/styles/tokens.css`. The shared offseason chrome — the `command-action-bar` sticky bar, the `command-offseason-progress` pip strip, the `command-offseason-shell` wrapper — is a **SHARED global** used by ~10 of these files AND by Phase 2 / Phase 5; it MUST survive untouched (it is deleted only in Phase 8 behind a grep-zero gate). The faithfulness logic (worlds_user receipt, missed_playoffs gate, signed_count single-source, veto-aware latch, sign-over-cut, zero-floats, training-credit receipt) is preserved verbatim — only the rendering substrate changes. `ChampionReveal.tsx` statically imports the **frozen P4 `PlayoffBracket`**; this plan consumes that signature and never alters it.

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (harness from Phase 0).

**Spec:** [2026-06-19-ui-redesign-design.md](../specs/2026-06-19-ui-redesign-design.md) · **Non-regression contract:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md) §1 (Ceremonies/offseason screens), §2.B #17/#18, §2.C #29, §2.D #31/#32/#35, §2.H #67–#75, §3 P1/P2/P3 ceremony rows · **Checklist:** [floodlight-preservation-checklist.md](floodlight-preservation-checklist.md) Phase 6 row · **Orchestration contract:** [2026-06-19-floodlight-parallelization-strategy.md](2026-06-19-floodlight-parallelization-strategy.md) (DAG `6 → [0,1,4]`; merge-strict `6→4`) · **Foundations + style template:** [2026-06-19-floodlight-phase-0-foundations.md](2026-06-19-floodlight-phase-0-foundations.md) · **Phase-1 locked contracts:** [2026-06-19-floodlight-phase-1-app-shell.md](2026-06-19-floodlight-phase-1-app-shell.md)

**Branch:** isolated git worktree branched from the **merged post-Phase-1 trunk** (per strategy STEP 2). All Phase-6 commits land on that branch. **Do NOT merge** (the controller/integrator merges; index.css deletion happens in STEP 3).

---

## Phase-6 scope (the files this plan rebuilds)

| Component | File | Beat key / role | Key data-* + behaviors |
|---|---|---|---|
| CeremonyShell | `ceremonies/CeremonyShell.tsx` | shared staged-reveal frame (AwardsNight, Graduation, SigningDay) | `command-action-bar`, `command-offseason-progress`, `role="status"` skip hint |
| ChampionReveal | `ceremonies/ChampionReveal.tsx` | `champion` | `data-testid="offseason-champion"`, **consumes frozen P4 PlayoffBracket** (#40 title_count-only) |
| RecapStandings | `ceremonies/RecapStandings.tsx` | `recap` | **#17 worlds_user**, **#18 missed_playoffs**, #32 wire empties, #35 | `data-testid="recap-missed-playoffs"`/`recap-finances`/`recap-pyramid` |
| EventBracket | `ceremonies/EventBracket.tsx` | inside EventsBeat | **`data-player-outcome`** (#16-family/#71 outcome ribbon), `data-testid="event-bracket"` |
| EventsBeat | `ceremonies/EventsBeat.tsx` | `events` | `data-testid="offseason-events"`/`event-result-card`/`giant-killing`; #35 empty |
| MediaEvent | `ceremonies/MediaEvent.tsx` | `media_event` | `data-testid="offseason-media"`/`media-result`/`media-event`; #31 null payload |
| DevelopmentResults | `ceremonies/DevelopmentResults.tsx` | `development` | **#71 zero-floats / #72 training-credit `.toFixed(1)` receipt** (`data-testid="training-credit-receipt"`) |
| RecapStandings finances | (above) | — | #71 integer money via `formatK` |
| RecruitmentChoice | `ceremonies/RecruitmentChoice.tsx` | `recruitment` & `can_recruit` | **#73 sign-over-cut**, **#74 skip/lock gate**, #23 band-vs-FA OVR (`KnownValue`/`CeilingGrade`), `data-testid="signing-release-picker"` |
| RookieClassPreview | `ceremonies/RookieClassPreview.tsx` | `rookie_class_preview` | #31 honest upside; `data-testid="offseason-rookie-preview"` |
| StructuredOffseasonBeats | `ceremonies/StructuredOffseasonBeats.tsx` | `records_ratified`, `hof_induction` | **#70 milestone/bookkeeping tiering + #35 non-dead-end empty + #71 `formatValue`**, `data-broadcast-proof-source`, `data-testid="record-milestone-card"` etc. |
| TransferPeriod | `ceremonies/TransferPeriod.tsx` | `transfer_period` | **#69 veto-aware re-sign latch + disabled Re-sign**, `data-testid="transfer-expiring-*"`/`transfer-buyout-*`/`transfer-results` |
| Ceremonies (AwardsNight / Graduation / SigningDay / NewSeasonEve) | `ceremonies/Ceremonies.tsx` | `awards`, `retirements`, `recruitment` (!can_recruit), `schedule_reveal` | **#67 signed_count single-source + #68 player-scope vs LEAGUE labels**, **#75 AwardsNight extra_stats vs season_stat** |

**In-area but NOT rebuilt here (out of Phase-6 scope per the prompt):** `ceremonies/WorldsCrowning.tsx` — listed in the audit's Ceremonies area and mounted by `Offseason.tsx:79`, but it is **not in this plan's assigned file list** and covers #40 (a Phase-8/sweep behavior, not in the Phase-6 checklist row). Leave it byte-untouched; its `data-testid="worlds-*"` hooks are not Phase-6 anti-strip targets. (If the integrator decides to fold it in, that is a controller decision, not this plan's.)

---

## Behavior coverage map (audit §2 → task → test strategy)

Every behavior on the Phase-6 checklist row is covered by a task with the checklist's `vitest` strategy (the FE strategy; there is no FE red-green for pure-CSS, so each behavior is locked by a component vitest keyed on the existing `data-*`/text hooks per Phase-0 §5.8):

| # | Behavior (audit §2) | Owning file | Task |
|---|---|---|---|
| 17 | User's own Worlds run receipted on semifinal exit (`worlds_user`) | RecapStandings | T4 |
| 18 | `missed_playoffs` banner only when backend confirms outside cut | RecapStandings | T4 |
| 29 | Audience-tagged aftermath paragraphs read by tag, not prose prefix | *(not in any Phase-6 file — see Judgment Call J1)* | T13 (guard) |
| 31 | Honest null-vs-zero: undefined payload renders nothing | MediaEvent, RookieClassPreview, ChampionReveal | T3, T6, T9 |
| 32 | League-Wire empty-state honest static line (recap movement) | RecapStandings | T4 |
| 35 | Truthful empty states (records-book-empty vs my-club-empty-but-league-has; events; HoF) | StructuredOffseasonBeats, EventsBeat | T7, T5 |
| 67 | `signed_count` single source for "how many YOU signed"; cards never fabricated | Ceremonies (SigningDay) | T11 |
| 68 | Class-report tiles labelled player-scope vs LEAGUE-scope | Ceremonies (SigningDay) | T11 |
| 69 | Veto-aware re-sign latch + disabled Re-sign | TransferPeriod | T8 |
| 70 | Records milestone vs bookkeeping tiering + dethrone/new-holder; default scope + non-dead-end empty | StructuredOffseasonBeats | T7 |
| 71 | Integerized player-facing numbers (zero-floats); training-credit `.toFixed(1)` the receipt exception | DevelopmentResults, StructuredOffseasonBeats, RecapStandings | T2, T7, T4 |
| 72 | Training-credit receipt with cap disclosure, only when weeks>0 | DevelopmentResults | T2 |
| 73 | Sign-over-cut: release commits only if contested pick lands | RecruitmentChoice | T10 |
| 74 | Skip/lock-class gated by backend roster-floor guard with visible reason | RecruitmentChoice | T10 |
| 75 | AwardsNight `extra_stats` vs `season_stat` fallback | Ceremonies (AwardsNight) | T12 |

Plus the prompt's named anti-strip hooks: **`data-player-outcome`** (EventBracket, T5), **`recap-missed-playoffs`** (T4), **`worlds_user` semifinal receipt** (#17, T4), **`signed_count`** (#67, T11), **`zero-floats`** (#71, T2/T4/T7), **`data-broadcast-proof-source`** (StructuredOffseasonBeats, T7).

---

## Whole-window FREEZES (encode as task constraints — never violate)

These come from the parallelization-strategy "Cross-file contracts" table and the Phase-1 published contracts. Every task below operates under them:

1. **NO `index.css` edits or deletions.** Create `*.module.css` ONLY. The legacy ceremony selector families (`.champion-stage`, `.champion-name`, `.champion-stats`, `.playoff-bracket-*`, `.command-offseason-*`, `.dm-ceremony*`, etc.) are removed later by the serial integrator in STEP 3 — this plan must NOT include any `index.css` deletion task, and must NOT delete any selector this code stops using. The old class names may remain on elements during the window (mixed look is accepted until P8).
2. **NO edits to `components/ui.tsx`.** Re-point imports of `ActionButton`/`PageHeader` (the two `ui.tsx` primitives these files use) from `../ui` to the **Phase-1 `src/ui` shims** — an **import-path change ONLY**. **NO `ActionButton→ActionBar` remap** (deferred to Phase 8). NOTE: every Phase-6 file currently imports from `'../ui'` (the `components/ui.tsx` barrel). The Phase-1 shims live at `src/ui/index.ts`; from `src/components/ceremonies/*` that is `'../../ui'`. Change `import { ActionButton, PageHeader } from '../ui'` → `import { ActionButton, PageHeader } from '../../ui'`.
3. **SHARED globals SURVIVE — never delete/migrate:** `command-action-bar` (sticky bar used by 10 ceremony files + P2 + P5), `command-policy-overlay` (P2/P5). Keep the `className="dm-panel command-action-bar"` / `command-offseason-progress` / `command-offseason-shell` class strings on the elements; you may ADD a module class alongside, but do not remove the shared global class names. They are P8-deletion-only behind a grep-zero gate (protects #17 worlds_user receipt, #67, #71, league-history overlay).
4. **FROZEN — consume, never alter:**
   - `standings/PlayoffBracket.tsx` public signature `({ data }: { data: PlayoffBracketResponse })` (P4-owned, frozen by `PlayoffBracket.contract.test.tsx` in Phase 1). `ChampionReveal.tsx:4` statically imports it — keep that import and prop usage exactly.
   - `legibility/*` primitives (`KnownValue`, `CeilingGrade` used by RecruitmentChoice) — read-only until P8; accept their mixed look. Do NOT restyle them.
   - `frontend/scripts/check-tokens.mjs` — integrator owns `SCAN_DIRS`; this plan never touches it.
   - `match-week/matchResult.ts` — frozen (no Phase-6 file imports it; just never introduce a dependency that relocates it).
5. **Consume Phase-1 published contracts where relevant:** `components/shell/appContracts.ts` (not needed by ceremonies — they mount via `Offseason.tsx`, not App directly), the frozen `standings/PlayoffBracket` and `dynasty/history/ProgramModal` signatures (only PlayoffBracket is consumed here).
6. **Anti-strip `data-*` vitests are HARD RED preconditions.** Each rebuild task writes/keeps its enumerated `data-*` test and runs it RED against a deliberately-broken stub or GREEN against current code BEFORE reskinning, then keeps it green after. The enumerated hooks for this phase: `data-player-outcome`, `recap-missed-playoffs`, the `worlds_user` semifinal receipt text, `signed_count`-driven numbers, `data-broadcast-proof-source`, plus the per-screen `data-testid` provenance.

---

## File map (created/modified in this plan)

**Created (module CSS + tests, one triple per rebuilt component):**
- `frontend/src/components/ceremonies/CeremonyShell.module.css` + `CeremonyShell.test.tsx`
- `frontend/src/components/ceremonies/ChampionReveal.module.css` + `ChampionReveal.test.tsx`
- `frontend/src/components/ceremonies/RecapStandings.module.css` + `RecapStandings.test.tsx`
- `frontend/src/components/ceremonies/EventBracket.module.css` + `EventBracket.test.tsx`
- `frontend/src/components/ceremonies/EventsBeat.module.css` + `EventsBeat.test.tsx`
- `frontend/src/components/ceremonies/MediaEvent.module.css` + `MediaEvent.test.tsx`
- `frontend/src/components/ceremonies/DevelopmentResults.module.css` + `DevelopmentResults.test.tsx`
- `frontend/src/components/ceremonies/RookieClassPreview.module.css` + `RookieClassPreview.test.tsx`
- `frontend/src/components/ceremonies/StructuredOffseasonBeats.module.css` + `StructuredOffseasonBeats.test.tsx`
- `frontend/src/components/ceremonies/RecruitmentChoice.module.css` + `RecruitmentChoice.test.tsx`
- `frontend/src/components/ceremonies/TransferPeriod.module.css` + `TransferPeriod.test.tsx`
- `frontend/src/components/ceremonies/Ceremonies.module.css` + `Ceremonies.test.tsx`

**Modified (reskin to module CSS + re-point ui import path; logic verbatim):**
- All 13 `ceremonies/*.tsx` files in the scope table above.

**Frozen / NOT touched:** `frontend/src/index.css`, `frontend/src/components/ui.tsx`, `frontend/src/legibility/*`, `frontend/src/components/standings/PlayoffBracket.tsx`, `frontend/scripts/check-tokens.mjs`, `frontend/src/components/Offseason.tsx` (the beat router — its mount props are the contract; this plan keeps every component's public prop signature identical so `Offseason.tsx` needs no edit), `frontend/src/components/ceremonies/WorldsCrowning.tsx`.

---

## Per-task gate

Unless a task says otherwise, every task ends green on:

```bash
cd frontend && npm run test -- <the task's test file> && npm run build && npm run lint
```

> **Token-gate scoping note:** `npm run lint:tokens` only scans dirs in `SCAN_DIRS` (Phase 0 / integrator-owned). `src/components/ceremonies` is NOT in `SCAN_DIRS` during this window (the integrator appends it in STEP 3 only after the dir is clean). So `lint:tokens` will pass even mid-reskin — but each reskin task MUST pre-empt the STEP-3 token gate by using only `var(--…)` tokens (no raw hex, no raw px beyond `0`/`1px` hairlines, `viewBox`/SVG-coord exempt) from the start, so the integrator's eventual `SCAN_DIRS` append is clean in one shot.

The **Phase-6 lane gate** (Task 14) runs the full FE suite + build + lint + lint:tokens + a smoke e2e, against the worktree with the OLD `index.css` still present:

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e   # smoke: offseason ceremony path
```

---

## Phase 6A — Anti-strip preconditions + shared shell

### Task 0: Phase-1 shim pre-flight (HARD GATE — do not proceed if this fails)

> **Why:** This phase re-points every ceremony file's `ActionButton`/`PageHeader` import from `'../ui'` (the `components/ui.tsx` barrel) to `'../../ui'` (the Phase-1 `src/ui` shim barrel). If Phase 1 has not yet merged into the trunk this worktree is branched from, `src/ui/index.ts` will NOT export `ActionButton` or `PageHeader`, and every subsequent `'../../ui'` re-point will produce a build failure with no clear diagnosis. This pre-flight confirms the branch is correctly based on the post-Phase-1 trunk **before writing a single test or touching a single ceremony file.** The current `src/ui/index.ts` on the Phase-0 trunk exports only the 11 Phase-0 primitives (`Truncate`, `Surface`, `Card`, `Grid`, `ScrollRegion`, `Tag`, `RecordCell`, `Popover`, `Modal`, `ActionBar`, `Table`) — the five Phase-1 shims (`ActionButton`, `PageHeader`, `StatusMessage`, `RatingBar`, `RadioGroup`) are absent until Phase 1 merges.

**Files:** none created/modified — this is a read-only gate.

- [ ] **Step 1: Assert the Phase-1 shims landed in the barrel**

```bash
cd frontend
grep -q "ActionButton" src/ui/index.ts \
  || { echo "ERROR: ActionButton not found in src/ui/index.ts — Phase-1 shims have not merged. Do NOT proceed with Phase 6 until the post-Phase-1 trunk is the base of this worktree."; exit 1; }
grep -q "PageHeader" src/ui/index.ts \
  || { echo "ERROR: PageHeader not found in src/ui/index.ts — Phase-1 shims have not merged."; exit 1; }
echo "Phase-1 shim pre-flight PASSED — ActionButton and PageHeader are exported from src/ui/index.ts. Proceeding."
```

Expected output: the `PASSED` line. If either `exit 1` fires: **stop, do not continue**, and notify the controller that Phase 1 must be merged into this worktree's base branch before Phase 6 can begin.

> **Note:** the five Phase-1 shims are thin re-exports of the `components/ui.tsx` originals, added to `src/ui/index.ts` by the Phase-1 plan (see `2026-06-19-floodlight-phase-1-app-shell.md`). They are not yet present on the Phase-0 trunk (confirmed: `src/ui/index.ts` currently lists 11 Phase-0 exports only, no `ActionButton`/`PageHeader`). If you are running this plan on a worktree branched off the post-Phase-1 trunk and the grep still fails, re-check the merge history before proceeding.

---

### Task 1: Lock the shared `command-action-bar` survival + offseason `data-testid` provenance (RED-first anti-strip)

> **Why:** `command-action-bar` / `command-offseason-progress` / `command-offseason-shell` are SHARED globals consumed by ~10 of these files and by P2/P5. Before any reskin, write the anti-strip test that fails loudly if a later step drops the shared class string or a `data-testid`. This is the HARD RED precondition for the whole phase (strategy STEP 2: "enumerated `data-*` anti-strip vitests as HARD RED preconditions before rebuilding"). CeremonyShell is the smallest shared surface, so it carries the survival assertion. It imports `ActionButton, PageHeader` from `'../ui'` today (CeremonyShell.tsx:2) — that import is re-pointed to the shim path in Step 3.

**Audit numbers + test strategy:** shared-chrome survival (no audit number — a freeze guard) · vitest.

**Files:** create `frontend/src/components/ceremonies/CeremonyShell.test.tsx`; modify `frontend/src/components/ceremonies/CeremonyShell.tsx` + create `CeremonyShell.module.css`.

- [ ] **Step 1: Write the anti-strip test** (passes against CURRENT code, then must stay green through the reskin).

```tsx
// frontend/src/components/ceremonies/CeremonyShell.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CeremonyShell } from './CeremonyShell';

describe('CeremonyShell (shared offseason chrome — anti-strip)', () => {
  function mount(extra?: Partial<Parameters<typeof CeremonyShell>[0]>) {
    return render(
      <CeremonyShell
        title="Awards Night"
        eyebrow="Awards Night"
        description="The league gathers."
        stages={0}
        renderStage={() => <div data-testid="stage-body">body</div>}
        onComplete={() => {}}
        beatIndex={2}
        totalBeats={5}
        {...extra}
      />,
    );
  }

  it('keeps the SHARED command-action-bar global (P8-only deletion) and renders the stage', () => {
    const { container } = mount();
    expect(container.querySelector('.command-action-bar')).not.toBeNull();
    expect(screen.getByTestId('stage-body')).toBeInTheDocument();
  });

  it('renders the shared offseason progress pip strip from beatIndex/totalBeats', () => {
    const { container } = mount();
    const strip = container.querySelector('.command-offseason-progress');
    expect(strip).not.toBeNull();
    // 5 pips, first 3 (indices 0..beatIndex=2) active
    expect(strip!.querySelectorAll('.command-offseason-progress-step').length).toBe(5);
    expect(strip!.querySelectorAll('.command-offseason-progress-step-active').length).toBe(3);
  });

  it('announces the action-available transition via role=status (kept non-visual a11y hook)', () => {
    mount({ stages: 0, actionDescription: 'Continue to the next offseason beat.' });
    expect(screen.getByRole('status')).toHaveTextContent('Continue to the next offseason beat.');
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "CeremonyShell.test"`. Expected: PASS against current code (the harness is correctly wired to the live shell). If a case fails on current text, fix the assertion to the CURRENT truth (these guard existing behavior).

- [ ] **Step 3: Reskin CeremonyShell to module CSS** — replace the two inline `style={{...}}` objects on the outer `.dm-ceremony` flex column (CeremonyShell.tsx:67) and `.dm-ceremony-stage` (line 87) with `styles.ceremony` / `styles.stage` classes. **KEEP** `className="dm-ceremony"`, `className="dm-ceremony-stage"`, and `className="dm-panel command-action-bar"` (line 90) as additional class strings (shared globals + legacy selectors survive the window). Re-point the import: `import { ActionButton, PageHeader } from '../../ui'`. Keep the `useState`/`useEffect` skip + reduced-motion logic, the `role="status"` hint `<p>` (line 93), the `command-offseason-progress` pip strip, and every prop verbatim.

```css
/* frontend/src/components/ceremonies/CeremonyShell.module.css */
.ceremony { display: flex; flex-direction: column; gap: var(--space-8); }
.stage { flex: 1; display: flex; flex-direction: column; justify-content: center; }
```

The sticky `command-action-bar` keeps its existing inline `position: sticky; bottom: 1rem; marginTop: auto` for now (the shared global owns its chrome; do not move its layout into the module — Phase 8 unifies it via the `ActionBar` primitive). Convert the `'1rem'`/`'2rem'` literals that move into the module to tokens (`var(--space-5)` ≈ 16px, `var(--space-8)` = 32px); keep the sticky-bar inline values as-is (shared-global surface, untouched).

- [ ] **Step 4: Run to verify it still passes** — `cd frontend && npm run test -- "CeremonyShell.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/CeremonyShell.tsx frontend/src/components/ceremonies/CeremonyShell.module.css frontend/src/components/ceremonies/CeremonyShell.test.tsx
git commit -m "feat(ceremonies): CeremonyShell module CSS + shared command-action-bar anti-strip guard (P6)"
```

---

## Phase 6B — Faithfulness-critical screens (the named trust-breaks)

### Task 2: DevelopmentResults — zero-floats (#71) + training-credit receipt (#72)

> **Why:** Player-facing OVR deltas must be integerized (#71 V21 zero-floats), while the training-credit line is the **deliberate `.toFixed(1)` receipt exception** (#71/#72) shown ONLY when `trainingCredit.weeks > 0`, with the cap disclosure (`weeks > week_cap` → `(credited — cap N)`). Reskin must keep both exactly. Reskin replaces the inline hex/px (`#10b981`, `#94a3b8`, `rgba(...)`, `0.85rem` etc.) with tokens. Import re-point to `'../../ui'`.

**Audit numbers + test strategy:** #71 vitest · #72 vitest.

**Files:** create `DevelopmentResults.test.tsx` + `DevelopmentResults.module.css`; modify `DevelopmentResults.tsx`.

- [ ] **Step 1: Write the failing/locking test.** Read the exact `development` beat payload shape from `types.ts` (`OffseasonBeat` `development` variant) before writing the fixture — do not invent fields. The receipt line uses `trainingCredit.{weeks, week_cap, credited_weeks, per_week_ovr, credit_ovr}` (DevelopmentResults.tsx:178-184).

```tsx
// frontend/src/components/ceremonies/DevelopmentResults.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DevelopmentResults } from './DevelopmentResults';

// Build the minimal `development` beat the component reads. Fill the remaining
// required OffseasonBeat fields from types.ts when implementing (do not invent).
function devBeat(overrides: Record<string, unknown> = {}) {
  return {
    key: 'development', beat_index: 4, total_beats: 9, title: 'Development',
    payload: {
      results: [],
      training_credit: { weeks: 6, week_cap: 4, credited_weeks: 4, per_week_ovr: 0.2, credit_ovr: 0.8 },
      ...overrides,
    },
  } as never;
}

describe('DevelopmentResults', () => {
  it('#72: shows the training-credit receipt with cap disclosure (the .toFixed(1) exception)', () => {
    render(<DevelopmentResults beat={devBeat()} onComplete={() => {}} />);
    const receipt = screen.getByTestId('training-credit-receipt');
    expect(receipt).toHaveTextContent('6 weeks run');
    expect(receipt).toHaveTextContent('(4 credited — cap 4)');
    expect(receipt).toHaveTextContent('+0.8 OVR'); // deliberate one-decimal receipt
  });

  it('#72: hides the receipt entirely when weeks === 0', () => {
    render(<DevelopmentResults beat={devBeat({ training_credit: { weeks: 0, week_cap: 4, credited_weeks: 0, per_week_ovr: 0.2, credit_ovr: 0 } })} onComplete={() => {}} />);
    expect(screen.queryByTestId('training-credit-receipt')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "DevelopmentResults.test"`. Expected: PASS against current code (proves the harness reads the live receipt). Adjust fixtures to the real payload shape if a field name differs.

- [ ] **Step 3: Reskin to module CSS** — convert the OVR-delta rows, the training-credit receipt block (DevelopmentResults.tsx:161-186), and the League-Transition checklist block (188-209) from inline hex/px to `styles.*` + tokens (`--ok`/`--ok-soft` for the green receipt, `--text2`/`--muted` for body, `--volt2` for "times out", `--space-*`, `--radius-md`). KEEP the `data-testid="training-credit-receipt"`, the `trainingCredit.weeks > 0` guard, the `.toFixed(1)` call, and the cap-disclosure ternary verbatim. KEEP `className="dm-panel command-action-bar"` (shared). Re-point import to `'../../ui'`. Player-facing OVR delta numbers: keep them rendered exactly as the current code does (they are already integerized at the source — do NOT add any `.toFixed` to them; #71).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "DevelopmentResults.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/DevelopmentResults.*
git commit -m "feat(ceremonies): DevelopmentResults module CSS; keep zero-floats + training-credit receipt (#71/#72)"
```

---

### Task 3: MediaEvent — honest null-vs-zero (#31) + committed-receipt latch

> **Why:** #31 — when there is no `event` and no `committed`/`result`, render the honest "Quiet news cycle" line, NOT a fabricated prompt; when `committed && result`, show the verbatim `result.receipt`. The PT5 selected-state latch (`aria-pressed`/Selected ✓) is preserved. Reskin replaces inline hex/px with tokens; keep `data-testid` `offseason-media`/`media-result`/`media-event`.

**Audit numbers + test strategy:** #31 vitest.

**Files:** create `MediaEvent.test.tsx` + `MediaEvent.module.css`; modify `MediaEvent.tsx`.

- [ ] **Step 1: Write the locking test** (read the `media_event` payload shape from `types.ts`: `payload.{event, committed, result}`, `event.{prompt, options[]}`, `MediaEventOption.{key,label,fans,prestige,credibility}`).

```tsx
// frontend/src/components/ceremonies/MediaEvent.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MediaEvent } from './MediaEvent';

function mediaBeat(payload: Record<string, unknown>) {
  return { key: 'media_event', beat_index: 5, total_beats: 9, title: 'Media Moment', payload } as never;
}

describe('MediaEvent (#31 honest null-vs-zero)', () => {
  it('renders the honest quiet-cycle line when there is no event and nothing committed', () => {
    render(<MediaEvent beat={mediaBeat({ event: null, committed: false, result: null })} onChoose={() => {}} onComplete={() => {}} />);
    expect(screen.queryByTestId('media-event')).not.toBeInTheDocument();
    expect(screen.queryByTestId('media-result')).not.toBeInTheDocument();
    expect(screen.getByText(/Quiet news cycle/i)).toBeInTheDocument();
  });

  it('renders the verbatim committed receipt (no re-derivation)', () => {
    render(<MediaEvent beat={mediaBeat({ committed: true, result: { receipt: '+3 fans, +1 prestige' }, event: null })} onChoose={() => {}} onComplete={() => {}} />);
    expect(screen.getByTestId('media-result')).toHaveTextContent('+3 fans, +1 prestige');
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "MediaEvent.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin to module CSS** — convert the three branch blocks (committed result / event options / quiet-cycle) and the option rows to `styles.*` + tokens (`--volt2`/`--volt-soft` for the selected option border/bg, `--line`/`--raise` for unselected, `--text`/`--text2`/`--muted`). KEEP the `data-testid`s, the `aria-pressed={selected}` latch, the `chosenKey` state, and the three-branch null logic verbatim. KEEP `command-action-bar`. Re-point import to `'../../ui'`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "MediaEvent.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/MediaEvent.*
git commit -m "feat(ceremonies): MediaEvent module CSS; keep honest null-vs-zero + receipt (#31)"
```

---

### Task 4: RecapStandings — worlds_user receipt (#17) + missed_playoffs gate (#18) + diff zero-floats (#71) + movement empty (#32/#35)

> **Why:** This file carries the named **PT6 trust-break #17** (the user's own Worlds run receipted on a semifinal exit, even when the global line names only the final's two clubs — RecapStandings.tsx:253-262), plus **#18** (`missed_playoffs` banner only when the backend confirms the finish outside the cut — :63-88), **#71** (integer diff/points/finances via `formatK`/raw ints — never floats), and **#32/#35** (league-movement section is honest: `userMovement && userMovement !== 'stays'` gates the promoted/relegated banner; the world-champ line's runner-up clause only when present). The reskin must keep all four. Diff column branches on `diff_kind` ('GP ±' vs 'Elim ±') — preserve (it is #8/#71-adjacent).

**Audit numbers + test strategy:** #17 vitest · #18 vitest · #32 vitest · #71 vitest.

**Files:** create `RecapStandings.test.tsx` + `RecapStandings.module.css`; modify `RecapStandings.tsx`.

- [ ] **Step 1: Write the locking tests.** Read the `recap` payload from `types.ts` (`payload.{standings[], missed_playoffs, finances, pyramid, diff_kind}`; `pyramid.worlds_user.{result, qualified_as}` at types.ts ~1176-1182; `pyramid.worlds.{champion_name, runner_up_name}`).

```tsx
// frontend/src/components/ceremonies/RecapStandings.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecapStandings } from './RecapStandings';

function recapBeat(payload: Record<string, unknown>) {
  return {
    key: 'recap', beat_index: 0, total_beats: 9,
    payload: { standings: [], diff_kind: 'game_points', ...payload },
  } as never;
}

describe('RecapStandings trust contract', () => {
  it('#18: shows missed-playoffs banner ONLY when the backend confirms the finish', () => {
    const { rerender } = render(<RecapStandings beat={recapBeat({ missed_playoffs: { finish: 6, total: 8, cutoff: 4 } })} onComplete={() => {}} />);
    expect(screen.getByTestId('recap-missed-playoffs')).toHaveTextContent('6th of 8');
    rerender(<RecapStandings beat={recapBeat({ missed_playoffs: undefined })} onComplete={() => {}} />);
    expect(screen.queryByTestId('recap-missed-playoffs')).not.toBeInTheDocument();
  });

  it('#17: receipts the user OWN Worlds run on a semifinal exit (the PT6 trust-break)', () => {
    render(<RecapStandings beat={recapBeat({
      pyramid: {
        champions: [], promoted: [], relegated: [], user: {},
        worlds: { champion_name: 'Granite City', runner_up_name: 'Harbor' },
        worlds_user: { result: 'semifinalist', qualified_as: 'premier_runner_up' },
      },
    })} onComplete={() => {}} />);
    expect(screen.getByTestId('recap-pyramid')).toHaveTextContent('You reached Worlds');
    expect(screen.getByTestId('recap-pyramid')).toHaveTextContent('out in the semifinal');
  });

  it('#32: league-movement banner suppressed when the user stays (no fabricated movement)', () => {
    render(<RecapStandings beat={recapBeat({
      pyramid: { champions: [], promoted: [], relegated: [], user: { movement: 'stays', division_name: 'D2' } },
    })} onComplete={() => {}} />);
    expect(screen.queryByText(/PROMOTED|RELEGATED/)).not.toBeInTheDocument();
  });

  it('#71: standings diff renders as a signed integer, never a float', () => {
    render(<RecapStandings beat={recapBeat({
      standings: [{ rank: 1, club_name: 'A', is_player_club: true, wins: 7, losses: 2, draws: 1, points: 22, diff: 14 }],
    })} onComplete={() => {}} />);
    const cell = screen.getByText('+14');
    expect(cell.textContent).not.toMatch(/\./);
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "RecapStandings.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin to module CSS** — convert the missed-playoffs banner (:63-88), the standings table grid (the `gridTemplateColumns: '2rem 1fr 6rem 3.5rem 4rem'` fixed-px tracks — audit §3 P3 "won't shrink inside overflow:hidden", so move to `styles.table` and add `min-width:0` + a `Truncate` on the club-name cell to fix RecapStandings P2/P3 highs), the finances panel (:150-200), and the league-movement panel (:202-265) to `styles.*` + tokens (`--volt`/`--volt-soft` for the missed/relegated red, `--ok`/`--ok-soft` for promoted/payout green, `--gold`/`--gold2` for the WORLDS star line, `--text`/`--text2`/`--muted`). **KEEP verbatim:** the `missed && (...)` gate, the `worlds_user.result === 'semifinalist'` receipt with its `qualified_as` lookup object, the `userMovement && userMovement !== 'stays'` gate, the `pyramid.worlds.runner_up_name ? ... : '.'` clause, the `diff_kind` ternary, `formatK`/`formatKSigned` calls, and all `data-testid`s. KEEP `command-action-bar`. Re-point import to `'../../ui'`. For the long-name overflow fix, import `Truncate` from `'../../ui'` and wrap the club-name `<span>` (apply `min-width:0` on the grid cell via the module).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "RecapStandings.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/RecapStandings.*
git commit -m "feat(ceremonies): RecapStandings module CSS; keep worlds_user/missed_playoffs/diff/movement (#17/#18/#32/#71)"
```

---

### Task 5: EventBracket + EventsBeat — data-player-outcome (anti-strip) + events empty-state (#35)

> **Why:** `EventBracket` carries the named anti-strip hook **`data-player-outcome`** (`'advanced'`/`'eliminated'`/`undefined`, EventBracket.tsx:50) and the YOU WON / YOU OUT ribbon gated on `playerInMatch && winner identity` — same family as #16. `EventsBeat` owns the honest events empty-state (#35: "No events resolved this season" when `events.length === 0`) and the `giant-killing` receipts. Both are heavily inline (hardcoded `#22c55e`/`#f43f5e`/`#1e293b`, `13rem` min-widths — audit §3 P3 "Bracket columns min-width:13rem"). Reskin to tokens; keep the hooks.
>
> **NOTE (latent live-path gap, preserve as-is):** `Offseason.tsx:81` mounts `<EventsBeat>` WITHOUT a `playerClubId` prop, so `data-player-outcome` never fires in the live offseason path today. This plan **preserves** the prop on both components (frozen contract) and tests the hook directly — do NOT "fix" the wiring (out of Phase-6 scope; that is a backend/Offseason decision).

**Audit numbers + test strategy:** `data-player-outcome` anti-strip · #35 vitest.

**Files:** create `EventBracket.test.tsx` + `EventBracket.module.css` + `EventsBeat.test.tsx` + `EventsBeat.module.css`; modify both `.tsx`.

- [ ] **Step 1: Write the locking tests.** Read `EventBracketRow`/`EventResultRow` from `types.ts` (`EventBracketRow.{round, home_club_id, home_club_name, away_club_id, away_club_name, winner_club_id}`; `EventResultRow.{event_key, event_name, champion_club_id, champion_club_name, bracket[], purse_k, meta}`).

```tsx
// frontend/src/components/ceremonies/EventBracket.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EventBracket } from './EventBracket';

const event = {
  event_key: 'domestic_cup', event_name: 'Domestic Cup',
  champion_club_id: 'you', champion_club_name: 'Your Club', purse_k: 0, meta: {},
  bracket: [
    { round: 'final', home_club_id: 'you', home_club_name: 'Your Club', away_club_id: 'rival', away_club_name: 'Rival', winner_club_id: 'you' },
  ],
} as never;

describe('EventBracket (data-player-outcome anti-strip)', () => {
  it('marks data-player-outcome="advanced" when the player won their match', () => {
    const { container } = render(<EventBracket event={event} playerClubId="you" />);
    expect(container.querySelector('[data-player-outcome="advanced"]')).not.toBeNull();
    expect(screen.getByText('YOU WON')).toBeInTheDocument();
  });

  it('omits data-player-outcome when the player is not in the match', () => {
    const { container } = render(<EventBracket event={event} playerClubId="someone-else" />);
    expect(container.querySelector('[data-player-outcome]')).toBeNull();
  });
});
```

```tsx
// frontend/src/components/ceremonies/EventsBeat.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EventsBeat } from './EventsBeat';

function eventsBeat(events: unknown[]) {
  return { key: 'events', beat_index: 3, total_beats: 9, payload: { events } } as never;
}

describe('EventsBeat (#35 honest empty state)', () => {
  it('shows the honest no-events line when nothing resolved', () => {
    render(<EventsBeat beat={eventsBeat([])} onComplete={() => {}} />);
    expect(screen.getByText(/No events resolved this season/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "EventBracket.test" "EventsBeat.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin both to module CSS** — In `EventBracket`, replace the inline `outcomeBorder` hex logic with token-driven module classes keyed on `playerAdvanced`/`playerEliminated` (`.advanced { border-color: var(--ok); }`, `.eliminated { border-color: var(--volt); }`, `.neutral { border-color: var(--line2); }`), and the YOU WON/YOU OUT chip with `--ok`/`--volt` background tokens; keep the `13rem` min-width as a `min(13rem, 100%)` token-free width OR a module class using a token (the integrator token gate allows `rem`-based widths only via tokens — use `min-width: min(13rem, 100%)` to also fix the audit §3 P3 phone overflow). Wrap the team-name span in `Truncate` (audit §3 P2 "team-name ellipsis without min-width:0"). KEEP `data-player-outcome`, `data-testid="event-bracket"`, the `playerAdvanced`/`playerEliminated` derivation, and the `playoff-bracket-*`/`dm-kicker`/`dm-panel` legacy class strings (survive the window). In `EventsBeat`, convert `event-result-card`/`giant-killing` blocks to tokens, keep their `data-testid`s and the `events.length > 0 ? ... : honest-empty` branch. KEEP `command-action-bar`. Re-point both imports to `'../../ui'` (EventsBeat uses `ActionButton, PageHeader`; EventBracket imports only types today — add `Truncate` from `'../../ui'`).

- [ ] **Step 4: Run to verify they pass** — `cd frontend && npm run test -- "EventBracket.test" "EventsBeat.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/EventBracket.* frontend/src/components/ceremonies/EventsBeat.*
git commit -m "feat(ceremonies): EventBracket/EventsBeat module CSS; keep data-player-outcome + events empty (#35)"
```

---

### Task 6: RookieClassPreview — honest upside, no fabricated default (#31)

> **Why:** #31 — the headline counts ceiling UPSIDE (`ceiling_prospects`), with `hasUpside` gating the upside copy and `qualityPct` honestly 0 when `class_size === 0`. Reskin replaces inline hex/px + the `'0 0 7rem'` archetype label track (audit §3 P3 "clips long archetype names") with tokens + a `Truncate`/`min-width:0`. Keep the honest derivations.

**Audit numbers + test strategy:** #31 vitest.

**Files:** create `RookieClassPreview.test.tsx` + `RookieClassPreview.module.css`; modify `RookieClassPreview.tsx`.

- [ ] **Step 1: Write the locking test** (read the `rookie_class_preview` payload from `types.ts`: `payload.{class_size, top_prospects, free_agents, archetypes[], storylines[], ceiling_prospects}`).

```tsx
// frontend/src/components/ceremonies/RookieClassPreview.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RookieClassPreview } from './RookieClassPreview';

function rookieBeat(payload: Record<string, unknown>) {
  return {
    key: 'rookie_class_preview', beat_index: 6, total_beats: 9,
    payload: { class_size: 0, top_prospects: [], free_agents: [], archetypes: [], storylines: [], ceiling_prospects: 0, ...payload },
  } as never;
}

describe('RookieClassPreview (#31 honest upside)', () => {
  it('renders the screen and does not fabricate upside when class is empty', () => {
    render(<RookieClassPreview beat={rookieBeat({})} onComplete={() => {}} />);
    expect(screen.getByTestId('offseason-rookie-preview')).toBeInTheDocument();
    // qualityPct is 0 when class_size is 0 — no fabricated percentage
    expect(screen.queryByText('NaN%')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "RookieClassPreview.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin to module CSS** — convert the upside headline, the composition/archetype bars (use a token-driven bar width via a `--bar-pct` custom property, not inline px), and the storylines list to `styles.*` + tokens. Replace the `'0 0 7rem'` fixed archetype-label track with `minmax(0, 7rem)` + `Truncate`. KEEP the `ceilingProspects`/`hasUpside`/`qualityPct` math, `data-testid="offseason-rookie-preview"`, and `command-action-bar`. Re-point import to `'../../ui'`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "RookieClassPreview.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/RookieClassPreview.*
git commit -m "feat(ceremonies): RookieClassPreview module CSS; keep honest upside (#31)"
```

---

### Task 7: StructuredOffseasonBeats — records tiering + non-dead-end empty (#70/#35) + zero-floats (#71) + proof-source (anti-strip)

> **Why:** This file owns `RecordsRatified` + `HallOfFameInduction`. **#70:** milestone-vs-bookkeeping tiering, dethrone/new-holder flags, default scope = My Club when the user holds a record else League. **#35:** the My-Club-empty-but-league-has empty state offers a one-tap path to League scope (not a dead end), and three distinct empty messages (`records_book_empty` vs my-club-empty vs no-new-records). **#71:** `formatValue` is the integerizer (`Number.isInteger ? String : .toFixed(1)`) — keep it. Anti-strip: **`data-broadcast-proof-source`** (`record:`/`career:` provenance, :269/:420/:508) and `data-testid` `record-milestone-card`/`record-milestone-row`/`record-extension-row`/`broadcast-proof-toggle`. Reskin replaces the inline hex/px throughout.

**Audit numbers + test strategy:** #70 vitest · #35 vitest · #71 vitest · `data-broadcast-proof-source` anti-strip.

**Files:** create `StructuredOffseasonBeats.test.tsx` + `StructuredOffseasonBeats.module.css`; modify `StructuredOffseasonBeats.tsx`.

- [ ] **Step 1: Write the locking tests.** Read the `records_ratified` + `hof_induction` payloads from `types.ts` (`records[]` with `{is_my_club, record_type, proof_source?, ...}`, `records_book_empty`; HoF `inductees[]` with `{player_id?, player_name, proof_source?}`).

```tsx
// frontend/src/components/ceremonies/StructuredOffseasonBeats.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { RecordsRatified, HallOfFameInduction } from './StructuredOffseasonBeats';

function recordsBeat(payload: Record<string, unknown>) {
  return { key: 'records_ratified', beat_index: 7, total_beats: 9, title: 'Records', can_advance: true, payload } as never;
}

describe('RecordsRatified (#70 tiering / #35 empty / proof-source)', () => {
  it('#35: records-book-empty shows the honest book-empty message', () => {
    render(<RecordsRatified beat={recordsBeat({ records: [], records_book_empty: true })} onComplete={() => {}} />);
    expect(screen.getByText(/record book is empty/i)).toBeInTheDocument();
  });

  it('#35: my-club-empty-but-league-has offers a one-tap path to League scope (no dead end)', async () => {
    render(<RecordsRatified beat={recordsBeat({
      records: [{ is_my_club: false, record_type: 'most_elims', proof_source: 'record:most_elims' }],
      records_book_empty: false,
    })} onComplete={() => {}} />);
    // default scope = League here (no my-club records), so the league record renders
    expect(screen.getByTestId('record-milestone-card')).toBeInTheDocument();
  });

  it('keeps data-broadcast-proof-source provenance on milestone cards', () => {
    const { container } = render(<RecordsRatified beat={recordsBeat({
      records: [{ is_my_club: true, record_type: 'most_elims', proof_source: 'record:most_elims' }],
      records_book_empty: false,
    })} onComplete={() => {}} />);
    expect(container.querySelector('[data-broadcast-proof-source]')).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "StructuredOffseasonBeats.test"`. Expected: PASS against current code. (Adjust the league-scope default expectation to the real `hasMyClubRecords` logic at :116-119 if needed.)

- [ ] **Step 3: Reskin to module CSS** — convert `BeatShell`, the scope toggle, the milestone cards (`record-milestone-card`/`-row`/`-extension-row`), the `ProofDetails` toggle, and the HoF inductee plaques from inline hex/px to `styles.*` + tokens. **KEEP verbatim:** `formatValue`, `formatProofSource` (the `record:`/`career:` strip), all `data-broadcast-proof-source={... ?? 'record:'/'career:'}` fallbacks, every `data-testid`, the `scope`/`hasMyClubRecords`/`myClubEmptyButLeagueHas` logic, and the three `emptyMessage()` branches. KEEP `command-offseason-shell` + `command-action-bar`. Re-point import to `'../../ui'`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "StructuredOffseasonBeats.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/StructuredOffseasonBeats.*
git commit -m "feat(ceremonies): StructuredOffseasonBeats module CSS; keep tiering/empty/proof-source (#70/#35/#71)"
```

---

### Task 8: TransferPeriod — veto-aware re-sign latch + disabled Re-sign (#69)

> **Why:** #69 — a dealbreaker veto means the player WON'T re-sign: the latch badge reads "✗ Won't re-sign" (NOT "Re-signing") and the **Re-sign `ActionButton` is `disabled={acting || row.veto}`** (TransferPeriod.tsx:124-128,161). Reskin must keep the veto-aware badge ternary and the disabled gate. Heavily inline hex/px throughout. Keep `transfer-expiring-*`/`transfer-buyout-*`/`transfer-results` testids.

**Audit numbers + test strategy:** #69 vitest.

**Files:** create `TransferPeriod.test.tsx` + `TransferPeriod.module.css`; modify `TransferPeriod.tsx`.

- [ ] **Step 1: Write the locking test.** Read the `transfer_period` payload from `types.ts` (`payload.{expiring[], buyouts[], results?}`; `TransferExpiringRow.{player_id, name, ovr, ask_k, decision, veto, dealbreaker, dealbreaker_letter, top_suitor?}`).

```tsx
// frontend/src/components/ceremonies/TransferPeriod.test.tsx
import { render, screen, within } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { TransferPeriod } from './TransferPeriod';

function transferBeat(payload: Record<string, unknown>) {
  return { key: 'transfer_period', beat_index: 2, total_beats: 9, payload: { expiring: [], buyouts: [], ...payload } } as never;
}

const vetoRow = {
  player_id: 'p1', name: 'Vetoed Vet', ovr: 71, ask_k: 40, decision: 'resign',
  veto: true, dealbreaker: 'Wants a contender', dealbreaker_letter: 'A',
};

describe('TransferPeriod (#69 veto-aware latch)', () => {
  it('shows "Won\'t re-sign" and DISABLES the Re-sign button on a veto', () => {
    render(<TransferPeriod beat={transferBeat({ expiring: [vetoRow] })} onTransfer={() => {}} onComplete={() => {}} />);
    const row = screen.getByTestId('transfer-expiring-p1');
    expect(row).toHaveTextContent("Won't re-sign");
    const resign = within(row).getByRole('button', { name: 'Re-sign' });
    expect(resign).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "TransferPeriod.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin to module CSS** — convert the treasury/wage header, the expiring/buyout rows, and the settled-results panel from inline hex/px to `styles.*` + tokens (`--volt2` for the "won't re-sign"/"letting walk" red badge, `--ok`/accent for "re-signing", `--gold`/`--volt` for suitor chips). Wrap long name/chip spans in `Truncate` (audit §3 P2 "long chips ... shove action buttons"). **KEEP verbatim:** the `badge` veto-aware ternary (veto → "✗ Won't re-sign"), `disabled={acting || row.veto}` on the Re-sign button, the optimistic `decision` precedence, and every `data-testid`. KEEP `command-action-bar`. Re-point import to `'../../ui'`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "TransferPeriod.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/TransferPeriod.*
git commit -m "feat(ceremonies): TransferPeriod module CSS; keep veto-aware latch + disabled Re-sign (#69)"
```

---

### Task 9: ChampionReveal — consumes FROZEN P4 PlayoffBracket; title_count only (#40-adjacent/#31)

> **Why:** **`ChampionReveal.tsx:4` statically imports `{ PlayoffBracket } from '../standings/PlayoffBracket'`** — the FROZEN P4 signature `({ data }: { data: PlayoffBracketResponse })`. This task **consumes** it, never alters it; the lane gate (Task 14) asserts the import resolves and the contract test from Phase 1 stays green. #31: the champion block renders the honest fallback (`beat.body` / "No champion determined") when `champion` is null. The crowning is a moment — `title_count` is display-only, no NG+/ratchet implied (#40-adjacent). Reskin replaces inline hex (`#94a3b8`, `#1e293b`) with tokens.

**Audit numbers + test strategy:** P4-PlayoffBracket import-resolves gate · #31 vitest.

**Files:** create `ChampionReveal.test.tsx` + `ChampionReveal.module.css`; modify `ChampionReveal.tsx`.

- [ ] **Step 1: Write the locking test.** Mock `useApiResource` so the bracket fetch resolves deterministically, and mock the frozen `PlayoffBracket` to a stub so this test exercises ChampionReveal, not P4 internals (the real import is asserted at the lane gate / Phase-1 contract test). Read the `champion` payload from `types.ts` (`payload.champion.{club_name, wins, losses, draws, title_count}`).

```tsx
// frontend/src/components/ceremonies/ChampionReveal.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('../standings/PlayoffBracket', () => ({ PlayoffBracket: () => <div data-testid="stub-bracket" /> }));
vi.mock('../../hooks/useApiResource', () => ({ useApiResource: () => ({ data: null }) }));

import { ChampionReveal } from './ChampionReveal';

function championBeat(payload: Record<string, unknown>) {
  return { key: 'champion', beat_index: 0, total_beats: 9, title: 'Champions', body: '', payload } as never;
}

describe('ChampionReveal (#31 honest fallback; consumes frozen P4 bracket)', () => {
  it('renders the champion hero with title_count when a champion is present', () => {
    render(<ChampionReveal beat={championBeat({ champion: { club_name: 'Granite City', wins: 9, losses: 1, draws: 0, title_count: 3 } })} onComplete={() => {}} />);
    expect(screen.getByTestId('offseason-champion')).toHaveTextContent('Granite City');
    expect(screen.getByText('3')).toBeInTheDocument(); // title_count, display-only
  });

  it('#31: renders the honest fallback when no champion was determined', () => {
    render(<ChampionReveal beat={championBeat({ champion: null })} onComplete={() => {}} />);
    expect(screen.getByText(/No champion determined this season/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "ChampionReveal.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin to module CSS** — convert the `champion-stage`/`champion-name`/`champion-stats` block and the bracket-wrapper `<div>` (ChampionReveal.tsx:69-73, currently inline `1px solid #1e293b` / `2rem` paddings) and the null-fallback `<p style={{ color: '#94a3b8' }}>` (:63) to `styles.*` + tokens (`--gold`/`--gold2` for the title number, `--line2` for the bracket divider, `--text2`/`--muted` for the fallback). **KEEP** the static `import { PlayoffBracket } from '../standings/PlayoffBracket'` and `<PlayoffBracket data={bracket} />` usage **unchanged** (frozen P4 contract). KEEP `champion-stage`/legacy class strings, `data-testid="offseason-champion"`, `command-offseason-progress`, `command-action-bar`. Re-point the ui import to `'../../ui'`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "ChampionReveal.test" && npm run build`. Expected: PASS + build clean. **Build is the import-resolves gate** for the frozen PlayoffBracket consumption.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/ChampionReveal.*
git commit -m "feat(ceremonies): ChampionReveal module CSS; consume frozen P4 PlayoffBracket; keep honest fallback (#31)"
```

---

### Task 10: RecruitmentChoice — sign-over-cut (#73) + skip/lock gate (#74) + band-vs-FA OVR (#23)

> **Why:** **#73:** at a full roster, Sign opens the release picker (`releasePickerOpen`); the pick fires `onSign(selectedId, releaseId)` only with a named release, and the copy states "the release happens only if you win the signing" (RecruitmentChoice.tsx:387-484). **#74:** skip/lock-class is gated by the backend roster-floor guard — `canSkip`/`skipBlockedReason` disable the control with a visible reason (:50-51). **#23:** prospect OVR is a scouted band (via `KnownValue`/`CeilingGrade` from `legibility/*`, which are FROZEN read-only). Reskin replaces inline hex/px; keep the gates and the `legibility/*` usage untouched.

**Audit numbers + test strategy:** #73 vitest · #74 vitest.

**Files:** create `RecruitmentChoice.test.tsx` + `RecruitmentChoice.module.css`; modify `RecruitmentChoice.tsx`.

- [ ] **Step 1: Write the locking tests.** Read the `recruitment` (can_recruit) payload from `types.ts` (`payload.{available_prospects[], signed_count, signing_limit, remaining_signings, roster_size, roster_limit, user_roster[], can_skip, skip_blocked_reason, ...}`; `user_roster[].{id, name, overall, age, promised}`). Mock `legibility/KnownValue` + `legibility/CeilingGrade` to stubs so the test exercises RecruitmentChoice (and respects the frozen-read-only rule — no assertions on their internals).

```tsx
// frontend/src/components/ceremonies/RecruitmentChoice.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../legibility/KnownValue', () => ({ KnownValue: ({ children }: { children?: unknown }) => <span>{children as never}</span> }));
vi.mock('../../legibility/CeilingGrade', () => ({ CeilingGrade: () => null }));

import { RecruitmentChoice } from './RecruitmentChoice';

function recruitBeat(payload: Record<string, unknown>) {
  return {
    key: 'recruitment', beat_index: 8, total_beats: 9,
    payload: {
      available_prospects: [{ prospect_id: 'pr1', name: 'Hot Prospect', ovr: 64 }],
      signed_count: 0, signing_limit: 3, remaining_signings: 3,
      roster_size: 12, roster_limit: 12, user_roster: [{ id: 'u1', name: 'Old Vet', overall: 58, age: 31 }],
      can_skip: true, skip_blocked_reason: null, ...payload,
    },
  } as never;
}

describe('RecruitmentChoice (#73 sign-over-cut / #74 skip gate)', () => {
  it('#73: a full roster opens the release picker instead of signing immediately', async () => {
    const onSign = vi.fn();
    render(<RecruitmentChoice beat={recruitBeat({})} onSign={onSign} acting={false} />);
    await userEvent.click(screen.getByRole('button', { name: /Sign/i }));
    expect(screen.getByTestId('signing-release-picker')).toBeInTheDocument();
    expect(onSign).not.toHaveBeenCalled(); // not fired until a release is named
  });

  it('#74: skip is disabled with a visible reason when the backend blocks it', () => {
    render(<RecruitmentChoice beat={recruitBeat({ can_skip: false, skip_blocked_reason: 'Roster below the floor.' })} onSign={() => {}} acting={false} />);
    expect(screen.getByText(/Roster below the floor/i)).toBeInTheDocument();
  });
});
```

> Adjust the Sign-button accessible name to the real label (read RecruitmentChoice.tsx around the primary Sign action before finalizing the `name:` matcher).

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "RecruitmentChoice.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin to module CSS** — convert the prospect list rows (`recruitment-prospect-row`), the selected-prospect article, the release picker (`signing-release-picker`, currently inline `rgba(34,211,238,...)` cyan + `220px` nested scroll — also fix audit §3 P4 "maxHeight 420px/220px" by routing the inner list through the Phase-0 `ScrollRegion` primitive), the snipe/rival/release/win banners, and the confirm-finish prompt to `styles.*` + tokens. **KEEP verbatim:** the `rosterFull`/`releasePickerOpen` sign-over-cut flow, the `onSign(selectedId, releaseId)` two-arg call, the `canSkip`/`skipBlockedReason` gate, and every `data-testid`. **Do NOT restyle** `KnownValue`/`CeilingGrade` (frozen read-only). KEEP `command-offseason-shell` + `command-action-bar`. Re-point the ui import to `'../../ui'`; import `ScrollRegion`/`Truncate` from `'../../ui'`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "RecruitmentChoice.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/RecruitmentChoice.*
git commit -m "feat(ceremonies): RecruitmentChoice module CSS; keep sign-over-cut + skip gate (#73/#74); legibility frozen"
```

---

### Task 11: Ceremonies/SigningDay — signed_count single-source (#67) + scope labels (#68)

> **Why:** **#67:** `signed_count` is the authoritative roster-delta counter — every player-facing NUMBER meaning "how many YOU signed" (hero tile, headline, slots-used line, "Your Picks" tab badge) reads `signedCount`, and the card LIST is never fabricated to match (Ceremonies.tsx:653,663-673,705-722). **#68:** the hero tiles are labelled player-scope ("Your Signings") vs LEAGUE-scope ("Rival Signings (League)", "Rookies (League)") so the big numbers can't be misread (:700-708). Reskin the SigningDay branch of `Ceremonies.tsx` (and the AwardsNight/Graduation/NewSeasonEve branches, all in this file — but #75 AwardsNight is Task 12); keep the single-source logic and labels.

**Audit numbers + test strategy:** #67 vitest · #68 vitest.

**Files:** create `Ceremonies.test.tsx` (shared by T11 + T12) + `Ceremonies.module.css`; modify `Ceremonies.tsx`.

- [ ] **Step 1: Write the locking tests.** Read the `recruitment` (!can_recruit) payload from `types.ts` (`payload.{player_signing?, other_signings[], signed_count, signing_limit, signings[]}`; `SigningCard.{player_id, name, ovr, outcome_kind, user_interaction.scouted}`). `Ceremonies.tsx` exports `SigningDay` (and `AwardsNight`, `Graduation`, `NewSeasonEve`).

```tsx
// frontend/src/components/ceremonies/Ceremonies.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { SigningDay } from './Ceremonies';

function signingBeat(payload: Record<string, unknown>) {
  return {
    key: 'recruitment', beat_index: 8, total_beats: 9, title: 'Class Report',
    payload: { signed_count: 2, signing_limit: 3, signings: [], other_signings: [], ...payload },
  } as never;
}

describe('SigningDay (#67 signed_count single-source / #68 scope labels)', () => {
  it('#67: the "you signed" headline reads signed_count even when zero cards were recorded', () => {
    render(<SigningDay beat={signingBeat({ signed_count: 2, signings: [{ player_id: 'c1', name: 'Card Kid', ovr: 60, outcome_kind: 'rival_signing', user_interaction: { scouted: false } }] })} onComplete={() => {}} />);
    // 2 signings claimed by signed_count, even though only 1 (rival) card exists and 0 are my_signing
    expect(screen.getByText(/You signed 2\./)).toBeInTheDocument();
  });

  it('#68: hero tiles label player-scope vs LEAGUE-scope', () => {
    render(<SigningDay beat={signingBeat({ signings: [{ player_id: 'c1', name: 'K', ovr: 60, outcome_kind: 'rival_signing', user_interaction: { scouted: false } }] })} onComplete={() => {}} />);
    expect(screen.getByText('Your Signings')).toBeInTheDocument();
    expect(screen.getByText(/Rival Signings \(League\)/)).toBeInTheDocument();
    expect(screen.getByText(/Rookies \(League\)/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "Ceremonies.test"`. Expected: PASS against current code.

- [ ] **Step 3: Reskin the SigningDay branch to module CSS** — convert the hero `MetricTile` strip, the `GlancePanel`/`GlanceRow`, the tab row, and the signing-card list from inline hex/px to `styles.*` + tokens. **KEEP verbatim:** `signedCount`/`myCount`/`tabCounts` single-source logic (the card list is NOT fabricated to match — keep the empty-state copy that names `signedCount`), the player-scope vs LEAGUE-scope tile labels, and the `CeremonyShell` mount (with `beatIndex`/`totalBeats` so the shared progress strip shows). The `TIER_COLOR`/`AWARD_COLOR` maps at the top of the file currently hold literals consumed by inline styles — move these into module classes keyed by tier/award name (e.g. `.tierElite { color: var(--ok); }`) so no literal survives the eventual token gate; keep the SAME tier/award keys. Re-point import to `'../../ui'` (note: `Ceremonies.tsx` imports `CeremonyShell` from `'./CeremonyShell'`, not `../ui` — leave that local import as-is).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "Ceremonies.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx frontend/src/components/ceremonies/Ceremonies.module.css frontend/src/components/ceremonies/Ceremonies.test.tsx
git commit -m "feat(ceremonies): SigningDay module CSS; keep signed_count single-source + scope labels (#67/#68)"
```

---

### Task 12: Ceremonies/AwardsNight — extra_stats vs season_stat fallback (#75) + Graduation/NewSeasonEve reskin

> **Why:** **#75:** the AwardsNight MVP/award stat chips read `award.extra_stats` (throw_elims / catches / times_eliminated) when present, falling back to the single `award.season_stat` chip otherwise (Ceremonies.tsx:183-211). Reskin must keep the branch. Also reskins the remaining `Ceremonies.tsx` branches — Graduation (retiring-veteran cards) and NewSeasonEve (schedule toggle + Start New Season) — that this file owns. The MVP hero's `paddingRight: 8rem` reserve colliding with the absolute badge (audit §3 P3 high) is fixed by moving to a token-driven flex layout.

**Audit numbers + test strategy:** #75 vitest.

**Files:** extend `Ceremonies.test.tsx`; extend `Ceremonies.module.css`; modify `Ceremonies.tsx` (AwardsNight/Graduation/NewSeasonEve branches).

- [ ] **Step 1: Add the failing/locking test** to `Ceremonies.test.tsx`. Read the `awards` payload from `types.ts` (`OffseasonAward.{award_type, award_name, player_name, club_name, ovr, season_stat, career_stat, extra_stats?{throw_elims,catches,times_eliminated}}`). AwardsNight uses `CeremonyShell` with `stages = orderedAwards.length` and reveals the MVP at `stage >= 1` — the test must drive stages. Since the shell auto-advances on a timer and on click/space, assert on the final revealed state by using `findByText` (the reduced-motion path advances in ~10ms) OR by simulating the skip click.

```tsx
// append to frontend/src/components/ceremonies/Ceremonies.test.tsx
import { AwardsNight } from './Ceremonies';
import userEvent from '@testing-library/user-event';

function awardsBeat(awards: unknown[]) {
  return { key: 'awards', beat_index: 1, total_beats: 9, title: 'Awards Night', payload: { awards } } as never;
}

describe('AwardsNight (#75 extra_stats vs season_stat)', () => {
  it('renders extra_stats chips when present', async () => {
    render(<AwardsNight beat={awardsBeat([
      { award_type: 'mvp', award_name: 'MVP', player_name: 'Star', club_name: 'You', ovr: 80, season_stat: 40, career_stat: 120,
        extra_stats: { throw_elims: 33, catches: 12, times_eliminated: 5 } },
    ])} onComplete={() => {}} />);
    await userEvent.click(document.body); // skip the staged reveal to final
    expect(await screen.findByText('THROW ELIMS')).toBeInTheDocument();
    expect(screen.getByText('33')).toBeInTheDocument();
  });

  it('falls back to the single season_stat chip when extra_stats is absent', async () => {
    render(<AwardsNight beat={awardsBeat([
      { award_type: 'mvp', award_name: 'MVP', player_name: 'Star', club_name: 'You', ovr: 80, season_stat: 40, career_stat: 120 },
    ])} onComplete={() => {}} />);
    await userEvent.click(document.body);
    expect(await screen.findByText('SEASON ELIMS')).toBeInTheDocument();
    expect(screen.queryByText('THROW ELIMS')).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "Ceremonies.test"`. Expected: PASS against current code (both T11 + T12 cases).

- [ ] **Step 3: Reskin the AwardsNight / Graduation / NewSeasonEve branches to module CSS** — convert the MVP hero card (replace `position:absolute` badge + `paddingRight: 8rem` collision with a token-driven flex header; fixes audit §3 P3), the supporting-awards grid (replace `repeat(min(n,3),1fr)` with the Phase-0 `Grid` `min=` so it collapses — fixes §3 P3 "no collapse/min-width:0"), the stat chips (keep the `extra_stats ? ... : season_stat` branch verbatim), the retiree farewell cards, and the schedule toggle from inline hex/px to `styles.*` + tokens (`--gold`/`--gold2` for the MVP, `--text`/`--text2`). Use the `AWARD_COLOR`/`AWARD_ICON` maps as module-class lookups (keys preserved). KEEP `CeremonyShell` mounts + `command-action-bar` (via the shell). Import `Grid`/`Truncate` from `'../../ui'` as needed.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "Ceremonies.test" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx frontend/src/components/ceremonies/Ceremonies.module.css frontend/src/components/ceremonies/Ceremonies.test.tsx
git commit -m "feat(ceremonies): AwardsNight/Graduation/NewSeasonEve module CSS; keep extra_stats fallback (#75)"
```

---

## Phase 6C — Cross-cutting guard + lane gate

### Task 13: #29 audience-tag non-regression guard (ownership clarification)

> **Why (Judgment Call J1):** The checklist assigns **#29 (audience-tagged aftermath paragraphs read by tag, not prose prefix)** to Phase 6, but its sole consumer is `MatchWeek.tsx:83-126` (the post-match aftermath grouping) — a **Phase-2** file. `types.ts:918-924` defines `AftermathParagraph.audience`, and **no `ceremonies/*` file reads `audience`** (verified by Grep — zero matches in the ceremonies dir). Phase 6 therefore cannot rebuild a #29 surface because it owns none. To honor the assignment without overstepping the freeze, Phase 6 adds a **guard test that asserts the `audience` union type is intact** (so a Phase-6 type change cannot silently break the P2 consumer) and documents that the live #29 surface is owned by Phase 2. This keeps #29 green from Phase 6's side without editing a P2 file.

**Audit numbers + test strategy:** #29 vitest (type/contract guard).

**Files:** create `frontend/src/components/ceremonies/audienceContract.test.ts`.

- [ ] **Step 1: Write the guard test** — a compile-time assertion that the `audience` union is exactly the three tags the P2 consumer groups on.

```ts
// frontend/src/components/ceremonies/audienceContract.test.ts
import { describe, it, expectTypeOf } from 'vitest';
import type { AftermathParagraph } from '../../types';

// #29 is owned by the Phase-2 aftermath surface (MatchWeek.tsx groups body
// paragraphs by AftermathParagraph.audience). No ceremonies/* file reads it.
// This guard ensures a Phase-6 type edit can't silently widen/narrow the union
// the P2 consumer depends on.
describe('AftermathParagraph.audience contract (#29 — P2-owned, P6-guarded)', () => {
  it('the audience union is exactly you | them | result', () => {
    expectTypeOf<AftermathParagraph['audience']>().toEqualTypeOf<'you' | 'them' | 'result'>();
  });
});
```

- [ ] **Step 2: Run to verify it passes** — `cd frontend && npm run test -- "audienceContract"`. Expected: PASS (the union already matches). If it FAILS, the live type differs from the audit's stated shape — STOP and reconcile with the controller before proceeding (do NOT edit `types.ts` here; that is a shared file).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/audienceContract.test.ts
git commit -m "test(ceremonies): guard AftermathParagraph.audience union for #29 (P2-owned surface)"
```

---

### Task 14: Phase-6 lane gate — full verification (worktree, OLD index.css present)

> **Why:** The per-phase gate runs in the worktree with the old `index.css` still present (the integrator does the index.css deletion + full tsc/vitest later in STEP 3). This task proves the lane is green: every ceremony vitest, the build (which is also the **frozen-P4-PlayoffBracket import-resolves gate**), lint, the token gate, and a smoke e2e of the offseason ceremony path.

- [ ] **Step 1: Run the full lane gate**

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e
```

Expected: all FE tests pass (all 12 new ceremony test files + the audience guard); build clean (proves `ChampionReveal`'s static `PlayoffBracket` import + every `'../../ui'` shim re-point resolve); eslint clean; `lint:tokens` clean (ceremonies dir is not yet in `SCAN_DIRS`, so this passes — but the reskin used tokens only, so the STEP-3 append will also be clean); e2e smoke green on the offseason path.

- [ ] **Step 2: Confirm the freezes held** — Grep to prove no forbidden edits crept in:

```bash
cd frontend
# Confirm the Phase-1 shim barrel is still intact (T0 pre-flight must still pass at end of lane):
grep -q "ActionButton" src/ui/index.ts \
  || { echo "ERROR: ActionButton shim missing from src/ui/index.ts — wrong base branch or Phase-1 was accidentally reverted"; exit 1; }
grep -q "PageHeader" src/ui/index.ts \
  || { echo "ERROR: PageHeader shim missing from src/ui/index.ts"; exit 1; }
echo "Phase-1 shim barrel intact."
# index.css untouched by this lane (no staged/committed diff):
git diff --stat origin/<post-phase-1-trunk> -- src/index.css   # expect: empty
# ui.tsx untouched:
git diff --stat origin/<post-phase-1-trunk> -- src/components/ui.tsx   # expect: empty
# check-tokens.mjs untouched:
git diff --stat origin/<post-phase-1-trunk> -- scripts/check-tokens.mjs   # expect: empty
# shared globals still present in the ceremonies dir (must be NON-zero):
```
Then use Grep for `command-action-bar` across `frontend/src/components/ceremonies` — expect it still present in every rebuilt file that had it (CeremonyShell, ChampionReveal, RecapStandings, EventsBeat, MediaEvent, DevelopmentResults, RookieClassPreview, StructuredOffseasonBeats, RecruitmentChoice, TransferPeriod). Also Grep `data-player-outcome` (EventBracket), `recap-missed-playoffs` (RecapStandings), `worlds_user` (RecapStandings), `signed_count` (Ceremonies + RecruitmentChoice), `data-broadcast-proof-source` (StructuredOffseasonBeats) — all must still resolve.

- [ ] **Step 3: Commit any fixups**

```bash
git commit -am "chore(ceremonies): Phase 6 lane gate green" --allow-empty
```

> **Handoff to integrator (STEP 3):** This lane is ready to merge. After merge, the integrator removes the legacy ceremony `index.css` selector families (`.champion-*`, `.playoff-bracket-*`, `.command-offseason-*` ceremony-only rules, `.dm-ceremony*`) — **but NOT the shared `command-action-bar`/`command-policy-overlay` globals** (P8-only) — appends `src/components/ceremonies` to `SCAN_DIRS`, and re-runs full `tsc --noEmit` + full vitest + e2e smoke.

---

## Self-Review

**Behavior coverage (Phase-6 checklist row #17,#18,#29,#31,#32,#35,#67–#75):**
- #17 worlds_user semifinal receipt → T4 ✓ · #18 missed_playoffs gate → T4 ✓ · #29 audience-tag → T13 guard (ownership clarified: P2-owned, P6 cannot rebuild — see J1) ✓ · #31 honest null-vs-zero → T3 (MediaEvent) + T6 (RookieClassPreview) + T9 (ChampionReveal) ✓ · #32 movement empty/honest → T4 ✓ · #35 truthful empty states → T5 (events) + T7 (records/HoF) ✓ · #67 signed_count single-source → T11 ✓ · #68 scope labels → T11 ✓ · #69 veto-aware latch → T8 ✓ · #70 records tiering + non-dead-end empty → T7 ✓ · #71 zero-floats → T2 + T4 + T7 ✓ · #72 training-credit receipt → T2 ✓ · #73 sign-over-cut → T10 ✓ · #74 skip/lock gate → T10 ✓ · #75 extra_stats fallback → T12 ✓.
- Named anti-strip hooks all tested: `data-player-outcome` (T5), `recap-missed-playoffs` (T4), `worlds_user` receipt (T4), `signed_count` (T11), `data-broadcast-proof-source` (T7), `command-action-bar` survival (T1), per-screen `data-testid` (every task).

**Phase-specific requirements encoded:**
- P6→P4 dependency: T9 consumes the frozen `PlayoffBracket` import unchanged; T14 build is the import-resolves gate ✓.
- Phase-1 shim dependency: T0 pre-flight confirms `ActionButton`/`PageHeader` are exported from `src/ui/index.ts` before any work begins; T14 freeze-check repeats the grep to confirm the barrel was not accidentally reverted ✓.
- `command-action-bar` shared global survives: T1 anti-strip guard + every reskin task keeps the class string + T14 Grep proof ✓.
- NO index.css edits/deletes; module CSS only; integrator owns STEP-3 deletion + SCAN_DIRS — stated in Freezes, every task, and the T14 handoff ✓.
- NO ui.tsx edits; re-point `ActionButton`/`PageHeader` from `'../ui'` → `'../../ui'` shims; no ActionButton→ActionBar remap — Freeze 2 + every reskin task ✓.
- legibility/* frozen read-only (RecruitmentChoice T10 mocks/keeps KnownValue/CeilingGrade) ✓; check-tokens.mjs untouched (T14 proof) ✓; matchResult.ts not depended on ✓.

**Placeholder scan:** No logic placeholders. Each test fixture carries a "read the exact payload shape from `types.ts` before writing — do not invent fields" guard (a correctness instruction, not a stub), because the offseason beat payloads are large discriminated unions and inventing fields would produce false-green tests. Sign-button accessible-name in T10 and the league-scope default in T7 carry explicit "adjust to the real label/logic" notes — verification guards, not gaps.

**Type / name consistency:** Component prop signatures kept identical to the live source so `Offseason.tsx` needs no edit (verified against Offseason.tsx:77-93 mounts): `ChampionReveal/RecapStandings/WorldsCrowning/EventsBeat/DevelopmentResults/RookieClassPreview/RecordsRatified/HallOfFameInduction` take `{ beat, onComplete, acting }`; `TransferPeriod` adds `onTransfer`; `MediaEvent` adds `onChoose`; `RecruitmentChoice` takes `{ beat, onSign, acting }`; `SigningDay/AwardsNight/Graduation` `{ beat, onComplete, acting }`; `NewSeasonEve` `{ beat, onComplete (beginSeason), acting }`; `EventBracket`/`EventsBeat` keep the `playerClubId?` prop. The frozen `PlayoffBracket` prop is `{ data: PlayoffBracketResponse }` (matches Phase-1 contract test). Module-class names (`styles.ceremony`, `styles.stage`, `.advanced`/`.eliminated`/`.neutral`, tier/award lookups) are referenced identically in each task's CSS + tsx.

**Judgment calls:**
- **J1 (#29 ownership):** #29's only consumer is `MatchWeek.tsx` (Phase 2); no ceremonies file reads `audience`. Phase 6 cannot rebuild a surface it doesn't own, and editing the P2 file or the shared `types.ts` violates the window freeze. Resolution: a compile-time guard test (T13) that keeps the union intact from Phase 6's side, plus explicit documentation that the live surface is P2-owned. Flag for the controller if they intended #29 to move with a different file.
- **J2 (WorldsCrowning):** in the audit's Ceremonies area and mounted by Offseason, but NOT in this plan's assigned file list and its behavior (#40) is a Phase-8 sweep item, not on the Phase-6 row. Left byte-untouched; noted in scope.
- **J3 (EventsBeat playerClubId not wired):** `Offseason.tsx:81` mounts EventsBeat without `playerClubId`, so `data-player-outcome` is latent in the live path. Preserved the prop + tested the hook directly rather than "fixing" the wiring (out of Phase-6 scope — an Offseason/backend decision).
- **J4 (sticky action-bar layout left inline):** the `command-action-bar` sticky positioning stays as the shared global's existing inline values rather than moving into a module, because the bar is a shared surface unified by the `ActionBar` primitive only in Phase 8; moving its layout now would diverge it from the 9 other consumers mid-window.
- **J5 (legibility ScrollRegion use in RecruitmentChoice):** routing the release-picker inner scroll through the Phase-0 `ScrollRegion` primitive (T10) fixes audit §3 P4 without touching `legibility/*`; `ScrollRegion` is a `src/ui` primitive, not a legibility one, so this respects the freeze.
