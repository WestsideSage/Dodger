# V3 Experience Rebuild — QA Playthrough Report

**Date:** 2026-04-28  
**Milestone tested:** V3 Experience Rebuild (Implemented 2026-04-29)  
**Tester:** QA automation + manual review  
**Status:** PASS with one confirmed bug and two UX notes  

---

## Test Environment

- **Python:** 3.13  
- **Platform:** Windows 11 Pro 10.0.26200  
- **Test runner:** `python -m pytest` — **320 passed in 1.52s**  
- **QA script:** `qa_v3_playthrough.py` (headless, in-memory DB via `:memory:`)  
- **DB backup:** `dodgeball_manager.qa-backup.db` (production save preserved)  

---

## Setup

Two career paths exercised:

1. **Take Over (curated):** `initialize_manager_career(conn, "aurora", root_seed=42)` — 6 clubs, 6-player rosters, 15-match regular season, playoffs, full off-season ceremony, recruitment, next-season carry-forward.
2. **Build a Club (expansion):** `initialize_build_a_club_career(conn, ...)` — 7 clubs, expansion roster (weaker gap ~12 OVR), 21-match round-robin schedule.

---

## Feature Checklist

| # | Feature | Result | Notes |
|---|---------|--------|-------|
| 1 | **Take Over career** | | |
| | 6 curated clubs loaded | PASS | |
| | Player club persisted (aurora) | PASS | |
| | Cursor = SEASON_ACTIVE_PRE_MATCH, season=1, week=1 | PASS | |
| | Season format = top4_single_elimination | PASS | |
| | All 6 clubs have 6-player rosters | PASS | |
| | Default lineup persisted for all clubs | PASS | |
| | 15 scheduled regular-season matches | PASS | |
| | 3 named scouts seeded (vera, bram, linnea) | PASS | |
| | 25 prospects in pool | PASS | |
| | Splash/club picker/career screens | SKIP | GUI only — Tkinter requires display |
| 2 | **Hub / Roster / Tactics / Save** | | |
| | Wire items: 0 pre-season | PASS | |
| | Schedule rows: 15 total, 5 user matches | PASS | |
| | Player profile name resolved (no raw IDs) | PASS | |
| | Player profile body: no raw system IDs | PASS | |
| | title_label: acronyms and capitalization correct | PASS | |
| | Tactics: 8 policy fields (V2-D) | PASS | |
| | Tactics: policy_effect text non-empty | PASS | |
| | Hub team snapshot: no raw player IDs | PASS | |
| 3 | **Match Day / Replay / Report (V3 Pillars 1 & 2)** | | |
| | build_match_team_snapshot: 6-player roster -> 6 active starters | PASS | |
| | build_match_team_snapshot: 9-player roster capped at 6 active | PASS | |
| | simulate_match: home/away active_player_ids == 6 (oversize) | PASS | |
| | simulate_match: survivors capped at 6 | PASS | |
| | Box score: exactly 6 home players with stats | PASS | |
| | Box score: exactly 6 away players with stats | PASS | |
| | match_role field in roster snapshots | PASS | |
| | Replay event labels: non-empty and clean | PASS | |
| | Replay phase delay: 420ms | PASS | |
| | format_bulk_sim_digest: correct V3 structure | PASS | |
| 4 | **Full Regular Season** | | |
| | All 15 regular-season matches simulated and persisted | PASS | |
| | Standings: 6 clubs, all have match results | PASS | |
| | Hub wire: 15 items post-season | PASS | |
| | League leaders: 3 categories (Eliminations, Catches, MVP Score) | PASS | |
| | League leaders: player_id in data (GUI resolves name) | PARTIAL | By design — resolved in Treeview |
| | Season awards computed: 4 awards | PASS | |
| | Award type labels clean (no raw IDs) | PASS | |
| | Wire award text: uses raw player_id | FAIL | **BUG-302** — see below |
| | Match MVP computed | PASS | |
| 5 | **Pacing Controls (V3 Pillar 3)** | | |
| | choose_matches_to_sim(week): stops before user match | PASS | |
| | choose_matches_to_sim(to_next_user_match): stops at first user match | PASS | |
| | choose_matches_to_sim(multiple_weeks=2): weeks 1-2 only | PASS | |
| | choose_matches_to_sim(milestone=playoffs): no playoffs in regular schedule | PARTIAL | Expected — playoff matches only exist post-regular-season |
| | summarize_sim_digest: all required V3 keys present | PASS | |
| 6 | **Scouting (V2-A)** | | |
| | Scouting center: 3 scout strips | PASS | |
| | Scout specialty blurbs clean | PASS | |
| | Prospect board: 25 rows | PASS | |
| | UNKNOWN tier: 50-wide OVR band from public_ratings_band | PASS | |
| | Fuzzy profile UNKNOWN state: correct labels | PASS | |
| | GLIMPSED tier: 30-wide OVR band | PASS | |
| | KNOWN tier + HIGH CEILING label in fuzzy profile | PASS | |
| | Reveal ticker: chronological | PASS | |
| | Scouting alerts returned (may be empty at week 2) | PASS | |
| | Scout assignment persists to strip data | PASS | |
| | Hidden gem spotlight | PASS | |
| | has_accuracy_reckoning_data: False (correct pre-draft) | PASS | |
| | Scouting carry-forward decay applied at transition | PASS | |
| 7 | **Playoffs (V2-F)** | | |
| | 2 semifinal matches created | PASS | |
| | Semifinal match IDs are playoff format | PASS | |
| | Final match created after semis | PASS | |
| | Season outcome persisted (champion = lunar) | PASS | |
| | Bracket loadable after play | PASS | |
| 8 | **Off-season Ceremony (all 10 beats)** | | |
| | initialize_manager_offseason: no error | PASS | |
| | All 10 beats: title and body non-empty | PASS | |
| | All 10 beat keys match spec | PASS | |
| | Champion beat: source = 'Playoff final' | PASS | |
| | Off-season idempotent: re-run preserves records payload | PASS | |
| 9 | **Recruitment Day (V2-B)** | | |
| | Recruitment Day summary: 25 available, round 1 | PASS | |
| | Round 1: user signed prospect | PASS | |
| | Round 1: AI signings in same round (4) | PASS | |
| | Round 2: completed without error | PASS | |
| | Round 2: total signings accumulate correctly | PASS | |
| | No prospect signed twice across rounds | PASS | |
| | User club roster grew after signings | PASS | |
| 10 | **Next Season State Carry-Forward** | | |
| | season_2 created and persisted | PASS | |
| | Season 2 schedule: 15 matches | PASS | |
| | Season 2: playoff format preserved | PASS | |
| | Season 2: all clubs still present | PASS | |
| | Season 2: rosters loaded (36 total) | PASS | |
| | Season 2: prospect pool for class year 2 | PARTIAL | Pool empty until initialize_scouting_for_career called for new season |
| 11 | **Build a Club (V2-C)** | | |
| | 7 clubs (6 curated + expansion) | PASS | |
| | Expansion club ID correct | PASS | |
| | player_club_id = expansion club | PASS | |
| | career_path = build_club | PASS | |
| | Expansion roster has 6 players | PASS | |
| | Expansion roster is weaker (gap ~12 OVR) | PASS | |
| | 21 regular-season matches (7-club round-robin) | PASS | |
| | Recruitment profiles for all 7 clubs | PASS | |
| | Prospect pool seeded (25 prospects) | PASS | |
| | Expansion club identity persisted correctly | PASS | |
| 12 | **Copy Quality (V3 Pillar 5)** | | |
| | has_unresolved_token: all edge cases correct | PASS | |
| | title_label: key edge cases correct | PASS | |
| | narrate_event: produces clean text (no raw IDs) | PASS | |
| | Curated club names: human-readable | PASS | |
| | Player names: human-readable (no raw IDs) | PASS | |
| | Expansion player names: human-readable | PASS | |
| 13 | **Module Import / Smoke Tests** | | |
| | manager_gui: imports without error | PASS | |
| | ui_style: imports without error | PASS | |
| | uncertainty_bar_halo_width_for_tier: correct values | PASS | |
| | court_renderer: imports without error | PASS | |
| | Tkinter canvas animation (replay) | SKIP | GUI only — CourtRenderer requires Tk display |
| | Match preview screen (visual layout) | SKIP | GUI only |
| | Tactics slider widgets | SKIP | GUI only |
| | Scouting center widget layout | SKIP | GUI only |
| | Off-season ceremony step-through UI | SKIP | GUI only |
| | Save button / manual save | SKIP | GUI only — _manual_save() calls tk.messagebox |

