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
