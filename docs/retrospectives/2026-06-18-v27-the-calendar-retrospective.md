# V27 — The Calendar: Retrospective

**Shipped:** 2026-06-18 on `feature/v24-the-board` (not yet on main — the Climb-Era arc V23–V27 merges as a unit).
**Spec:** `docs/specs/2026-06-17-v27-the-calendar-spec.md`
**Plan:** `docs/specs/2026-06-17-v27-the-calendar-sprint-plan.md` (7 phases)
**Scope:** give the season a calendar of real competitions — a revived cross-division Domestic Cup, cloth/no-sting Ruleset Invitationals (behind balance gates), the Midseason International, the fan-invited Founders' Exhibition, and an elevated Worlds crowning ceremony — each a deterministic auto-simmed real-engine knockout with a trophy, purse, fans, and journalism, behind `pyramid_world_active` so legacy saves stay byte-identical.

## What shipped

All 7 plan phases, each its own commit (`6c8b15f` → `f661453` + the Phase 7 close-out):
- **Phase 1** — `event_calendar.py` (`EventResult` / `EventBracketRow`, idempotent `apply_event_purse` with the per-event `v27_<event>_purse_for` guard mirroring `FINANCES_APPLIED_KEY`, the per-season `v27_events_json` store, `emit_event_news`), the widened news-wire filter (`event_news` now passes), and the conditional `events` offseason beat scaffold.
- **Phase 2** — `cup_service.py` revives the dormant `cup.py` (kept import-pure) in the web path: `ensure_domestic_cup` generates the cross-division bracket; `resolve_domestic_cup` auto-sims it to a champion through the real foam engine, awards the trophy + fans + an idempotent purse + a giant-killing news line.
- **Phase 3** — `tools/ruleset_balance_probe.py` + the permanent `tests/test_v27_ruleset_balance.py` gates for cloth + no-sting (the V17 precedent applied BEFORE the invitationals). **No imbalance found** — no retune; the gates pin the current good behavior.
- **Phase 4** — `invitationals.py`: `run_invitational` auto-sims a cloth/no-sting knockout via `OfficialEngineAdapter`; the Cloth Classic / No-Sting Open invite by fame (prestige) + standing, the champion gets an idempotent purse + a small prospect-showcase warmth (`warmth_credibility`, the V26 credibility channel).
- **Phase 5** — MSI (`msi_invitees` returns the Premier leader + the Circuit leader keyed on `division_id` not tier; foam knockout + prestige + purse + a Worlds-seeding note in `meta`) + Founders' Exhibition (`founders_invitees` top-N by `fan_ledger.club_fans`, no-seeding, money-only).
- **Phase 6** — the `worlds_champion` crowning ceremony beat: `worlds_crowning_for_user` reads the postseason ledger + `worlds_history_json` (first-ever crown ⇒ `is_first`; later ⇒ defending-champion); no post-summit ratchet (the vision law).
- **Phase 7** — frontend (`EventsBeat.tsx` + `EventBracket.tsx` + `WorldsCrowning.tsx` + `types.ts` union + `Offseason.tsx` dispatch) + `tests/test_v27_phase7_frontend_payloads.py` (the strip-trap regression) + `tools/event_finance_probe.py` + `tools/v27_api_walk.py` + docs (this retro, STATUS, MILESTONES).

## Verification

