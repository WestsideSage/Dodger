"""V27 The Calendar â€” Phase 1: event foundation.

Per docs/specs/2026-06-17-v27-the-calendar-spec.md (Phase 1): the event-result
model + an idempotent ``apply_event_purse`` (the FINANCES_APPLIED_KEY guard
pattern â€” ``set_treasury_k`` has no guard of its own) + a per-season
``v27_events_json`` store + an ``emit_event_news`` helper, plus a widened news
filter and a conditional ``events`` offseason beat scaffold. Pyramid-gated;
legacy single-league saves stay byte-identical.
"""
from __future__ import annotations

import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_EVENTS, EventConfig
from dodgeball_sim.economy import set_treasury_k, treasury_k
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_news_headlines,
    save_news_headlines,
)

_SEED = 20260617


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


def _legacy_career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


# ---------------------------------------------------------------------------
# Task 1.1 â€” EventConfig + events.py (idempotent purse + per-season store)
# ---------------------------------------------------------------------------


class TestEventConfig:
    def test_default_events_config_has_required_knobs(self):
        cfg: EventConfig = DEFAULT_EVENTS
        # Founders' invite count is a small top-N by fan count (spec table: 4-6).
        assert 4 <= cfg.founders_invite_count <= 6
        # Invitational fame threshold gates cloth/no-sting invites by prestige.
        assert cfg.invitational_fame_min > 0
        # Prospect-showcase warmth is a one-season credibility bump (>=0).
        assert cfg.warmth_credibility >= 0
        # Purses are tier-scaled (a mapping keyed by tier 1/2/3) for the cup.
        assert set(cfg.cup_purse_champion_k.keys()) == {1, 2, 3}

    def test_cup_purses_are_a_margin_not_league_rival(self):
        cfg = DEFAULT_EVENTS
        # The cup purse must stay a MODEST margin relative to league payout â€”
        # never dwarf the V22 economy. The D3 champion payout base+step is 240k;
        # a cup champion purse well under that keeps the squeeze invariant.
        for tier, purse in cfg.cup_purse_champion_k.items():
            assert 0 < purse <= 200, f"tier {tier} cup purse {purse} too rich"


class TestApplyEventPurse:
    def test_credits_treasury_once_and_is_idempotent(self):
        from dodgeball_sim.event_calendar import apply_event_purse

        conn, season_id = _pyramid_career()
        before = treasury_k(conn)
        first = apply_event_purse(conn, "domestic_cup", purse_k=80, season_id=season_id)
        assert treasury_k(conn) == before + 80
        assert first is not None
        # A second call must NOT double-pay â€” the per-event guard keys on season_id.
        second = apply_event_purse(conn, "domestic_cup", purse_k=80, season_id=season_id)
        assert treasury_k(conn) == before + 80
        assert second == first  # same ledger, no re-apply

    def test_per_event_guard_is_distinct_per_event_key(self):
        """Two different events in the same season each pay once (distinct guards)."""
        from dodgeball_sim.event_calendar import apply_event_purse

        conn, season_id = _pyramid_career()
        before = treasury_k(conn)
        apply_event_purse(conn, "domestic_cup", purse_k=80, season_id=season_id)
        apply_event_purse(conn, "cloth_classic", purse_k=40, season_id=season_id)
        assert treasury_k(conn) == before + 120

    def test_guard_key_namespaced_per_event(self):
        from dodgeball_sim.event_calendar import apply_event_purse

        conn, season_id = _pyramid_career()
        apply_event_purse(conn, "domestic_cup", purse_k=80, season_id=season_id)
        # The guard must be the per-event namespaced key, never finances_applied_for.
        assert get_state(conn, "v27_domestic_cup_purse_for") == season_id
        assert get_state(conn, "finances_applied_for") is None


