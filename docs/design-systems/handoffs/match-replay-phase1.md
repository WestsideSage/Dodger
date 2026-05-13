# Match Replay Phase 1: Fix the Layout and Readability

**Design system reference:** `docs/design-systems/Match-Replay-Design-System.md`, sections 2, 4, 5, 9, 10, 12

---

## Goal

Restructure the match replay page so it has the correct layout: dominant scoreboard up top, team rosters on the sides, court in the center, and a tabbed info panel on the right. The current 856-line monolithic component needs to be decomposed into focused sub-components.

---

## What exists today

The match replay lives in `frontend/src/components/MatchReplay.tsx` (856 lines). It renders everything inline:

- **Scoreboard:** Inline header with team names and survivor counts
- **Court:** Full SVG court with player tokens, throw trajectories, resolution animations
- **Play-by-play:** A scrollable event list on the right
- **Controls:** Play/pause, step forward/back, speed selector, timeline scrubber

**Data:** Uses `useApiResource<MatchReplayResponse>('/api/match-replay/{match_id}')`.

**`MatchReplayResponse` type:**
```ts
{
  match_id: string;
  home_team_name: string;
  away_team_name: string;
  home_survivors: number;
  away_survivors: number;
  events: ReplayEvent[];
  proof_events: ReplayProofEvent[];
  key_play_indices: number[];
  report: {
    summary: string;
    turning_point: string;
    top_performers: TopPerformer[];
    evidence_lanes: CommandDashboardLane[];
  };
}
```

**Current layout problem:** Everything is in one giant component with no clear visual hierarchy. The court, roster, and info panel are mixed together without a proper grid structure.

---

## What to build

This phase extracts sub-components from the existing monolith. The goal is layout, not new features.

### 1. `ReplayScoreboard`

**New file:** `frontend/src/components/match-replay/ReplayScoreboard.tsx`

Extract the scoreboard from the top of `MatchReplay.tsx`.

**Props:**
```ts
{
  homeTeam: string;
  awayTeam: string;
  homeSurvivors: number;
  awaySurvivors: number;
  status: 'notStarted' | 'playing' | 'paused' | 'final';
  currentTick: number;
  winnerSide: 'home' | 'away' | null;
}
```

**Layout:**
```
LUNAR SYNDICATE       2        FINAL        6       NORTHWOOD IRONCLADS
```

**Rules:**
- Survivor counts are huge (`text-4xl` or larger, `font-display`, `font-black`)
- Center label shows current state: `Tick N` during playback, `FINAL` when done, `PAUSED` when paused
- Winner side gets subtle glow; loser is subdued (reduced opacity ~0.6)
- Team names are prominent (`text-xl`, uppercase)
- Left team uses warm accent, right team uses cool accent
- Full width, `dm-panel` background

### 2. `TeamReplayRoster`

**New file:** `frontend/src/components/match-replay/TeamReplayRoster.tsx`

Side panel showing team lineup with active/out status.

**Props:**
```ts
{
  teamName: string;
  players: Array<{
    id: string;
    name: string;
    status: 'active' | 'out';
  }>;
  side: 'left' | 'right';
  selectedPlayerId?: string;
  onSelectPlayer: (id: string) => void;
}
```

**Layout:**
```
LUNAR SYNDICATE

Priya Turner          OUT
Zara Stone            OUT
Lin Bolt              OUT
Avery Zenith          ACTIVE
Tate Keene            OUT
Nex Crane             ACTIVE
```

**Rules:**
- Left roster aligns left; right roster aligns right
- Active players are bright; out players are muted with "OUT" in red
- "ACTIVE" label in cyan/green
- Clicking a player highlights them on the court (pass selection up)
- Team name is a `dm-kicker` header
- Panel width ~240px

**Data derivation:** Build the player list from `proof_events`. Track which players are out by scanning events where `resolution` indicates elimination. The existing code already tracks this — extract the logic.

### 3. `ReplayControls`

**New file:** `frontend/src/components/match-replay/ReplayControls.tsx`

