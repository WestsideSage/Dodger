from __future__ import annotations

import json
import sqlite3

import pytest

from dodgeball_sim.persistence import create_schema, load_clubs


def test_load_clubs_migrates_legacy_coach_policy_to_defaults():
    """Pre-Plan-C saves must load without raising; legacy policy silently migrates to v2 defaults."""
    from dodgeball_sim.models import CoachPolicy

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.execute(
        """
        INSERT INTO clubs (
            club_id, name, colors, home_region, founded_year, coach_policy_json,
            primary_color, secondary_color, venue_name, tagline
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy",
            "Legacy Club",
            "red/white",
            "North",
            2020,
            json.dumps(
                {
                    "target_stars": 0.7,
                    "target_ball_holder": 0.5,
                    "risk_tolerance": 0.5,
                    "sync_throws": 0.2,
                    "rush_frequency": 0.5,
                    "rush_proximity": 0.5,
                    "tempo": 0.5,
                    "catch_bias": 0.5,
                }
            ),
            "",
            "",
            "",
            "",
        ),
    )
    conn.execute(
        "INSERT INTO club_rosters (club_id, players_json) VALUES (?, ?)",
        ("legacy", "[]"),
    )

    clubs = load_clubs(conn)
    assert clubs["legacy"].coach_policy == CoachPolicy()
