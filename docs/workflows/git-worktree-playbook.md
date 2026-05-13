# Retired Worktree Playbook

The external `.worktrees` repo is retired for Dodgeball Manager.

## Current Source Of Truth

- Active repo: `C:\GPT5-Projects\Dodgeball Simulator`
- Retired stale checkout: `C:\GPT5-Projects\Dodgeball Simulator.worktrees\...`

Do not use the retired `.worktrees` folders for implementation, verification, planning truth, or handoff state unless Maurice explicitly re-authorizes that exact checkout for a recovery task.

If a task references files from the retired checkout, treat those files as historical reference only. Inspect the current main repo first, then port only the relevant changes by adapting them to the current source, tests, and docs.

## Current Branch Workflow

- `main` is the active local source of truth unless Maurice names another branch.
- Create a normal branch in the main repo when the task needs isolation.
- Keep standard Windows paths as the default working environment.
- Do not set up new worktrees under `/mnt/c/...`.
- Do not recreate `C:\GPT5-Projects\Dodgeball Simulator.worktrees` as a default workflow.

Start each task from the active repo:

```powershell
cd "C:\GPT5-Projects\Dodgeball Simulator"
git status --short
git branch --show-current
```

For a branch:

```powershell
git switch -c feature/<scope>
```

## Dependency Bootstrap

Run this from the active repo when `.venv` is missing, Python tests cannot find project dependencies, or pytest is unavailable:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e '.[dev]'
```

Run this from `frontend/` when frontend dependencies are missing:

```powershell
npm install
```

Then verify as needed:

```powershell
python -m pytest -q
cd frontend
npm run lint
npm run build
```

## If A Stale Worktree Has Valuable Work

1. Stop editing in the stale checkout.
2. Record its path, branch, and `git status --short`.
3. Inspect the active main repo for the same files and current behavior.
4. Port the smallest relevant changes into `C:\GPT5-Projects\Dodgeball Simulator`.
5. Re-run verification from the active repo.
6. Do not delete, clean, reset, or overwrite the stale checkout unless Maurice explicitly asks.

## Avoid Generated Files

Do not commit:

- local SQLite files (`*.db`, `*.sqlite`, `saves/`)
- dependency folders (`node_modules/`, `frontend/node_modules/`)
- build output (`dist/`, `build/`, `frontend/dist/`)
- caches (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`)
- logs, screenshots, videos, and `output/`

Lockfiles, source fixtures, migrations, specs, tests, and golden logs are source-controlled unless there is a clear reason not to track them.
