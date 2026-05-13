# League Office / Standings Design System

## 1. Design Thesis

**Standings should feel like:**

> “This is the league table, playoff race, and weekly league newspaper in one screen.”

The standings table is the factual core. It should be stable, readable, and low-drama.

> **Implementation note:** The frontend uses Tailwind CSS v4 with `@theme` tokens and `dm-` utility classes. Raw CSS custom properties shown here are for design intent — translate them to `dm-` classes or `@theme` tokens when implementing.

The **Around the League** panel is where the personality goes. That’s where blowouts, upsets, hot streaks, player spotlights, and league narratives should live.

## Core split

| Area                          | Purpose                   | Tone                     |
| ----------------------------- | ------------------------- | ------------------------ |
| **Standings Table**           | Objective league position | Clean, factual, sortable |
| **Your Team Summary**         | Immediate player context  | Focused, glanceable      |
| **Around the League**         | Recent results and drama  | Punchy, sports recap     |
| **Playoff/Tiebreaker Footer** | Rules and interpretation  | Helpful, quiet           |

---

# 2. Page Layout

## Desktop layout

```txt
┌──────────────────────────────────────────────────────────────┐
│ LEAGUE OFFICE / STANDINGS                         Season 2026 │
│ Track your team’s position, playoff picture, and season race. │
├───────────────────────────────────────┬──────────────────────┤
│ Your Team Summary                     │ Around the League    │
├───────────────────────────────────────┤                      │
│ Standings Table                       │ Recent Results       │
│                                       │ League Recap         │
│                                       │ Player Spotlight     │
├───────────────────────────────────────┤                      │
│ Playoffs / Tiebreakers / Elim Diff    │                      │
└───────────────────────────────────────┴──────────────────────┘
```

## Recommended grid

```css
.standings-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 24px;
  align-items: start;
}

.standings-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.league-rail {
  position: sticky;
  top: 24px;
}
```

The right rail being sticky is a sneaky good quality-of-life move. The standings can scroll, but the “league newspaper” stays visible.

---

# 3. Page Header

## Component

```tsx
<LeagueOfficeHeader
  eyebrow="League Office"
  title="Standings"
  subtitle="Track your team's position, playoff picture, and season race."
  season={2026}
  onSeasonChange={setSeason}
/>
```

## Layout

```txt
LEAGUE OFFICE
STANDINGS
Track your team’s position, playoff picture, and season race.

[Season 2026 v]
```

## Rules

* Season selector belongs top-right.
* Title should be prominent, but not bigger than the actual standings content.
* Keep this clean. The table and right rail are the stars.

---

# 4. Your Team Summary

This is the top summary card above the standings table.

## Component

The API provides `StandingRow` with `wins`, `losses`, `draws`, `points`, `elimination_differential`, and `is_user_club`. Additional display values must be computed client-side:

```tsx
<YourTeamSummary
  rank={4}                  // derived from sort position
  teamName="Autopsy Comets" // from standing.club_name
  record="3-3"              // derived from W-L-D
  points={9}                // from standing.points
  elimDiff={+1}             // from standing.elimination_differential
/>
```

> **Aspirational fields:** `winRate`, `gamesBack`, and `streak` are useful display values but must be computed client-side — they are not on the `StandingRow` API response.

## Visual layout

```txt
YOUR TEAM        POINTS       WIN RATE       GAMES BACK       STREAK
4th              9            .500           1.5 from 1st     W1
Autopsy Comets   3-3 record   50%            —                1 Win
```

## Rules

* This card answers: **Where am I right now?**
* The current team should also be highlighted in the standings table.
* Use cyan for the user tag, not a huge glow.
* Streak can use green/red, but keep it contained.

## Suggested tags

```txt
YOU
1ST
PLAYOFF
HUNT
ELIM
```

---

# 5. Standings Table

## Component

```tsx
<StandingsTable
  teams={teams}
  currentTeamId={currentTeamId}
  sortBy="points"
  playoffCutoffRank={4}
/>
```

## Available columns from `StandingRow`

```txt
Rank | Club | W | L | D | Pts | Elim Diff
```

| Column        | Source                               |
| ------------- | ------------------------------------ |
| **Rank**      | Derived from sort position           |
| **Club**      | `club_name` + `is_user_club` badge   |
| **W/L/D**     | `wins`, `losses`, `draws`            |
| **Pts**       | `points`                             |
| **Elim Diff** | `elimination_differential`           |

