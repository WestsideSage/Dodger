from dodgeball_sim.playoffs import (
    create_final_match,
    create_semifinal_bracket,
    outcome_from_final,
    playoff_stage_label,
    top_four_seeds,
)
from dodgeball_sim.season import StandingsRow


def test_top_four_seeds_use_standings_tiebreakers():
    standings = [
        StandingsRow("club_b", wins=3, losses=0, draws=0, elimination_differential=4, points=9),
        StandingsRow("club_a", wins=3, losses=0, draws=0, elimination_differential=4, points=9),
        StandingsRow("club_c", wins=2, losses=1, draws=0, elimination_differential=8, points=6),
        StandingsRow("club_d", wins=2, losses=1, draws=0, elimination_differential=2, points=6),
        StandingsRow("club_e", wins=1, losses=2, draws=0, elimination_differential=9, points=3),
    ]

    assert top_four_seeds(standings) == ("club_a", "club_b", "club_c", "club_d")


def test_create_semifinal_bracket_higher_seed_hosts():
    standings = [
        StandingsRow("one", 5, 0, 0, 10, 15),
        StandingsRow("two", 4, 1, 0, 8, 12),
        StandingsRow("three", 3, 2, 0, 6, 9),
        StandingsRow("four", 2, 3, 0, 4, 6),
    ]

    bracket, matches = create_semifinal_bracket("season_1", standings, week=6)

    assert bracket.seeds == ("one", "two", "three", "four")
    assert [match.match_id for match in matches] == ["season_1_p_r1_m1", "season_1_p_r1_m2"]
    assert (matches[0].home_club_id, matches[0].away_club_id) == ("one", "four")
    assert (matches[1].home_club_id, matches[1].away_club_id) == ("two", "three")


def test_create_final_match_higher_remaining_seed_hosts_and_outcome_uses_final_winner():
    standings = [
        StandingsRow("one", 5, 0, 0, 10, 15),
        StandingsRow("two", 4, 1, 0, 8, 12),
        StandingsRow("three", 3, 2, 0, 6, 9),
        StandingsRow("four", 2, 3, 0, 4, 6),
    ]
    bracket, _matches = create_semifinal_bracket("season_1", standings, week=6)

    bracket, final = create_final_match(
        bracket,
        {"season_1_p_r1_m1": "four", "season_1_p_r1_m2": "two"},
        week=7,
    )
    outcome = outcome_from_final(
        bracket,
        final_match_id=final.match_id,
        home_club_id=final.home_club_id,
        away_club_id=final.away_club_id,
        winner_club_id="four",
    )

    assert (final.home_club_id, final.away_club_id) == ("two", "four")
    assert playoff_stage_label("season_1", final.match_id) == "Playoff Final"
    assert outcome.champion_club_id == "four"
    assert outcome.runner_up_club_id == "two"
    assert outcome.champion_source == "playoff_final"
