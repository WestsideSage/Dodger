# V6 Player Identity and Development Loop Learnings

Date: 2026-05-05
Milestone: V6

## What Worked

V6 landed cleanly because it stayed narrow: player identity became a structural input to existing systems instead of a new parallel progression game. The archetype enum, Tactical IQ rating, lineup liability matrix, and development focus all attach to existing roster, command-center, engine, and development paths.

The useful pattern is "identity first, explanation second." V6 gives players tactical shape; V7 can now explain that shape in match evidence without inventing drama.

## Implementation Lessons

- Keep the event log canonical. The V7 viewer should derive proof from persisted `MatchEvent` payloads rather than creating a separate replay model that can drift.
- Liability mechanics must stay paired: a warning in the UI needs a measurable engine consequence, and an engine consequence needs visible context in the report.
- `CoachPolicy` and `PlayerArchetype` should remain compact. More knobs would dilute the proof loop before the existing ones are legible.
- Development math needs stored reps, not just end-of-season copy. The `minutes_played` gap was the main V6 data lesson and is now closed through extraction, persistence, aggregation, and server reconstruction.
- Frontend tables are trust surfaces. If headers and cells drift, later proof UX loses credibility even when the backend is correct.

## Verification Lessons

The focused V6 test file was valuable because it tests the milestone's integrity contract directly:

- Liability warnings exist.
- AI avoids bad fits where possible.
- Development focus changes growth outcomes.
- Liability fatigue penalties are measurable.

The remaining coverage gaps are equally important:

- No test currently proves replay payloads expose liability/tactic evidence in a stable, UI-friendly shape.
- No browser report currently proves a human can notice and understand V6 identity consequences end to end.

These become V7 gate work, not optional polish. The former `minutes_played` extraction and persistence gap is now covered in `tests/test_stats.py` and `tests/test_persistence.py`.

## V7 Guidance

V7 should build a proof loop, not a broadcast layer. The player should be able to answer:

- Who made the play?
- Why was that target selected?
- What were the odds and rolls?
- Did tactics matter?
- Did fatigue matter?
- Did a lineup liability matter?
- What should I adjust next week?

If the event payload does not contain enough evidence for one of those answers, V7 should say the evidence is unavailable rather than making up a causal explanation.

## Deferred Beyond V7

- Recruiting promises and program credibility belong in V8.
- Broadcast commentary belongs after proof is stable.
- Physics-heavy animation belongs after the event model can be trusted visually.
- Morale, personality, leadership, and chemistry systems should not be smuggled into V7.

## Closeout Note

V6 is closed with its two documented stabilization follow-ups completed before V7 feature implementation:

1. Real reps persistence through `minutes_played`.
2. Roster truth-table alignment before role/archetype evidence is reused in replay.

Verified during closeout:

- `/mnt/c/WINDOWS/py.exe -3 -m pytest tests/test_stats.py tests/test_persistence.py tests/test_server.py tests/test_command_center.py tests/test_v2a_scouting_persistence.py tests/test_v2b_recruitment_persistence.py tests/test_v6_player_identity.py -q`
- `npm run lint` from `frontend/` via Windows Node 24.15.0
- `npm run build` from `frontend/` via Windows Node 24.15.0
