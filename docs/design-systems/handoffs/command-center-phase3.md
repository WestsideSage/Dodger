# Command Center Phase 3: Add Polish

**Depends on:** Phase 2 complete (ReplayTimeline, KeyPlayersPanel, TacticalSummaryCard exist)

**Design system reference:** `docs/design-systems/Command-Center-Design-System.md`, sections 9–10

---

## Goal

Add animation and visual polish to the post-match view so the result feels rewarding, not just informative.

---

## What to build

### 1. Score count-up animation

In `MatchScoreHero`, animate survivor counts from 0 to final value over ~1.5s. Use `requestAnimationFrame` or a simple interval — don't add a dependency.

### 2. Winner glow

The winning side in `MatchScoreHero` gets a subtle glow: `box-shadow: 0 0 24px rgba(34, 211, 238, 0.12)` (or orange equivalent for home). Loser side stays readable but at reduced opacity (~0.6).

### 3. Reveal animation refinement

Current reveal uses `setTimeout` with 1s delays. Refine to use CSS transitions:
- Each stage fades in from `opacity: 0` to `1` with `translateY(8px)` to `0`
- Duration: 400ms ease-out per stage
- Stages: Headline → Score Hero → Timeline+Players → Fallout → Action Bar

### 4. Hover states on FalloutGrid cards

```css
.fallout-card {
  transition: border-color 140ms ease, transform 140ms ease;
}
.fallout-card:hover {
  transform: translateY(-1px);
  border-color: rgba(34, 211, 238, 0.35);
}
```

### 5. Empty-state improvements

Replace debug-language empty states with front-office language:
- "No attribute growth detected this week." → "No player development changes this week."
- "No significant rank changes in the top table." → "No standings movement this week."
- "No prospect interest changes reported." → "No recruiting reactions from this match."

---

## Files to touch

| File | Action |
| ---- | ------ |
| `frontend/src/components/match-week/aftermath/MatchScoreHero.tsx` | Add count-up + winner glow |
| `frontend/src/components/match-week/aftermath/FalloutGrid.tsx` | Add hover states + empty-state copy |
| `frontend/src/components/MatchWeek.tsx` | Refine reveal animation CSS |

---

## What NOT to build

- Full-match animation system — that's the Match Replay screen
- Sound effects
- Particle effects or confetti
