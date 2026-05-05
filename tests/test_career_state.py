import sqlite3

import pytest

from dodgeball_sim.career_state import (
    CareerState,
    CareerStateCursor,
    InvalidTransitionError,
    advance,
    can_transition,
)
from dodgeball_sim.persistence import (
    create_schema,
    load_career_state_cursor,
    save_career_state_cursor,
)


def test_cursor_defaults_to_splash_state():
    cursor = CareerStateCursor(state=CareerState.SPLASH)
    assert cursor.season_number == 0
    assert cursor.week == 0
    assert cursor.match_id is None


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (CareerState.SPLASH, CareerState.SEASON_ACTIVE_PRE_MATCH),
        (CareerState.SEASON_ACTIVE_PRE_MATCH, CareerState.SEASON_ACTIVE_IN_MATCH),
        (CareerState.SEASON_ACTIVE_IN_MATCH, CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING),
        (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_ACTIVE_PRE_MATCH),
        (CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
        (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT),
        (CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING),
        (CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING, CareerState.NEXT_SEASON_READY),
        (CareerState.NEXT_SEASON_READY, CareerState.SEASON_ACTIVE_PRE_MATCH),
    ],
)
def test_allowed_transitions(from_state, to_state):
    assert can_transition(from_state, to_state)
    assert advance(CareerStateCursor(state=from_state), to_state).state == to_state


def test_disallowed_transition_raises():
    cursor = CareerStateCursor(state=CareerState.SPLASH)
    with pytest.raises(InvalidTransitionError):
        advance(cursor, CareerState.SEASON_ACTIVE_IN_MATCH)


def test_advance_applies_payload_updates():
    cursor = CareerStateCursor(state=CareerState.SEASON_ACTIVE_PRE_MATCH, week=3)
    new_cursor = advance(
        cursor,
        CareerState.SEASON_ACTIVE_IN_MATCH,
        match_id="s1_w3_aurora_vs_lunar",
    )
    assert new_cursor.match_id == "s1_w3_aurora_vs_lunar"
    assert new_cursor.week == 3


def test_advance_match_report_to_pre_match_advances_week():
    cursor = CareerStateCursor(
        state=CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING,
        week=3,
    )
    new_cursor = advance(
        cursor,
        CareerState.SEASON_ACTIVE_PRE_MATCH,
        week=cursor.week + 1,
        match_id=None,
    )
    assert new_cursor.week == 4
    assert new_cursor.match_id is None


def test_career_state_cursor_roundtrip():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)

    cursor = CareerStateCursor(
        state=CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING,
        season_number=2,
        week=7,
        offseason_beat_index=0,
        match_id="s2_w7_aurora_vs_lunar",
    )
    save_career_state_cursor(conn, cursor)
    assert load_career_state_cursor(conn) == cursor


def test_load_career_state_cursor_returns_splash_when_absent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    loaded = load_career_state_cursor(conn)
    assert loaded.state == CareerState.SPLASH
    assert loaded.season_number == 0


def test_load_career_state_cursor_recovers_from_malformed_json():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.execute(
        "INSERT INTO dynasty_state (key, value) VALUES (?, ?)",
        ("career_state_cursor", "{not-json"),
    )

    loaded = load_career_state_cursor(conn)

    assert loaded == CareerStateCursor(state=CareerState.SPLASH)


def test_load_career_state_cursor_recovers_from_invalid_state_value():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.execute(
        "INSERT INTO dynasty_state (key, value) VALUES (?, ?)",
        ("career_state_cursor", '{"state":"bogus","season_number":1,"week":1,"offseason_beat_index":0}'),
    )

    loaded = load_career_state_cursor(conn)

    assert loaded == CareerStateCursor(state=CareerState.SPLASH)


def test_load_career_state_cursor_clamps_negative_numbers_and_excessive_beat():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.execute(
        "INSERT INTO dynasty_state (key, value) VALUES (?, ?)",
        (
            "career_state_cursor",
            '{"state":"season_complete_offseason_beat","season_number":-3,"week":-8,"offseason_beat_index":999,"match_id":"m1"}',
        ),
    )

    loaded = load_career_state_cursor(conn)

    assert loaded.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
    assert loaded.season_number == 0
    assert loaded.week == 0
    assert loaded.offseason_beat_index == 9
    assert loaded.match_id == "m1"
