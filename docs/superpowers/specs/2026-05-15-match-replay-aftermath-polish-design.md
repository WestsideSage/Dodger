# Match Replay & Aftermath Polish

**Date:** 2026-05-15
**Scope:** `frontend/src/components/MatchReplay.tsx`, `frontend/src/components/match-week/aftermath/*.tsx`, `frontend/src/components/MatchWeek.tsx`

Surgical visual upgrades to the post-match aftermath screen and the match replay viewer. No structural file reorganization, no new components, no backend changes. Every change is styling and presentation within the existing component boundary.

---

## Design Direction

**Aftermath:** Drama-first. The post-match screen should feel like a broadcast moment — a clear climax to the weekly match loop. Each staged reveal gains visual weight without changing the 5-stage structure or the sequenced reveal timing.

**Replay:** Full-court immersive. The court takes the full viewport width; info lives below it in a strip. The existing dual-pane (court-left, sidebar-right) layout is replaced.

---

## Relation to Prior Specs

- Inherits design pillars from `docs/superpowers/plans/2026-05-08-ux-polish/00-MAIN.md` — specifically pillar (a): Match-as-weekly-climax.
- Does not implement subplan 10 (voice library) or subplan 12 (replay commentary) — those remain future work.
- Player positioning fix described in subplan 12 is implemented here as part of the full-court layout change.
- Does not alter backend endpoints, `server.py`, or any Python layer.

---

## Part 1 — Aftermath Components

The aftermath renders 5 stages via `revealStage` in `MatchWeek.tsx`. Stage structure and timing are unchanged. Each component is upgraded in place.

### 1.1 `Headline.tsx` — Stage 0

**Problem:** Bare `<h1>` centered on a plain `dm-panel` background. No context, no visual weight.

**Fix:**
- Replace the plain panel with a full-width gradient banner: `background: linear-gradient(110deg, rgba(249,115,22,0.18) 0%, rgba(249,115,22,0.06) 45%, #0f172a 80%)`.
- Add a bottom border: `1px solid rgba(249,115,22,0.25)`.
- Add an eyebrow line above the headline text: `"WEEK {week} RESULT"` in monospace caps, muted orange (`#f97316` at 80% opacity), `letter-spacing: 3px`, `font-size: 0.65rem`. The week number comes from the `Aftermath` data passed from `MatchWeek.tsx` — `aftermath.match_card?.week` or fall back to the dashboard's `week` field.
- Headline `<h1>` stays as-is in content; change styling to `font-family: Oswald`, `font-size: clamp(1.4rem, 4vw, 2rem)`, `text-shadow: 0 0 30px rgba(249,115,22,0.35)`.
- Add a subtitle line below: `"{winnerName} def. {loserName} · {homeSurvivors} survivors to {awaySurvivors}"` derived from `aftermath.match_card`. Font: Inter, `0.65rem`, `#94a3b8`. Hidden if `match_card` is absent.

**Prop change:** Add optional `matchCard?: Aftermath['match_card']` prop so Headline can render the subtitle. `MatchWeek.tsx` passes `aftermath.match_card` when rendering Stage 0.

### 1.2 `MatchScoreHero.tsx` — Stage 1

**Problem:** Score numbers are undersized for a "broadcast moment" reveal. Winner and loser look nearly identical.

**Fix:**
- Increase `command-score-number` rendered size: target `font-size: clamp(2.8rem, 8vw, 4rem)` (currently ~2rem).
- Winner side: deepen `text-shadow` to `0 0 24px rgba(249,115,22,0.6)` (home) / `0 0 24px rgba(34,211,238,0.5)` (away).
- Loser side: dim the big number to `opacity: 0.45`.
- Winner team name: slightly bolder, increase `font-size` to `1rem`.
- No changes to the animated count-up logic (`useCountUp`) or the overall two-column layout.

### 1.3 `ReplayTimeline.tsx` — Stage 2 (left column)

**Problem:** Section is titled "Replay identity" in the panel header — meaningless to the user. Lane items are unstyled list rows.

**Fix:**
- Rename `dm-panel-title` from `"Replay identity"` to `"Match Flow"`.
- Remove the kicker line `"Match Flow"` that currently duplicates this.
- Each `command-timeline-item` article: add a left-accent border colored by position in list — first item `#f97316`, subsequent items `#334155`. Width `3px`, `border-radius: 0 4px 4px 0`.
- Lane summary (`<strong>`): `font-size: 0.85rem`, `color: #f8fafc`.
- Lane items (`<li>`): `color: #64748b`, `font-size: 0.75rem`.

