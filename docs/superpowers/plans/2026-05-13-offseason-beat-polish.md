# Offseason Beat Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the offseason ceremony flow — dynamic beat skipping, four new custom components, season-stat awards, player-club-only development, and all copy/formatting fixes — without touching the recruiting lifecycle (Project B).

**Architecture:** A `compute_active_beats()` helper in `offseason_ceremony.py` builds the ordered list of beats that have real content at init time, stores it in state, and every downstream function (presentation, service) reads from that stored list. The fixed `OFFSEASON_CEREMONY_BEATS` constant remains as a fallback for legacy saves. New frontend components consume structured payloads from the backend; the generic beat card is used only for beats with no structured payload.

**Tech Stack:** Python 3.10+ backend (pytest for tests), React + TypeScript frontend (Vite build, npm run build to verify).

---

## File Map

| File | Role |
|---|---|
| `src/dodgeball_sim/offseason_ceremony.py` | Add `compute_active_beats()`, call in `initialize_manager_offseason`, fix body copy for champion + rookie preview |
| `src/dodgeball_sim/offseason_presentation.py` | Add `load_active_beats()`, rewrite `build_beat_response` to use active list, add dev/awards/rookie payload cases to `build_beat_payload`, update function signature |
| `src/dodgeball_sim/offseason_service.py` | Replace hardcoded-index guards with `load_active_beats()` calls |
| `src/dodgeball_sim/awards.py` | Audit `compute_season_awards` for edge-case duplicate emission |
| `frontend/src/types.ts` | Update `OffseasonAward`; add `DevelopmentBeatPayload`, `RookieClassPreviewBeatPayload`; update `OffseasonBeat` union |
| `frontend/src/components/ceremonies/ChampionReveal.tsx` | New — renders structured champion payload |
| `frontend/src/components/ceremonies/RecapStandings.tsx` | New — renders structured standings table |
| `frontend/src/components/ceremonies/DevelopmentResults.tsx` | New — renders player-club-only dev results |
| `frontend/src/components/ceremonies/RookieClassPreview.tsx` | New — renders structured rookie class data |
| `frontend/src/components/ceremonies/Ceremonies.tsx` | Fix AwardsNight icons/names/stats/sort; add NewSeasonEve toggle |
| `frontend/src/components/Offseason.tsx` | Route four beats to their new components |
| `tests/test_offseason_ceremony.py` | Add tests for active beats + awards dedup |

---

### Task 1: Audit awards dedup + add invariant test

**Files:**
- Read: `src/dodgeball_sim/awards.py`
- Modify: `tests/test_offseason_ceremony.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_offseason_ceremony.py`:

```python
from dodgeball_sim.awards import compute_season_awards
from dodgeball_sim.stats import PlayerMatchStats


def test_compute_season_awards_no_duplicate_award_types():
    """Each award_type appears at most once; a player can win multiple types."""
    stats = {
        "p1": PlayerMatchStats(eliminations_by_throw=10, catches_made=8, dodges_successful=5),
        "p2": PlayerMatchStats(eliminations_by_throw=3, catches_made=15, dodges_successful=2),
        "p3": PlayerMatchStats(eliminations_by_throw=6, catches_made=4, dodges_successful=3),
    }
    club_map = {"p1": "team_a", "p2": "team_b", "p3": "team_a"}
    newcomers = frozenset(["p3"])

    awards = compute_season_awards("s1", stats, club_map, newcomers)

    award_types = [a.award_type for a in awards]
    assert len(award_types) == len(set(award_types)), f"Duplicate award_type found: {award_types}"


def test_compute_season_awards_player_can_win_two_types():
    """p1 dominates all stats — should win mvp AND best_thrower (different types, not a bug)."""
    stats = {
        "p1": PlayerMatchStats(eliminations_by_throw=20, catches_made=1, dodges_successful=10),
        "p2": PlayerMatchStats(eliminations_by_throw=1, catches_made=20, dodges_successful=1),
    }
    club_map = {"p1": "team_a", "p2": "team_b"}
    newcomers = frozenset()

    awards = compute_season_awards("s1", stats, club_map, newcomers)

    winners = {a.award_type: a.player_id for a in awards}
    assert winners["mvp"] == "p1"
    assert winners["best_thrower"] == "p1"
    # p2 dominates catches
    assert winners["best_catcher"] == "p2"
    # No newcomers → no best_newcomer award
    assert "best_newcomer" not in winners
```

- [ ] **Step 2: Run to confirm both pass (no code changes needed — this verifies the algorithm is already correct)**

```
python -m pytest tests/test_offseason_ceremony.py::test_compute_season_awards_no_duplicate_award_types tests/test_offseason_ceremony.py::test_compute_season_awards_player_can_win_two_types -v
```

Expected: both PASS. If either fails, the algorithm has a real bug — inspect `compute_season_awards` in `awards.py` and fix before continuing.

- [ ] **Step 3: Commit**

```bash
git add tests/test_offseason_ceremony.py
git commit -m "test: add awards dedup and multi-award invariant tests"
```

---

### Task 2: Add `compute_active_beats()` to offseason_ceremony.py

**Files:**
- Modify: `src/dodgeball_sim/offseason_ceremony.py`
- Modify: `tests/test_offseason_ceremony.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_offseason_ceremony.py`:

```python
import json
from dodgeball_sim.offseason_ceremony import compute_active_beats, OFFSEASON_CEREMONY_BEATS
from dodgeball_sim.persistence import get_state


def test_compute_active_beats_always_includes_core():
    active = compute_active_beats(
        records_payload_json=None,
        hof_payload_json=None,
        retirement_rows=[],
    )
    core = ["champion", "recap", "awards", "development",
            "rookie_class_preview", "recruitment", "schedule_reveal"]
    for key in core:
        assert key in active, f"'{key}' missing from active beats"


def test_compute_active_beats_excludes_empty_conditional():
    active = compute_active_beats(
        records_payload_json=None,
        hof_payload_json=None,
        retirement_rows=[],
    )
    assert "records_ratified" not in active
    assert "hof_induction" not in active
    assert "retirements" not in active


def test_compute_active_beats_includes_retirements_when_present():
    active = compute_active_beats(
        records_payload_json=None,
        hof_payload_json=None,
        retirement_rows=[{"player_id": "p1", "player_name": "Bob"}],
    )
    assert "retirements" in active


def test_compute_active_beats_includes_records_when_present():
    records_json = json.dumps([{"record_type": "most_elims", "holder_name": "Bob",
                                 "previous_value": 5.0, "new_value": 10.0, "detail": ""}])
    active = compute_active_beats(
        records_payload_json=records_json,
        hof_payload_json=None,
        retirement_rows=[],
    )
    assert "records_ratified" in active


def test_compute_active_beats_preserves_order():
    records_json = json.dumps([{"record_type": "x", "holder_name": "A",
                                 "previous_value": 1, "new_value": 2, "detail": ""}])
    active = compute_active_beats(
        records_payload_json=records_json,
        hof_payload_json=None,
        retirement_rows=[{"player_id": "p1"}],
    )
    # records_ratified comes before retirements in the full sequence
    assert active.index("records_ratified") < active.index("retirements")
    # schedule_reveal is always last
    assert active[-1] == "schedule_reveal"


def test_initialize_manager_offseason_stores_active_beats():
    """After init, offseason_active_beats_json is stored and well-formed."""
    conn = _career_conn()
    season_id = conn.execute(
        "SELECT value FROM dynasty_state WHERE key = 'active_season_id'"
    ).fetchone()["value"]
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    raw = get_state(conn, "offseason_active_beats_json")
    assert raw is not None, "offseason_active_beats_json not stored"
    active = json.loads(raw)
    assert isinstance(active, list)
    assert len(active) > 0
    assert "schedule_reveal" in active
    assert active[-1] == "schedule_reveal"
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_offseason_ceremony.py::test_compute_active_beats_always_includes_core -v
```

Expected: `ImportError` or `AttributeError` — `compute_active_beats` not defined yet.

- [ ] **Step 3: Implement `compute_active_beats` in `offseason_ceremony.py`**

