from __future__ import annotations


def test_throw_context_required_keys_match_engine_output():
    """Verify engine throw events contain all required ThrowContext keys."""
    from dodgeball_sim.event_types import ThrowContext
    from dodgeball_sim.engine import MatchEngine
    from dodgeball_sim.models import MatchSetup, Team, Player, PlayerRatings

    def _player(pid):
        return Player(id=pid, name=pid, ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60))

    team_a = Team(id="a", name="A", players=tuple(_player(f"a{i}") for i in range(6)))
    team_b = Team(id="b", name="B", players=tuple(_player(f"b{i}") for i in range(6)))
    result = MatchEngine().run(MatchSetup(team_a=team_a, team_b=team_b), seed=1)

    required = ThrowContext.__required_keys__
    optional = ThrowContext.__optional_keys__
    allowed = required | optional

    throws = [e for e in result.events if e.event_type == "throw"]
    assert throws, "Expected at least one throw event"
    for throw in throws:
        missing = required - throw.context.keys()
        assert not missing, f"Required ThrowContext keys missing from engine output: {missing}"
        unknown = throw.context.keys() - allowed
        assert not unknown, f"Engine emits keys not declared in ThrowContext: {unknown}"


def test_match_start_context_required_keys_match_engine_output():
    """Verify engine match_start event contains all required MatchStartContext keys."""
    from dodgeball_sim.event_types import MatchStartContext
    from dodgeball_sim.engine import MatchEngine
    from dodgeball_sim.models import MatchSetup, Team, Player, PlayerRatings

    def _player(pid):
        return Player(id=pid, name=pid, ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60))

    team_a = Team(id="a", name="A", players=tuple(_player(f"a{i}") for i in range(6)))
    team_b = Team(id="b", name="B", players=tuple(_player(f"b{i}") for i in range(6)))
    result = MatchEngine().run(MatchSetup(team_a=team_a, team_b=team_b), seed=1)

    required = MatchStartContext.__required_keys__
    optional = MatchStartContext.__optional_keys__
    allowed = required | optional

    starts = [e for e in result.events if e.event_type == "match_start"]
    assert starts
    for event in starts:
        missing = required - event.context.keys()
        assert not missing, f"Required MatchStartContext keys missing: {missing}"
        unknown = event.context.keys() - allowed
        assert not unknown, f"Engine emits undeclared MatchStartContext keys: {unknown}"


def test_match_end_context_required_keys_match_engine_output():
    """Verify engine match_end event contains all required MatchEndContext keys."""
    from dodgeball_sim.event_types import MatchEndContext
    from dodgeball_sim.engine import MatchEngine
    from dodgeball_sim.models import MatchSetup, Team, Player, PlayerRatings

    def _player(pid):
        return Player(id=pid, name=pid, ratings=PlayerRatings(accuracy=60, power=60, dodge=60, catch=60))

    team_a = Team(id="a", name="A", players=tuple(_player(f"a{i}") for i in range(6)))
    team_b = Team(id="b", name="B", players=tuple(_player(f"b{i}") for i in range(6)))
    result = MatchEngine().run(MatchSetup(team_a=team_a, team_b=team_b), seed=1)

    required = MatchEndContext.__required_keys__
    optional = MatchEndContext.__optional_keys__
    allowed = required | optional

    ends = [e for e in result.events if e.event_type == "match_end"]
    assert ends
    for event in ends:
        missing = required - event.context.keys()
        assert not missing, f"Required MatchEndContext keys missing: {missing}"
        unknown = event.context.keys() - allowed
        assert not unknown, f"Engine emits undeclared MatchEndContext keys: {unknown}"


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
