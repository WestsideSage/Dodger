from fastapi.testclient import TestClient
from dodgeball_sim.server import app
import sqlite3
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema
from dodgeball_sim import server

def test_matchup_details_payload():
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
        response = client.get('/api/command-center')
        assert response.status_code == 200
        plan = response.json()['plan']
        
        assert 'matchup_details' in plan
        details = plan['matchup_details']
        assert 'opponent_record' in details
        assert 'last_meeting' in details
        assert 'key_matchup' in details
        assert 'framing_line' in details

        sim = client.post('/api/command-center/simulate', json={'intent': 'Win Now'})
        assert sim.status_code == 200

        updated = client.get('/api/command-center')
        assert updated.status_code == 200
        updated_plan = updated.json()['plan']
        opponent_id = updated_plan['opponent']['club_id']
        standings = conn.execute(
            """
            SELECT wins, losses, draws
            FROM season_standings
            WHERE season_id = ? AND club_id = ?
            """,
            (updated.json()['season_id'], opponent_id),
        ).fetchone()
        assert standings is not None
        expected_record = (
            f"{standings['wins']}-{standings['losses']}"
            if standings['draws'] == 0
            else f"{standings['wins']}-{standings['losses']}-{standings['draws']}"
        )
        assert updated_plan['matchup_details']['opponent_record'] == expected_record
        assert updated_plan['matchup_details']['key_matchup'] != 'Opponent file unavailable.'
    finally:
        server.app.dependency_overrides.clear()
