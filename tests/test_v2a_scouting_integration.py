import sqlite3

from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_scout_assignments,
    load_all_scouting_states,
    load_prospect_pool,
    load_scout_contributions_for_season,
    load_scouting_domain_events_for_season,
    load_scouts,
    save_scout_assignment,
    save_scout_strategy,
)
from dodgeball_sim.scouting_center import (
    ScoutAssignment,
    ScoutStrategyState,
    initialize_scouting_for_career,
    run_scouting_week_tick,
)


def _setup():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def test_initialize_scouting_for_career_seeds_scouts_and_class_1():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    scouts = load_scouts(conn)
    assert {scout.scout_id for scout in scouts} == {"vera", "bram", "linnea"}
    pool = load_prospect_pool(conn, class_year=1)
    assert len(pool) == DEFAULT_SCOUTING_CONFIG.prospect_class_size
    assert get_state(conn, "scouts_seeded_for_career") == "1"


def test_initialize_scouting_idempotent():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    pool = load_prospect_pool(conn, class_year=1)
    assert len(pool) == DEFAULT_SCOUTING_CONFIG.prospect_class_size


def test_week_tick_advances_active_assignments_and_writes_contribution():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    pool = load_prospect_pool(conn, class_year=1)
    target_pid = pool[0].player_id

    save_scout_assignment(conn, ScoutAssignment("vera", target_pid, 1))

    run_scouting_week_tick(conn, season=1, current_week=1, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)

    states = load_all_scouting_states(conn)
    assert target_pid in states
    assert states[target_pid].scout_points["ratings"] > 0
    contribs = load_scout_contributions_for_season(conn, season=1)
    assert any(c.scout_id == "vera" and c.player_id == target_pid for c in contribs)


def test_week_tick_auto_scout_picks_target_when_idle():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    save_scout_strategy(
        conn,
        ScoutStrategyState("vera", "AUTO", "TOP_PUBLIC_OVR", (), ()),
    )
    run_scouting_week_tick(conn, season=1, current_week=1, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    assignments = load_all_scout_assignments(conn)
    assert assignments["vera"].player_id is not None


def test_full_season_run_deterministic():
    def run_once() -> tuple:
        conn = _setup()
        initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
        save_scout_strategy(conn, ScoutStrategyState("vera", "AUTO", "TOP_PUBLIC_OVR", (), ()))
        save_scout_strategy(conn, ScoutStrategyState("bram", "AUTO", "SPECIALTY_FIT", (), ()))
        save_scout_strategy(conn, ScoutStrategyState("linnea", "AUTO", "TOP_PUBLIC_OVR", (), ()))
        for week in range(1, 15):
            run_scouting_week_tick(
                conn,
                season=1,
                current_week=week,
                root_seed=20260426,
                config=DEFAULT_SCOUTING_CONFIG,
            )
        states = load_all_scouting_states(conn)
        events = load_scouting_domain_events_for_season(conn, season=1)
        state_snapshot = sorted(
            [
                (
                    pid,
                    state.ratings_tier,
                    state.archetype_tier,
                    state.traits_tier,
                    state.trajectory_tier,
                    tuple(sorted(state.scout_points.items())),
                )
                for pid, state in states.items()
            ]
        )
        event_snapshot = [
            (event["week"], event["event_type"], event["player_id"], event["scout_id"])
            for event in events
        ]
        return state_snapshot, event_snapshot

    assert run_once() == run_once()


def test_carry_forward_decay_at_season_transition():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    pool = load_prospect_pool(conn, class_year=1)
    unsigned = pool[0]
    from dodgeball_sim.persistence import (
        load_ceiling_label,
        load_revealed_traits,
        load_scouting_state,
        save_ceiling_label,
        save_revealed_traits,
        save_scouting_state,
    )
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import apply_scouting_carry_forward_at_transition

    save_scouting_state(
        conn,
        ScoutingState(
            player_id=unsigned.player_id,
            ratings_tier="VERIFIED",
            archetype_tier="KNOWN",
            traits_tier="GLIMPSED",
            trajectory_tier="UNKNOWN",
            scout_points={"ratings": 70, "archetype": 35, "traits": 10, "trajectory": 0},
            last_updated_week=14,
        ),
    )
    save_revealed_traits(conn, unsigned.player_id, ("IRONWALL",), 8)
    save_ceiling_label(conn, unsigned.player_id, "HIGH_CEILING", 10, "bram")
    apply_scouting_carry_forward_at_transition(conn, prior_class_year=1)
    decayed = load_scouting_state(conn, unsigned.player_id)
    assert decayed is not None
    assert decayed.ratings_tier == "KNOWN"
    assert decayed.archetype_tier == "GLIMPSED"
    assert decayed.traits_tier == "UNKNOWN"
    assert decayed.trajectory_tier == "UNKNOWN"
    assert load_revealed_traits(conn, unsigned.player_id) == ("IRONWALL",)
    assert load_ceiling_label(conn, unsigned.player_id)["label"] == "HIGH_CEILING"


def test_carry_forward_skips_signed_prospects():
    conn = _setup()
    initialize_scouting_for_career(conn, root_seed=20260426, config=DEFAULT_SCOUTING_CONFIG)
    signed = load_prospect_pool(conn, class_year=1)[0]
    from dodgeball_sim.persistence import load_scouting_state, mark_prospect_signed, save_scouting_state
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import apply_scouting_carry_forward_at_transition

    save_scouting_state(
        conn,
        ScoutingState(
            player_id=signed.player_id,
            ratings_tier="VERIFIED",
            archetype_tier="VERIFIED",
            traits_tier="VERIFIED",
            trajectory_tier="VERIFIED",
            scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
            last_updated_week=14,
        ),
    )
    mark_prospect_signed(conn, class_year=1, player_id=signed.player_id)
    apply_scouting_carry_forward_at_transition(conn, prior_class_year=1)
    assert load_scouting_state(conn, signed.player_id) is None
