# Command Center Phase 1: Fix the Hierarchy

## Goal

Redesign the post-sim "Aftermath" view in `MatchWeek.tsx` so the result screen has clear visual hierarchy: dominant match result up top, readable fallout in the middle, and one obvious next action at the bottom.

**Design system reference:** `docs/design-systems/Command-Center-Design-System.md`

---

## What exists today

The post-sim view lives in `renderPostSimMode()` inside `frontend/src/components/MatchWeek.tsx:215–244`. It renders five aftermath components in a staggered reveal sequence:

1. `Headline` — one-line match headline (`aftermath.headline`)
2. `MatchCard` — barebones VS layout showing club IDs and survivor counts
3. `PlayerGrowthBlock` — attribute growth deltas
4. `StandingsShift` — rank changes
5. `RecruitReactions` — prospect interest changes
6. `ActionButton` — "Advance to Next Week"

All five aftermath sub-components are in `frontend/src/components/match-week/aftermath/`. They are minimal — `dm-panel` wrappers with inline styles. They work but have no visual hierarchy.

### Data already available

The `Aftermath` interface (`frontend/src/types.ts:292–319`) provides:

```ts
{
  headline: string;
  match_card: {
    home_club_id: string;       // Note: club IDs, not names
    away_club_id: string;
    winner_club_id: string | null;
    home_survivors: number;
    away_survivors: number;
  } | null;
  player_growth_deltas: Array<{ player_id, player_name, attribute, delta }>;
  standings_shift: Array<{ club_id, club_name, old_rank, new_rank }>;
  recruit_reactions: Array<{ prospect_id, prospect_name, interest_delta, evidence }>;
}
```

The parent also has access to `CommandCenterSimResponse` which includes `dashboard.opponent_name` and the full `CommandCenterResponse` with `player_club_name`.

**Important:** `match_card` has `home_club_id` / `away_club_id` but not team names. You'll need to pass team names down from the parent context (`data.player_club_name` for the user's team, `data.plan.opponent.name` for the opponent). If the engine should provide names on `match_card` directly, flag that as a backend change.

### Shared UI components to reuse

From `frontend/src/components/ui.tsx`:

| Component     | Use for                                    |
| ------------- | ------------------------------------------ |
| `PageHeader`  | Already used for the "Aftermath" header    |
| `ActionButton`| Already used for "Advance to Next Week"    |
| `Badge`       | Small status labels                        |
| `StatChip`    | Compact stat displays                      |
| `Card`        | Panel wrapper (applies `dm-panel`)         |
| `Tile`        | Interactive panel variant                  |

### Styling approach

- Use Tailwind CSS v4 classes and existing `dm-` utility classes
- Design tokens are in `frontend/src/index.css` under `@theme`
- Key classes: `dm-panel`, `dm-kicker`, `dm-headline`, `dm-badge-cyan`, `dm-badge-orange`
- Do NOT use raw CSS custom properties like `--bg-panel` — use the Tailwind equivalents

---

## What to build

### 1. `MatchScoreHero`

**New file:** `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx`

Replaces the current `MatchCard` component. This is the most important visual on the screen.

**Props:**
```ts
{
  homeTeam: string;
  awayTeam: string;
  homeSurvivors: number;
  awaySurvivors: number;
  winnerClubId: string | null;
  homeClubId: string;
}
```

**Layout:**
```
┌────────────────────────────────────────────────────────────┐
│ SOLSTICE              8       VS       0        CYPHERS     │
│ 8 Survivors                 FINAL             0 Survivors   │
└────────────────────────────────────────────────────────────┘
```

**Rules from design system:**
- Survivor counts are enormous (`text-5xl` or larger, `font-display`, `font-black`)
- Winner side gets stronger opacity / subtle glow; loser side is subdued
- "FINAL" label sits centered between the counts
- Team names are prominent (`text-xl` or `text-2xl`, `uppercase`)
- Use `--color-dm-team-home` (warm) and `--color-dm-team-away` (cool) if those tokens exist, otherwise use red/blue accents from the design system

### 2. `FalloutGrid`

**New file:** `frontend/src/components/match-week/aftermath/FalloutGrid.tsx`

Replaces the three separate flat panels (`PlayerGrowthBlock`, `StandingsShift`, `RecruitReactions`) with a consistent card grid.

**Props:**
```ts
{
  playerGrowth: Aftermath['player_growth_deltas'];
  standingsShift: Aftermath['standings_shift'];
  recruitReactions: Aftermath['recruit_reactions'];
}
```

