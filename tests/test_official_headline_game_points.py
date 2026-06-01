"""WT-2: the official aftermath headline reports game points, not survivors.

An official foam/cloth game is set-scored: the real score is game points. A
game that expires 0-0 on game points is an honest draw even if survivor counts
were lopsided (e.g. 0-3). The headline must never render the survivor count as
the score — that reads a draw as a blowout.
"""

from __future__ import annotations

from dodgeball_sim.aftermath_context import AftermathContext
from dodgeball_sim.engine import MatchResult
from dodgeball_sim.events import MatchEvent
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.voice_verdict import render_headline


def _result(*, winner, survivors_a, survivors_b, official_metadata=None, config="phase1.v1"):
    return MatchResult(
        events=(
            MatchEvent(
                event_id=1, tick=10, seed=7, event_type="match_end", phase="complete",
                actors={"winner": winner}, context={"reason": "elimination", "moment_events": []},
                probabilities={}, rolls={}, outcome={"winner": winner}, state_diff={},
            ),
        ),
        winner_team_id=winner,
        box_score={
            "teams": {
                "A": {"name": "Aurora", "totals": {"living": survivors_a}, "players": {}},
                "B": {"name": "Solstice", "totals": {"living": survivors_b}, "players": {}},
            },
            "winner": winner,
        },
        final_tick=10, seed=7, config_version=config, official_metadata=official_metadata,
    )


def _ctx(result, *, player="A"):
    return AftermathContext(
        match_result=result, moment_events=(), policy_team=CoachPolicy(),
        policy_opponent=CoachPolicy(), tier=1, player_club_id=player,
    )


def test_official_0_0_game_point_draw_uses_game_points_not_survivors():
    result = _result(
        winner=None, survivors_a=0, survivors_b=3,
        official_metadata={"team_a_id": "A", "team_a_game_points": 0, "team_b_game_points": 0},
        config="usad_foam.v1",
    )
    headline = render_headline(_ctx(result))
    assert "0-0" in headline, headline
    assert "0-3" not in headline, headline
    assert "Draw" in headline and "Win" not in headline and "Loss" not in headline, headline


def test_official_decisive_win_renders_game_point_score():
    result = _result(
        winner="A", survivors_a=2, survivors_b=1,
        official_metadata={"team_a_id": "A", "team_a_game_points": 4, "team_b_game_points": 0},
        config="usad_foam.v1",
    )
    headline = render_headline(_ctx(result))
    assert "4-0" in headline and "2-1" not in headline, headline
    assert "Win" in headline, headline


def test_official_game_points_mapped_by_club_id_not_position():
    # Player is club B; team_a_id is the opponent. The score must be B's points.
    result = _result(
        winner="B", survivors_a=1, survivors_b=3,
        official_metadata={"team_a_id": "A", "team_a_game_points": 1, "team_b_game_points": 4},
        config="usad_cloth.v1",
    )
    headline = render_headline(_ctx(result, player="B"))
    assert "4-1" in headline and "Win" in headline, headline


def test_legacy_match_without_metadata_still_uses_survivors():
    result = _result(winner="A", survivors_a=4, survivors_b=2, official_metadata=None)
    headline = render_headline(_ctx(result))
    assert "4-2" in headline and "Win" in headline, headline


def test_official_1_0_win_is_not_a_total_control_shutout():
    # A 1-0 game-point win (one elimination, the rest no-point draws) must not
    # read as a dominant "shutout / total control" blowout — survivor-tuned
    # tiers over-claim on low game-point totals.
    result = _result(
        winner="A", survivors_a=3, survivors_b=0,
        official_metadata={"team_a_id": "A", "team_a_game_points": 1, "team_b_game_points": 0},
        config="usad_foam.v1",
    )
    headline = render_headline(_ctx(result))
    assert "1-0" in headline and "Win" in headline, headline
    low = headline.lower()
    for overclaim in ("shutout", "total control", "never let them breathe", "never in doubt", "commanding"):
        assert overclaim not in low, f"1-0 official win over-claims: {headline!r}"


def test_official_2_1_win_reads_as_narrow():
    result = _result(
        winner="A", survivors_a=1, survivors_b=2,
        official_metadata={"team_a_id": "A", "team_a_game_points": 2, "team_b_game_points": 1},
        config="usad_foam.v1",
    )
    headline = render_headline(_ctx(result))
    assert "2-1" in headline and "Win" in headline, headline
    assert "shutout" not in headline.lower(), headline


def test_official_4_0_sweep_still_allowed_to_read_dominant():
    # A genuine multi-game sweep SHOULD still be allowed the shutout flavor.
    result = _result(
        winner="A", survivors_a=4, survivors_b=0,
        official_metadata={"team_a_id": "A", "team_a_game_points": 4, "team_b_game_points": 0},
        config="usad_foam.v1",
    )
    headline = render_headline(_ctx(result))
    assert "4-0" in headline and "Win" in headline, headline
