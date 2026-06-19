# V24 — The Board (Recruiting Apparatus)

Date: 2026-06-12
Status: **Active spec.** Implementation authority for the V24 milestone.
Era authority: `docs/specs/2026-06-12-climb-era-vision.md` (§ "V24 — The Board").
Build-state truth remains `docs/STATUS.md`.

**Implementation status (2026-06-12, branch `feature/v24-the-board`):** Phases
1–3 implemented + verified (commits `4d37c94`, `7e2c99f`, `f5d7747`; full
pytest green at each). Phases 4–7 remain. Minor resequencing from the plan
below: the Hometown *grade* ships with the other motivations in Phase 3 (Phase
2 delivered the district *data*). See `docs/STATUS.md` for the measured Phase-1
end-state evidence and the disclosed deferrals (AI motivation symmetry, the
Development ledger, in-season interest momentum from fit).

## Relation to Prior Specs

- **Supersedes nothing wholesale.** V24 *deepens* the existing recruiting chassis;
  it keeps the V16 contested round, the V2-A/B scouting + recruitment-domain
  models, and the V22 economy treasury as load-bearing substrate.
- **Builds directly on V23 — The World** (`2026-06-12-v23-the-world-spec.md`).
  V23 shipped the 28-club pyramid and **disclosed one open problem: end-state
  dominance** — on a pyramid save the AI Signing Day market is scoped to the
  *user's division only* (`recruitment._eligible_ai_offer_clubs`), so the
  world's top clubs (D1 Premier + International Circuit) get **no new blood**
  while the user compounds, eventually winning Worlds unopposed. **Closing that
  gap is V24's load-bearing requirement** and ships first (Phase 1).
- **Extends V16 (Contested Offseason)**: the contested resolver
  (`recruitment.conduct_recruitment_round` → `recruitment_domain.resolve_recruitment_round`)
  becomes the chokepoint where motivation grades feed offer strength and the
  hidden dealbreaker can veto a verbal.
- **Extends V18 (Development)**: V24 adds the per-(club, signee) ceiling-delivery
  ledger that `development.apply_season_development` currently computes and
  discards — the data source for the **Development** motivation.
- **Inherits** the integrity contract in `docs/specs/AGENTS.md` and ADR 0002
  (faithfulness-first): every motivation grade is computed from real save data
  with a ProofChip receipt; no hidden dials; intentional outcome changes update
  golden logs in the same pass.

## The problem V24 solves

The recruiting chassis is mechanically sound but shallow, and the V23 pyramid
exposed a structural hole:

1. **End-state dominance (the V23 open problem).** AI recruiting is hard-scoped
   to the user's division on pyramid saves. The 21 clubs outside the user's
   division never build a board, never bid, never sign — they only age, develop,
   and retire. The Worlds feeders (Premier + Circuit) therefore decay or stagnate
   while an engaged user compounds talent, producing unopposed Worlds dominance
   by ~S4–S6 (measured in `tools/climb_resistance_probe.py`).
2. **Recruiting is a menu errand, not a battle.** Today: scout narrows a band,
   contact/visit raise a flat 0–100 `interest` number, and at Signing Day the
   user offer is `79 + interest×0.18` against AI bids. There are no motivations,
   no rivals visible in-season, no funnel, no persistent focus list, no
   money-gated scouting reach, and `Prospect.hometown` is a misused surname.

V24 makes recruiting **the centerpiece system**: head-to-head battles for
prospects who *want* specific things, fought across a living world where every
club recruits on merit.

## Core design decision — pool structure (DISCLOSED owner-level call)

> Two mapping passes independently flagged this: the world holds **one shared
> 25-prospect class** (`prospect_pool`, PK `class_year, player_id`). Simply
> deleting the division filter so all 28 clubs bid on a 25-deep pool **starves
> the world** — with ~1.8 retirements/club/season (V18) the world needs ~50
> replacements/year; a 25-class shrinks every roster toward the 6-player floor
> over a dynasty. The fix is a pool-structure decision, not a one-line deletion.

