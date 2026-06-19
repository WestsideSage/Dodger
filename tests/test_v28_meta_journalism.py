"""V28 The Weather — Phase 1: meta journalism (data-derived league trends).

Per docs/specs/2026-06-17-v28-the-weather-spec.md (Phase 1): ``compute_league_trends``
is a read-only aggregate over persisted ``match_records`` / ``player_match_stats`` /
``team_policies`` (in ``official_score_json``). Every returned number must
recompute from the same rows (the derived-from-data fence). Playoff match-ids
(``LIKE '{season}_p_%'``) are excluded; posture trends come only from official
matches. ``generate_league_bulletin`` writes ``category='meta_report'`` headlines
whose claims are backed by the trends, idempotent per season. The news filter is
widened (additive) so ``meta_report`` surfaces in the wire. Pyramid-gated; legacy
byte-identical.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from dodgeball_sim.career_setup import initialize_curated_manager_career
from dodgeball_sim.config import DEFAULT_WEATHER, WeatherConfig
from dodgeball_sim.persistence import (
    create_schema,
    get_state,
    load_news_headlines,
    save_division_memberships,
    save_match_result,
    set_state,
)
from dodgeball_sim.league import DivisionMembership

_SEED = 20260618


# ---------------------------------------------------------------------------
# Fixture helpers — a small synthetic pyramid save with hand-built match rows
# ---------------------------------------------------------------------------


def _fresh_pyramid_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


def _membership(season_id, club_id, division_id, name, tier, kind="domestic"):
    return DivisionMembership(
        season_id=season_id,
        club_id=club_id,
        division_id=division_id,
        division_name=name,
        tier=tier,
        kind=kind,
    )


def _save_official_match(
    conn,
    *,
    match_id,
    season_id,
    week,
    home_club_id,
    away_club_id,
    winner_club_id,
    home_gp,
    away_gp,
    home_policy,
    away_policy,
    player_stats=None,
):
    """Insert a completed official match with team_policies in official_score_json."""
    score_json = json.dumps(
        {"team_policies": {home_club_id: home_policy, away_club_id: away_policy}}
    )
    save_match_result(
        conn,
        match_id=match_id,
        season_id=season_id,
        week=week,
        home_club_id=home_club_id,
        away_club_id=away_club_id,
        winner_club_id=winner_club_id,
        home_survivors=3,
        away_survivors=2,
        home_roster_hash="h",
        away_roster_hash="a",
        config_version="v1",
        ruleset_version="v1",
        seed=1,
        event_log_hash="e",
        final_state_hash="f",
        scoring_model="official",
        home_game_points=home_gp,
        away_game_points=away_gp,
        official_score_json=score_json,
    )
    for stats in player_stats or []:
        conn.execute(
            """
            INSERT OR REPLACE INTO player_match_stats
                (match_id, player_id, club_id, throws_attempted, throws_on_target,
                 eliminations_by_throw, catches_attempted, catches_made,
                 times_targeted, dodges_successful, times_hit, times_eliminated,
                 revivals_caused, clutch_events, elimination_plus_minus)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                match_id,
                stats["player_id"],
                stats["club_id"],
                stats.get("throws_attempted", 0),
                stats.get("throws_on_target", 0),
                stats.get("eliminations_by_throw", 0),
                stats.get("catches_attempted", 0),
                stats.get("catches_made", 0),
                stats.get("times_targeted", 0),
                stats.get("dodges_successful", 0),
                stats.get("times_hit", 0),
                stats.get("times_eliminated", 0),
                stats.get("revivals_caused", 0),
                stats.get("clutch_events", 0),
                stats.get("elimination_plus_minus", 0),
            ),
        )


