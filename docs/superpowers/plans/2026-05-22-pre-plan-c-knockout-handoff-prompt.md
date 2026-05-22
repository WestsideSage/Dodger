# Handoff Prompt — Pre-Plan-C Knockout (for Gemini)

Copy everything between the `=====` markers into Gemini as the initial prompt. The repo path assumes Windows; adapt slashes if Gemini's environment differs.

=====

You are implementing a closed, well-scoped bug-fix pass in the **Dodgeball Manager** repo at `C:\GPT5-Projects\Dodgeball Simulator`. This is a Python (3.11) + TypeScript/React codebase. The work is already designed and planned — your job is to execute it task-by-task, with discipline.

## Read these first, in this order

1. `AGENTS.md` — repo rules, workflow, architecture snapshot, "Current Facts Worth Remembering." Pay attention to the engine-integrity rules.
2. `docs/STATUS.md` — current build state and the "Open Work And Known Gaps" list.
3. `docs/superpowers/specs/2026-05-22-pre-plan-c-knockout-design.md` — the design spec for this work, with scope boundaries.
4. `docs/superpowers/plans/2026-05-22-pre-plan-c-knockout.md` — **THE PLAN. This is your task list.** 13 tasks, ordered easiest → hardest. Each task has explicit files, steps, and commit messages.
5. `docs/qa/2026-05-21-browser-playthrough-audit.md` — the QA audit that surfaced the bugs. Use it as the canonical description of the user-visible symptom for each bug; the plan tells you what to do about it.

You do NOT need to read other docs or specs unless a task points you to one. Stay narrow.

## The mission

Execute every task in the plan, in order, top to bottom. Each task corresponds to one bug (or one cleanup item). Each task lands as **one git commit** using the commit message shown in the task's final step.

The plan is the contract. Do not improvise scope. Do not refactor adjacent code. Do not add features. Do not "while I'm in here, also clean up X." If you see something out of scope that genuinely needs attention, append a one-line note to a scratch file `docs/superpowers/plans/2026-05-22-pre-plan-c-knockout-followups.md` and keep moving.

## How to execute one task

1. **Read the task in the plan.** Note its `Files` block — that's the surface area.
2. **For tasks marked "Grep to locate":** the plan does not pin every line because the audit screenshots alone don't identify the exact component. Run the grep the task names. Read the surrounding code. Then apply the change template.
3. **TDD where the bug is observable in code (Tasks 2, 5, 9, 10, 11, 12):** write the failing test first, run it, see it fail, then implement, then see it pass.
4. **Manual repro tasks (Tasks 3, 4, 6, 7, 8):** these are frontend-only or copy-only. The plan tells you what to verify in the browser. You may not have a browser available; if so, do the build + lint verification, then describe in the commit message what a human should see when they manually verify.
5. **Verify before committing:** every task ends with `python -m pytest -q` green. Frontend tasks also end with `cd frontend && npm run build && npm run lint`.
6. **Commit exactly the message the plan shows.** One commit per task. Do not amend. Do not squash. Do not skip pre-commit hooks (no `--no-verify`).
7. **Mark the task's checkboxes done in the plan file as you complete each step.** This is the progress signal.

## Hard constraints

- **Do not touch the O1 engine balance.** This means: do not modify `accuracy_scale` / `catch_scale` in `config.py`, do not regenerate any golden log under `tests/golden_logs/`, do not change `compute_throw_probabilities`. O1 is explicitly out of scope and has its own future brief per `AGENTS.md` engine-integrity rules.
- **Do not pre-empt Plan C.** Bug 7.6 (disabled approach buttons), audit P0 narrative-on-loss, audit P1 round-by-round survivor ribbon — these belong to Plan C. If a task tempts you in that direction, stop and re-read the plan.
- **Do not add dependencies.** No new npm packages, no new pip requirements. Use what's already in `pyproject.toml` and `frontend/package.json`.
- **Do not change public APIs, routing, or auth behavior** unless a task explicitly requires it.
- **Do not delete or rename files** unless the task says so. The repo just went through a Tkinter scorched-earth cleanup; the structure is intentional.
- **Do not commit secrets, .env files, screenshots, or Playwright artifacts.** Task 1 is precisely about ignoring those.

## How to handle ambiguity

