from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.dynasty_office import (
    build_dynasty_office_state,
    hire_staff_candidate,
    save_recruiting_promise,
)
from dodgeball_sim.persistence import create_schema, load_department_heads


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
