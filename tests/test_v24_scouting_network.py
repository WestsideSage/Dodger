"""V24 The Board Phase 6 — money-gated Scouting Network visibility tiers.

Per docs/specs/2026-06-12-v24-the-board-spec.md (Phase 6): a per-club network
LEVEL (L1/L2/L3) is a treasury sink that gates which prospects render a full
sheet vs a bare name. L1 = your district + neighbors (district-reach kids only);
L2 adds regional reach; L3 adds national. A prospect's REACH band is a pure
function of his hidden trajectory (no new draw). AI clubs carry network levels by
tier, producing the blind spots that leave gems unrecruited. The scouting head
compresses upgrade cost (the staff cost-compression consumer).

These pin the pure layer (reach band, neighbors, visibility, cost). The DB-level
treasury sink + board gate + AI blind-spot fences ride in the integration tests.
"""
from __future__ import annotations

from dodgeball_sim.scouting_network import (
    REACH_BANDS,
    network_upgrade_cost,
    prospect_fully_visible,
    reach_band_for_trajectory,
)
from dodgeball_sim.world import district_neighbors


class TestReachBand:
    def test_star_and_generational_are_national(self):
        assert reach_band_for_trajectory("STAR") == "NATIONAL"
        assert reach_band_for_trajectory("GENERATIONAL") == "NATIONAL"

    def test_impact_is_regional(self):
        assert reach_band_for_trajectory("IMPACT") == "REGIONAL"

    def test_normal_is_district(self):
        assert reach_band_for_trajectory("NORMAL") == "DISTRICT"

    def test_bands_are_the_three_known(self):
        assert set(REACH_BANDS) == {"DISTRICT", "REGIONAL", "NATIONAL"}


class TestDistrictNeighbors:
    def test_symmetric_ring(self):
        # Adjacency is symmetric: if A neighbors B, B neighbors A.
        from dodgeball_sim.world import DISTRICT_REGIONS

        for region in DISTRICT_REGIONS:
            for neighbor in district_neighbors(region):
                assert region in district_neighbors(neighbor)

    def test_each_district_has_two_neighbors(self):
        from dodgeball_sim.world import DISTRICT_REGIONS

        for region in DISTRICT_REGIONS:
            assert len(district_neighbors(region)) == 2

    def test_unknown_region_has_no_neighbors(self):
        assert district_neighbors("Nowhere") == ()


class TestVisibility:
    HOME = "Harborside District"
    NEIGH = district_neighbors("Harborside District")

    def _visible(self, *, reach, hometown, level):
        return prospect_fully_visible(
            reach_band=reach, hometown=hometown, level=level,
            home_district=self.HOME, neighbors=self.NEIGH,
        )

    def test_l1_sees_local_district_kid(self):
        assert self._visible(reach="DISTRICT", hometown=self.HOME, level=1)
        assert self._visible(reach="DISTRICT", hometown=self.NEIGH[0], level=1)

    def test_l1_cannot_see_far_district_kid(self):
        far = "Eastreach District"
        # Eastreach is not Harborside's neighbor on the ring.
        if far not in self.NEIGH and far != self.HOME:
            assert not self._visible(reach="DISTRICT", hometown=far, level=1)

    def test_l1_cannot_see_regional_or_national(self):
        assert not self._visible(reach="REGIONAL", hometown=self.HOME, level=1)
        assert not self._visible(reach="NATIONAL", hometown=self.HOME, level=1)

    def test_l2_adds_regional_and_all_district(self):
        assert self._visible(reach="REGIONAL", hometown="Eastreach District", level=2)
        assert self._visible(reach="DISTRICT", hometown="Eastreach District", level=2)
        assert not self._visible(reach="NATIONAL", hometown=self.HOME, level=2)

    def test_l3_sees_national(self):
        assert self._visible(reach="NATIONAL", hometown="Eastreach District", level=3)


