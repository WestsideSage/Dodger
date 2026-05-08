from pathlib import Path
import dataclasses
import json
import math
import mimetypes
import re
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

from dodgeball_sim.persistence import (
    connect, load_career_state_cursor, get_state, load_club_roster,
    load_clubs, save_club, load_season, load_completed_match_ids,
    save_career_state_cursor, load_all_rosters, load_standings, load_awards,
    load_lineup_default,
    save_match_lineup_override,
    fetch_roster_snapshot,
    fetch_match,
    CorruptSaveError,
    save_weekly_command_plan,
    load_weekly_command_plan,
    save_command_history_record,
    load_command_history,
    load_free_agents,
    load_season_outcome,
    load_playoff_bracket,
    save_playoff_bracket,
    save_scheduled_matches,
    save_season_outcome,
)
from dodgeball_sim.awards import compute_match_mvp
from dodgeball_sim.career_state import CareerState, advance
from dodgeball_sim.models import CoachPolicy
from dodgeball_sim.sim_pacing import SimRequest, choose_matches_to_sim
from dodgeball_sim.stats import PlayerMatchStats
from dodgeball_sim.replay_proof import build_replay_proof, event_detail, event_label
from dodgeball_sim.game_loop import (
    current_week,
    recompute_regular_season_standings,
    simulate_scheduled_match,
)
from dodgeball_sim.career_setup import ensure_default_web_career, initialize_curated_manager_career
from dodgeball_sim.offseason_ceremony import (
    OFFSEASON_CEREMONY_BEATS,
    build_offseason_ceremony_beat,
    finalize_season,
    initialize_manager_offseason,
    sign_best_rookie,
    begin_next_season,
    stored_root_seed,
    create_next_manager_season,
    clamp_offseason_beat_index,
    ensure_ai_rosters_playable,
)
from dodgeball_sim.playoffs import (
    PLAYOFF_FORMAT,
    create_final_match,
    create_semifinal_bracket,
    is_playoff_match_id,
    outcome_from_final,
)
from dodgeball_sim.sample_data import curated_clubs
from dodgeball_sim.scheduler import ScheduledMatch
from dodgeball_sim.season import Season, StandingsRow
from dodgeball_sim.view_models import build_schedule_rows, build_wire_items, normalize_root_seed
from dodgeball_sim.command_center import (
    build_command_center_state,
    build_default_weekly_plan,
    build_post_week_dashboard,
)
from dodgeball_sim.dynasty_office import (
    build_dynasty_office_state,
    hire_staff_candidate,
    save_recruiting_promise,
)

app = FastAPI(title="Dodgeball Manager API")

DEFAULT_DB_PATH = Path("dodgeball_sim.db")
SAVES_DIR = Path("saves")

_active_save_path: Path | None = None
_LEGACY_TARGET_EVIDENCE_RE = re.compile(r"^Target evidence: ([A-Za-z0-9_]+) was targeted (\d+) times\.$")
_LEGACY_STAR_SETTING_RE = re.compile(r"^Tactical target-stars setting: ([0-9.]+)\.$")
_LEGACY_RUSH_SETTING_RE = re.compile(r"^Rush frequency setting: ([0-9.]+)\.$")


def _resolve_managed_save_path(raw: str, *, allow_legacy: bool) -> Path:
    """Resolve a client-supplied save path against the managed save area.

    Returns the resolved Path on success. Raises HTTPException with the
    appropriate status on path traversal, missing files, non-managed
    locations, or non-`.db` files.
    """
    if not raw or not isinstance(raw, str):
        raise HTTPException(status_code=400, detail="Save path is required.")
    candidate = Path(raw)
    try:
        resolved = candidate.resolve(strict=False)
    except OSError:
        raise HTTPException(status_code=400, detail="Invalid save path.")
    saves_root = SAVES_DIR.resolve()
    legacy = DEFAULT_DB_PATH.resolve()
    if resolved.suffix.lower() != ".db":
        raise HTTPException(status_code=400, detail="Save files must end in .db.")
    is_managed = False
    try:
        resolved.relative_to(saves_root)
        is_managed = True
    except ValueError:
        is_managed = False
    if not is_managed and not (allow_legacy and resolved == legacy):
        raise HTTPException(
            status_code=403,
            detail="Save path must be under the managed saves directory.",
        )
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Save file not found.")
    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="Save path is not a file.")
    return resolved


def _looks_like_dodgeball_save(path: Path) -> bool:
    """Verify the file at *path* is a SQLite save with our schema row.

    The check opens through `connect()` so that schema migrations are exercised
    the same way the live request path would exercise them; if any step fails,
    the file is rejected.
    """
    try:
        conn = connect(path)
    except Exception:
        return False
    try:
        try:
            row = conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ).fetchone()
        except Exception:
            return False
        return row is not None
    finally:
        try:
            conn.close()
        except Exception:
            pass

_ROLE_LABELS = ["Captain", "Striker", "Anchor", "Runner", "Rookie", "Utility"]


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": _json_safe(exc.errors())})

def get_db():
    if _active_save_path is None:
        raise HTTPException(status_code=503, detail="No save loaded. Use the save menu to load or create a game.")
    conn = connect(_active_save_path)
    try:
        yield conn
    finally:
        conn.close()


def _read_save_meta(path: Path) -> dict:
    try:
        conn = connect(path)
        try:
            from dodgeball_sim.persistence import create_schema
            create_schema(conn)
            club_id = conn.execute("SELECT value FROM dynasty_state WHERE key='player_club_id'").fetchone()
            season_id = conn.execute("SELECT value FROM dynasty_state WHERE key='active_season_id'").fetchone()
            week_row = conn.execute("SELECT value FROM dynasty_state WHERE key='career_week'").fetchone()
            club_name = None
            if club_id:
                row = conn.execute("SELECT name FROM clubs WHERE club_id=?", (club_id[0],)).fetchone()
                club_name = row[0] if row else club_id[0]
            return {
                "name": path.stem,
                "path": str(path),
                "club_id": club_id[0] if club_id else None,
                "club_name": club_name,
                "season_id": season_id[0] if season_id else None,
                "week": int(week_row[0]) if week_row else None,
            }
        finally:
            conn.close()
    except Exception:
        return {"name": path.stem, "path": str(path), "club_id": None, "club_name": None, "season_id": None, "week": None}

# --- Pydantic Models ---

class CoachPolicyUpdate(BaseModel):
    target_stars: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    target_ball_holder: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    risk_tolerance: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    sync_throws: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    rush_frequency: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    rush_proximity: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    tempo: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    catch_bias: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)


