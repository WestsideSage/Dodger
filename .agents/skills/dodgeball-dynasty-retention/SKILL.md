---
name: dodgeball-dynasty-retention
description: Use when Dodgeball Manager work asks about multi-season retention, dynasty progression, roster lifecycle, recruiting/scouting/development economy, AI league health, awards, records, rivalries, or season-5 texture.
---

# Dodgeball Dynasty Retention

Use this skill for multi-season progression, economy, roster lifecycle, and long-term retention work.

## Operating Stance

Answer the core question: does the player have strong reasons to care about season 2, season 5, and season 10?

Long-term stories must be earned from real saved data. Do not fabricate history, awards, records, rivalries, promises, player arcs, or AI parity.

If the user requests read-only, review-only, or browser-only work, obey that boundary.

## Orientation

Start from live repo truth:

1. Confirm repo path, branch, and dirty status.
2. Read `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md`.
3. Read `CLAUDE.md` when present.
4. Inspect relevant files for career, season, playoffs, recruiting, recruitment domain, scouting, scouting center, development, awards, records, offseason beats, ceremonies, AI program manager, persistence schema/save state, dynasty office components, and multi-season tests/probes.

Use Pare MCP commands where available and useful. If Pare is unavailable, unsuitable, or raw output is needed, use normal shell/git commands and state that fallback in the handoff.

## Non-Negotiables

- No fake history, fake accomplishments, hidden boosts, or hidden punishments.
- Do not change match outcomes unless a real bug requires it and the change is measured.
- Do not introduce unseeded randomness.
- Do not make recruiting or development outcomes opaque.
- Prefer strengthening current systems over inventing a new economy layer.
- Do not add a huge new system without first proving the existing loops cannot carry retention.

## Workflow

1. Map the dynasty loop.
   Trace new career to week loop, playoffs, offseason, recruiting/development, next season, records, awards, rivalries, staff/program loops, and persistent state.

2. Simulate multiple seasons.
   Use existing fast-forward or deterministic tools. Track standings, champions, player growth, roster churn, awards, records, recruiting outcomes, AI strength, and user trajectory. If broad sampling is too slow, say so and run a smaller evidence-backed slice.

3. Analyze retention and balance.
   For each phase, identify the interesting decision, the consequence that carries forward, the story produced, the data proving it, and what feels flat, repetitive, fake, or solved.

4. Implement safe improvements.
   Good targets include development/recruiting truth, multi-season persistence tests, real-data ceremony/history improvements, AI differentiation where already scaffolded, snowball/parity probes, small config tuning with evidence, and fixes where long-term decisions do not persist or matter.

5. Verify.
   Run focused multi-season tests. Run broader Python tests when touching persistence, development, recruiting, awards, records, season transition, or shared ceremony payloads. Run frontend build/lint if presentation changes. Re-run multi-season samples where practical.

## Required Analysis

Explicitly answer:

- Strongest current long-term hook.
- Where the dynasty loop loses tension.
- Whether recruiting is too easy to solve.
- Whether development creates meaningful roster planning.
- Whether AI programs keep the league alive.
- Whether records and awards are meaningful enough.
- Biggest risk to season-5 retention.
- Measurements that should become dynasty-health gates.

## Handoff

Provide: dynasty-health verdict, multi-season evidence generated or inspected, retention strengths, retention risks, implemented changes by system, exact measurements/probes/tests, owner decisions, and ranked next improvements for season-5 retention.
