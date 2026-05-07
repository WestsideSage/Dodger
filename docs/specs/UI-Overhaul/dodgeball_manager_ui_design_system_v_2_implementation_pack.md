# Dodgeball Manager 2026 — Design System v2 Implementation Pack

## Verdict

The design direction is strong. **“Premium Tactical Sports Sim” is the right north star** because it preserves the serious manager-game density while finally giving the app a game identity.

The biggest improvement needed is not “more neon” or “more darkness.” It is **stricter visual grammar**: every screen needs to know whether it is acting like a war room, a match broadcast, a roster lab, or a league office. Otherwise, the new dark theme risks becoming the same dashboard again, just in slate.

This version tightens the system so it can be implemented consistently.

---

# 1. Design Pillars

## Pillar 1 — Dense, Not Cluttered

Dodgeball Manager should stay information-rich. This is a sim game, not a landing page.

**Rule:** Use compact typography, strong alignment, table density, and small badges — but reduce nested boxes.

## Pillar 2 — Broadcast Energy on Match Moments

Not every screen needs to scream. The UI should reserve cinematic treatment for:

- Matchups
- Scoreboards
- Eliminations
- Clutch catches
- Momentum swings
- Rivalry/news moments
- Playoff/championship context

## Pillar 3 — Transparent Simulation Evidence

The game’s no-hidden-math ethos is a strength. The redesign should make proof feel like an analyst booth, not a debug console.

**Rule:** Simulation proof should be visually staged as **Replay Analysis**, **Outcome Breakdown**, or **Coach Tape**, not raw developer telemetry.

## Pillar 4 — Team Identity Is an Accent Layer

Team colors should add emotion, not destroy readability.

**Rule:** Team colors may tint headers, score tiles, badges, and matchup rails. They should not become full-page backgrounds unless heavily darkened.

## Pillar 5 — No Beige Foundation

The old cream/card system should be retired as a primary visual language.

Optional exception: a tiny “archival paper” treatment may be used for rare scouting notes, historical records, or newspaper-like league flavor — never as the default surface.

---

# 2. Screen Modes

This is the most important structural addition.

## A. War Room Mode

Used for:

- Command Center
- Hub
- Tactics overview
- Team planning
- Front-office decisions

Feel:

- Dark tactical dashboard
- Slate panels
- Cyan/orange action highlights
- Dense but calm

Primary accent: `cyan`
Secondary accent: `orange`

## B. Match Day Mode

Used for:

- Match Replay
- Live match dashboard
- Playoff games
- Rivalry games
- Postgame report

Feel:

- Broadcast cockpit
- Scoreboard typography
- Momentum colors
- Event timeline
- High-impact glow moments

Primary accent: `orange`
Secondary accents: `cyan`, `rose`

## C. Roster Lab Mode

Used for:

- Roster
- Player cards
- Development
- Scouting
- Training

Feel:

- Evaluation room
- Sticky identity columns
- Compact stat bars
- Player archetype tags
- Clean ratings hierarchy

Primary accent: `cyan`
Secondary accents: role/stat colors

## D. League Office Mode

Used for:

- Standings
- Schedule
- News
- League context
- Records

Feel:

- Serious league database
- More restrained color
- Strong tables
- Occasional headline treatment

Primary accent: `slate`
Secondary accent: context-driven team colors

---

# 3. Typography System

## Font Stack

### Display / Broadcast

**Font:** `Oswald`

Use for:

- App title
- Team names
- Scoreboards
- Section headers
- Match titles
- Major cinematic events

Rules:

- Always uppercase
- Use tracking
- Prefer condensed, punchy text
- Avoid using for long paragraphs

Suggested classes:

```txt
font-display uppercase tracking-wide
font-display uppercase tracking-widest
```

### Data / Telemetry

**Font:** `JetBrains Mono`

Use for:

- Ratings
- Timers
- Match log timestamps
- Win probability
- Tactical values
- Stat chips
- Seeds/records

Rules:

- Always use `tabular-nums`
- Keep compact
- Never use for long body text

Suggested classes:

```txt
font-mono-data tabular-nums
```

### Body / UI

**Font:** `Inter`

Use for:

- Table names
- Buttons
- Tooltips
- General UI copy
- Explanatory text

Suggested classes:

```txt
font-body
```

## Type Scale