class SimCommand(BaseModel):
    mode: str = "week"
    weeks: int = 1
    milestone: str | None = None


class WeeklyCommandPlanUpdate(BaseModel):
    intent: str | None = None
    department_orders: dict[str, str] | None = None
    tactics: dict[str, float] | None = None
    lineup_player_ids: list[str] | None = None


class CareerStateResponse(BaseModel):
    state: str
    season_number: int
    week: int
    offseason_beat_index: int
    match_id: str | None = None


class StatusContextResponse(BaseModel):
    season_id: str | None = None
    player_club_id: str | None = None
    player_club_name: str | None = None


class StatusResponse(BaseModel):
    status: str
    state: CareerStateResponse
    context: StatusContextResponse


class RosterResponse(BaseModel):
    club_id: str
    roster: list[Any]
    default_lineup: list[str] | None


class TacticsResponse(BaseModel):
    target_stars: float
    target_ball_holder: float
    risk_tolerance: float
    sync_throws: float
    rush_frequency: float
    rush_proximity: float
    tempo: float
    catch_bias: float


class StandingItem(BaseModel):
    club_id: str
    club_name: str
    wins: int
    losses: int
    draws: int
    points: int
    elimination_differential: int
    is_user_club: bool


class StandingsResponse(BaseModel):
    season_id: str
    standings: list[StandingItem]


class ScheduleItem(BaseModel):
    match_id: str
    week: int
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    status: str
    is_user_match: bool


class ScheduleResponse(BaseModel):
    season_id: str
    schedule: list[ScheduleItem]


class NewsItem(BaseModel):
    tag: str
    text: str
    match_id: str | None = None
    player_id: str | None = None


class NewsResponse(BaseModel):
    season_id: str
    items: list[NewsItem]


class SimResponse(BaseModel):
    status: str
    simulated_count: int
    stop_reason: str
    message: str
    match_id: str | None = None
    next_state: str | None = None


class SaveInfo(BaseModel):
    name: str
    path: str
    club_id: str | None
    club_name: str | None
    season_id: str | None
    week: int | None


class SaveListResponse(BaseModel):
    saves: list[SaveInfo]
    active_path: str | None


class SaveStateResponse(BaseModel):
    loaded: bool
    active_path: str | None
    meta: SaveInfo | None


class NewSaveRequest(BaseModel):
    name: str
    club_id: str = "aurora"
    root_seed: int = 20260426


class MatchReplayResponse(BaseModel):
    match_id: str
    season_id: str
    week: int
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    winner_club_id: str | None
    winner_name: str
    home_survivors: int
    away_survivors: int
    events: list[dict[str, Any]]
    proof_events: list[dict[str, Any]] = Field(default_factory=list)
    key_play_indices: list[int] = Field(default_factory=list)
    report: dict[str, Any]


class AcknowledgeMatchResponse(BaseModel):
    status: str
    state: CareerStateResponse


class CommandCenterResponse(BaseModel):
    season_id: str
    week: int
    player_club_id: str
    player_club_name: str
    current_objective: str
    plan: dict[str, Any]
    latest_dashboard: dict[str, Any] | None = None
    history: list[dict[str, Any]]


class CommandCenterSimResponse(BaseModel):
    status: str
    message: str
    plan: dict[str, Any]
    dashboard: dict[str, Any]
    next_state: str | None = None


class RecruitingPromiseRequest(BaseModel):
    player_id: str
    promise_type: str


class StaffHireRequest(BaseModel):
    candidate_id: str

# --- API Endpoints ---

@app.get("/api/status", response_model=StatusResponse)
def get_status(conn = Depends(get_db)) -> StatusResponse:
    cursor = load_career_state_cursor(conn)
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    clubs = load_clubs(conn) if player_club_id else {}
    player_club = clubs.get(player_club_id) if player_club_id else None
    return {
        "status": "ok",
        "state": {
            "state": cursor.state.value,
            "season_number": cursor.season_number,
            "week": cursor.week,
            "offseason_beat_index": cursor.offseason_beat_index,
            "match_id": cursor.match_id,
        },
        "context": {
            "season_id": season_id,
            "player_club_id": player_club_id,
            "player_club_name": player_club.name if player_club else player_club_id,
        }
    }

@app.get("/api/roster", response_model=RosterResponse)
def get_roster(conn = Depends(get_db)) -> RosterResponse:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise HTTPException(status_code=400, detail="No player club assigned")
    
    try:
        roster = load_club_roster(conn, player_club_id)
    except (CorruptSaveError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="roster save data is damaged") from exc
    lineup = load_lineup_default(conn, player_club_id)
    
    enriched = []
    for i, player in enumerate(roster):
        role = _ROLE_LABELS[i] if i < len(_ROLE_LABELS) else "Utility"
        d = dataclasses.asdict(player)
        d["overall"] = round(player.overall(), 1)
        d["role"] = role
        enriched.append(d)

    return {
        "club_id": player_club_id,
        "roster": enriched,
        "default_lineup": lineup
    }

