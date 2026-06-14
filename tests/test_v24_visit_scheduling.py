"""V24 The Board Phase 4 (remainder) — visits scheduled against real home fixtures.

Per docs/specs/2026-06-12-v24-the-board-spec.md (Phase 4): "Visits scheduled
against the user's real home fixtures (scheduler join)." A campus visit is hosted
at one of your upcoming HOME games; when no home fixtures remain this season the
visit is honestly refused (you cannot host a visit with no home game to host it
at). The binding is persisted so the board can show where each recruit visits.

These pin the pure fixture-selection helper and the integration through
``apply_recruiting_action`` on a pyramid save.
"""
from __future__ import annotations

import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import get_state, load_prospect_pool, load_season
from dodgeball_sim.recruiting_office import (
    apply_recruiting_action,
    load_visit_fixtures,
    select_visit_fixture,
    toggle_focus,
)
from dodgeball_sim.scheduler import ScheduledMatch

ROOT_SEED = 20260612


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _m(week: int, home: str, away: str) -> ScheduledMatch:
    return ScheduledMatch(
        match_id=f"s_w{week:02d}_{home}_vs_{away}",
        season_id="s",
        week=week,
        home_club_id=home,
        away_club_id=away,
    )


class TestSelectVisitFixture:
    def test_picks_earliest_upcoming_home_fixture(self):
        matches = [
            _m(1, "rivals", "aurora"),   # away — not a home game
            _m(3, "aurora", "rivals"),   # home, upcoming
            _m(5, "aurora", "others"),   # home, later
        ]
        fixture = select_visit_fixture(
            matches, player_club_id="aurora", current_week=2, bound_match_ids=set()
        )
        assert fixture is not None
        assert fixture.week == 3
        assert fixture.home_club_id == "aurora"

    def test_skips_past_weeks(self):
        matches = [_m(1, "aurora", "rivals"), _m(4, "aurora", "others")]
        fixture = select_visit_fixture(
            matches, player_club_id="aurora", current_week=3, bound_match_ids=set()
        )
        assert fixture is not None and fixture.week == 4

    def test_none_when_no_home_fixtures_remain(self):
        # All remaining games are away — nothing to host a visit at.
        matches = [_m(5, "rivals", "aurora"), _m(6, "others", "aurora")]
        fixture = select_visit_fixture(
            matches, player_club_id="aurora", current_week=1, bound_match_ids=set()
        )
        assert fixture is None


class TestVisitBinding:
    def test_visit_schedules_against_a_real_home_fixture(self):
        conn = _conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED, world="pyramid")
        season_id = get_state(conn, "active_season_id")
        club_id = get_state(conn, "player_club_id")

        pool = load_prospect_pool(conn, 1)
        assert pool, "pyramid career should seed a class-1 prospect pool"
        pid = pool[0].player_id

        # Visit requires the prospect be a top focus target (Phase 4 funnel).
        toggle_focus(conn, pid)
        result = apply_recruiting_action(
            conn, prospect_id=pid, action="visit", season_id=season_id,
            player_club_id=club_id, root_seed=ROOT_SEED, history=[],
        )

        fixture = result.get("visit_fixture")
        assert fixture is not None, "a visit must report the home fixture hosting it"
        assert fixture["home_club_id"] == club_id

        # The binding is persisted and recoverable for the board.
        bound = load_visit_fixtures(conn)
        assert pid in bound
        assert bound[pid]["match_id"] == fixture["match_id"]

        # The bound fixture is a real scheduled match for the user club.
        season = load_season(conn, season_id)
        real_ids = {m.match_id for m in season.scheduled_matches if m.home_club_id == club_id}
        assert fixture["match_id"] in real_ids
