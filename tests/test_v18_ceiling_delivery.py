"""V18 ceiling-delivery gates: the displayed ceiling is an honest promise.

BEFORE (post-V17 baseline, BEFORE table in
``docs/specs/2026-06-10-v18-development-mortality-sprint-plan.md``): full-time
starters closed only 20-34% of promised headroom and peaked ~10 OVR short of
the effective potential the Roster Lab displays as "Ceiling". Two structural
leaks: 40% of every growth pool was spread across all nine rated stats while
OVR averages five (so 18-48% of growth, depending on archetype primaries,
never moved OVR), and the geometric headroom taper plus per-stat int rounding
starved the final approach.

These gates pin the V18 contract: a fully-repped starter reaches within 2 OVR
of their effective potential by the end of their peak window, regardless of
archetype, and bench/no-headroom players still do not move.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from dodgeball_sim.development import apply_season_development
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.stats import PlayerMatchStats

# growth_curve=50 -> "steady" -> peak window 25-28 (development._peak_window).
_STEADY_PEAK_END = 28


def _starter(pid: str, *, ovr: int, potential: int, age: int, archetype: PlayerArchetype) -> Player:
    ratings = PlayerRatings(
        accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr,
        tactical_iq=ovr, catch_courage=ovr, throw_selection_iq=ovr,
        conditioning_curve=ovr,
    )
    return Player(
        id=pid,
        name=pid.title(),
        ratings=ratings,
        archetype=archetype,
        traits=PlayerTraits(potential=potential, growth_curve=50, consistency=50, pressure=50),
        age=age,
        club_id="aurora",
        newcomer=False,
    )


def _develop_to_peak_end(player: Player, *, root_seed: int = 20260610) -> Player:
    """Season-by-season full-reps development through the peak window.

    Mirrors the offseason caller: develop, then age +1. Empty match stats keep
    the performance signal at zero, so the dev-trait upgrade branch never
    fires and the promise being tested is the SEEDED effective potential.
    """
    developed = player
    season = 0
    while developed.age <= _STEADY_PEAK_END:
        rng = DeterministicRNG(
            derive_seed(root_seed, "v18_delivery", str(season), developed.id)
        )
        developed = apply_season_development(
            developed,
            PlayerMatchStats(),
            facilities=(),
            rng=rng,
            matches_played=7,
            club_matches=7,
        )
        developed = replace(developed, age=developed.age + 1)
        season += 1
    return developed


class TestCeilingDelivery:
    @pytest.mark.parametrize("age", (18, 21, 24))
    @pytest.mark.parametrize(
        "archetype",
        (
            PlayerArchetype.THROWER,        # both primaries are OVR stats
            PlayerArchetype.CATCHER,        # catch_courage primary leaked off-OVR
            PlayerArchetype.DODGER_ANCHOR,  # tactical_iq primary leaked off-OVR
        ),
    )
    def test_full_reps_starter_reaches_ceiling_by_peak_end(self, age, archetype):
        player = _starter(
            f"deliver_{archetype.name.lower()}_{age}",
            ovr=60, potential=82, age=age, archetype=archetype,
        )
        developed = _develop_to_peak_end(player)
        assert developed.overall_skill() >= 80, (
            f"{archetype.name} starter (age {age}, OVR 60, ceiling 82) peaked at "
            f"{developed.overall_skill()} — the displayed ceiling is still an overpromise"
        )
        # The cap side of the promise: delivery must never overshoot.
        assert developed.overall_skill() <= 82

    def test_delivery_is_archetype_independent(self):
        """The old pool gave OVR 82% of growth for a THROWER but 52% for a
        CATCHER/DODGER — the same displayed ceiling meant different things per
        archetype. Delivery must now land within the same 2-OVR band."""
        finals = []
        for archetype in (
            PlayerArchetype.THROWER,
            PlayerArchetype.CATCHER,
            PlayerArchetype.DODGER_ANCHOR,
            PlayerArchetype.BALL_HAWK,
        ):
            player = _starter(
                f"arch_{archetype.name.lower()}", ovr=62, potential=80, age=21,
                archetype=archetype,
            )
            finals.append(_develop_to_peak_end(player).overall_skill())
        assert max(finals) - min(finals) <= 2, (
            f"archetype-dependent ceiling delivery: finals={finals}"
        )

    def test_zero_headroom_player_does_not_grow(self):
        player = _starter(
            "plateaued", ovr=70, potential=60, age=24,
            archetype=PlayerArchetype.THROWER,
        )
        developed = apply_season_development(
            player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(11),
            matches_played=7, club_matches=7,
        )
        assert developed.overall_skill() <= player.overall_skill()

    def test_benched_adult_still_gated_despite_finish_floor(self):
        """The arrival floor must scale with reps: a 26-year-old who never
        fields stays parked even with headroom on the books."""
        player = _starter(
            "benched", ovr=66, potential=88, age=26,
            archetype=PlayerArchetype.THROWER,
        )
        developed = apply_season_development(
            player, PlayerMatchStats(), facilities=(), rng=DeterministicRNG(11),
            matches_played=0, club_matches=7,
        )
        assert developed.overall_skill() - player.overall_skill() <= 1
