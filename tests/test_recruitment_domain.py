from __future__ import annotations

from dataclasses import replace

from dodgeball_sim.scouting_center import Prospect


def _prospect(
    player_id: str,
    public_ovr: tuple[int, int],
    public_archetype: str,
    *,
    hidden_accuracy: float = 70.0,
    hidden_power: float = 70.0,
) -> Prospect:
    return Prospect(
        player_id=player_id,
        class_year=1,
        name=player_id,
        age=18,
        hometown="Test",
        hidden_ratings={
            "accuracy": hidden_accuracy,
            "power": hidden_power,
            "dodge": 55.0,
            "catch": 55.0,
            "stamina": 55.0,
        },
        hidden_trajectory="GENERATIONAL",
        hidden_traits=["CLUTCH"],
        public_archetype_guess=public_archetype,
        public_ratings_band={"ovr": public_ovr},
    )


def test_build_recruitment_profile_is_deterministic_and_distinct_by_club():
    from dodgeball_sim.recruitment_domain import build_recruitment_profile

    first = build_recruitment_profile(20260428, "aurora")
    second = build_recruitment_profile(20260428, "aurora")
    other = build_recruitment_profile(20260428, "zephyr")

    assert first == second
    assert first.club_id == "aurora"
    assert set(first.archetype_priorities) == {
        "Sharpshooter",
        "Enforcer",
        "Escape Artist",
        "Ball Hawk",
        "Iron Engine",
    }
    assert first != other


def test_board_ranking_uses_public_prospect_data_and_public_noise_only():
    from dodgeball_sim.recruitment_domain import RecruitmentProfile, build_recruitment_board

    profile = RecruitmentProfile(
        club_id="aurora",
        archetype_priorities={
            "Sharpshooter": 1.0,
            "Enforcer": 0.0,
            "Escape Artist": 0.0,
            "Ball Hawk": 0.0,
            "Iron Engine": 0.0,
        },
        risk_tolerance=0.5,
        prestige=0.5,
        playing_time_pitch=0.5,
        evaluation_quality=1.0,
    )
    public_star = _prospect("p_public_star", (76, 84), "Sharpshooter", hidden_accuracy=45.0)
    hidden_star = _prospect("p_hidden_star", (58, 62), "Enforcer", hidden_accuracy=99.0, hidden_power=99.0)

    board = build_recruitment_board(
        root_seed=99,
        season_id="season_1",
        profile=profile,
        prospects=[hidden_star, public_star],
        roster_needs={"Sharpshooter": 1.0, "Enforcer": 0.0},
    )

    assert [row.player_id for row in board] == ["p_public_star", "p_hidden_star"]

    changed_truth = replace(public_star, hidden_ratings={key: 1.0 for key in public_star.hidden_ratings})
    unchanged_truth_board = build_recruitment_board(
        root_seed=99,
        season_id="season_1",
        profile=profile,
        prospects=[changed_truth],
        roster_needs={"Sharpshooter": 1.0},
    )
    original_truth_board = build_recruitment_board(
        root_seed=99,
        season_id="season_1",
        profile=profile,
        prospects=[public_star],
        roster_needs={"Sharpshooter": 1.0},
    )

    assert unchanged_truth_board[0] == original_truth_board[0]


def test_build_recruitment_board_uses_v4_lower_need_weight():
    from dodgeball_sim.recruitment_domain import RecruitmentProfile, build_recruitment_board

    prospect = _prospect("p1", (60, 60), "Enforcer")
    profile = RecruitmentProfile(
        club_id="aurora",
        archetype_priorities={"Enforcer": 0.0},
        risk_tolerance=0.0,
        prestige=0.5,
        playing_time_pitch=0.5,
        evaluation_quality=1.0,
    )

    row = build_recruitment_board(
        20260426,
        "season_1",
        profile,
        [prospect],
        {"Enforcer": 1.0},
    )[0]

    assert row.need_score == 4.0
    assert row.visible_reason == "club need 4.00; public fit 0.00"


