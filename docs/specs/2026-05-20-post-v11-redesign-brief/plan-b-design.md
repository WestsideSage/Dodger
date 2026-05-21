# Plan B — Player Attribute v2 (Design)

Date: 2026-05-20
Status: Design approved. Ready for implementation-plan authoring.
Parent roadmap: [tier-1-roadmap.md](./tier-1-roadmap.md)
Predecessor: [plan-a-hybrid-driver.md](./plan-a-hybrid-driver.md) (landed 2026-05-20)

This design is the brainstormed and approved scope for Plan B. The detailed
task-by-task implementation plan is authored separately at
`plan-b-player-attribute-v2.md`.

## Goal

Upgrade the player data model from the V1–V11 ratings shape (accuracy /
power / dodge / catch / stamina / tactical_iq) and the vestigial single-value
`PlayerArchetype` to a v2 model that drives recognizable individual behavior
in the rec driver, with rec-league archetype semantics that downstream Plan C
work (voice, recruiting, scouting copy) can consume.

## Scope

In scope:

1. Three new `PlayerRatings` fields — `catch_courage`, `throw_selection_iq`,
   `conditioning_curve`. All 0–100, default 50. Bounded by `apply_bounds()`.
2. `PlayerArchetype` rewrite — drop `TACTICAL`; add 4 base archetypes
   (`THROWER`, `CATCHER`, `RETRIEVER`, `DODGER_ANCHOR`) plus 4 named hybrids
   (`THROWER_CATCHER`, `THROWER_DODGER`, `CATCHER_RETRIEVER`,
   `RETRIEVER_DODGER`).
3. Rec-driver behavior wiring — one decision point per new attribute (see
   "Architecture").
4. Cross-file audit + cleanup of the 21 modules that reference
   `PlayerArchetype`. STATUS.md asserts the field is vestigial; the audit
   verifies that and updates each consumer.
5. Curated seed rosters get v2 fields written in (hand-authored archetype
   where it reads as obvious; helper-derived otherwise).
6. Tests for each new attribute's behavioral effect, plus enum coverage and
   a seed-roundtrip test.

Explicit non-goals (deferred to Plan C, per roadmap):

