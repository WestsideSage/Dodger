"""Tests that /api/offseason/beat returns a `payload` dict with the right top-level keys."""
from __future__ import annotations

import sqlite3

import pytest
from dodgeball_sim.server import _build_beat_payload
from dodgeball_sim.persistence import create_schema


def _empty_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.commit()
    return conn


def test_awards_payload_has_awards_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "awards",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "awards" in result
    assert isinstance(result["awards"], list)


def test_retirements_payload_has_retirees_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "retirements",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "retirees" in result
    assert isinstance(result["retirees"], list)


def test_retiree_career_length_includes_prior_seasons():
    """Playtest 3 F-10: a curated veteran seeded with `seasons_played_prior`
    must show their FULL career length on the farewell card, not just the
    recorded sim seasons ("3 seasons" on a 33-year-old read as a mislabel)."""
    from dodgeball_sim.persistence import save_player_career_stats

    conn = _empty_conn()
    save_player_career_stats(
        conn,
        "vet_1",
        {
            "player_id": "vet_1",
            "player_name": "Yuki Rodriguez",
            "seasons_played": 3,
            "seasons_played_prior": 8,
            "total_eliminations": 120,
            "championships": 2,
        },
    )
    conn.commit()
    result = _build_beat_payload(
        "retirements",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[
            {
                "player_id": "vet_1",
                "player_name": "Yuki Rodriguez",
                "club_id": "club_x",
                "age": 33,
                "overall": 58,
                "reason": "age_decline",
            }
        ],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    (retiree,) = result["retirees"]
    assert retiree["seasons_played"] == 3  # recorded-only stays recorded-only
    assert retiree["career_seasons"] == 11  # biography includes the prior


def test_development_payload_itemizes_training_credit():
    """Playtest 3 F-7: the disclosed +0.2/week training credit must have
    visible accounting — the dev beat reports weeks run and OVR banked using
    the same helper the growth model spends."""
    from dodgeball_sim.career_setup import initialize_curated_manager_career
    from dodgeball_sim.persistence import (
        get_state,
        load_season,
        save_weekly_command_plan,
    )

    conn = _empty_conn()
    initialize_curated_manager_career(conn, "aurora", 20260611)
    season_id = get_state(conn, "active_season_id")
    for week in (1, 2, 5):
        save_weekly_command_plan(conn, {
            "season_id": season_id, "week": week, "player_club_id": "aurora",
            "intent": "Balanced",
            "department_orders": {"focus_department": "training"},
        })
    conn.commit()

    result = _build_beat_payload(
        "development",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=load_season(conn, season_id),
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        player_club_id="aurora",
        conn=conn,
    )
    credit = result["training_credit"]
    assert credit["weeks"] == 3
    assert credit["credited_weeks"] == 3
    assert credit["credit_ovr"] == pytest.approx(0.6)


def test_recap_payload_has_standings_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "recap",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "standings" in result
    assert isinstance(result["standings"], list)


def test_recruitment_payload_has_player_signing_key():
    conn = _empty_conn()
    result = _build_beat_payload(
        "recruitment",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "player_signing" in result
    assert "other_signings" in result


def test_schedule_reveal_payload_has_fixtures_list():
    conn = _empty_conn()
    result = _build_beat_payload(
        "schedule_reveal",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "fixtures" in result
    assert isinstance(result["fixtures"], list)


def test_records_ratified_payload_has_records_key():
    conn = _empty_conn()
    result = _build_beat_payload(
        "records_ratified",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "records" in result
    assert isinstance(result["records"], list)


def test_hof_induction_payload_has_inductees_key():
    conn = _empty_conn()
    result = _build_beat_payload(
        "hof_induction",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "inductees" in result
    assert isinstance(result["inductees"], list)


def test_development_payload_has_players_key():
    conn = _empty_conn()
    result = _build_beat_payload(
        "development",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "players" in result
    assert result["players"] == []


def test_rookie_class_preview_payload_has_structured_keys():
    conn = _empty_conn()
    result = _build_beat_payload(
        "rookie_class_preview",
        awards=[],
        clubs={},
        rosters={},
        standings=[],
        ret_rows=[],
        season=None,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        conn=conn,
    )
    assert "class_size" in result
    assert "top_prospects" in result
    assert "free_agents" in result
    assert "archetypes" in result
    assert "storylines" in result
    assert result["class_size"] == 0
    assert result["archetypes"] == []
    assert result["storylines"] == []
