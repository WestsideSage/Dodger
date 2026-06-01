"""WT-3: the broadcast last-meeting scoreline shows game points for official
matches, survivors for legacy — so history agrees with the official scoreboard.
"""

import sqlite3

from dodgeball_sim.broadcast import _historical_hook, load_last_meeting


def _hook(meeting):
    return _historical_hook(
        player_club_id="P",
        opponent_club_id="O",
        rivalry_summary=None,
        last_meeting=meeting,
        stage_label="Regular Season",
    )


def test_official_last_meeting_shows_game_points_not_survivors():
    meeting = {
        "match_id": "m1", "week": 5, "winner_club_id": "P",
        "home_club_id": "P", "away_club_id": "O",
        "home_survivors": 1, "away_survivors": 3,
        "scoring_model": "foam", "home_game_points": 4, "away_game_points": 2,
    }
    hook = _hook(meeting)
    assert "4-2" in hook.text and "1-3" not in hook.text, hook.text
    assert "Win" in hook.text


def test_official_draw_reads_0_0_not_survivor_blowout():
    meeting = {
        "match_id": "m2", "week": 6, "winner_club_id": None,
        "home_club_id": "P", "away_club_id": "O",
        "home_survivors": 0, "away_survivors": 3,
        "scoring_model": "foam", "home_game_points": 0, "away_game_points": 0,
    }
    hook = _hook(meeting)
    assert "0-0" in hook.text and "0-3" not in hook.text, hook.text
    assert "Draw" in hook.text


def test_official_away_perspective_orders_player_score_first():
    meeting = {
        "match_id": "m3", "week": 7, "winner_club_id": "P",
        "home_club_id": "O", "away_club_id": "P",
        "home_survivors": 3, "away_survivors": 1,
        "scoring_model": "cloth", "home_game_points": 2, "away_game_points": 4,
    }
    hook = _hook(meeting)
    assert "4-2" in hook.text, hook.text  # player (away) 4, opponent 2


def test_legacy_last_meeting_still_uses_survivors():
    meeting = {
        "match_id": "m4", "week": 8, "winner_club_id": "P",
        "home_club_id": "P", "away_club_id": "O",
        "home_survivors": 5, "away_survivors": 2,
        "scoring_model": "legacy", "home_game_points": 0, "away_game_points": 0,
    }
    hook = _hook(meeting)
    assert "5-2" in hook.text, hook.text


def _conn(*, with_gp_columns):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cols = (
        "match_id TEXT, week INT, season_id TEXT, home_club_id TEXT, away_club_id TEXT, "
        "winner_club_id TEXT, home_survivors INT, away_survivors INT"
    )
    if with_gp_columns:
        cols += ", scoring_model TEXT, home_game_points INT, away_game_points INT"
    conn.execute(f"CREATE TABLE match_records ({cols})")
    return conn


def test_loader_returns_game_point_columns():
    conn = _conn(with_gp_columns=True)
    conn.execute(
        "INSERT INTO match_records VALUES ('m1',5,'s1','P','O','P',1,3,'foam',4,2)"
    )
    meeting = load_last_meeting(conn, season_id="s1", player_club_id="P", opponent_club_id="O")
    assert meeting is not None
    assert meeting["scoring_model"] == "foam"
    assert meeting["home_game_points"] == 4 and meeting["away_game_points"] == 2


def test_loader_falls_back_on_legacy_db_without_game_point_columns():
    conn = _conn(with_gp_columns=False)
    conn.execute("INSERT INTO match_records VALUES ('m1',5,'s1','P','O','P',5,2)")
    meeting = load_last_meeting(conn, season_id="s1", player_club_id="P", opponent_club_id="O")
    assert meeting is not None  # did not crash
    assert meeting["home_survivors"] == 5 and meeting["away_survivors"] == 2
