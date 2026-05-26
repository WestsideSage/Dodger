Dodger UI/UX Teardown Report
Review Summary
Model: GPT-5 Codex
Tools/MCPs used: in-app Browser with Playwright-style navigation/screenshots, console log inspection, API fast-forward helpers, custom DOM accessibility/overflow probes. Axe/Chrome DevTools/Figma/Antigravity MCPs were not exposed; axe-core was not locally installed and in-page injection was blocked by the browser sandbox.
Browser URL: http://127.0.0.1:8000
Screens reviewed: save menu, new game, build-from-scratch, command center, roster, dynasty recruit/history, standings/playoff bracket, aftermath, replay, offseason champion/recap/records/development/rookie/recruitment/schedule.
Overall UX verdict: Playable and flavorful, but not yet polished. The core fantasy is present; the biggest issues are comprehension, mobile layout, and a few actual state/display bugs.
Biggest product risk: players cannot quickly answer “what decision am I making, why, and what changed because of it?”
Highest Priority UX Problems
1. Command Center Hides The Main Decision
Issue: The first viewport over-prioritizes tags, broadcast frame, and three equal panels before the core “lock/simulate” action.
Severity: Critical
Screen/component: Command Center / PreSimDashboard
Evidence: 01-command-center-desktop.png, 02-command-center-mobile.png
Why this hurts the player: the management loop starts by making the player hunt for the action.
Concrete Codex fix: add a sticky or top-level “This Week Decision” strip with opponent, recommendation, current plan, blockers, and primary CTA.
Acceptance criteria: at 1440x900 and 390x844, the primary action and recommendation are visible without scrolling.
2. Mobile Command Center Overflows
Issue: proof/source strings and policy grids exceed mobile width.
Severity: High
Screen/component: Broadcast proof + plan editor
Evidence: DOM probe found command mobile overflow: proof code reached right: 415 in a 390px viewport; plan panel scrollWidth: 436.
Concrete Codex fix: word-break: break-word / overflow-wrap:anywhere for proof sources; stack policy editor sections on mobile.
Acceptance criteria: no horizontal overflow at 390px.
3. Roster Mobile Is Still A Desktop Table
Issue: mobile roster hides Potential, OVR, and Role offscreen.
Severity: High
Screen/component: Roster table
Evidence: table width 798px in 390px viewport; 04-roster-mobile.png.
Concrete Codex fix: render roster cards on mobile with name, starter/age, OVR, role, potential, and four ratings.
Acceptance criteria: no horizontal scroll; each player card exposes role, OVR, potential, and ratings.
4. Replay And Aftermath Use Conflicting Score Language
Issue: aftermath says 0-2 survivors; replay header shows 6-7.
Severity: High
Screen/component: Aftermath + Match Replay
Evidence: 19-aftermath-desktop.png, 21-match-replay-desktop.png
Concrete Codex fix: make replay header show the same survivor result, with secondary raw/event score clearly labeled.
Acceptance criteria: player can match replay result to aftermath result without interpretation.
5. Actual Bug: Recent Results Says “Winner: Draw” For A 1-0 Match
Issue: standings recent results contradict themselves.
Severity: High
Screen/component: Standings / Recent Results
Evidence: 09-standings-desktop.png
Concrete Codex fix: fix recent-match winner derivation; draw label only when score is tied/no winner.
Acceptance criteria: non-draw score never renders Winner: Draw.
6. Actual Bug Risk: Replay Court Token Shows “NONE”
Issue: one replay player marker rendered as NONE.
Severity: Medium
Screen/component: Match Replay court
Evidence: 21-match-replay-desktop.png, Solstice Flare side.
Concrete Codex fix: trace player-token label source; replace null fallback with player name or an explicit “empty slot” state only when valid.
Acceptance criteria: replay court never renders NONE for an active player.
7. Save Menu Shows Debug Saves While Debug Toggle Is Off
Issue: debug-* saves are visible in the normal load list.
Severity: Medium
Screen/component: Save Menu
Evidence: 11-save-menu-list-desktop.png, 12-save-menu-list-mobile.png
Concrete Codex fix: filter debug-*, e2e-*, and qa-* saves behind the debug toggle or add save metadata.
Acceptance criteria: normal player load list contains only real user saves.
Screen-by-Screen Review
Command Center / Home
What works: strong club-management fantasy; broadcast proof is valuable; scout/readiness panels are meaningful.
What does not: too dense; primary action is not first-class; mobile overflows; plan editor/scout/readiness compete visually.
Fixes for Codex: build a decision summary CTA strip; collapse advanced policy details; stack mobile controls.
Roster
What works: ratings bars and role/potential framing are useful.
What does not: mobile table is unusable; no obvious sort/filter/comparison path.
Fixes for Codex: mobile card layout; sortable desktop columns; expose “why this player matters this week.”
Match / Live Sim
What works: court visualization, highlights, and replay controls support the fantasy.
What does not: score vocabulary conflict; control strip is dense on mobile; possible NONE token bug.
Fixes for Codex: unify result language; simplify mobile replay controls; fix null player labels.
Training / Development
What works: dev focus exists in Command Center and offseason development reports progression.
What does not: training/development feel secondary, not like a management pillar.
Fixes for Codex: add visible “Training impact this week” and “Development focus changed because…” summaries.
Recruiting / Scouting / Transactions
What works: onboarding roster draft and offseason Signing Day are understandable.
What does not: Dynasty recruiting buttons are disabled with weak explanation; Signing Day lacks fit/need comparison.
Fixes for Codex: show remaining slots as 0/3 remaining, next unlock timing, and prospect fit against current roster.
Season / League / Standings
What works: playoff bracket is clear; standings context helps.
What does not: recent result winner bug; small metadata contrast is weak.
Fixes for Codex: fix winner copy; raise contrast; keep bracket + table readable on mobile.
Any Other Screens
Save menu: debug saves leak into normal flow.
Offseason: ceremony beats work, but champion/development/rookie screens feel sparse.
Fixes: richer season context cards, clearer progress, and fewer huge empty states.
Accessibility Findings
Issue: build-from-scratch labels are visual-only.

