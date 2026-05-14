# Documentation Source Map

This file is the documentation front door for Dodgeball Manager. If two docs disagree, use this order of authority.

## Current Sources Of Truth

1. `AGENTS.md` - repo rules, active path, workflow, architecture snapshot, and current implementation facts.
2. `docs/specs/MILESTONES.md` - milestone status and the current product phase.
3. Active plan/spec for the current work:
   - Command Center / UX polish initiative: `docs/superpowers/plans/2026-05-08-ux-polish/00-MAIN.md`
   - Design-system references: `docs/design-systems/README.md`
4. Source code and tests - final authority when docs and implementation disagree.

## Current Implementation Snapshot

- Active repo: `C:\GPT5-Projects\Dodgeball Simulator`.
- Retired external worktrees under `C:\GPT5-Projects\Dodgeball Simulator.worktrees\...` are historical only.
- Product foundation: web backend plus React/Vite frontend.
- Current UI work is post-V8-V10 polish, with Command Center / Match Week work in progress before the remaining design-system passes.
- The current frontend has `MatchWeek.tsx`, `DynastyOffice.tsx`, `Roster.tsx`, `LeagueContext.tsx`, `MatchReplay.tsx`, and split Command Center aftermath components under `frontend/src/components/match-week/`.
- Do not treat older references to `CommandCenter.tsx`, the Tkinter GUI, WSL paths, or the retired external worktrees as current implementation instructions unless a current source explicitly revives them.

## Directory Guide

- `docs/specs/` - milestone specs and the milestone index. Current milestone truth lives here.
- `docs/superpowers/` - execution plans and planning artifacts. These are perishable unless named as active by this file or `MILESTONES.md`.
- `docs/design-systems/` - visual and UX contracts for the design-system push. See its README before using any individual file.
- `docs/retrospectives/` - historical handoffs, audits, QA reports, and session closeouts. Useful evidence, not current marching orders.
- `docs/learnings/` - durable technical lessons from prior implementation.
- `docs/workflows/` - workflow helpers for branching, handoff, and dependency/bootstrap behavior.
- `docs/roadmap/` and `docs/phase0/` - historical product context. Do not use as current implementation authority.
- `docs/agents/` - optional skill/issue-tracker integration notes, subordinate to root `AGENTS.md`.

## Cleanup Policy

- Keep official guidance short and current.
- Prefer one canonical index over repeated summaries.
- Preserve historical reports when they explain why a decision was made, but label them as historical if they contain stale paths, stale file names, or obsolete process guidance.
- Delete or consolidate docs only when the information is duplicated elsewhere and has no historical value.
- When behavior changes, update the active source of truth in the same pass as the code or leave a dated handoff explaining the gap.
