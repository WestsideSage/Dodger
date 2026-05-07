import sqlite3

import pytest

from dodgeball_sim.awards import SeasonAward
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.events import MatchEvent
from dodgeball_sim.manager_gui import (
    OFFSEASON_CEREMONY_BEATS,
    ManagerModeApp,
    build_offseason_ceremony_beat,
    build_expansion_club,
    build_player_profile_details,
    create_next_manager_season,
    build_league_leaders,
    build_schedule_rows,
    build_wire_items,
    clamp_offseason_beat_index,
    generate_expansion_roster,
    initialize_manager_offseason,
    update_manager_career_summaries,
    friendly_match_stats,
    friendly_preview_text,
    has_accuracy_reckoning_data,
    initialize_build_a_club_career,
    initialize_manager_career,
    load_offseason_state_rows,
    replay_event_label,
    replay_phase_delay,
    build_recruitment_day_summary,
    conduct_recruitment_round,
    format_bulk_sim_digest,
    sign_prospect_to_club,
)
from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits
from dodgeball_sim.persistence import (
    CorruptSaveError,
    create_schema,
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_free_agents,
    load_lineup_default,
    load_player_career_stats,
    load_season_format,
    load_season_outcome,
    load_season,
    save_awards,
    save_career_state_cursor,
    save_match_result,
    save_player_season_stats,
    set_state,
)
from dodgeball_sim.sample_data import sample_match_setup
from dodgeball_sim.scheduler import ScheduledMatch
from dodgeball_sim.season import Season, StandingsRow
from dodgeball_sim.stats import PlayerMatchStats


def test_build_expansion_club_persists_custom_identity():
    club = build_expansion_club(
        name="Portland Breakers",
        primary_color="#123456",
        secondary_color="#abcdef",
        venue_name="Breakers Gym",
        home_region="Northwest",
        tagline="Build from the ground up",
    )
    same = build_expansion_club(
        name="Portland Breakers",
        primary_color="#123456",
        secondary_color="#abcdef",
        venue_name="Breakers Gym",
        home_region="Northwest",
        tagline="Build from the ground up",
    )

    assert club.club_id == same.club_id == "exp_portland_breakers"
    assert club.name == "Portland Breakers"
    assert club.primary_color == "#123456"
    assert club.secondary_color == "#abcdef"
    assert club.venue_name == "Breakers Gym"
    assert club.home_region == "Northwest"
    assert club.tagline == "Build from the ground up"


def test_build_expansion_club_sanitizes_untrusted_identity_fields():
    club = build_expansion_club(
        name="  " + ("A" * 80),
        primary_color="not-a-color",
        secondary_color="#12345g",
        venue_name="  " + ("V" * 90),
        home_region="  " + ("R" * 60),
        tagline="  " + ("T" * 180),
    )

    assert club.name == "A" * 48
    assert club.primary_color == "#1A365D"
    assert club.secondary_color == "#F6AD55"
    assert club.venue_name == "V" * 64
    assert club.home_region == "R" * 40
    assert club.tagline == "T" * 120


def test_generate_expansion_roster_is_weaker_than_curated_rosters_without_hidden_modifiers():
    from dodgeball_sim.manager_gui import _club_roster
    from dodgeball_sim.rng import derive_seed
    from dodgeball_sim.sample_data import curated_clubs

    root_seed = 20260426
    expansion_club = build_expansion_club(
        name="Portland Breakers",
        primary_color="#123456",
        secondary_color="#abcdef",
        venue_name="Breakers Gym",
        home_region="Northwest",
        tagline="Build from the ground up",
    )
    expansion_roster = generate_expansion_roster(expansion_club.club_id, root_seed)
    curated_top_six_means = []
    for club in curated_clubs():
        roster = _club_roster(club, derive_seed(root_seed, "roster", club.club_id))
        curated_top_six_means.append(sum(player.overall() for player in roster[:6]) / 6)

    curated_mean = sum(curated_top_six_means) / len(curated_top_six_means)
    expansion_mean = sum(player.overall() for player in expansion_roster[:6]) / 6

    assert len(expansion_roster) == 6
    assert 8.0 <= curated_mean - expansion_mean <= 16.0
    assert all(player.club_id == expansion_club.club_id for player in expansion_roster)


def test_initialize_manager_career_rejects_non_integer_seed():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    with pytest.raises(ValueError, match="root_seed"):
        initialize_manager_career(conn, "aurora", root_seed="MALICIOUS_STRING")


def test_initialize_build_a_club_career_rejects_non_integer_seed():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    with pytest.raises(ValueError, match="root_seed"):
        initialize_build_a_club_career(
            conn,
            club_name="Portland Breakers",
            primary_color="#123456",
            secondary_color="#abcdef",
            venue_name="Breakers Gym",
            home_region="Northwest",
            tagline="Build from the ground up",
            root_seed="MALICIOUS_STRING",
        )


def test_initialize_build_a_club_career_creates_expansion_save_with_recruitment_setup():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    cursor = initialize_build_a_club_career(
        conn,
        club_name="Portland Breakers",
        primary_color="#123456",
        secondary_color="#abcdef",
        venue_name="Breakers Gym",
        home_region="Northwest",
        tagline="Build from the ground up",
        root_seed=20260426,
    )

    club_id = "exp_portland_breakers"
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    season = load_season(conn, "season_1")
    from dodgeball_sim.persistence import load_club_recruitment_profiles, load_prospect_pool

    assert cursor == CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, season_number=1, week=1)
    assert get_state(conn, "career_path") == "build_club"
    assert get_state(conn, "player_club_id") == club_id
    assert len(clubs) == 7
    assert clubs[club_id].name == "Portland Breakers"
    assert len(rosters[club_id]) == 6
    assert load_lineup_default(conn, club_id) == [player.id for player in rosters[club_id]]
    assert len(season.scheduled_matches) == 21
    assert len(load_prospect_pool(conn, 1)) > 0
    assert set(load_club_recruitment_profiles(conn)) == set(clubs)
    assert load_season_format(conn, "season_1") == "top4_single_elimination"


def test_sign_prospect_to_club_rejects_duplicate_roster_owner():
    from dodgeball_sim.persistence import load_prospect_pool

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    prospect = load_prospect_pool(conn, 1)[0]

    signed = sign_prospect_to_club(conn, prospect, "aurora", 1)

    with pytest.raises(ValueError, match="already signed"):
        sign_prospect_to_club(conn, prospect, "lunar", 1)

    locations = [
        club_id
        for club_id, roster in load_all_rosters(conn).items()
        if any(player.id == signed.id for player in roster)
    ]
    assert locations == ["aurora"]


