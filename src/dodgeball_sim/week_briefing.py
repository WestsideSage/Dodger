"""Pure, server-side "where do I stand this week" briefing.

The briefing is the canonical read of the player's upcoming-match situation:
readiness gates, starter edge, fatigue, recent form, the opponent threat, and an
HONEST advisory recommendation. It is computed from data the player can verify
and the engine actually uses (net starter OVR, starter stamina, recent results,
bye status). It NEVER claims a mechanical counter-edge the engine does not model
(see AGENTS.md "no hidden boosts") -- the recommendation is explicitly advisory.

This module is pure: it takes plain dicts/rows in and returns a dict out, so the
frontend and pytest read the exact same shape. No SQLite, no I/O.
"""

from __future__ import annotations

from typing import Any, Sequence

from .season import StandingsRow

# Starter stamina at/under this is "at risk" -- enough to shape advice but not
# a hard blocker.
_AT_RISK_STAMINA = 60
# Starter stamina under this trips the health readiness gate -- too depleted to
# responsibly start without a deliberate choice.
_CRITICAL_STAMINA = 30
# Minimum starters for a legal rotation.
_MIN_ROTATION = 5
# Net starter-OVR band that still reads as an even matchup.
_EVEN_BAND = 8

_HEALTH_INTENT = "Preserve Health"
_AGGRESSIVE_INTENT = "Win Now"


def compute_staff_recommendation(
    *,
    recent_results: Sequence[str],
    at_risk_count: int,
) -> dict[str, Any]:
    """The staff's advisory call, derived purely from verifiable context.

    It reads only recent results and squad health -- NEVER the player's
    currently-selected plan. That independence is the whole point: a
    recommendation that mirrors the active selection ("Keep current plan" no
    matter what you pick) is meaningless feedback. Returns a stable shape:
    ``action`` ("keep" | "change"), ``recommended_intent`` (intent label or
    None), and a short ``reason``.
    """
    # Squad health outranks form: depleted starters are the louder signal.
    if at_risk_count >= 2:
        return {
            "action": "change",
            "recommended_intent": _HEALTH_INTENT,
            "reason": (
                f"{at_risk_count} starters are low on stamina; "
                "Preserve Health protects them."
            ),
        }
    last_two = [str(result).lower() for result in list(recent_results)[-2:]]
    if len(last_two) >= 2 and all(result.startswith("l") for result in last_two):
        return {
            "action": "change",
            "recommended_intent": _AGGRESSIVE_INTENT,
            "reason": "Two straight losses; staff wants a Win Now push to break the skid.",
        }
    return {
        "action": "keep",
        "recommended_intent": None,
        "reason": "Recent form and squad health support the current approach.",
    }


def _starters(plan: dict[str, Any]) -> list[dict[str, Any]]:
    lineup = plan.get("lineup") or {}
    return list(lineup.get("players") or [])


def _opponents(plan: dict[str, Any]) -> list[dict[str, Any]]:
    lineup = plan.get("opponent_lineup") or {}
    return list(lineup.get("players") or [])


def _stamina_values(players: Sequence[dict[str, Any]]) -> list[int]:
    out: list[int] = []
    for p in players:
        value = p.get("stamina")
        if value is not None:
            out.append(int(value))
    return out


def _sum_overall(players: Sequence[dict[str, Any]]) -> int:
    return sum(int(p.get("overall", 0)) for p in players)