**Totals: 96 Pass · 3 Partial · 1 Fail · 7 Skip**

---

## Bugs Found

### BUG-302 — Award wire items display raw `player_id` instead of player name

**Severity:** Medium — visible to user in the Hub wire feed after a completed season.  
**Location:** `manager_gui.py`, `build_wire_items()` around line 492-497.  
**Reproduction:**
1. Complete a full regular season.
2. Call `build_wire_items(match_rows, clubs)`.
3. Inspect returned items for entries with `award_type`.
4. Observe: `"Best Newcomer: granite_5 of Granite Foxes."` — raw `player_id` in the text.

**Expected:** Player's display name (e.g., `"Best Newcomer: Vale Keene of Granite Foxes."`).  
**Actual:** `"Best Newcomer: granite_5 of Granite Foxes."`  
**Root cause:** The wire item formatter uses `award.player_id` directly. The player name is available through rosters loaded in context but the formatter does not resolve it.  
**Suggested fix:** Pass rosters into `build_wire_items()` when available, or build a `player_id -> name` lookup from `clubs` before formatting award items.

---

## UX Notes (not bugs)

1. **League leader data stores `player_id`; name resolved in GUI treeview.** Consistent with V2 design — the model layer stores IDs and the view layer resolves names. No code change needed, but a future improvement could cache resolved names for headless readability.

2. **Season 2 prospect pool is empty until `initialize_scouting_for_career` is called for the new season.** `create_next_manager_season` does not automatically seed a new prospect class. Callers must invoke the scouting initialization step explicitly. This is handled in the GUI flow but worth noting for integrators.

---

## Spec Drift

None observed. All 10 off-season ceremony beats match the V2-E spec. Playoff bracket matches V2-F spec. Build a Club behavior matches V2-C spec (21 matches, 7-club, expansion roster gap within expected range).

---

## Headless Coverage Gaps

The following paths were skipped because they require a live Tkinter display:

- Court renderer canvas animations (Pillar 2 visual replay)
- Match preview screen layout and stat display
- Tactics slider widgets (target, catch_bias, rush_proximity from V2-D)
- Scouting center widget layout (UncertaintyBar rendering)
- Off-season ceremony step-through UI (Next button, beat transitions)
- Save button / manual save dialog

These should be covered by a manual GUI smoke test before marking V3 as Shipped.

---

## Pre-V4 Fix Recommendation

**BUG-302 is the only confirmed code defect.** It is a small fix in `build_wire_items()` and should be resolved before V4 development starts so award copy is clean going into the next milestone.

The two UX notes are not blocking but worth considering for the V4 backlog.

---

*QA script: `qa_v3_playthrough.py` · Results JSON: `qa_v3_results.json`*
