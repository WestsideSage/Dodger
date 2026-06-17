"""V25 The Market — full-stack offseason-service integration for the Transfer
Period beat. Drives the REAL service (get-beat -> action -> advance -> commit)
across two seasons until the user's contracts start expiring.

Heavier than the unit tests (it plays two real seasons on auto-pilot), but it is
the one gate proving the beat is reachable and commits through the live service.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import (
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.offseason_service import (
    OffseasonError,
    advance_offseason_beat_payload,
    begin_next_season_payload,
    get_offseason_beat_payload,
    recruit_offseason_payload,
    transfer_action_payload,
)
from dodgeball_sim.persistence import create_schema, get_state, load_club_roster
from dodgeball_sim.use_cases import auto_pilot_weeks


def _founding_conn(seed=20260617):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    club = build_expansion_club(
        name="Integration FC", primary_color="#111", secondary_color="#EEE",
        venue_name="Hall", home_region="Place", tagline="t",
    )
    roster = generate_expansion_roster(club.club_id, seed)
    initialize_curated_manager_career(
        conn, club.club_id, seed, custom_club=club, custom_roster=roster,
        ruleset_selection="official_foam", world="pyramid",
    )
    conn.commit()
    return conn, club.club_id


def _walk_to_transfer_or_end(conn):
    """Advance offseason beats; if the transfer beat appears, stop on it and
    return its payload, else walk to next_season_ready and return None."""
    for _ in range(24):
        payload = get_offseason_beat_payload(conn)
        if payload.get("key") == "transfer_period":
            return payload
        st = payload.get("state")
        if st == "next_season_ready":
            return None
        if st == "season_complete_recruitment_pending":
            recruit_offseason_payload(conn, prospect_id="skip")
            continue
        try:
            advance_offseason_beat_payload(conn)
        except OffseasonError:
            return None
    return None


def _finish_offseason(conn):
    for _ in range(24):
        payload = get_offseason_beat_payload(conn)
        st = payload.get("state")
        if st == "next_season_ready":
            break
        if st == "season_complete_recruitment_pending":
            recruit_offseason_payload(conn, prospect_id="skip")
            continue
        try:
            advance_offseason_beat_payload(conn)
        except OffseasonError:
            break
    begin_next_season_payload(conn)


def test_transfer_beat_reachable_and_commits_through_the_service():
    conn, user = _founding_conn()

    # Season 1: play + roll the offseason forward (no expiring players yet).
    auto_pilot_weeks(conn, max_weeks=None)
    assert _walk_to_transfer_or_end(conn) is None  # nothing to transfer in S1
    _finish_offseason(conn)

    # Season 2: contracts have ticked down — the Transfer Period should appear.
    auto_pilot_weeks(conn, max_weeks=None)
    beat = _walk_to_transfer_or_end(conn)
    assert beat is not None and beat["key"] == "transfer_period"
    payload = beat["payload"]
    assert payload["committed"] is False
    assert payload["expiring"], "season 2 should have at least one expiring player"

    # Exercise a real action through the service, then advance (commit).
    first = payload["expiring"][0]["player_id"]
    updated = transfer_action_payload(conn, "release", first)
    assert any(r["player_id"] == first and r["decision"] == "release"
               for r in updated["payload"]["expiring"])

    advance_offseason_beat_payload(conn)  # commit-on-advance
    assert get_state(conn, "v25_user_transfer_committed_for") == get_state(conn, "active_season_id")
    # Roster stays legal (floor guard) and the season can still roll on.
    assert len(load_club_roster(conn, user)) >= 6
    _finish_offseason(conn)
