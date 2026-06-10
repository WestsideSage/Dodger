# V16 — Contested Offseason: Retrospective (2026-06-10)

Shipped in one implementation pass on 2026-06-10, directly after Task 0
landed the six 2026-06-09 audit passes. Plan:
`docs/specs/2026-06-09-v16-contested-offseason-sprint-plan.md`. All seven
plan tasks implemented; owner decision D1 (scouted band) honored, D2 snipe
model retuned against measurement, D3 (1 AI signing/club/offseason) as a
config constant.

## What shipped

1. **Signing Day payload truth (Task 1).** The offseason picker stopped
   emitting `true_overall()` for prospects — field, `fit_score`, and sort
   order all moved to the scouted public band (shared `narrow_band` math
   with the in-season board). Free agents keep verified OVR. The picker
   renders `KnownValue` band states with a rewritten fog-of-war disclosure.
2. **Off-center public bands (found during Task 1, not in the plan).** The
   generated band was symmetric around the hidden truth, so its midpoint WAS
   the true OVR and banding the picker would have been decorative fog. Band
   centers are now jittered (`ScoutingBalanceConfig.public_band_center_jitter
   = 8.0`), making the public read a genuine estimate. This was required for
   "scouting matters" to be true at all.
3. **Contested user pick (Task 3).** Prospect picks resolve through the
   formerly dormant `recruitment.conduct_recruitment_round`. The user offer
   was retuned from the dormant `100 + interest*0.2` (uncourted picks could
   never lose) to config `90.0 + interest*0.18` against measured rival
   offers (`tools/contested_offer_probe.py`, 60 seeds: rival max offers on
   the star run 84.9–111.7). Measured outcomes: uncourted star pick sniped
   54%, contact+visit 22%, full courtship 7%. Snipes are honest outcomes
   (no 409, no slot consumed, full explanation with offer numbers and
   interest evidence); wins reveal "Scouted L–H → verified OVR N".
4. **AI offseason signings (Task 2).** Eligible AI clubs bid on their own
   board targets in the user's rounds and a close-of-recruitment sweep
   (`ensure_ai_offseason_signings`, idempotent per season) lets every AI
   club sign up to the D3 cap. League churn measured at 5.0 AI prospect
   signings per offseason (was zero).
5. **Term registry truth flip (Task 4, one deviation).** `recruit.interest`,
   `recruit.pipeline`, `program.credibility` flipped to mechanical with copy
   naming the consumer. `recruit.fit` deliberately stays flavor: it is a
   display blend (band midpoint + credibility) with no consumer — flipping
   it would have been the same fiction the audit removed. All courtship copy
   (board evidence, next-step lines, credibility blurb) now claims exactly
   what the code does.
6. **History sort hygiene (Task 5).** `season_sort_key` applied across the
   my-program hero/first-win/timeline/banners/HoF/last-club queries, the
   league streak query, and seven persistence loaders (one-pass sweep per
   the owner decision log).
7. **Dynasty-health CI gate (Task 6).** `TestDynastyHealthGate` pins a
   4-seed × 6-season probe sweep: title share ≤ 0.35 (evidence-based: the
   pre-V16 solved config measured 41.7%, post-V16 12.5% — a contested-round
   revert fails the gate), AI roster floor ≥ 6, ≥ 2 distinct champions per
   run, ≥ 1 AI signing per offseason, and ≥ 1 user snipe across the sweep
   (the direct contested-ness tripwire). The probe itself now drives the
   shipping contested path.

## Measured before → after (dynasty probe, 4 seeds × 6 seasons, auto-pilot user)

| Metric | Pre-V16 | Post-V16 |
|---|---|---|
| User title share | 10/24 (41.7%) | 3/24 (12.5%) |
| Champion distribution | aurora=10, then 5/5/2/1/1 | 5/5/5/3/3/3 across six clubs |
| AI roster sizes (final) | all pinned at 6 | 10 |
| AI prospect signings | 0 ever | 5.0 per offseason |
| User picks sniped | impossible | 5 across 24 offseasons |
| User fielded-6 edge vs best AI | +8–9 compounding | −1.0 → −5.6 (passive play falls behind) |

The static league and solved recruiting are dead. Note the last row: a
zero-effort auto-pilot user now finishes below the AI curve — engaged play
(scouting, courtship, lineup care) is what buys the edge back. Owner may
want to tune `AI_OFFSEASON_SIGNINGS_PER_CLUB` / `AI_OFFSEASON_MAX_ROSTER`
if passive careers feel too punishing in real playtests.

## Plan deviations (source-wins honesty)

1. **Symmetric band fix** (above) — required, not planned.
2. **D2 formula retuned** — the plan said the dormant 100 + 0.2·interest
   "stands"; it could not satisfy acceptance criterion 3 (an uncourted pick
   was mathematically unsnipeable). Constants moved to the config layer and
   tuned against the probe.
3. **`recruit.fit` stays flavor** — the plan listed all four terms; fit has
   no consumer and ADR 0002 wins.
4. **No-leak pin is at the HTTP wire, not a pydantic response_model** — the
   offseason routes are raw-dict by design; adding a response model would
   re-create the WT-2/3 field-stripping hazard across ten beat payload
   shapes. The pin asserts the serialized JSON the SPA receives
   (`tests/test_signing_day_band.py`).
5. **Credibility source unified** — the dormant round used single-season
   command history while the board used career-wide; the round now uses
   career-wide (`load_command_history_all_seasons`), so the picker and board
   can never disagree about the same prospect's interest.

## Verification

- Full `python -m pytest -q` green (1,350 passed incl. 25 net-new); engine
  invariance pins, WT-7 frozen winners, and golden logs untouched and green.
- `npm run build` + `npm run lint` clean.
- Adversarial review: six-lens workflow (tests lens completed externally
  with measured findings — all three majors fixed: auto-pick behavioral
  leak pin, structurally-uncontested flow tests, gate teeth vs revert; five
  lenses re-run inline: drift clean, leak clean, determinism/flow/copy
  audited).
- Live two-offseason browser walk + targeted Playwright: see the fable
  handoff for the session evidence.

## Follow-ups (not blockers)

- Passive-career difficulty tuning knob review after real playtests (see
  table note above).
- Snipe outcomes are transient UI state (the class-report cards persist
  them permanently; the banner itself is response-local by design).
- Cross-process determinism of set-iteration order is documented as a test
  blind spot (live code uses `sorted()` everywhere).
