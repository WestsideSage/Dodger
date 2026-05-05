# V2-B Recruitment Domain Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the V1 one-rookie Draft beat with deterministic contested recruitment rounds where AI clubs pursue prospects from public boards and the user competes using V2-A private scouting information.

**Architecture:** Add a pure `recruitment_domain.py` for profiles, boards, prepared round offers, conflict resolution, and recap data. Add persistence helpers for the new recruitment tables, then route Manager Mode's off-season Draft beat through the canonical prospect-to-player signing path.

**Tech Stack:** Python dataclasses, SQLite persistence helpers, pytest, Tkinter Manager Mode helper tests.

---

## File Map

- Create `src/dodgeball_sim/recruitment_domain.py`: pure recruitment profiles, board scoring, round prep, offer resolution.
- Modify `src/dodgeball_sim/persistence.py`: add recruitment tables and load/save helpers.
- Modify `src/dodgeball_sim/manager_gui.py`: replace V1 Draft beat with Recruitment Day helpers and UI.
- Modify `src/dodgeball_sim/recruitment.py`: keep generation helpers; add no AI logic.
- Add `tests/test_recruitment_domain.py`: pure board/round tests.
- Add/modify `tests/test_v2b_recruitment_persistence.py`: schema and idempotency tests.
- Modify `tests/test_manager_gui.py`: Recruitment Day row/recap helper tests.

---

### Task 1: Pure Recruitment Domain

**Files:**
- Create: `src/dodgeball_sim/recruitment_domain.py`
- Test: `tests/test_recruitment_domain.py`

- [ ] Write failing tests for deterministic club profiles, board ranking, prepared AI offers, user/AI conflict resolution, and visible snipe reason.
- [ ] Implement dataclasses: `RecruitmentProfile`, `RecruitmentBoardRow`, `RecruitmentOffer`, `RecruitmentSigning`, `RecruitmentRoundResult`.
- [ ] Implement `build_recruitment_profile`, `build_recruitment_board`, `prepare_ai_offers`, and `resolve_recruitment_round`.
- [ ] Ensure `evaluation_quality` only reduces public-score noise and never reads private scouting state.
- [ ] Run `python -m pytest tests/test_recruitment_domain.py -q -p no:cacheprovider`.

---

### Task 2: Recruitment Persistence

**Files:**
- Modify: `src/dodgeball_sim/persistence.py`
- Test: `tests/test_v2b_recruitment_persistence.py`

- [ ] Write failing schema test for `club_recruitment_profile`, `recruitment_board`, `recruitment_round`, `recruitment_offer`, `recruitment_signing`, and `prospect_market_signal`.
- [ ] Add schema migration tables.
- [ ] Add save/load helpers for profiles, board rows, prepared/resolved rounds, offers, signings, and market signals.
- [ ] Add idempotency tests proving prepared rounds and resolved rounds reload without rerolling or duplicating signings.
- [ ] Run `python -m pytest tests/test_v2b_recruitment_persistence.py -q -p no:cacheprovider`.

---

### Task 3: Canonical Prospect Signing

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py`
- Modify: `src/dodgeball_sim/persistence.py`
- Test: `tests/test_manager_gui.py`

- [ ] Write failing test proving the old `_sign_best_rookie` path routes through a canonical prospect-to-player signing helper or is bypassed by Recruitment Day.
- [ ] Implement a single helper that signs one `Prospect` into a club roster, persists trajectory, marks prospect signed, and removes it from available recruitment rows.
- [ ] Update off-season continuation so V1 auto-sign fallback no longer signs a separate free-agent rookie when V2-A prospect pool exists.
- [ ] Run `python -m pytest tests/test_manager_gui.py -q -p no:cacheprovider`.

---

### Task 4: Manager Recruitment Day UI Helpers

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py`
- Test: `tests/test_manager_gui.py`

- [ ] Write failing tests for Recruitment Day display rows: public market risk, private scouting fields, shortlist state, AI ticker, snipe callout, and recap.
- [ ] Implement pure helper builders before Tkinter wiring.
- [ ] Replace Draft beat body with Recruitment Day render path when prospect pool exists.
- [ ] Preserve old-save fallback for legacy free-agent Draft if no prospect pool exists.
- [ ] Run `python -m pytest tests/test_manager_gui.py -q -p no:cacheprovider`.

---

### Task 5: V2-B Verification

**Files:**
- Update docs only if implementation reveals a verified spec adjustment.

- [ ] Run `python -m pytest tests/test_recruitment_domain.py tests/test_v2b_recruitment_persistence.py tests/test_manager_gui.py -q -p no:cacheprovider`.
- [ ] Run `python -m pytest tests/test_regression.py tests/test_v2a_scouting_integration.py tests/test_v2a_scouting_persistence.py -q -p no:cacheprovider`.
- [ ] Run `python -m pytest -q -p no:cacheprovider`.
- [ ] Update `docs/specs/MILESTONES.md` V2-B row to shipped only after all tests pass.

---

## Self-Review

- Spec coverage: plan covers pure AI boards, public-only evaluation quality, prepared-round persistence, conflict resolution, canonical signing, UI, and verification.
- Placeholder scan: each task has concrete files and commands; implementation details are bounded by the approved spec.
- Type consistency: names match V2-B design terms.

