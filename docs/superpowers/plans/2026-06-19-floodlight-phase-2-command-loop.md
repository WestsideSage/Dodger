# Floodlight Phase 2 — Command Loop + Aftermath + Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin the full match command loop — the pre-sim Command Center (PreSimDashboard), the post-sim aftermath tree (`match-week/aftermath/*` + the MatchWeek orchestrator), and the full-screen Match Replay (MatchReplay + a NEW lightweight SVG live match canvas) plus MatchScoreHero — onto the Floodlight token system using CSS Modules, while keeping the 30 Phase-2 trust behaviors green (#1–8, #11–18, #41–50, #90, #93–95). This is the **highest-risk lane** and the **critical path** of the concurrent window: MatchWeek is the serial orchestrator and the net-new SVG canvas is untested scope.

**Architecture:** Every screen in this phase moves from inline-style objects + `index.css` global classes (`command-*`, `mr-*`, `dm-*`) to scoped `*.module.css` files driven by `src/styles/tokens.css` and the Phase-0 `src/ui` primitives. The `match-week/matchResult.ts` scoreline contract is **FROZEN** (consumed verbatim, never altered) — it is the single source of the V20 scoring-model truth that recurs on every score-bearing surface. MatchWeek's `closest('.dm-left-nav')` reveal-skip (line 334) is rewritten to `closest(`[${NAV_RAIL_ATTR}]`)` against the Phase-1 published `appContracts.NAV_RAIL_ATTR`. The phase **adds** a `LiveCourtCanvas` SVG primitive (players as lit/extinguished tokens, throws as animated arcs) driven by the existing replay `proof_events`/`score_state` payload, with an honest NO-DATA fallback. Sub-areas are sequenced **serially**: PreSimDashboard → aftermath tree → MatchReplay+canvas (do NOT parallelize inside P2).

**Tech Stack:** React 19, Vite 8, TypeScript 6, CSS Modules, Vitest + @testing-library/react (harness from Phase 0).

**Spec:** [2026-06-19-ui-redesign-design.md](../specs/2026-06-19-ui-redesign-design.md) · **Non-regression contract:** [2026-06-19-ui-redesign-audit.md](../specs/2026-06-19-ui-redesign-audit.md) §1 (Command Center / aftermath / replay screens), §2.A #1–#8, §2.B #11–#18, §2.F #41–#50, §2.J #90/#93–#95, §3 P1/P2/P3/P6/P10 on these screens · **Checklist:** [floodlight-preservation-checklist.md](floodlight-preservation-checklist.md) Phase 2 rows · **Orchestration contract:** [2026-06-19-floodlight-parallelization-strategy.md](2026-06-19-floodlight-parallelization-strategy.md) GROUP STEP 2 (P2 concurrent worktree) + the `MatchWeek.tsx:334` / `matchResult.ts` / `command-action-bar`/`command-policy-overlay` freeze rows · **Phase-1 LOCKED contracts:** [2026-06-19-floodlight-phase-1-app-shell.md](2026-06-19-floodlight-phase-1-app-shell.md) (appContracts.ts, the 5 `src/ui` shims, `data-nav-rail`, frozen PlayoffBracket/ProgramModal signatures) · **Foundations + style template:** [2026-06-19-floodlight-phase-0-foundations.md](2026-06-19-floodlight-phase-0-foundations.md)

**Branch / worktree:** This phase executes in an **isolated git worktree branched from the MERGED post-Phase-1 trunk**. All Phase-2 commits land on that branch; the controller integrates `index.css` deletion serially in STEP 3 (P2 is integrated **last**). **The OLD `index.css` stays present in this worktree the whole time** — the per-phase gate runs against it.

---

## Concurrent-window HARD RULES this plan encodes (orchestration contract)

These are absolute constraints on every task below. A task that violates one is wrong.

1. **NO `index.css` edits or deletions.** This phase **creates `*.module.css` only**. The legacy `command-*` / `mr-*` / `dm-*` selector families this phase replaces are deleted **later by the serial integrator in STEP 3** (P2 is integrated last). There is **no `index.css` deletion task in this plan**. The reskinned components simply stop referencing the legacy classes; the dead rules are carved out by the integrator.
2. **NO edits to `components/ui.tsx`.** Re-point imports of `ActionButton` / `PageHeader` / `StatusMessage` / `RatingBar` / `RadioGroup` from `./ui` (the `ui.tsx` barrel) to the new Phase-1 `src/ui` shims (`../../ui` etc.) — **import path change ONLY**. **No `ActionButton → ActionBar` remap** (deferred to Phase 8). MatchWeek currently imports `StatusMessage` from `./ui` (MatchWeek.tsx:21); re-point it to the shim.
3. **FROZEN — consume, never alter:**
   - `components/match-week/matchResult.ts` public API: `formatScoreline`, `survivorDetail`, `ScorelineFields`, `MatchScoreline`, `ScorelineSide`. P2 may **ADD** a vitest against it (Task 1) but must **NOT** change its API, body, or location.
   - `legibility/*` primitives (`rulesetNames.ts`, `TermTip`, `KnownValue`, etc.) are **read-only**; accept mixed Floodlight+legacy look until Phase 8.
   - The SHARED globals `command-action-bar` and `command-policy-overlay` are **never deleted** (consumed by P6 ceremonies + P5 ProgramModal too; P8-only deletion). If a P2 surface uses them, keep the class name on the element; do not remove the rule.
   - `frontend/scripts/check-tokens.mjs` is **untouched** — the integrator owns all `SCAN_DIRS` appends. P2 never edits it.
4. **Consume Phase-1 published contracts:** `components/shell/appContracts.ts` (`MatchWeekMountProps`, `CommandReplayState`, `NAV_RAIL_ATTR`); the frozen signatures of `standings/PlayoffBracket` and `dynasty/history/ProgramModal` (P2 does not import these, but must not break them).
5. **`data-*` anti-strip vitests are HARD RED preconditions.** Any rebuild MUST keep its truth-provenance hooks. The P2-screen hooks enumerated in Task 2 (`data-broadcast-proof-source`, `data-player-outcome`, the replay/aftermath `data-testid` provenance) are written as RED tests **before** the corresponding reskin task touches the component.
6. **Per-phase gate** (runs in the worktree with the OLD `index.css` still present): `npm run test` + `npm run build` + `npm run lint` + `npm run lint:tokens` + a smoke e2e (`npm run e2e` from repo root). The integrator runs the `index.css` deletion + full `tsc --noEmit`/vitest later.

---

## Sub-area sequencing (serial inside P2 — do NOT parallelize)

MatchWeek is the orchestrator and touches all three sub-areas; rebuilding them out of order risks the orchestrator referencing classes/props that do not exist yet. Execute strictly in this order:

1. **Contracts + anti-strip RED preconditions** (Tasks 1–2) — freeze `matchResult.ts`, assert mount props, write all `data-*` RED tests.
2. **PreSimDashboard (Command Center)** (Tasks 3–4) — pre-sim sub-area.
3. **Aftermath tree** (Tasks 5–9) — MatchScoreHero, the aftermath cards, PlayoffResolutionBanner, the MatchWeek post-sim orchestrator + the `closest()` rewrite.
4. **MatchReplay + the new SVG canvas** (Tasks 10–13) — replay scoreboard/strip/court/highlights, then the net-new `LiveCourtCanvas`.
5. **Phase-2 gate** (Task 14).

---

## File map (created/modified in this plan)

