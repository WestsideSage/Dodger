"""V19b staff focus — the Department Orders fiction becomes one real weekly
decision (owner 2026-06-10: staff must stop being meaningless; wire or remove).

The club's staff concentrates on ONE room per week
(``plan.department_orders.focus_department``):

* tactics      -> +18 targeting read next match (V19a tiq consumer)
* conditioning -> fatigue/stamina drag halved next match (V19a stamina consumer)
* training     -> practice credits toward offseason development (+0.2 OVR/week, cap 8)
* scouting     -> +1 Scout action this week
* culture      -> courtship gains land 25% warmer this week
* medical      -> REMOVED (injuries are not modeled; nothing to order)

AI clubs run the same system through their weekly plans (ai_orders assigns an
archetype-flavored focus), so there are no user-only buffs.
"""
from __future__ import annotations

from dataclasses import replace as dc_replace

import pytest

from dodgeball_sim.ai_orders import get_ai_department_orders
from dodgeball_sim.command_center import DEFAULT_DEPARTMENT_ORDERS
from dodgeball_sim.development import apply_season_development
from dodgeball_sim.game_loop import match_prep_from_plan
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.official_engine import OfficialMatchEngineDriver
from dodgeball_sim.rec_engine import RecTier1Driver
from dodgeball_sim.recruiting_actions import apply_action
from dodgeball_sim.rng import DeterministicRNG
from dodgeball_sim.stats import PlayerMatchStats
from tools.probe_lib import make_match_input

_SEEDS = range(6)


class TestPrepDerivation:
    def test_tactics_focus_maps_to_targeting_read(self):
        plan = {"department_orders": {"focus_department": "tactics"}}
        assert match_prep_from_plan(plan) == {"targeting_read_bonus": 18.0}

    def test_conditioning_focus_maps_to_stamina_relief(self):
        plan = {"department_orders": {"focus_department": "conditioning"}}
        assert match_prep_from_plan(plan) == {"stamina_relief": 0.5}

    @pytest.mark.parametrize("focus", ["training", "scouting", "culture", "", None])
    def test_non_match_focuses_carry_no_prep(self, focus):
        plan = {"department_orders": {"focus_department": focus}}
        assert match_prep_from_plan(plan) == {}

    def test_default_orders_carry_a_focus_and_no_medical(self):
        assert DEFAULT_DEPARTMENT_ORDERS["focus_department"] == "tactics"
        assert "medical" not in DEFAULT_DEPARTMENT_ORDERS

    def test_ai_orders_assign_a_focus(self):
        for archetype in (
            "Contender", "Development Factory", "Aging Veterans",
            "Balanced Rebuild", "Defensive Specialist", "Power Throwers",
        ):
            orders = get_ai_department_orders(archetype, "Balanced")
            assert orders.get("focus_department") in (
                "tactics", "training", "conditioning", "scouting", "culture"
            )
        assert (
            get_ai_department_orders("Contender", "Preserve Health")["focus_department"]
            == "conditioning"
        )


def _with_prep_a(mi, prep: dict):
    return dc_replace(mi, config={**mi.config, "prep_a": prep})


@pytest.mark.parametrize(
    "driver_factory",
    [RecTier1Driver, OfficialMatchEngineDriver],
    ids=["rec", "official"],
)
@pytest.mark.parametrize(
    "prep",
    [{"targeting_read_bonus": 18.0}, {"stamina_relief": 0.5}],
    ids=["tactics", "conditioning"],
)
def test_match_preps_are_consumed_by_both_engines(driver_factory, prep):
    """A staff-focus prep must change the match — it rides the V19a consumers."""

    def _fingerprint(out):
        return (out.winner_team_id, out.final_active_a, out.final_active_b, len(out.events))

    driver = driver_factory()
    assert any(
        _fingerprint(driver.run(make_match_input(seed=seed)))
        != _fingerprint(driver.run(_with_prep_a(make_match_input(seed=seed), prep)))
        for seed in _SEEDS
    ), f"prep {prep} never changed a match — the staff focus is dead"


