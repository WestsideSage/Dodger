# Subplan 10 (STUB): Templated Voice Library

> **Status:** STUB. Detailed task breakdown authored after Wave 2 ships. Read `../00-MAIN.md` first.

**Goal:** Author three Python writer modules that turn flat sim data into sports-commentator prose, replacing debug-string surfaces in three places: pre-match framing line (Subplan 05), post-match Aftermath headline (Subplan 06), and play-by-play replay commentary (Subplan 12).

**Dependencies:** Wave 2 must have shipped — the surfaces consuming the voice need to exist first. Subplan 12 depends on this subplan; 11, 13, 14, 15 are parallel-safe.

**Acceptance criteria:**
- Three modules in `src/dodgeball_sim/`:
  - `voice_pregame.py` — `def render_matchup_framing(home, away, season_history, last_meeting, injuries) -> str` (≥30 templates)
  - `voice_playbyplay.py` — `def render_play(event) -> str` (≥30 templates covering: throws, dodges, catches, eliminations, key moments, team-scope events)
  - `voice_aftermath.py` — `def render_headline(match_result, expectation, rivalry, streak) -> str` (≥30 templates keyed on: upset, expected, blowout, comeback, streak-break, rivalry beat)
- Each module is deterministic given the same input + a stable RNG seed, so testing is straightforward.
- Templates use simple string substitution + small ad-hoc helper functions for grammar (e.g., player surname, team nickname). No heavy NLG framework.
- Frontend surfaces from Subplan 05/06/12 swap their stub copy for calls to new endpoints that wrap these renderers.
- Existing `narration.py`, `news.py`, and `copy_quality.py` are reviewed for overlap; if reusable helpers exist, adopt them rather than re-implementing.

**Files anticipated:**
- New: `src/dodgeball_sim/voice_pregame.py`
- New: `src/dodgeball_sim/voice_playbyplay.py`
- New: `src/dodgeball_sim/voice_aftermath.py`
- New: `tests/test_voice_pregame.py`, `tests/test_voice_playbyplay.py`, `tests/test_voice_aftermath.py`
- `src/dodgeball_sim/server.py` (new endpoints or extensions to existing endpoints to surface rendered prose)
- Possible refactor: existing `narration.py` / `news.py` / `copy_quality.py` if voice modules can absorb them

**Verification gates:** build + pytest green; per-module test suite covers ≥10 distinct input scenarios each, asserting no template falls through to a default; manual smoke confirms variety across multiple match results.
