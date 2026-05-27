from __future__ import annotations

from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings, PlayerArchetype
from dodgeball_sim.official_engine import run_autonomous_match
from dodgeball_sim.rulesets import CLOTH_OPEN, FOAM_OPEN


def _make_team(prefix: str, count: int = 6):
    return {
        f"{prefix}{i}": Player(
            id=f"{prefix}{i}", name=f"{prefix}{i}",
            ratings=PlayerRatings(
                accuracy=55 + i, power=55 + i, dodge=50, catch=50,
            ),
            archetype=PlayerArchetype.CATCHER,
        ) for i in range(count)
    }


def test_autonomous_match_series_runs_foam():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}

    result = run_autonomous_match(
        profile=FOAM_OPEN,
        match_id="m1_regular_season",
        team_a_id="A",
        team_b_id="B",
        starters_a=tuple(a.keys()),
        starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=100,
    )

    # Asserts
    assert len(result.official_match_score.games) >= 1
    assert result.replay_state.match_clock is not None
    # elapsed time must be positive
    assert result.replay_state.match_clock.elapsed_seconds > 0
    # match score must be consistent
    score = result.official_match_score
    assert score.team_a_game_points == score.team_a_games_won
    assert score.team_b_game_points == score.team_b_games_won


def test_autonomous_match_series_runs_cloth():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}

    result = run_autonomous_match(
        profile=CLOTH_OPEN,
        match_id="m1_p_r1_m1",  # play-off semifinal -> 30 mins
        team_a_id="A",
        team_b_id="B",
        starters_a=tuple(a.keys()),
        starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=101,
    )

    assert len(result.official_match_score.games) >= 1
    assert result.replay_state.match_clock.limit_seconds == 30 * 60
    
    # Cloth game wins award 2 points, ties award 1
    score = result.official_match_score
    expected_a_points = score.team_a_games_won * 2 + score.tied_games
    expected_b_points = score.team_b_games_won * 2 + score.tied_games
    assert score.team_a_game_points == expected_a_points
    assert score.team_b_game_points == expected_b_points


def test_autonomous_match_determinism():
    a = _make_team("a")
    b = _make_team("b")
    lookup = {**a, **b}

    r1 = run_autonomous_match(
        profile=FOAM_OPEN,
        match_id="m1_regular_season",
        team_a_id="A",
        team_b_id="B",
        starters_a=tuple(a.keys()),
        starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=42,
    )

    r2 = run_autonomous_match(
        profile=FOAM_OPEN,
        match_id="m1_regular_season",
        team_a_id="A",
        team_b_id="B",
        starters_a=tuple(a.keys()),
        starters_b=tuple(b.keys()),
        player_lookup=lookup,
        policy_a=CoachPolicy(),
        policy_b=CoachPolicy(),
        seed=42,
    )

    assert r1.winner_team_id == r2.winner_team_id
    assert len(r1.official_match_score.games) == len(r2.official_match_score.games)
    assert r1.ticks == r2.ticks
