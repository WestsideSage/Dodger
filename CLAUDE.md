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

- Treat root `AGENTS.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md` as the orientation source of truth.
- Prefer search-first reading over opening huge files end to end.
- Keep plans and reports concise. Link to existing docs rather than restating them.
- When receiving a handoff, implement only the requested phase unless Maurice expands scope.

## Current Gotchas

See the "Current Facts Worth Remembering" section of root `AGENTS.md` for the
canonical list (e.g. `MatchResult.winner_team_id`, the 8-field `CoachPolicy`,
the `recruitment` offseason key). New player-facing work targets the web app.

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`WestsideSage/Dodger`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

This repo does not use a root `CONTEXT.md` or ADR files. The domain map is
`AGENTS.md`, `docs/README.md`, and `docs/STATUS.md`. See `docs/agents/domain.md`
for read order and vocabulary.
