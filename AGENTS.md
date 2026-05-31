# IMPORTANT

ALWAYS use Pare MCP commands (a tool that returns structured JSON to help reduce token usage while preserving vital information) when necessary and where applicable. If Pare is unavailable, unsuitable for the task, or raw command output is required, fall back to normal shell/git commands and state that fallback in the handoff.

# Repository Guidelines

## Project Shape

Dodgeball Manager uses a `src/` layout. Core Python code lives in `src/dodgeball_sim/`; tests live in `tests/`; docs, specs, retrospectives, and roadmap notes live in `docs/`. The React + Vite frontend is in `frontend/`.

Important entry points:

- Web backend: `src/dodgeball_sim/server.py`
- Web launcher: `src/dodgeball_sim/web_cli.py`
- Frontend app: `frontend/`

Treat local SQLite files such as `demo.db`, `dodgeball_sim.db`, and `dodgeball_manager.db` as generated data.

## Commands

- Install Python dev environment in the current Windows worktree:
  - `py -3 -m venv .venv`
  - `.venv\Scripts\Activate.ps1`
  - `python -m pip install -U pip`
  - `python -m pip install -e '.[dev]'`
- Run Python tests: `python -m pytest -q`
- Run focused tests: `python -m pytest tests/test_invariants.py -q`
- Launch the web app: `python -m dodgeball_sim` or `dodgeball-manager`
- Launch sandbox CLI: `python -m dodgeball_sim.cli` or `dodgeball-sim`
- Launch the web app explicitly: `python -m dodgeball_sim.web_cli` or `dodgeball-manager-web`
- Install frontend dependencies from `frontend/`: `npm install`
- Build frontend from `frontend/`: `npm run build`
- Lint frontend from `frontend/`: `npm run lint`
- Run root Playwright smoke checks: `npm run e2e`

## Architecture Snapshot

The project has three main layers:

1. Engine core: `engine.py`, `models.py`, `rng.py`, `config.py`, `events.py`
   - Deterministic, no SQLite or UI ownership.
   - `MatchEngine.run()` consumes a `MatchSetup` plus seed and returns a `MatchResult`.
   - Outcome randomness should flow through `DeterministicRNG` and `derive_seed(root_seed, namespace, *ids)`.
2. Franchise/domain layer: `franchise.py`, `season.py`, `scheduler.py`, `playoffs.py`, `recruitment.py`, `recruitment_domain.py`, `scouting.py`, `scouting_center.py`, `offseason_beats.py`, `development.py`, `awards.py`, `career.py`
   - Owns season and manager rules.
   - Prefer pure helpers and explicit data flow.
3. Persistence: `persistence.py`
   - SQLite boundary.
   - Schema version is `CURRENT_SCHEMA_VERSION`; migrations run through `connect()`.

The web app is the supported foundation. `server.py` wraps the domain and persistence layers for the React client; new player-facing work should target the web surface.

## Documentation Routing & Read Order

Required read order and source-of-truth hierarchy:
1. `AGENTS.md` (this file): Durable repo rules and architecture boundaries.
2. `docs/README.md`: Documentation map.
3. `docs/STATUS.md`: Current build state, current implementation phase, and open work.
4. `docs/specs/MILESTONES.md`: Milestone history/index (not the sole source of current work).
5. Active spec / issue / handoff: Task-specific intent.
6. Source code and tests: Final authority when docs disagree.

For GitHub issue work, read `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md` before creating, labeling, closing, or triaging issues.

Model-specific files like `CLAUDE.md` and `GEMINI.md` may add workflow preferences, but they do not override root `AGENTS.md` unless Maurice explicitly says so.

**Anti-Staleness Rule:**
Do not store fast-moving implementation facts, API field lists, shipped-milestone rosters, or current-phase labels in root `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`. Put current implementation state in `docs/STATUS.md`; put milestone history in `docs/specs/MILESTONES.md`; put task-specific details in active specs/issues/handoffs.

