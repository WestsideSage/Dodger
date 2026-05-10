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
