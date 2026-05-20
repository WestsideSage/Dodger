from dodgeball_sim.flood_throws import (
    FloodThrowTracker,
    FLOOD_THRESHOLD,
    PendingThrow,
)


def test_flood_threshold_is_three():
    assert FLOOD_THRESHOLD == 3


def test_no_flood_with_two_throws():
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow(thrower_id="p1", team_id="a", tick=5))
    tracker.record(PendingThrow(thrower_id="p2", team_id="a", tick=5))
    detected = tracker.detect_flood(tick=5)
    assert detected is None


def test_flood_with_three_same_team_same_tick():
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "a", 5))
    detected = tracker.detect_flood(tick=5)
    assert detected is not None
    assert detected.team_id == "a"
    assert set(detected.thrower_ids) == {"p1", "p2", "p3"}


def test_no_flood_across_different_teams():
    """Three throws in one tick split 2-1 across teams should not flood."""
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "b", 5))
    detected = tracker.detect_flood(tick=5)
    assert detected is None


def test_flood_clears_per_tick():
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "a", 5))
    assert tracker.detect_flood(tick=5) is not None
    # Next tick starts clean
    tracker.record(PendingThrow("p4", "a", 6))
    assert tracker.detect_flood(tick=6) is None


def test_flood_records_team_with_majority_when_split_above_threshold():
    """4-1 split: flood credited to the majority team."""
    tracker = FloodThrowTracker()
    tracker.record(PendingThrow("p1", "a", 5))
    tracker.record(PendingThrow("p2", "a", 5))
    tracker.record(PendingThrow("p3", "a", 5))
    tracker.record(PendingThrow("p4", "a", 5))
    tracker.record(PendingThrow("p5", "b", 5))
    detected = tracker.detect_flood(tick=5)
    assert detected is not None
    assert detected.team_id == "a"
    assert len(detected.thrower_ids) == 4
