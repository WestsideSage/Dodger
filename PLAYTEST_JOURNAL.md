# Dodgeball Manager Championship Playtest Journal

Playtester: Codex, acting as a first-time dynasty manager  
Date: 2026-06-10  
Repo: `C:\GPT5-Projects\Dodgeball Simulator`  
Mode: UI-only browser playthrough, no source/docs/tests/save inspection  

## Setup Notes

- Installed with `python -m pip install -e ".[dev]"`.
- Launched with `python -m dodgeball_sim`.
- The launcher output did not print a one-time tokenized URL. It started on `http://127.0.0.1:8000`, and the browser accepted that bare URL rather than rejecting it.

### Issue Log

1. **[Confusing / setup trust] Launch token mismatch**
   - Screen: startup / first browser load.
   - Action: launched the game with the requested command and checked startup output.
   - Expected: a one-time tokenized URL, with bare localhost rejected.
   - Actual: no token was printed; `http://127.0.0.1:8000/` loaded the game.
   - Why it matters: setup instructions and live behavior disagree before play starts.

2. **[Confusing] Season preview roster-strength labels are hard to parse**
   - Screen: Season 1 preview after committing the starting roster.
   - Action: reviewed the summary before entering Command Center.
   - Expected: a direct readout of my expansion roster's strengths and weaknesses.
   - Actual: the screen said `Roster strength` -> `Sharpshooter group - 56 avg OVR` and `Watch area` -> `Two-Way Threat group - 46 avg OVR`. I could infer this means Vale Kerrigan is the best archetype group and Imani Petrov's group is weakest, but it did not explicitly say why those groups matter.
   - Why it matters: the preview is a good time to teach me what my roster is good at, but this made me translate labels instead of plan.

3. **[Confusing] Scouting language contradicts itself and some labels run together**
   - Screen: Week 1 Command Center, Opponent File after scouting Lunar Syndicate.
   - Action: clicked Scout Opponent.
   - Expected: hidden tendency rows become readable and explain what I learned.
   - Actual: the screen said `All tendency reads revealed from tape` and then also `No tape yet`; tendency labels rendered as `Aggressiveplaybook`, `Their starsplaybook`, `Opportunisticplaybook`, `All inplaybook`, and `Centerplaybook`.
   - Why it matters: scouting did real work, but the copy made me less confident about whether I had actual tape or just default identity guesses.

4. **[Confusing] Replay set-score strip mixes final score and current-moment score without enough labeling**
   - Screen: Week 1 full replay.
   - Action: opened full replay after an 0-11 loss.
   - Expected: final match score and current replay moment state are visually distinct.
   - Actual: header correctly showed Lunar Syndicate 11, Glassworks 0; the set strip initially showed `0-0 on game points` at Game 1 Tick 1, then `2-0 on game points` after jumping to Game 3 Tick 59.
   - Why it matters: this is probably current replay state, not a data mismatch, but it reads like a contradiction until you reason it through.

5. **[Confusing] Dynasty Office week labels disagree**
   - Screen: Dynasty Office after Week 2 match, before advancing to Week 3.
   - Action: opened Dynasty Office from the Week 2 debrief.
   - Expected: one clear current week/state label.
   - Actual: page banner said `Season 1 -- Week 02` while the office panel said `Front Office - Week 03`.
   - Why it matters: I eventually understood this as between-week front-office work for the next week, but it initially made me wonder whether I had advanced or not.

6. **[Wrong] Debrief recruiting recommendation goes stale after front-office actions**
   - Screen: Week 2 debrief after visiting Dynasty Office and returning to Command Center.
   - Action: raised River Dubois from 37% interest to 69% in Dynasty Office, then returned to the debrief.
   - Expected: recommendation either updates or is clearly marked as the original postgame recommendation.
   - Actual: debrief still said `Warm up River Dubois - High fit (65) but only 37% interest. Contact or visit to close the gap.`
   - Why it matters: I had already done exactly that. Seeing the old number makes the game feel unaware of my front-office work.

7. **[Confusing] Changing Weekly Intent appears to reset Development focus**
   - Screen: Week 4 Command Center.
   - Action: selected Youth acceleration, then changed Weekly Intent from Defensive to Aggressive.
   - Expected: tactical intent and development focus stay independent unless the game explains a linkage.
   - Actual: after Aggressive applied, Development focus showed Balanced again and had to be reselected.
   - Why it matters: I had an active River Dubois promise requiring a focused dev plan, so an unnoticed reset could break a player promise.

8. **[Confusing] Recruiting recommendation says `only 96% interest`**
   - Screen: Week 4 debrief after Northwood Ironclads.
   - Action: reviewed next-best improvements after raising Noor Perez to 96% interest.
   - Expected: the recommendation should stop asking me to warm up a recruit who is nearly maxed, or explain that 100% is required.
   - Actual: `Warm up Noor Perez - High fit (66) but only 96% interest. Contact or visit to close the gap.`
   - Why it matters: 96% reads like a strong close, not a weakness. The word `only` makes the recommendation feel formulaic.

9. **[Wrong] Bye week screen has conflicting week numbers**
   - Screen: bye week after advancing from Week 4.
   - Action: advanced from Week 4 debrief/front-office work.
   - Expected: one clear current week label.
   - Actual: banner said `Season 1 -- Week 06`, while Week Context said `W05 · Bye Week` and the match panel said `Week 05`.
   - Why it matters: the game is asking me to lock a bye week, so I need to know whether I am making Week 5 or Week 6 decisions.

