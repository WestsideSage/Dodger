import json
import sqlite3

from dodgeball_sim.models import Player, PlayerRatings
from dodgeball_sim.offseason_beats import (
    HallOfFameInductee,
    InductionPayload,
    RatificationPayload,
    RatifiedRecord,
    RookiePreviewPayload,
    RookieStoryline,
    build_rookie_class_preview,
    induct_hall_of_fame,
    ratify_records,
)
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_hall_of_fame,
    save_club_recruitment_profile,
    save_free_agents,
    save_hall_of_fame_entry,
    save_league_record,
    save_player_career_stats,
    save_prospect_pool,
    save_retired_player,
    set_state,
)
from dodgeball_sim.recruitment_domain import RecruitmentProfile
from dodgeball_sim.scouting_center import Prospect


def test_module_exposes_expected_dataclasses_and_functions():
    assert RatifiedRecord is not None
    assert RatificationPayload is not None
    assert HallOfFameInductee is not None
    assert InductionPayload is not None
    assert RookieStoryline is not None
    assert RookiePreviewPayload is not None
    assert callable(ratify_records)
    assert callable(induct_hall_of_fame)
    assert callable(build_rookie_class_preview)


def test_dataclass_payload_constructors_accept_minimal_inputs():
    rp = RatificationPayload(season_id="season_1", new_records=())
    assert rp.season_id == "season_1"
    assert rp.new_records == ()

    ip = InductionPayload(season_id="season_1", new_inductees=())
    assert ip.season_id == "season_1"
    assert ip.new_inductees == ()

    pp = RookiePreviewPayload(
        season_id="season_1",
        class_year=2,
        source="prospect_pool",
        class_size=0,
        archetype_distribution={},
        top_band_depth=0,
        free_agent_count=0,
        storylines=(),
    )
    assert pp.class_year == 2


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _seed_career(conn: sqlite3.Connection, player_id: str, name: str, eliminations: int, championships: int = 0):
    save_player_career_stats(
        conn,
        player_id,
        {
            "player_id": player_id,
            "player_name": name,
            "seasons_played": 5,
            "championships": championships,
            "awards_won": 0,
            "total_matches": 50,
            "total_eliminations": eliminations,
            "total_catches_made": 0,
            "total_dodges_successful": 0,
            "total_times_eliminated": 0,
            "peak_eliminations": eliminations,
            "career_eliminations": eliminations,
            "career_catches": 0,
            "career_dodges": 0,
            "clubs_served": 1,
        },
    )


def test_ratify_records_persists_new_record_once_when_no_prior_records():
    conn = _fresh_conn()
    _seed_career(conn, "p1", "Alpha", eliminations=80)
    _seed_career(conn, "p2", "Bravo", eliminations=40)

    payload = ratify_records(conn, "season_1")

    types = {record.record_type for record in payload.new_records}
    assert "career_eliminations" in types
    assert get_state(conn, "offseason_records_ratified_for") == "season_1"

    # Second call returns the same payload, doesn't re-ratify
    payload_again = ratify_records(conn, "season_1")
    assert payload_again.new_records == payload.new_records


def test_ratify_records_skips_records_that_did_not_improve():
    conn = _fresh_conn()
    _seed_career(conn, "p1", "Alpha", eliminations=80)
    save_league_record(
        conn,
        record_type="career_eliminations",
        holder_id="legacy",
        holder_type="player",
        record_value=100.0,
        set_in_season="season_0",
        record_payload={"holder_name": "Legacy", "value": 100.0, "detail": "previous"},
    )

    payload = ratify_records(conn, "season_1")

    types = {record.record_type for record in payload.new_records}
    assert "career_eliminations" not in types


def test_ratify_records_empty_payload_when_no_career_data():
    conn = _fresh_conn()

    payload = ratify_records(conn, "season_1")

    assert payload.season_id == "season_1"
    assert payload.new_records == ()
    assert get_state(conn, "offseason_records_ratified_for") == "season_1"


