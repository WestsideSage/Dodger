# Product Coherence Audit — Dodgeball Manager
*Senior game designer / product designer / UX strategist review — post Codex UI/UX polish pass*
*Audit date: 2026-05-15*

---

## A. Executive Verdict

**Does the app currently feel like a real management sim?**
Conditionally yes — more than most indie sims at this stage. The bones are correct: there is a loop, there are decisions, there is data. The aesthetic is excellent. But the app still has a critical gap: **it shows the player information and outcomes without completing the narrative**. A real management sim is a story machine — every match has a story, every player has an arc, every week moves the season forward in a way the player *feels*. Right now, the app *reports* things but doesn't *tell* them.

**The biggest thing holding it back:**
The app does not reliably close the loop between "decision made" → "match happened" → "here's what your decision caused." The player can pick "Aggressive," simulate, win or lose, and move to the next week without a clear sense of whether their plan worked, why it worked, and who they should care about going forward. The connection between *input* (tactical approach, training order, stamina management) and *outcome* (match result, player growth, standings) is technically present in the data but not communicated back clearly enough to feel real.

**What is already working:**
- The Command Center pre-sim flow (checklist → plan lock → simulate) is genuinely good. The two-step "confirm then run" UX is smart and sports-like.
- The animated post-sim reveal (headline → score → story → fallout) is a strong game-feel feature. It creates anticipation.
- The Match Replay is a standout feature — animated SVG court, play-by-play, key plays, stats panel. It already feels like a real broadcast product.
- The Offseason ceremony sequence is the most emotionally resonant part of the app. Awards Night, Graduation, Signing Day, and Schedule Reveal are all doing their jobs.
- The visual design system is consistent and professional. The dark theme, monospaced data fonts, and color-coded results are excellent.

**What should absolutely not be changed:**
- The Command Center two-step lock/simulate flow.
- The post-sim animated reveal sequence. It's the best moment in the game.
- The Match Replay court view. It's technically impressive and creates authentic sports texture.
- The offseason ceremony shell structure. It deserves more content, not a redesign.
- The global four-tab navigation (Command / Roster / Dynasty / Standings). It's the right architecture.

---

## B. Player Loop Diagnosis

### The loop as the app currently communicates it

1. Open the app → land on Command Center with a checklist of 5 items.
2. Select a tactical approach (Aggressive / Balanced / Control / Defensive) — one of four buttons.
3. Check the readiness list, see that training and rotation are already set.
4. Lock the plan. Click "Simulate Match."
5. A transition animation plays. Watch a headline, a score, a story grid, a fallout section.
6. Click "Advance Week" or "View Replay." Go back to step 1.
7. Occasionally visit Roster (data table), Dynasty (recruit board + history), Standings (table).
8. After many weeks: offseason ceremonies, signing, new season.

**What's missing from this loop:**
- No clear signal about *what changed* from last week that should affect this week's decision.
- No meaningful variation in the pre-sim decisions — the training order lives in a hidden modal under "Program Settings" in Dynasty; most players never find it. The tactical approach is the only real pre-sim lever that's surfaced.
- No player or team development arc that feels *authored* — player growth happens but is listed as "+1 accuracy" in the fallout; there is no character or trajectory.
- No season narrative — at week 6 of 12, the player should know where they stand, what's at stake, and who the season villain is. The Standings tab shows this factually but not dramatically.

### The ideal loop

1. **Start of week**: Command Center immediately tells you *what matters*. Not just the opponent — your form, a brewing player story, what your last decision produced.
2. **Decisions**: At minimum two consequential choices: tactical approach AND a training emphasis. Both should feel like trade-offs.
3. **Simulate**: The match plays. Something happens that you didn't expect at least 30% of the time.
4. **Post-match**: A clear "here's what your plan caused" message, plus a "here's who stepped up / stepped back" read with your actual players named.
5. **Consequence scan**: One piece of information you need to act on before next week (fatigue, a player about to break out, a standings threat).
6. **Return**: Knowing what you want to do differently — or feeling good about what you did.

---

## C. Screen-by-Screen Critique

### 1. Save Menu / New Game

**Current purpose:** Load or create a career. Two paths: Take Over a Program or Build from Scratch.

**Actual player value:** High functional value. The three-step Build path (Identity → Coach → Roster) is better than most indie sims offer at game start.

