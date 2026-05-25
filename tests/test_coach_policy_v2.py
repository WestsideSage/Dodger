from __future__ import annotations

import pytest

from dodgeball_sim.models import CoachPolicy


def test_coach_policy_v2_defaults_and_roundtrip_use_string_enums():
    expected = {
        "approach": "mixed",
        "target_focus": "spread",
        "catch_posture": "opportunistic",
        "rush_commit": "balanced",
        "rush_target": "center",
    }

    policy = CoachPolicy()

    assert policy.as_dict() == expected
    assert CoachPolicy.from_dict(expected) == policy


def test_coach_policy_v2_from_dict_still_rejects_legacy_payloads():
    """from_dict remains strict — API calls must not silently accept stale payloads."""
    legacy_payload = {
        "target_stars": 0.7,
        "target_ball_holder": 0.5,
        "risk_tolerance": 0.5,
        "sync_throws": 0.2,
        "rush_frequency": 0.5,
        "rush_proximity": 0.5,
        "tempo": 0.5,
        "catch_bias": 0.5,
    }
    with pytest.raises(ValueError, match="target_stars"):
        CoachPolicy.from_dict(legacy_payload)


def test_coach_policy_v2_from_legacy_dict_returns_defaults():
    """from_legacy_dict is the persistence migration path — always returns v2 defaults."""
    assert CoachPolicy.from_legacy_dict({}) == CoachPolicy()
    assert CoachPolicy.from_legacy_dict({"target_stars": 0.9}) == CoachPolicy()


def test_coach_policy_v2_rejects_unknown_or_missing_values():
    with pytest.raises(ValueError, match="approach"):
        CoachPolicy.from_dict(
            {
                "approach": "reckless",
                "target_focus": "spread",
                "catch_posture": "opportunistic",
                "rush_commit": "balanced",
                "rush_target": "center",
            }
        )

    with pytest.raises(ValueError, match="rush_target"):
        CoachPolicy.from_dict(
            {
                "approach": "mixed",
                "target_focus": "spread",
                "catch_posture": "opportunistic",
                "rush_commit": "balanced",
            }
        )
