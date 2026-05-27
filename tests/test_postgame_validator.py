"""Structural postgame validator tests.

The validator is a second line of defense (after `_assert_postgame_copy_truthful`)
that compares the *assembled aftermath payload* — specifically its match_card and
top_performers — against the source `MatchResult`. If they disagree, ship a
degraded but truthful payload instead of the lie.
"""
from __future__ import annotations

import pytest

from dodgeball_sim.postgame_validator import (
    PostgameTruthError,
    validate_postgame_payload,
)
from dodgeball_sim.sample_data import scripted_blowout_loss


def _consistent_payload(result, player_club_id: str, opponent_club_id: str) -> dict:
    """Build a payload that matches the resolved MatchResult."""
    teams = result.box_score["teams"]
    home_id, away_id = list(teams.keys())[0], list(teams.keys())[1]
    return {
        "headline": "Match complete.",
        "match_card": {
            "home_club_id": home_id,
            "away_club_id": away_id,
            "winner_club_id": result.winner_team_id,
            "home_survivors": int(teams[home_id]["totals"]["living"]),
            "away_survivors": int(teams[away_id]["totals"]["living"]),
            "scoring_model": "legacy",
            "home_game_points": 0,
            "away_game_points": 0,
        },
        "player_growth_deltas": [],
        "standings_shift": [],
        "recruit_reactions": [],
        "body": [],
        "top_performers": [],
    }


@pytest.fixture
def loss_fixture():
    result, player_club_id, opponent_club_id = scripted_blowout_loss(
        player_survivors=0, opponent_survivors=5
    )
    payload = _consistent_payload(result, player_club_id, opponent_club_id)
    return payload, result, player_club_id, opponent_club_id


def test_validator_accepts_consistent_payload(loss_fixture):
    payload, result, _, _ = loss_fixture
    # Should not raise.
    validate_postgame_payload(payload, result)


def test_validator_rejects_winner_mismatch(loss_fixture):
    payload, result, player_club_id, _ = loss_fixture
    payload["match_card"]["winner_club_id"] = player_club_id  # claim wrong winner
    with pytest.raises(PostgameTruthError, match="winner"):
        validate_postgame_payload(payload, result)


def test_validator_rejects_home_score_mismatch(loss_fixture):
    payload, result, _, _ = loss_fixture
    payload["match_card"]["home_survivors"] = 99
    with pytest.raises(PostgameTruthError, match="survivor score mismatch"):
        validate_postgame_payload(payload, result)


def test_validator_rejects_away_score_mismatch(loss_fixture):
    payload, result, _, _ = loss_fixture
    payload["match_card"]["away_survivors"] = 99
    with pytest.raises(PostgameTruthError, match="survivor score mismatch"):
        validate_postgame_payload(payload, result)


def test_validator_rejects_catches_exceeding_team_total(loss_fixture):
    payload, result, _, _ = loss_fixture
    # Team catch totals in scripted_blowout_loss are 0; any positive
    # catches_made on a top_performer must trip the validator.
    payload["top_performers"] = [
        {
            "player_id": "p1",
            "player_name": "Phantom Catcher",
            "club_name": "Aurora Sentinels",
            "score": 5.0,
            "eliminations_by_throw": 0,
            "catches_made": 7,
            "dodges_successful": 0,
        }
    ]
    with pytest.raises(PostgameTruthError, match="catches"):
        validate_postgame_payload(payload, result)


def test_validator_ignores_payload_without_match_card():
    """Bye-week aftermath has no match_card — nothing structural to check."""
    result, _, _ = scripted_blowout_loss(player_survivors=0, opponent_survivors=5)
    payload = {"headline": "Bye Week Complete", "match_card": None}
    validate_postgame_payload(payload, result)  # no exception


def test_validator_rejects_non_mapping_payload():
    result, _, _ = scripted_blowout_loss(player_survivors=0, opponent_survivors=5)
    with pytest.raises(PostgameTruthError):
        validate_postgame_payload("not a payload", result)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Degraded fallback path
# ---------------------------------------------------------------------------


def test_degraded_payload_passes_validator():
    """The degraded fallback must itself satisfy the validator."""
    from dodgeball_sim.use_cases import _degraded_postgame_payload

    result, player_club_id, opponent_club_id = scripted_blowout_loss(
        player_survivors=0, opponent_survivors=5
    )
    payload = _degraded_postgame_payload(
        result,
        home_club_id=player_club_id,
        away_club_id=opponent_club_id,
    )
    # No narrative copy in degraded form.
    assert payload.get("body") == []
    assert "verdict" not in payload
    assert payload["headline"] == "Match complete."
    # And it must pass structural validation.
    validate_postgame_payload(payload, result)
