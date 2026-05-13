# Roster Lab Design System

## 1. Design Thesis

**Roster Lab should feel like:**

> “This is where I evaluate my team’s current ability, future ceiling, role fit, and match readiness.”

The page should not just show ratings. It should help the player instantly answer:

1. **Who are my best players right now?**
2. **Who has the rarest upside?**
3. **Who is ready to start?**
4. **Who is a development project?**
5. **What kind of player is this?**
6. **Where is my roster weak?**

The core improvement is separating these concepts visually:

| Concept            | Meaning                            |
| ------------------ | ---------------------------------- |
| **OVR**            | Current ability                    |
| **Potential Tier** | Future ceiling                     |
| **Archetype**      | Player identity/style              |
| **Role**           | Current team role (e.g. Starter)   |
| **Ratings**        | Skill profile                      |

That separation matters a lot. Right now, a few of these signals blur together.

> **Implementation note:** The frontend uses Tailwind CSS v4 with `@theme` tokens and `dm-` utility classes (e.g. `dm-panel`, `dm-kicker`, `dm-badge-cyan`). Raw CSS custom properties shown in this document are for design intent — translate them to the appropriate `dm-` classes or `@theme` tokens when implementing.

---

# 2. Roster Page Layout

## Recommended Desktop Structure

```txt
┌──────────────────────────────────────────────────────────────┐
│ ROSTER LAB / ROSTER                                          │
├──────────────────────────────────────────────────────────────┤
│ Team Roster Header                                           │
│ 19 Players · 66 Avg OVR · 1 Open Slot · Dev Focus: Balanced  │
│                                    [Depth Focus] [Compact]   │
├──────────────────────────────────────────────────────────────┤
│ Column Header                                                │
├──────────────────────────────────────────────────────────────┤
│ Player Rows                                                  │
│ Player Identity | Ratings | Potential | OVR | Role           │
├──────────────────────────────────────────────────────────────┤
│ Potential Tier Legend                                        │
└──────────────────────────────────────────────────────────────┘
```

## Implementation Shell

```tsx
<RosterScreen>
  <AppSidebar />

  <MainContent>
    <RosterHeader />
    <RosterToolbar />
    <RosterTable />
    <PotentialTierLegend />
  </MainContent>
</RosterScreen>
```

---

# 3. Main Hierarchy Rules

## The user should read the page in this order

```txt
Player Name → Current OVR → Potential Tier → Archetype → Key Ratings → Status
```

## Visual weight order

| Priority | Element         | Visual Weight                  |
| -------: | --------------- | ------------------------------ |
|        1 | Player name     | High                           |
|        2 | OVR             | High                           |
|        3 | Potential tier  | High, but controlled by rarity |
|        4 | Archetype badge | Medium                         |
|        5 | Role            | Medium-low                     |
|        6 | Rating bars     | Medium-low                     |

The potential tier should be **loud only when rare**. Elite gets spectacle. Everything below it gets progressively quieter.

---

# 4. Roster Header

## Purpose

The header summarizes the team state.

```tsx
<RosterHeader
  title="Team Roster"
  subtitle="Player condition, role fit, and match readiness."
  players={19}
  averageOverall={66}
  openSlots={1}
  devFocus="Balanced"
/>
```

## Visual Layout

```txt
TEAM ROSTER
Player condition, role fit, and match readiness.

19 Players    66 Avg OVR    1 Open Slot    Dev Focus: Balanced
```

## Rules

* `Players`, `Avg OVR`, and `Open Slot` are compact stat blocks.
* `Dev Focus` gets a larger pill because it affects development strategy.
* Avoid huge empty header space.
* Keep the controls on the right.

---

# 5. Roster Toolbar

## Controls

```tsx
<RosterToolbar
  depthFocus="balanced"
  viewMode="standard"
  sortBy="depth"
  filters={filters}
/>
```

Recommended controls:

```txt
[Depth Focus: Balanced v] [Sort: Depth v] [Compact View]
```

Eventually add:

```txt
[All Roles v] [Potential v] [Status v]
```

But don’t overbuild yet. The roster is already readable.

---

# 6. Player Row System

## Standard Row Layout

```txt
┌────────────────────────────────────────────────────────────────────────────┐
│ 1  [Archetype Icon]  Mika Thorn  [Playmaker]                               │
│                      Tactician · Age 31                                    │
│                                                                            │
│ Ratings: Accuracy 76  Dodge 60  Power 63  Tactical IQ 71  Catch 91         │
│                                                                            │
│ Potential: Elite 90+   Rare talent. Franchise-changing upside.              │
│                                                                            │
│ OVR 66                                      Role: Starter                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## Grid Columns

```css
.roster-row {
  display: grid;
  grid-template-columns: 64px minmax(260px, 1.2fr) minmax(420px, 1.6fr) minmax(260px, 0.9fr) 96px 120px;
  gap: 24px;
  align-items: center;
}
```

Columns:

| Column          | Purpose              |
| --------------- | -------------------- |
| #               | Roster order         |
| Player Identity | Name, archetype, age |
| Ratings         | Skill bars           |
| Potential       | Future ceiling       |
| OVR             | Current strength     |
| Role            | Team role            |

---

# 7. Roster Order Column

## Current State

The `Player` type does not carry a `depthRank` or `jerseyNumber` field. Roster order is derived from the `default_lineup` array in `RosterResponse` and the sort the player chooses.

## Recommendation

Display a simple row index based on the current sort. Use a muted `#` column header.

```txt
#
1
2
3
```

### Visual rules

* The index should be muted — it is a positional reference, not a stat.
* Only highlight the selected row.
* Index color should not compete with potential tier.

> **Aspirational:** If a `depthRank` field is added to the `Player` type in the future, consider a `D1`/`D2`/`D3` notation to distinguish depth chart position from roster sort order.

---

# 8. Archetype System

## Current Engine State

The engine defines three archetypes via `PlayerArchetype` enum:

| Archetype    | Meaning                                   |
| ------------ | ----------------------------------------- |
| **Balanced** | Well-rounded, no extreme stat skew        |
| **Power**    | Favors accuracy/power — offensive threat  |
| **Tactical** | Favors tactical_iq/dodge — evasion/reads  |

The `Player.archetype` field is a string matching one of these values.

## Archetype Color Mapping

| Archetype | Color  | Badge Class       |
| --------- | ------ | ----------------- |
| Balanced  | Cyan   | `dm-badge-cyan`   |
| Power     | Orange | `dm-badge-orange` |
| Tactical  | Purple | `dm-badge-purple` |

## Archetype Badge Rules

* Color communicates **play style**, not quality.
* Badge text shows the archetype name.
* All three archetypes should feel equal in visual weight — none implies “better.”

```tsx
<ArchetypeBadge archetype={player.archetype} />
```

> **Aspirational — expanded archetype taxonomy:** If the archetype system is expanded in the future (e.g. sub-archetypes like Sharpshooter, Enforcer, Playmaker), consider a family-based color grouping with Leadership (Gold), Creator (Cyan), Scorer (Orange), Physical (Red), Specialist (Purple), and Defender (Green) families. This would require adding an `archetypeFamily` field to the `Player` type.

---

# 9. Archetype Icons

## Rule

With only three archetypes, each gets one clear icon:

| Icon              | Archetype | Meaning              |
| ----------------- | --------- | -------------------- |
| Scale / Circle    | Balanced  | Well-rounded         |
| Bolt / Crosshair  | Power     | Offensive strength   |
| Brain / Compass   | Tactical  | Reads and evasion    |

Icons need a **legend or tooltip** — do not rely on the icon alone to communicate meaning.

```tsx
<ArchetypeBadge archetype={player.archetype} />
```

---

