# PLAYTEST JOURNAL 5 - Climb-Era Fresh-Eyes Trust Playtest

## Scope

- Branch: `feature/v24-the-board`
- Mode: browser-only player-facing playtest after setup; no source-code explanation for gameplay behavior.
- Target app: production web app on port 8010.
- Careers:
  - Build-from-scratch D3 club, with staff-hire step, at least 4 full seasons.
  - Premier takeover club, at least 2 full seasons.
- North star: decision traceability. Any UI claim must be traceable to a visible outcome, receipt, or contradiction.

## Setup Log

- Repo path confirmed: `C:\GPT5-Projects\Dodgeball Simulator`.
- Branch confirmed: `feature/v24-the-board`.
- Initial dirty state: pre-existing untracked `opencode.json`; left untouched.
- Install completed: `python -m pip install -e '.[dev]'`.
- Frontend production build completed from `frontend/`: `npm run build`.
- Pare MCP was not available in callable tools, so setup used normal local commands.

### Setup Trust Issue

- **P1 - Launcher ignores explicit port argument and can touch the owner's live port.**
  - Screen/setup surface: production launcher command.
  - Claim/expectation: playtest must launch on port 8010 and never touch port 8000.
  - What happened: `python -m dodgeball_sim.web_cli --port 8010` started the app on `http://localhost:8000`, logged `Stopped previous Dodgeball Manager server.`, and ignored the explicit port argument.
  - Repro: from repo root, run `python -m dodgeball_sim.web_cli --port 8010`.
  - Cleanup: stopped only the process started by this run (`57524`). Port 8000 is now only in `TIME_WAIT`; port 8010 is clear.
  - Player/trust impact: not in-game, but it violates the launch contract for this playtest and can disrupt a live owner session.

## Findings

- **P2 - New Game still leaves old-save context on screen while choosing a creation path.**
  - Screen: title screen after clicking `New Game`.
  - Claim/expectation: a fresh career start should feel unambiguously separate from old saves.
  - What the UI did: the page kept `Load Game`, old active-career context, and the old save list visible above the `Take Over a Program` / `Build from Scratch` choices.
  - Actual player effect: not a data contradiction, but it is confusing to a newcomer because the fresh-start state still visually competes with old saves.
  - Repro: landing page with existing saves -> click `New Game` -> observe creation choices below old-save context.

### Build-from-Scratch Career: Tacoma Harbor Glass

- Founding setup:
  - Save: `Climb Era Playtest 5 D3`.
  - Club: `Tacoma Harbor Glass`, city `Tacoma`.
  - Coach: Dana Mercer, `Recruiting Legend`.
  - Staff choice: all Premium heads. Staff screen changed committed payroll from `$177k/season` to `$330k/season`, and opening treasury from `$423k` to `$270k`; no contradiction observed at setup.
  - Founding roster: 10/10, including visible high-ceiling/elite prospects Sita Parr, Tomas Mwangi, Manaia Banerjee, and Andres Thorn. Roster draft counters and `OK` markers updated when picks were swapped.

- Season 1 Preview:
  - Screen claim: D3 District League; champion promotes; next four play promotion playoff; regular season 7 weeks; Week 5 bye; playoff cut `Top 4 of 7`.
  - Verification status: Week 2 Standings confirmed a 7-club D3 table with `TOP 4`, a playoff-cut row between #4 and #5, and Tacoma at #1 after a 1-0 start.

- Week 1 command loop:
  - Scout action passed traceability: before scouting, Tactical Diff showed `0/5 reads revealed` and each row was `Unscouted`; after `Scout Opponent`, it showed `5/5 reads revealed`, changed the rows to playbook tendencies, and clearly caveated that these were identity/playbook reads rather than the hidden weekly plan.
  - Confirm lineup action passed traceability: readiness moved from 5/6 to 6/6, `Starting six confirmed` appeared, and `Lock Plan` became enabled.
  - Week 1 result: Old Quarter Wanderers 1, Tacoma Harbor Glass 10. Debrief, replay header, and sampled replay events agreed on game-point score and had explicit throw targets; no replay placeholder target observed in sampled events.

