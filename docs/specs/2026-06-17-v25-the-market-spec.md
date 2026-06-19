# V25 — The Market (Contracts)

Date: 2026-06-17
Status: **Active spec.** Implementation authority for the V25 milestone.
Era authority: `docs/specs/2026-06-12-climb-era-vision.md` (§ "V25 — The Market").
Build-state truth remains `docs/STATUS.md`.

**Implementation status (2026-06-17, branch `feature/v24-the-board`):** not yet
started. V24 — The Board is complete on this branch (through `f3d3975`); per the
owner decision (2026-06-14) V25 builds on the **same branch** — the Climb-Era arc
merges to `main` as a unit when ready. Phases below are each independently
shippable and gated.

## Relation to Prior Specs

- **Supersedes nothing wholesale.** V25 *adds a money layer to people*; it keeps
  the V22 economy treasury, the V23 pyramid, and the V24 recruiting apparatus +
  motivation grades as load-bearing substrate.
- **Builds directly on V24 — The Board** (`2026-06-12-v24-the-board-spec.md`).
  V24 made recruiting the centerpiece via seven receipts-backed motivation grades
  (`motivations.club_fit` / `build_club_context` / `prospect_motivation_profile`)
  and a dealbreaker veto. **V25 retention is recruiting's mirror: the same grades,
  the same contested resolver, the same veto — applied to a rostered player vs his
  own club.** `club_fit()` and `build_club_context()` already accept any `club_id`
  and any object exposing the prospect interface (`.player_id`, `hometown`,
  `public_archetype_guess`), so a `Player` is passable directly.
- **Extends V22 — Founding Choices & Club Economy**
  (`2026-06-11-v22-founding-choices-club-economy.md`). V22 shipped the user-club
  treasury (`economy.treasury_k` / `set_treasury_k`), the once-per-offseason
  settlement (`economy.apply_season_finances`, `offseason_ceremony.py`), the
  tier-scaled payouts (`TIER_PAYOUT_MULTIPLIERS = {1:1.8, 2:1.35, 3:1.0}`), and
  the `hiring_frozen` squeeze gate. V25 adds a **player wage bill** as a new
  outflow line in that same settlement, and a **standardized entry salary** at
  signing. The V22 comment at `economy.py` ("AI club budgets stay abstracted")
  already anticipates V25 as the pressure counterweight to promotion payouts.
- **Extends V23 — The World** (`2026-06-12-v23-the-world-spec.md`). Poaching
  "flows uphill" along the tier pyramid; salaries scale by division; promotion
  inflates payroll exactly as it raises prize money (the `0.35×`-D3-spiral
  rejection from V23 is the precedent for *squeeze, never spiral*).
- **Inherits** the integrity contract in `docs/specs/AGENTS.md` and ADR 0002
  (faithfulness-first): every departure carries a data-derived receipt; no hidden
  dials; intentional outcome changes update golden logs in the same pass.

## The problem V25 solves

The dynasty record is real and recruiting is now a battle, but **money never
enters a player's story.** A signed player is yours forever, free, with no wage
cost and no rival able to take him. There is:

1. **No wage pressure.** The treasury settles staff payroll only; a champion
   roster costs the same as a basement one. Promotion raises income with no
   matching cost, so climbing *unsqueezes* the treasury — the opposite of the
   intended tension.
2. **No retention game.** Players never expire, never get courted away, never
   have to be re-signed. The motivation grades that decide *who you sign* have no
   say in *who you keep*.
3. **No uphill poaching.** A homegrown D3 star you develop to Premier caliber
   can never be hunted by a richer club — removing the central drama of a climb
   (the roster fortress you cannot fully hold) and a structural pressure that
   keeps the world's rosters churning.

V25 makes **keeping a roster as much a decision as building one**, with the same
receipts-backed grades and the same contested resolver, played symmetrically by
the AI.

## Core design decisions (owner-confirmed)

### 1. AI finance scope — wage *budget cap*, not full treasuries (DISCLOSED call)

The repo deliberately keeps AI club finances abstracted (`economy.py` is
user-club-only; `dynasty_state['club_treasury_k']` is a single user value). Full
per-club AI treasuries — income settlement, running balances, going-broke spirals
across 28 clubs — is a large, risky build and is **not** what the vision needs.

