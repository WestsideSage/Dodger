# Post V8-V10 Frontend Audit — Polish & Hardening Phase

Date: 2026-05-07
Role: Lead Front-End UX Engineer
Phase under review: Polish & hardening following the V8-V10 Dynasty Office blitz (2026-05-06) and the 2026-05-07 "UI Revamp" commit (`042c044`)
Branch: `main`

## Project Trajectory

### WHERE WE WERE
- The V4 UI Polish retro (`docs/retrospectives/2026-04-30-v4-ui-polish.md`) called for shared dashboard primitives, denser tables, scoped Match Day rerenders, and consistent async state surfaces before V5+ feature screens were piled on.
- V5 (Weekly Command Center), V6 (player identity), V7 (replay proof loop), and the V8-V10 Dynasty Office blitz all landed on top of that foundation. Each milestone added a new screen or surface (`CommandCenter.tsx`, `MatchReplay.tsx`, `DynastyOffice.tsx`) without an aligned UI primitives sweep.
- The recent "UI Revamp" commit `042c044` introduced a broadcast-style dark shell ("DM v2") in `index.css`, a left-rail layout in `App.tsx`, and added shared primitives in `components/ui.tsx` (`PageHeader`, `ActionButton`, `Badge`, `StatChip`, `StatusMessage`, `CompactList`, `DataTable`, `RatingBar`, `TendencySlider`).
- The 2026-05-07 content-language pass (`fc84bfd`, retros under `docs/retrospectives/2026-05-07-*-content-update.md`) replaced "future hook"/"V5 slice" copy with diegetic sports-management language in both `dynasty_office.py` and `DynastyOffice.tsx`.

