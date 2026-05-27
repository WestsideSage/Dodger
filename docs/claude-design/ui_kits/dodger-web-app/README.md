# Dodger Web App -- UI Kit

A pixel-faithful recreation of the shipped Dodger frontend (React + Vite + Tailwind v4), rebuilt as a self-contained React + Babel prototype.

## Surfaces

- **Command Center** (`WAR ROOM`) -- weekly plan + simulate + post-match aftermath
- **Roster** (`ROSTER LAB`) -- player table, potential tiers, rating bars
- **Dynasty Office** (`FRONT OFFICE`) -- credibility, recruiting board, staff room
- **Standings** (`LEAGUE OFFICE`) -- league table + recent matches
- **Match Replay** (`MATCH DAY`) -- top-down court + scrubber + event log

## Files

- `index.html` -- shell. Loads fonts, scripts, mounts `<App />`.
- `app.jsx` -- top-level state + screen router.
- `data.js` -- fake season data (Solstice vs Northwood Cyphers, 18-player roster, 8 recruits).
- `components/shared.jsx` -- Badge, Button, Panel, StatChip, RatingBar, PotentialBadge, Kicker.
- `components/Nav.jsx` -- `<LeftNav>` + `<BroadcastHeader>`.
- `components/CommandCenter.jsx` -- pre-sim + post-sim aftermath.
- `components/Roster.jsx` -- roster table.
- `components/DynastyOffice.jsx` -- recruit board.
- `components/Standings.jsx` -- standings table.
- `components/MatchReplay.jsx` -- court visualisation + log.

Open `index.html`. The Command Center loads by default. Use the left nav to navigate. The "Simulate Week" button in Command Center plays a fake match and reveals the aftermath in staged reveals.

This kit re-uses tokens from `../../colors_and_type.css`; do not duplicate token definitions.