## Aspirational columns (require client-side computation or engine changes)

| Column     | Derivation needed                                |
| ---------- | ------------------------------------------------ |
| **Win %**  | `wins / (wins + losses + draws)`                 |
| **GB**     | Points gap from 1st-place team                   |
| **Strk**   | Requires match history not on `StandingRow`      |
| **Last 5** | Requires match history not on `StandingRow`      |

## Table row visual states

| State            | Visual Treatment                             |
| ---------------- | -------------------------------------------- |
| **1st Place**    | Subtle gold rank cell                        |
| **Current Team** | Cyan left accent + low-opacity row highlight |
| **Playoff Spot** | Optional green dot or side marker            |
| **In the Hunt**  | Blue/cyan small marker                       |
| **Eliminated**   | Muted row opacity, red marker                |
| **Hovered**      | Slight panel lift or border brighten         |

## Example row

```txt
4  [Logo] Autopsy Comets  YOU   3  3  0  9  .500  1.5  W1  ● ● ● ● ●  +1
```

## CSS row rules

```css
.standings-row {
  display: grid;
  grid-template-columns: 52px minmax(220px, 1fr) 56px 56px 56px 72px 80px 72px 80px 112px 96px;
  align-items: center;
  min-height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-muted);
  background: var(--bg-panel);
}

.standings-row[data-current-team="true"] {
  border-left: 3px solid var(--accent-cyan);
  background: rgba(34, 211, 238, 0.07);
}

.standings-row[data-rank="1"] .rank-cell {
  background: rgba(250, 204, 21, 0.18);
  color: #facc15;
}
```

---

# 6. Last 5 Form Dots

This is a small thing, but it makes the table feel alive.

## Component

```tsx
<FormDots results={["W", "L", "W", "W", "W"]} />
```

## Visual

```txt
● ● ● ● ●
G R G G G
```

## Rules

* Green = win
* Red = loss
* Gray = tie/no result
* Dots should be small, not candy-coated chaos.
* Add tooltip on hover:

```txt
Last 5: W-L-W-W-W
```

---

# 7. Streak Display

## Component

```tsx
<StreakBadge streak="W2" />
```

## Rules

| Streak    | Color |
| --------- | ----- |
| W1/W2/W3+ | Green |
| L1/L2/L3+ | Red   |
| T         | Slate |

Use compact badges:

```txt
W2
L1
```

Do not write full sentences in the table. Save that for the right rail.

---

# 8. Around the League Panel

This is where the page gets fun.

## Component

```tsx
<AroundLeaguePanel>
  <RecentResults />
  <LeagueRecap />
  <PlayerSpotlight />
  <ViewScheduleButton />
</AroundLeaguePanel>
```

## Structure

```txt
AROUND THE LEAGUE

RECENT RESULTS
Week 9
Solstice Flare 0–6 Autopsy Comets      BLOWOUT
Autopsy Comets dominate with a clean sweep.

Week 8
Northwood Ironclads 0–4 Solstice Flare      SHUTOUT
Solstice Flare shuts out Northwood on the road.

LEAGUE RECAP
Biggest Blowout
Autopsy Comets 6–0 vs Solstice Flare

Best Defense
Aurora Sentinels
Only 2.0 GA per game

PLAYER SPOTLIGHT
Mika Thorn
18 eliminations · 6 assists · 2 GA
Key playmaker in Autopsy’s Week 9 shutout.

[View Full Schedule]
```

## Big rule

The right rail should be **narrative**, but not goofy.

No fake ESPN screaming unless the game’s tone wants that. Think: compact sports-page copy.

---

# 9. Recent Results System

## Component

```tsx
<RecentResultCard
  week={9}
  homeTeam="Solstice Flare"
  awayTeam="Autopsy Comets"
  homeSurvivors={0}
  awaySurvivors={6}
  winner="away"
  tag="blowout"
  recap="Autopsy Comets dominate with a clean sweep."
/>
```

> **Note:** The numbers (0, 6) are survivor counts, not traditional scores.

## Result card layout

```txt
WEEK 9                         BLOWOUT
Solstice Flare      0 - 6      Autopsy Comets
Winner: Autopsy Comets

Autopsy Comets dominate with a clean sweep.
```

## Result tag types

