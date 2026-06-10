---
name: dodgeball-first-hour-onboarding
description: Use when Dodgeball Manager work asks about first-time-player onboarding, fresh-save playthroughs, first-hour comprehension, new career setup, first command loop, first match, first aftermath, or early retention.
---

# Dodgeball First Hour Onboarding

Use this skill for first-time-player comprehension, onboarding, and early-retention work.

## Operating Stance

Answer the core question: does the game teach itself through play, or does the player need repo knowledge to enjoy it?

Act like a new player when evaluating the flow. Do not use source knowledge to excuse confusion in the UI.

If the user requests browser-only, stay browser-only unless the game hard-crashes or the user changes scope.

## Orientation

Start from live repo truth:

1. Confirm repo path, branch, and dirty status.
2. Read `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md`.
3. Read `CLAUDE.md` when present.
4. Inspect relevant frontend routes/components, server/use-case payloads for onboarding, weekly loop, replay, aftermath, and relevant Playwright/E2E tests.

Use Pare MCP commands where available and useful. If Pare is unavailable, unsuitable, or raw output is needed, use normal shell/git commands and state that fallback in the handoff.

## Non-Negotiables

- Do not add a heavy tutorial overlay unless evidence proves it is necessary.
- Prefer contextual teaching, progressive disclosure, proof-backed labels, better defaults, stronger empty states, and clearer next steps.
- Do not invent gameplay effects to make onboarding feel better.
- Do not hide complexity needed for trust.
- Do not optimize for mobile.
- Do not add dependencies.
- Do not make player-facing claims unsupported by real data.

## Workflow

1. Play like a brand-new player.
   Start from a fresh custom club/save. Narrate what the game seems to want, what you click, why, what changes, what is confusing, and what feels meaningful versus decorative. Capture notes or screenshots for friction.

2. Cover the first-hour path.
   Include entry/save selection, career creation/build-from-scratch, first Command Center visit, readiness gates, Scout Opponent, lineup/tactics, first match replay, first aftermath, standings/discovery surfaces, and first offseason if reachable.

3. Classify comprehension failures.
   Use these labels: what do I do next, why did this happen, what does this term mean, did my choice matter, this looks broken, too much information, not enough information, or no reason to continue.

4. Implement focused improvements.
   Good targets include first-run copy, calls to action, progressive disclosure, term explanations, readiness gate reasons, ordering, error states, next-step prompts, and tests for critical first-hour paths.

5. Verify.
   Re-run the first-hour flow after changes. Check 1440x900 and 1280x720. Run frontend build/lint for UI changes. Run relevant Playwright/E2E. Run backend tests if payload/copy logic changed.

## Quality Bar

- A new player knows how to start.
- A new player knows what to do before the first match.
- A new player knows what decisions are meant to influence.
- A new player can read the first match.
- A new player gets an honest explanation afterward.
- A new player has a clear next step.
- Teaching comes from real systems, not fake hand-holding.

## Handoff

Provide: first-hour verdict, fresh-player flow tested, biggest comprehension failures, implemented improvements by flow stage, screens/pages verified, exact tests/checks, remaining onboarding risks, and owner decisions.
