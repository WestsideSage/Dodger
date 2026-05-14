# Offseason Beat Polish — Design Spec

**Date:** 2026-05-13  
**Scope:** Project A — everything in the offseason ceremony flow except the recruiting lifecycle (Project B, separate spec).  
**Status:** Approved, ready for implementation planning.

---

## Problem Statement

The offseason ceremony flow has ten fixed beats but several of them are broken or unpolished:

- Empty beats (no records broken, no retirements, no HOF inductees) still show and force the user to click through "nothing happened" screens every season.
- The Recap and Champion beats render as plain unformatted text with unprofessional shorthand (`pts=`, `diff=`, `*` marker).
- The Awards ceremony shows career stats instead of season stats, has broken icon/color keys, shows no award name label, and places the highest-prestige award (MVP) at the bottom of the completed list.
- The Development beat shows all 38 players across the whole league when only the player's own club is relevant.
- The Rookie Class Preview has confusing jargon and embeds a hardcoded "Continue to Recruitment Day." line in the body text.
- The Schedule beat defaults to the full league fixture list when the player only cares about their own games.
- A player sometimes appears on the awards list more than once in a way that may be a bug.

---

## Architecture: Dynamic Active Beat List

### Core change

At the end of `initialize_manager_offseason`, after records, HOF, and retirements are computed, a helper function evaluates which beats have content and writes the result to state as `offseason_active_beats_json`.

```python
# Example stored value when retirements happened but no records or HOF:
["champion", "recap", "awards", "development", "retirements",
 "rookie_class_preview", "recruitment", "schedule_reveal"]
```

**Always-included beats:**  
`champion`, `recap`, `awards`, `development`, `rookie_class_preview`, `recruitment`, `schedule_reveal`

**Conditionally-included beats:**
| Beat | Included when |
|---|---|
| `records_ratified` | At least one record broken this season |
| `hof_induction` | At least one player qualified for induction |
| `retirements` | At least one player retired |

### Beat serving and advancement

`build_beat_response` reads from `offseason_active_beats_json` instead of the full `OFFSEASON_CEREMONY_BEATS` constant. `beat_index` is relative to the active list. The frontend receives `total_beats` equal to the active beat count — progress dots always reflect reality.

**Legacy save fallback:** If `offseason_active_beats_json` is absent (old save file), fall back to the full 10-beat constant. No existing saves break.

### State machine unchanged

`CareerState` values (`SEASON_COMPLETE_OFFSEASON_BEAT`, `SEASON_COMPLETE_RECRUITMENT_PENDING`, `NEXT_SEASON_READY`) are unchanged. The recruitment gate checks beat key, not beat index, so it works correctly against any active list.

---

## Frontend Components

All new components live in `frontend/src/components/ceremonies/`. Updated components are in the same file as today.

### `ChampionReveal` (new)

Replaces the generic beat card for the `champion` beat. Uses the structured `champion` payload (already sent by the backend).

- Large team name as the headline
- W-L-D record and title count as clean stat chips below
- Gold accent border if the champion is the player's club
- No "Champion source" text anywhere — that field is removed from the backend body string

### `RecapStandings` (new)

Replaces the generic beat card for `recap`. Renders a proper standings table from the structured `standings` payload (already sent by the backend).

**Columns:** Rank · Club · W-L-D · Pts · Diff

- Player's club row: colored left border + slightly brighter text instead of `*` marker
- Number formatting: `18 pts`, `+12` — no `=` signs, no `pts=`, no `diff=`
- Elimination differential shown with explicit `+`/`-` sign

### `DevelopmentResults` (new)

Replaces the generic beat card for `development`.

- Shows **only the player club's players** — no other teams, no league-wide count
- Sorted by absolute delta descending (biggest movers first)
- OVR displayed as integers (rounded, no decimals)
- Delta displayed as `+2` or `-1` — no decimal places
- Each row: player name, OVR before → after, delta badge

**Backend change:** `build_beat_payload` for `development` filters `development_rows` to only the player club before building the payload. The payload shape gains a `players` array (filtered, rounded) rather than relying on the body string.

### `RookieClassPreview` (new)

Replaces the generic beat card for `rookie_class_preview`.

**Copy changes (backend `build_offseason_ceremony_beat`):**
- `"Top-band prospects (>= 70 OVR band low): N"` → `"Top prospects (70+ OVR): N"`
- `"Free-agent count: N"` → `"Veteran free agents available: N"` (clarifies these are not rookies)
- Storyline items render as `"- {sentence}"` inline, not split across two lines
- Remove hardcoded `"Continue to Recruitment Day."` entirely

Frontend renders the structured rookie preview payload cleanly with section headers.

### `AwardsNight` (updated)

Four changes to the existing component:

**1. Fix icon/color key mismatch**

Current keys (`top_rookie`, `best_defender`, `most_improved`) don't match actual award types. Replace with correct keys:

