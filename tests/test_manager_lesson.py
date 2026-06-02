"""Unit tests for the WT-32 Manager Lesson hybrid selection.

Pure primitives in, ``ManagerLesson`` (or ``None``) out — no match or database
required. The faithfulness fences under test:

* a lesson surfaces on an inconclusive loss OR an inconclusive (even, close)
  draw — a win never gets one;
* an ignored recommendation ALWAYS wins;
* otherwise the strongest controllable signal by severity (deterministic);
* when NO controllable signal applies, the honest "nothing you controlled"
  message — never a fabricated lever;
* a conclusive result yields no lesson at all (Primary Factor unchanged);
* the result-flavored copy never misdescribes a draw as a loss (ADR 0002).
"""

from dodgeball_sim.manager_lesson import (
    FATIGUE,
    IGNORED_RECOMMENDATION,
    NO_LEVER,
    ROSTER_EDGE,
    WEAKEST_ROLE_GROUP,
    derive_manager_lesson,
    is_inconclusive_factor,
)
from dodgeball_sim.match_explanation import (
    CATCH_DISPARITY,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    UPSET_VARIANCE,
)


# ---------------------------------------------------------------------------
# is_inconclusive_factor predicate
# ---------------------------------------------------------------------------


def test_inconclusive_predicate_only_low_confidence_variance():
    # The genuine coin-flip fallback.
    assert is_inconclusive_factor(code=UPSET_VARIANCE, confidence=CONFIDENCE_LOW)
    # A decisive 0-4 blowout ALSO carries UPSET_VARIANCE but at medium
    # confidence — that is a CONCLUSIVE result and must NOT count as inconclusive.
    assert not is_inconclusive_factor(code=UPSET_VARIANCE, confidence=CONFIDENCE_MEDIUM)
    # A real event-derived factor is never inconclusive.
    assert not is_inconclusive_factor(code=CATCH_DISPARITY, confidence=CONFIDENCE_LOW)


# ---------------------------------------------------------------------------
# Gate: only inconclusive losses get a lesson
# ---------------------------------------------------------------------------


def test_conclusive_loss_gets_no_lesson():
    # factor_is_inconclusive=False -> the Primary Factor answered it; no lesson.
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=False,
        roster_edge={"net_ovr": -40},
        fatigue={"name": "Jordan", "stamina": 10},
    )
    assert lesson is None


def test_win_gets_no_lesson_even_if_inconclusive():
    lesson = derive_manager_lesson(
        result="Win",
        factor_is_inconclusive=True,
        fatigue={"name": "Jordan", "stamina": 10},
    )
    assert lesson is None


def test_conclusive_draw_gets_no_lesson():
    # A draw the Primary Factor pinned on a real factor (factor_is_inconclusive
    # =False) is answered by that factor; no Manager Lesson.
    lesson = derive_manager_lesson(
        result="Draw",
        factor_is_inconclusive=False,
        roster_edge={"net_ovr": -30},
        fatigue={"name": "Jordan", "stamina": 10},
    )
    assert lesson is None


# ---------------------------------------------------------------------------
# Owner-approved scope: an inconclusive DRAW also yields a lesson (a draw at an
# even matchup is exactly "what could I have changed to edge it?").
# ---------------------------------------------------------------------------


def test_inconclusive_draw_with_lever_surfaces_controllable_lesson():
    lesson = derive_manager_lesson(
        result="Draw",
        factor_is_inconclusive=True,
        roster_edge={"net_ovr": -24},
    )
    assert lesson is not None
    assert lesson.code == ROSTER_EDGE
    assert lesson.controllable is True


def test_inconclusive_draw_no_lever_is_honest_no_lever_not_loss_copy():
    # No controllable signal on an even, rested draw -> the honest no-lever
    # message. Faithfulness: the copy must NOT claim the draw was lost.
    lesson = derive_manager_lesson(
        result="Draw",
        factor_is_inconclusive=True,
        ignored_recommendation=None,
        roster_edge=None,
        fatigue=None,
        weakest_role_group=None,
    )
    assert lesson is not None
    assert lesson.code == NO_LEVER
    assert lesson.controllable is False
    # The loss-only phrasing ("went the other way") must be absent on a draw;
    # the draw says it "stayed level".
    assert "went the other way" not in lesson.sentence
    assert "stayed level" in lesson.sentence


