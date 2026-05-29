"""Phase 5 — Growth legibility tests.

Asserts that:
- Roster payload carries numeric potential_ceiling, projected_growth, and headroom.
- An Elite-potential player differs from a Low-potential player as expected.
- Development beat carries per-attribute deltas (attr_deltas) for each player.
- Roster Lab trend is an honest empty-state (no stored season OVR history exists
  yet) — surfaces as ovr_season_trend: None on each roster player.
"""
from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.models import Player, PlayerArchetype, PlayerRatings, PlayerTraits
from dodgeball_sim.persistence import create_schema
from dodgeball_sim.server import _build_beat_payload
from dodgeball_sim.web_status_service import build_roster_payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _make_player(pid: str, *, potential: int, ovr: int, age: int, growth_curve: int = 50) -> Player:
    """Build a synthetic player with controllable potential / OVR."""
    r = PlayerRatings(
        accuracy=ovr, power=ovr, dodge=ovr, catch=ovr, stamina=ovr,
        tactical_iq=50, catch_courage=50, throw_selection_iq=50, conditioning_curve=50,
    )
    return Player(
        id=pid,
        name=pid.title(),
        ratings=r,
        archetype=PlayerArchetype.THROWER,
        traits=PlayerTraits(potential=potential, growth_curve=growth_curve, consistency=50, pressure=50),
        age=age,
        club_id="aurora",
        newcomer=False,
    )


# ---------------------------------------------------------------------------
# 1. Roster payload — Player Card fields
# ---------------------------------------------------------------------------

class TestPlayerCardPayload:
    """build_roster_payload enriches each player with ceiling, growth, headroom."""

    def test_new_career_roster_has_ceiling_fields(self):
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
        conn.commit()

        payload = build_roster_payload(conn)
        players = payload["roster"]
        assert len(players) > 0, "Roster must be non-empty"
        for p in players:
            assert "potential_ceiling" in p, f"Missing potential_ceiling on {p['name']}"
            assert "projected_growth" in p, f"Missing projected_growth on {p['name']}"
            assert "headroom" in p, f"Missing headroom on {p['name']}"

    def test_elite_player_has_higher_ceiling_than_low_player(self):
        """Elite ceiling > Low ceiling, and headroom reflects the gap."""
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)

        from dodgeball_sim.persistence import save_club, load_clubs
        clubs = load_clubs(conn)
        club = clubs["aurora"]

        elite = _make_player("p_elite", potential=95, ovr=60, age=20)
        low = _make_player("p_low", potential=63, ovr=60, age=20)

        save_club(conn, club, [elite, low])
        conn.commit()

        payload = build_roster_payload(conn)
        by_id = {p["id"]: p for p in payload["roster"]}

        elite_card = by_id["p_elite"]
        low_card = by_id["p_low"]

        assert elite_card["potential_ceiling"] > low_card["potential_ceiling"]
        assert elite_card["headroom"] > low_card["headroom"]

    def test_projected_growth_is_growing_for_young_player_with_headroom(self):
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)

        from dodgeball_sim.persistence import save_club, load_clubs
        club = load_clubs(conn)["aurora"]
        young = _make_player("p_young", potential=90, ovr=60, age=19)
        save_club(conn, club, [young])
        conn.commit()

        payload = build_roster_payload(conn)
        card = next(p for p in payload["roster"] if p["id"] == "p_young")
        assert card["projected_growth"] == "growing"

    def test_projected_growth_is_declining_for_old_player(self):
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)

        from dodgeball_sim.persistence import save_club, load_clubs
        club = load_clubs(conn)["aurora"]
        # Age 36 > all peak windows, so engine applies decline
        veteran = _make_player("p_vet", potential=75, ovr=74, age=36)
        save_club(conn, club, [veteran])
        conn.commit()

        payload = build_roster_payload(conn)
        card = next(p for p in payload["roster"] if p["id"] == "p_vet")
        assert card["projected_growth"] == "declining"

    def test_headroom_is_ceiling_minus_ovr(self):
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)

        from dodgeball_sim.persistence import save_club, load_clubs
        club = load_clubs(conn)["aurora"]
        player = _make_player("p_check", potential=85, ovr=70, age=23)
        save_club(conn, club, [player])
        conn.commit()

        payload = build_roster_payload(conn)
        card = next(p for p in payload["roster"] if p["id"] == "p_check")
        # ceiling = 85, OVR = 70 (each stat is 70 so overall is 70)
        assert card["potential_ceiling"] == 85
        assert card["headroom"] == 15

    def test_ovr_season_trend_is_none_on_fresh_save(self):
        """No offseason run yet — honest empty-state (None)."""
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
        conn.commit()

        payload = build_roster_payload(conn)
        for p in payload["roster"]:
            assert "ovr_season_trend" in p, f"Missing ovr_season_trend on {p['name']}"
            assert p["ovr_season_trend"] is None, (
                f"Expected None (no offseason yet) but got {p['ovr_season_trend']!r} for {p['name']}"
            )

    def test_ovr_season_trend_is_two_element_list_after_offseason(self):
        """After an offseason, trend = [before, after] from offseason_development_json."""
        import json
        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)

        # Simulate what initialize_manager_offseason writes
        dev_rows = [
            {
                "player_id": "aurora_1",
                "player_name": "Test",
                "club_id": "aurora",
                "before": 62,
                "after": 65,
                "delta": 3,
                "notes": [],
                "attr_deltas": {},
                "potential_ceiling": 85,
            }
        ]
        from dodgeball_sim.persistence import set_state
        set_state(conn, "offseason_development_json", json.dumps(dev_rows))
        conn.commit()

        payload = build_roster_payload(conn)
        by_id = {p["id"]: p for p in payload["roster"]}

        # Only the player that appeared in dev_rows gets a trend
        if "aurora_1" in by_id:
            card = by_id["aurora_1"]
            assert card["ovr_season_trend"] is not None, "Expected trend after offseason"
            assert len(card["ovr_season_trend"]) == 2
            assert card["ovr_season_trend"][0] == 62
            assert card["ovr_season_trend"][1] == 65

        # Players NOT in dev_rows still have None
        others = [p for p in payload["roster"] if p["id"] != "aurora_1"]
        for p in others:
            assert p["ovr_season_trend"] is None, (
                f"Expected None for player not in offseason dev rows: {p['name']}"
            )


