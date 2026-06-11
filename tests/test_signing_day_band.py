"""V16 Task 1 — Signing Day payload truth.

The offseason picker must expose the SCOUTED public band for prospects, never
``true_overall()`` (not as a field, not via fit_score, not via sort order).
Free agents are league veterans with public history: their true OVR stays.

These tests also pin the deeper honesty fix: the generated public band must
not be symmetric around the hidden true overall, because a symmetric band's
midpoint IS the truth and scouting would remain strategically void.
"""

import json
import sqlite3

from fastapi.testclient import TestClient

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.career_state import CareerState, CareerStateCursor
from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
from dodgeball_sim.offseason_ceremony import (
    available_recruitment_choices,
    finalize_season,
    initialize_manager_offseason,
)
from dodgeball_sim.offseason_presentation import load_active_beats
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_all_rosters,
    load_clubs,
    load_command_history_all_seasons,
    load_prospect_pool,
    load_season,
    save_career_state_cursor,
    save_prospect_pool,
    set_state,
)
from dodgeball_sim.recruiting_actions import narrow_band
from dodgeball_sim.recruiting_office import _credibility_score
from dodgeball_sim.recruitment import generate_prospect_pool
from dodgeball_sim.rng import DeterministicRNG
from dodgeball_sim.scouting_center import Prospect
from dodgeball_sim.server import app, get_db

ROOT_SEED = 20260426

PROSPECT_CHOICE_KEYS = {
    "prospect_id",
    "name",
    "age",
    "hometown",
    "archetype",
    "kind",
    "pipeline_tier",
    "public_ovr_band",
    "scouted",
    "contacted",
    "visited",
    "interest",
    "fit_score",
    # Codex issue 13: flags a target carrying one of the MANAGER'S OWN open
    # promises (Signing Day "Promise at stake" badge). Player-side state —
    # discloses nothing about the prospect's hidden ratings.
    "promised",
}
FREE_AGENT_CHOICE_KEYS = {
    "prospect_id",
    "name",
    "overall",
    "age",
    "hometown",
    "archetype",
    "kind",
}


def _fresh_career_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(conn, "aurora", root_seed=ROOT_SEED)
    return conn


def _mid(band) -> float:
    return (band[0] + band[1]) / 2.0


def test_band_generation_is_not_centered_on_truth():
    pool = generate_prospect_pool(1, DeterministicRNG(123), DEFAULT_SCOUTING_CONFIG)
    assert pool
    off_center = [p for p in pool if _mid(p.public_ratings_band["ovr"]) != p.true_overall()]
    # With a jittered band center virtually every prospect is off-center; a
    # symmetric implementation puts the truth at the midpoint for everyone.
    assert len(off_center) >= int(len(pool) * 0.6)
    half_width = DEFAULT_SCOUTING_CONFIG.public_baseline_band_half_width
    for prospect in pool:
        low, high = prospect.public_ratings_band["ovr"]
        assert 0 <= low < high <= 100
        assert high - low == 2 * half_width


def test_prospect_choices_emit_band_and_scout_state_not_true_overall():
    conn = _fresh_career_conn()
    # Run the real offseason init so free agents exist — a fresh career has
    # zero FAs and the free-agent assertions below would be vacuous.
    _enter_recruitment_state(conn)
    choices = available_recruitment_choices(conn, 1)
    prospects = [c for c in choices if c["kind"] == "prospect"]
    free_agents = [c for c in choices if c["kind"] == "free_agent"]
    assert prospects
    assert free_agents, "fixture must exercise the free-agent payload shape"

    pool = {p.player_id: p for p in load_prospect_pool(conn, class_year=1)}
    season_id = get_state(conn, "active_season_id")
    credibility = _credibility_score(
        conn, season_id, "aurora", load_command_history_all_seasons(conn)
    )

    for choice in prospects:
        assert set(choice.keys()) == PROSPECT_CHOICE_KEYS
        prospect = pool[choice["prospect_id"]]
        expected_band = list(narrow_band(prospect.public_ratings_band["ovr"], scouted=False))
        assert choice["public_ovr_band"] == expected_band
        assert choice["scouted"] is False
        assert choice["fit_score"] == round(
            _mid(expected_band) + credibility * 0.12
        )

    for choice in free_agents:
        assert set(choice.keys()) == FREE_AGENT_CHOICE_KEYS
        assert isinstance(choice["overall"], int)


def test_scouted_prospect_band_narrows_in_picker():
    conn = _fresh_career_conn()
    pool = load_prospect_pool(conn, class_year=1)
    target = pool[0]
    set_state(
        conn,
        "prospect_recruitment_actions_json",
        json.dumps({target.player_id: {"scouted": True, "interest": 64}}),
    )
    conn.commit()

    choices = available_recruitment_choices(conn, 1)
    choice = next(c for c in choices if c["prospect_id"] == target.player_id)
    base = target.public_ratings_band["ovr"]
    assert choice["public_ovr_band"] == list(narrow_band(base, scouted=True))
    assert choice["scouted"] is True
    assert choice["interest"] == 64
    width = choice["public_ovr_band"][1] - choice["public_ovr_band"][0]
    assert width < base[1] - base[0]

    # Two-surface agreement (the WT-2/3 lesson): the in-season recruit board
    # and the offseason picker must show the SAME band for the same prospect
    # and scout state.
    from dodgeball_sim.recruiting_office import build_recruiting_state

    board = build_recruiting_state(
        conn,
        season_id=get_state(conn, "active_season_id"),
        player_club_id="aurora",
        root_seed=ROOT_SEED,
        history=[],
    )
    board_row = next(
        r for r in board["prospects"] if r["player_id"] == target.player_id
    )
    assert board_row["public_ovr_band"] == choice["public_ovr_band"]


