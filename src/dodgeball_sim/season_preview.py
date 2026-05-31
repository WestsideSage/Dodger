"""Pure helper for the Week 1 Season Preview screen.

Task 12 (2026-05-28 playtest-fixes): a new player went three or four
weeks without being told the season length, where their bye falls, or
what the playoff cut is. This module shapes that orientation screen from
schedule facts and roster values the engine already has -- no new
scoring, no I/O -- so the copy can be pinned by tests.
"""

from __future__ import annotations

from typing import Any

from .models import archetype_display_name
from .next_best_improvement import strongest_position_group, weakest_position_group


def derive_schedule_facts(
    *,
    regular_weeks: list[int],
    user_match_weeks: list[int],
) -> dict[str, Any]:
    """Return ``{regular_season_weeks, bye_week}`` from week numbers.

    ``regular_weeks`` is every distinct regular-season week; the bye is
    the first regular week in which the player has no match.
    """

    distinct = sorted(set(int(w) for w in regular_weeks))
    played = set(int(w) for w in user_match_weeks)
    bye_week = next((w for w in distinct if w not in played), None)
    return {"regular_season_weeks": len(distinct), "bye_week": bye_week}


def build_season_preview(
    *,
    regular_season_weeks: int,
    bye_week: int | None,
    playoff_cut: int,
    total_clubs: int,
    roster: list[dict[str, Any]],
    skipped: bool = False,
) -> dict[str, Any]:
    """Assemble the season-preview payload.

    ``roster`` items: ``{"archetype": str, "overall": int}``. Strength and
    weakness name the highest/lowest average-OVR archetype groups.
    """

    strength = strongest_position_group(roster)
    weakness = weakest_position_group(roster)
    bye_text = f"Week {bye_week}" if bye_week else "None scheduled"
    return {
        "regular_season_weeks": regular_season_weeks,
        "bye_week": bye_week,
        "bye_text": bye_text,
        "playoff_cut": playoff_cut,
        "total_clubs": total_clubs,
        "top_goal": (
            f"Finish in the top {playoff_cut} of {total_clubs} to reach the playoffs."
        ),
        "strength": (
            {
                "archetype": archetype_display_name(strength["archetype"]),
                "archetype_key": strength["archetype"],
                "avg_overall": strength["avg_overall"],
            }
            if strength is not None
            else None
        ),
        "weakness": (
            {
                "archetype": archetype_display_name(weakness["archetype"]),
                "archetype_key": weakness["archetype"],
                "avg_overall": weakness["avg_overall"],
            }
            if weakness is not None
            else None
        ),
        "skipped": bool(skipped),
    }


__all__ = ["build_season_preview", "derive_schedule_facts"]
