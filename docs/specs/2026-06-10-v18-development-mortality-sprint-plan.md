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

### Task 2 measurements (2026-06-10 — SHIPPED)

**Implementation** (`development.py`, offseason math only — no engine, no
career_setup): growth is budgeted directly in OVR points (1 OVR = 5 stat
points) as a fraction of remaining OVR headroom per fully-repped season
(`_HEADROOM_CLOSE_RATE = 0.40`), with an arrival floor
(`_FINISH_FLOOR_OVR = 3.0`) that terminates the old geometric asymptote. The
budget is spent on the five OVR skills gap-proportionally (the only
allocation that can deliver, since every stat caps at potential and OVR is
their mean), biased toward archetype primaries while they have room
(`_PRIMARY_BIAS = 0.5`). Identity stats close their own gap at half pace on
a parallel track (`_IDENTITY_CLOSE_SHARE = 0.5`). Focus multipliers keep
their old semantics (uniform part scales pace, relative part shifts
distribution); trajectory/staff scale the close rate, capped at
`_MAX_CLOSE_RATE = 0.85`. Decline path unchanged. RNG stream feeding the
dev-trait upgrade branch unchanged (same 9 noise rolls, same order).

**Gate results** (same probe config as the BEFORE table):

| Gate | Result |
|---|---|
| Mean peak within 2 OVR of eff. ceiling | ✅ engaged user shortfall **0.0** (was 9.6); AI 0.2–0.3 (was 10.3); passive user 0.5 (was 6.3) |
| ≥ 70% of starters peak within 2 | ✅ engaged **100%**, AI 95–97%, passive 90% (was 6% / 9–10% / 21%) |
| Headroom closure ≥ 85% | ✅ engaged **100%**, AI 96–98% (was 34% / 20%); passive user 81% is bench-composition (its actual starters: 90% within-2), not math |
| AI symmetry control | ✅ AI clubs deliver 96–98% on the same math — no asymmetry |
| `TestDynastyHealthGate` (CI config) | ✅ green (title share, AI floor, distinct champions, churn, snipes) |
| Determinism pins | ✅ green; full `python -m pytest -q` green at the final constants |
| New permanent gates | `tests/test_v18_ceiling_delivery.py`: delivery by peak-end at ages 18/21/24 × 3 archetypes, archetype-independence ≤ 2 OVR band, zero-headroom stasis, bench gating with the floor |
| Engaged OVR-edge "does not grow materially" | ❌ **NOT MET by dev math — structural, escalated** (below) |

**The engaged snowball is recruiting-structural, not a dev defect.** With
ceilings delivering, the engaged sweep (8×10, `--signings 3
--optimize-lineup`) goes from 17.5% → **41.2%** user title share, OVR-edge
peaking **+4.5** at S5–S6 and self-correcting to ~+1 by S10 as AI ceilings
deliver and the roster cap saturates. A pace experiment
(`_HEADROOM_CLOSE_RATE` 0.40 vs 0.35, both sweeps re-run) produced the SAME
edge curve (+4.5 peak) and statistically indistinguishable title share
(41.2% vs 48.8% on 80 binomial trials) — **global dev pace does not couple
to the snowball.** The hump is the V16 structural asymmetry (user signs up
to 3 prospects/offseason and keeps 12; AI clubs sign 1 and are trimmed to 9)
that broken development used to mask. Dev math must stay club-symmetric (no
hidden boosts), so the fix lives in recruiting volume/roster parity — V16
plan D3 ("AI volume = 1/club/offseason") was an unconfirmed
recommended-default and is now the binding lever. **OPEN owner item:**
raise AI offseason signing volume / revisit trim-to-9 vs user-12, or accept
the engaged hump as the reward for maximal engagement. Passive title share
is 5.0% (auto-pilot never rotates its aging lineup — the known lineup trap,
worth a separate auto-pilot fix note for V19).

Mortality is unchanged (first retirement S9 on all seeds) — that is Task 3's
job, as planned.

## Task 3 — Vet seeding + mortality (career_setup + retirement gates)

- Seed curated rosters with a vet/rising-star/prodigy age mix (owner-cited
  Teamfight Manager 2 shape), including 31–33-year-olds, instead of uniform
  18–29. Build-a-club keeps its younger profile unless measurement says
  otherwise.
- Handle the `should_retire` trap: seeded vets need synthetic
  `seasons_played` history consistent with their age (or the age gates need
  a measured retune) so mortality starts in seasons 2–4, not at age 40.
- Acceptance gates: first league retirement by season ≤ 3 (mean across
  seeds; BEFORE = 9 on all 8 seeds), retirements/season produces visible
  offseason texture
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

### Task 3 + owner D3 measurements (2026-06-10 — SHIPPED)