def test_forged_offseason_cursor_is_clamped_to_valid_beat():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    save_career_state_cursor(
        conn,
        CareerStateCursor(
            state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
            season_number=1,
            week=0,
            offseason_beat_index=999,
        ),
    )

    cursor = load_career_state_cursor(conn)
    beat = build_offseason_ceremony_beat(
        cursor.offseason_beat_index,
        load_season(conn, "season_1"),
        load_clubs(conn),
        load_all_rosters(conn),
        [],
        [],
        "aurora",
    )

    assert cursor.offseason_beat_index == OFFSEASON_CEREMONY_BEATS.index("schedule_reveal")
    assert beat.key == "schedule_reveal"


def test_uncertainty_bar_halo_widths():
    from dodgeball_sim.ui_components import uncertainty_bar_halo_width_for_tier

    assert uncertainty_bar_halo_width_for_tier("UNKNOWN") == 100
    assert uncertainty_bar_halo_width_for_tier("GLIMPSED") == 30
    assert uncertainty_bar_halo_width_for_tier("KNOWN") == 12
    assert uncertainty_bar_halo_width_for_tier("VERIFIED") == 0


def test_build_scout_strip_data_three_scouts():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.persistence import create_schema, save_prospect_pool, save_scout_assignment, seed_default_scouts
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.scouting_center import ScoutAssignment
    from dodgeball_sim.manager_gui import build_scout_strip_data

    create_schema(conn)
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
    cards = build_scout_strip_data(conn, season=1)
    assert len(cards) == 3
    vera_card = next(card for card in cards if card["scout_id"] == "vera")
    assert vera_card["assignment_player_id"] == "prospect_1_005"
    assert "Enforcer" in vera_card["specialty_blurb"]
    assert vera_card["mode"] == "MANUAL"


