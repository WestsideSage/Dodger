"""Phase 1 — manual lineup persists across the season rollover (D1).

The user's manual lineup must survive ``initialize_manager_offseason``: surviving
starters keep their chosen order, departed players (retirements) are dropped, and
any vacated slots are backfilled by best-by-role/OVR. Before the fix the offseason
overwrote the user club's default with raw roster order, silently discarding the
manual lineup and re-introducing the weak-six fielding bug.
"""

from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_build_a_club_career
from dodgeball_sim.lineup import STARTERS_COUNT
from dodgeball_sim.offseason_ceremony import (
    initialize_manager_offseason,
    sign_best_rookie,
    stored_root_seed,
)
from dodgeball_sim.persistence import (
    create_schema,
    load_all_rosters,
    load_clubs,
    load_lineup_default,
    load_season,
    get_state,
    save_lineup_default,
)


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_build_a_club_career(
        conn,
        club_name="Testers FC",
        primary_color="#123456",
        secondary_color="#abcdef",
        venue_name="Test Arena",
        home_region="Testville",
        tagline="We test.",
        root_seed=20260529,
    )
    conn.commit()
    return conn


def test_manual_lineup_survives_offseason_rollover():
    conn = _career_conn()
    player_club_id = get_state(conn, "player_club_id")
    roster = list(load_all_rosters(conn)[player_club_id])

    # A deliberately custom manual order (reverse of roster) that differs from
    # both roster order and the optimized default.
    manual = list(reversed([p.id for p in roster]))
    save_lineup_default(conn, player_club_id, manual)
    conn.commit()

    season = load_season(conn, get_state(conn, "active_season_id"))
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    initialize_manager_offseason(conn, season, clubs, rosters, stored_root_seed(conn))

    new_default = load_lineup_default(conn, player_club_id)
    new_roster_ids = {p.id for p in load_all_rosters(conn)[player_club_id]}

    surviving_manual = [pid for pid in manual if pid in new_roster_ids]
    # Surviving manual picks keep their chosen relative order at the front.
    assert new_default[: len(surviving_manual)] == surviving_manual
    # No departed players linger and no roster member is dropped.
    assert set(new_default) == new_roster_ids


def test_signing_a_rookie_preserves_manual_top_five_and_starts_the_recruit():
    conn = _career_conn()
    player_club_id = get_state(conn, "player_club_id")
    roster = list(load_all_rosters(conn)[player_club_id])

    # Pin a custom manual lineup distinct from roster/optimized order.
    manual = list(reversed([p.id for p in roster]))
    save_lineup_default(conn, player_club_id, manual)

    # A rollover so a rookie/free-agent pool exists to sign from.
    season = load_season(conn, get_state(conn, "active_season_id"))
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    initialize_manager_offseason(conn, season, clubs, rosters, stored_root_seed(conn))
    pre_sign_default = load_lineup_default(conn, player_club_id)

    signed = sign_best_rookie(conn, player_club_id, season_number=1)
    assert signed is not None

    new_default = load_lineup_default(conn, player_club_id)
    # The recruit becomes an active starter (within the fielded six).
    assert signed.id in new_default[:STARTERS_COUNT]
    # The manual top five carry forward into slots 1-5 — signing does NOT reset
    # the lineup to raw roster order.
    assert new_default[:5] == pre_sign_default[:5]
