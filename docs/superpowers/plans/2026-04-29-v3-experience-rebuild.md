# V3 Experience Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild V3 game feel by fixing active-roster integrity, improving match/replay presentation, adding season pacing controls, tightening visual hierarchy, and polishing copy/name generation.

**Architecture:** Keep the engine pure and unchanged unless a test proves the engine contract itself is wrong. Enforce legal starters in the dynasty-to-engine boundary, derive replay/report UI from the same active match setup and event log, and add pacing as a manager-layer loop over existing deterministic simulation functions. Centralize reusable UI/copy helpers instead of scattering one-off fixes through `manager_gui.py`.

**Tech Stack:** Python 3, Tkinter/ttk, SQLite persistence, pytest, existing `src/dodgeball_sim` modules.

---

## File Structure

- Modify `src/dodgeball_sim/lineup.py`: add active-starter helper while preserving full ordered lineup diagnostics for UI.
- Modify `src/dodgeball_sim/franchise.py`: ensure `simulate_match()` and `build_match_team_snapshot()` use active starters only and hash/audit active snapshots consistently.
- Modify `src/dodgeball_sim/manager_gui.py`: use active match setups for replay/report persistence, add roster starter/bench visual separation, add pacing controls and digest screens, and tighten major screen copy.
- Modify `src/dodgeball_sim/court_renderer.py`: render a larger, clearer court with capped starter tokens, player initials from display names when available, and better event focus.
- Modify `src/dodgeball_sim/ui_style.py`: add stricter typography/action styles and any missing constants needed by the rebuilt screens.
- Modify `src/dodgeball_sim/ui_components.py`: add the `PageHeader` component used by the rebuilt major screens.
- Modify `src/dodgeball_sim/recruitment.py`: expand deterministic name pools and add unique display-name selection for generated rookie/prospect classes.
- Create `src/dodgeball_sim/sim_pacing.py`: pure helpers for bulk-sim requests, stop reasons, and digest payloads.
- Create `tests/test_v3_roster_integrity.py`: tests for active starter enforcement and bench exclusion.
- Create `tests/test_v3_pacing.py`: tests for bulk sim parity and stop reasons.
- Create `tests/test_copy_quality.py`: tests for repeated generated names, unresolved IDs, unresolved template tokens, and title casing helper behavior.
- Modify existing tests where expectations intentionally change: `tests/test_lineup.py`, `tests/test_manager_gui.py`, `tests/test_recruitment.py`.

This workspace currently has no `.git` directory. If implementation happens in a Git worktree, run the commit commands listed in each task. If not, treat each commit step as a checkpoint and record the changed files in the final handoff.

---

### Task 1: Enforce Active Starters At The Lineup Boundary

**Files:**
- Modify: `src/dodgeball_sim/lineup.py`
- Modify: `tests/test_lineup.py`
- Create: `tests/test_v3_roster_integrity.py`

- [ ] **Step 1: Write failing lineup tests**

Add these tests to `tests/test_lineup.py`:

```python
def test_active_starters_caps_full_resolved_lineup_at_six():
    roster = [_p(f"p{i}", 50 + i) for i in range(9)]
    resolver = LineupResolver()

    resolved = resolver.resolve(roster=roster, default=[p.id for p in roster], override=None)
    active = resolver.active_starters(resolved)

    assert len(resolved) == 9
    assert active == ["p0", "p1", "p2", "p3", "p4", "p5"]


def test_active_starters_preserves_resolved_order_after_invalid_backfill():
    roster = [_p("a", 70), _p("b", 90), _p("c", 80), _p("d", 60), _p("e", 50), _p("f", 40), _p("g", 95)]
    resolver = LineupResolver()

    resolved = resolver.resolve(roster=roster, default=["ghost", "a", "c"], override=None)
    active = resolver.active_starters(resolved)

    assert resolved[:7] == ["a", "c", "g", "b", "d", "e", "f"]
    assert active == ["a", "c", "g", "b", "d", "e"]
```

- [ ] **Step 2: Run the focused failing tests**

Run: `python -m pytest tests/test_lineup.py::test_active_starters_caps_full_resolved_lineup_at_six tests/test_lineup.py::test_active_starters_preserves_resolved_order_after_invalid_backfill -q`

Expected: both tests fail with `AttributeError: 'LineupResolver' object has no attribute 'active_starters'`.

- [ ] **Step 3: Implement the helper**

In `src/dodgeball_sim/lineup.py`, update the module docstring and add the method:

```python
"""Lineup resolution for Manager Mode.

A lineup is an ordered list of player IDs. The UI may show the full ordered
roster, but match simulation activates only the first STARTERS_COUNT valid
players. Bench players remain rostered and visible outside the match.
"""
```

Inside `LineupResolver`:

```python
    def active_starters(self, resolved_lineup: Sequence[str]) -> List[str]:
        """Return the legal active match participants from a resolved lineup."""
        return list(resolved_lineup[:STARTERS_COUNT])
```

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_lineup.py -q`

Expected: all lineup tests pass.

- [ ] **Step 5: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/lineup.py tests/test_lineup.py
git commit -m "Enforce active starter lineup helper"
```

---

### Task 2: Make Match Simulation Use Only Active Starters

**Files:**
- Modify: `src/dodgeball_sim/franchise.py`
- Create: `tests/test_v3_roster_integrity.py`

- [ ] **Step 1: Write failing simulation tests**

Create `tests/test_v3_roster_integrity.py`:

