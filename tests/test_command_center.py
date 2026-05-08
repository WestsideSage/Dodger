from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.command_center import (
    build_command_center_state,
    build_default_weekly_plan,
    build_post_week_dashboard,
)
from dodgeball_sim.copy_quality import has_unresolved_token
from dodgeball_sim.game_loop import simulate_scheduled_match
from dodgeball_sim.persistence import (
    create_schema,
    get_schema_version,
    load_all_rosters,
    load_clubs,
    load_command_history,
    load_completed_match_ids,
    load_department_heads,
    load_season,
    save_command_history_record,
    save_weekly_command_plan,
)
from dodgeball_sim.view_models import normalize_root_seed


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_v5_schema_creates_department_plan_and_history_tables():
    conn = _career_conn()

    assert get_schema_version(conn) == 13
    assert load_department_heads(conn)
    assert conn.execute("SELECT COUNT(*) FROM weekly_command_plans").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM command_history").fetchone()[0] == 0


def test_weekly_plan_and_command_history_round_trip_json_payloads():
    conn = _career_conn()
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state)

    save_weekly_command_plan(conn, plan)
    save_command_history_record(
        conn,
        {
            "season_id": plan["season_id"],
            "week": plan["week"],
            "match_id": "demo-match",
            "opponent_club_id": plan["opponent"]["club_id"],
            "intent": plan["intent"],
            "plan": plan,
            "dashboard": {"lanes": [{"title": "Result", "summary": "Demo"}]},
        },
    )
    conn.commit()

    history = load_command_history(conn, plan["season_id"])
    assert history[0]["intent"] == "Win Now"
    assert history[0]["plan"]["department_orders"]["training"] == "fundamentals"
    assert history[0]["dashboard"]["lanes"][0]["title"] == "Result"


def test_command_center_default_plan_includes_staff_recommendations_and_warnings():
    conn = _career_conn()
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state)

    assert plan["intent"] == "Win Now"
    assert plan["recommendations"]
    assert "tactics" in plan["department_orders"]
    assert plan["lineup"]["player_ids"]
    assert plan["tactics"]["target_stars"] >= 0.0


def test_post_week_dashboard_is_derived_from_persisted_match_facts():
    conn = _career_conn()
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state)
    season = load_season(conn, plan["season_id"])
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    completed = load_completed_match_ids(conn, plan["season_id"])
    user_match = next(
        match
        for match in season.scheduled_matches
        if match.match_id not in completed
        and plan["player_club_id"] in (match.home_club_id, match.away_club_id)
    )

    record = simulate_scheduled_match(
        conn,
        scheduled=user_match,
        clubs=clubs,
        rosters=rosters,
        root_seed=normalize_root_seed("20260426", default_on_invalid=True),
        difficulty="pro",
    )
    dashboard = build_post_week_dashboard(conn, plan, record)

    assert dashboard["match_id"] == record.match_id
    assert {lane["title"] for lane in dashboard["lanes"]} >= {
        "Result",
        "Why it happened",
        "Roster health",
        "Player movement",
        "Next decisions",
    }
    assert any("pressure" in item.lower() or "plan" in item.lower() for item in dashboard["lanes"][1]["items"])


def test_post_week_dashboard_copy_is_player_facing_not_raw_tuning_output():
    conn = _career_conn()
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state)
    season = load_season(conn, plan["season_id"])
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    completed = load_completed_match_ids(conn, plan["season_id"])
    user_match = next(
        match
        for match in season.scheduled_matches
        if match.match_id not in completed
        and plan["player_club_id"] in (match.home_club_id, match.away_club_id)
    )

    record = simulate_scheduled_match(
        conn,
        scheduled=user_match,
        clubs=clubs,
        rosters=rosters,
        root_seed=normalize_root_seed("20260426", default_on_invalid=True),
        difficulty="pro",
    )
    dashboard = build_post_week_dashboard(conn, plan, record)
    visible_copy = [
        text
        for lane in dashboard["lanes"]
        for text in [lane["title"], lane["summary"], *lane["items"]]
    ]

    assert not any(has_unresolved_token(text) for text in visible_copy)
    assert not any("setting:" in text.lower() for text in visible_copy)
    assert not any("target-stars" in text.lower() for text in visible_copy)