10. **[Wrong / confusing] Recruiting buttons can appear to click without spending the action**
   - Screen: Dynasty Office, Week 7 recruiting board.
   - Action: pressed Visit / Contact buttons on Mara Hassan, Mara Parr, Sloane Park, and Niko Hansen after River Dubois reached 100%.
   - Expected: every accepted click either changes the recruit and decrements the visible action counter, or clearly refuses the action.
   - Actual: some clicks returned me to the board but did not change interest, status, or the counters. I only caught it because I audited `Scout`, `Contact`, and `Visit` remaining after every attempt.
   - Why it matters: a normal player could waste a recruiting week without realizing their intended action never applied.

11. **[Wrong] Postgame advice says a 100% recruit has `only 100% interest`**
   - Screen: Week 6 and Week 7 debriefs.
   - Action: closed Noor Perez to 100%, then returned to Command Center and later completed Week 7.
   - Expected: the recruiting recommendation should disappear or say Noor is closed.
   - Actual: Next best improvement said `Warm up Noor Perez - High fit (66) but only 100% interest. Contact or visit to close the gap.`
   - Why it matters: the copy is plainly false at max interest and makes the assistant layer look disconnected from the recruiting state.

12. **[Confusing] Final standings show elimination differential as zero for every club**
   - Screen: Season 1 Offseason Recap, Final Regular-Season Table.
   - Action: reviewed the table after missing playoffs.
   - Expected: `Elim +/-` should help explain team strength across the season.
   - Actual: every club showed `0`, including the 5-1 champion-level teams and my 0-6 club.
   - Why it matters: a stat column that is uniformly zero looks broken or unpopulated.

13. **[Wrong / high impact] Promised target vanished during Signing Day after first signing**
   - Screen: Season 1 Signing Day.
   - Action: signed Noor Perez first, intending to sign promised recruit River Dubois second.
   - Expected: the UI should warn that each signing triggers contested rival bids and can remove other targets, especially players with open promises.
   - Actual: River Dubois disappeared from the list after Noor signed. I could no longer keep River's development-priority promise despite 100% interest.
   - Why it matters: player promises are framed as serious, but the signing flow can make them impossible to keep without a clear warning.

14. **[Confusing] Signing slots and roster cap conflict**
   - Screen: Season 1 Signing Day and Class Report.
   - Action: entered Signing Day with `3 signings remain` and roster `10 / 12`; signed Noor Perez and Callum Saito.
   - Expected: the game should explain that only two players can be signed unless a cut/roster move is possible.
   - Actual: after two signings the class ended at `2/3 slots used` because roster size hit 12/12.
   - Why it matters: I planned around three signings, but the true capacity was two.

15. **[Wrong] Noor Perez promise broke before she could play a Season 2 match**
   - Screen: Season 2 Dynasty Office, after Week 2.
   - Action: checked promises after signing Noor Perez and playing one Season 2 match.
   - Expected: early-playing-time promise should remain open until the season gives me enough matches to satisfy or fail it.
   - Actual: promise was already marked broken: `Player appeared in only 0 matches this season (threshold: 6)`.
   - Why it matters: the promise failed before I had a fair chance to act on it, and it cost credibility.

16. **[Wrong / confusing] Command Center and Standings disagree on playoff rank**
   - Screen: Season 2 Week 7 Command Center vs Standings.
   - Action: checked standings before the regular-season finale.
   - Expected: both screens should agree on my rank and playoff cushion.
   - Actual: Command Center showed rank `#4` and said `Outside the top three`; Standings showed Glassworks `#3`, in playoff position, one point behind #1, with a two-point cushion.
   - Why it matters: playoff race decisions depend on exact rank, points, and tiebreak context.

17. **[Wrong] Playoff semifinal copy says it is the final**
   - Screen: Season 2 Week 8 playoff semifinal vs Aurora.
   - Action: reached the playoffs as Glassworks.
   - Expected: semifinal copy should say winner advances to the final.
   - Actual: `This Week The Final. Win it and the banner is yours — there is no next week.` while the frame also said `Playoff Semifinal`.
   - Why it matters: it overstates the stakes and makes the bracket state feel unreliable.

18. **[Confusing] Semifinal tiebreaker seeding is hard to trust after prior rank drift**
   - Screen: Season 2 playoff semifinal debrief.
   - Action: drew Aurora 9-9 and was eliminated by higher-seed tiebreaker.
   - Expected: the game should make the semifinal seed order unmistakable before and after the match.
   - Actual: debrief said the `#2 seed` advanced, but earlier Week 7/standings/debrief surfaces had implied or shown Glassworks as high as #2. The final result may be correct, but I could not confidently trace the seed.
   - Why it matters: playoff elimination by tiebreaker requires especially clear proof.

19. **[Wrong] `Fix is squad strength` appears after losses where Glassworks was favored**
   - Screen: Season 3 Week 2 vs Aurora and Week 6 vs Lunar debriefs.
   - Action: entered Aurora as +20 starter OVR favorite and Lunar as +12 starter OVR favorite.
   - Expected: if a favored team loses, the debrief should identify the tactical/statistical failure, not say the roster was simply outclassed.
   - Actual: both losses used `Outclassed across the sets` and said `the fix is squad strength, not luck`.
   - Why it matters: this directly contradicts pre-match matchup evidence and makes the lesson untrustworthy.

20. **[Confusing] Offseason auto-reorder checkbox does not keep the lineup current after growth**
   - Screen: Season 3 roster / lineup editor.
   - Action: started Season 3 with `Auto-reorder lineup each offseason` checked.
   - Expected: the best current six should already be seated after offseason development.
   - Actual: 69 OVR Noor Perez and 69 OVR Callum Saito remained benched behind 68 OVR Nia Rhodes until I manually pressed `Auto-Assign`.
   - Why it matters: the player can unknowingly carry an outdated lineup into important matches.

