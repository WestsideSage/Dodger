"""V26 The Crowd — Phase 6: media mini-events (effects isolated to fans/prestige/credibility)."""
import sqlite3

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.economy import set_treasury_k, treasury_k
from dodgeball_sim.persistence import create_schema, get_state, load_club_prestige
from dodgeball_sim import media_events as me
from dodgeball_sim import fan_ledger as fl

_SEED = 20260617


def _career():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    set_treasury_k(conn, 500)
    conn.commit()
    return conn, get_state(conn, "active_season_id")


def _event_by_id(event_id):
    return next(e for e in me._CATALOG if e.event_id == event_id)


def test_select_media_event_is_deterministic():
    conn, season_id = _career()
    a = me.select_media_event(conn, season_id, _SEED)
    b = me.select_media_event(conn, season_id, _SEED)
    assert (a is None and b is None) or (a is not None and a.event_id == b.event_id)


def test_prestige_choice_changes_only_prestige_not_treasury_or_fans():
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("local_feature"))
    me.set_media_choice(conn, "prestige")  # +4 prestige only
    treasury_before = treasury_k(conn)
    prestige_before = load_club_prestige(conn, "aurora")
    fans_before = fl.club_fans(conn, "aurora")

    me.apply_media_choice(conn, season_id)

    assert load_club_prestige(conn, "aurora") == prestige_before + 4
    assert treasury_k(conn) == treasury_before          # ISOLATION: treasury untouched
    assert fl.club_fans(conn, "aurora") == fans_before   # ISOLATION: no fans for this choice


def test_fans_choice_grows_fans_with_a_receipt():
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("local_feature"))
    me.set_media_choice(conn, "fans")  # +300 fans
    me.apply_media_choice(conn, season_id)
    assert fl.club_fans(conn, "aurora") == 300
    receipts = fl.load_fan_receipts(conn, entity_type="club", entity_id="aurora")
    assert any("media" in r["event_type"] for r in receipts)


def test_recruits_choice_grants_a_credibility_bonus():
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("local_feature"))
    me.set_media_choice(conn, "recruits")  # +6 credibility
    me.apply_media_choice(conn, season_id)
    assert me.media_credibility_bonus(conn) == 6


def test_apply_is_idempotent():
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("controversy"))
    me.set_media_choice(conn, "fire_back")  # +350 fans
    first = me.apply_media_choice(conn, season_id)
    fans_after = fl.club_fans(conn, "aurora")
    second = me.apply_media_choice(conn, season_id)
    assert first == second
    assert fl.club_fans(conn, "aurora") == fans_after  # no double-apply


def test_default_choice_is_first_option_when_none_chosen():
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("star_interview"))
    # No set_media_choice — auto-pilot advances and commits the default.
    result = me.apply_media_choice(conn, season_id)
    assert result["chosen"] == "embrace"  # the first option


def test_beat_index_clamp_matches_the_new_tuple():
    from dodgeball_sim.offseason_ceremony import OFFSEASON_CEREMONY_BEATS
    from dodgeball_sim.persistence import _MAX_OFFSEASON_BEAT_INDEX

    assert "media_event" in OFFSEASON_CEREMONY_BEATS
    assert _MAX_OFFSEASON_BEAT_INDEX == len(OFFSEASON_CEREMONY_BEATS) - 1
