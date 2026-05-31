# Plan B — Player Attribute v2 (Design)

Date: 2026-05-20
Status: Design v2, post adversarial review. Implementation-plan ready.
Parent roadmap: [tier-1-roadmap.md](./tier-1-roadmap.md)
Predecessor: [plan-a-hybrid-driver.md](./plan-a-hybrid-driver.md) (landed 2026-05-20)

This design is the brainstormed-and-revised scope for Plan B. The detailed
task-by-task implementation plan is authored separately at
`plan-b-player-attribute-v2.md`.

## Relation to Prior Specs

- **Builds on Plan A.** Plan A introduced the `EngineDriver` protocol, the
  rec driver, and the `fatigue` / `flood_throws` / `stall_timer` /
  `moment_events` primitives. Plan B fills in the per-player attribute
  layer that those primitives were designed to accept.
- **Supersedes the V6 player-identity assumptions.** The current
  `PlayerArchetype` enum (POWER / AGILITY / PRECISION / DEFENSE / TACTICAL)
  and the standalone tactical-IQ rating come from the V6 identity work
  (`src/dodgeball_sim/identity.py`, `tests/test_v6_player_identity.py`).
  Plan B replaces the enum with a rec-league archetype set and re-bases the
  parallel string-archetypes used in `recruitment.py` / `scouting.py` /
  `identity.py` on the new enum. Where V6 documents conflict with this
  design, this design wins.
- **Inherits the AGENTS engine-integrity contract.** Behavior changes are
  pinned by tests written in the same task. The Plan A sanity probe
  (`tools/tier_1_sanity_probe.py`) is a regression gate; all six moment
  kinds must still emit at least once across its 25-match run.
- **Does not expand Plan C / UI / scouting scope.** Voice modules, the
  Command Center pre-match UI, recruiting-screen reads of the new
  attributes, and `CoachPolicy` v2 are explicitly Plan C work.
  Recruiting / scouting copy in this codebase already uses parallel
  string-archetypes; Plan B re-bases that derivation on the new enum but
  does not change which screens read it.

## Goal

Upgrade the player data model from the V1–V11 ratings shape (accuracy /
power / dodge / catch / stamina / tactical_iq) and the V6 single-axis
`PlayerArchetype` to a v2 model that drives recognizable individual
behavior in the rec driver, with rec-league archetype semantics that
downstream Plan C work (voice, recruiting, scouting copy) can consume.

## Scope

In scope:

1. Three new `PlayerRatings` fields — `catch_courage`, `throw_selection_iq`,
   `conditioning_curve`. All 0–100, default 50 for tests and randomizer.
   Bounded by `apply_bounds()`. These are **behavioral identity traits**,
   not pure skill ratings (see "Skill OVR vs. Identity OVR" below).
2. `PlayerArchetype` rewrite — drop POWER / AGILITY / PRECISION / DEFENSE /
   TACTICAL. Add 4 base archetypes (`THROWER`, `CATCHER`, `BALL_HAWK`,
   `DODGER_ANCHOR`) plus 4 named hybrids (`THROWER_CATCHER`,
   `THROWER_DODGER`, `CATCHER_HAWK`, `HAWK_DODGER`). `BALL_HAWK` replaces
   the originally-proposed `RETRIEVER` because USAD's "designated
   retriever" is an inactive support role; `BALL_HAWK` describes an active
   on-court possession-specialist.
3. Rec-driver behavior wiring — one decision point per new attribute (see
   "Architecture").
4. Cross-file audit + cleanup of the modules that reference the old enum
   and the parallel string-archetypes (table below).
5. Curated seed rosters get v2 fields written in.
6. Tests for each new attribute's behavioral effect using deterministic
   mocked-RNG branch tests (no "measurably more" probabilistic assertions).

Explicit non-goals (deferred to Plan C, per roadmap):

- `CoachPolicy` v2 (the four-knob redesign).
- Recruiting / scouting screens reading new attributes for player-facing
  scout copy.
