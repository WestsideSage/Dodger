# PLAYTEST_JOURNAL_2

Hard-mode browser-only playtest of Dodgeball Manager: "The Orphanage Run."

## Setup Notes

- Repo: `C:\GPT5-Projects\Dodgeball Simulator`
- Date: 2026-06-11
- Install command completed: `python -m pip install -e ".[dev]"`
- Repo status before play: `main...origin/main`, clean.
- Port 8000 already had `python -m dodgeball_sim` listening before I started the browser. I used that running app rather than touching existing saves or killing an unknown process.
- Pare MCP was not available in the exposed tool list; I used normal local commands for setup/status.
- Frontend was treated as pre-built; I did not run npm.
- Conduct boundary: UI only. No source, docs, tests, or save-file inspection.

## Run Rules I Am Enforcing

- New Game -> Build from Scratch only.
- Draft the lowest-rated roster the creator allows.
- No veteran free agents.
- Sign at least one prospect every offseason when class slot and roster space allow.
- Keep promises open aggressively up to the cap, and never intentionally break one.
- Exercise all staff focuses at least twice, all development focuses for at least one season stretch, playoff policy adjustment, manual lineup, auto-assign, auto-reorder, scouting every playable week, and two fast-forward audits.
- Minimum length: 8 full seasons.

## Season 1 - Founding Draft

Expectation: Taking the six lowest-rated players should create the weakest plausible roster. I selected only six because the creator permits 6-10 and extra players would raise the floor.

Selected founding roster:

- Luca Hawthorne, 40 OVR, Possession Specialist, Catcher / Survivor.
- Luca Slate, 42 OVR, Two-Way Threat, Thrower / Catcher.
- Ash Kline, 43 OVR, Hit-and-Run, Survivor.
- Rin Garcia, 44 OVR, Net Specialist, Catcher.
- Remy Ramirez, 45 OVR, Skirmisher, Thrower / Survivor.
- Avery Ash, 45 OVR, Hit-and-Run, Survivor.

Immediate note: the setup copy says the roster card OVR and archetype will match the committed roster. I will verify that after creation.

## Season 1 - Preview

The new save opened to Season 1, Week 1. Season Preview claims:

- Regular season is 7 weeks.
- My bye is Week 5.
- Playoff cut is top 4 of 7.
- Roster strength: Skirmisher group, 45 avg OVR.
- Watch area: Possession Specialist group, 40 avg OVR.

Expectation: I should be noncompetitive early, and the game should make development/recruiting the believable escape route rather than handing me surprise parity.

## Season 1 - Initial Roster Verification

Roster tab verified the draft values carried through:

- Remy Ramirez: age 20, Skirmisher, 45 OVR, Low, Ceil 70.
- Avery Ash: age 18, Hit-and-Run, 45 OVR, Low, Ceil 70.
- Rin Garcia: age 20, Net Specialist, 44 OVR, Low, Ceil 70.
- Ash Kline: age 21, Hit-and-Run, 43 OVR, Low, Ceil 70.
- Luca Slate: age 20, Two-Way Threat, 42 OVR, Mid, Ceil 72.
- Luca Hawthorne: age 19, Possession Specialist, 40 OVR, Low, Ceil 70.

Roster state: 6 contracted, all 6 starters, no bench. Team lineup OVR 43. Potential mix: 0 Elite, 0 High, 1 Mid, 5 Low. This is a clean baseline for starter-vs-bench development later because every founder is currently a full-time starter.

## Season 1 - Week 1 Plan

Opponent: Lunar Syndicate. Command Center says I am an underdog by `-143 net starter OVR`; opponent key threat Yuki Rodriguez is a 71 OVR Sharpshooter. Scout report says their primary threat outrates Remy Ramirez by +26 OVR.

Expectation: I should lose or need a very clear tactical upset path. If I win, replay/debrief must explain it with catches, wipe-outs, or opponent mistakes rather than vague momentum.

Planned actions: scout opponent, inspect Dynasty Office for any weekly scouting/promise levers, confirm the six-player lineup, and follow the Counter Read if the UI lets me do so without spending impossible actions.

Dynasty Office Week 1 claims:

- Program credibility starts Tier D / Regional, 50 / 100.
- Credibility factors explicitly include wins/losses, youth development weeks, club prestige, and match history.
- Weekly recruiting: 3 scout slots, 5 contact slots, 1 visit slot.
- Promises: 0/3 open, checked at season end, kept promises build credibility and broken ones cost more.
- Scout narrows OVR range; Contact and visits build interest.
- Training staff button advertises `+6% dev`.
- Prospect board includes three Pipeline Tier 5 (Elite) prospects but their fit is only Fair/At Risk; this is "Elite pipeline tier," not necessarily Elite potential.
- Staff tab lists six departments: Conditioning, Culture, Medical, Scouting, Tactics, Training. Training's expanded claim is `+6% offseason growth`.
- Program Settings exposes five weekly Staff Focus options:
  - Tactics: next match throwers get +18 effective Tactical IQ on target reads, release timing, and catch-beating timing.
  - Conditioning: next match stamina drag on every action stat is halved.
- Training: each training week adds +0.2 OVR offseason growth for the whole squad, cap 8 weeks.
  - Scouting: one extra Scout action this week, 3 -> 4.
  - Culture: Contact and Visit interest gains are 25% stronger this week.

Staff focus rotation plan: Training W1, Scouting W2, Culture W3, Conditioning W4, Tactics W6, then repeat so every option is used at least twice by the end of Season 2. I selected Training in W1.

Additional Training tooltip after selecting it: "affects play"; banks toward offseason; each training week adds +0.2 OVR of offseason growth for the whole squad, cap 8 weeks per season, headroom-capped per player.

Promises opened W1:

- Noor Perez: Early playing time. Condition shown: "They appear in at least 6 matches this season."
- River Dubois: Early playing time. Condition shown: "They appear in at least 6 matches this season."
- Callum Saito: Early playing time. Condition shown: "They appear in at least 6 matches this season."

Concern logged now: these promises can be made before the players are signed. If the season-end grading checks the current season before prospects can join or appear, that would be unfair. If it only grades after signing or future availability, that needs to be visible.

Recruiting actions W1:

- Scout River Dubois: OVR narrowed from 34-84 estimated to 44-74 known.
- Scout Mara Hassan: OVR narrowed from 31-81 estimated to 41-71 known.
- Scout Niko Hansen: OVR narrowed from 13-63 estimated to 23-53 known.
- Contact Noor Perez: interest moved 52% -> 64%.
- Visit Noor Perez: interest moved 64% -> 84%.
- Contact Callum Saito: interest moved 52% -> 64%.
- Contact Mara Hassan: interest moved 38% -> 50%.
- Contact Mara Parr: interest moved 42% -> 54%.
- I attempted Contact River Dubois in the same action sequence, but the visible board still showed River as Scouted with 38% interest and one Contact slot remaining. I will spend that visible remaining slot on River and log this as an action-order/feedback wrinkle if it repeats.
- Follow-up: spending the visible remaining contact on River changed him to Contacted and interest 38% -> 50%. Weekly recruiting then showed 0/3 Scout, 0/5 Contact, 0/1 Visit remaining.

Lineup Editor W1:

- Slot order tooltip claims this affects play.
- Role fit: starters whose archetype fits seats 1-4 get +3 on every action stat; mismatch only forgoes the bonus.
- Opening rush: first slots secure designated balls when Rush Target is Nearest; other targets re-order by power/overall.
- Auto-reorder each offseason is ON by default.
- Current fielded six: Remy captain, Avery striker, Ash anchor, Rin runner, Luca Slate rookie, Luca Hawthorne utility.
- No bench exists, so true manual starter/bench swap is impossible yet. I used Auto-Assign now and will perform a real manual swap after the first prospect class creates a bench.

Command Center W1 final plan before lock:

- Development focus set to Youth acceleration. This is the Season 1 full-season development stretch unless the UI forces a change.
- Weekly intent set to Defensive, following the Counter Read. This changed the read from "Adjust to Defensive" to "Keep current plan" and dropped risk to Low.
- Visible tactical plan changed from Mixed to Patient after selecting Defensive.
- Opponent scout revealed 5/5 tactical reads. Copy says these are identity-playbook reads, not hidden plans, because there is no match tape yet.
- Scouted opponent tendency rows: their Approach Aggressive, Target Focus Their stars, Catch Posture Opportunistic, Opening Rush All in, Rush Target Center.

## Season 1 - Week 1 Result

Result: Lunar Syndicate 15, Cinderfield Orphans 0. This matched expectation for a -143 net starter OVR underdog.

Debrief:

- Headline: "Luca Slate is alone against 6."
- Primary Factor: Catch disparity, high confidence.
- Numeric claim: opponent had 18 catches to my 0, a +18 catch swing.
- Tactical read cites a momentum-shifting catch by Yuki Rodriguez robbing Remy Ramirez, with Nola Diallo re-entering.
- Key performers: Sasha Fern 35K/4C/185 impact, Ayo Slate 13K/59 impact, Yuki Rodriguez 7K/4C/56 impact.
- Training Impact: Youth acceleration boosts offseason growth for players 22 and under and slows it for older players. It also says offseason growth follows the dev focus in effect at season's end, currently Youth acceleration.
- Prospect Pulse says no prospect movement this week, even though I spent recruiting actions. This may mean no signings/macro board movement, but the wording underplays visible interest gains.
- Next best improvement says to shore up Possession Specialist depth and warm up River Dubois, matching the weak-group and recruiting state.