| Tag                 | Trigger                                     | Tone       |
| ------------------- | ------------------------------------------- | ---------- |
| **Blowout**         | Margin ≥ 5                                  | Dominant   |
| **Shutout**         | Losing team score = 0                       | Defensive  |
| **Statement Win**   | Beat a top-ranked/good team by solid margin | Respectful |
| **Upset**           | Lower-ranked team beats higher-ranked team  | Surprising |
| **Comeback**        | Winner trailed late                         | Dramatic   |
| **Clutch Finish**   | Margin ≤ 1                                  | Tense      |
| **Collapse**        | Favorite loses after lead                   | Critical   |
| **Streak Extender** | Team extends W streak                       | Momentum   |
| **Skid Continues**  | Team extends L streak                       | Negative   |
| **Clean Sweep**     | Perfect/no survivors lost, if applicable    | Dominant   |

## Tag visual tokens

```ts
const resultTagStyles = {
  blowout: {
    label: "Blowout",
    color: "#a78bfa",
    bg: "rgba(167, 139, 250, 0.10)",
    border: "rgba(167, 139, 250, 0.35)",
  },
  shutout: {
    label: "Shutout",
    color: "#22d3ee",
    bg: "rgba(34, 211, 238, 0.10)",
    border: "rgba(34, 211, 238, 0.35)",
  },
  statementWin: {
    label: "Statement Win",
    color: "#22c55e",
    bg: "rgba(34, 197, 94, 0.10)",
    border: "rgba(34, 197, 94, 0.35)",
  },
  upset: {
    label: "Upset",
    color: "#facc15",
    bg: "rgba(250, 204, 21, 0.10)",
    border: "rgba(250, 204, 21, 0.35)",
  },
  comeback: {
    label: "Comeback",
    color: "#38bdf8",
    bg: "rgba(56, 189, 248, 0.10)",
    border: "rgba(56, 189, 248, 0.35)",
  },
  clutchFinish: {
    label: "Clutch Finish",
    color: "#fb923c",
    bg: "rgba(251, 146, 60, 0.10)",
    border: "rgba(251, 146, 60, 0.35)",
  },
  collapse: {
    label: "Collapse",
    color: "#ef4444",
    bg: "rgba(239, 68, 68, 0.10)",
    border: "rgba(239, 68, 68, 0.35)",
  },
};
```

---

# 10. Recap Generation Rules

This can be implemented with simple deterministic logic first. No need for fancy AI text generation yet.

## Inputs

> **Note:** This type is aspirational — it extends the shipped `MatchResult` with recap-specific fields. The engine's `MatchResult` uses `winner_team_id`, `home_survivors`, and `away_survivors`.

```ts
type RecapMatchResult = {
  id: string;
  week: number;
  homeTeamId: string;
  awayTeamId: string;
  homeSurvivors: number;
  awaySurvivors: number;
  winnerTeamId: string;
  homeRankBefore?: number;    // aspirational: not on current API
  awayRankBefore?: number;    // aspirational: not on current API
};
```

## Tag resolver

```ts
function getResultTag(match: RecapMatchResult): ResultTag {
  const margin = Math.abs(match.homeSurvivors - match.awaySurvivors);
  const loserSurvivors = Math.min(match.homeSurvivors, match.awaySurvivors);

  if (loserSurvivors === 0 && margin >= 5) return "blowout";
  if (loserSurvivors === 0) return "shutout";
  if (margin <= 1) return "clutchFinish";

  const winnerRank =
    match.winnerTeamId === match.homeTeamId
      ? match.homeRankBefore
      : match.awayRankBefore;

  const loserRank =
    match.winnerTeamId === match.homeTeamId
      ? match.awayRankBefore
      : match.homeRankBefore;

  if (winnerRank && loserRank && winnerRank > loserRank + 2) {
    return "upset";
  }

  if (margin >= 4) return "statementWin";

  return "standard";
}
```

## Recap sentence resolver

```ts
function getResultRecap(match: RecapMatchResult, tag: ResultTag): string {
  const winner = getTeamName(match.winnerTeamId);
  const loser = getLoserTeamName(match);

  switch (tag) {
    case "blowout":
      return `${winner} dominate ${loser} in a one-sided result.`;
    case "shutout":
      return `${winner} shut out ${loser} with a disciplined defensive showing.`;
    case "statementWin":
      return `${winner} earn a convincing win and strengthen their league position.`;
    case "upset":
      return `${winner} stun ${loser} and shake up the standings.`;
    case "comeback":
      return `${winner} rally late to steal the result.`;
    case "clutchFinish":
      return `${winner} edge ${loser} in a tight finish.`;
    default:
      return `${winner} handle business against ${loser}.`;
  }
}
```

