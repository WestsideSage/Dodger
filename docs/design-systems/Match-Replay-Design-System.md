# Match Replay Design System

## 1. Design Thesis

**Match Replay should feel like:**

> “A broadcast-quality tactical replay console for a dodgeball simulation.”

The player should be able to watch casually like a sports broadcast, but also pause and inspect the match like a nerdy little front-office sicko. Respectfully, that is the target audience. Us.

> **Implementation note:** The frontend uses Tailwind CSS v4 with `@theme` tokens and `dm-` utility classes. Raw CSS custom properties shown here are for design intent — translate them to `dm-` classes or `@theme` tokens when implementing.
>
> **Terminology:** Dodgeball matches are decided by survivors, not traditional scores. The numbers shown in the scoreboard represent `home_survivors` and `away_survivors`. The match runs in discrete ticks, not real-time minutes.

The page needs to answer:

1. **What is the score?**
2. **Who is alive/out?**
3. **What is happening right now?**
4. **Who made the key plays?**
5. **How did the match flow tactically?**
6. **Why did one team win?**

---

# 2. Core Page Structure

## Recommended Desktop Layout

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│ MATCH DAY / MATCH REPLAY                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Scoreboard Header                                                           │
├──────────────┬──────────────────────────────────────┬──────────────────────┤
│ Left Roster  │ Court Replay                         │ Right Replay Panel   │
│ Team A       │ Player positions / ball paths        │ Play-by-play / stats │
│              │ Timeline controls                    │ Key plays / summary  │
├──────────────┴──────────────────────────────────────┴──────────────────────┤
│ Replay Timeline / Controls / Event Legend                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

The big win from the redesign is that the court gets to breathe. The roster context moves to the sides, and the replay information moves to the right rail.

---

# 3. Core Mental Model

The screen should have **two major modes**.

## A. Live Replay Mode

Used while the match is being played/watched.

Priorities:

1. Current score
2. Current tick/time
3. Active players
4. Current ball/action path
5. Current play-by-play event
6. Minimal trails

This mode should be clean and watchable.

## B. Post-Match Analysis Mode

Used after the match ends.

Priorities:

1. Final score
2. Winner
3. Key plays
4. Full tactical pathing
5. Match summary
6. Player of the match
7. Team stats

This mode can be busier because the player is analyzing, not watching live.

```ts
type ReplayMode = "live" | "postMatch";
```

---

# 4. Layout Grid

## Main layout

```css
.match-replay-layout {
  display: grid;
  grid-template-columns: 260px minmax(640px, 1fr) 360px;
  gap: 16px;
  align-items: stretch;
}
```

## Screen content

```css
.match-replay-main {
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px 28px 32px;
}
```

## Responsive behavior

At smaller widths:

```txt
Scoreboard
Court
Controls
Right Panel
Team Rosters
```

Mobile is not the main target here, but the layout should not explode.

---

# 5. Scoreboard Header

## Purpose

The scoreboard is the single most important global element.

```tsx
<ReplayScoreboard
  homeTeam="Lunar Syndicate"
  awayTeam="Northwood Ironclads"
  homeSurvivors={2}
  awaySurvivors={6}
  week={9}
  status="final"
  winnerTeamId="northwood"
/>
```

> **Note:** The numbers (2, 6) are survivor counts, not goals or points. The team with more survivors at match end wins.

## Visual structure

```txt
LUNAR SYNDICATE       2        FINAL        6       NORTHWOOD IRONCLADS
3-4 · 5th                                           4-2 · 2nd
```

## States

| State     | Center Label       |
| --------- | ------------------ |
| Pre-match | `Tick 0`           |
| Live      | `Tick 14`          |
| Final     | `FINAL`            |
| Paused    | `PAUSED`           |

## Rules

* Score should be huge.
* Winner gets subtle glow or accent.
* Loser remains readable but subdued.
* Team colors should map consistently: left/orange, right/cyan.
* Do not bury `FINAL`; it should feel official.

---

# 6. Court Replay Component

## Component

```tsx
<ReplayCourt
  leftTeam={leftTeam}
  rightTeam={rightTeam}
  players={visiblePlayers}
  ball={ballState}
  events={visibleEvents}
  mode={replayMode}
  selectedEventId={selectedEventId}
/>
```

