# 2026-04-28 V2 Playthrough QA Report

## Test Environment

- **Platform**: Windows 11 Pro 10.0.26200, Python 3.x
- **Working directory**: `C:\GPT5-Projects\Dodgeball Simulator`
- **Test suite**: `python -m pytest -q` â†’ **303 passed in 0.83s**
- **Database**: Fresh in-memory SQLite for each test phase (no existing `dodgeball_manager.db` present; previous saves exist as `.old.db` and `.qa-backup.db`)
- **QA method**: Programmatic (API-level). GUI/Tkinter widgets cannot be driven headlessly. All helper functions, domain logic, and persistence are tested directly. GUI paths are covered by code inspection.

## Save Setup

All programmatic tests used:

```python
conn = sqlite3.connect(':memory:')
conn.row_factory = sqlite3.Row
create_schema(conn)
cursor = initialize_manager_career(conn, 'aurora', root_seed=20260426)
```

Build a Club tests used `root_seed=20260428` and club_name `Portland Breakers`.

Simulation commands:

```
python -m pytest -q                          # full test suite
python qa_phase3.py                          # playoffs + offseason
python qa_phase4.py                          # scouting + recruitment + Build a Club
```

---

## Feature Checklist

| # | Feature | Result | Notes |
|---|---------|--------|-------|
| 1 | pytest suite (303 tests) | **Pass** | 303 passed, 0 failed |
| 2 | Fresh Take Over career init | **Pass** | 6 clubs, aurora selected, cursor = PRE_MATCH |
| 3 | Season format = top4_single_elimination | **Pass** | Persisted correctly via `load_season_format` |
| 4 | Splash screen (visual) | **Not tested** | GUI only â€” no headless Tkinter |
| 5 | Club picker (curated clubs displayed) | **Not tested** | GUI only |
| 6 | New Career â†’ Hub transition | **Pass** | `initialize_manager_career` returns correct cursor, load_clubs has 6 clubs |
| 7 | Hub: standings panel | **Pass** | `_standings_with_all_clubs` + `load_standings` work correctly |
| 8 | Hub: next-match panel (shows opponent) | **Pass** | `_next_user_match` returns correct upcoming match |
| 9 | Hub: league wire panel | **Pass** | `build_wire_items` returns 0 items pre-season, fills with match results post-play |
| 10 | Hub: awards in wire text | **Partial** | Awards render correctly but show `player_id` (e.g. `aurora_3`) not player name â€” see BUG-002 |
| 11 | Roster: 6 players per club | **Pass** | All 6 clubs have 6-player rosters, correct `club_id` |
| 12 | Roster: default lineup persisted | **Pass** | 6 player IDs for all clubs |
| 13 | Tactics: CoachPolicy 8 fields (V2-D) | **Pass** | All 8 fields present: `target_stars, target_ball_holder, risk_tolerance, sync_throws, rush_frequency, rush_proximity, tempo, catch_bias` |
| 14 | Tactics: edit/save policy (visual) | **Not tested** | GUI only |
| 15 | Scouting: scouts seeded (vera, bram, linnea) | **Pass** | 3 scouts with correct IDs |
| 16 | Scouting: prospect pool (25 prospects) | **Pass** | Generated at career init |
| 17 | Scouting: scout strip data | **Pass** | 3 strips, specialty blurb present |
| 18 | Scouting: prospect board rows | **Pass** | 25 rows, correct tier widths |
| 19 | Scouting: fuzzy profile UNKNOWN state | **Pass** | ratings_tier=UNKNOWN, ceiling=?, trait_badges=[?,?,?] |
| 20 | Scouting: fuzzy profile GLIMPSED state | **Pass** | 30-wide OVR band via prospect board `ovr_band` |
| 21 | Scouting: fuzzy profile KNOWN state | **Pass** | 12-wide OVR band |
| 22 | Scouting: fuzzy profile VERIFIED state | **Pass** | ratings_tier=VERIFIED |
| 23 | Scouting: scout assignment | **Pass** | `save_scout_assignment` â†’ `build_scout_strip_data` reflects assignment |
| 24 | Scouting: alerts â€” unassigned early season | **Pass** | "3 unassigned" alert appears at week 2 |
| 25 | Scouting: alerts â€” trajectory late season | **Pass** | Trajectory/verified alert at week 13 |
| 26 | Scouting: trajectory reveal sweep | **Pass** | Only VERIFIED-trajectory prospects appear, correct trajectory label |
| 27 | Scouting: carry-forward decay (GLIMPSED â†’ UNKNOWN) | **Pass** | `apply_scouting_carry_forward_at_transition` resets points correctly |
| 28 | Scouting: accuracy reckoning | **Pass** | Builds summary, writes track records, idempotent |
| 29 | Scouting: hidden gem spotlight | **Pass** | Returns spotlight for HIGH_CEILING events, None when no events |
| 30 | Scouting: reveal ticker (chronological) | **Pass** | Items ordered by week |
| 31 | League: standings | **Pass** | Correct after all 15 regular matches |
| 32 | League: schedule rows (status, is_user_match) | **Pass** | Correct open/played status, user matches flagged |
| 33 | League: wire items with match results | **Pass** | 15 items from 15 match rows |
| 34 | League: league leaders | **Pass** | Correct top performer by category |
| 35 | Match preview: lineup + team overview | **Pass** | `_lineup_text` shows player name, role, OVR |
| 36 | Match day: simulate and persist | **Pass** | All 15 regular matches simulated via `simulate_matchday` |
| 37 | Match day: standings recompute | **Pass** | `_recompute_standings` updates DB correctly |
| 38 | Match report: winner, survivors, MVP | **Pass** | Correct output |
| 39 | Match report: top performers (player IDs in text) | **Partial** | Text block shows `aurora_3`; Treeview panel shows name â€” see BUG-003 |
| 40 | Match report: retrospective leverage section | **Pass** | Renders when `current_record` is set |
| 41 | Match replay: canvas animation | **Not tested** | GUI only (CourtRenderer + Tkinter Canvas) |
| 42 | Playoffs: semis scheduled after regular season | **Pass** | 2 semifinal matches (p_r1_m1, p_r1_m2) materialized |
| 43 | Playoffs: final scheduled after semis | **Pass** | 1 final match (p_final) materialized |
| 44 | Playoffs: AI-only semis auto-simulated | **Pass** | `_simulate_ai_matches` runs when player not involved |
| 45 | Playoffs: player's playoff match waits for user | **Pass** | `_advance_playoffs_if_needed` returns without simulating player match |
| 46 | Playoffs: season outcome (playoff_final) | **Pass** | `load_season_outcome` returns champion + runner_up |
| 47 | Playoffs: bracket status = complete | **Pass** | After all 3 matches played |
| 48 | Playoffs: champion beat prefers playoff_final | **Pass** | Champion source: "Playoff final" in beat body |
| 49 | Offseason: `initialize_manager_offseason` | **Pass** | Persists development, records, HoF, rookie preview |
| 50 | Offseason: all 10 ceremony beats render | **Pass** | All titles correct, all bodies non-empty |
| 51 | Offseason: champion beat | **Pass** | Correct champion, source, runner-up |
| 52 | Offseason: recap beat | **Pass** | |
| 53 | Offseason: awards beat | **Pass** | |
| 54 | Offseason: records_ratified beat | **Pass** | "No new records" on season 1 (correct) |
| 55 | Offseason: hof_induction beat | **Pass** | "No new inductees" on season 1 (correct) |
| 56 | Offseason: development beat | **Pass** | Renders rows or empty state |
| 57 | Offseason: retirements beat | **Pass** | Renders rows or empty state |
| 58 | Offseason: rookie_class_preview beat | **Pass** | Class size 12, storylines present |
| 59 | Offseason: draft/recruitment beat routes to Recruitment Day | **Pass** | `show_offseason_draft_beat()` called when beat key = "draft" |
| 60 | Offseason: schedule_reveal beat | **Pass** | Renders next season preview |
| 61 | Offseason: idempotent re-entry | **Pass** | Re-running `initialize_manager_offseason` does not change stored payloads |
| 62 | Recruitment Day: summary (round 1, 0 signed) | **Pass** | 25 available, current_round=1 |
| 63 | Recruitment Day: round 1 user pick | **Pass** | User signed `River Beck`; 6 AI clubs also signed prospects |
| 64 | Recruitment Day: round advance after round 1 | **Pass** | summary.current_round = 2, 7 total signings |
| 65 | Recruitment Day: round 2 | **Pass** | Completed, 11 total signings across 2 rounds |
| 66 | Recruitment Day: AI signings | **Pass** | AI clubs sign parallel to user pick in each round |
| 67 | Recruitment Day: snipe detection | **Pass** | Snipe flagged when AI takes user's selected prospect |
| 68 | Recruitment Day: prospect excluded after signing | **Pass** | Signed prospects removed from subsequent rounds |
| 69 | Begin next season: season_2 created | **Pass** | 15 matches, season_2, year=2027 |
| 70 | Begin next season: cursor advances | **Pass** | season_number=2, state=PRE_MATCH, week=1 |
| 71 | Build a Club: career init (7 clubs, expansion) | **Pass** | career_path=build_club, 7 clubs, 21 matches |
| 72 | Build a Club: expansion roster weaker | **Pass** | 13.7 OVR gap (spec: 8-16) |
| 73 | Build a Club: recruitment profiles all 7 clubs | **Pass** | All club IDs in profiles |
| 74 | Build a Club: format top4_single_elimination | **Pass** | |
| 75 | Build a Club: accessible from UI | **Fail** | No UI button calls `initialize_build_a_club_career` â€” see BUG-001 |
| 76 | Save: manual save button | **Pass** (inspection) | `_manual_save` calls `self.conn.commit()` â€” simple and correct |