Expectation before replay: event stream should show repeated catches by Lunar, especially Yuki catching Remy, and the score should agree with the 15-0 debrief and later standings.

Replay audit:

- Replay header matches: Lunar 15, Cinderfield 0.
- Official state shows full time, Foam Division, No Blocking final mode, game/match clock 00:00.
- Game plans match locked plan after the fact: Lunar Aggressive / Opportunistic / targets their stars; Cinderfield Patient / Play safe / targets spread.
- Biggest Swing is the same Yuki catch cited in debrief.
- Event 13 exactly matches: Remy Ramirez vs Yuki Rodriguez catch, Remy out, Nola Diallo re-enters, USA Dodgeball rule 22.
- Visible event-log count: 250 events, 18 CATCH, 96 HIT, 114 MISS, 22 BLOCKED. This supports the debrief's 18-catch number.
- The replay is dense but trustworthy here; it made the blowout feel earned rather than arbitrary.

Standings audit after W1:

- My row: rank 7, 0-1-0, 0 PTS, Defensive plan, -15 GP diff.
- Lunar row: rank 1, 1-0-0, 3 PTS, +15 GP diff.
- Recent results: "Week 1: Lunar Syndicate 15-0 Cinderfield Orphans" marked as my match.
- This agrees with debrief and replay on score and record.
- Contradiction: the playoff race panel says I am "0 BACK OF CUT" and "0 points outside the playoff line," but the #4 team has 1 point and I have 0. The standings table itself is clearer than the summary.

## Season 1 - Week 2 Plan

Opponent: Aurora Sentinels, #6, 0-0, key threat Ayo Smirnov 67 OVR Net Specialist. Cinderfield is still a -133 net starter OVR underdog. Development focus persisted as Youth acceleration; intent persisted as Defensive and the Counter Read still says Keep current plan.

Staff Focus: Scouting. Claim verified immediately: scout slots changed to 4 / 4, contact stayed 5 / 5, visit stayed 1 / 1.

Recruiting W2:

- Scouted Noor, River, Callum, Mara Hassan. These consumed 4 scout slots, but their displayed ranges did not visibly narrow, which supports S1-TRUST-004.
- Contact attempts on already-contacted/visited targets were inconsistent; visible contact slots remained. I redirected the remaining contacts to Sloane Park, Rin Zane, Niko Hansen, and Mara Hassan.
- Final visible board after W2 contacts: Noor 84%, River 70%, Callum 64%, Mara Hassan 62%, Mara Parr 66%, Sloane 49%, Rin Zane 64%, Niko 54%.
- Visit River Dubois: River increased from 50% to 70%.

Expectation: another loss, but the debrief should mention whether Defensive/Play Safe is at least limiting damage compared with W1.

## Season 1 - Week 2 Result

Result: Aurora Sentinels 13, Cinderfield Orphans 0. Still credible given the -133 net starter OVR gap.

Debrief:

- Headline: "Luca Hawthorne is alone against 6."
- Primary Factor: Catch disparity, high confidence.
- Numeric claim: opponent had 28 catches to my 0, a +28 catch swing.
- Tactical read cites Lux Stone catching Luca Hawthorne, Lena Forge re-entering.
- Key performers: Ayo Smirnov 26K/3C/135 impact, Lux Stone 3K/10C/65 impact, Cass Chavez 11K/47 impact.
- Problem: Training Impact says "Balanced development" was this week's development focus and that offseason growth currently follows Balanced development. This contradicts the W2 command screen before recruiting, where Youth acceleration was selected and meant to persist for Season 1.

Impact: This is the first direct Claims Ledger trust break. Development focus is one of the core systems under test; if the selected focus silently falls back to Balanced, every later growth claim is suspect.

Replay audit: W2 replay event count showed 250 events with 28 CATCH, 74 HIT, 119 MISS, 29 BLOCKED. That supports the 28-catch debrief claim. The result story is consistent; the development-focus state is not.

Standings audit after W2:

- My row: 0-2-0, 0 PTS, Defensive, -28 GP diff. This matches the two losses: -15 and -13.
- Playoff summary now says "1 BACK OF CUT" and "1 point outside the playoff line," but #4 Granite has 3 PTS and Cinderfield has 0. S1-TRUST-003 persists and is not just a W1 edge.

## Season 1 - Week 3 Result

Staff Focus selected: Culture. Note: I intended to spend recruiting actions here, but after closing Program Settings the front-office subtab was not on Recruit, so no recruit slots were actually spent before I returned to the match loop. I still scouted the opponent and played the week. I am correcting the play routine to explicitly open the Recruit subtab before spending actions.

Result: Granite Specters 14, Cinderfield Orphans 0.

- Primary Factor: Catch disparity, 18 catches to 0.
- Key debrief point: "Luca Slate is alone against 3."
- Development focus check: Because I explicitly set Youth acceleration immediately before lock, W3 debrief correctly reported Youth acceleration and "currently Youth acceleration."

Interpretation: W3 narrows S1-TRUST-005. Youth acceleration can work if set immediately before lock; W2 likely failed because the selected dev focus did not persist through navigation or was not actually saved from the earlier Command Center state.

## Season 1 - Week 4 Result

Staff Focus selected: Conditioning. The visible claim was that stamina drag should bite half as hard next match. I did not see an explicit Conditioning callout in the debrief, so this is not yet verified beyond selection.

Recruiting note: my UI helper still failed to spend recruit slots because its slot parser was too case-sensitive. This is a playtest-process miss, not a game bug. Fixed before the next week.

Result: Northwood Ironclads 13, Cinderfield Orphans 0.

- Primary Factor: Catch disparity, 23 catches to 0.
- Key debrief point: "Rin Garcia is alone against 6."
- Youth acceleration was correctly reported again because I explicitly set it before lock.
- "Your club's best" was Avery Ash with 9K and 1 impact, which is the first small player-specific bright spot in a loss.

## Season 1 - Week 5 Bye

The page presented the scheduled bye as "Week 05 Bye Week" in context but "Season 1 -- Week 06" in the banner, logged as S1-TRUST-006.

Staff Focus selected: Culture.

Recruiting under Culture:

- Before: Noor 84, River 70, Callum 64, Mara Hassan 62, Mara Parr 66, Sloane 49, Rin 64, Niko 54.
- Actions: Scout Mara Parr, Sloane Park, Noor Perez; Contact Callum, Mara Hassan, Sloane, Rin, Niko; Visit Callum.
- Scout claims kept for ranges: Mara Parr narrowed 18-68 -> 28-58; Sloane narrowed 17-67 -> 27-57.
- Contact gains looked normal, not Culture-boosted: Mara Hassan 62 -> 74 (+12), Rin 64 -> 76 (+12), Niko 54 -> 66 (+12). Sloane moved 49 -> 61 (+12) after I spent the remaining contact separately.
- Visit Callum plus contact moved Callum 64 -> 96 (+32), which matches normal +12 contact and +20 visit, not a 25% boosted +15/+25 pattern.

Interpretation: Culture focus did not visibly apply its "Contact and Visit interest gains are 25% stronger" claim on the bye week. If Culture is match-week only, the UI should say so; if it should apply to bye recruiting, the claim broke.

Bye result:

- Rest Report says no match scheduled and no match minutes logged.
- Training Impact correctly says Youth acceleration held through the bye.
- Prospect Pulse again says no prospect movement despite visible interest/range changes from the same week.

## Season 1 - Week 6 Plan

Staff Focus selected: Tactics. This should test the +18 effective Tactical IQ claim.

Recruiting bug discovered before match work: the Week 6 recruit board still showed 0 scout, 0 contact, 0 visit remaining immediately after the bye-week budget was exhausted. It did not reset at the start of Week 6. This is a serious pipeline break because the required weekly recruiting loop becomes unavailable after a bye.

Result: Solstice Flare 14, Cinderfield Orphans 0.

- Primary Factor: Catch disparity, 16 catches to 0.
- Key debrief point: "Avery Ash is alone against 5."
- Your club's best: Remy Ramirez, 12K, 6 impact.
- Youth acceleration correctly reported again.
- Tactics focus did not receive an explicit debrief callout, so the +18 Tactical IQ claim is still unverified from the player-facing evidence.

## Season 1 - Week 7 Result

Staff Focus selected: Training, second Training week.

Recruiting before match:

- Slots reset normally after W6, confirming S1-TRUST-008 is bye-specific.
- Final target interest before endgame: Noor 84%, River 90%, Callum 96%, Mara Hassan 86%, Mara Parr 78%, Sloane 73%, Rin 88%, Niko 78%.
- Remaining contact no-ops on already-visited targets continued; I redirected to lower-contact targets to spend the budget.
- Credibility panel showed 43/100 and 4 weeks prioritizing youth development after W6, which matches W2 failing to count as Youth and the bye not adding a match week.

Result: Harbor Tidebreakers 15, Cinderfield Orphans 0.

- Primary Factor: Catch disparity, 22 catches to 0.
- Key debrief point: "Rin Garcia vs Dray Keene - last two standing."
- Youth acceleration correctly reported at season end. This is crucial because offseason growth claims should now be based on Youth acceleration, not Balanced.

Season 1 regular-season record: 0-6 across six played matches plus one bye. Total visible GP differential from match results: -84 (0-15, 0-13, 0-14, 0-13, bye, 0-14, 0-15).

## Season 1 - Offseason Beat 1/8

Final regular-season table:

