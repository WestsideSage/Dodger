# Subplan 11: Sim Transition Animation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Replace the page-blink that currently happens on Sim Match with a single continuous animation: pre-sim panel slides up → match replay takes screen → final whistle freeze → court fades → Aftermath fades in.

**Dependencies:** Subplans 05, 06 (pre-sim and post-sim layouts must exist). Parallel-safe with 10, 12, 13, 14, 15.

**Acceptance criteria (from 00-MAIN.md):**
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

---

- [ ] **Step 1: Create Transition Container**

Create `frontend/src/components/match-week/SimTransition.tsx`:
```tsx
import { useEffect, useState } from 'react';

export function SimTransition({ onComplete, isFast }: { onComplete: () => void, isFast: boolean }) {
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const duration = prefersReducedMotion ? 800 : (isFast ? 1500 : 4000);
    const t = setTimeout(onComplete, duration);
    return () => clearTimeout(t);
  }, [onComplete, isFast]);

  return <div className="dm-transition-overlay">Simulating...</div>;
}
```
Commit.

- [ ] **Step 2: Add CSS Animation Tokens**

In `frontend/src/index.css`, add classes for `.slide-up-out`, `.fade-in`, `.fade-out`, and `@media (prefers-reduced-motion: reduce)` overrides. Commit.

- [ ] **Step 3: Update MatchWeek.tsx State Machine**

In `MatchWeek.tsx`, add a `transitioning` state.
```tsx
const [isTransitioning, setIsTransitioning] = useState(false);

const simulate = () => {
    setIsTransitioning(true);
    // run fetch...
    // on complete, don't change mode until SimTransition calls onComplete
}
```
If `isTransitioning` is true, render the `SimTransition` component (with Fast/Normal logic passed down) instead of immediately showing `post-sim` mode. Commit.

- [ ] **Step 4: Wire Offseason Transition**

In `MatchWeek.tsx`, add a brief fade transition state for advancing weeks in the offseason mode. Commit.

- [ ] **Step 5: Cross-cutting principle check**

Run `npm run build`.
Manual test: Check that the "Fast" sim speed has a minimum 0.8s delay (no instant blink). Verify `prefers-reduced-motion` cuts instantly instead of fading.
```bash
git commit --amend --no-edit
```