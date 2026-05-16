# Aftermath Screen Redesign

**Date:** 2026-05-15
**Status:** Approved

## Problem

The post-match aftermath screen has strong top-half energy (scoreboard is the best part) but falls apart below it. Issues: title duplication ("Command Center" × 2), result stated three times before the scoreboard even settles, Match Flow buried in a tiny carousel nobody notices, left column dead zone after the timeline, Tactical Read floating disconnected, stat chips cryptic, empty fallout section kills page energy, orange accent doing all emotional labor.

## Goal

Fix information density and page rhythm. Top half works; make the bottom half earn its space.

---

## Architecture

Four stacked sections in this order:

```
┌──────────────────────────────────────────────┐
│  PageHeader: WAR ROOM · Week N Debrief       │
├──────────────────────────────────────────────┤
│  Headline (punchy line + context line)       │
├──────────────────────────────────────────────┤
│  Scoreboard (unchanged — best emotional beat)│
├──────────────────────────────────────────────┤
│  Match Flow (full-width hero)                │
├──────────────────────────────────────────────┤
│  Tactical Read │ Key Performers              │
├──────────────────────────────────────────────┤
│  Week Fallout (collapses if all empty)       │
├──────────────────────────────────────────────┤
│  CTA Bar: Watch Replay │ Advance to Next Week│
└──────────────────────────────────────────────┘
```

---

## Section 1: Page Header & Headline

### Page Header
- Eyebrow: `WAR ROOM` (unchanged)
- Title: `Week N Debrief` — where N is `activeResult.dashboard.week`
- Removes the duplicate "Command Center" title that appeared in both the global nav and the page header

