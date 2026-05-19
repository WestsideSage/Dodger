# Browser Playthrough — Bug & UI Log

Playthrough started 2026-05-18. Club: **Granite Bay Summit Vipers**, coach Marcus Vale (Recruiting Legend).
Pure browser-only playthrough (Playwright), no backend simulation shortcuts.

---

## RESOLUTION (2026-05-19) — all 14 bugs fixed + playoff bracket added

Every confirmed bug below (B1–B14; B15 was withdrawn) is fixed. Verified with the full Python
test suite (`python -m pytest -q`, all pass), a clean frontend build + lint, and a fresh browser
re-test that played Seasons 5–6 including a full playoff run.

| Bug | Fix summary | Verified |
|-----|-------------|----------|
| B1 | `aria-label` on the simulate button changed `Simulate Match` → `Simulate Week` to match the visible text. | aria-label reads "Simulate Week" |
| B2 | `TacticalSummaryCard.buildStatLine` now skips any evidence item equal to the turning-point line. | Tactical Read shows two distinct lines |
| B3 | `buildContextLine` is now player-perspective: real win copy on a win, defeat copy (player score first) on a loss. | win copy verified live |
| B4 | Was a *symptom of B5* — the stale strip fell back to "player = home". Fixed by the B5 fix; no separate change. | strip home/away matches debrief |
| B5 | The Command Center strip no longer trusts the league-wide `current_week`; it finds the player's next *unplayed* match from the schedule and shows that week + opponent. | correct week/opponent incl. bye + playoff weeks |
| B6 | Removed `white-space:nowrap` from the standings "Approach" cell and tightened table padding — table fits, no scrollbar, no truncation. | `scrollWidth <= clientWidth` |
| B7 | Reclassified: the "4-1" field is **last-5-game form**, not season record — not a bug. Added `title` tooltips to every strip field for clarity. | tooltips present |
| B8 | New `/api/playoffs/bracket` endpoint + `PlayoffBracket` component on the Standings page; playoff `stage` added to schedule rows & post-week dashboard; "Playoff Semifinal/Final" badge in the strip and debrief header. | bracket renders; badges show |
| B9 | Champion ceremony adds "Won the championship final…" and labels the record "Regular Season"; the recap table is retitled "Final Regular-Season Table" with a note that the top 4 seed the playoffs. | copy verified live |
| B10 | Awards `career_stat` now tracks the *same metric* as `season_stat` (throws+catches for MVP/Newcomer, throws for Best Thrower, catches for Best Catcher). | career 44 ≥ season 15 |
| B11 | Offseason development `delta` is now derived from the rounded `ovr_after - ovr_before`, so the badge always agrees with the displayed numbers. | all 14 rows consistent |
| B12 | Reclassified: the count is a deliberate *scouted-floor* metric (encoded in tests). Fixed the misleading label `(70+ OVR)` → `(70+ floor)` with an explanatory tooltip. | label verified live |
| B13 | Roster "Starters" now counts the first 6 of the ordered lineup (a dodgeball lineup is 6), not the whole squad. | shows "6 Starters" |
| B14 | Roster "Role" column shows the player's real derived archetype (Enforcer/Sharpshooter/etc., from their top rating) instead of the index-based `Captain/…/Rookie` placeholder. | shows real archetypes |
| O2 | Same fix as B14: the roster no longer surfaces the vestigial always-"Tactical" enum; the "X · Age" line now reads "Starter/Bench · Age". The `PlayerArchetype` enum is dead code (never assigned) — left in place, noted here. | roster shows varied archetypes |

**O1 is an engine-balance matter — investigated, not silently changed.** See the investigation
section at the very bottom of this file. Per `AGENTS.md` engine rules, a balance change needs
sign-off and golden-log updates, so it is written up as a proposal.

---

## Bugs / UI issues

### B1 — "Simulate Match" button: accessible name vs visible text mismatch
- Location: Command Center, Week Lock panel, after locking plan.
- Visible button text reads `SIMULATE WEEK`; the accessible name / testid-derived label is `Simulate Match`.
- Severity: low (cosmetic/a11y inconsistency).

### B2 — Tactical Read shows a duplicated line
- Location: Command Center post-match debrief, "TACTICAL READ" panel.
- Week 1: the line "Nia Novak secures the catch against Tate Keene." is rendered twice, back to back.
- Confirmed again Week 2 ("...against Zeph Pierce.") and Week 3 ("Kiran Wilder reads Vale Novak perfectly for the catch.").
- Consistent across every match — the headline read and the boxed detail line are populated from the same string.
- Severity: low-medium (looks like a content bug).

