# V27 — The Calendar (Events)

Date: 2026-06-17
Status: **Active spec.** Implementation authority for the V27 milestone.
Era authority: `docs/specs/2026-06-12-climb-era-vision.md` (§ "V27 — The Calendar").
Build-state truth remains `docs/STATUS.md`.

**Implementation status (2026-06-17, branch `feature/v24-the-board`):** not yet
started. V23–V26 are complete on this branch; the Climb-Era arc merges to `main`
as a unit. Phases below are each independently shippable and gated.

## Relation to Prior Specs

- **Revives the dormant Cup system, modernized to current standards.** `cup.py`
  (the pure `CupBracket`/`CupRound`/`CupMatch`/`CupEntrant` model + the
  `cup_brackets`/`cup_results` tables) was built CLI-era and is wired ONLY in
  `dynasty_cli.py` — the web game is cup-blind. V27 wires it into the web path as
  the Domestic Cup (the facilities/prestige revival pattern from V26).
- **Builds on V26 — The Crowd.** The Founders' Exhibition is invited by FAN COUNT
  (`fan_ledger.club_fans`); event wins grant fans (`fan_economy`, `trophy_type='cup'`
  already pays `fans_cup`); event purses pay into the V22 treasury.
- **Builds on V23 — The World.** The Domestic Cup draws all three pyramid
  divisions; MSI invites the Premier + Circuit leaders; the Worlds crowning is the
  existing `pyramid_postseason` Worlds result, elevated to a ceremony.
- **Uses the existing engine ruleset infrastructure (no engine changes).** The
  cloth and no-sting `RulesetProfile`s run end-to-end through
  `OfficialEngineAdapter(RulesetSelection.OFFICIAL_CLOTH/_NO_STING)`. The V17
  full-run cloth crash (the `to_official_event` missing-`event_id` discretion bug)
  is **fixed** (`bb07fda`). Ruleset Invitationals are the ONLY home of non-foam
  rulesets; foam stays the league/cup/Worlds spine.
- **Inherits** the integrity contract (`docs/specs/AGENTS.md`, ADR 0002): every
  result is a real seeded engine match (no fake results), every purse/fan grant is
  receipted and idempotent, and — per the V17 precedent — **played content must be
  balanced content** (per-ruleset balance gates before any invitational ships).

## The problem V27 solves

The dynasty plays one competition: its division's league + the playoffs/Worlds.
There is no **cup** (no giant-killing across tiers), no home for the alternate
rulesets the engine fully supports (cloth/no-sting are unreachable in normal
play), no midseason or preseason occasion, and the first Worlds title — the
save's intended crowning moment — renders as a one-line recap bullet, not a
ceremony. V27 gives the season a calendar of events, each a real competition with
a trophy, a purse, fans, and journalism.

## Core design decisions (owner-confirmed)

### 1. Events resolve as deterministic auto-simmed knockouts at dedicated
windows — NOT an in-season weekly-schedule rebuild

The vision frames events as "dedicated calendar breaks." Rebuilding the in-season
weekly schedule is the single highest-risk change in the engine (the postseason
week-offset arithmetic, the alphabetical division-sort determinism, the duplicate
`advance_playoffs_if_needed` implementations). **Decision: each event runs as a
deterministic, fully-real auto-simmed knockout** (the real engine, seeded, no fake
results) resolved at its thematic window and surfaced as a result display +
ceremony + trophy + purse + fans + news. The Domestic Cup runs alongside the
league and is presented at season's end; the Founders' Exhibition is a preseason
event; MSI a midseason event; the invitationals their own occasions. **The user's
INTERACTIVE participation in event matches is a disclosed deferral** — the auto-sim
uses the real engine and produces real, watchable results; "play your own cup run"
is a refinement, not v1. This delivers all the event content without the
schedule-surgery risk.

### 2. Per-ruleset balance gates ship BEFORE the invitationals (the V17 precedent)

