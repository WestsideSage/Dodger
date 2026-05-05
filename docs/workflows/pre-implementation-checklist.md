# Pre-Implementation Checklist

Complete this before implementation work:

- Read `AGENTS.md`.
- Read `docs/specs/MILESTONES.md` for milestone work.
- Confirm worktree path and branch.
- Confirm the branch starts from the intended base, normally `develop`.
- Bootstrap missing worktree dependencies without waiting for Maurice:
  - Create/use `.venv`.
  - Install Python dev deps with `python -m pip install -e '.[dev]'`.
  - Run `npm install` from `frontend/` if frontend dependencies are missing.
- Do not use `sudo`, upgrade system runtimes, or change global Node/Python configuration without explicit approval.
- Run baseline tests or document why they cannot run.
- Inspect `git status --short`.
- Confirm there are no unrelated changes in the worktree.
- State the intended files or modules to modify.
- Keep commits small and coherent.
- Run relevant tests after changes.
- Update docs, specs, golden logs, or handoff notes when behavior changes.
- Leave a handoff using `docs/workflows/agent-handoff-template.md` when another agent will continue.
