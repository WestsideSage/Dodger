from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    create_schema,
    load_command_history,
    load_clubs,
    load_career_state_cursor,
    load_lineup_default,
    save_career_state_cursor,
)


def test_sim_week_endpoint_advances_frozen_cursor_without_mutation_error():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    save_career_state_cursor(
        conn,
        CareerStateCursor(
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            season_number=1,
            week=1,
        ),
    )
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).post("/api/sim/week")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["simulated_count"] > 0
    assert load_career_state_cursor(conn).week == 2


def test_status_endpoint_includes_player_club_display_name():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    club_name = load_clubs(conn)["aurora"].name
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).get("/api/status")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["context"]["player_club_id"] == "aurora"
    assert response.json()["context"]["player_club_name"] == club_name


def test_roster_endpoint_returns_players_and_default_lineup():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    expected_lineup = load_lineup_default(conn, "aurora")
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).get("/api/roster")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["club_id"] == "aurora"
    assert payload["default_lineup"] == expected_lineup
    assert [player["id"] for player in payload["roster"]][: len(expected_lineup)] == expected_lineup


def test_league_context_endpoints_return_display_ready_rows():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    club_name = load_clubs(conn)["aurora"].name
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        standings = client.get("/api/standings")
        schedule = client.get("/api/schedule")
        news = client.get("/api/news")
    finally:
        server.app.dependency_overrides.clear()

    assert standings.status_code == 200
    assert any(
        row["club_id"] == "aurora" and row["club_name"] == club_name and row["is_user_club"]
        for row in standings.json()["standings"]
    )
    assert schedule.status_code == 200
    assert schedule.json()["schedule"]
    assert {"home_club_name", "away_club_name", "status", "is_user_match"} <= set(schedule.json()["schedule"][0])
    assert news.status_code == 200
    assert "items" in news.json()


def test_sim_command_endpoint_supports_web_pacing_modes_and_updates_standings():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        response = client.post("/api/sim", json={"mode": "week"})
        standings = client.get("/api/standings")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["simulated_count"] > 0
    assert any(row["wins"] or row["losses"] or row["draws"] for row in standings.json()["standings"])


def test_user_match_enters_report_pending_and_exposes_replay_payload():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        response = client.post("/api/sim", json={"mode": "user_match"})
        status = client.get("/api/status")
        match_id = response.json()["match_id"]
        replay = client.get(f"/api/matches/{match_id}/replay")
        acknowledged = client.post(f"/api/matches/{match_id}/acknowledge")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["simulated_count"] == 1
    assert response.json()["next_state"] == CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING.value
    assert status.json()["state"]["state"] == CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING.value
    assert status.json()["state"]["match_id"] == match_id
    assert replay.status_code == 200
    replay_payload = replay.json()
    assert replay_payload["match_id"] == match_id
    assert replay_payload["events"]
    assert replay_payload["report"]["winner_name"]
    assert replay_payload["report"]["top_performers"]
    assert acknowledged.status_code == 200
    assert load_career_state_cursor(conn).state == CareerState.SEASON_ACTIVE_PRE_MATCH


def test_sim_command_rejects_non_active_lifecycle_states():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    save_career_state_cursor(
        conn,
        CareerStateCursor(
            state=CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            season_number=1,
            week=0,
        ),
    )
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).post("/api/sim", json={"mode": "week"})
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "season_active_pre_match" in response.json()["detail"]


def test_tactics_endpoint_rejects_non_finite_and_out_of_range_values():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        out_of_range = client.post(
            "/api/tactics",
            json={
                "target_stars": -1,
                "target_ball_holder": 0.5,
                "risk_tolerance": 0.5,
                "sync_throws": 0.5,
                "rush_frequency": 0.5,
                "rush_proximity": 0.5,
                "tempo": 0.5,
                "catch_bias": 0.5,
            },
        )
        nan_token = client.post(
            "/api/tactics",
            content=b'{"target_stars":NaN,"target_ball_holder":0.5,"risk_tolerance":0.5,"sync_throws":0.5,"rush_frequency":0.5,"rush_proximity":0.5,"tempo":0.5,"catch_bias":0.5}',
            headers={"content-type": "application/json"},
        )
    finally:
        server.app.dependency_overrides.clear()

    assert out_of_range.status_code == 422
    assert nan_token.status_code == 422


def test_roster_endpoint_reports_corrupt_roster_save_without_uncontrolled_500():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.execute("UPDATE club_rosters SET players_json = ? WHERE club_id = ?", ("{not json", "aurora"))
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app, raise_server_exceptions=False).get("/api/roster")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "roster save data is damaged" in response.json()["detail"]


def test_unknown_api_routes_return_404_not_spa_shell():
    response = TestClient(server.app).get("/api/replay/not-a-route")

    assert response.status_code == 404


def test_server_module_uses_web_safe_view_helpers():
    source = Path(server.__file__).read_text(encoding="utf-8")

    assert "dodgeball_sim.view_models" in source


def test_openapi_schema_names_existing_api_response_models():
    schema = TestClient(server.app).get("/openapi.json").json()
    components = schema["components"]["schemas"]

    assert {
        "StatusResponse",
        "RosterResponse",
        "TacticsResponse",
        "StandingsResponse",
        "ScheduleResponse",
        "NewsResponse",
        "SimResponse",
    } <= set(components)


def test_default_db_dependency_initializes_playable_web_career():
    import sqlite3 as _sqlite3
    db_path = Path("output") / "test_web_default_career.db"
    db_path.parent.mkdir(exist_ok=True)
    for candidate in (db_path, db_path.with_suffix(".db-wal"), db_path.with_suffix(".db-shm")):
        if candidate.exists():
            candidate.unlink()

    original_save_path = server._active_save_path
    conn = _sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = _sqlite3.Row
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    conn.close()
    server._active_save_path = db_path
    try:
        client = TestClient(server.app)
        responses = [
            client.get("/api/status"),
            client.get("/api/roster"),
            client.get("/api/tactics"),
            client.get("/api/standings"),
            client.get("/api/schedule"),
            client.get("/api/news"),
        ]
    finally:
        server._active_save_path = original_save_path
        for candidate in (db_path, db_path.with_suffix(".db-wal"), db_path.with_suffix(".db-shm")):
            if candidate.exists():
                candidate.unlink()

    assert [response.status_code for response in responses] == [200, 200, 200, 200, 200, 200]
    assert responses[0].json()["context"]["player_club_id"] == "aurora"


def test_command_center_endpoints_save_plan_simulate_and_record_dashboard():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        loaded = client.get("/api/command-center")
        saved = client.post("/api/command-center/plan", json={"intent": "Develop Youth"})
        simulated = client.post("/api/command-center/simulate")
        history = client.get("/api/command-center/history")
    finally:
        server.app.dependency_overrides.clear()

    assert loaded.status_code == 200
    assert loaded.json()["current_objective"]
    assert saved.status_code == 200
    assert saved.json()["plan"]["intent"] == "Develop Youth"
    assert simulated.status_code == 200
    assert simulated.json()["dashboard"]["lanes"]
    assert simulated.json()["next_state"] == CareerState.SEASON_ACTIVE_PRE_MATCH.value
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert load_command_history(conn, "season_1")[0]["dashboard"]["match_id"]
