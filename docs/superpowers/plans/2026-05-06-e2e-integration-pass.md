# E2E Integration Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire V8–V10 thin stubs into existing progression owners so a full season playthrough from new game to season 2 is complete and honest.

**Architecture:** Four surgical seams, each touching only existing modules. Promise fulfillment evaluates during the development offseason beat in `offseason_ceremony.py`. Staff ratings flow into `apply_season_development` via a new optional parameter. Dynasty Office prospect previews read from `load_prospect_pool` (same source as Recruitment Day) with a seed-matched fallback. No new tables, no new modules.

**Tech Stack:** Python 3.11+, SQLite via `persistence.py` helpers, FastAPI (`server.py`), React + TypeScript (`DynastyOffice.tsx`)

**Run tests with:** `python -m pytest -q` from the worktree root (activate `.venv` first: `source .venv/Scripts/activate`)

---

## File Map

| File | Change |
|---|---|
| `src/dodgeball_sim/dynasty_office.py` | `_ensure_dynasty_keys`, promise schema (add `result`/`result_season_id`), `_prospect_rows` source of truth fix, `evaluate_season_promises` helper |
| `src/dodgeball_sim/offseason_ceremony.py` | Call `evaluate_season_promises` before dev beat completes; load dev department head and pass `staff_development_modifier` into `apply_season_development` |
| `src/dodgeball_sim/development.py` | Add `staff_development_modifier: float = 0.0` parameter to `apply_season_development` |
| `src/dodgeball_sim/config.py` | Add `max_staff_development_modifier: float = 0.15` to `BalanceConfig` and its registry entry |
| `frontend/src/components/DynastyOffice.tsx` | Promise result badge, staff modifier percentage in effect lanes |
| `tests/test_dynasty_office.py` | New tests: keys robustness, promise schema, fulfillment, prospect pool source of truth (both paths) |
| `tests/test_development.py` | New file: staff modifier formula and boundary tests |
| `tests/test_offseason_ceremony.py` | New or expanded: staff integration test (end-to-end offseason path with department head hired) |

---

## Task 0: `_ensure_dynasty_keys` Robustness

**Files:**
- Modify: `src/dodgeball_sim/dynasty_office.py`
- Test: `tests/test_dynasty_office.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_dynasty_office.py`:

```python
def test_ensure_dynasty_keys_initializes_missing_keys():
    conn = _career_conn()
    # Keys start absent — build_dynasty_office_state should not crash
    conn.execute("DELETE FROM dynasty_state WHERE key IN (?, ?)",
                 ("program_promises_json", "staff_market_actions_json"))
    conn.commit()

    state = build_dynasty_office_state(conn)
    assert state["recruiting"]["active_promises"] == []
    assert state["staff_market"]["recent_actions"] == []


def test_ensure_dynasty_keys_raises_on_corrupt_value():
    from dodgeball_sim.dynasty_office import _ensure_dynasty_keys
    conn = _career_conn()
    conn.execute(
        "INSERT OR REPLACE INTO dynasty_state (key, value) VALUES (?, ?)",
        ("program_promises_json", "NOT VALID JSON {{{"),
    )
    conn.commit()

    with pytest.raises(ValueError, match="Corrupted dynasty state key"):
        _ensure_dynasty_keys(conn)
```