# ---------------------------------------------------------------------------
# 2. Development beat — per-attribute deltas
# ---------------------------------------------------------------------------

class TestDevBeatAttrDeltas:
    """The development beat payload carries attr_deltas on each player entry."""

    def _make_dev_rows(self, *, include_deltas: bool = True):
        """Construct a hand-built dev_rows list as offseason_ceremony would produce."""
        before_ratings = dict(
            accuracy=60, power=62, dodge=58, catch=61, stamina=63,
            tactical_iq=50, catch_courage=50, throw_selection_iq=50, conditioning_curve=50,
        )
        after_ratings = dict(
            accuracy=62, power=63, dodge=58, catch=61, stamina=64,
            tactical_iq=51, catch_courage=50, throw_selection_iq=50, conditioning_curve=50,
        )
        row = {
            "player_id": "p1",
            "player_name": "Test Player",
            "club_id": "aurora",
            "before": 60,
            "after": 62,
            "delta": 2,
            "notes": [],
            "potential_ceiling": 85,
            "projected_growth": "growing",
        }
        if include_deltas:
            row["attr_deltas"] = {
                stat: after_ratings[stat] - before_ratings[stat]
                for stat in before_ratings
            }
        return [row]

    def test_dev_beat_players_have_attr_deltas_key(self):
        conn = _make_conn()
        dev_rows = self._make_dev_rows()
        result = _build_beat_payload(
            "development",
            awards=[],
            clubs={},
            rosters={},
            standings=[],
            ret_rows=[],
            season=None,
            season_outcome=None,
            next_preview=None,
            signed_player_id="",
            dev_rows=dev_rows,
            player_club_id="aurora",
            conn=conn,
        )
        assert "players" in result
        players = result["players"]
        assert len(players) > 0
        for p in players:
            assert "attr_deltas" in p, f"Missing attr_deltas in dev beat player {p}"

    def test_dev_beat_attr_deltas_are_correct(self):
        conn = _make_conn()
        dev_rows = self._make_dev_rows()
        result = _build_beat_payload(
            "development",
            awards=[],
            clubs={},
            rosters={},
            standings=[],
            ret_rows=[],
            season=None,
            season_outcome=None,
            next_preview=None,
            signed_player_id="",
            dev_rows=dev_rows,
            player_club_id="aurora",
            conn=conn,
        )
        p = result["players"][0]
        deltas = p["attr_deltas"]
        # accuracy went from 60 -> 62, delta = +2
        assert deltas["accuracy"] == 2
        # dodge didn't change, delta = 0
        assert deltas["dodge"] == 0
        # stamina went from 63 -> 64, delta = +1
        assert deltas["stamina"] == 1

    def test_dev_beat_attr_deltas_are_ints(self):
        conn = _make_conn()
        dev_rows = self._make_dev_rows()
        result = _build_beat_payload(
            "development",
            awards=[],
            clubs={},
            rosters={},
            standings=[],
            ret_rows=[],
            season=None,
            season_outcome=None,
            next_preview=None,
            signed_player_id="",
            dev_rows=dev_rows,
            player_club_id="aurora",
            conn=conn,
        )
        p = result["players"][0]
        for stat, val in p["attr_deltas"].items():
            assert isinstance(val, int), f"{stat} delta is {type(val)}, expected int"

    def test_dev_beat_attr_deltas_empty_when_no_rows_with_deltas(self):
        """When dev_rows has no attr_deltas key, payload gracefully uses empty dict."""
        conn = _make_conn()
        dev_rows = self._make_dev_rows(include_deltas=False)
        result = _build_beat_payload(
            "development",
            awards=[],
            clubs={},
            rosters={},
            standings=[],
            ret_rows=[],
            season=None,
            season_outcome=None,
            next_preview=None,
            signed_player_id="",
            dev_rows=dev_rows,
            player_club_id="aurora",
            conn=conn,
        )
        p = result["players"][0]
        assert "attr_deltas" in p
        assert isinstance(p["attr_deltas"], dict)

    def test_dev_beat_also_carries_ceiling_on_players(self):
        """Dev beat surfaces potential_ceiling for display alongside the delta."""
        conn = _make_conn()
        dev_rows = self._make_dev_rows()
        result = _build_beat_payload(
            "development",
            awards=[],
            clubs={},
            rosters={},
            standings=[],
            ret_rows=[],
            season=None,
            season_outcome=None,
            next_preview=None,
            signed_player_id="",
            dev_rows=dev_rows,
            player_club_id="aurora",
            conn=conn,
        )
        p = result["players"][0]
        assert "potential_ceiling" in p
        assert p["potential_ceiling"] == 85