**Main confusion:** "Build from Scratch" implies more creative control than actually exists. The city, colors, and coach backstory are entered but seem to have little visible impact on anything in-game. The player may feel they made choices that didn't matter.

**Biggest improvement opportunity:** After creating the save, show a brief "Your Program" summary card — club name, coach name, season year, a one-line prediction — before entering the game. This closes the identity loop and makes the creation feel real.

**Recommendation: Keep.** Minor enhancement — post-creation welcome state.

---

### 2. Command Center (Pre-Sim: PreSimDashboard)

**Current purpose:** Weekly planning hub. Opponent intel, tactical approach selection, readiness checklist, and the simulate trigger.

**Actual player value:** High — this is the most content-dense and well-structured screen in the game.

**Main confusion:**
- The page has *two* "Confirm Plan" / "Lock Plan" buttons (one at top in the Next Action panel, one at bottom of the Control Tower). This creates visual redundancy and mild confusion about which one to press.
- "Tactical Profile" (Target Stars, Catch Bias, Risk, Tempo percentages) is displayed but not explained. What does 73% Target Stars mean? What changes when I pick Aggressive vs. Balanced? The connection between approach selection and these numbers isn't bridged for the player.
- "Command Intent Selected" is listed as a readiness checklist item that is always green, because an intent is always selected. This wastes a checklist slot on a non-decision.
- The "Win Condition" in Opponent Intel (`latestDashboard?.lanes?.[1]?.summary`) is pulling from a *previous match's* dashboard lane. A first-time player sees this card and thinks it's about today's game, but it's stale data.
- `Plan Fit: Current approach is aggressive.` followed by `Review: Compare the current approach against staff recommendations.` is the same information stated twice in different tones. One is green, one is orange. This is confusing.
- The "Tactical Profile" stats (percentages) are from `plan.tactics` (CoachPolicy) — a fixed property of the selected approach, not personalized feedback. They feel like detail for detail's sake.

**What information is overemphasized:** The two duplicate lock buttons; the tactics percentages; the "Plan Fit" duplicate logic.

**What information is underemphasized:** The season context (what week is this of how many? are we in playoff contention?). The consequence of last week (did the previous approach work? were there fatigued players because of it?).

**Recommendation: Revise.** Remove one of the two lock buttons. Replace the "Command Intent Selected" readiness item with something more dynamic. Add a "Last Week" one-liner above the Opponent Intel panel.

---

### 3. Command Center (Post-Sim: MatchWeek aftermath view)

**Current purpose:** Post-match reveal — headline, score, story grid (replay timeline + key players + tactical read), fallout grid (growth, standings, recruits), action bar.

**Actual player value:** Very high. The reveal sequence is the strongest moment in the game.

**Main confusion:**
- The "Tactical Read" card (`TacticalSummaryCard`) shows either a turning point string or a lane summary. The fallback is "The staff report is still assembling the tactical read for this match." — this appears when replay data is loading, and it looks like an error.
- The "Key Performers" panel shows performers from both teams. A first-time player often has to look at the club name label (in small gray text) to figure out which performers are theirs.
- The `ReplayTimeline` (evidence lanes) and `TacticalSummaryCard` together cover essentially the same content — "what happened tactically." The duplication dilutes both.
- The fallout section title "Front office report" has weak energy. Nothing about a post-match situation feels like a "front office report."
- The "Player Development" fallout items show `+1 accuracy`, `+0 power`, etc. Seeing "+0" changes (which can appear) feels broken and anticlimactic.

**Biggest improvement opportunity:** Make it immediately obvious which players are *yours* in the Key Performers panel. Add a one-sentence "Did your plan work?" verdict at the top of the story grid, tied to the approach you chose.

**Recommendation: Revise.** Tighten the story grid. Replace "Front office report" language. Add "Your plan" verdict.

---

### 4. Match Replay (MatchReplay)

**Current purpose:** Full match playback — animated SVG court, event-by-event navigation, play-by-play, key plays, match report.

**Actual player value:** Extremely high — this is the game's showcase feature.

