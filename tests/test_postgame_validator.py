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


def _with_official_meta(
    result, *, home_id: str, away_id: str, home_gp: int, away_gp: int
):
    """Return a copy of ``result`` with official_metadata attached (team_a==home)."""
    import dataclasses

    return dataclasses.replace(
        result,
        official_metadata={
            "team_a_id": home_id,
            "team_b_id": away_id,
            "team_a_game_points": home_gp,
            "team_b_game_points": away_gp,
        },
    )


def test_validator_rejects_game_points_mismatch(loss_fixture):
    payload, result, player_club_id, opponent_club_id = loss_fixture
    # player_first_in_box=True so home is player_club_id.
    result = _with_official_meta(
        result, home_id=player_club_id, away_id=opponent_club_id, home_gp=2, away_gp=5
    )
    payload["match_card"]["home_game_points"] = 2
    payload["match_card"]["away_game_points"] = 5
    # Sanity: consistent payload passes.
    validate_postgame_payload(payload, result)
    # Mutate home_game_points away from the real value.
    payload["match_card"]["home_game_points"] = 99
    with pytest.raises(PostgameTruthError, match="game_points"):
        validate_postgame_payload(payload, result)


def test_validator_skips_game_points_when_meta_absent_or_zero(loss_fixture):
    """Legacy / no-scoring matches must not false-positive."""
    payload, result, _, _ = loss_fixture
    # No official_metadata: passes (already covered by other tests, asserting here).
    assert result.official_metadata is None
    validate_postgame_payload(payload, result)
    # official_metadata present but both zero: still skipped (legacy scoring).
    result = _with_official_meta(
        result,
        home_id=payload["match_card"]["home_club_id"],
        away_id=payload["match_card"]["away_club_id"],
        home_gp=0,
        away_gp=0,
    )
    # Even with mismatched (nonzero) game_points in the payload it should not
    # raise, because both meta values are zero (no scoring signal).
    payload["match_card"]["home_game_points"] = 7
    validate_postgame_payload(payload, result)


def test_validator_handles_none_in_payload_gracefully(loss_fixture):
    """A malformed payload with None scores must raise PostgameTruthError,
    not a bare TypeError that would skip the fallback."""
    payload, result, _, _ = loss_fixture
    payload["match_card"]["home_survivors"] = None
    with pytest.raises(PostgameTruthError):
        validate_postgame_payload(payload, result)


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


def test_degraded_payload_preserves_real_game_points():
    """When official_metadata is present, the fallback must carry the real
    game_points through — not silently zero them."""
    from dodgeball_sim.use_cases import _degraded_postgame_payload

    result, player_club_id, opponent_club_id = scripted_blowout_loss(
        player_survivors=0, opponent_survivors=5
    )
    result = _with_official_meta(
        result,
        home_id=player_club_id,
        away_id=opponent_club_id,
        home_gp=3,
        away_gp=7,
    )
    payload = _degraded_postgame_payload(
        result,
        home_club_id=player_club_id,
        away_club_id=opponent_club_id,
    )
    assert payload["match_card"]["home_game_points"] == 3
    assert payload["match_card"]["away_game_points"] == 7
    assert payload["match_card"]["scoring_model"] in ("cloth", "foam")
    # And it must still satisfy the validator.
    validate_postgame_payload(payload, result)


def test_build_aftermath_falls_back_on_validator_error(monkeypatch, caplog):
    """Integration: when validate_postgame_payload raises, _build_aftermath
    returns the degraded payload AND logs ERROR."""
    import logging
    import sqlite3

    from dodgeball_sim import use_cases
    from dodgeball_sim.postgame_validator import PostgameTruthError

    # Construct a minimal record stub with what _build_aftermath touches up to
    # the validation step. We reuse scripted_blowout_loss for box_score.
    result, player_club_id, opponent_club_id = scripted_blowout_loss(
        player_survivors=0, opponent_survivors=5
    )

    class _Record:
        match_id = "m-test"
        home_club_id = player_club_id
        away_club_id = opponent_club_id
        result = None

    record = _Record()
    record.result = result

    def _boom(_payload, _result):
        raise PostgameTruthError("synthetic failure for test")

    monkeypatch.setattr(use_cases, "validate_postgame_payload", _boom)

    dashboard = {"result": "Match complete."}

    caplog.set_level(logging.ERROR, logger="dodgeball_sim.use_cases")
    # Need a real conn because _build_aftermath now also computes development feedback.
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE club_rosters (club_id TEXT PRIMARY KEY, players_json TEXT)")
    aftermath = use_cases._build_aftermath(
        conn=conn,
        dashboard=dashboard,
        record=record,
        season_id="s-1",
    )

    # Degraded payload shape.
    assert aftermath["headline"] == "Match complete."
    assert aftermath.get("body") == []
    assert "verdict" not in aftermath or aftermath["verdict"] in (None, "")
    assert aftermath["match_card"]["winner_club_id"] == result.winner_team_id
    # And the ERROR log fired.
    assert any(
        "structural validation" in rec.message and rec.levelname == "ERROR"
        for rec in caplog.records
    )
