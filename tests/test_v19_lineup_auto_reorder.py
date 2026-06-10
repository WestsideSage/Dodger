"""V19 Task 8 — the lineup auto-reorder toggle (owner-decided, CFB26 pattern).

The V18 sweeps measured the silent stale-lineup default costing a passive
career 20pp of title share (22.5% engaged vs 2.5% passive — the only
difference was re-seating the six each offseason). The owner's call: keep
manual control AND offer set-and-forget — a toggle, defaulting ON for new
careers, flipped OFF implicitly by a manual lineup save, plus a one-shot
Auto-assign tool that changes the lineup but never the mode.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.lineup import optimize_ai_lineup
from dodgeball_sim.offseason_ceremony import (
    _maintain_user_lineup_for_new_season,
    begin_next_season,
    ensure_ai_offseason_signings,
    finalize_season,
    initialize_manager_offseason,
)
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_lineup_default,
    load_season,
    save_lineup_default,
    set_state,
)
from dodgeball_sim.use_cases import auto_pilot_weeks
from dodgeball_sim.web_status_service import (
    auto_assign_lineup_payload,
    build_roster_payload,
    lineup_auto_reorder_enabled,
    set_lineup_auto_reorder_payload,
    update_manual_lineup_payload,
)

ROOT_SEED = 20260610


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", ROOT_SEED, ruleset_selection="official_foam"
    )
    conn.commit()
    return conn


class TestToggleState:
    def test_new_career_defaults_to_auto_reorder_on(self):
        conn = _career_conn()
        assert get_state(conn, "lineup_auto_reorder") == "1"
        assert lineup_auto_reorder_enabled(conn) is True
        assert build_roster_payload(conn)["lineup_auto_reorder"] is True

    def test_manual_lineup_save_flips_hands_on(self):
        conn = _career_conn()
        roster = load_all_rosters(conn)["aurora"]
        starters = [p.id for p in roster[:6]]
        payload = update_manual_lineup_payload(conn, starters)
        assert payload["lineup_auto_reorder"] is False
        assert lineup_auto_reorder_enabled(conn) is False

    def test_toggle_endpoint_round_trips(self):
        conn = _career_conn()
        assert set_lineup_auto_reorder_payload(conn, False)["lineup_auto_reorder"] is False
        assert lineup_auto_reorder_enabled(conn) is False
        assert set_lineup_auto_reorder_payload(conn, True)["lineup_auto_reorder"] is True
        assert lineup_auto_reorder_enabled(conn) is True

    def test_auto_assign_is_a_tool_not_a_mode_change(self):
        conn = _career_conn()
        set_lineup_auto_reorder_payload(conn, False)
        payload = auto_assign_lineup_payload(conn)
        roster = load_all_rosters(conn)["aurora"]
        assert payload["ordered_player_ids"] == optimize_ai_lineup(roster)
        assert load_lineup_default(conn, "aurora") == optimize_ai_lineup(roster)
        # The one-shot does NOT re-enable set-and-forget.
        assert lineup_auto_reorder_enabled(conn) is False


class TestSeasonRolloverMaintenance:
    def test_auto_reorder_on_reseats_the_six(self):
        conn = _career_conn()
        roster = load_all_rosters(conn)["aurora"]
        # Scramble the saved order so the optimizer has real work to do.
        scrambled = [p.id for p in reversed(roster)]
        save_lineup_default(conn, "aurora", scrambled)
        _maintain_user_lineup_for_new_season(conn)
        assert load_lineup_default(conn, "aurora") == optimize_ai_lineup(roster)
        assert get_state(conn, "offseason_lineup_reordered") == "1"

    def test_hands_off_mode_respects_the_chosen_order(self):
        conn = _career_conn()
        set_lineup_auto_reorder_payload(conn, False)
        roster = load_all_rosters(conn)["aurora"]
        chosen = [p.id for p in reversed(roster)]
        save_lineup_default(conn, "aurora", chosen)
        _maintain_user_lineup_for_new_season(conn)
        assert load_lineup_default(conn, "aurora") == chosen
        assert get_state(conn, "offseason_lineup_reordered") == "0"

    def test_hands_off_mode_still_repairs_departures(self):
        conn = _career_conn()
        set_lineup_auto_reorder_payload(conn, False)
        roster = load_all_rosters(conn)["aurora"]
        chosen = [p.id for p in roster]
        # A retired starter leaves a ghost id at the front of the order.
        save_lineup_default(conn, "aurora", ["ghost_retired_id"] + chosen[1:])
        _maintain_user_lineup_for_new_season(conn)
        repaired = load_lineup_default(conn, "aurora")
        assert "ghost_retired_id" not in repaired
        # The surviving chosen order is preserved as a prefix; the displaced
        # player re-enters by OVR backfill, never silently dropped.
        assert repaired[: len(chosen) - 1] == chosen[1:]
        assert sorted(repaired) == sorted(chosen)

    def test_full_offseason_applies_the_default_reorder(self):
        """End-to-end through the shipping loop: after one season + offseason
        with the default toggle, the next season opens on the optimized six
        (signings included), not the creation order."""
        conn = _career_conn()
        result = auto_pilot_weeks(conn)
        assert result["stop_reason"] in ("season_complete", "already_complete")
        season = load_season(conn, get_state(conn, "active_season_id"))
        clubs = load_clubs(conn)
        rosters = load_all_rosters(conn)
        finalize_season(conn, season, rosters)
        initialize_manager_offseason(conn, season, clubs, rosters, root_seed=ROOT_SEED)
        ensure_ai_offseason_signings(conn)
        cursor = load_career_state_cursor(conn)
        begin_next_season(conn, cursor, clubs)
        final_roster = load_all_rosters(conn)["aurora"]
        assert load_lineup_default(conn, "aurora") == optimize_ai_lineup(final_roster)
