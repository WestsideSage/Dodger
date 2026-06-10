---
name: dodgeball-watchability-broadcast
description: Use when Dodgeball Manager work asks whether match replay, broadcast framing, moment selection, aftermath, Primary Factor, Manager Lesson, playoff presentation, or match storytelling is watchable and truthful.
---

# Dodgeball Watchability Broadcast

Use this skill for match-experience, replay, broadcast, and postgame narrative work.

## Operating Stance

Answer the core question: is watching a match fun, tense, readable, believable, and truthful about why the match unfolded that way?

Preserve simulation truth. Presentation may select, order, label, and explain events, but it must not invent events or alter outcomes for drama.

If the user requests read-only, review-only, or browser-only work, obey that boundary.

## Orientation

Start from live repo truth:

1. Confirm repo path, branch, and dirty status.
2. Read `AGENTS.md`, `docs/README.md`, `docs/STATUS.md`, and `docs/specs/MILESTONES.md`.
3. Read `CLAUDE.md` when present.
4. Inspect relevant match/replay/broadcast code: match engines, official engine/resolution, replay services, timeline/event transforms, aftermath context/explanation code, frontend replay and aftermath components, V13 broadcast docs if relevant, and related tests/Playwright specs.

Use Pare MCP commands where available and useful. If Pare is unavailable, unsuitable, or raw output is needed, use normal shell/git commands and state that fallback in the handoff.

## Non-Negotiables

- Do not change match outcomes for presentation drama.
- Do not add hidden momentum, comeback code, rubber-banding, animation-driven results, or unseeded randomness.
- Do not invent events, tactical causes, or official-rules claims that the event data does not support.
- Do not make the replay slower, noisier, or harder to parse just to add drama.
- If event classification, moment selection, or recap logic changes, prove before/after behavior with tests.

## Workflow

1. Inventory the match experience.
   Map pre-match, replay, scoreboard, event rows, timeline, moment cards, official rules panels, aftermath, Primary Factor, Manager Lesson, playoff war room, and ceremony references to matches.

2. Generate varied match samples.
   Use deterministic seeds, existing fixtures, tests, fast-forward tools, or real career flows. Seek close wins, blowouts, upsets, draws/no-point states, playoffs, championship matches, high-catch and low-event games, and multi-moment matches. Label any isolated component inspection clearly.

3. Diagnose each sample.
   Identify the match story, emotional peak, memorable moment, manager lesson, noisy events, misleading labels, and whether the replay made the story obvious.

4. Improve watchability safely.
   Good targets include moment selection/filtering, event labels, timeline grouping, scoreboard state, postgame narrative order, playoff/championship framing, draw/no-point disclosure, tactical evidence chips, replay fixtures, and commentary truth tests.

5. Verify.
   Browser-check replay and aftermath flows. Run focused replay/aftermath tests. Run full Python tests for broad event/moment logic changes. Run frontend build/lint for UI changes. Confirm outcomes were not dishonestly changed.

## Quality Bar

- A new player understands what happened.
- A returning player can see whether their plan worked.
- Close matches feel tense.
- Blowouts still explain why they were blowouts.
- The most important moment is not buried.
- The aftermath does not lie.
- Official-rules-inspired scoring is clear.
- Playoff and championship states feel more important than normal weeks.

## Handoff

Provide: watchability verdict, match samples inspected and how reached, biggest replay/narrative problems, implemented changes by replay/moments/aftermath/tests, evidence outcomes were not dishonestly changed, exact tests/checks run, and unreachable states or owner decisions.
