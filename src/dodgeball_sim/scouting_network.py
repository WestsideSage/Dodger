"""V24 The Board Phase 6 — the money-gated Scouting Network.

A per-club network LEVEL (L1/L2/L3) decides which prospects render a full sheet
versus a bare name. Visibility is gated by the prospect's REACH band — a pure
function of his hidden trajectory, no new RNG draw — and (at L1) by geography:

  L1  full sheets for DISTRICT-reach kids in your home + neighbor districts.
  L2  + every REGIONAL-reach prospect, and DISTRICT-reach anywhere (regional net).
  L3  + every NATIONAL-reach prospect (the whole country).

Below your level a prospect is a NAME WITHOUT A SHEET: you know he exists and
where he's from, but not his ratings, motivations, or archetype until you invest.
The free agent pool stays ungated (the hope layer) — this gates the class only.

This is a DISTINCT concept from the slot-budget Scout verb (recruiting_actions)
and the dormant named-scout four-axis engine (scouting_center): the trap the
spec flags is conflating the three. This module owns ONLY the money-gated reach.
"""
from __future__ import annotations

from typing import Sequence, Tuple

from .config import (
    AI_NETWORK_LEVEL_BY_TIER,
    NETWORK_DEFAULT_LEVEL,
    NETWORK_MAX_LEVEL,
    NETWORK_UPGRADE_COSTS,
)
from .scouting_center import Trajectory

REACH_DISTRICT = "DISTRICT"
REACH_REGIONAL = "REGIONAL"
REACH_NATIONAL = "NATIONAL"
REACH_BANDS: Tuple[str, ...] = (REACH_DISTRICT, REACH_REGIONAL, REACH_NATIONAL)


def reach_band_for_trajectory(trajectory: str) -> str:
    """A prospect's reach band, derived purely from his hidden growth arc: the
    rare STAR/GENERATIONAL arcs are NATIONAL names, IMPACT arcs REGIONAL, the
    common NORMAL arcs DISTRICT-local. No new draw — a pure function of a value
    the generator already rolled."""
    if trajectory in (Trajectory.STAR.value, Trajectory.GENERATIONAL.value):
        return REACH_NATIONAL
    if trajectory == Trajectory.IMPACT.value:
        return REACH_REGIONAL
    return REACH_DISTRICT


def prospect_fully_visible(
    *,
    reach_band: str,
    hometown: str,
    level: int,
    home_district: str,
    neighbors: Sequence[str],
    home_recognized: bool = True,
) -> bool:
    """Whether a club at this network ``level`` sees the prospect's full sheet.

    NATIONAL needs L3; REGIONAL needs L2; DISTRICT is visible at L2+ anywhere, or
    at L1 only when the prospect is from the club's home or a neighbor district.
    ``home_recognized`` is False for a club not rooted in one of the seven
    districts (e.g. a brand-new founder with a custom home): such a club runs a
    generic local network that sees all DISTRICT-reach prospects at L1 rather
    than being blinded to the entire class.
    """
    level = int(level)
    if reach_band == REACH_NATIONAL:
        return level >= 3
    if reach_band == REACH_REGIONAL:
        return level >= 2
    # DISTRICT reach.
    if level >= 2:
        return True
    if not home_recognized:
        return True
    return hometown == home_district or hometown in tuple(neighbors)


def network_upgrade_cost(*, to_level: int, scouting_head_rating: float) -> int:
    """Treasury cost ($k) to upgrade the network to ``to_level``, compressed by
    the scouting head (a stronger head makes reach cheaper)."""
    from .staff_effects import scouting_network_cost_compression

    base = NETWORK_UPGRADE_COSTS[int(to_level)]
    return round(base * scouting_network_cost_compression(scouting_head_rating))


def next_network_level(level: int) -> int | None:
    """The level you'd upgrade to next, or None if already maxed."""
    nxt = int(level) + 1
    return nxt if nxt <= NETWORK_MAX_LEVEL else None


def ai_network_level(tier: int | None, *, jitter: float) -> int:
    """An AI club's network level by division tier, with a deterministic chance
    of a one-level blind spot (the caller supplies a stable [0,1) ``jitter``)."""
    from .config import AI_NETWORK_BLINDSPOT_RATE

    base = AI_NETWORK_LEVEL_BY_TIER.get(int(tier or 0), NETWORK_DEFAULT_LEVEL)
    if jitter < AI_NETWORK_BLINDSPOT_RATE:
        base = max(NETWORK_DEFAULT_LEVEL, base - 1)
    return base


__all__ = [
    "REACH_BANDS",
    "REACH_DISTRICT",
    "REACH_REGIONAL",
    "REACH_NATIONAL",
    "ai_network_level",
    "network_upgrade_cost",
    "next_network_level",
    "prospect_fully_visible",
    "reach_band_for_trajectory",
]
