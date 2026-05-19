# V2-D — Expanded CoachPolicy Tendencies — Design Spec

**Date:** 2026-04-28
**Status:** Design approved, ready for implementation planning
**Scope:** Add three new `CoachPolicy` tendencies with real engine behavior, visible audit logging, persistence backcompat, tactics UI updates, and legibility tests.

---

## 0. Relation to Prior Specs

This document is the canonical V2-D spec. It implements the expanded CoachPolicy direction from `docs/specs/AGENTS.md` and the milestone index.

V2-D is independent of V2-B, V2-C, V2-E, and V2-F, but it is the only V2-B through V2-F milestone that intentionally touches match-engine behavior.

---

## 1. Goals

1. Add Target Ball-Holder, Catch Bias, and Rush Proximity to `CoachPolicy`.
2. Make every new tendency measurably shift behavior.
3. Keep all effects visible in event logs.
4. Preserve determinism, symmetry, monotonicity, and difficulty-without-buffs.
5. Update tactics UI without crowding or misleading users.

---

## 2. CoachPolicy Fields

`CoachPolicy` expands from five fields to eight:

```
target_stars: float = 0.7
risk_tolerance: float = 0.5
sync_throws: float = 0.2
tempo: float = 0.5
rush_frequency: float = 0.5
target_ball_holder: float = 0.5
catch_bias: float = 0.5
rush_proximity: float = 0.5
```

Missing fields in old saves default to `0.5`. Unknown future fields remain ignored.

Default values must preserve historical behavior as closely as possible. A neutral `catch_bias = 0.5` should reproduce the current catch-attempt threshold, and neutral `target_ball_holder` / `rush_proximity` should avoid broad golden-log churn except where new audit payload fields are intentionally added.

---

## 3. Engine Behavior

### 3.1 Target Ball-Holder

The current engine has team possession, not full player ball ownership. V2-D uses a deterministic recent-pressure hook:

- track the most recent opposing thrower or pressure player,
- pass that identity into target selection,
- blend target score from star value, vulnerability, and ball-holder pressure.

The recent-pressure identity lives in match runtime state, not in persisted player or team models. It is derived from the ordered event flow and resets naturally when a match starts.

High `target_ball_holder` should target the recent pressure player more often. Low values should preserve existing star/vulnerability emphasis.

### 3.2 Catch Bias

`catch_bias` controls willingness to attempt a catch.

It must not change `p_catch`. It changes only the decision threshold for whether the catch attempt is made. This keeps catch rating monotonicity clear: catch skill affects catch success, while catch bias affects tactical risk.

### 3.3 Rush Proximity

`rush_frequency` decides whether rush behavior activates. `rush_proximity` controls intensity when it does.

Rush intensity can apply visible, logged context terms, such as:

- small on-target pressure modifier,
- extra fatigue cost,
- catch exposure tradeoff.

All constants must live in config, not inline engine logic.

---

## 4. Event Log Requirements

Relevant throw events must log:

- full 8-field policy snapshot,
- target score components,
- target-ball-holder contribution,
- catch decision threshold and components,
- catch-bias contribution,
- rush active flag,
- rush frequency and proximity values,
- applied rush modifiers,
- any new RNG roll.

No unlogged randomness is allowed.

If implementation adds new RNG draws, they must use explicit namespaces:

- `coach_policy_catch_attempt` for any stochastic catch-attempt decision introduced by `catch_bias`.
- `coach_policy_rush_activation` for rush activation if `rush_frequency` becomes stochastic.
- `coach_policy_rush_intensity` for any stochastic variation in rush proximity effects.

If the implementation keeps these decisions deterministic, these namespaces remain reserved and unused.

---

## 5. Persistence and Compatibility

Existing club policy persistence uses JSON, so no new policy columns are required.

Implementation must update all policy construction and formatting paths:

- setup loader,
- randomizer,
- sample data,
- GUI / Manager GUI tactics,
- UI formatters,
- tests and fixtures.

Old saves load with neutral values. New saves persist all eight fields.

---

## 6. UI

Tactics screen groups tendencies:

- **Targeting:** Target Stars, Target Ball-Holder.
- **Throw Style:** Risk Tolerance, Sync Throws.
- **Pressure:** Rush Frequency, Rush Proximity.
- **Pace and Defense:** Tempo, Catch Bias.

Effect text:

- Target Ball-Holder: prioritizes the opponent driving the current possession.
- Catch Bias: increases catch attempts, with visible risk.
- Rush Proximity: determines how close pressure gets during rushes.

---

## 7. Golden Logs

V2-D intentionally changes engine behavior and event audit payloads. The clean path is:

1. Update or add a V2-D golden log.
2. Record a change note explaining the policy audit and behavior changes.
3. Keep invariant tests green.

Do not silently shift the existing regression contract without a documented reason.

Implementation should first try to preserve historical default-policy outcomes and limit existing golden changes to additive audit payloads. If neutral defaults still change outcomes because the old behavior was implicit or inconsistent, update the golden with a specific V2-D note explaining why.

---

## 8. Testing

Required coverage:

- High target-ball-holder targets recent pressure player more often than low.
- High catch-bias increases catch attempts without changing `p_catch`.
- High rush-proximity logs stronger rush context than low.
- Event logs include all new policy fields and score components.
- Determinism still passes.
- Symmetry still passes.
- Difficulty still does not alter player stats or probabilities through hidden buffs.
- Catch rating monotonicity remains true.
- UI formatter renders eight readable policy rows.

---

## 9. Acceptance Criteria

V2-D ships when:

1. `CoachPolicy` has eight fields with backcompatible defaults.
2. All three new tendencies measurably affect behavior.
3. Event logs expose the relevant calculations.
4. Tactics UI displays grouped controls.
5. Golden-log changes are documented.
6. Integrity harness remains green.

---

*End of V2-D Expanded CoachPolicy Tendencies design spec.*