```txt
Display XL:  text-5xl / 6xl   Scoreboards, champion moments
Display LG:  text-3xl / 4xl   Team names, page titles
Display MD:  text-xl / 2xl    Section headers
Display SM:  text-sm / base   Table headers, nav labels
Data LG:     text-xl / 2xl    Score numbers, major ratings
Data MD:     text-sm / base   Table values, timeline values
Data SM:     text-xs          Chips, timestamps, micro labels
Body MD:     text-sm / base   Main UI
Body SM:     text-xs          Help text, secondary labels
```

---

# 4. Color System

## Base Shell

```txt
App Background:        #020617  slate-950
Primary Surface:       #0f172a  slate-900
Elevated Surface:      #1e293b  slate-800
Soft Surface:          rgba(15, 23, 42, 0.72)
Border:                #1e293b  slate-800
Strong Border:         #334155  slate-700
```

## Text

```txt
Primary Text:          #ffffff
Secondary Text:        #cbd5e1  slate-300
Muted Text:            #94a3b8  slate-400
Dead Text:             #64748b  slate-500
```

## Brand / Court-Line Accents

```txt
Power / Primary Action:     #f97316  orange-500
Friendly / Agility:         #22d3ee  cyan-400
Opponent / Eliminated:      #f43f5e  rose-500
Success / Healthy:          #10b981  emerald-500
Warning / Fatigue:          #f59e0b  amber-500
```

## Stat Color Mapping

Use consistent stat colors everywhere.

```txt
Power:       rose-500
Accuracy:    orange-500
Agility:     cyan-400
Hands:       emerald-500
Awareness:   violet-400
Stamina:     amber-500
Morale:      sky-400
Injury/Risk: red-500
```

## Team Color Rules

Team colors can be used for:

- Left/right matchup rails
- Score tile outlines
- Small logo glows
- Record badges
- Replay timeline side markers

Team colors should be darkened or alpha-blended before use as surfaces.

Good:

```txt
border-[teamColor]
bg-[teamColor]/10
shadow-[0_0_18px_teamColorAlpha]
```

Bad:

```txt
Full bright team-color card backgrounds
Team-color table rows
Unreadable team-color text on dark surfaces
```

---

# 5. Layout & Containment Rules

## No Nested Card Soup

Avoid:

```txt
Panel > Card > Card > Table > Mini Card
```

Prefer:

```txt
Panel > Header Band > Divided Sections > Table/List
```

## Main Shell

Recommended layout:

```txt
App Shell
├── Left Navigation Rail
├── Top Broadcast Header / Context Bar
└── Main Workspace
    ├── Page Header Band
    ├── Primary Panel
    ├── Secondary Grid / Tables
    └── Context Drawer if needed
```

## Panel Anatomy

```txt
.panel
├── .panel-header
├── .panel-section
├── .panel-section
└── .panel-footer
```

Use borders/dividers instead of nested backgrounds.

---

# 6. Motion Rules

Motion should feel like a sports UI, not a SaaS dashboard.

## Allowed Motion

- Hover row highlight
- Active nav rail slide/stripe
- Score change pulse
- Elimination flash
- Momentum bar shift
- Timeline event reveal
- Button press scale from `0.98` to `1.0`

## Avoid

- Bouncy playful animations
- Constant pulsing glows
- Excessive page transitions
- Decorative animations that slow dense workflows

## Motion Timing

```txt
Fast UI response:      120ms
Standard transition:   180ms
Match impact flash:    280ms
Cinematic reveal:      400–600ms max
```

---

# 7. Component Recipes

## A. App Shell

Purpose: Make the whole app feel like a game shell instead of a website.

```tsx
<div className="min-h-screen bg-slate-950 text-white font-body bg-[radial-gradient(circle_at_top_left,rgba(6,182,212,0.12),transparent_32%),radial-gradient(circle_at_top_right,rgba(249,115,22,0.10),transparent_28%)]">
  <div className="flex min-h-screen">
    <aside className="w-64 border-r border-slate-800 bg-slate-950/80 backdrop-blur">
      {/* nav */}
    </aside>
    <main className="flex-1">
      {/* broadcast header + workspace */}
    </main>
  </div>
</div>
```

## B. Broadcast Header

```tsx
<header className="border-b border-slate-800 bg-slate-950/80 px-5 py-4 backdrop-blur">
  <div className="flex items-center justify-between gap-4">
    <div>
      <p className="font-mono-data text-xs uppercase tracking-[0.24em] text-cyan-400">Dodgeball Manager 2026</p>
      <h1 className="font-display text-2xl font-bold uppercase tracking-wide text-white">Command Center</h1>
    </div>
    <div className="font-mono-data text-xs text-slate-400 tabular-nums">
      SEASON 2026 · WEEK 04
    </div>
  </div>
</header>
```

