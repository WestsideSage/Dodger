# Floodlight Phase 7 — New-Game Wizard (4 steps) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the four Build-From-Scratch wizard steps (`new-game/{IdentityStep,CoachStep,StaffHiringStep,StartingRecruitmentStep}.tsx`) from inline-style objects + literal slate/cyan hex onto the Floodlight token system via scoped CSS Modules, while keeping the 7 onboarding-integrity trust behaviors green (#22, #76–#81) and every `data-*`/`role`/`aria` truth hook intact. **Only the styling substrate changes** — the wizard's validation logic, seed continuity, role-coverage tally, budget defaulting, and the 6..10 roster bound are preserved verbatim.

**Architecture:** Each step component moves its inline `style={{…}}` objects and the literal `#0f172a/#334155/#94a3b8/#22d3ee/#f97316` palette to a per-component `*.module.css` driven by `src/styles/tokens.css`, and re-points its `ActionButton` import from `../ui` (the `components/ui.tsx` source) to the Phase-1 `src/ui` shim. Runtime club-color values (`currentPrimary`/`currentSecondary` in IdentityStep's preview) move from inline `style={{ background: currentPrimary }}` to CSS custom properties set on the element (`style={{ ['--kit-primary']: currentPrimary }}`) consumed by the module CSS — so the token gate sees no raw hex on those lines. `TermTip`/`CeilingGrade` (legibility) and the `StaffCandidate`/`ProspectOption` types are consumed unchanged.

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (harness from Phase 0).

**Spec:** [2026-06-19-ui-redesign-design.md](../specs/2026-06-19-ui-redesign-design.md) §3.4 (the 5-color contract; runtime club color is data, not theme) · **Non-regression contract:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md) §1 (New-game wizard screens), §2.B #22, §2.I #76–#81, §3 wizard layout-bug rows (off-screen-footer maxHeight 380/360px; nowrap prospect name; Foundation/budget chip wrap) · **Checklist:** [floodlight-preservation-checklist.md](floodlight-preservation-checklist.md) Phase 7 row (#22, #76–#81) · **Orchestration contract:** [2026-06-19-floodlight-parallelization-strategy.md](2026-06-19-floodlight-parallelization-strategy.md) STEP 2 concurrent window, **merge-strict edge 7→1**, runtime club-color token-gate risk · **Foundations + style template:** [2026-06-19-floodlight-phase-0-foundations.md](2026-06-19-floodlight-phase-0-foundations.md) · **Phase-1 locked contracts:** [2026-06-19-floodlight-phase-1-app-shell.md](2026-06-19-floodlight-phase-1-app-shell.md) (the 5 `src/ui` shims, `appContracts.ts`).

**Branch / worktree:** This is a MIDDLE phase in STEP 2 of the parallelized window. Run it in an **isolated git worktree branched from the MERGED post-Phase-1 trunk** (merge-strict 7→1: the wizard is mounted from `SaveMenu.tsx`, which Phase 1 owns and reskins — branch only after Phase 1 has merged, so the SaveMenu mount frame + build state are already in their final structural form). All Phase-7 commits land on the worktree branch; the controller merges.

---

## Hard rules this phase encodes (from the orchestration contract)

These are task constraints, not suggestions. Every task below honors them.

- **Touch ONLY `frontend/src/components/new-game/*`** (the 4 step components + their new `*.module.css` + `*.test.tsx`). **Do NOT edit `SaveMenu.tsx`** — Phase 1 owns it; it hosts the wizard mounts (`SaveMenu.tsx:960–963`) and the shared build state (`buildIdentity/buildCoach/buildStaff/buildSeed`), left structurally intact for this phase. The step props (`identity/setIdentity/onNext/onBack/takenNames`, `coach/setCoach`, `seed/choices/setChoices`, `seed/onCommit/onBack/creating`) are the frozen interface — **do not change a single prop name or shape**, or SaveMenu's call sites break.
- **NO `index.css` edits or deletions.** Create `*.module.css` ONLY. The wizard's legacy `index.css` selector families it still leans on (`.dm-kicker`, `.dm-helper-copy`, `.dm-helper-copy-warning`, `.dm-badge`, `.dm-badge-slate`, `.dm-data`) are removed later by the serial integrator in STEP 3 — this plan does **not** include any `index.css` deletion task and must leave those globals untouched. (Migrate the wizard's own usages of them into module CSS so STEP 3's removal is safe, but do not delete the global rules.)
- **NO edits to `components/ui.tsx`.** Re-point each step's `ActionButton` import from `../ui` to the Phase-1 `src/ui` shim. **Import-path change ONLY** — keep `ActionButton`; **no `ActionButton→ActionBar` remap** (deferred to Phase 8).
- **FROZEN — consume, never alter:** the wizard data already routes through `saveApi.startingStaff(seed)` / `saveApi.startingProspects(seed)` (folded in during Phase 0 — verified in `StaffHiringStep.tsx:41` and `StartingRecruitmentStep.tsx:68`); **consume those, do NOT re-add raw `fetch`**. `match-week/matchResult.ts` (not used here, do not import). `legibility/*` (`TermTip`, `CeilingGrade`, `TermId`) — read-only, accept mixed Floodlight+legacy look until Phase 8. `frontend/scripts/check-tokens.mjs` — integrator owns `SCAN_DIRS`; this phase NEVER appends `new-game` to it.
- **Consume Phase-1 published contracts where relevant:** none of the new-game steps mount `MatchWeek`, `PlayoffBracket`, or `ProgramModal`, so `appContracts.ts` is not imported here. The relevant Phase-1 contract this phase consumes is the **5 `src/ui` shims** (`ActionButton`).
- **`data-*` anti-strip vitests are HARD RED preconditions.** The truth-provenance hooks present on this phase's screens are: `data-testid="save-name-collision-banner"` (IdentityStep, #76), `data-testid="staff-budget-bar"` + `data-testid="staff-candidate-card"` (StaffHiringStep), `role="alert"` on the collision banner (IdentityStep, #76), `role="radio"`+`aria-checked` (StaffHiringStep candidate cards), `role="checkbox"`+`aria-checked` (StartingRecruitmentStep prospect rows), `aria-pressed` on color/archetype toggles. Every rebuild keeps them; each task writes the assertions before touching markup.

