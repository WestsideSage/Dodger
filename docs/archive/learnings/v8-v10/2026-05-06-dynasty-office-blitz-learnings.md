# V8-V10 Dynasty Office Blitz Learnings

Date: 2026-05-06
Milestones: V8, V9, V10

## Summary

The implementation blitz completed thin web-facing versions of the remaining long-range milestone loops in one unified Dynasty Office surface. That was the right shape for speed: it gave recruiting promises, league memory, and staff market decisions a playable home without pretending the deeper simulation consequences are already finished.

The main learning is that the project is now past milestone expansion and into polish/hardening. Future work should deepen the loops already visible in the game instead of opening new surfaces.

## What Worked

- A single Dynasty Office avoided three shallow new tabs while still making V8, V9, and V10 visible.
- The implementation reused existing truth where possible: command history, club prestige, rivalry records, awards, records, recent matches, current department heads, and seeded prospect generation.
- The UI explicitly labels thin or limited states instead of inventing fake historical depth.
- JSON-backed `dynasty_state` entries were enough for a blitz layer without forcing a schema migration before the loop shape was proven.
- Tests locked down the important honesty constraints: saved promises persist, promise count is limited, staff hires update real department heads, and hired departments leave the candidate market.

## Implementation Lessons

- A facade module can be useful for milestone aggregation. `src/dodgeball_sim/dynasty_office.py` connects existing domain and persistence data into one product-facing model while leaving core match and season logic untouched.
- Thin persistence is acceptable for early office actions, but it should not become the final home for deep mechanics. Promise fulfillment and staff history will eventually need stronger domain modeling if they affect season outcomes.
- Deterministic generation is the right default for office previews. Staff candidates and prospect interest can feel alive while still respecting the no-hidden-randomness rule.
- Browser smoke caught an important product flaw after tests passed: hired staff needed to disappear from the visible candidate market. The test suite now covers that behavior.
- The web app benefits from dense operational UI for manager workflows. This surface should stay focused on decisions, evidence, and consequences rather than becoming an explanatory landing page.

## Verification Lessons

- Test-first work was useful even in blitz mode. The missing module, missing endpoint, promise limit, and staff hire behavior all had tests before or alongside implementation.
- Full Python verification passed with:
  - `TMPDIR=/tmp .venv/bin/python -m pytest -q`
- Frontend verification passed with:
  - `npm run lint`
  - `npm run build`
- Browser smoke passed after launching backend/frontend and opening the Dynasty Office. The smoke confirmed the office renders, a recruiting promise can be saved, a staff candidate can be hired, and the visible state updates afterward.
- In this WSL/Windows setup, Playwright CLI needed `TMPDIR=/tmp` so the browser bridge could use a safe socket path.

## Honesty Boundaries

- V8 promises are persisted but not evaluated at season end yet.
- V8 prospect preview does not yet drive the existing Recruitment Day signing machinery.
- V9 league memory reports available saved data and limited-state copy; it is not a full archive system yet.
- V10 staff hires update department heads and visible recommendations, but they do not yet alter development math, scouting point generation, recovery, AI staff competition, or poaching.
- The event log remains canon for match outcomes. Dynasty Office surfaces should never decide or rewrite match results.

## Recommended Next Work

1. Add promise fulfillment checks at season or offseason transition, with explicit success/failure evidence.
2. Connect staff ratings to development, scouting, or recovery through tested and documented balance rules.
3. Expand league memory into deeper record, rivalry, title, and player history pages.
4. Run Gemini and Claude review against the V7-V10 branch before merging.
5. Do a dedicated browser QA pass after review-driven polish.

## For Gemini and Claude

Review these files first:

- `src/dodgeball_sim/dynasty_office.py`
- `src/dodgeball_sim/server.py`
- `frontend/src/components/DynastyOffice.tsx`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `tests/test_dynasty_office.py`
- `tests/test_server.py`
- `docs/retrospectives/v8-v10/2026-05-06-dynasty-office-blitz-handoff.md`
- `docs/specs/MILESTONES.md`

Suggested review stance:

- Verify that every displayed claim is backed by real saved data, deterministic generated data, or clear limited-state copy.
- Check that no staff, recruiting, or memory feature adds hidden buffs, rubber-banding, user aura, or unlogged outcome changes.
- Decide whether the first polish slice should be V8 promise fulfillment, V10 staff effects, or V9 history depth.

## Closeout Note

The roadmap now has a playable web surface for every remaining milestone. The next phase should be polish, QA, balance, and integration review.