**Owner decision (2026-06-10), resolving Task 2's escalated item:** AI clubs
get the SAME Signing Day plays as the player — "the AI should be able to
make the same plays as the player… you are competing against them."
Implemented as `AI_OFFSEASON_SIGNINGS_PER_CLUB` 1 → 3 (= the user picker's
cap) and `AI_OFFSEASON_MAX_ROSTER` 10 → 12 (= `MAX_USER_ROSTER`, so the
volume is actually reachable). League churn: 5.0 → **15.0 AI prospect
signings per offseason**.

**Task 3 implementation:**

- `career_setup.build_curated_roster`: role-banded ages — Captain 31–33
  (vet), Anchor 28–31, Striker 26–29, Runner 22–25, Utility 19–23, Rookie
  18–20 — replacing the uniform 18–29 draw. One `rng.unit()` per player, so
  every other rolled value (names, ratings, traits) is stream-identical.
- Synthetic prior careers: seeded players carry
  `seasons_played_prior = age − 19` in `career_summary_json`.
  `should_retire` counts recorded + prior; **`seasons_played`, HoF cases,
  records, and every display surface keep recorded-only history** — no
  fabricated careers render. `_update_career_summaries` carries the prior
  across rewrites.
- Stale-recent truth fix: `recent_eliminations` now means the season being
  finalized — a vet benched all season reads 0, not the count from their
  last fielded season (which kept declining vets permanently above the <4
  retirement gate).
- Knock-on re-tune (measured): the vet-mix moved club recruitment profiles,
  collapsing the uncourted top-pick snipe rate 54% → 16%.
  `CONTESTED_USER_OFFER_BASE` re-tuned 90.0 → 85.0 against
  `tools/contested_offer_probe.py` (60 seeds): uncourted **43%** sniped,
  courted +32 **12%**, interest-100 0% — the V16 design targets restored.
  Witness seeds re-derived per the pinned procedure (7, 13).
- New gates: `tests/test_v18_mortality_seeding.py` (age mix per club,
  prior-career consistency, recorded-history honesty, retirement-gate
  cause→effect, benched-recent truth).

**Task 3/4 gate results** (8 seeds × 10 seasons, official_foam, final
constants — this is the milestone AFTER state):

| Gate | Result |
|---|---|
| First league retirement ≤ S3 (mean) | ✅ engaged **3.0** (S3 on 8/8 seeds), passive **3.1** (BEFORE: 9.0 on 8/8) |
| Visible mortality without cratering | ✅ **1.80 retirements/season** league-wide (BEFORE 0.68, all S9–10); league mean OVR still grows 67 → 89; AI rosters at 12; HoF cadence revived (≤5.8 inducted by S10) |
| Ceiling delivery intact | ✅ engaged user 100%/100% shortfall 0.0; AI 95–99% (symmetry control holds) |
| Engaged snowball (Task 2 escalation) | ✅ **RESOLVED**: title share 41.2% → **22.5%** (parity baseline 16.7%), OVR-edge peak +4.5 → **+2.9**, and the AI league overtakes the engaged user by S8 (edge −1.6 by S10); six distinct champions |
| Contested-ness | ✅ 17–19 user snipes per sweep; `TestDynastyHealthGate` green |
| Determinism + full suite | ✅ dynasty determinism pins green; full `python -m pytest -q` green |

**AFTER table — title share & OVR-edge curves** (compare §BEFORE):

| Season | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Engaged titles /8 | 2 | 0 | 1 | 4 | 4 | 1 | 1 | 2 | 2 | 1 | **18/80 (22.5%)** |
| Engaged OVR-edge | −0.1 | +0.8 | +2.1 | +2.5 | +2.9 | +2.1 | +0.9 | −0.5 | −1.3 | −1.6 | |
| Passive titles /8 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **2/80 (2.5%)** |
| Retirements/season (league) | 0.0 | 0.0 | 1.4 | 1.4 | 5.1 | 1.4 | 2.8 | 2.5 | 1.9 | 1.7 | mean **1.80** |

**Flagged for V19 planning:**

