"""V28 The Weather — Phase 1 meta-journalism probe.

The derived-from-data gate for the league bulletin: builds a small synthetic
pyramid save with hand-built official matches (plus one playoff match that MUST
be excluded), then asserts:

  1. Every ``meta_report`` headline claim recomputes from
     ``compute_league_trends`` over the same rows (no injected dials) — the
     formatted number in the headline matches the independently computed trend.
  2. Playoff match-ids (``LIKE '{season}_p_%'``) are excluded from the trends
     (a 100%/100-catch playoff blowout must not move a division's rate).
  3. The report surfaces in ``build_news_payload`` (the widened news filter).
  4. A legacy (non-pyramid) save writes no bulletin (byte-identical).

Usage:  python tools/meta_journalism_probe.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dodgeball_sim.career_setup import initialize_curated_manager_career  # noqa: E402
from dodgeball_sim.meta_journalism import (  # noqa: E402
    _division_display_name,
    compute_league_trends,
    generate_league_bulletin,
)
from dodgeball_sim.persistence import (  # noqa: E402
    create_schema,
    get_state,
    load_division_memberships,
    load_news_headlines,
    save_match_result,
    set_state,
)
from dodgeball_sim.web_status_service import build_news_payload  # noqa: E402

_SEED = 20260618


def _fresh_pyramid_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    initialize_curated_manager_career(
        conn, "aurora", _SEED, ruleset_selection="official_foam", world="pyramid"
    )
    conn.commit()
    return conn


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


def _build_fixture():
    conn = _fresh_pyramid_conn()
    season_id = "season_1"
    ms = load_division_memberships(conn, season_id)
    premier = [m.club_id for m in ms if m.division_id == "premier"][:2]
    challenger = [m.club_id for m in ms if m.division_id == "challenger"][:2]
    assert len(premier) >= 2 and len(challenger) >= 2, "need 2 clubs per division"
    club_a, club_b = premier
    club_c, club_d = challenger
    go_for = {
        "approach": "aggressive", "target_focus": "their_stars",
        "catch_posture": "go_for_catches", "rush_commit": "all_in",
        "rush_target": "nearest",
    }
    play_safe = {
        "approach": "patient", "target_focus": "spread",
        "catch_posture": "play_safe", "rush_commit": "hold_back",
        "rush_target": "center",
    }
    _save_official_match(
        conn, match_id="season_1_w1_ab", season_id=season_id, week=1,
        home_club_id=club_a, away_club_id=club_b, winner_club_id=club_a,
        home_gp=6, away_gp=3, home_policy=go_for, away_policy=play_safe,
        player_stats=[
            {"player_id": "pa1", "club_id": club_a, "catches_attempted": 10, "catches_made": 6,
             "throws_attempted": 20, "eliminations_by_throw": 8},
            {"player_id": "pb1", "club_id": club_b, "catches_attempted": 10, "catches_made": 3,
             "throws_attempted": 20, "eliminations_by_throw": 4},
        ],
    )
    _save_official_match(
        conn, match_id="season_1_w2_ab", season_id=season_id, week=2,
        home_club_id=club_b, away_club_id=club_a, winner_club_id=club_a,
        home_gp=2, away_gp=6, home_policy=play_safe, away_policy=go_for,
        player_stats=[
            {"player_id": "pa2", "club_id": club_a, "catches_attempted": 5, "catches_made": 3,
             "throws_attempted": 10, "eliminations_by_throw": 5},
        ],
    )
    _save_official_match(
        conn, match_id="season_1_w1_cd", season_id=season_id, week=1,
        home_club_id=club_c, away_club_id=club_d, winner_club_id=club_c,
        home_gp=7, away_gp=5, home_policy=go_for, away_policy=play_safe,
        player_stats=[
            {"player_id": "pc1", "club_id": club_c, "catches_attempted": 8, "catches_made": 4,
             "throws_attempted": 16, "eliminations_by_throw": 6},
        ],
    )
    _save_official_match(
        conn, match_id="season_1_w2_cd", season_id=season_id, week=2,
        home_club_id=club_d, away_club_id=club_c, winner_club_id=club_d,
        home_gp=6, away_gp=4, home_policy=play_safe, away_policy=go_for,
        player_stats=[],
    )
    # Playoff blowout — MUST be excluded.
    _save_official_match(
        conn, match_id="season_1_p_1", season_id=season_id, week=99,
        home_club_id=club_a, away_club_id=club_c, winner_club_id=club_a,
        home_gp=6, away_gp=0, home_policy=go_for, away_policy=play_safe,
        player_stats=[
            {"player_id": "px", "club_id": club_a, "catches_attempted": 100, "catches_made": 100,
             "throws_attempted": 100, "eliminations_by_throw": 100},
        ],
    )
    conn.commit()
    return conn, season_id


def _check_headline_claims(headlines, trends) -> None:
    """Each headline's formatted number must recompute from the trends."""
    by_division = trends["by_division"]
    posture_wins = trends["posture_wins"]
    by_id = {h["headline_id"]: h["headline_text"] for h in headlines}

    # meta_catch_<season>: top catch-rate division, formatted as a percentage.
    catch_id = next((i for i in by_id if i.startswith("meta_catch_")), None)
    if catch_id:
        divs = sorted(
            ((d, v["catch_rate"]) for d, v in by_division.items() if v["match_count"] > 0),
            key=lambda x: x[1], reverse=True,
        )
        top_div, top_rate = divs[0]
        low_div, low_rate = divs[-1]
        text = by_id[catch_id]
        assert f"{top_rate:.1%}" in text, (
            f"meta_catch headline lost its catch rate: {text!r} missing {top_rate:.1%}"
        )
        assert f"{top_rate - low_rate:.1%}" in text, (
            f"meta_catch headline lost its spread: {text!r} missing {top_rate - low_rate:.1%}"
        )
        assert _division_display_name(top_div) in text
        print(f"    meta_catch derives: {_division_display_name(top_div)} {top_rate:.1%} "
              f"(+{top_rate - low_rate:.1%}) [ok]")

    # meta_posture_<season>: the most-winning posture value, W-L record.
    posture_id = next((i for i in by_id if i.startswith("meta_posture_")), None)
    if posture_id:
        best = None
        best_wr = 0.0
        for _dim, values in posture_wins.items():
            for val, bucket in values.items():
                if bucket["appearances"] >= 3 and bucket["win_rate"] > best_wr:
                    best_wr = bucket["win_rate"]
                    best = (val, bucket["wins"], bucket["appearances"])
        assert best is not None, "meta_posture headline written but no qualifying posture in trends"
        val, wins, apps = best
        text = by_id[posture_id]
        assert f"{wins}-{apps - wins}" in text, (
            f"meta_posture headline lost its record: {text!r} missing {wins}-{apps - wins}"
        )
        print(f"    meta_posture derives: {val} went {wins}-{apps - wins} (wr {best_wr:.0%}) [ok]")

    # meta_margin_<season>: top avg game-point margin, 1 decimal.
    margin_id = next((i for i in by_id if i.startswith("meta_margin_")), None)
    if margin_id:
        divs = sorted(
            ((d, v["avg_game_point_margin"]) for d, v in by_division.items() if v["match_count"] > 0),
            key=lambda x: x[1], reverse=True,
        )
        top_div, top_margin = divs[0]
        text = by_id[margin_id]
        assert f"{top_margin:.1f}" in text, (
            f"meta_margin headline lost its margin: {text!r} missing {top_margin:.1f}"
        )
        print(f"    meta_margin derives: {_division_display_name(top_div)} {top_margin:.1f} [ok]")