class TestEventStoreRoundTrip:
    def test_record_event_and_load_events_round_trip(self):
        from dodgeball_sim.event_calendar import EventBracketRow, EventResult, load_events, record_event

        conn, season_id = _pyramid_career()
        result = EventResult(
            event_key="domestic_cup",
            event_name="Domestic Cup",
            season_id=season_id,
            champion_club_id="aurora",
            champion_club_name="Aurora Sentinels",
            ruleset="official_foam",
            purse_k=80,
            bracket=(
                EventBracketRow(round="Final", home_club_id="aurora", away_club_id="lunar",
                                winner_club_id="aurora", home_club_name="Aurora Sentinels",
                                away_club_name="Lunar Eclipse"),
            ),
        )
        record_event(conn, season_id, result)
        loaded = load_events(conn, season_id)
        assert len(loaded) == 1
        assert loaded[0]["event_key"] == "domestic_cup"
        assert loaded[0]["champion_club_id"] == "aurora"
        assert loaded[0]["purse_k"] == 80
        assert loaded[0]["bracket"][0]["winner_club_id"] == "aurora"

    def test_load_events_empty_when_none_recorded(self):
        from dodgeball_sim.event_calendar import load_events

        conn, season_id = _pyramid_career()
        assert load_events(conn, season_id) == []

    def test_record_event_appends_not_overwrites(self):
        from dodgeball_sim.event_calendar import EventResult, load_events, record_event

        conn, season_id = _pyramid_career()
        for key in ("domestic_cup", "cloth_classic"):
            record_event(conn, season_id, EventResult(
                event_key=key, event_name=key, season_id=season_id,
                champion_club_id="aurora", champion_club_name="Aurora Sentinels",
                ruleset="official_foam", purse_k=10, bracket=(),
            ))
        loaded = load_events(conn, season_id)
        assert {e["event_key"] for e in loaded} == {"domestic_cup", "cloth_classic"}


class TestEmitEventNews:
    def test_emits_an_event_news_headline(self):
        from dodgeball_sim.event_calendar import EventResult, emit_event_news

        conn, season_id = _pyramid_career()
        result = EventResult(
            event_key="domestic_cup", event_name="Domestic Cup", season_id=season_id,
            champion_club_id="aurora", champion_club_name="Aurora Sentinels",
            ruleset="official_foam", purse_k=80, bracket=(),
        )
        emit_event_news(conn, season_id, result)
        wire = [h for h in load_news_headlines(conn, season_id)
                if h["category"] == "event_news"]
        assert wire, "emit_event_news must write an event_news headline"
        assert "Aurora Sentinels" in wire[0]["headline_text"]

    def test_emit_event_news_is_idempotent(self):
        from dodgeball_sim.event_calendar import EventResult, emit_event_news

        conn, season_id = _pyramid_career()
        result = EventResult(
            event_key="domestic_cup", event_name="Domestic Cup", season_id=season_id,
            champion_club_id="aurora", champion_club_name="Aurora Sentinels",
            ruleset="official_foam", purse_k=80, bracket=(),
        )
        emit_event_news(conn, season_id, result)
        emit_event_news(conn, season_id, result)
        wire = [h for h in load_news_headlines(conn, season_id)
                if h["category"] == "event_news"]
        assert len(wire) == 1


# ---------------------------------------------------------------------------
# Task 1.2 — widen the news filter (event_news surfaces in the wire)
# ---------------------------------------------------------------------------


class TestNewsPayloadSurfacesEventNews:
    def test_event_news_appears_in_news_payload(self):
        from dodgeball_sim.web_status_service import build_news_payload

        conn, season_id = _pyramid_career()
        save_news_headlines(conn, season_id, 0, [{
            "headline_id": "event_domestic_cup_s1",
            "category": "event_news",
            "headline_text": "Aurora Sentinels lift the Domestic Cup",
            "entity_ids": ["aurora"],
        }])
        payload = build_news_payload(conn)
        assert any("Domestic Cup" in item["text"] for item in payload["items"])

    def test_class_wire_still_surfaces_after_widening(self):
        from dodgeball_sim.web_status_service import build_news_payload

        conn, season_id = _pyramid_career()
        save_news_headlines(conn, season_id, 0, [{
            "headline_id": "classwire_still_here",
            "category": "class_wire",
            "headline_text": "Aurora land star-arc prospect Marquee Kid",
            "entity_ids": ["p", "aurora"],
        }])
        payload = build_news_payload(conn)
        assert any("star-arc prospect" in item["text"] for item in payload["items"])


# ---------------------------------------------------------------------------
# Task 1.3 — the conditional `events` offseason beat scaffold
# ---------------------------------------------------------------------------


class TestEventsBeatClampAndTuple:
    def test_max_offseason_beat_index_equals_len_beats_minus_one(self):
        from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS
        from dodgeball_sim.persistence import _MAX_OFFSEASON_BEAT_INDEX

        assert "events" in OFFSEASON_CEREMONY_BEATS
        assert _MAX_OFFSEASON_BEAT_INDEX == len(OFFSEASON_CEREMONY_BEATS) - 1

    def test_events_beat_sits_after_recap_area(self):
        from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS

        beats = OFFSEASON_CEREMONY_BEATS
        # "After the recap area" — recap/champion/awards are the season-summary
        # honors block; events (the season's competitions) follow it.
        assert beats.index("events") > beats.index("awards")
        assert beats.index("events") < beats.index("records_ratified")

    def test_pinned_beat_tuple_witness_matches(self):
        from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS

        assert OFFSEASON_CEREMONY_BEATS == (
            "recap",
            "champion",
            "awards",
            "events",
            "records_ratified",
            "hof_induction",
            "development",
            "retirements",
            "transfer_period",
            "rookie_class_preview",
            "media_event",
            "recruitment",
            "schedule_reveal",
        )


