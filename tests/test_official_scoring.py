from __future__ import annotations

from dodgeball_sim.official_scoring import (
    OfficialGameScore,
    OfficialMatchScore,
    cloth_game_points,
    foam_game_points,
    match_winner_from_points,
)


def test_foam_game_points():
    team_a = "team_a"
    team_b = "team_b"

    # Foam/No-Sting: Elimination win awards 1 point.
    assert foam_game_points(team_a, team_a, team_b) == (1, 0)
    assert foam_game_points(team_b, team_a, team_b) == (0, 1)

    # Foam/No-Sting: Unresolved/No Blocking expiry awards 0 points.
    assert foam_game_points(None, team_a, team_b) == (0, 0)


def test_cloth_game_points():
    team_a = "team_a"
    team_b = "team_b"

    # Cloth: Win awards 2 points.
    assert cloth_game_points(team_a, is_tie=False, team_a_id=team_a, team_b_id=team_b) == (2, 0)
    assert cloth_game_points(team_b, is_tie=False, team_a_id=team_a, team_b_id=team_b) == (0, 2)

    # Cloth: Tie awards 1 point each.
    assert cloth_game_points(None, is_tie=True, team_a_id=team_a, team_b_id=team_b) == (1, 1)
    assert cloth_game_points(None, is_tie=False, team_a_id=team_a, team_b_id=team_b) == (1, 1)


def test_match_winner_from_points():
    team_a = "team_a"
    team_b = "team_b"

    # Team A has more game points -> Team A wins match.
    assert match_winner_from_points(5, 3, team_a, team_b) == team_a

    # Team B has more game points -> Team B wins match.
    assert match_winner_from_points(2, 6, team_a, team_b) == team_b

    # Tied game points -> Drawn match.
    assert match_winner_from_points(4, 4, team_a, team_b) is None


def test_official_score_dataclasses():
    # Verify that OfficialGameScore and OfficialMatchScore instantiate successfully
    game_1 = OfficialGameScore(
        game_number=1,
        winner_team_id="team_a",
        team_a_points=1,
        team_b_points=0,
        result_type="elimination",
        final_active_a=4,
        final_active_b=0,
        mode="standard",
        elapsed_seconds=145,
    )

    match_score = OfficialMatchScore(
        team_a_id="team_a",
        team_b_id="team_b",
        team_a_game_points=1,
        team_b_game_points=0,
        team_a_games_won=1,
        team_b_games_won=0,
        tied_games=0,
        no_point_games=0,
        games=(game_1,),
        winner_team_id="team_a",
    )

    assert len(match_score.games) == 1
    assert match_score.games[0].winner_team_id == "team_a"
