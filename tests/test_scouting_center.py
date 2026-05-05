from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG, ScoutingBalanceConfig
from dodgeball_sim.scouting_center import (
    CeilingLabel,
    DEFAULT_SCOUT_PROFILES,
    Prospect,
    Scout,
    ScoutAssignment,
    ScoutMode,
    ScoutPriority,
    ScoutStrategyState,
    ScoutingSnapshot,
    ScoutingState,
    ScoutingAxis,
    ScoutingTier,
    SeededScoutProfile,
    TraitSense,
    Trajectory,
    advance_scouting_snapshot,
    advance_scouting_state,
    apply_carry_forward_decay,
    ceiling_label_for_trajectory,
    ceiling_reveal_eligible,
    compute_scout_points_for_axis,
    pick_traits_to_reveal,
    select_auto_scout_target,
    tier_for_points,
)


def test_scouting_tier_enum_values():
    assert ScoutingTier.UNKNOWN.value == "UNKNOWN"
    assert ScoutingTier.GLIMPSED.value == "GLIMPSED"
    assert ScoutingTier.KNOWN.value == "KNOWN"
    assert ScoutingTier.VERIFIED.value == "VERIFIED"


def test_scouting_axis_enum_values():
    assert ScoutingAxis.RATINGS.value == "ratings"
    assert ScoutingAxis.ARCHETYPE.value == "archetype"
    assert ScoutingAxis.TRAITS.value == "traits"
    assert ScoutingAxis.TRAJECTORY.value == "trajectory"


def test_trajectory_ordering():
    order = [Trajectory.NORMAL, Trajectory.IMPACT, Trajectory.STAR, Trajectory.GENERATIONAL]
    assert [t.value for t in order] == ["NORMAL", "IMPACT", "STAR", "GENERATIONAL"]


def test_ceiling_label_values():
    assert CeilingLabel.HIGH_CEILING.value == "HIGH_CEILING"
    assert CeilingLabel.SOLID.value == "SOLID"
    assert CeilingLabel.STANDARD.value == "STANDARD"


def test_scout_mode_and_priority_values():
    assert ScoutMode.MANUAL.value == "MANUAL"
    assert ScoutMode.AUTO.value == "AUTO"
    assert ScoutPriority.TOP_PUBLIC_OVR.value == "TOP_PUBLIC_OVR"
    assert ScoutPriority.SPECIALTY_FIT.value == "SPECIALTY_FIT"
    assert ScoutPriority.USER_PINNED.value == "USER_PINNED"


def test_trait_sense_values():
    assert TraitSense.LOW.value == "LOW"
    assert TraitSense.MEDIUM.value == "MEDIUM"
    assert TraitSense.HIGH.value == "HIGH"


def test_default_scouting_config_has_documented_defaults():
    cfg = DEFAULT_SCOUTING_CONFIG
    assert isinstance(cfg, ScoutingBalanceConfig)
    assert cfg.tier_thresholds == {"GLIMPSED": 10, "KNOWN": 35, "VERIFIED": 70}
    assert cfg.weekly_scout_point_base == 5
    assert cfg.archetype_affinity_multiplier == 1.20
    assert cfg.archetype_weakness_multiplier == 0.80
    assert cfg.archetype_neutral_multiplier == 1.00
    assert cfg.trait_sense_multipliers == {"LOW": 0.70, "MEDIUM": 1.00, "HIGH": 1.30}
    assert cfg.jitter_min == 0.90
    assert cfg.jitter_max == 1.10
    assert cfg.trajectory_rates == {
        "NORMAL": 0.70,
        "IMPACT": 0.22,
        "STAR": 0.07,
        "GENERATIONAL": 0.01,
    }
    assert cfg.public_archetype_mislabel_rate == 0.15
    assert cfg.public_baseline_band_half_width == 25
    assert cfg.prospect_class_size == 25
    assert cfg.hidden_gem_ovr_floor == 8


def test_trajectory_rates_sum_to_one():
    rates = DEFAULT_SCOUTING_CONFIG.trajectory_rates
    assert abs(sum(rates.values()) - 1.0) < 1e-9


def test_scout_dataclass_construction():
    scout = Scout(
        scout_id="vera",
        name="Vera Khan",
        base_accuracy=1.05,
        archetype_affinities=("Enforcer",),
        archetype_weakness="Escape Artist",
        trait_sense="MEDIUM",
    )
    assert scout.scout_id == "vera"
    assert scout.archetype_affinities == ("Enforcer",)


def test_scouting_state_default_unknown():
    state = ScoutingState(
        player_id="prospect_1_001",
        ratings_tier="UNKNOWN",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=0,
    )
    assert state.ratings_tier == "UNKNOWN"
    assert state.scout_points["ratings"] == 0


