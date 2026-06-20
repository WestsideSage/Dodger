# Floodlight Phase 5 — Dynasty Office + Recruiting + History (Record Room) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the Dynasty Office shell + Recruit subtab (CredibilityStrip, ProspectCard, RecruitingBadge), the History subtab (HistorySubTab, MyProgramView, LeagueView, BannerShelf, AlumniLineage, ProgramModal), and introduce the cream + ink Fraunces **"Record Room"** legacy mode (§3.8) — onto the Floodlight token system using CSS Modules, while keeping the 19 assigned trust behaviors (#19–#28, #30, #59–#66, #97) green and consuming the Phase-1 frozen contracts. This is one of six concurrent STEP-2 lanes; it runs in an **isolated git worktree branched from the merged post-Phase-1 trunk** and ships its `*.module.css` + rewired components + vitests. The serial integrator deletes legacy `index.css` selector families later (STEP 3).

**Architecture:** Dynasty/recruiting/history components move from `index.css` global classes (`.do-*`, `.dm-badge*`) + inline-style objects + literal hex to scoped `*.module.css` driven by `src/styles/tokens.css`. The live Recruit surfaces stay in the warm-graphite Floodlight palette. The **History/Record Room** surfaces (MyProgramView, LeagueView, BannerShelf, AlumniLineage, ProgramModal) adopt the cream/ink/Fraunces **legacy tokens already present in `tokens.css`** (`--legacy-paper`, `--legacy-ink`, `--legacy-brick`, `--font-serif`) — strictly quarantined to history/records, never warming live UI. `ProgramModal`'s frozen public signature `{ clubId, clubName, onClose }` (consumed by P4's LeagueContext + this phase's LeagueView) is preserved exactly. The five orphan `ui.tsx` primitives consumed here (`StatusMessage`) are re-pointed to the Phase-1 `src/ui` shims (import-path change only). `command-policy-overlay` (the shared global ProgramModal wraps via `Dialog`) **survives untouched** this phase.

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (Phase-0 harness).

**Spec:** [2026-06-19-ui-redesign-design.md](../specs/2026-06-19-ui-redesign-design.md) §3.2 color contract, §3.3 type, §3.8 Record Room, §4 primitives · **Non-regression contract:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md) §1 (Dynasty office + history; recruiting rows), §2.C #19–#28/#30, §2.H #59–#66, §2.J #97, §3 P2/P3/P7 (overflow/fixed-grid/tiny-font) on these screens · **Checklist:** [floodlight-preservation-checklist.md](floodlight-preservation-checklist.md) Phase 5 row (#19–#28, #30, #59–#66, #97) · **Orchestration contract:** [2026-06-19-floodlight-parallelization-strategy.md](2026-06-19-floodlight-parallelization-strategy.md) STEP 2 concurrent window, freezes table · **Foundations + style template:** [2026-06-19-floodlight-phase-0-foundations.md](2026-06-19-floodlight-phase-0-foundations.md) · **Phase-1 contracts consumed:** [2026-06-19-floodlight-phase-1-app-shell.md](2026-06-19-floodlight-phase-1-app-shell.md)

**Branch:** isolated worktree off the **merged post-Phase-1 trunk** (controller creates it). All Phase-5 commits land on that branch. Do NOT merge — the controller integrates.

---

## Orchestration contract — what this phase MUST honor (hard rules)

These are non-negotiable, encoded as explicit per-task constraints below. A reviewer must be able to verify each by grep.