def _seed_gem_and_hype(conn: sqlite3.Connection) -> None:
    """Replace the class pool with two prospects whose truth order and public
    order DISAGREE: "Hidden Gem" (true 72, band mid 60) vs "Hype Train"
    (true 60, band mid 66)."""
    gem = Prospect(
        player_id="prospect_1_900",
        class_year=1,
        name="Hidden Gem",
        age=18,
        hometown="Quietville",
        hidden_ratings={k: 72 for k in (
            "accuracy", "power", "dodge", "catch", "stamina",
            "tactical_iq", "catch_courage", "throw_selection_iq", "conditioning_curve",
        )},
        hidden_trajectory="NORMAL",
        hidden_traits=[],
        public_archetype_guess="Sharpshooter",
        public_ratings_band={"ovr": (35, 85)},
        pipeline_tier=3,
    )
    overrated = Prospect(
        player_id="prospect_1_901",
        class_year=1,
        name="Hype Train",
        age=18,
        hometown="Loudtown",
        hidden_ratings={k: 60 for k in gem.hidden_ratings},
        hidden_trajectory="NORMAL",
        hidden_traits=[],
        public_archetype_guess="Iron Anchor",
        public_ratings_band={"ovr": (41, 91)},
        pipeline_tier=3,
    )
    conn.execute("DELETE FROM prospect_pool WHERE class_year = 1")
    save_prospect_pool(conn, [gem, overrated])
    conn.commit()


def test_prospect_ordering_uses_public_band_not_truth():
    conn = _fresh_career_conn()
    _seed_gem_and_hype(conn)

    choices = available_recruitment_choices(conn, 1)
    prospect_order = [c["prospect_id"] for c in choices if c["kind"] == "prospect"]
    # Public-estimate order: Hype Train (mid 66) before Hidden Gem (mid 60),
    # even though the hidden truth says the opposite.
    assert prospect_order == ["prospect_1_901", "prospect_1_900"]

    # Behavioral pin: auto-pick ("Sign Best Available") must follow the same
    # public order — a truth-ordered sign_best_rookie would silently re-leak
    # the hidden overall through behavior.
    from dodgeball_sim.offseason_ceremony import sign_best_rookie

    signed = sign_best_rookie(conn, "aurora", 1)
    assert signed is not None
    assert signed.id == "prospect_1_901", (
        "auto-pick signed the hidden gem — best-available is leaking "
        "true_overall through behavior"
    )


def test_service_auto_pick_follows_public_order(monkeypatch):
    # The shipping auto-pick (POST /api/offseason/recruit with prospect_id
    # null) must sign the best prospect BY PUBLIC ESTIMATE. Rival bids are
    # disabled so the pin is about ordering, not contested-round odds.
    from dodgeball_sim import recruitment
    from dodgeball_sim.offseason_service import recruit_offseason_payload

    conn = _fresh_career_conn()
    _enter_recruitment_state(conn)
    _seed_gem_and_hype(conn)
    monkeypatch.setattr(
        recruitment, "_eligible_ai_offer_clubs", lambda *args, **kwargs: set()
    )

    payload = recruit_offseason_payload(conn, None)
    assert payload["signed_player"] is not None
    assert payload["signed_player"]["id"] == "prospect_1_901", (
        "service auto-pick signed the hidden gem — the public-estimate "
        "ordering contract is broken at the service layer"
    )


def _enter_recruitment_state(conn: sqlite3.Connection) -> None:
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    finalize_season(conn, season, rosters)
    initialize_manager_offseason(conn, season, clubs, rosters, root_seed=ROOT_SEED)
    recruitment_index = load_active_beats(conn).index("recruitment")
    save_career_state_cursor(
        conn,
        CareerStateCursor(
            state=CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
            season_number=1,
            week=0,
            offseason_beat_index=recruitment_index,
        ),
    )
    conn.commit()


def test_recruit_beat_http_payload_has_no_true_overall_for_prospects():
    # Serialization-layer pin (the WT-2/3 lesson): assert on the wire JSON the
    # SPA receives, not on the builder dict.
    conn = _fresh_career_conn()
    _enter_recruitment_state(conn)
    pool = {p.player_id: p for p in load_prospect_pool(conn, class_year=1)}

    def override_db():
        yield conn

    app.dependency_overrides[get_db] = override_db
    try:
        response = TestClient(app).get("/api/offseason/beat")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()["payload"]
    prospects = [c for c in payload["available_prospects"] if c["kind"] == "prospect"]
    assert prospects

    for choice in prospects:
        assert set(choice.keys()) == PROSPECT_CHOICE_KEYS

    # The band must not encode the truth: with a jittered center, the midpoint
    # diverges from true_overall for the pool at large (a symmetric band would
    # match it for everyone).
    off_center = [
        c
        for c in prospects
        if _mid(c["public_ovr_band"]) != pool[c["prospect_id"]].true_overall()
    ]
    assert len(off_center) >= int(len(prospects) * 0.6)

    mids = [_mid(c["public_ovr_band"]) for c in prospects]
    assert mids == sorted(mids, reverse=True)
    truths = [pool[c["prospect_id"]].true_overall() for c in prospects]
    assert truths != sorted(truths, reverse=True), (
        "picker ordering still follows hidden true OVR exactly — with a "
        "jittered public band the public order must diverge from truth order"
    )
