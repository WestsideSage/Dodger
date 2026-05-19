# Subplan 08: Dynasty Office Recruit Sub-Tab + Verb Set + Slot Economy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Restructure Dynasty Office around sub-tabs (`Recruit` default, `History` stub) and implement the full recruiting verb set with a weekly slot economy that ties Program Credibility and Staff Market to concrete in-game effects.

**Dependencies:** Subplan 04. Parallel-safe with 05, 06, 07, 09.

**Acceptance criteria (from 00-MAIN.md):**
- `DynastyOffice` has sub-tab nav: `Recruit` (default) / `History` (stub).
- Recruit sub-tab implements 6 verbs (Scout, Contact, Visit, Make Promise, Pitch Angle, Sign).
- Weekly slot budget rendered (current/max). Default: 3 Scout, 5 Contact, 1 Visit.
- Each prospect card shows: name, hometown, archetype, OVR band, fit_score (GRADE ONLY), interest evidence, verbs.
- Scout reveals attributes incrementally (band → stat → personality).
- Pitch Angle locks for the season once chosen.
- Sign action is disabled until Signing Day ceremony.
- Active promises rendered; hovering shows fulfillment progress.
- Credibility strip shows tier + slot grants.
- Staff strip shows current staff with effects; Staff Market opens as a modal.
- **LOCKED DECISION:** Program Priorities panel (from Subplan 04) moves to a small Settings Modal accessible from the Dynasty Office header.

---

- [ ] **Step 1: Test & Backend for Slot Economy**

Create `tests/test_recruitment_slots.py`. Test that the default budget (3 Scout, 5 Contact, 1 Visit) is returned by the API.
Update `src/dodgeball_sim/recruitment.py` and `server.py` to expose `budget: { scout: [0, 3], contact: [0, 5], visit: [0, 1] }`.
Commit.

- [ ] **Step 2: Test & Backend for Recruiting Verbs**

In `tests/test_recruitment_verbs.py`, test the POST endpoints for Scout, Contact, Visit.
Ensure backend deducts slots.
Implement the endpoints in `server.py`. Commit.

- [ ] **Step 3: Test & Backend for Pitch Angle (Season Lock) and Sign Gating**

Write tests asserting Pitch Angle cannot be changed twice in one season.
Write tests asserting `/api/recruiting/sign` returns `403` if save state is not `signing_day`.
Implement logic in backend. Convert `fit_score` and `interest` floats to Grade strings (e.g. "A-", "Strong") in the payload before transmission. Commit.

- [ ] **Step 4: Create ProspectCard & Sub-components**

Create `frontend/src/components/dynasty/ProspectCard.tsx`. Ensure it displays the verbs, checks remaining slots before enabling them, and explicitly renders `fit_score` as the grade string.
Create `CredibilityStrip.tsx` and `StaffMarketModal.tsx`. Commit.

- [ ] **Step 5: Relocate Program Priorities & Create Dynasty Layout**

In `DynastyOffice.tsx`, create a `<SettingsModal>` component. Move the existing "Program Priorities" department-orders mapping into this modal. Trigger it from a gear icon in the page header.
Implement the sub-tab navigation (`Recruit` vs `History`). Render the `History` stub.
Render `Recruit` layout: Credibility left, Staff right, Prospects center.
Render Active Promises in the Credibility strip. Commit.

- [ ] **Step 6: Cross-cutting principle check (No Float Leaks)**

Run `npm run build` & `pytest -q`.
**Critical Check:** Verify that `fit_score` is a grade. Verify that `interest` is qualitative text or a grade. Ensure no raw numbers for these fields reach the DOM.
```bash
git commit --amend --no-edit
```