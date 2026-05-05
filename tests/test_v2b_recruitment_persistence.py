from __future__ import annotations

import sqlite3

from dodgeball_sim.persistence import (
    CURRENT_SCHEMA_VERSION,
    create_schema,
    get_schema_version,
    load_club_recruitment_profiles,
    load_recruitment_board,
    load_recruitment_offers,
    load_recruitment_round,
    load_recruitment_signings,
    load_prospect_market_signals,
    save_club_recruitment_profile,
    save_prospect_market_signal,
    save_recruitment_board,
    save_recruitment_offers,
    save_recruitment_round,
    save_recruitment_signings,
)
from dodgeball_sim.recruitment_domain import (
    RecruitmentBoardRow,
    RecruitmentOffer,
    RecruitmentProfile,
    RecruitmentSigning,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def test_schema_version_is_11():
    assert CURRENT_SCHEMA_VERSION == 13


def test_create_schema_creates_v2b_recruitment_tables():
    conn = _conn()
    assert get_schema_version(conn) == 13

    expected_tables = {
        "club_recruitment_profile",
        "recruitment_board",
        "recruitment_round",
        "recruitment_offer",
        "recruitment_signing",
        "prospect_market_signal",
    }
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {row["name"] for row in rows}
    assert not (expected_tables - table_names)


def test_save_and_load_club_recruitment_profile():
    conn = _conn()
    profile = RecruitmentProfile(
        club_id="aurora",
        archetype_priorities={"Sharpshooter": 0.8, "Enforcer": 0.2},
        risk_tolerance=0.4,
        prestige=0.7,
        playing_time_pitch=0.6,
        evaluation_quality=0.9,
    )

    save_club_recruitment_profile(conn, profile)
    loaded = load_club_recruitment_profiles(conn)

    assert loaded["aurora"] == profile


def test_save_and_load_recruitment_board_rows():
    conn = _conn()
    rows = [
        RecruitmentBoardRow("aurora", "p1", 1, 80.0, 10.0, 7.0, 97.0, "need and fit"),
        RecruitmentBoardRow("aurora", "p2", 2, 75.0, 4.0, 5.0, 84.0, "public fit"),
    ]

    save_recruitment_board(conn, "season_1", rows)
    loaded = load_recruitment_board(conn, "season_1", "aurora")

    assert loaded == tuple(rows)


def test_save_and_load_prepared_recruitment_round_and_offers_idempotent():
    conn = _conn()
    offers = [
        RecruitmentOffer("season_1", 1, "aurora", "p1", 95.0, "ai", 8.0, 0.7, 0.6, 0.12, "need"),
        RecruitmentOffer("season_1", 1, "lunar", "p2", 90.0, "ai", 7.0, 0.5, 0.8, 0.21, "fit"),
    ]

    save_recruitment_round(conn, "season_1", 1, "prepared", {"prepared_offer_count": 2})
    save_recruitment_offers(conn, offers)
    save_recruitment_round(conn, "season_1", 1, "prepared", {"prepared_offer_count": 2})
    save_recruitment_offers(conn, offers)

    round_row = load_recruitment_round(conn, "season_1", 1)
    loaded_offers = load_recruitment_offers(conn, "season_1", 1)

    assert round_row == {"season_id": "season_1", "round_number": 1, "status": "prepared", "payload": {"prepared_offer_count": 2}}
    assert loaded_offers == tuple(offers)


def test_save_and_load_recruitment_signings_and_market_signals():
    conn = _conn()
    signing = RecruitmentSigning("season_1", 1, "aurora", "p1", "ai", 95.0, "club need")

    save_recruitment_signings(conn, [signing])
    save_recruitment_signings(conn, [signing])
    save_prospect_market_signal(conn, "season_1", "p1", {"risk": "high", "clubs": ["aurora"]})

    assert load_recruitment_signings(conn, "season_1") == (signing,)
    assert load_prospect_market_signals(conn, "season_1") == {"p1": {"risk": "high", "clubs": ["aurora"]}}
