# Dodger Multi-Week Playtest Report — 2026-05-29

## Run Summary
- **Driver:** Automated Playwright walk (`playtest_multiweek.py`), naive first-time-player framing. Headless Chromium, fresh dev server (PID confirmed distinct via `scripts/dev-restart.ps1`, frontend rebuilt first).
- **Career:** Build from Scratch → "Cobalt Surge" (Tidewater), coach Dana Reyes (Recruiting Legend), 8 starting recruits. Ruleset = **foam-official** (the new default — confirmed `ruleset-select-new` = `official_foam`).
- **Method (two-pass, per design intent of the new multi-week sim):** manual Weeks 1–3 for observation texture (Favorite band, readiness gates, aftermath/PRIMARY FACTOR, dev beat), then **Fast-forward Season** to blast the rest of the regular season → playoffs → offseason.
- **Final state reached:** Season 1 complete; offseason ceremonies (Recap → Champion → Awards); explored Roster/Standings/Dynasty in offseason.
- **Result:** Cobalt Surge finished **0-4-2**, 7th of 7, missed playoffs (−67 net starter OVR underdog by design). League champion: Solstice Flare.
- **Stability:** **0 console errors, 0 network responses ≥400 across the entire run, including the full playoff traversal.** Evidence: `playtest_output/mw/_run.json`, screenshots `playtest_output/mw/*.png`.

## Headline: the new Fast-forward Season works and the prior STOP-blocker is dead
The 2026-05-24 run ended because the **playoff semifinal hard-crashed** (`ValueError: Both semifinal winners are required`). This run, Fast-forward Season auto-piloted through the regular season **and the playoffs into the offseason** in one call — `HTTP 200`, `stop_reason=season_complete`, champion crowned, no traceback. The multi-week sim is a genuine iteration accelerator: a full season + playoffs in seconds.

## Regression status — the 11 fixes from 2026-05-24
| # | Prior bug | Status this run | Evidence |
|---|-----------|-----------------|----------|
| 1 | Playoff semifinal simulation hard-blocks championship | **FIXED** | Fast-forward traversed playoffs → offseason, 200, champion = Solstice Flare |
| 2 | Postseason "Winner: Draw" on a non-draw semifinal | **FIXED (now tiebroken)** | 0-0 semifinal resolves to higher seed with a `SEED` pill; no crash, no false "Draw". See Confusion #2 (under-explained). |
| 3 | Weekly recruiting slots never reset | **Not exercised** (no manual recruiting actions this run) | — flag for a recruiting-focused pass |
| 4 | Applied staff recommendation still says "adjust" | **Not exercised** (kept Balanced all weeks) | — |
| 5 | No way to resolve captain mismatch warning | **Not observed** (no captain warning surfaced) | — |
| 6 | Playoff cutoff language inconsistent (Top 4 vs top three) | **FIXED / consistent** | CC "Top 4 of 7" + Standings "PLAYOFF LINE — TOP 4" agree |
| 7 | Missing target names in narration ("lets it fly at -") | **FIXED** | W3 "Noa Keene lets it fly at Briar Cross"; W1 "throw by Ayo Slate toward Imani Crosby" — names present |
| 8 | Training "No growth logged this week" felt cosmetic | **Mostly fixed** | W2/W3 show "+1 training unit toward balanced development for [named players]"; **W1 still "No growth logged this week"** — see Confusion #3 |
| 9 | High-OVR favorite loses with no explanation | **FIXED** | PRIMARY FACTOR card quantifies cause every loss (e.g. "Catch disparity … Catches 1-11, +10 catch swing") |
| 10 | Comeback recap claims "0 catches" | **Not observed this run** | — |
| 11 | Run-together text "This WeekA chance" | **FIXED visually** | CC renders the "This Week" kicker and body with proper separation (06_command_center_loaded.png) |

## New / still-open findings

### Critical / Major

**1. (Major, display bug — NOT a scoring bug) The foam aftermath survivor hero shows numbers that contradict the actual games played.**
- **Where:** Aftermath, Week 1 vs Lunar Syndicate.
- **What the player sees:** "Match complete. **A drawn result: 0–3.**" with **Lunar Syndicate 0 SURVIVORS (FINAL)** and **Cobalt Surge 3 SURVIVORS (FINAL)**. Reads as "I wiped them out 3-to-0 yet it's a draw?!"
- **Verified against the match record (`saves/<save>.db` → `match_records` + `official_score_json`):** the **0-0 draw is correct.** The match was two foam games, **both `no_point`** (`no_point_games=2`), each ending on the 1200s game clock with **no full elimination**: game 1 final_active 3-3, game 2 final_active **lunar 1 / cobalt 4**. `winner_club_id = NULL`. Scoring is working as designed (foam scores only on full elimination; clock-expiry games award nothing).
- **The actual bug:** the stored/displayed `home_survivors=0, away_survivors=3` **match no game** — the last game's active counts were 1 and 4. The survivor hero is reading the legacy single-game box-score "living" total (`command_center.py:340-341`, `box[club]["totals"]["living"]`), which for a multi-game official/foam match is meaningless and diverges from the authoritative per-game `final_active` in `official_score_json`. So the headline number is simply wrong, and "(FINAL)" makes it look authoritative.
- **Why it matters:** on the foam path (now the default) the aftermath's most prominent number — the survivor score — can be fiction. That's a direct decision-traceability break: the player can't trust the headline result display even though the underlying sim is correct.
- **Fix direction:** on the foam/official path, bind the aftermath score to the official result (game points, e.g. "0-0 — no game decided") and/or per-game `final_active`, not the box-score `living` aggregate. Drop "(FINAL)" survivor counts when `scoring_model='foam'` and `no_point_games>0`.
- Evidence: `playtest_output/mw/08_w1_aftermath.png`; `match_records.official_score_json` for `season_1_w01_lunar_vs_<save>` (winner NULL, two `no_point` games, final_active 3-3 then 1-4).