- Command Center UI surfacing the new fields.
- Voice modules narrating archetype.
- AI Program Manager use of attributes (cuttable subsystem #9).

Explicit non-goals (clean break, per brief §8):

- Save-file migration. Existing V1–V11 saves will not load after Plan B.
  Loaders **fail loudly** on legacy data — no silent default-50 backfill.

## Architecture

### Skill OVR vs. Identity OVR

`PlayerRatings.overall()` MUST NOT average behavioral traits with skills.
The split is:

| Bucket | Fields | OVR helper |
|---|---|---|
| **Skill ratings** | `accuracy`, `power`, `dodge`, `catch`, `stamina` | `overall_skill()` — mean. Replaces today's `overall()` for player-facing displays. |
| **Identity traits** | `catch_courage`, `throw_selection_iq`, `conditioning_curve`, `tactical_iq` | `identity_profile()` — returns a dataclass, not a number. Surfaced as text in Plan C, never averaged into skill OVR. |
| **Composite (optional)** | weighted blend, used only for matchmaking / draft ordering | `overall_composite(skill_weight=0.8)` — explicit, never the default. |

The existing `overall()` becomes `overall_skill()` to make the rename
intentional at every call site. Downstream code that uses `overall()` for
UI display gets the renamed call. Any code that wants a composite must opt
in explicitly.

### models.py

`PlayerRatings`: extended with `catch_courage`, `throw_selection_iq`,
`conditioning_curve` (all default 50.0 in the dataclass for tests /
randomizer). `apply_bounds()` clamps them. `normalized_*` helpers added
as needed for rec-driver math. `overall()` is renamed to `overall_skill()`
and covers only the five skill fields.

`PlayerArchetype`: enum rewritten to the 4 base + 4 hybrid values listed
above. `Player.archetype` keeps no default — every construction path
(randomizer, curated loader, identity helpers, tests) must supply one.

A new module-level helper `derive_archetype(ratings: PlayerRatings, *,
allow_hybrid: bool = True) -> PlayerArchetype` is the **single canonical
source** for archetype derivation. It is total and deterministic:

1. Compute four base scores from rating fields (formula pinned in the
   implementation plan; sketch: `accuracy + power` → THROWER,
   `catch + catch_courage` → CATCHER, `stamina + dodge` → BALL_HAWK,
   `dodge + tactical_iq` → DODGER_ANCHOR — final weights tuned in plan).
2. Take the top two base scores. If `allow_hybrid` and the gap between
   them is below a pinned threshold (e.g. 8 points on the rating scale),
   return the named hybrid for that pair. Otherwise return the top base.
3. Tie-breaking is alphabetical on the enum value name — fully
   deterministic, no RNG.

The randomizer **calls this helper** for both base and hybrid assignment.
The persistence loader uses it for back-compat reads only when explicitly
in fallback mode (otherwise loaders fail loudly — see "Error handling").

### rec_engine.py — three decision points

| Attribute | Where | Effect |
|---|---|---|
| `throw_selection_iq` | `_select_throwers` | Modulates the candidate filter. High IQ raises the value threshold a throw must clear (target identification, expected hit value under current effectiveness, and stall-clock pressure when `stall_timer.seconds_holding` approaches `STALL_CAP_SECONDS`). Under late-stall pressure, high IQ throws *more*, not less — the trait is "good judgment," not "passive." Low IQ throws on roughly the current heuristic. |
| `catch_courage` | `_resolve_throw` target-response branch | Replaces the binary catch-vs-dodge choice with a **three-way** weighted choice: dodge, block, catch. Block is its own lane (deflects the ball without removing the thrower). Catch rate scales with courage; block is the medium-courage middle ground; dodge dominates at low courage. Tier 1 has `no_blocking_mode_enabled=False`, so block is legal here; higher tiers with no-blocking will collapse the lane via the existing `no_blocking.py` module without changing this design. |
| `conditioning_curve` | `FatigueParams.conditioning_curve` | Re-sourced from `ratings.conditioning_curve` (Plan A used `ratings.stamina` as a placeholder). `stamina` returns to being a general fitness pool used by recovery between rallies and across matches. |

The driver still reads `accuracy`, `dodge`, `catch`, `stamina` where it
does today. The new attributes modulate *which decision branch fires*;
the existing skill ratings still determine the magnitude of the outcome
within the chosen branch.

### Higher-tier compatibility note on `throw_selection_iq`

Tier 1 has `burden_modeled=False`. The IQ trait is wired against Tier 1's
`stall_timer` (the rec equivalent of burden). When the official driver
gains v2 behavior in a future plan, the same trait flows naturally into
the formal `burden` module via the same shape: under burden pressure,
high IQ chooses the best legal pressure throw rather than refusing to
throw. The trait MUST NOT translate to "throws less" once burden /
throw-clock is in play — it translates to "throws smarter, including
smarter forced throws."

### Curated seed rosters

The roster source path is located in the implementation plan (a `grep`
of `club_id` and `Player(` in `src/` and any `data/`). For each curated
player, v2 fields are hand-authored when the archetype reads as obvious
from existing ratings, and `derive_archetype` is used otherwise. No
runtime-only fallback: curated rosters must declare v2 fields explicitly.

### Cross-file archetype audit

Two systems coexist today and must be reconciled in this plan:

**System 1 — `PlayerArchetype` enum** (5 V6 values):

| File | Current usage | Class | Required change |
|---|---|---|---|
| `models.py` | Defines enum + `Player.archetype` field with default `TACTICAL`. | Owner | Rewrite enum to 4 base + 4 hybrids. Drop default; add `display_name`. |
| `randomizer.py` (L91-100) | `rng.choice(list(PlayerArchetype))`; per-archetype rating bonuses. | Load-bearing | Replace with `derive_archetype(ratings)` after rolling ratings; rewrite per-archetype rating bonus blocks against the new enum values. |
| `development.py` (L92-99) | Per-archetype primary-stat lists for growth allocation. | Load-bearing | Rewrite the four primary-stat lists for the new base archetypes. Hybrids inherit from their two base parents (intersection or union — pinned in plan). |
| `lineup.py` (L20-23) | Per-court-slot archetype preferences. | Load-bearing | Rewrite the slot→archetype map against the new base archetypes. Hybrid players match either base. |
| `persistence.py` (L74) | `PlayerArchetype(d.get("archetype", "Tactical"))` — defaults to Tactical on missing key. | Load-bearing | Remove default; raise loud `ValueError` if `archetype` key is missing or unknown. (Clean break: legacy saves fail at load.) |

**System 2 — parallel string-archetypes** (5 string labels):

| File | Current usage | Class | Required change |
|---|---|---|---|
| `recruitment.py` (L146, L293-304) | `_archetype_for_ratings` returns one of `"Sharpshooter"`, `"Enforcer"`, `"Escape Artist"`, `"Ball Hawk"`, `"Iron Engine"`. | Load-bearing (string) | Re-base on `derive_archetype` and the new enum; map each new enum value to a recruiting display string. Keep the recruiting-pool list itself stable in shape but sourced from the new enum's `display_name`. |
| `scouting.py` (L71-84) | `_reveal_archetype` — same five strings, derived from ratings. | Load-bearing (string) | Same: route through `derive_archetype`; map enum → display string. |
| `identity.py` (L66+, L140+) | `classify_archetype(player)` returns one of the same five strings; drives prefix/suffix/title lookup tables. | Load-bearing (string) | Route through `derive_archetype`. Rewrite the prefix/suffix/title tables against the new enum values. |
| `replay_proof.py` (L356, L366-372) | Reads `archetype` string from player dict for liability copy. | Cosmetic | No code change beyond verifying the upstream payload now carries new strings. |
| `matchup_details.py` (L68) | Prints `focal_player.archetype.value` in a label. | Cosmetic | Verify display reads cleanly with new enum values. |

**Files that touch `scout.archetype_affinities` (not Player.archetype):**

| File | Note |
|---|---|
| `scouting_center.py`, `manager_gui.py`, `config.py`, `offseason_beats.py`, `recruitment_domain.py`, `recruiting_office.py`, `save_service.py`, `web_status_service.py`, `dynasty_cli.py`, `offseason_presentation.py`, `offseason_ceremony.py` | These reference scout-side affinity strings that come from `recruitment.py`'s pool. They follow System 2 transitively. Once `recruitment.py`'s pool is re-sourced from `derive_archetype`, these files require no direct changes beyond a verification pass. |

**Tests that depend on archetype semantics:**

- `tests/test_development.py` — asserts per-archetype growth allocation.
  Rewrite against new base archetypes.
- `tests/test_v6_player_identity.py` — asserts classify-archetype string
  outputs and identity-card titles. Rewrite against the new enum and
  re-derived display strings.

The implementation plan opens with a verification task that re-runs this
audit grep against the current main and reconciles any drift.

## Data flow

```
Career creation
  randomizer    -> roll PlayerRatings (incl. 3 new fields)
                -> derive_archetype(ratings) -> base | hybrid
                -> Player(ratings=..., archetype=...)
  curated       -> roster JSON with explicit v2 fields -> Player(...)
                              |
                              v
                  DriverMatchInput.player_lookup
                              |
                              v
                       RecTier1Driver
                       /      |        \
                      v       v         v
              _select_   _resolve_     FatigueParams.
              throwers   throw          conditioning_curve
              (uses      (3-way:        (from
              throw_     dodge|block|   ratings.conditioning
              selection_ catch,          _curve)
              iq +       weighted by
              stall_     catch_courage)
              clock)
```

Recruiting / scouting / identity all consume `derive_archetype` (or
`player.archetype` directly) and map to display strings via a single
enum-level `display_name` accessor.

## Error handling

- `PlayerRatings.apply_bounds()` clamps the three new fields to `[0, 100]`.
- `PlayerArchetype(value)` raises `ValueError` on unknown strings —
  surfaced as a clear roster-loader error, never a silent default.
- `persistence.load_player(...)` raises `ValueError` when a saved player
  is missing v2 rating fields OR the new `archetype` enum value
  (clean-break failure mode).
- Test for the clean-break behavior: a fixture V1–V11-shaped dict raises
  the documented error with a message naming the missing fields.
- `derive_archetype` is total: every rating profile maps to exactly one
  archetype, with deterministic tie-breaking.

## Testing strategy

All behavioral tests use **mocked / seeded RNG with deterministic
threshold assertions**, not probabilistic "measurably more" language.

| Layer | Test |
|---|---|
| `PlayerRatings` | New fields exist, default 50, clamp at bounds. `overall_skill()` covers only the 5 skill fields and is the rename of today's `overall()`. |
| `PlayerArchetype` | Enum has exactly 8 values; old V6 values (POWER, AGILITY, PRECISION, DEFENSE, TACTICAL) are gone; `display_name` returns rec-league copy. |
| `derive_archetype` | Canonical rating profiles map to expected base archetype; pinned gap threshold returns hybrids; tie-breaking is deterministic and alphabetical. |
| Rec driver — `catch_courage` | With mocked RNG forcing the response-roll boundary, courage=10 → dodge branch entered; courage=50 → block branch; courage=90 → catch branch. Exact branch coverage, no probabilistic count. |
| Rec driver — `throw_selection_iq` | With seeded driver run and fixed ratings except IQ: high-IQ runs produce throws only when the value threshold is cleared (verified by event-by-event inspection, not aggregate counts). Late-stall test: with `stall_timer.seconds_holding` near cap, high IQ still throws — the trait is good judgment, not passivity. |
| Rec driver — `conditioning_curve` | With mocked accumulation, high-curve player's `FatigueState.value` after N ticks is below low-curve player's. Exact comparison, no probabilistic count. |
| Curated rosters | Load → serialize → load roundtrip, no field loss; legacy fixture raises documented `ValueError`. |
| Cross-file (System 1) | `development.py`, `lineup.py`, `randomizer.py`, `persistence.py` tests rewritten against new enum. |
| Cross-file (System 2) | `recruitment.py`, `scouting.py`, `identity.py` derive strings from `derive_archetype`; `test_v6_player_identity.py` rewritten. |
| Regression gate | Full pytest green; `tools/tier_1_sanity_probe.py` still OK with all 6 moment kinds; V11 / USAD conformance tests untouched. |

## Risks

- **Cross-file ripple wider than first audit suggested.** Two archetype
  systems coexist (enum + strings). Both must be re-sourced from
  `derive_archetype`. Mitigated by the audit table above and by the
  first implementation task being a re-grep verification.
- **Behavioral drift in sanity probe.** Adding three new decision points
  (especially the new block lane) could shift moment-kind balance enough
  that the probe stops emitting one of the six. Mitigated by running the
  probe as a regression check at the end of every implementation task
  that touches the rec driver.
- **OVR meaning change.** `overall()` → `overall_skill()` is a rename
  that touches every UI display call site. Risk of mismatched display
  semantics if a caller is missed. Mitigated by deleting the old
  `overall()` rather than aliasing, so any miss is a `AttributeError` at
  test time, not a silent semantic shift.
- **Clean-break friction.** Live V11 careers do not survive. Accepted per
  brief §8 and user confirmation.

## Definition of done

- `PlayerRatings` carries the three new fields; `PlayerArchetype` has 8
  values; old V6 enum values are gone.
- `overall()` renamed to `overall_skill()` at every call site; identity
  traits are not averaged into skill OVR.
- `derive_archetype` is the single canonical helper for base + hybrid
  archetype assignment; randomizer, persistence (fallback path only),
  recruitment, scouting, and identity all route through it.
- Rec driver behavior changes are pinned by deterministic mocked-RNG
  branch tests, not probabilistic assertions.
- All files in the audit table compile and pass tests after cleanup.
- Curated seed rosters declare v2 fields explicitly; loaders raise loud
  `ValueError` on legacy data.
- Full pytest suite green; Plan A's sanity probe still prints `OK` with
  all six moment kinds emitted across 25 matches.
- `docs/STATUS.md` updated to reflect Plan B landing (and to correct the
  "vestigial archetype" claim).
- `tier-1-roadmap.md` updated: Plan B row marked landed.