- `python -m pytest -q` green, **real exit code 0** (NOT piped), **1792 tests**.
- `npm run build` + `npm run lint` clean (no FE test runner — build/lint + the Python payload guards, per repo convention).
- Probes: `tools/cup_probe.py` (valid champion 20/20 seeds, giant-killing 45%, determinism), `tools/ruleset_balance_probe.py` (cloth + no-sting parity/health/stability — see the recorded numbers below), `tools/event_finance_probe.py` (every event purse 5–21% of a league champion's payout — a declared margin, never its rival).
- API-level walk (`tools/v27_api_walk.py`, port 8010, isolated temp save dir so the owner's 8000 game was never touched): the events payload (domestic_cup + MSI + Founders) came through `/api/offseason/beat` un-stripped across 5 seeds; the Worlds crowning is conditional on a real Worlds win and did not land on auto-pilot in 5 seeds (honest — its strip-trap is pinned end-to-end by the TestClient guard; the live crowning is the owner's browser acceptance walk). Walk save purged; port confirmed free.

## Hard-won lessons

### 1. The `events.py` → `event_calendar.py` rename
The plan named the new event-result module `src/dodgeball_sim/events.py`. That name was already taken — `events.py` is the engine's `MatchEvent` module (the canonical event-log types). Importing a new event-result model into `events.py` would have collided with the engine layer and confused every reader. The V27 event model lives in **`event_calendar.py`** instead. The lesson repeats the repo's "name the thing for what it is, not the generic word" — when a plan's filename collides with an existing module, rename the new file, not the old one.

### 2. The clamp lockstep — bit three times now
`OFFSEASON_CEREMONY_BEATS` gained two new beats (`worlds_champion` at index 1 after `recap`; `events` at index 4 after `awards`). `persistence._MAX_OFFSEASON_BEAT_INDEX` moved **11 → 13** and the pinned beat-tuple witness in `test_dispersed_helpers` / `test_v27_events` / `test_v27_worlds_crowning` moved with it. This is the V25/V26 clamp bug (a new beat pushed the final beat past the clamp, making it unreachable) — now bit three times. The standing rule is in the plan: `OFFSEASON_CEREMONY_BEATS` + `compute_active_beats` + `_MAX_OFFSEASON_BEAT_INDEX` + the pinned beat-tuple witness change **together** in one commit. The witness tuple is the cheap guard that catches a forgotten clamp bump.

### 3. Cloth / no-sting recorded balance numbers + caps (the V17 precedent, no retune)
Step 1 of the balance gate ran the full nightly config (`tools/ruleset_balance_probe.py --seeds 16 --seasons 2 --clubs 6 --health-trials 150 --attr-trials 150 --stability-matches 500`) and found **no imbalance** — so no ruleset constant was retuned. The gates pin the recorded good behavior:
- **official_cloth:** 3 distinct champions; distribution {Power Throwers 53.1%, Balanced Rebuild 40.6%, Defensive Specialist 6.2%}; max_share 0.531, Wilson-95 upper 0.691 → **cap 0.72** (~3pp headroom). Health: OVR slope **+55.3pp** (top floor 99.3%); even baseline 45.3%; +12 accuracy 69.3% / power 80.0% / dodge 62.7% / catch 86.7%; **no liabilities**. Stability: 500/500, 0 crashes.
- **official_no_sting:** 3 distinct champions; distribution {Balanced Rebuild 46.9%, Power Throwers 40.6%, Defensive Specialist 12.5%}; max_share 0.469, Wilson-95 upper 0.636 → **cap 0.68** (~21pp headroom). Health: OVR slope **+56.7pp** (top floor 99.3%); even baseline 44.7%; +12 accuracy 72.0% / power 80.0% / dodge 70.7% / catch 85.3%; **no liabilities**. Stability: 500/500, 0 crashes.

The caps are pinned from the recorded Wilson-95 upper (rounded up), NOT the gate's reduced trial count — the gate runs a faster subset but its caps come from the full nightly run, so benign drift stays green and a balance regression big enough to matter trips at the reduced N too.

### 4. V26 warmth coexistence
The invitationals' prospect-showcase `warmth_credibility` rides the **V26** recruiting-credibility channel (a one-season bump); MSI awards prestige (the V24/V26 credibility source); Founders' is money-only (no prestige, no warmth, no Worlds seeding — being beloved is the ticket). The three events touch three different V26-era economies without overlapping, so the V27 layer composes with V26 rather than re-inventing it. The lesson: a new milestone's small bumps should flow through the existing channels (credibility / prestige / fans / treasury), not spin up parallel ones.

### 5. Round-clock match-id encoding
`invitationals._invitational_match_id` encodes the round slug (`inv_{event_key}_{season_id}_{slug}_m{slot}_{home}_vs_{away}`) so `run_autonomous_match`'s clock resolution picks the right per-round clock. This is the V17 round-clock trap again: a knockout match-id that doesn't encode its round makes the engine's clock resolution pick a wrong/none clock and the match mis-runs. The cup uses the same encoding via `cup_service`. Match-ids in a knockout are not just identifiers — they carry the round the engine clock needs.

### 6. The strip-trap structural absence (and the guard that pins it)
The offseason beat endpoints (`/api/offseason/beat` etc.) declare **NO `response_model=`** — they return raw dicts, so FastAPI does not strip undeclared keys and the new `events` / `worlds_champion` payloads pass through verbatim (the V26 `media_event` beat already ships this way). The historical WT-12 `MatchReplayResponse` bug was a `response_model=` stripping fields; the beat layer never made that mistake. But "works today" is not "guaranteed tomorrow" — a future developer adding a `response_model=` would silently strip the new payload keys and the frontend would render empty beats. `tests/test_v27_phase7_frontend_payloads.py` is the regression: it drives the **real FastAPI `TestClient`** against a pyramid career with both beats active and asserts the `/api/offseason/beat` JSON carries every payload field end-to-end — the test that fires if the strip trap ever closes. The lesson: when a payload's survival depends on a *structural absence* (no response model), pin that absence with a positive end-to-end assertion, not a comment.

## Disclosed deferrals / honest residuals

- **Invitationals did not fire in season 1 of the API walk** — no club met the fame threshold (`invitational_fame_min = 20`) that early. Honest; their payload shape is the same `EventResult` row the Domestic Cup verifies end-to-end, so the strip-trap is covered. They fire once clubs accrue prestige (the V26 growth path).
- **The live Worlds crowning did not fire on the API walk** (5 seeds, aurora takeover, auto-pilot) — the crowning is a conditional beat requiring the user to actually WIN Worlds, which is non-deterministic on auto-pilot. Its strip-trap is pinned end-to-end by the TestClient guard (real FastAPI serialization + a written Worlds ledger). The live crowning is the owner's browser acceptance walk.
- **The API walk's giant-killing display** — the cup fired every seed (giant-killing rate 45% per `cup_probe`); the walk logged the events that fired but did not pretty-print the giant-killing receipts (they ride in `meta['giant_killings']`, which the FE renders and the guard test asserts survives).
- **Bench-role visual assignment control, in-season media, the V26 deferred items** — unchanged; V27 added no new deferrals in those lanes.

## What I'd do differently

- **Name-collision check before the plan's file list.** The `events.py` rename was caught at implementation time; a 30-second `glob` for each planned new file at spec-writing time would have caught it at plan time and kept the plan's file list honest.
- **The clamp witness as a single shared fixture.** Three test modules (`test_dispersed_helpers`, `test_v27_events`, `test_v27_worlds_crowning`) each re-pin the beat tuple. A single `conftest`-level witness would make the lockstep one place to update, not three. Small refactor for a future cleanup pass.
- **The API walk's Worlds crowning.** A deterministic crowning on a pure API drive is genuinely hard (the user must win Worlds interactively). The honest answer is the TestClient guard + the owner's browser walk; I spent a 5-seed sweep confirming the crowning is non-deterministic on auto-pilot, which is the right disclosure but not a live crowning. A future walk could take over a club, manually play the Worlds matches via the week-sim endpoint, and force a win — but that's a scripted postseason, not an auto-pilot, and the strip-trap is already covered.
