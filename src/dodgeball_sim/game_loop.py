from __future__ import annotations

import json
import sqlite3
from typing import Any, Mapping, Sequence

from .franchise import MatchRecord, extract_match_stats, simulate_match
from .league import Club
from .models import MatchSetup, Player, Team
from .persistence import (
    get_state,
    load_completed_match_ids,
    load_lineup_default,
    load_match_lineup_override,
    record_match,
    record_roster_snapshot,
    save_match_result,
    save_player_stats_batch,
    save_standings,
)
from .scheduler import ScheduledMatch
from .season import Season, SeasonResult, compute_standings


def current_week(conn: sqlite3.Connection, season: Season) -> int | None:
    completed = load_completed_match_ids(conn, season.season_id)
    for week in range(1, season.total_weeks() + 1):
        if any(match.match_id not in completed for match in season.matches_for_week(week)):
            return week
    return None


# V19b staff focus: the ONE department a club's staff concentrates on this
# week (plan.department_orders.focus_department). Two of the five focuses are
# MATCH preps consumed by both engines; the other three (training credits,
# scouting slot, culture courtship) land outside the match. A genuine weekly
# decision: one room gets the week, the others run standard.
# V22 Phase 4: with the club's HEAD RATINGS provided, the prep scales with
# the head running the week (staff_effects formulas). Without them — every
# AI club, whose staff stay abstracted — the legacy flat numbers apply
# (equivalent to ~rating-7x staff by the same formulas, so no side gets a
# user-only buff).
_MATCH_PREP_BY_FOCUS: dict[str, dict] = {
    # Film week: throwers read the court like +18 Tactical IQ (V19a consumer).
    "tactics": {"targeting_read_bonus": 18.0},
    # Recovery week: fatigue/stamina drag on action stats is halved.
    "conditioning": {"stamina_relief": 0.5},
}


def match_prep_from_plan(
    plan: Mapping[str, Any] | None,
    head_ratings: Mapping[str, float] | None = None,
) -> dict:
    """Derive the engine-facing match prep from a club's weekly plan.

    ``head_ratings`` (department -> primary rating) scales the prep with the
    head who runs the focused week; ``None`` keeps the legacy flat prep.
    """
    orders = dict((plan or {}).get("department_orders") or {})
    focus = str(orders.get("focus_department") or "").strip().lower()
    if head_ratings is not None and focus in head_ratings:
        from .staff_effects import conditioning_focus_relief, tactics_focus_tiq_bonus

        if focus == "tactics":
            return {"targeting_read_bonus": tactics_focus_tiq_bonus(head_ratings[focus])}
        if focus == "conditioning":
            return {"stamina_relief": conditioning_focus_relief(head_ratings[focus])}
    return dict(_MATCH_PREP_BY_FOCUS.get(focus, {}))


def simulate_scheduled_match(
    conn: sqlite3.Connection,
    *,
    scheduled: ScheduledMatch,
    clubs: Mapping[str, Club],
    rosters: Mapping[str, Sequence[Player]],
    root_seed: int,
    difficulty: str,
    record_engine_match: bool = True,
) -> MatchRecord:
    home_default = load_lineup_default(conn, scheduled.home_club_id)
    away_default = load_lineup_default(conn, scheduled.away_club_id)
    home_override = load_match_lineup_override(conn, scheduled.match_id, scheduled.home_club_id)
    away_override = load_match_lineup_override(conn, scheduled.match_id, scheduled.away_club_id)
    from .persistence import get_state, load_department_heads, load_weekly_command_plan
    ruleset_selection = get_state(conn, "ruleset_selection")
    # V19b: both clubs' staff-focus preps, symmetrically from their persisted
    # weekly plans (the user's plan and the AI plans share the same table).
    # V22 Phase 4: the USER club's prep scales with their actual department
    # heads (the heads table is user-only); AI clubs keep the legacy flat
    # prep, which the staff_effects anchors make ~rating-7x staff.
    player_club_id = get_state(conn, "player_club_id")
    user_head_ratings = {
        head["department"]: float(head["rating_primary"])
        for head in load_department_heads(conn)
    }
    home_prep = match_prep_from_plan(
        load_weekly_command_plan(conn, scheduled.season_id, scheduled.week, scheduled.home_club_id),
        user_head_ratings if scheduled.home_club_id == player_club_id else None,
    )
    away_prep = match_prep_from_plan(
        load_weekly_command_plan(conn, scheduled.season_id, scheduled.week, scheduled.away_club_id),
        user_head_ratings if scheduled.away_club_id == player_club_id else None,
    )
    record, _ = simulate_match(
        scheduled=scheduled,
        home_club=clubs[scheduled.home_club_id],
        away_club=clubs[scheduled.away_club_id],
        home_roster=list(rosters[scheduled.home_club_id]),
        away_roster=list(rosters[scheduled.away_club_id]),
        root_seed=root_seed,
        difficulty=difficulty,
        home_lineup_default=home_default,
        away_lineup_default=away_default,
        home_lineup_override=home_override,
        away_lineup_override=away_override,
        ruleset_selection=ruleset_selection,
        home_prep=home_prep or None,
        away_prep=away_prep or None,
    )
    persist_match_record(
        conn,
        record,
        clubs=clubs,
        rosters=rosters,
        difficulty=difficulty,
        record_engine_match=record_engine_match,
    )
    return record


