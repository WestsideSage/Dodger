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
