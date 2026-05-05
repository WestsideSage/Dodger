from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .models import CoachPolicy, MatchSetup, Player, PlayerRatings, PlayerTraits, Team


def _coach_policy_from_dict(payload: Dict[str, Any]) -> CoachPolicy:
    return CoachPolicy(
        target_stars=float(payload.get("target_stars", 0.5)),
        target_ball_holder=float(payload.get("target_ball_holder", 0.5)),
        risk_tolerance=float(payload.get("risk_tolerance", 0.5)),
        sync_throws=float(payload.get("sync_throws", 0.2)),
        rush_frequency=float(payload.get("rush_frequency", 0.5)),
        rush_proximity=float(payload.get("rush_proximity", 0.5)),
        tempo=float(payload.get("tempo", 0.5)),
        catch_bias=float(payload.get("catch_bias", 0.5)),
    )


def _player_from_dict(payload: Dict[str, Any]) -> Player:
    ratings_payload = payload.get("ratings", {})
    traits_payload = payload.get("traits", {})
    ratings = PlayerRatings(
        accuracy=ratings_payload.get("accuracy", 50.0),
        power=ratings_payload.get("power", 50.0),
        dodge=ratings_payload.get("dodge", 50.0),
        catch=ratings_payload.get("catch", 50.0),
        stamina=ratings_payload.get("stamina", 50.0),
    ).apply_bounds()
    traits = PlayerTraits(
        potential=traits_payload.get("potential", 50.0),
        growth_curve=traits_payload.get("growth_curve", 50.0),
        consistency=traits_payload.get("consistency", 50.0),
        pressure=traits_payload.get("pressure", 50.0),
    )
    return Player(
        id=payload["id"],
        name=payload.get("name", payload["id"]),
        ratings=ratings,
        traits=traits,
    )


def _team_from_dict(payload: Dict[str, Any]) -> Team:
    players = tuple(_player_from_dict(player) for player in payload.get("players", []))
    return Team(
        id=payload["id"],
        name=payload.get("name", payload["id"]),
        players=players,
        coach_policy=_coach_policy_from_dict(payload.get("coach_policy", {})),
        chemistry=float(payload.get("chemistry", 0.5)),
    )


def match_setup_from_dict(payload: Dict[str, Any]) -> MatchSetup:
    team_a = _team_from_dict(payload["team_a"])
    team_b = _team_from_dict(payload["team_b"])
    config_version = payload.get("config_version", "phase1.v1")
    return MatchSetup(team_a=team_a, team_b=team_b, config_version=config_version)


def load_match_setup_from_path(path: str | Path) -> MatchSetup:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return match_setup_from_dict(data)


def describe_matchup(setup: MatchSetup) -> str:
    def _team_desc(team: Team) -> str:
        policy = team.coach_policy.normalized()
        return (
            f"{team.name} (chemistry {team.chemistry:.2f}, "
            f"target_stars={policy.target_stars:.2f}, risk={policy.risk_tolerance:.2f})"
        )

    return f"{_team_desc(setup.team_a)} vs\n{_team_desc(setup.team_b)}"


def summarize_team(team: Team) -> Dict[str, Any]:
    players = list(team.players)
    aggregates = {"accuracy": 0.0, "power": 0.0, "dodge": 0.0, "catch": 0.0}
    player_rows = []
    for player in players:
        ratings = player.ratings
        aggregates["accuracy"] += ratings.accuracy
        aggregates["power"] += ratings.power
        aggregates["dodge"] += ratings.dodge
        aggregates["catch"] += ratings.catch
        player_rows.append(
            {
                "id": player.id,
                "name": player.name,
                "ratings": {
                    "accuracy": ratings.accuracy,
                    "power": ratings.power,
                    "dodge": ratings.dodge,
                    "catch": ratings.catch,
                },
            }
        )
    count = max(len(players), 1)
    averages = {key: value / count for key, value in aggregates.items()}
    return {
        "team_id": team.id,
        "team_name": team.name,
        "chemistry": team.chemistry,
        "policy": team.coach_policy.as_dict(),
        "player_count": len(players),
        "average_ratings": averages,
        "players": player_rows,
    }


def summarize_matchup(setup: MatchSetup) -> Dict[str, Any]:
    return {
        "team_a": summarize_team(setup.team_a),
        "team_b": summarize_team(setup.team_b),
        "config_version": setup.config_version,
    }


def format_team_summary(team: Team) -> str:
    summary = summarize_team(team)
    averages = summary["average_ratings"]
    lines = [
        f"{team.name} (chem {team.chemistry:.2f})",
        (
            f"  Avg ratings -> accuracy={averages['accuracy']:.1f} "
            f"power={averages['power']:.1f} dodge={averages['dodge']:.1f} "
            f"catch={averages['catch']:.1f}"
        ),
    ]
    for player in summary["players"]:
        ratings = player["ratings"]
        lines.append(
            f"    {player['name']}: ACC={ratings['accuracy']:.0f} "
            f"POW={ratings['power']:.0f} DOD={ratings['dodge']:.0f} "
            f"CAT={ratings['catch']:.0f}"
        )
    return "\n".join(lines)


def format_matchup_summary(setup: MatchSetup) -> str:
    return f"{format_team_summary(setup.team_a)}\nVS\n{format_team_summary(setup.team_b)}"


__all__ = [
    "match_setup_from_dict",
    "load_match_setup_from_path",
    "describe_matchup",
    "summarize_team",
    "summarize_matchup",
    "format_team_summary",
    "format_matchup_summary",
]
