"""Canonical Plan B archetype derivation helper."""

from __future__ import annotations

from typing import Tuple

from .models import PlayerArchetype, PlayerRatings


GAP_THRESHOLD: float = 15.0

_BASE_ARCHETYPES = (
    PlayerArchetype.THROWER,
    PlayerArchetype.CATCHER,
    PlayerArchetype.BALL_HAWK,
    PlayerArchetype.DODGER_ANCHOR,
)

_HYBRID_MAP: dict[frozenset[PlayerArchetype], PlayerArchetype] = {
    frozenset({PlayerArchetype.THROWER, PlayerArchetype.CATCHER}): PlayerArchetype.THROWER_CATCHER,
    frozenset({PlayerArchetype.THROWER, PlayerArchetype.DODGER_ANCHOR}): PlayerArchetype.THROWER_DODGER,
    frozenset({PlayerArchetype.CATCHER, PlayerArchetype.BALL_HAWK}): PlayerArchetype.CATCHER_HAWK,
    frozenset({PlayerArchetype.BALL_HAWK, PlayerArchetype.DODGER_ANCHOR}): PlayerArchetype.HAWK_DODGER,
}


def _score(ratings: PlayerRatings, archetype: PlayerArchetype) -> float:
    if archetype == PlayerArchetype.THROWER:
        return ratings.accuracy + ratings.power
    if archetype == PlayerArchetype.CATCHER:
        return ratings.catch + ratings.catch_courage
    if archetype == PlayerArchetype.BALL_HAWK:
        return ratings.stamina + ratings.throw_selection_iq
    if archetype == PlayerArchetype.DODGER_ANCHOR:
        return ratings.dodge + ratings.tactical_iq
    raise ValueError(f"Non-base archetype passed to _score: {archetype!r}")


def _ranked_base_scores(ratings: PlayerRatings) -> list[tuple[PlayerArchetype, float]]:
    scored = [(archetype, _score(ratings, archetype)) for archetype in _BASE_ARCHETYPES]
    scored.sort(key=lambda item: (-item[1], item[0].name))
    return scored


def derive_archetype(ratings: PlayerRatings, *, allow_hybrid: bool = True) -> PlayerArchetype:
    ranked = _ranked_base_scores(ratings)
    primary, primary_score = ranked[0]
    secondary, secondary_score = ranked[1]
    if not allow_hybrid:
        return primary
    if primary_score - secondary_score > GAP_THRESHOLD:
        return primary
    hybrid = _HYBRID_MAP.get(frozenset({primary, secondary}))
    return hybrid or primary


def primary_and_secondary_bases(ratings: PlayerRatings) -> Tuple[PlayerArchetype, PlayerArchetype]:
    ranked = _ranked_base_scores(ratings)
    return ranked[0][0], ranked[1][0]


__all__ = ["GAP_THRESHOLD", "derive_archetype", "primary_and_secondary_bases"]
