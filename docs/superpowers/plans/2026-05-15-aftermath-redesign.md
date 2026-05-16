# Aftermath Screen Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the post-match aftermath screen so Match Flow is a full-width hero, Tactical Read and Key Performers are real analysis cards, Week Fallout collapses when empty, and the page title and result messaging are no longer redundant.

**Architecture:** Seven components are touched in a fixed order — CSS first (so components can reference class names immediately), then leaf components (Headline, TacticalSummaryCard, ReplayTimeline, KeyPlayersPanel, FalloutGrid, AftermathActionBar), then the orchestrating parent (MatchWeek) that re-wires the layout. No new files. No backend changes. All data is already available in `activeResult.dashboard.lanes`, `replayForMatch.report`, and `aftermath`.

**Tech Stack:** React 18, TypeScript, plain CSS (index.css), Vite. No test runner is set up for the frontend; each task is verified with `npm run build` from `frontend/` (TypeScript compile + bundle).

---

## Reference: Key Types

```ts
// types.ts — referenced throughout, do not change
interface CommandDashboardLane { title: string; summary: string; items: string[]; }
interface TopPerformer {
  player_id: string; player_name: string; club_name?: string;
  score: number; eliminations_by_throw: number; catches_made: number; dodges_successful: number;
}
interface Aftermath {
  headline: string;
  match_card: { home_club_id: string; away_club_id: string; winner_club_id: string | null;
                home_survivors: number; away_survivors: number; } | null;
  player_growth_deltas: Array<{ player_id: string; player_name: string; attribute: string; delta: number }>;
  standings_shift: Array<{ club_id: string; club_name: string; old_rank: number; new_rank: number }>;
  recruit_reactions: Array<{ prospect_id: string; prospect_name: string; interest_delta: string; evidence: string }>;
}
```

---

## Task 1: CSS — New Layout Classes

**Files:**
- Modify: `frontend/src/index.css`

Find the `.command-story-grid` block (currently around line 1819) and replace the story-grid section. Also update `.command-tactical-card`, `.command-key-player > span`, and `.command-action-bar`. Add new classes for the analysis row, match flow hero, and rank badge.

- [ ] **Step 1: Remove `.command-story-grid` and `.command-story-side`**

Find and delete these two rule-blocks in `index.css`:
```css
/* DELETE these two blocks */
.command-story-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(18rem, 0.75fr);
  gap: 1.25rem;
  align-items: start;
}

.command-story-side {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1.25rem;
}
```

Also remove the responsive override that references them (around line 2065):
```css
/* DELETE this override */
.command-story-grid,
.command-fallout-grid {
  grid-template-columns: 1fr;
}
```
Replace with just:
```css
.command-fallout-grid {
  grid-template-columns: 1fr;
}
```

- [ ] **Step 2: Add `.command-analysis-row` (replaces story-grid)**

After the deleted block, add:
```css
.command-analysis-row {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 1.25rem;
  align-items: start;
}
```

And inside the existing `@media (max-width: 768px)` block, add:
```css
.command-analysis-row {
  grid-template-columns: 1fr;
}
```

- [ ] **Step 3: Add Match Flow hero styles**

After `.command-analysis-row`, add:
```css
.command-match-flow-header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  padding: 1rem 1.25rem 0.75rem;
  flex-wrap: wrap;
}

.command-match-flow-count {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: #475569;
  letter-spacing: 1px;
  margin-left: auto;
}

.command-match-flow-scroll-wrap {
  position: relative;
}

.command-match-flow-scroll-wrap::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 12px;
  height: 40px;
  background: linear-gradient(to bottom, transparent, rgba(15, 23, 42, 0.9));
  pointer-events: none;
}

.command-match-flow-scroll {
  max-height: 560px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #334155 transparent;
  outline-offset: 2px;
}

.command-match-flow-list {
  list-style: none;
  margin: 0;
  padding: 0 1.25rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.command-match-flow-event {
  display: grid;
  grid-template-columns: 1.75rem 1fr;
  gap: 0.75rem;
  align-items: start;
}

.command-event-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  background: #1e293b;
  color: #64748b;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.command-event-phase {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.55rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #475569;
  margin-bottom: 0.3rem;
}

.command-event-desc {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #f1f5f9;
  line-height: 1.45;
}

.command-event-items {
  margin: 0.5rem 0 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.command-event-items li {
  font-size: 0.72rem;
  color: #64748b;
  line-height: 1.5;
  padding-left: 0.75rem;
  border-left: 1px solid #1e293b;
}
```