**Main confusion:**
- Accessed via a separate button from the aftermath screen ("View Replay"), but it's the most compelling content in the game. Many players may skip it because the aftermath already showed a result.
- The "CONTINUE ->" button at the bottom of the replay feels unfinished compared to the rest of the polish. It reads like a placeholder.
- The play-by-play panel shows raw `TICK {n}` timestamps. "Tick" is an engine concept; a player should see something like "Play #12" or "Round 4."
- The "Stats" tab in the sidebar is labeled "REPORT" in the UI. The tab bar says PLAY-BY-PLAY | KEY PLAYS | REPORT. The label "REPORT" could be "MATCH STATS" or "BOX SCORE" to feel more sports-like.
- There is no connection from the replay back to the roster — if a player sees that "Marcus Chen" dominated, there is no "go to his roster card" affordance.

**Recommendation: Keep.** Light copy refinements. Add a "Back to Results" label with sports language rather than "CONTINUE ->."

---

### 5. Roster (Roster)

**Current purpose:** View all players, their ratings, potential tier, OVR trend, and role. Compact/theater toggle.

**Actual player value:** High for information — moderate for decision support.

**Main confusion:**
- The "Trend: UP" stat chip in the header is hardcoded. Every team's roster always trends "UP." A first-time player may notice this eventually and it will feel dishonest.
- The `DevFocusChip` sits at the top of the roster page but is labeled "Dev Focus: BALANCED" (in monospace uppercase). This is a plan-level setting that affects training, and it lives here inside a dropdown buried in a header stat area. Most players will never find it or understand why it's on the Roster page.
- The OVR sparkline (`Sparkline`) is visually very small and has no scale. A player can't tell if a player is improving by 1 point or 5 points from the sparkline alone.
- The "Potential" column shows a badge (e.g. "Elite") with a scouting confidence number. The scouting confidence is opaque — what is 0.8 confidence? What changes it?
- The column "Status" shows a role badge (Thrower, Catcher, etc.) — but "Status" implies health or availability, not archetype. The column is mislabeled.
- There is no way to see which players need rest (low stamina) or which players are currently injured from the roster page alone.

**Biggest improvement opportunity:** Move Dev Focus to Command Center pre-sim settings where it belongs. Rename "Status" to "Role." Replace the hardcoded Trend chip with something real or remove it.

**Recommendation: Revise.** Label corrections, Dev Focus migration, stamina callout column.

---

### 6. Dynasty Office (DynastyOffice)

**Current purpose:** Recruit board and program history. Also contains staff management and hidden department orders via "Program Settings" modal.

**Actual player value:** The recruit board has value. The "History" sub-tab has archival value. The staff room has almost no current player value.

**Main confusion:**
- The page title is "Dynasty Office" but the default sub-tab is "Recruit" — so a player opening this screen sees the recruit board, not dynasty content. The tab label "History" undersells what's there (banner shelves, alumni lineage, milestone trees are interesting).
- "Program Credibility" shows `Tier B, Score 47, + 3 evidence bullets`. The grade is meaningful but the score number (47) has no range or scale. Is this out of 100? Out of 200?
- The Staff Room (`dynasty-staff-room`) shows a list of staff names with department labels, and a single "Staff Market" button. There is no indication of what each staff member actually does, what their rating affects, or how to improve the department. The effect is invisible.
- The "Program Settings" modal (department orders) is hidden behind a small gray text button at the top right of the page. This is arguably the second most important weekly decision in the game (after tactical approach), and most players will never find it.
- Recruiting budget (Scout 0/2, Contact 1/3, Visit 0/1) is functional but doesn't communicate urgency. If I've used all my scout slots, so what? Why does it matter?
- Promise options shown on prospect cards (`promise_options: string[]`) are not explained. What's the difference between "playing time" and "role promise"? What happens when I break one?
- **ProspectCard's Scout / Contact / Visit actions are unexplained.** The three action buttons on each prospect card spend from a weekly budget, but the card gives no indication of what each verb actually does or produces. "Scout" presumably reveals hidden OVR data. "Contact" presumably builds interest. "Visit" presumably locks pursuit priority. None of this is communicated. A player must infer what they're spending toward — and the error feedback on budget exhaustion is an unpolished `alert()` dialog.

**What information is overemphasized:** Staff room (names only, no context). Raw credibility score.

**What information is underemphasized:** What your department orders do. What your staff ratings affect. Why credibility matters to recruiting.

**Recommendation: Revise substantially.** Promote "Program Settings" department orders to the Command Center. Give the Staff Room a purpose statement per hire. Add a credibility-to-recruiting-outcome explanation.

---

### 7. Standings (Standings / LeagueContext)

**Current purpose:** League table showing W/L/T, points, win rate, games back, elimination differential, and current approach.

