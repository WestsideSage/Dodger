# Subplan 11 (STUB): Sim Transition Animation

> **Status:** STUB. Detailed task breakdown authored after Wave 2 ships. Read `../00-MAIN.md` first.

**Goal:** Replace the page-blink that currently happens on Sim Match with a single continuous animation: pre-sim panel slides up → match replay takes screen → final whistle freeze → court fades → Aftermath fades in.

**Dependencies:** Subplans 05, 06 (pre-sim and post-sim layouts must exist). Parallel-safe with 10, 12, 13, 14, 15.

**Acceptance criteria:**
- Clicking `Sim Match` from pre-sim mode begins a non-skippable animation:
  1. Pre-sim panel slides up off-screen (~300ms ease-out)
  2. Match replay takes the full content area
  3. On match end, court freezes for 1s with score displayed
  4. Court fades out (~400ms)
  5. Aftermath panel fades in
  6. Aftermath blocks reveal in sequence (Subplan 06 already does this)
- Fast Sim path (no replay viz) still gets a ≥0.8s "results coming in" beat — never an instant blink. A simple animated indicator (spinner, coin-flip, scoreboard ticker) covers the gap.
- Animation respects user `prefers-reduced-motion` — at the system level, replace slides/fades with instant cuts but keep the timing gates so the sequence still feels paced.
- Offseason `Advance Week` action (when no match is involved) gets its own simpler transition: brief content fade, no replay step.

**Files anticipated:**
- `frontend/src/components/MatchWeek.tsx` (orchestrate the transition state machine)
- New: `frontend/src/components/match-week/SimTransition.tsx` (or similar — encapsulates the animated lifecycle)
- CSS / animation tokens — possibly extend `frontend/src/index.css` or component-local styles
- No backend changes anticipated.

**Verification gates:** build green; manual smoke confirms no instant blinks across all three speeds; reduced-motion mode confirmed.
