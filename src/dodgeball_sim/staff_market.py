from __future__ import annotations

import sqlite3
from typing import Any

from .config import DEFAULT_CONFIG
from .persistence import load_club_facilities, load_department_heads, load_json_state
from .rng import DeterministicRNG, derive_seed

STAFF_ACTION_STATE_KEY = "staff_market_actions_json"

# Per-department effect summary. V22 Phase 4: every head's rating now has a
# real mechanical hook (see staff_effects for the formulas; the concrete
# per-head numbers ride on each card via staff_effect_detail).
_STAFF_EFFECT_LABELS = {
    "tactics": "Scales the tactics-focus week's effective-TIQ bonus.",
    "training": "Scales offseason player growth for the whole roster.",
    "conditioning": "Scales the conditioning-focus week's fatigue relief.",
    "medical": "Softens veteran age-decline each offseason.",
    "scouting": "Scales how tightly Scout actions narrow prospect bands.",
    "culture": "Scales the culture-focus week's courtship gains.",
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
    from .economy import hiring_frozen, staff_salary_k, treasury_k
    from .staff_effects import staff_effect_detail

    current_staff = [
        {
            **head,
            "rating_primary": round(float(head["rating_primary"])),
            "rating_secondary": round(float(head["rating_secondary"])),
            "effect_summary": staff_effect_summary(head["department"]),
            # V22 Phase 4: this head's concrete wired number.
            "effect_detail": staff_effect_detail(
                head["department"], head["rating_primary"]
            ),
            # V22 Phase 3: every head carries their annual salary so the
            # payroll delta of a hire is visible before the click.
            "salary_k": staff_salary_k(
                head["rating_primary"], head["rating_secondary"]
            ),
            **(
                {"training_modifier_pct": _training_modifier_pct(head["rating_primary"])}
                if head["department"] == "training"
                else {}
            ),
        }
        for head in load_department_heads(conn)
    ]
    # PT5 fix: on pyramid (web) saves, facilities are permanent owned buildings
    # in v26_owned_facilities_json (facilities_office), NOT the legacy per-season
    # club_facilities table that only the CLI pick-3 flow writes. Reading the
    # legacy table here made the Staff summary show "Facilities 0" even after a
    # web purchase the Facilities panel already showed as Built. Legacy
    # single-league saves keep the old table read (byte-identical).
    from .world import pyramid_world_active

    if pyramid_world_active(conn):
        from .facilities_office import owned_facilities

        facilities = owned_facilities(conn)
    else:
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
        # V22 Phase 3: the money context every hire decision needs.
        "treasury_k": treasury_k(conn),
        "hiring_frozen": hiring_frozen(conn),
        "payroll_k": sum(head["salary_k"] for head in current_staff),
        "rules": {
            # V22 Phase 4: all six heads carry real hooks now; the per-head
            # numbers are on each card. AI club staff stay abstracted (their
            # focus weeks run at the flat legacy strength).
            "honesty": "Every department head's rating drives a real effect — training scales offseason growth, medical softens age-decline, and tactics/conditioning/culture/scouting scale their focus-week payoffs. AI club staff are abstracted at standard strength.",
            "economy": "Salaries are paid from the club treasury every offseason. Hiring freezes while the treasury is negative.",
        },
    }


def _candidate_for_head(head: dict[str, Any], root_seed: int, season_id: str) -> dict[str, Any]:
    from .economy import staff_salary_k

    department = head["department"]
    rng = DeterministicRNG(derive_seed(root_seed, "staff_market", season_id, department))
    primary_gain = round(rng.roll(3.0, 9.0), 1)
    secondary_gain = round(rng.roll(1.0, 7.0), 1)
    primary = round(min(99.0, float(head["rating_primary"]) + primary_gain))
    secondary = round(min(99.0, float(head["rating_secondary"]) + secondary_gain))
    name = f"{_staff_first_name(rng)} {_staff_last_name(rng)}"
    salary = staff_salary_k(primary, secondary)
    current_salary = staff_salary_k(head["rating_primary"], head["rating_secondary"])
    return {
        "candidate_id": f"{season_id}_{department}_candidate",
        "department": department,
        "name": name,
        "rating_primary": primary,
        "rating_secondary": secondary,
        # V22 Phase 3: the hire's payroll consequences, disclosed up front.
        "salary_k": salary,
        "salary_delta_k": salary - current_salary,
        "voice": _staff_voice(department, rng),
        "effect_lanes": _staff_effect_lanes(department, primary, secondary)
        + [f"Annual salary ${salary}k (payroll {'+' if salary >= current_salary else ''}{salary - current_salary}k/season)."],
    }


