# V8-V10 Dynasty Office Blitz Handoff

Date: 2026-05-06
Milestones: V8, V9, V10
Status: Shipped thin in `feature/codex-next-task`; ready for Gemini/Claude review and polish planning.

## Summary

Maurice authorized an implementation blitz for the remaining long-range milestones so future work can focus on polishing a complete game surface rather than continuing milestone sequencing. The result is a single new web surface, the Dynasty Office, that exposes thin but honest versions of:

- V8: Recruiting, Promises, and Program Credibility.
- V9: Living League Memory.
- V10: Staff Market and Program Arms Race.

This was intentionally not a deep simulation rewrite. The implementation reuses existing persisted truth where possible and labels thin/future boundaries explicitly instead of pretending the game now has full recruiting, alumni, or staff-economy depth.

## Shipped Surface

New tab:

- `Dynasty Office` in the main web navigation.

New backend module:

- `src/dodgeball_sim/dynasty_office.py`

New API endpoints:

- `GET /api/dynasty-office`
- `POST /api/dynasty-office/promises`
- `POST /api/dynasty-office/staff/hire`

New frontend component:

- `frontend/src/components/DynastyOffice.tsx`

New tests:

- `tests/test_dynasty_office.py`
- Server API coverage added in `tests/test_server.py`

## V8: Recruiting, Promises, and Credibility

Implemented:

- Program credibility score and grade derived from command-history wins/losses, youth-development command weeks, and persisted club prestige.
- Deterministic prospect preview using the existing prospect generator and scouting balance config.
- Public prospect info: archetype guess, OVR band, hometown, fit score, and evidence lines.
- Limited saved promises:
  - `early_playing_time`
  - `development_priority`
  - `contender_path`
- Promise persistence through `dynasty_state` JSON under `program_promises_json`.
- Promise limit of three active open promises.

Integrity boundary:

- Promises do not yet alter recruiting outcomes.
- Promise cards say they will be checked against future command history and match stats.
- Interest evidence says there is no hidden promise effect until a promise is saved.

## V9: Living League Memory

Implemented:

- League memory panel with records, awards, rivalries, and recent matches.
- Existing persisted records, awards, and rivalry loaders are reused.
- Recent match memory comes from saved `match_records`.
- Empty states are explicit:
  - No records have been ratified yet.
  - Awards appear after season closeout.
  - Rivalries build from repeated saved match results.

Integrity boundary:

- No scripted news/drama director was added.
- No fake alumni or former-player return events were added.
- The panel reports real saved data or says the evidence is not there yet.

## V10: Staff Market and Arms Race

Implemented:

- Staff market candidates are deterministically generated from current department heads, season id, department, and root seed.
- Hiring a candidate replaces the department head row.
- Recent staff actions are persisted through `dynasty_state` JSON under `staff_market_actions_json`.
- Hired departments are removed from the current market.
- Candidate effect lanes explain current visible impact:
  - recommendations
  - recruiting fit explanations
  - fatigue-risk framing
  - promise-risk framing

Integrity boundary:

- Staff changes affect visible staff state and recommendations now.
- Deeper development, scouting, recovery, and AI-program effects remain explicit future hooks.
- No hidden staff buffs were added to match outcomes.

## Verification

Backend:

- `TMPDIR=/tmp .venv/bin/python -m pytest tests/test_dynasty_office.py tests/test_server.py::test_dynasty_office_endpoint_exposes_remaining_milestone_loops_and_actions -q`
  - Result: pass.
- `TMPDIR=/tmp .venv/bin/python -m pytest -q`
  - Result: pass, full suite.

Frontend:

- `npm run lint`
  - Result: pass.
- `npm run build`
  - Result: pass.

Browser smoke:

- Loaded `http://127.0.0.1:5173/?tab=dynasty`.
- Loaded existing `V7 QA` save.
- Opened Dynasty Office.
- Saved an `early playing time` promise.
- Hired a staff candidate.
- Confirmed:
  - Promise appears in Program Credibility.
  - Staff move appears under Recent staff moves.
  - Hired department is removed from the current candidate market.

## Known Thin Spots

- V8 promise evaluation is not resolved at season end yet. The data is persisted, but fulfillment checks need a future polish task.
- V8 prospect preview is generated for the office surface and does not yet drive the existing Recruitment Day signing machinery.
- V9 living memory is mostly a browser surface over existing backend data. The historical model needs deeper player pages, title history pages, and season archives.
- V10 staff hires do not yet feed into development math, scouting point generation, recovery math, AI hiring, or poaching events.
- There is no dedicated V8/V9/V10 browser QA report beyond the smoke pass captured here.

## Recommended Review Focus

Gemini and Claude should review in this order:

1. `src/dodgeball_sim/dynasty_office.py`
2. `src/dodgeball_sim/server.py` Dynasty Office endpoints.
3. `frontend/src/components/DynastyOffice.tsx`
4. `tests/test_dynasty_office.py`
5. `tests/test_server.py` Dynasty Office API test.
6. `docs/specs/MILESTONES.md` updated V8-V10 status.

Primary review questions:

- Are the honesty boundaries clear enough in the UI copy?
- Should V8 promise fulfillment become the first polish task?
- Should V10 staff effects remain recommendation-only until a balance pass approves mechanical impact?
- Should the Dynasty Office be split later into Recruiting, League Memory, and Staff tabs, or stay unified until the loops deepen?

## Closeout Verdict

V8-V10 are shipped-thin, not finished-deep. The long-range roadmap now has playable web surfaces for every remaining milestone, and the next phase should be polish, balance, QA, and integration cleanup rather than another major feature expansion.
