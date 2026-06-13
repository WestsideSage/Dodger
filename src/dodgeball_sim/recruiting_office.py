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
from .recruiting_actions import (
    Action,
    apply_action,
    current_interest,
    narrow_band,
    scouted_band_from_state,
)
from .recruitment import generate_prospect_pool, get_current_recruiting_budget
from .rng import DeterministicRNG, derive_seed

PROMISE_STATE_KEY = "program_promises_json"
# PT4-05: week-stamped log of the user's scout/contact/visit actions, the
# derivation source for the post-week Prospect Pulse (capped at 120 entries).
RECRUITING_WEEK_LOG_KEY = "recruiting_week_log_json"
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
    prospects = _prospect_rows(conn, season_id, root_seed, promises, credibility, player_club_id)
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
    # V19b: the promise record is a real credibility consumer — kept promises
    # build trust, broken ones cost more (recruiting reputations work that
    # way). Capped so the record shades, never dominates, the win/prestige
    # base. This closes the loop the owner asked for: promise results ->
    # credibility -> prospect interest -> your contested Signing Day offer.
    promises = list(load_json_state(conn, PROMISE_STATE_KEY, []))
    kept = sum(1 for p in promises if p.get("status") == "fulfilled")
    broken = sum(1 for p in promises if p.get("status") == "broken")
    promise_delta = max(-15, min(15, kept * 4 - broken * 6))
    score = max(
        0,
        min(100, 50 + prestige * 2 + wins * 4 - losses * 3 + youth_weeks * 2 + promise_delta),
    )
    evidence = [
        f"{wins} wins and {losses} losses across your career.",
        f"{youth_weeks} week{'' if youth_weeks == 1 else 's'} spent prioritizing youth development.",
        f"Club prestige: {prestige} (a long-term score earned from titles and facilities).",
    ]
    if kept or broken:
        evidence.append(
            f"Promise record: {kept} kept, {broken} broken "
            f"({promise_delta:+d} credibility — kept promises build trust, broken ones cost more)."
        )
    if not history:
        evidence.append("No match history yet — credibility starts from the program baseline.")
    return {"score": score, "grade": _grade(score), "evidence": evidence}


def _motivation_fields(ctx, prospect, scouted: bool) -> dict[str, Any]:
    """V24 board motivation view: the prospect's visible cared-about grades, plus
    his dealbreaker (revealed only once scouted). Empty on legacy (no context)."""
    if ctx is None:
        return {"motivations": [], "dealbreaker": None, "fit": None}
    from .motivations import club_fit

    fit = club_fit(ctx, prospect)
    visible = [
        {"motivation": g.motivation, "label": g.label, "letter": g.letter, "receipt": g.receipt}
        for g in fit.grades.values()
        if g.cared and g.motivation != fit.dealbreaker
    ]
    dealbreaker = None
    if scouted:
        g = fit.grades[fit.dealbreaker]
        dealbreaker = {
            "motivation": g.motivation,
            "label": g.label,
            "letter": g.letter,
            "receipt": g.receipt,
            "veto": fit.veto,
        }
    return {"motivations": visible, "dealbreaker": dealbreaker, "fit": round(fit.fit, 4)}


def _prospect_rows(
    conn: sqlite3.Connection,
    season_id: str,
    root_seed: int,
    promises: list[dict[str, Any]],
    credibility: dict[str, Any],
    player_club_id: str,
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

    # V24 motivations (pyramid only): grade the user club's fit once per
    # prospect; legacy single-league saves get no motivation context.
    motivation_ctx = None
    from .world import pyramid_world_active

    if pyramid_world_active(conn):
        from .motivations import build_club_context

        motivation_ctx = build_club_context(conn, player_club_id, season_id)

    rows = []
    for prospect in prospects[:8]:
        base_low, base_high = prospect.public_ratings_band["ovr"]
        pid = prospect.player_id
        p_actions = actions.get(pid, {})
        scouted = bool(p_actions.get("scouted"))
        # V22 Phase 4: the band persisted at scout time (scaled by the
        # scouting head who ran it); legacy states fall back to the default
        # narrowing.
        low, high = scouted_band_from_state(p_actions, (base_low, base_high))
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
                f"Interest {interest}% strengthens your Signing Day offer — contact and visits build it.",
                f"Credibility grade {credibility['grade']} contributes to interest.",
            ],
            "pipeline_tier": prospect.pipeline_tier,
            "scouted": scouted,
            # Playtest 3 (owner-approved elite reveal): the Scout action also
            # grades the prospect's growth arc — the coarse ceiling label the
            # development engine's trajectory actually delivers (HIGH_CEILING
            # = STAR/GENERATIONAL floor 90+, SOLID = IMPACT floor 82+,
            # STANDARD = their natural ceiling only). Hidden until scouted;
            # the exact trajectory tier is never leaked.
            "ceiling_label": _scouted_ceiling_label(prospect, scouted),
            "contacted": bool(p_actions.get("contacted")),
            "visited": bool(p_actions.get("visited")),
            "recruiting_status": compute_recruiting_status(p_actions),
            **_motivation_fields(motivation_ctx, prospect, scouted),
        })
    return rows


