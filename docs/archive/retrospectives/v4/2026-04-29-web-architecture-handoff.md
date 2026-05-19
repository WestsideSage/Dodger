# Web Architecture Foundation Handoff

**Date:** 2026-04-29
**Milestone:** V4 Web Architecture Foundation
**Status:** Shipped. The web app is the product foundation going forward.

## WHERE WE WERE
The project had accumulated a complete season-management experience, but the player-facing surface was difficult for agents to inspect, style, and verify reliably. V4 moved the product foundation to a browser-delivered app so future work can be tested through HTTP APIs, React components, and browser automation.

## WHERE WE ARE
The foundation is now a client-server web app:

1. **Backend (`src/dodgeball_sim/server.py`):** FastAPI REST service wrapping the existing deterministic simulation, franchise, and persistence layers.
2. **Frontend (`frontend/`):** Vite + React + TypeScript single-page app using the project dashboard styling.
3. **Delivery (`src/dodgeball_sim/web_cli.py`):** Starts the local server, serves the built frontend, and opens the browser.
4. **Default launch:** `python -m dodgeball_sim`, `dodgeball-manager`, and `dodgeball-manager-web` all target the web app.

Implemented web surfaces include Hub, Roster, Tactics, Match Replay, Standings, Schedule, and News.

## WHERE WE ARE GOING
V5 should build directly on the web app. Good next targets:

1. Deepen Scouting and Recruitment workflows in React.
2. Expand match replay controls and report presentation.
3. Add richer league-history and player-detail screens.
4. Keep shared simulation and persistence logic UI-agnostic.

## Engineering Guidelines

- Keep HTTP and React concepts out of the engine/domain models.
- Add FastAPI endpoints for shared domain capabilities instead of duplicating business rules in the frontend.
- Use browser/build verification for player-facing web changes.
- Keep visual styling aligned with `frontend/src/index.css` and existing components.
