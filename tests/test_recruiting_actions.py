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


# The displayed-strongest pipeline tier. The UI (PipelineEmblem.tsx TIER_STYLE)
# labels tier 5 "Elite" and terms.ts `recruit.pipeline` teaches "stronger pipeline
# tier means warmer prospects" — so 5 is the displayed strongest. There is no
# frontend test runner (see docs/agents memory), so we pin the displayed-strongest
# tier here as a source-of-truth constant the contract test reads.
DISPLAYED_STRONGEST_TIER = 5
PIPELINE_TIERS = range(1, DISPLAYED_STRONGEST_TIER + 1)  # recruitment.py rolls 1..5


def test_base_interest_warmer_for_better_pipeline():
    # WT-25: higher pipeline tier must start WARMER. The displayed-strongest tier
    # (5 = Elite) must beat a weaker tier. Compare 5 vs 1 (never adjacent tiers like
    # 1 vs 2, which both floor at the same base) so the inequality is strict.
    strongest = base_interest(pipeline_tier=DISPLAYED_STRONGEST_TIER, credibility_score=50)
    weaker = base_interest(pipeline_tier=1, credibility_score=50)
    assert strongest > weaker


def test_base_interest_is_monotonic_in_pipeline_tier():
    # The flip must be a clean direction reversal: interest is non-decreasing as the
    # tier rises, and strictly increasing somewhere (not a flat curve).
    values = [base_interest(pipeline_tier=t, credibility_score=50) for t in PIPELINE_TIERS]
    assert values == sorted(values), values
    assert values[-1] > values[0], values


def test_base_interest_preserves_warmest_magnitude():
    # WT-25 must NOT re-tune balance: only the tier→interest direction flips. The
    # exact-mirror flip keeps the warmest contribution identical to the old curve.
    # Prior curve's warmest tier_floor was max(0, 4 - 1) * 5 = 15, so the warmest
    # base (zero credibility) was 30 + 15 = 45. The new warmest tier must match it.
    warmest = base_interest(pipeline_tier=DISPLAYED_STRONGEST_TIER, credibility_score=0)
    assert warmest == 45


def test_displayed_strongest_tier_matches_base_interest_argmax():
    # Audit CONTRACT (ADR 0002): the tier the UI displays as strongest must BE the
    # mechanically strongest. The displayed-strongest tier and base_interest's
    # ordering must point the SAME way — the argmax of base_interest over all tiers
    # equals the displayed-strongest tier. This is the regression guard against the
    # inversion that taught players to value prospects backwards.
    argmax_tier = max(
        PIPELINE_TIERS,
        key=lambda t: base_interest(pipeline_tier=t, credibility_score=50),
    )
    assert argmax_tier == DISPLAYED_STRONGEST_TIER


def test_narrow_band_noop_when_unscouted():
    assert narrow_band((68, 82), scouted=False) == (68, 82)
