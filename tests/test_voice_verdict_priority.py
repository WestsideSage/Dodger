from __future__ import annotations

from dodgeball_sim.aftermath_context import AftermathContext
from dodgeball_sim.engine import MatchResult
from dodgeball_sim.events import MatchEvent
from dodgeball_sim.moment_events import Comeback, DramaticCatch
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.voice_verdict import HEADLINE_PRIORITY, render_headline


def test_headline_priority_prefers_comeback_over_dramatic_catch():
    ctx = AftermathContext(
        match_result=_match_result(winner_team_id="A"),
        moment_events=(
            DramaticCatch(
                match_id="m1",
                tick=8,
                catcher_id="a1",
                catcher_team_id="A",
                thrower_id="b1",
                thrower_team_id="B",
                returning_player_id="a2",
                active_count_a=3,
                active_count_b=2,
            ),
            Comeback(
                match_id="m1",
                tick=12,
                team_id="A",
                deficit_at_low_point=3,
                catches_during_comeback=2,
            ),
        ),
        policy_team=CoachPolicy(),
        policy_opponent=CoachPolicy(),
        tier=1,
    )

    assert HEADLINE_PRIORITY[0] == "one_v_one_finale"
    assert HEADLINE_PRIORITY[1] == "comeback"
    assert render_headline(ctx) == "Aurora were down 3 and clawed it back with 2 catches."


def test_headline_without_moments_falls_back_to_margin_copy():
    ctx = AftermathContext(
        match_result=_match_result(winner_team_id="A"),
        moment_events=(),
        policy_team=CoachPolicy(),
        policy_opponent=CoachPolicy(),
        tier=1,
    )

    headline = render_headline(ctx)
    assert "4-2" in headline
    assert "Win" in headline


def _match_result(*, winner_team_id: str | None) -> MatchResult:
    return MatchResult(
        events=(
            MatchEvent(
                event_id=0,
                tick=0,
                seed=7,
                event_type="match_start",
                phase="init",
                actors={"team_a": "A", "team_b": "B"},
                context={
                    "config_version": "phase1.v1",
                    "difficulty": "pro",
                    "meta_patch": None,
                    "team_policies": {
                        "A": CoachPolicy().as_dict(),
                        "B": CoachPolicy().as_dict(),
                    },
                },
                probabilities={},
                rolls={},
                outcome={"message": "start"},
                state_diff={},
            ),
            MatchEvent(
                event_id=1,
                tick=10,
                seed=7,
                event_type="match_end",
                phase="complete",
                actors={"winner": winner_team_id},
                context={"reason": "elimination", "moment_events": []},
                probabilities={},
                rolls={},
                outcome={"winner": winner_team_id},
                state_diff={},
            ),
        ),
        winner_team_id=winner_team_id,
        box_score={
            "teams": {
                "A": {"name": "Aurora", "totals": {"living": 4}, "players": {"a1": {"name": "Maurice"}, "a2": {"name": "Sam"}}},
                "B": {"name": "Solstice", "totals": {"living": 2}, "players": {"b1": {"name": "Riley"}}},
            },
            "winner": winner_team_id,
        },
        final_tick=10,
        seed=7,
        config_version="phase1.v1",
    )