### 1.4 `KeyPlayersPanel.tsx` — Stage 2 (right column, top)

**Problem:** Stats rendered as plain prose (`"3 eliminations / 2 catches / 94 impact"`). No visual differentiation between stat types.

**Fix:**
- Replace the `statLine()` prose string with colored stat chips inline:
  - Eliminations: orange pill — `background: rgba(249,115,22,0.15)`, `color: #f97316`, text `{n}K`
  - Catches: cyan pill — `background: rgba(34,211,238,0.12)`, `color: #22d3ee`, text `{n}C`
  - Dodges: lime pill — `background: rgba(163,230,53,0.12)`, `color: #a3e635`, text `{n}D`
  - Impact score: keep as muted text after the chips, `color: #475569`, `font-size: 0.65rem`
- Pills: `font-family: monospace`, `font-size: 0.65rem`, `border-radius: 3px`, `padding: 2px 6px`.
- Only render a chip if the count is > 0 (same logic as current `statLine()`).
- `#1` ranked performer: add a subtle `border-left: 2px solid #f97316` to their article card.

### 1.5 `TacticalSummaryCard.tsx` — Stage 2 (right column, bottom)

**Problem:** Plain paragraph on a plain panel — no visual distinction from filler text.

**Fix:**
- Add `border-left: 3px solid rgba(249,115,22,0.5)` to the panel.
- Add `background: rgba(249,115,22,0.04)` tint.
- Add a "TACTICAL READ" kicker label above the paragraph: `font-size: 0.6rem`, `letter-spacing: 2px`, `color: #f97316`, `font-family: monospace`.
- Paragraph: `font-size: 0.8rem`, `color: #94a3b8`, `line-height: 1.5`.

### 1.6 `FalloutGrid.tsx` — Stage 3

**Problem:** Standings arrows (`↑`, `↓`) have no color. Player growth deltas are plain text. Visual density feels uniform — nothing pops.

**Fix:**
- Standings shift rows: wrap `↑` in `<span style="color: #10b981">` and `↓` in `<span style="color: #f43f5e">`. Apply same color to the rank number itself when the direction is clear.
- Player growth delta: if `delta > 0`, color the value `#10b981`. If `delta < 0`, color `#f43f5e`.
- Recruit reactions `interest_delta`: positive → `#10b981`, zero/negative → `#64748b`.
- `FalloutCard` title: upgrade from `dm-kicker` to a slightly larger label with a colored top-border accent (`border-top: 2px solid #1e293b`).

### 1.7 `AftermathActionBar.tsx` — Stage 4

**Problem:** Both buttons have equal visual weight. "Advance to Next Week" is the primary action but looks identical to "Watch Replay".

**Fix:**
- Primary button (`Advance to Next Week`): full-width, `background: #f97316`, `color: #fff`, `border: none`, `border-radius: 8px`, `padding: 12px`, `font-family: Oswald`, `font-size: 0.9rem`, `letter-spacing: 2px`, `box-shadow: 0 0 20px rgba(249,115,22,0.2)`.
- Secondary button (`Watch Replay`): `background: transparent`, `border: 1px solid #334155`, `color: #64748b`, reduced padding. Rendered below the primary, full-width.
- Remove the "Review the replay or move the program..." prose paragraph — the button labels are self-explanatory.
- Remove `dm-panel command-action-bar` classes; replace with a simple `padding: 12px` wrapper.

---

## Part 2 — Match Replay Viewer

All changes are within `MatchReplay.tsx`.

### 2.1 Layout — Full-Court

**Current:** `dm-replay-layout` CSS grid splits court (left) and tabbed sidebar (right) side by side.

**Fix:**
- Remove the `dm-replay-layout` grid wrapper entirely.
- The component renders as a single full-width column: `ScoreHeader` → court → controls → play strip → tabbed section.
- Court SVG: `width: 100%`, `height: auto`, `max-height: 260px`. Remove the `dm-replay-court` width constraint.
- The `dm-replay-sidebar` div becomes a flat section below the controls. Tabs and panel content remain.

### 2.2 Score Header — Slim Strip

**Current:** `ScoreHeader` has significant vertical padding and a winner banner row above the score row. Takes up ~100px.