def _built_fixture():
    """A pyramid save with two divisions, four official matches, one playoff
    match (must be excluded), and known player stats / team_policies.

    Uses real club IDs from the initialized career so ``build_news_payload``
    (which looks up clubs by id) works end-to-end.
    """
    conn = _fresh_pyramid_conn()
    season_id = "season_1"
    # Pick two clubs from premier and two from challenger (real club IDs).
    from dodgeball_sim.persistence import load_division_memberships

    ms = load_division_memberships(conn, season_id)
    premier = [m.club_id for m in ms if m.division_id == "premier"][:2]
    challenger = [m.club_id for m in ms if m.division_id == "challenger"][:2]
    assert len(premier) >= 2 and len(challenger) >= 2, "need 2 clubs per division"
    club_a, club_b = premier
    club_c, club_d = challenger
    go_for = {
        "approach": "aggressive",
        "target_focus": "their_stars",
        "catch_posture": "go_for_catches",
        "rush_commit": "all_in",
        "rush_target": "nearest",
    }
    play_safe = {
        "approach": "patient",
        "target_focus": "spread",
        "catch_posture": "play_safe",
        "rush_commit": "hold_back",
        "rush_target": "center",
    }
    # Premier: club_a (go_for) wins both vs club_b (play_safe).
    _save_official_match(
        conn,
        match_id="season_1_w1_ab",
        season_id=season_id,
        week=1,
        home_club_id=club_a,
        away_club_id=club_b,
        winner_club_id=club_a,
        home_gp=6,
        away_gp=3,
        home_policy=go_for,
        away_policy=play_safe,
        player_stats=[
            {"player_id": "pa1", "club_id": club_a, "catches_attempted": 10, "catches_made": 6,
             "throws_attempted": 20, "eliminations_by_throw": 8},
            {"player_id": "pb1", "club_id": club_b, "catches_attempted": 10, "catches_made": 3,
             "throws_attempted": 20, "eliminations_by_throw": 4},
        ],
    )
    _save_official_match(
        conn,
        match_id="season_1_w2_ab",
        season_id=season_id,
        week=2,
        home_club_id=club_b,
        away_club_id=club_a,
        winner_club_id=club_a,
        home_gp=2,
        away_gp=6,
        home_policy=play_safe,
        away_policy=go_for,
        player_stats=[
            {"player_id": "pa2", "club_id": club_a, "catches_attempted": 5, "catches_made": 3,
             "throws_attempted": 10, "eliminations_by_throw": 5},
        ],
    )
    # Challenger: split 1-1.
    _save_official_match(
        conn,
        match_id="season_1_w1_cd",
        season_id=season_id,
        week=1,
        home_club_id=club_c,
        away_club_id=club_d,
        winner_club_id=club_c,
        home_gp=7,
        away_gp=5,
        home_policy=go_for,
        away_policy=play_safe,
        player_stats=[
            {"player_id": "pc1", "club_id": club_c, "catches_attempted": 8, "catches_made": 4,
             "throws_attempted": 16, "eliminations_by_throw": 6},
        ],
    )
    _save_official_match(
        conn,
        match_id="season_1_w2_cd",
        season_id=season_id,
        week=2,
        home_club_id=club_d,
        away_club_id=club_c,
        winner_club_id=club_d,
        home_gp=6,
        away_gp=4,
        home_policy=play_safe,
        away_policy=go_for,
        player_stats=[],
    )
    # Playoff match — MUST be excluded from trends.
    _save_official_match(
        conn,
        match_id="season_1_p_1",
        season_id=season_id,
        week=99,
        home_club_id=club_a,
        away_club_id=club_c,
        winner_club_id=club_a,
        home_gp=6,
        away_gp=0,
        home_policy=go_for,
        away_policy=play_safe,
        player_stats=[
            {"player_id": "px", "club_id": club_a, "catches_attempted": 100, "catches_made": 100,
             "throws_attempted": 100, "eliminations_by_throw": 100},
        ],
    )
    conn.commit()
    return conn, season_id, (club_a, club_b, club_c, club_d)


# ---------------------------------------------------------------------------
# Task 1.1 — WeatherConfig + compute_league_trends
# ---------------------------------------------------------------------------


