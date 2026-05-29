"""Offseason development must scale with the dev trait (headroom-proportional).

Approach A: a player's growth scales with the gap to their potential, so a
high-ceiling player develops the most even from a low current OVR, growth
tapers as they near their ceiling, and low-potential players (no headroom)
barely move. Replaces the old "uniform +1 OVR" behaviour.
"""
import dataclasses
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.development import apply_season_development
from dodgeball_sim.persistence import create_schema, get_state, load_all_rosters
from dodgeball_sim.rng import DeterministicRNG
from dodgeball_sim.stats import PlayerMatchStats


def _base_player():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return min(load_all_rosters(conn)[get_state(conn, "player_club_id")], key=lambda p: p.overall_skill())


def _grow(base, potential, *, dev_focus="BALANCED"):
    player = dataclasses.replace(base, age=20, traits=dataclasses.replace(base.traits, potential=potential))
    developed = apply_season_development(
        player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(7),
        trajectory=None, dev_focus=dev_focus, staff_development_modifier=0.0,
    )
    return developed.overall_skill() - player.overall_skill()


def test_growth_scales_with_potential_headroom():
    base = _base_player()
    elite = _grow(base, 95)
    high = _grow(base, 80)
    low = _grow(base, base.overall_skill() - 5)  # potential below current => no headroom

    assert elite >= 3, f"elite-ceiling youth grew only +{elite}"
    assert low <= 1, f"no-headroom player grew +{low}"
    assert elite > high >= low


def test_growth_never_overshoots_potential():
    base = _base_player()
    pot = base.overall_skill() + 2  # tiny headroom
    player = dataclasses.replace(base, age=20, traits=dataclasses.replace(base.traits, potential=pot))
    developed = apply_season_development(
        player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(7),
        trajectory=None, dev_focus="BALANCED", staff_development_modifier=0.0,
    )
    # Even with strong staff, OVR cannot exceed the ceiling.
    assert developed.overall_skill() <= pot


def test_potential_upgrade_path_draws_valid_increment():
    """The dev-trait upgrade branch (high performance/staff) must not crash and
    must bump potential by 2..6. Regression for a call to a non-existent
    DeterministicRNG.randint."""
    base = _base_player()
    start_pot = 70
    player = dataclasses.replace(base, age=20, traits=dataclasses.replace(base.traits, potential=start_pot))
    # A large staff modifier forces upgrade_chance > 0.6 and unit() < chance,
    # so the upgrade branch is taken regardless of performance.
    developed = apply_season_development(
        player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(7),
        trajectory=None, dev_focus="BALANCED", staff_development_modifier=2.0,
    )
    bump = developed.traits.potential - start_pot
    assert 2 <= bump <= 6, f"expected potential bump in 2..6, got +{bump}"
