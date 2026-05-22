# Dodgeball Manager — Browser Playthrough QA Audit

**Date:** 2026-05-21
**Tester:** Browser-only QA agent (Playwright via real DOM clicks, no backend access)
**Build:** Local `python -m dodgeball_sim` server, frontend bundled with the app
**Save profile:** "Championship Run QA" → club *Westside Sages*, City *Westside*, Tactical Mastermind coach (Maurice Calloway), 10-player from-scratch starting roster.

---

## 1. Executive Summary

**Verdict: Championship won — in two seasons. Game is technically playable and clean, but as a management sim it is currently a shell. Decisions don't matter, the season is a sprint, and there is almost no signal that the simulator is hiding anything interesting underneath.**

| Question | Answer |
|---|---|
| Did you win a championship? | **Yes — Season 2.** Season 1 = 6-0 regular season, lost the final 0-2 to Solstice Flare. Season 2 = 6-0 reg + 5-0 semi + 4-0 final. |
| Seasons to win? | **2.** |
| Playable? | Yes. No crashes. Zero console errors over the entire run. |
| Fun? | **Low.** Click "Lock Plan" → "Simulate Week" → "Advance" → repeat. I never felt I made a real decision. |
| Fair? | The regular season felt fair (the strongest roster won). The Season 1 final 0-2 loss with a +73.6 net OVR edge felt arbitrary. |
| Did it feel like dodgeball? | Only barely — surface terminology (catches, throws, eliminations, "survivors") is there. The match is one bullet of narrative + a survivor count. No sense of throws, dodges, court state, or momentum. |
| Management sim or spreadsheet? | **Closer to a debrief reader than a sim.** Most management surfaces (recruiting slots, staff market, tactics dept., training, development focus) are exposed but their effect on outcomes is invisible. |

### Top 5 issues hurting the game most

1. **The core loop is a 3-click rail.** Lock Plan → Simulate Week → Advance. The "Plan Editor" tactical sliders are read-only (disabled the moment you lock), and the recommended approach is always pre-selected and labeled "aligned." There is no decision pressure.
2. **Net OVR is so dominant that nothing else appears to matter.** Starter overall edge of +73 to +94 net OVR every single match. Sample 8-game playoff run: outscored opponents **31–2 in survivors**, with **5 shutouts in 8 matches**. This implies attributes ≫ tactics, fatigue, rotation — making every other system invisible.
3. **A single non-deterministic final game ended a 6-0 dominant season 0-2.** No explanation of *why*. This is the worst possible failure mode of a sim: a player can do everything right and the screen just says "you lost." See Section 5.
4. **Match output is one sentence + a survivor score.** There is no play-by-play, no shot list, no momentum chart, no per-player line for the actual match. "Beautiful catching form from Nia Novak against Tate Keene" is the entire tactical narrative. Replay was not tested in depth; the postgame report is 5 boilerplate "moments."
5. **Half the management surfaces are credible but unattached.** Dynasty Office has weekly Scout/Contact/Visit recruiting slots, a Staff Room, program credibility, but I won the title without touching any of them. Credibility was still "Tier D, score 50, 0 command-history wins" *after* a championship — a visible data bug.

### Top 5 strongest parts

1. **Zero crashes, zero console errors.** Eight match weeks + two offseasons + UI navigation produced a clean log. The plumbing is reliable.
2. **Command Center as a single decision screen is a good shape.** Three article cards (Plan Editor / Scout Read / Week Lock Status) plus a right-rail status pane is conceptually a glanceable war-room. It just needs the cards to mean something.
3. **Onboarding is fast and friction-free.** 3 steps, ~30 seconds. Save name → club identity → coach archetype → checkbox roster. Strong first impression.
4. **Lineup Leverage matchup pairs ("◀ SAGE +18") are a great pattern.** Compact, glanceable, immediately communicates the per-matchup story. This is the highest-density-of-meaning component in the app.
5. **Awards Night, Offseason Development, Schedule Reveal are real ceremonial beats.** The skeleton of a dynasty mode is here — MVP/Best Thrower/Best Catcher/Best Newcomer recognition, +1 OVR development reports, full upcoming schedule. The structure is right.

## RESOLUTION (2026-05-22) — Pre-Plan-C knockout

