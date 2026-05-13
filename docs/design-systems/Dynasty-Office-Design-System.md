# Dynasty Office Design System

## 1. Design Thesis

**Dynasty Office should feel like:**

> “This is where I manage the long-term identity, talent pipeline, staff, and legacy of my dodgeball program.”

It should not feel like a menu page. It should feel like an **athletic department dashboard**.

> **Implementation note:** The frontend uses Tailwind CSS v4 with `@theme` tokens and `dm-` utility classes (e.g. `dm-panel`, `dm-kicker`, `dm-badge-cyan`). Raw CSS custom properties shown in this document are for design intent — translate them to the appropriate `dm-` classes or `@theme` tokens when implementing.

The player should instantly understand:

1. **Who is my program?**
2. **How credible are we?**
3. **Who are we recruiting?**
4. **What resources do I have this week?**
5. **How has the program evolved over time?**

The page is not just information. It is the **dynasty brain**.

---

# 2. Core Information Architecture

## Dynasty Office contains two primary tabs

```txt
Dynasty Office
├── Recruit
└── History
```

This is correct.

I would not split recruiting into its own sidebar route yet. Keep it inside Dynasty Office because it reinforces that recruiting is a program-building activity, not a standalone mini-game.

## Shared page shell

Both tabs should share the same top identity area:

```txt
┌─────────────────────────────────────────────────────────────┐
│ DYNASTY OFFICE                                              │
│ Autopsy Comets / Northwood Ironclads                        │
│ Season 1 · Week 0                                           │
│ [Program Settings]                                          │
├─────────────────────────────────────────────────────────────┤
│ Recruit | History                                           │
└─────────────────────────────────────────────────────────────┘
```

This makes the page feel stable. The user changes **workspace**, not destination.

---

# 3. Shared Layout System

## Desktop shell

```txt
┌────────────┬────────────────────────────────────────────────┐
│ Sidebar    │ Dynasty Office Header                         │
│            ├────────────────────────────────────────────────┤
│            │ Tabs                                           │
│            ├────────────────────────────────────────────────┤
│            │ Current Tab Content                            │
└────────────┴────────────────────────────────────────────────┘
```

## Main content sizing

```css
.dynasty-content {
  max-width: 1480px;
  margin: 0 auto;
  padding: 28px 32px 40px;
}
```

Do **not** let the content stretch endlessly across ultrawide screens. That is how pages start looking like abandoned parking lots.

---

# 4. Shared Visual Tokens

Use the same tokens as Match Replay, but add a few Dynasty-specific semantic tokens.

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
  --accent-green: #22c55e;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;

  --recruit-strong-fit: #22c55e;
  --recruit-good-fit: #84cc16;
  --recruit-risk: #facc15;
  --recruit-poor-fit: #ef4444;

  --credibility-low: #ef4444;
  --credibility-mid: #facc15;
  --credibility-high: #22c55e;
}
```

## Color rules

| Meaning                     | Color       |
| --------------------------- | ----------- |
| System labels / active tabs | Cyan        |
| Primary action              | Orange      |
| Strong recruit fit          | Green       |
| Risk / warning              | Yellow      |
| Poor fit / blocked action   | Red         |
| Historical milestones       | Blue / cyan |
| Locked/empty legacy items   | Muted slate |

Big rule: **do not use cyan for everything.** Cyan is your UI identity color. Green is for fit. Orange is for action.

---

# 5. Dynasty Office Shared Components

## `DynastyOfficeHeader`

Purpose: establishes program identity and season context.

```tsx
<DynastyOfficeHeader
  programName="Autopsy Comets"
  season={1}
  week={0}
  logoUrl={program.logoUrl}
  onOpenSettings={openSettings}
/>
```

### Visual structure

```txt
[Logo] DYNASTY OFFICE
       AUTOPSY COMETS
       Season 1 · Week 0

       [Program Settings]
```

Use this on both Recruit and History.

---

## `DynastyTabs`

```tsx
<DynastyTabs
  activeTab="recruit"
  tabs={[
    { id: "recruit", label: "Recruit" },
    { id: "history", label: "History" }
  ]}