## Court layout

```txt
┌──────────────────────────────────────────────┐
│ LEFT TEAM                 RIGHT TEAM         │
│                                              │
│  Player lanes              Player lanes      │
│                                              │
│              center line / neutral zone      │
│                                              │
│  Player lanes              Player lanes      │
└──────────────────────────────────────────────┘
```

## Court visual rules

* Left half uses warm/orange tint.
* Right half uses cool/cyan tint.
* Center line is clear but not screaming.
* Center circle/neutral zone should be subtle.
* Court border should have a premium frame treatment.
* Court should be the largest single object on the page.

---

# 7. Player Positioning System

This is the part you specifically noticed: the old player lineup felt awkward.

## New rule

> **Aspirational:** The engine does not currently expose per-player court positions or lane assignments. The lane system below is a design target for when positional data becomes available. Until then, use a simple two-row formation based on team roster order.

Players should align into **role-based lanes**, not arbitrary circles.

### Recommended court lanes per side

```txt
Backline     Midline      Frontline

Top lane
Center lane
Bottom lane
```

Each team gets mirrored lane slots.

```ts
type CourtLane =
  | "backTop"
  | "backCenter"
  | "backBottom"
  | "midTop"
  | "midCenter"
  | "midBottom"
  | "frontTop"
  | "frontCenter"
  | "frontBottom";
```

## Positioning logic

```ts
type CourtPosition = {
  x: number;
  y: number;
  lane: CourtLane;
  side: "left" | "right";
};
```

## Suggested default slot map

For six players per side:

```ts
const leftSixPlayerFormation = [
  "frontTop",
  "frontBottom",
  "midTop",
  "midBottom",
  "backTop",
  "backBottom",
];

const rightSixPlayerFormation = [
  "frontTop",
  "frontBottom",
  "midTop",
  "midBottom",
  "backTop",
  "backBottom",
];
```

## Visual result

Players no longer look like they were evenly sprinkled on a PowerPoint slide. They look like they are occupying tactical space.

Big upgrade.

---

# 8. Player Tokens on Court

## Component

```tsx
<PlayerToken
  player={player}
  status="active"
  teamSide="left"
  isBallCarrier={false}
  isTargeted={true}
  isSelected={false}
/>
```

## Token states

| State          | Visual Treatment                 |
| -------------- | -------------------------------- |
| Active         | Solid ring, readable name/number |
| Ball carrier   | Strong glow + small ball marker  |
| Targeted       | Pulsing outline                  |
| Recently acted | Brief highlight                  |
| Out            | X marker / faded token           |
| Substituted    | Muted icon                       |
| Selected       | Brighter border                  |
| Injured        | Red warning marker               |

## Token label

Use either:

```txt
03
BROOK
```

or:

```txt
BROOK
```

For the court itself, I’d recommend **short name or number only** to reduce clutter.

The side roster can carry full identity.

---

# 9. Side Roster Panels

The roster panels are one of the biggest improvements.

## Component

```tsx
<TeamReplayRoster
  team={team}
  players={players}
  side="left"
  selectedPlayerId={selectedPlayerId}
  onSelectPlayer={setSelectedPlayerId}
/>
```

## Layout

```txt
LUNAR SYNDICATE

11 Priya Turner      Captain · Catcher       OUT
27 Zara Stone        Dodge Specialist        OUT
18 Lin Bolt          Power Thrower           OUT
09 Avery Zenith      Playmaker               ACTIVE
23 Tate Keene        Utility                 OUT
04 Nex Crane         Substitute              ACTIVE
```

## Status labels

| Status       | Label  | Color       |
| ------------ | ------ | ----------- |
| Active       | ACTIVE | Cyan/green  |
| Out          | OUT    | Red/muted   |
| Benched/Sub  | SUB    | Slate       |
| Injured      | INJ    | Red         |
| Captain      | C      | Gold        |
| Vice Captain | VC     | Blue/purple |

## Rules

* Left roster aligns with left team.
* Right roster aligns with right team.
* Active players should be easy to scan.
* Out players should fade, but remain readable.
* Clicking a player should highlight them on the court and filter their events.

---

# 10. Replay Timeline Controls

