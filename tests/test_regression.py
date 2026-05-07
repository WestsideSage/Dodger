from __future__ import annotations

import json
from pathlib import Path

from dodgeball_sim.engine import MatchEngine
from dodgeball_sim.models import CoachPolicy

from .factories import make_match_setup, make_player, make_team

_GOLDEN_FILE = Path(__file__).parent / "golden_logs" / "phase1_baseline.json"


def _baseline_setup():
    aurora_policy = CoachPolicy(target_stars=0.75, risk_tolerance=0.55, sync_throws=0.3, tempo=0.45, rush_frequency=0.4)
    lunar_policy = CoachPolicy(target_stars=0.65, risk_tolerance=0.5, sync_throws=0.25, tempo=0.5, rush_frequency=0.5)

    aurora = make_team(
        "aurora",
        [
            make_player("aurora_captain", accuracy=78, power=72, dodge=60, catch=55),
            make_player("aurora_scout", accuracy=68, power=52, dodge=64, catch=58),
            make_player("aurora_rookie", accuracy=60, power=50, dodge=52, catch=65),
        ],
        policy=aurora_policy,
        chemistry=0.58,
        name="Aurora Sentinels",
    )

    lunar = make_team(
        "lunar",
        [
            make_player("lunar_captain", accuracy=75, power=70, dodge=57, catch=50),
            make_player("lunar_anchor", accuracy=65, power=60, dodge=62, catch=70),
            make_player("lunar_spotter", accuracy=55, power=48, dodge=58, catch=60),
        ],
        policy=lunar_policy,
        chemistry=0.52,
        name="Lunar Syndicate",
    )

    return make_match_setup(aurora, lunar)


def test_phase_one_golden_log_regression():
    engine = MatchEngine()
    setup = _baseline_setup()
    result = engine.run(setup, seed=31415)
    result_dict = result.to_dict()

    with _GOLDEN_FILE.open("r", encoding="utf-8") as handle:
        golden = json.load(handle)

    assert result_dict == golden

