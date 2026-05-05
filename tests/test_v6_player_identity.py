from __future__ import annotations

from dataclasses import replace
from dodgeball_sim.models import PlayerArchetype
from dodgeball_sim.lineup import check_lineup_liabilities, optimize_ai_lineup
from dodgeball_sim.development import apply_season_development
from dodgeball_sim.stats import PlayerMatchStats
from dodgeball_sim.engine import MatchEngine
from dodgeball_sim.rng import DeterministicRNG

from .factories import make_player, make_team, make_match_setup

def test_check_lineup_liabilities():
    p1 = replace(make_player("p1"), archetype=PlayerArchetype.POWER)     # Cannot be Captain (idx 0) or Runner (idx 3)
    p2 = replace(make_player("p2"), archetype=PlayerArchetype.AGILITY)   # Cannot be Anchor (idx 2)
    p3 = replace(make_player("p3"), archetype=PlayerArchetype.PRECISION) # Clean fit for Captain/Striker
    p4 = replace(make_player("p4"), archetype=PlayerArchetype.DEFENSE)   # Cannot be Striker (idx 1)
    
    roster = [p1, p2, p3, p4]
    
    # Power at Captain (0), Defense at Striker (1), Agility at Anchor (2), Power at Runner (3)
    warnings = check_lineup_liabilities(roster, ["p1", "p4", "p2", "p1"])
    assert len(warnings) == 4
    assert "mismatched Captain" in warnings[0]
    assert "mismatched Striker" in warnings[1]
    assert "mismatched Anchor" in warnings[2]
    assert "mismatched Runner" in warnings[3]

def test_optimize_ai_lineup():
    p_power = replace(make_player("p1", power=99, accuracy=99, dodge=99, catch=99, stamina=99), archetype=PlayerArchetype.POWER)
    p_def = replace(make_player("p2", power=80, accuracy=80, dodge=80, catch=80, stamina=80), archetype=PlayerArchetype.DEFENSE)
    p_agi = replace(make_player("p3", power=70, accuracy=70, dodge=70, catch=70, stamina=70), archetype=PlayerArchetype.AGILITY)
    
    # optimize_ai_lineup puts the highest OVR player in the first available NON-liability slot.
    # p_power is OVR ~99. Slot 0 (Captain) liability is POWER. So it shouldn't go to 0.
    # It should go to slot 1 (Striker) which allows POWER.
    
    roster = [p_power, p_def, p_agi]
    lineup_ids = optimize_ai_lineup(roster)
    
    assert lineup_ids[1] == "p1"  # p_power placed at Striker (idx 1)
    # p_def is OVR ~80. Slot 0 (Captain) allows DEFENSE. So it goes to 0.
    assert lineup_ids[0] == "p2"  # p_def placed at Captain (idx 0)

def test_dev_focus_outcomes():
    from dodgeball_sim.models import PlayerTraits
    player = replace(
        make_player("p", accuracy=40, power=40, dodge=40, catch=40, stamina=40),
        age=20,
        archetype=PlayerArchetype.TACTICAL,
        traits=PlayerTraits(potential=90.0)
    )
    stats = PlayerMatchStats(minutes_played=1000)
    rng = DeterministicRNG(42)
    
    dev_balanced = apply_season_development(player, stats, [], rng, dev_focus="BALANCED")
    dev_youth = apply_season_development(player, stats, [], rng, dev_focus="YOUTH_ACCELERATION")
    dev_tactical = apply_season_development(player, stats, [], rng, dev_focus="TACTICAL_DRILLS")
    dev_strength = apply_season_development(player, stats, [], rng, dev_focus="STRENGTH_AND_CONDITIONING")
    
    # YOUTH_ACCELERATION (1.5x) should yield more growth overall for a 20yo than BALANCED
    assert dev_youth.overall() > dev_balanced.overall()
    
    # TACTICAL_DRILLS should specifically boost tactical_iq more than BALANCED
    assert dev_tactical.ratings.tactical_iq > dev_balanced.ratings.tactical_iq
    
    # STRENGTH_AND_CONDITIONING should boost power more than BALANCED
    assert dev_strength.ratings.power > dev_balanced.ratings.power

def test_engine_liabilities_affect_fatigue():
    # If a player is in a liability slot, fatigue should drain faster.
    # We can test this by running a small simulation with a liability vs non-liability team.
    
    # Team A: Liability. Power at Captain (0)
    team_a = make_team("team_a", [
        replace(make_player("a1"), archetype=PlayerArchetype.POWER),
        replace(make_player("a2"), archetype=PlayerArchetype.POWER),
        replace(make_player("a3"), archetype=PlayerArchetype.POWER),
    ])
    
    # Team B: Clean fit. Precision at Captain (0)
    team_b = make_team("team_b", [
        replace(make_player("b1"), archetype=PlayerArchetype.PRECISION),
        replace(make_player("b2"), archetype=PlayerArchetype.PRECISION),
        replace(make_player("b3"), archetype=PlayerArchetype.PRECISION),
    ])
    
    setup = make_match_setup(team_a=team_a, team_b=team_b)
    engine = MatchEngine()
    
    # Just checking internal _apply_fatigue logic
    from dodgeball_sim.models import PlayerState
    p_state_liable = PlayerState(player=team_a.players[0])
    p_state_clean = PlayerState(player=team_b.players[0])
    
    engine._apply_fatigue(p_state_liable, delta=1.0, is_liable=True)
    engine._apply_fatigue(p_state_clean, delta=1.0, is_liable=False)
    
    # Liable player should have exactly 15% more fatigue
    assert p_state_liable.fatigue > p_state_clean.fatigue
    assert round(p_state_liable.fatigue / p_state_clean.fatigue, 2) == 1.15