Extract playback controls from `MatchReplay.tsx`.

**Props:**
```ts
{
  isPlaying: boolean;
  currentTick: number;
  totalTicks: number;
  speed: number;
  onPlayPause: () => void;
  onStepForward: () => void;
  onStepBackward: () => void;
  onSeek: (tick: number) => void;
  onSpeedChange: (speed: number) => void;
}
```

**Layout:**
```
[◀] [▶ Play] [▶▶]    [1x ▼]
Tick 0 ━━━━━●━━━━━━━━━━━━━━━━━━ Tick 42
```

**Rules:**
- Play/pause is the primary button
- Step back/forward are secondary
- Speed dropdown: 0.5x, 1x, 2x, 4x
- Timeline scrubber shows current position in the match
- Controls sit directly below the court

### 4. `ReplayInfoPanel`

**New file:** `frontend/src/components/match-replay/ReplayInfoPanel.tsx`

The right-side panel with tabs for play-by-play and key plays.

**Props:**
```ts
{
  activeTab: 'playByPlay' | 'keyPlays';
  onTabChange: (tab: 'playByPlay' | 'keyPlays') => void;
  proofEvents: ReplayProofEvent[];
  keyPlayIndices: number[];
  currentTick: number;
  onSelectEvent: (index: number) => void;
}
```

**Layout:**
```
[ Play-by-Play ] [ Key Plays ]

TICK 07
Cade Kade sends a screamer toward Priya Turner.
The catch is fumbled and they're out.

TICK 12
Arc Brook catches a throw from Vera Turner.
```

**Rules:**
- Two tabs for Phase 1 (Stats and Shots tabs come in later phases)
- Play-by-play shows all events using `proof_events[].summary` and `.detail`
- Key plays shows only events where index is in `key_play_indices`
- Current/selected event gets a highlight border
- Clicking an event seeks to that tick
- Panel scrolls independently from the page
- Panel width ~340px

### 5. Restructure `MatchReplay.tsx` layout

**Edit:** `frontend/src/components/MatchReplay.tsx`

Restructure the component to use the new sub-components in a proper grid:

```tsx
<div>
  <PageHeader eyebrow="Match Day" title="Match Replay" />

  <ReplayScoreboard
    homeTeam={data.home_team_name}
    awayTeam={data.away_team_name}
    homeSurvivors={data.home_survivors}
    awaySurvivors={data.away_survivors}
    status={replayStatus}
    currentTick={currentTick}
    winnerSide={winnerSide}
  />

  <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr 340px', gap: '1rem' }}>
    <TeamReplayRoster side="left" teamName={data.home_team_name} players={homePlayers} ... />

    <div>
      {/* Existing SVG court — keep inline for now, extract in Phase 2 */}
      <ReplayControls ... />
    </div>

    <ReplayInfoPanel
      activeTab={infoTab}
      onTabChange={setInfoTab}
      proofEvents={data.proof_events}
      keyPlayIndices={data.key_play_indices}
      currentTick={currentTick}
      onSelectEvent={handleSeek}
    />
  </div>
</div>
```

**Key change:** The SVG court rendering stays in `MatchReplay.tsx` for now — it's deeply coupled to animation state and would be a large extraction. Phase 2 will address the court component.

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/match-replay/ReplayScoreboard.tsx` | Create |
| `frontend/src/components/match-replay/TeamReplayRoster.tsx` | Create |
| `frontend/src/components/match-replay/ReplayControls.tsx` | Create |
| `frontend/src/components/match-replay/ReplayInfoPanel.tsx` | Create |
| `frontend/src/components/MatchReplay.tsx` | Edit — restructure layout, delegate to sub-components |

---

## What NOT to build

- Extracting the SVG court into its own component — Phase 2
- PlayerToken redesign — Phase 2
- ActionPath throw/catch visualization — Phase 2
- Stats or Shots tabs — Phases 3–4
- Event marker dots on the timeline — Phase 2
- Post-match mode switching — Phase 3
