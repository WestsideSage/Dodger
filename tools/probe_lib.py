"""Shared pure-function helpers for Tier 1 / engine-health probes.

No I/O. No printing. No argparse. Callers (CLIs and pytest) compose.

Note: tools/ does not import from tests/. Player construction lives here
so both the sanity probe and the health probe consume the same helpers.

Match-length proxy: `len(DriverMatchOutput.events)`. `DriverMatchOutput`
does not expose an explicit end_tick (see src/dodgeball_sim/engine_driver.py).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import sqrt
from typing import Any

from dodgeball_sim.engine_driver import DriverMatchInput, EngineDriver
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


@dataclass(frozen=True)
class RungResult:
    net_ovr_edge: int
    trials: int
    fav_wins: int
    win_rate: float
    ci_low: float
    ci_high: float
    outputs: tuple[Any, ...]


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson 95% CI for a binomial proportion.

    Returns (0.0, 0.0) for trials == 0. Clamps upper bound at 1.0 so a
    perfect score reports a finite interval.
    """
    if trials <= 0:
        return (0.0, 0.0)
    p = successes / trials
    denom = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denom
    spread = (z * sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))


def run_ovr_curve(
    driver: EngineDriver,
    *,
    rungs: tuple[int, ...] = (0, 4, 8, 12),
    trials_per_rung: int = 400,
    base_rating: float = 63.0,
    seed_offset: int = 0,
) -> tuple[RungResult, ...]:
    """Run a Monte Carlo OVR-edge curve through `driver`.

    Each rung's per-player edge becomes a net six-player OVR edge. Favorite
    rating = base_rating + per_player_edge; dog = base_rating.

    Seeding: seed = rung_index * 10_000 + trial_index + seed_offset.
    """
    results: list[RungResult] = []
    for rung_index, edge in enumerate(rungs):
        fav_wins = 0
        outputs: list[Any] = []
        for trial in range(trials_per_rung):
            seed = rung_index * 10_000 + trial + seed_offset
            mi = make_match_input(
                seed=seed,
                rating_a=base_rating + edge,
                rating_b=base_rating,
            )
            out = driver.run(mi)
            outputs.append(out)
            if out.winner_team_id == "fav":
                fav_wins += 1
        win_rate = fav_wins / trials_per_rung if trials_per_rung else 0.0
        ci_low, ci_high = wilson_ci(fav_wins, trials_per_rung)
        results.append(
            RungResult(
                net_ovr_edge=edge * 6,
                trials=trials_per_rung,
                fav_wins=fav_wins,
                win_rate=win_rate,
                ci_low=ci_low,
                ci_high=ci_high,
                outputs=tuple(outputs),
            )
        )
    return tuple(results)


_MOMENT_KINDS = (
    "dramatic_catch",
    "late_game_escape",
    "one_v_one_finale",
    "gassed_collapse",
    "flood_throw",
    "comeback",
)


def _all_outputs(results: tuple[RungResult, ...]) -> tuple[Any, ...]:
    return tuple(out for rung in results for out in rung.outputs)


def summarize_moments(results: tuple[RungResult, ...]) -> dict[str, dict[str, float]]:
    """Per-moment-kind statistics across every match in `results`."""
    outputs = _all_outputs(results)
    match_count = len(outputs)
    totals: Counter[str] = Counter()
    matches_with: Counter[str] = Counter()
    for out in outputs:
        seen: set[str] = set()
        for event in out.moment_events:
            kind = event.kind.value if hasattr(event.kind, "value") else str(event.kind)
            totals[kind] += 1
            seen.add(kind)
        for kind in seen:
            matches_with[kind] += 1
    summary: dict[str, dict[str, float]] = {}
    for kind in _MOMENT_KINDS:
        summary[kind] = {
            "per_match": totals[kind] / match_count if match_count else 0.0,
            "pct_matches_with": matches_with[kind] / match_count if match_count else 0.0,
            "total": totals[kind],
        }
    return summary


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    idx = min(len(sorted_values) - 1, max(0, int(round((pct / 100.0) * (len(sorted_values) - 1)))))
    return sorted_values[idx]


def summarize_match_lengths(results: tuple[RungResult, ...]) -> dict[str, int]:
    """P25 / P50 / P75 / P95 of `len(events)` across every match."""
    outputs = _all_outputs(results)
    lengths = sorted(len(out.events) for out in outputs)
    return {
        "p25": _percentile(lengths, 25),
        "p50": _percentile(lengths, 50),
        "p75": _percentile(lengths, 75),
        "p95": _percentile(lengths, 95),
    }


def summarize_outcomes(results: tuple[RungResult, ...]) -> dict[str, int]:
    """Aggregate fav / dog / draw counts and percentages across `results`."""
    outputs = _all_outputs(results)
    fav = sum(1 for out in outputs if out.winner_team_id == "fav")
    dog = sum(1 for out in outputs if out.winner_team_id == "dog")
    draw = sum(1 for out in outputs if out.winner_team_id is None)
    total = len(outputs) or 1
    return {
        "fav": fav,
        "dog": dog,
        "draw": draw,
        "fav_pct": round(100.0 * fav / total, 1),
        "dog_pct": round(100.0 * dog / total, 1),
        "draw_pct": round(100.0 * draw / total, 1),
    }


__all__ = [
    "make_player",
    "make_team",
    "make_match_input",
    "RungResult",
    "wilson_ci",
    "run_ovr_curve",
    "summarize_moments",
    "summarize_match_lengths",
    "summarize_outcomes",
]