- Cinderfield finished 7th of 7, 0-6-0, 0 pts, -84 GP diff. This exactly matches tracked match results.
- Playoff cut: top 4.
- Seeding question: Northwood and Solstice both finished 2-2-2 with 8 pts, but Northwood took #4 at +5 GP diff while Solstice was #5 at +8. The screen did not explain the tiebreaker. This may be head-to-head, but the player-facing evidence is missing.

## Season 1 - Offseason Beat 2/8

Champion: Lunar Syndicate. Bracket: Harbor 7-7 Northwood, higher seed Harbor advanced; Lunar beat Granite 12-4; Lunar beat Harbor 11-10 in the final.

Positive note: the playoff bracket explicitly explained the 7-7 semifinal tiebreaker. That is the kind of explanation missing from the regular-season #4/#5 cut.

## Season 1 - Offseason Beat 3/8

Awards:

- MVP: Dray Slate, Harbor Tidebreakers, 171 throw eliminations, 21 catches, 107 times out, 68 OVR, 192 career eliminations.
- Best Thrower: Lex Mendoza, Granite Specters, 170 throw eliminations.
- Best Catcher: Cruz Ibarra, Harbor Tidebreakers, 38 catches.
- Best Newcomer: Dex Voss, Solstice Flare, 68 season eliminations.

No Cinderfield awards, which matches the season.

## Season 1 - Offseason Beat 4/8

Records Ratified:

- My Club: 0 records.
- League: 5 records.
- Cruz Ibarra now leads career catches with 38.
- Dray Slate now leads career eliminations with 171.
- Harbor Tidebreakers longest unbeaten run: 6.
- Yuki Rodriguez most player championships: 1.
- Lunar Syndicate most titles: 1.

Minor copy note: "Most Championships" for Yuki Rodriguez appears to be an individual/player-championship record; label could be clearer.

## Season 1 - Offseason Beat 5/8

Development:

- 6 players changed OVR.
- Luca Hawthorne: Ceiling 70, 40 -> 60 (+20). ACC +19, POW +22, DOD +19, CAT +18, STA +21, IQ +11, CC +13, TIQ +13, CON +9.
- Luca Slate: Ceiling 72, 42 -> 62 (+20). ACC +19, POW +19, DOD +19, CAT +24, STA +18, IQ +11, CC +12, TIQ +11, CON +3.
- Ash Kline: Ceiling 70, 43 -> 61 (+18). ACC +17, POW +20, DOD +14, CAT +19, STA +18, IQ +9, CC +9, TIQ +9, CON +7.
- Rin Garcia: Ceiling 70, 44 -> 61 (+17). ACC +21, POW +14, DOD +13, CAT +21, STA +17, IQ +9, CC +10, TIQ +9, CON +8.
- Avery Ash: Ceiling 70, 45 -> 62 (+17). ACC +20, POW +18, DOD +15, CAT +16, STA +16, IQ +7, CC +9, TIQ +11, CON +11.
- Remy Ramirez: Ceiling 70, 45 -> 61 (+16). ACC +18, POW +14, DOD +14, CAT +19, STA +18, IQ +12, CC +5, TIQ +5, CON +6.
- League transition checklist: all active players aged by 1 year; match fatigue fully reset; offseason development and skill regression applied.

Claims Ledger read:

- Full-time starters did develop dramatically: +16 to +20 OVR after one season.
- None reached ceiling yet. They are now 8-10 OVR below displayed ceilings.
- Luca Slate, the only Mid-tier founder, is tied for highest OVR at 62 but did not clearly separate from Low-tier Avery Ash at 62 or Luca Hawthorne at 60.
- Youth acceleration appears directionally strong for a roster entirely aged 18-21, but W2's focus-state failure means the exact season input is already contaminated.

## Season 1 - Offseason Beat 6/8

Rookie Class Preview:

- 0 top prospects by the screen's definition.
- No rookies project at 70+ OVR this year.
- 0% high-confidence.
- 12 incoming rookies.
- 12 veteran free agents also available.

Run rule: ignore veteran free agents completely.

## Season 1 - Offseason Beat 7/8 - Signing Day

Signing Day setup:

- Add up to 3 players before next season; 3 signings remain.
- Roster size starts 6 / 12.
- Screen explains prospect ranges are scouted and verified OVR is revealed only when signed.
- Rival clubs can sign between my picks, so promised players should be signed first.
- Free agents have public verified ratings and sign uncontested, but the run forbids signing them.

Signing priority: Noor Perez, River Dubois, Callum Saito because all three have promises at stake.

Signing 1:

- Noor Perez signed.
- Contested Round Won: offer 94 beat Lunar Syndicate's 83; interest 84% strengthened it.
- Scouted 46-76 -> verified OVR 57.
- Roster size 7 / 12, 2 signings remain.
- Problem: River Dubois, a promised 90%-interest target, disappeared from the board after the first signing with no visible "signed elsewhere" explanation in the current view.

Signing 2:

- Callum Saito signed.
- Contested Round Won: offer 96 beat Lunar Syndicate's 76; interest 96% strengthened it.
- Scouted 41-71 -> verified OVR 60.
- Roster size 8 / 12, 1 signing remains.
- Mara Hassan also disappeared between picks without an explicit current-view explanation.

Signing 3 target: Ash Ibarra, prospect, Net Specialist, Age 19, estimated OVR 30-80, Interest 51%. Chosen because the promised River target and higher-warmed Mara target were gone, and free agents are forbidden.

Signing 3:

- Ash Ibarra signed.
- Estimated 30-80 -> verified OVR 50.
- Class Report says Ash signed despite no prior contact.

Class Report:

- You signed 3.
- 18 others joined the league.
- 3/3 slots used.
- Top signing: Callum Saito, OVR 60.
- You scouted 7 prospects.
- Your picks: Callum Saito 60, Noor Perez 57, Ash Ibarra 50.
- No veteran free agents signed.

Promise status still unresolved: Noor and Callum signed, River was promised but disappeared between picks.

## Season 1 - Offseason Beat 8/8

Schedule Reveal for Season 2027:

- 6 matches shown.
- First listed match is Week 2: Solstice Flare vs Cinderfield Orphans, implying Week 1 is a bye.
- Other listed opponents: Northwood, Lunar, Harbor, Aurora, Granite.
- No promise grading appeared during the offseason beats. This may be fair for signed prospects if the promise applies to their first rostered season, but River Dubois disappearing with an open promise remains unexplained.

## Season 2 - Opening Roster

Roster after starting Season 2:

- 9 contracted.
- Lineup OVR 59.
- 6 starters, 2 rotation, 1 bench.
- Potential mix: 0 Elite, 0 High, 3 Mid, 6 Low.
- Age average 20, range 19-22.
- New prospect claims:
  - Callum Saito: age 19, Two-Way Threat, 60 OVR, Mid, Ceil 74.
  - Noor Perez: age 21, Skirmisher, 57 OVR, Mid, Ceil 75.
  - Ash Ibarra: age 19, Net Specialist, 50 OVR, Low, Ceil 68.

Concern: auto-reorder left Callum and Noor outside the starting six despite playing-time promises. I will manually field them before the first match to avoid breaking promises through my own choice.

Prospect board snapshot before actions:

- Noor Perez: Skirmisher, Contacted, Pipeline Tier 5 (Elite), Fit 67, Interest 52%, OVR 46-76 known.
- River Dubois: Possession Specialist, Unscouted, Pipeline Tier 2 (Silver), Fit 65, Interest 38%, OVR 34-84 estimated.
- Callum Saito: Two-Way Threat, Contacted, Pipeline Tier 5 (Elite), Fit 62, Interest 52%, OVR 41-71 known.
- Mara Hassan: Ball Hawk, Unscouted, Pipeline Tier 1 (Bronze), Fit 62, Interest 38%, OVR 31-81 estimated.
- Mara Parr: Skirmisher, Unscouted, Pipeline Tier 3 (Gold), Fit 49, Interest 42%, OVR 18-68 estimated.
- Sloane Park: Two-Way Threat, Unscouted, Pipeline Tier 2 (Silver), Fit 48, Interest 38%, OVR 17-67 estimated.
- Rin Zane: Two-Way Threat, Contacted, Pipeline Tier 5 (Elite), Fit 45, Interest 52%, OVR 24-54 known.
- Niko Hansen: Iron Anchor, Unscouted, Pipeline Tier 3 (Gold), Fit 44, Interest 42%, OVR 13-63 estimated.

## Development Claims Ledger