---

## Bugs Found

### BUG-001 [HIGH] â€” Build a Club: no UI entry point

**Description**: `initialize_build_a_club_career` is fully implemented (V2-C shipped 2026-04-28), but no button in the UI calls it. The player cannot start a Build a Club career through the game interface.

**Affected code**: `manager_gui.py`, `show_splash()` (line ~1798) and `show_club_picker()` (line ~1888).

**Reproduction**:
1. Launch `python -m dodgeball_sim` â†’ splash appears.
2. Buttons shown: "Continue Career" (if save exists), "New Career", "Friendly Match Sandbox".
3. "New Career" â†’ `show_club_picker()` â†’ only shows 6 curated clubs with "Confirm Coach".
4. No "Build a Club" option anywhere in the UI flow.

**Evidence**: Searching `manager_gui.py` for all calls to `initialize_build_a_club_career` returns only the function definition itself â€” no caller in the UI layer.

**Suggested fix**: Add a "Build a Club" button on the splash (or as a tab in `show_club_picker`) that opens a form for custom club name/colors/venue, then calls `initialize_build_a_club_career`.

---

### BUG-002 [LOW] â€” Match report text shows player IDs instead of player names

**Description**: `_report_text()` renders raw `player_id` strings (e.g. `aurora_3`) in the text block for MVP and Top Performers. The side-panel Treeview correctly resolves to player names via `_find_player()`. The inconsistency means the monospace text area is harder to read.

