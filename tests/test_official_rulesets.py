import pytest

from dodgeball_sim.models import MatchSetup, Player, PlayerRatings, Team
from dodgeball_sim.player_state import (
    OfficialSetupValidationError,
    initial_states,
    validate_starters,
)
from dodgeball_sim.rulesets import (
    CLOTH_OPEN,
    FOAM_OPEN,
    NO_STING_OPEN,
    BallMaterial,
    DivisionType,
    Gender,
    mixed_division,
    profile_by_name,
)


def test_foam_profile():
    assert FOAM_OPEN.material == BallMaterial.FOAM
    assert FOAM_OPEN.ball_count == 6
    assert FOAM_OPEN.burden_majority_threshold == 4
    assert FOAM_OPEN.roster_rule.starters == 6


def test_no_sting_profile_matches_foam_counts():
    assert NO_STING_OPEN.ball_count == 6
    assert NO_STING_OPEN.burden_majority_threshold == 4
    # foam vs no-sting must remain distinct materials
    assert NO_STING_OPEN.material == BallMaterial.NO_STING
    assert NO_STING_OPEN.material != FOAM_OPEN.material


def test_cloth_profile():
    assert CLOTH_OPEN.material == BallMaterial.CLOTH
    assert CLOTH_OPEN.ball_count == 5
    assert CLOTH_OPEN.burden_majority_threshold == 3


def test_profile_by_name_roundtrip():
    assert profile_by_name("foam-open") is FOAM_OPEN
    with pytest.raises(KeyError):
        profile_by_name("does-not-exist")


def test_mixed_starters_reject_four_of_one_gender():
    profile = mixed_division(FOAM_OPEN)
    starters = [
        ("p1", Gender.MALE),
        ("p2", Gender.MALE),
        ("p3", Gender.MALE),
        ("p4", Gender.MALE),
        ("p5", Gender.FEMALE),
        ("p6", Gender.FEMALE),
    ]
    with pytest.raises(OfficialSetupValidationError):
        validate_starters(profile, starters)


def test_mixed_starters_allow_three_three():
    profile = mixed_division(FOAM_OPEN)
    starters = [
        ("p1", Gender.MALE),
        ("p2", Gender.MALE),
        ("p3", Gender.MALE),
        ("p4", Gender.FEMALE),
        ("p5", Gender.FEMALE),
        ("p6", Gender.FEMALE),
    ]
    validate_starters(profile, starters)


def test_mixed_starters_allow_three_two_when_only_two_of_gender_available():
    profile = mixed_division(FOAM_OPEN)
    # Roster has only 2 females total -> 4M/2F should be allowed because the
    # 3-cap on males cannot be met with only 2 females available.
    starters = [
        ("p1", Gender.MALE),
        ("p2", Gender.MALE),
        ("p3", Gender.MALE),
        ("p4", Gender.MALE),
        ("p5", Gender.FEMALE),
        ("p6", Gender.FEMALE),
    ]
    roster_genders = [
        Gender.MALE,
        Gender.MALE,
        Gender.MALE,
        Gender.MALE,
        Gender.MALE,
        Gender.MALE,
        Gender.FEMALE,
        Gender.FEMALE,
    ]
    validate_starters(profile, starters, roster_genders=roster_genders)


def test_mixed_starters_count_must_match_profile():
    profile = mixed_division(FOAM_OPEN)
    with pytest.raises(OfficialSetupValidationError):
        validate_starters(profile, [("p1", Gender.MALE)])


def test_mixed_starters_rejects_duplicates():
    profile = mixed_division(FOAM_OPEN)
    starters = [
        ("p1", Gender.MALE),
        ("p1", Gender.MALE),
        ("p3", Gender.MALE),
        ("p4", Gender.FEMALE),
        ("p5", Gender.FEMALE),
        ("p6", Gender.FEMALE),
    ]
    with pytest.raises(OfficialSetupValidationError):
        validate_starters(profile, starters)


def test_initial_states_marks_starters_active_and_nonstarters_inactive():
    states = initial_states(
        starters=[("p1", "A", Gender.MALE), ("p2", "A", Gender.FEMALE)],
        nonstarters=[("p3", "A", None)],
    )
    by_id = {s.player_id: s for s in states}
    assert by_id["p1"].is_starter and by_id["p1"].is_live_for_hits()
    assert by_id["p3"].is_starter is False
    assert by_id["p3"].is_live_for_hits() is False


def _team(prefix: str) -> Team:
    players = tuple(
        Player(id=f"{prefix}{i}", name=f"{prefix} {i}", ratings=PlayerRatings(50, 50, 50, 50))
        for i in range(6)
    )
    return Team(id=prefix, name=prefix, players=players)


def test_generic_match_setup_unchanged():
    # Phase 1 must not change the existing MatchSetup contract.
    setup = MatchSetup(team_a=_team("A"), team_b=_team("B"))
    assert setup.config_version == "phase1.v1"
    assert setup.team_a.id == "A"
    assert setup.team_b.id == "B"