### WHERE WE ARE
- The new component primitives in `components/ui.tsx` are real and used in most screens. Roster, Tactics, Standings, Schedule, News, and DynastyOffice all sit on `useApiResource` + `PageHeader` + `StatusMessage`. The four async-state ergonomics highlighted in the V4 retro are largely absorbed.
- However, the same revamp commit shipped **two confirmed regressions** that this audit flags as Polish-Phase blockers (see Workflow Findings #1 and #2).
- The Dynasty Office surface is functional but visibly leaks developer milestone labels ("V8", "V9", "V10") and "V5 Command Center" into player-facing chrome — directly contradicting the content-language pass that just landed.
- Several screens still hand-roll fetch/loading/error logic instead of using `useApiResource`. The component-debt picture from the V4 retro has improved but is still partial.
- `MatchReplay.tsx` is a 968-line monolith. The V4 retro flagged the rerender scope; the revamp expanded the scope rather than memoizing the boundary.

### WHERE WE ARE GOING
This is the polish-and-hardening phase before V11+. The next round of UI work should:

1. Land the regressions fix in this report (responsive layouts, font-display, leaked dev labels) immediately. They are inherited from the most recent merge.
2. Pull the duplicated card surface and async state plumbing into a small `Tile` + `useApiResource` migration sweep — the cost is small now and grows once V11 starts adding screens.
3. Decide whether `MatchReplay.tsx` keeps its bespoke styling or finally adopts the DM v2 design tokens. The current state is two different products visually.
4. Tighten the Dynasty Office to drop developer-facing chrome (`V8`/`V9`/`V10` badges, "V5 Command Center" right-side header label).

## Workflow Findings

The audit walked the four primary daily workflows and the Dynasty Office, plus the entry path through `SaveMenu.tsx`.

### 1. Hub → Sim → Replay → Acknowledge — broken on desktop ❶ HIGH
- File: [frontend/src/components/Hub.tsx:221](frontend/src/components/Hub.tsx)
- The Match Controls panel and the Club Status panel are wrapped in a `display: grid; grid-template-columns: 1fr` container with `className="lg-two-col-hub"`. The intent is clearly: "stack on mobile, side-by-side on lg+". But `lg-two-col-hub` is **not defined in any CSS file** (verified by Grep across `frontend/`). The result: at every viewport width including 1440+, the Hub renders as a single column with two stacked panels, wasting the right half of the screen.
- This is a regression introduced by the UI Revamp commit. Fix is one CSS rule.

### 2. Command Center weekly loop — same bug, twice ❶ HIGH
- Files: [frontend/src/components/CommandCenter.tsx:137](frontend/src/components/CommandCenter.tsx) and [frontend/src/components/CommandCenter.tsx:266](frontend/src/components/CommandCenter.tsx)
- The Weekly Plan + Staff Room row uses `className="xl-two-col"`; the Lineup Accountability + Tactics Evidence row uses `className="lg-two-col-roster"`. Neither class exists. Both rows render single-column on every screen size. A user on a 27" display sees Weekly Plan, then has to scroll past it to see the Staff Room recommendations the plan was supposed to be paired with. The "Set the program intent, then accept the staff plan" framing in the panel subtitle is undermined by the layout.
- Fix is the same CSS rule pattern as #1.

### 3. Command Center plan saves silently on every change ❷ MEDIUM
- File: [frontend/src/components/CommandCenter.tsx:159-161](frontend/src/components/CommandCenter.tsx) and [frontend/src/components/CommandCenter.tsx:186-188](frontend/src/components/CommandCenter.tsx)
- The Intent and Dev Focus `<select>` `onChange` handlers immediately call `savePlan(...)`. The same panel also exposes an "Accept Recommended Plan" primary button that re-issues the same POST, plus a "Refresh" ghost button. The mental model is unclear: is the plan auto-saved? Is "Accept" required? What does "Refresh" overwrite? A user changing intent twice silently fires two POSTs to `/api/command-center/plan`.
- The selects also do not show a saving state. If `savePlan` errors (e.g., 409 from a stale dynasty state per the post-V8-V10 audit's C3 contract), the select snaps back without explanation.
- Recommendation: pick one model. Either treat selects as committed-on-change and remove "Accept Recommended Plan" (since the plan is the current selection); or treat them as a buffer and require an explicit save click. Show a small `Saved`/`Unsaved`/`Saving` indicator next to the select group either way.

### 4. Dynasty Office → Promise flow leaks developer chrome ❷ MEDIUM
- File: [frontend/src/components/DynastyOffice.tsx:79](frontend/src/components/DynastyOffice.tsx), [:170](frontend/src/components/DynastyOffice.tsx), [:207](frontend/src/components/DynastyOffice.tsx)
- The 2026-05-07 content polish removed "V5 slice" copy from card text but left the `<Badge tone="warning">V8</Badge>`, `V9`, and `V10` badges in the panel headers. These are developer milestone IDs presented as if they were in-fiction labels. The honesty boundary is supposed to be expressed *diegetically* per the content polish report; the badges are the most visible violation.
- Recommendation: either replace with a meaningful diegetic kicker (e.g., "Recruiting · 2026", "Memory Archive", "Front Office") or remove the badges entirely. Their information value is zero for the player.

### 5. App broadcast header leaks "V5 Command Center" ❷ MEDIUM
- File: [frontend/src/App.tsx:211](frontend/src/App.tsx)
- The right side of the broadcast header always renders the literal string `"V5 Command Center"` regardless of which tab is active. This is a stale developer label from before the revamp consolidated the header. It contradicts the just-completed content-language pass and is wrong on every tab except possibly Command Center.
- Recommendation: delete it. If a status pill is wanted there, surface real save context (current season, week, club) — but the StatChip strip in each `PageHeader` already does that.

### 6. Dynasty Office → League Memory is silent when empty ❸ MEDIUM
- File: [frontend/src/components/DynastyOffice.tsx:172-198](frontend/src/components/DynastyOffice.tsx)
- The League Memory panel renders `data.league_memory.records.items.slice(0, 4)` and `data.league_memory.recent_matches.map(...)` directly. At save start (Week 1, no matches), both arrays are empty. The component renders an empty `CompactList` and nothing else — no empty-state copy. The user sees an unexplained blank panel right after a content polish that explicitly added empty-state copy on the Python side.
- Recommendation: render the diegetic empty-state lines from the content polish report (`EMPTY_STATE_RECORDS`, `EMPTY_STATE_AWARDS`, `EMPTY_STATE_RIVALRIES`) when the lists are empty. There's already a `dm-empty-state` class in `index.css` ready to use.

### 7. Tactics "Intent" stat chip is mathematically meaningless ❸ MEDIUM
- File: [frontend/src/components/Tactics.tsx:240](frontend/src/components/Tactics.tsx)
- The page header chip computes `averageIntent` by averaging all 8 `CoachPolicy` slider values. The 8 sliders are different polarities — `target_stars` and `risk_tolerance` measure aggression; `sync_throws` and `catch_bias` measure conservatism. Averaging them produces a number that looks scoreboard-like but means nothing. A team set to "all aggressive" reads ~85%; a team set to "all conservative" reads ~15%; both reads are spurious because half the sliders are inverted in meaning.
- Recommendation: drop the chip, or replace with a per-group indicator (Targeting / Risk / Court Posture) using the `tacticGroups` definition already in the file.

### 8. MatchReplay typography drifts from the design system ❸ MEDIUM
- File: [frontend/src/components/MatchReplay.tsx](frontend/src/components/MatchReplay.tsx)
- The component hardcodes `fontFamily: 'Oswald, sans-serif'` and `fontFamily: 'JetBrains Mono, monospace'` in 30+ places instead of using `var(--font-display)` and `var(--font-mono-data)`. The DM v2 token is `--font-display: 'Bahnschrift SemiBold', 'Arial Narrow', sans-serif;` — but `index.html` loads Oswald (and not Bahnschrift) via Google Fonts. So:
  - On Windows, `--font-display` resolves to Bahnschrift; MatchReplay uses Oswald. **Two different display fonts on the same screen.**
  - On macOS/Linux, `--font-display` falls back to Arial Narrow → sans-serif; MatchReplay uses the loaded Oswald. Even more visual divergence.
- Recommendation: this audit fixes the token to `Oswald` (the actual loaded font) so the rest of the app catches up to MatchReplay rather than the reverse — that's the smallest change. Then in a follow-up, MatchReplay should adopt the CSS variable.

### 9. Offseason narrative is rendered in a `<pre>` tag ❹ LOW
- File: [frontend/src/components/Offseason.tsx:101](frontend/src/components/Offseason.tsx)
- Beat narrative comes back as prose sentences but is rendered with `<pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono-data)' }}>`. Mono-spaced prose at 0.875rem is slow to read; the offseason ceremony copy was rewritten in the content pass to be *prose*, not column-aligned data. The `pre` styling is a leftover from a debug-output era.
- Recommendation: switch to a `<div>` with normal body font.

### 10. MatchReplay fixed `flex: 0 0 60%` left pane ❹ LOW
- File: [frontend/src/components/MatchReplay.tsx:857](frontend/src/components/MatchReplay.tsx)
- The replay's left pane (court + controls) is hardcoded to 60% of its container, with the right pane taking the rest. On a 1280-wide laptop with the 13rem left nav, the content area is ~1080px and the right pane gets ~430px — fine. On narrower laptops with the nav expanded, the right tab content (PROOF/KEY PLAYS/REPORT) becomes cramped and the dice-roll/odds chips wrap awkwardly. No mobile breakpoint at all.
- Recommendation: defer until V11 or later. Document only.

## Component Debt

- **Async state migration is partial.** `useApiResource` is used by Roster, Tactics, DynastyOffice, Standings, Schedule, News. **Hub, CommandCenter, Offseason, MatchReplay, and SaveMenu still hand-roll** `fetch`/`then`/`catch`/`finally` with their own loading and error state. CommandCenter has *two near-identical* fetch blocks (the `useEffect` at line 46-68 and the `load(...)` helper at line 30-44) that diverge only by the cancel guard. This is direct V4-retro debt that the revamp left behind.
- **Card-tile pattern is repeated inline ~12 times.** The same `borderRadius: '4px', border: '1px solid #1e293b', background: '#0f172a', padding: '0.75rem'` block appears in DynastyOffice (prospect cards, candidate cards, current-staff tile), CommandCenter (department tiles, post-week dashboard lanes, lineup tiles), Hub (sim tiles), and Offseason (action panel). Promote to a `Tile` primitive in `ui.tsx`. This will make the next milestone's screens cheaper to build and pull a meaningful chunk of inline styles out of feature components.
- **Two slider implementations exist.** `ui.tsx::TendencySlider` is exported and looks like it should be the canonical primitive, but `Tactics.tsx::TacticSlider` is a near-duplicate with a per-tendency `valueColor` prop that the canonical version doesn't take. Either extend the canonical primitive to accept `valueColor` and delete the local copy, or formally tier them.
- **Heavy inline styles in CommandCenter and DynastyOffice.** Most layouts use 12-30 line inline-style objects per element. The intent is local and that's fine in isolation, but the pattern duplicates `flex` + `gap` + `borderRadius` constants that already exist in `index.css`. After the `Tile` primitive lands, a second pass should pull the common border/background combos onto utility classes.
- **MatchReplay is 968 lines and unsplit.** `CourtView`, `ScoreHeader`, `ProofPanel`, `StatsPanel`, `KeyPlaysPanel`, and `EventCard` are defined inline in the same file. `CourtView` and `StatsPanel` are already `memo`-wrapped, but the top-level component holds `eventIndex` and rerenders the entire subtree on every step. The V4 retro flagged this; the revamp grew the file by ~570 lines without splitting it.

## Friction Audit

- **Refresh button overuse.** Hub and CommandCenter both expose visible "Refresh" ghost buttons. The data they fetch is cheap and already updates after every action. The buttons add visual noise and signal "this might be stale" — which it shouldn't be.
- **Save Menu lacks playable empty-state.** SaveMenu shows an empty list with a "Start New Game" CTA when no saves exist (good), but during the loading window between mount and first response, there's a "Loading saves…" line that flashes. Two-frame flash is fine; in low-network conditions it persists. A `dm-skeleton` row already exists in `index.css` and would feel more deliberate.
- **Tactics dirty-state is implicit.** The header pill toggles between `Saved` and `Unsaved` only after a slider event. Right after a fresh load, the pill says `Saved` (correct). After a single ArrowRight tap on a slider it says `Unsaved` (correct). But the V4 retro's QA finding about keyboard-driven changes not exposing Save Tactics — verified resolved here on inspection — should get a Playwright regression test in the next polish slice.
- **Save Menu "Start Career" submit button** in `SaveMenu.tsx` is positioned below all form fields with no error inline-recovery. If the create call returns 400 (e.g., name conflict), the user sees a small `<p>` with the message but the submit button stays at "Creating…" until the user changes the name. The button should reset to "Start Career" on error.
  - Confirmed in code: `setCreating(false)` is only called in the catch branch (good), so this is fine — strike this finding.

## Rendering / State Performance

- **CommandCenter rerenders on every keystroke during select changes.** Each select change writes `selectedIntent`/`selectedDevFocus`, fires `savePlan`, which fetches and writes `data`. Three rerenders per change minimum. Acceptable for a single click; problematic if a "save plan" click ever becomes part of a tighter loop.
- **DynastyOffice keys lists by player_id and candidate_id (good)**, but the `interest_evidence` and `effect_lanes` strings are used as keys (line 103, 264). If two evidence lines are identical, React will warn. Low risk in practice, but the data shape doesn't guarantee uniqueness — server-side this should pair an explicit ID.
- **Hub state concentration unchanged from V4 retro.** Same observation, same recommendation.
- **MatchReplay rerender scope unchanged from V4 retro.** The revamp added more inline subcomponents but did not split state. The component will be harder to optimize as the file grows; do the split before any further proof-loop content lands.

## Responsive / Accessibility Notes

- **Three desktop two-col layouts collapsed to one column** (see Workflow Findings #1, #2). Fixed by this audit.
- **No mobile/narrow-viewport styling for the app shell.** `dm-left-nav` is `13rem` fixed width; below ~720px the left nav consumes a third of the viewport with no collapse. The V3/V4 product target was desktop, but the recent SaveMenu form does work on narrow widths.
- **Tab-key navigation works** through `dm-nav-item` (verified by inspection), but `outline` is set on `tactic-range` only. Buttons in `ActionButton` rely on the browser's default focus ring against a near-black background, which is hard to see. Adding a `:focus-visible` outline to `ActionButton` would help keyboard users without changing mouse-driven UX.
- **Colour-only state on schedule rows.** `LeagueContext.tsx::scheduleStatusBadge` uses badge colour to distinguish Final/Live/Scheduled. Colour-blind users have only the text label to fall back on — that's acceptable since the badge text is also legible, but a leading dot or icon would harden it.

## Pre-Next-Phase Polish (ordered)

These are the small fixes that materially de-risk the next milestone. Items 1-3 are landed by this audit's code edits; 4-7 are recommended for the next slice.

1. **Add the missing responsive utility classes** (`lg-two-col-hub`, `lg-two-col-roster`, `xl-two-col`) to `index.css`. Restores three desktop layouts. **(this audit)**
2. **Align `--font-display` with the actually loaded Oswald font** so the rest of the app stops drifting from the MatchReplay surface across platforms. **(this audit)**
3. **Remove the leaked "V5 Command Center" developer label** from `App.tsx`'s broadcast header. Honors the diegetic content boundary the recent content polish established. **(this audit)**
4. **Replace `V8`/`V9`/`V10` badges in `DynastyOffice.tsx`** with diegetic kickers or remove. (Next slice — touches three lines but should land with the rest of the Dynasty Office cleanup.)
5. **Add empty-state rendering to `DynastyOffice.tsx::League Memory`** using the `EMPTY_STATE_*` strings already designed in the content update report. (Next slice.)
6. **Migrate `Hub.tsx`, `CommandCenter.tsx`, and `Offseason.tsx` to `useApiResource`.** Each migration is ~30 line diff and removes a hand-rolled async state machine.
7. **Promote the inline card-tile pattern to a `Tile` primitive** in `components/ui.tsx`. Touches DynastyOffice, CommandCenter, Hub, Offseason. ~80 line diff total, removes ~250 lines of inline styles.

After items 1-7 are in, the app surface will be ready for V11+ feature additions without inheriting a layer of polish debt.

## Verification of This Audit's Code Changes

- Frontend: `cd frontend && npm run lint && npm run build` — see Verification section in this audit's commit message.
- Code edits sit only in `frontend/src/index.css` and `frontend/src/App.tsx`. No domain logic, no API contracts, no test changes. Match outcomes, golden logs, and the V8-V10 promise/staff-market flow are untouched.