**Actual player value:** Moderate. The data is accurate and readable.

**Main confusion:**
- "Elimination Differential" is the most sports-specific column and it has the most generic column header. A first-time player has no idea what "Elim Differential" means. Is this total players eliminated across all matches? This needs a tooltip or a brief explainer.
- The "Approach" column (`latest_approach`) shows each team's current tactical approach. This is a cool idea — it implies the league has coaches making decisions too. But it reads as orphaned data without context: why do I care if the Northwood Wreckers are running "Balanced maintenance"?
- Clicking a team row navigates to `#?tab=dynasty&subtab=history&team_id=...` — but the navigation is silent. The player doesn't know the row is clickable.
- The recent matches sidebar shows match summaries but they're not connected to the standings. After seeing the table, a player naturally wants to know: "what happened to the teams above me this week?" The sidebar answers this but is visually disconnected.
- The page shows no indicator of playoff position, playoff format, or how many weeks remain. A player can be at #3 with 4 weeks left and have no idea if they're safe or if they need to win 3 of 4 to qualify.

**Biggest improvement opportunity:** Add a "X games remaining" note and a playoff position callout above the table. Add a hover/tooltip for "Elimination Differential." Make row clickability more obvious.

**Recommendation: Revise.** Season context, tooltip explanations, visual clickability cue.

---

### 8. Offseason (Offseason + Ceremonies)

**Current purpose:** Sequential story beats — champion reveal, standings recap, awards night, retirements, development, rookie class preview, recruitment, schedule reveal.

**Actual player value:** Very high. This is the most emotionally resonant section of the app.

**Main confusion:**
- The generic fallback offseason beat template (for `records_ratified` and `hof_induction`) shows `<beat.key.replaceAll('_', ' ')>` as the kicker — this renders as "records ratified" in plain lowercase. It's a visible seam.
- "Offseason Beat 3/9" as the eyebrow is accurate but uninspiring. Players don't care they're on beat 3 of 9 — they want to know what's happening.
- The Offseason progress dot row (the little step indicators) is a good UX pattern but the dots are very small and easy to miss.
- The `records_ratified` and `hof_induction` beats use only `beat.body` text with no structured UI — they render as plain text paragraphs. This is the weakest moment in an otherwise strong ceremony sequence.
- The Development ceremony (`DevelopmentResults`) shows player OVR deltas. This is good data but the timing is odd — it happens before players are on the roster page for review.
- **The `recruitment` beat is a player agency hole.** When `can_recruit` is true, the player sees a single "Sign Best Rookie" button — the game auto-selects the best available prospect and signs them. There is no player choice about *who* to sign. In a management sim, roster construction is one of the core decisions. Collapsing it into one button removes the decision entirely.

**Recommendation: Keep, with targeted enhancements.** Replace the generic beat fallback with structured cards. Replace the "Sign Best Rookie" auto-pick with a prospect selection panel (show top 3 available; let the player choose). The ceremony sequence architecture is sound.

---

## D. Top 10 Product Coherence Fixes

### Fix 1: Add a "Did Your Plan Work?" Verdict

**Problem:** After simulating a match, the player receives a headline, a score, and a story grid — but no direct connection between their tactical approach choice and the outcome.

**Why it matters:** Without this, the tactical approach selection feels cosmetic. The player has no reason to change it next week.

**Recommended change:** Add a single verdict line immediately below the score hero, before the story grid. Pull from approach + win/loss + the top evidence lane. Example:

> *Your Aggressive approach paid off — the pressure forced 4 early eliminations before the Wreckers found their footing.* [Win]

> *The Control approach limited risk but couldn't close out a well-organized Harbor defense.* [Loss]

**Implementation complexity:** Low — requires a backend sentence generator for a few approach/result combos, or a simple front-end template using existing data (`selectedIntent` + `result` + `lanes[0].summary`).
**Risk:** Low.

---

### Fix 2: Move Department Orders to Command Center Pre-Sim

**Problem:** "Program Settings" (department orders for tactics, training, conditioning, etc.) is hidden in the Dynasty Office behind a small button. This is the second most impactful weekly decision in the game, and it's invisible.

**Why it matters:** Players can't engage with a decision they don't know exists. Department orders currently feel like a developer debug panel.

