from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .career_setup import initialize_curated_manager_career
from .persistence import connect, load_prospect_pool, set_state
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
    import os
    last_modified = 0.0
    try:
        last_modified = os.path.getmtime(path)
    except Exception:
        pass

    try:
        conn = connect(path)
        try:
            from .persistence import create_schema, load_all_rosters

            create_schema(conn)
            # Try loading rosters to verify database compatibility
            try:
                load_all_rosters(conn)
                is_incompatible = False
            except Exception:
                is_incompatible = True

            club_id = conn.execute("SELECT value FROM dynasty_state WHERE key='player_club_id'").fetchone()
            season_id = conn.execute("SELECT value FROM dynasty_state WHERE key='active_season_id'").fetchone()
            week_row = conn.execute("SELECT value FROM dynasty_state WHERE key='career_week'").fetchone()
            club_name = None
            if club_id:
                row = conn.execute("SELECT name FROM clubs WHERE club_id=?", (club_id[0],)).fetchone()
                club_name = row[0] if row else club_id[0]

            wins = 0
            losses = 0
            draws = 0
            if club_id and season_id:
                try:
                    standings_row = conn.execute(
                        "SELECT wins, losses, draws FROM season_standings WHERE season_id = ? AND club_id = ?",
                        (season_id[0], club_id[0])
                    ).fetchone()
                    if standings_row:
                        wins, losses, draws = standings_row
                except Exception:
                    pass

            season_number = 1
            try:
                cursor_row = conn.execute("SELECT value FROM dynasty_state WHERE key='career_state_cursor'").fetchone()
                if cursor_row:
                    cursor_data = json.loads(cursor_row[0])
                    season_number = cursor_data.get("season_number", 1)
            except Exception:
                pass

            return {
                "name": path.stem,
                "path": str(path),
                "club_id": club_id[0] if club_id else None,
                "club_name": club_name,
                "season_id": season_id[0] if season_id else None,
                "week": int(week_row[0]) if week_row else None,
                "incompatible": is_incompatible,
                "last_modified": last_modified,
                "season_number": season_number,
                "wins": wins,
                "losses": losses,
                "draws": draws,
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
            "incompatible": True,
            "last_modified": last_modified,
            "season_number": 1,
            "wins": 0,
            "losses": 0,
            "draws": 0,
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
    saves.sort(key=lambda s: s.get("last_modified", 0.0), reverse=True)
    return {"saves": saves, "active_path": str(active_save_path) if active_save_path else None}



def create_new_save(
    saves_dir: Path,
    *,
    name: str,
    club_id: str,
    root_seed: int,
    ruleset_selection: str | None = None,
) -> dict[str, str]:
    saves_dir.mkdir(exist_ok=True)
    safe_name = sanitize_save_name(name)
    path = saves_dir / f"{safe_name}.db"
    if path.exists():
        raise SaveServiceError(f"Save '{safe_name}' already exists.", status_code=409)
    conn = connect(path)
    try:
        initialize_curated_manager_career(
            conn, club_id, root_seed, ruleset_selection=ruleset_selection,
        )
    finally:
        conn.close()
    return {"status": "ok", "path": str(path)}


def starting_prospects_payload() -> dict[str, Any]:
    """Founding-draft prospect list.

    The founding draft is the moment a coach signs their own first roster,
    not an arms-length scouting report. There is no fog-of-war story here,
    so we expose the *true* archetype label and the *true* integer OVR — the
    same values the roster screen will render the instant the user commits.
    The OVR is still expressed as a band for layout compatibility, but the
    low and high bound the same true value so the displayed and persisted
    numbers cannot drift. See test_founding_roster_continuity.py.
    """
    from .archetype_derivation import derive_archetype
    from .config import DEFAULT_SCOUTING_CONFIG
    from .models import PlayerRatings
    from .recruitment import _display_name_for_archetype, generate_prospect_pool
    from .rng import DeterministicRNG

    pool = generate_prospect_pool(2026, DeterministicRNG(12345), DEFAULT_SCOUTING_CONFIG)
    prospects_out = []
    for prospect in pool:
        ratings = PlayerRatings(
            accuracy=prospect.hidden_ratings["accuracy"],
            power=prospect.hidden_ratings["power"],
            dodge=prospect.hidden_ratings["dodge"],
            catch=prospect.hidden_ratings["catch"],
            stamina=prospect.hidden_ratings["stamina"],
            tactical_iq=prospect.hidden_ratings.get("tactical_iq", 50.0),
            catch_courage=prospect.hidden_ratings.get("catch_courage", 50.0),
            throw_selection_iq=prospect.hidden_ratings.get("throw_selection_iq", 50.0),
            conditioning_curve=prospect.hidden_ratings.get("conditioning_curve", 50.0),
        ).apply_bounds()
        true_archetype_label = _display_name_for_archetype(
            derive_archetype(ratings), ratings
        )
        true_overall = ratings.overall_skill()
        prospects_out.append(
            {
                "player_id": prospect.player_id,
                "name": prospect.name,
                "hometown": prospect.hometown,
                "public_archetype": true_archetype_label,
                "public_ovr_band": (true_overall, true_overall),
            }
        )
    return {"prospects": prospects_out}


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
    from .archetype_derivation import derive_archetype
    for player_id in request["roster_player_ids"]:
        if player_id in roster_map:
            prospect = roster_map[player_id]
            ratings = PlayerRatings(
                accuracy=prospect.hidden_ratings["accuracy"],
                power=prospect.hidden_ratings["power"],
                dodge=prospect.hidden_ratings["dodge"],
                catch=prospect.hidden_ratings["catch"],
                stamina=prospect.hidden_ratings["stamina"],
                tactical_iq=prospect.hidden_ratings.get("tactical_iq", 50.0),
                catch_courage=prospect.hidden_ratings.get("catch_courage", 50.0),
                throw_selection_iq=prospect.hidden_ratings.get("throw_selection_iq", 50.0),
                conditioning_curve=prospect.hidden_ratings.get("conditioning_curve", 50.0),
            ).apply_bounds()
            custom_roster.append(
                Player(
                    id=prospect.player_id,
                    name=prospect.name,
                    age=prospect.age,
                    club_id=club_id,
                    newcomer=True,
                    ratings=ratings,
                    archetype=derive_archetype(ratings),
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
            ruleset_selection=request.get("ruleset_selection"),
        )
        set_state(conn, "coach_backstory", request["coach_backstory"])

        # Seed 3 warm prospects from the active career pool.
        remaining_prospects = load_prospect_pool(conn, class_year=1)
        remaining_prospects.sort(key=lambda p: (-p.pipeline_tier, p.player_id))
        warm = remaining_prospects[:3]
        warm_actions = {
            p.player_id: {"scouted": True, "contacted": True}
            for p in warm
        }
        set_state(conn, "prospect_recruitment_actions_json", json.dumps(warm_actions))

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
