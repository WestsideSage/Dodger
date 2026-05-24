from __future__ import annotations

from dodgeball_sim.ai_lineup import optimize_archetype_lineup
from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits, PlayerArchetype


def _make_player(
    pid: str,
    name: str,
    newcomer: bool,
    overall: float,
    potential: float,
    conditioning: float = 50.0,
    archetype: PlayerArchetype = PlayerArchetype.THROWER,
) -> Player:
    ratings = PlayerRatings(
        accuracy=overall,
        power=overall,
        dodge=overall,
        catch=overall,
        stamina=overall,
        conditioning_curve=conditioning,
    )
    traits = PlayerTraits(potential=potential)
    return Player(
        id=pid,
        name=name,
        ratings=ratings,
        archetype=archetype,
        traits=traits,
        newcomer=newcomer,
    )


def test_standard_lineup_optimization():
    # 8 players: 6 veterans, 2 bench players
    roster = [
        _make_player("v1", "Vet 1", False, 75.0, 50.0),
        _make_player("v2", "Vet 2", False, 74.0, 50.0),
        _make_player("v3", "Vet 3", False, 73.0, 50.0),
        _make_player("v4", "Vet 4", False, 72.0, 50.0),
        _make_player("v5", "Vet 5", False, 71.0, 50.0),
        _make_player("v6", "Vet 6", False, 70.0, 50.0),
        _make_player("b1", "Bench 1", False, 60.0, 50.0),
        _make_player("b2", "Bench 2", False, 58.0, 50.0),
    ]
    
    # Under standard Rebuild club, lineup starters should contain v1..v6
    lineup = optimize_archetype_lineup(roster, "Balanced Rebuild", "Balanced")
    assert set(lineup[:6]) == {"v1", "v2", "v3", "v4", "v5", "v6"}


def test_development_factory_rookie_substitution():
    # 7 veterans, 1 high-potential newcomer rookie on the bench (lower OVR than standard starters)
    roster = [
        _make_player("v1", "Vet 1", False, 75.0, 45.0), # Vet to replace (low potential 45)
        _make_player("v2", "Vet 2", False, 74.0, 60.0),
        _make_player("v3", "Vet 3", False, 73.0, 60.0),
        _make_player("v4", "Vet 4", False, 72.0, 60.0),
        _make_player("v5", "Vet 5", False, 71.0, 60.0),
        _make_player("v6", "Vet 6", False, 70.0, 60.0),
        _make_player("v7", "Vet 7", False, 68.0, 60.0), # Bench vet
        _make_player("r1", "Rookie 1", True, 62.0, 85.0, conditioning=60.0), # High potential rookie on the bench
    ]
    
    # In a low-stakes week ("Balanced"), the Development Factory should swap the rookie ("r1") into the starting lineup in place of "v1" (lowest potential starter).
    lineup = optimize_archetype_lineup(roster, "Development Factory", "Balanced")
    
    # Rookie r1 should be a starter (one of first 6)
    assert "r1" in lineup[:6]
    # v1 (lowest potential starter replaced) should be on the bench (index >= 6)
    assert "v1" not in lineup[:6]


def test_development_factory_ignores_must_win_weeks():
    roster = [
        _make_player("v1", "Vet 1", False, 75.0, 45.0),
        _make_player("v2", "Vet 2", False, 74.0, 60.0),
        _make_player("v3", "Vet 3", False, 73.0, 60.0),
        _make_player("v4", "Vet 4", False, 72.0, 60.0),
        _make_player("v5", "Vet 5", False, 71.0, 60.0),
        _make_player("v6", "Vet 6", False, 70.0, 60.0),
        _make_player("v7", "Vet 7", False, 68.0, 60.0),
        _make_player("r1", "Rookie 1", True, 62.0, 85.0, conditioning=60.0),
    ]
    
    # Must-win week ("Win Now") should suppress rookie promotion
    lineup = optimize_archetype_lineup(roster, "Development Factory", "Win Now")
    assert "r1" not in lineup[:6]
    assert "v1" in lineup[:6]


def test_development_factory_ignores_tired_rookie():
    roster = [
        _make_player("v1", "Vet 1", False, 75.0, 45.0),
        _make_player("v2", "Vet 2", False, 74.0, 60.0),
        _make_player("v3", "Vet 3", False, 73.0, 60.0),
        _make_player("v4", "Vet 4", False, 72.0, 60.0),
        _make_player("v5", "Vet 5", False, 71.0, 60.0),
        _make_player("v6", "Vet 6", False, 70.0, 60.0),
        _make_player("v7", "Vet 7", False, 68.0, 60.0),
        _make_player("r1", "Rookie 1", True, 62.0, 85.0, conditioning=40.0), # Tired rookie (conditioning < 50)
    ]
    
    lineup = optimize_archetype_lineup(roster, "Development Factory", "Balanced")
    assert "r1" not in lineup[:6]
    assert "v1" in lineup[:6]
