# V6 Player Identity and Development Loop Handoff

Date: 2026-05-05
Milestone: V6
Status: Shipped and implementation-closed for V7 handoff.

## Milestone Summary

V6 moved Dodgeball Manager from generic roster bodies toward distinct player assets. The shipped slice adds archetype identity, Tactical IQ, positional lineup liabilities, AI lineup avoidance, liability penalties in the match engine, and a development-focus control in the Weekly Command Center.

The intended loop is now present at the product level:

`evaluate roster -> set development priority -> allocate reps -> simulate weeks -> inspect player movement -> adjust depth chart`

## Shipped Mechanics

- `PlayerArchetype` exists in `src/dodgeball_sim/models.py` with Power, Agility, Precision, Defense, and Tactical identities.
- `PlayerRatings` includes `tactical_iq`, and `Player.overall()` includes Tactical IQ in the rating aggregate.
- Curated/random player generation assigns archetypes and archetype-shaped ratings through `src/dodgeball_sim/randomizer.py`.
- Lineup liability logic lives in `src/dodgeball_sim/lineup.py`.
- The command center includes liability warnings through `src/dodgeball_sim/command_center.py`.
- AI lineup optimization avoids liability slots where possible.
- The engine applies liability consequences:
  - +15% fatigue drain for liable players.
  - -20% Tactical IQ effect in target-selection decision noise.
- The Weekly Command Center includes `dev_focus` selection in `frontend/src/components/CommandCenter.tsx`.
- The roster UI surfaces role, archetype, age, OVR, potential, Tactical IQ, and ratings under aligned headers in `frontend/src/components/Roster.tsx`.
- Real match reps now flow through `PlayerMatchStats.minutes_played`, persistence schema version 13, season stat aggregation, and server stat reconstruction.

## Verification

Focused V6 verification run during closeout:

`/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_v6_player_identity.py -q`

Result:

`4 passed`

This verifies lineup liability warnings, AI lineup avoidance, development-focus deltas, and the liability fatigue multiplier.

Implementation closeout verification:

- `/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_stats.py tests/test_persistence.py tests/test_server.py tests/test_command_center.py tests/test_v2a_scouting_persistence.py tests/test_v2b_recruitment_persistence.py tests/test_v6_player_identity.py -q`
- Result: pass
- `npm run lint` from `frontend/` via Windows Node 24.15.0
- Result: pass
- `npm run build` from `frontend/` via Windows Node 24.15.0
- Result: pass

## Known Thin Spots

The two implementation thin spots originally carried into V7 prerequisite work are now closed:

1. `PlayerMatchStats.minutes_played` is extracted, migrated, persisted, aggregated, and reconstructed in server-facing stat payloads.
2. `frontend/src/components/Roster.tsx` now aligns Role, Archetype, Age, OVR, Potential, Tactical IQ, and ratings with their headers.

Remaining boundaries are scope decisions, not V6 defects:

1. V6 browser-specific QA was not found as a separate report. V7 adds a formal browser playthrough gate before it can ship.
2. V6 mechanics are intentionally first-pass. There is no morale system, individual skill tree, staff market, recruiting promise system, or program credibility model in V6.

## What V7 Inherits

- Persisted match events remain the canonical replay truth.
- Roster snapshots are already available for match replay identity mapping.
- Event context already contains probabilities, rolls, policy snapshots, rush context, sync context, fatigue context, and calculation details useful for V7 proof panels.
- Command history is persisted and can connect a weekly plan to replay evidence.
- The V7 milestone should not tune match outcomes. Its job is to explain autonomous play using stored evidence.

## Closeout Verdict

V6 is closed for documentation, implementation, and milestone sequencing. The next implementation milestone is V7 Watchable Match Proof Loop, starting with the replay-proof backend view model in `docs/specs/2026-05-05-v7-sprint-plan.md`.
