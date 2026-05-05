from __future__ import annotations

from dodgeball_sim.career import (
    aggregate_career,
    build_signature_moment,
    evaluate_hall_of_fame,
)


def test_aggregate_career_sums_season_totals_and_keeps_top_signature_moments():
    summary = aggregate_career(
        player_id="player_9",
        player_name="Mina Vale",
        season_rows=[
            {
                "season_id": "2026",
                "matches": 8,
                "total_eliminations": 18,
                "total_catches_made": 7,
                "total_dodges_successful": 9,
                "total_times_eliminated": 6,
                "champion": True,
            },
            {
                "season_id": "2027",
                "matches": 9,
                "total_eliminations": 21,
                "total_catches_made": 6,
                "total_dodges_successful": 11,
                "total_times_eliminated": 8,
                "champion": False,
            },
        ],
        awards=[
            {"award": "MVP"},
            {"award": "All-Star"},
        ],
        signature_moments=[
            build_signature_moment(
                season_id="2026",
                match_id="m1",
                label="Final Stand",
                description="Closed the championship with two catches.",
                leverage=1.9,
                catches=2,
                eliminations=1,
                clutch_bonus=2.0,
            ),
            build_signature_moment(
                season_id="2027",
                match_id="m8",
                label="Comeback Surge",
                description="Rallied from down three players.",
                leverage=1.4,
                eliminations=3,
                dodges=2,
            ),
        ],
    )

    assert summary.seasons_played == 2
    assert summary.championships == 1
    assert summary.awards_won == 2
    assert summary.total_matches == 17
    assert summary.total_eliminations == 39
    assert summary.total_catches_made == 13
    assert summary.total_dodges_successful == 20
    assert summary.total_times_eliminated == 14
    assert summary.peak_eliminations == 21
    assert summary.signature_moments[0].label == "Final Stand"


def test_evaluate_hall_of_fame_inducts_decorated_star():
    summary = aggregate_career(
        player_id="legend_1",
        player_name="Sol Vega",
        season_rows=[
            {
                "season_id": "2024",
                "matches": 9,
                "total_eliminations": 16,
                "total_catches_made": 6,
                "total_dodges_successful": 8,
                "total_times_eliminated": 5,
                "champion": True,
            },
            {
                "season_id": "2025",
                "matches": 9,
                "total_eliminations": 14,
                "total_catches_made": 7,
                "total_dodges_successful": 10,
                "total_times_eliminated": 6,
                "champion": False,
            },
            {
                "season_id": "2026",
                "matches": 10,
                "total_eliminations": 19,
                "total_catches_made": 8,
                "total_dodges_successful": 11,
                "total_times_eliminated": 6,
                "champion": True,
            },
            {
                "season_id": "2027",
                "matches": 10,
                "total_eliminations": 17,
                "total_catches_made": 5,
                "total_dodges_successful": 9,
                "total_times_eliminated": 7,
                "champion": False,
            },
            {
                "season_id": "2028",
                "matches": 10,
                "total_eliminations": 15,
                "total_catches_made": 6,
                "total_dodges_successful": 8,
                "total_times_eliminated": 6,
                "champion": False,
            },
            {
                "season_id": "2029",
                "matches": 10,
                "total_eliminations": 18,
                "total_catches_made": 7,
                "total_dodges_successful": 9,
                "total_times_eliminated": 6,
                "champion": False,
            },
        ],
        awards=[{"award": "MVP"}, {"award": "Finals MVP"}],
        signature_moments=[
            build_signature_moment(
                season_id="2026",
                match_id="final",
                label="Title Clincher",
                description="Won the final with a last-player double out.",
                leverage=2.0,
                eliminations=2,
                catches=1,
                clutch_bonus=3.0,
            )
        ],
    )

    hof = evaluate_hall_of_fame(summary)

    assert hof.eligible is True
    assert hof.inducted is True
    assert hof.score >= hof.threshold
    assert "longevity" in hof.reasons
    assert "championship pedigree" in hof.reasons
    assert "signature moments" in hof.reasons


def test_evaluate_hall_of_fame_rejects_short_unremarkable_resume():
    summary = aggregate_career(
        player_id="depth_1",
        player_name="Pax Rowan",
        season_rows=[
            {
                "season_id": "2028",
                "matches": 6,
                "total_eliminations": 8,
                "total_catches_made": 1,
                "total_dodges_successful": 3,
                "total_times_eliminated": 7,
                "champion": False,
            },
            {
                "season_id": "2029",
                "matches": 7,
                "total_eliminations": 7,
                "total_catches_made": 2,
                "total_dodges_successful": 4,
                "total_times_eliminated": 8,
                "champion": False,
            },
        ],
    )

    hof = evaluate_hall_of_fame(summary)

    assert hof.eligible is False
    assert hof.inducted is False
    assert hof.score < hof.threshold


def test_build_signature_moment_normalizes_value_and_leverage():
    moment = build_signature_moment(
        season_id="2030",
        match_id="semi",
        label="Semifinal Escape",
        description="Survived and flipped the match late.",
        leverage=0.2,
        eliminations=2,
        catches=1,
        dodges=3,
        clutch_bonus=1.5,
    )

    assert moment.season_id == "2030"
    assert moment.match_id == "semi"
    assert moment.leverage == 0.5
    assert moment.value == 15.5
