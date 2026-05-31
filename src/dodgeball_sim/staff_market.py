from __future__ import annotations

import sqlite3
from typing import Any

from .config import DEFAULT_CONFIG
from .persistence import load_club_facilities, load_department_heads, load_json_state
from .rng import DeterministicRNG, derive_seed

STAFF_ACTION_STATE_KEY = "staff_market_actions_json"

# Honest per-department effect summary. Only the "training" lane currently has a
# real mechanical hook (offseason player development); the rest describe the
# recommendation surface that department drives. See the staff_market honesty
# rule below.
_STAFF_EFFECT_LABELS = {
    "tactics": "Tactics recommendations and replay-proof preparation.",
    "training": "Development focus advice and offseason player-growth impact.",
    "conditioning": "Fatigue-risk recommendations and recovery planning.",
    "medical": "Availability warnings and overuse-risk reporting.",
    "scouting": "Recruiting fit explanations and prospect board clarity.",
    "culture": "Promise-risk framing and command-plan stability.",
}


def staff_effect_summary(department: str) -> str:
    return _STAFF_EFFECT_LABELS.get(department, "Program recommendations.")


_MAX_STAFF_DEV_MOD: float = DEFAULT_CONFIG.max_staff_development_modifier


def _training_modifier_pct(rating_primary: float | int) -> int:
    """Return the rounded-percentage offseason dev modifier for a training head.
    Formula mirrors offseason_ceremony.py:493-494. Clamps at 0 (no penalty exposed)."""
    raw = max(0.0, (float(rating_primary) - 50.0) / 50.0 * _MAX_STAFF_DEV_MOD)
    return round(raw * 100)


def build_staff_market_state(
    conn: sqlite3.Connection,
    *,
    season_id: str,
    player_club_id: str,
    root_seed: int,
) -> dict[str, Any]:
    current_staff = [
        {
            **head,
            "rating_primary": round(float(head["rating_primary"])),
            "rating_secondary": round(float(head["rating_secondary"])),
            "effect_summary": staff_effect_summary(head["department"]),
            **(
                {"training_modifier_pct": _training_modifier_pct(head["rating_primary"])}
                if head["department"] == "training"
                else {}
            ),
        }
        for head in load_department_heads(conn)
    ]
    facilities = load_club_facilities(conn, player_club_id, season_id)
    recent_actions = list(load_json_state(conn, STAFF_ACTION_STATE_KEY, []))
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
            "honesty": "Training staff affects offseason player development now; scouting, recovery, and deeper staff economy effects remain explicit future hooks.",
        },
    }


def _candidate_for_head(head: dict[str, Any], root_seed: int, season_id: str) -> dict[str, Any]:
    department = head["department"]
    rng = DeterministicRNG(derive_seed(root_seed, "staff_market", season_id, department))
    primary_gain = round(rng.roll(3.0, 9.0), 1)
    secondary_gain = round(rng.roll(1.0, 7.0), 1)
    primary = round(min(99.0, float(head["rating_primary"]) + primary_gain))
    secondary = round(min(99.0, float(head["rating_secondary"]) + secondary_gain))
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


def _staff_effect_lanes(department: str, primary: int, secondary: int) -> list[str]:
    return [
        staff_effect_summary(department),
        f"Visible staff ratings would become {primary}/{secondary}.",
    ]


def _staff_first_name(rng: DeterministicRNG) -> str:
    return rng.choice(("Ari", "Blair", "Carmen", "Dev", "Eli", "Juno", "Morgan", "Sasha",
        "Taylor", "Jordan", "Casey", "Riley", "Avery", "Quinn", "Peyton", "Skyler",
        "Dallas", "Reese", "Rowan", "Ellis", "Kendall", "Micah", "Emerson", "Finley"))


def _staff_last_name(rng: DeterministicRNG) -> str:
    return rng.choice(("Vale", "Cross", "Hart", "Rook", "Sol", "Pike", "Ives", "Chen",
        "Gaines", "Mercer", "Vance", "Sutton", "Hayes", "Frost", "Graves", "Cole",
        "Bridges", "Stark", "Rivers", "Banks", "Shaw", "Kerr", "Brooks", "Glover"))


def _staff_voice(department: str, rng: DeterministicRNG) -> str:
    voices = {
        "tactics": ["Make every matchup leave evidence.", "Execution beats raw talent when the plan is clear.", "We dictate the tempo, they react to the pressure.", "A rigid lineup is a vulnerable lineup."],
        "training": ["Growth needs visible reps.", "Potential means nothing without court time.", "Drills build the floor; match minutes build the ceiling.", "We measure progress in successful catches, not promises."],
        "conditioning": ["Late-match legs are earned early.", "Fatigue makes cowards of us all.", "We win the war of attrition in the practice gym.", "Stamina is the shield that protects our strategy."],
        "medical": ["Availability is the quiet edge.", "I tell you who can play; you tell them how.", "Managing overuse is managing the season's fate.", "Don't risk a career for a single regular-season win."],
        "scouting": ["Fit beats noise.", "We draft for the liabilities we can hide and the traits we can use.", "The tape never lies, even when the public hype does.", "I find the ceiling; you build the floor."],
        "culture": ["Promises become program memory.", "Trust is built on fulfilled expectations.", "A fractured locker room will drop the ball when it matters most.", "Recruits watch how we treat our veterans."],
    }
    return rng.choice(voices.get(department, ["Build the program with proof."]))


__all__ = ["STAFF_ACTION_STATE_KEY", "build_staff_market_state", "staff_effect_summary"]
