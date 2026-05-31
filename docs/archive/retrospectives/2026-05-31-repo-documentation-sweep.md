# Documentation Audit and Cleanup Sweep
**Date:** 2026-05-31

## Context and Goals
A comprehensive documentation sweep was performed across the `Dodgeball Manager` repository. The primary goal was to ensure the documentation architecture enforces a single source of truth, correctly reflects the current product direction (desktop-first), and archives legacy implementation plans or reviews that were cluttering the root `docs/` and `docs/specs/` directories.

## Executive Summary of Actions
1. **Desktop-First Mandate Enforced:**
   - The Section 4 design briefs (`docs/specs/2026-05-29-section4-design-briefs/`) were preserved as active downstream implementation specs but were stripped of their hard 390x844 mobile constraints.
   - `docs/STATUS.md` was updated to emphasize the current desktop-first redesign work as the primary active follow-up.
   - A note was added to the active V15 spec (`docs/specs/2026-05-30-v15-systems-legibility/implementation-index.md`) clarifying that its viewport constraint requirements and Playwright mobile layout checks are officially superseded by the desktop-first mandate.
2. **Archived Stale/Shipped Milestones:**
   - V11, V12, and V13 specs and related extraction matrices were safely moved to `docs/archive/specs/`.
   - The playtest fix multi-phase plan and its handoff were moved to `docs/archive/plans/` and `docs/archive/retrospectives/`, respectively.
   - V11, V12, and V13 links in `docs/specs/MILESTONES.md` were successfully repointed.
3. **Cleaned Up `docs/` Root:**
   - `docs/superpowers/`, `docs/qa/`, `docs/reviews/`, and `docs/rules/` were emptied and their contents organized into standard archive directories (`docs/archive/specs/superpowers/`, `docs/archive/qa/`, `docs/archive/reviews/`, etc.).
   - The historical Claude-generated UI prototype (`docs/claude-design/`) was relocated to `docs/archive/prototypes/claude-design/` with a README clarifying it is non-canonical.
4. **Clarified Source References:**
   - Kept the USA Dodgeball Rulebook in `docs/sources/USA-Dodgeball-2026-Rulebook.pdf`.
   - Added `docs/sources/` to the canonical directory guide in `docs/README.md`.
5. **Verified Worktree Status:**
   - Verified that all remaining mentions of the retired `.worktrees` are properly contextualized as historical or as explicit "do not use" warnings in `AGENTS.md` and `docs/workflows/git-worktree-playbook.md`.

## Resulting State
- `docs/specs/` now strictly contains the active milestone(s) (`docs/specs/2026-05-30-v15-systems-legibility/` and the Section 4 briefs) plus the roadmap and milestone index.
- `docs/` root is cleanly organized per `docs/README.md`.
- Mobile constraints and retired worktree concepts are thoroughly documented as historical.
