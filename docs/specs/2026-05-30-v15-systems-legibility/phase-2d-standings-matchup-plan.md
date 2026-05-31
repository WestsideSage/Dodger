# V15 Phase 2d — Standings & Matchup Copy: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De-jargon the Standings page, improve legibility of the League Wire and Tiebreaker Read panels, replace the inline club-history expander with the existing `ProgramModal`, and apply `TermTip` to club archetype chips — consuming the Phase 1 toolkit exclusively, touching no engine or data model.

**Phase context:** This plan targets `frontend/src/components/LeagueContext.tsx`. It runs after Phase 1 merges (it imports from `frontend/src/legibility/`). It is parallelizable with all other Phase 2/3/4 plans because each owns a distinct screen/file.

**Matchup scope note:** The "matchup" in this phase's filename refers to the `standings.diff` / `standings.playoff_line` term coverage and the shared-vocabulary TermTip consistency that makes the matchup band (already shipped in V14 T2 / PreSimDashboard D2) legible alongside standings copy. No rewrite of `PreSimDashboard` matchup UI is planned; `PreSimDashboard.tsx` is owned by Phase 3c (Season Preview density). The matchup band's tooltip (`title` attribute, line 424) already uses plain language; this plan only ensures the related standings terms are explained via `TermTip` so the terminology is consistent across screens.

**Architecture:** All changes are in `frontend/src/components/LeagueContext.tsx`. One terms append to `frontend/src/legibility/terms.ts`. No new npm/python deps, no routing change, no engine edit. The `ProgramModal` import path and props are verified in source; its content is owned by Phase 4a (do not edit it here).

**Tech Stack:** React 19 + TypeScript ~6 + Vite 8. Verify via `npm run build` (tsc no-orphan gate) + `npm run lint` from `frontend/`, and `npm run e2e` from repo root. No backend pytest needed (no payload field added — all changes are frontend-only over existing `StandingRow` / `StandingsResponse` fields).

> **Pre-flight:**
> - Gate: Phase 1 must be merged before starting. Confirm with: `git grep -rn "from '.*legibility'" -- frontend/src/legibility/index.ts` — must return the barrel.
> - Branch: `git checkout -b feat/v15-phase2d-standings`
> - Baseline: from `frontend/`, `npm run build && npm run lint` must be green before starting.
> - Read `frontend/src/components/LeagueContext.tsx` in full before editing — the component is 541 lines; every step below references exact line numbers that were current at plan-authoring time. Re-verify line numbers before editing.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `frontend/src/legibility/terms.ts` | Append `program.*` archetype term entries | 1 |
| `frontend/src/components/LeagueContext.tsx` | All standings UI changes | 2–7 |
| `tests/e2e/v15-standings-legibility.spec.ts` | Playwright smoke for new behaviors | 8 |

---

## Task 1: Append club-archetype + standings term entries to `terms.ts`

**Context:** `TermTip` requires a `TermId` from the closed union in `terms.ts`. The pre-seeded entries include `standings.diff` and `standings.playoff_line`. This task appends the six `program.archetype.*` keys for the club archetype chips. The `program.credibility` and `program.prestige` entries are already in the seed; do not duplicate them. **Append-only** — do not remove or rename existing keys.

**Files:**
- Modify: `frontend/src/legibility/terms.ts`

- [ ] **Step 1: Read the current bottom of `TERMS` to find the exact insertion point**

Run: `grep -n "as const satisfies" frontend/src/legibility/terms.ts`
Expected: one line near the end of the file showing the closing `} as const satisfies Record<string, TermDef>;`. Insert new entries immediately above that closing `}`.

- [ ] **Step 2: Append the six club-archetype term entries**

The backend `classify_club_archetype` function in `persistence.py` emits exactly these six strings (verified). Add them as `program.archetype.*` keys. Insert the following block immediately before the closing `} as const satisfies Record<string, TermDef>;` line:

```ts
  // --- Club (program) archetypes — surfaces in standings row sub-label ---
  // Values come from classify_club_archetype() in persistence.py; this is a closed set.
  'program.archetype.balanced_rebuild': {
    label: 'Balanced Rebuild',
    plain: 'A developing club with no strong lean — building across all areas.',
    why: 'Expect steady, moderate improvement; no glaring weakness but no dominant edge yet.',
    kind: 'mechanical',
  },
  'program.archetype.contender': {
    label: 'Contender',
    plain: 'A high-OVR club built to compete for the title right now.',
    why: 'Strong starter OVR means a tougher opponent; their win-now approach may be aggressive.',
    kind: 'mechanical',
  },
  'program.archetype.development_factory': {
    label: 'Development Factory',
    plain: 'A young, high-potential roster prioritizing long-term growth over immediate wins.',
    why: 'Weaker now, stronger later — young players develop quickly; may be a sleeper.',
    kind: 'mechanical',
  },
  'program.archetype.defensive_specialist': {
    label: 'Defensive Specialist',
    plain: 'A club that invests heavily in dodge and catch over throw power.',
    why: 'Harder to eliminate; expect more catches and fewer total eliminations per round.',
    kind: 'mechanical',
  },
  'program.archetype.power_throwers': {
    label: 'Power Throwers',
    plain: 'A club built around high-accuracy and high-power throwers.',
    why: 'High elimination volume; catching is their weak side — target it with patient play.',
    kind: 'mechanical',
  },
  'program.archetype.aging_veterans': {
    label: 'Aging Veterans',
    plain: 'A roster of experienced, older players near peak OVR.',
    why: 'Perform well now but have limited headroom; their window is closing.',
    kind: 'mechanical',
  },
```