def test_inconclusive_draw_weakest_group_copy_does_not_say_lost():
    # The weakest-group lever's result-flavored clause must not say "lost this
    # match" on a draw.
    lesson = derive_manager_lesson(
        result="Draw",
        factor_is_inconclusive=True,
        weakest_role_group={"archetype": "wall", "avg_overall": 48, "count": 3},
    )
    assert lesson is not None
    assert lesson.code == WEAKEST_ROLE_GROUP
    assert "lost this match" not in lesson.sentence
    assert "kept this match even" in lesson.sentence


def test_inconclusive_draw_ignored_recommendation_still_wins():
    lesson = derive_manager_lesson(
        result="Draw",
        factor_is_inconclusive=True,
        ignored_recommendation={
            "advised_intent": "Preserve Health",
            "selected_intent": "Win Now",
            "reason": "2 starters are low on stamina; Preserve Health protects them.",
        },
        roster_edge={"net_ovr": -50},
    )
    assert lesson is not None
    assert lesson.code == IGNORED_RECOMMENDATION


def test_loss_no_lever_copy_unchanged():
    # Regression: the loss no-lever copy keeps its original wording.
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
    )
    assert lesson is not None
    assert lesson.code == NO_LEVER
    assert "went the other way" in lesson.sentence


# ---------------------------------------------------------------------------
# Case 1: ignored recommendation ALWAYS wins
# ---------------------------------------------------------------------------


def test_ignored_recommendation_always_wins_over_other_signals():
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        ignored_recommendation={
            "advised_intent": "Preserve Health",
            "selected_intent": "Win Now",
            "reason": "2 starters are low on stamina; Preserve Health protects them.",
        },
        # Strong competing signals present — the ignored rec must still win.
        roster_edge={"net_ovr": -50},
        fatigue={"name": "Jordan", "stamina": 5},
        weakest_role_group={"archetype": "wall", "avg_overall": 40, "count": 3},
    )
    assert lesson is not None
    assert lesson.code == IGNORED_RECOMMENDATION
    assert lesson.controllable is True
    assert "Preserve Health" in lesson.sentence
    assert any("Preserve Health" in chip for chip in lesson.evidence_chips)


def test_ignored_recommendation_without_advised_intent_falls_through():
    # An "aligned" recommendation (no advised_intent) is NOT an ignored rec;
    # selection falls through to the strongest controllable signal.
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        ignored_recommendation={"advised_intent": None, "reason": "Your plan fits."},
        fatigue={"name": "Jordan", "stamina": 12},
    )
    assert lesson is not None
    assert lesson.code == FATIGUE


# ---------------------------------------------------------------------------
# Case 2: strongest-by-magnitude among controllable signals
# ---------------------------------------------------------------------------


def test_only_roster_edge_signal_surfaces_it():
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        roster_edge={"net_ovr": -24},
    )
    assert lesson is not None
    assert lesson.code == ROSTER_EDGE
    assert lesson.controllable is True
    assert any("Net starter OVR -24" in chip for chip in lesson.evidence_chips)


def test_only_fatigue_signal_surfaces_it():
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        fatigue={"name": "Jordan", "stamina": 18},
    )
    assert lesson is not None
    assert lesson.code == FATIGUE
    assert "Jordan" in lesson.sentence


def test_strongest_by_severity_wins_roster_over_weak_fatigue():
    # Roster deficit of 40 -> severity 40/8 = 5.0.
    # Stamina 90 -> severity (100-90)/20 = 0.5. Roster edge must win.
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        roster_edge={"net_ovr": -40},
        fatigue={"name": "Jordan", "stamina": 90},
        weakest_role_group={"archetype": "wall", "avg_overall": 58, "count": 2},
    )
    assert lesson is not None
    assert lesson.code == ROSTER_EDGE


def test_strongest_by_severity_wins_fatigue_over_small_roster_gap():
    # Stamina 5 -> severity (100-5)/20 = 4.75.
    # Roster deficit of 8 -> severity 8/8 = 1.0. Fatigue must win.
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        roster_edge={"net_ovr": -8},
        fatigue={"name": "Jordan", "stamina": 5},
    )
    assert lesson is not None
    assert lesson.code == FATIGUE


def test_non_negative_roster_edge_is_not_a_lever():
    # A roster edge in the player's favour is not a controllable shortfall; with
    # no other signal it must fall to the honest no-lever message.
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        roster_edge={"net_ovr": 12},
    )
    assert lesson is not None
    assert lesson.code == NO_LEVER


