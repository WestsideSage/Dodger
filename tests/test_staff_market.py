import sqlite3

from dodgeball_sim.staff_market import build_staff_market_state


def _seed_minimal(conn: sqlite3.Connection) -> None:
    # Department heads are stored as REAL; seed a fractional rating to prove
    # the payload coerces it to int on the way out. Schema already exists
    # because the connection came from persistence.connect() in the test.
    conn.execute(
        "UPDATE department_heads SET name=?, rating_primary=?, rating_secondary=?, voice=? WHERE department=?",
        ("Sam Reed", 72.4, 61.7, "Reps build the ceiling.", "training"),
    )
    conn.commit()


def test_staff_payload_ratings_are_integers(tmp_path):
    from dodgeball_sim import persistence
    from dodgeball_sim.persistence import create_schema

    db = tmp_path / "staff.db"
    conn = persistence.connect(str(db))
    create_schema(conn)
    _seed_minimal(conn)

    state = build_staff_market_state(
        conn, season_id="season_1", player_club_id="club_user", root_seed=7
    )

    for member in state["current_staff"]:
        assert isinstance(member["rating_primary"], int), member
        assert isinstance(member["rating_secondary"], int), member
    for candidate in state["candidates"]:
        assert isinstance(candidate["rating_primary"], int), candidate
        assert isinstance(candidate["rating_secondary"], int), candidate
        # No ".0" float text leaks into the effect lanes either.
        for lane in candidate["effect_lanes"]:
            assert ".0/" not in lane and not lane.endswith(".0")
            assert ".4" not in lane and ".7" not in lane