- **A grep returns multiple plausible files:** read the most recent commits touching those files (`git log --oneline -10 -- <file>`); pick the file the audit symptom would route through. Note your choice in the commit body.
- **A test name or fixture name in the plan does not exist in the file:** look at the *neighbouring* tests in the same file and reuse their fixtures. The plan's test code is a template, not a verbatim spec.
- **A downstream test breaks after your fix:** this is expected for Tasks 9 and 12 specifically (potential distribution; comeback heuristic). If the broken test asserted the old buggy behavior, update it with a code comment explaining the old expectation reflected the bug. Do NOT mask the bug to keep the test green.
- **You hit a genuine blocker — code state contradicts the plan, a fix would require a Plan C scope change, etc.:** stop. Do not push past it. Output a short note describing what you found and what you're stuck on, and wait for the human.

## Conventions

- **Python:** 3.11. Install with `python -m pip install -e .[dev]`. Test with `python -m pytest -q`.
- **Frontend:** in `frontend/`. Build with `npm run build`. Lint with `npm run lint`. No need to run dev server unless a task asks.
- **Imports inside `src/dodgeball_sim/`:** relative (`from .persistence import ...`). Inside `tests/`: absolute (`from dodgeball_sim.persistence import ...`).
- **Commit prefix:** `fix(audit-7.N): …` for the audit bugs, `fix(plan-a-followup): …` for Task 12, `chore: …` for Task 1, `docs: …` for Task 13. The plan shows the exact message for each.
- **Author identity:** use whatever the local `git config user.name` / `user.email` are. Do not modify git config.
- **Working directory:** `C:\GPT5-Projects\Dodgeball Simulator`. The web app entry is `python -m dodgeball_sim`.

## What "done" looks like

- All 13 tasks committed, one commit each, in plan order.
- `python -m pytest -q` green from the repo root (target ~795+ tests passing — the existing baseline as of 2026-05-22).
- `cd frontend && npm run build` clean, `npm run lint` clean.
- `docs/STATUS.md` updated (Task 13).
- `docs/qa/2026-05-21-browser-playthrough-audit.md` has a resolution table at the top (Task 13).
- The followups scratch file, if you created one, contains short out-of-scope notes — not new work you did.

## Communication expectations

- After each task, print a one-line status: `Task N done — <bug> — <test name added or "manual repro"> — committed <sha7>`.
- After all tasks: print a final summary table mirroring Task 13's resolution table, plus the `git log --oneline` of the commits you landed.
- If you skip a task, say which and why, with a pointer to the plan section that justifies it.
- Do not narrate inner reasoning. Brief status lines only. The plan is the design rationale; you don't need to re-derive it.

## Anti-patterns specific to this repo

- Do not regenerate or hand-edit `tests/golden_logs/*.json`. They are engine-truth snapshots and changing them requires a deliberate, signed-off engine change (which this is not).
- Do not add `try/except` blocks "for safety" around code that the existing tests already exercise. The codebase trusts its internals; only validate at system boundaries.
- Do not write multi-line docstrings or comment blocks. The codebase convention is one-line where the why is non-obvious, none otherwise.
- Do not "improve" CSS, refactor unrelated React components, or rename variables. The Plan C work will reshape the frontend; let it.
- Do not add backwards-compatibility shims. The clean break is intentional (see STATUS.md on Plan B v2 player attributes failing loudly on legacy saves).

Begin with Task 1 once you've read the five orientation docs. Confirm in one sentence that you've read them and what the current `git status` shows before you start changing files.

=====

## Notes for the human handing this off

- The plan file's task checkboxes (`- [ ]`) are the progress ledger. Tell Gemini to flip them to `- [x]` as it goes.
- If Gemini's environment can't run a browser, that's fine — Tasks 3, 4, 5, 6, 7, 8, 10 have build+lint as the floor and a manual-repro note in the commit body. You verify the browser behavior on your end before merging.
- If Gemini wants to deviate from the plan, the rule is: write it into the followups scratch file, do not act on it. Review that file after the run.
- After Gemini finishes, you should: (1) read the resolution table in the audit doc, (2) `git log --oneline -20` to spot-check the commit shape, (3) load a real save in the browser and walk Roster Lab + Dynasty Office + Standings to verify the visible fixes.
