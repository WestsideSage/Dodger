# Subplan 08 (STUB): Dynasty Office Recruit Sub-Tab + Verb Set + Slot Economy

> **Status:** STUB. Detailed task breakdown authored after Wave 1 ships. Read `../00-MAIN.md` first.

**Goal:** Restructure Dynasty Office around sub-tabs (`Recruit` default, `History` stub) and implement the full recruiting verb set with a weekly slot economy that ties Program Credibility and Staff Market to concrete in-game effects.

**Dependencies:** Subplan 04 (department orders already moved to Dynasty Office's Program Priorities panel — that panel may be reorganized by this subplan into the Recruit sub-tab or marked for relocation). Parallel-safe with 05, 06, 07, 09.

**Acceptance criteria:**

**Sub-tab structure:**
- `DynastyOffice` adds top-of-page sub-tab nav: `Recruit` (default) and `History`.
- `History` is a stub for Wave 3 Subplan 14.

**Recruit sub-tab (the hero, ~70% of page real estate):**
- Six verbs implemented: `Scout`, `Contact`, `Visit`, `Make Promise`, `Pitch Angle`, `Sign`.
- Weekly slot budget rendered prominently (current/max for each: Scout, Contact, Visit).
- Each prospect card shows: name · hometown · public archetype · public OVR band · fit_score (rendered as label/grade, NEVER a number) · interest evidence · available verb buttons.
- Scout reveals attributes incrementally — first pass narrows OVR band, second reveals one specific stat, third reveals more, fourth reveals personality. Tracked per-prospect.
- Pitch Angle locks for the season once chosen — UI prevents re-selection until offseason.
- Sign action is disabled until Signing Day ceremony (Wave 3 Subplan 15).
- Active promises rendered with current status; hovering shows fulfillment progress.

**Credibility strip (left, ~15%):**
- Tier label + grade + slot grants from current tier (e.g., "Tier B → 3 Scout, 5 Contact, 1 Visit per week").
- Evidence list for what's helping/hurting credibility.

**Staff strip (right, ~15%):**
- Current staff with their effects on slot economy (e.g., "Coordinator Wallace: +1 Scout slot/wk").
- Staff Market opens as a modal, NOT a peer panel — modal shows hireable candidates with their effect on slot economy before commit.

**Files anticipated:**
- `frontend/src/components/DynastyOffice.tsx` (substantial rewrite around sub-tabs)
- New: `frontend/src/components/dynasty/RecruitSubTab.tsx`
- New: `frontend/src/components/dynasty/HistorySubTab.tsx` (stub, gets fleshed out in Subplan 14)
- New: `frontend/src/components/dynasty/ProspectCard.tsx`
- New: `frontend/src/components/dynasty/CredibilityStrip.tsx`
- New: `frontend/src/components/dynasty/StaffStrip.tsx`
- New: `frontend/src/components/dynasty/StaffMarketModal.tsx`
- `src/dodgeball_sim/recruitment.py` and/or `recruitment_domain.py` (verbs, slot budget, partial-reveal scouting state)
- `src/dodgeball_sim/scouting_center.py` (incremental reveal tracking)
- `src/dodgeball_sim/server.py` (new endpoints for verb actions: `/api/recruiting/scout/{prospect_id}`, `/api/recruiting/contact/{prospect_id}`, `/api/recruiting/visit/{prospect_id}`, `/api/recruiting/pitch-angle`, `/api/staff/hire/{candidate_id}`)

**Critical constraint:** No numeric `fit_score` or `interest` value rendered to the player. Use grade labels (e.g., "Strong fit", "Lukewarm", "Cold") and visual meters.

**Decision deferred to authoring:** what to do with the temporary "Program Priorities" panel from Subplan 04. Options:
- Keep on Dynasty Office but relocate to a sub-section of Recruit (or a settings panel).
- Move to a separate "Program Settings" page accessible from Dynasty Office's header.
- Collapse into the Pitch Angle / Credibility model (department orders may overlap conceptually).

The orchestrator should consult `00-MAIN.md` cross-cutting principles when authoring — specifically, "if the player's answer is the same 9 weeks in a row, don't surface it weekly".

**Verification gates:** build + pytest green; tests cover slot budget enforcement, partial-reveal sequencing, pitch-angle season lock, sign-action gating; manual smoke confirms no numeric leaks.
