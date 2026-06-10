# Watchable Match Replay Research

Status: research/adaptation draft, 2026-06-09.

Numbering note (2026-06-09 product-director pass): the "V16A" label used for
the intent-frames slice in this draft is provisional and now collides with
the planned V16 Contested Offseason milestone
(`docs/specs/2026-06-09-v16-contested-offseason-sprint-plan.md`). Renumber
this work when (if) it is activated as a milestone spec.

Scope: adapt the Teamfight Manager / Teamfight Manager 2 watched-match pattern to the current Dodgeball Manager codebase. This is not an implementation plan yet. It identifies the replay contract, code seams, risks, and the first credible milestone slice.

## Bottom Line

Teamfight Manager works as a watched sim because the match is readable before the result lands. TFM1 gets there with compact champion identities, short deathmatch sets, and strategy controls that make a manager instruction visible during combat. TFM2 moves the same idea toward a MOBA decision sim: player stats shape AI decision quality and control rather than simply multiplying damage.

Dodger should not copy MOBA lanes or champion kits. The transferable pattern is:

`manager choice -> visible player intent -> telegraph -> commitment -> consequence -> film-review lesson`

The current Dodger replay already has a strong proof foundation. `match_replay_payload()` reads persisted match events, enriches them with labels, proof events, moment events, official state, broadcast frames, and report evidence. `replay_proof.py` reconstructs key plays, survivor state, tactics proof, fatigue proof, liability proof, and command-plan proof from saved event truth. The frontend `MatchReplay` renders a replay cockpit, court, event log, scoreline, official rules panel, and current-event card.

The missing transformative layer is anticipation. The viewer mostly sees a throw after the engine already chose it. To become Teamfight-level watchable, Dodger needs a replay grammar that shows what a player is trying to do before the ball result resolves.

## External Reference Check

These source-backed points matter for Dodger:

- TFM1's official Steam page describes a 1-minute deathmatch match process, pick/ban, unique champion characteristics, one cooldown skill, one once-per-set ultimate, and player attack/defense/champion skill/trait differences. This supports the "small readable hero-combat diorama" reading, not a claim about source code internals. Source: https://store.steampowered.com/app/1372810/Teamfight_Manager/
- TFM1 patch 1.1 added strategy controls for ultimate timing, linked ultimates, and distance between allies. That is the key manager-to-watch bridge: the player can recognize an instruction in the watched fight. Source: https://steamdb.info/patchnotes/6460214/
- TFM2's official Steam page describes a MOBA-style map with Top, Jungle, Mid, Bottom, Support, Nexus destruction, refined team/individual tactics, and says player stats affect AI-driven decision-making and control rather than direct damage values. Source: https://store.steampowered.com/app/3009300/Teamfight_Manager_2/
- TFM2 patch notes show ongoing match-engine work on laning positioning and recall/buy decisions, and warn that match engine changes can make older replays differ from recorded results. This is a caution for Dodger: never rerun the engine to render the replay. Source: https://steamcommunity.com/app/3009300/allnews/?l=english
- Community discussion around TFM2 repeatedly flags non-human AI failures such as units wandering, re-entering fights at low HP, ignoring objectives, or running in circles. Treat that as anecdotal but useful product evidence: a watched sim can contain mistakes, but they must look like plausible player mistakes. Source: https://steamcommunity.com/app/3009300/discussions/0/654856256529562927/

## Current Dodger Baseline

### What already maps well

- `PlayerRatings` already separates performance stats from identity-like behavior. Accuracy, power, dodge, catch, stamina, tactical IQ, catch courage, throw selection IQ, and conditioning curve exist in `src/dodgeball_sim/models.py`.
- `CoachPolicy` already exposes readable manager knobs: approach, target focus, catch posture, rush commit, and rush target.
- `RecTier1Driver` already uses behavior stats in decisions, not only outcome numbers. Examples: throw selection IQ gates whether a player throws, catch courage plus catch posture influence catch/block/dodge response, and target focus affects target scoring.
- `moment_events.py` already defines recognition moments: dramatic catch, late-game escape, one-v-one finale, gassed collapse, flood throw, and comeback.
- `replay_service.py` already keeps the correct source-of-truth shape: persisted events first, then replay proof, moments, official state, broadcast frame, playoff frame, commentary inserts, and report lanes.
- `replay_proof.py` already converts saved events into a stable proof view model with decision, tactic, fatigue, liability, and score-state sections.
- `MatchReplay.tsx` already gives the player an actual watched surface: scoreboard, official rules panel, court, possession strip, transport controls, current-event card, and event log.

### What is still too thin