## Component

```tsx
<ReplayControls
  isPlaying={isPlaying}
  currentTime={currentTime}
  duration={duration}
  speed={speed}
  events={events}
  onPlayPause={togglePlay}
  onSeek={seekToTime}
  onStepForward={stepForward}
  onStepBackward={stepBackward}
/>
```

## Layout

```txt
[Back] [Play/Pause] [Forward] [1x v]
00:00 ━━━━━●━━━━━━━━━━━━━━━━━━━━ 20:00
      |    |      |        |
    throw catch  out     special
```

## Controls

| Control           | Purpose               |
| ----------------- | --------------------- |
| Back tick         | Step backward         |
| Play/Pause        | Watch replay          |
| Forward tick      | Step forward          |
| Speed dropdown    | 0.5x / 1x / 2x / 4x   |
| Timeline scrubber | Jump through match    |
| Event markers     | Show important events |

## Event marker colors

| Event            | Color  |
| ---------------- | ------ |
| Throw            | Orange |
| Catch            | Cyan   |
| Dodge            | Purple |
| Out              | Red    |
| Special / Clutch | Gold   |
| Substitution     | Slate  |

## Rule

During live replay, timeline should show only major event markers.
During post-match analysis, it can show more detail.

---

# 11. Event Path Visualization

This is where you must avoid “Tron spaghetti.”

## Live Replay Path Rules

Show only:

* Current throw path
* Current dodge movement
* Current catch moment
* Last 1–2 recent trails

```ts
const liveTrailWindow = 2;
```

## Post-Match Path Rules

Show:

* Key play paths
* Selected event path
* Final sequence path
* Optional full-match overlay toggle

```tsx
<PathLayer
  mode="postMatch"
  visibility="keyPlaysOnly"
/>
```

## Path types

| Path Type   | Visual             |
| ----------- | ------------------ |
| Throw       | Orange line        |
| Catch       | Cyan line          |
| Dodge       | Purple dashed line |
| Elimination | Red endpoint / X   |
| Assist      | Thin support line  |
| Clutch      | Gold highlight     |

## Path component

```tsx
<ActionPath
  type="throw"
  from={sourcePosition}
  to={targetPosition}
  result="caught"
  isKeyPlay={true}
/>
```

---

# 12. Right Replay Panel

This panel is the replay brain.

## Component

```tsx
<ReplayInfoPanel
  activeTab={activeTab}
  events={events}
  keyPlays={keyPlays}
  matchStats={matchStats}
  selectedEventId={selectedEventId}
/>
```

## Tabs

```txt
Play-by-Play | Key Plays | Stats | Shots
```

## Tab purposes

| Tab          | Purpose                |
| ------------ | ---------------------- |
| Play-by-Play | Full event log         |
| Key Plays    | Important moments only |
| Stats        | Team/player summary    |
| Shots        | Throw/catch/dodge map  |

This is excellent because it supports both casual and deep viewing.

---

# 13. Play-by-Play Tab

## Component

```tsx
<PlayByPlayList
  events={events}
  selectedEventId={selectedEventId}
  onSelectEvent={setSelectedEventId}
/>
```

## Event card layout

```txt
TICK 07
Cade Kade sends a screamer toward Priya Turner.
The catch is fumbled and they're out.
```

## Rules

* Most recent/current event should highlight.
* Clicking an event seeks to that tick.
* Use event icons/colors.
* Keep each event compact.
* Long events can wrap, but avoid giant cards.

## Event type display

The engine's `event_type` field uses values like `"throw_resolution"`. Map these to display labels:

| Engine `event_type`  | Display Label |
| -------------------- | ------------- |
| `throw_resolution`   | Throw         |
| (resolution=caught)  | Catch         |
| (resolution=dodged)  | Dodge         |
| (resolution=hit)     | Elimination   |

Use `ReplayProofEvent.resolution` and `proof_tags` to determine the display category.

---

# 14. Key Plays Tab

This should be the default tab after match end.

## Component

```tsx
<KeyPlaysList
  keyPlays={keyPlays}
  onSelectPlay={setSelectedEventId}
/>
```

## Key play examples

