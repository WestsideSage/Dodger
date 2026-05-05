# V3 Bug Patches

Date: 2026-04-29
Owner: Senior Debug & Maintenance Engineer
Codename: Baseline Lock

## Summary

Resolved the V3 audit corruption and parity blockers carried into the V4 sprint:

- Duplicate prospect signing now rejects already-signed prospects through the shared recruitment domain path.
- Web week simulation no longer mutates frozen career cursors directly.
- Malformed save-state JSON and forged offseason beat indices are validated defensively.
- V4 follow-on tasks added schema migration coverage, shared scheduled-match persistence, pure scouting week planning, balance/content updates, and first-pass web feature parity.
- Award wire text now has a human-readable fallback even when older call sites do not pass roster context.

## Files Patched

- `src/dodgeball_sim/recruitment.py`
- `src/dodgeball_sim/persistence.py`
- `src/dodgeball_sim/manager_gui.py`
- `src/dodgeball_sim/server.py`
- `src/dodgeball_sim/game_loop.py`
- `src/dodgeball_sim/scouting_center.py`
- `src/dodgeball_sim/config.py`
- `src/dodgeball_sim/recruitment_domain.py`
- `src/dodgeball_sim/franchise.py`
- `src/dodgeball_sim/randomizer.py`
- `src/dodgeball_sim/identity.py`
- `src/dodgeball_sim/news.py`
- `src/dodgeball_sim/content/club_lore.json`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/components/Hub.tsx`
- `frontend/src/components/Roster.tsx`
- `frontend/src/components/Tactics.tsx`
- `frontend/src/components/LeagueContext.tsx`
- `tests/`

## Validation

- `python -m pytest -q`: passed
- `npm run lint`: passed
- `npm run build`: passed
- `python qa_v3_playthrough.py`: passed with 0 failures and 0 bugs
- `PRAGMA integrity_check`: `ok` for local SQLite artifacts checked

## Project Trajectory

### WHERE WE WERE

V3 shipped its experience rebuild, but audits identified state-corruption bugs, a frozen cursor mutation crash in the web API, weak defensive handling around saved JSON, raw IDs in some player-facing copy, and early web-client parity gaps.

### WHERE WE ARE

The critical corruption bugs are covered by regression tests, shared simulation persistence is factored out for web and Tkinter clients, content/name/copy fixes are in place, and the React app now exposes first-pass Hub pacing, standings, schedule, news, roster OVR/Potential, and tactics save feedback.

### WHERE WE ARE GOING

V4 can continue toward deeper web parity from a safer base: remaining work should focus on richer match preview/play flows, offseason/recruitment web screens, and any concurrency hardening needed after the single-user local web path is stable.