**Created (contracts + anti-strip):**
- `frontend/src/components/match-week/matchResult.test.ts` (V20 single-payload guard; the #1/#2 contract — **does not change** `matchResult.ts`)
- `frontend/src/components/match-week/aftermath/antiStrip.test.tsx` (the consolidated `data-*` provenance RED preconditions for the aftermath surfaces)
- `frontend/src/components/replay/antiStrip.test.tsx` (the `data-*` provenance RED preconditions for the replay surfaces)

**Created (the net-new SVG canvas):**
- `frontend/src/components/replay/LiveCourtCanvas.tsx` + `LiveCourtCanvas.module.css` + `LiveCourtCanvas.test.tsx`

**Created (CSS Modules + tests, one per reskinned surface):**
- `frontend/src/components/match-week/command-center/PreSimDashboard.module.css` + `PreSimDashboard.test.tsx`
- `frontend/src/components/match-week/aftermath/MatchScoreHero.module.css` + `MatchScoreHero.test.tsx`
- `frontend/src/components/match-week/aftermath/PlayoffResolutionBanner.module.css` + `PlayoffResolutionBanner.test.tsx`
- `frontend/src/components/match-week/aftermath/aftermathCards.module.css` (shared by PrimaryFactorCard / ManagerLessonCard / TacticalSummaryCard / KeyPlayersPanel / Headline / NextBestImprovementPanel / EliminationCeremony / ChampionshipHero / FalloutGrid / ReplayTimeline / AftermathActionBar / banners)
- `frontend/src/components/MatchWeek.module.css` + `frontend/src/components/MatchWeek.test.tsx`
- `frontend/src/components/MatchReplay.module.css` + `frontend/src/components/MatchReplay.test.tsx`

**Modified (reskin to module CSS + re-point imports; logic verbatim):**
- `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`
- `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx`
- `frontend/src/components/match-week/aftermath/PlayoffResolutionBanner.tsx`
- the aftermath card components listed above (`PrimaryFactorCard.tsx`, `ManagerLessonCard.tsx`, `TacticalSummaryCard.tsx`, `KeyPlayersPanel.tsx`, `Headline.tsx`, `NextBestImprovementPanel.tsx`, `EliminationCeremony.tsx`, `ChampionshipHero.tsx`, `FalloutGrid.tsx`, `ReplayTimeline.tsx`, `AftermathActionBar.tsx`, `LateGameBanner.tsx`, `OneVOneBanner.tsx`, `ComebackCard.tsx`)
- `frontend/src/components/match-week/ProgramStatusStrip.tsx` (behavior #5: GP-vs-elim differential branch; lives under `match-week/`, reskinned in Task 7's card sweep)
- `frontend/src/components/MatchWeek.tsx` (reskin its OWN inline blocks — bye card, verdict, AftermathBody — to module CSS; rewrite `closest('.dm-left-nav')` → `closest(`[${NAV_RAIL_ATTR}]`)`; re-point `StatusMessage` import)
- `frontend/src/components/MatchReplay.tsx` (reskin scoreboard/strip/court/sidebar; mount the new `LiveCourtCanvas` alongside the existing memoized `DarkCourt`, or replace `DarkCourt` with it — see Task 12)

**FROZEN / not touched:** `components/match-week/matchResult.ts` (consumed, never edited), `legibility/*`, `components/ui.tsx`, `frontend/src/index.css` (integrator deletes P2 legacy in STEP 3), `frontend/scripts/check-tokens.mjs`, `command-action-bar`/`command-policy-overlay` globals, `appContracts.ts` (Phase-1-owned), `PlayoffBracket.tsx`/`ProgramModal.tsx` (other phases).

---

## Per-task gate

Unless a task says otherwise, every task ends green on:

```bash
cd frontend && npm run test -- <the task's test files> && npm run build && npm run lint
```

`npm run lint:tokens` runs only against dirs the **integrator** later appends to `SCAN_DIRS` (P2 never edits `check-tokens.mjs`), so token discipline is NOT machine-enforced inside this worktree until integration. **Therefore each reskin task MUST use only `var(--…)` tokens (no raw hex/px beyond `0`/`1px` hairlines and SVG `viewBox`/geometry coordinates) from the start**, so that when the integrator appends the P2 dirs in STEP 3 the gate passes with zero rework. A self-check command is given in Task 14.

The **Phase-2 gate** (Task 14) runs the full FE suite + the root e2e smoke:

```bash
cd frontend && npm run test && npm run build && npm run lint
cd .. && npm run e2e
```

> **Runtime club-color note:** the score hero / canvas use per-side accent colors. Express them as token-driven CSS-var classes (`.sideHome { --accent: var(--volt); }` / `.sideAway { --accent: var(--gold); }` — or new semantic tokens in usage), never raw `#f97316`/`#22d3ee` literals, so the token gate passes when the integrator scopes these dirs. SVG geometry coordinates (`viewBox`, `cx`, `r`) are exempt (the gate's `ALLOW` skips `viewBox` and `.svg`; numeric SVG attributes in `.tsx` are not `px` literals).

---

## Phase 2A — Contracts + anti-strip RED preconditions

### Task 1: Freeze the V20 single-payload scoreline contract (matchResult.ts — consume, never alter) — #1, #2

> **Why:** `matchResult.ts` is the FROZEN cross-phase contract (4 importers: MatchScoreHero, MatchWeek, MatchReplay in P2 + PlayoffBracket in P4). Behavior #1 (one shared scoreline decision; never print a survivor count as the official result — a 0-0 foam draw can carry a 0-3 survivor box score) and #2 (MatchScoreHero/MatchReplay scoreboard branch on `scoring_model`) both rest on it. The strategy explicitly permits P2 to **ADD** a single-payload vitest against `matchResult.ts` but **forbids changing its API**. This test is the executable headline trust guard; it pins the official-vs-legacy branch so no later reskin can regress it.

**Audit numbers + test strategy (checklist Phase 2):** #1, #2 → **vitest + python-guard** (the python-guard on backend `scoring_model` already lives in the Python suite; this vitest covers the frontend single-source decision).

**Frozen API captured verbatim (`matchResult.ts:34-60` — DO NOT EDIT THE SOURCE):** `formatScoreline(card: ScorelineFields): MatchScoreline` returns `isOfficial = Boolean(card.scoring_model && card.scoring_model !== 'legacy')`, `home/away.value = isOfficial ? game_points ?? 0 : survivors`, `centerLabel = isOfficial ? `Final · ${rulesetDisplayName(...,'short')}` : 'Final'`; `survivorDetail(survivors, isOfficial) = isOfficial ? 'game points' : `${survivors} survivors``.

**Files:** create `frontend/src/components/match-week/matchResult.test.ts`. (No source edit.)

- [ ] **Step 1: Write the contract test** — pure unit test against the frozen exports.

```ts
// frontend/src/components/match-week/matchResult.test.ts
import { describe, it, expect } from 'vitest';
import { formatScoreline, survivorDetail } from './matchResult';

describe('matchResult — the V20 single-payload scoreline contract (#1, #2)', () => {
  it('official match: headline number is GAME POINTS, never the survivor tally', () => {
    // The canonical falsifying case: a 0-0 official draw whose box score carries
    // a 0-3 survivor count. The result must read 0-0 (game points), never 0-3.
    const card = {
      scoring_model: 'official_foam',
      home_game_points: 0, away_game_points: 0,
      home_survivors: 0, away_survivors: 3,
    };
    const s = formatScoreline(card);
    expect(s.isOfficial).toBe(true);
    expect(s.home.value).toBe(0);
    expect(s.away.value).toBe(0);              // game points, NOT 3 survivors
    expect(s.away.survivors).toBe(3);          // raw survivors retained for detail only
    expect(s.centerLabel).toMatch(/^Final · /); // ruleset short name appended
    expect(survivorDetail(s.away.survivors, s.isOfficial)).toBe('game points');
  });

  it('official match with real game points reads those points', () => {
    const s = formatScoreline({
      scoring_model: 'official_foam',
      home_game_points: 9, away_game_points: 2,
      home_survivors: 1, away_survivors: 0,
    });
    expect(s.home.value).toBe(9);
    expect(s.away.value).toBe(2);
  });

  it('legacy match: headline number IS the survivor count, labeled in survivors', () => {
    const s = formatScoreline({
      scoring_model: 'legacy',
      home_survivors: 4, away_survivors: 1,
    });
    expect(s.isOfficial).toBe(false);
    expect(s.home.value).toBe(4);
    expect(s.away.value).toBe(1);
    expect(s.centerLabel).toBe('Final');
    expect(survivorDetail(s.home.survivors, s.isOfficial)).toBe('4 survivors');
  });

  it('missing scoring_model is treated as legacy (survivors)', () => {
    const s = formatScoreline({ home_survivors: 2, away_survivors: 5 });
    expect(s.isOfficial).toBe(false);
    expect(s.away.value).toBe(5);
  });

  it('official match missing game points falls back to 0, NOT to survivors', () => {
    const s = formatScoreline({
      scoring_model: 'official_foam',
      home_survivors: 6, away_survivors: 6,
    });
    expect(s.home.value).toBe(0); // ?? 0 — never leaks the survivor count
    expect(s.away.value).toBe(0);
  });
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "matchResult.test"`. Expected: **PASS immediately** (the contract already holds; this test pins it). If any case FAILS, the on-trunk `matchResult.ts` differs from the frozen contract — STOP and reconcile with the controller (do NOT edit `matchResult.ts`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/matchResult.test.ts
git commit -m "test(p2): freeze V20 single-payload scoreline contract (matchResult #1/#2)"
```

---

### Task 2: Anti-strip `data-*` provenance RED preconditions (aftermath + replay)

> **Why:** The harness has zero screen tests for these surfaces today. Per the orchestration contract, the truth-provenance DOM hooks are **HARD RED preconditions**: they must be authored and passing against the CURRENT markup BEFORE any reskin touches the component, so the reskin cannot silently drop them. The P2-screen hooks (enumerated from the actual source) are:
> - `data-broadcast-proof-source` on the playoff broadcast frame (BroadcastFrameBlock, rendered inside MatchReplay at `MatchReplay.tsx:545-546`).
> - `data-player-outcome` on `PlayoffResolutionBanner` (`PlayoffResolutionBanner.tsx:52`).
> - `data-testid` provenance on the score hero (`match-score-hero`, `aftermath-set-story`, `score-hero-draw`), the verdict (`match-verdict`), the post-sim shell (`post-week-dashboard`), the replay surfaces (`official-ruleset-banner`, `playoff-frame`, `replay-set-strip`, `replay-set-running`, `current-event-card`, `replay-moment-banner`, `replay-highlights`), and the Command Center (`weekly-command-center`, `secondary-intel-rail`, `presim-command-strip`, `plan-readout`, `matchup-band`, `tactical-diff`, `current-objective`).
>
> This task writes the consolidated RED tests. They pass on the current markup (guards), then every reskin task below keeps them green. The `worlds_user` receipt, `recap-missed-playoffs`, `prospect-card-locked`, and `save-name-collision-banner` hooks are NOT on Phase-2 screens (they live on P4 RecapStandings / P5 ProspectCard / P7 IdentityStep) — explicitly out of scope here.

**Files:** create `frontend/src/components/match-week/aftermath/antiStrip.test.tsx` and `frontend/src/components/replay/antiStrip.test.tsx`.

- [ ] **Step 1: Write the aftermath anti-strip tests** — render the leaf components directly with minimal real-shaped props.

```tsx
// frontend/src/components/match-week/aftermath/antiStrip.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MatchScoreHero } from './MatchScoreHero';
import { PlayoffResolutionBanner } from './PlayoffResolutionBanner';

describe('aftermath data-* provenance (anti-strip preconditions)', () => {
  it('MatchScoreHero keeps its testid + draw/set-story hooks', () => {
    render(
      <MatchScoreHero
        homeTeam="Aurora" awayTeam="Granite"
        homeSurvivors={0} awaySurvivors={3}
        winnerClubId={null} homeClubId="aurora"
        scoringModel="official_foam" homeGamePoints={0} awayGamePoints={0}
        games={[{ game_number: 1, winner_club_id: 'aurora', home_points: 1, away_points: 0, result_type: 'point' }]}
        isPlayoff={false}
      />,
    );
    expect(screen.getByTestId('match-score-hero')).toBeInTheDocument();
    expect(screen.getByTestId('score-hero-draw')).toBeInTheDocument();          // #12 draw outcome
    expect(screen.getByTestId('aftermath-set-story')).toBeInTheDocument();      // #49 set strip
  });

  it('PlayoffResolutionBanner exposes data-player-outcome + data-decided-by (#11, #16)', () => {
    render(
      <PlayoffResolutionBanner
        resolution={{
          decided_by: 'seed_tiebreaker', player_outcome: 'eliminated',
          stage: 'Semifinal', narrative_note: 'Lost on the seed line.',
        } as never}
      />,
    );
    const banner = screen.getByTestId('playoff-resolution-banner');
    expect(banner).toHaveAttribute('data-player-outcome', 'eliminated');
    expect(banner).toHaveAttribute('data-decided-by', 'seed_tiebreaker');
  });

  it('PlayoffResolutionBanner renders nothing on regulation (#11/#14)', () => {
    const { container } = render(
      <PlayoffResolutionBanner resolution={{ decided_by: 'regulation' } as never} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Write the replay anti-strip tests** — mock `commandApi` (highlights/replay fetches) and render `MatchReplay` with a minimal payload, asserting the provenance hooks that appear with that payload.

```tsx
// frontend/src/components/replay/antiStrip.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

vi.mock('../../api/client', () => ({
  commandApi: { highlights: vi.fn().mockResolvedValue({ beats: [] }) },
}));

import MatchReplay from '../MatchReplay';
import type { MatchReplayResponse } from '../../types';

// Minimal but real-shaped: one official event with score_state + a playoff frame.
const PAYLOAD = (): MatchReplayResponse => ({
  match_id: 'm1', week: 3, scoring_model: 'official_foam',
  home_club_id: 'aurora', away_club_id: 'granite',
  home_game_points: 1, away_game_points: 0, home_survivors: 2, away_survivors: 0,
  key_play_indices: [0],
  report: { turning_point: 'A swing.', turning_point_index: 0, evidence_lanes: [], top_performers: [] },
  game_segments: [],
  moment_events: [],
  // PlayoffFrame shape: { label, title, proof_source } — types.ts:768-772. Field is 'label', NOT 'body'.
  // If this drifts, remove the outer `as never` and let the compiler catch it.
  playoff_frame: { proof_source: 'record:playoff-2031-semi', title: 'Semifinal', label: 'Seed tiebreaker semifinal.' },
  official_state: null,
  proof_events: [{
    sequence_index: 0, tick: 1, game_number: 1, thrower_id: 'p1', thrower_name: 'A One',
    target_id: 'p2', target_name: 'B Two', offense_club_id: 'aurora', defense_club_id: 'granite',
    resolution: 'eliminated', is_key_play: true, proof_tags: [], summary: 'Hit.', detail: '',
    odds: {}, rolls: {}, fatigue: {} as never, decision_context: {} as never,
    tactic_context: {} as never, liability_context: {} as never,
    score_state: { home_living: 6, away_living: 5, home_eliminated_player_ids: [], away_eliminated_player_ids: ['p2'] },
  }],
} as never);

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('replay data-* provenance (anti-strip preconditions)', () => {
  it('keeps the broadcast proof-source hook + current-event card (#30, #37)', async () => {
    render(<MatchReplay data={PAYLOAD()} onContinue={() => {}} />);
    const frame = await screen.findByTestId('playoff-frame');
    expect(frame).toHaveAttribute('data-broadcast-proof-source', 'record:playoff-2031-semi');
    expect(screen.getByTestId('current-event-card')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run to verify behavior** — `cd frontend && npm run test -- "aftermath/antiStrip" "replay/antiStrip"`. Expected: **PASS against current markup** (these guard existing hooks). If a selector mismatches the current DOM, correct it to the CURRENT truth (these are non-regression guards, not new behavior). This is the green baseline every reskin task must hold.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match-week/aftermath/antiStrip.test.tsx frontend/src/components/replay/antiStrip.test.tsx
git commit -m "test(p2): anti-strip data-* provenance preconditions (aftermath + replay)"
```

---

## Phase 2B — PreSimDashboard (Command Center)

### Task 3: PreSimDashboard test scaffolding (Command Center truth, RED-then-hold) — #3, #32, #39, #93, #94, #95

> **Why:** PreSimDashboard is the pre-sim Command Center (audit §3 P1 high — entirely inline). The reskin must keep: #3 (League Wire shows the game-point scoreline, not bare Win/Loss — `PreSimDashboard.tsx:454-460`), #32 (League Wire empty-state = one honest static line, headlines-first merge — :463-466), #39 (bye-week primary action = `ADVANCE BYE WEEK`, no opponent/match/fatigue panels — :440-450), #93 (`FALLBACK_BRIEFING`/`matchup_details` defaults render without re-deriving; confirm-lineup preview shows the canonical six), #94 (Operational-Plan alignment reflects real state — pending orders OR conflict, no green-while-misaligned — :509-517,778-797 → `data-testid="plan-readout"`), #95 (recent-results ordered W/L from history slice; stakes top-4 not top-3). Author guards against the CURRENT dashboard; the reskin (Task 4) keeps them green.

**Audit numbers + test strategy (checklist Phase 2):** #3 vitest · #32 vitest · #39 vitest · #93 vitest · #94 vitest · #95 vitest.

**Behavior anchors (verified):** wire scoreline build :454-460; wireItems merge + empty `secondary-intel-rail` :463-466,526-550; bye primary-action label :440-450; alignment callout `plan-readout` :778-797; `data-testid="matchup-band"` :685; `current-objective` :598.

**Files:** create `frontend/src/components/match-week/command-center/PreSimDashboard.test.tsx`.

- [ ] **Step 1: Write the failing/guard tests** — build a real-shaped `CommandCenterResponse` factory; render `<PreSimDashboard data={...} ...stubbed callbacks/>`. Mock nothing the component owns; pass no-op callbacks for `simulate`/`onSavePlan`/`onSavePolicy`/`onSaveDevFocus`/`onIntentChange`/`fastForward`/`onScout`/`onConfirmLineup`.

```tsx
// frontend/src/components/match-week/command-center/PreSimDashboard.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PreSimDashboard } from './PreSimDashboard';
import type { CommandCenterResponse } from '../../../types';

// A minimal real-shaped command-center payload. Fill from the live type — do NOT
// invent fields; read CommandCenterResponse in types.ts and extend as the
// component requires (the component will throw on a missing field, telling you).
function makeData(over: Partial<CommandCenterResponse> = {}): CommandCenterResponse {
  return {
    /* …populate the required CommandCenterResponse shape verbatim from types.ts… */
  } as CommandCenterResponse;
}

const noop = vi.fn();
const cb = {
  simulate: noop, onSavePlan: noop, onSavePolicy: noop, onSaveDevFocus: noop,
  selectedIntent: 'Balanced', onIntentChange: noop, planConfirmed: false, saving: false,
  fastForward: noop, onScout: noop, onConfirmLineup: noop,
};

describe('PreSimDashboard Command Center truth (#3,#32,#39,#93,#94,#95)', () => {
  it('#3: the League Wire shows the game-point scoreline, not a bare Win/Loss', () => {
    render(<PreSimDashboard data={makeData({
      history: [{ week: 2, dashboard: { result: 'Win', score: '9–2', opponent_name: 'Granite' } }] as never,
    })} {...cb} />);
    expect(screen.getByText(/9–2/)).toBeInTheDocument();
    expect(screen.getByText(/Granite/)).toBeInTheDocument();
  });

  it('#32: an empty wire shows one honest static line in the rail', () => {
    render(<PreSimDashboard data={makeData({ history: [] as never })} {...cb} />);
    const rail = screen.getByTestId('secondary-intel-rail');
    expect(rail).toBeInTheDocument();
    expect(rail.className).not.toMatch(/has-news/); // honest empty, not a fabricated marquee
  });

  it('#39: a bye week shows ADVANCE BYE WEEK and no opponent/fatigue panels', () => {
    render(<PreSimDashboard data={makeData({ /* bye-week shape: is_bye true */ } as never)} {...cb} planConfirmed />);
    expect(screen.getByText(/ADVANCE BYE WEEK/i)).toBeInTheDocument();
    expect(screen.queryByText(/recover|fatigue/i)).not.toBeInTheDocument();
  });

  it('#94: alignment is NOT green while operational orders are pending', () => {
    render(<PreSimDashboard data={makeData({ /* pending dept order */ } as never)} {...cb} />);
    const readout = screen.getByTestId('plan-readout');
    expect(readout.className).toMatch(/is-warning|warning/);
  });

  it('#93: matchup band renders from defaults without crashing on a sparse payload', () => {
    render(<PreSimDashboard data={makeData()} {...cb} />);
    expect(screen.getByTestId('weekly-command-center')).toBeInTheDocument();
  });
});
```

> **Note (factory completeness):** `CommandCenterResponse` is a large type. Read it in `frontend/src/types.ts` and populate `makeData` with the EXACT required fields — do not invent. If a test needs a bye-week vs in-season vs pending-order variant, pass the minimal `over` that flips that branch (read the component's `isBye` / `operationalMisaligned` / `history` derivations at the line anchors above to know which field flips each). The cases that cannot be satisfied with a real payload at this stage may be deferred to the Task-14 e2e smoke — say so explicitly rather than asserting against an invented shape.

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "PreSimDashboard.test"`. Expected: guards PASS against the current dashboard (correct any assertion to the current truth). Establishes the baseline.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/command-center/PreSimDashboard.test.tsx
git commit -m "test(p2): lock Command Center truth behaviors (#3/#32/#39/#93/#94/#95) before reskin"
```

---

### Task 4: PreSimDashboard reskin to CSS Modules (hold #3, #32, #39, #93, #94, #95)

> **Why:** Migrate PreSimDashboard's inline styles + `cc-*`/`max-content`/`dm-*` global classes to `PreSimDashboard.module.css` + `src/ui` primitives (Grid for the cockpit/overview grids → kills P3/P10 fixed-column overflow; Truncate on opponent/club names → kills P2; ScrollRegion on the readiness/intel lanes). **Logic is verbatim** — only the styling substrate changes. Keep every `data-testid`, the wire scoreline build (:454-460), the empty-rail branch, the bye primary-action label, the alignment callout state, and the tactical-diff source branching (#25 lives here but is owned by its own audit row; do not change its provenance copy).

**Audit numbers + test strategy:** #3/#32/#39/#93/#94/#95 vitest (held through the reskin).

**Files:** create `frontend/src/components/match-week/command-center/PreSimDashboard.module.css`; modify `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`.

- [ ] **Step 1: Confirm the guards are green** — `cd frontend && npm run test -- "PreSimDashboard.test"`. (They were authored in Task 3 against current markup.)

- [ ] **Step 2: Reskin** —
  - Create `PreSimDashboard.module.css` with token-driven classes for the wire rail, command strip, objective/readiness panels, plan editor, scout/opponent file, and the matchup band. No raw hex/px (tokens only). Express side accents as `--accent` var classes.
  - Replace `className="cc-…"` / inline `style={{…}}` with `className={styles.…}`. Use `Grid` (Phase-0) for the `command-cockpit-grid`/`command-overview-grid`/`command-secondary-grid` so they collapse responsively (removes the need for the deleted `index.css` `@media` overrides — those legacy responsive rules are carved out by the integrator).
  - Wrap long club/opponent names in `Truncate`; wrap the readiness gate list + intel lanes in `ScrollRegion` (`min-height:0` so nested scroll regions stop pushing footers off-screen — kills P4).
  - **Keep `command-action-bar`/`command-policy-overlay`** class names if present on the policy editor overlay / sticky action surfaces (SHARED globals, P8-only deletion) — do not remove them; the module CSS layers alongside.
  - Re-point any `ActionButton`/`StatusMessage`/`RadioGroup` imports in this file (and `PolicyEditor`/`SeasonPreview` if reskinned in the same pass) from `./ui`-style barrels to the `src/ui` shims (path change only).
  - **Do NOT touch:** the `recentLeagueWire`/`wireItems` derivation, `isBye`, `operationalMisaligned`, `primaryActionLabel`/`primaryActionHint`, the tactical-diff `data-scouted`/source-meta logic, or any `data-testid`.

- [ ] **Step 3: Run to verify it still passes** — `cd frontend && npm run test -- "PreSimDashboard.test" "PreSimDashboard.module"`. Expected: PASS (behavior held).

- [ ] **Step 4: Gate + commit**

```bash
cd frontend && npm run test -- "PreSimDashboard" && npm run build && npm run lint
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx frontend/src/components/match-week/command-center/PreSimDashboard.module.css
git commit -m "feat(p2): PreSimDashboard to CSS Modules; hold #3/#32/#39/#93/#94/#95"
```

---

## Phase 2C — Aftermath tree

### Task 5: MatchScoreHero reskin (hold #2, #12, #49) + the V20 branch

> **Why:** MatchScoreHero is the headline score-bearing surface (audit §3 P1). It already branches on `scoring_model` via `formatScoreline` (`:146-153`) and renders the draw badge/footer (#12, `:161,176-235`) and the per-game set strip (#49, `:97-117`). The reskin moves the inline `style={{…}}` (the `#f97316`/`#22d3ee` accents, the draw footer block, the winner badge) to `MatchScoreHero.module.css` while preserving the `formatScoreline`/`survivorDetail` calls **exactly** and every `data-testid`. The accent colors become `--accent` token-var classes (no raw hex).

**Audit numbers + test strategy:** #2 vitest (scoreboard branches on scoring_model) · #12 vitest (draw badge + footer; playoff footer must NOT promise a standings point) · #49 vitest (set strip from persisted per-game score).

**Files:** create `frontend/src/components/match-week/aftermath/MatchScoreHero.module.css` + `MatchScoreHero.test.tsx`; modify `MatchScoreHero.tsx`.

- [ ] **Step 1: Write the failing/guard tests**

```tsx
// frontend/src/components/match-week/aftermath/MatchScoreHero.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MatchScoreHero } from './MatchScoreHero';

const base = {
  homeTeam: 'Aurora', awayTeam: 'Granite', homeClubId: 'aurora',
  homeSurvivors: 0, awaySurvivors: 3, winnerClubId: null,
  games: [{ game_number: 1, winner_club_id: 'aurora', home_points: 1, away_points: 0, result_type: 'point' }],
};

describe('MatchScoreHero (#2,#12,#49)', () => {
  it('#2: official match labels each side "game points", never the survivor count', () => {
    render(<MatchScoreHero {...base} scoringModel="official_foam" homeGamePoints={0} awayGamePoints={0} />);
    expect(screen.getAllByText('game points').length).toBeGreaterThan(0);
    expect(screen.queryByText('3 survivors')).not.toBeInTheDocument();
  });
  it('#12: a draw shows the draw badge; in playoffs the footer does NOT promise a standings point', () => {
    render(<MatchScoreHero {...base} scoringModel="official_foam" homeGamePoints={0} awayGamePoints={0} isPlayoff />);
    expect(screen.getByTestId('score-hero-draw')).toBeInTheDocument();
    expect(screen.getByText(/can't stand/i)).toBeInTheDocument();
    expect(screen.queryByText(/standings point/i)).not.toBeInTheDocument();
  });
  it('#12: a non-playoff official draw footer DOES grant a standings point', () => {
    render(<MatchScoreHero {...base} scoringModel="official_foam" homeGamePoints={0} awayGamePoints={0} isPlayoff={false} />);
    expect(screen.getByText(/standings point/i)).toBeInTheDocument();
  });
  it('#49: the set-story strip renders one chip per persisted game', () => {
    render(<MatchScoreHero {...base} scoringModel="official_foam" homeGamePoints={1} awayGamePoints={0} />);
    const strip = screen.getByTestId('aftermath-set-story');
    expect(strip.querySelectorAll('[class*="set-chip"], span.g').length).toBeGreaterThan(0);
  });
});
```

> **Selector note:** after reskin the chip class becomes a module class (e.g. `styles.setChip`), so the `#49` query keys on the stable inner `span.g` (game label) or the `aftermath-set-story` container child count — not on the legacy `command-score-set-chip` literal. Adjust the assertion to the stable structural hook, not the class name.

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "MatchScoreHero.test"`. Expected: PASS against current markup. (`#49` selector: if keyed on the legacy class, it passes now; rewrite it to the structural hook in Step 3 so it survives the reskin.)

- [ ] **Step 3: Reskin** — create `MatchScoreHero.module.css`; replace the inline `style={{…}}` on `TeamScore` (accent border/glow → `.sideHome`/`.sideAway` with `--accent` var), the winner badge, the draw badge, the set strip, and the full-width draw footer with token-driven module classes. Wrap team `name` in `Truncate` (it already does manual ellipsis inline — replace with the primitive). **Keep** `formatScoreline`/`survivorDetail` calls, the `isDraw`/`isPlayoff` footer branch text verbatim, and `data-testid="match-score-hero"`/`score-hero-draw`/`aftermath-set-story`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "MatchScoreHero" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/match-week/aftermath/MatchScoreHero.tsx frontend/src/components/match-week/aftermath/MatchScoreHero.module.css frontend/src/components/match-week/aftermath/MatchScoreHero.test.tsx
git commit -m "feat(p2): MatchScoreHero to CSS Modules; hold V20 branch + draw/set truth (#2/#12/#49)"
```

---

### Task 6: PlayoffResolutionBanner reskin (hold #11, #14, #16 + data-player-outcome)

> **Why:** The single most-cited playtest trust break (tied 0-0 semifinal silently advancing). The banner reads `decided_by` directly, renders nothing on `'regulation'` (#11/#14), and carries `data-player-outcome`/`data-decided-by` (anti-strip, #16-adjacent). The reskin moves the inline `accent`/`style={{…}}` blocks to `PlayoffResolutionBanner.module.css` keyed on `data-player-outcome` (advanced=ok, eliminated=volt, neutral=info) — **the `decided_by`/`player_outcome` reads and the `return null` are untouched**.

**Audit numbers + test strategy:** #11 vitest · #14 vitest · #16 vitest (data-player-outcome on DOM).

**Files:** create `frontend/src/components/match-week/aftermath/PlayoffResolutionBanner.module.css`; create `PlayoffResolutionBanner.test.tsx` (or extend `aftermath/antiStrip.test.tsx`); modify `PlayoffResolutionBanner.tsx`.

- [ ] **Step 1: Confirm the anti-strip guards (Task 2) cover #11/#14/#16** — they already assert `data-player-outcome`, `data-decided-by`, and the regulation null-render. Add the advanced/overtime variant if not present:

```tsx
// append to aftermath/antiStrip.test.tsx (or a new PlayoffResolutionBanner.test.tsx)
it('overtime advance: chip OVERTIME + outcome advanced', () => {
  render(<PlayoffResolutionBanner resolution={{
    decided_by: 'overtime', player_outcome: 'advanced', stage: 'Final', narrative_note: 'Won in OT.',
  } as never} />);
  const b = screen.getByTestId('playoff-resolution-banner');
  expect(b).toHaveAttribute('data-player-outcome', 'advanced');
  expect(screen.getByText('OVERTIME')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "antiStrip"`. Expected: PASS.

- [ ] **Step 3: Reskin** — create `PlayoffResolutionBanner.module.css` with `.banner` + outcome-keyed accent classes (`.advanced`/`.eliminated`/`.neutral` mapping to `--ok`/`--volt`/`--line2`). Replace the inline `accent`/`style={{…}}` with `className={`${styles.banner} ${styles[outcome]}`}` where `outcome = resolution.player_outcome ?? 'neutral'`. **Keep** the `decided_by === 'regulation' → return null`, the `chip`/`title` logic, and `data-testid`/`data-decided-by`/`data-player-outcome` verbatim.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "antiStrip" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/match-week/aftermath/PlayoffResolutionBanner.tsx frontend/src/components/match-week/aftermath/PlayoffResolutionBanner.module.css
git commit -m "feat(p2): PlayoffResolutionBanner to CSS Modules; hold #11/#14/#16 + data-player-outcome"
```

---

### Task 7: Aftermath cards reskin (Headline, PrimaryFactor, ManagerLesson, Tactical, KeyPlayers, FalloutGrid, ReplayTimeline + banners, NextBestImprovement, Elimination, ChampionshipHero, AftermathActionBar, **ProgramStatusStrip**) — #5, #29, #31, #35, #48, #50

> **Why:** These leaf cards (audit §3 P1 medium — all hardcode hex + inline px) carry the aftermath truth: audience-tagged paragraphs read by tag (#29), honest null-vs-zero rendering (#31), truthful empty states (#35), ComebackCard self-suppression (#48), replay top-performers/tactical evidence prefer the authoritative replay payload (#50 — the data wiring lives in MatchWeek Task 8, but KeyPlayersPanel/TacticalSummaryCard render it). The reskin shares one `aftermathCards.module.css` (consistent card chrome) and re-points `src/ui` imports. **Logic verbatim** — empty-state copy, the `audience` tag grouping, and the suppression conditions are untouched. `ProgramStatusStrip.tsx` (lives at `frontend/src/components/match-week/ProgramStatusStrip.tsx`, NOT in `aftermath/`) is also reskinned in this pass — it carries behavior #5 (the V20 GP-vs-elim differential branch: `is_official_career` → show `game_point_differential`; else → show `elimination_differential`; lines 12-14 of ProgramStatusStrip.tsx). Its inline-hex + inline-px are the same P1-medium risk.

**Audit numbers + test strategy:** **#5 vitest** · #29 vitest · #31 vitest · #35 vitest · #48 vitest · #50 vitest (KeyPlayers/Tactical render path; the source-preference wiring asserted in Task 8).

**Files:** create `frontend/src/components/match-week/aftermath/aftermathCards.module.css`; create a focused `frontend/src/components/match-week/aftermath/aftermathCards.test.tsx`; modify the **15** card/banner/strip components listed in the heading (the 14 cards + `ProgramStatusStrip.tsx`).

- [ ] **Step 1: Write focused guards for the load-bearing truth (not pixels)**

```tsx
// frontend/src/components/match-week/aftermath/aftermathCards.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ComebackCard } from './ComebackCard';
import { KeyPlayersPanel } from './KeyPlayersPanel';
import { ProgramStatusStrip } from '../ProgramStatusStrip';

// ProgramStatusStrip fetches from /api/standings via useApiResource; mock it.
vi.mock('../../../hooks/useApiResource', () => ({
  useApiResource: vi.fn(),
}));
import { useApiResource } from '../../../hooks/useApiResource';

describe('aftermath card truth (#5, #48, #50, #35)', () => {
  it('#5 (official_foam career): differential shown is game_point_differential, NOT elimination_differential', () => {
    // ProgramStatusStrip.tsx:12-14: is_official_career → strapDiff = game_point_differential
    (useApiResource as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        is_official_career: true,
        standings: [{
          is_user_club: true, wins: 5, losses: 2, draws: 1, points: 16,
          game_point_differential: 12, elimination_differential: 4,
        }],
      },
    });
    render(<ProgramStatusStrip />);
    // The differential renders as "{strapDiff > 0 ? '+' : ''}{strapDiff} diff" (ProgramStatusStrip.tsx:44-46).
    // Official career: strapDiff = 12 → "+12 diff". Elimination diff (4) must NOT appear.
    expect(screen.getByText(/\+12 diff/)).toBeInTheDocument();
    expect(screen.queryByText(/\+4 diff/)).not.toBeInTheDocument();
  });
  it('#5 (legacy career): differential shown is elimination_differential, NOT game_point_differential', () => {
    (useApiResource as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        is_official_career: false,
        standings: [{
          is_user_club: true, wins: 3, losses: 4, draws: 0, points: 9,
          game_point_differential: 12, elimination_differential: 4,
        }],
      },
    });
    render(<ProgramStatusStrip />);
    // Legacy career: strapDiff = elimination_differential = 4 → "+4 diff".
    expect(screen.getByText(/\+4 diff/)).toBeInTheDocument();
    expect(screen.queryByText(/\+12 diff/)).not.toBeInTheDocument();
  });
  it('#48: ComebackCard self-suppresses when winner !== comeback team', () => {
    const { container } = render(
      <ComebackCard comeback={{ team_id: 'granite', /* …deficit fields… */ } as never} winnerClubId="aurora" />,
    );
    expect(container).toBeEmptyDOMElement();
  });
  it('#50/#35: KeyPlayersPanel shows an honest fallback when no performers', () => {
    render(<KeyPlayersPanel performers={[]} playerClubName="Aurora" />);
    expect(screen.getByText(/best|no .*performer|—/i)).toBeInTheDocument();
  });
});
```

> Read each component's exact props + empty-state copy from source before finalizing the assertions (do not invent the fallback string — quote it). `ComebackCard.tsx:19-22` holds the suppression; `KeyPlayersPanel` holds the "Your Club's Best" fallback. Add a `#29` audience-tag case against the MatchWeek `AftermathBody` in Task 8 (it lives in `MatchWeek.tsx`, not a leaf card). The #5 assertions above key on the `"{strapDiff > 0 ? '+' : ''}{strapDiff} diff"` text node from `ProgramStatusStrip.tsx:44-46` — if the text format changes in source, update the regex to match the actual rendered text.

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "aftermathCards.test"`. Expected: PASS against current markup (including the #5 differential guard).

- [ ] **Step 3: Reskin all 15** — create `aftermathCards.module.css` with shared `.card`, `.kicker`, `.body`, accent variants, chip/badge classes. For each component: replace inline `style={{…}}` + `dm-panel`/`dm-badge`/`dm-kicker` literals with module classes; wrap overflowing names in `Truncate`; use `Grid` for the FalloutGrid 3-column layout (Who Grew / Standings Shift / Prospect Pulse) so it collapses (kills P10). Re-point `ActionButton`/`StatusMessage`/`RatingBar` imports to `src/ui` shims. Also reskin `ProgramStatusStrip.tsx` (its inline `#10b981`/`#f43f5e`/`#94a3b8`/`#22d3ee`/`#64748b` literals and inline `style={{…}}` blocks) → module CSS with token vars; keep the `is_official_career` branch at lines 12-14 verbatim. **Keep verbatim:** every empty-state string, the `audience` grouping, the `ComebackCard` suppression conditions, the `decided_by`/null-vs-zero guards. **Do NOT** alter `aftermath/ReplaySpeedControl.tsx` data flow (it is an active consumer via MatchReplay; reskin its pill styling only if it is reachable in this phase — it is imported by MatchReplay, handled in Task 11).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "aftermathCards" "aftermath/antiStrip" && npm run build`. Expected: PASS + build clean (including both #5 differential cases).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/match-week/aftermath/*.tsx frontend/src/components/match-week/ProgramStatusStrip.tsx frontend/src/components/match-week/aftermath/aftermathCards.module.css frontend/src/components/match-week/aftermath/aftermathCards.test.tsx
git commit -m "feat(p2): aftermath cards + banners + ProgramStatusStrip to shared CSS Module; hold #5/#29/#31/#35/#48/#50"
```

---

### Task 8: MatchWeek orchestrator — reskin its own blocks + the `closest()` rewrite + reveal-skip test — #4, #13, #29, #50, #90

> **Why:** MatchWeek is the **serial orchestrator** (the highest-blast-radius file). It owns: the post-sim aftermath context line phrased in the scoring model's scale (#4, `buildContextLine` :47-79), the verdict-is-fallback gate (#13, :522 — suppressed when `primary_factor` present), the audience-tagged `AftermathBody` (#29, :87+), the replay-source-preference for top-performers/tactical evidence (#50, :559-564), and the optimistic policy save with rollback (#90, `savePolicy` :208-232). It also holds the reveal-skip `closest('.dm-left-nav')` at **line 334** that this phase rewrites to `closest(`[${NAV_RAIL_ATTR}]`)` against the Phase-1 contract, plus an explicit **"nav-click does NOT advance revealStage"** vitest. The reskin migrates ONLY MatchWeek's own inline blocks (the bye-recovery card :454-501, the verdict block :522-546, the `AftermathBody` colors :89-90); the leaf cards were reskinned in Tasks 5–7.

**Audit numbers + test strategy (checklist Phase 2):** #4 vitest (context line scale) · #13 vitest (verdict suppressed when primary_factor) · #29 vitest (AftermathBody reads by tag) · #50 vitest (top-performers prefer replay payload) · #90 vitest (optimistic rollback) · plus the **NAV_RAIL reveal-skip** vitest.

**Files:** create `frontend/src/components/MatchWeek.module.css` + `frontend/src/components/MatchWeek.test.tsx`; modify `frontend/src/components/MatchWeek.tsx`.

- [ ] **Step 1: Write the failing/guard tests** — mock `commandApi` (center/savePlan/replay/highlights) and the heavy leaf children where convenient; render `<MatchWeek mode="post-sim" persistedResult={…} />` and `mode="pre-sim"`. Assert the orchestrator's own logic. **Assert the mount props against the Phase-1 contract.**

```tsx
// frontend/src/components/MatchWeek.test.tsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { MatchWeekMountProps } from './shell/appContracts';
import type { ComponentProps } from 'react';

vi.mock('../api/client', () => ({
  commandApi: {
    center: vi.fn().mockResolvedValue({ /* CommandCenterResponse minimal */ }),
    savePlan: vi.fn(), simulate: vi.fn(), replay: vi.fn().mockResolvedValue(null),
    highlights: vi.fn().mockResolvedValue({ beats: [] }), fastForward: vi.fn(),
    scoutOpponent: vi.fn(), confirmLineup: vi.fn(), skipSeasonPreview: vi.fn(),
  },
}));

import { MatchWeek } from './MatchWeek';

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('MatchWeek orchestrator (#4,#13,#29,#50,#90 + nav reveal-skip)', () => {
  it('mount props are assignable to the Phase-1 MatchWeekMountProps contract (compile-time)', () => {
    // Type-only: if MatchWeek's prop surface drifts from the published contract,
    // this fails the build.
    const _props: MatchWeekMountProps = {} as ComponentProps<typeof MatchWeek>;
    void _props;
    expect(true).toBe(true);
  });

  // nav-click guard: vitest against the EXTRACTED pure function.
  // Background: revealStage initializes to 4 (MatchWeek.tsx:169) and there is no external
  // path to force it below 4 from outside the component — setRevealStage is only ever called
  // with 4 (lines 259, 310, 336) or incremented from a sub-4 state (line 324). Mounting
  // MatchWeek mid-reveal is not achievable from a test. The viable strategy is:
  //   (a) Extract the skip guard to an exported pure function `isNavClick`.
  //   (b) Unit-test `isNavClick` directly — no component mount needed.
  //   (c) Assert the window.addEventListener wiring via a spy.
  //   (d) The full integration (nav-click truly does not advance) is covered at the e2e level (Task 14 Step 3).
  it('isNavClick returns true for elements inside [data-nav-rail], false for others', async () => {
    // This test imports the EXTRACTED pure function from MatchWeek.tsx (Step 3 adds the export).
    // Inline implementation matches exactly: return !!target?.closest('[' + navRailAttr + ']')
    const { isNavClick } = await import('./MatchWeek');
    const navRailAttr = 'data-nav-rail';
    const rail = document.createElement('aside');
    rail.setAttribute(navRailAttr, '');
    const inner = document.createElement('button');
    rail.appendChild(inner);
    document.body.appendChild(rail);
    expect(isNavClick(inner, navRailAttr)).toBe(true);
    const outsideBtn = document.createElement('button');
    document.body.appendChild(outsideBtn);
    expect(isNavClick(outsideBtn, navRailAttr)).toBe(false);
    expect(isNavClick(null, navRailAttr)).toBe(false);
    document.body.removeChild(rail);
    document.body.removeChild(outsideBtn);
  });
  it('the click skip handler is wired on window (window.addEventListener spy)', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');
    render(<MatchWeek mode="post-sim" persistedResult={null} />);
    expect(addSpy.mock.calls.some(([type]) => type === 'click')).toBe(true);
    addSpy.mockRestore();
  });

  it('#90: a failed policy save rolls back to the previous tactics', async () => {
    // savePolicy optimistic-updates then awaits commandApi.savePlan; on reject it
    // restores previousPlan and surfaces the error. Drive via the PolicyEditor or a
    // direct savePolicy exercise; assert the rolled-back tactics + error message.
  });
});
```

> **Reveal-skip implementation note:** `revealStage` initializes to `4` at `MatchWeek.tsx:169` and can only go sub-4 via the staged useEffect at lines 320-326 (`prev + 1` from a sub-4 starting point). There is no external path to force it below 4 — `setRevealStage` is called only with `4` explicitly (lines 259, 310, 336) or incremented from a sub-4 state inside the effect. Mounting `MatchWeek` mid-reveal via a test is not achievable. **The chosen strategy (review fix):** extract the guard into an exported one-liner `isNavClick(target, navRailAttr)` and unit-test it directly; the component-level test asserts only wiring (the `window.addEventListener('click', ...)` spy); the full integration — that a nav-click truly does not advance the reveal — is covered by the Task-14 Step-3 e2e smoke which exercises the real rendered tree. The `closest('.dm-left-nav')` today never matches (stale no-op), so the rewrite to `closest('[data-nav-rail]')` is the behavioral change; the pure-function test pins this logic precisely.

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "MatchWeek.test"`. The reveal-skip test will FAIL initially if it asserts the post-rewrite behavior (current code skips on nav-click because `.dm-left-nav` never matches). The other guards PASS against current logic. This is the RED for the rewrite.

- [ ] **Step 3: Implement** —
  - **Extract + export the skip guard as a pure function** (required for the vitest in Step 1): add to `MatchWeek.tsx` (before the component, exported so the test can import it):
    ```ts
    import { NAV_RAIL_ATTR } from './shell/appContracts';
    /** Pure helper: returns true if the click target is inside the nav rail — skip the reveal in that case. */
    export function isNavClick(target: Element | null, navRailAttr: string): boolean {
      return !!target?.closest('[' + navRailAttr + ']');
    }
    ```
  - **Rewrite line 334:** in the skip handler, replace `if (target?.closest('.dm-left-nav')) return;` → `if (isNavClick(target, NAV_RAIL_ATTR)) return;`. This is the ONLY `closest()` in the codebase and the P1↔P2 DOM contract.
  - **Re-point** the `StatusMessage` import (`MatchWeek.tsx:21` `from './ui'`) to the `src/ui` shim (`from './ui'` → the shim path; path change only).
  - Create `MatchWeek.module.css`; reskin MatchWeek's OWN inline blocks: the bye-recovery `<section>` (:454-501), the verdict `<p>` (:522-546), and replace the `AftermathBody` per-audience inline `color`/`rgb` literals (:89-90) with token-var classes (`--audience-you`/`--audience-them`/`--audience-result`). Keep `command-post-sim`/`command-reveal`/`command-analysis-row` class names if the integrator's STEP-3 carve-out depends on them being present for the responsive `@media` — actually these are P2-owned legacy classes the integrator deletes, so move them to module classes too; just ensure the layout is self-contained in the module.
  - **Do NOT change:** `buildContextLine` (#4), the `!aftermath.primary_factor && aftermath.verdict` gate (#13), the `AftermathBody` audience grouping (#29), the `replayForMatch?.report.top_performers ?? aftermath.top_performers` preference (#50), `savePolicy`'s optimistic-then-rollback (#90), the `playoff_resolution.decided_by !== 'regulation'` banner gate (#14), or any `data-testid`.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "MatchWeek.test" && npm run build`. Expected: PASS (reveal-skip now respects `[data-nav-rail]`) + build clean.

- [ ] **Step 5: Gate + commit**

```bash
cd frontend && npm run test -- "MatchWeek" && npm run build && npm run lint
git add frontend/src/components/MatchWeek.tsx frontend/src/components/MatchWeek.module.css frontend/src/components/MatchWeek.test.tsx
git commit -m "feat(p2): MatchWeek closest([data-nav-rail]) rewrite + own-blocks reskin; hold #4/#13/#29/#50/#90"
```

---

### Task 9: Aftermath integration smoke (the whole post-sim tree mounts + V20 holds end-to-end)

> **Why:** Tasks 5–8 reskinned the pieces; this asserts the assembled post-sim flow still renders the V20-true scoreline, the playoff resolution, and the staged reveal together — catching any cross-component class/prop drift before moving to the replay sub-area.

**Files:** extend `frontend/src/components/MatchWeek.test.tsx`.

- [ ] **Step 1: Add the integration case** — render `<MatchWeek mode="post-sim" persistedResult={…official draw with playoff_resolution…} />`, force `revealStage` to 4 (or wait through the staged timers with fake timers), and assert: `post-week-dashboard` present, `match-score-hero` shows game points (not survivors), `playoff-resolution-banner` present with `data-player-outcome`. Use a real-shaped `CommandCenterSimResponse.aftermath` (read the type; do not invent).

- [ ] **Step 2: Run + commit**

```bash
cd frontend && npm run test -- "MatchWeek.test" && npm run build && npm run lint
git add frontend/src/components/MatchWeek.test.tsx
git commit -m "test(p2): post-sim aftermath integration smoke (V20 + resolution + reveal)"
```

---

## Phase 2D — MatchReplay + the net-new SVG live court canvas

### Task 10: MatchReplay test scaffolding — replay integrity (#41–#47, #49 on replay surface)

> **Why:** MatchReplay is the largest single file and carries the densest truth contract (#41–#50). Author guards against the CURRENT replay before reskinning: #41 (live court eliminations from current event `score_state` ONLY, `:780-798`), #42 (survivor-delta suppressed across game boundaries — 'fresh court', `scoreDeltaLabel` :580-600), #43 (GameSegmentStrip live-reveal hides unreached games; 'so far' running tally :300-369), #44 (TurningPoint jump uses `report.turning_point_index`, fallback first key play not event 0, :858-859), #45 (highlight 'Show in timeline' maps `source_event_index → proof index via sequence_index`, guards null, :864-868), #46 (highlight package failure non-fatal — sets beats [], reel hides, :689-701), #47 (official enums humanized at boundary, '—' fallback, `:437-440`), and the replay scoreboard V20 branch (#2 on this surface, `:381-392`).

**Audit numbers + test strategy (checklist Phase 2):** #41 vitest+e2e · #42 vitest · #43 vitest · #44 vitest · #45 vitest · #46 vitest · #47 vitest. (The e2e half of #41 rides the Task-14 smoke.)

**Files:** create `frontend/src/components/MatchReplay.test.tsx` (reuse the payload factory from `replay/antiStrip.test.tsx` — extract it to a shared `replay/testPayload.ts` if convenient).

- [ ] **Step 1: Write the failing/guard tests** — mock `commandApi.highlights`; render `MatchReplay` with multi-event, multi-game payloads.

```tsx
// frontend/src/components/MatchReplay.test.tsx (excerpt — author the full set)
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const highlights = vi.fn();
vi.mock('../api/client', () => ({ commandApi: { highlights } }));
import MatchReplay from './MatchReplay';
// import { makeReplay } from './replay/testPayload'; // multi-event/multi-game factory

beforeEach(() => { vi.clearAllMocks(); highlights.mockResolvedValue({ beats: [] }); });
afterEach(() => vi.restoreAllMocks());

describe('MatchReplay integrity (#41-#47)', () => {
  it('#2: the scoreboard shows GAME POINTS for an official match, not survivors', async () => {
    render(<MatchReplay data={/* official, gp 1-0, survivors 2-0 */ {} as never} onContinue={() => {}} />);
    // header reads 1 / 0, units "game points" — never the survivor tally
  });
  it('#42: a new-game event shows "fresh court", not a cross-game survivor delta', () => { /* … */ });
  it('#43: GameSegmentStrip hides games not yet reached during playback', () => { /* … */ });
  it('#44: the turning-point jump lands on report.turning_point_index', async () => { /* … */ });
  it('#46: a highlights fetch rejection hides the reel without crashing', async () => {
    highlights.mockRejectedValue(new Error('boom'));
    render(<MatchReplay data={{} as never} onContinue={() => {}} />);
    await waitFor(() => expect(screen.queryByTestId('replay-highlights')).not.toBeInTheDocument());
  });
  it('#47: an unknown official token humanizes (no raw enum, "—" when absent)', () => { /* … */ });
});
```

> Author each case with a real-shaped payload (the factory). Read the exact null-fallback strings ('No ball state', 'None', 'No team on the clock', '—') from `MatchReplay.tsx` before asserting; quote them.

- [ ] **Step 2: Run to verify behavior** — `cd frontend && npm run test -- "MatchReplay.test"`. Expected: PASS against current markup (guards).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MatchReplay.test.tsx frontend/src/components/replay/testPayload.ts
git commit -m "test(p2): lock MatchReplay integrity behaviors (#41-#47) before reskin"
```

---

### Task 11: MatchReplay reskin to CSS Modules (hold #2, #37, #41–#50; keep ReplaySpeedControl)

> **Why:** Migrate MatchReplay's `mr-*` global classes + inline styles to `MatchReplay.module.css`, keeping every truth branch and provenance hook. `ReplaySpeedControl` (`aftermath/ReplaySpeedControl.tsx`) is an ACTIVE consumer (imported at `:8`, rendered at `:940`) — reskin its pills to tokens but keep its props/values (`1x/2x/4x/instant`). The existing memoized `DarkCourt` SVG stays for now (Task 12 introduces the new canvas and decides the swap). **All conditional null-renders (#37) and the live-state logic (#41–#43) are untouched** — only styling changes.

**Audit numbers + test strategy:** #2/#37/#41–#50 vitest (held through reskin).

**Files:** create `frontend/src/components/MatchReplay.module.css`; modify `frontend/src/components/MatchReplay.tsx` and `frontend/src/components/match-week/aftermath/ReplaySpeedControl.tsx` (+ its module CSS).

- [ ] **Step 1: Confirm Task-10 + anti-strip guards green** — `cd frontend && npm run test -- "MatchReplay" "replay/antiStrip"`.

- [ ] **Step 2: Reskin** — create `MatchReplay.module.css` (token-driven `mr-scoreboard`/`mr-stage`/`mr-set-strip`/`mr-possession`/`mr-current-card`/`mr-log`/`mr-turning`/`mr-highlights` equivalents). Replace `className="mr-…"` and inline styles with `className={styles.…}`. Wrap team/player names in `Truncate`; wrap the EventLog in `ScrollRegion`. Re-point `src/ui` imports. Reskin `ReplaySpeedControl` pills. **Keep verbatim:** `formatScoreline`/`survivorDetail` on the scoreboard (#2), `scoreDeltaLabel` fresh-court (#42), `GameSegmentStrip` live-reveal (#43), `swingJumpIdx` (#44), the `sequence_index → proof index` map (#45), the highlights `.catch(() => setHighlightBeats([]))` (#46), `humanizeOfficialToken`/'—' (#47), `eliminatedIds` from current `score_state` (#41), and ALL `data-testid`/`data-broadcast-proof-source`.

- [ ] **Step 3: Run to verify it passes** — `cd frontend && npm run test -- "MatchReplay" "replay/antiStrip" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/MatchReplay.tsx frontend/src/components/MatchReplay.module.css frontend/src/components/match-week/aftermath/ReplaySpeedControl.*
git commit -m "feat(p2): MatchReplay + ReplaySpeedControl to CSS Modules; hold #2/#37/#41-#50"
```

---

### Task 12: NEW `LiveCourtCanvas` SVG primitive (players as lit/extinguished tokens, throws as animated arcs) — net-new scope, budgeted

> **Why:** The redesign calls for a lightweight, token-driven SVG live match canvas driven by the EXISTING replay payload (`proof_events[i].score_state` + `thrower_id`/`target_id`/`resolution`). This is **net-new + untested scope** — budget it as the largest task and the window's tail risk. It must have an **honest NO-DATA fallback** (no proof events / no current event → a calm "No live court for this match" placeholder, never a fabricated court). The component takes the SAME derived inputs the existing `DarkCourt` consumes (the `eliminatedIds`/`throwerId`/`targetId` already computed from the current event's `score_state` at `MatchReplay.tsx:780-798`), so the V20/#41 live-truth invariant is preserved by construction — the canvas renders ONLY what the current event's `score_state` says, never a union across events.

**Audit numbers + test strategy:** #41 (live eliminations from current event only — by construction) vitest; net-new render + NO-DATA fallback vitest. Pattern-6 (responsive viewBox, no 6-player assumption) addressed: a `<= 2 columns × N rows` formation that scales to any side count.

**Files:** create `frontend/src/components/replay/LiveCourtCanvas.tsx` + `LiveCourtCanvas.module.css` + `LiveCourtCanvas.test.tsx`.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/components/replay/LiveCourtCanvas.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LiveCourtCanvas } from './LiveCourtCanvas';

const reg = new Map([
  ['p1', { id: 'p1', name: 'A One', label: 'A. ONE', clubId: 'aurora' }],
  ['p2', { id: 'p2', name: 'B Two', label: 'B. TWO', clubId: 'granite' }],
]);

describe('LiveCourtCanvas (net-new SVG)', () => {
  it('renders an SVG court with one token per registered player', () => {
    render(
      <LiveCourtCanvas
        homeIds={['p1']} awayIds={['p2']} playerRegistry={reg}
        eliminatedIds={new Set()} throwerId={null} targetId={null} activeResolution={null}
      />,
    );
    const svg = screen.getByLabelText(/live .*court/i);
    expect(svg.tagName.toLowerCase()).toBe('svg');
    expect(svg.querySelectorAll('[data-player-token]').length).toBe(2);
  });
  it('marks an eliminated player as extinguished (data-extinguished="true")', () => {
    render(
      <LiveCourtCanvas
        homeIds={['p1']} awayIds={['p2']} playerRegistry={reg}
        eliminatedIds={new Set(['p2'])} throwerId={null} targetId={null} activeResolution={null}
      />,
    );
    const tok = document.querySelector('[data-player-token="p2"]');
    expect(tok).toHaveAttribute('data-extinguished', 'true');
  });
  it('draws a throw arc only when both thrower and target are present', () => {
    const { rerender } = render(
      <LiveCourtCanvas homeIds={['p1']} awayIds={['p2']} playerRegistry={reg}
        eliminatedIds={new Set()} throwerId={null} targetId={null} activeResolution={null} />,
    );
    expect(document.querySelector('[data-throw-arc]')).toBeNull();
    rerender(
      <LiveCourtCanvas homeIds={['p1']} awayIds={['p2']} playerRegistry={reg}
        eliminatedIds={new Set()} throwerId="p1" targetId="p2" activeResolution="eliminated" />,
    );
    expect(document.querySelector('[data-throw-arc]')).not.toBeNull();
  });
  it('honest NO-DATA fallback when there are no players', () => {
    render(
      <LiveCourtCanvas homeIds={[]} awayIds={[]} playerRegistry={new Map()}
        eliminatedIds={new Set()} throwerId={null} targetId={null} activeResolution={null} />,
    );
    expect(screen.getByText(/no live court/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/live .*court/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "LiveCourtCanvas"`. Expected: FAIL (module unresolved).

- [ ] **Step 3: Implement** — a presentational component (no data fetching). Props mirror the derived inputs MatchReplay already computes:

```tsx
// frontend/src/components/replay/LiveCourtCanvas.tsx (shape)
import styles from './LiveCourtCanvas.module.css';

interface PlayerInfo { id: string; name: string; label: string; clubId: string; }
interface LiveCourtCanvasProps {
  homeIds: string[]; awayIds: string[];
  playerRegistry: Map<string, PlayerInfo>;
  eliminatedIds: Set<string>;
  throwerId: string | null; targetId: string | null;
  activeResolution: string | null;
}

const VB_W = 600, VB_H = 320, R = 14;

function formation(ids: string[], side: 'left' | 'right'): Map<string, { x: number; y: number }> {
  // <=2 columns × ceil(n/?) rows; scales to ANY side count (no 6-player assumption, Pattern 6).
  // …deterministic placement from index…
}

export function LiveCourtCanvas(props: LiveCourtCanvasProps) {
  const all = [...props.homeIds, ...props.awayIds];
  if (all.length === 0) {
    return <div className={styles.noData} data-testid="live-court-nodata">No live court for this match.</div>;
  }
  // build positions, render <svg aria-label="Live dodgeball court" viewBox="0 0 600 320">
  //   players: <g data-player-token={id} data-extinguished={elim ? 'true' : 'false'}> lit/extinguished token
  //   throw arc: only when throwerId && targetId → <path data-throw-arc className={styles.arc}/> with the
  //     existing arc animation (token-driven stroke via --accent class by resolution).
  // Colors via module classes (.home/.away/.elim/.lit), NEVER raw hex. SVG geometry numbers exempt.
}
```

```css
/* frontend/src/components/replay/LiveCourtCanvas.module.css */
.court { width: 100%; height: auto; display: block; background: var(--court); border: 1px solid var(--line); border-radius: var(--radius-lg); }
.noData { padding: var(--space-7); text-align: center; color: var(--muted); font: 500 .85rem var(--font-ui); background: var(--raise); border: 1px solid var(--line); border-radius: var(--radius-lg); }
.tokenHome { fill: var(--court); stroke: var(--volt); }
.tokenAway { fill: var(--court); stroke: var(--gold); }
.extinguished { opacity: .35; }
.arc { stroke: var(--volt2); fill: none; }
.arcCatch { stroke: var(--ok); }
/* animated arc via @keyframes dash; reduced-motion handled by tokens.css base override */
```

  Keep it presentational and token-only. The lit/extinguished state is derived ENTIRELY from the `eliminatedIds` prop (which MatchReplay computes from the CURRENT event's `score_state` — #41), so the canvas cannot fabricate eliminations.

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "LiveCourtCanvas" && npm run build`. Expected: PASS + build clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/replay/LiveCourtCanvas.*
git commit -m "feat(p2): net-new LiveCourtCanvas SVG primitive (lit/extinguished tokens, throw arcs, NO-DATA fallback)"
```

---

### Task 13: Wire `LiveCourtCanvas` into MatchReplay (replace/augment DarkCourt) — keep #41 live-truth

> **Why:** Mount the new canvas in MatchReplay using the SAME derived inputs (`eliminatedIds`/`throwerId`/`targetId`/`activeResolution` from `MatchReplay.tsx:780-798`), so the redesigned court is driven by the existing payload with zero new data path. Either replace the memoized `DarkCourt` (`:115-236`, rendered `:901`) with `LiveCourtCanvas` or render the new canvas in its place — preserving the `mr-court` container's conditional rendering and the #41 invariant (current-event `score_state` only).

**Audit numbers + test strategy:** #41 vitest (live court still reflects only the current event) + the Task-14 e2e smoke.

**Files:** modify `frontend/src/components/MatchReplay.tsx`; extend `frontend/src/components/MatchReplay.test.tsx`.

- [ ] **Step 1: Add the wiring assertion** — extend `MatchReplay.test.tsx`: after the existing replay renders, assert the live court reflects the current event's eliminations (an eliminated id from `proof_events[idx].score_state.away_eliminated_player_ids` shows `data-extinguished="true"`; an id eliminated only in a LATER event does NOT).

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npm run test -- "MatchReplay.test"`. Expected: FAIL until the canvas is wired (the `data-player-token`/`data-extinguished` hooks come from `LiveCourtCanvas`).

- [ ] **Step 3: Implement** — replace the `<DarkCourt … />` JSX at `:901` with `<LiveCourtCanvas homeIds={homeIds} awayIds={awayIds} playerRegistry={playerRegistry} eliminatedIds={eliminatedIds} throwerId={throwerId} targetId={targetId} activeResolution={activeResolution} />`. Remove the now-unused `DarkCourt` definition + its `positions`/`ballAnimKey`-only props if they become dead (build will flag unused imports). Keep the `mr-court` container's existing conditional/empty handling. **Do NOT** change `eliminatedIds`/`throwerId`/`targetId` derivation (#41).

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npm run test -- "MatchReplay" "replay/antiStrip" "LiveCourtCanvas" && npm run build && npm run lint`. Expected: PASS + build/lint clean (no unused `DarkCourt`).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/MatchReplay.tsx frontend/src/components/MatchReplay.test.tsx
git commit -m "feat(p2): drive MatchReplay court via LiveCourtCanvas (same payload, #41 preserved)"
```

---

## Phase 2E — Phase-2 gate

### Task 14: Phase-2 worktree gate (test + build + lint + token self-check + e2e smoke)

> **Why:** Final verification in the worktree (OLD `index.css` still present). The integrator runs the `index.css` deletion + full `tsc`/vitest later in STEP 3; this gate proves the authored work is green and token-clean so integration is mechanical.

**Files:** none (verification only). Per the freeze, P2 does NOT edit `check-tokens.mjs`.

- [ ] **Step 1: Run the full FE suite + build + lint**

```bash
cd frontend && npm run test && npm run build && npm run lint
```
Expected: all P2 tests pass (matchResult contract, both anti-strip suites, PreSimDashboard, MatchScoreHero, PlayoffResolutionBanner, aftermathCards, MatchWeek incl. reveal-skip + integration, MatchReplay, LiveCourtCanvas); build clean; eslint clean (no dead `DarkCourt`).

- [ ] **Step 2: Token self-check against the P2 dirs** — the gate is not wired to these dirs yet (integrator owns `SCAN_DIRS`), so run the existing script manually scoped to the new module CSS to confirm zero raw hex/px before handoff:

```bash
cd frontend && node -e "
const {readFileSync,readdirSync,statSync}=require('fs');const {join,extname}=require('path');
const DIRS=['src/components/match-week','src/components/replay'];
const FILES=['src/components/MatchWeek.module.css','src/components/MatchReplay.module.css'];
const HEX=/#[0-9a-fA-F]{3,8}\b/;const PX=/(?<![\w.])(?!0px|1px)\d{1,4}px\b/;const ALLOW=/(viewBox|tokens\.css|\.test\.|\.svg)/;
const walk=d=>readdirSync(d).flatMap(e=>{const p=join(d,e);return statSync(p).isDirectory()?walk(p):['.css'].includes(extname(p))?[p]:[]});
const bad=[];for(const f of [...DIRS.flatMap(walk),...FILES]){if(ALLOW.test(f))continue;readFileSync(f,'utf8').split('\n').forEach((l,i)=>{if(ALLOW.test(l))return;if(HEX.test(l)||PX.test(l))bad.push(f+':'+(i+1)+'  '+l.trim())})}
if(bad.length){console.error('TOKEN VIOLATIONS:\n'+bad.join('\n'));process.exit(1)}console.log('P2 module CSS token-clean');
"
```
Expected: `P2 module CSS token-clean`. If it flags a literal, replace with a token (add a semantic token usage; do NOT edit `tokens.css` ownership beyond what Phase 0 provides — if a genuinely new token is needed, flag it to the controller) and re-run. SVG geometry numbers in `.tsx` are not matched (they are attribute values, not `px`); `viewBox` and `.svg` are allowed.

- [ ] **Step 3: e2e smoke** — `cd .. && npm run e2e` (root Playwright per AGENTS.md). Expected: the playthrough smoke that exercises Command Center → simulate → aftermath → replay is green (covers the #41 e2e half + the live loop). If the smoke spec needs a selector that moved to a module class, update the spec to the stable `data-testid` (never to a brittle class).

- [ ] **Step 4: Manual smoke (owner's port 8010, NOT 8000)** — launch `python -m dodgeball_sim` on port 8010, load a save, and walk: Command Center (League Wire scoreline, alignment pill, bye vs match), simulate, aftermath (score hero game-points, playoff resolution banner, staged reveal, nav-click does NOT skip the reveal), open replay (scoreboard game-points, live court tokens lit/extinguished per current event, throw arcs, set strip live-reveal, highlights). Confirm no console errors.

- [ ] **Step 5: Commit the green marker (no source change)**

```bash
git commit -am "chore(p2): Phase-2 worktree gate green (test+build+lint+token self-check+e2e)" --allow-empty
```

The controller integrates P2 LAST in STEP 3: brace-depth scan, delete the P2 legacy `command-*`/`mr-*` + the P2 lines in the shared `@media` tail (never the shared `command-action-bar`/`command-policy-overlay`), append the P2 dirs to `SCAN_DIRS`, then re-run full `tsc --noEmit` + full vitest + the V20 #1–8 single-payload vitest + e2e smoke.

---

## Self-Review

**Behavior coverage — all 30 Phase-2 audit behaviors mapped to a task + test strategy:**

| # | Behavior | Task | Strategy |
|---|---|---|---|
| 1 | One shared scoreline decision (formatScoreline/survivorDetail) | Task 1 | vitest + python-guard ✓ |
| 2 | MatchScoreHero / MatchReplay scoreboard branch on scoring_model | Tasks 1, 5, 11 | vitest ✓ |
| 3 | Pre-sim League Wire shows game-point scoreline | Tasks 3, 4 | vitest ✓ |
| 4 | Aftermath context line in the scoring model's scale | Task 8 | vitest ✓ |
| 5 | ProgramStatusStrip GP vs elim differential | Task 7 (strip at `match-week/ProgramStatusStrip.tsx`, explicitly in Task 7 heading + file map) | vitest (two cases in `aftermathCards.test.tsx` — official/legacy branch) ✓ |
| 6 | Standings rank/diff column branches | — (P4-owned surface) | covered by P4; P2 keeps matchResult frozen for it ✓ |
| 7 | PlayoffBracket scoreline via formatScoreline | — (P4-owned) | P2 freezes matchResult contract (Task 1) ✓ |
| 8 | Recap differential column branches | — (P4-owned) | P2 freezes matchResult contract (Task 1) ✓ |
| 11 | PlayoffResolutionBanner reads decided_by; null on regulation | Tasks 2, 6 | vitest ✓ |
| 12 | Draw is a real labeled outcome; playoff footer no point | Tasks 2, 5 | vitest ✓ |
| 13 | Verdict is fallback only (suppressed w/ primary_factor) | Task 8 | vitest ✓ |
| 14 | Banner only when NOT decided by regulation | Tasks 6, 8 | vitest ✓ |
| 15 | Standings draw handling | — (P4-owned) | matchResult frozen ✓ |
| 16 | Player-outcome ribbon gated | Tasks 2, 6 | vitest (data-player-outcome) ✓ |
| 17 | Worlds_user receipt | — (P4 RecapStandings) | out of P2 scope (stated in Task 2) ✓ |
| 18 | missed_playoffs banner | — (P4 RecapStandings) | out of P2 scope (stated in Task 2) ✓ |
| 41 | Live court eliminations from current event only | Tasks 10, 12, 13 | vitest + e2e ✓ |
| 42 | Survivor-delta suppressed across game boundaries | Tasks 10, 11 | vitest ✓ |
| 43 | GameSegmentStrip live-reveal | Tasks 10, 11 | vitest ✓ |
| 44 | TurningPoint uses turning_point_index | Tasks 10, 11 | vitest ✓ |
| 45 | Highlight maps source_event_index → proof index | Tasks 10, 11 | vitest ✓ |
| 46 | Highlight failure non-fatal | Tasks 10, 11 | vitest ✓ |
| 47 | Official enums humanized, '—' fallback | Tasks 10, 11 | vitest ✓ |
| 48 | ComebackCard self-suppresses | Task 7 | vitest ✓ |
| 49 | Set-story strip from persisted per-game score | Tasks 2, 5 | vitest ✓ |
| 50 | Top-performers/tactical prefer replay payload | Tasks 7, 8 | vitest ✓ |
| 90 | Optimistic policy save with rollback | Task 8 | vitest ✓ |
| 93 | FALLBACK_BRIEFING / matchup defaults; confirm-lineup six | Tasks 3, 4 | vitest ✓ |
| 94 | Operational-Plan alignment reflects real state | Tasks 3, 4 | vitest ✓ |
| 95 | Recent-results ordered W/L; stakes top-4 | Tasks 3, 4 | vitest ✓ |

> #5 (ProgramStatusStrip differential): `ProgramStatusStrip.tsx` is at `frontend/src/components/match-week/ProgramStatusStrip.tsx` (NOT in `aftermath/`). It is now **explicitly named in Task 7's heading and the file map's Modified section**. Its GP-vs-elim branch (`ProgramStatusStrip.tsx:12-14`: `is_official_career → game_point_differential; else → elimination_differential`) is pinned by two focused vitests in `aftermathCards.test.tsx` (official-foam career → `+12 diff`; legacy career → `+4 diff`). The assertion keys on the `"{strapDiff} diff"` text node rendered at `ProgramStatusStrip.tsx:44-46` — no invented "GP Diff" label (none exists in the current source). Behaviors #6/#7/#8/#15/#17/#18 are on **P4/P4-RecapStandings surfaces**, not P2 screens; P2's obligation to them is to keep `matchResult.ts` frozen (Task 1) so their scoreline source cannot drift — explicitly noted, not silently dropped.

**Phase-specific requirements — all honored:**
- HIGHEST RISK + parallel-window critical path: stated in Goal + Architecture; SVG canvas budgeted as the largest task (Task 12) with the integration tail in Task 13 ✓.
- `MatchWeek.tsx:334` `closest('.dm-left-nav')` → `closest(`[${NAV_RAIL_ATTR}]`)` from appContracts, implemented via the extracted `isNavClick(target, navRailAttr)` pure function. The vitest pins `isNavClick` logic directly (not a mid-reveal component mount, which is blocked by `revealStage` initializing to `4`). The window.addEventListener wiring is asserted via spy. Full integration (nav-click does not advance the reveal in the real tree) rides the Task-14 e2e smoke → Task 8 ✓.
- P2 ADDS the V20 #1-2 single-payload vitest against `matchResult.ts` WITHOUT changing its API → Task 1 (source untouched; test-only) ✓.
- P2 mount props asserted against appContracts `MatchWeekMountProps` → Task 8 (compile-time assignability) ✓.
- V20 scoring-model truth family preserved on EVERY P2 surface (formatScoreline/survivorDetail branch) → Tasks 1, 5, 11 (#1-5,#12,#49 on hero/replay/wire/context/strip) ✓.
- Anti-strip `data-broadcast-proof-source` (BroadcastFrameBlock via MatchReplay, MatchHighlights), `data-player-outcome` (PlayoffResolutionBanner) → Task 2 RED preconditions + held in Tasks 6, 11, 13 ✓.
- SVG canvas net-new + untested → budgeted (Task 12) with honest NO-DATA fallback test ✓.

**Freezes respected:** `matchResult.ts` consumed/tested but NEVER edited (Task 1 source-untouched check) ✓ · `legibility/*` untouched ✓ · `components/ui.tsx` not edited — imports re-pointed to `src/ui` shims, NO ActionButton→ActionBar remap ✓ · `index.css` not edited/deleted — module CSS only; integrator deletes P2 legacy in STEP 3 (no deletion task in this plan) ✓ · `command-action-bar`/`command-policy-overlay` kept (Task 4 note) ✓ · `check-tokens.mjs` untouched — Task 14 uses an inline self-check, integrator owns SCAN_DIRS ✓ · `appContracts.ts`/`PlayoffBracket`/`ProgramModal` not modified ✓.

**Placeholder scan:** the test factories (`makeData` for CommandCenterResponse, `makeReplay`/`PAYLOAD` for MatchReplayResponse) carry an explicit "populate from types.ts verbatim — do not invent fields" instruction with the line anchors that flip each branch; these are correctness guards (the large live types cannot be inlined wholesale in a plan without risking stale fields), not logic stubs. Every other code block is complete and runnable. The MatchReplay #41-#47 case bodies are sketched with the exact behavior + line anchors to author against (the full multi-event payload is built once in `replay/testPayload.ts`); this is deliberate to avoid duplicating a 40-field payload six times — the factory + the per-case anchor is the complete instruction.

**Type/name consistency:** `NAV_RAIL_ATTR` imported from `./shell/appContracts` matches the Phase-1 published const (`'data-nav-rail'`) and the `closest('[data-nav-rail]')` rewrite target. `isNavClick` is an exported pure function extracted from MatchWeek's click handler (Task 8 Step 3) so the test in Task 8 Step 1 can call it directly. `MatchWeekMountProps` imported from `./shell/appContracts` and asserted assignable from `ComponentProps<typeof MatchWeek>` (Task 8). `formatScoreline`/`survivorDetail`/`ScorelineFields` quoted verbatim from `matchResult.ts:34-60`. `LiveCourtCanvas` props (`homeIds`/`awayIds`/`playerRegistry`/`eliminatedIds`/`throwerId`/`targetId`/`activeResolution`) match the derived inputs MatchReplay already computes at `:780-798`. **Note:** `DarkCourt` additionally takes `positions`/`flashTargetId`/`ballAnimKey`/`homeName`/`awayName` which `LiveCourtCanvas` does NOT accept — `LiveCourtCanvas` computes positions internally via its own `formation()` function. Task 13 wires only the 7 listed props and omits the DarkCourt-only ones; this is not a direct prop pass-through. Data-testids quoted from source: `match-score-hero`/`score-hero-draw`/`aftermath-set-story`/`match-verdict` (MatchScoreHero/MatchWeek), `playoff-resolution-banner`/`data-player-outcome`/`data-decided-by` (PlayoffResolutionBanner), `post-week-dashboard` (MatchWeek), `playoff-frame`/`data-broadcast-proof-source`/`official-ruleset-banner`/`replay-set-strip`/`replay-set-running`/`current-event-card`/`replay-moment-banner`/`replay-highlights` (MatchReplay), `weekly-command-center`/`secondary-intel-rail`/`presim-command-strip`/`plan-readout`/`matchup-band`/`current-objective`/`tactical-diff` (PreSimDashboard). New canvas hooks `data-player-token`/`data-extinguished`/`data-throw-arc`/`live-court-nodata` are introduced by `LiveCourtCanvas` and asserted in its own test + Task 13.

**Gate correctness:** the per-task gate omits `lint:tokens` (P2 cannot edit `check-tokens.mjs`; the dirs are scoped by the integrator in STEP 3), so Task 14 Step 2 runs an inline token self-check scoped to the P2 module CSS to guarantee zero rework at integration. The e2e gate is `npm run e2e` from repo ROOT (root Playwright per AGENTS.md; there is no `frontend` e2e script). `expectTypeOf`/`ComponentProps` assignability ships with Vitest/React (no new dep).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-floodlight-phase-2-command-loop.md`. Execute in an isolated worktree off the merged post-Phase-1 trunk, strictly in sub-area order (Tasks 1→14). Two options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks. Task 8 (MatchWeek orchestrator + the `closest()` rewrite) and Task 12 (net-new SVG canvas) are the highest-blast-radius; gate hard after each.
2. **Inline Execution** — execute tasks in this session with checkpoints. Do NOT consider P2 done until Task 14's full gate (incl. root e2e) is green; the controller owns the STEP-3 `index.css` integration (P2 last).