/>
```

### Rules

* Active tab gets cyan underline.
* Inactive tab uses muted text.
* Tabs should sit under the program header, not float randomly.

---

# 6. Recruit Page Design System

## Recruit Page Goal

The recruiting page should answer:

> “Who should I spend my limited recruiting actions on this week?”

Not:

> “Here is a massive scroll tube of names. Good luck, bozo.”

The big improvement is turning the list into a **Recruit Board**.

---

## Recruit Page Layout

```txt
┌─────────────────────────────────────────────────────────────┐
│ Top Summary Cards                                           │
│ [Program Credibility] [Weekly Recruiting Slots]             │
├───────────────┬───────────────────────────────┬─────────────┤
│ Filters       │ Recruit Board                 │ Staff Room  │
│               │ Card Grid / Table Toggle      │             │
└───────────────┴───────────────────────────────┴─────────────┘
```

Recommended desktop columns:

```css
.recruit-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 280px;
  gap: 20px;
}
```

On smaller screens:

```css
.recruit-layout {
  grid-template-columns: 1fr;
}
```

---

# 7. Recruit Page Components

## A. `ProgramCredibilityCard`

```tsx
<ProgramCredibilityCard
  tier="C"
  score={61}
  reasons={[
    "5 command-history wins and 3 losses.",
    "0 youth-development command weeks.",
    "Club prestige score 0."
  ]}
/>
```

### Visual rules

* Tier is large.
* Score is secondary.
* Reasons are compact bullets.
* Use color only for the tier.

```txt
PROGRAM CREDIBILITY

Tier C
Score 61

+ 5 command-history wins and 3 losses.
+ 0 youth-development command weeks.
+ Club prestige score 0.
```

This card should be informative but not giant.

---

## B. `RecruitingSlotsCard`

The API returns budget as `[used, max]` tuples:

```tsx
<RecruitingSlotsCard
  scout={recruiting.budget.scout}   // [0, 3]
  contact={recruiting.budget.contact} // [0, 5]
  visit={recruiting.budget.visit}    // [0, 1]
/>
```

### Visual rules

Display as three compact resource counters:

```txt
WEEKLY RECRUITING SLOTS

Scout      0 / 3
Contact    0 / 5
Visit      0 / 1
```

This should be visible at all times near the top. Recruiting is fundamentally a resource allocation screen.

---

## C. `RecruitFilterPanel`

This replaces the “scroll forever and suffer” problem.

```tsx
<RecruitFilterPanel
  filters={filters}
  onChange={setFilters}
  onClear={clearFilters}
/>
```

Recommended filters (based on available prospect fields):

```ts
type RecruitFilters = {
  search: string;              // matches prospect name, hometown
  archetype: string | "any";   // public_archetype: "Balanced" | "Power" | "Tactical"
  minFitScore: number;         // fit_score threshold
  hasPromise: boolean | null;  // filter by active_promise presence
};
```

> **Note:** Prospects expose `public_ovr_band` (a `[min, max]` range) rather than a precise overall, and `fit_score` rather than a named fit tier. Filtering by OVR band range is possible but should present as a range slider, not exact values.

### Filter layout

```txt
FILTERS                         Clear

Search
[ name, hometown... ]

Archetype
[ All Archetypes ]

Fit Score
Min ━━━━━━━━━━━━━ Max

Promise Status
[ Any ]

[ Apply Filters ]
```

### UX critique

Do **not** make the player scroll through 40 cards just to find “best player who fits my team.”

That is spreadsheet brain. Recruit board brain is: **filter, sort, shortlist, act.**

---

## D. `RecruitBoard`

This is the main replacement for the giant vertical list.

```tsx
<RecruitBoard
  recruits={filteredRecruits}
  sortBy={sortBy}
  viewMode="grid"
  selectedRecruitId={selectedRecruitId}
  onSelectRecruit={setSelectedRecruitId}
