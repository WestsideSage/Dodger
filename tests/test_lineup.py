from dodgeball_sim.lineup import STARTERS_COUNT, LineupResolver
from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits


def _p(player_id: str, overall: float = 60.0) -> Player:
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


def test_resolve_default_falls_back_to_roster_order_when_no_default():
    roster = [_p("a"), _p("b"), _p("c")]
    assert LineupResolver().resolve(roster=roster, default=None, override=None) == ["a", "b", "c"]


def test_resolve_uses_default_when_no_override():
    roster = [_p("a"), _p("b"), _p("c")]
    assert LineupResolver().resolve(roster=roster, default=["b", "a", "c"], override=None) == ["b", "a", "c"]


def test_resolve_override_beats_default():
    roster = [_p("a"), _p("b"), _p("c")]
    assert LineupResolver().resolve(
        roster=roster,
        default=["b", "a", "c"],
        override=["c", "a", "b"],
    ) == ["c", "a", "b"]


def test_resolve_drops_invalid_player_ids_silently():
    roster = [_p("a", 70), _p("b", 80), _p("c", 50), _p("d", 90)]
    result = LineupResolver().resolve(
        roster=roster,
        default=["ghost", "a", "c"],
        override=None,
    )
    assert result[:2] == ["a", "c"]
    assert result[2:] == ["d", "b"]


def test_resolve_returns_invalid_flag_when_default_was_partially_invalid():
    roster = [_p("a"), _p("b")]
    out = LineupResolver().resolve_with_diagnostics(
        roster=roster,
        default=["ghost", "a", "b"],
        override=None,
    )
    assert out.lineup == ["a", "b"]
    assert out.dropped_ids == ["ghost"]


def test_starters_count_is_six():
    assert STARTERS_COUNT == 6


def test_resolver_invalid_then_backfill_round_trip():
    roster = [_p("a", 70), _p("b", 80), _p("c", 50), _p("d", 90)]
    out = LineupResolver().resolve_with_diagnostics(
        roster=roster,
        default=["a", "ghost"],
        override=None,
    )
    assert out.lineup == ["a", "d", "b", "c"]
    assert out.dropped_ids == ["ghost"]
