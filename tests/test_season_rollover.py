"""Coach identity must survive season rollover.

Playtest finding (Task 4): a user ran S1 on Aggressive, won the division,
opened S2 W1, and the coach policy had silently reset to defaults
(Approach.MIXED / Balanced). This eroded save identity. These tests pin
the policy carry-over against ``begin_next_season`` — the canonical
rollover entry point in the web path.
"""
from __future__ import annotations

import dataclasses
import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.models import (
    Approach,
    CatchPosture,
    CoachPolicy,
    OpeningRushCommit,
    OpeningRushTarget,
    TargetFocus,
)
from dodgeball_sim.offseason_ceremony import begin_next_season
from dodgeball_sim.persistence import (
    create_schema,
    load_club_roster,
    load_clubs,
    save_career_state_cursor,
    save_club,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_schema(connection)
    initialize_manager_career(connection, "aurora", root_seed=20260528)
    return connection


@pytest.fixture
def scripted_aggressive_policy() -> CoachPolicy:
    """A non-default policy that touches every CoachPolicy field.

    Using all five fields rather than just ``approach`` lets us catch
    regressions where the rollover preserves the headline tactic but
    silently resets the rest of the dial.
    """
    return CoachPolicy(
        approach=Approach.AGGRESSIVE,
        target_focus=TargetFocus.THEIR_STARS,
        catch_posture=CatchPosture.GO_FOR_CATCHES,
        rush_commit=OpeningRushCommit.ALL_IN,
        rush_target=OpeningRushTarget.STRONGEST_SIDE,
    )


def _set_player_club_policy(conn: sqlite3.Connection, policy: CoachPolicy) -> None:
    clubs = load_clubs(conn)
    club = clubs["aurora"]
    updated = dataclasses.replace(club, coach_policy=policy)
    save_club(conn, updated, load_club_roster(conn, "aurora"))
    conn.commit()


def _advance_to_next_season(conn: sqlite3.Connection) -> None:
    cursor = CareerStateCursor(
        state=CareerState.NEXT_SEASON_READY,
        season_number=1,
        week=15,
        offseason_beat_index=9,
    )
    save_career_state_cursor(conn, cursor)
    begin_next_season(conn, cursor, load_clubs(conn))


def test_coach_policy_approach_persists_across_season_rollover(
    conn, scripted_aggressive_policy
):
    _set_player_club_policy(conn, scripted_aggressive_policy)
    assert load_clubs(conn)["aurora"].coach_policy.approach == Approach.AGGRESSIVE

    _advance_to_next_season(conn)

    after = load_clubs(conn)["aurora"].coach_policy
    assert after.approach == Approach.AGGRESSIVE, (
        "Coach approach must carry over across season rollover"
    )


def test_coach_policy_all_fields_persist_across_season_rollover(
    conn, scripted_aggressive_policy
):
    _set_player_club_policy(conn, scripted_aggressive_policy)
    before = load_clubs(conn)["aurora"].coach_policy

    _advance_to_next_season(conn)

    after = load_clubs(conn)["aurora"].coach_policy
    assert after.approach == before.approach
    assert after.target_focus == before.target_focus
    assert after.catch_posture == before.catch_posture
    assert after.rush_commit == before.rush_commit
    assert after.rush_target == before.rush_target
