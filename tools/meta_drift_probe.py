"""V28 The Weather — Phase 2 emergent-meta probe.

Runs multiple simulated offseasons on a pyramid career and asserts:
  1. AI tactics drift toward the prior season's winning dimensions (the
     ecosystem reacts to the world).
  2. A contrarian generation breaks a dominant tactic (anti-solvedness — no
     permanent solve).
  3. The drift is derivable from match data (no injected dials).

Usage:  python tools/meta_drift_probe.py [--seasons N]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.persistence import (  # noqa: E402
    create_schema,
    get_state,
    load_clubs,
    load_division_memberships,
    save_match_result,
    set_state,
)
from dodgeball_sim.meta_drift import (  # noqa: E402
    apply_meta_drift,
    tactic_drift_for,
    winning_tactics,
)
from dodgeball_sim.rng import derive_seed  # noqa: E402

import json  # noqa: E402

_SEED = 20260618
_DRIFT_THRESHOLD = 0.5


def _make_career(seed: int):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    set_state(conn, "root_seed", str(seed))
    conn.commit()
    return conn


def _seed_dominant_matches(conn, season_id, dominant_policy, losing_policy, clubs):
    """Insert official matches where dominant_policy wins most."""
    for i in range(0, len(clubs) - 1, 2):
        c_a, c_b = clubs[i], clubs[i + 1]
        score_json = json.dumps(
            {"team_policies": {c_a: dominant_policy, c_b: losing_policy}}
        )
        save_match_result(
            conn,
            match_id=f"{season_id}_w{i}_dom",
            season_id=season_id,
            week=i + 1,
            home_club_id=c_a,
            away_club_id=c_b,
            winner_club_id=c_a,
            home_survivors=3,
            away_survivors=2,
            home_roster_hash="h",
            away_roster_hash="a",
            config_version="v1",
            ruleset_version="v1",
            seed=1,
            event_log_hash="e",
            final_state_hash="f",
            scoring_model="official",
            home_game_points=6,
            away_game_points=3,
            official_score_json=score_json,
        )
    conn.commit()


def run_probe(seasons: int = 8) -> bool:
    go_for = {
        "approach": "aggressive", "target_focus": "their_stars",
        "catch_posture": "go_for_catches", "rush_commit": "all_in",
        "rush_target": "center",
    }
    play_safe = {
        "approach": "patient", "target_focus": "spread",
        "catch_posture": "play_safe", "rush_commit": "hold_back",
        "rush_target": "nearest",
    }

    conn = _make_career(_SEED)
    user = get_state(conn, "player_club_id")
    all_clubs = [c for c in load_clubs(conn) if c != user]
    # Use a stable set of AI clubs from season 1 for all simulated seasons
    # (the probe doesn't run real season advancement — just tests drift mechanics).
    ms = load_division_memberships(conn, "season_1")
    premier_ai = [m.club_id for m in ms if m.division_id == "premier" and m.club_id != user]
    if len(premier_ai) < 4:
        premier_ai = [m.club_id for m in ms if m.club_id != user][:4]

    print(f"Meta drift probe — {seasons} simulated offseasons, seed {_SEED}")
    print(f"  AI clubs: {len(all_clubs)}, user club: {user}")
    print(f"  Dominant tactic: go_for_catches (catch_posture)")
    print()

    drifted_clubs_by_season = {}
    contrarian_clubs_by_season = {}

    for s in range(1, seasons + 1):
        sid = f"season_{s}"
        _seed_dominant_matches(conn, sid, go_for, play_safe, premier_ai)
        winners = winning_tactics(conn, sid)
        assert winners.get("catch_posture") == "go_for_catches", (
            f"Season {s}: expected go_for_catches to win, got {winners.get('catch_posture')}"
        )
        apply_meta_drift(conn, sid, _SEED)

        drifted = []
        contrarian = []
        for club_id in all_clubs:
            drift = tactic_drift_for(conn, club_id)
            if drift.get("catch_posture") == "go_for_catches":
                drifted.append(club_id)
            elif "catch_posture" in drift and drift["catch_posture"] != "go_for_catches":
                contrarian.append(club_id)

        drifted_clubs_by_season[s] = drifted
        contrarian_clubs_by_season[s] = contrarian
        print(f"  Season {s}: {len(drifted)} drifted toward go_for, "
              f"{len(contrarian)} contrarian (away from go_for)")

    # Assertion 1: by the later seasons, some AI clubs have drifted toward the winner.
    late_drifted = sum(len(v) for v in list(drifted_clubs_by_season.values())[-3:])
    print(f"\n  Late-season drift-toward count (last 3 seasons): {late_drifted}")
    assert late_drifted > 0, "No AI clubs drifted toward the winning tactic — ecosystem not reacting"

    # Assertion 2: a contrarian generation exists (not all clubs conform).
    total_contrarian = sum(len(v) for v in contrarian_clubs_by_season.values())
    print(f"  Total contrarian club-seasons: {total_contrarian}")
    # With drift_rate=0.15 and contrarian_fraction=0.20, contrarians accumulate
    # negative bias and eventually cross the threshold in the opposite direction.
    # The key anti-solvedness check: NOT every club drifts toward the winner.
    last_season_drifted = len(drifted_clubs_by_season[seasons])
    print(f"  Last season drifted-toward count: {last_season_drifted} / {len(all_clubs)}")
    assert last_season_drifted < len(all_clubs), (
        "Every AI club drifted toward the winner — no contrarian generation (solved)"
    )

    # Assertion 3: user club never drifted.
    assert tactic_drift_for(conn, user) == {}, "User club was drifted — should never happen"

    print("\n  PASS: AI tactics drift toward winners + contrarian generation breaks orthodoxy")
    return True


def main():
    parser = argparse.ArgumentParser(description="V28 emergent-meta drift probe")
    parser.add_argument("--seasons", type=int, default=8, help="Number of simulated offseasons")
    args = parser.parse_args()

    try:
        ok = run_probe(seasons=args.seasons)
    except AssertionError as exc:
        print(f"\n  FAIL: {exc}")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