class TestCultureCourtship:
    def test_culture_multiplier_scales_contact_gain(self):
        base_state: dict = {}
        _, normal = apply_action(
            base_state, "contact", base_band=(40, 90), pipeline_tier=2,
            credibility_score=50,
        )
        _, warm = apply_action(
            base_state, "contact", base_band=(40, 90), pipeline_tier=2,
            credibility_score=50, gain_multiplier=1.25,
        )
        normal_gain = normal.interest_after - normal.interest_before
        warm_gain = warm.interest_after - warm.interest_before
        assert warm_gain > normal_gain > 0


class TestTrainingCredits:
    def _adult(self, ovr: int = 66, potential: int = 80) -> Player:
        ratings = PlayerRatings(
            accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr,
            tactical_iq=ovr, catch_courage=ovr, throw_selection_iq=ovr,
            conditioning_curve=ovr,
        )
        return Player(
            id="trainee", name="Trainee", ratings=ratings,
            archetype=PlayerArchetype.THROWER,
            traits=PlayerTraits(potential=potential, growth_curve=50, consistency=50, pressure=50),
            age=26, club_id="aurora", newcomer=False,
        )

    def test_practice_credit_grows_a_benched_adult(self):
        """Practice is off-court: a zero-appearance adult still benefits from a
        season of training-focus weeks (reps gate untouched otherwise)."""
        without = apply_season_development(
            self._adult(), PlayerMatchStats(), facilities=(), rng=DeterministicRNG(5),
            matches_played=0, club_matches=7,
        )
        with_credit = apply_season_development(
            self._adult(), PlayerMatchStats(), facilities=(), rng=DeterministicRNG(5),
            matches_played=0, club_matches=7, practice_credit_ovr=1.6,
        )
        assert with_credit.overall_skill() > without.overall_skill()

    def test_practice_credit_never_pushes_past_the_ceiling(self):
        capped = apply_season_development(
            self._adult(ovr=79, potential=80), PlayerMatchStats(), facilities=(),
            rng=DeterministicRNG(5), matches_played=7, club_matches=7,
            practice_credit_ovr=8.0,
        )
        assert capped.overall_skill() <= 80


class TestScoutingSlotAndCounting:
    def test_scouting_focus_buys_an_extra_scout_action(self):
        import sqlite3

        from dodgeball_sim.career_setup import initialize_curated_manager_career
        from dodgeball_sim.persistence import (
            create_schema, get_state, save_weekly_command_plan,
        )
        from dodgeball_sim.recruitment import (
            deduct_recruiting_slot, get_current_recruiting_budget,
        )

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        initialize_curated_manager_career(conn, "aurora", 20260610)
        season_id = get_state(conn, "active_season_id")
        save_weekly_command_plan(conn, {
            "season_id": season_id, "week": 1, "player_club_id": "aurora",
            "intent": "Balanced",
            "department_orders": {"focus_department": "scouting"},
        })
        conn.commit()
        budget = get_current_recruiting_budget(conn, season_id, 1)
        assert budget["scout"][1] == 4  # 3 + the focus bonus
        for _ in range(4):
            deduct_recruiting_slot(conn, season_id, 1, "scout")
        with pytest.raises(ValueError):
            deduct_recruiting_slot(conn, season_id, 1, "scout")

    def test_training_weeks_are_counted_per_club(self):
        import sqlite3

        from dodgeball_sim.career_setup import initialize_curated_manager_career
        from dodgeball_sim.persistence import (
            count_staff_focus_weeks, create_schema, get_state,
            save_weekly_command_plan,
        )

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        initialize_curated_manager_career(conn, "aurora", 20260610)
        season_id = get_state(conn, "active_season_id")
        for week in (1, 2, 4):
            save_weekly_command_plan(conn, {
                "season_id": season_id, "week": week, "player_club_id": "aurora",
                "intent": "Balanced",
                "department_orders": {"focus_department": "training"},
            })
        save_weekly_command_plan(conn, {
            "season_id": season_id, "week": 3, "player_club_id": "aurora",
            "intent": "Balanced",
            "department_orders": {"focus_department": "tactics"},
        })
        conn.commit()
        assert count_staff_focus_weeks(conn, season_id, "aurora", "training") == 3
        assert count_staff_focus_weeks(conn, season_id, "aurora", "tactics") == 1
