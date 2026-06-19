"""V28 The Weather — Phase 4: frontend payload guards (the strip-trap regression).

The two new V28 frontend surfaces ride existing endpoints:

* the league news wire (``wire_headlines``: class/event/meta/league_bulletin
  headlines) rides ``/api/standings`` (``StandingsResponse`` — a STRICT model, so
  ``wire_headlines`` is declared or FastAPI strips it);
* the preseason officiating bulletin (``officiating_emphasis``) rides inside the
  free-form ``season_preview`` dict on ``/api/command-center``.

These guards drive the REAL FastAPI ``TestClient`` and assert both fields reach
the client un-stripped — the regression that fires if a future model change
closes the strip trap (the historical WT-12 ``MatchReplayResponse`` bug family).
"""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    save_news_headlines,
)
from dodgeball_sim.season_emphasis import generate_officiating_bulletin, select_season_emphasis
from dodgeball_sim.server import app, get_db

_SEED = 20260618


def _pyramid_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _client_for(conn):
    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


class TestNewsWirePayloadEndToEnd:
    def test_wire_headlines_survive_the_standings_api(self):
        conn, sid = _pyramid_career()
        # Seed one of each wire kind for the active season.
        save_news_headlines(conn, sid, 0, [
            {"headline_id": f"meta_probe_{sid}", "category": "meta_report",
             "headline_text": "META WIRE PROBE LINE", "entity_ids": []},
            {"headline_id": f"emphasis_{sid}", "category": "league_bulletin",
             "headline_text": "LEAGUE BULLETIN PROBE LINE", "entity_ids": []},
        ])
        conn.commit()

        client = _client_for(conn)
        try:
            res = client.get("/api/standings")
            assert res.status_code == 200, res.text
            data = res.json()
            # The strip trap (StandingsResponse is a strict model) would drop this.
            assert "wire_headlines" in data, "wire_headlines stripped by StandingsResponse"
            texts = {item["text"] for item in (data["wire_headlines"] or [])}
            assert "META WIRE PROBE LINE" in texts
            assert "LEAGUE BULLETIN PROBE LINE" in texts
            # The NewsItem shape survives intact.
            for item in data["wire_headlines"]:
                assert {"tag", "text", "match_id", "player_id"} <= set(item.keys())
        finally:
            app.dependency_overrides.clear()


class TestOfficiatingEmphasisPayloadEndToEnd:
    def test_officiating_emphasis_survives_the_command_center_api(self):
        conn, sid = _pyramid_career()
        # Seed an emphasis for the active (week-1) season so the preview surfaces
        # it. (In normal play the bulletin is announced at the prior offseason for
        # the upcoming season; here we seed the active season directly to exercise
        # the payload passthrough.)
        generate_officiating_bulletin(conn, sid, _SEED)
        emph = select_season_emphasis(conn, sid, _SEED)

        client = _client_for(conn)
        try:
            res = client.get("/api/command-center")
            assert res.status_code == 200, res.text
            data = res.json()
            preview = data.get("season_preview")
            assert preview is not None, "no season_preview at week 1"
            # officiating_emphasis rides inside the free-form season_preview dict;
            # a strict sub-model would strip it.
            assert "officiating_emphasis" in preview, "officiating_emphasis stripped"
            assert preview["officiating_emphasis"] == emph.announcement
        finally:
            app.dependency_overrides.clear()