def test_ratify_records_payload_round_trips_through_dynasty_state():
    conn = _fresh_conn()
    _seed_career(conn, "p1", "Alpha", eliminations=80)
    ratify_records(conn, "season_1")

    raw = get_state(conn, "offseason_records_ratified_json")
    assert raw is not None
    parsed = json.loads(raw)
    assert isinstance(parsed, list)
    assert any(entry["record_type"] == "career_eliminations" for entry in parsed)


# ---------------------------------------------------------------------------
# Task 4 helpers and tests
# ---------------------------------------------------------------------------


def _hof_player(player_id: str, name: str, age: int = 35) -> Player:
    return Player(
        id=player_id,
        name=name,
        ratings=PlayerRatings(accuracy=80.0, power=80.0, dodge=80.0, catch=80.0, stamina=80.0),
        age=age,
        club_id="aurora",
        newcomer=False,
    )


def _seed_hof_candidate(conn, player_id: str, name: str, season_id: str):
    save_player_career_stats(
        conn,
        player_id,
        {
            "player_id": player_id,
            "player_name": name,
            "seasons_played": 8,
            "championships": 2,
            "awards_won": 4,
            "total_matches": 100,
            "total_eliminations": 220,
            "total_catches_made": 90,
            "total_dodges_successful": 110,
            "total_times_eliminated": 60,
            "peak_eliminations": 28,
            "career_eliminations": 220,
            "career_catches": 90,
            "career_dodges": 110,
            "clubs_served": 1,
        },
    )
    save_retired_player(conn, _hof_player(player_id, name), season_id, "age_decline")


def test_induct_hall_of_fame_inducts_qualified_retiree_once():
    conn = _fresh_conn()
    _seed_hof_candidate(conn, "p1", "Eligible Star", "season_1")
    _seed_hof_candidate(conn, "p2", "Average Joe", "season_1")
    # Overwrite p2's career stats with a weak profile (too few seasons to qualify)
    save_player_career_stats(
        conn,
        "p2",
        {
            "player_id": "p2",
            "player_name": "Average Joe",
            "seasons_played": 3,
            "championships": 0,
            "awards_won": 0,
            "total_matches": 30,
            "total_eliminations": 20,
            "total_catches_made": 5,
            "total_dodges_successful": 10,
            "total_times_eliminated": 25,
            "peak_eliminations": 9,
            "career_eliminations": 20,
            "career_catches": 5,
            "career_dodges": 10,
            "clubs_served": 1,
        },
    )

    payload = induct_hall_of_fame(conn, "season_1")
    inducted_ids = {entry.player_id for entry in payload.new_inductees}

    assert "p1" in inducted_ids
    assert "p2" not in inducted_ids
    assert len(load_hall_of_fame(conn)) == 1

    # Idempotent re-entry
    payload_again = induct_hall_of_fame(conn, "season_1")
    assert payload_again.new_inductees == payload.new_inductees
    assert len(load_hall_of_fame(conn)) == 1


def test_induct_hall_of_fame_skips_already_inducted_player():
    conn = _fresh_conn()
    _seed_hof_candidate(conn, "p1", "Already In", "season_1")
    save_hall_of_fame_entry(conn, "p1", "season_0", {"player_id": "p1", "player_name": "Already In"})

    payload = induct_hall_of_fame(conn, "season_1")

    assert all(entry.player_id != "p1" for entry in payload.new_inductees)
    existing = load_hall_of_fame(conn)
    assert len(existing) == 1
    assert existing[0]["induction_season"] == "season_0"


def test_induct_hall_of_fame_empty_state_when_nobody_retired():
    conn = _fresh_conn()

    payload = induct_hall_of_fame(conn, "season_1")

    assert payload.new_inductees == ()
    assert get_state(conn, "offseason_hof_inducted_for") == "season_1"


# ---------------------------------------------------------------------------
# Task 5 helpers and tests
# ---------------------------------------------------------------------------


