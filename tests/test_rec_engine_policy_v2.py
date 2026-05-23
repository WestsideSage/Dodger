from __future__ import annotations

from dodgeball_sim.engine_driver import DriverMatchInput
from dodgeball_sim.models import CoachPolicy, Player, PlayerArchetype, PlayerRatings
from dodgeball_sim.player_state import OfficialPlayerState, OfficialPlayerStatus
from dodgeball_sim.rec_engine import (
    RecTier1Driver,
    _response_branch_for_policy,
    _should_throw_under_iq,
)


def _player(
    pid: str,
    club: str,
    *,
    accuracy: float = 50,
    power: float = 50,
    dodge: float = 50,
    catch: float = 50,
    catch_courage: float = 50,
    throw_selection_iq: float = 50,
) -> Player:
    return Player(
        id=pid,
        name=pid.upper(),
        club_id=club,
        archetype=PlayerArchetype.CATCHER,
        ratings=PlayerRatings(
            accuracy=accuracy,
            power=power,
            dodge=dodge,
            catch=catch,
            stamina=60,
            tactical_iq=50,
            catch_courage=catch_courage,
            throw_selection_iq=throw_selection_iq,
            conditioning_curve=50,
        ),
    )


def _match_input(
    *,
    policy_a: CoachPolicy | None = None,
    policy_b: CoachPolicy | None = None,
) -> DriverMatchInput:
    starters_a = tuple(f"a{i}" for i in range(6))
    starters_b = tuple(f"b{i}" for i in range(6))
    players = {pid: _player(pid, "A") for pid in starters_a}
    players.update({pid: _player(pid, "B") for pid in starters_b})
    return DriverMatchInput(
        match_id="policy-match",
        team_a_id="A",
        team_b_id="B",
        starters_a=starters_a,
        starters_b=starters_b,
        player_lookup=players,
        policy_a=policy_a or CoachPolicy(),
        policy_b=policy_b or CoachPolicy(),
        seed=7,
    )


def _state(pid: str, team_id: str) -> OfficialPlayerState:
    return OfficialPlayerState(
        player_id=pid,
        team_id=team_id,
        status=OfficialPlayerStatus.ACTIVE,
        is_starter=True,
    )


def test_approach_gate_biases_throw_timing():
    expected_value = 0.33

    assert _should_throw_under_iq(
        iq=80,
        expected_value=expected_value,
        stall_seconds=0.0,
        stall_cap=30.0,
        gate_multiplier=0.85,
    ) is True
    assert _should_throw_under_iq(
        iq=80,
        expected_value=expected_value,
        stall_seconds=0.0,
        stall_cap=30.0,
        gate_multiplier=1.20,
    ) is False


def test_target_focus_selects_star_ball_holder_and_spread_targets():
    driver = RecTier1Driver()
    mi = _match_input(policy_a=CoachPolicy(target_focus="their_stars"))
    mi.player_lookup["b_star"] = _player("b_star", "B", dodge=50, accuracy=95, power=95, catch=80)
    mi.player_lookup["b_holder"] = _player("b_holder", "B", dodge=50, accuracy=55, power=55, catch=55)
    mi.player_lookup["b_recent"] = _player("b_recent", "B", dodge=50, accuracy=55, power=55, catch=55)

    defense = [_state("b_star", "B"), _state("b_holder", "B"), _state("b_recent", "B")]
    star_pick = driver._select_target_state(  # type: ignore[attr-defined]
        defense_states=defense,
        player_lookup=mi.player_lookup,
        policy=CoachPolicy(target_focus="their_stars"),
        ball_holder_ids={"b_holder"},
        recent_targets=["b_recent", "b_holder"],
    )
    holder_pick = driver._select_target_state(  # type: ignore[attr-defined]
        defense_states=defense,
        player_lookup=mi.player_lookup,
        policy=CoachPolicy(target_focus="ball_holders"),
        ball_holder_ids={"b_holder"},
        recent_targets=["b_recent", "b_star"],
    )
    spread_pick = driver._select_target_state(  # type: ignore[attr-defined]
        defense_states=defense,
        player_lookup=mi.player_lookup,
        policy=CoachPolicy(target_focus="spread"),
        ball_holder_ids={"b_holder"},
        recent_targets=["b_recent", "b_holder", "b_star"],
    )

    assert star_pick.player_id == "b_star"
    assert holder_pick.player_id == "b_holder"
    assert spread_pick.player_id == "b_star"


def test_catch_posture_changes_response_branch():
    assert _response_branch_for_policy(
        courage=90,
        posture="go_for_catches",
        response_roll=0.66,
    ) == "catch"
    assert _response_branch_for_policy(
        courage=90,
        posture="opportunistic",
        response_roll=0.66,
    ) == "block"
    assert _response_branch_for_policy(
        courage=90,
        posture="play_safe",
        response_roll=0.66,
    ) == "dodge"


def test_opening_rush_assigns_sprinters_and_ball_targets():
    driver = RecTier1Driver()
    starters = tuple(f"a{i}" for i in range(6))

    all_in_center = driver._opening_rush(  # type: ignore[attr-defined]
        team_id="A",
        starters=starters,
        policy=CoachPolicy(rush_commit="all_in", rush_target="center"),
    )
    hold_back_nearest = driver._opening_rush(  # type: ignore[attr-defined]
        team_id="A",
        starters=starters,
        policy=CoachPolicy(rush_commit="hold_back", rush_target="nearest"),
    )

    assert all_in_center["sprinter_ids"] == list(starters)
    assert len(all_in_center["ball_targets"]) == 6
    assert set(all_in_center["ball_targets"].values()) <= {"ball_center_0", "ball_center_1", "ball_center_2"}

    assert hold_back_nearest["sprinter_ids"] == ["a0", "a1"]
    assert hold_back_nearest["hold_back_ids"] == ["a2", "a3", "a4", "a5"]
    assert hold_back_nearest["ball_targets"] == {
        "a0": "ball_a_0",
        "a1": "ball_a_1",
    }
