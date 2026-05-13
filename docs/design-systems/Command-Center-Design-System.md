# Command Center Design System

> **Terminology note:** In the app, this screen is the “Match Week” tab (kicker: “WAR ROOM”). “Command Center” is the design system name for the post-match result/replay view within that tab.

> **Implementation note:** The frontend uses Tailwind CSS v4 with `@theme` tokens and `dm-` utility classes. Raw CSS custom properties shown here are for design intent — translate them to the appropriate `dm-` classes or `@theme` tokens when implementing.

## 1. Design Thesis

**The post-match view should feel like:**

> “I am reviewing a decisive simulated sports event with clear stakes, readable outcomes, and tactical consequence.”

Right now the UI feels jank because everything has similar visual weight. The player has to hunt for what matters.

The redesign should enforce this hierarchy:

1. **Who played?**
2. **Who won?**
3. **How did the match unfold?**
4. **Who mattered?**
5. **What changed because of it?**
6. **What can I do next?**

That is the whole screen.

---

# 2. Core Layout

## Screen Shell

Keep the current sidebar idea, but make the replay screen use a stronger central structure.

```txt
┌───────────────────────────────────────────────┐
│ Top Context Bar                               │
│ War Room / Command Center      Week 4 / 2026    │
├───────────┬───────────────────────────────────┤
│ Sidebar   │ Main Content                      │
│           │                                   │
│           │ Match Header / Scoreboard         │
│           │ Replay Timeline                   │
│           │ Key Moments / Player Impact       │
│           │ Fallout / Changes                 │
│           │ CTA                               │
└───────────┴───────────────────────────────────┘
```

## Main Content Width

Use a centered max-width instead of stretching everything across the entire monitor.

```css
.main-content {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 40px;
}
```

Your current screenshots have a lot of “giant empty airplane hangar” energy. The content needs a readable arena.

---

# 3. Visual Tokens

## Color Palette

Use colors functionally, not decoratively.

```css
:root {
  --bg-page: #050914;
  --bg-panel: #0b1220;
  --bg-panel-raised: #101a2b;
  --bg-panel-soft: #0d1626;

  --border-muted: rgba(148, 163, 184, 0.16);
  --border-strong: rgba(34, 211, 238, 0.35);

  --text-primary: #f8fafc;
  --text-secondary: #a8b3c7;
  --text-muted: #64748b;

  --accent-cyan: #22d3ee;
  --accent-cyan-soft: rgba(34, 211, 238, 0.12);

  --accent-orange: #f97316;
  --accent-orange-hover: #fb923c;

  --team-home: #ef4444;
  --team-away: #3b82f6;

  --success: #22c55e;
  --warning: #facc15;
  --danger: #ef4444;
}
```

## Color Rules

| Use Case                | Color              |
| ----------------------- | ------------------ |
| Navigation active state | Cyan               |
| Primary action          | Orange             |
| Home team identity      | Red / warm accent  |
| Away team identity      | Blue / cool accent |
| Positive outcome        | Green              |
| Warnings / blockers     | Yellow             |
| Loss / damage / injury  | Red                |
| Neutral system info     | Slate / muted gray |

The key rule: **orange is only for actions**. Cyan is only for navigation, labels, and system identity. Red/blue are only for team conflict.

---

# 4. Typography

Your current typography has flavor, but it is too evenly distributed. Keep the condensed sci-fi sports identity, but create levels.

## Font Roles

| Role          | Style                             |
| ------------- | --------------------------------- |
| Page Title    | Large condensed uppercase         |
| Section Label | Tiny uppercase letter-spaced cyan |
| Card Title    | Medium uppercase bold             |
| Body          | Clean readable sans               |
| Numeric Stats | Tabular / mono / bold             |
| Event Log     | Compact sans or mono hybrid       |

## Suggested Scale