| Season | Week/Phase | Player/Surface | Claim | Follow-up Evidence | Verdict |
| --- | --- | --- | --- | --- | --- |
| Setup | Rules screen | Game rules card | Official-style foam rules: catches flip games, wipe-outs score, shot-clock pressure, 24-minute match window, draws are real. | To cross-check in replay, recap, box score, and standings. | Open |
| Setup | Coach screen | Tactical Mastermind archetype | Claims boosts to tactical preparation, key-matchup reads, and in-match adjustments. | Selected because it does not directly boost development or recruiting; to cross-check whether tactic information feels meaningfully stronger. | Open |
| Setup | Roster draft | Draft screen copy | Prospect OVR/archetype values shown here are "the same values their roster row will show after you commit." | To compare with the first roster screen. | Open |
| S1 | Season Preview | Roster strength/watch area cards | Team is a 45 avg OVR Skirmisher-strength group with 40 avg OVR Possession Specialist weak area. | To compare with Roster tab and early results. | Open |
| S1 | Roster | Remy Ramirez | Low tier, Ceil 70, starting at 45 OVR as full-time starter. | Track annual OVR and whether he approaches/reaches 70. | Open |
| S1 | Roster | Avery Ash | Low tier, Ceil 70, starting at 45 OVR as full-time starter. | Track annual OVR and whether he approaches/reaches 70. | Open |
| S1 | Roster | Rin Garcia | Low tier, Ceil 70, starting at 44 OVR as full-time starter. | Track annual OVR and whether he approaches/reaches 70. | Open |
| S1 | Roster | Ash Kline | Low tier, Ceil 70, starting at 43 OVR as full-time starter. | Track annual OVR and whether he approaches/reaches 70. | Open |
| S1 | Roster | Luca Slate | Mid tier, Ceil 72, starting at 42 OVR as full-time starter. | Track annual OVR and whether Mid tier separates from Low tier. | Open |
| S1 | Roster | Luca Hawthorne | Low tier, Ceil 70, starting at 40 OVR as full-time starter. | Track annual OVR and whether he approaches/reaches 70. | Open |
| S1 W1 | Command Center | Opponent file / matchup card | Orphans are `-143 net starter OVR`; Yuki Rodriguez is 71 OVR and +26 over Remy Ramirez. | Cross-check whether result/debrief respects this huge gap. | Open |
| S1 W1 | Dynasty Office | Program credibility | Tier D, 50/100; rises with wins, youth development, club prestige, and match history. | Track credibility after youth-focus weeks and wins/losses. | Open |
| S1 W1 | Dynasty Office | Recruiting actions | Each week provides 3 scout, 5 contact, 1 visit; scout narrows OVR, contact/visit build interest. | Count slots before/after actions; compare interest/range changes. | Open |
| S1 W1 | Dynasty Office | Promises panel | Promises are checked at season end; kept promises build credibility, broken promises cost more. | Make promises up to cap and audit grading fairness. | Open |
| S1 W1 | Staff Room | Training staff focus | Button advertises `+6% dev`. | Compare offseason growth after Training focus season vs non-Training season. | Open |
| S1 W1 | Staff tab | Training department | Training role advertises `+6% offseason growth` and "development focus advice and offseason player-growth impact." | Compare offseason growth when Training is emphasized vs not. | Open |
| S1 W1 | Staff Focus | Tactics | Next match throwers get +18 effective Tactical IQ on target reads, release timing, and catch-beating timing. | Use at least twice; compare match/debrief legibility. | Open |
| S1 W1 | Staff Focus | Conditioning | Next match stamina drag on every action stat is halved. | Use at least twice; watch fatigue/health copy and late-match outcomes. | Open |
| S1 W1 | Staff Focus | Training | Each training week adds +0.2 OVR offseason growth for whole squad, cap 8 weeks; tooltip adds headroom-capped per player and "affects play." | Selected W1; count training weeks and compare offseason growth claim. | Open |
| S1 W1 | Staff Focus | Scouting | One extra Scout action this week, 3 -> 4. | Use at least twice; count scout slots before/after. | Open |
| S1 W1 | Staff Focus | Culture | Contact and Visit interest gains are 25% stronger this week. | Use at least twice; compare interest movement after contact/visit. | Open |
| S1 W1 | Promise | Noor Perez | Early playing time: appears in at least 6 matches this season. | Promise made before signing; track whether grading waits for eligibility/signing. | Open |
| S1 W1 | Promise | River Dubois | Early playing time: appears in at least 6 matches this season. | Promise made before signing; track whether grading waits for eligibility/signing. | Open |
| S1 W1 | Promise | Callum Saito | Early playing time: appears in at least 6 matches this season. | Promise made before signing; track whether grading waits for eligibility/signing. | Open |
| S1 W1 | Lineup Editor | Slot order tooltip | Slot order affects play; archetype fit in slots 1-4 grants +3 every action stat; opening rush depends on order. | Use auto-assign now; later compare lineup/replay/debrief after manual swaps. | Open |
| S1 | Development Focus | Youth acceleration | Development focus is a player development direction and credibility factor includes weeks spent prioritizing youth development. | Keep through Season 1; audit offseason growth and credibility. | Open |
| S1 W1 | Debrief | Youth acceleration Training Impact | Youth acceleration boosts offseason growth for players 22 and under and slows it for older players; offseason growth follows dev focus in effect at season's end. | All founders are 18-21, so S1 offseason should show youth-friendly growth if focus stays. | Open |
| S1 W1 | Debrief | Primary Factor | Lunar won 15-0 largely through 18 catches to Cinderfield's 0. | Replay event log counted 18 CATCH events and event 13 matched the highlighted Yuki catch. | Kept |
| S1 W2 | Debrief | Primary Factor | Aurora won 13-0 largely through 28 catches to Cinderfield's 0. | Replay event log counted 28 CATCH events. | Kept |
| S1 Offseason | Development | Luca Hawthorne | Low tier, Ceil 70, full-time starter from 40 OVR. | Grew 40 -> 60 (+20), still 10 below ceiling. | Partly kept |
| S1 Offseason | Development | Luca Slate | Mid tier, Ceil 72, full-time starter from 42 OVR. | Grew 42 -> 62 (+20), still 10 below ceiling; not clearly separated from Low tier yet. | Partly kept |
| S1 Offseason | Development | Ash Kline | Low tier, Ceil 70, full-time starter from 43 OVR. | Grew 43 -> 61 (+18), still 9 below ceiling. | Partly kept |
| S1 Offseason | Development | Rin Garcia | Low tier, Ceil 70, full-time starter from 44 OVR. | Grew 44 -> 61 (+17), still 9 below ceiling. | Partly kept |
| S1 Offseason | Development | Avery Ash | Low tier, Ceil 70, full-time starter from 45 OVR. | Grew 45 -> 62 (+17), still 8 below ceiling. | Partly kept |
| S1 Offseason | Development | Remy Ramirez | Low tier, Ceil 70, full-time starter from 45 OVR. | Grew 45 -> 61 (+16), still 9 below ceiling. | Partly kept |
| S1 Signing | Recruiting | Noor Perez | Scouted 46-76, 84% interest, Promise at stake. | Signed with Cinderfield; verified OVR 57. | Kept |
| S1 Signing | Recruiting | Callum Saito | Scouted 41-71, 96% interest, Promise at stake. | Signed with Cinderfield; verified OVR 60. | Kept |
| S1 Signing | Recruiting | Ash Ibarra | Estimated 30-80, 51% interest, no prior contact. | Signed with Cinderfield; verified OVR 50. | Kept |
| S2 Start | Roster | Callum Saito | Mid tier, Ceil 74, starting at 60 OVR as prospect signing. | Track growth and playing-time promise. | Open |
| S2 Start | Roster | Noor Perez | Mid tier, Ceil 75, starting at 57 OVR as prospect signing. | Track growth and playing-time promise. | Open |
| S2 Start | Roster | Ash Ibarra | Low tier, Ceil 68, starting at 50 OVR as prospect signing. | Track growth as likely bench/rotation player. | Open |

## Issues Ledger

| ID | Severity | Screen | Action | Expected | Actual |
| --- | --- | --- | --- | --- | --- |
| S1-UI-001 | Low | Command Center / Season Preview | Dismissed Season Preview, visited Roster, returned to Command Center. | Preview stays dismissed for the current season/session unless I ask for it again. | Preview appeared again and blocked the Command Center a second time. |
| S1-UX-002 | Low | Week 1 Debrief / Prospect Pulse | Spent all recruiting actions and gained visible interest on prospects. | Postgame "Prospect Pulse" should summarize interest movement or say no signing/rank movement. | It says "No prospect movement this week," which is technically ambiguous and undersells the visible recruiting work. |
| S1-TRUST-003 | Medium | Standings / Playoff Race | Checked playoff race after W1 loss. | Summary should say Cinderfield is 1 point behind the #4 cutoff, matching the table. | Summary says "0 BACK OF CUT" and "0 points outside the playoff line" while #4 has 1 PTS and Cinderfield has 0. |
| S1-TRUST-004 | Medium | Dynasty Office / Recruit Board | W2 Scouting focus gave 4 scout slots. I clicked Scout on already-known targets and Contact on already-contacted/visited targets because buttons were enabled. | Enabled actions should either produce visible change, consume a slot with feedback, or be disabled with a reason. | Several clicks produced no visible range/interest/status change and did not consume Contact slots; Scout slots were consumed without visible range refinement. |
| S1-TRUST-005 | High | Command Center / Week 2 Debrief | Youth acceleration was selected entering W2 and intended as the Season 1 dev focus. | Postgame Training Impact should report Youth acceleration unless I changed it. | Debrief reported Balanced development as this week's focus and current offseason-growth basis. |
| S1-TRUST-006 | Medium | Command Center / Bye Week | Advanced after W4 into the scheduled bye. | Header, week context, and match card should use the same week number. | Banner says Season 1 -- Week 06, but Week Context says W05 · Bye Week and match card says Week 05 Bye Week. |
| S1-TRUST-007 | High | Dynasty Office / Staff Focus Culture | Selected Culture focus on W5 bye, then used Contact/Visit actions. | Contact/Visit gains should be 25% stronger than normal, or Culture should be disabled/explained on bye weeks. | Gains matched normal +12 contact and +20 visit; no visible 25% boost. |
| S1-TRUST-008 | High | Dynasty Office / Weekly Recruiting | Exhausted recruiting slots on W5 bye, advanced to W6, opened Recruit. | W6 should reset weekly scout/contact/visit slots. | W6 still showed 0 scout, 0 contact, 0 visit remaining and all prospect actions disabled. |
| S1-TRUST-009 | Medium | Offseason Recap / Final Table | Compared #4 and #5 playoff cut. | Tied points/record with lower GP diff should either rank below or show the tiebreaker reason. | Northwood #4 and Solstice #5 both 2-2-2 / 8 pts, but Northwood has +5 GP diff and Solstice +8 with no explanation. |
| S1-TRUST-010 | High | Signing Day | Signed Noor first; River Dubois had a promise at stake and 90% interest before signing. | If a rival signs a promised target between picks, the screen should explicitly say who took them and what happens to the promise. | River disappeared from the board after Noor with no visible explanation in the current Signing Day view. |
### Season 2 continuation - lineup and promise audit

