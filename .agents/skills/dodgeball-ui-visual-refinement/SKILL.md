---
name: dodgeball-ui-visual-refinement
description: Use when Dodgeball Manager work asks to implement or verify broad desktop UI/UX visual refinement, premium sports-management polish, page/panel redesign, screenshot-driven frontend QA, or app-wide visual elevation.
---

# Dodgeball UI Visual Refinement

Use this skill for broad frontend polish, desktop UI/UX elevation, and screenshot-driven visual QA.

## Operating Stance

Make the app feel like a premium desktop sports-management control room while preserving gameplay truth, repo contracts, and accessibility.

This is implementation work unless the user explicitly asks for audit-only. Section 4 is historical reference, not pending work.

## Orientation

Start from live repo truth:

1. Confirm repo path, branch, and dirty status.
2. Read `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md`.
3. Read `CLAUDE.md` when present.
4. Inspect relevant frontend source under `frontend/`, especially `frontend/src/legibility/`, shared components, CSS/theme files, route/layout structure, and existing Playwright/E2E helpers.
5. Inspect server/use-case payloads only when needed to understand real UI data.

Use Pare MCP commands where available and useful. If Pare is unavailable, unsuitable, or raw output is needed, use normal shell/git commands and state that fallback in the handoff.

## Desktop Matrix

- Primary: 1440x900.
- Stress: 1366x768.
- Minimum desktop: 1280x720.
- Large desktop polish: 1920x1080.
- Mobile optimization is out of scope unless catastrophic breakage blocks desktop-critical behavior.

## Non-Negotiables

- Do not change match outcomes, engine math, seeded randomness, player progression, signing math, standings logic, or official-rules behavior.
- Do not add hidden buffs, rubber-banding, unlogged randomness, or animation-driven outcomes.
- Do not add dependencies unless overwhelmingly justified.
- Do not invent data or overclaim official-rules behavior.
- Do not change routing/auth/build architecture unless directly required and justified.
- Preserve semantic markup, keyboard access, focus visibility, accessible names, and honest disabled/error states.
- Before making claims about code, open the relevant code. Before reporting progress, tie claims to files, screenshots, tests, or command output.

## Design Direction

Aim for sports front office command center, tournament broadcast package, court-line geometry, bracket-room pressure, scouting binder, roster lab, and war-room boards. Avoid purple-gradient SaaS sameness, random glassmorphism, unreadable stat soup, low contrast, decorative clutter, over-animation, and generic card grids.

Improve hierarchy, spacing, alignment, page composition, typography scale, density, contrast, grouping, scanability, empty/loading/error states, affordances, selected/disabled/pending states, table readability, modals, ceremony drama, replay readability, tactical editor clarity, proof-backed legibility, and accessibility.

## Workflow

1. Map the app.
   Inventory reachable pages, panels, modals, ceremonies, editors, tabs, drawers, tooltips, empty states, blocked states, loading states, and deep states. Include save/career creation, command center, pre-match, readiness, scout opponent, lineup, policy editor, roster/player modal, recruiting/scouting, dynasty office, standings, replay, aftermath, season preview, playoffs, ceremonies, records, awards, errors, and any discovered surfaces.

2. Capture before-state evidence.
   Launch the app through the supported workflow. Capture screenshots at 1440x900 and 1280x720 first, then other desktop targets as scope allows. Use real app flows or existing test/dev endpoints for deep states. Label isolated component inspection clearly.

3. Diagnose as design.
   For each major surface, identify the first thing the user should understand, the decision being asked, primary/secondary/tertiary information, grouping, desktop-space use, focal point, honest copy, disabled states, Dodgeball-specific identity, and accessibility concerns.

4. Implement visual elevation.
   Prefer shared layout primitives, CSS variables, component tokens, and reusable patterns already present in the repo. Use page-specific upgrades where a surface needs unique drama or hierarchy. Preserve data flow and behavior unless a UI bug is proven and safely fixable.

5. Verify continuously.
   Re-open the live app after batches. Compare before/after screenshots. Check no horizontal overflow at 1280x720, composition at 1440x900, large-desktop density at 1920x1080, usability at 1366x768, browser console errors, focus states, labels, contrast, and touched ARIA semantics.

## Verification

For frontend/UI changes, run `npm run build` and `npm run lint` from `frontend/`, plus targeted Playwright/E2E or browser verification for touched flows. Capture screenshot evidence at 1280x720 and 1440x900. If backend payload/copy changes are made, run focused Python tests and broader `python -m pytest -q` when shared use cases, persistence, engine-adjacent presentation, or ceremony payloads are affected.

Do not claim verification that was not run. If a state could not be reached, say so and identify the evidence you do have.

## Handoff

Provide: outcome first, files changed grouped by purpose, pages/panels verified in browser, desktop viewport results, exact tests/checks with pass/fail status, unresolved issues or unreachable states, and owner-decision taste calls separated from bugs.
