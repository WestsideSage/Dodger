# UX Polish Initiative — Main Orientation Plan

> **For agentic workers (Codex / orchestrator):** This is the master orientation contract. You do **not** implement subplans yourself from this file — you read it, then dispatch a subagent per subplan and verify their work matches the principles, acceptance criteria, and dependency graph defined here. Use `superpowers:subagent-driven-development` to dispatch.
>
> **For subagents:** Read this file first to internalize the design pillars and cross-cutting principles, then implement only your assigned subplan. Do not change scope. If you encounter a conflict between this file and your subplan, surface it to the orchestrator — do not silently resolve.

**Goal:** Transform the Dodgeball Manager web app from a "menu-clicking simulator" into a paced, dramatic sports-management game with clear visual hierarchy, written voice, and a felt long-term progression arc.

**Architecture:** A staged three-wave initiative — Bones (IA rework) → Hierarchy (per-page redesigns) → Soul (voice, animation, ceremonies, new game flow). Waves ship sequentially. Within a wave, subplans are mostly parallelizable; the dependency graph below specifies exactly which.

**Tech Stack:** React 18 + TypeScript + Vite frontend (`frontend/src/components/*.tsx`) backed by FastAPI Python (`src/dodgeball_sim/server.py` + sibling modules).

---

## Design Pillars (every subplan must serve at least one)

- **(a) Match-as-weekly-climax.** The match is the dramatic peak of every in-season week. Every screen and action either builds anticipation for it, IS it, or processes its consequences.
- **(b) Recruit-and-grow as season-long arc.** Watching recruits cook into stars across multiple seasons is the long-tail motivator. Growth must be *visible* — at point of recruitment, on the Roster, in match aftermath, and in History.

If a feature serves neither pillar, it should not exist.

---

## Cross-Cutting Principles (binding on every subplan)

1. **Information hierarchy: every screen answers three questions at a glance** — *what's at stake right now*, *what should I do next*, *what just happened*. If a player has to interpret a wall of cards to figure out their next move, the screen is broken.
2. **One primary action per screen.** Visual weight follows it. Other actions are demoted typographically.
3. **Show, don't surface raw sim values.** Internal floats (potential, fit_score, etc.) are NEVER displayed numerically. Use tier labels, confidence stars, deltas with arrows, sparklines.
4. **Written voice over debug strings.** Three places where templated prose replaces flat data: pre-match framing line, play-by-play commentary, post-match Aftermath headline. See subplan 10.
5. **Mixed gating for player choice.** Hard gates only for things the sim literally needs to run (lineup, tactic). Everything else is optional with smart defaults via "Accept Recommended Plan" — which must show a diff toast of what changed.
6. **Reveal in sequence at emotional peaks.** Aftermath blocks unfold over ~5 seconds; offseason ceremonies are paced reveals; sim transitions are never instant blinks (Fast Sim still gets ≥0.8s).
7. **Departed content persists.** Graduated players, awards, broken records — all auto-write into Program History. The system writes the game's own history without manual logging.
8. **Tabs are scarce. Sub-tabs handle internal complexity.** The top-level IA is locked at 4 tabs (see below); deeper navigation lives as sub-tabs *within* a top-level tab.

---

## Locked Information Architecture

**Top-level tabs (4, locked):**

| Tab | Component file | Job |
|---|---|---|
| **Match Week** | `frontend/src/components/MatchWeek.tsx` (renamed from `CommandCenter.tsx`) | State-driven home screen: pre-sim, post-sim, offseason. The (a) pillar lives here. |
| **Roster** | `frontend/src/components/Roster.tsx` | Development theater. The (b) pillar's "watching them cook" surface. |
| **Dynasty Office** | `frontend/src/components/DynastyOffice.tsx` | Sub-tabs: `Recruit` (verb set + slot economy) and `History` (My Program / League toggle). |
| **Standings** | `frontend/src/components/LeagueContext.tsx` (Standings export only — Schedule/NewsWire are deleted) | League context with full column names and recent-matches sidebar. |

