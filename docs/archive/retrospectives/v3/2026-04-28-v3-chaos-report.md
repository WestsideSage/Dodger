# Dodgeball Manager V3 Chaos Report (2026-04-28)

## Project Trajectory
- **WHERE WE WERE**: Past versions had issues with deterministic results and basic persistence. V3 introduced "Pacing Controls" and "Roster Integrity," which increased the complexity of state management.
- **WHERE WE ARE**: V3 is remarkably resilient in its core simulation and offseason logic. Most "heavy" operations are idempotent or individually committed, allowing for recovery from interruptions.
- **WHERE WE ARE GOING**: To be "bulletproof" for V4, we must close logic holes in player acquisition and enforce stricter type/value boundaries at the API level.

## Critical Failure Points
### 1. Double Signing Vulnerability
- **Description**: `sign_prospect_to_club` allows a prospect to be signed multiple times to different clubs without error.
- **Reproduction**:
    1. Initialize a career.
    2. Call `sign_prospect_to_club(conn, target, "club_a", 1)`.
    3. Call `sign_prospect_to_club(conn, target, "club_b", 1)`.
- **Impact**: The same `player_id` exists in multiple club rosters. This violates the integrity of a single-league simulation and could lead to stat aggregation confusion or UI glitches.
- **Status**: **FAIL**

### 2. Seed Type Validation
- **Description**: The system accepts non-integer seeds (e.g., strings) for career initialization.
- **Reproduction**: `initialize_manager_career(conn, "aurora", root_seed="MALICIOUS_STRING")`.
- **Impact**: While `derive_seed` handles this via f-string hashing, it deviates from the `int` type hint and could cause issues if the seed is later used in an operation requiring numeric properties.
- **Status**: **WARNING** (Functional but unsafe)

## State Corruptions
- **Sequence Breaking**: Manually jumping the `CareerStateCursor` to the offseason without playing matches does NOT crash the application. `initialize_manager_offseason` handles the absence of data gracefully, though it produces a "boring" offseason. **Status: PASS**
- **Bulk Sim Interruption**: Matches are committed individually. A crash during `_sim_week` leaves match records in the DB. Standings may be out of sync until the next `_recompute_standings` call. Since `_recompute_standings` is idempotent, the system is self-healing. **Status: PASS**

## Edge Case Checklist
- **Empty Roster**: `simulate_match` handles empty rosters without crashing. **Status: PASS**
- **Input Injection (Names)**: SQL injection in club names is prevented by parameterized queries. Extremely long names are stored correctly. **Status: PASS**
- **Malicious Scouting Filters**: Scouting tick handles invalid/malicious filters in `ScoutStrategyState` without crashing. **Status: PASS**
- **Roster Bloat**: Persisting 1000 players to a single club and recomputing standings is handled without performance collapse. **Status: PASS**

## Conclusion
V3 is **STABLE** enough to serve as the foundation for V4, but the **Double Signing** bug should be fixed as a high priority before V4 recruitment or multi-user features are added. The system's self-healing properties (idempotent standings and offseason) provide excellent resilience against "non-happy path" interruptions.

**Recommendation**: Add a check in `sign_prospect_to_club` to verify `is_signed` status, and enforce `root_seed: int` at the entry point.