| Bug | Fix |
|-----|-----|
| 7.1 | Recruit picker now labels two numbers as "NOW / PEAK" with a legend. (Task 8) |
| 7.2 | League Rank hidden until at least one match is played league-wide. (Task 3) |
| 7.3 | Standings Approach falls back to the club's default `coach_policy.approach`. (Task 5) |
| 7.4 | Credibility now uses `load_command_history_all_seasons` — career wins/losses, not just the active season. (Task 11) |
| 7.5 | Right-rail Plan Status flips to `OK Plan locked.` after Lock Plan. (Task 4) |
| 7.6 | **Deferred to Plan C** — picker is being rebuilt for `CoachPolicy` v2. |
| 7.7 | Bye Week is now an explicit beat in the Command Center. (Task 10) |
| 7.8 | Replay proof copy rewritten in player-facing register. (Task 2) |
| 7.9 | `qa-playthrough-*` saves hidden behind a "Show debug saves" toggle. (Task 6) |
| 7.10 | Real potential-tier distribution; pinned by a pool-distribution test. (Task 9) |
| 7.11 | PotentialBadge stars are derived from the tier (Elite=5★, High=4★…); confidence shown as separate pips. (Task 7) |
| 7.12 | No action needed (positive observation). |

Audit P0 items related to tactical variance, narrative-on-loss, and round-by-round match readout are **deferred to Plan C** as a coherent rewrite, not band-aided here. The O1 engine balance fix is **deferred to its own brief** per `AGENTS.md` engine-integrity rules.

---

## 2. Season-by-Season Playthrough Log

### Season 1 Summary

**Club status at start:** Brand new club, 10 players selected from prospects screen (most at 50 current / 100 potential). Player current OVRs presented as `50-100` in the picker were rendered as **79/80/81 actual OVR** on the Command Center the moment the season began — see Bug 7.1.

**Key roster situation:**
- Starting six: Elio Penn (S), Ash Kline (S), Nia Novak (Sh), Vale Novak (Sh), Cass Okafor (Sh), Vale Lark (Sh).
- Bench (4): Jules Cole, Ezra Mercer, Briar Slate, Callum Penn.
- League rank shown as "#2" at week 1 — unclear why a brand-new club has any rank.

**Strategic plan:** Tactical Mastermind coach archetype. Auto-selected "Aggressive" + "Fundamentals" + "Balanced" with the staff recommendation pinned to "Keep current plan" every single week. I did not change it because the system never suggested I should.

**Important matches / turning points:**
| Wk | Match | Result | Net OVR edge | Score (survivors) |
|---|---|---|---|---|
| 1 | @ Lunar Syndicate | W | +84.5 | 5-0 |
| 2 | @ Aurora Sentinels | W | +80 | 4-0 |
| 3 | vs Granite Specters | W | +79.4 | 6-0 |
| 4 | @ Northwood Ironclads | W | +76.7 | 5-0 |
| 5 | *(bye? week absent from log)* | — | — | — |
| 6 | @ Solstice Flare | W | +73.6 | 3-0 |
| 7 | vs Harbor Tidebreakers | W | +77 | 4-0 |
| 8 (Semi) | vs Harbor Tidebreakers | W | +77 | 6-0 |
| 9 (Final) | vs Solstice Flare | **L** | +73.6 | **0-2** |

**Final record:** 7-1 incl. playoffs. Regular season 6-0. **Lost the championship 0-2** to Solstice Flare despite a +73.6 net OVR edge.

**Biggest success:** Cass Okafor / Nia Novak carrying matchup advantage; Nia Novak as MVP-tier catcher all season.
**Biggest failure:** Got shut out 0-2 in the final. **No explanation** for why a +73.6 OVR favorite was held to zero survivors at home.
**What I learned:** Nothing tactical. The game gave me no readable lesson from the loss — the postgame just said "Beat by Solstice Flare." No "their key threat was uncontained," no "we were tired," no "tactics mismatch." A real player would feel cheated.
**What I changed for next season:** Nothing — there was nothing to change. The screen never told me which lever to pull. I kept the same lineup, same tactic.

**Did the game teach me how to get better?** **No.** I had to guess. The final felt like a coin flip.