def test_build_prospect_board_rows_uses_tier_widths():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.persistence import create_schema, save_prospect_pool, save_scouting_state
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_prospect_board_rows

    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(1, rng, DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    target = pool[0]
    save_scouting_state(
        conn,
        ScoutingState(
            player_id=target.player_id,
            ratings_tier="GLIMPSED",
            archetype_tier="UNKNOWN",
            traits_tier="UNKNOWN",
            trajectory_tier="UNKNOWN",
            scout_points={"ratings": 12, "archetype": 0, "traits": 0, "trajectory": 0},
            last_updated_week=3,
        ),
    )
    rows = build_prospect_board_rows(conn, class_year=1)
    target_row = next(row for row in rows if row["player_id"] == target.player_id)
    assert target_row["ratings_tier"] == "GLIMPSED"
    low, high = target_row["ovr_band"]
    assert high - low == 30


def test_build_reveal_ticker_items_chronological():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.persistence import append_scouting_domain_event, create_schema
    from dodgeball_sim.manager_gui import build_reveal_ticker_items

    create_schema(conn)
    append_scouting_domain_event(
        conn, 1, 2, "TIER_UP_RATINGS", "p1", "vera", {"new_tier": "GLIMPSED"}
    )
    append_scouting_domain_event(
        conn, 1, 5, "TRAIT_REVEALED", "p1", "vera", {"trait_id": "IRONWALL"}
    )
    items = build_reveal_ticker_items(conn, season=1)
    assert items[0]["week"] == 2
    assert items[1]["week"] == 5
    assert "GLIMPSED" in items[0]["text"]
    assert "IRONWALL" in items[1]["text"]


def test_worth_a_look_sort_prioritizes_low_confidence_high_ovr():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.persistence import create_schema, save_prospect_pool
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.manager_gui import build_prospect_board_rows, sort_rows_worth_a_look

    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(1, rng, DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    rows = build_prospect_board_rows(conn, class_year=1)
    sorted_rows = sort_rows_worth_a_look(rows)
    assert len(sorted_rows) == len(rows)


def test_build_fuzzy_profile_details_unknown_prospect():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.persistence import create_schema, save_prospect_pool
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.manager_gui import build_fuzzy_profile_details

    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(1, rng, DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    target = pool[0]
    details = build_fuzzy_profile_details(conn, class_year=1, player_id=target.player_id)
    assert details["name"] == target.name
    assert details["age"] == target.age
    assert details["archetype_label"] == target.public_archetype_guess
    assert details["ratings_tier"] == "UNKNOWN"
    assert details["ceiling_label"] == "?"
    assert details["trajectory_label"] == "Hidden (revealed at Draft Day)"
    assert details["trait_badges"] == ["?", "?", "?"] or details["trait_badges"] == []
    assert {row["rating_name"] for row in details["rating_rows"]} == {
        "accuracy",
        "power",
        "dodge",
        "catch",
        "stamina",
    }
    assert all(row["tier"] == "UNKNOWN" for row in details["rating_rows"])


def test_build_fuzzy_profile_details_with_known_ratings_and_revealed_traits():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.persistence import (
        create_schema,
        save_ceiling_label,
        save_prospect_pool,
        save_revealed_traits,
        save_scouting_state,
    )
    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_fuzzy_profile_details

    create_schema(conn)
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(1, rng, DEFAULT_SCOUTING_CONFIG)
    save_prospect_pool(conn, pool)
    target = pool[0]
    save_scouting_state(
        conn,
        ScoutingState(
            player_id=target.player_id,
            ratings_tier="KNOWN",
            archetype_tier="VERIFIED",
            traits_tier="GLIMPSED",
            trajectory_tier="UNKNOWN",
            scout_points={"ratings": 35, "archetype": 70, "traits": 12, "trajectory": 0},
            last_updated_week=8,
        ),
    )
    save_revealed_traits(conn, target.player_id, ("IRONWALL",), 5)
    save_ceiling_label(conn, target.player_id, "HIGH_CEILING", 8, "bram")
    details = build_fuzzy_profile_details(conn, class_year=1, player_id=target.player_id)
    assert details["ratings_tier"] == "KNOWN"
    assert details["archetype_label"] == target.true_archetype()
    assert details["ceiling_label"] == "HIGH CEILING"
    assert "IRONWALL" in details["trait_badges"]
    assert details["trajectory_label"] == "Hidden (revealed at Draft Day)"


def test_sign_prospect_converts_to_player_and_persists_trajectory():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_all_rosters, load_player_trajectory, load_prospect_pool
    from dodgeball_sim.manager_gui import sign_prospect_to_club

    target = load_prospect_pool(conn, class_year=1)[0]
    sign_prospect_to_club(conn, prospect=target, club_id="aurora", season_num=1)
    assert load_player_trajectory(conn, target.player_id) == target.hidden_trajectory
    raw = conn.execute(
        "SELECT is_signed FROM prospect_pool WHERE player_id = ?",
        (target.player_id,),
    ).fetchone()
    assert raw["is_signed"] == 1
    assert any(player.id == target.player_id for player in load_all_rosters(conn)["aurora"])


def test_sign_prospect_drops_scouting_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_prospect_pool, load_scouting_state, save_scouting_state
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import sign_prospect_to_club

    target = load_prospect_pool(conn, class_year=1)[0]
    save_scouting_state(
        conn,
        ScoutingState(
            player_id=target.player_id,
            ratings_tier="VERIFIED",
            archetype_tier="VERIFIED",
            traits_tier="VERIFIED",
            trajectory_tier="VERIFIED",
            scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
            last_updated_week=14,
        ),
    )
    sign_prospect_to_club(conn, prospect=target, club_id="aurora", season_num=1)
    assert load_scouting_state(conn, target.player_id) is None


def test_offseason_development_reads_trajectory_for_signed_prospect():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_all_rosters,
        load_clubs,
        load_prospect_pool,
        load_season,
        save_player_trajectory,
    )
    from dodgeball_sim.manager_gui import initialize_manager_offseason, sign_prospect_to_club

    target = load_prospect_pool(conn, class_year=1)[0]
    sign_prospect_to_club(conn, prospect=target, club_id="aurora", season_num=1)
    save_player_trajectory(conn, player_id=target.player_id, trajectory="GENERATIONAL")
    rosters = load_all_rosters(conn)
    pre = next(player for player in rosters["aurora"] if player.id == target.player_id)
    initialize_manager_offseason(
        conn,
        load_season(conn, "season_1"),
        load_clubs(conn),
        rosters,
        root_seed=20260426,
    )
    post = next(player for player in load_all_rosters(conn)["aurora"] if player.id == target.player_id)
    delta_generational = post.overall() - pre.overall()

    conn2 = sqlite3.connect(":memory:")
    conn2.row_factory = sqlite3.Row
    create_schema(conn2)
    initialize_manager_career(conn2, "aurora", root_seed=20260426)
    target2 = load_prospect_pool(conn2, class_year=1)[0]
    sign_prospect_to_club(conn2, prospect=target2, club_id="aurora", season_num=1)
    save_player_trajectory(conn2, player_id=target2.player_id, trajectory="NORMAL")
    rosters2 = load_all_rosters(conn2)
    pre2 = next(player for player in rosters2["aurora"] if player.id == target2.player_id)
    initialize_manager_offseason(
        conn2,
        load_season(conn2, "season_1"),
        load_clubs(conn2),
        rosters2,
        root_seed=20260426,
    )
    post2 = next(player for player in load_all_rosters(conn2)["aurora"] if player.id == target2.player_id)
    delta_normal = post2.overall() - pre2.overall()
    assert delta_generational > 0
    assert delta_generational > delta_normal


def test_build_trajectory_reveal_sweep_only_includes_verified_axis():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_prospect_pool, save_scouting_state
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_trajectory_reveal_sweep

    pool = load_prospect_pool(conn, class_year=1)
    p_verified = pool[0]
    p_glimpsed = pool[1]
    save_scouting_state(
        conn,
        ScoutingState(
            player_id=p_verified.player_id,
            ratings_tier="VERIFIED",
            archetype_tier="VERIFIED",
            traits_tier="VERIFIED",
            trajectory_tier="VERIFIED",
            scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
            last_updated_week=14,
        ),
    )
    save_scouting_state(
        conn,
        ScoutingState(
            player_id=p_glimpsed.player_id,
            ratings_tier="GLIMPSED",
            archetype_tier="UNKNOWN",
            traits_tier="UNKNOWN",
            trajectory_tier="GLIMPSED",
            scout_points={"ratings": 12, "archetype": 0, "traits": 0, "trajectory": 12},
            last_updated_week=8,
        ),
    )
    sweep = build_trajectory_reveal_sweep(conn, class_year=1)
    sweep_ids = {entry["player_id"] for entry in sweep}
    assert p_verified.player_id in sweep_ids
    assert p_glimpsed.player_id not in sweep_ids
    entry = next(item for item in sweep if item["player_id"] == p_verified.player_id)
    assert entry["trajectory"] == p_verified.hidden_trajectory
    assert entry["display_weight"] in ("standard", "elevated")


def test_build_accuracy_reckoning_writes_track_records():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import (
        load_prospect_pool,
        load_scout_track_records_for_scout,
        upsert_scout_contribution,
    )
    from dodgeball_sim.scouting_center import ScoutContribution
    from dodgeball_sim.manager_gui import build_accuracy_reckoning

    target = load_prospect_pool(conn, class_year=1)[0]
    upsert_scout_contribution(
        conn,
        ScoutContribution(
            scout_id="vera",
            player_id=target.player_id,
            season=1,
            first_assigned_week=2,
            last_active_week=10,
            weeks_worked=8,
            contributed_scout_points={"ratings": 40, "archetype": 40, "traits": 25, "trajectory": 20},
            last_estimated_ratings_band={"ovr": (int(target.true_overall()) - 6, int(target.true_overall()) + 6)},
            last_estimated_archetype=target.public_archetype_guess,
            last_estimated_traits=tuple(target.hidden_traits[:1]),
            last_estimated_ceiling=None,
            last_estimated_trajectory=None,
        ),
    )
    summary = build_accuracy_reckoning(conn, season=1, class_year=1)
    assert "vera" in {row["scout_id"] for row in summary}
    records = load_scout_track_records_for_scout(conn, "vera")
    assert any(record["player_id"] == target.player_id for record in records)
    before = len(records)
    build_accuracy_reckoning(conn, season=1, class_year=1)
    after = len(load_scout_track_records_for_scout(conn, "vera"))
    assert after == before


def test_has_accuracy_reckoning_data_only_when_scout_work_exists():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    assert has_accuracy_reckoning_data(conn, season=1) is False

    from dodgeball_sim.persistence import load_prospect_pool, upsert_scout_contribution
    from dodgeball_sim.scouting_center import ScoutContribution

    target = load_prospect_pool(conn, class_year=1)[0]
    upsert_scout_contribution(
        conn,
        ScoutContribution(
            scout_id="vera",
            player_id=target.player_id,
            season=1,
            first_assigned_week=1,
            last_active_week=2,
            weeks_worked=2,
            contributed_scout_points={"ratings": 10, "archetype": 10, "traits": 0, "trajectory": 0},
            last_estimated_ratings_band={"ovr": [50, 70]},
            last_estimated_archetype=target.public_archetype_guess,
            last_estimated_traits=(),
            last_estimated_ceiling=None,
            last_estimated_trajectory=None,
        ),
    )

    assert has_accuracy_reckoning_data(conn, season=1) is True


def test_build_hidden_gem_spotlight_picks_recent_high_ceiling_event():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import append_scouting_domain_event, load_prospect_pool, save_ceiling_label
    from dodgeball_sim.manager_gui import build_hidden_gem_spotlight

    target = load_prospect_pool(conn, class_year=1)[0]
    save_ceiling_label(conn, target.player_id, "HIGH_CEILING", 8, "bram")
    append_scouting_domain_event(
        conn,
        season=1,
        week=8,
        event_type="CEILING_REVEALED",
        player_id=target.player_id,
        scout_id="bram",
        payload={"label": "HIGH_CEILING"},
    )
    spotlight = build_hidden_gem_spotlight(conn, season=1, class_year=1)
    if spotlight is not None:
        assert spotlight["player_id"] == target.player_id
        assert spotlight["label"] == "HIGH_CEILING"


def test_build_hidden_gem_spotlight_returns_none_without_high_ceiling_events():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.manager_gui import build_hidden_gem_spotlight

    assert build_hidden_gem_spotlight(conn, season=1, class_year=1) is None


def test_build_scouting_alerts_unassigned_scouts():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.manager_gui import build_scouting_alerts

    alerts = build_scouting_alerts(conn, season=1, current_week=2, total_weeks=14)
    assert any("3 unassigned" in alert["text"] for alert in alerts)


def test_build_scouting_alerts_late_season_verified_count():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import load_prospect_pool, save_scouting_state
    from dodgeball_sim.scouting_center import ScoutingState
    from dodgeball_sim.manager_gui import build_scouting_alerts

    target = load_prospect_pool(conn, class_year=1)[0]
    save_scouting_state(
        conn,
        ScoutingState(
            player_id=target.player_id,
            ratings_tier="VERIFIED",
            archetype_tier="VERIFIED",
            traits_tier="VERIFIED",
            trajectory_tier="VERIFIED",
            scout_points={"ratings": 70, "archetype": 70, "traits": 70, "trajectory": 70},
            last_updated_week=13,
        ),
    )
    alerts = build_scouting_alerts(conn, season=1, current_week=13, total_weeks=14)
    assert any("Verified" in alert["text"] or "trajectory" in alert["text"].lower() for alert in alerts)
    alerts_mid = build_scouting_alerts(conn, season=1, current_week=4, total_weeks=14)
    assert not any("trajectory" in alert["text"].lower() for alert in alerts_mid)


def test_wire_items_include_high_ceiling_buzz():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import append_scouting_domain_event, load_prospect_pool, save_ceiling_label

    target = load_prospect_pool(conn, class_year=1)[0]
    save_ceiling_label(conn, target.player_id, "HIGH_CEILING", 6, "bram")
    append_scouting_domain_event(
        conn,
        season=1,
        week=6,
        event_type="CEILING_REVEALED",
        player_id=target.player_id,
        scout_id="bram",
        payload={"label": "HIGH_CEILING"},
    )
    items = build_wire_items(conn, season_id="season_1", current_week=8)
    assert any(target.name in (item.get("body") or "") for item in items)


def test_initialize_manager_career_persists_curated_league_and_cursor():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    cursor = initialize_manager_career(conn, "aurora", root_seed=20260426)

    clubs = load_clubs(conn)
    season = load_season(conn, "season_1")
    loaded_cursor = load_career_state_cursor(conn)

    assert len(clubs) == 6
    assert get_state(conn, "player_club_id") == "aurora"
    assert season.total_weeks() == 5
    assert len(season.scheduled_matches) == 15
    assert cursor == loaded_cursor
    assert loaded_cursor.state == CareerState.SEASON_ACTIVE_PRE_MATCH


def test_initialize_manager_career_seeds_scouting():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    from dodgeball_sim.persistence import get_state, load_prospect_pool, load_scouts

    scouts = load_scouts(conn)
    assert {scout.scout_id for scout in scouts} == {"vera", "bram", "linnea"}
    pool = load_prospect_pool(conn, class_year=1)
    assert len(pool) > 0
    assert get_state(conn, "scouts_seeded_for_career") == "1"


def test_initialize_manager_career_saves_default_lineups():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    initialize_manager_career(conn, "lunar", root_seed=20260426)

    for club_id in load_clubs(conn):
        lineup = load_lineup_default(conn, club_id)
        assert lineup is not None
        assert len(lineup) == 6


def test_initialize_manager_career_replaces_existing_manager_save():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    initialize_manager_career(conn, "aurora", root_seed=1)
    initialize_manager_career(conn, "lunar", root_seed=2)

    assert get_state(conn, "player_club_id") == "lunar"
    assert len(load_clubs(conn)) == 6


def _throw_event(resolution: str) -> MatchEvent:
    return MatchEvent(
        event_id=1,
        tick=12,
        seed=0,
        event_type="throw",
        phase="volley",
        actors={"thrower": "aurora_1", "target": "lunar_2"},
        context={},
        probabilities={},
        rolls={},
        outcome={"resolution": resolution},
        state_diff={},
    )


def test_replay_event_label_punctuates_hits_and_catches():
    assert replay_event_label(_throw_event("hit")).startswith("HIT:")
    assert replay_event_label(_throw_event("catch")).startswith("CATCH:")


def test_replay_phase_delay_holds_impact_events_longer_than_misses():
    assert replay_phase_delay(_throw_event("hit")) > replay_phase_delay(_throw_event("miss"))


def test_build_league_leaders_uses_persisted_stats():
    leaders = build_league_leaders(
        {
            "p1": PlayerMatchStats(eliminations_by_throw=4, catches_made=1),
            "p2": PlayerMatchStats(eliminations_by_throw=1, catches_made=6),
        },
        {"p1": "aurora", "p2": "lunar"},
        limit=1,
    )

    assert leaders["Eliminations"][0].player_id == "p1"
    assert leaders["Catches"][0].player_id == "p2"
    assert leaders["MVP Score"][0].player_id == "p2"


def test_build_player_profile_details_includes_bio_ratings_and_stats():
    player = Player(
        id="p1",
        name="Casey Cannon",
        ratings=PlayerRatings(accuracy=72, power=81, dodge=64, catch=58, stamina=70),
        traits=PlayerTraits(),
        age=22,
        club_id="aurora",
        newcomer=False,
    )

    details = build_player_profile_details(
        player,
        "Aurora Sentinels",
        season_stats=PlayerMatchStats(
            throws_attempted=10,
            eliminations_by_throw=4,
            catches_made=2,
            dodges_successful=3,
            times_eliminated=1,
            elimination_plus_minus=3,
        ),
        matches_played=2,
        career_summary={
            "seasons_played": 1,
            "total_eliminations": 9,
            "total_catches_made": 4,
            "total_dodges_successful": 6,
            "total_times_eliminated": 3,
            "recent_eliminations": 9,
        },
    )

    assert details.title == "Casey Cannon"
    assert "Club: Aurora Sentinels" in details.text
    assert "Role:" in details.text
    assert "Accuracy: 72.0" in details.text
    assert "Matches: 2" in details.text
    assert "Eliminations: 4" in details.text
    assert "Seasons: 1" in details.text


def test_build_player_profile_details_handles_missing_persisted_stats():
    player = Player(
        id="p1",
        name="Riley Rookie",
        ratings=PlayerRatings(accuracy=60, power=61, dodge=62, catch=63),
    )

    details = build_player_profile_details(player, "Aurora Sentinels")

    assert "Status: Rookie" in details.text
    assert "No persisted season stats yet." in details.text
    assert "No persisted career totals yet." in details.text


def test_build_schedule_rows_marks_status_and_user_match():
    season = Season(
        season_id="season_1",
        year=2026,
        league_id="league",
        config_version="phase1.v1",
        ruleset_version="default.v1",
        scheduled_matches=(
            ScheduledMatch("m1", "season_1", 1, "aurora", "lunar"),
            ScheduledMatch("m2", "season_1", 1, "harbor", "granite"),
        ),
    )

    rows = build_schedule_rows(season, completed_match_ids={"m1"}, user_club_id="aurora")

    assert rows[0].status == "played"
    assert rows[0].is_user_match is True
    assert rows[1].status == "open"
    assert rows[1].is_user_match is False


def test_build_wire_items_uses_match_results():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    row = {
        "match_id": "m1",
        "week": 2,
        "home_club_id": "aurora",
        "away_club_id": "lunar",
        "winner_club_id": "aurora",
        "home_survivors": 2,
        "away_survivors": 0,
    }

    items = build_wire_items([row], clubs, awards=[])

    assert items[0].tag == "RESULT"
    assert items[0].match_id == "m1"
    assert "Aurora Sentinels beat Lunar Syndicate" in items[0].text


def test_build_wire_items_resolves_award_player_names():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    player = rosters["aurora"][0]
    awards = [SeasonAward("season_1", "mvp", player.id, "aurora", 99.0)]

    items = build_wire_items([], clubs, awards=awards, rosters=rosters)

    assert items[0].tag == "AWARD"
    assert player.name in items[0].text
    assert player.id not in items[0].text


def test_build_wire_items_falls_back_to_human_award_player_label_without_rosters():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    awards = [SeasonAward("season_1", "best_newcomer", "aurora_5", "aurora", 12.0)]

    items = build_wire_items([], clubs, awards=awards)

    assert items[0].tag == "AWARD"
    assert "Aurora 5" in items[0].text
    assert "aurora_5" not in items[0].text


def test_build_offseason_ceremony_uses_expected_beats_and_real_rows():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    standings = [
        StandingsRow("aurora", wins=5, losses=0, draws=0, elimination_differential=14, points=15),
        StandingsRow("lunar", wins=3, losses=2, draws=0, elimination_differential=4, points=9),
    ]
    awards = [
        SeasonAward("season_1", "mvp", rosters["aurora"][0].id, "aurora", 42.0),
    ]

    champion = build_offseason_ceremony_beat(0, None, clubs, rosters, standings, awards, "aurora")
    development = build_offseason_ceremony_beat(
        5,
        None,
        clubs,
        rosters,
        standings,
        awards,
        "aurora",
        development_rows=[
            {
                "player_id": rosters["aurora"][0].id,
                "player_name": rosters["aurora"][0].name,
                "club_id": "aurora",
                "before": 70.0,
                "after": 71.2,
                "delta": 1.2,
            }
        ],
    )
    retirements = build_offseason_ceremony_beat(
        6,
        None,
        clubs,
        rosters,
        standings,
        awards,
        "aurora",
        retirement_rows=[
            {
                "player_id": "old_star",
                "player_name": "Old Star",
                "club_id": "aurora",
                "age": 40,
                "overall": 58.0,
            }
        ],
    )
    draft = build_offseason_ceremony_beat(
        8,
        None,
        clubs,
        rosters,
        standings,
        awards,
        "aurora",
        draft_pool=rosters["lunar"][:2],
    )

    assert OFFSEASON_CEREMONY_BEATS == (
        "champion",
        "recap",
        "awards",
        "records_ratified",
        "hof_induction",
        "development",
        "retirements",
        "rookie_class_preview",
        "recruitment",
        "schedule_reveal",
    )
    assert champion.title == "Champion"
    assert "Aurora Sentinels" in champion.body
    assert "Development applied to 1 active players" in development.body
    assert "+1.2" in development.body
    assert "Retirements processed: 1" in retirements.body
    assert "Old Star" in retirements.body
    assert "v1 Draft is active" in draft.body
    assert "Available rookies: 2" in draft.body


def test_offseason_champion_beat_prefers_playoff_outcome():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    standings = [
        StandingsRow("aurora", wins=5, losses=0, draws=0, elimination_differential=14, points=15),
        StandingsRow("lunar", wins=3, losses=2, draws=0, elimination_differential=4, points=9),
    ]
    from dodgeball_sim.playoffs import SeasonOutcome

    beat = build_offseason_ceremony_beat(
        0,
        load_season(conn, "season_1"),
        clubs,
        rosters,
        standings,
        [],
        "aurora",
        season_outcome=SeasonOutcome(
            season_id="season_1",
            champion_club_id="lunar",
            champion_source="playoff_final",
            final_match_id="season_1_p_final",
            runner_up_club_id="aurora",
            payload={},
        ),
    )

    assert "Champion: Lunar Syndicate" in beat.body
    assert "Champion source: Playoff final" in beat.body
    assert "Runner-up: Aurora Sentinels" in beat.body


def test_create_next_manager_season_uses_existing_clubs_and_next_id():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)

    season = create_next_manager_season(clubs, root_seed=20260426, season_number=2, year=2027)

    assert season.season_id == "season_2"
    assert season.year == 2027
    assert len(season.scheduled_matches) == 15
    assert {match.season_id for match in season.scheduled_matches} == {"season_2"}


def test_playoff_progression_simulates_ai_only_bracket_and_persists_outcome():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    app = ManagerModeApp.__new__(ManagerModeApp)
    app.conn = conn
    app.clubs = load_clubs(conn)
    app.rosters = load_all_rosters(conn)
    app.season = load_season(conn, "season_1")

    strength = {"lunar": 6, "northwood": 5, "harbor": 4, "granite": 3, "solstice": 2, "aurora": 1}
    for match in app.season.scheduled_matches:
        home_score = strength[match.home_club_id]
        away_score = strength[match.away_club_id]
        winner = match.home_club_id if home_score > away_score else match.away_club_id
        save_match_result(
            conn,
            match_id=match.match_id,
            season_id=match.season_id,
            week=match.week,
            home_club_id=match.home_club_id,
            away_club_id=match.away_club_id,
            winner_club_id=winner,
            home_survivors=home_score,
            away_survivors=away_score,
            home_roster_hash="home",
            away_roster_hash="away",
            config_version="phase1.v1",
            ruleset_version="default.v1",
            meta_patch_id=None,
            seed=1,
            event_log_hash="events",
            final_state_hash="state",
            engine_match_id=None,
        )
    app._recompute_standings()

    app._advance_playoffs_if_needed()

    season = load_season(conn, "season_1")
    outcome = load_season_outcome(conn, "season_1")
    assert {match.match_id for match in season.scheduled_matches if "_p_" in match.match_id} == {
        "season_1_p_r1_m1",
        "season_1_p_r1_m2",
        "season_1_p_final",
    }
    assert outcome is not None
    assert outcome.champion_source == "playoff_final"
    assert outcome.final_match_id == "season_1_p_final"


def test_initialize_manager_offseason_develops_rosters_and_creates_rookie_pool():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    season = load_season(conn, "season_1")
    before = {club_id: [player.overall() for player in roster] for club_id, roster in rosters.items()}

    updated = initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    assert get_state(conn, "offseason_initialized_for") == "season_1"
    assert len(load_free_agents(conn)) == 12
    assert any(
        updated[club_id][index].overall() != before[club_id][index]
        for club_id in before
        for index in range(min(len(before[club_id]), len(updated[club_id])))
    )
    assert "player_name" in get_state(conn, "offseason_development_json", "[]")


def test_update_manager_career_summaries_rolls_up_finalized_season_stats():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    rosters = load_all_rosters(conn)
    season = load_season(conn, "season_1")
    player = rosters["aurora"][0]
    save_player_season_stats(
        conn,
        season.season_id,
        {player.id: PlayerMatchStats(eliminations_by_throw=7, catches_made=3, dodges_successful=2, times_eliminated=1)},
        {player.id: "aurora"},
        {player.id: 5},
        frozenset(),
    )
    award = SeasonAward(season.season_id, "mvp", player.id, "aurora", 25.0)
    save_awards(conn, [award])

    update_manager_career_summaries(conn, season, rosters, [award])

    summary = load_player_career_stats(conn, player.id)
    assert summary["seasons_played"] == 1
    assert summary["awards_won"] == 1
    assert summary["total_eliminations"] == 7
    assert summary["career_catches"] == 3


def test_sign_best_rookie_adds_player_to_user_roster_once():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    app = ManagerModeApp.__new__(ManagerModeApp)
    app.conn = conn
    app.clubs = load_clubs(conn)
    app.rosters = load_all_rosters(conn)
    app.season = load_season(conn, "season_1")
    app.cursor = CareerStateCursor(
        state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
        season_number=1,
        week=0,
        offseason_beat_index=5,
    )
    app.rosters = initialize_manager_offseason(conn, app.season, app.clubs, app.rosters, root_seed=20260426)
    before_size = len(app.rosters["aurora"])

    signed = app._sign_best_rookie()
    second = app._sign_best_rookie()

    assert signed is not None
    assert second is None
    assert get_state(conn, "offseason_draft_signed_player_id") == signed.id
    assert len(load_all_rosters(conn)["aurora"]) == before_size + 1
    assert all(player.id != signed.id for player in load_free_agents(conn))


def test_sign_best_rookie_uses_prospect_pool_when_available():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    app = ManagerModeApp.__new__(ManagerModeApp)
    app.conn = conn
    app.clubs = load_clubs(conn)
    app.rosters = load_all_rosters(conn)
    app.season = load_season(conn, "season_1")
    app.cursor = CareerStateCursor(
        state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
        season_number=1,
        week=0,
        offseason_beat_index=5,
    )
    app.rosters = initialize_manager_offseason(conn, app.season, app.clubs, app.rosters, root_seed=20260426)

    signed = app._sign_best_rookie()

    from dodgeball_sim.persistence import load_player_trajectory, load_prospect_pool

    assert signed is not None
    assert signed.id.startswith("prospect_1_")
    assert load_player_trajectory(conn, signed.id) is not None
    assert any(prospect.player_id == signed.id for prospect in load_prospect_pool(conn, class_year=1))


def test_draft_beat_copy_switches_to_recruitment_when_prospect_pool_exists():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        8,
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        draft_pool=load_free_agents(conn),
        recruitment_available=True,
        recruitment_summary={"available_prospects": 25, "signed_count": 0, "sniped_count": 0},
    )

    assert beat.title == "Recruitment Day"
    assert "Recruitment Day is active" in beat.body
    assert "Available prospects: 25" in beat.body


