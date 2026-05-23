# Plan C — Tier 1 Player-Facing Surface (Design)

Date: 2026-05-22
Status: Design v1. Implementation-plan-ready once reviewed.
Parent roadmap: [tier-1-roadmap.md](./tier-1-roadmap.md)
Predecessors: [plan-a-hybrid-driver.md](./plan-a-hybrid-driver.md) (landed 2026-05-20), [plan-b-design.md](./plan-b-design.md) (landed 2026-05-20)

This is the brainstormed-and-scoped design for Plan C. The detailed
task-by-task implementation plan will be authored separately at
`plan-c-tier1-surface.md` after this design is reviewed.

## Relation to Prior Specs

- **Builds on Plan A.** Plan A's `RecTier1Driver` already emits the six
  `MomentEvent` kinds with stable shapes (`moment_events.py`). Plan C is
  the first consumer of those events on the player-facing side — replay
  UI and voice modules — and is the first non-test consumer of the
  driver's `CoachPolicy` input slot. The `EngineDriver` protocol is **not**
  changed by Plan C.
- **Builds on Plan B.** Plan B landed the v2 `PlayerRatings`
  (`catch_courage`, `throw_selection_iq`, `conditioning_curve`), the 8-value
  `PlayerArchetype`, and `derive_archetype` / `identity_profile`. Plan C is
  the first place the *player* can see those new attributes through
  recruiting / scouting / Command Center copy.
- **Deletes the V1–V11 `CoachPolicy` 8-field model.** Per brief §6.5 the
  old data model is deleted; the useful semantic behaviors are preserved
  by mapping them into the new four-knob tier-aware tactics concepts.
  Old fields are not preserved verbatim and no migration shim is added —
  loaders fail loudly on V11 policy payloads, consistent with the
  brief §8 clean-break stance and the Plan B precedent.
- **Inherits the engine-integrity contract.** V11 / USAD conformance
  tests stay green. The Plan A sanity probe (`tools/tier_1_sanity_probe.py`)
  remains a regression gate — all six moment kinds must still emit at
  least once across its 25-match run, with the v2 policy used as the
  driver input.
- **Does not expand Plan D / O1 scope.** No engine balance work, no
  Monte Carlo reporting, no new simulation-health probe. Plan C narrows
  to the rec-league surface; Plan D writes the probe.

## Goal

Make the Tier 1 (Local Rec League) match loop end-to-end *recognizable*
to a rec-league dodgeball player:

1. The player makes four small pre-match choices in the Command Center
   that the rec driver actually consumes.
2. The match replay surfaces all six moment beats in rec-league vocabulary.
3. The aftermath narrates the result by referencing the moments that
   happened and the tactics that produced them.
4. A Playwright e2e walks Career start → Command Center → Sim →
   Match Replay → Aftermath and asserts the recognizable beats render.

The brief's success test (§2.4) is the explicit acceptance bar: *a
rec-league dodgeball player watching a session must recognize the sport*.

## Scope

In scope:

1. **`CoachPolicy` v2** — four enum-valued knobs (Approach, Target Focus,
   Catch Posture, Opening Rush Plan). Old 8-float model deleted at every
   call site listed in the audit table below. The initial draft listed 14
   files; the 2026-05-22 handoff audit found additional live call sites in
   orchestration, AI plan generation, official resolution, frontend types,
   and existing tests. Treat the expanded table as authoritative until the
   opening implementation grep proves otherwise.
2. **Rec driver wiring** — `RecTier1Driver` reads the new policy at four
   pinned decision points (one per knob). USAD `OfficialDriver` keeps a
   stub that accepts the same v2 shape but ignores it (Plan A explicitly
   left `OfficialDriver.moment_events` empty; the policy stays inert for
   USAD until a later tier sub-project picks it up).
3. **Command Center pre-match UI** — a single screen with the four knobs,
   each as a 2-to-5-option chooser with a one-line rec-league
   explanation. Persists per-team policy across weeks (carries the same
   storage contract that the old 8-field model used — same key, new
   payload shape). The live API currently owns `/api/tactics` and
   `/api/command-center/plan`; Plan C rewrites those contracts to v2
   rather than silently bypassing them. A new `/api/match-week/policy`
   route is optional only as a compatibility alias if the implementation
   wants the clearer name.
4. **Match Replay UI — moment beats** — `ReplayTimeline` highlights the
   six moment kinds inline with the existing event stream. Speed
   controls (1x / 2x / 4x / instant), already partly present, are
   audited and locked to a single component.