@app.get("/api/tactics", response_model=TacticsResponse)
def get_tactics(conn = Depends(get_db)) -> TacticsResponse:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise HTTPException(status_code=400, detail="No player club assigned")
    
    clubs = load_clubs(conn)
    club = clubs.get(player_club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
        
    return club.coach_policy.as_dict()


@app.get("/api/standings", response_model=StandingsResponse)
def get_standings(conn = Depends(get_db)) -> StandingsResponse:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id:
        raise HTTPException(status_code=400, detail="No active season")

    clubs = load_clubs(conn)
    saved = {row.club_id: row for row in load_standings(conn, season_id)}
    rows = []
    for club_id, club in clubs.items():
        row = saved.get(club_id)
        rows.append({
            "club_id": club_id,
            "club_name": club.name,
            "wins": row.wins if row else 0,
            "losses": row.losses if row else 0,
            "draws": row.draws if row else 0,
            "points": row.points if row else 0,
            "elimination_differential": row.elimination_differential if row else 0,
            "is_user_club": club_id == player_club_id,
        })
    rows.sort(key=lambda item: (-item["points"], -item["elimination_differential"], item["club_id"]))
    return {"season_id": season_id, "standings": rows}


@app.get("/api/schedule", response_model=ScheduleResponse)
def get_schedule(conn = Depends(get_db)) -> ScheduleResponse:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id:
        raise HTTPException(status_code=400, detail="No active season")

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    completed = load_completed_match_ids(conn, season_id)
    rows = []
    for row in build_schedule_rows(season, completed, player_club_id):
        home = clubs.get(row.home_club_id)
        away = clubs.get(row.away_club_id)
        rows.append({
            "match_id": row.match_id,
            "week": row.week,
            "home_club_id": row.home_club_id,
            "home_club_name": home.name if home else row.home_club_id,
            "away_club_id": row.away_club_id,
            "away_club_name": away.name if away else row.away_club_id,
            "status": row.status,
            "is_user_match": row.is_user_match,
        })
    return {"season_id": season_id, "schedule": rows}


@app.get("/api/news", response_model=NewsResponse)
def get_news(conn = Depends(get_db)) -> NewsResponse:
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise HTTPException(status_code=400, detail="No active season")

    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    match_rows = conn.execute(
        """
        SELECT match_id, season_id, week, home_club_id, away_club_id,
               winner_club_id, home_survivors, away_survivors
        FROM match_records
        WHERE season_id = ?
        ORDER BY week DESC, match_id DESC
        LIMIT 20
        """,
        (season_id,),
    ).fetchall()
    items = build_wire_items(match_rows, clubs, load_awards(conn, season_id), rosters)
    return {
        "season_id": season_id,
        "items": [
            {"tag": item.tag, "text": item.text, "match_id": item.match_id, "player_id": item.player_id}
            for item in items[:20]
        ],
    }


def _command_center_payload(conn) -> CommandCenterResponse:
    state = build_command_center_state(conn)
    club = state["player_club"]
    existing = load_weekly_command_plan(conn, state["season_id"], state["week"], state["player_club_id"])
    plan = existing or build_default_weekly_plan(state)
    history = _sanitized_command_history(conn, state["season_id"])
    latest_dashboard = history[-1]["dashboard"] if history else None
    return {
        "season_id": state["season_id"],
        "week": state["week"],
        "player_club_id": state["player_club_id"],
        "player_club_name": club.name,
        "current_objective": "Review the staff plan, accept it, then simulate the week.",
        "plan": plan,
        "latest_dashboard": latest_dashboard,
        "history": history,
    }


@app.get("/api/command-center", response_model=CommandCenterResponse)
def get_command_center(conn = Depends(get_db)) -> CommandCenterResponse:
    try:
        return _command_center_payload(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/command-center/plan", response_model=CommandCenterResponse)
def save_command_center_plan(update: WeeklyCommandPlanUpdate, conn = Depends(get_db)) -> CommandCenterResponse:
    try:
        state = build_command_center_state(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    plan = build_default_weekly_plan(state, intent=update.intent or "Win Now")
    if update.department_orders:
        merged = dict(plan["department_orders"])
        for key, value in update.department_orders.items():
            if key in merged:
                merged[key] = value
        plan["department_orders"] = merged
    if update.tactics:
        merged_tactics = dict(plan["tactics"])
        for key, value in update.tactics.items():
            if key in merged_tactics:
                merged_tactics[key] = max(0.0, min(1.0, float(value)))
        plan["tactics"] = merged_tactics
    if update.lineup_player_ids:
        roster_ids = {player.id for player in state["roster"]}
        selected = [player_id for player_id in update.lineup_player_ids if player_id in roster_ids]
        if selected:
            players_by_id = {player.id: player for player in state["roster"]}
            plan["lineup"] = {
                "player_ids": selected,
                "players": [
                    {
                        "id": players_by_id[player_id].id,
                        "name": players_by_id[player_id].name,
                        "overall": round(players_by_id[player_id].overall(), 1),
                    }
                    for player_id in selected
                ],
                "summary": "User-adjusted lineup saved for the command plan.",
            }
            from dodgeball_sim.command_center import _lineup_warnings
            plan["warnings"] = _lineup_warnings(list(state["roster"]), selected, plan["intent"], plan["tactics"])
    save_weekly_command_plan(conn, plan)
    conn.commit()
    return _command_center_payload(conn)


@app.get("/api/command-center/history", response_model=list[dict[str, Any]])
def get_command_history(conn = Depends(get_db)) -> list[dict[str, Any]]:
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise HTTPException(status_code=400, detail="No active season")
    return _sanitized_command_history(conn, season_id)


def _sanitized_command_history(conn, season_id: str) -> list[dict[str, Any]]:
    rosters = load_all_rosters(conn)
    player_names = {
        player.id: player.name
        for roster in rosters.values()
        for player in roster
    }
    sanitized: list[dict[str, Any]] = []
    for record in load_command_history(conn, season_id):
        next_record = dict(record)
        dashboard = record.get("dashboard")
        if isinstance(dashboard, dict):
            next_record["dashboard"] = _sanitize_dashboard_copy(dashboard, player_names)
        sanitized.append(next_record)
    return sanitized


def _sanitize_dashboard_copy(dashboard: dict[str, Any], player_names: dict[str, str]) -> dict[str, Any]:
    next_dashboard = dict(dashboard)
    lanes = []
    for lane in dashboard.get("lanes", []):
        if not isinstance(lane, dict):
            lanes.append(lane)
            continue
        next_lane = dict(lane)
        summary = str(next_lane.get("summary", ""))
        if summary == "Tactical diagnosis correlates execution metrics to the mandated game plan.":
            next_lane["summary"] = "The staff review ties the result to visible pressure, target selection, and late-match execution."
        next_lane["items"] = [
            _sanitize_dashboard_item(str(item), player_names)
            for item in next_lane.get("items", [])
        ]
        lanes.append(next_lane)
    next_dashboard["lanes"] = lanes
    return next_dashboard


def _sanitize_dashboard_item(text: str, player_names: dict[str, str]) -> str:
    target_match = _LEGACY_TARGET_EVIDENCE_RE.match(text)
    if target_match:
        player_id, count = target_match.groups()
        player_name = player_names.get(player_id, "The busiest defender")
        return f"{player_name} absorbed the most pressure, drawing {int(count)} throws."
    star_match = _LEGACY_STAR_SETTING_RE.match(text)
    if star_match:
        value = float(star_match.group(1))
        if value >= 0.7:
            return "The plan leaned into star containment and forced their best players to work through traffic."
        if value <= 0.35:
            return "The plan spread attention across the lineup instead of overcommitting to one star matchup."
        return "The plan balanced star containment with broader lineup pressure."
    rush_match = _LEGACY_RUSH_SETTING_RE.match(text)
    if rush_match:
        value = float(rush_match.group(1))
        if value >= 0.65:
            return "The team played on the front foot, using frequent pressure to speed up possessions."
        if value <= 0.35:
            return "The team stayed patient, choosing shape and recovery over constant rush pressure."
        return "The team mixed patient possessions with selective rush pressure."
    return text


def _regular_season_matches(season: Season) -> list[ScheduledMatch]:
    return [
        match
        for match in season.scheduled_matches
        if not is_playoff_match_id(season.season_id, match.match_id)
    ]


def _standings_with_all_clubs(standings: list[StandingsRow], clubs: dict[str, Any]) -> list[StandingsRow]:
    by_id = {row.club_id: row for row in standings}
    rows = [
        by_id.get(club_id, StandingsRow(club_id, wins=0, losses=0, draws=0, elimination_differential=0, points=0))
        for club_id in clubs
    ]
    rows.sort(key=lambda row: (-row.points, -row.elimination_differential, row.club_id))
    return rows


def _regular_season_complete(conn, season: Season) -> bool:
    completed = load_completed_match_ids(conn, season.season_id)
    return all(match.match_id in completed for match in _regular_season_matches(season))


def _simulate_ai_playoff_matches(
    conn,
    matches: list[ScheduledMatch],
    clubs: dict[str, Any],
    player_club_id: str,
    season_id: str,
) -> None:
    if not matches:
        return
    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    _validate_match_rosters(matches, rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"
    for match in matches:
        simulate_scheduled_match(
            conn,
            scheduled=match,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )


def _advance_playoffs_if_needed(conn, season: Season, clubs: dict[str, Any], player_club_id: str) -> Season:
    if load_season_outcome(conn, season.season_id) is not None:
        return season
    if not _regular_season_complete(conn, season):
        return season

    while True:
        bracket = load_playoff_bracket(conn, season.season_id)
        completed = load_completed_match_ids(conn, season.season_id)
        if bracket is None:
            standings = _standings_with_all_clubs(load_standings(conn, season.season_id), clubs)
            next_week = max((match.week for match in _regular_season_matches(season)), default=0) + 1
            bracket, semifinals = create_semifinal_bracket(season.season_id, standings, next_week)
            save_playoff_bracket(conn, bracket)
            save_scheduled_matches(conn, semifinals)
            conn.commit()
            season = load_season(conn, season.season_id)
            continue

        if bracket.status == "semifinals_scheduled":
            semifinal_ids = {f"{season.season_id}_p_r1_m1", f"{season.season_id}_p_r1_m2"}
            semifinal_matches = [match for match in season.scheduled_matches if match.match_id in semifinal_ids]
            pending = [match for match in semifinal_matches if match.match_id not in completed]
            ai_pending = [
                match
                for match in pending
                if player_club_id not in (match.home_club_id, match.away_club_id)
            ]
            if ai_pending:
                _simulate_ai_playoff_matches(conn, ai_pending, clubs, player_club_id, season.season_id)
                recompute_regular_season_standings(conn, season)
                conn.commit()
                continue
            if pending:
                return season
            winners = {
                row["match_id"]: row["winner_club_id"]
                for row in conn.execute(
                    "SELECT match_id, winner_club_id FROM match_records WHERE match_id IN (?, ?)",
                    (f"{season.season_id}_p_r1_m1", f"{season.season_id}_p_r1_m2"),
                ).fetchall()
            }
            next_week = max(match.week for match in semifinal_matches) + 1
            bracket, final = create_final_match(bracket, winners, next_week)
            save_playoff_bracket(conn, bracket)
            save_scheduled_matches(conn, [final])
            conn.commit()
            season = load_season(conn, season.season_id)
            continue

        if bracket.status == "final_scheduled":
            final = next(
                (match for match in season.scheduled_matches if match.match_id == f"{season.season_id}_p_final"),
                None,
            )
            if final is None:
                return season
            if final.match_id not in completed:
                if player_club_id in (final.home_club_id, final.away_club_id):
                    return season
                _simulate_ai_playoff_matches(conn, [final], clubs, player_club_id, season.season_id)
                recompute_regular_season_standings(conn, season)
                completed = load_completed_match_ids(conn, season.season_id)
            if final.match_id in completed:
                row = conn.execute(
                    "SELECT winner_club_id FROM match_records WHERE match_id = ?",
                    (final.match_id,),
                ).fetchone()
                if row is None or row["winner_club_id"] is None:
                    return season
                save_season_outcome(
                    conn,
                    outcome_from_final(
                        bracket,
                        final_match_id=final.match_id,
                        home_club_id=final.home_club_id,
                        away_club_id=final.away_club_id,
                        winner_club_id=row["winner_club_id"],
                    ),
                )
                save_playoff_bracket(conn, dataclasses.replace(bracket, status="complete"))
                conn.commit()
            return season
        return season


def _choose_next_user_match_after_automation(
    conn,
    season: Season,
    clubs: dict[str, Any],
    player_club_id: str,
) -> tuple[Season, list[ScheduledMatch], str]:
    season = _advance_playoffs_if_needed(conn, season, clubs, player_club_id)
    completed = load_completed_match_ids(conn, season.season_id)
    chosen, stop_reason = _choose_user_match(season, completed, player_club_id)
    if chosen:
        return season, chosen, stop_reason

    ai_regular_pending = [
        match
        for match in _regular_season_matches(season)
        if match.match_id not in completed
        and player_club_id not in (match.home_club_id, match.away_club_id)
    ]
    if ai_regular_pending:
        _simulate_ai_playoff_matches(conn, ai_regular_pending, clubs, player_club_id, season.season_id)
        recompute_regular_season_standings(conn, season)
        conn.commit()
        season = load_season(conn, season.season_id)
        season = _advance_playoffs_if_needed(conn, season, clubs, player_club_id)
        completed = load_completed_match_ids(conn, season.season_id)
        chosen, stop_reason = _choose_user_match(season, completed, player_club_id)
    return season, chosen, stop_reason


@app.get("/api/dynasty-office", response_model=dict[str, Any])
def get_dynasty_office(conn = Depends(get_db)) -> dict[str, Any]:
    try:
        return build_dynasty_office_state(conn)
    except CorruptSaveError as exc:
        raise HTTPException(status_code=409, detail=f"Corrupted dynasty state: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/dynasty-office/promises", response_model=dict[str, Any])
def create_recruiting_promise(request: RecruitingPromiseRequest, conn = Depends(get_db)) -> dict[str, Any]:
    try:
        return save_recruiting_promise(conn, request.player_id, request.promise_type)
    except CorruptSaveError as exc:
        raise HTTPException(status_code=409, detail=f"Corrupted dynasty state: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/dynasty-office/staff/hire", response_model=dict[str, Any])
def hire_dynasty_staff(request: StaffHireRequest, conn = Depends(get_db)) -> dict[str, Any]:
    try:
        return hire_staff_candidate(conn, request.candidate_id)
    except CorruptSaveError as exc:
        raise HTTPException(status_code=409, detail=f"Corrupted dynasty state: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/tactics", response_model=dict[str, str])
def update_tactics(policy: CoachPolicyUpdate, conn = Depends(get_db)) -> dict[str, str]:
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise HTTPException(status_code=400, detail="No player club assigned")
    
    clubs = load_clubs(conn)
    club = clubs.get(player_club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
        
    new_policy = CoachPolicy(
        target_stars=policy.target_stars,
        target_ball_holder=policy.target_ball_holder,
        risk_tolerance=policy.risk_tolerance,
        sync_throws=policy.sync_throws,
        rush_frequency=policy.rush_frequency,
        rush_proximity=policy.rush_proximity,
        tempo=policy.tempo,
        catch_bias=policy.catch_bias
    )
    
    updated_club = dataclasses.replace(club, coach_policy=new_policy)
    roster = load_club_roster(conn, player_club_id)
    save_club(conn, updated_club, roster)
    conn.commit()
    
    return {"status": "success"}


def _simulation_request(command: SimCommand, week: int, season) -> SimRequest:
    mode = command.mode
    if mode == "week":
        return SimRequest(mode="week", current_week=week, include_user_matches=True)
    if mode == "next_user_match":
        return SimRequest(mode="to_next_user_match", include_user_matches=False)
    if mode == "multiple_weeks":
        return SimRequest(mode="multiple_weeks", current_week=week, weeks=max(1, command.weeks), include_user_matches=False)
    if mode == "milestone":
        milestone = command.milestone or "playoffs"
        milestone_week = None
        if milestone in {"season_end", "recruitment_day", "offseason"}:
            milestone_week = season.total_weeks() + 1
        return SimRequest(mode="milestone", milestone=milestone, milestone_week=milestone_week, include_user_matches=True)
    if mode == "user_match":
        return SimRequest(mode="user_match", include_user_matches=False)
    raise HTTPException(status_code=400, detail=f"Unknown simulation mode: {mode}")


def _choose_user_match(season, completed: set[str], player_club_id: str):
    for match in sorted(season.scheduled_matches, key=lambda item: (item.week, item.match_id)):
        if match.match_id in completed:
            continue
        if player_club_id in (match.home_club_id, match.away_club_id):
            return [match], "user_match"
    return [], "season_complete"


def _run_simulation_command(conn, command: SimCommand) -> SimResponse:
    player_club_id = get_state(conn, "player_club_id")
    season_id = get_state(conn, "active_season_id")
    if not player_club_id or not season_id:
        raise HTTPException(status_code=400, detail="No active season or club")

    season = load_season(conn, season_id)
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH:
        raise HTTPException(
            status_code=409,
            detail="Simulation requires career state season_active_pre_match.",
        )
    clubs = load_clubs(conn)
    week = cursor.week or current_week(conn, season) or 1
    if command.mode == "user_match":
        season, chosen, stop_reason = _choose_next_user_match_after_automation(conn, season, clubs, player_club_id)
        completed = load_completed_match_ids(conn, season_id)
    else:
        season = _advance_playoffs_if_needed(conn, season, clubs, player_club_id)
        completed = load_completed_match_ids(conn, season_id)
        chosen, stop = choose_matches_to_sim(
            list(season.scheduled_matches),
            completed,
            player_club_id,
            _simulation_request(command, week, season),
        )
        stop_reason = stop.reason

    if not chosen:
        if stop_reason == "season_complete" and cursor.state == CareerState.SEASON_ACTIVE_PRE_MATCH:
            cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
            save_career_state_cursor(conn, cursor)
            conn.commit()
        return {
            "status": "success",
            "message": "No matches simulated.",
            "simulated_count": 0,
            "stop_reason": stop_reason,
            "next_state": cursor.state.value,
        }

    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    _validate_match_rosters(chosen, rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"

    records = [
        simulate_scheduled_match(
            conn,
            scheduled=scheduled,
            clubs=clubs,
            rosters=rosters,
            root_seed=root_seed,
            difficulty=difficulty,
        )
        for scheduled in chosen
    ]
    recompute_regular_season_standings(conn, season)
    next_week = current_week(conn, season) or week
    if command.mode == "user_match" and len(records) == 1:
        in_match = advance(cursor, CareerState.SEASON_ACTIVE_IN_MATCH, week=records[0].week, match_id=records[0].match_id)
        cursor = advance(in_match, CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING, match_id=records[0].match_id)
    else:
        cursor = dataclasses.replace(cursor, week=next_week)
    save_career_state_cursor(conn, cursor)
    conn.commit()

    return {
        "status": "success",
        "simulated_count": len(records),
        "stop_reason": stop_reason,
        "message": f"Simulated {len(records)} matches.",
        "match_id": records[0].match_id if command.mode == "user_match" and records else None,
        "next_state": cursor.state.value,
    }


def _apply_command_plan_to_match(conn, plan: dict[str, Any], match_id: str, club_id: str) -> None:
    clubs = load_clubs(conn)
    club = clubs.get(club_id)
    if club is None:
        raise HTTPException(status_code=404, detail="Club not found")
    tactics = plan.get("tactics", {})
    policy_values = club.coach_policy.as_dict()
    for key in policy_values:
        if key in tactics:
            policy_values[key] = max(0.0, min(1.0, float(tactics[key])))
    updated_club = dataclasses.replace(club, coach_policy=CoachPolicy(**policy_values))
    save_club(conn, updated_club, load_club_roster(conn, club_id))
    lineup_ids = plan.get("lineup", {}).get("player_ids") or []
    if lineup_ids:
        save_match_lineup_override(conn, match_id, club_id, list(lineup_ids))


@app.post("/api/command-center/simulate", response_model=CommandCenterSimResponse)
def simulate_command_center_week(update: WeeklyCommandPlanUpdate | None = None, conn = Depends(get_db)) -> CommandCenterSimResponse:
    player_club_id = get_state(conn, "player_club_id")
    season_id = get_state(conn, "active_season_id")
    if not player_club_id or not season_id:
        raise HTTPException(status_code=400, detail="No active season or club")
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_PRE_MATCH:
        raise HTTPException(status_code=409, detail="Command center simulation requires season_active_pre_match.")

    state = build_command_center_state(conn)
    existing = load_weekly_command_plan(conn, state["season_id"], state["week"], state["player_club_id"])
    plan = existing or build_default_weekly_plan(state, intent=(update.intent if update else None) or "Win Now")
    if update is not None:
        if update.intent and update.intent != plan.get("intent"):
            plan = build_default_weekly_plan(state, intent=update.intent)
        if update.department_orders:
            plan["department_orders"] = {**plan["department_orders"], **update.department_orders}
        if update.tactics:
            plan["tactics"] = {**plan["tactics"], **{key: max(0.0, min(1.0, float(value))) for key, value in update.tactics.items() if key in plan["tactics"]}}
        if update.lineup_player_ids:
            plan["lineup"]["player_ids"] = update.lineup_player_ids
    save_weekly_command_plan(conn, plan)

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
            }
        raise HTTPException(status_code=409, detail=f"No user match available: {stop_reason}")

    scheduled = chosen[0]
    _apply_command_plan_to_match(conn, plan, scheduled.match_id, player_club_id)
    rosters = load_all_rosters(conn)
    root_seed = normalize_root_seed(get_state(conn, "root_seed", "1"), default_on_invalid=True)
    if ensure_ai_rosters_playable(conn, clubs, rosters, root_seed, season_id, player_club_id):
        rosters = load_all_rosters(conn)
    _validate_match_rosters([scheduled], rosters)
    difficulty = get_state(conn, "difficulty", "pro") or "pro"
    record = simulate_scheduled_match(
        conn,
        scheduled=scheduled,
        clubs=clubs,
        rosters=rosters,
        root_seed=root_seed,
        difficulty=difficulty,
    )
    recompute_regular_season_standings(conn, season)
    dashboard = build_post_week_dashboard(conn, plan, record)
    save_command_history_record(
        conn,
        {
            "season_id": season_id,
            "week": record.week,
            "match_id": record.match_id,
            "opponent_club_id": record.away_club_id if record.home_club_id == player_club_id else record.home_club_id,
            "intent": plan["intent"],
            "plan": plan,
            "dashboard": dashboard,
        },
    )
    season = load_season(conn, season.season_id)
    season, next_chosen, _stop_reason = _choose_next_user_match_after_automation(conn, season, clubs, player_club_id)
    if next_chosen:
        cursor = dataclasses.replace(
            cursor,
            state=CareerState.SEASON_ACTIVE_PRE_MATCH,
            week=next_chosen[0].week,
            match_id=None,
        )
    else:
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    save_career_state_cursor(conn, cursor)
    conn.commit()
    return {
        "status": "success",
        "message": f"Simulated Week {record.week} command plan.",
        "plan": plan,
        "dashboard": dashboard,
        "next_state": cursor.state.value,
    }


@app.post("/api/sim", response_model=SimResponse)
def simulate_command(command: SimCommand, conn = Depends(get_db)) -> SimResponse:
    return _run_simulation_command(conn, command)


@app.post("/api/sim/week", response_model=SimResponse)
def simulate_week(conn = Depends(get_db)) -> SimResponse:
    return _run_simulation_command(conn, SimCommand(mode="week"))


def _validate_match_rosters(chosen, rosters) -> None:
    for scheduled in chosen:
        for club_id in (scheduled.home_club_id, scheduled.away_club_id):
            if len(rosters.get(club_id, ())) < 1:
                raise HTTPException(
                    status_code=409,
                    detail=f"Club {club_id} does not have a playable roster.",
                )


def _score_player(stats: PlayerMatchStats | None) -> float:
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


def _stats_for_match(conn, match_id: str) -> dict[str, PlayerMatchStats]:
    rows = conn.execute("SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,)).fetchall()
    return {
        row["player_id"]: PlayerMatchStats(
            throws_attempted=row["throws_attempted"],
            throws_on_target=row["throws_on_target"],
            eliminations_by_throw=row["eliminations_by_throw"],
            catches_attempted=row["catches_attempted"],
            catches_made=row["catches_made"],
            times_targeted=row["times_targeted"],
            dodges_successful=row["dodges_successful"],
            times_hit=row["times_hit"],
            times_eliminated=row["times_eliminated"],
            revivals_caused=row["revivals_caused"],
            clutch_events=row["clutch_events"],
            elimination_plus_minus=row["elimination_plus_minus"],
            minutes_played=row["minutes_played"],
        )
        for row in rows
    }


def _match_record_row(conn, match_id: str):
    return conn.execute("SELECT * FROM match_records WHERE match_id = ?", (match_id,)).fetchone()


def _roster_snapshots(conn, match_id: str, home_club_id: str, away_club_id: str) -> dict[str, list[dict[str, Any]]]:
    try:
        return {
            home_club_id: fetch_roster_snapshot(conn, match_id, home_club_id),
            away_club_id: fetch_roster_snapshot(conn, match_id, away_club_id),
        }
    except (KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Match roster snapshot is damaged.") from exc


def _command_plan_for_match(conn, match_id: str, season_id: str) -> dict[str, Any] | None:
    for record in load_command_history(conn, season_id):
        if record.get("match_id") == match_id:
            plan = record.get("plan")
            return plan if isinstance(plan, dict) else None
    return None


@app.get("/api/matches/{match_id}/replay", response_model=MatchReplayResponse)
def get_match_replay(match_id: str, conn = Depends(get_db)) -> MatchReplayResponse:
    row = _match_record_row(conn, match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if row["engine_match_id"] is None:
        raise HTTPException(status_code=409, detail="Match replay is not available")

    clubs = load_clubs(conn)
    home = clubs.get(row["home_club_id"])
    away = clubs.get(row["away_club_id"])
    if home is None or away is None:
        raise HTTPException(status_code=409, detail="Match club data is damaged")

    try:
        stored = fetch_match(conn, int(row["engine_match_id"]))
    except (KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Match replay data is damaged") from exc

    snapshots = _roster_snapshots(conn, match_id, row["home_club_id"], row["away_club_id"])
    name_map = {
        str(player.get("id", "")): str(player.get("name", player.get("id", "")))
        for players in snapshots.values()
        for player in players
    }
    events = []
    for index, event in enumerate(stored["events"]):
        events.append({
            **event,
            "index": index,
            "label": event_label(event, name_map),
            "detail": event_detail(event, name_map),
        })

    stats = _stats_for_match(conn, match_id)
    proof = build_replay_proof(
        stored["events"],
        name_map=name_map,
        roster_snapshots=snapshots,
        home_club_id=row["home_club_id"],
        away_club_id=row["away_club_id"],
        home_survivors=row["home_survivors"],
        away_survivors=row["away_survivors"],
        player_match_stats=stats,
        command_plan=_command_plan_for_match(conn, match_id, row["season_id"]),
    )
    top = sorted(stats.items(), key=lambda item: (-_score_player(item[1]), item[0]))[:6]
    top_performers = [
        {
            "player_id": player_id,
            "player_name": name_map.get(player_id, player_id),
            "score": round(_score_player(stat), 1),
            "eliminations_by_throw": stat.eliminations_by_throw,
            "catches_made": stat.catches_made,
            "dodges_successful": stat.dodges_successful,
        }
        for player_id, stat in top
    ]
    mvp_id = compute_match_mvp(stats)
    winner_id = row["winner_club_id"]
    winner_name = clubs[winner_id].name if winner_id in clubs else "Draw"
    report = {
        "winner_name": winner_name,
        "match_mvp_player_id": mvp_id,
        "match_mvp_name": name_map.get(mvp_id, mvp_id) if mvp_id else None,
        "top_performers": top_performers,
        "turning_point": next(
            (event["label"] for event in events if event.get("event_type") == "throw" and event.get("outcome", {}).get("resolution") in {"hit", "failed_catch", "catch"}),
            "No high-leverage swing detected.",
        ),
        "evidence_lanes": proof["evidence_report"]["evidence_lanes"],
    }
    return {
        "match_id": match_id,
        "season_id": row["season_id"],
        "week": row["week"],
        "home_club_id": row["home_club_id"],
        "home_club_name": home.name,
        "away_club_id": row["away_club_id"],
        "away_club_name": away.name,
        "winner_club_id": winner_id,
        "winner_name": winner_name,
        "home_survivors": row["home_survivors"],
        "away_survivors": row["away_survivors"],
        "events": events,
        "proof_events": proof["proof_events"],
        "key_play_indices": proof["key_play_indices"],
        "report": report,
    }


@app.post("/api/matches/{match_id}/acknowledge", response_model=AcknowledgeMatchResponse)
def acknowledge_match_report(match_id: str, conn = Depends(get_db)) -> AcknowledgeMatchResponse:
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING or cursor.match_id != match_id:
        raise HTTPException(status_code=409, detail="No matching report is pending")
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise HTTPException(status_code=400, detail="No active season")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    season, chosen, _stop_reason = _choose_next_user_match_after_automation(
        conn,
        season,
        clubs,
        get_state(conn, "player_club_id") or "",
    )
    if chosen:
        cursor = advance(cursor, CareerState.SEASON_ACTIVE_PRE_MATCH, week=chosen[0].week, match_id=None)
    else:
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    save_career_state_cursor(conn, cursor)
    conn.commit()
    return {
        "status": "success",
        "state": {
            "state": cursor.state.value,
            "season_number": cursor.season_number,
            "week": cursor.week,
            "offseason_beat_index": cursor.offseason_beat_index,
            "match_id": cursor.match_id,
        },
    }


# --- Save Management ---

@app.get("/api/save-state", response_model=SaveStateResponse)
def api_save_state():
    global _active_save_path
    if _active_save_path is None:
        return SaveStateResponse(loaded=False, active_path=None, meta=None)
    meta = _read_save_meta(_active_save_path)
    return SaveStateResponse(loaded=True, active_path=str(_active_save_path), meta=SaveInfo(**meta))


@app.get("/api/saves", response_model=SaveListResponse)
def api_list_saves():
    global _active_save_path
    saves = []
    SAVES_DIR.mkdir(exist_ok=True)
    for db_file in sorted(SAVES_DIR.glob("*.db")):
        saves.append(SaveInfo(**_read_save_meta(db_file)))
    # Legacy root-level save
    if DEFAULT_DB_PATH.exists():
        saves.append(SaveInfo(**_read_save_meta(DEFAULT_DB_PATH)))
    return SaveListResponse(saves=saves, active_path=str(_active_save_path) if _active_save_path else None)


@app.post("/api/saves/new")
def api_new_save(req: NewSaveRequest):
    global _active_save_path
    SAVES_DIR.mkdir(exist_ok=True)
    safe_name = "".join(c for c in req.name if c.isalnum() or c in "-_ ").strip() or "save"
    path = SAVES_DIR / f"{safe_name}.db"
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Save '{safe_name}' already exists.")
    conn = connect(path)
    try:
        initialize_curated_manager_career(conn, req.club_id, req.root_seed)
    finally:
        conn.close()
    _active_save_path = path
    return {"status": "ok", "path": str(path)}


class LoadSaveRequest(BaseModel):
    path: str


@app.post("/api/saves/load")
def api_load_save(req: LoadSaveRequest):
    global _active_save_path
    resolved = _resolve_managed_save_path(req.path, allow_legacy=True)
    if not _looks_like_dodgeball_save(resolved):
        raise HTTPException(
            status_code=400,
            detail="File is not a recognizable Dodgeball Manager save.",
        )
    _active_save_path = resolved
    return {"status": "ok", "path": str(resolved)}


class DeleteSaveRequest(BaseModel):
    path: str


@app.post("/api/saves/delete")
def api_delete_save(req: DeleteSaveRequest):
    global _active_save_path
    resolved = _resolve_managed_save_path(req.path, allow_legacy=False)
    if resolved == DEFAULT_DB_PATH.resolve():
        raise HTTPException(status_code=403, detail="Cannot delete the legacy save via this endpoint.")
    resolved.unlink()
    if _active_save_path is not None and _active_save_path.resolve() == resolved:
        _active_save_path = None
    return {"status": "ok"}


@app.post("/api/saves/unload")
def api_unload_save():
    global _active_save_path
    _active_save_path = None
    return {"status": "ok"}


@app.get("/api/saves/clubs")
def api_list_clubs():
    clubs = curated_clubs()
    return {"clubs": [{"club_id": c.club_id, "name": c.name, "tagline": getattr(c, "tagline", ""), "colors": getattr(c, "colors", "")} for c in clubs]}


_OFFSEASON_STATES = {
    CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
    CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
    CareerState.NEXT_SEASON_READY,
}

_RECRUITMENT_INDEX = OFFSEASON_CEREMONY_BEATS.index("recruitment")
_SCHEDULE_REVEAL_INDEX = OFFSEASON_CEREMONY_BEATS.index("schedule_reveal")


def _build_beat_response(conn, cursor):
    """Build the full offseason beat payload from current cursor + DB."""
    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id) if season_id else None
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    beat_index = clamp_offseason_beat_index(cursor.offseason_beat_index)
    standings = load_standings(conn, season_id) if season_id else []
    awards = load_awards(conn, season_id) if season_id else []
    season_outcome = load_season_outcome(conn, season_id) if season_id else None
    free_agents = load_free_agents(conn)
    signed_player_id = get_state(conn, "offseason_draft_signed_player_id") or ""

    next_preview: Any = None
    if beat_index >= _SCHEDULE_REVEAL_INDEX:
        season_number = cursor.season_number or 1
        root_seed = stored_root_seed(conn)
        next_preview = create_next_manager_season(clubs, root_seed, season_number + 1, (season.year + 1) if season else 2026)

    dev_rows_raw = get_state(conn, "offseason_development_json") or "[]"
    ret_rows_raw = get_state(conn, "offseason_retirements_json") or "[]"
    records_json = get_state(conn, "offseason_records_json")
    hof_json = get_state(conn, "offseason_hof_json")
    rookie_preview_json = get_state(conn, "offseason_rookie_preview_json")

    try:
        dev_rows = json.loads(dev_rows_raw)
    except (TypeError, json.JSONDecodeError):
        dev_rows = []
    try:
        ret_rows = json.loads(ret_rows_raw)
    except (TypeError, json.JSONDecodeError):
        ret_rows = []

    beat = build_offseason_ceremony_beat(
        beat_index=beat_index,
        season=season,
        clubs=clubs,
        rosters=rosters,
        standings=standings,
        awards=awards,
        player_club_id=get_state(conn, "player_club_id"),
        next_season=next_preview,
        development_rows=dev_rows,
        retirement_rows=ret_rows,
        draft_pool=free_agents,
        signed_player_id=signed_player_id,
        season_outcome=season_outcome,
        records_payload_json=records_json,
        hof_payload_json=hof_json,
        rookie_preview_payload_json=rookie_preview_json,
    )
    state = cursor.state.value
    is_recruitment = OFFSEASON_CEREMONY_BEATS[beat_index] == "recruitment"
    is_last = beat_index >= _SCHEDULE_REVEAL_INDEX
    can_advance = (
        cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
        and not is_last
        and not is_recruitment
    )
    can_recruit = (
        cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING
        and not signed_player_id
    )
    can_begin_season = cursor.state == CareerState.NEXT_SEASON_READY

    return {
        "beat_index": beat_index,
        "total_beats": len(OFFSEASON_CEREMONY_BEATS),
        "key": beat.key,
        "title": beat.title,
        "body": beat.body,
        "state": state,
        "can_advance": can_advance,
        "can_recruit": can_recruit,
        "can_begin_season": can_begin_season,
        "signed_player_id": signed_player_id,
    }


@app.get("/api/offseason/beat")
def get_offseason_beat(conn = Depends(get_db)):
    cursor = load_career_state_cursor(conn)
    if cursor.state not in _OFFSEASON_STATES:
        raise HTTPException(status_code=409, detail=f"Not in an offseason state (current: {cursor.state.value})")
    season_id = get_state(conn, "active_season_id")
    if season_id:
        season = load_season(conn, season_id)
        if season:
            clubs = load_clubs(conn)
            rosters = load_all_rosters(conn)
            finalize_season(conn, season, rosters)
            root_seed = stored_root_seed(conn)
            initialize_manager_offseason(conn, season, clubs, rosters, root_seed)
            rosters = load_all_rosters(conn)
    return _build_beat_response(conn, cursor)


@app.post("/api/offseason/advance")
def advance_offseason_beat(conn = Depends(get_db)):
    cursor = load_career_state_cursor(conn)
    if cursor.state not in _OFFSEASON_STATES:
        raise HTTPException(status_code=409, detail=f"Not in an offseason state (current: {cursor.state.value})")
    beat_index = clamp_offseason_beat_index(cursor.offseason_beat_index)
    if beat_index >= _SCHEDULE_REVEAL_INDEX:
        raise HTTPException(status_code=409, detail="Already at the final beat. Use begin-season to start next season.")
    if cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT and OFFSEASON_CEREMONY_BEATS[beat_index] == "recruitment":
        raise HTTPException(status_code=409, detail="Cannot advance past recruitment without signing. Use /api/offseason/recruit first.")

    next_index = beat_index + 1
    next_key = OFFSEASON_CEREMONY_BEATS[next_index]
    if next_key == "recruitment":
        from dodgeball_sim.career_state import advance as state_advance
        cursor = state_advance(cursor, CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING, offseason_beat_index=next_index)
    else:
        cursor = dataclasses.replace(cursor, offseason_beat_index=next_index)

    save_career_state_cursor(conn, cursor)
    conn.commit()
    return _build_beat_response(conn, cursor)


@app.post("/api/offseason/recruit")
def offseason_recruit(conn = Depends(get_db)):
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING:
        raise HTTPException(status_code=409, detail=f"Not in recruitment state (current: {cursor.state.value})")
    signed_player_id = get_state(conn, "offseason_draft_signed_player_id") or ""
    if signed_player_id:
        raise HTTPException(status_code=409, detail="Already recruited a player this offseason.")
    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        raise HTTPException(status_code=400, detail="No player club assigned")
    signed = sign_best_rookie(conn, player_club_id, cursor.season_number or 1)
    from dodgeball_sim.career_state import advance as state_advance
    cursor = state_advance(cursor, CareerState.NEXT_SEASON_READY, offseason_beat_index=_SCHEDULE_REVEAL_INDEX)
    save_career_state_cursor(conn, cursor)
    conn.commit()
    return {
        **_build_beat_response(conn, cursor),
        "signed_player": {
            "id": signed.id,
            "name": signed.name,
            "overall": round(signed.overall(), 1),
            "age": signed.age,
        } if signed else None,
    }


@app.post("/api/offseason/begin-season")
def offseason_begin_season(conn = Depends(get_db)):
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.NEXT_SEASON_READY:
        raise HTTPException(status_code=409, detail=f"Not ready to begin next season (current: {cursor.state.value})")
    clubs = load_clubs(conn)
    new_cursor = begin_next_season(conn, cursor, clubs)
    return {
        "status": "success",
        "state": {
            "state": new_cursor.state.value,
            "season_number": new_cursor.season_number,
            "week": new_cursor.week,
            "offseason_beat_index": new_cursor.offseason_beat_index,
            "match_id": new_cursor.match_id,
        },
    }


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def unknown_api_route(full_path: str):
    raise HTTPException(status_code=404, detail=f"Unknown API route: /api/{full_path}")

# --- SPA Routing ---

frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        path = frontend_dist / full_path
        if path.exists() and path.is_file():
            return FileResponse(path)
        return FileResponse(frontend_dist / "index.html")