```css
.text-kicker {
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent-cyan);
  font-weight: 700;
}

.text-page-title {
  font-size: 32px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-primary);
  font-weight: 900;
}

.text-section-title {
  font-size: 18px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-primary);
  font-weight: 800;
}

.text-body {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.text-stat-large {
  font-size: 56px;
  line-height: 1;
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}
```

## Hard Rule

Do **not** use tiny text for important information.

Tiny text is for labels only. Anything the player needs to act on should be at least 14px.

---

# 5. Component System

## A. MatchReplayHeader

Purpose: tells the player where they are.

```txt
WAR ROOM

Match Week
Review the full match flow, key eliminations, and weekly fallout.
```

Implementation shape:

```tsx
<ScreenHeader
  eyebrow="WAR ROOM"
  title="Match Week"
  subtitle="Review the full match flow, key eliminations, and weekly fallout."
  meta="Week 4 · Season 2026"
/>
```

---

## B. MatchScoreHero

This is the most important component.

```txt
┌────────────────────────────────────────────────────────────┐
│ SOLSTICE              8       VS       0        CYPHERS     │
│ 3-1 · 8 Survivors           FINAL             1-3 · 0 Survivors │
└────────────────────────────────────────────────────────────┘
```

> **Key concept:** Dodgeball matches are decided by survivors, not traditional scoring. The “score” numbers (8 vs 0) represent `home_survivors` and `away_survivors` from `MatchResult`. The team with more survivors wins.

### Rules

* Winner side gets stronger glow / stronger opacity.
* Loser side remains readable but subdued.
* Survivor count is enormous — this IS the score.
* “FINAL” sits between the survivor counts.
* Team names should be big enough to be memorable.
* Records are under team identity.

Suggested structure:

```tsx
<MatchScoreHero
  homeTeam={matchResult.home_club_name}
  awayTeam={matchResult.away_club_name}
  homeSurvivors={matchResult.home_survivors}
  awaySurvivors={matchResult.away_survivors}
  homeRecord=”3-1”
  awayRecord=”1-3”
  winner={matchResult.winner_team_id}
/>
```

---

## C. ReplayTimeline

This is where the Command Center becomes a replay, not just a result screen.

```txt
MATCH FLOW

Q1 / Opening Phase
00:42  Mika Novak eliminates Quinn Nova
01:18  Ash Zane catches throw from Elio Penn
02:04  Solstice gains ball control

Midgame
03:27  Cyphers lose final backline defender
04:10  Solstice snowballs possession

Final Sequence
05:31  Last Agent eliminated
```

### Visual Design

Use a vertical event rail.

```txt
│
● 00:42  Elimination
│        Mika Novak tagged Quinn Nova.
│
● 01:18  Catch
│        Ash Zane reversed possession.
│
● 05:31  Final Out
│        Solstice wins with 8 survivors.
│
```

### Event Types

| Event Type     | Icon / Accent         |
| -------------- | --------------------- |
| Elimination    | Red                   |
| Catch          | Cyan                  |
| Dodge          | Slate                 |
| Clutch         | Orange                |
| Injury         | Yellow / Red          |
| Final Out      | Green or Orange       |
| Momentum Shift | Purple/blue, optional |

Suggested data model:

```ts
type ReplayEventType =
  | "elimination"
  | "catch"
  | "dodge"
  | "clutch"
  | "injury"
  | "momentum"
  | "final_out";

type ReplayEvent = {
  id: string;
  time: string;
  phase: "Opening" | "Midgame" | "Endgame";
  type: ReplayEventType;
  title: string;
  description: string;
  playerName?: string;
  teamName?: string;
  impact?: "low" | "medium" | "high";
};
```

This gives you replay flavor without needing full animation yet.

---

## D. KeyPlayersPanel

This gives the player story.

```txt
KEY PERFORMERS

Mika Novak
3 eliminations · 1 catch · +18 impact

Ash Zane
2 eliminations · 2 dodges · +12 impact

Elio Penn
1 elimination · 4 assists · +9 impact
```

### Rules

