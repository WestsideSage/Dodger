# V26 — The Crowd (Fans, Facilities, Roles, Media)

Date: 2026-06-17
Status: **Active spec.** Implementation authority for the V26 milestone.
Era authority: `docs/specs/2026-06-12-climb-era-vision.md` (§ "V26 — The Crowd").
Build-state truth remains `docs/STATUS.md`.

**Implementation status (2026-06-17, branch `feature/v24-the-board`):** not yet
started. V23 (The World), V24 (The Board), and V25 (The Market) are complete on
this branch; per the owner decision the Climb-Era arc builds on the one branch
and merges to `main` as a unit. Phases below are each independently shippable
and gated.

## Relation to Prior Specs

- **Revives dormant-but-built systems, modernized to current standards.** Two
  subsystems were fully built in the CLI era but never activated in the web game:
  - **Facilities** (`facilities.py` + the `club_facilities` table + the
    `apply_facility_effects` → `_facility_bonus` development hook). The CLI
    dynasty path wires them; the web offseason passes `facilities=()` for every
    club, so the effects are silently suppressed. V26 revives them in the web
    path and modernizes them to the V22–V25 economy idiom (treasury-gated,
    `pyramid_world_active`-gated, config-driven constants, deterministic).
  - **Prestige growth** (`dynasty_cli._award_prestige_for_season` + the cup/title
    `+6` grants). This is **CLI-only** — on web saves prestige is frozen at its
    founding/takeover seed, so V24's `motivations._grade_contender` (the only
    motivation consumer of prestige) reads a static value. V26 ports prestige
    growth to the web offseason as part of the club-fan phase.
- **Extends V22 — Founding Choices & Club Economy.** Matchday + merch income are
  new lines in `economy.apply_season_finances` alongside V25's wage bill; new
  `EconomyConfig` fields (defaults `0` → legacy byte-identical).
- **Extends V25 — The Market.** The bench-role **Ambassador** monetizes a
  player's fan following into the same treasury; facilities/fan income compete
  with V25 wages for the one treasury (TFM2 budget freedom — no earmarks).
- **Extends V18 — Development.** The bench-role **Mentor** adds the first
  *per-player* development modifier (the existing `staff_development_modifier` is
  a club-wide scalar) and is the identity traits' first honest consumer.
- **Extends V24 — The Board.** The bench-role **Analyst** feeds the existing
  `targeting_read_bonus` preps channel (scaling with `tactical_iq`); media
  mini-events route effects into prestige + a one-season credibility bonus
  (`recruiting_office._credibility`), never match outcomes.
- **Inherits** the integrity contract in `docs/specs/AGENTS.md` and ADR 0002
  (faithfulness-first): every fan change is an **append-only receipt** derivable
  from a logged event; no hidden dials; intentional development-outcome changes
  (the facility revival) update golden logs in the same pass.

## The problem V26 solves

The world has a record but no **crowd**. Specifically:

1. **Dormant facilities.** A full facilities system ships in the build but the
   web game feeds it `()` — the player can never invest in development
   infrastructure, and the effect code is dead weight.
2. **Frozen prestige.** Prestige only grows in the legacy CLI loop, so on the
   real (web) game a club's V24 Contender grade and recruiting pull never reflect
   its actual rise.
3. **No fan economy.** Wins, titles, promotions, Worlds runs, MVPs, and records
   are all logged but lead nowhere — there is no following, no matchday, no
   merch. The dynasty has no fans to play for.
4. **Bench is inert.** Non-starters do nothing between matches, and three of the
   four identity traits are honestly dead. There is no role for a veteran to
   mentor, analyze, or be a club ambassador.

V26 gives the program a living crowd: a receipted fan ledger that pays a
meaningful margin, facilities to invest in, bench roles that make depth and the
identity traits matter, and occasional media beats — all from real events,
nothing injected.

## Core design decisions (owner-confirmed)

### 1. Facilities are a TREASURY sink (modernized), not prestige

