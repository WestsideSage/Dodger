from __future__ import annotations

import json
import sqlite3
from typing import Any

from .config import DEFAULT_SCOUTING_CONFIG
from .game_loop import current_week
from .league_memory import build_league_memory_state
from .persistence import (
    CorruptSaveError,
    get_state,
    load_all_rosters,
    load_clubs,
    load_command_history,
    load_command_history_all_seasons,
    load_json_state,
    load_playoff_bracket,
    load_prospect_pool,
    load_season,
    set_state,
)
from .recruiting_office import (
    MAX_ACTIVE_PROMISES,
    PROMISE_OPTIONS,
    PROMISE_STATE_KEY,
    _class_year_from_season,
    build_recruiting_state,
)
from .recruitment import generate_prospect_pool
from .rng import DeterministicRNG, derive_seed
from .staff_market import STAFF_ACTION_STATE_KEY, build_staff_market_state
from typing import Dict, List, Mapping, Optional
from statistics import mean
from dataclasses import dataclass
from .models import Player, Team
from .stats import PlayerMatchStats
from .season import StandingsRow, Season
from .scheduler import ScheduledMatch
from .playoffs import is_playoff_match_id
from .league import Club
from typing import Dict, List, Mapping, Optional
from statistics import mean
from dataclasses import dataclass
from .models import Player, Team
from .stats import PlayerMatchStats
from .season import StandingsRow, Season
from .scheduler import ScheduledMatch
from .playoffs import is_playoff_match_id
from .league import Club
from typing import Dict, List, Mapping, Optional
from statistics import mean
from dataclasses import dataclass
from .models import Player, Team
from .stats import PlayerMatchStats
from .season import StandingsRow, Season
from .scheduler import ScheduledMatch
from .playoffs import is_playoff_match_id
from .league import Club


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
    history = load_command_history_all_seasons(conn)
    root_seed = _root_seed(conn)
    week = current_week(conn, season) or 0
    return {
        "season_id": season_id,
        "week": week,
        "player_club_id": player_club_id,
        "player_club_name": clubs[player_club_id].name if player_club_id in clubs else player_club_id,
        "recruiting": build_recruiting_state(
            conn,
            season_id=season_id,
            player_club_id=player_club_id,
            root_seed=root_seed,
            history=history,
        ),
        "league_memory": build_league_memory_state(conn, season_id=season_id, clubs=clubs),
        "staff_market": build_staff_market_state(
            conn,
            season_id=season_id,
            player_club_id=player_club_id,
            root_seed=root_seed,
        ),
    }


def save_recruiting_promise(
    conn: sqlite3.Connection,
    player_id: str,
    promise_type: str,
) -> dict[str, Any]:
    _ensure_dynasty_keys(conn)
    if promise_type not in PROMISE_OPTIONS:
        raise ValueError(f"Unknown promise type: {promise_type}")
    if not _is_known_player(conn, player_id):
        raise ValueError(
            f"Unknown player_id: {player_id} is not in the current prospect pool or any club roster."
        )
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
            promise["status"] = "broken"
            promise["result_season_id"] = season_id
            promise["evidence"] = "Legacy promise — player identity not recorded."
            changed = True
            continue

        promise_type = promise.get("promise_type", "")
        result, evidence = _evaluate_one_promise(
            conn, season_id, club_id, player_id, promise_type
        )
        promise["result"] = result
        promise["status"] = result
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


def _current_prospect_pool(conn: sqlite3.Connection) -> list[Any]:
    """Return the prospect pool the Dynasty Office surfaces today."""
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        return []
    class_year = _class_year_from_season(season_id)
    persisted = load_prospect_pool(conn, class_year)
    if persisted:
        return list(persisted)
    rng = DeterministicRNG(derive_seed(_root_seed(conn), "prospect_gen", str(class_year)))
    return list(generate_prospect_pool(class_year, rng, DEFAULT_SCOUTING_CONFIG))


def _is_known_player(conn: sqlite3.Connection, player_id: str) -> bool:
    """A promise must reference either a current prospect or a current club player."""
    if not player_id:
        return False
    for prospect in _current_prospect_pool(conn):
        if prospect.player_id == player_id:
            return True
    rosters = load_all_rosters(conn)
    for roster in rosters.values():
        for player in roster:
            if getattr(player, "id", None) == player_id:
                return True
    return False


