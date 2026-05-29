"""Every recruiting action must produce a visible, non-trivial delta.

Codex's recurring complaint was that Scout / Contact / Visit changed a label
but showed no payoff. These tests pin the honest effect model: scouting tightens
the OVR band, contact/visit build interest, and each action reports before/after.
"""

from __future__ import annotations

from dodgeball_sim.recruiting_actions import (
    RecruitingActionResult,
    apply_action,
    base_interest,
    narrow_band,
)


def test_scout_narrows_the_ovr_band():
    state, result = apply_action(
        {}, "scout", base_band=(68, 82), pipeline_tier=2, credibility_score=50
    )
    assert isinstance(result, RecruitingActionResult)
    assert state["scouted"] is True
    # The reported band must actually be tighter than the public band.
    after = result.ovr_band_after
    assert after[1] - after[0] < 82 - 68
    assert after != result.ovr_band_before


def test_contact_raises_interest():
    state, result = apply_action(
        {}, "contact", base_band=(70, 80), pipeline_tier=2, credibility_score=50
    )
    assert result.interest_after > result.interest_before
    assert state["interest"] == result.interest_after
    assert state["contacted"] is True


def test_visit_raises_interest_more_than_contact():
    _, contact = apply_action(
        {}, "contact", base_band=(70, 80), pipeline_tier=2, credibility_score=50
    )
    _, visit = apply_action(
        {}, "visit", base_band=(70, 80), pipeline_tier=2, credibility_score=50
    )
    contact_gain = contact.interest_after - contact.interest_before
    visit_gain = visit.interest_after - visit.interest_before
    assert visit_gain > contact_gain > 0


def test_interest_is_capped_at_100():
    state = {"interest": 95}
    _, result = apply_action(
        state, "visit", base_band=(70, 80), pipeline_tier=1, credibility_score=80
    )
    assert result.interest_after == 100


def test_every_action_reports_a_non_trivial_delta():
    # Step 7.4: if any action produces no delta in a tracked field, that's the
    # real bug. Guard all three.
    for action in ("scout", "contact", "visit"):
        _, result = apply_action(
            {}, action, base_band=(65, 85), pipeline_tier=2, credibility_score=50
        )
        changed_band = result.ovr_band_after != result.ovr_band_before
        changed_interest = result.interest_after != result.interest_before
        assert changed_band or changed_interest, f"{action} produced no delta"
        assert result.headline
        assert result.next_step


def test_base_interest_warmer_for_better_pipeline():
    strong = base_interest(pipeline_tier=1, credibility_score=50)
    weak = base_interest(pipeline_tier=4, credibility_score=50)
    assert strong > weak


def test_narrow_band_noop_when_unscouted():
    assert narrow_band((68, 82), scouted=False) == (68, 82)
