"""Tests for the Week 1 Season Preview pure helpers."""

from __future__ import annotations

from dodgeball_sim.season_preview import build_season_preview, derive_schedule_facts


def test_derive_schedule_facts_finds_bye_week() -> None:
    facts = derive_schedule_facts(
        regular_weeks=[1, 2, 3, 4, 5],
        user_match_weeks=[1, 2, 4, 5],
    )
    assert facts["regular_season_weeks"] == 5
    assert facts["bye_week"] == 3


def test_derive_schedule_facts_no_bye_when_every_week_played() -> None:
    facts = derive_schedule_facts(
        regular_weeks=[1, 2, 3],
        user_match_weeks=[1, 2, 3],
    )
    assert facts["regular_season_weeks"] == 3
    assert facts["bye_week"] is None


def test_build_season_preview_names_strength_and_weakness() -> None:
    roster = [
        {"archetype": "Thrower", "overall": 80},
        {"archetype": "Thrower", "overall": 78},
        {"archetype": "Blocker", "overall": 60},
        {"archetype": "Blocker", "overall": 62},
    ]
    preview = build_season_preview(
        regular_season_weeks=12,
        bye_week=6,
        playoff_cut=8,
        total_clubs=16,
        roster=roster,
    )
    assert preview["regular_season_weeks"] == 12
    assert preview["bye_text"] == "Week 6"
    assert preview["top_goal"] == "Finish in the top 8 of 16 to reach the playoffs."
    assert preview["strength"]["archetype"] == "Thrower"
    assert preview["weakness"]["archetype"] == "Blocker"
    assert preview["skipped"] is False


def test_build_season_preview_handles_no_bye() -> None:
    preview = build_season_preview(
        regular_season_weeks=10,
        bye_week=None,
        playoff_cut=4,
        total_clubs=8,
        roster=[],
    )
    assert preview["bye_text"] == "None scheduled"
    assert preview["strength"] is None
    assert preview["weakness"] is None


def test_build_season_preview_marks_skipped() -> None:
    preview = build_season_preview(
        regular_season_weeks=10,
        bye_week=5,
        playoff_cut=4,
        total_clubs=8,
        roster=[{"archetype": "Thrower", "overall": 70}],
        skipped=True,
    )
    assert preview["skipped"] is True