Inside the existing `@media (max-width: 768px)` block, add:
```css
.command-match-flow-scroll {
  max-height: none;
  overflow-y: visible;
}

.command-match-flow-scroll-wrap::after {
  display: none;
}
```

Inside a new `@media (min-width: 769px) and (max-width: 1023px)` block, add:
```css
.command-match-flow-scroll {
  max-height: 480px;
}
```

- [ ] **Step 4: Update `.command-tactical-card` — remove orange accent**

Find the existing `.command-tactical-card` block and remove the orange border/background. The block should become:
```css
.command-tactical-card {
  padding: 1.25rem;
}

.command-tactical-card-footer {
  margin-top: 0.75rem;
  padding-top: 0.625rem;
  border-top: 1px solid #1e293b;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  color: #475569;
  letter-spacing: 0.5px;
}
```

- [ ] **Step 5: Update `.command-key-player > span` to circular rank badge**

Find the `.command-key-player > span` block and replace with:
```css
.command-rank-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
  flex-shrink: 0;
  color: #fff;
}
```

Also update `.command-key-player` grid columns to match:
```css
.command-key-player {
  display: grid;
  grid-template-columns: 1.75rem minmax(0, 1fr);
  gap: 0.75rem;
  align-items: start;
}
```

- [ ] **Step 6: Add `.command-action-bar` responsive styles**

Find the existing `.command-action-bar p` line. Add before it:
```css
.command-action-bar {
  display: flex;
  gap: 8px;
  align-items: stretch;
  padding: 12px 16px;
}

.command-action-bar-secondary {
  background: #1a2234;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #e2e8f0;
  padding: 10px 18px;
  font-family: var(--font-display);
  font-size: 0.75rem;
  letter-spacing: 1px;
  cursor: pointer;
  white-space: nowrap;
}

.command-action-bar-secondary:hover {
  background: #1e293b;
  border-color: #475569;
}

.command-action-bar-secondary:focus-visible {
  outline: 2px solid #f97316;
  outline-offset: 2px;
}
```

Inside the existing `@media (max-width: 768px)` block, add:
```css
.command-action-bar {
  flex-direction: column;
}

.command-action-bar-secondary {
  width: 100%;
  text-align: center;
}
```

- [ ] **Step 7: Verify the build compiles**

```
cd frontend && npm run build
```
Expected: Build succeeds. CSS-only changes — no TypeScript errors expected here.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/index.css
git commit -m "style: aftermath layout classes — analysis-row, match-flow hero, rank badge, action bar"
```

---

## Task 2: Headline — Add Context Line Prop

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/Headline.tsx`