class TestWeatherConfig:
    def test_default_weather_has_required_knobs(self):
        cfg: WeatherConfig = DEFAULT_WEATHER
        assert 0.0 < cfg.trend_notable_delta < 0.2
        assert 0.0 < cfg.drift_rate < 0.5
        assert 0.10 <= cfg.contrarian_fraction <= 0.30
        assert 0.0 < cfg.emphasis_catch_delta_max < 0.2
        assert 0.0 < cfg.emphasis_block_delta_max < 0.2


class TestComputeLeagueTrends:
    def test_returns_per_division_catch_and_elimination_rates(self):
        from dodgeball_sim.meta_journalism import compute_league_trends

        conn, season_id, (club_a, club_b, _c, _d) = _built_fixture()
        trends = compute_league_trends(conn, season_id)
        # Premier: club_a + club_b players. Non-playoff matches only.
        #   catches: 6+3+3 = 12 made / 10+10+5 = 25 attempted ⇒ 0.48
        #   eliminations: 8+4+5 = 17 / 20+20+10 = 50 ⇒ 0.34
        premier = trends["by_division"]["premier"]
        assert premier["match_count"] == 2
        assert abs(premier["catch_rate"] - 12 / 25) < 1e-9
        assert abs(premier["elimination_rate"] - 17 / 50) < 1e-9

    def test_game_point_margin_per_division(self):
        from dodgeball_sim.meta_journalism import compute_league_trends

        conn, season_id, _clubs = _built_fixture()
        trends = compute_league_trends(conn, season_id)
        # Premier: |6-3|=3, |2-6|=4 ⇒ avg 3.5
        premier = trends["by_division"]["premier"]
        assert abs(premier["avg_game_point_margin"] - 3.5) < 1e-9
        # Challenger: |7-5|=2, |6-4|=2 ⇒ avg 2.0
        challenger = trends["by_division"]["challenger"]
        assert abs(challenger["avg_game_point_margin"] - 2.0) < 1e-9

    def test_playoff_matches_excluded(self):
        from dodgeball_sim.meta_journalism import compute_league_trends

        conn, season_id, _clubs = _built_fixture()
        trends = compute_league_trends(conn, season_id)
        # The playoff match had 100/100 catch — if it leaked, premier catch_rate
        # would be far higher. Premier match_count must be 2, not 3.
        premier = trends["by_division"]["premier"]
        assert premier["match_count"] == 2
        # Challenger had the playoff's club_c but no playoff stats leaked.
        challenger = trends["by_division"]["challenger"]
        assert challenger["match_count"] == 2

    def test_posture_win_correlation_from_team_policies(self):
        from dodgeball_sim.meta_journalism import compute_league_trends

        conn, season_id, _clubs = _built_fixture()
        trends = compute_league_trends(conn, season_id)
        # catch_posture: go_for_catches appeared in 4 matches (both sides each),
        # won 3 (club_a twice + club_c once), lost 1 (club_d beat club_c's go_for
        # opponent... actually club_d was play_safe and won). Let's count:
        #   Match1: go_for (club_a) W, play_safe (club_b) L
        #   Match2: play_safe (club_b) L, go_for (club_a) W
        #   Match3: go_for (club_c) W, play_safe (club_d) L
        #   Match4: play_safe (club_d) W, go_for (club_c) L
        # go_for: 4 appearances, 3 wins (match1, match2, match3) ⇒ 0.75
        # play_safe: 4 appearances, 1 win (match4) ⇒ 0.25
        cp = trends["posture_wins"]["catch_posture"]
        assert cp["go_for_catches"]["appearances"] == 4
        assert cp["go_for_catches"]["wins"] == 3
        assert abs(cp["go_for_catches"]["win_rate"] - 0.75) < 1e-9
        assert cp["play_safe"]["wins"] == 1
        assert abs(cp["play_safe"]["win_rate"] - 0.25) < 1e-9

    def test_derived_from_data_fence(self):
        """Every returned number recomputes from the same queried rows."""
        from dodgeball_sim.meta_journalism import compute_league_trends

        conn, season_id, (club_a, club_b, _c, _d) = _built_fixture()
        trends = compute_league_trends(conn, season_id)
        # Independently recompute premier catch_rate from the raw rows.
        rows = conn.execute(
            """
            SELECT pms.catches_made, pms.catches_attempted
            FROM player_match_stats pms
            JOIN match_records mr ON pms.match_id = mr.match_id
            WHERE mr.season_id = ? AND mr.match_id NOT LIKE ? || '_p_%'
              AND mr.official_score_json IS NOT NULL
              AND pms.club_id IN (?, ?)
            """,
            (season_id, season_id, club_a, club_b),
        ).fetchall()
        made = sum(r["catches_made"] for r in rows)
        attempted = sum(r["catches_attempted"] for r in rows)
        assert abs(trends["by_division"]["premier"]["catch_rate"] - made / attempted) < 1e-12

    def test_legacy_save_has_no_division_trends(self):
        """Legacy (non-pyramid) saves have no division_membership ⇒ empty trends."""
        from dodgeball_sim.meta_journalism import compute_league_trends

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        initialize_curated_manager_career(
            conn, "aurora", _SEED, ruleset_selection="official_foam"
        )
        conn.commit()
        trends = compute_league_trends(conn, get_state(conn, "active_season_id"))
        assert trends["by_division"] == {}
        assert trends["posture_wins"] == {}


