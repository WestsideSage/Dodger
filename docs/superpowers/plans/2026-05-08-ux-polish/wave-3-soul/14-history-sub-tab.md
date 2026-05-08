# Subplan 14 (STUB): History Sub-Tab (My Program + League Toggle)

> **Status:** STUB. Detailed task breakdown authored after Wave 2 ships. Read `../00-MAIN.md` first.

**Goal:** Flesh out the `History` sub-tab in Dynasty Office (stubbed in Subplan 08). Two views: `My Program` (your team's arc — "how it started ↔ how it finished") and `League` (every program's arc, dynasty rankings, all-time records, Hall of Fame).

**Dependencies:** Subplan 08 (sub-tab structure exists). Parallel-safe with 10, 11, 12, 13, 15. Subplan 09 deep-links from Standings into League view here.

**Acceptance criteria:**

**Sub-tab structure:**
- Within Dynasty Office's `History` sub-tab, a toggle: `My Program | League`.

**My Program view:**
- Hero strip: side-by-side "How it started ↔ How it finished" cards.
  - Left: Year 1 — starting roster (with photos/initials), starting OVR, starting Credibility grade, coach backstory tile from Subplan 13.
  - Right: Today — current roster, current OVR, current Credibility grade, lifetime W/L across all played seasons.
- Milestone timeline (horizontal): beads marking first win, first conference championship, signing of a now-elite recruit, awards, broken records, rivalry-shifting wins.
- Alumni lineage: every departed player listed forever — peak attributes, awards under your tenure, championship years, the recruiting cycle they came from.
- Banner shelf: championships and major awards rendered as visual trophies/banners across the top.

**League view:**
- Program directory: every team in the league. Click any team → opens THAT team's My-Program-style view (same template).
- Dynasty rankings: most championships all-time, longest win streak, most Elite-tier players developed.
- All-time league records: per-match, per-season, per-career. Each record shows player + program + when set; updates visibly as records break.
- Hall of Fame: peak players from any program across history. Filterable by era / program.
- Rivalries directory: top historical rivalries league-wide, ranked by intensity / closeness.

**Auto-population (CRITICAL):**
- All entries auto-generate from sim event history. No manual logging.
- Departed players persist forever in alumni lineage (no garbage collection).
- Records update on each match completion.
- Banners append on championship wins.

**Files anticipated:**
- `frontend/src/components/dynasty/HistorySubTab.tsx` (replace stub from Subplan 08)
- New: `frontend/src/components/dynasty/history/MyProgramView.tsx`
- New: `frontend/src/components/dynasty/history/LeagueView.tsx`
- New: `frontend/src/components/dynasty/history/MilestoneTimeline.tsx`
- New: `frontend/src/components/dynasty/history/AlumniLineage.tsx`
- New: `frontend/src/components/dynasty/history/BannerShelf.tsx`
- New: `frontend/src/components/dynasty/history/ProgramDirectory.tsx`
- New: `frontend/src/components/dynasty/history/HallOfFame.tsx`
- `src/dodgeball_sim/career.py`, `src/dodgeball_sim/career_state.py` (alumni persistence — verify departed players survive offseason cleanup)
- `src/dodgeball_sim/records.py`, `src/dodgeball_sim/awards.py`, `src/dodgeball_sim/rivalries.py` (existing — wire into history endpoints)
- `src/dodgeball_sim/meta.py` (cross-program meta history)
- `src/dodgeball_sim/server.py` (new endpoints: `/api/history/my-program`, `/api/history/league`, `/api/history/program/{club_id}`)

**Verification gates:** build + pytest green; tests confirm departed players persist across season transitions; tests for record auto-update; manual smoke confirms a multi-season save renders rich History data.
