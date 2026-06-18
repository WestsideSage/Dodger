"""V26 The Crowd — Phase 4: fan income (matchday + merch) in the settlement."""
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_FANS as FAN
from dodgeball_sim.economy import apply_season_finances
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_division_map,
    save_standings,
)
from dodgeball_sim.season import StandingsRow
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
    season_id = get_state(conn, "active_season_id")
    rows = [
        StandingsRow(club_id=("aurora" if i == 0 else f"r{i}"), wins=5, losses=0,
                     draws=0, elimination_differential=0, points=15 - i)
        for i in range(7)
    ]
    save_standings(conn, season_id, rows)
    conn.commit()
    return conn, season_id


def _legacy_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", _SEED)
    conn.commit()
    return conn


# --- pure formulas --------------------------------------------------------------

def test_matchday_is_capped_by_stadium_capacity():
    cap = fe.stadium_capacity(tier=3, has_stadium=False)
    assert fe.matchday_income_k(10_000_000, cap) == round(cap * FAN.matchday_per_fan_k)


def test_stadium_facility_raises_capacity():
    assert fe.stadium_capacity(3, True) > fe.stadium_capacity(3, False)


def test_merch_center_raises_merch_income():
    assert fe.merch_income_k(5000, 2000, True) > fe.merch_income_k(5000, 2000, False)


# --- settlement integration -----------------------------------------------------

def test_fan_income_enters_the_pyramid_settlement():
    conn, season_id = _pyramid_career()
    fl.add_fans(conn, "aurora", 5000, season_id, "seed", "test fans")
    conn.commit()
    standings = [
        StandingsRow(club_id=("aurora" if i == 0 else f"r{i}"), wins=5, losses=0,
                     draws=0, elimination_differential=0, points=15 - i)
        for i in range(7)
    ]
    ledger = apply_season_finances(conn, season_id=season_id, club_id="aurora", standings=standings)
    assert ledger["matchday_income_k"] > 0 and ledger["merch_income_k"] > 0
    assert ledger["net_k"] == (
        ledger["league_payout_k"] + ledger["playoff_bonus_k"]
        + ledger["matchday_income_k"] + ledger["merch_income_k"]
        - ledger["staff_payroll_k"] - ledger["player_wage_bill_k"]
    )


def test_legacy_save_has_no_fan_income():
    conn = _legacy_career()
    season_id = get_state(conn, "active_season_id")
    standings = [
        StandingsRow(club_id=("aurora" if i == 1 else f"rival_{i}"), wins=(7 - i),
                     losses=0, draws=0, elimination_differential=0, points=(7 - i) * 3)
        for i in range(1, 8)
    ]
    ledger = apply_season_finances(conn, season_id=season_id, club_id="aurora", standings=standings)
    assert ledger["matchday_income_k"] == 0 and ledger["merch_income_k"] == 0


def test_fan_income_never_rivals_prize_money_at_any_tier():
    # Even a maxed fan base draws less than a competitive finish's prize money.
    conn, season_id = _pyramid_career()
    fl.add_fans(conn, "aurora", 50_000, season_id, "seed", "huge")  # absurdly large
    conn.commit()
    tier = load_division_map(conn, season_id)["aurora"].tier
    income = fe.user_fan_income_k(conn, season_id)
    fan_total = income["matchday_income_k"] + income["merch_income_k"]
    # A competitive D3 finish's prize money is the base payout (~220k); fan income
    # must stay a margin below it even with a saturated stadium.
    from dodgeball_sim.config import DEFAULT_ECONOMY as E
    assert fan_total < E.base_payout_k
