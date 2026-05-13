# Standings Phase 3: Add League Texture

**Depends on:** Phase 2 complete (RecentResultCard, ResultTagBadge, recap generation exist)

**Design system reference:** `docs/design-systems/League-Office-Standings-Design-System.md`, sections 11–12

---

## Goal

Add league recap and player spotlight sections to the right rail so the league feels alive — not just a table of numbers, but a world with narratives and standout performers.

---

## What exists after Phase 2

The right rail ("Around the League" panel) shows:
- `RecentResultCard` components with result tags and recap sentences
- An optional "View Full Schedule" button

**What's missing:**
- No league-wide recap items (biggest blowout, best defense, hottest team)
- No player spotlight for standout weekly performances
- The right rail tells individual match stories but not league-wide narratives

---

## What to build

### 1. `LeagueRecap`

**New file:** `frontend/src/components/standings/LeagueRecap.tsx`

A section showing 2–3 league-wide stat highlights below the recent results.

**Props:**
```ts
{
  items: LeagueRecapItem[];
}
```

**Type:**
```ts
type LeagueRecapItem = {
  label: string;
  teamName: string;
  value: string;
  type: 'dominance' | 'defense' | 'attack' | 'hot' | 'cold' | 'race';
};
```

**Layout:**
```
LEAGUE RECAP

Biggest Blowout
Autopsy Comets
6–0 vs Solstice Flare

Best Defense
Aurora Sentinels
Only 2.0 survivors allowed per game
```

**Rules:**
- Section header uses `dm-kicker`
- Each item: label is muted, team name is bright, value is secondary
- Show 2–3 items max — don't turn it into a spreadsheet
- Items should be computed from standings + recent results data

### 2. League recap stat resolvers

**Add to:** `frontend/src/components/standings/LeagueRecap.tsx` or a shared utility

These resolvers compute recap items from available data:

```ts
function computeLeagueRecap(standings: StandingRow[], recentResults: RecentResult[]): LeagueRecapItem[] {
  const items: LeagueRecapItem[] = [];

  // Biggest blowout from recent results
  if (recentResults.length > 0) {
    const biggestMargin = recentResults.reduce((best, r) => {
      const margin = Math.abs(r.homeSurvivors - r.awaySurvivors);
      return margin > best.margin ? { result: r, margin } : best;
    }, { result: recentResults[0], margin: 0 });

    if (biggestMargin.margin >= 3) {
      items.push({
        label: 'Biggest Blowout',
        teamName: biggestMargin.result.winnerName,
        value: `${biggestMargin.result.homeSurvivors}–${biggestMargin.result.awaySurvivors} vs ${loserName}`,
        type: 'dominance',
      });
    }
  }

  // Best elimination differential from standings
  const bestElimDiff = [...standings].sort((a, b) => b.elimination_differential - a.elimination_differential)[0];
  if (bestElimDiff) {
    items.push({
      label: 'Best Elimination Diff',
      teamName: bestElimDiff.club_name,
      value: `+${bestElimDiff.elimination_differential}`,
      type: 'defense',
    });
  }

  return items.slice(0, 3);
}
```

**Data note:** More sophisticated recap items (best defense by average, hottest team by streak) require match history data beyond what `StandingRow` provides. Start with what's computable from standings + recent results, and expand when more data is available.

### 3. `PlayerSpotlight`

**New file:** `frontend/src/components/standings/PlayerSpotlight.tsx`

Highlights one standout player from recent results.

**Props:**
```ts
{
  playerName: string;
  teamName: string;
  stats: {
    eliminations?: number;
    catches?: number;
    dodges?: number;
  };
  note: string;
}
```

**Layout:**
```
PLAYER SPOTLIGHT

Mika Thorn
Autopsy Comets

18 Eliminations · 6 Catches
Key performer in Autopsy's Week 9 shutout.
```

**Rules:**
- Player name is the strongest text
- Team name is secondary
- Stats shown as inline badges or text
- Note is one sentence of context
- If no standout player, show: "No standout performance this week." or hide the section

**Data note:** Player performance data per match is available on the `MatchReplayResponse` (`report.top_performers`). However, the standings page doesn't currently fetch replay data. Two options:

**Option A (recommended for Phase 3):** Add a `weekly_spotlight` field to the standings API response containing the top performer. Backend change but keeps the frontend clean.

**Option B:** Skip PlayerSpotlight until match performance data is available on the standings endpoint. Show a placeholder: "Player spotlights coming soon."

### 4. Wire into the right rail

**Edit:** `frontend/src/components/standings/RecentMatchesSidebar.tsx`

Add `LeagueRecap` and `PlayerSpotlight` below the recent results:

```tsx
<div className="dm-panel">
  <span className="dm-kicker">Around the League</span>

  {/* Recent results from Phase 2 */}
  {recentResults.map(r => <RecentResultCard key={r.id} ... />)}

  {/* League recap */}
  {recapItems.length > 0 && <LeagueRecap items={recapItems} />}

  {/* Player spotlight */}
  {spotlight && <PlayerSpotlight ... />}

  {/* Schedule button from Phase 2 */}
</div>
```

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/standings/LeagueRecap.tsx` | Create |
| `frontend/src/components/standings/PlayerSpotlight.tsx` | Create (may need backend `weekly_spotlight` field) |
| `frontend/src/components/standings/RecentMatchesSidebar.tsx` | Edit — add LeagueRecap and PlayerSpotlight sections |

---

## What NOT to build

- Interactive team/player links from recap items — future feature
- Historical league recap (season-long superlatives) — future feature
- Multiple spotlight players — one is enough for the rail
- AI-generated recap text — keep it deterministic for now
