"""The post-loss improvement panel must point at real, ranked weak spots
without inventing data.

Task 11 (2026-05-28 playtest-fixes).
"""

from __future__ import annotations

from dodgeball_sim.next_best_improvement import (
    build_improvement_panel,
    coolest_critical_recruit,
    lowest_condition_starter,
    weakest_position_group,
)


def test_weakest_group_is_lowest_average_ovr():
    roster = [
        {"archetype": "Sharpshooter", "overall": 80},
        {"archetype": "Sharpshooter", "overall": 78},
        {"archetype": "Blocker", "overall": 60},
        {"archetype": "Blocker", "overall": 64},
    ]
    group = weakest_position_group(roster)
    assert group is not None
    assert group["archetype"] == "Blocker"
    assert group["avg_overall"] == 62.0


def test_lowest_condition_starter_picks_min_stamina():
    starters = [
        {"name": "A", "stamina": 70},
        {"name": "B", "stamina": 41},
        {"name": "C", "stamina": 55},
    ]
    starter = lowest_condition_starter(starters)
    assert starter == {"name": "B", "stamina": 41}


def test_coolest_critical_recruit_ignores_low_fit():
    recruits = [
        {"name": "HighFitCool", "fit_score": 82, "interest": 20},
        {"name": "LowFitCold", "fit_score": 40, "interest": 5},
        {"name": "HighFitWarm", "fit_score": 75, "interest": 60},
    ]
    recruit = coolest_critical_recruit(recruits)
    assert recruit is not None
    assert recruit["name"] == "HighFitCool"


def test_panel_returns_at_most_three_with_categories():
    panel = build_improvement_panel(
        roster=[{"archetype": "Blocker", "overall": 60}],
        starters=[{"name": "B", "stamina": 41}],
        recruits=[{"name": "R", "fit_score": 80, "interest": 15}],
    )
    assert len(panel) == 3
    assert {p["category"] for p in panel} == {"position_group", "condition", "recruit"}
    for card in panel:
        assert card["title"]
        assert card["detail"]


def test_panel_degrades_when_inputs_missing():
    panel = build_improvement_panel(roster=[], starters=[], recruits=[])
    assert panel == []