## C. Navigation Item

```tsx
<button className="group flex w-full items-center gap-3 border-l-2 border-transparent px-4 py-3 text-left font-display text-sm uppercase tracking-wide text-slate-400 transition-colors hover:border-slate-600 hover:bg-slate-800/60 hover:text-slate-200 data-[active=true]:border-cyan-400 data-[active=true]:bg-cyan-900/20 data-[active=true]:text-cyan-300">
  <span className="h-1.5 w-1.5 rounded-full bg-slate-600 group-data-[active=true]:bg-cyan-400" />
  Roster
</button>
```

For Match Day:

```tsx
data-[mode=match]:data-[active=true]:border-orange-500 data-[mode=match]:data-[active=true]:bg-orange-500/10 data-[mode=match]:data-[active=true]:text-orange-400
```

## D. Panel

```tsx
<section className="overflow-hidden border border-slate-800 bg-slate-900/80 shadow-2xl shadow-black/20">
  <div className="border-b border-slate-800 px-5 py-4">
    <h2 className="font-display text-xl uppercase tracking-wide text-white">Roster Lab</h2>
    <p className="mt-1 text-sm text-slate-400">Evaluate player condition, role fit, and match readiness.</p>
  </div>
  <div className="divide-y divide-slate-800">
    {/* sections */}
  </div>
</section>
```

Recommended border radius: use either sharp or slight rounding globally. For this game, **slightly sharp is better**.

```txt
Default: rounded-none or rounded-sm
Premium exception: rounded-xl only for score tiles and modal surfaces
```

## E. High-Density Table

```tsx
<table className="w-full border-collapse text-left">
  <thead>
    <tr className="border-b border-slate-800 bg-slate-950">
      <th className="px-4 py-3 font-display text-xs uppercase tracking-widest text-slate-500">Player</th>
      <th className="px-3 py-3 font-display text-xs uppercase tracking-widest text-slate-500">Role</th>
      <th className="px-3 py-3 font-display text-xs uppercase tracking-widest text-slate-500">POW</th>
      <th className="px-3 py-3 font-display text-xs uppercase tracking-widest text-slate-500">AGI</th>
      <th className="px-3 py-3 font-display text-xs uppercase tracking-widest text-slate-500">STA</th>
    </tr>
  </thead>
  <tbody className="divide-y divide-slate-800/70">
    <tr className="transition-colors hover:bg-slate-800/50">
      <td className="sticky left-0 bg-slate-900 px-4 py-3 font-body text-sm font-bold text-white">Maya Cross</td>
      <td className="px-3 py-3 font-mono-data text-xs uppercase text-cyan-400">CANNON</td>
      <td className="px-3 py-3 font-mono-data text-sm tabular-nums text-slate-300">87</td>
      <td className="px-3 py-3 font-mono-data text-sm tabular-nums text-slate-300">74</td>
      <td className="px-3 py-3 font-mono-data text-sm tabular-nums text-amber-400">62</td>
    </tr>
  </tbody>
</table>
```

## F. Stat Bar

```tsx
function StatBar({ value, colorClass = "bg-cyan-400" }: { value: number; colorClass?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-7 text-right font-mono-data text-xs tabular-nums text-slate-300">{value}</span>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-800">
        <div className={`h-full ${colorClass}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
```

## G. Badge

```tsx
<span className="inline-flex items-center border border-slate-700 bg-slate-800 px-1.5 py-0.5 font-mono-data text-[10px] uppercase tracking-wide text-slate-400">
  starter
</span>
```

Semantic variants:

```txt
Starter:   border-cyan-500/30 bg-cyan-500/10 text-cyan-300
Injured:   border-rose-500/30 bg-rose-500/10 text-rose-300
Hot:       border-orange-500/30 bg-orange-500/10 text-orange-300
Rested:    border-emerald-500/30 bg-emerald-500/10 text-emerald-300
Tired:     border-amber-500/30 bg-amber-500/10 text-amber-300
```

## H. Scoreboard Tile

```tsx
<div className="border border-slate-700 bg-slate-950 px-5 py-4 shadow-[0_0_24px_rgba(249,115,22,0.16)]">
  <p className="font-display text-xs uppercase tracking-widest text-slate-500">Home</p>
  <div className="mt-2 flex items-end justify-between gap-4">
    <h3 className="font-display text-3xl font-bold uppercase tracking-wide text-white">Vipers</h3>
    <span className="font-mono-data text-6xl font-bold tabular-nums text-orange-400">12</span>
  </div>
