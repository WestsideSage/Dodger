from dodgeball_sim.catch_queue import (
    CatchQueueState,
    block_same_sequence,
    enqueue_out_player,
    out_of_order_entry,
    return_player_on_catch,
    tick_entering,
)


def _queue():
    return CatchQueueState(team_id="A")


def test_catch_returns_first_eligible_queued_player():
    q = _queue()
    enqueue_out_player(q, player_id="p1", is_starter=True, match_id="m1")
    enqueue_out_player(q, player_id="p2", is_starter=True, match_id="m1")
    event, pid = return_player_on_catch(q, sequence_id="s1", match_id="m1")
    assert pid == "p1"
    assert event.player_ids == ("p1",)
    assert q.entering and q.entering.player_id == "p1"


def test_nonstarters_cannot_enter_from_catches():
    q = _queue()
    enqueue_out_player(q, player_id="ns1", is_starter=False, match_id="m1")
    event, pid = return_player_on_catch(q, sequence_id="s1", match_id="m1")
    assert pid is None
    assert event is None
    assert "ns1" in q.nonstarter_ids


def test_same_sequence_blocked_player_is_skipped():
    q = _queue()
    enqueue_out_player(q, player_id="p1", is_starter=True, match_id="m1")
    enqueue_out_player(q, player_id="p2", is_starter=True, match_id="m1")
    block_same_sequence(q, sequence_id="s1", player_id="p1")
    event, pid = return_player_on_catch(q, sequence_id="s1", match_id="m1")
    # p1 is involved in s1 so cannot return from s1
    assert pid == "p2"


def test_out_of_order_entry_sends_player_to_back():
    q = _queue()
    enqueue_out_player(q, player_id="p1", is_starter=True, match_id="m1")
    enqueue_out_player(q, player_id="p2", is_starter=True, match_id="m1")
    enqueue_out_player(q, player_id="p3", is_starter=True, match_id="m1")
    event = out_of_order_entry(q, attempting_player_id="p2", match_id="m1")
    assert q.queued_ids == ["p1", "p3", "p2"]
    assert event.payload["kind"] == "out_of_order_entry"


def test_entering_window_expires_after_5_seconds_default():
    q = _queue()
    enqueue_out_player(q, player_id="p1", is_starter=True, match_id="m1")
    return_player_on_catch(q, sequence_id="s1", match_id="m1")
    assert q.entering is not None
    miss_event = tick_entering(q, seconds=5)
    assert miss_event is not None
    assert q.entering is None
    assert "p1" in q.queued_ids  # bumped to back


def test_no_eligible_when_queue_empty():
    q = _queue()
    event, pid = return_player_on_catch(q, sequence_id="s1", match_id="m1")
    assert event is None and pid is None