```ts
const AWARD_ICON: Record<string, string> = {
  mvp: '🏆',
  best_thrower: '🎯',
  best_catcher: '🤲',
  best_newcomer: '⚡',
};

const AWARD_COLOR: Record<string, string> = {
  mvp: '#f97316',
  best_thrower: '#3b82f6',
  best_catcher: '#10b981',
  best_newcomer: '#eab308',
};
```

**2. Add award name label**

Each card displays the human-readable award name above the player name:
- `mvp` → "MVP"
- `best_thrower` → "Best Thrower"
- `best_catcher` → "Best Catcher"
- `best_newcomer` → "Best Newcomer"

**3. Season stats instead of career stats**

Each award card shows the season stat relevant to that award as the primary figure. Career total moves to a dimmer secondary line.

| Award | Primary stat | Label |
|---|---|---|
| MVP | season total eliminations | "N season elims" |
| Best Thrower | season eliminations by throw | "N throw elims" |
| Best Catcher | season catches made | "N catches" |
| Best Newcomer | season total eliminations | "N season elims" |

**Backend payload change:** `build_beat_payload` for `awards` calls `fetch_season_player_stats` and attaches `season_stat: int` and `season_stat_label: str` per award entry. The `career_elims` field is renamed `career_stat` for clarity.

**TypeScript type update:**
```ts
export interface OffseasonAward {
  player_name: string;
  club_name: string;
  award_type: string;
  season_stat: number;
  season_stat_label: string;
  career_stat: number;
  ovr: number;
}
```

**4. Sort order — MVP pinned at top**

Awards sorted descending by prestige so MVP is at index 0:

```python
_AWARD_PRESTIGE = {
    "mvp": 3,
    "best_thrower": 2,
    "best_catcher": 1,
    "best_newcomer": 0,
}
sorted_awards = sorted(awards, key=lambda a: _AWARD_PRESTIGE.get(a.award_type, -1), reverse=True)
```

In the ceremony, MVP is revealed first at stage 1 (highlighted). Subsequent awards appear below it. When the ceremony completes, MVP is at the top of the stack, always highlighted. `isLatest` logic remains `i === stage - 1` — the last-revealed item gets the active highlight as the ceremony progresses, but MVP stays at position 0 as the anchor.

### `NewSeasonEve` (updated)

Add a "My Games / All Games" toggle above the fixture list.

- Default: show only fixtures where `is_player_match === true`
- Toggle to "All Games" reveals full fixture list with player matches still highlighted in orange
- Toggle state is local UI state only — no backend change needed

---

## Bug Fixes

### Awards duplicate player investigation

The `season_awards` table enforces `PRIMARY KEY (season_id, award_type)` so a player can legitimately win multiple awards (e.g., MVP + Best Thrower). With award names now displayed, multi-award winners are readable and not confusing.

Investigation targets:
1. `compute_season_awards` — audit for cases where the same player wins awards that should be distinct (e.g., Best Thrower and Best Catcher simultaneously). Add assertion: no two entries in the returned list share the same `player_id` unless they are truly different `award_type` values.
2. `load_awards` — audit for duplicate rows returned by the query. Add a dedup pass.
3. Add a test asserting no duplicate `(season_id, player_id, award_type)` tuples are returned by `load_awards` after a full season simulation.

### Champion body copy

Remove `"Champion source: Playoff Final"` from `build_offseason_ceremony_beat`. The body string for `champion` becomes a minimal fallback (e.g., `"Champion: {club_name}"`) since `ChampionReveal` uses the structured payload directly.

---

## What Is NOT in Scope

- Recruiting lifecycle redesign (Project B — separate spec)
- Any changes to `CareerState` values or the state machine transition logic
- New award types (OPOY, DPOY, Rookie of the Year as distinct awards — those belong in a future identity/story layer phase)
- Playoff or tournament bracket changes
- Any Tkinter GUI (`manager_gui.py`) updates — web app only

---

## File Change Summary

| File | Change |
|---|---|
| `src/dodgeball_sim/offseason_ceremony.py` | Add `compute_active_beats()`, call at end of `initialize_manager_offseason`, fix champion body copy, fix rookie preview copy |
| `src/dodgeball_sim/offseason_presentation.py` | Filter dev rows to player club, add season stats to awards payload, reverse award prestige sort, add `players` array to development payload |
| `src/dodgeball_sim/offseason_service.py` | Read active beats from state in `build_beat_response`, fallback to full constant |
| `frontend/src/components/ceremonies/Ceremonies.tsx` | Fix `AWARD_ICON`/`AWARD_COLOR`, add award name label, season stats, sort fix, NewSeasonEve toggle |
| `frontend/src/components/ceremonies/` (new files) | `ChampionReveal.tsx`, `RecapStandings.tsx`, `DevelopmentResults.tsx`, `RookieClassPreview.tsx` |
| `frontend/src/components/Offseason.tsx` | Route `champion`, `recap`, `development`, `rookie_class_preview` beats to their new components |
| `frontend/src/types.ts` | Update `OffseasonAward` interface; add payload types for new components |
| `src/dodgeball_sim/awards.py` | Audit and fix duplicate award bug |
| `tests/` | New test for no duplicate award tuples |
