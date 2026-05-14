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
    set_state,
    load_league_records,
    load_club_trophies,
    load_retired_players,
    load_player_career_stats,
    load_hall_of_fame,
    load_rivalry_records,
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
from dodgeball_sim.development import calculate_potential_tier
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
    refresh_weekly_plan_context,
)
from dodgeball_sim.dynasty_office import (
    build_dynasty_office_state,
    hire_staff_candidate,
    save_recruiting_promise,
)
from dodgeball_sim.league_memory import recent_match_item
from dodgeball_sim.match_orchestration import _choose_next_user_match_after_automation
from dodgeball_sim.use_cases import SimulateWeekError, simulate_week as _simulate_week
from dodgeball_sim.command_week_service import (
    CommandWeekError,
    command_center_payload,
    command_history_payload,
    run_simulation_command,
    save_command_center_plan_payload,
)
from dodgeball_sim.web_status_service import (
    build_news_payload,
    build_roster_payload,
    build_schedule_payload,
    build_standings_payload,
    build_status_payload,
    build_tactics_payload,
    update_tactics_payload,
)
from dodgeball_sim.replay_service import (
    ReplayError,
    acknowledge_match_payload,
    match_replay_payload,
)
from dodgeball_sim.offseason_service import (
    OffseasonError,
    advance_offseason_beat_payload,
    begin_next_season_payload,
    get_offseason_beat_payload,
    recruit_offseason_payload,
)
from dodgeball_sim.offseason_presentation import build_beat_payload
from dodgeball_sim.save_service import (
    SaveServiceError,
    build_from_scratch_save,
    create_new_save,
    list_clubs_payload,
    list_saves_payload,
    looks_like_dodgeball_save,
    read_save_meta,
    resolve_managed_save_path,
    starting_prospects_payload,
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
    try:
        return resolve_managed_save_path(
            raw,
            saves_dir=SAVES_DIR,
            default_db_path=DEFAULT_DB_PATH,
            allow_legacy=allow_legacy,
        )
    except SaveServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _looks_like_dodgeball_save(path: Path) -> bool:
    """Verify the file at *path* is a SQLite save with our schema row.

    The check opens through `connect()` so that schema migrations are exercised
    the same way the live request path would exercise them; if any step fails,
    the file is rejected.
    """
    return looks_like_dodgeball_save(path)

_ROLE_LABELS = ["Captain", "Striker", "Anchor", "Runner", "Rookie", "Utility"]


def _build_beat_payload(*args, **kwargs):
    """Compatibility wrapper for tests; implementation lives in offseason_presentation."""
    return build_beat_payload(*args, **kwargs)


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
    return read_save_meta(path)

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
    recent_matches: list[dict[str, Any]] | None = None


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


class BuildFromScratchRequest(BaseModel):
    save_name: str
    club_name: str
    city: str
    colors: str
    coach_name: str
    coach_backstory: str
    roster_player_ids: list[str]
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
    aftermath: dict[str, Any] | None = None


class RecruitingPromiseRequest(BaseModel):
    player_id: str
    promise_type: str


class StaffHireRequest(BaseModel):
    candidate_id: str


class PitchAngleRequest(BaseModel):
    angle: str

# --- API Endpoints ---

@app.get("/api/status", response_model=StatusResponse)
def get_status(conn = Depends(get_db)) -> StatusResponse:
    return build_status_payload(conn)

@app.get("/api/roster", response_model=RosterResponse)
def get_roster(conn = Depends(get_db)) -> RosterResponse:
    try:
        return build_roster_payload(conn)
    except CorruptSaveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/api/tactics", response_model=TacticsResponse)
def get_tactics(conn = Depends(get_db)) -> TacticsResponse:
    try:
        return build_tactics_payload(conn)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/standings", response_model=StandingsResponse)
def get_standings(conn = Depends(get_db)) -> StandingsResponse:
    try:
        return build_standings_payload(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/schedule", response_model=ScheduleResponse)
def get_schedule(conn = Depends(get_db)) -> ScheduleResponse:
    try:
        return build_schedule_payload(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/news", response_model=NewsResponse)
def get_news(conn = Depends(get_db)) -> NewsResponse:
    try:
        return build_news_payload(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/command-center", response_model=CommandCenterResponse)
def get_command_center(conn = Depends(get_db)) -> CommandCenterResponse:
    try:
        return command_center_payload(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/command-center/plan", response_model=CommandCenterResponse)
def save_command_center_plan(update: WeeklyCommandPlanUpdate, conn = Depends(get_db)) -> CommandCenterResponse:
    try:
        return save_command_center_plan_payload(conn, update.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/command-center/history", response_model=list[dict[str, Any]])
def get_command_history(conn = Depends(get_db)) -> list[dict[str, Any]]:
    try:
        return command_history_payload(conn)
    except CommandWeekError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


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
    try:
        return update_tactics_payload(conn, policy.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/command-center/simulate", response_model=CommandCenterSimResponse)
def simulate_command_center_week(update: WeeklyCommandPlanUpdate | None = None, conn = Depends(get_db)) -> CommandCenterSimResponse:
    try:
        return _simulate_week(
            conn,
            update=update.model_dump(exclude_none=True) if update else None,
        )
    except SimulateWeekError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/sim", response_model=SimResponse)
def simulate_command(command: SimCommand, conn = Depends(get_db)) -> SimResponse:
    try:
        return run_simulation_command(conn, command.model_dump())
    except CommandWeekError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/sim/week", response_model=SimResponse)
def simulate_week(conn = Depends(get_db)) -> SimResponse:
    try:
        return run_simulation_command(conn, {"mode": "week"})
    except CommandWeekError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/recruiting/scout/{prospect_id}")
def recruiting_scout(prospect_id: str, conn = Depends(get_db)):
    from dodgeball_sim.recruitment import deduct_recruiting_slot
    season_id = get_state(conn, "active_season_id")
    week = int(get_state(conn, "career_week") or 0)
    try:
        deduct_recruiting_slot(conn, season_id, week, "scout")
        # In a real impl, this would update scouting_state for the prospect
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success"}


@app.post("/api/recruiting/contact/{prospect_id}")
def recruiting_contact(prospect_id: str, conn = Depends(get_db)):
    from dodgeball_sim.recruitment import deduct_recruiting_slot
    season_id = get_state(conn, "active_season_id")
    week = int(get_state(conn, "career_week") or 0)
    try:
        deduct_recruiting_slot(conn, season_id, week, "contact")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success"}


@app.post("/api/recruiting/visit/{prospect_id}")
def recruiting_visit(prospect_id: str, conn = Depends(get_db)):
    from dodgeball_sim.recruitment import deduct_recruiting_slot
    season_id = get_state(conn, "active_season_id")
    week = int(get_state(conn, "career_week") or 0)
    try:
        deduct_recruiting_slot(conn, season_id, week, "visit")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success"}


@app.post("/api/recruiting/pitch-angle")
def recruiting_pitch_angle(request: PitchAngleRequest, conn = Depends(get_db)):
    season_id = get_state(conn, "active_season_id")
    key = f"pitch_angle_locked_{season_id}"
    if get_state(conn, key):
        raise HTTPException(status_code=400, detail="Pitch angle already chosen this season.")
    set_state(conn, key, request.angle)
    conn.commit()
    return {"status": "success"}


@app.post("/api/recruiting/sign/{prospect_id}")
def recruiting_sign(prospect_id: str, conn = Depends(get_db)):
    cursor = load_career_state_cursor(conn)
    if cursor.state.value != "signing_day":
        raise HTTPException(status_code=403, detail="Signing only allowed on Signing Day.")
    return {"status": "success"}


@app.get("/api/matches/{match_id}/replay", response_model=MatchReplayResponse)
def get_match_replay(match_id: str, conn = Depends(get_db)) -> MatchReplayResponse:
    try:
        return match_replay_payload(conn, match_id)
    except ReplayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/matches/{match_id}/acknowledge", response_model=AcknowledgeMatchResponse)
def acknowledge_match_report(match_id: str, conn = Depends(get_db)) -> AcknowledgeMatchResponse:
    try:
        return acknowledge_match_payload(conn, match_id)
    except ReplayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


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
    return SaveListResponse(**list_saves_payload(SAVES_DIR, DEFAULT_DB_PATH, _active_save_path))


@app.post("/api/saves/new")
def api_new_save(req: NewSaveRequest):
    global _active_save_path
    try:
        payload = create_new_save(SAVES_DIR, name=req.name, club_id=req.club_id, root_seed=req.root_seed)
    except SaveServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    _active_save_path = Path(payload["path"])
    return payload


@app.get("/api/saves/starting-prospects")
def api_starting_prospects():
    return starting_prospects_payload()


@app.post("/api/saves/build-from-scratch")
def api_build_from_scratch(req: BuildFromScratchRequest):
    global _active_save_path
    try:
        payload = build_from_scratch_save(SAVES_DIR, req.model_dump())
    except SaveServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    _active_save_path = Path(payload["path"])
    return payload

    SAVES_DIR.mkdir(exist_ok=True)
    safe_name = "".join(c for c in req.save_name if c.isalnum() or c in "-_ ").strip() or "save"
    path = SAVES_DIR / f"{safe_name}.db"
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Save '{safe_name}' already exists.")
    
    from dodgeball_sim.league import Club
    from dodgeball_sim.models import CoachPolicy
    club_id = safe_name.lower().replace(" ", "_")
    custom_club = Club(
        club_id=club_id,
        name=req.club_name,
        colors=req.colors,
        home_region=req.city,
        founded_year=2026,
        tagline=f"{req.city} • {req.coach_name}"
    )

    from dodgeball_sim.recruitment import generate_prospect_pool
    from dodgeball_sim.config import DEFAULT_SCOUTING_CONFIG
    from dodgeball_sim.rng import DeterministicRNG
    rng = DeterministicRNG(12345)
    pool = generate_prospect_pool(2026, rng, DEFAULT_SCOUTING_CONFIG)
    roster_map = {p.player_id: p for p in pool}
    from dodgeball_sim.models import Player, PlayerRatings, PlayerTraits
    custom_roster = []
    for pid in req.roster_player_ids:
        if pid in roster_map:
            prospect = roster_map[pid]
            custom_roster.append(Player(
                id=prospect.player_id,
                name=prospect.name,
                age=prospect.age,
                club_id=club_id,
                newcomer=True,
                ratings=PlayerRatings(
                    accuracy=prospect.hidden_ratings["accuracy"],
                    power=prospect.hidden_ratings["power"],
                    dodge=prospect.hidden_ratings["dodge"],
                    catch=prospect.hidden_ratings["catch"],
                    stamina=prospect.hidden_ratings["stamina"],
                ).apply_bounds(),
                traits=PlayerTraits(
                    potential=min(100.0, max(70.0, max(prospect.hidden_ratings.values()) + 8.0)),
                    growth_curve=50.0,
                    consistency=0.5,
                    pressure=0.5,
                ),
            ))

    if len(custom_roster) < 6:
        raise HTTPException(status_code=400, detail="Must select at least 6 prospects.")

    conn = connect(path)
    try:
        initialize_curated_manager_career(
            conn, 
            club_id, 
            req.root_seed, 
            custom_club=custom_club, 
            custom_roster=custom_roster
        )
        set_state(conn, "coach_backstory", req.coach_backstory)
        conn.commit()
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
    return list_clubs_payload()


_OFFSEASON_STATES = {
    CareerState.SEASON_COMPLETE_OFFSEASON_BEAT,
    CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING,
    CareerState.NEXT_SEASON_READY,
}

_RECRUITMENT_INDEX = OFFSEASON_CEREMONY_BEATS.index("recruitment")
_SCHEDULE_REVEAL_INDEX = OFFSEASON_CEREMONY_BEATS.index("schedule_reveal")


@app.get("/api/offseason/beat")
def get_offseason_beat(conn = Depends(get_db)):
    try:
        return get_offseason_beat_payload(conn)
    except OffseasonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/offseason/advance")
def advance_offseason_beat(conn = Depends(get_db)):
    try:
        return advance_offseason_beat_payload(conn)
    except OffseasonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/offseason/recruit")
def offseason_recruit(conn = Depends(get_db)):
    try:
        return recruit_offseason_payload(conn)
    except OffseasonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/offseason/begin-season")
def offseason_begin_season(conn = Depends(get_db)):
    try:
        return begin_next_season_payload(conn)
    except OffseasonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.get("/api/history/my-program")
def get_history_my_program(club_id: str, conn = Depends(get_db)):
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    current_roster = rosters.get(club_id, [])

    # Hero: first and latest completed season for this club
    all_seasons = conn.execute(
        """
        SELECT season_id, wins, losses, draws, points
        FROM season_standings WHERE club_id = ?
        ORDER BY season_id ASC
        """,
        (club_id,),
    ).fetchall()

    hero: dict = {}
    if all_seasons:
        def _standing_hero(row):
            return {
                "season_label": row["season_id"],
                "wins": row["wins"],
                "losses": row["losses"],
                "draws": row["draws"],
            }

        trophies = load_club_trophies(conn)
        champ_count = sum(
            1 for t in trophies
            if t["club_id"] == club_id and t["trophy_type"] == "championship"
        )
        avg_ovr = (
            round(sum(p.overall() for p in current_roster) / len(current_roster), 1)
            if current_roster else 0
        )
        hero["season_1"] = _standing_hero(all_seasons[0])
        current = _standing_hero(all_seasons[-1])
        current["avg_ovr"] = avg_ovr
        current["championships"] = champ_count
        hero["current"] = current

    # Timeline events
    timeline = []

    # First win
    first_win = conn.execute(
        """
        SELECT season_id, week FROM match_records
        WHERE winner_club_id = ?
        ORDER BY season_id ASC, week ASC
        LIMIT 1
        """,
        (club_id,),
    ).fetchone()
    if first_win:
        timeline.append({
            "season": first_win["season_id"],
            "week": first_win["week"],
            "event_type": "standard",
            "label": "First Win",
            "weight": "standard",
        })

    # Championships
    for t in load_club_trophies(conn):
        if t["club_id"] == club_id and t["trophy_type"] == "championship":
            timeline.append({
                "season": t["season_id"],
                "week": None,
                "event_type": "championship",
                "label": "Champions",
                "weight": "championship",
            })

    # Awards won by this club's players
    award_rows = conn.execute(
        "SELECT season_id, award_type, player_id FROM season_awards WHERE club_id = ?",
        (club_id,),
    ).fetchall()
    for row in award_rows:
        label_map = {
            "mvp": "MVP Award",
            "top_rookie": "Top Rookie",
            "best_defender": "Best Defender",
            "most_improved": "Most Improved",
            "championship": "Championship Award",
        }
        timeline.append({
            "season": row["season_id"],
            "week": None,
            "event_type": "award",
            "label": label_map.get(row["award_type"], row["award_type"]),
            "weight": "award",
        })

    current_ids = {p.id for p in current_roster}
    retired_rows = load_retired_players(conn)

    # Build last_club_map: player_id -> last club_id they played for
    last_club_rows = conn.execute(
        """
        SELECT ps.player_id, ps.club_id
        FROM player_season_stats ps
        INNER JOIN (
            SELECT player_id, MAX(season_id) AS max_season
            FROM player_season_stats
            GROUP BY player_id
        ) latest ON ps.player_id = latest.player_id AND ps.season_id = latest.max_season
        """
    ).fetchall()
    last_club_map = {row["player_id"]: row["club_id"] for row in last_club_rows}

    # Hall of Fame inductees from this club
    for entry in conn.execute(
        "SELECT player_id, induction_season FROM hall_of_fame ORDER BY induction_season"
    ).fetchall():
        if last_club_map.get(entry["player_id"]) == club_id or entry["player_id"] in current_ids:
            # find player name
            player_name = entry["player_id"]
            for r in retired_rows:
                if r["player_id"] == entry["player_id"] and r.get("player"):
                    player_name = r["player"].name
                    break
            for p in current_roster:
                if p.id == entry["player_id"]:
                    player_name = p.name
                    break
            timeline.append({
                "season": entry["induction_season"],
                "week": None,
                "event_type": "hof",
                "label": f"HoF: {player_name}",
                "weight": "hof",
            })

    # Records set by players from this club
    for rec in conn.execute(
        "SELECT record_type, holder_id, record_value, set_in_season FROM league_records"
    ).fetchall():
        if last_club_map.get(rec["holder_id"]) == club_id or rec["holder_id"] in current_ids:
            timeline.append({
                "season": rec["set_in_season"],
                "week": None,
                "event_type": "record",
                "label": f"Record: {rec['record_type']}",
                "weight": "record",
            })

    # Sort timeline by season then week (None last in week)
    timeline.sort(key=lambda e: (e["season"], e["week"] or 999))

    # Alumni (retired players whose last known club was this one)
    alumni = []
    for r in retired_rows:
        if last_club_map.get(r["player_id"]) != club_id:
            continue
        p = r.get("player")
        if p is None:
            continue
        career = load_player_career_stats(conn, r["player_id"])
        alumni.append({
            "id": r["player_id"],
            "name": p.name,
            "seasons_played": int((career or {}).get("seasons_played", 0)),
            "career_elims": int((career or {}).get("total_eliminations", 0)),
            "championships": int((career or {}).get("championships", 0)),
            "ovr_final": float(r.get("overall", round(p.overall(), 1))),
            "potential_tier": calculate_potential_tier(p.traits.potential),
        })

    # Banners
    banners = []
    for t in load_club_trophies(conn):
        if t["club_id"] != club_id:
            continue
        if t["trophy_type"] == "championship":
            banners.append({
                "type": "championship",
                "season": t["season_id"],
                "label": "Champions",
            })
    for row in award_rows:
        label_map = {
            "mvp": "MVP Award",
            "top_rookie": "Top Rookie",
            "best_defender": "Best Defender",
            "most_improved": "Most Improved",
        }
        if row["award_type"] in label_map:
            banners.append({
                "type": "award",
                "season": row["season_id"],
                "label": label_map[row["award_type"]],
            })
    banners.sort(key=lambda b: b["season"])

    return {
        "club_id": club_id,
        "hero": hero,
        "timeline": timeline,
        "alumni": alumni,
        "banners": banners,
    }


@app.get("/api/history/league")
def get_history_league(conn = Depends(get_db)):
    clubs = load_clubs(conn)

    # Directory
    directory = [{"club_id": c.club_id, "name": c.name} for c in clubs.values()]

    # Dynasty rankings: championship count + longest win streak per club
    all_trophies = load_club_trophies(conn)
    trophy_counts: dict = {}
    for t in all_trophies:
        if t["trophy_type"] == "championship":
            trophy_counts[t["club_id"]] = trophy_counts.get(t["club_id"], 0) + 1

    # Longest win streak per club from match_records
    streak_map: dict = {}
    for c_id in clubs:
        rows = conn.execute(
            """
            SELECT winner_club_id FROM match_records
            WHERE home_club_id = ? OR away_club_id = ?
            ORDER BY season_id, week
            """,
            (c_id, c_id),
        ).fetchall()
        best = cur = 0
        for row in rows:
            if row["winner_club_id"] == c_id:
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        streak_map[c_id] = best

    dynasty_rankings = sorted(
        [
            {
                "club_id": c_id,
                "club_name": clubs[c_id].name,
                "championships": trophy_counts.get(c_id, 0),
                "longest_win_streak": streak_map.get(c_id, 0),
            }
            for c_id in clubs
        ],
        key=lambda r: (-r["championships"], -r["longest_win_streak"], r["club_name"]),
    )

    # Hall of Fame
    hof = []
    for entry in load_hall_of_fame(conn):
        cs = entry.get("career_summary") or {}
        player_name = cs.get("player_name", entry["player_id"])
        hof.append({
            "player_id": entry["player_id"],
            "player_name": player_name,
            "induction_season": entry["induction_season"],
            "career_elims": int(cs.get("total_eliminations", 0)),
            "championships": int(cs.get("championships", 0)),
            "seasons_played": int(cs.get("seasons_played", 0)),
        })

    # Rivalries
    rivalries = []
    for r in load_rivalry_records(conn):
        rv = r.get("rivalry") or {}
        a_id = r["club_a_id"]
        b_id = r["club_b_id"]
        a_wins = int(rv.get("a_wins", 0))
        b_wins = int(rv.get("b_wins", 0))
        draws = int(rv.get("draws", 0))
        rivalries.append({
            "club_a": clubs[a_id].name if a_id in clubs else a_id,
            "club_b": clubs[b_id].name if b_id in clubs else b_id,
            "a_wins": a_wins,
            "b_wins": b_wins,
            "draws": draws,
            "meetings": a_wins + b_wins + draws,
        })
    rivalries.sort(key=lambda r: -r["meetings"])

    return {
        "directory": directory,
        "dynasty_rankings": dynasty_rankings,
        "records": load_league_records(conn),
        "hof": hof,
        "rivalries": rivalries,
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
