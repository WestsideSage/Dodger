import sqlite3
from fastapi.testclient import TestClient
from dodgeball_sim.server import app, get_db
from dodgeball_sim.persistence import create_schema
from dodgeball_sim.career_setup import initialize_curated_manager_career

def test_standings_includes_recent_matches():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        # Advance the week to generate matches
        client.post("/api/sim", json={"mode": "week"})
        client.post("/api/sim", json={"mode": "week"})
        
        res = client.get('/api/standings')
        data = res.json()
        assert 'recent_matches' in data
        assert type(data['recent_matches']) == list
    finally:
        app.dependency_overrides.clear()


def test_standings_exposes_user_games_remaining():
    """The standings table must report the same games-remaining count the
    command center uses, so the two surfaces never contradict each other."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        before = client.get('/api/standings').json()['user_games_remaining']
        assert isinstance(before, int)
        assert before > 0
        client.post("/api/sim", json={"mode": "week"})
        after = client.get('/api/standings').json()['user_games_remaining']
        # Playing a user match must decrement the count (byes excluded).
        assert after < before
    finally:
        app.dependency_overrides.clear()
