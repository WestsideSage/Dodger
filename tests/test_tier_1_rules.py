from dodgeball_sim.tier_1_rules import TIER_1_RULES, TierRules


def test_tier_1_id():
    assert TIER_1_RULES.tier_id == "local_rec_league"
    assert TIER_1_RULES.display_name == "Local Rec League"


def test_tier_1_team_and_ball_counts():
    assert TIER_1_RULES.team_size == 6
    assert TIER_1_RULES.ball_count == 6
    assert TIER_1_RULES.balls_per_side_at_rush == 3


def test_tier_1_headshot_inverted():
    assert TIER_1_RULES.headshot_thrower_out is True


def test_tier_1_no_refs_no_discipline():
    assert TIER_1_RULES.refs_present is False
    assert TIER_1_RULES.discipline_modeled is False
    assert TIER_1_RULES.no_blocking_mode_enabled is False


def test_tier_1_chaos_retrieval():
    assert TIER_1_RULES.designated_retriever is False


def test_tier_1_burden_not_modeled():
    assert TIER_1_RULES.burden_modeled is False


def test_tier_1_game_end():
    assert TIER_1_RULES.time_cap_seconds == 300  # 5 min
    assert TIER_1_RULES.match_format == "single_game"


def test_tier_1_stall_cap():
    from dodgeball_sim.stall_timer import STALL_CAP_SECONDS
    assert TIER_1_RULES.stall_cap_seconds == STALL_CAP_SECONDS


def test_rules_dataclass_is_frozen():
    import dataclasses
    assert TierRules.__dataclass_params__.frozen is True
