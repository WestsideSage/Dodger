from __future__ import annotations

from dodgeball_sim.aftermath_context import AftermathContext
from dodgeball_sim.engine import MatchResult
from dodgeball_sim.events import MatchEvent
from dodgeball_sim.moment_events import DramaticCatch
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.voice_aftermath import render_body


def test_render_body_anchors_on_moment_and_tactic_without_invention():
    ctx = AftermathContext(
        match_result=_match_result(),
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
        ),
        policy_team=CoachPolicy(catch_posture="go_for_catches"),
        policy_opponent=CoachPolicy(),
        tier=1,
    )

    paragraphs = render_body(ctx)
    rendered = " ".join(paragraphs)
    assert 2 <= len(paragraphs) <= 4
    assert "Maurice" in rendered and "Sam" in rendered
    assert "Go for catches" in rendered


def test_render_body_with_no_moments_does_not_invent_one():
    ctx = AftermathContext(
        match_result=_match_result(),
        moment_events=(),
        policy_team=CoachPolicy(),
        policy_opponent=CoachPolicy(catch_posture="play_safe"),
        tier=1,
    )

    paragraphs = render_body(ctx)
    rendered = " ".join(paragraphs).lower()
    assert 2 <= len(paragraphs) <= 4
    assert "maurice" not in rendered
    assert "plucks" not in rendered
    assert "one back on" not in rendered


def _match_result() -> MatchResult:
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
                actors={"winner": "A"},
                context={"reason": "elimination", "moment_events": []},
                probabilities={},
                rolls={},
                outcome={"winner": "A"},
                state_diff={},
            ),
        ),
        winner_team_id="A",
        box_score={
            "teams": {
                "A": {"name": "Aurora", "totals": {"living": 4}, "players": {"a1": {"name": "Maurice"}, "a2": {"name": "Sam"}}},
                "B": {"name": "Solstice", "totals": {"living": 2}, "players": {"b1": {"name": "Riley"}}},
            },
            "winner": "A",
        },
        final_tick=10,
        seed=7,
        config_version="phase1.v1",
    )