- **P1 - League Wire claims game results were decided by `0-0 survivors` even when the debrief/replay shows game points.**
  - Screen: Standings -> League Wire / Recent Results, Season 1 Week 2 after banking Week 1.
  - Claim: `Week 1: Tacoma Harbor Glass beat Old Quarter Wanderers with 0-0 survivors.` Similar copy appeared for AI winners.
  - What actually happened: the debrief and replay showed Old Quarter Wanderers 1, Tacoma Harbor Glass 10 in game points, with Tacoma marked winner; the same Standings page later correctly listed `Week 1: Old Quarter Wanderers 1-10 Tacoma Harbor Glass`.
  - Repro: Build-from-scratch career -> play/bank Week 1 -> Standings -> Recent Results.
  - Trust impact: high. A league-truth surface uses a different scoring frame from the match report and creates impossible-looking `0-0` winner copy.

- **P2 - Command Center rank chip is ambiguous and appeared inconsistent with Standings immediately after banking Week 1.**
  - Screen: Command Center, Season 1 Week 2.
  - Claim: Broadcast frame showed `Rank #2`.
  - What the data/screen later showed: Standings in the same week showed `Our Rank 1 of 7`, Tacoma #1 on 3 pts and +9 diff.
  - Repro: Build-from-scratch career -> bank Week 1 10-1 win -> Command Center Week 2 -> note `Rank #2` -> Standings.
  - Trust impact: medium-low until clarified, because it may be an unlabeled opponent-rank field; as presented, it reads like our weekly rank and contradicts the table.

- Recruiting Week 2:
  - Staff/economy carry-forward passed: Dynasty Office showed `Treasury $270k`, matching the all-premium-staff opening treasury after founding.
  - Tegan Xu recruiting gates passed after discovering the intended order:
    - Scout: `44-94 -> 55-83`, status `Scouted`, hidden dealbreaker revealed as `Court Time A`.
    - Focus: stage changed to `TOP3`, rival suitors appeared, race showed `TRAILING -49`, Contact/Visit unlocked.
    - Contact: interest `38% -> 50%`, race `TRAILING -37`.
    - Visit: interest `50% -> 70%`, race `TRAILING -17`, `VISIT SET` for Week 7 home game.
    - Promise: `Early playing time` recorded as 1/3 open promises, with exact future check: appear in at least 6 matches in first season.

- **P1 - Scouting Network upgrade spends money but the visible board count goes down while copy says it opens more sheets.**
  - Screen: Dynasty Office -> Scouting Network, Season 1 Week 2.
  - Claim: Level 1 copy said `Raise to L2 to open more sheets across the class.`
  - What happened: clicking `Upgrade to L2 - $122k` changed treasury `$270k -> $148k` and network `Level 1 -> Level 2`, but the Recruit tab and board count changed from `30` prospects to `26` prospects.
  - Repro: Build-from-scratch career -> Dynasty Office Week 2 -> observe `Recruit 30` and L1 network -> click `Upgrade to L2 - $122k` -> observe `Recruit 26`.
  - Trust impact: high for a money-gated system. The spend receipt is visible, but the player-facing result contradicts the stated benefit.

- **P1 - Facility purchase records `Built` in the row but the Staff summary still says `Facilities 0`.**
  - Screen: Dynasty Office -> Staff -> Facilities, Season 1 Week 2.
  - Claim: `Merch Center` is a fan-economy facility; buying facilities should be tracked and visible.
  - What happened: clicked `Build - $140k` for Merch Center. Treasury changed `$148k -> $8k` and the row changed to `Built ✓`, but the top Staff summary still said `Facilities 0` and `No facility upgrades tracked`.
  - Repro: Build-from-scratch career -> buy Scouting Network L2 -> Staff tab -> click `Build - $140k` on Merch Center -> compare row vs Staff summary.
  - Trust impact: high for V26 crowd/facilities because the money is gone and the row says built, but the summary denies any facility upgrades.