def run_probe() -> bool:
    print(f"Meta journalism probe — derived-from-data fence, seed {_SEED}")
    conn, season_id = _build_fixture()

    # --- 1. Playoff exclusion: the 100/100 blowout must not move premier ------
    trends = compute_league_trends(conn, season_id)
    premier = trends["by_division"]["premier"]
    assert premier["match_count"] == 2, (
        f"playoff match leaked into premier trends (match_count={premier['match_count']})"
    )
    # Premier catch rate without the playoff: (6+3+3)/(10+10+5) = 12/25 = 0.48.
    assert abs(premier["catch_rate"] - 12 / 25) < 1e-12, (
        f"premier catch_rate {premier['catch_rate']} != 0.48 — playoff leak or math drift"
    )
    print(f"  [1] playoff excluded — premier catch_rate {premier['catch_rate']:.1%} over 2 matches [ok]")

    # --- 2. Every headline claim recomputes from the trends -------------------
    generate_league_bulletin(conn, season_id)
    headlines = [
        h for h in load_news_headlines(conn, season_id) if h["category"] == "meta_report"
    ]
    assert headlines, "generate_league_bulletin wrote no meta_report headlines"
    print(f"  [2] {len(headlines)} meta_report headline(s) — checking derived-from-data:")
    _check_headline_claims(headlines, trends)

    # --- 3. The report surfaces in the news wire ------------------------------
    set_state(conn, "active_season_id", season_id)
    conn.commit()
    payload = build_news_payload(conn)
    wire_texts = {item["text"] for item in payload["items"]}
    surfaced = [h["headline_text"] for h in headlines if h["headline_text"] in wire_texts]
    assert surfaced, "no meta_report headline surfaced in build_news_payload (filter not widened?)"
    print(f"  [3] {len(surfaced)}/{len(headlines)} meta_report headline(s) surfaced in the news wire [ok]")

    # --- 4. Legacy save writes no bulletin ------------------------------------
    legacy = sqlite3.connect(":memory:", check_same_thread=False)
    legacy.row_factory = sqlite3.Row
    create_schema(legacy)
    initialize_curated_manager_career(legacy, "aurora", _SEED, ruleset_selection="official_foam")
    legacy.commit()
    sid = get_state(legacy, "active_season_id")
    generate_league_bulletin(legacy, sid)
    legacy_meta = [
        h for h in load_news_headlines(legacy, sid) if h["category"] == "meta_report"
    ]
    assert legacy_meta == [], "legacy (non-pyramid) save wrote a bulletin — should be byte-identical"
    print("  [4] legacy save wrote no bulletin (byte-identical) [ok]")

    print("\n  PASS: every bulletin claim is derivable from the queried match data")
    return True


def main():
    try:
        ok = run_probe()
    except AssertionError as exc:
        print(f"\n  FAIL: {exc}")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
