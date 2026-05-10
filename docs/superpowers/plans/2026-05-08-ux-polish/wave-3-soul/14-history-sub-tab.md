# Subplan 14: History Sub-Tab (My Program + League Toggle)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Flesh out the `History` sub-tab in Dynasty Office (stubbed in Subplan 08). Two views: `My Program` (your team's arc) and `League` (every program's arc, dynasty rankings, all-time records, Hall of Fame).

**Dependencies:** Subplan 08. Parallel-safe with 10, 11, 12, 13, 15.

**Acceptance criteria (from 00-MAIN.md):**
- Toggle: `My Program | League` in the `History` sub-tab.
- My Program view:
  - Hero strip: "How it started ↔ How it finished" cards.
  - Milestone timeline (horizontal): beads for first win, awards, rivalry wins.
  - Alumni lineage: departed players listed forever.
  - Banner shelf: championships and awards rendered as visual trophies.
- League view:
  - Program directory: every team, clickable to their My-Program view.
  - Dynasty rankings: most championships, longest win streak.
  - All-time league records & Hall of Fame.
- **Auto-population:** All entries auto-generate from sim history. Departed players persist forever.

---

- [ ] **Step 1: Write backend tests for History endpoints**

Create `tests/test_dynasty_history.py` testing `/api/history/my-program` and `/api/history/league`. Ensure `alumni` and `timeline` data are present. Run, fail.

- [ ] **Step 2: Implement History Data Layer**

In `src/dodgeball_sim/server.py`, add the `/api/history/` endpoints.
Query `career_state`, `awards`, `match_records`, and retired players from the DB. Pass tests. Commit.

- [ ] **Step 3: Create MyProgram Components**

Create `frontend/src/components/dynasty/history/MyProgramView.tsx`.
Create sub-components: `MilestoneTimeline.tsx`, `AlumniLineage.tsx`, `BannerShelf.tsx`.
Use JSX structure to visually represent the horizontal timeline and banner shelf. Commit.

- [ ] **Step 4: Create League Components**

Create `frontend/src/components/dynasty/history/LeagueView.tsx`, `ProgramDirectory.tsx`, `HallOfFame.tsx`. Commit.

- [ ] **Step 5: Wire History Sub-Tab**

Update `frontend/src/components/dynasty/HistorySubTab.tsx` (the stub from Subplan 08).
Add the toggle state for `My Program` vs `League`. Render the respective components. Commit.

- [ ] **Step 6: Cross-cutting principle check**

Run `npm run build` & `pytest -q`.
Verify NO manual logging inputs are present (it's entirely read-only auto-population).
```bash
git commit --amend --no-edit
```