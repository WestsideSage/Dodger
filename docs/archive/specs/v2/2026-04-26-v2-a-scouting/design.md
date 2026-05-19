# V2-A — Stateful Scouting Model — Design Spec

**Date:** 2026-04-26
**Status:** Design approved, ready for implementation planning
**Scope:** Convert scouting from a stateless one-shot helper into a persistent multi-week loop with named scouts, tiered confidence narrowing across four hidden axes, an off-season Draft Day moment-of-truth that reveals trajectory and scout accuracy, and a Scouting Center surface inside Manager Mode.

---

## 0. Relation to Prior Specs

This document is the canonical V2-A spec. It refines and supersedes the following sections of `docs/specs/2026-04-26-manager-mode/design.md`:

- §2.5.5 (Scouting model engine dependency) — the deferred "v2 target system" lands here.
- §5.3 (Profile in fuzzy mode) — fuzzy Profile mode ships as part of V2-A.
- §10 (Section 8 — Scouting Center) — the full v2 target vision is realized here, with refinements based on brainstorming (CEILING label, manual/auto toggle, scout track records).
- §11.3, §11.4, §14 — the V2-G row (UncertaintyBar component + fuzzy Profile mode) is collapsed into V2-A because the Scouting Center cannot render honestly without it.
- §12.2 — the Scouting tab activates between Tactics and League under V2-A.

Inherits:

- Integrity contract from `docs/specs/AGENTS.md`.
- V1 closeout state from `docs/retrospectives/2026-04-26-manager-mode-handoff.md` — including all M0 deliverables (Club color/venue/tagline extension, Lineup persistence + `LineupResolver`, Win-probability analyzer, Match-MVP function, Career state machine, schema v7).
- V1 implementation learnings from `docs/learnings/2026-04-26-manager-mode-implementation-learnings.md`.

V2-A explicitly does NOT cover:

- AI club competition / sniping / public-vs-private information asymmetry on signing → **V2-B**.
- Build a Club expansion path → **V2-C**.
- Expanded `CoachPolicy` tendencies → **V2-D**.
- Records Ratified / HoF Induction / Rookie Class Preview off-season beats → **V2-E**.
- Playoffs in `scheduler.py` → **V2-F**.
- Scout aging / retirement / hire / fire flows — deferred to a later milestone.
- Multi-scout-on-same-prospect overlapping reports — V3 polish.
- Per-trait scouting axes (we use one `traits_axis` with traits revealed in waves at tier-up moments).
- Mid-season free-agent signings — V3+.

---

## 1. Goals

1. **A real mid-season scouting loop.** Between matches, the user assigns scouts to prospects. Confidence narrows over weeks. By off-season, the user's private view of the prospect class is meaningfully different from the public view.
2. **Named scouts with legible specialties.** Three persistent scouts with distinct strengths and weaknesses. Each assignment is a real decision.
3. **Manual or delegated.** Per-scout MANUAL/AUTO toggle. Manual is the deep loop; Auto delegates the click work without removing the dynasty payoff.
4. **Honest uncertainty.** Tiered narrowing (Unknown → Glimpsed → Known → Verified) rendered via an `UncertaintyBar` component. The UI never pretends to know more than it does.
5. **Earned reveals.** Trajectory (the dev-trait axis: Normal / Impact / Star / Generational) is gated to the off-season Draft beat. CEILING labels (HIGH CEILING / SOLID / STANDARD) surface at full ratings scouting as the mid-stream payoff.
6. **Scouts as dynasty entities.** Per-scout track records persist across seasons. Scouts who consistently hit become trusted; scouts who consistently miss become known liabilities.
7. **Integrity contract intact.** Every displayed value derives from an engine source. Scouting writes do not influence match resolution. `development.py` honors the trajectory axis so scouting cannot lie about ceilings.

### Non-goals (V2-A only)

See §0 above for the deferred list.

---

## 2. Design Contracts

In addition to the inherited contracts from `docs/specs/AGENTS.md` and the V1 design:

- **Scouting state never influences match resolution.** Phase 1 golden regression must remain unchanged after V2-A lands. Match RNG seed namespaces are disjoint from scouting RNG seed namespaces.
- **Trajectory must be honored by `development.py`.** If a prospect is scouted as Generational, their post-signing development curve must measurably reflect that. This is the integrity-critical engine wire-up.
- **Tier display rules are a spec contract, not implementation detail.** Each tier shows a documented information set (band width, archetype confidence, traits visibility, trajectory visibility). UI cannot display tighter information than the tier authorizes.
- **Trajectory never reveals mid-season.** Even if a prospect's `trajectory_axis` reaches VERIFIED in Week 8, the trajectory value stays hidden until the off-season Draft beat. Internal tier value tracks; UI keeps it gated.
- **CEILING label, once revealed, persists.** Carry-forward decay reduces ratings/archetype/traits tiers but does not unreveal CEILING. You don't unlearn a ceiling read.
- **Auto-Scout strategies are deterministic given seed + state.** Replaying a season produces identical Auto-scout assignments.
- **One Player Profile component, four states.** Prospect (fuzzy via UncertaintyBar) → signed (crisp) → veteran (crisp + history) → HoF (crisp + retirement framing). V2-A delivers the prospect-fuzzy state.

---

## 3. Architecture

### 3.1 Module layout

**New module: `scouting_center.py`**
Owns the stateful scouting model — scout entities, assignments, per-prospect confidence per axis, tier transitions, scouting reports, accuracy track records. The single source of truth for scouting state.

**Deprecated (kept for backwards compatibility): `scouting.py`**
Existing stateless `generate_scout_report(player, budget_level, rng)` is no longer called by the manager flow. Module-level docstring marked deprecated; function preserved so any external callers (e.g. `dynasty_cli.py` or test fixtures) still resolve. Not removed in this milestone.

**Extended: `recruitment.py`**
- `generate_rookie_class()` gains a `class_year: int` argument.
- Generation now writes hidden true ratings + hidden trajectory trait + hidden traits + a wide public baseline (archetype guess, OVR baseline band, no trait/trajectory hints) to a new persisted `prospect_pool` table at season start, not at off-season.
- The off-season Draft beat reads from `prospect_pool` rather than calling `generate_rookie_class()` itself.

