# Audit Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all frontend-only product coherence fixes identified in `docs/product-coherence-audit.md` — label corrections, UX clarity improvements, and information hierarchy fixes.

**Architecture:** All changes are frontend-only (`frontend/src/`). No backend changes. No new files created — all edits to existing components. Eight files total across five groups.

**Tech Stack:** React 18, TypeScript, Vite. Run `npm run build` and `npm run lint` from `frontend/` to verify.

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/components/Roster.tsx` | Rename "Status" → "Role"; remove hardcoded Trend chip; add starters count |
| `frontend/src/components/match-week/aftermath/FalloutGrid.tsx` | Rename section heading and all three card titles |
| `frontend/src/components/MatchWeek.tsx` | Update post-sim PageHeader description; pass `playerClubId` to `KeyPlayersPanel` |
| `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx` | Accept `playerClubId` prop; add "Your Club" badge on matching performers |
| `frontend/src/components/MatchReplay.tsx` | Rename CONTINUE button, REPORT tab, TICK label |
| `frontend/src/components/LeagueContext.tsx` | Add tooltip to Elimination Differential column headers |
| `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` | Remove duplicate lock button; add Last Match strip; add season record to subtitle |
| `frontend/src/components/dynasty/ProspectCard.tsx` | Add action description tooltips for Scout/Contact/Visit |

---

## Task 1: Roster — rename Status column and fix Trend chip

**Files:**
- Modify: `frontend/src/components/Roster.tsx:110` (Trend chip)
- Modify: `frontend/src/components/Roster.tsx:136` (theater Status header)
- Modify: `frontend/src/components/Roster.tsx:149` (compact Status header)

- [ ] **Step 1: Rename theater-view Status header to Role**

In `Roster.tsx` line 136, change:
```tsx
<th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Status</th>
```
to:
```tsx
<th style={{ padding: '1rem', color: '#64748b', fontSize: '0.75rem', textTransform: 'uppercase' }}>Role</th>
```

- [ ] **Step 2: Rename compact-view Status header to Role**

In `Roster.tsx` line 149, change:
```tsx
<th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Status</th>
```
to:
```tsx
<th style={{ padding: '0.5rem', color: '#64748b', fontSize: '0.75rem' }}>Role</th>
```

- [ ] **Step 3: Replace hardcoded Trend chip with real starters count**

In `Roster.tsx` lines 110, replace:
```tsx
<StatChip label="Trend" value="UP" tone="success" />
```
with:
```tsx
<StatChip label="Starters" value={roster.filter(r => r.starter).length} />
```

Note: `roster` is already computed above this render block as a memoized array of `{ player, starter }` objects. This reference is valid.

- [ ] **Step 4: Verify build**

From `frontend/`:
```
npm run build
```
Expected: exits 0, no TypeScript errors.

- [ ] **Step 5: Commit**

```
git add frontend/src/components/Roster.tsx
git commit -m "fix: rename Status column to Role, replace hardcoded Trend chip with starters count"
```

---

## Task 2: FalloutGrid — rename section and card titles

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/FalloutGrid.tsx:32-33` (section heading)
- Modify: `frontend/src/components/match-week/aftermath/FalloutGrid.tsx:36,49,62` (card titles)

- [ ] **Step 1: Rename section heading**

In `FalloutGrid.tsx` lines 31–33, change:
```tsx
<div className="command-section-heading">
  <p className="dm-kicker">Fallout</p>
  <h3>Front office report</h3>
</div>
```
to:
```tsx
<div className="command-section-heading">
  <p className="dm-kicker">Match Fallout</p>
  <h3>What your week caused</h3>
</div>
```

- [ ] **Step 2: Rename the three card titles**

Change `<FalloutCard title="Player Development">` → `<FalloutCard title="Who Grew">`

Change `<FalloutCard title="League Table">` → `<FalloutCard title="Standings Shift">`

Change `<FalloutCard title="Recruit Reactions">` → `<FalloutCard title="Prospect Pulse">`

- [ ] **Step 3: Commit**

```
git add frontend/src/components/match-week/aftermath/FalloutGrid.tsx
git commit -m "fix: rename fallout section and card titles to active sports language"
```

---

## Task 3: MatchWeek — update PageHeader description

**Files:**
- Modify: `frontend/src/components/MatchWeek.tsx:202`

- [ ] **Step 1: Update the post-sim PageHeader description**

In `MatchWeek.tsx` line 202, change:
```tsx
<PageHeader eyebrow="WAR ROOM" title="Command Center" description="Review the match result, replay identity, and weekly fallout." />
```
to:
```tsx
<PageHeader eyebrow="WAR ROOM" title="Command Center" description="Review the result, who performed, and what your week caused." />
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/MatchWeek.tsx
git commit -m "fix: update post-sim PageHeader description"
```

