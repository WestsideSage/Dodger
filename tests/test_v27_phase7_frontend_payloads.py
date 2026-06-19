"""V27 The Calendar — Phase 7: frontend payload guards (the strip-trap regression).

The offseason beat endpoints (``/api/offseason/beat`` etc.) return raw dicts with
NO ``response_model=`` declared, so FastAPI does not strip undeclared keys — the
``events`` + ``worlds_champion`` payloads pass through verbatim today. But that
is a structural property, not a guarantee: a future developer adding a
``response_model=`` (the historical WT-12 ``MatchReplayResponse`` bug) would
silently strip the new payload keys and the frontend would render empty beats.

These guards drive the REAL FastAPI ``TestClient`` against a pyramid career with
both new beats active and assert the response JSON carries every payload field
end-to-end — the regression that would fire if the strip trap ever closes.
"""
from __future__ import annotations

import json
import sqlite3
import dataclasses

from fastapi.testclient import TestClient

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.economy import set_treasury_k
from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
from dodgeball_sim.offseason_presentation import load_active_beats
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_season,
    save_career_state_cursor,
    set_state,
)
from dodgeball_sim.server import app, get_db

_SEED = 20260618


def _pyramid_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _write_worlds_ledger(conn, season_id, *, champion_club_id="aurora"):
    from dodgeball_sim.pyramid_postseason import postseason_ledger_key

    ledger = {
        "season_id": season_id,
        "complete": True,
        "champions": {},
        "runners_up": {},
        "champion_names": {},
        "promotion_playoff": {},
        "promoted": {},
        "relegated": {},
        "worlds": {
            "champion_club_id": champion_club_id,
            "champion_name": "Aurora Sentinels",
            "runner_up_club_id": "rival",
            "runner_up_name": "Rival",
            "final_match_id": f"{season_id}_p_worlds_final",
        },
    }
    set_state(conn, postseason_ledger_key(season_id), json.dumps(ledger))
    conn.commit()


def _init_offseason(conn, season_id):
    season = load_season(conn, season_id)
    initialize_manager_offseason(
        conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
    )
    conn.commit()


def _position_cursor_on_beat(conn, beat_key):
    """Move the career cursor onto the named offseason beat so the beat endpoint
    renders it, mirroring a player who advanced to that beat."""
    active = load_active_beats(conn)
    assert beat_key in active, f"{beat_key} not active; active={active}"
    idx = active.index(beat_key)
    cursor = load_career_state_cursor(conn)
    cursor = dataclasses.replace(
        cursor,
        state=CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
        offseason_beat_index=idx,
        week=0,
    )
    save_career_state_cursor(conn, cursor)
    conn.commit()


def _client_for(conn):
    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


class TestEventsBeatPayloadEndToEnd:
    """The `events` beat payload survives the full API response un-stripped."""

    def test_events_payload_carries_all_fields_through_the_api(self):
        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id)  # also activates worlds_champion
        # No pre-recorded event: the real initialize_manager_offseason resolves
        # the cup (and invitationals/MSI/Founders) — this is the true end-to-end
        # path the frontend hits.
        _init_offseason(conn, season_id)
        _position_cursor_on_beat(conn, "events")

        client = _client_for(conn)
        try:
            res = client.get("/api/offseason/beat")
            assert res.status_code == 200, res.text
            data = res.json()
            # The top-level discriminant + payload wrapper survive.
            assert data["key"] == "events"
            assert isinstance(data["payload"], dict)
            payload = data["payload"]
            # The strip trap would drop these.
            assert payload["beat_key"] == "events"
            assert isinstance(payload["events"], list)
            assert len(payload["events"]) >= 1
            # The real offseason resolution (cup + invitationals + MSI/Founders)
            # produces the event set; find the Domestic Cup among them.
            cup = next(
                (e for e in payload["events"] if e["event_key"] == "domestic_cup"),
                None,
            )
            assert cup is not None, "domestic_cup event missing from payload"
            event = cup
            # Every field the frontend EventResultRow type reads.
            for key in (
                "event_key",
                "event_name",
                "season_id",
                "champion_club_id",
                "champion_club_name",
                "ruleset",
                "purse_k",
                "bracket",
                "meta",
            ):
                assert key in event, f"event payload missing {key!r} (strip trap?)"
            assert event["event_key"] == "domestic_cup"
            assert event["ruleset"] == "official_foam"
            assert isinstance(event["bracket"], list) and event["bracket"]
            # The bracket rows carry the EventBracketRow fields the FE renders.
            row = event["bracket"][0]
            for key in (
                "round",
                "home_club_id",
                "away_club_id",
                "winner_club_id",
                "home_club_name",
                "away_club_name",
            ):
                assert key in row, f"bracket row missing {key!r} (strip trap?)"
            assert row["winner_club_id"]
            # meta is additive (giant_killings is optional); it must survive.
            assert isinstance(event["meta"], dict)
        finally:
            app.dependency_overrides.clear()


class TestWorldsChampionBeatPayloadEndToEnd:
    """The `worlds_champion` crowning payload survives the full API response."""

    def test_first_crown_payload_carries_is_first_through_the_api(self):
        conn, season_id = _pyramid_career()
        _write_worlds_ledger(conn, season_id, champion_club_id="aurora")
        _init_offseason(conn, season_id)
        _position_cursor_on_beat(conn, "worlds_champion")

        client = _client_for(conn)
        try:
            res = client.get("/api/offseason/beat")
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["key"] == "worlds_champion"
            payload = data["payload"]
            # The strip trap would drop these four keys.
            assert payload["beat_key"] == "worlds_champion"
            assert payload["champion_club_id"] == "aurora"
            assert payload["champion_name"] == "Aurora Sentinels"
            assert payload["season_id"] == season_id
            assert payload["is_first"] is True
            # The vision law: no post-summit ratchet field leaks into the payload.
            assert "ratchet" not in payload
            assert "ng_plus" not in payload
            assert "next_season_seed" not in payload
        finally:
            app.dependency_overrides.clear()