def persist_match_record(
    conn: sqlite3.Connection,
    record: MatchRecord,
    *,
    clubs: Mapping[str, Club],
    rosters: Mapping[str, Sequence[Player]],
    difficulty: str | None = None,
    record_engine_match: bool = True,
) -> int | None:
    home_active_ids = record.home_active_player_ids or list(
        record.result.box_score["teams"][record.home_club_id]["players"].keys()
    )
    away_active_ids = record.away_active_player_ids or list(
        record.result.box_score["teams"][record.away_club_id]["players"].keys()
    )
    setup = MatchSetup(
        team_a=_team_snapshot_for_ids(
            clubs[record.home_club_id],
            rosters[record.home_club_id],
            home_active_ids,
        ),
        team_b=_team_snapshot_for_ids(
            clubs[record.away_club_id],
            rosters[record.away_club_id],
            away_active_ids,
        ),
    )
    engine_match_id = None
    if record_engine_match:
        engine_match_id = record_match(
            conn,
            setup=setup,
            result=record.result,
            difficulty=difficulty or get_state(conn, "difficulty", "pro") or "pro",
        )

    box = record.result.box_score["teams"]
    record_roster_snapshot(
        conn,
        match_id=record.match_id,
        club_id=record.home_club_id,
        players=list(rosters[record.home_club_id]),
        active_player_ids=record.home_active_player_ids,
    )
    record_roster_snapshot(
        conn,
        match_id=record.match_id,
        club_id=record.away_club_id,
        players=list(rosters[record.away_club_id]),
        active_player_ids=record.away_active_player_ids,
    )

    _home_survivors = box[record.home_club_id]["totals"]["living"]
    _away_survivors = box[record.away_club_id]["totals"]["living"]
    _winner_club_id = record.result.winner_team_id
    is_official = record.config_version and record.config_version.startswith("official:")
    if not is_official:
        if _winner_club_id is None and _home_survivors != _away_survivors:
            _winner_club_id = (
                record.home_club_id if _home_survivors > _away_survivors else record.away_club_id
            )
    scoring_model = "legacy"
    home_game_points = 0
    away_game_points = 0
    home_games_won = 0
    away_games_won = 0
    tied_games = 0
    no_point_games = 0
    official_score_json: str | None = None
    if is_official and record.result.official_metadata:
        meta = record.result.official_metadata
        scoring_model = "cloth" if "cloth" in (record.config_version or "") else "foam"
        # Adapter sets team_a == home_club, team_b == away_club (see
        # OfficialEngineAdapter._run_raw + franchise.simulate_match).
        if meta.get("team_a_id") == record.home_club_id:
            home_game_points = int(meta.get("team_a_game_points", 0))
            away_game_points = int(meta.get("team_b_game_points", 0))
            home_games_won = int(meta.get("team_a_games_won", 0))
            away_games_won = int(meta.get("team_b_games_won", 0))
        else:
            home_game_points = int(meta.get("team_b_game_points", 0))
            away_game_points = int(meta.get("team_a_game_points", 0))
            home_games_won = int(meta.get("team_b_games_won", 0))
            away_games_won = int(meta.get("team_a_games_won", 0))
        tied_games = int(meta.get("tied_games", 0))
        no_point_games = int(meta.get("no_point_games", 0))
        official_score_json = json.dumps(meta, default=str)

    save_match_result(
        conn,
        match_id=record.match_id,
        season_id=record.season_id,
        week=record.week,
        home_club_id=record.home_club_id,
        away_club_id=record.away_club_id,
        winner_club_id=_winner_club_id,
        home_survivors=_home_survivors,
        away_survivors=_away_survivors,
        home_roster_hash=record.home_roster_hash,
        away_roster_hash=record.away_roster_hash,
        config_version=record.config_version,
        ruleset_version=record.ruleset_version,
        meta_patch_id=record.meta_patch_id,
        seed=record.seed,
        event_log_hash=record.event_log_hash,
        final_state_hash=record.final_state_hash,
        engine_match_id=engine_match_id,
        scoring_model=scoring_model,
        home_game_points=home_game_points,
        away_game_points=away_game_points,
        home_games_won=home_games_won,
        away_games_won=away_games_won,
        tied_games=tied_games,
        no_point_games=no_point_games,
        official_score_json=official_score_json,
    )

    stats = extract_match_stats(
        record,
        list(rosters[record.home_club_id]),
        list(rosters[record.away_club_id]),
    )
    player_club_map = {player.id: record.home_club_id for player in rosters[record.home_club_id]}
    player_club_map.update({player.id: record.away_club_id for player in rosters[record.away_club_id]})
    save_player_stats_batch(conn, record.match_id, stats, player_club_map)
    return engine_match_id


