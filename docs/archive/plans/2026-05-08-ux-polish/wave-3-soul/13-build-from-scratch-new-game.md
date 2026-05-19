# Subplan 13: Build-From-Scratch New Game Flow

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Replace the single-input new save flow (name + preset club) with a two-path entry: `Take Over a Program` (fast, polished current flow) and `Build a Program From Scratch` (custom identity → coach → recruit-your-starting-roster mini-game).

**Dependencies:** Subplan 08 (recruiting verb set must exist). Parallel-safe with 10, 11, 12, 14, 15.

**Acceptance criteria (from 00-MAIN.md):**
- **Take Over a Program path:** Pick from preset clubs (existing flow). Optional rename/recolor. Optional coach backstory tile (affects starting Credibility). ~60 seconds end-to-end.
- **Build a Program From Scratch path:**
  - Identity step: club name, abbreviation, primary/secondary colors, city, conference.
  - Coach step: your name, backstory tile.
  - Roster step (mini-game): ~30 prospects shown. Player uses Scout/Contact/Visit verbs with a generous one-shot slot budget to pick 10 prospects. Chosen prospects become Year-1 roster.
- Estimated ~10-15 minutes for the full path. The mini-game IS the recruiting tutorial.

---

- [ ] **Step 1: Write backend tests for new save endpoints**

Create `tests/test_new_game_flow.py`:
```python
def test_build_from_scratch_endpoint():
    # Test POST /api/saves/build-from-scratch payload
    # Assert custom roster is saved, custom club is created, state is Pre-Match
```
Run, fail.

- [ ] **Step 2: Add Mini-Game Endpoints**

In `src/dodgeball_sim/server.py`, add `/api/saves/starting-prospects` which generates a one-shot prospect pool of 30 players.
Implement `/api/saves/build-from-scratch` which accepts the final selection of 10 players, creates the custom club in the DB, inserts the players, and initializes the manager career. Pass tests. Commit.

- [ ] **Step 3: Create UI Steps**

Create `frontend/src/components/new-game/IdentityStep.tsx` and `CoachStep.tsx` with forms for Name, City, Colors, and Coach Backstory.
Create `frontend/src/components/new-game/StartingRecruitmentStep.tsx`. This renders a simplified `ProspectCard` list, uses local state for a generous slot budget (e.g. 15 Scouts, 20 Contacts), and a "Commit Roster (X/10)" button. Commit.

- [ ] **Step 4: Rewrite SaveMenu.tsx**

In `frontend/src/components/SaveMenu.tsx`, create the initial branching screen: two large cards ("Take Over a Program" vs "Build a Program from Scratch").
Route the paths appropriately. "Take Over" flows into the existing preset selector. Commit.

- [ ] **Step 5: Cross-cutting principle check**

Run `npm run build` & `pytest -q`.
Verify the mini-game uses qualitative labels (grades) for Fit, not floats. Ensure the save creates correctly.
```bash
git commit --amend --no-edit
```