- **P2 - Bench roles are not discoverable from the roster, player card, or Program Settings surfaces checked.**
  - Screen: Roster, Tomas Mwangi player card, Dynasty Office -> Program Settings, Season 1 Week 2.
  - Claim/expectation from V26 scope: bench roles should include Mentor/Analyst/Ambassador.
  - What the UI showed: Roster showed starters/rotation/bench counts, but no Mentor/Analyst/Ambassador controls. Tomas Mwangi's player card exposed bio, ratings, release, and close only. Program Settings opened a Staff Focus modal only.
  - Repro: Build-from-scratch career -> Roster -> inspect table and bench player card -> Dynasty Office -> Program Settings.
  - Trust impact: medium. This may be hidden elsewhere, but a normal player cannot find the role system from the obvious roster/bench locations.

- Season 1 playoffs/offseason:
  - Fast-forward modal passed traceability: it explicitly stated skipped weeks use the last saved weekly plan and canonical best-six lineup, and defaulted to stop before playoffs.
  - Semifinal: Tacoma 9-4 Millfields. Surface was internally coherent; set chips summed to 9-4 and the primary factor used cautious `INCONCLUSIVE` confidence for a narrow 16-15 catch edge.
  - Final: Tacoma 17-5 Harborside. Champion banner said `17-5 over Harborside Rovers`, matching the debrief score and set chips.
  - Offseason Beat 1:
    - Final table: Tacoma #1, 4-0-2, 14 pts, +30 GP diff; promoted to Challenger League. This matches the preview's top-4-of-7 regular-season structure plus playoffs.
    - Finances: league payout +$340k, playoff bonus +$140k, staff payroll -$330k, player wages -$62k, net +$88k, treasury $96k. This reconciles with pre-offseason treasury $8k after facility/network spending.
    - Worlds surfaced: `Rhein Kollektiv are World Champions — Osaka Tempo fall in the final.`
  - Offseason Beat 2: champion bracket agreed with semifinal/final scores and marked Tacoma `YOU ADVANCED`.
  - Offseason Beat 4 calendar: Domestic Cup, Midseason International, and Founders' Exhibition winners and brackets appeared. Thin traceability note: intro promises trophy, purse, and story, but this beat showed winner/bracket only; no scorelines or purse receipts were visible.
  - Offseason Beat 6 development: before/after OVR and attribute deltas were shown for every rostered player, and the aging/fatigue reset checklist was explicit.
  - Offseason Beat 7 rookie class preview: archetype breakdown summed to 56 incoming rookies, with 12 veteran free agents also visible.
  - Offseason Beat 8 media moment: chose `Let him shine - +400 fans +1 prestige`; the button press advanced after confirm, but the selected choice did not visibly latch before confirmation.

- **P1 - Signing Day says a rival offer `106` beat my offer `106` without showing a tiebreaker.**
  - Screen: Offseason Beat 9/10 -> Signing Day, Season 1 after courting Tegan Xu through Scout -> Focus -> Contact -> Visit -> Promise.
  - Claim: `Harbor Tidebreakers signed Tegan Xu - their offer 106 beat yours 106. Your interest was 70%, built from 3 recruiting actions. Your signing slot was not used - pick from the remaining class.`
  - What the player can verify: my visible recruiting path built Tegan to 70% interest and one active Early Playing Time promise; the receipt then describes equal numeric offers as one offer beating the other, with no visible tiebreaker, hidden dealbreaker result, or promise consequence.
  - Repro: Build-from-scratch career -> Season 1 Week 2 recruit board -> Scout Tegan Xu -> Focus -> Contact -> Visit -> Promise Early Playing Time -> fast-forward to offseason Signing Day -> click `Sign Tegan Xu`.
  - Trust impact: high. The snipe receipt is present, which is good, but the key outcome reason is mathematically impossible as written unless a hidden tiebreaker exists.

