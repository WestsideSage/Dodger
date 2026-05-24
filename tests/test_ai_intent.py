from __future__ import annotations

import pytest
from dodgeball_sim.ai_intent import choose_ai_intent
from dodgeball_sim.league import Club
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.season import StandingsRow


def _make_club(archetype: str) -> Club:
    return Club(
        club_id="test_club",
        name="Test Club",
        colors=("blue", "red"),
        home_region="Midwest",
        founded_year=2026,
        coach_policy=CoachPolicy(),
        program_archetype=archetype,
    )


def test_contender_intent_scoring():
    club = _make_club("Contender")
    # Early season, no record yet
    row = StandingsRow("test_club", wins=0, losses=0, draws=0, elimination_differential=0, points=0)
    intent = choose_ai_intent(row, week=1, total_weeks=10, club=club, roster=[])
    # Contender has +8 on Win Now, bringing Win Now to 18.0 (highest)
    assert intent == "Win Now"


def test_development_factory_intent_scoring():
    club = _make_club("Development Factory")
    row = StandingsRow("test_club", wins=1, losses=1, draws=0, elimination_differential=0, points=3)
    intent = choose_ai_intent(row, week=3, total_weeks=10, club=club, roster=[])
    # Development Factory has +12 on Develop Youth, bringing it to 22.0
    assert intent == "Develop Youth"


def test_aging_veterans_intent_scoring_under_pressure():
    club = _make_club("Aging Veterans")
    # Under pressure (losing record)
    row = StandingsRow("test_club", wins=0, losses=4, draws=0, elimination_differential=-5, points=0)
    intent = choose_ai_intent(row, week=5, total_weeks=10, club=club, roster=[])
    # Base: Balanced: 10, Win Now: 10, Develop Youth: 10, Preserve Health: 10
    # Losses < Wins: Develop Youth +6, Preserve Health +3
    # Differential <= -3: Preserve Health +8, Develop Youth +4
    # Archetype (Aging Veterans): Win Now +4, Preserve Health +6
    # Total Preserve Health: 10 + 3 + 8 + 6 = 27.0
    # Total Develop Youth: 10 + 6 + 4 = 20.0
    assert intent == "Preserve Health"
