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

from typing import Any, Mapping

from .aftermath_context import AftermathContext
from .moment_events import MomentKind
from .rng import DeterministicRNG
from .voice_register import tier1

# Player-facing Approach label for each backend Intent. Intents not in this
# mapping (e.g. "Develop Youth", "Balanced" handled below) get a neutral
# verdict rather than an invented Approach claim.
_APPROACH_LABEL: dict[str, str] = {
    "Win Now": "Aggressive",
    "Balanced": "Balanced",
    "Prepare For Playoffs": "Control",
    "Preserve Health": "Defensive",
}

HEADLINE_PRIORITY = [
    MomentKind.ONE_V_ONE_FINALE.value,
    MomentKind.COMEBACK.value,
    MomentKind.LATE_GAME_ESCAPE.value,
    MomentKind.DRAMATIC_CATCH.value,
    MomentKind.FLOOD_THROW.value,
    MomentKind.GASSED_COLLAPSE.value,
]

_WIN_TEMPLATES = [
    "A decisive Win for the squad.",
    "The team secures a hard-fought Win.",
    "An impressive Win that sends a message.",
]

_LOSS_TEMPLATES = [
    "A tough Loss the squad will want to forget.",
    "The team falls to a hard Loss.",
    "A costly Loss that raises questions.",
]

_DRAW_TEMPLATES = [
    "A hard-fought Draw - honors even.",
    "Neither side blinked: a Draw.",
    "The squad settles for a Draw.",
]

_MARGIN_TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("Win", "shutout"): [
        "A {score} shutout Win - the squad never let them breathe.",
        "Total control in a {score} shutout Win.",
    ],
    ("Win", "dominant"): [
        "A commanding {score} Win for the squad.",
        "A {score} Win that was never in doubt.",
    ],
    ("Win", "solid"): [
        "A solid {score} Win on the court.",
        "The squad banks a {score} Win.",
    ],
    ("Win", "narrow"): [
        "A nervy {score} Win, decided in the margins.",
        "A {score} Win that came down to the final exchanges.",
    ],
    ("Loss", "shutout"): [
        "Shut out {score} - a Loss to bury quickly.",
        "Nothing landed: a {score} Loss without a survivor.",
    ],
    ("Loss", "heavy"): [
        "A heavy {score} Loss the staff will dissect.",
        "Outclassed in a {score} Loss.",
    ],
    ("Loss", "clear"): [
        "A clear {score} Loss for the squad.",
        "A {score} Loss this week.",
    ],
    ("Loss", "narrow"): [
        "A {score} Loss by the finest of margins.",
        "So close: a {score} Loss decided late.",
    ],
    ("Draw", "draw"): [
        "A {score} Draw - honors even on the court.",
        "Neither side blinked: a {score} Draw.",
    ],
}


def approach_label_for_intent(intent: str) -> str:
    return _APPROACH_LABEL.get(intent, intent)


def render_headline(ctx: AftermathContext) -> str:
    for kind in HEADLINE_PRIORITY:
        matching = [event for event in ctx.moment_events if event.kind.value == kind]
        if not matching:
            continue
        chosen = max(matching, key=lambda event: event.tick)
        return _moment_headline(ctx, chosen)
    return _margin_fallback(ctx)


def _moment_headline(ctx: AftermathContext, moment: Any) -> str:
    kind = moment.kind.value
    if kind == MomentKind.ONE_V_ONE_FINALE.value:
        return tier1(
            "moment.one_v_one_finale.headline",
            a=ctx.player_name(moment.player_a_id),
            b=ctx.player_name(moment.player_b_id),
        )
    if kind == MomentKind.COMEBACK.value:
        if moment.team_id != ctx.match_result.winner_team_id:
            return _margin_fallback(ctx)
        return tier1(
            "moment.comeback.headline",
            team=ctx.team_name(moment.team_id),
            deficit=moment.deficit_at_low_point,
            catches=moment.catches_during_comeback,
        )
    if kind == MomentKind.LATE_GAME_ESCAPE.value:
        return tier1(
            "moment.late_game_escape.headline",
            survivor=ctx.player_name(moment.survivor_id),
            attacker_count=moment.attacker_count,
        )
    if kind == MomentKind.DRAMATIC_CATCH.value:
        return tier1(
            "moment.dramatic_catch.headline",
            catcher=ctx.player_name(moment.catcher_id),
            returning=ctx.player_name(moment.returning_player_id),
        )
    if kind == MomentKind.FLOOD_THROW.value:
        return tier1(
            "moment.flood_throw.headline",
            team=ctx.team_name(moment.thrower_team_id),
            count=len(moment.thrower_ids),
        )
    return tier1(
        "moment.gassed_collapse.headline",
        player=ctx.player_name(moment.player_id),
    )