**Per-phase gate** (runs in the worktree with the OLD `index.css` still present — the integrator runs the `index.css` deletion + full `tsc`/vitest later):

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e   # smoke
```

> **Token-gate note:** `npm run lint:tokens` currently scans only `src/ui` + `src/styles` (Phase-0 `SCAN_DIRS`). `new-game/*` is NOT in scope during this window — the integrator appends it in STEP 3 only once the dir is clean. **Therefore the gate will not catch a raw hex/px left in a wizard module.** Each reskin task MUST pre-empt this by using only `var(--…)` tokens (no raw hex; no raw px beyond `0`/`1px` hairlines) from the start, and Task 7 runs a **temporary scoped token scan** over `new-game/` to prove cleanliness before handoff (without modifying the committed gate). The runtime club-color custom-property pattern (below) is the one deliberate exception, kept off the literal-bearing lines.

---

## Runtime club-color handling (the token-gate trap, decided here)

IdentityStep renders the user's chosen kit colors at runtime: `currentPrimary`/`currentSecondary` (derived from `identity.colors`, e.g. `"#22d3ee,#0f172a"`) drive the preset swatches (`IdentityStep.tsx:176–177`), the preview chip (`:189–190`), and the preview card border (`:201–202`). These are **user data, not theme tokens** (design §3.4: the 5-color Floodlight contract is the chrome; the club kit is content painted into it). Inline `style={{ background: currentPrimary }}` is correct semantically but would read as a raw-hex literal if `new-game/` were ever scanned.

**Decision (encoded in Task 6):** move every runtime club-color value off the JSX style literal into a **CSS custom property** set on the element and consumed by the module CSS:

```tsx
// the element carries the data as a custom property (a JS variable, not a hex literal in source)
<span className={styles.swatchPrimary} style={{ ['--kit-primary' as string]: preset.primary }} />
```
```css
/* module CSS consumes it via var() — the only place "color" appears is a token-named var */
.swatchPrimary { background: var(--kit-primary); }
```

The `preset.primary` hex literals live in ONE place — the `COLOR_PRESETS` array (`IdentityStep.tsx:3–10`), which is **data** (six named kits the user picks from), not styling. Keep that array as-is; it is the single literal-bearing construct and is exempt by intent (the integrator extends `ALLOW_LINE`/`ALLOW_FILE` for the preset data line at STEP-3 token-clean time if needed — Task 6 leaves a `// token-gate: COLOR_PRESETS is kit DATA, not theme` marker on it so the integrator can target it precisely). No other line in any wizard module may carry a raw hex.

---

## File map (created/modified in this plan)

**Created:**
- `frontend/src/components/new-game/IdentityStep.module.css`
- `frontend/src/components/new-game/IdentityStep.test.tsx`
- `frontend/src/components/new-game/CoachStep.module.css`
- `frontend/src/components/new-game/CoachStep.test.tsx`
- `frontend/src/components/new-game/StaffHiringStep.module.css`
- `frontend/src/components/new-game/StaffHiringStep.test.tsx`
- `frontend/src/components/new-game/StartingRecruitmentStep.module.css`
- `frontend/src/components/new-game/StartingRecruitmentStep.test.tsx`

**Modified:**
- `frontend/src/components/new-game/IdentityStep.tsx` (reskin to module CSS + `src/ui` ActionButton import + kit-color custom properties)
- `frontend/src/components/new-game/CoachStep.tsx` (reskin)
- `frontend/src/components/new-game/StaffHiringStep.tsx` (reskin; **keep** `saveApi.startingStaff` + budget logic verbatim; replace `maxHeight:'380px'` scroll with token-driven `ScrollRegion`/module class)
- `frontend/src/components/new-game/StartingRecruitmentStep.tsx` (reskin; **keep** `saveApi.startingProspects` + tally + 6..10 bound verbatim; fix prospect-name overflow; replace `maxHeight:'360px'`)

**Frozen / not touched:** `SaveMenu.tsx`, `components/ui.tsx`, `index.css`, `frontend/scripts/check-tokens.mjs`, `legibility/*`, `match-week/matchResult.ts`, `appContracts.ts`, all step **prop interfaces** (names + shapes).

---

## Behavior coverage map (audit §2 → task → test strategy)

| # | Behavior (short) | Source line(s) | Task | Test strategy |
|---|---|---|---|---|
| 76 | Save-name uniqueness validated up-front on Step 1 with visible banner | IdentityStep.tsx:76–82,107–124 | 2, 6 | vitest |
| 22 | Founding-class prospects shown UNFOGGED (full sheet, same as roster row) | StartingRecruitmentStep.tsx:13–27,145–149 (ratings/ceiling render :284–321) | 8, 9 | vitest |
| 77 | Seed continuity: fetch seed === root_seed POSTed | SaveMenu.tsx:158,258 (consumed via `seed` prop, fetched StaffHiring:41 / Recruitment:68) | 4, 8, 9 | vitest (prop→fetch wiring) |
| 78 | Staff step never soft-locks: defaults each dept to cheapest affordable; over-budget blocked | StaffHiringStep.tsx:46–61,77–78,216–221 | 8 | vitest |
| 79 | Empty `{}` staff_choices never sent; omitted when empty | SaveMenu.tsx:256 (NOT in scope — owned by P1/SaveMenu) | — | (out of scope; assert step never emits empty via setChoices default — Task 8) |
| 80 | Role-coverage tally counts coverage (hybrids multi-lane), imbalance advisory-only | StartingRecruitmentStep.tsx:82–98,198–212 | 9 | vitest |
| 81 | Roster selection bounded 6..10, state-specific helper copy, hard 11th-cap refusal | StartingRecruitmentStep.tsx:73–80,100–109,337–341 | 9 | vitest |

> #77 and #79 are primarily SaveMenu's responsibility (the POST is built there, out of this phase's scope). This phase covers the **step side** of the contract: the step fetches with exactly the `seed` prop SaveMenu passes (#77), and the staff step keeps `choices` populated via the cheapest-affordable default so SaveMenu never receives an empty `{}` from a touched-but-empty state (#79 corollary). The SaveMenu-side POST assertions remain Phase 1's; this plan does not duplicate or move them.

---

## Phase 7A — Lock behavior before reskin (RED preconditions on current markup)

> Discipline (spec §5.8): author behavior + `data-*` anti-strip vitests against the CURRENT (pre-reskin) components so they pass on existing markup, then each reskin task must keep them green. The harness has zero new-game screen tests today, so these tests are net-new and become the non-regression contract.

### Task 1: IdentityStep behavior lock (#76 collision banner + anti-strip hooks)

**Files:** create `frontend/src/components/new-game/IdentityStep.test.tsx`.

**Current truth captured (IdentityStep.tsx):** props `{ identity, setIdentity, onNext, onBack, takenNames=[] }` (`:56–69`); `nameTaken` is case-insensitive, trim-aware (`:78–81`); banner has `role="alert"` + `data-testid="save-name-collision-banner"` (`:110–111`); `aria-invalid={nameTaken}` on input (`:103`); Next is disabled unless `canContinue` (all fields + not taken) (`:82,216`); color presets are `<button aria-pressed>` (`:160`).