Add a `contextLine` prop that renders as a second styled paragraph below the headline text. The `subtitle` prop stays in the signature (don't remove it — keeps backward compatibility) but won't be passed in post-sim anymore.

- [ ] **Step 1: Add `contextLine` prop and render it**

Replace the entire file with:
```tsx
export function Headline({
  text,
  week,
  subtitle,
  contextLine,
}: {
  text: string;
  week?: number;
  subtitle?: string;
  contextLine?: string;
}) {
  return (
    <div
      style={{
        background: 'linear-gradient(110deg, rgba(249,115,22,0.18) 0%, rgba(249,115,22,0.06) 45%, #0f172a 80%)',
        borderBottom: '1px solid rgba(249,115,22,0.25)',
        padding: '18px 20px 16px',
      }}
    >
      {week !== undefined && (
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.6rem',
            letterSpacing: '3px',
            color: '#f97316',
            textTransform: 'uppercase' as const,
            marginBottom: '6px',
            opacity: 0.8,
          }}
        >
          Week {week} Result
        </div>
      )}
      <h1
        style={{
          fontFamily: 'Oswald, sans-serif',
          fontSize: 'clamp(1.4rem, 4vw, 2rem)',
          fontWeight: 700,
          color: '#fff',
          letterSpacing: '1px',
          lineHeight: 1.1,
          textShadow: '0 0 30px rgba(249,115,22,0.35)',
          margin: 0,
        }}
      >
        {text}
      </h1>
      {contextLine && (
        <p
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.8rem',
            color: '#94a3b8',
            marginTop: '8px',
            marginBottom: 0,
            lineHeight: 1.5,
            letterSpacing: '0.3px',
          }}
        >
          {contextLine}
        </p>
      )}
      {subtitle && !contextLine && (
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.65rem',
            color: '#94a3b8',
            marginTop: '6px',
            letterSpacing: '0.5px',
          }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
}
```

Note: `subtitle` still renders as a fallback if `contextLine` is not provided, preserving any other uses.

- [ ] **Step 2: Verify build**

```
cd frontend && npm run build
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/Headline.tsx
git commit -m "feat: Headline — add contextLine prop for two-line post-match flavor text"
```

---

## Task 3: TacticalSummaryCard — Hide When Empty, Evidence Footer, No Orange

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx`

Return `null` when `turningPoint` is falsy. Add an evidence footer using the first `evidenceLanes` title. Remove the orange left-border and background — the `.command-tactical-card` CSS (updated in Task 1) now handles neutral styling.

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:
```tsx
import type { CommandDashboardLane } from '../../../types';

export function TacticalSummaryCard({
  turningPoint,
  evidenceLanes = [],
}: {
  turningPoint: string;
  evidenceLanes?: CommandDashboardLane[];
}) {
  if (!turningPoint) return null;

  const evidenceLabel = evidenceLanes.length > 0
    ? `Based on ${evidenceLanes[0].title}`
    : null;

  return (
    <section
      className="dm-panel command-tactical-card"
      data-testid="tactical-summary"
    >
      <p className="dm-kicker" style={{ letterSpacing: '2px', marginBottom: '6px' }}>
        TACTICAL READ
      </p>
      <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5, margin: 0 }}>
        {turningPoint}
      </p>
      {evidenceLabel && (
        <p className="command-tactical-card-footer">
          {evidenceLabel}
        </p>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```
cd frontend && npm run build
```
Expected: Build succeeds. TypeScript will validate that `TacticalSummaryCard` still satisfies its usage in `MatchWeek.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx
git commit -m "feat: TacticalSummaryCard — hide when empty, evidence footer, remove orange accent"
```

---

## Task 4: ReplayTimeline — Full Rebuild as Expanded Timeline

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx`

Replace the carousel (prev/next buttons, dot indicators, single-lane view) with a scrollable expanded list. Each lane with a non-empty `summary` becomes an event card. No score chips or impact labels (data doesn't support them without invention). Scroll container is keyboard-accessible via `tabIndex={0}`.

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:
```tsx
import type { CommandDashboardLane } from '../../../types';

export function ReplayTimeline({ lanes }: { lanes: CommandDashboardLane[] }) {
  const beats = lanes.filter((lane) => lane.summary.trim().length > 0);

  if (beats.length === 0) {
    return (
      <section className="dm-panel" data-testid="replay-timeline">
        <div className="command-match-flow-header">
          <p className="dm-kicker">Match Flow</p>
          <h3 className="dm-panel-title" style={{ margin: 0 }}>How It Unfolded</h3>
        </div>
        <p className="command-empty-copy" style={{ padding: '0 1.25rem 1.25rem' }}>
          No match flow notes were logged.
        </p>
      </section>
    );
  }

  return (
    <section className="dm-panel" data-testid="replay-timeline">
      <div className="command-match-flow-header">
        <p className="dm-kicker">Match Flow</p>
        <h3 className="dm-panel-title" style={{ margin: 0 }}>How It Unfolded</h3>
        <span className="command-match-flow-count">
          {beats.length} key moment{beats.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="command-match-flow-scroll-wrap">
        <div
          className="command-match-flow-scroll"
          tabIndex={0}
          aria-label="Match timeline — use arrow keys or scroll to read"
        >
          <ol className="command-match-flow-list">
            {beats.map((lane, i) => (
              <li key={i} className="command-match-flow-event">
                <span className="command-event-badge" aria-hidden="true">
                  {i + 1}
                </span>
                <div>
                  <span className="command-event-phase">{lane.title}</span>
                  <p className="command-event-desc">{lane.summary}</p>
                  {lane.items.length > 0 && (
                    <ul className="command-event-items">
                      {lane.items.map((item, j) => (
                        <li key={j}>{item}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```
cd frontend && npm run build
```
Expected: Build succeeds. The `useState` import is now gone — TypeScript will flag it only if it's still referenced. Confirm the import list is clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/ReplayTimeline.tsx
git commit -m "feat: ReplayTimeline — replace carousel with full-width expanded timeline"
```

---

## Task 5: KeyPlayersPanel — Circular Badges, Expanded Stat Labels, Your Club Tag

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`

Return `null` when `performers` is empty. Replace `NK`/`NC`/`ND` with `N Kills`/`N Catches`/`N Dodges`. Replace the boxed rank number with a circular `.command-rank-badge` (orange for player club, muted blue for opponent). Change "Your Club" badge from cyan to orange solid background.

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:
```tsx
import type { TopPerformer } from '../../../types';

function StatChips({ player }: { player: TopPerformer }) {
  return (
    <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap', marginTop: '4px', alignItems: 'center' }}>
      {player.eliminations_by_throw > 0 && (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.62rem',
            background: 'rgba(249,115,22,0.15)',
            color: '#f97316',
            borderRadius: '3px',
            padding: '2px 6px',
          }}
        >
          {player.eliminations_by_throw} Kill{player.eliminations_by_throw !== 1 ? 's' : ''}
        </span>
      )}
      {player.catches_made > 0 && (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.62rem',
            background: 'rgba(34,211,238,0.12)',
            color: '#22d3ee',
            borderRadius: '3px',
            padding: '2px 6px',
          }}
        >
          {player.catches_made} Catch{player.catches_made !== 1 ? 'es' : ''}
        </span>
      )}
      {player.dodges_successful > 0 && (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.62rem',
            background: 'rgba(163,230,53,0.12)',
            color: '#a3e635',
            borderRadius: '3px',
            padding: '2px 6px',
          }}
        >
          {player.dodges_successful} Dodge{player.dodges_successful !== 1 ? 's' : ''}
        </span>
      )}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.6rem',
          color: '#475569',
        }}
      >
        Impact Score {Math.round(player.score)}
      </span>
    </div>
  );
}

export function KeyPlayersPanel({
  performers,
  playerClubName,
}: {
  performers: TopPerformer[];
  playerClubName?: string;
}) {
  if (performers.length === 0) return null;

  return (
    <section className="dm-panel command-key-players" data-testid="key-players-panel">
      <div className="dm-panel-header">
        <p className="dm-kicker">Key Performers</p>
      </div>
      <div className="command-key-player-list">
        {performers.slice(0, 3).map((player, index) => {
          const isYours = Boolean(playerClubName && player.club_name === playerClubName);
          const badgeColor = isYours ? '#f97316' : '#334155';

          return (
            <article
              key={player.player_id}
              className="command-key-player"
              style={{ paddingTop: '10px', paddingBottom: '10px' }}
            >
              <span
                className="command-rank-badge"
                style={{ background: badgeColor }}
                aria-label={`Rank ${index + 1}`}
              >
                {index + 1}
              </span>
              <div>
                <strong style={{ fontSize: '0.9rem', color: '#f1f5f9' }}>{player.player_name}</strong>
                {isYours ? (
                  <span
                    style={{
                      marginLeft: '0.4rem',
                      fontSize: '0.6rem',
                      fontWeight: 700,
                      background: '#f97316',
                      color: '#000',
                      borderRadius: '3px',
                      padding: '1px 5px',
                      letterSpacing: '0.5px',
                    }}
                  >
                    Your Club
                  </span>
                ) : player.club_name ? (
                  <span style={{ fontSize: '0.7rem', color: '#64748b', marginLeft: '0.35rem' }}>
                    {player.club_name}
                  </span>
                ) : null}
                <StatChips player={player} />
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```
cd frontend && npm run build
```
Expected: Build succeeds. The `dm-badge-cyan` class reference is now gone — confirm no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx
git commit -m "feat: KeyPlayersPanel — circular badges, full stat labels, orange Your Club tag, hide when empty"
```

---

## Task 6: FalloutGrid — Rename to Week Fallout, Collapse When All Empty

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/FalloutGrid.tsx`

Return `null` when all three arrays are empty. Rename the section heading from "What your week caused" to "Week Fallout". Remove the "No notable fallout" empty-state message (the `null` return handles it).

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:
```tsx
import type { Aftermath } from '../../../types';
import type { ReactNode } from 'react';

function FalloutCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="dm-panel command-fallout-card">
      <p className="dm-kicker" style={{ borderTop: '2px solid #1e293b', paddingTop: '6px' }}>
        {title}
      </p>
      <div className="command-fallout-card-body">{children}</div>
    </article>
  );
}

export function FalloutGrid({
  playerGrowth,
  standingsShift,
  recruitReactions,
}: {
  playerGrowth: Aftermath['player_growth_deltas'];
  standingsShift: Aftermath['standings_shift'];
  recruitReactions: Aftermath['recruit_reactions'];
}) {
  if (playerGrowth.length === 0 && standingsShift.length === 0 && recruitReactions.length === 0) {
    return null;
  }

  return (
    <section className="command-fallout" data-testid="fallout-grid">
      <div className="command-section-heading">
        <p className="dm-kicker">Aftermath</p>
        <h3>Week Fallout</h3>
      </div>
      <div className="command-fallout-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        {playerGrowth.length > 0 && (
          <FalloutCard title="Who Grew">
            <ul className="command-clean-list">
              {playerGrowth.slice(0, 4).map((item) => (
                <li key={`${item.player_id}-${item.attribute}`}>
                  <strong>{item.player_name}</strong>
                  <span style={{ color: item.delta > 0 ? '#10b981' : '#f43f5e' }}>
                    {item.attribute} {item.delta > 0 ? '+' : ''}{item.delta}
                  </span>
                </li>
              ))}
            </ul>
          </FalloutCard>
        )}

        {standingsShift.length > 0 && (
          <FalloutCard title="Standings Shift">
            <ul className="command-clean-list">
              {standingsShift.slice(0, 4).map((item) => {
                const moved = item.new_rank - item.old_rank;
                const up = moved < 0;
                return (
                  <li key={item.club_id}>
                    <strong>{item.club_name}</strong>
                    <span style={{ color: up ? '#10b981' : '#f43f5e', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem' }}>
                      {up ? '↑' : '↓'} #{item.old_rank} → #{item.new_rank}
                    </span>
                  </li>
                );
              })}
            </ul>
          </FalloutCard>
        )}

        {recruitReactions.length > 0 && (
          <FalloutCard title="Prospect Pulse">
            <ul className="command-clean-list command-clean-list-loose">
              {recruitReactions.slice(0, 3).map((item) => {
                const delta = parseInt(item.interest_delta, 10);
                const isPositive = !isNaN(delta) && delta > 0;
                const isZero = !isNaN(delta) && delta === 0;
                return (
                  <li key={item.prospect_id}>
                    <strong>{item.prospect_name}</strong>
                    <span style={{ color: isPositive ? '#10b981' : isZero ? '#64748b' : '#f43f5e' }}>
                      {item.interest_delta}
                    </span>
                    <small>{item.evidence}</small>
                  </li>
                );
              })}
            </ul>
          </FalloutCard>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```
cd frontend && npm run build
```
Expected: Build succeeds. No type errors — the props interface is unchanged.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/FalloutGrid.tsx
git commit -m "feat: FalloutGrid — rename to Week Fallout, collapse entirely when no data"
```

---

## Task 7: AftermathActionBar — Solid Secondary Button, Responsive, Focus States

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx`

Switch Watch Replay from ghost/outline to solid dark fill. Use the `.command-action-bar` and `.command-action-bar-secondary` classes from Task 1. Add explicit `focus-visible` styles on the primary button too.

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:
```tsx
export function AftermathActionBar({
  onAdvance,
  onViewReplay,
  matchId,
  isAdvancing = false,
}: {
  onAdvance: () => void;
  onViewReplay?: () => void;
  matchId?: string;
  isAdvancing?: boolean;
}) {
  const hasReplay = Boolean(matchId && onViewReplay);

  return (
    <div className="command-action-bar" data-testid="after-action-bar">
      {hasReplay && (
        <button
          onClick={onViewReplay}
          className="command-action-bar-secondary"
        >
          WATCH REPLAY
        </button>
      )}
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        style={{
          flex: 1,
          background: isAdvancing ? '#7c3d12' : '#f97316',
          border: 'none',
          borderRadius: '8px',
          color: '#fff',
          padding: '10px 16px',
          fontFamily: 'Oswald, sans-serif',
          fontSize: '0.85rem',
          letterSpacing: '2px',
          cursor: isAdvancing ? 'default' : 'pointer',
          outline: 'none',
        }}
        onFocus={(e) => { e.currentTarget.style.outline = '2px solid #f97316'; e.currentTarget.style.outlineOffset = '2px'; }}
        onBlur={(e) => { e.currentTarget.style.outline = 'none'; }}
      >
        {isAdvancing ? 'ADVANCING...' : 'ADVANCE TO NEXT WEEK →'}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```
cd frontend && npm run build
```
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/AftermathActionBar.tsx
git commit -m "feat: AftermathActionBar — solid secondary Watch Replay, responsive stacking, focus states"
```

---

## Task 8: MatchWeek — Wire New Layout, Title, Context Line

**Files:**
- Modify: `frontend/src/components/MatchWeek.tsx`

This is the orchestrating change: rename the title to "Week N Debrief", compose the `contextLine` from `match_card` data, stop passing `subtitle` to Headline, move ReplayTimeline to full-width, add the `.command-analysis-row` for Tactical + Key Players, and conditionally render the analysis row only when at least one card has content.

- [ ] **Step 1: Add `buildContextLine` helper above `resolveMatchCardNames`**

After the imports block and before `resolveMatchCardNames`, add:

```tsx
function buildContextLine(mc: NonNullable<Aftermath['match_card']>): string {
  const { home_survivors, away_survivors, winner_club_id, home_club_id } = mc;
  if (!winner_club_id) {
    return `${home_survivors}–${away_survivors}. A rare dead heat.`;
  }
  const winnerSurvs = winner_club_id === home_club_id ? home_survivors : away_survivors;
  const loserSurvs = winner_club_id === home_club_id ? away_survivors : home_survivors;
  if (loserSurvs === 0) return `A ${winnerSurvs}–0 shutout. The margin left no room for argument.`;
  const diff = winnerSurvs - loserSurvs;
  if (diff >= 5) return `The ${winnerSurvs}–${loserSurvs} margin says everything.`;
  if (diff <= 1) return `A ${winnerSurvs}–${loserSurvs} finish. It could have gone either way.`;
  return `The final count: ${winnerSurvs}–${loserSurvs} survivors.`;
}
```

- [ ] **Step 2: Update `renderPostSimMode` — title, headline, layout**

The full updated `renderPostSimMode` function. Replace the existing function body with:

```tsx
const renderPostSimMode = () => {
  const activeResult = result ?? persistedResult;
  if (!activeResult?.aftermath) {
    return (
      <StatusMessage title="Processing results">
        Building the aftermath debrief.
      </StatusMessage>
    );
  }

  const { aftermath } = activeResult;
  const matchId = activeResult.dashboard.match_id;
  const week = activeResult.dashboard.week;
  const replayForMatch = replayData?.match_id === matchId ? replayData : null;
  const matchCardNames = aftermath.match_card
    ? resolveMatchCardNames({ matchCard: aftermath.match_card, currentData: data, activeResult })
    : null;

  const contextLine = aftermath.match_card
    ? buildContextLine(aftermath.match_card)
    : undefined;

  const turningPoint = replayForMatch?.report.turning_point ?? '';
  const evidenceLanes = replayForMatch?.report.evidence_lanes ?? [];
  const performers = replayForMatch?.report.top_performers ?? [];
  const showAnalysisRow = Boolean(turningPoint) || performers.length > 0;

  return (
    <div className="command-post-sim" data-testid="post-week-dashboard">
      <PageHeader eyebrow="WAR ROOM" title={`Week ${week} Debrief`} description="Review the result, who performed, and what your week caused." />

      {revealStage >= 0 && (
        <div className="command-reveal">
          <Headline
            text={aftermath.headline}
            week={week}
            contextLine={contextLine}
          />
        </div>
      )}

      {revealStage >= 1 && aftermath.match_card && matchCardNames && (
        <div className="command-reveal">
          <MatchScoreHero
            homeTeam={matchCardNames.homeTeam}
            awayTeam={matchCardNames.awayTeam}
            homeSurvivors={aftermath.match_card.home_survivors}
            awaySurvivors={aftermath.match_card.away_survivors}
            winnerClubId={aftermath.match_card.winner_club_id}
            homeClubId={aftermath.match_card.home_club_id}
          />
        </div>
      )}

      {revealStage >= 2 && (
        <div className="command-reveal">
          <ReplayTimeline lanes={activeResult.dashboard.lanes} />
        </div>
      )}

      {revealStage >= 2 && showAnalysisRow && (
        <div className="command-analysis-row command-reveal">
          <TacticalSummaryCard
            turningPoint={turningPoint}
            evidenceLanes={evidenceLanes}
          />
          <KeyPlayersPanel
            performers={performers}
            playerClubName={data?.player_club_name}
          />
        </div>
      )}

      {revealStage >= 3 && (
        <div className="command-reveal">
          <FalloutGrid
            playerGrowth={aftermath.player_growth_deltas}
            standingsShift={aftermath.standings_shift}
            recruitReactions={aftermath.recruit_reactions}
          />
        </div>
      )}

      {revealStage >= 4 && (
        <div className="command-reveal">
          <AftermathActionBar
            onAdvance={handleAdvanceWeek}
            onViewReplay={onOpenReplay ? () => onOpenReplay(matchId) : undefined}
            matchId={matchId}
            isAdvancing={isAdvancingWeek}
          />
        </div>
      )}
    </div>
  );
};
```

Note: `headlineSubtitle` is no longer computed — remove that `const headlineSubtitle = (() => {...})()` block entirely.

- [ ] **Step 3: Verify the build compiles cleanly**

```
cd frontend && npm run build
```
Expected: Build succeeds with no TypeScript errors. Check that `headlineSubtitle` reference is fully removed and `buildContextLine` is imported/accessible (it's defined in the same file).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/MatchWeek.tsx
git commit -m "feat: MatchWeek aftermath — Week N Debrief title, context line, full-width Match Flow, analysis row"
```

---

## Acceptance Criteria Checklist

Run through these manually after the final build to confirm all spec requirements are met:

- [ ] Page title reads "Week N Debrief" (N = actual week number from `dashboard.week`)
- [ ] "Command Center" does not appear as a heading on the aftermath screen
- [ ] No carousel controls (arrows, dots, prev/next) in Match Flow
- [ ] Match Flow is full-width (not constrained to a grid column)
- [ ] Week Fallout section does not render at all when all three data arrays are empty
- [ ] Watch Replay button has solid dark fill, not a ghost/outline border
- [ ] Orange appears only in: Advance CTA, player-club rank badge, "Your Club" tag, winner score box
- [ ] Stat chips display full words: "N Kills", "N Catches", "N Dodges", "Impact Score N"
- [ ] On mobile viewport (< 768px), Match Flow timeline has no internal scroll container
- [ ] Tactical Read card is hidden when `turning_point` is missing or empty
- [ ] Match Flow scroll area has `tabIndex={0}` and is keyboard-scrollable on desktop
- [ ] Both action buttons have visible focus states
