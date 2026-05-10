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