The vision mandates "one treasury, no earmarks." V26 web facilities cost
treasury (cloning the proven V24 Scouting-Network upgrade pattern: a per-club
persisted level, a `POST` upgrade endpoint, a `DynastyOffice` panel). The
existing `DevelopmentModifiers` effects are revived in the web development path.
The legacy CLI prestige-gated picker is left untouched. **Back-compat holds:** a
fresh web save owns no facilities, so reviving the `load_club_facilities` *read*
changes nothing until the user buys one.

### 2. Fans are a NEW append-only ledger, separate from prestige

Two ledgers — **club fans** and **per-player followings** — grown ONLY from real
logged events, each change an append-only **receipt** (never the opaque single-
scalar prestige pattern). Prestige stays the V24 motivation/credibility signal
(and V26 finally grows it on web); fans feed **income** and the Ambassador role.
Both are **user-program features** (AI clubs are abstracted, like the treasury) —
fan income is the user's program-building margin.

### 3. Fan income is a meaningful margin, never prize money's rival

Matchday (fans drawn, capped by stadium capacity) + merch (club fans + star
followings × merch level) are new `apply_season_finances` outflow-companions,
tuned so combined fan income is **~15–25% of a competitive finish's prize money**
(tension, not tyranny). Pyramid-gated; legacy `0`.

### 4. Media mini-events are an OFFSEASON choice beat

A new `media_event` offseason beat (between `rookie_class_preview` and
`recruitment`) presents occasional choice cards whose effects land ONLY in
fans / prestige / a one-season credibility bonus — **never** match outcomes
(HARD invariant). The in-season command-card surface is a heavier integration,
deferred.

## Data model (the first Climb-Era schema migration)

- **New tables (`_migrate_v19`, `CURRENT_SCHEMA_VERSION` 18→19):**
  - `club_fans (club_id PK, fans_count INTEGER DEFAULT 0)`
  - `player_fans (player_id PK, followers_count INTEGER DEFAULT 0)`
  - `fan_ledger (ledger_id PK, entity_id, entity_type 'club'|'player', season_id,
    event_type, delta, running_total, receipt)` — append-only.
  All additive, idempotent ALTER/CREATE with column-existence guards (the v18
  `division_membership` precedent). Legacy saves: empty tables → no fans → no fan
  income → byte-identical.
- **Facilities** reuse the existing `club_facilities` table (per-club/season
  rows) with new `FacilityType` values added to `FACILITY_DEFINITIONS` — no
  migration for facility storage; a per-club facility **level** (treasury cost)
  rides `dynasty_state` or a small additive column, decided at planning time.
- **Bench roles** persist as a small per-(club, season) map in `dynasty_state`
  JSON (`v26_bench_roles_json`) — zero migration; one role per non-starter.
- **`EconomyConfig`** gains `stadium_base_capacity`, `merch_base_rate_k`,
  `fan_income_per_1k_k`, and facility/fan-gain knobs — all defaulting so legacy
  finances are unchanged.
- **New `derive_seed` namespaces** only (`v26_media` for media-event selection);
  fan gains are deterministic functions of logged events (no new RNG).

## Phased plan (each phase independently shippable + gated)

### Phase 1 — Facilities revival + modernization
- Wire `load_club_facilities(conn, club_id, season_id)` into the web offseason
  development pass (`offseason_ceremony.py` — the `facilities=()` site), so the
  existing `DevelopmentModifiers` effects finally land for clubs that own them.
- Modernize: a treasury-gated per-club facility level + `POST
  /api/dynasty-office/facilities/upgrade` + a `FacilitiesUpgradePanel` (clone
  `ScoutingNetworkPanel`); add **Training Hall / Stadium / Merch Center** facility
  types (Stadium + Merch feed Phase 4 income; Training Hall feeds development).
  Move the facility constants into the config layer; `pyramid_world_active`-gated.
- **Gate:** `tests/test_v26_facilities.py` — owning a Training Hall measurably
  raises a developing player's delta (effect is real, not flavor); treasury-sink
  consumer test; legacy/non-pyramid + no-facilities byte-identical; the dead
  computed `scouting_*_bonus` fields either consumed or removed (current
  standards — no dead modifiers).

