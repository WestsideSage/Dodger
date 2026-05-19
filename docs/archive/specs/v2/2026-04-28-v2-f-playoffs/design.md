# V2-F — Playoffs — Design Spec

**Date:** 2026-04-28
**Status:** Design approved, ready for implementation planning
**Scope:** Add league playoff bracket support to Manager Mode, materialize playoff matches into the normal match flow, and change champion source-of-truth from regular-season standings leader to persisted playoff outcome.

---

## 0. Relation to Prior Specs

This document is the canonical V2-F spec. It follows V1 Manager Mode's regular-season-only design and supersedes the V1 scheduler summary that reported no playoffs.

V2-F should be implemented before V2-E so off-season beats can read the correct champion.

V2-F explicitly does not cover:

- Cup tournaments.
- Best-of series.
- Random tiebreakers.
- Recruitment, scouting, Build a Club, or CoachPolicy changes.
- Rich broadcast presentation beyond readable bracket and schedule state.

---

## 1. Goals

1. Add a deterministic top-4 playoff bracket.
2. Keep regular-season schedule generation unchanged.
3. Materialize playoff matches into existing scheduled-match flow.
4. Persist bracket metadata and final season outcome.
5. Make off-season champion beat read champion outcome, not standings leader.
6. Preserve old-save fallback for regular-season-only saves.

---

## 2. Bracket Model

V2-F scope is a top-4 single-elimination bracket:

- Semifinal 1: seed 1 vs seed 4.
- Semifinal 2: seed 2 vs seed 3.
- Final: semifinal winners.

Seeding uses existing standings order:

1. points descending,
2. elimination differential descending,
3. club id ascending.

No random tiebreakers.

---

## 3. Scheduling

Regular season remains round robin.

After all regular-season matches are complete:

1. Compute final regular-season standings.
2. Persist bracket seeds.
3. Materialize semifinal `ScheduledMatch` rows after the regular-season final week.
4. Higher seed hosts.
5. When semifinals are complete, materialize the final.
6. When final is complete, persist season outcome.

Stable match id pattern:

- `season_id_p_r1_m1`
- `season_id_p_r1_m2`
- `season_id_p_final`

Materialization must be idempotent. Save/resume cannot duplicate semifinals or finals.

---

## 4. Persistence

Prefer additive tables:

```
playoff_brackets(
    season_id TEXT PRIMARY KEY,
    format TEXT,
    seeds_json TEXT,
    rounds_json TEXT,
    status TEXT
)

season_outcomes(
    season_id TEXT PRIMARY KEY,
    champion_club_id TEXT,
    champion_source TEXT,       -- playoff_final | regular_season
    final_match_id TEXT,
    runner_up_club_id TEXT,
    payload_json TEXT
)
```

Keep `scheduled_matches` as the playable queue. Add minimal stage metadata if needed, or derive stage from bracket metadata and match id.

Old saves without `season_outcomes` fall back to standings leader.

Migration rule: seasons already in progress when V2-F first loads remain on their original no-playoff format. Playoffs apply to seasons created after V2-F is active. This avoids injecting a bracket into a partially completed regular season with no recorded season-format decision.

---

## 5. Season Flow

Season is complete only when:

- no regular-season matches are pending,
- playoff bracket exists if the season format has playoffs,
- all required playoff matches are complete,
- `season_outcome` is persisted.

The app must not transition into off-season immediately after regular-season completion when playoffs are enabled.

---

## 6. UI

Hub:

- shows Regular Season, Playoff Semifinal, Playoff Final, or Champion Crowned state.

League screen:

- adds Playoffs tab or bracket section,
- schedule rows show stage labels,
- future playoff slots can show placeholders until teams are known.

Off-season Champion beat:

- reads `season_outcome`,
- shows playoff champion,
- final opponent/result,
- regular-season seed,
- fallback label for old no-playoff seasons.

---

## 7. Testing

Required coverage:

- Deterministic top-4 bracket generation.
- Tie-stable seeding.
- Higher seed hosts.
- Semifinals materialize once.
- Final materializes once after semifinal winners.
- Season is not complete after regular season if playoffs are pending.
- Final winner persists as `season_outcome`.
- Off-season champion uses playoff outcome.
- Old regular-season-only saves still render champion.
- In-flight regular-season saves created before V2-F do not receive retroactive playoff brackets.
- Schedule rows and Hub labels show playoff stage.

---

## 8. Acceptance Criteria

V2-F ships when:

1. Manager Mode seasons create top-4 playoffs after regular season.
2. User can play through semifinals and final in the normal match flow.
3. Bracket and playoff matches persist across save/resume.
4. Champion comes from playoff final.
5. Off-season does not begin until playoff final is complete.
6. Regular-season-only old saves and in-flight pre-V2-F seasons still work without retroactive brackets.

---

*End of V2-F Playoffs design spec.*