- [ ] **Step 1: Write the failing tests** (fail only because the file doesn't exist yet; logic is current behavior):

```tsx
// frontend/src/components/new-game/IdentityStep.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { IdentityStep } from './IdentityStep';

type Identity = { save_name: string; club_name: string; city: string; colors: string };
const base: Identity = { save_name: '', club_name: '', city: '', colors: '#22d3ee,#0f172a' };

function setup(identity: Partial<Identity>, takenNames: string[] = []) {
  const setIdentity = vi.fn();
  const onNext = vi.fn();
  const onBack = vi.fn();
  render(
    <IdentityStep
      identity={{ ...base, ...identity }}
      setIdentity={setIdentity}
      onNext={onNext}
      onBack={onBack}
      takenNames={takenNames}
    />,
  );
  return { setIdentity, onNext, onBack };
}

describe('IdentityStep (audit #76 — save-name uniqueness up front)', () => {
  it('shows the collision banner (role=alert, data-testid) for a case-insensitive taken name', () => {
    setup({ save_name: 'My Career', club_name: 'Hawks', city: 'Northwood' }, ['my career']);
    const banner = screen.getByTestId('save-name-collision-banner');
    expect(banner).toHaveAttribute('role', 'alert');
    expect(banner).toHaveTextContent(/already exists/i);
  });
  it('disables Next while the name collides and marks the input invalid', () => {
    setup({ save_name: 'Dup', club_name: 'Hawks', city: 'Northwood' }, ['dup']);
    expect(screen.getByRole('button', { name: /Next: Coach Profile/i })).toBeDisabled();
    expect(screen.getByLabelText(/Save Name/i)).toHaveAttribute('aria-invalid', 'true');
  });
  it('enables Next and renders no banner when all fields are filled and the name is free', () => {
    setup({ save_name: 'Fresh', club_name: 'Hawks', city: 'Northwood' }, ['other']);
    expect(screen.queryByTestId('save-name-collision-banner')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next: Coach Profile/i })).toBeEnabled();
  });
  it('keeps color presets as aria-pressed toggles that emit a colors value', async () => {
    const { setIdentity } = setup({ club_name: 'Hawks', city: 'Northwood' });
    const fire = screen.getByRole('button', { name: 'Fire' });
    expect(fire).toHaveAttribute('aria-pressed', 'false');
    await userEvent.click(fire);
    expect(setIdentity).toHaveBeenCalledWith(expect.objectContaining({ colors: expect.stringContaining(',') }));
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "new-game/IdentityStep"`. Expected: PASS against the current component (markup unchanged), proving the harness + assertions are correctly wired. The accessible name for each preset button comes from the label span text (e.g. `"Fire"`) nested inside the button — RTL resolves it from the visible text content, not the `title` attribute. If the accessible name lookup fails for any reason, fix the assertion to the current truth rather than guessing.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/new-game/IdentityStep.test.tsx
git commit -m "test(new-game): lock IdentityStep #76 collision banner + anti-strip hooks before reskin"
```

---

### Task 2: StaffHiringStep + StartingRecruitmentStep behavior lock (#22,#77,#78,#80,#81 + anti-strip)

**Files:** create `frontend/src/components/new-game/StaffHiringStep.test.tsx` and `frontend/src/components/new-game/StartingRecruitmentStep.test.tsx`. (CoachStep has no audit behavior; its anti-strip + reskin guard is folded into Task 5.)

**Current truth captured:**
- StaffHiringStep props `{ seed, choices, setChoices, onNext, onBack }` (`:23–36`); fetches via `saveApi.startingStaff(seed)` (`:41`); defaults each dept to cheapest affordable on market load (`:48–61`); `overBudget` blocks Next (`:78,216`); budget bar `data-testid="staff-budget-bar"` (`:96`); candidate cards `role="radio"` + `aria-checked` + `data-testid="staff-candidate-card"` (`:159–161`).
- StartingRecruitmentStep props `{ seed, onCommit, onBack, creating }` (`:50–62`); fetches via `saveApi.startingProspects(seed)` (`:68`); `toggleProspect` caps add at `next.size < 10` (`:77`); tally counts role coverage with hybrids multi-lane (`:83–93`); `rosterReady = size>=6` / `rosterFull = size>=10` with state-specific `rosterHelp` (`:101–109`); Commit disabled `size<6||creating`, label `Next: Commit Roster (n/10)` (`:337–341`); prospect rows `role="checkbox"` + `aria-checked` + descriptive `aria-label` (`:237–239`); ratings/ceiling render unfogged (`:284–321`).

Mock the client so the steps render deterministically:

```tsx
// frontend/src/components/new-game/StaffHiringStep.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useState } from 'react';

vi.mock('../../api/client', () => ({
  saveApi: { startingStaff: vi.fn() },
}));
import { saveApi } from '../../api/client';
import { StaffHiringStep } from './StaffHiringStep';
import type { StartingStaffResponse } from '../../types';

const MARKET: StartingStaffResponse = {
  departments: ['offense', 'defense'],
  budget_k: 500,
  mid_table_payout_k: 800,
  rules: 'One head per department.',
  candidates: [
    { candidate_id: 'o-cheap', department: 'offense', tier: 'journeyman', name: 'Cheap O', rating_primary: 50, rating_secondary: 50, salary_k: 100, voice: 'v', effect_summary: 'e' },
    { candidate_id: 'o-pricey', department: 'offense', tier: 'premium', name: 'Pricey O', rating_primary: 80, rating_secondary: 80, salary_k: 900, voice: 'v', effect_summary: 'e' },
    { candidate_id: 'd-cheap', department: 'defense', tier: 'journeyman', name: 'Cheap D', rating_primary: 50, rating_secondary: 50, salary_k: 100, voice: 'v', effect_summary: 'e' },
  ],
};

// A controlled choices container so we can observe defaulting + selection.
// Top-level import (not CJS require) is required for Vite 8 + Vitest ESM.
function Harness({ seed = 7 }: { seed?: number }) {
  const [choices, setChoices] = useState<Record<string, string>>({});
  return <StaffHiringStep seed={seed} choices={choices} setChoices={setChoices} onNext={() => {}} onBack={() => {}} />;
}

beforeEach(() => vi.clearAllMocks());

describe('StaffHiringStep (audit #77 seed continuity, #78 no soft-lock)', () => {
  it('#77: fetches the founding staff market with exactly the seed prop', async () => {
    vi.mocked(saveApi.startingStaff).mockResolvedValue(MARKET);
    render(<Harness seed={4242} />);
    await waitFor(() => expect(saveApi.startingStaff).toHaveBeenCalledWith(4242));
  });
  it('#78: defaults every department to its cheapest candidate and enables Next', async () => {
    vi.mocked(saveApi.startingStaff).mockResolvedValue(MARKET);
    render(<Harness />);
    await screen.findByTestId('staff-budget-bar');
    // cheapest in each dept selected => all filled => Next enabled, not over budget
    await waitFor(() => expect(screen.getByRole('button', { name: /Next: Recruit Roster/i })).toBeEnabled());
  });
  it('#78: selecting an over-budget candidate blocks Next with the cheapen-a-hire label', async () => {
    vi.mocked(saveApi.startingStaff).mockResolvedValue(MARKET);
    render(<Harness />);
    await screen.findByTestId('staff-budget-bar');
    const cards = await screen.findAllByTestId('staff-candidate-card');
    // pick the pricey offense head (900 > 500 budget)
    const pricey = cards.find(c => c.textContent?.includes('Pricey O'))!;
    await userEvent.click(pricey);
    expect(pricey).toHaveAttribute('role', 'radio');
    await waitFor(() => expect(screen.getByRole('button', { name: /Over budget/i })).toBeDisabled());
  });
});
```

```tsx
// frontend/src/components/new-game/StartingRecruitmentStep.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../api/client', () => ({
  saveApi: { startingProspects: vi.fn() },
}));
import { saveApi } from '../../api/client';
import { StartingRecruitmentStep } from './StartingRecruitmentStep';
import type { ProspectOption } from '../../types';

