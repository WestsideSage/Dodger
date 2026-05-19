# Documentation Map

The front door for Dodgeball Manager documentation. Start here, then read only
what you need. If two docs disagree, follow the authority order below.

## Authority Order

1. `AGENTS.md` (repo root) — repo rules, workflow, architecture snapshot, and
   current implementation facts.
2. `docs/README.md` — this file: where things live and what to read.
3. `docs/STATUS.md` — current build state and the live open-work backlog.
4. `docs/specs/MILESTONES.md` — the milestone history index.
5. Source code and tests — final authority when docs and code disagree.

## Directory Guide

- `docs/STATUS.md` — what is built, what is open. Read this before assuming a
  feature exists or a planned item is done.
- `docs/specs/` — current milestone authority: the milestone index
  (`MILESTONES.md`), the inherited integrity contract (`AGENTS.md`), and the
  long-range scope-control roadmap. A new milestone's spec lives here while it
  is active, then moves to `docs/archive/` once shipped.
- `docs/workflows/` — process helpers: branching, agent handoff template,
  pre-implementation checklist, and worktree/remote notes.
- `docs/agents/` — optional skill, issue-tracker, and domain notes. Subordinate
  to root `AGENTS.md`.
- `docs/archive/` — the full historical record: shipped-milestone specs,
  retrospectives, learnings, QA reviews, Phase 0 research, execution plans, and
  closed audits. Evidence and decision history, never current marching orders.

## Where New Documents Go

- Milestone specs and sprint plans (while active): `docs/specs/`.
- Retrospectives, balance reports, learnings, and other dated session
  artifacts: directly into `docs/archive/retrospectives/` or
  `docs/archive/learnings/` — they are records from birth, never active
  authority.

## Cleanup Policy

- Keep official guidance short, current, and in one canonical place.
- Source-of-truth docs stay at the top of `docs/`; dated artifacts go to
  `docs/archive/`.
- When behavior changes, update the relevant source-of-truth doc in the same
  pass as the code.
- Delete docs outright only when they are duplicated elsewhere and have no
  historical value. Otherwise archive.
