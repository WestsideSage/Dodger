"""V24 The Board — the class wire.

Per docs/specs/2026-06-12-v24-the-board-spec.md (Phase 1 "basic class wire" +
Phase 7 surfacing): a league-wide news line whenever a STAR/GENERATIONAL prospect
signs anywhere in the world, reusing the news_headlines table and surfaced in the
/api/news wire payload.
"""
from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    get_state,
    load_clubs,
    load_news_headlines,
    save_news_headlines,
)
from dodgeball_sim.recruitment import _emit_class_wire
from dodgeball_sim.scouting_center import Prospect
from dodgeball_sim.web_status_service import build_news_payload

ROOT_SEED = 20260612


def _conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    initialize_curated_manager_career(conn, "aurora", ROOT_SEED, world="pyramid")
    return conn


def _prospect(pid: str, trajectory: str) -> Prospect:
    ratings = {k: 80 for k in (
        "accuracy", "power", "dodge", "catch", "stamina",
        "tactical_iq", "catch_courage", "throw_selection_iq", "conditioning_curve",
    )}
    return Prospect(
        player_id=pid,
        class_year=1,
        name=f"Name {pid}",
        age=18,
        hometown="Harborside District",
        hidden_ratings=ratings,
        hidden_trajectory=trajectory,
        hidden_traits=[],
        public_archetype_guess="Sharpshooter",
        public_ratings_band={"ovr": (80, 88)},
        pipeline_tier=5,
    )


class TestEmitClassWire:
    def test_star_signing_writes_a_class_wire_headline(self):
        conn = _conn()
        season_id = get_state(conn, "active_season_id")
        prospect = _prospect("p_star", "STAR")
        signing = SimpleNamespace(player_id="p_star", club_id="aurora")
        _emit_class_wire(conn, season_id, [signing], {"p_star": prospect}, load_clubs(conn))

        wire = [h for h in load_news_headlines(conn, season_id) if h["category"] == "class_wire"]
        assert wire, "a STAR signing must produce a class-wire headline"
        text = wire[0]["headline_text"]
        assert "Name p_star" in text  # the prospect
        assert "p_star" in wire[0]["entity_ids"]

    def test_normal_signing_writes_nothing(self):
        conn = _conn()
        season_id = get_state(conn, "active_season_id")
        prospect = _prospect("p_norm", "NORMAL")
        signing = SimpleNamespace(player_id="p_norm", club_id="aurora")
        _emit_class_wire(conn, season_id, [signing], {"p_norm": prospect}, load_clubs(conn))

        wire = [h for h in load_news_headlines(conn, season_id) if h["category"] == "class_wire"]
        assert wire == []

    def test_idempotent_no_duplicate_headline(self):
        conn = _conn()
        season_id = get_state(conn, "active_season_id")
        prospect = _prospect("p_gen", "GENERATIONAL")
        signing = SimpleNamespace(player_id="p_gen", club_id="aurora")
        clubs = load_clubs(conn)
        _emit_class_wire(conn, season_id, [signing], {"p_gen": prospect}, clubs)
        _emit_class_wire(conn, season_id, [signing], {"p_gen": prospect}, clubs)
        wire = [h for h in load_news_headlines(conn, season_id) if h["category"] == "class_wire"]
        assert len(wire) == 1


class TestNewsPayloadSurfacesClassWire:
    def test_class_wire_appears_in_news_payload(self):
        conn = _conn()
        season_id = get_state(conn, "active_season_id")
        save_news_headlines(conn, season_id, 0, [{
            "headline_id": "classwire_x",
            "category": "class_wire",
            "headline_text": "Aurora land star-arc prospect Marquee Kid",
            "entity_ids": ["p", "aurora"],
        }])
        payload = build_news_payload(conn)
        assert any("star-arc prospect" in item["text"] for item in payload["items"])
