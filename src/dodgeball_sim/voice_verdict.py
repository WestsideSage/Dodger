"""Post-match Verdict writer.

A Verdict is a single honest sentence stating whether the chosen Approach's
intended mechanical behaviour actually showed up in the box score — not merely
whether the match was won.

See `docs/adr/0001-honest-verdict-design.md` for the binding decisions:

1. Signature-not-result honesty — the verdict tracks the approach's signature
   in the box score, not the win/loss.
2. Comparative metrics vs the opponent in the same match (no static thresholds).
3. Data injection — the signature numbers appear in the sentence itself.
4. No-op is a first-class verdict state.
5. Approach labels never leak the raw Intent id.

This module is pure: same inputs → same string, no DB or I/O.
"""
from __future__ import annotations

from typing import Mapping

# Player-facing Approach label for each backend Intent. Intents not in this
# mapping (e.g. "Develop Youth", "Balanced" handled below) get a neutral
# verdict rather than an invented Approach claim.
_APPROACH_LABEL: dict[str, str] = {
    "Win Now": "Aggressive",
    "Balanced": "Balanced",
    "Prepare For Playoffs": "Control",
    "Preserve Health": "Defensive",
}


def approach_label_for_intent(intent: str) -> str:
    return _APPROACH_LABEL.get(intent, intent)


def _result_clause(result: str) -> str:
    if result == "Win":
        return "and you won"
    if result == "Loss":
        return "but you lost"
    return "and the match drew"


def _round_policy(policy: Mapping[str, float]) -> dict[str, float]:
    return {key: round(float(value), 2) for key, value in policy.items()}


def _is_noop(tactics: Mapping[str, float], base_tactics: Mapping[str, float]) -> bool:
    if not tactics or not base_tactics:
        return False
    return _round_policy(tactics) == _round_policy(base_tactics)


def _aggressive_signature(player_box: Mapping, opponent_box: Mapping) -> tuple[bool, int, int]:
    p_catches = int(player_box["totals"].get("catches", 0))
    o_catches = int(opponent_box["totals"].get("catches", 0))
    return (p_catches > o_catches, p_catches, o_catches)


def _defensive_signature(player_box: Mapping, opponent_box: Mapping) -> tuple[bool, int, int]:
    # "Eliminations against us" = the opponent's offensive count
    # (their players' eliminations_by_throw, summed as totals.outs_recorded).
    our_eliminated = int(opponent_box["totals"].get("outs_recorded", 0))
    their_eliminated = int(player_box["totals"].get("outs_recorded", 0))
    return (our_eliminated < their_eliminated, our_eliminated, their_eliminated)


def _hit_rate(team_box: Mapping) -> float:
    total_throws = sum(int(p.get("throws", 0)) for p in team_box.get("players", {}).values())
    if total_throws <= 0:
        return 0.0
    outs = int(team_box["totals"].get("outs_recorded", 0))
    return outs / total_throws


def _control_signature(player_box: Mapping, opponent_box: Mapping) -> tuple[bool, int, int, bool]:
    p_total = sum(int(p.get("throws", 0)) for p in player_box.get("players", {}).values())
    o_total = sum(int(p.get("throws", 0)) for p in opponent_box.get("players", {}).values())
    degenerate = (p_total == 0 and o_total == 0)
    p_rate = _hit_rate(player_box)
    o_rate = _hit_rate(opponent_box)
    return (p_rate > o_rate, int(round(p_rate * 100)), int(round(o_rate * 100)), degenerate)


def _aggressive_verdict(present: bool, p: int, o: int, result: str) -> str:
    if result == "Win":
        if present:
            return f"Your Aggressive plan delivered — {p} catches to {o}, and you won."
        return f"You won despite Aggressive — only {p} catches to their {o}."
    if result == "Loss":
        if present:
            return f"Aggressive delivered the catches it promised ({p} to {o}), but you lost anyway."
        return f"Aggressive never materialized — {p} catches to their {o}, and you lost."
    # Draw
    if present:
        return f"Aggressive showed up ({p} catches to {o}); the match ended in a draw."
    return f"Aggressive never took hold ({p} catches to their {o}); the match ended in a draw."