### Headline
Two lines, not one bloated sentence:
```
They drop this one — a loss that stings.
A 6–0 shutout leaves no room for excuses.
```
- Line 1: existing `aftermath.headline` text (keep as-is, it's already punchy)
- Line 2: one contextual sentence composed client-side from `match_card` data (score margin, shutout, comeback, etc.). Must be short (one clause). Not appended to line 1. No backend change needed.
- The subtitle below the headline (`"Lunar Syndicate def. Iron Owls · 6 survivors to 0"`) is **removed** — the scoreboard immediately below makes it redundant.

---

## Section 2: Scoreboard

Unchanged. `MatchScoreHero` stays exactly as-is. It is the best part of the page. Do not touch it.

---

## Section 3: Match Flow (Hero)

Replaces `ReplayTimeline` carousel with a full-width expanded timeline.

### Behavior
- No carousel, no arrows, no dot indicators
- All meaningful events shown in order (not every raw sim tick — backend `lanes` data already groups into phases/beats; only include beats with a description worth showing)
- `maxHeight` with internal scroll when event list is tall
- Subtle top/bottom fade mask at scroll edges (signals scrollability; must be visible enough to notice, not invisible)
- Responsive max-height:
  - Desktop ≥ 1024px: `520px–600px`
  - Tablet 768–1023px: `480px`
  - Mobile < 768px: no internal scroll; events flow vertically at full height

### Event Card Structure
Each event is a card containing (left to right):
1. **Numbered badge** — styled circular disc (not unicode ①②; use CSS `::before` or a `<span>` with a circle shape), 1-based, muted color
2. **Phase label** — small uppercase tag: `EARLY` / `MID` / `LATE`
3. **Event description** — full readable sentence, main text weight
4. **Score chip** — inline, right-aligned: e.g. `6–3`
5. **Impact label** — colored tag: `DECISIVE` (orange), `MOMENTUM` (blue), `ROUTINE` (muted grey)

### Section Heading
- Title: "How It Unfolded"
- Sub-label: event/phase count (e.g. "7 key moments")

---

## Section 4: Analysis Row

Two cards in a CSS grid row below Match Flow.

### Grid
```css
grid-template-columns: 1.15fr 0.85fr;
gap: 1.25rem;
```
Tactical Read gets slightly more width because its text runs longer. If text is consistently short, this can be `1fr 1fr` — keep it flexible.

### Tactical Read (left card)
- Heading: "Tactical Read"
- Body: `turning_point` text from `replayForMatch.report.turning_point`
- Footer (small, quiet): "Based on [Phase] · Lane [N]" — derived from `evidence_lanes`. One line. No second paragraph.
- Accent color: **neutral** (not orange — orange discipline)

### Key Performers (right card)
- Heading: "Key Performers"
- Each player row, same structure every time:
  1. Circular rank badge — filled disc, color = orange for player club, muted blue for opponent
  2. Player name (bold)
  3. Team tag — **"Your Club"** rendered with orange solid background so it stands out from grey position tags. Opponent name uses muted grey tag.
  4. Stat chips — expanded labels, never cryptic shorthand:
     - `5C` → `5 Catches`
     - `1D` → `1 Dodge`
     - `impact` → `Impact Score N`
     - Abbreviate on small screens if needed (e.g. `Ctch`, `Dgd`) but never single letters
  5. Impact score chip last

---

## Section 5: Week Fallout

### Naming
Renamed from "What Your Week Caused" → **"Week Fallout"**

### Collapse Rule
If all three sub-sections are empty (`player_growth_deltas.length === 0 && standings_shift.length === 0 && recruit_reactions.length === 0`), the entire section does **not render**. No empty state card, no "No notable fallout" message.

### Partial Empty
If only some sub-sections have data, render only the non-empty cards. Use `grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))` so cards redistribute naturally without gaps.

### Sub-section Names (unchanged)
- Who Grew
- Standings Shift
- Prospect Pulse

---

## Section 6: CTA Bar

### Layout
- Desktop: side-by-side in one row, right-aligned
- Mobile: stacked, full-width
- Attached directly after Week Fallout (or after Analysis Row if Fallout collapses) — no floating dead space

### Buttons
- **Advance to Next Week** — primary, orange fill, large. Unchanged.
- **Watch Replay** — solid secondary button: dark fill (e.g. `#1e1e1e` or near-black), white text, same height as primary, narrower. Not a ghost/outline. Feels like a real action but clearly subordinate to Advance.

---

## Orange Accent Discipline

Orange is reserved for **exactly these uses**:
- Advance to Next Week CTA button
- Player club rank badge (circular disc)
- "Your Club" team tag background
- `DECISIVE` impact label on timeline events
- Winner score box in scoreboard (unchanged)

Orange is removed from:
- Tactical Read card border / accent
- Section headings and dividers
- Decorative elements that don't signal action or player-club identity

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/MatchWeek.tsx` | Title → "Week N Debrief", remove subtitle from Headline, layout restructure (Match Flow full-width, Analysis Row, Fallout collapse) |
| `frontend/src/components/match-week/aftermath/ReplayTimeline.tsx` | Full rebuild: expanded timeline, event cards with badge/phase/desc/score/impact, maxHeight + scroll, no carousel |
| `frontend/src/components/match-week/aftermath/KeyPlayersPanel.tsx` | Expanded stat labels, circular rank badges (team-colored), "Your Club" orange tag |
| `frontend/src/components/match-week/aftermath/TacticalSummaryCard.tsx` | Evidence footer, remove orange accent |
| `frontend/src/components/match-week/aftermath/FalloutGrid.tsx` | Rename section, collapse logic |
| `frontend/src/components/match-week/aftermath/AftermathActionBar.tsx` | Watch Replay → solid secondary, responsive stacking |
| `frontend/src/index.css` | Layout classes for Analysis Row, Match Flow hero, orange discipline, responsive rules |

## Out of Scope

- Backend changes — all data already exists in `replayForMatch.report` and `activeResult.dashboard`
- The context line on the Headline (line 2) can be composed client-side from `match_card` data; no new API needed
- Scoreboard component (`MatchScoreHero`) — untouched
