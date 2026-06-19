# V28 — The Weather (Anti-Solvedness)

Date: 2026-06-17
Status: **Active spec.** Implementation authority for the V28 milestone (the
Climb-Era finale).
Era authority: `docs/specs/2026-06-12-climb-era-vision.md` (§ "V28 — The Weather").
Build-state truth remains `docs/STATUS.md`.

**Implementation status (2026-06-17, branch `feature/v24-the-board`):** not yet
started. V23–V27 precede it on this branch; the arc merges to `main` as a unit.

## Relation to Prior Specs

- **Generalizes the existing V12 adaptation** ("react to the player" →
  "react to the world"). Today `ai_program_manager.apply_adaptation_shift` nudges
  an AI club's intent only when it faces a dominant user (`user_win_rate ≥ 0.70`,
  rolling 8). V28 adds an ecosystem signal: AI programs drift toward the tactics
  actually WINNING across the league, computed from real match records — until a
  new generation breaks the orthodoxy. **Nothing injected.**
- **Uses persisted match telemetry** (`match_records`, `player_match_stats`, and
  the per-match `official_score_json.team_policies` written by `official_adapter`)
  as the raw material for both the meta drift and the journalism. No fake signals.
- **`meta.py` (MetaPatch / RuleSetOverrides) stays RETIRED.** It is the authored-
  seasonal-dial pattern the vision explicitly rejects. V28 computes the same kind
  of structural weather from observed data, never an injected patch. The
  `test_meta_module_has_no_db_boundary_imports` fence stays; no code wires
  MetaPatch.
- **Uses the existing officiating pipeline** (`rule_discretion.RuleDiscretionEvent`
  → `OfficialEvent(kind=DISCRETION)` → `collect_official_metadata`) for the
  officiating points of emphasis. No new event kind needed.
- **Uses the existing news pipeline** (`news_headlines` + `build_news_payload`)
  for the meta channel; widens the category filter (after V27's `event_news`).
- **Inherits** the integrity contract (`docs/specs/AGENTS.md`, ADR 0002): every
  journalism claim is derivable from real match data; the officiating emphasis is
  announced preseason, applied symmetrically, and logged; no hidden dials.

## The problem V28 solves

The world is alive but **solvable**: AI program archetypes are fixed at creation
and never drift, so a dominant strategy stays dominant forever; there is no
league-wide journalism reporting what the meta is doing (every trend is invisible
unless the player counts it themselves); and officiating is identical every
season, so the rulebook's discretion space is dead. V28 gives the ecosystem its
own weather — emergent, data-derived, and self-disrupting — so the game never
fully solves.

## Core design decisions (owner-confirmed)

### 1. Emergent meta = a data-derived per-club tactic-drift overlay + a contrarian generation (no injected dials)

Each offseason, a `meta_drift` pass computes which `CoachPolicy` dimensions
(approach, catch_posture, target_focus, rush_commit) **correlated with wins** in
the season's real official matches (`official_score_json.team_policies` vs
`winner_club_id`). AI clubs probabilistically drift their tactic tendencies toward
the winning dimensions — a **per-club tactic-tendency overlay** stored in
`dynasty_state` and consumed in `ai_tactics.get_ai_tactics` (the program_archetype
identity stays stable; the overlay is a learned bias on top). A **contrarian
fraction** of clubs each generation buck the orthodoxy (drift AWAY from the
dominant tactic), so a new generation breaks a solved meta — exactly as the vision
asks. The drift is fully derivable from match data; `MetaPatch` is not the
mechanism.

### 2. Officiating emphasis is a separate `SeasonEmphasis`, default-zero byte-identical, with NO new RNG draw (the determinism landmine)

A seasonal League Bulletin shifts call tendencies (catch-leniency / block-leniency)
within the rulebook's discretion space, announced preseason, applied
**symmetrically** (both sides pass through the same `resolve_throw` shift), and
**logged** as `RuleDiscretionEvent` (kind=DISCRETION, `selection_basis='emphasis_<season>'`).
Hard constraints: (a) the emphasis is a **`SeasonEmphasis` dataclass threaded as a
separate argument** into `run_autonomous_game` — NOT a field on the frozen
`RulesetProfile` (ruleset = sourced USAD fidelity; emphasis = sim-design weather,
cleanly separated); (b) the shift adjusts the EXISTING sigmoid bias constant
BEFORE the existing catch/block roll — it **must not add an RNG draw** inside
`resolve_throw`, or every golden witness shifts; (c) `SeasonEmphasis()` default
(all deltas 0.0) is **byte-identical to today**, so a no-bulletin season changes
nothing. The conformance ledger gains honest entries for the new discretion space.

