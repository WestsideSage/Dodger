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

    gates = [
        {
            "id": "scout",
            "label": "Scout the opponent",
            "short_label": "Scout",
            "detail": "Opponent lineup reviewed.",
            "ready": bool(_opponents(plan)),
        },
        {
            "id": "gameplan",
            "label": "Set a game plan",
            "short_label": "Game plan",
            "detail": "Match intent selected.",
            "ready": bool(plan.get("intent")),
        },
        {
            "id": "training",
            "label": "Assign a training order",
            "short_label": "Training",
            "detail": "Weekly training focus assigned.",
            "ready": bool(orders.get("training")),
        },
        {
            "id": "rotation",
            "label": "Field a full rotation",
            "short_label": "Rotation",
            "detail": f"At least {_MIN_ROTATION} starters set.",
            "ready": len(starters) >= _MIN_ROTATION,
        },
        {
            "id": "health",
            "label": "Clear the health check",
            "short_label": "Health",
            "detail": "No starter is critically fatigued.",
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


def _build_edge(plan: dict[str, Any]) -> dict[str, Any]:
    net = _sum_overall(_starters(plan)) - _sum_overall(_opponents(plan))
    if net > _EVEN_BAND:
        standing = "favorite"
    elif net < -_EVEN_BAND:
        standing = "underdog"
    else:
        standing = "even"
    return {"net_starter_ovr": net, "standing": standing}


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
    fatigue: dict[str, Any],
) -> dict[str, Any]:
    if is_bye:
        return {
            "verdict": "aligned",
            "advised_intent": None,
            "reason": "Bye week -- rest and develop, no opponent to plan for.",
            "advisory": True,
        }

    at_risk = int(fatigue["at_risk_count"])
    if at_risk >= 2 and plan.get("intent") != _HEALTH_INTENT:
        return {
            "verdict": "adjust",
            "advised_intent": _HEALTH_INTENT,
            "reason": (
                f"{at_risk} starters are low on stamina; "
                "consider Preserve Health to protect them."
            ),
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
        "recommendation": _build_recommendation(
            plan, is_bye=is_bye, fatigue=fatigue
        ),
    }


__all__ = ["build_week_briefing"]