5. **Voice modules rewritten against moment events** —
   `voice_verdict.py` and `voice_aftermath.py` read the emitted
   `MomentEvent` list and produce rec-league copy. `voice_pregame.py`
   reads the v2 policy for one pre-match line.
6. **Rec-league vocabulary glossary** — a single source-of-truth dict
   (`voice_register.py` or equivalent) that locks the Tier 1 register.
   All voice / replay / Command Center copy at Tier 1 routes through it.
7. **Playwright e2e** for the Tier 1 loop.

Explicit non-goals:

- **No Tier 2+ tactical knobs.** The brief explicitly grows the tactical
  surface tier by tier; Tier 1 stays at four knobs.
- **No multi-tier vocabulary switching.** A single rec-league register
  is implemented; the dispatch shape (`voice_register.for_tier(tier)`) is
  designed for future tiers but only the Tier 1 entry exists.
- **No stats / awards screens redesign** (brief §6.8, Plan D adjacent).
- **No recruiting / scouting redesign** beyond surfacing the Plan B v2
  attributes that already flow through `identity.py` and `scouting.py`.
- **No O1 engine balance fix.** Balance work is gated on Plan D's probe
  and golden-log regeneration.
- **No AI Program Manager wiring.** Subsystem #9 stays cuttable.
- **No save migration shim.** Legacy policy payloads fail loud at load.

## Architecture

### `CoachPolicy` v2 — exact shape

```python
class Approach(str, Enum):
    AGGRESSIVE = "aggressive"
    PATIENT = "patient"
    MIXED = "mixed"

class TargetFocus(str, Enum):
    THEIR_STARS = "their_stars"
    BALL_HOLDERS = "ball_holders"
    SPREAD = "spread"

class CatchPosture(str, Enum):
    GO_FOR_CATCHES = "go_for_catches"
    PLAY_SAFE = "play_safe"
    OPPORTUNISTIC = "opportunistic"

class OpeningRushCommit(str, Enum):
    ALL_IN = "all_in"
    BALANCED = "balanced"
    HOLD_BACK = "hold_back"

class OpeningRushTarget(str, Enum):
    NEAREST = "nearest"
    STRONGEST_SIDE = "strongest_side"
    CENTER = "center"

@dataclass(frozen=True)
class CoachPolicy:
    approach: Approach = Approach.MIXED
    target_focus: TargetFocus = TargetFocus.SPREAD
    catch_posture: CatchPosture = CatchPosture.OPPORTUNISTIC
    rush_commit: OpeningRushCommit = OpeningRushCommit.BALANCED
    rush_target: OpeningRushTarget = OpeningRushTarget.CENTER
```

Notes:

- "Opening Rush Plan" is **one knob in the UI** but **two enums in the
  data model** (commit + target). The UI presents commit and target as
  paired radios under one heading; persistence stores both.
- Defaults are the "balanced / spread / opportunistic / mixed" centroid —
  every existing curated team gets these defaults at load when no policy
  is declared, which keeps the rec-driver behavior in the centre of
  Plan A's tuned envelope until the player intentionally changes it.
- `as_dict()` returns string enum values (not floats). `from_dict()` is
  total: unknown strings raise `ValueError`.

### Old 8-field model — call-site audit

Every file that references the deleted fields gets rewritten in the same
phase. The implementation plan opens with a re-grep verification task,
identical in spirit to Plan B's opening audit. This table includes code,
frontend contracts, and tests/golden fixtures discovered by the 2026-05-22
handoff audit.

