# Match Replay Phase 4: Add Tactical Depth

**Depends on:** Phase 3 complete (WinnerBanner, MatchSummaryCard, PlayerOfTheMatch, Stats tab, ReplayFooterActions exist)

**Design system reference:** `docs/design-systems/Match-Replay-Design-System.md`, sections 15–16

---

## Goal

Add the "nerdy front-office sicko" layer — shot map, event filtering, player filtering, and a full-match path overlay. This is the tactical depth that turns the replay from a sports broadcast into an analysis console.

---

## What exists after Phase 3

- Complete replay experience: scoreboard, court, rosters, controls, info panel
- Live and post-match modes with proper transitions
- Play-by-play, Key Plays, and Stats tabs in the info panel
- Winner banner, match summary, and player of the match
- Watch Again / Continue action bar

**What's missing:**
- No shot map (throw origin → target visualization)
- No way to filter events by player or type
- No full-match path overlay toggle
- No advanced stat breakdowns beyond basic counts

---

## What to build

### 1. `ShotMap` (Shots tab)

**New file:** `frontend/src/components/match-replay/ShotMap.tsx`

A court overlay showing all throw origins, targets, and outcomes.

**Props:**
```ts
{
  proofEvents: ReplayProofEvent[];
  filter: ShotMapFilter;
  onFilterChange: (filter: ShotMapFilter) => void;
  homeTeamName: string;
  awayTeamName: string;
}
```

**Filter type:**
```ts
type ShotMapFilter = {
  type: 'all' | 'throws' | 'catches' | 'eliminations';
  team: 'all' | 'home' | 'away';
  playerId?: string;
};
```

**Layout:**
```
SHOT MAP

[All] [Throws] [Catches] [Eliminations]    [All Teams ▼]

┌─────────────────────────────────────┐
│ Court diagram with markers          │
│                                     │
│  ● throw origins                    │
│  × elimination endpoints            │
│  ○ catch locations                  │
└─────────────────────────────────────┘

23 throws · 6 catches · 4 eliminations
```

**Marker types:**
| Marker | Event | Color |
| ------ | ----- | ----- |
| Filled circle | Throw origin | Orange |
| X | Elimination endpoint | Red |
| Open circle | Catch location | Cyan |
| Dashed circle | Dodge location | Purple |

**Rules:**
- Uses the same court SVG layout as `ReplayCourt` but simplified (no player tokens, just markers)
- Filter buttons at top to toggle event types
- Team filter dropdown
- Summary count below the map
- Position derivation: same formation-based mapping as `ActionPath` in Phase 2

**Aspirational note:** True spatial accuracy requires the engine to expose per-event positions. Until then, derive approximate positions from formation slots + some jitter to avoid marker overlap.

### 2. Player event filtering

**Edit:** `frontend/src/components/match-replay/ReplayInfoPanel.tsx`

Add a player filter dropdown at the top of the Play-by-Play tab:

```
[All Players ▼]
```

When a player is selected:
- Play-by-play shows only events involving that player (as thrower or target)
- Key plays tab also filters to that player
- The court highlights that player's token

**Player list derivation:** Build from unique `thrower_name` and `target_name` values in `proof_events`.

### 3. Event type filtering

**Edit:** `frontend/src/components/match-replay/ReplayInfoPanel.tsx`

Add filter chips below the player dropdown:

```
[All] [Throws] [Catches] [Dodges] [Eliminations]
```

Filters events by resolution:
| Chip | Filter logic |
| ---- | ------------ |
| Throws | All events (every proof_event is a throw resolution) |
| Catches | `resolution === 'caught'` |
| Dodges | `resolution === 'dodged'` |
| Eliminations | `resolution === 'hit'` |

### 4. Full-match path overlay toggle

**Edit:** `frontend/src/components/match-replay/ReplayCourt.tsx`

In post-match mode, add a toggle button above the court:

```
[Show All Paths]
```

When enabled:
- Render all throw paths at once using `ActionPath` components at ~15% opacity
- Key play paths at ~40% opacity
- Selected event path at full opacity
- Creates a "heat map" feel showing the full flow of the match

When disabled (default):
- Only show the current/selected event path (normal behavior)

### 5. Shots tab in ReplayInfoPanel

**Edit:** `frontend/src/components/match-replay/ReplayInfoPanel.tsx`

Add the Shots tab (only available in post-match mode):

```ts
const tabs = mode === 'postMatch'
  ? ['playByPlay', 'keyPlays', 'stats', 'shots']
  : ['playByPlay', 'keyPlays'];
```

The Shots tab renders the `ShotMap` component.

### 6. Advanced stat breakdowns

**Edit:** `frontend/src/components/match-replay/MatchSummaryCard.tsx`

Expand the Stats tab content with per-player breakdowns:

```
PLAYER STATS

Player           Elim  Catches  Dodges  Throws
Cade Kade          3      2       2       8
Vera Turner        2      3       1       7
Arc Brook          1      4       3       6
```

**Data derivation:** Count events per player from `proof_events`:

```ts
function computePlayerStats(proofEvents: ReplayProofEvent[]): PlayerMatchStats[] {
  const stats = new Map<string, PlayerMatchStats>();

  for (const event of proofEvents) {
    // Thrower stats
    const thrower = stats.get(event.thrower_id) ?? { name: event.thrower_name, ... };
    thrower.throws++;
    if (event.resolution === 'hit') thrower.eliminations++;

    // Target stats
    const target = stats.get(event.target_id) ?? { name: event.target_name, ... };
    if (event.resolution === 'caught') target.catches++;
    if (event.resolution === 'dodged') target.dodges++;

    stats.set(event.thrower_id, thrower);
    stats.set(event.target_id, target);
  }

  return [...stats.values()].sort((a, b) => b.eliminations - a.eliminations);
}
```

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/match-replay/ShotMap.tsx` | Create |
| `frontend/src/components/match-replay/ReplayInfoPanel.tsx` | Edit — add Shots tab, player filter, event type filter |
| `frontend/src/components/match-replay/ReplayCourt.tsx` | Edit — add full-match path overlay toggle |
| `frontend/src/components/match-replay/MatchSummaryCard.tsx` | Edit — add per-player stat table |

---

## What NOT to build

- Heatmap visualization (requires true spatial data from engine)
- Exportable stats / share replay — future feature
- Replay comparison (match A vs match B) — future feature
- Player tendencies / scouting report from replay data — future feature
- Animated replay GIF export — future feature