</div>
```

## I. Replay Cockpit Layout

```txt
Replay Cockpit
├── Match Header / Scoreboard Band
├── Momentum + Possession / Control Strip
├── Event Timeline
├── Current Event Spotlight
└── Analyst Proof Drawer
```

The replay should not feel like a list of debug events. It should feel like watching tape.

### Current Event Spotlight

```tsx
<section className="border border-orange-500/30 bg-orange-500/10 px-6 py-5 shadow-[0_0_24px_rgba(249,115,22,0.18)]">
  <p className="font-mono-data text-xs uppercase tracking-[0.24em] text-orange-300">Impact Moment</p>
  <h2 className="mt-2 font-display text-4xl font-bold uppercase tracking-wide text-white">
    Cross fires a clean body shot
  </h2>
  <p className="mt-2 max-w-3xl text-sm text-slate-300">
    Accuracy check beat dodge reaction by 14. Stamina penalty applied to defender.
  </p>
</section>
```

## J. Telemetry / Analyst Proof

```tsx
<div className="border border-slate-800 bg-slate-950 font-mono-data text-sm">
  <div className="border-b border-slate-800 px-4 py-3">
    <h3 className="font-display text-sm uppercase tracking-widest text-slate-400">Replay Analysis</h3>
  </div>
  <div className="divide-y divide-slate-800/70">
    <div className="px-4 py-3 text-slate-400">
      <span className="text-slate-600">[12:04]</span>{" "}
      <span className="border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">throw</span>{" "}
      <span className="text-cyan-300">Maya Cross</span>{" "}
      generated <span className="text-orange-300">87 POW</span> vs <span className="text-rose-300">62 DODGE</span>.
    </div>
  </div>
</div>
```

## K. Tactical Slider

Style sliders like coaching-board controls, not browser defaults.

```tsx
<div className="border-t border-slate-800 px-5 py-4">
  <div className="mb-2 flex items-center justify-between">
    <label className="font-display text-sm uppercase tracking-widest text-slate-300">Aggression</label>
    <span className="font-mono-data text-sm tabular-nums text-orange-400">72</span>
  </div>
  <input
    type="range"
    className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-slate-800 accent-orange-500"
  />
  <div className="mt-2 flex justify-between font-mono-data text-[10px] uppercase text-slate-500">
    <span>Hold</span>
    <span>Balanced</span>
    <span>Hunt</span>
  </div>
</div>
```

---

# 8. Implementation Files

## A. `index.html` font import

Add:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Oswald:wght@400;500;600;700&display=swap" rel="stylesheet">
```

## B. `tailwind.config.ts`

```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx,js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Oswald", "ui-sans-serif", "system-ui"],
        body: ["Inter", "ui-sans-serif", "system-ui"],
        "mono-data": ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        "glow-cyan": "0 0 18px rgba(6,182,212,0.28)",
        "glow-orange": "0 0 18px rgba(249,115,22,0.28)",
        "glow-rose": "0 0 18px rgba(244,63,94,0.28)",
      },
      backgroundImage: {
        "war-room": "radial-gradient(circle at top left, rgba(6,182,212,0.12), transparent 32%), radial-gradient(circle at top right, rgba(249,115,22,0.10), transparent 28%)",
        "court-grid": "linear-gradient(rgba(148,163,184,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.05) 1px, transparent 1px)",
      },
      backgroundSize: {
        "court-grid": "32px 32px",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

## C. `src/styles/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    color-scheme: dark;
  }

  html,
  body,
  #root {
    min-height: 100%;
  }

  body {
    margin: 0;
    background: #020617;
    color: #fff;
    font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  }

  * {
    box-sizing: border-box;
  }
}

