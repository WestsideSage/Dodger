from __future__ import annotations

import json
import sqlite3
from typing import Any

from .config import DEFAULT_SCOUTING_CONFIG
from .persistence import (
    get_state,
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
    from .world import pyramid_world_active

    network = scouting_network_status(conn) if pyramid_world_active(conn) else None
    return {
        "credibility": credibility,
        "active_promises": promises,
        "prospects": prospects,
        "budget": budget,
        "scouting_network": network,
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
    # V26: a media mini-event choice can grant a one-season credibility bonus
    # (effects land only in fans/prestige/credibility — never match outcomes).
    from .media_events import media_credibility_bonus

    media_bonus = media_credibility_bonus(conn)
    # V27: an invitational champion's prospect-showcase warmth is a SECOND
    # one-season credibility bonus on a SEPARATE state key
    # (v27_invitational_warmth — NOT v26_credibility_bonus) so a media bonus
    # and an invitational warmth in the same offseason both reach recruiting
    # SUMMED, never clobbering each other. Both reset next offseason init.
    from .invitationals import invitational_warmth

    warmth_bonus = invitational_warmth(conn)
    score = max(
        0,
        min(
            100,
            50
            + prestige * 2
            + wins * 4
            - losses * 3
            + youth_weeks * 2
            + promise_delta
            + media_bonus
            + warmth_bonus,
        ),
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


# V24: how many of the wide pyramid class the in-season board surfaces (the
# vision's ~25-prospect battle view, up from the old hard cap of 8). Deeper
# visibility into the full class is the money-gated scouting network (a later
# phase).
_RECRUIT_BOARD_SIZE = 25
# V24 Phase 6: how many tantalizing "names beyond your network" the board tails
# on so the Scouting Network upgrade has a visible payoff.
_HIDDEN_TEASER_CAP = 6
_REACH_ORDER = {"DISTRICT": 0, "REGIONAL": 1, "NATIONAL": 2}
# Per-club Scouting Network level (the user club; AI clubs derive theirs by tier).
NETWORK_LEVEL_STATE_KEY = "scouting_network_level"


def network_level(conn) -> int:
    """The user club's Scouting Network level.

    An explicit upgrade (persisted) wins. Otherwise the STARTING level scales
    with the club's division tier (the vision's "takeover inherits reach,
    founding starts local"): Premier/Circuit clubs already run an L3 national
    network; a D3 founder starts at L1 and must invest to widen it. This keeps a
    big-club takeover from being blinded to the very class it should dominate.
    """
    raw = get_state(conn, NETWORK_LEVEL_STATE_KEY)
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    return _default_network_level_for_user(conn)


def _default_network_level_for_user(conn) -> int:
    from .config import AI_NETWORK_LEVEL_BY_TIER, NETWORK_DEFAULT_LEVEL, NETWORK_MAX_LEVEL
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        return NETWORK_MAX_LEVEL  # legacy single-league: no reach gating
    season_id = get_state(conn, "active_season_id")
    club_id = get_state(conn, "player_club_id")
    if not season_id or not club_id:
        return NETWORK_DEFAULT_LEVEL
    from .persistence import load_division_map

    seat = load_division_map(conn, season_id).get(club_id)
    tier = seat.tier if seat is not None else None
    return AI_NETWORK_LEVEL_BY_TIER.get(int(tier or 0), NETWORK_DEFAULT_LEVEL)


def _scouting_head_rating(conn) -> float:
    from .persistence import load_department_heads

    head = next(
        (h for h in load_department_heads(conn) if h["department"] == "scouting"), None
    )
    return float(head["rating_primary"]) if head else 50.0


def scouting_network_status(conn) -> dict[str, Any]:
    """The network panel payload: current level, the next upgrade's level + cost
    (staff-compressed), and whether the treasury can afford it."""
    from .economy import treasury_k
    from .scouting_network import network_upgrade_cost, next_network_level

    level = network_level(conn)
    to_level = next_network_level(level)
    treasury = treasury_k(conn)
    cost = (
        network_upgrade_cost(
            to_level=to_level, scouting_head_rating=_scouting_head_rating(conn)
        )
        if to_level is not None
        else None
    )
    return {
        "level": level,
        "next_level": to_level,
        "upgrade_cost_k": cost,
        "treasury_k": treasury,
        "can_afford": bool(cost is not None and treasury >= cost),
        "maxed": to_level is None,
    }


def upgrade_scouting_network(conn) -> dict[str, Any]:
    """Spend treasury to raise the network one level (the Phase 6 treasury sink).

    Refuses at max level or when the treasury cannot cover the staff-compressed
    cost (squeeze, never a spiral — you cannot go negative on an upgrade)."""
    from .economy import set_treasury_k, treasury_k
    from .scouting_network import network_upgrade_cost, next_network_level

    level = network_level(conn)
    to_level = next_network_level(level)
    if to_level is None:
        raise ValueError("Your Scouting Network is already at L3 — full national reach.")
    cost = network_upgrade_cost(
        to_level=to_level, scouting_head_rating=_scouting_head_rating(conn)
    )
    treasury = treasury_k(conn)
    if treasury < cost:
        raise ValueError(
            f"Upgrading to L{to_level} costs ${cost}k; your treasury holds ${treasury}k."
        )
    set_treasury_k(conn, treasury - cost)
    set_state(conn, NETWORK_LEVEL_STATE_KEY, str(to_level))
    return {"level": to_level, "cost_k": cost, "treasury_k": treasury - cost}


def _prospect_network_visible(conn, prospect, player_club_id: str) -> bool:
    """Whether the user's current network opens this single prospect's sheet."""
    from .persistence import load_clubs
    from .scouting_network import prospect_fully_visible, reach_band_for_trajectory
    from .world import district_neighbors

    from .world import DISTRICT_REGIONS

    club = load_clubs(conn).get(player_club_id)
    home = getattr(club, "home_region", "") or ""
    return prospect_fully_visible(
        reach_band=reach_band_for_trajectory(prospect.hidden_trajectory),
        hometown=prospect.hometown,
        level=network_level(conn),
        home_district=home,
        neighbors=district_neighbors(home),
        home_recognized=home in DISTRICT_REGIONS,
    )


def _name_only_row(prospect, reach_band: str, on_focus: bool) -> dict[str, Any]:
    """A redacted board card for a prospect beyond your Scouting Network reach:
    name + district only, no sheet, no actions (the vision's 'name without a
    sheet'). The hint says exactly which level opens him."""
    needed = 3 if reach_band == "NATIONAL" else 2
    return {
        "player_id": prospect.player_id,
        "name": prospect.name,
        "hometown": prospect.hometown,
        "fully_visible": False,
        "reach_band": reach_band,
        "visibility_hint": (
            f"{reach_band.title()}-reach prospect — raise your Scouting Network to "
            f"L{needed} to open his sheet."
        ),
        "public_archetype": None,
        "public_ovr_band": None,
        "fit_score": None,
        "interest": None,
        "promise_options": [],
        "active_promise": None,
        "interest_evidence": [],
        "pipeline_tier": None,
        "scouted": False,
        "ceiling_label": None,
        "contacted": False,
        "visited": False,
        "recruiting_status": "UNSCOUTED",
        "funnel_stage": None,
        "on_focus_list": on_focus,
        "can_contact": False,
        "can_visit": False,
        "visit_fixture": None,
        "market_signal": None,
        "motivations": [],
        "dealbreaker": None,
        "fit": None,
    }

# V24 Phase 4 funnel: the slot verbs are gated by how committed you are to a
# prospect. Scout is always allowed; Contact requires shortlisting (on the focus
# list); Visit is reserved for your top targets.
FUNNEL_STAGES = ("OPEN", "SHORTLIST", "TOP3", "VERBAL")
FOCUS_LIST_STATE_KEY = "recruiting_focus_list_json"
# V24 Phase 4 (remainder): a campus visit is hosted at one of your upcoming HOME
# fixtures (the scheduler join). The binding (prospect_id -> fixture facts) is
# persisted so the board can show where each recruit visits, and a visit is
# refused when no home fixtures remain this season — you cannot host a visit
# with no home game to host it at.
VISIT_FIXTURES_STATE_KEY = "recruiting_visit_fixtures_json"


def funnel_stage(*, on_focus_list: bool, interest: int, focus_rank, vetoed: bool) -> str:
    """The prospect's funnel stage: OPEN until shortlisted, SHORTLIST once on the
    focus list, TOP3 among your three highest-interest focus targets, VERBAL at
    high interest with no dealbreaker veto."""
    from .config import VERBAL_INTEREST_THRESHOLD

    if not on_focus_list:
        return "OPEN"
    if interest >= VERBAL_INTEREST_THRESHOLD and not vetoed:
        return "VERBAL"
    if focus_rank is not None and focus_rank < 3:
        return "TOP3"
    return "SHORTLIST"


def funnel_allows(stage: str) -> tuple[bool, bool]:
    """``(can_contact, can_visit)`` for a funnel stage. Scout is always allowed."""
    can_contact = stage in ("SHORTLIST", "TOP3", "VERBAL")
    can_visit = stage in ("TOP3", "VERBAL")
    return can_contact, can_visit


def load_focus_list(conn) -> list[str]:
    return list(load_json_state(conn, FOCUS_LIST_STATE_KEY, []))


def toggle_focus(conn, prospect_id: str) -> bool:
    """Add/remove a prospect from the persistent focus list. Returns True if the
    prospect is now focused, False if it was removed."""
    import json as _json

    from .persistence import set_state

    current = load_focus_list(conn)
    if prospect_id in current:
        current = [p for p in current if p != prospect_id]
        set_state(conn, FOCUS_LIST_STATE_KEY, _json.dumps(current))
        return False
    current.append(prospect_id)
    set_state(conn, FOCUS_LIST_STATE_KEY, _json.dumps(current))
    return True


def select_visit_fixture(
    scheduled_matches,
    *,
    player_club_id: str,
    current_week: int,
    bound_match_ids: set[str],
):
    """The earliest upcoming HOME fixture available to host an official visit.

    A visit is hosted at one of the user club's own home games at or after the
    current week. ``bound_match_ids`` lets the caller exclude fixtures already
    spoken for; returns ``None`` when no home fixture remains (the visit is then
    refused — there is no home game left to host it at). Pure: no DB, no I/O.
    """
    candidates = [
        m
        for m in scheduled_matches
        if m.home_club_id == player_club_id
        and m.week >= current_week
        and m.match_id not in bound_match_ids
    ]
    candidates.sort(key=lambda m: (m.week, m.match_id))
    return candidates[0] if candidates else None


def load_visit_fixtures(conn) -> dict[str, Any]:
    """Persisted map of prospect_id -> the home fixture hosting his visit."""
    stored = load_json_state(conn, VISIT_FIXTURES_STATE_KEY, {})
    return dict(stored) if isinstance(stored, dict) else {}


def compute_market_signals(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    *,
    prospect_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """V24 Phase 5: the in-season interest race for the given prospects.

    For each prospect, derive the AI clubs courting him — a deterministic
    talent+tier pursuit proxy (prospect_market.derive_club_pursuit), gated by
    WILLINGNESS (a club he would veto on his dealbreaker is not a real suitor) —
    and how the user's tracked interest leads or trails the strongest rival.
    Returns a map prospect_id -> MarketSignal.to_dict(). Pyramid only (the world
    of rival clubs); empty on legacy single-league saves.
    """
    from .world import pyramid_world_active

    if not pyramid_world_active(conn):
        return {}

    from .config import RIVAL_SUITORS_SHOWN
    from .motivations import build_club_context, club_fit
    from .persistence import (
        load_clubs,
        load_command_history_all_seasons,
        load_division_map,
    )
    from .prospect_market import RivalSuitor, build_market_signal, derive_club_pursuit

    persisted = load_prospect_pool(conn, _class_year_from_season(season_id))
    by_id = {p.player_id: p for p in persisted}
    wanted = [by_id[pid] for pid in prospect_ids if pid in by_id]
    if not wanted:
        return {}

    clubs = load_clubs(conn)
    division_map = load_division_map(conn, season_id)
    actions = load_json_state(conn, "prospect_recruitment_actions_json", {})
    cred = _credibility_score(
        conn, season_id, player_club_id, load_command_history_all_seasons(conn)
    )
    rival_club_ids = [cid for cid in sorted(clubs) if cid != player_club_id]
    ctx_cache: dict[str, Any] = {}

    signals: dict[str, dict[str, Any]] = {}
    for prospect in wanted:
        high_band = float(prospect.public_ratings_band["ovr"][1])
        user_interest = current_interest(
            actions.get(prospect.player_id, {}),
            pipeline_tier=prospect.pipeline_tier,
            credibility_score=cred,
        )
        # Cheap pass: rank every rival club by talent+tier pursuit.
        scored = []
        for club_id in rival_club_ids:
            seat = division_map.get(club_id)
            jitter = DeterministicRNG(
                derive_seed(0, "v24_rival", str(prospect.player_id), str(club_id))
            ).roll(0.0, 1.0)
            pursuit = derive_club_pursuit(
                public_high_band=high_band,
                tier=seat.tier if seat is not None else None,
                jitter=jitter,
            )
            scored.append((pursuit, club_id, seat))
        scored.sort(key=lambda t: (-t[0], t[1]))

        # Willingness gate: build context only for the strongest candidates and
        # drop any the prospect would veto (he won't go there). Buffer a few so a
        # veto doesn't shrink the shown list below the cap.
        rivals: list[RivalSuitor] = []
        for pursuit, club_id, seat in scored[: RIVAL_SUITORS_SHOWN + 4]:
            if club_id not in ctx_cache:
                ctx_cache[club_id] = build_club_context(conn, club_id, season_id)
            fit = club_fit(ctx_cache[club_id], prospect)
            if fit.veto:
                continue
            club = clubs.get(club_id)
            club_name = getattr(club, "name", club_id)
            tier_label = seat.division_name if seat is not None else "the wider world"
            cared = [g for g in fit.grades.values() if g.cared]
            best = max(cared, key=lambda g: g.score) if cared else None
            note = f"; he rates their {best.label} {best.letter}" if best else ""
            rivals.append(
                RivalSuitor(
                    club_id=club_id,
                    club_name=club_name,
                    tier=seat.tier if seat is not None else None,
                    interest=pursuit,
                    receipt=f"{club_name} ({tier_label}) is in the race{note}.",
                )
            )
            if len(rivals) >= RIVAL_SUITORS_SHOWN:
                break

        signals[prospect.player_id] = build_market_signal(
            user_interest=user_interest, rivals=rivals
        ).to_dict()
    return signals


def _motivation_fields(fit, scouted: bool) -> dict[str, Any]:
    """V24 board motivation view from a precomputed ``Fit``: the prospect's
    visible cared-about grades plus his dealbreaker (revealed only once
    scouted). Empty when ``fit`` is None (legacy single-league)."""
    if fit is None:
        return {"motivations": [], "dealbreaker": None, "fit": None}
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

    # V24 Phase 4: the persistent focus list. Rank focus-listed prospects by
    # interest so the funnel can mark your top targets (TOP3). Pyramid only.
    focus_set = set(load_focus_list(conn)) if motivation_ctx is not None else set()
    # V24 Phase 4 (remainder): which home fixture hosts each recruit's visit.
    visit_fixtures = load_visit_fixtures(conn) if motivation_ctx is not None else {}
    # V24 Phase 5: the in-season interest race for your focused targets. Stored
    # signals are authoritative (written on each courtship action); any focused
    # prospect without one yet gets a freshly derived signal so the board never
    # hides his rivals.
    market_signals: dict[str, Any] = {}
    if motivation_ctx is not None and focus_set:
        from .persistence import load_prospect_market_signals

        market_signals = dict(load_prospect_market_signals(conn, season_id))
        missing = [pid for pid in focus_set if pid not in market_signals]
        if missing:
            market_signals.update(
                compute_market_signals(
                    conn, season_id, player_club_id, prospect_ids=missing
                )
            )
    focus_interest = sorted(
        (
            (
                p.player_id,
                current_interest(
                    actions.get(p.player_id, {}),
                    pipeline_tier=p.pipeline_tier,
                    credibility_score=credibility["score"],
                ),
            )
            for p in prospects
            if p.player_id in focus_set
        ),
        key=lambda t: -t[1],
    )
    focus_rank_map = {pid: rank for rank, (pid, _interest) in enumerate(focus_interest)}

    # V24 Phase 6: the money-gated Scouting Network decides whose full sheet you
    # can open. Below your level a prospect is a NAME WITHOUT A SHEET. Pyramid
    # only — legacy single-league saves see every prospect's sheet.
    net_level = network_level(conn) if motivation_ctx is not None else None
    home_district = (motivation_ctx.home_region or "") if motivation_ctx is not None else ""
    neighbors: tuple[str, ...] = ()
    visible_map: dict[str, bool] = {}
    reach_map: dict[str, str] = {}
    if motivation_ctx is not None:
        from .scouting_network import prospect_fully_visible, reach_band_for_trajectory
        from .world import DISTRICT_REGIONS, district_neighbors

        neighbors = district_neighbors(home_district)
        home_recognized = home_district in DISTRICT_REGIONS
        for p in prospects:
            band = reach_band_for_trajectory(p.hidden_trajectory)
            reach_map[p.player_id] = band
            visible_map[p.player_id] = prospect_fully_visible(
                reach_band=band, hometown=p.hometown, level=net_level,
                home_district=home_district, neighbors=neighbors,
                home_recognized=home_recognized,
            )

    # V24: surface the wide pyramid class (was hard-capped at the first 8),
    # strongest public estimate first — the vision's class-sized battle view.
    # Your focus targets always show, even if their public estimate is low.
    ranked = sorted(
        prospects,
        key=lambda p: -sum(p.public_ratings_band.get("ovr", (0, 0))),
    )
    if motivation_ctx is not None:
        # Lead with the prospects you can actually scout; tail a few tantalizing
        # names beyond your network (highest reach first) so the upgrade has a
        # visible payoff, then always include your focus targets.
        visible_ranked = [p for p in ranked if visible_map.get(p.player_id)]
        hidden_ranked = sorted(
            (p for p in ranked if not visible_map.get(p.player_id)),
            key=lambda p: (-_REACH_ORDER.get(reach_map.get(p.player_id, ""), 0), p.player_id),
        )
        # PT5 fix: a FIXED-SIZE board (visible sheets first, then teaser names to
        # fill the target). A Scouting Network upgrade converts teaser names into
        # full sheets WITHOUT shrinking the total — previously the 25-visible cap
        # clipped the new sheets while the teaser tail shrank, so a PAID upgrade
        # showed FEWER rows. The board total is now monotonic in level.
        _board_target = _RECRUIT_BOARD_SIZE + _HIDDEN_TEASER_CAP
        board_prospects = visible_ranked[:_board_target]
        if len(board_prospects) < _board_target:
            board_prospects += hidden_ranked[: _board_target - len(board_prospects)]
    else:
        board_prospects = ranked[:_RECRUIT_BOARD_SIZE]
    board_ids = {p.player_id for p in board_prospects}
    board_prospects += [
        p for p in ranked if p.player_id in focus_set and p.player_id not in board_ids
    ]
    rows = []
    for prospect in board_prospects:
        # V24 Phase 6: redact prospects beyond your network to a bare name card.
        if motivation_ctx is not None and not visible_map.get(prospect.player_id, True):
            rows.append(_name_only_row(prospect, reach_map[prospect.player_id], prospect.player_id in focus_set))
            continue
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
        # V24 motivations + funnel (pyramid only): one club_fit per prospect,
        # reused for both the grade view and the dealbreaker veto in the funnel.
        fit = None
        if motivation_ctx is not None:
            from .motivations import club_fit

            fit = club_fit(motivation_ctx, prospect)
        on_focus = pid in focus_set
        if motivation_ctx is not None:
            stage = funnel_stage(
                on_focus_list=on_focus,
                interest=interest,
                focus_rank=focus_rank_map.get(pid),
                vetoed=bool(fit and fit.veto),
            )
            can_contact, can_visit = funnel_allows(stage)
        else:
            stage, can_contact, can_visit = None, True, True
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
            "funnel_stage": stage,
            "on_focus_list": on_focus,
            "can_contact": can_contact,
            "can_visit": can_visit,
            "visit_fixture": visit_fixtures.get(pid),
            "market_signal": market_signals.get(pid),
            "fully_visible": True,
            "reach_band": reach_map.get(pid),
            **_motivation_fields(fit, scouted),
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

    # V24 Phase 4: the funnel gates the stronger verbs (pyramid worlds). Contact
    # and Visit require shortlisting first; Scout is always allowed. The board
    # payload mirrors this (can_contact/can_visit) so the UI disables rather than
    # firing a doomed request — this is the server-side backstop.
    from .world import pyramid_world_active

    # V24 Phase 6: a prospect beyond your Scouting Network is a name without a
    # sheet — you cannot scout, contact, or visit him until you invest reach.
    if pyramid_world_active(conn) and not _prospect_network_visible(
        conn, prospect, player_club_id
    ):
        raise ValueError(
            "This prospect is beyond your Scouting Network's reach — raise your "
            "network to open his sheet first."
        )

    if action in ("contact", "visit") and pyramid_world_active(conn):
        if prospect_id not in load_focus_list(conn):
            raise ValueError(
                "Add this prospect to your focus list before you can contact or visit him."
            )

    # V24 Phase 4 (remainder): a Visit is hosted at an upcoming HOME fixture.
    # Schedule it against the next available home game; refuse if none remain.
    # Pyramid only (legacy single-league saves keep the unscheduled visit).
    visit_fixture: dict[str, Any] | None = None
    if action == "visit" and pyramid_world_active(conn):
        from .persistence import load_season

        current_week = int(load_career_state_cursor(conn).week or 0)
        bound = load_visit_fixtures(conn)
        # Re-visiting a prospect keeps his already-booked fixture; otherwise the
        # set of home games already hosting a visit is excluded so each visit
        # books a distinct home game.
        existing = bound.get(prospect_id)
        if isinstance(existing, dict) and existing.get("match_id"):
            visit_fixture = existing
        else:
            bound_ids = {
                b["match_id"]
                for b in bound.values()
                if isinstance(b, dict) and b.get("match_id")
            }
            fixture = select_visit_fixture(
                load_season(conn, season_id).scheduled_matches,
                player_club_id=player_club_id,
                current_week=current_week,
                bound_match_ids=bound_ids,
            )
            if fixture is None:
                raise ValueError(
                    "No home fixtures remain this season to host an official visit — "
                    "schedule visits earlier next year."
                )
            visit_fixture = {
                "match_id": fixture.match_id,
                "week": fixture.week,
                "home_club_id": fixture.home_club_id,
                "opponent_club_id": fixture.away_club_id,
            }
            bound[prospect_id] = visit_fixture
            set_state(conn, VISIT_FIXTURES_STATE_KEY, json.dumps(bound))

    # V24 Phase 5: the in-season interest race. Compute the PRE-action market
    # signal once (pyramid courtship only) so momentum keys off whether the user
    # was already leading, and the refreshed signal can be persisted afterward.
    pre_signal: dict[str, Any] | None = None
    momentum_bonus = 0
    if action in ("contact", "visit") and pyramid_world_active(conn):
        from .persistence import load_season
        from .prospect_market import leading_momentum_bonus

        pre_signal = compute_market_signals(
            conn, season_id, player_club_id, prospect_ids=[prospect_id]
        ).get(prospect_id)
        leading = bool(pre_signal and pre_signal["leader"] == "user")
        cur_week = int(load_career_state_cursor(conn).week or 0)
        max_week = max(
            (m.week for m in load_season(conn, season_id).scheduled_matches), default=0
        )
        momentum_bonus = leading_momentum_bonus(
            weeks_remaining=max(0, max_week - cur_week), leading=leading
        )

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

    # V24 Phase 5: a leading user's courtship compounds — add the momentum bonus
    # (computed pre-action) on top of the normal gain, clamped, and say so.
    if momentum_bonus:
        from dataclasses import replace as _replace

        bumped = max(0, min(100, int(result.interest_after) + momentum_bonus))
        added = bumped - int(result.interest_after)
        if added:
            new_state = dict(new_state)
            new_state["interest"] = bumped
            result = _replace(
                result,
                interest_after=bumped,
                headline=f"{result.headline} You lead the race — momentum +{added}%.",
            )

    actions[prospect_id] = new_state
    set_state(conn, "prospect_recruitment_actions_json", json.dumps(actions))

    # V24 Phase 5: persist the refreshed interest-race signal (revives the
    # prospect_market_signal table) so the board + receipts read a stored value.
    # Rivals are talent/tier-derived (independent of this action), so the
    # post-action signal is the pre-action one with the user's new interest.
    if pre_signal is not None:
        from .persistence import save_prospect_market_signal

        top = int(pre_signal["top_rival_interest"])
        new_interest = int(new_state.get("interest", pre_signal["user_interest"]))
        rivals = pre_signal["rivals"]
        post_signal = dict(pre_signal)
        post_signal["user_interest"] = new_interest
        post_signal["user_lead"] = new_interest - top
        post_signal["leader"] = (
            "user" if new_interest >= top else (rivals[0]["club_id"] if rivals else "user")
        )
        save_prospect_market_signal(conn, season_id, prospect_id, post_signal)

    # PT4-05: week-stamp every action so the post-week debrief's Prospect
    # Pulse can report the recruiting work that actually happened this week
    # (it claimed "no prospect movement" forever — the reactions list was
    # never fed). Derivation source for use_cases.recruit_reactions_for_week.
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
    payload = result.to_dict()
    if visit_fixture is not None:
        payload["visit_fixture"] = visit_fixture
    return payload


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