```txt
19:48 Cade Kade eliminates Priya Turner
18:05 Lin Bolt eliminates Sora Hale
16:47 Arc Brook catches a throw from Vera Turner
12:10 Avery Zenith dodges Dex Vale’s throw
00:00 Final whistle — Northwood wins 6–2
```

## Key play resolver

The `ReplayProofEvent` type already has an `is_key_play` boolean from the engine:

```ts
function isKeyPlay(event: ReplayProofEvent) {
  return event.is_key_play;
}
```

## Rule

Key Plays should be a curated digest, not the whole event log wearing a fake mustache.

---

# 15. Stats Tab

## Component

```tsx
<ReplayStatsPanel
  teamStats={teamStats}
  playerStats={playerStats}
/>
```

## Team stat cards

```txt
MATCH SUMMARY

             Lunar    Northwood
Eliminations   2         6
Catches        6         11
Dodges         8         12
Throws         28        34
Accuracy       46%       61%
Possession     47%       53%
```

## Rules

* Use side-by-side comparison.
* Winner side gets subtle emphasis.
* Do not make this a giant spreadsheet.
* Show only the stats that explain match flow.

Recommended stats:

* Eliminations
* Catches
* Dodges
* Throws
* Accuracy
* Possession time
* Clutch plays
* Turnovers/fumbles, if relevant

---

# 16. Shots Tab

> **Aspirational:** This requires spatial position data from the engine, which is not currently available. The tab architecture supports it for future implementation.

## Component

```tsx
<ShotMap
  throws={throws}
  catches={catches}
  eliminations={eliminations}
/>
```

## Purpose

Shows:

* Throw origins
* Target zones
* Catch success
* Dodge success
* Eliminating throws

## Filters

```txt
[All] [Throws] [Catches] [Outs] [Player v] [Team v]
```

This is the nerd panel. Not required for MVP, but very spicy later.

---

# 17. Match Start State

The match start should feel calm and anticipatory.

## Layout rules

At `currentTime = 0`:

* Score is 0–0
* Court shows starting formations
* Play-by-play shows empty state
* Match info panel is visible
* Controls say `Play`
* Event paths hidden

## Empty state copy

```txt
Match has not started yet.
Press Play to begin the replay.
```

## Component state

```tsx
<ReplayEmptyState
  title="Match has not started yet."
  body="Press Play to begin the replay."
/>
```

This is better than a blank play-by-play panel.

---

# 18. Match End State

The end state should feel like payoff.

## Layout rules

At final whistle:

* Scoreboard shows `FINAL`
* Winner banner appears subtly
* Court shows final positions/out states
* Key Plays tab becomes default
* Match Summary card appears
* Player of the Match appears
* Continue button becomes available

## End-state layout

```txt
NORTHWOOD IRONCLADS WIN

Final Score
Lunar Syndicate 2 — 6 Northwood Ironclads

Key Plays
Match Summary
Player of the Match

[Continue]
```

## Winner banner

```tsx
<WinnerBanner teamName="Northwood Ironclads" />
```

Visual rule:

* Full-width, subtle, not a giant modal.
* The page should still be usable.

---

# 19. Match Summary Card

## Component

```tsx
<MatchSummaryCard
  leftTeam="Lunar Syndicate"
  rightTeam="Northwood Ironclads"
  leftStats={leftStats}
  rightStats={rightStats}
  winner="right"
/>
```

## Layout

```txt
MATCH SUMMARY

                 Lunar    Northwood
Eliminations       2          6
Catches            6         11
Dodges             8         12
Throws            28         34
Accuracy          46%        61%
Possession        47%        53%
```

## Interpretation line

Optional but good:

```txt
Northwood controlled the catch game and converted possession into steady eliminations.
```

This gives the sim a “why.”

---

# 20. Player of the Match

## Component

```tsx
<PlayerOfTheMatch
  playerName="Cade Kade"
  teamName="Northwood Ironclads"
  statline="3 eliminations · 2 catches · 2 dodges"
  impactScore={91}
/>
```

## Layout

```txt
PLAYER OF THE MATCH

Cade Kade
Northwood Ironclads

3 Eliminations
2 Catches
2 Dodges
Impact 91
```

## Resolver

