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


# --- Cross-offseason credibility-bonus reset (one-season, not forever) --------
#
# The credibility bonus is a ONE-offseason effect: this offseason's recruiting
# reads it; the next offseason's must not. Because a media event only fires
# ~55% of offseasons, apply_media_choice (the only writer) does not run in a
# no-event offseason, so without an explicit reset a stale bonus persists and
# keeps inflating the recruiting credibility score forever. These pin the fix.

def _next_season(conn, root_seed=_SEED):
    from dodgeball_sim.offseason_ceremony import create_next_manager_season
    from dodgeball_sim.persistence import load_clubs

    clubs = load_clubs(conn)
    return create_next_manager_season(clubs, root_seed, season_number=2, year=2)


def _run_next_offseason_init(conn):
    from dodgeball_sim.offseason_ceremony import initialize_manager_offseason
    from dodgeball_sim.persistence import load_all_rosters, load_clubs

    season2 = _next_season(conn)
    initialize_manager_offseason(
        conn, season2, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
    )
    return season2


def test_stale_bonus_cleared_when_next_offseason_has_no_media_event():
    """Case 1 (leak fix): a +C media bonus from offseason N must NOT persist
    into offseason N+1's recruiting when N+1 fires no media event. Before the
    fix the bonus was never reset, so a single +6 inflated credibility forever.
    """
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("local_feature"))
    me.set_media_choice(conn, "recruits")  # +6 credibility
    me.apply_media_choice(conn, season_id)
    assert me.media_credibility_bonus(conn) == 6  # offseason N: recruiting sees +6

    # Advance to offseason N+1. No apply_media_choice runs here (the user has
    # not advanced past the beat), so the stale bonus must already be gone.
    _run_next_offseason_init(conn)
    assert me.media_credibility_bonus(conn) == 0


def test_same_offseason_recruiting_still_reads_bonus_after_apply():
    """Case 2 (same-offseason consumption preserved): within offseason N, after
    the +C choice commits, this offseason's recruiting reads +C. The N+1 reset
    must not wipe the bonus before N's recruiting consumes it.
    """
    from dodgeball_sim.recruiting_office import _credibility

    conn, season_id = _career()
    base = _credibility(conn, season_id, "aurora", [])["score"]
    me.cache_media_event(conn, _event_by_id("local_feature"))
    me.set_media_choice(conn, "recruits")  # +6
    me.apply_media_choice(conn, season_id)
    after = _credibility(conn, season_id, "aurora", [])["score"]
    assert after - base == 6  # same offseason still consumes the +6


def test_next_offseason_media_event_replaces_not_adds():
    """Case 3 (refresh): N+1 fires a media event with a +D choice. Recruiting
    in N+1 sees exactly +D, not the stale +C plus +D.
    """
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("local_feature"))
    me.set_media_choice(conn, "recruits")  # +6
    me.apply_media_choice(conn, season_id)
    assert me.media_credibility_bonus(conn) == 6

    season2 = _run_next_offseason_init(conn)
    # N+1 fires a different event with a +2 credibility option ("classy").
    me.cache_media_event(conn, _event_by_id("controversy"))
    me.set_media_choice(conn, "classy")  # +2 credibility
    me.apply_media_choice(conn, season2.season_id)
    assert me.media_credibility_bonus(conn) == 2  # not 6 + 2


def test_zero_credibility_choice_clears_stale_bonus():
    """Case 4 (zero choice clears): N+1 fires and the user commits a 0-cred
    option. Recruiting sees 0 (no residual from N).
    """
    conn, season_id = _career()
    me.cache_media_event(conn, _event_by_id("local_feature"))
    me.set_media_choice(conn, "recruits")  # +6
    me.apply_media_choice(conn, season_id)
    assert me.media_credibility_bonus(conn) == 6

    season2 = _run_next_offseason_init(conn)
    me.cache_media_event(conn, _event_by_id("star_interview"))
    me.set_media_choice(conn, "embrace")  # +400 fans, 0 credibility
    me.apply_media_choice(conn, season2.season_id)
    assert me.media_credibility_bonus(conn) == 0


def test_legacy_world_never_touches_credibility_bonus_key():
    """Case 5 (legacy byte-identical): in a non-pyramid world the credibility
    bonus key is never touched by initialize_manager_offseason — the reset is
    gated inside the player_club_id + pyramid_world_active block.
    """
    from dodgeball_sim.career_setup import initialize_curated_manager_career
    from dodgeball_sim.persistence import (
        create_schema,
        get_state,
        load_all_rosters,
        load_clubs,
        load_season,
        set_state,
    )
    from dodgeball_sim.offseason_ceremony import initialize_manager_offseason

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    # No world="pyramid" -> legacy single-league world.
    initialize_curated_manager_career(conn, "aurora", _SEED, ruleset_selection="official_foam")
    # Plant a stale value as if some path had written it.
    set_state(conn, "v26_credibility_bonus", "99")
    conn.commit()

    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    initialize_manager_offseason(
        conn, season, load_clubs(conn), load_all_rosters(conn), root_seed=_SEED
    )
    # Legacy: the key is unchanged — the reset is gated inside pyramid_world_active.
    assert get_state(conn, "v26_credibility_bonus") == "99"
