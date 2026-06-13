"""V24 Phase 1 gates — whole-world AI recruiting (the end-state-dominance fix).

Per docs/specs/2026-06-12-v24-the-board-spec.md (Phase 1):

V23 shipped the 28-club pyramid but scoped the AI Signing Day market to the
USER'S DIVISION only (recruitment._eligible_ai_offer_clubs), so the world's top
clubs (Premier + Circuit) got NO new blood while an engaged user compounded —
the disclosed "end-state dominance" path to unopposed Worlds wins. V24 opens
recruiting to the whole world on merit: every division's AI clubs recruit their
own class, so the top keeps pace.

These tests pin the fix: the offseason AI sweep signs new prospects in divisions
OTHER than the user's, and every AI-bearing division gets new blood — while the
LEGACY (non-pyramid) world is untouched.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.persistence import (
    get_state,
    load_division_map,
    load_prospect_pool,
    load_recruitment_signings,
    save_prospect_pool,
)
from dodgeball_sim.recruitment import generate_prospect_pool, run_ai_offseason_signings
from dodgeball_sim.rng import DeterministicRNG, derive_seed

ROOT_SEED = 20260612


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _pyramid_takeover(conn: sqlite3.Connection, seed: int = ROOT_SEED) -> str:
    """A fresh pyramid takeover career: user 'aurora' seated in the Premier League."""
    initialize_curated_manager_career(
        conn, "aurora", seed, ruleset_selection="official_foam", world="pyramid"
    )
    return "aurora"


def _ensure_prospect_pool(conn: sqlite3.Connection, class_year: int, seed: int = ROOT_SEED) -> None:
    """Seed the class the way the offseason scouting wiring does (same namespace),
    so calling the AI sweep in isolation has a pool to draw from."""
    if not load_prospect_pool(conn, class_year):
        rng = DeterministicRNG(derive_seed(seed, "prospect_gen", str(class_year)))
        save_prospect_pool(conn, generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG))


def _run_sweep(conn: sqlite3.Connection, user_club_id: str, seed: int = ROOT_SEED):
    season_id = get_state(conn, "active_season_id")
    digits = "".join(ch for ch in season_id if ch.isdigit())
    class_year = int(digits) if digits else 1
    _ensure_prospect_pool(conn, class_year, seed)
    run_ai_offseason_signings(conn, seed, season_id, class_year, user_club_id)
    return season_id


class TestWholeWorldAIRecruiting:
    def test_ai_clubs_outside_user_division_sign_new_blood(self):
        conn = _conn()
        user = _pyramid_takeover(conn)
        season_id = _run_sweep(conn, user)

        division_map = load_division_map(conn, season_id)
        seat = division_map[user]
        ai_signings = [s for s in load_recruitment_signings(conn, season_id) if s.source == "ai"]
        out_of_division = {
            s.club_id
            for s in ai_signings
            if division_map[s.club_id].division_id != seat.division_id
        }
        assert out_of_division, (
            "V23 end-state-dominance gap: AI clubs outside the user's division "
            "signed no new prospects. Whole-world recruiting must give every "
            "division new blood."
        )

    def test_every_domestic_division_signs_new_blood(self):
        # With the whole world recruiting from a class wide enough to feed 28
        # clubs, each of the three domestic divisions draws new blood every
        # offseason (the Circuit is seeded full early and churns later).
        conn = _conn()
        user = _pyramid_takeover(conn)
        season_id = _run_sweep(conn, user)

        division_map = load_division_map(conn, season_id)
        ai = [s for s in load_recruitment_signings(conn, season_id) if s.source == "ai"]
        signed_divisions = {division_map[s.club_id].division_id for s in ai}
        for div_id in ("premier", "challenger", "district"):
            assert div_id in signed_divisions, f"{div_id} signed no new blood"


class TestPyramidProspectClass:
    def test_pyramid_recruiting_class_is_wide(self):
        from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG, PYRAMID_PROSPECT_CLASS_SIZE
        from dodgeball_sim.scouting_center import initialize_scouting_for_career

        conn = _conn()
        _pyramid_takeover(conn)
        # class_year 7 is unseeded — exercise the authoritative seed path.
        initialize_scouting_for_career(conn, ROOT_SEED, DEFAULT_SCOUTING_CONFIG, class_year=7)
        assert len(load_prospect_pool(conn, 7)) == PYRAMID_PROSPECT_CLASS_SIZE

    def test_legacy_recruiting_class_is_unchanged(self):
        from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
        from dodgeball_sim.scouting_center import initialize_scouting_for_career

        conn = _conn()
        initialize_curated_manager_career(conn, "aurora", ROOT_SEED)  # legacy world
        initialize_scouting_for_career(conn, ROOT_SEED, DEFAULT_SCOUTING_CONFIG, class_year=7)
        assert len(load_prospect_pool(conn, 7)) == 25


class TestTierCeilingWeighting:
    def test_top_tier_chases_ceiling_harder_than_bottom(self):
        from dodgeball_sim.recruitment import _tier_ceiling_bonus

        # A high-upside prospect (public high band ~90) is worth more to a
        # tier-1 board (Premier/Circuit) than a tier-3 (District) board.
        assert _tier_ceiling_bonus(1, 90) > _tier_ceiling_bonus(3, 90) > 0

    def test_floor_prospect_earns_no_ceiling_premium(self):
        from dodgeball_sim.recruitment import _tier_ceiling_bonus

        # A floor-level prospect (high band at/below the baseline) earns no
        # ceiling premium — the bonus rewards upside, not raw signing.
        assert _tier_ceiling_bonus(1, 55) < _tier_ceiling_bonus(1, 90)
        assert _tier_ceiling_bonus(1, 40) == 0.0


class TestMotivationOffer:
    def test_fit_raises_offer_and_veto_floors_it(self):
        from dodgeball_sim.config import (
            CONTESTED_USER_OFFER_BASE,
            CONTESTED_USER_OFFER_INTEREST_WEIGHT,
            CONTESTED_VETO_OFFER_FLOOR,
        )
        from dodgeball_sim.recruitment import _user_offer_strength

        # No fit reproduces the legacy V16 offer exactly (legacy byte-identical).
        base = _user_offer_strength(interest=50, fit_score=0.0, veto=False)
        assert base == round(
            CONTESTED_USER_OFFER_BASE + 50 * CONTESTED_USER_OFFER_INTEREST_WEIGHT, 4
        )
        # Satisfying his motivations strengthens the offer (courtship -> outcome).
        assert _user_offer_strength(50, 0.8, False) > base
        # Failing his dealbreaker floors the offer — he never verbals, even at
        # max interest and fit.
        assert _user_offer_strength(100, 1.0, True) == CONTESTED_VETO_OFFER_FLOOR
        assert _user_offer_strength(100, 1.0, True) < base


class TestBoardMotivations:
    def test_pyramid_board_reveals_dealbreaker_only_when_scouted(self):
        import json

        from dodgeball_sim.persistence import set_state
        from dodgeball_sim.recruiting_office import build_recruiting_state

        conn = _conn()
        _pyramid_takeover(conn)
        state = build_recruiting_state(
            conn, season_id="season_1", player_club_id="aurora", root_seed=ROOT_SEED, history=[]
        )
        rows = state["prospects"]
        assert rows
        row = rows[0]
        # Non-dealbreaker motivations are visible; each is a graded receipt.
        assert row["motivations"], "expected visible motivation grades"
        for grade in row["motivations"]:
            assert {"label", "letter", "receipt"} <= set(grade)
        # The dealbreaker is hidden until the prospect is scouted.
        assert row["dealbreaker"] is None

        # Scout him -> the dealbreaker (and its veto) is revealed.
        set_state(
            conn,
            "prospect_recruitment_actions_json",
            json.dumps({row["player_id"]: {"scouted": True}}),
        )
        scouted = build_recruiting_state(
            conn, season_id="season_1", player_club_id="aurora", root_seed=ROOT_SEED, history=[]
        )
        srow = next(r for r in scouted["prospects"] if r["player_id"] == row["player_id"])
        assert srow["dealbreaker"] is not None
        assert {"label", "letter", "receipt", "veto"} <= set(srow["dealbreaker"])


class TestDistrictRooting:
    def test_pyramid_prospects_are_district_rooted(self):
        from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
        from dodgeball_sim.scouting_center import initialize_scouting_for_career
        from dodgeball_sim.world import DISTRICT_REGIONS

        conn = _conn()
        _pyramid_takeover(conn)
        initialize_scouting_for_career(conn, ROOT_SEED, DEFAULT_SCOUTING_CONFIG, class_year=7)
        pool = load_prospect_pool(conn, 7)
        assert pool
        assert all(p.hometown in DISTRICT_REGIONS for p in pool), (
            "Pyramid prospects must be rooted in one of the 7 districts, not a surname"
        )

    def test_hometown_pool_does_not_shift_the_rng_stream(self):
        # The whole point of routing hometown through rng.choice (one draw,
        # any list length): swapping surnames for districts changes ONLY the
        # hometown — every other prospect attribute stays byte-identical, so no
        # downstream witness moves and legacy saves are unaffected.
        from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
        from dodgeball_sim.recruitment import generate_prospect_pool
        from dodgeball_sim.world import DISTRICT_REGIONS

        def _fresh_rng():
            return DeterministicRNG(derive_seed(ROOT_SEED, "prospect_gen", "1"))

        surnamed = generate_prospect_pool(1, _fresh_rng(), DEFAULT_SCOUTING_CONFIG)
        districted = generate_prospect_pool(
            1, _fresh_rng(), DEFAULT_SCOUTING_CONFIG, hometown_pool=DISTRICT_REGIONS
        )
        assert len(surnamed) == len(districted)
        for s, d in zip(surnamed, districted):
            assert s.player_id == d.player_id
            assert s.name == d.name
            assert s.hidden_ratings == d.hidden_ratings
            assert s.hidden_trajectory == d.hidden_trajectory
            assert s.public_ratings_band == d.public_ratings_band
            assert s.pipeline_tier == d.pipeline_tier
            assert s.hometown != d.hometown  # only the hometown differs
            assert d.hometown in DISTRICT_REGIONS
