from __future__ import annotations

"""Season scheduling.

v1 status (Manager Mode Milestone 0, verified 2026-04-26):
  - Single round-robin only.
  - V2-F Manager Mode can append playoff matches after this module's
    regular-season schedule.
  - Odd club counts get a bye round.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

from .rng import DeterministicRNG, derive_seed


@dataclass(frozen=True)
class ScheduledMatch:
    match_id: str
    season_id: str
    week: int
    home_club_id: str
    away_club_id: str


def generate_round_robin(
    club_ids: List[str],
    root_seed: int,
    season_id: str,
    league_id: str,
) -> List[ScheduledMatch]:
    """Generate a balanced round-robin schedule. Pure and deterministic.

    Uses the circle algorithm: one club is fixed, the rest rotate each round.
    Home/away assignment is randomised per matchup via schedule_seed.
    An odd number of clubs receives a bye each round; bye placeholders are
    omitted from the returned match list.
    """
    if len(club_ids) < 2:
        raise ValueError("Need at least 2 clubs for a schedule")

    ids = list(club_ids)  # copy so caller's list is unaffected
    if len(ids) % 2 != 0:
        ids.append("__bye__")

    n = len(ids)
    rounds = n - 1
    matches_per_round = n // 2

    seed = derive_seed(root_seed, "schedule", league_id, season_id)
    rng = DeterministicRNG(seed)

    schedule: List[ScheduledMatch] = []
    fixed = ids[0]
    rotating = ids[1:]

    for round_idx in range(rounds):
        week = round_idx + 1
        pairs: List[tuple[str, str]] = []

        # Fixed club vs last in rotation
        pairs.append((fixed, rotating[-1]))

        # Middle pairs
        for i in range(matches_per_round - 1):
            pairs.append((rotating[i], rotating[-(i + 2)]))

        for home_candidate, away_candidate in pairs:
            if "__bye__" in (home_candidate, away_candidate):
                continue
            # Randomise home/away so neither club always hosts
            if rng.unit() < 0.5:
                home_candidate, away_candidate = away_candidate, home_candidate
            schedule.append(
                ScheduledMatch(
                    match_id=_stable_match_id(season_id, week, home_candidate, away_candidate),
                    season_id=season_id,
                    week=week,
                    home_club_id=home_candidate,
                    away_club_id=away_candidate,
                )
            )

        # Rotate: move last element to front of rotation
        rotating = [rotating[-1]] + rotating[:-1]

    return schedule


def _stable_match_id(season_id: str, week: int, home_id: str, away_id: str) -> str:
    """Stable, human-readable match ID that doesn't depend on insertion order."""
    return f"{season_id}_w{week:02d}_{home_id}_vs_{away_id}"


def season_format_summary() -> Dict[str, Any]:
    """Return the current Manager Mode season format for UI labels and reports."""
    return {
        "format": "round_robin_top4_playoff",
        "playoffs": True,
        "champion_rule": "playoff_final",
    }


__all__ = ["ScheduledMatch", "generate_round_robin", "season_format_summary"]
