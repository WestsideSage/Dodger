# Command Center CSS Fix — Design Spec
_Date: 2026-05-18_

## Problem

GPT 5.5 added a cockpit-grid layout to PreSimDashboard with ~800 lines of new CSS.
The layout structure and color palette are acceptable; the problems are typography,
density, and panel structure. Specifically:

- Panel h3 headings are too small (inheriting 1.18rem base) — they don't read as the
  dominant content of each panel.
- Panel padding is too tight (0.8rem), making all content feel cramped.
- Approach selector buttons are undersized (min-height 2.2rem), not feeling like
  real selectable options.
- Plan editor's two-column split (Tactical Approach / Tactical Profile) has no gap,
  so the columns are flush against each other.
- Tactical profile bar stack gap (0.45rem) is too tight to scan.
- Secondary rail (bottom checklist/standings tabs) has a hard max height of 7rem
  (~112px), causing content to overflow without visible scrolling.

## Scope

CSS-only. No JSX changes. Six rules in `frontend/src/index.css`.

## Changes

| Rule | Property | Old | New |
|------|----------|-----|-----|
| `.command-cockpit-panel h3` | `font-size` | inherited 1.18rem | **1.55rem** |
| `.command-cockpit-panel` | `padding` | 0.8rem | **1rem 1.15rem** |
| `.command-cockpit-panel .command-panel-heading` | `margin-bottom` | 0.55rem | **0.9rem** |
| `.command-approach-grid button` | `min-height` | 2.2rem | **3rem** |
| `.command-plan-grid` | `gap` | (none) | **1.1rem** |
| `.command-meter-stack` | `gap` | 0.45rem | **0.7rem** |
| `.command-dashboard` grid row 3 | `minmax` | minmax(5.5rem, 7rem) | **minmax(9rem, 12rem)** |

## Out of Scope

- No JSX structural changes.
- No color, accent, or font-family changes.
- No changes to MatchCard, WeeklyChecklist, or PreSimDashboard logic.
- No responsive breakpoint changes.

## Acceptance

- Panel headings (`AGGRESSIVE`, `ADJUSTMENT ADVISED`, `READY TO DECIDE`) read as the
  dominant text in their respective panels.
- Approach buttons are tall enough to feel like selectable tiles.
- Tactical Approach and Tactical Profile columns have clear separation.
- Checklist tab shows its content without overflow.
- No regressions to aftermath view or other CSS consumers.