### Phase 2 — Club fan ledger (+ prestige growth ported to web)
- A receipted `club_fans` ledger grown from logged events: wins (per-win),
  promotions + Worlds finalist/champion (`pyramid_postseason` ledger /
  `worlds_history_json`), titles + cups (`club_trophies`), rivalry wins
  (`rivalry_records`, weighted by `compute_rivalry_score`). Each grant writes a
  `fan_ledger` receipt ("+400 after the promotion final"). Idempotent
  (`v26_fans_awarded_for` guard, the `prestige_awarded_for` precedent).
- **Port prestige growth to the web offseason** (the dormant
  `_award_prestige_for_season` logic + the cup/title `+6`), so V24 Contender +
  credibility grow from real events on web saves. Modernized into a shared
  offseason event-rollup that feeds BOTH prestige and club fans.
- **Gate:** fan-ledger receipt audit (every delta derivable from a logged event);
  prestige-grows-on-web fence; idempotency.

### Phase 3 — Player followings
- A receipted `player_fans` ledger from MVPs/awards (`signature_moments`
  `moment_type`), records + round-number milestones (`RatifiedRecord.is_new_holder`
  / `milestone_label`), and **district ties** (`Club.home_region`, the dormant-
  but-real field). (In-game `MomentKind` events are replay-only / not persisted —
  disclosed; a future moment-persistence pass would add them.)
- **Gate:** player-following receipt audit; a star accrues a following its
  benchwarmer does not; determinism.

### Phase 4 — Fan income (matchday + merch)
- New `apply_season_finances` lines: **matchday** = `min(club_fans, stadium
  capacity) × per-fan rate` (stadium capacity from the Phase-1 Stadium facility);
  **merch** = `(club_fans + Σ star followings) × merch level rate` (Merch Center
  facility). Surfaced in the Recap finances block + the `season_finances_json`
  ledger + the honest rules line. Pyramid-gated; legacy `0`.
- **Gate:** `tools/fan_income_probe.py` — combined fan income is a meaningful
  margin (~15–25% of competitive prize money) and **never exceeds** prize money
  at any tier; legacy byte-identical (no fan lines).

### Phase 5 — Bench roles
- One role per non-starter, per-season (no weekly micro), persisted in
  `v26_bench_roles_json`:
  - **Mentor** — a per-player development modifier on paired youngsters (a NEW
    `mentor_dev_bonus` parameter on `apply_season_development`, applied only to
    young targets); effectiveness scales with the mentor's relevant identity
    trait (the traits' first honest consumer).
  - **Analyst** — adds a `targeting_read_bonus` into the preps dict (both
    engines already read it), scaling with the analyst's `tactical_iq`.
  - **Ambassador** — converts his own following into merch/matchday income.
- Assignment UI on the lineup/roster surface; AI symmetric where cheap (AI may
  auto-assign a Mentor), else user-only and disclosed.
- **Gate:** role-consumer tests — each role has a measurable, receipted effect
  (nothing flavor-only); a Mentor measurably lifts a youngster's delta vs an
  unmentored control; an Analyst measurably shifts the targeting read.

### Phase 6 — Media mini-events
- A new `media_event` offseason beat (between `rookie_class_preview` and
  `recruitment`), conditional (only when an event fires). Choice cards on the
  `v26_media` stream; each option's effect routes ONLY to fans (`club_fans` /
  `player_fans` deltas with receipts), prestige (`save_club_prestige`), or a
  one-season credibility bonus stored in `dynasty_state` and read inside
  `recruiting_office._credibility`. Commit-on-choose (the V25 beat precedent).
- **Gate:** media-effect-isolation fence (a media choice can NEVER alter a match
  result, standings, or development — only fans/prestige/credibility); beat
  appears/absent correctly; determinism.

### Phase 7 — Balance pass + probes + verification
- Tune + pin: fan-gain constants per event, stadium capacity by tier, merch +
  matchday rates, facility costs + effects — each with probe evidence.
- Run + record: `fan_income_probe` (margin, never rivals prize money), facility
  effect probe (BEFORE/AFTER development delta), role-consumer probes.
- Re-derive any moved development witnesses (the facility revival changes deltas
  for facility-owning clubs) → update golden logs in the same pass.
- Full `python -m pytest -q` green (real exit code, no pipe); `npm run build` +
  `npm run lint` clean; live prod-server browser walk (buy a facility, watch fans
  accrue with receipts, see matchday/merch in the Recap, assign a bench role,
  resolve a media beat); docs (STATUS / MILESTONES) + retrospective + learnings.

