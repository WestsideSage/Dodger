from dodgeball_sim.official_events import OfficialEventKind
from dodgeball_sim.rule_discretion import RuleDiscretionEvent


def test_rule_discretion_serializes_as_official_event():
    discretion = RuleDiscretionEvent(
        rule_section="14",
        trigger="cloth-equal-ball-burden",
        default_ruling="invert-previous-burden",
        alternative_rulings=("award-to-reachable-side",),
        selected_ruling="invert-previous-burden",
        selection_basis="default",
        replay_summary="Equal balls; previous burden inverted.",
    )

    event = discretion.to_official_event(
        event_id="evt-1",
        match_id="m1",
        game_id="g1",
        team_ids=("A", "B"),
        rule_clause="d",
    )

    assert event.kind == OfficialEventKind.DISCRETION
    assert event.rule_labels() == ("14.d",)
    assert event.payload["default_ruling"] == "invert-previous-burden"
    assert event.payload["selected_ruling"] == "invert-previous-burden"
    assert event.payload["selection_basis"] == "default"
    assert event.replay_summary.startswith("Equal balls")


def test_rule_discretion_non_default_selection_records_basis():
    discretion = RuleDiscretionEvent(
        rule_section="33",
        trigger="undocumented-state",
        default_ruling="reset-sequence",
        alternative_rulings=("forfeit-game", "no-call"),
        selected_ruling="no-call",
        selection_basis="official",
        replay_summary="Undocumented state, official chose no-call.",
    )
    event = discretion.to_official_event(event_id="evt-2", match_id="m1")
    assert event.payload["selected_ruling"] == "no-call"
    assert event.payload["selection_basis"] == "official"
