# Dodger UI/UX Teardown Report

## Review Summary
- Model: Claude Opus 4.7
- Tools/MCPs used: Playwright MCP (navigation, snapshot, evaluate, screenshot, console), Bash (server + log inspection), in-page JS for an axe-style accessibility scan (contrast, labels, headings, alt text)
- Browser URL: http://127.0.0.1:8000 (save `playtest-naive-1779685637909`, Seattle Steelheads, Year 2 Week 7)
- Screens reviewed: Save Menu (Load Game, New Game), Command Center (pre-lock, locked, postgame, ceremony beats), Roster, Dynasty Office (Recruit, Staff Room), Standings, Match Replay, Postgame Report, Season Champion, Final Regular-Season Table, Awards Night, Records Ratified
- Overall UX verdict: The shell is genuinely promising — strong typographic identity, a coherent "war room" framing, and a real attempt at narrative copy. But under playtest the seams show fast: load failures with no recovery path, a recap that contradicts the result, a replay that disagrees with the result, and a season-ending sequence whose beats fire in the wrong order. The product *looks* like a polished management sim and *behaves* like a prototype whose state machine and copy generator are out of sync.
- Biggest product risk: **Authoritative-feeling UI presenting contradictory numbers.** A user who reads the recap "clawed it back with 0 catches" next to "0–4 shutout loss," then opens the replay and sees "6 — 5," cannot trust anything else the game tells them. Truth integrity must be fixed before any cosmetic work.

## Highest Priority UX Problems

### 1. Match Replay score disagrees with Postgame Result for the same match
- Issue: Postgame screen shows `SEATTLE STEELHEADS 0 — HARBOR TIDEBREAKERS 4` (final, shutout). Clicking *View Full Replay* opens Match Replay showing `SEATTLE STEELHEADS 6 — 5 HARBOR TIDEBREAKERS`.
- Severity: **Critical**
- Screen/component: Postgame `RESULT` card vs Match Replay header at the top of `/?tab=command` after `Simulate Week` → `View Full Replay`.
- Evidence: `match-result.png` (0–4, shutout banner) and `replay.png` (6 — 5 header, "Harbor Tidebreakers wins" star elsewhere on result screen).
- Why this hurts the player: The replay is the user's primary "did I really lose like that?" sanity check. If the two views disagree, the user concludes the game has no source of truth and stops trusting any reported outcome — including standings, awards, and prospect growth.
- Concrete Codex fix: There are two different score sources feeding these two screens. Identify the result payload returned by the `/api/simulate` (or equivalent) response and make Match Replay's header read from the same `match_result.survivors_home / survivors_away` (or `score`) field that the Postgame card uses. Delete any client-side recomputation of score from replay events.
- Acceptance criteria: For ten consecutive simulated weeks across two saves, the score shown on Postgame `RESULT` exactly matches the score shown on Match Replay header. A unit test asserts `replay.header_score == result.final_score` for every match in a fixture season.

### 2. Recap headline contradicts the result it sits above
- Issue: Above the 0–4 result card, the recap reads:
  - "Seattle Steelheads were down 2 and clawed it back with 0 catches."
  - "A 0–4 shutout loss with nowhere to hide."
- Severity: **Critical**
- Screen/component: Command Center → Postgame headline strip; also repeated in Postgame Report panel under `COMEBACK`.
- Evidence: `match-result.png`, `postgame.png`, raw text capture in conversation.
- Why this hurts the player: The recap is the loudest text on the screen. A "comeback narrative" attached to a shutout loss is not a typo — it's a tell that the narrative generator is firing templates that never check the result. It makes the post-match moment feel automated and broken, exactly when emotional payoff matters most.
- Concrete Codex fix: The comeback template (`"<team> were down N and clawed it back with M catches"`) is being chosen regardless of outcome. Add a precondition: comeback templates may only fire when `winner_team_id == player_team_id` AND `max_deficit >= 2`. For losses, switch to a loss-template family (e.g. "Couldn't dent the wall — Tidebreakers shut us out 0–4"). The `COMEBACK` block in Postgame Report should be hidden entirely when there was no comeback.
- Acceptance criteria: Add unit tests on the recap selector: (a) for every shutout loss in fixtures, no template containing "clawed it back" or "comeback" is selected; (b) for every win where opponent was up ≥2 survivors at some tick, a comeback template is allowed.