1. **NO `index.css` edits or deletions.** CREATE `*.module.css` only. The legacy `.do-*` / `.dm-badge*` / `.do-hist-*` / `.do-recruit*` / `.do-cred*` selector families are removed later by the serial integrator (STEP 3). This plan contains **zero** `index.css` deletion tasks. New components stop *consuming* the legacy classes (so the integrator's later deletion is safe), but the file itself is not touched here.
2. **NO edits to `components/ui.tsx`.** Re-point imports of `StatusMessage` (the only `ui.tsx` orphan-shim primitive used on these screens) from `'../ui'` / `'../../ui'` to the Phase-1 `src/ui` shims. **Import-path change ONLY. No `ActionButton→ActionBar` remap** (deferred to P8). `Dialog` stays imported from `components/ui` (it is NOT one of the five shimmed primitives and is not relocated this phase).
3. **FROZEN — consume, never alter:**
   - `dynasty/history/ProgramModal.tsx` **public signature** `{ clubId, clubName, onClose }` (P4 LeagueContext imports it; this phase's LeagueView imports it). The Phase-1 contract test `ProgramModal.contract.test.tsx` guards it — keep it green.
   - `components/match-week/matchResult.ts` public API — not imported by Phase-5 files, but never relocate/alter if a refactor tempts it.
   - `legibility/*` primitives (`TermTip`, `ProofChip`, `KnownValue`, `CeilingGrade`, `PipelineEmblem`, `EmptyState`) — **read-only**, accept mixed Floodlight+legacy look until P8. Keep importing them as-is; do not reskin or relocate.
   - `frontend/scripts/check-tokens.mjs` — **untouched**; the integrator owns all `SCAN_DIRS` appends.
4. **SHARED globals SURVIVE — never delete this phase:** `command-policy-overlay` (ProgramModal passes `className="command-policy-overlay"` + `panelClassName="command-policy-overlay-body do-hist-modal-body"` into `Dialog`) and `command-action-bar`. These are P8-deletion-gated. ProgramModal keeps the `command-policy-overlay` overlay class; only the *body* presentation moves to a module.
5. **Consume Phase-1 published contracts** where relevant: `components/shell/appContracts.ts` is not directly imported by dynasty screens, but the **frozen ProgramModal signature** is the contract this phase is bound by. P4's `standings/PlayoffBracket` is unrelated here.
6. **`data-*` anti-strip vitests are HARD RED preconditions.** The provenance hook on Phase-5 screens is **`data-testid="prospect-card-locked"`** (ProspectCard's beyond-network locked variant) plus the family of dynasty/history test ids (`prospect-card`, `prospect-motivations`, `prospect-rivals`, `prospect-promise-chip`, `treasury-chip`, `promises-panel`, `recruiting-badge-${status}`). Every rebuild keeps its hooks; the anti-strip vitest is written BEFORE the reskin. (No `data-broadcast-proof-source` / `data-player-outcome` / `recap-missed-playoffs` / `worlds_user` / `save-name-collision-banner` hooks live on Phase-5 screens — those belong to P2/P6/P7. The one Phase-5 anti-strip target is `prospect-card-locked`, enumerated in Task 4.)
7. **Record Room uses the legacy cream/ink tokens already in `tokens.css`** (`--legacy-paper #F3EBD8`, `--legacy-ink #211C16`, `--legacy-brick #B4452F`, `--font-serif 'Fraunces'`). No new color literals; quarantine to `history/*.module.css`.
8. **#97 `isSelf` gates self-only copy** ("My Program" label, "Your first alumni…", "Next banner" placeholder) — ProgramModal forces `isSelf=false`; preserve verbatim.
9. **AlumniLineage stale tier map** (`Elite/High/Limited/Solid/Unknown`) must be re-pointed to `src/domain/tiers.ts` (`Elite/High/Mid/Low/Raw`) — see Task 9 (#26 vocabulary de-collision; current map silently mismatches the rendered potential vocabulary).

---

## Per-phase gate (runs in the worktree with the OLD `index.css` still present)

Unless a task says otherwise, every task ends green on:

```bash
cd frontend && npm run test -- <the task's test files> && npm run build && npm run lint
```

> `npm run lint:tokens` only scans the dirs in `SCAN_DIRS`. The integrator appends the Phase-5 dirs in STEP 3, so token violations in the new modules are caught at integration — **each reskin task must pre-empt them by using only `var(--…)` tokens (no raw hex, no raw px beyond `0`/`1px` hairlines) from the start**, both in the live-Floodlight modules and the Record-Room legacy modules (legacy uses `var(--legacy-*)` / `var(--font-serif)`, never a raw `#F3EBD8`).

The **Phase-5 worktree gate** (Task 12) additionally runs the full FE suite + build + lint + a token check on the Phase-5 dirs + an e2e smoke (the dynasty/history path is exercised by the existing root `tests/e2e/maximized-playthrough-qa.spec.ts`):

```bash
cd frontend && npm run test && npm run build && npm run lint
node scripts/check-tokens.mjs --extra src/components/dynasty   # local pre-check only; see Task 12 note
cd .. && npm run e2e -- tests/e2e/maximized-playthrough-qa.spec.ts
```

> **Token pre-check note (Task 12):** the committed `check-tokens.mjs` is frozen (integrator-owned). To self-verify token discipline in the worktree without editing it, run a **throwaway one-off** scan (a temporary local `--extra` arg or an ad-hoc node snippet over `src/components/dynasty/**`) and DISCARD it — never commit a `check-tokens.mjs` change. The plan's tasks each keep modules literal-free so this pre-check passes trivially.

---

## File map (created/modified in this plan)

**Created — anti-strip + behavior vitests (RED preconditions):**
- `frontend/src/components/dynasty/ProspectCard.test.tsx` (#23, #24, #30 anti-strip `prospect-card-locked`, #63, #64, #65)
- `frontend/src/components/dynasty/RecruitingBadge.test.tsx` (#64 monotonic display via status tone/label)
- `frontend/src/components/dynasty/CredibilityStrip.test.tsx` (#20, #59)
- `frontend/src/components/dynasty/history/MyProgramView.test.tsx` (#60, #97)
- `frontend/src/components/dynasty/history/LeagueView.test.tsx` (#35, #38, #66)
- `frontend/src/components/dynasty/history/BannerShelf.test.tsx` (#97 "Next banner" placeholder isSelf-gated)
- `frontend/src/components/dynasty/history/AlumniLineage.test.tsx` (#26 tier vocabulary via `tiers.ts`)
- `frontend/src/components/dynasty/HistorySubTab.test.tsx` (#97 "My Program" vs "Program" label) — NOTE: co-located with the source at `dynasty/`, NOT in `dynasty/history/`
- `frontend/src/components/dynasty/history/ProgramModal.test.tsx` (frozen signature + forces isSelf=false + keeps `command-policy-overlay`)

**Created — CSS Modules (live Floodlight):**
- `frontend/src/components/dynasty/DynastyOffice.module.css`
- `frontend/src/components/dynasty/CredibilityStrip.module.css`
- `frontend/src/components/dynasty/ProspectCard.module.css`
- `frontend/src/components/dynasty/RecruitingBadge.module.css`

**Created — CSS Modules (Record Room legacy / cream-ink-Fraunces):**
- `frontend/src/components/dynasty/history/recordRoom.module.css` (the shared Record-Room frame: paper surface, ink text, Fraunces headings, brick accents — imported by every history module)
- `frontend/src/components/dynasty/history/MyProgramView.module.css`
- `frontend/src/components/dynasty/history/LeagueView.module.css`
- `frontend/src/components/dynasty/history/BannerShelf.module.css`
- `frontend/src/components/dynasty/history/AlumniLineage.module.css`
- `frontend/src/components/dynasty/history/ProgramModal.module.css`
- `frontend/src/components/dynasty/history/HistorySubTab.module.css`

**Modified (reskin — markup→module classes; logic/signatures verbatim):**
- `frontend/src/components/DynastyOffice.tsx` (shell + recruit subtab body → module classes; re-point `StatusMessage` import to `src/ui`; History/recruit mount unchanged in structure)
- `frontend/src/components/dynasty/CredibilityStrip.tsx`
- `frontend/src/components/dynasty/ProspectCard.tsx`
- `frontend/src/components/dynasty/RecruitingBadge.tsx`
- `frontend/src/components/dynasty/history/HistorySubTab.tsx`
- `frontend/src/components/dynasty/history/MyProgramView.tsx` (re-point `StatusMessage` import to `src/ui`)
- `frontend/src/components/dynasty/history/LeagueView.tsx` (re-point `StatusMessage` import to `src/ui`)
- `frontend/src/components/dynasty/history/BannerShelf.tsx`
- `frontend/src/components/dynasty/history/AlumniLineage.tsx` (re-point tier map to `src/domain/tiers.ts`)
- `frontend/src/components/dynasty/history/ProgramModal.tsx` (body presentation → module; KEEP `Dialog` import + `command-policy-overlay` overlay class + frozen props)

**Frozen / not touched:** `components/ui.tsx`, `components/match-week/matchResult.ts`, `legibility/*`, `frontend/scripts/check-tokens.mjs`, `frontend/src/index.css` (no edits — integrator deletes legacy selectors in STEP 3), `frontend/src/domain/tiers.ts` (consumed, not edited), `frontend/src/components/dynasty/history/formatters.ts` (consumed verbatim — the centralized faithfulness formatters per §5.4).

---

## Behavior coverage map (audit §2 → task → test strategy)

| # | Behavior (short) | Task | Test strategy |
|---|---|---|---|
| 19 | Mechanical-vs-flavor badge (AFFECTS PLAY/FLAVOR) via TermTip/terms.ts kind | 5,6,7 | vitest — TermTip rendered, not reskinned; badge text preserved |
| 20 | Receipts/'why' rendered verbatim from backend evidence strings | 5,7 | vitest (CredibilityStrip evidence list verbatim; ProofChip source) |
| 21 | KnownValue three-state (known/estimated/hidden) survives | 6 | vitest (ProspectCard OVR KnownValue state from `scouted`) |
| 22 | Founding-class prospects shown UNFOGGED (wizard) | n/a-P7 | (StartingRecruitmentStep is Phase 7; no Phase-5 surface) — see note |
| 23 | Prospect OVR = scouted band vs verified FA OVR | 6 | vitest (band low–high from `public_ovr_band`, KnownValue estimated) |
| 24 | Dealbreaker (★) hidden until scouted; veto shows WON'T VERBAL | 6 | vitest (no `dealbreaker` → "scout to reveal"; veto → "WON'T VERBAL") |
| 25 | Tactical-Diff tape vs playbook vs unscouted | n/a-P2 | (PreSimDashboard is Phase 2) — see note |
| 26 | Vocabulary de-collision (pipeline / potential / ceiling) distinct sets | 9 | vitest (AlumniLineage tier map re-pointed to `tiers.ts` POTENTIAL_TIERS) |
| 27 | Ruleset display-name never leaks impl keys | n/a | (rulesetNames.ts not on Phase-5 surfaces) — see note |
| 28 | CeilingGrade never leaks tier/number; null on unknown | 6 | vitest (CeilingGrade rendered as-is; null grade renders nothing) |
| 30 | Proof-source provenance preserved on DOM (data-* + testid) | 4,6 | vitest anti-strip (`prospect-card-locked` + the dynasty testid family) |
| 59 | Credibility grade read from payload, never re-derived | 7 | vitest (grade comes from `credibility.grade` prop) |
| 60 | All-Time vs Latest-Season label branches on `hero.all_time` | 8 | vitest (all_time present → "All-Time Record"; absent → "Latest Season Record") |
| 61 | Promise resolution KEPT/VOIDED/BROKEN; void no manager blame | 6 | vitest (ProspectCard promise chip label states) |
| 62 | Roster-promises "first season"; contender_path grades regardless | 6 | vitest (PROMISE_TYPE_LABELS preserved) |
| 63 | Name-only/out-of-reach prospects no scoutable data, sink, excluded from At-Risk | 4,6,10 | vitest (locked card renders no fit/meter; sort sink; At-Risk count excludes `fully_visible===false`) |
| 64 | Optimistic recruiting status never regresses below server (monotonic) | 6 | vitest (displayStatus = max(optimistic, server) precedence) |
| 65 | Refused recruiting actions unmistakable + "action not spent" + refetch | 6 | vitest (rejected action → "action not spent" + `onAction` called) |
| 66 | Record/HoF rows use persisted holder display name, not humanized id | 8 | vitest (LeagueView record uses `record.holder_name` when present) |
| 97 | isSelf gates self-only copy + 'Next banner' placeholder | 8,11 | vitest (HistorySubTab label, BannerShelf placeholder, ProgramModal isSelf=false) |

**Notes on #22/#25/#27 (assigned to Phase 5 in the checklist but their surfaces live in other phases):** The checklist line for Phase 5 lists `#19–#28`. Within that range, **#22** (founding-class unfogged) is on `new-game/StartingRecruitmentStep.tsx` (Phase 7), **#25** (Tactical-Diff intel source) is on `command-center/PreSimDashboard.tsx` (Phase 2), and **#27** (ruleset name normalization) is on `rulesetNames.ts` consumers (SaveMenu/MatchReplay — Phases 1/2). **None of these three files is a Phase-5 screen.** Phase 5 must NOT reskin them. They are covered by their owning phase's plan; this plan records them here only to make the range-gap explicit and prevent an accidental cross-phase edit. The reviewer should confirm Phase 5 touches none of those files.

---

## Task 1: Capture the Phase-5 frozen-signature + anti-strip baseline (RED-first guard)

> **Why:** Before any reskin, lock the two cross-phase invariants this lane is bound by: (a) `ProgramModal`'s frozen public signature `{ clubId, clubName, onClose }` (P4 + LeagueView import it), and (b) that ProgramModal still wraps the SHARED `command-policy-overlay` global and forces `isSelf=false`. These pass immediately on current code; they are tripwires that fail if a later reskin step drifts the contract.

**Audit numbers:** #97 (ProgramModal forces isSelf=false), frozen-signature orchestration rule.

**Files:** create `frontend/src/components/dynasty/history/ProgramModal.test.tsx`.

- [ ] **Step 1: Write the guard test**

```tsx
// frontend/src/components/dynasty/history/ProgramModal.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, expectTypeOf, vi } from 'vitest';
import type { ComponentProps } from 'react';
import { ProgramModal } from './ProgramModal';

// MyProgramView fetches; stub it so this test exercises ONLY the modal frame.
vi.mock('./MyProgramView', () => ({
  MyProgramView: ({ isSelf }: { clubId: string; isSelf?: boolean }) => (
    <div data-testid="stub-myprogram" data-is-self={String(isSelf)} />
  ),
}));

describe('ProgramModal (P5-owned, P4-consumed — frozen contract)', () => {
  it('accepts exactly { clubId, clubName, onClose }', () => {
    expectTypeOf<ComponentProps<typeof ProgramModal>>()
      .toEqualTypeOf<{ clubId: string; clubName: string; onClose: () => void }>();
  });

  it('renders a labelled dialog with the club name and forces isSelf=false (#97)', () => {
    render(<ProgramModal clubId="hammers" clubName="Granite City Hammers" onClose={() => {}} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Granite City Hammers')).toBeInTheDocument();
    expect(screen.getByTestId('stub-myprogram')).toHaveAttribute('data-is-self', 'false');
  });

  it('keeps the SHARED command-policy-overlay global on the overlay (must survive this phase)', () => {
    const { container } = render(
      <ProgramModal clubId="hammers" clubName="Granite City Hammers" onClose={() => {}} />,
    );
    expect(container.querySelector('.command-policy-overlay')).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "ProgramModal"`. Expected: **PASS immediately** against current code (signature + isSelf=false + overlay class all already true). If any FAILS, the on-trunk code differs from the orchestration contract — STOP and reconcile with the controller before editing.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dynasty/history/ProgramModal.test.tsx
git commit -m "test(dynasty): freeze ProgramModal signature + isSelf=false + shared overlay survival (P5 contract)"
```

---

## Task 2: Re-point `StatusMessage` imports to the Phase-1 `src/ui` shims (import path only)

> **Why:** Orchestration rule 2: no `ui.tsx` edits during the window; consumers re-point to the signature-identical Phase-1 `src/ui` shims. `StatusMessage` is the only shimmed primitive used by Phase-5 files (`DynastyOffice.tsx`, `MyProgramView.tsx`, `LeagueView.tsx`). `Dialog` is NOT one of the five shims — it stays imported from `components/ui`. This is a pure import-path change; **no markup, no `ActionButton→ActionBar` remap, no logic change.**

**Files:** modify `frontend/src/components/DynastyOffice.tsx`, `frontend/src/components/dynasty/history/MyProgramView.tsx`, `frontend/src/components/dynasty/history/LeagueView.tsx`.

- [ ] **Step 0: Verify Phase-1 shims are merged to trunk (PREREQUISITE)**

  ```bash
  grep 'StatusMessage' frontend/src/ui/index.ts || (echo 'STOP: Phase-1 Task 1 (Step 1A shims — ActionButton, PageHeader, StatusMessage, RatingBar, RadioGroup) has not been merged to trunk yet. This task cannot proceed until it is.' && exit 1)
  ```

  **Expected:** the grep prints a line containing `StatusMessage`. If it returns nothing and exits 1, halt and notify the controller — Phase-1 must be merged before Task 2 runs. The current `frontend/src/ui/index.ts` (Phase-0 barrel) exports only: Truncate, Surface/Card, Grid, ScrollRegion, Tag/TagTone, RecordCell, Popover, Modal, ActionBar, Table. The five Phase-1A shims (ActionButton, PageHeader, StatusMessage, RatingBar, RadioGroup) are absent until Phase-1 lands on trunk. Proceeding without them causes a build failure at Step 3.

- [ ] **Step 1: Confirm current imports** (already verified):
  - `DynastyOffice.tsx:4` → `import { StatusMessage, Dialog } from './ui';`
  - `MyProgramView.tsx:3` → `import { StatusMessage } from '../../ui';`
  - `LeagueView.tsx:3` → `import { StatusMessage } from '../../ui';`

- [ ] **Step 2: Re-point ONLY `StatusMessage`** to the new `src/ui` barrel, leaving `Dialog` on `components/ui`:
  - In `DynastyOffice.tsx`: split into `import { Dialog } from './ui';` + `import { StatusMessage } from '../ui';` (the Phase-1 shim barrel is `frontend/src/ui/index.ts`, i.e. `../ui` relative to `src/components/`).
  - In `MyProgramView.tsx`: change `import { StatusMessage } from '../../ui';` → `import { StatusMessage } from '../../../ui';` (relative to `src/components/dynasty/history/`).
  - In `LeagueView.tsx`: same change as MyProgramView (`'../../ui'` → `'../../../ui'`).

  > Verify the relative depth by counting dirs: `src/components/X.tsx` → `src/ui` is `../ui`; `src/components/dynasty/history/X.tsx` → `src/ui` is `../../../ui`. The `src/ui/index.ts` shim barrel exports `StatusMessage` (Phase-1 Task 1, Step 5). Do not touch `components/ui.tsx`.

- [ ] **Step 3: Verify build + the Task-1 guard still passes** — `cd frontend && npm run build && npm run test -- "ProgramModal"`. Expected: build green (shim is signature-identical), guard still green.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DynastyOffice.tsx frontend/src/components/dynasty/history/MyProgramView.tsx frontend/src/components/dynasty/history/LeagueView.tsx
git commit -m "refactor(dynasty): re-point StatusMessage to src/ui shim (no ui.tsx edit, Dialog unchanged)"
```

---

## Task 3: RecruitingBadge — module reskin + monotonic-display guard (#64)

> **Why:** `RecruitingBadge` is the smallest leaf; reskinning it first proves the module pattern and locks the status label/tone mapping (#64 monotonic display is enforced upstream in ProspectCard, but the badge is the rendered surface). It currently uses global `dm-badge dm-badge-*` classes + an inline `style={{opacity}}` for pending. Move tone/pending to a module; preserve `data-testid="recruiting-badge-${status}"`, `aria-label`, `title` verbatim.

**Audit numbers:** #64 vitest (the badge faithfully renders the resolved status — its label/aria are the monotonic-display surface).

**Files:** create `frontend/src/components/dynasty/RecruitingBadge.test.tsx`, `frontend/src/components/dynasty/RecruitingBadge.module.css`; modify `frontend/src/components/dynasty/RecruitingBadge.tsx`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/dynasty/RecruitingBadge.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RecruitingBadge } from './RecruitingBadge';

describe('RecruitingBadge', () => {
  it('renders the human label + provenance testid + aria for a status', () => {
    render(<RecruitingBadge status="INTERESTED" />);
    const el = screen.getByTestId('recruiting-badge-INTERESTED');
    expect(el).toHaveTextContent('Interested');
    expect(el).toHaveAttribute('aria-label', 'Recruiting status: Interested');
  });
  it('marks the pending (saving) state in the aria-label and appends an ellipsis', () => {
    render(<RecruitingBadge status="SCOUTED" pending />);
    const el = screen.getByTestId('recruiting-badge-SCOUTED');
    expect(el).toHaveAttribute('aria-label', 'Recruiting status: Scouted (saving)');
    expect(el).toHaveTextContent('Scouted…');
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "RecruitingBadge"`. Expected: FAIL (no `data-testid` survives only if reskin keeps it — but the test is RED first because the module/file change is pending; if it passes against current code that is fine, it then becomes a regression guard for the reskin). *(This is a behavior-lock test; it may pass on current markup. That is acceptable — Step 4 must keep it green after the reskin.)*

- [ ] **Step 3: Implement the module + reskin** — create `RecruitingBadge.module.css` with a `.badge` base (token padding/radius/font, legibility floor `0.7rem`) and per-status tone classes (`.toneScouted` etc.) using the 5-color contract: live/interested → `--ok`, locked-out → `--out` (losses get darkness not red, §3.2), neutral/unscouted → `--text2`. Add a `.pending` class (dim via `color`/`opacity` token-free). In `RecruitingBadge.tsx`, replace `className={`dm-badge ${tone}`}` with `className={`${styles.badge} ${styles[toneClass]} ${pending ? styles.pending : ''}`.trim()}` and drop the inline `style={{opacity}}`. **Keep `data-testid`, `aria-label`, `title`, and the `label`/`…` text verbatim.** Map each `RecruitingStatus` to a module tone class via a small `Record<RecruitingStatus, string>`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "RecruitingBadge" && npm run build`. Expected: PASS + build green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/RecruitingBadge.*
git commit -m "feat(dynasty): RecruitingBadge to CSS Module (tokens; testid/aria preserved) (#64)"
```

---

## Task 4: ProspectCard anti-strip preconditions — `prospect-card-locked` + testid family (#30, #63)

> **Why:** ProspectCard carries the phase's load-bearing provenance hook **`data-testid="prospect-card-locked"`** (the beyond-Scouting-Network "name without a sheet" variant, #63) plus `prospect-card`, `prospect-motivations`, `prospect-rivals`, `prospect-promise-chip`. Per orchestration rule 6 these anti-strip vitests are **HARD RED preconditions** authored BEFORE the reskin. They assert the locked card renders the name + hometown + reach ONLY (no fit meter, no scoutable data) and the hook survives.

**Audit numbers:** #30 (proof/test attribute survives), #63 (locked card = no scoutable data).

**Files:** create `frontend/src/components/dynasty/ProspectCard.test.tsx`.

- [ ] **Step 1: Write the anti-strip + locked-card tests** (RED precondition). Build a minimal prospect fixture matching `DynastyOfficeResponse['recruiting']['prospects'][number]` — read the exact field names from `types.ts` before writing; do not invent fields. The fixture below uses only fields the component reads.

```tsx
// frontend/src/components/dynasty/ProspectCard.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProspectCard } from './ProspectCard';
import type { DynastyOfficeResponse } from '../../types';

type Prospect = DynastyOfficeResponse['recruiting']['prospects'][number];
type Budget = DynastyOfficeResponse['recruiting']['budget'];

// Shape verified against types.ts lines 1564-1567: Budget = { scout: [number, number]; contact: [number, number]; visit: [number, number] }.
// No `as Budget` cast — rely on TypeScript structural checking to catch field-name drift at compile time.
const budget: Budget = { scout: [0, 3], contact: [0, 2], visit: [0, 1] };

function baseProspect(overrides: Partial<Prospect> = {}): Prospect {
  return {
    player_id: 'p1',
    name: 'Dax Holloway',
    hometown: 'Granite City',
    public_archetype: 'Sharpshooter',
    public_ovr_band: [62, 71],
    fit_score: 84,
    interest: 40,
    scouted: false,
    pipeline_tier: 3,
    recruiting_status: 'UNSCOUTED',
    interest_evidence: [],
    motivations: [],
    fully_visible: true,
    ...overrides,
  } as Prospect;
}

describe('ProspectCard anti-strip + locked variant (#30, #63)', () => {
  it('beyond-network prospect renders the LOCKED variant with its provenance hook', () => {
    render(
      <ProspectCard
        prospect={baseProspect({ fully_visible: false, reach_band: 'NATIONAL', name: 'Kit Marsh', hometown: 'Far Harbor' })}
        budget={budget}
        onAction={() => {}}
        priority={5}
      />,
    );
    const locked = screen.getByTestId('prospect-card-locked');
    expect(locked).toBeInTheDocument();
    expect(locked).toHaveTextContent('Kit Marsh');
    expect(locked).toHaveTextContent('Far Harbor');
    // No scoutable data leaks: no fit meter / FIT score on a locked card.
    expect(screen.queryByTestId('prospect-card')).not.toBeInTheDocument();
    expect(screen.queryByText('FIT')).not.toBeInTheDocument();
  });

  it('a visible prospect renders the full card hook', () => {
    render(<ProspectCard prospect={baseProspect()} budget={budget} onAction={() => {}} priority={1} />);
    expect(screen.getByTestId('prospect-card')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "ProspectCard"`. Expected: PASS against current markup (the hooks exist today). This task **locks** them so Task 6's reskin cannot strip them. If a field name in the fixture mismatches `types.ts`, fix the fixture to the real shape (do not change the component).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dynasty/ProspectCard.test.tsx
git commit -m "test(dynasty): ProspectCard anti-strip — prospect-card-locked + full-card hooks (#30,#63)"
```

---

## Task 5: CredibilityStrip — behavior lock (#20, #59) then module reskin

> **Why:** CredibilityStrip is the Recruit subtab's hero. #59 (grade read from payload, never re-derived) and #20 (evidence rendered verbatim) are load-bearing. It currently uses `.do-cred*` global classes + inline `style={{left: pct%}}` tick positions + inline `width: fillPct%` fill (those % are LAYOUT MATH, an allowed token exception). Reskin to a module while keeping the verbatim evidence list and the payload-driven grade.

**Audit numbers:** #59 vitest (grade from `credibility.grade`), #20 vitest (evidence list verbatim).

**Files:** create `frontend/src/components/dynasty/CredibilityStrip.test.tsx`, `frontend/src/components/dynasty/CredibilityStrip.module.css`; modify `frontend/src/components/dynasty/CredibilityStrip.tsx`.

- [ ] **Step 1: Write the behavior-lock test**

```tsx
// frontend/src/components/dynasty/CredibilityStrip.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CredibilityStrip } from './CredibilityStrip';
import type { DynastyOfficeResponse } from '../../types';

type Cred = DynastyOfficeResponse['recruiting']['credibility'];

const credibility: Cred = {
  score: 72,
  grade: 'B',
  evidence: ['Won 8 of last 10 league games.', 'Developed 3 youth prospects past their ceiling.'],
} as Cred;

describe('CredibilityStrip (#59 payload grade, #20 verbatim evidence)', () => {
  it('shows the grade exactly from the payload, never re-derived', () => {
    render(<CredibilityStrip credibility={credibility} />);
    // grade 'B' is shown even though score 72 sits in the B bracket; the point is
    // it reads credibility.grade, not a local recomputation.
    expect(screen.getAllByText('B').length).toBeGreaterThan(0);
    expect(screen.getByText('72')).toBeInTheDocument();
  });
  it('renders every backend evidence string verbatim', () => {
    render(<CredibilityStrip credibility={credibility} />);
    expect(screen.getByText('Won 8 of last 10 league games.')).toBeInTheDocument();
    expect(screen.getByText('Developed 3 youth prospects past their ceiling.')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "CredibilityStrip"`. Expected: PASS on current markup (behavior-lock). Fix the fixture to the real `credibility` shape if a field mismatches.

- [ ] **Step 3: Implement the module + reskin** — create `CredibilityStrip.module.css`: `.cred` (Floodlight surface), `.letter`/`.tier` (the big grade — `--font-disp`, gold scaled per §3.5 talent glow, but credibility uses neutral/`--text` since it is reputation not ceiling — keep it `--text`/`--gold` per the existing amber halo intent), `.main`, `.kicker` (instrumentation all-caps `--font-ui`), `.title` (`--font-head`), `.blurb` (`--text2`), `.progress`/`.track`/`.fill`/`.marker`/`.tick`/`.evidence`/`.item`. Keep the inline `left: \`${pct}%\`` / `width: \`${fillPct}%\`` (LAYOUT MATH — allowed). Replace every `dm-kicker`/`do-cred*` class with `styles.*`. **TermTip stays imported from `legibility` and rendered as-is (frozen). Keep the `role="group"` + `aria-label` on the progress + each tick's `aria-label`.** No raw hex/px.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "CredibilityStrip" && npm run build`. Expected: PASS + build green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/CredibilityStrip.*
git commit -m "feat(dynasty): CredibilityStrip to CSS Module (#59 grade, #20 evidence preserved)"
```

---

## Task 6: ProspectCard — behavior lock (#21,#23,#24,#28,#61,#62,#64,#65) then module reskin

> **Why:** ProspectCard is the densest recruiting surface and carries the most behaviors. Its anti-strip hooks are already locked (Task 4). This task adds the **interaction/fog behavior tests** then reskins the heavy inline-style soup (literal hex `#64748b`/`#94a3b8`/`#34d399`/`#f59e0b`/`#f87171`, inline absolute feedback overlay, inline badge fonts — audit §3 P1/P2/P7) to a module. The `KnownValue`/`CeilingGrade`/`TermTip`/`PipelineEmblem`/`RecruitingBadge` children are preserved as-is; only ProspectCard's own chrome moves to tokens.

**Audit numbers:** #21 (KnownValue 3-state), #23 (band vs verified), #24 (dealbreaker hidden/veto), #28 (CeilingGrade null on unknown), #30 (hooks — already in Task 4), #61/#62 (promise chip states + labels), #64 (monotonic optimistic status), #65 (refused action "not spent" + refetch).

**Files:** create `frontend/src/components/dynasty/ProspectCard.module.css`; extend `frontend/src/components/dynasty/ProspectCard.test.tsx`; modify `frontend/src/components/dynasty/ProspectCard.tsx`.

- [ ] **Step 1: Add the failing/locking behavior tests** to `ProspectCard.test.tsx`:

```tsx
import userEvent from '@testing-library/user-event';
import { dynastyApi } from '../../api/client';

vi.mock('../../api/client', () => ({
  dynastyApi: {
    scoutProspect: vi.fn(),
    contactProspect: vi.fn(),
    visitProspect: vi.fn(),
    focusProspect: vi.fn(),
    makePromise: vi.fn(),
  },
}));

describe('ProspectCard fog + interaction behaviors', () => {
  it('#24: unscouted prospect hides the dealbreaker behind "scout to reveal"', () => {
    render(<ProspectCard prospect={baseProspect({ motivations: [{ motivation: 'x', label: 'Playing time', letter: 'A', receipt: 'r' }] })} budget={budget} onAction={() => {}} priority={1} />);
    expect(screen.getByText(/scout to reveal/i)).toBeInTheDocument();
    // Negative: the veto copy must NOT appear, and no dealbreaker label leaks through.
    expect(screen.queryByText(/WON'T VERBAL/)).not.toBeInTheDocument();
  });
  it('#24: a base prospect with empty motivations array renders no motivations block at all', () => {
    // When motivations is empty the entire block does not render (ProspectCard only
    // renders the motivations+dealbreaker section when motivations.length > 0).
    // This tightens the fog boundary: the dealbreaker cannot surface via empty-block leakage.
    render(<ProspectCard prospect={baseProspect()} budget={budget} onAction={() => {}} priority={1} />);
    expect(screen.queryByTestId('prospect-motivations')).not.toBeInTheDocument();
    expect(screen.queryByText(/WON'T VERBAL/)).not.toBeInTheDocument();
  });
  it('#24: a veto dealbreaker shows WON\'T VERBAL', () => {
    render(<ProspectCard prospect={baseProspect({ motivations: [{ motivation: 'x', label: 'P', letter: 'A', receipt: 'r' }], dealbreaker: { label: 'Wants a contender', letter: 'F', veto: true, receipt: 'r' } })} budget={budget} onAction={() => {}} priority={1} />);
    expect(screen.getByText(/WON'T VERBAL/)).toBeInTheDocument();
  });
  it('#23 + #21: OVR shows the scouted band via KnownValue (estimated when unscouted)', () => {
    render(<ProspectCard prospect={baseProspect({ public_ovr_band: [62, 71], scouted: false })} budget={budget} onAction={() => {}} priority={1} />);
    expect(screen.getByText('62–71')).toBeInTheDocument();
  });
  it('#65: a refused action says "action not spent" and still refetches the board', async () => {
    vi.mocked(dynastyApi.scoutProspect).mockRejectedValue(new Error('No scout slots'));
    const onAction = vi.fn();
    render(<ProspectCard prospect={baseProspect()} budget={budget} onAction={onAction} priority={1} />);
    await userEvent.click(screen.getByRole('button', { name: 'Scout' }));
    expect(await screen.findByText(/action not spent/i)).toBeInTheDocument();
    expect(onAction).toHaveBeenCalled();
  });
});
```

> **#64 monotonic note:** the monotonic-precedence logic (`displayStatus = optimistic only when it surpasses server`) is pure and already covered by the RecruitingBadge render + the precedence helper in ProspectCard. Add a focused assertion only if the reskin risks touching that branch — it must NOT (logic verbatim). Document that #64 is held by the unchanged `STATUS_PRECEDENCE`/`promoteStatus`/`displayStatus` block.

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "ProspectCard"`. Expected: the new cases PASS against current markup (behavior-lock). Reconcile any fixture field name to `types.ts`.

- [ ] **Step 3: Implement the module + reskin** — create `ProspectCard.module.css`. Classes: `.card` (+ `.fitStrong`/`.fitNeutral`/`.fitRisk` accent — use 5-color contract: strong → `--ok`, neutral → `--gold`, risk → `--out`, NOT red), `.locked` (dim but readable, ≥0.85 per §3.5), `.head`, `.id`, `.name` (Truncate-style ellipsis), `.sub`, `.fromLabel`/`.fromValue` (legibility floor ≥0.7rem — retire the `0.55rem`/`0.7rem` literals), `.fit`/`.fitValue`, `.meter`/`.meterBg`/`.meterFill` (fill `width:%` is LAYOUT MATH — allowed), `.evidence`, `.motivations`, `.feedback` (+ `.feedbackSuccess`/`.feedbackError` — replace the inline `rgba(16,185,129…)`/`rgba(244,63,94…)` with `--ok-soft`/`--volt-soft` token surfaces), `.actions`, `.btn`/`.btnPrimary`. Replace ALL inline `style={{...}}` literal-hex/px chrome with `className={styles.*}`. **Keep `data-testid` on both card variants, `data-testid="prospect-motivations"`/`prospect-rivals"`/`prospect-promise-chip"`, every `aria-label`/`title`, the `KnownValue`/`CeilingGrade`/`TermTip`/`PipelineEmblem`/`RecruitingBadge` children, the promise `<select>`, and ALL handler logic (runAction, focus, makePromise, the feedback timer cleanup) byte-for-byte.** The only allowed inline styles after reskin are the `width:`/`left:` percentage layout-math on the meter and tick. CeilingGrade renders only when `prospect.ceiling_label` truthy (its own null-on-unknown is #28, inside the frozen primitive).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "ProspectCard" && npm run build`. Expected: PASS + build green. The Task-4 anti-strip cases must still be green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/ProspectCard.*
git commit -m "feat(dynasty): ProspectCard to CSS Module (tokens; fog + hooks + handlers preserved) (#21,#23,#24,#28,#61,#62,#64,#65)"
```

---

## Task 7: DynastyOffice shell + Recruit subtab body → CSS Module

> **Why:** The shell (`do-shell`, `max-content`, the `DoTabs` bar, treasury chip `data-testid="treasury-chip"`, `promises-panel`, the recruit body grid `do-tab-content`/`do-grid-row`/`do-board*`) is global-class + inline-style (e.g. `style={{ padding: '0.85rem 1rem' }}` at line 265, `display:flex;gap:0.4rem` inline). Move DynastyOffice's own chrome to a module; the History mount and Recruit-subtab CHILD components are already (or being) reskinned in their own tasks. **#19 (mechanical-vs-flavor TermTip badges) and #20 (ProofChip receipts) survive because the legibility primitives are imported as-is and the badge text is preserved.**

**Audit numbers:** #19 (TermTip badge kinds preserved — rendered via frozen primitive), #63 (At-Risk count excludes `fully_visible===false` — logic verbatim; locked-card sink verbatim).

**Files:** create `frontend/src/components/dynasty/DynastyOffice.module.css`; modify `frontend/src/components/DynastyOffice.tsx`.

- [ ] **Step 1: Confirm the behavior tests already cover the load-bearing logic.** The At-Risk count (`prospects.filter(p => p.fully_visible !== false && (p.fit_score ?? 0) < 65)`, line 663) and the sort sink (`fully_visible === false ? 1 : 0`, lines 626/999) are PURE and must stay verbatim. Task 10 adds a focused vitest for the At-Risk exclusion (#63); this task is a presentation-only reskin and relies on the existing build + Task 10's guard. No new test file here — the reskin must not alter any filter/sort/handler.

- [ ] **Step 2: Implement the module + reskin** — create `DynastyOffice.module.css` with `.shell`, `.maxContent` (or keep `max-content` if it is a shared layout util — verify; if `max-content` is a global layout class shared with other phases, leave it and add a module wrapper), `.tabs`/`.tab`/`.tabActive`, `.treasuryChip`, `.tabContent`, `.gridRow`, `.boardHead`/`.boardFilter`/`.boardFilterActive`/`.boardMeta`/`.boardSortIndicator`, `.promisesPanel`, `.context`, `.slotMeter`, `.staffBrief`, `.scoutingNetwork`. Replace inline `style={{ padding: '0.85rem 1rem' }}` (line 265) and `style={{ display: 'flex', gap: '0.4rem' }}` (and similar) with module classes. Replace global `do-*` / `dm-panel` / `dm-kicker` on DynastyOffice-OWNED markup only (NOT on child components — those own their own modules). **Keep `data-testid="treasury-chip"`, `data-testid="promises-panel"`, `data-screen-label="03 Dynasty"`, every TermTip/ProofChip/EmptyState child, and ALL sort/filter/At-Risk/handler logic verbatim.** Re-point any remaining `StatusMessage` already done in Task 2. Legibility floor ≥0.7rem on all labels. No raw hex/px.

  > **Scope guard:** DynastyOffice.tsx is 1070 lines with many sub-components (DoTabs, PromisesPanel, RecruitingContext, SlotMeter, StaffBrief, ScoutingNetworkPanel, RecruitBoard, StaffTab, SettingsModal, plus the live Dialog usage). Reskin ONLY the Recruit-subtab + shell chrome and the sub-components that render in the Recruit/shell path. The **Staff subtab** (StaffTab, FacilitiesUpgradePanel, StaffMarketModal) is part of this phase's dynasty office but is NOT in the assigned behavior list — reskin its chrome to the module too (it shares `do-*` classes), but add NO new behavior tests for it (no assigned behaviors). Keep its handlers verbatim. `SettingsModal`/`Dialog` keep their `command-policy-overlay`-family classes if present (shared global — do not delete).

- [ ] **Step 3: Verify build + the recruit/history guards** — `cd frontend && npm run build && npm run test -- "ProspectCard" "CredibilityStrip" "RecruitingBadge" "ProgramModal"`. Expected: build green, all guards green.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DynastyOffice.* frontend/src/components/dynasty/DynastyOffice.module.css
git commit -m "feat(dynasty): DynastyOffice shell + recruit body to CSS Module (tokens; logic + hooks preserved) (#19,#63)"
```

---

## Task 8: LeagueView + MyProgramView behavior lock (#35,#38,#60,#66,#97) — RED-first

> **Why:** Before reskinning the history surfaces into the Record Room (Task 11), lock the truth behaviors: #60 (All-Time vs Latest-Season label branches on `hero.all_time`), #66 (record/HoF holder uses persisted display name not humanized id), #38 (Worlds roll only when worlds data exists; runner-up clause only when present), #35 (truthful empty states), #97 (isSelf self-only copy). These tests assert against the CURRENT markup so the cream/ink reskin must keep them green.

**Audit numbers:** #35, #38, #60, #66, #97.

**Files:** create `frontend/src/components/dynasty/history/MyProgramView.test.tsx` + `frontend/src/components/dynasty/history/LeagueView.test.tsx`.

- [ ] **Step 1: Write the MyProgramView test** — mock `useApiResource` to return controlled `ProgramData`.

```tsx
// frontend/src/components/dynasty/history/MyProgramView.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MyProgramView } from './MyProgramView';

const useApiResource = vi.fn();
vi.mock('../../../hooks/useApiResource', () => ({ useApiResource: (...a: unknown[]) => useApiResource(...a) }));

function programData(overrides: Record<string, unknown> = {}) {
  return {
    club_id: 'hammers',
    hero: {
      season_1: { season_label: 'season_1', wins: 6, losses: 4, draws: 0 },
      current: { season_label: 'season_3', wins: 1, losses: 0, draws: 0 },
      all_time: { wins: 18, losses: 10, draws: 2, seasons: 3 },
    },
    timeline: [],
    alumni: [],
    banners: [],
    ...overrides,
  };
}

describe('MyProgramView (#60 all-time label, #97 isSelf)', () => {
  it('#60: labels the record "All-Time Record" when hero.all_time is present', () => {
    useApiResource.mockReturnValue({ data: programData(), error: null, loading: false });
    render(<MyProgramView clubId="hammers" isSelf />);
    expect(screen.getByText('All-Time Record')).toBeInTheDocument();
    expect(screen.getByText('18-10-2')).toBeInTheDocument();
  });
  it('#60: falls back to "Latest Season Record" when all_time is absent', () => {
    const d = programData();
    delete (d.hero as Record<string, unknown>).all_time;
    useApiResource.mockReturnValue({ data: d, error: null, loading: false });
    render(<MyProgramView clubId="hammers" isSelf />);
    expect(screen.getByText('Latest Season Record')).toBeInTheDocument();
  });
  it('#97: shows "Your first alumni season is ahead" only when isSelf', () => {
    useApiResource.mockReturnValue({ data: programData(), error: null, loading: false });
    const { rerender } = render(<MyProgramView clubId="hammers" isSelf />);
    expect(screen.getByText(/Your first alumni season is ahead/)).toBeInTheDocument();
    rerender(<MyProgramView clubId="rivals" isSelf={false} />);
    expect(screen.getByText(/No departed players yet/)).toBeInTheDocument();
  });
}
);
```

- [ ] **Step 2: Write the LeagueView test** — mock `useApiResource` + stub `ProgramModal`.

```tsx
// frontend/src/components/dynasty/history/LeagueView.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { LeagueView } from './LeagueView';

const useApiResource = vi.fn();
vi.mock('../../../hooks/useApiResource', () => ({ useApiResource: (...a: unknown[]) => useApiResource(...a) }));
vi.mock('./ProgramModal', () => ({ ProgramModal: () => <div data-testid="stub-program-modal" /> }));

function leagueData(overrides: Record<string, unknown> = {}) {
  return {
    directory: [{ club_id: 'hammers', name: 'Granite City Hammers' }],
    dynasty_rankings: [],
    records: [{
      record_type: 'most_eliminations_season', holder_id: 'plr_zed_99', record_value: 41,
      set_in_season: 'season_2', record: { holder_name: 'Zed Calloway' },
    }],
    hof: [],
    rivalries: [],
    ...overrides,
  };
}

describe('LeagueView (#66 holder name, #38 worlds-gated, #35 empty states)', () => {
  it('#66: records use the persisted holder display name, not the humanized id', () => {
    useApiResource.mockReturnValue({ data: leagueData(), error: null, loading: false });
    render(<LeagueView />);
    expect(screen.getByText(/Zed Calloway/)).toBeInTheDocument();
    expect(screen.queryByText(/plr zed 99/i)).not.toBeInTheDocument();
  });
  it('#38: the World Championship roll renders only when worlds data exists', () => {
    useApiResource.mockReturnValue({ data: leagueData(), error: null, loading: false });
    const { rerender } = render(<LeagueView />);
    expect(screen.queryByText('World Championship')).not.toBeInTheDocument();
    rerender(<LeagueView />);
    useApiResource.mockReturnValue({
      data: leagueData({ worlds: [{ season_id: 'season_2', champion_club_id: 'hammers', champion_name: 'Granite City Hammers', runner_up_club_id: null, runner_up_name: null }] }),
      error: null, loading: false,
    });
    rerender(<LeagueView />);
    expect(screen.getByText('World Championship')).toBeInTheDocument();
  });
  it('#35 (LeagueView surface only): empty dynasty rankings show a truthful empty state, not a fabricated row', () => {
    // NOTE: #35 is PRIMARILY a Phase-6 behavior (ceremony / offseason empty states);
    // it is assigned to Phase 6 in the preservation checklist (Phase 6 row: #17,#18,#29,#31,#32,#35,#67–#75).
    // The assertion below is a DEFENSE-IN-DEPTH guard for the LeagueView surface only.
    // Phase 6 owns the full #35 contract; the Phase-6 implementer must NOT skip #35
    // on other surfaces just because this LeagueView assertion is green here.
    useApiResource.mockReturnValue({ data: leagueData(), error: null, loading: false });
    render(<LeagueView />);
    expect(screen.getByText(/No dynasty rankings yet/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run to verify behavior** — `cd frontend && npm run test -- "MyProgramView" "LeagueView"`. Expected: PASS against current markup (behavior-lock). Reconcile any field name to the real `ProgramData`/`LeagueData` interfaces in the source files if a mock key mismatches.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dynasty/history/MyProgramView.test.tsx frontend/src/components/dynasty/history/LeagueView.test.tsx
git commit -m "test(dynasty): lock history truth behaviors (#35,#38,#60,#66,#97) before Record Room reskin"
```

---

## Task 9: AlumniLineage — re-point stale tier map to `src/domain/tiers.ts` (#26) + module reskin

> **Why:** Orchestration rule 9 + audit #26: `AlumniLineage`'s `TIER_TONE` keys (`Elite/High/Limited/Solid/Unknown`) DO NOT match the canonical rendered potential vocabulary (`Elite/High/Mid/Low/Raw` in `src/domain/tiers.ts`). `Mid/Low/Raw` tiers silently fall to the `?? 'dm-badge-slate'` default — the de-collision (#26) is broken. Re-point the tone map to the canonical `POTENTIAL_TIERS` so every rendered tier has a distinct treatment, and move the badge to a Record-Room module.

**Audit numbers:** #26 vitest (tier vocabulary aligned to `tiers.ts`).

**Files:** create `frontend/src/components/dynasty/history/AlumniLineage.test.tsx`, `frontend/src/components/dynasty/history/AlumniLineage.module.css`; modify `frontend/src/components/dynasty/history/AlumniLineage.tsx`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/dynasty/history/AlumniLineage.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AlumniLineage } from './AlumniLineage';
import { POTENTIAL_TIERS } from '../../../domain/tiers';

const alum = (potential_tier: string) => ({
  id: `a-${potential_tier}`, name: `Player ${potential_tier}`, seasons_played: 4,
  career_elims: 120, championships: 1, ovr_final: 78, potential_tier,
});

describe('AlumniLineage tier vocabulary (#26)', () => {
  it('gives every canonical potential tier a DISTINCT tone class (no silent slate-bucket)', () => {
    const { container } = render(<AlumniLineage alumni={POTENTIAL_TIERS.map(alum)} />);
    const badges = Array.from(container.querySelectorAll('[data-tier]'));
    const classByTier = new Map(badges.map((b) => [b.getAttribute('data-tier'), b.className]));
    // Mid/Low/Raw must not collapse into the same class as each other.
    const distinct = new Set(['Mid', 'Low', 'Raw'].map((t) => classByTier.get(t)));
    expect(distinct.size).toBe(3);
  });
  it('renders an honest empty state when there are no alumni', () => {
    render(<AlumniLineage alumni={[]} />);
    expect(screen.getByText('No Alumni Yet')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "AlumniLineage"`. Expected: FAIL (current map collapses Mid/Low/Raw into the slate default AND has no `data-tier` hook).

- [ ] **Step 3: Implement** — in `AlumniLineage.tsx`, replace `TIER_TONE` with a `Record<PotentialTier, string>` keyed on `POTENTIAL_TIERS` imported from `'../../../domain/tiers'` (Elite/High/Mid/Low/Raw), each mapping to a distinct module tone class; fall back to a `.toneUnknown` class for off-vocabulary strings. Add `data-tier={entry.potential_tier}` to the badge. Create `AlumniLineage.module.css` importing the Record-Room frame: `.list`/`.row`/`.main`/`.meta`/`.side`/`.note`/`.tier` + per-tier tones using the **legacy/ink palette accents** (Record Room is cream/ink, so tier tones are ink-on-paper variants + a brick accent for Elite, per §3.8 — NOT the live Floodlight `--volt`/`--ok`). Keep the `EmptyState` import + the season/title pluralization copy verbatim. No raw hex/px (use `var(--legacy-*)`/`var(--font-serif)`).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "AlumniLineage" && npm run build`. Expected: PASS + build green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/history/AlumniLineage.*
git commit -m "fix(dynasty): re-point AlumniLineage tier map to domain/tiers.ts + Record Room module (#26)"
```

---

## Task 10: At-Risk exclusion guard (#63) for the locked-prospect sink

> **Why:** #63 has two halves: (a) the locked card renders no scoutable data (Task 4) and (b) name-only/out-of-reach prospects are **excluded from the At-Risk count** and **sink to the bottom of every sort**. The At-Risk filter `p.fully_visible !== false && (p.fit_score ?? 0) < 65` (DynastyOffice.tsx:663) and the sort sink (`fully_visible === false ? 1 : 0`) are pure and must survive the Task-7 reskin. Add a focused unit guard on the exclusion predicate so the reskin cannot regress it.

**Audit numbers:** #63 vitest (At-Risk excludes `fully_visible===false`; locked sinks).

**Files:** create `frontend/src/components/dynasty/atRisk.ts` (extracted pure helper) + `frontend/src/components/dynasty/atRisk.test.ts`; modify `frontend/src/components/DynastyOffice.tsx` to consume the helper (de-duplicates the inline predicate).

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/components/dynasty/atRisk.test.ts
import { describe, it, expect } from 'vitest';
import { isAtRisk, lockedSinkKey } from './atRisk';

describe('At-Risk + locked-sink predicates (#63)', () => {
  it('counts a visible low-fit prospect as at-risk', () => {
    expect(isAtRisk({ fully_visible: true, fit_score: 50 })).toBe(true);
  });
  it('excludes a beyond-network (locked) prospect from at-risk even if fit is low/absent', () => {
    expect(isAtRisk({ fully_visible: false, fit_score: 10 })).toBe(false);
    expect(isAtRisk({ fully_visible: false })).toBe(false);
  });
  it('a strong-fit visible prospect is not at-risk', () => {
    expect(isAtRisk({ fully_visible: true, fit_score: 84 })).toBe(false);
  });
  it('locked prospects sort AFTER visible ones', () => {
    expect(lockedSinkKey({ fully_visible: false })).toBeGreaterThan(lockedSinkKey({ fully_visible: true }));
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "atRisk"`. Expected: FAIL (`./atRisk` unresolved).

- [ ] **Step 3: Implement the helper** and re-point DynastyOffice to it.

```ts
// frontend/src/components/dynasty/atRisk.ts
// Single source for the #63 "name-only prospects excluded from At-Risk and
// sunk to the bottom of every sort" predicate. Mirrors the inline logic that
// previously lived in DynastyOffice.tsx (At-Risk count + sort comparators).
type ProspectLike = { fully_visible?: boolean; fit_score?: number };

/** A prospect is At-Risk only if he is fully visible AND his fit is below 65. */
export function isAtRisk(p: ProspectLike): boolean {
  return p.fully_visible !== false && (p.fit_score ?? 0) < 65;
}

/** 0 for visible prospects, 1 for beyond-network (locked) — locked sinks last. */
export function lockedSinkKey(p: ProspectLike): number {
  return p.fully_visible === false ? 1 : 0;
}
```

  Then in `DynastyOffice.tsx`: replace the inline At-Risk count expression (line ~663) with `prospects.filter(isAtRisk).length` and the two `fully_visible === false ? 1 : 0` sink expressions (lines ~626, ~999) with `lockedSinkKey(a)`/`lockedSinkKey(left)`. Import `{ isAtRisk, lockedSinkKey }` from `./dynasty/atRisk`. **No behavior change — the predicates are identical; this is a de-dup + testability extraction.** Keep the rest of the sort comparators verbatim.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "atRisk" && npm run build`. Expected: PASS + build green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/dynasty/atRisk.* frontend/src/components/DynastyOffice.tsx
git commit -m "feat(dynasty): extract At-Risk + locked-sink predicates (#63 testable, byte-identical)"
```

---

## Task 11: Record Room reskin — HistorySubTab, MyProgramView, LeagueView, BannerShelf, ProgramModal (cream/ink/Fraunces §3.8)

> **Why:** The history surfaces become the **Record Room** — cream paper, ink text, Fraunces headings, brick accents — strictly quarantined to `history/*` per §3.8. The behavior tests are locked (Tasks 1, 8, 9). This task moves all remaining `do-hist-*`/`dm-panel`/`dm-kicker`/`dm-badge*` global classes + inline styles (e.g. MyProgramView's `style={{ display:'flex', gap:'0.4rem' }}` at line 439) to Record-Room modules. **Keep #60/#66/#38/#35/#97/#26 behaviors green and the ProgramModal frozen signature + `command-policy-overlay` survival.**

**Audit numbers:** #35, #38, #60, #66, #97 (all locked in Tasks 1/8), plus the §3 P2/P3/P7 layout-bug fixes (truncation on `do-hist-glance`/`do-hist-list` rows, responsive collapse on the hard 5-col glance + `do-hist-grid`, legibility floor on the `.lbl`/`.note` micro-fonts).

**Files:** create `frontend/src/components/dynasty/history/recordRoom.module.css` (shared frame), `MyProgramView.module.css`, `LeagueView.module.css`, `BannerShelf.module.css`, `HistorySubTab.module.css`, `ProgramModal.module.css` + create `frontend/src/components/dynasty/history/BannerShelf.test.tsx`, `frontend/src/components/dynasty/HistorySubTab.test.tsx` (in `dynasty/`, NOT `dynasty/history/` — see File Map line 69); modify the 5 components.

- [ ] **Step 1: Write the BannerShelf + HistorySubTab #97 tests (RED-first)**

```tsx
// frontend/src/components/dynasty/history/BannerShelf.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BannerShelf } from './BannerShelf';

describe('BannerShelf (#97 next-banner placeholder gated on isSelf)', () => {
  it('shows the "Next banner" open slot only when showNextPlaceholder', () => {
    const { rerender } = render(<BannerShelf banners={[]} showNextPlaceholder />);
    expect(screen.getByText('Next banner')).toBeInTheDocument();
    rerender(<BannerShelf banners={[]} showNextPlaceholder={false} />);
    expect(screen.queryByText('Next banner')).not.toBeInTheDocument();
    expect(screen.getByText('No Banners Yet')).toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/components/dynasty/HistorySubTab.test.tsx
// NOTE: placed in dynasty/ (same dir as HistorySubTab.tsx), NOT in dynasty/history/.
// Importing from './HistorySubTab' resolves correctly here.
// vi.mock specifiers must match the EXACT strings HistorySubTab.tsx uses in its own imports
// (Vitest resolves mock specifiers relative to the module under test, not the test file).
// Confirmed from HistorySubTab.tsx lines 2-3:
//   import { MyProgramView } from './history/MyProgramView';
//   import { LeagueView } from './history/LeagueView';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { HistorySubTab } from './HistorySubTab';

vi.mock('./history/MyProgramView', () => ({ MyProgramView: () => <div data-testid="stub-mp" /> }));
vi.mock('./history/LeagueView', () => ({ LeagueView: () => <div data-testid="stub-lv" /> }));

describe('HistorySubTab (#97 self-only label)', () => {
  it('labels the program tab "My Program" when isSelf and "Program" otherwise', () => {
    const { rerender } = render(<HistorySubTab clubId="hammers" isSelf />);
    expect(screen.getByRole('button', { name: 'My Program' })).toBeInTheDocument();
    rerender(<HistorySubTab clubId="rivals" isSelf={false} />);
    expect(screen.getByRole('button', { name: 'Program' })).toBeInTheDocument();
  });
});
```

  > **Mock-path correctness:** `HistorySubTab.tsx` lives at `dynasty/` and imports `'./history/MyProgramView'` and `'./history/LeagueView'` (confirmed at HistorySubTab.tsx lines 2-3). The test file is co-located at `dynasty/HistorySubTab.test.tsx` and imports `'./HistorySubTab'`. Vitest resolves `vi.mock` specifiers against the **module under test's** location (`dynasty/`), so `'./history/MyProgramView'` and `'./history/LeagueView'` are the correct mock keys — they match the source import strings exactly. Do NOT place this test in `dynasty/history/` or the import `'./HistorySubTab'` would resolve to a nonexistent `dynasty/history/HistorySubTab.tsx`.

- [ ] **Step 2: Run to verify** — `cd frontend && npm run test -- "BannerShelf" "HistorySubTab"`. Expected: PASS on current markup (behavior-lock; #97 already true). Fix mock specifiers to the real import strings if resolution fails.

- [ ] **Step 3: Build the shared Record-Room frame module** — `recordRoom.module.css`:

```css
/* frontend/src/components/dynasty/history/recordRoom.module.css */
/* §3.8 Record Room: cream paper + ink + Fraunces. Quarantined to history/*. */
.room {
  background: var(--legacy-paper);
  color: var(--legacy-ink);
  font-family: var(--font-serif);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}
.kicker {
  font: 600 .72rem var(--font-ui);   /* instrumentation label, ≥0.7rem floor */
  letter-spacing: .08em; text-transform: uppercase; color: var(--legacy-brick);
}
.heading { font: 600 1.05rem var(--font-serif); color: var(--legacy-ink); margin: 0; }
.panel {
  background: var(--legacy-paper); color: var(--legacy-ink);
  border: 1px solid var(--legacy-ink); border-radius: var(--radius-md); padding: var(--space-5);
}
.note { font: 400 .8rem var(--font-ui); color: var(--legacy-ink); opacity: .8; }
```

  (All history modules `composes`/import from this or restate the legacy vars; never a raw `#F3EBD8`.)

- [ ] **Step 4: Reskin the five components** to their modules + the shared frame:
  - **HistorySubTab.tsx** — `.filters`/`.filter`/`.filterActive`/`.meta`; keep the `programLabel` isSelf branch + both view mounts verbatim.
  - **MyProgramView.tsx** — glance strip (responsive `Grid`-style collapse on the hard 5-col `do-hist-glance`), timeline, Program Arc, the Banner/Alumni shelf tabs; replace the inline `style={{ display:'flex', gap:'0.4rem' }}` (line 439) with a module class. **Keep the `allTime ? 'All-Time Record' : 'Latest Season Record'` branch (#60), the isSelf alumni copy (#97), the `TermTip`/`ProofChip`/`EmptyState`/`StatusMessage` children, and the `HeroCard`/`buildEntry`/`fallbackEntry`/`seasonTick` logic verbatim.** Truncate long club/holder names (P2).
  - **LeagueView.tsx** — glance, directory buttons, the worlds/dynasty/records/HoF/rivalries cards; responsive collapse on `do-hist-grid`; ellipsis on `do-hist-list-row` names. **Keep `record.record?.holder_name || humanizeHistoryToken(...)` (#66), the `data.worlds && data.worlds.length > 0` gate + runner-up clause (#38), every `EmptyState` (#35), and the `ProgramModal` mount with its frozen props verbatim.**
  - **BannerShelf.tsx** — `.banners`/`.banner`/`.bannerTitle`/`.bannerAward`/`.bannerEmpty` + the `formatSeasonLabel` import; keep the `showNextPlaceholder` placeholder + EmptyState verbatim (#97).
  - **ProgramModal.tsx** — move the BODY presentation (`do-hist-modal-header`/`do-hist-modal-title`/`do-hist-card-note`/`command-policy-overlay-close`) to `ProgramModal.module.css`. **KEEP: the `Dialog` import from `components/ui`; `className="command-policy-overlay"` on the overlay (SHARED global — survives); `labelledBy="program-modal-title"`; `MyProgramView` with `isSelf={false}`; the frozen `{clubId, clubName, onClose}` props.** Only the modal's own header/note/close-button classes move to the module. The `panelClassName` may keep `command-policy-overlay-body` (shared) + swap `do-hist-modal-body` → `styles.body`.

  All five: no raw hex/px (only `var(--legacy-*)`/`var(--font-serif)`/spacing/radius tokens). Legibility floor ≥0.7rem on every label.

- [ ] **Step 5: Run the full Phase-5 test set** — `cd frontend && npm run test -- "dynasty" && npm run build`. Expected: every Phase-5 test green (ProgramModal contract, MyProgramView #60/#97, LeagueView #66/#38/#35, BannerShelf #97, HistorySubTab #97, AlumniLineage #26, ProspectCard, CredibilityStrip, RecruitingBadge, atRisk) + build green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/dynasty/history/
git commit -m "feat(dynasty): Record Room reskin (cream/ink/Fraunces §3.8) — history quarantined; truth + frozen signature preserved (#35,#38,#60,#66,#97)"
```

---

## Task 12: Phase-5 worktree gate — full verification

> **Why:** Prove the whole lane green before the controller integrates. This runs with the OLD `index.css` still present (the legacy `do-*` selectors are deleted later by the integrator in STEP 3); the gate must pass anyway because the new modules supply all needed styling and the new components no longer depend on the legacy classes for correctness (visual mixed-look is acceptable until STEP 3 cleanup).

**Files:** none (verification only).

- [ ] **Step 1: Run the full FE gate**

```bash
cd frontend && npm run test && npm run build && npm run lint
```
Expected: all Phase-5 vitests pass; full FE suite green; build clean; eslint clean.

- [ ] **Step 2: Token-discipline self-check (throwaway — do NOT commit a `check-tokens.mjs` edit)** — run an ad-hoc scan over the Phase-5 dirs to confirm no raw hex/px slipped into the new modules:

```bash
cd frontend && node -e "const {readFileSync}=require('fs');const {execSync}=require('child_process');const files=execSync('git ls-files src/components/dynasty').toString().split('\n').filter(f=>/\.(css|tsx|ts)$/.test(f)&&!/\.test\./.test(f));const HEX=/#[0-9a-fA-F]{3,8}\b/;const PX=/(?<![\w.])(?!0px|1px)\d{1,4}px\b/;let bad=[];for(const f of files){readFileSync(f,'utf8').split('\n').forEach((l,i)=>{if(/viewBox/.test(l))return;if(HEX.test(l)||PX.test(l))bad.push(f+':'+(i+1)+'  '+l.trim());});}if(bad.length){console.error(bad.join('\n'));process.exit(1);}console.log('phase-5 token self-check OK');"
```
Expected: `phase-5 token self-check OK`. (This mirrors the committed gate's HEX/PX rules but is run inline so `check-tokens.mjs` stays frozen. If it flags a literal, replace it with a token and re-run; layout-math `%` and `viewBox` are not flagged.)

- [ ] **Step 3: e2e smoke (the dynasty/history path)**

```bash
cd .. && npm run e2e -- tests/e2e/maximized-playthrough-qa.spec.ts
```
Expected: green (this spec drives the playthrough into the dynasty office + offseason). If the dynasty office isn't exercised by it, also run `npm run e2e` (full) and confirm no regression on the dynasty/history surfaces.

- [ ] **Step 4: Manual smoke (optional but recommended)** — launch `python -m dodgeball_sim`, open the Dynasty tab, switch Recruit ↔ History ↔ League, open a club ProgramModal from the League directory; confirm the Recruit subtab is warm-graphite Floodlight and the History/League/ProgramModal surfaces are the cream/ink Record Room, with no live UI warming.

- [ ] **Step 5: Final commit (gate marker)**

```bash
git commit -am "chore(dynasty): Phase 5 worktree gate green (dynasty + recruiting + Record Room)" --allow-empty
```

> Do NOT merge. The controller integrates this branch in STEP 3 (legacy `index.css` selector deletion + SCAN_DIRS append + full tsc/vitest re-gate).

---

## Self-Review

**Behavior coverage (Phase-5 assigned: #19–#28, #30, #59–#66, #97):**
- #19 (mechanical/flavor TermTip badge) → Task 7 (legibility primitive rendered as-is; badge text preserved) ✓
- #20 (verbatim receipts/evidence) → Task 5 (CredibilityStrip evidence vitest) ✓
- #21 (KnownValue 3-state) → Task 6 (ProspectCard OVR band vitest) ✓
- #22 (founding-class unfogged) → **out of Phase-5 scope** (StartingRecruitmentStep = Phase 7); documented in the coverage map note ✓ (no Phase-5 surface)
- #23 (band vs verified OVR) → Task 6 ✓
- #24 (dealbreaker hidden/veto) → Task 6 vitest ✓
- #25 (Tactical-Diff intel source) → **out of Phase-5 scope** (PreSimDashboard = Phase 2); documented ✓
- #26 (vocabulary de-collision) → Task 9 (AlumniLineage re-pointed to `tiers.ts`, distinct-tone vitest) ✓
- #27 (ruleset name normalization) → **out of Phase-5 scope** (rulesetNames.ts consumers = P1/P2); documented ✓
- #28 (CeilingGrade null-on-unknown) → Task 6 (rendered via frozen primitive; conditional on `ceiling_label`) ✓
- #30 (data-* provenance survives) → Task 4 anti-strip (`prospect-card-locked` + family), HARD RED precondition ✓
- #59 (credibility grade from payload) → Task 5 vitest ✓
- #60 (all-time vs latest label) → Task 8 vitest (both branches) ✓
- #61/#62 (promise states + labels) → Task 6 (promise chip + PROMISE_TYPE_LABELS preserved) ✓
- #63 (locked sink + At-Risk exclusion) → Task 4 (no scoutable data) + Task 10 (`isAtRisk`/`lockedSinkKey` vitest) ✓
- #64 (monotonic optimistic status) → Task 3 (badge render) + Task 6 (precedence logic verbatim) ✓
- #65 (refused action "not spent" + refetch) → Task 6 vitest ✓
- #66 (persisted holder display name) → Task 8 vitest ✓
- #97 (isSelf self-only copy + Next-banner) → Task 1 (ProgramModal isSelf=false), Task 8 (MyProgramView alumni copy), Task 11 (BannerShelf placeholder + HistorySubTab label) ✓

Every assigned behavior maps to a task + a named test strategy from the checklist. The three range-gap behaviors (#22/#25/#27) are explicitly flagged as other-phase surfaces with a "do not touch" instruction, preventing accidental cross-phase edits.

**Phase-specific requirements + freezes (encoded as task constraints):**
- NO `index.css` edits/deletions → stated in Orchestration rule 1 + every reskin task creates `*.module.css` only; zero index.css deletion tasks ✓
- NO `ui.tsx` edits; re-point to `src/ui` shims, no ActionButton→ActionBar → Task 2 (StatusMessage only; Dialog stays on components/ui) ✓
- ProgramModal frozen `{clubId,clubName,onClose}` → Task 1 contract guard + Task 11 preserves props ✓
- `command-policy-overlay` SHARED survives → Task 1 asserts overlay class survival + Task 11 keeps it ✓
- Record Room legacy tokens already in tokens.css → Task 11 `recordRoom.module.css` uses `var(--legacy-*)`/`var(--font-serif)` (verified present at tokens.css:13,19) ✓
- Anti-strip `prospect-card-locked` → Task 4 HARD RED precondition ✓
- #97 isSelf gating → Tasks 1/8/11 ✓
- AlumniLineage stale tier map re-pointed to `src/domain/tiers.ts` → Task 9 ✓
- legibility/* read-only, matchResult.ts frozen, check-tokens.mjs untouched, per-phase gate with old index.css → Orchestration rules 3/4 + Task 12 (throwaway token self-check, no gate edit) ✓
- FROZEN consumed contracts → ProgramModal signature (the live one for this lane); appContracts.ts not directly imported (noted) ✓

**Placeholder scan:** No `TODO`/`...`/"fill in" placeholders. Every code step has concrete content. Two correctness guards are intentional (not placeholders): (a) Task 4/5/6/8 fixtures say "read the exact field names from `types.ts` before writing" — this is an anti-invention guard, the shape is otherwise fully specified; (b) Task 11 Step 1 mock-path note says "confirm the exact import specifier from `HistorySubTab.tsx`" — a resolution-correctness guard. Both are deliberate verify-don't-invent instructions consistent with the repo's "verify current names" rule, not logic gaps.

**Type/name consistency:** Component prop names match source (`ProgramModal {clubId,clubName,onClose}`, `MyProgramView {clubId, isSelf}`, `HistorySubTab {clubId, isSelf}`, `BannerShelf {banners, showNextPlaceholder}`, `AlumniLineage {alumni}`, `ProspectCard {prospect, budget, onAction, priority}`, `CredibilityStrip {credibility}`, `RecruitingBadge {status, pending}`). Test ids match the source verbatim (`prospect-card-locked`, `prospect-card`, `prospect-motivations`, `prospect-rivals`, `prospect-promise-chip`, `treasury-chip`, `promises-panel`, `recruiting-badge-${status}`). Extracted helper names (`isAtRisk`, `lockedSinkKey`, `POTENTIAL_TIERS`) match between source, consumer, and test. The legacy tokens referenced (`--legacy-paper`, `--legacy-ink`, `--legacy-brick`, `--font-serif`) match `tokens.css` exactly. Relative import depths corrected for the `dynasty/history/` directory level (`../../../ui`, `../../../domain/tiers`, `../../../hooks/useApiResource`).

**Gaps found + fixed during review:**

1. *(Initial draft)* Re-pointed `Dialog` to `src/ui` along with `StatusMessage` — corrected; `Dialog` is NOT one of the five Phase-1 shims and stays on `components/ui`.

2. *(Reviewer blocker)* Task 2 assumed Phase-1 shims were already present in `src/ui/index.ts`. The current barrel (Phase-0) exports only the 11 Phase-0 primitives; `StatusMessage` is absent. Task 2 now opens with a mandatory Step 0 preflight (`grep 'StatusMessage' frontend/src/ui/index.ts || exit 1`) that STOPS the task if Phase-1 has not yet merged to trunk. Documented as an explicit PREREQUISITE.

3. *(Reviewer blocker)* `HistorySubTab.test.tsx` was placed in `dynasty/history/` in the File Map and Task 11 Step 1. `HistorySubTab.tsx` lives at `dynasty/HistorySubTab.tsx` (NOT in the `history/` subdirectory). A test at `dynasty/history/HistorySubTab.test.tsx` importing `'./HistorySubTab'` would resolve to a nonexistent file. Fixed: test is now at `dynasty/HistorySubTab.test.tsx`; vi.mock specifiers (`'./history/MyProgramView'`, `'./history/LeagueView'`) correctly mirror the source file's own import strings (confirmed HistorySubTab.tsx lines 2-3).

4. *(Reviewer major)* The #35 LeagueView empty-state assertion in Task 8 overlaps with the Phase-6 preservation checklist assignment. The assertion is retained as a defense-in-depth guard for the LeagueView surface only, with an explicit in-code comment that Phase 6 owns the full #35 contract and must not skip non-LeagueView surfaces. Self-Review no longer claims full #35 ownership for Phase 5.

5. *(Reviewer minor)* Task 6 #24 test lacked negative assertions confirming the veto copy is absent and that an empty-motivations base prospect renders no motivations block. Both assertions added.

6. *(Reviewer minor)* Task 4 `as Budget` cast removed. The fixture now uses `const budget: Budget = { ... }` without a cast. TypeScript structural checking catches any future field-name drift at compile time. Shape pre-verified against `types.ts` lines 1564-1567: `{ scout: [number,number]; contact: [number,number]; visit: [number,number] }` — exact match to the fixture.

**#35 cross-phase ownership (Phase 5 vs Phase 6):** #35 is assigned to Phase 6 in the preservation checklist. The LeagueView empty-state check in Task 8 is a defense-in-depth guard for that one surface. Phase 6 retains full ownership of the #35 contract and must cover ceremony/offseason + all other surfaces; this guard does not reduce Phase 6's obligation.