# 10. Potential Tier System

This is the most important refinement.

## Design Principle

> **Potential rarity should have visual falloff.**

Elite should look extravagant. High should look valuable. Solid should look normal. Developing and below should be quieter.

## Potential Tiers (Engine: `calculate_potential_tier`)

The engine defines exactly four tiers:

| Tier         | Range | Visual Weight | Description                             |
| ------------ | ----: | ------------- | --------------------------------------- |
| **Elite**    |   90+ | Legendary     | Rare talent. Franchise-changing upside. |
| **High**     | 80–89 | Strong        | High chance to become a top player.     |
| **Solid**    | 65–79 | Standard      | Reliable growth with proper reps.       |
| **Limited**  |   <65 | Muted         | Role-player ceiling.                    |

## Potential Visual Tokens

```ts
const potentialTierStyles = {
  elite: {
    label: "Elite",
    range: "90+",
    color: "#facc15",
    bg: "rgba(250, 204, 21, 0.10)",
    border: "rgba(250, 204, 21, 0.75)",
    glow: "0 0 28px rgba(250, 204, 21, 0.35)",
    icon: "crown",
    emphasis: "legendary",
  },

  high: {
    label: "High",
    range: "80–89",
    color: "#22d3ee",
    bg: "rgba(34, 211, 238, 0.07)",
    border: "rgba(34, 211, 238, 0.45)",
    glow: "0 0 12px rgba(34, 211, 238, 0.14)",
    icon: "diamond",
    emphasis: "strong",
  },

  solid: {
    label: "Solid",
    range: "65–79",
    color: "#84cc16",
    bg: "rgba(132, 204, 22, 0.035)",
    border: "rgba(132, 204, 22, 0.25)",
    glow: "none",
    icon: "chevrons",
    emphasis: "standard",
  },

  limited: {
    label: "Limited",
    range: "<65",
    color: "#94a3b8",
    bg: "rgba(148, 163, 184, 0.02)",
    border: "rgba(148, 163, 184, 0.16)",
    glow: "none",
    icon: "hexagon",
    emphasis: "low",
  },
};
```

## Potential Badge Component

The existing `PotentialBadge` component takes `tier` and `confidence` (scouting confidence as star count):

```tsx
<PotentialBadge tier={player.potential_tier} confidence={player.scouting_confidence} />
```

## Potential Badge Layout

```txt
ELITE  ★★★★
```

The tier text is colored by tier. Stars indicate scouting confidence (how certain the assessment is).

## Hard Rule

**Only Elite gets:**

* Gold
* Crown
* Glow
* Strong border
* Premium visual treatment

High can be bright, but it should not feel legendary.

Solid and below should have reduced saturation, weaker borders, and no glow.

---

# 11. OVR Display System

## Key Rule

OVR should represent **current ability only**.

Do not color OVR by potential tier.

A player can be:

* High OVR / Low Potential
* Low OVR / Elite Potential
* Mid OVR / Solid Potential

Those are different stories.

## Recommended OVR Treatment

```tsx
<OverallRating value={78} tier="teamHigh" />
```

## OVR Color Options

You can color OVR relative to current team quality:

| OVR Meaning      | Color               |
| ---------------- | ------------------- |
| Team elite       | Bright cyan / white |
| Starter quality  | Cyan                |
| Rotation quality | Muted cyan          |
| Developing       | Slate               |
| Weak             | Muted gray          |

But keep this separate from potential.

## Visual Example

```txt
OVR
78
```

Clean. Big. Readable. Not overly decorative.

---

# 12. Role Badge System

The `Player.role` field communicates the player’s **current team role** (e.g. "Starter", "Bench", "Rotation"). The specific set of role values is determined by the engine and may expand over time.

## Recommended Role Color Rules

| Role       | Color          |
| ---------- | -------------- |
| Starter    | Cyan           |
| Rotation   | Purple / slate |
| Bench      | Muted slate    |
| Captain    | Gold           |
| Injured    | Red            |