**Recommended change:** Add a collapsible "Weekly Orders" section to the Command Center pre-sim, below the Game Plan section. Show 2-3 of the most impactful orders (Training, Conditioning, Scouting) with current values and a quick-change UI. Remove the redundant Dynasty Office modal.

**Implementation complexity:** Medium — requires moving/duplicating the department orders UI into the Command Center, keeping API calls identical.
**Risk:** Low.

---

### Fix 3: Eliminate the Duplicate Lock Button

**Problem:** The Command Center pre-sim has two "Lock Weekly Plan" / "Confirm Plan" buttons — one at the top (Next Action panel) and one at the bottom of the Control Tower. Both do the same thing.

**Why it matters:** Redundancy signals design confusion. A first-time player may not realize they're identical and wonder which one "counts."

**Recommended change:** Keep only the Control Tower lock button. Transform the top Next Action panel into a status indicator only (showing the current step, a description, and a "jump to checklist" link), not an action target.

**Implementation complexity:** Low — remove one button, update the top panel to read-only.
**Risk:** Low.

---

### Fix 4: Add "Last Week" Context to Command Center

**Problem:** Every week the Command Center opens cold. There is no line telling the player what happened last week and whether their approach succeeded.

**Why it matters:** Without it, the game has no week-to-week narrative. Every week feels like the first week.

**Recommended change:** Add a one-line "Last match" kicker above the Opponent Intel panel. Pull from `data.history[data.history.length - 1]`. Example:

> *Last week: Won vs. Solstice Embers (Aggressive plan). Fatigue flagged on 2 starters.*

> *Last week: Lost vs. Lunar Arcs (Control plan). Opponent filed their strongest passing game yet.*

**Implementation complexity:** Low — data already exists in `data.history`. Render the last record's `dashboard.result`, `plan.intent`, and any stamina warnings from the prior lineup.
**Risk:** Low.

---

### Fix 5: Rename "Status" Column to "Role" in Roster

**Problem:** The Roster table's final column is labeled "Status" but shows a role badge (Thrower, Catcher, etc.). "Status" implies health or availability.

**Why it matters:** A player expecting health status here will look for an injury column that doesn't exist. A wrong label makes the screen feel incomplete.

**Recommended change:** Rename the column header from "Status" to "Role." The current badge already carries dual signal — the badge color differentiates starters (cyan) from bench (slate), and the text is the archetype (Thrower, Catcher). This dual meaning should be preserved: do not collapse it to a single meaning with the rename. If space permits, add a small stamina icon alongside starters to give the column a health-status function it currently promises but doesn't deliver.

**Implementation complexity:** Low — label change plus optional stamina icon.
**Risk:** None — just preserve the existing color-code signal.

---

### Fix 6: Add Playoff Position Context to Standings

**Problem:** The Standings screen shows a full table but no indication of how many games remain, what the playoff cutoff is, or whether the player's current position is safe.

**Why it matters:** A standings table without elimination context creates no tension. The player doesn't know if they're fighting for their playoff life or coasting.

**Recommended change:** Add a callout above the table: `Season X · Week Y of Z · Playoff cutoff: Top N`. Highlight the cutoff row with a visual divider. Add a "X games remaining" chip on the player's own row.

**Implementation complexity:** Medium — requires the backend to send `total_weeks` and `playoff_spots` in the standings response.
**Risk:** Low.

---

### Fix 7: Explain Elimination Differential with a Tooltip

**Problem:** "Elimination Differential" is a meaningful stat (total players your team eliminated minus total players eliminated against you across all matches) but nothing explains it.

**Why it matters:** It's a tiebreaker stat and a good proxy for team dominance, but to a first-time player it looks like noise.

**Recommended change:** Add a small `?` tooltip icon next to the column header. Tooltip text: *"Elimination differential: total opponents eliminated minus times your players were eliminated across all matches. Used as a tiebreaker."*

**Implementation complexity:** Low — HTML tooltip attribute or a simple hover component.
**Risk:** None.

---

### Fix 8: Remove the Hardcoded "Trend: UP" Chip

**Problem:** The Roster header always shows `Trend: UP` as a static chip. It is never `DOWN` or `FLAT`. 

**Why it matters:** Hardcoded optimistic stats erode trust. A player who loses 4 games in a row and sees "Trend: UP" will feel mocked by the UI.

**Recommended change:** Either (a) compute the actual trend from `weekly_ovr_history` for the starting 6 and show a real direction, or (b) remove the chip entirely and replace with something factual (e.g., `N Active Players`, `N Starters`).

