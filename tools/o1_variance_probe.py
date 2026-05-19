"""O1 investigation probe: measure favourite win-rate vs OVR edge.

Read-only Monte Carlo over the existing match engine. Does NOT change balance.
Run: python tools/o1_variance_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from dodgeball_sim.engine import MatchEngine  # noqa: E402
from factories import make_match_setup, make_player, make_team  # noqa: E402


def team(team_id: str, rating: float):
    players = [
        make_player(
            f"{team_id}_{i}",
            accuracy=rating,
            power=rating,
            dodge=rating,
            catch=rating,
            stamina=rating,
        )
        for i in range(6)
    ]
    return make_team(team_id, players)


def measure(fav_rating: float, dog_rating: float, trials: int = 400) -> float:
    engine = MatchEngine()
    fav = team("fav", fav_rating)
    dog = team("dog", dog_rating)
    setup = make_match_setup(fav, dog)
    fav_wins = 0
    for seed in range(trials):
        result = engine.run(setup, seed=seed)
        if result.winner_team_id == "fav":
            fav_wins += 1
    return fav_wins / trials


if __name__ == "__main__":
    print("per-player OVR edge -> favourite win rate (400 trials each)")
    base = 63.0
    for edge in (0, 4, 8, 12, 16, 20):
        rate = measure(base + edge, base)
        net = edge * 6
        print(f"  +{edge:>2} per player (net +{net:>3} OVR): {rate * 100:5.1f}%")
