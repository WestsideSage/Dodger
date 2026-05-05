from __future__ import annotations

from pathlib import Path

import pytest

from dodgeball_sim.models import PlayerTraits
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.scouting import generate_scout_report

from .factories import make_player


def test_generate_scout_report_is_seeded_and_budget_scoped():
    player = make_player(
        "prospect",
        accuracy=78,
        power=64,
        dodge=61,
        catch=58,
        stamina=72,
    )
    seed = derive_seed(2026, "scouting", "season_2027", player.id, "club_a")

    low = generate_scout_report(player, "low", DeterministicRNG(seed))
    medium = generate_scout_report(player, "medium", DeterministicRNG(seed))
    high = generate_scout_report(player, "high", DeterministicRNG(seed))

    assert low.player_id == player.id
    assert low.revealed_archetype == "Sharpshooter"
    assert low.rating_ranges == {}
    assert low.exact_ratings == {}

    assert set(medium.rating_ranges) == {"accuracy", "power", "dodge", "catch", "stamina"}
    assert medium.exact_ratings == {}
    assert set(high.exact_ratings) == {"accuracy", "power", "dodge", "catch", "stamina"}


def test_generate_scout_report_same_seed_produces_same_ranges():
    player = make_player("rookie", accuracy=66, power=73, dodge=57, catch=62, stamina=69)
    seed = derive_seed(2026, "scouting", "season_2028", player.id, "club_b")

    report_a = generate_scout_report(player, "medium", DeterministicRNG(seed))
    report_b = generate_scout_report(player, "medium", DeterministicRNG(seed))

    assert report_a == report_b


@pytest.mark.parametrize("budget_level,expected_width", [("medium", 15), ("high", 3)])
def test_generate_scout_report_ranges_contain_actual_rating_with_budget_width(
    budget_level: str,
    expected_width: int,
):
    player = make_player("target", accuracy=74, power=68, dodge=63, catch=59, stamina=71)
    report = generate_scout_report(player, budget_level, DeterministicRNG(77))

    for rating_name, actual_value in {
        "accuracy": 74,
        "power": 68,
        "dodge": 63,
        "catch": 59,
        "stamina": 71,
    }.items():
        low, high = report.rating_ranges[rating_name]
        assert low <= actual_value <= high
        assert actual_value - low <= expected_width
        assert high - actual_value <= expected_width


def test_generate_scout_report_high_budget_exposes_near_exact_values():
    player = make_player("elite", accuracy=81.6, power=70.2, dodge=66.4, catch=64.5, stamina=75.1)
    report = generate_scout_report(player, "high", DeterministicRNG(101))

    assert report.exact_ratings == {
        "accuracy": 82,
        "power": 70,
        "dodge": 66,
        "catch": 64,
        "stamina": 75,
    }


def test_generate_scout_report_invalid_budget_raises():
    with pytest.raises(ValueError):
        generate_scout_report(make_player("bad"), "elite", DeterministicRNG(1))


def test_scouting_module_has_no_db_boundary_imports():
    source = Path("src/dodgeball_sim/scouting.py").read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "sqlite3" not in source
