"""V25 The Market — Phase 5: AI symmetry, transfer ledger, news, roster fortress.

AI clubs resolve their own expiring squads on the same motivation grades; the
tier wage budget forces real churn; league veteran movement is never zero.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace
from types import SimpleNamespace

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings
from dodgeball_sim.motivations import prospect_motivation_profile
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_club_roster,
    load_clubs,
    load_division_map,
    load_free_agents,
    load_news_headlines,
    save_club,
    save_club_prestige,
)
from dodgeball_sim import transfer_market as tm

_SEED = 20260617


def _pyramid_conn(seed: int = _SEED):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _ai_clubs_at_tier(conn, season_id, tier):
    division_map = load_division_map(conn, season_id)
    user = get_state(conn, "player_club_id")
    return [c for c, s in division_map.items() if s.tier == tier and c != user]


def _set_club_roster(conn, club_id, n, ovr, term, salary=20):
    club = load_clubs(conn)[club_id]
    base = load_club_roster(conn, club_id)
    roster = []
    for i in range(n):
        src = base[i % len(base)]
        roster.append(replace(
            src, id=f"{club_id}_v25_{i}", salary_k=salary, contract_term=term,
            ratings=PlayerRatings(accuracy=ovr, power=ovr, dodge=ovr, catch=ovr),
        ))
    save_club(conn, club, roster)
    conn.commit()


def _find_id_with_dealbreaker(motivation, n=600):
    for i in range(n):
        pid = f"seek_{i}"
        if prospect_motivation_profile(SimpleNamespace(player_id=pid)).dealbreaker == motivation:
            return pid
    raise AssertionError(f"no id caring about {motivation}")


def test_ai_transfer_period_resolves_all_expiring_players():
    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    targets = _ai_clubs_at_tier(conn, season_id, tier=2)[:2]
    for club in targets:
        _set_club_roster(conn, club, n=8, ovr=70, term=0)

    tm.run_ai_transfer_period(conn, season_id, _SEED)
    for club in targets:
        # No zombie term-0 players remain: each was re-signed or released.
        assert all(p.contract_term > 0 for p in load_club_roster(conn, club))


def test_wage_budget_forces_release_to_free_agency():
    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    club = _ai_clubs_at_tier(conn, season_id, tier=3)[0]  # D3 budget is tightest
    _set_club_roster(conn, club, n=12, ovr=78, term=0)  # 12 priced -> over budget

    fa_before = len(load_free_agents(conn))
    summary = tm.run_ai_transfer_period(conn, season_id, _SEED)
    assert summary["released"] > 0  # the cap really bites
    assert len(load_free_agents(conn)) > fa_before  # released join the FA pool


def test_transfer_ledger_records_movement_roster_fortress():
    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    for club in _ai_clubs_at_tier(conn, season_id, tier=2)[:2]:
        _set_club_roster(conn, club, n=10, ovr=72, term=0)

    summary = tm.run_ai_transfer_period(conn, season_id, _SEED)
    ledger = tm.load_transfers(conn, season_id)
    assert summary["moved"] > 0 and len(ledger) == summary["moved"]  # movement > 0


def test_notable_veto_release_emits_news():
    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    club = _ai_clubs_at_tier(conn, season_id, tier=2)[0]
    save_club_prestige(conn, club, 1)  # broke-on-prestige -> Contender grade collapses
    conn.commit()

    star_id = _find_id_with_dealbreaker("contender")
    base = load_club_roster(conn, club)
    club_obj = load_clubs(conn)[club]
    # 6 contracted keepers (so must_keep doesn't force the star) + the expiring star.
    keepers = [replace(base[i % len(base)], id=f"{club}_keep_{i}", salary_k=10, contract_term=2)
               for i in range(6)]
    star = Player(
        id=star_id, name="Marquee Star",
        ratings=PlayerRatings(accuracy=88, power=88, dodge=86, catch=86),
        archetype=PlayerArchetype.THROWER, salary_k=40, contract_term=0,
    )
    save_club(conn, club_obj, keepers + [star])
    conn.commit()

    tm.run_ai_transfer_period(conn, season_id, _SEED)
    # The star was vetoed out (Contender dealbreaker) and made the news ticker.
    assert star_id not in {p.id for p in load_club_roster(conn, club)}
    texts = " ".join(h["headline_text"] for h in load_news_headlines(conn, season_id))
    assert "Marquee Star" in texts


def test_ai_resigns_an_affordable_keeper():
    conn = _pyramid_conn()
    season_id = get_state(conn, "active_season_id")
    club = _ai_clubs_at_tier(conn, season_id, tier=1)[0]  # Premier: ample budget
    _set_club_roster(conn, club, n=6, ovr=75, term=0)  # at floor, all affordable

    tm.run_ai_transfer_period(conn, season_id, _SEED)
    roster = load_club_roster(conn, club)
    assert len(roster) == 6  # nobody dropped below the floor
    assert all(p.contract_term == 3 and p.salary_k > 0 for p in roster)  # re-signed