### 3. Championship is awarded before the Final Regular-Season Table screen, with no playoff bracket shown
- Issue: After `Simulate Week` on Week 7, ceremony beats fire in this order: `SEASON CHAMPION (Solstice Flare)` → `Final Regular-Season Table` → `Awards Night` → `Records Ratified`. There is no playoff bracket screen and the champion is announced before the player has seen the regular-season standings finalize.
- Severity: **Critical**
- Screen/component: Command Center ceremony / offseason beat sequence (`OFFSEASON BEAT n/8`).
- Evidence: `champion.png` (champion announced, no bracket), `regseason-final.png` (table explicitly says "The top four seeds advance to the playoff bracket, where the champion is decided" — *after* champion already crowned).
- Why this hurts the player: The whole point of a dynasty sim is the climb. Telling the player who won before showing how they got there destroys narrative tension and makes the playoff system feel imaginary. The on-screen text on the Final Table screen actively lies about what comes next.
- Concrete Codex fix: Reorder beats: `Final Regular-Season Table` → `Playoff Bracket` (new screen) → playoff match recaps (one per round) → `Championship Final Recap` → `Season Champion` → `Awards Night` → `Records Ratified`. If playoffs are not yet implemented as visible matches, at minimum: (a) move `Season Champion` to after `Final Regular-Season Table`, and (b) edit Final Table copy to remove the "top four advance" sentence until brackets exist.
- Acceptance criteria: For three simulated seasons, the beat counter shows `Final Regular-Season Table` strictly before `Season Champion`, and the Final Table subtitle no longer references a bracket unless a bracket screen actually follows.

### 4. Loading an old save crashes silently — the button does nothing, no error UI
- Issue: Clicking *Load* on `Championship Quest` (Summit Vipers) returns HTTP 500 from `/api/status` with `ValueError: Legacy CoachPolicy payload detected during Plan C migration: catch_bias, risk_tolerance, rush_frequency, rush_proximity, sync_throws, target_ball_holder, target_stars, tempo.` No toast, no banner, no error message — the user stays on the save menu wondering if the click registered.
- Severity: **Critical**
- Screen/component: Save Menu → Load button; backend `persistence.load_clubs` → `CoachPolicy.from_dict`.
- Evidence: Server traceback in background log (`bmbi3vi33.output`), console error `Failed to load resource: the server responded with a status of 500 (Internal Server Error) @ /api/status`.
- Why this hurts the player: A passion-project sim collects saves over time. If an update silently breaks every pre-Plan-C save and the UI gives no signal, the user assumes their dynasty is gone. This is the single fastest way to lose a returning player.
- Concrete Codex fix: Two parts. (a) Add a `CoachPolicy.from_legacy_dict` migration that maps the eight legacy keys to the current 8-field schema (the renames are mostly recoverable: `target_stars`→target focus, `rush_frequency`+`rush_proximity`→opening-rush commit/target, `catch_bias`→catch posture, `risk_tolerance`→approach, etc.). (b) When migration is impossible, surface the failure: `/api/status` should return 422 with `{"error": "save_incompatible", "reason": "Save predates Plan C coach policy; please start a new game."}` and the React save menu should render that string in an inline error row next to the offending save with a *Delete* affordance and a "Why?" tooltip.
- Acceptance criteria: Loading every save currently on disk either succeeds, or fails with a visible per-save error row in the menu and a non-500 status code. No load attempt leaves the UI in an indeterminate "click did nothing" state.

