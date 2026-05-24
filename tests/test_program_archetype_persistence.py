from __future__ import annotations

import sqlite3
import pytest

from dodgeball_sim.persistence import (
    create_schema,
    load_clubs,
    save_club,
    save_program_trajectory,
    load_program_trajectories,
    classify_club_archetype,
)
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.league import Club


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_program_archetype_defaults_and_roundtrip():
    conn = _career_conn()
    clubs = load_clubs(conn)
    
    # Assert that all curated clubs were loaded and backfilled deterministically
    assert "aurora" in clubs
    # Aurora is the user club, so it defaults to Balanced Rebuild
    assert clubs["aurora"].program_archetype == "Balanced Rebuild"
    
    # Let's verify other clubs have deterministic archetypes
    assert any(c.program_archetype != "Balanced Rebuild" for c in clubs.values())

    # Roundtrip save/load
    club = clubs["aurora"]
    modified_club = Club(
        club_id=club.club_id,
        name=club.name,
        colors=club.colors,
        home_region=club.home_region,
        founded_year=club.founded_year,
        coach_policy=club.coach_policy,
        primary_color=club.primary_color,
        secondary_color=club.secondary_color,
        venue_name=club.venue_name,
        tagline=club.tagline,
        program_archetype="Contender",
    )
    save_club(conn, modified_club, [])
    
    reloaded = load_clubs(conn)
    assert reloaded["aurora"].program_archetype == "Contender"


def test_program_trajectory_roundtrip():
    conn = _career_conn()
    traj = {
        "club_id": "aurora",
        "season_id": "season_1",
        "archetype": "Balanced Rebuild",
        "dominant_intent": "Balanced",
        "record_w": 5,
        "record_l": 3,
        "record_d": 2,
        "top_dev_archetype": "thrower",
        "recruiting_class_strength": "A",
        "notes": {"rebuild_progress": 0.5},
    }
    save_program_trajectory(conn, traj)

    trajectories = load_program_trajectories(conn, "aurora")
    assert len(trajectories) == 1
    assert trajectories[0]["club_id"] == "aurora"
    assert trajectories[0]["season_id"] == "season_1"
    assert trajectories[0]["archetype"] == "Balanced Rebuild"
    assert trajectories[0]["dominant_intent"] == "Balanced"
    assert trajectories[0]["record_w"] == 5
    assert trajectories[0]["record_l"] == 3
    assert trajectories[0]["record_d"] == 2
    assert trajectories[0]["top_dev_archetype"] == "thrower"
    assert trajectories[0]["recruiting_class_strength"] == "A"
    assert trajectories[0]["notes"] == {"rebuild_progress": 0.5}


def test_classify_backfill_archetype():
    # Empty players
    assert classify_club_archetype("test_club", False, []) == "Balanced Rebuild"
    
    # Aging Veterans (average age >= 26.5)
    veterans = [{"age": 30}, {"age": 28}, {"age": 27}]
    assert classify_club_archetype("test_club", False, veterans) == "Aging Veterans"
    
    # Contender (high overall >= 67.0)
    contenders = [
        {"age": 24, "ratings": {"accuracy": 70, "power": 70, "dodge": 70, "catch": 70, "stamina": 70}},
        {"age": 25, "ratings": {"accuracy": 80, "power": 80, "dodge": 80, "catch": 80, "stamina": 80}},
    ]
    assert classify_club_archetype("test_club", False, contenders) == "Contender"
    
    # Development Factory (young <= 22.5 and high potential >= 60)
    prospects = [
        {"age": 19, "ratings": {}, "traits": {"potential": 75}},
        {"age": 20, "ratings": {}, "traits": {"potential": 80}},
    ]
    assert classify_club_archetype("test_club", False, prospects) == "Development Factory"
