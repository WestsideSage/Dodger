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


def test_records_ratified_payload_is_empty_dict():
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
    assert result == {}


def test_hof_induction_payload_is_empty_dict():
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
    assert result == {}


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


def test_rookie_class_preview_payload_is_empty_dict():
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
    assert result == {}
