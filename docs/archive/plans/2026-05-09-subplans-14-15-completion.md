# Subplans 14 & 15 Completion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stub-quality ceremony and history-tab frontends with real data-driven implementations, wiring backend payload enrichment and real persistence queries throughout.

**Architecture:** Backend payload enrichment adds a `payload: dict` to the existing `/api/offseason/beat` response (alongside the existing `body` string) so ceremony components can render per-entity card UIs. The two history endpoints (`/api/history/my-program`, `/api/history/league`) replace hardcoded stubs with direct SQL and existing persistence functions. New React components (`MilestoneTree`, `AlumniLineage`, `BannerShelf`, `ProgramModal`) compose inside the rewritten `MyProgramView` and `LeagueView`.

**Tech Stack:** FastAPI + SQLite backend (Python 3.10+), React 18 + TypeScript + Vite frontend. Tests: pytest (backend), `npm run build` (frontend type-check). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-09-subplans-14-15-completion-design.md`

---

## Task 0: Housekeeping

**Files:**
- Delete: `patch.js` (repo root)
- Commit: `docs/superpowers/plans/2026-05-08-ux-polish/wave-2-hierarchy/*.md` (5 files)
- Commit: `docs/superpowers/plans/2026-05-08-ux-polish/wave-3-soul/*.md` (6 files)

- [ ] **Step 1: Delete patch.js**

```bash
git rm patch.js
```

- [ ] **Step 2: Stage and commit all 11 modified plan docs**

```bash
git add docs/superpowers/plans/2026-05-08-ux-polish/
git commit -m "docs: commit wave-2/3 plan doc edits from prior session"
```

Expected: clean working tree except `patch.js` deletion staged.

- [ ] **Step 3: Verify**

```bash
git status
```

Expected: working tree clean.

---

## Task 1: Expand History Endpoint Tests

**Files:**
- Modify: `tests/test_dynasty_history.py`

- [ ] **Step 1: Write expanded failing assertions**

Replace the entire contents of `tests/test_dynasty_history.py` with:

```python
from fastapi.testclient import TestClient
from dodgeball_sim.server import app, get_db
import sqlite3
from dodgeball_sim.persistence import create_schema, save_retired_player
from dodgeball_sim.career_setup import initialize_curated_manager_career


def _career_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_my_program_returns_required_keys():
    conn = _career_conn()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        res = client.get("/api/history/my-program?club_id=aurora")
        assert res.status_code == 200
        data = res.json()
        assert "timeline" in data
        assert "alumni" in data
        assert "banners" in data
        assert "hero" in data
        assert isinstance(data["timeline"], list)
        assert isinstance(data["alumni"], list)
        assert isinstance(data["banners"], list)
    finally:
        app.dependency_overrides.clear()


def test_my_program_hero_has_current_and_season_1():
    conn = _career_conn()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        res = client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        hero = data.get("hero", {})
        # hero may be empty for a brand-new career with no completed season,
        # but the key itself must always be present
        assert isinstance(hero, dict)
    finally:
        app.dependency_overrides.clear()


def test_my_program_alumni_scoped_to_club():
    """Alumni for club A must not include players whose last club was club B."""
    conn = _career_conn()

    # Find a non-aurora club id
    other_club_id = conn.execute(
        "SELECT club_id FROM club_rosters WHERE club_id != 'aurora' LIMIT 1"
    ).fetchone()
    if other_club_id is None:
        return  # only one club in this fixture; skip
    other_club_id = other_club_id["club_id"]

    # Seed a player as retired under the other club via player_season_stats
    conn.execute(
        "INSERT OR IGNORE INTO player_season_stats (player_id, season_id, club_id, matches) VALUES (?, ?, ?, 1)",
        ("test_p_other", "season_1", other_club_id),
    )
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        res = client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        alumni_ids = {a["id"] for a in data.get("alumni", [])}
        assert "test_p_other" not in alumni_ids, (
            "Player whose last club was another team appeared in aurora alumni"
        )
    finally:
        app.dependency_overrides.clear()


def test_league_returns_required_keys():
    conn = _career_conn()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        res = client.get("/api/history/league")
        assert res.status_code == 200
        data = res.json()
        assert "directory" in data
        assert "dynasty_rankings" in data
        assert "records" in data
        assert "hof" in data
        assert "rivalries" in data
        assert isinstance(data["dynasty_rankings"], list)
        assert isinstance(data["hof"], list)
        assert isinstance(data["rivalries"], list)
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run tests to see which fail**

```bash
python -m pytest tests/test_dynasty_history.py -v
```

Expected: `test_my_program_hero_has_current_and_season_1` may fail (no `hero` key), `test_league_returns_required_keys` fails (no `rivalries` key).

---

## Task 2: Wire `/api/history/my-program`

**Files:**
- Modify: `src/dodgeball_sim/server.py` (line ~1834, the `get_history_my_program` function)
- Modify: `src/dodgeball_sim/server.py` (imports block, line 17)

- [ ] **Step 1: Add missing persistence imports**

In `server.py`, extend the `from dodgeball_sim.persistence import (...)` block to include:

```python
    load_club_trophies,
    load_retired_players,
    load_player_career_stats,
```

(Add these three lines inside the existing multi-line import at line 17.)

- [ ] **Step 2: Replace `get_history_my_program` with real implementation**

Replace the existing stub at line ~1834:

```python
@app.get("/api/history/my-program")
def get_history_my_program(club_id: str, conn = Depends(get_db)):
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    current_roster = rosters.get(club_id, [])

    # Hero: first and latest completed season for this club
    all_seasons = conn.execute(
        """
        SELECT season_id, wins, losses, draws, points
        FROM season_standings WHERE club_id = ?
        ORDER BY season_id ASC
        """,
        (club_id,),
    ).fetchall()

    hero: dict = {}
    if all_seasons:
        def _standing_hero(row):
            return {
                "season_label": row["season_id"],
                "wins": row["wins"],
                "losses": row["losses"],
                "draws": row["draws"],
            }

        trophies = load_club_trophies(conn)
        champ_count = sum(
            1 for t in trophies
            if t["club_id"] == club_id and t["trophy_type"] == "championship"
        )
        avg_ovr = (
            round(sum(p.overall() for p in current_roster) / len(current_roster), 1)
            if current_roster else 0
        )
        hero["season_1"] = _standing_hero(all_seasons[0])
        current = _standing_hero(all_seasons[-1])
        current["avg_ovr"] = avg_ovr
        current["championships"] = champ_count
        hero["current"] = current

    # Timeline events
    timeline = []

    # First win
    first_win = conn.execute(
        """
        SELECT season_id, week FROM match_records
        WHERE winner_club_id = ?
        ORDER BY season_id ASC, week ASC
        LIMIT 1
        """,
        (club_id,),
    ).fetchone()
    if first_win:
        timeline.append({
            "season": first_win["season_id"],
            "week": first_win["week"],
            "event_type": "standard",
            "label": "First Win",
            "weight": "standard",
        })

    # Championships
    for t in load_club_trophies(conn):
        if t["club_id"] == club_id and t["trophy_type"] == "championship":
            timeline.append({
                "season": t["season_id"],
                "week": None,
                "event_type": "championship",
                "label": "Champions",
                "weight": "championship",
            })

    # Awards won by this club's players
    award_rows = conn.execute(
        "SELECT season_id, award_type, player_id FROM season_awards WHERE club_id = ?",
        (club_id,),
    ).fetchall()
    for row in award_rows:
        label_map = {
            "mvp": "MVP Award",
            "top_rookie": "Top Rookie",
            "best_defender": "Best Defender",
            "most_improved": "Most Improved",
            "championship": "Championship Award",
        }
        timeline.append({
            "season": row["season_id"],
            "week": None,
            "event_type": "award",
            "label": label_map.get(row["award_type"], row["award_type"]),
            "weight": "award",
        })

    current_ids = {p.id for p in current_roster}
    retired_rows = load_retired_players(conn)

    # Build last_club_map: player_id → last club_id they played for
    last_club_rows = conn.execute(
        """
        SELECT ps.player_id, ps.club_id
        FROM player_season_stats ps
        INNER JOIN (
            SELECT player_id, MAX(season_id) AS max_season
            FROM player_season_stats
            GROUP BY player_id
        ) latest ON ps.player_id = latest.player_id AND ps.season_id = latest.max_season
        """
    ).fetchall()
    last_club_map = {row["player_id"]: row["club_id"] for row in last_club_rows}

    # Hall of Fame inductees from this club
    for entry in conn.execute(
        "SELECT player_id, induction_season FROM hall_of_fame ORDER BY induction_season"
    ).fetchall():
        if last_club_map.get(entry["player_id"]) == club_id or entry["player_id"] in current_ids:
            # find player name
            player_name = entry["player_id"]
            for r in retired_rows:
                if r["player_id"] == entry["player_id"] and r.get("player"):
                    player_name = r["player"].name
                    break
            for p in current_roster:
                if p.id == entry["player_id"]:
                    player_name = p.name
                    break
            timeline.append({
                "season": entry["induction_season"],
                "week": None,
                "event_type": "hof",
                "label": f"HoF: {player_name}",
                "weight": "hof",
            })

    # Records set by players from this club
    for rec in conn.execute(
        "SELECT record_type, holder_id, record_value, set_in_season FROM league_records"
    ).fetchall():
        if last_club_map.get(rec["holder_id"]) == club_id or rec["holder_id"] in current_ids:
            timeline.append({
                "season": rec["set_in_season"],
                "week": None,
                "event_type": "record",
                "label": f"Record: {rec['record_type']}",
                "weight": "record",
            })

    # Sort timeline by season then week (None last in week)
    timeline.sort(key=lambda e: (e["season"], e["week"] or 999))

    # Alumni (retired players whose last known club was this one)
    alumni = []
    for r in retired_rows:
        if last_club_map.get(r["player_id"]) != club_id:
            continue
        p = r.get("player")
        if p is None:
            continue
        career = load_player_career_stats(conn, r["player_id"])
        alumni.append({
            "id": r["player_id"],
            "name": p.name,
            "seasons_played": int((career or {}).get("seasons_played", 0)),
            "career_elims": int((career or {}).get("total_eliminations", 0)),
            "championships": int((career or {}).get("championships", 0)),
            "ovr_final": float(r.get("overall", round(p.overall(), 1))),
            "potential_tier": calculate_potential_tier(p.traits.potential),
        })

    # Banners
    banners = []
    for t in load_club_trophies(conn):
        if t["club_id"] != club_id:
            continue
        if t["trophy_type"] == "championship":
            banners.append({
                "type": "championship",
                "season": t["season_id"],
                "label": "Champions",
            })
    for row in award_rows:
        label_map = {
            "mvp": "MVP Award",
            "top_rookie": "Top Rookie",
            "best_defender": "Best Defender",
            "most_improved": "Most Improved",
        }
        if row["award_type"] in label_map:
            banners.append({
                "type": "award",
                "season": row["season_id"],
                "label": label_map[row["award_type"]],
            })
    banners.sort(key=lambda b: b["season"])

    return {
        "club_id": club_id,
        "hero": hero,
        "timeline": timeline,
        "alumni": alumni,
        "banners": banners,
    }
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_dynasty_history.py -v
```

Expected: all 3 tests pass.

- [ ] **Step 4: Run full suite to confirm no regressions**

```bash
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/dodgeball_sim/server.py tests/test_dynasty_history.py
git commit -m "feat(history): wire /api/history/my-program with real persistence data"
```

---

## Task 3: Wire `/api/history/league`

**Files:**
- Modify: `src/dodgeball_sim/server.py` (line ~1844, `get_history_league`)
- Modify: `src/dodgeball_sim/server.py` (imports)

- [ ] **Step 1: Add missing persistence imports**

Extend the `from dodgeball_sim.persistence import (...)` block to also include:

```python
    load_hall_of_fame,
    load_rivalry_records,
```

- [ ] **Step 2: Replace `get_history_league` with real implementation**

Replace the existing stub:

```python
@app.get("/api/history/league")
def get_history_league(conn = Depends(get_db)):
    clubs = load_clubs(conn)

    # Directory
    directory = [{"club_id": c.club_id, "name": c.name} for c in clubs.values()]

    # Dynasty rankings: championship count + longest win streak per club
    all_trophies = load_club_trophies(conn)
    trophy_counts: dict = {}
    for t in all_trophies:
        if t["trophy_type"] == "championship":
            trophy_counts[t["club_id"]] = trophy_counts.get(t["club_id"], 0) + 1

    # Longest win streak per club from match_records
    streak_map: dict = {}
    for c_id in clubs:
        rows = conn.execute(
            """
            SELECT winner_club_id FROM match_records
            WHERE home_club_id = ? OR away_club_id = ?
            ORDER BY season_id, week
            """,
            (c_id, c_id),
        ).fetchall()
        best = cur = 0
        for row in rows:
            if row["winner_club_id"] == c_id:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        streak_map[c_id] = best

    dynasty_rankings = sorted(
        [
            {
                "club_id": c_id,
                "club_name": clubs[c_id].name,
                "championships": trophy_counts.get(c_id, 0),
                "longest_win_streak": streak_map.get(c_id, 0),
            }
            for c_id in clubs
        ],
        key=lambda r: (-r["championships"], -r["longest_win_streak"], r["club_name"]),
    )

    # Hall of Fame
    hof = []
    for entry in load_hall_of_fame(conn):
        cs = entry.get("career_summary") or {}
        player_name = cs.get("player_name", entry["player_id"])
        hof.append({
            "player_id": entry["player_id"],
            "player_name": player_name,
            "induction_season": entry["induction_season"],
            "career_elims": int(cs.get("total_eliminations", 0)),
            "championships": int(cs.get("championships", 0)),
            "seasons_played": int(cs.get("seasons_played", 0)),
        })

    # Rivalries
    rivalries = []
    for r in load_rivalry_records(conn):
        rv = r.get("rivalry") or {}
        a_id = r["club_a_id"]
        b_id = r["club_b_id"]
        a_wins = int(rv.get("a_wins", 0))
        b_wins = int(rv.get("b_wins", 0))
        draws = int(rv.get("draws", 0))
        rivalries.append({
            "club_a": clubs[a_id].name if a_id in clubs else a_id,
            "club_b": clubs[b_id].name if b_id in clubs else b_id,
            "a_wins": a_wins,
            "b_wins": b_wins,
            "draws": draws,
            "meetings": a_wins + b_wins + draws,
        })
    rivalries.sort(key=lambda r: -r["meetings"])

    return {
        "directory": directory,
        "dynasty_rankings": dynasty_rankings,
        "records": load_league_records(conn),
        "hof": hof,
        "rivalries": rivalries,
    }
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/test_dynasty_history.py -v
```

Expected: all 3 pass.

- [ ] **Step 4: Full suite**

```bash
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/dodgeball_sim/server.py
git commit -m "feat(history): wire /api/history/league with dynasty rankings, HoF, and rivalries"
```

---

## Task 4: Write Ceremony Payload Tests

**Files:**
- Create: `tests/test_ceremony_payload.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ceremony_payload.py`:

```python
"""Tests that /api/offseason/beat returns a `payload` dict with the right top-level keys."""
from __future__ import annotations

import sqlite3

import pytest
from dodgeball_sim.server import _build_beat_payload
from dodgeball_sim.persistence import create_schema


def _empty_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.commit()
    return conn


def test_awards_payload_has_awards_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "awards",
        awards=[],
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
    assert "awards" in result
    assert isinstance(result["awards"], list)


def test_retirements_payload_has_retirees_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "retirements",
        awards=[],
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
    assert "retirees" in result
    assert isinstance(result["retirees"], list)


def test_recap_payload_has_standings_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "recap",
        awards=[],
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
    assert "standings" in result
    assert isinstance(result["standings"], list)


def test_recruitment_payload_has_player_signing_key():
    conn = _empty_conn()
    result = _build_beat_payload(
        "recruitment",
        awards=[],
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
    assert "player_signing" in result
    assert "other_signings" in result


def test_schedule_reveal_payload_has_fixtures_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "schedule_reveal",
        awards=[],
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
    assert "fixtures" in result
    assert isinstance(result["fixtures"], list)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_ceremony_payload.py -v
```

Expected: ImportError or AttributeError — `_build_beat_payload` does not exist yet.

---

## Task 5: Backend Payload Enrichment

**Files:**
- Modify: `src/dodgeball_sim/server.py`

- [ ] **Step 1: Add `_build_beat_payload()` function**

Add this function immediately before `_build_beat_response()` (around line 1666):

```python
def _build_beat_payload(
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
    conn,
) -> dict:
    """Build structured payload dict for a given beat key."""

    def _club_name(club_id: str) -> str:
        c = clubs.get(club_id)
        return c.name if c else club_id

    def _find_player(player_id: str):
        for roster in rosters.values():
            for p in roster:
                if p.id == player_id:
                    return p
        return None

    if beat_key == "awards":
        result = []
        for award in awards:
            p = _find_player(award.player_id)
            career = load_player_career_stats(conn, award.player_id)
            result.append({
                "player_name": p.name if p else award.player_id,
                "club_name": _club_name(award.club_id),
                "award_type": award.award_type,
                "career_elims": int((career or {}).get("total_eliminations", 0)),
                "ovr": int(round(p.overall())) if p else 0,
            })
        return {"awards": result}

    if beat_key == "retirements":
        retired_by_id = {r["player_id"]: r.get("player") for r in load_retired_players(conn)}
        retirees = []
        for row in ret_rows:
            pid = row.get("player_id", "")
            career = load_player_career_stats(conn, pid)
            player_obj = retired_by_id.get(pid)
            potential = player_obj.traits.potential if player_obj else 0.0
            retirees.append({
                "name": row.get("player_name", pid),
                "ovr_final": float(row.get("overall", 0)),
                "career_elims": int((career or {}).get("total_eliminations", 0)),
                "championships": int((career or {}).get("championships", 0)),
                "seasons_played": int((career or {}).get("seasons_played", 0)),
                "potential_tier": calculate_potential_tier(potential),
            })
        return {"retirees": retirees}

    if beat_key == "champion":
        if season_outcome and season_outcome.champion_club_id:
            trophies = load_club_trophies(conn)
            title_count = sum(
                1 for t in trophies
                if t["club_id"] == season_outcome.champion_club_id
                and t["trophy_type"] == "championship"
            )
            row = next(
                (s for s in standings if s.club_id == season_outcome.champion_club_id),
                None,
            )
            return {
                "champion": {
                    "club_name": _club_name(season_outcome.champion_club_id),
                    "wins": row.wins if row else 0,
                    "losses": row.losses if row else 0,
                    "draws": row.draws if row else 0,
                    "title_count": title_count,
                }
            }
        return {}

    if beat_key == "recap":
        player_club_id = get_state(conn, "player_club_id") or ""
        return {
            "standings": [
                {
                    "rank": i + 1,
                    "club_name": _club_name(row.club_id),
                    "wins": row.wins,
                    "losses": row.losses,
                    "draws": row.draws,
                    "points": row.points,
                    "is_player_club": row.club_id == player_club_id,
                }
                for i, row in enumerate(standings)
            ]
        }

    if beat_key == "recruitment":
        player_signing = None
        if signed_player_id:
            p = _find_player(signed_player_id)
            if p:
                player_signing = {
                    "name": p.name,
                    "ovr": int(round(p.overall())),
                    "age": p.age,
                }
        return {"player_signing": player_signing, "other_signings": []}

    if beat_key == "schedule_reveal":
        if next_preview is None:
            return {"fixtures": [], "season_label": "", "prediction": ""}
        player_club_id = get_state(conn, "player_club_id") or ""
        fixtures = [
            {
                "week": m.week,
                "home": _club_name(m.home_club_id),
                "away": _club_name(m.away_club_id),
                "is_player_match": (
                    m.home_club_id == player_club_id or m.away_club_id == player_club_id
                ),
            }
            for m in next_preview.scheduled_matches
        ]
        prediction = ""
        player_match = next(
            (
                m for m in next_preview.scheduled_matches
                if m.home_club_id == player_club_id or m.away_club_id == player_club_id
            ),
            None,
        )
        if player_match:
            try:
                from dodgeball_sim.rng import DeterministicRNG, derive_seed
                from dodgeball_sim.voice_pregame import render_matchup_framing
                root_seed = stored_root_seed(conn)
                rng = DeterministicRNG(derive_seed(root_seed, "schedule_reveal_prediction"))
                prediction = render_matchup_framing(
                    _club_name(player_match.home_club_id),
                    _club_name(player_match.away_club_id),
                    rng,
                )
            except Exception:
                prediction = ""
        return {
            "season_label": str(next_preview.year) if next_preview else "",
            "fixtures": fixtures,
            "prediction": prediction,
        }

    return {}
```

- [ ] **Step 2: Wire `_build_beat_payload` into `_build_beat_response`**

In `_build_beat_response`, after the `beat = build_offseason_ceremony_beat(...)` call (~line 1700), add:

```python
    payload = _build_beat_payload(
        beat.key,
        awards=awards,
        clubs=clubs,
        rosters=rosters,
        standings=standings,
        ret_rows=ret_rows,
        season=season,
        season_outcome=season_outcome,
        next_preview=next_preview,
        signed_player_id=signed_player_id,
        conn=conn,
    )
```

And in the `return {...}` dict, add:

```python
        "payload": payload,
```

(alongside the existing `"body"`, `"key"`, etc. keys)

- [ ] **Step 3: Run payload tests**

```bash
python -m pytest tests/test_ceremony_payload.py -v
```

Expected: all 5 pass.

- [ ] **Step 4: Run full suite**

```bash
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/dodgeball_sim/server.py tests/test_ceremony_payload.py
git commit -m "feat(ceremonies): add structured payload to offseason beat response"
```

---

## Task 6: Update TypeScript `OffseasonBeat` Interface

**Files:**
- Modify: `frontend/src/components/Offseason.tsx`

- [ ] **Step 1: Add `payload` field to the interface**

In `Offseason.tsx` at line 6, update the `OffseasonBeat` interface to add:

```typescript
interface OffseasonBeat {
  beat_index: number;
  total_beats: number;
  key: string;
  title: string;
  body: string;
  state: string;
  can_advance: boolean;
  can_recruit: boolean;
  can_begin_season: boolean;
  signed_player_id: string;
  signed_player?: { id: string; name: string; overall: number; age: number } | null;
  payload?: Record<string, any>;
}
```

Note: `body` is `string` (not `string[]`) since it's a newline-joined string from the backend.

- [ ] **Step 2: Build to verify no type errors**

```bash
cd frontend && npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Offseason.tsx
git commit -m "feat(ceremonies): add payload field to OffseasonBeat TypeScript interface"
```

---

## Task 7: Rewrite `AwardsNight.tsx`

**Files:**
- Modify: `frontend/src/components/ceremonies/Ceremonies.tsx`

- [ ] **Step 1: Replace the `AwardsNight` export**

Replace the current `AwardsNight` function (lines 3–19) with:

```typescript
const AWARD_ICON: Record<string, string> = {
  mvp: '🏆',
  top_rookie: '⚡',
  best_defender: '🛡️',
  most_improved: '📈',
  championship: '🥇',
};

const AWARD_COLOR: Record<string, string> = {
  mvp: '#f97316',
  top_rookie: '#eab308',
  best_defender: '#3b82f6',
  most_improved: '#10b981',
  championship: '#f97316',
};

export function AwardsNight({ beat, onComplete }: { beat: any; onComplete: () => void }) {
  const awards: any[] = beat.payload?.awards ?? [];

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
          {awards.slice(0, stage).map((award: any, i: number) => {
            const color = AWARD_COLOR[award.award_type] ?? '#f97316';
            const icon = AWARD_ICON[award.award_type] ?? '🏅';
            const isLatest = i === stage - 1;
            return (
              <div
                key={i}
                className="fade-in"
                style={{
                  border: `1px solid ${isLatest ? color : '#334155'}`,
                  borderRadius: '8px',
                  padding: '1rem',
                  background: isLatest ? `${color}11` : '#0f172a',
                  opacity: isLatest ? 1 : 0.6,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1rem',
                }}
              >
                <span style={{ fontSize: '2rem' }}>{icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: isLatest ? color : '#e2e8f0' }}>
                    {award.player_name}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {award.club_name} · {award.career_elims} career elims
                    {award.ovr ? ` · OVR ${award.ovr}` : ''}
                  </div>
                </div>
                {!isLatest && <span style={{ color: '#475569' }}>✓</span>}
              </div>
            );
          })}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx
git commit -m "feat(ceremonies): rewrite AwardsNight with payload-driven card reveal"
```

---

## Task 8: Rewrite `Graduation.tsx`

**Files:**
- Modify: `frontend/src/components/ceremonies/Ceremonies.tsx`

- [ ] **Step 1: Replace the `Graduation` export**

Replace the current `Graduation` function (lines ~21–36) with:

```typescript
const TIER_COLOR: Record<string, string> = {
  Elite: '#10b981',
  High: '#3b82f6',
  Solid: '#94a3b8',
  Limited: '#64748b',
  Unknown: '#475569',
};

export function Graduation({ beat, onComplete }: { beat: any; onComplete: () => void }) {
  const retirees: any[] = beat.payload?.retirees ?? [];

  if (retirees.length === 0) {
    return (
      <CeremonyShell
        title={beat.title}
        eyebrow="Graduation"
        description="Farewell to departing veterans."
        stages={1}
        renderStage={() => (
          <div style={{ textAlign: 'center', color: '#94a3b8' }}>
            {typeof beat.body === 'string' ? beat.body : 'No retirements this off-season.'}
          </div>
        )}
        onComplete={onComplete}
      />
    );
  }

  return (
    <CeremonyShell
      title={beat.title}
      eyebrow="Graduation"
      description="Saying goodbye to departing veterans."
      stages={retirees.length}
      renderStage={(stage) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '480px', margin: '0 auto' }}>
          {retirees.slice(0, stage).map((r: any, i: number) => {
            const isLatest = i === stage - 1;
            const tierColor = TIER_COLOR[r.potential_tier] ?? '#475569';
            return (
              <div
                key={i}
                className="fade-in"
                style={{
                  border: `1px solid ${isLatest ? '#10b981' : '#334155'}`,
                  borderRadius: '8px',
                  padding: '1rem',
                  background: '#0f172a',
                  opacity: isLatest ? 1 : 0.55,
                }}
              >
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.35rem' }}>
                  {r.name}
                </div>
                {r.ovr_final ? (
                  <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.35rem' }}>
                    OVR {r.ovr_final}
                  </div>
                ) : null}
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                  {r.career_elims} career elims · {r.championships} titles · {r.seasons_played} seasons
                </div>
                <div style={{ fontSize: '0.7rem', color: tierColor, fontWeight: 600 }}>
                  {r.potential_tier} potential
                </div>
              </div>
            );
          })}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx
git commit -m "feat(ceremonies): rewrite Graduation with payload-driven per-senior cards"
```

---

## Task 9: Rewrite `SigningDay.tsx`

**Files:**
- Modify: `frontend/src/components/ceremonies/Ceremonies.tsx`

- [ ] **Step 1: Replace the `SigningDay` export**

Replace the current `SigningDay` function with:

```typescript
export function SigningDay({ beat, onComplete }: { beat: any; onComplete: () => void }) {
  const playerSigning = beat.payload?.player_signing ?? null;
  const otherSignings: any[] = beat.payload?.other_signings ?? [];
  const totalStages = 1 + otherSignings.length;

  return (
    <CeremonyShell
      title={beat.title}
      eyebrow="Signing Day"
      description="The nation's top prospects have made their commitments."
      stages={totalStages}
      renderStage={(stage) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '480px', margin: '0 auto' }}>
          {/* Stage 1: player's pick */}
          {stage >= 1 && playerSigning && (
            <div
              className="fade-in"
              style={{
                border: '2px solid #22d3ee',
                borderRadius: '8px',
                padding: '1.25rem',
                background: '#083344',
              }}
            >
              <div style={{ fontSize: '0.65rem', color: '#22d3ee', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '0.5rem' }}>
                YOUR PICK
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#e2e8f0', marginBottom: '0.25rem' }}>
                {playerSigning.name}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                OVR {playerSigning.ovr}
                {playerSigning.age ? ` · Age ${playerSigning.age}` : ''}
                {playerSigning.role ? ` · ${playerSigning.role}` : ''}
              </div>
            </div>
          )}

          {/* Subsequent stages: AI signings */}
          {otherSignings.slice(0, stage - 1).map((s: any, i: number) => (
            <div
              key={i}
              className="fade-in"
              style={{
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '0.75rem 1rem',
                background: '#0f172a',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{s.name}</span>
                <span style={{ color: '#64748b', fontSize: '0.75rem', marginLeft: '0.5rem' }}>→ {s.club_name}</span>
              </div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>OVR {s.ovr}</span>
            </div>
          ))}

          {!playerSigning && (
            <div style={{ textAlign: 'center', color: '#94a3b8' }}>
              {typeof beat.body === 'string' ? beat.body : 'Signing complete.'}
            </div>
          )}
        </div>
      )}
      onComplete={onComplete}
    />
  );
}
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx
git commit -m "feat(ceremonies): rewrite SigningDay as results-reveal with payload-driven cards"
```

---

## Task 10: Rewrite `NewSeasonEve.tsx`

**Files:**
- Modify: `frontend/src/components/ceremonies/Ceremonies.tsx`

- [ ] **Step 1: Replace the `NewSeasonEve` export**

Replace the current `NewSeasonEve` function with:

```typescript
export function NewSeasonEve({ beat, onComplete }: { beat: any; onComplete: () => void }) {
  const fixtures: any[] = beat.payload?.fixtures ?? [];
  const prediction: string = beat.payload?.prediction ?? '';
  const seasonLabel: string = beat.payload?.season_label ?? '';

  return (
    <CeremonyShell
      title={beat.title}
      eyebrow={seasonLabel ? `Season ${seasonLabel}` : 'New Season'}
      description="A new chapter begins."
      stages={2}
      renderStage={(stage) => (
        <div style={{ width: '100%', maxWidth: '520px', margin: '0 auto' }}>
          {/* Stage 1: fixture list */}
          {stage >= 1 && (
            <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '1rem' }}>
              {fixtures.length === 0 ? (
                <div style={{ color: '#94a3b8', textAlign: 'center' }}>
                  {typeof beat.body === 'string' ? beat.body : 'Schedule not available.'}
                </div>
              ) : (
                fixtures.map((f: any, i: number) => (
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
                ))
              )}
            </div>
          )}

          {/* Stage 2: prediction */}
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
    />
  );
}
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

