# V6 Sprint Plan: Player Identity and Development Loop

**Milestone:** V6
**Date:** 2026-05-04
**Target:** Playable week-by-week development loop with explicit archetype-driven lineup liabilities.

## Current State Summary
The web app supports a full command center, simulation loop, and offseason ceremony (V5). Players have varied traits but identical structural identities. The command center accepts orders but lacks depth in roster optimization.

## Readiness Verdict
Ready for implementation. The long-range roadmap and architectural decisions (Archetypes, `dev_focus` math, Lineup Fit matrix) are fully documented and approved.

## Prerequisites
- Completed V5 web flow. (Done)
- Approved V6 implementation plan. (Done)

## At-Risk or Deferred Scope
- Deep personality/morale traits are deferred.
- No new UI screens; all V6 additions must live within the existing Command Center, Roster, and Offseason screens.

## Ordered Atomic Tasks

1. **Backend Model Updates (Schema + RNG)**
   - Define `PlayerArchetype` Enum.
   - Update `PlayerRatings` schema to include `tactical_iq` (default 50).
   - Update `Player` schema to include `archetype`.
   - Update save schema version and migration logic in `persistence.py`.
   - Update `randomizer.py` to assign organic archetypes and constrain ratings generation based on the archetype.

2. **Lineup Liabilities (Logic + UI)**
   - Implement `check_lineup_liabilities(roster)` returning a list of warnings based on the Compatibility Matrix.
   - Expose warnings on the `/api/command-center` endpoint.
   - Update `frontend/src/components/CommandCenter.tsx` and `Roster.tsx` to surface Archetypes, Tactical IQ, and Liability warnings.

3. **Engine Adjustments (Simulation Honesty)**
   - Update the simulation engine (likely `engine.py` or match resolution logic) to apply the `-20% Tactical IQ` and `+15% Fatigue Drain Rate` penalties to players in Liability slots.
   - Write tests confirming these penalties alter simulation probabilities.
   - Ensure AI clubs avoid Liability slots when setting lineups.

4. **Active Development Loop**
   - Add `dev_focus` to `WeeklyIntent` or `DepartmentOrders` and track its selection over the season.
   - Track `minutes_played` (reps) on players during matches.
   - Refactor `development.py` (`apply_season_development`) to use the Reps-based formula, applying potential, focus multipliers, and weighting stat distribution to the Archetype.

5. **Offseason Reports UI**
   - Expose the detailed stat deltas (with focus tracking) in the Offseason API.
   - Update `frontend/src/components/Offseason.tsx` to display meaningful development reports.

## Regression Gate
- Run all existing V5 tests. The migration of `tactical_iq` into `PlayerRatings` might break tests that assert specific key sets or model shapes.
- Verify `offseason_ceremony.py` handles the new development deltas without breaking the beat sequence.

## Handoff Prompt for Next Implementation Task
"Begin Phase 2 Backend Core: Define `PlayerArchetype` in `models.py`, move `tactical_iq` into `PlayerRatings`, update the `Player` model, and implement safe migration in `persistence.py`. Ensure `randomizer.py` generates valid V6 players."