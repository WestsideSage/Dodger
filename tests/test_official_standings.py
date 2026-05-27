from __future__ import annotations

from dodgeball_sim.season import SeasonResult, compute_standings


def test_compute_standings_legacy_rules():
    # In legacy rules, sorting is points -> elimination_differential -> club_id
    res1 = SeasonResult(
        match_id="m1", season_id="s1", week=1,
        home_club_id="A", away_club_id="B",
        home_survivors=4, away_survivors=0,
        winner_club_id="A", seed=1,
        config_version="legacy",
    )
    res2 = SeasonResult(
        match_id="m2", season_id="s1", week=1,
        home_club_id="C", away_club_id="D",
        home_survivors=2, away_survivors=0,
        winner_club_id="C", seed=1,
        config_version="legacy",
    )
    standings = compute_standings([res1, res2])
    assert standings[0].club_id == "A"  # 3 pts, +4 survivors
    assert standings[1].club_id == "C"  # 3 pts, +2 survivors


def test_compute_standings_official_rules():
    # In official rules, sorting is points -> total_game_points_scored -> game_point_differential -> club_id
    # Team A won with fewer survivors than C, but scored more game points!
    res1 = SeasonResult(
        match_id="m1", season_id="s1", week=1,
        home_club_id="A", away_club_id="B",
        home_survivors=1, away_survivors=0,
        winner_club_id="A", seed=1,
        config_version="official:foam",
        home_game_points=8, away_game_points=2,
    )
    res2 = SeasonResult(
        match_id="m2", season_id="s1", week=1,
        home_club_id="C", away_club_id="D",
        home_survivors=6, away_survivors=0,
        winner_club_id="C", seed=1,
        config_version="official:foam",
        home_game_points=4, away_game_points=1,
    )
    
    standings = compute_standings([res1, res2])
    # A should be ranked #1 despite lower survivors because 8 game points > 4 game points
    assert standings[0].club_id == "A"
    assert standings[0].game_points_for == 8
    assert standings[0].game_points_against == 2
    assert standings[0].game_point_differential == 6
    assert standings[0].total_game_points_scored == 8

    assert standings[1].club_id == "C"
    assert standings[1].game_points_for == 4
    assert standings[1].game_points_against == 1
    assert standings[1].game_point_differential == 3
    assert standings[1].total_game_points_scored == 4
