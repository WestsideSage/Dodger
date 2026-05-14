# Superpowers Plans And Specs

This folder contains execution plans produced by planning skills. These docs are useful for task execution, but they are not the repo's highest source of truth.

## Authority

- Current documentation map: `docs/README.md`
- Milestone status: `docs/specs/MILESTONES.md`
- Active UI polish control plan: `docs/superpowers/plans/2026-05-08-ux-polish/00-MAIN.md`

## How To Use These Files

- Treat dated plans as implementation artifacts for the date and branch they were written for.
- Before executing any subplan, verify the named files and current UI state in source.
- If a plan references retired worktrees, WSL-only commands, old component names, or old top-level tabs, adapt to the current Windows main repo.
- Do not treat unchecked task boxes in an old plan as current backlog unless the active plan or milestone index still names them.

## Historical Areas

- `plans/2026-04-*` and early `2026-05-*` files are mostly historical milestone execution records.
- `plans/2026-05-08-ux-polish/` is the current design-system initiative, but subplans may lag behind implementation. Use `00-MAIN.md` for intent and source/tests for reality.
- `specs/` entries here support superpowers plans and do not supersede `docs/specs/`.