**Extended: `development.py`**
- `apply_season_development()` gains a `trajectory: Trajectory | None` parameter (None for legacy non-prospect-pool players).
- Growth curve is modulated by trajectory: Normal < Impact < Star < Generational in cumulative OVR delta over a typical career arc.
- This is the **integrity-critical wire-up**: if scouting says "Generational" and development never produces a Generational career, scouting is lying.

**Extended: `manager_gui.py`**
- New top-level **Scouting** tab (between Tactics and League).
- Off-season Draft beat extended to render scouting tier displays per rookie, run the trajectory reveal sweep, and render the post-Draft Accuracy Reckoning panel.
- Hub Spotlight gains the HIDDEN GEM rotation.
- Reminder strip gains scouting alerts.
- Player Profile gains fuzzy mode for prospects.

**Extended: `ui_components.py`**
- New shared component: `UncertaintyBar` (filled bar with center dot + halo width tied to tier).

**Extended: `career_state.py`**
- No new states or transitions. Existing `season_active_pre_match` is when Scouting Center is reachable. Existing `season_complete_offseason_beat[draft]` is where the moment-of-truth lands.
- Scouting tick fires on the existing match-week-advance hook (the V1 transition `season_active_match_report_pending → season_active_pre_match`).

**Extended: `persistence.py`**
- Schema migration v7 → v8 adds new tables (no existing tables change shape).
- Scouts seeded on first week-tick after load if `scouts_seeded_for_career` flag is unset (idempotent — same pattern as V1 `offseason_initialized_for`). Flag stored via existing `dynasty_state` key/value API; no new flags table is introduced.

### 3.2 Schema v8 — new tables

```
prospect_pool(
    class_year INT,
    player_id TEXT,
    hidden_ratings_json TEXT,           -- POW/ACC/DOD/CAT/AWR/STM exact values
    hidden_trajectory TEXT,             -- NORMAL | IMPACT | STAR | GENERATIONAL
    hidden_traits_json TEXT,            -- list of true trait identifiers
    public_archetype_guess TEXT,
    public_ratings_band_json TEXT,      -- ±25 around true OVR baseline
    is_signed INT,                      -- 0 = available, 1 = signed (carryover bookkeeping)
    PRIMARY KEY (class_year, player_id)
)

scouting_state(
    player_id TEXT,
    axis TEXT,                          -- ratings | archetype | traits | trajectory
    tier TEXT,                          -- UNKNOWN | GLIMPSED | KNOWN | VERIFIED
    scout_points INT,
    last_updated_week INT,
    PRIMARY KEY (player_id, axis)
)

scouting_revealed_traits(
    player_id TEXT,
    trait_id TEXT,
    revealed_at_week INT,
    PRIMARY KEY (player_id, trait_id)
)

scouting_ceiling_label(
    player_id TEXT PRIMARY KEY,
    label TEXT,                         -- HIGH_CEILING | SOLID | STANDARD
    revealed_at_week INT,
    revealed_by_scout_id TEXT
)

scout(
    scout_id TEXT PRIMARY KEY,
    name TEXT,
    base_accuracy REAL,                 -- e.g. 0.7
    archetype_affinities_json TEXT,     -- list of archetype ids
    archetype_weakness TEXT,
    trait_sense TEXT                    -- LOW | MEDIUM | HIGH
)

scout_assignment(
    scout_id TEXT PRIMARY KEY,
    player_id TEXT,                     -- nullable when idle
    started_week INT
)

scout_strategy(
    scout_id TEXT PRIMARY KEY,
    mode TEXT,                          -- MANUAL | AUTO
    priority TEXT,                      -- TOP_PUBLIC_OVR | SPECIALTY_FIT | USER_PINNED
    archetype_filter_json TEXT,
    pinned_prospects_json TEXT          -- USER_PINNED only; data-model present, UI disabled in V2-A
)

scout_prospect_contribution(
    scout_id TEXT,
    player_id TEXT,
    season INT,
    first_assigned_week INT,
    last_active_week INT,
    weeks_worked INT,
    contributed_scout_points_json TEXT,    -- {ratings: N, archetype: N, traits: N, trajectory: N}
    last_estimated_ratings_band_json TEXT, -- frozen snapshot of this scout's view at last_active_week
    last_estimated_archetype TEXT,
    last_estimated_traits_json TEXT,
    last_estimated_ceiling TEXT,
    last_estimated_trajectory TEXT,        -- nullable until trajectory_axis VERIFIED via this scout's contribution
    PRIMARY KEY (scout_id, player_id, season)
)
-- Source-of-truth for per-scout-per-prospect history. Written/updated on every week-tick where this
-- scout actively works this prospect. When a scout is reassigned, the row remains; if reassigned later
-- to the same prospect in the same season, the row is updated (last_active_week + weeks_worked accrue).
-- Cross-season: each season gets its own row (so track records can compare year-over-year).

scout_track_record(
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scout_id TEXT,
    player_id TEXT,
    season INT,
    predicted_ovr_band_json TEXT,
    actual_ovr INT,
    predicted_archetype TEXT,
    actual_archetype TEXT,
    predicted_trajectory TEXT,          -- nullable if scout did not reach trajectory VERIFIED
    actual_trajectory TEXT,
    predicted_ceiling TEXT,             -- nullable if CEILING not revealed
    actual_ceiling TEXT
)
-- Written at off-season Draft beat by reading scout_prospect_contribution and joining against
-- prospect_pool's hidden_* truths. Append-only.

scouting_domain_event(
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INT,
    week INT,
    event_type TEXT,                    -- TIER_UP_RATINGS | TIER_UP_ARCHETYPE | TIER_UP_TRAITS | TIER_UP_TRAJECTORY | TRAIT_REVEALED | CEILING_REVEALED | TRAJECTORY_REVEALED
    player_id TEXT,
    scout_id TEXT,                      -- the scout whose week-tick fired the event (nullable for season-transition decay events)
    payload_json TEXT                   -- event-specific data (which trait, which tier, etc.)
)
-- Persisted ScoutingDomainEvent log. Drives the Reveal Ticker UI, the Hub Spotlight HIDDEN GEM
-- trigger, and (with scout_prospect_contribution) is the audit trail for the season's scouting work.
-- Cleared on a per-season basis by the Reveal Ticker UI default; persisted across seasons for
-- replay/audit needs.
```