/>
```

### Board header

```txt
RECRUIT BOARD      12 RESULTS              Sort By: Overall v
[ Grid ] [ Compact ] [ Scouted ]
```

You want **view modes** eventually:

1. **Grid** — default, best visual experience.
2. **Compact table** — best for min-max players.
3. **Shortlist** — only players the user has marked.

For now, implement grid first.

---

## E. `RecruitCard`

This is the money component.

Props come from `DynastyOfficeResponse.recruiting.prospects[*]`:

```tsx
<RecruitCard
  name={prospect.name}
  hometown={prospect.hometown}
  archetype={prospect.public_archetype}       // "Balanced" | "Power" | "Tactical"
  ovrBand={prospect.public_ovr_band}          // [min, max]
  fitScore={prospect.fit_score}
  promiseOptions={prospect.promise_options}
  activePromise={prospect.active_promise}
  interestEvidence={prospect.interest_evidence}
/>
```

### Card structure

```txt
┌──────────────────────────────┐
│ [Icon] AVERY HELIX     OVR   │
│        Bishop · Balanced     │
│                       75-85  │
│                              │
│ Fit Score              82    │
│ Interest: Shows interest     │
│                              │
│ [Scout] [Contact] [Visit]    │
└──────────────────────────────┘
```

> **Note:** `public_ovr_band` is a range `[min, max]`, not a single number. Display it as a range (e.g. "75–85") to reflect scouting uncertainty.

### Why this fixes the UX

Instead of each recruit consuming a full horizontal slab, each recruit becomes a **decision card**. You can see 6–12 prospects above the fold depending on resolution.

That is the correct move.

---

## F. `RecruitFitBadge`

The API provides `fit_score` as a numeric value. Derive a display tier client-side:

```tsx
<RecruitFitBadge fitScore={prospect.fit_score} />
```

Recommended tier mapping:

```ts
function getFitTier(score: number) {
  if (score >= 80) return { label: "Strong Fit", color: "green" };
  if (score >= 60) return { label: "Good Fit", color: "lime" };
  if (score >= 40) return { label: "Neutral", color: "slate" };
  if (score >= 20) return { label: "Risk", color: "yellow" };
  return { label: "Poor Fit", color: "red" };
}
```

Important: **fit should be more visually important than raw overall** once the player understands the game.

That reinforces the sim philosophy: context > raw number.

---

## G. `RecruitActions`

```tsx
// Budget tuples are [used, max] — remaining = max - used
<RecruitActions
  prospectId={prospect.player_id}
  canScout={budget.scout[1] - budget.scout[0] > 0}
  canContact={budget.contact[1] - budget.contact[0] > 0}
  canVisit={budget.visit[1] - budget.visit[0] > 0}
  onScout={handleScout}
  onContact={handleContact}
  onVisit={handleVisit}
/>
```

### Rules

* Disabled actions should explain why on hover.
* The highest-value action available can get subtle emphasis.
* Do not make all three buttons orange.
* Scout/contact/visit should be secondary buttons unless this recruit is selected.

Recommended:

```txt
[Scout] [Contact] [Visit]
```

Selected card:

```txt
[Scout] [Contact] [Schedule Visit]
```

Only **Schedule Visit** can use orange if it is the major action.

---

## H. `StaffRoomCard`

This right rail is good. Keep it.

The API provides `staff_market.current_staff` with `department`, `name`, `rating_primary`, `rating_secondary`, and `voice`:

```tsx
<StaffRoomCard staff={dynastyData.staff_market.current_staff} />
```

### Visual rules

* Staff names should be readable.
* Departments should be tiny cyan/muted labels.
* Put `Staff Market` at the bottom.
* This card should not compete with the recruit board.

---

# 8. Recruit Page Interaction Rules

## Rule 1: No infinite page-length recruiting list

Use:

* Card grid
* Filters
* Sort
* Pagination or virtualized scroll inside the board

Not:

* Full-page vertical slabs forever

Better:

```txt
Showing 1–12 of 43 recruits
[Previous] [1] [2] [3] [4] [Next]
```

or:

```txt
Recruit board scrolls internally while page shell stays stable.
```

## Rule 2: Top prospects should be visible without scrolling

Default sort should probably be:

```txt
Fit Score desc, Overall desc
```

Not just OVR. This gives the game more identity.

## Rule 3: Selecting a recruit should open detail, not expand the whole page

Eventually:

```txt
Click recruit card → right-side drawer opens
```

Drawer contains:

* Full stats
* Interest factors
* Personality/scouting notes
* Fit explanation
* Recruit history
* Actions

Do not expand cards vertically in the grid unless you want layout chaos.

## Rule 4: Add shortlist eventually

This would be huge:

```txt
[☆ Shortlist]
```

Then a player can create a personal recruiting board.

That is how you kill scroll fatigue.

---

# 9. History Page Design System

## History Page Goal

The history page should answer:

> “What is the story of this program over time?”

Right now it has the right idea, but it feels too empty. The redesign should make even a young program feel like it has an arc.

---

## History Page Layout

```txt
┌─────────────────────────────────────────────────────────────┐
│ Program Summary Cards                                      │
│ [How It Started] [Today]                                   │
├─────────────────────────────────────────────────────────────┤
│ Program Arc Timeline                                       │
├──────────────────────────────┬──────────────────────────────┤
│ Alumni Lineage               │ Banner Shelf                 │
└──────────────────────────────┴──────────────────────────────┘
```

---

# 10. History Page Components

## A. `HistoryScopeToggle`

```tsx
<HistoryScopeToggle value="my-program" />
```

```txt
[ My Program ] [ League ]
```

Good. Keep this.

### Rule

* `My Program` shows your dynasty arc.
* `League` shows league-wide champions, dynasties, awards, historic records.

Do not mix these on one page.

---

## B. `ProgramSummaryCards`

```tsx
<ProgramSummaryCards
  started={{
    season: 1,
    record: "1-1-0"
  }}
  current={{
    season: 1,
    week: 3,
    record: "1-1-0",
    avgOverall: 61.6
  }}
