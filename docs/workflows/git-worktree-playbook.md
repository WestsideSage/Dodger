# Git Worktree Playbook

Dodgeball Manager uses Git worktrees so Codex, Claude, Gemini, and review work can happen in separate folders without sharing one dirty working tree.

## Folder Layout

- Main repo: `C:\GPT5-Projects\Dodgeball Simulator`
- Codex: `C:\GPT5-Projects\Dodgeball Simulator.worktrees\codex`
- Claude: `C:\GPT5-Projects\Dodgeball Simulator.worktrees\claude`
- Gemini: `C:\GPT5-Projects\Dodgeball Simulator.worktrees\gemini`
- Review: `C:\GPT5-Projects\Dodgeball Simulator.worktrees\review`

## Branch Rules

- `main` is the stable baseline. Do not do active implementation there.
- `develop` is the integration branch for upcoming milestone work.
- Agents branch from `develop` unless Maurice gives a different base.
- Audit branches stay read-only unless Maurice explicitly authorizes implementation.

## Agent Assignments

- Codex implementation: `feature/codex-next-task`
- Claude planning/architecture: `audit/claude-planning`
- Gemini research/spec: `audit/gemini-research`
- Review/integration: `review/integration`

## Per-Worktree Dependency Bootstrap

Each agent owns dependency setup inside its assigned worktree. Maurice should not need to visit every branch or folder to prepare dependencies.

Run this from the agent's worktree when `.venv` is missing, Python tests cannot find project dependencies, or pytest is unavailable:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

Run this from the frontend folder when `frontend/node_modules/` is missing or frontend checks cannot find packages:

```powershell
cd frontend
npm install
```

Then verify:

```powershell
python -m pytest -q
cd frontend
npm run lint
npm run build
```

The expected model is shared system runtimes, separate dependencies per worktree:

- Shared: Windows Python launcher (`py`) or `python`, Node 20.19+ or 22.12+, and npm.
- Per worktree: `.venv/`, editable Python install, `frontend/node_modules/`.

Agents may install per-worktree dependencies by default. They should not use `sudo`, upgrade system runtimes, or change global Node/Python configuration unless Maurice explicitly authorizes it.

## Start A New Task Branch

From the main repo or review worktree:

```powershell
git switch develop
git pull --ff-only
git switch -c feature/<scope>
```

For an additional worktree:

```powershell
git worktree add "../Dodgeball Simulator.worktrees/<agent-or-task>" -b feature/<scope> develop
```

## Switch Branches Safely

Before switching:

```powershell
git status --short
```

If there are unrelated edits, stop and write a handoff. Do not stash or revert someone else's work unless Maurice explicitly asks.

## Sync From Develop

```powershell
git fetch origin
git switch develop
git pull --ff-only
git switch <task-branch>
git merge develop
```

If there is no remote or fetch is unavailable, merge from the local `develop` branch.

## Merge Finished Work

Use the review worktree for integration:

```powershell
git switch review/integration
git merge develop
git merge --no-ff <task-branch>
```

Run the relevant Python tests and frontend checks. If the merge changes match outcomes, verify golden logs and document the reason.

## Avoid Generated Files

Do not commit:

- local SQLite files (`*.db`, `*.sqlite`, `saves/`)
- dependency folders (`node_modules/`, `frontend/node_modules/`)
- build output (`dist/`, `build/`, `frontend/dist/`)
- caches (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`)
- logs, screenshots, videos, and `output/`

Lockfiles, source fixtures, migrations, specs, tests, and golden logs are source-controlled unless there is a clear reason not to track them.

## If The Wrong Tree Gets Dirty

1. Stop editing.
2. Record `pwd`, branch, and `git status --short`.
3. If the work is valuable, make a temporary branch from that exact state.
4. Move the change by committing/cherry-picking, or write a handoff for another agent.
5. Do not delete, clean, reset, or overwrite files to hide the mistake.

## Remote Use

If a remote exists, use normal pull/push only after confirming the target branch. If no remote exists, follow `docs/workflows/remote-setup.md`.
