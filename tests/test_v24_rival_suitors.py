"""V24 The Board Phase 5 — visible rival suitors + interest race.

Per docs/specs/2026-06-12-v24-the-board-spec.md (Phase 5): named rival suitors
per focused prospect with a relative interest/lead, surfaced in-season; early
leads are defensible (leading interest compounds modestly).

These pin the deterministic pure core (rival pursuit + lead computation) and the
momentum rule (more weeks remaining → a bigger compounding bump while leading).
The DB-level wiring + determinism fence ride in the integration test below.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import get_state, load_prospect_pool
from dodgeball_sim.prospect_market import (
    RivalSuitor,
    build_market_signal,
    derive_club_pursuit,
    leading_momentum_bonus,
)
from dodgeball_sim.recruiting_office import compute_market_signals, toggle_focus

ROOT_SEED = 20260612


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


class TestDeriveClubPursuit:
    def test_is_deterministic(self):
        a = derive_club_pursuit(public_high_band=88, tier=1, jitter=0.3)
        b = derive_club_pursuit(public_high_band=88, tier=1, jitter=0.3)
        assert a == b

    def test_top_tier_chases_upside_harder(self):
        # A Premier (tier 1) club pursues a high-ceiling prospect harder than a
        # District (tier 3) club at identical talent + jitter.
        premier = derive_club_pursuit(public_high_band=92, tier=1, jitter=0.5)
        district = derive_club_pursuit(public_high_band=92, tier=3, jitter=0.5)
        assert premier > district

    def test_bounded_0_100(self):
        assert 0 <= derive_club_pursuit(public_high_band=99, tier=1, jitter=1.0) <= 100
        assert 0 <= derive_club_pursuit(public_high_band=40, tier=3, jitter=0.0) <= 100


class TestBuildMarketSignal:
    def _rivals(self):
        return [
            RivalSuitor(club_id="north", club_name="Northgate", tier=1, interest=70, receipt="r"),
            RivalSuitor(club_id="south", club_name="Southbank", tier=2, interest=55, receipt="r"),
        ]

    def test_user_leads_when_interest_tops_rivals(self):
        sig = build_market_signal(user_interest=75, rivals=self._rivals())
        assert sig.leader == "user"
        assert sig.top_rival_interest == 70
        assert sig.user_lead == 5

    def test_rival_leads_when_ahead(self):
        sig = build_market_signal(user_interest=60, rivals=self._rivals())
        assert sig.leader == "north"
        assert sig.user_lead == -10

    def test_no_rivals_user_leads_uncontested(self):
        sig = build_market_signal(user_interest=10, rivals=[])
        assert sig.leader == "user"
        assert sig.top_rival_interest == 0


class TestLeadingMomentum:
    def test_more_weeks_remaining_compounds_more(self):
        early = leading_momentum_bonus(weeks_remaining=10, leading=True)
        late = leading_momentum_bonus(weeks_remaining=2, leading=True)
        assert early > late > 0

    def test_no_momentum_when_trailing(self):
        assert leading_momentum_bonus(weeks_remaining=10, leading=False) == 0


class TestMarketSignalsIntegration:
    def test_focused_prospect_gets_named_rivals_with_receipts(self):
        conn = _conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED, world="pyramid")
        season_id = get_state(conn, "active_season_id")
        club_id = get_state(conn, "player_club_id")
        pool = load_prospect_pool(conn, 1)
        pid = pool[0].player_id
        toggle_focus(conn, pid)

        signals = compute_market_signals(conn, season_id, club_id, prospect_ids=[pid])
        assert pid in signals
        sig = signals[pid]
        # Rivals are other clubs (never the user), each with a receipt.
        for rival in sig["rivals"]:
            assert rival["club_id"] != club_id
            assert rival["receipt"]
        # Deterministic: recompute yields the identical signal.
        again = compute_market_signals(conn, season_id, club_id, prospect_ids=[pid])
        assert again[pid] == sig


def _lead_prospect(conn, season_id, club_id):
    """Focus a prospect the user can genuinely lead and seed an interest just
    above his strongest rival, with clamp headroom so momentum stays visible.
    Momentum only rewards HOLDING a lead, so the scenario must be a winnable one."""
    import json

    from dodgeball_sim.persistence import set_state

    pool = sorted(load_prospect_pool(conn, 1), key=lambda p: p.public_ratings_band["ovr"][1])
    for prospect in pool[:15]:  # lowest ceilings → weakest, leadable rivals
        toggle_focus(conn, prospect.player_id)
        sig = compute_market_signals(conn, season_id, club_id, prospect_ids=[prospect.player_id])
        top = sig[prospect.player_id]["top_rival_interest"]
        if top <= 60:  # leadable with clamp headroom for +contact +momentum
            seed = top + 6
            set_state(
                conn,
                "prospect_recruitment_actions_json",
                json.dumps({prospect.player_id: {"scouted": True, "contacted": True, "interest": seed}}),
            )
            return prospect.player_id
        toggle_focus(conn, prospect.player_id)  # unfocus and try the next
    raise AssertionError("no leadable prospect found in the lowest-ceiling slice")


class TestMomentumDefensibility:
    def _interest_after_contact_at_week(self, week: int) -> int:
        conn = _conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED, world="pyramid")
        season_id = get_state(conn, "active_season_id")
        club_id = get_state(conn, "player_club_id")
        pid = _lead_prospect(conn, season_id, club_id)

        # Advance the career cursor to the chosen week.
        from dodgeball_sim.career_state import CareerState, CareerStateCursor
        from dodgeball_sim.persistence import load_career_state_cursor, save_career_state_cursor

        cur = load_career_state_cursor(conn)
        save_career_state_cursor(
            conn, CareerStateCursor(state=cur.state, season_number=cur.season_number, week=week)
        )

        result = apply_recruiting_action_local(conn, pid, season_id, club_id)
        return int(result["interest_after"])

    def test_early_lead_beats_late_entry_at_equal_effort(self):
        early = self._interest_after_contact_at_week(1)
        late = self._interest_after_contact_at_week(12)
        # One identical contact, applied while leading: earlier (more weeks left)
        # compounds harder, so it ends with strictly more interest.
        assert early > late


def apply_recruiting_action_local(conn, pid, season_id, club_id):
    from dodgeball_sim.recruiting_office import apply_recruiting_action

    return apply_recruiting_action(
        conn, prospect_id=pid, action="contact", season_id=season_id,
        player_club_id=club_id, root_seed=ROOT_SEED, history=[],
    )
