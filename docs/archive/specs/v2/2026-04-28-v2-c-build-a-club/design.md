# V2-C — Build a Club Path — Design Spec

**Date:** 2026-04-28
**Status:** Design approved, ready for implementation planning
**Scope:** Activate the disabled Build a Club career path as an expansion-franchise start with custom identity, a deterministic weak roster, honest recruitment tradeoffs, and no hidden match assistance.

---

## 0. Relation to Prior Specs

This document is the canonical V2-C spec. It depends on:

- V2-A scouting, which supplies the hidden-gem information loop.
- V2-B recruitment, which supplies contested signings and public/private prospect evaluation.
- V1 Manager Mode, which already has Career Path Picker, curated club takeover, Manager Mode persistence, schedule generation, and off-season flow.

V2-C explicitly does not cover:

- Full logo or uniform creator.
- Hidden expansion-club stat boosts.
- New match-resolution rules.
- Playoffs.
- Scout hiring, firing, aging, or multi-scout stacking.
- Mid-season free-agent market beyond what V2-B provides.

---

## 1. Goals

1. **A real expansion fantasy.** Build a custom club, start weaker than the league, and climb through scouting and recruitment.
2. **Honest difficulty.** The club receives no secret match boosts or rubber-band help.
3. **Distinct from Take Over.** Take Over means inheriting a stable club. Build a Club means creating identity and surviving a harder roster start.
4. **Visible tradeoffs.** Expansion has more roster opportunity but lower prestige and less contender appeal in recruitment.
5. **Deterministic creation.** Same inputs and seed produce the same club id, roster, schedule, and initial state.

---

## 2. Architecture

### 2.1 Career path state

Persist:

- `career_path = take_over | build_club`,
- selected custom `club_id`,
- expansion origin metadata,
- creation season,
- identity payload.

This can live in `dynasty_state` for simple keys, with an additive `expansion_club` table if implementation needs a structured record.

### 2.2 Club identity

Use existing `Club` identity fields:

- name,
- primary color,
- secondary color,
- venue name,
- tagline.

V2-C adds only the editor and persistence path needed to create those fields from user input.

### 2.3 Expansion roster

Generate a legal roster with:

- deterministic seed: `derive_seed(root_seed, "expansion_roster", club_id)`,
- low-to-mid ratings,
- flawed specialists,
- normal traits and development rules,
- valid default lineup.

The roster should be weaker on average than curated clubs, but every rating must be visible and real.

Initial tuning target: for a fixed root seed, the expansion roster's mean top-six OVR should be at least 8 points and at most 16 points below the mean top-six OVR of the curated league clubs. This keeps the start meaningfully difficult without making the roster noncompetitive by construction.

---

## 3. Onboarding Flow

1. Splash remains unchanged.
2. Career Path Picker activates Build a Club.
3. Build editor collects club name, short name or generated id preview, colors, venue, region, and tagline.
4. Confirmation explains: expansion roster, low expectations, scouting-forward rebuild, no hidden boosts.
5. Career initializer creates curated league plus expansion club, roster, lineup, scouting state, recruitment profile, and schedule.
6. Hub opens on Season 1 Week 1.

---

## 4. Schedule Impact

If adding the expansion club creates an odd club count, byes are legal V2-C behavior.

The scheduler already has internal `__bye__` placeholder handling for odd club counts. V2-C's work is to exercise that path end-to-end in Manager Mode, render bye weeks clearly, and remove or update the stale scheduler docstring comment that says odd-club byes are not implemented.

Requirements:

- scheduler output remains deterministic,
- Hub renders bye weeks clearly,
- schedule rows identify byes or weeks with no user match,
- career state advances through bye weeks without looking stuck.

V2-C does not redesign league format beyond this bye support.

---

## 5. Recruitment Impact

Expansion club uses V2-B recruitment rules with visible profile differences:

- more available roster spots,
- lower prestige / contender appeal,
- possible higher playing-time pitch,
- same public/private information rules as everyone else.

The expansion club does not receive secret prospect truth.

---

## 6. UI Surfaces

### 6.1 Career Path Picker

Build a Club tile becomes active and routes to the editor. Take Over remains unchanged.

### 6.2 Build Editor

Compact operational form:

- club name,
- id/short name preview,
- primary and secondary color,
- venue,
- region,
- tagline.

Validation prevents empty names, duplicate ids, invalid color values, and unreadable identity defaults.

### 6.3 Expansion Welcome

One confirmation beat after creation. It shows roster expectation and first-match context. It must not be a marketing landing page.

---

## 7. Testing

Required coverage:

- Build-a-club initialization persists custom identity.
- Generated expansion club id is stable and collision-safe.
- Expansion roster is deterministic, legal, and weaker on average than curated rosters.
- Expansion roster top-six mean OVR lands 8 to 16 points below the curated-club top-six mean for fixed seed fixtures.
- Default lineup is saved.
- Scouting and recruitment initialization are idempotent.
- Odd-club schedule with byes is deterministic.
- Scheduler documentation accurately describes implemented bye behavior.
- Hub handles bye week.
- Take Over path is unchanged.
- Phase 1 golden regression remains unchanged.

---

## 8. Acceptance Criteria

V2-C ships when:

1. Build a Club is active from Career Path Picker.
2. User can create a custom expansion club identity.
3. Expansion career persists and resumes.
4. Expansion roster is legal, deterministic, and 8 to 16 top-six OVR points weaker than curated-club average without hidden match modifiers.
5. Schedule and Hub support byes if league count is odd.
6. V2-B recruitment treats expansion through visible profile inputs only.
7. Take Over career path remains unchanged.

---

*End of V2-C Build a Club Path design spec.*
