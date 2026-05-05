from dodgeball_sim.records import (
    CareerStats,
    LeagueRecord,
    TeamRecordStats,
    UpsetResult,
    build_individual_records,
    build_team_records,
    check_records_broken,
)


def test_build_individual_records_picks_correct_leaders() -> None:
    records = build_individual_records(
        [
            CareerStats(
                player_id="p1",
                player_name="Rin Vale",
                career_eliminations=91,
                career_catches=30,
                career_dodges=44,
                seasons_at_one_club=4,
                championships=1,
            ),
            CareerStats(
                player_id="p2",
                player_name="Mara Keene",
                career_eliminations=88,
                career_catches=37,
                career_dodges=51,
                seasons_at_one_club=6,
                championships=3,
            ),
        ],
        season_id="season_2030",
    )

    assert records["career_eliminations"].holder_id == "p1"
    assert records["career_catches"].holder_id == "p2"
    assert records["career_dodges"].holder_id == "p2"
    assert records["most_seasons_at_one_club"].value == 6
    assert records["most_championships"].holder_name == "Mara Keene"


def test_build_team_records_includes_biggest_upset() -> None:
    records = build_team_records(
        [
            TeamRecordStats(club_id="c1", club_name="Aurora", titles=2, unbeaten_run=7),
            TeamRecordStats(club_id="c2", club_name="Blaze", titles=4, unbeaten_run=5),
        ],
        [
            UpsetResult(
                match_id="m1",
                season_id="season_2029",
                winner_club_id="c1",
                winner_club_name="Aurora",
                loser_club_id="c2",
                loser_club_name="Blaze",
                winner_overall=73.0,
                loser_overall=84.5,
            )
        ],
        season_id="season_2030",
    )

    assert records["most_titles"].holder_id == "c2"
    assert records["longest_unbeaten_run"].value == 7
    assert records["biggest_upset_win"].value == 11.5
    assert "11.5 OVR underdog" in records["biggest_upset_win"].detail


def test_check_records_broken_reports_only_true_improvements() -> None:
    current_records = {
        "career_eliminations": LeagueRecord(
            record_type="career_eliminations",
            holder_id="old_p1",
            holder_type="player",
            holder_name="Old Guard",
            value=90,
            set_in_season="season_2028",
        ),
        "most_titles": LeagueRecord(
            record_type="most_titles",
            holder_id="old_c1",
            holder_type="club",
            holder_name="Legacy Club",
            value=3,
            set_in_season="season_2027",
        ),
    }

    broken = check_records_broken(
        {
            "season_id": "season_2030",
            "team_stats": [
                TeamRecordStats(club_id="c9", club_name="Nova", titles=4, unbeaten_run=6)
            ],
            "upset_results": [
                UpsetResult(
                    match_id="m9",
                    season_id="season_2030",
                    winner_club_id="c9",
                    winner_club_name="Nova",
                    loser_club_id="c5",
                    loser_club_name="Titans",
                    winner_overall=70.0,
                    loser_overall=81.0,
                )
            ],
        },
        [
            CareerStats(
                player_id="p9",
                player_name="Nova Star",
                career_eliminations=95,
                career_catches=20,
                career_dodges=12,
                seasons_at_one_club=3,
                championships=2,
            )
        ],
        current_records,
    )

    broken_types = [item.record_type for item in broken]
    assert "career_eliminations" in broken_types
    assert "most_titles" in broken_types
    assert "biggest_upset_win" in broken_types
    elimination_record = next(item for item in broken if item.record_type == "career_eliminations")
    assert elimination_record.previous_holder_id == "old_p1"
    assert elimination_record.new_value == 95