Tiny note: for final copy, you may want singular/plural grammar helpers. “Autopsy Comets dominate” sounds natural for team plural names, but “Solstice Flare dominate” might be weird depending on team-name style. You can avoid that by using neutral phrasing:

```txt
A dominant showing from Autopsy Comets.
A clean shutout win for Solstice Flare.
```

Less grammar risk. More robust. Boring? A little. Stable? Very.

---

# 11. League Recap Section

This sits under Recent Results in the right rail.

## Component

```tsx
<LeagueRecap
  items={[
    {
      label: "Biggest Blowout",
      teamName: "Autopsy Comets",
      value: "6–0 vs Solstice Flare",
      icon: "zap",
      type: "dominance"
    },
    {
      label: "Best Defense",
      teamName: "Aurora Sentinels",
      value: "Only 2.0 GA per game",
      icon: "shield",
      type: "defense"
    }
  ]}
/>
```

## Recommended recap items

| Item                      | Calculation                             |
| ------------------------- | --------------------------------------- |
| **Biggest Blowout**       | Largest margin in recent results        |
| **Best Defense**          | Lowest average points/survivors allowed |
| **Hottest Team**          | Longest current win streak              |
| **Coldest Team**          | Longest current losing streak           |
| **Most Dangerous Attack** | Highest eliminations/points for         |
| **Tightest Race**         | Closest points gap near playoff cutoff  |

## Visual

```txt
LEAGUE RECAP

⚡ Biggest Blowout
Autopsy Comets
6–0 vs Solstice Flare

🛡 Best Defense
Aurora Sentinels
Only 2.0 GA per game
```

Use icons sparingly. Two or three recap items is enough. Don’t turn the panel into a slot machine.

---

# 12. Player Spotlight

This is optional but very good.

## Component

```tsx
<PlayerSpotlight
  playerName="Mika Thorn"
  teamName="Autopsy Comets"
  archetype="Playmaker"
  age={31}
  stats={{
    eliminations: 18,
    assists: 6,
    catches: 2
  }}
  note="Key playmaker in Autopsy's Week 9 shutout."
/>
```

## Visual

```txt
PLAYER SPOTLIGHT

Mika Thorn
Playmaker · Age 31

18 Eliminations
6 Assists
2 Catches

Key playmaker in Autopsy’s Week 9 shutout.
```

## Rules

* Spotlight should be earned by performance.
* Do not show a portrait unless your game has consistent player portraits.
* A silhouette/avatar/team icon is fine.
* If no clear player popped off, hide the section or show “No standout performance this week.”

## Spotlight resolver

```ts
function getPlayerSpotlight(players: PlayerWeekStats[]) {
  return players
    .map(player => ({
      ...player,
      score:
        player.eliminations * 3 +
        player.catches * 2 +
        player.assists * 1.5 +
        player.clutchPlays * 4
    }))
    .sort((a, b) => b.score - a.score)[0];
}
```

---

# 13. Playoff Footer / Explainer Panel

This section is good because standings often need interpretation.

## Component

```tsx
<StandingsExplainer
  playoffRules={[
    "Clinched Playoff Spot",
    "In The Hunt",
    "Eliminated"
  ]}
  tiebreakers={[
    "Head-to-Head Record",
    "Elimination Differential",
    "Total Eliminations",
    "Coin Flip"
  ]}
  eliminationDifferentialDescription="Total players eliminated minus total players lost. Higher is better."
/>
```

## Layout

```txt
PLAYOFFS
■ Clinched Playoff Spot
■ In The Hunt
■ Eliminated

TIEBREAKERS
1. Head-to-Head Record
2. Elimination Differential
3. Total Eliminations
4. Coin Flip

ELIMINATION DIFFERENTIAL
Total players eliminated minus total players lost.
Higher is better.
```

## Rules

* Keep this at the bottom.
* Use quiet color.
* This is reference material, not the main show.

---

# 14. Color System

Use restrained colors. The standings page should not be louder than Roster Lab.

```css
:root {
  --standings-rank-first: #facc15;
  --standings-current-team: #22d3ee;

  --form-win: #22c55e;
  --form-loss: #ef4444;
  --form-tie: #94a3b8;

  --streak-win: #22c55e;
  --streak-loss: #ef4444;

  --playoff-clinched: #22c55e;
  --playoff-hunt: #0ea5e9;
  --playoff-eliminated: #ef4444;

  --result-blowout: #a78bfa;
  --result-shutout: #22d3ee;
  --result-upset: #facc15;
  --result-clutch: #fb923c;
  --result-collapse: #ef4444;
}
```

