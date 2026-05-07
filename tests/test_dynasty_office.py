from __future__ import annotations

import json as _json
import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.dynasty_office import (
    build_dynasty_office_state,
    hire_staff_candidate,
    save_recruiting_promise,
)
from dodgeball_sim.persistence import create_schema, load_department_heads


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


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_dynasty_office_surfaces_v8_v9_v10_loops_without_fake_claims():
    conn = _career_conn()

    state = build_dynasty_office_state(conn)

    assert state["recruiting"]["credibility"]["score"] >= 0
    assert state["recruiting"]["prospects"]
    assert state["recruiting"]["prospects"][0]["promise_options"]
    assert state["league_memory"]["records"]["items"][0]["status"] == "limited"
    assert state["staff_market"]["current_staff"]
    assert state["staff_market"]["candidates"]
    assert state["staff_market"]["candidates"][0]["effect_lanes"]


def test_recruiting_promises_are_limited_and_persisted_as_truth():
    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    prospect_id = state["recruiting"]["prospects"][0]["player_id"]

    updated = save_recruiting_promise(conn, prospect_id, "early_playing_time")

    promises = updated["recruiting"]["active_promises"]
    assert promises == [
        {
            "player_id": prospect_id,
            "promise_type": "early_playing_time",
            "status": "open",
            "result": None,
            "result_season_id": None,
            "evidence": "Will be checked against future command history and player match stats.",
        }
    ]


def test_staff_hire_updates_department_head_and_records_visible_effects():
    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    candidate = state["staff_market"]["candidates"][0]
    before = {row["department"]: row for row in load_department_heads(conn)}

    updated = hire_staff_candidate(conn, candidate["candidate_id"])

    after = {row["department"]: row for row in load_department_heads(conn)}
    department = candidate["department"]
    assert after[department]["name"] == candidate["name"]
    assert after[department]["rating_primary"] >= before[department]["rating_primary"]
    assert updated["staff_market"]["recent_actions"][0]["candidate_id"] == candidate["candidate_id"]
    assert all(item["department"] != department for item in updated["staff_market"]["candidates"])


def test_ensure_dynasty_keys_initializes_missing_keys():
    from dodgeball_sim.dynasty_office import PROMISE_STATE_KEY, STAFF_ACTION_STATE_KEY
    conn = _career_conn()
    # Keys start absent — build_dynasty_office_state should not crash
    conn.execute("DELETE FROM dynasty_state WHERE key IN (?, ?)",
                 (PROMISE_STATE_KEY, STAFF_ACTION_STATE_KEY))
    conn.commit()

    state = build_dynasty_office_state(conn)
    assert state["recruiting"]["active_promises"] == []
    assert state["staff_market"]["recent_actions"] == []


def test_ensure_dynasty_keys_raises_on_corrupt_value():
    from dodgeball_sim.dynasty_office import _ensure_dynasty_keys
    from dodgeball_sim.persistence import CorruptSaveError
    conn = _career_conn()
    conn.execute(
        "INSERT OR REPLACE INTO dynasty_state (key, value) VALUES (?, ?)",
        ("program_promises_json", "NOT VALID JSON {{{"),
    )
    conn.commit()

    with pytest.raises(CorruptSaveError, match="Corrupted dynasty state key"):
        _ensure_dynasty_keys(conn)


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
    evaluate_season_promises(conn, season_id, club_id)  # second call must be idempotent

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


def _insert_dev_focus_history(conn, season_id, club_id, n_weeks, dev_focus="YOUTH_ACCELERATION"):
    """Insert n_weeks of command_history rows with the given dev_focus."""
    import json as j
    for week_num in range(1, n_weeks + 1):
        conn.execute(
            "INSERT INTO command_history (season_id, week, club_id, intent, plan_json, dashboard_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                season_id,
                week_num,
                club_id,
                "weekly_plan",
                j.dumps({"department_orders": {"dev_focus": dev_focus}}),
                j.dumps({}),
            ),
        )
    conn.commit()


def test_promise_development_priority_fulfilled_when_focused_weeks_and_on_roster():
    from dodgeball_sim.dynasty_office import evaluate_season_promises
    from dodgeball_sim.persistence import load_all_rosters

    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]

    rosters = load_all_rosters(conn)
    roster_player_id = rosters[club_id][0].id

    save_recruiting_promise(conn, roster_player_id, "development_priority")
    _insert_dev_focus_history(conn, season_id, club_id, n_weeks=3)

    evaluate_season_promises(conn, season_id, club_id)

    promises = _json.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    match = next(p for p in promises if p["player_id"] == roster_player_id)
    assert match["result"] == "fulfilled"


def test_promise_development_priority_broken_when_insufficient_focused_weeks():
    from dodgeball_sim.dynasty_office import evaluate_season_promises
    from dodgeball_sim.persistence import load_all_rosters

    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]

    rosters = load_all_rosters(conn)
    roster_player_id = rosters[club_id][0].id

    save_recruiting_promise(conn, roster_player_id, "development_priority")
    _insert_dev_focus_history(conn, season_id, club_id, n_weeks=2)

    evaluate_season_promises(conn, season_id, club_id)

    promises = _json.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    match = next(p for p in promises if p["player_id"] == roster_player_id)
    assert match["result"] == "broken"


def test_promise_development_priority_broken_when_player_not_on_roster():
    from dodgeball_sim.dynasty_office import evaluate_season_promises

    conn = _career_conn()
    state = build_dynasty_office_state(conn)
    season_id = state["season_id"]
    club_id = state["player_club_id"]

    save_recruiting_promise(conn, "nonexistent_player", "development_priority")
    _insert_dev_focus_history(conn, season_id, club_id, n_weeks=3)

    evaluate_season_promises(conn, season_id, club_id)

    promises = _json.loads(
        conn.execute(
            "SELECT value FROM dynasty_state WHERE key = 'program_promises_json'"
        ).fetchone()["value"]
    )
    match = next(p for p in promises if p["player_id"] == "nonexistent_player")
    assert match["result"] == "broken"


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
    assert match["result"] == "fulfilled"


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

    class_year = _class_year_from_season(season_id)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", str(class_year)))
    expected_pool = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
    expected_ids = [p.player_id for p in expected_pool[:8]]

    office_ids = [p["player_id"] for p in state["recruiting"]["prospects"]]

    assert office_ids == expected_ids
