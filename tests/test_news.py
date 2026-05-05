from dodgeball_sim.news import MatchdayResult, generate_matchday_news
from dodgeball_sim.records import RecordBroken
from dodgeball_sim.rivalries import RivalryRecord


def test_generate_matchday_news_prioritizes_record_upset_and_rivalry() -> None:
    headlines = generate_matchday_news(
        [
            MatchdayResult(
                match_id="m1",
                season_id="season_2030",
                week=4,
                winner_club_id="aurora",
                winner_club_name="Aurora Arcs",
                loser_club_id="blaze",
                loser_club_name="Blaze Battalion",
                winner_score=4,
                loser_score=3,
                winner_pre_match_overall=73.0,
                loser_pre_match_overall=84.0,
                flashpoint_text="the benches nearly cleared after a final-round catch",
            )
        ],
        [
            RecordBroken(
                record_type="career_eliminations",
                holder_id="p7",
                holder_type="player",
                holder_name="Mara Keene",
                previous_holder_id="p1",
                previous_value=90,
                new_value=91,
                set_in_season="season_2030",
            )
        ],
        [
            RivalryRecord(
                club_a_id="aurora",
                club_b_id="blaze",
                a_wins=5,
                b_wins=5,
                total_meetings=10,
                total_margin=12,
                playoff_meetings=2,
                championship_meetings=1,
                defining_moments=("old overtime classic",),
            )
        ],
    )

    assert [headline.category for headline in headlines] == [
        "record_broken",
        "big_upset",
        "rivalry_flashpoint",
    ]
    assert "Mara Keene" in headlines[0].text
    assert "Aurora Arcs" in headlines[1].text
    assert "Blaze Battalion" in headlines[1].text
    assert "benches nearly cleared" in headlines[2].text
    assert "{" not in "".join(headline.text for headline in headlines)


def test_generate_matchday_news_falls_back_to_milestone_and_recap() -> None:
    headlines = generate_matchday_news(
        [
            MatchdayResult(
                match_id="m2",
                season_id="season_2031",
                week=1,
                winner_club_id="comets",
                winner_club_name="Comet Circuit",
                loser_club_id="nova",
                loser_club_name="Nova Drift",
                winner_score=5,
                loser_score=2,
                winner_pre_match_overall=79.0,
                loser_pre_match_overall=78.5,
                milestone_player_id="rook1",
                milestone_player_name="Jules Frost",
                milestone_label="eliminations",
                milestone_value=100,
                rookie_player_id="rook1",
                rookie_player_name="Jules Frost",
                rookie_club_name="Comet Circuit",
            )
        ],
        [],
        [],
    )

    assert len(headlines) == 3
    assert [headline.category for headline in headlines] == [
        "player_milestone",
        "rookie_debut",
        "match_recap",
    ]
    assert "Jules Frost" in headlines[0].text
    assert "{" not in "".join(headline.text for headline in headlines)
    assert any(text in headlines[2].text for text in ("Comet Circuit", "Nova Drift"))


def test_generate_matchday_news_template_selection_is_deterministic() -> None:
    result = MatchdayResult(
        match_id="m3",
        season_id="season_2032",
        week=2,
        winner_club_id="atlas",
        winner_club_name="Atlas Surge",
        loser_club_id="circuit",
        loser_club_name="Circuit Hawks",
        winner_score=4,
        loser_score=1,
        winner_pre_match_overall=80.0,
        loser_pre_match_overall=79.0,
    )

    first = generate_matchday_news([result], [], [])
    second = generate_matchday_news([result], [], [])

    assert [headline.text for headline in first] == [headline.text for headline in second]
