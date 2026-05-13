# Match Replay Phase 2: Make the Replay Understandable

**Depends on:** Phase 1 complete (ReplayScoreboard, TeamReplayRoster, ReplayControls, ReplayInfoPanel exist, layout restructured)

**Design system reference:** `docs/design-systems/Match-Replay-Design-System.md`, sections 6–8, 11, 13–14

---

## Goal

Make the replay watchable and understandable — redesigned player tokens on the court, clear throw/catch/dodge path visualization, a proper play-by-play list, and event markers on the timeline.

---

## What exists after Phase 1

- Proper 3-column grid: left roster | court + controls | right info panel
- `ReplayScoreboard` with dominant survivor counts
- `TeamReplayRoster` panels showing active/out status
- `ReplayControls` with play/pause, step, speed, timeline
- `ReplayInfoPanel` with Play-by-Play and Key Plays tabs
- SVG court still renders inline in `MatchReplay.tsx`

**Current court issues:**
- Player tokens are basic SVG circles with names — no clear status indicators
- Throw trajectories are drawn but visually undifferentiated (all same color/style)
- No distinction between throws, catches, dodges, and eliminations in path rendering
- Timeline scrubber has no event markers

---

## What to build

### 1. `ReplayCourt` (extract from MatchReplay.tsx)

**New file:** `frontend/src/components/match-replay/ReplayCourt.tsx`

Extract the SVG court rendering from `MatchReplay.tsx` into its own component.

**Props:**
```ts
{
  homePlayerStates: PlayerState[];
  awayPlayerStates: PlayerState[];
  currentEvent: ReplayProofEvent | null;
  recentEvents: ReplayProofEvent[];  // last 1–2 events for trail rendering
  selectedPlayerId?: string;
  mode: 'live' | 'postMatch';
}
```

**Court visual rules:**
- Left half warm/orange tint, right half cool/cyan tint
- Subtle center line
- Court should be the largest single element in the center column
- Players arranged in a two-row formation per side (3 front, 3 back) based on roster order

### 2. `PlayerToken`

**New file:** `frontend/src/components/match-replay/PlayerToken.tsx`

Redesigned player markers on the court.

**Props:**
```ts
{
  name: string;
  status: 'active' | 'out';
  teamSide: 'left' | 'right';
  isBallCarrier: boolean;
  isTargeted: boolean;
  isSelected: boolean;
  isRecentlyActive: boolean;
}
```

**Token states:**
| State | Visual |
| ----- | ------ |
| Active | Solid ring, team color, readable name |
| Ball carrier | Strong glow + small ball indicator |
| Targeted | Pulsing outline |
| Recently acted | Brief highlight fade |
| Out | X marker over faded token |
| Selected | Brighter border |

**Rules:**
- Show short name only on court (e.g. "THORN") to reduce clutter
- Left team tokens use warm color, right team uses cool color
- Out tokens stay visible but faded with an X
- Token size should be consistent — don't make them too large
- Active tokens should be clearly distinguishable from out tokens at a glance

### 3. `ActionPath`

**New file:** `frontend/src/components/match-replay/ActionPath.tsx`

SVG path visualization for throw/catch/dodge events.

**Props:**
```ts
{
  type: 'throw' | 'catch' | 'dodge' | 'elimination';
  fromPosition: { x: number; y: number };
  toPosition: { x: number; y: number };
  isKeyPlay: boolean;
  isActive: boolean;  // currently animating
}
```

**Path visual mapping:**
| Type | Line Style | Color |
| ---- | ---------- | ----- |
| Throw | Solid line with arrowhead | Orange `#f97316` |
| Catch | Solid line | Cyan `#22d3ee` |
| Dodge | Dashed line | Purple `#a78bfa` |
| Elimination | Solid line with X at endpoint | Red `#ef4444` |

**Rules:**
- During live replay, show only the current event path + last 1–2 trails (fading)
- During post-match, show selected event path and key play paths
- Key plays get a slightly thicker line
- Active paths animate: line draws from source to target
- Inactive trails fade to ~30% opacity
- Don't show all paths at once during live replay — it creates visual noise

**Position derivation:** Since the engine doesn't expose spatial positions, derive approximate positions from the two-row formation layout. Map `thrower_id` and `target_id` to their formation position on the court SVG.

### 4. `PlayByPlayList`

**Edit:** `frontend/src/components/match-replay/ReplayInfoPanel.tsx`

Refine the play-by-play list within the info panel.

**Event card layout:**
```
TICK 07                            ●
Cade Kade sends a screamer toward
Priya Turner. The catch is fumbled
and they're out.
```

**Rules:**
- Tick number is a `dm-kicker` label
- Event dot uses the event type color (orange for throw, cyan for catch, red for elimination)
- `summary` field is the primary text
- `detail` field shown as secondary text below (if present and different from summary)
- Current tick's event gets a cyan left border highlight
- Clicking an event calls `onSelectEvent` to seek the replay
- List auto-scrolls to the current event during playback

### 5. `KeyPlaysList`

**Also in:** `frontend/src/components/match-replay/ReplayInfoPanel.tsx`

Separate view showing only key plays.

**Rules:**
- Filter `proof_events` by checking if `index` is in `key_play_indices`
- Same card layout as play-by-play but with larger text
- Default tab after match ends
- Each key play shows a type icon/color matching the event resolution

### 6. Event markers on timeline

**Edit:** `frontend/src/components/match-replay/ReplayControls.tsx`

Add small colored dots on the timeline scrubber at key event ticks:

```
Tick 0 ━━━━●━━━━━━━━●━━●━━━━━━━●━━━ Tick 42
           ↑         ↑  ↑       ↑
         throw   catch  out   key play
```

**Rules:**
- Only show key play markers (from `key_play_indices`) — not every event
- Marker color: gold for key plays (keeps it simple)
- Markers are small (4–6px dots) and don't block the scrubber
- Hover on a marker shows a tooltip with the event summary

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/match-replay/ReplayCourt.tsx` | Create (extract from MatchReplay.tsx) |
| `frontend/src/components/match-replay/PlayerToken.tsx` | Create |
| `frontend/src/components/match-replay/ActionPath.tsx` | Create |
| `frontend/src/components/match-replay/ReplayInfoPanel.tsx` | Edit — refine PlayByPlayList and KeyPlaysList rendering |
| `frontend/src/components/match-replay/ReplayControls.tsx` | Edit — add event markers on timeline |
| `frontend/src/components/MatchReplay.tsx` | Edit — use ReplayCourt, simplify inline SVG code |

---

## What NOT to build

- Post-match mode switching (auto-switch to key plays tab) — Phase 3
- Winner banner — Phase 3
- Match summary card — Phase 3
- Stats tab content — Phase 3
- ShotMap — Phase 4
- Full-match path overlay toggle — Phase 4
