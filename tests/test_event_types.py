from __future__ import annotations


def test_match_start_context_shape():
    from dodgeball_sim.event_types import MatchStartContext
    ctx: MatchStartContext = {
        "config_version": "phase1.v1",
        "difficulty": "pro",
        "meta_patch": None,
        "team_policies": {"team_a": {}, "team_b": {}},
    }
    assert ctx["difficulty"] == "pro"


def test_match_end_context_shape():
    from dodgeball_sim.event_types import MatchEndContext
    ctx: MatchEndContext = {"reason": "all_out"}
    assert ctx["reason"] == "all_out"


def test_throw_context_has_required_keys():
    from dodgeball_sim.event_types import ThrowContext
    ctx: ThrowContext = {
        "tick": 1,
        "thrower_selection": {},
        "target_selection": {},
        "difficulty": "pro",
        "policy_snapshot": {},
        "chemistry_delta": 0.0,
        "meta_patch": None,
        "rush_context": {},
        "sync_context": {"is_synced": False, "sync_modifier": 0.0},
        "calc": {},
        "fatigue": {},
        "catch_decision": None,
        "pressure_context": {},
    }
    assert ctx["tick"] == 1


def test_engine_emits_typed_events():
    """End-to-end: engine events have context shapes matching their TypedDict."""
    from dodgeball_sim.engine import MatchEngine
    from dodgeball_sim.models import MatchSetup, Team, Player, PlayerRatings

    def _player(pid: str) -> Player:
        return Player(
            id=pid, name=pid,
            ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60),
        )

    team_a = Team(id="a", name="A", players=tuple(_player(f"a{i}") for i in range(6)))
    team_b = Team(id="b", name="B", players=tuple(_player(f"b{i}") for i in range(6)))
    setup = MatchSetup(team_a=team_a, team_b=team_b)
    result = MatchEngine().run(setup, seed=1)

    start = next(e for e in result.events if e.event_type == "match_start")
    assert "config_version" in start.context
    assert "team_policies" in start.context

    end = next(e for e in result.events if e.event_type == "match_end")
    assert "reason" in end.context

    throw = next(e for e in result.events if e.event_type == "throw")
    for key in ("tick", "thrower_selection", "calc", "fatigue", "rush_context"):
        assert key in throw.context, f"Missing key: {key}"