def test_default_scout_profiles_three_seeded_distinctly():
    assert len(DEFAULT_SCOUT_PROFILES) == 3
    assert all(isinstance(profile, SeededScoutProfile) for profile in DEFAULT_SCOUT_PROFILES)
    ids = [profile.scout_id for profile in DEFAULT_SCOUT_PROFILES]
    assert ids == ["vera", "bram", "linnea"]

    vera, bram, linnea = DEFAULT_SCOUT_PROFILES
    assert "Enforcer" in vera.archetype_affinities
    assert vera.trait_sense == "MEDIUM"
    assert "Ball Hawk" in bram.archetype_affinities
    assert bram.trait_sense == "HIGH"
    assert linnea.trait_sense == "LOW"
    assert vera.base_accuracy > bram.base_accuracy


def test_scouting_snapshot_holds_all_runtime_state():
    snapshot = ScoutingSnapshot(
        prospects={},
        scouting_states={},
        revealed_traits={},
        ceiling_labels={},
        scouts={},
        assignments={},
        strategies={},
        contributions={},
    )
    assert snapshot.prospects == {}
    assert snapshot.scouting_states == {}


def test_advance_scouting_snapshot_is_pure_and_returns_persistence_plan():
    prospect = Prospect(
        player_id="prospect_1_001",
        class_year=1,
        name="Rin Voss",
        age=18,
        hometown="Voss",
        hidden_ratings={"accuracy": 90, "power": 88, "dodge": 86, "catch": 84, "stamina": 82},
        hidden_trajectory="STAR",
        hidden_traits=["IRONWALL"],
        public_archetype_guess="Enforcer",
        public_ratings_band={"ovr": (55, 95)},
    )
    scout = Scout(
        scout_id="vera",
        name="Vera Khan",
        base_accuracy=5.0,
        archetype_affinities=("Enforcer",),
        archetype_weakness="Escape Artist",
        trait_sense="HIGH",
    )
    snapshot = ScoutingSnapshot(
        prospects={prospect.player_id: prospect},
        scouting_states={},
        revealed_traits={},
        ceiling_labels={},
        scouts={scout.scout_id: scout},
        assignments={scout.scout_id: ScoutAssignment(scout.scout_id, prospect.player_id, 1)},
        strategies={},
        contributions={},
    )

    plan = advance_scouting_snapshot(
        snapshot,
        season=1,
        current_week=1,
        root_seed=20260426,
        config=DEFAULT_SCOUTING_CONFIG,
    )

    assert snapshot.scouting_states == {}
    assert plan.states_to_save[0].player_id == prospect.player_id
    assert any(event.event_type == "TIER_UP_RATINGS" for event in plan.events)
    assert plan.contributions_to_save[0].player_id == prospect.player_id


def test_assignment_and_strategy_dataclasses_construct():
    assignment = ScoutAssignment(scout_id="vera", player_id=None, started_week=0)
    strategy = ScoutStrategyState(
        scout_id="vera",
        mode=ScoutMode.MANUAL.value,
        priority=ScoutPriority.TOP_PUBLIC_OVR.value,
        archetype_filter=(),
        pinned_prospects=(),
    )
    assert assignment.player_id is None
    assert strategy.mode == "MANUAL"


def test_tier_for_points_respects_thresholds():
    assert tier_for_points(0, DEFAULT_SCOUTING_CONFIG) == "UNKNOWN"
    assert tier_for_points(9, DEFAULT_SCOUTING_CONFIG) == "UNKNOWN"
    assert tier_for_points(10, DEFAULT_SCOUTING_CONFIG) == "GLIMPSED"
    assert tier_for_points(34, DEFAULT_SCOUTING_CONFIG) == "GLIMPSED"
    assert tier_for_points(35, DEFAULT_SCOUTING_CONFIG) == "KNOWN"
    assert tier_for_points(69, DEFAULT_SCOUTING_CONFIG) == "KNOWN"
    assert tier_for_points(70, DEFAULT_SCOUTING_CONFIG) == "VERIFIED"
    assert tier_for_points(999, DEFAULT_SCOUTING_CONFIG) == "VERIFIED"


def test_compute_scout_points_neutral_scout_neutral_axis():
    scout = Scout(
        scout_id="x",
        name="Test",
        base_accuracy=1.00,
        archetype_affinities=(),
        archetype_weakness="",
        trait_sense="MEDIUM",
    )
    points = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Sharpshooter",
        axis="ratings",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert points == 5


def test_compute_scout_points_affinity_match_boosts():
    scout = Scout(
        scout_id="x",
        name="Test",
        base_accuracy=1.00,
        archetype_affinities=("Enforcer",),
        archetype_weakness="Escape Artist",
        trait_sense="MEDIUM",
    )
    points = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Enforcer",
        axis="ratings",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert points == 6