def _defensive_verdict(present: bool, ours: int, theirs: int, result: str) -> str:
    if result == "Win":
        if present:
            return f"Your Defensive plan held — only {ours} of yours eliminated to their {theirs}, and you won."
        return f"You won, but Defensive didn't really hold — {ours} of yours eliminated to their {theirs}."
    if result == "Loss":
        if present:
            return f"Defensive held the line ({ours} of yours eliminated to their {theirs}), but you couldn't put it away."
        return f"Defensive never held — {ours} of yours eliminated to their {theirs}, and you lost."
    if present:
        return f"Defensive limited the damage ({ours} of yours to their {theirs}); the match ended in a draw."
    return f"Defensive didn't hold ({ours} of yours eliminated to their {theirs}); the match ended in a draw."


def _control_verdict(present: bool, p_pct: int, o_pct: int, degenerate: bool, result: str) -> str:
    if degenerate:
        if result == "Win":
            return "Control's efficiency couldn't be measured this match — no throws recorded — and you won."
        if result == "Loss":
            return "Control's efficiency couldn't be measured this match — no throws recorded — and you lost."
        return "Control's efficiency couldn't be measured this match — no throws recorded — match ended in a draw."
    if result == "Win":
        if present:
            return f"Your Control plan executed — {p_pct}% hit rate to their {o_pct}%, and you won."
        return f"You won, but Control's efficiency didn't show — {p_pct}% hit rate to their {o_pct}%."
    if result == "Loss":
        if present:
            return f"Control delivered the efficiency ({p_pct}% to {o_pct}%), but you lost anyway."
        return f"Control never landed — {p_pct}% hit rate to their {o_pct}%, and you lost."
    if present:
        return f"Control executed ({p_pct}% hit rate to {o_pct}%); the match ended in a draw."
    return f"Control never landed ({p_pct}% hit rate to their {o_pct}%); the match ended in a draw."


def _balanced_verdict(result: str) -> str:
    if result == "Win":
        return "A Balanced plan, a win — no single lever defined this one."
    if result == "Loss":
        return "A Balanced plan, a loss — no single lever defined this one."
    return "A Balanced plan ended in a draw — no single lever defined this one."


def _noop_verdict(approach: str, result: str) -> str:
    tail = {
        "Win": "You won.",
        "Loss": "You lost.",
        "Draw": "The match ended in a draw.",
    }.get(result, "")
    return f"Your {approach} plan looked identical to your default — no real lever pulled this week. {tail}".strip()


def _neutral_fallback(result: str) -> str:
    if result == "Win":
        return "A win this week — no specific plan signature to assess."
    if result == "Loss":
        return "A loss this week — no specific plan signature to assess."
    return "A draw this week — no specific plan signature to assess."


def render_verdict(
    *,
    intent: str,
    tactics: Mapping[str, float],
    base_tactics: Mapping[str, float],
    result: str,
    player_team_box: Mapping,
    opponent_team_box: Mapping,
) -> str:
    """Render the single-sentence post-match Verdict.

    Parameters
    ----------
    intent: backend Intent id stored on the plan (e.g. "Win Now").
    tactics: the post-`_policy_for_intent` tactics dict.
    base_tactics: the club's base `CoachPolicy.as_dict()` for no-op detection.
    result: "Win" | "Loss" | "Draw".
    player_team_box / opponent_team_box: the per-team subdicts of
        `record.result.box_score["teams"]`.
    """
    approach = _APPROACH_LABEL.get(intent)
    if approach is None:
        return _neutral_fallback(result)

    if approach == "Balanced":
        # Balanced never overrides anything, so the "no-op" detector would
        # always fire — but Balanced has its own canonical verdicts.
        return _balanced_verdict(result)

    if _is_noop(tactics, base_tactics):
        return _noop_verdict(approach, result)

    if approach == "Aggressive":
        present, p, o = _aggressive_signature(player_team_box, opponent_team_box)
        return _aggressive_verdict(present, p, o, result)

    if approach == "Defensive":
        present, ours, theirs = _defensive_signature(player_team_box, opponent_team_box)
        return _defensive_verdict(present, ours, theirs, result)

    # Control
    present, p_pct, o_pct, degenerate = _control_signature(player_team_box, opponent_team_box)
    return _control_verdict(present, p_pct, o_pct, degenerate, result)


__all__ = ["approach_label_for_intent", "render_verdict"]
