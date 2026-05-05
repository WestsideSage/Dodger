from __future__ import annotations

from dodgeball_sim.events import MatchEvent
from dodgeball_sim.franchise import extract_match_stats, simulate_match
from dodgeball_sim.league import Club
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.stats import aggregate_club_stats, extract_player_stats

from .factories import make_player


def test_extract_match_stats_match_box_score_totals():
    home_roster = [
        make_player("home_1", accuracy=82, power=74, dodge=55, catch=40),
        make_player("home_2", accuracy=64, power=58, dodge=68, catch=52),
        make_player("home_3", accuracy=59, power=63, dodge=60, catch=66),
    ]
    away_roster = [
        make_player("away_1", accuracy=78, power=70, dodge=57, catch=42),
        make_player("away_2", accuracy=62, power=60, dodge=67, catch=56),
        make_player("away_3", accuracy=57, power=55, dodge=61, catch=72),
    ]
    home_club = Club("home", "Home Club", "red/white", "North", 2020, CoachPolicy())
    away_club = Club("away", "Away Club", "blue/black", "South", 2020, CoachPolicy())

    scheduled, season_result = simulate_match(
        scheduled=type("Scheduled", (), {
            "match_id": "season_2026_w01_home_vs_away",
            "season_id": "season_2026",
            "week": 1,
            "home_club_id": "home",
            "away_club_id": "away",
        })(),
        home_club=home_club,
        away_club=away_club,
        home_roster=home_roster,
        away_roster=away_roster,
        root_seed=4242,
    )

    stats = extract_match_stats(scheduled, home_roster, away_roster)
    box = scheduled.result.box_score["teams"]

    home_stats = [stats[player.id] for player in home_roster]
    away_stats = [stats[player.id] for player in away_roster]

    assert sum(item.throws_attempted for item in home_stats) == sum(
        player_box["throws"] for player_box in box["home"]["players"].values()
    )
    assert sum(item.throws_attempted for item in away_stats) == sum(
        player_box["throws"] for player_box in box["away"]["players"].values()
    )

    home_aggregate = aggregate_club_stats(home_stats, season_result.home_survivors)
    away_aggregate = aggregate_club_stats(away_stats, season_result.away_survivors)

    assert home_aggregate.outs_recorded == box["home"]["totals"]["hits"]
    assert away_aggregate.outs_recorded == box["away"]["totals"]["hits"]
    assert home_aggregate.catches_made == box["home"]["totals"]["catches"]
    assert away_aggregate.catches_made == box["away"]["totals"]["catches"]
    assert sum(item.dodges_successful for item in home_stats) == box["home"]["totals"]["dodges"]
    assert sum(item.dodges_successful for item in away_stats) == box["away"]["totals"]["dodges"]
    assert home_aggregate.surviving_players == box["home"]["totals"]["living"]
    assert away_aggregate.surviving_players == box["away"]["totals"]["living"]


def test_extract_player_stats_returns_minutes_played_for_active_player():
    events = [
        MatchEvent(
            event_id=1,
            tick=4,
            seed=101,
            event_type="throw",
            phase="live",
            actors={"thrower": "p1", "target": "p2"},
            context={},
            probabilities={},
            rolls={},
            outcome={"resolution": "dodged"},
            state_diff={},
        ),
        MatchEvent(
            event_id=2,
            tick=9,
            seed=102,
            event_type="throw",
            phase="live",
            actors={"thrower": "p2", "target": "p1"},
            context={},
            probabilities={},
            rolls={},
            outcome={"resolution": "hit"},
            state_diff={"player_out": {"player_id": "p1", "team": "home"}},
        ),
        MatchEvent(
            event_id=3,
            tick=14,
            seed=103,
            event_type="throw",
            phase="live",
            actors={"thrower": "p2", "target": "p3"},
            context={},
            probabilities={},
            rolls={},
            outcome={"resolution": "dodged"},
            state_diff={},
        ),
    ]

    stats = extract_player_stats(events, "p1", "home")

    assert stats.minutes_played == 9
