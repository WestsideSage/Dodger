from __future__ import annotations

import json
import sqlite3
from typing import Any

from .config import DEFAULT_SCOUTING_CONFIG
from .persistence import (
    load_career_state_cursor,
    load_json_state,
    load_prospect_pool,
    set_state,
)
from .recruiting_actions import Action, apply_action, current_interest, narrow_band
from .recruitment import generate_prospect_pool, get_current_recruiting_budget
from .rng import DeterministicRNG, derive_seed

PROMISE_STATE_KEY = "program_promises_json"
MAX_ACTIVE_PROMISES = 3
PROMISE_OPTIONS = (
    "early_playing_time",
    "development_priority",
    "contender_path",
)

# Canonical recruiting status values. Order matters in this list, but precedence
# is enforced explicitly in compute_recruiting_status() below.
RECRUITING_STATUSES = (
    "UNSCOUTED",
    "SCOUTED",
    "CONTACTED",
    "VISITED",
    "INTERESTED",
    "LOCKED_OUT",
)


def compute_recruiting_status(actions: dict[str, Any] | None) -> str:
    """Derive the canonical recruiting status for a prospect from its action flags.

    Precedence (highest wins):
        LOCKED_OUT > INTERESTED > VISITED > CONTACTED > SCOUTED > UNSCOUTED

    `actions` is the per-prospect dict stored in `prospect_recruitment_actions_json`,
    e.g. ``{"scouted": True, "contacted": True}``.

    Note: INTERESTED and LOCKED_OUT are reserved for future use once the domain
    has explicit signals for them. They are recognised here so that any
    explicitly-set flag of the same name is respected, but they are not
    currently derived implicitly.
    """
    if not actions:
        return "UNSCOUTED"
    if actions.get("locked_out"):
        return "LOCKED_OUT"
    if actions.get("interested"):
        return "INTERESTED"
    if actions.get("visited"):
        return "VISITED"
    if actions.get("contacted"):
        return "CONTACTED"
    if actions.get("scouted"):
        return "SCOUTED"
    return "UNSCOUTED"


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
    week_val = load_career_state_cursor(conn).week
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
        f"{wins} career command-history wins and {losses} losses.",
        f"{youth_weeks} youth-development command weeks across your career.",
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

    actions = load_json_state(conn, "prospect_recruitment_actions_json", {})

    rows = []
    for prospect in prospects[:8]:
        base_low, base_high = prospect.public_ratings_band["ovr"]
        pid = prospect.player_id
        p_actions = actions.get(pid, {})
        scouted = bool(p_actions.get("scouted"))
        low, high = narrow_band((base_low, base_high), scouted=scouted)
        fit_score = round(((low + high) / 2.0) + credibility["score"] * 0.12)
        interest = current_interest(
            p_actions,
            pipeline_tier=prospect.pipeline_tier,
            credibility_score=credibility["score"],
        )
        rows.append({
            "player_id": pid,
            "name": prospect.name,
            "hometown": prospect.hometown,
            "public_archetype": prospect.public_archetype_guess,
            "public_ovr_band": [low, high],
            "fit_score": fit_score,
            "interest": interest,
            "promise_options": list(PROMISE_OPTIONS),
            "active_promise": promised.get(pid),
            "interest_evidence": [
                f"Public range {low}-{high}{' (scouted)' if scouted else ''}.",
                f"Pipeline Tier {prospect.pipeline_tier} base interest.",
                f"Interest {interest}% — contact and visits build it.",
                f"Credibility grade {credibility['grade']} contributes to interest.",
            ],
            "pipeline_tier": prospect.pipeline_tier,
            "scouted": scouted,
            "contacted": bool(p_actions.get("contacted")),
            "visited": bool(p_actions.get("visited")),
            "recruiting_status": compute_recruiting_status(p_actions),
        })
    return rows


def _credibility_score(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    history: list[dict[str, Any]],
) -> int:
    return int(_credibility(conn, season_id, player_club_id, history)["score"])


def apply_recruiting_action(
    conn: sqlite3.Connection,
    *,
    prospect_id: str,
    action: Action,
    season_id: str,
    player_club_id: str,
    root_seed: int,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply a scout/contact/visit to a prospect and return the visible delta.

    Persists the updated per-prospect action state (flags + interest) and
    returns a ``RecruitingActionResult`` dict so the caller can show the player
    exactly what changed. See :mod:`recruiting_actions` for the effect model.
    """
    class_year = _class_year_from_season(season_id)
    persisted = load_prospect_pool(conn, class_year)
    if persisted:
        prospects = persisted
    else:
        rng = DeterministicRNG(derive_seed(root_seed, "prospect_gen", str(class_year)))
        prospects = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
    prospect = next((p for p in prospects if p.player_id == prospect_id), None)
    if prospect is None:
        raise ValueError(f"Unknown prospect: {prospect_id}")

    actions = load_json_state(conn, "prospect_recruitment_actions_json", {})
    state = actions.get(prospect_id, {})
    base_band = tuple(prospect.public_ratings_band["ovr"])
    credibility_score = _credibility_score(conn, season_id, player_club_id, history)

    new_state, result = apply_action(
        state,
        action,
        base_band=base_band,
        pipeline_tier=prospect.pipeline_tier,
        credibility_score=credibility_score,
    )
    actions[prospect_id] = new_state
    set_state(conn, "prospect_recruitment_actions_json", json.dumps(actions))
    return result.to_dict()


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
    """Class year the in-season recruiting board targets.

    This must match the class the offseason actually signs from
    (``offseason_service`` / ``offseason_ceremony`` use ``season_number``), so
    the Scout/Contact/Visit interest a player builds during the season lands on
    the same prospects they can sign afterward. Previously this returned
    ``season + 1``, pointing the board at a different (unsigned) class so all
    in-season recruiting effort was cosmetic.
    """
    digits = "".join(ch for ch in season_id if ch.isdigit())
    return int(digits or "1")


__all__ = [
    "PROMISE_OPTIONS",
    "PROMISE_STATE_KEY",
    "MAX_ACTIVE_PROMISES",
    "RECRUITING_STATUSES",
    "build_recruiting_state",
    "compute_recruiting_status",
    "apply_recruiting_action",
]