**Decision: a single national class per year, district-rooted and
caliber-banded, with division-anchored *willingness* and money-gated
*visibility*.** This is the most faithful reading of the vision (which wants
"L1 district / L2 regional / L3 national" reach and "the D3 club courting a
national prodigy … visible, courtable, heartbreaking, and occasionally wins via
Local + Development receipts" — i.e. a national pool with geographic tiers, not
isolated per-division pools).

Concretely, each prospect gains two derived attributes (computed from rolls the
generator **already makes** — no new RNG draw, see Determinism below):

- **Home district** — one of the 7 D3 District identities
  (`world.DISTRICT_CLUBS` home_regions: Harborside, Old Quarter, Millfields,
  Northgate, Southbank, Westvale, Eastreach).
- **Reach band** — `DISTRICT` / `REGIONAL` / `NATIONAL`, derived from the
  prospect's rolled ceiling + trajectory (NATIONAL ≈ STAR/GENERATIONAL arcs,
  REGIONAL ≈ IMPACT, DISTRICT ≈ NORMAL).

**Visibility** is money-gated by a per-club **Scouting Network level** (L1/L2/L3,
treasury sink): L1 shows full sheets for DISTRICT-reach prospects in your home +
neighbor districts (everyone else is a *name without a sheet*); L2 adds REGIONAL;
L3 adds NATIONAL (national reach). **Willingness** is gated organically by
motivation grades, never a hard lock: a NATIONAL prodigy's Contender / Court-Time
grades for a D3 club are usually too low to verbal — unless **Hometown** (he's
from your district) and **Development** receipts flip him.

The class size grows from **25 → 56 (default, probe-tuned)** so the whole world
can sustain itself; the **user's in-scope board still surfaces ~the
caliber+network-appropriate slice (~25)**, so it does not feel like 56 cards.
Every AI club recruits the shared class biased to its reach + district, with its
own network level and district bias producing the **required blind spots** that
make unrecruited gems happen.

This structurally fixes end-state dominance (Premier/Circuit clubs win their
caliber-appropriate prospects → new blood every year) **and** delivers the
vision's signature cross-tier-courtship fantasy.

## Phased plan (each phase independently shippable + gated)

### Phase 1 — Whole-world AI recruiting *(the end-state-dominance fix; ships first)*
- Remove the division scope in `_eligible_ai_offer_clubs` (recruitment.py:445)
  **and** its mirror gate in `_ensure_recruitment_prepared` (recruitment.py:542)
  — both must change together (out-of-division clubs are otherwise eligible but
  boardless). Preserve **classic (non-pyramid) world** behavior unchanged.
- Grow `prospect_class_size` 25 → 56 (probe-tuned) so contention doesn't starve
  the world.
- Each AI club bids on its reach/district-appropriate prospects (basic reach
  weighting in this phase; full motivation weighting lands Phase 3).
- Update the disclosed division-scope copy on recruiting surfaces and the
  `recruitment.py:454-458` docstring.
- Basic **class wire**: a league-wide news line when a STAR/GENERATIONAL prospect
  signs (reuse `news_headlines`).
