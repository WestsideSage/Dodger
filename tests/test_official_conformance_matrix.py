"""Conformance matrix: every V11 must-have / partial-core section has at
least one named test home.

This test fails when a covered rule section loses its test home, so the
matrix in implementation-plan.md cannot silently drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_TESTS = Path(__file__).parent

SECTION_HOMES = {
    "1": ["test_official_rulesets.py"],
    "4": ["test_official_rulesets.py"],
    "6": ["test_official_match_lifecycle.py"],
    "9": ["test_official_match_lifecycle.py"],
    "11": ["test_official_ball_state.py"],
    "13": ["test_official_burden.py"],
    "14": ["test_official_burden.py"],
    "16": ["test_official_ball_state.py"],
    "17": ["test_official_ball_state.py", "test_official_sequence.py"],
    "18": ["test_official_sequence.py"],
    "20": ["test_official_sequence.py"],
    "21": ["test_official_sequence.py", "test_official_no_blocking.py"],
    "22": ["test_official_sequence.py", "test_official_catch_queue.py"],
    "23": ["test_official_catch_queue.py"],
    "24-core": ["test_official_ball_state.py", "test_official_catch_queue.py"],
    "25": ["test_official_sequence.py"],
    "27": ["test_official_no_blocking.py"],
    "34": ["test_official_discipline.py"],
    "35": ["test_official_discipline.py"],
}


@pytest.mark.parametrize("section,homes", sorted(SECTION_HOMES.items()))
def test_section_has_a_test_home(section, homes):
    for home in homes:
        path = REPO_TESTS / home
        assert path.exists(), f"V11 section {section} missing test home: {home}"
        text = path.read_text(encoding="utf-8")
        # Light-weight check: at least one test function exists.
        assert "def test_" in text, f"{home} has no test functions"