@layer components {
  .dm-app-shell {
    @apply min-h-screen bg-slate-950 bg-war-room text-white font-body;
  }

  .dm-panel {
    @apply overflow-hidden border border-slate-800 bg-slate-900/80 shadow-2xl shadow-black/20;
  }

  .dm-panel-header {
    @apply border-b border-slate-800 px-5 py-4;
  }

  .dm-panel-title {
    @apply font-display text-xl font-semibold uppercase tracking-wide text-white;
  }

  .dm-panel-subtitle {
    @apply mt-1 text-sm text-slate-400;
  }

  .dm-section {
    @apply px-5 py-4;
  }

  .dm-kicker {
    @apply font-mono-data text-xs uppercase tracking-[0.24em] text-cyan-400;
  }

  .dm-table {
    @apply w-full border-collapse text-left;
  }

  .dm-table thead tr {
    @apply border-b border-slate-800 bg-slate-950;
  }

  .dm-table th {
    @apply px-4 py-3 font-display text-xs uppercase tracking-widest text-slate-500;
  }

  .dm-table tbody {
    @apply divide-y divide-slate-800/70;
  }

  .dm-table td {
    @apply px-4 py-3 text-sm;
  }

  .dm-table tbody tr {
    @apply transition-colors hover:bg-slate-800/50;
  }

  .dm-nav-item {
    @apply flex w-full items-center gap-3 border-l-2 border-transparent px-4 py-3 text-left font-display text-sm uppercase tracking-wide text-slate-400 transition-colors hover:border-slate-600 hover:bg-slate-800/60 hover:text-slate-200;
  }

  .dm-nav-item-active {
    @apply border-cyan-400 bg-cyan-900/20 text-cyan-300;
  }

  .dm-nav-item-active-match {
    @apply border-orange-500 bg-orange-500/10 text-orange-400;
  }

  .dm-badge {
    @apply inline-flex items-center border border-slate-700 bg-slate-800 px-1.5 py-0.5 font-mono-data text-[10px] uppercase tracking-wide text-slate-400;
  }

  .dm-badge-cyan {
    @apply border-cyan-500/30 bg-cyan-500/10 text-cyan-300;
  }

  .dm-badge-orange {
    @apply border-orange-500/30 bg-orange-500/10 text-orange-300;
  }

  .dm-badge-rose {
    @apply border-rose-500/30 bg-rose-500/10 text-rose-300;
  }

  .dm-badge-emerald {
    @apply border-emerald-500/30 bg-emerald-500/10 text-emerald-300;
  }

  .dm-badge-amber {
    @apply border-amber-500/30 bg-amber-500/10 text-amber-300;
  }

  .dm-data {
    @apply font-mono-data tabular-nums;
  }

  .dm-display {
    @apply font-display uppercase tracking-wide;
  }
}
```

---

# 9. Component Migration Map

## Replace Generic Cards With Panels

Search for existing card wrappers like:

```txt
.card
.panel-card
.bg-cream
.bg-paper
.rounded-lg border charcoal
```

Replace most of them with:

```txt
dm-panel
```

Inside the panel, use:

```txt
dm-panel-header
dm-section
divide-y divide-slate-800
```

## Replace Page Headers

Old pattern:

```txt
Title + subtitle in beige card
```

New pattern:

```txt
Broadcast header + page mode kicker + action cluster
```

## Replace Tables First

Tables will create the biggest perceived quality jump with the least risk.

Priority order:

1. Roster table
2. Standings table
3. Schedule table
4. Player stats table
5. Match event/proof table

## Replace Match Replay Second

Replay is the feature with the most upside. Convert it into:

1. Scoreboard band
2. Event spotlight
3. Timeline
4. Analyst proof drawer
5. Playback controls

## Replace Navigation Third

Change from dashboard tabs to a left rail or strong top shell.

If the current app structure makes left rail expensive, use a top nav bar with the same active-state grammar.

---

# 10. Match Replay Redesign Specification

## Replay Header

Must show:

- Home team
- Away team
- Score
- Match phase
- Possession/control/momentum if applicable
- Record or playoff context if available

## Event Types

Each event type gets a visual treatment.

```txt
Throw:       orange tag
Catch:       emerald tag
Dodge:       cyan tag
Elimination: rose tag + impact flash
Substitution: slate tag
Injury:      amber/rose tag
Momentum:    violet/cyan tag
Timeout:     amber tag
```

## Event Spotlight Copy Rules

Bad:

```txt
Player A action success. Roll: 0.71. Threshold: 0.62.
```

Good:

```txt
Cross wins the exchange with a clean body shot.
Accuracy beat dodge reaction by 14. Stamina penalty applied.
```

Then put raw math in the proof drawer.

## Proof Drawer Structure

```txt
Replay Analysis
├── Inputs
│   ├── Thrower POW
│   ├── Accuracy
│   ├── Defender Dodge
│   └── Fatigue modifier
├── Roll / Check
├── Outcome
└── Secondary Effects
```

This preserves explainability while making the first read feel like sports drama.

---

# 11. Accessibility & Readability Rules

## Contrast

- Never put cyan text on bright cyan backgrounds.
- Never put orange text on orange backgrounds except very dark translucent orange.
- Table body text should stay `slate-300` or `white`.
- Muted labels should not drop below `slate-500` unless decorative.

## Color Is Not Enough

Status should use both color and label/icon.

Examples:

```txt
HOT
TIRED
OUT
STARTER
BENCH
INJ
CLUTCH
```

## Dense Tables

- Use sticky identity columns for wide roster/stat tables.
- Right-align numeric columns.
- Use tabular numbers.
- Keep row hover states strong enough to track across the screen.

---

# 12. Implementation Order

## Phase 1 — Foundation

1. Add fonts.
2. Update Tailwind config.
3. Add global CSS component classes.
4. Replace app background and root shell.
5. Remove beige/paper default surfaces.

## Phase 2 — Shared Components

1. `AppShell`
2. `BroadcastHeader`
3. `Panel`
4. `DataTable`
5. `Badge`
6. `StatBar`
7. `ScoreboardTile`
8. `TelemetryLog`
9. `TacticalSlider`

## Phase 3 — Highest-Impact Screens

1. Match Replay
2. Roster
3. Command Center
4. Tactics
5. Standings/Schedule
6. News/League Context

## Phase 4 — Polish

1. Motion states
2. Team-color accent rails
3. Match impact flashes
4. Empty states
5. Loading/skeleton states
6. Mobile/tablet pass if applicable

---

# 13. Codex / Agent Implementation Prompt

Paste this into the implementation agent:

```txt
You are implementing a UI redesign for Dodgeball Manager using the “Premium Tactical Sports Sim” design system.

