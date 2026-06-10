"""Unit tests for the V14 deterministic Primary Factor ranking.

These exercise the pure ranking/tie-break/fallback logic with synthetic
primitives — no match or database required.
"""

from dataclasses import dataclass

from dodgeball_sim.match_explanation import (
    CATCH_DISPARITY,
    FLOOD_THROWS_PUNISHED,
    LATE_STAMINA_COLLAPSE,
    OPENING_RUSH_DEFICIT,
    UPSET_VARIANCE,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    derive_match_explanation,
)


@dataclass(frozen=True)
class _Gassed:
    tick: int
    player_id: str
    team_id: str
    fatigue_pct: float
    kind: str = "gassed_collapse"


@dataclass(frozen=True)
class _Flood:
    tick: int
    thrower_team_id: str
    thrower_ids: tuple
    kind: str = "flood_throw"


PLAYER = "player"
OPP = "opp"


def _base(**overrides):
    kwargs = dict(
        result="Loss",
        player_survivors=2,
        opponent_survivors=4,
        player_catches=0,
        opponent_catches=0,
        moment_events=(),
        player_club_id=PLAYER,
        opponent_club_id=OPP,
        largest_deficit=0,
        deficit_low_tick=0,
        final_tick=100,
        name_map={"p1": "Jordan", "o1": "Casey"},
    )
    kwargs.update(overrides)
    return derive_match_explanation(**kwargs)


def test_catch_disparity_wins_when_dominant():
    exp = _base(
        result="Win",
        player_survivors=5,
        opponent_survivors=2,
        player_catches=5,
        opponent_catches=1,
    )
    assert exp.primary_factor.code == CATCH_DISPARITY
    assert exp.primary_factor.confidence == CONFIDENCE_HIGH
    assert any("Catches 5-1" in chip for chip in exp.primary_factor.evidence_chips)


def test_catch_disparity_not_claimed_against_result():
    # Player out-caught the opponent but still LOST: catches did not cause the
    # loss, so catch_disparity must not be the primary factor.
    exp = _base(
        result="Loss",
        player_catches=4,
        opponent_catches=1,
        # nothing else supported -> fallback
    )
    assert exp.primary_factor.code != CATCH_DISPARITY


def test_massive_catch_diff_outranks_minor_stamina():
    # Catch diff of 4 (weight 4) must outrank a single late stamina collapse
    # (weight ~2). Spec tie-break: severity of disparity.
    gassed = _Gassed(tick=90, player_id="p1", team_id=PLAYER, fatigue_pct=0.95)
    exp = _base(
        result="Loss",
        player_catches=0,
        opponent_catches=4,
        moment_events=(gassed,),
    )
    assert exp.primary_factor.code == CATCH_DISPARITY


def test_late_event_wins_finality_tie():
    # Two factors at equal weight: the later (more final) one wins.
    # Catch diff of 2 (weight 2.0, finality 0) vs one late gassed collapse
    # (weight 2.0, finality = late tick). Stamina should win on finality.
    gassed = _Gassed(tick=95, player_id="p1", team_id=PLAYER, fatigue_pct=0.9)
    exp = _base(
        result="Loss",
        player_catches=0,
        opponent_catches=2,
        moment_events=(gassed,),
    )
    assert exp.primary_factor.code == LATE_STAMINA_COLLAPSE
    assert exp.primary_factor.confidence == CONFIDENCE_HIGH


def test_opening_rush_deficit_requires_early_low_point():
    # Deep deficit but the low point came late -> not an opening-rush factor.
    late = _base(result="Loss", largest_deficit=3, deficit_low_tick=90, final_tick=100)
    assert late.primary_factor.code != OPENING_RUSH_DEFICIT
    # Same deficit but early -> opening rush factor surfaces.
    early = _base(result="Loss", largest_deficit=3, deficit_low_tick=20, final_tick=100)
    assert early.primary_factor.code == OPENING_RUSH_DEFICIT
    assert early.primary_factor.confidence == CONFIDENCE_HIGH