def test_build_recruitment_day_summary_counts_available_signings_and_snipes():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    from dodgeball_sim.persistence import (
        load_prospect_pool,
        save_recruitment_signings,
    )
    from dodgeball_sim.recruitment_domain import RecruitmentSigning

    prospect = load_prospect_pool(conn, class_year=1)[0]
    save_recruitment_signings(
        conn,
        [RecruitmentSigning("season_1", 1, "lunar", prospect.player_id, "ai", 95.0, "club need")],
    )

    summary = build_recruitment_day_summary(conn, season_id="season_1", class_year=1, user_club_id="aurora")

    assert summary["available_prospects"] == 24
    assert summary["signed_count"] == 1
    assert summary["sniped_count"] == 1
    assert summary["current_round"] == 2


def test_conduct_recruitment_round_uses_prepared_ai_offer_and_records_snipe():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    from dodgeball_sim.persistence import (
        load_all_rosters,
        load_prospect_pool,
        load_recruitment_signings,
        save_recruitment_offers,
        save_recruitment_round,
    )
    from dodgeball_sim.recruitment_domain import RecruitmentOffer

    target = load_prospect_pool(conn, class_year=1)[0]
    save_recruitment_round(conn, "season_1", 1, "prepared", {"prepared_offer_count": 1})
    save_recruitment_offers(
        conn,
        [
            RecruitmentOffer(
                "season_1",
                1,
                "lunar",
                target.player_id,
                200.0,
                "ai",
                10.0,
                0.9,
                0.9,
                0.1,
                "club need 10.00; public fit 9.00; round priority 0.1000",
            )
        ],
    )

    result = conduct_recruitment_round(
        conn,
        root_seed=20260426,
        season_id="season_1",
        class_year=1,
        user_club_id="aurora",
        selected_player_id=target.player_id,
    )

    assert result.snipes
    assert result.signings[0].club_id == "lunar"
    assert load_recruitment_signings(conn, "season_1")[0].club_id == "lunar"
    assert any(player.id == target.player_id for player in load_all_rosters(conn)["lunar"])


