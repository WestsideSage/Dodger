from dodgeball_sim.voice_pregame import render_matchup_framing
from dodgeball_sim.voice_aftermath import render_headline
from dodgeball_sim.rng import DeterministicRNG

def test_voice_pregame_deterministic():
    rng1 = DeterministicRNG(42)
    rng2 = DeterministicRNG(42)
    assert render_matchup_framing("Aurora", "Solstice", rng1) == render_matchup_framing("Aurora", "Solstice", rng2)

def test_voice_aftermath_deterministic():
    rng = DeterministicRNG(1)
    res = render_headline("Win", "expected", rng)
    assert len(res) > 5


def test_voice_aftermath_margin_headline_references_score():
    rng = DeterministicRNG(1)
    shutout = render_headline("Win", "expected", rng, player_survivors=6, opponent_survivors=0)
    assert "6-0" in shutout
    assert "Win" in shutout

    loss = render_headline("Loss", "expected", DeterministicRNG(2), player_survivors=1, opponent_survivors=5)
    assert "1-5" in loss
    assert "Loss" in loss


def test_voice_aftermath_margin_headline_deterministic():
    a = render_headline("Win", "expected", DeterministicRNG(7), player_survivors=4, opponent_survivors=2)
    b = render_headline("Win", "expected", DeterministicRNG(7), player_survivors=4, opponent_survivors=2)
    assert a == b
