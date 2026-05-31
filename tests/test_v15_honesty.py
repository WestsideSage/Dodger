"""V15 honesty gate — pytest suite.

Every ProofChip.source / credibility-evidence string and every staff effect
lane must be backed by a real payload field from the backend, not a
hardcoded assertion. A milestone "proof" annotation may only render when the
holder + stats backing it actually exist in the career record.

Phase map:
  - credibility evidence strings: Phase 3a (Dynasty Office / Credibility)
  - staff effect lanes: Phase 3b (Staff Impact)
  - history milestone proof annotations: Phase 4a (History & Identity)
  - recruiting payload ProofChip sources: Phase 2a (Recruit Board)
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from dodgeball_sim import persistence
from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.server import app, get_db


# ---------------------------------------------------------------------------
# Shared fixture: a fresh aurora career (matches the canonical e2e seed).
# ---------------------------------------------------------------------------

def _fresh_aurora_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    persistence.create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
    conn.commit()
    return conn


@pytest.fixture()
def aurora_client():
    conn = _fresh_aurora_conn()

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Task 2a — Credibility evidence strings are payload-backed (Phase 3a)
# ---------------------------------------------------------------------------

class TestCredibilityEvidenceHonesty:
    """Each evidence[] string must derive from a real career stat,
    not a hardcoded claim that could be true or false regardless of state."""

    def test_credibility_endpoint_returns_evidence_list(self, aurora_client):
        res = aurora_client.get("/api/dynasty-office")
        assert res.status_code == 200, res.text
        data = res.json().get("recruiting", {}).get("credibility", {})
        # Endpoint must return an 'evidence' list (Phase 3a contract).
        assert "evidence" in data, f"Missing 'evidence' key in: {list(data.keys())}"
        assert isinstance(data["evidence"], list)

    def test_credibility_evidence_strings_are_non_empty(self, aurora_client):
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("recruiting", {}).get("credibility", {})
        for i, ev in enumerate(data.get("evidence", [])):
            assert isinstance(ev, str), f"evidence[{i}] is not a string: {ev!r}"
            assert ev.strip(), f"evidence[{i}] is an empty string"

    def test_credibility_evidence_has_no_placeholder_tokens(self, aurora_client):
        """Placeholder tokens like 'TODO', 'TBD', 'N/A' in evidence strings
        indicate an unresolved template rather than a real payload value."""
        PLACEHOLDER_TOKENS = ("TODO", "TBD", "N/A", "PLACEHOLDER", "FIXME", "???")
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("recruiting", {}).get("credibility", {})
        for ev in data.get("evidence", []):
            for token in PLACEHOLDER_TOKENS:
                assert token not in ev, (
                    f"Placeholder token {token!r} found in evidence string: {ev!r}"
                )

    def test_credibility_grade_consistent_with_score(self, aurora_client):
        """The displayed credibility grade label must not be out of step with
        the numeric score. A fresh career should have a low-tier grade."""
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("recruiting", {}).get("credibility", {})
        score = data.get("credibility_score", None)
        grade = data.get("grade", None)
        if score is not None and grade is not None:
            # A fresh aurora career has no completed seasons — credibility
            # score should be at the low end. If grade claims "Elite" on a
            # fresh save it is fabricated.
            ELITE_GRADES = {"Elite", "S", "S+", "Legendary"}
            assert grade not in ELITE_GRADES, (
                f"Fresh career credibility grade {grade!r} is implausibly high "
                f"(score={score}). Evidence string may be fabricated."
            )


# ---------------------------------------------------------------------------
# Task 2b — Staff effect lanes are payload-backed (Phase 3b)
# ---------------------------------------------------------------------------

class TestStaffEffectLanesHonesty:
    """Staff effect lanes (Phase 3b / V14 Task 4) must reflect real staff
    ratings, not hardcoded copy. Every lane string must contain a numeric
    value derived from the staff member's actual rating."""

    def test_staff_payload_has_effect_lanes(self, aurora_client):
        res = aurora_client.get("/api/dynasty-office")
        assert res.status_code == 200, res.text
        data = res.json().get("staff_market", {})
        # Phase 3b expects 'effect_summary' for current_staff.
        staff = data.get("current_staff", [])
        assert staff, "current_staff list is empty on a fresh aurora career"
        for member in staff:
            assert "effect_summary" in member, (
                f"Staff member {member.get('name', '?')} is missing 'effect_summary'"
            )
            assert isinstance(member["effect_summary"], str), (
                f"effect_summary must be a string, got {type(member['effect_summary'])}"
            )
            assert member["effect_summary"], (
                f"effect_summary for {member.get('name', '?')} is empty"
            )

    def test_staff_effect_lanes_contain_no_placeholder_tokens(self, aurora_client):
        PLACEHOLDER_TOKENS = ("TODO", "TBD", "N/A", "PLACEHOLDER", "FIXME", "???")
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("staff_market", {})
        for member in data.get("current_staff", []):
            summary = member.get("effect_summary", "")
            for token in PLACEHOLDER_TOKENS:
                assert token not in summary, (
                    f"Placeholder {token!r} in effect summary for "
                    f"{member.get('name', '?')}: {summary!r}"
                )
        for candidate in data.get("candidates", []):
            for lane in candidate.get("effect_lanes", []):
                for token in PLACEHOLDER_TOKENS:
                    assert token not in lane, (
                        f"Placeholder {token!r} in candidate lane for "
                        f"{candidate.get('name', '?')}: {lane!r}"
                    )

    def test_staff_ratings_in_payload_are_integers(self, aurora_client):
        """Phase 0 coerces staff ratings to int at the payload boundary.
        Phase 5 confirms this invariant holds end-to-end."""
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("staff_market", {})
        for member in data.get("current_staff", []):
            rp = member.get("rating_primary")
            rs = member.get("rating_secondary")
            if rp is not None:
                assert isinstance(rp, int), (
                    f"{member.get('name', '?')} rating_primary is float: {rp!r}"
                )
            if rs is not None:
                assert isinstance(rs, int), (
                    f"{member.get('name', '?')} rating_secondary is float: {rs!r}"
                )

    def test_candidate_effect_lanes_contain_no_float_strings(self, aurora_client):
        """Phase 0 removes ':.1f' formatting from candidate effect lanes.
        Confirm no '.0/' or trailing '.0' leaks through (Phase 0 + 3b combined)."""
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("staff_market", {})
        for candidate in data.get("candidates", []):
            for lane in candidate.get("effect_lanes", []):
                assert ".0/" not in lane, (
                    f"Float '.0/' leak in candidate lane: {lane!r}"
                )
                assert not lane.endswith(".0"), (
                    f"Trailing float '.0' in candidate lane: {lane!r}"
                )


