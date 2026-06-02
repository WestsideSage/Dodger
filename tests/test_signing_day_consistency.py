"""BUG #5 — Signing Day must not contradict itself.

A new-player playtest saw the Signing-Day surface report "2/3 used" while also
saying "You signed 1" with a roster cap of "10/12". The three figures came from
different stores: a standalone ``offseason_draft_signed_count`` counter, a
card-derived ``my_signing`` count (from ``recruitment_signing`` rows the
offseason flow never writes), and the live roster length.

The fix makes the signed-slot count a single source of truth — the guarded
``offseason_draft_signed_count`` counter, which equals the players actually added
to the roster this offseason. These tests pin, at the PAYLOAD level (the frontend
has no test runner), that:

* after K offseason signings the three numbers agree:
  ``signed_count == K``, ``remaining_signings == limit - K``,
  ``roster_size == baseline + K``; and
* the counter is faithful — pressing "sign best available" against an empty pool
  signs nobody and therefore does NOT advance the counter.
"""
import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.offseason_ceremony import finalize_season, initialize_manager_offseason
from dodgeball_sim.offseason_presentation import load_active_beats
from dodgeball_sim.offseason_service import recruit_offseason_payload
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_season,
    save_career_state_cursor,
    save_free_agents,
)
from dodgeball_sim.server import app, get_db


def _enter_recruitment_state(conn: sqlite3.Connection) -> None:
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    finalize_season(conn, season, rosters)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260426)
    recruitment_index = load_active_beats(conn).index("recruitment")
    save_career_state_cursor(
        conn,
        CareerStateCursor(
            state=CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            season_number=1,
            week=0,
            offseason_beat_index=recruitment_index,
        ),
    )
    conn.commit()


def test_signing_day_counts_agree_across_used_signed_and_cap():
    """signed_count, remaining_signings, and roster_size stay mutually consistent."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    _enter_recruitment_state(conn)
    baseline_roster = len(load_all_rosters(conn)["aurora"])

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        beat = client.get("/api/offseason/beat").json()
        limit = beat["payload"]["signing_limit"]

        for k in (1, 2):
            prospect_id = beat["payload"]["available_prospects"][0]["prospect_id"]
            beat = client.post(
                "/api/offseason/recruit", json={"prospect_id": prospect_id}
            ).json()
            payload = beat["payload"]

            # The three figures that contradicted each other in the playtest must
            # now agree, all anchored to the real roster delta of k.
            assert payload["signed_count"] == k
            assert payload["remaining_signings"] == limit - k
            assert payload["roster_size"] == baseline_roster + k
            # Internal identity: remaining is exactly limit - used (single source).
            assert (
                payload["remaining_signings"]
                == payload["signing_limit"] - payload["signed_count"]
            )
            # The roster the cap counts is the same roster the engine persisted.
            assert payload["roster_size"] == len(load_all_rosters(conn)["aurora"])
    finally:
        app.dependency_overrides.clear()


def test_signing_counter_does_not_advance_when_pool_is_empty():
    """Faithfulness: 'sign best available' with nothing to sign must not count.

    Previously the counter incremented unconditionally, so pressing sign against
    an exhausted pool inflated "used" above the real number of roster additions —
    exactly the drift that made "used" disagree with "you signed".
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    _enter_recruitment_state(conn)

    season_number = 1
    class_year = season_number  # available_recruitment_choices uses season_number
    # Exhaust every signee: clear the prospect pool and the free-agent pool so
    # sign_best_rookie has nobody to sign.
    conn.execute("DELETE FROM prospect_pool WHERE class_year = ?", (class_year,))
    save_free_agents(conn, [], f"season_{season_number + 1}")
    conn.commit()

    roster_before = len(load_all_rosters(conn)["aurora"])
    signed_before = int(get_state(conn, "offseason_draft_signed_count") or "0")

    # "Sign best available" (prospect_id omitted) against the empty pool.
    result = recruit_offseason_payload(conn, prospect_id=None)

    assert result["signed_player"] is None
    payload = result["payload"]
    # Counter unchanged → "used" still equals the real roster delta (zero here).
    assert payload["signed_count"] == signed_before
    assert int(get_state(conn, "offseason_draft_signed_count") or "0") == signed_before
    assert payload["roster_size"] == roster_before
    assert payload["remaining_signings"] == payload["signing_limit"] - payload["signed_count"]
