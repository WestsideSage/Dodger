# Branch Naming

Use clear branch names that describe the work and the level of authority.

- `feature/<scope>`: implementation work, for example `feature/codex-next-task`.
- `fix/<bug-or-system>`: targeted repair, for example `fix/replay-report-state`.
- `audit/<role>-<scope>`: read-only review or planning, for example `audit/claude-planning`.
- `review/<scope>`: integration and review, for example `review/integration`.
- `chore/<repo-or-tooling>`: repo hygiene, setup, or tooling.
- `docs/<scope>`: documentation-only work.

Keep names lowercase, use hyphens between words, and avoid names tied only to dates unless the date is part of a published milestone.
