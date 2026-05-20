from dodgeball_sim.events import MatchEvent
from dodgeball_sim.official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)
from dodgeball_sim.official_translator import (
    collect_official_metadata,
    translate_events,
)


def _seq_event(eid, thrower="tA", outs=None, catches=None, thrower_out=False):
    return OfficialEvent(
        event_id=eid, kind=OfficialEventKind.SEQUENCE, match_id="m1",
        sequence_id=eid, ball_ids=("b1",), player_ids=(thrower,),
        team_ids=("A",), rule_refs=(RuleReference("20"),),
        replay_summary="",
        payload={
            "kind": "sequence_final", "thrower_id": thrower,
            "thrower_team_id": "A", "outs": outs or [],
            "catches": catches or [], "thrower_out": thrower_out,
        },
    )


def test_translator_prepends_match_start_and_appends_match_end():
    events = translate_events(
        [_seq_event("s1", outs=["vB"])],
        seed=42, team_a_id="A", team_b_id="B",
        starters_a=("tA",), starters_b=("vB",),
        winner_team_id="A",
    )
    assert events[0].event_type == "match_start"
    assert events[-1].event_type == "match_end"
    assert all(isinstance(e, MatchEvent) for e in events)


def test_translator_classifies_hit_caught_miss():
    events = translate_events(
        [
            _seq_event("s1", outs=["vB"]),
            _seq_event("s2", outs=["tA"], catches=["cB"], thrower_out=True),
            _seq_event("s3"),
        ],
        seed=1, team_a_id="A", team_b_id="B",
        starters_a=("tA",), starters_b=("vB", "cB"),
        winner_team_id=None,
    )
    throw_events = [e for e in events if e.event_type == "throw"]
    assert throw_events[0].outcome["kind"] == "hit"
    assert throw_events[1].outcome["kind"] == "caught"
    assert throw_events[2].outcome["kind"] == "miss"


def test_translator_includes_rule_refs_in_outcome():
    events = translate_events(
        [_seq_event("s1", outs=["vB"])],
        seed=1, team_a_id="A", team_b_id="B",
        starters_a=("tA",), starters_b=("vB",),
        winner_team_id="A",
    )
    throw_event = next(e for e in events if e.event_type == "throw")
    assert "20" in throw_event.outcome["rule_refs"]


def test_translator_emits_generic_replay_contract_fields():
    events = translate_events(
        [_seq_event("s1", outs=["vB"])],
        seed=7,
        team_a_id="A",
        team_b_id="B",
        starters_a=("tA",),
        starters_b=("vB",),
        winner_team_id="A",
    )
    throw_event = next(e for e in events if e.event_type == "throw")
    assert throw_event.actors["thrower"] == "tA"
    assert throw_event.actors["target"] == "vB"
    assert throw_event.actors["offense_team"] == "A"
    assert throw_event.actors["defense_team"] == "B"
    assert throw_event.outcome["resolution"] == "hit"
    assert throw_event.outcome["player_out"] == "vB"
    assert throw_event.state_diff["player_out"] == {"team": "B", "player_id": "vB"}


def test_collect_official_metadata_buckets_event_kinds():
    events = [
        OfficialEvent(
            event_id="b1", kind=OfficialEventKind.BALL, match_id="m1",
            rule_refs=(RuleReference("11"),), replay_summary="activated",
        ),
        OfficialEvent(
            event_id="d1", kind=OfficialEventKind.DISCRETION, match_id="m1",
            rule_refs=(RuleReference("13"),), replay_summary="default",
        ),
    ]
    meta = collect_official_metadata(events)
    assert len(meta["ball_events"]) == 1
    assert len(meta["discretion_events"]) == 1
    assert meta["queue_events"] == []
