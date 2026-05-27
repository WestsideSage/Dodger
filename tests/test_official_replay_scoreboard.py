from __future__ import annotations

import sqlite3
import json

from dodgeball_sim.persistence import create_schema, save_match_result, save_club
from dodgeball_sim.replay_service import match_replay_payload, ReplayError
from dodgeball_sim.league import Club
from dodgeball_sim.models import CoachPolicy


def test_match_replay_payload_includes_official_scoring():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    # Save clubs
    club_a = Club("club_a", "Club A", "red/white", "North", 2020, CoachPolicy())
    club_b = Club("club_b", "Club B", "blue/gold", "South", 2020, CoachPolicy())
    save_club(conn, club_a, roster=[])
    save_club(conn, club_b, roster=[])

    # Save in matches table (so engine_match_id is resolved and exists)
    conn.execute(
        """
        INSERT INTO matches (id, seed, config_version, winner_team_id, team_a_id, team_b_id, difficulty, setup_json, box_score_json, final_tick)
        VALUES (42, 123, 'official:foam', 'club_a', 'club_a', 'club_b', 'pro', '{}', '{"teams": {"club_a": {"totals": {"living": 2}}, "club_b": {"totals": {"living": 0}}}}', 150)
        """
    )
    conn.execute(
        """
        INSERT INTO match_roster_snapshots (match_id, club_id, players_json)
        VALUES ('match_1', 'club_a', '[]'), ('match_1', 'club_b', '[]')
        """
    )

    # Save match record with official USAD scoring columns
    save_match_result(
        conn,
        match_id="match_1",
        season_id="season_1",
        week=1,
        home_club_id="club_a",
        away_club_id="club_b",
        winner_club_id="club_a",
        home_survivors=2,
        away_survivors=0,
        home_roster_hash="h1",
        away_roster_hash="h2",
        config_version="official:foam",
        ruleset_version="v1.0",
        seed=123,
        event_log_hash="event_h",
        final_state_hash="state_h",
        engine_match_id=42,
        scoring_model="foam",
        home_game_points=8,
        away_game_points=3,
        home_games_won=8,
        away_games_won=3,
        tied_games=0,
        no_point_games=1,
        official_score_json='{"team_a_game_points": 8}',
    )

    payload = match_replay_payload(conn, "match_1")
    assert payload["match_id"] == "match_1"
    assert payload["scoring_model"] == "foam"
    assert payload["home_game_points"] == 8
    assert payload["away_game_points"] == 3
    assert payload["home_games_won"] == 8
    assert payload["away_games_won"] == 3
    assert payload["tied_games"] == 0
    assert payload["no_point_games"] == 1
