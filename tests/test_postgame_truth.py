"""Postgame copy must reflect the resolved MatchResult.

Regression test for the playtest report: a 0-5 blowout loss displayed a
"Win" / "So close" headline. The root cause was that `render_headline`'s
margin fallback used `box_score["teams"]` dict-iteration order as the
player perspective, so a player team that happened to be the second key
got its scoreline flipped and was tagged as the winner.

The contract this test locks in:

    Given a resolved MatchResult where the player team lost 0-5, the
    rendered postgame headline must not contain "Win" and must not
    contain "So close"; it must reflect the actual Loss + the actual
    scoreline (player survivors first, opponent survivors second).
"""

from __future__ import annotations

import pytest

from dodgeball_sim.aftermath_context import AftermathContext
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.sample_data import scripted_blowout_loss
from dodgeball_sim.voice_verdict import render_headline


def _build_ctx(result, player_club_id: str) -> AftermathContext:
    return AftermathContext(
        match_result=result,
        moment_events=(),
        policy_team=CoachPolicy(),
        policy_opponent=CoachPolicy(),
        tier=1,
        player_club_id=player_club_id,
    )


def test_aftermath_headline_matches_final_score_on_blowout_loss():
    result, player_club_id, opponent_club_id = scripted_blowout_loss(
        player_survivors=0, opponent_survivors=5
    )
    ctx = _build_ctx(result, player_club_id)

    headline = render_headline(ctx)

    # The headline must respect the resolved winner.
    assert result.winner_team_id == opponent_club_id
    # It must not falsely claim a Win.
    assert "Win" not in headline
    # The "So close" template is reserved for narrow losses; a 0-5 loss is
    # a shutout and must not use it.
    assert "So close" not in headline
    # The scoreline must read player-first, opponent-second.
    assert "0-5" in headline


def test_aftermath_headline_when_player_is_second_team_in_box_score():
    """The bug fired specifically when the player's club_id was not the
    first key in box_score["teams"]. Force that ordering and confirm the
    headline still says Loss with the correct scoreline."""
    result, player_club_id, opponent_club_id = scripted_blowout_loss(
        player_survivors=0, opponent_survivors=5, player_first_in_box=False
    )
    # Sanity: the opponent should be the first key.
    teams_iter = list(result.box_score["teams"].keys())
    assert teams_iter[0] == opponent_club_id
    assert teams_iter[1] == player_club_id

    ctx = _build_ctx(result, player_club_id)
    headline = render_headline(ctx)

    assert result.winner_team_id == opponent_club_id
    assert "Loss" in headline
    assert "Win" not in headline
    assert "0-5" in headline


def test_aftermath_player_perspective_win_renders_win():
    """Sanity check the inverse: a 5-0 win for the player still renders
    a Win with the correct scoreline."""
    result, player_club_id, _ = scripted_blowout_loss(
        player_survivors=5, opponent_survivors=0
    )
    ctx = _build_ctx(result, player_club_id)
    headline = render_headline(ctx)

    assert "Win" in headline
    assert "Loss" not in headline
    assert "5-0" in headline


# ---------------------------------------------------------------------------
# Guard function: word-boundary + Draw cases
# ---------------------------------------------------------------------------

from dodgeball_sim.use_cases import _assert_postgame_copy_truthful


def test_guard_allows_winning_streak_in_loss_headline():
    """The guard uses \\bwin\\b, so 'winning streak' (substring 'win' inside
    'winning') must NOT trip the Loss assertion."""
    # Should not raise.
    _assert_postgame_copy_truthful(
        headline="Loss snaps a winning streak",
        verdict=None,
        result="Loss",
        player_survivors=0,
        opponent_survivors=5,
    )


def test_guard_allows_lossless_in_win_headline():
    """'lossless' contains 'loss' as a substring but not as a whole word;
    the regex guard must accept it on a Win."""
    _assert_postgame_copy_truthful(
        headline="A lossless run continues",
        verdict=None,
        result="Win",
        player_survivors=5,
        opponent_survivors=0,
    )


def test_guard_still_trips_on_literal_win_in_loss_headline():
    """Sanity: the guard must still fire when 'Win' appears as a whole word
    on a Loss."""
    with pytest.raises(AssertionError):
        _assert_postgame_copy_truthful(
            headline="What a Win for the team",
            verdict=None,
            result="Loss",
            player_survivors=0,
            opponent_survivors=5,
        )


def test_guard_still_trips_on_literal_loss_in_win_headline():
    with pytest.raises(AssertionError):
        _assert_postgame_copy_truthful(
            headline="A tough Loss to take",
            verdict=None,
            result="Win",
            player_survivors=5,
            opponent_survivors=0,
        )


def test_guard_draw_rejects_win_word():
    with pytest.raises(AssertionError):
        _assert_postgame_copy_truthful(
            headline="A Win-flavored Draw",
            verdict=None,
            result="Draw",
            player_survivors=3,
            opponent_survivors=3,
        )


def test_guard_draw_rejects_loss_word():
    with pytest.raises(AssertionError):
        _assert_postgame_copy_truthful(
            headline="Felt like a Loss out there",
            verdict=None,
            result="Draw",
            player_survivors=3,
            opponent_survivors=3,
        )


def test_guard_draw_accepts_neutral_headline():
    _assert_postgame_copy_truthful(
        headline="Stalemate at the buzzer",
        verdict=None,
        result="Draw",
        player_survivors=3,
        opponent_survivors=3,
    )
