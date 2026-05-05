from __future__ import annotations

from statistics import mean
from typing import Iterable

from .analysis import MatchAnalysis
from .events import MatchEvent
from .models import CoachPolicy, MatchSetup, Player, Team
from .narration import Lookup, narrate_event


def player_role(player: Player) -> str:
    ratings = {
        "Sniper": player.ratings.accuracy,
        "Power Arm": player.ratings.power,
        "Dodger": player.ratings.dodge,
        "Catcher": player.ratings.catch,
    }
    return max(ratings.items(), key=lambda item: item[1])[0]


def team_overall(team: Team) -> float:
    if not team.players:
        return 0.0
    return mean(player.overall() for player in team.players)


def policy_label(value: float) -> str:
    if value >= 0.8:
        return "Very High"
    if value >= 0.65:
        return "High"
    if value >= 0.45:
        return "Balanced"
    if value >= 0.25:
        return "Low"
    return "Very Low"


def policy_effect(key: str, value: float) -> str:
    label = policy_label(value)
    mapping = {
        "target_stars": f"{label} - focuses high-value opponents first.",
        "target_ball_holder": f"{label} - prioritizes opponents controlling the ball.",
        "risk_tolerance": f"{label} - accepts tighter odds for outs.",
        "sync_throws": f"{label} - looks for coordinated volleys and stamina burn.",
        "rush_frequency": f"{label} - changes how often the team forces pressure.",
        "rush_proximity": f"{label} - adjusts how close rushes must be before pressure.",
        "tempo": f"{label} - sets the pace of possessions and resets.",
        "catch_bias": f"{label} - changes how willingly defenders try catches.",
    }
    return mapping.get(key, label)


def matchup_preview(setup: MatchSetup) -> str:
    team_a = setup.team_a
    team_b = setup.team_b
    a_overall = team_overall(team_a)
    b_overall = team_overall(team_b)
    stronger = team_a if a_overall >= b_overall else team_b
    weaker = team_b if stronger is team_a else team_a
    delta = abs(a_overall - b_overall)
    style_line = (
        f"{team_a.name} tempo {policy_label(team_a.coach_policy.tempo)} vs "
        f"{team_b.name} risk {policy_label(team_b.coach_policy.risk_tolerance)}."
    )
    pressure_line = (
        f"{stronger.name} enters with a {delta:.1f} overall edge. "
        f"{weaker.name} needs catches and chemistry swings to flip the script."
    )
    return f"{style_line}\n{pressure_line}"


def team_snapshot(team: Team) -> str:
    top = sorted(team.players, key=lambda player: player.overall(), reverse=True)[:3]
    lines = [
        f"{team.name}",
        f"Overall {team_overall(team):.1f} | Chemistry {team.chemistry:.2f}",
        "Top Rotation:",
    ]
    for player in top:
        lines.append(f"  {player.name} - {player_role(player)} ({player.overall():.1f})")
    return "\n".join(lines)


def format_event_row(event: MatchEvent, lookup: Lookup) -> tuple[str, str, str, str, str]:
    actor = lookup.player(event.actors.get("thrower", event.actors.get("winner", "")))
    target = lookup.player(event.actors.get("target", ""))
    outcome = event.outcome.get("resolution") or event.outcome.get("winner") or event.event_type.upper()
    return (f"{event.tick:03d}", event.event_type.upper(), actor or "-", target or "-", str(outcome).upper())


def format_event_details(event: MatchEvent, lookup: Lookup) -> str:
    lines = [
        f"Tick {event.tick} | {event.event_type.upper()} | phase={event.phase}",
        narrate_event(event, lookup),
    ]
    if event.actors:
        lines.append("")
        lines.append("Actors")
        for key, value in event.actors.items():
            label = lookup.player(value) or lookup.team(value) or value
            lines.append(f"  {key}: {label}")
    if event.probabilities:
        lines.append("")
        lines.append("Probabilities")
        for key, value in event.probabilities.items():
            lines.append(f"  {key}: {value:.2f}")
    if event.rolls:
        lines.append("")
        lines.append("RNG Rolls")
        for key, value in event.rolls.items():
            lines.append(f"  {key}: {value:.2f}")
    if event.context:
        lines.append("")
        lines.append("Context")
        for key, value in event.context.items():
            lines.append(f"  {key}: {value}")
    if event.state_diff:
        lines.append("")
        lines.append("State Diff")
        for key, value in event.state_diff.items():
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def format_analysis_report(analysis: MatchAnalysis, lookup: Lookup) -> str:
    lines: list[str] = []
    if analysis.hero:
        lines.append(
            f"Hero Moment: {lookup.player(analysis.hero.player_id)} kept {lookup.team(analysis.hero.team_id)} alive."
        )
    if analysis.momentum:
        swing = max(analysis.momentum, key=lambda point: abs(point.differential))
        if swing.differential > 0:
            direction = "Team A"
        elif swing.differential < 0:
            direction = "Team B"
        else:
            direction = "Neither side"
        lines.append(f"Biggest swing: {direction} at tick {swing.tick} ({swing.differential:+d}).")
    return "\n".join(lines) if lines else "No analysis available yet."


def policy_rows(policy: CoachPolicy) -> Iterable[tuple[str, float, str]]:
    policy_dict = policy.as_dict()
    for key in (
        "target_stars",
        "target_ball_holder",
        "risk_tolerance",
        "sync_throws",
        "rush_frequency",
        "rush_proximity",
        "tempo",
        "catch_bias",
    ):
        value = policy_dict[key]
        yield key.replace("_", " ").title(), value, policy_effect(key, value)


__all__ = [
    "format_analysis_report",
    "format_event_details",
    "format_event_row",
    "matchup_preview",
    "player_role",
    "policy_effect",
    "policy_label",
    "policy_rows",
    "team_overall",
    "team_snapshot",
]