# ---------------------------------------------------------------------------
# 3. Integration — attr_deltas round-trip through initialize_manager_offseason
# ---------------------------------------------------------------------------

class TestDevBeatRoundTrip:
    """Exercises the real offseason path to confirm attr_deltas survive into the beat."""

    def test_attr_deltas_survive_real_offseason_roundtrip(self):
        """initialize_manager_offseason writes attr_deltas; read them back via build_beat_payload."""
        import json
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import (
            get_state,
            load_all_rosters,
            load_clubs,
            load_season,
            set_state,
        )
        from dodgeball_sim.rng import DeterministicRNG

        conn = _make_conn()
        initialize_curated_manager_career(conn, "aurora", root_seed=20260426)
        conn.commit()

        clubs = load_clubs(conn)
        rosters = load_all_rosters(conn)
        season_id = get_state(conn, "active_season_id")
        season = load_season(conn, season_id)

        # Run the offseason — this writes offseason_development_json with attr_deltas
        initialize_manager_offseason(
            conn=conn,
            season=season,
            clubs=clubs,
            rosters=rosters,
            root_seed=20260426,
        )
        conn.commit()

        # Load the dev rows that were persisted
        raw = get_state(conn, "offseason_development_json")
        assert raw, "offseason_development_json must be set after initialize_manager_offseason"
        dev_rows = json.loads(raw)

        player_club_id = get_state(conn, "player_club_id") or "aurora"
        player_dev_rows = [r for r in dev_rows if r.get("club_id") == player_club_id]
        assert len(player_dev_rows) > 0, "Must have dev rows for the player club"

        # Every dev row must carry attr_deltas
        for row in player_dev_rows:
            assert "attr_deltas" in row, f"attr_deltas missing from dev row: {row['player_name']}"
            assert isinstance(row["attr_deltas"], dict)
            for stat, val in row["attr_deltas"].items():
                assert isinstance(val, int), f"{stat} delta should be int, got {type(val)}"

        # Build the beat payload and confirm attr_deltas survive into the frontend payload
        updated_rosters = load_all_rosters(conn)
        result = _build_beat_payload(
            "development",
            awards=[],
            clubs=clubs,
            rosters=updated_rosters,
            standings=[],
            ret_rows=[],
            season=season,
            season_outcome=None,
            next_preview=None,
            signed_player_id="",
            dev_rows=dev_rows,
            player_club_id=player_club_id,
            conn=conn,
        )
        assert "players" in result
        for beat_player in result["players"]:
            assert "attr_deltas" in beat_player, (
                f"attr_deltas missing from beat player {beat_player['name']}"
            )
            assert isinstance(beat_player["attr_deltas"], dict)
            # potential_ceiling must also be present
            assert "potential_ceiling" in beat_player
