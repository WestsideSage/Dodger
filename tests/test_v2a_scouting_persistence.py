import sqlite3

from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.persistence import (
    CURRENT_SCHEMA_VERSION,
    append_scouting_domain_event,
    create_schema,
    get_schema_version,
    load_all_scout_assignments,
    load_all_scouting_states,
    load_ceiling_label,
    load_prospect_pool,
    load_revealed_traits,
    load_scout_assignment,
    load_scout_contributions_for_season,
    load_scout_strategy,
    load_scout_track_records_for_scout,
    load_scouting_domain_events_for_season,
    load_scouting_state,
    load_scouts,
    migrate_schema,
    save_ceiling_label,
    save_prospect_pool,
    save_revealed_traits,
    save_scout_assignment,
    save_scout_strategy,
    save_scout_track_record,
    save_scouting_state,
    seed_default_scouts,
    upsert_scout_contribution,
)
from dodgeball_sim.recruitment import generate_prospect_pool
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.scouting_center import (
    ScoutAssignment,
    ScoutContribution,
    ScoutStrategyState,
    ScoutingState,
)


def test_schema_version_is_11():
    assert CURRENT_SCHEMA_VERSION == 13


def test_create_schema_creates_v2a_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    assert get_schema_version(conn) == 13

    expected_tables = {
        "prospect_pool",
        "scouting_state",
        "scouting_revealed_traits",
        "scouting_ceiling_label",
        "scout",
        "scout_assignment",
        "scout_strategy",
        "scout_prospect_contribution",
        "scout_track_record",
        "scouting_domain_event",
    }
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {row["name"] for row in rows}
    missing = expected_tables - table_names
    assert not missing, f"Missing V2-A tables: {missing}"


def test_v7_to_v10_migration_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    from dodgeball_sim.persistence import _MIGRATIONS, _set_schema_version

    for version in range(1, 8):
        _MIGRATIONS[version](conn)
    _set_schema_version(conn, 7)
    conn.commit()
    assert get_schema_version(conn) == 7

    migrate_schema(conn, 7, 10)
    assert get_schema_version(conn) == 10

    create_schema(conn)
    assert get_schema_version(conn) == 13


def test_prospect_pool_table_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cols = {row["name"]: row for row in conn.execute("PRAGMA table_info(prospect_pool)").fetchall()}
    assert "class_year" in cols
    assert "player_id" in cols
    assert "hidden_ratings_json" in cols
    assert "hidden_trajectory" in cols
    assert "hidden_traits_json" in cols
    assert "public_archetype_guess" in cols
    assert "public_ratings_band_json" in cols
    assert "is_signed" in cols


def test_scout_prospect_contribution_table_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cols = {
        row["name"]: row
        for row in conn.execute("PRAGMA table_info(scout_prospect_contribution)").fetchall()
    }
    expected = {
        "scout_id",
        "player_id",
        "season",
        "first_assigned_week",
        "last_active_week",
        "weeks_worked",
        "contributed_scout_points_json",
        "last_estimated_ratings_band_json",
        "last_estimated_archetype",
        "last_estimated_traits_json",
        "last_estimated_ceiling",
        "last_estimated_trajectory",
    }
    assert expected.issubset(cols.keys()), f"Missing columns: {expected - cols.keys()}"


def test_scouting_domain_event_table_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    cols = {
        row["name"]: row
        for row in conn.execute("PRAGMA table_info(scouting_domain_event)").fetchall()
    }
    expected = {"event_id", "season", "week", "event_type", "player_id", "scout_id", "payload_json"}
    assert expected.issubset(cols.keys())


def _setup_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def test_save_and_load_prospect_pool():
    conn = _setup_conn()
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    loaded = load_prospect_pool(conn, class_year=1)
    assert len(loaded) == len(pool)
    assert {p.player_id for p in loaded} == {p.player_id for p in pool}
    original = pool[0]
    roundtrip = next(p for p in loaded if p.player_id == original.player_id)
    assert roundtrip.hidden_trajectory == original.hidden_trajectory
    assert roundtrip.hidden_traits == original.hidden_traits


def test_seed_default_scouts_idempotent():
    conn = _setup_conn()
    seed_default_scouts(conn)
    first = load_scouts(conn)
    assert len(first) == 3
    assert {scout.scout_id for scout in first} == {"vera", "bram", "linnea"}
    seed_default_scouts(conn)
    assert len(load_scouts(conn)) == 3


def test_save_and_load_scouting_state():
    conn = _setup_conn()
    state = ScoutingState(
        player_id="prospect_1_001",
        ratings_tier="GLIMPSED",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 12, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=3,
    )
    save_scouting_state(conn, state)
    loaded = load_scouting_state(conn, "prospect_1_001")
    assert loaded is not None
    assert loaded.ratings_tier == "GLIMPSED"
    assert loaded.scout_points["ratings"] == 12
    assert load_all_scouting_states(conn)["prospect_1_001"].last_updated_week == 3


def test_save_and_load_scout_assignment():
    conn = _setup_conn()
    seed_default_scouts(conn)
    save_prospect_pool(
        conn,
        generate_prospect_pool(
            1,
            DeterministicRNG(derive_seed(20260426, "prospect_gen", "1")),
            DEFAULT_SCOUTING_CONFIG,
        ),
    )
    save_scout_assignment(conn, ScoutAssignment("vera", "prospect_1_005", 2))
    loaded = load_scout_assignment(conn, "vera")
    assert loaded is not None
    assert loaded.player_id == "prospect_1_005"
    assert loaded.started_week == 2
    assert load_all_scout_assignments(conn)["vera"].player_id == "prospect_1_005"


