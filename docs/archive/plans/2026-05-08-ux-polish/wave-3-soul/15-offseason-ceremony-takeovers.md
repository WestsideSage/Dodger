# Subplan 15: Offseason Ceremony Takeovers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Replace the current offseason flat-checklist for five specific beats with full-screen ceremony takeovers — paced reveals that feel like events, not menu items.

**Dependencies:** Subplan 14, Subplan 10. Parallel-safe with 11, 12, 13.

**Acceptance criteria (from 00-MAIN.md):**
1. **Awards Night** — stage-spotlight animation, player cards, writes to History banner shelf.
2. **Graduation** — departing seniors revealed, peak stats, projected future. Writes to alumni lineage.
3. **Coaching Carousel** — staff movement reveals, replacement hire flow.
4. **Signing Day** — recruited prospects commit one-by-one. Tension meter. Writes to incoming class history.
5. **New Season Eve** — team photo, schedule reveal, prediction headline. `Start the Season` CTA.
- Paced reveals (30-90s), skippable via spacebar.
- Cannot skip the ceremony list (must play automatically on state entry).
- Reduced-motion mode cuts instantly.

---

- [ ] **Step 1: Test & Backend for Ceremony Payloads**

Update `tests/test_offseason_ceremony.py` to ensure `/api/offseason/beat` returns structured data suitable for paced reveals (e.g., list of awards, list of graduating seniors). Run, fix if needed. Commit.

- [ ] **Step 2: Create CeremonyShell Component**

Create `frontend/src/components/ceremonies/CeremonyShell.tsx` to handle the spacebar-skip, reduced-motion logic, and staged-reveal indexing (similar to Subplan 06 Aftermath but reusable). Commit.

- [ ] **Step 3: Create Individual Ceremony Components**

Create `AwardsNight.tsx`, `Graduation.tsx`, `CoachingCarousel.tsx`, `SigningDay.tsx`, `NewSeasonEve.tsx`. Each uses `CeremonyShell`. Implement custom animations (like stage spotlight for Awards) using CSS classes. Commit.

- [ ] **Step 4: Wire Offseason.tsx Router**

In `frontend/src/components/Offseason.tsx`, detect the current `beat_index` / `key` and render the appropriate Ceremony component instead of the flat generic checklist, when applicable. Commit.

- [ ] **Step 5: Cross-cutting principle check**

Run `npm run build` & `pytest -q`.
Verify spacebar skipping works. Verify NO generic debug strings are shown (ensure templates from Subplan 10 voice library are passed through).
```bash
git commit --amend --no-edit
```