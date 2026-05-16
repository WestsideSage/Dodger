from __future__ import annotations

import sqlite3

from dodgeball_sim.ai_program_manager import build_ai_weekly_plan, choose_ai_intent
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema, load_all_rosters, load_clubs
from dodgeball_sim.season import StandingsRow


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


def test_ai_intent_shifts_with_visible_competitive_context():
    front_runner = StandingsRow("northwood", wins=4, losses=0, draws=0, elimination_differential=8, points=12)
    chasing = StandingsRow("northwood", wins=1, losses=3, draws=0, elimination_differential=-4, points=3)

    assert choose_ai_intent(front_runner, week=5, total_weeks=5) == "Prepare For Playoffs"
    assert choose_ai_intent(chasing, week=4, total_weeks=5) == "Develop Youth"


def test_ai_weekly_plan_contains_real_tactics_and_playable_lineup():
    conn = _career_conn()
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    plan = build_ai_weekly_plan(
        season_id="season_1",
        week=1,
        club=clubs["northwood"],
        roster=rosters["northwood"],
        standings_row=StandingsRow("northwood", wins=0, losses=0, draws=0, elimination_differential=0, points=0),
        total_weeks=5,
    )

    assert plan["player_club_id"] == "northwood"
    assert plan["intent"] in {"Balanced", "Win Now", "Develop Youth", "Preserve Health", "Prepare For Playoffs"}
    assert len(plan["lineup"]["player_ids"]) == 6
    assert set(plan["tactics"]) >= {"target_stars", "risk_tolerance", "tempo"}
