# Architecture Deepening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deepen six shallow modules by promoting private logic to public seams, introducing typed interfaces, splitting mixed-concern modules, and extracting orchestration from HTTP handlers.

**Architecture:** Work proceeds in dependency order — smaller pure-function promotions first, then module splits, then typed interfaces, then the HTTP use-case extraction last. Each task produces a self-contained commit with a passing test suite.

**Tech Stack:** Python 3.11, FastAPI, SQLite/sqlite3, React + TypeScript (Vite), pytest

---

## File Map

**New files:**
- `src/dodgeball_sim/event_types.py` — TypedDicts for each MatchEvent context shape
- `src/dodgeball_sim/matchup_details.py` — public DB-querying matchup details builder
- `src/dodgeball_sim/recruiting_office.py` — recruiting state, credibility, promises
- `src/dodgeball_sim/league_memory.py` — league memory state builder
- `src/dodgeball_sim/staff_market.py` — staff market state builder + hire helpers
- `src/dodgeball_sim/use_cases.py` — orchestration extracted from server.py endpoints
- `docs/superpowers/plans/2026-05-13-architecture-deepening.md` — this file

**Modified files:**
- `src/dodgeball_sim/offseason_ceremony.py` — promote `_apply_scouting_carry_forward` to public
- `src/dodgeball_sim/events.py` — annotate context with Union TypedDict
- `src/dodgeball_sim/command_center.py` — import from matchup_details.py
- `src/dodgeball_sim/dynasty_office.py` — thin facade delegating to sub-modules
- `src/dodgeball_sim/server.py` — delegate simulate endpoint to use_cases.py
- `frontend/src/types.ts` — type ReplayEvent.context as discriminated union; type OffseasonBeat.payload per key

---

## Task 1: Promote scouting carry-forward to public API

**Files:**
- Modify: `src/dodgeball_sim/offseason_ceremony.py`
- Test: `tests/test_offseason_ceremony.py`

Currently `_apply_scouting_carry_forward` is a private helper of `begin_next_season`. It orchestrates I/O but its pure core (`apply_carry_forward_decay`) already lives in `scouting_center.py`. Making the wrapper public gives a testable seam for "advance to new season and decay scouting knowledge" without running the full ceremony.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_offseason_ceremony.py`:

```python
def test_apply_scouting_carry_forward_is_importable():
    from dodgeball_sim.offseason_ceremony import apply_scouting_carry_forward
    assert callable(apply_scouting_carry_forward)


def test_apply_scouting_carry_forward_decays_verified_to_known(tmp_path):
    """Prospects that were VERIFIED become KNOWN after carry-forward."""
    from dodgeball_sim.offseason_ceremony import apply_scouting_carry_forward
    from dodgeball_sim.persistence import (
        connect, create_schema, load_scouting_state, save_scouting_state,
    )
    from dodgeball_sim.scouting_center import ScoutingState, ScoutingTier

    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    create_schema(conn)

    player_id = "prospect_1_001"
    # Insert a minimal prospect_pool row so the function can iterate
    conn.execute(
        """INSERT INTO prospect_pool
           (player_id, class_year, name, age, hometown,
            hidden_ratings_json, hidden_trajectory, hidden_traits_json,
            public_archetype_guess, public_ratings_band_json, is_signed)
           VALUES (?, 1, 'Test Player', 18, 'Somewhere',
            '{}', 'NORMAL', '[]', 'Sharpshooter', '{"ovr":[50,60]}', 0)""",
        (player_id,),
    )
    initial_state = ScoutingState(
        player_id=player_id,
        scout_id="auto",
        ratings_tier=ScoutingTier.VERIFIED.value,
        archetype_tier=ScoutingTier.VERIFIED.value,
        traits_tier=ScoutingTier.UNKNOWN.value,
        trajectory_tier=ScoutingTier.UNKNOWN.value,
        ratings_points=100,
        archetype_points=100,
        traits_points=0,
        trajectory_points=0,
    )
    save_scouting_state(conn, initial_state)
    conn.commit()

    apply_scouting_carry_forward(conn, prior_class_year=1)

    decayed = load_scouting_state(conn, player_id)
    assert decayed is not None
    assert decayed.ratings_tier == ScoutingTier.KNOWN.value
    assert decayed.archetype_tier == ScoutingTier.KNOWN.value
```

- [ ] **Step 2: Run the test to confirm it fails**

```
python -m pytest tests/test_offseason_ceremony.py::test_apply_scouting_carry_forward_is_importable -v
```

Expected: `ImportError: cannot import name 'apply_scouting_carry_forward'`

- [ ] **Step 3: Rename the private function in offseason_ceremony.py**

In `src/dodgeball_sim/offseason_ceremony.py`, rename `_apply_scouting_carry_forward` → `apply_scouting_carry_forward` (two places: definition and call site inside `begin_next_season`).

Find:
```python
def _apply_scouting_carry_forward(conn: sqlite3.Connection, prior_class_year: int) -> None:
```
Replace with:
```python
def apply_scouting_carry_forward(conn: sqlite3.Connection, prior_class_year: int) -> None:
```

Find the call site in `begin_next_season`:
```python
    _apply_scouting_carry_forward(conn, prior_season_num)
```
Replace with:
```python
    apply_scouting_carry_forward(conn, prior_season_num)
```

Add to `__all__` at the bottom of the file:
```python
"apply_scouting_carry_forward",
```

- [ ] **Step 4: Run the tests to confirm they pass**

```
python -m pytest tests/test_offseason_ceremony.py -v
```

Expected: PASS

- [ ] **Step 5: Run the full suite to check for regressions**

```
python -m pytest -q
```

Expected: all green

- [ ] **Step 6: Commit**

```
git add src/dodgeball_sim/offseason_ceremony.py tests/test_offseason_ceremony.py
git commit -m "refactor: promote _apply_scouting_carry_forward to public API"
```

---

## Task 2: Type MatchEvent context with TypedDicts

**Files:**
- Create: `src/dodgeball_sim/event_types.py`
- Modify: `src/dodgeball_sim/events.py`
- Modify: `frontend/src/types.ts`
- Test: `tests/test_event_types.py`

There are exactly three event types: `match_start`, `match_end`, and `throw`. Each emits a structurally different context dict. Replacing `Dict[str, Any]` with a Union of TypedDicts makes the interface self-documenting and lets callers (MatchReplay, KeyPlayers) trust the shape they receive.

- [ ] **Step 1: Write the failing test**

Create `tests/test_event_types.py`:

```python
from __future__ import annotations


def test_match_start_context_shape():
    from dodgeball_sim.event_types import MatchStartContext
    ctx: MatchStartContext = {
        "config_version": "phase1.v1",
        "difficulty": "pro",
        "meta_patch": None,
        "team_policies": {"team_a": {}, "team_b": {}},
    }
    assert ctx["difficulty"] == "pro"


