"""Tests for the manual lineup override pipeline.

Task 2 (Lineup Editor) — agency win: a benched 76 OVR player can be promoted
into the starting six and the override sticks.
"""

import pytest

from dodgeball_sim.lineup import apply_manual_lineup, LineupViolation
from dodgeball_sim.sample_data import club_with_bench_star


def test_manual_swap_promotes_bench_star():
    club = club_with_bench_star(bench_player_id="ezra_prism", bench_ovr=76)
    new_lineup = apply_manual_lineup(
        club,
        starters=["ezra_prism", "p2", "p3", "p4", "p5", "p6"],
    )
    starter_ids = [p.player_id for p in new_lineup.starters]
    assert "ezra_prism" in starter_ids
    assert len(starter_ids) == 6


def test_manual_swap_rejects_non_roster_player():
    club = club_with_bench_star(bench_player_id="ezra_prism", bench_ovr=76)
    with pytest.raises(LineupViolation) as exc:
        apply_manual_lineup(club, starters=["ghost", "p2", "p3", "p4", "p5", "p6"])
    assert exc.value.reason == "not_on_roster"


def test_manual_swap_rejects_duplicate():
    club = club_with_bench_star(bench_player_id="ezra_prism", bench_ovr=76)
    with pytest.raises(LineupViolation) as exc:
        apply_manual_lineup(
            club, starters=["ezra_prism", "ezra_prism", "p3", "p4", "p5", "p6"]
        )
    assert exc.value.reason == "duplicate"


def test_manual_swap_rejects_wrong_count():
    club = club_with_bench_star(bench_player_id="ezra_prism", bench_ovr=76)
    with pytest.raises(LineupViolation) as exc:
        apply_manual_lineup(club, starters=["ezra_prism", "p2", "p3"])
    assert exc.value.reason == "position_count"
