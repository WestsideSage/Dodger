# V2-C Build a Club Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate Build a Club as a deterministic expansion career path with custom identity, a weak legal roster, default lineup, scouting/recruitment initialization, and bye-safe scheduling.

**Architecture:** Add pure helper builders in `manager_gui.py` for expansion club identity and roster generation, then add an `initialize_build_a_club_career` path that reuses the existing Manager Mode persistence flow. Use existing scheduler odd-club bye handling, but update tests and docstring to reflect that byes are implemented.

**Tech Stack:** Python dataclasses, Tkinter Manager Mode helpers, SQLite persistence, pytest.

---

## File Map

- Modify `src/dodgeball_sim/manager_gui.py`: expansion club helpers and career initializer.
- Modify `src/dodgeball_sim/scheduler.py`: update stale odd-club docstring.
- Modify `tests/test_manager_gui.py`: expansion identity, roster, career init, recruitment profile, and Take Over regression tests.
- Modify `tests/test_scheduler.py`: odd-club bye schedule coverage.
- Update `docs/specs/MILESTONES.md` after full verification.

---

### Task 1: Expansion Helpers

- [ ] Add failing tests for stable expansion club id, custom identity, and expansion roster top-six mean 8-16 OVR below curated average.
- [ ] Implement `build_expansion_club` and `generate_expansion_roster`.
- [ ] Run focused tests.

### Task 2: Build A Club Career Initialization

- [ ] Add failing test for `initialize_build_a_club_career`: persists `career_path=build_club`, selected custom club, seven clubs total, default lineup, scouting pool, recruitment profile, and active cursor.
- [ ] Implement initializer using existing save helpers and V2-B profile seeding.
- [ ] Run focused tests.

### Task 3: Bye Handling

- [ ] Add failing scheduler test for odd club count: no `__bye__` scheduled matches, each real club has one bye, deterministic match count.
- [ ] Update scheduler docstring to remove stale "not implemented" text.
- [ ] Run scheduler tests.

### Task 4: Verification

- [ ] Run `python -m pytest tests/test_manager_gui.py tests/test_scheduler.py -q -p no:cacheprovider`.
- [ ] Run `python -m pytest tests/test_regression.py tests/test_recruitment_domain.py tests/test_v2b_recruitment_persistence.py -q -p no:cacheprovider`.
- [ ] Run `python -m pytest -q -p no:cacheprovider`.
- [ ] Mark V2-C shipped in `docs/specs/MILESTONES.md`.

---

## Self-Review

- Spec coverage: expansion identity, weaker roster tolerance, recruitment/scouting initialization, bye behavior, and Take Over preservation are covered.
- Placeholder scan: all tasks include concrete files and commands.
- Type consistency: helper names match tests.

