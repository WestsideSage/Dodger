# Floodlight Phase 4 — Standings + League + Bracket + Pyramid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the League Office screen (`LeagueContext.tsx` `Standings` + its `PyramidPanel`), the `standings/PlayoffBracket.tsx`, and the season-label/sort consolidation onto the Floodlight token system using CSS Modules — while keeping the 8 Phase-4 trust behaviors green (#6, #7, #15, #16, #33, #34, #38, #96). This is one of the six CONCURRENT worktree lanes (STEP 2) branched from the **merged post-Phase-1 trunk**.

**Architecture:** `LeagueContext.tsx`, `standings/PlayoffBracket.tsx`, and the new `standings/PyramidPanel.tsx` (extracted from `LeagueContext.tsx`) move from inline-style objects + the legacy `index.css` `.ls-*` / `.playoff-*` selector families to scoped `*.module.css` files driven by `src/styles/tokens.css`. The V20 scoring-model branch logic (GP-Diff vs Survivor-Diff, official vs legacy differential, draw labels, player-outcome ribbon) is preserved verbatim — only the styling substrate changes. A new shared `src/domain/seasonLabel.ts` centralizes season-label parsing AND the numeric sort comparator (#96), consumed by standings and (frozen-import) the history surfaces.

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (harness from Phase 0).

**Spec:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md) §1 (Standings + league-context screens), §2.A #6/#7, §2.B #15/#16, §2.D #33/#34/#38, §2.J #96, §3 P2/P3/P10 standings rows · **Checklist:** [floodlight-preservation-checklist.md](floodlight-preservation-checklist.md) Phase 4 rows · **Orchestration contract:** [2026-06-19-floodlight-parallelization-strategy.md](2026-06-19-floodlight-parallelization-strategy.md) GROUP STEP 2 (concurrent worktree) · **Phase-1 contracts consumed:** [2026-06-19-floodlight-phase-1-app-shell.md](2026-06-19-floodlight-phase-1-app-shell.md) · **Foundations + style template:** [2026-06-19-floodlight-phase-0-foundations.md](2026-06-19-floodlight-phase-0-foundations.md)

**Branch:** an isolated git worktree off the merged post-Phase-1 trunk (per strategy STEP 2). All Phase-4 commits land on that worktree branch; the controller commits and the serial integrator (STEP 3) merges + does the `index.css` deletions.

---

## Hard rules this phase operates under (orchestration contract — encoded as task constraints)

These are the binding freezes for the concurrent window. Every task below is written to obey them; they are repeated here so a worker cannot miss one.

1. **NO `index.css` edits or deletions.** This phase CREATES `*.module.css` files ONLY. The legacy `.ls-*`, `.playoff-bracket-*`, `.playoff-seed-chip`, `.playoff-champion-card`, `.need-*`, `.race-*`, `.cut-row`, `.ls-tb-*`, `.ls-wire-*`, `.ls-diff-*` selector families in `index.css` are removed **later by the serial integrator in STEP 3** (after this branch merges). Do **not** add a task to delete them. (Strategy: `index.css` is a single-writer resource; the 8631-line shared `@media` block makes concurrent deletion a silent-dangling-brace hazard.)
2. **NO edits to `components/ui.tsx`.** `LeagueContext.tsx` currently imports `StatusMessage` from `./ui` (`LeagueContext.tsx:4`). Re-point that import to the Phase-1 `src/ui` shim (`import { StatusMessage } from '../ui'` → from the barrel `src/ui/index.ts`). This is an **import-path change ONLY** — no `ActionButton→ActionBar` remap (deferred to Phase 8), and `StatusMessage`'s signature is identical between `ui.tsx` and the shim.
3. **FROZEN — consume, never alter:**
   - `components/match-week/matchResult.ts` public API (`formatScoreline` / `survivorDetail` / `ScorelineFields` / `MatchScoreline`). PlayoffBracket imports `formatScoreline` from it — keep that import as-is, do not relocate or re-implement (re-introduces the PT6 0-0 trust-break).
   - `legibility/*` primitives (`TermTip`, `EmptyState`, `CLUB_ARCHETYPE_TERM`) — read-only until Phase 8. Accept their mixed Floodlight+legacy look. Keep consuming them by their current import (`'../legibility'`).
   - The SHARED globals `command-action-bar` / `command-policy-overlay` — not used on these screens; never delete them.
   - `frontend/scripts/check-tokens.mjs` — the **integrator owns SCAN_DIRS appends**. This phase does not edit it. (Token violations in the new modules are therefore not caught by `npm run lint:tokens` until the integrator appends `src/components/standings` + the standings files — so every reskin task MUST use only `var(--…)` tokens from the start; the per-phase gate runs `lint:tokens` to prove the *already-scanned* dirs stay clean.)
4. **FROZEN public signatures this phase OWNS but must not change:**
   - `standings/PlayoffBracket.tsx` exports `export function PlayoffBracket({ data }: { data: PlayoffBracketResponse })`. **P6 `ChampionReveal.tsx:4` statically imports it.** This phase REBUILDS its internals (MatchCard sub-component + markup → CSS Modules) but MUST NOT change the export name, file path, or props. The Phase-1 contract test `standings/PlayoffBracket.contract.test.tsx` (already on trunk) must stay green.