### Season 2 Summary

**Club status at start:** 1 rookie signed via "Sign Best Rookie" (Cass Frost — went on to become Best Newcomer). Roster otherwise carried forward. Net OVR edge actually *grew* to +94.7 at S2W1 because... unclear, since opponents should also recruit.

**Strategic plan:** Identical to S1.
**Important matches:**
| Wk | Match | Result | Score |
|---|---|---|---|
| 1-7 | Regular season | 6-0 | 4-0, 5-0, 6-0, 4-0, (bye), 5-0, 2-0 |
| 8 (Semi) | vs Lunar Syndicate | W | 5-0 |
| 9 (Final) | vs Solstice Flare | **W** | **4-0** |

**Final record:** 8-0 incl. playoffs. **Championship.** MVP: Nia Novak (6 throw elims, 20 catches). Best Thrower: Vale Novak (12). Best Catcher: Nia Novak. Best Newcomer: Cass Frost.
**Biggest success:** Sweep.
**Biggest failure:** It was *too* easy. Two of seven regular-season margins were shutouts of 4–6 survivors with zero opposing survivors. There was never a moment of doubt.

**Did the game teach me anything?** No new information vs S1. I won by doing literally the same thing.

---

## 3. UX / UI Audit

### Save Menu (landing screen)

- **Works:** Two clear tabs (Load Game / New Game). Save list rows are scannable.
- **Doesn't work:** Save list has **27 `qa-playthrough-*` orphan saves** visible to the user. No grouping, no search, no pagination. A first-time player landing on this would lose trust immediately. The list looks like an unflushed test bucket.
- **Recommend:** Hide saves with the `qa-` prefix behind a "Show debug saves" toggle, or just garbage-collect them at startup.

### Career Setup (3 steps)

- **Works:** Step pacing is right; disabled "Next" with helper text ("Add a save name, club name and city to continue") is clean.
- **Doesn't work:**
  - **Roster picker is the only screen that uses `current-potential` notation (e.g., "50-100") and the rest of the app uses single OVR (e.g., "80").** New players will not know if `50-100` means a range, a min-max, current/potential, or something else. There is no legend.
  - The `OVR` numbers on this screen don't match what shows up the very next click on the Command Center. Most players I picked as "50-100" appeared at 76-82 actual OVR. The mapping rule is not exposed.
  - "Custom kit selected" status text is dead weight after color choice.
- **Recommend:** Label as "Current — Potential" with a tooltip, or just show one number with a "potential" pip.

### Command Center (the main screen — this carries the game)

- **Purpose:** Pick weekly plan, see opponent, lock plan, simulate match.
- **Works:**
  - Three-card layout (Plan Editor / Scout Read / Week Lock Status) is glanceable at 1440×900 without scrolling above the right-rail summary.
  - Week context banner reading "Westside Sages @ Lunar Syndicate · 0-0 · +84.5 net OVR" is the right shape.
  - Lineup Leverage matchup chips (`◀ SAGE +18`) are the best component in the app.
- **Doesn't work:**
  - **The four tactical approach buttons are disabled the second you click Lock Plan.** And before locking, the system says "Current approach aligns" and "Keep current plan" — so there is no signal you should ever click anything other than the default. The lever is decorative.
  - "Tactical Profile" sliders (Target Stars 75%, Catch Bias 55%, Risk 50%, Tempo 50%) appear *fixed* — clicking the approach buttons (when not locked) didn't visibly mutate them in my session, and there is no per-knob editor.
  - "Plan Status: ! Confirm the staff plan to unlock match simulation" — the `!` warning persists on the right-rail status even *after* locking, while the main card already says "Locked." Conflicting signals.
  - Lineup Leverage shows 2 of 6 matchups with an "Expand all 6 matchups" button; expanded view was not tested but the default 2-of-6 is too few.
  - "OK Scout / OK Intent / OK Training / OK Rotation / OK Health" chips just say OK every time. They are unreadable unless they ever flip — and I never saw them flip.
  - **The headline number "Westside Sages +84.5 net OVR" is the dominant decision input and it is also the only one that moves.** Everything else is pinned. This trains players that the game has one input: roster OVR.