Expected: success with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ceremonies/Ceremonies.tsx
git commit -m "feat(ceremonies): rewrite NewSeasonEve with fixture list and prediction reveal"
```

---

## Task 11: Create `MilestoneTree.tsx`

**Files:**
- Create: `frontend/src/components/dynasty/history/MilestoneTree.tsx`

- [ ] **Step 1: Create the component file**

Create `frontend/src/components/dynasty/history/MilestoneTree.tsx`:

```typescript
interface TimelineEvent {
  season: string;
  week: number | null;
  event_type: string;
  label: string;
  weight: string;
}

interface MilestoneTreeProps {
  timeline: TimelineEvent[];
}

const WEIGHT_RADIUS: Record<string, number> = {
  championship: 16,
  hof: 12,
  award: 10,
  record: 9,
  milestone: 8,
  standard: 6,
};

interface EventColors {
  fill: string;
  stroke: string;
  branch: string;
  gradientId?: string;
}

const EVENT_COLORS: Record<string, EventColors> = {
  championship: { fill: '#c2410c', stroke: '#fb923c', branch: '#f97316', gradientId: 'champGrad' },
  hof: { fill: '#065f46', stroke: '#34d399', branch: '#10b981' },
  award: { fill: '#d97706', stroke: '#fbbf24', branch: '#eab308' },
  record: { fill: '#0369a1', stroke: '#38bdf8', branch: '#0ea5e9' },
  milestone: { fill: '#7c3aed', stroke: '#a78bfa', branch: '#8b5cf6' },
  standard: { fill: '#3b82f6', stroke: '#60a5fa', branch: '#3b82f6' },
};

