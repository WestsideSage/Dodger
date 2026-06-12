from __future__ import annotations

import json
import sqlite3
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


def _connect_readonly(path: Path) -> sqlite3.Connection:
    """Open a save STRICTLY read-only so listing/metadata cannot write to the
    save database file.

    WT-15: ``read_save_meta`` runs on the save-listing path. Going through
    ``connect()`` would (a) flip the file into WAL mode (a header write) and
    (b) tempt callers into running ``create_schema``/migrations, silently
    upgrading an older save with no backup the moment it is merely listed.
    A ``mode=ro`` URI handle forbids every write to the database at the SQLite
    layer, so the listing path reads metadata without changing a single byte of
    the save ``.db`` itself — it is byte-identical afterward, and no migration or
    schema upgrade ever runs on a mere listing. (``mode=ro`` guards the database
    file, not the directory: SQLite may create empty ``-wal``/``-shm`` sidecars
    on open; the save's data is never written.) Migration happens only on an
    explicit resume/load through the backed-up path.
    """
    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def read_save_meta(path: Path) -> dict[str, Any]:
    import os
    last_modified = 0.0
    try:
        last_modified = os.path.getmtime(path)
    except Exception:
        pass

    try:
        conn = _connect_readonly(path)
        try:
            from .persistence import load_all_rosters

            # WT-15: do NOT run create_schema/migrate here. Listing a save must
            # be non-mutating; an older-schema save is detected as
            # ``incompatible`` below (or surfaces via the outer guard) and is
            # migrated only on an explicit resume.
            #
            # Try loading rosters to verify database compatibility.
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


# Historical default creation seed (matches BuildFromScratchRequest.root_seed).
# V22 Phase 1: the founding pool used to be hardcoded to DeterministicRNG(12345),
# so every created club drafted the SAME 25 prospects forever. The wizard now
# holds a per-creation seed that drives both the prospect list it shows and the
# build it commits — the two MUST agree, so both run through this helper.
DEFAULT_CREATION_SEED = 20260426


def _founding_pool(seed: int):
    from .config import DEFAULT_SCOUTING_CONFIG
    from .recruitment import generate_prospect_pool
    from .rng import DeterministicRNG, derive_seed

    rng = DeterministicRNG(derive_seed(int(seed), "founding_pool"))
    return generate_prospect_pool(2026, rng, DEFAULT_SCOUTING_CONFIG)


def _founding_ceiling(prospect) -> int:
    """The ceiling a founder will actually carry, exactly as the roster
    computes it post-commit: natural headroom (best hidden rating + 8 — the
    V19 rule, no more 70 floor) raised by the trajectory arc's floor."""
    from .development import _TRAJECTORY_POTENTIAL_FLOOR

    natural = min(100.0, max(prospect.hidden_ratings.values()) + 8.0)
    floor = _TRAJECTORY_POTENTIAL_FLOOR.get(prospect.hidden_trajectory)
    return int(round(max(natural, floor) if floor is not None else natural))


def starting_prospects_payload(seed: int | None = None) -> dict[str, Any]:
    """Founding-draft prospect list.

    The founding draft is the moment a coach signs their own first roster,
    not an arms-length scouting report. There is no fog-of-war story here,
    so we expose the *true* archetype label, the *true* integer OVR, the six
    display ratings, the ceiling, and the growth-arc grade — the same values
    the roster screen will render the instant the user commits. The OVR is
    still expressed as a band for layout compatibility, but the low and high
    bound the same true value so the displayed and persisted numbers cannot
    drift. See test_founding_roster_continuity.py.
    """
    from .archetype_derivation import derive_archetype
    from .development import calculate_potential_tier
    from .models import PlayerRatings
    from .recruitment import _display_name_for_archetype
    from .scouting_center import ceiling_label_for_trajectory

    pool = _founding_pool(DEFAULT_CREATION_SEED if seed is None else seed)
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
        ceiling = _founding_ceiling(prospect)
        try:
            arc = ceiling_label_for_trajectory(prospect.hidden_trajectory)
        except ValueError:
            arc = None
        prospects_out.append(
            {
                "player_id": prospect.player_id,
                "name": prospect.name,
                "hometown": prospect.hometown,
                "public_archetype": true_archetype_label,
                "public_ovr_band": (true_overall, true_overall),
                # V22 Phase 1/5: the founding picker shows the full sheet —
                # it is the player's own class, so nothing is fogged.
                "age": prospect.age,
                "ratings": {
                    "accuracy": int(round(ratings.accuracy)),
                    "power": int(round(ratings.power)),
                    "dodge": int(round(ratings.dodge)),
                    "catch": int(round(ratings.catch)),
                    "stamina": int(round(ratings.stamina)),
                    "tactical_iq": int(round(ratings.tactical_iq)),
                },
                "potential_ceiling": ceiling,
                "potential_tier": calculate_potential_tier(float(ceiling)),
                "ceiling_label": arc,
            }
        )
    return {"prospects": prospects_out}


FOUNDING_ROSTER_MIN = 6
FOUNDING_ROSTER_MAX = 10