def test_conduct_recruitment_round_advances_after_resolved_round():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    from dodgeball_sim.persistence import (
        load_prospect_pool,
        load_recruitment_round,
        load_recruitment_signings,
        save_recruitment_signings,
    )
    from dodgeball_sim.recruitment_domain import RecruitmentSigning

    prospects = load_prospect_pool(conn, class_year=1)
    already_signed = prospects[0]
    next_target = next(prospect for prospect in prospects if prospect.player_id != already_signed.player_id)
    save_recruitment_signings(
        conn,
        [RecruitmentSigning("season_1", 1, "lunar", already_signed.player_id, "ai", 90.0, "round one")],
    )

    result = conduct_recruitment_round(
        conn,
        root_seed=20260426,
        season_id="season_1",
        class_year=1,
        user_club_id="aurora",
        selected_player_id=next_target.player_id,
    )

    assert result.round_number == 2
    assert load_recruitment_round(conn, "season_1", 2)["status"] == "resolved"
    assert {signing.round_number for signing in load_recruitment_signings(conn, "season_1")} == {1, 2}


def test_conduct_recruitment_round_user_club_not_in_ai_offers():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    from dodgeball_sim.persistence import load_prospect_pool, load_recruitment_offers

    target = load_prospect_pool(conn, class_year=1)[0]
    conduct_recruitment_round(
        conn,
        root_seed=20260426,
        season_id="season_1",
        class_year=1,
        user_club_id="aurora",
        selected_player_id=target.player_id,
    )
    offers = load_recruitment_offers(conn, "season_1", 1)
    assert all(offer.club_id != "aurora" for offer in offers)


