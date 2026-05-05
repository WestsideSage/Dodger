# V6: Player Identity and Development Loop

## Relation to Prior Specs

This document defines the V6 milestone of Dodgeball Manager. It builds directly upon:
- `docs/specs/v5/2026-05-02-v5-weekly-command-center/design.md`: V6 expands the Weekly Command Center introduced in V5 by adding a `dev_focus` order and making the post-week reports meaningful through player archetypes and development tracking.
- `docs/retrospectives/v5/2026-05-02-v5-weekly-command-center-handoff.md`: Inherits the V5 structural components (PlayerTraits) and the shared `offseason_ceremony.py` flow.
- `docs/specs/AGENTS.md`: The integrity contract remains in effect. All liability warnings must have measurable simulation effects. All development must be causally traceable to reps and program focus.

## 1. Overview

V6 is the archetype milestone. It transforms players from interchangeable bodies with generic names into distinct athletic assets with clear identities, strengths, and weaknesses. It introduces a structural puzzle to roster management: players have native `PlayerArchetypes`, but must be slotted into fixed positional `Roles`.

The core loop change:
`evaluate roster -> set development priority -> allocate reps -> simulate weeks -> inspect player movement -> adjust depth chart`

## 2. Player Model Changes

### 2.1 Player Archetypes
Players are assigned a `PlayerArchetype` at creation:
- **Power**: Physical dominance. High base Power.
- **Agility**: Speed and evasion. High base Dodge/Catch.
- **Precision**: Accuracy and targeting. High base Accuracy.
- **Defense**: Blocking and survival. High base Block.
- **Tactical**: Game flow management. High Tactical IQ.

### 2.2 Tactical IQ
`tactical_iq` is added to `PlayerRatings` alongside existing physical stats. It governs decision-making quality in the match engine.

## 3. Positional Liabilities (Lineup Fit)

Slotting a player into a positional Role (Captain, Striker, Anchor, Runner, Rookie, Utility) compares their `PlayerArchetype` against the Role's demands.

| Positional Slot | Clean Fit | Tolerated | Liability |
| :--- | :--- | :--- | :--- |
| **Captain** | Tactical, Precision | Defense, Agility | Power |
| **Striker** | Power, Precision | Agility, Tactical | Defense |
| **Anchor** | Defense, Power | Tactical, Precision | Agility |
| **Runner** | Agility | Tactical, Precision, Defense | Power |
| **Rookie** | *Any* | None | None |
| **Utility** | Tactical | Power, Agility, Precision, Defense | None |

### 3.1 Engine Effects of Liabilities
If a player occupies a Liability slot, they suffer during simulation:
1. **-20% Modifier to Tactical IQ**.
2. **+15% Fatigue Drain Rate**.

## 4. Development Loop

Development transitions from flat offseason events to an active, rep-driven system over the season.

### 4.1 Reps Tracking
The simulation tracks `minutes_played` per player throughout the season, serving as their developmental reps.

### 4.2 Development Focus
The Weekly Command Center allows the manager to select a `dev_focus`:
- `BALANCED`: 1.0x multiplier.
- `YOUTH_ACCELERATION`: 1.5x (Age <= 22), 0.5x (Age > 22).
- `TACTICAL_DRILLS`: 1.5x (Tactical IQ), 0.8x (Physical).
- `STRENGTH_AND_CONDITIONING`: 1.5x (Power/Stamina), 0.8x (Technical).

### 4.3 Season Development Formula
Calculated in the offseason:
1. **Base Growth**: `(Minutes Played / 1000) * 15`.
2. **Potential Modifier**: `1.0 + ((Potential Trait - 50) / 100)`.
3. **Focus Multiplier**: Based on the active `dev_focus` history.
4. **Final Allocation**: The growth pool is distributed to the player's `PlayerRatings`, with 60% heavily weighted toward their Archetype's primary stats.

## 5. UI and Migration

- **UI Update**: Archetypes, Tactical IQ, and Lineup Liabilities are fully surfaced in the Command Center and Roster views.
- **Migration**: Existing V5 saves assign an organic Archetype and base Tactical IQ upon load to prevent crashes.

## 6. Verification Gates

1. **Functional/Playable**: Player can read liabilities, set focus, and advance.
2. **AI Gate**: AI clubs avoid Liability slots where possible during pre-match lineup set.
3. **Simulation Honesty Gate**: Liability engine penalties are measurably enforced in outcome tests.