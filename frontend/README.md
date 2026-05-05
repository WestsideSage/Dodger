# Dodgeball Manager Web Frontend

React + TypeScript + Vite client for the Dodgeball Manager web migration.

The frontend talks to the FastAPI backend in `src/dodgeball_sim/server.py`. Keep simulation rules, persistence logic, and state transitions in the Python domain layer; this client should render and submit intent through API endpoints.

## Commands

```bash
npm install
npm run dev
npm run build
npm run lint
```

`npm run build` writes `frontend/dist/`. The Python launcher `python -m dodgeball_sim.web_cli` serves that built frontend through Uvicorn.

## Current Scope

- Hub status
- Roster view
- Tactics editing
- Simulate-week action

V4 feature parity still needs standings, schedule, news, scouting/recruitment, and match replay.

## UI Rules

Use the existing flat, border-heavy design tokens in `src/index.css`. Avoid renderer-only truth: UI numbers and replay visuals must trace back to API data from canonical simulation logs.
