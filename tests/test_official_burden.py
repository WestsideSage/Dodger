from dodgeball_sim.burden import (
    BurdenBasis,
    burden_event,
    cloth_play_n_call,
    cloth_play_n_failure,
    establish_burden,
    foam_failure_forfeit,
    reset_burden_after_valid_throw,
)
from dodgeball_sim.rulesets import CLOTH_OPEN, FOAM_OPEN, NO_STING_OPEN


def _ctrls(a_count, b_count):
    out = {}
    for i in range(a_count):
        out[f"a{i}"] = "A"
    for i in range(b_count):
        out[f"b{i}"] = "B"
    return out


def test_foam_burden_by_ball_majority():
    state, disc = establish_burden(
        FOAM_OPEN,
        ball_controllers=_ctrls(4, 2),
        live_player_counts={"A": 6, "B": 6},
        previous_burden_team_id=None,
        team_a_id="A",
        team_b_id="B",
    )
    assert state.team_id == "A"
    assert state.basis == BurdenBasis.BALL_MAJORITY
    assert disc is None


def test_foam_burden_falls_through_to_player_majority():
    state, _ = establish_burden(
        FOAM_OPEN,
        ball_controllers=_ctrls(3, 3),
        live_player_counts={"A": 5, "B": 6},
        previous_burden_team_id=None,
        team_a_id="A",
        team_b_id="B",
    )
    assert state.team_id == "B"
    assert state.basis == BurdenBasis.PLAYER_MAJORITY


def test_foam_burden_inverts_prior_when_all_tied():
    state, _ = establish_burden(
        FOAM_OPEN,
        ball_controllers=_ctrls(3, 3),
        live_player_counts={"A": 5, "B": 5},
        previous_burden_team_id="A",
        team_a_id="A",
        team_b_id="B",
    )
    assert state.team_id == "B"
    assert state.basis == BurdenBasis.PRIOR_BURDEN_INVERSION


def test_no_sting_burden_threshold_matches_foam():
    state, _ = establish_burden(
        NO_STING_OPEN,
        ball_controllers=_ctrls(4, 2),
        live_player_counts={"A": 6, "B": 6},
        previous_burden_team_id=None,
        team_a_id="A",
        team_b_id="B",
    )
    assert state.team_id == "A"


def test_valid_throw_resets_burden():
    state, _ = establish_burden(
        FOAM_OPEN,
        ball_controllers=_ctrls(4, 2),
        live_player_counts={"A": 6, "B": 6},
        previous_burden_team_id=None,
        team_a_id="A",
        team_b_id="B",
    )
    reset = reset_burden_after_valid_throw(state)
    assert reset.team_id is None
    assert reset.previous_burden_team_id == "A"


def test_foam_failure_forfeits_all_balls_to_opponent():
    state, _ = establish_burden(
        FOAM_OPEN,
        ball_controllers=_ctrls(4, 2),
        live_player_counts={"A": 6, "B": 6},
        previous_burden_team_id=None,
        team_a_id="A",
        team_b_id="B",
    )
    penalty = foam_failure_forfeit(
        burden=state, opponent_team_id="B", all_ball_ids=("b1", "b2", "b3")
    )
    assert penalty.team_id == "A"
    assert penalty.awarded_to_team_id == "B"
    assert penalty.forfeited_ball_ids == ("b1", "b2", "b3")
    assert penalty.out_player_ids == ()


def test_cloth_equal_balls_emits_discretion_event():
    state, disc = establish_burden(
        CLOTH_OPEN,
        ball_controllers=_ctrls(2, 2),
        live_player_counts={"A": 6, "B": 6},
        previous_burden_team_id="A",
        team_a_id="A",
        team_b_id="B",
    )
    assert state.basis == BurdenBasis.CLOTH_REACHABLE_BALL_RULING
    assert disc is not None
    assert disc.rule_section == "13"
    assert disc.selection_basis == "default_reachable_side"
    # Default inverts the previous holder
    assert state.team_id == "B"


def test_cloth_play_n_call_calculates_n_as_balls_minus_one_capped_by_players():
    call = cloth_play_n_call(
        team_id="A",
        controlled_ball_ids=("a1", "a2", "a3"),
        live_player_count=2,
        now_ms=0,
    )
    # n = 3 - 1 = 2, capped by 2 players -> 2
    assert call.n == 2
    assert call.deadline_ms == 5000

    call2 = cloth_play_n_call(
        team_id="A",
        controlled_ball_ids=("a1", "a2", "a3"),
        live_player_count=1,
        now_ms=0,
    )
    assert call2.n == 1  # capped by live players


def test_cloth_play_n_failure_outs_controllers_first_then_captain_selected():
    call = cloth_play_n_call(
        team_id="A",
        controlled_ball_ids=("a1", "a2", "a3"),
        live_player_count=6,
        now_ms=0,
    )
    penalty = cloth_play_n_failure(
        call=call,
        controllers_in_order=("p1", "p2", "p3"),
        captain_selected=("p4",),
        attempts_made=0,
        opponent_team_id="B",
    )
    # n=2, attempts=0, eliminated=0 -> shortfall 2 -> first two controllers
    assert penalty.out_player_ids == ("p1", "p2")


def test_eliminated_before_attempt_counts_toward_thrown():
    call = cloth_play_n_call(
        team_id="A",
        controlled_ball_ids=("a1", "a2", "a3"),
        live_player_count=6,
        now_ms=0,
    )
    penalty = cloth_play_n_failure(
        call=call,
        controllers_in_order=("p1", "p2", "p3"),
        captain_selected=("p4",),
        attempts_made=0,
        opponent_team_id="B",
        eliminated_before_attempt=("p1", "p2"),
    )
    # n=2, attempts=0, eliminated=2 -> shortfall 0 -> no extra outs
    assert penalty.out_player_ids == ()


def test_burden_event_emits_rule_13():
    state, _ = establish_burden(
        FOAM_OPEN,
        ball_controllers=_ctrls(4, 2),
        live_player_counts={"A": 6, "B": 6},
        previous_burden_team_id=None,
        team_a_id="A",
        team_b_id="B",
    )
    ev = burden_event(state, match_id="m1")
    assert ev.rule_labels() == ("13",)
    assert ev.payload["team_id"] == "A"
