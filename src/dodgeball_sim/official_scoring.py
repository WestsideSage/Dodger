"""Canonical USA Dodgeball pro-style match scoring domain models and helpers.

Precedence (see V11 rules):
- Foam/No-Sting: A team earns 1 game point ONLY on full elimination of the opponent.
  Unresolved games (e.g. time expires, or No Blocking tie) award 0 points.
- Cloth: Wins (elimination or player majority at expiry) award 2 game points.
  Ties (equal active player counts at expiry) award 1 game point each.
  Losses award 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple


@dataclass(frozen=True)
class OfficialGameScore:
    """Score summary of a single game inside an official match."""

    game_number: int
    winner_team_id: str | None
    team_a_points: int
    team_b_points: int
    result_type: Literal[
        "elimination",
        "cloth_active_count",
        "tie",
        "no_point",
        "forfeit",
        "overtime",
        "sudden_death",
    ]
    final_active_a: int
    final_active_b: int
    mode: str
    elapsed_seconds: int


@dataclass(frozen=True)
class OfficialMatchScore:
    """Match-level pro-style scoreboard for official ruleset matches."""

    team_a_id: str
    team_b_id: str
    team_a_game_points: int
    team_b_game_points: int
    team_a_games_won: int
    team_b_games_won: int
    tied_games: int
    no_point_games: int
    games: Tuple[OfficialGameScore, ...]
    winner_team_id: str | None


def foam_game_points(winner_team_id: str | None, team_a_id: str, team_b_id: str) -> Tuple[int, int]:
    """Calculate game points for a foam or no-sting game.

    Only full elimination wins award a game point (1 point). Unresolved games
    award 0 points.
    """
    if winner_team_id == team_a_id:
        return 1, 0
    if winner_team_id == team_b_id:
        return 0, 1
    return 0, 0


def cloth_game_points(
    winner_team_id: str | None,
    is_tie: bool,
    team_a_id: str,
    team_b_id: str,
) -> Tuple[int, int]:
    """Calculate game points for a cloth game.

    Wins award 2 points, ties award 1 point each, losses award 0.
    """
    if is_tie or (winner_team_id is None and not is_tie):
        # In cloth, if no winner is declared or it is explicitly a tie, it's a 1-1 tie.
        # Wait, if there's a forfeit or unresolved situation, winner_team_id could be something else,
        # but standard tie at expiry is 1-1.
        return 1, 1
    if winner_team_id == team_a_id:
        return 2, 0
    if winner_team_id == team_b_id:
        return 0, 2
    return 0, 0


def match_winner_from_points(
    team_a_points: int,
    team_b_points: int,
    team_a_id: str,
    team_b_id: str,
) -> str | None:
    """Determine the match winner based on aggregated game points."""
    if team_a_points > team_b_points:
        return team_a_id
    if team_b_points > team_a_points:
        return team_b_id
    return None
