"""V25 The Market — Phase 1 contract foundation tests.

Pure-formula + Player-serialization round-trip coverage. DB-backed settlement /
entry-deal / backfill tests live alongside the later Phase 1 tasks once the
career fixtures are in place.
"""
from dodgeball_sim import contracts
from dodgeball_sim.config import DEFAULT_CONTRACTS as C
from dodgeball_sim.models import Player, PlayerRatings, PlayerArchetype


def _player(salary_k: int = 0, contract_term: int = 1) -> Player:
    return Player(
        id=f"p{salary_k}-{contract_term}",
        name="x",
        ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
        archetype=PlayerArchetype.THROWER,
        salary_k=salary_k,
        contract_term=contract_term,
    )


# --- contracts.py pure formulas -------------------------------------------------

def test_entry_salary_is_ability_blind_and_tier_standard():
    assert contracts.entry_salary_k(tier=3) == C.entry_salary_by_tier[3]
    assert contracts.entry_salary_k(tier=1) == C.entry_salary_by_tier[1]
    # entry deal takes no OVR argument at all — courtship, not money.


def test_entry_term_is_the_standard_default():
    assert contracts.entry_term() == C.entry_term


def test_second_contract_prices_ability_and_tier():
    low = contracts.second_contract_salary_k(ovr=70, tier=3)
    high = contracts.second_contract_salary_k(ovr=90, tier=1)
    assert high > low > 0
    # same OVR costs more in a higher tier.
    assert contracts.second_contract_salary_k(ovr=80, tier=1) > \
        contracts.second_contract_salary_k(ovr=80, tier=3)


def test_second_contract_floors_at_base_for_low_ovr():
    # below the pivot, the per-OVR term is clamped to 0 -> base * tier mult.
    assert contracts.second_contract_salary_k(ovr=40, tier=3) == C.second_base_k


def test_wage_bill_sums_active_roster_salaries():
    roster = [_player(salary_k=10), _player(salary_k=14), _player(salary_k=0)]
    assert contracts.wage_bill_k(roster) == 24


def test_wage_budget_is_tier_derived():
    assert contracts.wage_budget_for_tier(1) > contracts.wage_budget_for_tier(3)


def test_buyout_fee_scales_with_salary_term_and_factor():
    assert contracts.buyout_fee_k(salary_k=20, term_remaining=2) == round(
        C.buyout_fee_factor * 20 * 2
    )


def test_dev_compensation_is_a_modest_fraction_of_fee():
    fee = contracts.buyout_fee_k(salary_k=20, term_remaining=2)
    comp = contracts.dev_compensation_k(salary_k=20, term_remaining=2)
    assert comp == round(C.dev_compensation_fraction * fee)
    assert comp < fee


# --- Player serialization round-trip --------------------------------------------

def test_player_contract_fields_roundtrip_and_default():
    from dodgeball_sim.persistence import _player_to_dict, _player_from_dict

    p = _player(salary_k=18, contract_term=2)
    back = _player_from_dict(_player_to_dict(p))
    assert back.salary_k == 18 and back.contract_term == 2


def test_legacy_player_dict_without_contract_fields_defaults():
    # A pre-V25 blob (no salary_k/contract_term keys) must load, not raise.
    from dodgeball_sim.persistence import _player_from_dict, _player_to_dict

    blob = _player_to_dict(_player())
    del blob["salary_k"]
    del blob["contract_term"]
    back = _player_from_dict(blob)
    assert back.salary_k == 0 and back.contract_term == 1


# --- wage bill in the offseason settlement (DB-backed) --------------------------

import sqlite3
from dataclasses import replace as _replace

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.economy import apply_season_finances, player_wage_bill_k
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_roster,
    load_clubs,
    load_division_map,
    save_club,
)
from dodgeball_sim.season import StandingsRow

_SEED = 20260617


def _legacy_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=_SEED)
    conn.commit()
    return conn


def _pyramid_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _set_salaries(conn: sqlite3.Connection, club_id: str, salaries: list[int]) -> int:
    club = load_clubs(conn)[club_id]
    roster = load_club_roster(conn, club_id)
    new_roster = [
        _replace(p, salary_k=salaries[i]) if i < len(salaries) else p
        for i, p in enumerate(roster)
    ]
    save_club(conn, club, new_roster)
    conn.commit()
    return sum(salaries)


def _division_standings(conn, season_id, club_id, user_rank=1):
    division_map = load_division_map(conn, season_id)
    seat = division_map[club_id]
    clubs = [
        cid for cid, m in division_map.items() if m.division_id == seat.division_id
    ]
    # Put the user club at the requested rank by points order.
    others = [c for c in clubs if c != club_id]
    ordered = others[: user_rank - 1] + [club_id] + others[user_rank - 1 :]
    total = len(ordered)
    return [
        StandingsRow(
            club_id=cid,
            wins=(total - i) ,
            losses=0,
            draws=0,
            elimination_differential=0,
            points=(total - i) * 3,
        )
        for i, cid in enumerate(ordered)
    ]


def test_player_wage_bill_helper_pyramid_vs_legacy():
    pconn = _pyramid_conn()
    total = _set_salaries(pconn, "aurora", [10, 14, 8, 8, 8, 8])
    assert player_wage_bill_k(pconn, "aurora") == total == 56

    lconn = _legacy_conn()
    _set_salaries(lconn, "aurora", [10, 14, 8, 8, 8, 8])
    # Non-pyramid save: the wage bill is gated OFF (byte-identical economics).
    assert player_wage_bill_k(lconn, "aurora") == 0