**2. (Major, sim-balance) Foam regular season is draw-heavy enough to blunt the standings.**
- Final S1 table: Lunar 1-1-4, Harbor 2-1-3, Northwood 1-3-2, Cobalt 0-4-2 — multiple clubs with 3-4 draws in a 6-game season. A **playoff semifinal also finished 0-0** (decided on seed).
- This is the known "foam scores on full elimination only, no tiebreaker" property (per the plan's verification note, even-team ~26% draws is expected). At a 6-game season length the draw density makes W-L-D hard to separate and amplifies Finding #1's frequency.
- **Fix direction:** consider a within-match tiebreaker (survivor count) for regular-season games, or surface draws as "X-X on the clock" so they read as intentional rather than broken. Couple any change with the existing `test_official_engine_balance.py` draw-rate assertion.

### Gameplay confusion points

**3. (Minor) Playoff seed-tiebreak is under-explained.** The 0-0 Solstice Flare vs Granite Specters semifinal advances Solstice with only a small cyan `SEED` pill as the cue (`PlayoffBracket.tsx:66`). The backend records an explicit `tiebreaker_reason`, but the bracket UI doesn't show it. A naive viewer can't tell *why* a 0-0 game has a winner. Fix: tooltip or inline "Advanced on #1 seed" on the pill.

**4. (Minor) Training feedback inconsistent across Week 1.** W1 aftermath: "No growth logged this week"; W2/W3: "+1 training unit toward balanced development for [named players]." If W1 genuinely logs no reps (first-week default), say why; otherwise it reads like the dev beat is flaky.

### Sim / game logic observations

**5. Catch disparity is the PRIMARY FACTOR in 100% of sampled losses, monotonically.** W2 "Catches 6-10, +4 swing"; W3 "Catches 1-11, +10 swing." For a −67-OVR underdog the OVR gap expresses almost entirely as catch volume (1-11 is extreme). The PRIMARY FACTOR card itself is excellent and honest — but if *every* result is "catch disparity," the lever may be over-dominant relative to throws/dodges/eliminations. Worth a probe on whether throwing/survival ever decides a foam game at a large OVR gap. (Consistent with the P4a catch-tuning history — flagging that the floor may have over-rotated toward catches.)

### Text / layout

**6. (Cosmetic) Aftermath "(FINAL)" label on survivor counts** — see Finding #1; the label is the proximate cause of the confusion even if scoring is "correct."

## What's working well (don't regress these)
- **Fast-forward Season** — robust, fast, traverses playoffs cleanly. The iteration win this session was built for.
- **PRIMARY FACTOR card** — quantified, confidence-tagged, honest ("Catches 1-11, +10 catch swing"). Strong traceability.
- **Favorite/Even/Underdog band** — "MATCHUP UNDERDOG, −67 NET STARTER OVR" reads honestly; raw OVR demoted to advisory as designed.
- **Readiness gates** — scout-opponent + confirm-lineup cleared cleanly; Lock → Simulate enabled correctly.
- **Named targets in narration** + **moment events** ("5 moments", VIEW FULL REPLAY) survive on the foam path.
- **Playoff cutoff language** consistent between Command Center and Standings.

## Top fixes before next playtest
1. Fix the **foam aftermath survivor hero** (Finding #1) — it displays a score that contradicts the games actually played (scoring is fine; the *number on screen* is wrong). Single biggest traceability break this run.
2. Address **foam draw density** in the regular season (Finding #2) — tiebreaker or honest "on the clock" framing.
3. Surface the **playoff seed-tiebreak reason** in the bracket (Finding #3).
4. Probe **catch-lever dominance** — confirm non-catch levers can decide a foam game at large OVR gaps (Finding #5).
5. Clarify **Week-1 training "No growth logged"** vs later weeks (Finding #4).
6. Run a **recruiting-focused pass** to regression-check the prior weekly-slot-reset bug (#3) and applied-recommendation bug (#4), which this sim-heavy run didn't exercise.

## Artifacts
- Harness: `playtest_multiweek.py`
- Screenshots + machine-readable log: `playtest_output/mw/` (`_run.json`)
