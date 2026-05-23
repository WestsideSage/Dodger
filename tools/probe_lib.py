"""Shared pure-function helpers for Tier 1 / engine-health probes.

No I/O. No printing. No argparse. Callers (CLIs and pytest) compose.

Note: tools/ does not import from tests/. Player construction lives here
so both the sanity probe and the health probe consume the same helpers.

Match-length proxy: `len(DriverMatchOutput.events)`. `DriverMatchOutput`
does not expose an explicit end_tick (see src/dodgeball_sim/engine_driver.py).
"""
from __future__ import annotations

from dataclasses import dataclass

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player, PlayerArchetype, PlayerRatings


def make_player(pid: str, club: str, rating: float) -> Player:
    """Build a six-skill-uniform player at the requested rating."""
    return Player(
        id=pid,
        name=pid.upper(),
        ratings=PlayerRatings(
            accuracy=rating,
            power=rating,
            dodge=rating,
            catch=rating,
            stamina=rating,
            tactical_iq=rating,
            catch_courage=rating,
            throw_selection_iq=rating,
            conditioning_curve=rating,
        ),
        club_id=club,
        archetype=PlayerArchetype.CATCHER,
    )


def make_team(team_id: str, rating: float, size: int = 6) -> tuple[str, ...]:
    """Return the starter IDs for a team of `size` players at uniform rating."""
    return tuple(f"{team_id}_{i}" for i in range(size))


def make_match_input(
    seed: int,
    *,
    rating_a: float = 63.0,
    rating_b: float = 63.0,
    policy_a: CoachPolicy | None = None,
    policy_b: CoachPolicy | None = None,
    match_id_prefix: str = "probe",
) -> DriverMatchInput:
    """Build a DriverMatchInput with synthetic fav/dog teams.

    Team A is "fav" at `rating_a`; team B is "dog" at `rating_b`. The
    fav/dog naming is load-bearing for downstream `winner_team_id == "fav"`
    counting in `run_ovr_curve`.
    """
    starters_a = make_team("fav", rating_a)
    starters_b = make_team("dog", rating_b)
    player_lookup = {pid: make_player(pid, "fav", rating_a) for pid in starters_a}
    player_lookup.update({pid: make_player(pid, "dog", rating_b) for pid in starters_b})
    return DriverMatchInput(
        match_id=f"{match_id_prefix}_{seed}",
        team_a_id="fav",
        team_b_id="dog",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=player_lookup,
        policy_a=policy_a if policy_a is not None else CoachPolicy(),
        policy_b=policy_b if policy_b is not None else CoachPolicy(),
        seed=seed,
    )


__all__ = ["make_player", "make_team", "make_match_input"]