def _prospect(player_id: str, archetype: str, low_band: int, class_year: int = 2) -> Prospect:
    return Prospect(
        player_id=player_id,
        class_year=class_year,
        name=f"Rookie {player_id}",
        age=18,
        hometown="Anywhere",
        hidden_ratings={"accuracy": 70.0, "power": 70.0, "dodge": 70.0, "catch": 70.0, "stamina": 70.0},
        hidden_trajectory="normal",
        hidden_traits=[],
        public_archetype_guess=archetype,
        public_ratings_band={
            key: (low_band, low_band + 10) for key in ("accuracy", "power", "dodge", "catch", "stamina")
        },
    )


def _profile(club_id: str, top_archetype: str) -> RecruitmentProfile:
    priorities = {arc: 0.1 for arc in ("Sharpshooter", "Enforcer", "Escape Artist", "Ball Hawk", "Iron Engine")}
    priorities[top_archetype] = 0.9
    return RecruitmentProfile(
        club_id=club_id,
        archetype_priorities=priorities,
        risk_tolerance=0.5,
        prestige=0.5,
        playing_time_pitch=0.5,
        evaluation_quality=0.5,
    )


def test_rookie_preview_uses_prospect_pool_when_present():
    conn = _fresh_conn()
    save_prospect_pool(conn, [
        _prospect("r1", "Sharpshooter", 75),
        _prospect("r2", "Enforcer", 65),
        _prospect("r3", "Sharpshooter", 78),
    ])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert payload.source == "prospect_pool"
    assert payload.class_size == 3
    assert payload.archetype_distribution.get("Sharpshooter") == 2
    assert payload.archetype_distribution.get("Enforcer") == 1
    assert payload.top_band_depth == 2  # r1 (75) and r3 (78) above 70


def test_rookie_preview_falls_back_to_legacy_free_agents_when_pool_empty():
    conn = _fresh_conn()
    save_free_agents(
        conn,
        [_hof_player("fa1", "Free Agent A", age=21), _hof_player("fa2", "Free Agent B", age=22)],
        "season_2",
    )

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert payload.source == "legacy_free_agents"
    assert payload.class_size == 2
    assert payload.archetype_distribution == {}
    assert all(s.template_id != "archetype_demand" for s in payload.storylines)


def test_rookie_preview_does_not_mutate_prospect_pool():
    conn = _fresh_conn()
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 75)])

    build_rookie_class_preview(conn, "season_1", class_year=2)
    rows = conn.execute("SELECT player_id, is_signed FROM prospect_pool").fetchall()

    assert [(row["player_id"], row["is_signed"]) for row in rows] == [("r1", 0)]


def test_rookie_preview_does_not_leak_hidden_prospect_data():
    conn = _fresh_conn()
    p = _prospect("r1", "Sharpshooter", 75)
    save_prospect_pool(conn, [p])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)
    raw = get_state(conn, "offseason_rookie_preview_json")
    text = raw or ""

    assert "hidden_ratings" not in text
    assert "hidden_trajectory" not in text
    assert "hidden_traits" not in text
    for storyline in payload.storylines:
        for key in storyline.fact:
            assert key not in {"hidden_ratings", "hidden_trajectory", "hidden_traits"}


def test_rookie_preview_archetype_demand_storyline_fires_only_when_threshold_met():
    conn = _fresh_conn()
    # 4 clubs, 3 prioritize Sharpshooter (threshold ceil(4/2) = 2 -> fires)
    for club_id, top in [("a", "Sharpshooter"), ("b", "Sharpshooter"), ("c", "Sharpshooter"), ("d", "Enforcer")]:
        save_club_recruitment_profile(conn, _profile(club_id, top))
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 70)])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    demand = [s for s in payload.storylines if s.template_id == "archetype_demand"]
    assert len(demand) == 1
    assert demand[0].fact["archetype"] == "Sharpshooter"
    assert demand[0].fact["count"] == 3
    assert demand[0].fact["total"] == 4
    assert "Sharpshooter in heavy demand" in demand[0].sentence