**Idempotency flags** (e.g. `scouts_seeded_for_career`) reuse the existing `dynasty_state` key/value store via the V1 `get_state` / `set_state` API. **No new flags table is introduced** — V1's pattern is the canonical home for career-scoped boolean flags. This avoids split-brain state storage.

**Player ID identity contract** (cross-table invariant): **prospect `player_id` values are globally unique for the lifetime of a save**. Generated once at prospect creation in `prospect_pool` and never reused. `class_year` is metadata on `prospect_pool` rows, not part of identity. All downstream tables (`scouting_state`, `scouting_revealed_traits`, `scouting_ceiling_label`, `scout_assignment`, `scout_prospect_contribution`, `scout_track_record`, `scouting_domain_event`) key on `player_id` alone, which is safe because IDs never collide across classes. Carry-forward across seasons preserves `player_id`, so scouting state on unsigned-rolled-forward prospects naturally stays bound to the same rows.

---

## 4. Engine Model

### 4.1 Scout entity

Three scouts are seeded at career creation. Static for V2-A — no aging, retirement, hiring.

```
Scout {
  scout_id: str
  name: str                           e.g. "Vera Khan"
  base_accuracy: float                ~1.0 typical (range ~0.85–1.15); multiplier applied per scouting week
  archetype_affinities: [str]         e.g. ["power_arm"]   — affinity multiplier 1.20 on these
  archetype_weakness: str             e.g. "dodger"        — weakness multiplier 0.80 on this
  trait_sense: enum                   LOW | MEDIUM | HIGH  — multiplier on traits_axis & trajectory_axis only
}
```

**Seeded scout profiles** (concrete picks land in implementation; design contract is that they are *legibly different* and the UI surfaces specialties plainly):

- **Vera Khan** — fast (high base_accuracy), power-arm specialist, weak on dodgers, trait_sense MEDIUM.
- **Bram Tessen** — slow (lower base_accuracy) but trait_sense HIGH; catch-archetype specialist; weak on awareness.
- **Linnea Voss** — balanced; awareness/dodger affinities; weak on power-arm; trait_sense LOW.

The HIGH trait_sense on Bram is what gives him the **early CEILING reveal** capability (see §4.5). That's the asymmetry that makes choosing which scout to point at which prospect a real decision.

### 4.2 Prospect pool

Generated at season start (Week 1 advance) for the current class_year. Each prospect carries hidden truths plus a public baseline.

```
Prospect {
  player_id: str                      (unsigned, lives in prospect_pool)
  class_year: int
  hidden_true_ratings: dict           POW/ACC/DOD/CAT/AWR/STM exact values
  hidden_trajectory: enum             NORMAL | IMPACT | STAR | GENERATIONAL
  hidden_traits: [str]                IRONWALL, CLUTCH, etc. — true trait identifiers
  public_archetype_guess: str         may be wrong (~15% mislabel rate, tunable in config)
  public_ratings_band: dict           ±25 around true OVR baseline (very wide)
  public_trait_hints: []              always empty — traits are private-only
  public_trajectory_hint: null        always null — trajectory is private-only
}
```

**Trajectory generation distribution** (tunable in `config.py`):

| Trajectory   | Rate | Notes |
|--------------|------|-------|
| NORMAL       | 70%  | Most common; baseline growth curve |
| IMPACT       | 22%  | Reliable contributor projection |
| STAR         | 7%   | High-end starter projection |
| GENERATIONAL | 1%   | Rare, league-defining ceiling |

**Class size:** ~25 prospects per class. Tunable.

**Throughput target (informs class size and tier-threshold tuning):** "deep scouting depth" is defined as **reaching KNOWN tier on `ratings_axis`** (band ±6, archetype confirmed, ~2 traits surfaced) — *not* VERIFIED. KNOWN is the productive working depth most prospects are scouted to; VERIFIED is reserved for top priorities (and is what unlocks the CEILING label for non-HIGH-trait-sense scouts, plus Draft-Day trajectory reveal eligibility).

With baseline numbers (5 scout-points/week neutral, KNOWN cumulative threshold 35, VERIFIED 70):

- One scout, neutral fit: KNOWN in ~7 weeks, VERIFIED in ~14 weeks (full season).
- Per-scout per-season throughput: ~2 prospects to KNOWN OR ~1 to VERIFIED.
- Three scouts × full season: **~6 prospects to KNOWN, ~3 to VERIFIED, or a mix** (e.g. 2 VERIFIED + 2 KNOWN).
- With affinity multipliers (1.20×) on specialty fits, slightly higher.

This is the **forced prioritization that is the gameplay**: out of ~25 prospects in the class, you're working ~6 of them in any depth and only a handful to VERIFIED. The rest stay at UNKNOWN with public baseline only.

**Public baseline mislabel rates:** ~15% of prospects ship with a wrong `public_archetype_guess` so scouting can correct misimpressions. Tunable.

### 4.3 Scouting state — the four axes

For each prospect with any scouting touch, four parallel axes carry their own tier:

```
ScoutingState(player_id) {
  ratings_axis:    Tier         UNKNOWN | GLIMPSED | KNOWN | VERIFIED
  archetype_axis:  Tier         (same scale)
  traits_axis:     Tier         (same scale)
  trajectory_axis: Tier         (same scale; UI never reveals this mid-season)
  scout_points: dict[axis, int] (accumulated; thresholds determine current tier)
}
```

### 4.4 Tier display rules (UI contract)

| Tier       | Ratings shown    | Archetype           | Traits                                                | Trajectory                |
|------------|------------------|---------------------|-------------------------------------------------------|---------------------------|
| UNKNOWN    | wide public band | public guess        | none                                                  | hidden                    |
| GLIMPSED   | ±15 band         | public guess        | up to 1 trait revealed (deterministic pick from true traits if any exist; row is empty if prospect has no true traits) | hidden  |
| KNOWN      | ±6 band          | confirmed/corrected | up to 2 traits revealed                               | hidden                    |
| VERIFIED   | exact value      | confirmed           | all true traits surfaced                              | **eligible for Draft-beat reveal**; UI still gates display until that beat |

