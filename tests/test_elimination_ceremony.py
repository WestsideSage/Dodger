"""The elimination ceremony must state how the run ended without
contradicting the score, and surface the players who carried the match.

Task 9 (2026-05-28 playtest-fixes): a playoff exit used to jump straight
to the regular-season recap. These tests pin the honest summary model.
"""

from __future__ import annotations

from dodgeball_sim.elimination_ceremony import build_elimination_summary, cause_line


def _contribs():
    return [
        {"player_name": "Ezra Prism", "score": 18.0},
        {"player_name": "Mara Vela", "score": 14.0},
        {"player_name": "Dax Orr", "score": 11.0},
        {"player_name": "Kit Lune", "score": 9.0},
    ]


def test_tiebreaker_loss_reuses_narrative_note_verbatim():
    line = cause_line(
        decided_by="seed_tiebreaker",
        narrative_note="Deadlocked after overtime; the higher seed advanced.",
        player_score=0,
        opponent_score=0,
    )
    assert line == "Deadlocked after overtime; the higher seed advanced."


def test_regulation_shutout_loss_does_not_claim_a_close_game():
    line = cause_line(decided_by="regulation", narrative_note="", player_score=0, opponent_score=3)
    assert "shut out" in line.lower()
    assert "edged" not in line.lower()


def test_regulation_blowout_reads_as_a_gap():
    line = cause_line(decided_by="regulation", narrative_note="", player_score=1, opponent_score=4)
    assert "gap" in line.lower()


def test_one_possession_loss_reads_as_close():
    line = cause_line(decided_by="regulation", narrative_note="", player_score=3, opponent_score=4)
    assert "one-possession" in line.lower()


def test_summary_keeps_top_three_contributors_and_returning_core():
    summary = build_elimination_summary(
        stage="Semifinal",
        opponent_name="Lunar Syndicate",
        player_score=2,
        opponent_score=3,
        decided_by="regulation",
        narrative_note="",
        contributors=_contribs(),
    )
    assert summary["stage"] == "Semifinal"
    assert summary["opponent_name"] == "Lunar Syndicate"
    assert len(summary["contributors"]) == 3
    assert summary["returning"] == ["Ezra Prism", "Mara Vela", "Dax Orr"]
    assert "3–2" in summary["cause"] or "gap" in summary["cause"].lower()
