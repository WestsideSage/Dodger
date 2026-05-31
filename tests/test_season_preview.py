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


def test_build_season_preview_prettifies_raw_archetype_keys() -> None:
    """Raw archetype enum values must render as display names, not keys."""
    roster = [
        {"archetype": "thrower", "overall": 80},
        {"archetype": "thrower", "overall": 78},
        {"archetype": "hawk_dodger", "overall": 60},
        {"archetype": "hawk_dodger", "overall": 62},
    ]
    preview = build_season_preview(
        regular_season_weeks=12, bye_week=6, playoff_cut=8, total_clubs=16, roster=roster,
    )
    assert preview["strength"]["archetype"] == "Sharpshooter"
    assert preview["weakness"]["archetype"] == "Hit-and-Run"
    assert "hawk_dodger" not in preview["weakness"]["archetype"]


class TestSeasonPreviewArchetypeKey:
    """strength and weakness expose the raw archetype_key alongside the display name."""

    def test_strength_carries_raw_key(self):
        roster = [
            {"archetype": "hawk_dodger", "overall": 72}
        ]
        payload = build_season_preview(
            regular_season_weeks=12,
            bye_week=6,
            playoff_cut=4,
            total_clubs=8,
            roster=roster,
        )
        assert payload["strength"]["archetype"] == "Hit-and-Run"
        assert payload["strength"]["archetype_key"] == "hawk_dodger"

    def test_weakness_carries_raw_key(self):
        roster = [
            {"archetype": "thrower", "overall": 80},
            {"archetype": "catcher", "overall": 55},
        ]
        payload = build_season_preview(
            regular_season_weeks=12,
            bye_week=6,
            playoff_cut=4,
            total_clubs=8,
            roster=roster,
        )
        assert payload["weakness"]["archetype_key"] == "catcher"

    def test_null_strength_when_roster_empty(self):
        payload = build_season_preview(
            regular_season_weeks=12,
            bye_week=6,
            playoff_cut=4,
            total_clubs=8,
            roster=[],
        )
        assert payload["strength"] is None
        assert payload["weakness"] is None

