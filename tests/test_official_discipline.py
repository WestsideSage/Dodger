import pytest
import json
from dodgeball_sim.catch_queue import CatchQueueState, enqueue_out_player
from dodgeball_sim.official_events import OfficialEvent, OfficialEventKind, RuleReference
from dodgeball_sim.match_lifecycle import OfficialGameState, OfficialGameClock, OfficialGameResult, RulesetProfile
from dodgeball_sim.player_state import OfficialPlayerState, OfficialPlayerStatus
from dodgeball_sim.discipline import (
    WarningRecord,
    BlueCardRecord,
    DisciplineState,
    issue_warning,
    issue_blue_card,
    clear_discipline_blocked,
)
from dodgeball_sim.rulesets import FOAM_OPEN


def _queue(team_id="A"):
    return CatchQueueState(team_id=team_id)


def _game_state():
    clock = OfficialGameClock(limit_seconds=180)
    return OfficialGameState(
        game_number=1,
        profile=FOAM_OPEN,
        clock=clock,
        active_count_a=6,
        active_count_b=6,
    )


def test_issue_warning_records_without_removing():
    state = DisciplineState()
    q = _queue("A")
    players = {
        "p1": OfficialPlayerState(player_id="p1", team_id="A", status=OfficialPlayerStatus.ACTIVE)
    }

    warn_ev, esc_ev = issue_warning(
        state,
        q,
        player_id="p1",
        team_id="A",
        offense="arriving late",
        match_id="m1",
        players=players,
    )

    assert warn_ev is not None
    assert esc_ev is None
    assert warn_ev.kind == OfficialEventKind.DISCIPLINE
    assert warn_ev.rule_refs == (RuleReference("34"),)
    assert "p1" in state.warnings_by_player
    assert state.warnings_by_player["p1"][0].offense == "arriving late"
    assert "A" in state.warnings_by_team
    assert state.warnings_by_team["A"][0].player_id == "p1"
    # Player should still be active
    assert players["p1"].status == OfficialPlayerStatus.ACTIVE
    assert "p1" not in q.queued_ids


def test_same_player_same_offense_twice_escalates_to_blue():
    state = DisciplineState()
    q = _queue("A")
    players = {
        "p1": OfficialPlayerState(player_id="p1", team_id="A", status=OfficialPlayerStatus.ACTIVE)
    }
    game = _game_state()

    # First warning
    warn_ev1, esc_ev1 = issue_warning(
        state,
        q,
        player_id="p1",
        team_id="A",
        offense="arguing",
        match_id="m1",
        players=players,
        game_state=game,
        team_a_id="A",
    )
    assert warn_ev1 is not None
    assert esc_ev1 is None

    # Second warning for same offense -> Escalate to blue card
    warn_ev2, esc_ev2 = issue_warning(
        state,
        q,
        player_id="p1",
        team_id="A",
        offense="arguing",
        match_id="m1",
        players=players,
        game_state=game,
        team_a_id="A",
    )
    assert warn_ev2 is None
    assert esc_ev2 is not None
    assert esc_ev2.kind == OfficialEventKind.DISCIPLINE
    assert esc_ev2.rule_refs == (RuleReference("35"),)

    # Player should be in queue and blocked
    assert players["p1"].status == OfficialPlayerStatus.BLUE_CARD_QUEUE
    assert q.queued_ids == ["p1"]
    assert "p1" in q.discipline_blocked_ids
    assert game.active_count_a == 5


def test_blue_card_moves_player_to_back_of_queue():
    state = DisciplineState()
    q = _queue("A")
    players = {
        "p1": OfficialPlayerState(player_id="p1", team_id="A", status=OfficialPlayerStatus.ACTIVE),
        "p2": OfficialPlayerState(player_id="p2", team_id="A", status=OfficialPlayerStatus.ACTIVE),
    }

    # Put p2 in queue first
    enqueue_out_player(q, player_id="p2", is_starter=True, match_id="m1")
    assert q.queued_ids == ["p2"]

    # Issue blue card to p1
    blue_ev, placeholder = issue_blue_card(
        state,
        q,
        player_id="p1",
        team_id="A",
        offense="pinch throw",
        match_id="m1",
        players=players,
    )
    assert blue_ev is not None
    assert placeholder is None

    # Player 1 is added to the back of the queue
    assert q.queued_ids == ["p2", "p1"]
    assert "p1" in q.discipline_blocked_ids
    assert players["p1"].status == OfficialPlayerStatus.BLUE_CARD_QUEUE

    # Test clear_discipline_blocked
    clear_discipline_blocked(q, "p1")
    assert "p1" not in q.discipline_blocked_ids