Add this function after the `OFFSEASON_CEREMONY_BEATS` constant (around line 67):

```python
def compute_active_beats(
    records_payload_json: Optional[str],
    hof_payload_json: Optional[str],
    retirement_rows: List[Dict[str, Any]],
) -> List[str]:
    """Return the ordered subset of OFFSEASON_CEREMONY_BEATS that have real content."""
    _CONDITIONAL = {
        "records_ratified": lambda: bool(
            _parse_json_list(records_payload_json)
        ),
        "hof_induction": lambda: bool(
            _parse_json_list(hof_payload_json)
        ),
        "retirements": lambda: bool(retirement_rows),
    }
    return [
        beat for beat in OFFSEASON_CEREMONY_BEATS
        if beat not in _CONDITIONAL or _CONDITIONAL[beat]()
    ]


def _parse_json_list(raw: Optional[str]) -> list:
    try:
        parsed = json.loads(raw or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []
```

Also add `compute_active_beats` to the `__all__` list at the bottom of `offseason_ceremony.py`.

- [ ] **Step 4: Wire `compute_active_beats` into `initialize_manager_offseason`**

At the end of `initialize_manager_offseason`, just before `set_state(conn, "offseason_initialized_for", season.season_id)`, add:

```python
    # Compute and store the active beat list for this offseason
    active_beats = compute_active_beats(
        records_payload_json=get_state(conn, "offseason_records_json"),
        hof_payload_json=get_state(conn, "offseason_hof_json"),
        retirement_rows=retirement_rows,
    )
    set_state(conn, "offseason_active_beats_json", json.dumps(active_beats))
```

- [ ] **Step 5: Run tests**

```
python -m pytest tests/test_offseason_ceremony.py -k "active_beats or initialize_manager_offseason_stores" -v
```

Expected: all PASS.

- [ ] **Step 6: Run full suite to check no regressions**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/dodgeball_sim/offseason_ceremony.py tests/test_offseason_ceremony.py
git commit -m "feat: compute and store active beat list at offseason init"
```

---

### Task 3: Add `load_active_beats()` and update `build_beat_response`

**Files:**
- Modify: `src/dodgeball_sim/offseason_presentation.py`

- [ ] **Step 1: Add `load_active_beats` helper and update imports**

At the top of `offseason_presentation.py`, update the import from `offseason_ceremony` to include `compute_active_beats`:

```python
from .offseason_ceremony import (
    OFFSEASON_CEREMONY_BEATS,
    build_offseason_ceremony_beat,
    clamp_offseason_beat_index,
    compute_active_beats,
    create_next_manager_season,
    stored_root_seed,
)
```

Remove `SCHEDULE_REVEAL_INDEX` from the module-level constant (it will no longer be used as a fixed index). Delete this line:

```python
SCHEDULE_REVEAL_INDEX = OFFSEASON_CEREMONY_BEATS.index("schedule_reveal")
```

Add this helper immediately after the imports:

```python
def load_active_beats(conn: sqlite3.Connection) -> list:
    """Load the stored active beat list, falling back to the full sequence."""
    raw = get_state(conn, "offseason_active_beats_json")
    if raw:
        try:
            beats = json.loads(raw)
            if beats and isinstance(beats, list):
                return beats
        except (TypeError, ValueError):
            pass
    return list(OFFSEASON_CEREMONY_BEATS)
```

- [ ] **Step 2: Rewrite `build_beat_response` to use active beats**

Replace the current `build_beat_response` function body with:

```python
def build_beat_response(conn: sqlite3.Connection, cursor) -> dict[str, Any]:
    active_beats = load_active_beats(conn)
    beat_index = max(0, min(int(cursor.offseason_beat_index or 0), len(active_beats) - 1))
    beat_key = active_beats[beat_index]
    is_last = beat_key == "schedule_reveal"
    is_recruitment = beat_key == "recruitment"

    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id) if season_id else None
    clubs = load_all_clubs(conn)
    rosters = load_all_rosters(conn)
    standings = load_standings(conn, season_id) if season_id else []
    awards = load_awards(conn, season_id) if season_id else []
    season_outcome = load_season_outcome(conn, season_id) if season_id else None
    signed_player_id = get_state(conn, "offseason_draft_signed_player_id") or ""

    next_preview: Any = None
    if beat_key == "schedule_reveal":
        season_number = cursor.season_number or 1
        root_seed = stored_root_seed(conn)
        next_preview = create_next_manager_season(
            clubs,
            root_seed,
            season_number + 1,
            (season.year + 1) if season else 2026,
        )

    dev_rows = _load_json_list(conn, "offseason_development_json")
    ret_rows = _load_json_list(conn, "offseason_retirements_json")
    records_json = get_state(conn, "offseason_records_json")
    hof_json = get_state(conn, "offseason_hof_json")
    rookie_preview_json = get_state(conn, "offseason_rookie_preview_payload_json")
    player_club_id = get_state(conn, "player_club_id") or ""

    beat = build_offseason_ceremony_beat(
        beat_index=beat_index,
        season=season,
        clubs=clubs,
        rosters=rosters,
        standings=standings,
        awards=awards,
        player_club_id=player_club_id,
        next_season=next_preview,
        development_rows=dev_rows,
        retirement_rows=ret_rows,
        draft_pool=load_free_agents(conn),
        signed_player_id=signed_player_id,
        season_outcome=season_outcome,
        records_payload_json=records_json,
        hof_payload_json=hof_json,
        rookie_preview_payload_json=rookie_preview_json,
    )
    payload = build_beat_payload(
        beat_key,
        awards=awards,
        clubs=clubs,
        rosters=rosters,
        standings=standings,
        ret_rows=ret_rows,
        season=season,
        season_outcome=season_outcome,
        next_preview=next_preview,
        signed_player_id=signed_player_id,
        dev_rows=dev_rows,
        player_club_id=player_club_id,
        rookie_preview_json=rookie_preview_json,
        conn=conn,
    )

    return {
        "beat_index": beat_index,
        "total_beats": len(active_beats),
        "key": beat_key,
        "title": beat.title,
        "body": beat.body,
        "state": cursor.state.value,
        "can_advance": (
            (
                cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
                and not is_last
                and not is_recruitment
            )
            or (cursor.state == CareerState.NEXT_SEASON_READY and not is_last)
        ),
        "can_recruit": (
            cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING
            and not signed_player_id
        ),
        "can_begin_season": cursor.state == CareerState.NEXT_SEASON_READY,
        "signed_player_id": signed_player_id,
        "payload": payload,
    }
```

- [ ] **Step 3: Update `build_beat_payload` signature to accept new parameters**

Add three keyword arguments to `build_beat_payload` (with defaults so no call sites break):

```python
def build_beat_payload(
    beat_key: str,
    *,
    awards: list,
    clubs: dict,
    rosters: dict,
    standings: list,
    ret_rows: list,
    season: Any,
    season_outcome: Any,
    next_preview: Any,
    signed_player_id: str,
    dev_rows: list = [],
    player_club_id: str = "",
    rookie_preview_json: Optional[str] = None,
    conn: sqlite3.Connection,
) -> dict:
```

Add `Optional` to the imports at the top of the file:
```python
from typing import Any, Optional
```

- [ ] **Step 4: Add `load_active_beats` to exports**

`load_active_beats` needs to be importable from `offseason_service.py`. It is a module-level function, so no explicit `__all__` change needed. Just verify `offseason_service.py` can import it after this task (done in Task 4).

- [ ] **Step 5: Run the full Python test suite**

```
python -m pytest -q
```

Expected: all pass. The `SCHEDULE_REVEAL_INDEX` removal may break `offseason_service.py`'s import — that's expected and will be fixed in Task 4.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/offseason_presentation.py
git commit -m "feat: load_active_beats helper + build_beat_response uses active beat list"
```

---

### Task 4: Update offseason_service.py to use active beats

**Files:**
- Modify: `src/dodgeball_sim/offseason_service.py`

- [ ] **Step 1: Update imports**

In `offseason_service.py`, change the import block:

