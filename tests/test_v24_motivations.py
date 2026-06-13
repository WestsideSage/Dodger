"""V24 The Board Phase 3 — receipts-backed recruiting motivations.

Per docs/specs/2026-06-12-v24-the-board-spec.md (Phase 3): each prospect cares
about 2-3 of seven motivations and has one hidden dealbreaker; a club's FIT is
the weighted blend of its GRADE in the motivations he cares about, every grade
computed from real club data with a receipt. A club graded below ~C in the
dealbreaker can never earn a verbal.

These pin the pure layer: deterministic profiles, grades that respond to real
club state, fit, and the dealbreaker veto.
"""
from __future__ import annotations

from types import SimpleNamespace

from dodgeball_sim.motivations import (
    DEALBREAKER_MIN_GRADE,
    MOTIVATIONS,
    ClubMotivationContext,
    club_fit,
    grade_letter,
    grade_motivation,
    prospect_motivation_profile,
)


def _prospect(pid="prospect_1_001", hometown="Harborside District", archetype="Power Thrower"):
    return SimpleNamespace(
        player_id=pid, hometown=hometown, public_archetype_guess=archetype
    )


def _ctx(**over):
    base = dict(
        club_id="c",
        tier=1,
        roster_archetype_counts={},
        roster_size=6,
        prestige=50,
        titles=0,
        hof_count=0,
        staff_avg=60.0,
        program_archetype="Balanced Rebuild",
        home_region=None,
    )
    base.update(over)
    return ClubMotivationContext(**base)


class TestProfile:
    def test_profile_is_deterministic(self):
        a = prospect_motivation_profile(_prospect("prospect_1_004"))
        b = prospect_motivation_profile(_prospect("prospect_1_004"))
        assert a.dealbreaker == b.dealbreaker
        assert a.cared == b.cared
        assert a.weights == b.weights

    def test_profile_structure(self):
        p = prospect_motivation_profile(_prospect("prospect_1_007"))
        assert 2 <= len(p.cared) <= 3
        assert p.dealbreaker in p.cared
        assert all(m in MOTIVATIONS for m in p.cared)
        assert abs(sum(p.weights.values()) - 1.0) < 1e-6
        # The dealbreaker carries the most weight.
        assert p.weights[p.dealbreaker] == max(p.weights.values())

    def test_different_prospects_differ(self):
        seen = {prospect_motivation_profile(_prospect(f"prospect_1_{i:03d}")).dealbreaker
                for i in range(20)}
        assert len(seen) >= 3  # not all the same motivation


class TestGrades:
    def test_hometown_rewards_local(self):
        prospect = _prospect(hometown="Harborside District")
        local, _ = grade_motivation("hometown", _ctx(home_region="Harborside District"), prospect)
        away, _ = grade_motivation("hometown", _ctx(home_region="Northgate District"), prospect)
        assert local > away

    def test_court_time_rewards_open_depth(self):
        prospect = _prospect(archetype="Power Thrower")
        open_lane, _ = grade_motivation("court_time", _ctx(roster_archetype_counts={}), prospect)
        crowded, _ = grade_motivation(
            "court_time", _ctx(roster_archetype_counts={"Power Thrower": 4}), prospect
        )
        assert open_lane > crowded

    def test_contender_rewards_prestige(self):
        prospect = _prospect()
        weak, _ = grade_motivation("contender", _ctx(prestige=5), prospect)
        strong, _ = grade_motivation("contender", _ctx(prestige=95), prospect)
        assert strong > weak

    def test_every_grade_returns_score_and_receipt(self):
        prospect = _prospect()
        ctx = _ctx()
        for m in MOTIVATIONS:
            score, receipt = grade_motivation(m, ctx, prospect)
            assert 0.0 <= score <= 1.0
            assert isinstance(receipt, str) and receipt

    def test_grade_letter_monotonic(self):
        assert grade_letter(0.95) == "A"
        assert grade_letter(0.05) == "F"
        # higher score never maps to a worse letter
        order = "FDCBA"
        prev = -1
        for s in (0.1, 0.42, 0.6, 0.75, 0.9):
            assert order.index(grade_letter(s)) >= prev
            prev = order.index(grade_letter(s))


class TestFitAndVeto:
    def test_all_strong_club_never_vetoes(self):
        strong = _ctx(prestige=99, titles=8, hof_count=5, staff_avg=95,
                      home_region="Harborside District", roster_archetype_counts={})
        for i in range(20):
            p = _prospect(f"prospect_1_{i:03d}", hometown="Harborside District")
            fit = club_fit(strong, p)
            assert not fit.veto
            assert fit.fit > 0.5

    def test_weak_club_vetoes_a_dealbreaker_it_fails(self):
        # Find a prospect whose dealbreaker is 'contender', then a club with
        # rock-bottom prestige must fail his dealbreaker -> veto.
        target = None
        for i in range(60):
            p = _prospect(f"prospect_1_{i:03d}")
            if prospect_motivation_profile(p).dealbreaker == "contender":
                target = p
                break
        assert target is not None, "no contender-dealbreaker prospect found"
        weak = _ctx(prestige=2)
        fit = club_fit(weak, target)
        assert fit.dealbreaker == "contender"
        assert fit.grades["contender"].score < DEALBREAKER_MIN_GRADE
        assert fit.veto

    def test_fit_is_weighted_blend_of_cared_grades(self):
        p = _prospect()
        ctx = _ctx(prestige=80, staff_avg=80, home_region="Harborside District")
        fit = club_fit(ctx, p)
        profile = prospect_motivation_profile(p)
        expected = sum(profile.weights[m] * fit.grades[m].score for m in profile.cared)
        assert abs(fit.fit - expected) < 1e-6
        # Only cared motivations are flagged as such.
        for m in MOTIVATIONS:
            assert fit.grades[m].cared == (m in profile.cared)