class TestUpgradeCost:
    def test_costs_decrease_with_a_better_scouting_head(self):
        weak = network_upgrade_cost(to_level=2, scouting_head_rating=30)
        strong = network_upgrade_cost(to_level=2, scouting_head_rating=95)
        assert strong < weak

    def test_l3_costs_more_than_l2(self):
        assert network_upgrade_cost(to_level=3, scouting_head_rating=50) > network_upgrade_cost(
            to_level=2, scouting_head_rating=50
        )

    def test_default_head_is_near_base(self):
        # A neutral 50-rated head leaves the base price essentially intact.
        assert network_upgrade_cost(to_level=2, scouting_head_rating=50) == 140


# --- Integration: the money-gated reach on a real D3 (tier-3) save ----------
import sqlite3  # noqa: E402

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.persistence import get_state  # noqa: E402
from dodgeball_sim.recruiting_office import (  # noqa: E402
    apply_recruiting_action,
    build_recruiting_state,
    network_level,
    upgrade_scouting_network,
)

ROOT_SEED = 20260612
D3_CLUB = "harborside"  # a tier-3 District club → starts at network L1


def _d3_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    initialize_curated_manager_career(conn, D3_CLUB, ROOT_SEED, world="pyramid")
    return conn


def _board(conn):
    season_id = get_state(conn, "active_season_id")
    return build_recruiting_state(
        conn, season_id=season_id, player_club_id=D3_CLUB, root_seed=ROOT_SEED, history=[]
    )


class TestNetworkVisibilityFence:
    def test_d3_club_starts_at_l1(self):
        conn = _d3_conn()
        assert network_level(conn) == 1

    def test_below_level_prospects_are_names_not_sheets(self):
        conn = _d3_conn()
        rows = _board(conn)["prospects"]
        hidden = [r for r in rows if r.get("fully_visible") is False]
        assert hidden, "an L1 D3 club must have prospects beyond its reach"
        for r in hidden:
            assert r["public_ovr_band"] is None        # no sheet
            assert r["motivations"] == []
            assert r["can_contact"] is False and r["can_visit"] is False
            assert r["visibility_hint"]                 # tells you how to open him

    def test_visible_prospects_carry_a_full_sheet(self):
        conn = _d3_conn()
        rows = _board(conn)["prospects"]
        visible = [r for r in rows if r.get("fully_visible")]
        assert visible
        for r in visible:
            assert r["public_ovr_band"] is not None


class TestTreasurySink:
    def test_upgrade_spends_treasury_and_widens_reach(self):
        from dodgeball_sim.economy import set_treasury_k, treasury_k

        conn = _d3_conn()
        set_treasury_k(conn, 1000)  # fund the upgrade
        before_visible = sum(1 for r in _board(conn)["prospects"] if r.get("fully_visible"))
        before_treasury = treasury_k(conn)

        result = upgrade_scouting_network(conn)
        assert result["level"] == 2
        assert treasury_k(conn) == before_treasury - result["cost_k"]
        assert network_level(conn) == 2

        after_visible = sum(1 for r in _board(conn)["prospects"] if r.get("fully_visible"))
        assert after_visible > before_visible  # L2 opens more sheets

    def test_upgrade_refused_when_broke(self):
        from dodgeball_sim.economy import set_treasury_k

        conn = _d3_conn()
        set_treasury_k(conn, 0)
        with pytest.raises(ValueError):
            upgrade_scouting_network(conn)


class TestActionBackstop:
    def test_scout_refused_on_a_prospect_beyond_reach(self):
        conn = _d3_conn()
        season_id = get_state(conn, "active_season_id")
        rows = _board(conn)["prospects"]
        hidden_id = next(r["player_id"] for r in rows if r.get("fully_visible") is False)
        with pytest.raises(ValueError):
            apply_recruiting_action(
                conn, prospect_id=hidden_id, action="scout", season_id=season_id,
                player_club_id=D3_CLUB, root_seed=ROOT_SEED, history=[],
            )


import pytest  # noqa: E402
