Dodger Playthrough Report
Playthrough Summary
New club: Aurora Sentinels ("Caveman Dynasty"), Generic ruleset, recommended path
Played S1-S10 fully via UI (browser only, no backend touch)
Championships won: 1 of 2 target (S4 only - upset run from 2-3-0 #4 seed)
Career: ~30W-28L regular season, 1 title, 0 in S5/S6/S7/S8/S9/S10 despite multiple playoff appearances
Progress Milestones
M1: New career flow (ruleset select → club pick → save name → start) - smooth
M2: First match completion (S1 W1 vs Solstice Flare, won 1-0)
M3: First offseason loop (signing day, schedule reveal, start new season)
M4: First playoff loss (S1 final 0-1 vs Solstice Flare)
M5: First championship (S4, beat Solstice 5-0 in final, came from 2-3-0 reg season)
M6: S5 dominant regular season (4-0-1 #1 seed) - upset loss in semi
M7: Reached 10 seasons of stable play with no save corruption, no crashes
Bugs / Issues
S1 — Trust-breaking
S1-A. Standings page during offseason still shows live-race language. After S10 finished and champion was Harbor Tidebreakers, the Standings page header reads:

"OUR RANK 3 OF 6 · ABOVE LINE THROUGH W07 · NEXT RESULT NEEDS WIN NEXT → HOLD TOP 4 · You are on the line with 2 points of breathing room over the bubble."

We are in offseason. Season is over. The cushion / "win next" language is stale. Confirmed across S1, S5, S10 offseasons.
Repro: finish any season, click STANDINGS sidebar after the final.

S1-B. Header season counter lags by one during schedule-reveal ceremony. At end of S6 offseason, page body says "SEASON 2032 · SCHEDULE REVEAL" (this would be S7), but the persistent header banner still says "SEASON 6 -- WEEK 00". You click START NEW SEASON and only then does header flip to S7. Felt like a stale render across the offseason ceremonies.

S1-C. Header WEEK shows "00" throughout offseason. "SEASON N -- WEEK 00" is the persistent label across 7+ offseason beats (final table → champion ceremony → awards → development → recruiting → signing → schedule reveal). No indication of which beat you're on, and "Week 00" is semantically wrong for a post-season ceremony.

S2 — Major UX / visual
S2-A. "BANNER COUNT 21 TITLES" vs "TITLES 1" right next to each other in Dynasty Office → History → My Program. Reads as contradictory. Likely 21 is league-wide and 1 is ours, but labels do not disambiguate.

S2-B. Multiple instances of missing space between adjacent text blocks (text overflow / concatenation):

"Noor SinclairFREE AGENT", "Jules BloomFREE AGENT", and ~12 other free-agent rows on Signing Day - the FA tag is jammed against the name
"SEASON STANDINGSLIVE SEASON TABLE" on Standings page (Live Season Table title runs into prior label)
"This WeekA chance to set the tone..." in opponent file
"WatchLux Stone carries the highest ceiling..." in watch-line
Likely all the same root cause: missing white-space or inline-block gap between a label and content.
S2-C. Dynasty Office credibility tier breakdown labels concatenated:

"0130 career command-history wins and 28 losses."
"020 youth-development command weeks across your career."
"03Club prestige score 0."

These appear to be numbered items (01., 02., 03.) where the index and the first number of the body have collapsed (e.g. "01" + "30 career command-history wins" → "0130 ..."). Real shame, this is in the most-trafficked status block.

S2-D. Two recruiting systems with no cross-reference. Dynasty Office has a "RECRUIT BOARD" with SCOUT / CONTACT / VISIT actions and a Tier-A credibility tracker. Offseason Signing Day shows a completely separate prospect list with "SCOUTED" pills and SIGN buttons. As a new player I never realized the weekly Dynasty Office board existed - I only used Signing Day. Across 10 seasons the Tier-A meter showed "86 / 75 TOWARD TIER B" (over capacity, not advancing). Either the systems should reference each other or the weekly board needs onboarding.

S2-E. Awards Night ceremony needs ~8+ SKIP/CONTINUE clicks per season. Each award appears to be its own confirm screen even when "Press Space or click anywhere to skip animation" is shown. By S10 this is the dominant click cost of the offseason.

S2-F. Tier-A credibility meter reads "86 / 75 TOWARD TIER B". Numerator exceeds denominator yet tier hasn't advanced. Either the gating value is hidden or the meter is wrong.

S3 — Polish
S3-A. "You won despite Aggressive" copy after a clean 1-0 shutout (S1 W1). Reads as if my plan was wrong when I won and matched their catches. Confusing tone for a first-game win.

S3-B. S4 final summary: "Your Aggressive plan was identical to Base Tactics this week. Default plan held the line — banking it." The system is telling me my plan was effectively the default - but this fires after I locked an Aggressive plan. Either the engine treated Aggressive as default for this matchup (in which case it should warn before lock) or the message is misleading.

S3-C. "Lux Stone and Dex Voss were the last two left" framing for a 1-0 shutout (S1 W1) - ambiguous whether "last two left" means the duel ending or two survivors. Could be clearer.

Severity scale annotations
S0: none observed
S1: A, B, C
S2: A, B, C, D, E, F
S3: A, B, C
S4 (wishlist): cumulative title display on standings; clearer playoff bracket header during offseason
Replay / Result / Standings Cross-checks
Match results match standings. Spot-checked S1 (Aurora 3-0 vs Granite semi appears both in postseason bracket and W06 league wire). Consistent.
Playoff structure is consistent once understood: if you make playoffs you play your semi / final live as Wk6/Wk7; if eliminated, remaining games auto-sim and appear in the post-season ceremony screen. Initially this felt like a bug ("playoffs not playable in S2/S3") but tracking across S4 (won everything live) and S5 (lost semi live, final auto-simmed) confirmed the rule. Worth noting as a UX clarification target — no banner explains "you've been eliminated, the rest will be presented."
What felt fun
The S4 comeback arc (2-3-0 reg → champion) was a genuine highlight - the storyline that you can sneak in as a low seed and win it all felt rewarding.
The Court Read / Key Threat / Counter Read trio on Command Center is good at-a-glance info.
The Postgame Report "★ WINNER" / "5 moments" framing is tight.
What felt broken trust-wise
Same record (3-2-0) shared by 4 of 6 teams in S10 - tiebreakers are opaque to a new player, and clubs were ranked by survivor differential without a clear in-UI explanation.
S5 dominance (4-0-1, +13 diff) lost semi 0-1 to a 2-3-0 #4 seed - sim variance feels too high for a top seed to have such thin survival edge. Could be intended, but the result page does not explain why the underdog won.
Demo-killing issues
None. No crashes, no save corruption, no soft-locks across 10 seasons. The visible-but-cosmetic bugs (S2-B concatenations, S2-C numbered list, S1-A stale standings copy) are what a first-time demo viewer will fixate on - those are the priority fixes before showing this to anyone.

Final state
10 seasons complete, save "Caveman Dynasty", Aurora Sentinels, 1 championship (S4), 1 MVP (Lux Stone, S4), career 30W-28L. Did not achieve the 2-championship target through normal UI play within the playtest window.