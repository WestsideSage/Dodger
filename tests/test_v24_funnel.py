"""V24 The Board Phase 4 — funnel stages + persistent focus list.

Per docs/specs/2026-06-12-v24-the-board-spec.md (Phase 4): the slot verbs are
gated by a funnel — Open -> Shortlist -> Top 3 -> Verbal. Contact requires a
prospect be on your (persistent) focus list; Visit is reserved for your top
targets; Scout is always allowed (it's how you evaluate). Verbal is a
high-interest, leading, non-vetoed target.

These pin the pure funnel layer and the focus-list persistence round-trip.
"""
from __future__ import annotations

import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import get_state, load_prospect_pool
from dodgeball_sim.recruiting_office import (
    FUNNEL_STAGES,
    apply_recruiting_action,
    funnel_allows,
    funnel_stage,
    load_focus_list,
    toggle_focus,
)

ROOT_SEED = 20260612


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


class TestFunnelStage:
    def test_open_until_shortlisted(self):
        assert funnel_stage(on_focus_list=False, interest=90, focus_rank=None, vetoed=False) == "OPEN"

    def test_shortlist_when_focused(self):
        assert funnel_stage(on_focus_list=True, interest=10, focus_rank=5, vetoed=False) == "SHORTLIST"

    def test_top3_when_among_leaders(self):
        assert funnel_stage(on_focus_list=True, interest=40, focus_rank=1, vetoed=False) == "TOP3"

    def test_verbal_when_high_interest_and_clear(self):
        assert funnel_stage(on_focus_list=True, interest=85, focus_rank=0, vetoed=False) == "VERBAL"

    def test_veto_blocks_verbal(self):
        # A dealbreaker veto can never reach Verbal, no matter the interest.
        stage = funnel_stage(on_focus_list=True, interest=99, focus_rank=0, vetoed=True)
        assert stage != "VERBAL"

    def test_all_stages_known(self):
        assert FUNNEL_STAGES == ("OPEN", "SHORTLIST", "TOP3", "VERBAL")


class TestVerbGating:
    def test_scout_always_contact_needs_shortlist_visit_needs_top3(self):
        assert funnel_allows("OPEN") == (False, False)      # only Scout
        assert funnel_allows("SHORTLIST") == (True, False)   # +Contact
        assert funnel_allows("TOP3") == (True, True)         # +Visit
        assert funnel_allows("VERBAL") == (True, True)


class TestFocusListPersistence:
    def test_toggle_round_trips(self):
        conn = _conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED, world="pyramid")
        assert load_focus_list(conn) == []
        assert toggle_focus(conn, "prospect_1_003") is True   # added
        assert "prospect_1_003" in load_focus_list(conn)
        assert toggle_focus(conn, "prospect_1_003") is False  # removed
        assert "prospect_1_003" not in load_focus_list(conn)


class TestVerbGatingEnforced:
    def test_contact_is_gated_behind_focus_on_pyramid(self):
        conn = _conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED, world="pyramid")
        season_id = get_state(conn, "active_season_id")
        pool = load_prospect_pool(conn, 1)
        assert pool, "pyramid career should seed a class-1 prospect pool"
        pid = pool[0].player_id

        # Contact before shortlisting is refused (the server backstop).
        with pytest.raises(ValueError):
            apply_recruiting_action(
                conn, prospect_id=pid, action="contact", season_id=season_id,
                player_club_id="aurora", root_seed=ROOT_SEED, history=[],
            )
        # Shortlist him, then Contact is allowed.
        toggle_focus(conn, pid)
        result = apply_recruiting_action(
            conn, prospect_id=pid, action="contact", season_id=season_id,
            player_club_id="aurora", root_seed=ROOT_SEED, history=[],
        )
        assert result