**Killed (no longer top-level tabs):** Hub, Tactics-as-tab, Schedule-as-tab, News-as-tab. Their content is either deleted, redistributed, or folded into surviving surfaces (see subplan 01).

---

## State Model: Match Week's Three Modes

`MatchWeek.tsx` renders ONE of three modes based on save-state:

| Mode | When | Primary content | Primary action |
|---|---|---|---|
| **pre-sim** | In-season, before the week's match has been simulated | Hero matchup card (top 50%) + weekly checklist (bottom-left 60%) + program status strip (bottom-right 40%) | `Sim Match` button on the matchup card with Fast/Normal/Slow speed toggle |
| **post-sim** | In-season, after the week's match has been simulated | Aftermath blocks revealing in sequence: Headline → Match Card → Player Growth → Standings Shift → Recruit Reactions | `Advance to Next Week` |
| **offseason** | Save state in `OFFSEASON_STATES` | Offseason checklist (routine weeks) OR full-screen ceremony takeover (5 specific beats) | Varies by beat |

The transition from pre-sim → match replay → post-sim is a **single continuous animation** (subplan 11), never a page reload.

---

## Locked Hard Gates and Slot Economy

**Pre-sim mode hard gates** (Sim button disabled until met):
- Valid 6-player lineup
- Tactic selected (any tactic)

**Optional checklist items** (not gated, included in Accept Recommended):
- Scout opponent
- Set match intent (Win Now / Develop / Rest Starters)
- Pre-match team talk
- Send recruit contacts (consumes Dynasty Office slots)

**Recruiting weekly slot budget** (subplan 08):
- Default: 3 Scout slots, 5 Contact slots, 1 Visit slot per week
- Modified by Program Credibility tier (gates slot count)
- Modified by Staff hires (e.g., Recruiting Coordinator: +1 Scout slot)
- Active Promises capped via existing `max_active_promises`
- Pitch Angle: locks for the season once chosen
- Sign action: only available on Signing Day ceremony

---

## Locked Player Display Rules (subplan 07)

**Potential** is NEVER shown as a number. Display as:

```
Potential: High ★★★★☆
```

Where `High`/`Elite`/`Solid`/`Limited` is the tier label and stars (1-5) are scouting confidence. Confidence increases with player age and applied scouting passes.

**Stat abbreviations are banned in the Roster theater view.** Use full words: `Throwing`, `Catching`, `Dodging`, `Stamina` (and any others the sim exposes). Compact toggle may use abbreviations.

**Per-player row content (theater view):**
```
[#7] Marcus Reyes              Senior · Captain · Newcomer
     Throwing 84 ↑3   Catching 71 ↑1   Dodging 88 ↑5   Stamina 79 →
     Potential: High ★★★★☆     OVR 80 (↑4 this season)
     [Sparkline]                Status: Starter
```

**Header strip** (replaces the existing 3-number corner card):
`Avg Age · Avg OVR · OVR Trend ↑ · Players Improving (12/16) · Dev Focus [chip]`

Dev Focus chip lives here (relocated from `MatchWeek` per subplan 03).

---

## Subplan Index, Acceptance Criteria, and Dependency Graph

Subplans are listed in dependency order within each wave. **Parallel** = can run concurrently with siblings; **Serial** = blocks subsequent siblings.

### Wave 1 — Bones (IA rework, ships first)