```python
from .offseason_ceremony import (
    OFFSEASON_CEREMONY_BEATS,
    begin_next_season,
    clamp_offseason_beat_index,
    finalize_season,
    initialize_manager_offseason,
    sign_best_rookie,
    stored_root_seed,
)
from .offseason_presentation import build_beat_response, load_active_beats
```

Remove the `SCHEDULE_REVEAL_INDEX` import:
```python
# DELETE this line:
from .offseason_presentation import SCHEDULE_REVEAL_INDEX, build_beat_response
```

- [ ] **Step 2: Rewrite `advance_offseason_beat_payload`**

Replace the current function body:

```python
def advance_offseason_beat_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = _require_offseason_cursor(conn)
    active_beats = load_active_beats(conn)
    beat_index = max(0, min(int(cursor.offseason_beat_index or 0), len(active_beats) - 1))
    current_key = active_beats[beat_index]

    if current_key == "schedule_reveal":
        raise OffseasonError(
            "Already at the final beat. Use begin-season to start next season.",
            status_code=409,
        )
    if (
        cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
        and current_key == "recruitment"
    ):
        raise OffseasonError(
            "Cannot advance past recruitment without signing. Use /api/offseason/recruit first.",
            status_code=409,
        )

    next_index = beat_index + 1
    next_key = active_beats[next_index]
    if next_key == "recruitment":
        cursor = state_advance(
            cursor,
            CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            offseason_beat_index=next_index,
        )
    else:
        cursor = dataclasses.replace(cursor, offseason_beat_index=next_index)

    save_career_state_cursor(conn, cursor)
    conn.commit()
    return build_beat_response(conn, cursor)
```

- [ ] **Step 3: Update `recruit_offseason_payload` to use active beats index**

Replace the hardcoded `OFFSEASON_CEREMONY_BEATS.index("recruitment")` lookup:

```python
def recruit_offseason_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING:
        raise OffseasonError(
            f"Not in recruitment state (current: {cursor.state.value})", status_code=409
        )
    signed_player_id = get_state(conn, "offseason_draft_signed_player_id") or ""
    if signed_player_id:
        raise OffseasonError("Already recruited a player this offseason.", status_code=409)
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise OffseasonError("No player club assigned")

    signed = sign_best_rookie(conn, player_club_id, cursor.season_number or 1)

    active_beats = load_active_beats(conn)
    recruitment_index = active_beats.index("recruitment")
    cursor = state_advance(
        cursor,
        CareerState.NEXT_SEASON_READY,
        offseason_beat_index=recruitment_index,
    )
    save_career_state_cursor(conn, cursor)
    conn.commit()
    return {
        **build_beat_response(conn, cursor),
        "signed_player": (
            {
                "id": signed.id,
                "name": signed.name,
                "overall": round(signed.overall(), 1),
                "age": signed.age,
            }
            if signed
            else None
        ),
    }
```

- [ ] **Step 4: Remove now-unused imports from `offseason_service.py`**

Remove `OFFSEASON_CEREMONY_BEATS` and `clamp_offseason_beat_index` from the `offseason_ceremony` import if they are no longer used directly. Keep `stored_root_seed` only if it appears elsewhere in the file. Check each symbol.

- [ ] **Step 5: Run full test suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/offseason_service.py
git commit -m "feat: offseason_service uses load_active_beats instead of fixed-index constants"
```

---

### Task 5: Awards payload — season stats, award name, prestige sort

**Files:**
- Modify: `src/dodgeball_sim/offseason_presentation.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_offseason_ceremony.py`:

```python
from dodgeball_sim.offseason_presentation import build_beat_payload
from dodgeball_sim.awards import SeasonAward
from dodgeball_sim.stats import PlayerMatchStats


def _make_award(award_type, player_id, club_id="team_a"):
    return SeasonAward(
        season_id="s1",
        award_type=award_type,
        player_id=player_id,
        club_id=club_id,
        award_score=1.0,
    )


def test_awards_payload_has_season_stat_fields(tmp_path):
    import sqlite3
    from dodgeball_sim.persistence import create_schema, save_awards
    from dodgeball_sim.persistence import fetch_season_player_stats

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.commit()

    awards_list = [_make_award("mvp", "p1"), _make_award("best_thrower", "p1")]
    save_awards(conn, awards_list)

    # Insert a player_season_stats row so fetch_season_player_stats returns something
    conn.execute(
        """INSERT OR IGNORE INTO player_season_stats
           (season_id, player_id, club_id, matches,
            total_eliminations, eliminations_by_throw, catches_made,
            total_catches_made, total_dodges_successful, times_eliminated)
           VALUES ('s1','p1','team_a',5, 12, 8, 4, 4, 6, 2)"""
    )
    conn.commit()

    payload = build_beat_payload(
        "awards",
        awards=awards_list,
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )

    assert "awards" in payload
    first = payload["awards"][0]
    assert "award_name" in first, "award_name missing"
    assert "season_stat" in first, "season_stat missing"
    assert "season_stat_label" in first, "season_stat_label missing"
    assert "career_stat" in first, "career_stat missing"
    # career_elims renamed to career_stat
    assert "career_elims" not in first


def test_awards_payload_prestige_sort_mvp_first(tmp_path):
    awards_list = [
        _make_award("best_newcomer", "p1"),
        _make_award("best_catcher", "p2"),
        _make_award("best_thrower", "p3"),
        _make_award("mvp", "p4"),
    ]
    import sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    payload = build_beat_payload(
        "awards",
        awards=awards_list,
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )

    types = [a["award_type"] for a in payload["awards"]]
    assert types[0] == "mvp", f"Expected mvp first, got {types}"
    assert types[-1] == "best_newcomer", f"Expected best_newcomer last, got {types}"
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_offseason_ceremony.py::test_awards_payload_has_season_stat_fields -v
```

Expected: `KeyError` or `AssertionError` — fields don't exist yet.

- [ ] **Step 3: Update the `awards` case in `build_beat_payload`**

Add these imports at the top of `offseason_presentation.py`:

```python
from .persistence import fetch_season_player_stats
from .stats import PlayerMatchStats
```

Replace the entire `if beat_key == "awards":` block:

```python
    if beat_key == "awards":
        _AWARD_PRESTIGE = {
            "mvp": 3,
            "best_thrower": 2,
            "best_catcher": 1,
            "best_newcomer": 0,
        }
        _AWARD_NAME = {
            "mvp": "MVP",
            "best_thrower": "Best Thrower",
            "best_catcher": "Best Catcher",
            "best_newcomer": "Best Newcomer",
        }
        sorted_awards = sorted(
            awards,
            key=lambda a: _AWARD_PRESTIGE.get(a.award_type, -1),
            reverse=True,
        )
        season_stats: dict = {}
        if season is not None:
            season_stats = fetch_season_player_stats(conn, season.season_id)

        result = []
        for award in sorted_awards:
            player = find_player(award.player_id)
            career = load_player_career_stats(conn, award.player_id)
            stats = season_stats.get(award.player_id, PlayerMatchStats())
            if award.award_type == "best_thrower":
                season_stat = stats.eliminations_by_throw
                season_stat_label = f"{season_stat} throw elims"
            elif award.award_type == "best_catcher":
                season_stat = stats.catches_made
                season_stat_label = f"{season_stat} catches"
            else:  # mvp, best_newcomer
                season_stat = stats.eliminations_by_throw + stats.catches_made
                season_stat_label = f"{season_stat} season elims"
            result.append(
                {
                    "player_name": player.name if player else award.player_id,
                    "club_name": club_name(award.club_id),
                    "award_type": award.award_type,
                    "award_name": _AWARD_NAME.get(
                        award.award_type,
                        award.award_type.replace("_", " ").title(),
                    ),
                    "season_stat": int(season_stat),
                    "season_stat_label": season_stat_label,
                    "career_stat": int((career or {}).get("total_eliminations", 0)),
                    "ovr": int(round(player.overall())) if player else 0,
                }
            )
        return {"awards": result}
```

- [ ] **Step 4: Run tests**

```
python -m pytest tests/test_offseason_ceremony.py::test_awards_payload_has_season_stat_fields tests/test_offseason_ceremony.py::test_awards_payload_prestige_sort_mvp_first -v
```

Expected: both PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/offseason_presentation.py tests/test_offseason_ceremony.py
git commit -m "feat: awards payload adds award_name, season stats, and MVP-first sort"
```

