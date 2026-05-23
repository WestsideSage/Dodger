# Tier 1 Match Loop - Plan Roadmap

Date: 2026-05-20 (last updated 2026-05-22)
Status: Active. Plans A and B landed on 2026-05-20; Plan C landed 2026-05-22. **Plan D is the next strict step.**
Parent brief: [brief.md](./brief.md)

This is the parent roadmap for the **Tier 1 Match Loop** milestone - the
first sub-project of the post-V11 redesign. It exists so the A/B/C/D
shape is visible without committing to a 30+ task mega-plan.

## Milestone goal

Deliver a single mergeable slice that boots a Tier 1 (Local Rec League)
match, runs it to completion against the rules from brief section 3.5, and
produces aftermath the player can read in rec-league vocabulary -
**without breaking V11 / USAD behavior covered by existing tests**.

## Architecture

Brief section 7.1 Option C, **Hybrid**, as a thin slice. Shared primitive
layer (existing `ball_state`, `catch_queue`, `sequence`, `player_state`
modules - *not moved*) plus new primitives (`fatigue`, `flood_throws`,
`stall_timer`, `moment_events`) and per-tier drivers. V11's
`run_autonomous_game` is wrapped, not rewritten.

## Plan sequence

| # | Plan | Role | Depends on | Risk |
|---|---|---|---|---|
| **A** | **Hybrid driver architecture + Tier 1 engine** | Architectural risk gate | V11 baseline | High - factoring without breaking USAD |
| **B** | **Player attribute v2** | Data-model upgrade | landed 2026-05-20 | - |
| **C** | **Tier 1 player-facing surface** | Tactics, replay, aftermath | landed 2026-05-22 | - |
| D | Simulation-health probe | Verification harness | A + B + C | Low |

**Order is strict.** C is now landed, which unblocks D. D replaces
`tools/o1_variance_probe.py`.

The full Plan A file is at
[plan-a-hybrid-driver.md](./plan-a-hybrid-driver.md). C and D are
stubbed below - they will each get a full plan written when their turn
comes.

---

## Plan B - Player attribute v2 (landed 2026-05-20)

**Inputs from Plan A:**
- `EngineDriver` protocol with attribute-attached hooks for catch
  courage, throw-selection IQ, conditioning curve.
- `fatigue.py` primitive that accepts a per-player `conditioning_curve`
  attribute and modulates accumulation/decay accordingly.
- Stubs on `Player` model for the new attribute fields (defaults
  preserve existing behavior - Plan A's tests pass without v2).

**Outputs:**
- `PlayerRatings` v2 - adds `catch_courage`, `throw_selection_iq`,
  `conditioning_curve` alongside the existing
  accuracy/power/dodge/catch/stamina/tactical_iq.
- Position-aware `PlayerArchetype` - replaces the old V6 enum with
  `THROWER`, `CATCHER`, `BALL_HAWK`, `DODGER_ANCHOR`, plus documented
  hybrids (`THROWER_CATCHER`, etc.).
- Seed/data migration for existing curated rosters: each player gets a
  derived archetype and v2 ratings from existing fields.
- Tests for each new attribute affecting expected driver behavior
  (for example `catch_courage` changes the throw-response branch,
  `throw_selection_iq` gates smarter throw timing, and
  `conditioning_curve` changes fatigue accumulation).

**Out of scope for Plan B:**
- Recruiting / scouting reading the new attributes (Plan C work).
- Command Center showing the new attributes (Plan C work).
- AI Program Manager use of attributes (cuttable subsystem #9).

## Plan C - Tier 1 player-facing surface (landed 2026-05-22)

**Inputs from Plans A + B:**
- Tier 1 driver emits the six moment events (Plan A defines the
  contract).
- Player attributes drive recognizable individual behavior (Plan B).
- Tactics policy v2 stub exists; driver consumes new policy shape.

**Outputs:**
- New `CoachPolicy` v2 - **Approach** (aggressive/patient/mixed),
  **Target Focus** (their stars / their ball-holders / spread),
  **Catch Posture** (go / safe / opportunistic), **Opening Rush Plan**
  (all-in / balanced / hold-back x nearest / strongest-side / center).
  Old 8-field model deleted.
- Command Center wiring: pre-match decision UI with the four knobs.
- Match Replay UI: surfaces all six moment beats from Plan A's
  emitted events. Speed controls. Rec-league vocabulary at Tier 1.
- Aftermath voice rewritten - `voice_verdict.py` and
  `voice_aftermath.py` reference moment events; rec-league register at
  Tier 1.
- Playwright e2e for the Tier 1 loop.

**Out of scope for Plan C:**
- Tier 2+ tactical knobs.
- Multi-tier UI vocabulary switching (single rec-league register only).
- Stats screens redesign (Plan D adjacent).

## Plan D stub - Simulation-health probe

**Inputs from Plans A + B + C:**
- Both drivers fully working.
- Six moment events emitted reliably.
- Player attribute model stable.

**Outputs:**
- New `tools/tier_engine_health_probe.py` - replaces
  `tools/o1_variance_probe.py`.
- Per-driver Monte Carlo runner: configurable matchups, N matches,
  seed range.
- Reports per tier: six-moment occurrence rate, upset frequency
  (OVR-gap vs win-rate curve), outcome variance, match-length
  distribution.
- CI-runnable smoke mode (fast, about 10 matches) for regressions; full
  mode for periodic health checks.
- Deletion of `tools/o1_variance_probe.py` (or graceful redirect).

---

## Out of scope for this whole milestone

These come in later sub-projects, not in any of A/B/C/D:

- Tier 2+ rules, drivers, or content.
- Promotion / relegation system.
- Tournament structure.
- Recruiting/scouting redesign for any tier.
- Stats / awards screens redesign.
- AI Program Manager work.
- Save migration tooling (the brief commits to clean break).
- Tkinter-era code deletion (separate cleanup task).

## Definition of done for the Tier 1 Match Loop milestone

A new career starts at Tier 1 (Local Rec League). The player makes a
small set of pre-match choices (the four Plan C knobs). The match
runs visibly to completion with the six moments surfacing where they
occur. The aftermath reads in rec-league language and explains the
outcome with reference to the decisions made. The full Python test
suite and the new Playwright e2e all pass. A rec-league dodgeball
player watching a session would recognize the sport.

This roadmap is updated as each plan lands.