/>
```

### Visual structure

```txt
HOW IT STARTED
Season 1
1-1-0

TODAY
Season 1 · Week 3
1-1-0
AVG OVR 61.6
```

The “today” card should have a stronger border. It represents the current point in the timeline.

---

## C. `ProgramArcTimeline`

This should be the hero of the History tab.

```tsx
<ProgramArcTimeline
  milestones={[
    {
      id: "season-start",
      label: "Season 1",
      sublabel: "0-1-0",
      type: "start"
    },
    {
      id: "week-2",
      label: "Week 2",
      sublabel: "1-1-0",
      type: "win"
    },
    {
      id: "now",
      label: "Now",
      sublabel: "1-1-0 · First Win",
      type: "current"
    }
  ]}
/>
```

### Visual rules

* Horizontal timeline on desktop.
* Vertical timeline on mobile.
* Current moment gets cyan glow.
* Big accomplishments get bigger nodes.
* Empty early-program state is okay, but make it intentional.

```txt
PROGRAM ARC

Season 1 ───────── Week 2 ───────── Now
0-1-0              1-1-0            First Win
```

This is way better than a tiny floating line in a giant empty rectangle.

---

## D. `AlumniLineageCard`

```tsx
<AlumniLineageCard alumni={departedPlayers} />
```

Empty state:

```txt
ALUMNI LINEAGE

No departed players yet.
Your program’s player legacy will appear here after roster turnover.
```

Make the empty state feel designed, not missing.

---

## E. `BannerShelf`

```tsx
<BannerShelf banners={banners} />
```

Empty state:

```txt
BANNER SHELF

Earn banners through championships, undefeated seasons, rivalry wins, and milestone achievements.
```

This is a great long-term dynasty motivator.

Eventually banner types could be:

```ts
type BannerType =
  | "championship"
  | "undefeated_season"
  | "rivalry_title"
  | "first_win"
  | "recruiting_class"
  | "defensive_masterclass"
  | "program_milestone";