| # | Subplan | File | Parallel? | Acceptance criteria |
|---|---|---|---|---|
| 01 | Cut redundant tabs | `wave-1-bones/01-cut-redundant-tabs.md` | Serial (must run first in wave) | Hub, Tactics, Schedule, News removed from `tabs` array in `App.tsx`. `Hub.tsx` and `Tactics.tsx` deleted. `Schedule` and `NewsWire` exports removed from `LeagueContext.tsx`. App still loads, no broken routes, frontend build passes, Python tests pass. |
| 02 | Build Match Week shell (state-driven) | `wave-1-bones/02-build-match-week-shell.md` | Serial (after 01) | `CommandCenter.tsx` renamed `MatchWeek.tsx`. Component renders one of three modes based on save state. Each mode is a stub with placeholder content + correct primary CTA. Mode selection logic verified by tests. |
| 03 | Relocate Dev Focus to Roster | `wave-1-bones/03-relocate-dev-focus.md` | Parallel with 04 (after 02) | `dev_focus` setting removed from Match Week / Command Center plan UI. Editable Dev Focus chip surfaces on Roster header strip. Backend `/api/command-center/plan` still accepts dev_focus (for now); a new `/api/roster/dev-focus` endpoint or extension routes the setting from Roster. Existing Python tests pass; new test covers Roster setting Dev Focus. |
| 04 | Relocate department orders to Dynasty Office | `wave-1-bones/04-relocate-department-orders.md` | Parallel with 03 (after 02) | Department orders no longer rendered on Match Week. A "Program Priorities" panel renders on Dynasty Office's `Recruit` sub-tab placeholder area, allowing the 6-department orders to be set. Existing endpoint preserved. New test covers setting orders from Dynasty Office. |

**Wave 1 ships when:** all four subplans merged, frontend build clean, Python suite green, manual smoke test confirms (a) the 4-tab IA, (b) Match Week renders the right mode for current save state, (c) Dev Focus and department orders are settable in their new homes.

### Wave 2 — Hierarchy (per-page redesigns)

Authored after Wave 1 ships. Each subplan begins as a stub in `wave-2-hierarchy/` containing only its acceptance criteria from this section.

| # | Subplan | Parallel? | Acceptance criteria |
|---|---|---|---|
| 05 | Hero matchup card + checklist + program status strip (Match Week pre-sim) | Serial (foundational for wave) | Pre-sim mode renders top-50% hero matchup card with team logos, records, written framing line (template stub OK in Wave 2; voice library lands in subplan 10), key matchup, last meeting, Sim button, speed toggle. Bottom: 60/40 split for checklist (with required items gated, optional items showing slot costs) and program status strip. `Accept Recommended Plan` shows a diff toast listing what changed. |
| 06 | Aftermath blocks with sequenced reveal (Match Week post-sim) | Parallel with 05 | Post-sim mode renders 5 stacked blocks (Headline, Match Card, Player Growth, Standings Shift, Recruit Reactions), each fading in with a stagger. Skippable via space/click. Player Growth and Recruit Reactions blocks pull real sim data. `Advance to Next Week` is the single primary CTA. |
| 07 | Roster theater redesign + tier-stars potential | Parallel with 05/06 | Roster default mode is theater view (rich per-player rows with deltas, sparklines, full attribute names). Compact toggle present. Potential is `Tier + ★` only. Header strip implements `Avg Age · Avg OVR · OVR Trend · Players Improving · Dev Focus chip`. Newcomer is a name-line tag; Status shows role only (no redundancy). |
| 08 | Dynasty Office Recruit sub-tab + verb set + slot economy | Parallel with 05/06/07 | `DynastyOffice` has sub-tab nav: `Recruit` (default) / `History` (stub). Recruit sub-tab implements 6 verbs (Scout, Contact, Visit, Make Promise, Pitch Angle, Sign). Weekly slot budget rendered (with current/max). Credibility strip shows tier + slot grants + perks. Staff strip shows current staff with effects; Staff Market opens as a modal. Scouting reveals attributes incrementally (band → stat → personality across passes). |
| 09 | Standings polish | Parallel | Full column names (`Wins`, `Losses`, `Ties`, etc., not `W`/`L`/`T`). Recent matches sidebar absorbs old NewsWire-style content. Click-through rows deep-link to a (placeholder ok) team detail; team detail finalized in subplan 14. |

**Wave 2 ships when:** all five subplans merged, every screen has clear visual hierarchy per the cross-cutting principles, Accept Recommended Plan diff toast works, manual smoke confirms a player can complete a match week without confusion.