### 3. Meta journalism = derivable-from-data trend reports on the news ticker

A `generate_league_bulletin` computes season/division trend lines that ARE
derivable from persisted data — catch rate (`catches_made/catches_attempted`),
elimination rate, game-point margins, and posture win-correlation (from
`team_policies` for official matches) — and writes `category='meta_report'` /
`'league_bulletin'` headlines, surfaced by widening `build_news_payload`'s filter.
Every claim cites the data. Moment-based claims (DramaticCatch frequency, etc.)
are replay-only / not persisted → a disclosed deferral (would need a
`match_moment_counts` table).

### 4. Pyramid-gated; post-summit stays legacy play

The whole layer is behind `pyramid_world_active`; legacy single-league saves are
byte-identical. Post-summit is legacy play (records, defense, HoF) — never NG+ or
a difficulty ratchet (the vision law).

## Data model

- **Tactic-drift overlay**: a per-club tendency map in `dynasty_state`
  (`v28_tactic_drift_json`: `{club_id: {dimension: bias}}`), recomputed each
  offseason from match telemetry. Zero migration.
- **Season emphasis**: the active bulletin in `dynasty_state`
  (`v28_season_emphasis_json`: `{catch_delta, block_delta, announcement}`),
  set preseason, read by the match runner. Zero migration.
- **Archetype-keyed journalism (optional):** archetype is not a native
  `player_match_stats` column; archetype trend lines need a JOIN through
  `match_roster_snapshots` JSON. If archetype trends prove valuable, a small
  additive `_migrate_v20` could add `player_archetype` to `player_match_stats` at
  write time — decided at planning; the catch-rate/elimination/posture trends need
  no migration.
- **New `derive_seed` namespaces**: `v28_meta_drift`, `v28_emphasis` (the
  contrarian draw + the preseason emphasis selection are deterministic).
- **New config** `WeatherConfig` (drift rate, contrarian fraction, emphasis delta
  bounds, trend thresholds) — all defaulting safe / zero so legacy is unchanged.

## Phased plan (each phase independently shippable + gated)

### Phase 1 — Meta journalism (trend reports on the ticker)
- `meta_journalism.py`: `compute_league_trends(conn, season_id)` (catch rate,
  elimination rate, game-point margin, posture win-correlation from
  `team_policies`, per division/tier — using `season_sort_key`, excluding playoff
  match-ids, using `fetch_season_player_stats` not the lossy `player_season_stats`)
  and `generate_league_bulletin(conn, season_id)` → `news_headlines` rows with
  `category='meta_report'`. Widen `build_news_payload`'s category filter to admit
  `meta_report` (additive after V27's `event_news`). Write at the offseason sweep.
- **Gate:** `tools/meta_journalism_probe.py` — every bulletin claim is derivable
  from the queried data (a derived-from-data fence: recompute the claim and assert
  it matches the headline); legacy/non-official matches excluded honestly; the
  ticker surfaces the report.

### Phase 2 — Emergent meta (ecosystem tactic drift)
- `meta_drift.py`: `winning_tactics(conn, season_id)` (which CoachPolicy
  dimensions correlated with wins, from `team_policies`); `apply_meta_drift(conn,
  season_id, root_seed)` (an offseason pass that nudges each AI club's
  `v28_tactic_drift_json` overlay toward the winners, with a deterministic
  contrarian fraction bucking the trend). Consume the overlay in
  `ai_tactics.get_ai_tactics` (a learned bias on the archetype base; precedence
  ordering audited so archetype/intent/drift don't collide).
- **Gate:** `tools/meta_drift_probe.py` — across simulated seasons, AI tactics
  measurably drift toward the prior season's winning dimensions (the ecosystem
  reacts to the world), AND a contrarian generation breaks a dominant tactic (no
  permanent solve); the drift is derivable from match data; user matches unchanged
  in determinism (the overlay only changes AI policy, real CoachPolicy, no special
  math).

### Phase 3 — Officiating points of emphasis (the engine-touching half)
- Add a `SeasonEmphasis` dataclass (`catch_delta`, `block_delta`, `announcement`);
  thread it as a separate arg into `run_autonomous_match`/`run_autonomous_game`
  (NOT the frozen profile); in `resolve_throw`/`decide_catch_attempt` shift the
  EXISTING `_CATCH_BIAS`/`_BLOCK_BIAS` by the bounded delta BEFORE the existing
  roll (NO new RNG draw) and emit a `RuleDiscretionEvent(selection_basis='emphasis_<season>')`
  on any sequence the delta changed. A preseason `generate_officiating_bulletin`
  picks the season's emphasis (`v28_emphasis` stream, within the discretion
  space), writes a `league_bulletin` headline + injects it into the season-preview
  payload, and persists `v28_season_emphasis_json`. Conformance ledger entries for
  the new discretion space.