**Decision: each AI club carries a wage *bill* (sum of its roster `salary_k`)
measured against a tier-derived wage *budget cap*; it has no treasury balance.**
Headroom (`budget − bill`) gates how aggressively the club poaches and re-signs;
a club over budget must shed wage (cut/sell a player — the "AI mistake" and news
fodder). This delivers the symmetric *pressure* the vision requires ("AI wage
bills, AI mistakes, news fodder") while keeping AI finances abstracted, fully
deterministic, and far cheaper than per-club accounting. AI wage budget is a pure
function of `tier` (reusing the `TIER_PAYOUT_MULTIPLIERS` shape), never persisted
as a mutable balance.

### 2. Transfer Period — a new gating beat mirroring Signing Day

**Decision: a new offseason ceremony beat `transfer_period` with its own
`CareerState` (`SEASON_COMPLETE_TRANSFER_PENDING`), modeled on the proven
`recruitment` beat.** It resolves: re-sign offers on expiring players, responses
to incoming buyout offers, and optional outgoing buyout bids. It carries a
one-click **"resolve all / auto"** path so fast-forward / auto-pilot still works
(the tested PT4 pattern — auto-pilot is a first-class path). Mandatory decisions
(an expiring star, an incoming buyout) must be acted on (or auto-resolved by
motivation default) before advancing — exactly as `recruitment` gates today.

This needs a new `CareerState` plus its `_ALLOWED` edges in `career_state.py`
(the existing `recruitment` beat is the template); a non-gating beat would risk
half-resolved contract state.

### 3. Beat placement + back-compat

**Decision: insert `transfer_period` between `retirements` and
`rookie_class_preview`** in `OFFSEASON_CEREMONY_BEATS`:

```
… development → retirements → transfer_period → rookie_class_preview → recruitment → schedule_reveal
```

You see who developed and who retired, **then** resolve your standing roster's
contracts (re-sign / lose to poaching / sell), **then** preview and sign the
incoming class into the space you just managed. Contract aging (term decrement)
and the wage-bill settlement happen inside `initialize_manager_offseason` before
any beat renders (alongside the existing finances + development passes), so the
beat reads cached state and never re-settles.

**The entire V25 layer is gated behind `world.pyramid_world_active()`.**
Legacy / non-pyramid saves stay byte-identical: no salaries, no wage bill, no
Transfer Period beat — exactly as V23/V24 gate their additions.

## Data model (minimal, low-risk)

- **`Player` gains `salary_k: int = 0` and `contract_term: int = 1`** (seasons
  remaining on the current deal). `Player` is a frozen dataclass serialized as a
  JSON blob in `club_rosters.players_json`, `free_agents.player_json`, and
  `retired_players.player_json` — there is **no per-player table row**. The two
  fields ride the existing `_player_to_dict` / `_player_from_dict` boundary
  (`persistence.py`) with **`.get('salary_k', 0)` / `.get('contract_term', 1)`
  defaults** → pre-V25 saves deserialize unchanged, **no schema migration for
  player fields**. (`_player_from_dict` raises on *missing required* fields, so
  the `.get()` default is mandatory — never `d['salary_k']`.)
- **One-time deterministic backfill.** On the first V25 offseason of an
  in-progress pyramid save (guarded by a `dynasty_state` sentinel
  `v25_contracts_seeded_for`), every existing rostered player is priced in
  (salary from the second-contract formula on current OVR + tier; a spread of
  terms so they do not all expire the same season). New careers seed entry deals
  at signing and need no backfill.
- **AI wage bill / budget are computed, not stored.** Bill = `sum(p.salary_k)`
  over an AI club's roster (every player now carries `salary_k`); budget =
  `wage_budget_for_tier(tier)`. No clubs-table column, no AI treasury row.
- **Transfer-period state + idempotency guards** live in `dynasty_state` KV
  (`v25_transfer_state_json`, `v25_transfer_resolved_for`, `v25_poach_done_for`)
  — never reuse `finances_applied_for`, `offseason_ai_signings_done_for`, or
  `offseason_draft_signed_count`.
- **Transfer ledger (the one possible migration).** League-wide veteran movement
  (the roster-fortress proof + the news line + the departures-with-receipts strip)
  reads from a movement record. Default: a `v25_transfers_json` blob per season in
  `dynasty_state` (zero migration). If a queryable history proves cleaner during
  planning, a single additive `player_transfers` table lands via a registered
  `_migrate_v19` + `CURRENT_SCHEMA_VERSION` 18→19 (the v18 `division_membership`
  precedent), idempotent ALTER/CREATE with column-existence guards.
- **New `derive_seed` namespaces:** `v25_contract`, `v25_transfer`, `v25_poach`
  (globally unique). The motivation stream stays `derive_seed(0, 'v24_motivation',
  player_id)` — **root_seed is the hardcoded `0`, not the save seed**; retention
  reuses it verbatim so existing grades never flip.

## Phased plan (each phase independently shippable + gated)

### Phase 1 — Contracts foundation (data, entry deals, wage settlement)
- Add `salary_k` / `contract_term` to `Player` (`models.py`) with defaults; thread
  through `_player_to_dict` / `_player_from_dict` with `.get()` defaults.
- **STANDARD entry deals at signing** (ability-blind, tier-standardized): the
  point a prospect becomes a `Player` (`recruitment.sign_prospect_to_club`, and
  the user contested path through `offseason_ceremony`) assigns a tier-standard
  entry `salary_k` and an entry `contract_term` (e.g. 3 seasons). Money does *not*
  enter at recruiting — every prospect signs the same tier-standard deal, so
  recruiting stays a pure courtship game.
- **Wage bill in settlement.** Extend `economy.apply_season_finances` with a
  `player_wage_bill_k` outflow (sum of the user club's active roster `salary_k`),
  subtracted alongside `staff_payroll_k`; add the line to the persisted ledger
  JSON and the recap **Finances** block. Promotion raises tier-standard salaries
  (payroll inflates) as it raises payouts — **MODERATE** squeeze.
- One-time backfill (above), gated by `pyramid_world_active`.
- **Gate:** `tests/test_v25_contracts.py` — entry-deal standardization (two
  prospects of different OVR sign equal entry salaries at the same tier);
  wage-bill appears as a settlement outflow; legacy/non-pyramid saves
  byte-identical (no salary, no wage line); backfill determinism + idempotency.

### Phase 2 — Contract aging, expiry, and retention (re-sign) — user side
- **Term decrement** for every club's players in the `initialize_manager_offseason`
  all-clubs loop; `contract_term` reaching 0 ⇒ *expiring* this Transfer Period.
  Expiry keys on the numeric season order (`season_sort_key`), never lexical
  `season_id` sort.
- **Retention = recruiting's mirror.** For each expiring user player, build the
  club context for *his own club* (`build_club_context`) and grade him
  (`club_fit` on the `Player`); the user makes a re-sign offer (salary + term).
  Willingness is the motivation fit plus the offer — a high-fit player re-signs
  willingly/cheap, a low-fit one demands more or walks. **Second-contract salaries
  scale with ability + division** (this is where money enters his story).
- Reuse the contested resolver shape: the re-sign offer is a `user_offer` analog;
  the dealbreaker veto still applies (a player whose dealbreaker grade for your
  club has fallen below ~C will not re-sign regardless of money — with the honest
  why shown).
- **Gate:** retention traceability (a strong Contender/Court-Time grade re-signs a
  player a weak-grade club would lose at equal money); expiry-cohort spread fence
  (terms do not all collapse to one season); squeeze invariant (re-signing a star
  raises the wage bill, never creates a multi-season negative spiral).

### Phase 3 — Uphill poaching (AI hunts the user's expiring stars)
- Higher-tier AI clubs **with wage headroom** bid on the user's expiring players.
  Poach interest reuses `prospect_market.derive_club_pursuit` (substituting player
  OVR for the prospect public band) on the new `v25_poach` stream; eligibility
  reuses the `_eligible_ai_offer_clubs` shape extended with the wage-headroom
  check. Resolution is the existing offer-strength comparison
  (`recruitment_domain.resolve_recruitment_round`): the user's retention offer
  competes against poach bids; **motivations break ties.**
- **Every departure carries a receipt** ("outbid ×2.1, and your Contender grade
  is D"), derived from the actual offer ratio + the grade that lost him.
- **Modest development-compensation credit** to the user treasury when a homegrown
  player is taken (a tuned fraction; income, not a windfall).
- **Gate:** `tools/poach_retention_probe.py` — grades demonstrably flip poach
  outcomes (a well-graded club keeps a star a rival outbids; a poorly-graded club
  loses one it outbids); uphill-only fence (lower-tier clubs do not poach up);
  receipt-derivable-from-data fence.

### Phase 4 — Buyouts (incoming refusable, outgoing bids)
- **Incoming buyout offers you can refuse** on your *contracted* (non-expiring)
  players — the "couldn't let him fall into another team's hands" beat. Accepting
  is treasury income (buyout fee); refusing keeps the player and the wage.
- **Outgoing buyout bids** against AI asking prices to buy a contracted player
  from another club — rich-club privilege by construction (gated by treasury and,
  on success, by the resulting wage bill). Asking price is a tuned function of OVR
  + remaining term + tier.
- **Gate:** buyout-fee formula probe; refuse-keeps-player fence; outgoing-bid
  treasury + wage-headroom gating; no mid-season movement (buyouts resolve only in
  the Transfer Period beat).

### Phase 5 — AI symmetry + news fodder
- **AI re-signs its own expiring players** via the same motivation grades (the AI
  proxy staff/context already exists from V24); wage-budget headroom forces an AI
  club to let an expiring player walk or to cut wage — real AI roster churn.
- **Class-wire-style news line** on a notable transfer/poach (reuse the V24
  `news_headlines` chokepoint), e.g. "Premier side signs your D3 star".
- **Roster-fortress invariant:** league-wide veteran (re-sign/poach/buyout)
  movement > 0 every offseason — no frozen rosters.
- **Gate:** AI-symmetry fence (AI clubs re-sign and lose players on merit, not
  fake results); `tools/roster_fortress_probe.py` (movement > 0/offseason across
  ~8 seasons); news-line derivable-from-data fence.

### Phase 6 — Frontend Transfer Period UI + contract surfacing
- New `transfer_period` ceremony component (own file or `Ceremonies.tsx`), routed
  through `Offseason.tsx`'s beat dispatcher and wrapped in `CeremonyShell`: the
  re-sign offer cards, incoming-buyout accept/refuse, outgoing-bid actions, and a
  departures-with-receipts strip. New `dynastyApi`/offseason POST methods follow
  the `hireStaff` / `upgradeNetwork` / `recruit` pattern (typed response →
  `setBeat`).
- Surface **`salary_k` / `contract_term`** on roster + player cards (via `money.ts`
  `formatK`, integer-thousands); add a **wages** line to the `RecapStandings`
  Finances block. Add the new optional fields to the Pydantic response models
  **before** the frontend reads them (the `response_model` strips undeclared keys
  — Playtest-3 F-8 trap) and to `types.ts`.
- No frontend test runner → verify via `npm run build` + `npm run lint` +
  data-flow inspection + Python guards on the rendered backend strings.

### Phase 7 — Balance pass + probes + verification
- Tune and pin: entry-salary scale, second-contract scale, wage-budget caps,
  poach pursuit weighting, buyout-fee formula, dev-compensation size — each shipped
  with its probe evidence.
- Run + record BEFORE/AFTER: `poach_retention_probe`, `roster_fortress_probe`, the
  squeeze-never-spiral invariant over ~8 seasons (promotion inflates payroll but
  never spirals the treasury negative across multiple seasons).
- Re-derive any moved witnesses (adding `salary_k`/`contract_term` to the player
  JSON shifts player-blob fixtures; the wage bill changes the user finances
  ledger) → update golden logs in the same pass.
- Full `python -m pytest -q` green; `npm run build` + `npm run lint` clean; live
  prod-server browser walk on a founded D3 career across several seasons (re-sign a
  star, lose one to an uphill poach with a receipt, refuse a buyout); docs
  (STATUS / MILESTONES) + retrospective + learnings.

## Disclosed constants (defaults; each ships with probe evidence)

All live in the config layer (`config.EconomyConfig` / new V25 fields), never
hardcoded in engine logic.

| Constant | Default (proposed) | Tuned by |
|---|---|---|
| Entry `contract_term` | 3 seasons | expiry-cohort spread fence |
| Entry `salary_k` by tier (ability-blind) | D3 / D2 / D1·Circuit standardized, scaled on `TIER_PAYOUT_MULTIPLIERS` shape | wage-pressure probe (vs V22 payouts) |
| Second-contract `salary_k` | `floor + per_ovr × OVR`, × tier multiplier | wage-pressure + squeeze probe |
| AI wage budget by tier | tier-scaled cap (no balance) | `roster_fortress_probe` (AI churns, never freezes/explodes) |
| Poach pursuit weighting (OVR → uphill interest) | parallels `derive_club_pursuit` talent/upside split | `poach_retention_probe` (grades flip outcomes) |
| Dev-compensation credit | modest fraction of the player's market value | squeeze probe (income, not windfall) |
| Buyout fee / AI asking price | `f(OVR, term_remaining, tier)` | buyout-fee probe |
| MODERATE squeeze calibration | promotion wage inflation consumes a *meaningful fraction* (not all) of the payout bump | multi-season squeeze-never-spiral invariant |

Constants are proposed sim-design with measured evidence, **never claimed as
real-world fidelity** (the WT-20 precedent).

## Determinism & back-compat guards

- **Player JSON blob (the #1 trap).** New fields read via `.get()` defaults in
  `_player_from_dict`, never `d[...]` — pre-V25 saves load unchanged. Salary
  assignment at seeding/backfill happens **outside** the roster RNG draw loop (or
  on the separate `v25_contract` stream) so roster witnesses do not shift
  (`build_curated_roster` uses post-hoc `dataclasses.replace` for exactly this).
- **Motivation stream is `root_seed=0`** (`derive_seed(0, 'v24_motivation', id)`).
  Retention reuses it verbatim; do not switch it to the save seed or every grade
  flips.
- **New namespaces only.** Poach/transfer draws use `v25_poach` / `v25_transfer`
  / `v25_contract`; never append draws to `recruitment_offer_strength` or any
  existing namespace (it shifts all later draws there).
- **Idempotency guards are V25-specific** dynasty_state keys; never reuse
  `finances_applied_for` (season-scoped — a Transfer Period mutation under that key
  would be skipped on reload), `offseason_ai_signings_done_for`, or
  `offseason_draft_signed_count` (the Signing Day slot counter must keep counting
  only Signing Day).
- **`OFFSEASON_CEREMONY_BEATS` + active-beats list must change together.** Adding
  `transfer_period` to the canonical tuple without the conditional/active-beats
  wiring corrupts beat routing (positional index + `.index(beat_key)` lookup). An
  already-initialized in-progress offseason caches its active-beats list — the new
  beat appears from the next offseason; `load_active_beats` falls back to the full
  tuple on mid-migration saves.
- **New `CareerState` needs `_ALLOWED` edges.** `SEASON_COMPLETE_TRANSFER_PENDING`
  must be reachable from the beat before it and able to advance to the recruitment
  path, or `advance()` raises `InvalidTransitionError`.
- **Settlement ordering.** Wage bill is settled inside `initialize_manager_offseason`
  with the existing finances pass (before beats render); re-sign/buyout treasury
  effects from the *interactive* beat apply as point-in-time `set_treasury_k`
  events (the `upgrade_scouting_network` precedent), not via a second
  `apply_season_finances` call.
- **Classic (non-pyramid) worlds unchanged** — the whole V25 layer is behind
  `pyramid_world_active`. Pre-V22 saves (lazy `takeover_treasury_k` default) keep
  loading without a wage bill.

## Proof obligations (vision § V25)

- **Poach/retention probe** — motivation grades demonstrably flip outcomes
  (a good Contender grade keeps a star a rival outbids).
- **Squeeze-never-spiral invariants extended** — promotion raises payroll and
  payouts together; no multi-season negative treasury spiral (the V23 −217k
  rejection precedent).
- **Roster-fortress gate** — league-wide veteran movement > 0 per offseason.
- **AI symmetry** — AI re-signs and loses players on merit (real results, no fake
  movement); wage budgets produce real AI churn.
- **Determinism preserved**; intentional outcome changes (player-blob fields, the
  finances ledger) update golden logs in the same pass.

## Out of scope (deferred per the era ledger)

Fans / facilities / bench roles / media spice (V26); the event calendar, cups,
ruleset invitationals, Worlds crowning ceremony (V27); emergent meta + journalism
+ officiating emphasis (V28). No mid-season transfer windows (Transfer Period is
an offseason beat only). No full AI club treasuries (wage-budget cap only — see
core decision 1). No NG+, no patch dials, no abstracted/fake match or transfer
results. International recruiting "go global" stays deferred until a Worlds-regular
expansion. The post-V26 *fan premium* on salaries is a forward hook, not built
here.