Tool/evidence: custom DOM probe found SAVE NAME, CLUB NAME, CITY, CLUB COLORS labels without for or wrapped controls.

Impact: screen-reader and click-target labeling risk.

Concrete fix: add stable input ids and htmlFor.

Acceptance criteria: probe reports zero orphan labels.

Issue: low-contrast metadata.

Evidence: DOM probe found small text ratios around 2.36:1 and 1.72:1.

Impact: playoff labels, “Present,” OVR labels, and disabled/secondary copy are hard to read.

Concrete fix: update muted text tokens to meet WCAG contrast.

Acceptance criteria: small functional text >= 4.5:1.

Layout / Text Overflow Findings
Roster mobile: 798px table inside 390px viewport. Fix with mobile cards.
Dynasty history mobile: 460px timeline SVG inside 390px viewport. Fix responsive SVG/viewBox.
Command mobile: proof source and plan grid overflow. Fix wrapping and stacked controls.
Interaction Bugs
Action attempted: inspect normal save list.

Expected: debug saves hidden unless debug toggle enabled.

Actual: debug-* saves visible.

Concrete fix: broaden debug-save filter.

Action attempted: inspect standings recent results.

Expected: winner matches result.

Actual: Solstice Flare 1-0 Northwood Ironclads says Winner: Draw.

Concrete fix: repair recent result winner mapping.

Design System Consistency Issues
Pattern: tabs vary between left rail, top mobile nav, save menu tabs, dynasty subtabs.

Recommended version: one tab primitive with consistent active, focus, disabled, and mobile behavior.

Pattern: action bars vary between Lock Plan, Simulate, Continue, Start New Season.

Recommended version: standardized action bar with primary CTA, secondary CTA, explanatory copy, disabled reason.

Pattern: proof toggles use small <summary> text.

Recommended version: standardized “Show proof” disclosure with consistent touch target and wrapped proof source.

Top 15 Codex Tasks
Add Command Center decision CTA strip.
Make Command Center mobile layout single-column.
Convert mobile roster table to player cards.
Unify aftermath/replay score terminology.
Fix Recent Results Winner: Draw bug.
Fix replay court NONE token fallback.
Hide debug saves behind debug toggle.
Wire build-from-scratch labels with htmlFor.
Raise muted metadata contrast tokens.
Explain disabled Dynasty recruiting actions.
Add Signing Day fit/need details.
Improve offseason ceremony density and progress context.
Make Dynasty timeline responsive.
Standardize action bars and disabled states.
Add Playwright regression checks for mobile overflow, recent-result winner text, and replay token labels.