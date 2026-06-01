"""WT-6: the defender's OWN catch posture governs the defender's catch attempts.

The catch decision inside ``resolve_throw`` is the target/defender's decision.
Before the fix the official engine handed it the *offense* team's policy, so
choosing "go for catches" made the *opponent* more likely to catch your throws
— tactics were inverted. This pins the corrected wiring with an asymmetric,
same-seed A/B: the only thing that differs between the two runs is which team
holds GO_FOR_CATCHES, and the defender that goes for catches must out-catch the
one that plays safe. On the pre-fix code this assertion inverts and fails.
"""

from __future__ import annotations

from dodgeball_sim.models import CatchPosture, CoachPolicy
from dodgeball_sim.official_engine import OfficialMatchEngineDriver
from dodgeball_sim.official_events import OfficialEventKind
from tools.probe_lib import make_match_input

GO = CoachPolicy(catch_posture=CatchPosture.GO_FOR_CATCHES)
SAFE = CoachPolicy(catch_posture=CatchPosture.PLAY_SAFE)


def _dog_defensive_catches(events) -> int:
    """Catches credited to team 'dog' when 'fav' threw (i.e. dog defending)."""
    total = 0
    for ev in events:
        if ev.kind != OfficialEventKind.SEQUENCE:
            continue
        payload = ev.payload or {}
        if payload.get("kind") != "sequence_final":
            continue
        if payload.get("thrower_team_id") == "fav" and payload.get("catches"):
            total += len(payload.get("catches"))
    return total


def _dog_catches(seed: int, policy_fav: CoachPolicy, policy_dog: CoachPolicy) -> int:
    driver = OfficialMatchEngineDriver()
    out = driver.run(make_match_input(seed, policy_a=policy_fav, policy_b=policy_dog))
    return _dog_defensive_catches(out.events)


def test_defenders_own_catch_posture_drives_its_catches():
    seeds = range(12)
    dog_go = sum(_dog_catches(s, SAFE, GO) for s in seeds)    # dog defends with GO_FOR_CATCHES
    dog_safe = sum(_dog_catches(s, GO, SAFE) for s in seeds)  # dog defends with PLAY_SAFE
    # The defender that goes for catches must out-catch the one that plays safe.
    # Pre-fix the thrower's posture drove the defender, inverting this.
    assert dog_go > dog_safe, (
        f"defender's own posture must drive its catches: GO={dog_go} SAFE={dog_safe}"
    )
