"""V26 The Crowd — Phase 1: facilities revival + modernization."""
from dodgeball_sim.facilities import FacilityType, FACILITY_DEFINITIONS, apply_facility_effects
from dodgeball_sim.config import DEFAULT_FACILITIES as F


def test_new_facility_types_exist_with_treasury_costs():
    for t in (FacilityType.TRAINING_HALL, FacilityType.STADIUM, FacilityType.MERCH_CENTER):
        assert t in FACILITY_DEFINITIONS
        assert F.treasury_cost_k[t.value] > 0


def test_training_hall_provides_a_practice_development_bonus():
    # The Training Hall's effect is extra practice growth (the V19b channel).
    assert F.training_hall_dev_ovr > 0


def test_stadium_and_merch_have_no_development_modifiers():
    for t in (FacilityType.STADIUM, FacilityType.MERCH_CENTER):
        mods = apply_facility_effects(None, None, [t])
        assert mods.power_growth_multiplier == 1.0 and mods.stamina_recovery_multiplier == 1.0


def test_web_catalog_is_the_effective_facilities():
    # The web offers only facilities with real web effects.
    assert set(F.web_catalog) == {
        "velocity_lab", "reaction_wall", "recovery_suite",
        "training_hall", "stadium", "merch_center",
    }
    assert "film_room" not in F.web_catalog  # CLI-legacy (no web effect)


# --- Task 1.2: treasury-gated permanent buy -------------------------------------

import sqlite3
import pytest
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.economy import set_treasury_k, treasury_k
from dodgeball_sim.persistence import create_schema
from dodgeball_sim import facilities_office as fo

_SEED = 20260617


def _pyramid_conn(treasury=1000):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    set_treasury_k(conn, treasury)
    conn.commit()
    return conn


def _legacy_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", _SEED)
    conn.commit()
    return conn


def test_buy_facility_spends_treasury_and_persists():
    conn = _pyramid_conn(treasury=1000)
    assert fo.owned_facilities(conn) == []
    res = fo.buy_facility(conn, "training_hall")
    assert "training_hall" in fo.owned_facilities(conn)
    assert treasury_k(conn) == 1000 - res["cost_k"]


def test_buy_facility_refuses_when_short_or_duplicate_or_offcatalog():
    conn = _pyramid_conn(treasury=1000)
    fo.buy_facility(conn, "stadium")
    with pytest.raises(ValueError):
        fo.buy_facility(conn, "stadium")          # duplicate
    with pytest.raises(ValueError):
        fo.buy_facility(conn, "film_room")        # off the web catalog
    set_treasury_k(conn, 5); conn.commit()
    with pytest.raises(ValueError):
        fo.buy_facility(conn, "training_hall")    # short


def test_buy_facility_refuses_on_legacy_world():
    conn = _legacy_conn()
    with pytest.raises(ValueError):
        fo.buy_facility(conn, "training_hall")


def test_facility_catalog_flags_owned_and_affordable():
    conn = _pyramid_conn(treasury=150)
    cat = {row["facility_type"]: row for row in fo.facility_catalog(conn)}
    assert cat["training_hall"]["can_afford"] is False  # costs 160 > 150
    assert cat["recovery_suite"]["can_afford"] is True   # costs 90
    fo.buy_facility(conn, "recovery_suite")
    cat2 = {row["facility_type"]: row for row in fo.facility_catalog(conn)}
    assert cat2["recovery_suite"]["owned"] is True and cat2["recovery_suite"]["can_afford"] is False


# --- Task 1.3: the Training Hall's practice credit lands through real development -

def test_training_hall_practice_credit_raises_development():
    from dodgeball_sim.development import apply_season_development
    from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
    from dodgeball_sim.rng import DeterministicRNG, derive_seed
    from dodgeball_sim.stats import PlayerMatchStats

    # A modest-headroom prime player whose base growth stays under the season cap,
    # so the practice credit the Training Hall feeds is visible.
    p = Player(
        id="y", name="Y", age=24,
        ratings=PlayerRatings(accuracy=62, power=62, dodge=62, catch=62),
        archetype=PlayerArchetype.THROWER,
        traits=PlayerTraits(potential=72, growth_curve=50, consistency=50, pressure=50),
    )

    def grew(practice):
        rng = DeterministicRNG(derive_seed(1, "manager_development", "s1", "y"))
        dev = apply_season_development(
            p, PlayerMatchStats(), (), rng,
            trajectory=None, matches_played=12, club_matches=12, practice_credit_ovr=practice,
        )
        return dev.overall_skill() - p.overall_skill()

    # The practice credit the Training Hall adds closes more headroom.
    assert grew(F.training_hall_dev_ovr) > grew(0.0)


# --- Task 1.4: the Dynasty Office payload carries the facilities block -----------

def test_dynasty_office_payload_includes_facilities_on_pyramid():
    from dodgeball_sim.dynasty_office import build_dynasty_office_state

    conn = _pyramid_conn()
    state = build_dynasty_office_state(conn)
    assert state["facilities"] is not None
    keys = {row["facility_type"] for row in state["facilities"]["catalog"]}
    assert "training_hall" in keys


def test_dynasty_office_payload_facilities_none_on_legacy():
    from dodgeball_sim.dynasty_office import build_dynasty_office_state

    conn = _legacy_conn()
    assert build_dynasty_office_state(conn)["facilities"] is None
