"""V25 The Market — Phase 3: uphill poaching of the user's expiring stars.

Higher-tier money hunts your expiring players; motivations break ties; every
departure carries a data-derived receipt and a modest development credit.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace

from dodgeball_sim.career_setup import (
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_division_map,
    save_club,
)
from dodgeball_sim import transfer_market as tm

_SEED = 20260617


def _founding_conn(seed: int = _SEED):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    club = build_expansion_club(
        name="Orphanage Athletic",
        primary_color="#101010",
        secondary_color="#FAFAFA",
        venue_name="The Yard",
        home_region="Eastside",
        tagline="Founded from nothing",
    )
    roster = generate_expansion_roster(club.club_id, seed)
    initialize_curated_manager_career(
        conn, club.club_id, seed,
        custom_club=club, custom_roster=roster,
        ruleset_selection="official_foam", world="pyramid",
    )
    conn.commit()
    return conn, club.club_id


def _star(pid="star_x", ovr=85):
    return Player(
        id=pid, name="Star",
        ratings=PlayerRatings(accuracy=ovr, power=ovr, dodge=ovr, catch=ovr),
        archetype=PlayerArchetype.THROWER, salary_k=20, contract_term=0,
    )


def _suitor(club_id="rival", offer=100, interest=80, tier=1):
    return tm.PoachSuitor(
        club_id=club_id, club_name=club_id.title(), tier=tier,
        offer_salary_k=offer, interest=interest, receipt="x",
    )


# --- poach_suitors (DB reader) --------------------------------------------------

def test_poach_suitors_are_uphill_only():
    conn, user_club = _founding_conn()
    season_id = get_state(conn, "active_season_id")
    user_tier = load_division_map(conn, season_id)[user_club].tier
    suitors = tm.poach_suitors(conn, season_id, _star(), user_club, root_seed=_SEED)
    assert suitors, "a D3 star should draw higher-tier interest"
    assert all(s.tier < user_tier for s in suitors)  # strictly uphill


def test_poach_suitors_gated_by_wage_headroom():
    conn, user_club = _founding_conn()
    season_id = get_state(conn, "active_season_id")
    division_map = load_division_map(conn, season_id)
    clubs = load_clubs(conn)
    # Pick a tier-1 rival and bury it over its wage budget.
    broke = next(cid for cid, seat in division_map.items() if seat.tier == 1)
    roster = load_all_rosters(conn).get(broke, [])
    save_club(conn, clubs[broke], [replace(p, salary_k=90) for p in roster])
    conn.commit()
    suitor_ids = {s.club_id for s in tm.poach_suitors(conn, season_id, _star(), user_club, _SEED)}
    assert broke not in suitor_ids            # capped out, no headroom
    assert any(division_map[c].tier == 1 for c in suitor_ids)  # solvent tier-1s still bid


# --- resolve_poaching (pure) ----------------------------------------------------

def test_resolve_poaching_grades_break_ties_at_equal_money():
    common = dict(player_id="p", expected_salary_k=100, dealbreaker_letter="C",
                  suitors=[_suitor(offer=100)], salary_k=20, term_remaining=2)
    loyal = tm.resolve_poaching(user_offer_k=100, fit=0.95, veto=False, **common)
    mercenary = tm.resolve_poaching(user_offer_k=100, fit=0.05, veto=False, **common)
    assert loyal.stayed is True            # loyalty buffer holds him at matched money
    assert mercenary.stayed is False       # low fit leaves for the rival
    assert mercenary.winner_club_id == "rival"


def test_resolve_poaching_veto_always_leaves():
    res = tm.resolve_poaching(
        player_id="p", user_offer_k=10_000, expected_salary_k=50, fit=0.9, veto=True,
        dealbreaker_letter="F", suitors=[_suitor(offer=40)], salary_k=20, term_remaining=2,
    )
    assert res.stayed is False and res.winner_club_id == "rival"


def test_poach_departure_credits_dev_compensation_and_receipt():
    res = tm.resolve_poaching(
        player_id="p", user_offer_k=50, expected_salary_k=100, fit=0.2, veto=False,
        dealbreaker_letter="D", suitors=[_suitor(offer=120)], salary_k=20, term_remaining=2,
    )
    assert res.stayed is False
    assert res.dev_compensation_k > 0
    assert "Poached by" in res.receipt and "×" in res.receipt


def test_no_suitor_keeps_player_with_no_compensation():
    res = tm.resolve_poaching(
        player_id="p", user_offer_k=50, expected_salary_k=100, fit=0.2, veto=False,
        dealbreaker_letter="D", suitors=[], salary_k=20, term_remaining=2,
    )
    assert res.winner_club_id is None and res.dev_compensation_k == 0