def _build_readiness(plan: dict[str, Any]) -> dict[str, Any]:
    starters = _starters(plan)
    orders = plan.get("department_orders") or {}
    stamina = _stamina_values(starters)
    health_ok = not any(value < _CRITICAL_STAMINA for value in stamina)
    is_bye = bool(plan.get("is_bye"))

    # D3: scout-opponent and confirm-lineup are deliberate-action gates. They
    # start UNMET on a fresh weekly plan and are cleared only by a real player
    # action (which persists a flag on the plan) — so readiness is meaningful
    # rather than auto-5/5. A bye week auto-clears both: there is no opponent to
    # scout and no six to field. Gameplan/training/health stay
    # default-satisfied to preserve the Balanced-default convenience.
    scouted = is_bye or bool(plan.get("opponent_scouted"))
    lineup_confirmed = is_bye or bool(plan.get("lineup_confirmed"))
    # State-aware gate details: WT-4 makes the detail VISIBLE on pending (red)
    # gates, so the string must describe the actual blocker when unmet — a
    # satisfied-state assertion shown on a red gate is a lie.
    intent_set = bool(plan.get("intent"))
    training_set = bool(orders.get("training"))
    rotation_ok = len(starters) >= _MIN_ROTATION

    gates = [
        {
            "id": "scout",
            "label": "Scout the opponent",
            "short_label": "Scout",
            "detail": (
                "No opponent to scout."
                if is_bye
                else "Opponent lineup reviewed."
                if scouted
                else "Review the opponent's projected six."
            ),
            "ready": scouted,
        },
        {
            "id": "confirm_lineup",
            "label": "Confirm your starting six",
            "short_label": "Lineup",
            "detail": (
                "No lineup to confirm on a bye."
                if is_bye
                else "Starting six confirmed."
                if lineup_confirmed
                else "Confirm the six you will field."
            ),
            "ready": lineup_confirmed,
        },
        {
            "id": "gameplan",
            "label": "Set a game plan",
            "short_label": "Game plan",
            "detail": "Match intent selected." if intent_set else "Select a match intent to set the team's approach.",
            "ready": intent_set,
        },
        {
            "id": "training",
            "label": "Assign a training order",
            "short_label": "Training",
            "detail": "Weekly training focus assigned." if training_set else "Assign a weekly training focus.",
            "ready": training_set,
        },
        {
            "id": "rotation",
            "label": "Field a full rotation",
            "short_label": "Rotation",
            "detail": (
                f"At least {_MIN_ROTATION} starters set."
                if rotation_ok
                else f"Field at least {_MIN_ROTATION} starters (you have {len(starters)})."
            ),
            "ready": rotation_ok,
        },
        {
            "id": "health",
            "label": "Clear the health check",
            "short_label": "Health",
            "detail": (
                "No starter is critically fatigued."
                if health_ok
                else "A starter is critically fatigued — rest or rotate before you sim."
            ),
            "ready": health_ok,
        },
    ]

    ready_count = sum(1 for g in gates if g["ready"])
    items_remaining = len(gates) - ready_count
    next_issue = "No blockers"
    for gate in gates:
        if not gate["ready"]:
            next_issue = gate["label"]
            break

    return {
        "gates": gates,
        "total": len(gates),
        "ready_count": ready_count,
        "is_ready_to_lock": items_remaining == 0,
        "items_remaining": items_remaining,
        "next_issue": next_issue,
    }


_EDGE_HEADLINES = {
    "favorite": "Favorite",
    "even": "Even Matchup",
    "underdog": "Underdog",
}


def _build_edge(plan: dict[str, Any]) -> dict[str, Any]:
    """Banded matchup standing (D2).

    The headline is the BAND (Favorite / Even / Underdog) derived from the
    fielded-6 net starter OVR — never a raw ``+NNN`` that reads like a
    win-probability. The signed net OVR is kept as a small, explicitly advisory
    "roster strength" detail; it informs but never implies a mechanical edge
    (see AGENTS.md "no hidden boosts").
    """
    net = _sum_overall(_starters(plan)) - _sum_overall(_opponents(plan))
    if net > _EVEN_BAND:
        standing = "favorite"
    elif net < -_EVEN_BAND:
        standing = "underdog"
    else:
        standing = "even"
    advisory = f"{net:+d} net starter OVR" if not plan.get("is_bye") else "Bye week"
    return {
        "net_starter_ovr": net,
        "standing": standing,
        "headline": _EDGE_HEADLINES[standing],
        "advisory_detail": advisory,
        "advisory": True,
    }