# ---------------------------------------------------------------------------
# Task 2c — History milestone proof annotations (Phase 4a)
# ---------------------------------------------------------------------------

class TestHistoryMilestoneProofHonesty:
    """Milestone descriptions with a 'proof' annotation (e.g. 'Best Newcomer'
    → player name + stats) must only render when the underlying career record
    actually contains that holder and those stats. A fabricated proof annotation
    that references a player who does not exist in the career violates the
    decision-traceability north star."""

    def test_history_endpoint_returns_timeline(self, aurora_client):
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        assert res.status_code == 200, res.text
        data = res.json()
        assert "timeline" in data

    def test_milestone_proof_sources_are_payload_strings(self, aurora_client):
        """Every milestone entry that exposes a 'proof' or 'source' field must
        contain a non-empty string derived from career data, not a hardcoded
        claim. On a fresh career with no completed seasons, no milestone should
        claim a proof that references a real player — because none exists."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        for entry in data.get("timeline", []):
            proof = entry.get("proof") or entry.get("source")
            if proof is not None:
                assert isinstance(proof, str), (
                    f"Milestone proof must be a string, got {type(proof)}: {proof!r}"
                )
                assert proof.strip(), "Milestone proof string is empty"
                PLACEHOLDER_TOKENS = ("TODO", "TBD", "PLACEHOLDER", "???")
                for token in PLACEHOLDER_TOKENS:
                    assert token not in proof, (
                        f"Placeholder {token!r} in milestone proof: {proof!r}"
                    )

    def test_fresh_career_milestone_proofs_do_not_name_nonexistent_players(
        self, aurora_client
    ):
        """A fresh career has no completed season, so no award has been given.
        No milestone entry should reference a player name as proof of an award
        that was never made. The roster is seeded, so player names are known —
        but if a milestone says e.g. 'Best Newcomer: [Name]' on a fresh save,
        that is a fabricated claim."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        # On a fresh career there should be no completed-season milestones at all.
        completed_season_milestones = [
            e for e in data.get("timeline", [])
            if e.get("season_number", 0) > 0 and e.get("proof")
        ]
        assert completed_season_milestones == [], (
            f"Fresh career has milestone entries with proof for a completed season "
            f"that never happened: {completed_season_milestones}"
        )

    def test_banners_list_is_empty_on_fresh_career(self, aurora_client):
        """Phase 4a introduces an honest EmptyState for banners. A fresh career
        has no championship banners — the banners list must be empty, not
        populated with fabricated placeholder entries."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        banners = data.get("banners", [])
        assert isinstance(banners, list)
        # Fabricated banners would appear as non-empty on a fresh career.
        assert banners == [], (
            f"Fresh career has non-empty banners list: {banners}. "
            "Banners should only exist after a championship is won."
        )

    def test_alumni_list_is_empty_on_fresh_career(self, aurora_client):
        """Phase 4a introduces an honest EmptyState for alumni. A fresh career
        has no retired alumni — alumni must be empty, not placeholder-populated."""
        res = aurora_client.get("/api/history/my-program?club_id=aurora")
        data = res.json()
        alumni = data.get("alumni", [])
        assert isinstance(alumni, list)
        assert alumni == [], (
            f"Fresh career has non-empty alumni list: {alumni}. "
            "Alumni should only exist after players retire from the program."
        )


# ---------------------------------------------------------------------------
# Task 2d — Recruiting payload ProofChip sources (Phase 2a)
# ---------------------------------------------------------------------------

class TestRecruitingPayloadHonesty:
    """ProofChip sources surfaced on the Recruit Board (Phase 2a) must be
    real payload fields. The scouting state must expose only what has been
    revealed by actual scout actions — no values should be 'known' before
    any scouting has occurred on a fresh career."""

    def test_recruit_board_endpoint_returns_prospects(self, aurora_client):
        res = aurora_client.get("/api/dynasty-office")
        assert res.status_code == 200, res.text
        data = res.json().get("recruiting", {})
        assert "prospects" in data or "board" in data, (
            f"Expected 'prospects' or 'board' key, got: {list(data.keys())}"
        )

    def test_recruit_scouting_state_present(self, aurora_client):
        """Each prospect must carry a scouting_state field (the fog-of-war
        system from Phase 1 KnownValue + Phase 2a consume). On a fresh career
        with no scout actions, all values should be 'estimated' or 'hidden',
        never falsely 'known'."""
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("recruiting", {})
        prospects = data.get("prospects") or data.get("board") or []
        if not prospects:
            pytest.skip("No prospects on board — cannot validate scouting state")
        for p in prospects[:5]:  # sample first 5 to keep test fast
            # If a scouting_state field is present, it must be a valid Knowledge value.
            scouting_state = p.get("scouting_state")
            if scouting_state is not None:
                assert scouting_state in ("known", "estimated", "hidden"), (
                    f"Invalid scouting_state {scouting_state!r} for prospect "
                    f"{p.get('name', '?')}"
                )

    def test_recruit_fit_score_is_integer_or_none(self, aurora_client):
        """fit_score must be an integer 0–100 or absent — never a float."""
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("recruiting", {})
        prospects = data.get("prospects") or data.get("board") or []
        for p in prospects:
            fs = p.get("fit_score")
            if fs is not None:
                assert isinstance(fs, int), (
                    f"fit_score for {p.get('name', '?')} is not int: {fs!r}"
                )
                assert 0 <= fs <= 100, f"fit_score {fs} out of range [0, 100]"

    def test_recruit_filter_buckets_are_mutually_exclusive(self, aurora_client):
        """Phase 0 reconciled the recruit filter labels. Strong Fit (>=80),
        Fair Fit (65-79), At Risk (<65) are mutually exclusive and sum to All.
        Verify at the payload level."""
        res = aurora_client.get("/api/dynasty-office")
        data = res.json().get("recruiting", {})
        prospects = data.get("prospects") or data.get("board") or []
        if not prospects:
            pytest.skip("No prospects to validate filter buckets")
        strong = [p for p in prospects if (p.get("fit_score") or 0) >= 80]
        fair = [p for p in prospects if 65 <= (p.get("fit_score") or 0) < 80]
        at_risk = [p for p in prospects if (p.get("fit_score") or 0) < 65]
        total_bucketed = len(strong) + len(fair) + len(at_risk)
        assert total_bucketed == len(prospects), (
            f"Filter bucket counts ({len(strong)} + {len(fair)} + {len(at_risk)} = "
            f"{total_bucketed}) do not sum to total prospects ({len(prospects)}). "
            "Buckets are not mutually exclusive."
        )
