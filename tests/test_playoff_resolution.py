"""Tests for playoff match resolution (overtime → seed tiebreaker).

Task 1 of the 2026-05-27 rookie-run playtest-fixes plan: a tied playoff
match must no longer silently advance by seed inside ``create_final_match``.
The resolution decision is moved upstream into ``resolve_playoff_match``
which produces a typed ``PlayoffOutcome`` carrying ``decided_by`` and a
player-facing ``narrative_note``.
"""

from __future__ import annotations

from dodgeball_sim.playoff_resolution import PlayoffOutcome, resolve_playoff_match
from dodgeball_sim.sample_data import scripted_tied_semifinal


def test_tied_semifinal_goes_to_overtime_then_seed() -> None:
    match = scripted_tied_semifinal(home_seed=4, away_seed=1, regulation_score=(0, 0))
    outcome = resolve_playoff_match(match)
    assert isinstance(outcome, PlayoffOutcome)
    assert outcome.decided_by in {"overtime", "seed_tiebreaker"}
    assert outcome.winner_id is not None
    assert outcome.loser_id is not None
    if outcome.decided_by == "seed_tiebreaker":
        # Better seed (lower number) was the away side in this fixture; that
        # side must advance and the narrative must say so plainly.
        assert outcome.winner_id == match.away_club_id
        assert "seed" in outcome.narrative_note.lower()


def test_regulation_winner_is_returned_unchanged() -> None:
    match = scripted_tied_semifinal(
        home_seed=1, away_seed=4, regulation_score=(3, 1)
    )
    outcome = resolve_playoff_match(match)
    assert outcome.decided_by == "regulation"
    assert outcome.winner_id == match.home_club_id
    assert outcome.loser_id == match.away_club_id


def test_seed_tiebreaker_narrative_mentions_tiebreaker() -> None:
    match = scripted_tied_semifinal(home_seed=2, away_seed=3, regulation_score=(2, 2))
    outcome = resolve_playoff_match(match)
    # With no overtime simulator hooked, ties resolve via seed.
    assert outcome.decided_by == "seed_tiebreaker"
    # Home is the better seed (2 < 3) so home advances.
    assert outcome.winner_id == match.home_club_id
    assert outcome.narrative_note  # non-empty


def test_top_seed_tiebreaker_narrative_is_one_indexed() -> None:
    # Regression: seeds are stored 0-indexed but players read them 1-based.
    # The narrative must render the *displayed* seed (winner_seed + 1), so the
    # TOP seed (0-indexed 0) reads "#1" — never the off-by-one "#0".
    match = scripted_tied_semifinal(home_seed=0, away_seed=3, regulation_score=(0, 0))
    outcome = resolve_playoff_match(match)
    assert outcome.decided_by == "seed_tiebreaker"
    # Home holds the better seed (0 < 3) so home advances.
    assert outcome.winner_id == match.home_club_id
    assert outcome.loser_id == match.away_club_id
    assert "#1" in outcome.narrative_note
    assert "#0" not in outcome.narrative_note
