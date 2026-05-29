"""Unit tests for the V14 pre-match Tactical Diff.

The headline guarantee is fog-of-war: the opponent's hidden command policy for
the upcoming match must never surface in the diff. These tests exercise the
pure builder with synthetic policies — no match or database required.
"""

import inspect
import json

from dodgeball_sim.tactical_diff import build_tactical_diff

PLAYER_POLICY = {
    "approach": "aggressive",
    "target_focus": "their_stars",
    "catch_posture": "go_for_catches",
    "rush_commit": "all_in",
    "rush_target": "strongest_side",
}

# A *hidden* opponent policy with values that are deliberately distinct from the
# player's, so any leak would be unmistakable in the serialized output.
HIDDEN_OPPONENT_POLICY = {
    "approach": "patient",
    "target_focus": "ball_holders",
    "catch_posture": "play_safe",
    "rush_commit": "hold_back",
    "rush_target": "nearest",
}


def test_builder_has_no_opponent_policy_parameter():
    # Structural fog-of-war guarantee: there is no way to feed the opponent's
    # hidden policy into the diff.
    params = set(inspect.signature(build_tactical_diff).parameters)
    assert "opponent_policy" not in params
    assert all("opponent_policy" not in p for p in params)


def test_player_plan_reflects_player_policy_only():
    diff = build_tactical_diff(player_policy=PLAYER_POLICY)
    by_axis = {row["axis"]: row for row in diff["player_plan"]}
    assert by_axis["approach"]["player_value"] == "Aggressive"
    assert by_axis["target_focus"]["player_value"] == "Their stars"
    # Every opponent axis is explicitly unscouted.
    assert all(row["opponent_value"] is None for row in diff["player_plan"])
    assert all(row["opponent_known"] is False for row in diff["player_plan"])


def test_no_intel_means_unscouted():
    diff = build_tactical_diff(player_policy=PLAYER_POLICY)
    assert diff["opponent_unscouted"] is True
    assert diff["opponent_intel"] == []
    assert "unscouted" in diff["note"].lower()


def test_adaptation_summary_surfaces_as_intel():
    diff = build_tactical_diff(
        player_policy=PLAYER_POLICY,
        adaptation_summary="They adapted toward safer catches after last week.",
    )
    assert diff["opponent_unscouted"] is False
    sources = {item["source"] for item in diff["opponent_intel"]}
    assert "adaptation" in sources


def test_prior_meeting_surfaces_only_when_real():
    first = build_tactical_diff(
        player_policy=PLAYER_POLICY,
        has_prior_meeting=False,
        last_meeting="First meeting - no tape on them yet.",
    )
    assert first["opponent_intel"] == []

    prior = build_tactical_diff(
        player_policy=PLAYER_POLICY,
        has_prior_meeting=True,
        last_meeting="Week 3: Win 5-2",
    )
    sources = {item["source"] for item in prior["opponent_intel"]}
    assert "prior_meeting" in sources


def test_hidden_opponent_policy_values_never_leak():
    # Even when intel is present, none of the opponent's hidden per-axis policy
    # values may appear anywhere in the serialized diff.
    diff = build_tactical_diff(
        player_policy=PLAYER_POLICY,
        adaptation_summary="They adapted their pressure.",
        has_prior_meeting=True,
        last_meeting="Week 3: Win 5-2",
    )
    serialized = json.dumps(diff).lower()
    leaking = {
        value
        for axis, value in HIDDEN_OPPONENT_POLICY.items()
        if value != PLAYER_POLICY[axis]  # ignore values shared with the player
        and value.replace("_", " ") in serialized
    }
    assert not leaking, f"hidden opponent policy leaked: {leaking}"