```python
from dodgeball_sim.franchise import build_match_team_snapshot, simulate_match
from dodgeball_sim.league import Club
from dodgeball_sim.lineup import STARTERS_COUNT
from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings, PlayerTraits
from dodgeball_sim.scheduler import ScheduledMatch


def _player(player_id: str, overall: float = 60.0) -> Player:
    return Player(
        id=player_id,
        name=player_id.upper(),
        ratings=PlayerRatings(overall, overall, overall, overall, overall),
        traits=PlayerTraits(),
        club_id=None,
    )


def _club(club_id: str) -> Club:
    return Club(
        club_id=club_id,
        name=club_id.title(),
        primary_color="#111111",
        secondary_color="#eeeeee",
        home_region="Test",
        founded_year=2026,
        coach_policy=CoachPolicy(),
    )


def test_build_match_team_snapshot_uses_only_active_starters():
    roster = [_player(f"home_{idx}", 50 + idx) for idx in range(9)]
    lineup = [player.id for player in roster]

    team = build_match_team_snapshot(_club("home"), roster, lineup)

    assert len(team.players) == STARTERS_COUNT
    assert [player.id for player in team.players] == lineup[:STARTERS_COUNT]


def test_simulate_match_caps_both_expanded_rosters_at_six():
    home_roster = [_player(f"home_{idx}", 70) for idx in range(10)]
    away_roster = [_player(f"away_{idx}", 70) for idx in range(8)]
    scheduled = ScheduledMatch(
        match_id="season_1_w1_m1",
        season_id="season_1",
        week=1,
        home_club_id="home",
        away_club_id="away",
    )

    record, result = simulate_match(
        scheduled=scheduled,
        home_club=_club("home"),
        away_club=_club("away"),
        home_roster=home_roster,
        away_roster=away_roster,
        root_seed=20260429,
        home_lineup_default=[player.id for player in home_roster],
        away_lineup_default=[player.id for player in away_roster],
    )

    assert len(record.result.box_score["teams"]["home"]["players"]) == STARTERS_COUNT
    assert len(record.result.box_score["teams"]["away"]["players"]) == STARTERS_COUNT
    assert result.home_survivors <= STARTERS_COUNT
    assert result.away_survivors <= STARTERS_COUNT
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_v3_roster_integrity.py -q`

Expected: `test_build_match_team_snapshot_uses_only_active_starters` fails because all rostered players are included.

- [ ] **Step 3: Update `build_match_team_snapshot()` and `simulate_match()`**

In `src/dodgeball_sim/franchise.py`, import `STARTERS_COUNT` and use a stable player lookup:

```python
from .lineup import LineupResolver, STARTERS_COUNT
```

Update `build_match_team_snapshot()`:

```python
def build_match_team_snapshot(
    club: Club,
    roster: List[Player],
    lineup: List[str],
) -> Team:
    """Convert a Club + active lineup into an immutable Team for MatchEngine.

    The lineup may contain a full ordered roster. Only the first STARTERS_COUNT
    valid IDs are active in the engine.
    """
    active_ids = list(lineup[:STARTERS_COUNT])
    by_id = {player.id: player for player in roster}
    players = [by_id[player_id] for player_id in active_ids if player_id in by_id]
    return Team(
        id=club.club_id,
        name=club.name,
        players=tuple(players),
        coach_policy=club.coach_policy,
        chemistry=0.5,
    )
```

Update `simulate_match()` so it imports no local resolver and passes active IDs:

```python
    resolver = LineupResolver()
    home_resolved = resolver.resolve(home_roster, home_lineup_default, home_lineup_override)
    away_resolved = resolver.resolve(away_roster, away_lineup_default, away_lineup_override)
    home_lineup = resolver.active_starters(home_resolved)
    away_lineup = resolver.active_starters(away_resolved)
```

- [ ] **Step 4: Run focused roster tests**

Run: `python -m pytest tests/test_lineup.py tests/test_v3_roster_integrity.py -q`

Expected: all tests pass.

- [ ] **Step 5: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/franchise.py tests/test_v3_roster_integrity.py
git commit -m "Cap match snapshots at active starters"
```

---

### Task 3: Make Manager GUI Persistence And Reports Use Active Match Setup

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py`
- Modify: `tests/test_manager_gui.py`
- Modify: `tests/test_v3_roster_integrity.py`

- [ ] **Step 1: Add a failing manager-level regression test**

Append to `tests/test_v3_roster_integrity.py`:

```python
import sqlite3

from dodgeball_sim.manager_gui import initialize_manager_career, sign_prospect_to_club
from dodgeball_sim.persistence import create_schema, load_all_rosters, load_lineup_default, load_prospect_pool


def test_recruited_players_stay_on_bench_until_promoted_to_top_six():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    prospect = load_prospect_pool(conn, class_year=1)[0]
    signed = sign_prospect_to_club(conn, prospect, "aurora", class_year=1)
    rosters = load_all_rosters(conn)
    lineup = load_lineup_default(conn, "aurora")

    assert signed.id in [player.id for player in rosters["aurora"]]
    assert len(rosters["aurora"]) == 7
    assert len(lineup) == 7
    assert signed.id == lineup[-1]
```

This test documents current roster ordering and supports the next assertion.

Then add:

