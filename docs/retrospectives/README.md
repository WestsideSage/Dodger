# Retrospectives — Session Handoffs

This folder contains session retrospectives for handoffs between Claude Code and Codex (or any other implementation agent). Each file is a snapshot of project state at a decision boundary, written so the next agent can pick up cold.

## File Naming and Organization

Retrospectives, QA reviews, and audits are now organized by version (`v1`, `v2`, `v3`, `v4`) to keep the documentation structured as the project scales.

```
docs/retrospectives/v[N]/YYYY-MM-DD-phase-[N]-handoff.md
```

## What Each Handoff Contains

- **State snapshot** — exactly what was built, file by file
- **Test status** — which tests pass, which are expected to fail
- **Known issues** — bugs deferred, design decisions that need follow-up
- **Next steps** — concrete first task the incoming agent should do
- **Gotchas** — non-obvious things that will cause confusion if not noted

## How to Use (Incoming Agent)

1. Read the most recent handoff file in full (e.g., in `v4/` or `v5/`).
2. Read `docs/roadmap/revival-roadmap.md` for the full plan context.
3. Read `docs/learnings/` (also versioned) for technical gotchas before touching any module.
4. Run `python -m pytest tests/ -q` to verify baseline green before making any changes.
5. Then begin work from the "Next Steps" section of the handoff.

Do not skip step 4. The test suite is the contract.
