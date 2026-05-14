# Documentation Blitz Report

Date: 2026-05-14
Role: Chief Documentation Manager

## Goal

Make the repo safer for Codex, Claude, Gemini, and future agents by defining current documentation authority, marking stale process history, and reducing the chance that historical reports override current implementation truth.

## Current Authority Stack

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/specs/MILESTONES.md`
4. The active plan/spec named by those files
5. Source code and tests

## Changes Made

- Added `docs/README.md` as the documentation front door and source map.
- Rewrote `docs/specs/MILESTONES.md` into a tighter current-phase index.
- Added `docs/design-systems/README.md` to define design-system reading order and warn that handoffs may be target-state prompts.
- Added `docs/superpowers/README.md` to separate active execution plans from historical planning artifacts.
- Added `docs/phase0/README.md` to mark Phase 0 PDFs as background archive only.
- Rewrote `docs/retrospectives/README.md` so retrospectives are evidence/history, not current marching orders.
- Replaced generic `docs/agents/domain.md` guidance with Dodgeball-specific source order and vocabulary.
- Updated `docs/specs/AGENTS.md` to point at the new documentation source map while preserving the still-valid integrity principles.
- Updated `docs/workflows/pre-implementation-checklist.md` to include `docs/README.md` for documentation/design-system work and to avoid overwriting unrelated dirty-tree changes.
- Marked the old roadmap and old gitification report as historical workflow/product snapshots.
- Added historical warnings to the early Phase 2 handoff, V7 playthrough QA, and V8-V10 chaos report where stale source-of-truth/worktree language was most likely to mislead future agents.

## Stale Material Handling

Historical files were mostly preserved because they contain useful evidence, QA paths, and decision context. The cleanup strategy is now:

- Keep historical reports when they explain why a decision happened.
- Put current instructions in short front-door docs.
- Warn agents before they enter stale historical areas.
- Avoid mass deletion that would break backlinks from specs and retrospectives.

## Prune Candidates

No files were deleted in this pass. These areas are candidates for a later, explicit archive/prune pass if Maurice wants the tree physically smaller:

- `docs/phase0/*.pdf` - large historical research artifacts. Now labeled as archive.
- Old `docs/superpowers/plans/2026-04-*` files - execution records, not active backlog.
- Old retrospective reports that only duplicate newer closeout facts and have no unique QA evidence.
- Generic issue-tracker docs under `docs/agents/` if the repo stops using those skills.

## Verification

- Confirmed active repo path and dirty worktree before editing.
- Checked current frontend component names and active Match Week aftermath structure against `frontend/src/`.
- Verified the new linked authority files exist.
- Ran `git diff --check -- AGENTS.md docs`; docs-only whitespace check passed.

## Remaining Risk

Many historical docs still contain stale commands, paths, and component names inside their original report bodies. They are now bounded by front-door guidance and targeted historical warnings, but they should not be treated as current instructions.
