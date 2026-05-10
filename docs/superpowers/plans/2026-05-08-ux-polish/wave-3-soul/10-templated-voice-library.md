# Subplan 10: Templated Voice Library

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Read `../00-MAIN.md` first.

**Goal:** Author three Python writer modules that turn flat sim data into sports-commentator prose, replacing debug-string surfaces in three places: pre-match framing line (Subplan 05), post-match Aftermath headline (Subplan 06), and play-by-play replay commentary (Subplan 12).

**Dependencies:** Wave 2 must have shipped — the surfaces consuming the voice need to exist first. Subplan 12 depends on this subplan; 11, 13, 14, 15 are parallel-safe.

**Acceptance criteria (from 00-MAIN.md):**
- Three modules in `src/dodgeball_sim/`:
  - `voice_pregame.py` — `def render_matchup_framing(home, away, season_history, last_meeting, injuries) -> str` (≥30 templates)
  - `voice_playbyplay.py` — `def render_play(event) -> str` (≥30 templates covering: throws, dodges, catches, eliminations, key moments, team-scope events)
  - `voice_aftermath.py` — `def render_headline(match_result, expectation, rivalry, streak) -> str` (≥30 templates keyed on: upset, expected, blowout, comeback, streak-break, rivalry beat)
- Each module is deterministic given the same input + a stable RNG seed, so testing is straightforward.
- Templates use simple string substitution + small ad-hoc helper functions for grammar (e.g., player surname, team nickname). No heavy NLG framework.
- Frontend surfaces from Subplan 05/06/12 swap their stub copy for calls to new endpoints that wrap these renderers.
- Existing `narration.py`, `news.py`, and `copy_quality.py` are reviewed for overlap; if reusable helpers exist, adopt them rather than re-implementing.

---

- [ ] **Step 1: Write backend tests for voice library**

Create `tests/test_voice_library.py`:
```python
from dodgeball_sim.voice_pregame import render_matchup_framing
from dodgeball_sim.voice_aftermath import render_headline
from dodgeball_sim.rng import DeterministicRNG

def test_voice_pregame_deterministic():
    rng1 = DeterministicRNG(42)
    rng2 = DeterministicRNG(42)
    assert render_matchup_framing("Aurora", "Solstice", rng1) == render_matchup_framing("Aurora", "Solstice", rng2)

def test_voice_aftermath_deterministic():
    rng = DeterministicRNG(1)
    res = render_headline("Win", "expected", rng)
    assert len(res) > 5
```
Run, fail.

- [ ] **Step 2: Implement `voice_pregame.py`**

Create `src/dodgeball_sim/voice_pregame.py`. Define `render_matchup_framing(home: str, away: str, rng: DeterministicRNG, **kwargs) -> str`. Include at least 30 templates (e.g. "A classic showdown awaits as {home} hosts {away}."). Commit.

- [ ] **Step 3: Implement `voice_aftermath.py`**

Create `src/dodgeball_sim/voice_aftermath.py`. Define `render_headline(result: str, context: str, rng: DeterministicRNG, **kwargs) -> str`. Include at least 30 templates. Commit.

- [ ] **Step 4: Implement `voice_playbyplay.py`**

Create `src/dodgeball_sim/voice_playbyplay.py`. Define `render_play(event_type: str, actor: str, target: str, rng: DeterministicRNG, **kwargs) -> str`. Include at least 30 templates for throws, catches, and dodges. Commit.

- [ ] **Step 5: Integrate with API responses**

Update `src/dodgeball_sim/command_center.py` and `src/dodgeball_sim/server.py` to use `voice_pregame` for the Match Week framing line, and `voice_aftermath` for the post-sim headline. Ensure deterministic seeds based on week/match_id. Pass tests. Commit.

- [ ] **Step 6: Cross-cutting principle check**

Run `python -m pytest -q`.
Verify that no floating point numbers leak into the templates. Ensure that the strings returned are not "debug logs".
```bash
git commit --amend --no-edit
```