- **P2 - Media-event choice has no visible selected state before confirmation.**
  - Screen: Offseason Beat 8/10 -> Media Moment.
  - Claim: one of two choices should be selected before `Confirm & Continue`.
  - What happened: clicked `Let him shine - +400 fans +1 prestige`; the choice button did not show a clear selected state, though `Confirm & Continue` advanced to the next beat.
  - Repro: Build-from-scratch career -> Season 1 offseason -> Beat 8 Media Moment -> click an option -> observe choice state before confirming.
  - Trust impact: low-medium. The beat likely registered the choice, but a player cannot verify the pending selection before committing.

- **P1 - Class Report summary numbers contradict the class tabs and body.**
  - Screen: Offseason Beat 9/10 -> Signing Day Update -> Class Report, after signing two free agents and locking the class with one unused slot.
  - Claim: the summary strip read `Your Signings 52`, `Rival Signings 56`, `Total Rookies 66`, while the same screen said `You signed 2`, `2/3 slots used`, and the selected tab was `Your Picks (2)`. The rival tab was `Rival Picks (52)`.
  - What the player can verify: my picks were Ines Fairbanks and Marco Garrison only; the page's own detailed count says 2, so `Your Signings 52` appears to be a shifted or mislabeled metric.
  - Repro: Build-from-scratch career -> Season 1 Signing Day -> sign Ines Fairbanks and Marco Garrison -> `Lock class early` -> `Yes, lock the class` -> Class Report.
  - Recurrence: Season 2 Class Report after signing one free agent, Rhys Villanueva, repeated the pattern: summary said `Your Signings 56`, while body said `You signed 1`, `1/3 slots used`, and tab said `Your Picks (1)`.
  - Recurrence: Season 4 Class Report after locking the class with no signings said `Your Signings 56`, while body said `You didn't sign anyone`, `0/3 slots used`, and tab said `Your Picks (0)`.
  - Recurrence: Takeover Season 1 Class Report after locking the class with no signings said `Your Signings 56`, while body said `You didn't sign anyone`, `0/3 slots used`, and tab said `Your Picks (0)`.
  - Trust impact: high. This is a summary surface for a major roster outcome, and the headline count disagrees with the body on the same screen.

- Season 2 opening preview:
  - New division: D2 Challenger League.
  - Preview claim: champion promotes; next four play promotion playoff; bottom two relegate; 7-week regular season; Week 7 bye; Playoff Cut `Top 4 of 7`; finish top 4 of 7 to reach playoffs.
  - V28 League Bulletin appeared in the season preview: `Points of emphasis: officials will reward clean catches this season - a caught ball flips possession, so go up and take it.`
  - Schedule reveal just before this preview showed six Tacoma matches, consistent with a 7-club league and one bye, pending standings cross-check.
  - Week 1 scouting/decision trace: Riverton's observed tendencies showed `Opening Rush: All in` at `100% · n8`; the counter read said holding back the rush and going for catches punishes it on the counter. I kept Balanced / Opportunistic and locked the plan after Scout + Confirm Lineup.

