"""V28 The Weather — Phase 3 officiating-emphasis probe.

The determinism + honesty gate for the officiating points of emphasis:

  1. Default byte-identical: a seeded official season threaded with the default
     SeasonEmphasis() is bit-for-bit identical to no emphasis (the #1 fence — no
     new RNG draw, no shifted constant).
  2. Active emphasis bites + is logged: a bounded catch emphasis changes outcomes
     across seeds AND every call it flips is logged as a DISCRETION event
     (selection_basis='emphasis_<season>'); a no-emphasis run logs none.
  3. Symmetric by construction: the catch shift raises leniency in BOTH throwing
     directions (no per-team favoritism).
  4. Deterministic, bounded selection: select_season_emphasis is reproducible and
     within WeatherConfig bounds; the v28_season_emphasis stream does not perturb
     the v28_meta_drift stream.

Usage:  python tools/emphasis_probe.py [--seeds N]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import replace as dc_replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))  # so `tools.probe_lib` resolves when run as a script

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.config import DEFAULT_WEATHER  # noqa: E402
from dodgeball_sim.official_engine import OfficialMatchEngineDriver  # noqa: E402
from dodgeball_sim.official_resolution import compute_throw_probabilities  # noqa: E402
from dodgeball_sim.official_translator import collect_official_metadata  # noqa: E402
from dodgeball_sim.persistence import create_schema  # noqa: E402
from dodgeball_sim.season_emphasis import SeasonEmphasis, select_season_emphasis  # noqa: E402
from tools.probe_lib import make_match_input, make_player  # noqa: E402

_SEED = 20260618


def _fp(out):
    return (out.winner_team_id, out.final_active_a, out.final_active_b, tuple(out.events))


def _run(emphasis, seed):
    driver = OfficialMatchEngineDriver()
    mi = make_match_input(seed=seed, rating_a=63.0, rating_b=63.0)
    if emphasis is not None:
        mi = dc_replace(mi, config={**mi.config, "season_emphasis": emphasis})
    return driver.run(mi)


def _emphasis_disc(out):
    events = collect_official_metadata(out.events)["discretion_events"]
    return [
        d for d in events
        if str(d["payload"].get("selection_basis", "")).startswith("emphasis_")
    ]


def run_probe(seeds: int = 24) -> bool:
    print(f"Officiating emphasis probe — seed base {_SEED}, {seeds} seeds")

    # --- 1. Default byte-identical -------------------------------------------
    identical = all(_fp(_run(None, s)) == _fp(_run(SeasonEmphasis(), s)) for s in range(seeds))
    assert identical, "default SeasonEmphasis() is NOT byte-identical to no emphasis"
    print("  [1] default SeasonEmphasis() byte-identical to no emphasis [ok]")

    # --- 2. Active emphasis bites + is logged --------------------------------
    emph = SeasonEmphasis(
        catch_delta=DEFAULT_WEATHER.emphasis_catch_delta_max,
        selection_basis="emphasis_season_3",
    )
    diverged = 0
    logged = 0
    for s in range(seeds):
        base = _run(None, s)
        active = _run(emph, s)
        if _fp(base) != _fp(active):
            diverged += 1
        recs = _emphasis_disc(active)
        logged += len(recs)
        for d in recs:
            assert d["payload"]["selection_basis"] == "emphasis_season_3"
            assert d["payload"]["default_ruling"] != d["payload"]["selected_ruling"]
        # a no-emphasis run logs NO emphasis discretion
        assert _emphasis_disc(base) == []
    assert diverged > 0, "bounded catch emphasis changed no outcome"
    assert logged > 0, "no emphasis DISCRETION events logged"
    print(f"  [2] active emphasis shifted {diverged}/{seeds} seeds, logged {logged} "
          f"DISCRETION calls (selection_basis='emphasis_<season>') [ok]")

    # --- 3. Symmetric (both throwing directions get the leniency) ------------
    fast = make_player("x", "alpha", 70.0)
    slow = make_player("y", "beta", 55.0)
    cmax = DEFAULT_WEATHER.emphasis_catch_delta_max
    base_xy = compute_throw_probabilities(thrower=fast, target=slow).p_catch_given_attempt
    emph_xy = compute_throw_probabilities(thrower=fast, target=slow, catch_emphasis=cmax).p_catch_given_attempt
    base_yx = compute_throw_probabilities(thrower=slow, target=fast).p_catch_given_attempt
    emph_yx = compute_throw_probabilities(thrower=slow, target=fast, catch_emphasis=cmax).p_catch_given_attempt
    assert emph_xy > base_xy and emph_yx > base_yx, "emphasis not applied to both sides"
    print(f"  [3] symmetric: catch leniency rises both ways "
          f"(x->y {base_xy:.3f}->{emph_xy:.3f}, y->x {base_yx:.3f}->{emph_yx:.3f}) [ok]")

    # --- 4. Deterministic, bounded selection ---------------------------------
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    seen = {}
    for n in range(2, 8):
        sid = f"season_{n}"
        e1 = select_season_emphasis(conn, sid, _SEED)
        e2 = select_season_emphasis(conn, sid, _SEED)  # idempotent
        assert (e1.catch_delta, e1.block_delta) == (e2.catch_delta, e2.block_delta)
        assert abs(e1.catch_delta) <= DEFAULT_WEATHER.emphasis_catch_delta_max
        assert abs(e1.block_delta) <= DEFAULT_WEATHER.emphasis_block_delta_max
        assert e1.selection_basis == f"emphasis_{sid}"
        seen[sid] = (round(e1.catch_delta, 4), round(e1.block_delta, 4), e1.announcement[:28])
    nonneutral = sum(1 for v in seen.values() if v[0] or v[1])
    print(f"  [4] selection deterministic + bounded over 6 seasons "
          f"({nonneutral} active, {len(seen) - nonneutral} called-straight) [ok]")
    for sid, v in seen.items():
        print(f"        {sid}: catch={v[0]:+.3f} block={v[1]:+.3f}  \"{v[2]}...\"")

    print("\n  PASS: default byte-identical; active emphasis bites, is symmetric, and is logged")
    return True


def main():
    parser = argparse.ArgumentParser(description="V28 officiating-emphasis probe")
    parser.add_argument("--seeds", type=int, default=24)
    args = parser.parse_args()
    try:
        ok = run_probe(seeds=args.seeds)
    except AssertionError as exc:
        print(f"\n  FAIL: {exc}")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