def test_evaluation_quality_only_reduces_public_score_noise():
    from dodgeball_sim.recruitment_domain import RecruitmentProfile, build_recruitment_board

    prospect = _prospect("p_noisy", (60, 80), "Ball Hawk")
    base_profile = RecruitmentProfile(
        club_id="aurora",
        archetype_priorities={"Ball Hawk": 0.0},
        risk_tolerance=0.5,
        prestige=0.5,
        playing_time_pitch=0.5,
        evaluation_quality=0.0,
    )
    low_quality = build_recruitment_board(
        123,
        "season_1",
        base_profile,
        [prospect],
        roster_needs={},
    )[0]
    high_quality = build_recruitment_board(
        123,
        "season_1",
        replace(base_profile, evaluation_quality=1.0),
        [prospect],
        roster_needs={},
    )[0]

    public_midpoint = 70.0
    assert abs(high_quality.public_score - public_midpoint) <= abs(low_quality.public_score - public_midpoint)
    assert high_quality.need_score == low_quality.need_score
    assert high_quality.preference_score == low_quality.preference_score


def test_prepare_ai_offers_uses_persistable_board_payload_without_rerolling():
    from dodgeball_sim.recruitment_domain import (
        RecruitmentBoardRow,
        RecruitmentProfile,
        prepare_ai_offers,
    )

    profiles = [
        RecruitmentProfile("aurora", {"Sharpshooter": 1.0}, 0.3, 0.7, 0.8, 0.9),
        RecruitmentProfile("zephyr", {"Enforcer": 1.0}, 0.6, 0.4, 0.5, 0.7),
    ]
    boards = {
        "aurora": [
            RecruitmentBoardRow("aurora", "p1", 1, 80.0, 10.0, 10.0, 100.0, "need:10.00; fit:10.00"),
        ],
        "zephyr": [
            RecruitmentBoardRow("zephyr", "p1", 1, 79.0, 8.0, 6.0, 93.0, "need:8.00; fit:6.00"),
            RecruitmentBoardRow("zephyr", "p2", 2, 77.0, 6.0, 6.0, 89.0, "need:6.00; fit:6.00"),
        ],
    }

    first = prepare_ai_offers(20260428, "season_1", 1, profiles, boards)
    second = prepare_ai_offers(20260428, "season_1", 1, profiles, boards)

    assert first == second
    assert [(offer.club_id, offer.player_id, offer.source) for offer in first] == [
        ("aurora", "p1", "ai"),
        ("zephyr", "p1", "ai"),
    ]
    assert all(offer.visible_reason for offer in first)


def test_resolve_recruitment_round_tie_breaks_without_user_hidden_advantage():
    from dodgeball_sim.recruitment_domain import RecruitmentOffer, resolve_recruitment_round

    user_offer = RecruitmentOffer(
        season_id="season_1",
        round_number=1,
        club_id="user",
        player_id="p1",
        offer_strength=100.0,
        source="user",
        need_score=5.0,
        playing_time_pitch=0.2,
        prestige=0.9,
        round_order_value=0.01,
        visible_reason="user choice",
    )
    ai_offer = RecruitmentOffer(
        season_id="season_1",
        round_number=1,
        club_id="ai",
        player_id="p1",
        offer_strength=100.0,
        source="ai",
        need_score=7.0,
        playing_time_pitch=0.1,
        prestige=0.1,
        round_order_value=0.99,
        visible_reason="higher need",
    )

    result = resolve_recruitment_round("season_1", 1, [ai_offer], user_offer=user_offer)

    assert [(signing.player_id, signing.club_id) for signing in result.signings] == [("p1", "ai")]
    assert result.snipes[0].player_id == "p1"
    assert "higher need" in result.snipes[0].visible_reason


def test_resolve_recruitment_round_tie_break_order_after_need_score():
    from dodgeball_sim.recruitment_domain import RecruitmentOffer, resolve_recruitment_round

    offers = [
        RecruitmentOffer("season_1", 1, "b_club", "p1", 50.0, "ai", 5.0, 0.5, 0.9, 0.1, "prestige edge"),
        RecruitmentOffer("season_1", 1, "a_club", "p1", 50.0, "ai", 5.0, 0.5, 0.9, 0.2, "club id fallback"),
        RecruitmentOffer("season_1", 1, "c_club", "p1", 50.0, "ai", 5.0, 0.7, 0.1, 0.9, "playing time edge"),
    ]

    result = resolve_recruitment_round("season_1", 1, offers)

    assert result.signings[0].club_id == "c_club"
