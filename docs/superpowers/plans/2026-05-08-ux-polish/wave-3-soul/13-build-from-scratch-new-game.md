# Subplan 13 (STUB): Build-From-Scratch New Game Flow

> **Status:** STUB. Detailed task breakdown authored after Wave 2 ships. Read `../00-MAIN.md` first.

**Goal:** Replace the single-input new save flow (name + preset club) with a two-path entry: `Take Over a Program` (fast, polished current flow) and `Build a Program From Scratch` (custom identity → coach → recruit-your-starting-roster mini-game).

**Dependencies:** Subplan 08 (recruiting verb set must exist — Build From Scratch reuses the same verbs as a tutorial). Parallel-safe with 10, 11, 12, 14, 15.

**Acceptance criteria:**

**Take Over a Program path:**
- Pick from preset clubs (existing flow).
- Optional: rename the club, recolor (palette picker).
- Optional: pick a coach backstory tile (e.g., `Local Hero`, `Unknown`, `Disgraced Rival`) — affects starting Program Credibility.
- ~60 seconds end-to-end. Direct path to Match Week.

**Build a Program From Scratch path:**
- Identity step: club name, abbreviation, primary/secondary colors, city, conference assignment (or `Independent`).
- Coach step: your name, coach backstory tile.
- Roster step (the hero of this path): a starting recruitment mini-game using the Subplan 08 verb set.
  - ~30 prospects shown with partially revealed attributes.
  - Player must pick 10 to commit to the program.
  - Apply Scout / Contact / Visit / Promise verbs to influence which prospects accept (with a generous starting slot budget specifically for new-game).
  - On commit, the chosen prospects enter the save as the year-1 roster, deliberately weaker than preset clubs (this is the rebuild fantasy).
- Estimated ~10-15 minutes for the full path. The mini-game IS the recruiting tutorial — by the end of the flow the player has used every verb at least once.

**Files anticipated:**
- `frontend/src/components/SaveMenu.tsx` (substantial rewrite — currently jumps to game on club pick; now branches to two paths)
- New: `frontend/src/components/new-game/TakeOverPath.tsx`
- New: `frontend/src/components/new-game/BuildFromScratchPath.tsx`
- New: `frontend/src/components/new-game/IdentityStep.tsx`
- New: `frontend/src/components/new-game/CoachStep.tsx`
- New: `frontend/src/components/new-game/StartingRecruitmentStep.tsx`
- `src/dodgeball_sim/persistence.py` (extended save creation that accepts custom club identity)
- `src/dodgeball_sim/career_setup.py` (extended career setup to accept custom roster)
- `src/dodgeball_sim/identity.py` (custom identity persistence)
- `src/dodgeball_sim/server.py` (new endpoint: `/api/saves/build-from-scratch` accepting full custom-club + chosen-roster payload)
- `src/dodgeball_sim/recruitment.py` (one-shot starting-recruitment slot budget separate from in-season weekly budget)

**Verification gates:** build + pytest green; new endpoint tested for happy-path + validation errors (duplicate club name, invalid color, roster size mismatch); manual smoke confirms both paths reach Match Week with correct save state.