def test_begin_next_season_persists_schedule_and_active_cursor():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    app = ManagerModeApp.__new__(ManagerModeApp)
    app.conn = conn
    app.clubs = load_clubs(conn)
    app.rosters = load_all_rosters(conn)
    app.season = load_season(conn, "season_1")
    app.cursor = CareerStateCursor(
        state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
        season_number=1,
        week=0,
        offseason_beat_index=len(OFFSEASON_CEREMONY_BEATS) - 1,
    )
    app._load_state = lambda: None
    app.show_hub = lambda: None

    app._begin_next_season()

    next_season = load_season(conn, "season_2")
    cursor = load_career_state_cursor(conn)
    from dodgeball_sim.persistence import load_prospect_pool

    assert get_state(conn, "active_season_id") == "season_2"
    assert next_season.total_weeks() == 5
    assert len(next_season.scheduled_matches) == 15
    assert cursor.state == CareerState.SEASON_ACTIVE_PRE_MATCH
    assert cursor.season_number == 2
    assert cursor.week == 1
    assert len(load_prospect_pool(conn, class_year=2)) > 0
    assert build_recruitment_day_summary(conn, "season_2", 2, "aurora")["available_prospects"] > 0


def test_load_offseason_state_rows_reports_corrupt_json():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    set_state(conn, "offseason_development_json", "{bad-json")

    with pytest.raises(CorruptSaveError, match="offseason_development_json"):
        load_offseason_state_rows(conn, "offseason_development_json")