---

## Task 4: KeyPlayersPanel — distinguish player's club performers

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`
- Modify: `frontend/src/components/MatchWeek.tsx` (pass playerClubId)

- [ ] **Step 1: Add playerClubId prop to KeyPlayersPanel**

In `KeyPlayersPanel.tsx`, update the component signature and rendering:

```tsx
export function KeyPlayersPanel({
  performers,
  playerClubId,
}: {
  performers: TopPerformer[];
  playerClubId?: string;
}) {
  return (
    <section className="dm-panel command-key-players" data-testid="key-players-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">Key Performers</p>
      </div>
      <div className="command-key-player-list">
        {performers.length === 0 ? (
          <p className="command-empty-copy">Replay stats are loading.</p>
        ) : (
          performers.slice(0, 3).map((player, index) => {
            const isYours = playerClubId
              ? player.club_id === playerClubId
              : false;
            return (
              <article
                key={player.player_id}
                className="command-key-player"
                style={isYours ? { borderLeft: '2px solid #22d3ee' } : undefined}
              >
                <span>{index + 1}</span>
                <div>
                  <strong>{player.player_name}</strong>
                  {isYours && (
                    <span className="dm-badge dm-badge-cyan" style={{ marginLeft: '0.4rem', fontSize: '0.6rem' }}>
                      Your Club
                    </span>
                  )}
                  {!isYours && player.club_name && (
                    <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: '0.35rem' }}>
                      {player.club_name}
                    </span>
                  )}
                  <p>{statLine(player)}</p>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
```

Note: `TopPerformer` must have a `club_id` field. Check `frontend/src/types.ts` — if `club_id` is absent on `TopPerformer`, fall back to matching on `club_name` against `currentData?.player_club_name`. Use whichever is available.

- [ ] **Step 2: Check TopPerformer type for club_id**

```
grep -n "TopPerformer" frontend/src/types.ts
```

If `club_id` is not present, use `club_name` matching. Replace `player.club_id === playerClubId` with `player.club_name === playerClubName` and update the prop to accept `playerClubName?: string` instead.

- [ ] **Step 3: Pass playerClubId from MatchWeek.tsx to KeyPlayersPanel**

In `MatchWeek.tsx`, the `renderPostSimMode()` function already computes:
```tsx
const playerClubId = currentData?.player_club_id ?? activeResult.plan.player_club_id;
```
via `resolveMatchCardNames`. Extract it and pass it:

Find line 227:
```tsx
<KeyPlayersPanel performers={replayForMatch?.report.top_performers ?? []} />
```

Change to:
```tsx
<KeyPlayersPanel
  performers={replayForMatch?.report.top_performers ?? []}
  playerClubId={currentData?.player_club_id ?? activeResult.plan.player_club_id}
/>
```

- [ ] **Step 4: Build and check**

```
npm run build
```
Expected: exits 0.

- [ ] **Step 5: Commit**

```
git add frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx frontend/src/components/MatchWeek.tsx
git commit -m "feat: distinguish player's club performers in Key Players panel"
```

---

## Task 5: MatchReplay — rename CONTINUE button, REPORT tab, TICK label

**Files:**
- Modify: `frontend/src/components/MatchReplay.tsx:818` (CONTINUE button)
- Modify: `frontend/src/components/MatchReplay.tsx:828` (labels object)
- Modify: `frontend/src/components/MatchReplay.tsx:500` (TICK label in play-by-play)

- [ ] **Step 1: Rename CONTINUE button to BACK TO RESULTS**

In `MatchReplay.tsx` line 818, change:
```tsx
{'CONTINUE ->'}
```
to:
```tsx
{'BACK TO RESULTS'}
```

- [ ] **Step 2: Rename REPORT tab to BOX SCORE**

In `MatchReplay.tsx` line 828, change:
```tsx
const labels = { pbp: 'PLAY-BY-PLAY', keyplays: 'KEY PLAYS', stats: 'REPORT' };
```
to:
```tsx
const labels = { pbp: 'PLAY-BY-PLAY', keyplays: 'KEY PLAYS', stats: 'BOX SCORE' };
```

- [ ] **Step 3: Rename TICK N to PLAY N in play-by-play**

In `MatchReplay.tsx` line 500, the `PlayByPlayPanel` maps with `(ev, i)`. Change:
```tsx
<span className="dm-time" style={{ color: '#64748b', fontFamily: 'var(--font-mono-data)', marginRight: '0.5rem', fontSize: '0.75rem' }}>TICK {ev.tick}</span>
```
to:
```tsx
<span className="dm-time" style={{ color: '#64748b', fontFamily: 'var(--font-mono-data)', marginRight: '0.5rem', fontSize: '0.75rem' }}>PLAY {i + 1}</span>
```

- [ ] **Step 4: Commit**

```
git add frontend/src/components/MatchReplay.tsx
git commit -m "fix: rename CONTINUE button, REPORT tab to BOX SCORE, TICK to PLAY in replay"
```

---

## Task 6: Standings — add Elimination Differential tooltip

**Files:**
- Modify: `frontend/src/components/LeagueContext.tsx:69-73` (desktop header)
- Modify: `frontend/src/components/LeagueContext.tsx` (mobile header)

- [ ] **Step 1: Add title tooltip to desktop Elim Differential header**

In `LeagueContext.tsx`, the desktop thead has:
```tsx
<th style={{ textAlign: 'right' }}>
  <span className="dm-desktop-only">Elim Differential</span>
  <span className="dm-mobile-only">Diff</span>
</th>
```

Change to:
```tsx
<th
  style={{ textAlign: 'right' }}
  title="Total opponents eliminated minus times your players were eliminated across all matches. Used as a tiebreaker."
>
  <span className="dm-desktop-only">Elim Differential</span>
  <span className="dm-mobile-only">Diff</span>
</th>
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/LeagueContext.tsx
git commit -m "fix: add tooltip to Elimination Differential column header"
```

---

## Task 7: PreSimDashboard — remove duplicate lock button

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx:208-233`

The `command-next-action` section currently renders action buttons that duplicate the Control Tower buttons. Replace that button block with read-only status text.

- [ ] **Step 1: Remove duplicate buttons from command-next-action**

Find the `command-next-action-buttons` div (lines 208–233):
```tsx
<div className="command-next-action-buttons">
  {!planConfirmed ? (
    <button
      type="button"
      data-testid="lock-weekly-plan-top"
      aria-label="Confirm Plan"
      onClick={() => {
        if (isReadyToLock) onSavePlan(selectedIntent, true);
      }}
      disabled={!isReadyToLock}
      className="command-primary-button"
    >
      {isReadyToLock ? 'Confirm Plan' : 'Review Checklist'}
    </button>
  ) : (
    <>
      <button type="button" data-testid="simulate-command-week-top" onClick={simulate} className="command-primary-button is-live">
        Simulate Match
      </button>
      <button type="button" onClick={() => onSavePlan(selectedIntent, false)} className="command-secondary-button" style={{ marginTop: 0 }}>
        Unlock Plan
      </button>
    </>
  )}
</div>
```

Replace with:
```tsx
<div className="command-next-action-status">
  <p style={{ margin: 0, fontSize: '0.8rem', color: planConfirmed ? '#10b981' : '#94a3b8', fontFamily: 'var(--font-body)' }}>
    {planConfirmed
      ? 'Plan locked. Simulate the match using the button below.'
      : isReadyToLock
      ? 'The board is ready. Lock the plan to unlock simulation.'
      : `Complete the readiness checklist below, then lock the plan to run the match.`}
  </p>
</div>
```

- [ ] **Step 2: Build and verify no TypeScript errors**

```
npm run build
```
Expected: exits 0.

- [ ] **Step 3: Commit**

```
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "fix: remove duplicate lock button from Next Action panel, replace with read-only status"
```

---

## Task 8: PreSimDashboard — add Last Match context strip

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

Insert a "Last Match" strip between `command-alert-strip` and `command-dashboard-main`. The data is in `data.history`.

- [ ] **Step 1: Add last match variables**

After the existing computed variables (around line 151, after `hasPlanConflict`), add:

```tsx
const lastRecord = data.history.length > 0 ? data.history[data.history.length - 1] : null;
const lastMatchResult = lastRecord?.dashboard?.result ?? null;
const lastMatchIntent = lastRecord?.plan?.intent ?? null;
const lastMatchOpponent = lastRecord?.dashboard?.opponent_name ?? null;
const showLastMatch = !planConfirmed && lastRecord !== null && data.week > 1;
```

- [ ] **Step 2: Insert the strip into the JSX**

Find where `command-dashboard-main` opens (after the `command-alert-strip` block, around line 235). Insert before `<div className="command-dashboard-main">`:

```tsx
{showLastMatch && lastMatchResult && (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.6rem 1rem',
    background: '#0a1628',
    borderBottom: '1px solid #1e293b',
    fontSize: '0.75rem',
    fontFamily: 'var(--font-display)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    color: '#64748b',
  }}>
    <span>Last Match</span>
    <span style={{ color: lastMatchResult === 'Win' ? '#10b981' : lastMatchResult === 'Loss' ? '#f43f5e' : '#94a3b8', fontWeight: 700 }}>
      {lastMatchResult}
    </span>
    {lastMatchOpponent && <span>vs {lastMatchOpponent}</span>}
    {lastMatchIntent && <span>({humanize(lastMatchIntent)} plan)</span>}
  </div>
)}
```

- [ ] **Step 3: Build and verify**

```
npm run build
```
Expected: exits 0.

- [ ] **Step 4: Commit**

```
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "feat: add Last Match context strip to Command Center pre-sim"
```

---

## Task 9: PreSimDashboard — add season record to subtitle

**Files:**
- Modify: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx:164`

`recentRecord` is already computed on line 90 as e.g. `"3-2"`. Update the subtitle to include it.

- [ ] **Step 1: Update the subtitle**

Find line 164:
```tsx
<div className="command-dashboard-subtitle">Week {data.week} vs {plan.opponent.name}</div>
```

Change to:
```tsx
<div className="command-dashboard-subtitle">Week {data.week} · {recentRecord} · vs {plan.opponent.name}</div>
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/match-week/command-center/PreSimDashboard.tsx
git commit -m "feat: add season record to Command Center subtitle"
```

---

## Task 10: ProspectCard — add action description tooltips

**Files:**
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx:85-87`

Each of the three action buttons gets a descriptive `title` tooltip explaining what the action does.

- [ ] **Step 1: Expand the ActionButton titles**

In `ProspectCard.tsx`, find the three ActionButton renders (lines 85–87):

```tsx
<ActionButton title={canScout ? 'Spend one Scout slot' : 'No Scout slots remain this week'} disabled={loading || !canScout} onClick={() => doAction('scout')}>Scout</ActionButton>
<ActionButton title={canContact ? 'Spend one Contact slot' : 'No Contact slots remain this week'} disabled={loading || !canContact} onClick={() => doAction('contact')}>Contact</ActionButton>
<ActionButton title={canVisit ? 'Spend one Visit slot' : 'No Visit slots remain this week'} disabled={loading || !canVisit} onClick={() => doAction('visit')}>Visit</ActionButton>
```

Change to:
```tsx
<ActionButton
  title={canScout ? 'Scout: Reveals hidden rating data and narrows the OVR band for this prospect.' : 'No Scout slots remain this week'}
  disabled={loading || !canScout}
  onClick={() => doAction('scout')}
>Scout</ActionButton>
<ActionButton
  title={canContact ? 'Contact: Reaches out directly to build interest. Increases their engagement with your program.' : 'No Contact slots remain this week'}
  disabled={loading || !canContact}
  onClick={() => doAction('contact')}
>Contact</ActionButton>
<ActionButton
  title={canVisit ? 'Visit: Invites the prospect to your facility. Strongest commitment signal — use it on top targets.' : 'No Visit slots remain this week'}
  disabled={loading || !canVisit}
  onClick={() => doAction('visit')}
>Visit</ActionButton>
```

- [ ] **Step 2: Commit**

```
git add frontend/src/components/dynasty/ProspectCard.tsx
git commit -m "fix: add descriptive tooltips to Scout/Contact/Visit actions on prospect cards"
```

---

## Task 11: Final build and lint check

- [ ] **Step 1: Full lint**

From `frontend/`:
```
npm run lint
```
Fix any reported issues.

- [ ] **Step 2: Full build**

```
npm run build
```
Expected: exits 0 with no errors or warnings.

- [ ] **Step 3: Commit any lint fixes**

```
git add -A
git commit -m "fix: lint cleanup after audit fixes"
```

---

## Self-Review

**Spec coverage:**
- ✅ Group 1 label fixes: Tasks 1, 2, 5, 6 cover all 7 items
- ✅ Group 2 Key Players: Task 4
- ✅ Group 3 duplicate button: Task 7
- ✅ Group 4 last match context: Task 8
- ✅ Group 5 season record: Task 9
- ✅ ProspectCard action explanations: Task 10
- ⏭️ Fix 1 (plan verdict) — excluded, needs backend `verdict` field
- ⏭️ Fix 2 (department orders move) — medium complexity, separate pass
- ⏭️ Fix 6 (playoff standings context) — needs backend changes
- ⏭️ Offseason recruitment choice — significant UI rebuild, separate pass

**Placeholder scan:** None found — all steps contain actual code.

**Type consistency:** `playerClubId` threaded consistently from `MatchWeek.tsx` → `KeyPlayersPanel`. Task 4 includes a check against `types.ts` to verify `club_id` exists on `TopPerformer` before committing to that field.
