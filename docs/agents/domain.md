# Domain Docs

This repo does not currently use `CONTEXT.md` or ADR files as its primary domain map. Do not start by looking for generic context files.

## Read Order

1. Root `AGENTS.md`
2. `docs/README.md`
3. `docs/specs/MILESTONES.md`
4. The active spec, design-system doc, or plan named by those files
5. Relevant source and tests

## Domain Vocabulary

Use terms from the active repo guidance and code:

- `Club` is the persistent franchise entity.
- `Team` is the immutable match-time snapshot.
- `MatchResult` uses `winner_team_id`.
- `CareerStateCursor` governs save/resume state.
- `Match Week` / `Command Center` currently names the weekly management loop. Verify the active component names in source before editing.
- `Dynasty Office` owns recruiting/program-memory/staff-market surfaces from the thin V8-V10 implementation.

## Conflict Rule

When historical docs disagree with source, root `AGENTS.md`, or `docs/specs/MILESTONES.md`, treat the historical doc as evidence only and document the conflict in your handoff.
