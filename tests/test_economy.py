"""V22 Phase 2 — the club treasury and season finances.

Owner (2026-06-11): a light financial-management layer (Teamfight Manager
cited) — one treasury, league payouts by finish, annual staff payroll, user
club only. These tests pin the formulas, the offseason settlement (once and
only once), the calibration (mid-table solvent, basement squeezed but never
spiraling), and the surfaces that disclose the books.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_ECONOMY
from dodgeball_sim.economy import (
    apply_season_finances,
    format_k,
    hiring_frozen,
    season_income_k,
    set_treasury_k,
    staff_payroll_k,
    staff_salary_k,
    treasury_k,
)
from dodgeball_sim.persistence import create_schema, get_state
from dodgeball_sim.season import StandingsRow


def _career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260611)
    conn.commit()
    return conn


def _row(club_id: str, points: int) -> StandingsRow:
    return StandingsRow(
        club_id=club_id,
        wins=points // 3,
        losses=0,
        draws=0,
        elimination_differential=0,
        points=points,
    )


def _standings_with_user_rank(rank: int, total: int = 7) -> list[StandingsRow]:
    rows = []
    for i in range(1, total + 1):
        club = "aurora" if i == rank else f"rival_{i}"
        rows.append(_row(club, points=(total - i) * 3))
    return rows


def test_salary_formula_prices_quality_with_a_floor():
    assert staff_salary_k(74, 68) == round(0.75 * 74 + 0.25 * 68) - 25
    assert staff_salary_k(99, 99) == 74
    # Floor: a journeyman can never be cheaper than the floor.
    assert staff_salary_k(30, 30) == DEFAULT_ECONOMY.salary_floor_k


def test_income_table_rewards_finish_and_playoffs():
    champ = season_income_k(rank=1, total_clubs=7, playoff_result="champion")
    mid = season_income_k(rank=4, total_clubs=7, playoff_result=None)
    tail = season_income_k(rank=7, total_clubs=7, playoff_result=None)
    assert champ["league_payout_k"] == 340 and champ["playoff_bonus_k"] == 140
    assert mid["league_payout_k"] == 280 and mid["playoff_bonus_k"] == 0
    assert tail["league_payout_k"] == 220 and tail["playoff_bonus_k"] == 0


def test_calibration_mid_table_solvent_basement_squeezed_not_spiraled():
    """The economy's design targets, pinned: default staff payroll is roughly
    break-even at mid-table, clearly funded by a title, and a slow squeeze —
    never a cliff — at the bottom."""
    conn = _career_conn()
    payroll = staff_payroll_k(conn)
    champ = season_income_k(rank=1, total_clubs=7, playoff_result="champion")
    mid = season_income_k(rank=4, total_clubs=7, playoff_result=None)
    tail = season_income_k(rank=7, total_clubs=7, playoff_result=None)

    assert sum(mid.values()) - payroll >= -10, "mid-table must be ~break-even"
    assert sum(champ.values()) - payroll >= 150, "a title must fund upgrades"
    tail_net = sum(tail.values()) - payroll
    assert -90 <= tail_net < 0, (
        f"basement must squeeze, not spiral (net {tail_net}k/season)"
    )


def test_apply_season_finances_settles_once_and_moves_the_treasury():
    conn = _career_conn()
    season_id = get_state(conn, "active_season_id")
    opening = treasury_k(conn)
    payroll = staff_payroll_k(conn)
    standings = _standings_with_user_rank(rank=4)

    ledger = apply_season_finances(
        conn, season_id=season_id, club_id="aurora", standings=standings
    )

    assert ledger["rank"] == 4
    assert ledger["league_payout_k"] == 280
    assert ledger["staff_payroll_k"] == payroll
    assert ledger["net_k"] == 280 - payroll
    assert ledger["closing_treasury_k"] == opening + ledger["net_k"]
    assert treasury_k(conn) == ledger["closing_treasury_k"]

    # Idempotent: a second call returns the same books and moves nothing.
    again = apply_season_finances(
        conn, season_id=season_id, club_id="aurora", standings=standings
    )
    assert again == ledger
    assert treasury_k(conn) == ledger["closing_treasury_k"]


def test_hiring_freezes_while_negative_and_legacy_saves_default():
    conn = _career_conn()
    assert hiring_frozen(conn) is False
    set_treasury_k(conn, -40)
    assert hiring_frozen(conn) is True

    # Legacy save (no treasury key): defaults to the takeover seed, no crash.
    legacy = sqlite3.connect(":memory:", check_same_thread=False)
    legacy.row_factory = sqlite3.Row
    create_schema(legacy)
    assert treasury_k(legacy) == DEFAULT_ECONOMY.takeover_treasury_k


def test_offseason_attaches_finances_to_the_recap_beat():
    """End to end through the real pipeline: finalize → initialize offseason →
    the recap beat carries this season's settled books."""
    from dodgeball_sim.offseason_ceremony import (
        finalize_season,
        initialize_manager_offseason,
    )
    from dodgeball_sim.persistence import (
        load_all_rosters,
        load_clubs,
        load_season,
    )
    from dodgeball_sim.server import _build_beat_payload

    conn = _career_conn()
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    # A real finished season always has standings; this fixture skipped the
    # matches, so persist a final table before the offseason settles the books.
    from dodgeball_sim.persistence import load_standings, save_standings

    save_standings(conn, season_id, _standings_with_user_rank(rank=4, total=len(clubs)))
    conn.commit()
    finalize_season(conn, season, rosters)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=20260611)

    payload = _build_beat_payload(
        "recap",
        awards=[],
        clubs=clubs,
        rosters=rosters,
        standings=load_standings(conn, season_id),
        ret_rows=[],
        season=season,
        season_outcome=None,
        next_preview=None,
        signed_player_id="",
        player_club_id="aurora",
        conn=conn,
    )
    finances = payload["finances"]
    assert finances["season_id"] == season_id
    assert finances["staff_payroll_k"] == staff_payroll_k(conn)
    assert finances["closing_treasury_k"] == treasury_k(conn)
    assert "user program only" in finances["rules"]


def test_created_club_opens_books_with_budget_minus_payroll(tmp_path):
    import sqlite3 as sq

    from dodgeball_sim.save_service import (
        build_from_scratch_save,
        starting_prospects_payload,
    )

    seed = 4242
    ids = [p["player_id"] for p in starting_prospects_payload(seed)["prospects"]][:6]
    result = build_from_scratch_save(tmp_path, {
        "save_name": "books",
        "club_name": "Books FC",
        "city": "Ledger",
        "colors": "green/black",
        "coach_name": "Coach",
        "coach_backstory": "Builder",
        "roster_player_ids": ids,
        "root_seed": seed,
    })
    conn = sq.connect(result["path"])
    conn.row_factory = sq.Row
    try:
        opening = treasury_k(conn)
        payroll = staff_payroll_k(conn)
    finally:
        conn.close()
    assert opening == DEFAULT_ECONOMY.starting_budget_k - payroll


def test_format_k_renders_thousands_and_millions():
    assert format_k(420) == "$420k"
    assert format_k(-56) == "-$56k"
    assert format_k(1250) == "$1.25M"