**Implementation complexity:** Low — calculate the actual OVR trend from existing `weekly_ovr_history` data already present on each player.
**Risk:** None.

---

### Fix 9: Replace "Front Office Report" with "Match Fallout"

**Problem:** The fallout section after a match is labeled "Front office report." This is vague and doesn't communicate what the section contains (player growth, standings shifts, recruit reactions).

**Why it matters:** This is the most consequential part of the post-match — it tells the player what their decision caused. Weak framing buries it.

**Recommended change:** Rename to **"Match Fallout"** or **"After the Whistle"**. Update the sub-label from `h3: "Front office report"` to something like `"What your week caused"`. Make each fallout card title more active: "Player Development" → "Who Grew," "League Table" → "Standings Shift," "Recruit Reactions" → "Prospect Pulse."

**Implementation complexity:** Low — label changes only.
**Risk:** None.

---

### Fix 10: Make the "Key Performers" Panel Distinguish Your Players

**Problem:** The Key Performers post-match panel shows the top 3 performers from both teams. The player's own performers have a small gray club name label that's easy to miss.

**Why it matters:** The first question after every match is "how did my guys do?" The app makes the player work to find the answer.

**Recommended change:** Visually separate player performers from opponent performers. Add a colored left border or a "Your Club" tag to entries belonging to the player's club. Optionally, show only the player's top performer first, then the match-wide top performers below a divider.

**Implementation complexity:** Low — `player_club_id` is available in the `CommandCenterResponse`. Pass it to `KeyPlayersPanel` and conditionally apply a CSS class.
**Risk:** None.

---

## E. "Make It Feel Real" Recommendations

These are lightweight changes — no new systems, no major rebuilds. Each makes the game feel more like a real sports management product.

### E1. Write a post-match one-liner for every match

The `aftermath.headline` exists but feels machine-generated and generic. Instead of:
> *"Aurora Pilots take the win after a tight contest."*

Aim for:
> *"Pilots' back line held — Wreckers couldn't find a lane in the second phase."*

This requires a slightly richer headline template that references tactical elements. The engine already produces lane summaries — use them.

### E2. Give the season a title

Every sports season has a narrative frame. "Season 3" is not a narrative. Add a procedurally generated season subtitle at the start of each season:

> *Season 3: The Comeback Year*  
> *Season 4: A League on Fire*

This appears during the Schedule Reveal offseason beat and again at the top of the Command Center header. Low effort, high emotional payoff.

### E3. Surface a "Player to Watch" each week

Add a single highlighted player in the Command Center pre-sim — a player about to hit a development milestone, a player with a hot OVR trend, or a player who underperformed last week. One name, one sentence. This makes the roster feel alive without adding a new system.

*Example: "Dario Kim has shown a 4-point OVR jump over the last 3 matches. Consider featuring him this week."*

### E4. Add a season record note to the Command Center header

`Week 6 vs. Northwood Wreckers` is less motivating than:
`Week 6 of 12 · 3-2 · Ranked #4 · 2 games from playoff cutoff`

This single line contextualizes every match in the season. No new data required — it's all in `CommandCenterResponse`.

### E5. Add an opponent history line to Opponent Intel

"Last: No meeting recorded" is the default fallback for `matchup_details.last_meeting`. This is cold. Even when there's no historical data, write something:

> *"First meeting of the season — no tape, trust your reads."*

And when there is history:
> *"Faced them in Week 2. They ran a pressure-heavy formation. Harbor won 6-3."*

### E6. Make "Advance Week" feel earned

The current `AftermathActionBar` has two buttons: "View Replay" and "Advance Week." The advance button is functional but has no ceremony. Consider renaming it based on the result:

- Win: **"Bank the Result →"**
- Loss: **"Move On →"**
- Close match: **"Shake It Off →"**

Small copy changes, meaningful emotional difference.

### E7. Add a "This Week's Stakes" line to Command Center

One sentence above the opponent intel: what does this game mean for the season? Generate from standings position, games remaining, and win/loss streak:

> *"A win here puts you in playoff position for the first time this season."*  
> *"Three losses in a row — a win doesn't fix everything, but it stops the slide."*  
> *"Comfortable at #2. Use this week to rest the starters."*

### E8. Give the Staff Room a purpose statement

