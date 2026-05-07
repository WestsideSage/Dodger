from __future__ import annotations

import sqlite3
from pathlib import Path

from dodgeball_sim.engine import MatchEngine
from dodgeball_sim.league import Club
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.persistence import (
    CorruptSaveError,
    CURRENT_SCHEMA_VERSION,
    StoredMatchSummary,
    _migrate_v1,
    create_schema,
    fetch_match,
    get_schema_version,
    initialize_schema,
    list_recent_matches,
    load_clubs,
    load_club_roster,
    load_lineup_default,
    load_match_lineup_override,
    migrate_schema,
    record_match,
    save_club,
    save_lineup_default,
    save_match_lineup_override,
    save_player_stats_batch,
)
from dodgeball_sim.stats import PlayerMatchStats

from .factories import make_match_setup, make_player, make_team


def _make_setup():
    team_a = make_team(
        "alpha",
        [make_player("a1", accuracy=70), make_player("a2", dodge=65)],
        policy=CoachPolicy(target_stars=0.7),
    )
    team_b = make_team(
        "beta",
        [make_player("b1", power=72), make_player("b2", catch=68)],
        policy=CoachPolicy(target_stars=0.7),
    )
    return make_match_setup(team_a, team_b)


def test_club_has_identity_fields():
    club = Club(
        club_id="aurora",
        name="Aurora Sentinels",
        colors="teal/charcoal",
        home_region="Northwest",
        founded_year=1998,
        coach_policy=CoachPolicy(),
        primary_color="#2E5E5C",
        secondary_color="#1F2933",
        venue_name="Aurora Field House",
        tagline="Power-arm aggression, deep scouting tradition",
    )
    assert club.primary_color == "#2E5E5C"
    assert club.secondary_color == "#1F2933"
    assert club.venue_name == "Aurora Field House"
    assert club.tagline == "Power-arm aggression, deep scouting tradition"


def test_club_identity_fields_default_to_empty():
    club = Club("legacy", "Legacy Club", "red/white", "North", 2020, CoachPolicy())
    assert club.primary_color == ""
    assert club.secondary_color == ""
    assert club.venue_name == ""
    assert club.tagline == ""


def test_v6_adds_club_identity_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cursor = conn.execute("PRAGMA table_info(clubs)")
    column_names = {row["name"] for row in cursor.fetchall()}
    assert "primary_color" in column_names
    assert "secondary_color" in column_names
    assert "venue_name" in column_names
    assert "tagline" in column_names
    assert get_schema_version(conn) >= 6


def test_save_load_club_roundtrip_includes_identity_fields():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    club = Club(
        club_id="aurora",
        name="Aurora Sentinels",
        colors="teal/charcoal",
        home_region="Northwest",
        founded_year=1998,
        coach_policy=CoachPolicy(),
        primary_color="#2E5E5C",
        secondary_color="#1F2933",
        venue_name="Aurora Field House",
        tagline="Power-arm aggression, deep scouting tradition",
    )
    save_club(conn, club, roster=[])

    loaded = load_clubs(conn)["aurora"]
    assert loaded.primary_color == "#2E5E5C"
    assert loaded.secondary_color == "#1F2933"
    assert loaded.venue_name == "Aurora Field House"
    assert loaded.tagline == "Power-arm aggression, deep scouting tradition"


def test_load_club_roster_raises_corrupt_save_error_for_bad_json():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    club = Club("aurora", "Aurora Sentinels", "teal/charcoal", "Northwest", 1998, CoachPolicy())
    save_club(conn, club, roster=[])
    conn.execute(
        "UPDATE club_rosters SET players_json = ? WHERE club_id = ?",
        ("[bad-json", "aurora"),
    )

    try:
        load_club_roster(conn, "aurora")
    except CorruptSaveError as exc:
        assert "aurora" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected CorruptSaveError")


def test_current_schema_version_is_thirteen():
    assert CURRENT_SCHEMA_VERSION == 13


def test_v1_database_migrates_to_current_schema():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _migrate_v1(conn)

    migrate_schema(conn, 1, CURRENT_SCHEMA_VERSION)

    assert get_schema_version(conn) == CURRENT_SCHEMA_VERSION
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {
        "matches",
        "clubs",
        "lineup_default",
        "prospect_pool",
        "recruitment_signing",
        "playoff_brackets",
        "season_outcomes",
        "season_formats",
    }.issubset(tables)
    club_columns = {row["name"] for row in conn.execute("PRAGMA table_info(clubs)")}
    assert {"primary_color", "secondary_color", "venue_name", "tagline"}.issubset(club_columns)
    prospect_columns = {row["name"] for row in conn.execute("PRAGMA table_info(prospect_pool)")}
    assert "is_signed" in prospect_columns
    stat_columns = {row["name"] for row in conn.execute("PRAGMA table_info(player_match_stats)")}
    assert "minutes_played" in stat_columns
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_save_player_stats_batch_persists_minutes_played():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    save_player_stats_batch(
        conn,
        "match_1",
        {"p1": PlayerMatchStats(throws_attempted=2, minutes_played=17)},
        {"p1": "aurora"},
    )

    row = conn.execute(
        "SELECT minutes_played FROM player_match_stats WHERE match_id = ? AND player_id = ?",
        ("match_1", "p1"),
    ).fetchone()
    assert row["minutes_played"] == 17


def test_v7_creates_lineup_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('lineup_default', 'match_lineup_override')"
    )
    names = {row["name"] for row in cursor.fetchall()}
    assert names == {"lineup_default", "match_lineup_override"}


def test_save_load_lineup_default_roundtrip():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    save_lineup_default(conn, "aurora", ["p3", "p1", "p4", "p1"])
    assert load_lineup_default(conn, "aurora") == ["p3", "p1", "p4", "p1"]


def test_load_lineup_default_returns_none_when_absent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    assert load_lineup_default(conn, "no_such_club") is None


def test_connect_enables_file_db_write_safety_pragmas():
    from dodgeball_sim.persistence import connect

    db_path = Path("output") / "test_write_safety.db"
    db_path.parent.mkdir(exist_ok=True)
    for candidate in (db_path, db_path.with_suffix(".db-wal"), db_path.with_suffix(".db-shm")):
        if candidate.exists():
            candidate.unlink()

    conn = connect(db_path)
    try:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    finally:
        conn.close()
        for candidate in (db_path, db_path.with_suffix(".db-wal"), db_path.with_suffix(".db-shm")):
            if candidate.exists():
                candidate.unlink()

    assert journal_mode.lower() == "wal"
    assert busy_timeout == 5000


def test_save_load_match_lineup_override_roundtrip():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    save_match_lineup_override(conn, "match_42", "aurora", ["p2", "p1"])
    assert load_match_lineup_override(conn, "match_42", "aurora") == ["p2", "p1"]


def test_load_match_lineup_override_returns_none_when_absent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    assert load_match_lineup_override(conn, "match_99", "aurora") is None


def test_record_and_fetch_match():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)

    setup = _make_setup()
    engine = MatchEngine()
    result = engine.run(setup, seed=42)

    match_id = record_match(conn, setup=setup, result=result, difficulty="pro")

    summaries = list_recent_matches(conn)
    assert len(summaries) == 1
    summary = summaries[0]
    assert isinstance(summary, StoredMatchSummary)
    assert summary.match_id == match_id
    assert summary.team_a_id == setup.team_a.id

    payload = fetch_match(conn, match_id)
    assert payload["box_score"] == result.box_score
    assert len(payload["events"]) == len(result.events)


def test_fetch_missing_match_raises():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)
    try:
        fetch_match(conn, 99)
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Expected KeyError")
