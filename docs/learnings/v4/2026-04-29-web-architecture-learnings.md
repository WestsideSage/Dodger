# Web Architecture Migration Learnings

**Date:** 2026-04-29
**Author:** Gemini (Lead Front-End UX Engineer)
**Phase:** Pre-V4 Web Architecture Transition

## 1. The Power of "Semantic Vision" for AI Models
The primary motivation for migrating from Tkinter to a Web Architecture (FastAPI + React/Tailwind) was to enable AI agents (like myself, Claude, and Codex) to better understand and style the UI. 
- **Tkinter is Opaque:** Deeply nested Tkinter widget trees in a 4,000+ line monolith (`manager_gui.py`) are extremely difficult for LLMs to reason about contextually. State, styling, and data fetching are heavily coupled.
- **The DOM is Semantic:** By moving to React and Tailwind CSS, we unlocked the ability to "see" the UI structurally. HTML tags provide semantic meaning, and utility classes (Tailwind) map directly to visual outcomes. This allows AI assistants to rapidly generate, style, and debug UI components with high accuracy.

## 2. Windows Registry MIME Type Trap
During the initial deployment of the React SPA served via FastAPI (`StaticFiles`), the browser rendered a completely white screen despite the Python server logging no errors.
- **The Issue:** On some Windows machines, the OS registry maps `.js` files to `text/plain` instead of `application/javascript`. FastAPI relies on Python's `mimetypes` module, which in turn reads the Windows registry. When the browser received the React bundle as `text/plain`, strict MIME checking blocked execution, causing a silent client-side failure.
- **The Fix:** We forcefully patched the `mimetypes` registry at application startup in `server.py` before serving static files:
  ```python
  import mimetypes
  mimetypes.add_type("application/javascript", ".js")
  mimetypes.add_type("text/css", ".css")
  ```

## 3. Graceful Null-State Handling in React
The previous Tkinter app heavily relied on the assumption that if the app was open, a database and career state likely existed (or it explicitly routed to a splash screen). 
- **The Issue:** When decoupling the UI into an API-driven React app, the frontend mounts *before* the data arrives. If the SQLite database is empty or uninitialized, endpoints like `/api/status` return `null` for `season_id` or `player_club_id`.
- **The Fix:** The React components must be engineered defensively. Calling string methods (e.g., `.split('-')`) on potentially null payload fields immediately crashes the React tree. We implemented defensive rendering and fallback UI states (e.g., showing "None" or "Loading...") to ensure the app shell survives an empty database state.

## 4. The Strangler Fig Pattern Success
We successfully proved that we can build the V4 Web UI *alongside* the V3 Tkinter UI without touching the core simulation engine (`src/dodgeball_sim/engine.py`) or the persistence layer. 
- FastAPI simply imports the existing SQLite readers/writers.
- Both the old `manager_gui.py` and the new `web_cli.py` can theoretically be used interchangeably to play the same save file during the transition period.
- This approach completely de-risked the architectural rewrite, ensuring the deterministic test suite (300+ tests) remained green throughout the entire process.