class TestEventsBeatPresence:
    def test_beat_present_when_an_event_is_recorded_on_pyramid_world(self):
        from dodgeball_sim.event_calendar import EventResult, record_event
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import load_all_rosters, load_clubs, load_season

        conn, season_id = _pyramid_career()
        record_event(conn, season_id, EventResult(
            event_key="domestic_cup", event_name="Domestic Cup", season_id=season_id,
            champion_club_id="aurora", champion_club_name="Aurora Sentinels",
            ruleset="official_foam", purse_k=80, bracket=(),
        ))
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        from dodgeball_sim.persistence import get_state as _gs
        import json as _json
        active = _json.loads(_gs(conn, "offseason_active_beats_json") or "[]")
        assert "events" in active

    def test_beat_absent_when_no_events_recorded(self):
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import get_state, load_all_rosters, load_clubs, load_season
        import json

        conn, season_id = _pyramid_career()
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        active = json.loads(get_state(conn, "offseason_active_beats_json") or "[]")
        assert "events" not in active

    def test_beat_absent_on_legacy_world_even_if_event_somehow_recorded(self):
        """Legacy byte-identical: the events beat never appears on a non-pyramid
        world, and offseason init never touches the v27_events_json store."""
        from dodgeball_sim.event_calendar import EventResult, record_event
        from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
        from dodgeball_sim.persistence import get_state, load_all_rosters, load_clubs, load_season
        import json

        conn, season_id = _legacy_career()
        record_event(conn, season_id, EventResult(
            event_key="domestic_cup", event_name="Domestic Cup", season_id=season_id,
            champion_club_id="aurora", champion_club_name="Aurora Sentinels",
            ruleset="official_foam", purse_k=80, bracket=(),
        ))
        store_before = get_state(conn, "v27_events_json")
        season = load_season(conn, season_id)
        initialize_manager_offseason(
            conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
        )
        active = json.loads(get_state(conn, "offseason_active_beats_json") or "[]")
        assert "events" not in active
        # Offseason init must not rewrite/clear the events store on a legacy world.
        assert get_state(conn, "v27_events_json") == store_before


class TestEventsBeatPayload:
    def test_build_offseason_ceremony_beat_renders_events_beat(self):
        from dodgeball_sim.offseason_ceremony import (
            OFFSEASON_CEREMONY_BEATS,
            build_offseason_ceremony_beat,
        )
        from dodgeball_sim.persistence import load_all_rosters, load_clubs
        from dodgeball_sim.event_calendar import EventResult, record_event

        conn, season_id = _pyramid_career()
        record_event(conn, season_id, EventResult(
            event_key="domestic_cup", event_name="Domestic Cup", season_id=season_id,
            champion_club_id="aurora", champion_club_name="Aurora Sentinels",
            ruleset="official_foam", purse_k=80, bracket=(),
        ))
        beat = build_offseason_ceremony_beat(
            OFFSEASON_CEREMONY_BEATS.index("events"),
            None, load_clubs(conn), load_all_rosters(conn), [], [], "aurora",
            conn=conn,
        )
        assert beat.key == "events"
        assert "Domestic Cup" in beat.body
        assert "Aurora Sentinels" in beat.body

    def test_build_beat_payload_events_branch_returns_event_list(self):
        from dodgeball_sim.offseason_presentation import build_beat_payload
        from dodgeball_sim.persistence import load_all_rosters, load_clubs
        from dodgeball_sim.event_calendar import EventResult, record_event

        conn, season_id = _pyramid_career()
        record_event(conn, season_id, EventResult(
            event_key="domestic_cup", event_name="Domestic Cup", season_id=season_id,
            champion_club_id="aurora", champion_club_name="Aurora Sentinels",
            ruleset="official_foam", purse_k=80, bracket=(),
        ))
        payload = build_beat_payload(
            "events",
            awards=[], clubs=load_clubs(conn), rosters=load_all_rosters(conn),
            standings=[], ret_rows=[], season=None, season_outcome=None,
            next_preview=None, signed_player_id="", player_club_id="aurora",
            conn=conn,
        )
        assert payload["beat_key"] == "events"
        assert len(payload["events"]) == 1
        assert payload["events"][0]["event_key"] == "domestic_cup"