def test_rookie_preview_archetype_demand_storyline_skipped_when_under_threshold():
    conn = _fresh_conn()
    # 4 clubs, only 1 prioritizes Sharpshooter (under threshold 2)
    for club_id, top in [("a", "Sharpshooter"), ("b", "Enforcer"), ("c", "Ball Hawk"), ("d", "Iron Engine")]:
        save_club_recruitment_profile(conn, _profile(club_id, top))
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 70)])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert all(s.template_id != "archetype_demand" for s in payload.storylines)


def test_rookie_preview_persists_class_summary_for_future_comparisons():
    conn = _fresh_conn()
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 80), _prospect("r2", "Enforcer", 60)])

    build_rookie_class_preview(conn, "season_1", class_year=2)

    raw = get_state(conn, "rookie_class_summary_2")
    assert raw is not None
    summary = json.loads(raw)
    assert summary["class_size"] == 2
    assert summary["top_band_depth"] == 1
    assert "free_agent_count" in summary


def test_rookie_preview_top_band_depth_storyline_fires_when_class_is_deepest():
    conn = _fresh_conn()
    set_state(conn, "rookie_class_summary_1", json.dumps({"class_size": 5, "top_band_depth": 1, "free_agent_count": 4}))
    save_prospect_pool(conn, [
        _prospect("r1", "Sharpshooter", 80, class_year=2),
        _prospect("r2", "Enforcer", 80, class_year=2),
        _prospect("r3", "Ball Hawk", 80, class_year=2),
    ])

    payload = build_rookie_class_preview(conn, "season_2", class_year=2)

    deepest = [s for s in payload.storylines if s.template_id == "top_band_depth"]
    assert len(deepest) == 1
    assert deepest[0].fact["current_depth"] == 3
    assert deepest[0].fact["prior_max"] == 1
    assert "Deepest top-band class" in deepest[0].sentence


def test_rookie_preview_idempotent_returns_same_payload_on_second_call():
    conn = _fresh_conn()
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 75)])

    first = build_rookie_class_preview(conn, "season_1", class_year=2)
    second = build_rookie_class_preview(conn, "season_1", class_year=2)

    assert first == second
    assert get_state(conn, "offseason_rookie_preview_for") == "season_1"


def test_rookie_preview_ai_cluster_storyline_fires_when_three_or_more_clubs_cluster():
    conn = _fresh_conn()
    # 5 clubs, 4 prioritize Sharpshooter — strict top (Enforcer has 1), count >= 3 -> fires
    for club_id, top in [("a", "Sharpshooter"), ("b", "Sharpshooter"), ("c", "Sharpshooter"), ("d", "Sharpshooter"), ("e", "Enforcer")]:
        save_club_recruitment_profile(conn, _profile(club_id, top))
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 70)])

    payload = build_rookie_class_preview(conn, "season_1", class_year=2)

    cluster = [s for s in payload.storylines if s.template_id == "ai_cluster"]
    assert len(cluster) == 1
    assert cluster[0].fact["archetype"] == "Sharpshooter"
    assert cluster[0].fact["count"] == 4
    assert "clustering on Sharpshooter" in cluster[0].sentence


def test_rookie_preview_free_agent_crop_storyline_fires_when_crop_is_lightest():
    conn = _fresh_conn()
    # Prior class_year=1 had 5 free agents; current has 2 -> fires (2 <= 5)
    set_state(conn, "rookie_class_summary_1", json.dumps({"class_size": 6, "top_band_depth": 2, "free_agent_count": 5}))
    save_prospect_pool(conn, [_prospect("r1", "Sharpshooter", 70, class_year=2)])
    save_free_agents(conn, [_hof_player("fa1", "Agent A", age=21), _hof_player("fa2", "Agent B", age=22)], "season_1")

    payload = build_rookie_class_preview(conn, "season_2", class_year=2)

    crop = [s for s in payload.storylines if s.template_id == "free_agent_crop"]
    assert len(crop) == 1
    assert crop[0].fact["current_count"] == 2
    assert crop[0].fact["prior_min"] == 5
    assert "Lightest free-agent crop" in crop[0].sentence
