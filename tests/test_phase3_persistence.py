from __future__ import annotations

import sqlite3
from dataclasses import replace

from dodgeball_sim.models import PlayerTraits
from dodgeball_sim.persistence import (
    fetch_player_career_summary,
    initialize_schema,
    load_free_agents,
    load_retired_players,
    save_free_agents,
    save_player_season_stats,
    save_retired_player,
)
from dodgeball_sim.stats import PlayerMatchStats

from .factories import make_player


def test_free_agent_round_trip_and_retirement_storage():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)

    free_agents = [
        replace(make_player("fa_1", accuracy=70), club_id=None, newcomer=True),
        replace(make_player("fa_2", power=72), club_id=None, newcomer=False),
    ]
    save_free_agents(conn, free_agents, "season_2026")
    save_retired_player(conn, replace(make_player("retired_1"), age=39, traits=PlayerTraits()), "season_2025", "age_decline")
    conn.commit()

    assert load_free_agents(conn) == free_agents
    retired = load_retired_players(conn)
    assert len(retired) == 1
    assert retired[0]["player_id"] == "retired_1"
    assert retired[0]["final_season"] == "season_2025"


def test_player_season_stats_feed_career_summary():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)

    save_player_season_stats(
        conn,
        "season_2025",
        {
            "player_1": PlayerMatchStats(
                throws_attempted=10,
                eliminations_by_throw=6,
                catches_made=2,
                dodges_successful=3,
                times_eliminated=1,
            )
        },
        {"player_1": "club_a"},
        {"player_1": 4},
        frozenset({"player_1"}),
    )
    save_player_season_stats(
        conn,
        "season_2026",
        {
            "player_1": PlayerMatchStats(
                throws_attempted=9,
                eliminations_by_throw=5,
                catches_made=1,
                dodges_successful=2,
                times_eliminated=2,
            )
        },
        {"player_1": "club_a"},
        {"player_1": 4},
        frozenset(),
    )
    conn.commit()

    summary = fetch_player_career_summary(conn, "player_1")

    assert summary["seasons_played"] == 2.0
    assert summary["total_eliminations"] == 11.0
    assert summary["recent_eliminations"] == 5.0
