"""Phase 1 — canonical fielded-6 (D1).

The week briefing and the match sim must consume ONE canonical fielded-6.
Before this phase, a fresh build-a-club career saved its default lineup as raw
roster order (all players), so:
  * the sim fielded the first-6 in roster order (a weak six), while
  * the briefing summed the *whole* roster for its matchup edge,
producing a FAVORITE headline over a lineup that actually got shut out.

These tests pin the fix: the user club's default lineup is the best-by-role/OVR
six (``optimize_ai_lineup``), and the briefing's fielded-6 equals exactly what
the sim activates.
"""

from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_build_a_club_career
from dodgeball_sim.command_center import (
    _lineup_recommendation,
    build_command_center_state,
    build_default_weekly_plan,
)
from dodgeball_sim.lineup import (
    STARTERS_COUNT,
    LineupResolver,
    optimize_ai_lineup,
)
from dodgeball_sim.persistence import (
    create_schema,
    load_all_rosters,
    load_lineup_default,
)

from .factories import make_player


def _roster_of_ten():
    """Ten players in deliberately WEAK-first order.

    Roster order puts the worst players first, so a naive 'first six in roster
    order' fields the weakest six while the strongest sit on the bench — the
    fresh build-a-club shape that produced the FAVORITE-then-shutout bug.
    """
    return [
        make_player(f"p{i}", accuracy=40 + i * 5, power=40 + i * 5, dodge=40 + i * 5, catch=40 + i * 5)
        for i in range(10)
    ]


def _build_club_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_build_a_club_career(
        conn,
        club_name="Testers FC",
        primary_color="#123456",
        secondary_color="#abcdef",
        venue_name="Test Arena",
        home_region="Testville",
        tagline="We test.",
        root_seed=20260529,
    )
    conn.commit()
    return conn


def _player_club_id(conn: sqlite3.Connection) -> str:
    return build_command_center_state(conn)["player_club_id"]


def _player_roster(conn: sqlite3.Connection):
    club_id = _player_club_id(conn)
    return list(load_all_rosters(conn)[club_id])


def test_fresh_club_default_lineup_is_optimized_not_roster_order():
    conn = _build_club_conn()
    club_id = _player_club_id(conn)
    roster = _player_roster(conn)

    saved_default = load_lineup_default(conn, club_id)
    assert saved_default is not None

    # The fielded six must be the best-by-role/OVR six, not whatever order the
    # roster happened to be built in.
    assert saved_default[:STARTERS_COUNT] == optimize_ai_lineup(roster)[:STARTERS_COUNT]


def test_briefing_fielded_six_matches_sim_active_starters_fresh_club():
    conn = _build_club_conn()
    club_id = _player_club_id(conn)
    roster = _player_roster(conn)
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state)

    fielded = plan["lineup"]["player_ids"]
    # The briefing must field exactly six — not sum the whole roster.
    assert len(fielded) == STARTERS_COUNT

    # And those six must be exactly what the sim activates from the same saved
    # default (single canonical resolver path).
    resolver = LineupResolver()
    sim_active = resolver.active_starters(
        resolver.resolve(roster, load_lineup_default(conn, club_id), None)
    )
    assert fielded == sim_active


def test_lineup_recommendation_caps_to_fielded_six_over_large_roster():
    """The briefing must field exactly six, not sum a 7+ player roster.

    With a roster-order default of all ten players, the old recommendation
    returned all ten (inflating the matchup edge) while the sim fielded only
    the first six. The fielded-6 must be capped and equal to what the sim
    activates from the same default.
    """
    roster = _roster_of_ten()
    roster_order_default = [p.id for p in roster]

    rec = _lineup_recommendation(roster, roster_order_default, "Balanced")
    assert len(rec["player_ids"]) == STARTERS_COUNT

    resolver = LineupResolver()
    sim_active = resolver.active_starters(
        resolver.resolve(roster, roster_order_default, None)
    )
    assert rec["player_ids"] == sim_active


def test_lineup_recommendation_no_default_uses_optimized_six():
    """With no saved default, the recommendation falls back to the best-by-role
    /OVR six (optimize_ai_lineup), matching the sim's fresh-club default."""
    roster = _roster_of_ten()
    rec = _lineup_recommendation(roster, None, "Balanced")
    assert rec["player_ids"] == optimize_ai_lineup(roster)[:STARTERS_COUNT]


def test_optimized_fielded_six_materially_outperforms_roster_order_six():
    """Cause -> effect: fielding the optimized six actually changes the result.

    Reproduces the synthesis's traceability failure on the rec path (which rewards
    OVR): a weak roster-order six gets shut out / loses, while the optimized six
    (the new fresh-club default) wins decisively. This proves the fix *matters*,
    not merely that the briefing and sim agree on which six are fielded.
    """
    from dodgeball_sim.franchise import simulate_match
    from dodgeball_sim.league import Club
    from dodgeball_sim.models import CoachPolicy

    # Home roster: six weak players first (roster order), four elites on the bench.
    home_roster = [
        make_player(f"weak{i}", accuracy=42, power=42, dodge=42, catch=42)
        for i in range(6)
    ] + [
        make_player(f"elite{i}", accuracy=92, power=92, dodge=92, catch=92)
        for i in range(4)
    ]
    away_roster = [
        make_player(f"away{i}", accuracy=58, power=58, dodge=58, catch=58)
        for i in range(6)
    ]
    home_club = Club("home", "Home", "red/white", "North", 2020, CoachPolicy())
    away_club = Club("away", "Away", "blue/black", "South", 2020, CoachPolicy())

    def _scheduled(seed: int):
        return type(
            "Scheduled",
            (),
            {
                "match_id": f"season_2026_w{seed:02d}_home_vs_away",
                "season_id": "season_2026",
                "week": seed,
                "home_club_id": "home",
                "away_club_id": "away",
            },
        )()

    def _run(home_default):
        survivors = 0
        home_wins = 0
        for seed in range(1, 13):
            _, season_result = simulate_match(
                scheduled=_scheduled(seed),
                home_club=home_club,
                away_club=away_club,
                home_roster=home_roster,
                away_roster=away_roster,
                root_seed=4242 + seed,
                home_lineup_default=home_default,
            )
            survivors += season_result.home_survivors
            home_wins += 1 if season_result.winner_club_id == "home" else 0
        return survivors, home_wins

    roster_order = [p.id for p in home_roster]  # weak six field first
    optimized = optimize_ai_lineup(home_roster)  # elite six field first

    weak_survivors, weak_wins = _run(roster_order)
    strong_survivors, strong_wins = _run(optimized)

    # Aggregated over a dozen seeds the optimized lineup must clearly outperform
    # the weak roster-order six — both in survivors and wins.
    assert strong_survivors > weak_survivors
    assert strong_wins > weak_wins


def test_briefing_summary_players_match_player_ids():
    conn = _build_club_conn()
    state = build_command_center_state(conn)
    plan = build_default_weekly_plan(state)

    summary_ids = [p["id"] for p in plan["lineup"]["players"]]
    assert summary_ids == plan["lineup"]["player_ids"]
    assert len(summary_ids) == STARTERS_COUNT
