"""Decision-impact probe — measures whether player-facing levers move outcomes.

Two sections, both run on the shipping drivers (RecTier1Driver and the
multi-set OfficialMatchEngineDriver — the engine real official careers play):

1. ``tactics``: for each CoachPolicy axis, team A plays one option against a
   default-policy team B at even strength. Reports W/D/L with a Wilson CI so a
   "dead knob" (within CI of the mirror baseline) is visible as measurement,
   not vibes. The mirror baseline (default vs default) is printed first.
   Both teams use a per-player catch/dodge SPREAD around the same 63 mean
   (career seeds draw each attribute ~gauss(62,10)) — a uniform-rating fixture
   is degenerate for threshold-based knobs (e.g. catch postures gate on the
   catch rating, so a uniform roster sits entirely on one side of the cliff).

2. ``attributes``: team A is uniform-63 except ONE rating raised to 75 (+12);
   team B is uniform 63. Reports the favorite win rate per attribute. An
   attribute whose curve sits at the mirror baseline has no outcome consumer
   in that driver (e.g. stamina has no consumer in either shipping driver;
   power / the three identity traits differ per driver — see the 2026-06-09
   systems audit in docs/fable/).

Usage:
    python tools/decision_impact_probe.py [--trials 300] [--driver rec|official|both] [--section tactics|attributes|both]

Determinism: every condition uses its own disjoint seed block; same args ->
same numbers. No I/O beyond stdout.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace as dc_replace
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "tools"))

from dodgeball_sim.engine_driver import EngineDriver  # noqa: E402
from dodgeball_sim.models import (  # noqa: E402
    Approach,
    CatchPosture,
    CoachPolicy,
    OpeningRushCommit,
    OpeningRushTarget,
    TargetFocus,
)

from probe_lib import make_match_input, make_player, wilson_ci  # noqa: E402

BASE_RATING = 63.0
ATTR_BUMP = 12.0

# Per-player catch/dodge spread (mean 63) applied to BOTH teams in the tactics
# section; mirrors realistic career-roster variance. See module docstring.
TACTICS_SPREAD = (48, 55, 60, 66, 72, 77)

_POLICY_AXES: tuple[tuple[str, tuple[object, ...]], ...] = (
    ("approach", tuple(Approach)),
    ("target_focus", tuple(TargetFocus)),
    ("catch_posture", tuple(CatchPosture)),
    ("rush_commit", tuple(OpeningRushCommit)),
    ("rush_target", tuple(OpeningRushTarget)),
)

_ATTRIBUTES = (
    "accuracy",
    "power",
    "dodge",
    "catch",
    "stamina",
    "tactical_iq",
    "catch_courage",
    "throw_selection_iq",
    "conditioning_curve",
)


def _build_driver(name: str) -> EngineDriver:
    if name == "rec":
        from dodgeball_sim.rec_engine import RecTier1Driver

        return RecTier1Driver()
    if name == "official":
        from dodgeball_sim.official_engine import OfficialMatchEngineDriver

        return OfficialMatchEngineDriver()
    if name in ("official_cloth", "official_no_sting"):
        # V27 Phase 3: extend the decision-impact measurement onto the cloth /
        # no-sting profiles so the ruleset-balance harness can reuse this probe.
        # Foam path is untouched (the "official" branch above stays the default).
        from dodgeball_sim.official_engine import OfficialMatchEngineDriver

        return OfficialMatchEngineDriver(ruleset=name)
    raise ValueError(f"Unknown driver: {name}")


def _apply_tactics_spread(mi):
    """Give BOTH teams the same per-player catch/dodge spread (mean 63)."""
    lookup = dict(mi.player_lookup)
    for starters in (mi.starters_a, mi.starters_b):
        for index, pid in enumerate(starters):
            player = lookup[pid]
            lookup[pid] = dc_replace(
                player,
                ratings=dc_replace(
                    player.ratings,
                    catch=TACTICS_SPREAD[index],
                    dodge=TACTICS_SPREAD[-1 - index],
                ),
            )
    return dc_replace(mi, player_lookup=lookup)


def _run_condition(
    driver: EngineDriver,
    *,
    trials: int,
    seed_block: int,
    policy_a: CoachPolicy | None = None,
    attr_bump: str | None = None,
    spread: bool = False,
) -> tuple[int, int, int]:
    """Return (a_wins, draws, b_wins) for one condition."""
    a_wins = draws = b_wins = 0
    for trial in range(trials):
        seed = seed_block * 1_000_000 + trial
        mi = make_match_input(
            seed=seed,
            rating_a=BASE_RATING,
            rating_b=BASE_RATING,
            policy_a=policy_a,
            match_id_prefix="dprobe",
        )
        if spread:
            mi = _apply_tactics_spread(mi)
        if attr_bump is not None:
            lookup = dict(mi.player_lookup)
            for pid in mi.starters_a:
                player = lookup[pid]
                ratings = dc_replace(
                    player.ratings, **{attr_bump: int(BASE_RATING + ATTR_BUMP)}
                )
                lookup[pid] = dc_replace(player, ratings=ratings)
            mi = dc_replace(mi, player_lookup=lookup)
        out = driver.run(mi)
        if out.winner_team_id == "fav":
            a_wins += 1
        elif out.winner_team_id is None:
            draws += 1
        else:
            b_wins += 1
    return a_wins, draws, b_wins


def _fmt_row(label: str, a_wins: int, draws: int, b_wins: int, trials: int) -> str:
    win_rate = a_wins / trials if trials else 0.0
    lo, hi = wilson_ci(a_wins, trials)
    return (
        f"  {label:<22} W {win_rate * 100:5.1f}% "
        f"[CI {lo * 100:5.1f}-{hi * 100:5.1f}]   "
        f"D {draws / trials * 100:5.1f}%   L {b_wins / trials * 100:5.1f}%"
    )


def run_tactics_section(driver_name: str, trials: int) -> None:
    driver = _build_driver(driver_name)
    print(
        f"=== Tactic impact ({driver_name}, even teams @ {BASE_RATING:.0f} "
        f"with catch/dodge spread, {trials} trials/option) ==="
    )
    seed_block = 1
    a, d, b = _run_condition(driver, trials=trials, seed_block=seed_block, spread=True)
    print(_fmt_row("BASELINE default", a, d, b, trials))
    for axis, options in _POLICY_AXES:
        print(f"  -- {axis} --")
        for option in options:
            seed_block += 1
            policy = CoachPolicy(**{axis: option})
            a, d, b = _run_condition(
                driver, trials=trials, seed_block=seed_block, policy_a=policy, spread=True
            )
            print(_fmt_row(f"{getattr(option, 'value', option)}", a, d, b, trials))
    print()


def run_attributes_section(driver_name: str, trials: int) -> None:
    driver = _build_driver(driver_name)
    print(
        f"=== Attribute value (+{ATTR_BUMP:.0f} single stat vs uniform {BASE_RATING:.0f}, "
        f"{driver_name}, {trials} trials/attr) ==="
    )
    seed_block = 100
    a, d, b = _run_condition(driver, trials=trials, seed_block=seed_block)
    print(_fmt_row("BASELINE no bump", a, d, b, trials))
    for attr in _ATTRIBUTES:
        seed_block += 1
        a, d, b = _run_condition(
            driver, trials=trials, seed_block=seed_block, attr_bump=attr
        )
        print(_fmt_row(f"+12 {attr}", a, d, b, trials))
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Decision-impact probe (tactics + attribute value)")
    ap.add_argument("--trials", type=int, default=300)
    ap.add_argument("--driver", choices=("rec", "official", "both"), default="both")
    ap.add_argument("--section", choices=("tactics", "attributes", "both"), default="both")
    args = ap.parse_args()

    drivers = ("rec", "official") if args.driver == "both" else (args.driver,)
    for driver_name in drivers:
        if args.section in ("tactics", "both"):
            run_tactics_section(driver_name, args.trials)
        if args.section in ("attributes", "both"):
            run_attributes_section(driver_name, args.trials)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