- `CoachPolicy` v2 (the four-knob redesign).
- Recruiting / scouting reading new attributes for scout copy.
- Command Center UI surfacing the new fields.
- Voice modules narrating archetype.
- AI Program Manager use of attributes (cuttable subsystem #9).

Explicit non-goals (clean break, per brief §8):

- Save-file migration. Existing V1–V11 saves will not load after Plan B.
  This is accepted; the brief commits to clean break for the wider redesign,
  and this is the natural break point.

## Architecture

### models.py

`PlayerRatings`: extended with three new fields and default 50. `overall()`
updates to include the new fields in the average. `apply_bounds()` clamps
them. `normalized_*` helpers added for any new field consumed by rec-driver
math.

`PlayerArchetype`: enum rewritten. `Player.archetype` loses its default —
all `Player(...)` construction sites (randomizer, curated loader, tests) must
supply a value. This is the bulk of the cross-file diff.

A new helper `derive_archetype_from_ratings(ratings: PlayerRatings) ->
PlayerArchetype` returns a base archetype using deterministic rules over
the rating fields. Sketch: `accuracy` and `power` favor `THROWER`; `catch`
and `catch_courage` favor `CATCHER`; `dodge` favors `DODGER_ANCHOR`;
`stamina` and a retriever-leaning composite favor `RETRIEVER`. The exact
formula and tie-breaking are pinned in the implementation plan, not here —
the design constraint is only that the helper is total and deterministic.
Hybrids are assigned by the randomizer's secondary roll when the top-two
base scores are close.

### rec_engine.py

Three decision points, one per attribute:

| Attribute | Decision point | Effect |
|---|---|---|
| `throw_selection_iq` | `_select_throwers` | Gates the throw-trigger probability. High IQ throws only when `accuracy * effectiveness * f(iq)` exceeds a threshold. Low IQ keeps current near-random behavior. |
| `catch_courage` | `_resolve_throw` catch branch | Replaces the hard-coded `catch_skill * 0.4` weighting with a courage-modulated branch. High courage = catch attempt rate climbs; low courage = dodge-only. Catch *success* rate still driven by `catch` rating. |
| `conditioning_curve` | `FatigueParams.conditioning_curve` | Already wired in Plan A but sourced from `ratings.stamina`. Plan B re-sources it from `ratings.conditioning_curve`; `stamina` returns to being a generic fitness-pool rating used elsewhere (recovery between rallies / matches). |

The driver still reads the existing `accuracy`, `dodge`, `catch`, `stamina`
fields where it does today. The new attributes are additive decision-makers,
not replacements for the core skill math.

### Curated seed rosters

The roster JSON path is to be located during implementation
(`grep -rln "club_id" data/ src/`). For each curated player, hand-edit v2
fields where the archetype reads as obvious from existing ratings, and use
`derive_archetype_from_ratings` for the rest. No runtime-only fallback —
curated rosters must declare their v2 fields explicitly. Random players use
the default-50 / randomizer path.

### Cross-file archetype audit

The 21 modules that import `PlayerArchetype` get classified during
implementation:

- **Cosmetic** — file imports the enum only to print or compare equality.
  Mechanical update: `TACTICAL` references swap to the new enum's
  `display_name` accessor or to a specific new value.
- **Load-bearing** — file branches behaviorally on `TACTICAL`. STATUS.md says
  none exist. If any are found, each becomes its own implementation sub-task.

A `display_name` property is added to the enum to keep voice / UI copy
working without per-call mapping tables.

## Data flow

```
Career creation
  randomizer  -> Player(ratings = 9 rating fields, archetype = base | hybrid)
  curated     -> roster JSON with explicit v2 fields -> Player(...)
                              |
                              v
                  DriverMatchInput.player_lookup
                              |
                              v
                       RecTier1Driver
                       /      |       \
                      v       v        v
            _select_      _resolve_   FatigueParams.
            throwers      throw        conditioning_curve
            (uses         (uses        (sourced from
            throw_        catch_       ratings.conditioning
            selection_    courage)     _curve)
            iq)
```

## Error handling

- `PlayerRatings.apply_bounds()` clamps the three new fields to `[0, 100]`.
- `PlayerArchetype(value)` raises `ValueError` on unknown strings — surfaced
  as a clear roster-loader error rather than silent default.
- Roster-loader test asserts every curated player parses with v2 fields
  present (no silent default-50 fallback for curated rosters).
- `derive_archetype_from_ratings` is total: every rating profile maps to
  exactly one base archetype, with deterministic tie-breaking.

## Testing strategy

| Layer | Test |
|---|---|
| `PlayerRatings` | New fields exist, default 50, clamp at bounds, `overall()` covers them. |
| `PlayerArchetype` | Enum has exactly 8 values; `TACTICAL` gone; `display_name` returns rec-league copy. |
| `derive_archetype_from_ratings` | Canonical rating profiles map to expected base archetype; tie-breaking is deterministic. |
| Rec driver — `catch_courage` | With all other ratings held, `catch_courage=90` vs `=10` produces measurably more catch attempts across a seeded run. |
| Rec driver — `throw_selection_iq` | High IQ produces fewer total throws but higher hit-rate per throw across a seeded run. |
| Rec driver — `conditioning_curve` | High `conditioning_curve` produces lower mean fatigue at match end. |
| Curated rosters | Load -> serialize -> load roundtrip, no field loss. |
| Cross-file | All 21 archetype consumers still import; any pattern-match on `TACTICAL` resolved. |
| Regression gate | Full pytest green; `tools/tier_1_sanity_probe.py` still OK with all 6 moment kinds; V11 / USAD untouched. |

## Risks

- **Cross-file ripple** — 21 consumers is a wide diff surface. Mitigated by
  the audit task and by `display_name` keeping copy-sites stable.
- **Behavioral drift in sanity probe** — adding three new decision points
  could shift moment-kind balance enough that the probe stops emitting one
  of the six. Mitigated by re-running the probe as a regression check at the
  end of every implementation task that touches the rec driver.
- **Clean-break friction** — anyone with a live V11 career cannot upgrade.
  Accepted per brief §8 and user confirmation.

## Definition of done

- `PlayerRatings` carries the three new fields; `PlayerArchetype` has 8
  values; `TACTICAL` is gone.
- Rec driver behavior changes are pinned by attribute-specific tests.
- All 21 archetype consumers compile and pass tests after the cleanup.
- Curated seed rosters declare v2 fields explicitly.
- Full pytest suite green; Plan A's sanity probe still prints `OK` with all
  six moment kinds emitted across 25 matches.
- `docs/STATUS.md` updated to reflect Plan B landing.
- `tier-1-roadmap.md` updated: Plan B row marked landed.
