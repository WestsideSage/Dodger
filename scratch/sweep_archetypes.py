import sqlite3
import collections
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import create_schema, load_clubs, load_season, load_all_rosters, load_standings, save_career_state_cursor
from dodgeball_sim.game_loop import simulate_scheduled_match, current_week, recompute_regular_season_standings
from dodgeball_sim.offseason_ceremony import finalize_season, initialize_manager_offseason, begin_next_season
from dodgeball_sim.career_state import CareerStateCursor, CareerState
from dodgeball_sim.playoffs import create_semifinal_bracket, create_final_match, outcome_from_final
from dodgeball_sim.persistence import save_playoff_bracket, save_season_outcome

def simulate_playoff_match_until_winner(conn, m, clubs, rosters, base_seed, difficulty):
    attempt = 0
    while True:
        record = simulate_scheduled_match(
            conn,
            scheduled=m,
            clubs=clubs,
            rosters=rosters,
            root_seed=base_seed + attempt,
            difficulty=difficulty,
            record_engine_match=False
        )
        if record.result.winner_team_id is not None:
            return record
        attempt += 1

def run_sweep():
    # 1. Initialize an in-memory DB
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    
    # Manually assign fully diverse, balanced archetypes to each club
    conn.execute("UPDATE clubs SET program_archetype = 'Balanced Rebuild' WHERE club_id = 'aurora'")
    conn.execute("UPDATE clubs SET program_archetype = 'Power Throwers' WHERE club_id = 'lunar'")
    conn.execute("UPDATE clubs SET program_archetype = 'Defensive Specialist' WHERE club_id = 'northwood'")
    conn.execute("UPDATE clubs SET program_archetype = 'Development Factory' WHERE club_id = 'harbor'")
    conn.execute("UPDATE clubs SET program_archetype = 'Contender' WHERE club_id = 'granite'")
    conn.execute("UPDATE clubs SET program_archetype = 'Aging Veterans' WHERE club_id = 'solstice'")
    conn.commit()

    print("Initial Club Archetypes (assigned for balanced sweep):")
    clubs = load_clubs(conn)
    for club_id, club in clubs.items():
        print(f"  {club.name} ({club_id}): {club.program_archetype}")

    champions = []
    champion_archetypes = []

    # 2. Run 50 seasons
    num_seasons = 50
    cursor = CareerStateCursor(
        state=CareerState.SEASON_ACTIVE_PRE_MATCH,
        season_number=1,
        week=1,
        offseason_beat_index=0,
        match_id=None
    )

    for season_num in range(1, num_seasons + 1):
        season_id = f"season_{season_num}"
        season = load_season(conn, season_id)
        clubs = load_clubs(conn)
        rosters = load_all_rosters(conn)
        
        # Simulate regular season matches
        for week in range(1, season.total_weeks() + 1):
            for match in season.matches_for_week(week):
                simulate_scheduled_match(
                    conn,
                    scheduled=match,
                    clubs=clubs,
                    rosters=rosters,
                    root_seed=12345 + season_num * 100 + week,
                    difficulty="pro",
                    record_engine_match=False
                )
        
        # Recompute regular season standings
        recompute_regular_season_standings(conn, season)
        standings = load_standings(conn, season_id)
        
        # Semifinals (week=6)
        bracket, semi_matches = create_semifinal_bracket(season_id, standings, week=6)
        save_playoff_bracket(conn, bracket)
        
        # Simulate semis
        winners_by_match_id = {}
        for m in semi_matches:
            record = simulate_playoff_match_until_winner(
                conn,
                m=m,
                clubs=clubs,
                rosters=rosters,
                base_seed=12345 + season_num * 200,
                difficulty="pro"
            )
            winners_by_match_id[m.match_id] = record.result.winner_team_id
            
        # Final match (week=7)
        bracket, final_match = create_final_match(bracket, winners_by_match_id, week=7)
        final_record = simulate_playoff_match_until_winner(
            conn,
            m=final_match,
            clubs=clubs,
            rosters=rosters,
            base_seed=12345 + season_num * 300,
            difficulty="pro"
        )
        
        # Outcomes
        outcome = outcome_from_final(
            bracket,
            final_match_id=final_match.match_id,
            home_club_id=final_match.home_club_id,
            away_club_id=final_match.away_club_id,
            winner_club_id=final_record.result.winner_team_id
        )
        save_season_outcome(conn, outcome)
        
        # Determine champion
        champ_id = outcome.champion_club_id
        champ_club = clubs[champ_id]
        champ_archetype = champ_club.program_archetype
        
        champions.append(champ_id)
        champion_archetypes.append(champ_archetype)
        
        # Finalize and offseason development
        finalize_season(conn, season, rosters)
        updated_rosters = initialize_manager_offseason(conn, season, clubs, rosters, root_seed=12345)
        
        # Advance state to next season
        cursor = begin_next_season(conn, cursor, clubs)
        
        print(f"Season {season_num} Champion: {champ_club.name} ({champ_archetype})")

    # 3. Aggregate results
    print("\nSweep Complete! Championship Distribution:")
    club_counts = collections.Counter(champions)
    for cid, count in club_counts.most_common():
        percentage = (count / num_seasons) * 100
        print(f"  {clubs[cid].name}: {count} titles ({percentage:.1f}%)")

    print("\nArchetype Title Distribution:")
    arch_counts = collections.Counter(champion_archetypes)
    for arch, count in arch_counts.most_common():
        percentage = (count / num_seasons) * 100
        print(f"  {arch}: {count} titles ({percentage:.1f}%)")
        assert percentage <= 50.0, f"Error: Archetype {arch} won {percentage:.1f}% of titles (exceeding 50% limit)!"

    # Ensure at least 3 distinct archetypes win titles
    distinct_arches = len(arch_counts)
    assert distinct_arches >= 3, f"Error: Only {distinct_arches} distinct archetypes won titles (expected >= 3)!"

    print("\nSUCCESS: Parity verification sweep passed green. At least 3 distinct archetypes won, and no single archetype dominated more than 50% of titles.")

if __name__ == "__main__":
    run_sweep()
