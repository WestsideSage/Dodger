from __future__ import annotations

"""Post-hoc retrospective win-probability analyzer.

These functions are retrospective leverage estimates, not live predictions.
They are consumed post-match by Match Report surfaces such as turning points
and upset tags. The pre-match preview must not display these numbers.
"""

import math
from typing import Iterable, List

from .events import MatchEvent
from .models import Team

_K_OVR = 0.06
_K_SURV = 0.6


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _team_average_overall(team: Team) -> float:
    if not team.players:
        return 0.0
    return sum(player.overall() for player in team.players) / len(team.players)


def pre_match_expected_outcome(team_a: Team, team_b: Team) -> float:
    """Return p(team_a wins), as a retrospective post-match baseline."""
    diff = _team_average_overall(team_a) - _team_average_overall(team_b)
    return _sigmoid(_K_OVR * diff)


def per_event_wp_delta(
    events: Iterable[MatchEvent],
    team_a_id: str,
    team_b_id: str,
    team_a_player_ids: List[str],
    team_b_player_ids: List[str],
) -> List[float]:
    """Return each event's win-probability delta from team_a's perspective."""
    alive_a = set(team_a_player_ids)
    alive_b = set(team_b_player_ids)

    def _wp_a() -> float:
        return _sigmoid(_K_SURV * (len(alive_a) - len(alive_b)))

    deltas: List[float] = []
    wp_before = _wp_a()
    for event in events:
        eliminated = event.state_diff.get("player_out")
        if eliminated:
            player_id = eliminated.get("player_id")
            team_id = eliminated.get("team")
            if team_id == team_a_id:
                alive_a.discard(player_id)
            elif team_id == team_b_id:
                alive_b.discard(player_id)
        wp_after = _wp_a()
        deltas.append(wp_after - wp_before)
        wp_before = wp_after
    return deltas


__all__ = ["pre_match_expected_outcome", "per_event_wp_delta"]