**Tier thresholds** are concrete `int` cutoffs (scout-points required) defined in `config.py`. Same pattern as existing balance config. Crossing a threshold ticks the tier up at the week-advance hook.

Starting numbers (tunable):

- UNKNOWN → GLIMPSED: 10 scout points
- GLIMPSED → KNOWN: 25 scout points (cumulative 35)
- KNOWN → VERIFIED: 35 scout points (cumulative 70)

A typical 1.0-baseline scout against a no-modifier prospect generates ~5 scout points per week. So full-VERIFY against a neutral target takes ~14 weeks (a full season) of unbroken work — affordable for ~3 deeply-scouted prospects per scout-season under Manual.

### 4.5 CEILING label — the moment-of-truth payoff at full ratings

At `ratings_axis = VERIFIED`, a CEILING label is computed from the hidden trajectory and surfaced on the prospect:

| Label          | Trajectories                           | Approx. rate |
|----------------|----------------------------------------|--------------|
| HIGH CEILING   | trajectory ∈ {STAR, GENERATIONAL}      | ~8%          |
| SOLID          | trajectory = IMPACT                    | ~22%         |
| STANDARD       | trajectory = NORMAL                    | ~70%         |

The label tells the user the *band* of trajectories. SOLID and STANDARD have a 1:1 mapping to IMPACT and NORMAL respectively, so for those prospects the trajectory is fully known once CEILING reveals. **The genuine Draft-Day surprise is reserved for HIGH CEILING prospects, which split into STAR (~7/8 of the HIGH CEILING population) or the rare GENERATIONAL (~1/8).**

Interaction with `trajectory_axis`:

- A prospect with **HIGH CEILING + `trajectory_axis = VERIFIED`** gets a punctuated STAR-or-GENERATIONAL reveal at the Draft beat.
- A prospect with **HIGH CEILING + `trajectory_axis < VERIFIED`** stays ambiguous — you know they're high-ceiling but never learn whether it's STAR or GENERATIONAL until their post-signing development arc plays out across multiple seasons. That's a legitimate strategic gap, not a bug.
- A prospect with **no CEILING revealed but `trajectory_axis = VERIFIED`** (e.g. a HIGH-trait-sense scout pushed the trajectory axis hard without enough ratings work) — Draft Day still reveals the exact trajectory, so you learn it then.
- Prospects with neither — Draft Day shows `Trajectory: ?`.

**Trait-sense HIGH scouts surface CEILING one tier earlier — at `ratings_axis = KNOWN` instead of VERIFIED.** This is the V2-A analog of CFB 26's "Mind Reader" ability — not a probabilistic instant-reveal (which would be hard to test deterministically) but a scout-driven *acceleration*. Trait-sense MEDIUM and LOW scouts get CEILING only at VERIFIED.

CEILING, once revealed, persists across carry-forward decay (see §7).

### 4.6 Narrowing rule per scouting week

When a scout has an active assignment, every week-advance hook fires the narrowing rule **per axis**. The same scouting week credits points to all four axes simultaneously, but the per-axis modifier differs (trait_sense applies only to two of the four):

```
scout_points_gained_for_axis =
  base_accuracy             (~1.0 typical)
  × archetype_modifier      (1.20 affinity match, 0.80 weakness, 1.00 otherwise)
  × axis_modifier           (1.00 for ratings_axis & archetype_axis;
                             trait_sense for traits_axis & trajectory_axis:
                             LOW=0.70, MEDIUM=1.00, HIGH=1.30)
  × random_jitter           (uniform in [0.90, 1.10], deterministic via derive_seed)
  × WEEKLY_SCOUT_POINT_BASE (config constant, e.g. 5)
```

Result is rounded to the nearest integer and added to that axis's `scout_points`. A 1.0-baseline scout against a no-modifier prospect produces ~5 points/axis/week; cumulative thresholds (10 / 35 / 70) reach VERIFIED in ~14 weeks of unbroken work — affordable for ~3 deeply-scouted prospects per scout-season under Manual mode. Affinity (1.20×) shaves about 2–3 weeks off VERIFY; weakness (0.80×) adds 3–4. HIGH trait_sense reaches trait/trajectory VERIFIED noticeably faster than ratings VERIFIED on the same prospect.

Tier-up checks fire after points are added (per axis).

**Deterministic seed:** `derive_seed(root, "scouting", scout_id, player_id, week)` — single seed used to derive jitter for all four axes that week, guaranteeing re-running a season produces identical scouting output.

### 4.7 Auto-Scout strategy

Each scout has an independently-toggled mode:

```
ScoutStrategy {
  mode: MANUAL | AUTO
  priority: TOP_PUBLIC_OVR | SPECIALTY_FIT | USER_PINNED
  archetype_filter: [str]   optional whitelist
  pinned_prospects: [player_id]   USER_PINNED only — data model present, UI disabled in V2-A
}
```

**Two strategies ship in V2-A:**

- **TOP_PUBLIC_OVR** — pick the unscouted-or-lowest-tier prospect with the highest public OVR baseline midpoint, restricted to `archetype_filter` if set.
- **SPECIALTY_FIT** — same as above, but restricted to prospects whose `public_archetype_guess` matches the scout's `archetype_affinities`.

USER_PINNED is wired in the schema but the UI is disabled in V2-A. Re-enabled in V2-B (where it becomes the primary mechanism for protecting target prospects against AI sniping).

**Auto-Scout pick logic** (runs at week-tick before scouting points are advanced):

1. If scout has a current assignment whose target hasn't VERIFIED on all axes → keep working it.
2. Else, pick a new target this same week per the strategy:
   - Restrict pool to prospects where no other scout is currently assigned (the no-overlap default).
   - Apply strategy filter.
   - Tie-break deterministically by `derive_seed(root, "auto_scout_pick", scout_id, week)`.
3. If no eligible target, scout sits idle for the week.