The staff list in Dynasty Office currently shows: Department → Name. That's it. Add one sentence per staff member describing what they actually do:

> *Tactics / Coach Rivera — Refines opponent game plans. Boosts accuracy of scouting reads.*

This makes the Staff Market meaningful — the player can evaluate hires.

### E9. Post-match recap email / "Bulletin board"

Add a short text block at the top of the next week's Command Center that reads like a news clipping from the match outcome. Pull from the headline, result, and one performer name:

> *"Aurora held steady in a 5-3 win against Solstice. Rivera's conditioning program paid dividends as no starters dropped below 70% stamina."*

This closes the "did my decision matter" loop from the prior week.

### E10. Make the offseason "records_ratified" and "hof_induction" beats structured

These two beats currently render as plain body text paragraphs — no visual structure. Give each one a simple card template:

**Records Ratified:** Show 3-4 season records set with player names and stat values.

**Hall of Fame Induction:** Show the inducted player's name, career stats, and one career highlight in a ceremony card matching the Awards Night aesthetic.

---

## F. Implementation Handoff for Codex

Below is a ready-to-paste prompt for Codex to implement the safest, highest-leverage fixes from this audit. These are all low-risk, low-complexity changes that do not require new systems or API changes (except Fix 6 which needs a backend addition).

---

```
## Codex Task: Product Coherence Fixes — Dodgeball Manager

Implement the following changes to the frontend. Do not change any Python backend unless explicitly noted. Do not change any game logic, match simulation, or persistence behavior. All changes are UI/copy/logic improvements only. Run `npm run build` and `npm run lint` to verify after each group.

**Note on Fix 1 (plan verdict):** Fix 1 — the "Did Your Plan Work?" verdict — is the highest-leverage change in this audit but is deliberately excluded from this Codex pass. It requires a backend sentence generator that bridges `selected_intent + match_result + lanes[0].summary` into natural language. That's a Python-side addition. Once the backend exposes a `verdict` string in the `Aftermath` payload, displaying it is a one-line frontend change — Codex can handle the display side then.

### Group 1 — Label and Copy Fixes (no logic changes)

1. **Roster: rename "Status" column to "Role"**
   File: `frontend/src/components/Roster.tsx`
   - In both the theater view thead and the compact view thead, change the column header text from "Status" to "Role".

2. **Roster: remove hardcoded "Trend: UP" chip**
   File: `frontend/src/components/Roster.tsx`
   - Remove the `<StatChip label="Trend" value="UP" tone="success" />` chip from the Roster header stats.
   - Replace it with `<StatChip label="Starters" value={roster.filter(r => r.starter).length} />`.

3. **Post-match fallout: rename labels**
   File: `frontend/src/components/MatchWeek.tsx`
   - Change the `PageHeader` description from `"Review the match result, replay identity, and weekly fallout."` to `"Review the result, who performed, and what your week caused."`
   
   File: `frontend/src/components/match-week/aftermath/FalloutGrid.tsx`
   - Change section heading from `"Front office report"` to `"Match Fallout"`.
   - Change h3 from `"Front office report"` to `"What your week caused"`.
   - Change FalloutCard title `"Player Development"` → `"Who Grew"`.
   - Change FalloutCard title `"League Table"` → `"Standings Shift"`.
   - Change FalloutCard title `"Recruit Reactions"` → `"Prospect Pulse"`.

4. **Match Replay: rename "CONTINUE ->" button**
   File: `frontend/src/components/MatchReplay.tsx`
   - Change button label from `'CONTINUE ->'` to `'BACK TO RESULTS'`.
   
   File: `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx` (if this component exists, otherwise the parent)
   - Ensure the "View Replay" button label is clear about where it goes.

5. **Match Replay: rename stats tab from "REPORT" to "BOX SCORE"**
   File: `frontend/src/components/MatchReplay.tsx`
   - In the tab bar, change `labels.stats` from `'REPORT'` to `'BOX SCORE'`.

6. **Match Replay: rename "TICK N" to "PLAY N" in play-by-play**
   File: `frontend/src/components/MatchReplay.tsx` — `PlayByPlayPanel`
   - Change `TICK {ev.tick}` to `PLAY {i + 1}` for the sequence display.

7. **Standings: add tooltip to Elimination Differential**
   File: `frontend/src/components/LeagueContext.tsx`
   - Add a `title` attribute to the "Elim Differential" / "Diff" th elements:
     `title="Total opponents eliminated minus times your players were eliminated. Tiebreaker stat."`
   - Do this for both the desktop and mobile header variants.

### Group 2 — Key Players: distinguish your club's performers

File: `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx`

- Accept a new optional prop: `playerClubId?: string`
- If `playerClubId` is provided, for each performer, check `player.club_name` against it (or add `club_id` to `TopPerformer` if the data is available — if not, use club name matching against the `player_club_name` from the parent component).
- Apply a `dm-badge dm-badge-cyan` badge reading "Your Club" next to the performer name when they belong to the player's club.
- Update `MatchWeek.tsx` to pass `playerClubId={currentData?.player_club_id ?? activeResult?.plan.player_club_id}` to `KeyPlayersPanel`.

### Group 3 — Duplicate lock button: remove top Action panel button

File: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

The `command-next-action` panel at the top currently contains a duplicate lock/simulate button.

- Remove the button from the `command-next-action` section.
- Replace it with read-only status text:
  - When not confirmed: `"Complete the readiness checklist below, then lock the plan to run the match."`
  - When confirmed: `"Plan locked. Simulate the match using the button below."`
- Keep all buttons in the `command-control-tower` section only (single source of action).
- Keep the `command-next-action-step` ("Step 1 of 2" / "Step 2 of 2") and `nextActionTitle` label — just remove the button.

### Group 4 — Last week context in Command Center

File: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

After the `command-alert-strip`, and before the `command-game-plan` section, add a "Last Match" one-liner.

Logic:
```typescript
const lastRecord = data.history.length > 0 ? data.history[data.history.length - 1] : null;
const lastResult = lastRecord?.dashboard?.result;  // "Win" | "Loss" | "Draw"
const lastIntent = lastRecord?.plan?.intent;
const lastOpponent = lastRecord?.dashboard?.opponent_name;
```

Render as a small `dm-kicker`-style strip above the game plan section:
```
LAST MATCH — [Win/Loss] vs {lastOpponent} ({humanize(lastIntent)} plan)
```
Color the result word: green for Win, red for Loss, gray for Draw.
Only render this strip if `lastRecord` is not null and `data.week > 1`.

Do not render this strip if `planConfirmed` is true (it becomes visual noise post-lock).

### Group 5 — Season context in Command Center header

File: `frontend/src/components/match-week/command-center/PreSimDashboard.tsx`

Update the `command-dashboard-subtitle` element. Currently: `Week {data.week} vs {plan.opponent.name}`

Change to: `Week {data.week} · {recentRecord} this season · vs {plan.opponent.name}`

Where `recentRecord` is already computed in the component (the `recentWins`-based record string).

This gives the player their season record at a glance every week.

---

After all changes:
- Run `npm run lint` and fix any issues.
- Run `npm run build` and confirm it succeeds with no errors.
- Do not run Playwright tests unless specifically asked.
- Write a short handoff note summarizing what changed and what still needs backend work (Fix 6 — playoff context in standings — requires backend changes, skip it for this Codex pass).
```