### Wave 3 — Soul (voice, animation, ceremonies, new game)

Authored after Wave 2 ships.

| # | Subplan | Parallel? | Acceptance criteria |
|---|---|---|---|
| 10 | Templated voice library | Serial (others depend on it) | Three writer modules in `src/dodgeball_sim/`: `voice_pregame.py` (matchup framing line), `voice_playbyplay.py` (replay commentary), `voice_aftermath.py` (Aftermath headline). Each ships ≥30 templates keyed on relevant features (rivalry, expectation, score margin, streak break, injury status). Frontend surfaces consume the new endpoints. Existing data flows unchanged; only the rendering text upgrades. |
| 11 | Sim transition animation | Parallel with 12-15 (after 10) | Clicking Sim Match initiates a non-skippable animation: pre-sim panel slides up (~300ms), match replay takes screen, post-match 1s freeze, court fades, Aftermath fades in. Fast Sim still gets a ≥0.8s "results coming in" beat (no instant blink). Works for both in-season and offseason advance actions where applicable. |
| 12 | Match Replay commentary + player positioning fix | Parallel (after 10) | "Proof" tab killed; replaced with "Play-by-Play" tab rendered from `voice_playbyplay.py`. Player dot positioning rewritten so each team clusters on its own half (left/right), facing center (NOT 3-top + 3-bottom per team). Three speeds: Fast (skip viz), Normal (sped commentary + viz), Slow (real-time per-tick). Speed selectable before AND during match. |
| 13 | Build-From-Scratch new game flow | Parallel | `SaveMenu` adds two paths: `Take Over a Program` (current flow + optional rename/recolor + coach backstory tile) and `Build a Program From Scratch` (full custom identity → coach step → starting recruitment mini-game). Custom build's starting roster is deliberately weaker than preset clubs. Mini-game uses the same recruiting verb set from subplan 08 as a tutorial. |
| 14 | History sub-tab (My Program + League toggle) | Parallel | `DynastyOffice` History sub-tab gains a `My Program / League` toggle. My Program: "How it started ↔ How it finished" hero cards, milestone timeline, alumni lineage with peak stats, banner shelf. League: program-by-program directory (each clickable to open their My-Program-style view), dynasty rankings, all-time records, Hall of Fame, rivalries directory. All entries auto-generated from sim event history. Departed players persist forever in alumni lineage. |
| 15 | Offseason ceremony takeovers | Parallel | Five full-screen ceremony surfaces, each replacing the routine offseason checklist when their beat fires: `Awards Night`, `Graduation`, `Coaching Carousel` (skipped if no movement), `Signing Day`, `New Season Eve`. Each is paced reveal content (skippable). Each writes its outcomes into History (subplan 14) automatically. |

**Wave 3 ships when:** all six subplans merged, manual smoke test of one full season cycle confirms voice templates render correctly across all three writer surfaces, sim transitions never blink, ceremonies fire on the correct save-state beats, Build-From-Scratch new game completes a recruit-your-starting-10 mini-game and lands the player on Match Week.

---

## Verification Rubric (orchestrator runs this between subplans and at wave boundaries)

When a subagent reports a subplan complete, the orchestrator verifies:

1. **Build & test gates green.**
   - `cd frontend && npm run build` exits 0
   - `python -m pytest -q` exits 0
   - Subplan-specific tests added and passing
2. **Acceptance criteria match.** Re-read the subplan's row in this file. Each bullet of the acceptance criteria is satisfied by the diff. If not, send the subagent back with a specific delta.
3. **Cross-cutting principles upheld.** Specifically check:
   - No internal sim float (potential, fit_score, etc.) leaked numerically into UI
   - No new top-level tab introduced
   - Hard gates limited to lineup + tactic (no homework gates added)
   - Any new player-facing copy uses templated voice (Wave 3+) or is clearly stubbed for replacement