### 5. Standings says "1 game remaining" but Simulate Week ends the season
- Issue: Standings tab header reads `WEEK 7 OF 7 · PLAYOFF CUTOFF — TOP 4 · 1 GAME REMAINING` while the Command Center is on Week 7. Clicking `Simulate Week` plays one game (the Week 7 fixture) and immediately jumps to season-end ceremony, bypassing any playoff games.
- Severity: **High**
- Screen/component: Standings header vs Command Center end-of-season transition.
- Evidence: `standings.png` ("1 GAME REMAINING") followed by `champion.png` after a single `Simulate Week`.
- Why this hurts the player: "1 game remaining" implies one game stands between you and your fate. The user expects to play that game and then see playoff weeks. When the engine collapses everything into "season over," the prior status text reads like a lie.
- Concrete Codex fix: Either (a) genuinely simulate playoff games as visible weeks (preferred — see fix #3), or (b) until playoffs are real, change the Standings header to `WEEK 7 OF 7 · REGULAR SEASON FINALE · SEASON ENDS NEXT` and remove the "playoff cutoff — top 4" subtext until playoffs exist.
- Acceptance criteria: The countdown text on Standings always matches the number of `Simulate Week` clicks until the next ceremony beat fires.

### 6. "Show debug saves" defaults on; debug clutter dominates the save list
- Issue: On the load menu the `Show debug saves` checkbox is checked by default. Result: 24 saves visible, of which 10+ are clearly developer artifacts (`debug-hof-65e3fab0`, `debug-v13-1779659044145`, `playtest-naive-1779685177693`, `ux-teardown-1779685010902`, etc.). Real saves like `Iron Dynasty` and `Wraith Dynasty` are buried.
- Severity: **High**
- Screen/component: Save Menu list.
- Evidence: `01-landing.png` (failed to save earlier but visible in `browser_snapshot` for landing).
- Why this hurts the player: First impression of the game's storage is "messy database dump." A returning player can't quickly find the save they actually care about.
- Concrete Codex fix: Default `Show debug saves` to unchecked. Treat a save as "debug" if its name matches `^(debug-|playtest-|ux-teardown-|test_)`. While unchecked, show a small footer "5 debug saves hidden · Show" rather than a checkbox in the header.
- Acceptance criteria: With default settings, only user-created saves appear; toggling reveals the rest; the count is shown.

### 7. Awards: MVP and Best Catcher are the same player, same stat
- Issue: MVP = Ezra Bloom (Solstice Flare) shown with 10 catches. The "BEST CATCHER" tile right below also reads Ezra Bloom — 10 catches. Identical line item twice.
- Severity: **High** (because Awards Night is a payoff moment)
- Screen/component: Ceremony beat `AWARDS NIGHT`.
- Evidence: `awards.png`.
- Why this hurts the player: Awards Night should feel like the league recognizing distinct excellence. Doubling the same player in two slots makes the ceremony feel automated and small — it tells the user "we just printed the top of each leaderboard" rather than "the league saw what you did."
- Concrete Codex fix: When MVP also leads a category, suppress that category's tile and replace with the next-best at that stat, OR show a single combined "MVP + Best Catcher" card with a unified treatment. Recommended: keep MVP unique and elevate runners-up for category awards.
- Acceptance criteria: No category award tile shows the same player as MVP in the same season.

### 8. Save list rows lack date / season / record — can't tell which save is most recent
- Issue: Each save row shows only title (often debug hash) and club name. No date, no season/week, no W-L, no last-played timestamp.
- Severity: **High** for returning users.
- Screen/component: Save Menu list.
- Evidence: Snapshot listing — every `listitem` is two lines of text + Load/Delete.
- Why this hurts the player: After a week away, a user opens the game and cannot identify which save was their active dynasty. They have to load each one to find out, and loading is currently risky (see #4).
- Concrete Codex fix: Extend `/api/saves` to include `last_modified`, `season`, `week`, `record` (W-L-D), and `phase` (Regular / Playoffs / Offseason). Render a third line in each row: `Season 4 · Week 9 · 6-2 · saved 2h ago`. Default sort: most recently modified first.
- Acceptance criteria: Top-of-list is always the save most recently written to disk; each row visibly shows season + week + record.

### 9. Plan Editor and Policy Editor present the same approach twice in different vocab
- Issue: Command Center has `PLAN EDITOR` showing tactical approach buttons `BALANCED / AGGRESSIVE / CONTROL / DEFENSIVE`. Directly underneath, `POLICY EDITOR → Approach` shows `Aggressive / Patient / Mixed`. Both control "approach"; both are simultaneously visible; the vocabularies don't line up (no "Patient" in plan editor, no "Defensive" in policy editor).
- Severity: **High** (this is the primary decision the player makes each week)
- Screen/component: Command Center `PLAN EDITOR` + `POLICY EDITOR` panels.
- Evidence: Command Center text capture showing both blocks back to back.
- Why this hurts the player: The single most important interaction in a match-prep loop is "set my approach." Splitting it across two editors with overlapping-but-different word lists makes the player unsure which control is authoritative, and what "Aggressive" in one means relative to "Aggressive" in the other.
- Concrete Codex fix: Pick one. Recommended: keep Policy Editor (the 5-axis policy) as the authoritative input, demote Plan Editor's approach buttons to a derived "Suggested approach" read-only chip that updates from policy selections. Unify vocab to a single canonical list (e.g. `Aggressive / Balanced / Control / Defensive`).
- Acceptance criteria: Only one set of approach buttons is interactive. Both labels and the resulting `coach_policy.approach` use a single shared enum.

### 10. Page `<title>` is "frontend"
- Issue: Browser tab title is literally the string "frontend" (the Vite default).
- Severity: **High** for polish; trivial to fix.
- Screen/component: `frontend/index.html`.
- Evidence: Page URL/title in every Playwright snapshot.
- Why this hurts the player: Pinning the tab, alt-tabbing, or coming back from another window shows a generic dev placeholder — instantly breaks the "real product" illusion.
- Concrete Codex fix: Set `<title>Dodgeball Manager</title>` in `frontend/index.html` (and update dynamically with the active club/week if you want extra polish: `Steelheads · S2 W7 · Dodgeball Manager`).
- Acceptance criteria: Tab title reads `Dodgeball Manager` on first load and updates when a save is loaded.

## Screen-by-Screen Review

### Command Center / Home
- What works: Strong typographic identity. The "WAR ROOM / COMMAND CENTER" framing is evocative. The week-context strip (year, week, opponent record, net OVR delta) gives a fast read of where you stand. `WEEK LOCK STATUS` with 5 green check chips communicates readiness clearly. `LINEUP LEVERAGE` matchup comparisons are a great idea — telling the player "Mika Thorn (52) ▶ Kenji Vega (69), −17" turns abstract OVR into a felt mismatch.
- What does not:
  - Two redundant approach controls (#9).
  - "Outside the top three with 1 to play — the margin for error is gone" is dramatic but factually fuzzy: the player is 4th of 7 and standings say top-4 makes playoffs, so they are technically *in*, not "outside." Microcopy should reflect the current playoff line.
  - `BROADCAST FRAME · REGULAR SEASON · Show proof` is mystery furniture — no obvious purpose for the player, and "Show proof" is a debugging affordance that leaked into the player UI.
  - `TACTICS DEPT.` advisory copy ("Scouting indicates Harbor Tidebreakers will challenge our rotations…") sits at the bottom of a long scroll without visual emphasis; should sit next to the matchup header where the decision is being made.
  - `READINESS` warnings ("Nia Frost is a mismatched Runner…", "Mika Thorn is a weak starter…") are useful but use generic `!` bullets, not severity-coded chips. A weak-starter warning and a fatigue warning read with the same weight.
- Fixes for Codex:
  - Collapse Plan Editor's approach buttons into a read-only chip; keep Policy Editor as the single input.
  - Hide `BROADCAST FRAME / Show proof` behind a debug flag (or behind Settings → Developer).
  - Move `TACTICS DEPT.` directive into the opponent banner as a one-line "Scout brief."
  - Color readiness warnings by severity (red = blocking, amber = caution, blue = info) and add icons distinct from `!`.

### Roster
- What works: Compact view toggle is a smart progressive-disclosure choice. Four rating bars per player (Accuracy, Power, Dodge, Catch) with both numeric and visual length is exactly right for a sim of this depth. Potential expressed as two parallel encodings (stars + filled dots) is forgiving for different reading styles. Role pills (`TWO-WAY THREAT`, `BALL HAWK`, etc.) give identity quickly.
- What does not:
  - Header row labels (`PLAYER / RATINGS / POTENTIAL / OVR / ROLE`) are very faint; visual weight goes to the rows, but the column boundaries are unclear so it's hard to scan a column.
  - "Starter · Age 21" sub-label repeats `Starter` for every starter — a row-level "Bench" badge would land better as a colored chip than as plain text.
  - There is no way to sort or filter (by OVR, age, role, potential, fatigue) from this screen. For a 20-player roster this is tolerable; if rosters grow, it becomes painful fast.
  - Nothing on this screen exposes injury / fatigue / morale — the Command Center talks about "extreme fatigue risk" but Roster shows no fatigue column.
- Fixes for Codex:
  - Strengthen column headers (uppercase, higher contrast, sticky on scroll).
  - Replace "Starter · Age 21" with a colored `STARTER` / `BENCH` pill + "Age 21" small text.
  - Add at minimum sort-by-column on header click; defer filters until rosters exceed ~20.
  - Add a Fatigue and Injury column (or compact icon strip) so the fatigue warnings on Command Center have a place to land here.

### Match / Live Sim (Match Replay)
- What works: The 2D court layout with named circles per side is immediately legible — you understand who is on, who is out, who got eliminated. Tempo controls (1x / 2x / 4x / instant) are a nice touch. Tabs for `HIGHLIGHTS / PLAY-BY-PLAY / KEY PLAYS / BOX SCORE` cover the right four views.
- What does not:
  - **Score header disagrees with Postgame** (#1, critical).
  - Highlights show `TICK 6` then `TICK 5` — out-of-chronological-order highlight numbering is confusing; "Highlight 1 / 2 / 3" labels suggest order matters but ticks contradict it.
  - "Match Start" panel under the timeline restates "Match Start" twice (header + body). Empty/initial state should say something like "Press play to begin the replay."
  - No keyboard shortcuts surfaced (Space to play/pause, arrows to step) on a screen built around playback.
  - The court takes ~half the viewport and is mostly empty; the high-value text content (highlights, play-by-play) sits below the fold on a 900px viewport.
- Fixes for Codex:
  - Fix score parity with Postgame first (#1).
  - Sort highlight tiles by `tick` ascending and put the tick number as a header chip.
  - Add `←` / `→` / `space` keybindings with a one-line "Space play · ← → step · 1 2 4 speed" hint under the controls.
  - Tighten the court height by ~30% so two or three highlight cards are visible alongside it.

### Training / Development
- What works: Training is folded into the Command Center policy panel (`TRAINING · FUNDAMENTALS · DEVELOPMENT · Balanced / Youth acceleration / Tactical drills / Strength and conditioning`). For a weekly-cadence sim, putting training next to plan/policy keeps the decision loop compact.
- What does not: There is no standalone Training screen. The four training focus options are labels with no per-player visibility into who is gaining what. After ceremonies, the Postgame Report says "Training order: fundamentals. Youth-rep visibility continues to track with recent program trajectory." That sentence does not name any player or any stat change — it's pure non-content.
- Fixes for Codex:
  - Surface a small per-week training delta on the Postgame Report: "Selah Ibarra +1 Catch, Elio Penn +1 Dodge (Fundamentals)."
  - Add a "Training Focus" callout in the Roster header showing the current focus and which 2–3 players are expected to gain.
  - "WHO GREW · No growth logged this week" is honest but redundant when training never visibly grows anyone. Either growth happens and is named, or this section is dropped from Postgame.

### Recruiting / Scouting / Transactions (Dynasty Office → Recruit)
- What works: Eight prospects shown with priority order, range (`37-87`), fit score (`67.4`), and three action verbs per row (`SCOUT / CONTACT / VISIT`). Credibility tier (`Tier D`) shown alongside, with a clear breakdown of what feeds it. Slot counters (`SCOUT 0/3 · CONTACT 0/5 · VISIT 0/1`) communicate weekly budget at a glance.
- What does not:
  - Every prospect row shows the same credibility line: "Public range 37-87. Credibility grade D contributes to interest." Repeating this on eight rows is noise — show it once at the panel level.
  - "Strong fit / Worth tracking" badges have only two states across 8 rows; the gradient is invisible.
  - The three action buttons (`SCOUT / CONTACT / VISIT`) per row have no obvious affordance for "what does this cost / what does this do?" — first-time players will button-mash and burn slots.
  - "Munn | Hit-and-Run", "Turner | Skirmisher" — what is "Munn"? Looks like a position code with no legend.
  - Scout Read panel name "Briar Santos · Munn | Hit-and-Run" repeats the surname-as-archetype pattern; check whether `Munn` is intended as an archetype label or is a leaked internal id.
- Fixes for Codex:
  - Replace the per-row credibility sentence with a single panel header note.
  - Add a hover tooltip on each action: "SCOUT (1 slot): reveals a hidden rating. CONTACT (1 slot): improves interest by +X. VISIT (1 slot): scheduled campus visit, biggest interest boost."
  - Add a legend or expand `Munn` / `Vega` / `Turner` etc. to full archetype names.
  - Add a third fit tier (`MARGINAL`) so the badge column actually segments the board.

### Season / League / Standings
- What works: Clean table, color-coded W/L/T cells, your team highlighted in amber. "Around the League · Recent Results" sidebar is a great touch — gives the league texture without leaving the screen. The `ELIM DIFFERENTIAL` column is a nice sim-native stat.
- What does not:
  - W-L-D column header is right-aligned and visually distant from the data; takes a beat to associate.
  - Approach column shows raw config strings ("Win Now", "Develop Youth", "Balanced Rebuild") that look more like dropdown values than league flavor.
  - The "YOU" pill on Seattle Steelheads is rendered as a tiny chip; it could be bolder.
  - "1 GAME REMAINING" subtext misleads (#5).
  - No way to click a club name to see their roster / recent form / head-to-head — leaves you in a dead-end view.
- Fixes for Codex:
  - Left-align numeric column headers under their data.
  - Make club name a link that opens a lightweight club drawer (roster preview, last 3 results, H2H vs you).
  - Wrap each approach in a small badge with a one-word category instead of free text.

### Save Menu
- What works: Two prominent tabs (Load / New Game), New Game branches into "Take Over a Program" vs "Build from Scratch" with one-line descriptions — that fork is well framed.
- What does not: See #6 (debug clutter), #8 (no dates/season), #4 (silent failure).
- Fixes for Codex: As described above plus: add a "Continue" hero button at the top that loads the most-recently-modified non-debug save in one click.

### Ceremony / Offseason Beats
- What works: The "OFFSEASON BEAT n/8" counter is great — it tells the player the rhythm is finite and forward-moving. Records Ratified screen with "5 → 15" deltas is exactly the kind of league-history flavor a dynasty sim needs.
- What does not: Beats are in the wrong order (#3). "CEREMONY CONTROL · Continue to the next offseason beat" is verbose chrome that repeats on every screen; should be a single sticky footer button labeled with the *next* beat's name, e.g. "Continue → Awards Night."
- Fixes for Codex: Reorder beats; replace generic "Continue" with `Continue → <next beat name>`.

## Accessibility Findings

### A11y-1. Low-contrast secondary text on dark surfaces
- Issue: "Show proof" links (`rgb(100,116,139)` on dark panel) score contrast ratio ≈ 3.94 — below WCAG AA 4.5:1 for normal text. The `record:career_catches` style debug-id tokens score ≈ 2.47. The orange "Continue" button text was measured at 2.80 on its current orange background.
- Tool/evidence: In-page contrast scan via Playwright `browser_evaluate`.
- Impact: Players with low vision and players in bright environments will lose secondary affordances; the "Continue" CTA failing AA on the primary action is the most worrying.
- Concrete fix: Bump "Show proof" link color to at least `#94a3b8` (contrast ≈ 7+ on the `#0b1220` background). For the orange `Continue` button, darken background OR switch label to near-black on the orange to lift contrast above 4.5:1. Strip the `record:*` debug tokens from the player-facing UI entirely.
- Acceptance criteria: All visible text passes WCAG AA contrast on every reviewed screen, verified by a contrast-scanning script in CI.

### A11y-2. Heading structure under-uses semantic levels
- Issue: Only one `<h1>` and one `<h2>` per page; almost every other text block is a styled `<p>` or `<div>`. Many things that read as section headings ("LINEUP LEVERAGE", "WEEK LOCK STATUS", "SCOUT READ", "BROADCAST FRAME", "TACTICS DEPT.") are not `<h3>` — they're styled small caps in generic divs.
- Tool/evidence: `browser_evaluate` heading enumeration returned only `H1, H2`.
- Impact: Screen reader users get a flat document with no way to jump between Command Center sections; keyboard navigation is harder.
- Concrete fix: Promote each panel title to `<h3>` (or `<h2>` if it's a top-level region under the page heading). Keep visual styling identical.
- Acceptance criteria: Every visible "SECTION TITLE" small-caps label is a heading element of an appropriate level; tab-through navigation lands on each panel heading.

### A11y-3. Settings nav button is disabled with no explanation
- Issue: `Settings` sits in the sidebar with `disabled` attribute and no tooltip.
- Tool/evidence: Snapshot shows `button "Settings" [disabled]`.
- Impact: Players who tab through the nav land on a disabled control. A keyboard-only user can't tell why.
- Concrete fix: If Settings isn't built yet, hide the button entirely; if it's intentionally disabled in this build, add `aria-describedby` pointing to a "Coming soon" message.
- Acceptance criteria: No disabled nav items present, OR every disabled control has an accessible name explaining why.

### A11y-4. SVG icons (court positions, badges) are visible without aria treatment
- Issue: The scan found zero `<img>` without alt and zero `<svg>` missing both `aria-label` and `aria-hidden` *on the current view* — but this was on a text-heavy page. Match Replay's court visualization heavily uses SVG circles for players; verify those have `aria-label="Cross"`, `aria-label="Vega · eliminated"` etc., or `aria-hidden="true"` if the names appear in adjacent text.
- Tool/evidence: Spot-check needed on Match Replay.
- Impact: Court state invisible to screen readers.
- Concrete fix: For each player circle in the court SVG, set `<circle aria-label="${player.name}${eliminated ? ' (out)' : ''}">`. The container `<svg>` should have `role="img" aria-label="Court state at tick N: 6 Steelheads, 5 Tidebreakers on court"`.
- Acceptance criteria: Screen reader announces every player and their state when focused on the court.

## Layout / Text Overflow Findings

### L-1. Some headers use SHOUTING ALL CAPS for everything — visual fatigue
- Location: Command Center (every panel title), ceremony screens, banners.
- Problem: When every label shouts (`WAR ROOM / COMMAND CENTER / PLAN EDITOR / POLICY EDITOR / SCOUT READ / WEEK LOCK STATUS / LINEUP LEVERAGE / READINESS / PLAN STATUS / TACTICS DEPT.`), nothing draws focus. The hierarchy collapses.
- Evidence: `command-center.png`, `match-result.png`.
- Concrete fix: Reserve uppercase small-caps for top-level region tags only (`WAR ROOM`). Section panel titles (`Plan Editor`, `Scout Read`, `Week Lock Status`) should be sentence case with the existing slim-bold treatment.
- Acceptance criteria: No more than 3 distinct uppercase labels visible above the fold on any screen.

### L-2. Final Regular-Season Table — W-L-D column far from its values
- Location: Final Regular-Season Table ceremony screen.
- Problem: `W-L-D` and `Pts` and `Elim ±` column headers float to the right edge while club names are far left; nothing rules the columns; scanning across rows is harder than it should be.
- Evidence: `regseason-final.png`.
- Concrete fix: Add a thin column separator or alternating row backgrounds; pull numeric columns ~80px left so they sit closer to the club name column.

### L-3. Postgame headline "Wk 7 Debrief · WAR ROOM" microbreadcrumb is hard to parse
- Location: Top of Postgame.
- Problem: "WAR ROOM · Wk 7 Debrief" prefix above the recap reads like nav crumbs but doesn't link anywhere; combined with the giant recap below, the user's eye is unsure where to land first.
- Concrete fix: Drop the prefix entirely; the page header already says "Command Center" and the recap is self-identifying.

### L-4. `EXPAND ALL 6 MATCHUPS` is shouty and oversized
- Location: Lineup Leverage panel.
- Problem: All-caps button in the middle of body content competes with section titles.
- Concrete fix: Make it a regular-weight underlined text button: "Expand all 6 matchups ⌄".

## Interaction Bugs

### B-1. Load button can be clicked but state never advances; no error feedback
- Action attempted: Click `Load` on `Championship Quest`.
- Expected behavior: Save loads OR an error appears explaining why.
- Actual behavior: URL stays at `/`; save menu stays open; 500 error logged in dev console only.
- Reproduction steps: Fresh open `/` → ensure Show debug saves is on → click Load on `Championship Quest`.
- Evidence: Server traceback in `bmbi3vi33.output`; console error message.
- Concrete fix: See #4.

### B-2. Match Replay header score does not match Postgame Result score
- Action attempted: `Simulate Week` → `View Full Replay`.
- Expected behavior: Replay top-of-screen score = Postgame final score.
- Actual behavior: Postgame says 0–4; Replay header says 6 — 5.
- Reproduction steps: Load `playtest-naive-1779685637909` → Command Center → Lock Plan → Simulate Week → View Full Replay.
- Evidence: `match-result.png`, `replay.png`.
- Concrete fix: See #1.

### B-3. Recap headline narrates a comeback for a shutout loss
- Action attempted: Read Postgame headline.
- Expected behavior: Headline matches result.
- Actual behavior: "Seattle Steelheads were down 2 and clawed it back with 0 catches." appears above "A 0–4 shutout loss with nowhere to hide."
- Reproduction steps: Same as B-2.
- Evidence: `match-result.png`, `postgame.png`.
- Concrete fix: See #2.

### B-4. Ceremony beats fire out of order
- Action attempted: After final regular-season `Simulate Week`, click `Move On →` then `Continue`.
- Expected behavior: Final standings → playoff bracket → playoff matches → champion → awards → records.
- Actual behavior: Champion → final standings → awards → records (no bracket, no playoff matches).
- Reproduction steps: Run any save to end of regular season; click through ceremony.
- Evidence: `champion.png`, `regseason-final.png`, `awards.png`.
- Concrete fix: See #3.

## Design System Consistency Issues

### DS-1. Two competing button styles for primary action
- Pattern: The orange filled CTA (`SIMULATE WEEK`, `CONTINUE`, `MOVE ON`) is the most important affordance. But `LOCK PLAN`, `SCOUT / CONTACT / VISIT` use the same color/weight, so by the time the user gets to a real terminal action, the orange has lost meaning.
- Where it appears: Command Center (Lock Plan), Dynasty Office (recruiting actions), Postgame (Move On), Ceremony (Continue).
- Why it is inconsistent: Same visual treatment for "spend a slot," "lock a decision," and "advance the week." These are three different commitment levels.
- Recommended standardized version: Three tiers — `primary` (filled orange, only for "advance the simulation"), `secondary` (outlined orange, for committing within a week), `tertiary` (text button, for inline picks). `SIMULATE WEEK` and ceremony `CONTINUE` are primary; `LOCK PLAN` is secondary; `SCOUT/CONTACT/VISIT` are tertiary.

### DS-2. Approach vocabulary doubled
- Pattern: Approach axis exists in both Plan Editor and Policy Editor with overlapping vocab.
- Where it appears: Command Center, two panels.
- Why it is inconsistent: See #9.
- Recommended standardized version: One canonical enum (`Aggressive · Balanced · Patient · Defensive`) and one canonical control.

### DS-3. Section headers oscillate between uppercase small caps, sentence case, and title case
- Pattern: `WAR ROOM` (all caps), `Final Regular-Season Table` (title case), `Player condition, role fit, and match readiness` (sentence case), `TEAM ROSTER` (all caps).
- Where it appears: Across every screen.
- Why it is inconsistent: Three case conventions read as three different heading levels visually but they're being used at the same level.
- Recommended standardized version: A typography ramp documented in code. Example: `regionEyebrow` = uppercase small caps; `pageTitle` = title case 32px; `sectionTitle` = title case 18px semibold; `subsectionTitle` = sentence case 14px.

### DS-4. "Show proof" disclosure
- Pattern: A "Show proof" affordance appears in Broadcast Frame and again on Records Ratified.
- Where it appears: Command Center (Broadcast Frame), Records Ratified (each record).
- Why it is inconsistent: Reads like a developer-debug link in player-facing UI. Either it's a real feature (expand to see the math), in which case it deserves a real disclosure pattern (caret, "View evidence"), or it isn't, in which case it should be flagged behind a debug toggle.
- Recommended standardized version: Replace with `<details>` element labeled `Why this counted ⌄` with a proper expand caret.

## Top 15 Codex Tasks

1. **Fix Match Replay / Postgame score parity.** Make both screens read from the same `match_result.final_score` field; add unit test asserting equality across a fixture season. *(Acceptance: #1)*
2. **Make recap selector outcome-aware.** Comeback templates require `winner == player` AND `max_deficit ≥ 2`; loss templates required when player lost; hide `COMEBACK` panel when no comeback occurred. Add tests. *(Acceptance: #2)*
3. **Reorder ceremony beats.** Sequence: Final Regular-Season Table → (Playoff Bracket if implemented) → Season Champion → Awards Night → Records Ratified. Update the "top four advance" subtitle until brackets exist. *(Acceptance: #3)*
4. **Add legacy CoachPolicy migration.** Implement `CoachPolicy.from_legacy_dict` mapping the 8 legacy keys; on irrecoverable failure return 422 with an explicit reason; render that reason inline next to the affected save row. *(Acceptance: #4)*
5. **Default `Show debug saves` to off, and add a "5 debug saves hidden" footer toggle.** Classify by name prefix (`debug-`, `playtest-`, `ux-teardown-`, `test_`). *(Acceptance: #6)*
6. **Enrich save list rows with season/week/record/last-modified.** Extend `/api/saves`; default sort by last-modified desc; add a top-of-list "Continue" button that loads the most recent non-debug save. *(Acceptance: #8)*
7. **Collapse Plan Editor approach buttons into a derived chip.** Make Policy Editor the only interactive approach control; unify vocab. *(Acceptance: #9)*
8. **Set `<title>Dodgeball Manager</title>`** in `frontend/index.html`; optionally make it dynamic with current club + week. *(Acceptance: #10)*
9. **De-duplicate Awards.** If MVP also leads a category, promote runner-up in that category. *(Acceptance: #7)*
10. **Standings → "1 game remaining" wording fix.** Either implement playoffs as real weeks (preferred) or change the header to "Regular-Season Finale · Season Ends Next." Remove "top four advance" copy until brackets exist. *(Acceptance: #5)*
11. **Strip player-facing debug tokens.** Remove `record:career_catches` etc. from Records screen; hide `Show proof` affordances behind a Developer setting OR replace with a real `<details>` "Why this counted" disclosure. *(Acceptance: A11y-1, DS-4)*
12. **Promote panel section labels to `<h3>`.** Convert "LINEUP LEVERAGE", "WEEK LOCK STATUS", "SCOUT READ", etc. from styled divs to headings. Keep visuals. *(Acceptance: A11y-2)*
13. **Fix contrast on secondary text and the orange Continue button.** Target WCAG AA 4.5:1 (or 3:1 for ≥18.66px bold). Add a contrast-scan script to CI. *(Acceptance: A11y-1)*
14. **Sort Match Replay highlights by tick ascending, fix initial state copy, add keyboard shortcuts.** Replace duplicate "Match Start / Match Start." with "Press play to begin." Add `Space/←/→` keybindings with an on-screen hint. *(Acceptance: Match section)*
15. **Codify three-tier button styles and apply.** Primary (advance sim) / Secondary (commit within week) / Tertiary (inline pick). Re-classify `SIMULATE WEEK` + ceremony `CONTINUE` as primary, `LOCK PLAN` as secondary, `SCOUT/CONTACT/VISIT` as tertiary. *(Acceptance: DS-1)*