def test_save_scout_assignment_drops_unknown_player_and_clamps_week():
    conn = _setup_conn()
    seed_default_scouts(conn)

    save_scout_assignment(conn, ScoutAssignment("vera", "missing-prospect", -9))

    loaded = load_scout_assignment(conn, "vera")
    assert loaded is not None
    assert loaded.player_id is None
    assert loaded.started_week == 0


def test_save_and_load_scout_strategy():
    conn = _setup_conn()
    seed_default_scouts(conn)
    save_scout_strategy(
        conn,
        ScoutStrategyState("vera", "AUTO", "SPECIALTY_FIT", ("Enforcer",), ()),
    )
    loaded = load_scout_strategy(conn, "vera")
    assert loaded is not None
    assert loaded.mode == "AUTO"
    assert loaded.priority == "SPECIALTY_FIT"
    assert loaded.archetype_filter == ("Enforcer",)


def test_save_scout_strategy_normalizes_invalid_mode_and_priority():
    conn = _setup_conn()
    seed_default_scouts(conn)

    save_scout_strategy(
        conn,
        ScoutStrategyState("vera", "DROP TABLE", "INVALID_PRIORITY", ("Enforcer",), ()),
    )

    loaded = load_scout_strategy(conn, "vera")
    assert loaded is not None
    assert loaded.mode == "MANUAL"
    assert loaded.priority == "TOP_PUBLIC_OVR"


def test_upsert_scout_contribution_accrues_across_calls():
    conn = _setup_conn()
    seed_default_scouts(conn)
    upsert_scout_contribution(
        conn,
        ScoutContribution(
            scout_id="vera",
            player_id="p1",
            season=1,
            first_assigned_week=2,
            last_active_week=2,
            weeks_worked=1,
            contributed_scout_points={"ratings": 5, "archetype": 5, "traits": 5, "trajectory": 5},
            last_estimated_ratings_band={"ovr": (50, 80)},
            last_estimated_archetype="Enforcer",
            last_estimated_traits=(),
            last_estimated_ceiling=None,
            last_estimated_trajectory=None,
        ),
    )
    upsert_scout_contribution(
        conn,
        ScoutContribution(
            scout_id="vera",
            player_id="p1",
            season=1,
            first_assigned_week=2,
            last_active_week=3,
            weeks_worked=2,
            contributed_scout_points={"ratings": 10, "archetype": 10, "traits": 10, "trajectory": 10},
            last_estimated_ratings_band={"ovr": (55, 75)},
            last_estimated_archetype="Enforcer",
            last_estimated_traits=("CLUTCH",),
            last_estimated_ceiling=None,
            last_estimated_trajectory=None,
        ),
    )
    rows = load_scout_contributions_for_season(conn, season=1)
    assert len(rows) == 1
    assert rows[0].weeks_worked == 2
    assert rows[0].contributed_scout_points["ratings"] == 10
    assert rows[0].last_estimated_traits == ("CLUTCH",)


def test_append_scouting_domain_event_and_read():
    conn = _setup_conn()
    append_scouting_domain_event(
        conn,
        season=1,
        week=4,
        event_type="TIER_UP_RATINGS",
        player_id="p1",
        scout_id="vera",
        payload={"old_tier": "UNKNOWN", "new_tier": "GLIMPSED"},
    )
    events = load_scouting_domain_events_for_season(conn, season=1)
    assert len(events) == 1
    assert events[0]["event_type"] == "TIER_UP_RATINGS"
    assert events[0]["payload"]["new_tier"] == "GLIMPSED"


def test_save_revealed_traits_and_ceiling():
    conn = _setup_conn()
    save_revealed_traits(conn, player_id="p1", trait_ids=("IRONWALL",), revealed_at_week=4)
    save_ceiling_label(conn, "p1", "HIGH_CEILING", 8, "bram")
    assert load_revealed_traits(conn, "p1") == ("IRONWALL",)
    label_row = load_ceiling_label(conn, "p1")
    assert label_row is not None
    assert label_row["label"] == "HIGH_CEILING"
    assert label_row["revealed_by_scout_id"] == "bram"


def test_save_track_record_and_aggregate():
    conn = _setup_conn()
    seed_default_scouts(conn)
    save_scout_track_record(
        conn,
        scout_id="vera",
        player_id="p1",
        season=1,
        predicted_ovr_band=(55, 65),
        actual_ovr=62,
        predicted_archetype="Enforcer",
        actual_archetype="Enforcer",
        predicted_trajectory=None,
        actual_trajectory="IMPACT",
        predicted_ceiling=None,
        actual_ceiling="SOLID",
    )
    save_scout_track_record(
        conn,
        scout_id="vera",
        player_id="p2",
        season=1,
        predicted_ovr_band=(70, 78),
        actual_ovr=75,
        predicted_archetype="Sharpshooter",
        actual_archetype="Sharpshooter",
        predicted_trajectory="STAR",
        actual_trajectory="STAR",
        predicted_ceiling="HIGH_CEILING",
        actual_ceiling="HIGH_CEILING",
    )
    records = load_scout_track_records_for_scout(conn, "vera")
    assert len(records) == 2


def test_player_trajectory_save_and_load():
    conn = _setup_conn()
    from dodgeball_sim.persistence import load_player_trajectory, save_player_trajectory

    save_player_trajectory(conn, player_id="p1", trajectory="STAR")
    assert load_player_trajectory(conn, "p1") == "STAR"
    assert load_player_trajectory(conn, "nonexistent") is None


def test_player_trajectory_overwrite_on_resave():
    conn = _setup_conn()
    from dodgeball_sim.persistence import load_player_trajectory, save_player_trajectory

    save_player_trajectory(conn, player_id="p1", trajectory="NORMAL")
    save_player_trajectory(conn, player_id="p1", trajectory="GENERATIONAL")
    assert load_player_trajectory(conn, "p1") == "GENERATIONAL"