1. **The passive lineup cliff.** The only difference between 22.5% and 2.5%
   title share is the one-click offseason lineup re-optimize. With the
   league now recruiting and developing at parity, a fast-forward player who
   never opens the Lineup Editor finishes rank ~6.0 from S7 on. The
   auto-pilot default (creation lineup order, signings seated at slot 6) is
   the V19 candidate: fast-forward should re-seat the fielded six (or
   disclose that it won't).
2. **S5 retirement cohort wave** (~5/league in one offseason): the seeded
   31–33 vets age out together in a fresh league. It washes out by S6 and
   only affects new careers' first cycle; acceptable texture, noted.
3. **League OVR inflation watch**: with everyone delivering, league mean
   fielded OVR converges high-80s by S10 (prospect pool mean potential ~87).
   Zero-sum match outcomes are unaffected, but stat/records cadence on an
   all-elite league is a V20/V21 presentation consideration.

## Task 5 — Verification sweep + retro

Full `python -m pytest -q`; `npm run build` + `npm run lint` if any frontend
copy changed; focused Playwright only if player-facing surfaces changed;
retro in `docs/retrospectives/`; STATUS + MILESTONES updates; push.

---

## BEFORE table (Task 1 capture — post-V17 main, pre-V18 dev changes)

Captured 2026-06-10 on main at `5fb72d4` (engine source unchanged since the
V17 sweep `a6165fa`; the only working-tree delta is the additive dev-arc
trace in `tools/dynasty_health_probe.py`). Config: 8 seeds × 10 seasons,
`official_foam`, seed base 20260600/stride 211, user club aurora.
**Engaged** = `--signings 3 --optimize-lineup`; **Passive** = `--signings 3`
(shipping auto-pilot default lineup). All arcs are post-offseason snapshots;
"peak OVR" is a starter's best post-offseason OVR; "eff. ceiling" is the
highest effective potential observed (stored potential + trajectory floor —
the engine growth cap), NOT the OVR-maxed display value.

### 1. Ceiling delivery — full-time starters (fielded six in ≥3 snapshots)

| Cohort | n | first OVR | peak OVR | eff. ceiling | shortfall | headroom closed | peak within 2 of ceiling |
|---|---|---|---|---|---|---|---|
| Engaged user club | 62 | 64.4 | 71.4 | 81.0 | **9.6** | **34%** | **6%** |
| Passive user club | 48 | 64.8 | 67.7 | 74.0 | 6.3 | 20% | 21% |
| AI clubs (engaged run) | 343 | 66.0 | 70.0 | 80.3 | 10.3 | 20% | 9% |
| AI clubs (passive run) | 344 | 66.0 | 70.0 | 80.2 | 10.3 | 20% | 10% |

The displayed ceiling is a ~10-OVR overpromise for a decade-long starter.
The pre-V17 report language ("~half of headroom closed by peak-end") was
GENEROUS: measured post-V17 closure for full-time starters is 20–34%. The
passive cohort's lower mean ceiling (74.0) is a composition effect — the
auto-pilot keeps the creation lineup, so high-potential signings ride the
bench and never qualify as starters; that is the lineup trap, not better
delivery. AI delivery (20%) is the Task 2/4 symmetry control: user and AI
develop on the same math today, and must still do so AFTER.

### 2. Mortality

| Metric | Engaged | Passive |
|---|---|---|
| First league retirement season (per seed) | 9, 9, 9, 9, 9, 9, 9, 9 | 9, 9, 9, 9, 9, 9, 9, 9 |
| League retirements/season (mean) | 0.68 | 0.69 |
| …of which seasons 1–8 | 0.00 | 0.00 |
| …seasons 9–10 (mean/offseason) | ~3.4 | ~3.4 |
| User-club retirements/season | 0.16 | 0.19 |

Zero retirements for eight straight seasons on every seed, then a season-9
cliff — exactly the `should_retire` seasons-played gate expressing (curated
players start at `seasons_played = 0`; the 18–29 age band reaches the age-36+
gates only by season ~9). Task 3 gate: first league retirement by season ≤ 3.

### 3. Title-share curve (user titles per season, /8 seeds)

| Season | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Engaged | 3 | 1 | 1 | 1 | 2 | 3 | 2 | 0 | 0 | 1 | **14/80 (17.5%)** |
| Passive | 3 | 2 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | **7/80 (8.8%)** |

Parity baseline = 1/6 = 16.7%. Engaged sits at parity with six distinct
champions (solstice 18, northwood 17, aurora 14, lunar 14, harbor 13,
granite 4); passive decays toward zero as the auto-pilot lineup ages. No
snowball in the BEFORE state — the V17-retro concern is a watch item for
AFTER, not a present condition.

### 4. OVR-edge curve (user fielded-6 OVR − best-AI fielded-6 OVR)

| Season | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Engaged | −0.50 | −0.29 | −0.21 | −0.10 | −0.44 | −0.27 | −0.59 | −0.33 | −0.75 | −1.23 |
| Passive | −1.50 | −2.86 | −3.13 | −3.79 | −5.19 | −6.16 | −7.86 | −9.29 | −8.63 | −7.75 |

The engaged user tracks the best AI club (slightly behind, −0.1 to −1.2)
while the league as a whole drifts upward ~+5 OVR over ten seasons with no
retirement pressure. The passive curve shows the aging-starter slide
(user fielded OVR 65.4 → 62.7 by S8 while the league grows), partially
recovering S9–S10 only because the retirement cliff finally clears vets.
League texture context: AI signings 5.0/offseason and 16 user snipes per
sweep in both configs (V16 churn intact).
