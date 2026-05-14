# Retrospectives - Historical Handoffs

This folder contains session retrospectives, audits, QA reports, and handoffs. Each file is a snapshot of project state at a decision boundary. Use these reports as evidence and history, not as the first source of current instructions.

For current orientation, read:

1. Root `AGENTS.md`
2. `docs/README.md`
3. `docs/specs/MILESTONES.md`
4. The active spec or plan named by those files

## File Naming And Organization

Retrospectives, QA reviews, and audits are organized by version when they belong to a milestone (`v1`, `v2`, `v3`, etc.). Repo-wide reports may sit directly in this folder.

```
docs/retrospectives/v[N]/YYYY-MM-DD-<topic>.md
```

## What Each Handoff Contains

- State snapshot - exactly what was built, file by file
- Test status - which tests pass, which are expected to fail
- Known issues - bugs deferred, design decisions that need follow-up
- Next steps - concrete first task the incoming agent should do
- Gotchas - non-obvious things that will cause confusion if not noted

## How To Use

1. Start from the current sources of truth above.
2. Open retrospectives only when you need the evidence behind a decision, a QA reproduction path, or a prior handoff.
3. Prefer the newest relevant report, then cross-check it against source and tests.
4. Treat old paths, old branch/worktree names, old test counts, and old component names as stale unless current docs confirm them.

## Known Historical Stale Areas

- `2026-05-05-gitification-report.md` records the old multi-worktree setup. That process is retired. Use root `AGENTS.md` and `docs/workflows/git-worktree-playbook.md` for current workflow.
- Early V1/V2 reports may mention "not a git repository"; the repo is now under git.
- Older V6/V7 reports may reference `CommandCenter.tsx` or WSL `/mnt/c/...` commands. Current Windows path and frontend component names must be verified against source.
