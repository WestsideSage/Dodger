import pytest

from dodgeball_sim.match_lifecycle import (
    OfficialGameClock,
    OfficialGameMode,
    OfficialGameResult,
    OfficialGameState,
    OfficialMatchClock,
    OfficialRoundType,
    bracket_match_clock_seconds,
    cloth_final_game_clock_seconds,
    decide_cloth_game_by_active_count,
)
from dodgeball_sim.rulesets import CLOTH_OPEN, FOAM_OPEN, NO_STING_OPEN


def _game(profile, elapsed=0, a=6, b=6):
    return OfficialGameState(
        game_number=1,
        profile=profile,
        clock=OfficialGameClock(limit_seconds=profile.game_clock_seconds, elapsed_seconds=elapsed),
        active_count_a=a,
        active_count_b=b,
    )


def test_foam_game_triggers_no_blocking_at_180s():
    g = _game(FOAM_OPEN, elapsed=180)
    assert g.trigger_no_blocking() is True


def test_no_sting_triggers_no_blocking_at_180s():
    g = _game(NO_STING_OPEN, elapsed=180)
    assert g.trigger_no_blocking() is True


def test_cloth_does_not_trigger_game_no_blocking():
    g = _game(CLOTH_OPEN, elapsed=180)
    assert g.trigger_no_blocking() is False


def test_cloth_game_clock_decision_by_active_count():
    g = _game(CLOTH_OPEN, elapsed=180, a=4, b=2)
    assert decide_cloth_game_by_active_count(g) == OfficialGameResult.TEAM_A_WIN
    g2 = _game(CLOTH_OPEN, elapsed=180, a=2, b=4)
    assert decide_cloth_game_by_active_count(g2) == OfficialGameResult.TEAM_B_WIN
    g3 = _game(CLOTH_OPEN, elapsed=180, a=3, b=3)
    assert decide_cloth_game_by_active_count(g3) == OfficialGameResult.TIE


def test_decide_cloth_active_count_rejects_non_cloth():
    with pytest.raises(ValueError):
        decide_cloth_game_by_active_count(_game(FOAM_OPEN))


def test_cloth_final_game_clock_90s_when_match_time_short():
    assert cloth_final_game_clock_seconds(remaining_match_seconds=80) == 90
    assert cloth_final_game_clock_seconds(remaining_match_seconds=120) == 180


def test_bracket_match_clock_durations():
    assert bracket_match_clock_seconds(OfficialRoundType.BRACKET_STANDARD) == 24 * 60
    assert bracket_match_clock_seconds(OfficialRoundType.BRACKET_SEMIFINAL) == 30 * 60
    assert bracket_match_clock_seconds(OfficialRoundType.BRACKET_FINAL) == 40 * 60
    assert bracket_match_clock_seconds(OfficialRoundType.ROUND_ROBIN) == 0


def test_game_clock_remaining_and_expired():
    c = OfficialGameClock(limit_seconds=180, elapsed_seconds=30)
    assert c.remaining() == 150
    assert not c.expired()
    c.advance(150)
    assert c.expired()
    assert c.remaining() == 0


def test_match_clock_untimed_sentinel():
    c = OfficialMatchClock(limit_seconds=0)
    assert c.remaining() > 10**8
    assert not c.expired()


def test_game_state_defaults_to_pending_standard():
    g = _game(FOAM_OPEN)
    assert g.mode == OfficialGameMode.STANDARD
    assert g.result == OfficialGameResult.PENDING
