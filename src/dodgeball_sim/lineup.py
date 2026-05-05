from __future__ import annotations

"""Lineup resolution for Manager Mode.

A lineup is an ordered list of player IDs. The UI may show the full ordered
roster, but match simulation activates only the first STARTERS_COUNT valid
players. Bench players remain rostered and visible outside the match.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .models import Player, PlayerArchetype

STARTERS_COUNT = 6

_ROLE_NAMES = ["Captain", "Striker", "Anchor", "Runner", "Rookie", "Utility"]

_ROLE_LIABILITIES = {
    0: {PlayerArchetype.POWER},
    1: {PlayerArchetype.DEFENSE},
    2: {PlayerArchetype.AGILITY},
    3: {PlayerArchetype.POWER},
    4: set(),
    5: set(),
}

def check_lineup_liabilities(roster: Sequence[Player], lineup_ids: Sequence[str]) -> List[str]:
    players_by_id = {player.id: player for player in roster}
    starters = [players_by_id[pid] for pid in lineup_ids[:STARTERS_COUNT] if pid in players_by_id]
    warnings = []
    for idx, player in enumerate(starters):
        role_name = _ROLE_NAMES[idx] if idx < len(_ROLE_NAMES) else "Utility"
        liabilities = _ROLE_LIABILITIES.get(idx, set())
        if player.archetype in liabilities:
            warnings.append(f"{player.name} is a mismatched {role_name}: lacks appropriate archetype.")
    return warnings

def is_liability(team_players: Sequence[Player], player: Player) -> bool:
    try:
        idx = list(team_players).index(player)
        return player.archetype in _ROLE_LIABILITIES.get(idx, set())
    except ValueError:
        return False

def optimize_ai_lineup(roster: Sequence[Player]) -> List[str]:
    """Greedy heuristic: assign highest OVR players to non-liability slots."""
    sorted_roster = sorted(roster, key=lambda p: -p.overall())
    lineup: List[Player | None] = [None] * STARTERS_COUNT
    remaining = list(sorted_roster)

    for i in range(STARTERS_COUNT):
        liabilities = _ROLE_LIABILITIES.get(i, set())
        for p in remaining:
            if p.archetype not in liabilities:
                lineup[i] = p
                remaining.remove(p)
                break

    for i in range(STARTERS_COUNT):
        if lineup[i] is None and remaining:
            lineup[i] = remaining.pop(0)

    final_ids = [p.id for p in lineup if p is not None]
    final_ids.extend(p.id for p in remaining)
    return final_ids

@dataclass(frozen=True)
class ResolvedLineup:
    """Lineup with diagnostics about IDs dropped during resolution."""
    lineup: List[str]
    dropped_ids: List[str]


class LineupResolver:
    """Resolve override -> default -> roster order, then backfill by OVR."""

    def resolve(
        self,
        roster: Sequence[Player],
        default: Optional[Sequence[str]],
        override: Optional[Sequence[str]],
    ) -> List[str]:
        return self.resolve_with_diagnostics(roster, default, override).lineup

    def resolve_with_diagnostics(
        self,
        roster: Sequence[Player],
        default: Optional[Sequence[str]],
        override: Optional[Sequence[str]],
    ) -> ResolvedLineup:
        roster_ids = {player.id for player in roster}
        chosen: Sequence[str]
        if override is not None:
            chosen = override
        elif default is not None:
            chosen = default
        else:
            chosen = [player.id for player in roster]

        kept: List[str] = []
        dropped: List[str] = []
        seen: set[str] = set()
        for player_id in chosen:
            if player_id in roster_ids and player_id not in seen:
                kept.append(player_id)
                seen.add(player_id)
            elif player_id not in roster_ids:
                dropped.append(player_id)

        remaining = [player for player in roster if player.id not in seen]
        remaining.sort(key=lambda player: (-player.overall(), player.id))
        kept.extend(player.id for player in remaining)

        return ResolvedLineup(lineup=kept, dropped_ids=dropped)

    def active_starters(self, resolved_lineup: Sequence[str]) -> List[str]:
        """Return the legal active match participants from a resolved lineup."""
        return list(resolved_lineup[:STARTERS_COUNT])


__all__ = ["STARTERS_COUNT", "LineupResolver", "ResolvedLineup", "check_lineup_liabilities", "is_liability", "optimize_ai_lineup"]
