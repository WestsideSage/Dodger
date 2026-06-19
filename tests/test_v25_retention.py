"""V25 The Market — Phase 2: contract aging, expiry, and retention (re-sign).

Retention is recruiting's mirror: the same V24 motivation grades, applied to a
rostered player vs his own club, decide whether he re-signs.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_roster,
    load_clubs,
    save_club,
)

_SEED = 20260617


def _pyramid_conn(seed: int = _SEED) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _legacy_conn(seed: int = _SEED) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", seed)
    conn.commit()
    return conn


def _price_roster(conn, club_id, salary_k=20, term=3):
    club = load_clubs(conn)[club_id]
    roster = [
        replace(p, salary_k=salary_k, contract_term=term)
        for p in load_club_roster(conn, club_id)
    ]
    save_club(conn, club, roster)
    conn.commit()
    return roster


# --- Task 2.1: term decrement ---------------------------------------------------

def test_contract_terms_decrement_each_offseason():
    from dodgeball_sim.offseason_ceremony import _decrement_contract_terms

    conn = _pyramid_conn()
    _price_roster(conn, "aurora", salary_k=20, term=3)
    season_id = get_state(conn, "active_season_id")

    _decrement_contract_terms(conn, season_id)
    assert all(p.contract_term == 2 for p in load_club_roster(conn, "aurora"))

    # Idempotent within a season (its own season-scoped guard).
    _decrement_contract_terms(conn, season_id)
    assert all(p.contract_term == 2 for p in load_club_roster(conn, "aurora"))


def test_contract_term_floors_at_zero_expiring():
    from dodgeball_sim.offseason_ceremony import _decrement_contract_terms

    conn = _pyramid_conn()
    _price_roster(conn, "aurora", salary_k=20, term=1)
    season_id = get_state(conn, "active_season_id")
    _decrement_contract_terms(conn, season_id)
    roster = load_club_roster(conn, "aurora")
    assert all(p.contract_term == 0 for p in roster)  # expiring, never negative


def test_decrement_skips_legacy_world():
    from dodgeball_sim.offseason_ceremony import _decrement_contract_terms

    conn = _legacy_conn()
    _price_roster(conn, "aurora", salary_k=20, term=3)
    _decrement_contract_terms(conn, get_state(conn, "active_season_id"))
    assert all(p.contract_term == 3 for p in load_club_roster(conn, "aurora"))


# --- Task 2.2: expiring cohort --------------------------------------------------

def test_expiring_players_are_those_at_term_zero():
    from dataclasses import replace as _r
    from dodgeball_sim.transfer_market import expiring_players

    conn = _pyramid_conn()
    club = load_clubs(conn)["aurora"]
    roster = load_club_roster(conn, "aurora")
    # First two expiring (term 0), rest under contract.
    mixed = [
        _r(p, salary_k=20, contract_term=(0 if i < 2 else 2))
        for i, p in enumerate(roster)
    ]
    save_club(conn, club, mixed)
    conn.commit()
    expiring = expiring_players(conn, "aurora")
    assert len(expiring) == 2
    assert all(p.contract_term <= 0 for p in expiring)


# --- Task 2.3: retention (re-sign) via motivation grades ------------------------

def test_resign_required_salary_bends_with_fit():
    from dodgeball_sim.transfer_market import resign_required_salary_k

    loyal = resign_required_salary_k(100, fit=1.0)
    neutral = resign_required_salary_k(100, fit=0.5)
    mercenary = resign_required_salary_k(100, fit=0.0)
    assert loyal < neutral < mercenary
    assert loyal < 100 < mercenary  # loyalty discounts; disloyalty demands a premium


def test_retention_decision_grades_flip_outcome_at_equal_money():
    from dodgeball_sim.transfer_market import retention_decision

    # Same offer, same ask — only fit differs.
    signed, _, _ = retention_decision(offer_salary_k=100, expected_salary_k=100, fit=0.9, veto=False)
    walked, _, _ = retention_decision(offer_salary_k=100, expected_salary_k=100, fit=0.1, veto=False)
    assert signed is True and walked is False


def test_retention_dealbreaker_veto_walks_at_any_price():
    from dodgeball_sim.transfer_market import retention_decision

    signed, _, receipt = retention_decision(
        offer_salary_k=10_000, expected_salary_k=50, fit=0.9, veto=True, dealbreaker="contender"
    )
    assert signed is False and "Contender" in receipt


def _find_id_with_dealbreaker(motivation: str, n: int = 600) -> str:
    from types import SimpleNamespace
    from dodgeball_sim.motivations import prospect_motivation_profile

    for i in range(n):
        pid = f"seek_{i}"
        if prospect_motivation_profile(SimpleNamespace(player_id=pid)).dealbreaker == motivation:
            return pid
    raise AssertionError(f"no synthetic id caring about {motivation} as dealbreaker in {n}")


def test_evaluate_retention_contender_grade_flips_a_real_resign():
    # A star whose DEALBREAKER is Contender re-signs at a proud club and walks
    # at a broke one — same player, same generous offer; only the grade differs.
    from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings
    from dodgeball_sim.persistence import save_club_prestige
    from dodgeball_sim.transfer_market import evaluate_retention

    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    pid = _find_id_with_dealbreaker("contender")
    star = Player(
        id=pid, name="Star Player",
        ratings=PlayerRatings(accuracy=85, power=85, dodge=80, catch=82),
        archetype=PlayerArchetype.THROWER, salary_k=30, contract_term=0,
    )
    generous = 10_000  # well above any fit-adjusted ask

    save_club_prestige(conn, "aurora", 90)
    conn.commit()
    strong = evaluate_retention(conn, "aurora", star, generous, season_id)

    save_club_prestige(conn, "aurora", 1)
    conn.commit()
    weak = evaluate_retention(conn, "aurora", star, generous, season_id)

    assert strong.re_signed and not strong.veto
    assert weak.veto and not weak.re_signed  # Contender collapses → dealbreaker veto