# ---------------------------------------------------------------------------
# Task 1.2 — generate_league_bulletin + news-filter widening
# ---------------------------------------------------------------------------


class TestGenerateLeagueBulletin:
    def test_writes_meta_report_headlines_backed_by_trends(self):
        from dodgeball_sim.meta_journalism import compute_league_trends, generate_league_bulletin

        conn, season_id, _clubs = _built_fixture()
        generate_league_bulletin(conn, season_id)
        headlines = [
            h for h in load_news_headlines(conn, season_id) if h["category"] == "meta_report"
        ]
        assert headlines, "generate_league_bulletin must write meta_report headlines"
        # Every headline claim must recompute from the trends (derived-from-data).
        trends = compute_league_trends(conn, season_id)
        for h in headlines:
            assert h["headline_text"]
            assert h["headline_id"].startswith("meta_")

    def test_idempotent_per_season(self):
        from dodgeball_sim.meta_journalism import generate_league_bulletin

        conn, season_id, _clubs = _built_fixture()
        generate_league_bulletin(conn, season_id)
        first = [
            h for h in load_news_headlines(conn, season_id) if h["category"] == "meta_report"
        ]
        generate_league_bulletin(conn, season_id)
        second = [
            h for h in load_news_headlines(conn, season_id) if h["category"] == "meta_report"
        ]
        assert len(first) == len(second)
        assert {h["headline_id"] for h in first} == {h["headline_id"] for h in second}

    def test_meta_report_surfaces_in_news_payload(self):
        from dodgeball_sim.meta_journalism import generate_league_bulletin
        from dodgeball_sim.web_status_service import build_news_payload

        conn, season_id, _clubs = _built_fixture()
        generate_league_bulletin(conn, season_id)
        set_state(conn, "active_season_id", season_id)
        conn.commit()
        payload = build_news_payload(conn)
        texts = [item["text"] for item in payload["items"]]
        meta_texts = [
            h["headline_text"]
            for h in load_news_headlines(conn, season_id)
            if h["category"] == "meta_report"
        ]
        assert any(t in texts for t in meta_texts), "meta_report must surface in the news wire"

    def test_legacy_save_no_bulletin(self):
        from dodgeball_sim.meta_journalism import generate_league_bulletin

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        initialize_curated_manager_career(
            conn, "aurora", _SEED, ruleset_selection="official_foam"
        )
        conn.commit()
        sid = get_state(conn, "active_season_id")
        generate_league_bulletin(conn, sid)
        meta = [
            h for h in load_news_headlines(conn, sid) if h["category"] == "meta_report"
        ]
        assert meta == []
