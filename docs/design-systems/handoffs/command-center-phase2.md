# Command Center Phase 2: Add Replay Identity

**Depends on:** Phase 1 complete (MatchScoreHero, FalloutGrid, AftermathActionBar exist)

**Design system reference:** `docs/design-systems/Command-Center-Design-System.md`, sections 5C–5E

---

## Goal

Add replay-flavored content between the score hero and the fallout grid so the post-match screen tells a story, not just a result.

---

## What exists after Phase 1

```
PageHeader (WAR ROOM / Match Week)
Headline
MatchScoreHero (survivors, team names, winner)
FalloutGrid (3 cards: growth, standings, recruits)
AftermathActionBar (Advance / Watch Replay)
```

---

## What to build

### 1. `ReplayTimeline`

**New file:** `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx`

A vertical event rail showing key moments from the match.

**Data source:** The `CommandCenterSimResponse` includes `dashboard.lanes` (`CommandDashboardLane[]`) with title/summary/items. Additionally, the `MatchReplayResponse` (fetched via `/api/match-replay/{match_id}`) has `proof_events` with `is_key_play` flags. For Phase 2, use the dashboard lanes as the simplest data source — they're already on the response.

**Props:**
```ts
{
  lanes: CommandDashboardLane[];   // from dashboard.lanes
}
```

**Layout:**
```
MATCH FLOW

│
● Opening Phase
│  Solstice controlled early possession.
│
● Midgame
│  Cyphers lost their backline defender.
│
● Endgame
│  Solstice snowballed and closed it out.
│
```

**Rules:**
- Vertical rail with dot markers
- Each phase gets a `dm-kicker` label
- Items within each lane are compact text
- Keep it scannable — this is a summary, not a full play-by-play

### 2. `KeyPlayersPanel`

**New file:** `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`

Shows top 3 performers from the match.

**Data source:** `MatchReplayResponse.report.top_performers` (requires fetching the replay data). The `TopPerformer` type is already in `types.ts`.

**Props:**
```ts
{
  performers: TopPerformer[];
}
```

**Layout:**
```
KEY PERFORMERS

Mika Novak
3 eliminations · 1 catch · +18 impact

Ash Zane
2 eliminations · 2 dodges · +12 impact
```

**Rules:**
- Show top 3 only
- Use impact badges (StatChip or Badge component)
- Don't turn it into a spreadsheet
- Player name is the strongest text

### 3. `TacticalSummaryCard`

**New file:** `frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx`

One-paragraph explanation of why the result happened.

**Data source:** `MatchReplayResponse.report.turning_point` provides a narrative sentence. The `evidence_lanes` provide additional tactical context.

**Props:**
```ts
{
  turningPoint: string;
  evidenceLanes?: CommandDashboardLane[];
}
```

**Layout:**
```
TACTICAL READ

Solstice controlled the opening exchange, forced Cyphers into
low-percentage throws, and converted two catch reversals into
a full backline collapse.
```

**Rules:**
- One paragraph max
- No generic sports fluff — mention mechanics (possession, catches, stamina)
- Use `dm-kicker` for the "TACTICAL READ" label
- Body text is `text-secondary` color

### 4. Update `renderPostSimMode()` composition

Insert the new components between MatchScoreHero and FalloutGrid:

```tsx
{revealStage >= 1 && <MatchScoreHero ... />}

{revealStage >= 2 && (
  <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 0.9fr', gap: '1.25rem' }}>
    <ReplayTimeline lanes={activeResult.dashboard.lanes} />
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <KeyPlayersPanel performers={replayData?.report.top_performers ?? []} />
      <TacticalSummaryCard turningPoint={replayData?.report.turning_point ?? ''} />
    </div>
  </div>
)}

{revealStage >= 3 && <FalloutGrid ... />}
```

**Data fetching note:** `KeyPlayersPanel` and `TacticalSummaryCard` need data from the match replay endpoint (`/api/match-replay/{match_id}`). You'll need to fetch this when the post-sim view mounts if a `match_id` is available. The `ReplayTimeline` can work with just the dashboard lanes from `CommandCenterSimResponse`.

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx` | Create |
| `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx` | Create |
| `frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx` | Create |
| `frontend/src/components/MatchWeek.tsx` | Edit composition + add replay data fetch |

---

## What NOT to build

- Full play-by-play event list — that's on the Match Replay screen
- Score animations — Phase 3
- Interactive timeline seeking — that's the replay viewer
