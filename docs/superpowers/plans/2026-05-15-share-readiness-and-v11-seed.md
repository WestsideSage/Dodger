# Share Readiness And V11 Seed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current web loop more truthful to the approved UX vision and land the first real V11 slice: visible AI weekly planning that can affect AI match behavior.

**Architecture:** First, align the frontend shell with the locked four-tab IA and make offseason/recruiting states self-explanatory. Then add a small backend-only AI planning module that chooses weekly intents from visible season context, persists those plans, applies them to AI matches through the existing command-plan pathway, and exposes the latest visible AI approach through the standings payload.

**Tech Stack:** React 19 + TypeScript + Vite frontend, FastAPI/Python backend, pytest, Playwright.

---

### Task 1: Make top-level navigation truthful

**Files:**
- Modify: `frontend/src/App.tsx`
- Test: `tests/e2e/command-center-aftermath.spec.ts`

- [ ] Remove unfinished top-level tabs so the app only exposes Match Week / Roster / Dynasty Office / Standings.
- [ ] While the save is in offseason, keep Match Week available and render the other three tabs disabled with explicit offseason titles instead of letting them look live.
- [ ] Re-run the focused browser regression and verify the nav still supports the weekly loop.

### Task 2: Clarify recruiting affordances

**Files:**
- Modify: `frontend/src/components/dynasty/ProspectCard.tsx`
- Test: browser verification in Dynasty Office

- [ ] Add explicit helper text and button titles for exhausted recruiting verbs so a disabled action explains itself.
- [ ] Keep the current slot economy intact; only improve truthfulness and legibility.
- [ ] Re-check Dynasty Office in desktop and mobile layouts.

### Task 3: Seed V11 AI weekly planning

**Files:**
- Create: `src/dodgeball_sim/ai_program_manager.py`
- Modify: `src/dodgeball_sim/use_cases.py`
- Modify: `src/dodgeball_sim/command_week_service.py`
- Modify: `src/dodgeball_sim/web_status_service.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/components/LeagueContext.tsx`
- Test: `tests/test_ai_program_manager.py`
- Test: `tests/test_server.py`

- [ ] Add deterministic AI weekly intent selection from visible season context.
- [ ] Build AI weekly plans with honest tactic values and playable lineups.
- [ ] Persist/apply AI plans before AI matches simulate so the choice changes real match behavior rather than being decorative.
- [ ] Expose each club's latest visible approach in the standings payload and render it in the standings table.
- [ ] Cover the planner with unit tests and the API surface with a regression test.

### Task 4: Verify the full pass

**Files:**
- Verify: `frontend/src/App.tsx`
- Verify: `frontend/src/components/dynasty/ProspectCard.tsx`
- Verify: `src/dodgeball_sim/ai_program_manager.py`
- Verify: `frontend/src/components/LeagueContext.tsx`

- [ ] Run focused backend tests for the new planner and standings payload.
- [ ] Run frontend build.
- [ ] Run the focused Playwright weekly-loop regression.
- [ ] Browser-check desktop and mobile nav, Dynasty Office recruit cards, and Standings with AI approaches visible.
