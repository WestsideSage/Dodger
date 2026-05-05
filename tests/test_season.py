from __future__ import annotations

from dataclasses import replace

from dodgeball_sim.franchise import create_season, simulate_full_season, trim_ai_roster_for_offseason
from dodgeball_sim.league import Club, Conference, League
from dodgeball_sim.models import CoachPolicy, PlayerTraits

from .factories import make_player


def test_full_round_robin_standings_balance_wins_and_losses():
    clubs = {
        club_id: Club(
            club_id=club_id,
            name=club_id.replace("_", " ").title(),
            colors="red/white",
            home_region="Region",
            founded_year=2020,
            coach_policy=CoachPolicy(),
        )
        for club_id in ("club_a", "club_b", "club_c", "club_d")
    }
    rosters = {
        club_id: [
            replace(make_player(f"{club_id}_p1", accuracy=75, power=68, dodge=58, catch=54), club_id=club_id),
            replace(make_player(f"{club_id}_p2", accuracy=67, power=62, dodge=64, catch=61), club_id=club_id),
            replace(make_player(f"{club_id}_p3", accuracy=60, power=58, dodge=70, catch=66), club_id=club_id),
        ]
        for club_id in clubs
    }
    league = League(
        league_id="league_main",
        name="Main League",
        conferences=(Conference("conf_main", "Main", tuple(clubs.keys())),),
    )
    season = create_season("season_2026", 2026, league, root_seed=10101)

    records, results, standings = simulate_full_season(
        season=season,
        clubs=clubs,
        rosters=rosters,
        root_seed=10101,
    )

    assert len(records) == 6
    assert len(results) == 6
    assert len(standings) == 4
    assert sum(row.wins for row in standings) == sum(row.losses for row in standings)
    assert all(row.wins + row.losses + row.draws == 3 for row in standings)


def test_trim_ai_roster_keeps_young_high_potential_over_raw_overall():
    starters = [
        make_player(f"starter_{index}", accuracy=75, power=75, dodge=75, catch=75)
        for index in range(6)
    ]
    veteran_keep = replace(
        make_player("veteran_keep", accuracy=64, power=64, dodge=64, catch=64),
        age=28,
    )
    young_high_potential = replace(
        make_player("young_high_potential", accuracy=55, power=55, dodge=55, catch=55),
        age=19,
        traits=PlayerTraits(potential=95),
    )
    young_low_potential = replace(
        make_player("young_low_potential", accuracy=58, power=58, dodge=58, catch=58),
        age=19,
        traits=PlayerTraits(potential=40),
    )
    older_low_value = replace(
        make_player("older_low_value", accuracy=45, power=45, dodge=45, catch=45),
        age=33,
    )
    roster = starters + [veteran_keep, young_high_potential, young_low_potential, older_low_value]

    kept, released = trim_ai_roster_for_offseason(roster, max_size=8)

    assert len(kept) == 8
    assert {player.id for player in released} == {"older_low_value", "young_low_potential"}
    assert "young_high_potential" in {player.id for player in kept}