## Component

```tsx
<RoleBadge role={player.role} />
```

## Important

Do not let role badges compete with potential badges.

Role is important, but potential is the long-term roster-building signal.

---

# 13. Ratings Bar System

## Current Issue

The rating bars are readable, but color meaning can get muddy.

## Recommended Rating Groups

Use color by rating quality, not arbitrary stat type.

| Rating Value | Color            |
| -----------: | ---------------- |
|          85+ | Cyan             |
|        70–84 | Green            |
|        55–69 | Yellow           |
|          <55 | Muted orange/red |

```ts
function getRatingColor(value: number) {
  if (value >= 85) return "eliteRating";
  if (value >= 70) return "goodRating";
  if (value >= 55) return "averageRating";
  return "poorRating";
}
```

## Component

```tsx
<RatingBar label="Accuracy" value={76} />
```

## Rating Bar Layout

The six ratings from `PlayerRatings`:

```txt
Accuracy      76  ━━━━━━━━━━━
Power         63  ━━━━━━━━
Dodge         60  ━━━━━━━
Catch         91  ━━━━━━━━━━━━━
Stamina       72  ━━━━━━━━━━
Tactical IQ   71  ━━━━━━━━━━
```

## Rules

* Always show the number.
* Bars are secondary visual aids.
* Do not make bars brighter than potential badges.
* Keep the stat set consistent row-to-row.

---

# 14. Player Identity Cell

## Component

```tsx
<PlayerIdentity
  name={player.name}
  archetype={player.archetype}
  role={player.role}
  age={player.age}
/>
```

## Layout

```txt
[Balanced Icon]  Mika Thorn  [Balanced]
                 Starter · Age 31
```

## Rules

* Name is the strongest text in the row.
* Archetype badge sits next to name.
* Role and age are secondary.

---

# 15. Potential Legend

The legend is good and should stay pinned to the bottom of the table/card.

## Layout

```txt
POTENTIAL TIERS
[Gold Crown] Elite 90+    [Cyan Diamond] High 80–89    [Green] Solid 65–79    [Gray] Limited <65
```

## Legend Rules

* Use the same icons as the row badges.
* Use reduced size.
* Elite still gets gold, but smaller glow than in-row.
* Legend should be explanatory, not decorative.

---

# 16. Row Emphasis Rules

## Selected Row

Selected row gets:

```css
border-color: rgba(34, 211, 238, 0.45);
background: rgba(34, 211, 238, 0.045);
```

## Elite Potential Row

Elite row can get a subtle gold left accent or potential-cell glow.

Do **not** make the entire row gold. That gets gaudy fast.

```css
.roster-row[data-potential="elite"] {
  border-left: 2px solid rgba(250, 204, 21, 0.75);
}
```

## Starter Row

Starter status should not recolor the whole row.

Use status badge only.

---

# 17. Recommended Sorting Defaults

The default roster view should probably be:

```txt
Lineup Order → OVR → Role
```

But add other useful options:

```txt
Sort By:
- Overall
- Potential Tier
- Age
- Archetype
- Role
```

For min-max players, **Potential + Age** is a spicy option.

---

# 18. View Modes

## Standard View

Best default.

Shows:

* Identity
* Ratings
* Potential
* OVR
* Role

## Compact View

For scanning.

```txt
1  Mika Thorn   Balanced   Age 31  OVR 66  Elite  Starter
2  Quinn Novak  Power      Age 21  OVR 64  High   Rotation
```

## Detail Drawer

Eventually, clicking a row should open:

```txt
Player Detail Drawer
- Full ratings
- Traits
- Development notes
- Match history
- Training focus
- Role fit
- Injury/readiness
```

Do not cram everything into the row.

---

# 19. Data Model (Shipped Types)

> These types are the source of truth from `frontend/src/types.ts`. Design work should use these fields — do not invent fields that aren't on the API response.

