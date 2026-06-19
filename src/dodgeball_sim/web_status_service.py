from __future__ import annotations

import dataclasses
import json
import sqlite3
from typing import Any

from .career_state import CareerStateCursor
from .development import (
    calculate_potential_tier,
    _normalize_growth_curve,
    _peak_window,
    _TRAJECTORY_POTENTIAL_FLOOR,
)
from .league_memory import recent_match_item
from .models import CoachPolicy
from .persistence import (
    CorruptSaveError,
    get_state,
    load_all_rosters,
    load_awards,
    load_career_state_cursor,
    load_club_roster,
    load_clubs,
    load_completed_match_ids,
    load_lineup_default,
    load_player_trajectory,
    load_playoff_bracket,
    load_season,
    load_season_outcome,
    load_standings,
    load_weekly_command_plan,
    save_club,
    save_lineup_default,
    set_state,
)
from .playoffs import PLAYOFF_FIELD_SIZE, playoff_stage_label
from .view_models import build_schedule_rows, build_wire_items


def player_archetype_label(player) -> str:
    """Expose the same recruiting-facing label used elsewhere in Plan B.

    Keeps roster, recruit-board, and scout-facing copy aligned.
    """
    from .recruitment import archetype_for_player

    return archetype_for_player(player)


def career_state_payload(cursor: CareerStateCursor) -> dict[str, Any]:
    return {
        "state": cursor.state.value,
        "season_number": cursor.season_number,
        "week": cursor.week,
        "offseason_beat_index": cursor.offseason_beat_index,
        "match_id": cursor.match_id,
    }


def build_status_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    clubs = load_clubs(conn) if player_club_id else {}
    player_club = clubs.get(player_club_id) if player_club_id else None
    season = load_season(conn, season_id) if season_id else None
    return {
        "status": "ok",
        "state": career_state_payload(cursor),
        "context": {
            "season_id": season_id,
            "player_club_id": player_club_id,
            "player_club_name": player_club.name if player_club else player_club_id,
            "season_year": season.year if season else None,
            "ruleset_selection": get_state(conn, "ruleset_selection"),
        },
    }


def _load_last_offseason_ovr_deltas(conn: sqlite3.Connection, club_id: str) -> dict[str, tuple[int, int]]:
    """Return a mapping of player_id -> (before_ovr, after_ovr) from the most recent offseason.

    This is the only genuine before/after OVR data available: the offseason
    development JSON is overwritten each year, so this represents the **latest**
    offseason only (not a multi-season series). Returns an empty dict when no
    offseason has run yet.
    """
    raw = get_state(conn, "offseason_development_json")
    if not raw:
        return {}
    try:
        rows = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    result: dict[str, tuple[int, int]] = {}
    for row in rows:
        if row.get("club_id") != club_id:
            continue
        pid = row.get("player_id")
        before = row.get("before")
        after = row.get("after")
        if pid and before is not None and after is not None:
            result[pid] = (int(round(float(before))), int(round(float(after))))
    return result


