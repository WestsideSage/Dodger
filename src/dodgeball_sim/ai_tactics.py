from __future__ import annotations

from typing import Dict, Optional


def get_ai_tactics(
    archetype: str,
    intent: str,
    *,
    drift: Optional[Dict[str, str]] = None,
) -> dict[str, str]:
    """Returns a tactics dictionary (CoachPolicy v2 dict format) based on the club's archetype and intent.

    Provides highly tailored game plans that align with the club's identity
    while adjusting for weekly tactical demands.

    V28 The Weather: ``drift`` is the resolved tactic-drift overlay for this
    club (from ``meta_drift.tactic_drift_for``). It folds in AFTER the intent
    override (precedence: archetype base → intent override → drift bias). The
    drift only changes which CoachPolicy values the AI plays — a real policy
    the engine already consumes — so determinism is preserved. ``None`` (the
    default for all existing callers) leaves the policy unchanged.
    """
    # Base policy selection by archetype
    if archetype == "Contender":
        policy = {
            "approach": "aggressive",
            "target_focus": "their_stars",
            "catch_posture": "go_for_catches",
            "rush_commit": "all_in",
            "rush_target": "center",
        }
    elif archetype == "Development Factory":
        policy = {
            "approach": "patient",
            "target_focus": "spread",
            "catch_posture": "opportunistic",
            "rush_commit": "balanced",
            "rush_target": "nearest",
        }
    elif archetype == "Defensive Specialist":
        policy = {
            "approach": "patient",
            "target_focus": "ball_holders",
            "catch_posture": "go_for_catches",
            "rush_commit": "hold_back",
            "rush_target": "nearest",
        }
    elif archetype == "Power Throwers":
        policy = {
            "approach": "aggressive",
            "target_focus": "their_stars",
            "catch_posture": "opportunistic",
            "rush_commit": "all_in",
            "rush_target": "center",
        }
    elif archetype == "Aging Veterans":
        policy = {
            "approach": "patient",
            "target_focus": "spread",
            "catch_posture": "play_safe",
            "rush_commit": "hold_back",
            "rush_target": "nearest",
        }
    else:  # Balanced Rebuild & default fallbacks
        policy = {
            "approach": "mixed",
            "target_focus": "spread",
            "catch_posture": "opportunistic",
            "rush_commit": "balanced",
            "rush_target": "center",
        }

    # Intent-based overrides to keep the plans reactive
    if intent == "Win Now":
        policy["approach"] = "aggressive"
        policy["rush_commit"] = "all_in"
    elif intent == "Preserve Health":
        policy["approach"] = "patient"
        policy["catch_posture"] = "play_safe"
        policy["rush_commit"] = "hold_back"
    elif intent == "Develop Youth":
        policy["target_focus"] = "spread"
        policy["catch_posture"] = "opportunistic"

    # V28 The Weather: drift overlay folds in last (precedence: archetype base
    # → intent override → drift bias). The drift only overrides dimensions it
    # explicitly specifies; others stay as archetype+intent determined.
    if drift:
        for dim, val in drift.items():
            if dim in policy and val:
                policy[dim] = val

    return policy