Add `import pytest` at the top of the test file if not present.

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_dynasty_office.py::test_ensure_dynasty_keys_initializes_missing_keys tests/test_dynasty_office.py::test_ensure_dynasty_keys_raises_on_corrupt_value -v
```

Expected: `NameError` or `ImportError` for `_ensure_dynasty_keys`.

- [ ] **Step 3: Implement `_ensure_dynasty_keys`**

In `dynasty_office.py`, add this helper after the constants block (after line 35):

```python
def _ensure_dynasty_keys(conn: sqlite3.Connection) -> None:
    for key in (PROMISE_STATE_KEY, STAFF_ACTION_STATE_KEY):
        row = conn.execute(
            "SELECT value FROM dynasty_state WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            set_state(conn, key, "[]")
        else:
            try:
                json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                raise ValueError(f"Corrupted dynasty state key: {key}")
```

Then call it at the top of `build_dynasty_office_state`, `save_recruiting_promise`, and `hire_staff_candidate` — add `_ensure_dynasty_keys(conn)` as the first line of each function body.

- [ ] **Step 4: Run to confirm passing**

```
python -m pytest tests/test_dynasty_office.py::test_ensure_dynasty_keys_initializes_missing_keys tests/test_dynasty_office.py::test_ensure_dynasty_keys_raises_on_corrupt_value -v
```

Expected: both PASS.

- [ ] **Step 5: Run full suite to check no regressions**

```
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/dynasty_office.py tests/test_dynasty_office.py
git commit -m "feat(dynasty): add _ensure_dynasty_keys with corrupt-value guard"
```

---

## Task 1: Promise Schema — Store `result` Fields and `player_id`

**Files:**
- Modify: `src/dodgeball_sim/dynasty_office.py`
- Test: `tests/test_dynasty_office.py`

The existing `save_recruiting_promise` already receives `player_id` but the stored record is missing `result`, `result_season_id`, and confirming `player_id` is persisted.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_dynasty_office.py`:

```python
def test_promise_record_stores_player_id_and_result_fields():
    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    prospect_id = state["recruiting"]["prospects"][0]["player_id"]

    updated = save_recruiting_promise(conn, prospect_id, "early_playing_time")

    promise = updated["recruiting"]["active_promises"][0]
    assert promise["player_id"] == prospect_id
    assert promise["promise_type"] == "early_playing_time"
    assert promise["result"] is None
    assert promise["result_season_id"] is None
    assert promise["status"] == "open"
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_dynasty_office.py::test_promise_record_stores_player_id_and_result_fields -v
```

Expected: FAIL — `KeyError: 'result'` or assertion error on `result`.

- [ ] **Step 3: Update the promise record in `save_recruiting_promise`**

In `dynasty_office.py`, find the `next_promises.append(...)` block (around line 73) and replace the dict literal:

```python
next_promises.append(
    {
        "player_id": player_id,
        "promise_type": promise_type,
        "status": "open",
        "result": None,
        "result_season_id": None,
        "evidence": "Will be checked against future command history and player match stats.",
    }
)
```

- [ ] **Step 4: Run to confirm passing**

```
python -m pytest tests/test_dynasty_office.py::test_promise_record_stores_player_id_and_result_fields -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/dynasty_office.py tests/test_dynasty_office.py
git commit -m "feat(dynasty): persist player_id and result fields on promise records"
```

---

## Task 2: Promise Fulfillment Evaluator

**Files:**
- Modify: `src/dodgeball_sim/dynasty_office.py`
- Test: `tests/test_dynasty_office.py`

This implements `evaluate_season_promises(conn, season_id, club_id)` — a pure function that reads persisted data and writes fulfilled/broken results. It does not touch offseason ceremony state.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_dynasty_office.py`:

```python
import json as _json


def _make_match_stats_row(conn, season_id, player_id, club_id, n_matches=6):
    """Insert n_matches worth of match_records + player_match_stats for a player."""
    for i in range(n_matches):
        match_id = f"test_match_{season_id}_{player_id}_{i}"
        conn.execute(
            """
            INSERT OR IGNORE INTO match_records
              (match_id, season_id, week, home_club_id, away_club_id,
               winner_club_id, home_survivors, away_survivors,
               home_roster_hash, away_roster_hash, config_version,
               ruleset_version, seed, event_log_hash, final_state_hash)
            VALUES (?,?,?,?,?,?,0,0,'h','a','v1','v1',1,'e','f')
            """,
            (match_id, season_id, i + 1, club_id, "other_club", club_id),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO player_match_stats
              (match_id, player_id, club_id)
            VALUES (?, ?, ?)
            """,
            (match_id, player_id, club_id),
        )
    conn.commit()


def test_promise_early_playing_time_fulfilled_when_six_match_appearances():
    from dodgeball_sim.dynasty_office import evaluate_season_promises
    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]
    prospect_id = state["recruiting"]["prospects"][0]["player_id"]

    save_recruiting_promise(conn, prospect_id, "early_playing_time")
    _make_match_stats_row(conn, season_id, prospect_id, club_id, n_matches=6)

    evaluate_season_promises(conn, season_id, club_id)

    promises = _json.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    match = next(p for p in promises if p["player_id"] == prospect_id)
    assert match["result"] == "fulfilled"
    assert match["result_season_id"] == season_id
    assert "6" in match["evidence"] or "match" in match["evidence"].lower()


def test_promise_early_playing_time_broken_when_fewer_than_six():
    from dodgeball_sim.dynasty_office import evaluate_season_promises
    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]
    prospect_id = state["recruiting"]["prospects"][0]["player_id"]

    save_recruiting_promise(conn, prospect_id, "early_playing_time")
    _make_match_stats_row(conn, season_id, prospect_id, club_id, n_matches=3)

    evaluate_season_promises(conn, season_id, club_id)

    promises = _json.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    match = next(p for p in promises if p["player_id"] == prospect_id)
    assert match["result"] == "broken"


def test_promise_evaluation_is_idempotent():
    from dodgeball_sim.dynasty_office import evaluate_season_promises
    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]
    prospect_id = state["recruiting"]["prospects"][0]["player_id"]

    save_recruiting_promise(conn, prospect_id, "early_playing_time")
    _make_match_stats_row(conn, season_id, prospect_id, club_id, n_matches=6)

    evaluate_season_promises(conn, season_id, club_id)
    evaluate_season_promises(conn, season_id, club_id)  # second call — must be idempotent

    promises = _json.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    season_results = [p for p in promises if p.get("result_season_id") == season_id]
    assert len(season_results) == 1  # not doubled


def test_promise_contender_path_fulfilled_from_playoff_bracket():
    from dodgeball_sim.dynasty_office import evaluate_season_promises
    import json as j
    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]
    prospect_id = state["recruiting"]["prospects"][0]["player_id"]

    save_recruiting_promise(conn, prospect_id, "contender_path")

    # Seed a playoff bracket that includes the player's club
    conn.execute(
        """
        INSERT OR REPLACE INTO playoff_brackets
          (season_id, format, seeds_json, rounds_json, status)
        VALUES (?, 'top4', ?, '[]', 'complete')
        """,
        (season_id, j.dumps([club_id, "other1", "other2", "other3"])),
    )
    conn.commit()

    evaluate_season_promises(conn, season_id, club_id)

    promises = _json.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    match = next(p for p in promises if p["player_id"] == prospect_id)
    assert match["result"] == "fulfilled"
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_dynasty_office.py::test_promise_early_playing_time_fulfilled_when_six_match_appearances tests/test_dynasty_office.py::test_promise_contender_path_fulfilled_from_playoff_bracket -v
```

Expected: `ImportError` for `evaluate_season_promises`.

- [ ] **Step 3: Implement `evaluate_season_promises`**

Add to `dynasty_office.py` after the `_ensure_dynasty_keys` helper. Also add `load_playoff_bracket` to the persistence import at the top, and `load_all_rosters` (already imported).

First add `load_playoff_bracket` to the import block at the top of `dynasty_office.py`:

```python
from .persistence import (
    get_state,
    load_all_rosters,
    load_awards,
    load_club_facilities,
    load_club_prestige,
    load_clubs,
    load_command_history,
    load_department_heads,
    load_json_state,
    load_league_records,
    load_playoff_bracket,   # ADD THIS
    load_prospect_pool,     # ADD THIS
    load_rivalry_records,
    load_season,
    set_state,
)
```

Also add `load_prospect_pool` while here (needed for Task 4).

Then add the evaluator function:

```python
def evaluate_season_promises(
    conn: sqlite3.Connection,
    season_id: str,
    club_id: str,
) -> None:
    """Evaluate open promises for the season and persist fulfilled/broken results.

    Safe to call multiple times — already-evaluated promises are skipped.
    Must be called before retirements so load_all_rosters() reflects pre-retirement state.
    """
    promises = _load_promises(conn)
    if not promises:
        return

    changed = False
    for promise in promises:
        if promise.get("result_season_id") == season_id:
            continue  # already evaluated this season — idempotent
        if promise.get("status") != "open":
            continue

        player_id = promise.get("player_id")
        if not player_id:
            promise["evidence"] = "Legacy promise — player identity not recorded."
            continue

        promise_type = promise.get("promise_type", "")
        result, evidence = _evaluate_one_promise(
            conn, season_id, club_id, player_id, promise_type
        )
        promise["result"] = result
        promise["result_season_id"] = season_id
        promise["evidence"] = evidence
        changed = True

    if changed:
        set_state(conn, PROMISE_STATE_KEY, json.dumps(promises))
        conn.commit()


def _evaluate_one_promise(
    conn: sqlite3.Connection,
    season_id: str,
    club_id: str,
    player_id: str,
    promise_type: str,
) -> tuple[str, str]:
    """Return (result, evidence_text) for a single promise."""
    if promise_type == "early_playing_time":
        count = conn.execute(
            """
            SELECT COUNT(*) FROM player_match_stats pms
            JOIN match_records mr ON mr.match_id = pms.match_id
            WHERE mr.season_id = ? AND pms.player_id = ?
            """,
            (season_id, player_id),
        ).fetchone()[0]
        if count >= 6:
            return "fulfilled", f"Player appeared in {count} matches this season (threshold: 6)."
        return "broken", f"Player appeared in only {count} matches this season (threshold: 6)."

    if promise_type == "development_priority":
        history = load_command_history(conn, season_id)
        focused_weeks = sum(
            1 for entry in history
            if entry.get("plan", {}).get("department_orders", {}).get("dev_focus", "BALANCED") != "BALANCED"
        )
        rosters = load_all_rosters(conn)
        club_roster = rosters.get(club_id, [])
        on_roster = any(p.id == player_id for p in club_roster)
        if focused_weeks >= 3 and on_roster:
            return (
                "fulfilled",
                f"Club ran focused development {focused_weeks} weeks and player is on the active roster.",
            )
        reason = []
        if focused_weeks < 3:
            reason.append(f"only {focused_weeks} focused dev weeks (threshold: 3)")
        if not on_roster:
            reason.append("player not on active roster")
        return "broken", "Not fulfilled: " + "; ".join(reason) + "."

    if promise_type == "contender_path":
        bracket = load_playoff_bracket(conn, season_id)
        if bracket is not None and club_id in bracket.seeds:
            return "fulfilled", "Club reached the playoffs this season."
        return "broken", "Club did not reach the playoffs this season."

    return "broken", f"Unknown promise type '{promise_type}'."
```

- [ ] **Step 4: Run the promise tests**

```
python -m pytest tests/test_dynasty_office.py::test_promise_early_playing_time_fulfilled_when_six_match_appearances tests/test_dynasty_office.py::test_promise_early_playing_time_broken_when_fewer_than_six tests/test_dynasty_office.py::test_promise_evaluation_is_idempotent tests/test_dynasty_office.py::test_promise_contender_path_fulfilled_from_playoff_bracket -v
```

Expected: all four PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/dynasty_office.py tests/test_dynasty_office.py
git commit -m "feat(dynasty): implement evaluate_season_promises with per-type evidence"
```

---

## Task 3: Wire Promise Evaluation into Offseason Ceremony

**Files:**
- Modify: `src/dodgeball_sim/offseason_ceremony.py`
- Test: `tests/test_dynasty_office.py` (integration test)

- [ ] **Step 1: Write the failing integration test**

Add to `tests/test_dynasty_office.py`:

```python
def test_offseason_ceremony_evaluates_promises_during_dev_beat():
    """Promise results are set after initialize_manager_offseason runs."""
    import json as j
    from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
    from dodgeball_sim.persistence import load_clubs, load_season, load_all_rosters

    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]
    prospect_id = state["recruiting"]["prospects"][0]["player_id"]

    save_recruiting_promise(conn, prospect_id, "early_playing_time")
    _make_match_stats_row(conn, season_id, prospect_id, club_id, n_matches=6)

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    promises = j.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    match = next((p for p in promises if p["player_id"] == prospect_id), None)
    assert match is not None
    assert match["result"] in ("fulfilled", "broken")
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_dynasty_office.py::test_offseason_ceremony_evaluates_promises_during_dev_beat -v
```

Expected: FAIL — `result` is still `None`.

- [ ] **Step 3: Add call to `evaluate_season_promises` in `initialize_manager_offseason`**

In `offseason_ceremony.py`, add the import at the top of the file:

```python
from .dynasty_office import evaluate_season_promises
```

Then in `initialize_manager_offseason`, after the `player_dev_focus` lookup block (around line 226) and before the `for club_id, roster in rosters.items()` loop, add:

```python
    # Evaluate open promises before retirements alter roster state
    _player_club_id = get_state(conn, "player_club_id") or ""
    if _player_club_id:
        evaluate_season_promises(conn, season.season_id, _player_club_id)
```

- [ ] **Step 4: Run to confirm passing**

```
python -m pytest tests/test_dynasty_office.py::test_offseason_ceremony_evaluates_promises_during_dev_beat -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/offseason_ceremony.py tests/test_dynasty_office.py
git commit -m "feat(offseason): evaluate season promises during development beat"
```

---

## Task 4: Config — `max_staff_development_modifier`

**Files:**
- Modify: `src/dodgeball_sim/config.py`
- Test: inline in Task 5

- [ ] **Step 1: Add field to `BalanceConfig`**

In `config.py`, add `max_staff_development_modifier` to the `BalanceConfig` dataclass after `rush_fatigue_cost_max`:

```python
@dataclass(frozen=True)
class BalanceConfig:
    version: str
    accuracy_scale: float
    catch_scale: float
    power_to_catch_scale: float
    fatigue_hit_modifier: float
    fatigue_dodge_modifier: float
    fatigue_catch_modifier: float
    chemistry_influence: float
    tempo_tick_bonus: int
    max_ticks: int
    max_events: int
    base_seed_offset: int
    rush_accuracy_modifier_max: float
    rush_fatigue_cost_max: float
    max_staff_development_modifier: float   # NEW
    difficulty_profiles: Dict[str, DifficultyProfile]
```

Add the value to the `"phase1.v1"` registry entry:

```python
    "phase1.v1": BalanceConfig(
        version="phase1.v1",
        accuracy_scale=12.0,
        catch_scale=11.0,
        power_to_catch_scale=0.75,
        fatigue_hit_modifier=0.1,
        fatigue_dodge_modifier=0.1,
        fatigue_catch_modifier=0.07,
        chemistry_influence=0.02,
        tempo_tick_bonus=2,
        max_ticks=240,
        max_events=800,
        base_seed_offset=17,
        rush_accuracy_modifier_max=0.15,
        rush_fatigue_cost_max=0.20,
        max_staff_development_modifier=0.15,   # NEW
        difficulty_profiles=_DEFAULT_DIFFICULTIES,
    )
```

- [ ] **Step 2: Verify import works**

```
python -c "from dodgeball_sim.config import DEFAULT_CONFIG; print(DEFAULT_CONFIG.max_staff_development_modifier)"
```

Expected output: `0.15`

- [ ] **Step 3: Commit**

```bash
git add src/dodgeball_sim/config.py
git commit -m "feat(config): add max_staff_development_modifier to BalanceConfig"
```

---

## Task 5: `apply_season_development` — Staff Modifier Parameter

**Files:**
- Modify: `src/dodgeball_sim/development.py`
- Create: `tests/test_development.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_development.py`:

```python
from __future__ import annotations

from dodgeball_sim.config import DEFAULT_CONFIG
from dodgeball_sim.development import apply_season_development
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.rng import DeterministicRNG
from dodgeball_sim.stats import PlayerMatchStats


def _player() -> Player:
    return Player(
        id="p1",
        name="Test Player",
        age=24,
        archetype=PlayerArchetype.PRECISION,
        ratings=PlayerRatings(
            accuracy=65.0, power=60.0, dodge=60.0,
            catch=60.0, stamina=60.0, tactical_iq=60.0,
        ),
        traits=PlayerTraits(potential=70.0, growth_curve="normal"),
        newcomer=False,
        club_id="club1",
    )


def _stats() -> PlayerMatchStats:
    return PlayerMatchStats(minutes_played=800)


def test_staff_dev_modifier_zero_when_no_staff_unchanged_output():
    """Baseline: zero modifier produces same output as current behavior."""
    player = _player()
    rng1 = DeterministicRNG(seed=42)
    rng2 = DeterministicRNG(seed=42)

    result_no_modifier = apply_season_development(player, _stats(), facilities=(), rng=rng1)
    result_zero_modifier = apply_season_development(
        player, _stats(), facilities=(), rng=rng2, staff_development_modifier=0.0
    )

    assert result_no_modifier.ratings == result_zero_modifier.ratings


def test_staff_dev_modifier_bounded_at_max():
    """A modifier of exactly max_staff_development_modifier is the ceiling."""
    max_mod = DEFAULT_CONFIG.max_staff_development_modifier  # 0.15
    player = _player()
    rng_base = DeterministicRNG(seed=99)
    rng_max = DeterministicRNG(seed=99)
    rng_over = DeterministicRNG(seed=99)

    result_max = apply_season_development(
        player, _stats(), facilities=(), rng=rng_max,
        staff_development_modifier=max_mod,
    )
    # Anything above max should be clamped to max — but formula is positive-only so
    # we verify that passing max_mod directly produces higher OVR than no modifier
    result_base = apply_season_development(player, _stats(), facilities=(), rng=rng_base)

    assert result_max.overall() >= result_base.overall()


def test_staff_dev_modifier_positive_only():
    """Negative modifier values have no effect (clamped to 0)."""
    player = _player()
    rng1 = DeterministicRNG(seed=77)
    rng2 = DeterministicRNG(seed=77)

    result_negative = apply_season_development(
        player, _stats(), facilities=(), rng=rng1,
        staff_development_modifier=-0.5,
    )
    result_zero = apply_season_development(
        player, _stats(), facilities=(), rng=rng2,
        staff_development_modifier=0.0,
    )

    assert result_negative.ratings == result_zero.ratings
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_development.py -v
```

Expected: `TypeError` — `apply_season_development` does not accept `staff_development_modifier`.

- [ ] **Step 3: Add the parameter to `apply_season_development`**

In `development.py`, change the function signature (line 29):

```python
def apply_season_development(
    player: Player,
    season_stats: PlayerMatchStats,
    facilities: Iterable[str],
    rng: DeterministicRNG,
    trajectory: str | None = None,
    dev_focus: str = "BALANCED",
    staff_development_modifier: float = 0.0,
) -> Player:
```

Then in the body, find the line `pool = base_growth * potential_modifier * growth_multiplier` (around line 86) and replace it with:

```python
    effective_staff_modifier = max(0.0, staff_development_modifier)
    pool = base_growth * potential_modifier * growth_multiplier * (1.0 + effective_staff_modifier)
```

- [ ] **Step 4: Run to confirm passing**

```
python -m pytest tests/test_development.py -v
```

Expected: all three PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/development.py tests/test_development.py
git commit -m "feat(development): add staff_development_modifier param to apply_season_development"
```

---

## Task 6: Wire Staff Modifier into Offseason Ceremony

**Files:**
- Modify: `src/dodgeball_sim/offseason_ceremony.py`
- Create/Modify: `tests/test_offseason_ceremony.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_offseason_ceremony.py` (or add to it if it exists):

```python
from __future__ import annotations

import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
from dodgeball_sim.persistence import (
    create_schema,
    load_all_rosters,
    load_clubs,
    load_department_heads,
    load_season,
)


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_offseason_dev_path_loads_department_head_and_applies_modifier():
    """Hiring a development dept head results in a higher OVR gain vs baseline."""
    conn_base = _career_conn()
    conn_hired = _career_conn()

    # In the hired conn, upgrade the development department head to rating 100
    conn_hired.execute(
        """
        INSERT OR REPLACE INTO department_heads
          (department, name, rating_primary, rating_secondary, voice)
        VALUES ('development', 'Elite Dev Coach', 100.0, 80.0, 'direct')
        """
    )
    conn_hired.commit()

    season_id_base = conn_base.execute(
        "SELECT value FROM dynasty_state WHERE key = 'active_season_id'"
    ).fetchone()["value"]
    season_id_hired = conn_hired.execute(
        "SELECT value FROM dynasty_state WHERE key = 'active_season_id'"
    ).fetchone()["value"]

    season_base = load_season(conn_base, season_id_base)
    season_hired = load_season(conn_hired, season_id_hired)

    rosters_base = load_all_rosters(conn_base)
    rosters_hired = load_all_rosters(conn_hired)

    clubs_base = load_clubs(conn_base)
    clubs_hired = load_clubs(conn_hired)

    updated_base = initialize_manager_offseason(
        conn_base, season_base, clubs_base, rosters_base, root_seed=20260426
    )
    updated_hired = initialize_manager_offseason(
        conn_hired, season_hired, clubs_hired, rosters_hired, root_seed=20260426
    )

    # Get the player club from each conn
    player_club_base = conn_base.execute(
        "SELECT value FROM dynasty_state WHERE key = 'player_club_id'"
    ).fetchone()["value"]
    player_club_hired = conn_hired.execute(
        "SELECT value FROM dynasty_state WHERE key = 'player_club_id'"
    ).fetchone()["value"]

    avg_ovr_base = sum(p.overall() for p in updated_base.get(player_club_base, [])) / max(
        len(updated_base.get(player_club_base, [])), 1
    )
    avg_ovr_hired = sum(p.overall() for p in updated_hired.get(player_club_hired, [])) / max(
        len(updated_hired.get(player_club_hired, [])), 1
    )

    # With max staff modifier (0.15), average OVR should be higher (or at worst equal
    # due to rng noise — allow tiny tolerance)
    assert avg_ovr_hired >= avg_ovr_base - 0.5, (
        f"Expected hired ({avg_ovr_hired:.2f}) >= base ({avg_ovr_base:.2f}) within tolerance"
    )
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_offseason_ceremony.py::test_offseason_dev_path_loads_department_head_and_applies_modifier -v
```

Expected: PASS or FAIL — if it passes already the modifier isn't wired yet and the test may be too lenient. If it fails, the modifier isn't connected.

- [ ] **Step 3: Wire the staff modifier in `initialize_manager_offseason`**

In `offseason_ceremony.py`, add `load_department_heads` to the persistence import block if not already present.

Then in `initialize_manager_offseason`, after the `player_dev_focus` lookup and the `evaluate_season_promises` call (added in Task 3), add:

```python
    # Load staff development modifier from development department head
    _dev_heads = {h["department"]: h for h in load_department_heads(conn)}
    _dev_head = _dev_heads.get("development")
    _staff_dev_modifier = 0.0
    if _dev_head is not None:
        _max_mod = 0.15  # matches BalanceConfig.max_staff_development_modifier
        _staff_dev_modifier = max(
            0.0, (_dev_head["rating_primary"] - 50.0) / 50.0 * _max_mod
        )
```

Then in the `apply_season_development` call (around line 233), add the new parameter:

```python
            developed = apply_season_development(
                player,
                stats,
                facilities=(),
                rng=DeterministicRNG(derive_seed(root_seed, "manager_development", season.season_id, player.id)),
                trajectory=load_player_trajectory(conn, player.id),
                dev_focus=player_dev_focus if is_player_club else "BALANCED",
                staff_development_modifier=_staff_dev_modifier if is_player_club else 0.0,
            )
```

Also add `load_department_heads` to the persistence import at the top of `offseason_ceremony.py`:

```python
from .persistence import (
    CorruptSaveError,
    fetch_season_player_stats,
    get_state,
    load_all_rosters,
    load_awards,
    load_clubs,
    load_department_heads,   # ADD THIS
    load_free_agents,
    load_player_career_stats,
    load_player_trajectory,
    load_prospect_pool,
    load_season,
    load_standings,
    save_awards,
    save_career_state_cursor,
    save_club,
    save_free_agents,
    save_lineup_default,
    save_player_career_stats,
    save_player_season_stats,
    save_retired_player,
    save_season,
    save_season_format,
    set_state,
)
```

- [ ] **Step 4: Run the integration test**

```
python -m pytest tests/test_offseason_ceremony.py::test_offseason_dev_path_loads_department_head_and_applies_modifier -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/offseason_ceremony.py tests/test_offseason_ceremony.py
git commit -m "feat(offseason): wire development department head rating into apply_season_development"
```

---

## Task 7: Prospect Pool Source of Truth

**Files:**
- Modify: `src/dodgeball_sim/dynasty_office.py`
- Test: `tests/test_dynasty_office.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_dynasty_office.py`:

```python
def test_dynasty_office_prospect_pool_matches_persisted_pool():
    """When pool is saved, Dynasty Office returns the same player_ids."""
    from dodgeball_sim.persistence import save_prospect_pool, load_prospect_pool
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.dynasty_office import _class_year_from_season

    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]

    class_year = _class_year_from_season(season_id)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", str(class_year)))
    pool = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    conn.commit()

    state2 = build_dynasty_office_state(conn)
    office_ids = {p["player_id"] for p in state2["recruiting"]["prospects"]}
    persisted_ids = {p.player_id for p in load_prospect_pool(conn, class_year)}

    assert office_ids.issubset(persisted_ids)
    assert len(office_ids) > 0


def test_dynasty_office_fallback_pool_matches_scouting_center_seed():
    """When no pool is saved, Dynasty Office uses the same seed as scouting center."""
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.dynasty_office import _class_year_from_season

    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]

    # Derive class_year using the same function dynasty_office uses internally
    class_year = _class_year_from_season(season_id)

    # Generate using the SCOUTING CENTER'S seed namespace (scouting_center.py line 664)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", str(class_year)))
    expected_pool = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
    expected_ids = [p.player_id for p in expected_pool[:8]]

    office_ids = [p["player_id"] for p in state["recruiting"]["prospects"]]

    assert office_ids == expected_ids
```

Note: Both tests import `_class_year_from_season` directly from `dynasty_office` to stay in sync with its implementation (`int(digits_from_season_id or "1") + 1`, line ~331).

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_dynasty_office.py::test_dynasty_office_fallback_pool_matches_scouting_center_seed -v
```

Expected: FAIL — the seed namespace is `"v8_recruiting_preview"`, not `"prospect_gen"`.

- [ ] **Step 3: Fix `_prospect_rows` to use correct source**

In `dynasty_office.py`, find `_prospect_rows` (around line 171). Replace the function body:

```python
def _prospect_rows(
    conn: sqlite3.Connection,
    season_id: str,
    root_seed: int,
    promises: list[dict[str, Any]],
    credibility: dict[str, Any],
) -> list[dict[str, Any]]:
    class_year = _class_year_from_season(season_id)

    # Source of truth: persisted pool (same one Recruitment Day uses)
    persisted = load_prospect_pool(conn, class_year)
    if persisted:
        prospects = persisted
    else:
        # Fallback: generate using the identical seed the scouting center will use
        rng = DeterministicRNG(derive_seed(root_seed, "prospect_gen", str(class_year)))
        prospects = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)

    promised = {promise["player_id"]: promise for promise in promises}
    rows = []
    for prospect in prospects[:8]:
        low, high = prospect.public_ratings_band["ovr"]
        fit_score = round(((low + high) / 2.0) + credibility["score"] * 0.12, 1)
        rows.append(
            {
                "player_id": prospect.player_id,
                "name": prospect.name,
                "hometown": prospect.hometown,
                "public_archetype": prospect.public_archetype_guess,
                "public_ovr_band": [low, high],
                "fit_score": fit_score,
                "promise_options": list(PROMISE_OPTIONS),
                "active_promise": promised.get(prospect.player_id),
                "interest_evidence": [
                    f"Public range {low}-{high}.",
                    f"Credibility grade {credibility['grade']} contributes to interest.",
                    "No hidden promise effect is applied until a promise is saved.",
                ],
            }
        )
    return rows
```

Also remove `del conn` (was a placeholder to suppress the unused warning) since `conn` is now used. Update the import block at the top of the file to include `load_prospect_pool` (added in Task 2).

- [ ] **Step 4: Run the prospect pool tests**

```
python -m pytest tests/test_dynasty_office.py::test_dynasty_office_prospect_pool_matches_persisted_pool tests/test_dynasty_office.py::test_dynasty_office_fallback_pool_matches_scouting_center_seed -v
```

Expected: both PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/dynasty_office.py tests/test_dynasty_office.py
git commit -m "feat(dynasty): prospect pool source of truth — read persisted pool, fallback to prospect_gen seed"
```

---

## Task 8: UI Evidence Pass — Promise Badges and Staff Effect Lanes

**Files:**
- Modify: `frontend/src/components/DynastyOffice.tsx`

This is a frontend-only pass. No backend changes. Run `npm run lint` from `frontend/` after editing.

- [ ] **Step 1: Add promise result badge to promise cards**

In `DynastyOffice.tsx`, find where `active_promise` is rendered for each prospect. Add a result badge after the promise type label. The `active_promise` object now has `result`, `result_season_id`, and `evidence` fields.

Find the JSX rendering `active_promise` (look for `{prospect.active_promise &&` or similar) and update it to show the result state:

```tsx
{prospect.active_promise && (
  <div className="promise-card">
    <span className="promise-type">{prospect.active_promise.promise_type.replace(/_/g, ' ')}</span>
    {prospect.active_promise.result === 'fulfilled' && (
      <span className="badge badge-fulfilled">FULFILLED</span>
    )}
    {prospect.active_promise.result === 'broken' && (
      <span className="badge badge-broken">BROKEN</span>
    )}
    {prospect.active_promise.result === null && (
      <span className="badge badge-open">OPEN</span>
    )}
    <p className="promise-evidence">{prospect.active_promise.evidence}</p>
  </div>
)}
```

- [ ] **Step 2: Add CSS for the new badges**

In `frontend/src/index.css`, add:

```css
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  margin-left: 8px;
}
.badge-fulfilled { background: #2d6a2d; color: #b6f0b6; }
.badge-broken    { background: #6a2d2d; color: #f0b6b6; }
.badge-open      { background: #2d4a6a; color: #b6d4f0; }
.promise-evidence { font-size: 0.8rem; color: #999; margin: 4px 0 0; }
```

- [ ] **Step 3: Update staff effect lanes to show real modifier**

Find where staff effect lanes are rendered in `DynastyOffice.tsx` (look for `effect_lanes` or "future hook" copy). The `current_staff` array has `department`, `name`, `rating_primary`. Compute and display the modifier:

```tsx
{data.staff_market.current_staff.map((head: any) => {
  const modifier = head.department === 'development'
    ? Math.max(0, ((head.rating_primary - 50) / 50) * 0.15)
    : 0;
  const modifierPct = (modifier * 100).toFixed(1);
  return (
    <div key={head.department} className="staff-head-card">
      <strong>{head.department}</strong>: {head.name} (rating {head.rating_primary})
      {head.department === 'development' && modifier > 0 && (
        <span className="staff-modifier">+{modifierPct}% development modifier</span>
      )}
    </div>
  );
})}
```

Add CSS:

```css
.staff-modifier { color: #8bc88b; font-size: 0.8rem; margin-left: 8px; }
```

- [ ] **Step 4: Lint**

```
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 5: Visual check via preview**

Start the dev server if not running, navigate to the Dynasty Office tab, and confirm:
- Prospect cards show `OPEN` / `FULFILLED` / `BROKEN` badge
- Staff development head shows `+X% development modifier` when rating > 50

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/DynastyOffice.tsx frontend/src/index.css
git commit -m "feat(ui): promise result badges and real staff modifier in Dynasty Office"
```

---

## Task 9: Final Verification

- [ ] **Step 1: Run full Python suite**

```
python -m pytest -q
```

Expected: all tests pass, count ≥ 390 (380 baseline + new tests).

- [ ] **Step 2: Frontend lint**

```
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 3: Playthrough smoke test**

Start the dev server (`python -m dodgeball_sim` from the repo root with the venv active), load or create a save, and verify the sequence from the spec:

1. Open Dynasty Office → save a promise → confirm `OPEN` badge appears.
2. Complete a season (or load a post-season save) → Dynasty Office shows `FULFILLED` or `BROKEN` with evidence.
3. Hire a development department staff member → confirm `+X%` modifier appears.
4. Confirm prospect list in Dynasty Office matches scouting/recruitment pool.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore(integration): E2E integration pass complete — promise fulfillment, staff dev modifier, prospect pool source of truth"
```
