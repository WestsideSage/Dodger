from __future__ import annotations

from dataclasses import replace
import sqlite3

from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.manager_gui import initialize_manager_career
from dodgeball_sim.persistence import create_schema, load_all_rosters, load_prospect_pool
from dodgeball_sim import randomizer
from dodgeball_sim.recruitment import (
    build_transaction_event,
    generate_prospect_pool,
    generate_rookie_class,
    sign_prospect_to_club,
)
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.scouting_center import Trajectory

import pytest


def test_generate_rookie_class_is_seeded_and_marks_players_as_newcomers():
    seed = derive_seed(2026, "draft", "season_2026")
    rookies_a = generate_rookie_class("season_2026", DeterministicRNG(seed))
    rookies_b = generate_rookie_class("season_2026", DeterministicRNG(seed))

    assert rookies_a == rookies_b
    assert len(rookies_a) == 12
    assert len({player.id for player in rookies_a}) == 12
    assert len({player.name for player in rookies_a}) == 12
    assert all(player.newcomer is True for player in rookies_a)
    assert all(player.club_id is None for player in rookies_a)


def test_build_transaction_event_returns_structured_transaction_payload():
    event = build_transaction_event("sign", "player_1", "club_a")

    assert event.event_type == "transaction"
    assert event.action == "sign"
    assert event.player_id == "player_1"
    assert event.club_id == "club_a"


def test_generate_prospect_pool_produces_class_size():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    assert len(pool) == DEFAULT_SCOUTING_CONFIG.prospect_class_size


def test_generate_prospect_pool_is_deterministic():
    rng_a = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    rng_b = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool_a = generate_prospect_pool(class_year=1, rng=rng_a, config=DEFAULT_SCOUTING_CONFIG)
    pool_b = generate_prospect_pool(class_year=1, rng=rng_b, config=DEFAULT_SCOUTING_CONFIG)
    assert [p.player_id for p in pool_a] == [p.player_id for p in pool_b]
    assert [p.hidden_trajectory for p in pool_a] == [p.hidden_trajectory for p in pool_b]


def test_generate_prospect_pool_player_ids_globally_unique_per_class():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "5"))
    pool = generate_prospect_pool(class_year=5, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    ids = [p.player_id for p in pool]
    names = [p.name for p in pool]
    assert len(set(ids)) == len(ids)
    assert len(set(names)) == len(names)
    assert all(f"_class{5}_" in pid or pid.startswith("prospect_5_") for pid in ids)


def test_generate_prospect_pool_includes_all_trajectory_tiers_in_long_run():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen_large", "1"))
    big_config = replace(DEFAULT_SCOUTING_CONFIG, prospect_class_size=1000)
    pool = generate_prospect_pool(class_year=1, rng=rng, config=big_config)
    counts = {t.value: 0 for t in Trajectory}
    for prospect in pool:
        counts[prospect.hidden_trajectory] += 1

    for tier in Trajectory:
        assert counts[tier.value] > 0, f"No {tier.value} prospects in 1000-prospect class"
    assert 5 <= counts["GENERATIONAL"] <= 25
    assert 650 <= counts["NORMAL"] <= 750


def test_generate_prospect_pool_public_baseline_band_width_matches_config():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen", "1"))
    pool = generate_prospect_pool(class_year=1, rng=rng, config=DEFAULT_SCOUTING_CONFIG)
    half_width = DEFAULT_SCOUTING_CONFIG.public_baseline_band_half_width
    for prospect in pool:
        low, high = prospect.public_ratings_band["ovr"]
        assert high - low == 2 * half_width


def test_generate_prospect_pool_some_archetypes_mislabeled():
    rng = DeterministicRNG(derive_seed(20260426, "mislabel_check", "1"))
    big_config = replace(DEFAULT_SCOUTING_CONFIG, prospect_class_size=1000)
    pool = generate_prospect_pool(class_year=1, rng=rng, config=big_config)
    mislabel_count = sum(1 for prospect in pool if prospect.public_archetype_guess != prospect.true_archetype())
    assert 100 <= mislabel_count <= 200


def test_generate_prospect_pool_display_names_unique_within_class():
    rng = DeterministicRNG(derive_seed(20260426, "prospect_gen_unique", "1"))
    big_config = replace(DEFAULT_SCOUTING_CONFIG, prospect_class_size=24)
    pool = generate_prospect_pool(class_year=1, rng=rng, config=big_config)
    names = [p.name for p in pool]
    assert len(set(names)) == len(names), "Prospect display names must be unique within a class"


def test_generate_rookie_class_display_names_unique_within_class():
    seed = derive_seed(2026, "draft", "season_2026_unique")
    rookies = generate_rookie_class("season_2026", DeterministicRNG(seed), size=24)
    names = [p.name for p in rookies]
    assert len(set(names)) == len(names), "Rookie display names must be unique within a class"


def test_randomizer_name_and_team_pools_have_v4_depth():
    assert len(randomizer._FIRST_NAMES) >= 64
    assert len(randomizer._LAST_NAMES) >= 64
    assert len(randomizer._TEAM_NAMES) >= 24
    assert len(randomizer._SUFFIXES) >= 22


def test_sign_prospect_to_club_rejects_duplicate_signed_flag():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    prospect = load_prospect_pool(conn, class_year=1)[0]

    signed = sign_prospect_to_club(conn, prospect, "aurora", season_num=1)

    with pytest.raises(ValueError, match="already signed"):
        sign_prospect_to_club(conn, prospect, "lunar", season_num=1)

    rosters = load_all_rosters(conn)
    owned_copies = [
        player
        for roster in rosters.values()
        for player in roster
        if player.id == signed.id
    ]
    assert len(owned_copies) == 1
    assert owned_copies[0].club_id == "aurora"