21. **[Confusing] Development focus reset again on title week**
   - Screen: Season 3 playoff final vs Lunar Syndicate.
   - Action: banked the semifinal after using Tactical drills, then reviewed the final-week Command Center.
   - Expected: Tactical drills should persist into the final, or the game should clearly tell me a new week requires a fresh development choice.
   - Actual: the development focus was back on Balanced and had to be manually changed to Tactical drills before simming the final.
   - Why it matters: the final week determines the season-end development focus, so an unnoticed reset can silently change offseason growth.

22. **[Wrong / high impact] Championship banner reports the wrong score**
   - Screen: Season 3 playoff final debrief after beating Lunar Syndicate.
   - Action: won the championship 13-12.
   - Expected: the champion banner should repeat the actual final score.
   - Actual: the page header said `Glassworks` and `0-0 over Lunar Syndicate to take the title`, while the score panel below correctly showed Lunar 12, Glassworks 13.
   - Why it matters: this is the biggest celebratory moment in the game, and the first line of the title screen contradicts the match result.

## Club Identity

- Save: Glassworks Championship Run
- Club: Cleveland Glassworks
- Colors: Emerald preset
- Coach: Nia Calder
- Coach backstory: former public-school athletics director who built a citywide dodgeball circuit from donated gym time.
- Archetype: Recruiting Legend.
- Strategic expectation: early seasons should be about surviving with a balanced roster while Calder's recruiting edge helps close the talent gap.

## Starting Roster

I drafted the maximum 10 players because a long season should reward depth:

- Wren Mendoza, Possession Specialist, 56 OVR
- Vale Kerrigan, Sharpshooter, 56 OVR
- Imani Crosby, Hit-and-Run, 53 OVR
- Noor Griffin, Hit-and-Run, 52 OVR
- Nia Rhodes, Hit-and-Run, 52 OVR
- River Rousseau, Skirmisher, 52 OVR
- Cass West, Net Specialist, 51 OVR
- Rin Johansen, Hit-and-Run, 50 OVR
- Sable Ivanov, Possession Specialist, 49 OVR
- Imani Petrov, Two-Way Threat, 46 OVR

Role-count feedback after selection: Throwing 3/2+, Catching 4/2+, Survival 7/1+. This was one of the clearest early decision aids.

Screenshots saved outside the repo at `C:\Users\Maurice\AppData\Local\Temp\dodgeball-playtest-shots`.

## Season 1

### Preseason

Record: not started.

Decision notes:

- I built around Wren Mendoza and Vale Kerrigan as the best current players.
- I expected a survival-heavy team to keep games alive, but with only three throw-capable players I worried we might struggle to finish wipe-outs.
- The game made the playoff target clear: top 4 of 7 after seven weeks, with our bye in Week 5.

### Week 1 vs Lunar Syndicate

Record after week: 0-1.

Pre-match read:

- We were a huge underdog: `-81 net starter OVR`.
- Lunar Syndicate's key threat was Yuki Rodriguez, Sharpshooter, 71 OVR.
- Scouting said their default identity leaned Aggressive, targeted stars, Opportunistic catching, all-in opening rush, center rush target.

Decision:

- I used the required scouting action.
- I changed Weekly Intent from Balanced to Defensive because the Counter Read said `Adjust to Defensive`; the plan updated to Patient / Play safe / Hold back and risk dropped from Medium to Low.
- I confirmed the default six rather than benching anyone because they were my best current players.

Result:

- Lost 0-11. Every game point went Lunar Syndicate 1-0.
- Primary factor: Catch disparity, high confidence. They had 22 catches to our 0.
- Key performers were all Lunar players: Sasha Fern (26K, 8C), Yuki Rodriguez (9K, 2C), Lin Kone (1K, 5C).

Traceability verdict:

- Strong: the debrief showed our actual locked plan (`Patient`, `Play safe`, `Spread`) and showed their catching as the reason we got destroyed.
- Strong: the full replay jumped to a cited swing play, Lin Kone catching Vale Kerrigan and returning Nola Diallo.
- Weak: I could not tell whether Defensive helped at all. Losing badly was believable, but the game did not say whether the plan reduced injury/fatigue, slowed the pace, or merely made us less aggressive while still getting wiped out.

### Week 2 vs Aurora Sentinels

Record after week: 0-2.

Pre-match read:

- We were still a big underdog, around `-76 net starter OVR` after my lineup change.
- Aurora's key threat was Ayo Smirnov, Net Specialist, 67 OVR.
- Counter Read said the Defensive plan still fit.

Decision:

- Opened Roster after Week 1 debrief told me to rest Wren Mendoza.
- Lineup Editor taught that slot order affects play, role fit can grant +3 action stats in slots 1-4, and opening rush order can matter.
- Benched Wren Mendoza (56 OVR, 46 STA, high ceiling) for Cass West (51 OVR, 51 STA, Net Specialist) to respect fatigue advice and improve catching reliability.
- Changed development focus to Youth acceleration because every rostered player is 18-21 and River Dubois's later promise will require a focused youth/dev plan.
- Scouted, confirmed lineup, kept Defensive.

Result:

- Lost 1-9. We took Game 1, then Aurora took the next nine.
- Primary factor again: Catch disparity. Aurora had 16 catches to our 0.
- Cass West finished as our best performer and made the top-three performers list with 11K, so the lineup change at least created visible impact.
- The debrief recommended resting River Rousseau next and continued to recommend warming up River Dubois.

Traceability verdict:

- Strong: Cass replacing Wren was visible in Command Center and the debrief; Cass actually showed up as our best performer.
- Strong: Youth acceleration was explicitly acknowledged in Training Impact and described as the current end-of-season growth focus.
- Weak: there was no explicit feedback that Wren recovered from rest or that fatigue improved because of the rotation.

### Week 2 Front Office / Week 3 Recruiting Prep

Decision:

- Targeted River Dubois because the game repeatedly recommended them: Possession Specialist, 65 fit, interest 37%, OVR estimate 34-84.
- Scouted River first. OVR narrowed to 44-74, which made the action feel real.
- Contacted River and used the only visit slot on River. Interest rose from 37% to 49%, then the visit landed 49% to 69%.
- Made River a Development priority promise. Promise text says I must run focused dev at least three weeks and keep them rostered.
- Used remaining contacts/scouts on Noor Perez, Callum Saito, Mara Hassan, and Sloane Park. Noor and Callum rose to 64%; Mara and Sloane rose to 49%.

Traceability verdict:

- Strong: recruiting actions have immediate, named, numeric effects. This was the clearest non-match evidence that a decision mattered.
- Mixed: I had to verify remaining action slots because some attempted clicks did not land at first; the UI did eventually show 0 scout, 0 contact, 0 visit remaining.

### Week 3 vs Granite Specters

Record after week: 0-3.

Decision:

- Continued Youth acceleration to satisfy River Dubois's development-priority promise.
- Rested River Rousseau and brought Wren Mendoza back into the six, hoping the added ceiling/catching would help.
- Kept Defensive because the counter-read still said current plan fit.

Result:

- Lost 0-14, the worst defeat yet.
- Primary factor: Catch disparity again, this time 0-27.
- No Glassworks player made the top performers.

Traceability verdict:

- Bad for agency: three straight Defensive/Play safe weeks all produced the same failure mode, including zero catches by us.
- The game explained the losses, but it made the recommended plan feel like a trap or at least not useful for a weak roster.

### Week 3 Front Office / Week 4 Recruiting Prep

Decision:

- Credibility fell from 46 to 45 after the 0-3 start, and the board's fit scores slipped by about a point. That made poor match results feel connected to recruiting.
- Reinvested heavily in Noor Perez, River Dubois, and Callum Saito.
- Visited Noor Perez and promised early playing time. Noor reached 96% interest.
- River reached 81% interest. Mara Hassan and Sloane Park reached 61%.

Traceability verdict:

- Strong: credibility factors explicitly listed 0 wins, 3 losses, and 2 weeks spent prioritizing youth development.
- Strong: visit/contact feedback gave exact before/after interest jumps.
- Weak: the action buttons were easy to mis-click when scrolling; I had to re-check remaining slots several times to make sure I actually spent the budget.

### Week 4 vs Northwood Ironclads

Record after week: 0-4.

Decision:

- Switched Weekly Intent to Aggressive despite the Counter Read recommending Defensive.
- Reason: Defensive/Play safe produced three straight zero-catch losses. I wanted to test whether `Go for catches` would actually change the match story.
- Re-selected Youth acceleration after the intent change reset it.

Result:

- Lost 3-12, still noncompetitive but no longer inert.
- Primary factor changed to `Outclassed across the sets` instead of catch disparity.
- The result explicitly said: `Go for catches: Vale Kerrigan plucked it clean and Cass West sprinted straight back in.`
- Tactical Read included both opponent catch punishment and our own catch moment: Imani Crosby caught Saga Kone's throw.

Traceability verdict:

- Strong: changing to Aggressive visibly changed the locked plan, risk, catch posture, target focus, and debrief language.
- Strong: this was the first match where my choice clearly produced a different kind of evidence.
- Still weak competitively: 3 game points is progress, not a path to a championship.

### Week 5 Bye

Record: 0-4.

Decision:

- Kept Youth acceleration active because River Dubois's promise explicitly depends on focused development.
- Did not touch lineup or tactics because there was no match.

Result:

- Bye report said `Youth acceleration held through the bye`.
- This was useful: the game confirmed the week counted toward the development strategy rather than leaving me to guess.

Traceability verdict:

- Strong: the bye gave direct feedback that my development choice persisted.
- Wrong: the page showed conflicting week labels, logged above.

### Week 6 vs Solstice Flare

Record after week: 0-5.

Decision:

- Stayed Aggressive because Week 4 proved `Go for catches` could change the match story.
- Kept Youth acceleration for the River promise.
- Scouted/confirmed the opponent rather than guessing.

Result:

- Lost 5-10, but this was the best match yet.
- Debrief credited `Go for catches`: Nia Rhodes caught a ball and Imani Crosby sprinted back in.
- Tactical read named Noor catching Remy Dusk, and Wren re-entering.
- Cass West was our club's best player with 10 knockouts and 2 catches.

Traceability verdict:

- Strong: Aggressive continued to produce visible catch and re-entry evidence.
- Mixed: the team was still 0-5, but I finally had a plausible style for an underdog roster.
- Weak: the debrief still recommended warming Noor Perez despite Noor already being at 100% interest.

### Week 6 Front Office / Week 7 Recruiting Prep

Decision:

- Closed River Dubois from 93% to 100% with a contact.
- Used the visit on Mara Hassan, who rose from 85% to 100%.
- Scouted Mara Parr and Niko Hansen. Mara Parr narrowed from 18-68 to 28-58; Niko narrowed from 13-63 to 23-53.
- Contacted Mara Parr to 53% and Sloane Park to 97%. Used the final scout on Rin Zane mostly to avoid wasting a slot.

Board after actions:

