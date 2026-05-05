from __future__ import annotations

from dodgeball_sim.events import MatchEvent
from dodgeball_sim.narration import build_lookup_from_setup, narrate_event

from .factories import make_match_setup, make_player, make_team


def _match_setup():
    team_a = make_team("alpha", [make_player("a1", name="Alpha Ace", accuracy=75)])
    team_b = make_team("beta", [make_player("b1", name="Beta Block", dodge=70)])
    return make_match_setup(team_a, team_b)


def test_narration_for_hit_event():
    setup = _match_setup()
    lookup = build_lookup_from_setup(setup)
    event = MatchEvent(
        event_id=1,
        tick=5,
        seed=1,
        event_type="throw",
        phase="live",
        actors={
            "offense_team": "alpha",
            "defense_team": "beta",
            "thrower": "a1",
            "target": "b1",
        },
        context={},
        probabilities={},
        rolls={},
        outcome={"resolution": "hit", "player_out": "b1"},
        state_diff={},
    )
    text = narrate_event(event, lookup)
    assert "Alpha" in text and "Beta" in text and "OUT" in text


def test_narration_handles_start_and_end():
    setup = _match_setup()
    lookup = build_lookup_from_setup(setup)
    start_event = MatchEvent(
        event_id=0,
        tick=0,
        seed=1,
        event_type="match_start",
        phase="init",
        actors={"team_a": "alpha", "team_b": "beta"},
        context={},
        probabilities={},
        rolls={},
        outcome={},
        state_diff={},
    )
    end_event = MatchEvent(
        event_id=2,
        tick=10,
        seed=1,
        event_type="match_end",
        phase="complete",
        actors={},
        context={},
        probabilities={},
        rolls={},
        outcome={"winner": "alpha"},
        state_diff={},
    )
    assert "underway" in narrate_event(start_event, lookup)
    assert "wins" in narrate_event(end_event, lookup)