def test_blue_card_on_only_live_player_forfeits_game():
    state = DisciplineState()
    q = _queue("A")
    players = {
        "p1": OfficialPlayerState(player_id="p1", team_id="A", status=OfficialPlayerStatus.ACTIVE),
        "p2": OfficialPlayerState(player_id="p2", team_id="A", status=OfficialPlayerStatus.QUEUED),
    }
    game = _game_state()
    game.active_count_a = 1

    blue_ev, forfeit_ev = issue_blue_card(
        state,
        q,
        player_id="p1",
        team_id="A",
        offense="interference",
        match_id="m1",
        players=players,
        game_state=game,
        team_a_id="A",
    )

    assert blue_ev is not None
    assert forfeit_ev is not None
    assert forfeit_ev.kind == OfficialEventKind.DISCIPLINE
    assert forfeit_ev.payload["kind"] == "game_forfeit"
    assert forfeit_ev.payload["forfeit_result"] == "forfeit_a"
    assert game.result == OfficialGameResult.FORFEIT_A


def test_second_blue_card_same_offense_emits_yellow_placeholder():
    state = DisciplineState()
    q = _queue("A")
    players = {
        "p1": OfficialPlayerState(player_id="p1", team_id="A", status=OfficialPlayerStatus.ACTIVE),
        "p2": OfficialPlayerState(player_id="p2", team_id="A", status=OfficialPlayerStatus.ACTIVE)
    }
    game = _game_state()

    # First blue card
    issue_blue_card(
        state,
        q,
        player_id="p1",
        team_id="A",
        offense="pinch throw",
        match_id="m1",
        players=players,
        game_state=game,
        team_a_id="A",
    )

    # Second blue card for same offense
    blue_ev, yellow_ev = issue_blue_card(
        state,
        q,
        player_id="p1",
        team_id="A",
        offense="pinch throw",
        match_id="m1",
        players=players,
        game_state=game,
        team_a_id="A",
    )

    assert blue_ev is not None
    assert yellow_ev is not None
    assert yellow_ev.kind == OfficialEventKind.DISCIPLINE
    assert yellow_ev.payload["kind"] == "yellow_card_placeholder"
    assert yellow_ev.payload["deferred"] is True
    assert ("p1", "pinch throw") in state.yellow_card_placeholder_emitted


def test_discipline_state_serialization():
    state = DisciplineState()
    q = _queue("A")
    players = {
        "p1": OfficialPlayerState(player_id="p1", team_id="A", status=OfficialPlayerStatus.ACTIVE)
    }

    issue_warning(state, q, player_id="p1", team_id="A", offense="arguing", match_id="m1", players=players)
    issue_blue_card(state, q, player_id="p1", team_id="A", offense="pinch throw", match_id="m1", players=players)
    # Second blue card triggers yellow placeholder
    issue_blue_card(state, q, player_id="p1", team_id="A", offense="pinch throw", match_id="m1", players=players)

    serialized = state.to_dict()
    deserialized = DisciplineState.from_dict(serialized)

    assert deserialized.warnings_by_player == state.warnings_by_player
    assert deserialized.warnings_by_team == state.warnings_by_team
    assert len(deserialized.blue_cards_by_player["p1"]) == len(state.blue_cards_by_player["p1"])
    assert deserialized.blue_cards_by_player["p1"][0].offense == state.blue_cards_by_player["p1"][0].offense
    assert deserialized.yellow_card_placeholder_emitted == state.yellow_card_placeholder_emitted

    # Verify JSON encoding/decoding works
    json_str = json.dumps(serialized)
    loaded = json.loads(json_str)
    deserialized_json = DisciplineState.from_dict(loaded)
    assert deserialized_json.yellow_card_placeholder_emitted == state.yellow_card_placeholder_emitted
