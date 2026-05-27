from __future__ import annotations

import sqlite3
from pathlib import Path
import json

from dodgeball_sim.persistence import (
    CURRENT_SCHEMA_VERSION,
    create_schema,
    get_schema_version,
    migrate_schema,
    save_match_result,
    save_standings,
    load_standings,
    _migrate_v1,
)
from dodgeball_sim.season import SeasonResult, compute_standings


def test_migration_v15_schema_upgrade():
    # Verify that we can migrate from V1 schema to current schema (which is V15)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _migrate_v1(conn)

    # Perform migration up to CURRENT_SCHEMA_VERSION (15)
    migrate_schema(conn, 1, CURRENT_SCHEMA_VERSION)

    assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
    
    # Assert new columns exist in match_records
    match_cols = {row["name"] for row in conn.execute("PRAGMA table_info(match_records)")}
    assert "scoring_model" in match_cols
    assert "home_game_points" in match_cols
    assert "away_game_points" in match_cols
    assert "home_games_won" in match_cols
    assert "away_games_won" in match_cols
    assert "tied_games" in match_cols
    assert "no_point_games" in match_cols
    assert "official_score_json" in match_cols

    # Assert new columns exist in season_standings
    standings_cols = {row["name"] for row in conn.execute("PRAGMA table_info(season_standings)")}
    assert "game_points_for" in standings_cols
    assert "game_points_against" in standings_cols
    assert "game_point_differential" in standings_cols
    assert "total_game_points_scored" in standings_cols
    
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_legacy_saves_compatibility():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    # Insert a record using old match fields only (without the new fields)
    conn.execute(
        """
        INSERT INTO match_records (
            match_id, season_id, week, home_club_id, away_club_id,
            winner_club_id, home_survivors, away_survivors,
            home_roster_hash, away_roster_hash, config_version, ruleset_version,
            seed, event_log_hash, final_state_hash
        ) VALUES ('legacy_m', 'season_1', 1, 'club_a', 'club_b',
                 'club_a', 3, 0, 'hash1', 'hash2', 'legacy_config', 'legacy_rules',
                 123, 'log_h', 'state_h')
        """
    )
    
    # Verify we can fetch the row and it has default values for new columns
    row = conn.execute("SELECT * FROM match_records WHERE match_id = 'legacy_m'").fetchone()
    assert row["match_id"] == "legacy_m"
    assert row["scoring_model"] == "legacy"
    assert row["home_game_points"] == 0
    assert row["official_score_json"] is None


def test_legacy_standings_computation():
    # Legacy mode: winner based on survivor count, sorted by survivors differential
    res1 = SeasonResult(
        match_id="m1",
        season_id="s1",
        week=1,
        home_club_id="club_a",
        away_club_id="club_b",
        home_survivors=4,
        away_survivors=0,
        winner_club_id="club_a",
        seed=1,
        config_version="legacy",
    )
    res2 = SeasonResult(
        match_id="m2",
        season_id="s1",
        week=1,
        home_club_id="club_c",
        away_club_id="club_d",
        home_survivors=2,
        away_survivors=0,
        winner_club_id="club_c",
        seed=1,
        config_version="legacy",
    )
    # club_a has +4 diff, club_c has +2 diff. Both have 1 win (3 pts).
    standings = compute_standings([res1, res2])
    assert standings[0].club_id == "club_a"  # Sorted higher because of higher survivor differential
    assert standings[1].club_id == "club_c"


def test_official_standings_computation():
    # Official mode: sorted by game points first, not survivor differential!
    res1 = SeasonResult(
        match_id="m1",
        season_id="s1",
        week=1,
        home_club_id="club_a",
        away_club_id="club_b",
        home_survivors=1, # club_a won by only 1 survivor in the final game
        away_survivors=0,
        winner_club_id="club_a",
        seed=1,
        config_version="official:foam",
        home_game_points=8, # but won 8 games
        away_game_points=2,
    )
    res2 = SeasonResult(
        match_id="m2",
        season_id="s1",
        week=1,
        home_club_id="club_c",
        away_club_id="club_d",
        home_survivors=6, # club_c won by 6 survivors in the final game
        away_survivors=0,
        winner_club_id="club_c",
        seed=1,
        config_version="official:foam",
        home_game_points=4, # but won only 4 games
        away_game_points=1,
    )
    # Both have 1 win (3 pts).
    # Under legacy rules, club_c would be first because +6 survivors vs +1.
    # Under official rules, club_a should be first because 8 game points scored vs 4!
    standings = compute_standings([res1, res2])
    assert standings[0].club_id == "club_a"
    assert standings[1].club_id == "club_c"
