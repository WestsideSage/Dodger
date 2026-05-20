from dodgeball_sim.moment_events import (
    DramaticCatch,
    LateGameEscape,
    OneVOneFinale,
    GassedCollapse,
    FloodThrow,
    Comeback,
    MomentEvent,
    MomentKind,
)


def test_moment_kinds_are_unique():
    kinds = {
        MomentKind.DRAMATIC_CATCH,
        MomentKind.LATE_GAME_ESCAPE,
        MomentKind.ONE_V_ONE_FINALE,
        MomentKind.GASSED_COLLAPSE,
        MomentKind.FLOOD_THROW,
        MomentKind.COMEBACK,
    }
    assert len(kinds) == 6


def test_dramatic_catch_fields():
    ev = DramaticCatch(
        match_id="m1",
        tick=12,
        catcher_id="p7",
        catcher_team_id="a",
        thrower_id="p2",
        thrower_team_id="b",
        returning_player_id="p9",
        active_count_a=3,
        active_count_b=4,
    )
    assert ev.kind == MomentKind.DRAMATIC_CATCH
    assert ev.catcher_id == "p7"
    assert ev.returning_player_id == "p9"


def test_late_game_escape_requires_three_or_more_attackers():
    ev = LateGameEscape(
        match_id="m1",
        tick=40,
        survivor_id="p1",
        survivor_team_id="a",
        attacker_team_id="b",
        attacker_count=4,
    )
    assert ev.kind == MomentKind.LATE_GAME_ESCAPE
    assert ev.attacker_count >= 3


def test_one_v_one_finale_fields():
    ev = OneVOneFinale(
        match_id="m1",
        tick=55,
        player_a_id="p1",
        player_b_id="p10",
        tick_started=53,
    )
    assert ev.kind == MomentKind.ONE_V_ONE_FINALE


def test_gassed_collapse_fields():
    ev = GassedCollapse(
        match_id="m1",
        tick=44,
        player_id="p5",
        team_id="a",
        fatigue_pct=0.86,
    )
    assert ev.kind == MomentKind.GASSED_COLLAPSE
    assert ev.fatigue_pct >= 0.75


def test_flood_throw_three_or_more_simultaneous():
    ev = FloodThrow(
        match_id="m1",
        tick=22,
        thrower_team_id="b",
        thrower_ids=("p2", "p3", "p5"),
    )
    assert ev.kind == MomentKind.FLOOD_THROW
    assert len(ev.thrower_ids) >= 3


def test_comeback_records_deficit():
    ev = Comeback(
        match_id="m1",
        tick=60,
        team_id="a",
        deficit_at_low_point=4,
        catches_during_comeback=5,
    )
    assert ev.kind == MomentKind.COMEBACK
    assert ev.deficit_at_low_point >= 3


def test_moment_event_union_accepts_all_six():
    events: list[MomentEvent] = [
        DramaticCatch("m", 0, "a", "ta", "b", "tb", "c", 1, 1),
        LateGameEscape("m", 0, "a", "ta", "tb", 3),
        OneVOneFinale("m", 0, "a", "b", 0),
        GassedCollapse("m", 0, "a", "ta", 0.8),
        FloodThrow("m", 0, "ta", ("a", "b", "c")),
        Comeback("m", 0, "ta", 3, 3),
    ]
    assert len(events) == 6
