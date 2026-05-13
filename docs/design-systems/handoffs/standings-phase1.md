# Standings Phase 1: Make Standings Clearer

**Design system reference:** `docs/design-systems/League-Office-Standings-Design-System.md`, sections 4–7, 13

---

## Goal

Give the standings page strong readability — a summary card for the user's team, proper row highlighting, form indicators, and a playoff explainer so the player always knows where they stand.

---

## What exists today

The standings screen lives in `frontend/src/components/LeagueContext.tsx` (173 lines). It renders:

- `PageHeader` with eyebrow "League Office", title "Standings"
- A `<table>` with columns: Rank, Club, W, L, D, Pts, Win Rate, GB, Elim Diff
- `RecentMatchesSidebar` on the right showing recent match results

**Key data:** Uses `useApiResource<StandingsResponse>('/api/standings')`. The `StandingsResponse` includes `standings: StandingRow[]`.

**`StandingRow` type (from `types.ts`):**
```ts
{
  club_id: string;
  club_name: string;
  wins: number;
  losses: number;
  draws: number;
  points: number;
  elimination_differential: number;
  is_user_club: boolean;
}
```

**Current client-side computations:**
- `winPct` = `wins / (wins + losses + draws)` (already computed)
- `gamesBack` = points difference from 1st place (already computed)

**Current gaps:**
- No "Your Team" summary card above the table
- User's team row has no visual highlight beyond the data
- No form dots (last 5 results) — requires match history data
- No streak display — requires match history data
- No playoff/tiebreaker explainer
- No 1st-place visual treatment

---

## What to build

### 1. `YourTeamSummary`

**New file:** `frontend/src/components/standings/YourTeamSummary.tsx`

A summary card above the standings table showing the user's team at a glance.

**Props:**
```ts
{
  rank: number;
  teamName: string;
  record: string;         // "3-3-0"
  points: number;
  elimDiff: number;
  winRate: number;         // 0.500
  gamesBack: number;       // 1.5
}
```

**Layout:**
```
YOUR TEAM          RANK       POINTS     WIN RATE     GAMES BACK     ELIM DIFF
Autopsy Comets     4th        9          .500         1.5            +1
                              3-3-0
```

**Rules:**
- "YOUR TEAM" is a `dm-kicker` label
- Team name is prominent (`text-lg`, `font-bold`)
- Stat values are large; labels are muted secondary text
- Card uses `dm-panel` with a left cyan border
- Record shown below points in smaller text

**Data derivation:** Find the user's team from `standings` where `is_user_club === true`. Rank is the 1-indexed position in the sorted standings array. Record is `W-L-D` format. Win rate and games back are already computed in the existing code.

### 2. Update `StandingsRow` highlighting

**Edit:** `frontend/src/components/LeagueContext.tsx`

Add visual states to table rows:

**Current team highlight:**
```css
border-left: 3px solid rgba(34, 211, 238, 0.45);
background: rgba(34, 211, 238, 0.045);
```

Add a small "YOU" badge next to the user's club name:
```tsx
{standing.is_user_club && <span className="dm-badge dm-badge-cyan" style={{ marginLeft: '0.5rem', fontSize: '0.6rem' }}>YOU</span>}
```

**1st place highlight:**
```css
/* rank cell for 1st place */
background: rgba(250, 204, 21, 0.18);
color: #facc15;
```

**Hover state:**
```css
.standings-row:hover {
  background: rgba(148, 163, 184, 0.04);
}
```

### 3. `FormDots`

**New file:** `frontend/src/components/standings/FormDots.tsx`

A compact last-5-results indicator.

**Props:**
```ts
{
  results: ('W' | 'L' | 'D')[];
}
```

**Layout:**
```
● ● ● ● ●
```

**Color mapping:**
| Result | Color |
| ------ | ----- |
| W | `#22c55e` (green) |
| L | `#ef4444` (red) |
| D | `#94a3b8` (slate) |

**Rules:**
- Dots are small (6–8px circles)
- Add a `title` tooltip: "Last 5: W-L-W-W-W"
- If fewer than 5 results, show only what exists
- Most recent result on the right

**Data note:** `StandingRow` does not include match history. This column requires either:
- **Option A:** Adding a `recent_results` array to `StandingRow` on the backend
- **Option B:** Fetching match history from a separate endpoint

Recommend **Option A** — it's a small addition to the standings API. If not feasible, skip this component in Phase 1 and add it when match history is available.

### 4. `StreakBadge`

**New file:** `frontend/src/components/standings/StreakBadge.tsx`

**Props:**
```ts
{
  streak: string;  // "W2", "L1", "D1"
}
```

**Layout:**
```
W2
```

**Color mapping:**
| Prefix | Color |
| ------ | ----- |
| W | `#22c55e` (green) |
| L | `#ef4444` (red) |
| D/T | `#94a3b8` (slate) |

**Same data caveat as FormDots** — requires match history that's not currently on `StandingRow`.

### 5. `StandingsExplainer`

**New file:** `frontend/src/components/standings/StandingsExplainer.tsx`

A quiet footer panel explaining playoff rules and tiebreakers.

**Props:**
```ts
{
  playoffCutoff?: number;  // e.g. 4 (top 4 make playoffs)
}
```

**Layout:**
```
TIEBREAKERS
1. Head-to-Head Record
2. Elimination Differential
3. Total Eliminations
4. Coin Flip

ELIMINATION DIFFERENTIAL
Total players eliminated minus total players lost. Higher is better.
```

**Rules:**
- Sits below the standings table
- Muted text color (`text-muted`)
- `dm-kicker` labels for section headers
- Small `dm-panel` with reduced padding
- Content is static — no dynamic data needed

### 6. Wire into `LeagueContext.tsx`

**Edit:** `frontend/src/components/LeagueContext.tsx`

Add `YourTeamSummary` above the standings table:

```tsx
{userTeamStanding && (
  <YourTeamSummary
    rank={userTeamRank}
    teamName={userTeamStanding.club_name}
    record={`${userTeamStanding.wins}-${userTeamStanding.losses}-${userTeamStanding.draws}`}
    points={userTeamStanding.points}
    elimDiff={userTeamStanding.elimination_differential}
    winRate={computeWinRate(userTeamStanding)}
    gamesBack={computeGamesBack(userTeamStanding, standings[0])}
  />
)}
```

Add `StandingsExplainer` after the table. Add row highlighting logic.

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/standings/YourTeamSummary.tsx` | Create |
| `frontend/src/components/standings/FormDots.tsx` | Create (may require backend `recent_results` field) |
| `frontend/src/components/standings/StreakBadge.tsx` | Create (may require backend `streak` field) |
| `frontend/src/components/standings/StandingsExplainer.tsx` | Create |
| `frontend/src/components/LeagueContext.tsx` | Edit — add YourTeamSummary, row highlighting, StandingsExplainer |

---

## What NOT to build

- Around the League right rail — Phase 2
- Recent result cards with tags — Phase 2
- Clickable team rows — future feature
- Season selector — future feature
- Playoff bracket visualization — future feature
