# V5 Weekly Command Center Handoff

Date: 2026-05-02 (design + initial build); 2026-05-04 (playthrough QA + post-QA fixes; gates closed)
Milestone: V5

## Milestone Summary

The V5 milestone shifts the weekly dodgeball flow from a passive "inspect tabs and simulate" model to an interactive, playable **Weekly Command Center**. The user acts as a hybrid athletic director, selecting weekly intents, processing staff warnings, choosing tactical focuses, and reviewing causal dashboards post-simulation. V5 also closes the offseason gap that existed in the web app since V4: the full 10-beat offseason ceremony, recruitment, and next-season transition are now browser-playable without touching the Tkinter GUI.

## Readiness Gates Status

- ✅ **Functional Gate:** Backend, frontend, persistence, and tests all work for the intended loop. 366 tests passing. Frontend builds clean.
- ✅ **Playable Gate:** Verified via full AI-assisted browser playthrough on 2026-05-04. Human-readable flow — command center → sim week → match report → acknowledge → offseason ceremony → recruit → begin season. No external guidance required.
- ✅ **AI Playthrough Gate:** Verified. Automated browser evaluation completed a full season loop through command center, post-week dashboard, match replay, offseason ceremony beats (champion → recap → awards → records → HoF → development → retirements → rookie class preview → recruitment), rookie signing, and begin-season transition.
- ✅ **Simulation Honesty Gate:** Tactics sliders (`sync_throws`, `rush_frequency`) have measurable engine effects. Post-week dashboard reports causal evidence through tracked plan/outcome facts. Department order effects and their limits are explicitly disclosed in the staff room copy.
- ✅ **Documentation Gate:** This retrospective and the learnings document are complete.

## Post-QA Fixes (2026-05-04)

The 2026-05-02 build passed the functional gate but revealed six gaps during the first full AI playthrough. All six were fixed before closing V5.

**BUG-03 (P0) — Offseason ceremony blocked in web app.** The 10-beat offseason ceremony, recruitment, and next-season transition existed only in the Tkinter GUI. The web app had no API endpoints or React component. Fixed by: extracting shared logic into `src/dodgeball_sim/offseason_ceremony.py`; adding four endpoints (`GET /api/offseason/beat`, `POST /api/offseason/advance`, `POST /api/offseason/recruit`, `POST /api/offseason/begin-season`); creating `frontend/src/components/Offseason.tsx`; routing `App.tsx` to the offseason screen when the career cursor is in any offseason state.

**BUG-04 (P1) — Roster API missing computed fields.** `/api/roster` did not expose player overall rating or positional role. Fixed by adding `overall` (float, rounded to one decimal) and `role` (Captain/Striker/Anchor/Runner/Rookie/Utility by roster-position index) to each player dict in `get_roster()`. Role is derived from position index, not name parsing, so it survives BUG-06.

**BUG-05 (P1) — PlayerTraits all flat 50.** `build_curated_roster` initialized every player with `PlayerTraits()` defaults, making `potential`, `growth_curve`, `consistency`, and `pressure` identical across all players on every team. Fixed by replacing the defaults with `rng.gauss()`-sampled values (potential σ=15, others σ=12, all clamped 10–90). Development calculations that depend on these traits now produce meaningful variance.

**BUG-06 (P2) — Generic positional names.** Players were named `"{Club} Captain"`, `"{Club} Striker"`, etc. Fixed by importing `_FIRST_NAMES` and `_LAST_NAMES` from `randomizer.py` and generating names with `rng.choice()` during roster creation.

**BUG-07 (P2) — Season awards not computed in web flow.** `compute_season_awards` was only called from the Tkinter `_finalize_season` method, which never ran in the web path. Fixed by extracting `finalize_season()` into `offseason_ceremony.py` and calling it at the start of `GET /api/offseason/beat`. Awards are now computed and persisted idempotently when the player first enters the offseason screen.

**BUG-08 (P3) — No dev hot-reload.** `web_cli.py` did not support uvicorn reload or Vite dev server coordination. Fixed by: reading `DODGEBALL_DEV` env var; in dev mode, spawning `npm run dev` as a background subprocess, opening the browser to port 5173, and starting uvicorn with `reload=True`; in production mode, auto-building the frontend if `frontend/dist` is missing. `.claude/launch.json` simplified to a single "Dev Server" entry.

## Thin Mechanics Inherited by V6

The following V5 systems are present but intentionally minimal. V6 should either deepen them or leave them as acknowledged stubs.

- **Department orders** affect staff room copy and warning generation, but most do not yet wire into the simulation engine (medical, culture, conditioning). The dashboard discloses this.
- **Staff entities** are seeded with name and role but have no ratings that affect recommendation quality or engine behavior.
- **PlayerTraits** (`potential`, `growth_curve`, `consistency`, `pressure`) are now varied but only `potential` and `growth_curve` are consumed by `apply_season_development`. `consistency` and `pressure` are stored and displayed but not yet wired into match-phase behavior.
- **Player names** are now real but players do not yet have archetypes. V6 is the archetype milestone.
- **Season awards** are computed at offseason entry. The news feed (`/api/news`) reports them for the active season, but match-by-match MVP attribution is displayed in match reports only — it is not accumulated into a running wire feed during the season.
- **`offseason_development_json` / `offseason_retirements_json`** are computed by `initialize_manager_offseason` and shown in the ceremony beats. Development deltas are thin because all traits were flat-50 until BUG-05; season 2 onward will produce meaningful variance.

## What V6 Inherits

- `offseason_ceremony.py` is the canonical shared offseason module. Both the Tkinter GUI and the web server import from it.
- Career state machine handles `SEASON_COMPLETE_OFFSEASON_BEAT → SEASON_COMPLETE_RECRUITMENT_PENDING → NEXT_SEASON_READY → SEASON_ACTIVE_PRE_MATCH` cleanly.
- `_ROLE_LABELS` in `server.py` defines the positional contract (index 0–5). V6's archetype system should align to this rather than replace it silently.
- `finalize_season()` in `offseason_ceremony.py` must be called before `initialize_manager_offseason()`. The GET beat endpoint enforces this order.
- Command history is persisted per-week and available to any later system that needs player/staff credibility, development trajectories, or program reputation.
- The launcher (`python -m dodgeball_sim`) auto-builds the frontend on first run. `DODGEBALL_DEV=1` starts the full dev stack with one command.
