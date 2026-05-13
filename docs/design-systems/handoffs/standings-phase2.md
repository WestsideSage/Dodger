# Standings Phase 2: Make Around the League Useful

**Depends on:** Phase 1 complete (YourTeamSummary, row highlighting, StandingsExplainer exist)

**Design system reference:** `docs/design-systems/League-Office-Standings-Design-System.md`, sections 8–10

---

## Goal

Turn the right rail from a bare recent-matches list into a sports recap panel with result tags, narrative recaps, and a schedule link.

---

## What exists today

`frontend/src/components/LeagueContext.tsx` renders a `RecentMatchesSidebar` component on the right side. This sidebar (`frontend/src/components/standings/RecentMatchesSidebar.tsx`) shows recent match results in a simple list format.

**Current gaps:**
- Match results have no tags (blowout, upset, shutout, etc.)
- No recap sentences explaining what happened
- No "Around the League" header giving the panel personality
- Results are a plain list with no visual character

---

## What to build

### 1. `RecentResultCard`

**New file:** `frontend/src/components/standings/RecentResultCard.tsx`

A single match result card with team names, survivor counts, result tag, and recap sentence.

**Props:**
```ts
{
  week: number;
  homeTeam: string;
  awayTeam: string;
  homeSurvivors: number;
  awaySurvivors: number;
  winner: 'home' | 'away' | null;
  tag?: string;
  recap?: string;
}
```

**Layout:**
```
WEEK 9                            BLOWOUT
Solstice Flare      0 – 6        Autopsy Comets
Autopsy Comets dominate with a clean sweep.
```

**Rules:**
- Week number is a `dm-kicker` label
- Team names are left-aligned (home) and right-aligned (away)
- Survivor counts are bold, centered between team names
- Winner's name is brighter; loser is muted
- Tag badge sits top-right, colored by tag type
- Recap is one sentence of secondary text below the score line
- Card uses `dm-panel` with subtle border

### 2. `ResultTagBadge`

**New file:** `frontend/src/components/standings/ResultTagBadge.tsx`

A small colored badge for match result classification.

**Props:**
```ts
{
  tag: string;
}
```

**Tag color mapping:**
| Tag | Label | Color |
| --- | ----- | ----- |
| `blowout` | Blowout | Purple `#a78bfa` |
| `shutout` | Shutout | Cyan `#22d3ee` |
| `statementWin` | Statement Win | Green `#22c55e` |
| `upset` | Upset | Gold `#facc15` |
| `clutchFinish` | Clutch Finish | Orange `#fb923c` |
| `collapse` | Collapse | Red `#ef4444` |
| `standard` | — | Don't show badge |

**Rules:**
- Badge has a colored text + tinted background + colored border (matching the design system token patterns)
- Standard results don't display a badge
- Badge is compact — one word

### 3. Result tag resolver

**Add to:** `frontend/src/components/standings/RecentResultCard.tsx` (or a shared utility)

Deterministic tag assignment based on match result:

```ts
function getResultTag(homeSurvivors: number, awaySurvivors: number): string {
  const margin = Math.abs(homeSurvivors - awaySurvivors);
  const loserSurvivors = Math.min(homeSurvivors, awaySurvivors);

  if (loserSurvivors === 0 && margin >= 5) return 'blowout';
  if (loserSurvivors === 0) return 'shutout';
  if (margin <= 1) return 'clutchFinish';
  if (margin >= 4) return 'statementWin';
  return 'standard';
}
```

Recap sentence resolver:

```ts
function getRecapSentence(winner: string, loser: string, tag: string): string {
  switch (tag) {
    case 'blowout': return `A dominant showing from ${winner}.`;
    case 'shutout': return `A clean shutout win for ${winner}.`;
    case 'statementWin': return `${winner} earn a convincing win.`;
    case 'clutchFinish': return `${winner} edge ${loser} in a tight finish.`;
    default: return `${winner} handle business against ${loser}.`;
  }
}
```

**Note:** Using neutral phrasing ("A dominant showing from...") avoids singular/plural grammar issues with team names.

### 4. Update `RecentMatchesSidebar`

**Edit:** `frontend/src/components/standings/RecentMatchesSidebar.tsx`

Replace the current simple list with an "Around the League" panel:

```tsx
<div className="dm-panel">
  <span className="dm-kicker">Around the League</span>

  {recentResults.map(result => (
    <RecentResultCard
      key={result.id}
      week={result.week}
      homeTeam={result.homeTeamName}
      awayTeam={result.awayTeamName}
      homeSurvivors={result.homeSurvivors}
      awaySurvivors={result.awaySurvivors}
      winner={result.winnerSide}
      tag={getResultTag(result.homeSurvivors, result.awaySurvivors)}
      recap={getRecapSentence(winnerName, loserName, tag)}
    />
  ))}
</div>
```

**Data source:** The recent results data should already be available from the existing sidebar. If the sidebar currently receives raw match data, the tag/recap can be computed client-side with the resolver functions above.

### 5. `ViewScheduleButton`

**Add to:** bottom of the `RecentMatchesSidebar` panel.

A simple muted button linking to the full schedule (if a schedule view exists) or acting as a placeholder:

```tsx
<button className="dm-badge dm-badge-slate" style={{ width: '100%', textAlign: 'center', padding: '0.75rem', cursor: 'pointer' }}>
  View Full Schedule
</button>
```

If no schedule route exists yet, this can be a no-op or hidden.

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/standings/RecentResultCard.tsx` | Create |
| `frontend/src/components/standings/ResultTagBadge.tsx` | Create |
| `frontend/src/components/standings/RecentMatchesSidebar.tsx` | Edit — wrap in "Around the League" panel, use RecentResultCard |

---

## What NOT to build

- League Recap section (biggest blowout, best defense) — Phase 3
- Player Spotlight — Phase 3
- Clickable team links from result cards — future feature
- Upset/comeback detection using rankings — requires rank-before-match data not currently available