Goal:
Transform the current cream/charcoal sports-management dashboard into a dark, high-contrast tactical sports sim UI while preserving dense manager information, clear controls, and transparent simulation evidence.

Core rules:
- Do not remove useful information or hide sim math.
- Do not add decorative clutter that reduces readability.
- Remove beige/paper surfaces as the default foundation.
- Use slate-950/slate-900/slate-800 as the base shell.
- Use Oswald for display/header text, JetBrains Mono for telemetry/numbers, and Inter for body/UI.
- Use cyan/orange/rose/emerald/amber as controlled accents.
- Avoid nested card soup. Prefer panels with header bands and internal dividers.
- Tables must become high-density sports sim tables with strong headers, hover states, tabular numbers, and sticky identity columns where useful.
- Match Replay must feel like a broadcast replay cockpit, not a debug panel.

Implementation sequence:
1. Inspect the repo structure and identify the styling system, routing/screens, shared components, and current global CSS/Tailwind setup.
2. Add or update font loading for Inter, Oswald, and JetBrains Mono.
3. Update Tailwind theme with font families, glow shadows, and war-room/court-grid background utilities.
4. Add global component classes for app shell, panels, nav items, badges, data typography, tables, and display typography.
5. Refactor the app shell/root layout first.
6. Refactor shared card/panel primitives so future screens inherit the new look.
7. Refactor tables next: roster, standings, schedule, and stats.
8. Refactor Match Replay into: scoreboard band, momentum/control strip, event timeline, current event spotlight, and analyst proof drawer.
9. Refactor Tactics sliders into coaching-board controls.
10. Run the app, fix visual regressions, type errors, broken imports, and layout overflow.
11. Produce a final summary of changed files, design-system components created, and any follow-up tasks.

Use this visual grammar:
- War Room Mode: Command Center, Hub, Tactics overview. Calm slate shell, cyan primary accent, orange action accent.
- Match Day Mode: Replay/live/postgame. Orange primary accent, cyan/rose secondary accents, scoreboard typography, impact moments.
- Roster Lab Mode: Roster/scouting/player development. Dense tables, stat bars, role/status badges, cyan accents.
- League Office Mode: Standings/schedule/news. Restrained database style with team-color accents.

Do not over-radicalize the UX. This is a redesign pass, not a product rewrite.
```

---

# 14. Final Design System Delta

The original system was good, but these upgrades make it implementation-safe:

1. Added screen modes so every page does not become the same dark card dashboard.
2. Added stat color mapping for consistency.
3. Added team-color rules to prevent unreadable chaos.
4. Added motion constraints so the UI feels alive but not corny.
5. Added accessibility rules.
6. Added migration priority.
7. Added concrete Tailwind/CSS/component recipes.
8. Added Match Replay structure so the best feature gets the strongest identity.

The key warning: **do not let every element glow.** The glow is the seasoning, not the whole meal. If everything is a highlight, nothing is a highlight.