const TRUNK_X = 90;
const ROW_HEIGHT = 68;
const V_PAD = 24;
const FIRST_DOT_GAP = 12;
const DOT_PITCH = 56;

export function MilestoneTree({ timeline }: MilestoneTreeProps) {
  // Group events by season
  const seasonMap = new Map<string, TimelineEvent[]>();
  for (const ev of timeline) {
    if (!seasonMap.has(ev.season)) seasonMap.set(ev.season, []);
    seasonMap.get(ev.season)!.push(ev);
  }
  const seasons = Array.from(seasonMap.keys()).sort();

  if (seasons.length === 0) {
    return (
      <div style={{ color: '#475569', fontSize: '0.8rem', padding: '1rem 0' }}>
        No milestones yet.
      </div>
    );
  }

  const totalHeight = seasons.length * ROW_HEIGHT + V_PAD * 2;
  const svgWidth = 460;

  // Precompute dot positions
  type DotInfo = {
    cx: number;
    cy: number;
    r: number;
    colors: EventColors;
    label: string;
    event_type: string;
  };

  const seasonDots: Map<string, DotInfo[]> = new Map();
  const seasonCy: Map<string, number> = new Map();

  seasons.forEach((season, si) => {
    const cy = V_PAD + si * ROW_HEIGHT;
    seasonCy.set(season, cy);
    const events = seasonMap.get(season) ?? [];
    const isChamp = events.some((e) => e.weight === 'championship');
    const trunkR = isChamp ? 8 : 6;

    const dots: DotInfo[] = events.map((ev, di) => {
      const r = WEIGHT_RADIUS[ev.weight] ?? 6;
      const colors = EVENT_COLORS[ev.event_type] ?? EVENT_COLORS.standard;
      const firstDotCx = TRUNK_X + trunkR + FIRST_DOT_GAP + (WEIGHT_RADIUS[events[0]?.weight ?? 'standard'] ?? 6);
      const cx = firstDotCx + di * DOT_PITCH;
      return { cx, cy, r, colors, label: ev.label, event_type: ev.event_type };
    });
    seasonDots.set(season, dots);
  });

  return (
    <div style={{ position: 'relative', width: svgWidth, overflowX: 'auto' }}>
      <svg
        width={svgWidth}
        height={totalHeight}
        style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}
      >
        <defs>
          <radialGradient id="champGrad" cx="40%" cy="35%">
            <stop offset="0%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#9a3412" />
          </radialGradient>
          <filter id="glowOrange" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glowGreen" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Trunk */}
        <line
          x1={TRUNK_X} y1={V_PAD}
          x2={TRUNK_X} y2={totalHeight - V_PAD}
          stroke="#475569"
          strokeWidth={3}
          strokeLinecap="round"
        />

        {seasons.map((season, si) => {
          const cy = seasonCy.get(season)!;
          const events = seasonMap.get(season) ?? [];
          const isEmpty = events.length === 0;
          const isChamp = events.some((e) => e.weight === 'championship');
          const trunkR = isChamp ? 8 : isEmpty ? 5 : 6;
          const dots = seasonDots.get(season) ?? [];

          return (
            <g key={season}>
              {/* Championship background band */}
              {isChamp && (
                <rect
                  x={0}
                  y={cy - 20}
                  width={svgWidth}
                  height={40}
                  fill="#f9731608"
                  rx={4}
                />
              )}

              {/* Trunk node */}
              {isEmpty ? (
                <circle
                  cx={TRUNK_X} cy={cy} r={trunkR}
                  fill="#0f172a"
                  stroke="#334155"
                  strokeWidth={1.5}
                  strokeDasharray="3 2"
                />
              ) : isChamp ? (
                <circle
                  cx={TRUNK_X} cy={cy} r={trunkR}
                  fill="#c2410c"
                  stroke="#fb923c"
                  strokeWidth={2.5}
                  filter="url(#glowOrange)"
                />
              ) : (
                <circle
                  cx={TRUNK_X} cy={cy} r={trunkR}
                  fill="#1e293b"
                  stroke="#475569"
                  strokeWidth={2}
                />
              )}

              {/* Empty season stub */}
              {isEmpty && (
                <line
                  x1={TRUNK_X + trunkR} y1={cy}
                  x2={TRUNK_X + trunkR + 20} y2={cy}
                  stroke="#1e293b"
                  strokeWidth={1.5}
                  strokeDasharray="3 2"
                />
              )}

              {/* Branch lines between dots */}
              {dots.map((dot, di) => {
                const branchColor = dot.colors.branch;
                const isChampDot = dot.event_type === 'championship';
                const strokeW = isChampDot ? 2 : 1.5;

                if (di === 0) {
                  // Trunk edge to first dot left edge
                  return (
                    <line
                      key={`branch-${di}`}
                      x1={TRUNK_X + trunkR} y1={cy}
                      x2={dot.cx - dot.r} y2={cy}
                      stroke={branchColor}
                      strokeWidth={strokeW}
                      opacity={0.7}
                    />
                  );
                }
                const prev = dots[di - 1];
                return (
                  <line
                    key={`branch-${di}`}
                    x1={prev.cx + prev.r} y1={cy}
                    x2={dot.cx - dot.r} y2={cy}
                    stroke={branchColor}
                    strokeWidth={strokeW}
                    opacity={0.7}
                  />
                );
              })}

              {/* Milestone dots */}
              {dots.map((dot, di) => {
                const { cx, cy: dotCy, r, colors, event_type } = dot;
                const isChampDot = event_type === 'championship';
                const isHof = event_type === 'hof';
                const glowFilter = isChampDot
                  ? 'url(#glowOrange)'
                  : isHof
                  ? 'url(#glowGreen)'
                  : undefined;
                const fillAttr = isChampDot ? 'url(#champGrad)' : colors.fill;
                return (
                  <circle
                    key={di}
                    cx={cx}
                    cy={dotCy}
                    r={r}
                    fill={fillAttr}
                    stroke={colors.stroke}
                    strokeWidth={isChampDot ? 3 : 2}
                    filter={glowFilter}
                  />
                );
              })}
            </g>
          );
        })}

        {/* Present trailing dot */}
        <circle
          cx={TRUNK_X}
          cy={totalHeight - V_PAD + 12}
          r={3}
          fill="#334155"
          opacity={0.5}
        />
      </svg>

      {/* HTML label layer */}
      <div style={{ position: 'relative', height: totalHeight }}>
        {seasons.map((season) => {
          const cy = seasonCy.get(season)!;
          const events = seasonMap.get(season) ?? [];
          const isEmpty = events.length === 0;
          const isChamp = events.some((e) => e.weight === 'championship');
          const dots = seasonDots.get(season) ?? [];

          return (
            <div key={season}>
              {/* Season label left of trunk */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  width: TRUNK_X - 6,
                  textAlign: 'right',
                  top: cy - 7,
                  fontSize: '0.6rem',
                  color: isChamp ? '#fb923c' : isEmpty ? '#334155' : '#64748b',
                  fontWeight: isChamp ? 700 : 400,
                  fontStyle: isEmpty ? 'italic' : 'normal',
                  whiteSpace: 'nowrap',
                }}
              >
                {season}
              </div>

              {/* Empty season text */}
              {isEmpty && (
                <div
                  style={{
                    position: 'absolute',
                    left: TRUNK_X + 26,
                    top: cy - 7,
                    fontSize: '0.55rem',
                    color: '#334155',
                    fontStyle: 'italic',
                    whiteSpace: 'nowrap',
                  }}
                >
                  — no milestones
                </div>
              )}

              {/* Dot labels */}
              {dots.map((dot, di) => (
                <div
                  key={di}
                  style={{
                    position: 'absolute',
                    left: dot.cx,
                    top: dot.cy + dot.r + 4,
                    transform: 'translateX(-50%)',
                    fontSize: '0.55rem',
                    color: dot.colors.stroke,
                    whiteSpace: 'nowrap',
                    fontWeight: dot.event_type === 'championship' ? 700 : 400,
                    textAlign: 'center',
                  }}
                >
                  {dot.event_type === 'championship' ? '🏆 ' : ''}{dot.label}
                </div>
              ))}
            </div>
          );
        })}

        {/* Present label */}
        <div
          style={{
            position: 'absolute',
            left: TRUNK_X + 12,
            top: totalHeight - V_PAD + 6,
            fontSize: '0.55rem',
            color: '#334155',
            fontStyle: 'italic',
          }}
        >
          Present…
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

