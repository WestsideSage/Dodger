from __future__ import annotations

import json
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.offseason_ceremony import (
    compute_active_beats,
    initialize_manager_offseason,
    OFFSEASON_CEREMONY_BEATS,
)
from dodgeball_sim.offseason_presentation import build_beat_payload
from dodgeball_sim.awards import SeasonAward
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_season,
)


def _make_award(award_type, player_id, club_id="team_a"):
    return SeasonAward(
        season_id="s1",
        award_type=award_type,
        player_id=player_id,
        club_id=club_id,
        award_score=1.0,
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


def test_compute_season_awards_no_duplicate_award_types():
    """Each award_type appears at most once; a player can win multiple types."""
    from dodgeball_sim.awards import compute_season_awards
    from dodgeball_sim.stats import PlayerMatchStats

    stats = {
        "p1": PlayerMatchStats(eliminations_by_throw=10, catches_made=8, dodges_successful=5),
        "p2": PlayerMatchStats(eliminations_by_throw=3, catches_made=15, dodges_successful=2),
        "p3": PlayerMatchStats(eliminations_by_throw=6, catches_made=4, dodges_successful=3),
    }
    club_map = {"p1": "team_a", "p2": "team_b", "p3": "team_a"}
    newcomers = frozenset(["p3"])

    awards = compute_season_awards("s1", stats, club_map, newcomers)

    award_types = [a.award_type for a in awards]
    assert len(award_types) == len(set(award_types)), f"Duplicate award_type found: {award_types}"


def test_compute_season_awards_player_can_win_two_types():
    """p1 dominates all stats — should win mvp AND best_thrower (different types, not a bug)."""
    from dodgeball_sim.awards import compute_season_awards
    from dodgeball_sim.stats import PlayerMatchStats

    stats = {
        "p1": PlayerMatchStats(eliminations_by_throw=30, catches_made=15, dodges_successful=10),
        "p2": PlayerMatchStats(eliminations_by_throw=1, catches_made=20, dodges_successful=1),
    }
    club_map = {"p1": "team_a", "p2": "team_b"}
    newcomers = frozenset()

    awards = compute_season_awards("s1", stats, club_map, newcomers)

    winners = {a.award_type: a.player_id for a in awards}
    assert winners["mvp"] == "p1"
    assert winners["best_thrower"] == "p1"
    # p2 dominates catches
    assert winners["best_catcher"] == "p2"
    # No newcomers → no best_newcomer award
    assert "best_newcomer" not in winners


def test_compute_active_beats_always_includes_core():
    active = compute_active_beats(
        records_payload_json=None,
        hof_payload_json=None,
        retirement_rows=[],
    )
    core = ["champion", "recap", "awards", "development",
            "rookie_class_preview", "recruitment", "schedule_reveal"]
    for key in core:
        assert key in active, f"'{key}' missing from active beats"


def test_compute_active_beats_excludes_empty_conditional():
    active = compute_active_beats(
        records_payload_json=None,
        hof_payload_json=None,
        retirement_rows=[],
    )
    assert "records_ratified" not in active
    assert "hof_induction" not in active
    assert "retirements" not in active


def test_compute_active_beats_includes_retirements_when_present():
    active = compute_active_beats(
        records_payload_json=None,
        hof_payload_json=None,
        retirement_rows=[{"player_id": "p1", "player_name": "Bob"}],
    )
    assert "retirements" in active


def test_compute_active_beats_includes_records_when_present():
    records_json = json.dumps([{"record_type": "most_elims", "holder_name": "Bob",
                                 "previous_value": 5.0, "new_value": 10.0, "detail": ""}])
    active = compute_active_beats(
        records_payload_json=records_json,
        hof_payload_json=None,
        retirement_rows=[],
    )
    assert "records_ratified" in active


def test_compute_active_beats_preserves_order():
    records_json = json.dumps([{"record_type": "x", "holder_name": "A",
                                 "previous_value": 1, "new_value": 2, "detail": ""}])
    active = compute_active_beats(
        records_payload_json=records_json,
        hof_payload_json=None,
        retirement_rows=[{"player_id": "p1"}],
    )
    # records_ratified comes before retirements in the full sequence
    assert active.index("records_ratified") < active.index("retirements")
    # schedule_reveal is always last
    assert active[-1] == "schedule_reveal"


def test_initialize_manager_offseason_stores_active_beats():
    """After init, offseason_active_beats_json is stored and well-formed."""
    conn = _career_conn()
    season_id = conn.execute(
        "SELECT value FROM dynasty_state WHERE key = 'active_season_id'"
    ).fetchone()["value"]
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    raw = get_state(conn, "offseason_active_beats_json")
    assert raw is not None, "offseason_active_beats_json not stored"
    active = json.loads(raw)
    assert isinstance(active, list)
    assert len(active) > 0
    assert "schedule_reveal" in active
    assert active[-1] == "schedule_reveal"


def test_awards_payload_has_season_stat_fields():
    import sqlite3
    from dodgeball_sim.persistence import create_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.commit()

    awards_list = [_make_award("mvp", "p1"), _make_award("best_thrower", "p1")]

    # season=None means season_stats will be {} and stats default to zeros,
    # but the keys must still exist in the payload.
    payload = build_beat_payload(
        "awards",
        awards=awards_list,
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )

    assert "awards" in payload
    first = payload["awards"][0]
    assert "award_name" in first, "award_name missing"
    assert "season_stat" in first, "season_stat missing"
    assert "season_stat_label" in first, "season_stat_label missing"
    assert "career_stat" in first, "career_stat missing"
    # career_elims renamed to career_stat
    assert "career_elims" not in first


def test_awards_payload_prestige_sort_mvp_first():
    awards_list = [
        _make_award("best_newcomer", "p1"),
        _make_award("best_catcher", "p2"),
        _make_award("best_thrower", "p3"),
        _make_award("mvp", "p4"),
    ]
    import sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    payload = build_beat_payload(
        "awards",
        awards=awards_list,
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )

    types = [a["award_type"] for a in payload["awards"]]
    assert types[0] == "mvp", f"Expected mvp first, got {types}"
    assert types[-1] == "best_newcomer", f"Expected best_newcomer last, got {types}"


def test_development_payload_player_club_only():
    import sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    dev_rows = [
        {"player_id": "p1", "player_name": "Alice", "club_id": "my_club",
         "before": 65.4, "after": 67.2, "delta": 1.8},
        {"player_id": "p2", "player_name": "Bob",   "club_id": "other_club",
         "before": 70.1, "after": 71.5, "delta": 1.4},
        {"player_id": "p3", "player_name": "Carol",  "club_id": "my_club",
         "before": 58.9, "after": 60.0, "delta": 1.1},
    ]

    payload = build_beat_payload(
        "development",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        dev_rows=dev_rows,
        player_club_id="my_club",
        conn=conn,
    )

    assert "players" in payload
    names = [p["name"] for p in payload["players"]]
    assert "Alice" in names
    assert "Carol" in names
    assert "Bob" not in names, "Other club player should not appear"


def test_development_payload_no_decimals():
    import sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    dev_rows = [
        {"player_id": "p1", "player_name": "Alice", "club_id": "my_club",
         "before": 65.4, "after": 67.2, "delta": 1.8},
    ]

    payload = build_beat_payload(
        "development",
        awards=[], clubs={}, rosters={}, standings=[], ret_rows=[],
        season=None, season_outcome=None, next_preview=None,
        signed_player_id="", dev_rows=dev_rows, player_club_id="my_club",
        conn=conn,
    )

    player = payload["players"][0]
    assert isinstance(player["ovr_before"], int), "ovr_before must be int"
    assert isinstance(player["ovr_after"], int), "ovr_after must be int"
    assert isinstance(player["delta"], int), "delta must be int"
    assert player["ovr_before"] == 65
    assert player["ovr_after"] == 67
    assert player["delta"] == 2  # round(1.8) == 2


def test_rookie_class_preview_payload_structured():
    import json, sqlite3
    from dodgeball_sim.persistence import create_schema
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    rookie_json = json.dumps({
        "class_size": 14,
        "top_band_depth": 3,
        "free_agent_count": 6,
        "archetype_distribution": {"thrower": 8, "catcher": 6},
        "storylines": [
            {"sentence": "A blue-chip thrower leads this class."},
            {"sentence": "Defensive depth is thin this year."},
        ],
        "source": "prospect_pool",
    })

    payload = build_beat_payload(
        "rookie_class_preview",
        awards=[], clubs={}, rosters={}, standings=[], ret_rows=[],
        season=None, season_outcome=None, next_preview=None,
        signed_player_id="", rookie_preview_json=rookie_json,
        conn=conn,
    )

    assert payload["class_size"] == 14
    assert payload["top_prospects"] == 3
    assert payload["free_agents"] == 6
    assert len(payload["archetypes"]) == 2
    assert payload["archetypes"][0]["name"] == "thrower"  # sorted by count desc
    assert len(payload["storylines"]) == 2
    assert payload["storylines"][0] == "A blue-chip thrower leads this class."