**Affected code**: `manager_gui.py`, `_report_text()` (line ~2459), specifically lines 2472 and 2482.

**Reproduction**:
1. Play any match.
2. View match report.
3. The text area shows: `Match MVP: aurora_3 (16.5)` and `aurora_3   score=16.5 ...`

**Suggested fix**: In `_report_text`, look up player name from `self.rosters` for MVP line and top-performers block.

---

### BUG-003 [LOW] â€” Hub league wire shows player IDs in awards

**Description**: `_hub_wire_text()` uses `award.player_id` directly in the "Awards posted" section, producing lines like `Mvp: aurora_3`.

**Affected code**: `manager_gui.py`, `_hub_wire_text()` (line ~2099), line 2109:
```python
f"{award.award_type.replace('_', ' ').title()}: {award.player_id}"
```

**Reproduction**:
1. Play enough matches that season awards are computed.
2. Return to Hub.
3. League wire panel shows `Mvp: aurora_3` instead of `Mvp: Aurora Anchor`.

**Suggested fix**: Look up player name from `self.rosters` using `award.player_id`.

---

## UX Friction

### UX-001 â€” Splash screen stale copy
The label on the splash reads: `"Build a Club arrives after the scouting and recruitment engine milestones."` V2-C shipped on 2026-04-28 and implemented Build a Club. This text should be replaced with a functional button or removed.