```

This gives your game a trophy-room feeling.

---

# 11. History Page Interaction Rules

## Rule 1: History should never feel empty

Even early in a save, show:

* First match
* First win
* Current week
* Current record
* Best player so far
* Program identity snapshot

Empty does not mean blank. Empty means **future legacy space**.

## Rule 2: Timeline should be milestone-based, not week-spam

Do not add every week to the main timeline.

Only add meaningful events:

* First win
* First shutout
* First recruit signed
* First winning season
* First championship
* Rivalry win
* Star player graduation
* Coach/staff milestone

## Rule 3: League history should be separate

League history can show:

* Champions by year
* MVPs
* Best teams
* Worst collapses
* Records

But do not clutter `My Program`.

---

# 12. Data Models (Shipped Types)

> These types come from `DynastyOfficeResponse` in `frontend/src/types.ts`. Design work should use these fields.

## Prospect (from `recruiting.prospects[*]`)

```ts
{
  player_id: string;
  name: string;
  hometown: string;
  public_archetype: string;       // "Balanced" | "Power" | "Tactical"
  public_ovr_band: number[];      // [min, max] range
  fit_score: number;
  promise_options: string[];
  active_promise: { promise_type: string; status: string } | null;
  interest_evidence: string[];
}
```

## Recruiting Budget (from `recruiting.budget`)

```ts
{
  scout: [number, number];    // [used, max]
  contact: [number, number];
  visit: [number, number];
}
```

## Credibility (from `recruiting.credibility`)

```ts
{
  score: number;
  grade: string;          // letter grade like "C"
  evidence: string[];
}
```

## Staff (from `staff_market.current_staff[*]`)

```ts
{
  department: string;
  name: string;
  rating_primary: number;
  rating_secondary: number;
  voice: string;
}
```

## Program history

```ts
export type ProgramMilestone = {
  id: string;
  season: number;
  week?: number;
  title: string;
  subtitle?: string;
  type:
    | "founded"
    | "first_win"
    | "championship"
    | "rivalry"
    | "recruiting"
    | "player"
    | "current";
  record?: string;
};
```

## Banner

```ts
export type ProgramBanner = {
  id: string;
  title: string;
  season: number;
  type:
    | "championship"
    | "undefeated"
    | "rivalry"
    | "milestone"
    | "development";
  description?: string;
};
```

---

# 13. Component Tree

## Recruit tab

```tsx
<DynastyOfficeScreen>
  <AppSidebar />

  <DynastyMain>
    <DynastyOfficeHeader />
    <DynastyTabs activeTab="recruit" />

    <RecruitSummaryRow>
      <ProgramCredibilityCard />
      <RecruitingSlotsCard />
    </RecruitSummaryRow>

    <RecruitWorkspace>
      <RecruitFilterPanel />
      <RecruitBoard>
        <RecruitBoardToolbar />
        <RecruitCardGrid>
          <RecruitCard />
          <RecruitCard />
          <RecruitCard />
        </RecruitCardGrid>
      </RecruitBoard>
      <StaffRoomCard />
    </RecruitWorkspace>
  </DynastyMain>
</DynastyOfficeScreen>
```

## History tab

```tsx
<DynastyOfficeScreen>
  <AppSidebar />

  <DynastyMain>
    <DynastyOfficeHeader />
    <DynastyTabs activeTab="history" />

    <HistoryScopeToggle />

    <ProgramSummaryCards />

    <ProgramArcTimeline />

    <HistoryLowerGrid>
      <AlumniLineageCard />
      <BannerShelf />
    </HistoryLowerGrid>
  </DynastyMain>
</DynastyOfficeScreen>
```

---

# 14. Implementation Priority

## Phase 1: Replace the recruiting list

Build these first:

1. `RecruitBoard`
2. `RecruitCard`
3. `RecruitFilterPanel`
4. `RecruitingSlotsCard`

This fixes the worst UX immediately.

## Phase 2: Stabilize Dynasty Office shell

Build:

1. `DynastyOfficeHeader`
2. `DynastyTabs`
3. Shared `Panel`
4. Shared `StatCard`

This makes Recruit and History feel like siblings.

## Phase 3: Make History feel intentional

Build:

1. `ProgramSummaryCards`
2. `ProgramArcTimeline`
3. `AlumniLineageCard`
4. `BannerShelf`

This turns the History page from “placeholder dashboard” into actual dynasty storytelling.

---

# 15. The Big Critique

The current Dynasty Office is not conceptually bad. It is actually aimed in the right direction.

The real problem is:

> **The UI is treating long-term dynasty systems like raw database rows.**

Recruiting should feel like a **board**.

History should feel like a **legacy wall**.

Staff should feel like a **support department**.

Program credibility should feel like a **reputation report**.

Once those mental models are separated, the page gets way cleaner immediately.

The implementation goal should be:

> **Turn Dynasty Office into a stable shell with two polished workspaces: Recruit Board and Program Legacy.**

That is the sauce.