- Replay events are throw-centric. The viewer sees thrower, target, resolution, odds, rolls, and proof text, but not a pre-throw intent state.
- The rec driver saves useful context, but it is still mostly evidence after a throw. It does not persist a first-class "this player is baiting / hunting / protecting / holding / panicking" contract.
- The official path is thinner than the rec path. `official_translator.py` maps official sequence finals to generic throw events with mostly empty context, while official rules state rides separately in `official_state`.
- Moment events are recognition events, not intent events. They identify a dramatic result, not the player decision cycle that made the moment watchable.
- The replay court uses fixed 2-column formations and throw lines. That is a good base for a diorama, but it does not yet show pressure, spacing, retreat, baiting, recovery, or ball retrieval as court states.
- The frontend auto-advances by proof event. It does not have a telegraph frame, commitment frame, consequence frame, and reset frame for a single play.

## Design Principle For Dodger

Dodger's watchable match should be a court-reading simulator:

`six dodgeball players with roles, instincts, courage, reflexes, and teamwork try to read the court correctly`

The engine does not need continuous physics first. It needs discrete, truthful states the player can read:

- Pressuring: stepping forward to force a reaction.
- Hunting: focusing a vulnerable target.
- Baiting: inviting a throw to create a catch chance.
- Holding: waiting because the shot quality is poor.
- Resetting: recovering formation or fatigue after a sequence.
- Covering: protecting a teammate or discouraging a focus throw.
- Retrieving: prioritizing ball control.
- Panicking: low-quality release under clock, pressure, or fatigue.
- Overcommitting: plausible human mistake caused by aggression, low discipline, or bad read.
- Freezing: plausible human mistake caused by poor awareness, low tactical IQ, or pressure.

Every visible action should have:

`perceive -> choose intent -> telegraph -> commit -> resolve -> reset`

## Proposed Replay Contract

Keep the existing `MatchEvent` stream canonical. Do not let the renderer decide outcomes. Add a replay-specific view model that expands saved match truth into watchable frames.

### 1. Intent Snapshot

Drivers should persist an intent snapshot at the moment a player/team decision is made. It can live inside event context at first, then graduate to a shared contract module if both rec and official drivers converge.

Suggested shape:

```python
{
    "intent_kind": "pressure" | "hunt" | "bait" | "hold" | "retrieve" | "reset" | "cover" | "panic_throw",
    "actor_id": "player_id",
    "team_id": "club_id",
    "target_id": "player_id | None",
    "cause_codes": ["policy:aggressive", "target:vulnerable", "clock:burden", "fatigue:high"],
    "rating_inputs": {
        "tactical_iq": 68,
        "throw_selection_iq": 74,
        "catch_courage": 61,
        "conditioning_curve": 55
    },
    "policy_snapshot": {...},
    "confidence": 0.72,
    "mistake_kind": None | "overcommit" | "late_read" | "panic_release"
}
```

Rules:

- Intent snapshots must be persisted at simulation time or derived deterministically from persisted context.
- They must never rerun the engine.
- They must not claim a cause unless the event context contains the cause.
- "Mistake" labels must be conservative. Prefer "low-quality release under pressure" over "AI bug" or decorative blame.

### 2. Watch Frame

`replay_proof.py` or a new `replay_watch.py` should expand each proof event into 2-4 frames:

```python
{
    "frame_id": "match_1:throw_12:telegraph",
    "event_index": 12,
    "phase": "telegraph" | "commit" | "resolve" | "reset",
    "tick": 42,
    "primary_actor_id": "p1",
    "target_id": "p8",
    "intent_kind": "hunt",
    "headline": "Gray steps in to hunt the weak-side dodger.",
    "proof_tags": ["TARGET FOCUS", "PRESSURE", "TACTICAL IQ"],
    "court_marks": [
        {"kind": "focus", "player_id": "p8"},
        {"kind": "step_forward", "player_id": "p1"},
        {"kind": "threat_lane", "from": "p1", "to": "p8"}
    ],
    "outcome_ref": {"resolution": "hit", "score_delta": "Away -1"}
}
```

Rules:

- The first phase makes intent readable.
- The second phase shows commitment.
- The third phase shows the outcome.
- The fourth phase shows reset when there is meaningful state movement: eliminated player, returned player, ball side change, fatigue recovery, burden/clock state, or formation recovery.

### 3. Court Marks Instead Of Physics

Do not start with continuous animation. Start with discrete court marks:

- step forward
- retreat
- focus target
- catch-ready stance
- dodge lane
- ball-control side
- pressure lane
- teammate covered
- fatigue warning
- burden/clock warning

This matches the current fixed court and avoids building a physics engine before the data contract exists.

## Recommended Milestone Strategy

### Option A: Intent Overlay Only

Add intent labels and proof copy to current proof events. This is the safest first improvement, but it will still feel like annotated play-by-play rather than a watched match.

Pros: low risk, mostly backend proof and copy.
Cons: limited transformation, no telegraph/commit rhythm.

### Option B: Watch Frame Model

Add intent snapshots, build `watch_frames` from persisted events, and update `MatchReplay` to step through frames instead of only throw events.

