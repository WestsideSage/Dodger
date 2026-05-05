from dodgeball_sim.rivalries import (
    RivalryMatchResult,
    RivalryRecord,
    compute_rivalry_score,
    update_rivalry,
)


def test_update_rivalry_tracks_wins_draws_and_moments() -> None:
    record = RivalryRecord(club_a_id="aurora", club_b_id="blaze")

    updated = update_rivalry(
        record,
        RivalryMatchResult(
            match_id="m1",
            season_id="season_2030",
            club_a_id="aurora",
            club_b_id="blaze",
            winner_club_id="aurora",
            score_margin=1,
            was_playoff=True,
            notable_moment="a one-player comeback sealed the match",
        ),
    )

    assert updated.a_wins == 1
    assert updated.b_wins == 0
    assert updated.draws == 0
    assert updated.total_meetings == 1
    assert updated.total_margin == 1
    assert updated.playoff_meetings == 1
    assert updated.last_winner_club_id == "aurora"
    assert updated.defining_moments == ("a one-player comeback sealed the match",)


def test_compute_rivalry_score_rewards_close_frequent_high_stakes_series() -> None:
    heated = RivalryRecord(
        club_a_id="aurora",
        club_b_id="blaze",
        a_wins=5,
        b_wins=4,
        total_meetings=9,
        total_margin=11,
        playoff_meetings=3,
        championship_meetings=1,
        defining_moments=("late catch", "cup clincher"),
    )
    mild = RivalryRecord(
        club_a_id="aurora",
        club_b_id="comets",
        a_wins=4,
        b_wins=0,
        total_meetings=4,
        total_margin=26,
    )

    assert compute_rivalry_score(heated) > compute_rivalry_score(mild)
    assert compute_rivalry_score(heated) > 70


def test_update_rivalry_accepts_reversed_match_order() -> None:
    record = RivalryRecord(club_a_id="aurora", club_b_id="blaze", a_wins=2, b_wins=1)

    updated = update_rivalry(
        record,
        RivalryMatchResult(
            match_id="m2",
            season_id="season_2031",
            club_a_id="blaze",
            club_b_id="aurora",
            winner_club_id="blaze",
            score_margin=2,
            was_championship=True,
        ),
    )

    assert updated.a_wins == 2
    assert updated.b_wins == 2
    assert updated.championship_meetings == 1
    assert updated.last_winner_club_id == "blaze"
