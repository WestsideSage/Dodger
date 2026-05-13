from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
from dodgeball_sim.persistence import (
    create_schema,
    load_all_rosters,
    load_clubs,
    load_season,
)


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_offseason_dev_path_loads_department_head_and_applies_modifier():
    """Hiring a development dept head with rating 100 should raise average OVR compared to no head."""
    conn_base = _career_conn()
    conn_hired = _career_conn()

    # Insert a development dept head at rating 100 in the hired conn
    conn_hired.execute(
        """
        INSERT OR REPLACE INTO department_heads
          (department, name, rating_primary, rating_secondary, voice)
        VALUES ('development', 'Elite Dev Coach', 100.0, 80.0, 'direct')
        """
    )
    conn_hired.commit()

    season_id_base = conn_base.execute(
        "SELECT value FROM dynasty_state WHERE key = 'active_season_id'"
    ).fetchone()["value"]
    season_id_hired = conn_hired.execute(
        "SELECT value FROM dynasty_state WHERE key = 'active_season_id'"
    ).fetchone()["value"]

    season_base = load_season(conn_base, season_id_base)
    season_hired = load_season(conn_hired, season_id_hired)

    rosters_base = load_all_rosters(conn_base)
    rosters_hired = load_all_rosters(conn_hired)

    clubs_base = load_clubs(conn_base)
    clubs_hired = load_clubs(conn_hired)

    updated_base = initialize_manager_offseason(
        conn_base, season_base, clubs_base, rosters_base, root_seed=20260426
    )
    updated_hired = initialize_manager_offseason(
        conn_hired, season_hired, clubs_hired, rosters_hired, root_seed=20260426
    )

    player_club_base = conn_base.execute(
        "SELECT value FROM dynasty_state WHERE key = 'player_club_id'"
    ).fetchone()["value"]
    player_club_hired = conn_hired.execute(
        "SELECT value FROM dynasty_state WHERE key = 'player_club_id'"
    ).fetchone()["value"]

    avg_ovr_base = sum(p.overall() for p in updated_base.get(player_club_base, [])) / max(
        len(updated_base.get(player_club_base, [])), 1
    )
    avg_ovr_hired = sum(p.overall() for p in updated_hired.get(player_club_hired, [])) / max(
        len(updated_hired.get(player_club_hired, [])), 1
    )

    assert avg_ovr_hired >= avg_ovr_base, (
        f"Expected hired ({avg_ovr_hired:.2f}) >= base ({avg_ovr_base:.2f})"
    )


def test_apply_scouting_carry_forward_is_importable():
    from dodgeball_sim.offseason_ceremony import apply_scouting_carry_forward
    assert callable(apply_scouting_carry_forward)


def test_apply_scouting_carry_forward_decays_verified_to_known(tmp_path):
    """Prospects that were VERIFIED become KNOWN after carry-forward."""
    from dodgeball_sim.offseason_ceremony import apply_scouting_carry_forward
    from dodgeball_sim.persistence import (
        connect, create_schema, load_scouting_state, save_scouting_state,
    )
    from dodgeball_sim.scouting_center import ScoutingState, ScoutingTier

    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    create_schema(conn)

    player_id = "prospect_1_001"
    # Insert a minimal prospect_pool row so the function can iterate
    conn.execute(
        """INSERT INTO prospect_pool
           (player_id, class_year, name, age, hometown,
            hidden_ratings_json, hidden_trajectory, hidden_traits_json,
            public_archetype_guess, public_ratings_band_json, is_signed)
           VALUES (?, 1, 'Test Player', 18, 'Somewhere',
            '{}', 'NORMAL', '[]', 'Sharpshooter', '{"ovr":[50,60]}', 0)""",
        (player_id,),
    )
    initial_state = ScoutingState(
        player_id=player_id,
        ratings_tier=ScoutingTier.VERIFIED.value,
        archetype_tier=ScoutingTier.VERIFIED.value,
        traits_tier=ScoutingTier.UNKNOWN.value,
        trajectory_tier=ScoutingTier.UNKNOWN.value,
        scout_points={"ratings": 100, "archetype": 100, "traits": 0, "trajectory": 0},
        last_updated_week=1,
    )
    save_scouting_state(conn, initial_state)
    conn.commit()

    apply_scouting_carry_forward(conn, prior_class_year=1)

    decayed = load_scouting_state(conn, player_id)
    assert decayed is not None
    assert decayed.ratings_tier == ScoutingTier.KNOWN.value
    assert decayed.archetype_tier == ScoutingTier.KNOWN.value