Pros: directly targets watchability; still preserves event truth; gives design room for telegraph and consequence.
Cons: requires backend contract, frontend type changes, and tests across rec/official paths.

Recommendation: choose Option B, but implement it in two slices. First ship frame data and a modest UI treatment. Then improve court marks and pacing.

### Option C: Full Court Simulation Rebuild

Build player positions, ball ownership, movement choices, retrieval, coverage, and pathing as a full simulation.

Pros: highest ceiling.
Cons: too large and risky before the intent/frame contract exists. This can easily create TFM2-style non-human failures if movement looks broken.

Recommendation: do not start here.

## First Implementation Slice

Working title: V16A Watchable Replay Intent Frames.

Thesis: after simulating a match, the player can watch not just what happened, but what each key actor appeared to be trying to do before the result landed.

Files likely involved:

- `src/dodgeball_sim/rec_engine.py`: emit intent snapshots for thrower selection, target selection, catch response, panic/headshot, fatigue pressure, synchronized attacks, and rush state.
- `src/dodgeball_sim/official_tactics.py`: return scored thrower/target/catch decision metadata that official replay can preserve.
- `src/dodgeball_sim/official_translator.py`: preserve official decision context, probabilities, rule pressure, and replay summary instead of translating sequence finals into mostly empty throw context.
- `src/dodgeball_sim/replay_proof.py` or new `src/dodgeball_sim/replay_watch.py`: build `watch_frames` from saved proof events and intent snapshots.
- `src/dodgeball_sim/replay_service.py`: include `watch_frames` in `match_replay_payload()`.
- `src/dodgeball_sim/server.py`: type the response field.
- `frontend/src/types.ts`: add `ReplayWatchFrame`, `ReplayCourtMark`, and optional `watch_frames`.
- `frontend/src/components/MatchReplay.tsx`: drive the main replay stage from frames when present; keep proof events as fallback.
- `frontend/src/index.css`: add stable desktop-first layout for frame headlines, phase rail, and court marks.
- Tests: `tests/test_replay_watch.py`, `tests/test_replay_proof.py`, `tests/test_official_translator.py`, `tests/test_server.py`, and a focused Playwright replay spec.

Acceptance criteria:

- Existing replay payloads still work when `watch_frames` is absent.
- Rec matches expose at least telegraph, commit, resolve frames for throw events with saved decision context.
- Official matches expose enough intent context that official replay is not a context-empty downgrade.
- The renderer never changes outcomes and never reruns the engine.
- Every visible intent sentence is backed by saved event context, policy, ratings, clock/burden, fatigue, or score state.
- "Mistake" labels only appear when backed by explicit low-IQ/pressure/fatigue/clock/courage conditions.
- Targeted Python tests prove frame construction is deterministic and event-derived.
- Frontend build/lint pass.
- Browser verification at 1440x900, 1366x768, 1280x720, and 1920x1080 confirms no overlap, no blank court, and readable frame text.

## Second Slice

Working title: V16B Court Reading Diorama.

Thesis: the court view itself shows pressure and player reads, not only a line from thrower to target.

Add court marks for:

- threat lane
- focus target
- catch-ready stance
- dodge lane
- retreat / reset
- ball-control side
- low-stamina warning
- synchronized pressure

This should still use discrete marks and stable slots. No freeform pathfinding, no collision physics, and no live outcome math in React.

## Third Slice

Working title: V16C Film Review.

Thesis: post-match review groups repeated player behaviors into coachable lessons.

Examples:

- "Our captain hunted the ball-holder three times; two became outs."
- "The rival catcher baited two throws and turned one into a return."
- "Late fatigue turned two safe throws into poor releases."
- "Our aggressive rush produced early pressure but left the weak-side dodger exposed."

This should link each lesson to watch frames. It must not invent personality or blame; it should cite frames and proof tags.

## Risks And Guardrails

- Do not create a second truth source. The event log remains canon.
- Do not compute old replays by rerunning the engine. TFM2 patch notes explicitly show why that is dangerous: engine changes can make old replays diverge from recorded results.
- Do not let React decide outcomes, target choices, or player mistakes.
- Do not over-label ordinary throws. If everything is dramatic, nothing is readable.
- Do not ship decorative intent. If "baiting" does not affect catch decision, target choice, or proof framing, do not call it baiting.
- Do not make official replay worse than rec replay. The official path needs comparable decision context, or the default official career will feel less watchable than the rec architecture.
- Do not optimize for mobile. The repo is desktop-first; verify the desktop matrix.
- Avoid continuous pathing until discrete court marks are working and trusted.

## Why This Fits Dodger

The codebase already has the important foundations:

- deterministic event logs
- separate behavior traits
- policy-driven decisions
- proof events
- moment events
- official replay state
- browser replay surface

The TFM-inspired change is not "more animation." It is a stricter replay grammar:

`show the player's read, show the commitment, show the consequence, then let the manager learn from it`

That is the path from "proof timeline" to "watched match."