def test_match_end_context_shape():
    from dodgeball_sim.event_types import MatchEndContext
    ctx: MatchEndContext = {"reason": "all_out"}
    assert ctx["reason"] == "all_out"


def test_throw_context_has_required_keys():
    from dodgeball_sim.event_types import ThrowContext
    # Verify TypedDict keys are correct by constructing a minimal valid one
    ctx: ThrowContext = {
        "tick": 1,
        "thrower_selection": {},
        "target_selection": {},
        "difficulty": "pro",
        "policy_snapshot": {},
        "chemistry_delta": 0.0,
        "meta_patch": None,
        "rush_context": {},
        "sync_context": {"is_synced": False, "sync_modifier": 0.0},
        "calc": {},
        "fatigue": {},
        "catch_decision": None,
        "pressure_context": {},
    }
    assert ctx["tick"] == 1


def test_engine_emits_typed_events():
    """End-to-end: engine events have context shapes matching their TypedDict."""
    from dodgeball_sim.engine import MatchEngine
    from dodgeball_sim.config import BalanceConfig
    from dodgeball_sim.models import MatchSetup, Team, Player, PlayerRatings, PlayerTraits

    def _player(pid: str) -> Player:
        return Player(
            id=pid, name=pid,
            ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
        )

    team_a = Team(id="a", name="A", players=tuple(_player(f"a{i}") for i in range(6)))
    team_b = Team(id="b", name="B", players=tuple(_player(f"b{i}") for i in range(6)))
    setup = MatchSetup(team_a=team_a, team_b=team_b)
    result = MatchEngine().run(setup, seed=1)

    start = next(e for e in result.events if e.event_type == "match_start")
    assert "config_version" in start.context
    assert "team_policies" in start.context

    end = next(e for e in result.events if e.event_type == "match_end")
    assert "reason" in end.context

    throw = next(e for e in result.events if e.event_type == "throw")
    for key in ("tick", "thrower_selection", "calc", "fatigue", "rush_context"):
        assert key in throw.context, f"Missing key: {key}"
```

- [ ] **Step 2: Run to confirm it fails**

```
python -m pytest tests/test_event_types.py -v
```

Expected: `ModuleNotFoundError: No module named 'dodgeball_sim.event_types'`

- [ ] **Step 3: Create event_types.py**

Create `src/dodgeball_sim/event_types.py`:

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from typing_extensions import TypedDict


class MatchStartContext(TypedDict):
    config_version: str
    difficulty: str
    meta_patch: Optional[Dict[str, Any]]
    team_policies: Dict[str, Dict[str, float]]


class MatchEndContext(TypedDict):
    reason: str


class ThrowContext(TypedDict):
    tick: int
    thrower_selection: Dict[str, Any]
    target_selection: Dict[str, Any]
    difficulty: str
    policy_snapshot: Dict[str, float]
    chemistry_delta: float
    meta_patch: Optional[Dict[str, Any]]
    rush_context: Dict[str, Any]
    sync_context: Dict[str, Any]
    calc: Dict[str, Any]
    fatigue: Dict[str, Any]
    catch_decision: Optional[Dict[str, Any]]
    pressure_context: Dict[str, Any]


EventContext = Union[MatchStartContext, MatchEndContext, ThrowContext]

__all__ = [
    "EventContext",
    "MatchEndContext",
    "MatchStartContext",
    "ThrowContext",
]
```

- [ ] **Step 4: Update events.py to import and annotate**

In `src/dodgeball_sim/events.py`, add the import and update the annotation:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Union

from .event_types import EventContext


@dataclass(frozen=True)
class MatchEvent:
    event_id: int
    tick: int
    seed: int
    event_type: str
    phase: str
    actors: Dict[str, Any]
    context: EventContext  # was Dict[str, Any]
    probabilities: Dict[str, float]
    rolls: Dict[str, float]
    outcome: Dict[str, Any]
    state_diff: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = ["MatchEvent"]
```

- [ ] **Step 5: Run tests**

```
python -m pytest tests/test_event_types.py tests/test_regression.py -v
```

Expected: PASS (the annotation is not enforced at runtime so engine.py needs no changes)

- [ ] **Step 6: Update frontend/src/types.ts**

Find the `ReplayEvent` interface and replace `context: Record<string, unknown>` with a typed union.

Replace:
```typescript
export interface ReplayEvent {
    index: number;
    tick: number;
    event_type: string;
    phase: string;
    actors: Record<string, string>;
    context: Record<string, unknown>;
```

With:
```typescript
export interface MatchStartContext {
    config_version: string;
    difficulty: string;
    meta_patch: Record<string, unknown> | null;
    team_policies: Record<string, Record<string, number>>;
}

export interface MatchEndContext {
    reason: string;
}

export interface ThrowContext {
    tick: number;
    thrower_selection: Record<string, unknown>;
    target_selection: Record<string, unknown>;
    difficulty: string;
    policy_snapshot: Record<string, number>;
    chemistry_delta: number;
    meta_patch: Record<string, unknown> | null;
    rush_context: Record<string, unknown>;
    sync_context: { is_synced: boolean; sync_modifier: number };
    calc: Record<string, unknown>;
    fatigue: Record<string, unknown>;
    catch_decision: Record<string, unknown> | null;
    pressure_context: Record<string, unknown>;
}

export type ReplayEventContext = MatchStartContext | MatchEndContext | ThrowContext;

export interface ReplayEvent {
    index: number;
    tick: number;
    event_type: 'match_start' | 'match_end' | 'throw';
    phase: string;
    actors: Record<string, string>;
    context: ReplayEventContext;
```

- [ ] **Step 7: Build frontend to confirm no TypeScript errors**

From `frontend/`:
```
npm run build
```

Expected: build succeeds with 0 type errors

- [ ] **Step 8: Run full suite**

```
python -m pytest -q
```

Expected: all green

- [ ] **Step 9: Commit**

```
git add src/dodgeball_sim/event_types.py src/dodgeball_sim/events.py frontend/src/types.ts tests/test_event_types.py
git commit -m "refactor: type MatchEvent.context with TypedDicts and TypeScript discriminated union"
```

---

## Task 3: Split dynasty_office.py into sub-modules

**Files:**
- Create: `src/dodgeball_sim/recruiting_office.py`
- Create: `src/dodgeball_sim/league_memory.py`
- Create: `src/dodgeball_sim/staff_market.py`
- Modify: `src/dodgeball_sim/dynasty_office.py`
- Test: `tests/test_dynasty_office.py` (add focused sub-module tests)

`dynasty_office.py` (614 lines) bundles recruiting, league memory, and staff market. Each concern has independent domain logic and test needs. After this task, `dynasty_office.py` becomes a thin facade: it loads shared context (season, clubs) and delegates to each sub-module.

- [ ] **Step 1: Write failing tests for the new sub-modules**

Add to `tests/test_dynasty_office.py`:

```python
def test_recruiting_office_module_is_importable():
    from dodgeball_sim.recruiting_office import build_recruiting_state
    assert callable(build_recruiting_state)


def test_league_memory_module_is_importable():
    from dodgeball_sim.league_memory import build_league_memory_state
    assert callable(build_league_memory_state)


def test_staff_market_module_is_importable():
    from dodgeball_sim.staff_market import build_staff_market_state
    assert callable(build_staff_market_state)


def test_build_recruiting_state_returns_expected_keys(career_conn):
    from dodgeball_sim.recruiting_office import build_recruiting_state
    from dodgeball_sim.persistence import get_state, load_command_history, load_season