function prospect(id: string, archetype: string, over = 60): ProspectOption {
  return {
    player_id: id, name: `Player ${id}`, hometown: 'Townsville',
    public_archetype: archetype, public_ovr_band: [over - 5, over + 5],
    age: 18, potential_ceiling: over + 20, potential_tier: 'High',
    ratings: { accuracy: over, power: over, dodge: over, catch: over, stamina: over, tactical_iq: over },
  };
}
// 11 prospects so we can test the hard 11th-cap refusal. Mix archetypes for tally.
const POOL: ProspectOption[] = [
  prospect('a', 'Sharpshooter'), prospect('b', 'Sharpshooter'), prospect('c', 'Net Specialist'),
  prospect('d', 'Net Specialist'), prospect('e', 'Iron Anchor'), prospect('f', 'Two-Way Threat'),
  prospect('g', 'Skirmisher'), prospect('h', 'Ball Hawk'), prospect('i', 'Hit-and-Run'),
  prospect('j', 'Possession Specialist'), prospect('k', 'Sharpshooter'),
];

beforeEach(() => vi.clearAllMocks());

async function loaded(onCommit = vi.fn()) {
  vi.mocked(saveApi.startingProspects).mockResolvedValue({ prospects: POOL });
  render(<StartingRecruitmentStep seed={99} onCommit={onCommit} onBack={() => {}} creating={false} />);
  await screen.findAllByRole('checkbox');
  return { onCommit, rows: screen.getAllByRole('checkbox') };
}

describe('StartingRecruitmentStep (audit #22,#77,#80,#81)', () => {
  it('#77: fetches the founding prospect pool with exactly the seed prop', async () => {
    vi.mocked(saveApi.startingProspects).mockResolvedValue({ prospects: POOL });
    render(<StartingRecruitmentStep seed={314} onCommit={() => {}} onBack={() => {}} creating={false} />);
    await waitFor(() => expect(saveApi.startingProspects).toHaveBeenCalledWith(314));
  });

  it('#22: renders each prospect UNFOGGED — full ratings + numeric ceiling on the row', async () => {
    await loaded();
    const firstRow = screen.getAllByRole('checkbox')[0];
    expect(firstRow).toHaveTextContent('ACC');
    expect(firstRow).toHaveTextContent('IQ');
    expect(firstRow).toHaveTextContent(/Ceil/);
  });

  it('#81: roster bounded 6..10 — Commit disabled below 6, helper copy is state-specific', async () => {
    const { onCommit, rows } = await loaded();
    const commit = () => screen.getByRole('button', { name: /Commit Roster/i });
    expect(commit()).toBeDisabled();
    expect(screen.getByText(/Choose between 6 and 10 players/i)).toBeInTheDocument();
    for (let i = 0; i < 6; i++) await userEvent.click(rows[i]);
    expect(commit()).toBeEnabled();
    expect(screen.getByText(/Roster ready/i)).toBeInTheDocument();
    await userEvent.click(commit());
    expect(onCommit).toHaveBeenCalledWith(expect.arrayContaining([expect.any(String)]));
  });

  it('#81: hard 11th-cap refusal — a non-selected row is non-togglable once 10 are chosen', async () => {
    const { rows } = await loaded();
    for (let i = 0; i < 10; i++) await userEvent.click(rows[i]);
    expect(screen.getAllByRole('checkbox').filter(r => r.getAttribute('aria-checked') === 'true')).toHaveLength(10);
    await userEvent.click(rows[10]); // the 11th
    expect(rows[10]).toHaveAttribute('aria-checked', 'false');
    expect(screen.getAllByRole('checkbox').filter(r => r.getAttribute('aria-checked') === 'true')).toHaveLength(10);
  });

  it('#80: role-coverage tally is advisory — imbalance never blocks Commit', async () => {
    const { rows } = await loaded();
    // Select 6 rows by index: Sharpshooter×2, Net Specialist×2, Iron Anchor, Two-Way Threat.
    // Whether composition is balanced or not, Commit must be enabled (tally is advisory only).
    // Index-based selection avoids coupling to formatPlayerName's output format.
    for (let i = 0; i < 6; i++) await userEvent.click(rows[i]);
    expect(screen.getByRole('button', { name: /Commit Roster/i })).toBeEnabled();
  });
});
```

- [ ] **Step 1: Write both failing test files** (above).
- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "new-game/StaffHiringStep" "new-game/StartingRecruitmentStep"`. Expected: PASS against current components. Do not invent component behavior if assertions fail — fix the assertion to the current truth instead.
- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/new-game/StaffHiringStep.test.tsx frontend/src/components/new-game/StartingRecruitmentStep.test.tsx
git commit -m "test(new-game): lock staff/recruitment #22/#77/#78/#80/#81 + anti-strip hooks before reskin"
```

---

## Phase 7B — Reskin each step to CSS Modules (keep all behavior + hooks green)

> Each reskin task: (1) add a thin RED guard for any structural detail the reskin must preserve that Phase-7A didn't already pin (often none — the 7A tests are the guard); (2) move inline styles → `*.module.css` token classes; (3) re-point the `ActionButton` import to `src/ui`; (4) re-run the step's 7A tests GREEN + build + lint. **Logic lines are copied verbatim** — diff should show only `style={{…}}` → `className={styles.…}`, import path, and the kit-color custom-property rewrite.

### Task 3: Re-point all 4 steps' `ActionButton` import to the `src/ui` shim

**Files:** modify the import line in all 4 step components.

> The shim is signature-identical (Phase 1 Task 1) and keeps the `dm-action dm-action-${variant}` classes, so this is a pure import-path swap with no visual or behavioral change. Doing it as its own commit isolates the contract change from the CSS churn.

- [ ] **Pre-condition guard (STOP if not met):** Run `grep -n "ActionButton" frontend/src/ui/index.ts`. The output MUST contain a non-empty match (e.g. `export { ActionButton } from './ActionButton';`). If it returns empty, Phase 1 has not merged to trunk yet — **stop here, do not edit any step file**, and notify the STEP-2 controller to confirm Phase 1 is on the branch this worktree forked from before continuing. (This guard enforces the merge-strict 7→1 edge stated in the plan header.)

- [ ] **Step 1:** In each of `IdentityStep.tsx`, `CoachStep.tsx`, `StaffHiringStep.tsx`, `StartingRecruitmentStep.tsx`, change `import { ActionButton } from '../ui';` → `import { ActionButton } from '../../ui';` (the `src/ui` barrel is at `frontend/src/ui/index.ts`; from `components/new-game/` that is `../../ui`). **Do not** change to `ActionBar`.
- [ ] **Step 2: Verify** — `cd frontend && npm run test -- "new-game/" && npm run build && npm run lint`. Expected: all 7A tests still GREEN; build + lint clean (the shim resolves; same component contract).
- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/new-game/IdentityStep.tsx frontend/src/components/new-game/CoachStep.tsx frontend/src/components/new-game/StaffHiringStep.tsx frontend/src/components/new-game/StartingRecruitmentStep.tsx
git commit -m "refactor(new-game): re-point ActionButton imports to src/ui shim (no remap)"
```