```python
def test_recruited_bench_player_not_in_next_match_stats():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    app_cursor = initialize_manager_career(conn, "aurora", root_seed=20260426)

    prospect = load_prospect_pool(conn, class_year=1)[0]
    signed = sign_prospect_to_club(conn, prospect, "aurora", class_year=1)
    from dodgeball_sim.persistence import load_clubs, load_season, get_state
    from dodgeball_sim.franchise import simulate_match

    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    season = load_season(conn, get_state(conn, "active_season_id"))
    user_match = next(
        match for match in season.scheduled_matches
        if "aurora" in (match.home_club_id, match.away_club_id)
    )

    record, _ = simulate_match(
        scheduled=user_match,
        home_club=clubs[user_match.home_club_id],
        away_club=clubs[user_match.away_club_id],
        home_roster=rosters[user_match.home_club_id],
        away_roster=rosters[user_match.away_club_id],
        root_seed=20260426,
        home_lineup_default=load_lineup_default(conn, user_match.home_club_id),
        away_lineup_default=load_lineup_default(conn, user_match.away_club_id),
    )

    active_ids = {player.id for player in record.result.setup.team_a.players}
    active_ids.update(player.id for player in record.result.setup.team_b.players)
    assert signed.id not in active_ids
```

- [ ] **Step 2: Run focused manager roster tests**

Run: `python -m pytest tests/test_v3_roster_integrity.py -q`

Expected: all tests pass after Task 2. If the second test fails, the match path is still using full rosters.

- [ ] **Step 3: Update GUI setup helpers to use active teams**

In `src/dodgeball_sim/manager_gui.py`, add a helper near `_team_for_club()`:

```python
    def _active_team_for_club(self, club: Club, roster: List[Player]) -> Team:
        default = load_lineup_default(self.conn, club.club_id)
        resolved = LineupResolver().resolve(roster, default, None)
        active_ids = LineupResolver().active_starters(resolved)
        by_id = {player.id: player for player in roster}
        players = tuple(by_id[player_id] for player_id in active_ids if player_id in by_id)
        return Team(id=club.club_id, name=club.name, players=players, coach_policy=club.coach_policy, chemistry=0.5)
```

Keep `_team_for_club()` for full-roster summaries only. Replace match/replay persistence setup construction in `_persist_record()`, `_report_text()` leverage calculation, `_setup_for_current_record()`, and match preview calculations when they refer to engine participants.

Use this pattern:

```python
home_team = self._active_team_for_club(home, self.rosters[home.club_id])
away_team = self._active_team_for_club(away, self.rosters[away.club_id])
```

- [ ] **Step 4: Run focused manager tests**

Run: `python -m pytest tests/test_v3_roster_integrity.py tests/test_manager_gui.py -q`

Expected: tests pass. Existing tests may need expected active counts adjusted from full roster length to `STARTERS_COUNT` only where the test is about a match setup.

- [ ] **Step 5: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/manager_gui.py tests/test_v3_roster_integrity.py tests/test_manager_gui.py
git commit -m "Use active match teams in manager GUI"
```

---

### Task 4: Separate Starters And Bench In The Roster UI

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py`
- Modify: `tests/test_manager_gui.py`

- [ ] **Step 1: Add a pure display helper test**

Add to `tests/test_manager_gui.py`:

```python
def test_lineup_text_separates_starters_and_bench(monkeypatch):
    import sqlite3
    from dodgeball_sim.manager_gui import ManagerModeApp
    from dodgeball_sim.persistence import create_schema, save_lineup_default

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    app = object.__new__(ManagerModeApp)
    app.conn = conn
    app.rosters = {"aurora": [_make_player(f"p{i}", overall=70 + i) for i in range(8)]}
    save_lineup_default(conn, "aurora", [f"p{i}" for i in range(8)])

    text = ManagerModeApp._lineup_text(app, "aurora")

    assert "Starters" in text
    assert "Bench" in text
    assert "7. P6 | Bench" in text
```

If `_make_player` does not exist in the test file, add:

```python
def _make_player(player_id: str, overall: float = 60.0) -> Player:
    return Player(
        id=player_id,
        name=player_id.upper(),
        ratings=PlayerRatings(overall, overall, overall, overall, overall),
        traits=PlayerTraits(),
    )
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py::test_lineup_text_separates_starters_and_bench -q`

Expected: fail because `_lineup_text()` currently has only a single "Starters: first 6" header.

- [ ] **Step 3: Update `_lineup_text()`**

Replace `_lineup_text()` with:

```python
    def _lineup_text(self, club_id: str) -> str:
        roster = self.rosters[club_id]
        default = load_lineup_default(self.conn, club_id)
        ordered_ids = LineupResolver().resolve(roster, default, None)
        by_id = {player.id: player for player in roster}
        lines = ["Starters", ""]
        for index, player_id in enumerate(ordered_ids[:STARTERS_COUNT], 1):
            player = by_id[player_id]
            lines.append(f"{index}. {player.name} | Starter | {player_role(player)} | OVR {player.overall():.1f}")
        bench_ids = ordered_ids[STARTERS_COUNT:]
        if bench_ids:
            lines.extend(["", "Bench", ""])
            for index, player_id in enumerate(bench_ids, STARTERS_COUNT + 1):
                player = by_id[player_id]
                lines.append(f"{index}. {player.name} | Bench | {player_role(player)} | OVR {player.overall():.1f}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run the test**

Run: `python -m pytest tests/test_manager_gui.py::test_lineup_text_separates_starters_and_bench -q`

Expected: pass.

- [ ] **Step 5: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/manager_gui.py tests/test_manager_gui.py
git commit -m "Separate starters and bench in roster display"
```

---

### Task 5: Rebuild Replay Event Summary And Court Sizing

**Files:**
- Modify: `src/dodgeball_sim/court_renderer.py`
- Modify: `src/dodgeball_sim/manager_gui.py`
- Modify: `tests/test_manager_gui.py`