---

### Task 6: Development payload — player-club-only structured data

**Files:**
- Modify: `src/dodgeball_sim/offseason_presentation.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_offseason_ceremony.py`:

```python
def test_development_payload_player_club_only():
    import sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    dev_rows = [
        {"player_id": "p1", "player_name": "Alice", "club_id": "my_club",
         "before": 65.4, "after": 67.2, "delta": 1.8},
        {"player_id": "p2", "player_name": "Bob",   "club_id": "other_club",
         "before": 70.1, "after": 71.5, "delta": 1.4},
        {"player_id": "p3", "player_name": "Carol",  "club_id": "my_club",
         "before": 58.9, "after": 60.0, "delta": 1.1},
    ]

    payload = build_beat_payload(
        "development",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        dev_rows=dev_rows,
        player_club_id="my_club",
        conn=conn,
    )

    assert "players" in payload
    names = [p["name"] for p in payload["players"]]
    assert "Alice" in names
    assert "Carol" in names
    assert "Bob" not in names, "Other club player should not appear"


def test_development_payload_no_decimals():
    import sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    dev_rows = [
        {"player_id": "p1", "player_name": "Alice", "club_id": "my_club",
         "before": 65.4, "after": 67.2, "delta": 1.8},
    ]

    payload = build_beat_payload(
        "development",
        awards=[], clubs={}, rosters={}, standings=[], ret_rows=[],
        season=None, season_outcome=None, next_preview=None,
        signed_player_id="", dev_rows=dev_rows, player_club_id="my_club",
        conn=conn,
    )

    player = payload["players"][0]
    assert isinstance(player["ovr_before"], int), "ovr_before must be int"
    assert isinstance(player["ovr_after"], int), "ovr_after must be int"
    assert isinstance(player["delta"], int), "delta must be int"
    assert player["ovr_before"] == 65
    assert player["ovr_after"] == 67
    assert player["delta"] == 2  # round(1.8) == 2
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_offseason_ceremony.py::test_development_payload_player_club_only -v
```

Expected: `AssertionError` — `players` key not in payload (returns `{}`).

- [ ] **Step 3: Add `development` case to `build_beat_payload`**

Add this block after the `retirements` case (before `if beat_key == "rookie_class_preview":`):

```python
    if beat_key == "development":
        player_rows = [
            row for row in dev_rows if row.get("club_id") == player_club_id
        ]
        player_rows_sorted = sorted(
            player_rows, key=lambda r: -abs(float(r.get("delta", 0)))
        )
        players = [
            {
                "name": row.get("player_name", row.get("player_id", "")),
                "ovr_before": int(round(float(row.get("before", 0)))),
                "ovr_after": int(round(float(row.get("after", 0)))),
                "delta": int(round(float(row.get("delta", 0)))),
            }
            for row in player_rows_sorted
        ]
        return {"players": players}
```

- [ ] **Step 4: Run tests**

```
python -m pytest tests/test_offseason_ceremony.py::test_development_payload_player_club_only tests/test_offseason_ceremony.py::test_development_payload_no_decimals -v
```

Expected: both PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/offseason_presentation.py tests/test_offseason_ceremony.py
git commit -m "feat: development payload returns player-club-only rows as integers"
```

---

### Task 7: Rookie class preview structured payload

**Files:**
- Modify: `src/dodgeball_sim/offseason_presentation.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_offseason_ceremony.py`:

```python
def test_rookie_class_preview_payload_structured():
    import json, sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    rookie_json = json.dumps({
        "class_size": 14,
        "top_band_depth": 3,
        "free_agent_count": 6,
        "archetype_distribution": {"thrower": 8, "catcher": 6},
        "storylines": [
            {"sentence": "A blue-chip thrower leads this class."},
            {"sentence": "Defensive depth is thin this year."},
        ],
        "source": "prospect_pool",
    })

    payload = build_beat_payload(
        "rookie_class_preview",
        awards=[], clubs={}, rosters={}, standings=[], ret_rows=[],
        season=None, season_outcome=None, next_preview=None,
        signed_player_id="", rookie_preview_json=rookie_json,
        conn=conn,
    )

    assert payload["class_size"] == 14
    assert payload["top_prospects"] == 3
    assert payload["free_agents"] == 6
    assert len(payload["archetypes"]) == 2
    assert payload["archetypes"][0]["name"] == "thrower"  # sorted by count desc
    assert len(payload["storylines"]) == 2
    assert payload["storylines"][0] == "A blue-chip thrower leads this class."
```

- [ ] **Step 2: Run to confirm failure**

```
python -m pytest tests/test_offseason_ceremony.py::test_rookie_class_preview_payload_structured -v
```

Expected: `KeyError` — `class_size` not in empty dict `{}`.

- [ ] **Step 3: Add `rookie_class_preview` case to `build_beat_payload`**

Add this block (before the final `return {}`):

```python
    if beat_key == "rookie_class_preview":
        try:
            payload_dict = json.loads(rookie_preview_json or "{}") or {}
        except (TypeError, ValueError):
            payload_dict = {}
        archetype_dist: dict = payload_dict.get("archetype_distribution", {}) or {}
        storylines = [
            s.get("sentence", "")
            for s in (payload_dict.get("storylines", []) or [])
            if s.get("sentence")
        ]
        return {
            "class_size": int(payload_dict.get("class_size", 0)),
            "top_prospects": int(payload_dict.get("top_band_depth", 0)),
            "free_agents": int(payload_dict.get("free_agent_count", 0)),
            "archetypes": sorted(
                [{"name": k, "count": v} for k, v in archetype_dist.items()],
                key=lambda x: (-x["count"], x["name"]),
            ),
            "storylines": storylines,
        }
```

Also add `import json` if it's not already at the top of `offseason_presentation.py` (check the imports).

- [ ] **Step 4: Run tests**

```
python -m pytest tests/test_offseason_ceremony.py::test_rookie_class_preview_payload_structured -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/dodgeball_sim/offseason_presentation.py tests/test_offseason_ceremony.py
git commit -m "feat: rookie class preview returns structured payload instead of empty dict"
```

---

### Task 8: Fix champion body copy + rookie preview body copy

**Files:**
- Modify: `src/dodgeball_sim/offseason_ceremony.py`

- [ ] **Step 1: Fix champion body copy**

In `build_offseason_ceremony_beat`, find the `if key == "champion":` block. Remove the `"Champion source: Playoff Final"` line. The body string is used as a fallback only (the new `ChampionReveal` component uses the structured payload). Change the lines list to:

```python
        if season_outcome is not None:
            lines = [f"Champion: {club_name(season_outcome.champion_club_id)}"]
            if season_outcome.runner_up_club_id:
                lines.append(f"Runner-up: {club_name(season_outcome.runner_up_club_id)}")
            body = "\n".join(lines)
        elif not ordered_standings:
            body = "No completed standings are available for this season."
        else:
            champion = ordered_standings[0]
            body = f"Champion: {club_name(champion.club_id)}"
```

- [ ] **Step 2: Fix rookie class preview body copy**

In `build_offseason_ceremony_beat`, find the `if key == "rookie_class_preview":` block. Replace the body construction logic:

```python
        if class_size == 0 and free_agent_count == 0:
            body = "No incoming class data is available yet."
        else:
            lines = [f"Incoming class: {class_size} rookies"]
            lines.append(f"Top prospects (70+ OVR): {top_band_depth}")
            lines.append(f"Veteran free agents available: {free_agent_count}")
            if archetype_distribution:
                ordered = sorted(
                    archetype_distribution.items(), key=lambda item: (-item[1], item[0])
                )
                lines.append(
                    "Archetypes: " + ", ".join(f"{name} {count}" for name, count in ordered)
                )
            if storylines:
                lines.append("")
                lines.append("Market storylines:")
                for storyline in storylines:
                    sentence = storyline.get("sentence", "")
                    if sentence:
                        lines.append(f"  - {sentence}")
            body = "\n".join(lines)
        # Note: "Continue to Recruitment Day." line is intentionally omitted
