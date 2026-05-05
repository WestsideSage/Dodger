from __future__ import annotations

import sqlite3
from dataclasses import replace

from dodgeball_sim.league import Club, Conference, League
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.persistence import (
    initialize_schema,
    load_all_rosters,
    load_clubs,
    load_season,
    load_season_format,
    load_season_outcome,
    load_standings,
    save_playoff_bracket,
    save_club,
    save_season,
    save_season_format,
    save_season_outcome,
    save_standings,
)
from dodgeball_sim.season import StandingsRow
from dodgeball_sim.playoffs import create_semifinal_bracket, outcome_from_final
from dodgeball_sim.franchise import create_season

from .factories import make_player


def test_dynasty_round_trip_preserves_clubs_season_and_standings():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)

    clubs = {
        "club_a": Club("club_a", "Club A", "red/white", "North", 2020, CoachPolicy()),
        "club_b": Club("club_b", "Club B", "blue/black", "South", 2020, CoachPolicy()),
        "club_c": Club("club_c", "Club C", "gold/green", "East", 2020, CoachPolicy()),
        "club_d": Club("club_d", "Club D", "silver/navy", "West", 2020, CoachPolicy()),
    }
    rosters = {
        club_id: [
            replace(make_player(f"{club_id}_p1", accuracy=70, power=66, dodge=58, catch=54), club_id=club_id, newcomer=False, age=22),
            replace(make_player(f"{club_id}_p2", accuracy=63, power=61, dodge=67, catch=64), club_id=club_id, newcomer=True, age=19),
        ]
        for club_id in clubs
    }
    for club_id, club in clubs.items():
        save_club(conn, club, rosters[club_id])

    league = League(
        league_id="league_main",
        name="Main League",
        conferences=(Conference("conf_main", "Main", tuple(clubs.keys())),),
    )
    season = create_season("season_2026", 2026, league, root_seed=5150)
    save_season(conn, season)

    standings = [
        StandingsRow("club_a", wins=3, losses=0, draws=0, elimination_differential=9, points=9),
        StandingsRow("club_b", wins=2, losses=1, draws=0, elimination_differential=3, points=6),
        StandingsRow("club_c", wins=1, losses=2, draws=0, elimination_differential=-4, points=3),
        StandingsRow("club_d", wins=0, losses=3, draws=0, elimination_differential=-8, points=0),
    ]
    save_standings(conn, season.season_id, standings)
    conn.commit()

    loaded_clubs = load_clubs(conn)
    loaded_rosters = load_all_rosters(conn)
    loaded_season = load_season(conn, season.season_id)
    loaded_standings = load_standings(conn, season.season_id)

    assert loaded_clubs == clubs
    assert loaded_rosters == rosters
    assert loaded_season == season
    assert loaded_standings == standings


def test_playoff_bracket_format_and_outcome_round_trip():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_schema(conn)
    standings = [
        StandingsRow("club_a", 5, 0, 0, 10, 15),
        StandingsRow("club_b", 4, 1, 0, 7, 12),
        StandingsRow("club_c", 3, 2, 0, 4, 9),
        StandingsRow("club_d", 2, 3, 0, 1, 6),
    ]
    bracket, matches = create_semifinal_bracket("season_1", standings, week=6)
    outcome = outcome_from_final(
        bracket,
        final_match_id="season_1_p_final",
        home_club_id="club_a",
        away_club_id="club_b",
        winner_club_id="club_b",
    )

    save_season_format(conn, "season_1", "top4_single_elimination")
    save_playoff_bracket(conn, bracket)
    save_season_outcome(conn, outcome)

    from dodgeball_sim.persistence import load_playoff_bracket

    assert load_season_format(conn, "season_1") == "top4_single_elimination"
    assert load_playoff_bracket(conn, "season_1").seeds == ("club_a", "club_b", "club_c", "club_d")
    assert load_season_outcome(conn, "season_1").champion_club_id == "club_b"
    assert [match.week for match in matches] == [6, 6]