4. **No scope creep.** Diff stays within the subplan's declared file boundaries (allowed exceptions: minor type updates in `frontend/src/types.ts` to support new payload fields). Cross-surface changes that weren't in the subplan get rejected.
5. **Frequent commits.** Subagent should have committed after each TDD red-green cycle, not in one mega-commit. If only one commit lands, ask for a re-do with proper TDD cadence.

If verification fails, the orchestrator sends the subagent a specific list of deltas to fix. Subagent does NOT mark the task complete until verification passes.

---

## Wave Authoring Protocol (for the orchestrator)

When Wave 1 merges:
1. Re-read this file's Wave 2 section.
2. For each Wave 2 subplan stub, invoke `superpowers:writing-plans` with the stub's acceptance criteria + the now-merged Wave 1 reality (file paths, components, routes) as input.
3. The skill produces full task-by-task content, written into the stub file.
4. Repeat for Wave 3 after Wave 2 ships.

This deferred authoring is intentional. Pre-detailing all 15 subplans up front would lock in assumptions that get falsified by Wave 1's actual implementation. The MAIN doc holds the design contract; the subplans hold the perishable implementation detail.

---

## Files-Touched Summary (for parallelization safety)

| Surface | Files |
|---|---|
| Top-level shell | `frontend/src/App.tsx`, `frontend/src/types.ts` |
| Match Week | `frontend/src/components/MatchWeek.tsx` (renamed), `src/dodgeball_sim/command_center.py`, `src/dodgeball_sim/server.py` |
| Roster | `frontend/src/components/Roster.tsx`, `src/dodgeball_sim/server.py` (Roster endpoints) |
| Dynasty Office | `frontend/src/components/DynastyOffice.tsx`, `src/dodgeball_sim/dynasty_office.py`, `src/dodgeball_sim/recruitment.py`, `src/dodgeball_sim/scouting.py`, `src/dodgeball_sim/scouting_center.py`, `src/dodgeball_sim/server.py` |
| Standings | `frontend/src/components/LeagueContext.tsx` (Standings export only after Wave 1) |
| Match Replay | `frontend/src/components/MatchReplay.tsx`, `src/dodgeball_sim/replay_proof.py`, `src/dodgeball_sim/voice_playbyplay.py` (Wave 3 new) |
| Save / New Game | `frontend/src/components/SaveMenu.tsx`, `src/dodgeball_sim/persistence.py`, `src/dodgeball_sim/career_setup.py`, `src/dodgeball_sim/identity.py` |
| Voice library (Wave 3) | `src/dodgeball_sim/voice_pregame.py`, `voice_playbyplay.py`, `voice_aftermath.py` |
| Ceremonies (Wave 3) | `src/dodgeball_sim/offseason_ceremony.py` (existing, expand), new ceremony components in `frontend/src/components/ceremonies/` |
| History (Wave 3) | `frontend/src/components/DynastyOffice.tsx` (History sub-tab additions), `src/dodgeball_sim/records.py`, `src/dodgeball_sim/career.py`, `src/dodgeball_sim/meta.py` |

Subagents working in parallel must not edit the same file. The orchestrator enforces this by reading subplan declared file boundaries before dispatch.

---

## Glossary

- **OVR** — Overall rating (composite player score). Acceptable as an abbreviation in compact views; spelled out elsewhere.
- **Dev Focus** — Season-long player-development priority (Balanced / Youth Acceleration / Tactical Drills / Strength And Conditioning). Lives on Roster header strip.
- **Pitch Angle** — Season-locked recruiting message identity (Develop / Win / Culture / Playing Time). Affects fit_score for all prospects.
- **Program Credibility** — Tiered reputation that gates the recruiting weekly slot budget. Has a grade and an evidence list.
- **Aftermath blocks** — The 5 stacked surfaces that reveal in sequence after a match simulates.
- **Three speeds** — Fast (no viz, ≥0.8s transition), Normal (sped commentary + viz), Slow (real-time per-tick).