**Document Destinations:**
- **Active specs/plans**: `docs/specs/`
- **Shipped milestone retrospectives/learnings**: follow `docs/specs/MILESTONES.md` and use `docs/retrospectives/...` plus `docs/learnings/...`. Do not let a milestone shipping agent place milestone retrospectives in `docs/archive/retrospectives/`.
- **General analysis/audit/balance reports**: `docs/archive/retrospectives/`

## Engineering Rules

- Keep engine behavior explainable: no hidden AI boosts, comeback code, user aura, or animation-driven outcomes.
- Do not use unseeded randomness for outcome-affecting behavior.
- Do not hardcode balance constants in engine logic when a config layer is the right place.
- Keep SQLite I/O in persistence-facing code; do not casually spread database access into pure domain modules.
- Add or update tests when behavior changes.
- Run verification appropriate to the change. Full tests are expected for broad behavior, persistence, or engine changes; focused docs-only edits do not need the full integrity harness.
- If match outcomes intentionally change, update golden logs and document why.
- If a reported bug/gap is already fixed, report the evidence and do not force a code change just to produce a diff.
- **Frontend / UI Matrix:** Frontend/UI work is desktop-first for now. The supported design targets are 1440x900 primary, 1366x768 desktop stress, 1280x720 minimum desktop, and 1920x1080 large-desktop polish. Mobile layouts are not a product goal unless Maurice explicitly reopens mobile support. Agents may note catastrophic mobile breakage, but should not spend implementation budget optimizing for mobile.


## Coding Style

- Python: 4-space indentation, `snake_case` functions/modules, `PascalCase` classes, explicit imports at the top.
- Prefer type hints, dataclasses, and small helpers.
- Match the surrounding style; no formatter is configured in `pyproject.toml`.
- Keep edits scoped. Avoid unrelated rewrites and metadata churn.

## Git / Main Repo / Multi-Agent Workflow

Current source of truth:

- Active local repo: `C:\GPT5-Projects\Dodgeball Simulator`
- The old external `.worktrees` checkout at `C:\GPT5-Projects\Dodgeball Simulator.worktrees\...` is retired and stale. Do not use it for implementation, planning truth, verification, or handoff state unless Maurice explicitly re-authorizes it for a specific recovery task.
- If old `.worktrees` files are referenced, treat them as historical reference only. Port by inspecting diffs and adapting to this repo; never assume those files include current main-repo changes.

Branch model:

- `main`: stable baseline. Only tested, reviewed work should land here.
- `develop`: integration branch for upcoming milestone work. New task branches normally start here.
- `feature/<scope>`: implementation work.
- `fix/<bug-or-system>`: defect or system repair.
- `audit/<role>-<scope>`: read-only review, planning, or research unless Maurice explicitly authorizes implementation.
- `review/<scope>`: integration and review work.
- `chore/<repo-or-tooling>` or `docs/<scope>`: repo hygiene and documentation.

Rules:

- Implement active work in the main repo unless Maurice explicitly asks for a fresh isolated checkout.
- Use standard Windows paths for local work. Do not set up new worktrees under `/mnt/c/...` or document WSL-only commands as the normal path.
- Before editing, confirm the repo path, branch, baseline status, and intended files.
- Agents are responsible for bootstrapping dependencies when missing: create/use `.venv`, install Python dev deps, run `npm install` in `frontend/`, then verify.
- Inspect `git status --short` before and after work. Do not overwrite or revert someone else's changes.
- Keep generated files, local SQLite saves, logs, dependency folders, screenshots, videos, and cache output out of commits.
- Commit small, coherent changes with a handoff note when another agent will continue.
- The event log is canon for match outcomes. Renderers may display outcomes but must not decide them.
- No hidden boosts, rubber-banding, user aura, animation-driven outcomes, or unlogged outcome randomness.
- If outcomes intentionally change, update golden logs in the same branch and document why in the spec, learning, or handoff.

Use `docs/workflows/git-worktree-playbook.md` for the retired-worktree warning and current main-repo workflow. Use `docs/workflows/agent-handoff-template.md` for cross-agent handoffs.
