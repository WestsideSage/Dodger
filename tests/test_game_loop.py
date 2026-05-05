from __future__ import annotations

import sqlite3

from dodgeball_sim.game_loop import (
    current_week,
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from dodgeball_sim.manager_gui import initialize_manager_career
from dodgeball_sim.persistence import (
    create_schema,
    fetch_roster_snapshot,
    load_all_rosters,
    load_clubs,
    load_completed_match_ids,
    load_season,
    load_standings,
)
from dodgeball_sim.lineup import STARTERS_COUNT


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    return conn


def test_simulate_scheduled_match_persists_record_stats_and_active_snapshot():
    conn = _conn()
    season = load_season(conn, "season_1")
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    match = season.scheduled_matches[0]

    record = simulate_scheduled_match(
        conn,
        scheduled=match,
        clubs=clubs,
        rosters=rosters,
        root_seed=20260426,
        difficulty="pro",
    )

    assert record.match_id in load_completed_match_ids(conn, season.season_id)
    assert conn.execute(
        "SELECT COUNT(*) FROM player_match_stats WHERE match_id = ?",
        (record.match_id,),
    ).fetchone()[0] > 0
    snapshot = fetch_roster_snapshot(conn, record.match_id, record.home_club_id)
    assert len([player for player in snapshot if player["match_role"] == "active"]) == STARTERS_COUNT


def test_current_week_and_recompute_standings_use_persisted_records():
    conn = _conn()
    season = load_season(conn, "season_1")
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    week_one = season.matches_for_week(1)

    for match in week_one:
        simulate_scheduled_match(
            conn,
            scheduled=match,
            clubs=clubs,
            rosters=rosters,
            root_seed=20260426,
            difficulty="pro",
        )
    recompute_regular_season_standings(conn, season)

    assert current_week(conn, season) == 2
    assert {row.club_id for row in load_standings(conn, season.season_id)} == set(clubs)