def recompute_regular_season_standings(conn: sqlite3.Connection, season: Season) -> None:
    rows = conn.execute(
        "SELECT * FROM match_records WHERE season_id = ?",
        (season.season_id,),
    ).fetchall()
    results = []
    for row in rows:
        if row["match_id"].startswith(f"{season.season_id}_p_"):
            continue
        keys = list(row.keys())
        results.append(
            SeasonResult(
                match_id=row["match_id"],
                season_id=row["season_id"],
                week=row["week"],
                home_club_id=row["home_club_id"],
                away_club_id=row["away_club_id"],
                home_survivors=row["home_survivors"],
                away_survivors=row["away_survivors"],
                winner_club_id=row["winner_club_id"],
                seed=row["seed"],
                config_version=row["config_version"] if "config_version" in keys else "legacy",
                home_game_points=row["home_game_points"] if "home_game_points" in keys else 0,
                away_game_points=row["away_game_points"] if "away_game_points" in keys else 0,
                home_games_won=row["home_games_won"] if "home_games_won" in keys else 0,
                away_games_won=row["away_games_won"] if "away_games_won" in keys else 0,
                tied_games=row["tied_games"] if "tied_games" in keys else 0,
                no_point_games=row["no_point_games"] if "no_point_games" in keys else 0,
            )
        )
    save_standings(conn, season.season_id, compute_standings(results))
    # Rivalries ride the same post-match chokepoint: every web-path sim batch
    # (user week, AI batch, playoff round) recomputes standings, so rebuilding
    # here keeps the rivalry book in lockstep with the match records. Before
    # this, rivalry_records was only ever written by the legacy sandbox CLI —
    # the Dynasty Office, /api/history/league, and broadcast rivalry tags all
    # read a table the web game never fed.
    rebuild_rivalry_records(conn)


def season_sort_key(season_id: str) -> tuple[int, str]:
    """Numeric-aware sort key for ``season_N`` ids (string sort puts 10 < 2)."""
    suffix = str(season_id).rsplit("_", 1)[-1]
    if suffix.isdigit():
        return (int(suffix), "")
    return (1 << 30, str(season_id))


def rebuild_rivalry_records(conn: sqlite3.Connection) -> None:
    """Recompute the full rivalry book from persisted match records.

    Derivation from truth, not incremental updates: re-simulated or
    tie-resolution-patched matches can never double-count, and legacy saves
    gain their full rivalry history retroactively on the next recompute.
    Margins use each match's own scoring scale (game points when set-scored,
    survivors otherwise).
    """
    from .rivalries import rivalries_from_match_rows, rivalry_payload

    rows = conn.execute(
        """
        SELECT match_id, season_id, week, home_club_id, away_club_id,
               winner_club_id, home_survivors, away_survivors,
               home_game_points, away_game_points, scoring_model
        FROM match_records
        """
    ).fetchall()
    # Chronological order needs a NUMERIC season sort: the season_id strings
    # sort "season_10" before "season_2", which would scramble multi-season
    # last-meeting fields. Same hazard for any streak math over season_id.
    rows = sorted(
        rows, key=lambda r: (season_sort_key(r["season_id"]), r["week"], r["match_id"])
    )
    prepared = []
    for row in rows:
        season_id = row["season_id"]
        # Same prefix contract as playoffs.is_playoff_match_id (inlined to keep
        # this module free of a playoffs import).
        is_playoff = row["match_id"].startswith(f"{season_id}_p_")
        is_final = row["match_id"] == f"{season_id}_p_final"
        if (row["scoring_model"] or "legacy") != "legacy":
            margin = abs(int(row["home_game_points"] or 0) - int(row["away_game_points"] or 0))
        else:
            margin = abs(int(row["home_survivors"] or 0) - int(row["away_survivors"] or 0))
        prepared.append(
            {
                "match_id": row["match_id"],
                "season_id": season_id,
                "home_club_id": row["home_club_id"],
                "away_club_id": row["away_club_id"],
                "winner_club_id": row["winner_club_id"],
                "margin": margin,
                "was_playoff": is_playoff,
                "was_championship": is_final,
            }
        )
    records = rivalries_from_match_rows(prepared)
    conn.execute("DELETE FROM rivalry_records")
    from .persistence import save_rivalry_record

    for record in records.values():
        save_rivalry_record(
            conn, record.club_a_id, record.club_b_id, rivalry_payload(record)
        )


def _team_snapshot_for_ids(
    club: Club,
    roster: Sequence[Player],
    ordered_player_ids: Sequence[str],
) -> Team:
    players_by_id = {player.id: player for player in roster}
    players = [
        players_by_id[player_id]
        for player_id in ordered_player_ids
        if player_id in players_by_id
    ]
    return Team(
        id=club.club_id,
        name=club.name,
        players=tuple(players),
        coach_policy=club.coach_policy,
        chemistry=0.5,
    )


__all__ = [
    "current_week",
    "persist_match_record",
    "rebuild_rivalry_records",
    "recompute_regular_season_standings",
    "simulate_scheduled_match",
]
