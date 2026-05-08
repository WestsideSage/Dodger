# Subplan 12 (STUB): Match Replay Commentary + Player Positioning Fix

> **Status:** STUB. Detailed task breakdown authored after Wave 2 ships. Read `../00-MAIN.md` first.

**Goal:** Replace the "Proof" tab with a "Play-by-Play" tab rendered from the voice library. Fix the player-dot positioning bug that splits each team into 3-top + 3-bottom (creating visual ambiguity about which team is on which side of the court). Implement three speeds.

**Dependencies:** Subplan 10 (voice library, specifically `voice_playbyplay.py`). Parallel-safe with 11, 13, 14, 15.

**Acceptance criteria:**

**Commentary:**
- "Proof" tab renamed to "Play-by-Play" and rendered from `voice_playbyplay.py` templates.
- Each event in the existing event stream maps to one or more templated commentary lines.
- Tab visually styled like a sports broadcast feed (timestamp + line of prose), NOT a debug log.
- Resolution states (`eliminated`, `caught`, `dodged`) no longer surface as raw labels; they're embedded in the prose.

**Player positioning:**
- Each team's players cluster on their own half of the court (left vs. right), facing center.
- Layout for 6 players per team: NOT 3-cols × 2-rows in the team's half (which creates the 3-top/3-bottom ambiguity), but a clearer formation that reads as one cluster facing the centerline.
- Specific layout to implement: 2 players forward (closer to centerline), 2 mid, 2 back. Vertically centered in the team's half. Each team's "facing direction" is implied by spacing density (denser toward centerline).
- Court still split horizontally as today, but with strong visual separators (centerline, possibly half-tinting) so the left/right team identity is unambiguous regardless of jersey color.
- The bug at `MatchReplay.tsx:30-50` (`assignPositions` doing `cols = ceil(n/2), rows = ceil(n/cols)`) is the root cause. Replace with explicit per-team formation logic.

**Three speeds:**
- Speed selector (Fast / Normal / Slow) on the matchup card (Subplan 05) AND inside the replay (toggleable mid-match).
- Fast: skip viz entirely, jump to result with the Subplan 11 transition beat.
- Normal: animation runs at ~3x real-tick speed; commentary lines appear faster.
- Slow: real-time per-tick; commentary paces with the action.

**Files anticipated:**
- `frontend/src/components/MatchReplay.tsx` (rewrite positioning + tab labels + speed handling)
- `src/dodgeball_sim/replay_proof.py` (may need restructure — the data is fine; the labels need work)
- `src/dodgeball_sim/voice_playbyplay.py` (consumed here)
- `frontend/src/types.ts` (extend ReplayProofEvent type if voice rendering is server-side)

**Verification gates:** build + pytest green; manual smoke confirms commentary reads like a broadcaster, player clusters are unambiguous, all three speeds work and are switchable mid-match.
