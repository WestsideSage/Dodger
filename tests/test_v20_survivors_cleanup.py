"""V20 §7.3 survivors cleanup — official surfaces stop showing survivor noise.

On official matches the ``home/away_survivors`` columns hold only the FINAL
game's living counts. Three surfaces treated them as a match score anyway:

* league memory / standings "recent matches" lines rendered "Home 0-3 Away"
  (and could name the recorded LOSER as winner via score comparison),
* the Command Center last-meeting line printed the same false score,
* standings accumulated them into a displayed "differential" and the web
  standings payload even TIEBROKE on that noise (diverging from the
  persisted season.compute_standings official sort).

The columns stay (raw box data for rec scoring + postgame validation); the
cleanup removes them from every official display/aggregation path.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.league_memory import recent_match_item
from dodgeball_sim.season import StandingsRow, compute_standings


class _FakeResult:
    def __init__(self, home, away, winner, *, home_surv, away_surv, home_gp, away_gp, official):
        self.home_club_id = home
        self.away_club_id = away
        self.winner_club_id = winner
        self.home_survivors = home_surv
        self.away_survivors = away_surv
        self.home_game_points = home_gp
        self.away_game_points = away_gp
        self.config_version = "official:foam" if official else None


def _row(**kwargs):
    """A sqlite3.Row over the recent-match columns."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    keys = ", ".join(kwargs)
    placeholders = ", ".join("?" for _ in kwargs)
    return conn.execute(
        f"SELECT {placeholders}".replace(placeholders, ", ".join(f"? AS {k}" for k in kwargs)),
        tuple(kwargs.values()),
    ).fetchone()


def test_official_recent_match_line_uses_game_points_and_recorded_winner():
    # A 2-1 game-points HOME win whose final game ended 0-3: the old code
    # rendered "0-3" and named the AWAY club the winner.
    row = _row(
        match_id="season_1_w1_m1", week=1,
        home_club_id="aurora", away_club_id="lunar", winner_club_id="aurora",
        home_survivors=0, away_survivors=3,
        scoring_model="official", home_game_points=2, away_game_points=1,
    )
    item = recent_match_item(row, clubs={})
    assert "2-1" in item["summary"]
    assert "0-3" not in item["summary"]
    assert item["winner_name"] == "aurora"


def test_legacy_recent_match_line_keeps_survivor_scores():
    row = _row(
        match_id="season_1_w1_m1", week=1,
        home_club_id="aurora", away_club_id="lunar", winner_club_id="lunar",
        home_survivors=1, away_survivors=4,
        scoring_model="legacy", home_game_points=0, away_game_points=0,
    )
    item = recent_match_item(row, clubs={})
    assert "1-4" in item["summary"]


def test_official_standings_do_not_accumulate_survivor_noise():
    results = [
        _FakeResult("aurora", "lunar", "aurora",
                    home_surv=0, away_surv=3, home_gp=2, away_gp=1, official=True),
    ]
    rows = compute_standings(results)
    by_club = {row.club_id: row for row in rows}
    # The survivor "differential" stays honestly zero on officials...
    assert by_club["aurora"].elimination_differential == 0
    assert by_club["lunar"].elimination_differential == 0
    # ...while the real ranking stats accumulate.
    assert by_club["aurora"].game_point_differential == 1
    assert by_club["lunar"].game_point_differential == -1
    assert by_club["aurora"].wins == 1 and by_club["lunar"].losses == 1


def test_legacy_standings_keep_survivor_differential():
    results = [
        _FakeResult("aurora", "lunar", "aurora",
                    home_surv=4, away_surv=1, home_gp=0, away_gp=0, official=False),
    ]
    rows = compute_standings(results)
    by_club = {row.club_id: row for row in rows}
    assert by_club["aurora"].elimination_differential == 3
    assert by_club["lunar"].elimination_differential == -3


def test_standings_row_carries_game_point_fields():
    # Guard the payload contract the web standings sort now depends on.
    row = StandingsRow(
        club_id="aurora", wins=1, losses=0, draws=0,
        elimination_differential=0, points=3,
        game_points_for=2, game_points_against=1,
        game_point_differential=1, total_game_points_scored=2,
    )
    assert row.total_game_points_scored == 2