- **P0 - Debrief final-score panel shows `0-0` for a match the same screen calls a `12-2` win.**
  - Screen: Command Center -> Season 2 Week 1 Debrief after simulating Tacoma Harbor Glass vs Riverton Current.
  - Claim: headline said `A dominant 12-2 win`; game-by-game chips showed twelve Tacoma game wins and two Riverton game wins; the Primary Factor said catching decided it, `Catches 22-8`.
  - What contradicted it: the `Final game score` region displayed Tacoma Harbor Glass `0 game points` and Riverton Current `0 game points`, while still marking Tacoma as `Winner`.
  - Repro: Build-from-scratch career -> Season 2 Week 1 -> Scout Opponent -> Confirm Lineup -> Lock Plan -> Simulate Week -> inspect the debrief score panel.
  - Trust impact: critical. The most important outcome panel says 0-0 even though the rest of the debrief proves 12-2.
  - Follow-up: after banking the result, Standings correctly showed Tacoma #2, 1-0-0, +10 diff, and Recent Results included `Week 1: Tacoma Harbor Glass 12-2 Riverton Current`; however, the League Wire result item also said `Tacoma Harbor Glass beat Riverton Current with 0-0 survivors`, so the bad score frame leaks into a league-truth surface.

- V28 catch-emphasis bulletin cross-check, first sample:
  - The Week 1 bulletin said officials would reward clean catches.
  - The Week 1 debrief did support a catch-heavy result: Primary Factor `HIGH CONFIDENCE`, `Catch disparity`, `Catches 22-8`, `+14 catch swing`.
  - Because the same debrief also has the `0-0` final-score contradiction above, the bulletin itself passes this first sample but the match-result shell around it does not.
  - Season 2 Week 2 Standings confirmed the preview structure: D2 table has 7 clubs, `TOP 4`, a playoff-cut row after #4, and bottom-two `DROP` labels in World Standings.

- Season 2 fast-forward/offseason:
  - Fast-forwarded from Week 2 to offseason using the modal's explicit `To the offseason` option, which says it accepts the current defaults through remaining regular-season and playoff matches.
  - Final regular-season table: Tacoma Harbor Glass #1, 5-0-1, 16 pts, +41 GP diff; top four qualified for playoffs.
  - Finances: league payout +$459k, playoff bonus +$189k, matchday +$40k, merch +$5k, staff payroll -$330k, player wages -$85k, net +$278k, treasury $374k. Wage bill increased from Season 1's -$62k after signing Ines Fairbanks and Marco Garrison.
  - League movement: Tacoma and Lunar Syndicate promoted to Premier; Meadowbrook Hornets and Northgate Union relegated to District; Worlds surfaced again (`Rhein Kollektiv are World Champions - Nairobi Thunder fall in the final`).
  - Champion bracket: Tacoma beat Kestrel Bay 14-4 and Lunar Syndicate 13-11, matching the champion banner.
  - Awards: Marco Garrison won Best Catcher and Ines Fairbanks won Best Newcomer, visible consequences from the Season 1 free-agent signings.
  - Calendar beat: Tacoma appeared in Domestic Cup, Cloth Classic, No-Sting Open, and Founders' Exhibition brackets; the bracket paths were visible, but purse receipts were still not shown despite the intro saying these events have a trophy, purse, and story.
  - Development beat: 10 players changed OVR with exact before/after and attribute deltas.

- **P2 - Transfer Period choices do not show a selected state or pre-commit receipt.**
  - Screen: Offseason Beat 8/11 -> Transfer Period, Season 2.
  - Claim: the player can re-sign expiring players, let them walk, accept/refuse buyouts, then `Confirm & Continue`.
  - What happened: clicked first `Let walk` for Ash Yang, second `Re-sign` for Lakshmi Kone, and `Keep him` for Manaia Banerjee. The buttons did not visibly latch, summarize pending choices, or change the wage/treasury figures before confirmation.
  - What the player can verify afterward: Roster showed 11 contracted; Ash Yang was gone, Lakshmi Kone remained, and Manaia Banerjee remained. So the choices did apply, but only after leaving the decision screen.
  - Repro: Build-from-scratch career -> Season 2 offseason -> Transfer Period -> choose one let-walk, one re-sign, one keep-buyout -> observe no selected state before `Confirm & Continue` -> check Roster afterward.
  - Trust impact: medium-low. Outcome is traceable after the fact, but the moment of commitment is opaque and easy to misclick.