def test_flood_throws_punished_only_when_returns_exist():
    flood = _Flood(tick=50, thrower_team_id=PLAYER, thrower_ids=("p1", "p2", "p3"))
    # No catches by opponent -> flood was not punished -> not the factor.
    not_punished = _base(result="Loss", moment_events=(flood,), opponent_catches=0)
    assert not_punished.primary_factor.code != FLOOD_THROWS_PUNISHED
    # Opponent caught 3 returns -> punished. Give the player matching catches
    # so catch disparity stays minor and the flood is the dominant signal.
    punished = _base(
        result="Loss", moment_events=(flood,), player_catches=2, opponent_catches=3
    )
    assert punished.primary_factor.code == FLOOD_THROWS_PUNISHED


def test_liability_involvement_never_ranks_as_a_factor():
    """2026-06-09 audit: slot-role fit has no consumer in any shipping engine,
    so a role mismatch can never be ranked as a cause of the result. The old
    "liability_involvement" factor was removed; a loss with nothing else
    supported must fall back to the honest variance message instead of
    directing the player at a lever that does not exist."""
    exp = _base(result="Loss")
    assert exp.primary_factor.code == UPSET_VARIANCE
    assert "liability" not in exp.primary_factor.sentence.lower()
    assert all(
        "liability" not in factor.sentence.lower() for factor in exp.considered
    )


def test_close_match_falls_back_to_variance_with_soft_language():
    # 1-catch edge in a one-survivor game -> no dominant factor.
    exp = _base(
        result="Loss",
        player_survivors=3,
        opponent_survivors=4,
        player_catches=0,
        opponent_catches=1,
    )
    assert exp.primary_factor.code == UPSET_VARIANCE
    assert exp.primary_factor.confidence == CONFIDENCE_LOW
    assert "no one thing" in exp.primary_factor.sentence.lower() or "no single factor" in exp.primary_factor.sentence.lower()


def test_no_evidence_falls_back_to_variance():
    exp = _base(result="Draw", player_survivors=3, opponent_survivors=3)
    assert exp.primary_factor.code == UPSET_VARIANCE


def test_decisive_set_loss_with_no_factor_is_not_inconclusive():
    # 4.4: a 0-4 set loss with a small survivor margin and no standout tactical
    # factor must NOT read as "stayed close / no one thing to fix"; the set
    # margin makes it decisive, so the copy says the result wasn't close.
    exp = _base(
        result="Loss",
        player_survivors=3,
        opponent_survivors=4,
        player_catches=0,
        opponent_catches=0,
        point_margin=4,
    )
    assert exp.primary_factor.code == UPSET_VARIANCE
    sentence = exp.primary_factor.sentence.lower()
    assert "stayed close" not in sentence
    assert "wasn't close" in sentence or "outclassed" in exp.primary_factor.title.lower()


def test_decisive_set_loss_with_a_weak_factor_surfaces_it():
    # A decisive result must not bury a real (if weak) cause under "variance":
    # a catch edge in a 0-4 loss is surfaced rather than shrugged off.
    exp = _base(
        result="Loss",
        player_survivors=3,
        opponent_survivors=4,
        player_catches=0,
        opponent_catches=1,
        point_margin=4,
    )
    assert exp.primary_factor.code != UPSET_VARIANCE


def test_decisive_set_win_is_not_a_coin_flip():
    exp = _base(
        result="Win",
        player_survivors=4,
        opponent_survivors=3,
        player_catches=0,
        opponent_catches=0,
        point_margin=6,
    )
    assert exp.primary_factor.code == UPSET_VARIANCE
    sentence = exp.primary_factor.sentence.lower()
    assert "came down to the margins" not in sentence
    assert "held the edge" in sentence or "controlled" in exp.primary_factor.title.lower()


def test_generic_match_without_point_margin_unchanged():
    # No official metadata -> point_margin 0 -> the close-match soft fallback
    # is preserved for the survivor-scored generic engine.
    exp = _base(
        result="Loss",
        player_survivors=3,
        opponent_survivors=4,
        player_catches=0,
        opponent_catches=1,
    )
    assert exp.primary_factor.code == UPSET_VARIANCE
    assert "stayed close" in exp.primary_factor.sentence.lower()


def test_deterministic_repeated_calls():
    gassed = _Gassed(tick=90, player_id="p1", team_id=PLAYER, fatigue_pct=0.95)
    a = _base(result="Loss", opponent_catches=4, moment_events=(gassed,))
    b = _base(result="Loss", opponent_catches=4, moment_events=(gassed,))
    assert a.as_dict() == b.as_dict()
