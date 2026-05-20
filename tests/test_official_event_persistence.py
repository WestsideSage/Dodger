from dodgeball_sim.official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)
from dodgeball_sim.official_persistence import (
    event_from_dict,
    event_to_dict,
    events_from_json,
    events_to_json,
    replay_state_from_events,
)


def _ev():
    return OfficialEvent(
        event_id="e1",
        kind=OfficialEventKind.SEQUENCE,
        match_id="m1",
        game_id="g1",
        sequence_id="s7",
        ball_ids=("b1",),
        player_ids=("p1", "p2"),
        team_ids=("A", "B"),
        rule_refs=(RuleReference("20"), RuleReference("22", "b")),
        replay_summary="catch resolved",
        payload={"resolution": "catch", "outs": ["p1"]},
    )


def test_round_trip_preserves_all_envelope_fields():
    original = _ev()
    restored = event_from_dict(event_to_dict(original))
    assert restored == original


def test_json_round_trip_for_list():
    events = [_ev(), _ev()]
    restored = events_from_json(events_to_json(events))
    assert restored == events


def test_round_trip_preserves_version_fields():
    original = _ev()
    d = event_to_dict(original)
    assert d["official_payload_version"] == original.official_payload_version
    assert d["ruleset_version"] == original.ruleset_version
    assert d["rulebook_version"] == original.rulebook_version


def test_replay_state_from_events_includes_rule_calls():
    state = replay_state_from_events(ruleset="foam-open", events=[_ev()])
    assert state.ruleset == "foam-open"
    labels = [c.rule_label for c in state.rule_calls]
    assert "20" in labels
    assert "22.b" in labels
    assert len(state.events) == 1


def test_replay_state_empty_events_is_valid():
    state = replay_state_from_events(ruleset="cloth-open", events=[])
    assert state.ruleset == "cloth-open"
    assert state.events == ()
    assert state.rule_calls == ()
