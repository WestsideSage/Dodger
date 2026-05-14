# Command Center — Opponent Intel Panel Polish

**Date:** 2026-05-14  
**Scope:** `PreSimDashboard.tsx` — Opponent Intel section only  
**Status:** Approved

## Problem

The bottom of the Opponent Intel panel had two readability problems:

1. **`key_matchup` text lacked context.** The field rendered raw player data (`Mika Keene, Tactical, 65 OVR`) as a `command-muted-copy` paragraph with no label. A user seeing it for the first time has no idea whether this is their own player, an opponent, or something else.

2. **Week timeline looked unstyled and wasted space.** The Practice / Team Meeting / Match Day rows used a plain label–value grid layout that matched no visual language in the rest of the panel. With no visual weight or grouping, the section felt like a data dump.

## Design

### 1 — Key Threat Card

Replace the bare `<p className="command-muted-copy">` that renders `details.key_matchup` with a structured card:

Layout: two-column flex row filling the full card width.

**Left column (flex: 1):**
- Red-tinted card container (`rgba(248,113,113,0.07)` bg, `rgba(248,113,113,0.2)` border, `border-radius 6px`)
- Warning icon circle on the far left (`rgba(248,113,113,0.15)` bg, 36×36px)
- "KEY THREAT" kicker label in red (`#f87171`) above the player name
- Player name rendered large (`0.9rem`, bold, `#f8fafc`)
- Role as a small pill badge below the name (muted gray)

**Right column (flex: 0, separated by a subtle `rgba(248,113,113,0.2)` left border):**
- OVR value as a large number (`1.6rem`, `font-weight 800`, `#f87171`, monospace)
- "OVR" label below in muted uppercase (`0.58rem`, `#64748b`)

This replaces the OVR cyan badge that was previously inline with the role badge on the left.

The `key_matchup` string from the backend is expected to be in the format `"Name, Role, OVR OVR"`. The card parses it by rendering name, role, and OVR in their respective positions — no backend change required. If the string doesn't follow this format, the card degrades gracefully by showing the raw text as the name field with the right column hidden.

**New label above scouting note:** Add a small `"SCOUTING"` uppercase kicker label (`color: #64748b`) immediately above the `command-muted-copy` recommendation text so both text blocks have clear identity.

### 2 — Week Timeline: Icon Pill Cards

Replace `.command-week-timeline.command-week-timeline-inline` with three horizontal pill cards in a CSS grid (`grid-template-columns: 1fr 1fr 1fr`):

| Slot | Icon | Label | Value | Style |
|------|------|-------|-------|-------|
| Practice | 🏋️ | Practice | `humanize(training)` | Neutral dark pill |
| Team Meeting | 🎯 | Meeting | `{approach} Review` | Neutral dark pill |
| Match Day | ⚡ | Match Day | `vs {opponent.name}` | Cyan-tinted pill + cyan border |

Each pill: `background rgba(30,41,59,0.6)`, `border-radius 6px`, flex row with icon + label/value stacked. Match Day gets `rgba(34,211,238,0.08)` background and `rgba(34,211,238,0.25)` border with cyan label color.

**`humanize()` capitalization fix:** Update the existing `humanize()` helper to sentence-case the output (capitalize first letter) instead of returning all-lowercase. Affects Practice and Development fields across the panel.

### 3 — No other changes

The rest of the Opponent Intel panel (framing line verdict, Win Condition / Best Fit / Plan Fit fit-notes, scout headline) is unchanged. No changes to other Command Center panels.

## Files Affected

- `frontend/src/components/match-week/command-center/PreSimDashboard.tsx` — JSX changes to intel section
- `frontend/src/index.css` — new CSS classes for key threat card and timeline pills; remove `.command-week-timeline-inline` overrides no longer needed

## Out of Scope

- Backend changes
- Changes to other Command Center sections (Game Plan, Control Tower)
- Win Condition / Best Fit / Plan Fit fit-note styling
