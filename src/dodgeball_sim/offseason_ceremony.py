"""Offseason ceremony shared logic for both web app and Tkinter GUI."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .config import DEFAULT_CONFIG
from .career_state import CareerState, CareerStateCursor
from .copy_quality import title_label
from .development import apply_season_development, should_retire
from .franchise import create_season, trim_ai_roster_for_offseason
from .league import Club, Conference, League
from .models import Player
from .stats import PlayerMatchStats
from .awards import compute_season_awards
from .offseason_beats import build_rookie_class_preview, induct_hall_of_fame, ratify_records
from .persistence import (
    CorruptSaveError,
    fetch_season_player_stats,
    get_state,
    load_all_rosters,
    load_awards,
    load_clubs,
    load_department_heads,
    load_free_agents,
    load_player_career_stats,
    load_player_trajectory,
    load_prospect_pool,
    load_season,
    load_standings,
    save_awards,
    save_career_state_cursor,
    save_club,
    save_free_agents,
    save_lineup_default,
    save_player_career_stats,
    save_player_season_stats,
    save_retired_player,
    save_season,
    save_season_format,
    set_state,
)
from .playoffs import PLAYOFF_FORMAT
from .recruitment import generate_rookie_class, sign_prospect_to_club
from .rng import DeterministicRNG, derive_seed
from .season import Season, StandingsRow
from .view_models import normalize_root_seed


OFFSEASON_CEREMONY_BEATS = (
    "champion",
    "recap",
    "awards",
    "records_ratified",
    "hof_induction",
    "development",
    "retirements",
    "rookie_class_preview",
    "recruitment",
    "schedule_reveal",
)

_RECRUITMENT_BEAT_INDEX = OFFSEASON_CEREMONY_BEATS.index("recruitment")
_SCHEDULE_REVEAL_BEAT_INDEX = OFFSEASON_CEREMONY_BEATS.index("schedule_reveal")
AI_MIN_PLAYABLE_ROSTER_SIZE = 6
PLAYER_FREE_AGENT_RESERVE = 6


def _parse_json_list(raw: Optional[str]) -> list:
    try:
        parsed = json.loads(raw or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def compute_active_beats(
    records_payload_json: Optional[str],
    hof_payload_json: Optional[str],
    retirement_rows: List[Dict[str, Any]],
) -> List[str]:
    """Return the ordered subset of OFFSEASON_CEREMONY_BEATS that have real content."""
    _CONDITIONAL = {
        "records_ratified": lambda: bool(_parse_json_list(records_payload_json)),
        "hof_induction": lambda: bool(_parse_json_list(hof_payload_json)),
        "retirements": lambda: bool(retirement_rows),
    }
    return [
        beat for beat in OFFSEASON_CEREMONY_BEATS
        if beat not in _CONDITIONAL or _CONDITIONAL[beat]()
    ]


@dataclass(frozen=True)
class OffseasonCeremonyBeat:
    key: str
    title: str
    body: str


def clamp_offseason_beat_index(beat_index: Any) -> int:
    try:
        numeric = int(beat_index)
    except (TypeError, ValueError):
        numeric = 0
    return max(0, min(numeric, len(OFFSEASON_CEREMONY_BEATS) - 1))


def stored_root_seed(conn: sqlite3.Connection, default: int = 1) -> int:
    return normalize_root_seed(get_state(conn, "root_seed", str(default)), default_on_invalid=True)


def _is_already_signed(conn: sqlite3.Connection, class_year: int, player_id: str) -> bool:
    row = conn.execute(
        "SELECT is_signed FROM prospect_pool WHERE class_year = ? AND player_id = ?",
        (class_year, player_id),
    ).fetchone()
    return bool(row and row["is_signed"])


def create_next_manager_season(
    clubs: Mapping[str, Club],
    root_seed: int,
    season_number: int,
    year: int,
) -> Season:
    """Create the next Manager Mode season from the active club field."""
    league = League(
        league_id="manager_league",
        name="Dodgeball Premier League",
        conferences=(Conference("main", "Premier", tuple(clubs)),),
    )
    return create_season(f"season_{season_number}", year, league, root_seed=root_seed)


def _sign_ai_replacements(
    rosters: Dict[str, List[Player]],
    clubs: Mapping[str, Club],
    player_club_id: str,
    candidates: List[Player],
    min_size: int = AI_MIN_PLAYABLE_ROSTER_SIZE,
) -> List[Player]:
    """Fill depleted AI rosters from a deterministic candidate pool."""
    remaining = sorted(candidates, key=lambda player: (-player.overall(), player.id))
    ai_club_ids = sorted(club_id for club_id in clubs if club_id != player_club_id)
    while remaining:
        needy = [
            club_id
            for club_id in sorted(ai_club_ids, key=lambda cid: (len(rosters.get(cid, [])), cid))
            if len(rosters.get(club_id, [])) < min_size
        ]
        if not needy:
            break
        for club_id in needy:
            if not remaining:
                break
            roster = list(rosters.get(club_id, []))
            roster.append(replace(remaining.pop(0), club_id=club_id, newcomer=True))
            rosters[club_id] = roster
    return remaining


def ensure_ai_rosters_playable(
    conn: sqlite3.Connection,
    clubs: Mapping[str, Club],
    rosters: Mapping[str, List[Player]],
    root_seed: int,
    season_id: str,
    player_club_id: Optional[str] = None,
    min_size: int = AI_MIN_PLAYABLE_ROSTER_SIZE,
) -> bool:
    """Repair legacy or long-running saves whose AI clubs fell below starter count."""
    player_club_id = player_club_id or get_state(conn, "player_club_id") or ""
    updated_rosters = {club_id: list(roster) for club_id, roster in rosters.items()}
    shortfall = sum(
        max(0, min_size - len(updated_rosters.get(club_id, [])))
        for club_id in clubs
        if club_id != player_club_id
    )
    if shortfall <= 0:
        return False

    free_agents = load_free_agents(conn)
    extra_needed = max(0, shortfall + PLAYER_FREE_AGENT_RESERVE - len(free_agents))
    emergency_rookies = generate_rookie_class(
        season_id,
        DeterministicRNG(derive_seed(root_seed, "ai_roster_repair", season_id, str(shortfall))),
        size=extra_needed,
    ) if extra_needed else []
    remaining = _sign_ai_replacements(
        updated_rosters,
        clubs,
        player_club_id,
        free_agents + emergency_rookies,
        min_size=min_size,
    )

    from .lineup import optimize_ai_lineup

    for club_id, club in clubs.items():
        if club_id == player_club_id:
            continue
        roster = updated_rosters.get(club_id, [])
        save_club(conn, club, roster)
        save_lineup_default(conn, club_id, optimize_ai_lineup(roster))
    save_free_agents(conn, remaining, season_id)
    conn.commit()
    return True


def _career_rows_for_player(conn: sqlite3.Connection, player_id: str) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT pss.*,
               CASE
                 WHEN COALESCE(
                    (SELECT champion_club_id FROM season_outcomes WHERE season_id = pss.season_id),
                    (
                        SELECT club_id FROM season_standings
                        WHERE season_id = pss.season_id
                        ORDER BY points DESC, elimination_differential DESC, club_id ASC
                        LIMIT 1
                    )
                 ) = pss.club_id THEN 1 ELSE 0
               END AS champion
        FROM player_season_stats pss
        WHERE pss.player_id = ?
        ORDER BY pss.season_id
        """,
        (player_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def _update_career_summaries(
    conn: sqlite3.Connection,
    rosters: Mapping[str, List[Player]],
    awards: Iterable[Any],
) -> None:
    award_rows = list(awards)
    player_lookup = {player.id: player for roster in rosters.values() for player in roster}
    for player_id, player in player_lookup.items():
        rows = _career_rows_for_player(conn, player_id)
        if not rows:
            continue
        player_awards = [award for award in award_rows if award.player_id == player_id]
        club_ids = {str(row.get("club_id") or "") for row in rows if row.get("club_id")}
        summary = {
            "player_id": player_id,
            "player_name": player.name,
            "seasons_played": len(rows),
            "championships": sum(1 for row in rows if int(row.get("champion") or 0)),
            "awards_won": len(player_awards),
            "total_matches": sum(int(row.get("matches") or 0) for row in rows),
            "total_eliminations": sum(int(row.get("total_eliminations") or 0) for row in rows),
            "total_catches_made": sum(int(row.get("total_catches_made") or 0) for row in rows),
            "total_dodges_successful": sum(int(row.get("total_dodges_successful") or 0) for row in rows),
            "total_times_eliminated": sum(int(row.get("total_times_eliminated") or 0) for row in rows),
            "peak_eliminations": max((int(row.get("total_eliminations") or 0) for row in rows), default=0),
            "recent_eliminations": int(rows[-1].get("total_eliminations") or 0),
            "career_eliminations": sum(int(row.get("total_eliminations") or 0) for row in rows),
            "career_catches": sum(int(row.get("total_catches_made") or 0) for row in rows),
            "career_dodges": sum(int(row.get("total_dodges_successful") or 0) for row in rows),
            "clubs_served": len(club_ids),
        }
        save_player_career_stats(conn, player_id, summary)


def finalize_season(
    conn: sqlite3.Connection,
    season: Season,
    rosters: Mapping[str, List[Player]],
) -> None:
    """Compute and persist season awards, player season stats, and career summaries (idempotent)."""
    existing_awards = load_awards(conn, season.season_id)
    if existing_awards:
        _update_career_summaries(conn, rosters, existing_awards)
        conn.commit()
        return
    season_stats = fetch_season_player_stats(conn, season.season_id)
    player_club_map = {
        row["player_id"]: row["club_id"]
        for row in conn.execute(
            "SELECT DISTINCT player_id, club_id FROM player_match_stats "
            "WHERE match_id IN (SELECT match_id FROM match_records WHERE season_id = ?)",
            (season.season_id,),
        ).fetchall()
    }
    newcomers = frozenset(player.id for roster in rosters.values() for player in roster if player.newcomer)
    awards = compute_season_awards(season.season_id, season_stats, player_club_map, newcomers)
    save_awards(conn, awards)
    matches_by_player = {
        row["player_id"]: row["matches"]
        for row in conn.execute(
            "SELECT player_id, COUNT(*) AS matches FROM player_match_stats "
            "WHERE match_id IN (SELECT match_id FROM match_records WHERE season_id = ?) GROUP BY player_id",
            (season.season_id,),
        )
    }
    save_player_season_stats(conn, season.season_id, season_stats, player_club_map, matches_by_player, newcomers)
    _update_career_summaries(conn, rosters, awards)
    conn.commit()


def initialize_manager_offseason(
    conn: sqlite3.Connection,
    season: Season,
    clubs: Mapping[str, Club],
    rosters: Mapping[str, List[Player]],
    root_seed: int,
) -> Dict[str, List[Player]]:
    """Apply v1 off-season roster changes once and persist factual summaries."""
    if get_state(conn, "offseason_initialized_for") == season.season_id:
        return load_all_rosters(conn)

    season_stats = fetch_season_player_stats(conn, season.season_id)
    updated_rosters: Dict[str, List[Player]] = {}
    released_ai_players: List[Player] = []
    development_rows: List[Dict[str, Any]] = []
    retirement_rows: List[Dict[str, Any]] = []

    cursor = conn.execute(
        "SELECT plan_json FROM weekly_command_plans WHERE season_id = ? ORDER BY week DESC LIMIT 1",
        (season.season_id,),
    )
    row = cursor.fetchone()
    player_dev_focus = "BALANCED"
    if row:
        plan = json.loads(row[0])
        player_dev_focus = plan.get("department_orders", {}).get("dev_focus", "BALANCED")

    # Evaluate open promises before retirements alter roster state
    from .dynasty_office import evaluate_season_promises
    _player_club_id = get_state(conn, "player_club_id") or ""
    if _player_club_id:
        evaluate_season_promises(conn, season.season_id, _player_club_id)

    # Training is the persisted staff department that owns player-growth work.
    _all_dept_heads = {h["department"]: h for h in load_department_heads(conn)}
    _dev_head = _all_dept_heads.get("training")
    _max_mod = DEFAULT_CONFIG.max_staff_development_modifier
    _staff_dev_modifier = 0.0
    if _dev_head is not None:
        _staff_dev_modifier = max(
            0.0, (_dev_head["rating_primary"] - 50.0) / 50.0 * _max_mod
        )

    for club_id, roster in rosters.items():
        next_roster: List[Player] = []
        is_player_club = club_id == get_state(conn, "player_club_id")
        for player in roster:
            stats = season_stats.get(player.id, PlayerMatchStats())
            developed = apply_season_development(
                player,
                stats,
                facilities=(),
                rng=DeterministicRNG(derive_seed(root_seed, "manager_development", season.season_id, player.id)),
                trajectory=load_player_trajectory(conn, player.id),
                dev_focus=player_dev_focus if is_player_club else "BALANCED",
                staff_development_modifier=_staff_dev_modifier if is_player_club else 0.0,
            )
            aged = replace(developed, age=developed.age + 1)
            delta = round(aged.overall() - player.overall(), 2)
            if should_retire(aged, load_player_career_stats(conn, player.id)):
                save_retired_player(conn, aged, season.season_id, "age_decline")
                retirement_rows.append(
                    {
                        "player_id": aged.id,
                        "player_name": aged.name,
                        "club_id": club_id,
                        "age": aged.age,
                        "overall": round(aged.overall(), 1),
                        "reason": "age_decline",
                    }
                )
                continue
            development_rows.append(
                {
                    "player_id": aged.id,
                    "player_name": aged.name,
                    "club_id": club_id,
                    "before": round(player.overall(), 1),
                    "after": round(aged.overall(), 1),
                    "delta": delta,
                }
            )
            next_roster.append(aged)
        if club_id != get_state(conn, "player_club_id") and len(next_roster) > 9:
            next_roster, released = trim_ai_roster_for_offseason(next_roster, max_size=9)
            released_ai_players.extend(replace(player, club_id=None) for player in released)
        updated_rosters[club_id] = next_roster

    next_season_id = (
        f"season_{int(season.season_id.rsplit('_', 1)[-1]) + 1}"
        if season.season_id.rsplit("_", 1)[-1].isdigit()
        else f"{season.season_id}_next"
    )
    player_club_id = get_state(conn, "player_club_id") or ""
    ai_shortfall = sum(
        max(0, AI_MIN_PLAYABLE_ROSTER_SIZE - len(updated_rosters.get(club_id, [])))
        for club_id in clubs
        if club_id != player_club_id
    )
    rookies = generate_rookie_class(
        next_season_id,
        DeterministicRNG(derive_seed(root_seed, "manager_draft", next_season_id)),
        size=max(12, ai_shortfall + PLAYER_FREE_AGENT_RESERVE),
    )
    free_agents = _sign_ai_replacements(
        updated_rosters,
        clubs,
        player_club_id,
        rookies + released_ai_players,
    )
    from .lineup import optimize_ai_lineup
    for club_id, club in clubs.items():
        save_club(conn, club, updated_rosters.get(club_id, []))
        if club_id == player_club_id:
            save_lineup_default(conn, club_id, [player.id for player in updated_rosters.get(club_id, [])])
        else:
            save_lineup_default(conn, club_id, optimize_ai_lineup(updated_rosters.get(club_id, [])))
    save_free_agents(conn, free_agents, next_season_id)
    set_state(conn, "offseason_development_json", json.dumps(development_rows))
    set_state(conn, "offseason_retirements_json", json.dumps(retirement_rows))
    set_state(conn, "offseason_draft_signed_player_id", "")
    ratify_records(conn, season.season_id)
    induct_hall_of_fame(conn, season.season_id)
    next_class_year = (
        int(season.season_id.rsplit("_", 1)[-1]) + 1
        if season.season_id.rsplit("_", 1)[-1].isdigit()
        else 1
    )
    build_rookie_class_preview(conn, season.season_id, next_class_year)
    # Compute and store the active beat list for this offseason
    active_beats = compute_active_beats(
        records_payload_json=get_state(conn, "offseason_records_json"),
        hof_payload_json=get_state(conn, "offseason_hof_json"),
        retirement_rows=retirement_rows,
    )
    set_state(conn, "offseason_active_beats_json", json.dumps(active_beats))
    set_state(conn, "offseason_initialized_for", season.season_id)
    conn.commit()
    return updated_rosters


def sign_best_rookie(
    conn: sqlite3.Connection,
    player_club_id: str,
    season_number: int,
) -> Optional[Player]:
    """Sign the highest-rated available prospect or free agent to the player's club."""
    class_year = season_number or 1
    available_prospects = [
        prospect
        for prospect in load_prospect_pool(conn, class_year=class_year)
        if not _is_already_signed(conn, class_year, prospect.player_id)
    ]
    if available_prospects:
        selected_prospect = sorted(
            available_prospects,
            key=lambda prospect: (-prospect.true_overall(), prospect.player_id),
        )[0]
        signed_prospect = sign_prospect_to_club(conn, selected_prospect, player_club_id, class_year)
        rosters = load_all_rosters(conn)
        set_state(conn, "offseason_draft_signed_player_id", signed_prospect.id)
        roster = list(rosters.get(player_club_id, []))
        save_lineup_default(conn, player_club_id, [player.id for player in roster])
        conn.commit()
        return signed_prospect
    free_agents = load_free_agents(conn)
    if not free_agents:
        conn.commit()
        return None
    selected = sorted(free_agents, key=lambda player: (-player.overall(), player.id))[0]
    remaining = [player for player in free_agents if player.id != selected.id]
    signed = replace(selected, club_id=player_club_id, newcomer=True)
    rosters = load_all_rosters(conn)
    roster = list(rosters.get(player_club_id, []))
    roster.append(signed)
    clubs = load_clubs(conn)
    save_club(conn, clubs[player_club_id], roster)
    save_lineup_default(conn, player_club_id, [player.id for player in roster])
    save_free_agents(conn, remaining, f"season_{(season_number or 1) + 1}")
    set_state(conn, "offseason_draft_signed_player_id", signed.id)
    conn.commit()
    return signed


def begin_next_season(
    conn: sqlite3.Connection,
    cursor: CareerStateCursor,
    clubs: Mapping[str, Club],
) -> CareerStateCursor:
    """Create next season, wire scouting, advance cursor to SEASON_ACTIVE_PRE_MATCH."""
    from .config import DEFAULT_SCOUTING_CONFIG
    from .scouting_center import initialize_scouting_for_career

    active_season_id = get_state(conn, "active_season_id")
    season = load_season(conn, active_season_id) if active_season_id else None
    if season is None:
        raise RuntimeError("No active season to advance from")

    next_number = (cursor.season_number or 1) + 1
    root_seed = stored_root_seed(conn)
    next_season = create_next_manager_season(clubs, root_seed, next_number, season.year + 1)
    prior_season_num = cursor.season_number or 1

    apply_scouting_carry_forward(conn, prior_season_num)
    save_season(conn, next_season)
    save_season_format(conn, next_season.season_id, PLAYOFF_FORMAT)
    set_state(conn, "active_season_id", next_season.season_id)

    new_cursor = CareerStateCursor(
        state=CareerState.SEASON_ACTIVE_PRE_MATCH,
        season_number=next_number,
        week=1,
        offseason_beat_index=0,
        match_id=None,
    )
    save_career_state_cursor(conn, new_cursor)
    initialize_scouting_for_career(
        conn,
        root_seed=root_seed,
        config=DEFAULT_SCOUTING_CONFIG,
        class_year=next_number,
    )
    conn.commit()
    return new_cursor


def apply_scouting_carry_forward(conn: sqlite3.Connection, prior_class_year: int) -> None:
    from .config import DEFAULT_SCOUTING_CONFIG
    from .persistence import load_scouting_state, save_scouting_state
    from .scouting_center import apply_carry_forward_decay

    for prospect in load_prospect_pool(conn, prior_class_year):
        if _is_already_signed(conn, prior_class_year, prospect.player_id):
            conn.execute("DELETE FROM scouting_state WHERE player_id = ?", (prospect.player_id,))
            continue
        state = load_scouting_state(conn, prospect.player_id)
        if state is not None:
            save_scouting_state(conn, apply_carry_forward_decay(state, DEFAULT_SCOUTING_CONFIG))
    conn.commit()


def build_offseason_ceremony_beat(
    beat_index: int,
    season: Optional[Season],
    clubs: Mapping[str, Club],
    rosters: Mapping[str, List[Player]],
    standings: Iterable[StandingsRow],
    awards: Iterable[Any],
    player_club_id: Optional[str],
    next_season: Optional[Season] = None,
    development_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    retirement_rows: Optional[Iterable[Mapping[str, Any]]] = None,
    draft_pool: Optional[Iterable[Player]] = None,
    signed_player_id: Optional[str] = None,
    recruitment_available: bool = False,
    recruitment_summary: Optional[Mapping[str, Any]] = None,
    season_outcome: Optional[Any] = None,
    records_payload_json: Optional[str] = None,
    hof_payload_json: Optional[str] = None,
    rookie_preview_payload_json: Optional[str] = None,
) -> OffseasonCeremonyBeat:
    """Build factual v1 offseason ceremony copy from persisted season data."""
    clamped_index = clamp_offseason_beat_index(beat_index)
    key = OFFSEASON_CEREMONY_BEATS[clamped_index]
    ordered_standings = list(standings)
    award_rows = list(awards)
    development = list(development_rows or ())
    retirements = list(retirement_rows or ())
    rookies = list(draft_pool or ())

    def club_name(club_id: str) -> str:
        return clubs[club_id].name if club_id in clubs else club_id

    def player_name(player_id: str) -> str:
        for roster in rosters.values():
            for player in roster:
                if player.id == player_id:
                    return player.name
        return player_id

    if key == "champion":
        if season_outcome is not None:
            seed = None
            for index, row in enumerate(ordered_standings, 1):
                if row.club_id == season_outcome.champion_club_id:
                    seed = index
                    break
            lines = [
                f"Champion: {club_name(season_outcome.champion_club_id)}",
                "Champion source: Playoff final",
            ]
            if season_outcome.runner_up_club_id:
                lines.append(f"Runner-up: {club_name(season_outcome.runner_up_club_id)}")
            if seed is not None:
                lines.append(f"Regular-season seed: {seed}")
            body = "\n".join(lines)
        elif not ordered_standings:
            body = "No completed standings are available for this season."
        else:
            champion = ordered_standings[0]
            body = "\n".join(
                [
                    f"Champion: {club_name(champion.club_id)}",
                    f"Record: {champion.wins}-{champion.losses}-{champion.draws}",
                    f"Points: {champion.points}",
                    f"Elimination differential: {champion.elimination_differential:+}",
                ]
            )
        return OffseasonCeremonyBeat(key, "Champion", body)

    if key == "recap":
        if not ordered_standings:
            body = "No standings rows were recorded."
        else:
            lines = ["Final Table:"]
            for index, row in enumerate(ordered_standings, 1):
                marker = " *" if row.club_id == player_club_id else ""
                lines.append(
                    f"{index:>2}. {club_name(row.club_id):<22} {row.wins}-{row.losses}-{row.draws} "
                    f"pts={row.points} diff={row.elimination_differential:+}{marker}"
                )
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Recap", body)

    if key == "awards":
        if not award_rows:
            body = "No awards were posted for this season."
        else:
            lines = ["Season Awards:"]
            for award in award_rows:
                lines.append(
                    f"{title_label(award.award_type)}: "
                    f"{player_name(award.player_id)} ({club_name(award.club_id)})"
                )
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Awards", body)

    if key == "records_ratified":
        entries = []
        if records_payload_json:
            try:
                entries = list(json.loads(records_payload_json) or [])
            except (TypeError, ValueError):
                entries = []
        if not entries:
            body = "No new records were set this season."
        else:
            lines = ["New league records:"]
            for entry in entries:
                holder = entry.get("holder_name", entry.get("holder_id", "?"))
                prev = float(entry.get("previous_value", 0.0))
                new = float(entry.get("new_value", 0.0))
                lines.append(
                    f"  {title_label(entry.get('record_type', '?'))}: "
                    f"{holder} {prev:g} -> {new:g} ({entry.get('detail', '')})"
                )
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Records Ratified", body)

    if key == "hof_induction":
        entries = []
        if hof_payload_json:
            try:
                entries = list(json.loads(hof_payload_json) or [])
            except (TypeError, ValueError):
                entries = []
        if not entries:
            body = "No new inductees this off-season."
        else:
            lines = ["Hall of Fame inductees:"]
            for entry in entries:
                reasons = ", ".join(entry.get("reasons", [])) or "qualified by score"
                lines.append(
                    f"  {entry.get('player_name', entry.get('player_id', '?'))}: "
                    f"legacy {float(entry.get('legacy_score', 0.0)):.1f} "
                    f"(threshold {float(entry.get('threshold', 0.0)):.1f})"
                )
                lines.append(
                    f"    {int(entry.get('seasons_played', 0))} seasons, "
                    f"{int(entry.get('championships', 0))} titles, "
                    f"{int(entry.get('awards_won', 0))} awards, "
                    f"{int(entry.get('total_eliminations', 0))} career eliminations"
                )
                lines.append(f"    Reasons: {reasons}")
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Hall of Fame Induction", body)

    if key == "development":
        rows = sorted(development, key=lambda row: (-abs(float(row.get("delta", 0))), str(row.get("player_id", ""))))[:8]
        lines = [f"Development applied to {len(development)} active players."]
        if not rows:
            lines.append("No active development rows were recorded.")
        for row in rows:
            marker = " *" if row.get("club_id") == player_club_id else ""
            lines.append(
                f"  {row.get('player_name', row.get('player_id'))} ({club_name(str(row.get('club_id', '')))}): "
                f"{float(row.get('before', 0)):.1f} -> {float(row.get('after', 0)):.1f} "
                f"({float(row.get('delta', 0)):+.1f}){marker}"
            )
        return OffseasonCeremonyBeat(key, "Development", "\n".join(lines))

    if key == "retirements":
        lines = [f"Retirements processed: {len(retirements)}"]
        if not retirements:
            lines.append("No players retired this off-season.")
        for row in retirements:
            marker = " *" if row.get("club_id") == player_club_id else ""
            lines.append(
                f"  {row.get('player_name', row.get('player_id'))} ({club_name(str(row.get('club_id', '')))}): "
                f"age {row.get('age')} OVR {float(row.get('overall', 0)):.1f}{marker}"
            )
        return OffseasonCeremonyBeat(key, "Retirements", "\n".join(lines))

    if key == "rookie_class_preview":
        payload_dict: Dict[str, Any] = {}
        if rookie_preview_payload_json:
            try:
                payload_dict = dict(json.loads(rookie_preview_payload_json) or {})
            except (TypeError, ValueError):
                payload_dict = {}
        class_size = int(payload_dict.get("class_size", 0))
        archetype_distribution: Dict[str, int] = dict(payload_dict.get("archetype_distribution", {}) or {})
        free_agent_count = int(payload_dict.get("free_agent_count", 0))
        top_band_depth = int(payload_dict.get("top_band_depth", 0))
        storylines = list(payload_dict.get("storylines", []) or [])
        source = str(payload_dict.get("source", "prospect_pool"))

        if class_size == 0 and free_agent_count == 0:
            body = "No incoming class data is available yet."
        else:
            lines = [f"Incoming class size: {class_size}"]
            lines.append(f"Top-band prospects (>= 70 OVR band low): {top_band_depth}")
            lines.append(f"Free-agent count: {free_agent_count}")
            if archetype_distribution:
                ordered = sorted(archetype_distribution.items(), key=lambda item: (-item[1], item[0]))
                lines.append("Archetype distribution: " + ", ".join(f"{name} {count}" for name, count in ordered))
            if storylines:
                lines.append("")
                lines.append("Market storylines:")
                for storyline in storylines:
                    lines.append(f"  - {storyline.get('sentence', '')}")
            lines.append("")
            lines.append("Continue to Recruitment Day.")
            body = "\n".join(lines)
        return OffseasonCeremonyBeat(key, "Rookie Class Preview", body)

    if key == "recruitment":
        roster_sizes = sorted((club_id, len(list(roster))) for club_id, roster in rosters.items())
        signed = next((player for roster in rosters.values() for player in roster if player.id == signed_player_id), None)
        if recruitment_available:
            summary = dict(recruitment_summary or {})
            lines = ["Recruitment Day is active: compete with AI clubs for this prospect class."]
            lines.append(f"Current round: {int(summary.get('current_round', 1))}")
            lines.append(f"Available prospects: {int(summary.get('available_prospects', 0))}")
            lines.append(f"Signed this recruitment: {int(summary.get('signed_count', 0))}")
            lines.append(f"Snipes recorded: {int(summary.get('sniped_count', 0))}")
            if signed is not None:
                lines.append(f"Your latest signing: {signed.name} ({signed.overall():.1f} OVR)")
            lines.append("")
            lines.append("Current roster sizes:")
            for club_id, size in roster_sizes:
                lines.append(f"  {club_name(club_id)}: {size} players")
            return OffseasonCeremonyBeat(key, "Recruitment Day", "\n".join(lines))
        lines = ["v1 Draft is active: sign one rookie into your roster before beginning next season."]
        if signed is not None:
            lines.append(f"Signed rookie: {signed.name} ({signed.overall():.1f} OVR)")
        else:
            lines.append(f"Available rookies: {len(rookies)}")
            for player in sorted(rookies, key=lambda item: (-item.overall(), item.id))[:5]:
                lines.append(f"  {player.name}: OVR {player.overall():.1f} age {player.age}")
        lines.append("")
        lines.append("Current roster sizes:")
        for club_id, size in roster_sizes:
            lines.append(f"  {club_name(club_id)}: {size} players")
        return OffseasonCeremonyBeat(key, "Draft", "\n".join(lines))

    # schedule_reveal (or any unknown key falls here)
    scheduled = next_season.scheduled_matches if next_season is not None else ()
    season_label = next_season.season_id if next_season is not None else "next season"
    lines = [f"{season_label} schedule is ready to be created."]
    if scheduled:
        lines.append("Opening fixtures:")
        for match in scheduled[: min(6, len(scheduled))]:
            lines.append(
                f"  Week {match.week}: {club_name(match.home_club_id)} vs {club_name(match.away_club_id)}"
            )
    else:
        lines.append("Begin Next Season will generate the next round-robin schedule.")
    return OffseasonCeremonyBeat(key, "Schedule Reveal", "\n".join(lines))


__all__ = [
    "OFFSEASON_CEREMONY_BEATS",
    "OffseasonCeremonyBeat",
    "compute_active_beats",
    "clamp_offseason_beat_index",
    "stored_root_seed",
    "finalize_season",
    "initialize_manager_offseason",
    "sign_best_rookie",
    "begin_next_season",
    "build_offseason_ceremony_beat",
    "create_next_manager_season",
    "apply_scouting_carry_forward",
]