- Roster start after Signing Day: 9 contracted, lineup OVR 59, potential mix 0 Elite / 0 High / 3 Mid / 6 Low.
- The auto-created starting six did **not** include the two signed playing-time promise players. Callum Saito (60 OVR, Mid, Ceil 74) and Noor Perez (57 OVR, Mid, Ceil 75) were rotation/non-starters at season start.
- Manual lineup action: opened Lineup Editor, swapped Callum into Utility for Luca Hawthorne, then Noor into Anchor for Ash Kline. The editor showed "Saved" and the roster table reordered with both Callum and Noor marked as starters.
- Lineup editor note: slot order is meaningful (+3 action stats for fit seats in slots 1-4 and opening rush order), so this was not just cosmetic.
- UI note: after the second swap, the visible DONE button did not match through the normal role locator, but the editor had already saved and the roster confirmed the state. Low severity interaction miss.
- Promise audit in Dynasty Office:
  - Noor Perez: Early playing time, OPEN, "They appear in at least 6 matches this season."
  - River Dubois: Early playing time, OPEN, "They appear in at least 6 matches this season."
  - Callum Saito: Early playing time, OPEN, "They appear in at least 6 matches this season."
- **Finding S2-TRUST-011 (High):** River Dubois is still an open playing-time promise even though River disappeared from Signing Day and is not on my roster. Expected: promise should resolve, fail with a clear cause, or be removed if the player signed elsewhere. Actual: impossible active promise remains, with no visible way to satisfy it.

#### Season 2 claims ledger additions

| Claim / surface | Logged expectation | Later check |
| --- | --- | --- |
| Program Credibility says 5 weeks spent prioritizing youth development | S1 had 6 match weeks plus one bye with Youth selected most of the time; the count makes W2's Balanced mismatch and/or bye handling visible. Expect this to affect future base interest. | Check after S2 and compare recruiting warmth. |
| Staff Room Training head shows "+6% dev" | If Training staff focus or training department matters, offseason growth should be measurably strong in Training-focus seasons and/or for young players. | Compare S2 Tactical-drills season to S1 Youth+Training season. |
| Playing-time promises require 6 appearances this season | Noor and Callum must start all six matches because S2 has a Week 1 bye and six games. River cannot be satisfied because he is not rostered. | Check promise grading at S2 end. |

### Season 2 Week 1 - bye week

- Season preview kept resurfacing after navigation to Roster/Dynasty/Command Center. Low friction issue: it interrupts weekly management even after being dismissed.
- Development focus set to **Tactical drills** for Season 2. The real dropdown value changed to `TACTICAL_DRILLS`, though the compact command card still visually lists all options.
- Staff Focus location discovery: the five Staff Focus options are buried under **Dynasty Office -> Program Settings**, not the Staff tab or Command Center. This is findable only after hunting.
- Staff Focus selected: **Scouting - extra assignment**. Claim: one extra Scout action this week, 3 -> 4.
- Verification: recruit board changed to **4 / 4 Scout** and "4 scout · 5 contact" in Reach Remaining. Claim kept for a bye week.
- Recruit board before action:
  - Rowan Cole: Two-Way Threat, Pipeline 3, Fit 67 Fair, Interest 41%, Unscouted OVR 37-87.
  - Zara Rodriguez: Iron Anchor, Pipeline 3, Fit 61 At Risk, Interest 41%, Unscouted OVR 31-81.
  - Remy Garrison: Sharpshooter, Pipeline 4, Fit 57 At Risk, Interest 46%, Unscouted OVR 27-77.
  - Luca Cross: Sharpshooter, Pipeline 5, Fit 56 At Risk, Interest 51%, Unscouted OVR 26-76.
  - Talia Vale: Ball Hawk, Pipeline 3, Fit 56 At Risk, Interest 41%, Unscouted OVR 26-76.
- Scouting results:
  - Rowan Cole 37-87 -> 47-77.
  - Zara Rodriguez 31-81 -> 41-71.
  - Remy Garrison 27-77 -> 37-67.
  - Luca Cross 26-76 -> 36-66.
  - Scout counter reached 0 / 4.
- Contact/visit results under Scouting focus:
  - Rowan Cole contact + visit: 41% -> 73% (+12 +20).
  - Luca Cross contact: 51% -> 63%.
  - Zara Rodriguez contact: 41% -> 53%.
  - Remy Garrison contact: 46% -> 58%.
  - Talia Vale contact: 41% -> 53%.
  - Contact/Visit math was normal this week, as expected because Culture was not selected.
- **Finding S2-UX-012 (Low):** Staff Focus is hidden in Program Settings even though it is a weekly tactical/recruiting lever. Expected: weekly focus near Command Center or Staff Room. Actual: buried modal, easy to miss.

### Season 2 Week 2 setup notes

- After advancing from the Week 1 bye, the roster gate showed the promised lineup still intact: Luca Slate, Avery Ash, Noor Perez, Rin Garcia, Remy Ramirez, Callum Saito.
- Matchup vs Solstice: underdog by -39 net starter OVR. This is much closer than Season 1's massive gaps, suggesting S1 development materially changed competitiveness.
- Week 2 recruit slots reset correctly after the bye: 3 scout / 5 contact / 1 visit. This did **not** repeat the S1 W6 no-reset bug.
- Staff Focus selected for Week 2: **Conditioning - recovery week**. Claim: next match stamina drag on every action stat is halved.
- Recruiting actions:
  - Scouted Talia Vale 26-76 -> 36-66.
  - Scouted Ash Prism 23-73 -> 33-63.
  - Scouted Rin Keene 13-63 -> 23-53.
  - Rowan Cole contacted + visited again: 73% -> 100%.
  - Luca Cross 63% -> 75%, Remy Garrison 58% -> 70%, Zara Rodriguez 53% -> 65%, Talia Vale 53% -> 65%.
- **Finding S2-TRUST-013 (High):** Development focus reset from Tactical drills to Balanced at Week 2. Expected: a season-stretch focus persists after a bye, especially because the W1 Rest Report said Tactical drills was current and would shape offseason growth. Actual: Week 2 dropdown value was Balanced until I re-selected Tactical drills.

### Season 2 Week 2 - Solstice Flare

- Before lock: re-selected Tactical drills, set Weekly Intent to Defensive / Preserve Health, scouted opponent, confirmed the promise-player lineup.
- Opponent scouting after reveal: Solstice tendencies showed 5/5 reads, including Aggressive 100%, Opportunistic 100%, Opening Rush All in 100%, Rush Target Center 100%. Defensive plan lowered displayed risk to Low.
- Result: Solstice Flare 8, Cinderfield Orphans 2. First non-shutout of the run.
- Debrief claim: catch disparity decided it, Catches 0-18, +18 catch swing.
- Replay verification: counted 18 `CATCH` event labels in the event log. Visible opening lineup included Noor Perez and Callum Saito. Debrief catch claim held.
- Key performers: Dex Voss 27K/4C/149 impact, Luca Slate 22K/36 impact, Tyne Hassan 5C/18 impact.
- Development focus aftermath correctly said Tactical drills was this week's focus and current season-end focus.
- Standings cross-check: Cinderfield 0-1-0, -6 GP Diff, Defensive plan. This matched the match result.
- Standings tiebreaker concern: Northwood showed 1-0-0, 3 pts, +3 diff but ranked #5 outside the cut behind Aurora 1-1-0, 3 pts, 0 diff. No explanation for games-played/tiebreaker logic.
- Promise panel after match still says only condition text, not progress. Noor and Callum should be 1/6 appearances; River remains impossible.
- Program Credibility dropped from D 42/100 to F 39/100 after the loss. It still says 5 weeks spent prioritizing youth development, so S2 Tactical drills does not increment that youth-specific line.
- **Finding S2-TRUST-014 (Medium):** Promise progress is not visible week to week. Expected: Noor/Callum 1/6, River 0/6 or impossible. Actual: all three remain open with only generic season-end condition text.
- **Finding S2-TRUST-015 (Medium):** Standings cut ordering/tiebreaker remains unexplained when teams have equal points and uneven games played.
- **Finding S2-UX-016 (Low):** Replay's visible Close control did not expose as a normal button target; had to navigate away through the main nav.

### Season 2 Week 3 - Northwood Ironclads

- Staff Focus selected: **Tactics - film week**. This is the second Tactics-focus use of the run. Claim: next match throwers get +18 effective Tactical IQ on reads/timing.
- Development focus check: Tactical drills was still selected at the start of W3, so the W2 reset was not a simple every-week reset. Re-selected before sim anyway.
- Recruiting:
  - Scouted Rowan Zane 9-59 -> 19-49.
  - Re-scouted Rowan Cole and Talia Vale; the UI said the scout report was already as tight as it gets. Scout slots were still spent.
  - Luca Cross 75% -> 100% after contact + visit.
  - Remy Garrison 70% -> 82%, Zara Rodriguez 65% -> 77%, Ash Prism 41% -> 53%, Rowan Zane 51% -> 63%.
  - Talia Vale contact attempt did not change interest or spend the slot despite the click succeeding; leftover slot then went to Rowan Zane.