* Show top 3 only.
* Use impact badges.
* Do not turn it into a spreadsheet.
* The player should instantly know who cooked.

Component:

```tsx
<KeyPlayersPanel players={topPerformers} />
```

Data:

```ts
type KeyPlayer = {
  id: string;
  name: string;
  teamName: string;
  statline: string;
  impactScore: number;
  tags: string[];
};
```

---

## E. TacticalSummaryCard

This is where your sim can communicate meaning.

```txt
TACTICAL READ

Solstice dominated possession early and forced Northwood Cyphers into weak-side throws.
Cyphers failed to protect the backline and collapsed after the first catch reversal.
```

This is secretly one of the most important cards for your game because it makes the simulation feel intelligent.

### Rules

* One paragraph max.
* No generic sports fluff.
* Mention actual mechanics: possession, target priority, weak side, stamina, formation, clutch, morale.
* Should explain why the result happened.

Bad:

> Solstice played better and won the match.

Good:

> Solstice controlled the opening exchange, forced Cyphers into low-percentage throws, and converted two catch reversals into a full backline collapse.

---

## F. MatchFalloutPanel

This is your “what changed?” section.

```txt
FALLOUT

Player Development
No attribute growth detected this week.

League Table
Solstice rises to #4. Cyphers fall to #9.

Recruit Reactions
No prospect interest changes reported.
```

This already exists in your screenshot, but it should become a consistent 3-card row instead of flat bars.

```tsx
<FalloutGrid>
  <FalloutCard type="development" title="Player Development" body="No attribute growth detected." />
  <FalloutCard type="standings" title="League Table" body="No significant rank changes." />
  <FalloutCard type="recruiting" title="Recruit Reactions" body="No prospect interest changes reported." />
</FalloutGrid>
```

### Why cards instead of bars?

Because bars look like debug output. Cards look like a management game.

---

## G. PrimaryActionBar

Your CTA should not float randomly in the void.

```txt
[ View Box Score ] [ Watch Key Moments ]              [ Advance to Next Week ]
```

Primary action on the right. Secondary actions on the left.

```tsx
<ActionBar
  secondary={[
    { label: "View Box Score" },
    { label: "Watch Key Moments" }
  ]}
  primary={{ label: "Advance to Next Week" }}
/>
```

### Rules

* Only one orange button per screen.
* Secondary buttons are dark/outlined.
* Primary CTA should be visually anchored at bottom of content, not floating mid-screen.

---

# 6. Command Center Page Composition

This is the actual implementation order I would use.

```tsx
<MatchReplayScreen>
  <Sidebar />

  <MainContent>
    <ScreenHeader />

    <MatchScoreHero />

    <TwoColumnLayout>
      <ReplayTimeline />
      <RightRail>
        <KeyPlayersPanel />
        <TacticalSummaryCard />
      </RightRail>
    </TwoColumnLayout>

    <MatchFalloutPanel />

    <ActionBar />
  </MainContent>
</MatchReplayScreen>
```

Desktop layout:

```txt
┌─────────────────────────────────────────────┐
│ Header                                      │
├─────────────────────────────────────────────┤
│ Score Hero                                  │
├───────────────────────────────┬─────────────┤
│ Replay Timeline               │ Key Players │
│                               │ Tactical    │
├───────────────────────────────┴─────────────┤
│ Fallout Cards                               │
├─────────────────────────────────────────────┤
│ Actions                                     │
└─────────────────────────────────────────────┘
```

Responsive layout:

```txt
Header
Score Hero
Key Players
Tactical Summary
Replay Timeline
Fallout
Actions
```

---

# 7. Spacing System

Use an 8px spacing scale.

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 24px;
--space-6: 32px;
--space-7: 48px;
--space-8: 64px;
```

## Rules

| Element        | Padding   |
| -------------- | --------- |
| Small badge    | 4px 8px   |
| Button         | 12px 18px |
| Card           | 20px-24px |
| Major panel    | 24px-32px |
| Screen content | 32px-40px |

Current UI issue: lots of elements are technically aligned, but not **compositionally grouped**. Spacing should tell the player what belongs together.

---

# 8. Borders, Radius, Shadows

Keep it sharp, not bubbly.

```css
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;

