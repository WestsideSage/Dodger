# V2-E Off-season Beats Completion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Records Ratified, Hall of Fame Induction, and Rookie Class Preview beats to complete the 10-beat off-season ceremony in Manager Mode.

**Architecture:** A new pure-computation module `src/dodgeball_sim/offseason_beats.py` houses three idempotent functions (`ratify_records`, `induct_hall_of_fame`, `build_rookie_class_preview`). They read/write existing tables (`league_records`, `hall_of_fame`, `prospect_pool`, `free_agents`, `club_recruitment_profile`) plus six new `dynasty_state` keys for season-keyed payload caching. `manager_gui.py` is updated to insert three new beats in the existing tuple, run the computations once at off-season entry inside `initialize_manager_offseason`, and render the persisted payloads in `build_offseason_ceremony_beat`.

**Tech Stack:** Python 3.10+, SQLite, Tkinter, pytest. No new dependencies.

---

## Working Constraints

- **Project is not a git repo.** No commits. "Save and verify" replaces commit steps.
- **No new schema migration required.** All needed tables already exist (created in v4 / v9 / v10). New persistence is via `dynasty_state` KV (`get_state` / `set_state`).
- **274 tests must remain green.** Existing 7-beat order tests in `tests/test_manager_gui.py` (lines ~855 and ~1200) need updating in this plan.

## Beat Order (10-beat ceremony)

Old (7): `champion, recap, awards, development, retirements, draft, schedule_reveal`

New (10):
```
champion, recap, awards, records_ratified, hof_induction,
development, retirements, rookie_class_preview, draft, schedule_reveal
```

---

## File Structure

**Created:**
- `src/dodgeball_sim/offseason_beats.py` — pure-computation module (dataclasses + 3 idempotent functions)
- `tests/test_offseason_beats.py` — unit tests for the three computation functions

**Modified:**
- `src/dodgeball_sim/manager_gui.py` — beat tuple expansion, renderer extensions, wiring inside `initialize_manager_offseason`
- `tests/test_manager_gui.py` — update 7-beat order assertion to 10-beat; add new render tests; add resume-at-each-beat integration test

**Untouched (read-only consumers):**
- `src/dodgeball_sim/records.py` — used as-is for `CareerStats`, `LeagueRecord`, `RecordBroken`, `check_records_broken`
- `src/dodgeball_sim/career.py` — used as-is for `CareerSummary`, `evaluate_hall_of_fame`
- `src/dodgeball_sim/persistence.py` — used as-is (no new tables, no new functions; `get_state`/`set_state` cover the new payload keys)

---

## Persisted `dynasty_state` Keys (added by this plan)

| Key | Type | Owner |
|-----|------|-------|
| `offseason_records_ratified_for` | season_id string | `ratify_records` |
| `offseason_records_ratified_json` | JSON list of new-record entries | `ratify_records` |
| `offseason_hof_inducted_for` | season_id string | `induct_hall_of_fame` |
| `offseason_hof_inducted_json` | JSON list of inductee entries | `induct_hall_of_fame` |
| `offseason_rookie_preview_for` | season_id string | `build_rookie_class_preview` |
| `offseason_rookie_preview_json` | JSON payload (class summary + storylines) | `build_rookie_class_preview` |
| `rookie_class_summary_<class_year>` | JSON `{class_size, top_band_depth, free_agent_count}` | `build_rookie_class_preview` (history for future comparisons) |

---

## Task 1: Beat Order Expansion (Stub Renderers)

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py:190-198` (tuple), `src/dodgeball_sim/manager_gui.py:1031-1190` (renderer)
- Modify: `tests/test_manager_gui.py:855-863` (existing order assertion)

Stubs first so the build stays green. Real payloads land in Tasks 5–7.

- [ ] **Step 1.1: Update existing beat-order test to expect the new 10-beat order**

In `tests/test_manager_gui.py`, find the assertion block around line 855:

```python
    assert OFFSEASON_CEREMONY_BEATS == (
        "champion",
        "recap",
        "awards",
        "development",
        "retirements",
        "draft",
        "schedule_reveal",
    )
```

Replace with:

```python
    assert OFFSEASON_CEREMONY_BEATS == (
        "champion",
        "recap",
        "awards",
        "records_ratified",
        "hof_induction",
        "development",
        "retirements",
        "rookie_class_preview",
        "draft",
        "schedule_reveal",
    )
```

- [ ] **Step 1.2: Run the test to confirm it fails**

Run: `python -m pytest tests/test_manager_gui.py -k "OFFSEASON_CEREMONY_BEATS" -v -p no:cacheprovider`

(That `-k` filter may not match by exact name — use `-k "ten_beat_order or offseason_ceremony_renders"` or just run the whole file. The test that contains the order assertion is the one that previously checked seven beats.)

Expected: FAIL with assertion mismatch (7-tuple vs 10-tuple).

- [ ] **Step 1.3: Update the `OFFSEASON_CEREMONY_BEATS` tuple in `manager_gui.py`**

Find:
```python
OFFSEASON_CEREMONY_BEATS = (
    "champion",
    "recap",
    "awards",
    "development",
    "retirements",
    "draft",
    "schedule_reveal",
)
```

Replace with:
```python
OFFSEASON_CEREMONY_BEATS = (
    "champion",
    "recap",
    "awards",
    "records_ratified",
    "hof_induction",
    "development",
    "retirements",
    "rookie_class_preview",
    "draft",
    "schedule_reveal",
)
```

- [ ] **Step 1.4: Add stub branches to `build_offseason_ceremony_beat`**

In `manager_gui.py`, immediately after the existing `awards` branch (the one that returns `OffseasonCeremonyBeat(key, "Awards", body)` near line 1122), insert two new branches:

```python
    if key == "records_ratified":
        body = "Records Ratified payload not yet computed."
        return OffseasonCeremonyBeat(key, "Records Ratified", body)

    if key == "hof_induction":
        body = "Hall of Fame Induction payload not yet computed."
        return OffseasonCeremonyBeat(key, "Hall of Fame Induction", body)
```

Then, immediately after the existing `retirements` branch (the one that returns `OffseasonCeremonyBeat(key, "Retirements", "\n".join(lines))` near line 1148), insert:

```python
    if key == "rookie_class_preview":
        body = "Rookie Class Preview payload not yet computed."
        return OffseasonCeremonyBeat(key, "Rookie Class Preview", body)