---

### Task 4: IdentityStep reskin (#76) + kit-color custom properties

**Files:** create `IdentityStep.module.css`; modify `IdentityStep.tsx`.

**Inline styles to migrate (IdentityStep.tsx):** `Field` label (`:34–39`); `inputStyle` object (`:45–54`) → `.input`; the wrapper flex column (`:88`); the `dm-kicker` + `<h2>` (`:90–93`); collision banner inline block (`:112–120`) → `.collisionBanner` (KEEP `role="alert"` + `data-testid` + `id` for `aria-describedby`); the `<fieldset>`/`<legend>` (`:149–152`); preset buttons (`:163–173`) → `.presetBtn` / `.presetBtnSelected`; swatch spans (`:176–177`) → `.swatch` + kit custom props; the preview chip (`:188–191`) + preview card (`:201–207`) → `.previewCard` + kit custom props; the helper-copy `<p>` (`:223`).

- [ ] **Step 1: Add the kit-color RED guard** to `IdentityStep.test.tsx` (proves the preview still paints the chosen kit after the rewrite — the data must survive the inline→custom-property move):

```tsx
it('paints the chosen kit on the preview via a custom property (no lost club color)', () => {
  // club_name and city are required in the setup — the preview block only
  // renders when (identity.club_name || identity.city) is truthy (IdentityStep.tsx:200).
  setup({ club_name: 'Hawks', city: 'Northwood', colors: '#abcdef,#123456' });
  const card = screen.getByText('Preview').closest('[data-testid="identity-preview"]')!;
  expect((card as HTMLElement).style.getPropertyValue('--kit-primary')).toBe('#abcdef');
});
```
(Add `data-testid="identity-preview"` to the preview card wrapper as part of the reskin — it is a new test hook, not a truth hook; documented here so the assertion is grounded.)

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "new-game/IdentityStep"`. Expected: the new case FAILS (no `--kit-primary` / `data-testid="identity-preview"` yet); the #76 cases still PASS.

- [ ] **Step 3: Implement** — create `IdentityStep.module.css` (token-only: `var(--court)/var(--raise)/var(--line)/var(--line2)/var(--text)/var(--text2)/var(--muted)/var(--volt)/var(--space-*)/var(--radius-*)/var(--font-*)`). Rewrite `IdentityStep.tsx` markup to `className={styles.*}`. For every runtime kit color, set a custom property and consume it in CSS:

```tsx
// preset swatch
<span className={styles.swatch} style={{ ['--kit-primary' as string]: preset.primary }} />
<span className={styles.swatch} style={{ ['--kit-secondary' as string]: preset.secondary }} />
// preview card (data-testid added for the guard test)
<div className={styles.previewCard} data-testid="identity-preview"
     style={{ ['--kit-primary' as string]: currentPrimary, ['--kit-secondary' as string]: currentSecondary }}>
```
```css
.swatch { width: 12px; height: 12px; border-radius: 2px; display: inline-block; }
/* one swatch uses primary, the other secondary — set via the inline custom prop */
.previewCard { background: var(--kit-secondary); border: 1px solid var(--kit-primary);
  border-left: 3px solid var(--kit-primary); border-radius: var(--radius-md); padding: var(--space-4) var(--space-5); }
```
Keep `COLOR_PRESETS` (`:3–10`) exactly as-is and add the marker comment `// token-gate: COLOR_PRESETS is kit DATA, not theme` above it. Keep `colorsToValue`, `nameTaken`, `canContinue`, `missingFields`, every `onChange`/`onClick`/`aria-*` verbatim. The collision banner keeps `role="alert" data-testid="save-name-collision-banner" id="identity-save-name-error"`. **No raw hex on any line except the `COLOR_PRESETS` data array.**

- [ ] **Step 4: Run to verify GREEN** — `cd frontend && npm run test -- "new-game/IdentityStep" && npm run build && npm run lint`. Expected: all IdentityStep cases PASS; build + lint clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/new-game/IdentityStep.tsx frontend/src/components/new-game/IdentityStep.module.css frontend/src/components/new-game/IdentityStep.test.tsx
git commit -m "feat(new-game): reskin IdentityStep to tokens + kit-color custom properties (#76 preserved)"
```

---

### Task 5: CoachStep reskin (no audit behavior; preserve a11y toggles)

**Files:** create `CoachStep.module.css`; create `CoachStep.test.tsx`; modify `CoachStep.tsx`.

**Inline styles to migrate (CoachStep.tsx):** wrapper (`:38`); kicker + `<h2>` (`:40–43`); coach-name label + input (`:47–69`) → `.input`; `<fieldset>`/`<legend>` (`:72–75`); archetype cards (`:85–96`) → `.archetypeCard` / `.archetypeCardSelected` (KEEP `aria-pressed`); the `dm-badge dm-badge-slate` tagline (`:102`) → `.tagline`; summary block (`:112`); helper copy (`:131`).

- [ ] **Step 1: Write a small behavior+anti-strip test** (CoachStep has no audit number, but its archetype radios are a UX truth surface):

```tsx
// frontend/src/components/new-game/CoachStep.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { CoachStep } from './CoachStep';

