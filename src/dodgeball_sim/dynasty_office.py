from __future__ import annotations

import json
import sqlite3
from typing import Any

from .config import DEFAULT_SCOUTING_CONFIG
from .game_loop import current_week
from .persistence import (
    CorruptSaveError,
    get_state,
    load_all_rosters,
    load_awards,
    load_club_facilities,
    load_club_prestige,
    load_clubs,
    load_command_history,
    load_department_heads,
    load_json_state,
    load_league_records,
    load_playoff_bracket,
    load_prospect_pool,
    load_rivalry_records,
    load_season,
    set_state,
)
from .recruitment import generate_prospect_pool
from .rng import DeterministicRNG, derive_seed


PROMISE_STATE_KEY = "program_promises_json"
STAFF_ACTION_STATE_KEY = "staff_market_actions_json"
MAX_ACTIVE_PROMISES = 3
PROMISE_OPTIONS = (
    "early_playing_time",
    "development_priority",
    "contender_path",
)


def _ensure_dynasty_keys(conn: sqlite3.Connection) -> None:
    for key in (PROMISE_STATE_KEY, STAFF_ACTION_STATE_KEY):
        row = conn.execute(
            "SELECT value FROM dynasty_state WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            set_state(conn, key, "[]")
        else:
            try:
                json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                raise CorruptSaveError(f"Corrupted dynasty state key: {key}")


def build_dynasty_office_state(conn: sqlite3.Connection) -> dict[str, Any]:
    _ensure_dynasty_keys(conn)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id or not player_club_id:
        raise ValueError("No active season or player club")

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    history = load_command_history(conn, season_id)
    root_seed = _root_seed(conn)
    week = current_week(conn, season) or 0
    return {
        "season_id": season_id,
        "week": week,
        "player_club_id": player_club_id,
        "player_club_name": clubs[player_club_id].name if player_club_id in clubs else player_club_id,
        "recruiting": _recruiting_state(conn, season_id, player_club_id, root_seed, history),
        "league_memory": _league_memory_state(conn, season_id, clubs),
        "staff_market": _staff_market_state(conn, season_id, player_club_id, root_seed),
    }


def save_recruiting_promise(
    conn: sqlite3.Connection,
    player_id: str,
    promise_type: str,
) -> dict[str, Any]:
    _ensure_dynasty_keys(conn)
    if promise_type not in PROMISE_OPTIONS:
        raise ValueError(f"Unknown promise type: {promise_type}")
    promises = _load_promises(conn)
    open_promises = [promise for promise in promises if promise.get("status") == "open"]
    if len(open_promises) >= MAX_ACTIVE_PROMISES and not any(p.get("player_id") == player_id for p in open_promises):
        raise ValueError(f"Only {MAX_ACTIVE_PROMISES} active promises may be open")

    next_promises = [promise for promise in promises if promise.get("player_id") != player_id]
    next_promises.append(
        {
            "player_id": player_id,
            "promise_type": promise_type,
            "status": "open",
            "result": None,
            "result_season_id": None,
            "evidence": "Will be checked against future command history and player match stats.",
        }
    )
    set_state(conn, PROMISE_STATE_KEY, json.dumps(next_promises))
    conn.commit()
    return build_dynasty_office_state(conn)


def hire_staff_candidate(conn: sqlite3.Connection, candidate_id: str) -> dict[str, Any]:
    _ensure_dynasty_keys(conn)
    state = build_dynasty_office_state(conn)
    candidates = state["staff_market"]["candidates"]
    candidate = next((item for item in candidates if item["candidate_id"] == candidate_id), None)
    if candidate is None:
        raise ValueError(f"Unknown staff candidate: {candidate_id}")

    conn.execute(
        """
        INSERT OR REPLACE INTO department_heads
            (department, name, rating_primary, rating_secondary, voice)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            candidate["department"],
            candidate["name"],
            float(candidate["rating_primary"]),
            float(candidate["rating_secondary"]),
            candidate["voice"],
        ),
    )
    actions = _load_staff_actions(conn)
    actions.insert(
        0,
        {
            "candidate_id": candidate["candidate_id"],
            "department": candidate["department"],
            "name": candidate["name"],
            "effect_lanes": candidate["effect_lanes"],
        },
    )
    set_state(conn, STAFF_ACTION_STATE_KEY, json.dumps(actions[:8]))
    conn.commit()
    return build_dynasty_office_state(conn)


def _recruiting_state(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    root_seed: int,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    promises = _load_promises(conn)
    credibility = _credibility(conn, season_id, player_club_id, history)
    prospects = _prospect_rows(conn, season_id, root_seed, promises, credibility)
    return {
        "credibility": credibility,
        "active_promises": promises,
        "prospects": prospects,
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
    del season_id
    prestige = load_club_prestige(conn, player_club_id)
    wins = sum(1 for item in history if item.get("dashboard", {}).get("result") == "Win")
    losses = sum(1 for item in history if item.get("dashboard", {}).get("result") == "Loss")
    youth_weeks = sum(
        1
        for item in history
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

    # Source of truth: persisted pool (same one Recruitment Day uses)
    persisted = load_prospect_pool(conn, class_year)
    if persisted:
        prospects = persisted
    else:
        # Fallback: generate using the identical seed the scouting center will use
        rng = DeterministicRNG(derive_seed(root_seed, "prospect_gen", str(class_year)))
        prospects = generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG)
    promised = {promise["player_id"]: promise for promise in promises}
    rows = []
    for prospect in prospects[:8]:
        low, high = prospect.public_ratings_band["ovr"]
        fit_score = round(((low + high) / 2.0) + credibility["score"] * 0.12, 1)
        rows.append(
            {
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
            }
        )
    return rows


def _league_memory_state(conn: sqlite3.Connection, season_id: str, clubs: dict[str, Any]) -> dict[str, Any]:
    awards = load_awards(conn, season_id)
    record_items = load_league_records(conn)
    rivalry_items = load_rivalry_records(conn)
    recent_matches = conn.execute(
        """
        SELECT match_id, week, home_club_id, away_club_id, winner_club_id, home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 6
        """,
        (season_id,),
    ).fetchall()
    return {
        "records": {
            "items": [
                _record_item(item) for item in record_items
            ]
            or [{"status": "limited", "text": "The league record books are currently empty. History begins when the first records are ratified."}],
        },
        "awards": {
            "items": [
                {
                    "award_type": award.award_type,
                    "player_id": award.player_id,
                    "club_name": clubs.get(award.club_id).name if award.club_id in clubs else award.club_id,
                    "score": award.award_score,
                }
                for award in awards
            ]
            or [{"status": "limited", "text": "The trophy cabinet awaits. Season awards will be decided and displayed after the offseason closeout."}],
        },
        "rivalries": {
            "items": [
                {
                    "club_a_name": clubs.get(item["club_a_id"]).name if item["club_a_id"] in clubs else item["club_a_id"],
                    "club_b_name": clubs.get(item["club_b_id"]).name if item["club_b_id"] in clubs else item["club_b_id"],
                    "score": item["rivalry"].get("rivalry_score", 0),
                    "meetings": item["rivalry"].get("total_meetings", 0),
                }
                for item in rivalry_items
            ]
            or [{"status": "limited", "text": "True rivalries require history. Bad blood will build here after repeated, high-stakes match results."}],
        },
        "recent_matches": [_recent_match_item(row, clubs) for row in recent_matches],
    }


def _staff_market_state(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    root_seed: int,
) -> dict[str, Any]:
    current_staff = load_department_heads(conn)
    facilities = load_club_facilities(conn, player_club_id, season_id)
    recent_actions = _load_staff_actions(conn)
    filled_departments = {action.get("department") for action in recent_actions}
    candidates = [
        _candidate_for_head(head, root_seed, season_id)
        for head in current_staff
        if head["department"] not in filled_departments
    ]
    return {
        "current_staff": current_staff,
        "active_facilities": facilities,
        "candidates": candidates,
        "recent_actions": recent_actions,
        "rules": {
            "honesty": "Staff upgrades are already reshaping our weekly training plans and scouting coverage.",
        },
    }


def _candidate_for_head(head: dict[str, Any], root_seed: int, season_id: str) -> dict[str, Any]:
    department = head["department"]
    rng = DeterministicRNG(derive_seed(root_seed, "staff_market", season_id, department))
    primary_gain = round(rng.roll(3.0, 9.0), 1)
    secondary_gain = round(rng.roll(1.0, 7.0), 1)
    primary = round(min(99.0, float(head["rating_primary"]) + primary_gain), 1)
    secondary = round(min(99.0, float(head["rating_secondary"]) + secondary_gain), 1)
    name = f"{_staff_first_name(rng)} {_staff_last_name(rng)}"
    return {
        "candidate_id": f"{season_id}_{department}_candidate",
        "department": department,
        "name": name,
        "rating_primary": primary,
        "rating_secondary": secondary,
        "voice": _staff_voice(department, rng),
        "effect_lanes": _staff_effect_lanes(department, primary, secondary),
    }


def _staff_effect_lanes(department: str, primary: float, secondary: float) -> list[str]:
    labels = {
        "tactics": "Tactics recommendations and replay-proof preparation.",
        "training": "Development focus advice and player-growth reporting.",
        "conditioning": "Fatigue-risk recommendations and recovery planning.",
        "medical": "Availability warnings and overuse-risk reporting.",
        "scouting": "Recruiting fit explanations and prospect board clarity.",
        "culture": "Promise-risk framing and command-plan stability.",
    }
    return [
        labels.get(department, "Program recommendations."),
        f"Visible staff ratings would become {primary:.1f}/{secondary:.1f}.",
    ]


def evaluate_season_promises(
    conn: sqlite3.Connection,
    season_id: str,
    club_id: str,
) -> None:
    """Evaluate open promises for the season and persist fulfilled/broken results.

    Safe to call multiple times — already-evaluated promises are skipped.
    Must be called before retirements so load_all_rosters() reflects pre-retirement state.
    """
    promises = _load_promises(conn)
    if not promises:
        return

    changed = False
    for promise in promises:
        if promise.get("result_season_id") == season_id:
            continue  # already evaluated this season — idempotent
        if promise.get("status") != "open":
            continue

        player_id = promise.get("player_id")
        if not player_id:
            promise["result"] = "broken"
            promise["result_season_id"] = season_id
            promise["evidence"] = "Legacy promise — player identity not recorded."
            changed = True
            continue

        promise_type = promise.get("promise_type", "")
        result, evidence = _evaluate_one_promise(
            conn, season_id, club_id, player_id, promise_type
        )
        promise["result"] = result
        promise["result_season_id"] = season_id
        promise["evidence"] = evidence
        changed = True

    if changed:
        set_state(conn, PROMISE_STATE_KEY, json.dumps(promises))
        conn.commit()


def _evaluate_one_promise(
    conn: sqlite3.Connection,
    season_id: str,
    club_id: str,
    player_id: str,
    promise_type: str,
) -> tuple[str, str]:
    """Return (result, evidence_text) for a single promise."""
    if promise_type == "early_playing_time":
        count = conn.execute(
            """
            SELECT COUNT(*) FROM player_match_stats pms
            JOIN match_records mr ON mr.match_id = pms.match_id
            WHERE mr.season_id = ? AND pms.player_id = ?
            """,
            (season_id, player_id),
        ).fetchone()[0]
        if count >= 6:
            return "fulfilled", f"Player appeared in {count} matches this season (threshold: 6)."
        return "broken", f"Player appeared in only {count} matches this season (threshold: 6)."

    if promise_type == "development_priority":
        history = load_command_history(conn, season_id)
        focused_weeks = sum(
            1 for entry in history
            if entry.get("plan", {}).get("department_orders", {}).get("dev_focus", "BALANCED") != "BALANCED"
        )
        rosters = load_all_rosters(conn)
        club_roster = rosters.get(club_id, [])
        on_roster = any(p.id == player_id for p in club_roster)
        if focused_weeks >= 3 and on_roster:
            return (
                "fulfilled",
                f"Club ran focused development {focused_weeks} weeks and player is on the active roster.",
            )
        reason = []
        if focused_weeks < 3:
            reason.append(f"only {focused_weeks} focused dev weeks (threshold: 3)")
        if not on_roster:
            reason.append("player not on active roster")
        return "broken", "Not fulfilled: " + "; ".join(reason) + "."

    if promise_type == "contender_path":
        bracket = load_playoff_bracket(conn, season_id)
        if bracket is not None and club_id in bracket.seeds:
            return "fulfilled", "Club reached the playoffs this season."
        return "broken", "Club did not reach the playoffs this season."

    return "broken", f"Unknown promise type '{promise_type}'."


def _load_promises(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return list(load_json_state(conn, PROMISE_STATE_KEY, []))


def _load_staff_actions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return list(load_json_state(conn, STAFF_ACTION_STATE_KEY, []))


def _root_seed(conn: sqlite3.Connection) -> int:
    try:
        return int(get_state(conn, "root_seed", "1") or "1")
    except ValueError:
        return 1


def _class_year_from_season(season_id: str) -> int:
    digits = "".join(ch for ch in season_id if ch.isdigit())
    return int(digits or "1") + 1


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


def _record_item(item: dict[str, Any]) -> dict[str, Any]:
    record = item.get("record", {})
    return {
        "record_type": item["record_type"],
        "holder_id": item["holder_id"],
        "holder_type": item["holder_type"],
        "value": item["record_value"],
        "season_id": item["set_in_season"],
        "text": record.get("detail") or f"{item['holder_id']} leads {item['record_type']}.",
    }


def _recent_match_item(row: sqlite3.Row, clubs: dict[str, Any]) -> dict[str, Any]:
    home = clubs.get(row["home_club_id"])
    away = clubs.get(row["away_club_id"])
    winner = clubs.get(row["winner_club_id"]) if row["winner_club_id"] else None
    return {
        "match_id": row["match_id"],
        "week": int(row["week"]),
        "summary": (
            f"{home.name if home else row['home_club_id']} {row['home_survivors']}-"
            f"{row['away_survivors']} {away.name if away else row['away_club_id']}"
        ),
        "winner_name": winner.name if winner else "Draw",
    }


def _staff_first_name(rng: DeterministicRNG) -> str:
    return rng.choice((
        "Ari", "Blair", "Carmen", "Dev", "Eli", "Juno", "Morgan", "Sasha",
        "Taylor", "Jordan", "Casey", "Riley", "Avery", "Quinn", "Peyton", "Skyler",
        "Dallas", "Reese", "Rowan", "Ellis", "Kendall", "Micah", "Emerson", "Finley"
    ))


def _staff_last_name(rng: DeterministicRNG) -> str:
    return rng.choice((
        "Vale", "Cross", "Hart", "Rook", "Sol", "Pike", "Ives", "Chen",
        "Gaines", "Mercer", "Vance", "Sutton", "Hayes", "Frost", "Graves", "Cole",
        "Bridges", "Stark", "Rivers", "Banks", "Shaw", "Kerr", "Brooks", "Glover"
    ))


def _staff_voice(department: str, rng: DeterministicRNG) -> str:
    voices = {
        "tactics": [
            "Make every matchup leave evidence.",
            "Execution beats raw talent when the plan is clear.",
            "We dictate the tempo, they react to the pressure.",
            "A rigid lineup is a vulnerable lineup."
        ],
        "training": [
            "Growth needs visible reps.",
            "Potential means nothing without court time.",
            "Drills build the floor; match minutes build the ceiling.",
            "We measure progress in successful catches, not promises."
        ],
        "conditioning": [
            "Late-match legs are earned early.",
            "Fatigue makes cowards of us all.",
            "We win the war of attrition in the practice gym.",
            "Stamina is the shield that protects our strategy."
        ],
        "medical": [
            "Availability is the quiet edge.",
            "I tell you who can play; you tell them how.",
            "Managing overuse is managing the season's fate.",
            "Don't risk a career for a single regular-season win."
        ],
        "scouting": [
            "Fit beats noise.",
            "We draft for the liabilities we can hide and the traits we can use.",
            "The tape never lies, even when the public hype does.",
            "I find the ceiling; you build the floor."
        ],
        "culture": [
            "Promises become program memory.",
            "Trust is built on fulfilled expectations.",
            "A fractured locker room will drop the ball when it matters most.",
            "Recruits watch how we treat our veterans."
        ]
    }
    options = voices.get(department, ["Build the program with proof."])
    return rng.choice(options)


__all__ = [
    "build_dynasty_office_state",
    "evaluate_season_promises",
    "hire_staff_candidate",
    "save_recruiting_promise",
]