- **Recommend:** Lock the tactical chooser *open* once the plan is locked (read-only display, not disabled buttons). Make at least one chip have a chance to flip (e.g., "WARN Health" if any starter is below 70 stamina). Show how the four tactics actually shift the profile sliders.

### Match Debrief

- **Works:** Final survivor scoreboard is clean. Key Performers ranking with 1K/3C/3D notation is good *if you know the codes* (Kills / Catches / Dodges / Impact). The "Imp 20" stat is interesting but unexplained.
- **Doesn't work:**
  - **One narrative sentence per match.** "Beautiful catching form from Nia Novak against Tate Keene." That's the whole story. For 6 minutes of dodgeball this is anorexic.
  - **"11 throw events were derived from the saved event log. Based on Result proof."** This is dev-facing language leaking into the player UI.
  - "POSTGAME REPORT · 5 moments" expands to 5 generic bullets that repeat across matches (Result / Why It Happened / Roster Health / Player Movement / Next Decisions). After 2 matches I knew the structure and stopped reading.
  - "Who Grew — No growth logged this week" / "Standings Shift — No standings changes this week" / "Prospect Pulse — No prospect movement this week" — three "no change" empty states stacked is bad density.

### Roster Lab

- **Works:** Per-player card with Accuracy/Power/Dodge/Catch is the right four-stat shape. Potential rendered as "Elite ★★★☆☆" is a nice compact device.
- **Doesn't work:**
  - **Every single player is "Potential: Elite ★★★☆☆"** in my roster — and they were *all* "50-100" in the recruit screen. Either the rating ceiling is uniformly applied at career start, or this isn't really potential. (See Bug 8.1.)
  - "DEV FOCUS: BALANCED" is shown but I have no UI to change it.
  - Compact View button visible but compact-vs-default delta not obvious.
- **Recommend:** A real potential spread (low/medium/high/elite distribution) at career creation.

### Standings

- **Works:** All 7 clubs with W/L/T/Pts/WinRate/GB/ElimDiff/Approach. Correct columns for a sport.
- **Doesn't work:**
  - "Approach: Not set" for every team at S3W1 — but I had been simming for two full seasons. This suggests Approach is per-week, not per-team, and the column is misleading.
  - Aurora Sentinels is **#1 at week 1 of a fresh season with 0-0-0**. Tie-broken alphabetically, almost certainly — but I'm "YOU" at #2 with the same 0-0-0 record. Confusing as a default order.

### Dynasty Office

- **Works:** Clear hierarchy: Program Settings / Recruit / History tabs. Recruiting board with priority order, fit score, public OVR range, scout/contact/visit chips.
- **Doesn't work:**
  - **"Program Credibility: Tier D, Score 50. + 0 command-history wins and 0 losses."** After winning the championship in Season 2, the credibility section still claimed 0 wins. **This is a visible state bug.** (Bug 7.4.)
  - Weekly recruiting slots (Scout 0/3, Contact 0/5, Visit 0/1) are exposed but I won a title without using a single one — so they're optional UI noise unless the game telegraphs that engaging changes my outcomes.
  - Staff Room shows six staff with names but no attributes, no actions, no market entry — "STAFF MARKET" button at the bottom dangles.

---

## 4. Gameplay Loop Evaluation

**What was I doing most of the time?** Clicking **Lock Plan → Simulate Week → Advance to Next Week**. Three clicks per game week. That is the *entire loop* I needed to win a championship.

**Was I making meaningful decisions?** No. The Aggressive plan was pre-selected, the lineup was auto-set, the staff recommendation was "keep current plan" 100% of weeks. I never overrode any default and won the title.

**Did decisions create visible consequences?** I made no decisions, so I cannot say. The first time I had a choice that mattered was the offseason rookie sign (one-click "Sign Best Rookie") — and the resulting player (Cass Frost, 83 OVR) was on-bench all year.

**Did I understand why matches were won or lost?** I understood **wins** (we had +80 net OVR and we won 4-0 to 6-0). I did **not** understand the Season 1 final loss (also +73 net OVR, lost 0-2).

**Did roster construction matter?** Couldn't tell — the picker showed everyone as 50-100, then everyone became 70s-80s, then everyone got "Elite ★★★☆☆" potential.