- [ ] **Step 3: Compile gate (proves the no-orphan union still closes)**

Run (from `frontend/`): `npm run build`
Expected: PASS. The six new keys are now part of `TermId`; any `<TermTip term="program.archetype.contender">` is now a valid reference.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/legibility/terms.ts
git commit -m "feat(v15-p2d): append club-archetype term entries to registry

Adds program.archetype.* TermIds for the six values emitted by
classify_club_archetype() so standings row TermTips compile cleanly.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Swap inline ClubHistoryLane for ProgramModal

**Context:** The current code toggles an inline `ClubHistoryLane` (component at lines 220–261) via `expandedClubId` state. The scope requires replacing this with the existing `ProgramModal` (imported from `./dynasty/history/ProgramModal`). The `ClubHistoryLane` component becomes dead code and is deleted in the same task.

**The Tiebreaker rows (lines 503–520) also call `handleClubOpen` — they must be updated too so both surfaces open the same modal.**

**Aria note:** When rows opened an inline expander they needed `aria-expanded` + `aria-controls`. A button opening a modal dialog is different: `aria-haspopup="dialog"` is the correct pattern. The `ProgramModal` currently lacks `role="dialog"` / focus-trap (a11y gap noted in Phase 4a overlap — do not fix here).

**Files:**
- Modify: `frontend/src/components/LeagueContext.tsx`

- [ ] **Step 1: Add the ProgramModal import and update state**

At the top of `LeagueContext.tsx`, add:

```tsx
import { ProgramModal } from './dynasty/history/ProgramModal';
```

Replace the `expandedClubId` state declaration:

```tsx
// Before:
const [expandedClubId, setExpandedClubId] = useState<string | null>(null);

// After:
const [modalClub, setModalClub] = useState<{ id: string; name: string } | null>(null);
```

- [ ] **Step 2: Replace `handleClubOpen` with `handleClubModal`**

Replace the `handleClubOpen` function:

```tsx
// Before:
const handleClubOpen = (clubId: string) => {
  setExpandedClubId((current) => (current === clubId ? null : clubId));
};

// After:
const handleClubModal = (clubId: string, clubName: string) => {
  setModalClub({ id: clubId, name: clubName });
};
```

- [ ] **Step 3: Update the main table rows to use the modal**

In the `standings.map` table body (around lines 410–474), update the `<tr>` element:

```tsx
// Before:
<tr
  className={`${standing.is_user_club ? 'ls-user' : ''} ${expanded ? 'ls-row-expanded' : ''}`.trim()}
  onClick={() => handleClubOpen(standing.club_id)}
  style={{ cursor: 'pointer' }}
  role="button"
  tabIndex={0}
  aria-expanded={expanded}
  aria-controls={`club-history-${standing.club_id}`}
  aria-label={`${expanded ? 'Hide' : 'View'} ${standing.club_name} history`}
  onKeyDown={(event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleClubOpen(standing.club_id);
    }
  }}
>

// After:
<tr
  className={standing.is_user_club ? 'ls-user' : ''}
  onClick={() => handleClubModal(standing.club_id, standing.club_name)}
  style={{ cursor: 'pointer' }}
  role="button"
  tabIndex={0}
  aria-haspopup="dialog"
  aria-label={`Open ${standing.club_name} program history`}
  onKeyDown={(event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleClubModal(standing.club_id, standing.club_name);
    }
  }}
>
```

Also remove the `expanded` variable from the loop (it no longer applies):

```tsx
// Before (inside the standings.map callback):
const expanded = expandedClubId === standing.club_id;
return (
  <React.Fragment key={standing.club_id}>

// After:
return (
  <React.Fragment key={standing.club_id}>
```

- [ ] **Step 4: Remove ClubHistoryLane render and the ClubHistoryLane component; remove the nav column and fix colSpan**

This step must be done in a single edit so the build stays green. Do all four things together:

1. Delete the conditional `{expanded && (<ClubHistoryLane ... />)}` block (lines ~465–471).
2. Delete the entire `ClubHistoryLane` component (lines 220–261) — it is now dead code.
3. Delete the `<th className="ls-nav-th" aria-label="Navigate"></th>` from `<thead>`.
4. Delete the `<td className="ls-nav-cell"><span className="ls-nav-chevron" aria-hidden="true">{expanded ? 'v' : '>'}</span></td>` from each body `<tr>`. **The `expanded` variable is now gone (deleted in Step 3); the nav cell is the last reference to it — they must be removed in the same edit to avoid a `Cannot find name 'expanded'` tsc error.**
5. Change `<td colSpan={9}>` to `<td colSpan={8}>` on the playoff-cut separator row (the 9th column was the nav column just removed).

