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


def test_official_draw_replay_header_shows_game_points_not_survivors():
    """BUG #2: an official 1-1 game-points draw must surface 1-1 in the replay
    header, never the 0-0 survivor count.

    The replay header (``ReplayScoreboard``) renders ``home_game_points`` /
    ``away_game_points`` for official matches via the shared ``formatScoreline``
    helper. This pins the payload contract that makes that possible: an
    official draw where both sides finished with zero survivors still carries a
    non-legacy ``scoring_model`` and the real 1-1 game-point total, so the
    header can show 1-1 instead of the survivor 0-0 the playtester reported.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    club_a = Club("club_a", "Club A", "red/white", "North", 2020, CoachPolicy())
    club_b = Club("club_b", "Club B", "blue/gold", "South", 2020, CoachPolicy())
    save_club(conn, club_a, roster=[])
    save_club(conn, club_b, roster=[])

    conn.execute(
        """
        INSERT INTO matches (id, seed, config_version, winner_team_id, team_a_id, team_b_id, difficulty, setup_json, box_score_json, final_tick)
        VALUES (43, 123, 'official:foam', NULL, 'club_a', 'club_b', 'pro', '{}', '{"teams": {"club_a": {"totals": {"living": 0}}, "club_b": {"totals": {"living": 0}}}}', 150)
        """
    )
    conn.execute(
        """
        INSERT INTO match_roster_snapshots (match_id, club_id, players_json)
        VALUES ('match_draw', 'club_a', '[]'), ('match_draw', 'club_b', '[]')
        """
    )

    save_match_result(
        conn,
        match_id="match_draw",
        season_id="season_1",
        week=1,
        home_club_id="club_a",
        away_club_id="club_b",
        winner_club_id=None,  # a true draw: no winner
        home_survivors=0,  # both sides wiped out — survivor score is 0-0
        away_survivors=0,
        home_roster_hash="h1",
        away_roster_hash="h2",
        config_version="official:foam",
        ruleset_version="v1.0",
        seed=123,
        event_log_hash="event_h",
        final_state_hash="state_h",
        engine_match_id=43,
        scoring_model="foam",
        home_game_points=1,  # but the official result was a 1-1 game-points draw
        away_game_points=1,
        home_games_won=1,
        away_games_won=1,
        tied_games=0,
        no_point_games=0,
        official_score_json='{"team_a_game_points": 1}',
    )

    payload = match_replay_payload(conn, "match_draw")
    # The header keys off scoring_model to choose game points over survivors;
    # an official match must never be classified as legacy.
    assert payload["scoring_model"] == "foam"
    assert payload["scoring_model"] != "legacy"
    # The official game-point result the header renders: 1-1.
    assert payload["home_game_points"] == 1
    assert payload["away_game_points"] == 1
    # The survivor count (the misleading 0-0) is still present as supporting
    # detail, but it is NOT the figure the header headlines for official play.
    assert payload["home_survivors"] == 0
    assert payload["away_survivors"] == 0


def test_replay_response_model_serializes_official_scoring():
    """The /api/matches/{id}/replay RESPONSE must carry the official scoring.

    The two tests above pin ``match_replay_payload`` (the service). The route
    serializes through ``server.MatchReplayResponse``, and a Pydantic response
    model silently DROPS any field it does not declare — which is exactly what
    happened: the service built ``scoring_model``/game points, the model
    stripped them, and every official replay rendered as a legacy survivor
    scoreline in the browser (caught by tests/e2e/replay-score-parity.spec.ts
    once the token sweep let it run again). This pins the serialized shape.
    """
    from dodgeball_sim.server import MatchReplayResponse

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    club_a = Club("club_a", "Club A", "red/white", "North", 2020, CoachPolicy())
    club_b = Club("club_b", "Club B", "blue/gold", "South", 2020, CoachPolicy())
    save_club(conn, club_a, roster=[])
    save_club(conn, club_b, roster=[])

    conn.execute(
        """
        INSERT INTO matches (id, seed, config_version, winner_team_id, team_a_id, team_b_id, difficulty, setup_json, box_score_json, final_tick)
        VALUES (44, 123, 'official:foam', 'club_a', 'club_a', 'club_b', 'pro', '{}', '{"teams": {"club_a": {"totals": {"living": 2}}, "club_b": {"totals": {"living": 0}}}}', 150)
        """
    )
    conn.execute(
        """
        INSERT INTO match_roster_snapshots (match_id, club_id, players_json)
        VALUES ('match_ser', 'club_a', '[]'), ('match_ser', 'club_b', '[]')
        """
    )
    save_match_result(
        conn,
        match_id="match_ser",
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
        engine_match_id=44,
        scoring_model="foam",
        home_game_points=8,
        away_game_points=3,
        home_games_won=8,
        away_games_won=3,
        tied_games=0,
        no_point_games=1,
        official_score_json='{"team_a_game_points": 8}',
    )

    payload = match_replay_payload(conn, "match_ser")
    serialized = MatchReplayResponse(**payload).model_dump()
    assert serialized["scoring_model"] == "foam"
    assert serialized["home_game_points"] == 8
    assert serialized["away_game_points"] == 3
    assert serialized["home_games_won"] == 8
    assert serialized["away_games_won"] == 3
    assert serialized["tied_games"] == 0
    assert serialized["no_point_games"] == 1
