# Match Replay & Aftermath Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surgically upgrade the visual presentation of the post-match aftermath screen and match replay viewer — drama-first aesthetic for aftermath, full-court layout for replay — with no backend changes and no structural reorganization.

**Architecture:** All 11 tasks touch only `frontend/src/` files. Each task is self-contained: make the change, verify the TypeScript build passes, commit. No new components, no new endpoints, no Python changes. The aftermath keeps its 5-stage staged-reveal structure; the replay shifts from a dual-pane grid to a single full-width column.

**Tech Stack:** React 18, TypeScript, Vite, inline styles (matching existing codebase pattern)

---

## File Map

| File | Role | Changes |
|---|---|---|
| `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx` | Post-match CTA bar | Replace ActionButton with custom styled buttons; remove prose |
| `frontend/src/components/match-week/aftermath/Headline.tsx` | Stage 0 headline | Add gradient banner, eyebrow, subtitle; two new optional props |
| `frontend/src/components/MatchWeek.tsx` | Orchestrates aftermath stages | Pass `week` and `subtitle` to `Headline` |
| `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx` | Stage 1 score | Bigger numbers, loser dimmed, deeper winner glow |
| `frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx` | Stage 2 tactical text | Orange left-border accent + kicker label |
| `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx` | Stage 2 performers | Replace prose stat line with colored K/C/D chips |
| `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx` | Stage 2 match flow | Rename "Replay identity" → "Match Flow"; add lane accent borders |
| `frontend/src/components/match-week/aftermath/FalloutGrid.tsx` | Stage 3 fallout | Color ↑↓ arrows and delta values |
| `frontend/src/components/MatchReplay.tsx` | Replay viewer | Full-court layout, slim score header, formation fix, play strip accent, tab rename |

---

## Task 1: AftermathActionBar — Primary CTA upgrade

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx`

- [ ] **Step 1: Replace the component**

Replace the entire file content:

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
  return (
    <div style={{ padding: '12px' }} data-testid="after-action-bar">
      <button
        onClick={onAdvance}
        disabled={isAdvancing}
        style={{
          width: '100%',
          background: isAdvancing ? '#7c3d12' : '#f97316',
          border: 'none',
          borderRadius: '8px',
          color: '#fff',
          padding: '12px',
          fontFamily: 'Oswald, sans-serif',
          fontSize: '0.9rem',
          letterSpacing: '2px',
          cursor: isAdvancing ? 'default' : 'pointer',
          boxShadow: isAdvancing ? 'none' : '0 0 20px rgba(249,115,22,0.2)',
        }}
      >
        {isAdvancing ? 'ADVANCING...' : 'ADVANCE TO NEXT WEEK →'}
      </button>
      {matchId && onViewReplay && (
        <button
          onClick={onViewReplay}
          style={{
            width: '100%',
            background: 'transparent',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#64748b',
            padding: '8px',
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.75rem',
            letterSpacing: '1px',
            cursor: 'pointer',
            marginTop: '6px',
          }}
        >
          WATCH REPLAY
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0, no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/AftermathActionBar.tsx
git commit -m "feat: upgrade aftermath action bar — primary orange CTA, secondary watch replay"
```

---