def _margin_tier(result: str, mine: int, theirs: int) -> str:
    if result == "Win":
        if theirs == 0:
            return "shutout"
        if mine >= theirs * 2:
            return "dominant"
        if mine - theirs <= 1:
            return "narrow"
        return "solid"
    if result == "Loss":
        if mine == 0:
            return "shutout"
        if theirs >= mine * 2:
            return "heavy"
        if theirs - mine <= 1:
            return "narrow"
        return "clear"
    return "draw"


def _margin_fallback(ctx: AftermathContext) -> str:
    """Render a margin-aware headline derived solely from MatchResult.

    The "mine"/"theirs" split is taken from ``ctx.player_club_id`` when
    available; otherwise it falls back to dict-iteration order of
    ``box_score["teams"]`` (the legacy behaviour, used by writer-side
    tests that don't have a player perspective). Either way, the result
    string (Win/Loss/Draw) is derived from ``MatchResult.winner_team_id``
    — never from in-progress state.
    """
    result_obj = ctx.match_result
    winner_id = result_obj.winner_team_id
    teams = result_obj.box_score.get("teams", {})
    if len(teams) >= 2:
        team_ids = list(teams.keys())
        if ctx.player_club_id and ctx.player_club_id in teams:
            mine_id = ctx.player_club_id
            theirs_id = next(tid for tid in team_ids if tid != mine_id)
        else:
            mine_id, theirs_id = team_ids[0], team_ids[1]
        mine_living = ctx.survivors_for(mine_id)
        theirs_living = ctx.survivors_for(theirs_id)
        if mine_living is not None and theirs_living is not None:
            if winner_id is None:
                result = "Draw"
            elif winner_id == mine_id:
                result = "Win"
            else:
                result = "Loss"
            templates = _MARGIN_TEMPLATES.get((result, _margin_tier(result, mine_living, theirs_living)))
            if templates:
                return (
                    DeterministicRNG(result_obj.seed)
                    .choice(templates)
                    .format(score=f"{mine_living}-{theirs_living}")
                )
    # Score-less fallback: still honour the resolved winner relative to
    # the player perspective.
    if winner_id is None:
        return DeterministicRNG(result_obj.seed).choice(_DRAW_TEMPLATES)
    if ctx.player_club_id is None or winner_id == ctx.player_club_id:
        return DeterministicRNG(result_obj.seed).choice(_WIN_TEMPLATES)
    return DeterministicRNG(result_obj.seed).choice(_LOSS_TEMPLATES)


def _result_clause(result: str) -> str:
    if result == "Win":
        return "and you won"
    if result == "Loss":
        return "but you lost"
    return "and the match drew"


def _normalize_policy(policy: Mapping[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in policy.items()}


def _is_noop(tactics: Mapping[str, Any], base_tactics: Mapping[str, Any]) -> bool:
    if not tactics or not base_tactics:
        return False
    return _normalize_policy(tactics) == _normalize_policy(base_tactics)


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
    tied = p == o
    if result == "Win":
        if present:
            return f"Your Aggressive plan delivered — {p} catches to {o}, and you won."
        if tied:
            if o == 0:
                return "Your Aggressive plan held the line, securing a shutout win with 0 catches surrendered."
            return f"You won under the Aggressive plan — matched their {o} catches."
        return f"You won despite Aggressive — only {p} catches to their {o}."
    if result == "Loss":
        if present:
            return f"Aggressive delivered the catches it promised ({p} to {o}), but you lost anyway."
        if tied:
            return f"Aggressive never broke through — matched their {o} catches, and you lost."
        return f"Aggressive never materialized — {p} catches to their {o}, and you lost."
    # Draw
    if present:
        return f"Aggressive showed up ({p} catches to {o}); the match ended in a draw."
    if tied:
        return f"Aggressive never took hold (matched their {o} catches); the match ended in a draw."
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
    win_tail = {
        "Win": "The strategy held the line — banking the win.",
        "Loss": "The strategy didn't move the needle this week.",
        "Draw": "The strategy held, neither side broke through.",
    }.get(result, tail)
    return f"Your {approach} plan aligned perfectly with your base tactics this week. {win_tail}".strip()


def _neutral_fallback(result: str) -> str:
    if result == "Win":
        return "A win this week — no specific plan signature to assess."
    if result == "Loss":
        return "A loss this week — no specific plan signature to assess."
    return "A draw this week — no specific plan signature to assess."


def render_verdict(
    *,
    intent: str,
    tactics: Mapping[str, Any],
    base_tactics: Mapping[str, Any],
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
