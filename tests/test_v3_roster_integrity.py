from __future__ import annotations

import sqlite3

from dodgeball_sim.franchise import build_match_team_snapshot, extract_match_stats, simulate_match
from dodgeball_sim.league import Club
from dodgeball_sim.lineup import STARTERS_COUNT
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.manager_gui import ManagerModeApp, initialize_manager_career, sign_prospect_to_club
from dodgeball_sim.persistence import (
    create_schema,
    fetch_roster_snapshot,
    load_all_rosters,
    load_clubs,
    load_prospect_pool,
    load_season,
)

from .factories import make_player


def _scheduled_match():
    return type(
        "Scheduled",
        (),
        {
            "match_id": "season_2026_w01_home_vs_away",
            "season_id": "season_2026",
            "week": 1,
            "home_club_id": "home",
            "away_club_id": "away",
        },
    )()


def test_match_uses_only_active_starters_when_roster_exceeds_six():
    home_roster = [make_player(f"home_{i}", accuracy=60 + i, power=60, dodge=60, catch=60) for i in range(1, 10)]
    away_roster = [make_player(f"away_{i}", accuracy=60 + i, power=60, dodge=60, catch=60) for i in range(1, 10)]
    home_club = Club("home", "Home Club", "red/white", "North", 2020, CoachPolicy())
    away_club = Club("away", "Away Club", "blue/black", "South", 2020, CoachPolicy())

    record, season_result = simulate_match(
        scheduled=_scheduled_match(),
        home_club=home_club,
        away_club=away_club,
        home_roster=home_roster,
        away_roster=away_roster,
        root_seed=4242,
    )

    box = record.result.box_score["teams"]
    assert len(record.home_active_player_ids) == STARTERS_COUNT
    assert len(record.away_active_player_ids) == STARTERS_COUNT
    assert len(box["home"]["players"]) == STARTERS_COUNT
    assert len(box["away"]["players"]) == STARTERS_COUNT
    assert season_result.home_survivors <= STARTERS_COUNT
    assert season_result.away_survivors <= STARTERS_COUNT


def test_build_match_team_snapshot_caps_full_lineup_to_active_starters():
    roster = [make_player(f"home_{i}", accuracy=60 + i, power=60, dodge=60, catch=60) for i in range(1, 10)]
    club = Club("home", "Home Club", "red/white", "North", 2020, CoachPolicy())

    team = build_match_team_snapshot(club, roster, [player.id for player in roster])

    assert len(team.players) == STARTERS_COUNT
    assert [player.id for player in team.players] == [player.id for player in roster[:STARTERS_COUNT]]


def test_bench_players_do_not_receive_match_stats():
    home_roster = [make_player(f"home_{i}", accuracy=60 + i, power=60, dodge=60, catch=60) for i in range(1, 10)]
    away_roster = [make_player(f"away_{i}", accuracy=60 + i, power=60, dodge=60, catch=60) for i in range(1, 10)]
    home_club = Club("home", "Home Club", "red/white", "North", 2020, CoachPolicy())
    away_club = Club("away", "Away Club", "blue/black", "South", 2020, CoachPolicy())

    record, _ = simulate_match(
        scheduled=_scheduled_match(),
        home_club=home_club,
        away_club=away_club,
        home_roster=home_roster,
        away_roster=away_roster,
        root_seed=4242,
    )

    stats = extract_match_stats(record, home_roster, away_roster)
    bench_player_ids = {player.id for player in home_roster[STARTERS_COUNT:]} | {
        player.id for player in away_roster[STARTERS_COUNT:]
    }
    assert bench_player_ids
    assert all(player_id not in stats for player_id in bench_player_ids)


def test_persisted_roster_snapshot_marks_active_and_bench_players():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_manager_career(conn, "aurora", root_seed=20260426)
    prospect = load_prospect_pool(conn, class_year=1)[0]
    signed = sign_prospect_to_club(conn, prospect, "aurora", season_num=1)

    app = ManagerModeApp.__new__(ManagerModeApp)
    app.conn = conn
    app.clubs = load_clubs(conn)
    app.rosters = load_all_rosters(conn)
    app.season = load_season(conn, "season_1")
    match = next(match for match in app.season.scheduled_matches if match.home_club_id == "aurora")

    app._simulate_match_for_schedule_row(match)

    snapshot = fetch_roster_snapshot(conn, match.match_id, "aurora")
    by_id = {player["id"]: player for player in snapshot}
    assert len([player for player in snapshot if player["match_role"] == "active"]) == STARTERS_COUNT
    assert by_id[signed.id]["match_role"] == "bench"
