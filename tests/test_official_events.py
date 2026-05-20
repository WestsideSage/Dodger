from dodgeball_sim.official_events import (
    OFFICIAL_PAYLOAD_VERSION,
    RULEBOOK_VERSION,
    RULESET_VERSION,
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)


def test_rule_reference_label():
    assert RuleReference("14", "g.4").as_label() == "14.g.4"
    assert RuleReference("22").as_label() == "22"


def test_official_event_carries_version_fields():
    event = OfficialEvent(
        event_id="evt-1",
        kind=OfficialEventKind.BALL,
        match_id="m1",
        rule_refs=(RuleReference("11"),),
        replay_summary="ball activated",
    )
    assert event.official_payload_version == OFFICIAL_PAYLOAD_VERSION
    assert event.ruleset_version == RULESET_VERSION
    assert event.rulebook_version == RULEBOOK_VERSION
    assert event.game_id is None
    assert event.sequence_id is None
    assert event.rule_labels() == ("11",)


def test_official_event_accepts_optional_context():
    event = OfficialEvent(
        event_id="evt-2",
        kind=OfficialEventKind.SEQUENCE,
        match_id="m1",
        game_id="g1",
        sequence_id="s7",
        ball_ids=("b1",),
        player_ids=("p1", "p2"),
        team_ids=("A", "B"),
        rule_refs=(RuleReference("20"), RuleReference("22", "b.xiii")),
        replay_summary="catch resolved",
        payload={"resolution": "catch"},
    )
    assert event.payload["resolution"] == "catch"
    assert event.rule_labels() == ("20", "22.b.xiii")