- **Gate:** `tools/emphasis_probe.py` — **`SeasonEmphasis()` default is
  byte-identical to today** (the #1 fence — re-run a seeded season with no
  emphasis, assert identical to pre-V28 golden); an active emphasis shifts catch
  outcomes **symmetrically** (both sides equally) and is **logged** as DISCRETION
  events; no extra RNG draw (existing match witnesses unchanged at delta 0).

### Phase 4 — Frontend + verification + docs
- Surface the meta_report + officiating League Bulletin in the news ticker and the
  Week-1 season-preview orientation screen; `types.ts` + the news/preview
  components. (No new offseason beat unless the bulletin warrants one — prefer the
  existing ticker + preview surfaces to avoid another `_MAX_OFFSEASON_BEAT_INDEX`
  bump.)
- Full `python -m pytest -q` green (real exit code, no pipe); `npm run build` +
  `npm run lint` clean; the three probes pass; live prod-server walk (read a meta
  report, see a preseason officiating bulletin, observe AI tactics having drifted);
  docs (STATUS / MILESTONES) + retrospective + the Climb-Era arc close-out note.

## Disclosed constants (defaults; each ships with probe evidence)

All in `WeatherConfig`, never hardcoded. Proposed sim-design with measured
evidence, never claimed as real-world fidelity.

| Constant | Default (proposed) | Tuned by |
|---|---|---|
| Tactic-drift rate (per offseason) | small bias nudge | `meta_drift_probe` (drifts but doesn't snap) |
| Contrarian fraction | ~15–25% of clubs | `meta_drift_probe` (a generation breaks the meta) |
| Catch/block emphasis delta bounds | small, within discretion | `emphasis_probe` (shifts calls, not a rewrite) |
| Trend-report thresholds (what's "notable") | a minimum delta to report | `meta_journalism_probe` |

## Determinism & back-compat guards

- **No new RNG draw in `resolve_throw`** (the #1 landmine) — the emphasis shifts
  the existing bias constant before the existing roll; `SeasonEmphasis()` (default
  0.0) is **byte-identical** to pre-V28, so every official-match golden witness is
  unchanged on a no-bulletin season.
- **Emphasis is symmetric by construction** (both sides through the same
  `resolve_throw` shift) — the symmetry proof obligation is satisfied structurally.
- **Emphasis is SOURCED within the discretion space** — it shifts tendencies the
  rulebook leaves to discretion, never invents enforcement; logged as DISCRETION;
  the conformance ledger stays honest (ANNOUNCED vs ENFORCED).
- **Meta drift changes only AI `CoachPolicy`** (a real policy the engine already
  consumes — no special-cased AI math), so it is honest emergent behavior, not a
  hidden buff. The user's matches are unaffected in determinism.
- **`meta.py`/MetaPatch stays retired** (the fence test holds); V28 computes
  weather from data, never an injected dial.
- **Journalism is read-only** over persisted data; `season_id` ordering via
  `season_sort_key`; playoff match-ids excluded; non-official matches excluded
  honestly from posture trends.
- **Pyramid-gate everything**; new `derive_seed` namespaces only; the news-filter
  widening is additive.

## Proof obligations (vision § V28)

- **Journalism derived-from-data fences** — every bulletin claim recomputes to the
  headline from the queried match data; nothing injected.
- **Emphasis symmetry + logging gates** — an emphasis shifts both sides equally and
  every shifted call is a logged DISCRETION event; the no-emphasis season is
  byte-identical.
- **Emergent-drift gates** — AI tactics measurably react to the prior season's
  winners, and a contrarian generation breaks a dominant tactic (anti-solvedness).
- **Determinism preserved**; legacy byte-identical; `MetaPatch` un-revived.

## Out of scope (deferred per the era ledger)

`MetaPatch` stat-dials (retired by owner decision). Moment-based journalism
(DramaticCatch frequency — replay-only / not persisted; needs a
`match_moment_counts` table). Interactive press / one-way journalism only. A
morale engine. The Nations Cup analog. No NG+, no difficulty ratchet — post-summit
is legacy play. This milestone closes the Climb-Era arc (V23–V28); the whole arc
merges to `main` as a unit after V28.