Before any cloth/no-sting invitational is schedulable, the cloth and no-sting
engines must pass archetype-parity + decision-impact/health probes equivalent to
the foam gates (the V17 retro's "played content must be balanced content" law). A
dedicated phase runs those probes and fixes any imbalance; only then do the
invitationals ship.

### 3. Events are user-facing, pyramid-gated; purses + fans are idempotent

All events are pyramid-world features (legacy single-league saves are
byte-identical — no events). Purses pay the user treasury via an idempotent
`apply_event_purse` (the `FINANCES_APPLIED_KEY` guard pattern — `set_treasury_k`
has no guard of its own). Fan grants reuse the V26 append-only ledger with their
own per-event guards. Event journalism reuses `news_headlines`; `build_news_payload`
widens its `class_wire`-only filter to include `event_news`.

### 4. The Worlds crowning is a new offseason ceremony beat

The first Worlds title is the save's crowning beat (credits-roll energy); later
titles a (smaller) defending-champion beat. A new conditional `worlds_champion`
offseason beat reads the existing `pyramid_postseason` ledger /
`worlds_history_json` (first-ever crown ⇒ the elevated treatment).

## Data model

- **Cup** reuses the existing `cup_brackets` / `cup_results` tables (no migration);
  a `cup_type` discriminator in the `cup_id` (`{season_id}_domestic_cup`) supports
  the Domestic Cup distinct from the legacy midseason cup.
- **Event results + purses + qualification** ride `dynasty_state` JSON
  (`v27_events_json` per season: each event's bracket result, champion, purse,
  participants) — **no schema migration** (the V26 `_migrate_v19` stays the latest).
- **Idempotency guards** (`dynasty_state`): `v27_<event>_resolved_for`,
  `v27_<event>_purse_for`, `v27_<event>_fans_for` — never reuse `finances_applied_for`.
- **New `derive_seed` namespaces**: `v27_cup`, `v27_msi`, `v27_founders`,
  `v27_invitational` (event draws/sims are deterministic).
- **New config** `EventConfig` (purses, invite counts, fame/fan thresholds, the
  prospect-showcase warmth) — all defaulting safe for legacy.

## Phased plan (each phase independently shippable + gated)

### Phase 1 — Event foundation (purses + journalism + the events beat)
- `events.py`: the event-result model + `apply_event_purse(conn, event_key, purse_k, season_id)` (idempotent treasury credit) + an event-news helper. Widen `build_news_payload`'s category filter to include `event_news`.
- A new conditional `events` offseason beat (scaffold) that presents the season's resolved events; cache the events state at offseason init (pyramid+user). Bump `_MAX_OFFSEASON_BEAT_INDEX` + guard test + the pinned beat-tuple witness (the V25/V26 clamp lesson).
- **Gate:** purse idempotency fence; news-filter widening; legacy byte-identical (no events beat); the clamp guard.

### Phase 2 — Domestic Cup (revive `cup.py` in the web path)
- A `cup_service.py` (the web home for the DB-touching cup logic — `cup.py` stays import-pure per `test_cup_module_has_no_db_boundary_imports`): generate the cross-division 28-club foam knockout at season start (`generate_cup_bracket` over all division clubs, `derive_seed(root_seed, 'v27_cup', season_id)`); auto-sim the bracket to a champion through the real foam engine (the CLI `_simulate_next_cup_round` is the reference); award the cup trophy + `fans_cup` + a purse + a news line (the giant-killing headlines). Surface in the events beat + a cup bracket display.
- **Gate:** `tools/cup_probe.py` (every cup completes a valid champion; lower-tier giant-killings occur; determinism); trophy/fans/purse idempotency; foam-only.

### Phase 3 — Ruleset balance gates (the V17 precedent)
- `tools/ruleset_balance_probe.py`: archetype-parity + decision-impact/health probes for cloth and no-sting (the foam-gate equivalents). Record BEFORE/AFTER; fix any imbalance found. Pin permanent gates (`test_v27_ruleset_balance`).
- **Gate:** cloth + no-sting pass the parity/health bars; no full-run crash across many seeded matches (the V17 precedent regression).

### Phase 4 — Ruleset Invitationals (Cloth Classic / No-Sting Open)
- An invitational event running an auto-simmed knockout under a non-foam ruleset (`OfficialEngineAdapter(RulesetSelection.OFFICIAL_CLOTH/_NO_STING)`); invitation by fame (prestige) + standing; a purse + prospect-showcase warmth (a small recruiting/fan bump). Match-ids encode the round so the engine clock is right (the trap).
- **Gate:** invitational runs cloth + no-sting to a valid champion (real engine); invite criteria fence; foam league untouched; the balance gates from Phase 3 are a prerequisite.

### Phase 5 — Midseason International + Founders' Exhibition
- **MSI**: Premier + Circuit leaders (`load_standings` ∩ `load_division_map` by `division_id`, not tier) in a small knockout; prestige + purse + a Worlds-seeding note.
- **Founders' Exhibition**: a preseason invitational by FAN COUNT (`fan_ledger.club_fans` top-N), money-only, declared no-seeding — being beloved is the ticket.
- **Gate:** MSI invites exactly the two division leaders; Founders' invites by fan rank; purses idempotent.

### Phase 6 — Worlds crowning ceremony
- A conditional `worlds_champion` offseason beat (after the recap), reading the postseason ledger / `worlds_history_json`: the **first-ever** crown gets the elevated credits-roll treatment (`CeremonyShell` staged reveal), later crowns a defending-champion beat. Post-summit is legacy play (no NG+ / difficulty ratchet — the vision law).
- **Gate:** the beat appears only for the Worlds champion; first-win vs defending distinction; determinism.

### Phase 7 — Frontend + verification + docs
- The events beat UI (event cards + results), cup/invitational bracket displays (extend/clone `PlayoffBracket`), the Worlds crowning ceremony component; `types.ts`, `Offseason.tsx` wiring, `apiPost` endpoints.
- Full `python -m pytest -q` green (real exit code, no pipe); `npm run build` + `npm run lint` clean; live prod-server walk (a season's events + a Worlds crowning); docs (STATUS / MILESTONES) + retrospective.

## Disclosed constants (defaults; each ships with probe evidence)

All in the config layer (`EventConfig`), never hardcoded. Constants are proposed
sim-design with measured evidence, never claimed as real-world fidelity.

| Constant | Default (proposed) | Tuned by |
|---|---|---|
| Domestic Cup purse (champion / runs) | tier-scaled, modest vs league payout | `cup_probe` + finances margin |
| Invitational purse + prospect-showcase warmth | modest | invite/finance fence |
| MSI / Founders' purse | modest | finance fence |
| Founders' invite count (top-N by fans) | 4–6 | fan-rank fence |
| Ruleset-invitational fame threshold | prestige + standing rank | invite fence |
| Event fan grants | reuse V26 `fans_cup` / event-scaled | fan-ledger audit |

## Determinism & back-compat guards

- **`cup.py` stays import-pure** (`test_cup_module_has_no_db_boundary_imports`) —
  all DB/sim wiring lives in the new `cup_service.py`.
- **No in-season schedule changes** (decision 1) — the postseason offset
  arithmetic + division-sort determinism are untouched; existing match/standings
  witnesses are byte-identical.
- **Pyramid-gate every event** — legacy single-league saves have no events, no
  event beat, no purses; byte-identical.
- **Purses are idempotent** (`apply_event_purse` guard) — `set_treasury_k` has no
  guard; a double-call must never double-pay.
- **`OFFSEASON_CEREMONY_BEATS` + active-beats + `_MAX_OFFSEASON_BEAT_INDEX` change
  together** (the V25/V26 clamp lesson) for the new `events` + `worlds_champion`
  beats; update the pinned beat-tuple witness.
- **Event match-ids encode round type** so the engine clock resolves correctly
  (the cloth/foam clock trap); never call `decide_cloth_game_by_active_count` on a
  foam match.
- **New `derive_seed` namespaces only**; events are deterministic per seed.
- **News filter** widening is additive (the `class_wire` path still works).

## Proof obligations (vision § V27)

- **Calendar integrity gates** — every event completes a valid champion from the
  right field; the season's events resolve deterministically.
- **Declared-stakes honesty fences** — Founders' is declared no-seeding (money
  only); every purse/fan/prestige grant is receipted and idempotent.
- **Per-ruleset balance gates** — cloth + no-sting pass parity/health before any
  invitational ships (the V17 precedent), and no full-run crash recurs.
- **Determinism preserved**; legacy byte-identical.

## Out of scope (deferred per the era ledger)

Emergent meta + journalism + officiating emphasis (V28). In-season weekly-schedule
integration of events + the user's interactive participation in event matches
(auto-sim is real-engine v1). The Nations Cup analog (needs player nationality).
A pick/ban draft phase (rejected). No NG+, no patch dials, no abstracted/fake
results. Post-summit stays legacy play, never a difficulty ratchet.
