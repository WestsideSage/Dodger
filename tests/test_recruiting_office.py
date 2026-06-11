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
    assert "2 wins and 0 losses across your career." in evidence
    assert "0 weeks spent prioritizing youth development." in evidence
    assert recruiting["credibility"]["score"] > 50

def _minimal_conn(tmp_path):
    import sqlite3
    from dodgeball_sim.persistence import create_schema
    from dodgeball_sim.career_setup import initialize_curated_manager_career
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=42)
    conn.commit()
    return conn


def test_ceiling_label_is_scout_gated_and_trajectory_true():
    """Playtest 3 elite reveal: the Scout action reveals the prospect's
    growth-arc grade — hidden until scouted, and when revealed it must be the
    exact coarse label of the hidden trajectory the development engine uses
    (the exact tier itself is never leaked)."""
    import json

    from dodgeball_sim.persistence import load_prospect_pool, set_state
    from dodgeball_sim.scouting_center import ceiling_label_for_trajectory

    conn = _minimal_conn(None)
    state = build_dynasty_office_state(conn)
    prospects = state["recruiting"]["prospects"]
    assert prospects, "career fixture should expose a prospect board"
    # Nothing scouted yet -> every grade hidden.
    assert all(row["ceiling_label"] is None for row in prospects)

    target_id = prospects[0]["player_id"]
    set_state(
        conn,
        "prospect_recruitment_actions_json",
        json.dumps({target_id: {"scouted": True}}),
    )
    conn.commit()

    refreshed = build_dynasty_office_state(conn)["recruiting"]["prospects"]
    scouted_row = next(row for row in refreshed if row["player_id"] == target_id)
    pool = {p.player_id: p for p in load_prospect_pool(conn, 1)}
    expected = ceiling_label_for_trajectory(pool[target_id].hidden_trajectory)
    assert scouted_row["ceiling_label"] == expected
    assert scouted_row["ceiling_label"] in {"HIGH_CEILING", "SOLID", "STANDARD"}
    # The raw trajectory tier must not ride along anywhere in the row.
    assert "trajectory" not in json.dumps(scouted_row).lower()
    # Unscouted prospects stay hidden.
    assert all(
        row["ceiling_label"] is None
        for row in refreshed
        if row["player_id"] != target_id
    )

def test_credibility_evidence_plain_language(tmp_path):
    """Evidence strings use plain language — no internal jargon like 'command week'."""
    conn = _minimal_conn(tmp_path)
    # Pass an empty history so the no-history edge case is also exercised.
    state = build_recruiting_state(
        conn,
        season_id="season_1",
        player_club_id="club_user",
        root_seed=42,
        history=[],
    )
    evidence = state["credibility"]["evidence"]
    # At least one item describes wins/losses in plain terms.
    assert any("wins" in e and "losses" in e for e in evidence)
    # No item leaks the internal "command" jargon.
    assert not any("command" in e.lower() for e in evidence)
    # Prestige item is present and uses the plain label.
    assert any("prestige" in e.lower() for e in evidence)
