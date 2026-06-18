"""V26 The Crowd — Phase 3: player personal followings from award moments."""
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_FANS as FAN
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_roster,
    save_signature_moment,
)
from dodgeball_sim import fan_economy as fe
from dodgeball_sim import fan_ledger as fl

_SEED = 20260617


def _pyramid_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def test_mvp_earns_a_following_a_benchwarmer_does_not():
    conn, season_id = _pyramid_career()
    roster = load_club_roster(conn, "aurora")
    star, benchwarmer = roster[0], roster[-1]
    save_signature_moment(conn, "m1", star.id, season_id, None, "mvp", "Season MVP")
    conn.commit()

    fe.award_season_followers(conn, season_id)
    assert fl.player_followers(conn, star.id) == FAN.followers_mvp
    assert fl.player_followers(conn, benchwarmer.id) == 0  # no moment, no following


def test_award_moments_earn_a_smaller_following_with_receipts():
    conn, season_id = _pyramid_career()
    p = load_club_roster(conn, "aurora")[1]
    save_signature_moment(conn, "m2", p.id, season_id, None, "best_thrower", "Best Thrower")
    conn.commit()

    fe.award_season_followers(conn, season_id)
    assert fl.player_followers(conn, p.id) == FAN.followers_milestone
    receipts = fl.load_fan_receipts(conn, entity_type="player", entity_id=p.id)
    assert receipts and sum(r["delta"] for r in receipts) == fl.player_followers(conn, p.id)
    assert "Best Thrower" in receipts[0]["receipt"]


def test_followings_are_idempotent_and_user_only():
    conn, season_id = _pyramid_career()
    star = load_club_roster(conn, "aurora")[0]
    save_signature_moment(conn, "m3", star.id, season_id, None, "mvp", "MVP")
    # An AI club player with an MVP gains nothing — followings are user-program.
    ai_roster = next(
        load_club_roster(conn, cid)
        for cid in __import__("dodgeball_sim.persistence", fromlist=["load_clubs"]).load_clubs(conn)
        if cid != "aurora"
    )
    save_signature_moment(conn, "m4", ai_roster[0].id, season_id, None, "mvp", "MVP")
    conn.commit()

    fe.award_season_followers(conn, season_id)
    first = fl.player_followers(conn, star.id)
    assert first == FAN.followers_mvp
    assert fl.player_followers(conn, ai_roster[0].id) == 0  # AI player: no following
    fe.award_season_followers(conn, season_id)  # idempotent
    assert fl.player_followers(conn, star.id) == first
