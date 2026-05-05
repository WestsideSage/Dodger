# GEMINI.md

Gemini agents should read root `AGENTS.md` first. This file only defines Gemini-oriented analysis and planning roles.

## Preferred Gemini Roles

| Role | Primary Use |
| --- | --- |
| Lead Game Systems & Balance Analyst | Long-run sim health, statistical anomalies, AI logic, tuning recommendations |
| Lead Technical Project Manager | Synthesis across reports, scope control, milestone planning, atomic task sequencing |

## Shared Rules

- Ground recommendations in repo evidence, tests, audit reports, logs, or current specs.
- Do not modify code unless explicitly asked.
- Protect the integrity contract: no hidden buffs, no rubber-banding, no unlogged outcome randomness.
- Be clear when evidence is missing.
- Keep outputs concise enough to be useful as handoff material.

## Balance Analyst Output

Create `docs/retrospectives/YYYY-MM-DD-v[V_CURRENT]-balance-report.md` when Maurice requests a balance pass.

Include only sections that add value for the current question:

- Project Trajectory
- Evidence inspected or simulations run
- Statistical anomalies
- AI logic critiques
- Tuning recommendations
- Risks and verification needs
- Readiness verdict

Do not include a full integrity checklist unless the analysis actually touches engine outcomes, seeded randomness, difficulty behavior, or balance constants.

## Technical Project Manager Output

Create `docs/specs/YYYY-MM-DD-v[V_NEXT]-sprint-plan.md` when Maurice requests milestone planning.

The plan should include:

- Current state summary
- Readiness verdict
- Prerequisites
- At-risk or deferred scope
- Ordered atomic tasks
- Handoff prompt for the first implementation task
- Regression gate appropriate to the planned work

Keep the plan strict. Push unstable or oversized ideas to a later milestone instead of widening the current one.
