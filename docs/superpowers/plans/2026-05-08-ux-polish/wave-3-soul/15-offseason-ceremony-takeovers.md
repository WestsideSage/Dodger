# Subplan 15 (STUB): Offseason Ceremony Takeovers

> **Status:** STUB. Detailed task breakdown authored after Wave 2 ships. Read `../00-MAIN.md` first.

**Goal:** Replace the current offseason flat-checklist for five specific beats with full-screen ceremony takeovers — paced reveals that feel like events, not menu items.

**Dependencies:** Subplan 14 (History sub-tab — ceremonies write outcomes there). Subplan 10 (voice library — ceremony copy uses templated voice). Parallel-safe with 11, 12, 13.

**Acceptance criteria:**

**Five ceremony surfaces, each replacing routine offseason content when their save-state beat fires:**

1. **Awards Night** — end of season, before offseason starts.
   - Conference awards revealed one-by-one with stage-spotlight reveal animation.
   - Your players honored get their own card showing their season stats.
   - Big league moments narrated via voice library.
   - Outcomes auto-write to History banner shelf and Hall of Fame consideration.

2. **Graduation** — early offseason.
   - Each departing senior gets their own card revealed in sequence: their full career arc (year-by-year OVR), peak stats, place in alumni lineage, future projection (e.g., "Pro prospects: Strong").
   - Auto-write to alumni lineage in History My Program view.

3. **Coaching Carousel** — mid-offseason; SKIPPED if no staff movement this offseason.
   - Dramatic "[Staff name] has accepted an offer at [club]" reveal.
   - Replacement hire flow embedded in the ceremony (uses Subplan 08 staff verbs).
   - Auto-writes movement to History.

4. **Signing Day** — late offseason; THE highest-polish ceremony.
   - Prospects you've worked on through the season commit one-by-one.
   - Tension on borderline prospects — visible interest meter, then reveal.
   - Successful signings drop into the Year+1 roster preview at the bottom of the screen.
   - Failed signings narrated with the recruit's reasoning (where they went, why).
   - Auto-writes Year+1 incoming class to History.

5. **New Season Eve** — final offseason beat.
   - Team photo of next year's roster (composite of player initials/portraits).
   - Schedule reveal animation.
   - Season prediction headline ("picked 4th in conference").
   - Single CTA: `Start the Season` → kicks save back into in-season Match Week pre-sim mode.

**Common requirements across all five:**
- Each ceremony is paced — content reveals over 30-90 seconds, skippable via spacebar / click-anywhere.
- Each ceremony fires automatically when its save-state beat is reached; the player can NOT skip the ceremony list (but CAN skip individual reveal animations).
- All copy uses the voice library (Subplan 10). No raw debug strings.
- Reduced-motion mode replaces transitions with instant cuts but keeps the per-beat structure.

**Files anticipated:**
- `src/dodgeball_sim/offseason_beats.py`, `src/dodgeball_sim/offseason_ceremony.py` (existing — extend to expose the five ceremony beat types and their payloads)
- `frontend/src/components/MatchWeek.tsx` (offseason mode — route to ceremony components based on beat)
- New: `frontend/src/components/ceremonies/AwardsNight.tsx`
- New: `frontend/src/components/ceremonies/Graduation.tsx`
- New: `frontend/src/components/ceremonies/CoachingCarousel.tsx`
- New: `frontend/src/components/ceremonies/SigningDay.tsx`
- New: `frontend/src/components/ceremonies/NewSeasonEve.tsx`
- New: `frontend/src/components/ceremonies/CeremonyShell.tsx` (shared layout/animation primitives)
- `src/dodgeball_sim/server.py` (ceremony beat detection in offseason endpoints)

**Verification gates:** build + pytest green; ceremony beat detection covered by tests (specifically: ceremonies fire on the right save state and skip when applicable); manual smoke runs a complete offseason cycle with all five ceremonies firing and auto-writes to History confirmed.
