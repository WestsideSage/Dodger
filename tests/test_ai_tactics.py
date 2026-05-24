from __future__ import annotations

from dodgeball_sim.ai_tactics import get_ai_tactics


def test_contender_tactics():
    tactics = get_ai_tactics("Contender", "Balanced")
    assert tactics["approach"] == "aggressive"
    assert tactics["target_focus"] == "their_stars"
    assert tactics["rush_commit"] == "all_in"


def test_defensive_specialist_tactics():
    tactics = get_ai_tactics("Defensive Specialist", "Balanced")
    assert tactics["approach"] == "patient"
    assert tactics["target_focus"] == "ball_holders"
    assert tactics["rush_commit"] == "hold_back"


def test_power_throwers_tactics_win_now():
    tactics = get_ai_tactics("Power Throwers", "Win Now")
    assert tactics["approach"] == "aggressive"
    assert tactics["rush_commit"] == "all_in"
    assert tactics["rush_target"] == "center"


def test_aging_veterans_tactics_preserve_health():
    tactics = get_ai_tactics("Aging Veterans", "Preserve Health")
    assert tactics["approach"] == "patient"
    assert tactics["catch_posture"] == "play_safe"
    assert tactics["rush_commit"] == "hold_back"