---

## Summary

**Strongest part of the current product:**
The post-sim reveal sequence (headline → score → story → fallout) combined with the Match Replay. This is genuinely fun, emotionally satisfying, and technically impressive. The Offseason ceremony sequence is the runner-up — it gives the game genuine seasonal rhythm.

**Weakest part of the current product:**
The connection between player decisions and visible consequences. The app tells the player what happened but not why it happened in relation to their choices. The plan-to-outcome link is the core feedback loop of a management sim, and it's currently the weakest link in the chain.

**Top 5 recommended next changes:**

1. **Remove the duplicate lock button and clean up the Next Action panel** (Group 3 in Codex handoff) — low effort, high clarity.
2. **Add "Last Match" context to Command Center** (Group 4) — directly attacks the biggest weakness, minimal effort.
3. **Rename "Fallout" section labels** (Group 1, Fix 9) — makes the most important post-match section feel real.
4. **Distinguish player club performers in Key Players panel** (Group 2) — eliminates the "which ones are mine?" confusion.
5. **Add season record to Command Center subtitle** (Group 5) — one line of text that adds permanent season context to every week.

**Which changes should go to Codex first:**
Groups 1 and 3 — all label/copy fixes and the duplicate button removal. These are zero-risk, non-interactive changes that clean up the product in one Codex session. Groups 2, 4, and 5 can follow in the same or next session.
