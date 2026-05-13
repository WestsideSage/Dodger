# Dynasty Office Phase 3: Make History Intentional

**Depends on:** Phase 2 complete (DynastyOfficeHeader, DynastyTabs exist)

**Design system reference:** `docs/design-systems/Dynasty-Office-Design-System.md`, sections 9–11

---

## Goal

Turn the History tab from a placeholder dashboard into dynasty storytelling — program arc, alumni legacy, and a trophy shelf that makes even a young program feel like it has a story.

---

## What exists today

The history tab in `DynastyOffice.tsx` renders two existing components:

- `MyProgramView` (`frontend/src/components/dynasty/MyProgramView.tsx`) — rebuilt with hero strip, MilestoneTree, alumni, and banners (per recent commit `cbaf2f5`)
- `LeagueView` (`frontend/src/components/dynasty/LeagueView.tsx`) — rebuilt with dynasty rankings, HoF, rivalries, and program modal (per recent commit `8e8529b`)

These components were recently rewritten and already contain:
- `MilestoneTree` — program milestone timeline
- `AlumniLineage` sub-component
- `BannerShelf` sub-component
- A scope toggle between My Program and League views

**Current gaps:**
- No "How It Started / Today" summary cards at the top
- The program arc timeline may need refinement for the design system's horizontal layout vision
- Empty states may use debug language
- The components were built before the design system was finalized — they may not match the visual spec

---

## What to build

### 1. `ProgramSummaryCards`

**New file:** `frontend/src/components/dynasty/ProgramSummaryCards.tsx`

Two side-by-side cards showing program origin vs. current state.

**Props:**
```ts
{
  started: {
    season: number;
    record: string;
  };
  current: {
    season: number;
    week: number;
    record: string;
    avgOverall: number;
  };
}
```

**Layout:**
```
┌─────────────────────────┐  ┌─────────────────────────┐
│ HOW IT STARTED           │  │ TODAY                    │
│ Season 1                 │  │ Season 1 · Week 3       │
│ Record: 0-0-0            │  │ Record: 1-1-0            │
│                          │  │ Avg OVR: 61.6            │
└─────────────────────────┘  └─────────────────────────┘
```

**Rules:**
- Two equal-width cards in a row
- "HOW IT STARTED" uses `dm-kicker` label
- "TODAY" card gets a stronger border (`rgba(34, 211, 238, 0.35)`) to mark the current point
- Both use `dm-panel` background
- "Started" record should reflect the very first season's initial record (0-0-0 for a new program)

**Data source:** The program milestones (from `MyProgramView`) should include a "founded" milestone. Derive `started.season` from the first milestone. The `current` values come from the command-center context (fetched in Phase 2) and `RosterResponse` for avg OVR.

### 2. Audit and refine `MyProgramView`

**Edit:** `frontend/src/components/dynasty/MyProgramView.tsx`

Review the existing component against the design system:

- **ProgramArcTimeline:** Ensure the milestone timeline uses horizontal layout on desktop (per design system §10C). If currently vertical, add a horizontal variant.
- **AlumniLineage:** Verify the empty state uses front-office language: "No departed players yet. Your program's player legacy will appear here after roster turnover."
- **BannerShelf:** Verify the empty state: "Earn banners through championships, undefeated seasons, rivalry wins, and milestone achievements."
- **Kicker labels:** Ensure section headers use `dm-kicker` class ("PROGRAM ARC", "ALUMNI LINEAGE", "BANNER SHELF")

### 3. Audit `LeagueView`

**Edit:** `frontend/src/components/dynasty/LeagueView.tsx`

Review against the design system:
- League history should show champions by year, MVPs, and dynasty rankings
- Should feel separate from "My Program" — no mixing of personal and league content
- Verify empty states use appropriate language

### 4. Wire `ProgramSummaryCards` into history tab

**Edit:** `frontend/src/components/DynastyOffice.tsx`

Add `ProgramSummaryCards` above the existing `MyProgramView` when the scope toggle is on "My Program":

```tsx
{activeTab === 'history' && (
  <>
    {scopeToggle}
    {scope === 'my-program' && (
      <>
        <ProgramSummaryCards started={...} current={...} />
        <MyProgramView ... />
      </>
    )}
    {scope === 'league' && <LeagueView ... />}
  </>
)}
```

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/dynasty/ProgramSummaryCards.tsx` | Create |
| `frontend/src/components/dynasty/MyProgramView.tsx` | Audit — refine timeline layout, empty states, kicker labels |
| `frontend/src/components/dynasty/LeagueView.tsx` | Audit — verify empty states and separation from My Program |
| `frontend/src/components/DynastyOffice.tsx` | Edit — wire ProgramSummaryCards into history tab |

---

## What NOT to build

- Interactive timeline (clickable milestones that open detail) — future feature
- Banner unlocking animations — future feature
- Alumni player detail drawer — future feature
- League history search/filter — future feature