| File | Current usage | Class | Required change |
|---|---|---|---|
| `models.py` | Defines old 8-field `CoachPolicy` with `normalized()` / `as_dict()`. | Owner | Replace with v2 dataclass + enums + `as_dict()` / `from_dict()`. |
| `rec_engine.py` | Imports `CoachPolicy` but does not yet consume fields. | Load-bearing | Wire the four pinned decision points (see "Rec driver wiring"). |
| `engine.py` | Reads old fields in the generic engine. | Demoted | Per brief §5, the generic `MatchEngine` is slated for deletion. Plan C scope: stop reading old fields; if the module is not yet deleted (cleanup task), gate behind the existing skip-the-generic-engine path so nothing imports the dead branch at runtime. **Full deletion remains a separate cleanup task** — Plan C does not own it. |
| `official_engine.py`, `official_tactics.py` | Read old fields for USAD tactical heuristics. | Load-bearing | Map each old field's *semantic intent* to a v2 enum read (table below). USAD behavior must stay test-green. |
| `command_center.py` | `POLICY_KEYS`, `policy_label`, `policy_effect`, `policy_rows` use old field names for the CC pills. | Load-bearing | Rewrite against v2 enums. `policy_rows` returns one row per knob with the rec-league copy from the vocabulary glossary. |
| `dynasty_cli.py`, `recruitment_domain.py`, `matchup_details.py`, `replay_proof.py` | Read old fields for display / opponent-tactic strings. | Cosmetic-to-load-bearing | Replace with v2 reads via `policy_label` / `policy_effect`. |
| `randomizer.py`, `sample_data.py`, `setup_loader.py` | Generate / load CoachPolicy values for seed teams. | Load-bearing | Generate v2 enum values; loaders raise `ValueError` on old float-shaped payloads. |
| `persistence.py` | Serializes / deserializes CoachPolicy on save. | Load-bearing | Write v2 dict shape; on read, raise loud `ValueError` for legacy 8-float payloads with a message naming the version drift. |
| `server.py`, `web_status_service.py` | Surface policy in API responses. | Load-bearing | Emit v2 dict shape. Rewrite existing `/api/tactics` and command-center payloads; add `/api/match-week/policy` only as a compatibility alias if desired. |
| `match_orchestration.py`, `command_week_service.py`, `use_cases.py` | Weekly command plans apply `plan["tactics"]` into `club.coach_policy`; simulations consume those saved plans. | Load-bearing | Rewrite `plan["tactics"]` from float dict to v2 policy dict; keep AI/user plans applying through the same persistence boundary. |
| `ai_program_manager.py` | Builds AI weekly-plan tactics by calling `_policy_for_intent`. | Load-bearing | `_policy_for_intent` returns v2 enum strings; existing intent names map to centroid / aggressive / patient policy choices. |
| `league.py` | `Club.coach_policy` default factory. | Owner-adjacent | Should continue to default to `CoachPolicy()` v2 centroid; no field reads expected. |
| `official_resolution.py`, `official_actions.py` | Accept `CoachPolicy` and call official tactic helpers. | Load-bearing | No direct old-field reads after `official_tactics.py` mapping; update docstrings/comments if they imply float weighting. |
| `frontend/src/types.ts` | `CoachPolicy` is currently eight numeric fields; command center plan `tactics` uses that type. | Load-bearing | Replace with v2 string unions and update command-center/replay payload types. |
| `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` | Displays the old four tactic chips (`target_stars`, `catch_bias`, `risk_tolerance`, `tempo`). | Load-bearing | Replace old chips with `PolicyEditor`; save through the current command-center plan flow and/or rewritten tactics endpoint. |
| `tests/test_coach_policy.py`, `tests/test_command_center.py`, `tests/test_server.py`, `tests/test_official_tactics_and_resolution.py`, `tests/test_invariants.py`, `tests/test_regression.py`, `tests/test_voice_verdict.py`, `tests/test_replay_proof.py`, `tests/test_ai_program_manager.py`, persistence/recruitment tests | Assert old float behavior, payload shape, and golden strings. | Test contract | Rewrite or retire old-float tests in the same phase that changes the owning behavior. Keep deterministic branch tests; do not preserve old float semantics. |
| `tests/golden_logs/phase1_baseline.json` | Golden baseline contains old `CoachPolicy` float snapshots. | Fixture | Regenerate only if the suite still consumes it. If obsolete, document deletion or replacement in Phase 1. |

**USAD semantic-intent mapping** (used by `official_tactics.py`):

| Old field intent | v2 read |
|---|---|
| `risk_tolerance` high → throw at stars | `target_focus == THEIR_STARS` |
| `target_ball_holder` high | `target_focus == BALL_HOLDERS` |
| `tempo` high, `sync_throws` high | `approach == AGGRESSIVE` |
| `tempo` low | `approach == PATIENT` |
| `catch_bias` high | `catch_posture == GO_FOR_CATCHES` |
| `rush_frequency`, `rush_proximity` | `rush_commit`, `rush_target` |

This mapping is documented inline in `official_tactics.py` and pinned by
a USAD regression test that asserts the migrated heuristic produces the
same branch on equivalent inputs.

### Rec driver wiring — four decision points

