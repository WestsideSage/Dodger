import random

import pytest

from dodgeball_sim.ball_state import BallState, OfficialBall
from dodgeball_sim.burden import BurdenBasis, BurdenState, ThrowClockStatus
from dodgeball_sim.official_actions import (
    ActionSelector,
    CatchAttemptAction,
    EnterCourtAction,
    LegalActionGenerator,
    ProactiveKind,
    ReactiveKind,
    RetrieveAction,
    ThrowAction,
    WaitAction,
    request_reactive_action,
)
from dodgeball_sim.player_state import OfficialPlayerState, OfficialPlayerStatus
from dodgeball_sim.rulesets import BallMaterial


def _player(pid, team, status=OfficialPlayerStatus.ACTIVE, is_starter=True):
    return OfficialPlayerState(
        player_id=pid, team_id=team, status=status, is_starter=is_starter
    )


def _ball(bid, side, controller=None, activated=True, state=BallState.HELD):
    return OfficialBall(
        ball_id=bid, material=BallMaterial.FOAM, side=side,
        state=state, controller_player_id=controller, activated=activated,
    )


def test_legal_actions_exclude_inactive_queued_suspended():
    players = {
        "pA1": _player("pA1", "A"),
        "pA2": _player("pA2", "A", status=OfficialPlayerStatus.QUEUED),
        "pA3": _player("pA3", "A", status=OfficialPlayerStatus.SUSPENDED),
        "pA4": _player("pA4", "A", status=OfficialPlayerStatus.INACTIVE_NONSTARTER),
    }
    gen = LegalActionGenerator(players=players, balls=[])
    assert gen.for_player("pA1")  # active
    assert gen.for_player("pA2") == []
    assert gen.for_player("pA3") == []
    assert gen.for_player("pA4") == []


def test_entering_player_only_gets_enter_court_action():
    players = {"pE": _player("pE", "A", status=OfficialPlayerStatus.ENTERING)}
    actions = LegalActionGenerator(players=players, balls=[]).for_player("pE")
    assert len(actions) == 1
    assert isinstance(actions[0], EnterCourtAction)


def test_held_ball_yields_throw_action():
    players = {"pA1": _player("pA1", "A")}
    balls = [_ball("b1", "A", controller="pA1")]
    actions = LegalActionGenerator(players=players, balls=balls).for_player("pA1")
    throws = [a for a in actions if isinstance(a, ThrowAction)]
    assert len(throws) == 1
    assert throws[0].ball_id == "b1"


def test_zero_called_removes_wait_for_burden_team():
    players = {"pA1": _player("pA1", "A")}
    balls = [_ball("b1", "A", controller="pA1")]
    burden = BurdenState(
        team_id="A", basis=BurdenBasis.BALL_MAJORITY,
        clock_status=ThrowClockStatus.ZERO_CALLED,
    )
    actions = LegalActionGenerator(players=players, balls=balls, burden=burden).for_player("pA1")
    assert not any(isinstance(a, WaitAction) for a in actions)
    assert any(isinstance(a, ThrowAction) for a in actions)


def test_zero_called_does_not_affect_non_burden_team():
    players = {"pB1": _player("pB1", "B")}
    balls = [_ball("b1", "B", controller="pB1")]
    burden = BurdenState(
        team_id="A", basis=BurdenBasis.BALL_MAJORITY,
        clock_status=ThrowClockStatus.ZERO_CALLED,
    )
    actions = LegalActionGenerator(players=players, balls=balls, burden=burden).for_player("pB1")
    assert any(isinstance(a, WaitAction) for a in actions)


def test_free_ball_on_team_side_yields_retrieve_action():
    players = {"pA1": _player("pA1", "A")}
    balls = [_ball("b1", "A", controller=None, state=BallState.ACTIVATED_FREE)]
    actions = LegalActionGenerator(players=players, balls=balls).for_player("pA1")
    retrieves = [a for a in actions if isinstance(a, RetrieveAction)]
    assert len(retrieves) == 1


def test_action_selector_is_deterministic_for_seed():
    players = {f"pA{i}": _player(f"pA{i}", "A") for i in range(3)}
    gen = LegalActionGenerator(players=players, balls=[])
    actions = gen.all_legal()
    selector_a = ActionSelector(random.Random(42))
    selector_b = ActionSelector(random.Random(42))
    a = selector_a.select(actions)
    b = selector_b.select(actions)
    assert a == b


def test_action_selector_respects_weights():
    players = {"pA1": _player("pA1", "A")}
    actions = LegalActionGenerator(players=players, balls=[]).for_player("pA1")
    selector = ActionSelector(random.Random(1))
    # Force WAIT by giving it overwhelming weight
    weights = [100.0 if isinstance(a, WaitAction) else 0.0 for a in actions]
    chosen = selector.select(actions, weights=weights)
    assert isinstance(chosen, WaitAction)


def test_request_reactive_action_rejects_non_active_player():
    queued = _player("p1", "A", status=OfficialPlayerStatus.QUEUED)
    with pytest.raises(ValueError):
        request_reactive_action(actor=queued, kind=ReactiveKind.CATCH_ATTEMPT, ball_id="b1")


def test_request_reactive_action_builds_catch_attempt():
    active = _player("p1", "A")
    action = request_reactive_action(actor=active, kind=ReactiveKind.CATCH_ATTEMPT, ball_id="b1")
    assert isinstance(action, CatchAttemptAction)
    assert action.ball_id == "b1"