def test_compute_scout_points_weakness_penalizes():
    scout = Scout(
        scout_id="x",
        name="Test",
        base_accuracy=1.00,
        archetype_affinities=("Enforcer",),
        archetype_weakness="Escape Artist",
        trait_sense="MEDIUM",
    )
    points = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Escape Artist",
        axis="ratings",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert points == 4


def test_compute_scout_points_high_trait_sense_only_affects_traits_and_trajectory():
    scout = Scout(
        scout_id="x",
        name="Test",
        base_accuracy=1.00,
        archetype_affinities=(),
        archetype_weakness="",
        trait_sense="HIGH",
    )
    p_traits = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Sharpshooter",
        axis="traits",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    p_trajectory = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Sharpshooter",
        axis="trajectory",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    p_ratings = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Sharpshooter",
        axis="ratings",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    p_archetype = compute_scout_points_for_axis(
        scout=scout,
        prospect_archetype="Sharpshooter",
        axis="archetype",
        jitter=1.00,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert p_traits == 7
    assert p_trajectory == 7
    assert p_ratings == 5
    assert p_archetype == 5


def test_advance_scouting_state_accumulates_and_tiers_up():
    scout = Scout(
        scout_id="x",
        name="Test",
        base_accuracy=1.00,
        archetype_affinities=(),
        archetype_weakness="",
        trait_sense="MEDIUM",
    )
    state = ScoutingState(
        player_id="p1",
        ratings_tier="UNKNOWN",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=0,
    )
    new_state, _events = advance_scouting_state(
        state=state,
        scout=scout,
        prospect_archetype="Sharpshooter",
        week=1,
        seed=12345,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert new_state.scout_points["ratings"] == 5
    assert new_state.ratings_tier == "UNKNOWN"

    new_state2, events2 = advance_scouting_state(
        state=new_state,
        scout=scout,
        prospect_archetype="Sharpshooter",
        week=2,
        seed=12346,
        config=DEFAULT_SCOUTING_CONFIG,
    )
    assert new_state2.scout_points["ratings"] == 10
    assert new_state2.ratings_tier == "GLIMPSED"
    tier_up_events = [event for event in events2 if event["event_type"].startswith("TIER_UP_")]
    assert any(
        event["event_type"] == "TIER_UP_RATINGS" and event["payload"]["new_tier"] == "GLIMPSED"
        for event in tier_up_events
    )


def test_ceiling_label_mapping():
    assert ceiling_label_for_trajectory("NORMAL") == "STANDARD"
    assert ceiling_label_for_trajectory("IMPACT") == "SOLID"
    assert ceiling_label_for_trajectory("STAR") == "HIGH_CEILING"
    assert ceiling_label_for_trajectory("GENERATIONAL") == "HIGH_CEILING"


def test_ceiling_reveal_eligible_default_at_verified():
    assert ceiling_reveal_eligible("VERIFIED", "MEDIUM") is True
    assert ceiling_reveal_eligible("VERIFIED", "LOW") is True
    assert ceiling_reveal_eligible("KNOWN", "MEDIUM") is False
    assert ceiling_reveal_eligible("GLIMPSED", "HIGH") is False


def test_ceiling_reveal_eligible_high_trait_sense_at_known():
    assert ceiling_reveal_eligible("KNOWN", "HIGH") is True
    assert ceiling_reveal_eligible("VERIFIED", "HIGH") is True
    assert ceiling_reveal_eligible("GLIMPSED", "HIGH") is False
    assert ceiling_reveal_eligible("UNKNOWN", "HIGH") is False


def test_pick_traits_to_reveal_glimpsed_returns_at_most_one():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    revealed = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="GLIMPSED", root_seed=42)
    assert len(revealed) <= 1


def test_pick_traits_to_reveal_known_returns_at_most_two():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    revealed = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="KNOWN", root_seed=42)
    assert len(revealed) <= 2


def test_pick_traits_to_reveal_verified_returns_all():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    revealed = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="VERIFIED", root_seed=42)
    assert set(revealed) == set(traits)


def test_pick_traits_to_reveal_deterministic_per_player():
    traits = ("IRONWALL", "CLUTCH", "QUICK_RELEASE")
    a = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="GLIMPSED", root_seed=42)
    b = pick_traits_to_reveal(player_id="p1", true_traits=traits, tier="GLIMPSED", root_seed=42)
    assert a == b
    c = pick_traits_to_reveal(player_id="p2", true_traits=traits, tier="GLIMPSED", root_seed=42)
    c2 = pick_traits_to_reveal(player_id="p2", true_traits=traits, tier="GLIMPSED", root_seed=42)
    assert c == c2


def test_pick_traits_empty_traits_returns_empty():
    assert pick_traits_to_reveal(player_id="p1", true_traits=(), tier="VERIFIED", root_seed=1) == ()


