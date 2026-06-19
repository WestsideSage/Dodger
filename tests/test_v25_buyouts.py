"""V25 The Market — Phase 4: buyouts (incoming refusable, outgoing bids)."""
from __future__ import annotations

import sqlite3
from dataclasses import replace

from dodgeball_sim.career_setup import (
    build_expansion_club,
    generate_expansion_roster,
    initialize_curated_manager_career,
)
from dodgeball_sim.config import ContractConfig
from dodgeball_sim.economy import set_treasury_k, treasury_k
from dodgeball_sim.models import PlayerRatings
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_club_roster,
    load_clubs,
    load_division_map,
    save_club,
)
from dodgeball_sim import transfer_market as tm

_SEED = 20260617
_OPEN = ContractConfig(buyout_interest_threshold=0)  # any interested club bids


def _founding_conn(seed: int = _SEED):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    club = build_expansion_club(
        name="Orphanage Athletic", primary_color="#101010", secondary_color="#FAFAFA",
        venue_name="The Yard", home_region="Eastside", tagline="x",
    )
    roster = generate_expansion_roster(club.club_id, seed)
    initialize_curated_manager_career(
        conn, club.club_id, seed, custom_club=club, custom_roster=roster,
        ruleset_selection="official_foam", world="pyramid",
    )
    conn.commit()
    return conn, club.club_id


def _seed_user_roster(conn, user_club, star_ovr=90):
    """Give the user a priced, contracted roster with one obvious star."""
    club = load_clubs(conn)[user_club]
    roster = load_club_roster(conn, user_club)
    seeded = []
    for i, p in enumerate(roster):
        ovr = star_ovr if i == 0 else 60
        seeded.append(replace(
            p, salary_k=30 if i == 0 else 15, contract_term=2,
            ratings=PlayerRatings(accuracy=ovr, power=ovr, dodge=ovr, catch=ovr),
        ))
    save_club(conn, club, seeded)
    conn.commit()
    return seeded


# --- incoming buyout offers -----------------------------------------------------

def test_incoming_buyout_offers_target_contracted_stars():
    conn, user_club = _founding_conn()
    _seed_user_roster(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    user_tier = load_division_map(conn, season_id)[user_club].tier

    offers = tm.incoming_buyout_offers(conn, season_id, user_club, _SEED, config=_OPEN)
    assert offers, "a contracted star should draw a higher-tier buyout bid"
    top = offers[0]
    assert top.buyer_tier < user_tier and top.fee_k > 0


def test_buyout_interest_threshold_gates_offers():
    conn, user_club = _founding_conn()
    _seed_user_roster(conn, user_club, star_ovr=62)  # modest squad, low pursuit
    season_id = get_state(conn, "active_season_id")
    # Default threshold (70) suppresses bids on an unremarkable roster.
    assert tm.incoming_buyout_offers(conn, season_id, user_club, _SEED) == []


# --- accept / refuse ------------------------------------------------------------

def test_accept_buyout_moves_player_and_credits_treasury():
    conn, user_club = _founding_conn()
    _seed_user_roster(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    offer = tm.incoming_buyout_offers(conn, season_id, user_club, _SEED, config=_OPEN)[0]

    before = treasury_k(conn)
    fee = tm.accept_buyout(conn, user_club, offer)
    assert fee == offer.fee_k
    assert treasury_k(conn) == before + offer.fee_k
    user_ids = {p.id for p in load_club_roster(conn, user_club)}
    buyer_ids = {p.id for p in load_club_roster(conn, offer.buyer_club_id)}
    assert offer.player_id not in user_ids and offer.player_id in buyer_ids


def test_refuse_keeps_player_and_wage():
    conn, user_club = _founding_conn()
    _seed_user_roster(conn, user_club)
    season_id = get_state(conn, "active_season_id")
    offer = tm.incoming_buyout_offers(conn, season_id, user_club, _SEED, config=_OPEN)[0]

    before = {(p.id, p.salary_k) for p in load_club_roster(conn, user_club)}
    # Refusing is simply not accepting — the roster and wages are untouched.
    after = {(p.id, p.salary_k) for p in load_club_roster(conn, user_club)}
    assert offer.player_id in {pid for pid, _ in after}
    assert before == after


# --- outgoing bids --------------------------------------------------------------

def _a_target(conn, user_club, season_id):
    """A contracted player on some other club, priced so it has an asking price."""
    division_map = load_division_map(conn, season_id)
    rosters = load_all_rosters(conn)
    clubs = load_clubs(conn)
    target_club = next(c for c in division_map if c != user_club)
    base = rosters[target_club]
    roster = [replace(p, salary_k=20, contract_term=2) for p in base]
    # Ensure depth above the roster floor so a sale is allowed.
    while len(roster) < 8:
        src = roster[len(roster) % len(base)]
        roster.append(replace(src, id=f"pad_{len(roster)}"))
    save_club(conn, clubs[target_club], roster)
    conn.commit()
    return target_club, roster[0]


def test_outgoing_bid_succeeds_when_meeting_asking_and_affordable():
    conn, user_club = _founding_conn()
    season_id = get_state(conn, "active_season_id")
    target_club, target = _a_target(conn, user_club, season_id)
    set_treasury_k(conn, 5000)
    conn.commit()
    asking = 2 * 20 * 2  # buyout_fee_factor * salary * term
    res = tm.outgoing_bid(conn, user_club, target_club, target.id, bid_k=asking)
    assert res.success and res.asking_k == asking
    assert target.id in {p.id for p in load_club_roster(conn, user_club)}
    assert treasury_k(conn) == 5000 - asking


def test_outgoing_bid_refused_when_underfunded_or_underbid():
    conn, user_club = _founding_conn()
    season_id = get_state(conn, "active_season_id")
    target_club, target = _a_target(conn, user_club, season_id)
    asking = 2 * 20 * 2

    set_treasury_k(conn, 10); conn.commit()
    poor = tm.outgoing_bid(conn, user_club, target_club, target.id, bid_k=asking)
    assert poor.success is False  # rich-club privilege: a broke club can't buy

    set_treasury_k(conn, 5000); conn.commit()
    lowball = tm.outgoing_bid(conn, user_club, target_club, target.id, bid_k=asking - 1)
    assert lowball.success is False  # under the asking price
    assert target.id not in {p.id for p in load_club_roster(conn, user_club)}
