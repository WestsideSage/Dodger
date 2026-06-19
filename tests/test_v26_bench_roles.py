"""V26 The Crowd — Phase 5: bench roles (Mentor / Analyst / Ambassador)."""
import sqlite3
from dataclasses import replace

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_club_roster,
    load_clubs,
    save_club,
    save_lineup_default,
)
from dodgeball_sim import bench_roles as br
from dodgeball_sim import fan_ledger as fl

_SEED = 20260617


def _career_with_bench():
    """A pyramid career whose user roster has 6 starters + 3 bench (a youngster
    starter to mentor, and high-trait bench veterans to hold roles)."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    club = load_clubs(conn)["aurora"]
    base = load_club_roster(conn, "aurora")

    def vet(pid, tiq):
        return Player(
            id=pid, name=pid, age=30,
            ratings=PlayerRatings(accuracy=70, power=70, dodge=70, catch=70,
                                  tactical_iq=tiq, catch_courage=tiq,
                                  throw_selection_iq=tiq, conditioning_curve=tiq),
            archetype=PlayerArchetype.THROWER, traits=PlayerTraits(potential=70),
        )

    youngster = Player(
        id="kid", name="Kid", age=19,
        ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
        archetype=PlayerArchetype.THROWER,
        traits=PlayerTraits(potential=90, growth_curve=50, consistency=50, pressure=50),
    )
    # 6 starters (kid + 5 base) then 3 bench veterans.
    starters = [youngster] + base[:5]
    bench = [vet("mentor_vet", 90), vet("analyst_vet", 88), vet("amb_vet", 60)]
    roster = starters + bench
    save_club(conn, club, roster)
    save_lineup_default(conn, "aurora", [p.id for p in roster])
    conn.commit()
    return conn


# --- assignment -----------------------------------------------------------------

def test_only_a_non_starter_can_hold_a_role():
    conn = _career_with_bench()
    br.assign_role(conn, "mentor_vet", "mentor")          # bench -> ok
    assert br.assigned_roles(conn)["mentor_vet"] == "mentor"
    with pytest.raises(ValueError):
        br.assign_role(conn, "kid", "analyst")            # a starter -> refused


def test_a_role_belongs_to_one_player_and_clears():
    conn = _career_with_bench()
    br.assign_role(conn, "mentor_vet", "mentor")
    br.assign_role(conn, "analyst_vet", "mentor")  # reassign -> unique
    roles = br.assigned_roles(conn)
    assert roles == {"analyst_vet": "mentor"}
    br.assign_role(conn, "analyst_vet", None)      # clear
    assert br.assigned_roles(conn) == {}


# --- Mentor (identity-traits consumer) ------------------------------------------

def test_mentor_lifts_a_youngster_scaled_by_identity_traits():
    conn = _career_with_bench()
    kid = next(p for p in load_club_roster(conn, "aurora") if p.id == "kid")
    assert br.mentor_dev_bonus_for(conn, kid) == 0.0  # no mentor yet
    br.assign_role(conn, "mentor_vet", "mentor")       # 90-trait mentor
    high = br.mentor_dev_bonus_for(conn, kid)
    assert high > 0.0
    # A weaker-identity mentor mentors less (the dead traits now matter).
    br.assign_role(conn, "amb_vet", "mentor")          # 60-trait mentor
    low = br.mentor_dev_bonus_for(conn, kid)
    assert 0.0 < low < high
    # No effect on a non-youngster.
    vet = next(p for p in load_club_roster(conn, "aurora") if p.id == "mentor_vet")
    assert br.mentor_dev_bonus_for(conn, vet) == 0.0


# --- Analyst --------------------------------------------------------------------

def test_analyst_targeting_bonus_scales_with_tactical_iq():
    conn = _career_with_bench()
    assert br.analyst_targeting_bonus(conn) == 0.0
    br.assign_role(conn, "analyst_vet", "analyst")  # tactical_iq 88
    assert br.analyst_targeting_bonus(conn) > 0.0


# --- Ambassador -----------------------------------------------------------------

def test_ambassador_monetizes_his_following():
    conn = _career_with_bench()
    assert br.ambassador_income_k(conn) == 0
    br.assign_role(conn, "amb_vet", "ambassador")
    season_id = get_state(conn, "active_season_id")
    fl.add_followers(conn, "amb_vet", 10_000, season_id, "mvp", "MVP")
    conn.commit()
    assert br.ambassador_income_k(conn) > 0