def test_weakest_group_surfaces_when_only_signal():
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        weakest_role_group={"archetype": "wall", "avg_overall": 48, "count": 3},
    )
    assert lesson is not None
    assert lesson.code == WEAKEST_ROLE_GROUP
    assert lesson.controllable is True


# ---------------------------------------------------------------------------
# Case 3: no controllable signal -> honest no-lever message (no fabrication)
# ---------------------------------------------------------------------------


def test_no_controllable_signal_is_honest_no_lever():
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        ignored_recommendation=None,
        roster_edge=None,
        fatigue=None,
        weakest_role_group=None,
    )
    assert lesson is not None
    assert lesson.code == NO_LEVER
    assert lesson.controllable is False
    assert "nothing you controlled" in lesson.sentence.lower()
    # The honest message must not fabricate evidence chips.
    assert lesson.evidence_chips == ()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_deterministic_repeated_calls():
    kwargs = dict(
        result="Loss",
        factor_is_inconclusive=True,
        roster_edge={"net_ovr": -16},
        fatigue={"name": "Jordan", "stamina": 40},
        weakest_role_group={"archetype": "wall", "avg_overall": 52, "count": 2},
    )
    a = derive_manager_lesson(**kwargs)
    b = derive_manager_lesson(**kwargs)
    assert a is not None and b is not None
    assert a.as_dict() == b.as_dict()


# ---------------------------------------------------------------------------
# Wiring extractors (use_cases): the "applies" thresholds that keep the honest
# no-lever branch reachable in real play and align levers with what the
# pre-match week briefing showed the player.
# ---------------------------------------------------------------------------

from dodgeball_sim.use_cases import (  # noqa: E402
    _aftermath_fatigue_signal,
    _aftermath_roster_edge,
)


def test_roster_edge_applies_only_beyond_underdog_band():
    # Net -15 (below -_EVEN_BAND of -8) -> the player was the clear underdog.
    under = {
        "lineup": {"players": [{"overall": 50}, {"overall": 50}]},
        "opponent_lineup": {"players": [{"overall": 58}, {"overall": 57}]},
    }
    assert _aftermath_roster_edge(under) == {"net_ovr": -15}
    # Net -4 sits inside the even band -> not a controllable shortfall.
    even = {
        "lineup": {"players": [{"overall": 50}, {"overall": 50}]},
        "opponent_lineup": {"players": [{"overall": 52}, {"overall": 52}]},
    }
    assert _aftermath_roster_edge(even) is None
    # Player favoured -> never a lever.
    favoured = {
        "lineup": {"players": [{"overall": 60}, {"overall": 60}]},
        "opponent_lineup": {"players": [{"overall": 50}, {"overall": 50}]},
    }
    assert _aftermath_roster_edge(favoured) is None


def test_roster_edge_requires_both_sixes():
    # Without an opponent lineup the net edge is not derivable -> None, never 0.
    assert _aftermath_roster_edge({"lineup": {"players": [{"overall": 50}]}}) is None
    assert _aftermath_roster_edge(None) is None


def test_fatigue_signal_applies_only_when_at_risk():
    tired = {"lineup": {"players": [{"name": "Jordan", "stamina": 45}, {"name": "Casey", "stamina": 80}]}}
    assert _aftermath_fatigue_signal(tired) == {"name": "Jordan", "stamina": 45}
    # All starters at/above the at-risk bar (60) -> no fatigue lever.
    fresh = {"lineup": {"players": [{"name": "Jordan", "stamina": 70}, {"name": "Casey", "stamina": 80}]}}
    assert _aftermath_fatigue_signal(fresh) is None
    assert _aftermath_fatigue_signal(None) is None


import sqlite3  # noqa: E402

from dodgeball_sim.persistence import (  # noqa: E402
    create_schema,
    save_command_history_record,
)
from dodgeball_sim.use_cases import _aftermath_ignored_recommendation  # noqa: E402

_CLUB = "club_player"
_SEASON = "season_1"


def _hist_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _save_match(conn, *, week: int, match_id: str, result: str, intent: str = "Balanced"):
    save_command_history_record(
        conn,
        {
            "season_id": _SEASON,
            "week": week,
            "match_id": match_id,
            "opponent_club_id": "club_opp",
            "intent": intent,
            "plan": {"player_club_id": _CLUB, "intent": intent},
            "dashboard": {"result": result},
        },
    )
    conn.commit()


