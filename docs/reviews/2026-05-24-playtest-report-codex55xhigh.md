Dodger Naive Playtest Report
Run Summary
Model: GPT-5 Codex
Tools/MCPs used: Codex in-app Browser with Playwright-style control, screenshots, console logs, local server log for crash evidence. No Antigravity/Chrome DevTools/BrowserMCP tool was available.
Browser URL: http://127.0.0.1:8000
Starting state: Existing saves were present; I used New Game → Build from Scratch.
Final season reached: Season 1, Week 8 Playoff Semifinal.
Championship won: No
Stop reason: Repeatable blocker when simulating the playoff semifinal.
Player Journey Summary
Created Rain City Breakers from scratch with coach Casey Park, chose Recruiting Legend, and selected the best visible NOW/PEAK roster options. I followed staff Defensive recommendations early, lost Weeks 1-2, tried Control in Week 3 and lost again, then checked roster/office options. After spending recruiting slots once, they never reset. Switching to Aggressive + Tactical drills produced wins in Weeks 4, 6, and 7, moving from 0-3 to playoff seed #3. The playoff semifinal could not be completed because simulating it repeatedly produced an Internal Server Error.

Critical Bugs
Title: Playoff semifinal simulation hard-blocks championship path

Severity: Blocker

Location: Command Center, Season 1 Week 8 Playoff Semifinal

What happened: Clicking Simulate Week returned Command center unavailable / Internal Server Error.

Expected behavior: Show semifinal result, advance to championship if won or end playoff run if lost.

Actual behavior: The semifinal does not advance. Reload returns to the same unsimulated semifinal. Retried Aggressive and Defensive plans; both failed.

Reproduction steps: Start a new club, qualify for playoffs, reach Week 8 semifinal, lock any plan, click Simulate Week.

Evidence: Playoff blocker

Suggested fix direction: Fix playoff advancement so the final is not created until both semifinal winners are recorded. Server log showed ValueError: Both semifinal winners are required.

Title: Postseason result says Winner: Draw for a 1-0 semifinal

Severity: Critical

Location: Standings → Postseason / Recent Results

What happened: Semifinal 1 displayed Solstice Flare 1-0 Northwood Ironclads, but Recent Results said Winner: Draw.

Expected behavior: Winner should be Solstice Flare.

Actual behavior: The winner label is wrong and likely contributes to the missing-winner semifinal crash.

Reproduction steps: Reach playoffs, open Standings after semifinal automation.

Evidence: Wrong semifinal winner

Suggested fix direction: Ensure playoff winner display and bracket winner persistence use the final survivor score consistently.

Title: Weekly recruiting slots never reset

Severity: Major

Location: Dynasty Office, Weeks 4-5

What happened: After spending Week 3 slots, Week 5 still showed Scout 3/3, Contact 5/5, Visit 1/1, all disabled.

Expected behavior: Weekly slots reset each week.

Actual behavior: Recruiting was locked for the rest of the season.

Reproduction steps: Spend all Dynasty Office recruiting slots, advance multiple weeks, return to Dynasty Office.

Evidence: Recruiting not reset

Suggested fix direction: Reset recruiting counters on week advancement, or rename/copy them if they are intended to be season-limited.

Gameplay Confusion Points
Moment: Applying Defensive still left Scout Read saying Adjustment advised → Adjust to Defensive.

Why it confused a first-time player: I had already done the recommended action, but the UI still told me to do it.

What decision it blocked or distorted: Made it unclear whether my plan had actually changed.

Suggested fix direction: After recommendation is applied, change the card to Recommendation applied.

Moment: Briar Mercer is a mismatched Captain warning persisted all season.

Why it confused a first-time player: There was no visible way to change captain or understand the required archetype.

What decision it blocked or distorted: I could not fix an apparently important readiness warning.

Suggested fix direction: Add a captain selector or link the warning to the roster action needed.

Moment: Standings said playoff cutoff is Top 4, but Command Center repeatedly said “outside the top three.”

Why it confused a first-time player: I did not know whether #4 or #3 was the target.

What decision it blocked or distorted: Changed how desperate the final weeks felt.

Suggested fix direction: Use one playoff cutoff definition everywhere.

Moment: Training choices produced No growth logged this week every week.

Why it confused a first-time player: I picked Tactical/Conditioning expecting visible development or recovery feedback.

What decision it blocked or distorted: Training felt cosmetic.

Suggested fix direction: Show when training has delayed effects, small stat movement, or no effect due to season phase.

Sim/Game Logic Issues
Issue: Several comeback summaries said the team clawed back with 0 catches.

Why it felt wrong: The text claims a comeback trigger but names no mechanism.

Evidence: Week 2 and Week 4 result screenshots.

Possible cause: Narrative template inserts catch count even when the comeback came from eliminations/misses.

Suggested fix direction: Branch the recap by actual comeback driver.

Issue: Week 3 tactical read included Avery Bishop lets it fly at -. It misses wide.

Why it felt wrong: Missing target name breaks replay credibility.

Evidence: Missing target text

Possible cause: Null/empty target display name in throw event narration.

Suggested fix direction: Fallback to opponent/team target text or suppress target-specific sentence.

Issue: Strong starter edge did not translate intelligibly early.

Why it felt wrong: +20, +15.5, +14.9 net OVR led to three straight shutout losses without enough explanation.

Evidence: Week 1-3 screenshots.

Possible cause: Fatigue/captain mismatch is overpowering OVR but not explained as the main cause.

Suggested fix direction: Make the result explanation quantify why OVR edge failed.

Text / Layout Issues Noticed Naturally
Location: Command Center recaps
Issue: Some sentences run together, e.g. This WeekA chance...
Evidence: Week planning screenshots.
Suggested fix direction: Add spacing between label and body copy.
Top 10 Fixes Before Next Playtest
Fix the playoff semifinal blocker.
Fix playoff winner persistence/display, especially Winner: Draw on non-draw semifinal scores.
Reset weekly recruiting slots on week advancement.
Make applied staff recommendations stop displaying as still-needed adjustments.
Add a visible way to resolve captain mismatch warnings.
Align playoff cutoff language between Standings and Command Center.
Fix missing target names in replay/result narration.
Make training effects visible, even if only “no immediate effect; offseason impact expected.”
Improve result explanations when a high-OVR favorite loses repeatedly.
Fix recap templates that say a team clawed back with 0 catches.