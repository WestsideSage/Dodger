# V25 — The Market: Retrospective

Date: 2026-06-17
Spec: `docs/specs/2026-06-17-v25-the-market-spec.md`
Plan: `docs/specs/2026-06-17-v25-the-market-sprint-plan.md`
Branch: `feature/v24-the-board` (the Climb-Era arc; merges to main as a unit).

## What shipped (7 phases)

Money finally enters a *player's* story. Every player carries a salary + contract
term; the offseason resolves contracts before the new class is signed; higher-tier
money flows uphill to hunt the user's expiring stars; the AI plays the same game.
The entire layer is behind `world.pyramid_world_active()` — legacy / non-pyramid
saves are byte-identical.

1. **Contracts foundation.** `Player.salary_k` / `contract_term` ride the JSON
   blob via `.get()` defaults (no player-field migration). `contracts.py` is the
   single formula home (entry / second / wage-budget / buyout / dev-comp). STANDARD
   ability-blind entry deals at signing; a self-healing pricing pass
   (`_seed_v25_contracts`) prices any unpriced rostered player every offseason.
   A player wage bill joins `apply_season_finances` as an outflow (the Recap
   Finances block names it).
2. **Aging + retention.** `_decrement_contract_terms` ticks every contract down
   each offseason (term 0 = expiring). Retention is recruiting's mirror —
   `evaluate_retention` grades a rostered player against his OWN club via the V24
   `club_fit` (his motivation profile is identical to his prospect days, keyed on
   the preserved id) and a fit-bent salary ask; the dealbreaker veto walks him at
   any price.
3. **Uphill poaching.** Higher-tier AI clubs with wage headroom court the user's
   expiring stars (`poach_suitors`, reusing `derive_club_pursuit`); `resolve_poaching`
   makes money the dominant pull with motivations as the tiebreak (a loyal player
   stays even when outbid, up to a fit-scaled buffer). Departures carry data-derived
   receipts and a modest dev-compensation credit.
4. **Buyouts.** Refusable incoming buyout offers (accept = treasury income) and
   outgoing bids against AI asking prices — rich-club privilege, floor-protected.
5. **AI symmetry.** `run_ai_transfer_period` resolves every AI club's expiring
   squad on the same grades; the tier wage cap genuinely bites (real churn). A
   transfer ledger (`v25_transfers_json`) feeds a roster-fortress invariant and a
   news line on notable departures.
6. **Transfer Period beat.** A new ceremony beat (between retirements and the
   rookie preview), commit-on-advance: cached default decisions (re-sign at ask,
   refuse buyouts) the user adjusts, committed through the same contested logic
   the AI faces. Frontend `TransferPeriod.tsx` + the Recap wages line.
7. **Balance + verification.** Constants tuned with probe evidence; full suite
   green; build + lint clean.

## Measured evidence (probes)

- `tools/poach_retention_probe.py` — **grades flip outcomes 6/6**: a Contender-
  dealbreaker star re-signs at a proud club and walks at a broke one on the same
  offer; at equal money a loyal player stays while a mercenary is poached.
- `tools/roster_fortress_probe.py` — league veteran movement > 0 every offseason
  (~108 moves/offseason on a developed league; the wage cap drives real releases).
- `tools/squeeze_probe.py` — tier-solvency: a competitive 9-player squad's wages
  are **18% / 24% / 28%** of a competitive finish's prize money at District /
  Challenger / Premier. Climbing raises wages AND income together — squeeze, never
  tyranny, never a spiral.

## Findings fixed mid-build (the honest list)

- **Self-healing pricing (Phase 1 adversarial review).** Salary was first assigned
  only at the prospect-signing path, so user free-agent signings and AI depth fills
  sat at a permanent $0 wage — a squeeze-dodge and a biased AI wage bill. Fix: the
  pricing pass now prices any unpriced rostered player every offseason.
- **Offseason clamp bug.** `_MAX_OFFSEASON_BEAT_INDEX` was a hardcoded `9`; the new
  beat made the final `schedule_reveal` beat unreachable (the offseason could never
  roll into the next season). Raised to `10` with a guard test pinning it to
  `len(OFFSEASON_CEREMONY_BEATS) - 1`.
- **Roster-floor guard.** The transfer commit could let a star be poached off a
  thin 6-player squad, dropping it below the legal six and stalling auto-pilot at
  the recruitment-skip guard. The commit now protects the floor (you cannot
  release/lose your way below a fielded six — mirrors the AI `must_keep`).
- **Wage scale recalibration (Phase 7).** The first constants priced a Premier
  player at ~43k (~77% of Premier income) — wage tyranny, not the owner's MODERATE
  squeeze. Recalibrated (entry {1:14,2:9,3:5}; second base 6 / per-OVR 0.35 / tier
  mult {1:1.4,2:1.2,3:1.0}); a full squad now lands at 18–28% of tier income.
- **`pytest | tail` masked failures.** A background full-suite run piped to `tail`
  reported tail's exit 0 while pytest had failed; the beat insertion's witness
  shifts were caught only on a no-pipe re-run. Lesson (already a documented trap):
  never pipe pytest to tail for a pass/fail signal.

## Core decisions (owner-confirmed in the spec)

- **AI finance = wage-budget cap, not full treasuries** — symmetric pressure,
  AI finances stay abstracted, deterministic, far cheaper than per-club accounting.
- **Commit-on-advance beat, not a new `CareerState`** — same UX as the spec's
  gating intent, far less state-machine risk.
- **STANDARD ability-blind entry deals** — recruiting stays a courtship game; money
  enters at the second contract.

## Disclosed deferrals

- **Player hometown for the retention Hometown grade.** Players don't carry a home
  district (a prospect-only field), so the Hometown motivation grades neutral (0.55-
  equivalent / no veto) in retention — like the Development limited-state. A
  player-district field would make it real.
- **AI-vs-AI poaching** is modeled as re-sign/release churn under the wage cap, not
  full higher-tier-buys-lower-tier transfers. The user-facing poaching (the drama)
  is full-fidelity.
- **Circuit/Premier-ceiling poaching.** Poaching is by domestic tier; a Premier
  user's stars aren't domestically poachable (no higher rung). A Circuit/Worlds-tier
  poacher is a future refinement.
- **Founders priced as second contracts.** A founding squad is backfilled on the
  second-contract formula, which for low-OVR founders floors at the same value as
  the entry deal, so there is no real front-loading.

## Verification

- `python -m pytest -q` green (real exit code, no pipe), incl. 6 new V25 test files
  + a 2-season offseason-service integration test.
- `npm run build` + `npm run lint` clean.
- The three probes pass with the measured evidence above.
- A live prod-server browser walk across the Transfer Period beat is recommended as
  the owner's first-playthrough validation (the engine, the live service flow, and
  the FE build are all verified in-process).