def _load_promises(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return list(load_json_state(conn, PROMISE_STATE_KEY, []))


def _load_staff_actions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return list(load_json_state(conn, STAFF_ACTION_STATE_KEY, []))


def _root_seed(conn: sqlite3.Connection) -> int:
    try:
        return int(get_state(conn, "root_seed", "1") or "1")
    except ValueError:
        return 1


__all__ = [
    "build_dynasty_office_state",
    "evaluate_season_promises",
    "hire_staff_candidate",
    "save_recruiting_promise",
]


# ----------------------------------------------------------------------
# League leader / player profile / display helpers (formerly manager_helpers)
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class LeagueLeader:
    category: str
    player_id: str
    club_id: str
    value: float

@dataclass(frozen=True)
class PlayerProfileDetails:
    title: str
    text: str

def _score_player(stats: Optional[PlayerMatchStats]) -> float:
    if stats is None:
        return 0.0
    return (
        stats.eliminations_by_throw * 3.0
        + stats.catches_made * 4.0
        + stats.dodges_successful * 1.5
        + stats.revivals_caused * 2.0
        - stats.times_eliminated * 2.0
        + stats.clutch_events
    )

def _standings_with_all_clubs(standings: List[StandingsRow], clubs: Dict[str, Club]) -> List[StandingsRow]:
    by_id = {row.club_id: row for row in standings}
    rows = [
        by_id.get(club_id, StandingsRow(club_id, wins=0, losses=0, draws=0, elimination_differential=0, points=0))
        for club_id in clubs
    ]
    rows.sort(key=lambda row: (-row.points, -row.elimination_differential, row.club_id))
    return rows

def _regular_season_matches(season: Season) -> List[ScheduledMatch]:
    return [
        match for match in season.scheduled_matches
        if not is_playoff_match_id(season.season_id, match.match_id)
    ]

def player_role(player: Player) -> str:
    ratings = {
        "Sniper": player.ratings.accuracy,
        "Power Arm": player.ratings.power,
        "Dodger": player.ratings.dodge,
        "Catcher": player.ratings.catch,
    }
    return max(ratings.items(), key=lambda item: item[1])[0]

def team_overall(team: Team) -> float:
    if not team.players:
        return 0.0
    return mean(player.overall_skill() for player in team.players)

def build_league_leaders(
    player_stats: Mapping[str, PlayerMatchStats],
    player_club_map: Mapping[str, str],
    limit: int = 3,
) -> Dict[str, List[LeagueLeader]]:
    """Build v1 league leader boards from persisted player stats."""
    specs = {
        "Eliminations": lambda stats: float(stats.eliminations_by_throw),
        "Catches": lambda stats: float(stats.catches_made),
        "MVP Score": _score_player,
    }
    leaders: Dict[str, List[LeagueLeader]] = {}
    for category, scorer in specs.items():
        rows = [
            LeagueLeader(category, player_id, player_club_map.get(player_id, ""), scorer(stats))
            for player_id, stats in player_stats.items()
        ]
        rows.sort(key=lambda row: (-row.value, row.player_id))
        leaders[category] = rows[:limit]
    return leaders

def build_player_profile_details(
    player: Player,
    club_name: str,
    season_stats: Optional[PlayerMatchStats] = None,
    matches_played: int = 0,
    career_summary: Optional[Mapping[str, float]] = None,
) -> PlayerProfileDetails:
    """Build display-ready player profile details without touching GUI state."""
    ratings = player.ratings
    status = "Rookie" if player.newcomer else "Veteran"
    lines = [
        f"{player.name}",
        f"Club: {club_name}",
        f"Role: {player_role(player)}",
        f"Age: {player.age} | Status: {status}",
        "",
        "Ratings",
        f"  OVR: {round(player.overall_skill())}",
        f"  Accuracy: {round(ratings.accuracy)}",
        f"  Power: {round(ratings.power)}",
        f"  Dodge: {round(ratings.dodge)}",
        f"  Catch: {round(ratings.catch)}",
        f"  Stamina: {round(ratings.stamina)}",
        "",
        "Current Season",
    ]
    if season_stats is None:
        lines.append("  No persisted season stats yet.")
    else:
        lines.extend(
            [
                f"  Matches: {matches_played}",
                f"  Throws: {season_stats.throws_attempted}",
                f"  Eliminations: {season_stats.eliminations_by_throw}",
                f"  Catches: {season_stats.catches_made}",
                f"  Dodges: {season_stats.dodges_successful}",
                f"  Times Eliminated: {season_stats.times_eliminated}",
                f"  Plus/Minus: {season_stats.elimination_plus_minus:+}",
                f"  MVP Score: {round(_score_player(season_stats))}",
            ]
        )

    lines.append("")
    lines.append("Career")
    if not career_summary or career_summary.get("seasons_played", 0) <= 0:
        lines.append("  No persisted career totals yet.")
    else:
        lines.extend(
            [
                f"  Seasons: {career_summary.get('seasons_played', 0):.0f}",
                f"  Eliminations: {career_summary.get('total_eliminations', 0):.0f}",
                f"  Catches: {career_summary.get('total_catches_made', 0):.0f}",
                f"  Dodges: {career_summary.get('total_dodges_successful', 0):.0f}",
                f"  Times Eliminated: {career_summary.get('total_times_eliminated', 0):.0f}",
                f"  Recent Eliminations: {career_summary.get('recent_eliminations', 0):.0f}",
            ]
        )
    return PlayerProfileDetails(title=player.name, text="\n".join(lines))


# ---------------------------------------------------------------------------
# V2-A scouting helper builders
# ---------------------------------------------------------------------------