**Mode toggle behavior:**
- MANUAL → AUTO: existing assignment (if any) becomes the Auto scout's first managed target; future picks follow strategy.
- AUTO → MANUAL: existing assignment converts to a MANUAL standing assignment. User can reassign next week-tick.

### 4.8 Track record entry

At off-season Draft Day, for every prospect any scout worked on this season, a `scout_track_record` row is written:

```
TrackRecordEntry {
  scout_id, player_id, season,
  predicted_ovr_band, actual_ovr,
  predicted_archetype, actual_archetype,
  predicted_trajectory   (nullable if scout did not reach trajectory VERIFIED),
  actual_trajectory,
  predicted_ceiling      (nullable if CEILING not revealed),
  actual_ceiling
}
```

Aggregated to per-scout accuracy stats for the UI ("Vera: power-arm hit rate 7/9 over 3 seasons"). Track record rows append-only; aggregates rebuild from row history.

---

## 5. Data Flow

Three transition points wire through V1's existing career state machine. **No new states, no new transitions.**

### 5.1 At career start (one-time)

Triggered on the V1 transition `splash → season_active_pre_match`.

1. Seed the 3 named scouts into `scout` table (Vera, Bram, Linnea or final picks).
2. Default each scout's `scout_strategy` row to `mode = MANUAL`, no assignment.
3. Generate Class 1 prospect pool via `recruitment.generate_rookie_class(class_year=1)`. Hidden truths and public baselines persisted to `prospect_pool`.
4. Initialize empty `scouting_state` (no rows — the absence of a row implies UNKNOWN tier).
5. Set `scouts_seeded_for_career = true` via existing `dynasty_state.set_state` (no new flags table — see §3.2 idempotency flags note).

Migrating a v1 save into V2-A code triggers this flow on first launch under V2-A.

### 5.2 At every match-week advance

Triggered on the V1 transition `season_active_match_report_pending → season_active_pre_match` (after the user clicks "Back to Hub" from a Match Report).

1. **Resolve Auto-Scout assignments first.** For each scout with `mode = AUTO` who has no current assignment or whose current target has VERIFIED on all axes, pick a new target via the strategy.
2. **Advance scouting points** for every active assignment using §4.6's narrowing rule.
   - Per axis, the scout's contribution updates the prospect's `scouting_state.scout_points` (cumulative across all scouts who have ever worked the prospect).
   - Per axis, the scout's contribution also updates the *per-scout* `scout_prospect_contribution` row (upsert keyed by `(scout_id, player_id, season)`): increment `weeks_worked`, accrue `contributed_scout_points`, refresh `last_active_week`, and snapshot the current per-axis estimate from this scout's perspective. This row is the source-of-truth for per-scout history and for off-season track-record writes.
3. **Tier-up check** per axis. Crossing a threshold:
   - Updates `scouting_state.tier`.
   - Emits a `ScoutingDomainEvent` (Glimpsed / Known / Verified, by axis) into the existing domain event log surface (the same one the League Wire and Hub Spotlight read from).
   - On `ratings_axis = VERIFIED` (or `ratings_axis = KNOWN` for HIGH-trait-sense scouts), compute and persist the CEILING label. Emit a `CeilingRevealedEvent`.
   - On `traits_axis` tier-ups, reveal additional traits per §4.4's table — up to 1 at GLIMPSED, up to 2 at KNOWN, all true traits at VERIFIED. If the prospect has fewer true traits than the tier authorizes, the wave reveals what exists. Each newly-revealed trait emits a `TraitRevealedEvent`. Trait pick at sub-VERIFIED tiers is deterministic via `derive_seed(root, "trait_reveal_pick", player_id, axis_tier)` so the same prospect always reveals the same traits in the same order regardless of which scout uncovered it.
   - **Trajectory tier-ups never reveal mid-season.** The internal `tier` value advances; the UI keeps it gated until the Draft beat.
4. **Hub Spotlight & alerts hook** read fresh domain events:
   - HIDDEN GEM rotation triggers when a `CeilingRevealedEvent` with `label = HIGH_CEILING` fires for a prospect whose public OVR baseline midpoint is meaningfully below the estimated true OVR (gem floor: `public_baseline_mid + 8 < estimated_ovr_mid`).
   - Reminder strip flags unassigned MANUAL scouts and "newly Verified — eligible for Draft Day reveal" prospects in the final 2 weeks of the regular season.

### 5.3 At regular-season end

Triggered on the V1 transition `season_active_pre_match → season_complete_offseason_beat[1]`.

No special scouting work. The Champion → Recap → Awards → Development → Retirements beats run as V1 designed.

### 5.4 At off-season Draft Day beat (the moment of truth)

This is the dramatic high point. The Draft beat that V1 already implements gets extended in-place:

1. **Pre-sign render:** for each rookie in the class, show its current scouting tier display per axis. Prospects no scout touched show wide public baseline only. Prospects scouted to KNOWN/VERIFIED show their bands and CEILING label. Off-season Draft uses the same `UncertaintyBar` component as the Scouting Center.
2. **Trajectory reveal sweep:** for any prospect whose `trajectory_axis = VERIFIED`, surface the true trajectory now in a punctuated UI moment. Generational and Star reveals get heavier visual weight. Skippable (per V1 ceremony patterns).
3. **User signs rookies** into open roster slots via V1's existing click-to-sign UI. Now better-informed: bands, CEILING labels, trajectory reveals (where earned) all visible per row.
4. **Post-Draft Accuracy Reckoning panel:** for every `(scout_id, player_id, season)` row in `scout_prospect_contribution` from this season, write a `scout_track_record` row by joining the contribution row's `last_estimated_*` snapshots against the prospect's `hidden_*` truths in `prospect_pool`. Track-record writes are append-only; aggregate per-scout accuracy stats rebuild from row history each time the Scout Strip card renders. **A scout that worked a prospect mid-season but was reassigned before the prospect was signed still writes a track record** — the contribution row preserves their last estimate at last_active_week, so their accuracy is judged on the work they did, not just on prospects they finished.
5. **Unsigned-prospect carry-forward:**
   - V1 already rolls unsigned rookies into next season's free pool.
   - V2-A persists their `scouting_state` rows with **one-tier decay** (VERIFIED → KNOWN, KNOWN → GLIMPSED, GLIMPSED → UNKNOWN, UNKNOWN unchanged).
   - **CEILING label and revealed traits stay revealed.** You don't unlearn known facts.
   - **Revealed trajectory** (after the Draft-beat reveal sweep) stays revealed for carryover prospects too — by Draft Day they are no longer hidden truths.