## Task 2: Headline — Gradient banner + eyebrow + subtitle

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/Headline.tsx`
- Modify: `frontend/src/components/MatchWeek.tsx`

- [ ] **Step 1: Replace `Headline.tsx`**

```tsx
export function Headline({
  text,
  week,
  subtitle,
}: {
  text: string;
  week?: number;
  subtitle?: string;
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
            textTransform: 'uppercase',
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
      {subtitle && (
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

- [ ] **Step 2: Update `MatchWeek.tsx` — compute subtitle and pass new props**

In `renderPostSimMode()`, directly after the existing `matchCardNames` derivation, add the `headlineSubtitle` computation. Then update the Stage 0 render.

Find this block (around line 196):

```tsx
    const matchCardNames = aftermath.match_card
      ? resolveMatchCardNames({ matchCard: aftermath.match_card, currentData: data, activeResult })
      : null;
```

Replace with:

```tsx
    const matchCardNames = aftermath.match_card
      ? resolveMatchCardNames({ matchCard: aftermath.match_card, currentData: data, activeResult })
      : null;

    const headlineSubtitle = (() => {
      const mc = aftermath.match_card;
      if (!mc || !matchCardNames) return undefined;
      if (!mc.winner_club_id) {
        return `${matchCardNames.homeTeam} vs ${matchCardNames.awayTeam} · ${mc.home_survivors} — ${mc.away_survivors}`;
      }
      const homeIsWinner = mc.winner_club_id === mc.home_club_id;
      const winnerName = homeIsWinner ? matchCardNames.homeTeam : matchCardNames.awayTeam;
      const loserName = homeIsWinner ? matchCardNames.awayTeam : matchCardNames.homeTeam;
      const winnerSurvs = homeIsWinner ? mc.home_survivors : mc.away_survivors;
      const loserSurvs = homeIsWinner ? mc.away_survivors : mc.home_survivors;
      return `${winnerName} def. ${loserName} · ${winnerSurvs} survivors to ${loserSurvs}`;
    })();
```

Then find the Stage 0 JSX:

```tsx
        {revealStage >= 0 && (
          <div className="command-reveal">
            <Headline text={aftermath.headline} />
          </div>
        )}
```

Replace with:

```tsx
        {revealStage >= 0 && (
          <div className="command-reveal">
            <Headline
              text={aftermath.headline}
              week={activeResult.dashboard.week}
              subtitle={headlineSubtitle}
            />
          </div>
        )}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0. TypeScript will catch any prop mismatch.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match-week/aftermath/Headline.tsx frontend/src/components/MatchWeek.tsx
git commit -m "feat: headline banner — gradient background, week eyebrow, winner subtitle"
```

---

## Task 3: MatchScoreHero — Bigger numbers, winner/loser contrast

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx`

- [ ] **Step 1: Update `TeamScore` to upgrade the score number**

Find the `<span className="command-score-number">` line inside `TeamScore` (around line 51):

```tsx
      <span className="command-score-number">{displayedSurvivors}</span>
```

Replace with:

```tsx
      <span
        className="command-score-number"
        style={{
          fontSize: 'clamp(2.8rem, 8vw, 4rem)',
          opacity: isWinner ? 1 : 0.45,
          textShadow: isWinner
            ? side === 'home'
              ? '0 0 24px rgba(249,115,22,0.6)'
              : '0 0 24px rgba(34,211,238,0.5)'
            : 'none',
          display: 'block',
        }}
      >
        {displayedSurvivors}
      </span>
```

- [ ] **Step 2: Deepen winner card glow**

Find the `style` on the outer `<div>` of `TeamScore` (the `boxShadow` line, around line 44):

```tsx
        boxShadow: isWinner ? `0 0 28px ${side === 'home' ? 'rgba(249,115,22,0.18)' : 'rgba(34,211,238,0.16)'}` : undefined,
```

Replace with:

```tsx
        boxShadow: isWinner ? `0 0 36px ${side === 'home' ? 'rgba(249,115,22,0.28)' : 'rgba(34,211,238,0.24)'}` : undefined,
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/match-week/aftermath/MatchScoreHero.tsx
git commit -m "feat: score hero — larger numbers, dimmed loser, deeper winner glow"
```

---

## Task 4: TacticalSummaryCard — Left-border callout

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx`

- [ ] **Step 1: Replace the component**

```tsx
import type { CommandDashboardLane } from '../../../types';

export function TacticalSummaryCard({
  turningPoint,
  evidenceLanes = [],
}: {
  turningPoint: string;
  evidenceLanes?: CommandDashboardLane[];
}) {
  const fallback = evidenceLanes.find((lane) => lane.summary)?.summary;
  const body = turningPoint || fallback || 'The staff report is still assembling the tactical read for this match.';

  return (
    <section
      className="dm-panel command-tactical-card"
      data-testid="tactical-summary"
      style={{
        borderLeft: '3px solid rgba(249,115,22,0.5)',
        background: 'rgba(249,115,22,0.04)',
      }}
    >
      <p
        className="dm-kicker"
        style={{ color: '#f97316', letterSpacing: '2px', marginBottom: '6px' }}
      >
        TACTICAL READ
      </p>
      <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.5, margin: 0 }}>
        {body}
      </p>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx
git commit -m "feat: tactical summary card — orange left border, kicker label"
```

---

## Task 5: KeyPlayersPanel — Colored stat chips

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`

- [ ] **Step 1: Replace the component**

Remove the old `statLine()` function and replace with a `StatChips` sub-component:

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
          {player.eliminations_by_throw}K
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
          {player.catches_made}C
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
          {player.dodges_successful}D
        </span>
      )}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '0.6rem',
          color: '#475569',
        }}
      >
        {Math.round(player.score)} impact
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
            const isYours = playerClubName
              ? player.club_name === playerClubName
              : false;
            return (
              <article
                key={player.player_id}
                className="command-key-player"
                style={{
                  borderLeft: index === 0
                    ? '2px solid #f97316'
                    : isYours
                    ? '2px solid #22d3ee'
                    : undefined,
                }}
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
                  <StatChips player={player} />
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

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx
git commit -m "feat: key performers — colored K/C/D stat chips, #1 gets orange accent"
```

---

## Task 6: ReplayTimeline — Rename and lane accent borders

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx`

- [ ] **Step 1: Replace the component**

```tsx
import type { CommandDashboardLane } from '../../../types';

export function ReplayTimeline({ lanes }: { lanes: CommandDashboardLane[] }) {
  return (
    <section className="dm-panel command-timeline" data-testid="replay-timeline">
      <div className="dm-panel-header">
        <p className="dm-kicker">Match Flow</p>
        <h3 className="dm-panel-title">How it unfolded</h3>
      </div>
      <div className="command-timeline-list">
        {lanes.length === 0 ? (
          <p className="command-empty-copy">No match flow notes were logged.</p>
        ) : (
          lanes.slice(0, 4).map((lane, index) => (
            <article
              key={`${lane.title}-${index}`}
              className="command-timeline-item"
              style={{
                borderLeft: `3px solid ${index === 0 ? '#f97316' : '#334155'}`,
                borderRadius: '0 4px 4px 0',
                paddingLeft: '10px',
              }}
            >
              <div>
                <p className="dm-kicker">{lane.title}</p>
                <strong style={{ fontSize: '0.85rem', color: '#f8fafc' }}>{lane.summary}</strong>
                {lane.items.length > 0 && (
                  <ul>
                    {lane.items.slice(0, 3).map((item) => (
                      <li key={item} style={{ color: '#64748b', fontSize: '0.75rem' }}>
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/ReplayTimeline.tsx
git commit -m "feat: match flow panel — renamed from Replay Identity, lane accent borders"
```

---

## Task 7: FalloutGrid — Colored arrows and deltas

**Files:**
- Modify: `frontend/src/components/match-week/aftermath/FalloutGrid.tsx`

- [ ] **Step 1: Replace the component**

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
  return (
    <section className="command-fallout" data-testid="fallout-grid">
      <div className="command-section-heading">
        <p className="dm-kicker">Match Fallout</p>
        <h3>What your week caused</h3>
      </div>
      <div className="command-fallout-grid">
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

        {playerGrowth.length === 0 && standingsShift.length === 0 && recruitReactions.length === 0 && (
          <p className="command-empty-copy" style={{ gridColumn: '1 / -1' }}>
            No notable fallout from this match.
          </p>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/match-week/aftermath/FalloutGrid.tsx
git commit -m "feat: fallout grid — colored rank arrows, green/red growth deltas"
```

---

## Task 8: MatchReplay — Full-court layout

**Files:**
- Modify: `frontend/src/components/MatchReplay.tsx`

The `dm-replay-layout` dual-pane grid is removed. The component becomes a single full-width column: score header → court → controls → play strip → tabs → "Back to Results".

- [ ] **Step 1: Replace the return statement in `MatchReplay`**

Find the `return (` at the bottom of the `MatchReplay` default export (around line 727) and replace the entire JSX return with:

```tsx
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', overflow: 'visible' }}>
      <ScoreHeader
        homeName={data.home_club_name}
        awayName={data.away_club_name}
        homeLiving={homeLiving}
        awayLiving={awayLiving}
        homeTotal={homeTotal}
        awayTotal={awayTotal}
        week={data.week}
        winnerName={winnerName}
        winnerClubId={data.winner_club_id}
        homeClubId={data.home_club_id}
      />

      {/* Court — full width */}
      <div style={{ background: '#060d1a', padding: '8px 0 4px' }}>
        {hasCourtData ? (
          <CourtView
            homeName={data.home_club_name}
            awayName={data.away_club_name}
            homeIds={homeIds}
            awayIds={awayIds}
            positions={positions}
            playerRegistry={playerRegistry}
            eliminatedIds={eliminatedIds}
            throwerId={throwerId}
            targetId={targetId}
            activeResolution={activeResolution}
            flashTargetId={flashTargetId}
            ballAnimKey={ballAnimKey}
          />
        ) : (
          <div
            style={{
              height: 180,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#0f172a',
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              color: '#475569',
            }}
          >
            No player tracking data available.
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="dm-replay-controls" style={{ padding: '6px 12px' }}>
        <button aria-label="Previous replay event" onClick={stepBack} disabled={eventIndex === 0} style={{ background: 'transparent', border: '1px solid #334155', borderRadius: 4, color: eventIndex === 0 ? '#334155' : '#94a3b8', padding: '4px 10px', cursor: eventIndex === 0 ? 'default' : 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>{'<'}</button>
        <button aria-label={isPlaying ? 'Pause replay' : 'Play replay'} onClick={togglePlay} style={{ background: isPlaying ? '#1e293b' : '#f97316', border: 'none', borderRadius: 4, color: '#ffffff', padding: '4px 14px', cursor: 'pointer', fontFamily: 'Oswald, sans-serif', fontSize: 13, letterSpacing: 1 }}>
          {isPlaying ? 'PAUSE' : 'PLAY'}
        </button>
        <button aria-label="Next replay event" onClick={stepForward} disabled={eventIndex >= totalEvents - 1} style={{ background: 'transparent', border: '1px solid #334155', borderRadius: 4, color: eventIndex >= totalEvents - 1 ? '#334155' : '#94a3b8', padding: '4px 10px', cursor: eventIndex >= totalEvents - 1 ? 'default' : 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>{'>'}</button>
        <button onClick={cycleSpeed} style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 4, color: '#f97316', padding: '4px 10px', cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, letterSpacing: 1 }}>{playSpeed}</button>
        <div
          className="dm-replay-scrubber"
          style={{ height: 8, background: '#1e293b', borderRadius: 4, cursor: 'pointer', position: 'relative', flex: 1 }}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            setEventIndex(Math.round(((e.clientX - rect.left) / rect.width) * (totalEvents - 1)));
            setIsPlaying(false);
          }}
        >
          <div style={{ height: '100%', width: `${progress * 100}%`, background: '#f97316', borderRadius: 4, transition: 'width 0.1s' }} />
          {data.key_play_indices.map((ki) => (
            <div key={ki} style={{ position: 'absolute', top: -2, left: `${(ki / (totalEvents - 1)) * 100}%`, width: 3, height: 12, background: '#f59e0b', borderRadius: 1.5, transform: 'translateX(-50%)' }} />
          ))}
        </div>
        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#475569', whiteSpace: 'nowrap' as const }}>
          {eventIndex + 1} / {totalEvents}
        </span>
        {data.key_play_indices.length > 0 && (
          <button aria-label="Next key replay event" onClick={jumpToKeyEvent} style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid #f59e0b44', borderRadius: 4, color: '#f59e0b', padding: '4px 8px', cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: 1, whiteSpace: 'nowrap' as const }}>
            KEY
          </button>
        )}
      </div>

      {/* Current play strip */}
      <div
        style={{
          margin: '0 12px 8px',
          borderLeft: `3px solid ${isKeyPlay ? '#f59e0b' : '#334155'}`,
          background: isKeyPlay ? 'rgba(245,158,11,0.06)' : '#0f172a',
          borderRadius: '0 6px 6px 0',
          padding: '8px 12px',
        }}
      >
        {currentEvent && (
          <EventCard
            label={currentEvent.label}
            detail={currentEvent.detail}
            eventType={currentEvent.event_type}
            isKeyPlay={isKeyPlay}
          />
        )}
      </div>

      {/* Tabbed analysis — full width below court */}
      <div style={{ borderTop: '1px solid #1e293b', flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', padding: '0 4px' }}>
          {(['pbp', 'keyplays', 'stats'] as const).map((tab) => {
            const labels = { pbp: 'PLAY-BY-PLAY', keyplays: 'KEY PLAYS', stats: 'REPORT' };
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{ background: 'transparent', border: 'none', borderBottom: `2px solid ${isActive ? '#f97316' : 'transparent'}`, color: isActive ? '#f97316' : '#475569', padding: '10px 12px', cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: 1, marginBottom: -1 }}
              >
                {labels[tab]}
              </button>
            );
          })}
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px', maxHeight: '280px' }}>
          {activeTab === 'pbp' && (
            <PlayByPlayPanel events={data.proof_events} currentIndex={eventIndex} />
          )}
          {activeTab === 'keyplays' && <KeyPlaysPanel data={data} currentIndex={eventIndex} onJump={jumpTo} />}
          {activeTab === 'stats' && <StatsPanel data={data} />}
        </div>
      </div>

      {/* Back to results */}
      <div style={{ padding: '8px 12px', borderTop: '1px solid #1e293b', background: '#020617' }}>
        <button
          onClick={onContinue}
          style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#94a3b8', padding: '8px', cursor: 'pointer', fontFamily: 'Oswald, sans-serif', fontSize: 13, letterSpacing: 1 }}
        >
          BACK TO RESULTS
        </button>
      </div>
    </div>
  );
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MatchReplay.tsx
git commit -m "feat: replay layout — full-court single column, tabs below court"
```

---

## Task 9: MatchReplay — Slim score header

**Files:**
- Modify: `frontend/src/components/MatchReplay.tsx` (the `ScoreHeader` sub-component)

- [ ] **Step 1: Replace `ScoreHeader`**

Find and replace the entire `ScoreHeader` function (lines ~310–434):

```tsx
function ScoreHeader({
  homeName,
  awayName,
  homeLiving,
  awayLiving,
  week,
  winnerName,
  winnerClubId,
  homeClubId,
}: {
  homeName: string;
  awayName: string;
  homeLiving: number;
  awayLiving: number;
  homeTotal: number;
  awayTotal: number;
  week: number;
  winnerName: string | null;
  winnerClubId: string | null;
  homeClubId: string;
}) {
  const homeIsWinner = winnerClubId === homeClubId;

  return (
    <div
      style={{
        background: '#0f172a',
        borderBottom: '1px solid #1e293b',
        borderRadius: '8px 8px 0 0',
      }}
    >
      {winnerName && (
        <div
          style={{
            textAlign: 'center',
            padding: '4px',
            background: 'rgba(249,115,22,0.08)',
            borderBottom: '1px solid rgba(249,115,22,0.2)',
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.7rem',
            color: '#f97316',
            letterSpacing: '2px',
          }}
        >
          ★ {winnerName.toUpperCase()} WIN
        </div>
      )}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
        }}
      >
        <div
          style={{
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.85rem',
            color: '#f97316',
            letterSpacing: '1px',
          }}
        >
          {homeName.toUpperCase()}
        </div>
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              fontFamily: 'Oswald, sans-serif',
              fontSize: '1.4rem',
              fontWeight: 700,
              letterSpacing: '3px',
              color: '#fff',
            }}
          >
            <span style={{ opacity: winnerClubId && !homeIsWinner ? 0.45 : 1, color: '#f97316' }}>
              {homeLiving}
            </span>
            {' '}
            <span style={{ color: '#334155', fontSize: '0.9rem' }}>—</span>
            {' '}
            <span style={{ opacity: winnerClubId && homeIsWinner ? 0.45 : 1, color: '#22d3ee' }}>
              {awayLiving}
            </span>
          </div>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.55rem',
              color: '#334155',
              letterSpacing: '2px',
              marginTop: '2px',
            }}
          >
            WEEK {week}
          </div>
        </div>
        <div
          style={{
            fontFamily: 'Oswald, sans-serif',
            fontSize: '0.85rem',
            color: '#22d3ee',
            letterSpacing: '1px',
            textAlign: 'right',
          }}
        >
          {awayName.toUpperCase()}
        </div>
      </div>
    </div>
  );
}
```

Note: `homeTotal` and `awayTotal` props are removed from this component. The `ScoreHeader` call in the return statement (set in Task 8) still passes them — update the call site now.

- [ ] **Step 2: Update the ScoreHeader call site in the return statement**

Find the `<ScoreHeader` block inside the return statement and replace it with:

```tsx
      <ScoreHeader
        homeName={data.home_club_name}
        awayName={data.away_club_name}
        homeLiving={homeLiving}
        awayLiving={awayLiving}
        week={data.week}
        winnerName={winnerName}
        winnerClubId={data.winner_club_id}
        homeClubId={data.home_club_id}
      />
```

- [ ] **Step 4: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0. TypeScript will error if `homeTotal`/`awayTotal` are still referenced in the component.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/MatchReplay.tsx
git commit -m "feat: replay score header — slim strip with team names and inline score"
```

---

## Task 10: MatchReplay — Player formation fix

**Files:**
- Modify: `frontend/src/components/MatchReplay.tsx` (the `getFormationPositions` function)

- [ ] **Step 1: Replace `getFormationPositions`**

Find and replace the entire `getFormationPositions` function (around lines 30–48):

```tsx
function getFormationPositions(ids: string[], side: 'left' | 'right', courtWidth: number, courtHeight: number): Map<string, Vec2> {
  const map = new Map<string, Vec2>();
  if (ids.length === 0) return map;

  const hMid = courtHeight / 2;
  const vGap = courtHeight / 3.2;

  // 2-column × 3-row formation: near-center column and back column
  const colX = {
    left:  [courtWidth / 2 - 55, courtWidth / 4],
    right: [courtWidth / 2 + 55, 3 * courtWidth / 4],
  };
  const rowY = [hMid - vGap, hMid, hMid + vGap];

  ids.forEach((id, i) => {
    const col = i < 3 ? 0 : 1;
    const row = i % 3;
    map.set(id, { x: colX[side][col], y: rowY[row] });
  });
  return map;
}
```

This places players 0–2 in the near-center column (top/mid/bottom rows) and players 3–5 in the back column — each team clustered on their own half, facing center.

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MatchReplay.tsx
git commit -m "fix: player formation — 2-column arc per team, clustered on own half"
```

---

## Task 11: Final verification

- [ ] **Step 1: Run Python test suite**

```bash
python -m pytest -q
```

Expected: all tests pass (no Python files changed, but confirm no breakage).

- [ ] **Step 2: Run frontend lint**

```bash
cd frontend && npm run lint
```

Expected: exits 0, no errors.

- [ ] **Step 3: Run full frontend build one final time**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 4: Smoke check in browser**

Launch the app:
```bash
python -m dodgeball_sim
```

Navigate through a full match week:
1. Pre-sim screen loads normally.
2. Simulate a match.
3. Aftermath reveals in sequence — verify:
   - Stage 0: orange gradient headline banner with "WEEK N RESULT" eyebrow and subtitle line.
   - Stage 1: large score numbers, loser at reduced opacity.
   - Stage 2: TacticalSummaryCard has orange left border; KeyPlayersPanel shows K/C/D chips; ReplayTimeline titled "Match Flow" with lane borders.
   - Stage 3: FalloutGrid arrows are green ↑ / red ↓.
   - Stage 4: "ADVANCE TO NEXT WEEK →" full-width orange button; "WATCH REPLAY" demoted below.
4. Open Watch Replay — verify:
   - Court is full width (no sidebar panel beside it).
   - Score header is a single compact strip.
   - Players cluster on their own half in arc formation.
   - "BOX SCORE" tab now reads "REPORT".
   - Back to Results button at bottom.