- Noor Perez: 100%, promised early playing time.
- River Dubois: 100%, promised development priority.
- Callum Saito: 100%.
- Mara Hassan: 100%.
- Sloane Park: 97%.
- Mara Parr: 53%.
- Rin Zane: 51%.
- Niko Hansen: 41%.

Traceability verdict:

- Strong: successful recruiting actions give exact before/after numbers, which is some of the clearest agency in the game.
- Wrong: some Visit/Contact attempts looked like they clicked but did not spend the action. I had to keep re-checking counters and repeat actions with refreshed controls.

### Week 7 vs Harbor Tidebreakers

Record after week: 0-6.

Decision:

- Opened the lineup editor because Wren Mendoza was still at 46 stamina and the debrief kept recommending rest.
- Used `Auto-Assign: seat the optimal starting six now`. It moved Wren to Captain and replaced Cass West with River Rousseau, leaving the starting six as Wren Mendoza, Imani Crosby, Vale Kerrigan, River Rousseau, Noor Griffin, and Nia Rhodes.
- Kept Aggressive despite the Counter Read recommending Defensive. My reasoning: Defensive had produced three zero-catch losses, while Aggressive produced the only meaningful Glassworks catch/re-entry evidence.
- Scouted Harbor Tidebreakers. The report revealed 5/5 tendencies: Aggressive, Their stars, Opportunistic catches, All in, Center. They were 4-1, led by 69 OVR Dray Slate, and we were a -76 starter OVR underdog.
- Kept Youth acceleration to satisfy the River Dubois promise.

Result:

- Lost 2-15.
- Primary factor: Catch disparity, 13-24 against us.
- The result text credited the catch posture, but the named decisive catch was by Harbor's Brin Moreau, not us.
- Tactical read did show our lineup change mattered: River Rousseau caught River Bolt and Vale Kerrigan re-entered.
- Next best improvement still said `Warm up Noor Perez` even though Noor had 100% interest.

Traceability verdict:

- Strong: Auto-Assign produced a visible lineup change, and River Rousseau appeared in the match evidence.
- Strong: Aggressive made catches happen, but not necessarily for us; the risk was visible.
- Weak: the advice loop still pushed stale/noisy recommendations, and the season ended without any sense that a win was near.

### Season 1 Offseason

Final regular season:

- Glassworks finished 7th of 7 at 0-6. Top four made the playoffs.
- Lunar Syndicate won the championship as the #3 seed, beating Harbor Tidebreakers 11-10 in the final.
- Awards gave the league useful texture: Lex Mendoza MVP, Dray Slate best thrower, Cruz Ibarra best catcher, Brin Moreau best newcomer.

Development:

- Youth acceleration paid off massively.
- Wren Mendoza jumped 56 -> 72 OVR.
- Imani Crosby jumped 53 -> 69.
- Noor Griffin 52 -> 66, Vale Kerrigan 56 -> 66, Cass West 51 -> 65, River Rousseau 52 -> 64, Nia Rhodes 52 -> 64.
- This was the first time the 0-6 season felt like it had a point: I had been losing now to grow later.

Recruiting / Signing Day:

- Rookie class preview said there were no 70+ rookies and 12 veterans were available.
- Signed Noor Perez first. Contested round won: my offer 97 beat Lunar Syndicate's 83; interest 100% strengthened it. Noor's scouted range 46-76 resolved to verified OVR 57.
- River Dubois disappeared after Noor signed, so I could not sign the promised development-priority target.
- Signed Callum Saito second for Two-Way depth. Callum verified at OVR 60.
- Class ended with only 2/3 slots used because roster reached 12/12.

Traceability verdict:

- Strong: development and contested signing both provided exact before/after evidence.
- Strong: the offseason made the larger dynasty loop come alive; the club finally had a plausible Year 2 roster.
- Bad: River disappearing during Signing Day damaged trust. I had spent weeks managing his promise, and the UI did not warn me that a promised 100% target could be lost between picks.

## Season 2

### Regular Season

Record: 4-2, made the playoffs.

Key decisions:

- Kept Youth acceleration through the Week 1 bye because the roster remained young and Season 1 proved the payoff.
- Used the grown core rather than chasing more tactical gimmicks: Balanced / Mixed / Spread / Opportunistic stayed the default because the Counter Read kept endorsing it.
- After Week 4, used Auto-Assign again and discovered Cass West (65 OVR) had been benched behind lower-OVR players after the new signings. Auto-Assign restored Cass and Nia Rhodes to the win-now six.
- In recruiting, avoided new promises after River and Noor broke; focused on Rowan Cole, Zara Rodriguez, Remy Garrison, Luca Cross, and Talia Vale instead.

Results:

- Week 2: beat Solstice Flare 12-2. First win in club history. Primary factor: catch disparity 25-11. Vale Kerrigan 28K/7C, Wren Mendoza 14K/8C. Full replay backed the win with named catch/re-entry events from Noor Griffin, Wren, and Vale.
- Week 3: lost 6-9 to Lunar Syndicate. This felt like progress against the defending champion, not a collapse.
- Week 4: beat Harbor Tidebreakers 9-5 after Auto-Assign fixed the lineup. Cass West immediately appeared as a top performer.
- Week 5: lost 6-8 to Aurora Sentinels. Primary factor: opening rush deficit; we fell down 5 bodies by tick 4.
- Week 6: beat Granite Specters 9-6. Wren carried with 35 eliminations and Imani Crosby made 6 catches.
- Week 7: beat Northwood Ironclads 11-3, with a 30-12 catch advantage. Wren posted 29K/6C and Glassworks moved into the playoff picture.

Traceability verdict:

- Strong: roster development, Auto-Assign, and catch disparity all felt visible and causally connected to wins.
- Strong: the Aurora loss gave an actionable diagnosis: opening rush. That directly shaped my playoff plan.
- Weak: the rank/playoff messaging drifted across screens, so I trusted Standings more than Command Center.

### Playoff Semifinal vs Aurora Sentinels

Decision:

- Opened the policy editor because Aurora had beaten us with an opening-rush deficit.
- Kept the broader Balanced plan but changed Opening Rush to `All in` and target to `Center`.
- Reason: I wanted to respond to the exact prior failure without abandoning Mixed/Spread/Opportunistic, which had powered the late-season wins.

Result:

- Drew 9-9.
- Eliminated on higher-seed tiebreaker.
- Primary factor said catch disparity favored us 27-16.
- Imani Crosby was our standout with 20K and 9 catches.

Traceability verdict:

- Strong: the policy editor itself is one of the best screens in the game; it explains that opening rush is sim behavior and names the risk.
- Mixed: the tactical adjustment plausibly helped, because we did not repeat the opening-rush collapse, but the debrief did not explicitly say the all-in center rush changed the early state.
- Bad: being eliminated by seed after multiple rank/seeding inconsistencies made the ending less trustworthy than the match evidence itself.

### Season 2 Offseason

League result:

- Lunar Syndicate repeated as champion, beating Aurora Sentinels 12-8 in the final.
- Awards made the league feel persistent: Ayo Slate won MVP, Nola Aura won Best Thrower, Wren Mendoza won Best Catcher with 51 catches, and Callum Saito won Best Newcomer.

Development:

- Youth acceleration turned the club from expansion fodder into a title threat.
- Wren Mendoza rose to 78 OVR.
- Imani Crosby rose to 76.
- Cass West and Noor Griffin reached 71.
- Vale Kerrigan reached 70.
- Noor Perez and Callum Saito reached 69.
- Most of the remaining roster landed around 67-68.

Signing Day:

- I had three signing slots, but the roster was already full at 12/12.
- Signing Day skipped straight to 0/3 remaining without letting me improve the roster.

Traceability verdict:

- Strong: development is a real lever. Choosing Youth acceleration for two seasons clearly created this roster.
- Mixed: the full-roster lock is understandable, but the game does not teach roster planning well enough before the signing window closes.

## Season 3

### Season Preview / Week 1 Bye

Decision:

- Changed development focus from Youth acceleration to Tactical drills. My reasoning: the roster was no longer merely young; it needed late-season tactical IQ and playoff conversion.
- Kept the existing balanced policy foundation because the team was now stronger than most opponents on starter OVR.

Result:

- Season preview labeled Glassworks as a Possession Specialist group with 73 average OVR.
- Week 1 was a bye and the game confirmed Tactical drills held through the bye.
- The season theme felt right: no longer a novelty club, now a hungry contender.

Traceability verdict:

- Strong: the development-focus feedback is consistent and clear.
- Weak: the preview labels still take effort to parse. I understood the roster was strong only after comparing the numbers myself.

### Week 2 vs Aurora Sentinels

Record after week: 0-1.

Decision:

- Stayed Balanced / Mixed / Spread / Opportunistic against Aurora because the starter OVR edge was huge and the regular-season match was not yet an elimination game.
- Tactical drills stayed active.

Result:

- Lost 7-9 despite being a +20 net starter OVR favorite.
- Debrief said `Outclassed across the sets; fix is squad strength`.
- Imani Crosby was excellent with 22K/8C, but Lux Stone carried Aurora with 41K/3C.
- After the loss, I inspected the lineup. The `Keep top six auto-ordered` checkbox was on, but the six were stale. Running Auto-Assign moved Noor Perez into the lineup and benched Nia Rhodes / Callum Saito.

Traceability verdict:

- Wrong: telling me the fix was squad strength after I entered as a heavy OVR favorite felt false.
- Wrong: an enabled auto-order checkbox not keeping the best six active is a trust problem.
- Useful: the loss gave a clear Aurora star name, but the advice text undercut it.

### Week 3 vs Solstice Flare

Record after week: 1-1.

Decision:

- Played the corrected lineup: Wren Mendoza, Imani Crosby, Noor Griffin, Cass West, Vale Kerrigan, Noor Perez.
- Stayed Balanced because the corrected lineup made us a +29 favorite.

Result:

- Won 11-5.
- Primary story was control across sets.
- Noor Griffin posted 27K, Wren Mendoza 17K/7C, Imani Crosby 23K/2C.

Traceability verdict:

- Strong: fixing the lineup looked like the right managerial action and the win followed immediately.

### Week 4 vs Northwood Ironclads

Record after week: 2-1.

Decision:

- Stayed Balanced as a +13 favorite.
- I expected the developed core to win without taking extra tactical risk.

Result:

- Won 14-4.
- Catch disparity was 22-6.
- Wren Mendoza exploded for 42K; Noor Griffin added 11K/7C; Imani Crosby added 20K.

Traceability verdict:

- Strong: the grown core was visibly overpowering a weaker club.

### Week 5 vs Harbor Tidebreakers

Record after week: 3-1.

Decision:

- Stayed Balanced as a +25 favorite.
- Watched for whether Noor Perez would finally look integrated after the broken early-playing-time promise.

Result:

- Won 15-1.
- Catch disparity was 23-3.
- Wren Mendoza had 43K.
- The tactical read named Noor Perez in a momentum catch and Vale Kerrigan re-entering.

Traceability verdict:

- Strong: the roster I built was now steamrolling the same kind of clubs that crushed us in Season 1.
- Good moment: seeing Noor Perez named in the evidence finally made the Year 1 recruiting story feel present in matches.