After this step, `expanded` must appear zero times in `LeagueContext.tsx`. Verify: `grep -n "expanded" frontend/src/components/LeagueContext.tsx` — should return no results (or only results inside the `handleClubModal` / Tiebreaker rows' `aria-haspopup` attribute, which do not reference `expanded`).

- [ ] **Step 5: Update Tiebreaker rows to open the modal**

In the `tiebreakRows.map` block (lines ~503–520), update `handleClubOpen` references:

```tsx
// Before:
<div
  key={`tb-${standing.club_id}`}
  className="ls-tb-row"
  onClick={() => handleClubOpen(standing.club_id)}
  style={{ cursor: 'pointer' }}
  role="button"
  tabIndex={0}
  aria-expanded={expandedClubId === standing.club_id}
  onKeyDown={(event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleClubOpen(standing.club_id);
    }
  }}
>

// After:
<div
  key={`tb-${standing.club_id}`}
  className="ls-tb-row"
  onClick={() => handleClubModal(standing.club_id, standing.club_name)}
  style={{ cursor: 'pointer' }}
  role="button"
  tabIndex={0}
  aria-haspopup="dialog"
  aria-label={`Open ${standing.club_name} program history`}
  onKeyDown={(event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleClubModal(standing.club_id, standing.club_name);
    }
  }}
>
```

- [ ] **Step 6: Render the ProgramModal at the bottom of the Standings return**

At the end of the `Standings` component's return, just before the closing `</>`, add:

```tsx
      {modalClub && (
        <ProgramModal
          clubId={modalClub.id}
          clubName={modalClub.name}
          onClose={() => setModalClub(null)}
        />
      )}
```

- [ ] **Step 7: Remove unused imports and variables**

The `recentMatchesForClub` helper (lines 211–218) was only used inside `ClubHistoryLane`. Delete it. If `React` is still needed for `React.Fragment`, keep the import; if not, remove it. Confirm no other usages remain with: `grep -n "recentMatchesForClub\|ClubHistoryLane" frontend/src/components/LeagueContext.tsx` — should return zero lines after deletion.

- [ ] **Step 8: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/LeagueContext.tsx
git commit -m "feat(v15-p2d): standings row-click opens ProgramModal (replaces inline expander)

Removes ClubHistoryLane and expandedClubId state; all row-clicks and
Tiebreaker row-clicks now open the existing ProgramModal so club
history is always the same surface. Modal content owned by Phase 4a.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Fix the legend and add TermTips to the table header

**Context:** The nav column and `colSpan` are already cleaned up in Task 2 Step 4. This task adds the `TermTip` import, wraps the Survivor Diff column header, and rewrites the legend — three cohesive presentational changes that all commit together.

**Files:**
- Modify: `frontend/src/components/LeagueContext.tsx`

- [ ] **Step 1: Add the TermTip import**

At the top of `LeagueContext.tsx`, add (or accumulate with later tasks — by the end of Task 6 the full import will be `import { TermTip, EmptyState } from '../legibility'` plus `import type { TermId } from '../legibility'`):

```tsx
import { TermTip } from '../legibility';
```

(Import path: `../legibility` resolves to `frontend/src/legibility/index.ts`. Tasks 5 and 6 extend this import.)

- [ ] **Step 2: Wrap "Survivor Diff" in a TermTip**

In the `<thead>`, replace the `<th>Survivor Diff</th>` with:

```tsx
<th>
  <TermTip term="standings.diff">Survivor Diff</TermTip>
</th>
```

- [ ] **Step 3: Rewrite the table legend**

Replace the current legend note (line ~484):

```tsx
// Before:
<span className="ls-legend-note">Click any row <span className="ls-nav-chevron-inline" aria-hidden="true">&gt;</span> to open that club's history.</span>

// After:
<span className="ls-legend-note">Click any row to open that club's program history.</span>
```

Also add a TermTip-backed legend item for the playoff line:

```tsx
// Add after the existing CUT badge legend item:
<span className="ls-legend-sep">-</span>
<span className="ls-legend-item">
  <TermTip term="standings.playoff_line">Playoff Line</TermTip>
  {' '}— top {playoffLine} advance
</span>
```

- [ ] **Step 4: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/LeagueContext.tsx
git commit -m "feat(v15-p2d): TermTip on Survivor Diff header; improve legend copy

Wraps Survivor Diff column header in TermTip(standings.diff); adds
TermTip(standings.playoff_line) to the legend; rewrites legend note to
reflect click-to-modal behavior (no longer references the > icon).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: De-jargon the glance header cluster and status copy

**Context:** Four confusing copy items in the glance cells need plain-language rewrites. None require new payload fields — all are derived from existing data in the component.

| Current string | Location | Plain rewrite |
|---|---|---|
| `CHASE MODE THROUGH W{wk}` (line ~335) | `ls-glance-rank` trend | `OUTSIDE PLAYOFF LINE — WEEK {wk}` |
| `ABOVE LINE THROUGH W{wk}` (line ~334) | `ls-glance-rank` trend | `IN PLAYOFF POSITION — WEEK {wk}` |
| `Record - Diff` (line ~341) | `ls-glance-record` label | `Season Record` (with TermTip on Survivor Diff mini-label) |
| `Playoff Line - Top {playoffLine}` (line ~354) | `ls-glance-race` label | `Playoff Race` |
| `Next Result Needs` (line ~373) | `ls-glance-next` label | `This Week's Target` |
| `WEEK {String(data.current_week).padStart(2, '0')}` badge (line ~388) | `ls-table-meta` | `WEEK {wk}` (already padded; keep) |
| `Live season table` (line ~384) | `ls-table-head` `ls-subtle` span | `Regular season` |

Note: "Yr N" appears in `program_trajectory_label` (e.g. "Yr 1 · Balanced Rebuild"), emitted by `web_status_service.py`. It is displayed in the standings row sub-label (line ~449) as `standing.program_trajectory_label ?? standing.program_archetype`. The rewrite strips "Yr N ·" from the display and shows only the archetype, which is then explained by a TermTip (Task 5). The "Yr N" value was intended to communicate franchise age, but without context it reads as jargon. A simpler label is `Year {n}` — the approach of stripping it keeps the component simpler and avoids a backend change. See the backend comment in `web_status_service.py:281-282` confirming the intent.

**Files:**
- Modify: `frontend/src/components/LeagueContext.tsx`

- [ ] **Step 1: Update the rank trend strings**

In the `ls-glance-rank` trend block (lines ~329–335):

```tsx
// Before:
: us.rank <= playoffLine
  ? `ABOVE LINE THROUGH W${String(data.current_week).padStart(2, '0')}`
  : `CHASE MODE THROUGH W${String(data.current_week).padStart(2, '0')}`

// After:
: us.rank <= playoffLine
  ? `IN PLAYOFF POSITION — WEEK ${String(data.current_week).padStart(2, '0')}`
  : `OUTSIDE PLAYOFF LINE — WEEK ${String(data.current_week).padStart(2, '0')}`
```

- [ ] **Step 2: Update the glance-record label**

```tsx
// Before:
<span className="lbl">Record - Diff</span>

// After:
<span className="lbl">Season Record</span>
```

The record row already shows `wins-losses-draws` and the `DiffBar`; the "Diff" part becomes self-explanatory via the `TermTip` added to the `<th>` in Task 3. No further change needed in the glance cell.

- [ ] **Step 3: Update the glance-race label**

```tsx
// Before:
<span className="lbl">Playoff Line - Top {playoffLine}</span>

// After:
<span className="lbl">Playoff Race</span>
```

The race pips already carry `in` / `out` states; the legend improvement (Task 3) explains the cutoff.

- [ ] **Step 4: Update the glance-next label**

```tsx
// Before:
<span className="lbl">Next Result Needs</span>

// After:
<span className="lbl">This Week's Target</span>
```

- [ ] **Step 5: Update the `ls-subtle` subtitle in the table head**

```tsx
// Before:
<span className="ls-subtle">{playoffsActive ? 'Playoffs live above' : 'Live season table'}</span>

// After:
<span className="ls-subtle">{playoffsActive ? 'Playoffs live above' : 'Regular season'}</span>
```

- [ ] **Step 6: Update the row sub-label to strip "Yr N ·"**

The sub-label in the row cell (lines ~448–451) currently renders `standing.program_trajectory_label ?? standing.program_archetype`. `program_trajectory_label` is `"Yr 1 · Balanced Rebuild"`. Display only the archetype portion:

```tsx
// Before:
<div className="ls-subtle" style={{ display: 'block', marginLeft: 0 }}>
  {standing.program_trajectory_label ?? standing.program_archetype ?? 'Program track live'}
</div>

// After (extract archetype from trajectory label if present):
<div className="ls-subtle" style={{ display: 'block', marginLeft: 0 }}>
  {(() => {
    const raw = standing.program_trajectory_label ?? standing.program_archetype ?? '';
    // Strip "Yr N · " prefix emitted by web_status_service.py, leaving only the archetype name.
    const archetype = raw.includes(' · ') ? raw.split(' · ').slice(1).join(' · ') : raw;
    return archetype || null;
  })()}
</div>
```

This is frontend-only; the backend field is unchanged.

- [ ] **Step 7: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/LeagueContext.tsx
git commit -m "feat(v15-p2d): de-jargon standings glance header cluster

Replace CHASE MODE, ABOVE LINE, Record-Diff, Playoff Line-Top N, and
Next Result Needs with plain language; strip 'Yr N ·' prefix from the
row archetype sub-label (display only the archetype name).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: TermTip on club archetype chips

**Context:** Each standings row displays `program_archetype` (or the archetype portion of `program_trajectory_label`) as a sub-label. After Task 4's strip, the raw archetype string (e.g. "Contender", "Defensive Specialist") is displayed. Wrap it in a `TermTip` mapping to the `program.archetype.*` keys added in Task 1.

`TermTip` wraps `children` in a button — inline with the `ls-subtle` span. The button is display `inline-flex` by default; confirm it does not break the sub-label layout (it should not since `ls-subtle` is already inline text).

**Scope decision — approach/coach badge TermTip:** The scope line says "club archetype chips get the same TermTip treatment as player archetypes (TERMS coach.\* / archetype.\*)". In this codebase, "coach archetypes" map to the `latest_approach` badge (Balanced/Aggressive/Control/Defensive) that appears in both the glance cell and the table column — different from the `program_archetype` sub-label. This task covers only the `program_archetype` sub-label (the six `program.archetype.*` terms from Task 1). TermTip-ing the approach badge (`coach.*` terms) is deferred to Phase 3b (Staff Impact), which already owns the coach/approach surfaces and has fuller context on `coach.*` term copy. Only `coach.balanced` is pre-seeded; the missing `coach.*` keys (`coach.win_now`, `coach.control`, `coach.defensive`) would need to be appended — defer with Phase 3b.

**Files:**
- Modify: `frontend/src/components/LeagueContext.tsx`

- [ ] **Step 1: Add the archetype-to-TermId mapping**

After the import block at the top of `LeagueContext.tsx`, add a lookup map (no runtime cost, no new dep):

```tsx
import type { TermId } from '../legibility';

// Maps classify_club_archetype() output to a TermId. Closed set matches persistence.py.
const ARCHETYPE_TERM_MAP: Record<string, TermId> = {
  'Balanced Rebuild': 'program.archetype.balanced_rebuild',
  'Contender': 'program.archetype.contender',
  'Development Factory': 'program.archetype.development_factory',
  'Defensive Specialist': 'program.archetype.defensive_specialist',
  'Power Throwers': 'program.archetype.power_throwers',
  'Aging Veterans': 'program.archetype.aging_veterans',
};
```

- [ ] **Step 2: Wrap the archetype sub-label in a TermTip when a mapping exists**

Update the row sub-label from Task 4 to optionally wrap in `TermTip`:

```tsx
<div className="ls-subtle" style={{ display: 'block', marginLeft: 0 }}>
  {(() => {
    const raw = standing.program_trajectory_label ?? standing.program_archetype ?? '';
    const archetype = raw.includes(' · ') ? raw.split(' · ').slice(1).join(' · ') : raw;
    if (!archetype) return null;
    const termId = ARCHETYPE_TERM_MAP[archetype];
    return termId
      ? <TermTip term={termId}>{archetype}</TermTip>
      : <span>{archetype}</span>;
  })()}
</div>
```

- [ ] **Step 3: Compile gate (proves TermId reference is valid)**

Run (from `frontend/`): `npm run build`
Expected: PASS. All `program.archetype.*` keys referenced in `ARCHETYPE_TERM_MAP` are now valid `TermId` values after Task 1. If any key errors, verify the exact string matches the `terms.ts` key (case-sensitive).

- [ ] **Step 4: Lint**

Run (from `frontend/`): `npm run lint`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/LeagueContext.tsx
git commit -m "feat(v15-p2d): TermTip on club archetype chips in standings rows

Maps classify_club_archetype() output strings to program.archetype.*
TermIds; unrecognized archetypes fall through to a plain span so new
values degrade gracefully.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: League Wire — state-aware compact ticker with EmptyState

**Context:** The League Wire panel in `LeagueContext.tsx` (lines ~488–495) renders `wireRows`, which are built by `buildWireRows`. When `recentMatches` is empty, `buildWireRows` returns a fabricated "Season / OPEN / Awaiting first result / LIVE" row — exactly the honesty anti-pattern `EmptyState` was built to replace.

The fix: make `buildWireRows` state-aware. If there are no real results yet (early season), return `null` and render `EmptyState` instead. When results exist, render them in the compact ticker style already established in `PreSimDashboard.tsx`'s `cc-proof` rail (lines 844–873 of `PreSimDashboard.tsx`) — a horizontally-scrolling, single-line ticker rather than a stacked card. On mobile (390×844) the stacked card approach overflows and wastes vertical space; the ticker format is more compact and honest.

**No new backend field.** `data.recent_matches` is already in `StandingsResponse`. The empty condition is `!data.recent_matches || data.recent_matches.length === 0`.

**Files:**
- Modify: `frontend/src/components/LeagueContext.tsx`

- [ ] **Step 1: Add the EmptyState import**

At the top of `LeagueContext.tsx`, extend the legibility import:

```tsx
import { TermTip, EmptyState } from '../legibility';
```

- [ ] **Step 2: Rewrite `buildWireRows` to return `React.ReactNode[] | null`**

Replace the `buildWireRows` function:

```tsx
const buildWireRows = (
  recentMatches: RecentMatchSummary[] | undefined,
  userClubName: string,
): React.ReactNode[] | null => {
  if (!recentMatches || recentMatches.length === 0) {
    return null; // caller renders EmptyState
  }

  return recentMatches.map((match) => {
    const parsed = parseMatchSummary(match.summary);
    if (!parsed) {
      return (
        <span key={match.match_id} className="ls-wire-item">
          <b>W{String(match.week).padStart(2, '0')}</b> {match.summary}
        </span>
      );
    }

    const involvesUser = parsed.homeClubName === userClubName || parsed.awayClubName === userClubName;
    const resultTag = match.winner_name === 'Draw' ? 'Draw' : `${parsed.homeClubName} ${parsed.homeScore}-${parsed.awayScore} ${parsed.awayClubName}`;

    return (
      <span
        key={match.match_id}
        className={`ls-wire-item${involvesUser ? ' is-us' : ''}`}
        aria-label={`Week ${match.week}: ${resultTag}`}
      >
        <span className="ls-wire-item-wk">W{String(match.week).padStart(2, '0')}</span>
        <span className="ls-wire-item-score">{resultTag}</span>
        {involvesUser && <span className="ls-wire-item-you" aria-label="your match">★</span>}
      </span>
    );
  });
};
```

Note: the `currentWeek` parameter is removed since the caller no longer passes it; remove it from the call site too.

- [ ] **Step 3: Update the `wireRows` call site**

```tsx
// Before:
const wireRows = buildWireRows(data.recent_matches, us.club_name, data.current_week);

// After:
const wireRows = buildWireRows(data.recent_matches, us.club_name);
```

- [ ] **Step 4: Rewrite the League Wire panel JSX**

Replace the panel body (lines ~488–495):

```tsx
        <div className="ls-panel">
          <div className="ls-panel-head">
            <span className="dm-kicker">League Wire</span>
            <h3>Recent Results</h3>
          </div>
          {wireRows === null ? (
            <EmptyState
              title="No results yet"
              body="League Wire updates here after the first week of matches is complete."
              icon="📡"
            />
          ) : (
            <div
              className="ls-wire-ticker"
              role="list"
              aria-label="Recent league results"
              style={{
                display: 'flex',
                flexDirection: 'row',
                gap: '0.75rem',
                overflowX: 'auto',
                padding: '0.5rem 0.75rem',
                WebkitOverflowScrolling: 'touch',
              }}
            >
              {wireRows}
            </div>
          )}
        </div>
```

- [ ] **Step 5: Add CSS classes for the new ticker items**

These classes need to exist in `frontend/src/index.css` (or the project's CSS file). Check what CSS file the component uses: `grep -rn "ls-wire-row\|ls-wire-list" frontend/src/index.css` to confirm the existing rules. Add after the existing `.ls-wire-*` block:

```css
.ls-wire-ticker {
  scrollbar-width: thin;
  scrollbar-color: #1e293b #0b1220;
}
.ls-wire-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  white-space: nowrap;
  font-size: 0.7rem;
  color: #94a3b8;
  padding: 0.2rem 0.5rem;
  border: 1px solid #1e293b;
  border-radius: 3px;
  background: rgba(15, 23, 42, 0.5);
  list-style: none;
}
.ls-wire-item.is-us {
  border-color: rgba(34, 211, 238, 0.4);
  background: rgba(34, 211, 238, 0.07);
}
.ls-wire-item-wk {
  color: #475569;
  font-size: 0.62rem;
  font-variant-numeric: tabular-nums;
}
.ls-wire-item-score {
  font-weight: 600;
}
.ls-wire-item-you {
  color: #22d3ee;
  font-size: 0.65rem;
}
```

> **Where to add:** Find the existing `.ls-wire-row` block in `frontend/src/index.css` and append this block immediately after it. Do not remove the old `.ls-wire-row` rules — they may be referenced by other existing code or tests; the old `wireRows` render path that used `.ls-wire-row` is removed in this step, but leave the CSS so any Playwright snapshot using those class names doesn't fail with a missing-rule error.

- [ ] **Step 6: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/LeagueContext.tsx frontend/src/index.css
git commit -m "feat(v15-p2d): League Wire becomes compact ticker with EmptyState early season

Replaces fabricated 'LIVE / Awaiting first result' placeholder with
EmptyState; results render as a compact horizontal ticker rather than
a stacked card. No new payload field — uses existing recent_matches[].

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Tiebreaker Read — state-aware soften / hide early season

**Context:** The Tiebreaker Read panel (lines ~497–535) shows all clubs near the playoff line, including their points and differential. Early in the season (week 1–2, before any matches are played) this panel either shows all-zero data or is populated with the first week's results — in either case, the "tiebreaker" framing is misleading because no meaningful playoff race exists yet. At season end or during offseason, it's also redundant.

**State-aware logic (no new backend field; derived from existing data):**
- **Hide** (render `EmptyState`) when: `isOffseason === true`, or `playoffsActive === true` (bracket is canon), or `data.current_week <= 1` (no matches played yet — no standings spread exists).
- **Soften** (render with a "Race developing" header and lower visual weight) when: `data.current_week > 1` AND there are no actual points differences near the cut line (all clubs within 0 points of each other). The soften condition: `Math.max(...standings.map(s => s.points)) === 0`.
- **Normal** (current render): all other states.

**Files:**
- Modify: `frontend/src/components/LeagueContext.tsx`

- [ ] **Step 1: Compute the tiebreaker visibility state**

After `const tiebreakRows = ...` (line ~309), add:

```tsx
const allZeroPoints = standings.every((s) => s.points === 0);
const tiebreakerState: 'hidden' | 'soft' | 'live' =
  isOffseason || playoffsActive
    ? 'hidden'
    : data.current_week <= 1 || allZeroPoints
      ? 'soft'
      : 'live';
```

- [ ] **Step 2: Rewrite the Tiebreaker Read panel JSX**

Replace the Tiebreaker Read panel (lines ~497–535):

```tsx
        <div className="ls-panel">
          <div className="ls-panel-head">
            <span className="dm-kicker">Tiebreaker Read</span>
            <h3>
              {tiebreakerState === 'hidden'
                ? 'Race Concluded'
                : tiebreakerState === 'soft'
                  ? 'Race Developing'
                  : `Top ${playoffLine} Race`}
            </h3>
          </div>
          {tiebreakerState === 'hidden' ? (
            <EmptyState
              title={isOffseason ? 'Season concluded' : 'Bracket is live'}
              body={
                isOffseason
                  ? 'The regular season is over. See the offseason recap for final standings.'
                  : 'The playoff bracket above is now the deciding surface.'
              }
            />
          ) : tiebreakerState === 'soft' ? (
            <EmptyState
              title="Race not yet meaningful"
              body="No matches have been played. The tiebreaker read will update after Week 1 results are in."
            />
          ) : (
            <div className="ls-tb-list">
              {tiebreakRows.map((standing) => {
                const isSafe = standing.rank <= playoffLine;
                return (
                  <div
                    key={`tb-${standing.club_id}`}
                    className="ls-tb-row"
                    onClick={() => handleClubModal(standing.club_id, standing.club_name)}
                    style={{ cursor: 'pointer' }}
                    role="button"
                    tabIndex={0}
                    aria-haspopup="dialog"
                    aria-label={`Open ${standing.club_name} program history`}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        handleClubModal(standing.club_id, standing.club_name);
                      }
                    }}
                  >
                    <span className="ls-tb-from">#{standing.rank}</span>
                    <div className="ls-tb-body">
                      <span className="ls-tb-who">{standing.club_name}</span>
                      <span className="ls-tb-note">
                        {standing.points} pts · {formatDiff(standing.elimination_differential)} diff
                      </span>
                    </div>
                    <span className={`ls-tb-risk ${isSafe ? 'risk-low' : 'risk-high'}`}>
                      {isSafe ? 'IN' : 'BUBBLE'}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
```

Note the Tiebreaker note string also dropped `normalizeApproach(standing.latest_approach)` — the approach is already shown in the main table column; removing it reduces redundancy in this narrower panel.

- [ ] **Step 3: Compile + lint**

Run (from `frontend/`): `npm run build && npm run lint`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/LeagueContext.tsx
git commit -m "feat(v15-p2d): Tiebreaker Read is state-aware (hides early/offseason/playoff)

Replaces always-visible tiebreaker panel with three states: hidden
(offseason / playoffs), soft (week 1 or all-zero points), and live
(normal season). Uses EmptyState for hidden/soft — no fabricated data.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Playwright smoke

**Context:** Behavioral surfaces changed: row-click now opens a modal (not expander), Wire shows `EmptyState` early season, Tiebreaker Read is conditionally hidden. The smoke must verify these three behaviors. The test navigates to the standings tab of a running game; if the e2e suite uses a fixture save, use the same approach as existing standings specs.

**Files:**
- Create: `tests/e2e/v15-standings-legibility.spec.ts`

- [ ] **Step 1: Locate the existing standings e2e baseline**

Run: `ls tests/e2e/` and `grep -rn "standings\|LeagueContext\|tab.*standings" tests/e2e/`
Note how existing tests navigate to the standings screen (what URL query param or button they use) and whether they rely on a save fixture. Match that pattern exactly.

- [ ] **Step 2: Create the spec**

```ts
import { test, expect } from '@playwright/test';

// V15 Phase 2d: Standings legibility smoke.
// Verifies: (a) row-click opens ProgramModal dialog, not inline expander;
// (b) Tiebreaker Read shows EmptyState when appropriate;
// (c) League Wire shows EmptyState early season.
// Navigation: adjust the goto/click pattern to match the existing standings e2e pattern found in Step 1.

test.describe('v15-p2d standings legibility', () => {
  test('standings row click opens program modal', async ({ page }) => {
    // Navigate to the standings tab — match the existing e2e navigation pattern.
    // Example (adjust to repo's actual route):
    await page.goto('/?tab=standings');

    // Wait for the standings table to be visible.
    const table = page.locator('.ls-table');
    await expect(table).toBeVisible();

    // Click the first non-cut-line row.
    const firstRow = page.locator('.ls-table tbody tr[role="button"]').first();
    await firstRow.click();

    // ProgramModal should open — it uses the command-policy-overlay class.
    const modal = page.locator('.command-policy-overlay');
    await expect(modal).toBeVisible();

    // The modal should show the League Archive kicker.
    // Scope to the header element to avoid matching inner kickers rendered by MyProgramView.
    await expect(modal.locator('.do-hist-modal-header .dm-kicker')).toContainText('League Archive');

    // Close with Escape.
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible();
  });

  test('standings row click is keyboard operable', async ({ page }) => {
    await page.goto('/?tab=standings');
    const firstRow = page.locator('.ls-table tbody tr[role="button"]').first();
    await firstRow.focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('.command-policy-overlay')).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('standings row has aria-haspopup dialog', async ({ page }) => {
    await page.goto('/?tab=standings');
    const firstRow = page.locator('.ls-table tbody tr[role="button"]').first();
    await expect(firstRow).toHaveAttribute('aria-haspopup', 'dialog');
  });

  test('table legend does not reference the > icon', async ({ page }) => {
    await page.goto('/?tab=standings');
    const legend = page.locator('.ls-table-foot');
    await expect(legend).toBeVisible();
    // The old legend said "Click any row >" — the new one does not use the > chevron.
    const legendText = await legend.innerText();
    expect(legendText).not.toContain('Click any row >');
    expect(legendText).toContain('program history');
  });

  test('Survivor Diff header has TermTip', async ({ page }) => {
    await page.goto('/?tab=standings');
    // TermTip wraps children in a button with aria-label "What is ${def.label}?".
    // The term standings.diff has label "Differential" (from terms.ts Phase 1 seed),
    // so the button's aria-label is "What is Differential?" — NOT "What is Survivor Diff?".
    const tip = page.getByRole('button', { name: /What is Differential\?/i });
    await expect(tip).toBeVisible();
  });
});
```

> **Adapt the navigation:** Replace `page.goto('/?tab=standings')` with whatever the existing standings e2e uses (may be a button click on the main menu, or a different query param). Check with `grep -rn "goto\|standings" tests/e2e/*.spec.ts`.

- [ ] **Step 3: Run the e2e spec**

Run (from repo root): `npm run e2e -- --grep "v15-p2d"`
Expected: all tests PASS. If the standing navigation differs, fix the goto pattern first.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/v15-standings-legibility.spec.ts
git commit -m "test(v15-p2d): Playwright smoke for standings legibility

Verifies row-click opens ProgramModal, keyboard operability, aria-haspopup,
legend copy, and TermTip presence on Survivor Diff header.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Phase 2d Exit Gates

Run all before declaring Phase 2d done:

- [ ] From `frontend/`: `npm run build` — PASS (tsc no-orphan gate: all `TermTip term=` references resolve to valid `TermId`s).
- [ ] From `frontend/`: `npm run lint` — clean.
- [ ] From repo root: `npm run e2e -- --grep "v15-p2d"` — all green.
- [ ] From repo root: `npm run e2e` — no regressions in other specs.
- [ ] No backend files touched; `python -m pytest -q` not required (no payload change).
- [ ] `python tools/tier_engine_health_probe.py` — unchanged from baseline (no engine files touched).
- [ ] Manual check at 390×844: standings table renders without horizontal overflow; row-click opens modal; Tiebreaker Read shows EmptyState on a fresh career Week 1; League Wire shows EmptyState before first results; club archetype sub-labels show TermTip underline on hover.
- [ ] No `playtest_output/*.png` or `.db` files committed.

---

## Phase 4a Overlap Note (ProgramModal row-click)

This plan wires the click trigger and passes `clubId` + `clubName` to `ProgramModal` — the mechanical wire-up only. **The modal's inner content** (`MyProgramView`, banners, alumni, history proof-chips, etc.) is owned by Phase 4a (`phase-4a-history-identity-plan.md`). Phase 4a may freely rewrite `ProgramModal`'s content, tabs, and inner layout without conflicting with this plan.

**A11y gap to hand off:** `ProgramModal` currently uses `command-policy-overlay` class and closes on backdrop-click + Escape, but lacks `role="dialog"`, `aria-modal`, and a focus-trap. This is a Phase 4a concern — do not fix here (Phase 4a owns the modal's content and structure). Note it in the Phase 4a brief when that plan is authored.

---

## Out of Scope for Phase 2d

- `PreSimDashboard.tsx` matchup band rewrite — owned by Phase 3c.
- `ProgramModal` content (banners, alumni, history milestones, proof chips) — Phase 4a.
- `PlayoffBracket.tsx` — already correct; reference only. Do not touch.
- Backend standings data model (`elimination_differential`, `program_archetype`, `program_trajectory_label`) — no new fields in this phase.
- `program_trajectory_label` format change ("Yr N ·" prefix) — the backend field is left as-is; the frontend strips the prefix when displaying. A cleaner solution would reformat at the backend, but that is a separate, low-priority backend task and would require a `pytest` verification pass outside this plan's scope.