- Match setup: Defensive / Preserve Health, Tactical drills, opponent scouted 5/5. Northwood -53 net starter OVR favorite.
- Result: Northwood 8, Cinderfield 3. Improvement trend continues: the team now takes points but still loses catch economy badly.
- Debrief claim: Catch disparity, Catches 1-19, +18 catch swing.
- Replay verification: counted 20 total `CATCH` event labels; 19 were Northwood catches and one was Rin Garcia catching Lin Steel at event 253. Debrief catch claim held.
- Key performers: Lux Zenith 30K/1C/132 impact, Nola Sinclair 1K/8C/38 impact, Avery Ash 16K/23 impact.
- Replay note: visible Cinderfield court order in replay (`Noor, Luca, Rin, Callum, Avery, Remy`) did not match the confirmed six order (`Luca, Avery, Noor, Rin, Remy, Callum`). This may be current court state rather than lineup slot order, but because the editor says slot order is mechanical, the replay should label what order is being shown.
- **Finding S2-TRUST-017 (Medium):** Some repeated scouting/contact actions remain enabled after they can no longer change the player. Expected: disabled, explained, or no slot spent. Actual: repeated scouting consumed slots for already-tight reports; one Talia contact click produced no interest gain and left a contact slot unspent.

### Season 2 Week 4 fast-forward audit

- Pre-fast-forward state:
  - Record 0-2, Week 4 vs Lunar Syndicate, underdog -53 net starter OVR.
  - Defensive plan, promised lineup visible in the confirmation panel: Luca Slate, Avery Ash, Noor Perez, Rin Garcia, Remy Ramirez, Callum Saito.
  - Scout/lineup gates were still pending.
  - Tactical drills was selected before opening fast-forward.
- Fast-forward modal claim:
  - Skips weekly decision loop.
  - Uses last saved weekly plan: intent, tactics, department orders.
  - Fields the **canonical best-six lineup**, not necessarily the manually promised lineup.
  - Does not show pre-match desk or weekly ceremony for skipped weeks.
  - Stop options: next bye, pre-playoffs, offseason.
- Screenshot saved outside repo: `C:/Users/Maurice/AppData/Local/Temp/codex-dodgeball-playtest/playtest2-s2w4-fast-forward-modal.png`.
- I used the default **To pre-playoffs** stop. Because Cinderfield missed the playoffs, the game landed directly in Offseason Beat 1.
- Final regular-season table after skipped weeks:
  - Cinderfield 7th of 7, 0-6-0, 0 pts, -34 GP diff.
  - Pre-fast-forward GP diff after W3 was -11, so the skipped W4-W7 matches combined for -23.
  - Screenshot saved outside repo: `C:/Users/Maurice/AppData/Local/Temp/codex-dodgeball-playtest/playtest2-s2-fast-forward-final-table.png`.
- Audit expectation: because fast-forward warned that it fields canonical best-six, I expect it may have benched Noor and/or Callum and broken playing-time promises unless the promise system overrides canonical best-six. Need check promise grading.
- **Finding S2-TRUST-018 (High, pending grading):** Fast-forward explicitly says it fields canonical best-six, which can conflict with active playing-time promises. If promise grading punishes the player for this, the fast-forward tool can silently break promises through automation.

### Season 2 offseason beats 2-6

- Champion: Harbor Tidebreakers won from the #3 seed. Lunar went 6-0-0 in the regular season but lost the final 12-11. Good league volatility; the table was not deterministic chalk.
- Awards:
  - MVP Brin Moreau, Harbor: 148 throw elims, 29 catches, 98 times out, 71 OVR, 255 career elims.
  - Best Thrower Ayo Slate, Lunar: 177 throw elims.
  - Best Catcher Cruz Ibarra, Harbor: 47 catches.
  - Best Newcomer Noor Perez, Cinderfield: 35 season elims.
- Records:
  - My club: 0 records. League: 3.
  - Ayo Slate career eliminations 171 -> 310, taking record from Dray Slate.
  - Lunar longest unbeaten run 6 -> 10.
  - Cruz Ibarra extended career catches 38 -> 85.
- Development under Season 2 Tactical drills:
  - Noor Perez 57 -> 65 (+8), Ceil 75, TIQ +6.
  - Ash Ibarra 50 -> 58 (+8), Ceil 68, TIQ +3.
  - Callum Saito 60 -> 66 (+6), Ceil 74, TIQ +6.
  - Luca Hawthorne 60 -> 64 (+4), Ceil 70, TIQ +6.
  - Luca Slate 62 -> 66 (+4), Ceil 72, TIQ +5.
  - Ash Kline 61 -> 65 (+4), Ceil 70, TIQ +4.
  - Rin Garcia 61 -> 65 (+4), Ceil 70, TIQ +4.
  - Remy Ramirez 61 -> 65 (+4), Ceil 70, TIQ +3.
  - Avery Ash 62 -> 65 (+3), Ceil 70, TIQ +5.
- Claims ledger read:
  - Tactical drills did tilt visible TIQ growth upward for several players, but total OVR growth was much lower than S1 Youth acceleration.
  - Playing-time impact remains unclear: Ash Ibarra was not a starter and still gained +8, tying Noor for largest growth. Callum, a promised starter, gained +6. Founders near ceiling gained +3 to +4, so headroom may matter more than minutes.
  - Ceilings are still not reached after two full seasons. Founders now sit around 64-66 against 70-72 ceilings; Noor/Callum remain 8-10 OVR short of ceiling.
- Rookie preview: 0 top prospects, 0% high-confidence, no rookies project at 70+ OVR, 12 incoming rookies and 12 veteran free agents. Veterans remain forbidden.
- **Finding S2-TRUST-019 (Medium):** The game says "reps now shape the climb" for Noor, but development evidence does not separate starter growth from bench/rotation growth clearly. Expected: a visible minutes/reps explanation. Actual: bench Ash Ibarra gained as much OVR as award-winning Noor.

### Season 2 Signing Day and schedule reveal

- Signing Day board included warmed prospects, new unscouted prospects, and veteran free agents. I ignored all free agents.
- Signed Rowan Cole first:
  - Pre-signing range 47-77, Interest 100%.
  - Contested round won: my offer 97 beat Lunar 84.
  - Verified OVR 68, age 19.
  - This became the strongest player on the roster and the top rookie in the class.
- After Rowan, Zara Rodriguez disappeared from the board without a visible explanation. This repeats the River/Mara disappearance problem from S1.
- Signed Elio Ibarra second:
  - Pre-signing unscouted range 34-84, Interest 40%.
  - Contested round won: my offer 86 beat Lunar 81.
  - Verified OVR 52. Upside chasing without scouting was punished but within the stated range.
- Signed Luca Cross third:
  - Pre-signing range 36-66, Interest 100%.
  - Verified OVR 54.
- Class report:
  - 3/3 signings used, roster 12/12.
  - 14 rival signings, 21 total rookies.
  - Top class OVR 68.
  - My class: Rowan Cole 68, Luca Cross 54, Elio Ibarra 52.
  - No veterans signed.
- Season 2028 schedule reveal:
  - Wk 1 bye, then Solstice, Aurora, Northwood, Harbor, Lunar, Granite.
- Promise grading audit:
  - No visible promise grading appeared anywhere in the S2 offseason beats or schedule reveal, despite open promises for Noor, Callum, and impossible River.
  - This is a major trust gap: the player made promises, watched/managed lineups for them, then got no explicit kept/broken/fairness verdict.
- **Finding S2-TRUST-020 (High):** Promise lifecycle is not fully visible. Expected: made -> tracked progress -> graded with kept/broken result. Actual: promises were open all season, no progress counts appeared, and no grading screen appeared during offseason.
- **Finding S2-TRUST-021 (High):** Board targets can disappear between picks without an audit line showing who signed them. Expected: "Zara signed with X" or rival picks interleaved. Actual: target vanishes from selectable board until the final class report, which is too late for decision accountability.

### Season 3 start audit

- Promise outcomes finally appeared in Dynasty Office at Season 3 Week 1, not during the S2 offseason ceremony:
  - Noor Perez: KEPT, appeared in 6 matches (threshold 6).
  - River Dubois: VOIDED, Aurora Sentinels signed them before I could deliver; no credibility effect.
  - Callum Saito: KEPT, appeared in 6 matches (threshold 6).
  - Promise record line: 2 kept, 0 broken, +8 credibility.
- Promise verdict was fair once found. The issue is timing/traceability: it appears only after starting the next season and going to Dynasty Office.
- Program Credibility: Tier F, 32/100, with career 0 wins and 12 losses. Losing dragged credibility down hard despite kept promises.
- Season 3 roster:
  - 12 contracted, lineup OVR 63, 6 starters / 2 rotation / 4 bench.
  - Potential mix: 0 Elite / 1 High / 3 Mid / 8 Low.
  - Rowan Cole is the first High potential player: OVR 68, Ceil 82, age 19.
  - Founding core after two development years: Luca Slate 66 (Ceil 72), Rin 65, Remy 65, Avery 65, Ash Kline 65, Luca Hawthorne 64.
  - Noor 65 (Ceil 75), Callum 66 (Ceil 74), Ash Ibarra 58, Elio Ibarra 52, Luca Cross 54.