- **P1 - Transfer Period re-sign click can appear to fail silently; Hugo Reyes showed up as a free agent after I clicked Re-sign.**
  - Screen: Season 3 Transfer Period into Season 3 Signing Day.
  - Claim: clicking `Re-sign` on an expiring player should keep that player; `Let walk` should release them.
  - What happened: I clicked `Re-sign` for Hakim Desai, Sita Parr, Hugo Reyes, Manaia Banerjee, and Ines Fairbanks, and clicked `Let walk` for Ji-Woo Onyeka, then confirmed. On the next Signing Day, Hugo Reyes appeared in the available free-agent list as `Hugo Reyes Free Agent ... 70 verified ovr`.
  - Repro: Build-from-scratch career -> Season 3 offseason -> Transfer Period with six expiring contracts -> click `Re-sign` for Hugo Reyes -> `Confirm & Continue` -> proceed to Signing Day -> observe Hugo in the free-agent list.
  - Trust impact: high. Because the transfer buttons do not visibly latch, the player has no way to know whether the click failed, toggled, or was overwritten until the player is gone.

- **P1 - Premier League stakes say `Top two reach WORLDS` but the same screens still use a `Top 4` playoff cut.**
  - Screen: Season 3 opening preview and Standings, Premier League.
  - Claim: Premier rule text says `Top two reach WORLDS · bottom two relegate to the Challenger League`.
  - What contradicts it: the preview also defines `Playoff Cut: Top 4 of 7` and says `Finish in the top 4 of 7 to reach the playoffs`; Standings shows `IN PLAYOFF POSITION`, `Hold Top 4`, a `Playoff Cut` row after #4, and helper copy `top 4 advance`.
  - Repro: Build-from-scratch career -> promoted to Premier after Season 2 -> Season 3 preview -> Standings Week 1.
  - Follow-up: Season 3 offseason showed `Top four seeds qualify for the playoffs`; Tacoma finished #1, became Premier champion, and the Worlds line said `Marseille Mistral are World Champions - Tacoma Harbor Glass fall in the final.` The systems appear to both exist, but the Premier preview/standings do not explain how top-four playoffs connect to top-two Worlds qualification.
  - Trust impact: high. A new Premier player cannot tell whether the real target is top 2 for Worlds, top 4 for playoffs, or both, and the stakes text does not explain how those systems relate.

- Season 3 opening preview:
  - New division: D1 Premier League.
  - V28 League Bulletin: `Points of emphasis: officials are discouraging walling up this season - blocks are judged tighter.`
  - Schedule reveal showed six Tacoma matches with Week 4 bye, matching a 7-club table.
  - Fast-forward result: Tacoma #1, 5-0-1, +39, Premier champion; Worlds surfaced with Tacoma losing the final to Marseille Mistral. Finances showed Premier tier scale 1.80x, player wages -$98k, treasury $901k.
  - Premier bracket: Tacoma beat Ridgeline Vanguard 15-4 and Solstice Flare 18-6, matching the Premier champion banner.
  - Calendar beat now did show purse receipts for some events: Tacoma won Cloth Classic `+70k purse`, No-Sting Open `+70k purse`, and Founders' Exhibition `+80k purse`.
  - Transfer Period dealbreaker pass: Ji-Woo Onyeka had `contender F - won't re-sign`; the `Re-sign` button was disabled, making the forced let-walk reason visible. The no-selected-state issue from Season 2 still repeated for the other clicked transfer decisions.

- Season 4 build-from-scratch summary:
  - Preview repeated Premier League stakes mismatch: rule text said top two reach WORLDS, while Playoff Cut still said Top 4 of 7.
  - Bulletin repeated `officials are discouraging walling up this season - blocks are judged tighter.`
  - Fast-forward result: Tacoma #2, 5-1-0, 15 pts, +41; Harbor Tidebreakers were Premier champions. Finances: league payout +$576k, playoff bonus +$144k, matchday +$108k, merch +$14k, staff payroll -$330k, player wages -$146k, net +$366k, treasury $1.49M. Worlds: Nairobi Thunder beat Rhein Kollektiv.