### Week 6 vs Lunar Syndicate

Record after week: 3-2.

Decision:

- Stayed Balanced because we were a +12 favorite even against the two-time champion.
- I wanted the default title-contender identity to prove itself before making a playoff-specific adjustment.

Result:

- Lost 5-9.
- Debrief again said `Outclassed across the sets; fix is squad strength` despite the starter OVR advantage.
- Dex Beck and Ayo Slate looked like Lunar's real engine: Dex 36K/2C, Ayo 20K/1C.
- My immediate playoff lesson: if we see Lunar again, stop spreading pressure and target their stars.

Traceability verdict:

- Wrong: the squad-strength advice repeated the same false-feeling diagnosis from the Aurora loss.
- Stronger evidence came from named performers: the real actionable read was `Dex and Ayo beat us`.

### Week 7 vs Granite Specters

Record after week: 4-2.

Decision:

- Stayed Balanced as a +19 favorite.
- No need to reveal a Lunar-specific adjustment before the playoffs.

Result:

- Won 9-4.
- Catches were closer, 16-12, but Glassworks controlled enough games to close the regular season 4-2.
- Imani Crosby and Wren Mendoza each posted 23K/2C; Noor Griffin added 12K/2C.

Traceability verdict:

- Strong: the club is now consistently beating weaker teams.
- The real test remains whether I can use policy choices to solve the two clubs that eliminated or blocked us: Aurora and Lunar.

### Playoff Semifinal vs Aurora Sentinels

Decision:

- Aurora had beaten us twice in important spots, so I repeated the Season 2 playoff adjustment more aggressively.
- Changed Opening Rush to `All in` and rush target to `Center`, while keeping Mixed / Spread / Opportunistic.
- Reason: the prior Aurora loss profile was early control and Lux Stone dominance. I wanted bodies won immediately without turning the whole tactic reckless.

Result:

- Won 15-4.
- Primary factor: catch disparity, 30-10 for Glassworks.
- Imani Crosby dominated with 30K/10C.
- Noor Griffin had 19K/4C, Wren Mendoza 22K/7C.
- Tactical read named Noor Griffin catching Nola Aura and Cass West re-entering.

Traceability verdict:

- Strong: this was one of the clearest cause-and-effect moments of the playthrough. I responded to a repeated Aurora problem, changed a policy lever, and the result swung from elimination/danger to a blowout.
- Mixed: the debrief still emphasized catch disparity more than opening rush, so the exact mechanism is partly inferred from my plan and the outcome rather than explicitly narrated.

### Playoff Final vs Lunar Syndicate

Decision:

- Scouted Lunar before the final. The report showed 5/5 reads across 23 games: Aggressive, Their stars, Opportunistic, All in, Center.
- The Week 6 loss had made Dex Beck and Ayo Slate look like the real Lunar engine, so I changed target focus from Spread to `Their stars`.
- I also changed Opening Rush to `All in` and Rush Target to `Center`, because Lunar's own tape showed an all-in center rush and I did not want to concede the first exchange.
- Kept Mixed / Opportunistic, because Glassworks had won all year on catch creation without needing a fully reckless approach.
- Re-selected Tactical drills after noticing the final-week screen had reset development focus to Balanced.

Result:

- Won the championship in Season 3: Glassworks 13, Lunar Syndicate 12.
- Match was a 25-game knife fight. The page called it `A hard-fought 13-12 win`.
- Primary factor: catch disparity, 26-21 for Glassworks.
- The debrief showed the plan I chose: Mixed / Their stars.
- Wren Mendoza delivered the defining title performance: 29K, 11C, Impact 125.
- Ayo Slate still carried Lunar with 37K, which made the star-target decision feel like a real risk rather than an instant hard counter.
- Tactical read named Cass West catching Lin Kone and Wren Mendoza re-entering.
- The banner had a serious bug: it said `0-0 over Lunar Syndicate to take the title` even though the score panel directly below said 13-12.

Traceability verdict:

- Strong: this was the best decision loop in the playtest. I used prior loss evidence, scouted the opponent, changed a specific tactic, and the final debrief reflected that tactic and the catch swing.
- Strong: the final still felt competitive. Ayo Slate's 37K made Lunar scary even after I targeted stars.
- Wrong: the championship banner score bug damaged the payoff at the exact moment the game needed to be most trustworthy.

Screenshots:

- Earlier screenshots were saved outside the repo at `C:\Users\Maurice\AppData\Local\Temp\dodgeball-playtest-shots`.
- Captured moments include founding identity, coach setup, starting roster, season preview, early losses, full replay, recruiting actions, bye/development feedback, and a post-title offseason recap.
- I could not capture the live title debrief through the resumed screenshot bridge; the screenshot-capable browser reloaded the save into the post-title offseason recap instead. The live title text and score contradiction are recorded above.

## Final Report

### 1. The story

Cleveland Glassworks began as a nobody expansion club: emerald colors, Coach Nia Calder, and a backstory rooted in donated gym time and public-school athletics. I drafted a full 10-player roster built around Wren Mendoza, Vale Kerrigan, Imani Crosby, Noor Griffin, Cass West, and a lot of underpowered depth.

Season 1 was a wipeout: 0-6, no playoffs. The meaningful choice was not match tactics; it was accepting the losses while running Youth acceleration and recruiting aggressively. That made the season feel like foundation work instead of wasted time.

Season 2 was the arrival: 4-2, first win over Solstice, multiple catch-driven wins, and a playoff semifinal against Aurora. I lost that semifinal 9-9 on higher-seed tiebreaker, but the loss taught me Aurora could be attacked through opening-rush adjustments.

