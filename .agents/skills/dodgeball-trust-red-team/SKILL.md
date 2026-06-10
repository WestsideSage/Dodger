---
name: dodgeball-trust-red-team
description: Use when Dodgeball Manager work asks for adversarial QA, trust/integrity review, fake decision detection, player-facing truth, stale docs, edge-state failures, accessibility sanity checks, or tests for high-risk claims.
---

# Dodgeball Trust Red Team

Use this skill for adversarial QA, simulation integrity, player-trust, and truthfulness work.

## Operating Stance

Answer the core question: where can Dodgeball Manager betray player trust mechanically, narratively, technically, or procedurally?

Code and tests beat docs when they disagree. Do not claim a path is verified unless you inspected that exact path or ran it.

If the user requests read-only, review-only, or browser-only work, obey that boundary.

## Orientation

Start from live repo truth:

1. Confirm repo path, branch, and dirty status.
2. Read `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md`.
3. Read `CLAUDE.md`, `docs/specs/long-range-playable-roadmap.md`, and official-rules/domain docs when relevant.
4. Inspect relevant backend, frontend, persistence, engine, replay, recruiting, scouting, development, playoffs, ceremonies, tests, and E2E paths.

Use Pare MCP commands where available and useful. If Pare is unavailable, unsuitable, or raw output is needed, use normal shell/git commands and state that fallback in the handoff.

## Non-Negotiables

- Do not assume docs are true when code may disagree.
- Do not assume code is correct when tests are weak.
- Do not patch symptoms before identifying the trust failure.
- Do not make broad rewrites.
- Do not change match outcomes unless a real bug requires it and before/after evidence is provided.
- Do not delete or overwrite unfamiliar work.
- Do not silently implement unresolved rules.

## Hunt Targets

- Fake decisions: controls, tactics, lineups, gates, scouting, recruiting, staff choices, or copy that imply effects not present in code.
- Outcome truth: unseeded randomness, hidden boosts, stale club/lineup/tactic data, nondeterministic paths, aftermath/event mismatches.
- Official-rules honesty: overclaims about No Blocking, throw-clock, opening rush, enforced versus announced-only behavior, and game-points versus survivor-score confusion.
- Persistence/state integrity: save/load, season rollover, offseason cursor, ceremony state, recruiting/development persistence, corrupt state, multi-tab or stale-server risks.
- UI truth/accessibility: disabled controls without reasons, misleading success states, weak error banners, misleading tooltips, focus traps, hidden labels, keyboard blockers.
- Edge states: empty/full rosters, no prospects, no records, byes, missed playoffs, champion states, draws, long names, extreme ratings, broken save names, unavailable actions.
- Test gaps: stale assumptions, wrong drivers, dead paths, missing launch-token/auth realities, and tests that give false confidence.

## Workflow

1. Build a trust-risk map.
   Inventory player-facing claims and supporting code paths. Rank by likely trust damage.

2. Trace contradictions.
   Follow decisions from UI to API to persistence to use case/domain/engine to replay/recap. Classify each as outcome, presentation, both, or neither.

3. Attack edge states.
   Use browser, tests, fixtures, fast-forward endpoints, and code inspection. Prioritize states a real player may hit.

4. Fix or guard.
   Fix proven bugs, add tests, correct overclaiming copy, add assertions/probes for drift, and mark owner decisions instead of guessing.

5. Verify.
   Run focused tests for every fixed area. Run full Python tests for broad backend/domain changes. Run frontend build/lint for frontend changes. Run targeted browser/E2E checks for trust-critical UI flows.

## Required Questions

Explicitly answer:

- Most dangerous player-facing lie present or likely to recur.
- Decisions most at risk of fake/no-op behavior.
- Docs most likely to mislead future agents.
- Tests giving false confidence.
- Edge state most likely to break a real playthrough.
- Unresolved issue that should not be fixed without owner input.

## Handoff

Provide: trust verdict, ranked high-risk findings, fixed issues with evidence, tests/probes added or updated, exact verification status, remaining risks, owner decisions, and source-of-truth doc updates.
