# Design-System Documentation

This folder contains the visual and UX contracts for the current design-system push. Read this file before opening an individual design-system document.

## Current Order Of Work

1. Command Center / Match Week polish is the active front of work.
2. After Command Center is stable, move through the remaining systems: Dynasty Office, Roster Lab, Match Replay, and League Office / Standings.
3. Verify every design-system instruction against the current frontend before implementation. Several handoff docs describe phase targets, not guaranteed shipped reality.

## Files

- `Command-Center-Design-System.md` - main visual/UX direction for Command Center / Match Week.
- `Dynasty-Office-Design-System.md` - Dynasty Office target direction.
- `Roster-Lab-Design-System.md` - roster development surface target direction.
- `Match-Replay-Design-System.md` - watchable replay target direction.
- `League-Office-Standings-Design-System.md` - standings/league context target direction.
- `handoffs/` - phase implementation prompts and design handoffs. Treat these as task packets, not canonical status reports.

## Source Boundaries

- Frontend source of truth: `frontend/src/`.
- Shared frontend API types: `frontend/src/types.ts`.
- Backend API surface: `src/dodgeball_sim/server.py` and sibling domain modules.
- Current milestone truth: `docs/specs/MILESTONES.md`.

## Staleness Rules

- A design doc may describe a target state that is not implemented yet.
- A handoff may reference old names such as `CommandCenter.tsx`; check for current files such as `MatchWeek.tsx` before editing.
- Do not widen a design-system pass into engine, balance, or persistence changes unless the active plan explicitly requires it.