def _validate_founding_roster_ids(
    requested_ids: Any, valid_ids: set[str]
) -> list[str]:
    """Validate the founding roster selection BEFORE any file is created.

    WT-14: a founding roster with duplicate or unknown ids must be rejected up
    front, so no save (not even a temp file) is ever written for a bad request.
    Returns the ordered list of unique, valid ids on success; raises
    ``SaveServiceError`` (mapped to 400 by the route) otherwise.
    """
    if not isinstance(requested_ids, list):
        raise SaveServiceError("Roster selection must be a list of player ids.")

    seen: set[str] = set()
    ordered_unique: list[str] = []
    for raw in requested_ids:
        if not isinstance(raw, str) or not raw:
            raise SaveServiceError("Roster selection contains an invalid player id.")
        if raw in seen:
            raise SaveServiceError(
                "Roster selection contains duplicate player ids."
            )
        seen.add(raw)
        ordered_unique.append(raw)

    unknown = [pid for pid in ordered_unique if pid not in valid_ids]
    if unknown:
        raise SaveServiceError(
            "Roster selection contains unknown player ids."
        )

    if len(ordered_unique) < FOUNDING_ROSTER_MIN:
        raise SaveServiceError(
            f"Must select at least {FOUNDING_ROSTER_MIN} prospects."
        )
    if len(ordered_unique) > FOUNDING_ROSTER_MAX:
        raise SaveServiceError(
            f"Cannot select more than {FOUNDING_ROSTER_MAX} prospects."
        )

    return ordered_unique


def build_from_scratch_save(saves_dir: Path, request: dict[str, Any]) -> dict[str, str]:
    import os

    from .league import Club
    from .models import Player, PlayerRatings, PlayerTraits

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

    # V22 Phase 1: the pool is derived from the creation seed the wizard also
    # used to FETCH the prospect list — picker and builder agree by
    # construction, and two creations with different seeds face different
    # founding classes.
    creation_seed = int(request.get("root_seed", DEFAULT_CREATION_SEED))
    pool = _founding_pool(creation_seed)
    roster_map = {prospect.player_id: prospect for prospect in pool}

    # WT-14: validate the selection up front. On rejection we have not created
    # any file, so no partial/corrupt .db can be left behind.
    roster_ids = _validate_founding_roster_ids(
        request.get("roster_player_ids"), set(roster_map.keys())
    )

    from .archetype_derivation import derive_archetype
    custom_roster = []
    for player_id in roster_ids:
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
                    # V22 Phase 1 (owner: natural ceilings + arcs): founders
                    # use the same V19 rule as every other signing — their own
                    # natural headroom (best hidden rating + 8). The old
                    # max(70, ...) floor made 9 of 10 founders carry an
                    # identical "Ceil 70" (playtest 3 Observation A); rare
                    # trajectory arcs raise the effective ceiling instead,
                    # persisted below exactly like a Signing Day signing.
                    potential=min(100.0, max(prospect.hidden_ratings.values()) + 8.0),
                    growth_curve=50.0,
                    consistency=0.5,
                    pressure=0.5,
                ),
            )
        )

    # WT-14: build into a temp file, then atomically rename into place. A crash
    # mid-build leaves only a temp artifact (cleaned below), never a half-written
    # save at the real path.
    tmp_path = path.with_name(f".{safe_name}.db.tmp")
    _cleanup_sqlite_file(tmp_path)
    try:
        conn = connect(tmp_path)
        try:
            initialize_curated_manager_career(
                conn,
                club_id,
                creation_seed,
                custom_club=custom_club,
                custom_roster=custom_roster,
                ruleset_selection=request.get("ruleset_selection"),
            )
            set_state(conn, "coach_backstory", request["coach_backstory"])

            # V22 Phase 1: persist each founder's growth arc exactly like a
            # Signing Day signing does — the development engine reads it for
            # the trajectory floor/multiplier, and the roster screen raises
            # the displayed ceiling with it.
            from .persistence import save_player_trajectory

            for player_id in roster_ids:
                save_player_trajectory(
                    conn, player_id, roster_map[player_id].hidden_trajectory
                )

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
        # Fold the WAL back into the main file so the rename moves a complete DB.
        _checkpoint_and_drop_wal(tmp_path)
        os.replace(tmp_path, path)
    except Exception:
        _cleanup_sqlite_file(tmp_path)
        # Never leave a partial save at the real path either.
        _cleanup_sqlite_file(path)
        raise
    return {"status": "ok", "path": str(path)}


def _cleanup_sqlite_file(path: Path) -> None:
    """Remove a SQLite file and its WAL/SHM sidecars, ignoring absence."""
    for suffix in ("", "-wal", "-shm"):
        sidecar = path if not suffix else path.with_name(path.name + suffix)
        try:
            sidecar.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _checkpoint_and_drop_wal(path: Path) -> None:
    """Checkpoint a WAL-mode DB and drop its sidecars so a single-file rename
    moves a complete, self-contained database."""
    try:
        conn = connect(path)
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass
    for suffix in ("-wal", "-shm"):
        sidecar = path.with_name(path.name + suffix)
        try:
            sidecar.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


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
