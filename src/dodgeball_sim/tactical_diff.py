"""Pre-match Tactical Diff (V14, WT-30 scout reveal).

Compares the player's fully-known command policy against what is *legitimately
observable* about the opponent. Fog-of-war is the headline constraint: the
opponent's live hidden ``CoachPolicy`` for the upcoming match must never reach
this module. The only opponent signals allowed here are ones the player has
already been shown or has earned by watching the opponent play:

* the V12 adaptation summary (already player-facing),
* the existence/result of a prior meeting (public match record),
* **observed tendencies from tape** — the opponent's *historical* coach policy
  aggregated from PAST completed matches (WT-30). These are tendencies the
  opponent already revealed by playing, labelled with honest confidence; they
  are NOT a read of the hidden upcoming plan, and
* **cold-start facts** — already-player-facing, always-derivable facts (roster
  shape, program archetype, key threat) so the scout is never empty when there
  is no tape yet (week 1 / first meeting / fresh league).

The per-axis tape reveal and the cold-start facts surface ONLY once the player
has scouted (``scouted=True``). Before that — and on any axis the tape cannot
speak to — the opponent column is reported as "unscouted", because the engine
does not expose the opponent's planned tactics. This keeps the panel honest
rather than fabricating a comparison.

The builder structurally refuses an opponent policy: there is no parameter that
accepts the opponent's live/upcoming ``CoachPolicy``. Tape is supplied as an
``observed_tendencies`` mapping derived by the caller from recorded matches —
``command_center.aggregate_opponent_tape`` — never from the live club object.
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


def _confidence_label(confidence: float) -> str:
    """Word for how strongly the tape leans toward the observed value."""
    if confidence >= 0.75:
        return "strong"
    if confidence >= 0.5:
        return "leans"
    return "mixed"


def build_tactical_diff(
    *,
    player_policy: Mapping[str, Any],
    adaptation_summary: str | None = None,
    has_prior_meeting: bool = False,
    last_meeting: str | None = None,
    scouted: bool = False,
    observed_tendencies: Mapping[str, Mapping[str, Any]] | None = None,
    cold_start_intel: Mapping[str, Any] | None = None,
    archetype_playbook: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the tactical diff payload from the player's policy and allowed intel.

    ``player_policy`` is the player's own command policy as a mapping of axis ->
    value (e.g. ``CoachPolicy.as_dict()``). No opponent policy is accepted: the
    opponent column is derived solely from the sanctioned, already-player-facing
    signals passed explicitly here.

    Parameters
    ----------
    scouted:
        Whether the player has run the scout action this week. Only when ``True``
        do the per-axis tape tendencies and the cold-start facts surface; until
        then every axis is reported "unscouted".
    observed_tendencies:
        Optional mapping ``axis -> {"value", "sample", "confidence"}`` aggregated
        by the caller from the opponent's PAST recorded matches. Each entry is an
        observed tendency (a frequency over completed games), never the hidden
        upcoming plan. Ignored unless ``scouted``.
    cold_start_intel:
        Optional mapping of always-derivable, already-player-facing opponent
        facts (``program_archetype``, ``roster_shape``, ``threat``). Surfaced
        only when ``scouted``; anchors the reveal when there is no tape yet.
    archetype_playbook:
        Optional mapping ``axis -> value`` of the opponent ARCHETYPE's base
        policy — the same generator their staff actually plans from
        (``ai_tactics.get_ai_tactics(archetype, "Balanced")``). V19b: a scout
        report fills tape-less axes from this playbook so week-1 scouting
        yields real information, honestly labelled as a playbook lean (their
        identity's default, before intent shifts it) rather than observed
        tape. Ignored unless ``scouted``.
    """
    tendencies = dict(observed_tendencies or {}) if scouted else {}
    playbook = dict(archetype_playbook or {}) if scouted else {}

    rows: list[dict[str, Any]] = []
    tape_axes_revealed = 0
    playbook_axes_revealed = 0
    for axis in _AXIS_ORDER:
        row: dict[str, Any] = {
            "axis": axis,
            "label": _AXIS_LABELS[axis],
            "player_value": _humanize(player_policy.get(axis, "-")),
            "opponent_value": None,
            "opponent_known": False,
        }
        tendency = tendencies.get(axis)
        if tendency and tendency.get("value"):
            # Observed-from-tape tendency: a frequency over the opponent's past
            # games, NOT their hidden upcoming choice. Labelled as such with its
            # sample size and confidence so the player reads it as a lean.
            confidence = float(tendency.get("confidence", 0.0) or 0.0)
            sample = int(tendency.get("sample", 0) or 0)
            row["opponent_value"] = _humanize(tendency["value"])
            row["opponent_known"] = True
            row["opponent_source"] = "tape"
            row["confidence"] = round(confidence, 2)
            row["confidence_label"] = _confidence_label(confidence)
            row["sample"] = sample
            tape_axes_revealed += 1
        elif playbook.get(axis):
            # V19b playbook lean: the archetype's base policy — real intel a
            # scout can produce before any tape exists, honestly labelled.
            row["opponent_value"] = _humanize(str(playbook[axis]))
            row["opponent_known"] = True
            row["opponent_source"] = "playbook"
            row["confidence"] = None
            row["confidence_label"] = "playbook lean"
            row["sample"] = 0
            playbook_axes_revealed += 1
        rows.append(row)

    intel: list[dict[str, str]] = []
    if adaptation_summary:
        intel.append({"source": "adaptation", "text": str(adaptation_summary)})
    if has_prior_meeting and last_meeting:
        intel.append({"source": "prior_meeting", "text": str(last_meeting)})

    # "opponent_unscouted" retains its original meaning (no sanctioned narrative
    # intel: adaptation summary or prior-meeting line), so existing consumers and
    # tests are unaffected. The richer scout state is reported separately below.
    opponent_unscouted = len(intel) == 0

    cold_start = dict(cold_start_intel or {}) if scouted else {}
    has_cold_start = bool(
        cold_start.get("program_archetype")
        or cold_start.get("roster_shape")
        or cold_start.get("threat")
    )
    # Whether scouting surfaced anything beyond the always-unscouted baseline.
    intel_revealed = bool(
        scouted and (tape_axes_revealed or playbook_axes_revealed or has_cold_start or intel)
    )

    if not scouted:
        note = (
            "Opponent tendencies are unscouted. Scout to reveal what they have "
            "shown on tape — observed leans, not their hidden plan."
        )
    elif tape_axes_revealed and playbook_axes_revealed:
        note = (
            "Opponent reads mix observed tape (weighted by confidence) with "
            "their identity's playbook on axes without tape yet — leans, not "
            "their hidden plan."
        )
    elif tape_axes_revealed:
        note = (
            "Opponent reads are tendencies observed from past tape (not their "
            "hidden plan) — treat them as leans, weighted by confidence."
        )
    elif playbook_axes_revealed:
        note = (
            "No tape yet — these reads are the playbook their program identity "
            "plans from (their default lean before weekly adjustments), not "
            "their hidden plan."
        )
    elif has_cold_start:
        note = (
            "No tape on their tactics yet — these are facts you can already see "
            "(roster shape, program identity, top threat), not their hidden plan."
        )
    else:
        note = "No reliable tape on their plan yet — opponent tendencies are unscouted. Trust your reads."

    return {
        "player_plan": rows,
        "opponent_intel": intel,
        "opponent_unscouted": opponent_unscouted,
        "scouted": bool(scouted),
        "intel_revealed": intel_revealed,
        "tape_axes_revealed": tape_axes_revealed,
        "playbook_axes_revealed": playbook_axes_revealed,
        "cold_start": cold_start if has_cold_start else None,
        "note": note,
    }


__all__ = ["build_tactical_diff"]