def _make_prospect(pid: str, ovr_mid: int, archetype: str) -> Prospect:
    half = DEFAULT_SCOUTING_CONFIG.public_baseline_band_half_width
    return Prospect(
        player_id=pid,
        class_year=1,
        name=pid,
        age=18,
        hometown="Test",
        hidden_ratings={"accuracy": 60, "power": 60, "dodge": 60, "catch": 60, "stamina": 60},
        hidden_trajectory="NORMAL",
        hidden_traits=[],
        public_archetype_guess=archetype,
        public_ratings_band={"ovr": (ovr_mid - half, ovr_mid + half)},
    )


def test_select_auto_scout_target_top_public_ovr():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=85, archetype="Enforcer"),
        "p3": _make_prospect("p3", ovr_mid=60, archetype="Ball Hawk"),
    }
    scout = Scout("x", "Test", 1.0, (), "", "MEDIUM")
    strategy = ScoutStrategyState("x", "AUTO", "TOP_PUBLIC_OVR", (), ())
    target = select_auto_scout_target(
        scout=scout,
        strategy=strategy,
        prospects=pool,
        already_assigned_player_ids=set(),
        week=1,
        root_seed=42,
    )
    assert target == "p2"


def test_select_auto_scout_target_skips_already_assigned():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=85, archetype="Enforcer"),
    }
    scout = Scout("x", "Test", 1.0, (), "", "MEDIUM")
    strategy = ScoutStrategyState("x", "AUTO", "TOP_PUBLIC_OVR", (), ())
    target = select_auto_scout_target(
        scout=scout,
        strategy=strategy,
        prospects=pool,
        already_assigned_player_ids={"p2"},
        week=1,
        root_seed=42,
    )
    assert target == "p1"


def test_select_auto_scout_target_specialty_fit_only_picks_affinity():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=85, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=70, archetype="Enforcer"),
    }
    scout = Scout("x", "Test", 1.0, ("Enforcer",), "", "MEDIUM")
    strategy = ScoutStrategyState("x", "AUTO", "SPECIALTY_FIT", (), ())
    target = select_auto_scout_target(
        scout=scout,
        strategy=strategy,
        prospects=pool,
        already_assigned_player_ids=set(),
        week=1,
        root_seed=42,
    )
    assert target == "p2"


def test_select_auto_scout_target_specialty_fit_falls_back_when_empty():
    pool = {
        "p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter"),
        "p2": _make_prospect("p2", ovr_mid=85, archetype="Ball Hawk"),
    }
    scout = Scout("x", "Test", 1.0, ("Enforcer",), "", "MEDIUM")
    strategy = ScoutStrategyState("x", "AUTO", "SPECIALTY_FIT", (), ())
    target = select_auto_scout_target(
        scout=scout,
        strategy=strategy,
        prospects=pool,
        already_assigned_player_ids=set(),
        week=1,
        root_seed=42,
    )
    assert target == "p2"


def test_select_auto_scout_target_returns_none_when_no_eligible():
    pool = {"p1": _make_prospect("p1", ovr_mid=70, archetype="Sharpshooter")}
    scout = Scout("x", "Test", 1.0, (), "", "MEDIUM")
    strategy = ScoutStrategyState("x", "AUTO", "TOP_PUBLIC_OVR", (), ())
    target = select_auto_scout_target(
        scout=scout,
        strategy=strategy,
        prospects=pool,
        already_assigned_player_ids={"p1"},
        week=1,
        root_seed=42,
    )
    assert target is None


def test_decay_drops_each_axis_one_tier():
    state = ScoutingState(
        player_id="p1",
        ratings_tier="VERIFIED",
        archetype_tier="KNOWN",
        traits_tier="GLIMPSED",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 70, "archetype": 35, "traits": 10, "trajectory": 0},
        last_updated_week=14,
    )
    decayed = apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG)
    assert decayed.ratings_tier == "KNOWN"
    assert decayed.archetype_tier == "GLIMPSED"
    assert decayed.traits_tier == "UNKNOWN"
    assert decayed.trajectory_tier == "UNKNOWN"


def test_decay_caps_scout_points_at_new_tier_threshold():
    state = ScoutingState(
        player_id="p1",
        ratings_tier="VERIFIED",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 70, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=14,
    )
    decayed = apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG)
    assert decayed.scout_points["ratings"] == 35
    assert decayed.scout_points["archetype"] == 0


def test_decay_unknown_unchanged():
    state = ScoutingState(
        player_id="p1",
        ratings_tier="UNKNOWN",
        archetype_tier="UNKNOWN",
        traits_tier="UNKNOWN",
        trajectory_tier="UNKNOWN",
        scout_points={"ratings": 0, "archetype": 0, "traits": 0, "trajectory": 0},
        last_updated_week=14,
    )
    decayed = apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG)
    assert decayed.ratings_tier == "UNKNOWN"
    assert decayed.scout_points["ratings"] == 0
