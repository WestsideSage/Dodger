# Subplan 09 (STUB): Standings Polish

> **Status:** STUB. Detailed task breakdown authored after Wave 1 ships. Read `../00-MAIN.md` first.

**Goal:** Replace cryptic column abbreviations with full words and add a recent-matches sidebar that absorbs old NewsWire-style "team beat team" content.

**Dependencies:** Subplan 01 (NewsWire export already removed). Parallel-safe with 05-08.

**Acceptance criteria:**
- Table column headers use full words: `Wins`, `Losses`, `Ties`, `Points For`, `Points Against`, `Differential`, `Streak`. (Adapt to the actual columns the sim exposes.)
- Compact display in narrow viewports may collapse to 2-letter abbreviations (`W`, `L`, `T`) but the default desktop view shows full words.
- Recent matches sidebar on the Standings page lists the last ~5 league results across all teams, written in the templated voice from Subplan 10 (stub copy is acceptable in Wave 2; voice library replaces the templates in Wave 3).
- Each row in the Standings table is clickable; clicking deep-links to a team detail view. The team detail view itself is finalized in Subplan 14 (League History) — for Wave 2, link to a placeholder route.
- Visual treatment: more breathing room, larger logos, clear separation between the user's team row and the rest.

**Files anticipated:**
- `frontend/src/components/LeagueContext.tsx` (Standings export — full rewrite of the table layout)
- New: `frontend/src/components/standings/RecentMatchesSidebar.tsx`
- `src/dodgeball_sim/server.py` (extended Standings endpoint payload to include recent matches league-wide)

**Verification gates:** build + pytest green; manual smoke confirms full column names, recent-matches sidebar populated, click-through links work.