5. **Consume Phase-1 published contracts** where relevant: `components/shell/appContracts.ts` (none of MatchWeekMountProps/CommandReplayState/NAV_RAIL_ATTR are used by standings — App mounts `<Standings/>` with no props, verified `App.tsx` standings tab) — so no contract import is needed, but do NOT add props to `Standings`. The frozen `dynasty/history/ProgramModal` signature `{ clubId, clubName, onClose }` IS consumed: `LeagueContext.tsx:676-681` renders `<ProgramModal>` — keep that call shape verbatim (P5 owns ProgramModal's body).
6. **data-* anti-strip hooks are HARD RED preconditions.** The truth-provenance hooks present on these screens MUST survive the rebuild and be tested before any reskin: `data-player-outcome` (+ `data-testid="playoff-bracket"`, `data-testid="playoff-bracket-decided-by-chip"`, `data-decided-by`) on PlayoffBracket; `data-screen-label` on the standings shell. Enumerated + tested in Tasks 1, 3, 6.

---

## Behaviors owned by this phase (audit §2 → task → test strategy)

| # | Behavior (short) | Owning task | Test strategy |
|---|---|---|---|
| 6 | Standings rank/diff column branches — 'GP Diff' vs 'Survivor Diff', need-copy label branches (LeagueContext.tsx:328-336,367,487; Pyramid 296-298) | Task 4, 5 | vitest |
| 7 | "Plan" badge uses command-center display vocabulary (Balanced/Aggressive/Control/Defensive/Develop Youth) (LeagueContext.tsx:36-48) | Task 4 | vitest |
| 15 | Draw handling — winner_name==='Draw' shows Draw not a fabricated win; unparseable summaries fall back to raw, never dropped (LeagueContext.tsx:185,177-181) | Task 4 | vitest |
| 16 | Player-outcome ribbon gated on played AND player-in-match AND winner identity (PlayoffBracket.tsx:16-19,59,75-89) | Task 3 | vitest |
| 33 | Tiebreaker panel three states (hidden/soft/live) gated on phase + games-played (LeagueContext.tsx:379-384,615-628) | Task 5 | vitest |
| 34 | Phase-aware race/need copy — regular-season math suppressed during playoffs/offseason (LeagueContext.tsx:346-367) | Task 5 | vitest |
| 38 | World Championship roll only when worlds data exists; runner_up clause only when present (LeagueView.tsx:132,145) | Task 2 | vitest (guard on shared seasonLabel + cross-phase note) |
| 96 | Season label parsing centralized; sort numerically (avoid season_10<season_2 string trap) (formatters.ts:26-39; MyProgramView seasonTick) | Task 2 | vitest |

**Cross-phase note for #38:** the worlds-roll markup physically lives in `dynasty/history/LeagueView.tsx`, which is **Phase-5-owned** (rebuilt there). This phase cannot reskin that file (freeze). Phase 4's deliverable for #38 is the **shared, tested season-label helper** that the worlds roll consumes (`formatSeasonLabel`) PLUS a guard vitest that pins "only render the worlds roll when `worlds.length > 0`, runner-up clause only when present" against the CURRENT `LeagueView` (a non-regression lock that does not touch the file). This keeps #38 green through the window without violating the P5 freeze; P5's reskin must keep this guard green. This is recorded as a judgment call in Self-Review.

---

## File map (created/modified in this plan)

**Created (shared season-label helper — #96/#38):**
- `frontend/src/domain/seasonLabel.ts` (centralized parse + numeric sort comparator)
- `frontend/src/domain/seasonLabel.test.ts`

**Created (anti-strip + behavior preconditions, RED-first):**
- `frontend/src/components/standings/PlayoffBracket.test.tsx` (#16 + data-* anti-strip)
- `frontend/src/components/LeagueContext.test.tsx` (#6 header+pyramid, #7, #15, #33, #34 + data-screen-label anti-strip)
- `frontend/src/components/standings/PyramidPanel.test.tsx` (#6 pyramid diff branch — extracted unit test, authored in Task 6 Step 2 after extraction)
- `frontend/src/components/dynasty/history/LeagueView.worlds.guard.test.tsx` (#38 cross-phase guard)

**Created (CSS Modules):**
- `frontend/src/components/standings/PlayoffBracket.module.css`
- `frontend/src/components/standings/PyramidPanel.module.css`
- `frontend/src/components/LeagueContext.module.css`

**Created (extracted component — keeps LeagueContext.tsx from re-growing):**
- `frontend/src/components/standings/PyramidPanel.tsx` (moved out of `LeagueContext.tsx`; default-stable internal component, NOT a public contract)

**Modified:**
- `frontend/src/components/standings/PlayoffBracket.tsx` (reskin internals to module CSS; **signature frozen**)
- `frontend/src/components/LeagueContext.tsx` (reskin to module CSS; extract `PyramidPanel`; re-point `StatusMessage` import to `../ui`; consume `seasonLabel` helper where it sorts/labels seasons; `ProgramModal` call verbatim)

**Frozen / NOT touched:** `index.css` (integrator deletes legacy selectors in STEP 3), `components/ui.tsx`, `match-week/matchResult.ts`, `legibility/*`, `dynasty/history/ProgramModal.tsx`, `dynasty/history/LeagueView.tsx` (P5-owned — only a non-mutating guard test is added against it), `dynasty/history/formatters.ts` (P5-owned; the new `domain/seasonLabel.ts` is the Phase-4 shared source — see Task 2 for the no-collision rationale), `scripts/check-tokens.mjs` (integrator-owned).

---

## Per-task gate

Unless a task says otherwise, every task ends green on:

```bash
cd frontend && npm run test -- <the task's test files> && npm run build && npm run lint && npm run lint:tokens
```

The **Phase-4 worktree gate** (Task 7) runs the full FE suite + build + lint + token gate + a smoke e2e (the integrator runs the index.css deletion + full `tsc --noEmit`/vitest later in STEP 3):

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e -- tests/e2e/maximized-playthrough-qa.spec.ts
```

> **Token-gate scope caveat (strategy rule 3):** `npm run lint:tokens` scans only `SCAN_DIRS` (`src/ui`, `src/styles`) on this branch — the integrator appends `src/components/standings` + the standings files to SCAN_DIRS in STEP 3. So the gate will NOT flag literals in the new modules during this window. Each reskin task MUST therefore use only `var(--…)` tokens (no raw hex; no raw px beyond `0`/`1px` hairlines) **from the start**, and Task 7 includes a manual self-scan step (run the gate logic locally against the new dir) so the integrator's later append does not surface violations.

---

## Phase 4A — Shared season-label helper (#96, #38 foundation)

### Task 1: PlayoffBracket anti-strip + #16 preconditions (RED-first, lock before reskin)

> **Why:** Before rebuilding PlayoffBracket's internals, lock its truth-provenance hooks and the #16 player-outcome gating so the reskin (Task 3) cannot strip them. The audit (§2.B #16) requires the player-outcome ribbon to be gated on `played AND playerInMatch AND winner identity`, exposed on the DOM as `data-player-outcome` ('advanced'|'eliminated'|absent). The component also carries `data-testid="playoff-bracket"`, `data-testid="playoff-bracket-decided-by-chip"` + `data-decided-by`, which P6 / Python guards key on. These are HARD RED anti-strip preconditions.

**Audit numbers + test strategy:** #16 vitest · anti-strip vitest (`data-player-outcome`, `data-testid` provenance).

**Real props captured (verified `PlayoffBracket.tsx:121`, `types.ts:534-581`):** `PlayoffBracket({ data }: { data: PlayoffBracketResponse })` where `PlayoffBracketResponse` = `{ active; seeds?; rounds?: { round; matches: PlayoffBracketMatch[] }[]; champion_club_id?; champion_club_name?; player_club_id? }` and a match carries `home/away_club_id`, `home/away_club_name`, `home/away_survivors`, `home/away_game_points?`, `scoring_model?`, `winner_club_id`, `status`, `decided_by?`, `narrative_note?`.

**Files:** create `frontend/src/components/standings/PlayoffBracket.test.tsx`.

- [ ] **Step 1: Write the failing/locking test** — render the CURRENT (pre-reskin) PlayoffBracket so the test proves the harness is wired and the hooks exist now (it then guards the reskin).

```tsx
// frontend/src/components/standings/PlayoffBracket.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PlayoffBracket } from './PlayoffBracket';
import type { PlayoffBracketResponse, PlayoffBracketMatch } from '../../types';

const baseMatch = (over: Partial<PlayoffBracketMatch>): PlayoffBracketMatch => ({
  match_id: 'm1',
  home_club_id: 'you',
  home_club_name: 'Granite City Hammers',
  away_club_id: 'them',
  away_club_name: 'Harbor Wolves',
  home_survivors: 0,
  away_survivors: 3,
  home_game_points: 2,
  away_game_points: 1,
  scoring_model: 'official_foam',
  winner_club_id: 'you',
  status: 'played',
  decided_by: 'regulation',
  narrative_note: null,
  ...over,
});

function bracket(matches: PlayoffBracketMatch[], over: Partial<PlayoffBracketResponse> = {}): PlayoffBracketResponse {
  return {
    active: true,
    seeds: [],
    rounds: [{ round: 'semifinal', matches }],
    player_club_id: 'you',
    ...over,
  };
}

describe('PlayoffBracket (Phase 4 — #16 + anti-strip)', () => {
  it('renders the panel with its data-testid provenance', () => {
    render(<PlayoffBracket data={bracket([baseMatch({})])} />);
    expect(screen.getByTestId('playoff-bracket')).toBeInTheDocument();
  });

  it('#16: player-outcome ribbon = advanced when the user played and won', () => {
    const { container } = render(<PlayoffBracket data={bracket([baseMatch({ winner_club_id: 'you' })])} />);
    expect(container.querySelector('[data-player-outcome="advanced"]')).not.toBeNull();
    expect(screen.getByText('YOU ADVANCED')).toBeInTheDocument();
  });

  it('#16: player-outcome ribbon = eliminated when the user played and lost', () => {
    const { container } = render(<PlayoffBracket data={bracket([baseMatch({ winner_club_id: 'them' })])} />);
    expect(container.querySelector('[data-player-outcome="eliminated"]')).not.toBeNull();
    expect(screen.getByText('YOU ELIMINATED')).toBeInTheDocument();
  });

  it('#16: NO ribbon when the user is not in the match', () => {
    const { container } = render(
      <PlayoffBracket data={bracket([baseMatch({ home_club_id: 'a', away_club_id: 'b', winner_club_id: 'a' })])} />,
    );
    expect(container.querySelector('[data-player-outcome]')).toBeNull();
  });

  it('#16: NO ribbon when the match is unplayed', () => {
    const { container } = render(
      <PlayoffBracket data={bracket([baseMatch({ status: 'scheduled', winner_club_id: null })])} />,
    );
    expect(container.querySelector('[data-player-outcome]')).toBeNull();
  });

  it('anti-strip: decided_by chip keeps its testid + data attribute on a tiebreaker', () => {
    render(<PlayoffBracket data={bracket([baseMatch({ decided_by: 'overtime' })])} />);
    const chip = screen.getByTestId('playoff-bracket-decided-by-chip');
    expect(chip).toHaveAttribute('data-decided-by', 'overtime');
    expect(chip).toHaveTextContent('OT');
  });

  it('renders nothing when the bracket is inactive', () => {
    const { container } = render(<PlayoffBracket data={{ active: false }} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "standings/PlayoffBracket"`. Expected: **PASS against the current component** (the hooks already exist), proving the harness + props are correct. If any case fails, fix the assertion to the CURRENT truth (these guard existing behavior).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/standings/PlayoffBracket.test.tsx
git commit -m "test(standings): lock PlayoffBracket #16 player-outcome + data-* anti-strip before reskin"
```

---

### Task 2: Centralized season-label parse + numeric sort (#96) and the #38 worlds-roll guard

> **Why:** Audit §2.J #96 — season labels must be parsed in ONE place and sorted **numerically** so `season_10` does not sort before `season_2` (the string-sort trap). Today two divergent helpers exist: `dynasty/history/formatters.ts` `formatSeasonLabel` (P5-owned) and `MyProgramView.tsx` `seasonTick`. There is no numeric comparator anywhere. This phase creates the canonical `src/domain/seasonLabel.ts` (parse → number, format → label, compare → numeric) in the **shared `src/domain/` dir** (already established by Phase 0's `tiers.ts`), so neither P4 nor P5 fights over `dynasty/history/formatters.ts` (frozen for P5). Standings consumes the comparator where it orders seasons; P5 re-points its helpers to it in Phase 5. #38 (worlds roll renders only when data exists) is locked here as a non-mutating guard because the worlds markup lives in P5's `LeagueView`.

> **No-collision rationale (freeze-safe):** this creates a NEW file in `src/domain/`; it does NOT edit `dynasty/history/formatters.ts`. The `formatSeasonLabel` output here is byte-identical to the existing helper's `season_N → "Season N"` rule, so any later re-point is a drop-in. (Re-pointing the P5 files is Phase 5's job, not this plan's.)

**Audit numbers + test strategy:** #96 vitest · #38 vitest (guard).

**Files:** create `frontend/src/domain/seasonLabel.ts` + `seasonLabel.test.ts`; create `frontend/src/components/dynasty/history/LeagueView.worlds.guard.test.tsx`.

- [ ] **Step 1: Write the failing tests**

```ts
// frontend/src/domain/seasonLabel.test.ts
import { describe, it, expect } from 'vitest';
import { parseSeasonNumber, formatSeasonLabel, compareSeasonAsc, compareSeasonDesc } from './seasonLabel';

describe('seasonLabel (#96 — centralized parse + numeric sort)', () => {
  it('parses season_N to its number', () => {
    expect(parseSeasonNumber('season_2')).toBe(2);
    expect(parseSeasonNumber('season_10')).toBe(10);
    expect(parseSeasonNumber('SEASON_07')).toBe(7);
  });
  it('returns null for unparseable labels (so callers can sort them last, not crash)', () => {
    expect(parseSeasonNumber('worlds-era')).toBeNull();
    expect(parseSeasonNumber(undefined)).toBeNull();
  });
  it('formats season_N to "Season N", passes other labels through humanized', () => {
    expect(formatSeasonLabel('season_3')).toBe('Season 3');
    expect(formatSeasonLabel(null)).toBe('Unknown season');
  });
  it('sorts NUMERICALLY, not lexically (season_10 after season_2)', () => {
    const ids = ['season_10', 'season_2', 'season_1'];
    expect([...ids].sort(compareSeasonAsc)).toEqual(['season_1', 'season_2', 'season_10']);
    expect([...ids].sort(compareSeasonDesc)).toEqual(['season_10', 'season_2', 'season_1']);
  });
  it('unparseable labels sort after all numbered seasons (deterministic)', () => {
    const ids = ['season_2', 'arc', 'season_1'];
    expect([...ids].sort(compareSeasonAsc)).toEqual(['season_1', 'season_2', 'arc']);
  });
});
```

```tsx
// frontend/src/components/dynasty/history/LeagueView.worlds.guard.test.tsx
// Phase-4-owned NON-REGRESSION GUARD on the #38 behavior. LeagueView.tsx is
// Phase-5-owned (frozen this window); this test only ASSERTS its current truth
// and must stay green through the P5 reskin. It does NOT modify the file.
//
// Mock shape verified against LeagueView.tsx (LeagueData interface, lines 8-49):
//   - `directory` (NOT `clubs`): Array<{ club_id; name }>  — called unconditionally at line 118
//   - `dynasty_rankings`: required at line 67 (rankings[0] ?? null)
//   - `records`: required at line 88 (records.length)
//   - `hof`: required at line 98 (hof.length)
//   - `rivalries`: required at line 104 (rivalries[0] ?? null)
//   - `worlds`: optional Array<{ season_id; champion_club_id; champion_name;
//       runner_up_club_id; runner_up_name }> — NO final_match_id (inline type lines 42-48)
//   - useApiResource is called as useApiResource<LeagueData>('/api/history/league') (line 52)
//     → mock resolves for any URL (single call per render) so mockReturnValue is correct.
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockUseApiResource = vi.fn();
vi.mock('../../../hooks/useApiResource', () => ({
  useApiResource: (_url: string) => mockUseApiResource(_url),
}));

import { LeagueView } from './LeagueView';

const BASE_LEAGUE_DATA = {
  directory: [],
  dynasty_rankings: [],
  records: [],
  hof: [],
  rivalries: [],
};

beforeEach(() => mockUseApiResource.mockReset());

describe('LeagueView worlds roll (#38 guard — cross-phase lock)', () => {
  it('renders the World Championship roll only when worlds data exists', () => {
    mockUseApiResource.mockReturnValue({
      data: {
        ...BASE_LEAGUE_DATA,
        worlds: [
          {
            season_id: 'season_3',
            champion_club_id: 'c1',
            champion_name: 'Granite City Hammers',
            runner_up_club_id: 'c2',
            runner_up_name: 'Harbor Wolves',
            // NO final_match_id — not in LeagueData.worlds inline type (LeagueView.tsx:42-48)
          },
        ],
      },
      error: null,
      loading: false,
    });
    render(<LeagueView />);
    expect(screen.getByText('World Championship')).toBeInTheDocument();
    // runner_up clause present only when runner_up_name is set (LeagueView.tsx:145)
    expect(screen.getByText(/beat Harbor Wolves in the final/)).toBeInTheDocument();
  });

  it('does NOT render the worlds roll when worlds is empty', () => {
    mockUseApiResource.mockReturnValue({
      data: { ...BASE_LEAGUE_DATA, worlds: [] },
      error: null,
      loading: false,
    });
    render(<LeagueView />);
    expect(screen.queryByText('World Championship')).not.toBeInTheDocument();
  });

  it('does NOT render the worlds roll when worlds is absent (legacy saves)', () => {
    mockUseApiResource.mockReturnValue({
      data: { ...BASE_LEAGUE_DATA },
      error: null,
      loading: false,
    });
    render(<LeagueView />);
    expect(screen.queryByText('World Championship')).not.toBeInTheDocument();
  });
});
```

> **Verification note (mock shape):** The shape above was derived from `LeagueView.tsx` directly (lines 8-52, 67-75, 88, 98, 104, 118, 132). `directory` is the correct field name (line 9). `clubs` does NOT exist in `LeagueData`. `final_match_id` is not part of the `worlds` inline type (lines 42-48); it exists only in `WorldsHistoryEntry` in `types.ts`, which is a different type. The mock must not include it on the object literal or TypeScript's excess-property check will reject it. The `useApiResource` import depth `'../../../hooks/useApiResource'` matches line 2 of `LeagueView.tsx`. Do not edit `LeagueView.tsx`.

- [ ] **Step 2: Run to verify** — `cd frontend && npm run test -- "domain/seasonLabel" "LeagueView.worlds.guard"`. Expected: `seasonLabel` tests FAIL (module missing); the LeagueView guard PASSES against the current file (it locks existing truth). If the guard fails, reconcile the mock shape to the file's real reads (do not edit the file).

- [ ] **Step 3: Implement `seasonLabel.ts`**

```ts
// frontend/src/domain/seasonLabel.ts
// Single source of truth for season-label parsing, display, and ordering.
// Replaces the divergent dynasty/history/formatters.ts formatSeasonLabel +
// MyProgramView seasonTick string handling, and adds the NUMERIC comparator
// that fixes the season_10 < season_2 lexical-sort trap (audit §2.J #96).

const SEASON_RE = /^season_(\d+)$/i;

/** The integer season for `season_N` labels; null when not a numbered season. */
export function parseSeasonNumber(value: string | null | undefined): number | null {
  if (!value) return null;
  const m = value.trim().match(SEASON_RE);
  return m ? Number(m[1]) : null;
}

/** Display label. `season_N` → "Season N"; other tokens pass through humanized. */
export function formatSeasonLabel(value: string | null | undefined): string {
  if (!value) return 'Unknown season';
  const n = parseSeasonNumber(value);
  if (n !== null) return `Season ${n}`;
  return value
    .trim()
    .replaceAll('-', ' ')
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => (/^\d+$/.test(w) ? w : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()))
    .join(' ');
}

/** Ascending numeric comparator. Unparseable labels sort AFTER all numbered ones. */
export function compareSeasonAsc(a: string | null | undefined, b: string | null | undefined): number {
  const na = parseSeasonNumber(a);
  const nb = parseSeasonNumber(b);
  if (na === null && nb === null) return 0;
  if (na === null) return 1;
  if (nb === null) return -1;
  return na - nb;
}

/** Descending numeric comparator (latest season first). Unparseable labels last. */
export function compareSeasonDesc(a: string | null | undefined, b: string | null | undefined): number {
  const na = parseSeasonNumber(a);
  const nb = parseSeasonNumber(b);
  if (na === null && nb === null) return 0;
  if (na === null) return 1;
  if (nb === null) return -1;
  return nb - na;
}
```

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "domain/seasonLabel" "LeagueView.worlds.guard"`. Expected: PASS.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "domain/seasonLabel" "LeagueView.worlds.guard" && npm run build && npm run lint
git add frontend/src/domain/seasonLabel.* frontend/src/components/dynasty/history/LeagueView.worlds.guard.test.tsx
git commit -m "feat(domain): centralized season-label parse + numeric sort (#96); #38 worlds-roll guard"
```

---

## Phase 4B — PlayoffBracket reskin (frozen signature)

### Task 3: Reskin PlayoffBracket internals to CSS Modules (#16 preserved, signature FROZEN)

> **Why:** `standings/PlayoffBracket.tsx` is built from inline-style objects + literal hex (`#22d3ee`, `#94a3b8`, `#f43f5e`, the `min-width: 13rem` magic columns — audit §3 P2/P3 high) and the legacy `.playoff-bracket-*` / `.playoff-seed-chip` / `.playoff-champion-card` `index.css` families. Replace the styling substrate with `PlayoffBracket.module.css` while keeping the V20 `formatScoreline` branch (line 24-32) and the #16 player-outcome gating (lines 16-19) and EVERY data-* hook byte-for-byte. **Signature is frozen** (P6 imports it) — do not change the export, path, or props; do not change the `MatchCard` sub-component's prop shape (internal, but the JSX output's hooks are contract).

**Audit numbers + test strategy:** #16 vitest (Task 1 guards it) · §3 P2/P3 overflow fixes (use `Truncate` for team names so the flex item shrinks — kills the "min-width:0 missing" P2 finding; use `Grid` min-collapse for the bracket columns instead of `min-width: 13rem`).

**Constraints (repeat):** NO `index.css` edits. NO `ui.tsx` edits. `formatScoreline` import from `matchResult.ts` stays. Keep `data-testid="playoff-bracket"`, `data-player-outcome`, `data-testid="playoff-bracket-decided-by-chip"`, `data-decided-by`, the `aria-label="Playoff seeds"` ol, and the trophy `aria-hidden`. Token-only CSS (no raw hex; the gate doesn't scan this dir yet, so be disciplined).

**Files:** create `frontend/src/components/standings/PlayoffBracket.module.css`; modify `frontend/src/components/standings/PlayoffBracket.tsx`.

- [ ] **Step 1: Confirm Task 1 is green** — `cd frontend && npm run test -- "standings/PlayoffBracket"`. Expected: PASS (this is the guard the reskin must not break).

- [ ] **Step 2: Implement the module CSS** — token-driven; map the inline winner/outcome colors to token classes:
  - `.panel`, `.header`, `.kicker`, `.title`
  - `.seeds` (ol, list-style none, flex-wrap), `.seedChip`, `.seedChipUser`
  - `.grid` — use the Phase-0 `Grid` primitive (`min="13rem"`) OR a module class with `grid-template-columns: repeat(auto-fill, minmax(min(13rem,100%),1fr))` so columns collapse on narrow widths instead of overflowing (kills P3). Prefer the `Grid` primitive import from `../../ui`.
  - `.column`, `.roundLabel`, `.empty`
  - `.card`, `.cardOutcomeAdvanced` (border `var(--ok)`), `.cardOutcomeEliminated` (border `var(--volt)`), `.cardNeutral` (border `var(--line)`)
  - `.matchLabel`, `.upcoming` (`var(--gold)`)
  - `.ribbon`, `.ribbonAdvanced` (`var(--ok)` bg), `.ribbonEliminated` (`var(--volt)` bg)
  - `.decidedChip` (accent bg)
  - `.teamRow`, `.teamRowWinner` (winner highlight via `var(--ok-soft)` / `var(--text)`), `.teamName` (uses `Truncate`), `.teamValue` (tabular-nums)
  - `.note`
  - `.championCard`, `.championCardUser`, `.trophy`

- [ ] **Step 3: Reskin the component** — replace each `style={{…}}` with `className={styles.*}` (and `Truncate` for the team name span). The branch logic, the `formatScoreline({...})` call (PlayoffBracket.tsx:24-32), the `playerAdvanced`/`playerEliminated`/`showNote` derivations (16-20), the `data-player-outcome={playerAdvanced ? 'advanced' : playerEliminated ? 'eliminated' : undefined}` attribute, and every `data-testid`/`data-decided-by`/`aria-*` attribute stay verbatim. Keep `import { formatScoreline } from '../match-week/matchResult';` and `import type { PlayoffBracketResponse, PlayoffBracketMatch } from '../../types';`. Add `import styles from './PlayoffBracket.module.css';` and `import { Truncate, Grid } from '../../ui';`.

  Example shape for `teamRow` (the load-bearing winner branch + the anti-strip-adjacent value):

```tsx
const teamRow = (clubId: string, name: string, value: number | null) => {
  const isWinner = played && match.winner_club_id === clubId;
  return (
    <div key={clubId} className={`${styles.teamRow} ${isWinner ? styles.teamRowWinner : ''}`.trim()}>
      <Truncate className={styles.teamName} title={name}>{name}</Truncate>
      <span className={styles.teamValue}>{value ?? '–'}</span>
    </div>
  );
};
```

- [ ] **Step 4: Run the guard + build + lint** — `cd frontend && npm run test -- "standings/PlayoffBracket" "PlayoffBracket.contract" && npm run build && npm run lint && npm run lint:tokens`. Expected: PASS (Task-1 behavior intact; the Phase-1 contract test still passes → signature unchanged; lint:tokens green on already-scanned dirs).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/standings/PlayoffBracket.tsx frontend/src/components/standings/PlayoffBracket.module.css
git commit -m "feat(standings): reskin PlayoffBracket internals to CSS Modules (signature frozen; #16 + data-* intact)"
```

---

## Phase 4C — LeagueContext (Standings) reskin

### Task 4: Lock Standings table behaviors (#6 GP/Survivor diff, #7 Plan badge, #15 draw) — RED-first

> **Why:** Before reskinning the big `Standings` screen, lock the V20 diff-column branch (#6: 'GP Diff' vs 'Survivor Diff' header + the `diffOf` value that branches on `is_official_career`), the Plan-badge vocabulary (#7: `approachToneClass`/`normalizeApproach` map Balanced/Aggressive/Control/Defensive/Develop Youth), and the wire draw handling (#15: `winner_name==='Draw'` → "Draw"; unparseable summary → raw fallback, never dropped). Author against the CURRENT `Standings` so they pass on existing markup, then the reskin (Task 6) keeps them green. Also lock the `data-screen-label="04 Standings"` anti-strip hook.

**Audit numbers + test strategy:** #6 vitest · #7 vitest · #15 vitest · anti-strip vitest (`data-screen-label`).

**Mocking approach (verified):** `Standings` uses `useApiResource('/api/standings')` for `data` and `useApiResource('/api/playoffs/bracket')` for `bracket` (`LeagueContext.tsx:314-315`). Mock `../hooks/useApiResource` to return per-URL payloads. `ProgramModal`, `PlayoffBracket`, `TermTip`, `EmptyState` are real children — keep them, or stub `PlayoffBracket`/`ProgramModal` to lightweight divs so the test exercises `Standings`' own logic. `StatusMessage` comes from `./ui` (the shim after Task 6's import re-point; before that, from `./ui` barrel which already re-exports it — verify the current import resolves in the test).

**Files:** create `frontend/src/components/LeagueContext.test.tsx`.

- [ ] **Step 1: Write the failing/locking tests**

```tsx
// frontend/src/components/LeagueContext.test.tsx
import { render, screen, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { StandingsResponse, StandingRow, DivisionStandingsBlock } from '../types';

const mockUseApiResource = vi.fn();
vi.mock('../hooks/useApiResource', () => ({
  useApiResource: (url: string) => mockUseApiResource(url),
}));
// Keep Standings' own logic in scope; stub the heavy children.
vi.mock('./standings/PlayoffBracket', () => ({ PlayoffBracket: () => <div data-testid="stub-bracket" /> }));
vi.mock('./dynasty/history/ProgramModal', () => ({ ProgramModal: () => <div data-testid="stub-modal" /> }));

import { Standings } from './LeagueContext';

const row = (over: Partial<StandingRow>): StandingRow => ({
  club_id: 'c', club_name: 'Club', wins: 3, losses: 1, draws: 0, points: 9,
  elimination_differential: 5, game_point_differential: 7, is_user_club: false,
  latest_approach: 'Balanced', ...over,
});

function standings(over: Partial<StandingsResponse> = {}): StandingsResponse {
  return {
    season_id: 'season_1',
    standings: [
      row({ club_id: 'you', club_name: 'Granite City Hammers', is_user_club: true, latest_approach: 'Aggressive' }),
      row({ club_id: 'them', club_name: 'Harbor Wolves' }),
    ],
    total_weeks: 12, current_week: 5, playoff_spots: 4,
    is_official_career: true,
    recent_matches: [],
    ...over,
  };
}

// pyramidDivisions: two DivisionStandingsBlock entries so data.divisions.length > 1
// triggers the PyramidPanel render (LeagueContext.tsx:667). The first entry carries
// game_point_differential: 10 and elimination_differential: 3 so both diff-branch
// assertions are non-tautological.
const MOVEMENT: DivisionStandingsBlock['movement'] = {
  auto_promotion: false, promotion_playoff: false, relegation_count: 0, worlds_slots: 1, summary: '',
};
const pyramidDivisions: DivisionStandingsBlock[] = [
  {
    division_id: 'd1', name: 'Premier', short_name: 'PRM', tier: 1, kind: 'league',
    is_user_division: true,
    movement: MOVEMENT,
    standings: [row({ club_id: 'you', club_name: 'Granite City Hammers', is_user_club: true,
      game_point_differential: 10, elimination_differential: 3 })],
  },
  {
    division_id: 'd2', name: 'Circuit', short_name: 'CRC', tier: 2, kind: 'league',
    is_user_division: false,
    movement: MOVEMENT,
    standings: [row({ club_id: 'ai', club_name: 'Harbor Wolves',
      game_point_differential: 5, elimination_differential: 2 })],
  },
];

function mountWith(data: StandingsResponse, bracket: unknown = { active: false }) {
  mockUseApiResource.mockImplementation((url: string) => {
    if (url === '/api/standings') return { data, error: null, loading: false };
    if (url === '/api/playoffs/bracket') return { data: bracket, error: null, loading: false };
    return { data: null, error: null, loading: false };
  });
  return render(<Standings />);
}

beforeEach(() => mockUseApiResource.mockReset());

describe('Standings (Phase 4 — #6/#7/#15 + anti-strip)', () => {
  it('anti-strip: keeps the data-screen-label hook', () => {
    const { container } = mountWith(standings());
    expect(container.querySelector('[data-screen-label="04 Standings"]')).not.toBeNull();
  });

  it('#6: official career → "GP Diff" header', () => {
    mountWith(standings({ is_official_career: true }));
    expect(screen.getByText('GP Diff')).toBeInTheDocument();
    expect(screen.queryByText('Survivor Diff')).not.toBeInTheDocument();
  });

  it('#6: legacy career → "Survivor Diff" header', () => {
    mountWith(standings({ is_official_career: false }));
    expect(screen.getByText('Survivor Diff')).toBeInTheDocument();
    expect(screen.queryByText('GP Diff')).not.toBeInTheDocument();
  });

  it('#6 Pyramid: official career → PyramidPanel uses game_point_differential in diff note', () => {
    // PyramidPanel renders when data.divisions && data.divisions.length > 1 (line 667).
    // It formats: "{W}-{L}-{D} · {pts} pts · {formatDiff(isOfficial ? gp_diff : elim_diff)} diff"
    // With game_point_differential: 10 → "+10 diff" (LeagueContext.tsx:297).
    mountWith(standings({ is_official_career: true, divisions: pyramidDivisions }));
    expect(screen.getByText(/\+10 diff/)).toBeInTheDocument();
  });

  it('#6 Pyramid: legacy career → PyramidPanel uses elimination_differential in diff note', () => {
    // With elimination_differential: 3 → "+3 diff" when is_official_career: false.
    mountWith(standings({ is_official_career: false, divisions: pyramidDivisions }));
    expect(screen.getByText(/\+3 diff/)).toBeInTheDocument();
  });

  it('#7: Plan badge renders the command-center vocabulary', () => {
    mountWith(standings());
    // user row is Aggressive; opponent Balanced
    expect(screen.getAllByText('Aggressive').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Balanced').length).toBeGreaterThan(0);
  });

  it('#15: draw in the wire shows "Draw", does not fabricate a win', () => {
    mountWith(standings({
      recent_matches: [
        { match_id: 'm1', week: 3, summary: 'Granite City Hammers 0-0 Harbor Wolves', winner_name: 'Draw' },
      ],
    }));
    expect(screen.getByText('Draw')).toBeInTheDocument();
  });

  it('#15: unparseable summary falls back to raw text, never dropped', () => {
    mountWith(standings({
      recent_matches: [
        { match_id: 'm2', week: 4, summary: 'Bye week — no match', winner_name: '' },
      ],
    }));
    expect(screen.getByText(/Bye week — no match/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "LeagueContext"`. Expected: PASS against the current `Standings`. Reconcile any assertion to the CURRENT rendered truth if it fails (these guard existing behavior). Confirm the `useApiResource` mock path (`../hooks/useApiResource`) matches the import in `LeagueContext.tsx:3`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LeagueContext.test.tsx
git commit -m "test(standings): lock #6 GP/Survivor diff, #7 Plan badge, #15 draw + data-screen-label before reskin"
```

---

### Task 5: Lock Standings phase-aware copy (#33 tiebreaker states, #34 race/need) — RED-first

> **Why:** #33 — the Tiebreaker Read panel has three states (`hidden` during offseason/playoffs; `soft` at week ≤1 or all-zero points; `live` otherwise), each driven by `LeagueContext.tsx:379-384` and rendering distinct `EmptyState`/list bodies (615-628). #34 — the race summary + "This Week's Target" need-copy suppress regular-season math during playoffs/offseason and substitute phase copy (`LeagueContext.tsx:346-367`). Lock both against the current screen before the reskin moves the markup.

**Audit numbers + test strategy:** #33 vitest · #34 vitest.

**Files:** extend `frontend/src/components/LeagueContext.test.tsx`.

- [ ] **Step 1: Add the failing/locking cases** (reuse the `mountWith`/`standings` helpers from Task 4):

```tsx
describe('Standings phase-aware copy (#33 tiebreaker, #34 race/need)', () => {
  it('#33: tiebreaker SOFT at week 1 (race not yet meaningful)', () => {
    mountWith(standings({ current_week: 1 }));
    expect(screen.getByText('Race Developing')).toBeInTheDocument();
    expect(screen.getByText('Race not yet meaningful')).toBeInTheDocument();
  });

  it('#33: tiebreaker HIDDEN in the offseason', () => {
    mountWith(standings({ is_offseason: true }));
    expect(screen.getByText('Race Concluded')).toBeInTheDocument();
    expect(screen.getByText('Season concluded')).toBeInTheDocument();
  });

  it('#33: tiebreaker LIVE mid-season with points on the board', () => {
    mountWith(standings({ current_week: 6 }));
    expect(screen.getByText(/Race$/)).toBeInTheDocument(); // "Top N Race"
  });

  it('#34: offseason replaces race/need copy with concluded-season phrasing', () => {
    mountWith(standings({ is_offseason: true }));
    expect(screen.getByText('SEASON CONCLUDED')).toBeInTheDocument();
    expect(screen.getByText('Season Concluded')).toBeInTheDocument();
  });

  it('#34: when playoffs are live, the bracket-decides copy replaces regular-season math', () => {
    mountWith(standings({ current_week: 12 }), { active: true });
    expect(screen.getByText('PLAYOFFS LIVE')).toBeInTheDocument();
    expect(screen.getByText('Bracket Decides')).toBeInTheDocument();
  });
});
```

> **String sources (verified against `LeagueContext.tsx`):**
> - `'Race Developing'` → tiebreaker panel `<h3>` when `tiebreakerState === 'soft'` (line 610)
> - `'Race not yet meaningful'` → `EmptyState title` when `tiebreakerState === 'soft'` (line 626)
> - `'Race Concluded'` → tiebreaker panel `<h3>` when `tiebreakerState === 'hidden'` (line 609)
> - `'Season concluded'` (lowercase 'c') → `EmptyState title` when `isOffseason` (line 617) — rendered in `<strong>` by `EmptyState`
> - `/Race$/` → matches `Top ${playoffLine} Race` (line 612); the default fixture has `playoff_spots: 4` so it renders "Top 4 Race"
> - `'SEASON CONCLUDED'` → `raceSummary.left` (line 351) — rendered in a `<span>` in the glance cell
> - `'Season Concluded'` (uppercase 'C') → `needCopy.action` (line 357) — rendered in `.need-action` span
> - `'PLAYOFFS LIVE'` → `raceSummary.right` when `playoffsActive` (line 353)
> - `'Bracket Decides'` → `needCopy.outcome` when `playoffsActive` (line 364)
>
> **`is_offseason` type note:** `StandingsResponse.is_offseason` is `is_offseason?: boolean` (types.ts:471). Passing `is_offseason: true` in the `standings()` override is valid and the `standings()` helper's spread accepts it — no separate mock type change is needed.

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "LeagueContext"`. Expected: PASS against current `Standings`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LeagueContext.test.tsx
git commit -m "test(standings): lock #33 tiebreaker states + #34 phase-aware race/need copy"
```

---

### Task 6: Reskin Standings + extract PyramidPanel to CSS Modules (#6/#7/#15/#33/#34 preserved)

> **Why:** `LeagueContext.tsx` mixes the legacy `index.css` `.ls-*` families with inline-style objects (the PyramidPanel tablist `style={{display:'flex',gap:'0.4rem',…}}` 246-261, the wire ticker inline flex 590-597, the `var(--dm-rose)` inline diff color 420, the DiffBar `calc(50% - …)` 86-89 — audit §3 P1/P2/P10). Replace the styling substrate with `LeagueContext.module.css` (+ `PyramidPanel.module.css`), extract `PyramidPanel` into its own file `standings/PyramidPanel.tsx`, and re-point `StatusMessage` to the `src/ui` shim. ALL branch logic (the `diffOf`/`isOfficial` differential, `approachToneClass`, `parseMatchSummary` fallback, `tiebreakerState`, `raceSummary`/`needCopy`) and EVERY `data-*`/`aria-*`/`role` attribute stay verbatim. Consume `seasonLabel` from `domain/seasonLabel.ts` anywhere a season is labeled/ordered (there is no season sort in the current standings list, but the season_id label uses it if surfaced — keep behavior identical; do not add new sorting that changes output).

**Audit numbers + test strategy:** #6/#7/#15/#33/#34 vitest (Tasks 4-5 guard them).

**Constraints (repeat):** NO `index.css` edits. NO `ui.tsx` edits — re-point `import { StatusMessage } from './ui'` (LeagueContext.tsx:4) to the barrel `from './ui'` shim path used elsewhere (verify the barrel `src/ui/index.ts` exports `StatusMessage` after Phase 1 Task 1; if the current `./ui` already resolves to `components/ui.tsx`, switch to the Phase-1 `../ui`-relative shim barrel — the import path is the ONLY change). Keep `ProgramModal` call `{ clubId, clubName, onClose }` verbatim (frozen P5 signature). Keep `TermTip`/`EmptyState`/`CLUB_ARCHETYPE_TERM` imports from `'../legibility'` unchanged (frozen). Token-only CSS.

**Files:** create `frontend/src/components/LeagueContext.module.css`, `frontend/src/components/standings/PyramidPanel.tsx`, `frontend/src/components/standings/PyramidPanel.module.css`; modify `frontend/src/components/LeagueContext.tsx`.

- [ ] **Step 1: Confirm the guards are green** — `cd frontend && npm run test -- "LeagueContext"`. Expected: PASS (Tasks 4-5).

- [ ] **Step 2: Extract `PyramidPanel`** — move the `PyramidPanel` component (LeagueContext.tsx:225-311) into `standings/PyramidPanel.tsx` as a named export `export function PyramidPanel(props)` with the SAME prop shape `{ divisions: DivisionStandingsBlock[]; isOfficial: boolean; onClubClick: (clubId: string, clubName: string) => void }`. Import it back into `LeagueContext.tsx` (`import { PyramidPanel } from './standings/PyramidPanel';`). It is an internal component (NOT a frozen public contract) — the extraction is allowed. Reskin its inline styles to `PyramidPanel.module.css`. Preserve the `role="tablist"`/`role="tab"`/`aria-selected`, the `ls-tb-row` `role="button"`/`tabIndex`/`aria-label` + `onKeyDown`, the `DROP` relegation badge gating, and the `formatDiff(isOfficial ? game_point_differential : elimination_differential)` branch (the #6 family on the pyramid, audit §2.A #6 "Pyramid 296-298") verbatim.

  > **#6 Pyramid unit test (REQUIRED after extraction):** The Task 4 `LeagueContext.test.tsx` tests the pyramid diff branch through `Standings` while PyramidPanel is still inline. After extraction, add `frontend/src/components/standings/PyramidPanel.test.tsx` with two direct unit tests (same `pyramidDivisions` fixture, `is_official_career` toggled) so the #6 Pyramid branch is tested against the extracted module and not only through the `Standings` wrapper. This closes the gap where an incorrect `isOfficial` prop propagation at the `LeagueContext.tsx:668-671` call site would not be caught by the inner unit alone. The file is `standings/PyramidPanel.test.tsx`; add it to the Step 5 gate run and the Step 6 commit.

- [ ] **Step 3: Implement the module CSS** — `LeagueContext.module.css` (`.shell`, `.glance`, `.glanceCell`, `.glanceRank`/`Record`/`Race`/`Next`, `.rankRow`, `.recordRow`, `.diff`, `.diffNeg` (replaces the inline `var(--dm-rose)`), `.race`, `.racePip` + `.in`/`.out`/`.us`, `.cushion`, `.needRow`/`.needArrow`/`.needOutcome`/`.needHelper`, `.tableCard`, `.tableHead`, `.tableMeta`, `.tableScroll`, `.table`, `.cutRow`, `.rank` + `.in`/`.out`, `.club`, `.clubName` (use `Truncate`), `.cellNum` + `.muted`/`.pts`, `.diffCell`/`.diffBar`/`.axis`/`.fill` + `.pos`/`.neg`, `.tableFoot`, `.legend*`, `.side`, `.panel`, `.panelHead`, `.wireTicker`, `.wireItem` + `.isUs`/`.isHeadline`, `.wireWk`/`.wireScore`/`.wireYou`, `.tbList`, `.tbRow`, `.tbFrom`/`.tbBody`/`.tbWho`/`.tbNote`/`.tbRisk` + `.riskLow`/`.riskHigh`). Map the `dm-badge dm-badge-cyan/violet/emerald/amber/slate` Plan-badge tones to module classes OR keep the `dm-badge` class names on the element (so they consume the untouched `index.css` `.dm-badge*` rules until P8) — prefer keeping `dm-badge` class names for the badges (matches the PlayoffBracket strategy of leaving `dm-action` alone) so #7's vocabulary tone mapping (`approachToneClass`) is unchanged; add a module wrapper class only for layout. The `DiffBar` `left`/`width` percentages stay inline computed values (runtime data, not literals) — that is allowed; only the static colors move to tokens.

- [ ] **Step 4: Reskin `Standings`** — replace each `className="ls-*"`/inline `style` with `className={styles.*}` and `Truncate` for the club-name cell. Re-point the `StatusMessage` import. Keep the `data-screen-label="04 Standings"` attribute, the `aria-haspopup="dialog"` + `aria-label={`Open ${club} program history`}` on rows, the wire `role="list"`/`aria-label`, the cut-line `colSpan={8}`, the `TermTip term={isOfficial ? 'standings.gp_diff' : 'standings.diff'}` header (the #6 hook), and the `ProgramModal` render verbatim. Add `import styles from './LeagueContext.module.css';` and `import { Truncate } from '../ui';`.

- [ ] **Step 5: Run the guards + build + lint** — `cd frontend && npm run test -- "LeagueContext" "standings/PlayoffBracket" "standings/PyramidPanel" && npm run build && npm run lint && npm run lint:tokens`. Expected: PASS (Tasks 4-5 behavior intact; PlayoffBracket guard still green; new PyramidPanel unit tests green; build + lint clean; lint:tokens green on scanned dirs).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/LeagueContext.tsx frontend/src/components/LeagueContext.module.css frontend/src/components/standings/PyramidPanel.tsx frontend/src/components/standings/PyramidPanel.module.css frontend/src/components/standings/PyramidPanel.test.tsx
git commit -m "feat(standings): reskin Standings + extract PyramidPanel to CSS Modules (#6/#7/#15/#33/#34 + data-* intact)"
```

---

## Phase 4D — Phase gate

### Task 7: Phase-4 worktree gate — full verification + token self-scan

> **Why:** Prove the whole phase is green on the worktree (with the OLD `index.css` still present) before the controller hands off to the serial integrator. The integrator later runs the `index.css` deletion + SCAN_DIRS append + full `tsc --noEmit`/vitest in STEP 3.

- [ ] **Step 1: Run the complete worktree gate**

```bash
cd frontend && npm run test && npm run build && npm run lint && npm run lint:tokens
cd .. && npm run e2e -- tests/e2e/maximized-playthrough-qa.spec.ts
```

Expected: full FE suite green (including the new `domain/seasonLabel`, `standings/PlayoffBracket`, `LeagueContext`, `LeagueView.worlds.guard` tests + the Phase-1 `PlayoffBracket.contract`/`ProgramModal.contract` tests); build clean; eslint clean; token gate clean on the currently-scanned dirs; e2e smoke green.

- [ ] **Step 2: Token self-scan the new dir** (the gate does not yet scan it — integrator appends it in STEP 3). Run the gate logic manually against the standings files to confirm they will pass once appended:

```bash
cd frontend && node -e "import('./scripts/check-tokens.mjs')" 2>/dev/null || true
# Manual scan: grep the new modules for raw hex / disallowed px and confirm none.
```

Use Grep for `#[0-9a-fA-F]{3,8}` and `[2-9][0-9]*px` across `src/components/standings/*.module.css`, `src/components/LeagueContext.module.css`, `src/components/standings/PlayoffBracket.tsx`, `src/components/LeagueContext.tsx`. Expected: zero raw hex; only `var(--…)` tokens and `0`/`1px` hairlines. Fix any literal inline.

- [ ] **Step 3: Confirm the freezes were respected** — verify (via `git diff --stat` against the merge-base) that this branch touched ONLY: `domain/seasonLabel.*`, `components/standings/*`, `components/LeagueContext.*`, and the `LeagueView.worlds.guard.test.tsx` file. Confirm NO change to `index.css`, `components/ui.tsx`, `match-week/matchResult.ts`, `legibility/*`, `dynasty/history/ProgramModal.tsx`, `dynasty/history/LeagueView.tsx` (the guard is a NEW file, not an edit), `dynasty/history/formatters.ts`, `scripts/check-tokens.mjs`.

- [ ] **Step 4: Hand off to the controller** — do NOT commit a merge or edit `index.css`. The controller commits; the integrator (STEP 3) does the legacy-selector deletion + SCAN_DIRS append + full re-gate.

```bash
git status   # confirm a clean tree of only the Phase-4 files
```

---

## Self-Review

**Behavior coverage (all 8 assigned behaviors mapped to a task with its checklist test strategy):**
- #6 (GP/Survivor diff column + header branch, incl. Pyramid) → Task 4 (header + Pyramid diff branch via `pyramidDivisions` fixture) + Task 6 (Step 2 `PyramidPanel.test.tsx` unit test after extraction) — vitest ✓ (Pyramid branch now has non-tautological assertions independent from the header; neither branch is tautological)
- #7 (Plan badge command-center vocabulary) → Task 4 — vitest ✓
- #15 (draw label + unparseable-summary raw fallback) → Task 4 — vitest ✓
- #16 (player-outcome ribbon gating + data-player-outcome) → Task 1 (lock) + Task 3 (reskin preserves) — vitest ✓
- #33 (tiebreaker three states) → Task 5 — vitest ✓
- #34 (phase-aware race/need copy) → Task 5 — vitest ✓
- #38 (worlds roll only when data exists) → Task 2 cross-phase guard — vitest ✓
- #96 (centralized season parse + numeric sort) → Task 2 `domain/seasonLabel.ts` — vitest ✓

**Phase-specific requirements encoded:**
- PlayoffBracket signature FROZEN (P6 ChampionReveal imports it) → Task 3 rebuilds internals only; Step 4 re-runs the Phase-1 `PlayoffBracket.contract` test as the freeze proof; export name/path/props unchanged ✓
- `matchResult.ts` frozen → Task 3 keeps `import { formatScoreline }` as-is, no relocation/re-impl ✓
- `ProgramModal` (P5) frozen → Task 6 keeps the `{ clubId, clubName, onClose }` call verbatim ✓
- #6/#7 = GP-Diff vs Survivor-Diff branch on `scoring_model`/`is_official_career` → Task 4 header + Task 6 `diffOf` preserved ✓
- `data-player-outcome` on PlayoffBracket → Task 1 locks it, Task 3 preserves it ✓
- #96 centralized numeric sort in a `formatters`-style module → Task 2 `domain/seasonLabel.ts` ✓

**Hard-rule (freeze) coverage:**
- NO index.css edits/deletions → stated in Hard Rules §1, repeated in Tasks 3/6, verified in Task 7 Step 3; CREATE *.module.css only ✓
- NO ui.tsx edits → Task 6 re-points `StatusMessage` import path only (no API remap) ✓
- legibility/* frozen → Tasks 3/6 keep `TermTip`/`EmptyState`/`CLUB_ARCHETYPE_TERM` imports unchanged ✓
- command-action-bar/command-policy-overlay shared globals → not on these screens; "never delete" noted ✓
- check-tokens.mjs integrator-owned → Hard Rule §3 + token-gate caveat + Task 7 manual self-scan ✓
- data-* anti-strip HARD RED preconditions → enumerated (data-player-outcome, playoff-bracket testids, data-decided-by, data-screen-label) and tested in Tasks 1/3/4/6 ✓
- Per-phase gate (test+build+lint+lint:tokens+e2e smoke, OLD index.css present) → Task 7 ✓

**Placeholder scan:** none. Every code step contains complete code; the two "Read/verify the file before finalizing the mock" notes (Task 2 LeagueView shape, Task 4/5 exact copy strings) are correctness guards against inventing fields/strings, not logic placeholders — they instruct verification against verified source lines.

**Type/name consistency:**
- `PlayoffBracketResponse`/`PlayoffBracketMatch`/`StandingsResponse`/`StandingRow`/`DivisionStandingsBlock` used exactly as declared in `types.ts` (verified lines 445-581).
- `DivisionStandingsBlock` is now imported in `LeagueContext.test.tsx` (added to the type import line alongside `StandingsResponse`/`StandingRow`) so the `pyramidDivisions` helper is typed correctly. `DivisionMovementRules` is accessed via `DivisionStandingsBlock['movement']` to avoid a second import.
- `LeagueData` (from `LeagueView.tsx`) requires `directory` (not `clubs`), `dynasty_rankings`, `records`, `hof`, `rivalries` — all provided in the Task 2 guard mock via `BASE_LEAGUE_DATA`. `worlds` inline type (lines 42-48) has NO `final_match_id`; the mock omits it.
- `seasonLabel.ts` exports `parseSeasonNumber`/`formatSeasonLabel`/`compareSeasonAsc`/`compareSeasonDesc` — names match the test and the prose.
- `PyramidPanel` prop shape `{ divisions; isOfficial; onClubClick }` matches the current inline component (LeagueContext.tsx:225-233) and the re-import.
- `useApiResource` mock returns `{ data, error, loading }` — matches the hook's real return (`useApiResource.ts:31` returns `{ data, loading, error, setData, setError, setLoading }`; tests read only `data/error/loading`, which is safe).
- `formatScoreline` import path `'../match-week/matchResult'` and `StatusMessage`/`Truncate`/`Grid` from the `src/ui` barrel match the Phase-0/Phase-1 exports.

**Judgment calls (recorded):**
1. **#38 is cross-phase.** Its surface (`LeagueView.tsx`) is Phase-5-owned and frozen this window, but the checklist assigns the behavior to Phase 4. Resolution: Phase 4 delivers the shared `formatSeasonLabel` the worlds roll consumes + a NON-MUTATING guard vitest that locks the "render only when worlds data exists / runner-up only when present" truth against the current file. This keeps #38 green without violating the P5 freeze; P5's reskin must keep the guard green. (Alternative — deferring #38 entirely to P5 — was rejected because the checklist binds it to P4's done-criteria.)
2. **New `domain/seasonLabel.ts` instead of editing `dynasty/history/formatters.ts`.** The history `formatters.ts` is P5-owned/frozen, so #96's centralized helper goes in the shared `src/domain/` dir (the convention Phase 0 set with `tiers.ts`). Output is byte-identical to the existing `season_N → "Season N"` rule so P5 can re-point as a drop-in later. This avoids a single-writer collision while still giving #96 one canonical source.
3. **PyramidPanel extracted to its own file.** It is an internal (non-frozen) component; extracting it keeps `LeagueContext.tsx` from re-growing and gives the Pyramid its own module CSS. The prop shape is preserved exactly, so the move is behavior-neutral. A `PyramidPanel.test.tsx` is added in Task 6 Step 2 (immediately after extraction) so the #6 Pyramid diff branch has a direct unit test on the extracted file — not only through the `Standings` wrapper.
4. **Plan badges keep their `dm-badge*` class names** (consume untouched `index.css` until P8) rather than re-implementing the tone palette in module CSS — mirrors the strategy's `ActionButton`-keeps-`dm-action` pattern and keeps #7's `approachToneClass` mapping untouched. Layout-only module wrappers are added around them.
5. **`vi.mock('./dynasty/history/ProgramModal', ...)` mock path in `LeagueContext.test.tsx` is correct.** Both `LeagueContext.tsx` and `LeagueContext.test.tsx` live in `src/components/`. Vitest resolves module mock paths relative to the test file. The test-relative path `./dynasty/history/ProgramModal` resolves to the same module that `LeagueContext.tsx:6` imports via the same relative path — so the mock intercepts cleanly. Worker should confirm on first Step 2 gate run (if `stub-modal` renders the mock is active).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-floodlight-phase-4-standings.md`. This is a CONCURRENT (STEP 2) worktree phase: execute task-by-task in an isolated worktree off the merged post-Phase-1 trunk, run the Task-7 gate, then hand the clean branch to the controller. Do NOT commit a merge or touch `index.css` — the serial integrator (STEP 3) owns the legacy-selector deletion, the SCAN_DIRS append, and the full cross-phase re-gate.
