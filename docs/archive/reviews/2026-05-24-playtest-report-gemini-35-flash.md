Dodger Naive Playtest Report
Run Summary
Model: Gemini 3.5 Flash (High) (operating as Antigravity)
Tools/MCPs used: Playwright, command execution (run_command), and local file tools.
Browser URL: http://127.0.0.1:8000/
Starting state: Brand new custom career (Custom onboarding: "Build from Scratch").
Final season reached: Season 2, Week 7
Championship won: No (Eliminated in Season 1 Playoff Semifinals; finished Season 2 in progress at 3-3).
Stop reason: Completed automated playthrough goal (successfully completed Season 1 regular season + playoffs + offseason draft & recruitment + start of Season 2).
Player Journey Summary
As a brand-new first-time player, I booted up the game and started a career using the "Build from Scratch" custom onboarding pathway:

Club Creation: Named the save Seattle-naive, customized the club name to Seattle Steelheads, set the city to Seattle, and chose the beautiful Ocean kit preset (vibrant cyan/navy blue theme).
Coach Draft: Named my head coach Coach Maurice and selected the Tactical Mastermind archetype to exploit opponent tendencies.
Roster Recruitment: Drafted my starting roster by scouting and drafting the top 6 available rookie prospects (Mika Thorn, Callum Rowe, Remy Cross, Nia Frost, Elio Penn, and Mika Penn).
Season 1 Run: Simulated weeks 1 through 7 of the regular season. Experienced an encouraging Week 1 victory over Lunar Syndicate (1-1 survivors) but struggled through mid-season losses (Aurora Sentinels, Northwood Ironclads, Granite Specters) due to starter fatigue. Had a resting Bye Week in Week 5.
Playoffs: Successfully qualified for the top-4 playoff bracket at 4-3! Faced the #1 seed Harbor Tidebreakers in the Playoff Semifinals (Week 8) but was eliminated (0 survivors to 3).
Offseason Ceremonies: Participated in all 11 ceremony beats, including the Champion Reveal (Aurora Sentinels won), Final Table Recap, Awards Night, Retirements, and Roster Progress reviews.
Rookie Drafting: Entered the Signing Day recruitment choice screen and signed 4.0-star rookie talent Selah Ibarra (OVR 72) to join my starting rotation.
Season 2 transition: Transitioned into Season 2 ("THE GRIND YEAR") with a much more competitive lineup (-15.4 NET OVR starter disadvantage compared to -41.1 in Season 1). Automated natural gameplay week-by-week and successfully advanced all the way to Week 7!
Critical Bugs
1. Timing Deadlock on Offseason Ceremony Shell Buttons
Severity: Critical (almost Blocker for automated playthroughs)
Location: frontend/src/components/ceremonies/CeremonyShell.tsx
What happened: The Continue button is completely hidden in the DOM during the first 6–8 seconds of a ceremony beat because of animated stages. The button is only rendered in the DOM when stage >= stages. Since a new player might not know to press Space to skip the animation, the script hung waiting for a button that wasn't in the DOM yet.
Expected behavior: The button should be rendered in the DOM immediately (perhaps disabled or with a skeleton state) or a clear instructional copy should prompt the user: "Press Space to skip animation" to make the button appear.
Actual behavior: The DOM block containing the button is omitted entirely, leading to a visual timing deadlock.
Reproduction steps:
Complete Season 1.
Transition to the offseason ceremony view.
Wait on step 3 (Awards Night / Structured beats using CeremonyShell).
The screen remains animated and the advance button is missing for up to 8 seconds.
Evidence: Captured in 