```

- [ ] **Step 1.5: Run the full suite — confirm green**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 274+ passed (the existing test now passes against the 10-tuple; nothing else broke because the new beat keys all hit their stub branches and return valid `OffseasonCeremonyBeat` records).

- [ ] **Step 1.6: Save**

(No git. Just verify the suite is still green and move on.)

---

## Task 2: Module Scaffolding for `offseason_beats.py`

**Files:**
- Create: `src/dodgeball_sim/offseason_beats.py`
- Create: `tests/test_offseason_beats.py`

The dataclasses are stable contracts the wiring will use. Define them up front; functions arrive in Tasks 3–5.

- [ ] **Step 2.1: Create the module with dataclasses and stub function signatures**

Create `src/dodgeball_sim/offseason_beats.py`:

```python
"""V2-E: pure-computation off-season ceremony beats.

Each function here is idempotent per `(conn, season_id)`. First call computes
and persists; subsequent calls read the persisted payload from `dynasty_state`
and return it unchanged. None of these functions mutate prospect pools,
recruitment state, or scouting state.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class RatifiedRecord:
    record_type: str
    holder_id: str
    holder_type: str
    holder_name: str
    previous_value: float
    new_value: float
    set_in_season: str
    detail: str


@dataclass(frozen=True)
class RatificationPayload:
    season_id: str
    new_records: Tuple[RatifiedRecord, ...]


@dataclass(frozen=True)
class HallOfFameInductee:
    player_id: str
    player_name: str
    induction_season: str
    legacy_score: float
    threshold: float
    reasons: Tuple[str, ...]
    seasons_played: int
    championships: int
    awards_won: int
    total_eliminations: int


@dataclass(frozen=True)
class InductionPayload:
    season_id: str
    new_inductees: Tuple[HallOfFameInductee, ...]


@dataclass(frozen=True)
class RookieStoryline:
    template_id: str       # one of: "archetype_demand", "top_band_depth", "ai_cluster", "free_agent_crop"
    sentence: str
    fact: Mapping[str, Any]  # source numeric fact backing the sentence


@dataclass(frozen=True)
class RookiePreviewPayload:
    season_id: str
    class_year: int
    source: str            # "prospect_pool" or "legacy_free_agents"
    class_size: int
    archetype_distribution: Mapping[str, int]
    top_band_depth: int
    free_agent_count: int
    storylines: Tuple[RookieStoryline, ...]


def ratify_records(
    conn: sqlite3.Connection,
    season_id: str,
) -> RatificationPayload:
    """Compute or load the Records Ratified beat payload. Idempotent per season_id."""
    raise NotImplementedError("Implemented in Task 3.")


def induct_hall_of_fame(
    conn: sqlite3.Connection,
    season_id: str,
) -> InductionPayload:
    """Compute or load the Hall of Fame Induction beat payload. Idempotent per season_id."""
    raise NotImplementedError("Implemented in Task 4.")


def build_rookie_class_preview(
    conn: sqlite3.Connection,
    season_id: str,
    class_year: int,
) -> RookiePreviewPayload:
    """Compute or load the Rookie Class Preview beat payload. Idempotent per season_id.

    Reads the V2-A prospect pool when present, falls back to V1 free agents otherwise.
    Never mutates either source.
    """
    raise NotImplementedError("Implemented in Task 5.")


__all__ = [
    "HallOfFameInductee",
    "InductionPayload",
    "RatifiedRecord",
    "RatificationPayload",
    "RookiePreviewPayload",
    "RookieStoryline",
    "build_rookie_class_preview",
    "induct_hall_of_fame",
    "ratify_records",
]
```

- [ ] **Step 2.2: Create a smoke test that imports the module**

Create `tests/test_offseason_beats.py`:

```python
import pytest

from dodgeball_sim.offseason_beats import (
    HallOfFameInductee,
    InductionPayload,
    RatificationPayload,
    RatifiedRecord,
    RookiePreviewPayload,
    RookieStoryline,
    build_rookie_class_preview,
    induct_hall_of_fame,
    ratify_records,
)


def test_module_exposes_expected_dataclasses_and_functions():
    assert RatifiedRecord is not None
    assert RatificationPayload is not None
    assert HallOfFameInductee is not None
    assert InductionPayload is not None
    assert RookieStoryline is not None
    assert RookiePreviewPayload is not None
    assert callable(ratify_records)
    assert callable(induct_hall_of_fame)
    assert callable(build_rookie_class_preview)


def test_dataclass_payload_constructors_accept_minimal_inputs():
    rp = RatificationPayload(season_id="season_1", new_records=())
    assert rp.season_id == "season_1"
    assert rp.new_records == ()

    ip = InductionPayload(season_id="season_1", new_inductees=())
    assert ip.season_id == "season_1"
    assert ip.new_inductees == ()

    pp = RookiePreviewPayload(
        season_id="season_1",
        class_year=2,
        source="prospect_pool",
        class_size=0,
        archetype_distribution={},
        top_band_depth=0,
        free_agent_count=0,
        storylines=(),
    )
    assert pp.class_year == 2
```

- [ ] **Step 2.3: Run the smoke test**

Run: `python -m pytest tests/test_offseason_beats.py -v -p no:cacheprovider`

Expected: 2 passed.

- [ ] **Step 2.4: Run the full suite**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 276+ passed (274 prior + 2 new).

---

## Task 3: Implement `ratify_records`

**Files:**
- Modify: `src/dodgeball_sim/offseason_beats.py` (replace the `ratify_records` stub)
- Modify: `tests/test_offseason_beats.py` (add tests)

Reads career stats from `player_career_stats`, builds candidate records via `records.build_individual_records` and `records.build_team_records`, compares against persisted `league_records`, persists new ones once. Spec §2 same-season rule: ratification computed exactly once per season; values are end-of-season.

- [ ] **Step 3.1: Write the failing tests**

Append to `tests/test_offseason_beats.py`:

```python
import json
import sqlite3

from dodgeball_sim.offseason_beats import ratify_records
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    save_league_record,
    save_player_career_stats,
)


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _seed_career(conn: sqlite3.Connection, player_id: str, name: str, eliminations: int, championships: int = 0):
    save_player_career_stats(
        conn,
        player_id,
        {
            "player_id": player_id,
            "player_name": name,
            "seasons_played": 5,
            "championships": championships,
            "awards_won": 0,
            "total_matches": 50,
            "total_eliminations": eliminations,
            "total_catches_made": 0,
            "total_dodges_successful": 0,
            "total_times_eliminated": 0,
            "peak_eliminations": eliminations,
            "career_eliminations": eliminations,
            "career_catches": 0,
            "career_dodges": 0,
            "clubs_served": 1,
        },
    )


def test_ratify_records_persists_new_record_once_when_no_prior_records():
    conn = _fresh_conn()
    _seed_career(conn, "p1", "Alpha", eliminations=80)
    _seed_career(conn, "p2", "Bravo", eliminations=40)

    payload = ratify_records(conn, "season_1")

    types = {record.record_type for record in payload.new_records}
    assert "career_eliminations" in types
    assert get_state(conn, "offseason_records_ratified_for") == "season_1"

    # Second call returns the same payload, doesn't re-ratify
    payload_again = ratify_records(conn, "season_1")
    assert payload_again.new_records == payload.new_records


def test_ratify_records_skips_records_that_did_not_improve():
    conn = _fresh_conn()
    _seed_career(conn, "p1", "Alpha", eliminations=80)
    save_league_record(
        conn,
        record_type="career_eliminations",
        holder_id="legacy",
        holder_type="player",
        record_value=100.0,
        set_in_season="season_0",
        record_payload={"holder_name": "Legacy", "value": 100.0, "detail": "previous"},
    )

    payload = ratify_records(conn, "season_1")

    types = {record.record_type for record in payload.new_records}
    assert "career_eliminations" not in types


def test_ratify_records_empty_payload_when_no_career_data():
    conn = _fresh_conn()

    payload = ratify_records(conn, "season_1")

    assert payload.season_id == "season_1"
    assert payload.new_records == ()
    assert get_state(conn, "offseason_records_ratified_for") == "season_1"


def test_ratify_records_payload_round_trips_through_dynasty_state():
    conn = _fresh_conn()
    _seed_career(conn, "p1", "Alpha", eliminations=80)
    ratify_records(conn, "season_1")

    raw = get_state(conn, "offseason_records_ratified_json")
    assert raw is not None
    parsed = json.loads(raw)
    assert isinstance(parsed, list)
    assert any(entry["record_type"] == "career_eliminations" for entry in parsed)
```

- [ ] **Step 3.2: Run the tests — verify they fail**

Run: `python -m pytest tests/test_offseason_beats.py -v -p no:cacheprovider`

Expected: 4 new tests FAIL with `NotImplementedError("Implemented in Task 3.")`.

- [ ] **Step 3.3: Implement `ratify_records`**

In `src/dodgeball_sim/offseason_beats.py`, replace the `ratify_records` stub with:

```python
def ratify_records(
    conn: sqlite3.Connection,
    season_id: str,
) -> RatificationPayload:
    """Compute or load the Records Ratified beat payload. Idempotent per season_id."""
    from .persistence import (
        get_state,
        load_league_records,
        save_league_record,
        set_state,
    )
    from .records import (
        CareerStats,
        LeagueRecord,
        build_individual_records,
    )

    cached_for = get_state(conn, "offseason_records_ratified_for")
    if cached_for == season_id:
        raw = get_state(conn, "offseason_records_ratified_json", "[]") or "[]"
        records = tuple(_record_from_dict(entry) for entry in json.loads(raw))
        return RatificationPayload(season_id=season_id, new_records=records)

    career_rows = conn.execute(
        """
        SELECT player_id, career_summary_json, career_eliminations, career_catches,
               career_dodges, championships
        FROM player_career_stats
        ORDER BY player_id
        """
    ).fetchall()
    career_stats: List[CareerStats] = []
    for row in career_rows:
        summary: Dict[str, Any] = json.loads(row["career_summary_json"]) if row["career_summary_json"] else {}
        career_stats.append(
            CareerStats(
                player_id=row["player_id"],
                player_name=str(summary.get("player_name") or row["player_id"]),
                career_eliminations=int(row["career_eliminations"] or 0),
                career_catches=int(row["career_catches"] or 0),
                career_dodges=int(row["career_dodges"] or 0),
                seasons_at_one_club=int(summary.get("clubs_served", 1) == 1) * int(summary.get("seasons_played", 0)),
                championships=int(row["championships"] or 0),
            )
        )

    current_records: Dict[str, LeagueRecord] = {}
    for row in load_league_records(conn):
        record_payload = row.get("record", {}) or {}
        current_records[row["record_type"]] = LeagueRecord(
            record_type=row["record_type"],
            holder_id=row["holder_id"],
            holder_type=row["holder_type"],
            holder_name=str(record_payload.get("holder_name", row["holder_id"])),
            value=float(row["record_value"]),
            set_in_season=row["set_in_season"],
            detail=str(record_payload.get("detail", "")),
        )

    next_records = build_individual_records(career_stats, season_id)
    broken = []
    for record_type, candidate in sorted(next_records.items()):
        existing = current_records.get(record_type)
        existing_value = existing.value if existing is not None else float("-inf")
        if candidate.value <= existing_value:
            continue
        broken.append(
            RatifiedRecord(
                record_type=candidate.record_type,
                holder_id=candidate.holder_id,
                holder_type=candidate.holder_type,
                holder_name=candidate.holder_name,
                previous_value=0.0 if existing is None else float(existing.value),
                new_value=float(candidate.value),
                set_in_season=candidate.set_in_season,
                detail=candidate.detail,
            )
        )
        save_league_record(
            conn,
            record_type=candidate.record_type,
            holder_id=candidate.holder_id,
            holder_type=candidate.holder_type,
            record_value=float(candidate.value),
            set_in_season=candidate.set_in_season,
            record_payload={
                "holder_name": candidate.holder_name,
                "value": float(candidate.value),
                "detail": candidate.detail,
            },
        )

    set_state(
        conn,
        "offseason_records_ratified_json",
        json.dumps([_record_to_dict(record) for record in broken]),
    )
    set_state(conn, "offseason_records_ratified_for", season_id)
    conn.commit()
    return RatificationPayload(season_id=season_id, new_records=tuple(broken))


def _record_to_dict(record: RatifiedRecord) -> Dict[str, Any]:
    return {
        "record_type": record.record_type,
        "holder_id": record.holder_id,
        "holder_type": record.holder_type,
        "holder_name": record.holder_name,
        "previous_value": float(record.previous_value),
        "new_value": float(record.new_value),
        "set_in_season": record.set_in_season,
        "detail": record.detail,
    }


def _record_from_dict(entry: Mapping[str, Any]) -> RatifiedRecord:
    return RatifiedRecord(
        record_type=str(entry["record_type"]),
        holder_id=str(entry["holder_id"]),
        holder_type=str(entry["holder_type"]),
        holder_name=str(entry["holder_name"]),
        previous_value=float(entry["previous_value"]),
        new_value=float(entry["new_value"]),
        set_in_season=str(entry["set_in_season"]),
        detail=str(entry.get("detail", "")),
    )
```

(Note: `check_records_broken` from `records.py` is NOT used directly here because it requires a `match_stats` payload we don't have at season-end; we replicate the comparison logic locally for individual records, which is the only category in scope for this task. Team records and biggest-upset are out of scope per spec §2 — only re-introduce them if a later milestone provides the required pre-match overall data.)

- [ ] **Step 3.4: Run the tests — verify they pass**

Run: `python -m pytest tests/test_offseason_beats.py -v -p no:cacheprovider`

Expected: 6 passed (2 from Task 2 + 4 from Task 3).

- [ ] **Step 3.5: Run the full suite**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 280+ passed.

---

## Task 4: Implement `induct_hall_of_fame`

**Files:**
- Modify: `src/dodgeball_sim/offseason_beats.py` (replace `induct_hall_of_fame` stub)
- Modify: `tests/test_offseason_beats.py` (add tests)

Iterates retired players whose `final_season == season_id`, builds `CareerSummary` from persisted career stats, calls `evaluate_hall_of_fame`, persists inductees once via `save_hall_of_fame_entry`. Skips players already in `hall_of_fame`.

- [ ] **Step 4.1: Write the failing tests**

Append to `tests/test_offseason_beats.py`:

```python
from dataclasses import replace

from dodgeball_sim.models import Player, PlayerRatings
from dodgeball_sim.offseason_beats import induct_hall_of_fame
from dodgeball_sim.persistence import (
    load_hall_of_fame,
    save_hall_of_fame_entry,
    save_retired_player,
)


def _hof_player(player_id: str, name: str, age: int = 35) -> Player:
    # PlayerTraits has only `potential`, `growth_curve`, `consistency`, `pressure` —
    # the default `PlayerTraits()` is sufficient for these tests; do not pass kwargs
    # like `stamina` / `composure` / `leadership` (those don't exist on PlayerTraits).
    return Player(
        id=player_id,
        name=name,
        age=age,
        ratings=PlayerRatings(accuracy=80.0, power=80.0, dodge=80.0, catch=80.0, stamina=80.0),
        club_id="aurora",
        newcomer=False,
    )


def _seed_hof_candidate(conn: sqlite3.Connection, player_id: str, name: str, season_id: str):
    save_player_career_stats(
        conn,
        player_id,
        {
            "player_id": player_id,
            "player_name": name,
            "seasons_played": 8,
            "championships": 2,
            "awards_won": 4,
            "total_matches": 100,
            "total_eliminations": 220,
            "total_catches_made": 90,
            "total_dodges_successful": 110,
            "total_times_eliminated": 60,
            "peak_eliminations": 28,
            "career_eliminations": 220,
            "career_catches": 90,
            "career_dodges": 110,
            "clubs_served": 1,
        },
    )
    save_retired_player(conn, _hof_player(player_id, name), season_id, "age_decline")


def test_induct_hall_of_fame_inducts_qualified_retiree_once():
    conn = _fresh_conn()
    _seed_hof_candidate(conn, "p1", "Eligible Star", "season_1")
    _seed_hof_candidate(conn, "p2", "Average Joe", "season_1")
    save_player_career_stats(
        conn,
        "p2",
        {
            "player_id": "p2",
            "player_name": "Average Joe",
            "seasons_played": 3,
            "championships": 0,
            "awards_won": 0,
            "total_matches": 30,
            "total_eliminations": 20,
            "total_catches_made": 5,
            "total_dodges_successful": 10,
            "total_times_eliminated": 25,
            "peak_eliminations": 9,
            "career_eliminations": 20,
            "career_catches": 5,
            "career_dodges": 10,
            "clubs_served": 1,
        },
    )

    payload = induct_hall_of_fame(conn, "season_1")
    inducted_ids = {entry.player_id for entry in payload.new_inductees}

    assert "p1" in inducted_ids
    assert "p2" not in inducted_ids
    assert len(load_hall_of_fame(conn)) == 1

    # Idempotent re-entry
    payload_again = induct_hall_of_fame(conn, "season_1")
    assert payload_again.new_inductees == payload.new_inductees
    assert len(load_hall_of_fame(conn)) == 1


def test_induct_hall_of_fame_skips_already_inducted_player():
    conn = _fresh_conn()
    _seed_hof_candidate(conn, "p1", "Already In", "season_1")
    save_hall_of_fame_entry(conn, "p1", "season_0", {"player_id": "p1", "player_name": "Already In"})

    payload = induct_hall_of_fame(conn, "season_1")

    assert all(entry.player_id != "p1" for entry in payload.new_inductees)
    # Existing entry unchanged
    existing = load_hall_of_fame(conn)
    assert len(existing) == 1
    assert existing[0]["induction_season"] == "season_0"


def test_induct_hall_of_fame_empty_state_when_nobody_retired():
    conn = _fresh_conn()

    payload = induct_hall_of_fame(conn, "season_1")

    assert payload.new_inductees == ()
    assert get_state(conn, "offseason_hof_inducted_for") == "season_1"
```

- [ ] **Step 4.2: Run the tests — verify they fail**

Run: `python -m pytest tests/test_offseason_beats.py -v -p no:cacheprovider`

Expected: 3 new tests FAIL with `NotImplementedError("Implemented in Task 4.")`.

- [ ] **Step 4.3: Implement `induct_hall_of_fame`**

In `src/dodgeball_sim/offseason_beats.py`, replace the `induct_hall_of_fame` stub with:

```python
def induct_hall_of_fame(
    conn: sqlite3.Connection,
    season_id: str,
) -> InductionPayload:
    """Compute or load the Hall of Fame Induction beat payload. Idempotent per season_id."""
    from .career import CareerSummary, evaluate_hall_of_fame
    from .persistence import (
        get_state,
        load_hall_of_fame,
        save_hall_of_fame_entry,
        set_state,
    )

    cached_for = get_state(conn, "offseason_hof_inducted_for")
    if cached_for == season_id:
        raw = get_state(conn, "offseason_hof_inducted_json", "[]") or "[]"
        inductees = tuple(_inductee_from_dict(entry) for entry in json.loads(raw))
        return InductionPayload(season_id=season_id, new_inductees=inductees)

    already_inducted = {entry["player_id"] for entry in load_hall_of_fame(conn)}

    retired_rows = conn.execute(
        """
        SELECT player_id, final_season, age_at_retirement, player_json
        FROM retired_players
        WHERE final_season = ?
        ORDER BY player_id
        """,
        (season_id,),
    ).fetchall()

    new_inductees: List[HallOfFameInductee] = []
    for row in retired_rows:
        player_id = row["player_id"]
        if player_id in already_inducted:
            continue

        career_row = conn.execute(
            "SELECT career_summary_json FROM player_career_stats WHERE player_id = ?",
            (player_id,),
        ).fetchone()
        if career_row is None or career_row["career_summary_json"] is None:
            continue
        summary_dict = json.loads(career_row["career_summary_json"])
        summary = CareerSummary(
            player_id=player_id,
            player_name=str(summary_dict.get("player_name", player_id)),
            seasons_played=int(summary_dict.get("seasons_played", 0)),
            championships=int(summary_dict.get("championships", 0)),
            awards_won=int(summary_dict.get("awards_won", 0)),
            total_matches=int(summary_dict.get("total_matches", 0)),
            total_eliminations=int(summary_dict.get("total_eliminations", 0)),
            total_catches_made=int(summary_dict.get("total_catches_made", 0)),
            total_dodges_successful=int(summary_dict.get("total_dodges_successful", 0)),
            total_times_eliminated=int(summary_dict.get("total_times_eliminated", 0)),
            peak_eliminations=int(summary_dict.get("peak_eliminations", 0)),
            signature_moments=(),
        )
        case = evaluate_hall_of_fame(summary)
        if not case.inducted:
            continue

        save_hall_of_fame_entry(conn, player_id, season_id, summary_dict)
        new_inductees.append(
            HallOfFameInductee(
                player_id=player_id,
                player_name=summary.player_name,
                induction_season=season_id,
                legacy_score=float(case.score),
                threshold=float(case.threshold),
                reasons=tuple(case.reasons),
                seasons_played=summary.seasons_played,
                championships=summary.championships,
                awards_won=summary.awards_won,
                total_eliminations=summary.total_eliminations,
            )
        )

    set_state(
        conn,
        "offseason_hof_inducted_json",
        json.dumps([_inductee_to_dict(entry) for entry in new_inductees]),
    )
    set_state(conn, "offseason_hof_inducted_for", season_id)
    conn.commit()
    return InductionPayload(season_id=season_id, new_inductees=tuple(new_inductees))


def _inductee_to_dict(entry: HallOfFameInductee) -> Dict[str, Any]:
    return {
        "player_id": entry.player_id,
        "player_name": entry.player_name,
        "induction_season": entry.induction_season,
        "legacy_score": float(entry.legacy_score),
        "threshold": float(entry.threshold),
        "reasons": list(entry.reasons),
        "seasons_played": entry.seasons_played,
        "championships": entry.championships,
        "awards_won": entry.awards_won,
        "total_eliminations": entry.total_eliminations,
    }


def _inductee_from_dict(entry: Mapping[str, Any]) -> HallOfFameInductee:
    return HallOfFameInductee(
        player_id=str(entry["player_id"]),
        player_name=str(entry["player_name"]),
        induction_season=str(entry["induction_season"]),
        legacy_score=float(entry["legacy_score"]),
        threshold=float(entry["threshold"]),
        reasons=tuple(str(item) for item in entry.get("reasons", [])),
        seasons_played=int(entry["seasons_played"]),
        championships=int(entry["championships"]),
        awards_won=int(entry["awards_won"]),
        total_eliminations=int(entry["total_eliminations"]),
    )
```

- [ ] **Step 4.4: Run the tests — verify pass**

Run: `python -m pytest tests/test_offseason_beats.py -v -p no:cacheprovider`

Expected: 9 passed.

- [ ] **Step 4.5: Run the full suite**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 283+ passed.

---

## Task 5: Implement `build_rookie_class_preview`

**Files:**
- Modify: `src/dodgeball_sim/offseason_beats.py` (replace stub)
- Modify: `tests/test_offseason_beats.py` (add tests)

Reads V2-A `prospect_pool` for the class year first, falls back to legacy `free_agents`. Computes class summary + four storyline templates (each fires only when its threshold inequality holds; each has a backing fact persisted alongside). Persists `rookie_class_summary_<class_year>` for future-class comparisons.

**Storyline templates (canonical rules, locked here):**

| `template_id` | Threshold | Sentence template | Backing fact keys |
|---------------|-----------|-------------------|-------------------|
| `archetype_demand` | Top archetype is the #1 priority for ≥ ceil(total_clubs/2) clubs | `"{archetype} in heavy demand: {count} of {total} clubs prioritizing them this off-season"` | `archetype`, `count`, `total` |
| `top_band_depth` | `top_band_depth >= 1.2 * max(prior_top_band_depths)` AND ≥ 1 prior class exists | `"Deepest top-band class in {N} seasons"` where N = number of prior classes considered | `current_depth`, `prior_max`, `prior_classes_considered` |
| `ai_cluster` | Some single archetype is the #1 priority for ≥ 3 clubs (and the cluster is the strict top, not a tie with another archetype reaching the same count) | `"{count} clubs clustering on {archetype}"` | `archetype`, `count` |
| `free_agent_crop` | `free_agent_count <= min(prior_free_agent_counts)` AND ≥ 1 prior class exists AND current count strictly less than the existing min, OR ties the existing min with at least 1 prior class | `"Lightest free-agent crop in {M} seasons"` where M = number of prior years | `current_count`, `prior_min`, `prior_classes_considered` |

`top_band_depth` is defined as the count of prospects whose mean of `public_ratings_band[k][0]` (low end across the 5 attribute keys: accuracy, power, dodge, catch, stamina) is `>= 70.0`. For the legacy free-agent fallback, `top_band_depth` is the count of `Player` instances whose `overall() >= 70.0` and `archetype_distribution` is `{}` (empty — legacy fallback has no public archetype labels).

**Source signal availability:**
- Prospect pool present (size > 0): use `archetype_demand`, `top_band_depth`, `ai_cluster`, `free_agent_crop`.
- Legacy fallback (free agents only): only `free_agent_crop` is applicable; other three storylines are skipped because the underlying signal types don't exist for legacy data.

Storylines emit ONLY when the threshold inequality holds — never padded with filler.

- [ ] **Step 5.1: Write the failing tests**

Append to `tests/test_offseason_beats.py`:

```python
from dodgeball_sim.offseason_beats import build_rookie_class_preview
from dodgeball_sim.persistence import (
    save_club_recruitment_profile,
    save_free_agents,
    save_prospect_pool,
    set_state,
)
from dodgeball_sim.recruitment_domain import RecruitmentProfile
from dodgeball_sim.scouting_center import Prospect


def _prospect(player_id: str, archetype: str, low_band: int, class_year: int = 2) -> Prospect:
    return Prospect(
        player_id=player_id,
        class_year=class_year,
        name=f"Rookie {player_id}",
        age=18,
        hometown="Anywhere",
        hidden_ratings={"accuracy": 70.0, "power": 70.0, "dodge": 70.0, "catch": 70.0, "stamina": 70.0},
        hidden_trajectory="normal",
        hidden_traits=[],
        public_archetype_guess=archetype,
        public_ratings_band={
            key: (low_band, low_band + 10) for key in ("accuracy", "power", "dodge", "catch", "stamina")
        },
    )


def _profile(club_id: str, top_archetype: str) -> RecruitmentProfile:
    priorities = {arc: 0.1 for arc in ("Sharpshooter", "Enforcer", "Escape Artist", "Ball Hawk", "Iron Engine")}
    priorities[top_archetype] = 0.9
    return RecruitmentProfile(
        club_id=club_id,
        archetype_priorities=priorities,
        risk_tolerance=0.5,
        prestige=0.5,
        playing_time_pitch=0.5,
        evaluation_quality=0.5,
    )


def test_rookie_preview_uses_prospect_pool_when_present():
    conn = _fresh_conn()
    save_prospect_pool(conn, [
        _prospect("r1", "Sharpshooter", 75),
        _prospect("r2", "Enforcer", 65),
        _prospect("r3", "Sharpshooter", 78),
    ])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert payload.source == "prospect_pool"
    assert payload.class_size == 3
    assert payload.archetype_distribution.get("Sharpshooter") == 2
    assert payload.archetype_distribution.get("Enforcer") == 1
    assert payload.top_band_depth == 2  # r1 (75) and r3 (78) above 70


def test_rookie_preview_falls_back_to_legacy_free_agents_when_pool_empty():
    conn = _fresh_conn()
    save_free_agents(
        conn,
        [_hof_player("fa1", "Free Agent A", age=21), _hof_player("fa2", "Free Agent B", age=22)],
        "season_2",
    )

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert payload.source == "legacy_free_agents"
    assert payload.class_size == 2
    assert payload.archetype_distribution == {}
    assert all(s.template_id != "archetype_demand" for s in payload.storylines)


def test_rookie_preview_does_not_mutate_prospect_pool():
    conn = _fresh_conn()
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 75)])

    build_rookie_class_preview(conn, "season_1", class_year=2)
    rows = conn.execute("SELECT player_id, is_signed FROM prospect_pool").fetchall()

    assert [(row["player_id"], row["is_signed"]) for row in rows] == [("r1", 0)]


def test_rookie_preview_does_not_leak_hidden_prospect_data():
    conn = _fresh_conn()
    p = _prospect("r1", "Sharpshooter", 75)
    save_prospect_pool(conn, [p])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)
    raw = get_state(conn, "offseason_rookie_preview_json")
    text = raw or ""

    assert "hidden_ratings" not in text
    assert "hidden_trajectory" not in text
    assert "hidden_traits" not in text
    # No exact public-band high values either; only allowed aggregates surface
    for storyline in payload.storylines:
        for key in storyline.fact:
            assert key not in {"hidden_ratings", "hidden_trajectory", "hidden_traits"}


def test_rookie_preview_archetype_demand_storyline_fires_only_when_threshold_met():
    conn = _fresh_conn()
    # 4 clubs, 3 prioritize Sharpshooter (threshold ceil(4/2) = 2 -> fires)
    for club_id, top in [("a", "Sharpshooter"), ("b", "Sharpshooter"), ("c", "Sharpshooter"), ("d", "Enforcer")]:
        save_club_recruitment_profile(conn, _profile(club_id, top))
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 70)])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    demand = [s for s in payload.storylines if s.template_id == "archetype_demand"]
    assert len(demand) == 1
    assert demand[0].fact["archetype"] == "Sharpshooter"
    assert demand[0].fact["count"] == 3
    assert demand[0].fact["total"] == 4
    assert "Sharpshooter in heavy demand" in demand[0].sentence


def test_rookie_preview_archetype_demand_storyline_skipped_when_under_threshold():
    conn = _fresh_conn()
    # 4 clubs, only 1 prioritizes Sharpshooter (under threshold 2)
    for club_id, top in [("a", "Sharpshooter"), ("b", "Enforcer"), ("c", "Ball Hawk"), ("d", "Iron Engine")]:
        save_club_recruitment_profile(conn, _profile(club_id, top))
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 70)])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert all(s.template_id != "archetype_demand" for s in payload.storylines)


def test_rookie_preview_persists_class_summary_for_future_comparisons():
    conn = _fresh_conn()
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 80), _prospect("r2", "Enforcer", 60)])

    build_rookie_class_preview(conn, "season_1", class_year=2)

    raw = get_state(conn, "rookie_class_summary_2")
    assert raw is not None
    summary = json.loads(raw)
    assert summary["class_size"] == 2
    assert summary["top_band_depth"] == 1
    assert "free_agent_count" in summary


def test_rookie_preview_top_band_depth_storyline_fires_when_class_is_deepest():
    conn = _fresh_conn()
    set_state(conn, "rookie_class_summary_1", json.dumps({"class_size": 5, "top_band_depth": 1, "free_agent_count": 4}))
    save_prospect_pool(conn, [
        _prospect("r1", "Sharpshooter", 80, class_year=2),
        _prospect("r2", "Enforcer", 80, class_year=2),
        _prospect("r3", "Ball Hawk", 80, class_year=2),
    ])

    payload = build_rookie_class_preview(conn, "season_2", class_year=2)

    deepest = [s for s in payload.storylines if s.template_id == "top_band_depth"]
    assert len(deepest) == 1
    assert deepest[0].fact["current_depth"] == 3
    assert deepest[0].fact["prior_max"] == 1
    assert "Deepest top-band class" in deepest[0].sentence


def test_rookie_preview_idempotent_returns_same_payload_on_second_call():
    conn = _fresh_conn()
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 75)])

    first = build_rookie_class_preview(conn, "season_1", class_year=2)
    second = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert first == second
    assert get_state(conn, "offseason_rookie_preview_for") == "season_1"
```

- [ ] **Step 5.2: Run the tests — verify they fail**

Run: `python -m pytest tests/test_offseason_beats.py -v -p no:cacheprovider`

Expected: 9 new tests FAIL with `NotImplementedError("Implemented in Task 5.")`.

- [ ] **Step 5.3: Implement `build_rookie_class_preview`**

In `src/dodgeball_sim/offseason_beats.py`, replace the `build_rookie_class_preview` stub with:

```python
_PROSPECT_RATING_KEYS = ("accuracy", "power", "dodge", "catch", "stamina")
_TOP_BAND_THRESHOLD = 70.0
_DEEPEST_CLASS_FACTOR = 1.2


def build_rookie_class_preview(
    conn: sqlite3.Connection,
    season_id: str,
    class_year: int,
) -> RookiePreviewPayload:
    """Compute or load the Rookie Class Preview beat payload. Idempotent per season_id.

    Reads the V2-A prospect pool when present, falls back to V1 free agents otherwise.
    Never mutates either source.
    """
    from .persistence import (
        get_state,
        load_club_recruitment_profiles,
        load_free_agents,
        load_prospect_pool,
        set_state,
    )

    cached_for = get_state(conn, "offseason_rookie_preview_for")
    if cached_for == season_id:
        raw = get_state(conn, "offseason_rookie_preview_json", "{}") or "{}"
        return _payload_from_dict(json.loads(raw))

    prospects = load_prospect_pool(conn, class_year=class_year)
    free_agents = load_free_agents(conn)

    if prospects:
        source = "prospect_pool"
        class_size = len(prospects)
        archetype_distribution: Dict[str, int] = {}
        for prospect in prospects:
            archetype_distribution[prospect.public_archetype_guess] = (
                archetype_distribution.get(prospect.public_archetype_guess, 0) + 1
            )
        top_band_depth = sum(
            1 for prospect in prospects if _prospect_band_low_mean(prospect) >= _TOP_BAND_THRESHOLD
        )
    else:
        source = "legacy_free_agents"
        class_size = len(free_agents)
        archetype_distribution = {}
        top_band_depth = sum(1 for player in free_agents if player.overall() >= _TOP_BAND_THRESHOLD)

    free_agent_count = len(free_agents)

    storylines: List[RookieStoryline] = []

    if source == "prospect_pool":
        profiles = load_club_recruitment_profiles(conn)
        if profiles:
            top_picks: Dict[str, int] = {}
            for profile in profiles.values():
                if not profile.archetype_priorities:
                    continue
                top_archetype = max(
                    profile.archetype_priorities.items(),
                    key=lambda item: (item[1], item[0]),
                )[0]
                top_picks[top_archetype] = top_picks.get(top_archetype, 0) + 1

            total_clubs = len(profiles)
            demand_threshold = (total_clubs + 1) // 2  # ceil(total/2)
            if top_picks:
                leading_archetype, leading_count = max(
                    top_picks.items(), key=lambda item: (item[1], item[0])
                )
                if leading_count >= demand_threshold:
                    storylines.append(
                        RookieStoryline(
                            template_id="archetype_demand",
                            sentence=(
                                f"{leading_archetype} in heavy demand: {leading_count} of "
                                f"{total_clubs} clubs prioritizing them this off-season"
                            ),
                            fact={
                                "archetype": leading_archetype,
                                "count": leading_count,
                                "total": total_clubs,
                            },
                        )
                    )

                strict_top = sorted(top_picks.values(), reverse=True)
                ai_cluster_threshold = 3
                if leading_count >= ai_cluster_threshold and (
                    len(strict_top) == 1 or strict_top[0] > strict_top[1]
                ):
                    storylines.append(
                        RookieStoryline(
                            template_id="ai_cluster",
                            sentence=f"{leading_count} clubs clustering on {leading_archetype}",
                            fact={
                                "archetype": leading_archetype,
                                "count": leading_count,
                            },
                        )
                    )

        prior_top_band, prior_classes_considered = _prior_top_band_history(conn, class_year)
        if prior_classes_considered >= 1 and prior_top_band > 0:
            if top_band_depth >= _DEEPEST_CLASS_FACTOR * prior_top_band:
                storylines.append(
                    RookieStoryline(
                        template_id="top_band_depth",
                        sentence=f"Deepest top-band class in {prior_classes_considered} seasons",
                        fact={
                            "current_depth": top_band_depth,
                            "prior_max": prior_top_band,
                            "prior_classes_considered": prior_classes_considered,
                        },
                    )
                )

    prior_min_fa, prior_fa_considered = _prior_free_agent_history(conn, class_year)
    if prior_fa_considered >= 1 and free_agent_count <= prior_min_fa:
        storylines.append(
            RookieStoryline(
                template_id="free_agent_crop",
                sentence=f"Lightest free-agent crop in {prior_fa_considered} seasons",
                fact={
                    "current_count": free_agent_count,
                    "prior_min": prior_min_fa,
                    "prior_classes_considered": prior_fa_considered,
                },
            )
        )

    set_state(
        conn,
        f"rookie_class_summary_{class_year}",
        json.dumps(
            {
                "class_size": class_size,
                "top_band_depth": top_band_depth,
                "free_agent_count": free_agent_count,
            }
        ),
    )

    payload = RookiePreviewPayload(
        season_id=season_id,
        class_year=class_year,
        source=source,
        class_size=class_size,
        archetype_distribution=archetype_distribution,
        top_band_depth=top_band_depth,
        free_agent_count=free_agent_count,
        storylines=tuple(storylines),
    )
    set_state(conn, "offseason_rookie_preview_json", json.dumps(_payload_to_dict(payload)))
    set_state(conn, "offseason_rookie_preview_for", season_id)
    conn.commit()
    return payload


def _prospect_band_low_mean(prospect) -> float:
    values = [float(prospect.public_ratings_band.get(key, (0, 0))[0]) for key in _PROSPECT_RATING_KEYS]
    return sum(values) / len(values) if values else 0.0


def _prior_top_band_history(conn: sqlite3.Connection, current_class_year: int) -> Tuple[int, int]:
    rows = conn.execute(
        "SELECT key, value FROM dynasty_state WHERE key LIKE 'rookie_class_summary_%'"
    ).fetchall()
    prior_depths: List[int] = []
    for row in rows:
        try:
            year = int(row["key"].rsplit("_", 1)[-1])
        except ValueError:
            continue
        if year >= current_class_year:
            continue
        try:
            payload = json.loads(row["value"])
        except (TypeError, ValueError):
            continue
        prior_depths.append(int(payload.get("top_band_depth", 0)))
    return (max(prior_depths) if prior_depths else 0, len(prior_depths))


def _prior_free_agent_history(conn: sqlite3.Connection, current_class_year: int) -> Tuple[int, int]:
    rows = conn.execute(
        "SELECT key, value FROM dynasty_state WHERE key LIKE 'rookie_class_summary_%'"
    ).fetchall()
    prior_counts: List[int] = []
    for row in rows:
        try:
            year = int(row["key"].rsplit("_", 1)[-1])
        except ValueError:
            continue
        if year >= current_class_year:
            continue
        try:
            payload = json.loads(row["value"])
        except (TypeError, ValueError):
            continue
        prior_counts.append(int(payload.get("free_agent_count", 0)))
    return (min(prior_counts) if prior_counts else 0, len(prior_counts))


def _payload_to_dict(payload: RookiePreviewPayload) -> Dict[str, Any]:
    return {
        "season_id": payload.season_id,
        "class_year": payload.class_year,
        "source": payload.source,
        "class_size": payload.class_size,
        "archetype_distribution": dict(payload.archetype_distribution),
        "top_band_depth": payload.top_band_depth,
        "free_agent_count": payload.free_agent_count,
        "storylines": [
            {"template_id": s.template_id, "sentence": s.sentence, "fact": dict(s.fact)}
            for s in payload.storylines
        ],
    }


def _payload_from_dict(entry: Mapping[str, Any]) -> RookiePreviewPayload:
    return RookiePreviewPayload(
        season_id=str(entry["season_id"]),
        class_year=int(entry["class_year"]),
        source=str(entry["source"]),
        class_size=int(entry["class_size"]),
        archetype_distribution=dict(entry.get("archetype_distribution", {})),
        top_band_depth=int(entry["top_band_depth"]),
        free_agent_count=int(entry["free_agent_count"]),
        storylines=tuple(
            RookieStoryline(
                template_id=str(item["template_id"]),
                sentence=str(item["sentence"]),
                fact=dict(item.get("fact", {})),
            )
            for item in entry.get("storylines", [])
        ),
    )
```

- [ ] **Step 5.4: Run the tests — verify they pass**

Run: `python -m pytest tests/test_offseason_beats.py -v -p no:cacheprovider`

Expected: 18 passed.

- [ ] **Step 5.5: Run the full suite**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 292+ passed.

---

## Task 6: Wire Computations into `initialize_manager_offseason` + Real Renderers

**Files:**
- Modify: `src/dodgeball_sim/manager_gui.py:1031-1190` (replace stub branches with real renderers)
- Modify: `src/dodgeball_sim/manager_gui.py:1254-1326` (`initialize_manager_offseason`)
- Modify: `tests/test_manager_gui.py` (add render tests)

The three pure computations need to run once at off-season entry, and the renderer needs to read their persisted payloads and format them for the ceremony shell.

- [ ] **Step 6.1: Write failing render tests for the three new beats**

Append to `tests/test_manager_gui.py` (after the existing `test_offseason_champion_beat_prefers_playoff_outcome` test, ~line 909):

```python
def test_offseason_records_ratified_beat_renders_persisted_payload():
    import json as _json
    from dodgeball_sim.persistence import set_state

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    set_state(
        conn,
        "offseason_records_ratified_for",
        "season_1",
    )
    set_state(
        conn,
        "offseason_records_ratified_json",
        _json.dumps([
            {
                "record_type": "career_eliminations",
                "holder_id": "p1",
                "holder_type": "player",
                "holder_name": "Alpha Star",
                "previous_value": 100.0,
                "new_value": 142.0,
                "set_in_season": "season_1",
                "detail": "Alpha Star now leads with 142 career eliminations",
            }
        ]),
    )
    conn.commit()

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("records_ratified"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        season_outcome=None,
        records_payload_json=_json.dumps([
            {
                "record_type": "career_eliminations",
                "holder_id": "p1",
                "holder_type": "player",
                "holder_name": "Alpha Star",
                "previous_value": 100.0,
                "new_value": 142.0,
                "set_in_season": "season_1",
                "detail": "Alpha Star now leads with 142 career eliminations",
            }
        ]),
    )

    assert beat.title == "Records Ratified"
    assert "Alpha Star" in beat.body
    assert "142" in beat.body


def test_offseason_records_ratified_beat_renders_empty_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("records_ratified"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        records_payload_json="[]",
    )

    assert beat.title == "Records Ratified"
    assert "No new records" in beat.body or "No league records" in beat.body


def test_offseason_hof_induction_beat_renders_persisted_payload():
    import json as _json

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("hof_induction"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        hof_payload_json=_json.dumps([
            {
                "player_id": "p1",
                "player_name": "Eternal Captain",
                "induction_season": "season_1",
                "legacy_score": 138.5,
                "threshold": 120.0,
                "reasons": ["longevity", "championship pedigree"],
                "seasons_played": 9,
                "championships": 2,
                "awards_won": 3,
                "total_eliminations": 240,
            }
        ]),
    )

    assert beat.title == "Hall of Fame Induction"
    assert "Eternal Captain" in beat.body
    assert "138" in beat.body  # legacy score


def test_offseason_hof_induction_beat_renders_empty_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("hof_induction"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        hof_payload_json="[]",
    )

    assert beat.title == "Hall of Fame Induction"
    assert "No new inductees" in beat.body or "no qualifying" in beat.body.lower()


def test_offseason_rookie_class_preview_beat_renders_persisted_payload():
    import json as _json

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("rookie_class_preview"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        rookie_preview_payload_json=_json.dumps({
            "season_id": "season_1",
            "class_year": 2,
            "source": "prospect_pool",
            "class_size": 12,
            "archetype_distribution": {"Sharpshooter": 5, "Enforcer": 4, "Ball Hawk": 3},
            "top_band_depth": 4,
            "free_agent_count": 6,
            "storylines": [
                {
                    "template_id": "archetype_demand",
                    "sentence": "Sharpshooter in heavy demand: 4 of 6 clubs prioritizing them this off-season",
                    "fact": {"archetype": "Sharpshooter", "count": 4, "total": 6},
                }
            ],
        }),
    )

    assert beat.title == "Rookie Class Preview"
    assert "12" in beat.body  # class size
    assert "Sharpshooter" in beat.body
    assert "heavy demand" in beat.body


def test_initialize_manager_offseason_runs_three_new_computations_once():
    from dodgeball_sim.persistence import save_player_career_stats, save_retired_player

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    season = load_season(conn, "season_1")

    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    assert get_state(conn, "offseason_records_ratified_for") == "season_1"
    assert get_state(conn, "offseason_hof_inducted_for") == "season_1"
    assert get_state(conn, "offseason_rookie_preview_for") == "season_1"

    # Re-entry does NOT recompute
    before_records = get_state(conn, "offseason_records_ratified_json")
    before_hof = get_state(conn, "offseason_hof_inducted_json")
    before_preview = get_state(conn, "offseason_rookie_preview_json")
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)
    assert get_state(conn, "offseason_records_ratified_json") == before_records
    assert get_state(conn, "offseason_hof_inducted_json") == before_hof
    assert get_state(conn, "offseason_rookie_preview_json") == before_preview
```

- [ ] **Step 6.2: Run the new tests — verify they fail**

Run: `python -m pytest tests/test_manager_gui.py -k "records_ratified or hof_induction or rookie_class_preview or initialize_manager_offseason_runs_three" -v -p no:cacheprovider`

Expected: 6 new tests FAIL — most with `TypeError` from unknown keyword arguments (`records_payload_json`, `hof_payload_json`, `rookie_preview_payload_json`), and the integration test failing because the dynasty_state keys aren't being set yet.

- [ ] **Step 6.3: Extend `build_offseason_ceremony_beat` signature with three new optional payload params**

In `manager_gui.py`, find the function signature (around line 1031) and add three new keyword args at the end:

```python
def build_offseason_ceremony_beat(
    beat_index: int,
    season: Optional[Season],
    clubs: Mapping[str, Club],
    rosters: Mapping[str, List[Player]],
    standings: Iterable[StandingsRow],
    awards: Iterable[Any],
    player_club_id: Optional[str],
    next_season: Optional[Season] = None,
    development_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    retirement_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    draft_pool: Optional[Iterable[Player]] = None,
    signed_player_id: Optional[str] = None,
    recruitment_available: bool = False,
    recruitment_summary: Optional[Mapping[str, Any]] = None,
    season_outcome: Optional[Any] = None,
    records_payload_json: Optional[str] = None,
    hof_payload_json: Optional[str] = None,
    rookie_preview_payload_json: Optional[str] = None,
) -> OffseasonCeremonyBeat:
```

- [ ] **Step 6.4: Replace the three stub branches with real renderers**

In `manager_gui.py`, replace the stub `records_ratified` branch added in Task 1 with:

```python
    if key == "records_ratified":
        entries = []
        if records_payload_json:
            try:
                entries = list(json.loads(records_payload_json) or [])
            except (TypeError, ValueError):
                entries = []
        if not entries:
            body = "No new league records were set this season."
        else:
            lines = ["New league records:"]
            for entry in entries:
                holder = entry.get("holder_name", entry.get("holder_id", "?"))
                prev = float(entry.get("previous_value", 0.0))
                new = float(entry.get("new_value", 0.0))
                detail = entry.get("detail", "")
                lines.append(
                    f"  {entry.get('record_type', '?').replace('_', ' ').title()}: "
                    f"{holder} {prev:g} -> {new:g} ({detail})"
                )
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Records Ratified", body)
```

Replace the stub `hof_induction` branch with:

```python
    if key == "hof_induction":
        entries = []
        if hof_payload_json:
            try:
                entries = list(json.loads(hof_payload_json) or [])
            except (TypeError, ValueError):
                entries = []
        if not entries:
            body = "No new inductees this off-season."
        else:
            lines = ["Hall of Fame inductees:"]
            for entry in entries:
                reasons = ", ".join(entry.get("reasons", [])) or "qualified by score"
                lines.append(
                    f"  {entry.get('player_name', entry.get('player_id', '?'))}: "
                    f"legacy {float(entry.get('legacy_score', 0.0)):.1f} "
                    f"(threshold {float(entry.get('threshold', 0.0)):.1f})"
                )
                lines.append(
                    f"    {int(entry.get('seasons_played', 0))} seasons, "
                    f"{int(entry.get('championships', 0))} titles, "
                    f"{int(entry.get('awards_won', 0))} awards, "
                    f"{int(entry.get('total_eliminations', 0))} career eliminations"
                )
                lines.append(f"    Reasons: {reasons}")
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Hall of Fame Induction", body)
```

Replace the stub `rookie_class_preview` branch with:

```python
    if key == "rookie_class_preview":
        payload: Dict[str, Any] = {}
        if rookie_preview_payload_json:
            try:
                payload = dict(json.loads(rookie_preview_payload_json) or {})
            except (TypeError, ValueError):
                payload = {}
        class_size = int(payload.get("class_size", 0))
        archetype_distribution: Dict[str, int] = dict(payload.get("archetype_distribution", {}) or {})
        free_agent_count = int(payload.get("free_agent_count", 0))
        top_band_depth = int(payload.get("top_band_depth", 0))
        storylines = list(payload.get("storylines", []) or [])
        source = str(payload.get("source", "prospect_pool"))

        if class_size == 0 and free_agent_count == 0:
            body = "No incoming class data is available yet."
        else:
            lines = [f"Incoming class size: {class_size}"]
            lines.append(f"Top-band prospects (>= 70 OVR band low): {top_band_depth}")
            lines.append(f"Free-agent count: {free_agent_count}")
            if archetype_distribution:
                ordered = sorted(archetype_distribution.items(), key=lambda item: (-item[1], item[0]))
                lines.append("Archetype distribution: " + ", ".join(f"{name} {count}" for name, count in ordered))
            if storylines:
                lines.append("")
                lines.append("Market storylines:")
                for storyline in storylines:
                    lines.append(f"  - {storyline.get('sentence', '')}")
            if source == "legacy_free_agents":
                lines.append("")
                lines.append("(Legacy save: showing free-agent fallback only.)")
            lines.append("")
            lines.append("Continue to Recruitment Day.")
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Rookie Class Preview", body)
```

- [ ] **Step 6.5: Add the offseason_beats import and wire computations into `initialize_manager_offseason`**

In `manager_gui.py`, near the top imports (after the existing `from .recruitment import generate_rookie_class` line ~70), add:

```python
from .offseason_beats import (
    build_rookie_class_preview,
    induct_hall_of_fame,
    ratify_records,
)
```

In `initialize_manager_offseason` (around line 1320), after the existing line:
```python
set_state(conn, "offseason_initialized_for", season.season_id)
```

Add:
```python
    ratify_records(conn, season.season_id)
    induct_hall_of_fame(conn, season.season_id)
    next_class_year = (
        int(season.season_id.rsplit("_", 1)[-1]) + 1
        if season.season_id.rsplit("_", 1)[-1].isdigit()
        else 1
    )
    build_rookie_class_preview(conn, season.season_id, next_class_year)
```

- [ ] **Step 6.6: Wire the persisted payloads into `show_season_complete`**

In `manager_gui.py`, find the `show_season_complete` method (~line 2487) and update the `build_offseason_ceremony_beat(...)` call (~line 2515-2529) to pass the three new payload arguments:

Find:
```python
        beat = build_offseason_ceremony_beat(
            self.cursor.offseason_beat_index,
            self.season,
            self.clubs,
            self.rosters,
            standings,
            awards,
            self.player_club_id,
            next_preview,
            development_rows,
            retirement_rows,
            draft_pool,
            signed_player_id,
            season_outcome=load_season_outcome(self.conn, self.season.season_id) if self.season else None,
        )
```

Replace with:
```python
        beat = build_offseason_ceremony_beat(
            self.cursor.offseason_beat_index,
            self.season,
            self.clubs,
            self.rosters,
            standings,
            awards,
            self.player_club_id,
            next_preview,
            development_rows,
            retirement_rows,
            draft_pool,
            signed_player_id,
            season_outcome=load_season_outcome(self.conn, self.season.season_id) if self.season else None,
            records_payload_json=get_state(self.conn, "offseason_records_ratified_json"),
            hof_payload_json=get_state(self.conn, "offseason_hof_inducted_json"),
            rookie_preview_payload_json=get_state(self.conn, "offseason_rookie_preview_json"),
        )
```

- [ ] **Step 6.7: Run the new tests — verify they pass**

Run: `python -m pytest tests/test_manager_gui.py -k "records_ratified or hof_induction or rookie_class_preview or initialize_manager_offseason_runs_three" -v -p no:cacheprovider`

Expected: 6 passed.

- [ ] **Step 6.8: Run the full suite**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 298+ passed.

---

## Task 7: Resume-At-Each-Beat Integration Test + Final Verification

**Files:**
- Modify: `tests/test_manager_gui.py`

The spec §7 explicitly requires "Resume at each inserted beat renders the correct payload." This task verifies that exiting and re-entering the off-season at any of the three new beats produces a correct render with the persisted payload.

- [ ] **Step 7.1: Write the failing resume test**

Append to `tests/test_manager_gui.py`:

```python
def test_resume_at_each_new_beat_renders_persisted_payload():
    """Spec §7: re-entering off-season at any of the three new beats reads the
    stored payload, never recomputes."""
    from dodgeball_sim.persistence import save_prospect_pool, save_player_career_stats, save_retired_player
    from dodgeball_sim.scouting_center import Prospect

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    season = load_season(conn, "season_1")

    # Seed a HoF candidate
    save_player_career_stats(
        conn,
        "hof_p",
        {
            "player_id": "hof_p",
            "player_name": "Captain Legacy",
            "seasons_played": 9,
            "championships": 2,
            "awards_won": 4,
            "total_matches": 110,
            "total_eliminations": 250,
            "total_catches_made": 100,
            "total_dodges_successful": 120,
            "total_times_eliminated": 50,
            "peak_eliminations": 30,
            "career_eliminations": 250,
            "career_catches": 100,
            "career_dodges": 120,
            "clubs_served": 1,
        },
    )
    aurora_first = next(iter(rosters["aurora"]))
    save_retired_player(conn, replace(aurora_first, id="hof_p", name="Captain Legacy"), "season_1", "age_decline")

    # Seed a prospect pool for class_year=2 so the rookie preview has data
    save_prospect_pool(conn, [
        Prospect(
            player_id="r1",
            class_year=2,
            name="Rookie One",
            age=18,
            hometown="Anywhere",
            hidden_ratings={k: 70.0 for k in ("accuracy", "power", "dodge", "catch", "stamina")},
            hidden_trajectory="normal",
            hidden_traits=[],
            public_archetype_guess="Sharpshooter",
            public_ratings_band={k: (75, 85) for k in ("accuracy", "power", "dodge", "catch", "stamina")},
        ),
    ])
    conn.commit()

    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    # Snapshot persisted state
    records_json = get_state(conn, "offseason_records_ratified_json")
    hof_json = get_state(conn, "offseason_hof_inducted_json")
    preview_json = get_state(conn, "offseason_rookie_preview_json")

    # Render each new beat: simulates resume after app restart
    rosters_after = load_all_rosters(conn)
    for beat_key in ("records_ratified", "hof_induction", "rookie_class_preview"):
        idx = OFFSEASON_CEREMONY_BEATS.index(beat_key)
        beat = build_offseason_ceremony_beat(
            idx,
            season,
            clubs,
            rosters_after,
            [],
            [],
            "aurora",
            records_payload_json=records_json,
            hof_payload_json=hof_json,
            rookie_preview_payload_json=preview_json,
        )
        assert beat.key == beat_key
        assert beat.body  # not empty

    # And: re-running initialize_manager_offseason does not change the persisted payloads
    initialize_manager_offseason(conn, season, clubs, rosters_after, root_seed=20260426)
    assert get_state(conn, "offseason_records_ratified_json") == records_json
    assert get_state(conn, "offseason_hof_inducted_json") == hof_json
    assert get_state(conn, "offseason_rookie_preview_json") == preview_json
```

- [ ] **Step 7.2: Run the test — verify it passes**

Run: `python -m pytest tests/test_manager_gui.py -k "resume_at_each_new_beat" -v -p no:cacheprovider`

Expected: PASS (the wiring from Task 6 already produces the correct behavior; this test simply verifies it end-to-end).

- [ ] **Step 7.3: Run the full suite — final green check**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 299+ passed.

- [ ] **Step 7.4: Run the existing milestone-specific suites flagged by V2-F's handoff**

Run: `python -m pytest tests/test_playoffs.py tests/test_dynasty_persistence.py tests/test_scheduler.py tests/test_manager_gui.py tests/test_persistence.py tests/test_v2a_scouting_persistence.py tests/test_v2b_recruitment_persistence.py tests/test_offseason_beats.py -q -p no:cacheprovider`

Expected: All passed. No regressions in V2-A / V2-B / V2-F territory.

- [ ] **Step 7.5: Update `docs/specs/MILESTONES.md` — mark V2-E shipped**

Find the V2-E row in the table:
```
| V2-E  | Off-season Beats Completion                     | Designed (2026-04-28)        | `docs/specs/2026-04-28-v2-e-offseason-beats/design.md`               | Adds Records Ratified, HoF Induction, Rookie Class Preview to complete the 10-beat ceremony. Implement after V2-F so champion truth is playoff-aware. |
```

Replace with:
```
| V2-E  | Off-season Beats Completion                     | Shipped (2026-04-28)         | `docs/specs/2026-04-28-v2-e-offseason-beats/design.md`               | Adds Records Ratified (idempotent), HoF Induction (uses career.evaluate_hall_of_fame), and Rookie Class Preview (V2-A/V2-B-derived storylines) to complete the 10-beat ceremony. |
```

- [ ] **Step 7.6: Write retrospective at `docs/retrospectives/2026-04-28-v2-e-handoff.md`**

Create the retrospective:

```markdown
# V2-E Off-season Beats Completion Handoff

Status: Shipped 2026-04-28.

Implemented the three trailing off-season beats — Records Ratified, Hall of Fame Induction, and Rookie Class Preview — completing the 10-beat ceremony in Manager Mode.

Pure-computation logic lives in `src/dodgeball_sim/offseason_beats.py`: three idempotent functions keyed by `(conn, season_id)`, each persisting their payload to `dynasty_state` so re-entry never recomputes. No new schema migration; all needed tables (`league_records`, `hall_of_fame`, `prospect_pool`, `free_agents`, `club_recruitment_profile`) existed from V2-A/V2-B/V2-F.

Records Ratified: end-of-season comparison only (per spec §2 same-season rule); individual records (career_eliminations, career_catches, career_dodges, most_seasons_at_one_club, most_championships) are in scope. Team and biggest-upset records remain out of scope until pre-match overall data lands in a later milestone.

Hall of Fame Induction: consumes `career.evaluate_hall_of_fame`; iterates only retired players whose `final_season == season_id`; skips players already in `hall_of_fame`. Empty state renders cleanly.

Rookie Class Preview: V2-A prospect pool first, legacy free agents fallback. Four deterministic storyline templates (`archetype_demand`, `top_band_depth`, `ai_cluster`, `free_agent_crop`), each fact-backed and threshold-gated — no LLM, no padded narrative. Persisted `rookie_class_summary_<class_year>` history enables across-season comparisons starting from class year 2.

Verification:

- `python -m pytest tests/test_offseason_beats.py tests/test_manager_gui.py -q -p no:cacheprovider`
- `python -m pytest -q -p no:cacheprovider`
```

- [ ] **Step 7.7: Save and verify**

Run: `python -m pytest -q -p no:cacheprovider`

Expected: 299+ passed (final state).

---

## Spec Coverage Audit (self-review of plan against spec)

| Spec Requirement | Task |
|------------------|------|
| §1 ten-beat order with Records / HoF / Rookie Preview inserted at positions 4, 5, 8 | Task 1 |
| §2 Records Ratified compares against persisted records, persists once, idempotent | Task 3 |
| §2 Same-season collisions: ratification computed once at off-season entry, end-of-season values | Task 3 (function structure: single computation at first call) |
| §2 Biggest-upset out of scope unless pre-match overall data exists | Task 3 (only individual records implemented; team + upset omitted) |
| §3 HoF uses `career.evaluate_hall_of_fame` | Task 4 |
| §3 Persist new inductees once, skip already-inducted | Task 4 |
| §3 Empty state renders dignified message | Task 6 (renderer empty-state) + Task 4 test |
| §4 V2-A pool when present, legacy free-agent fallback | Task 5 |
| §4 No mutation of pool | Task 5 (read-only `load_prospect_pool`); test in Task 5 |
| §4 No leakage of hidden trajectory/traits/exact ratings | Task 5 test |
| §4 Storylines: derived facts only, four permitted signal types, no LLM, threshold-gated | Task 5 |
| §4 Each storyline persisted with backing fact | Task 5 (`RookieStoryline.fact`) |
| §5 Persistence keys (six) all set under their canonical names | Tasks 3, 4, 5 |
| §5 Rookie preview class history key (`rookie_class_summary_<year>`) persisted | Task 5 |
| §5 Re-entry doesn't duplicate, regenerate, alter recruitment/scouting | Tasks 3, 4, 5 (idempotency cache); Task 7 integration test |
| §6 UI uses existing ceremony shell | Task 6 (renderers extend `build_offseason_ceremony_beat`) |
| §7 Beat order has ten entries | Task 1 |
| §7 Records Ratified persists new records once | Task 3 |
| §7 Records empty state renders | Task 6 |
| §7 HoF inducts eligible retired player once | Task 4 |
| §7 HoF empty state renders | Task 6 |
| §7 Rookie Preview uses prospect pool when present | Task 5 |
| §7 Rookie Preview falls back to legacy free agents | Task 5 |
| §7 Rookie Preview does not leak hidden prospect data | Task 5 |
| §7 Rookie Preview storylines fire only when threshold met, fact persisted | Task 5 |
| §7 Records Ratified surfaces only end-of-season improvements | Task 3 (single-pass at season-end) |
| §7 Resume at each inserted beat renders correct payload | Task 7 |
| §8 V2-F playoff champion truth honored | Already done in V2-F; verified intact by full-suite run in Task 7 |

No gaps detected.

---

*End of V2-E Off-season Beats Completion implementation plan.*
