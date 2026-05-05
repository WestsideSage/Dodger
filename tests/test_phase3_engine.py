from __future__ import annotations

from dataclasses import replace

from dodgeball_sim.engine import MatchEngine
from dodgeball_sim.models import CoachPolicy, PlayerState, PlayerTraits

from .factories import make_match_setup, make_player, make_team


def test_high_consistency_player_accumulates_less_fatigue_for_same_delta():
    engine = MatchEngine()
    high = PlayerState(player=replace(make_player("high"), traits=PlayerTraits(consistency=0.9)))
    low = PlayerState(player=replace(make_player("low"), traits=PlayerTraits(consistency=0.1)))

    engine._apply_fatigue(high, delta=1.0)
    engine._apply_fatigue(low, delta=1.0)

    assert high.fatigue < low.fatigue


def test_pressure_modifier_is_logged_on_qualifying_throw_events():
    offense = make_team(
        "alpha",
        [replace(make_player("alpha_1", accuracy=78, power=72), traits=PlayerTraits(pressure=1.0))],
        policy=CoachPolicy(),
    )
    defense = make_team(
        "beta",
        [make_player("beta_1", dodge=60, catch=55)],
        policy=CoachPolicy(),
    )

    result = MatchEngine().run(make_match_setup(offense, defense), seed=123, difficulty="pro")
    throw_events = [event for event in result.events if event.event_type == "throw"]

    assert throw_events
    assert all(event.context["pressure_active"] is True for event in throw_events)
    assert all(event.context["pressure_reason"] in {"last_player_alive", "final_elimination_opportunity"} for event in throw_events)
    assert all("pressure" in event.context["calc"]["context_terms"] for event in throw_events)
