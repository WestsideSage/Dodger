from dodgeball_sim.events import MatchEvent
from dodgeball_sim.models import CoachPolicy, Player, PlayerRatings, PlayerTraits, Team
from dodgeball_sim.win_probability import per_event_wp_delta, pre_match_expected_outcome


def _player(player_id: str, overall: float) -> Player:
    return Player(
        id=player_id,
        name=player_id.title(),
        ratings=PlayerRatings(
            accuracy=overall,
            power=overall,
            dodge=overall,
            catch=overall,
            stamina=overall,
        ),
        traits=PlayerTraits(),
    )


def _team(team_id: str, overall: float, n: int = 6) -> Team:
    return Team(
        id=team_id,
        name=team_id.title(),
        players=tuple(_player(f"{team_id}_{i}", overall) for i in range(n)),
        coach_policy=CoachPolicy(),
        chemistry=0.5,
    )


def _throw_event(
    event_id: int,
    thrower: str,
    target: str,
    resolution: str,
    *,
    out_player: str | None = None,
    out_team: str | None = None,
) -> MatchEvent:
    state_diff = {}
    if out_player and out_team:
        state_diff["player_out"] = {"player_id": out_player, "team": out_team}
    return MatchEvent(
        event_id=event_id,
        tick=event_id,
        seed=0,
        event_type="throw",
        phase="volley",
        actors={"thrower": thrower, "target": target},
        context={},
        probabilities={},
        rolls={},
        outcome={"resolution": resolution},
        state_diff=state_diff,
    )


def test_pre_match_expected_outcome_equal_teams_is_half():
    assert abs(pre_match_expected_outcome(_team("a", 70), _team("b", 70)) - 0.5) < 1e-9


def test_pre_match_expected_outcome_in_unit_interval():
    p = pre_match_expected_outcome(_team("a", 50), _team("b", 90))
    assert 0.0 <= p <= 1.0


def test_pre_match_expected_outcome_monotonicity():
    b = _team("b", 65)
    assert pre_match_expected_outcome(_team("a", 80), b) > pre_match_expected_outcome(_team("a", 50), b)


def test_pre_match_expected_outcome_symmetry():
    a = _team("a", 60)
    b = _team("b", 80)
    assert abs((pre_match_expected_outcome(a, b) + pre_match_expected_outcome(b, a)) - 1.0) < 1e-9


def test_pre_match_expected_outcome_deterministic():
    a = _team("a", 70)
    b = _team("b", 75)
    assert pre_match_expected_outcome(a, b) == pre_match_expected_outcome(a, b)


def test_per_event_wp_delta_length_matches_events():
    events = [_throw_event(1, "a1", "b1", "miss"), _throw_event(2, "b1", "a1", "miss")]
    deltas = per_event_wp_delta(events, "A", "B", ["a1", "a2", "a3"], ["b1", "b2", "b3"])
    assert len(deltas) == len(events)


def test_hit_against_team_a_lowers_a_wp():
    events = [_throw_event(1, "b1", "a1", "hit", out_player="a1", out_team="A")]
    deltas = per_event_wp_delta(events, "A", "B", ["a1", "a2", "a3"], ["b1", "b2", "b3"])
    assert deltas[0] < 0.0


def test_hit_against_team_b_raises_a_wp():
    events = [_throw_event(1, "a1", "b1", "hit", out_player="b1", out_team="B")]
    deltas = per_event_wp_delta(events, "A", "B", ["a1", "a2", "a3"], ["b1", "b2", "b3"])
    assert deltas[0] > 0.0


def test_catch_by_a_raises_a_wp():
    events = [_throw_event(1, "b1", "a1", "catch", out_player="b1", out_team="B")]
    deltas = per_event_wp_delta(events, "A", "B", ["a1", "a2", "a3"], ["b1", "b2", "b3"])
    assert deltas[0] > 0.0


def test_per_event_wp_delta_deterministic():
    events = [
        _throw_event(1, "b1", "a1", "hit", out_player="a1", out_team="A"),
        _throw_event(2, "a2", "b1", "hit", out_player="b1", out_team="B"),
    ]
    args = dict(team_a_id="A", team_b_id="B", team_a_player_ids=["a1", "a2", "a3"], team_b_player_ids=["b1", "b2", "b3"])
    assert per_event_wp_delta(events, **args) == per_event_wp_delta(events, **args)


def test_per_event_wp_delta_symmetry():
    events = [_throw_event(1, "b1", "a1", "hit", out_player="a1", out_team="A")]
    a_view = per_event_wp_delta(events, "A", "B", ["a1", "a2", "a3"], ["b1", "b2", "b3"])
    b_view = per_event_wp_delta(events, "B", "A", ["b1", "b2", "b3"], ["a1", "a2", "a3"])
    assert abs(a_view[0] + b_view[0]) < 1e-9
