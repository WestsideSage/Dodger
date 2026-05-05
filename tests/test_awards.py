from __future__ import annotations

from dodgeball_sim.awards import compute_match_mvp, compute_season_awards
from dodgeball_sim.stats import PlayerMatchStats


def test_compute_season_awards_matches_raw_player_stats_leaders():
    player_stats = {
        "alpha": PlayerMatchStats(eliminations_by_throw=8, catches_made=2, dodges_successful=3, times_eliminated=1),
        "bravo": PlayerMatchStats(eliminations_by_throw=6, catches_made=6, dodges_successful=1, times_eliminated=2),
        "charlie": PlayerMatchStats(eliminations_by_throw=4, catches_made=1, dodges_successful=2, times_eliminated=1),
    }
    awards = compute_season_awards(
        season_id="season_2026",
        player_season_stats=player_stats,
        player_club_map={"alpha": "club_a", "bravo": "club_b", "charlie": "club_c"},
        newcomer_player_ids=frozenset({"bravo", "charlie"}),
    )

    by_type = {award.award_type: award for award in awards}

    assert by_type["mvp"].player_id == "bravo"
    assert by_type["best_thrower"].player_id == "alpha"
    assert by_type["best_catcher"].player_id == "bravo"
    assert by_type["best_newcomer"].player_id == "bravo"


def test_compute_match_mvp_picks_highest_score():
    stats = {
        "alice": PlayerMatchStats(eliminations_by_throw=4, catches_made=1),
        "bob": PlayerMatchStats(eliminations_by_throw=2, catches_made=2),
        "carol": PlayerMatchStats(eliminations_by_throw=1, catches_made=0),
    }
    assert compute_match_mvp(stats) == "alice"


def test_compute_match_mvp_deterministic_tiebreak():
    stats = {
        "zeta": PlayerMatchStats(eliminations_by_throw=2),
        "alpha": PlayerMatchStats(eliminations_by_throw=2),
    }
    assert compute_match_mvp(stats) == "zeta"


def test_compute_match_mvp_empty_returns_none():
    assert compute_match_mvp({}) is None
