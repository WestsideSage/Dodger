"""V22 Phase 4 — all six department-head ratings drive real effects.

Owner: "go further: wire all six." Each test pins one hook end-to-end
through the REAL consumer (prep builder, recruiting action, development
decline path), plus the formula anchors that keep the legacy disclosed
numbers honest for the default heads.
"""
from __future__ import annotations

from dodgeball_sim.staff_effects import (
    conditioning_focus_relief,
    culture_focus_interest_multiplier,
    medical_decline_mitigation,
    scouting_band_quality,
    staff_effect_detail,
    tactics_focus_tiq_bonus,
    training_dev_modifier,
)


def test_formulas_anchor_to_the_legacy_flats_and_clamp():
    # Anchors: the default heads land on (or beside) the numbers the game
    # already disclosed before the wiring.
    assert abs(tactics_focus_tiq_bonus(75) - 18.0) < 1e-9      # legacy flat +18
    assert abs(conditioning_focus_relief(75) - 0.50) < 1e-9    # legacy "halved"
    assert culture_focus_interest_multiplier(70) == 1.25       # legacy x1.25
    assert abs(scouting_band_quality(75) - 1.0) < 1e-9         # legacy narrowing
    # Clamps.
    assert tactics_focus_tiq_bonus(0) == 12.0 and tactics_focus_tiq_bonus(200) == 24.0
    assert conditioning_focus_relief(0) == 0.30 and conditioning_focus_relief(200) == 0.70
    assert culture_focus_interest_multiplier(0) == 1.15
    assert culture_focus_interest_multiplier(200) == 1.40
    assert scouting_band_quality(0) == 0.70 and scouting_band_quality(200) == 1.30
    assert medical_decline_mitigation(50) == 0.0
    assert medical_decline_mitigation(40) == 0.0  # never a penalty


def test_every_hook_is_monotonic_in_the_head_rating():
    for formula in (
        tactics_focus_tiq_bonus,
        conditioning_focus_relief,
        culture_focus_interest_multiplier,
        scouting_band_quality,
        medical_decline_mitigation,
        training_dev_modifier,
    ):
        values = [formula(r) for r in (50, 60, 70, 80, 90, 99)]
        assert values == sorted(values), f"{formula.__name__} must not regress"
        assert values[-1] > values[0], f"{formula.__name__} must actually scale"


def test_every_department_has_a_concrete_disclosed_detail():
    for dept in ("tactics", "training", "conditioning", "medical", "scouting", "culture"):
        detail = staff_effect_detail(dept, 80)
        assert any(ch.isdigit() for ch in detail), (
            f"{dept} detail must carry a number, got: {detail}"
        )


def test_match_prep_scales_with_the_head_and_stays_flat_without_one():
    from dodgeball_sim.game_loop import match_prep_from_plan

    plan = {"department_orders": {"focus_department": "tactics"}}
    weak = match_prep_from_plan(plan, {"tactics": 55.0})
    strong = match_prep_from_plan(plan, {"tactics": 95.0})
    legacy = match_prep_from_plan(plan)  # AI clubs: no head table
    assert strong["targeting_read_bonus"] > weak["targeting_read_bonus"]
    assert legacy == {"targeting_read_bonus": 18.0}

    cond_plan = {"department_orders": {"focus_department": "conditioning"}}
    assert (
        match_prep_from_plan(cond_plan, {"conditioning": 95.0})["stamina_relief"]
        > match_prep_from_plan(cond_plan, {"conditioning": 55.0})["stamina_relief"]
    )
    assert match_prep_from_plan(cond_plan) == {"stamina_relief": 0.5}


def test_scout_quality_scales_the_persisted_band():
    from dodgeball_sim.recruiting_actions import apply_action, scouted_band_from_state

    base = (40, 80)
    weak_state, _ = apply_action(
        {}, "scout", base_band=base, pipeline_tier=3, credibility_score=50,
        scout_quality=scouting_band_quality(50),
    )
    strong_state, _ = apply_action(
        {}, "scout", base_band=base, pipeline_tier=3, credibility_score=50,
        scout_quality=scouting_band_quality(99),
    )
    weak_band = scouted_band_from_state(weak_state, base)
    strong_band = scouted_band_from_state(strong_state, base)
    assert (strong_band[1] - strong_band[0]) < (weak_band[1] - weak_band[0]), (
        "a better scouting head must produce a tighter band"
    )
    # The band persists on the state — every surface reads the same numbers.
    assert weak_state["scouted_band"] == list(weak_band)
    # Legacy states (scouted before V22, no persisted band) keep the default
    # narrowing instead of crashing or widening.
    legacy = scouted_band_from_state({"scouted": True}, base)
    assert legacy[0] > base[0] and legacy[1] < base[1]


def test_medical_head_mitigates_decline_training_no_longer_does():
    from dodgeball_sim.archetype_derivation import derive_archetype
    from dodgeball_sim.development import apply_season_development
    from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits
    from dodgeball_sim.rng import DeterministicRNG
    from dodgeball_sim.stats import PlayerMatchStats

    def veteran() -> Player:
        ratings = PlayerRatings(
            accuracy=70, power=70, dodge=70, catch=70, stamina=70,
            tactical_iq=70, catch_courage=70, throw_selection_iq=70,
            conditioning_curve=70,
        ).apply_bounds()
        return Player(
            id="vet",
            name="Old Pro",
            age=33,  # past every peak window -> decline path
            club_id="club",
            newcomer=False,
            ratings=ratings,
            archetype=derive_archetype(ratings),
            traits=PlayerTraits(potential=70.0, growth_curve=50.0, consistency=0.5, pressure=0.5),
        )

    def run(**kwargs) -> float:
        developed = apply_season_development(
            veteran(),
            PlayerMatchStats(),
            facilities=(),
            rng=DeterministicRNG(7),
            **kwargs,
        )
        return developed.overall_skill()

    unmitigated = run()
    medical = run(decline_mitigation_modifier=medical_decline_mitigation(90))
    training_only = run(staff_development_modifier=training_dev_modifier(90))

    assert medical > unmitigated, "a strong medical head must soften decline"
    assert training_only == unmitigated, (
        "the training modifier must no longer mitigate decline — medical owns it"
    )
