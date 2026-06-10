# V18 — Development & Mortality (sprint plan)

Date: 2026-06-10. Sequenced by
`docs/specs/2026-06-10-post-v16-greenlit-backlog-sequencing-plan.md` (§2 row
V18, §3 item 2). Owner dispositions in
`docs/fable/2026-06-10-owner-decision-log.md`: Dynasty §3 (dev-ceiling
overhaul GREENLIT — "pivotal"), Dynasty §4 (31–33yo vet seeding APPROVED,
Teamfight Manager 2 vet/rising-star/prodigy mix), Onboarding §1
(AI-symmetric development Monte Carlo re-run — "RUN IT").

## Relation to Prior Specs

- Follows V17 Official Engine Truth (shipped 2026-06-10; retro
  `docs/retrospectives/2026-06-10-v17-official-engine-truth-retrospective.md`).
  V17 settled the official-engine economy, so development is now measured
  against final win-rate context. The V17 retro explicitly flags that +24 net
  OVR → 82.5% match win, so **season-level snowball must be watched in this
  milestone's probes** — every dev buff is also a snowball risk.
- The development *reps unit bug* (minutes/1000 gate) was already fixed in the
  2026-06-09 dynasty retention pass; the remaining shortfall is the dev *math*
  itself. The 2026-06-09 dynasty-report numbers ("~half of headroom closed by
  peak-end") are **pre-V17 context** — all baselines are re-captured on
  current main (Task 1), not reused.
- Instrument: `tools/dynasty_health_probe.py` (V16/dynasty-pass probe), which
  Task 1 extends with a dev-arc trace.

## Goal

Players actually reach the ceilings the game displays, rosters age and retire
on a human timescale, and AI clubs develop on equal mechanical footing —
verified by a before/after Monte Carlo sweep of the shipping career loop.

## Non-goals

- No match-engine changes (official or rec). Development is offseason math.
- No new decision consumers (staff/roles/stamina/tactical_iq are V19).
- No recruiting changes beyond what vet seeding requires at career creation.
- No UI redesign; only display copy that the math changes make true/false.

## At-risk temptations (deferred)

- Per-stat dev sliders / training minigames — not this milestone.
- In-season development ticks — the offseason cadence stays.
- Champion-shape rebalance (Power Throwers 63.8% matched-OVR skew) — V19
  reshapes that economy anyway; only the dynasty-health gates bind here.

## Verified current-state facts (2026-06-10, main @ 93e3f70)

- `development.py:16` — `_HEADROOM_CLOSE_RATE = 0.9`;
  `gap_close_rate = 0.9 × potential/100 × reps_factor`, so even a full-time
  starter at potential 80 closes only ~72% of headroom *into the 9-stat pool*
  per season, before rounding losses.
- The growth pool spreads 40% across all **9** rated stats while OVR is the
  mean of **5** (accuracy/power/dodge/catch/stamina — `models.py:100`); 4 of
  the 9 pool targets (tactical_iq, catch_courage, throw_selection_iq,
  conditioning_curve) never move OVR. Per-stat deltas round to int
  (`int(round(...))`), so small slices floor to 0 — a second silent shortfall.
- Displayed ceiling (`web_status_service.build_roster_payload`) =
  `max(stored potential, trajectory floor, current OVR)`; the engine growth
  cap (`development._apply_delta`) is `max(current_value, potential)` with
  potential = trajectory-floored stored potential. "Ceiling delivery" is
  therefore measured against **effective potential**
  (`max(stored, trajectory floor)`), not the OVR-maxed display value.
- `development.py:252` `should_retire`: age ≥ 40 always retires; age 38–39
  needs OVR < 58; age 36–37 needs `seasons_played ≥ 8`; age 34–35 needs
  `seasons_played ≥ 10` AND OVR < 52. **Seeded vets start with
  `seasons_played = 0`, so a seeded 33-year-old cannot retire before age 40**
  — naive vet seeding does NOT deliver season-2–4 mortality. Task 3 must
  backfill synthetic career history or retune the gates, with measurement.
- Curated roster ages are `18 + int(rng.unit() * 12)` → 18–29
  (`career_setup.py:214`, `:383`); build-a-club is 18–27 (`:451`). No vets
  exist at creation, so league mortality texture starts near-zero (the
  dynasty pass measured first league retirement waiting until ~season 8).

## Task 0 — Land the planning pass

Commit this plan. Fix the `docs/specs/MILESTONES.md` doc-lag: the table has
no V17 row (STATUS has the milestone; the index does not). Add it as Shipped
(2026-06-10) pointing at the sequencing plan (§4 is the V17 sprint plan) and
the V17 retro.

## Task 1 — BEFORE baseline (post-V17 development truth)

Extend `tools/dynasty_health_probe.py` with a **dev-arc trace**: per
post-offseason season snapshot, record every rostered player's id, club, age,
OVR, effective potential, displayed ceiling, and whether they sit in the
club's resolved fielded six. Additive only — the pinned probe API
(`run_dynasty_career` / `run_dynasty_sweep` signatures, existing
`SeasonSnapshot` fields, `TestDynastyLoopDeterminism`,
`TestDynastyHealthGate`) must not change. **No changes to `development.py`
or `career_setup.py` in this task.**

Sweep config (both runs ≥ 8 seeds × 10 seasons, `official_foam`, default
seed base 20260600):

- **Engaged**: `--seeds 8 --seasons 10 --signings 3 --optimize-lineup`
  (player re-optimizes the fielded six each offseason).
- **Passive**: `--seeds 8 --seasons 10 --signings 3` (shipping auto-pilot
  default: creation lineup order, signings seated at slot 6).

Record into this doc (§ BEFORE table):

1. **Ceiling delivery for full-time starters** — full-time starter = player
   appearing in the user club's fielded six in ≥ 3 season snapshots of a run.
   Mean first OVR, mean peak OVR, mean effective potential, mean shortfall
   (potential − peak), % of initial headroom closed at peak, share of
   starters whose peak comes within 2 OVR of effective potential.
2. **Mortality** — first season with ≥ 1 league retirement (per seed),
   mean retirements/season.
3. **Title-share curve** — user titles per season across seeds, total share.
4. **OVR-edge curve** — user fielded-6 OVR minus best-AI fielded-6 OVR per
   season (the snowball curve), plus vs league mean.

Known capture trap: PowerShell `*>` redirection writes UTF-16; read such
files with `-Encoding Unicode` or redirect through a UTF-8-safe path.

## Task 2 — Dev-ceiling overhaul (outcome-affecting, measured)

Redo the development math so the displayed ceiling is an honest promise:

- Levers, in order: make the OVR-relevant share of the pool track headroom
  honestly (the 9-stat dilution vs 5-skill OVR is the structural leak);
  retune `_HEADROOM_CLOSE_RATE` only after the dilution is fixed; address
  int-rounding starvation of small slices (accumulate or randomize remainder
  through the seeded RNG).
- Acceptance gates (AFTER, same probe config as Task 1):
  - Full-time starters' mean peak OVR comes within **2 OVR** of effective
    potential; ≥ 70% of full-time starters peak within 2 OVR of it.
  - Headroom closure for full-time starters ≥ 85% at peak (BEFORE: see
    table; pre-V17 report language was "~half").
  - No snowball regression: `TestDynastyHealthGate` stays green (title share
    ≤ 0.35, AI roster floor, distinct champions, churn, snipe tripwire), and
    the engaged OVR-edge curve does not grow materially vs BEFORE (the AI
    develops on the same math — symmetry is the control).
  - Determinism pins hold (`TestDynastyLoopDeterminism`).
- Update displayed-growth copy only if the math makes existing copy false.

## Task 3 — Vet seeding + mortality (career_setup + retirement gates)

- Seed curated rosters with a vet/rising-star/prodigy age mix (owner-cited
  Teamfight Manager 2 shape), including 31–33-year-olds, instead of uniform
  18–29. Build-a-club keeps its younger profile unless measurement says
  otherwise.
- Handle the `should_retire` trap: seeded vets need synthetic
  `seasons_played` history consistent with their age (or the age gates need
  a measured retune) so mortality starts in seasons 2–4, not at age 40.
- Acceptance gates: first league retirement by season ≤ 3 (mean across
  seeds; BEFORE ~8), retirements/season produces visible offseason texture
  without cratering league OVR or roster floors (AI roster floor gate stays
  green); HoF/records cadence keeps producing texture (probe already
  records it).
- Curated-roster RNG stream changes are expected here — re-pin any
  frozen-seed curated fixtures in the same change and document the
  intentional change per `AGENTS.md`.

## Task 4 — AI-symmetric development Monte Carlo re-run

Owner: "RUN IT." Re-run the Task 1 sweep config (engaged + passive) on the
post-Task-2/3 build as the AFTER table; verify user and AI clubs develop
symmetrically (the probe's AI clubs run BALANCED focus, no staff modifier —
the user auto-pilot does too, so any persistent engaged-mode edge is
structural recruiting/lineup, not dev asymmetry). Record AFTER vs BEFORE in
this doc and flag any snowball drift for the V19 planning pass.

## Task 5 — Verification sweep + retro

Full `python -m pytest -q`; `npm run build` + `npm run lint` if any frontend
copy changed; focused Playwright only if player-facing surfaces changed;
retro in `docs/retrospectives/`; STATUS + MILESTONES updates; push.

---

## BEFORE table (Task 1 capture — post-V17 main, pre-V18 dev changes)

*To be filled by the Task 1 baseline capture in this milestone. Numbers below
this line are the binding baseline for Task 2/3/4 gates.*

(pending)