- **Gate:** new `tools/ai_board_coverage_probe.py` (every division signs > 0 new
  prospects/offseason; no division's reach-slice is exhausted) + extended
  `tools/climb_resistance_probe.py` over ~8 seasons (world top-tier fielded OVR
  keeps pace; user does **not** win Worlds unopposed). Re-derive moved contested
  / dynasty-health / prospect-pool witnesses (intentional outcome change → update
  golden logs).

### Phase 2 — Districts + Hometown
- Replace the surname `hometown` with one of the 7 districts at the existing
  draw site (recruitment.py:258); give each club a home district
  (D3 = its identity; founding user = its D3 seat / `custom_club.home_region`;
  higher tiers + Circuit = a district tie or muted Hometown).
- **Hometown** motivation (proximity grade). Persist district on `prospect_pool`.
- **Gate:** district-distribution fence; founding + takeover home-district
  resolution tests; determinism preserved (no stream shift — see below).

### Phase 3 — Motivations + dealbreaker (receipts-backed)
- Six motivations + Hometown, each an A–F grade per (prospect, club) computed
  from real save data with a ProofChip receipt:
  - **Court Time** — lineup/depth projection at the prospect's archetype slot.
  - **Contender** — standings / trophies / prestige.
  - **Development** — measured ceiling-delivery of past signees (NEW ledger;
    starts empty → honest limited-state, like league memory).
  - **Legacy** — HoF / league records / championships.
  - **Staff** — department-head ratings (AI proxy from tier/prestige; only the
    user club has a head table).
  - **Scheme Fit** — prospect archetype vs *actually-fielded* tactics.
  - **Hometown** — from Phase 2.
- **2–3 motivations visible; the dealbreaker hidden until scouted.** The
  dealbreaker is the prospect's single most-weighted motivation; a club graded
  below ~C in it **cannot reach Verbal** (a veto path, NOT a strength subtraction
  — `_resolution_sort_key` is offer-strength-dominant, so the veto must gate the
  offer's existence, with the honest "why" shown).
- Motivation fit feeds (a) in-season interest-gain momentum and (b) Signing Day
  offer strength (augments `79 + interest×0.18` with a motivation-fit term).
- Add the per-(club, signee) **dev-delivery ledger**, instrumenting BOTH
  `apply_season_development` call sites (`offseason_ceremony.py:662` and
  `dynasty_cli.py:1183`).
- **Gate:** courtship→outcome traceability (grades demonstrably flip outcomes:
  satisfying motivations wins picks a flat-interest offer would lose); dealbreaker
  veto fence; receipt-derivable-from-data fence.

### Phase 4 — Funnel stages + persistent focus list + visit scheduling
- **Open → Shortlist → Top 3 → Verbal** gating the verbs: Scout (any visible
  prospect), Contact (Shortlist+), Visit (Top 3 of the focus list only — visit is
  the scarce 1/week slot). Verbal = interest ≥ threshold AND leading all rival
  suitors AND no dealbreaker veto.
- **Persistent focus list** replaces the arbitrary `prospects[:8]` cap
  (recruiting_office.py:165). Persist stage + focus membership in the existing
  `prospect_recruitment_actions_json` blob (zero migration).
- Visits scheduled against the user's real **home fixtures** (scheduler join).
- **Gate:** verb-gating fence; focus-list persistence round-trip; visit↔fixture
  binding test.

### Phase 5 — Visible rival suitors + interest race
- Revive the dormant `prospect_market_signal` table (zero callers today): named
  rival suitors per focused prospect + relative interest/lead, surfaced
  **in-season** (not just at Signing Day). Early leads are defensible (momentum:
  leading interest compounds modestly).
- **Gate:** rival-signal determinism + receipt fence; momentum-defensibility
  measurement (an early lead wins more often than a late entry at equal effort).

### Phase 6 — Scouting Network visibility tiers
- Per-club network **level** (L1/L2/L3) as a treasury sink (V22 economy);
  upgrade cost + persisted scalar. Gates which prospects render a full sheet vs a
  name. AI clubs carry network levels by tier (blind spots).
- **Gate:** network-visibility fences (below-level prospects are names, not
  sheets); treasury-sink consumer test; staff cost-compression consumer
  (scouting head narrows bands faster at a given level — the vision's "staff
  cost-compression consumers").

### Phase 7 — Frontend integration + class-wire polish + verification
- Wire all new payload fields into `ProspectCard.tsx`, `RecruitmentChoice.tsx`,
  `RecruitingBadge.tsx`, `RecruitReactions.tsx` using the V15 legibility toolkit
  (ProofChip / TermTip / fog-of-war primitives). Class wire surfaced in the news
  ticker / Signing Day.
- Full `python -m pytest -q` green; `npm run build` + `npm run lint` clean; live
  prod-server browser walk on a fresh founded D3 career across several seasons;
  docs (STATUS / MILESTONES) + retrospective + learnings.

## Disclosed constants (defaults; each ships with probe evidence)

All live in the config layer (`config.py`), never hardcoded in engine logic.

| Constant | Default (proposed) | Tuned by |
|---|---|---|
| `prospect_class_size` | 25 → **56** | `ai_board_coverage_probe` (world sustains; ≥1 new blood/division) |
| Reach band cutoffs (ceiling/trajectory → DISTRICT/REGIONAL/NATIONAL) | NATIONAL=STAR+GEN, REGIONAL=IMPACT, DISTRICT=NORMAL | board-coverage + class-wire frequency |
| Network levels L1/L2/L3 upgrade cost ($k) | 60 / 140 / 280 (one-time, treasury) | economy-pressure probe (vs V22 payouts) |
| Network visibility map (level → reach bands fully visible) | L1=DISTRICT(+neighbors), L2=+REGIONAL, L3=+NATIONAL | visibility fence |
| Motivation weights (per-prospect, sum=1) | rolled from a stable per-prospect distribution | traceability probe |
| Dealbreaker veto threshold | grade < C (≈ < 0.45 normalized) | traceability/veto fence |
| Motivation-fit → offer-strength term | `+ fit × 18` (parallels interest weight 0.18×100) | `contested_offer_probe` (motivation flips outcomes) |
| Hometown proximity grades | same district = A, neighbor = B, else C/D by reach | district fence |
| AI network level by tier | D3=L1, D2=L2, D1/Circuit=L3 (+ jitter for blind spots) | board-coverage gem fence |

Constants are proposed sim-design with measured evidence, **never claimed as
real-world fidelity** (per the repo's WT-20 precedent).

## Determinism & back-compat guards

- **RNG stream (the #1 trap, flagged by 4 agents).** `generate_prospect_pool`
  consumes a fixed draw order per prospect. **Home district replaces the existing
  `rng.choice(_LAST_NAMES)` hometown draw at the same stream position**
  (verify `DeterministicRNG.choice` consumes a fixed number of underlying draws
  regardless of list length; if not, derive the district deterministically from
  the already-drawn value). **Reach band is a pure function of already-rolled
  ceiling+trajectory — no new draw.** Any genuinely new per-prospect draw is
  **appended at the end** of the per-prospect block or sourced from a separate
  `derive_seed` stream, so existing prospects stay byte-identical where possible.
- **Class-size growth is an intentional outcome change** (it shifts the contested
  market and dynasty witnesses). Re-derive and re-pin all moved witnesses and
  update golden logs in the same pass, with BEFORE/AFTER measurements in this
  spec's eventual retro.
- **Classic (non-pyramid) worlds unchanged.** The whole-world AI fix is gated on
  `world.pyramid_world_active`; legacy single-league saves keep current behavior.
- **Legacy-save reads** of any new `prospect_pool` column use the
  `if 'col' in row.keys()` defensive pattern (the v16 `pipeline_tier` precedent);
  new schema lands via a registered `_migrate_v19` + `CURRENT_SCHEMA_VERSION` 18→19.
- **Funnel/focus-list state** extends the existing `prospect_recruitment_actions_json`
  KV blob → zero migration, back-compat-free.
- **Signing limit (3)** is hardcoded in two places
  (`offseason_presentation.py:338`, `offseason_service.py:170`) — keep in sync.
- **Two scouting concepts stay distinct** (trap #2): the slot-budget **Scout
  verb**, the dormant named-scout four-axis engine (`scouting_center.py`), and the
  new money-gated **Scouting Network** are three different things — do not
  conflate.

## Proof obligations (vision § V24)

- **Courtship→outcome traceability gates** (Phase 3): motivation grades
  demonstrably change who signs.
- **AI board-coverage gap probe** (Phase 1): every division gets new blood;
  blind spots produce occasional unrecruited gems.
- **Network visibility fences** (Phase 6): below-level prospects are names, not
  sheets; money changes reach.
- **Staff cost-compression consumers** (Phase 6): the scouting head measurably
  compresses network/scout cost or band width.
- **End-state-dominance resolution probe** (Phase 1): extended climb-resistance
  run shows the world keeps pace; unopposed Worlds dominance is gone.
- **Determinism preserved**; intentional changes update golden logs.

## Out of scope (deferred per the era ledger)

Contracts/salaries/transfer market (V25), fans/facilities/bench roles (V26),
the event calendar / cups / invitationals (V27), emergent meta / journalism
(V28). International recruiting "go global" stays deferred until a Worlds-regular
expansion. No NG+, no patch dials.
