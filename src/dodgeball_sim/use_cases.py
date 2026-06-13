"""Application use cases — framework-agnostic business logic.

These functions contain the core logic extracted from server.py endpoints so
they can be tested and called without FastAPI.
"""
from __future__ import annotations

import dataclasses
import logging
import re
import sqlite3
from typing import Any, Mapping

logger = logging.getLogger(__name__)

from dodgeball_sim.career_state import CareerState, advance
from dodgeball_sim.command_center import (
    build_command_center_state,
    build_default_weekly_plan,
    build_post_week_dashboard,
    refresh_weekly_plan_context,
)
from dodgeball_sim.ai_program_manager import prepare_ai_plans_for_matches
from dodgeball_sim.aftermath_context import AftermathContext, moment_events_from_payload
from dodgeball_sim.game_loop import (
    current_week,
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from dodgeball_sim.match_orchestration import (
    SimulateWeekError,
    _apply_command_plan_to_match,
    _choose_next_user_match_after_automation,
    _validate_match_rosters,
)
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.offseason_ceremony import ensure_ai_rosters_playable
from dodgeball_sim.postgame_validator import (
    PostgameTruthError,
    validate_postgame_payload,
)
from dodgeball_sim.persistence import (
    get_state,
    load_all_rosters,
    load_career_state_cursor,
    load_clubs,
    load_completed_match_ids,
    load_latest_weekly_plan_intent,
    load_season,
    load_standings,
    load_weekly_command_plan,
    save_career_state_cursor,
    save_command_history_record,
    save_weekly_command_plan,
)
from dodgeball_sim.view_models import normalize_root_seed

__all__ = ["SimulateWeekError", "simulate_week"]


_DEV_FOCUS_LABELS = {
    "BALANCED": "Balanced development",
    "YOUTH_ACCELERATION": "Youth acceleration",
    "TACTICAL_DRILLS": "Tactical drills",
    "STRENGTH_AND_CONDITIONING": "Strength and conditioning",
}

# Honest mechanical description of each dev focus, mirroring the multipliers in
# development.apply_season_development. No "training units" exist anywhere in
# the model: weekly choices do NOT accumulate toward ratings — the focus in
# effect at season's end is the one the offseason development pass applies.
_DEV_FOCUS_EFFECTS = {
    "BALANCED": "spreads offseason growth evenly across attributes",
    "YOUTH_ACCELERATION": (
        "boosts offseason growth for players 22 and under (and slows it for older players)"
    ),
    "TACTICAL_DRILLS": (
        "tilts offseason growth toward Tactical IQ, at some cost to power, dodge, and stamina"
    ),
    "STRENGTH_AND_CONDITIONING": (
        "tilts offseason growth toward power and stamina, at some cost to accuracy, dodge, and catch"
    ),
}


def _development_feedback(
    plan: Mapping[str, Any] | None,
    rosters: Mapping[str, list[Any]] | None,
    player_club_id: str | None,
    *,
    is_bye: bool = False,
) -> dict[str, Any]:
    orders = dict((plan or {}).get("department_orders") or {})
    focus = str(orders.get("dev_focus") or "BALANCED")
    focus_label = _DEV_FOCUS_LABELS.get(focus, focus.replace("_", " ").title())
    effect = _DEV_FOCUS_EFFECTS.get(focus, _DEV_FOCUS_EFFECTS["BALANCED"])
    roster = list((rosters or {}).get(player_club_id or "", []))

    # Players the current focus is aimed at — illustrative context for the UI,
    # not a claim of per-player training credit.
    if focus == "YOUTH_ACCELERATION":
        candidates = sorted(roster, key=lambda player: (player.age, -player.traits.potential, player.name))[:3]
    elif focus == "TACTICAL_DRILLS":
        candidates = sorted(roster, key=lambda player: (player.ratings.tactical_iq, player.name))[:3]
    elif focus == "STRENGTH_AND_CONDITIONING":
        candidates = sorted(roster, key=lambda player: (player.ratings.stamina, player.name))[:3]
    else:
        candidates = sorted(roster, key=lambda player: (-player.overall_skill(), player.name))[:3]
    player_names = [player.name for player in candidates]

    # The previous copy claimed "+1 training unit ... for <names>" — fabricated
    # bookkeeping (no accumulator exists, and no per-player credit is tracked).
    # State the real rule instead.
    progress = (
        "Offseason growth follows the dev focus in effect at season's end — "
        f"currently {focus_label}."
    )
    held = "held through the bye" if is_bye else "is this week's development focus"
    summary = f"{focus_label} {held}; it {effect}."

    return {
        "focus": focus,
        "focus_label": focus_label,
        "summary": summary,
        "progress": progress,
        "players": player_names,
    }


def _simulate_bye_week(
    conn: sqlite3.Connection,
    *,
    state: Mapping[str, Any],
    plan: dict[str, Any],
    cursor,
) -> dict[str, Any]:
    player_club_id = state["player_club_id"]
    season_id = state["season_id"]
    week = int(state["week"])
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    completed = load_completed_match_ids(conn, season_id)
    week_matches = [
        match
        for match in sorted(season.matches_for_week(week), key=lambda item: item.match_id)
        if match.match_id not in completed
        and player_club_id not in (match.home_club_id, match.away_club_id)
    ]

    records = []
    rosters = load_all_rosters(conn)
    if week_matches:
        root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
        if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
            rosters = load_all_rosters(conn)
        _validate_match_rosters(week_matches, rosters)
        difficulty = get_state(conn, "difficulty", "pro") or "pro"
        prepare_ai_plans_for_matches(
            conn,
            season_id=season_id,
            season=season,
            matches=week_matches,
            clubs=clubs,
            rosters=rosters,
            player_club_id=player_club_id,
            standings_rows=load_standings(conn, season_id),
            apply_plan=_apply_command_plan_to_match,
            load_plan=load_weekly_command_plan,
            save_plan=save_weekly_command_plan,
        )
        records = [
            simulate_scheduled_match(
                conn,
                scheduled=week_match,
                clubs=clubs,
                rosters=rosters,
                root_seed=root_seed,
                difficulty=difficulty,
            )
            for week_match in week_matches
        ]
        recompute_regular_season_standings(conn, season)

    season = load_season(conn, season_id)
    season, next_chosen, stop_reason = _choose_next_user_match_after_automation(
        conn, season, clubs, player_club_id
    )
    if next_chosen:
        # PT4-02: the cursor week is the player's next TIMELINE stop — the
        # first week with anything left to play, which a bye week between
        # this match and the next one IS. Jumping straight to the next match
        # week made the header read "Week 06" while the body served the
        # week-5 bye.
        cursor = dataclasses.replace(
            cursor,
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            week=current_week(conn, season) or next_chosen[0].week,
            match_id=None,
        )
    elif stop_reason == "season_complete":
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    else:
        cursor = dataclasses.replace(cursor, week=current_week(conn, season) or week)
    save_career_state_cursor(conn, cursor)
    conn.commit()

    dashboard = {
        "season_id": season_id,
        "week": week,
        "match_id": None,
        "opponent_name": "Bye Week",
        "result": "Bye Week",
        "lanes": [
            {
                "title": "League Calendar",
                "summary": f"Bye week advanced after {len(records)} league matches.",
                "items": [
                    "No opponent was scheduled for your club.",
                    "The league calendar advanced to the next available user match.",
                ],
            }
        ],
    }
    return {
        "status": "success",
        "message": "Bye week advanced.",
        "plan": plan,
        "dashboard": dashboard,
        "next_state": cursor.state.value,
        "aftermath": {
            "headline": "Bye Week Complete",
            "match_card": None,
            "player_growth_deltas": [],
            "development_feedback": _development_feedback(plan, rosters, player_club_id, is_bye=True),
            # Honest bye copy: there is no persisted fatigue/recovery system —
            # stamina is a fixed rating — so claiming the squad "avoided fatigue
            # exposure" (or naming arbitrary players as "recovered") fabricates
            # a mechanic. A bye is simply a week with no match minutes.
            "bye_recovery": {
                "summary": "No match scheduled — your club logged no match minutes this week.",
                "players": [],
            },
            "standings_shift": [],
            # PT4-05: recruiting work done on a bye week is still real work.
            "recruit_reactions": _recruit_reactions(conn, season_id, week),
        },
    }


def _assert_postgame_copy_truthful(
    *,
    headline: str,
    verdict: str | None,
    result: str,
    player_survivors: int,
    opponent_survivors: int,
) -> None:
    """Cheap invariant guard against postgame copy drifting from the result.

    Future copy generators must not produce a "Win" headline on a Loss
    (or vice versa) and must not produce a "So close" / "narrow" tag on
    a shutout. This assertion is intentionally narrow: it doesn't try
    to validate every template, just the contradictions that have
    surfaced in playtest reports.

    ``player_survivors`` / ``opponent_survivors`` carry the *displayed score
    basis* the headline uses: official game points for set-scored matches,
    survivor counts otherwise — so the narrow/"so close" check reasons about
    the same numbers the headline shows (WT-2).
    """
    headline_lower = headline.lower()
    if result == "Loss":
        # The literal word "Win" never appears in Loss templates. (Note
        # that some Win templates say "you won" — fine on a Win; never
        # on a Loss.) Match "win" as a whole word so we don't trip on
        # "winning", "winless", "rewind", "swinging", etc.
        assert re.search(r"\bwin\b", headline_lower) is None, (
            f"Loss headline contains 'Win': {headline!r}"
        )
        # "So close" / "narrow" is reserved for one-survivor-margin losses.
        if abs(player_survivors - opponent_survivors) >= 2:
            assert "so close" not in headline_lower, (
                f"Non-narrow Loss headline uses 'So close': {headline!r} "
                f"(margin={player_survivors - opponent_survivors})"
            )
    elif result == "Win":
        assert re.search(r"\bloss\b", headline_lower) is None, (
            f"Win headline contains 'Loss': {headline!r}"
        )
    elif result == "Draw":
        assert re.search(r"\bwin\b", headline_lower) is None, (
            f"Draw headline contains 'Win': {headline!r}"
        )
        assert re.search(r"\bloss\b", headline_lower) is None, (
            f"Draw headline contains 'Loss': {headline!r}"
        )
    if verdict is not None and result == "Loss":
        assert "you won" not in verdict.lower(), (
            f"Loss verdict contains 'you won': {verdict!r}"
        )


def _degraded_postgame_payload(
    result,
    *,
    home_club_id: str,
    away_club_id: str,
) -> dict[str, Any]:
    """Build a minimal truthful aftermath payload.

    Used as a fallback when the assembled payload fails structural
    validation. Contains only raw facts derived from the resolved
    ``MatchResult`` — no headline copy, no verdict, no body, no top
    performers. Must itself satisfy ``validate_postgame_payload``.
    """
    teams = (result.box_score or {}).get("teams") or {}
    home_team = teams.get(home_club_id) or {}
    away_team = teams.get(away_club_id) or {}
    home_living = int(((home_team.get("totals") or {}).get("living") or 0))
    away_living = int(((away_team.get("totals") or {}).get("living") or 0))
    # Preserve real game_points when official_metadata is present so the
    # fallback never silently zeros a cloth/foam score. Mirror the
    # home<->team_a mapping used in game_loop._persist_match_result.
    scoring_model = "legacy"
    home_game_pts = 0
    away_game_pts = 0
    meta = getattr(result, "official_metadata", None)
    if isinstance(meta, Mapping):
        scoring_model = (
            "cloth" if "cloth" in (getattr(result, "config_version", "") or "") else "foam"
        )
        team_a_gp = meta.get("team_a_game_points")
        team_b_gp = meta.get("team_b_game_points")
        if team_a_gp is not None or team_b_gp is not None:
            try:
                team_a_gp_i = int(team_a_gp or 0)
                team_b_gp_i = int(team_b_gp or 0)
            except (TypeError, ValueError):
                team_a_gp_i = team_b_gp_i = 0
            team_a_id = meta.get("team_a_id")
            if team_a_id is not None and str(team_a_id) == str(away_club_id):
                home_game_pts = team_b_gp_i
                away_game_pts = team_a_gp_i
            else:
                home_game_pts = team_a_gp_i
                away_game_pts = team_b_gp_i
    return {
        "headline": "Match complete.",
        "match_card": {
            "home_club_id": home_club_id,
            "away_club_id": away_club_id,
            "winner_club_id": result.winner_team_id,
            "home_survivors": home_living,
            "away_survivors": away_living,
            "scoring_model": scoring_model,
            "home_game_points": home_game_pts,
            "away_game_points": away_game_pts,
        },
        "player_growth_deltas": [],
        "standings_shift": [],
        "recruit_reactions": [],
        "body": [],
        "top_performers": [],
    }


def _load_playoff_resolution(
    conn,
    record,
    player_club_id: str | None,
) -> dict[str, Any] | None:
    """Return the playoff-resolution block for a finished match, if any.

    Task 1 (2026-05-27 playtest-fixes): if the match is a playoff match
    that needed a tiebreaker, surface ``decided_by`` and the upstream
    ``narrative_note`` to the aftermath payload so the frontend banner
    can render an unambiguous "Advanced / Eliminated" sentence instead
    of leaving the player guessing. Returns ``None`` for regular-season
    matches and for playoff matches decided in regulation (no banner
    needed — the score itself tells the story).
    """

    from dodgeball_sim.playoffs import is_playoff_match_id, playoff_stage_label

    season_id = getattr(record, "season_id", None)
    match_id = getattr(record, "match_id", None)
    if not season_id or not match_id:
        return None
    if not is_playoff_match_id(season_id, match_id):
        return None

    row = conn.execute(
        "SELECT decided_by, narrative_note, winner_club_id"
        " FROM match_records WHERE match_id = ?",
        (match_id,),
    ).fetchone()
    if row is None:
        return None
    decided_by = row["decided_by"] or "regulation"
    if decided_by == "regulation":
        return None
    winner_id = row["winner_club_id"]
    loser_id = (
        record.away_club_id if winner_id == record.home_club_id else record.home_club_id
    )
    stage = playoff_stage_label(season_id, match_id)
    player_outcome: str | None = None
    if player_club_id is not None and player_club_id in (record.home_club_id, record.away_club_id):
        player_outcome = "advanced" if winner_id == player_club_id else "eliminated"
    return {
        "decided_by": decided_by,
        "narrative_note": row["narrative_note"] or "",
        "winner_club_id": winner_id,
        "loser_club_id": loser_id,
        "stage": stage,
        "player_outcome": player_outcome,
    }


def _load_elimination(
    conn,
    record,
    player_club_id: str | None,
    *,
    clubs,
    home_survivors: int,
    away_survivors: int,
    winner_id: str | None,
    top_performers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the elimination-ceremony block when the player lost a playoff
    match, else ``None``.

    Unlike :func:`_load_playoff_resolution` (tiebreakers only) this fires
    on *any* playoff loss the player took part in, including regulation,
    since that is exactly the moment a dynasty's season ends.
    """

    from dodgeball_sim.elimination_ceremony import build_elimination_summary
    from dodgeball_sim.playoffs import is_playoff_match_id, playoff_stage_label

    if player_club_id is None or clubs is None:
        return None
    season_id = getattr(record, "season_id", None)
    match_id = getattr(record, "match_id", None)
    if not season_id or not match_id:
        return None
    if not is_playoff_match_id(season_id, match_id):
        return None
    if player_club_id not in (record.home_club_id, record.away_club_id):
        return None
    if winner_id is None or winner_id == player_club_id:
        return None  # advanced, or undecided -- not an elimination

    player_is_home = record.home_club_id == player_club_id
    opponent_club_id = record.away_club_id if player_is_home else record.home_club_id
    opponent_club = clubs.get(opponent_club_id)
    opponent_name = opponent_club.name if opponent_club is not None else "your opponent"
    player_score = home_survivors if player_is_home else away_survivors
    opponent_score = away_survivors if player_is_home else home_survivors

    player_club = clubs.get(player_club_id)
    player_club_name = player_club.name if player_club is not None else None
    contributors = [
        {"player_name": p.get("player_name", ""), "score": p.get("score", 0)}
        for p in top_performers
        if player_club_name is not None and p.get("club_name") == player_club_name
    ]

    row = conn.execute(
        "SELECT decided_by, narrative_note FROM match_records WHERE match_id = ?",
        (match_id,),
    ).fetchone()
    decided_by = (row["decided_by"] if row is not None else None) or "regulation"
    narrative_note = (row["narrative_note"] if row is not None else None) or ""

    return build_elimination_summary(
        stage=playoff_stage_label(season_id, match_id),
        opponent_name=opponent_name,
        player_score=int(player_score),
        opponent_score=int(opponent_score),
        decided_by=decided_by,
        narrative_note=narrative_note,
        contributors=contributors,
    )


def _load_championship(
    conn,
    record,
    player_club_id: str | None,
    *,
    clubs,
    home_survivors: int,
    away_survivors: int,
    winner_id: str | None,
) -> dict[str, Any] | None:
    """Return the championship-celebration block when the player won the
    title-clinching final, else ``None``.

    Task 10 (2026-05-28 playtest-fixes): the title win used to be
    undersold by the standard debrief, with the celebration buried behind
    an extra Continue into the offseason. This surfaces the trophy moment
    as the first thing the player sees on the final-win aftermath.
    """

    from dodgeball_sim.playoffs import is_playoff_match_id

    if player_club_id is None or clubs is None:
        return None
    season_id = getattr(record, "season_id", None)
    match_id = getattr(record, "match_id", None)
    if not season_id or not match_id:
        return None
    if not is_playoff_match_id(season_id, match_id):
        return None
    if match_id != f"{season_id}_p_final":
        return None
    if winner_id != player_club_id:
        return None

    player_is_home = record.home_club_id == player_club_id
    opponent_club_id = record.away_club_id if player_is_home else record.home_club_id
    opponent_club = clubs.get(opponent_club_id)
    player_club = clubs.get(player_club_id)

    row = conn.execute(
        """
        SELECT decided_by, scoring_model, home_game_points, away_game_points
        FROM match_records WHERE match_id = ?
        """,
        (match_id,),
    ).fetchone()
    decided_by = (row["decided_by"] if row is not None else None) or "regulation"

    # Codex playtest issue 22: the champion banner read its score from the
    # survivors columns, which on official matches hold only the final
    # game's living counts — a 13-12 title win displayed as "0-0 over
    # Lunar Syndicate". Officials score in GAME POINTS; same branch every
    # other scoreline surface uses.
    if row is not None and (row["scoring_model"] or "legacy") != "legacy":
        home_score = int(row["home_game_points"] or 0)
        away_score = int(row["away_game_points"] or 0)
    else:
        home_score, away_score = home_survivors, away_survivors
    player_score = home_score if player_is_home else away_score
    opponent_score = away_score if player_is_home else home_score

    return {
        "champion_name": player_club.name if player_club is not None else "Your club",
        "opponent_name": opponent_club.name if opponent_club is not None else "your opponent",
        "player_score": int(player_score),
        "opponent_score": int(opponent_score),
        "decided_by": decided_by,
    }


# ---------------------------------------------------------------------------
# WT-32 Manager Lesson — controllable-signal extractors.
#
# Each returns a primitive dict ONLY when the lever genuinely *applies*, else
# None. "Applies" reuses the exact thresholds the pre-match week briefing shows
# the player, so a lesson never claims a lever the briefing wouldn't have
# flagged, and the honest "nothing you controlled" message stays reachable when
# none apply. All read the saved pre-sim ``plan`` (and, for the weakest group,
# the current roster) — already-resolved data the player can see.
# ---------------------------------------------------------------------------


def _aftermath_ignored_recommendation(
    conn,
    *,
    season_id: str | None,
    current_match_id: str | None,
    plan: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Reconstruct the pre-match advisory the player declined, if any.

    Faithful by construction: ``compute_staff_recommendation`` is a pure
    function of (recent results, at-risk starter count). We feed it the SAME
    inputs the live week briefing did for the final locked plan —

      * recent results with the just-played match EXCLUDED (the loss is already
        persisted to command_history before the aftermath is built, so dropping
        it by match_id recovers the genuine pre-match slice; including it would
        fabricate "advice you ignored" the player never saw — ADR 0002);
      * the at-risk starter count from the locked plan's lineup stamina.

    Returns ``{advised_intent, selected_intent, reason}`` only when the staff
    advised a DIFFERENT intent than the one the player ran (i.e. an advisory the
    player declined). Otherwise None.
    """
    if not plan or season_id is None:
        return None
    selected = str(plan.get("intent") or "").strip()
    if not selected:
        return None
    try:
        from dodgeball_sim.persistence import load_command_history
        from dodgeball_sim.week_briefing import (
            _build_fatigue,
            compute_staff_recommendation,
        )

        history = load_command_history(conn, season_id)
        recent_results = [
            result
            for record in history
            if record.get("match_id") != current_match_id
            and (result := (record.get("dashboard") or {}).get("result"))
        ][-5:]
        at_risk = int(_build_fatigue(dict(plan)).get("at_risk_count", 0))
        staff = compute_staff_recommendation(
            recent_results=recent_results, at_risk_count=at_risk
        )
    except Exception:
        return None

    advised = str(staff.get("recommended_intent") or "").strip()
    if not advised or advised == selected:
        return None
    return {
        "advised_intent": advised,
        "selected_intent": selected,
        "reason": str(staff.get("reason") or "").strip(),
    }


def _aftermath_roster_edge(plan: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Net fielded-six OVR edge, only when the player was the clear underdog.

    Mirrors ``week_briefing._build_edge`` (net = player starters − opponent
    starters) and its ``_EVEN_BAND`` underdog threshold, so the lesson aligns
    with the favourite/underdog band the player saw pre-match.
    """
    if not plan:
        return None
    from dodgeball_sim.week_briefing import _EVEN_BAND

    def _sum(side_key: str) -> int:
        players = ((plan.get(side_key) or {}).get("players")) or []
        return sum(int(p.get("overall", 0)) for p in players)

    starters = ((plan.get("lineup") or {}).get("players")) or []
    opponents = ((plan.get("opponent_lineup") or {}).get("players")) or []
    if not starters or not opponents:
        return None
    net = _sum("lineup") - _sum("opponent_lineup")
    if net >= -_EVEN_BAND:
        return None  # even or favoured — not a controllable shortfall
    return {"net_ovr": net}


def _aftermath_fatigue_signal(plan: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Most-depleted fielded starter, only when genuinely at-risk.

    Reuses ``next_best_improvement.lowest_condition_starter`` and the briefing's
    ``_AT_RISK_STAMINA`` bar so the lesson fires on the same fatigue the
    pre-match briefing would have flagged.
    """
    if not plan:
        return None
    from dodgeball_sim.next_best_improvement import lowest_condition_starter
    from dodgeball_sim.week_briefing import _AT_RISK_STAMINA

    starters = ((plan.get("lineup") or {}).get("players")) or []
    low = lowest_condition_starter(list(starters))
    if low is None or int(low.get("stamina", 100)) >= _AT_RISK_STAMINA:
        return None
    return low


def _aftermath_weakest_group(
    conn, player_club_id: str | None
) -> dict[str, Any] | None:
    """Thinnest roster position group, only when notably below the rest.

    Reuses ``next_best_improvement.weakest_position_group`` (which the post-loss
    improvement panel also uses). Requires the group to sit a real margin below
    the roster's overall average — otherwise "weakest" is meaningless on a flat
    roster and would fabricate a lever, so we return None and let the honest
    no-lever message stand.
    """
    if player_club_id is None:
        return None
    from dodgeball_sim.next_best_improvement import weakest_position_group

    rows: list[dict[str, Any]] = []
    overalls: list[int] = []
    for player in load_all_rosters(conn).get(player_club_id, []):
        arch = getattr(player, "archetype", None)
        ovr = int(player.overall_skill())
        rows.append({"archetype": getattr(arch, "value", str(arch or "")), "overall": ovr})
        overalls.append(ovr)
    group = weakest_position_group(rows)
    if group is None or not overalls:
        return None
    roster_avg = sum(overalls) / len(overalls)
    # 5-OVR margin below the roster average = a real depth hole, not noise.
    if roster_avg - float(group["avg_overall"]) < 5.0:
        return None
    return group


def _load_improvement_panel(
    conn,
    *,
    season_id: str | None,
    player_club_id: str | None,
    plan: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Build the post-loss "next best improvement" suggestions.

    Pulls only from already-computed engine values: roster OVR by
    archetype, starter stamina from the saved plan lineup, and recruit
    fit/interest. Recruit data needs extra loads, so it is fetched in its
    own guard -- if it fails the panel simply drops the recruit card.
    """

    from dodgeball_sim.next_best_improvement import build_improvement_panel

    if player_club_id is None:
        return []

    roster_rows: list[dict[str, Any]] = []
    try:
        for player in load_all_rosters(conn).get(player_club_id, []):
            arch = getattr(player, "archetype", None)
            roster_rows.append(
                {
                    "archetype": getattr(arch, "value", str(arch or "")),
                    "overall": int(player.overall_skill()),
                }
            )
    except Exception:
        roster_rows = []

    starters = list(((plan or {}).get("lineup") or {}).get("players") or [])

    recruits: list[dict[str, Any]] = []
    try:
        from dodgeball_sim.offseason_ceremony import stored_root_seed
        from dodgeball_sim.persistence import load_command_history_all_seasons
        from dodgeball_sim.recruiting_office import build_recruiting_state

        if season_id:
            state = build_recruiting_state(
                conn,
                season_id=season_id,
                player_club_id=player_club_id,
                root_seed=stored_root_seed(conn),
                history=load_command_history_all_seasons(conn),
            )
            recruits = list(state.get("prospects") or [])
    except Exception:
        recruits = []

    return build_improvement_panel(roster=roster_rows, starters=starters, recruits=recruits)


# Lesson code -> the improvement-panel item category that names the SAME lever.
# On an inconclusive loss both surfaces can fire; when they do, the Manager
# Lesson (the loss-specific contextual surface) is kept and the duplicate panel
# item is dropped so a single lever is not narrated twice.
#
# Faithfulness note (proven equality): the two surfaces compute these levers
# from the SAME inputs via the SAME pure helpers, so they cannot name DIFFERENT
# things when both are present:
#   * weakest_role_group / position_group -> both derive from
#     ``next_best_improvement.weakest_position_group`` over
#     ``load_all_rosters(conn)[player_club_id]`` (identical rows), so the
#     archetype is identical. ``_aftermath_weakest_group`` only adds a stricter
#     gate (must sit >=5 OVR below roster avg); it never changes WHICH group.
#   * fatigue / condition -> both derive from
#     ``next_best_improvement.lowest_condition_starter`` over the SAME
#     ``plan["lineup"]["players"]``, so the starter name is identical.
# Because each side has effectively one value and they provably match, keying
# the drop on the lesson's chosen ``code`` is exact, not a category shortcut.
# (``roster_edge``/``ignored_recommendation``/``no_lever`` have no panel
# counterpart and so are absent here, leaving the panel untouched for them.)
# If a future edit makes either helper diverge, revisit: the rule must stay
# fail-safe (suppress only a genuine duplicate; keep both on any mismatch).
#
# Keys are the ``manager_lesson`` code string literals (WEAKEST_ROLE_GROUP /
# FATIGUE). They are NOT imported as constants here on purpose: ``use_cases``
# imports ``manager_lesson`` lazily inside ``_build_aftermath`` to keep that
# submodule off the module-import path, and this dict is built at import time.
# The dedup test imports the same constants, so any future drift in their
# values fails that test red.
_LESSON_CODE_TO_PANEL_CATEGORY = {
    "weakest_role_group": "position_group",
    "fatigue": "condition",
}


def _dedup_lesson_panel(aftermath: dict[str, Any]) -> None:
    """Drop the improvement-panel item that names the SAME lever as the lesson.

    Pure presentation assembly over the already-built payload (no engine or
    scoring change, no helper change). Mutates ``aftermath`` in place:

    * When ``manager_lesson`` is present AND its ``code`` maps to a panel
      category, the matching panel item is removed. The Manager Lesson is the
      loss-specific contextual surface and is always kept.
    * The lesson picks exactly ONE code by severity, so at most ONE panel item
      is ever dropped; every non-duplicate item (recruit + the other lever) is
      kept.
    * If the panel becomes empty after the drop, ``improvement_panel`` is
      removed entirely rather than surfacing an empty panel.

    No-ops when either key is absent, or when the lesson code has no panel
    counterpart (``roster_edge`` / ``ignored_recommendation`` / ``no_lever``).
    """

    lesson = aftermath.get("manager_lesson")
    panel = aftermath.get("improvement_panel")
    if not isinstance(lesson, Mapping) or not isinstance(panel, list):
        return
    dup_category = _LESSON_CODE_TO_PANEL_CATEGORY.get(str(lesson.get("code") or ""))
    if dup_category is None:
        return  # lesson names a lever with no panel counterpart -> nothing to dedup

    filtered = [
        item
        for item in panel
        if not (isinstance(item, Mapping) and item.get("category") == dup_category)
    ]
    if filtered == panel:
        return  # no matching item was present -> leave the panel untouched
    if filtered:
        aftermath["improvement_panel"] = filtered
    else:
        # Panel held only the duplicate -> omit the key rather than ship [].
        aftermath.pop("improvement_panel", None)


def _recruit_reactions(conn, season_id: str, week: int | None) -> list:
    """PT4-05: Prospect Pulse rows for the week (defensive — never raises)."""
    from dodgeball_sim.recruiting_office import recruit_reactions_for_week

    try:
        return recruit_reactions_for_week(conn, season_id, int(week or 0))
    except Exception:
        return []


def _build_aftermath(
    conn,
    dashboard: dict[str, Any],
    record,
    season_id: str,
    standings_before: list | None = None,
    standings_after: list | None = None,
    clubs: dict | None = None,
    plan: Mapping[str, Any] | None = None,
    player_club_id: str | None = None,
) -> dict[str, Any]:
    """Build the aftermath payload for a simulated week."""
    from dodgeball_sim.voice_aftermath import render_body
    from dodgeball_sim.voice_verdict import render_headline, render_verdict

    box = record.result.box_score["teams"]
    home_survivors = int(box[record.home_club_id]["totals"]["living"])
    away_survivors = int(box[record.away_club_id]["totals"]["living"])
    # The resolved MatchResult is canon. The old survivor-derived fallback here
    # could only ever CONTRADICT it: franchise.simulate_match already patches
    # non-official winners from survivors upstream, so the only records that
    # reached this branch with a None winner were official game-points draws
    # (where unequal survivor counts are legitimate) — and any derived winner
    # then tripped validate_postgame_payload and degraded the entire aftermath
    # panel. Measured on a 10-season auto-pilot sweep: 17 degraded aftermaths
    # in 80 seasons, all from this branch.
    _winner_id = record.result.winner_team_id
    start_context = record.result.events[0].context if record.result.events else {}
    end_context = record.result.events[-1].context if record.result.events else {}
    team_policies = (
        dict(start_context.get("team_policies", {}))
        if isinstance(start_context, Mapping)
        else {}
    )
    parsed_moments = moment_events_from_payload(
        end_context.get("moment_events", []) if isinstance(end_context, Mapping) else []
    )

    standings_shift: list[dict] = []
    if standings_before is not None and standings_after is not None and clubs is not None:
        # PT4-04: on pyramid saves the shift card speaks in YOUR DIVISION's
        # ranks — global 28-club rank jumps named clubs from leagues the
        # player never faces and read as noise from a D3 viewpoint.
        # (Identity on legacy saves.)
        if player_club_id:
            from dodgeball_sim.pyramid_postseason import user_division_standings_filter

            standings_before = user_division_standings_filter(
                conn, season_id, list(standings_before), player_club_id
            )
            standings_after = user_division_standings_filter(
                conn, season_id, list(standings_after), player_club_id
            )
        before_rank = {row.club_id: (i + 1) for i, row in enumerate(standings_before)}
        after_rank = {row.club_id: (i + 1) for i, row in enumerate(standings_after)}
        for club_id, new_rank in after_rank.items():
            old_rank = before_rank.get(club_id, new_rank)
            if old_rank != new_rank:
                club = clubs.get(club_id)
                standings_shift.append({
                    "club_id": club_id,
                    "club_name": club.name if club else club_id,
                    "old_rank": old_rank,
                    "new_rank": new_rank,
                })
        standings_shift.sort(key=lambda item: item["new_rank"])

    verdict: str | None = None
    body: tuple[str, ...] = ()
    if plan is not None and player_club_id is not None and clubs is not None:
        opponent_club_id = record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
        winner = record.result.winner_team_id
        result = "Draw" if winner is None else ("Win" if winner == player_club_id else "Loss")
        club = clubs.get(player_club_id)
        if club is not None and player_club_id in box and opponent_club_id in box:
            base_tactics = club.coach_policy.as_dict()
            player_policy = CoachPolicy.from_dict(
                dict(team_policies.get(player_club_id) or plan.get("tactics") or base_tactics)
            )
            opponent_policy = CoachPolicy.from_dict(
                dict(team_policies.get(opponent_club_id) or CoachPolicy().as_dict())
            )
            voice_ctx = AftermathContext(
                match_result=record.result,
                moment_events=parsed_moments,
                policy_team=player_policy,
                policy_opponent=opponent_policy,
                tier=1,
                player_club_id=player_club_id,
                selected_intent=str(plan.get("intent", "") or ""),
            )
            headline = render_headline(voice_ctx)
            body = render_body(voice_ctx)
            verdict = render_verdict(
                intent=str(plan.get("intent", "")),
                tactics=dict(plan.get("tactics") or {}),
                base_tactics=base_tactics,
                result=result,
                player_team_box=box[player_club_id],
                opponent_team_box=box[opponent_club_id],
            )
            # Contract: postgame copy must never contradict the resolved
            # MatchResult. If it does, fail loudly rather than ship a
            # "Win" headline on a Loss.
            # The guard must judge the headline against the same score basis
            # the headline shows: official game points when set-scored, else
            # survivor counts. Otherwise a narrow game-point loss (e.g. 2-3)
            # would false-trip the survivor-margin "so close" check (WT-2).
            _player_gp = voice_ctx.game_points_for(player_club_id)
            _opp_gp = voice_ctx.game_points_for(opponent_club_id)
            if _player_gp is not None and _opp_gp is not None:
                _player_score, _opp_score = _player_gp, _opp_gp
            else:
                _player_score = int(box[player_club_id]["totals"]["living"])
                _opp_score = int(box[opponent_club_id]["totals"]["living"])
            _assert_postgame_copy_truthful(
                headline=headline,
                verdict=verdict,
                result=result,
                player_survivors=_player_score,
                opponent_survivors=_opp_score,
            )
        else:
            headline = dashboard["result"]
    else:
        headline = dashboard["result"]

    try:
        from dodgeball_sim.replay_service import roster_snapshots, stats_for_match, score_player

        _clubs = clubs if clubs is not None else load_clubs(conn)
        snapshots = roster_snapshots(conn, record.match_id, record.home_club_id, record.away_club_id)
        name_map = {
            str(player.get("id", "")): str(player.get("name", player.get("id", "")))
            for players in snapshots.values()
            for player in players
        }
        player_club_map = {
            str(player.get("id", "")): club_id
            for club_id, players in snapshots.items()
            for player in players
        }
        stats = stats_for_match(conn, record.match_id)

        # Weight impact by team outcome so the loser of a shutout can't out-rank
        # the winner. Winners get +50% Impact, losers get -25%, draws unchanged.
        def _weighted(player_id: str, stat) -> float:
            base = score_player(stat)
            club_id = player_club_map.get(player_id, "")
            if _winner_id and club_id == _winner_id:
                return base * 1.5
            if _winner_id and club_id and club_id != _winner_id:
                return base * 0.75
            return base

        top = sorted(stats.items(), key=lambda item: (-_weighted(item[0], item[1]), item[0]))[:6]
        top_performers = [
            {
                "player_id": player_id,
                "player_name": name_map.get(player_id, player_id),
                "club_name": _clubs[player_club_map.get(player_id, "")].name if player_club_map.get(player_id, "") in _clubs else "Unknown",
                "score": round(_weighted(player_id, stat), 1),
                "eliminations_by_throw": stat.eliminations_by_throw,
                "catches_made": stat.catches_made,
                "dodges_successful": stat.dodges_successful,
            }
            for player_id, stat in top
            if _weighted(player_id, stat) > 0
        ]
    except Exception:
        top_performers = []

    scoring_model = "legacy"
    home_game_pts = 0
    away_game_pts = 0
    match_card_games: list[dict[str, Any]] = []
    if record.result.official_metadata:
        meta = record.result.official_metadata
        if "cloth" in record.result.config_version:
            scoring_model = "cloth"
        else:
            scoring_model = "foam"
        home_game_pts = meta.get("team_a_game_points", 0)
        away_game_pts = meta.get("team_b_game_points", 0)
        # Per-game set story (won/lost/no-point per game, in order) so the
        # aftermath can show HOW the game points accumulated — a 9-2 win and
        # a 2-9 collapse read identically without it. Same team_a == home
        # adapter invariant as the totals above.
        for game in meta.get("games", []) or []:
            if not isinstance(game, dict):
                continue
            match_card_games.append(
                {
                    "game_number": int(game.get("game_number", 0) or 0),
                    "winner_club_id": game.get("winner_team_id"),
                    "home_points": int(game.get("team_a_points", 0) or 0),
                    "away_points": int(game.get("team_b_points", 0) or 0),
                    "result_type": str(game.get("result_type", "") or ""),
                }
            )

    aftermath: dict[str, Any] = {
        "headline": headline,
        "match_card": {
            "home_club_id": record.home_club_id,
            "away_club_id": record.away_club_id,
            "winner_club_id": _winner_id,
            "home_survivors": home_survivors,
            "away_survivors": away_survivors,
            "scoring_model": scoring_model,
            "home_game_points": home_game_pts,
            "away_game_points": away_game_pts,
            "games": match_card_games,
        },
        "player_growth_deltas": [],
        "development_feedback": _development_feedback(plan, load_all_rosters(conn), player_club_id),
        "standings_shift": standings_shift,
        # PT4-05: the week's real scout/contact/visit work, from the
        # week-stamped action log — "no prospect movement" only when true.
        "recruit_reactions": _recruit_reactions(conn, season_id, record.week),
        "body": list(body),
        "top_performers": top_performers,
    }
    if verdict is not None:
        aftermath["verdict"] = verdict

    # Surface NarrativeBeats so the frontend can gate comeback cards and
    # any narrative chip without re-deriving from raw box-score data.
    if plan is not None and player_club_id is not None:
        try:
            from dodgeball_sim.replay_proof import derive_narrative_beats
            beats = derive_narrative_beats(
                record.result,
                player_club_id=player_club_id,
                moment_events=parsed_moments,
                selected_intent=str(plan.get("intent", "") or ""),
            )
            aftermath["narrative_beats"] = beats.as_dict()
        except Exception:
            # Beats are a polish surface — if derivation fails, the
            # frontend conservatively renders nothing rather than blowing
            # up the entire aftermath payload.
            pass

    # V14 Task 1: deterministic Primary Factor explanation. Read-only over the
    # resolved MatchResult, moment events, deficit timeline, and lineup
    # liabilities — never alters outcomes. Polish surface: if anything fails
    # we simply omit the key rather than break the aftermath payload.
    if player_club_id is not None and player_club_id in box:
        try:
            from dodgeball_sim.match_explanation import (
                deficit_timeline,
                derive_match_explanation,
            )
            from dodgeball_sim.replay_service import roster_snapshots

            opponent_club_id = (
                record.away_club_id
                if record.home_club_id == player_club_id
                else record.home_club_id
            )
            if opponent_club_id in box:
                winner = record.result.winner_team_id
                result_pf = (
                    "Draw"
                    if winner is None
                    else ("Win" if winner == player_club_id else "Loss")
                )
                timeline = deficit_timeline(
                    record.result,
                    player_club_id=player_club_id,
                    opponent_club_id=opponent_club_id,
                )
                snapshots = roster_snapshots(
                    conn, record.match_id, record.home_club_id, record.away_club_id
                )
                name_map_pf = {
                    str(p.get("id", "")): str(p.get("name", p.get("id", "")))
                    for players in snapshots.values()
                    for p in players
                }
                # 2026-06-09 audit: lineup-liability (slot-role fit) facts are
                # no longer fed to the Primary Factor — no shipping engine
                # applies a role penalty, so role mismatch cannot be a cause of
                # the result. Role-fit notes remain on advisory surfaces (lineup
                # editor warnings, replay liability lane with advisory copy).
                # 4.4: for official set-based matches, the game-point gap is the
                # decisive scoreline — feed it so a 0-4 / 6-0 result is never
                # explained as "inconclusive / stayed close". Generic matches
                # carry no official_metadata, so point_margin stays 0.
                official_meta = getattr(record.result, "official_metadata", None) or {}
                point_margin = abs(
                    int(official_meta.get("team_a_game_points", 0))
                    - int(official_meta.get("team_b_game_points", 0))
                )
                # Codex playtest issue 19: feed the actual fielded-OVR edge so
                # a favored loss is never diagnosed as "squad strength".
                # Computed from the same roster snapshots the replay uses
                # (mean of the five OVR stats per fielded player, summed).
                def _fielded_ovr_total(players: list[dict[str, Any]]) -> float:
                    total = 0.0
                    for p in players[:6]:
                        r = p.get("ratings", {}) or {}
                        total += sum(
                            float(r.get(k, 0) or 0)
                            for k in ("accuracy", "power", "dodge", "catch", "stamina")
                        ) / 5.0
                    return total

                ovr_edge = round(
                    _fielded_ovr_total(snapshots.get(player_club_id, []))
                    - _fielded_ovr_total(snapshots.get(opponent_club_id, []))
                )
                explanation = derive_match_explanation(
                    result=result_pf,
                    player_survivors=int(box[player_club_id]["totals"]["living"]),
                    opponent_survivors=int(box[opponent_club_id]["totals"]["living"]),
                    player_catches=int(box[player_club_id]["totals"].get("catches", 0)),
                    opponent_catches=int(box[opponent_club_id]["totals"].get("catches", 0)),
                    moment_events=parsed_moments,
                    player_club_id=player_club_id,
                    opponent_club_id=opponent_club_id,
                    largest_deficit=timeline.largest_deficit,
                    deficit_low_tick=timeline.deficit_low_tick,
                    final_tick=int(getattr(record.result, "final_tick", 0) or 0),
                    name_map=name_map_pf,
                    point_margin=point_margin,
                    ovr_edge=ovr_edge,
                )
                aftermath["primary_factor"] = explanation.primary_factor.as_dict()

                # WT-32: when the Primary Factor is INCONCLUSIVE (a genuine
                # coin-flip loss OR an even, close draw — not a decisive
                # blowout), the player still wants to know "what could *I* have
                # changed?". Surface a SEPARATE, adjacent "Manager Lesson" drawn
                # only from CONTROLLABLE prep. ``derive_manager_lesson`` gates on
                # result internally (Loss/Draw only; a win is out of scope), so a
                # draw flows through here exactly like a loss. The Primary Factor
                # stays strictly event-derived; this never folds into or reranks
                # it. Faithfulness fences:
                #   * Each lever is passed only when it GENUINELY applies (the
                #     same thresholds the pre-match week briefing uses), so the
                #     honest "nothing you controlled" message is reachable.
                #   * The ignored recommendation (which ALWAYS wins) is the
                #     pre-match advisory recomputed from PRE-match inputs: the
                #     recent-results slice with the just-played match EXCLUDED,
                #     plus the locked plan's fatigue. This reproduces exactly what
                #     the week briefing showed for the final plan — a pure
                #     function of pre-match data, never hindsight (ADR 0002).
                from dodgeball_sim.manager_lesson import (
                    derive_manager_lesson,
                    is_inconclusive_factor,
                )

                if is_inconclusive_factor(
                    code=explanation.primary_factor.code,
                    confidence=explanation.primary_factor.confidence,
                ):
                    lesson = derive_manager_lesson(
                        result=result_pf,
                        factor_is_inconclusive=True,
                        ignored_recommendation=_aftermath_ignored_recommendation(
                            conn,
                            season_id=season_id,
                            current_match_id=record.match_id,
                            plan=plan,
                        ),
                        roster_edge=_aftermath_roster_edge(plan),
                        fatigue=_aftermath_fatigue_signal(plan),
                        weakest_role_group=_aftermath_weakest_group(
                            conn, player_club_id
                        ),
                    )
                    if lesson is not None:
                        aftermath["manager_lesson"] = lesson.as_dict()
        except Exception:
            pass

    # Task 1 (2026-05-27 playtest-fixes): surface playoff resolution.
    # Only present for playoff matches that needed a tiebreaker; the
    # frontend renders a banner only when this key exists.
    playoff_resolution = _load_playoff_resolution(conn, record, player_club_id)
    if playoff_resolution is not None:
        aftermath["playoff_resolution"] = playoff_resolution

    # Task 9 (2026-05-28 playtest-fixes): when the player's playoff run
    # ends, give the defeat its own beat instead of jumping straight to
    # the regular-season recap. Present only on a playoff *loss* the
    # player took part in. Polish surface -- omit on any failure.
    try:
        elimination = _load_elimination(
            conn,
            record,
            player_club_id,
            clubs=clubs,
            home_survivors=home_survivors,
            away_survivors=away_survivors,
            winner_id=_winner_id,
            top_performers=top_performers,
        )
        if elimination is not None:
            aftermath["elimination"] = elimination
    except Exception:
        pass

    # Task 10 (2026-05-28 playtest-fixes): celebrate a title-clinching win
    # up front instead of underselling it with the standard debrief.
    try:
        championship = _load_championship(
            conn,
            record,
            player_club_id,
            clubs=clubs,
            home_survivors=home_survivors,
            away_survivors=away_survivors,
            winner_id=_winner_id,
        )
        if championship is not None:
            aftermath["championship"] = championship
    except Exception:
        pass

    # Task 11 (2026-05-28 playtest-fixes): on a loss, give the player a
    # concrete next step instead of a dead end. Loss-only -- a win screen
    # doesn't need a to-do list.
    if str(dashboard.get("result")) == "Loss":
        try:
            panel = _load_improvement_panel(
                conn,
                season_id=season_id,
                player_club_id=player_club_id,
                plan=plan,
            )
            if panel:
                aftermath["improvement_panel"] = panel
        except Exception:
            pass

    # On an inconclusive loss the Manager Lesson (weakest_role_group / fatigue)
    # and the improvement panel (position_group / condition) can name the SAME
    # lever, computed from the same roster/lineup via the same pure helpers.
    # Drop the duplicate panel item, keep the loss-specific lesson, and keep
    # every non-duplicate panel item. Pure presentation assembly -- guarded so
    # a dedup hiccup can never block the payload.
    try:
        _dedup_lesson_panel(aftermath)
    except Exception:
        pass

    # Structural validation: confirm the assembled payload doesn't
    # contradict the resolved MatchResult (winner, survivor counts,
    # top-performer catch totals). If it does, log and fall back to a
    # minimal truthful payload rather than ship the contradiction.
    try:
        validate_postgame_payload(aftermath, record.result)
    except PostgameTruthError as exc:
        logger.error(
            "Postgame payload failed structural validation; "
            "falling back to degraded payload. match_id=%s reason=%s",
            getattr(record, "match_id", "<unknown>"),
            exc,
        )
        aftermath = _degraded_postgame_payload(
            record.result,
            home_club_id=record.home_club_id,
            away_club_id=record.away_club_id,
        )
    return aftermath


_OFFSEASON_SIM_STATES = frozenset(
    {
        CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
        CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
        CareerState.NEXT_SEASON_READY,
    }
)


def _off_phase_sim_message(state: CareerState) -> str:
    """Player-facing reason a match cannot be simulated in ``state``.

    Never surfaces raw lifecycle enum tokens to the UI; the offseason beats get
    a "head to the offseason" nudge, anything else a generic not-ready note.
    """
    if state in _OFFSEASON_SIM_STATES:
        return "The regular season is complete — continue in the offseason to start the next season."
    return "There's no match ready to simulate right now."


def simulate_week(
    conn: sqlite3.Connection,
    *,
    update: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Simulate the next user match in the active command-center week.

    Parameters
    ----------
    conn:
        Open SQLite connection to the career database.
    update:
        Optional dict with keys ``intent``, ``department_orders``,
        ``tactics``, ``lineup_player_ids`` to override the weekly plan.

    Returns
    -------
    dict with keys: status, message, plan, dashboard, next_state, aftermath.

    Raises
    ------
    SimulateWeekError
        If no active season/club, wrong career state, no user match, or
        roster validation fails.
    """
    player_club_id = get_state(conn, "player_club_id")
    season_id = get_state(conn, "active_season_id")
    if not player_club_id or not season_id:
        raise SimulateWeekError("No active season or club")

    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH:
        raise SimulateWeekError(_off_phase_sim_message(cursor.state))

    state = build_command_center_state(conn)
    existing = load_weekly_command_plan(conn, state["season_id"], state["week"], state["player_club_id"])

    intent_override = update.get("intent") if update else None
    if existing:
        plan = existing
    else:
        prior_intent = load_latest_weekly_plan_intent(conn, state["season_id"], state["week"], state["player_club_id"])
        plan = build_default_weekly_plan(state, intent=intent_override or prior_intent or "Balanced")
    plan = refresh_weekly_plan_context(plan, state)

    if update is not None:
        intent = update.get("intent")
        if intent and intent != plan.get("intent"):
            plan = build_default_weekly_plan(state, intent=intent)
        department_orders = update.get("department_orders")
        if department_orders:
            plan["department_orders"] = {**plan["department_orders"], **department_orders}
        tactics = update.get("tactics")
        if tactics:
            policy_values = dict(plan.get("tactics") or {})
            policy_values.update(dict(tactics))
            plan["tactics"] = CoachPolicy.from_dict(policy_values).as_dict()
        lineup_player_ids = update.get("lineup_player_ids")
        if lineup_player_ids:
            # WT-10: the inline override previously wrote straight into the plan
            # with NO validation, so a non-roster / duplicate / wrong-count set
            # could be persisted and later become a match_lineup_override —
            # making the saved plan and history lie about the fielded six. Route
            # it through the SAME validator the Roster Lineup Editor uses
            # (apply_manual_lineup). It runs BEFORE the first persistence
            # (save_weekly_command_plan below), so a rejection exits having
            # written nothing: no plan mutation, no match override, no history
            # row. The route maps the raised LineupViolation to HTTP 400 (see
            # the /api/lineup precedent in server.py).
            from types import SimpleNamespace
            from dodgeball_sim.command_center import _player_summary, _lineup_warnings
            from dodgeball_sim.lineup import apply_manual_lineup

            # Reuse the in-memory roster from the command-center state — same
            # club roster the editor validates against, no extra DB read.
            bundle = SimpleNamespace(
                club_id=player_club_id, roster=list(state["roster"])
            )
            # apply_manual_lineup enforces exactly STARTERS_COUNT starters, no
            # duplicates, and roster membership — wrong-count / duplicate /
            # not-on-roster all raise LineupViolation here.
            result = apply_manual_lineup(bundle, starters=lineup_player_ids)
            # Valid path: replace the WHOLE lineup dict so player_ids / players /
            # summary stay mutually consistent (a half-updated dict would itself
            # be an ADR-0002 lie). Use the validated starters directly — not the
            # recommendation builder, whose Develop-Youth swap would silently
            # override the player's explicit six. _player_summary keeps the
            # players shape identical to the WT-9 build/refresh path.
            plan["lineup"] = {
                "player_ids": [s.player_id for s in result.starters],
                "players": [_player_summary(s.player) for s in result.starters],
                "summary": "User-adjusted lineup saved for the command plan.",
            }
            # Recompute the sibling readiness warnings against the override six
            # (refresh_weekly_plan_context computed them for the default six), so
            # the saved plan and the history row never describe a six other than
            # the one actually fielded.
            plan["warnings"] = _lineup_warnings(
                list(state["roster"]),
                plan["lineup"]["player_ids"],
                plan.get("intent") or "Balanced",
                plan.get("tactics") or {},
            )

    save_weekly_command_plan(conn, plan)

    if state.get("is_bye"):
        return _simulate_bye_week(conn, state=state, plan=plan, cursor=cursor)

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    season, chosen, stop_reason = _choose_next_user_match_after_automation(conn, season, clubs, player_club_id)

    if not chosen:
        if stop_reason == "season_complete":
            cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
            save_career_state_cursor(conn, cursor)
            conn.commit()
            return {
                "status": "success",
                "message": "Season complete. Offseason review is ready.",
                "plan": plan,
                "dashboard": state.get("latest_dashboard")
                or {
                    "season_id": season_id,
                    "week": state["week"],
                    "match_id": None,
                    "opponent_name": "Season complete",
                    "result": "Season Complete",
                    "lanes": [],
                },
                "next_state": cursor.state.value,
                "aftermath": {
                    "headline": "Season Complete",
                    "match_card": None,
                    "player_growth_deltas": [],
                    "standings_shift": [],
                    "recruit_reactions": [],
                },
            }
        raise SimulateWeekError(f"No user match available: {stop_reason}")

    scheduled = chosen[0]
    completed = load_completed_match_ids(conn, season_id)
    week_matches = [
        match
        for match in sorted(season.matches_for_week(scheduled.week), key=lambda item: item.match_id)
        if match.match_id not in completed
    ]
    _apply_command_plan_to_match(conn, plan, scheduled.match_id, player_club_id)
    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    _validate_match_rosters(week_matches, rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"

    # load_standings already applies the official-vs-legacy sort authoritatively
    # (via match_records.config_version), so reuse its ordering directly.
    standings_before_raw = load_standings(conn, season_id)
    standings_before = list(standings_before_raw)
    prepare_ai_plans_for_matches(
        conn,
        season_id=season_id,
        season=season,
        matches=week_matches,
        clubs=clubs,
        rosters=rosters,
        player_club_id=player_club_id,
        standings_rows=standings_before_raw,
        apply_plan=_apply_command_plan_to_match,
        load_plan=load_weekly_command_plan,
        save_plan=save_weekly_command_plan,
    )

    # Reload clubs so the engine sees the coach policies just persisted by the
    # plan applications above. ``_apply_command_plan_to_match`` (user) and
    # ``prepare_ai_plans_for_matches`` (AI) write updated ``coach_policy`` rows;
    # the ``clubs`` dict loaded earlier is stale, and the engine builds each
    # team's tactics from ``club.coach_policy``. Without this reload the locked
    # tactical plan never reaches the match — and the recap records the base
    # policy instead of the player's choice.
    clubs = load_clubs(conn)
    records = [
        simulate_scheduled_match(
            conn,
            scheduled=week_match,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )
        for week_match in week_matches
    ]
    record = next(item for item in records if item.match_id == scheduled.match_id)
    recompute_regular_season_standings(conn, season)
    standings_after_raw = load_standings(conn, season_id)
    standings_after = list(standings_after_raw)
    dashboard = build_post_week_dashboard(conn, plan, record)
    save_command_history_record(
        conn,
        {
            "season_id": season_id,
            "week": record.week,
            "match_id": record.match_id,
            "opponent_club_id": (
                record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
            ),
            "intent": plan["intent"],
            "plan": plan,
            "dashboard": dashboard,
        },
    )

    season = load_season(conn, season.season_id)
    season, next_chosen, _stop_reason = _choose_next_user_match_after_automation(
        conn, season, clubs, player_club_id
    )
    if not next_chosen:
        # Defensive guard: before going to offseason, scan for any unplayed
        # playoff matches involving the player (catches bracket creation edge cases).
        from dodgeball_sim.playoffs import is_playoff_match_id
        completed_ids = load_completed_match_ids(conn, season_id)
        pending_user_playoff = [
            m for m in season.scheduled_matches
            if is_playoff_match_id(season.season_id, m.match_id)
            and m.match_id not in completed_ids
            and player_club_id in (m.home_club_id, m.away_club_id)
        ]
        if pending_user_playoff:
            next_chosen = pending_user_playoff[:1]
    if next_chosen:
        # PT4-02: next TIMELINE stop, not next match week (byes count).
        cursor = dataclasses.replace(
            cursor,
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            week=current_week(conn, season) or next_chosen[0].week,
            match_id=None,
        )
    else:
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    save_career_state_cursor(conn, cursor)
    conn.commit()

    aftermath = _build_aftermath(
        conn,
        dashboard,
        record,
        season_id,
        standings_before,
        standings_after,
        clubs,
        plan=plan,
        player_club_id=player_club_id,
    )

    return {
        "status": "success",
        "message": f"Simulated Week {record.week} command plan.",
        "plan": plan,
        "dashboard": dashboard,
        "next_state": cursor.state.value,
        "aftermath": aftermath,
    }


# Safety cap so a malformed schedule can never spin the auto-pilot forever.
_AUTO_PILOT_HARD_CAP = 120

# WT-29: fast-forward stop points the player can choose. Each maps to a
# ``max_weeks`` cap on auto_pilot_weeks; "offseason" is uncapped (run to the end
# of playoffs, the historical behaviour). The caps align to genuine decision
# boundaries, so the disclosure dialog can name exactly what is being skipped.
FAST_FORWARD_STOP_POINTS = ("next_bye", "pre_playoffs", "offseason")


def resolve_fast_forward_cap(
    conn: sqlite3.Connection, stop_point: str | None
) -> tuple[int | None, str]:
    """Map a fast-forward ``stop_point`` to a ``max_weeks`` cap.

    Returns ``(cap, resolved_stop_point)``. ``cap`` is ``None`` for "offseason"
    (or an unrecognised value, which defaults to running to the end) and an
    integer count of remaining user-relevant *weeks* (each user match OR bye is
    one auto-pilot step) for the bounded stop points.

    The caps are derived only from the schedule the player can already see:

    * **pre_playoffs** — stop after the last REGULAR-SEASON user step. Playoff
      matches are not pre-scheduled, so this is the count of the player's
      remaining regular-season weeks (matches + byes) from the current week on.
    * **next_bye** — stop at the player's next bye week (inclusive). If no bye
      remains this season, it honestly falls back to ``pre_playoffs`` rather
      than silently running on.
    * **offseason** — uncapped (``None``); an explicit, disclosed acceptance of
      the persisted defaults through playoffs.
    """
    if not stop_point or stop_point == "offseason" or stop_point not in FAST_FORWARD_STOP_POINTS:
        return None, "offseason"

    from dodgeball_sim.playoffs import is_playoff_match_id

    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id or not player_club_id:
        return None, "offseason"

    season = load_season(conn, season_id)
    week = current_week(conn, season) or 0
    completed = load_completed_match_ids(conn, season_id)

    # Regular-season weeks from the current week onward (the window the player is
    # about to fast-forward through). Playoff weeks are excluded — they are not
    # pre-scheduled and "pre_playoffs"/"next_bye" both live in the regular season.
    regular = [
        match
        for match in season.scheduled_matches
        if not is_playoff_match_id(season_id, match.match_id)
    ]
    upcoming_regular_weeks = sorted(
        {match.week for match in regular if match.week >= week and week > 0}
    )
    user_regular_weeks = {
        match.week
        for match in regular
        if player_club_id in (match.home_club_id, match.away_club_id)
    }

    # Each remaining regular week is exactly one auto-pilot step for the player
    # (a user match, or a bye that still advances one week).
    pre_playoffs_cap = len(upcoming_regular_weeks)

    if stop_point == "pre_playoffs":
        return max(pre_playoffs_cap, 0), "pre_playoffs"

    # next_bye: the first upcoming regular week in which the player has NO match.
    next_bye_week = next(
        (w for w in upcoming_regular_weeks if w not in user_regular_weeks),
        None,
    )
    if next_bye_week is None:
        # No bye left — fall back to stopping before the playoffs, disclosed.
        return max(pre_playoffs_cap, 0), "pre_playoffs"
    steps_to_bye = sum(1 for w in upcoming_regular_weeks if w <= next_bye_week)
    return max(steps_to_bye, 0), "next_bye"


def auto_pilot_weeks(
    conn: sqlite3.Connection,
    *,
    max_weeks: int | None = None,
) -> dict[str, Any]:
    """Fast-forward the command-center loop using persisted defaults.

    Repeatedly simulates the active user week via :func:`simulate_week` with
    ``update=None``. Passing no update means each skipped week reuses the
    persisted weekly plan when present, otherwise rebuilds the default plan from
    the *last* intent and the canonical fielded-6 (best-by-role/OVR lineup) — so
    auto-piloted weeks field exactly what a manual pass would. Readiness gates
    are an advisory briefing concern and never block simulation, so skipped
    weeks auto-satisfy by construction. Bye weeks advance transparently.

    The loop runs until the season completes (cursor leaves
    ``SEASON_ACTIVE_PRE_MATCH``) or ``max_weeks`` weeks have been simulated,
    whichever comes first. Determinism is inherited from the seeded per-match
    RNG used by :func:`simulate_week`: two careers started from the same
    ``root_seed`` produce identical week-by-week results.

    Parameters
    ----------
    conn:
        Open SQLite connection to the career database.
    max_weeks:
        Optional cap on how many weeks to simulate. ``None`` runs to the end of
        the season. Values < 1 are treated as a no-op.

    Returns
    -------
    dict with keys: ``status``, ``message``, ``weeks_simulated``,
    ``stop_reason`` (``"season_complete"`` | ``"max_weeks"`` | ``"already_complete"``),
    ``next_state``, ``week_summaries`` (one ``{week, opponent_name, result}``
    per simulated week), ``final_dashboard``, and ``final_aftermath``.

    Raises
    ------
    SimulateWeekError
        If the career is not in ``season_active_pre_match`` when called.
    """
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH:
        if cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT:
            return {
                "status": "success",
                "message": "Season already complete; offseason review is ready.",
                "weeks_simulated": 0,
                "stop_reason": "already_complete",
                "next_state": cursor.state.value,
                "week_summaries": [],
                "final_dashboard": None,
                "final_aftermath": None,
            }
        raise SimulateWeekError(_off_phase_sim_message(cursor.state))

    if max_weeks is not None and max_weeks < 1:
        return {
            "status": "success",
            "message": "No weeks requested.",
            "weeks_simulated": 0,
            "stop_reason": "max_weeks",
            "next_state": cursor.state.value,
            "week_summaries": [],
            "final_dashboard": None,
            "final_aftermath": None,
        }

    summaries: list[dict[str, Any]] = []
    last_result: dict[str, Any] | None = None
    stop_reason = "season_complete"
    cap = _AUTO_PILOT_HARD_CAP if max_weeks is None else min(max_weeks, _AUTO_PILOT_HARD_CAP)

    while len(summaries) < cap:
        result = simulate_week(conn, update=None)
        last_result = result
        dashboard = result.get("dashboard") or {}
        summaries.append(
            {
                "week": dashboard.get("week"),
                "opponent_name": dashboard.get("opponent_name"),
                "result": dashboard.get("result"),
            }
        )
        if result.get("next_state") != CareerState.SEASON_ACTIVE_PRE_MATCH.value:
            stop_reason = "season_complete"
            break
    else:
        # Loop exhausted the cap without the season completing.
        stop_reason = "max_weeks"

    final_state = (
        last_result.get("next_state")
        if last_result
        else load_career_state_cursor(conn).state.value
    )
    return {
        "status": "success",
        "message": f"Auto-piloted {len(summaries)} week(s).",
        "weeks_simulated": len(summaries),
        "stop_reason": stop_reason,
        "next_state": final_state,
        "week_summaries": summaries,
        "final_dashboard": last_result.get("dashboard") if last_result else None,
        "final_aftermath": last_result.get("aftermath") if last_result else None,
    }