## PlayerRatings

```ts
export interface PlayerRatings {
  accuracy: number;
  power: number;
  dodge: number;
  catch: number;
  stamina: number;
  tactical_iq: number;
}
```

## Player

```ts
export interface Player {
  id: string;
  name: string;
  ratings: PlayerRatings;
  traits: Omit<PlayerTraits, 'potential'>;  // growth_curve, consistency, pressure
  age: number;
  club_id: string | null;
  newcomer: boolean;
  archetype: string;        // "Balanced" | "Power" | "Tactical"
  overall: number;
  role: string;
  potential_tier: string;   // "Elite" | "High" | "Solid" | "Limited"
  scouting_confidence: number;
  weekly_ovr_history: number[];
}
```

## RosterResponse

```ts
export interface RosterResponse {
  club_id: string;
  roster: Player[];
  default_lineup: string[];
}
```

## Derived Display Data

These values are not on the API response but can be computed client-side:

| Value           | Derivation                                         |
| --------------- | -------------------------------------------------- |
| Player count    | `roster.length`                                    |
| Average OVR     | Mean of `roster[*].overall`                        |
| Lineup position | Index within `default_lineup`                      |
| Newcomer badge  | `player.newcomer === true`                         |
| OVR trend       | Computed from `weekly_ovr_history` (last N entries) |

---

# 20. Component Tree

```tsx
<RosterScreen>
  <AppSidebar activeRoute="roster" />

  <RosterMain>
    <ScreenHeader
      eyebrow="Roster Lab"
      title="Roster"
    />

    <RosterPanel>
      <RosterHeader
        title="Team Roster"
        subtitle="Player condition, role fit, and match readiness."
      />

      <RosterSummaryBar
        playerCount={19}
        averageOverall={66}
        openSlots={1}
        devFocus="balanced"
      />

      <RosterToolbar
        viewMode="standard"
        sortBy="overall"
      />

      <RosterTable>
        <RosterColumnHeader />
        {players.map(player => (
          <RosterRow key={player.id} player={player} />
        ))}
      </RosterTable>

      <PotentialTierLegend />
    </RosterPanel>
  </RosterMain>
</RosterScreen>
```

---

# 21. Implementation Priority

## Phase 1: Clarify existing screen

Build:

1. `PotentialBadge` with proper rarity falloff (already exists — refine visual treatment).
2. `ArchetypeBadge` with per-archetype color (Balanced/Power/Tactical).
3. `PotentialTierLegend` showing the 4 tiers.

This fixes the biggest visual confusion immediately.

## Phase 2: Improve roster scanning

Build:

1. `RosterToolbar`
2. Sorting by OVR / Potential / Age / Status
3. Compact View
4. Better column headers with tooltips

This makes the screen feel like a management tool.

## Phase 3: Add player depth

Build:

1. Clickable `RosterRow`
2. `PlayerDetailDrawer`
3. Training/development recommendation
4. Match readiness notes

This turns the roster into a true lab.

---

# 22. Final Design Rules

## Do

* Make **Elite Potential** feel rare and expensive.
* Use **archetype colors** to communicate player style (Balanced/Power/Tactical).
* Use **OVR** for current ability only.
* Keep ratings readable but secondary.
* Use a tier legend showing the 4 engine tiers.
* Reduce color intensity as potential tiers go down.
* Use scouting confidence stars to show assessment certainty.

## Do Not

* Make every tier equally colorful.
* Use unknown icons without a legend.
* Color OVR by potential tier.
* Let archetype badges imply quality.
* Make the whole row glow unless selected.
* Cram full player detail into the table row.
* Invent data model fields that don't exist on the API response.

# Core Rule

The Roster Lab should communicate:

> **Current value, future ceiling, and player identity are different things.**

Once the UI clearly separates those three signals, the roster screen becomes way easier to read and way more satisfying to min-max.