### B3 — Loss debrief reuses win-flavored copy ("leaves no room for excuses")
- Location: Command Center post-match debrief headline subline.
- Week 1 WIN subline: "A 5-0 shutout that leaves no room for excuses."
- Week 3 LOSS subline: "A 2-0 shutout that leaves no room for excuses."
- The "leaves no room for excuses" template fits a dominant win but reads wrong on a shutout loss.
- Severity: low (content/tone bug).

### B4 — Home/away flipped between week context and match debrief (Week 5)
- Pre-match "Week context" strip showed the matchup as `SOLSTICE FLARE @ SUMMIT VIPERS`
  (`@` convention = away @ home → Solstice Flare away, Summit Vipers home).
- Post-match debrief "Final survivor score" labelled **Solstice Flare as HOME** and **Summit Vipers as AWAY**.
- Weeks 1–4 were internally consistent; Week 5 is flipped. One of the two screens has the wrong side.
- RECURRED Season 2: vs Granite Specters the week context said `GRANITE SPECTERS @ SUMMIT VIPERS`
  (Granite away) but the debrief labelled Granite Specters HOME and Summit Vipers AWAY.
- Severity: medium (factual inconsistency a player would notice).

### B5 — Week numbering inconsistent between Command Center and Standings
- The Solstice Flare match (Summit Vipers' 5th game) was labelled **Week 5** in the Command Center
  (pre-match week context + "Wk 5 Debrief") but appears as **Week 6** in Standings → Recent Results
  ("Week 6 — Solstice Flare 0-5 Summit Vipers").
- After that match, the Command Center's next matchup (vs Harbor Tidebreakers, our 6th game) is again
  labelled **Week 5** — i.e. the Command Center shows "Week 5" twice in a row.
- Standings Recent Results lists Week 6 and Week 4 games but no Week 5 at all.
- The Northwood match was consistently Week 4 in both views, so the drift starts at game 5.
- UPDATE: across the Vipers' first 7 games the Command Center week labels read 1, 2, 3, 4, 5, 5, 8
  — week 5 duplicated and weeks 6 & 7 skipped. The counter is clearly not tracking games played.
- UPDATE 2: Season 2's Schedule Reveal shows the Vipers play weeks 1,2,3,4,6,7 — week 5 is a
  legitimate bye (7-team league). So the real week of the Solstice game was Week 6, which means
  the Standings "Recent Results" label (Week 6) was CORRECT and the Command Center label
  (Week 5) was the wrong one. The bug is specifically the **Command Center week-context counter**,
  which neither tracks byes nor matches the league week.
- UPDATE 3 (Season 2): the whole "Week context" strip — not just the number — goes stale. Going
  into the Vipers' 6th game the strip read "WEEK 5 — GRANITE SPECTERS @ SUMMIT VIPERS" but the
  actual opponent was **Solstice Flare** (the scout panel correctly named Solstice's threat Ezra
  Bloom, and the debrief header correctly said "Wk 7 Debrief"). So the strip lagged a full week
  behind on BOTH the week number and the opponent. A player reading only the strip would prep
  for the wrong team.
- Severity: high (the strip can show the wrong opponent entirely).

### B6 — Standings table overflows container; "Approach" value truncated
- Location: Standings page, league table.
- The table is wider than its column, producing a horizontal scrollbar at 1440px viewport width.
- Row 1 "Approach" cell shows "Prepare For Playoff" — the trailing "s" of "Prepare For Playoffs"
  is clipped by the overflow.
- The right-hand "Recent Results" panel squeezes the table; it should wrap/shrink or the table
  should be allowed full width.
- Severity: medium (visible truncation + unexpected scrollbar).

### B7 — Stale win/loss record in Command Center week context during playoff weeks
- The regular season is 6 games. Final standings correctly show Summit Vipers 5-1-0, 1st seed.
- After game 6 (last regular-season game, a win) our record should read 5-1.
- But both playoff games (game 7 vs Northwood, game 8 vs Granite Specters) showed our record in
  the pre-match "Week context" strip as **4-1** — frozen at the pre-game-6 value.
- The final standings table is correct (5-1); only the Command Center week-context strip is stale.
- Severity: low-medium (display only — does not affect standings/championship logic).

### B8 — Playoff games are not labelled as playoffs anywhere (no bracket, no "FINAL" banner)
- A 6-game regular season is followed by playoffs, but games 7 (semifinal vs Northwood) and 8
  (championship FINAL vs Granite Specters) are presented identically to regular-season weeks.
- No playoff bracket, no "Semifinal"/"Final" banner, no seeding view. The week-context strip even
  kept saying "Week 8"/"Week 9" and "League Rank #1" as if it were a normal week.
- Result: the player has no way to know game 8 is the championship final. We lost it 0-2 and only
  found out it mattered when the "SEASON CHAMPION: Granite Specters" ceremony appeared.
- For a game whose core loop is "win a championship", the total absence of playoff framing is a
  significant UX gap.
- Severity: medium-high (core-loop clarity).

### B9 — "Season Champion" ceremony vs "Final Standings" can look contradictory
- The ceremony screen crowns Granite Specters (playoff winner). The very next screen, "Final
  Standings / Season Table", ranks Summit Vipers #1 (5-1, 15 pts, +20) above Granite (4-2, 12).
- These are actually two different things (playoff champion vs regular-season table), but with no
  labelling that the table is "regular season" and no playoff framing (see B8), it reads as a
  flat contradiction: "we're #1 but they're champion?"
- Severity: medium (clarity — fixed largely by addressing B8 + labelling the table).

### B10 — Awards Night: "Career Elims" lower than this season's elims for a rookie
- Awards Night, MVP card for Nia Novak: stats row shows "4 THROW ELIMS" and "4 CAREER ELIMS".
- Same player wins Best Newcomer (i.e. a rookie) credited with "21 season elims".
- For a newcomer, career total should be >= this season's total. "4 career elims" vs "21 season
  elims" is internally inconsistent — looks like "career elims" only counts throw elims (=4) while
  "season elims" counts all elimination types (=21), but they sit on the same screen unlabelled.
- Severity: low (confusing stat labelling).

### B11 — Offseason Development screen: OVR before/after values disagree with the change badge
- Location: Offseason → "Your Roster Progress" (10 players changed OVR).
- Every row shows a green "+1" badge, but the before→after values do not all support it:
  - Ash Kline: `72 → 74` (a +2 delta) but badge says **+1**.
  - Nia Novak: `73.0 → 73.0` (no change) but badge says **+1**.
  - Cass Okafor: `72.0 → 72.0` (no change) but badge says **+1**.
  - Lyra Bishop: `68.0 → 68.0` (no change) but badge says **+1**.
- Also a formatting inconsistency: most rows show integer OVRs (`72 → 74`) while three rows show
  one-decimal values (`73.0 → 73.0`). Looks like rounded vs unrounded OVR are mixed, and the badge
  is a hardcoded/placeholder "+1" rather than the actual delta.
- Severity: medium (player progression is a core system; the numbers visibly contradict each other).

### B12 — Rookie Class Preview "Top Prospects (70+ OVR)" count contradicts the signed rookie
- Offseason "Rookie Class Preview" reported: 12 Incoming Rookies, **0 Top Prospects (70+ OVR)**,
  12 Veteran Free Agents.
- On Signing Day, "Sign Best Rookie" produced **Cass Frost, OVR 78, Age 19** — clearly a 70+ prospect.
- The preview's "0 top prospects" count is wrong, or it samples a different pool than Signing Day.
  (May interact with the Recruiting Legend coach perk, but the preview should still be accurate.)
- Severity: low-medium (misleading planning info).

### B13 — Roster page "Starters" stat shows full roster size (11), not the 6 starters
- Roster page header stats: Avg Age 20, Avg OVR 72, **Starters 11**.
- The roster has 11 players total and the lineup is 6. The Command Center separately states
  "6 listed starters". The Roster page's "Starters: 11" just echoes the roster count.
- Either mislabeled (should be "Players"/"Squad Size") or miscounting (should be 6).
- Severity: low.

### B14 — "Role" column shows "Rookie" (not a role) — and on a non-rookie
- Roster table "Role" column values: Captain, Striker, Anchor, Runner, Utility... and **"Rookie"**.
- "Rookie" is assigned to Cass Okafor — a 2nd-year player who was on the roster all of Season 1.
- Meanwhile the actual newcomer (Cass Frost, with a "NEWCOMER" badge) has role "Utility".
- "Rookie" is a tenure status, not a role; it should not appear in the Role column, and not on a
  veteran. Likely a fallback/placeholder leaking into the role field.
- Severity: low-medium.

### B15 — [WITHDRAWN] "Elite"/"High" potential stars
- Initially flagged because Elite and High both showed ★★★☆☆. After a season the stars rose to
  ★★★★☆, so the star count tracks development *progress*, not the potential tier. The tier word
  ("Elite"/"High") and the star meter are two different things — not a bug. Withdrawn.

## Observations (not necessarily bugs)

### O2 — All 11 players share the "Tactical" archetype
- Every roster player is listed as "Tactical". The new-game recruit screen used a different role
  taxonomy entirely (Enforcer / Ball Hawk / Iron Engine / Escape Artist / Sharpshooter).
- Possibly two unrelated systems, but zero archetype variety on the roster is worth a balance look.

### O1 — Heavy favorite repeatedly shut out by the same team
- Summit Vipers lost 0-2 (shut out, scoreless) to Granite Specters TWICE — game 3 and game 8 —
  despite being ~+61 net OVR favorites both times, and using the scout-recommended Control plan.
- Every other game was a comfortable shutout win for the Vipers. The losses are concentrated on
  one opponent with the identical 0-2 scoreline.
- Either a matchup-resolution quirk vs that club's "Tactical" profile, or extreme variance.
  Flagging for balance review — a 61-OVR favorite being scoreless twice vs one team looks off.
- UPDATE: the pattern is broader than Granite Specters. In Season 2, with a +71.8 net OVR edge,
  the Vipers were shut out 0-4 by last-place-calibre Solstice Flare while the scout reported the
  plan as "profile aligned". Heavy-favorite shutout losses recur across opponents — a ~70 OVR
  edge should make a scoreless loss extremely rare. Worth a hard look at match-resolution variance.

## Match results

| Season | Week | Opponent | Result | Notes |
|--------|------|----------|--------|-------|
| 1 | 1 | Lunar Syndicate (away) | W 5–0 | Shutout. Control plan. |
| 1 | 2 | Aurora Sentinels (away) | W 4–0 | Shutout. Control plan. |
| 1 | 3 | Granite Specters (home) | L 0–2 | Upset loss despite +60.9 OVR edge. Control plan. |
| 1 | 4 | Northwood Ironclads (away) | W 3–0 | Shutout. Control plan. |
| 1 | 5 | Solstice Flare | W 5–0 | Shutout. Home/away flipped vs week context (B4). |
| 1 | 6 | Harbor Tidebreakers (home) | W 5–0 | Shutout. CC mislabeled this "Week 5" (B5). Last regular-season game. |
| 1 | PO semi | Northwood Ironclads (home) | W 6–0 | Shutout. Playoff semifinal (unlabelled — B8). CC "Week 8". |
| 1 | PO FINAL | Granite Specters (home) | L 0–2 | Championship final (unlabelled — B8). Lost the title. CC "Week 9". |

**Season 1 result: Regular season 5-1 (1st seed). Lost championship final 0-2 to Granite Specters. NOT champions.**

| 2 | 1 | Lunar Syndicate (away) | W 6–0 | Control plan. |
| 2 | 2 | Harbor Tidebreakers (home) | W 6–0 | Control plan. |
| 2 | 3 | Northwood Ironclads (away) | W 4–0 | Control plan. |
| 2 | 4 | Aurora Sentinels (home) | W 1–0 | Close one. Control plan. |
| 2 | 6 | Granite Specters | W 6–0 | **Defensive** plan (not scout's Control) — finally beat them. Home/away flipped (B4). |
| 2 | 7 | Solstice Flare (home) | L 0–4 | Upset loss, +71.8 OVR favorite. Defensive plan, scout said "profile aligned". |
| 2 | PO semi | Aurora Sentinels | L 0–3 | Lost playoff semifinal. Defensive plan. Eliminated.|

**Season 2 result: Regular season 5-1 (1st seed). Lost playoff semifinal 0-3 to Aurora Sentinels. NOT champions.**

| 3 | 1 | Lunar Syndicate | L 0–1 | Heavy-favorite shutout loss. |
| 3 | 2 | Solstice Flare | L 0–3 | Heavy-favorite shutout loss. |
| 3 | 3 | Granite Specters (home) | W 2–0 | Defensive plan. |
| 3 | 4 | Harbor Tidebreakers (away) | W 5–0 | Control plan. |
| 3 | 6 | Aurora Sentinels (home) | W 4–0 | Control plan. |
| 3 | 7 | Northwood Ironclads | W 4–0 | Control plan. Regular season ends 4-2. |
| 3 | PO semi | Granite Specters | W 3–0 | Defensive plan. |
| 3 | PO FINAL | Lunar Syndicate | L 0–1 | Lost championship final again. Defensive plan. |

**Season 3 result: Regular season 4-2. Won semifinal, lost championship final 0-1 to Lunar Syndicate. NOT champions.**

| 4 | 1 | Aurora Sentinels | L 0–3 | Scout (Control) plan. |
| 4 | 2 | Harbor Tidebreakers | W 4–0 | |
| 4 | 3 | Granite Specters | W 3–0 | |
| 4 | 4 | Northwood Ironclads | W 4–0 | |
| 4 | 5/6 | Lunar Syndicate | W 4–0 | |
| 4 | 6/7 | Solstice Flare | W 4–0 | Regular season ends 5-1. |
| 4 | PO semi | Harbor Tidebreakers | W 4–0 | |
| 4 | PO FINAL | Northwood Ironclads | W 4–0 | **CHAMPIONSHIP WON.** |

**Season 4 result: Regular season 5-1. Won semifinal 4-0 and championship final 4-0 vs Northwood Ironclads.
SUMMIT VIPERS ARE SEASON CHAMPIONS. 🏆 (Confirmed in Dynasty Office → History: Season 4 "Champions"
node, Banner Shelf trophy, Program Arc "1 title".)**

## Playthrough summary

- Club: Granite Bay Summit Vipers, coach Marcus Vale (Recruiting Legend), built from scratch.
- Took 4 seasons to win the title (lost the S1 final 0-2, the S2 semifinal 0-3, the S3 final 0-1).
- Every match in this playthrough ended as a shutout for one side — the Vipers either won
  comfortably or were held scoreless. No close/non-shutout result was ever observed (see O1).
- The whole run was played browser-only (Playwright) with no backend simulation shortcuts.
- 14 issues logged above (B15 withdrawn). Most impactful: B5/B7 (stale Command Center week-context
  strip — can show the wrong week AND wrong opponent), B8/B9 (no playoff framing at all),
  B11 (offseason OVR deltas contradict the change badge), B6 (standings table overflow/truncation).

---

## O1 / O2 — engine investigation (2026-05-19)

### O2 — player archetypes (resolved as a display fix)
`Player.archetype` is a `PlayerArchetype` enum (Power/Agility/Precision/Defense/Tactical) that
**defaults to `TACTICAL` and is never assigned anywhere** — it is vestigial. The *real* archetype
concept is the recruitment-derived label (Sharpshooter/Enforcer/Escape Artist/Ball Hawk/Iron
Engine) computed from a player's dominant rating. The roster page was showing the dead enum
("Tactical" for everyone). Fixed under B14/O2: the roster now derives and shows the real
archetype. Recommendation: delete the unused `PlayerArchetype` enum + field in a future cleanup.

### O1 — heavy favourites lose far too often (BALANCE — proposal, NOT applied)

First, a correction to the original O1 report: "every loss is a shutout" is **not a bug**. This
is last-team-standing dodgeball — the losing side is by definition fully eliminated, so every
result is `X-0`. The survivor number is just how many of the winner's six were still in.

The real issue is genuine. A read-only Monte Carlo over the existing match engine
(`tools/o1_variance_probe.py`, 400 trials per data point, two 6-player teams with flat ratings):

| Per-player rating edge | Net OVR edge | Favourite win rate |
|------------------------|--------------|--------------------|
| +0  | +0   | 51.5% |
| +4  | +24  | 48.8% |
| +8  | +48  | 47.5% |
| +12 | +72  | 52.0% |
| +16 | +96  | 56.2% |
| +20 | +120 | 67.0% |

A **+72 net OVR favourite wins only ~52%** — essentially a coin flip. OVR barely matters until
the gap is enormous (+96/+120). This fully explains the playthrough: the Vipers were ~+70 net
OVR favourites all four seasons yet lost ~30-40% of games and three playoff series.

Root cause direction: the per-throw probability scales (`accuracy_scale=12.0`, `catch_scale=11.0`
in `config.py`) compress realistic rating gaps into a near-negligible per-throw delta, which then
washes out over a full match.

**Proposed change (needs sign-off):** raise the engine's rating sensitivity so a +72 net OVR
favourite wins roughly 75-80%. The likely lever is the `accuracy_scale` / `catch_scale` constants
(or how rating deltas feed `compute_throw_probabilities`). Per `AGENTS.md` ("If match outcomes
intentionally change, update golden logs and document why"), this must be a deliberate, signed-off
change with golden-log regeneration in the same commit — so it is deliberately **left unapplied**
here. Re-run `tools/o1_variance_probe.py` after any change to confirm the win-rate curve.