```ts
function calculateImpactScore(stats: PlayerMatchStats) {
  return (
    stats.eliminations * 12 +
    stats.catches * 10 +
    stats.dodges * 4 +
    stats.assists * 5 +
    stats.clutchPlays * 15 -
    stats.fumbles * 8 -
    stats.timesOut * 10
  );
}
```

## Rule

Player of the Match should not always be top eliminations. Catches, clutch plays, and survival should matter.

---

# 21. Continue / Exit Controls

The `Continue` button should be disabled or muted until one of these is true:

* Match is over
* Player skips replay
* Player confirms they want to exit

## Component

```tsx
<ReplayFooterActions
  canContinue={matchStatus === "final"}
  onContinue={advanceToAftermath}
/>
```

## Buttons

```txt
[Watch Again] [Box Score]                         [Continue →]
```

Primary action is `Continue`.

Secondary actions are `Watch Again` and `Box Score`.

---

# 22. Visual Tokens

## Team side colors

```css
:root {
  --team-left: #f97316;
  --team-left-soft: rgba(249, 115, 22, 0.12);
  --team-left-border: rgba(249, 115, 22, 0.45);

  --team-right: #22d3ee;
  --team-right-soft: rgba(34, 211, 238, 0.12);
  --team-right-border: rgba(34, 211, 238, 0.45);

  --event-throw: #f97316;
  --event-catch: #22d3ee;
  --event-dodge: #a78bfa;
  --event-out: #ef4444;
  --event-special: #facc15;
  --event-substitution: #94a3b8;
}
```

## Replay panel colors

```css
:root {
  --replay-bg: #050914;
  --replay-panel: #0b1220;
  --replay-panel-raised: #101a2b;
  --replay-border: rgba(148, 163, 184, 0.16);
  --replay-border-strong: rgba(34, 211, 238, 0.35);

  --replay-text-primary: #f8fafc;
  --replay-text-secondary: #a8b3c7;
  --replay-text-muted: #64748b;
}
```

---

# 23. Animation Rules

## Good animations

* Ball path draws from thrower to target.
* Player token pulses when selected.
* Eliminated player fades and gets an X.
* Catch event briefly flashes cyan.
* Dodge path uses quick dashed motion.
* Final whistle triggers subtle winner banner.

## Bad animations

* Constant glowing player tokens.
* Every path visible while playing.
* Big bouncy UI.
* Flashing panels on every event.
* Full-screen victory modal that blocks analysis.

## CSS interaction baseline

```css
.replay-card {
  transition:
    border-color 140ms ease,
    background-color 140ms ease,
    transform 140ms ease;
}

.replay-card:hover {
  border-color: var(--replay-border-strong);
}
```

---

# 24. Replay Event Data Model (Shipped Types)

> The shipped types are in `frontend/src/types.ts`. The engine produces two event types:

## ReplayEvent (raw engine event)

```ts
export interface ReplayEvent {
  index: number;
  tick: number;
  event_type: string;        // e.g. "throw_resolution"
  phase: string;
  actors: Record<string, string>;
  context: Record<string, unknown>;
  probabilities: Record<string, number>;
  rolls: Record<string, number>;
  outcome: Record<string, unknown>;
  state_diff: Record<string, unknown>;
  label: string;
  detail: string;
}
```

## ReplayProofEvent (enriched for UI display)

```ts
export interface ReplayProofEvent {
  sequence_index: number;
  tick: number;
  thrower_id: string;
  thrower_name: string;
  target_id: string;
  target_name: string;
  offense_club_id: string;
  defense_club_id: string;
  resolution: string;
  is_key_play: boolean;
  proof_tags: string[];
  summary: string;
  detail: string;
  odds: Record<string, number>;
  rolls: Record<string, number>;
  fatigue: Record<string, number>;
  decision_context: Record<string, unknown>;
  tactic_context: Record<string, unknown>;
  liability_context: Record<string, unknown>;
  score_state: Record<string, number>;
}
```

> **Note:** The `ReplayProofEvent` type is the richer version meant for the play-by-play UI. Use `is_key_play` to filter key moments. The `proof_tags` array provides event categorization. Path visualization (`from`/`to` coordinates) is aspirational — the engine does not yet expose spatial position data.

---

# 25. Player Match State Model

