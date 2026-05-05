from __future__ import annotations

from pathlib import Path

import pytest

from dodgeball_sim.cup import generate_cup_bracket
from dodgeball_sim.rng import DeterministicRNG


def test_generate_cup_bracket_is_deterministic_for_same_seed():
    club_ids = ("club_a", "club_b", "club_c", "club_d", "club_e", "club_f")

    bracket_a = generate_cup_bracket(club_ids, DeterministicRNG(77))
    bracket_b = generate_cup_bracket(club_ids, DeterministicRNG(77))

    assert bracket_a == bracket_b


def test_generate_cup_bracket_builds_expected_tree_with_byes():
    bracket = generate_cup_bracket(
        ("club_a", "club_b", "club_c", "club_d", "club_e", "club_f"),
        DeterministicRNG(11),
    )

    assert bracket.total_rounds == 3
    assert len(bracket.opening_round.matches) == 4
    assert len(bracket.opening_byes) == 2
    assert bracket.final_match_id == "cup_r3_m1"

    bye_matches = [match for match in bracket.opening_round.matches if match.is_bye]
    played_matches = [match for match in bracket.opening_round.matches if not match.is_bye]
    assert all(match.auto_advance_club_id is not None for match in bye_matches)
    assert all(match.auto_advance_club_id is None for match in played_matches)

    round_two = bracket.rounds[1]
    assert round_two.matches[0].side_a.source_match_id == "cup_r1_m1"
    assert round_two.matches[0].side_b.source_match_id == "cup_r1_m2"
    assert round_two.matches[1].side_a.source_match_id == "cup_r1_m3"
    assert round_two.matches[1].side_b.source_match_id == "cup_r1_m4"


def test_generate_cup_bracket_with_power_of_two_has_no_byes():
    bracket = generate_cup_bracket(
        ("club_a", "club_b", "club_c", "club_d"),
        DeterministicRNG(5),
    )

    assert bracket.total_rounds == 2
    assert bracket.opening_byes == ()
    assert all(not match.is_bye for match in bracket.opening_round.matches)


@pytest.mark.parametrize(
    ("club_ids", "message"),
    [
        (("club_a",), "At least two clubs"),
        (("club_a", "club_a"), "must be unique"),
        (("club_a", " "), "must not contain blank"),
    ],
)
def test_generate_cup_bracket_rejects_invalid_input(
    club_ids: tuple[str, ...],
    message: str,
):
    with pytest.raises(ValueError, match=message):
        generate_cup_bracket(club_ids, DeterministicRNG(1))


def test_cup_module_has_no_db_boundary_imports():
    source = Path("src/dodgeball_sim/cup.py").read_text(encoding="utf-8")

    assert "persistence" not in source
    assert "sqlite3" not in source
