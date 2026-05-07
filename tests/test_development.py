from __future__ import annotations

from dataclasses import replace

from dodgeball_sim.config import DEFAULT_CONFIG
from dodgeball_sim.development import (
    apply_season_development,
    fatigue_consistency_modifier,
    pressure_context,
    should_retire,
)
from dodgeball_sim.models import PlayerTraits
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.stats import PlayerMatchStats

from .factories import make_player


def test_apply_season_development_grows_young_player_without_exceeding_potential():
    player = replace(
        make_player("prospect", accuracy=62, power=61, dodge=60, catch=59, stamina=63),
        age=21,
        traits=PlayerTraits(potential=74.0, growth_curve="early", consistency=0.7, pressure=0.6),
    )
    season_stats = PlayerMatchStats(
        eliminations_by_throw=8,
        catches_made=3,
        dodges_successful=4,
        times_eliminated=1,
        elimination_plus_minus=5,
    )

    developed = apply_season_development(
        player=player,
        season_stats=season_stats,
        facilities=("Velocity Lab", "Reaction Wall"),
        rng=DeterministicRNG(77),
    )

    assert developed.newcomer is False
    assert developed.ratings.power >= player.ratings.power
    assert developed.ratings.catch >= player.ratings.catch
    assert developed.ratings.accuracy <= player.traits.potential
    assert developed.ratings.power <= player.traits.potential
    assert developed.ratings.dodge <= player.traits.potential
    assert developed.ratings.catch <= player.traits.potential
    assert developed.ratings.stamina <= player.traits.potential


def test_fatigue_consistency_modifier_rewards_higher_consistency():
    assert fatigue_consistency_modifier(0.9) < fatigue_consistency_modifier(0.2)


def test_pressure_context_only_activates_when_reason_is_present():
    inactive = pressure_context(replace(make_player("calm"), traits=PlayerTraits(pressure=0.8)), None)
    active = pressure_context(
        replace(make_player("clutch"), traits=PlayerTraits(pressure=0.8)),
        "last_player_alive",
    )

    assert inactive == {"pressure_active": False}
    assert active["pressure_active"] is True
    assert active["pressure_reason"] == "last_player_alive"


def test_should_retire_flags_old_declining_veteran():
    player = replace(make_player("veteran", accuracy=48, power=49, dodge=46, catch=47), age=38)
    assert should_retire(player, {"seasons_played": 9, "recent_eliminations": 2}) is True


def _baseline_prospect(player_id: str, age: int = 19) -> Player:
    return Player(
        id=player_id,
        name=player_id,
        age=age,
        club_id="aurora",
        newcomer=True,
        ratings=PlayerRatings(
            accuracy=60.0,
            power=60.0,
            dodge=60.0,
            catch=60.0,
            stamina=60.0,
        ),
        traits=PlayerTraits(potential=80.0, growth_curve=50.0, consistency=0.5, pressure=0.5),
    )


def _develop_for_n_seasons(
    player: Player, n: int, trajectory: str | None, root_seed: int
) -> Player:
    developed = player
    for season in range(n):
        rng = DeterministicRNG(derive_seed(root_seed, "dev_test", str(season), developed.id))
        developed = apply_season_development(
            developed,
            PlayerMatchStats(),
            facilities=(),
            rng=rng,
            trajectory=trajectory,
        )
        developed = replace(developed, age=developed.age + 1)
    return developed


def test_trajectory_none_matches_legacy_development():
    base = _baseline_prospect("legacy_p")
    rng_a = DeterministicRNG(derive_seed(20260426, "dev_legacy", base.id))
    legacy = apply_season_development(
        base,
        PlayerMatchStats(),
        facilities=(),
        rng=rng_a,
    )
    rng_b = DeterministicRNG(derive_seed(20260426, "dev_legacy", base.id))
    new_default = apply_season_development(
        base,
        PlayerMatchStats(),
        facilities=(),
        rng=rng_b,
        trajectory=None,
    )
    assert legacy.ratings.accuracy == new_default.ratings.accuracy
    assert legacy.ratings.power == new_default.ratings.power


def test_trajectory_ordering_in_cumulative_growth():
    base = _baseline_prospect("traj_p", age=19)

    def cumulative_delta(trajectory: str) -> float:
        end = _develop_for_n_seasons(base, n=6, trajectory=trajectory, root_seed=20260426)
        return end.overall() - base.overall()

    delta_normal = cumulative_delta("NORMAL")
    delta_impact = cumulative_delta("IMPACT")
    delta_star = cumulative_delta("STAR")
    delta_generational = cumulative_delta("GENERATIONAL")

    assert delta_normal < delta_impact
    assert delta_impact < delta_star
    assert delta_star < delta_generational


# ---------------------------------------------------------------------------
# staff_development_modifier tests
# ---------------------------------------------------------------------------

def _staff_mod_player() -> Player:
    return Player(
        id="p1",
        name="Test Player",
        age=24,
        archetype=PlayerArchetype.PRECISION,
        ratings=PlayerRatings(
            accuracy=65.0, power=60.0, dodge=60.0,
            catch=60.0, stamina=60.0, tactical_iq=60.0,
        ),
        traits=PlayerTraits(potential=70.0, growth_curve=50.0),
        newcomer=False,
        club_id="club1",
    )


def _staff_mod_stats() -> PlayerMatchStats:
    return PlayerMatchStats(minutes_played=800)


def test_staff_dev_modifier_zero_when_no_staff_unchanged_output():
    """Baseline: zero modifier produces same output as current behavior."""
    player = _staff_mod_player()
    rng1 = DeterministicRNG(seed=42)
    rng2 = DeterministicRNG(seed=42)

    result_no_modifier = apply_season_development(player, _staff_mod_stats(), facilities=(), rng=rng1)
    result_zero_modifier = apply_season_development(
        player, _staff_mod_stats(), facilities=(), rng=rng2, staff_development_modifier=0.0
    )

    assert result_no_modifier.ratings == result_zero_modifier.ratings


def test_staff_dev_modifier_bounded_at_max():
    """A non-zero modifier produces higher OVR than no modifier."""
    max_mod = DEFAULT_CONFIG.max_staff_development_modifier  # 0.15
    player = _staff_mod_player()
    rng_base = DeterministicRNG(seed=99)
    rng_max = DeterministicRNG(seed=99)

    result_base = apply_season_development(player, _staff_mod_stats(), facilities=(), rng=rng_base)
    result_max = apply_season_development(
        player, _staff_mod_stats(), facilities=(), rng=rng_max,
        staff_development_modifier=max_mod,
    )

    assert result_max.overall() >= result_base.overall()


def test_staff_dev_modifier_positive_only():
    """Negative modifier values have no effect (clamped to 0)."""
    player = _staff_mod_player()
    rng1 = DeterministicRNG(seed=77)
    rng2 = DeterministicRNG(seed=77)

    result_negative = apply_season_development(
        player, _staff_mod_stats(), facilities=(), rng=rng1,
        staff_development_modifier=-0.5,
    )
    result_zero = apply_season_development(
        player, _staff_mod_stats(), facilities=(), rng=rng2,
        staff_development_modifier=0.0,
    )

    assert result_negative.ratings == result_zero.ratings