**Did strategy matter?** No evidence either way. Buttons are disabled after locking; never tested an alternative.

**Did player attributes feel meaningful?** Awards screen confirmed Nia Novak's catch rating drove a "Best Catcher" award (20 catches), so *some* attribute-to-output linkage is alive. But the match log doesn't show throw/catch attempts to *verify* this.

**One-more-week energy?** No. Once I realized I would auto-pilot 3 clicks per week and likely win, I batched 10 weeks into a JS loop and the game played itself.

**Genuine hype moments?** Awards Night was the only screen that gave me a faint emotional read ("Nia Novak MVP" felt earned because she'd been our highest impact player every week). One moment. Out of two seasons.

**Flat or lifeless moments?** Every regular-season match after Week 2 of Season 1. After my third 5-0 stomp it became clear I was on rails.

**Loop quality: D-tier.** A management sim with no decision pressure, identical week-to-week clicks, and a one-sentence match payoff is a clicker, not a sim. The chassis is here — Command Center, Roster Lab, Dynasty Office, Standings, Offseason Beats — but none of the controls feed back into outcomes that I could see.

---

## 5. Simulation Trust Audit

**Did strong players feel strong?** Awards screen reflects roster strength (our players took 3 of 4 awards). At that aggregate level, yes.

**Did weak players feel weak?** Couldn't tell — opponents are anonymous outside the Lineup Leverage 2-of-6 preview.

**Did match outcomes feel believable?** Mostly: 6-0 / 5-0 / 4-0 wins against a +80-OVR-worse opponent is plausible. But of **9 matches in Season 1, 5 ended 0 opposing survivors**. A real dodgeball league has more variance than that.

**Did upsets feel earned or random?**

The Season 1 Final (`Solstice Flare 2 - 0 Westside Sages`, with Westside +73.6 net OVR) is the **single biggest sim-trust failure** in the playthrough. After 8 straight matches where the +OVR team won by 3-6 survivor margin, suddenly the +OVR team lost a shutout. No tactical narrative, no fatigue note, no "they cracked our weak side" callout. The Final's debrief was identical in structure to every other game. If this is a hard-coded "championship variance" mechanic, it is currently invisible and reads as cheating.

**Did the match log explain enough?** No. Eleven throw events in the postgame's single sentence (`11 throw events were derived from the saved event log`) — but I cannot view those events.

**Could you tell which players carried?** Awards Night yes; per-match no.

**Did fatigue/morale/form/injuries feel visible?** None of them surfaced in the debrief. "OK Health, OK Rotation" every week. Nia Novak played 5 starts in 7 days and was apparently never tired.

**Did any tactic feel useless / overpowered?** I never changed tactic, so I cannot judge. The fact that "Aggressive + Fundamentals + Balanced" won 7-of-9 matches by shutout and won the championship suggests one of two things, both bad: either *tactics don't matter*, or *the default is overpowered*.

**Did the game ever feel rigged or arbitrary?** The Season 1 final, yes.

---

## 6. Dodgeball Authenticity Audit

**What felt most like dodgeball:** Survivor count as the score, "throw / catch / dodge" stat letters, position roles (Sharpshooter, Skirmisher, Ball Hawk, Two-Way Threat, Possession Specialist, Net Specialist). The vocabulary is correct.

**What felt least like dodgeball:** The match itself. There is no court state. No "we have 4 left, they have 5, we lost a thrower." No comeback. No "they targeted our anchor and broke our line." The simulation produces a final survivor count and one prose sentence. A dodgeball match is *naturally* a momentum sport — early-elim shifts the math fast. The current debrief expresses none of that.

**Missing / under-expressed:**
- Round-by-round or phase-by-phase elimination log.
- A "court diagram" or "remaining-players ribbon" showing the state at key moments.
- Catch chains (one catch revives a teammate — currently invisible if it exists).
- Pressure moments / "headshot threats" / clutch plays.
- Team momentum — "down 3-5, regained line strength on the Novak catch."

A match readability pass would do more for this game's identity than another offseason beat.

---

## 7. Bugs and Defects

### 7.1 Recruit-roster OVR range is not the same scale as in-game OVR — Medium
- **Screen:** Career Setup Step 3 (Recruit Roster) → Command Center.
- **Repro:** Pick a player listed as `50-100 OVR`. Commit roster. Look at the same player in the Lineup Leverage card.
- **Expected:** The number labeled "OVR" on the picker matches the number labeled "OVR" on the next screen.
- **Actual:** "50-100 OVR" players show as `76-82 OVR` in Command Center / Roster Lab.
- **Impact:** Trust break on first-time player. The recruit screen looks unreliable.
- **Frequency:** Always.

### 7.2 League Rank #2 at career start, no games played — Low
- **Screen:** Command Center week-context banner, S1W1.
- **Expected:** League rank either hidden until first match or "—".
- **Actual:** Shows "League Rank #2" before a single game has been played.
- **Frequency:** Always at S1W1.

### 7.3 Standings "Approach: Not set" for all teams at S3W1, after 2 full seasons — Low/Medium
- **Screen:** Standings tab, Season 3 Week 1.
- **Impact:** The Approach column either is not implemented or resets every offseason, and the UI doesn't say which.
- **Frequency:** Always at season start.

### 7.4 Program Credibility says "0 command-history wins and 0 losses" after winning a championship — High
- **Screen:** Dynasty Office → Program Credibility, S3W1.
- **Repro:** Win Season 2 championship (8-0 record incl. playoffs). Go to Dynasty Office.
- **Expected:** Wins reflected; credibility tier elevated above D.
- **Actual:** Tier D, score 50, `+0 command-history wins and 0 losses`.
- **Impact:** Major. The credibility system is supposed to be the long-arc reward; if titles don't move it, the dynasty layer is decorative.
- **Frequency:** Confirmed once (after S2 title).

### 7.5 Plan Status panel shows `!` warning ("Confirm the staff plan to unlock match simulation") after the plan is already locked — Medium
- **Screen:** Command Center right rail after Lock Plan.
- **Expected:** Right-rail and main card agree.
- **Actual:** Right-rail keeps the warning while main card says "Locked." Sim button is enabled.
- **Frequency:** Every match week (8/8 weeks observed in S1 + sampled in S2).

### 7.6 Tactical Approach buttons become `disabled` after lock instead of read-only display — Cosmetic
- **Screen:** Command Center → Plan Editor.
- **Impact:** Visually grey buttons read as "broken" rather than "decided."
- **Frequency:** Every locked week.

### 7.7 Week 5 missing from match log in both Season 1 and Season 2 — Cosmetic (intentional bye?)
- **Screen:** Command Center sequence; full-schedule reveal also shows wk 5 absent.
- **Expected:** Either a "Bye Week" beat or contiguous numbering 1-2-3-4-5-6.
- **Actual:** Sequence jumps Wk 4 → Wk 6 silently.
- **Impact:** Reads as a missing-week bug unless the bye is surfaced.

### 7.8 Tactical Read leaks dev language — Cosmetic
- **Screen:** Match Debrief: "11 throw events were derived from the saved event log. Based on Result proof."
- **Impact:** Implementation phrasing in player UI.

### 7.9 Save menu contains 27 visible `qa-playthrough-*` orphan saves — Medium
- **Screen:** Save Menu (landing).
- **Impact:** Looks like a junk pile to a first-time user.

### 7.10 All players display "Potential: Elite ★★★☆☆" — High (if unintended)
- **Screen:** Roster Lab.
- **Impact:** Either potential is uniformly Elite (game-design issue) or the potential text is hard-coded (bug). Distinguishing players by potential is currently impossible.

### 7.11 Roster card potential label uses three filled stars and two empty for "Elite," same as "High" — Low
- **Screen:** Roster Lab.
- **Repro:** Vale Lark labeled "High ★★★☆☆"; Elio Penn labeled "Elite ★★★☆☆". Same star count.
- **Impact:** Star pattern fails to discriminate. Either Elite should have 4-5 stars or the wording is wrong.

### 7.12 Console: 0 errors, 0 warnings over entire run — *positive*, included for completeness.

---

## 8. Balance / Tuning Notes

### 8.1 Net OVR completely dominates outcomes

- **Observed:** 8 of 9 Season-1 matches won by +73 to +84 net OVR; 5 of those 8 wins were shutouts (0 opposing survivors). Season 2 was 8-0 with similar margins.
- **Why it hurts:** Trains the player that there is one game knob (roster OVR) and everything else (tactics, training, scouting, staff, fatigue) is cosmetic.
- **Recommend:** Cap the net-OVR contribution and amplify other vectors: tactical fit (rock-paper-scissors with the four approaches), per-matchup fatigue, scouting depth, opposing-coach archetype. A +80 OVR favorite should still drop 1-2 games a year and *the debrief should say why*.

### 8.2 Champion can lose with no explanation (S1 final 0-2 vs +73 favorite)

- **Why it hurts:** Worst single sim-trust failure I saw. Need post-match explanation: "Your Aggressive plan exposed Vale Lark to repeated catches; Solstice Flare's Possession scheme starved your Skirmishers of throws."
- **Recommend:** When the favored team loses by 3+ OVR per starter, *force* a tactical-narrative line that names a specific causal factor.

### 8.3 7-game season is too short

- **Observed:** Regular season is 6 visible games (week 5 missing), then 2-game playoff. Total 8 weeks. With 7 teams that means partial round-robin.
- **Why it hurts:** No room for a "midseason slump" arc, no room for player development to compound, no statistical regression to the mean.
- **Recommend:** Double round-robin (12 matches) with a 4-team playoff bracket. Adds depth without adding complexity.

### 8.4 Player development is +1 OVR for 7 of ~14 players in offseason

- **Observed:** S2 → S3 offseason: 7 players got +1 OVR; others got 0. No player got -1 (age regression).
- **Why it hurts:** Aging dynasty is the heart of a sports management game. With everyone trending up at +1/season and no regression, every roster bloats over time.
- **Recommend:** Aging curve. Players >=27 should occasionally regress -1 to -2. Young prospects should sometimes pop +3-4.

### 8.5 Sign Best Rookie is a one-click no-decision

- **Observed:** Signed one rookie post-S1 (Cass Frost). They went straight to bench, won Best Newcomer because the rest of my newcomer pool was empty.
- **Recommend:** Make rookie signing a slate of 3-5 candidates with different role profiles and trade-offs (high ceiling vs ready-now). Currently it's not a decision.

---

## 9. Fun Factor Report

| Category | Rating |
|---|---|
| First-time onboarding | **7/10** — fast, clean, friction-free |
| UI clarity | **6/10** — glanceable but key warnings conflict (Plan Status `!` vs Locked) |
| Roster management fun | **3/10** — uniform potential, no movement |
| Match watching fun | **2/10** — one sentence + a score |
| Strategic depth | **2/10** — defaults can't be improved upon |
| Sim trust | **4/10** — regular season feels honest; the final felt arbitrary |
| Season pacing | **3/10** — 8 weeks total, no narrative arc |
| Player attachment | **4/10** — Nia Novak felt real because of awards continuity; no one else |
| Replayability | **2/10** — same 3-click loop yields the same outcome |
| Championship chase excitement | **3/10** — got there in 2 seasons of pure auto-pilot |

**What made me want to keep playing:** Lineup Leverage card; Awards Night.
**What made me want to stop playing:** Realizing the four tactical approach buttons were window dressing.
**Most satisfying moment:** Nia Novak winning MVP after a 20-catch season — the only on-screen confirmation that *something* in the sim cared about an individual player's attribute.
**Most frustrating moment:** Losing the Season 1 final 0-2 with no narrative explanation.
**Did the game create stories I cared about?** Marginally — only Nia Novak.
**Did winning the title feel meaningful?** No — I knew at week 2 of Season 2 that I would win. The result felt determined, not earned.

---

## 10. Priority Fix List

### P0 — Must fix before more content

- **Fix Program Credibility to count championship wins.** Dynasty Office still showed "0 wins, Tier D" after a title. (Bug 7.4.)
- **Surface a tactical-narrative cause when the favored team loses.** Especially in playoffs. A debrief without a "why" kills sim trust. (Bug ref Section 5.)
- **Reconcile recruit-OVR with in-game OVR.** Either present one number, or label "Range 50-100 = current 50, potential 100" with a tooltip. (Bug 7.1, 7.10.)
- **Make at least one tactical lever actually change match outcome variance.** Currently no incentive to ever leave the default; that turns the Command Center into a Confirm button.
- **Garbage-collect or hide `qa-playthrough-*` saves on the landing screen.** (Bug 7.9.)

### P1 — Must fix before serious demo

- **Replace the postgame's single-sentence "tactical read" with a 4-6 line round-by-round survivor ribbon** — e.g., "T1: Westside 6-6, T2: Westside 5-6 after Novak catch, T3: Westside 5-4..."
- **Stop showing the right-rail Plan Status `!` warning after Lock Plan.** (Bug 7.5.)
- **Display the disabled tactical approach as a "Locked: Aggressive" read-only chip**, not greyed buttons. (Bug 7.6.)
- **Add real potential spread** (low/medium/high/elite distributed across the prospect pool). All-Elite is no information. (Bug 7.10.)
- **Resolve Week 5 (bye?) explicitly** with a "Bye Week" beat or contiguous numbering. (Bug 7.7.)
- **Acknowledge League Rank only after at least one match has been played.** (Bug 7.2.)
- **Fix Standings "Approach" column** to either persist last-set approach or hide the column outside of in-week views. (Bug 7.3.)

### P2 — Strong improvements

- **Lengthen the season to 12 regular-season weeks + a 4-team bracket.** Gives stories room.
- **Add an aging/regression curve.** +1 across the board is unsustainable. (8.4.)
- **Convert "Sign Best Rookie" into a slate of 3 candidates** with role/potential trade-offs. (8.5.)
- **Add a per-week opponent style chip ("Aggressive / Control / Defensive / Balanced")** in the Standings tab and Lineup Leverage card so the player learns the rock-paper-scissors.
- **Strip the dev-language "11 throw events were derived from the saved event log. Based on Result proof"** from the debrief. (Bug 7.8.)
- **Expand Lineup Leverage default from 2 of 6 matchups to all 6 by default**, since vertical real estate is available at 1440×900.
- **Give the Roster Lab a "DEV FOCUS" editor.** Currently it shows the value but no control.

### P3 — Nice-to-have polish

- **Differentiate the Elite vs High potential stars** so they're visually distinct. (Bug 7.11.)
- **Distinguish "you" in Standings** with a stronger row treatment than a small "YOU" pill.
- **Sort the Save List by recency by default.**
- **Add a Staff Market screen** behind the dangling "STAFF MARKET" button.
- **Show coach archetype effect on the Command Center** ("Tactical Mastermind: +5% in-match adjustment value") — currently the archetype is invisible after creation.

---

## 11. Final Verdict

**"Needs gameplay loop repair before more systems."**

The plumbing works, the UI chassis is the right shape, and the dynasty skeleton (Awards / Schedule Reveal / Offseason Development / Recruiting board) is laid out. But the player makes no decisions, the match output is a single sentence, and the one critical loss in two seasons was unexplained — which is exactly the failure mode a sim cannot afford.

Concretely, before adding more depth (more staff, more recruiting, more tactical knobs) the game needs **three specific repairs**:

1. **A real reason to ever change the default plan.** Right now the staff says "Keep current plan" 100% of weeks and you can win a title without overriding it. The four-tactic chooser must have a *visible* effect on the four tactical profile sliders, and tactical fit must affect outcomes enough that the +80 OVR favorite still loses occasionally — *and the debrief must say why*.

2. **A round-by-round or phase-by-phase match readout.** Dodgeball is a momentum sport. A survivor count + one sentence will never feel like dodgeball. A 4-6 line "moments ribbon" or per-round survivor ledger would transform the match-watching experience.

3. **Wire the dynasty layer to actual results.** Program Credibility ignoring my championship is the moment a player realizes the long arc isn't real. Fix that first; it costs nothing structurally but signals everything.

If those three land, this becomes a B-tier management sim shell ready for content. Until they land, it's a clicker with a great wireframe.

---

**Run artifacts:** Screenshots saved at the project root: `01_landing.png`, `02_build_scratch.png`, `03_command_center.png`, `04_postgame.png`, `05_after_season1.png`, `06_offseason.png`, `07_championship.png`, `08_roster.png`, `09_roster_tab.png`, `10_standings.png`, `11_dynasty.png`.
