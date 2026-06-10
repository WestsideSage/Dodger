"""Tests for the My Program history endpoints and timeline payloads."""

from dodgeball_sim.persistence import connect
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.league import Club
from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits
from dodgeball_sim.server import get_history_my_program

def test_history_my_program_award_proof():
    conn = connect(":memory:")
    
    club = Club("sea", "Seattle", "blue, green", "Seattle", 2026)
    player = Player(
        id="p_1", name="Alice Smith", age=20, club_id="sea", newcomer=True,
        ratings=PlayerRatings(50,50,50,50,50,50,50,50,50),
        archetype="thrower", traits=PlayerTraits(50,50,50,50)
    )
    
    # We need a 6 player roster for initialize_curated_manager_career
    roster = [player]
    for i in range(2, 7):
        roster.append(Player(
            id=f"p_{i}", name=f"Player {i}", age=20, club_id="sea", newcomer=True,
            ratings=PlayerRatings(50,50,50,50,50,50,50,50,50),
            archetype="thrower", traits=PlayerTraits(50,50,50,50)
        ))

    initialize_curated_manager_career(conn, "sea", 1, custom_club=club, custom_roster=roster)
    
    conn.execute(
        """
        INSERT INTO season_awards (season_id, award_type, player_id, club_id, award_score)
        VALUES (?, ?, ?, ?, ?)
        """,
        (2026, "mvp", "p_1", "sea", 100.0)
    )
    
    conn.execute(
        """
        INSERT INTO player_season_stats (player_id, season_id, club_id, matches, total_eliminations, total_catches_made)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("p_1", 2026, "sea", 12, 45, 10)
    )
    conn.commit()
    
    payload = get_history_my_program("sea", conn)
    timeline = payload["timeline"]

    award_events = [e for e in timeline if e["event_type"] == "award"]
    assert len(award_events) == 1

    award_event = award_events[0]
    assert award_event["holder_name"] == "Alice Smith"
    assert award_event["proof_stat"] == "45 elims across 12 matches that season."


def test_history_my_program_all_time_record_sums_every_season():
    # The glance cell labeled "All-Time Record" must be the career total, not
    # the latest season snapshot (hero.current) it used to render.
    conn = connect(":memory:")

    club = Club("sea", "Seattle", "blue, green", "Seattle", 2026)
    roster = [
        Player(
            id=f"p_{i}", name=f"Player {i}", age=20, club_id="sea", newcomer=True,
            ratings=PlayerRatings(50, 50, 50, 50, 50, 50, 50, 50, 50),
            archetype="thrower", traits=PlayerTraits(50, 50, 50, 50),
        )
        for i in range(1, 7)
    ]
    initialize_curated_manager_career(conn, "sea", 1, custom_club=club, custom_roster=roster)

    conn.execute("DELETE FROM season_standings WHERE club_id = 'sea'")
    for season_id, wins, losses, draws in (
        ("season_1", 3, 1, 1),
        ("season_2", 4, 0, 1),
        ("season_3", 1, 0, 0),  # in-progress season counts too
    ):
        conn.execute(
            """
            INSERT INTO season_standings (season_id, club_id, wins, losses, draws, points)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (season_id, "sea", wins, losses, draws, wins * 3 + draws),
        )
    conn.commit()

    payload = get_history_my_program("sea", conn)
    hero = payload["hero"]

    assert hero["all_time"] == {"wins": 8, "losses": 1, "draws": 2, "seasons": 3}
    # The latest-season snapshot keeps its own meaning.
    assert (hero["current"]["wins"], hero["current"]["losses"], hero["current"]["draws"]) == (1, 0, 0)


def _make_six_player_roster() -> list[Player]:
    return [
        Player(
            id=f"p_{i}", name=f"Player {i}", age=20, club_id="sea", newcomer=True,
            ratings=PlayerRatings(50, 50, 50, 50, 50, 50, 50, 50, 50),
            archetype="thrower", traits=PlayerTraits(50, 50, 50, 50),
        )
        for i in range(1, 7)
    ]


def test_history_my_program_season_10_sorts_after_season_2():
    # season_id is a string ("season_10" < "season_2" lexicographically), so a
    # string ORDER BY picks the wrong "latest" season from season 10 onward.
    # hero.current must be the numerically latest season and hero.season_1 the
    # numerically earliest; First Win must come from the numerically earliest
    # winning season, not the lexicographically smallest.
    conn = connect(":memory:")
    club = Club("sea", "Seattle", "blue, green", "Seattle", 2026)
    initialize_curated_manager_career(
        conn, "sea", 1, custom_club=club, custom_roster=_make_six_player_roster()
    )

    conn.execute("DELETE FROM season_standings WHERE club_id = 'sea'")
    for season_id, wins in (("season_2", 3), ("season_10", 7)):
        conn.execute(
            """
            INSERT INTO season_standings (season_id, club_id, wins, losses, draws, points)
            VALUES (?, ?, ?, 0, 0, ?)
            """,
            (season_id, "sea", wins, wins * 3),
        )
    for match_id, season_id, week in (
        ("m_s10_w1", "season_10", 1),
        ("m_s2_w5", "season_2", 5),
    ):
        conn.execute(
            """
            INSERT INTO match_records (
                match_id, season_id, week, home_club_id, away_club_id,
                winner_club_id, home_roster_hash, away_roster_hash,
                config_version, ruleset_version, seed,
                event_log_hash, final_state_hash
            ) VALUES (?, ?, ?, 'sea', 'opp', 'sea', 'h', 'a', 'v1', 'r1', 1, 'e', 'f')
            """,
            (match_id, season_id, week),
        )
    conn.commit()

    payload = get_history_my_program("sea", conn)
    hero = payload["hero"]

    assert hero["season_1"]["season_label"] == "season_2"
    assert hero["current"]["season_label"] == "season_10"
    assert hero["current"]["wins"] == 7

    first_win = [e for e in payload["timeline"] if e["label"] == "First Win"]
    assert len(first_win) == 1
    assert (first_win[0]["season"], first_win[0]["week"]) == ("season_2", 5)