- [ ] **Step 1: Add event-summary helper tests**

Add to `tests/test_manager_gui.py`:

```python
def test_replay_event_summary_includes_probability_roll_and_names():
    from dodgeball_sim.events import MatchEvent
    from dodgeball_sim.manager_gui import replay_event_summary

    event = MatchEvent(
        event_type="throw",
        tick=3,
        actors={"thrower": "p1", "target": "p2"},
        outcome={"resolution": "hit"},
        probabilities={"on_target": 0.61, "catch": 0.18},
        rolls={"on_target": 0.42, "catch": 0.91},
        state_diff={},
        context={"thrower_accuracy": 72, "target_dodge": 55},
    )

    summary = replay_event_summary(event, {"p1": "Mara Voss", "p2": "River Beck"})

    assert "Mara Voss" in summary
    assert "River Beck" in summary
    assert "Hit" in summary
    assert "61%" in summary
    assert "roll 0.42" in summary
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py::test_replay_event_summary_includes_probability_roll_and_names -q`

Expected: fail because `replay_event_summary` does not exist.

- [ ] **Step 3: Add `replay_event_summary()`**

In `src/dodgeball_sim/manager_gui.py`, add a module-level helper near report helpers:

```python
def replay_event_summary(event: Any, player_names: Mapping[str, str]) -> str:
    if event.event_type == "match_end":
        winner = event.outcome.get("winner", "Unknown")
        return f"Final whistle. Winner: {winner}."
    if event.event_type != "throw":
        return f"{str(event.event_type).replace('_', ' ').title()} at tick {event.tick}."

    thrower_id = event.actors.get("thrower", "")
    target_id = event.actors.get("target", "")
    thrower = player_names.get(thrower_id, thrower_id)
    target = player_names.get(target_id, target_id)
    resolution = str(event.outcome.get("resolution", "live")).replace("_", " ").title()
    on_target = event.probabilities.get("on_target")
    roll = event.rolls.get("on_target")
    probability_text = f"{on_target:.0%}" if isinstance(on_target, (int, float)) else "n/a"
    roll_text = f"{roll:.2f}" if isinstance(roll, (int, float)) else "n/a"
    return f"{thrower} targeted {target}. {resolution}. On-target chance {probability_text}; roll {roll_text}."
```

- [ ] **Step 4: Update replay UI to use the summary**

In `show_replay_then_report()`, add a readable event panel beside or below the larger court. Use this pattern when rendering the current event:

```python
player_names = {player.id: player.name for roster in self.rosters.values() for player in roster}
event = self.replay_events[self.replay_index] if self.replay_events else None
summary = replay_event_summary(event, player_names) if event else "No event selected."
ttk.Label(event_panel, text=summary, style="CardValue.TLabel", wraplength=420).grid(row=0, column=0, sticky="w")
```

Make the court canvas use `sticky="nsew"` and give its frame row/column weight so it occupies most of the screen.

- [ ] **Step 5: Update `CourtRenderer` initials**

In `CourtRenderer._draw_player()`, continue using player IDs for now, but make initials readable:

```python
initials = "".join(part[0] for part in token.player_id.replace("-", "_").split("_") if part).upper()
```

Leave full display-name initials for a later task only if `PlayerToken` is extended with a `label`.

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests/test_manager_gui.py::test_replay_event_summary_includes_probability_roll_and_names -q`

Expected: pass.

- [ ] **Step 7: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/manager_gui.py src/dodgeball_sim/court_renderer.py tests/test_manager_gui.py
git commit -m "Improve replay event summary and court layout"
```

---

### Task 6: Add Pure Pacing Helpers

**Files:**
- Create: `src/dodgeball_sim/sim_pacing.py`
- Create: `tests/test_v3_pacing.py`

- [ ] **Step 1: Write pacing helper tests**

Create `tests/test_v3_pacing.py`:

```python
from dodgeball_sim.scheduler import ScheduledMatch
from dodgeball_sim.sim_pacing import SimRequest, choose_matches_to_sim, summarize_sim_digest


def _match(match_id: str, week: int, home: str, away: str) -> ScheduledMatch:
    return ScheduledMatch(match_id=match_id, season_id="season_1", week=week, home_club_id=home, away_club_id=away)


def test_sim_to_next_user_match_stops_before_user_match():
    schedule = [
        _match("m1", 1, "lunar", "nova"),
        _match("m2", 1, "aurora", "ember"),
        _match("m3", 2, "lunar", "aurora"),
    ]

    chosen, stop = choose_matches_to_sim(
        schedule,
        completed_match_ids=set(),
        player_club_id="aurora",
        request=SimRequest(mode="to_next_user_match"),
    )

    assert [match.match_id for match in chosen] == ["m1"]
    assert stop.reason == "user_match"
    assert stop.match_id == "m2"


def test_sim_week_includes_current_week_when_user_match_allowed():
    schedule = [
        _match("m1", 1, "lunar", "nova"),
        _match("m2", 1, "aurora", "ember"),
        _match("m3", 2, "lunar", "aurora"),
    ]

    chosen, stop = choose_matches_to_sim(
        schedule,
        completed_match_ids=set(),
        player_club_id="aurora",
        request=SimRequest(mode="week", current_week=1, include_user_matches=True),
    )

    assert [match.match_id for match in chosen] == ["m1", "m2"]
    assert stop.reason == "request_complete"


def test_digest_summary_counts_matches_and_notables():
    digest = summarize_sim_digest(
        matches_simmed=3,
        user_record_delta="2-1",
        standings_note="Aurora moved from 4th to 2nd.",
        notable_lines=["Mara Voss posted 4 eliminations."],
        next_action="Play Next Match",
    )

    assert digest["matches_simmed"] == 3
    assert digest["next_action"] == "Play Next Match"
    assert "Aurora moved" in digest["standings_note"]
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_v3_pacing.py -q`