| Knob | Where | Effect |
|---|---|---|
| `approach` | Per-tick throw cadence in `_select_throwers` | `AGGRESSIVE` raises throw eagerness (lowers the IQ-gate `throw_selection_iq` threshold by a pinned delta). `PATIENT` raises it. `MIXED` = current Plan A behavior. Composes with Plan B's `throw_selection_iq` modulation; the policy shifts the floor, the trait shifts the per-player gate. |
| `target_focus` | Target-selection inside `_select_throwers` | `THEIR_STARS` weights `overall_skill()` into the target score. `BALL_HOLDERS` weights `is_holding_ball`. `SPREAD` weights inverse-recent-target (avoid the player most recently targeted). |
| `catch_posture` | Per-defender response branch in `_resolve_throw` | Biases the Plan B three-way dodge/block/catch weighting. `GO_FOR_CATCHES` lifts catch weight; `PLAY_SAFE` lifts dodge weight; `OPPORTUNISTIC` is the Plan B baseline. Policy is a multiplicative bias on top of `catch_courage` — the trait dominates, the policy nudges. |
| `rush_commit` + `rush_target` | `RecTier1Driver._opening_rush` | `rush_commit` controls how many starters sprint vs hold-back at the baseline. `rush_target` controls which balls the sprinters prioritize. `_opening_rush` is a *new* method in the rec driver — Plan A's opening-rush handling is currently fixed-balanced; Plan C makes it policy-aware. |

The driver still uses Plan B's three new attributes the same way; the
policy adds a second axis of variation on top. Plan A's `fatigue`,
`flood_throws`, `stall_timer`, and `moment_events` primitives are
**untouched** by Plan C.

### Moment event → replay UI mapping

The replay surfaces every emitted moment. The mapping below pins which
moment kind drives which UI beat, what fields are read, and the
rec-league register the beat must use.

| MomentKind | UI beat in `ReplayTimeline` | Fields read | Rec register copy template |
|---|---|---|---|
| `DRAMATIC_CATCH` | Inline highlight card under the catching event; pulses `catcher_id` and `returning_player_id` chips. | `catcher_id`, `thrower_id`, `returning_player_id`, `active_count_a`, `active_count_b` | "**{catcher}** plucks it — **{returning}** is back on court." |
| `LATE_GAME_ESCAPE` | Banner above the timeline: "1 vs N". Persists until `survivor_id` goes out or wins. | `survivor_id`, `attacker_count` | "**{survivor}** is alone against {attacker_count}." |
| `ONE_V_ONE_FINALE` | Banner flips to "1 vs 1" with both names. | `player_a_id`, `player_b_id`, `tick_started` | "**{a}** vs **{b}** — last two standing." |
| `GASSED_COLLAPSE` | Tag attached to the elimination event for `player_id`. Shows fatigue %. | `player_id`, `fatigue_pct` | "**{player}** is gassed — body just gave out." |
| `FLOOD_THROW` | Inline pill on the tick row: "Flood — N throws". Hovering lists thrower names. | `thrower_team_id`, `thrower_ids` | "{team} sends a wall — {N} throws at once." |
| `COMEBACK` | Closing card at the bottom of the replay if present. | `team_id`, `deficit_at_low_point`, `catches_during_comeback` | "{team} were down {deficit} — clawed back with {catches} catches." |

Beats are inserted by the frontend, not the backend. The match payload
already carries `moment_events` after Plan A; Plan C's frontend work is
to index by `tick` and render at the matching event row.

Banners (`LATE_GAME_ESCAPE`, `ONE_V_ONE_FINALE`) and the closing card
(`COMEBACK`) are component-local; inline beats (`DRAMATIC_CATCH`,
`GASSED_COLLAPSE`, `FLOOD_THROW`) attach to the event row whose tick
matches the moment's tick.

### Voice modules — contract

`voice_verdict.py` (match outcome line) and `voice_aftermath.py`
(aftermath narrative) become **moment-aware**. Both modules accept the
same `AftermathContext` input shape:

```python
@dataclass(frozen=True)
class AftermathContext:
    match_result: MatchResult            # existing, untouched
    moment_events: tuple[MomentEvent, ...]   # from Plan A
    policy_team: CoachPolicy             # v2 — the user's chosen tactics
    policy_opponent: CoachPolicy         # v2 — opponent tactics
    tier: int                            # 1 for now; routes vocabulary
```

Both modules pick from the `moment_events` list — they do **not** invent
moments. Rules:

- `voice_verdict.render_headline` references the scoreline AND the
  single most-load-bearing moment if one exists. Priority order
  (high → low): `ONE_V_ONE_FINALE` (if winner is `player_a_id` or
  `player_b_id`), `COMEBACK`, `LATE_GAME_ESCAPE`, `DRAMATIC_CATCH`,
  `FLOOD_THROW`, `GASSED_COLLAPSE`. If no moments fired, the existing
  margin-aware copy from the 2026-05-22 product-coherence pass is the
  fallback.
- `voice_aftermath.render_body` produces 2–4 short paragraphs, each
  anchored on either a moment or a tactic. Tactics paragraphs reference
  the v2 policy values that produced the moments (e.g. `catch_posture
  == GO_FOR_CATCHES` paired with a `DRAMATIC_CATCH` moment ⇒ "you told
  them to go for catches and it paid off").
- Both modules route every user-visible string through
  `voice_register.tier1(...)` so the rec-league register is enforced in
  one place.

`voice_pregame.py` reads `policy_team` and emits one pre-match line:
"Today we're {approach}, focused on {target_focus}, and {catch_posture}."

`voice_playbyplay.py` is **not** rewritten by Plan C — it stays event-driven
as today. (Future Plan C+1 work.)

### Command Center pre-match UI

A new component `PolicyEditor.tsx` lives in
`frontend/src/components/match-week/command-center/`. It is rendered
inline in `PreSimDashboard` above `MatchCard`, replacing the old
"policy pills" row that displayed the 8 floats.

Layout (rec-register copy is illustrative; final strings come from the
glossary):

```
─── Today's plan ─────────────────────────────────────────────
Approach        [ Aggressive ] [ Patient ] [• Mixed ]
Target focus    [ Their stars ] [ Ball-holders ] [• Spread ]
Catch posture   [ Go for catches ] [ Play safe ] [• Opportunistic ]
Opening rush
   Commit       [ All in ] [• Balanced ] [ Hold back ]
   Target       [ Nearest ] [ Strongest side ] [• Center ]
──────────────────────────────────────────────────────────────
```

Behavior:

- Each row is a single-select chooser. Defaults are the "balanced
  centroid" listed above (• marks the default in the mockup).
- Choosing a value saves the v2 dict through the live command-center
  plan flow and the rewritten tactics persistence boundary. If the
  implementation adds `PUT /api/match-week/policy`, it must call the
  same service used by `/api/tactics` so the two routes cannot drift.
  Optimistic update; rollback on error.
- A one-line preview under each row reads from the glossary:
  "Aggressive — your team throws first, asks questions later."
- The component is keyboard-navigable (arrow keys move within a row,
  Tab moves between rows) and reads cleanly for the `ai-friendly-web-design`
  skill — proper roles, labels, and aria-checked states.

The old `policy_label` / `policy_effect` helpers move from the
generic-engine vocabulary to rec-league vocabulary at Tier 1; the
function signatures stay so callers don't change.

### Match Replay UI

`ReplayTimeline.tsx` is extended, not rewritten:

- Speed controls audit: a single `ReplaySpeedControl` component handles
  1x / 2x / 4x / instant. Today's speed UI is split across two places;
  consolidate to one.
- Per-event row gets an optional `moment` slot. Inline beats attach
  here.
- Two banner components (`LateGameBanner`, `OneVOneBanner`) render
  above the timeline when their moment is active.
- A `ComebackCard` renders at the bottom of the replay if a
  `Comeback` moment was emitted for either team.
- All copy routes through the `voice_register.tier1` JSON the backend
  emits — frontend never hard-codes vocabulary.

### Rec-league vocabulary glossary

`src/dodgeball_sim/voice_register.py` is new. It holds:

```python
TIER1_REGISTER = {
    "approach.aggressive": "Throw first, ask questions later",
    "approach.patient":    "Wait for the open shot",
    ...
    "moment.dramatic_catch.headline": "{catcher} plucks it",
    "moment.flood_throw.headline":    "{team} sends a wall",
    ...
}

def tier1(key: str, **fmt) -> str: ...
def for_tier(tier: int) -> dict[str, str]: ...
```

This module is the only place rec-league copy lives. Voice modules,
`policy_label`, and the frontend (via an `/api/voice-register/{tier}`
read on session start) all consume it. Future tiers add new keys
without touching consumer code.

## Data flow

```
Career creation
  Team           -> CoachPolicy(v2 defaults)
                              |
                              v
                Command Center PolicyEditor
                  save plan / tactics v2
                              |
                              v
                  team.policy = CoachPolicy(...)
                              |
                              v
              DriverMatchInput.policies[team_id]
                              |
                              v
                     RecTier1Driver
                  /     |     |       \
                 v      v     v        v
            approach  target catch   _opening_rush
                      _focus posture  (commit+target)
                              |
                              v
                       moment_events
                              |
            ┌─────────────────┼──────────────────┐
            v                 v                  v
   ReplayTimeline      voice_verdict      voice_aftermath
   (per-event beats +  (headline picks    (paragraphs anchored
    banners +          most load-bearing   on moments + tactics)
    closing card)      moment)
                              |
                              v
                  voice_register.tier1(key, **fmt)
                              |
                              v
                         user sees copy
```

## Error handling

- `CoachPolicy.from_dict` raises `ValueError` on unknown enum strings or
  on missing keys.
- `persistence.load_team_policy` raises `ValueError` with a message
  naming the legacy 8-float fields if it sees an old payload.
  Test: a fixture V11-shaped dict raises the documented error.
- `voice_register.tier1(key)` raises `KeyError` on unknown keys.
  Tested — silent fallback would mask a missing copy entry, which is a
  recognition-bug.
- API payload validation: rewritten `/api/tactics`, command-center plan
  save, and any `/api/match-week/policy` alias return HTTP 400 on unknown
  enum strings.

## Testing strategy

Behavioral tests use deterministic mocked / seeded RNG, matching
Plan B's discipline. Probabilistic "measurably more" assertions are
not accepted.

| Layer | Test |
|---|---|
| `CoachPolicy` v2 | Default constructor returns the centroid. `as_dict` round-trips. `from_dict` on a legacy 8-float dict raises `ValueError`. Unknown enum string raises. |
| Rec driver — `approach` | With ratings + `throw_selection_iq` fixed, `AGGRESSIVE` produces a throw in a tick where `PATIENT` does not (seeded RNG, exact branch). |
| Rec driver — `target_focus` | With two opponents (one high-OVR, one ball-holder, both equally targetable), `THEIR_STARS` selects the high-OVR target; `BALL_HOLDERS` selects the holder; `SPREAD` rotates. |
| Rec driver — `catch_posture` | Plan B's three-way response test extended: courage=50 + `GO_FOR_CATCHES` → catch branch; same courage + `PLAY_SAFE` → dodge branch. |
| Rec driver — `rush_commit` / `rush_target` | `_opening_rush` deterministic: with seeded RNG, `ALL_IN + CENTER` produces 6 sprinters all targeting center balls; `HOLD_BACK + NEAREST` produces 2 sprinters targeting the nearest balls per player. |
| Replay UI (frontend unit) | `ReplayTimeline` renders the inline beat for each of the six moment kinds against a fixture payload. Banner mounts when `LateGameEscape` present, unmounts when survivor changes. |
| Voice — `voice_verdict` | Priority ordering: a payload with `Comeback` + `DramaticCatch` returns the comeback headline. No-moments payload returns the existing margin-aware fallback (regression). |
| Voice — `voice_aftermath` | Paragraph count is 2–4. A `DRAMATIC_CATCH` + `GO_FOR_CATCHES` payload emits a paragraph that names both. No invention: with empty moment list, no moment-anchored paragraphs are emitted. |
| `voice_register.tier1` | Unknown key raises. All keys consumed by voice / replay / Command Center exist (snapshot test enumerates keys). |
| API | `/api/tactics`, command-center plan save, and any `/api/match-week/policy` alias accept v2 dicts and reject legacy float dicts with HTTP 400. |
| USAD regression | Existing `official_tactics.py` tests pass under the semantic-intent mapping. New test pins the mapping table: given old-field thresholds, the new heuristic chooses the documented branch. |
| Plan A regression gate | `tools/tier_1_sanity_probe.py` still emits all six moment kinds across 25 matches with a default v2 policy on both sides. With a non-default policy (e.g. `AGGRESSIVE / GO_FOR_CATCHES`), the probe still emits all six. |
| Playwright e2e | New career → Tier 1. Choose policy in Command Center. Sim match. Replay surfaces at least one inline beat. Aftermath references a moment and a tactic. Headline is non-empty rec-league copy. |

## Implementation phasing

The implementation plan will sequence five phases, each landing as one
reviewable change with green tests:

1. **`CoachPolicy` v2 + USAD semantic-intent mapping.** Model, audit
   table, USAD regression test. No rec-driver behavior change yet
   (driver still ignores policy as it does in Plan A). Sanity probe
   still green.
2. **Rec-driver wiring.** Four decision points. Branch tests per knob.
   Plan A's sanity probe still emits all six moments under default and
   non-default policies.
3. **Voice modules + `voice_register`.** `AftermathContext`,
   moment-aware verdict + aftermath, rec-league register module.
   Unit tests for priority ordering, no-moment fallback, no-invention.
4. **Frontend — Command Center `PolicyEditor` + replay beats.**
   `PolicyEditor.tsx`, `ReplayTimeline` beat slots, banners, closing
   card. Frontend unit tests. `npm run build` + `npm run lint` clean.
5. **Playwright e2e + STATUS/roadmap docs.** The end-to-end recognition
   walk. STATUS update; roadmap marks Plan C landed; Plan D unblocked.

Each phase is independently revertible — Phase 2 doesn't require
Phase 3, etc. — so review can happen per phase, matching the A/B cadence
that worked.

## Risks

- **Old-policy ripple wider than first audit suggested.** The 8-field
  model is referenced in 14 files (audit table) and via persisted save
  data. Mitigated by the opening re-grep verification task in the
  implementation plan and by the clean-break loader error.
- **Voice register over-engineering.** A glossary module is one
  abstraction more than the current "string literals in code" pattern.
  Justified by tier-2+ vocabulary swaps being on the roadmap; keep the
  module deliberately small (a dict + two helpers) to avoid premature
  framework-ization.
- **Frontend regressions in `ReplayTimeline`.** It's been touched in
  every UX wave. Mitigated by extending — new slots, not a rewrite —
  and by the Playwright e2e covering the inline beat render.
- **Moment-headline priority gets stale.** The priority order
  (`ONE_V_ONE_FINALE` → `COMEBACK` → ...) is a judgment call; if Plan D's
  probe reveals certain moments fire so often they become noise, the
  order may need to change. Out-of-scope for Plan C but flagged here.
- **USAD semantic-intent drift.** The mapping table compresses 8 floats
  to 5 enums; some USAD branches that depended on subtle blends (e.g.
  `risk_tolerance=0.4` vs `0.6`) will collapse to a single enum value.
  Pinned by a regression test that asserts the post-Plan-C USAD
  behavior on a fixed seed matches the pre-Plan-C behavior within a
  documented tolerance band; band width is set during Phase 1 and
  recorded inline in the test.
- **Audit-7.6 carry-in.** The product-coherence audit deferred 7.6 to
  Plan C by design (see STATUS.md line 22). Plan C resolves it as part
  of the voice / aftermath rewrite — the implementation plan will name
  the specific 7.6 acceptance criteria up front. (If 7.6 doesn't fit
  cleanly within the four phases above, it stays a follow-up rather
  than expanding Plan C scope.)

## Definition of done

- `CoachPolicy` v2 is the only `CoachPolicy` in the codebase. Old
  8-field references are removed from every file in the audit table.
- `RecTier1Driver` consumes the four knobs at the four pinned decision
  points. Per-knob branch tests pass.
- `OfficialDriver` accepts v2 policy without breaking USAD conformance.
  Semantic-intent mapping is documented and pinned by regression test.
- `voice_verdict` and `voice_aftermath` reference moment events and v2
  policy. `voice_pregame` emits one policy-aware line. No invented
  moments. Priority ordering and no-moment fallback are tested.
- `voice_register.tier1` is the single source of rec-league copy.
  Unknown keys raise.
- Command Center `PolicyEditor` is the canonical pre-match UI. The old
  policy-pill display is gone. API accepts v2 strings and rejects
  legacy float payloads.
- `ReplayTimeline` surfaces all six moment beats. Banners and closing
  card render correctly. A single `ReplaySpeedControl` exists.
- Playwright e2e walks the recognition path and asserts beats + voice
  copy render.
- Full pytest green. `tools/tier_1_sanity_probe.py` still emits all six
  moment kinds under default and non-default v2 policies. V11 / USAD
  conformance tests untouched.
- Frontend `npm run build` and `npm run lint` clean.
- `docs/STATUS.md` updated. `tier-1-roadmap.md` Plan C row marked
  landed. Plan D is the next strict step.
