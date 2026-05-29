"""Pure helper for the playoff-loss elimination ceremony.

Task 9 (2026-05-28 playtest-fixes): when the player's playoff run ends,
the flow used to jump straight to the regular-season recap. This module
shapes the one-screen summary the frontend ceremony renders -- opponent,
final score, *what ended your run*, the players who carried the match,
and a one-line look-ahead.

Kept pure (dicts in, dict out, no I/O) so the "what ended your run"
phrasing can be pinned by tests without standing up a save.
"""

from __future__ import annotations

from typing import Any


def cause_line(
    *,
    decided_by: str,
    narrative_note: str,
    player_score: int,
    opponent_score: int,
) -> str:
    """One honest sentence explaining how the run ended.

    Tiebreaker losses reuse the upstream ``narrative_note`` verbatim (it
    already states the seed/overtime reason). Regulation losses derive
    the line from the final score so the copy can never contradict it.
    """

    note = (narrative_note or "").strip()
    if decided_by in {"overtime", "seed_tiebreaker"} and note:
        return note
    if player_score == 0:
        return f"Shut out {opponent_score}–{player_score}. Nothing fell your way."
    if opponent_score - player_score >= 2:
        return f"Outscored {opponent_score}–{player_score}; the gap never closed."
    return f"Edged {opponent_score}–{player_score} in a one-possession finish."


def build_elimination_summary(
    *,
    stage: str,
    opponent_name: str,
    player_score: int,
    opponent_score: int,
    decided_by: str,
    narrative_note: str,
    contributors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the elimination-ceremony payload.

    ``contributors`` is the already-ranked top-performer list filtered to
    the player's club. The top three become both the "who carried it"
    callout and the returning-core look-ahead.
    """

    top = list(contributors[:3])
    return {
        "stage": stage,
        "opponent_name": opponent_name,
        "player_score": int(player_score),
        "opponent_score": int(opponent_score),
        "decided_by": decided_by,
        "cause": cause_line(
            decided_by=decided_by,
            narrative_note=narrative_note,
            player_score=int(player_score),
            opponent_score=int(opponent_score),
        ),
        "contributors": top,
        "returning": [str(c.get("player_name", "")) for c in top if c.get("player_name")],
    }


__all__ = ["build_elimination_summary", "cause_line"]