def test_clamp_offseason_beat_index_bounds_forged_values():
    assert clamp_offseason_beat_index(-50) == 0
    assert clamp_offseason_beat_index(999) == len(OFFSEASON_CEREMONY_BEATS) - 1


def test_friendly_preview_text_describes_both_sample_teams():
    preview = friendly_preview_text(sample_match_setup())

    assert "Aurora Sentinels" in preview
    assert "Lunar Syndicate" in preview
    assert "Top Rotation" in preview


def test_friendly_match_stats_extracts_in_memory_events():
    setup = sample_match_setup()
    event = MatchEvent(
        event_id=1,
        tick=12,
        seed=0,
        event_type="throw",
        phase="volley",
        actors={"thrower": "aurora_captain", "target": "lunar_anchor"},
        context={},
        probabilities={},
        rolls={},
        outcome={"resolution": "hit"},
        state_diff={"player_out": {"player_id": "lunar_anchor", "team": "lunar"}},
    )

    stats = friendly_match_stats(setup, [event])

    assert stats["aurora_captain"].throws_attempted == 1
    assert stats["aurora_captain"].eliminations_by_throw == 1
    assert stats["lunar_anchor"].times_eliminated == 1


def test_sim_to_next_user_match_stops_before_user_match(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    app = ManagerModeApp.__new__(ManagerModeApp)
    app.conn = conn
    app.clubs = load_clubs(conn)
    app.rosters = load_all_rosters(conn)
    app.season = load_season(conn, "season_1")
    from dodgeball_sim.persistence import set_state
    set_state(conn, "player_club_id", "aurora")
    app.cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, season_number=1, week=1)
    app._advance_playoffs_if_needed = lambda: None
    app.show_hub = lambda: None

    infos = []
    monkeypatch.setattr("dodgeball_sim.manager_gui.messagebox.showinfo", lambda title, message: infos.append((title, message)))

    app._sim_to_next_user_match()

    user_next = app._next_user_match()
    assert user_next is not None
    completed = conn.execute("SELECT match_id FROM match_records").fetchall()
    completed_ids = {row["match_id"] for row in completed}
    assert user_next.match_id not in completed_ids
    assert infos


def test_format_bulk_sim_digest_includes_standings_notables_and_recruitment_context():
    text = format_bulk_sim_digest(
        matches_simmed=4,
        first_week=2,
        last_week=3,
        user_record="2-1-0",
        standings_note="Aurora Sentinels moved into second.",
        notable_lines=["Mara Voss posted 5 eliminations."],
        scouting_note="Scout reveal pending.",
        recruitment_note="Recruitment day is next.",
        next_action="Play Next Match",
    )

    assert "4 Matches Simmed" in text
    assert "Aurora Sentinels moved into second." in text
    assert "Mara Voss posted 5 eliminations." in text
    assert "Scout reveal pending." in text
    assert "Recruitment day is next." in text
    assert "Play Next Match" in text


