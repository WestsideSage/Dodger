# Subplan 12: Match Replay Commentary + Player Positioning Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Replace the "Proof" tab with a "Play-by-Play" tab rendered from the voice library. Fix the player-dot positioning bug that splits each team into 3-top + 3-bottom (creating visual ambiguity about which team is on which side of the court). Implement three speeds.

**Dependencies:** Subplan 10 (voice library, specifically `voice_playbyplay.py`). Parallel-safe with 11, 13, 14, 15.

**Acceptance criteria (from 00-MAIN.md):**
- "Proof" tab renamed to "Play-by-Play" and rendered from `voice_playbyplay.py` templates.
- Each event in the existing event stream maps to one or more templated commentary lines.
- Tab visually styled like a sports broadcast feed (timestamp + line of prose), NOT a debug log.
- Resolution states (`eliminated`, `caught`, `dodged`) no longer surface as raw labels; they're embedded in the prose.
- Each team's players cluster on their own half of the court (left vs. right), facing center.
- Specific layout to implement: 2 players forward, 2 mid, 2 back. Vertically centered in the team's half.
- Court still split horizontally as today, but with strong visual separators.
- The bug at `MatchReplay.tsx:30-50` (`assignPositions` doing `cols = ceil(n/2), rows = ceil(n/cols)`) is replaced with explicit per-team formation logic.
- Speed selector (Fast / Normal / Slow) on the matchup card (Subplan 05) AND inside the replay (toggleable mid-match).
- Fast: skip viz entirely, jump to result. Normal: ~3x real-tick. Slow: real-time.

---

- [ ] **Step 1: Test & Backend for Replay Commentary**

In `tests/test_voice_library.py` or `test_replay_proof.py`, assert that the `proof_events` list returns a `commentary` string for each play instead of raw resolution logic.
Update `src/dodgeball_sim/replay_proof.py` to use `render_play` from `voice_playbyplay.py`. Commit.

- [ ] **Step 2: Rewrite Player Positioning Logic**

In `frontend/src/components/MatchReplay.tsx`, find `assignPositions` (around line 30).
Rewrite to explicit 2-2-2 formation for 6 players:
```tsx
const getFormationPositions = (count: number, side: 'left' | 'right', courtWidth: number, courtHeight: number) => {
  // Explicit logic to place players in 2 forward, 2 mid, 2 back
  // Left team ranges from x=0 to courtWidth/2. Right team ranges from courtWidth/2 to courtWidth.
}
```
Commit.

- [ ] **Step 3: Create Play-by-Play Tab**

In `frontend/src/components/MatchReplay.tsx`, rename "Proof" to "Play-by-Play".
Map the event sequence into a stylized feed: `<div className="dm-feed-item"><span className="dm-time">{tick}</span> {commentary}</div>`.
Remove old raw labels. Commit.

- [ ] **Step 4: Implement Three-Speed Replay Logic**

In `MatchReplay.tsx`, add a speed toggle state: `const [speedMultiplier, setSpeedMultiplier] = useState(1);`.
Update the replay interval/timeout to use `baseInterval / speedMultiplier` (where Normal = 3, Slow = 1).
Wire the Fast option to instantly skip to `onComplete()`. Commit.

- [ ] **Step 5: Cross-cutting principle check**

Run `npm run build` & `pytest -q`.
Verify NO floats in the Play-by-Play UI. Verify visual layout creates clear left/right separation.
```bash
git commit --amend --no-edit
```