const coach = { coach_name: '', coach_backstory: 'Tactical Mastermind' };

it('keeps archetype options as aria-pressed toggles and gates Next on a coach name', async () => {
  const setCoach = vi.fn();
  const onNext = vi.fn();
  render(<CoachStep coach={coach} setCoach={setCoach} onNext={onNext} onBack={() => {}} />);
  expect(screen.getByRole('button', { name: /Next: Recruit Roster/i })).toBeDisabled();
  const lifer = screen.getByRole('button', { name: /Former Player/i });
  expect(lifer).toHaveAttribute('aria-pressed', 'false');
  await userEvent.click(lifer);
  expect(setCoach).toHaveBeenCalledWith(expect.objectContaining({ coach_backstory: 'Former Player' }));
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "new-game/CoachStep"`. Expected: PASS on current markup.
- [ ] **Step 3: Implement** — create `CoachStep.module.css` (token-only); rewrite `CoachStep.tsx` markup to module classes. Keep `ARCHETYPES`, `selected`, `coachReady`, every `aria-pressed`/`onClick`/`onChange` verbatim. Migrate the `dm-badge dm-badge-slate` tagline to a `.tagline` module class (do NOT delete the global rule). No raw hex/px.
- [ ] **Step 4: Run to verify GREEN** — `cd frontend && npm run test -- "new-game/CoachStep" && npm run build && npm run lint`. Expected: PASS + clean.
- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/new-game/CoachStep.tsx frontend/src/components/new-game/CoachStep.module.css frontend/src/components/new-game/CoachStep.test.tsx
git commit -m "feat(new-game): reskin CoachStep to tokens (archetype a11y preserved)"
```

---

### Task 6: StaffHiringStep reskin (#77,#78) + fix off-screen-footer scroll

**Files:** create `StaffHiringStep.module.css`; modify `StaffHiringStep.tsx`.

**Inline styles to migrate + layout bug to fix (StaffHiringStep.tsx):** wrapper (`:81`); kicker + header + intro (`:83–91`); budget bar (`:97–127`) → `.budgetBar` / `.budgetBarOver` (KEEP `data-testid="staff-budget-bar"`; the `TIER_LABEL` colors `:13–17` and the over-budget red move to module tone classes — see below); load-error block (`:130`); loading copy (`:135`); **`maxHeight:'380px'` scroll container (`:139` — audit §3 "high": pushes Next off-screen)** → token-driven scroll via a module class `.deptScroll` with `max-height: min(380px, 50vh)` (or wrap in `ScrollRegion` from `src/ui`); dept rows + candidate cards (`:144–202`) → `.candidateCard` / `.candidateCardSelected` (KEEP `role="radio"` + `aria-checked` + `data-testid="staff-candidate-card"`); the `rules` line (`:208`); action row (`:211`).

> **TIER_LABEL color trap:** `TIER_LABEL` (`:13–17`) maps tier → `{ label, color: '#94a3b8'|'#22d3ee'|'#fbbf24' }` and is applied at `:179`. Move the three colors to module tone classes (`.tierJourneyman`/`.tierSolid`/`.tierPremium`) keyed off `candidate.tier`, and reduce `TIER_LABEL` to `{ label }` only — so no raw hex survives in the component. The over-budget red (`:99,112,118`) becomes `.budgetBarOver` / `.amountOver` token classes (`var(--volt)` / `var(--gold)` / `var(--ok)`).

- [ ] **Step 1: Add a RED guard** for the scroll-fix + tier-class rewrite to `StaffHiringStep.test.tsx`:

```tsx
it('renders the dept market in a bounded scroll region without an inline 380px height', async () => {
  vi.mocked(saveApi.startingStaff).mockResolvedValue(MARKET);
  render(<Harness />);
  const region = await screen.findByTestId('staff-dept-scroll');
  // the height comes from a class, not an inline style literal
  expect(region.style.maxHeight).toBe('');
});
```
(Add `data-testid="staff-dept-scroll"` to the scroll container during the reskin.)

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "new-game/StaffHiringStep"`. Expected: the new case FAILS (no `staff-dept-scroll` yet); #77/#78 cases still PASS.
- [ ] **Step 3: Implement** — create `StaffHiringStep.module.css` (token-only); rewrite markup. **Keep verbatim:** the `saveApi.startingStaff(seed)` effect (`:40–44`), the cheapest-affordable defaulting effect (`:48–61`), `committedPayroll`/`budget`/`openingTreasury`/`allFilled`/`overBudget` (`:67–78`), the Next disable + label logic (`:213–221`). Reduce `TIER_LABEL` to labels-only and add tier tone classes. Replace the `maxHeight:'380px'` div with `<div data-testid="staff-dept-scroll" className={styles.deptScroll}>`. No raw hex/px in the module or component.
- [ ] **Step 4: Run to verify GREEN** — `cd frontend && npm run test -- "new-game/StaffHiringStep" && npm run build && npm run lint`. Expected: PASS + clean.
- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/new-game/StaffHiringStep.tsx frontend/src/components/new-game/StaffHiringStep.module.css frontend/src/components/new-game/StaffHiringStep.test.tsx
git commit -m "feat(new-game): reskin StaffHiringStep to tokens; fix off-screen footer (#77/#78 preserved)"
```

---

### Task 7: StartingRecruitmentStep reskin (#22,#80,#81) + name-overflow + scroll fix

**Files:** create `StartingRecruitmentStep.module.css`; modify `StartingRecruitmentStep.tsx`.

**Inline styles to migrate + layout bugs to fix (StartingRecruitmentStep.tsx):** wrapper (`:112`); header + intro copy (`:114–125`); composition guide (`:128–213`) → `.guide` + Foundation chips (`:154–172`, audit §3 "flex 1 1 0 minWidth 100px wrap unevenly") → `.foundationChip` with token `min-width` + the met/unmet tone via `.chipMet`/`.chipUnmet` (KEEP `id="composition-guide"` / `id="composition-warning"` / `title` tips); load-error + loading copy (`:216–223`); **`maxHeight:'360px'` scroll (`:225` — audit §3 "high")** → `.prospectScroll` token-bounded (`min(360px, 50vh)`); prospect rows (`:243–256`) → `.prospectRow`/`.prospectRowSelected` (KEEP `role="checkbox"` + `aria-checked` + `aria-label`); **prospect name `whiteSpace:'nowrap'` with no `textOverflow` (`:260` — audit §3 "forces row wider, clips OVR")** → `.prospectName` using the Phase-0 `Truncate` pattern (`overflow:hidden; text-overflow:ellipsis; min-width:0`); the unfogged ratings strip (`:284–300`) and ceiling block (`:302–321`) → token classes (KEEP all six rating cells + `Ceil`/`OVR` — the #22 unfogged contract); action row + helper copy (`:331–349`).

> **#22 / #80 / #81 logic is load-bearing — copy verbatim:** `toggleProspect` (`:73–80`, the `next.size < 10` cap), `compositionTally` (`:83–93`), `hasImbalance` (`:95–98`), `needed`/`rosterReady`/`rosterFull`/`rosterHelp` (`:100–109`), `canSelect = selected || rosterIds.size < 10` (`:228`), Commit disable/label (`:334–341`). The reskin changes only the styling substrate. `TermTip`/`CeilingGrade` render unchanged (frozen legibility).

- [ ] **Step 1: Add RED guards** to `StartingRecruitmentStep.test.tsx` for the two layout fixes:

```tsx
it('bounds the prospect list scroll via a class, not an inline 360px height', async () => {
  await loaded();
  const region = screen.getByTestId('prospect-scroll');
  expect(region.style.maxHeight).toBe('');
});
it('truncates the prospect name (overflow guard) rather than forcing the row wide', async () => {
  await loaded();
  const name = screen.getByTestId('prospect-name-a');
  // jsdom does NOT compute CSS-Module class rules via getComputedStyle — that
  // API returns empty/default values for module-scoped declarations even with
  // css:true in vite.config.ts. Assert the module class is applied instead;
  // the visual text-overflow:ellipsis is guaranteed by the .prospectName rule
  // in the module CSS, which the integrator can verify via the token-clean scan.
  expect(name.className).toMatch(/prospectName/);
});
```
(Add `data-testid="prospect-scroll"` to the list container and `data-testid={`prospect-name-${p.player_id}`}` to each name span during the reskin.)

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "new-game/StartingRecruitmentStep"`. Expected: the two new cases FAIL; #22/#77/#80/#81 cases still PASS.
- [ ] **Step 3: Implement** — create `StartingRecruitmentStep.module.css` (token-only); rewrite markup to module classes; add the two scroll/name test hooks. Copy ALL logic verbatim. No raw hex/px.
- [ ] **Step 4: Run to verify GREEN** — `cd frontend && npm run test -- "new-game/StartingRecruitmentStep" && npm run build && npm run lint`. Expected: PASS + clean.
- [ ] **Step 5: Scoped token-cleanliness proof (do NOT modify the committed gate)** — run a one-off scan to prove `new-game/` carries no stray hex/px outside the `COLOR_PRESETS` data line, so the integrator can append the dir to `SCAN_DIRS` in STEP 3 cleanly:

```bash
cd frontend && node -e "import('node:fs').then(async fs=>{const {readFileSync}=fs;const g=await import('node:child_process');const files=g.execSync('git ls-files src/components/new-game').toString().split('\n').filter(f=>/\.(tsx|css)$/.test(f)&&!/\.test\./.test(f));const HEX=/#[0-9a-fA-F]{3,8}\b/;const PX=/(?<![\w.])(?!0px|1px)\d{1,4}px\b/;let bad=[];for(const f of files){readFileSync(f,'utf8').split('\n').forEach((l,i)=>{if(/COLOR_PRESETS|token-gate:/.test(l))return;if(/viewBox/.test(l))return;if(HEX.test(l)||PX.test(l))bad.push(f+':'+(i+1)+'  '+l.trim());});}if(bad.length){console.error('STRAY LITERALS:\n'+bad.join('\n'));process.exit(1);}console.log('new-game token-clean (COLOR_PRESETS data excepted)');})"
```
Expected: `new-game token-clean`. If it flags a line, replace that literal with a token (or, for a runtime kit color, the custom-property pattern) and re-run. **Do not edit `scripts/check-tokens.mjs`.**

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/new-game/StartingRecruitmentStep.tsx frontend/src/components/new-game/StartingRecruitmentStep.module.css frontend/src/components/new-game/StartingRecruitmentStep.test.tsx
git commit -m "feat(new-game): reskin StartingRecruitmentStep to tokens; fix name overflow + off-screen scroll (#22/#80/#81 preserved)"
```

---

## Phase 7C — Phase gate

### Task 8: Full Phase-7 worktree gate

- [ ] **Step 1: Run the complete per-phase gate** (OLD `index.css` still present in the worktree; integrator runs the deletion + full `tsc`/vitest later):

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e   # smoke (the Build-From-Scratch flow if the e2e suite reaches it)
```
Expected: all FE tests pass (the 4 new-game test files + the rest of the suite); build clean; eslint clean; `lint:tokens` clean (unchanged scope — `new-game/` not yet in `SCAN_DIRS`, by design); e2e smoke green.

- [ ] **Step 2: Manual smoke (the wizard still creates a club)** — launch the app, open SaveMenu → Build From Scratch, walk all 4 steps: collision banner fires on a dup save name, archetype radios toggle, staff defaults + over-budget block, roster 6..10 bound + 11th refusal, Commit creates the career. Confirm the chosen kit colors paint the IdentityStep preview. (Frontend has no red-green runner for visuals; this manual proof + the vitests are the evidence — per the project's frontend-verification policy.)

- [ ] **Step 3: Handoff note for the integrator (no commit of gate files)** — in the merge note, record: (a) `new-game/` is token-clean except the `COLOR_PRESETS` data array + the `// token-gate:` marker line — append `src/components/new-game` to `SCAN_DIRS` and add an `ALLOW_LINE`/`ALLOW_FILE` carve-out for the `COLOR_PRESETS` line if the gate flags it; (b) the legacy `index.css` selector families now safe to remove (no longer referenced by `new-game/*`): the wizard's usages of `.dm-kicker`, `.dm-helper-copy`, `.dm-helper-copy-warning`, `.dm-badge`, `.dm-badge-slate`, `.dm-data` were migrated to module CSS — but **only delete those globals if NO other on-trunk consumer remains** (grep-zero gate; they are likely shared, so probably NOT deletable in this phase's slice). Do NOT delete `.dm-action*` (the `ActionButton` shim still emits those classes until Phase 8).

> **Do NOT commit a gate-marker empty commit and do NOT merge.** The controller merges this worktree branch in STEP 3.

---

## Self-Review

**Behavior coverage (audit §2 Phase-7 set = #22, #76–#81):**
- #76 save-name collision banner up front → Task 1 (lock) + Task 4 (preserve through reskin) ✓ (asserts `role="alert"` + `data-testid="save-name-collision-banner"` + Next-disable + `aria-invalid`)
- #77 seed continuity (fetch seed === passed seed) → Task 2 (staff + recruitment fetch-with-seed assertions) ✓ — the SaveMenu-side `root_seed` POST equality stays Phase 1's (out of scope, noted)
- #78 staff no-soft-lock (cheapest default + over-budget block) → Task 2 (lock) + Task 6 (preserve) ✓
- #79 empty `{}` staff_choices omitted → **out of scope** (SaveMenu.tsx:256 owns the POST); the step-side corollary (default keeps `choices` non-empty) is exercised by Task 2's "#78 defaults every department" ✓ — explicitly flagged so the controller knows #79's POST guard is Phase 1's, not silently dropped
- #80 role-coverage tally advisory-only → Task 2 (lock) + Task 7 (preserve) ✓
- #81 roster bounded 6..10 + hard 11th-cap refusal → Task 2 (lock, both the ≥6 bound AND the 11th-row non-toggle) + Task 7 (preserve) ✓
- #22 founding-class prospects UNFOGGED → Task 2 (asserts ACC/IQ ratings + numeric Ceil on the row) + Task 7 (preserve the full ratings strip + ceiling block) ✓

**Contracts consumed (Phase-1 / Phase-0 frozen signatures):**
- Phase-1 `src/ui` `ActionButton` shim (signature-identical, keeps `dm-action` classes; import path `../../ui`) — Task 3 ✓
- Phase-0 `saveApi.startingStaff(seed)` / `saveApi.startingProspects(seed)` (consume, no raw fetch) — Tasks 2, 6, 7 ✓
- Frozen `legibility` `TermTip` / `CeilingGrade` / `TermId` (read-only) — rendered unchanged in Task 7 ✓
- Frozen step **prop interfaces** (SaveMenu call sites `SaveMenu.tsx:960–963`) — never altered ✓

**Hard-rule encoding check:** SaveMenu.tsx untouched (rule stated in every relevant task) ✓; no `index.css` edits/deletions (only `*.module.css` created; STEP-3 deletion deferred + handoff-noted) ✓; no `ui.tsx` edits, no `ActionButton→ActionBar` remap (Task 3 explicit) ✓; `check-tokens.mjs` untouched (Task 7 uses a one-off inline scan, not a gate edit; integrator owns `SCAN_DIRS`) ✓; runtime club-color trap resolved via custom properties + `COLOR_PRESETS`-as-data marker (Task 4) ✓; all `data-*`/`role`/`aria` hooks enumerated + asserted as HARD RED preconditions before any markup change (Tasks 1, 2) ✓.

**Placeholder scan:** none — every task has concrete file paths (verified against the live tree), real test code with grounded fixtures (`StaffCandidate`/`ProspectOption` fields copied from `types.ts:1772–1816`), and exact source line numbers from the current components.

**Type / name consistency:** step prop names (`identity/setIdentity/onNext/onBack/takenNames`, `coach/setCoach`, `seed/choices/setChoices`, `seed/onCommit/onBack/creating`) match the live components AND SaveMenu's call sites exactly; `data-testid` strings (`save-name-collision-banner`, `staff-budget-bar`, `staff-candidate-card`) match the source verbatim; new test-only hooks (`identity-preview`, `staff-dept-scroll`, `prospect-scroll`, `prospect-name-<id>`) are introduced in the same task that asserts them; `saveApi.startingStaff/startingProspects` signatures match `api/client.ts` (single-arg `seed: number`); `StartingStaffResponse`/`ProspectOption` fixtures match `types.ts`.

**Gaps found + fixed during review pass:**

1. *lint:tokens gate scope* — the per-phase gate does NOT cover `new-game/` (Phase-0 `SCAN_DIRS` is `src/ui` + `src/styles` only), so a raw hex in a wizard module would slip the gate. Fixed by (a) requiring token-only CSS from the start in every reskin task, and (b) adding Task 7 Step 5's one-off scoped scan (which does NOT modify the committed gate, honoring the "integrator owns SCAN_DIRS" freeze) to prove cleanliness before handoff.

2. *CJS `require('react')` in ESM context (BLOCKER)* — Task 2 `Harness` originally called `(require('react') as ...).useState` inside a JSX component body. This is a CJS call inside a Vite 8 / Vitest ESM module and will fail to parse/transform before any test runs. Fixed: replaced with a top-level `import { useState } from 'react'` (now the authoritative code); the fallback note removed.

3. *`ActionButton` shim pre-condition not enforced (MAJOR)* — Task 3 re-points imports to `src/ui`, but `src/ui/index.ts` does NOT export `ActionButton` until Phase 1 merges. Added an explicit `grep` guard step at the top of Task 3 that halts the worker if the export is absent, enforcing the merge-strict 7→1 edge in executable form.

4. *`getComputedStyle` unreliable for CSS Module rules in jsdom (MAJOR)* — Task 7's prospect-name overflow guard originally asserted `getComputedStyle(name).textOverflow === 'ellipsis'` as primary. jsdom does not compute CSS Module rules via `getComputedStyle`, so this always fails for the wrong reason. Fixed: primary assertion is now `name.className.match(/prospectName/)` (module class applied); the jsdom limitation is documented in a comment.

5. *`#80` role-coverage test used aria-label regex keyed to `formatPlayerName` output (MAJOR)* — the pattern `new RegExp('Player ${id},')` couples the test to `formatPlayerName`'s string format. Although `formatPlayerName` currently returns `p.name` verbatim, this is fragile. Fixed: replaced with index-based `rows[i]` selection (order-stable per the POOL fixture) and removed the aria-label regex lookup.

6. *Task 1 note credited `title` as the accessible name source for preset buttons (MINOR)* — the actual accessible name comes from the visible label span text inside the button, not the `title` attribute. Updated the Step 2 note accordingly. No assertion change needed (the assertion was correct).

7. *Task 4 guard test setup intent not documented (MINOR)* — the preview block conditionally renders only when `club_name || city` is truthy; the guard test setup was intentional but undocumented, making it look like accidental fixture over-specification. Added a one-line comment in the test noting the conditional render dependency.
