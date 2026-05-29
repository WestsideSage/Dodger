"""Pre-match Tactical Diff (V14).

Compares the player's fully-known command policy against what is *legitimately
observable* about the opponent. Fog-of-war is the headline constraint: the
opponent's live hidden ``CoachPolicy`` for the upcoming match must never reach
this module. The only opponent signals allowed here are ones the player has
already been shown:

* the V12 adaptation summary (already player-facing), and
* the existence/result of a prior meeting (public match record).

Per-axis opponent tendencies are reported as "unscouted" unless a sanctioned
source supplies them, because the engine does not expose scouted opponent
tactics. This keeps the panel honest rather than fabricating a comparison.
"""

from __future__ import annotations

from typing import Any, Mapping

_AXIS_ORDER = ("approach", "target_focus", "catch_posture", "rush_commit", "rush_target")

_AXIS_LABELS = {
    "approach": "Approach",
    "target_focus": "Target Focus",
    "catch_posture": "Catch Posture",
    "rush_commit": "Opening Rush",
    "rush_target": "Rush Target",
}


def _humanize(value: Any) -> str:
    text = str(value).replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else "-"


def build_tactical_diff(
    *,
    player_policy: Mapping[str, Any],
    adaptation_summary: str | None = None,
    has_prior_meeting: bool = False,
    last_meeting: str | None = None,
) -> dict[str, Any]:
    """Build the tactical diff payload from the player's policy and allowed intel.

    ``player_policy`` is the player's own command policy as a mapping of axis ->
    value (e.g. ``CoachPolicy.as_dict()``). No opponent policy is accepted: the
    opponent column is derived solely from the sanctioned, already-player-facing
    signals passed explicitly here.
    """
    rows: list[dict[str, Any]] = []
    for axis in _AXIS_ORDER:
        rows.append(
            {
                "axis": axis,
                "label": _AXIS_LABELS[axis],
                "player_value": _humanize(player_policy.get(axis, "-")),
                # No sanctioned per-axis opponent read exists, so every axis is
                # explicitly unscouted. This is intentional fog-of-war honesty.
                "opponent_value": None,
                "opponent_known": False,
            }
        )

    intel: list[dict[str, str]] = []
    if adaptation_summary:
        intel.append({"source": "adaptation", "text": str(adaptation_summary)})
    if has_prior_meeting and last_meeting:
        intel.append({"source": "prior_meeting", "text": str(last_meeting)})

    opponent_unscouted = len(intel) == 0
    if opponent_unscouted:
        note = "No reliable tape on their plan yet — opponent tendencies are unscouted. Trust your reads."
    else:
        note = "Opponent reads below come only from prior tape and observed adaptations, not their hidden plan."

    return {
        "player_plan": rows,
        "opponent_intel": intel,
        "opponent_unscouted": opponent_unscouted,
        "note": note,
    }


__all__ = ["build_tactical_diff"]
