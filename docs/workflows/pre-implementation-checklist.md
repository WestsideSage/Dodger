# Pre-Implementation Checklist

Complete this before implementation work:

- Read `AGENTS.md`.
- Read `docs/README.md` when the task touches docs, milestones, workflows, design systems, or cross-agent handoff.
- Read `docs/specs/MILESTONES.md` for milestone work.
- Confirm the active path is `C:\GPT5-Projects\Dodgeball Simulator`, not the retired `C:\GPT5-Projects\Dodgeball Simulator.worktrees\...` checkout.
- Confirm repo path and branch.
- Confirm the branch starts from the intended base. New task branches normally start from `develop`; use `main` only when Maurice or the active workflow names it.
- Confirm the path is a normal Windows path such as `C:\GPT5-Projects\...`, not a WSL `/mnt/c/...` path.
- Bootstrap missing worktree dependencies without waiting for Maurice:
  - Create/use `.venv`.
  - Activate with `.venv\Scripts\Activate.ps1` when using PowerShell.
  - Install Python dev deps with `python -m pip install -e '.[dev]'`.
  - Run `npm install` from `frontend/` if frontend dependencies are missing.
- Do not use `sudo`, upgrade system runtimes, or change global Node/Python configuration without explicit approval.
- Run baseline tests or document why they cannot run.
- Inspect `git status --short`.
- Identify unrelated changes in the worktree and avoid overwriting them.
- State the intended files or modules to modify.
- Keep commits small and coherent.
- Run relevant tests after changes.
- Update docs, specs, golden logs, or handoff notes when behavior changes.
- Leave a handoff using `docs/workflows/agent-handoff-template.md` when another agent will continue.
