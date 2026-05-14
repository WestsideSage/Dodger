from __future__ import annotations

from pathlib import Path
from typing import Any

from .career_setup import initialize_curated_manager_career
from .persistence import connect, set_state
from .sample_data import curated_clubs


class SaveServiceError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def resolve_managed_save_path(raw: str, *, saves_dir: Path, default_db_path: Path, allow_legacy: bool) -> Path:
    if not raw or not isinstance(raw, str):
        raise SaveServiceError("Save path is required.")
    candidate = Path(raw)
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise SaveServiceError("Invalid save path.") from exc
    saves_root = saves_dir.resolve()
    legacy = default_db_path.resolve()
    if resolved.suffix.lower() != ".db":
        raise SaveServiceError("Save files must end in .db.")
    try:
        resolved.relative_to(saves_root)
        is_managed = True
    except ValueError:
        is_managed = False
    if not is_managed and not (allow_legacy and resolved == legacy):
        raise SaveServiceError("Save path must be under the managed saves directory.", status_code=403)
    if not resolved.exists():
        raise SaveServiceError("Save file not found.", status_code=404)
    if not resolved.is_file():
        raise SaveServiceError("Save path is not a file.")
    return resolved


def looks_like_dodgeball_save(path: Path) -> bool:
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


def read_save_meta(path: Path) -> dict[str, Any]:
    try:
        conn = connect(path)
        try:
            from .persistence import create_schema

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
        return {
            "name": path.stem,
            "path": str(path),
            "club_id": None,
            "club_name": None,
            "season_id": None,
            "week": None,
        }


_TEST_SAVE_PREFIXES = ("e2e-", "e2e_", "command-aftermath", "codex")


def _is_test_save(path: Path) -> bool:
    stem = path.stem.lower()
    return any(stem.startswith(prefix) for prefix in _TEST_SAVE_PREFIXES)


def list_saves_payload(saves_dir: Path, default_db_path: Path, active_save_path: Path | None) -> dict[str, Any]:
    saves_dir.mkdir(exist_ok=True)
    saves = [
        read_save_meta(db_file)
        for db_file in sorted(saves_dir.glob("*.db"))
        if not _is_test_save(db_file)
    ]
    if default_db_path.exists():
        saves.append(read_save_meta(default_db_path))
    return {"saves": saves, "active_path": str(active_save_path) if active_save_path else None}


def create_new_save(saves_dir: Path, *, name: str, club_id: str, root_seed: int) -> dict[str, str]:
    saves_dir.mkdir(exist_ok=True)
    safe_name = sanitize_save_name(name)
    path = saves_dir / f"{safe_name}.db"
    if path.exists():
        raise SaveServiceError(f"Save '{safe_name}' already exists.", status_code=409)
    conn = connect(path)
    try:
        initialize_curated_manager_career(conn, club_id, root_seed)
    finally:
        conn.close()
    return {"status": "ok", "path": str(path)}


def starting_prospects_payload() -> dict[str, Any]:
    from .config import DEFAULT_SCOUTING_CONFIG
    from .recruitment import generate_prospect_pool
    from .rng import DeterministicRNG

    pool = generate_prospect_pool(2026, DeterministicRNG(12345), DEFAULT_SCOUTING_CONFIG)
    return {
        "prospects": [
            {
                "player_id": prospect.player_id,
                "name": prospect.name,
                "hometown": prospect.hometown,
                "public_archetype": prospect.public_archetype_guess,
                "public_ovr_band": prospect.public_ratings_band["ovr"],
            }
            for prospect in pool
        ]
    }


def build_from_scratch_save(saves_dir: Path, request: dict[str, Any]) -> dict[str, str]:
    from .config import DEFAULT_SCOUTING_CONFIG
    from .league import Club
    from .models import Player, PlayerRatings, PlayerTraits
    from .recruitment import generate_prospect_pool
    from .rng import DeterministicRNG

    saves_dir.mkdir(exist_ok=True)
    safe_name = sanitize_save_name(request["save_name"])
    path = saves_dir / f"{safe_name}.db"
    if path.exists():
        raise SaveServiceError(f"Save '{safe_name}' already exists.", status_code=409)

    club_id = safe_name.lower().replace(" ", "_")
    custom_club = Club(
        club_id=club_id,
        name=request["club_name"],
        colors=request["colors"],
        home_region=request["city"],
        founded_year=2026,
        tagline=f"{request['city']} - {request['coach_name']}",
    )

    pool = generate_prospect_pool(2026, DeterministicRNG(12345), DEFAULT_SCOUTING_CONFIG)
    roster_map = {prospect.player_id: prospect for prospect in pool}
    custom_roster = []
    for player_id in request["roster_player_ids"]:
        if player_id in roster_map:
            prospect = roster_map[player_id]
            custom_roster.append(
                Player(
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
                )
            )

    if len(custom_roster) < 6:
        raise SaveServiceError("Must select at least 6 prospects.")

    conn = connect(path)
    try:
        initialize_curated_manager_career(
            conn,
            club_id,
            int(request.get("root_seed", 20260426)),
            custom_club=custom_club,
            custom_roster=custom_roster,
        )
        set_state(conn, "coach_backstory", request["coach_backstory"])
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok", "path": str(path)}


def list_clubs_payload() -> dict[str, Any]:
    return {
        "clubs": [
            {
                "club_id": club.club_id,
                "name": club.name,
                "tagline": getattr(club, "tagline", ""),
                "colors": getattr(club, "colors", ""),
            }
            for club in curated_clubs()
        ]
    }


def sanitize_save_name(name: str) -> str:
    return "".join(character for character in name if character.isalnum() or character in "-_ ").strip() or "save"