Expected: fail because `dodgeball_sim.sim_pacing` does not exist.

- [ ] **Step 3: Implement `sim_pacing.py`**

Create `src/dodgeball_sim/sim_pacing.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

from .scheduler import ScheduledMatch


SimMode = Literal["week", "to_next_user_match", "multiple_weeks", "to_milestone"]


@dataclass(frozen=True)
class SimRequest:
    mode: SimMode
    current_week: int | None = None
    weeks: int = 1
    include_user_matches: bool = False


@dataclass(frozen=True)
class SimStop:
    reason: str
    match_id: str | None = None
    week: int | None = None


def choose_matches_to_sim(
    schedule: Sequence[ScheduledMatch],
    completed_match_ids: set[str],
    player_club_id: str,
    request: SimRequest,
) -> tuple[list[ScheduledMatch], SimStop]:
    pending = sorted(
        [match for match in schedule if match.match_id not in completed_match_ids],
        key=lambda match: (match.week, match.match_id),
    )
    chosen: list[ScheduledMatch] = []
    if not pending:
        return chosen, SimStop(reason="season_complete")

    if request.mode == "week":
        target_week = request.current_week if request.current_week is not None else pending[0].week
        for match in pending:
            if match.week != target_week:
                continue
            if _is_user_match(match, player_club_id) and not request.include_user_matches:
                return chosen, SimStop(reason="user_match", match_id=match.match_id, week=match.week)
            chosen.append(match)
        return chosen, SimStop(reason="request_complete")

    if request.mode == "to_next_user_match":
        for match in pending:
            if _is_user_match(match, player_club_id):
                return chosen, SimStop(reason="user_match", match_id=match.match_id, week=match.week)
            chosen.append(match)
        return chosen, SimStop(reason="season_complete")

    if request.mode == "multiple_weeks":
        start_week = request.current_week if request.current_week is not None else pending[0].week
        end_week = start_week + max(1, request.weeks) - 1
        for match in pending:
            if match.week < start_week or match.week > end_week:
                continue
            if _is_user_match(match, player_club_id) and not request.include_user_matches:
                return chosen, SimStop(reason="user_match", match_id=match.match_id, week=match.week)
            chosen.append(match)
        return chosen, SimStop(reason="request_complete")

    for match in pending:
        if _is_user_match(match, player_club_id) and not request.include_user_matches:
            return chosen, SimStop(reason="user_match", match_id=match.match_id, week=match.week)
        chosen.append(match)
    return chosen, SimStop(reason="request_complete")


def summarize_sim_digest(
    matches_simmed: int,
    user_record_delta: str,
    standings_note: str,
    notable_lines: Iterable[str],
    next_action: str,
) -> dict[str, object]:
    return {
        "matches_simmed": matches_simmed,
        "user_record_delta": user_record_delta,
        "standings_note": standings_note,
        "notable_lines": list(notable_lines),
        "next_action": next_action,
    }


def _is_user_match(match: ScheduledMatch, player_club_id: str) -> bool:
    return player_club_id in (match.home_club_id, match.away_club_id)


__all__ = ["SimRequest", "SimStop", "choose_matches_to_sim", "summarize_sim_digest"]
```

- [ ] **Step 4: Run pacing tests**

Run: `python -m pytest tests/test_v3_pacing.py -q`

Expected: pass.

- [ ] **Step 5: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/sim_pacing.py tests/test_v3_pacing.py
git commit -m "Add season pacing helpers"
```

---

### Task 7: Wire Hub Pacing Controls And Digest Screen

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py`
- Modify: `tests/test_manager_gui.py`
- Modify: `tests/test_v3_pacing.py`

- [ ] **Step 1: Add digest-rendering helper test**

Add to `tests/test_manager_gui.py`:

```python
def test_format_sim_digest_text_is_readable():
    from dodgeball_sim.manager_gui import format_sim_digest_text

    text = format_sim_digest_text(
        {
            "matches_simmed": 4,
            "user_record_delta": "3-1",
            "standings_note": "Aurora moved from 4th to 2nd.",
            "notable_lines": ["Mara Voss posted 4 eliminations."],
            "next_action": "Play Next Match",
        }
    )

    assert "4 Matches Simmed" in text
    assert "Aurora moved from 4th to 2nd." in text
    assert "Play Next Match" in text
```

- [ ] **Step 2: Run failing test**

Run: `python -m pytest tests/test_manager_gui.py::test_format_sim_digest_text_is_readable -q`

Expected: fail because `format_sim_digest_text` does not exist.

- [ ] **Step 3: Add digest formatter**

In `src/dodgeball_sim/manager_gui.py`, add:

```python
def format_sim_digest_text(digest: Mapping[str, Any]) -> str:
    lines = [
        f"{digest.get('matches_simmed', 0)} Matches Simmed",
        f"User Club Record: {digest.get('user_record_delta', '-')}",
        str(digest.get("standings_note", "")),
        "",
        "Notable Updates:",
    ]
    notable_lines = list(digest.get("notable_lines", []))
    if notable_lines:
        lines.extend(f"- {line}" for line in notable_lines)
    else:
        lines.append("- No major updates.")
    lines.extend(["", f"Next: {digest.get('next_action', 'Continue')}"])
    return "\n".join(line for line in lines if line is not None)
```