--shadow-panel: 0 12px 40px rgba(0, 0, 0, 0.28);
--shadow-glow-cyan: 0 0 24px rgba(34, 211, 238, 0.12);
--shadow-glow-orange: 0 0 28px rgba(249, 115, 22, 0.25);
```

## Rules

* Main panels: 8px radius.
* Buttons: 6px radius.
* Score hero: 10px or 12px radius.
* Avoid huge rounded corners. This game wants “war room,” not “Duolingo dashboard.”

---

# 9. Animation Rules

Keep animation minimal and purposeful.

Good animations:

* Score counts up from 0 to final.
* Replay events reveal one by one.
* Final Out event gets a small pulse.
* Primary button glow appears after replay completes.
* Hover states brighten borders.

Bad animations:

* Constant glowing everywhere.
* Cards sliding from random directions.
* Big bouncy UI.
* Anything that makes it feel like a mobile gacha menu.

Implementation:

```css
.card {
  transition:
    border-color 140ms ease,
    background-color 140ms ease,
    transform 140ms ease;
}

.card:hover {
  transform: translateY(-1px);
  border-color: var(--border-strong);
}
```

---

# 10. Command Center Specific UX Rules

## Rule 1: The score owns the top of the screen

Do not bury the result.

## Rule 2: Every match needs a story

Even if the sim result is simple, the UI should surface a reason.

Examples:

* “Early possession snowball”
* “Backline collapse”
* “Catch reversal changed momentum”
* “Star player targeted”
* “Weak starter exposed”
* “Stamina failure in final phase”

## Rule 3: Fallout comes after story

The player should understand the match before seeing consequences.

## Rule 4: The CTA should feel earned

“Advance to Next Week” should come after the player has seen the result, replay, and fallout.

## Rule 5: Avoid debug language

Current phrasing like:

> No attribute growth detected this week.

That is okay, but it feels system-ish.

Better:

> No player development changes this week.

Or:

> No attribute gains from this match.

For a sports sim, the wording should feel like a front-office report, not a console log.

---

# 11. Recommended Command Center Variants

You probably want three replay states.

## A. Full Replay Available

Used after a simulated match.

Includes:

* Score hero
* Timeline
* Key players
* Tactical summary
* Fallout
* Actions

## B. Quick Result

Used when player skips detailed replay.

Includes:

* Score hero
* 3 key moments
* Fallout
* CTA

## C. No Match / Bye Week

Includes:

* Week summary
* Training/development
* League movement
* Recruiting
* CTA

This prevents the screen from feeling empty when nothing dramatic happened.

---

# 12. Implementation Priority

Do **not** build everything at once.

## Phase 1: Fix the hierarchy

Build:

1. `ScreenHeader`
2. `MatchScoreHero`
3. `FalloutGrid`
4. `ActionBar`

This alone will make the screen look 5x better.

## Phase 2: Add replay identity

Build:

1. `ReplayTimeline`
2. `KeyPlayersPanel`
3. `TacticalSummaryCard`

This makes it feel like an actual sim game instead of a results page.

## Phase 3: Add polish

Add:

1. Score count-up
2. Event reveal animation
3. Winner glow
4. Hover states
5. Empty-state variants

---

# 13. The Big Critique

The current UI has a cool foundation, but it is treating every piece of information like it has the same importance. That is the core jank.

The fix is not “more decoration.”

The fix is:

> **One dominant match result, one readable story path, one clear consequence section, one obvious next action.**

That should be the Command Center design system. The player opens the screen and immediately thinks:

> “Oh, we smoked them 8-0, Mika went crazy, our plan worked, nothing changed in recruiting, advance.”

That is the win condition.