## Color rules

* Cyan = current user/team context.
* Gold = 1st place or major achievement.
* Green = wins, playoff-clinched, positive streaks.
* Red = losses, eliminated, negative streaks.
* Purple/orange/yellow = recap tags only.

---

# 15. Data Models (Shipped Types)

> The shipped type is in `frontend/src/types.ts`. Design work should use these fields.

## StandingRow (from API)

```ts
export interface StandingRow {
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

> **Aspirational fields:** `streak`, `lastFive`, `winRate`, `gamesBack`, `eliminationsFor`, `eliminationsAgainst`, and `playoffStatus` are not currently on the API response. They would need to be either computed client-side from match history or added as engine fields.

## Recent result (aspirational display type)

```ts
export type RecentResult = {
  id: string;
  week: number;

  homeTeamId: string;
  awayTeamId: string;
  homeTeamName: string;
  awayTeamName: string;
  homeSurvivors: number;
  awaySurvivors: number;

  winnerTeamId: string;

  tag?:
    | "blowout"
    | "shutout"
    | "statementWin"
    | "upset"
    | "clutchFinish"
    | "standard";

  recap: string;
};
```

## League recap item

```ts
export type LeagueRecapItem = {
  id: string;
  label: string;
  teamName: string;
  value: string;
  type:
    | "dominance"
    | "defense"
    | "attack"
    | "hot"
    | "cold"
    | "race";
};
```

## Player spotlight

```ts
export type PlayerSpotlight = {
  playerId: string;
  playerName: string;
  teamName: string;
  archetype?: string;
  age?: number;

  stats: {
    eliminations?: number;
    assists?: number;
    catches?: number;
    dodges?: number;
    clutchPlays?: number;
  };

  note: string;
};
```

---

# 16. Component Tree

```tsx
<StandingsScreen>
  <AppSidebar activeRoute="standings" />

  <MainContent>
    <LeagueOfficeHeader
      eyebrow="League Office"
      title="Standings"
      subtitle="Track your team's position, playoff picture, and season race."
      season={2026}
    />

    <StandingsLayout>
      <StandingsMain>
        <YourTeamSummary />

        <StandingsTable>
          <StandingsTableHeader />
          {teams.map(team => (
            <StandingsRow
              key={team.teamId}
              team={team}
              isCurrentTeam={team.teamId === currentTeamId}
            />
          ))}
        </StandingsTable>

        <StandingsExplainer />
      </StandingsMain>

      <AroundLeaguePanel>
        <RecentResultsList />
        <LeagueRecap />
        <PlayerSpotlight />
        <ViewFullScheduleButton />
      </AroundLeaguePanel>
    </StandingsLayout>
  </MainContent>
</StandingsScreen>
```

---

# 17. Implementation Priority

## Phase 1: Make standings clearer

Build:

1. `YourTeamSummary`
2. `StandingsRow` with current-team highlight
3. `FormDots`
4. `StreakBadge`
5. `StandingsExplainer`

This gives the page strong readability.

## Phase 2: Make Around the League useful

Build:

1. `RecentResultCard`
2. `ResultTagBadge`
3. Deterministic recap generation
4. `ViewFullScheduleButton`

This turns the boring right rail into a sports recap panel.

## Phase 3: Add league texture

Build:

1. `LeagueRecap`
2. `PlayerSpotlight`
3. Recap stat resolvers
4. Optional clickable team/player links

This makes the league feel alive.

---

# 18. Hard UX Rules

## Do

* Keep the standings table boring **in a good way**.
* Put narrative spice in the right rail.
* Highlight the user’s team clearly.
* Show recent form with dots.
* Explain tiebreakers and elimination differential.
* Use recap tags only when deserved.
* Keep right rail copy short.

## Do Not

* Turn every result into a dramatic headline.
* Make the standings table visually chaotic.
* Use five different colors in one row.
* Hide playoff/tiebreaker logic.
* Make the right rail taller than the actual useful content unless needed.
* Use player portraits unless the whole game supports them consistently.

# Core Rule

The standings page should be:

> **League truth on the left, league drama on the right.**

That’s the final form. Clean table, spicy sidebar, no spreadsheet depression.
