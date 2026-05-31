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

def test_training_staff_exposes_modifier_pct(tmp_path):
    """Training head with rating 75 → modifier_pct ≥ 0 and > 0.
    Rating 50 → modifier_pct == 0. Other departments → no modifier_pct key (or None)."""
    from dodgeball_sim import persistence
    from dodgeball_sim.staff_market import build_staff_market_state
    from dodgeball_sim.persistence import create_schema

    db = tmp_path / "staff_mod.db"
    conn = persistence.connect(str(db))
    create_schema(conn)
    # Clear default seeded departments for the test
    conn.execute("DELETE FROM department_heads")
    conn.execute(
        "INSERT INTO department_heads (department, name, rating_primary, rating_secondary, voice)"
        " VALUES (?, ?, ?, ?, ?)",
        ("training", "Dev Head", 75, 60, "Reps build the ceiling."),
    )
    conn.execute(
        "INSERT INTO department_heads (department, name, rating_primary, rating_secondary, voice)"
        " VALUES (?, ?, ?, ?, ?)",
        ("tactics", "Tactic Head", 70, 55, "Make every matchup leave evidence."),
    )
    conn.commit()

    state = build_staff_market_state(
        conn, season_id="season_1", player_club_id="club_user", root_seed=7
    )

    training = next(m for m in state["current_staff"] if m["department"] == "training")
    tactics = next(m for m in state["current_staff"] if m["department"] == "tactics")

    assert "training_modifier_pct" in training
    assert isinstance(training["training_modifier_pct"], int)
    assert training["training_modifier_pct"] > 0  # rating 75 → ~8

    # Non-training departments must not claim a modifier.
    assert tactics.get("training_modifier_pct") is None or "training_modifier_pct" not in tactics

def test_training_modifier_pct_clamps_at_zero_below_baseline(tmp_path):
    """A training head rated exactly 50 → modifier 0% (no bonus, no penalty shown)."""
    from dodgeball_sim import persistence
    from dodgeball_sim.staff_market import build_staff_market_state
    from dodgeball_sim.persistence import create_schema

    db = tmp_path / "staff_clamp.db"
    conn = persistence.connect(str(db))
    create_schema(conn)
    conn.execute("DELETE FROM department_heads")
    conn.execute(
        "INSERT INTO department_heads (department, name, rating_primary, rating_secondary, voice)"
        " VALUES (?, ?, ?, ?, ?)",
        ("training", "Baseline Coach", 50, 50, "Baseline."),
    )
    conn.commit()

    state = build_staff_market_state(
        conn, season_id="season_1", player_club_id="club_user", root_seed=7
    )
    training = next(m for m in state["current_staff"] if m["department"] == "training")
    assert training["training_modifier_pct"] == 0
