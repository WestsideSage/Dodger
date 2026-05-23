from __future__ import annotations

from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.official_tactics import (
    _catch_thresholds,
    _target_base,
    _thrower_base,
    _tempo_level,
)


def test_v2_policy_mapping_preserves_documented_branch_choices():
    aggressive = CoachPolicy(approach="aggressive", target_focus="their_stars", catch_posture="go_for_catches")
    patient = CoachPolicy(approach="patient", target_focus="spread", catch_posture="play_safe")
    mixed = CoachPolicy(approach="mixed", target_focus="ball_holders", catch_posture="opportunistic")

    accuracy_player = _player(accuracy=90, power=30)
    power_player = _player(accuracy=30, power=90)
    assert _thrower_base(aggressive, power_player) > _thrower_base(aggressive, accuracy_player)
    assert _thrower_base(patient, accuracy_player) > _thrower_base(patient, power_player)
    assert _tempo_level(aggressive) > _tempo_level(mixed) > _tempo_level(patient)

    star_branch = _target_base(
        aggressive,
        normalized_overall=0.9,
        vulnerability=0.1,
        is_recent_pressure_target=False,
    )
    scrub_branch = _target_base(
        aggressive,
        normalized_overall=0.3,
        vulnerability=0.1,
        is_recent_pressure_target=False,
    )
    holder_branch = _target_base(
        mixed,
        normalized_overall=0.4,
        vulnerability=0.1,
        is_recent_pressure_target=True,
    )
    non_holder_branch = _target_base(
        mixed,
        normalized_overall=0.4,
        vulnerability=0.1,
        is_recent_pressure_target=False,
    )
    spread_branch = _target_base(
        patient,
        normalized_overall=0.9,
        vulnerability=0.7,
        is_recent_pressure_target=False,
    )
    assert star_branch > scrub_branch
    assert holder_branch > non_holder_branch
    assert spread_branch > 0.7

    go_for_catches_threshold, _ = _catch_thresholds(aggressive)
    safe_threshold, _ = _catch_thresholds(patient)
    opportunistic_threshold, _ = _catch_thresholds(mixed)
    assert go_for_catches_threshold < opportunistic_threshold < safe_threshold


def _player(*, accuracy: float = 80, power: float = 60):
    from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings

    return Player(
        id="p",
        name="Player",
        club_id="A",
        archetype=PlayerArchetype.CATCHER,
        ratings=PlayerRatings(
            accuracy=accuracy,
            power=power,
            dodge=60,
            catch=60,
            stamina=60,
            tactical_iq=60,
            catch_courage=60,
            throw_selection_iq=60,
            conditioning_curve=60,
        ),
    )
