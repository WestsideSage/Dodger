from pathlib import Path
import dataclasses
import json
import math
import mimetypes
import re
import secrets
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

from dodgeball_sim.persistence import (
    connect, load_career_state_cursor, get_state, load_club_roster,
    load_clubs, save_club, load_season, load_completed_match_ids,
    save_career_state_cursor, load_all_rosters, load_standings, load_awards,
    load_lineup_default,
    load_json_state,
    save_match_lineup_override,
    fetch_roster_snapshot,
    fetch_match,
    CorruptSaveError,
    repair_legacy_name_pool,
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
    season_sort_key,
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
from dodgeball_sim.use_cases import (
    SimulateWeekError,
    auto_pilot_weeks as _auto_pilot_weeks,
    resolve_fast_forward_cap as _resolve_fast_forward_cap,
    simulate_week as _simulate_week,
)
from dodgeball_sim.command_week_service import (
    CommandWeekError,
    command_center_payload,
    command_history_payload,
    mark_lineup_confirmed,
    mark_opponent_scouted,
    run_simulation_command,
    save_command_center_plan_payload,
    set_season_preview_skipped,
)
from dodgeball_sim.web_status_service import (
    build_news_payload,
    build_playoff_bracket_payload,
    build_roster_payload,
    build_schedule_payload,
    build_standings_payload,
    build_status_payload,
    build_tactics_payload,
    update_manual_lineup_payload,
    update_tactics_payload,
)
from dodgeball_sim.replay_service import (
    ReplayError,
    acknowledge_match_payload,
    match_replay_payload,
)
from dodgeball_sim.highlights import build_highlight_package
from dodgeball_sim.voice_register import for_tier
from dodgeball_sim.offseason_service import (
    OffseasonError,
    advance_offseason_beat_payload,
    begin_next_season_payload,
    get_offseason_beat_payload,
    media_choice_payload,
    recruit_offseason_payload,
    transfer_action_payload,
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

# ---------------------------------------------------------------------------
# WT-12: per-process launch token (CSRF defense for the local server)
#
# While the local server is running, a malicious page open in the same browser
# could issue a cross-origin form/fetch POST to localhost and mutate the active
# career (simulate / fast-forward / unload). We mint a random token once per
# process and require it as a header on every mutating /api request. The token
# is served INTO the page (a <meta> tag in index.html) and is also fetchable at
# GET /api/launch-token; the first-party SPA reads it and attaches it. A
# cross-origin drive-by cannot read the page or that response body (same-origin
# policy, and there is no CORS allowance on this app), so it cannot forge the
# header. No user action is required — the token rides the launcher.
#
# Enforcement is ON by the module default, so the live server is protected
# however it is launched (including the uvicorn --reload worker, which re-imports
# this module fresh and so picks up the default — no launcher wiring or env var
# needed). The pytest suite, which posts to mutating routes without a token, is
# the only context that disables it: a single autouse fixture in tests/conftest.py
# (a pytest-only mechanism, never loaded at app runtime) turns it OFF per test.
# The dedicated WT-12 test flips it back ON inside its own body to exercise both
# the 403 (missing/forged) and the allowed (valid) paths.
LAUNCH_TOKEN_HEADER = "X-Dodgeball-Launch-Token"
LAUNCH_TOKEN: str = secrets.token_urlsafe(32)
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_enforce_launch_token = True


def enable_launch_token_guard(enabled: bool = True) -> None:
    """Toggle launch-token enforcement.

    The module default is ON (production is protected on import). This exists so
    the test suite / conftest can disable it and the WT-12 test can re-enable it
    within a single test, without reaching into the private module global.
    """
    global _enforce_launch_token
    _enforce_launch_token = enabled


@app.middleware("http")
async def _launch_token_guard(request: Request, call_next):
    if (
        _enforce_launch_token
        and request.method in _MUTATING_METHODS
        and request.url.path.startswith("/api/")
    ):
        presented = request.headers.get(LAUNCH_TOKEN_HEADER, "")
        if not secrets.compare_digest(presented, LAUNCH_TOKEN):
            return JSONResponse(
                status_code=403,
                content={"detail": "Missing or invalid launch token."},
            )
    return await call_next(request)


def _inject_launch_token(response: Response) -> Response:
    """Rewrite a served index.html so the SPA can read the token synchronously.

    Falls back to fetching GET /api/launch-token at runtime when the meta tag
    is absent (e.g. the vite dev server serves the un-rewritten source file).
    """
    path = getattr(response, "path", None)
    if path is None:
        return response
    try:
        html = Path(path).read_text(encoding="utf-8")
    except OSError:
        return response
    meta = f'<meta name="launch-token" content="{LAUNCH_TOKEN}" />'
    if 'name="launch-token"' not in html:
        if "</head>" in html:
            html = html.replace("</head>", f"    {meta}\n  </head>", 1)
        else:
            html = meta + html
    return HTMLResponse(content=html, status_code=response.status_code)


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
        repair_legacy_name_pool(conn)
        yield conn
    finally:
        conn.close()


def _read_save_meta(path: Path) -> dict:
    return read_save_meta(path)

# --- Pydantic Models ---

class CoachPolicyUpdate(BaseModel):
    approach: str
    target_focus: str
    catch_posture: str
    rush_commit: str
    rush_target: str


class SimCommand(BaseModel):
    mode: str = "week"
    weeks: int = 1
    milestone: str | None = None


class WeeklyCommandPlanUpdate(BaseModel):
    intent: str | None = None
    department_orders: dict[str, str] | None = None
    tactics: dict[str, Any] | None = None
    lineup_player_ids: list[str] | None = None


class OffseasonRecruitRequest(BaseModel):
    prospect_id: str | None = None
    # Playtest 3 F-8 sign-over-cut: at a full roster, the player named here is
    # released to free agency when (and only when) the contested pick lands.
    release_player_id: str | None = None


class OffseasonTransferRequest(BaseModel):
    # V25 Transfer Period: action is one of resign | release | accept_buyout |
    # refuse_buyout; offer_k optionally raises a re-sign offer to fight a poacher.
    action: str
    player_id: str
    offer_k: int | None = None


class FacilityUpgradeRequest(BaseModel):
    # V26: the facility_type to build (treasury sink).
    facility_type: str


class BenchRoleRequest(BaseModel):
    # V26: assign (or clear, role=None/"none") a bench role to a non-starter.
    player_id: str
    role: str | None = None


class MediaChoiceRequest(BaseModel):
    # V26: the chosen Media Moment option key.
    option_key: str


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
    ruleset_selection: str | None = None  # V11: surfaces the official ruleset


class StatusResponse(BaseModel):
    status: str
    state: CareerStateResponse
    context: StatusContextResponse


class RosterResponse(BaseModel):
    club_id: str
    roster: list[Any]
    default_lineup: list[str] | None
    # Declared explicitly: a FastAPI response_model FILTERS undeclared keys,
    # so payload fields the frontend reads must appear here.
    lineup_auto_reorder: bool | None = None
    # Playtest 3 F-8: ids carrying an OPEN promise, so the release control can
    # warn that cutting them breaks your word.
    open_promise_player_ids: list[str] = []


class RosterReleaseRequest(BaseModel):
    player_id: str


class RosterReleaseResponse(RosterResponse):
    release_outcome: dict[str, Any]


class TacticsResponse(BaseModel):
    approach: str
    target_focus: str
    catch_posture: str
    rush_commit: str
    rush_target: str


class StandingItem(BaseModel):
    club_id: str
    club_name: str
    wins: int
    losses: int
    draws: int
    points: int
    elimination_differential: int
    # V20 §7.3: the differential that actually ranks official careers.
    # Declared or FastAPI strips them (WT-2/WT-3 bug family).
    game_point_differential: int = 0
    total_game_points_scored: int = 0
    is_user_club: bool
    latest_approach: str | None = None
    program_archetype: str | None = None
    program_trajectory_label: str | None = None


class StandingsResponse(BaseModel):
    season_id: str
    standings: list[StandingItem]
    recent_matches: list[dict[str, Any]] | None = None
    total_weeks: int = 0
    current_week: int = 0
    user_games_remaining: int = 0
    is_offseason: bool = False
    playoff_spots: int = 4
    # V20 §7.3: tells the standings UI which differential ranks this career.
    is_official_career: bool = False
    # V23: the player's division + the full pyramid. None on legacy
    # single-league saves. Declared or FastAPI strips them (WT-2/WT-3 family).
    division: dict[str, Any] | None = None
    divisions: list[dict[str, Any]] | None = None
    # V28: the league news wire (class_wire / event_news / meta_report /
    # league_bulletin) for the League Wire ticker. Declared or FastAPI strips it.
    wire_headlines: list[dict[str, Any]] | None = None


class ScheduleItem(BaseModel):
    match_id: str
    week: int
    home_club_id: str
    home_club_name: str
    away_club_id: str
    away_club_name: str
    status: str
    is_user_match: bool
    stage: str = "Regular Season"


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
    incompatible: bool = False
    last_modified: float = 0.0
    season_number: int = 1
    wins: int = 0
    losses: int = 0
    draws: int = 0


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
    # WT-17: new careers default to the official foam ruleset at the backend
    # boundary, matching the frontend default, so an API/automation-created
    # career no longer silently goes generic when the field is omitted. An
    # explicit "generic" (or None) is still honored for legacy/opt-out callers.
    ruleset_selection: str | None = "official_foam"


class BuildFromScratchRequest(BaseModel):
    save_name: str
    club_name: str
    city: str
    colors: str
    coach_name: str
    coach_backstory: str
    roster_player_ids: list[str]
    # V22 Phase 3: the wizard's founding staff picks — department -> the
    # candidate_id chosen from GET /api/saves/starting-staff for the same
    # seed. None keeps the default six (legacy callers).
    staff_choices: dict[str, str] | None = None
    root_seed: int = 20260426
    # WT-17: build-from-scratch careers also default to official foam at the
    # backend boundary (see NewSaveRequest). Explicit "generic"/None still
    # honored for legacy/opt-out callers.
    ruleset_selection: str | None = "official_foam"


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
    config_version: str | None = None  # V11: "official:..." when run under official ruleset
    # WT-2/WT-3 family: the replay scoreboard must score official matches in
    # game points, exactly like the aftermath hero. replay_service builds
    # these fields; omitting them here made FastAPI strip them from the
    # serialized response, so every official replay silently rendered as a
    # legacy survivor scoreline and could contradict the aftermath.
    scoring_model: str = "legacy"
    home_game_points: int = 0
    away_game_points: int = 0
    home_games_won: int = 0
    away_games_won: int = 0
    tied_games: int = 0
    no_point_games: int = 0
    events: list[dict[str, Any]]
    moment_events: list[dict[str, Any]] = Field(default_factory=list)
    proof_events: list[dict[str, Any]] = Field(default_factory=list)
    key_play_indices: list[int] = Field(default_factory=list)
    # Per-game story of an official match (set results, running points, proof
    # index ranges). None for legacy/rec matches. Must be declared here or
    # FastAPI strips it from the serialized response (WT-2/WT-3 bug family).
    game_segments: list[dict[str, Any]] | None = None
    report: dict[str, Any]
    # V20 intent context: the locked match policies both clubs played under
    # (club_id -> CoachPolicy dict). None for legacy/rec matches. Declared so
    # FastAPI does not strip it (WT-2/WT-3 bug family).
    team_policies: dict[str, dict[str, Any]] | None = None
    official_state: dict[str, Any] | None = None
    broadcast_frame: dict[str, Any] | None = None
    playoff_frame: dict[str, Any] | None = None
    commentary_inserts: list[dict[str, Any]] = Field(default_factory=list)


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
    season_preview: dict[str, Any] | None = None
    # Declared here so FastAPI does not strip it at the serialization layer
    # (the MatchReplayResponse field-stripping bug, 2026-06-09). Lets the
    # Policy Editor disclose announced-only knobs on official careers (WT-20).
    ruleset_selection: str | None = None


class SeasonPreviewSkipRequest(BaseModel):
    skipped: bool = True


class CommandCenterSimResponse(BaseModel):
    status: str
    message: str
    plan: dict[str, Any]
    dashboard: dict[str, Any]
    next_state: str | None = None
    aftermath: dict[str, Any] | None = None


class FastForwardRequest(BaseModel):
    max_weeks: int | None = None
    # WT-29: the player-chosen stop point ('next_bye' | 'pre_playoffs' |
    # 'offseason'). When supplied it is mapped server-side to a max_weeks cap and
    # takes precedence over an explicit max_weeks. Absent/None preserves the
    # legacy "run to the end" behaviour.
    stop_point: str | None = None


class FastForwardResponse(BaseModel):
    status: str
    message: str
    weeks_simulated: int
    stop_reason: str
    next_state: str | None = None
    week_summaries: list[dict[str, Any]]
    final_dashboard: dict[str, Any] | None = None
    final_aftermath: dict[str, Any] | None = None
    # WT-29: echo what the player asked for and what it resolved to (e.g. a
    # requested "next_bye" with no bye left resolves to "pre_playoffs"), so the
    # UI can confirm honestly what was skipped.
    requested_stop_point: str | None = None
    resolved_stop_point: str | None = None


class RecruitingPromiseRequest(BaseModel):
    player_id: str
    promise_type: str


class StaffHireRequest(BaseModel):
    candidate_id: str


class PitchAngleRequest(BaseModel):
    angle: str

# --- API Endpoints ---

@app.get("/api/launch-token")
def api_launch_token() -> dict[str, str]:
    """WT-12: expose the per-process launch token to the first-party SPA.

    This is a non-mutating GET, so the token guard never blocks it. It is safe
    to serve because a cross-origin page cannot read the response body (no CORS
    allowance on this app); only same-origin first-party code can consume it.
    """
    return {"token": LAUNCH_TOKEN}


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


@app.post("/api/roster/release", response_model=RosterReleaseResponse)
def post_roster_release(
    request: RosterReleaseRequest, conn = Depends(get_db)
) -> RosterReleaseResponse:
    """Playtest 3 F-8: release a contracted player to free agency."""
    from .roster_moves import RosterMoveError, release_player_to_free_agency

    try:
        outcome = release_player_to_free_agency(conn, request.player_id)
        return {**build_roster_payload(conn), "release_outcome": outcome}
    except RosterMoveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
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


@app.get("/api/playoffs/bracket", response_model=dict[str, Any])
def get_playoff_bracket(conn = Depends(get_db)) -> dict[str, Any]:
    try:
        return build_playoff_bracket_payload(conn)
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


@app.post("/api/command-center/scout", response_model=CommandCenterResponse)
def scout_opponent(conn = Depends(get_db)) -> CommandCenterResponse:
    """Clear the scout-opponent readiness gate (D3)."""
    try:
        return mark_opponent_scouted(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/command-center/confirm-lineup", response_model=CommandCenterResponse)
def confirm_lineup(conn = Depends(get_db)) -> CommandCenterResponse:
    """Clear the confirm-lineup readiness gate (D3)."""
    try:
        return mark_lineup_confirmed(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/command-center/season-preview/skip", response_model=CommandCenterResponse)
def skip_season_preview(request: SeasonPreviewSkipRequest, conn = Depends(get_db)) -> CommandCenterResponse:
    try:
        return set_season_preview_skipped(conn, request.skipped)
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
def update_tactics(policy: dict[str, Any], conn = Depends(get_db)) -> dict[str, str]:
    try:
        return update_tactics_payload(conn, policy)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/lineup", response_model=dict[str, Any])
def update_lineup(payload: dict[str, Any], conn = Depends(get_db)) -> dict[str, Any]:
    """Persist a manual lineup override (or clear it).

    Body:
      ``{"starter_ids": [...]}`` to set, ``{"starter_ids": null}`` to clear.
    Returns 400 with the ``LineupViolation.reason`` tag as ``detail`` when
    the submission fails structural validation, so the frontend can branch
    on a stable string.
    """
    from dodgeball_sim.lineup import LineupViolation

    starter_ids = payload.get("starter_ids", None)
    if starter_ids is not None and not isinstance(starter_ids, list):
        raise HTTPException(status_code=400, detail="starter_ids must be a list or null")
    try:
        return update_manual_lineup_payload(conn, starter_ids)
    except LineupViolation as exc:
        raise HTTPException(status_code=400, detail=exc.reason) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/lineup/auto-reorder", response_model=dict[str, Any])
def set_lineup_auto_reorder(payload: dict[str, Any], conn = Depends(get_db)) -> dict[str, Any]:
    """V19 Task 8: the set-and-forget switch (CFB26 depth-chart pattern).

    Body: ``{"enabled": true|false}``. ON = the offseason re-seats the
    fielded six automatically; OFF = hands-on (the offseason only repairs
    retirements, never re-ranks a chosen seat). A manual ``/api/lineup``
    save flips it OFF implicitly.
    """
    from dodgeball_sim.web_status_service import set_lineup_auto_reorder_payload

    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=400, detail="enabled must be a boolean")
    return set_lineup_auto_reorder_payload(conn, enabled)


@app.post("/api/lineup/auto-assign", response_model=dict[str, Any])
def auto_assign_lineup(conn = Depends(get_db)) -> dict[str, Any]:
    """V19 Task 8: one-shot Auto-assign — seat the optimal six right now.

    A manual tool: it does not change the auto-reorder toggle.
    """
    from dodgeball_sim.web_status_service import auto_assign_lineup_payload

    try:
        return auto_assign_lineup_payload(conn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/command-center/simulate", response_model=CommandCenterSimResponse)
def simulate_command_center_week(update: WeeklyCommandPlanUpdate | None = None, conn = Depends(get_db)) -> CommandCenterSimResponse:
    from dodgeball_sim.lineup import LineupViolation

    try:
        return _simulate_week(
            conn,
            update=update.model_dump(exclude_none=True) if update else None,
        )
    except LineupViolation as exc:
        # WT-10: an invalid inline lineup override (non-roster / duplicate /
        # wrong-count ids) must reject with 400 and persist nothing, mirroring
        # the /api/lineup precedent — not surface as an uncaught 500.
        raise HTTPException(status_code=400, detail=exc.reason) from exc
    except SimulateWeekError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/command-center/fast-forward", response_model=FastForwardResponse)
def fast_forward_command_center(
    request: FastForwardRequest | None = None, conn = Depends(get_db)
) -> FastForwardResponse:
    """Auto-pilot toward a player-chosen stop point using the persisted weekly
    plan and canonical fielded-6. Additive convenience over the per-week
    ``/api/command-center/simulate`` path.

    WT-29: when ``stop_point`` is supplied it is mapped server-side (from the
    schedule the player can already see) to a ``max_weeks`` cap and wins over an
    explicit ``max_weeks``. The response echoes the requested and resolved stop
    points so the UI can disclose exactly what was auto-decided."""
    requested_stop_point = request.stop_point if request else None
    try:
        if requested_stop_point is not None:
            cap, resolved_stop_point = _resolve_fast_forward_cap(conn, requested_stop_point)
        else:
            cap = request.max_weeks if request else None
            resolved_stop_point = None
        result = _auto_pilot_weeks(conn, max_weeks=cap)
        result["requested_stop_point"] = requested_stop_point
        result["resolved_stop_point"] = resolved_stop_point
        return result
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


def _run_recruiting_action(conn, prospect_id: str, action: str) -> dict[str, Any]:
    """Deduct a slot, apply the action, and return the visible before/after delta."""
    from dodgeball_sim.recruitment import deduct_recruiting_slot, staff_focus_for_week
    from dodgeball_sim.recruiting_office import apply_recruiting_action
    from dodgeball_sim.persistence import load_command_history_all_seasons
    from dodgeball_sim.staff_effects import culture_focus_interest_multiplier

    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    week = load_career_state_cursor(conn).week
    # V19b: a "culture" staff focus week makes courtship land warmer.
    # V22 Phase 4: HOW MUCH warmer scales with the culture head running it
    # (×1.15–×1.40; the old flat 1.25 ≈ the default head's 68 rating).
    culture_week = staff_focus_for_week(conn, season_id, week) == "culture"
    culture_multiplier = 1.0
    if culture_week:
        from dodgeball_sim.persistence import load_department_heads

        culture_head = next(
            (h for h in load_department_heads(conn) if h["department"] == "culture"),
            None,
        )
        culture_multiplier = culture_focus_interest_multiplier(
            culture_head["rating_primary"] if culture_head else 50.0
        )
    try:
        deduct_recruiting_slot(conn, season_id, week, action)
        delta = apply_recruiting_action(
            conn,
            prospect_id=prospect_id,
            action=action,  # type: ignore[arg-type]
            season_id=season_id,
            player_club_id=player_club_id or "",
            root_seed=stored_root_seed(conn),
            history=load_command_history_all_seasons(conn),
            interest_gain_multiplier=culture_multiplier,
        )
        conn.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success", "result": delta}


@app.post("/api/recruiting/scout/{prospect_id}")
def recruiting_scout(prospect_id: str, conn = Depends(get_db)):
    return _run_recruiting_action(conn, prospect_id, "scout")


@app.post("/api/recruiting/contact/{prospect_id}")
def recruiting_contact(prospect_id: str, conn = Depends(get_db)):
    return _run_recruiting_action(conn, prospect_id, "contact")


@app.post("/api/recruiting/visit/{prospect_id}")
def recruiting_visit(prospect_id: str, conn = Depends(get_db)):
    return _run_recruiting_action(conn, prospect_id, "visit")


@app.post("/api/recruiting/focus/{prospect_id}")
def recruiting_focus(prospect_id: str, conn = Depends(get_db)):
    """V24: toggle a prospect on/off the persistent focus list (shortlist). Once
    focused you can Contact him; your top focus targets unlock Visit."""
    from dodgeball_sim.recruiting_office import toggle_focus

    focused = toggle_focus(conn, prospect_id)
    conn.commit()
    return {"status": "success", "focused": focused}


@app.post("/api/recruiting/network/upgrade")
def recruiting_network_upgrade(conn = Depends(get_db)):
    """V24 Phase 6: spend treasury to raise the Scouting Network one level,
    widening which prospects render a full sheet (the money-gated reach)."""
    from dodgeball_sim.recruiting_office import upgrade_scouting_network

    try:
        result = upgrade_scouting_network(conn)
        conn.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success", "network": result}


@app.post("/api/dynasty-office/facilities/upgrade")
def dynasty_office_facilities_upgrade(request: FacilityUpgradeRequest, conn = Depends(get_db)):
    """V26 The Crowd: spend treasury to build a facility permanently."""
    from dodgeball_sim.facilities_office import buy_facility

    try:
        result = buy_facility(conn, request.facility_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success", "facilities": result}


@app.post("/api/dynasty-office/bench-role")
def dynasty_office_bench_role(request: BenchRoleRequest, conn = Depends(get_db)):
    """V26 The Crowd: assign a bench role (mentor / analyst / ambassador) to a
    non-starter, or clear it."""
    from dodgeball_sim.bench_roles import assign_role

    try:
        roles = assign_role(conn, request.player_id, request.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success", "bench_roles": roles}


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


@app.get("/api/matches/{match_id}/highlights", response_model=dict[str, Any])
def get_match_highlights(match_id: str, conn = Depends(get_db)) -> dict[str, Any]:
    try:
        replay = match_replay_payload(conn, match_id)
    except ReplayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    beats = build_highlight_package(
        events=replay["events"],
        proof_events=replay["proof_events"],
        moment_events=replay["moment_events"],
        name_map={},
    )
    return {
        "match_id": match_id,
        "beats": [beat.to_dict() for beat in beats],
    }


@app.post("/api/matches/{match_id}/acknowledge", response_model=AcknowledgeMatchResponse)
def acknowledge_match_report(match_id: str, conn = Depends(get_db)) -> AcknowledgeMatchResponse:
    try:
        return acknowledge_match_payload(conn, match_id)
    except ReplayError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.get("/api/voice-register/{tier}")
def get_voice_register(tier: int) -> dict[str, str]:
    try:
        return for_tier(tier)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        payload = create_new_save(
            SAVES_DIR,
            name=req.name, club_id=req.club_id, root_seed=req.root_seed,
            ruleset_selection=req.ruleset_selection,
        )
    except SaveServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    _active_save_path = Path(payload["path"])
    return payload


@app.get("/api/saves/starting-prospects")
def api_starting_prospects(seed: int | None = None):
    # V22 Phase 1: the wizard passes its per-creation seed so the list shown
    # here is exactly the pool the build POST (root_seed) will draft from.
    return starting_prospects_payload(seed)


@app.get("/api/saves/starting-staff")
def api_starting_staff(seed: int | None = None):
    # V22 Phase 3: the founding staff market — same creation seed as the
    # prospect list, so the build POST validates against the exact pool shown.
    from .save_service import starting_staff_payload

    return starting_staff_payload(seed)


@app.post("/api/saves/build-from-scratch")
def api_build_from_scratch(req: BuildFromScratchRequest):
    global _active_save_path
    try:
        payload = build_from_scratch_save(SAVES_DIR, req.model_dump())
    except SaveServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    _active_save_path = Path(payload["path"])
    return payload


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
    meta = read_save_meta(resolved)
    if meta.get("incompatible"):
        raise HTTPException(
            status_code=422,
            detail="Save predates Plan B player ratings. Please start a new game.",
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
def offseason_recruit(request: OffseasonRecruitRequest | None = None, conn = Depends(get_db)):
    try:
        return recruit_offseason_payload(
            conn,
            request.prospect_id if request else None,
            release_player_id=request.release_player_id if request else None,
        )
    except OffseasonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/offseason/transfer")
def offseason_transfer(request: OffseasonTransferRequest, conn = Depends(get_db)):
    try:
        return transfer_action_payload(
            conn, request.action, request.player_id, request.offer_k
        )
    except OffseasonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/offseason/media")
def offseason_media(request: MediaChoiceRequest, conn = Depends(get_db)):
    try:
        return media_choice_payload(conn, request.option_key)
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

    # Hero: first and latest completed season for this club. season_id is a
    # string ("season_10" < "season_2"), so order numerically in Python.
    all_seasons = conn.execute(
        """
        SELECT season_id, wins, losses, draws, points
        FROM season_standings WHERE club_id = ?
        """,
        (club_id,),
    ).fetchall()
    all_seasons = sorted(all_seasons, key=lambda row: season_sort_key(row["season_id"]))

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
            round(sum(p.overall_skill() for p in current_roster) / len(current_roster))
            if current_roster else 0
        )
        hero["season_1"] = _standing_hero(all_seasons[0])
        current = _standing_hero(all_seasons[-1])
        current["avg_ovr"] = avg_ovr
        current["championships"] = champ_count
        hero["current"] = current
        # The history glance "All-Time Record" sums COMPLETED seasons only
        # (owner decision §6.7, 2026-06-10): a season is completed when its
        # outcome is ratified, so the cell never mixes a half-played season
        # into a career total. With zero completed seasons the cell falls
        # back to the latest-season record (the frontend's honest fallback).
        completed_ids = {
            row["season_id"]
            for row in conn.execute("SELECT season_id FROM season_outcomes").fetchall()
        }
        completed_rows = [row for row in all_seasons if row["season_id"] in completed_ids]
        if completed_rows:
            hero["all_time"] = {
                "wins": sum(int(row["wins"]) for row in completed_rows),
                "losses": sum(int(row["losses"]) for row in completed_rows),
                "draws": sum(int(row["draws"]) for row in completed_rows),
                "seasons": len(completed_rows),
            }

    # Timeline events
    timeline = []

    # First win (numerically earliest season, then week — not string order)
    win_rows = conn.execute(
        """
        SELECT season_id, week FROM match_records
        WHERE winner_club_id = ?
        """,
        (club_id,),
    ).fetchall()
    first_win = (
        min(win_rows, key=lambda row: (season_sort_key(row["season_id"]), row["week"]))
        if win_rows
        else None
    )
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
    current_ids = {p.id for p in current_roster}
    retired_rows = load_retired_players(conn)

    award_rows = conn.execute(
        "SELECT season_id, award_type, player_id, club_id, award_score FROM season_awards WHERE club_id = ?",
        (club_id,),
    ).fetchall()

    def _player_display_name(player_id: str) -> str | None:
        for p in current_roster:
            if p.id == player_id:
                return p.name
        for r in retired_rows:
            if r["player_id"] == player_id and r.get("player"):
                return r["player"].name
        return None

    def _award_proof_stat(player_id: str, season_id: str, award_type: str) -> str | None:
        row = conn.execute(
            """
            SELECT total_eliminations, total_catches_made, matches
            FROM player_season_stats
            WHERE player_id = ? AND season_id = ?
            """,
            (player_id, season_id),
        ).fetchone()
        if row is None:
            return None
        elims = row["total_eliminations"]
        catches = row["total_catches_made"]
        games = row["matches"]
        if award_type in ("best_newcomer", "mvp", "best_thrower"):
            return f"{elims} elims across {games} match{'es' if games != 1 else ''} that season."
        if award_type == "best_catcher":
            return f"{catches} catches across {games} match{'es' if games != 1 else ''} that season."
        return f"{elims} elims across {games} match{'es' if games != 1 else ''} that season."

    award_label_map = {
        "mvp": "MVP Award",
        "best_thrower": "Best Thrower",
        "best_catcher": "Best Catcher",
        "best_newcomer": "Best Newcomer",
    }

    for row in award_rows:
        holder_name = _player_display_name(row["player_id"])
        proof_stat = _award_proof_stat(row["player_id"], row["season_id"], row["award_type"])
        timeline.append({
            "season": row["season_id"],
            "week": None,
            "event_type": "award",
            "label": award_label_map.get(row["award_type"], row["award_type"]),
            "weight": "award",
            "holder_name": holder_name,
            "proof_stat": proof_stat,
        })

    # Build last_club_map: player_id -> last club_id they played for.
    # SQL MAX(season_id) is a string max (season_9 > season_10), so pick the
    # numerically latest season per player in Python.
    last_club_map: dict[str, str] = {}
    last_club_season: dict[str, tuple] = {}
    for row in conn.execute(
        "SELECT player_id, club_id, season_id FROM player_season_stats"
    ).fetchall():
        key = season_sort_key(row["season_id"])
        if row["player_id"] not in last_club_season or key > last_club_season[row["player_id"]]:
            last_club_season[row["player_id"]] = key
            last_club_map[row["player_id"]] = row["club_id"]

    # Hall of Fame inductees from this club (numeric season order)
    hof_entries = conn.execute(
        "SELECT player_id, induction_season FROM hall_of_fame"
    ).fetchall()
    for entry in sorted(
        hof_entries, key=lambda e: (season_sort_key(e["induction_season"]), e["player_id"])
    ):
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

    # Sort timeline by season then week (None last in week); numeric season order
    timeline.sort(key=lambda e: (season_sort_key(e["season"]), e["week"] or 999))

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
            "ovr_final": int(r.get("overall", p.overall_skill())),
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
    banners.sort(key=lambda b: season_sort_key(b["season"]))

    from .persistence import load_program_trajectories
    return {
        "club_id": club_id,
        "hero": hero,
        "timeline": timeline,
        "alumni": alumni,
        "banners": banners,
        "program_archetype": clubs[club_id].program_archetype if club_id in clubs else "Balanced Rebuild",
        "program_trajectories": load_program_trajectories(conn, club_id),
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

    # Longest win streak per club from match_records (numeric season order —
    # a string ORDER BY scrambles streaks from season 10 onward)
    streak_map: dict = {}
    for c_id in clubs:
        rows = conn.execute(
            """
            SELECT winner_club_id, season_id, week, match_id FROM match_records
            WHERE home_club_id = ? OR away_club_id = ?
            """,
            (c_id, c_id),
        ).fetchall()
        rows = sorted(
            rows,
            key=lambda r: (season_sort_key(r["season_id"]), r["week"], r["match_id"]),
        )
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

    # V23: the World Championship roll — alive from Season 1, whether or not
    # the player's club has ever been near it.
    from dodgeball_sim.pyramid_postseason import load_worlds_history

    worlds = list(reversed(load_worlds_history(conn)))

    return {
        "directory": directory,
        "dynasty_rankings": dynasty_rankings,
        "records": load_league_records(conn),
        "hof": hof,
        "rivalries": rivalries,
        "worlds": worlds,
    }


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def unknown_api_route(full_path: str):
    raise HTTPException(status_code=404, detail=f"Unknown API route: /api/{full_path}")

# --- SPA Routing ---

frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    _frontend_dist_root = frontend_dist.resolve()
    _index_html = _frontend_dist_root / "index.html"

    def _serve_index() -> FileResponse:
        return _inject_launch_token(FileResponse(_index_html))

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # WT-13: the SPA fallback must never serve a file from outside
        # frontend/dist. An attacker can encode "../" segments (or use
        # backslashes / absolute paths on Windows) to try to walk out of the
        # bundle and read local repo files. Resolve the candidate against the
        # filesystem and confirm it stays inside the dist root before serving;
        # anything else falls through to index.html (the SPA's own router then
        # renders its 404). Resolving handles encoded traversal, mixed
        # separators, and symlinks regardless of how the bytes arrived.
        candidate = (_frontend_dist_root / full_path).resolve()
        if candidate.is_relative_to(_frontend_dist_root) and candidate.is_file():
            # index.html is always served through the injecting path so the
            # SPA can read the launch token regardless of how it was requested.
            if candidate == _index_html:
                return _serve_index()
            return FileResponse(candidate)
        return _serve_index()