```

- [ ] **Step 3: Run full test suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/dodgeball_sim/offseason_ceremony.py
git commit -m "fix: remove 'Champion source' jargon and 'Continue to Recruitment Day' from body copy"
```

---

### Task 9: TypeScript types

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Update `OffseasonAward` interface**

Find and replace the `OffseasonAward` interface (around line 361):

```typescript
export interface OffseasonAward {
    player_name: string;
    club_name: string;
    award_type: string;
    award_name: string;
    season_stat: number;
    season_stat_label: string;
    career_stat: number;
    ovr: number;
}
```

- [ ] **Step 2: Add `DevelopmentBeatPayload` and `RookieClassPreviewBeatPayload`**

After `RecapBeatPayload`, add:

```typescript
export interface DevelopmentPlayer {
    name: string;
    ovr_before: number;
    ovr_after: number;
    delta: number;
}

export interface DevelopmentBeatPayload {
    players: DevelopmentPlayer[];
}

export interface RookieClassPreviewBeatPayload {
    class_size: number;
    top_prospects: number;
    free_agents: number;
    archetypes: Array<{ name: string; count: number }>;
    storylines: string[];
}
```

- [ ] **Step 3: Update `OffseasonBeat` discriminated union**

Replace the `development` and `rookie_class_preview` lines in the union:

```typescript
export type OffseasonBeat =
    | (OffseasonBeatBase & { key: 'champion'; payload: ChampionBeatPayload })
    | (OffseasonBeatBase & { key: 'recap'; payload: RecapBeatPayload })
    | (OffseasonBeatBase & { key: 'awards'; payload: AwardsBeatPayload })
    | (OffseasonBeatBase & { key: 'records_ratified'; payload: EmptyBeatPayload })
    | (OffseasonBeatBase & { key: 'hof_induction'; payload: EmptyBeatPayload })
    | (OffseasonBeatBase & { key: 'development'; payload: DevelopmentBeatPayload })
    | (OffseasonBeatBase & { key: 'retirements'; payload: RetirementsBeatPayload })
    | (OffseasonBeatBase & { key: 'rookie_class_preview'; payload: RookieClassPreviewBeatPayload })
    | (OffseasonBeatBase & { key: 'recruitment'; payload: RecruitmentBeatPayload })
    | (OffseasonBeatBase & { key: 'schedule_reveal'; payload: ScheduleRevealBeatPayload });
```

- [ ] **Step 4: Run TypeScript check**

```
cd frontend && npm run build 2>&1 | head -40
```

