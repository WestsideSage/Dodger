"""V28 The Weather — Phase 1: meta journalism (data-derived league trends).

Read-only aggregate over persisted ``match_records`` / ``player_match_stats`` /
``team_policies`` (stored inside ``official_score_json``). Every returned number
recomputes from the same queried rows (the derived-from-data fence). Playoff
match-ids (``LIKE '{season}_p_%'``) are excluded; posture trends come only from
official matches. ``generate_league_bulletin`` writes ``category='meta_report'``
headlines whose text claims are backed by the trends, idempotent per season.

Spec: docs/specs/2026-06-17-v28-the-weather-spec.md (Phase 1). Pyramid-gated at
the offseason call site; legacy single-league saves have no division_membership
so ``compute_league_trends`` returns empty trends naturally (byte-identical).
``meta.py``/MetaPatch stays retired — weather is computed from data, never an
injected dial.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict

from .config import DEFAULT_WEATHER
from .game_loop import season_sort_key

# CoachPolicy dimensions tracked for posture win-correlation. Each maps to the
# key used in the team_policies dict stored inside official_score_json.
_POLICY_DIMENSIONS = (
    "approach",
    "target_focus",
    "catch_posture",
    "rush_commit",
    "rush_target",
)


def _is_playoff(match_id: str, season_id: str) -> bool:
    return match_id.startswith(f"{season_id}_p_")


def compute_league_trends(
    conn: sqlite3.Connection, season_id: str
) -> Dict[str, Any]:
    """Return data-derived league trends for a season.

    Structure::

        {
            "by_division": {
                "<division_id>": {
                    "catch_rate": float,          # catches_made / catches_attempted
                    "elimination_rate": float,    # eliminations_by_throw / throws_attempted
                    "avg_game_point_margin": float,
                    "match_count": int,
                },
                ...
            },
            "posture_wins": {
                "<dimension>": {
                    "<value>": {"wins": int, "appearances": int, "win_rate": float},
                    ...
                },
                ...
            },
        }

    Playoff match-ids are excluded. Posture trends come only from official
    matches (rows with ``official_score_json`` carrying ``team_policies``).
    Returns empty structures when there is no division_membership (legacy saves).
    """
    # club_id → division_id for this season (empty for legacy single-league).
    membership_rows = conn.execute(
        "SELECT club_id, division_id FROM division_membership WHERE season_id = ?",
        (season_id,),
    ).fetchall()
    club_to_division: Dict[str, str] = {
        r["club_id"]: r["division_id"] for r in membership_rows
    }
    if not club_to_division:
        return {"by_division": {}, "posture_wins": {}}

    # --- Per-division catch / elimination rates (from player_match_stats) ---
    # Official, non-playoff matches only. A match is "official" when it carries
    # official_score_json (the team_policies carrier). We join through
    # player_match_stats → match_records for the season/playoff/official filter,
    # then map each player's club to its division.
    stat_rows = conn.execute(
        """
        SELECT pms.club_id,
               pms.catches_made, pms.catches_attempted,
               pms.eliminations_by_throw, pms.throws_attempted,
               mr.match_id
        FROM player_match_stats pms
        JOIN match_records mr ON pms.match_id = mr.match_id
        WHERE mr.season_id = ?
          AND mr.official_score_json IS NOT NULL
        """,
        (season_id,),
    ).fetchall()

    div_catch_made: Dict[str, int] = {}
    div_catch_attempted: Dict[str, int] = {}
    div_elim_made: Dict[str, int] = {}
    div_elim_attempted: Dict[str, int] = {}
    div_match_ids: Dict[str, set] = {}

    for r in stat_rows:
        if _is_playoff(r["match_id"], season_id):
            continue
        div = club_to_division.get(r["club_id"])
        if div is None:
            continue
        div_catch_made[div] = div_catch_made.get(div, 0) + (r["catches_made"] or 0)
        div_catch_attempted[div] = div_catch_attempted.get(div, 0) + (r["catches_attempted"] or 0)
        div_elim_made[div] = div_elim_made.get(div, 0) + (r["eliminations_by_throw"] or 0)
        div_elim_attempted[div] = div_elim_attempted.get(div, 0) + (r["throws_attempted"] or 0)
        div_match_ids.setdefault(div, set()).add(r["match_id"])

    # --- Per-division game-point margin (from match_records) ---
    match_rows = conn.execute(
        """
        SELECT match_id, home_club_id, away_club_id,
               home_game_points, away_game_points
        FROM match_records
        WHERE season_id = ? AND official_score_json IS NOT NULL
        """,
        (season_id,),
    ).fetchall()

    div_margin_sum: Dict[str, float] = {}
    div_match_count: Dict[str, int] = {}

    for r in match_rows:
        if _is_playoff(r["match_id"], season_id):
            continue
        # A round-robin match is between two clubs in the same division; use the
        # home club's division (away is the same for intra-division scheduling).
        div = club_to_division.get(r["home_club_id"])
        if div is None:
            continue
        margin = abs((r["home_game_points"] or 0) - (r["away_game_points"] or 0))
        div_margin_sum[div] = div_margin_sum.get(div, 0.0) + margin
        div_match_count[div] = div_match_count.get(div, 0) + 1

    by_division: Dict[str, Dict[str, Any]] = {}
    all_divs = set(div_match_count) | set(div_catch_attempted)
    for div in all_divs:
        catch_rate = (
            div_catch_made.get(div, 0) / div_catch_attempted.get(div, 0)
            if div_catch_attempted.get(div, 0)
            else 0.0
        )
        elim_rate = (
            div_elim_made.get(div, 0) / div_elim_attempted.get(div, 0)
            if div_elim_attempted.get(div, 0)
            else 0.0
        )
        mc = div_match_count.get(div, 0)
        avg_margin = div_margin_sum.get(div, 0.0) / mc if mc else 0.0
        by_division[div] = {
            "catch_rate": catch_rate,
            "elimination_rate": elim_rate,
            "avg_game_point_margin": avg_margin,
            "match_count": mc,
        }

    # --- Posture win-correlation (from team_policies in official_score_json) ---
    posture_wins: Dict[str, Dict[str, Dict[str, Any]]] = {
        dim: {} for dim in _POLICY_DIMENSIONS
    }
    for r in match_rows:
        if _is_playoff(r["match_id"], season_id):
            continue
        raw = r["official_score_json"] if "official_score_json" in r.keys() else None
        # Re-fetch the json column (the SELECT above didn't include it).
        # We do a focused pull here to keep the query signature stable.
        score_row = conn.execute(
            "SELECT official_score_json, winner_club_id FROM match_records WHERE match_id = ?",
            (r["match_id"],),
        ).fetchone()
        if score_row is None or not score_row["official_score_json"]:
            continue
        try:
            score = json.loads(score_row["official_score_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        policies = score.get("team_policies") or {}
        winner = score_row["winner_club_id"]
        for club_id, policy in policies.items():
            if not isinstance(policy, dict):
                continue
            for dim in _POLICY_DIMENSIONS:
                val = policy.get(dim)
                if val is None:
                    continue
                bucket = posture_wins[dim].setdefault(
                    val, {"wins": 0, "appearances": 0, "win_rate": 0.0}
                )
                bucket["appearances"] += 1
                if club_id == winner:
                    bucket["wins"] += 1
    for dim, values in posture_wins.items():
        for val, bucket in values.items():
            bucket["win_rate"] = (
                bucket["wins"] / bucket["appearances"]
                if bucket["appearances"]
                else 0.0
            )

    return {"by_division": by_division, "posture_wins": posture_wins}


def _division_display_name(division_id: str) -> str:
    """Best-effort human name for a division id."""
    names = {
        "premier": "Premier League",
        "challenger": "Challenger League",
        "district": "District League",
        "circuit": "International Circuit",
    }
    return names.get(division_id, division_id.replace("_", " ").title())


def generate_league_bulletin(
    conn: sqlite3.Connection, season_id: str
) -> None:
    """Write ``category='meta_report'`` headlines derived from league trends.

    Every claim in a headline recomputes from ``compute_league_trends`` (the
    derived-from-data fence). Idempotent per season (its own
    ``v28_bulletin_for`` guard via ``INSERT OR REPLACE`` on a stable
    ``headline_id``). Pyramid-gated at the call site; a no-op when there are no
    division memberships (legacy saves).
    """
    from .persistence import load_news_headlines, save_news_headlines
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        return

    trends = compute_league_trends(conn, season_id)
    by_division = trends["by_division"]
    posture_wins = trends["posture_wins"]
    if not by_division:
        return

    cfg = DEFAULT_WEATHER
    headlines: list[Dict[str, Any]] = []

    # Trend 1: the division with the highest catch rate (if notable spread).
    divs_with_catch = [
        (d, v["catch_rate"]) for d, v in by_division.items() if v["match_count"] > 0
    ]
    if len(divs_with_catch) >= 2:
        divs_with_catch.sort(key=lambda x: x[1], reverse=True)
        top_div, top_rate = divs_with_catch[0]
        low_div, low_rate = divs_with_catch[-1]
        if top_rate - low_rate >= cfg.trend_notable_delta:
            headlines.append({
                "headline_id": f"meta_catch_{season_id}",
                "category": "meta_report",
                "headline_text": (
                    f"{_division_display_name(top_div)} lead the pyramid in catch rate "
                    f"({top_rate:.1%}), {top_rate - low_rate:.1%} above "
                    f"{_division_display_name(low_div)}."
                ),
                "entity_ids": [],
            })

    # Trend 2: the most winning posture across all divisions (anti-solvedness
    # signal — a dominant tactic the ecosystem should react to).
    best_posture = None
    best_win_rate = 0.0
    for dim, values in posture_wins.items():
        for val, bucket in values.items():
            if bucket["appearances"] >= 3 and bucket["win_rate"] > best_win_rate:
                best_win_rate = bucket["win_rate"]
                best_posture = (dim, val, bucket["wins"], bucket["appearances"])
    if best_posture and best_win_rate >= 0.60:
        dim, val, wins, apps = best_posture
        headlines.append({
            "headline_id": f"meta_posture_{season_id}",
            "category": "meta_report",
            "headline_text": (
                f"{val.replace('_', ' ').title()} went {wins}-{apps - wins} across "
                f"the pyramid — the meta is forming."
            ),
            "entity_ids": [],
        })

    # Trend 3: highest-scoring division by avg game-point margin.
    divs_with_margin = [
        (d, v["avg_game_point_margin"]) for d, v in by_division.items() if v["match_count"] > 0
    ]
    if divs_with_margin:
        divs_with_margin.sort(key=lambda x: x[1], reverse=True)
        top_div, top_margin = divs_with_margin[0]
        headlines.append({
            "headline_id": f"meta_margin_{season_id}",
            "category": "meta_report",
            "headline_text": (
                f"{_division_display_name(top_div)} matches averaged a {top_margin:.1f} "
                f"game-point margin — the tightest or widest finishes in the world."
            ),
            "entity_ids": [],
        })

    if headlines:
        save_news_headlines(conn, season_id, 0, headlines)
        conn.commit()


__all__ = [
    "compute_league_trends",
    "generate_league_bulletin",
]
