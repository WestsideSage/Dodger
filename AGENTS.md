# Repository Guidelines

## Project Shape

Dodgeball Manager uses a `src/` layout. Core Python code lives in `src/dodgeball_sim/`; tests live in `tests/`; docs, specs, retrospectives, and roadmap notes live in `docs/`. The React + Vite frontend is in `frontend/`.

Important entry points:

- Web backend: `src/dodgeball_sim/server.py`
- Web launcher: `src/dodgeball_sim/web_cli.py`
- Frontend app: `frontend/`

Treat local SQLite files such as `demo.db`, `dodgeball_sim.db`, and `dodgeball_manager.db` as generated data.

## Commands

- Install Python dev environment in the current worktree:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
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

## Current Facts Worth Remembering

- `Club` is the persistent franchise entity; `Team` is the immutable match-time snapshot.
- `franchise.build_match_team_snapshot()` bridges Club/roster data into match teams.
- `MatchResult` uses `winner_team_id`, not `.winner`.
- `CoachPolicy` has 8 fields: `target_stars`, `target_ball_holder`, `risk_tolerance`, `sync_throws`, `rush_frequency`, `rush_proximity`, `tempo`, and `catch_bias`.
- Save/resume is governed by `CareerStateCursor` in `career_state.py`.
- Offseason ceremony keys are: `champion`, `recap`, `awards`, `records_ratified`, `hof_induction`, `development`, `retirements`, `rookie_class_preview`, `recruitment`, `schedule_reveal`.
- Prospect scouting progresses `UNKNOWN -> GLIMPSED -> KNOWN -> VERIFIED`; carry-forward decay happens through `apply_scouting_carry_forward_at_transition(conn, prior_class_year)`.

## Milestones

Read `docs/specs/MILESTONES.md` before milestone work.

Current orientation:

- V1 season-management foundation shipped 2026-04-26.
- V2-A through V2-F shipped 2026-04-28.
- V3 Experience Rebuild shipped 2026-04-29.
- V4 Web Architecture Foundation shipped 2026-04-29 with the web backend, React app, shared orchestration work, and first-pass parity screens. V5 planning should build on the web app as the primary product surface.

When adding a milestone, create a focused spec under `docs/specs/`, update `docs/specs/MILESTONES.md`, and add retrospective/learnings documents when it ships.

## Engineering Rules

- Keep engine behavior explainable: no hidden AI boosts, comeback code, user aura, or animation-driven outcomes.
- Do not use unseeded randomness for outcome-affecting behavior.
- Do not hardcode balance constants in engine logic when a config layer is the right place.
- Keep SQLite I/O in persistence-facing code; do not casually spread database access into pure domain modules.
- Add or update tests when behavior changes.
- Run verification appropriate to the change. Full tests are expected for broad behavior, persistence, or engine changes; focused docs-only edits do not need the full integrity harness.
- If match outcomes intentionally change, update golden logs and document why.

## Coding Style

- Python: 4-space indentation, `snake_case` functions/modules, `PascalCase` classes, explicit imports at the top.
- Prefer type hints, dataclasses, and small helpers.
- Match the surrounding style; no formatter is configured in `pyproject.toml`.
- Keep edits scoped. Avoid unrelated rewrites and metadata churn.

## Squad Notes

Use the squad model when planning a new milestone or when Maurice explicitly asks for it. Reports belong in `docs/retrospectives/`; sprint plans belong in `docs/specs/`.

Role routing, when useful:

- Architecture: Principal Systems Architect
- Balance: Lead Game Systems & Balance Analyst
- Frontend UX: Lead Front-End UX Engineer
- QA abuse testing: Adversarial QA Tester
- Debug/maintenance: Senior Debug & Maintenance Engineer
- Content/narrative: Lead Procedural Content & Narrative Designer
- Planning: Lead Technical Project Manager
- Implementation: Codex

Do not force the full squad ceremony for small fixes or routine documentation cleanup.

## Git / Worktree / Multi-Agent Workflow

Every agent starts by reading this file before touching the repo. For milestone work, also read `docs/specs/MILESTONES.md` and the relevant spec or retrospective handoff.

Branch model:

- `main`: stable baseline. Only tested, reviewed work should land here.
- `develop`: integration branch for upcoming milestone work. New task branches normally start here.
- `feature/<scope>`: implementation work.
- `fix/<bug-or-system>`: defect or system repair.
- `audit/<role>-<scope>`: read-only review, planning, or research unless Maurice explicitly authorizes implementation.
- `review/<scope>`: integration and review work.
- `chore/<repo-or-tooling>` or `docs/<scope>`: repo hygiene and documentation.

Preferred local worktrees live outside the main repo:

- `../Dodgeball Simulator.worktrees/codex` on `feature/codex-next-task`
- `../Dodgeball Simulator.worktrees/claude` on `audit/claude-planning`
- `../Dodgeball Simulator.worktrees/gemini` on `audit/gemini-research`
- `../Dodgeball Simulator.worktrees/review` on `review/integration`

Rules:

- Do not implement major work directly in the main repo folder.
- Before editing, confirm the worktree path, branch, baseline status, and intended files.
- Agents are responsible for bootstrapping their own assigned worktree dependencies when missing: create/use `.venv`, install Python dev deps, run `npm install` in `frontend/`, then verify.
- Inspect `git status --short` before and after work. Do not overwrite or revert someone else's changes.
- Keep generated files, local SQLite saves, logs, dependency folders, screenshots, videos, and cache output out of commits.
- Commit small, coherent changes with a handoff note when another agent will continue.
- The event log is canon for match outcomes. Renderers may display outcomes but must not decide them.
- No hidden boosts, rubber-banding, user aura, animation-driven outcomes, or unlogged outcome randomness.
- If outcomes intentionally change, update golden logs in the same branch and document why in the spec, learning, or handoff.

Use `docs/workflows/git-worktree-playbook.md` for the full branch/worktree process and `docs/workflows/agent-handoff-template.md` for cross-agent handoffs.