def _staff_effect_lanes(department: str, primary: int, secondary: int) -> list[str]:
    from .staff_effects import staff_effect_detail

    return [
        staff_effect_summary(department),
        # V22 Phase 4: the candidate's CONCRETE wired number, from the same
        # formulas the engine consumes.
        staff_effect_detail(department, primary),
        f"Visible staff ratings would become {primary}/{secondary}.",
    ]


def _staff_first_name(rng: DeterministicRNG) -> str:
    # V22 Phase 1: staff draw from the same wide shared pools as players —
    # the old separate 24-name pool produced the same dozen coaches forever.
    from .names import FIRST_NAMES

    return rng.choice(FIRST_NAMES)


def _staff_last_name(rng: DeterministicRNG) -> str:
    from .names import LAST_NAMES

    return rng.choice(LAST_NAMES)


FOUNDING_DEPARTMENTS = (
    "tactics",
    "training",
    "conditioning",
    "medical",
    "scouting",
    "culture",
)

# Quality tiers for the founding pool: every department always offers a cheap
# journeyman (so filling all six is ALWAYS affordable), a solid mid-tier, and
# a premium hire whose salary commits real payroll. Ranges feed the V22
# economy salary formula (economy.staff_salary_k).
_FOUNDING_TIERS = (
    ("journeyman", (52.0, 60.0), (48.0, 58.0)),
    ("solid", (63.0, 72.0), (58.0, 70.0)),
    ("premium", (76.0, 88.0), (70.0, 84.0)),
)


def generate_founding_staff_pool(seed: int) -> list[dict[str, Any]]:
    """V22 Phase 3: the create-a-club staff market.

    Deterministic from the wizard's creation seed (same number the founding
    prospect pool uses, different namespace). Each of the six departments
    offers one candidate per quality tier; salaries come straight from the
    economy formula so the wizard's budget math and the offseason payroll
    are the same arithmetic.
    """
    from .economy import staff_salary_k
    from .names import unique_full_name
    from .staff_effects import staff_effect_detail

    rng = DeterministicRNG(derive_seed(seed, "founding_staff"))
    used_names: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for department in FOUNDING_DEPARTMENTS:
        for tier_name, primary_range, secondary_range in _FOUNDING_TIERS:
            primary = round(rng.roll(*primary_range))
            secondary = round(rng.roll(*secondary_range))
            name = unique_full_name(
                rng=rng, used_names=used_names, fallback_tag=f"{department}-{tier_name}"
            )
            candidates.append(
                {
                    "candidate_id": f"founding_{department}_{tier_name}",
                    "department": department,
                    "tier": tier_name,
                    "name": name,
                    "rating_primary": primary,
                    "rating_secondary": secondary,
                    "salary_k": staff_salary_k(primary, secondary),
                    "voice": _staff_voice(department, rng),
                    "effect_summary": staff_effect_summary(department),
                    # V22 Phase 4: the candidate's concrete wired number —
                    # the hiring decision is about THIS, not vibes.
                    "effect_detail": staff_effect_detail(department, primary),
                    **(
                        {"training_modifier_pct": _training_modifier_pct(primary)}
                        if department == "training"
                        else {}
                    ),
                }
            )
    return candidates


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


__all__ = [
    "FOUNDING_DEPARTMENTS",
    "STAFF_ACTION_STATE_KEY",
    "build_staff_market_state",
    "generate_founding_staff_pool",
    "staff_effect_summary",
]
