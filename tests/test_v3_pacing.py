from __future__ import annotations

from dodgeball_sim.scheduler import ScheduledMatch
from dodgeball_sim.sim_pacing import SimRequest, choose_matches_to_sim, summarize_sim_digest


def _match(match_id: str, week: int, home: str, away: str) -> ScheduledMatch:
    return ScheduledMatch(
        match_id=match_id,
        season_id="season_1",
        week=week,
        home_club_id=home,
        away_club_id=away,
    )


def test_choose_matches_to_sim_stops_before_next_user_match():
    schedule = [
        _match("m1", 1, "lunar", "harbor"),
        _match("m2", 1, "aurora", "granite"),
        _match("m3", 2, "lunar", "aurora"),
    ]

    chosen, stop = choose_matches_to_sim(schedule, set(), "aurora", SimRequest(mode="to_next_user_match"))

    assert [match.match_id for match in chosen] == ["m1"]
    assert stop.reason == "user_match"
    assert stop.match_id == "m2"


def test_choose_matches_to_sim_stops_at_recruitment_milestone_week():
    schedule = [
        _match("m1", 1, "lunar", "harbor"),
        _match("m2", 2, "granite", "solstice"),
        _match("m3", 3, "northwood", "harbor"),
    ]

    chosen, stop = choose_matches_to_sim(
        schedule,
        set(),
        "aurora",
        SimRequest(mode="milestone", milestone="recruitment_day", milestone_week=2),
    )

    assert [match.match_id for match in chosen] == ["m1"]
    assert stop.reason == "recruitment_day"
    assert stop.week == 2


def test_summarize_sim_digest_keeps_required_v3_context():
    digest = summarize_sim_digest(
        matches_simmed=3,
        user_record_delta="2-1-0",
        standings_note="Aurora moved from fourth to second.",
        notable_lines=["Mara Voss led the week with 6 eliminations."],
        scouting_note="A scout reveal is ready.",
        recruitment_note="Recruitment day is next.",
        next_action="Play Next Match",
    )

    assert digest["matches_simmed"] == 3
    assert digest["standings_note"] == "Aurora moved from fourth to second."
    assert digest["notable_lines"] == ["Mara Voss led the week with 6 eliminations."]
    assert digest["scouting_note"] == "A scout reveal is ready."
    assert digest["recruitment_note"] == "Recruitment day is next."