### Takeover Career: Aurora Sentinels

- Setup:
  - Save: `Climb Era Playtest 5 Takeover`.
  - Path: Take Over a Program.
  - Club: Aurora Sentinels, default Premier selection.
  - Setup promise: `finish in the bottom two and your club really is relegated; win the league and WORLDS is next.`
  - Season 1 preview repeated the Premier stakes mismatch: top-two-to-Worlds rule text plus Top 4 of 7 playoff cut. No League Bulletin appeared on Season 1 preview, which matches the season-2+ expectation.
  - Season 1 fast-forward result: Aurora #2, 4-2-0, +5; Solstice Flare were Premier champions. Bottom two, Ridgeline Vanguard and Harbor Tidebreakers, dropped to Challenger, matching the takeover setup's relegation promise. Worlds: Rhein Kollektiv beat Stockholm Norrsken.

- **P1 - Takeover offseason can leave a Premier roster at 6/12 while Signing Day still caps additions at 3.**
  - Screen: Takeover career -> Season 1 offseason -> Signing Day.
  - Claim/expectation: a Premier takeover career should preserve a playable roster or clearly warn when contract decisions will gut the team; Signing Day says you can add up to 3.
  - What happened: after advancing through the Season 1 offseason and confirming the Transfer Period without a visible warning state, Signing Day showed `Roster Size 6 / 12` and `3 signings remain`. Locking the class was still allowed, leaving no visible path to reach 12 before the next season.
  - Repro: Takeover Aurora Sentinels -> fast-forward Season 1 to offseason -> continue through Transfer Period with visible defaults -> Signing Day.
  - Trust impact: high. This makes roster lifecycle consequences much larger than the screen prepares the player for, and the signing cap cannot repair the roster.

- Takeover Season 2 preview:
  - League Bulletin appeared as expected in season 2+: `Points of emphasis: officials are discouraging walling up this season - blocks are judged tighter.`
  - Premier stakes mismatch repeated: top two reach WORLDS, while the same preview used `Playoff Cut Top 4 of 7`.
  - Week 1 command loop could still field a six-player lineup despite the thin roster: Sakura Hart, River Garcia, Avery Singh, Ash Apex, Tane Qureshi, Themba Papadopoulos.
  - Fast-forward result: Aurora #1, 5-1-0, +24, Premier champions. Bottom two Bellmare Chargers and Stillwater Herons dropped to Challenger. Worlds: Osaka Tempo beat Bahia Cobras.

## V28 Weather / AI Drift Notes

- League Bulletin appeared on season-2+ previews and Standings/League Wire surfaces, including catch emphasis and tighter-blocking emphasis.
- I could verify one catch-emphasis sample directly: Season 2 Week 1 debrief said catching decided the match, with `Catches 22-8`.
- I did not find a player-facing trend report that clearly tied multi-season AI tactic drift to a historical winning trend. Standings tables expose plan labels such as Balanced/Power Throwers, and scouting/game-plan cards expose weekly tendencies, but I did not see a clear on-screen statement like "clubs shifted toward X because X won last year" that could be verified from recaps alone.
- Relegation/promotion movement was visible and consistent in the season recaps checked.

## Console / Server Errors

- Initial page load: zero browser console errors.
- Repeated browser console checks during the run returned zero errors, including final check after both career paths.
- Server stderr tail showed uvicorn startup only; request log tail showed normal 200 responses for the playtest flow.

## Save Cleanup

- Purged throwaway saves after the run:
  - `Climb Era Playtest 5 D3`
  - `Climb Era Playtest 5 Takeover`
- Verification: `/api/saves` returned no `Climb Era Playtest 5*` matches after cleanup.
