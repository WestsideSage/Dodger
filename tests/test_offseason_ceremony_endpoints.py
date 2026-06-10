import sqlite3
from fastapi.testclient import TestClient

from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_season,
    save_career_state_cursor,
    set_state,
)
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.offseason_ceremony import finalize_season, initialize_manager_offseason
from dodgeball_sim.offseason_presentation import load_active_beats
import dataclasses

def test_offseason_ceremony_payload():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    
    # Put save into offseason state
    cursor = load_career_state_cursor(conn)
    cursor = dataclasses.replace(cursor, state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0)
    save_career_state_cursor(conn, cursor)
    
    # Set dummy offseason JSONs so parsing doesn't fail
    set_state(conn, "offseason_records_json", '[]')
    set_state(conn, "offseason_hof_json", '[]')
    set_state(conn, "offseason_rookie_preview_json", '[]')
    set_state(conn, "offseason_development_json", '[]')
    set_state(conn, "offseason_retirements_json", '[]')
    
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        res = client.get("/api/offseason/beat")
        assert res.status_code == 200
        data = res.json()
        assert "beat_index" in data
        assert "key" in data
        assert "body" in data
    finally:
        app.dependency_overrides.clear()


def _disable_rival_bids(monkeypatch) -> None:
    """These endpoint tests assert the signing FLOW (counters, transitions),
    not contested-round odds: remove rival bidders entirely so every pick is
    STRUCTURALLY guaranteed to land, independent of balance constants (snipe
    odds are pinned in test_contested_offseason.py)."""
    from dodgeball_sim import recruitment

    monkeypatch.setattr(
        recruitment, "_eligible_ai_offer_clubs", lambda *args, **kwargs: set()
    )


def _enter_recruitment_state(conn: sqlite3.Connection) -> None:
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    finalize_season(conn, season, rosters)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)
    recruitment_index = load_active_beats(conn).index("recruitment")
    save_career_state_cursor(
        conn,
        CareerStateCursor(
            state=CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            season_number=1,
            week=0,
            offseason_beat_index=recruitment_index,
        ),
    )
    conn.commit()


def test_offseason_recruit_endpoint_allows_multiple_signings_then_skip(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    _enter_recruitment_state(conn)
    _disable_rival_bids(monkeypatch)

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        opening = client.get("/api/offseason/beat")
        prospect_id = opening.json()["payload"]["available_prospects"][0]["prospect_id"]

        signed = client.post("/api/offseason/recruit", json={"prospect_id": prospect_id})
        skipped = client.post("/api/offseason/recruit", json={"prospect_id": "skip"})
    finally:
        app.dependency_overrides.clear()

    assert opening.status_code == 200
    assert signed.status_code == 200
    assert signed.json()["state"] == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING.value
    assert signed.json()["can_recruit"] is True
    assert signed.json()["payload"]["signed_count"] == 1
    assert signed.json()["payload"]["remaining_signings"] == 2
    assert skipped.status_code == 200
    assert skipped.json()["state"] == CareerState.NEXT_SEASON_READY.value
    assert skipped.json()["can_recruit"] is False
    assert skipped.json()["can_begin_season"] is True


def test_offseason_recruit_endpoint_completes_after_third_signing(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    _enter_recruitment_state(conn)
    _disable_rival_bids(monkeypatch)
    roster_before = len(load_all_rosters(conn)["aurora"])

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        beat = client.get("/api/offseason/beat").json()
        for expected_count in (1, 2, 3):
            prospect_id = beat["payload"]["available_prospects"][0]["prospect_id"]
            response = client.post("/api/offseason/recruit", json={"prospect_id": prospect_id})
            assert response.status_code == 200
            beat = response.json()
            assert beat["payload"]["signed_count"] == expected_count
    finally:
        app.dependency_overrides.clear()

    assert beat["state"] == CareerState.NEXT_SEASON_READY.value
    assert beat["can_recruit"] is False
    assert beat["can_begin_season"] is True
    assert len(load_all_rosters(conn)["aurora"]) == roster_before + 3