def _scouted_ceiling_label(prospect, scouted: bool) -> str | None:
    """The trajectory-gated ceiling grade, revealed only by the Scout action."""
    if not scouted:
        return None
    from .scouting_center import ceiling_label_for_trajectory

    try:
        return ceiling_label_for_trajectory(prospect.hidden_trajectory)
    except ValueError:
        return None


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
    interest_gain_multiplier: float = 1.0,
) -> dict[str, Any]:
    """Apply a scout/contact/visit to a prospect and return the visible delta.

    Persists the updated per-prospect action state (flags + interest) and
    returns a ``RecruitingActionResult`` dict so the caller can show the player
    exactly what changed. See :mod:`recruiting_actions` for the effect model.
    ``interest_gain_multiplier`` is the V19b "culture" staff-focus bonus
    (contact/visit gains land warmer during a culture week).
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

    # V22 Phase 4: the SCOUTING head's quality scales how tightly this scout
    # narrows the band (staff_effects.scouting_band_quality, 0.70-1.30).
    from .persistence import load_department_heads
    from .staff_effects import scouting_band_quality

    scouting_head = next(
        (h for h in load_department_heads(conn) if h["department"] == "scouting"),
        None,
    )
    scout_quality = scouting_band_quality(
        scouting_head["rating_primary"] if scouting_head else 50.0
    )

    new_state, result = apply_action(
        state,
        action,
        base_band=base_band,
        pipeline_tier=prospect.pipeline_tier,
        credibility_score=credibility_score,
        gain_multiplier=interest_gain_multiplier,
        scout_quality=scout_quality,
    )
    actions[prospect_id] = new_state
    set_state(conn, "prospect_recruitment_actions_json", json.dumps(actions))

    # PT4-05: week-stamp every action so the post-week debrief's Prospect
    # Pulse can report the recruiting work that actually happened this week
    # (it claimed "no prospect movement" forever — the reactions list was
    # never fed). Derivation source for use_cases.recruit_reactions_for_week.
    from .persistence import load_career_state_cursor

    cursor = load_career_state_cursor(conn)
    log = load_json_state(conn, RECRUITING_WEEK_LOG_KEY, [])
    if not isinstance(log, list):
        log = []
    log.append(
        {
            "season_id": season_id,
            "week": int(cursor.week or 0),
            "prospect_id": prospect_id,
            "prospect_name": prospect.name,
            "action": str(action),
            "interest_before": result.interest_before,
            "interest_after": result.interest_after,
            "headline": result.headline,
        }
    )
    set_state(conn, RECRUITING_WEEK_LOG_KEY, json.dumps(log[-120:]))
    return result.to_dict()


def recruit_reactions_for_week(
    conn: sqlite3.Connection, season_id: str, week: int
) -> list[dict[str, Any]]:
    """Prospect Pulse rows for one week, aggregated per prospect.

    Derived from the week-stamped action log (PT4-05) in the exact shape the
    aftermath FalloutGrid renders: ``prospect_name`` / ``interest_delta``
    (signed string) / ``evidence``. Scout-only weeks report the band
    narrowing instead of a phantom interest change. Empty when the player
    genuinely took no recruiting action that week — the "no movement" empty
    state is then true.
    """
    log = load_json_state(conn, RECRUITING_WEEK_LOG_KEY, [])
    if not isinstance(log, list):
        return []
    _VERBS = {"scout": "scouted", "contact": "contacted", "visit": "visited"}
    per_prospect: dict[str, dict[str, Any]] = {}
    for entry in log:
        if not isinstance(entry, dict):
            continue
        if entry.get("season_id") != season_id:
            continue
        if int(entry.get("week") or -1) != int(week):
            continue
        prospect_id = str(entry.get("prospect_id") or "")
        slot = per_prospect.setdefault(
            prospect_id,
            {
                "prospect_id": prospect_id,
                "prospect_name": entry.get("prospect_name") or prospect_id,
                "interest_first": entry.get("interest_before", 0),
                "interest_last": entry.get("interest_after", 0),
                "actions": [],
                "headline": "",
            },
        )
        slot["interest_last"] = entry.get("interest_after", slot["interest_last"])
        slot["actions"].append(str(entry.get("action") or ""))
        slot["headline"] = entry.get("headline") or slot["headline"]

    reactions: list[dict[str, Any]] = []
    for slot in per_prospect.values():
        delta = int(slot["interest_last"]) - int(slot["interest_first"])
        verbs = ", ".join(_VERBS.get(action, action) for action in slot["actions"])
        if delta != 0:
            evidence = (
                f"{verbs.capitalize()} this week — interest "
                f"{slot['interest_first']}% → {slot['interest_last']}%."
            )
        else:
            evidence = f"{verbs.capitalize()} this week — {slot['headline']}"
        reactions.append(
            {
                "prospect_id": slot["prospect_id"],
                "prospect_name": slot["prospect_name"],
                "interest_delta": f"{delta:+d}%",
                "evidence": evidence,
            }
        )
    reactions.sort(
        key=lambda r: (-abs(int(r["interest_delta"].rstrip('%'))), r["prospect_name"])
    )
    return reactions


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