**Fix:**
- Collapse to a single row: `display: flex; align-items: center; justify-content: space-between; padding: 8px 16px`.
- Left: home team name in orange, `font-size: 0.85rem`.
- Center: `{homeLiving} — {awayLiving}` in Oswald, `font-size: 1.4rem`, winner side in full white, loser side at 50% opacity. "WEEK N" below in muted monospace `0.6rem`.
- Right: away team name in cyan, `font-size: 0.85rem`.
- Winner banner row above: keep but slim — `padding: 4px`, `font-size: 0.7rem`, `letter-spacing: 2px`.
- Removes the large `font-size: 48px` numbers from the header (those belong in the aftermath, not the replay viewer).

### 2.3 Player Positioning — Formation Fix

**Current:** `getFormationPositions()` alternates Y positions top/bottom for all 6 players: players 0,2,4 cluster at `hMid - vGap`, players 1,3,5 at `hMid + vGap`. Results in 3 players along the top edge and 3 along the bottom edge.

**Fix:** Replace the alternating Y layout with a 2-column × 3-row arc formation. Each team gets 2 columns of 3 players spread evenly across court height:

```
Left team (home):
  col-A x = COURT_W/2 - 55   y = [hMid-vGap, hMid, hMid+vGap]   (players 0,1,2)
  col-B x = COURT_W/4        y = [hMid-vGap, hMid, hMid+vGap]   (players 3,4,5)

Right team (away):
  col-A x = COURT_W/2 + 55   y = [hMid-vGap, hMid, hMid+vGap]   (players 0,1,2)
  col-B x = 3*COURT_W/4      y = [hMid-vGap, hMid, hMid+vGap]   (players 3,4,5)
```

Where `vGap = COURT_H / 3.2`.

This keeps each team on their own half, facing center, with a natural depth stagger. If a team has fewer than 6 players (eliminations), the map only fills positions for IDs present — existing elimination logic is unchanged.

### 2.4 Current Play Strip

**Current:** Event description sits in a `<div style="padding: 8px 12px; background: #020617">` with the `EventCard` component.

**Fix:**
- Wrap `EventCard` in a strip: `margin: 0 0 4px`, `border-left: 3px solid` colored by event type (existing `borderColor` logic), `background: rgba(249,115,22,0.06)` for key plays, `background: #0f172a` otherwise.
- `EventCard` label: `font-size: 1rem` (up from `0.94rem`).
- Key play badge: keep existing amber badge.

### 2.5 Tabbed Section

No structural changes. Minor styling:
- Tab bar: `border-bottom: 1px solid #1e293b`, tab labels unchanged.
- `PlayByPlayPanel`: currently renders `proof_events` (not `events`) — this is already the correct data source. No logic change.
- `StatsPanel`: rename the "BOX SCORE" tab label to `"REPORT"` to better match the content (turning point, performers, evidence lanes).

---

## Implementation Order

1. `AftermathActionBar.tsx` — buttons (no logic, pure styling)
2. `Headline.tsx` — gradient banner + eyebrow + subtitle (add `matchCard` prop, update `MatchWeek.tsx` call)
3. `MatchScoreHero.tsx` — number sizing + opacity
4. `TacticalSummaryCard.tsx` — left border + kicker label
5. `KeyPlayersPanel.tsx` — stat chips
6. `ReplayTimeline.tsx` — rename + lane accent borders
7. `FalloutGrid.tsx` — arrow/delta colors
8. `MatchReplay.tsx` — full-court layout (remove dual-pane grid)
9. `MatchReplay.tsx` — slim score header
10. `MatchReplay.tsx` — player positioning fix
11. `MatchReplay.tsx` — play strip accent + tab label rename

---

## What Stays Unchanged

- 5-stage reveal timing and `revealStage` logic in `MatchWeek.tsx`
- All data types in `types.ts` (except the minor `matchCard` prop on `Headline`)
- Backend endpoints and Python layer
- Court SVG structure (dimensions, center line, ball animation, flash effects)
- Auto-play, scrubber, key play jump logic
- `PlayByPlayPanel`, `KeyPlaysPanel` panel content logic

---

## Non-Goals

- Voice library / templated commentary (subplan 10)
- Play-by-play commentary text (subplan 12)
- Mid-match coaching controls
- New top-level tabs or navigation changes
