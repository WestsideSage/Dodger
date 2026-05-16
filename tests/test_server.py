from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from dodgeball_sim import server
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.copy_quality import has_unresolved_token
from dodgeball_sim.persistence import (
    create_schema,
    load_all_rosters,
    load_command_history,
    load_clubs,
    load_career_state_cursor,
    load_completed_match_ids,
    load_lineup_default,
    load_playoff_bracket,
    load_season,
    load_season_outcome,
    save_command_history_record,
    save_career_state_cursor,
    save_club,
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


def test_standings_endpoint_surfaces_latest_visible_ai_approach():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.execute(
        """
        INSERT INTO weekly_command_plans
            (season_id, week, club_id, intent, plan_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "season_1",
            1,
            "northwood",
            "Prepare For Playoffs",
            '{"season_id":"season_1","week":1,"player_club_id":"northwood","intent":"Prepare For Playoffs"}',
            "2026-05-15T00:00:00Z",
        ),
    )
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).get("/api/standings")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    northwood = next(row for row in response.json()["standings"] if row["club_id"] == "northwood")
    assert northwood["latest_approach"] == "Prepare For Playoffs"


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


def test_sim_week_persists_ai_weekly_plans_for_non_user_clubs():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).post("/api/sim/week")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    rows = conn.execute(
        "SELECT club_id, intent FROM weekly_command_plans WHERE season_id = 'season_1' AND week = 1"
    ).fetchall()
    assert any(row["club_id"] != "aurora" and row["intent"] for row in rows)


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
    assert replay_payload["proof_events"]
    assert replay_payload["key_play_indices"]
    assert replay_payload["report"]["winner_name"]
    assert replay_payload["report"]["top_performers"]
    assert replay_payload["report"]["evidence_lanes"]
    assert acknowledged.status_code == 200
    assert load_career_state_cursor(conn).state == CareerState.SEASON_ACTIVE_PRE_MATCH


def test_command_center_match_replay_includes_saved_plan_evidence():
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
        simulated = client.post(
            "/api/command-center/simulate",
            json={"intent": "Prepare For Playoffs"},
        )
        match_id = simulated.json()["dashboard"]["match_id"]
        replay = client.get(f"/api/matches/{match_id}/replay")
    finally:
        server.app.dependency_overrides.clear()

    assert simulated.status_code == 200
    assert replay.status_code == 200
    lanes = {lane["title"]: lane for lane in replay.json()["report"]["evidence_lanes"]}
    assert lanes["Command plan"]["summary"] == "Intent: Prepare For Playoffs."
    assert any("sync throws" in item.lower() for item in lanes["Command plan"]["items"])


def test_match_replay_report_copy_does_not_expose_raw_ids_or_tuning_labels():
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
        simulated = client.post(
            "/api/command-center/simulate",
            json={"intent": "Prepare For Playoffs"},
        )
        match_id = simulated.json()["dashboard"]["match_id"]
        replay = client.get(f"/api/matches/{match_id}/replay")
    finally:
        server.app.dependency_overrides.clear()

    assert simulated.status_code == 200
    assert replay.status_code == 200
    lanes = replay.json()["report"]["evidence_lanes"]
    visible_copy = [
        text
        for lane in lanes
        for text in [lane["title"], lane["summary"], *lane["items"]]
    ]

    assert not any(has_unresolved_token(text) for text in visible_copy)
    assert not any("policy snapshot" in text.lower() for text in visible_copy)
    assert not any("rush frequency" in text.lower() for text in visible_copy)
    assert not any("target stars:" in text.lower() for text in visible_copy)


def test_command_center_simulation_completes_the_full_schedule_week():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    season = load_season(conn, "season_1")
    week_one_ids = {match.match_id for match in season.matches_for_week(1)}
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).post(
            "/api/command-center/simulate",
            json={"intent": "Win Now"},
        )
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert week_one_ids <= load_completed_match_ids(conn, "season_1")
    assert load_career_state_cursor(conn).week == 2


def test_dynasty_office_corrupt_state_returns_recoverable_conflict():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.execute(
        "INSERT OR REPLACE INTO dynasty_state (key, value) VALUES (?, ?)",
        ("program_promises_json", "NOT JSON {{{"),
    )
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app, raise_server_exceptions=False).get("/api/dynasty-office")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "dynasty state" in response.json()["detail"]


def test_save_load_rejects_path_outside_managed_saves_and_keeps_active_save(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    legacy_path = tmp_path / "dodgeball_sim.db"
    managed_path = saves_dir / "managed.db"
    outside_path = tmp_path / "not-a-save.txt"
    saves_dir.mkdir()
    outside_path.write_text("not sqlite", encoding="utf-8")

    conn = sqlite3.connect(managed_path)
    conn.close()

    monkeypatch.setattr(server, "SAVES_DIR", saves_dir)
    monkeypatch.setattr(server, "DEFAULT_DB_PATH", legacy_path)
    original_save_path = server._active_save_path
    server._active_save_path = managed_path
    try:
        response = TestClient(server.app).post("/api/saves/load", json={"path": str(outside_path)})
    finally:
        active_after = server._active_save_path
        server._active_save_path = original_save_path

    assert response.status_code == 400
    assert active_after == managed_path


def test_save_delete_rejects_path_outside_managed_saves_without_unlinking(tmp_path, monkeypatch):
    saves_dir = tmp_path / "saves"
    legacy_path = tmp_path / "dodgeball_sim.db"
    outside_path = tmp_path / "delete-victim.txt"
    saves_dir.mkdir()
    outside_path.write_text("keep me", encoding="utf-8")

    monkeypatch.setattr(server, "SAVES_DIR", saves_dir)
    monkeypatch.setattr(server, "DEFAULT_DB_PATH", legacy_path)

    response = TestClient(server.app).post("/api/saves/delete", json={"path": str(outside_path)})

    assert response.status_code == 400
    assert outside_path.exists()


def test_dynasty_office_endpoint_exposes_remaining_milestone_loops_and_actions():
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
        office = client.get("/api/dynasty-office")
        prospect_id = office.json()["recruiting"]["prospects"][0]["player_id"]
        promised = client.post(
            "/api/dynasty-office/promises",
            json={"player_id": prospect_id, "promise_type": "early_playing_time"},
        )
        candidate_id = office.json()["staff_market"]["candidates"][0]["candidate_id"]
        hired = client.post(
            "/api/dynasty-office/staff/hire",
            json={"candidate_id": candidate_id},
        )
    finally:
        server.app.dependency_overrides.clear()

    assert office.status_code == 200
    payload = office.json()
    assert payload["recruiting"]["credibility"]["grade"]
    assert payload["league_memory"]["records"]["items"]
    assert payload["staff_market"]["candidates"]
    assert promised.status_code == 200
    assert promised.json()["recruiting"]["active_promises"][0]["player_id"] == prospect_id
    assert hired.status_code == 200
    assert hired.json()["staff_market"]["recent_actions"][0]["candidate_id"] == candidate_id


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


def test_command_center_repairs_depleted_ai_roster_before_simulation():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    season = load_season(conn, "season_1")
    first_user_match = next(
        match
        for match in season.scheduled_matches
        if "aurora" in (match.home_club_id, match.away_club_id)
    )
    depleted_club_id = (
        first_user_match.away_club_id
        if first_user_match.home_club_id == "aurora"
        else first_user_match.home_club_id
    )
    save_club(conn, clubs[depleted_club_id], [])
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        response = TestClient(server.app).post("/api/command-center/simulate")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(load_all_rosters(conn)[depleted_club_id]) >= 6


def test_command_center_simulate_enters_offseason_when_no_user_match_remains():
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
        for _ in range(10):
            response = client.post("/api/command-center/simulate")
            if response.status_code == 200 and response.json()["next_state"] == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT.value:
                break
            assert response.status_code == 200
        else:
            response = client.post("/api/command-center/simulate")
    finally:
        server.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["next_state"] == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT.value
    assert load_career_state_cursor(conn).state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT


def test_command_center_completes_ai_schedule_and_persists_playoff_champion():
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
        for _ in range(20):
            response = client.post("/api/command-center/simulate")
            assert response.status_code == 200
            payload = response.json()
            if payload["next_state"] == CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING.value:
                match_id = payload["dashboard"]["match_id"]
                replay = client.get(f"/api/matches/{match_id}/replay")
                assert replay.status_code == 200
                ack = client.post(f"/api/matches/{match_id}/acknowledge")
                assert ack.status_code == 200
                continue
            if payload["next_state"] == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT.value:
                break
        else:
            raise AssertionError("Command Center did not reach offseason")
    finally:
        server.app.dependency_overrides.clear()

    assert load_playoff_bracket(conn, "season_1") is not None
    assert load_season_outcome(conn, "season_1") is not None


def test_command_center_api_sanitizes_legacy_dashboard_copy_from_saved_history():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "harbor", root_seed=20260426)
    save_command_history_record(
        conn,
        {
            "season_id": "season_1",
            "week": 2,
            "match_id": "legacy-match",
            "opponent_club_id": "solstice",
            "intent": "Win Now",
            "plan": {"intent": "Win Now", "player_club_id": "harbor"},
            "dashboard": {
                "season_id": "season_1",
                "week": 2,
                "match_id": "legacy-match",
                "opponent_name": "Solstice Flare",
                "result": "Loss",
                "lanes": [
                    {
                        "title": "Why it happened",
                        "summary": "Tactical diagnosis correlates execution metrics to the mandated game plan.",
                        "items": [
                            "Target evidence: harbor_3 was targeted 6 times.",
                            "Tactical target-stars setting: 0.75.",
                            "Rush frequency setting: 0.35.",
                        ],
                    }
                ],
            },
        },
    )
    conn.commit()

    def override_db():
        yield conn

    server.app.dependency_overrides[server.get_db] = override_db
    try:
        client = TestClient(server.app)
        loaded = client.get("/api/command-center")
        history = client.get("/api/command-center/history")
    finally:
        server.app.dependency_overrides.clear()

    assert loaded.status_code == 200
    assert history.status_code == 200
    visible_copy = [
        text
        for payload in (loaded.json()["latest_dashboard"], history.json()[0]["dashboard"])
        for lane in payload["lanes"]
        for text in [lane["title"], lane["summary"], *lane["items"]]
    ]
    assert not any(has_unresolved_token(text) for text in visible_copy)
    assert not any("target evidence" in text.lower() for text in visible_copy)
    assert not any("target-stars" in text.lower() for text in visible_copy)
    assert not any("setting:" in text.lower() for text in visible_copy)