- **Major lineup issue:** Season 3 starting six were Luca Slate 66, Rin 65, Remy 65, Avery 65, Noor 65, **Luca Cross 54**. Rowan Cole 68 and Callum Saito 66 were not starting. Expected: auto-reorder/canonical best-six starts Rowan and Callum. Actual: a 54 OVR rookie started over the highest-OVR, highest-ceiling player on the roster.
- Season 3 recruiting class claims:
  - Vale Cross: Net Specialist, Pipeline 2, Fit 70, Interest 35%, unscouted OVR 41-91.
  - Luca Petrov: Ball Hawk, Pipeline 4, Fit 66, Interest 45%, unscouted OVR 37-87.
  - Rin Bishop: Sharpshooter, Pipeline 5, Fit 59, Interest 50%, unscouted OVR 30-80.
  - This is the first class with a 90+ displayed ceiling range, but still no displayed Elite/Generational tag before scouting.
- **Finding S3-TRUST-022 (High):** Offseason/season-start lineup can be badly wrong after signings. Expected: best-six or clearly promised/manual lineup. Actual: 68 OVR High-potential Rowan benched while 54 OVR Luca Cross starts.

### Season 3 Week 1 - bye setup

- Used Auto-Assign to fix the lineup:
  - Before: Luca Slate, Avery, Noor, Rin, Remy, Luca Cross 54.
  - After: Rowan Cole 68, Luca Slate 66, Callum Saito 66, Ash Kline 65, Rin Garcia 65, Remy Ramirez 65.
  - Auto-Assign benched Noor and Avery on 65 OVR ties. This is defensible for OVR but weak for the "watch highest ceiling" prompt because Noor still has Ceil 75.
- Set Season 3 development focus to **Strength and conditioning** for the next full-season stretch.
- Roster is 12/12, so I did not open new prospect promises yet. Promise cap allows it, but with no visible roster space/cut flow, promising signings now risks breaking promises through my own choice.
- Staff Focus selected: **Culture - locker-room week**. Claim: Contact/Visit gains are 25% stronger.
- S3W1 recruiting:
  - Scouted Vale Cross 41-91 -> 51-81.
  - Scouted Luca Petrov 37-87 -> 47-77.
  - Scouted Rin Bishop 30-80 -> 40-70.
  - Vale Cross visit: 35% -> 60% (+25), then contact to 75% (+15).
  - Luca Petrov contact: 45% -> 60% (+15).
  - Rin Bishop contact: 50% -> 65% (+15).
  - Imani Ali contact: 45% -> 60% (+15).
  - Luca Hansen contact: 35% -> 50% (+15).
- Culture verdict: the numeric claim works when the action lands on a live card. Immediate contact clicks right after scout-result toasts initially did not spend slots, but later clicks worked.
- Claims ledger:
  - Vale Cross is now the strongest prospect claim so far: scouted 51-81 with a 91 pre-scout high range, but no Elite/Generational tag.
  - Rowan Cole is the first High-potential rostered player, OVR 68, Ceil 82. Track whether High produces a meaningfully different career.

### Season 3 Week 2 - Solstice Flare

- Matchup gap with Rowan starting: only -12 net starter OVR, a major improvement from Season 1 and 2 blowouts.
- Development focus: Strength and conditioning persisted in the actual dropdown. The compact command card still visually lists all dev options, which is misleading but not a state reset this time.
- Staff Focus: Training - practice block.
- Recruiting:
  - Scouted Imani Ali 22-72 -> 32-62.
  - Scouted Luca Hansen 21-71 -> 31-61.
  - Scouted Selah Kim 20-70 -> 30-60.
  - Vale Cross 75% -> 100% after normal contact + visit.
  - Luca Petrov 60% -> 72%, Rin Bishop 65% -> 77%, Imani Ali 60% -> 72%, Selah Kim 40% -> 52%.
- Result: Solstice 10, Cinderfield 5.
- Primary factor changed: Opening rush deficit, "Down 6 early, low point @ tick 93." This is the first time the failure was not pure catch disparity.
- Key performer: Ash Kline had 21K/5C/50 impact, a real player-facing bright spot from the founding core.
- Training impact correctly reported Strength and conditioning.
- Postgame suggestions: shore up Sharpshooter depth, rest Callum, warm up Luca Petrov.
- Claims ledger: Rowan changed the team's competitive profile immediately, but not enough to win. The High-potential tag is already meaningful at the lineup level.

### Season 3 explicit fast-forward to offseason

- Pre-fast-forward state:
  - Week 3, 0-1, at Aurora, -19 net starter OVR.
  - Rowan-led corrected lineup visible: Rowan, Ash Kline, Luca Slate, Callum, Rin, Remy.
  - Strength and conditioning selected.
  - Scout/lineup gates were pending.
- Fast-forward stop chosen: **To the offseason**. This explicitly accepts current defaults through every remaining match and playoffs.
- Resulting final table:
  - Cinderfield finished 6th of 7, 2-4-0, 6 pts, -7 GP diff.
  - First wins of the run happened inside fast-forward.
  - Missed playoffs by one win/3 points.
- Audit notes:
  - Fast-forward turned a 0-win club into a 2-win club, but the skipped weekly loop means the player does not see why the wins happened.
  - Recruiting actions after W2 were skipped; this is expected from the modal but costly in a dynasty run.
  - The team improved from S2's 0-6, -34 to S3's 2-4, -7 after adding Rowan and fixing lineup.
- **Finding S3-TRUST-023 (Medium):** Fast-forward can produce milestone wins without surfacing the evidence trail. Expected: a compact summary of skipped match results, lineup used, and any major tactical factors. Actual: immediate final table only.

### Season 3 offseason development and league state

- Champion: Granite Specters won from the #3 seed after a 3-3 regular season. Again, playoffs are volatile.
- Awards:
  - MVP Jules Martinez, Granite: 206 throw elims, 0 catches, 73 times out, 78 OVR.
  - Best Thrower Ayo Slate: 197 throw elims.
  - Best Catcher Lux Zenith: 48 catches.
  - Best Newcomer Rowan Cole: 120 season elims.
- Development under Strength and conditioning:
  - Elio Ibarra 52 -> 60 (+8), Ceil 69, STA +11.
  - Rowan Cole 68 -> 74 (+6), Ceil 82, STA +7, POW +5, but also DOD +10 and TIQ +9.
  - Noor Perez 65 -> 70 (+5), Ceil 75.
  - Ash Ibarra 58 -> 63 (+5), Ceil 68.
  - Luca Hawthorne 64 -> 68 (+4), Luca Slate 66 -> 70 (+4), Ash Kline 65 -> 69 (+4), Rin 65 -> 69 (+4), Remy 65 -> 69 (+4), Callum 66 -> 70 (+4), Luca Cross 54 -> 58 (+4), Avery 65 -> 68 (+3).
- Claims ledger:
  - High potential is meaningful: Rowan is already 74 OVR, Best Newcomer, and gained +6 despite starting much higher than the low-tier founders.
  - Founding core is approaching displayed ceilings: several 69/70 or 70/72.
  - Strength and conditioning partly supported stamina growth, but the stat tilt is noisy: Rowan gained more DOD/TIQ than POW/STA, so the player cannot easily see the claimed focus effect at a glance.
  - Bench/rotation growth still looks strong: Elio +8 and Ash Ibarra +5 despite not being key starters.
- **Finding S3-TRUST-024 (Medium):** Development focus stat tilts are hard to audit from the ceremony. Expected: group summary showing focus-boosted stats versus tradeoff stats. Actual: raw deltas only; some deltas do not obviously match the claimed focus.

### Season 3 retirements and blocked signing class

- Retirements:
  - Cass Chavez, 58 final OVR, 81 career elims, 0 titles, 2 seasons, Low potential.
  - Lane Holt, 55 final OVR, 63 career elims, 0 titles, 2 seasons, Low potential.
  - No Cinderfield retirements yet; founding core is still active.
- Rookie preview:
  - 1 top prospect.
  - 1 of 28 rookies projected at 70+ OVR.
  - 4% high-confidence.
  - 28 incoming rookies, 28 veteran free agents.
- Signing Day skipped to class report with no selection:
  - 0/3 signings, 0 others joined, 0 total rookies shown in report.
  - Class brief named Callum Zane 72, Quinn Sol 69, Talia Rousseau 67, Talia Vale 67, Niko Petrov 66.
  - Current roster sizes: every AI club 9 players, Cinderfield 12 players.
- Churn verdict:
  - Because Cinderfield is full, the game gave no cut/release or stash decision. This blocks the "sign at least one prospect when roster space exists" rule fairly, but it also stalls the multi-generation loop unless retirements/free slots happen.
- **Finding S3-SYSTEM-025 (High):** Full roster prevents new prospect churn and provides no player-facing release/roster-space tool. Expected: a dynasty manager can cut, graduate, redshirt, or otherwise manage room. Actual: full roster skips Signing Day and the player cannot refresh generations on purpose.

### Season 4 fast-forward regression

- Season 4 start:
  - Roster 12/12, lineup OVR 67.
  - Rowan Cole 74, Luca Slate 70, Callum 70, Ash Kline/Rin/Remy 69, Noor 70 in rotation.
  - Development focus set to **Balanced** for the fourth full-season mode.
