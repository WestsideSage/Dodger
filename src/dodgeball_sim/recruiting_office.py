from __future__ import annotations

import sqlite3
from typing import Any

from .config import DEFAULT_SCOUTING_CONFIG
from .persistence import (
    get_state,
    load_json_state,
    load_prospect_pool,
    load_season,
)
from .recruitment import generate_prospect_pool, get_current_recruiting_budget
from .rng import DeterministicRNG, derive_seed

PROMISE_STATE_KEY = "program_promises_json"
MAX_ACTIVE_PROMISES = 3
PROMISE_OPTIONS = (
    "early_playing_time",
    "development_priority",
    "contender_path",
)


def build_recruiting_state(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    root_seed: int,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    promises = list(load_json_state(conn, PROMISE_STATE_KEY, []))
    credibility = _credibility(conn, season_id, player_club_id, history)
    prospects = _prospect_rows(conn, season_id, root_seed, promises, credibility)
    week_val = 0
    row = conn.execute("SELECT value FROM dynasty_state WHERE key='career_week'").fetchone()
    if row:
        week_val = int(row[0])
    budget = get_current_recruiting_budget(conn, season_id, week_val)
    return {
        "credibility": credibility,
        "active_promises": promises,
        "prospects": prospects,
        "budget": budget,
        "rules": {
            "max_active_promises": MAX_ACTIVE_PROMISES,
            "promise_options": list(PROMISE_OPTIONS),
            "honesty": "Promise checks use command history, player match stats, and future roster usage only.",
        },
    }


def _credibility(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    from .persistence import load_club_prestige
    del season_id
    prestige = load_club_prestige(conn, player_club_id)
    wins = sum(1 for item in history if item.get("dashboard", {}).get("result") == "Win")
    losses = sum(1 for item in history if item.get("dashboard", {}).get("result") == "Loss")
    youth_weeks = sum(
        1 for item in history
        if item.get("plan", {}).get("department_orders", {}).get("dev_focus") == "YOUTH_ACCELERATION"
        or item.get("intent") == "Develop Youth"
    )
    score = max(0, min(100, 50 + prestige * 2 + wins * 4 - losses * 3 + youth_weeks * 2))
    evidence = [
        f"{wins} command-history wins and {losses} losses.",
        f"{youth_weeks} youth-development command weeks.",
        f"Club prestige score {prestige}.",
    ]
    if not history:
        evidence.append("No command history yet, so credibility starts from program baseline.")
    return {"score": score, "grade": _grade(score), "evidence": evidence}


def _prospect_rows(
    conn: sqlite3.Connection,
    season_id: str,
    root_seed: int,
    promises: list[dict[str, Any]],
    credibility: dict[str, Any],
) -> list[dict[str, Any]]:
    class_year = _class_year_from_season(season_id)
    persisted = load_prospect_pool(conn, class_year)
    if persisted:
        prospects = persisted
    else:
        rng = DeterministicRNG(derive_seed(root_seed, "prospect_gen", str(class_year)))
        prospects = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
    promised = {promise["player_id"]: promise for promise in promises}
    rows = []
    for prospect in prospects[:8]:
        low, high = prospect.public_ratings_band["ovr"]
        fit_score = round(((low + high) / 2.0) + credibility["score"] * 0.12, 1)
        rows.append({
            "player_id": prospect.player_id,
            "name": prospect.name,
            "hometown": prospect.hometown,
            "public_archetype": prospect.public_archetype_guess,
            "public_ovr_band": [low, high],
            "fit_score": fit_score,
            "promise_options": list(PROMISE_OPTIONS),
            "active_promise": promised.get(prospect.player_id),
            "interest_evidence": [
                f"Public range {low}-{high}.",
                f"Credibility grade {credibility['grade']} contributes to interest.",
                "No hidden promise effect is applied until a promise is saved.",
            ],
        })
    return rows


def _grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _class_year_from_season(season_id: str) -> int:
    digits = "".join(ch for ch in season_id if ch.isdigit())
    return int(digits or "1") + 1


__all__ = ["PROMISE_OPTIONS", "PROMISE_STATE_KEY", "MAX_ACTIVE_PROMISES", "build_recruiting_state"]