    season_id = get_state(career_conn, "active_season_id")
    player_club_id = get_state(career_conn, "player_club_id")
    season = load_season(career_conn, season_id)
    history = load_command_history(career_conn, season_id)

    result = build_recruiting_state(
        career_conn, season_id=season_id, player_club_id=player_club_id,
        root_seed=20260426, history=history,
    )
    assert "credibility" in result
    assert "prospects" in result
    assert "budget" in result
    assert "active_promises" in result


def test_build_league_memory_state_returns_expected_keys(career_conn):
    from dodgeball_sim.league_memory import build_league_memory_state
    from dodgeball_sim.persistence import get_state, load_clubs

    season_id = get_state(career_conn, "active_season_id")
    clubs = load_clubs(career_conn)

    result = build_league_memory_state(career_conn, season_id=season_id, clubs=clubs)
    assert "records" in result
    assert "awards" in result
    assert "rivalries" in result
    assert "recent_matches" in result


def test_build_staff_market_state_returns_expected_keys(career_conn):
    from dodgeball_sim.staff_market import build_staff_market_state
    from dodgeball_sim.persistence import get_state

    season_id = get_state(career_conn, "active_season_id")
    player_club_id = get_state(career_conn, "player_club_id")

    result = build_staff_market_state(
        career_conn, season_id=season_id,
        player_club_id=player_club_id, root_seed=20260426,
    )
    assert "current_staff" in result
    assert "candidates" in result
    assert "recent_actions" in result
```

(Note: `career_conn` fixture must exist in `tests/conftest.py` or at the top of `test_dynasty_office.py`. Check the existing test file for how it creates an in-memory career connection and reuse that pattern.)

- [ ] **Step 2: Run to confirm failures**

```
python -m pytest tests/test_dynasty_office.py -k "importable or expected_keys" -v
```

Expected: `ImportError` on all four new-module tests.

- [ ] **Step 3: Create recruiting_office.py**

Create `src/dodgeball_sim/recruiting_office.py` by moving these functions verbatim from `dynasty_office.py`:

- `_recruiting_state` → renamed to `build_recruiting_state` (public, same body, updated signature to match callers)
- `_credibility` → `_credibility` (keep private)
- `_prospect_rows` → `_prospect_rows` (keep private)
- `_load_promises` → `build_recruiting_state` calls `load_json_state` directly (inline)
- Constants: `PROMISE_STATE_KEY`, `MAX_ACTIVE_PROMISES`, `PROMISE_OPTIONS`

```python
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .config import DEFAULT_SCOUTING_CONFIG
from .game_loop import current_week
from .persistence import (
    CorruptSaveError,
    get_state,
    load_command_history,
    load_json_state,
    load_prospect_pool,
    load_season,
    set_state,
)
from .recruitment import generate_prospect_pool, get_current_recruiting_budget
from .rng import DeterministicRNG, derive_seed

PROMISE_STATE_KEY = "program_promises_json"
MAX_ACTIVE_PROMISES = 3
PROMISE_OPTIONS = (
    "early_playing_time",
    "development_priority",
    "contender_path",
)


def build_recruiting_state(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    root_seed: int,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    promises = list(load_json_state(conn, PROMISE_STATE_KEY, []))
    credibility = _credibility(conn, season_id, player_club_id, history)
    prospects = _prospect_rows(conn, season_id, root_seed, promises, credibility)
    week_val = 0
    row = conn.execute("SELECT value FROM dynasty_state WHERE key='career_week'").fetchone()
    if row:
        week_val = int(row[0])
    budget = get_current_recruiting_budget(conn, season_id, week_val)
    return {
        "credibility": credibility,
        "active_promises": promises,
        "prospects": prospects,
        "budget": budget,
        "rules": {
            "max_active_promises": MAX_ACTIVE_PROMISES,
            "promise_options": list(PROMISE_OPTIONS),
            "honesty": "Promise checks use command history, player match stats, and future roster usage only.",
        },
    }


def _credibility(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    from .persistence import load_club_prestige
    del season_id
    prestige = load_club_prestige(conn, player_club_id)
    wins = sum(1 for item in history if item.get("dashboard", {}).get("result") == "Win")
    losses = sum(1 for item in history if item.get("dashboard", {}).get("result") == "Loss")
    youth_weeks = sum(
        1 for item in history
        if item.get("plan", {}).get("department_orders", {}).get("dev_focus") == "YOUTH_ACCELERATION"
        or item.get("intent") == "Develop Youth"
    )
    score = max(0, min(100, 50 + prestige * 2 + wins * 4 - losses * 3 + youth_weeks * 2))
    evidence = [
        f"{wins} command-history wins and {losses} losses.",
        f"{youth_weeks} youth-development command weeks.",
        f"Club prestige score {prestige}.",
    ]
    if not history:
        evidence.append("No command history yet, so credibility starts from program baseline.")
    return {"score": score, "grade": _grade(score), "evidence": evidence}


def _prospect_rows(
    conn: sqlite3.Connection,
    season_id: str,
    root_seed: int,
    promises: list[dict[str, Any]],
    credibility: dict[str, Any],
) -> list[dict[str, Any]]:
    class_year = _class_year_from_season(season_id)
    persisted = load_prospect_pool(conn, class_year)
    if persisted:
        prospects = persisted
    else:
        rng = DeterministicRNG(derive_seed(root_seed, "prospect_gen", str(class_year)))
        prospects = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
    promised = {promise["player_id"]: promise for promise in promises}
    rows = []
    for prospect in prospects[:8]:
        low, high = prospect.public_ratings_band["ovr"]
        fit_score = round(((low + high) / 2.0) + credibility["score"] * 0.12, 1)
        rows.append({
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
        })
    return rows


def _grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _class_year_from_season(season_id: str) -> int:
    digits = "".join(ch for ch in season_id if ch.isdigit())
    return int(digits or "1") + 1


__all__ = ["PROMISE_OPTIONS", "PROMISE_STATE_KEY", "MAX_ACTIVE_PROMISES", "build_recruiting_state"]
```

- [ ] **Step 4: Create league_memory.py**

Create `src/dodgeball_sim/league_memory.py` by moving `_league_memory_state` from `dynasty_office.py`:

```python
from __future__ import annotations

import sqlite3
from typing import Any

from .persistence import load_awards, load_league_records, load_rivalry_records


def build_league_memory_state(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    clubs: dict[str, Any],
) -> dict[str, Any]:
    awards = load_awards(conn, season_id)
    record_items = load_league_records(conn)
    rivalry_items = load_rivalry_records(conn)
    recent_matches = conn.execute(
        """
        SELECT match_id, week, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 6
        """,
        (season_id,),
    ).fetchall()
    return {
        "records": {
            "items": [_record_item(item) for item in record_items]
            or [{"status": "limited", "text": "The league record books are currently empty. History begins when the first records are ratified."}],
        },
        "awards": {
            "items": [
                {
                    "award_type": award.award_type,
                    "player_id": award.player_id,
                    "club_name": clubs.get(award.club_id).name if award.club_id in clubs else award.club_id,
                    "score": award.award_score,
                }
                for award in awards
            ]
            or [{"status": "limited", "text": "The trophy cabinet awaits. Season awards will be decided and displayed after the offseason closeout."}],
        },
        "rivalries": {
            "items": [
                {
                    "club_a_name": clubs.get(item["club_a_id"]).name if item["club_a_id"] in clubs else item["club_a_id"],
                    "club_b_name": clubs.get(item["club_b_id"]).name if item["club_b_id"] in clubs else item["club_b_id"],
                    "score": item["rivalry"].get("rivalry_score", 0),
                    "meetings": item["rivalry"].get("total_meetings", 0),
                }
                for item in rivalry_items
            ]
            or [{"status": "limited", "text": "True rivalries require history. Bad blood will build here after repeated, high-stakes match results."}],
        },
        "recent_matches": [_recent_match_item(row, clubs) for row in recent_matches],
    }


def _record_item(item: dict[str, Any]) -> dict[str, Any]:
    record = item.get("record", {})
    return {
        "record_type": item["record_type"],
        "holder_id": item["holder_id"],
        "holder_type": item["holder_type"],
        "value": item["record_value"],
        "season_id": item["set_in_season"],
        "text": record.get("detail") or f"{item['holder_id']} leads {item['record_type']}.",
    }


def _recent_match_item(row: sqlite3.Row, clubs: dict[str, Any]) -> dict[str, Any]:
    home = clubs.get(row["home_club_id"])
    away = clubs.get(row["away_club_id"])
    winner = clubs.get(row["winner_club_id"]) if row["winner_club_id"] else None
    return {
        "match_id": row["match_id"],
        "week": int(row["week"]),
        "summary": (
            f"{home.name if home else row['home_club_id']} {row['home_survivors']}-"
            f"{row['away_survivors']} {away.name if away else row['away_club_id']}"
        ),
        "winner_name": winner.name if winner else "Draw",
    }


__all__ = ["build_league_memory_state"]
```

- [ ] **Step 5: Create staff_market.py**

Create `src/dodgeball_sim/staff_market.py` by moving `_staff_market_state` and its helpers from `dynasty_office.py`:

```python
from __future__ import annotations

import sqlite3
from typing import Any

from .persistence import load_club_facilities, load_department_heads, load_json_state
from .rng import DeterministicRNG, derive_seed

STAFF_ACTION_STATE_KEY = "staff_market_actions_json"


def build_staff_market_state(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    root_seed: int,
) -> dict[str, Any]:
    current_staff = load_department_heads(conn)
    facilities = load_club_facilities(conn, player_club_id, season_id)
    recent_actions = list(load_json_state(conn, STAFF_ACTION_STATE_KEY, []))
    filled_departments = {action.get("department") for action in recent_actions}
    candidates = [
        _candidate_for_head(head, root_seed, season_id)
        for head in current_staff
        if head["department"] not in filled_departments
    ]
    return {
        "current_staff": current_staff,
        "active_facilities": facilities,
        "candidates": candidates,
        "recent_actions": recent_actions,
        "rules": {
            "honesty": "Training staff affects offseason player development now; scouting, recovery, and deeper staff economy effects remain explicit future hooks.",
        },
    }


def _candidate_for_head(head: dict[str, Any], root_seed: int, season_id: str) -> dict[str, Any]:
    department = head["department"]
    rng = DeterministicRNG(derive_seed(root_seed, "staff_market", season_id, department))
    primary_gain = round(rng.roll(3.0, 9.0), 1)
    secondary_gain = round(rng.roll(1.0, 7.0), 1)
    primary = round(min(99.0, float(head["rating_primary"]) + primary_gain), 1)
    secondary = round(min(99.0, float(head["rating_secondary"]) + secondary_gain), 1)
    name = f"{_staff_first_name(rng)} {_staff_last_name(rng)}"
    return {
        "candidate_id": f"{season_id}_{department}_candidate",
        "department": department,
        "name": name,
        "rating_primary": primary,
        "rating_secondary": secondary,
        "voice": _staff_voice(department, rng),
        "effect_lanes": _staff_effect_lanes(department, primary, secondary),
    }


def _staff_effect_lanes(department: str, primary: float, secondary: float) -> list[str]:
    labels = {
        "tactics": "Tactics recommendations and replay-proof preparation.",
        "training": "Development focus advice and offseason player-growth impact.",
        "conditioning": "Fatigue-risk recommendations and recovery planning.",
        "medical": "Availability warnings and overuse-risk reporting.",
        "scouting": "Recruiting fit explanations and prospect board clarity.",
        "culture": "Promise-risk framing and command-plan stability.",
    }
    return [
        labels.get(department, "Program recommendations."),
        f"Visible staff ratings would become {primary:.1f}/{secondary:.1f}.",
    ]


def _staff_first_name(rng: DeterministicRNG) -> str:
    return rng.choice((
        "Ari", "Blair", "Carmen", "Dev", "Eli", "Juno", "Morgan", "Sasha",
        "Taylor", "Jordan", "Casey", "Riley", "Avery", "Quinn", "Peyton", "Skyler",
        "Dallas", "Reese", "Rowan", "Ellis", "Kendall", "Micah", "Emerson", "Finley",
    ))


def _staff_last_name(rng: DeterministicRNG) -> str:
    return rng.choice((
        "Vale", "Cross", "Hart", "Rook", "Sol", "Pike", "Ives", "Chen",
        "Gaines", "Mercer", "Vance", "Sutton", "Hayes", "Frost", "Graves", "Cole",
        "Bridges", "Stark", "Rivers", "Banks", "Shaw", "Kerr", "Brooks", "Glover",
    ))


def _staff_voice(department: str, rng: DeterministicRNG) -> str:
    voices = {
        "tactics": [
            "Make every matchup leave evidence.",
            "Execution beats raw talent when the plan is clear.",
            "We dictate the tempo, they react to the pressure.",
            "A rigid lineup is a vulnerable lineup.",
        ],
        "training": [
            "Growth needs visible reps.",
            "Potential means nothing without court time.",
            "Drills build the floor; match minutes build the ceiling.",
            "We measure progress in successful catches, not promises.",
        ],
        "conditioning": [
            "Late-match legs are earned early.",
            "Fatigue makes cowards of us all.",
            "We win the war of attrition in the practice gym.",
            "Stamina is the shield that protects our strategy.",
        ],
        "medical": [
            "Availability is the quiet edge.",
            "I tell you who can play; you tell them how.",
            "Managing overuse is managing the season's fate.",
            "Don't risk a career for a single regular-season win.",
        ],
        "scouting": [
            "Fit beats noise.",
            "We draft for the liabilities we can hide and the traits we can use.",
            "The tape never lies, even when the public hype does.",
            "I find the ceiling; you build the floor.",
        ],
        "culture": [
            "Promises become program memory.",
            "Trust is built on fulfilled expectations.",
            "A fractured locker room will drop the ball when it matters most.",
            "Recruits watch how we treat our veterans.",
        ],
    }
    options = voices.get(department, ["Build the program with proof."])
    return rng.choice(options)


__all__ = ["STAFF_ACTION_STATE_KEY", "build_staff_market_state"]
```

- [ ] **Step 6: Update dynasty_office.py to delegate to sub-modules**

Replace the body of `dynasty_office.py` with a thin facade. The import list at the top changes, the three private helpers (`_recruiting_state`, `_league_memory_state`, `_staff_market_state`) are removed, and `build_dynasty_office_state` delegates:

```python
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .game_loop import current_week
from .league_memory import build_league_memory_state
from .persistence import (
    CorruptSaveError,
    get_state,
    load_all_rosters,
    load_command_history,
    load_clubs,
    load_json_state,
    load_playoff_bracket,
    load_season,
    set_state,
)
from .recruiting_office import (
    MAX_ACTIVE_PROMISES,
    PROMISE_OPTIONS,
    PROMISE_STATE_KEY,
    build_recruiting_state,
)
from .recruitment import generate_prospect_pool
from .rng import DeterministicRNG, derive_seed
from .scouting_center import Prospect
from .staff_market import STAFF_ACTION_STATE_KEY, build_staff_market_state

# _ensure_dynasty_keys, save_recruiting_promise, hire_staff_candidate,
# evaluate_season_promises remain here — they are mutation functions that
# need access to both the state-building sub-modules and persistence.
```

Keep the mutation functions (`save_recruiting_promise`, `hire_staff_candidate`, `evaluate_season_promises`) in `dynasty_office.py` — they coordinate across modules and make DB writes. Update `build_dynasty_office_state` to call the sub-modules:

```python
def build_dynasty_office_state(conn: sqlite3.Connection) -> dict[str, Any]:
    _ensure_dynasty_keys(conn)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id or not player_club_id:
        raise ValueError("No active season or player club")

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    history = load_command_history(conn, season_id)
    root_seed = _root_seed(conn)
    week = current_week(conn, season) or 0

    return {
        "season_id": season_id,
        "week": week,
        "player_club_id": player_club_id,
        "player_club_name": clubs[player_club_id].name if player_club_id in clubs else player_club_id,
        "recruiting": build_recruiting_state(
            conn,
            season_id=season_id,
            player_club_id=player_club_id,
            root_seed=root_seed,
            history=history,
        ),
        "league_memory": build_league_memory_state(conn, season_id=season_id, clubs=clubs),
        "staff_market": build_staff_market_state(
            conn,
            season_id=season_id,
            player_club_id=player_club_id,
            root_seed=root_seed,
        ),
    }
```

Remove the now-moved private helpers from `dynasty_office.py`. Also remove `_recent_match_item` (moved to `league_memory.py`) — update the import in `server.py` to import from `league_memory` instead of `dynasty_office`.

- [ ] **Step 7: Fix server.py import**

In `server.py`, update:
```python
from dodgeball_sim.dynasty_office import (
    build_dynasty_office_state,
    hire_staff_candidate,
    save_recruiting_promise,
    _recent_match_item,
)
```
To:
```python
from dodgeball_sim.dynasty_office import (
    build_dynasty_office_state,
    hire_staff_candidate,
    save_recruiting_promise,
)
from dodgeball_sim.league_memory import _recent_match_item
```

- [ ] **Step 8: Run tests**

```
python -m pytest tests/test_dynasty_office.py -v
```

Expected: PASS

- [ ] **Step 9: Run full suite**

```
python -m pytest -q
```

Expected: all green

- [ ] **Step 10: Commit**

```
git add src/dodgeball_sim/recruiting_office.py src/dodgeball_sim/league_memory.py src/dodgeball_sim/staff_market.py src/dodgeball_sim/dynasty_office.py src/dodgeball_sim/server.py tests/test_dynasty_office.py
git commit -m "refactor: split dynasty_office.py into recruiting_office, league_memory, staff_market sub-modules"
```

---

## Task 4: Extract matchup_details from command_center.py

**Files:**
- Create: `src/dodgeball_sim/matchup_details.py`
- Modify: `src/dodgeball_sim/command_center.py`
- Test: `tests/test_command_center.py`

`_matchup_details` is a DB-querying function buried inside `command_center.py`. It queries `season_standings` and `match_records` to build context for the pre-match plan. Making it a public module means it can be tested independently, and the matchup context logic has _locality_ separate from the plan-building logic.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_command_center.py`:

```python
def test_build_matchup_details_is_importable():
    from dodgeball_sim.matchup_details import build_matchup_details
    assert callable(build_matchup_details)


def test_build_matchup_details_no_opponent():
    from dodgeball_sim.matchup_details import build_matchup_details
    from dodgeball_sim.persistence import connect, create_schema
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    result = build_matchup_details(
        conn,
        season_id="s1",
        player_club_id="aurora",
        opponent_id=None,
        rosters={},
    )
    assert result["opponent_record"] == "0-0"
    assert result["last_meeting"] == "None"
    assert "Season schedule complete" in result["key_matchup"]
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_command_center.py::test_build_matchup_details_is_importable -v
```

Expected: `ImportError: cannot import name 'build_matchup_details'`

- [ ] **Step 3: Create matchup_details.py**

Create `src/dodgeball_sim/matchup_details.py`:

```python
from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from .models import Player


def build_matchup_details(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    opponent_id: str | None,
    rosters: Mapping[str, list[Player]],
) -> dict[str, str]:
    if not opponent_id:
        return {
            "opponent_record": "0-0",
            "last_meeting": "None",
            "key_matchup": "Season schedule complete.",
        }

    standing = conn.execute(
        """
        SELECT wins, losses, draws
        FROM season_standings
        WHERE season_id = ? AND club_id = ?
        """,
        (season_id, opponent_id),
    ).fetchone()
    if standing is None:
        opponent_record = "0-0"
    else:
        wins = int(standing["wins"])
        losses = int(standing["losses"])
        draws = int(standing["draws"])
        opponent_record = f"{wins}-{losses}" if draws == 0 else f"{wins}-{losses}-{draws}"

    meeting = conn.execute(
        """
        SELECT week, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
          AND (
            (home_club_id = ? AND away_club_id = ?)
            OR (home_club_id = ? AND away_club_id = ?)
          )
        ORDER BY week DESC, match_id DESC
        LIMIT 1
        """,
        (season_id, player_club_id, opponent_id, opponent_id, player_club_id),
    ).fetchone()
    if meeting is None:
        last_meeting = "None"
    else:
        result = "Draw"
        if meeting["winner_club_id"] == player_club_id:
            result = "Win"
        elif meeting["winner_club_id"] == opponent_id:
            result = "Loss"
        last_meeting = f"Week {int(meeting['week'])}: {result} {int(meeting['home_survivors'])}-{int(meeting['away_survivors'])}"

    opponent_roster = list(rosters.get(opponent_id, []))
    if opponent_roster:
        focal_player = max(opponent_roster, key=lambda p: (p.overall(), p.id))
        key_matchup = f"{focal_player.name}, {focal_player.archetype.value}, {round(focal_player.overall())} OVR"
    else:
        key_matchup = "Opponent roster unavailable."

    return {
        "opponent_record": opponent_record,
        "last_meeting": last_meeting,
        "key_matchup": key_matchup,
    }


__all__ = ["build_matchup_details"]
```

- [ ] **Step 4: Update command_center.py to use the new module**

In `src/dodgeball_sim/command_center.py`, add the import at the top:

```python
from .matchup_details import build_matchup_details
```

Replace the `_matchup_details` function body with a thin wrapper that calls `build_matchup_details` (or just update the call site in `build_command_center_state` directly). The simplest approach: remove `_matchup_details` from `command_center.py` and update the one call site:

```python
# In build_command_center_state, replace:
"matchup_details": _matchup_details(conn, season_id, player_club_id, opponent_id, rosters),
# With:
"matchup_details": build_matchup_details(
    conn,
    season_id=season_id,
    player_club_id=player_club_id,
    opponent_id=opponent_id,
    rosters=rosters,
),
```

- [ ] **Step 5: Run tests**

```
python -m pytest tests/test_command_center.py -v
```

Expected: PASS

- [ ] **Step 6: Run full suite**

```
python -m pytest -q
```

Expected: all green

- [ ] **Step 7: Commit**

```
git add src/dodgeball_sim/matchup_details.py src/dodgeball_sim/command_center.py tests/test_command_center.py
git commit -m "refactor: extract matchup_details from command_center into its own module"
```

---

## Task 5: Type offseason beat payloads end-to-end

**Files:**
- Modify: `frontend/src/types.ts`
- Test: `tests/test_ceremony_payload.py` (verify backend beat shapes)

The Python side of `offseason_beats.py` already uses typed dataclasses (`RatificationPayload`, `InductionPayload`, `RookiePreviewPayload`). The gap is on the TypeScript side: `OffseasonBeat` uses a loose `payload?: OffseasonBeatPayload` that doesn't distinguish between beat types. This task introduces a discriminated union in TypeScript so that each beat's payload has a compile-checked shape.

- [ ] **Step 1: Write a backend payload shape test**

Add to `tests/test_ceremony_payload.py` (or create it if it doesn't exist — check first):

```python
def test_records_ratified_beat_payload_has_new_records_key(career_conn_at_offseason):
    """RatificationPayload serialization must include new_records."""
    from dodgeball_sim.offseason_beats import ratify_records
    from dodgeball_sim.persistence import get_state

    season_id = get_state(career_conn_at_offseason, "active_season_id")
    payload = ratify_records(career_conn_at_offseason, season_id)
    # Verify the payload is serializable to the shape TypeScript expects
    import dataclasses
    d = dataclasses.asdict(payload)
    assert "new_records" in d
    assert isinstance(d["new_records"], list)


def test_hof_induction_beat_payload_has_new_inductees_key(career_conn_at_offseason):
    from dodgeball_sim.offseason_beats import induct_hall_of_fame
    from dodgeball_sim.persistence import get_state

    season_id = get_state(career_conn_at_offseason, "active_season_id")
    payload = induct_hall_of_fame(career_conn_at_offseason, season_id)
    import dataclasses
    d = dataclasses.asdict(payload)
    assert "new_inductees" in d
    assert isinstance(d["new_inductees"], list)


def test_rookie_preview_beat_payload_has_expected_keys(career_conn_at_offseason):
    from dodgeball_sim.offseason_beats import build_rookie_class_preview
    from dodgeball_sim.persistence import get_state

    season_id = get_state(career_conn_at_offseason, "active_season_id")
    payload = build_rookie_class_preview(career_conn_at_offseason, season_id, class_year=2)
    import dataclasses
    d = dataclasses.asdict(payload)
    for key in ("class_year", "class_size", "archetype_distribution", "top_band_depth", "storylines"):
        assert key in d, f"Missing key: {key}"
```

(Note: `career_conn_at_offseason` is a fixture that creates a career connection at the point where offseason beats are available. Check `tests/test_offseason_beats.py` for the existing fixture pattern and reuse it.)

- [ ] **Step 2: Run to confirm the backend tests pass (they should already)**

```
python -m pytest tests/test_ceremony_payload.py -v
```

Expected: PASS (Python side is already typed; this confirms the shape)

- [ ] **Step 3: Update frontend/src/types.ts with per-beat payload interfaces**

Find the existing `OffseasonBeatPayload` and `OffseasonBeat` interfaces and replace them:

```typescript
// --- Per-beat payload interfaces ---

export interface ChampionBeatPayload {
    champion_club_id: string;
    champion_club_name: string;
    season_label?: string;
}

export interface RecapBeatPayload {
    standings?: StandingItem[];
    season_label?: string;
}

export interface AwardsBeatPayload {
    awards: OffseasonAward[];
    season_label?: string;
}

export interface RecordsRatifiedBeatPayload {
    new_records: Array<{
        record_type: string;
        holder_name: string;
        previous_value: number;
        new_value: number;
        detail: string;
    }>;
    season_id: string;
}

export interface HofInductionBeatPayload {
    new_inductees: Array<{
        player_id: string;
        player_name: string;
        legacy_score: number;
        threshold: number;
        reasons: string[];
        seasons_played: number;
        championships: number;
        awards_won: number;
        total_eliminations: number;
    }>;
    season_id: string;
}

export interface DevelopmentBeatPayload {
    rows: Array<{ player_id: string; player_name: string; delta: number }>;
    season_label?: string;
}

export interface RetirementsBeatPayload {
    retirees: OffseasonRetiree[];
    season_label?: string;
}

export interface RookiePreviewBeatPayload {
    class_year: number;
    class_size: number;
    source: string;
    archetype_distribution: Record<string, number>;
    top_band_depth: number;
    free_agent_count: number;
    storylines: Array<{ template_id: string; sentence: string; fact: Record<string, unknown> }>;
}

export interface RecruitmentBeatPayload {
    player_signing: OffseasonSigning | null;
    season_label?: string;
}

export interface ScheduleRevealBeatPayload {
    season_label?: string;
    schedule?: unknown[];
}

// Discriminated union — key is the discriminant
export type OffseasonBeat =
    | { beat_index: number; total_beats: number; key: 'champion'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: ChampionBeatPayload }
    | { beat_index: number; total_beats: number; key: 'recap'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: RecapBeatPayload }
    | { beat_index: number; total_beats: number; key: 'awards'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: AwardsBeatPayload }
    | { beat_index: number; total_beats: number; key: 'records_ratified'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: RecordsRatifiedBeatPayload }
    | { beat_index: number; total_beats: number; key: 'hof_induction'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: HofInductionBeatPayload }
    | { beat_index: number; total_beats: number; key: 'development'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: DevelopmentBeatPayload }
    | { beat_index: number; total_beats: number; key: 'retirements'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: RetirementsBeatPayload }
    | { beat_index: number; total_beats: number; key: 'rookie_class_preview'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: RookiePreviewBeatPayload }
    | { beat_index: number; total_beats: number; key: 'recruitment'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: RecruitmentBeatPayload }
    | { beat_index: number; total_beats: number; key: 'schedule_reveal'; can_begin_season: boolean; signed_player_id: string; signed_player?: { id: string; name: string; overall: number; age: number } | null; payload: ScheduleRevealBeatPayload };
```

- [ ] **Step 4: Fix any TypeScript errors in Offseason.tsx**

Run the build; if `Offseason.tsx` does a `beat.payload.awards` or similar field access, it will now need a type guard. For example:

```typescript
// Before (unsafe):
const awards = beat.payload?.awards;

// After (type-safe):
if (beat.key === 'awards') {
    const awards = beat.payload.awards; // TypeScript knows this is AwardsBeatPayload
}
```

Check each field access in `frontend/src/components/Offseason.tsx` and wrap with the appropriate `beat.key === '...'` guard.

- [ ] **Step 5: Build frontend**

From `frontend/`:
```
npm run build
```

Expected: 0 TypeScript errors

- [ ] **Step 6: Run full suite**

```
python -m pytest -q
```

Expected: all green

- [ ] **Step 7: Commit**

```
git add frontend/src/types.ts frontend/src/components/Offseason.tsx tests/test_ceremony_payload.py
git commit -m "refactor: type OffseasonBeat as discriminated union per beat key"
```

---

## Task 6: Extract simulate-week use-case from server.py

**Files:**
- Create: `src/dodgeball_sim/use_cases.py`
- Modify: `src/dodgeball_sim/server.py`
- Test: `tests/test_use_cases.py`

`simulate_command_center_week` in `server.py` is 130+ lines of orchestration inside a FastAPI endpoint. It cannot be tested without FastAPI's test client and a full HTTP round-trip. Extracting this to a use-case function gives a testable seam: the function takes a `conn` and an update dict, does the work, and returns the response dict. The endpoint becomes a 3-line adapter.

- [ ] **Step 1: Write the failing test**

Create `tests/test_use_cases.py`:

```python
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import connect, create_schema


def _career_conn(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_simulate_week_use_case_is_importable():
    from dodgeball_sim.use_cases import simulate_week
    assert callable(simulate_week)


def test_simulate_week_returns_expected_keys(tmp_path):
    from dodgeball_sim.use_cases import simulate_week

    conn = _career_conn(tmp_path)
    result = simulate_week(conn, update=None)

    assert "status" in result
    assert result["status"] == "success"
    assert "plan" in result
    assert "dashboard" in result
    assert "aftermath" in result
    assert "next_state" in result


def test_simulate_week_with_intent_override(tmp_path):
    from dodgeball_sim.use_cases import simulate_week

    conn = _career_conn(tmp_path)
    result = simulate_week(conn, update={"intent": "Develop Youth"})

    assert result["status"] == "success"
    assert result["plan"]["intent"] == "Develop Youth"
```

- [ ] **Step 2: Run to confirm failures**

```
python -m pytest tests/test_use_cases.py -v
```

Expected: `ImportError: cannot import name 'simulate_week'`

- [ ] **Step 3: Create use_cases.py**

Create `src/dodgeball_sim/use_cases.py` with the logic extracted from `simulate_command_center_week`. The function signature accepts a sqlite3 connection and an optional update dict (not a Pydantic model, since use-cases should not depend on FastAPI):

```python
from __future__ import annotations

import dataclasses
import sqlite3
from typing import Any, Mapping

from .career_state import CareerState, advance
from .command_center import (
    build_command_center_state,
    build_default_weekly_plan,
    build_post_week_dashboard,
    refresh_weekly_plan_context,
)
from .game_loop import (
    current_week,
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from .offseason_ceremony import ensure_ai_rosters_playable
from .persistence import (
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_completed_match_ids,
    load_season,
    load_weekly_command_plan,
    save_career_state_cursor,
    save_command_history_record,
    save_weekly_command_plan,
)
from .rng import DeterministicRNG, derive_seed
from .view_models import normalize_root_seed
from .voice_aftermath import render_headline


class SimulateWeekError(ValueError):
    """Raised when simulate_week cannot proceed due to invalid state."""


def simulate_week(
    conn: sqlite3.Connection,
    *,
    update: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Run one command-center week simulation.

    Raises SimulateWeekError if the career state is wrong.
    Returns the response dict matching CommandCenterSimResponse.
    """
    player_club_id = get_state(conn, "player_club_id")
    season_id = get_state(conn, "active_season_id")
    if not player_club_id or not season_id:
        raise SimulateWeekError("No active season or club")

    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH:
        raise SimulateWeekError(
            f"simulate_week requires season_active_pre_match; got {cursor.state.value}"
        )

    state = build_command_center_state(conn)
    intent = (update or {}).get("intent") or "Win Now"
    existing = load_weekly_command_plan(conn, state["season_id"], state["week"], state["player_club_id"])
    plan = existing or build_default_weekly_plan(state, intent=intent)
    plan = refresh_weekly_plan_context(plan, state)

    if update is not None:
        if update.get("intent") and update["intent"] != plan.get("intent"):
            plan = build_default_weekly_plan(state, intent=update["intent"])
        if update.get("department_orders"):
            plan["department_orders"] = {**plan["department_orders"], **update["department_orders"]}
        if update.get("tactics"):
            plan["tactics"] = {
                **plan["tactics"],
                **{
                    k: max(0.0, min(1.0, float(v)))
                    for k, v in update["tactics"].items()
                    if k in plan["tactics"]
                },
            }
        if update.get("lineup_player_ids"):
            plan["lineup"]["player_ids"] = update["lineup_player_ids"]
    save_weekly_command_plan(conn, plan)

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)

    from .server import _choose_next_user_match_after_automation, _apply_command_plan_to_match, _validate_match_rosters
    season, chosen, stop_reason = _choose_next_user_match_after_automation(conn, season, clubs, player_club_id)

    if not chosen:
        if stop_reason == "season_complete":
            cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
            save_career_state_cursor(conn, cursor)
            conn.commit()
            return {
                "status": "success",
                "message": "Season complete. Offseason review is ready.",
                "plan": plan,
                "dashboard": state.get("latest_dashboard") or {
                    "season_id": season_id,
                    "week": state["week"],
                    "match_id": None,
                    "opponent_name": "Season complete",
                    "result": "Season Complete",
                    "lanes": [],
                },
                "next_state": cursor.state.value,
                "aftermath": {
                    "headline": "Season Complete",
                    "match_card": None,
                    "player_growth_deltas": [],
                    "standings_shift": [],
                    "recruit_reactions": [],
                },
            }
        raise SimulateWeekError(f"No user match available: {stop_reason}")

    scheduled = chosen[0]
    completed = load_completed_match_ids(conn, season_id)
    week_matches = [
        match
        for match in sorted(season.matches_for_week(scheduled.week), key=lambda m: m.match_id)
        if match.match_id not in completed
    ]
    _apply_command_plan_to_match(conn, plan, scheduled.match_id, player_club_id)
    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    _validate_match_rosters(week_matches, rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"
    records = [
        simulate_scheduled_match(
            conn,
            scheduled=wm,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )
        for wm in week_matches
    ]
    record = next(r for r in records if r.match_id == scheduled.match_id)
    recompute_regular_season_standings(conn, season)
    dashboard = build_post_week_dashboard(conn, plan, record)
    save_command_history_record(conn, {
        "season_id": season_id,
        "week": record.week,
        "match_id": record.match_id,
        "opponent_club_id": record.away_club_id if record.home_club_id == player_club_id else record.home_club_id,
        "intent": plan["intent"],
        "plan": plan,
        "dashboard": dashboard,
    })
    season = load_season(conn, season.season_id)
    season, next_chosen, _ = _choose_next_user_match_after_automation(conn, season, clubs, player_club_id)
    if next_chosen:
        cursor = dataclasses.replace(
            cursor,
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            week=next_chosen[0].week,
            match_id=None,
        )
    else:
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    save_career_state_cursor(conn, cursor)
    conn.commit()

    root_seed_val = get_state(conn, "root_seed") or "1"
    rng = DeterministicRNG(derive_seed(int(root_seed_val), "headline", season_id, str(record.week)))
    headline = render_headline(dashboard["result"], "expected", rng)
    box = record.result.box_score["teams"]
    home_survivors = int(box[record.home_club_id]["totals"]["living"])
    away_survivors = int(box[record.away_club_id]["totals"]["living"])

    return {
        "status": "success",
        "message": f"Simulated Week {record.week} command plan.",
        "plan": plan,
        "dashboard": dashboard,
        "next_state": cursor.state.value,
        "aftermath": _build_aftermath(record, dashboard, clubs, player_club_id, headline, home_survivors, away_survivors),
    }


def _build_aftermath(record, dashboard, clubs, player_club_id, headline, home_survivors, away_survivors) -> dict[str, Any]:
    opponent_id = record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
    return {
        "headline": headline,
        "match_card": {
            "home_club_id": record.home_club_id,
            "home_club_name": clubs.get(record.home_club_id, object()).name if record.home_club_id in clubs else record.home_club_id,
            "away_club_id": record.away_club_id,
            "away_club_name": clubs.get(record.away_club_id, object()).name if record.away_club_id in clubs else record.away_club_id,
            "home_survivors": home_survivors,
            "away_survivors": away_survivors,
            "winner_club_id": record.result.winner_team_id,
            "result": dashboard["result"],
        },
        "player_growth_deltas": [],
        "standings_shift": [],
        "recruit_reactions": [],
    }


__all__ = ["SimulateWeekError", "simulate_week"]
```

**Note on circular import:** `use_cases.py` temporarily imports `_choose_next_user_match_after_automation`, `_apply_command_plan_to_match`, and `_validate_match_rosters` from `server.py`. This is a stopgap — in a follow-up, those helpers should move to a `match_orchestration.py` module. If the circular import causes an error at load time, move those three helpers to a `match_orchestration.py` file and import from there instead.

- [ ] **Step 4: Update the server.py endpoint to delegate**

In `server.py`, replace the body of `simulate_command_center_week`:

```python
from dodgeball_sim.use_cases import SimulateWeekError, simulate_week

@app.post("/api/command-center/simulate", response_model=CommandCenterSimResponse)
def simulate_command_center_week(
    update: WeeklyCommandPlanUpdate | None = None,
    conn = Depends(get_db),
) -> CommandCenterSimResponse:
    try:
        return simulate_week(
            conn,
            update=update.model_dump(exclude_none=True) if update else None,
        )
    except SimulateWeekError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
```

- [ ] **Step 5: Run the use-case tests**

```
python -m pytest tests/test_use_cases.py -v
```

Expected: PASS

- [ ] **Step 6: Run the full suite**

```
python -m pytest -q
```

Expected: all green

- [ ] **Step 7: Build frontend (no changes expected, but verify)**

```
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 8: Commit**

```
git add src/dodgeball_sim/use_cases.py src/dodgeball_sim/server.py tests/test_use_cases.py
git commit -m "refactor: extract simulate_week use-case from server.py endpoint"
```

---

## Self-Review

### Spec coverage

| Candidate | Task | Covered? |
|---|---|---|
| #5 Scouting carry-forward | Task 1 | ✓ |
| #4 Typed MatchEvent context | Task 2 | ✓ |
| #3 dynasty_office split | Task 3 | ✓ |
| #6 command_center matchup extraction | Task 4 | ✓ |
| #2 Typed beat payloads | Task 5 | ✓ |
| #1 Use-case layer | Task 6 | ✓ (simulate_week; pattern established) |

### Notes

- **Task 6 circular import risk:** `use_cases.py` imports helpers from `server.py`. If this causes a circular import at module load time (FastAPI imports `use_cases.py` which imports `server.py`), move `_choose_next_user_match_after_automation`, `_apply_command_plan_to_match`, and `_validate_match_rosters` to a new `match_orchestration.py` module before running the tests.
- **Task 5 TypeScript guards:** The number of type guards needed in `Offseason.tsx` depends on how many places `beat.payload` is accessed without a `key` check. Expect 3–6 guard additions.
- **Task 3 `_recent_match_item` export:** `server.py` currently imports `_recent_match_item` from `dynasty_office`. After the split it lives in `league_memory.py`. The function is private by convention but server.py uses it — make it public (`recent_match_item`) in `league_memory.py` and update the import.