def _plan(*, intent: str, stamina: list[int]):
    return {
        "player_club_id": _CLUB,
        "intent": intent,
        "lineup": {"players": [{"name": f"P{i}", "stamina": s} for i, s in enumerate(stamina)]},
    }


def test_ignored_rec_two_prior_losses_advises_win_now():
    conn = _hist_conn()
    _save_match(conn, week=1, match_id="m1", result="Loss")
    _save_match(conn, week=2, match_id="m2", result="Loss")
    # The just-played (current) match is already persisted before aftermath.
    _save_match(conn, week=3, match_id="m3", result="Loss", intent="Balanced")
    rec = _aftermath_ignored_recommendation(
        conn,
        season_id=_SEASON,
        current_match_id="m3",
        plan=_plan(intent="Balanced", stamina=[80, 80, 80]),
    )
    assert rec is not None
    assert rec["advised_intent"] == "Win Now"
    assert rec["selected_intent"] == "Balanced"


def test_ignored_rec_excludes_current_match_from_slice():
    # Only ONE prior loss (m1); the current loss m2 must be EXCLUDED, so the
    # "two straight losses" trigger does NOT fire -> no ignored rec. This is the
    # faithfulness guard against contaminating pre-match advice with hindsight.
    conn = _hist_conn()
    _save_match(conn, week=1, match_id="m1", result="Win")
    _save_match(conn, week=2, match_id="m2", result="Loss", intent="Balanced")
    rec = _aftermath_ignored_recommendation(
        conn,
        season_id=_SEASON,
        current_match_id="m2",
        plan=_plan(intent="Balanced", stamina=[80, 80, 80]),
    )
    assert rec is None


def test_ignored_rec_at_risk_starters_advise_preserve_health():
    # >=2 starters below the at-risk bar (60) -> staff advises Preserve Health;
    # player ran Win Now -> declined advisory surfaces as the ignored rec.
    conn = _hist_conn()
    _save_match(conn, week=1, match_id="m1", result="Win")
    rec = _aftermath_ignored_recommendation(
        conn,
        season_id=_SEASON,
        current_match_id="m1",  # not in slice anyway
        plan=_plan(intent="Win Now", stamina=[40, 45, 80]),
    )
    assert rec is not None
    assert rec["advised_intent"] == "Preserve Health"
    assert rec["selected_intent"] == "Win Now"


def test_ignored_rec_none_when_player_followed_advice():
    # Two prior losses advise Win Now; player ALREADY ran Win Now -> not ignored.
    conn = _hist_conn()
    _save_match(conn, week=1, match_id="m1", result="Loss")
    _save_match(conn, week=2, match_id="m2", result="Loss")
    rec = _aftermath_ignored_recommendation(
        conn,
        season_id=_SEASON,
        current_match_id="m3",
        plan=_plan(intent="Win Now", stamina=[80, 80, 80]),
    )
    assert rec is None


def test_ignored_rec_none_on_aligned_form_and_health():
    conn = _hist_conn()
    _save_match(conn, week=1, match_id="m1", result="Win")
    rec = _aftermath_ignored_recommendation(
        conn,
        season_id=_SEASON,
        current_match_id="m2",
        plan=_plan(intent="Balanced", stamina=[80, 80, 80]),
    )
    assert rec is None


def test_ignored_rec_handles_missing_inputs():
    conn = _hist_conn()
    assert _aftermath_ignored_recommendation(conn, season_id=None, current_match_id="m1", plan={}) is None
    assert _aftermath_ignored_recommendation(conn, season_id=_SEASON, current_match_id="m1", plan=None) is None


def test_even_rested_plan_yields_honest_no_lever_end_to_end():
    # A fair, rested six with a flat roster -> every extractor returns None ->
    # the honest no-lever message is the result (the production-reachability of
    # the "nothing you controlled" branch this whole design hinges on).
    plan = {
        "lineup": {"players": [{"name": "A", "overall": 60, "stamina": 80}, {"name": "B", "overall": 60, "stamina": 75}]},
        "opponent_lineup": {"players": [{"overall": 61, "stamina": 0}, {"overall": 60, "stamina": 0}]},
    }
    lesson = derive_manager_lesson(
        result="Loss",
        factor_is_inconclusive=True,
        ignored_recommendation=None,
        roster_edge=_aftermath_roster_edge(plan),
        fatigue=_aftermath_fatigue_signal(plan),
        weakest_role_group=None,  # flat roster -> caller passes None
    )
    assert lesson is not None
    assert lesson.code == NO_LEVER
