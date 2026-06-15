"""V24 The Board Phase 7 — motivations on the Signing Day picker.

The Signing Day choice cards must not know less than the in-season board the
player built their shortlist on: each prospect choice carries the same visible
motivation grades + dealbreaker (revealed once scouted) the board shows.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.offseason_ceremony import available_recruitment_choices

ROOT_SEED = 20260612


def _conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    initialize_curated_manager_career(conn, "aurora", ROOT_SEED, world="pyramid")
    return conn


def test_pyramid_signing_day_choices_carry_motivations():
    conn = _conn()
    choices = available_recruitment_choices(conn, 1)
    prospects = [c for c in choices if c.get("kind") == "prospect"]
    assert prospects, "pyramid Signing Day should offer prospect choices"
    # Every visible prospect choice exposes the motivation view (board parity).
    for choice in prospects:
        assert "motivations" in choice
        assert "dealbreaker" in choice
        assert "fit" in choice
    # At least one prospect cares about something (grades are populated).
    assert any(choice["motivations"] for choice in prospects)


def test_legacy_single_league_choices_have_no_motivations():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    initialize_curated_manager_career(conn, "aurora", ROOT_SEED)  # legacy world
    choices = available_recruitment_choices(conn, 1)
    prospects = [c for c in choices if c.get("kind") == "prospect"]
    for choice in prospects:
        # No motivation context on legacy saves — the field is absent or empty.
        assert not choice.get("motivations")