- Fast-forwarded from Week 1 bye to pre-playoffs.
- Result: missed playoffs, 7th of 7, 0-5-1, 1 pt, -24 GP diff.
- This is a regression from Season 3's 2-4-0, -7 despite a stronger roster.
- Audit concern: the game gives no explanation for why a stronger team collapsed under fast-forward/default plan. Because the weekly scouting/tactics loop was skipped, the player cannot tell whether this is bad tactics, matchup variance, lineup choice, or fast-forward behavior.
- **Finding S4-TRUST-026 (High):** Fast-forward/default management can produce a severe regression without an evidence trail. Expected: skipped-season summary with lineup used, match scores, and main failure factors. Actual: final table only.

### Season 4 offseason

- Champion: Granite Specters repeated, now 2 titles.
- Awards: Granite's Jules Martinez MVP again with 283 throw elims, 82 OVR; Granite is becoming the league boss.
- Development under Balanced:
  - Rowan Cole 74 -> 78 (+4), Ceil 82.
  - Elio Ibarra 60 -> 64 (+4), Ceil 69.
  - Noor 70 -> 73 (+3), Ceil 75.
  - Callum 70 -> 73 (+3), Ceil 74.
  - Founders began hitting ceilings:
    - Luca Hawthorne 68 -> 70, Ceil 70.
    - Luca Slate 70 -> 72, Ceil 72.
    - Avery 68 -> 70, Ceil 70.
    - Ash Kline 69 -> 70, Ceil 70.
    - Rin 69 -> 70, Ceil 70.
    - Remy 69 -> 70, Ceil 70.
- Claims ledger verdict so far:
  - Displayed ceilings do get reached, especially by the founding core after four seasons.
  - High-potential Rowan is separating but has not yet reached his 82 ceiling.
  - Balanced growth appears like a taper/cap year rather than a unique visible identity.
- Rookie preview: 4 top prospects, 4 of 30 rookies project at 70+ OVR, 13% high-confidence.
- Signing Day again skipped due full roster:
  - 0/3 signings.
  - Top class names included Ash Prism 73, Ezra Helix 73, Tobin Tanner 72, Cass Jensen 72.
  - Cinderfield remained 12 players while AI clubs are 9.
- **Finding S4-SYSTEM-027 (High):** The full-roster blocker repeated in a stronger rookie class. The game is now preventing the prospect-only churn challenge from continuing, not because of bad decisions, but because no roster-space lever is exposed.

### Season 5 hands-on regular season

- Strategy: hands-on weekly play, Balanced development, Weekly Intent Aggressive / Win Now, scout every opponent, confirm lineup every match.
- Week 2: beat Solstice 9-6.
  - Primary factor: Catch disparity in our favor, Catches 21-16.
  - Key performers: Luca Slate 15K/5C/86 impact, Ash Kline 18K/2C/69, Rowan Cole 17K/8C/68.
  - This was the first hands-on proof that the developed roster could win through catches.
- Week 3: lost to Granite 2-14.
  - Granite was -35 net starter OVR against us.
  - Catches 12-28 against; Wren Johansen 21K/12C/128 impact.
- Week 4: beat Harbor 8-7.
  - Catches 21-19 in our favor.
  - Ash Kline 20K/3C/84 impact, Rin 8K/6C/57.
- Week 5: beat Northwood 9-4.
  - Even matchup, +1 net starter OVR.
  - Catches 17-7 in our favor.
  - Rowan 32K/126 impact.
- Week 6: beat Aurora 10-5.
  - Catches 20-11 in our favor.
  - Cinderfield rose to #2 after this win.
- Week 7: lost to Lunar 5-10.
  - Catches 11-19 against.
  - Cinderfield fell from #2 to #3 but stayed in playoff position.
- Regular-season verdict: hands-on scouting/intent produced the first playoff push. The same roster had collapsed under Season 4 fast-forward, so the weekly loop appears materially important.
- **Finding S5-BALANCE-028 (Medium):** Catch economy dominates the outcome explanation in almost every competitive match. This is readable, but it risks becoming solved: win catches, win match.

### Season 5 playoff semifinal

- Opponent: Lunar Syndicate, rematch after Week 7 loss.
- Playoff-specific policy adjustment made in Policy Editor:
  - From Aggressive / Their stars / Go for catches / All in / Center.
  - To Mixed / Spread / Opportunistic / Balanced / Nearest.
  - Scouting then revealed Lunar tendencies: Aggressive 100%, Their stars 97%, Opportunistic 100%, All in 100%, Center 100%.
- Result: Lunar 11, Cinderfield 6. Eliminated in semifinal.
- Primary factor: "Edged across the sets" rather than catch disparity; no one lever proved decisive.
- The custom playoff policy was visible in the debrief: our side Mixed + Spread.
- Key performers: Dex Beck 34K/2C/132 impact, Quinn Das 28K/1C/105, Lin Kone 10K/5C/42. Our best: Ash Kline 22K/3C/41.
- **Finding S5-TRUST-029 (Critical):** The season-ending elimination panel contradicted the match result. Debrief result was Lunar 11, Cinderfield 6, but the elimination panel said `0 vs Lunar Syndicate 0` and "Shut out 0-0. Nothing fell your way." Expected: elimination summary repeats 6-11 and explains the actual loss. Actual: false 0-0 shutout copy.

### Season 5 offseason

- Final table: Cinderfield 4-2-0, 12 pts, -3 GP diff, #3 seed. Harbor missed playoffs despite +11 diff because points put them #5; standings were plausible by points this time.
- Champion: Granite Specters, third straight title. Granite now feels like the league boss.
- Playoff bracket correctly recorded our semifinal: Lunar 11, Cinderfield 6. This conflicts with the false elimination panel but the bracket itself is truthful.
- Awards: Wren Johansen MVP, Granite, 87 OVR; Dex Beck Best Thrower; Noor Sterling Best Catcher; Talia Jensen Best Newcomer.
- Records: Granite extended longest unbeaten run to 18; Granite titles to 3.
- Development:
  - Rowan 78 -> 81 (+3), Ceil 82.
  - Elio 64 -> 67 (+3), Ceil 69.
  - Luca Cross 61 -> 64 (+3), Ceil 64.
  - Noor 73 -> 75 (+2), Ceil 75.
  - Ash Ibarra 66 -> 68 (+2), Ceil 68.
  - Callum 73 -> 74 (+1), Ceil 74.
  - Only 6 players changed OVR; most founding-core players are now capped.
- Retirements: Dray Slate, Tyne Hassan, Yuki Rodriguez retired after 3 seasons. Veteran retirement exists and the league is turning over, but Cinderfield still has no departures.
- Claims ledger:
  - Ceilings are real and reachable: Luca Slate, Noor, Callum, Luca Cross, Ash Ibarra, and most low-ceiling founders have reached or nearly reached displayed ceilings.
  - High-potential Rowan is one point short of ceiling and is clearly a different class of player.

### Season 6 hands-on regular season

- Strategy: hands-on weekly again. Aggressive / Win Now for most opponents; Control used against Granite to see whether lower-risk possession helped.
- Week 2: lost to Solstice 7-8, catches 9-13 against.
- Week 3: lost to Granite 3-13 despite Control plan, catches 11-25 against. Control did not solve Granite.
- Week 4: drew Lunar 8-8, catches 19-16 in our favor. This was the first non-loss against Lunar and felt like progress.
- Week 5: beat Aurora 12-3, Rowan 46K/1C/204 impact.
- Week 6: beat Harbor 9-6.
- Week 7: beat Northwood 9-7, Rowan 44K/174 impact, climbed from #5 to #4.
- Season 6 regular-season verdict: made playoffs as #4 after a late surge. Rowan is now carrying title-contender performances, but Granite remains a wall.

### Season 6 playoff semifinal

- Opponent: Granite Specters, #1 seed, -43 net starter OVR against us.
- Tried high-risk Aggressive upset plan after Control failed in the regular season.
- Scouting confirmed Granite tendencies: Aggressive 100%, Their stars 86%, Opportunistic 100%, All in 100%, Center 100%.
- Result: Granite 15, Cinderfield 2. Eliminated.
- Primary factor: Catch disparity, Catches 11-24, +13 catch swing against.
- Granite performers: Noa Rodriguez 21K/1C/95 impact, Noor Sterling 21K/3C/95, Wren Johansen 16K/11C/90.
- **Finding S6-TRUST-030 (Critical):** The false playoff elimination panel repeated. Debrief said Granite 15, Cinderfield 2, but elimination panel again said `0 vs Granite Specters 0` and "Shut out 0-0. Nothing fell your way." Repro: lose a playoff semifinal, then read the elimination panel below the debrief.

### Season 6 offseason

- Final table: Cinderfield 3-2-1, 10 pts, +3 GP diff, #4 seed.
- Champion: Granite Specters again, fourth title. Final was Granite 11, Lunar 11; higher seed tiebreaker gave Granite the title, and this was clearly explained.
- Development:
  - Rowan Cole 81 -> 82, reached Ceil 82.
  - Elio Ibarra 67 -> 69, reached Ceil 69.
  - Only 2 players changed OVR. The roster is now effectively capped.
- Retirements: River Bolt, Saga Kone, Tyne Bishop retired. Still no Cinderfield retirements.
- Signing Day again skipped with 0 signings despite class top names Mara Hassan 75, Zeph Saito 74, Luca Tanner 74, Zara Olsen 72, Ash Hansen 70. Cinderfield 12 players, AI clubs 9.
- Claims ledger:
  - High-potential Rowan reached his displayed ceiling and became a true carry, but still could not overcome Granite's superteam alone.
  - Roster lifecycle is now stalled: no room for a second core to replace founders, and no retirements from my roster yet.
