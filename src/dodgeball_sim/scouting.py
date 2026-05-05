from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import Player
from .rng import DeterministicRNG

BudgetLevel = Literal["low", "medium", "high"]
_RATING_NAMES = ("accuracy", "power", "dodge", "catch", "stamina")


@dataclass(frozen=True)
class ScoutingReport:
    player_id: str
    revealed_archetype: str
    rating_ranges: dict[str, tuple[int, int]]
    exact_ratings: dict[str, int]


def generate_scout_report(
    player: Player,
    budget_level: BudgetLevel | str,
    rng: DeterministicRNG,
) -> ScoutingReport:
    """Return a deterministic scouting report for one player."""
    normalized_budget = _normalize_budget_level(budget_level)
    archetype = _reveal_archetype(player)
    exact_ratings = _rounded_ratings(player)

    if normalized_budget == "low":
        return ScoutingReport(
            player_id=player.id,
            revealed_archetype=archetype,
            rating_ranges={},
            exact_ratings={},
        )

    width = 15 if normalized_budget == "medium" else 3
    rating_ranges = {
        rating_name: _estimate_rating_range(exact_ratings[rating_name], width, rng)
        for rating_name in _RATING_NAMES
    }
    if normalized_budget == "medium":
        exact_ratings = {}

    return ScoutingReport(
        player_id=player.id,
        revealed_archetype=archetype,
        rating_ranges=rating_ranges,
        exact_ratings=exact_ratings,
    )


def _estimate_rating_range(
    actual_rating: int,
    width: int,
    rng: DeterministicRNG,
) -> tuple[int, int]:
    low_bias = int(round(rng.roll(0.0, float(width))))
    high_bias = int(round(rng.roll(0.0, float(width))))
    low = _clamp_rating(actual_rating - low_bias)
    high = _clamp_rating(actual_rating + high_bias)
    if low > high:
        low, high = high, low
    if low == high and width > 0:
        high = _clamp_rating(low + 1)
    return low, high


def _reveal_archetype(player: Player) -> str:
    ratings = player.ratings
    dominant_rating = max(
        _RATING_NAMES,
        key=lambda name: getattr(ratings, name),
    )
    archetypes = {
        "accuracy": "Sharpshooter",
        "power": "Enforcer",
        "dodge": "Escape Artist",
        "catch": "Ball Hawk",
        "stamina": "Iron Engine",
    }
    return archetypes[dominant_rating]


def _rounded_ratings(player: Player) -> dict[str, int]:
    ratings = player.ratings
    return {
        rating_name: int(round(getattr(ratings, rating_name)))
        for rating_name in _RATING_NAMES
    }


def _normalize_budget_level(value: BudgetLevel | str) -> BudgetLevel:
    normalized = str(value).strip().lower()
    if normalized not in {"low", "medium", "high"}:
        raise ValueError(f"Unsupported scouting budget level: {value!r}")
    return normalized


def _clamp_rating(value: int) -> int:
    return max(0, min(100, int(value)))


__all__ = ["BudgetLevel", "ScoutingReport", "generate_scout_report"]