## Disclosed constants (defaults; each ships with probe evidence)

All live in the config layer (`EconomyConfig` / new V26 fields / `facilities.py`
catalog), never hardcoded in engine logic. Constants are proposed sim-design with
measured evidence, never claimed as real-world fidelity.

| Constant | Default (proposed) | Tuned by |
|---|---|---|
| Club fans per win / promotion / title / Worlds win | small / medium / large / largest | fan-ledger receipt audit |
| Player followers per MVP / record / milestone / district tie | scaled by event weight | player-following audit |
| Stadium capacity by facility level (× tier) | base × level, tier-scaled | `fan_income_probe` |
| Matchday per-fan rate / merch rate per 1k fans | small $k | `fan_income_probe` (margin, never rivals prize money) |
| Facility upgrade costs (treasury) | by facility, like network L1/L2/L3 | economy-pressure probe |
| Training Hall dev effect | the revived `DevelopmentModifiers` multipliers | facility effect probe |
| Mentor dev bonus / Analyst targeting-read bonus | trait-scaled | role-consumer probes |
| Media event effect sizes | small fan/prestige/credibility deltas | media-isolation fence |

## Determinism & back-compat guards

- **Facility revival is an intentional development-outcome change.** Reviving the
  `()` → real read shifts per-stat deltas for any club that OWNS a facility
  (fresh saves own none → byte-identical). Re-derive + re-pin any development
  witness that owns facilities; update golden logs in the same pass.
- **Pyramid-gate every new income line + fan accrual.** `matchday_income_k` /
  `merch_income_k` return `0` on legacy / non-pyramid saves; `EconomyConfig`
  defaults keep the existing ledger byte-identical.
- **Append-only fan ledger** — every delta is a receipt row; never mutate a
  running total without a ledger entry (avoid the opaque single-scalar prestige
  pattern the spec explicitly rejects).
- **Idempotency guards are V26-specific** (`v26_fans_awarded_for`,
  `v26_media_done_for`) — never reuse `prestige_awarded_for`, `finances_applied_for`,
  or the offseason init guard. The cup/title `+6` grant lives OUTSIDE
  `_award_prestige_for_season` — the web port must hook cup wins for fans too.
- **`OFFSEASON_CEREMONY_BEATS` + active-beats + `_MAX_OFFSEASON_BEAT_INDEX` change
  together** (the V25 clamp-bug lesson): adding `media_event` bumps the canonical
  last index — update the persistence clamp literal + its guard test.
- **In-game `MomentKind` events are NOT persisted** (replay-only) — player
  followings must read `signature_moments` (awards) + records, not match-replay
  moments.
- **`season_id` is sorted via `_season_order`**, never lexically — fan-ledger
  grouping/ordering by season must use the numeric helper.
- **New `derive_seed` namespace** `v26_media` only; fan gains are pure functions
  of logged events (no new RNG stream).

## Proof obligations (vision § V26)

- **Fan-ledger receipt audit** — every fan change derivable from a logged event
  with a plain-language receipt.
- **Facility effect probes** — owning a facility measurably changes development.
- **Role consumer tests** — Mentor / Analyst / Ambassador each measurably matter;
  nothing flavor-only (the V19 dead-attribute lesson).
- **Fan-income margin invariant** — matchday + merch is a meaningful margin but
  never rivals prize money at any tier.
- **Media isolation fence** — media choices touch only fans/prestige/credibility,
  never match outcomes / standings / development.
- **Determinism preserved**; intentional development-outcome changes update golden
  logs.

## Out of scope (deferred per the era ledger)

The event calendar / cups / ruleset invitationals / Worlds crowning ceremony
(V27); emergent meta + journalism + officiating emphasis (V28). In-season
(weekly command-card) media events (offseason beat only in v1). Persisting
in-game `MomentKind` moments for player followings (a moment-persistence pass).
A morale engine (rejected on principle unless the game feels sterile post-V26).
AI club fan economies / AI facilities (user-program features; AI abstracted). No
NG+, no patch dials, no abstracted/fake results.