Season 3 was the title season: 4-2 regular season, semifinal revenge over Aurora 15-4, then a 13-12 championship win over two-time champion Lunar Syndicate. The turning point was using scouting plus prior-match evidence to target Lunar's stars and meet their all-in center rush. Wren Mendoza, the original expansion cornerstone, became the title MVP in practice: 29K and 11C in the final.

### 2. Did decisions matter?

Yes, but unevenly.

The real levers were development focus, lineup management, scouting, policy editor choices, and recruiting interest. Youth acceleration visibly transformed the roster. Auto-Assign fixed stale lineups and immediately changed results. The Aurora and Lunar playoff tactics felt deliberate and supported by evidence. Full replay and debriefs often named the players involved, which helped connect choices to outcomes.

The weak levers were weekly intent, staff presentation, promise management, and the advice layer. Weekly intent sometimes felt like a broad mood selector more than a proven tactical call. Staff names and ratings were present, but I rarely felt like I was making staff decisions. Promises were actively untrustworthy. The recommendation system repeatedly gave stale or false advice, especially around recruiting and favored losses.

### 3. Findings list, ordered by severity

1. Issue 22 - Championship banner says 0-0 after a 13-12 title win. Repro: win Season 3 final vs Lunar, read the champion banner above the score panel.
2. Issue 15 - Noor Perez early-playing-time promise broke before a fair chance to satisfy it. Repro: sign Noor, reach Season 2 after one played match, check promise record.
3. Issue 13 - Promised River Dubois vanished during Signing Day after first signing. Repro: close River to 100%, promise development priority, sign Noor first, River disappears.
4. Issue 16 - Command Center and Standings disagree on playoff rank. Repro: Season 2 Week 7 before finale, compare Command Center rank text to Standings.
5. Issue 17 - Playoff semifinal copy says it is the final. Repro: Season 2 or Season 3 semifinal screen, read `Win it and the banner is yours`.
6. Issue 19 - Favored losses get false squad-strength advice. Repro: lose as +20 vs Aurora or +12 vs Lunar in Season 3, read debrief.
7. Issue 10 - Recruiting action buttons can click without spending or changing state. Repro: use Contact/Visit late Season 1 and audit counters after each click.
8. Issues 7 and 21 - Development focus can reset unexpectedly. Repro: change Weekly Intent after selecting focus, or bank semifinal into final week.
9. Issue 20 - Auto-reorder checkbox does not keep lineup current after offseason growth. Repro: enter Season 3 with checkbox on, compare bench/starter OVRs, then press Auto-Assign.
10. Issue 18 - Semifinal tiebreaker is hard to trust after rank drift. Repro: draw Aurora 9-9 in Season 2 semifinal after conflicting rank screens.
11. Issue 12 - Final standings show Elim +/- as zero for every club. Repro: any offseason recap table observed in Seasons 1 or 3.
12. Issues 6 and 11 - Postgame recruiting advice goes stale and can say a 100% recruit has only 100% interest. Repro: warm Noor/River, return to debrief advice.
13. Issue 14 - Signing slots and roster cap conflict without enough warning. Repro: enter Signing Day with 3 slots and only 2 roster spots.
14. Issue 9 - Bye week has conflicting week numbers. Repro: Season 1 bye after Week 4.
15. Issue 5 - Dynasty Office week labels disagree with banner week. Repro: open office after Week 2 debrief.
16. Issue 3 - Scouting copy says reads are revealed and also `No tape yet`; labels run together. Repro: scout Lunar in Week 1.
17. Issue 4 - Full replay score strip reads like it contradicts the final score. Repro: open Week 1 full replay and jump between game moments.
18. Issue 1 - Launch token instructions did not match live behavior. Repro: launch server; no token printed, bare localhost accepted.
19. Issue 2 - Season preview labels require too much inference. Repro: read initial roster-strength/watch-area labels after founding.
20. Issue 8 - Recruiting recommendation says `only 96% interest`. Repro: raise Noor Perez to 96%, read debrief recommendation.

### 4. Top 5 fixes and 3 alive moments

Top 5 fixes before showing this to a paying player:

1. Fix championship and playoff state truth: banner scores, semifinal/final copy, rank/seeding, and tiebreak proof must be airtight.
2. Rework promises so they cannot fail before the player has a fair chance, and warn before Signing Day can make a promise impossible.
3. Make postgame advice state-aware. It must not recommend already-completed recruiting actions or tell a favored roster that the only fix is squad strength.
4. Make all action buttons transactional: if a recruiting click is accepted, counters and state must change; if not, explain why.
5. Fix persistence of lineup and development choices, or loudly communicate when a new week requires re-confirmation.

The 3 moments that made the game feel alive:

1. First win in Season 2: Vale Kerrigan and Wren Mendoza turned catch disparity into a 12-2 breakthrough, and full replay backed it with named re-entry events.
2. Season 1 offseason growth: Youth acceleration turning an 0-6 roster into a real contender made the dynasty loop click.
3. Season 3 final: targeting Lunar's stars, seeing Ayo Slate still post 37K, and watching Wren Mendoza answer with 29K/11C made the championship feel earned.

### 5. Verdict

I would play one defending-champion season out of curiosity. I would not start Season 11 in the current build as a normal player.

The core loop has something real: scouting, development, catch evidence, and rivalry context can produce a strong sports-management story. But long-run dynasty play depends on trust, and the current build breaks trust too often at high-leverage moments: promises, playoff state, standings, advice, and the championship banner itself. The game is compelling enough to test further, but not yet reliable enough to ask a paying player for eight more seasons.