### 5.5 At season transition

Triggered on the V1 transition `next_season_ready → season_active_pre_match`.

1. Generate Class N+1 prospect pool via `generate_rookie_class(class_year=N+1)`.
2. Free-pool carryovers merge in with their decayed `scouting_state`.
3. Auto-scout strategies persist as last-set; manual assignments cleared (their targets either signed or rolled to free pool).
4. Reset weekly scouting cadence — scouts begin Week 1 of the new season fresh.

### 5.6 Determinism contract

- Every random draw uses `derive_seed(root, namespace, *ids)`.
- Namespaces introduced by V2-A: `prospect_gen`, `scouting`, `auto_scout_pick`, `prospect_archetype_mislabel`, `trait_reveal_pick`.
- These namespaces are **disjoint from match resolution namespaces**. Phase 1 golden regression remains unchanged.
- Re-running a season produces byte-identical `scouting_state`, track records, signings, and reveal events.

---

## 6. UI Surfaces

Four screens get touched. Two are new builds; two are extensions.

### 6.1 Scouting Center (new top-level "Scouting" tab)

Identity Bar persists. Below it, three regions stacked:

**Scout Strip (top, always visible).** Three cards — one per scout. Each card shows:
- Scout name.
- Specialty + weakness as plain copy ("Power-arm specialist · weak on dodgers · trait-sharp").
- Current assignment ("Scouting Dax Marrow — KNOWN ratings, GLIMPSED traits") or `Available`.
- MODE badge (MANUAL / AUTO).
- Career-level accuracy callout once a track record exists ("Track record: 18/23 ratings within ±5 over 2 seasons").
- Click → Scout Detail modal (manage strategy, see assignment history, see full track record).

**Prospect Board (dominant, fills the rest).** Sortable / filterable table of all prospects in this season's class plus carried-over free-pool players.

Columns:

- Player (name + age + hometown).
- Archetype guess (corrected if archetype_axis ≥ KNOWN).
- **OVR band** rendered via `UncertaintyBar`; halo width tied to `ratings_axis` tier.
- **Confidence dots** — four small dots per row (one per axis), filled by tier. Compact at-a-glance read.
- **CEILING label** — empty if not revealed; "HIGH CEILING" / "SOLID" / "STANDARD" if revealed.
- Hidden trait hints (revealed traits as small badges; unrevealed as `?`).
- Last-scouted week.
- Assigned-to (scout name or `—`).

Sorts (defaults: by OVR band midpoint descending):

- OVR band midpoint (high / low).
- Confidence (low / high).
- Age.
- Last-scouted.

**"Worth a Look" first-class sort button.** Surfaces low-confidence-with-high-estimated-OVR rows — the gem-hunter shortcut. Implements the dynasty sort as a real UI affordance, not a column toggle.

Filters:

- Archetype.
- Age band.
- Confidence tier (Unknown / Glimpsed / Known / Verified).
- Assigned vs unassigned.
- Scouted by [scout].

Click row → fuzzy-mode Player Profile.

**Reveal Ticker (bottom, collapsible).** Chronological list of this season's `ScoutingDomainEvent`s — *"Week 4: Vera glimpsed Dax Marrow"*, *"Week 7: trait IRONWALL surfaced on Theo Kahn"*, *"Week 9: Bram revealed HIGH CEILING on Marrow"*. Resets each season; persists for current-season reference.

### 6.2 New shared component: `UncertaintyBar`

In `ui_components.py`. Filled bar with a center dot at the band midpoint and a translucent halo showing the band width.

- Halo width is tier-driven:
  - UNKNOWN → halo spans the full 0–100 range.
  - GLIMPSED → halo width ±15 around midpoint.
  - KNOWN → halo width ±6 around midpoint.
  - VERIFIED → halo collapses to a single tick.
- Used on the Prospect Board, fuzzy-mode Player Profile ratings rows, and the Off-season Draft beat row renders.
- This is the V2-G component, shipping inside V2-A because the Scouting Center cannot honestly render without it.

### 6.3 Player Profile — fuzzy mode (new state)

Profile already exists from V1 in crisp mode. New: when the player is a prospect (in `prospect_pool`, not yet signed), the Profile renders in **fuzzy mode**:

