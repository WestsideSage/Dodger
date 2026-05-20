from dodgeball_sim.official_events import (
    OFFICIAL_PAYLOAD_VERSION,
    RULEBOOK_VERSION,
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)
from dodgeball_sim.replay_contracts import (
    OfficialBallView,
    OfficialBurdenView,
    OfficialClockView,
    OfficialGameScoreView,
    OfficialReplayState,
    OfficialRuleCallView,
    OfficialSequenceView,
    OfficialTeamStateView,
    empty_replay_state,
)


def test_empty_replay_state_has_version_fields():
    s = empty_replay_state("foam-open")
    assert s.ruleset == "foam-open"
    assert s.rulebook_version == RULEBOOK_VERSION
    assert s.official_payload_version == OFFICIAL_PAYLOAD_VERSION
    assert s.balls == ()
    assert s.teams == ()
    assert s.rule_calls == ()
    assert s.events == ()


def test_replay_state_accepts_all_views():
    state = OfficialReplayState(
        ruleset="cloth-open",
        match_clock=OfficialClockView(limit_seconds=1440, elapsed_seconds=120),
        game_clock=OfficialClockView(limit_seconds=180, elapsed_seconds=30),
        game_score=OfficialGameScoreView("A", "B", team_a_games=1),
        mode="no_blocking",
        burden=OfficialBurdenView(team_id="A", basis="ball_majority", clock_status="active", seconds_remaining=3),
        balls=(OfficialBallView(ball_id="b1", state="held", side="A", controller_player_id="p1"),),
        teams=(OfficialTeamStateView(team_id="A", active_ids=("p1",), queued_ids=("p2",)),),
        player_statuses={"p1": "active", "p2": "queued"},
        active_sequences=(OfficialSequenceView(sequence_id="s1", thrower_id="p1", ball_id="b1"),),
        rule_calls=(OfficialRuleCallView(rule_label="14.g.4", summary="play 2 balls"),),
        events=(
            OfficialEvent(
                event_id="e1",
                kind=OfficialEventKind.BURDEN,
                match_id="m1",
                rule_refs=(RuleReference("14"),),
                replay_summary="burden established",
            ),
        ),
    )
    assert state.mode == "no_blocking"
    assert state.burden.basis == "ball_majority"
    assert state.balls[0].controller_player_id == "p1"
    assert state.events[0].rule_labels() == ("14",)


def test_generic_replay_payload_remains_valid_without_official_state():
    # The contract is optional from the frontend's perspective; this test
    # serves as a marker that nothing here forces existing replay payloads
    # to include OfficialReplayState. (No assertion needed; importability +
    # default constructor is the contract.)
    s = empty_replay_state("foam-open")
    assert isinstance(s, OfficialReplayState)