def build_roster_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    try:
        roster = load_club_roster(conn, player_club_id)
    except (CorruptSaveError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CorruptSaveError("roster save data is damaged") from exc
    lineup = load_lineup_default(conn, player_club_id)

    # Phase 5 — Growth legibility: load last-offseason deltas once, keyed by player id.
    # offseason_development_json holds before/after OVR for each player who went through
    # the most recent offseason. It is overwritten each year, so this is the latest
    # single-offseason delta — not a multi-season time series.
    last_offseason_deltas = _load_last_offseason_ovr_deltas(conn, player_club_id)

    enriched = []
    for player in roster:
        player_dict = dataclasses.asdict(player)
        ovr = int(round(player.overall_skill()))
        player_dict["overall"] = ovr
        player_dict["role"] = player_archetype_label(player)
        player_dict["scouting_confidence"] = 3
        player_dict["weekly_ovr_history"] = [ovr]

        # Phase 5 — Growth legibility: Player Card fields.
        # "Ceiling" is the highest OVR the development engine can actually
        # reach for this player, so it is computed exactly the way the engine
        # does: the stored potential, raised by the scouted-trajectory floor
        # when one exists, and never below the current OVR (development only
        # closes headroom; it cannot pull a player down). Legacy saves carry
        # seeded potential values below current OVR — displaying those raw
        # would claim a "highest projected OVR" the player has already passed.
        stored_potential = int(player.traits.potential)
        trajectory = load_player_trajectory(conn, player.id)
        trajectory_floor = _TRAJECTORY_POTENTIAL_FLOOR.get(trajectory)
        effective_potential = max(
            stored_potential,
            int(trajectory_floor) if trajectory_floor is not None else stored_potential,
        )
        ceiling = max(effective_potential, ovr)
        headroom = max(0, ceiling - ovr)
        player_dict["potential_tier"] = calculate_potential_tier(ceiling)
        growth_curve_str = _normalize_growth_curve(player.traits.growth_curve)
        _, peak_end = _peak_window(growth_curve_str)
        if player.age > peak_end:
            projected_growth = "declining"
        elif headroom <= 0:
            projected_growth = "plateauing"
        else:
            projected_growth = "growing"
        player_dict["potential_ceiling"] = ceiling
        player_dict["headroom"] = headroom
        player_dict["projected_growth"] = projected_growth
        
        core_skills = [
            ("Accuracy", player.ratings.accuracy),
            ("Power", player.ratings.power),
            ("Dodge", player.ratings.dodge),
            ("Catch", player.ratings.catch),
        ]
        core_skills.sort(key=lambda x: x[1], reverse=True)
        player_dict["bio_strongest_attr"] = core_skills[0][0]
        player_dict["bio_secondary_attr"] = core_skills[1][0]

        # Season-over-season OVR trend: no per-season ratings history is stored in
        # the database (player_season_stats only holds match stats, not ratings).
        # Best available: last offseason's before/after from offseason_development_json.
        # Fresh saves (no offseason run yet) get None — honest empty-state.
        # After the first offseason, ovr_season_trend is a 2-element [before, after]
        # sparkline from that latest offseason. Not a full multi-season series.
        delta_pair = last_offseason_deltas.get(player.id)
        player_dict["ovr_season_trend"] = list(delta_pair) if delta_pair is not None else None

        if "traits" in player_dict:
            player_dict["traits"].pop("potential", None)
        enriched.append(player_dict)

    # Playtest 3 F-8: the Release control warns before cutting a player who
    # carries an OPEN promise (releasing them breaks it immediately).
    from .roster_moves import open_promise_player_ids

    return {
        "club_id": player_club_id,
        "roster": enriched,
        "default_lineup": lineup,
        "lineup_auto_reorder": lineup_auto_reorder_enabled(conn),
        "open_promise_player_ids": sorted(open_promise_player_ids(conn)),
    }


# V19 Task 8 (owner-decided 2026-06-10, CFB26 depth-chart pattern): the
# lineup is either hands-on (manual saves, one-shot Auto-assign) or
# set-and-forget (auto-reorder each offseason). Default ON for new careers —
# the V18 sweeps measured the silent stale-lineup default costing a passive
# career 20pp of title share. A manual lineup save flips it OFF (hands-on
# intent); the editor toggle flips it back any time.
LINEUP_AUTO_REORDER_STATE_KEY = "lineup_auto_reorder"


def lineup_auto_reorder_enabled(conn: sqlite3.Connection) -> bool:
    return (get_state(conn, LINEUP_AUTO_REORDER_STATE_KEY) or "1") == "1"


def set_lineup_auto_reorder_payload(conn: sqlite3.Connection, enabled: bool) -> dict[str, Any]:
    set_state(conn, LINEUP_AUTO_REORDER_STATE_KEY, "1" if enabled else "0")
    conn.commit()
    return {"status": "saved", "lineup_auto_reorder": enabled}


def auto_assign_lineup_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    """One-shot CFB26-style Auto-assign: seat the optimal six right now.

    A manual TOOL, not a mode change — it does not touch the auto-reorder
    toggle, so a hands-on manager can auto-assign and keep tweaking.
    """
    from .lineup import check_lineup_liabilities, optimize_ai_lineup

    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")
    roster = load_club_roster(conn, player_club_id)
    ordered = optimize_ai_lineup(roster)
    save_lineup_default(conn, player_club_id, ordered)
    conn.commit()
    warnings = check_lineup_liabilities(roster, ordered[:6])
    return {
        "status": "saved",
        "ordered_player_ids": ordered,
        "warnings": warnings,
        "lineup_auto_reorder": lineup_auto_reorder_enabled(conn),
    }


def build_tactics_payload(conn: sqlite3.Connection) -> dict[str, str]:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    club = load_clubs(conn).get(player_club_id)
    if club is None:
        raise LookupError("Club not found")
    return club.coach_policy.as_dict()


def update_manual_lineup_payload(
    conn: sqlite3.Connection,
    starter_ids: list[str] | None,
) -> dict[str, Any]:
    """Persist a manual lineup override for the player's club.

    ``starter_ids`` of ``None`` clears the override and lets ``LineupResolver``
    fall back to the roster's natural OVR order. Otherwise the starters are
    structurally validated by ``apply_manual_lineup`` and the resolved order
    (starters + OVR-sorted bench) is saved via ``save_lineup_default``.

    Raises ``LineupViolation`` on structural failure; the route maps the
    ``.reason`` tag to a 400 with the same string so the frontend can show an
    inline error keyed to the offending row.
    """
    from types import SimpleNamespace
    from .lineup import LineupResolver, apply_manual_lineup, check_lineup_liabilities

    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    if starter_ids is None:
        conn.execute(
            "DELETE FROM lineup_default WHERE club_id = ?",
            (player_club_id,),
        )
        conn.commit()
        # Return the freshly-resolved auto-fill ordering so the client can
        # update its cached roster view without a follow-up refetch.
        roster = load_club_roster(conn, player_club_id)
        resolved = LineupResolver().resolve(roster, default=None, override=None)
        return {
            "status": "cleared",
            "ordered_player_ids": resolved,
            "warnings": [],
        }

    roster = load_club_roster(conn, player_club_id)
    bundle = SimpleNamespace(club_id=player_club_id, roster=roster)
    result = apply_manual_lineup(bundle, starters=starter_ids)
    save_lineup_default(conn, player_club_id, result.ordered_player_ids)
    # V19 Task 8: a manual save IS the hands-on signal — flip auto-reorder
    # off so the offseason never overwrites a deliberately set lineup. The
    # editor toggle turns it back on explicitly.
    set_state(conn, LINEUP_AUTO_REORDER_STATE_KEY, "0")
    conn.commit()

    warnings = check_lineup_liabilities(roster, [s.player_id for s in result.starters])
    return {
        "status": "saved",
        "ordered_player_ids": result.ordered_player_ids,
        "warnings": warnings,
        "lineup_auto_reorder": False,
    }


def update_tactics_payload(conn: sqlite3.Connection, policy_values: dict[str, Any]) -> dict[str, str]:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise ValueError("No player club assigned")

    clubs = load_clubs(conn)
    club = clubs.get(player_club_id)
    if club is None:
        raise LookupError("Club not found")

    new_policy = CoachPolicy.from_dict(policy_values)
    updated_club = dataclasses.replace(club, coach_policy=new_policy)
    roster = load_club_roster(conn, player_club_id)
    save_club(conn, updated_club, roster)
    conn.commit()
    return {"status": "success"}


# Faithfulness (ADR 0002 / bug #7): the standings "Plan" column shows a club's
# weekly *program intent* (the stored `plan["intent"]`, one of command_center
# `INTENTS`). The command center (where the player SETS it) renders these intent
# ids with friendlier labels — e.g. the player picks the tile labeled
# "Aggressive", which stores intent "Win Now". Emitting the raw "Win Now" in
# standings made the same decision read as two different words across screens.
# This map mirrors the 4 player-facing labels from the frontend command center
# (`frontend/src/components/match-week/command-center/PreSimDashboard.tsx`
# `approaches`); keep the two in sync. Any other intent (e.g. the AI-only
# "Develop Youth", or a future one) passes through unchanged — exactly as the
# command center's own `intentLabels.get(x) ?? x` fallback does — so no label
# is ever invented or blanked.
_INTENT_DISPLAY_LABELS = {
    "Balanced": "Balanced",
    "Win Now": "Aggressive",
    "Prepare For Playoffs": "Control",
    "Preserve Health": "Defensive",
}


def _intent_display_label(intent: str) -> str:
    """Translate a stored program intent to its command-center display label.

    Unknown / unmapped intents (incl. the AI-only "Develop Youth") return
    verbatim, matching the frontend command center's passthrough fallback.
    """
    return _INTENT_DISPLAY_LABELS.get(intent, intent)


def build_standings_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    from .persistence import load_program_trajectories
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id:
        raise ValueError("No active season")

    cursor = load_career_state_cursor(conn)
    is_offseason = cursor.state.value in (
        "season_complete_offseason_beat",
        "season_complete_recruitment_pending",
        "next_season_ready",
    )

    clubs = load_clubs(conn)
    saved = {row.club_id: row for row in load_standings(conn, season_id)}
    current_week = current_week_number(conn, season_id)
    rows = []
    for club_id, club in clubs.items():
        row = saved.get(club_id)
        latest_plan = latest_visible_plan(conn, season_id, current_week, club_id)
        trajectories = load_program_trajectories(conn, club_id)
        year_num = len(trajectories) + 1
        # Faithfulness (ADR 0002 / WT-24): the standings identity label must name
        # the rival's REAL archetype — the value the AI actually plays as — not a
        # separate hand-maintained per-club flavor map that can drift from the
        # mechanics. `program_archetype` (from `classify_club_archetype`) is
        # already a human-friendly Title-Case string, so it is the display label
        # verbatim. (`archetype_display_name` is the PlayerArchetype humanizer and
        # is a no-op for program archetypes, so it is intentionally not used here.)
        identity = club.program_archetype
        # Note: "Yr N" here is the franchise's tenure year, not the league
        # season number — abbreviated to reduce collision with the season label.
        traj_label = f"Yr {year_num} · {identity}"
        rows.append(
            {
                "club_id": club_id,
                "club_name": club.name,
                "wins": row.wins if row else 0,
                "losses": row.losses if row else 0,
                "draws": row.draws if row else 0,
                "points": row.points if row else 0,
                "elimination_differential": row.elimination_differential if row else 0,
                "game_point_differential": row.game_point_differential if row else 0,
                "total_game_points_scored": row.total_game_points_scored if row else 0,
                "is_user_club": club_id == player_club_id,
                "latest_approach": _intent_display_label(latest_plan["intent"]) if latest_plan else "Balanced",
                "program_archetype": club.program_archetype,
                "program_trajectory_label": traj_label,
            }
        )
    # V20 §7.3 survivors cleanup: official careers rank on game-point fields
    # (mirrors season.compute_standings exactly — this payload previously
    # tiebroke on the survivor-noise differential, so the web standings
    # order could disagree with the persisted standings on officials).
    is_official_career = (get_state(conn, "ruleset_selection") or "").startswith("official")
    if is_official_career:
        rows.sort(key=lambda item: (
            -item["points"],
            -item["total_game_points_scored"],
            -item["game_point_differential"],
            item["club_id"],
        ))
    else:
        rows.sort(key=lambda item: (-item["points"], -item["elimination_differential"], item["club_id"]))

    # V23: on pyramid saves the flat `standings` list becomes the USER'S
    # DIVISION table (so every existing consumer shows the table the player
    # is actually in), and the full pyramid rides alongside in `divisions`.
    from .world import DIVISIONS, pyramid_world_active

    division_payload: dict[str, Any] | None = None
    divisions_payload: list[dict[str, Any]] | None = None
    if pyramid_world_active(conn):
        from .persistence import load_division_map

        division_map = load_division_map(conn, season_id)
        user_division_id = (
            division_map[player_club_id].division_id
            if player_club_id in division_map
            else None
        )
        divisions_payload = []
        user_division_rows: list[dict[str, Any]] | None = None
        for division in DIVISIONS:
            division_rows = [
                row for row in rows
                if division_map.get(row["club_id"])
                and division_map[row["club_id"]].division_id == division.division_id
            ]
            if not division_rows:
                continue
            block = {
                "division_id": division.division_id,
                "name": division.name,
                "short_name": division.short_name,
                "tier": division.tier,
                "kind": division.kind,
                "is_user_division": division.division_id == user_division_id,
                "standings": division_rows,
                "movement": _division_movement_rules(division.division_id),
            }
            divisions_payload.append(block)
            if division.division_id == user_division_id:
                division_payload = {
                    key: block[key]
                    for key in ("division_id", "name", "short_name", "tier", "kind", "movement")
                }
                user_division_rows = division_rows
        # Reassign only after the loop: the per-division filters above must
        # all read the FULL table (reassigning mid-loop dropped the Circuit,
        # which sorts after the user's district — caught in the live walk).
        if user_division_rows is not None:
            rows = user_division_rows

    recent = conn.execute(
        """
        SELECT match_id, week, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors, scoring_model,
               home_game_points, away_game_points
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 40
        """,
        (season_id,),
    ).fetchall()
    if divisions_payload is not None:
        # Pyramid: the "recent results" strip stays the player's division
        # (a Circuit scoreline between two clubs you never face is noise here;
        # the pyramid view carries the rest of the world).
        recent = [
            row for row in recent
            if division_map.get(row["home_club_id"])
            and division_map[row["home_club_id"]].division_id == user_division_id
        ]
    recent = recent[:5]

    season = load_season(conn, season_id)
    # Count unplayed user matches the same way the command center does, so the
    # standings "to play" line never contradicts the pre-sim dashboard. This is
    # games (byes excluded), not calendar weeks remaining.
    user_games_remaining = 0
    if player_club_id:
        completed_ids = load_completed_match_ids(conn, season_id)
        user_games_remaining = sum(
            1
            for schedule_row in build_schedule_rows(season, completed_ids, player_club_id)
            if schedule_row.is_user_match and schedule_row.status != "played"
        )
    return {
        "season_id": season_id,
        "standings": rows,
        "recent_matches": [recent_match_item(row, clubs) for row in recent],
        "total_weeks": season.total_weeks(),
        "current_week": current_week or season.total_weeks(),
        "user_games_remaining": user_games_remaining,
        "playoff_spots": PLAYOFF_FIELD_SIZE,
        "is_offseason": is_offseason,
        # V20 §7.3: lets the standings UI show the differential that actually
        # ranks this career (game points on officials, survivors on legacy).
        "is_official_career": is_official_career,
        # V23: the player's division + the full pyramid (None on legacy saves).
        "division": division_payload,
        "divisions": divisions_payload,
        # V28: the league news wire HEADLINES (class_wire / event_news /
        # meta_report / league_bulletin) ride the standings payload so the
        # existing League Wire ticker surfaces them. HEADLINES ONLY — the
        # recent_matches block above already owns the match-result rows, so
        # folding the full news payload here double-printed results (PT5 fix).
        "wire_headlines": news_headline_items(conn, season_id),
    }


def _division_movement_rules(division_id: str) -> dict[str, Any]:
    """What's at stake at each end of a division table (V23 spec rules).

    Champions of D2/D3 auto-promote; the next four by regular-season rank
    play a promotion playoff for the second slot; the bottom two of D1/D2
    relegate; the Premier and Circuit tops feed WORLDS. The Circuit is
    closed — it represents the rest of the world.
    """
    rules = {
        "premier": {
            "auto_promotion": False,
            "promotion_playoff": False,
            "relegation_count": 2,
            "worlds_slots": 2,
            "summary": "Top 4 reach the playoffs; the two finalists go to Worlds (vs the International Circuit's two finalists). Bottom two teams face relegation.",
        },
        "challenger": {
            "auto_promotion": True,
            "promotion_playoff": True,
            "relegation_count": 2,
            "worlds_slots": 0,
            "summary": "Champion promotes · next four play a promotion playoff · bottom two relegate",
        },
        "district": {
            "auto_promotion": True,
            "promotion_playoff": True,
            "relegation_count": 0,
            "worlds_slots": 0,
            "summary": "Champion promotes · next four play a promotion playoff for the second slot",
        },
        "circuit": {
            "auto_promotion": False,
            "promotion_playoff": False,
            "relegation_count": 0,
            "worlds_slots": 2,
            "summary": "Closed international division · top two reach WORLDS",
        },
    }
    return rules.get(division_id, {
        "auto_promotion": False,
        "promotion_playoff": False,
        "relegation_count": 0,
        "worlds_slots": 0,
        "summary": "",
    })


def current_week_number(conn: sqlite3.Connection, season_id: str) -> int | None:
    row = conn.execute(
        "SELECT MIN(week) AS week FROM scheduled_matches WHERE season_id = ?",
        (season_id,),
    ).fetchone()
    if row is None:
        return None
    from .persistence import load_season
    from .game_loop import current_week

    season = load_season(conn, season_id)
    return current_week(conn, season) or season.total_weeks()


def latest_visible_plan(
    conn: sqlite3.Connection,
    season_id: str,
    current_week: int | None,
    club_id: str,
) -> dict[str, Any] | None:
    if current_week is None:
        return None
    row = conn.execute(
        """
        SELECT plan_json
        FROM weekly_command_plans
        WHERE season_id = ? AND club_id = ? AND week <= ?
        ORDER BY week DESC
        LIMIT 1
        """,
        (season_id, club_id, current_week),
    ).fetchone()
    return json.loads(row["plan_json"]) if row else None


def build_schedule_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id:
        raise ValueError("No active season")

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    completed = load_completed_match_ids(conn, season_id)
    rows = []
    for row in build_schedule_rows(season, completed, player_club_id):
        home = clubs.get(row.home_club_id)
        away = clubs.get(row.away_club_id)
        rows.append(
            {
                "match_id": row.match_id,
                "week": row.week,
                "home_club_id": row.home_club_id,
                "home_club_name": home.name if home else row.home_club_id,
                "away_club_id": row.away_club_id,
                "away_club_name": away.name if away else row.away_club_id,
                "status": row.status,
                "is_user_match": row.is_user_match,
                "stage": playoff_stage_label(season_id, row.match_id),
            }
        )
    return {"season_id": season_id, "schedule": rows}


def build_playoff_bracket_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    """Expose the current season's playoff bracket: seeds, rounds, results, champion."""
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        return {"active": False}
    bracket = load_playoff_bracket(conn, season_id)
    if bracket is None:
        return {"active": False}

    clubs = load_clubs(conn)
    player_club_id = get_state(conn, "player_club_id")
    standings = {row.club_id: row for row in load_standings(conn, season_id)}

    results: dict[str, dict[str, Any]] = {}
    for row in conn.execute(
        """
        SELECT match_id, home_club_id, away_club_id, winner_club_id,
               home_survivors, away_survivors, decided_by, narrative_note,
               scoring_model, home_game_points, away_game_points
        FROM match_records
        WHERE season_id = ?
        """,
        (season_id,),
    ).fetchall():
        results[row["match_id"]] = dict(row)

    def club_name(club_id: str | None) -> str | None:
        if club_id is None:
            return None
        club = clubs.get(club_id)
        return club.name if club else club_id

    seeds = []
    for index, club_id in enumerate(bracket.seeds):
        row = standings.get(club_id)
        seeds.append(
            {
                "seed": index + 1,
                "club_id": club_id,
                "club_name": club_name(club_id),
                "wins": row.wins if row else 0,
                "losses": row.losses if row else 0,
                "draws": row.draws if row else 0,
                "is_player_club": club_id == player_club_id,
            }
        )

    rounds = []
    for round_info in bracket.rounds:
        matches = []
        for match in round_info.get("matches", ()):
            result = results.get(match["match_id"])
            matches.append(
                {
                    "match_id": match["match_id"],
                    "home_club_id": match["home"],
                    "home_club_name": club_name(match["home"]),
                    "away_club_id": match["away"],
                    "away_club_name": club_name(match["away"]),
                    "home_survivors": result["home_survivors"] if result else None,
                    "away_survivors": result["away_survivors"] if result else None,
                    "winner_club_id": result["winner_club_id"] if result else None,
                    "status": "played" if result else "scheduled",
                    "decided_by": (result.get("decided_by") if result else None),
                    "narrative_note": (result.get("narrative_note") if result else None),
                    # Foam matches score by game points, not survivors; expose
                    # both so the bracket can show the meaningful scoreline
                    # instead of a survivors 0-0 that reads as "no game played".
                    "scoring_model": (result.get("scoring_model") if result else None),
                    "home_game_points": (result.get("home_game_points") if result else None),
                    "away_game_points": (result.get("away_game_points") if result else None),
                }
            )
        rounds.append({"round": round_info.get("round"), "matches": matches})

    outcome = load_season_outcome(conn, season_id)
    champion_club_id = outcome.champion_club_id if outcome else None

    return {
        "active": True,
        "season_id": season_id,
        "format": bracket.format,
        "status": bracket.status,
        "seeds": seeds,
        "rounds": rounds,
        "champion_club_id": champion_club_id,
        "champion_club_name": club_name(champion_club_id),
        "player_club_id": player_club_id,
    }


def build_news_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise ValueError("No active season")

    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    match_rows = conn.execute(
        """
        SELECT match_id, season_id, week, home_club_id, away_club_id,
               winner_club_id, home_survivors, away_survivors,
               scoring_model, home_game_points, away_game_points
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 20
        """,
        (season_id,),
    ).fetchall()
    items = build_wire_items(match_rows, clubs, load_awards(conn, season_id), rosters)
    payload_items = [
        {"tag": item.tag, "text": item.text, "match_id": item.match_id, "player_id": item.player_id}
        for item in items[:20]
    ]
    # The league-wide news HEADLINES ride at the top of the wire.
    payload_items = news_headline_items(conn, season_id) + payload_items
    return {"season_id": season_id, "items": payload_items}


# V24 class wire + V27 event news + V28 meta journalism / league bulletins:
# league-wide headline lines (news_headlines) — the chase target's destination
# (class_wire), the season's event journalism (event_news), the data-derived
# trend reports (meta_report), and the officiating bulletins (league_bulletin).
_WIRE_CATEGORIES = ("class_wire", "event_news", "meta_report", "league_bulletin")
_WIRE_CATEGORY_TAGS = {
    "class_wire": "Class Wire",
    "event_news": "Event Wire",
    "meta_report": "Meta Wire",
    "league_bulletin": "League Wire",
}


def news_headline_items(conn: sqlite3.Connection, season_id: str) -> list[dict[str, Any]]:
    """The league news-wire HEADLINES as wire items — NOT match results.

    Shared by ``build_news_payload`` and the standings ticker so headlines
    surface without duplicating the recent-results rows (which the standings
    ``recent_matches`` block already owns; folding the full news payload into the
    ticker double-printed every result and leaked the survivors scoreline).
    """
    from .persistence import load_news_headlines

    out: list[dict[str, Any]] = []
    for headline in load_news_headlines(conn, season_id):
        cat = headline.get("category")
        if cat not in _WIRE_CATEGORIES:
            continue
        entity_ids = headline.get("entity_ids") or []
        out.append({
            "tag": _WIRE_CATEGORY_TAGS.get(cat, "League Wire"),
            "text": headline["headline_text"],
            "match_id": None,
            "player_id": entity_ids[0] if entity_ids else None,
        })
    return out