```ts
export type ReplayPlayerState = {
  playerId: string;
  name: string;
  number: number;
  teamId: string;

  role: string;
  archetype?: string;

  side: "left" | "right";

  status:
    | "active"
    | "out"
    | "bench"
    | "injured"
    | "substituted";

  courtPosition: {
    x: number;
    y: number;
    lane?: CourtLane;
  };

  hasBall?: boolean;
  isTargeted?: boolean;
  isRecentlyActive?: boolean;
};
```

---

# 26. Match Replay State Model

```ts
// UI-side replay state (not a shipped API type — built client-side from MatchReplayResponse)
export type MatchReplayState = {
  matchId: string;
  status: "notStarted" | "playing" | "paused" | "final";

  currentTick: number;
  durationTicks: number;
  speed: 0.5 | 1 | 2 | 4;

  leftTeam: ReplayTeam;
  rightTeam: ReplayTeam;

  survivors: {
    left: number;
    right: number;
  };

  events: ReplayProofEvent[];

  selectedEventIndex?: number;
  selectedPlayerId?: string;

  activeTab: "playByPlay" | "keyPlays" | "stats" | "shots";
  mode: "live" | "postMatch";
};
```

---

# 27. Component Tree

```tsx
<MatchReplayScreen>
  <AppSidebar activeRoute="matchReplay" />

  <ReplayMain>
    <ScreenHeader
      eyebrow="Match Day"
      title="Match Replay"
    />

    <ReplayScoreboard />

    <ReplayLayout>
      <TeamReplayRoster side="left" />

      <ReplayCenter>
        <ReplayCourt />
        <ReplayControls />
        <ReplayEventLegend />
        <ReplayFooterActions />
      </ReplayCenter>

      <ReplayInfoPanel>
        <ReplayTabs />
        {activeTab === "playByPlay" && <PlayByPlayList />}
        {activeTab === "keyPlays" && <KeyPlaysList />}
        {activeTab === "stats" && <ReplayStatsPanel />}
        {activeTab === "shots" && <ShotMap />}
      </ReplayInfoPanel>
    </ReplayLayout>
  </ReplayMain>
</MatchReplayScreen>
```

---

# 28. Implementation Priority

## Phase 1: Fix the layout and readability

Build:

1. `ReplayScoreboard`
2. `TeamReplayRoster`
3. `ReplayCourt`
4. `ReplayControls`
5. `ReplayInfoPanel`

This gives the page its correct structure.

## Phase 2: Make the replay understandable

Build:

1. `PlayerToken`
2. `ActionPath`
3. `PlayByPlayList`
4. `KeyPlaysList`
5. Event marker timeline

This makes the sim watchable.

## Phase 3: Make the end state satisfying

Build:

1. `WinnerBanner`
2. `MatchSummaryCard`
3. `PlayerOfTheMatch`
4. Post-match default tab logic
5. `Watch Again` / `Box Score` / `Continue` actions

This makes the replay feel rewarding.

## Phase 4: Add tactical depth

Build:

1. `ShotMap`
2. Player filtering
3. Event filtering
4. Full-match path overlay toggle
5. Advanced stat breakdowns

This is the spicy nerd layer. Save it for after the page works cleanly.

---

# 29. Hard UX Rules

## Do

* Make the scoreboard dominant.
* Put team rosters on the sides.
* Use the court as the main visual stage.
* Keep live playback visually clean.
* Use post-match mode for full tactical detail.
* Let users click events to seek the replay.
* Let users click players to highlight them.
* Show key plays after the match ends.
* Make the final state feel like payoff.
* Keep path colors consistent with event types.

## Do Not

* Show every path at once during live replay.
* Make player tokens too large.
* Use unlabeled icons with no legend.
* Put all players in awkward evenly-spaced rows.
* Make the right panel only a raw event dump.
* Hide who is alive/out.
* Let the `Continue` button float randomly.
* Make the winner banner block the court.

---

# 30. Final Product Rule

The Match Replay page should support two fantasies at once:

> **“I want to watch the match.”**
> **“I want to understand why the match happened.”**

Live Replay Mode satisfies the first.
Post-Match Analysis Mode satisfies the second.

That is the full sauce. This page is where the simulation earns trust, drama, and replayability.