def test_sim_week_without_user_auto_sim_keeps_user_match_pending(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)

    app = ManagerModeApp.__new__(ManagerModeApp)
    app.conn = conn
    app.clubs = load_clubs(conn)
    app.rosters = load_all_rosters(conn)
    app.season = load_season(conn, "season_1")
    from dodgeball_sim.persistence import set_state
    set_state(conn, "player_club_id", "aurora")
    app.cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, season_number=1, week=1)
    app._advance_playoffs_if_needed = lambda: None
    app.show_hub = lambda: None

    monkeypatch.setattr("dodgeball_sim.manager_gui.messagebox.askyesno", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("dodgeball_sim.manager_gui.messagebox.showinfo", lambda *_args, **_kwargs: None)

    next_user_before = app._next_user_match()
    assert next_user_before is not None
    app._sim_week()

    completed_ids = {row["match_id"] for row in conn.execute("SELECT match_id FROM match_records").fetchall()}
    assert next_user_before.match_id not in completed_ids


def test_offseason_records_ratified_beat_renders_persisted_payload():
    import json as _json
    from dodgeball_sim.persistence import set_state

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("records_ratified"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        season_outcome=None,
        records_payload_json=_json.dumps([
            {
                "record_type": "career_eliminations",
                "holder_id": "p1",
                "holder_type": "player",
                "holder_name": "Alpha Star",
                "previous_value": 100.0,
                "new_value": 142.0,
                "set_in_season": "season_1",
                "detail": "Alpha Star now leads with 142 career eliminations",
            }
        ]),
    )

    assert beat.title == "Records Ratified"
    assert "Alpha Star" in beat.body
    assert "142" in beat.body


def test_offseason_records_ratified_beat_renders_empty_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("records_ratified"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        records_payload_json="[]",
    )

    assert beat.title == "Records Ratified"
    assert "No new records" in beat.body or "No league records" in beat.body


def test_offseason_hof_induction_beat_renders_persisted_payload():
    import json as _json

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("hof_induction"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        hof_payload_json=_json.dumps([
            {
                "player_id": "p1",
                "player_name": "Eternal Captain",
                "induction_season": "season_1",
                "legacy_score": 138.5,
                "threshold": 120.0,
                "reasons": ["longevity", "championship pedigree"],
                "seasons_played": 9,
                "championships": 2,
                "awards_won": 3,
                "total_eliminations": 240,
            }
        ]),
    )

    assert beat.title == "Hall of Fame Induction"
    assert "Eternal Captain" in beat.body
    assert "138" in beat.body  # legacy score


def test_offseason_hof_induction_beat_renders_empty_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("hof_induction"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        hof_payload_json="[]",
    )

    assert beat.title == "Hall of Fame Induction"
    assert "No new inductees" in beat.body or "no qualifying" in beat.body.lower()


def test_offseason_rookie_class_preview_beat_renders_persisted_payload():
    import json as _json

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("rookie_class_preview"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        rookie_preview_payload_json=_json.dumps({
            "season_id": "season_1",
            "class_year": 2,
            "source": "prospect_pool",
            "class_size": 12,
            "archetype_distribution": {"Sharpshooter": 5, "Enforcer": 4, "Ball Hawk": 3},
            "top_band_depth": 4,
            "free_agent_count": 6,
            "storylines": [
                {
                    "template_id": "archetype_demand",
                    "sentence": "Sharpshooter in heavy demand: 4 of 6 clubs prioritizing them this off-season",
                    "fact": {"archetype": "Sharpshooter", "count": 4, "total": 6},
                }
            ],
        }),
    )

    assert beat.title == "Rookie Class Preview"
    assert "12" in beat.body  # class size
    assert "Sharpshooter" in beat.body
    assert "heavy demand" in beat.body


def test_initialize_manager_offseason_runs_three_new_computations_once():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    season = load_season(conn, "season_1")

    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    assert get_state(conn, "offseason_records_ratified_for") == "season_1"
    assert get_state(conn, "offseason_hof_inducted_for") == "season_1"
    assert get_state(conn, "offseason_rookie_preview_for") == "season_1"

    # Re-entry does NOT recompute
    before_records = get_state(conn, "offseason_records_ratified_json")
    before_hof = get_state(conn, "offseason_hof_inducted_json")
    before_preview = get_state(conn, "offseason_rookie_preview_json")
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)
    assert get_state(conn, "offseason_records_ratified_json") == before_records
    assert get_state(conn, "offseason_hof_inducted_json") == before_hof
    assert get_state(conn, "offseason_rookie_preview_json") == before_preview


def test_offseason_rookie_class_preview_beat_renders_empty_state():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)

    beat = build_offseason_ceremony_beat(
        OFFSEASON_CEREMONY_BEATS.index("rookie_class_preview"),
        load_season(conn, "season_1"),
        clubs,
        rosters,
        [],
        [],
        "aurora",
        rookie_preview_payload_json="{}",
    )

    assert beat.title == "Rookie Class Preview"
    assert "No incoming class data" in beat.body


def test_resume_at_each_new_beat_renders_persisted_payload():
    """Spec §7: re-entering off-season at any of the three new beats reads the
    stored payload, never recomputes."""
    from dataclasses import replace
    from dodgeball_sim.persistence import save_prospect_pool, save_player_career_stats, save_retired_player
    from dodgeball_sim.scouting_center import Prospect

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    season = load_season(conn, "season_1")

    # Seed a HoF candidate
    save_player_career_stats(
        conn,
        "hof_p",
        {
            "player_id": "hof_p",
            "player_name": "Captain Legacy",
            "seasons_played": 9,
            "championships": 2,
            "awards_won": 4,
            "total_matches": 110,
            "total_eliminations": 250,
            "total_catches_made": 100,
            "total_dodges_successful": 120,
            "total_times_eliminated": 50,
            "peak_eliminations": 30,
            "career_eliminations": 250,
            "career_catches": 100,
            "career_dodges": 120,
            "clubs_served": 1,
        },
    )
    aurora_first = next(iter(rosters["aurora"]))
    save_retired_player(conn, replace(aurora_first, id="hof_p", name="Captain Legacy"), "season_1", "age_decline")

    # Seed a prospect pool for class_year=2 so the rookie preview has data
    save_prospect_pool(conn, [
        Prospect(
            player_id="r1",
            class_year=2,
            name="Rookie One",
            age=18,
            hometown="Anywhere",
            hidden_ratings={k: 70.0 for k in ("accuracy", "power", "dodge", "catch", "stamina")},
            hidden_trajectory="normal",
            hidden_traits=[],
            public_archetype_guess="Sharpshooter",
            public_ratings_band={k: (75, 85) for k in ("accuracy", "power", "dodge", "catch", "stamina")},
        ),
    ])
    conn.commit()

    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)

    # Snapshot persisted state
    records_json = get_state(conn, "offseason_records_ratified_json")
    hof_json = get_state(conn, "offseason_hof_inducted_json")
    preview_json = get_state(conn, "offseason_rookie_preview_json")

    # Render each new beat: simulates resume after app restart
    rosters_after = load_all_rosters(conn)
    for beat_key in ("records_ratified", "hof_induction", "rookie_class_preview"):
        idx = OFFSEASON_CEREMONY_BEATS.index(beat_key)
        beat = build_offseason_ceremony_beat(
            idx,
            season,
            clubs,
            rosters_after,
            [],
            [],
            "aurora",
            records_payload_json=records_json,
            hof_payload_json=hof_json,
            rookie_preview_payload_json=preview_json,
        )
        assert beat.key == beat_key
        assert beat.body  # not empty

    # And: re-running initialize_manager_offseason does not change the persisted payloads
    initialize_manager_offseason(conn, season, clubs, rosters_after, root_seed=20260426)
    assert get_state(conn, "offseason_records_ratified_json") == records_json
    assert get_state(conn, "offseason_hof_inducted_json") == hof_json
    assert get_state(conn, "offseason_rookie_preview_json") == preview_json