**Layout:**
```
FALLOUT

┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ PLAYER           │ │ LEAGUE TABLE     │ │ RECRUIT          │
│ DEVELOPMENT      │ │                  │ │ REACTIONS        │
│                  │ │ Solstice → #4    │ │                  │
│ No gains this    │ │ Cyphers → #9     │ │ No changes       │
│ week.            │ │                  │ │ reported.        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

**Rules:**
- Three equal-width cards in a row on desktop, stacked on mobile
- Each card has a `dm-kicker` label at top
- Empty states use front-office language, not debug language (e.g. "No player development changes this week" not "No attribute growth detected")
- Cards should feel like a management report, not console output

### 3. `AftermathActionBar`

**New file:** `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx`

Replaces the current centered `ActionButton` with a proper action bar anchored at the bottom of content.

**Props:**
```ts
{
  onAdvance: () => void;
  onViewReplay?: () => void;
  matchId?: string;
  isAdvancing?: boolean;
}
```

**Layout:**
```
[ Watch Replay ]                              [ Advance to Next Week → ]
```

**Rules:**
- Primary action ("Advance to Next Week") on the right, orange (`variant="primary"`)
- Secondary action ("Watch Replay") on the left, outlined or muted
- Only ONE orange button on the screen
- Action bar is visually anchored at the bottom of the content flow, not floating mid-screen
- "Watch Replay" only appears if `matchId` is available and `onViewReplay` is provided

### 4. Update `renderPostSimMode()` in `MatchWeek.tsx`

Wire the new components into the existing render flow:

```tsx
const renderPostSimMode = () => {
  const activeResult = result ?? persistedResult;
  if (!activeResult?.aftermath) return <StatusMessage>...</StatusMessage>;
  const { aftermath } = activeResult;

  return (
    <div>
      <PageHeader eyebrow="WAR ROOM" title="Match Week" description="Reviewing the weekly fallout." />

      {revealStage >= 0 && <Headline text={aftermath.headline} />}

      {revealStage >= 1 && aftermath.match_card && (
        <MatchScoreHero
          homeTeam={/* resolve name */}
          awayTeam={/* resolve name */}
          homeSurvivors={aftermath.match_card.home_survivors}
          awaySurvivors={aftermath.match_card.away_survivors}
          winnerClubId={aftermath.match_card.winner_club_id}
          homeClubId={aftermath.match_card.home_club_id}
        />
      )}

      {revealStage >= 2 && (
        <FalloutGrid
          playerGrowth={aftermath.player_growth_deltas}
          standingsShift={aftermath.standings_shift}
          recruitReactions={aftermath.recruit_reactions}
        />
      )}

      {revealStage >= 5 && (
        <AftermathActionBar onAdvance={handleAdvanceWeek} onViewReplay={...} />
      )}
    </div>
  );
};
```

**Key changes from current code:**
- `PageHeader` eyebrow changes from "Match Week" to "WAR ROOM", title stays "Match Week" (or becomes "Aftermath")
- `MatchScoreHero` replaces `AftermathMatchCard`
- `FalloutGrid` replaces three separate reveal stages (growth, standings, recruits) with one combined reveal
- `AftermathActionBar` replaces the bare `ActionButton`
- The staggered reveal can be simplified: headline → score hero → fallout grid → action bar (4 stages instead of 6)

---

## What NOT to build in this phase

- `ReplayTimeline` — Phase 2
- `KeyPlayersPanel` — Phase 2
- `TacticalSummaryCard` — Phase 2
- Score count-up animation — Phase 3
- Winner glow animation — Phase 3
- Pre-sim view changes — out of scope

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx` | Create |
| `frontend/src/components/match-week/aftermath/FalloutGrid.tsx` | Create |
| `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx` | Create |
| `frontend/src/components/MatchWeek.tsx` | Edit `renderPostSimMode()` |
| `frontend/src/components/match-week/aftermath/MatchCard.tsx` | Unused after migration — can delete or keep as fallback |

---

## Team name resolution

The `match_card` on the `Aftermath` type only has `home_club_id` and `away_club_id`, not display names. Two options:

**Option A (frontend-only):** Pass `data.player_club_name` and `data.plan.opponent.name` down from `MatchWeek` into `MatchScoreHero`. These are already available on the `CommandCenterResponse`. Determine home/away by comparing `match_card.home_club_id` against `data.player_club_id`.

**Option B (backend change):** Add `home_club_name` and `away_club_name` to the `match_card` object in the `Aftermath` response. Cleaner long-term.

Recommend **Option A** for Phase 1 since it requires no backend work.

---

## Verification

After building, run `npm run build` from `frontend/` to verify no type errors. Then launch the app (`python -m dodgeball_sim`), simulate a week, and verify:

1. Score hero is dominant — survivor counts are the largest element on screen
2. Fallout cards are in a 3-column grid, not stacked flat panels
3. Action bar has "Advance to Next Week" on the right
4. Staggered reveal still works (headline → score → fallout → actions)
5. Empty states use clean language ("No player development changes this week")