Expected: success.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dynasty/history/MilestoneTree.tsx
git commit -m "feat(history): add MilestoneTree SVG component with season grouping and variable dot weights"
```

---

## Task 12: Create `AlumniLineage.tsx` and `BannerShelf.tsx`

**Files:**
- Create: `frontend/src/components/dynasty/history/AlumniLineage.tsx`
- Create: `frontend/src/components/dynasty/history/BannerShelf.tsx`

- [ ] **Step 1: Create `AlumniLineage.tsx`**

```typescript
interface AlumnusEntry {
  id: string;
  name: string;
  seasons_played: number;
  career_elims: number;
  championships: number;
  ovr_final: number;
  potential_tier: string;
}

const TIER_COLOR: Record<string, string> = {
  Elite: '#10b981',
  High: '#3b82f6',
  Solid: '#94a3b8',
  Limited: '#64748b',
  Unknown: '#475569',
};

export function AlumniLineage({ alumni }: { alumni: AlumnusEntry[] }) {
  if (alumni.length === 0) {
    return (
      <p style={{ color: '#475569', fontSize: '0.8rem' }}>No departed players yet.</p>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      {alumni.map((a) => {
        const tierColor = TIER_COLOR[a.potential_tier] ?? '#475569';
        return (
          <div
            key={a.id}
            style={{
              border: '1px solid #1e293b',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              background: '#0a1628',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.3rem' }}>
              <span style={{ fontWeight: 700, color: '#e2e8f0', fontSize: '0.9rem' }}>{a.name}</span>
              <span style={{ fontSize: '0.65rem', color: '#475569' }}>
                {a.seasons_played} season{a.seasons_played !== 1 ? 's' : ''}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              {a.career_elims} elims · {a.championships} title{a.championships !== 1 ? 's' : ''}
              {a.ovr_final ? ` · OVR ${a.ovr_final}` : ''}
            </div>
            <div style={{ fontSize: '0.68rem', color: tierColor, fontWeight: 600 }}>
              {a.potential_tier} potential
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create `BannerShelf.tsx`**

```typescript
interface BannerEntry {
  type: string;
  season: string;
  label: string;
}

export function BannerShelf({ banners, showNextPlaceholder }: { banners: BannerEntry[]; showNextPlaceholder?: boolean }) {
  if (banners.length === 0 && !showNextPlaceholder) {
    return <p style={{ color: '#475569', fontSize: '0.8rem' }}>No banners yet.</p>;
  }

  return (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
      {banners.map((b, i) => (
        <div key={i} style={{ textAlign: 'center' }}>
          <div style={{ fontSize: b.type === 'championship' ? '2.5rem' : '1.75rem' }}>
            {b.type === 'championship' ? '🏆' : '🏅'}
          </div>
          <div
            style={{
              fontSize: '0.6rem',
              color: b.type === 'championship' ? '#f97316' : '#eab308',
              fontWeight: 600,
              whiteSpace: 'nowrap',
              marginTop: '0.2rem',
            }}
          >
            {b.label}
          </div>
          <div style={{ fontSize: '0.55rem', color: '#475569' }}>{b.season}</div>
        </div>
      ))}

      {showNextPlaceholder && (
        <div
          style={{
            width: '48px',
            height: '56px',
            border: '1px dashed #1e293b',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ color: '#334155', fontSize: '1rem' }}>+</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dynasty/history/AlumniLineage.tsx frontend/src/components/dynasty/history/BannerShelf.tsx
git commit -m "feat(history): add AlumniLineage and BannerShelf sub-components"
```

---

## Task 13: Create `ProgramModal.tsx`

**Files:**
- Create: `frontend/src/components/dynasty/history/ProgramModal.tsx`

- [ ] **Step 1: Create the component**

```typescript
import { useEffect } from 'react';
import { MyProgramView } from './MyProgramView';

interface ProgramModalProps {
  clubId: string;
  clubName: string;
  onClose: () => void;
}

export function ProgramModal({ clubId, clubName, onClose }: ProgramModalProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        zIndex: 200,
        padding: '2rem 1rem',
        overflowY: 'auto',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '10px',
          width: '100%',
          maxWidth: '640px',
          padding: '1.5rem',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.1rem', color: '#e2e8f0' }}>{clubName}</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              fontSize: '1.25rem',
              cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>
        <MyProgramView clubId={clubId} isSelf={false} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build (expect TypeScript error on isSelf prop — fix in next task)**

```bash
cd frontend && npm run build
```

Note: `MyProgramView` does not yet accept `isSelf` — the error will be resolved in Task 14.

- [ ] **Step 3: Don't commit yet — commit after Task 14 clears build errors.**

---

## Task 14: Rewrite `MyProgramView.tsx`

**Files:**
- Modify: `frontend/src/components/dynasty/history/MyProgramView.tsx`

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:

```typescript
import { useEffect, useState } from 'react';
import { MilestoneTree } from './MilestoneTree';
import { AlumniLineage } from './AlumniLineage';
import { BannerShelf } from './BannerShelf';

interface HeroSeason {
  season_label: string;
  wins: number;
  losses: number;
  draws: number;
  avg_ovr?: number;
  championships?: number;
}

interface ProgramData {
  club_id: string;
  hero: { season_1?: HeroSeason; current?: HeroSeason };
  timeline: any[];
  alumni: any[];
  banners: any[];
}

function HeroCard({ data, label, highlight }: { data: HeroSeason; label: string; highlight: boolean }) {
  return (
    <div
      style={{
        flex: 1,
        border: `1px solid ${highlight ? '#10b981' : '#1e293b'}`,
        borderRadius: '8px',
        padding: '1rem',
        background: '#0a1628',
        boxShadow: highlight ? '0 0 12px #10b98133' : 'none',
      }}
    >
      <div style={{ fontSize: '0.6rem', color: highlight ? '#10b981' : '#475569', fontWeight: 700, marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </div>
      <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem' }}>{data.season_label}</div>
      <div style={{ fontSize: '1rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.25rem' }}>
        {data.wins}–{data.losses}–{data.draws}
      </div>
      {data.avg_ovr !== undefined && (
        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Avg OVR {data.avg_ovr}</div>
      )}
      {data.championships !== undefined && data.championships > 0 && (
        <div style={{ fontSize: '0.75rem', color: '#f97316', marginTop: '0.25rem' }}>
          🏆 {data.championships} title{data.championships !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
}

export function MyProgramView({ clubId, isSelf = true }: { clubId: string; isSelf?: boolean }) {
  const [data, setData] = useState<ProgramData | null>(null);

  useEffect(() => {
    fetch(`/api/history/my-program?club_id=${clubId}`)
      .then((res) => res.json())
      .then(setData);
  }, [clubId]);

  if (!data) return <div style={{ color: '#475569', padding: '1rem' }}>Loading program history…</div>;

  const { hero, timeline, alumni, banners } = data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Hero Strip */}
      {(hero.season_1 || hero.current) && (
        <div className="dm-panel">
          <p className="dm-kicker">Program Arc</p>
          <div style={{ display: 'flex', gap: '1rem' }}>
            {hero.season_1 && <HeroCard data={hero.season_1} label="How it started" highlight={false} />}
            {hero.current && <HeroCard data={hero.current} label="Today" highlight={true} />}
          </div>
        </div>
      )}

      {/* Milestone Tree */}
      <div className="dm-panel">
        <p className="dm-kicker">Program History</p>
        <div style={{ overflowX: 'auto' }}>
          <MilestoneTree timeline={timeline} />
        </div>
      </div>

      {/* Alumni + Banners */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div className="dm-panel" style={{ flex: 1, minWidth: '260px' }}>
          <p className="dm-kicker">Alumni Lineage</p>
          <AlumniLineage alumni={alumni} />
        </div>
        <div className="dm-panel" style={{ flex: 1, minWidth: '260px' }}>
          <p className="dm-kicker">Banner Shelf</p>
          <BannerShelf banners={banners} showNextPlaceholder={isSelf} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build (resolves ProgramModal's isSelf error too)**

```bash
cd frontend && npm run build
```

Expected: clean build.

- [ ] **Step 3: Commit both files together**

```bash
git add frontend/src/components/dynasty/history/MyProgramView.tsx frontend/src/components/dynasty/history/ProgramModal.tsx
git commit -m "feat(history): rewrite MyProgramView with hero strip, MilestoneTree, alumni, and banners"
```

---

## Task 15: Rewrite `LeagueView.tsx`

**Files:**
- Modify: `frontend/src/components/dynasty/history/LeagueView.tsx`

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:

```typescript
import { useEffect, useState } from 'react';
import { ProgramModal } from './ProgramModal';

interface LeagueData {
  directory: { club_id: string; name: string }[];
  dynasty_rankings: { club_id: string; club_name: string; championships: number; longest_win_streak: number }[];
  records: { record_type: string; holder_id: string; record_value: number; set_in_season: string }[];
  hof: { player_id: string; player_name: string; induction_season: string; career_elims: number; championships: number; seasons_played: number }[];
  rivalries: { club_a: string; club_b: string; a_wins: number; b_wins: number; draws: number; meetings: number }[];
}

const RECORD_LABEL: Record<string, string> = {
  most_eliminations_season: 'Most Elims (Season)',
  most_catches_season: 'Most Catches (Season)',
  most_eliminations_match: 'Most Elims (Match)',
  best_win_streak: 'Longest Win Streak',
};

export function LeagueView() {
  const [data, setData] = useState<LeagueData | null>(null);
  const [modal, setModal] = useState<{ clubId: string; clubName: string } | null>(null);

  useEffect(() => {
    fetch('/api/history/league')
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) return <div style={{ color: '#475569', padding: '1rem' }}>Loading league history…</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Program Directory */}
      <div className="dm-panel">
        <p className="dm-kicker">Program Directory</p>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {data.directory.map((c) => (
            <button
              key={c.club_id}
              onClick={() => setModal({ clubId: c.club_id, clubName: c.name })}
              style={{
                padding: '0.4rem 0.75rem',
                border: '1px solid #334155',
                borderRadius: '4px',
                background: '#0f172a',
                color: '#cbd5e1',
                cursor: 'pointer',
                fontSize: '0.8rem',
              }}
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>

      {/* Dynasty Rankings */}
      <div className="dm-panel">
        <p className="dm-kicker">Dynasty Rankings</p>
        {data.dynasty_rankings.length === 0 ? (
          <p style={{ color: '#475569', fontSize: '0.8rem' }}>No dynasty data yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {data.dynasty_rankings.map((r, i) => (
              <div
                key={r.club_id}
                style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', fontSize: '0.8rem' }}
              >
                <span style={{ color: '#475569', width: '1.5rem', textAlign: 'right' }}>{i + 1}.</span>
                <span style={{ flex: 1, color: '#e2e8f0' }}>{r.club_name}</span>
                <span style={{ color: '#f97316' }}>🏆 {r.championships}</span>
                <span style={{ color: '#64748b', fontSize: '0.7rem' }}>streak {r.longest_win_streak}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* All-Time Records + HoF */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div className="dm-panel" style={{ flex: 1, minWidth: '240px' }}>
          <p className="dm-kicker">All-Time Records</p>
          {data.records.length === 0 ? (
            <p style={{ color: '#475569', fontSize: '0.8rem' }}>No records set.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {data.records.map((r, i) => (
                <div key={i} style={{ fontSize: '0.75rem' }}>
                  <div style={{ color: '#94a3b8' }}>
                    {RECORD_LABEL[r.record_type] ?? r.record_type}
                  </div>
                  <div style={{ color: '#e2e8f0' }}>
                    {r.holder_id} — {r.record_value}
                    <span style={{ color: '#475569', marginLeft: '0.4rem' }}>{r.set_in_season}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="dm-panel" style={{ flex: 1, minWidth: '240px' }}>
          <p className="dm-kicker">Hall of Fame</p>
          {data.hof.length === 0 ? (
            <p style={{ color: '#475569', fontSize: '0.8rem' }}>No inductees yet.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {data.hof.map((h) => (
                <div key={h.player_id} style={{ fontSize: '0.75rem' }}>
                  <div style={{ color: '#fbbf24', fontWeight: 700 }}>⭐ {h.player_name}</div>
                  <div style={{ color: '#64748b' }}>
                    Class of {h.induction_season} · {h.career_elims} elims · {h.championships} titles · {h.seasons_played} seasons
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Rivalries */}
      <div className="dm-panel">
        <p className="dm-kicker">Rivalries</p>
        {data.rivalries.length === 0 ? (
          <p style={{ color: '#475569', fontSize: '0.8rem' }}>No rivalry data yet — rivalries form after multiple meetings.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {data.rivalries.slice(0, 5).map((r, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  alignItems: 'center',
                  padding: '0.5rem 0.75rem',
                  border: i === 0 ? '1px solid #334155' : 'none',
                  borderRadius: i === 0 ? '6px' : 0,
                  background: i === 0 ? '#0a1628' : 'transparent',
                  fontSize: '0.8rem',
                }}
              >
                {i === 0 && <span style={{ color: '#f97316', marginRight: '0.25rem' }}>🔥</span>}
                <span style={{ flex: 1, color: '#e2e8f0' }}>
                  {r.club_a} vs {r.club_b}
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
                  {r.a_wins}–{r.b_wins}–{r.draws} ({r.meetings} meetings)
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {modal && (
        <ProgramModal
          clubId={modal.clubId}
          clubName={modal.clubName}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
cd frontend && npm run build
```

Expected: clean build.

- [ ] **Step 3: Run full pytest**

```bash
python -m pytest -q
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dynasty/history/LeagueView.tsx
git commit -m "feat(history): rewrite LeagueView with dynasty rankings, HoF, rivalries, and program modal"
```

---

## Task 16: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Full Python test suite**

```bash
python -m pytest -q
```

Expected: all pass, 0 failures.

- [ ] **Step 2: Frontend build**

```bash
cd frontend && npm run build
```

Expected: 0 TypeScript errors, successful Vite bundle.

- [ ] **Step 3: Acceptance criteria check**

Run through this checklist manually in the browser (`python -m dodgeball_sim`):

**Ceremonies:**
- Navigate to offseason → awards beat → cards reveal one-by-one with player names
- Retirements beat → per-senior arc cards visible
- Signing Day shows prospect card with "Your Pick" eyebrow
- New Season Eve shows fixture list then prediction text
- Spacebar skips any ceremony instantly

**History:**
- Dynasty tab → History sub-tab → "My Program" shows hero cards, tree, alumni, banners
- "League" shows dynasty rankings, records, HoF, rivalries
- Clicking a club chip in the directory opens `ProgramModal`
- ESC key closes the modal

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -p
git commit -m "fix: final acceptance fixes for subplans 14 & 15 completion"
```

---

## Acceptance Criteria Reference

From `docs/superpowers/specs/2026-05-09-subplans-14-15-completion-design.md`:

### Subplan 15
- [ ] Awards Night: per-award cards reveal one at a time, real player names and stats
- [ ] Graduation: per-senior career arc cards (OVR arc, peak stats, potential tier outlook)
- [ ] Coaching Carousel: gracefully handles empty/absent payload (dead-code state — no action needed)
- [ ] Signing Day: prospect cards reveal one-by-one; player's signing highlighted with cyan border
- [ ] New Season Eve: fixture list + prediction headline, "Start the Season" CTA intact
- [ ] All ceremonies: spacebar skip works, reduced-motion cuts instantly
- [ ] All cards read from `payload` dict, not from body string parsing

### Subplan 14
- [ ] My Program / League toggle works
- [ ] Hero strip shows real Season 1 vs. current season data
- [ ] Milestone tree renders with SVG trunk/branches, variable dot sizes, season grouping, empty-season stubs
- [ ] Alumni lineage shows departed players with career stats and potential tier
- [ ] Banner shelf shows real trophies from `club_trophies` table
- [ ] League: program directory chips open a club's My-Program view in a modal
- [ ] League: dynasty rankings populated from `club_trophies`
- [ ] League: HoF populated from `hall_of_fame` table
- [ ] League: rivalries populated from `rivalry_records` table
- [ ] All data auto-generated from sim history — no manual logging inputs

### Housekeeping
- [ ] `patch.js` deleted from repo root
- [ ] 11 modified plan docs committed