Expected: either clean build or only errors in files not yet updated (Ceremonies.tsx will error on `career_elims` — that's fixed in Task 14).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts
git commit -m "types: update OffseasonAward, add DevelopmentBeatPayload and RookieClassPreviewBeatPayload"
```

---

### Task 10: ChampionReveal component

**Files:**
- Create: `frontend/src/components/ceremonies/ChampionReveal.tsx`

- [ ] **Step 1: Create the component**

```typescript
import type { OffseasonBeat } from '../../types';

type ChampionBeat = Extract<OffseasonBeat, { key: 'champion' }>;

export function ChampionReveal({
    beat,
    onComplete,
    acting,
}: {
    beat: ChampionBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const champion = beat.payload.champion;

    return (
        <section className="command-offseason-shell" data-testid="offseason-champion">
            <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    SEASON CHAMPION
                </p>
                {champion ? (
                    <>
                        <h2
                            style={{
                                fontSize: '2rem',
                                fontWeight: 800,
                                color: '#fbbf24',
                                marginBottom: '1rem',
                                lineHeight: 1.2,
                            }}
                        >
                            {champion.club_name}
                        </h2>
                        <div
                            style={{
                                display: 'flex',
                                gap: '1.5rem',
                                justifyContent: 'center',
                                flexWrap: 'wrap',
                                marginBottom: '1.5rem',
                            }}
                        >
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#e2e8f0' }}>
                                    {champion.wins}-{champion.losses}-{champion.draws}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Record</div>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#fbbf24' }}>
                                    {champion.title_count}
                                </div>
                                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                                    {champion.title_count === 1 ? 'Title' : 'Titles'}
                                </div>
                            </div>
                        </div>
                    </>
                ) : (
                    <p style={{ color: '#94a3b8', fontSize: '1rem', marginBottom: '1.5rem' }}>
                        {typeof beat.body === 'string' ? beat.body : 'No champion determined this season.'}
                    </p>
                )}
            </div>

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to the next offseason beat.</p>
                </div>
                <div className="command-action-buttons">
                    <button
                        className="dm-btn dm-btn-primary"
                        onClick={onComplete}
                        disabled={acting}
                    >
                        {acting ? 'Continuing...' : 'Continue'}
                    </button>
                </div>
            </div>
        </section>
    );
}
```

- [ ] **Step 2: Build to verify no type errors**

```
cd frontend && npm run build 2>&1 | grep -i "ChampionReveal\|error" | head -20
```

Expected: no errors referencing `ChampionReveal.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/ChampionReveal.tsx
git commit -m "feat: ChampionReveal component for champion offseason beat"
```

---

### Task 11: RecapStandings component

**Files:**
- Create: `frontend/src/components/ceremonies/RecapStandings.tsx`

- [ ] **Step 1: Create the component**

```typescript
import type { OffseasonBeat } from '../../types';

type RecapBeat = Extract<OffseasonBeat, { key: 'recap' }>;

export function RecapStandings({
    beat,
    onComplete,
    acting,
}: {
    beat: RecapBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const standings = beat.payload.standings;

    return (
        <section className="command-offseason-shell" data-testid="offseason-recap">
            <div style={{ padding: '1.5rem 1rem 0.5rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    FINAL STANDINGS
                </p>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '1rem' }}>
                    Season Table
                </h2>
            </div>

            <div className="dm-panel" style={{ padding: '0', overflow: 'hidden' }}>
                {/* Header row */}
                <div
                    style={{
                        display: 'grid',
                        gridTemplateColumns: '2rem 1fr 6rem 3.5rem 4rem',
                        gap: '0 0.75rem',
                        padding: '0.5rem 1rem',
                        borderBottom: '1px solid #1e293b',
                        fontSize: '0.65rem',
                        color: '#475569',
                        letterSpacing: '0.06em',
                    }}
                >
                    <span>#</span>
                    <span>Club</span>
                    <span style={{ textAlign: 'center' }}>W-L-D</span>
                    <span style={{ textAlign: 'right' }}>Pts</span>
                    <span style={{ textAlign: 'right' }}>Diff</span>
                </div>

                {standings.map((row) => (
                    <div
                        key={row.rank}
                        style={{
                            display: 'grid',
                            gridTemplateColumns: '2rem 1fr 6rem 3.5rem 4rem',
                            gap: '0 0.75rem',
                            padding: '0.6rem 1rem',
                            borderLeft: row.is_player_club ? '3px solid #f97316' : '3px solid transparent',
                            borderBottom: '1px solid #0f172a',
                            background: row.is_player_club ? '#1c1009' : 'transparent',
                            color: row.is_player_club ? '#fb923c' : '#94a3b8',
                            fontSize: '0.85rem',
                            alignItems: 'center',
                        }}
                    >
                        <span style={{ color: '#475569', fontSize: '0.75rem' }}>{row.rank}</span>
                        <span style={{ fontWeight: row.is_player_club ? 700 : 400, color: row.is_player_club ? '#fb923c' : '#e2e8f0' }}>
                            {row.club_name}
                        </span>
                        <span style={{ textAlign: 'center', color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>
                            {row.wins}-{row.losses}-{row.draws}
                        </span>
                        <span style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums', color: '#e2e8f0' }}>
                            {row.points}
                        </span>
                        <span
                            style={{
                                textAlign: 'right',
                                fontVariantNumeric: 'tabular-nums',
                                color: row.points > 0 ? '#10b981' : row.points < 0 ? '#ef4444' : '#64748b',
                            }}
                        >
                            {row.points > 0 ? '+' : ''}{row.points}
                        </span>
                    </div>
                ))}
            </div>

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to the next offseason beat.</p>
                </div>
                <div className="command-action-buttons">
                    <button
                        className="dm-btn dm-btn-primary"
                        onClick={onComplete}
                        disabled={acting}
                    >
                        {acting ? 'Continuing...' : 'Continue'}
                    </button>
                </div>
            </div>
        </section>
    );
}
```

Note: The `Diff` column in the standings table should display `row.points` — actually it should display the elimination differential. Check: the `RecapBeatPayload` in `types.ts` has no `diff` or `elimination_differential` field. Look at `build_beat_payload` for `recap` in `offseason_presentation.py`:

```python
{
    "rank": index + 1,
    "club_name": club_name(row.club_id),
    "wins": row.wins,
    "losses": row.losses,
    "draws": row.draws,
    "points": row.points,
    "is_player_club": row.club_id == player_club_id,
}
```

`elimination_differential` is not in the payload yet. Add it to `build_beat_payload` for `recap`:

In `offseason_presentation.py`, in the `if beat_key == "recap":` block, add `"diff": row.elimination_differential` to each standings dict. Then update `RecapBeatPayload` in `types.ts` to include `diff: number`.

- [ ] **Step 2: Add `diff` to recap payload in `offseason_presentation.py`**

In `build_beat_payload`, the `recap` case, update each standings entry:

```python
        return {
            "standings": [
                {
                    "rank": index + 1,
                    "club_name": club_name(row.club_id),
                    "wins": row.wins,
                    "losses": row.losses,
                    "draws": row.draws,
                    "points": row.points,
                    "diff": row.elimination_differential,
                    "is_player_club": row.club_id == player_club_id,
                }
                for index, row in enumerate(standings)
            ]
        }
```

- [ ] **Step 3: Update `RecapBeatPayload` in `types.ts`**

```typescript
export interface RecapBeatPayload {
    standings: Array<{
        rank: number;
        club_name: string;
        wins: number;
        losses: number;
        draws: number;
        points: number;
        diff: number;
        is_player_club: boolean;
    }>;
}
```

- [ ] **Step 4: Update the Diff column in `RecapStandings.tsx` to use `row.diff`**

In the standings row, change the Diff `<span>` to:

```typescript
<span
    style={{
        textAlign: 'right',
        fontVariantNumeric: 'tabular-nums',
        color: row.diff > 0 ? '#10b981' : row.diff < 0 ? '#ef4444' : '#64748b',
    }}
>
    {row.diff > 0 ? '+' : ''}{row.diff}
</span>
```

- [ ] **Step 5: Build to verify no type errors**

```
cd frontend && npm run build 2>&1 | grep -i "error" | head -20
```

Expected: no new errors from `RecapStandings.tsx`.

- [ ] **Step 6: Run full Python test suite (recap payload change)**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ceremonies/RecapStandings.tsx frontend/src/types.ts src/dodgeball_sim/offseason_presentation.py
git commit -m "feat: RecapStandings component with proper table layout and diff column"
```

---

### Task 12: DevelopmentResults component

**Files:**
- Create: `frontend/src/components/ceremonies/DevelopmentResults.tsx`

- [ ] **Step 1: Create the component**

```typescript
import type { OffseasonBeat } from '../../types';

type DevelopmentBeat = Extract<OffseasonBeat, { key: 'development' }>;

export function DevelopmentResults({
    beat,
    onComplete,
    acting,
}: {
    beat: DevelopmentBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const players = beat.payload.players;

    return (
        <section className="command-offseason-shell" data-testid="offseason-development">
            <div style={{ padding: '1.5rem 1rem 0.5rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    OFFSEASON DEVELOPMENT
                </p>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.25rem' }}>
                    Your Roster Progress
                </h2>
                <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
                    {players.length} player{players.length !== 1 ? 's' : ''} on your roster
                </p>
            </div>

            <div className="dm-panel" style={{ padding: '0', overflow: 'hidden' }}>
                {players.length === 0 ? (
                    <p style={{ padding: '1rem', color: '#64748b', textAlign: 'center' }}>
                        No development data available for your roster.
                    </p>
                ) : (
                    players.map((player, i) => {
                        const improved = player.delta > 0;
                        const declined = player.delta < 0;
                        const deltaColor = improved ? '#10b981' : declined ? '#ef4444' : '#64748b';
                        const deltaLabel = player.delta > 0 ? `+${player.delta}` : `${player.delta}`;

                        return (
                            <div
                                key={i}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    padding: '0.65rem 1rem',
                                    borderBottom: '1px solid #0f172a',
                                    gap: '1rem',
                                }}
                            >
                                <span style={{ flex: 1, color: '#e2e8f0', fontSize: '0.9rem', fontWeight: 500 }}>
                                    {player.name}
                                </span>
                                <span style={{ color: '#64748b', fontSize: '0.8rem', fontVariantNumeric: 'tabular-nums' }}>
                                    {player.ovr_before} → {player.ovr_after}
                                </span>
                                <span
                                    style={{
                                        minWidth: '2.5rem',
                                        textAlign: 'right',
                                        fontWeight: 700,
                                        fontSize: '0.85rem',
                                        color: deltaColor,
                                        fontVariantNumeric: 'tabular-nums',
                                    }}
                                >
                                    {deltaLabel}
                                </span>
                            </div>
                        );
                    })
                )}
            </div>

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to the next offseason beat.</p>
                </div>
                <div className="command-action-buttons">
                    <button
                        className="dm-btn dm-btn-primary"
                        onClick={onComplete}
                        disabled={acting}
                    >
                        {acting ? 'Continuing...' : 'Continue'}
                    </button>
                </div>
            </div>
        </section>
    );
}
```

- [ ] **Step 2: Build to verify no type errors**

```
cd frontend && npm run build 2>&1 | grep -i "error" | head -20
```

Expected: no errors from `DevelopmentResults.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/DevelopmentResults.tsx
git commit -m "feat: DevelopmentResults component shows player-club roster progress"
```

---

### Task 13: RookieClassPreview component

**Files:**
- Create: `frontend/src/components/ceremonies/RookieClassPreview.tsx`

- [ ] **Step 1: Create the component**

```typescript
import type { OffseasonBeat } from '../../types';

type RookieClassPreviewBeat = Extract<OffseasonBeat, { key: 'rookie_class_preview' }>;

export function RookieClassPreview({
    beat,
    onComplete,
    acting,
}: {
    beat: RookieClassPreviewBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const { class_size, top_prospects, free_agents, archetypes, storylines } = beat.payload;

    return (
        <section className="command-offseason-shell" data-testid="offseason-rookie-preview">
            <div style={{ padding: '1.5rem 1rem 0.5rem' }}>
                <p style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    INCOMING CLASS
                </p>
                <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '1rem' }}>
                    Rookie Class Preview
                </h2>
            </div>

            <div className="dm-panel" style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', padding: '1rem' }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#e2e8f0' }}>{class_size}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Incoming Rookies</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#10b981' }}>{top_prospects}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Top Prospects (70+ OVR)</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2rem', fontWeight: 800, color: '#94a3b8' }}>{free_agents}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Veteran Free Agents</div>
                </div>
            </div>

            {archetypes.length > 0 && (
                <div className="dm-panel" style={{ padding: '0.75rem 1rem' }}>
                    <p className="dm-kicker">Archetype Breakdown</p>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                        {archetypes.map((a) => (
                            <span
                                key={a.name}
                                style={{
                                    background: '#1e293b',
                                    borderRadius: '4px',
                                    padding: '0.2rem 0.5rem',
                                    fontSize: '0.75rem',
                                    color: '#94a3b8',
                                }}
                            >
                                {a.name} ({a.count})
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {storylines.length > 0 && (
                <div className="dm-panel" style={{ padding: '0.75rem 1rem' }}>
                    <p className="dm-kicker">Market Storylines</p>
                    <ul style={{ margin: '0.5rem 0 0', padding: '0 0 0 1.1rem', color: '#94a3b8', fontSize: '0.85rem', lineHeight: 1.6 }}>
                        {storylines.map((s, i) => (
                            <li key={i}>{s}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to Signing Day.</p>
                </div>
                <div className="command-action-buttons">
                    <button
                        className="dm-btn dm-btn-primary"
                        onClick={onComplete}
                        disabled={acting}
                    >
                        {acting ? 'Continuing...' : 'Continue'}
                    </button>
                </div>
            </div>
        </section>
    );
}
```

- [ ] **Step 2: Build to verify no type errors**

```
cd frontend && npm run build 2>&1 | grep -i "error" | head -20
```

Expected: no errors from `RookieClassPreview.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/RookieClassPreview.tsx
git commit -m "feat: RookieClassPreview component with structured class data"
```

---

### Task 14: AwardsNight updates — icons, names, season stats, sort

**Files:**
- Modify: `frontend/src/components/ceremonies/Ceremonies.tsx`

- [ ] **Step 1: Fix `AWARD_ICON` and `AWARD_COLOR` maps**

Replace the constants at the top of `Ceremonies.tsx`:

```typescript
const AWARD_ICON: Record<string, string> = {
    mvp: '🏆',
    best_thrower: '🎯',
    best_catcher: '🤲',
    best_newcomer: '⚡',
};

const AWARD_COLOR: Record<string, string> = {
    mvp: '#f97316',
    best_thrower: '#3b82f6',
    best_catcher: '#10b981',
    best_newcomer: '#eab308',
};
```

- [ ] **Step 2: Update `AwardsNight` render to show award name, season stats, fix career field name, and pin highlight to index 0**

Replace the entire `AwardsNight` function:

```typescript
export function AwardsNight({ beat, onComplete, acting }: { beat: AwardsBeat; onComplete: () => void; acting?: boolean }) {
    const awards = beat.payload.awards;

    if (awards.length === 0) {
        return (
            <CeremonyShell
                title={beat.title}
                eyebrow="Awards"
                description="The league honors the season's finest."
                stages={1}
                renderStage={() => (
                    <div style={{ textAlign: 'center', color: '#94a3b8' }}>
                        {typeof beat.body === 'string' ? beat.body : 'No awards this season.'}
                    </div>
                )}
                onComplete={onComplete}
                isActing={acting}
            />
        );
    }

    return (
        <CeremonyShell
            title={beat.title}
            eyebrow="Awards Night"
            description="The league gathers to honor the season's best."
            stages={awards.length}
            renderStage={(stage) => (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '480px', margin: '0 auto' }}>
                    {awards.slice(0, stage).map((award: OffseasonAward, i: number) => {
                        const color = AWARD_COLOR[award.award_type] ?? '#f97316';
                        const icon = AWARD_ICON[award.award_type] ?? '🏅';
                        // MVP (index 0) is always highlighted; others dim as they appear
                        const isHighlighted = i === 0;
                        return (
                            <div
                                key={i}
                                className="fade-in"
                                style={{
                                    border: `1px solid ${isHighlighted ? color : '#334155'}`,
                                    borderRadius: '8px',
                                    padding: '1rem',
                                    background: isHighlighted ? `${color}11` : '#0f172a',
                                    opacity: isHighlighted ? 1 : 0.65,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '1rem',
                                }}
                            >
                                <span style={{ fontSize: '2rem' }}>{icon}</span>
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: '0.65rem', color: isHighlighted ? color : '#475569', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '0.2rem' }}>
                                        {award.award_name}
                                    </div>
                                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: isHighlighted ? color : '#e2e8f0' }}>
                                        {award.player_name}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.15rem' }}>
                                        {award.club_name} · {award.season_stat_label}
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: '#475569', marginTop: '0.1rem' }}>
                                        {award.career_stat} career elims{award.ovr ? ` · OVR ${award.ovr}` : ''}
                                    </div>
                                </div>
                                {!isHighlighted && i < stage - 1 && <span style={{ color: '#475569' }}>✓</span>}
                            </div>
                        );
                    })}
                </div>
            )}
            onComplete={onComplete}
            isActing={acting}
        />
    );
}
```

- [ ] **Step 3: Build to verify no type errors**

```
cd frontend && npm run build 2>&1 | grep -i "error" | head -30
```

Expected: no errors. The `career_elims` reference is removed; `award_name`, `season_stat_label`, `career_stat` are the new fields, defined in `OffseasonAward` from Task 9.

- [ ] **Step 4: Run full Python test suite (no regressions)**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx
git commit -m "feat: AwardsNight shows award names, season stats, correct icons, MVP pinned at top"
```

---

### Task 15: NewSeasonEve schedule toggle

**Files:**
- Modify: `frontend/src/components/ceremonies/Ceremonies.tsx`

- [ ] **Step 1: Add toggle to `NewSeasonEve`**

Replace the entire `NewSeasonEve` function:

```typescript
export function NewSeasonEve({ beat, onComplete, acting }: { beat: ScheduleRevealBeat; onComplete: () => void; acting?: boolean }) {
    const fixtures = beat.payload.fixtures;
    const prediction: string = beat.payload.prediction;
    const seasonLabel: string = beat.payload.season_label;
    const [showAll, setShowAll] = useState(false);

    const playerFixtures = fixtures.filter((f: OffseasonFixture) => f.is_player_match);
    const displayedFixtures = showAll ? fixtures : playerFixtures;

    return (
        <CeremonyShell
            title={beat.title}
            eyebrow={seasonLabel ? `Season ${seasonLabel}` : 'New Season'}
            description="A new chapter begins."
            stages={2}
            renderStage={(stage) => (
                <div style={{ width: '100%', maxWidth: '520px', margin: '0 auto' }}>
                    {stage >= 1 && (
                        <div className="fade-in" style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                                    {showAll ? `All ${fixtures.length} matches` : `Your ${playerFixtures.length} match${playerFixtures.length !== 1 ? 'es' : ''}`}
                                </span>
                                {fixtures.length > playerFixtures.length && (
                                    <button
                                        onClick={() => setShowAll(!showAll)}
                                        style={{
                                            background: 'none',
                                            border: '1px solid #334155',
                                            borderRadius: '4px',
                                            padding: '0.2rem 0.5rem',
                                            color: '#64748b',
                                            fontSize: '0.7rem',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        {showAll ? 'My Games' : 'Full Schedule'}
                                    </button>
                                )}
                            </div>

                            {displayedFixtures.length === 0 ? (
                                <div style={{ color: '#94a3b8', textAlign: 'center' }}>
                                    {typeof beat.body === 'string' ? beat.body : 'Schedule not available.'}
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                                    {displayedFixtures.map((f: OffseasonFixture, i: number) => (
                                        <div
                                            key={i}
                                            style={{
                                                display: 'flex',
                                                gap: '0.5rem',
                                                alignItems: 'center',
                                                padding: '0.4rem 0.6rem',
                                                borderRadius: '4px',
                                                background: f.is_player_match ? '#1c1009' : 'transparent',
                                                border: f.is_player_match ? '1px solid #f97316' : '1px solid transparent',
                                            }}
                                        >
                                            <span style={{ color: '#475569', fontSize: '0.65rem', width: '3rem', flexShrink: 0 }}>
                                                Wk {f.week}
                                            </span>
                                            <span style={{ color: f.is_player_match ? '#fb923c' : '#94a3b8', fontSize: '0.8rem', flex: 1 }}>
                                                {f.home} vs {f.away}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {stage >= 2 && prediction && (
                        <div
                            className="fade-in"
                            style={{
                                borderLeft: '3px solid #f97316',
                                paddingLeft: '1rem',
                                color: '#cbd5e1',
                                fontSize: '0.9rem',
                                fontStyle: 'italic',
                                lineHeight: 1.5,
                            }}
                        >
                            {prediction}
                        </div>
                    )}
                </div>
            )}
            onComplete={onComplete}
            actionLabel="Start New Season"
            actionDescription="The offseason is complete. Start the next season when ready."
            isActing={acting}
        />
    );
}
```

Since `useState` is used, ensure the import at the top of `Ceremonies.tsx` includes it:

```typescript
import { useState } from 'react';
```

- [ ] **Step 2: Build to verify no type errors**

```
cd frontend && npm run build 2>&1 | grep -i "error" | head -20
```

Expected: clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx
git commit -m "feat: NewSeasonEve defaults to player games with Full Schedule toggle"
```

---

### Task 16: Offseason.tsx routing + final build check

**Files:**
- Modify: `frontend/src/components/Offseason.tsx`

- [ ] **Step 1: Update imports and routing**

Replace the contents of `Offseason.tsx`:

```typescript
import { useState } from 'react';
import { useApiResource } from '../hooks/useApiResource';
import type { OffseasonBeat } from '../types';
import { ActionButton, PageHeader, StatusMessage } from './ui';
import { AwardsNight, Graduation, SigningDay, NewSeasonEve } from './ceremonies/Ceremonies';
import { ChampionReveal } from './ceremonies/ChampionReveal';
import { RecapStandings } from './ceremonies/RecapStandings';
import { DevelopmentResults } from './ceremonies/DevelopmentResults';
import { RookieClassPreview } from './ceremonies/RookieClassPreview';

export function Offseason() {
    const { data: beat, error, loading, setData: setBeat, setError } = useApiResource<OffseasonBeat>('/api/offseason/beat');
    const [acting, setActing] = useState(false);

    const act = (endpoint: string, method = 'POST') => {
        setActing(true);
        setError(null);
        fetch(endpoint, { method })
            .then(res => {
                if (!res.ok) return res.json().then(d => Promise.reject(new Error(d.detail || 'Action failed')));
                return res.json();
            })
            .then(data => {
                if (data.state?.state === 'season_active_pre_match') {
                    window.location.reload();
                    return;
                }
                setBeat(data);
            })
            .catch(err => setError(err.message))
            .finally(() => setActing(false));
    };

    if (loading && !beat) {
        return <StatusMessage title="Loading offseason">Preparing the ceremony.</StatusMessage>;
    }
    if (error && !beat) {
        return <StatusMessage title="Offseason unavailable" tone="danger">{error}</StatusMessage>;
    }
    if (!beat) return null;

    const advance = () => act('/api/offseason/advance');
    const recruit = () => act('/api/offseason/recruit');
    const beginSeason = () => act('/api/offseason/begin-season');

    if (beat.key === 'champion') return <ChampionReveal beat={beat} onComplete={advance} acting={acting} />;
    if (beat.key === 'recap') return <RecapStandings beat={beat} onComplete={advance} acting={acting} />;
    if (beat.key === 'awards') return <AwardsNight beat={beat} onComplete={advance} acting={acting} />;
    if (beat.key === 'retirements') return <Graduation beat={beat} onComplete={advance} acting={acting} />;
    if (beat.key === 'development') return <DevelopmentResults beat={beat} onComplete={advance} acting={acting} />;
    if (beat.key === 'rookie_class_preview') return <RookieClassPreview beat={beat} onComplete={advance} acting={acting} />;
    if (beat.key === 'recruitment' && beat.can_recruit) return (
        <section className="command-offseason-shell" data-testid="offseason-recruitment-action">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
                title="Signing Day"
                description="Make the next roster move before the league finishes its commitments."
            />
            <div className="dm-panel command-offseason-feature">
                <p className="dm-kicker">Recruitment Desk</p>
                <h3>Best available rookie</h3>
                <p>
                    Your staff has narrowed the class. Sign the strongest available prospect, then review the rest of the league's commitments.
                </p>
            </div>
            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Next action</p>
                    <p>Recruitment must be resolved before the offseason ceremony can continue.</p>
                </div>
                <div className="command-action-buttons">
                    <ActionButton variant="primary" onClick={recruit} disabled={acting}>
                        {acting ? 'Signing...' : 'Sign Best Rookie'}
                    </ActionButton>
                </div>
            </div>
        </section>
    );
    if (beat.key === 'recruitment') return <SigningDay beat={beat} onComplete={advance} acting={acting} />;
    if (beat.key === 'schedule_reveal') return <NewSeasonEve beat={beat} onComplete={beginSeason} acting={acting} />;

    // Generic fallback for records_ratified, hof_induction, or any future beats
    const bodyLines = typeof beat.body === 'string'
        ? beat.body.split('\n').map((line: string) => line.trim()).filter(Boolean)
        : [];

    return (
        <section className="command-offseason-shell" data-testid="offseason-beat">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
                title={beat.title}
                description="Review the league update, then continue the offseason sequence."
                stats={
                    <div className="command-offseason-progress" aria-label="Offseason beat progress">
                        {Array.from({ length: beat.total_beats }).map((_, index) => (
                            <span
                                key={index}
                                className={index <= beat.beat_index ? 'command-offseason-progress-step command-offseason-progress-step-active' : 'command-offseason-progress-step'}
                            />
                        ))}
                    </div>
                }
            />
            <article className="dm-panel command-offseason-feature">
                <p className="dm-kicker">{beat.key.replaceAll('_', ' ')}</p>
                <h3>{beat.title}</h3>
                <div className="command-offseason-copy">
                    {bodyLines.length === 0 ? (
                        <p>No additional report details for this beat.</p>
                    ) : (
                        bodyLines.map((line: string, i: number) => <p key={`${line}-${i}`}>{line}</p>)
                    )}
                </div>
            </article>
            {(beat.can_advance || beat.can_begin_season) && (
                <div className="dm-panel command-action-bar">
                    <div>
                        <p className="dm-kicker">Ceremony Control</p>
                        <p>{beat.can_begin_season ? 'The offseason is complete. Start the next season when ready.' : 'Continue to the next offseason beat.'}</p>
                    </div>
                    <div className="command-action-buttons">
                        {beat.can_advance && (
                            <ActionButton variant="primary" onClick={advance} disabled={acting}>
                                {acting ? 'Continuing...' : 'Continue'}
                            </ActionButton>
                        )}
                        {beat.can_begin_season && (
                            <ActionButton variant="primary" onClick={beginSeason} disabled={acting}>
                                {acting ? 'Starting...' : 'Start New Season'}
                            </ActionButton>
                        )}
                    </div>
                </div>
            )}
        </section>
    );
}
```

- [ ] **Step 2: Final build — must be clean**

```
cd frontend && npm run build
```

Expected: exit 0, no TypeScript errors, no import errors.

- [ ] **Step 3: Run full Python test suite**

```
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Offseason.tsx
git commit -m "feat: route champion, recap, development, rookie_class_preview to custom components"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Dynamic active beat list stored at offseason init | Task 2 |
| `load_active_beats` fallback to full constant | Task 3 |
| `advance_offseason_beat_payload` uses active beats | Task 4 |
| `recruit_offseason_payload` uses active beats index | Task 4 |
| Awards dedup invariant test | Task 1 |
| Awards: season stats, award name, prestige sort (MVP first) | Tasks 5, 14 |
| Awards: fix AWARD_ICON/AWARD_COLOR keys | Task 14 |
| Development: player-club-only, no decimals | Tasks 6, 12 |
| Rookie class preview: structured payload, fixed copy | Tasks 7, 8, 13 |
| Champion: remove "Champion source" jargon | Task 8 |
| Champion: custom ChampionReveal component | Task 10 |
| Recap: custom RecapStandings component with diff column | Task 11 |
| RecapStandings: player club highlighted, no `pts=` | Task 11 |
| NewSeasonEve: default to player games, Full Schedule toggle | Task 15 |
| Offseason.tsx routing for 4 new components | Task 16 |
| TypeScript types updated | Task 9 |
| `records_ratified`, `hof_induction`, `retirements` skip when empty | Task 2 (compute_active_beats excludes them) |

**Placeholder scan:** No TBDs or "implement later" found.

**Type consistency:**
- `OffseasonAward.career_stat` used in Task 9 (types) and Task 14 (Ceremonies.tsx) — consistent.
- `DevelopmentBeatPayload.players` defined in Task 9, consumed in Task 12 — consistent.
- `RookieClassPreviewBeatPayload` defined in Task 9, consumed in Task 13 — consistent.
- `RecapBeatPayload.diff` added in Task 11, consumed in Task 11 — consistent.
- `load_active_beats` defined in Task 3, imported in Task 4 — consistent.
- `compute_active_beats` defined in Task 2, called in Task 2 (init), used indirectly via stored state — consistent.
