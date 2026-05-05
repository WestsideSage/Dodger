# CLAUDE.md

Claude agents should read root `AGENTS.md` first. This file is only a short Claude-specific supplement.

## Useful Commands

- Install: `python -m pip install -e .[dev]`
- Test all Python: `python -m pytest -q`
- Launch web app: `python -m dodgeball_sim` or `dodgeball-manager`
- Launch web app explicitly: `python -m dodgeball_sim.web_cli` or `dodgeball-manager-web`
- Build frontend from `frontend/`: `npm run build`

## Workflow Preferences

- For non-trivial work, inspect first, then propose a short repo-grounded plan.
- For implementation, work one scoped phase at a time and verify with tests that match the risk of the change.
- Use focused tests for narrow changes; use the full Python suite and frontend build/lint when touching broad behavior or frontend code.
- Do not add dependencies, alter public APIs, or change build/routing/auth behavior without making the reason explicit.
- Do not preserve stale assumptions from old plans; check current code before acting.

## Claude-Specific Cautions

- Treat root `AGENTS.md` and `docs/specs/MILESTONES.md` as the orientation source of truth.
- Prefer search-first reading over opening huge files end to end.
- Keep plans and reports concise. Link to existing docs rather than restating them.
- When receiving a handoff, implement only the requested phase unless Maurice expands scope.

## Current Gotchas

- `MatchResult` uses `winner_team_id`.
- `CoachPolicy` has 8 fields.
- The offseason Recruitment Day key is `recruitment`.
- New player-facing work should target the web app.
