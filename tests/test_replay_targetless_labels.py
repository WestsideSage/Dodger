"""WT-1: replay never renders ``-`` / ``None`` placeholder targets.

A target-less throw is never a "miss against ``-``". It is one of three real
outcomes that must each read truthfully:

* rec illegal headshot — resolution ``miss``, the *thrower* is marked out;
* official throw-clock / burden violation — resolution ``clock_violation``,
  the thrower is out;
* official throw into space — resolution ``miss``, no one is out.

Across both render paths (``replay_proof`` and ``replay_service``) none of
these may emit ``vs -``, ``targets -``, ``toward -``, ``misses -`` or
``misses None``.
"""

from dodgeball_sim.events import MatchEvent
from dodgeball_sim.replay_proof import event_detail, event_label
from dodgeball_sim.replay_service import replay_event_label

NAME_MAP = {"p1": "Alex Rivera", "p2": "Sam Okoro"}
# Placeholder targets AND the "empty space" framing are both forbidden: in both
# the rec and official engines a target is always selected, so an official miss
# is a dodge/off-target against a real (if id-dropped) defender — never a throw
# into an empty lane.
FORBIDDEN = (
    "vs -", "targets -", "toward -", "misses -", "misses None", "vs None", " to -", " to None",
    "open space", "open floor", "into space", "into traffic", "tags no one",
)


def _proof_event(resolution, *, thrower="p1", target=None, thrower_out=False, tick=5):
    outcome = {"resolution": resolution}
    state_diff = {}
    if thrower_out:
        outcome["thrower_out"] = True
        state_diff = {"player_out": {"team": "A", "player_id": thrower}}
    return {
        "event_type": "throw",
        "tick": tick,
        "actors": {"thrower": thrower, "target": target},
        "outcome": outcome,
        "state_diff": state_diff,
        "probabilities": {},
        "rolls": {},
    }


def _match_event(resolution, *, thrower="p1", target=None, thrower_out=False):
    outcome = {"resolution": resolution}
    state_diff = {}
    if thrower_out:
        outcome["thrower_out"] = True
        state_diff = {"player_out": {"team": "A", "player_id": thrower}}
    return MatchEvent(
        event_id=1, tick=3, seed=7, event_type="throw", phase="live",
        actors={"thrower": thrower, "target": target},
        context={}, probabilities={}, rolls={},
        outcome=outcome, state_diff=state_diff,
    )


def _assert_clean(text):
    for token in FORBIDDEN:
        assert token not in text, f"placeholder {token!r} leaked into: {text!r}"
    assert "Alex Rivera" in text, f"thrower not named in: {text!r}"


def test_rec_headshot_reads_as_a_foul_not_a_miss():
    label = event_label(_proof_event("miss", thrower_out=True), NAME_MAP)
    _assert_clean(label)
    assert "headshot" in label.lower() and "out" in label.lower()


def test_official_clock_violation_reads_as_a_violation():
    label = event_label(_proof_event("clock_violation", thrower_out=True), NAME_MAP)
    _assert_clean(label)
    assert "out" in label.lower()


def test_official_miss_reads_as_clean_miss_not_empty_space():
    # Official 'miss' = a selected defender dodged / off-target throw. It must
    # read as a miss, NOT claim the thrower is out and NOT claim empty space.
    label = event_label(_proof_event("miss", thrower_out=False), NAME_MAP)
    _assert_clean(label)  # _assert_clean already forbids the empty-space framing
    assert "headshot" not in label.lower()
    assert "violation" not in label.lower()
    assert "ruled out" not in label.lower()
    assert "miss" in label.lower() or "connect" in label.lower() or "empty" in label.lower()


def test_event_detail_targetless_never_uses_vs_dash():
    for resolution, thrower_out in (("miss", True), ("clock_violation", True), ("miss", False)):
        detail = event_detail(_proof_event(resolution, thrower_out=thrower_out), NAME_MAP)
        _assert_clean(detail)


def test_replay_service_targetless_labels_are_clean():
    for resolution, thrower_out in (("miss", True), ("clock_violation", True), ("miss", False)):
        label = replay_event_label(_match_event(resolution, thrower_out=thrower_out), NAME_MAP)
        _assert_clean(label)


def test_normal_throw_with_target_still_names_the_target():
    ev = _proof_event("hit", target="p2", thrower_out=False)
    assert "Sam Okoro" in event_label(ev, NAME_MAP)
    assert "Sam Okoro" in event_detail(ev, NAME_MAP)
    me_label = replay_event_label(_match_event("hit", target="p2"), NAME_MAP)
    assert me_label.startswith("HIT:") and "Sam Okoro" in me_label