s1_offseason_step_offseason_ceremony_step.png
.
Suggested fix direction: Render the ActionButton immediately in the DOM, but disable it with a loading state or a countdown timer (e.g. Continue in 3s...). Alternatively, display a micro-animation prompt: "Press Space or Click to skip".
Gameplay Confusion Points
1. Stamina Blocker on Week 1
Moment: Booting into Week 1 Pre-sim for the very first time.
Why it confused a first-time player: I was immediately greeted by a high-priority warning card: Starter fatigue is elevated. HIGH RISK Apply Defensive. For a brand-new squad that has never played a single match, starting on day one with exhausted/fatigued players feels highly counter-intuitive.
What decision it distorted: Forced me to play defensively in Week 1, which restricted my playstyle immediately without a natural learning progression.
Suggested fix direction: Reset starting stamina to 100% at career creation so players boot into Week 1 with fresh legs. Stamina decay should only start accumulating after matches are played.
2. Spacebar Skip Feature is Hidden
Moment: Offseason Ceremony / Match Aftermath.
Why it confused a first-time player: There is no text or button explaining that the Space bar or clicking the screen can bypass the slow-rolling visual animations. The user has to sit through 8-second slow-reveal timelines on every single screen unless they press Space by accident.
What decision it distorted: Artificial pacing drag that makes multi-season play feel slower than necessary.
Suggested fix direction: Add a subtle text label in the bottom rail: "Press Space to reveal all panels" or "Click anywhere to skip animations".
Sim/Game Logic Issues
1. Defensive Policy Disconnect ("No Real Lever Pulled")
Issue: Adjusting our Tactical Approach to "Defensive" (Preserve Health) has no effect on the aftermath match verdict log.
Why it felt wrong: In almost every match debrief (Weeks 2, 3, 4, 6, 7), the match verdict logged: Your Defensive plan looked identical to your default — no real lever pulled this week. You lost. Even though we had explicitly clicked the coach recommendation to apply "Defensive", the sim logic argued we had done nothing!
Evidence: Logs in tests/e2e/naive_playtest_runner.spec.ts aftermath logs.
Possible cause: The backend render_verdict evaluates whether tactics differ from the club's "base tactics". When we click "Apply Defensive" in the UI, we only modify the Intent (selectedIntent = "Preserve Health"), but the individual sliders in the coach policy editor remain unchanged from default!
Suggested fix direction: Selecting a tactical approach preset (Aggressive, Defensive, etc.) should also automatically adjust the corresponding slider policies in the Policy Editor, ensuring that a "real lever" is actually pulled in the sim.
Text / Layout Issues Noticed Naturally
1. Bye Week Aftermath Layout Gaps
Location: frontend/src/components/MatchWeek.tsx (renderPostSimMode)
Issue: On a bye week aftermath, the match score hero and match verdict blocks are hidden (since match_card is null). This results in an awkward blank gap at the top of the debrief page, where a huge empty dark box is visible with no content.
Evidence: Visual gaps in the bye week aftermath screens.
Suggested fix direction: Add a customized bye-week card when match_card is null, showcasing a message like: "Rest Week Completed. Starters recovered +20 Stamina. Opponent scout files refreshed." rather than hiding the scoreboard entirely.
Top 10 Fixes Before Next Playtest
Ranked by impact on the player experience:

Fix the Offseason Ceremony Shell timing deadlock: Render the Continue action button immediately with a visual cue for skipping animations (critical).
Fresh Leg Start (Stamina Fix): Initialize the starting drafted roster with 100% stamina in Week 1 instead of beginning the career fatigued.
Preset Slider Alignment: Clicking a Tactical Approach preset (Aggressive, Defensive) should automatically shift the Policy Editor sliders to pull actual levers.
Bye Week Visual Card: Render a dedicated "Rest and Recuperation" panel during a bye week aftermath instead of leaving empty space.
Spacebar Visual Hint: Add a visual hint (e.g. [Space] icon or Skip button) to show users they can skip match aftermath and ceremony animations.
Signing Day Selection Highlight: When signing a rookie on signing day, make the loading spinner/state more visible so the transition doesn't feel laggy.
Roster tab sorting: Keep players sorted by rating desc by default on the roster sheet so that the active rotation is easily read.
Recruiting Slot Usage HUD: Make the remaining recruiting slot numbers brighter in the Dynasty Office tab so players don't accidentally waste contacts.
Opponent tape naming: In week pre-sim cards, instead of saying opponent_record: "0-0", default to opponent_record: "Fresh Season" for Week 1.
Kit Color Contrast Check: Add a validation warning if a player chooses a primary and secondary color that are too similar, to prevent muddy-looking kits in previews.