def test_legacy_finances_ledger_has_no_wage_effect():
    conn = _legacy_conn()
    _set_salaries(conn, "aurora", [10, 14, 8, 8, 8, 8])
    season_id = get_state(conn, "active_season_id")
    standings = [
        StandingsRow(
            club_id=("aurora" if i == 1 else f"rival_{i}"),
            wins=(7 - i),
            losses=0,
            draws=0,
            elimination_differential=0,
            points=(7 - i) * 3,
        )
        for i in range(1, 8)
    ]
    ledger = apply_season_finances(
        conn, season_id=season_id, club_id="aurora", standings=standings
    )
    assert ledger["player_wage_bill_k"] == 0
    # Net unchanged from the pre-V25 formula: payout + bonus - staff payroll.
    assert ledger["net_k"] == (
        ledger["league_payout_k"] + ledger["playoff_bonus_k"] - ledger["staff_payroll_k"]
    )


def test_pyramid_finances_subtracts_wage_bill():
    conn = _pyramid_conn()
    total = _set_salaries(conn, "aurora", [10, 14, 8, 8, 8, 8])
    season_id = get_state(conn, "active_season_id")
    standings = _division_standings(conn, season_id, "aurora", user_rank=1)
    ledger = apply_season_finances(
        conn, season_id=season_id, club_id="aurora", standings=standings
    )
    assert ledger["player_wage_bill_k"] == total == 56
    assert ledger["net_k"] == (
        ledger["league_payout_k"]
        + ledger["playoff_bonus_k"]
        - ledger["staff_payroll_k"]
        - ledger["player_wage_bill_k"]
    )


# --- entry deals at signing + one-time backfill ---------------------------------

def test_new_signing_gets_tier_standard_entry_deal():
    from dodgeball_sim.recruitment import sign_prospect_to_club
    from dodgeball_sim.scouting_center import Prospect
    from dodgeball_sim.persistence import save_prospect_pool

    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    tier = load_division_map(conn, season_id)["aurora"].tier
    prospect = Prospect(
        player_id="v25_rookie",
        class_year=1,
        name="Rook Ie",
        age=18,
        hometown="Harborside",
        hidden_ratings={
            "accuracy": 70, "power": 68, "dodge": 66, "catch": 64, "stamina": 60,
            "tactical_iq": 55, "catch_courage": 55, "throw_selection_iq": 55,
            "conditioning_curve": 55,
        },
        hidden_trajectory="normal",
        hidden_traits=[],
        public_archetype_guess="thrower",
        public_ratings_band={"accuracy": (60, 80)},
    )
    save_prospect_pool(conn, [prospect])
    conn.commit()
    signed = sign_prospect_to_club(conn, prospect, "aurora", season_num=1)
    assert signed.salary_k == contracts.entry_salary_k(tier)
    assert signed.contract_term == contracts.entry_term()
    # Ability-blind: a much better prospect signs the SAME entry salary at a tier.


def test_backfill_prices_existing_roster_once_and_spreads_terms():
    from dodgeball_sim.offseason_ceremony import _seed_v25_contracts, stored_root_seed
    from dodgeball_sim.persistence import load_all_rosters

    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    root_seed = stored_root_seed(conn)

    _seed_v25_contracts(conn, season_id, root_seed)
    roster = load_club_roster(conn, "aurora")
    assert roster and all(p.salary_k > 0 for p in roster)
    # Terms spread across the league cohort (1..entry_term), not one season.
    all_terms = {
        p.contract_term for r in load_all_rosters(conn).values() for p in r
    }
    assert len(all_terms) >= 2 and all_terms <= set(range(1, contracts.entry_term() + 1))

    before = [(p.id, p.salary_k, p.contract_term) for p in roster]
    # Idempotent on already-priced players: a second pass leaves them unchanged.
    _seed_v25_contracts(conn, season_id, root_seed)
    after = [(p.id, p.salary_k, p.contract_term) for p in load_club_roster(conn, "aurora")]
    assert after == before


def test_seed_self_heals_players_that_joined_unpriced():
    # The squeeze-dodge fix: a player who joined a roster OUTSIDE the prospect
    # path (free-agent signing, AI depth fill) sits at salary 0 until the next
    # pricing pass catches him — he must not stay a permanent $0 wage.
    from dataclasses import replace as _r
    from dodgeball_sim.offseason_ceremony import _seed_v25_contracts, stored_root_seed

    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    root_seed = stored_root_seed(conn)
    _seed_v25_contracts(conn, season_id, root_seed)  # prices the founders

    club = load_clubs(conn)["aurora"]
    roster = load_club_roster(conn, "aurora")
    intruder = _replace(roster[0], id="fa_intruder", salary_k=0, contract_term=1)
    save_club(conn, club, roster + [intruder])
    conn.commit()

    _seed_v25_contracts(conn, season_id, root_seed)  # self-heal pass
    healed = {p.id: p for p in load_club_roster(conn, "aurora")}
    assert healed["fa_intruder"].salary_k > 0
    # Priced incumbents untouched by the heal pass.
    assert all(p.salary_k > 0 for p in healed.values())


def test_backfill_skips_legacy_world():
    from dodgeball_sim.offseason_ceremony import _seed_v25_contracts, stored_root_seed

    conn = _legacy_conn()
    season_id = get_state(conn, "active_season_id")
    assert _seed_v25_contracts(conn, season_id, stored_root_seed(conn)) is None
    assert all(p.salary_k == 0 for p in load_club_roster(conn, "aurora"))
