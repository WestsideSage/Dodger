# V7 Roadmap: Watchable Match Proof Loop

Status: Active roadmap for V7 implementation.
Sprint plan: `docs/specs/2026-05-05-v7-sprint-plan.md`
Long-range source: `docs/specs/long-range-playable-roadmap.md` section "V7: Watchable Match Proof Loop"

## Playable Thesis

The match viewer makes autonomous play legible enough that the user can see tactics, roles, fatigue, and player decisions express themselves.

## Primary Loop

`set plan -> watch/skim match -> inspect key plays -> read report -> adjust tactics/lineup`

## Non-Negotiable Scope

- Tactical clarity first: possession, targets, pressure, fatigue, eliminations.
- Role and archetype expression in match evidence.
- Event context that explains why a player acted or failed.
- Key-play navigation across more than the first elimination.
- Fast result remains available.
- Report evidence for tactics, matchup fit, fatigue, and liabilities.

## Non-Goals

- Mid-match coaching.
- Broadcast commentary.
- Camera-heavy presentation polish.
- Physics-heavy arcade behavior.
- Recruiting promises or program credibility.
- Morale, personality, leadership, or chemistry systems.

## Completed Prerequisites

Closed before viewer feature work starts:

1. Repair V6 reps accounting so `minutes_played` is extracted, persisted, and available to development/report systems.
2. Fix the roster table truth alignment so role, archetype, age, OVR, potential, Tactical IQ, and ratings display under correct headers.

V7 implementation should now begin with the replay-proof backend view model in `docs/specs/2026-05-05-v7-sprint-plan.md`.

## Integrity Rules

- The viewer never contradicts the persisted event log.
- Visuals show simulation truth, not decorative drama.
- Tactics exposed in V5/V6 must be visible in match evidence before the UI claims they mattered.
- Missing evidence must be reported as missing evidence, not converted into fake causal explanation.

## Implementation Authority

Use `docs/specs/2026-05-05-v7-sprint-plan.md` for the ordered task list and handoff prompt. This roadmap is the compact scope reference; the sprint plan is the implementation contract.
