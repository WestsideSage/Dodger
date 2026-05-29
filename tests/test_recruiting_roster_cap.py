"""A created roster at the creation maximum (10) must still be able to recruit.

Playtest finding: recruiting never signed anyone. Root cause was a cap mismatch
— club creation allows up to 10 players, but the offseason recruiting gate
required ``len(roster) < 9``. A custom club built with 9 or 10 players was
therefore permanently locked out of recruiting (``can_recruit`` false, so the
frontend showed the read-only Signing Day instead of the prospect picker).
"""
import dataclasses
import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim.server import app, get_db
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.offseason_ceremony import finalize_season, initialize_manager_offseason
from dodgeball_sim.offseason_presentation import load_active_beats
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_season,
    save_career_state_cursor,
    save_club,
)


def _pad_user_roster_to(conn: sqlite3.Connection, target: int) -> None:
    player_club_id = get_state(conn, "player_club_id")
    clubs = load_clubs(conn)
    roster = list(load_all_rosters(conn)[player_club_id])
    i = 0
    while len(roster) < target:
        base = roster[i % len(roster)]
        roster.append(dataclasses.replace(base, id=f"{base.id}_pad{i}", name=f"Depth {i}"))
        i += 1
    save_club(conn, clubs[player_club_id], roster)
    conn.commit()


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


def test_full_created_roster_can_still_recruit():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    _pad_user_roster_to(conn, 10)  # the creation maximum
    _enter_recruitment_state(conn)
    player_club_id = get_state(conn, "player_club_id")
    roster_before = len(load_all_rosters(conn)[player_club_id])
    assert roster_before == 10

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        beat = client.get("/api/offseason/beat").json()
        assert beat["can_recruit"] is True, "a 10-player created roster must still be able to recruit"

        prospect_id = beat["payload"]["available_prospects"][0]["prospect_id"]
        signed = client.post("/api/offseason/recruit", json={"prospect_id": prospect_id})
        assert signed.status_code == 200
        assert signed.json()["payload"]["signed_count"] == 1
    finally:
        app.dependency_overrides.clear()

    assert len(load_all_rosters(conn)[player_club_id]) == roster_before + 1