- [ ] **Step 4: Add GUI methods for pacing**

In `ManagerModeApp`, add `_sim_with_request()`:

```python
    def _sim_with_request(self, request: SimRequest) -> None:
        if self.season is None or not self.player_club_id:
            return
        from .sim_pacing import choose_matches_to_sim, summarize_sim_digest

        completed = load_completed_match_ids(self.conn, self.season.season_id)
        matches, stop = choose_matches_to_sim(
            list(self.season.scheduled_matches),
            completed,
            self.player_club_id,
            request,
        )
        if matches:
            records, _ = simulate_matchday(
                matches,
                self.clubs,
                self.rosters,
                int(get_state(self.conn, "root_seed", "1") or "1"),
                difficulty=get_state(self.conn, "difficulty", "pro") or "pro",
            )
            for record in records:
                self._persist_record(record, record.home_club_id, record.away_club_id, None)
            self._recompute_standings()
            self.conn.commit()
        digest = summarize_sim_digest(
            matches_simmed=len(matches),
            user_record_delta=self._user_record_text(),
            standings_note=self._standings_movement_note(),
            notable_lines=self._bulk_sim_notables(matches),
            next_action=self._next_action_for_stop(stop),
        )
        self.show_sim_digest(digest)
```

Add these small helpers with deterministic, data-grounded output:

```python
    def _user_record_text(self) -> str:
        if self.season is None or not self.player_club_id:
            return "-"
        standings = {row.club_id: row for row in load_standings(self.conn, self.season.season_id)}
        row = standings.get(self.player_club_id)
        return f"{row.wins}-{row.losses}" if row else "0-0"

    def _standings_movement_note(self) -> str:
        if self.season is None:
            return "Standings unavailable."
        standings = _standings_with_all_clubs(load_standings(self.conn, self.season.season_id), self.clubs)
        if not standings:
            return "No standings changes yet."
        leader = standings[0]
        return f"{self.clubs[leader.club_id].name} leads at {leader.wins}-{leader.losses}."

    def _bulk_sim_notables(self, matches: Sequence[ScheduledMatch]) -> list[str]:
        if not matches:
            return []
        return [f"{len(matches)} scheduled matches resolved from the same match engine path."]

    def _next_action_for_stop(self, stop: Any) -> str:
        if stop.reason == "user_match":
            return "Play Next Match"
        if stop.reason == "season_complete":
            return "Continue To Season Summary"
        return "Return To Hub"
```

Add `show_sim_digest()`:

```python
    def show_sim_digest(self, digest: Mapping[str, Any]) -> None:
        self._refresh_header()
        frame = self._clear()
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Simulation Digest", style="Display.TLabel").grid(row=0, column=0, sticky="w")
        text = self._text(frame, font=FONT_MONO)
        text.grid(row=1, column=0, sticky="nsew", pady=SPACE_2)
        text.insert(tk.END, format_sim_digest_text(digest))
        text.configure(state=tk.DISABLED)
        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, sticky="e")
        ttk.Button(actions, text="Return To Hub", command=self.show_hub, style="Accent.TButton").pack(side=tk.LEFT)
```

- [ ] **Step 5: Add hub buttons**

In `show_hub()`, add a pacing action area near the existing next-match controls:

```python
ttk.Button(actions, text="Sim Week", command=lambda: self._sim_with_request(SimRequest(mode="week", current_week=self._current_week(), include_user_matches=True)), style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
ttk.Button(actions, text="Sim To Next User Match", command=lambda: self._sim_with_request(SimRequest(mode="to_next_user_match")), style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, SPACE_1))
ttk.Button(actions, text="Sim 4 Weeks", command=lambda: self._sim_with_request(SimRequest(mode="multiple_weeks", current_week=self._current_week(), weeks=4, include_user_matches=False)), style="Secondary.TButton").pack(side=tk.LEFT)
```

Add `from .sim_pacing import SimRequest` near imports.

- [ ] **Step 6: Run pacing and manager tests**

Run: `python -m pytest tests/test_v3_pacing.py tests/test_manager_gui.py::test_format_sim_digest_text_is_readable -q`

Expected: pass.

- [ ] **Step 7: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/manager_gui.py tests/test_manager_gui.py
git commit -m "Add manager pacing controls and digest"
```

---

### Task 8: Make Recruit And Rookie Names Deterministically Unique

**Files:**
- Modify: `src/dodgeball_sim/recruitment.py`
- Modify: `tests/test_recruitment.py`

- [ ] **Step 1: Add failing uniqueness tests**

Add to `tests/test_recruitment.py`:

```python
def test_generate_prospect_pool_display_names_unique_within_class():
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.rng import DeterministicRNG

    pool = generate_prospect_pool(class_year=7, rng=DeterministicRNG(20260429), config=DEFAULT_SCOUTING_CONFIG)
    names = [prospect.name for prospect in pool]

    assert len(names) == len(set(names))


