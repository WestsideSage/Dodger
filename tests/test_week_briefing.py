"""Unit tests for the pure week-briefing module.

The briefing is the canonical, server-side read of "where the player stands
this week": readiness gates, starter edge, fatigue, recent form, the opponent
threat, and an HONEST advisory recommendation. It never claims a mechanical
counter-edge the engine does not model (see AGENTS.md "no hidden boosts").
"""

from __future__ import annotations

from typing import Any

from dodgeball_sim.season import StandingsRow
from dodgeball_sim.week_briefing import build_week_briefing


def _starter(name: str, overall: int, stamina: int | None = 80) -> dict[str, Any]:
    summary: dict[str, Any] = {"id": name.lower(), "name": name, "overall": overall}
    if stamina is not None:
        summary["stamina"] = stamina
    return summary


def _plan(
    *,
    intent: str = "Balanced",
    training: str | None = "Fundamentals",
    starters: list[dict[str, Any]] | None = None,
    opponents: list[dict[str, Any]] | None = None,
    is_bye: bool = False,
    key_threat: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if starters is None:
        starters = [_starter(f"P{i}", 70) for i in range(6)]
    if opponents is None:
        opponents = [_starter(f"O{i}", 70) for i in range(6)]
    matchup: dict[str, Any] = {}
    if key_threat is not None:
        matchup["key_threat"] = key_threat
    return {
        "intent": intent,
        "is_bye": is_bye,
        "department_orders": {"training": training} if training else {},
        "lineup": {"players": starters},
        "opponent_lineup": {"players": opponents},
        "matchup_details": matchup,
    }


def _row(club_id: str, wins: int, losses: int, draws: int = 0) -> StandingsRow:
    return StandingsRow(
        club_id=club_id,
        wins=wins,
        losses=losses,
        draws=draws,
        elimination_differential=0,
        points=wins * 3 + draws,
    )


def _briefing(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = dict(
        plan=_plan(),
        standings_rows=[_row("you", 0, 0)],
        player_club_id="you",
        league_leader=None,
        recent_results=[],
        games_remaining=5,
        is_home=True,
        playoff_stage=None,
    )
    kwargs.update(overrides)
    return build_week_briefing(**kwargs)


# --- readiness gates -------------------------------------------------------

def test_all_gates_ready_is_ready_to_lock():
    out = _briefing()
    readiness = out["readiness"]
    assert readiness["total"] == 5
    assert readiness["ready_count"] == 5
    assert readiness["is_ready_to_lock"] is True
    assert readiness["items_remaining"] == 0
    assert readiness["next_issue"] == "No blockers"


def test_missing_training_order_blocks_lock():
    out = _briefing(plan=_plan(training=None))
    gate = next(g for g in out["readiness"]["gates"] if g["id"] == "training")
    assert gate["ready"] is False
    assert out["readiness"]["is_ready_to_lock"] is False
    assert out["readiness"]["next_issue"] == gate["label"]


def test_short_rotation_fails_rotation_gate():
    out = _briefing(plan=_plan(starters=[_starter(f"P{i}", 70) for i in range(4)]))
    gate = next(g for g in out["readiness"]["gates"] if g["id"] == "rotation")
    assert gate["ready"] is False


def test_very_low_stamina_fails_health_gate():
    starters = [_starter(f"P{i}", 70) for i in range(5)] + [_starter("Tired", 70, stamina=20)]
    out = _briefing(plan=_plan(starters=starters))
    gate = next(g for g in out["readiness"]["gates"] if g["id"] == "health")
    assert gate["ready"] is False


def test_missing_stamina_does_not_fail_health_gate():
    starters = [_starter(f"P{i}", 70, stamina=None) for i in range(6)]
    out = _briefing(plan=_plan(starters=starters))
    gate = next(g for g in out["readiness"]["gates"] if g["id"] == "health")
    assert gate["ready"] is True


# --- starter edge ----------------------------------------------------------

def test_higher_starters_make_player_a_favorite():
    starters = [_starter(f"P{i}", 80) for i in range(6)]
    opponents = [_starter(f"O{i}", 70) for i in range(6)]
    out = _briefing(plan=_plan(starters=starters, opponents=opponents))
    assert out["edge"]["net_starter_ovr"] == 60
    assert out["edge"]["standing"] == "favorite"


def test_weaker_starters_make_player_an_underdog():
    starters = [_starter(f"P{i}", 60) for i in range(6)]
    opponents = [_starter(f"O{i}", 70) for i in range(6)]
    out = _briefing(plan=_plan(starters=starters, opponents=opponents))
    assert out["edge"]["net_starter_ovr"] == -60
    assert out["edge"]["standing"] == "underdog"


def test_equal_starters_are_even():
    out = _briefing()
    assert out["edge"]["net_starter_ovr"] == 0
    assert out["edge"]["standing"] == "even"


# --- fatigue + recommendation ---------------------------------------------

def test_multiple_tired_starters_advise_preserve_health():
    starters = (
        [_starter(f"P{i}", 70) for i in range(4)]
        + [_starter("A", 70, stamina=55), _starter("B", 70, stamina=50)]
    )
    out = _briefing(plan=_plan(starters=starters))
    assert out["fatigue"]["at_risk_count"] == 2
    assert out["fatigue"]["min_stamina"] == 50
    rec = out["recommendation"]
    assert rec["verdict"] == "adjust"
    assert rec["advised_intent"] == "Preserve Health"
    assert rec["advisory"] is True
    assert "stamina" in rec["reason"].lower()


def test_single_tired_starter_does_not_trigger_adjustment():
    starters = [_starter(f"P{i}", 70) for i in range(5)] + [_starter("A", 70, stamina=55)]
    out = _briefing(plan=_plan(starters=starters))
    assert out["fatigue"]["at_risk_count"] == 1
    assert out["recommendation"]["verdict"] == "aligned"
    assert out["recommendation"]["advised_intent"] is None


def test_recommendation_never_claims_archetype_counter():
    # A "Tactical"/"Pressure"-style threat must NOT flip the recommendation,
    # because the engine has no such counter mechanic. Regression guard for
    # the stale frontend heuristic broken by the Plan B archetype rewrite.
    threat = {"name": "Ace", "archetype": "Ball Hawk", "ovr": 92}
    out = _briefing(plan=_plan(intent="Win Now", key_threat=threat))
    assert out["recommendation"]["verdict"] == "aligned"
    assert out["recommendation"]["advised_intent"] is None


# --- bye week --------------------------------------------------------------

def test_bye_week_short_circuits_recommendation_and_threat():
    out = _briefing(plan=_plan(is_bye=True, key_threat=None))
    assert out["threat"] is None
    rec = out["recommendation"]
    assert rec["verdict"] == "aligned"
    assert rec["advised_intent"] is None
    assert "bye" in rec["reason"].lower()


# --- form + rank -----------------------------------------------------------

def test_rank_is_none_before_any_games_played():
    out = _briefing(standings_rows=[_row("you", 0, 0), _row("them", 0, 0)])
    assert out["form"]["rank"] is None


def test_rank_reflects_position_once_games_played():
    rows = [_row("leader", 3, 0), _row("you", 1, 2, draws=1)]
    out = _briefing(standings_rows=rows, player_club_id="you")
    assert out["form"]["rank"] == 2
    # W-L-D, matching the standings table verbatim (draws are not folded in).
    assert out["form"]["regular_season_record"] == "1-2-1"


def test_recent_record_counts_wins_vs_rest():
    out = _briefing(recent_results=["Win", "Loss", "Win", "Win", "Loss"])
    assert out["form"]["recent_record"] == "3-2"


def test_form_carries_games_remaining():
    out = _briefing(games_remaining=7)
    assert out["form"]["games_remaining"] == 7


# --- threat + context passthrough -----------------------------------------

def test_structured_threat_passthrough():
    threat = {"name": "Ace", "archetype": "Sharpshooter", "ovr": 90}
    out = _briefing(plan=_plan(key_threat=threat))
    assert out["threat"] == threat


def test_match_context_and_league_leader():
    out = _briefing(is_home=False, playoff_stage="Semifinal", league_leader="Anchors FC")
    assert out["match_context"] == {"is_home": False, "playoff_stage": "Semifinal"}
    assert out["league_leader"] == "Anchors FC"
