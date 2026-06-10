---
name: dodgeball-milestone-planner
description: Use when Dodgeball Manager work asks for next-milestone planning, scope strategy, roadmap choices, sprint-plan writing, candidate prioritization, or deciding what to build next from live repo truth.
---

# Dodgeball Milestone Planner

Use this skill for product direction, milestone selection, and sprint-plan writing.

## Operating Stance

Answer the core question: what is the highest-leverage next milestone that makes Dodgeball Manager more playable, trustworthy, fun, and closer to its product promise without widening scope into chaos?

This is planning work. Do not implement code unless the user explicitly changes the request after the plan.

## Orientation

Start from live repo truth:

1. Confirm repo path, branch, and dirty status.
2. Read `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md`.
3. Read `CLAUDE.md` and `docs/specs/long-range-playable-roadmap.md`.
4. Read recent specs, retrospectives, audits, and playtest reports only when relevant.
5. Inspect source/tests only where needed to verify whether a proposed milestone is already done or feasible.

Use Pare MCP commands where available and useful. If Pare is unavailable, unsuitable, or raw output is needed, use normal shell/git commands and state that fallback in the handoff.

## Non-Negotiables

- Do not infer current phase from stale docs.
- Do not reopen Section 4 as pending.
- Do not propose unrelated new systems because they sound interesting.
- Do not produce a giant monolithic milestone.
- Do not duplicate shipped work.
- Do not bury risks.
- Do not use vague tasks like "improve UX" or "balance game" without concrete acceptance criteria.
- Do not plan work that violates the integrity contract.

## Candidate Directions

Evaluate, as relevant:

- Game systems refinement: tactics, lineup consequence, AI depth, scouting truth, recruiting tension, development pacing, dynasty parity.
- Match watchability: replay clarity, moment selection, broadcast pacing, aftermath truth, playoff drama, tactical feedback.
- First-hour retention: onboarding, career creation, first command loop, first match, first aftermath, first offseason.
- Trust and integrity: fake/no-op decisions, stale docs, official-rules overclaims, missing tests, edge failures.
- Long-term dynasty depth: season 2+ motivation, records/awards/rivalries, staff/program loops, player identity, AI league health.
- Official live rules only if unresolved rule parameters can be handled honestly.

## Workflow

1. Establish current truth.
   Summarize what is actually shipped, what is explicitly open, and which historical docs should not drive planning.

2. Score candidate milestones.
   Use explicit scoring for player impact, trust impact, implementation risk, testability, scope containment, dependency risk, and alignment with current direction.

3. Choose one primary milestone.
   Keep it narrow enough to ship. Define in scope, out of scope, prerequisites, and deferred temptations.

4. Write an implementation-ready plan.
   Include current state, readiness verdict, goals, non-goals, at-risk/deferred scope, ordered atomic tasks, acceptance criteria, verification plan, rollback/safety notes, and a first implementation handoff prompt.

5. Save only when asked.
   If asked to write a file, create the plan under `docs/specs/YYYY-MM-DD-<slug>-sprint-plan.md`. Otherwise, output the plan only.

## Handoff

Provide: current-state summary, candidate comparison table, recommended milestone, why it beats alternatives, in-scope/out-of-scope, ordered atomic tasks, acceptance criteria, verification gate, and first implementation handoff prompt.