def test_generate_rookie_class_display_names_unique_within_class():
    from dodgeball_sim.rng import DeterministicRNG

    rookies = generate_rookie_class("season_7", DeterministicRNG(20260429), size=24)
    names = [player.name for player in rookies]

    assert len(names) == len(set(names))
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_recruitment.py::test_generate_prospect_pool_display_names_unique_within_class tests/test_recruitment.py::test_generate_rookie_class_display_names_unique_within_class -q`

Expected: `test_generate_prospect_pool_display_names_unique_within_class` fails with the current small random name pool.

- [ ] **Step 3: Expand pools and add deterministic name helper**

In `src/dodgeball_sim/recruitment.py`, expand the pools:

```python
_FIRST_NAMES = (
    "Rin", "Avery", "Kai", "River", "Mara", "Ezra", "Sloane", "Jules",
    "Remy", "Quinn", "Niko", "Sable", "Ash", "Lyra", "Zeph", "Cass",
    "Talia", "Noor", "Imani", "Briar", "Callum", "Elio", "Mika", "Nia",
    "Rowan", "Selah", "Tobin", "Vale", "Wren", "Zara", "Kellan", "Luca",
)
_LAST_NAMES = (
    "Voss", "Helix", "Turner", "Lark", "Orion", "Vega", "Keene", "Hart",
    "Rowe", "Slate", "Frost", "Drake", "Munn", "Cole", "Beck", "Thorn",
    "Bishop", "Vale", "Cross", "Mercer", "Rhodes", "Santos", "Ibarra", "Kline",
    "Novak", "Penn", "Sol", "Tanner", "West", "Yardley", "Zane", "Okafor",
)
```

Add:

```python
def _unique_name(rng: DeterministicRNG, used_names: set[str], index: int) -> str:
    for _ in range(20):
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        if name not in used_names:
            used_names.add(name)
            return name
    first = _FIRST_NAMES[index % len(_FIRST_NAMES)]
    last = _LAST_NAMES[(index // len(_FIRST_NAMES)) % len(_LAST_NAMES)]
    name = f"{first} {last}"
    suffix = 2
    while name in used_names:
        name = f"{first} {last} {suffix}"
        suffix += 1
    used_names.add(name)
    return name
```

In `generate_rookie_class()`:

```python
    used_names: set[str] = set()
    for index in range(size):
        name = _unique_name(rng, used_names, index)
```

Use `name=name` instead of `name=f"{first} {last}"`.

In `generate_prospect_pool()`:

```python
    used_names: set[str] = set()
    for index in range(config.prospect_class_size):
        name = _unique_name(rng, used_names, index)
```

Use `name=name` in `Prospect`.

- [ ] **Step 4: Run recruitment tests**

Run: `python -m pytest tests/test_recruitment.py -q`

Expected: pass.

- [ ] **Step 5: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/recruitment.py tests/test_recruitment.py
git commit -m "Make generated class names unique"
```

---

### Task 9: Add Copy Quality Checks And Title-Case Helper

**Files:**
- Create: `src/dodgeball_sim/copy_quality.py`
- Create: `tests/test_copy_quality.py`
- Modify: `src/dodgeball_sim/manager_gui.py`

- [ ] **Step 1: Write copy helper tests**

Create `tests/test_copy_quality.py`:

```python
from dodgeball_sim.copy_quality import has_unresolved_token, title_label


def test_has_unresolved_token_detects_raw_ids_and_template_blanks():
    assert has_unresolved_token("MVP: aurora_3")
    assert has_unresolved_token("Winner: {winner}")
    assert has_unresolved_token("Prospect: <name>")


def test_has_unresolved_token_allows_normal_sports_copy():
    assert not has_unresolved_token("MVP: Mara Voss")
    assert not has_unresolved_token("Aurora Pilots Win The Final")


def test_title_label_normalizes_common_ui_labels():
    assert title_label("sim to next user match") == "Sim To Next User Match"
    assert title_label("mvp") == "MVP"
    assert title_label("hall of fame") == "Hall Of Fame"
```

- [ ] **Step 2: Run failing tests**

Run: `python -m pytest tests/test_copy_quality.py -q`

Expected: fail because `copy_quality.py` does not exist.

- [ ] **Step 3: Implement `copy_quality.py`**

Create `src/dodgeball_sim/copy_quality.py`:

```python
from __future__ import annotations

import re

_RAW_ID_RE = re.compile(r"\b[a-z]+_[0-9]+\b")
_TEMPLATE_RE = re.compile(r"(\{[^}]+\}|<[^>]+>)")
_ACRONYMS = {"mvp": "MVP", "ovr": "OVR", "rng": "RNG", "hof": "HOF"}


def has_unresolved_token(text: str) -> bool:
    return bool(_RAW_ID_RE.search(text) or _TEMPLATE_RE.search(text))


def title_label(text: str) -> str:
    words = str(text).replace("_", " ").split()
    return " ".join(_ACRONYMS.get(word.lower(), word.capitalize()) for word in words)


__all__ = ["has_unresolved_token", "title_label"]
```

- [ ] **Step 4: Use `title_label()` in obvious label generation**

In `src/dodgeball_sim/manager_gui.py`, import:

```python
from .copy_quality import title_label
```

Replace direct award title formatting like:

```python
award.award_type.replace("_", " ").title()
```

with:

```python
title_label(award.award_type)
```

- [ ] **Step 5: Run copy tests**

Run: `python -m pytest tests/test_copy_quality.py -q`

Expected: pass.

- [ ] **Step 6: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/copy_quality.py src/dodgeball_sim/manager_gui.py tests/test_copy_quality.py
git commit -m "Add copy quality helpers"
```

---

### Task 10: Visual System Pass On Core Screens

**Files:**
- Modify: `src/dodgeball_sim/ui_style.py`
- Modify: `src/dodgeball_sim/ui_components.py`
- Modify: `src/dodgeball_sim/manager_gui.py`

- [ ] **Step 1: Add missing styles**

In `src/dodgeball_sim/ui_style.py`, add:

```python
FONT_SUBTITLE = ("Segoe UI", 12)
FONT_BUTTON = ("Segoe UI Semibold", 10)
```

In `apply_theme()`, add:

```python
style.configure("Subtitle.TLabel", background=DM_CREAM, foreground=DM_MUTED_CHARCOAL, font=FONT_SUBTITLE)
style.configure("Action.TButton", background=DM_BURNT_ORANGE, foreground=DM_PAPER, bordercolor=DM_BORDER, padding=(14, 8), font=FONT_BUTTON)
style.map("Action.TButton", background=[("active", DM_BRICK), ("pressed", DM_BRICK)])
style.configure("Quiet.TButton", background=DM_OFF_WHITE_LINE, foreground=DM_CHARCOAL, bordercolor=DM_BORDER, padding=(12, 7), font=FONT_BUTTON)
style.map("Quiet.TButton", background=[("active", DM_PAPER), ("pressed", DM_PAPER)])
```

Add `FONT_SUBTITLE` and `FONT_BUTTON` to `__all__`.

- [ ] **Step 2: Add reusable page header**

In `src/dodgeball_sim/ui_components.py`, add:

```python
class PageHeader(ttk.Frame):
    def __init__(self, master: tk.Misc, title: str, subtitle: str = ""):
        super().__init__(master, style="TFrame")
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=title, style="Display.TLabel").grid(row=0, column=0, sticky="w")
        if subtitle:
            ttk.Label(self, text=subtitle, style="Subtitle.TLabel", wraplength=760).grid(row=1, column=0, sticky="w", pady=(4, 0))
```

Add `"PageHeader"` to `__all__`.

- [ ] **Step 3: Replace title/subtitle pairs on the core screens**

In `src/dodgeball_sim/manager_gui.py`, import `PageHeader` and update these screens:

```python
PageHeader(panel, "Dodgeball Manager", "Pick a club, build a season, and review every outcome from the engine log.").grid(row=0, column=0, sticky="ew")
```

Apply the same pattern to:

- `show_splash()`
- `show_club_picker()`
- `show_build_a_club_form()`
- `show_scouting_center()`
- `show_offseason_draft_beat()`
- `show_sim_digest()`

- [ ] **Step 4: Replace primary action button style**

For the primary action in each changed screen, use `style="Action.TButton"`. For secondary actions, use `style="Quiet.TButton"` where the action is not the primary next step.

- [ ] **Step 5: Run import smoke test**

Run: `python -c "from dodgeball_sim.manager_gui import ManagerModeApp, format_sim_digest_text, replay_event_summary; from dodgeball_sim.ui_components import PageHeader"`

Expected: exits with no output.

- [ ] **Step 6: Run focused tests**

Run: `python -m pytest tests/test_manager_gui.py tests/test_copy_quality.py -q`

Expected: pass.

- [ ] **Step 7: Checkpoint**

If in a Git worktree:

```bash
git add src/dodgeball_sim/ui_style.py src/dodgeball_sim/ui_components.py src/dodgeball_sim/manager_gui.py
git commit -m "Apply V3 visual system pass"
```

---

### Task 11: Verification Sweep And Screenshot Evidence

**Files:**
- Modify if needed: `docs/specs/2026-04-29-v3-experience-rebuild/design.md`
- Create if screenshots are captured: `output/ui-review-v3/`

- [ ] **Step 1: Run focused tests**

Run:

```bash
python -m pytest tests/test_lineup.py tests/test_v3_roster_integrity.py tests/test_v3_pacing.py tests/test_copy_quality.py tests/test_recruitment.py tests/test_manager_gui.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full suite**

Run:

```bash
python -m pytest -q
```

Expected: full suite passes. If local pytest cache warnings occur but tests pass, note that in the handoff.

- [ ] **Step 3: Capture GUI screenshots when the environment supports Tkinter**

If Tkinter can open windows in the current environment, capture screenshots for:

- splash
- hub
- roster/lineup
- replay arena
- match report
- scouting center
- recruitment day
- simulation digest

Save under `output/ui-review-v3/` with names:

```text
01-splash.png
02-hub.png
03-roster-lineup.png
04-replay-arena.png
05-match-report.png
06-scouting-center.png
07-recruitment-day.png
08-sim-digest.png
```

If Tkinter cannot render in the environment, run this import smoke test instead and state that visual QA remains manual:

```bash
python -c "from dodgeball_sim.manager_gui import ManagerModeApp, initialize_manager_career, initialize_build_a_club_career, replay_event_summary, format_sim_digest_text"
```

- [ ] **Step 4: Update spec status only after implementation ships**

When all tasks pass and visual QA is complete, update `docs/specs/MILESTONES.md` V3 status from `Designed (2026-04-29)` to `Shipped (YYYY-MM-DD)`. Do not mark shipped before implementation and verification are done.

- [ ] **Step 5: Final checkpoint**

If in a Git worktree:

```bash
git add docs/specs/MILESTONES.md output/ui-review-v3
git commit -m "Verify V3 experience rebuild"
```

---

## Self-Review Notes

Spec coverage:

- Court truth and roster integrity: Tasks 1-4.
- Match/replay rebuild: Task 5 and Task 10.
- Pacing controls and digest: Tasks 6-7.
- Visual hierarchy: Task 10 and screenshot verification in Task 11.
- Writing, names, flavor: Tasks 8-9.
- Verification: Task 11.

Scope control:

- This plan does not add facilities, meta patches, rivalries, or deep new tactical systems.
- The engine remains pure; active-player enforcement stays in lineup/franchise/manager boundaries.
- Bulk sim uses the same deterministic matchday path rather than a shortcut simulator.