- Header band uses a neutral charcoal instead of a club color (no club yet).
- Ratings panel: each rating row uses `UncertaintyBar` keyed to the prospect's `ratings_axis` tier.
- Archetype: shown as guess until `archetype_axis ≥ KNOWN`, then confirmed/corrected.
- Traits row: revealed traits as crisp badges; unrevealed as `?` placeholders. Count placeholders match "scouts believe X traits exist" framing once any have surfaced.
- CEILING row: `Ceiling: ?` until revealed; `HIGH CEILING / SOLID / STANDARD` once revealed.
- Trajectory row: `Trajectory: Hidden (revealed at Draft Day)` until the off-season Draft beat reveal; crisps after.
- "Open Scout Reports" link expanding into per-scout reports for this prospect (each scout's last-week best estimate, last-updated week).

The same canonical Profile component now supports four states per the V1 design's contract: prospect (fuzzy) → signed (crisp) → veteran (crisp + history) → HoF (crisp + retirement framing). V2-A delivers the prospect-fuzzy state.

**Once a prospect signs**, the header crisps to the user's club color, the UncertaintyBar rows replace with crisp rating bars, and CEILING+trajectory show their actual values. That visual transition is the *"now they're yours"* moment.

### 6.4 Hub — extended

- **Spotlight rotation** gains a **HIDDEN GEM** entry per §5.2 trigger. Click → fuzzy Profile. Replaces V1's stub copy that promised this for v2.
- **Reminder strip** gains scouting alerts: *"3 unassigned scouts"*, *"2 prospects newly Verified — eligible for Draft Day reveal"* (final 2 weeks only). Click jumps to Scouting Center filtered to the relevant rows.

### 6.5 Off-season Draft beat — extended

Per §5.4, the existing V1 Draft beat extends in-place:
- Pre-sign render uses `UncertaintyBar` per row for any unsigned prospect not at VERIFIED.
- Trajectory reveal sweep panel (skippable).
- Sign phase: existing V1 click-to-sign UI, now with all scouting info per row.
- Post-sign Accuracy Reckoning panel — per-scout summary card, predicted vs actual for every prospect that scout worked on this season. The moment scouts get *judged*.

### 6.6 League Wire — small touch

Rare CEILING-revealing events (a HIGH CEILING reveal) emit a low-priority Wire entry: *"Scouts in your room are buzzing about Dax Marrow."* Public-facing flavor only — actual ratings stay private. Other clubs don't see your scouting (V2-A has no AI competition); this is texture for the dynasty memory.

### 6.7 Nav shell

The top tab bar gains **Scouting** between Tactics and League. V2-A nav: **Hub · Roster · Tactics · Scouting · League · Save** (6 destinations, up from V1's 5).

---

## 7. Carry-Forward Across Season Transition

| State                                     | Carries forward? | Notes                                                  |
|-------------------------------------------|------------------|--------------------------------------------------------|
| Scout entities                            | Yes              | Static for V2-A. Same 3 names forever.                 |
| Scout track records                       | Yes (append-only)| Aggregates rebuild from row history.                   |
| Scout strategies (mode + params)          | Yes              | Persist as last-set; user can change anytime.          |
| `scouting_state` on signed prospects      | Migrates / drops | Once a prospect signs, scouting state is dropped — they're a roster player now, no fuzzy view. |
| `scouting_state` on unsigned prospects    | Yes (one-tier decay) | VERIFIED → KNOWN, KNOWN → GLIMPSED, GLIMPSED → UNKNOWN. UNKNOWN unchanged. |
| Revealed traits on unsigned prospects     | Yes (no decay)   | You don't unlearn revealed traits.                     |
| CEILING label on unsigned prospects       | Yes (no decay)   | You don't unlearn a ceiling read.                      |
| Revealed trajectory on unsigned prospects | Yes (no decay)   | After Draft-Day reveal, trajectory is no longer hidden.|
| `prospect_pool` rows                      | Unsigned roll into next class's free pool | Same rule V1 already established. |
| Auto-scout assignments                    | Cleared at season end | Targets either signed or carried over with decayed state — re-pick happens at next season's Week 1 advance. |

---

## 8. Testing

### 8.1 Layered coverage

V2-A introduces two new randomness sources (`prospect_gen`, `scouting`) and one engine wire-up (`development.py` honoring trajectory). Coverage breaks into three layers.

**Pure-helper unit tests** (mirror existing `test_manager_gui.py` pattern):
- Tier transitions: scout-points threshold crossings produce expected tier with deterministic input.
- Narrowing math: scout accuracy + specialty modifiers produce expected scout-points-per-week from a golden-number table.
- CEILING label derivation: known trajectory → known label, with HIGH-trait-sense early reveal at KNOWN tier.
- Carry-forward decay: VERIFIED → KNOWN, KNOWN → GLIMPSED, etc. CEILING + revealed traits/trajectory persist.
- Auto-scout target picking: deterministic given seed + strategy + pool state. SPECIALTY_FIT fallback to TOP_PUBLIC_OVR when archetype filter is empty in the class.
- Mode toggle behavior (MANUAL → AUTO and AUTO → MANUAL).

**Integration tests (state-machine level):**
- Full season simulation with 3 scouts on Auto: assert deterministic `scouting_state` values at end of season for fixed seed.
- Off-season Draft beat: trajectory_axis ≥ VERIFIED produces reveal events; track-record entries written for every `(scout_id, player_id, season)` row in `scout_prospect_contribution` for the season; signed prospects drop their `scouting_state`; unsigned prospects' state decays one tier and rolls into free pool.
- **Track-record-from-history test:** assign Vera to Dax for 5 weeks, reassign her to a different prospect, leave Dax untouched the rest of the season — at off-season Draft, Vera's track record entry for Dax exists and reflects her last estimate at week 5 (not the prospect's final state). Validates that contribution rows preserve historical estimates.
- Two-season run: scout track records aggregate correctly across seasons; carryover free-pool prospects retain decayed state; CEILING and revealed traits persist; `player_id` values for carryover prospects are identical across season transition (identity contract).

**Invariant tests (the integrity contract):**
- **Phase 1 golden regression unchanged.** No new randomness inside match resolution.
- **Trajectory honored by `development.py`:** golden test on a fixed-seed multi-season aging trace, asserting Generational > Star > Impact > Normal in cumulative OVR delta on hand-crafted prospects.
- **End-to-end determinism:** running the same career creation + season + Auto-scout + Draft seed twice produces byte-identical `scouting_state`, track records, signings, reveal event log.
- **Schema migration v7 → v8** adds tables idempotently; existing v7 saves load cleanly and seed scouts on first launch.

### 8.2 Edge cases — explicit handling

- **All scouts MANUAL with no assignments for an entire season** — legal. No scouting state advances; off-season Draft renders all prospects at UNKNOWN with public baselines only. Spam-recruit-by-volume style is preserved.
- **User toggles a scout from AUTO to MANUAL mid-season** — current Auto-picked assignment converts to MANUAL standing assignment.
- **A scout's specialty archetype is empty in the prospect class** (e.g. Vera is a power-arm specialist, no power-arm rookies) — Auto-scout SPECIALTY_FIT falls back to TOP_PUBLIC_OVR for that scout for that season. UI surfaces *"No power-arm prospects this class — Vera will scout broadly."*
- **Save/resume mid-week between scouting tick and match** — career state machine already handles this via `season_active_pre_match`; scouting tick fires on the existing match-week-advance hook, not on save/resume.
- **Existing v1 saves loaded into V2-A code** — schema migration v7→v8 adds new tables empty. First week-tick after load seeds scouts (idempotent gated by `scouts_seeded_for_career`). Existing dynasty intact.
- **Two scouts assigned to the same prospect** — disallowed in V2-A. Auto-scout pick logic restricts to non-overlap by default. MANUAL UI prevents overlap by greying out already-assigned prospects in the assignment dialog. Multi-scout overlap is a V3 polish concern.
- **Prospect signed by user mid-season** — N/A in V2-A. The only signing path is the off-season Draft beat. Mid-season free-agent signings are V3+.

---

## 9. Risks

1. **Trajectory generation rates need playtest tuning.** 1% Generational / 7% Star / 22% Impact / 70% Normal is a starting point. Too-rare Generational ⇒ the dopamine moment never lands; too-common ⇒ the system feels routine. Acceptance criteria flag playtest tuning explicitly.
2. **`development.py` integration is the integrity-critical wire.** Must ship green on the trajectory-honored golden test. Without it, scouting is lying.
3. **Auto-Scout strategy convergence.** TOP_PUBLIC_OVR + multiple scouts with no archetype filter would all converge on the top 3 prospects without the no-overlap default. The default is mandatory.
4. **UI density on the Prospect Board.** With 4 confidence dots + UncertaintyBar + CEILING + traits + scout assignment, rows risk getting noisy. Implementation acceptance includes a screenshot review.
5. **CEILING label rarity calibration.** ~8% HIGH CEILING per ~25-prospect class ⇒ ~2 high-ceiling prospects per year. About right for "rare but findable." Tunable.
6. **Schema migration robustness on v1 saves.** Existing v1 saves must load without losing dynasty state. Migration tests required.
7. **Tier threshold tuning.** Baseline numbers (5 scout-points/week neutral, KNOWN cumulative 35, VERIFIED cumulative 70) target the throughput shape spelled out in §4.2: ~6 prospects to KNOWN per scout-team-season, ~3 to VERIFIED. If playtest finds this too punishing (player feels they can't get useful information out of the system) or too generous (no forced prioritization), tune in `config.py` only. The implementation must keep all tunable values in `config.py` so playtest tuning never requires code changes.

---

## 10. Acceptance Criteria

V2-A ships when all of the following are green:

1. New career creates 3 named scouts and a Class 1 prospect pool with hidden truths and public baselines.
2. Scouting Center tab is reachable from the nav shell. User can assign manually, toggle Auto, see UncertaintyBar bands narrow as weeks pass.
3. Tier-ups surface in the Reveal Ticker; CEILING reveals fire at appropriate tiers (KNOWN for HIGH-trait-sense, VERIFIED otherwise); HIDDEN GEM Spotlight fires when applicable.
4. Off-season Draft beat reveals trajectory for all VERIFIED-trajectory prospects in a punctuated reveal sweep; CEILING surfaces on all VERIFIED-ratings prospects (and KNOWN-ratings prospects scouted by HIGH-trait-sense scouts).
5. Post-Draft Accuracy Reckoning panel writes track records; per-scout aggregate accuracy displays on the Scout Strip.
6. Unsigned prospects + their decayed scouting state carry into next season's free pool. CEILING and revealed traits/trajectory persist.
7. Player Profile renders fuzzy mode for prospects, crisps to user's club color on signing.
8. `development.py` honors trajectory: golden test passes showing Generational > Star > Impact > Normal cumulative OVR growth on multi-season aging traces.
9. Phase 1 golden regression unchanged.
10. All V1 153 tests still pass; new tests added for V2-A pure helpers, integration, and integrity invariants.
11. Schema migration v7 → v8 lands cleanly. Existing v1 saves load without loss.
12. Manual screenshot review of Scouting Center, fuzzy Profile, Off-season Draft beat under V2-A captured to `output/ui-review-v2a/` before shipping.
13. Trajectory generation rates and tier thresholds are reviewed in playtest; tuning happens in `config.py` only (no code changes outside config required for tuning).

---

## 11. Implementation Slicing Hint

**Not the implementation plan** — that's the writing-plans skill's job. The slicing rationale is recorded here so the planner doesn't lead with UI before engine contracts exist.

### M0 — Engine & Schema Contracts (no UI)

1. Schema v7 → v8 migration + new tables.
2. `Scout` entity + 3 seeded scouts + idempotent seeding flag.
3. Extended `recruitment.generate_rookie_class(class_year)` writing to `prospect_pool`.
4. `scouting_center.py` core: `ScoutingState`, tier rules, narrowing math, CEILING derivation, decay logic, Auto-scout pick logic.
5. `development.py` extended to honor trajectory.
6. Pure-helper tests + integrity invariant tests (Phase 1 regression, trajectory-honored golden, end-to-end determinism).

**Definition of done:** all engine tests green, golden logs unchanged, no UI yet. Invisible to the user but unblocks every UI step.

### M1 — Scouting Center vertical slice

1. New "Scouting" tab in nav shell.
2. `UncertaintyBar` component.
3. Scout Strip + Prospect Board + Reveal Ticker rendering.
4. Manual assignment dialog (one scout, one prospect at a time).
5. Auto-Scout toggle + strategy editor.
6. Week-tick wiring through `career_state.py` existing transitions.

**Acceptance:** user can play through one full season, assigning scouts manually or via Auto, watching tier-ups happen in real time as weeks advance. Bands narrow on Prospect Board.

### M2 — Player Profile fuzzy mode

1. Profile component supports prospect-fuzzy state.
2. CEILING + trait reveal display.
3. Per-scout reports view.
4. Click-through from Prospect Board, Hub HIDDEN GEM Spotlight, Off-season Draft beat.

### M3 — Off-season Draft beat extension

1. Tier-aware Draft list rendering.
2. Trajectory reveal sweep (skippable).
3. Sign phase using existing V1 click-to-sign with new info density.
4. Accuracy Reckoning panel.
5. Carry-forward decay logic at season transition.

### M4 — Hub integration & polish

1. HIDDEN GEM Spotlight rotation.
2. Reminder strip scouting alerts.
3. League Wire CEILING-buzz entries.
4. Screenshot review pass to `output/ui-review-v2a/`.
5. Playtest tuning pass on trajectory rates + tier thresholds.

---

*End of V2-A Stateful Scouting Model design spec.*