def _build_fatigue(plan: dict[str, Any]) -> dict[str, Any]:
    stamina = _stamina_values(_starters(plan))
    at_risk = sum(1 for value in stamina if value < _AT_RISK_STAMINA)
    return {
        "at_risk_count": at_risk,
        "min_stamina": min(stamina) if stamina else None,
    }


def _recent_record(recent_results: Sequence[str]) -> str:
    wins = sum(1 for r in recent_results if str(r).lower() == "win")
    return f"{wins}-{len(recent_results) - wins}"


def _build_form(
    *,
    standings_rows: Sequence[StandingsRow],
    player_club_id: str,
    recent_results: Sequence[str],
    games_remaining: int,
) -> dict[str, Any]:
    any_games = any(
        (row.wins + row.losses + row.draws) > 0 for row in standings_rows
    )
    ordered = sorted(standings_rows, key=lambda r: r.points, reverse=True)
    rank: int | None = None
    # Three-part W-L-D so this matches the standings table verbatim; a
    # two-part record silently folds draws into the loss column and reads as a
    # different record than the league office shows.
    regular_season_record = "0-0-0"
    for index, row in enumerate(ordered):
        if row.club_id == player_club_id:
            rank = index + 1 if any_games else None
            regular_season_record = f"{row.wins}-{row.losses}-{row.draws}"
            break
    return {
        "recent_record": _recent_record(recent_results),
        "rank": rank,
        "regular_season_record": regular_season_record,
        "games_remaining": games_remaining,
    }


def _build_recommendation(
    plan: dict[str, Any],
    *,
    is_bye: bool,
    staff: dict[str, Any],
) -> dict[str, Any]:
    """Turn the selection-independent staff call into player-facing advice.

    The staff recommendation (see :func:`compute_staff_recommendation`) is
    computed from verifiable context alone. Here we compare it against the
    player's *currently selected* intent to decide whether to nudge: if the
    staff wants a different intent than the one selected, the verdict is
    ``adjust``; otherwise it is ``aligned``. The staff call itself never reads
    the selection, so this is honest feedback rather than an echo.
    """
    if is_bye:
        return {
            "verdict": "aligned",
            "advised_intent": None,
            "reason": "Bye week -- rest and develop, no opponent to plan for.",
            "advisory": True,
        }

    recommended_intent = staff.get("recommended_intent")
    if recommended_intent and plan.get("intent") != recommended_intent:
        return {
            "verdict": "adjust",
            "advised_intent": recommended_intent,
            "reason": staff["reason"],
            "advisory": True,
        }

    return {
        "verdict": "aligned",
        "advised_intent": None,
        "reason": "Your plan fits the situation.",
        "advisory": True,
    }


def build_week_briefing(
    *,
    plan: dict[str, Any],
    standings_rows: Sequence[StandingsRow],
    player_club_id: str,
    league_leader: str | None,
    recent_results: Sequence[str],
    games_remaining: int,
    is_home: bool,
    playoff_stage: str | None,
) -> dict[str, Any]:
    is_bye = bool(plan.get("is_bye"))
    fatigue = _build_fatigue(plan)
    matchup = plan.get("matchup_details") or {}
    threat = None if is_bye else matchup.get("key_threat")
    staff = compute_staff_recommendation(
        recent_results=recent_results,
        at_risk_count=int(fatigue["at_risk_count"]),
    )

    return {
        "readiness": _build_readiness(plan),
        "edge": _build_edge(plan),
        "fatigue": fatigue,
        "form": _build_form(
            standings_rows=standings_rows,
            player_club_id=player_club_id,
            recent_results=recent_results,
            games_remaining=games_remaining,
        ),
        "threat": threat,
        "match_context": {"is_home": is_home, "playoff_stage": playoff_stage},
        "league_leader": league_leader,
        "staff_recommendation": staff,
        "recommendation": _build_recommendation(
            plan, is_bye=is_bye, staff=staff
        ),
    }


__all__ = ["build_week_briefing"]