### UX-002 â€” No manual scouting tick trigger
Scouting state advances only when a match is played (via `_simulate_ai_matches` / `simulate_matchday`). There is no way in the UI to "advance to next week" or "run scouting tick" without playing a game week. This means a player who wants to see scouting progress mid-week has to play their next match first.

### UX-003 â€” Recruitment Day combobox flow (known V2-B limit)
Recruitment Day uses a combobox to select a prospect and a "Sign Selected" button per round. The V2-B handoff explicitly notes this as "lighter than a full cinematic round timeline." The current flow is functional but the combobox shows `player_id | player_name` format, and there's no visual "snipe alert" â€” a snipe is only apparent after the round resolves and the selected prospect is gone. This leaves the player unclear why their pick was unavailable.

### UX-004 â€” "draft" beat key vs "Recruitment Day" UI label
The `OFFSEASON_CEREMONY_BEATS` tuple uses the key `"draft"` at index 8. The `show_offseason_draft_beat()` method renders the UI with the heading `"Recruitment Day"`. The `build_offseason_ceremony_beat()` for index 8 also returns a beat titled `"Recruitment Day"` when prospect pool is available. But the underlying key is `"draft"` â€” not updated to match V2-B's "Recruitment Day" branding. Minor internal inconsistency; no user impact but could confuse future agents editing the ceremony flow.

### UX-005 â€” Aurora's AI profile competes in same round as user's manual pick
In `conduct_recruitment_round`, after the user selects one prospect, the AI simulation runs for all clubs including `aurora`. This means Aurora can acquire multiple prospects in a single Recruitment Day round: one chosen by the user, and potentially one chosen by Aurora's AI recruitment profile. This is likely unintended behavior or undocumented design â€” the player may not realize Aurora's AI is bidding for extra prospects on their behalf.

---

## Spec Drift

### SD-001 â€” V2-C shipped but UI not wired
V2-C (Build a Club) is marked `Shipped (2026-04-28)` in `MILESTONES.md`. The implementation in `manager_gui.py` is complete and passes all tests. But the UI entry point was never added. The splash copy was also never updated. V2-C is effectively dark from the player's perspective.

### SD-002 â€” V2-B "cinematic Recruitment Day" vs actual combobox flow
V2-B handoff notes: "The current Manager Mode surface is a compact multi-round flow driven by repeated 'Sign Selected' actions. It is functionally multi-round and persisted, but it is still lighter than a full cinematic round timeline." The V2-B design spec called for a "cinematic Recruitment Day with parallel signings." The combobox sequential flow is acknowledged as a known V2-B limit. Flagged here for V3 planning.

---

## Suggested Pre-V3 Fixes

These are fixes to existing V2 behavior only. No V3 feature ideas.

| Priority | Fix | Effort |
|----------|-----|--------|
| High | Add Build a Club entry point to splash/club picker + remove stale text (BUG-001 + SD-001) | ~30 min (UI button + form + call) |
| Low | Resolve player IDs to names in `_report_text` and `_hub_wire_text` (BUG-002 + BUG-003) | ~15 min |
| Low | Rename `"draft"` key to `"recruitment"` in `OFFSEASON_CEREMONY_BEATS` and update all references (UX-004) | ~20 min (careful rename across ceremony) |
| Low | Clarify or guard aurora's AI bidding in the same round as user's manual pick (UX-005) | Needs design decision first |

---

## What Was Not Manually Tested

The following require interactive Tkinter rendering and could not be tested programmatically:

- Splash, club picker, and career selection visual layout
- Match replay canvas animation (CourtRenderer + `after()` loop)
- All Treeview row-selection and double-click bindings
- Scout manage dialog (open/close, assignment save)
- Trajectory reveal sweep popup window
- Accuracy reckoning popup window
- Nav button enable/disable between career states
- Responsive layout at different window sizes (1280Ã—820 vs min 1080Ã—720)
- Save button (confirmed by inspection: calls `self.conn.commit()` only)
- Friendly match sandbox end-to-end visual flow
