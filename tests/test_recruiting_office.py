from __future__ import annotations

import sqlite3
from dodgeball_sim.persistence import create_schema, save_command_history_record, get_state
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.recruiting_office import build_recruiting_state
from dodgeball_sim.dynasty_office import build_dynasty_office_state


def test_credibility_counts_career_wins_across_seasons():
    """Audit 7.4: credibility must reflect career performance, not just the active season."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()

    player_club_id = "aurora"
    season_id = get_state(conn, "active_season_id")

    # Insert a win in season 1
    save_command_history_record(
        conn,
        {
            "season_id": season_id,
            "week": 1,
            "match_id": "m1",
            "opponent_club_id": "adversary",
            "intent": "Win Now",
            "plan": {"player_club_id": player_club_id},
            "dashboard": {"result": "Win"},
        },
    )
    # Insert another win in season 2 (career credibility spans seasons)
    save_command_history_record(
        conn,
        {
            "season_id": "season_2",
            "week": 1,
            "match_id": "m2",
            "opponent_club_id": "adversary",
            "intent": "Win Now",
            "plan": {"player_club_id": player_club_id},
            "dashboard": {"result": "Win"},
        },
    )
    conn.commit()

    # Now let's fetch the dynasty office state (which calls build_recruiting_state with all-seasons history)
    state = build_dynasty_office_state(conn)
    recruiting = state["recruiting"]

    evidence = " ".join(recruiting["credibility"]["evidence"])
    assert "2 career command-history wins and 0 losses." in evidence
    assert "0 youth-development command weeks across your career." in evidence
    assert recruiting["credibility"]["score"] > 50
