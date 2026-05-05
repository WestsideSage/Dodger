from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .awards import SeasonAward
from .engine import MatchResult
from .league import Club
from .models import CoachPolicy, MatchSetup, Player, PlayerArchetype, PlayerRatings, PlayerTraits, Team
from .scheduler import ScheduledMatch
from .season import Season, SeasonResult, StandingsRow
from .stats import PlayerMatchStats

_JSON_OPTIONS = dict(separators=(",", ":"), sort_keys=True)

if TYPE_CHECKING:
    from .career_state import CareerStateCursor

# Increment when new migrations are added.
CURRENT_SCHEMA_VERSION = 13
_MAX_OFFSEASON_BEAT_INDEX = 9


class CorruptSaveError(RuntimeError):
    """Raised when persisted save JSON is unreadable and should not be guessed."""

    pass


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _player_to_dict(player: Player) -> Dict[str, Any]:
    ratings = player.ratings
    return {
        "id": player.id,
        "name": player.name,
        "age": player.age,
        "club_id": player.club_id,
        "newcomer": player.newcomer,
        "archetype": player.archetype.value,
        "ratings": {
            "accuracy": ratings.accuracy,
            "power": ratings.power,
            "dodge": ratings.dodge,
            "catch": ratings.catch,
            "stamina": ratings.stamina,
            "tactical_iq": ratings.tactical_iq,
        },
        "traits": {
            "potential": player.traits.potential,
            "growth_curve": player.traits.growth_curve,
            "consistency": player.traits.consistency,
            "pressure": player.traits.pressure,
        },
    }


def _player_from_dict(d: Dict[str, Any]) -> Player:
    r = d.get("ratings", {})
    t = d.get("traits", {})
    return Player(
        id=d["id"],
        name=d["name"],
        age=d.get("age", 18),
        club_id=d.get("club_id"),
        newcomer=d.get("newcomer", True),
        archetype=PlayerArchetype(d.get("archetype", "Tactical")),
        ratings=PlayerRatings(
            accuracy=r.get("accuracy", 60.0),
            power=r.get("power", 60.0),
            dodge=r.get("dodge", 60.0),
            catch=r.get("catch", 60.0),
            stamina=r.get("stamina", 60.0),
            tactical_iq=r.get("tactical_iq", 50.0),
        ),
        traits=PlayerTraits(
            potential=t.get("potential", 60),
            growth_curve=t.get("growth_curve", 50.0),
            consistency=t.get("consistency", 0.5),
            pressure=t.get("pressure", 0.5),
        ),
    )


def _team_to_dict(team: Team) -> Dict[str, Any]:
    return {
        "id": team.id,
        "name": team.name,
        "chemistry": team.chemistry,
        "coach_policy": team.coach_policy.as_dict(),
        "players": [_player_to_dict(player) for player in team.players],
    }


def match_setup_to_dict(setup: MatchSetup) -> Dict[str, Any]:
    return {
        "team_a": _team_to_dict(setup.team_a),
        "team_b": _team_to_dict(setup.team_b),
        "config_version": setup.config_version,
    }


def _json_dump(payload: Any) -> str:
    return json.dumps(payload, **_JSON_OPTIONS)


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    if path != Path(":memory:"):
        conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------

def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version, or 0 if unversioned/new."""
    try:
        cursor = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return int(row["version"]) if row else 0
    except sqlite3.OperationalError:
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
        (version, _utcnow_iso()),
    )


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Phase 1 tables: matches and match_events."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seed INTEGER NOT NULL,
            config_version TEXT NOT NULL,
            winner_team_id TEXT,
            team_a_id TEXT NOT NULL,
            team_b_id TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            setup_json TEXT NOT NULL,
            box_score_json TEXT NOT NULL,
            final_tick INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS match_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            event_index INTEGER NOT NULL,
            event_json TEXT NOT NULL,
            FOREIGN KEY(match_id) REFERENCES matches(id)
        );

        CREATE INDEX IF NOT EXISTS idx_match_events_match_id
            ON match_events(match_id);
        """
    )


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """Phase 2 tables: dynasty spine, roster snapshots, season scaffolding."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS domain_events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            scope TEXT NOT NULL,
            entity_ids_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            seed INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS clubs (
            club_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            colors TEXT NOT NULL,
            home_region TEXT NOT NULL,
            founded_year INTEGER NOT NULL,
            coach_policy_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS seasons (
            season_id TEXT PRIMARY KEY,
            year INTEGER NOT NULL,
            league_id TEXT NOT NULL,
            config_version TEXT NOT NULL,
            ruleset_version TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scheduled_matches (
            match_id TEXT PRIMARY KEY,
            season_id TEXT NOT NULL,
            week INTEGER NOT NULL,
            home_club_id TEXT NOT NULL,
            away_club_id TEXT NOT NULL,
            FOREIGN KEY(season_id) REFERENCES seasons(season_id)
        );

        CREATE TABLE IF NOT EXISTS match_records (
            match_id TEXT PRIMARY KEY,
            season_id TEXT NOT NULL,
            week INTEGER NOT NULL,
            home_club_id TEXT NOT NULL,
            away_club_id TEXT NOT NULL,
            winner_club_id TEXT,
            home_survivors INTEGER NOT NULL DEFAULT 0,
            away_survivors INTEGER NOT NULL DEFAULT 0,
            home_roster_hash TEXT NOT NULL,
            away_roster_hash TEXT NOT NULL,
            config_version TEXT NOT NULL,
            ruleset_version TEXT NOT NULL,
            meta_patch_id TEXT,
            seed INTEGER NOT NULL,
            event_log_hash TEXT NOT NULL,
            final_state_hash TEXT NOT NULL,
            engine_match_id INTEGER,
            FOREIGN KEY(season_id) REFERENCES seasons(season_id),
            FOREIGN KEY(engine_match_id) REFERENCES matches(id)
        );

        CREATE TABLE IF NOT EXISTS match_roster_snapshots (
            match_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            players_json TEXT NOT NULL,
            PRIMARY KEY (match_id, club_id)
        );

        CREATE TABLE IF NOT EXISTS player_match_stats (
            match_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            throws_attempted INTEGER NOT NULL DEFAULT 0,
            throws_on_target INTEGER NOT NULL DEFAULT 0,
            eliminations_by_throw INTEGER NOT NULL DEFAULT 0,
            catches_attempted INTEGER NOT NULL DEFAULT 0,
            catches_made INTEGER NOT NULL DEFAULT 0,
            times_targeted INTEGER NOT NULL DEFAULT 0,
            dodges_successful INTEGER NOT NULL DEFAULT 0,
            times_hit INTEGER NOT NULL DEFAULT 0,
            times_eliminated INTEGER NOT NULL DEFAULT 0,
            revivals_caused INTEGER NOT NULL DEFAULT 0,
            clutch_events INTEGER NOT NULL DEFAULT 0,
            elimination_plus_minus INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (match_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS season_standings (
            season_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            draws INTEGER NOT NULL DEFAULT 0,
            elimination_differential INTEGER NOT NULL DEFAULT 0,
            points INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (season_id, club_id)
        );

        CREATE TABLE IF NOT EXISTS season_awards (
            season_id TEXT NOT NULL,
            award_type TEXT NOT NULL,
            player_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            award_score REAL NOT NULL DEFAULT 0.0,
            PRIMARY KEY (season_id, award_type)
        );

        CREATE TABLE IF NOT EXISTS club_rosters (
            club_id TEXT NOT NULL,
            players_json TEXT NOT NULL,
            PRIMARY KEY (club_id)
        );

        CREATE TABLE IF NOT EXISTS dynasty_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_scheduled_matches_season
            ON scheduled_matches(season_id, week);

        CREATE INDEX IF NOT EXISTS idx_match_records_season
            ON match_records(season_id, week);

        CREATE INDEX IF NOT EXISTS idx_player_match_stats_player
            ON player_match_stats(player_id);
        """
    )


def _migrate_v3(conn: sqlite3.Connection) -> None:
    """Phase 3 tables: offseason continuity, retirements, free agents."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS free_agents (
            player_id TEXT PRIMARY KEY,
            available_since_season TEXT NOT NULL,
            player_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS player_season_stats (
            player_id TEXT NOT NULL,
            season_id TEXT NOT NULL,
            club_id TEXT,
            matches INTEGER NOT NULL DEFAULT 0,
            total_throws_attempted INTEGER NOT NULL DEFAULT 0,
            total_eliminations INTEGER NOT NULL DEFAULT 0,
            total_catches_made INTEGER NOT NULL DEFAULT 0,
            total_dodges_successful INTEGER NOT NULL DEFAULT 0,
            total_times_eliminated INTEGER NOT NULL DEFAULT 0,
            newcomer INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, season_id)
        );

        CREATE TABLE IF NOT EXISTS retired_players (
            player_id TEXT PRIMARY KEY,
            final_season TEXT NOT NULL,
            retirement_reason TEXT NOT NULL,
            age_at_retirement INTEGER NOT NULL,
            player_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_player_season_stats_season
            ON player_season_stats(season_id, club_id);
        """
    )


def _migrate_v4(conn: sqlite3.Connection) -> None:
    """Phase 4/5A tables: identity, story, facilities, league wire."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS player_identity (
            player_id TEXT PRIMARY KEY,
            nickname TEXT NOT NULL,
            archetype TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS player_career_stats (
            player_id TEXT PRIMARY KEY,
            career_eliminations INTEGER NOT NULL DEFAULT 0,
            career_catches INTEGER NOT NULL DEFAULT 0,
            career_dodges INTEGER NOT NULL DEFAULT 0,
            seasons_played INTEGER NOT NULL DEFAULT 0,
            championships INTEGER NOT NULL DEFAULT 0,
            clubs_served INTEGER NOT NULL DEFAULT 0,
            career_summary_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS signature_moments (
            moment_id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            season_id TEXT NOT NULL,
            match_id TEXT,
            moment_type TEXT NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS hall_of_fame (
            player_id TEXT PRIMARY KEY,
            induction_season TEXT NOT NULL,
            career_summary_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rivalry_records (
            club_a_id TEXT NOT NULL,
            club_b_id TEXT NOT NULL,
            a_wins INTEGER NOT NULL DEFAULT 0,
            b_wins INTEGER NOT NULL DEFAULT 0,
            draws INTEGER NOT NULL DEFAULT 0,
            rivalry_score REAL NOT NULL DEFAULT 0.0,
            last_meeting_season TEXT,
            rivalry_json TEXT NOT NULL,
            PRIMARY KEY (club_a_id, club_b_id)
        );

        CREATE TABLE IF NOT EXISTS league_records (
            record_type TEXT PRIMARY KEY,
            holder_id TEXT NOT NULL,
            holder_type TEXT NOT NULL,
            record_value REAL NOT NULL,
            set_in_season TEXT NOT NULL,
            record_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS news_headlines (
            headline_id TEXT PRIMARY KEY,
            season_id TEXT NOT NULL,
            week INTEGER NOT NULL,
            category TEXT NOT NULL,
            headline_text TEXT NOT NULL,
            entity_ids_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS club_facilities (
            club_id TEXT NOT NULL,
            season_id TEXT NOT NULL,
            facility_type TEXT NOT NULL,
            PRIMARY KEY (club_id, season_id, facility_type)
        );

        CREATE TABLE IF NOT EXISTS club_prestige (
            club_id TEXT PRIMARY KEY,
            prestige_score INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_signature_moments_player
            ON signature_moments(player_id, season_id);
        CREATE INDEX IF NOT EXISTS idx_news_headlines_season_week
            ON news_headlines(season_id, week);
        """
    )


def _migrate_v5(conn: sqlite3.Connection) -> None:
    """Phase 5B tables: meta patches, cup brackets/results, trophies."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta_patches (
            patch_id TEXT PRIMARY KEY,
            season_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            modifiers_json TEXT NOT NULL,
            ruleset_overrides_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cup_brackets (
            cup_id TEXT PRIMARY KEY,
            season_id TEXT NOT NULL,
            bracket_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cup_results (
            cup_id TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            match_id TEXT NOT NULL,
            winner_club_id TEXT NOT NULL,
            PRIMARY KEY (cup_id, match_id)
        );

        CREATE TABLE IF NOT EXISTS club_trophies (
            club_id TEXT NOT NULL,
            trophy_type TEXT NOT NULL,
            season_id TEXT NOT NULL,
            PRIMARY KEY (club_id, trophy_type, season_id)
        );
        """
    )


def _migrate_v6(conn: sqlite3.Connection) -> None:
    """Manager Mode M0: extend clubs with identity fields."""
    conn.executescript(
        """
        ALTER TABLE clubs ADD COLUMN primary_color TEXT NOT NULL DEFAULT '';
        ALTER TABLE clubs ADD COLUMN secondary_color TEXT NOT NULL DEFAULT '';
        ALTER TABLE clubs ADD COLUMN venue_name TEXT NOT NULL DEFAULT '';
        ALTER TABLE clubs ADD COLUMN tagline TEXT NOT NULL DEFAULT '';
        """
    )


def _migrate_v7(conn: sqlite3.Connection) -> None:
    """Manager Mode M0: persist default lineups and per-match overrides."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS lineup_default (
            club_id TEXT PRIMARY KEY,
            ordered_player_ids_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS match_lineup_override (
            match_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            ordered_player_ids_json TEXT NOT NULL,
            PRIMARY KEY (match_id, club_id)
        );
        """
    )


def _migrate_v8(conn: sqlite3.Connection) -> None:
    """V2-A Stateful Scouting Model tables."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS prospect_pool (
            class_year INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            age INTEGER NOT NULL DEFAULT 18,
            hometown TEXT NOT NULL DEFAULT '',
            archetype TEXT NOT NULL DEFAULT '',
            hidden_ratings_json TEXT NOT NULL,
            hidden_trajectory TEXT NOT NULL,
            hidden_traits_json TEXT NOT NULL,
            public_archetype_guess TEXT NOT NULL,
            public_ratings_band_json TEXT NOT NULL,
            is_signed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (class_year, player_id)
        );

        CREATE TABLE IF NOT EXISTS scouting_state (
            player_id TEXT NOT NULL,
            axis TEXT NOT NULL,
            tier TEXT NOT NULL,
            scout_points INTEGER NOT NULL DEFAULT 0,
            last_updated_week INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (player_id, axis)
        );

        CREATE TABLE IF NOT EXISTS scouting_revealed_traits (
            player_id TEXT NOT NULL,
            trait_id TEXT NOT NULL,
            revealed_at_week INTEGER NOT NULL,
            PRIMARY KEY (player_id, trait_id)
        );

        CREATE TABLE IF NOT EXISTS scouting_ceiling_label (
            player_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            revealed_at_week INTEGER NOT NULL,
            revealed_by_scout_id TEXT
        );

        CREATE TABLE IF NOT EXISTS scout (
            scout_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_accuracy REAL NOT NULL,
            archetype_affinities_json TEXT NOT NULL,
            archetype_weakness TEXT NOT NULL,
            trait_sense TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scout_assignment (
            scout_id TEXT PRIMARY KEY,
            player_id TEXT,
            started_week INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS scout_strategy (
            scout_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            priority TEXT NOT NULL,
            archetype_filter_json TEXT NOT NULL DEFAULT '[]',
            pinned_prospects_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS scout_prospect_contribution (
            scout_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            first_assigned_week INTEGER NOT NULL,
            last_active_week INTEGER NOT NULL,
            weeks_worked INTEGER NOT NULL DEFAULT 0,
            contributed_scout_points_json TEXT NOT NULL,
            last_estimated_ratings_band_json TEXT,
            last_estimated_archetype TEXT,
            last_estimated_traits_json TEXT,
            last_estimated_ceiling TEXT,
            last_estimated_trajectory TEXT,
            PRIMARY KEY (scout_id, player_id, season)
        );

        CREATE TABLE IF NOT EXISTS scout_track_record (
            season INTEGER NOT NULL,
            scout_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            predicted_ovr_mid REAL,
            actual_ovr REAL NOT NULL,
            ovr_error REAL,
            predicted_archetype TEXT,
            actual_archetype TEXT NOT NULL,
            predicted_trajectory TEXT,
            actual_trajectory TEXT NOT NULL,
            ceiling_label TEXT,
            signed_by_user INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (season, scout_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS scouting_domain_event (
            event_id TEXT PRIMARY KEY,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            player_id TEXT,
            scout_id TEXT,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS player_trajectory (
            player_id TEXT PRIMARY KEY,
            trajectory TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_scouting_state_player_id
            ON scouting_state(player_id);
        CREATE INDEX IF NOT EXISTS idx_scouting_events_season_week
            ON scouting_domain_event(season, week);
        """
    )


def _migrate_v9(conn: sqlite3.Connection) -> None:
    """V2-B Recruitment Domain Model tables."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS club_recruitment_profile (
            club_id TEXT PRIMARY KEY,
            archetype_priorities_json TEXT NOT NULL,
            risk_tolerance REAL NOT NULL,
            prestige REAL NOT NULL,
            playing_time_pitch REAL NOT NULL,
            evaluation_quality REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recruitment_board (
            season_id TEXT NOT NULL,
            club_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            rank INTEGER NOT NULL,
            public_score REAL NOT NULL,
            need_score REAL NOT NULL,
            preference_score REAL NOT NULL,
            total_score REAL NOT NULL,
            visible_reason TEXT NOT NULL,
            PRIMARY KEY (season_id, club_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS recruitment_round (
            season_id TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (season_id, round_number)
        );

        CREATE TABLE IF NOT EXISTS recruitment_offer (
            season_id TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            club_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            offer_strength REAL NOT NULL,
            source TEXT NOT NULL,
            need_score REAL NOT NULL,
            playing_time_pitch REAL NOT NULL,
            prestige REAL NOT NULL,
            round_order_value REAL NOT NULL,
            visible_reason TEXT NOT NULL,
            PRIMARY KEY (season_id, round_number, club_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS recruitment_signing (
            season_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            club_id TEXT NOT NULL,
            source TEXT NOT NULL,
            offer_strength REAL NOT NULL,
            recap_reason TEXT NOT NULL,
            PRIMARY KEY (season_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS prospect_market_signal (
            season_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            signal_json TEXT NOT NULL,
            PRIMARY KEY (season_id, player_id)
        );

        CREATE INDEX IF NOT EXISTS idx_recruitment_board_season_club
            ON recruitment_board(season_id, club_id, rank);
        CREATE INDEX IF NOT EXISTS idx_recruitment_offer_round
            ON recruitment_offer(season_id, round_number);
        """
    )


def _migrate_v10(conn: sqlite3.Connection) -> None:
    """V2-F Playoff bracket and season outcome tables."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS playoff_brackets (
            season_id TEXT PRIMARY KEY,
            format TEXT NOT NULL,
            seeds_json TEXT NOT NULL,
            rounds_json TEXT NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS season_outcomes (
            season_id TEXT PRIMARY KEY,
            champion_club_id TEXT NOT NULL,
            champion_source TEXT NOT NULL,
            final_match_id TEXT,
            runner_up_club_id TEXT,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS season_formats (
            season_id TEXT PRIMARY KEY,
            format TEXT NOT NULL
        );
        """
    )


def _migrate_v11(conn: sqlite3.Connection) -> None:
    """V5 Weekly Command Center tables."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS department_heads (
            department TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            rating_primary REAL NOT NULL,
            rating_secondary REAL NOT NULL,
            voice TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS weekly_command_plans (
            season_id TEXT NOT NULL,
            week INTEGER NOT NULL,
            club_id TEXT NOT NULL,
            intent TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (season_id, week, club_id)
        );

        CREATE TABLE IF NOT EXISTS command_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id TEXT NOT NULL,
            week INTEGER NOT NULL,
            club_id TEXT NOT NULL,
            match_id TEXT,
            opponent_club_id TEXT,
            intent TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            dashboard_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_command_history_season_week
            ON command_history(season_id, week, history_id);
        """
    )
    _seed_default_department_heads(conn)


def _seed_default_department_heads(conn: sqlite3.Connection) -> None:
    rows = [
        ("tactics", "Mara Ives", 74.0, 68.0, "Make the plan prove itself."),
        ("training", "Dante Rook", 70.0, 72.0, "Reps have to show up on court."),
        ("conditioning", "Nia Sol", 69.0, 75.0, "Fresh legs are a choice."),
        ("medical", "Dr. Vale Chen", 76.0, 71.0, "Availability is a decision."),
        ("scouting", "Owen Pike", 73.0, 66.0, "Know what you are walking into."),
        ("culture", "Tessa Hart", 68.0, 74.0, "Pressure habits travel."),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO department_heads
            (department, name, rating_primary, rating_secondary, voice)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


def _migrate_v12(conn: sqlite3.Connection) -> None:
    """V6 Player Identity and Development Loop."""
    pass


def _migrate_v13(conn: sqlite3.Connection) -> None:
    """Persist match reps for V6 development accounting."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(player_match_stats)")}
    if "minutes_played" not in columns:
        conn.execute(
            "ALTER TABLE player_match_stats "
            "ADD COLUMN minutes_played INTEGER NOT NULL DEFAULT 0"
        )


_MIGRATIONS: Dict[int, Any] = {
    1: _migrate_v1,
    2: _migrate_v2,
    3: _migrate_v3,
    4: _migrate_v4,
    5: _migrate_v5,
    6: _migrate_v6,
    7: _migrate_v7,
    8: _migrate_v8,
    9: _migrate_v9,
    10: _migrate_v10,
    11: _migrate_v11,
    12: _migrate_v12,
    13: _migrate_v13,
}


def create_schema(conn: sqlite3.Connection) -> None:
    """Idempotent: create all tables at the latest schema version."""
    current = get_schema_version(conn)
    for version in sorted(_MIGRATIONS.keys()):
        if version > current:
            _MIGRATIONS[version](conn)
    _set_schema_version(conn, CURRENT_SCHEMA_VERSION)
    conn.commit()


def migrate_schema(
    conn: sqlite3.Connection,
    from_version: int,
    to_version: int,
    db_path: Path | str | None = None,
) -> None:
    """Apply incremental migrations from_version+1 through to_version."""
    if db_path is not None:
        backup_before_migration(Path(db_path))
    for version in range(from_version + 1, to_version + 1):
        if version not in _MIGRATIONS:
            raise ValueError(f"No migration defined for version {version}")
        _MIGRATIONS[version](conn)
    _set_schema_version(conn, to_version)
    conn.commit()


def backup_before_migration(db_path: Path) -> Path:
    """Copy DB file before a destructive migration. Returns backup path."""
    backup = db_path.with_suffix(f".bak{db_path.suffix}")
    shutil.copy2(db_path, backup)
    return backup


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Backwards-compatible alias for create_schema()."""
    create_schema(conn)


def record_match(
    conn: sqlite3.Connection,
    *,
    setup: MatchSetup,
    result: MatchResult,
    difficulty: str,
) -> int:
    setup_json = _json_dump(match_setup_to_dict(setup))
    box_score_json = _json_dump(result.box_score)
    cursor = conn.execute(
        """
        INSERT INTO matches (
            seed,
            config_version,
            winner_team_id,
            team_a_id,
            team_b_id,
            difficulty,
            setup_json,
            box_score_json,
            final_tick
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.seed,
            result.config_version,
            result.winner_team_id,
            setup.team_a.id,
            setup.team_b.id,
            difficulty,
            setup_json,
            box_score_json,
            result.final_tick,
        ),
    )
    match_id = cursor.lastrowid
    events_payload = [
        (match_id, idx, _json_dump(event.to_dict())) for idx, event in enumerate(result.events)
    ]
    conn.executemany(
        "INSERT INTO match_events (match_id, event_index, event_json) VALUES (?, ?, ?)",
        events_payload,
    )
    conn.commit()
    return int(match_id)


@dataclass(frozen=True)
class StoredMatchSummary:
    match_id: int
    seed: int
    winner_team_id: str | None
    difficulty: str
    team_a_id: str
    team_b_id: str
    config_version: str
    final_tick: int
    created_at: str


def list_recent_matches(conn: sqlite3.Connection, limit: int = 10) -> List[StoredMatchSummary]:
    cursor = conn.execute(
        """
        SELECT id, seed, winner_team_id, difficulty, team_a_id, team_b_id,
               config_version, final_tick, created_at
        FROM matches
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    summaries = []
    for row in cursor.fetchall():
        summaries.append(
            StoredMatchSummary(
                match_id=row["id"],
                seed=row["seed"],
                winner_team_id=row["winner_team_id"],
                difficulty=row["difficulty"],
                team_a_id=row["team_a_id"],
                team_b_id=row["team_b_id"],
                config_version=row["config_version"],
                final_tick=row["final_tick"],
                created_at=row["created_at"],
            )
        )
    return summaries


def fetch_match(conn: sqlite3.Connection, match_id: int) -> Dict[str, Any]:
    cursor = conn.execute(
        "SELECT * FROM matches WHERE id = ?",
        (match_id,)
    )
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"Match {match_id} not found")
    events_cursor = conn.execute(
        "SELECT event_json FROM match_events WHERE match_id = ? ORDER BY event_index ASC",
        (match_id,)
    )
    events = [json.loads(item[0]) for item in events_cursor.fetchall()]
    return {
        "match_id": row["id"],
        "seed": row["seed"],
        "config_version": row["config_version"],
        "winner_team_id": row["winner_team_id"],
        "team_a_id": row["team_a_id"],
        "team_b_id": row["team_b_id"],
        "difficulty": row["difficulty"],
        "final_tick": row["final_tick"],
        "created_at": row["created_at"],
        "setup": json.loads(row["setup_json"]),
        "box_score": json.loads(row["box_score_json"]),
        "events": events,
    }


def record_roster_snapshot(
    conn: sqlite3.Connection,
    *,
    match_id: str,
    club_id: str,
    players: List[Player],
    active_player_ids: Sequence[str] | None = None,
) -> None:
    """Persist a point-in-time player snapshot for replay and audit."""
    active_ids = set(active_player_ids or [])
    player_payload = []
    for player in players:
        payload = _player_to_dict(player)
        payload["match_role"] = "active" if player.id in active_ids else "bench"
        player_payload.append(payload)
    players_json = _json_dump(player_payload)
    conn.execute(
        """
        INSERT OR REPLACE INTO match_roster_snapshots (match_id, club_id, players_json)
        VALUES (?, ?, ?)
        """,
        (match_id, club_id, players_json),
    )
    conn.commit()


def fetch_roster_snapshot(
    conn: sqlite3.Connection,
    match_id: str,
    club_id: str,
) -> List[Dict[str, Any]]:
    """Return the stored player dicts for a match/club pair."""
    cursor = conn.execute(
        "SELECT players_json FROM match_roster_snapshots WHERE match_id = ? AND club_id = ?",
        (match_id, club_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"No roster snapshot for match={match_id} club={club_id}")
    return json.loads(row["players_json"])


# ---------------------------------------------------------------------------
# Dynasty persistence — clubs, rosters, seasons, matches, stats, awards
# ---------------------------------------------------------------------------

def save_club(conn: sqlite3.Connection, club: Club, roster: List[Player]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO clubs
            (club_id, name, colors, home_region, founded_year, coach_policy_json,
             primary_color, secondary_color, venue_name, tagline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            club.club_id, club.name, club.colors, club.home_region,
            club.founded_year, _json_dump(club.coach_policy.as_dict()),
            club.primary_color, club.secondary_color, club.venue_name, club.tagline,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO club_rosters (club_id, players_json) VALUES (?, ?)",
        (club.club_id, _json_dump([_player_to_dict(p) for p in roster])),
    )


def load_clubs(conn: sqlite3.Connection) -> Dict[str, "Club"]:
    cursor = conn.execute("SELECT * FROM clubs")
    clubs: Dict[str, Club] = {}
    for row in cursor.fetchall():
        cp_dict = json.loads(row["coach_policy_json"])
        keys = row.keys()
        clubs[row["club_id"]] = Club(
            club_id=row["club_id"],
            name=row["name"],
            colors=row["colors"],
            home_region=row["home_region"],
            founded_year=row["founded_year"],
            coach_policy=CoachPolicy(**{k: v for k, v in cp_dict.items() if k in CoachPolicy.__dataclass_fields__}),
            primary_color=row["primary_color"] if "primary_color" in keys else "",
            secondary_color=row["secondary_color"] if "secondary_color" in keys else "",
            venue_name=row["venue_name"] if "venue_name" in keys else "",
            tagline=row["tagline"] if "tagline" in keys else "",
        )
    return clubs


def load_club_roster(conn: sqlite3.Connection, club_id: str) -> List[Player]:
    cursor = conn.execute(
        "SELECT players_json FROM club_rosters WHERE club_id = ?", (club_id,)
    )
    row = cursor.fetchone()
    if row is None:
        raise KeyError(f"No roster for club {club_id}")
    try:
        payload = json.loads(row["players_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise CorruptSaveError(f"Corrupt roster JSON for club {club_id}") from exc
    return [_player_from_dict(d) for d in payload]


def load_all_rosters(conn: sqlite3.Connection) -> Dict[str, List[Player]]:
    cursor = conn.execute("SELECT club_id, players_json FROM club_rosters")
    rosters: Dict[str, List[Player]] = {}
    for row in cursor.fetchall():
        club_id = row["club_id"]
        try:
            payload = json.loads(row["players_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise CorruptSaveError(f"Corrupt roster JSON for club {club_id}") from exc
        rosters[club_id] = [_player_from_dict(d) for d in payload]
    return rosters


def save_lineup_default(
    conn: sqlite3.Connection,
    club_id: str,
    ordered_player_ids: List[str],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO lineup_default
            (club_id, ordered_player_ids_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (club_id, _json_dump(list(ordered_player_ids)), _utcnow_iso()),
    )


def load_lineup_default(
    conn: sqlite3.Connection,
    club_id: str,
) -> Optional[List[str]]:
    row = conn.execute(
        "SELECT ordered_player_ids_json FROM lineup_default WHERE club_id = ?",
        (club_id,),
    ).fetchone()
    if row is None:
        return None
    return list(json.loads(row["ordered_player_ids_json"]))


def save_match_lineup_override(
    conn: sqlite3.Connection,
    match_id: str,
    club_id: str,
    ordered_player_ids: List[str],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO match_lineup_override
            (match_id, club_id, ordered_player_ids_json)
        VALUES (?, ?, ?)
        """,
        (match_id, club_id, _json_dump(list(ordered_player_ids))),
    )


def load_match_lineup_override(
    conn: sqlite3.Connection,
    match_id: str,
    club_id: str,
) -> Optional[List[str]]:
    row = conn.execute(
        """
        SELECT ordered_player_ids_json FROM match_lineup_override
        WHERE match_id = ? AND club_id = ?
        """,
        (match_id, club_id),
    ).fetchone()
    if row is None:
        return None
    return list(json.loads(row["ordered_player_ids_json"]))


def save_season(conn: sqlite3.Connection, season: Season) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO seasons
            (season_id, year, league_id, config_version, ruleset_version)
        VALUES (?, ?, ?, ?, ?)
        """,
        (season.season_id, season.year, season.league_id,
         season.config_version, season.ruleset_version),
    )
    conn.executemany(
        """
        INSERT OR REPLACE INTO scheduled_matches
            (match_id, season_id, week, home_club_id, away_club_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (m.match_id, m.season_id, m.week, m.home_club_id, m.away_club_id)
            for m in season.scheduled_matches
        ],
    )


def save_scheduled_matches(conn: sqlite3.Connection, matches: Iterable[ScheduledMatch]) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO scheduled_matches
            (match_id, season_id, week, home_club_id, away_club_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (m.match_id, m.season_id, m.week, m.home_club_id, m.away_club_id)
            for m in matches
        ],
    )


def load_season(conn: sqlite3.Connection, season_id: str) -> Season:
    row = conn.execute(
        "SELECT * FROM seasons WHERE season_id = ?", (season_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"Season {season_id} not found")
    matches_cur = conn.execute(
        "SELECT * FROM scheduled_matches WHERE season_id = ? ORDER BY week, match_id",
        (season_id,),
    )
    scheduled = tuple(
        ScheduledMatch(
            match_id=m["match_id"],
            season_id=m["season_id"],
            week=m["week"],
            home_club_id=m["home_club_id"],
            away_club_id=m["away_club_id"],
        )
        for m in matches_cur.fetchall()
    )
    return Season(
        season_id=row["season_id"],
        year=row["year"],
        league_id=row["league_id"],
        config_version=row["config_version"],
        ruleset_version=row["ruleset_version"],
        scheduled_matches=scheduled,
    )


def save_match_result(
    conn: sqlite3.Connection,
    *,
    match_id: str,
    season_id: str,
    week: int,
    home_club_id: str,
    away_club_id: str,
    winner_club_id: Optional[str] = None,
    home_survivors: int = 0,
    away_survivors: int = 0,
    home_roster_hash: str,
    away_roster_hash: str,
    config_version: str,
    ruleset_version: str,
    meta_patch_id: Optional[str] = None,
    seed: int,
    event_log_hash: str,
    final_state_hash: str,
    engine_match_id: Optional[int] = None,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO match_records (
            match_id, season_id, week, home_club_id, away_club_id,
            winner_club_id, home_survivors, away_survivors,
            home_roster_hash, away_roster_hash, config_version, ruleset_version,
            meta_patch_id, seed, event_log_hash, final_state_hash, engine_match_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            match_id, season_id, week, home_club_id, away_club_id,
            winner_club_id, home_survivors, away_survivors,
            home_roster_hash, away_roster_hash, config_version, ruleset_version,
            meta_patch_id, seed, event_log_hash, final_state_hash, engine_match_id,
        ),
    )


def save_player_stats_batch(
    conn: sqlite3.Connection,
    match_id: str,
    stats: Dict[str, "PlayerMatchStats"],
    player_club_map: Dict[str, str],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO player_match_stats (
            match_id, player_id, club_id,
            throws_attempted, throws_on_target, eliminations_by_throw,
            catches_attempted, catches_made, times_targeted,
            dodges_successful, times_hit, times_eliminated,
            revivals_caused, clutch_events, elimination_plus_minus,
            minutes_played
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                match_id, pid, player_club_map.get(pid, ""),
                s.throws_attempted, s.throws_on_target, s.eliminations_by_throw,
                s.catches_attempted, s.catches_made, s.times_targeted,
                s.dodges_successful, s.times_hit, s.times_eliminated,
                s.revivals_caused, s.clutch_events, s.elimination_plus_minus,
                s.minutes_played,
            )
            for pid, s in stats.items()
        ],
    )


def save_standings(
    conn: sqlite3.Connection,
    season_id: str,
    standings: List["StandingsRow"],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO season_standings
            (season_id, club_id, wins, losses, draws, elimination_differential, points)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (season_id, r.club_id, r.wins, r.losses, r.draws,
             r.elimination_differential, r.points)
            for r in standings
        ],
    )


def load_standings(
    conn: sqlite3.Connection, season_id: str
) -> List["StandingsRow"]:
    cursor = conn.execute(
        """
        SELECT club_id, wins, losses, draws, elimination_differential, points
        FROM season_standings WHERE season_id = ?
        ORDER BY points DESC, elimination_differential DESC, club_id ASC
        """,
        (season_id,),
    )
    return [
        StandingsRow(
            club_id=row["club_id"],
            wins=row["wins"],
            losses=row["losses"],
            draws=row["draws"],
            elimination_differential=row["elimination_differential"],
            points=row["points"],
        )
        for row in cursor.fetchall()
    ]


def save_awards(conn: sqlite3.Connection, awards: List["SeasonAward"]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO season_awards
            (season_id, award_type, player_id, club_id, award_score)
        VALUES (?, ?, ?, ?, ?)
        """,
        [(a.season_id, a.award_type, a.player_id, a.club_id, a.award_score) for a in awards],
    )


def load_awards(conn: sqlite3.Connection, season_id: str) -> List["SeasonAward"]:
    cursor = conn.execute(
        "SELECT * FROM season_awards WHERE season_id = ?", (season_id,)
    )
    return [
        SeasonAward(
            season_id=row["season_id"],
            award_type=row["award_type"],
            player_id=row["player_id"],
            club_id=row["club_id"],
            award_score=row["award_score"],
        )
        for row in cursor.fetchall()
    ]


def load_completed_match_ids(
    conn: sqlite3.Connection, season_id: str
) -> "set[str]":
    cursor = conn.execute(
        "SELECT match_id FROM match_records WHERE season_id = ?", (season_id,)
    )
    return {row["match_id"] for row in cursor.fetchall()}


def fetch_season_player_stats(
    conn: sqlite3.Connection, season_id: str
) -> Dict[str, "PlayerMatchStats"]:
    """Aggregate player stats across all completed matches in a season."""
    cursor = conn.execute(
        """
        SELECT player_id,
            SUM(throws_attempted) AS throws_attempted,
            SUM(throws_on_target) AS throws_on_target,
            SUM(eliminations_by_throw) AS eliminations_by_throw,
            SUM(catches_attempted) AS catches_attempted,
            SUM(catches_made) AS catches_made,
            SUM(times_targeted) AS times_targeted,
            SUM(dodges_successful) AS dodges_successful,
            SUM(times_hit) AS times_hit,
            SUM(times_eliminated) AS times_eliminated,
            SUM(revivals_caused) AS revivals_caused,
            SUM(clutch_events) AS clutch_events,
            SUM(elimination_plus_minus) AS elimination_plus_minus,
            SUM(minutes_played) AS minutes_played
        FROM player_match_stats
        WHERE match_id IN (
            SELECT match_id FROM match_records WHERE season_id = ?
        )
        GROUP BY player_id
        """,
        (season_id,),
    )
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
        for row in cursor.fetchall()
    }


def save_player_season_stats(
    conn: sqlite3.Connection,
    season_id: str,
    player_season_stats: Dict[str, "PlayerMatchStats"],
    player_club_map: Dict[str, str],
    matches_by_player: Dict[str, int],
    newcomer_player_ids: "set[str] | frozenset[str]",
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO player_season_stats (
            player_id, season_id, club_id, matches,
            total_throws_attempted, total_eliminations, total_catches_made,
            total_dodges_successful, total_times_eliminated, newcomer
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                player_id,
                season_id,
                player_club_map.get(player_id),
                matches_by_player.get(player_id, 0),
                stats.throws_attempted,
                stats.eliminations_by_throw,
                stats.catches_made,
                stats.dodges_successful,
                stats.times_eliminated,
                1 if player_id in newcomer_player_ids else 0,
            )
            for player_id, stats in player_season_stats.items()
        ],
    )


def fetch_player_career_summary(
    conn: sqlite3.Connection,
    player_id: str,
) -> Dict[str, float]:
    row = conn.execute(
        """
        SELECT
            COUNT(*) AS seasons_played,
            COALESCE(SUM(total_eliminations), 0) AS total_eliminations,
            COALESCE(SUM(total_catches_made), 0) AS total_catches_made,
            COALESCE(SUM(total_dodges_successful), 0) AS total_dodges_successful,
            COALESCE(SUM(total_times_eliminated), 0) AS total_times_eliminated
        FROM player_season_stats
        WHERE player_id = ?
        """,
        (player_id,),
    ).fetchone()
    recent_row = conn.execute(
        """
        SELECT total_eliminations
        FROM player_season_stats
        WHERE player_id = ?
        ORDER BY season_id DESC
        LIMIT 1
        """,
        (player_id,),
    ).fetchone()
    return {
        "seasons_played": float(row["seasons_played"] if row else 0),
        "total_eliminations": float(row["total_eliminations"] if row else 0),
        "total_catches_made": float(row["total_catches_made"] if row else 0),
        "total_dodges_successful": float(row["total_dodges_successful"] if row else 0),
        "total_times_eliminated": float(row["total_times_eliminated"] if row else 0),
        "recent_eliminations": float(recent_row["total_eliminations"] if recent_row else 0),
    }


def save_free_agents(
    conn: sqlite3.Connection,
    players: List[Player],
    available_since_season: str,
) -> None:
    conn.execute("DELETE FROM free_agents")
    conn.executemany(
        """
        INSERT INTO free_agents (player_id, available_since_season, player_json)
        VALUES (?, ?, ?)
        """,
        [
            (player.id, available_since_season, _json_dump(_player_to_dict(player)))
            for player in players
        ],
    )


def load_free_agents(conn: sqlite3.Connection) -> List[Player]:
    cursor = conn.execute(
        "SELECT player_json FROM free_agents ORDER BY available_since_season, player_id"
    )
    return [_player_from_dict(json.loads(row["player_json"])) for row in cursor.fetchall()]


def save_retired_player(
    conn: sqlite3.Connection,
    player: Player,
    final_season: str,
    retirement_reason: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO retired_players (
            player_id, final_season, retirement_reason, age_at_retirement, player_json
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            player.id,
            final_season,
            retirement_reason,
            player.age,
            _json_dump(_player_to_dict(player)),
        ),
    )


def load_retired_players(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT player_id, final_season, retirement_reason, age_at_retirement, player_json
        FROM retired_players
        ORDER BY final_season, player_id
        """
    )
    return [
        {
            "player_id": row["player_id"],
            "final_season": row["final_season"],
            "retirement_reason": row["retirement_reason"],
            "age_at_retirement": row["age_at_retirement"],
            "player": _player_from_dict(json.loads(row["player_json"])),
        }
        for row in cursor.fetchall()
    ]


def save_player_identity(
    conn: sqlite3.Connection,
    player_id: str,
    nickname: str,
    archetype: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO player_identity (player_id, nickname, archetype)
        VALUES (?, ?, ?)
        """,
        (player_id, nickname, archetype),
    )


def load_player_identity(conn: sqlite3.Connection, player_id: str) -> Dict[str, str] | None:
    row = conn.execute(
        "SELECT player_id, nickname, archetype FROM player_identity WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "player_id": row["player_id"],
        "nickname": row["nickname"],
        "archetype": row["archetype"],
    }


def save_player_career_stats(
    conn: sqlite3.Connection,
    player_id: str,
    career_summary: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO player_career_stats (
            player_id, career_eliminations, career_catches, career_dodges,
            seasons_played, championships, clubs_served, career_summary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            player_id,
            int(career_summary.get("career_eliminations", 0)),
            int(career_summary.get("career_catches", 0)),
            int(career_summary.get("career_dodges", 0)),
            int(career_summary.get("seasons_played", 0)),
            int(career_summary.get("championships", 0)),
            int(career_summary.get("clubs_served", 0)),
            _json_dump(career_summary),
        ),
    )


def load_player_career_stats(conn: sqlite3.Connection, player_id: str) -> Dict[str, Any] | None:
    row = conn.execute(
        "SELECT career_summary_json FROM player_career_stats WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    return json.loads(row["career_summary_json"]) if row else None


def save_signature_moment(
    conn: sqlite3.Connection,
    moment_id: str,
    player_id: str,
    season_id: str,
    match_id: Optional[str],
    moment_type: str,
    description: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO signature_moments (
            moment_id, player_id, season_id, match_id, moment_type, description
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (moment_id, player_id, season_id, match_id, moment_type, description),
    )


def load_signature_moments(conn: sqlite3.Connection, player_id: str) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT moment_id, player_id, season_id, match_id, moment_type, description
        FROM signature_moments
        WHERE player_id = ?
        ORDER BY season_id, moment_id
        """,
        (player_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def save_hall_of_fame_entry(
    conn: sqlite3.Connection,
    player_id: str,
    induction_season: str,
    career_summary: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO hall_of_fame (player_id, induction_season, career_summary_json)
        VALUES (?, ?, ?)
        """,
        (player_id, induction_season, _json_dump(career_summary)),
    )


def load_hall_of_fame(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT player_id, induction_season, career_summary_json
        FROM hall_of_fame
        ORDER BY induction_season, player_id
        """
    )
    return [
        {
            "player_id": row["player_id"],
            "induction_season": row["induction_season"],
            "career_summary": json.loads(row["career_summary_json"]),
        }
        for row in cursor.fetchall()
    ]


def save_rivalry_record(
    conn: sqlite3.Connection,
    club_a_id: str,
    club_b_id: str,
    rivalry_summary: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO rivalry_records (
            club_a_id, club_b_id, a_wins, b_wins, draws,
            rivalry_score, last_meeting_season, rivalry_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            club_a_id,
            club_b_id,
            int(rivalry_summary.get("a_wins", 0)),
            int(rivalry_summary.get("b_wins", 0)),
            int(rivalry_summary.get("draws", 0)),
            float(rivalry_summary.get("rivalry_score", 0.0)),
            rivalry_summary.get("last_meeting_season"),
            _json_dump(rivalry_summary),
        ),
    )


def load_rivalry_records(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT club_a_id, club_b_id, rivalry_json
        FROM rivalry_records
        ORDER BY rivalry_score DESC, club_a_id, club_b_id
        """
    )
    return [
        {
            "club_a_id": row["club_a_id"],
            "club_b_id": row["club_b_id"],
            "rivalry": json.loads(row["rivalry_json"]),
        }
        for row in cursor.fetchall()
    ]


def save_league_record(
    conn: sqlite3.Connection,
    record_type: str,
    holder_id: str,
    holder_type: str,
    record_value: float,
    set_in_season: str,
    record_payload: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO league_records (
            record_type, holder_id, holder_type, record_value, set_in_season, record_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (record_type, holder_id, holder_type, record_value, set_in_season, _json_dump(record_payload)),
    )


def load_league_records(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT record_type, holder_id, holder_type, record_value, set_in_season, record_json
        FROM league_records
        ORDER BY record_type
        """
    )
    return [
        {
            "record_type": row["record_type"],
            "holder_id": row["holder_id"],
            "holder_type": row["holder_type"],
            "record_value": row["record_value"],
            "set_in_season": row["set_in_season"],
            "record": json.loads(row["record_json"]),
        }
        for row in cursor.fetchall()
    ]


def save_news_headlines(
    conn: sqlite3.Connection,
    season_id: str,
    week: int,
    headlines: List[Dict[str, Any]],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO news_headlines (
            headline_id, season_id, week, category, headline_text, entity_ids_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                headline["headline_id"],
                season_id,
                week,
                headline["category"],
                headline["headline_text"],
                _json_dump(headline.get("entity_ids", [])),
            )
            for headline in headlines
        ],
    )


def load_news_headlines(
    conn: sqlite3.Connection,
    season_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if season_id is None:
        cursor = conn.execute(
            """
            SELECT headline_id, season_id, week, category, headline_text, entity_ids_json
            FROM news_headlines
            ORDER BY season_id DESC, week DESC, headline_id
            """
        )
    else:
        cursor = conn.execute(
            """
            SELECT headline_id, season_id, week, category, headline_text, entity_ids_json
            FROM news_headlines
            WHERE season_id = ?
            ORDER BY week DESC, headline_id
            """,
            (season_id,),
        )
    return [
        {
            "headline_id": row["headline_id"],
            "season_id": row["season_id"],
            "week": row["week"],
            "category": row["category"],
            "headline_text": row["headline_text"],
            "entity_ids": json.loads(row["entity_ids_json"]),
        }
        for row in cursor.fetchall()
    ]


def save_club_facilities(
    conn: sqlite3.Connection,
    club_id: str,
    season_id: str,
    facilities: List[str],
) -> None:
    conn.execute(
        "DELETE FROM club_facilities WHERE club_id = ? AND season_id = ?",
        (club_id, season_id),
    )
    conn.executemany(
        """
        INSERT INTO club_facilities (club_id, season_id, facility_type)
        VALUES (?, ?, ?)
        """,
        [(club_id, season_id, facility) for facility in facilities],
    )


def load_club_facilities(
    conn: sqlite3.Connection,
    club_id: str,
    season_id: str,
) -> List[str]:
    cursor = conn.execute(
        """
        SELECT facility_type
        FROM club_facilities
        WHERE club_id = ? AND season_id = ?
        ORDER BY facility_type
        """,
        (club_id, season_id),
    )
    return [row["facility_type"] for row in cursor.fetchall()]


def save_club_prestige(conn: sqlite3.Connection, club_id: str, prestige_score: int) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO club_prestige (club_id, prestige_score)
        VALUES (?, ?)
        """,
        (club_id, prestige_score),
    )


def load_club_prestige(conn: sqlite3.Connection, club_id: str) -> int:
    row = conn.execute(
        "SELECT prestige_score FROM club_prestige WHERE club_id = ?",
        (club_id,),
    ).fetchone()
    return int(row["prestige_score"]) if row else 0


def save_meta_patch(
    conn: sqlite3.Connection,
    season_id: str,
    patch_id: str,
    name: str,
    description: str,
    modifiers: Dict[str, Any],
    ruleset_overrides: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO meta_patches (
            patch_id, season_id, name, description, modifiers_json, ruleset_overrides_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            patch_id,
            season_id,
            name,
            description,
            _json_dump(modifiers),
            _json_dump(ruleset_overrides),
        ),
    )


def load_meta_patch(conn: sqlite3.Connection, season_id: str) -> Dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT patch_id, season_id, name, description, modifiers_json, ruleset_overrides_json
        FROM meta_patches
        WHERE season_id = ?
        """,
        (season_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "patch_id": row["patch_id"],
        "season_id": row["season_id"],
        "name": row["name"],
        "description": row["description"],
        "modifiers": json.loads(row["modifiers_json"]),
        "ruleset_overrides": json.loads(row["ruleset_overrides_json"]),
    }


def load_all_meta_patches(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT patch_id, season_id, name, description, modifiers_json, ruleset_overrides_json
        FROM meta_patches
        ORDER BY season_id
        """
    )
    return [
        {
            "patch_id": row["patch_id"],
            "season_id": row["season_id"],
            "name": row["name"],
            "description": row["description"],
            "modifiers": json.loads(row["modifiers_json"]),
            "ruleset_overrides": json.loads(row["ruleset_overrides_json"]),
        }
        for row in cursor.fetchall()
    ]


def save_cup_bracket(
    conn: sqlite3.Connection,
    cup_id: str,
    season_id: str,
    bracket_payload: Dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO cup_brackets (cup_id, season_id, bracket_json)
        VALUES (?, ?, ?)
        """,
        (cup_id, season_id, _json_dump(bracket_payload)),
    )


def load_cup_bracket(conn: sqlite3.Connection, season_id: str) -> Dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT cup_id, season_id, bracket_json
        FROM cup_brackets
        WHERE season_id = ?
        """,
        (season_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "cup_id": row["cup_id"],
        "season_id": row["season_id"],
        "bracket": json.loads(row["bracket_json"]),
    }


def save_cup_result(
    conn: sqlite3.Connection,
    cup_id: str,
    round_number: int,
    match_id: str,
    winner_club_id: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO cup_results (cup_id, round_number, match_id, winner_club_id)
        VALUES (?, ?, ?, ?)
        """,
        (cup_id, round_number, match_id, winner_club_id),
    )


def load_cup_results(conn: sqlite3.Connection, season_id: str) -> Dict[str, str]:
    cursor = conn.execute(
        """
        SELECT r.match_id, r.winner_club_id
        FROM cup_results r
        JOIN cup_brackets b ON b.cup_id = r.cup_id
        WHERE b.season_id = ?
        """,
        (season_id,),
    )
    return {row["match_id"]: row["winner_club_id"] for row in cursor.fetchall()}


def save_club_trophy(
    conn: sqlite3.Connection,
    club_id: str,
    trophy_type: str,
    season_id: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO club_trophies (club_id, trophy_type, season_id)
        VALUES (?, ?, ?)
        """,
        (club_id, trophy_type, season_id),
    )


def load_club_trophies(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.execute(
        """
        SELECT club_id, trophy_type, season_id
        FROM club_trophies
        ORDER BY season_id, club_id, trophy_type
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def load_department_heads(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT department, name, rating_primary, rating_secondary, voice
        FROM department_heads
        ORDER BY department
        """
    ).fetchall()
    return [
        {
            "department": row["department"],
            "name": row["name"],
            "rating_primary": float(row["rating_primary"]),
            "rating_secondary": float(row["rating_secondary"]),
            "voice": row["voice"],
        }
        for row in rows
    ]


def save_weekly_command_plan(conn: sqlite3.Connection, plan: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO weekly_command_plans
            (season_id, week, club_id, intent, plan_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            plan["season_id"],
            int(plan["week"]),
            plan["player_club_id"],
            plan["intent"],
            _json_dump(plan),
            _utcnow_iso(),
        ),
    )


def load_weekly_command_plan(
    conn: sqlite3.Connection,
    season_id: str,
    week: int,
    club_id: str,
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        """
        SELECT plan_json FROM weekly_command_plans
        WHERE season_id = ? AND week = ? AND club_id = ?
        """,
        (season_id, int(week), club_id),
    ).fetchone()
    return json.loads(row["plan_json"]) if row else None


def save_command_history_record(conn: sqlite3.Connection, record: Dict[str, Any]) -> None:
    plan = dict(record["plan"])
    dashboard = dict(record["dashboard"])
    conn.execute(
        """
        INSERT INTO command_history
            (season_id, week, club_id, match_id, opponent_club_id, intent, plan_json, dashboard_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["season_id"],
            int(record["week"]),
            plan["player_club_id"],
            record.get("match_id"),
            record.get("opponent_club_id"),
            record["intent"],
            _json_dump(plan),
            _json_dump(dashboard),
        ),
    )


def load_command_history(conn: sqlite3.Connection, season_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM command_history
        WHERE season_id = ?
        ORDER BY week, history_id
        """,
        (season_id,),
    ).fetchall()
    return [
        {
            "history_id": int(row["history_id"]),
            "season_id": row["season_id"],
            "week": int(row["week"]),
            "club_id": row["club_id"],
            "match_id": row["match_id"],
            "opponent_club_id": row["opponent_club_id"],
            "intent": row["intent"],
            "plan": json.loads(row["plan_json"]),
            "dashboard": json.loads(row["dashboard_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_state(
    conn: sqlite3.Connection, key: str, default: Optional[str] = None
) -> Optional[str]:
    cursor = conn.execute(
        "SELECT value FROM dynasty_state WHERE key = ?", (key,)
    )
    row = cursor.fetchone()
    return row["value"] if row else default


def set_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO dynasty_state (key, value) VALUES (?, ?)",
        (key, value),
    )


def load_json_state(conn: sqlite3.Connection, key: str, default: Any) -> Any:
    raw = get_state(conn, key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CorruptSaveError(f"Corrupt JSON for state {key}") from exc


_CAREER_STATE_KEY = "career_state_cursor"


def save_career_state_cursor(conn: sqlite3.Connection, cursor: "CareerStateCursor") -> None:
    """Persist the career state cursor in the dynasty_state KV table."""
    payload = {
        "state": cursor.state.value,
        "season_number": cursor.season_number,
        "week": cursor.week,
        "offseason_beat_index": cursor.offseason_beat_index,
        "match_id": cursor.match_id,
    }
    conn.execute(
        "INSERT OR REPLACE INTO dynasty_state (key, value) VALUES (?, ?)",
        (_CAREER_STATE_KEY, _json_dump(payload)),
    )


def load_career_state_cursor(conn: sqlite3.Connection) -> "CareerStateCursor":
    """Load the career cursor, defaulting to SPLASH for a fresh DB."""
    from .career_state import CareerState, CareerStateCursor

    row = conn.execute(
        "SELECT value FROM dynasty_state WHERE key = ?",
        (_CAREER_STATE_KEY,),
    ).fetchone()
    if row is None:
        return CareerStateCursor(state=CareerState.SPLASH)
    try:
        payload = json.loads(row["value"])
        state = CareerState(payload["state"])
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return CareerStateCursor(state=CareerState.SPLASH)

    def non_negative_int(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0

    return CareerStateCursor(
        state=state,
        season_number=non_negative_int(payload.get("season_number", 0)),
        week=non_negative_int(payload.get("week", 0)),
        offseason_beat_index=min(
            _MAX_OFFSEASON_BEAT_INDEX,
            non_negative_int(payload.get("offseason_beat_index", 0)),
        ),
        match_id=payload.get("match_id"),
    )


# ---------------------------------------------------------------------------
# V2-A scouting persistence
# ---------------------------------------------------------------------------

from .scouting_center import (  # noqa: E402
    DEFAULT_SCOUT_PROFILES,
    Prospect,
    Scout,
    ScoutAssignment,
    ScoutContribution,
    ScoutMode,
    ScoutPriority,
    ScoutStrategyState,
    ScoutingState,
)


def save_prospect_pool(conn: sqlite3.Connection, prospects: Iterable[Prospect]) -> None:
    rows = [
        (
            p.class_year,
            p.player_id,
            p.name,
            p.age,
            p.hometown,
            p.true_archetype(),
            _json_dump(p.hidden_ratings),
            p.hidden_trajectory,
            _json_dump(list(p.hidden_traits)),
            p.public_archetype_guess,
            _json_dump({key: list(value) for key, value in p.public_ratings_band.items()}),
            0,
        )
        for p in prospects
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO prospect_pool (
            class_year, player_id, name, age, hometown, archetype, hidden_ratings_json,
            hidden_trajectory, hidden_traits_json, public_archetype_guess,
            public_ratings_band_json, is_signed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def load_prospect_pool(conn: sqlite3.Connection, class_year: int) -> List[Prospect]:
    rows = conn.execute(
        "SELECT * FROM prospect_pool WHERE class_year = ? ORDER BY player_id",
        (class_year,),
    ).fetchall()
    result: List[Prospect] = []
    for row in rows:
        band_raw = json.loads(row["public_ratings_band_json"])
        result.append(
            Prospect(
                player_id=row["player_id"],
                class_year=row["class_year"],
                name=row["name"] or row["player_id"],
                age=row["age"],
                hometown=row["hometown"],
                hidden_ratings=json.loads(row["hidden_ratings_json"]),
                hidden_trajectory=row["hidden_trajectory"],
                hidden_traits=list(json.loads(row["hidden_traits_json"])),
                public_archetype_guess=row["public_archetype_guess"],
                public_ratings_band={key: tuple(value) for key, value in band_raw.items()},
            )
        )
    return result


def mark_prospect_signed(conn: sqlite3.Connection, class_year: int, player_id: str) -> None:
    cursor = conn.execute(
        """
        UPDATE prospect_pool
        SET is_signed = 1
        WHERE class_year = ? AND player_id = ? AND is_signed = 0
        """,
        (class_year, player_id),
    )
    if cursor.rowcount != 1:
        raise ValueError(f"Prospect {player_id} is already signed or missing")
    conn.commit()


def save_scout(conn: sqlite3.Connection, scout: Scout) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO scout (
            scout_id, name, base_accuracy, archetype_affinities_json,
            archetype_weakness, trait_sense
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            scout.scout_id,
            scout.name,
            scout.base_accuracy,
            _json_dump(list(scout.archetype_affinities)),
            scout.archetype_weakness,
            scout.trait_sense,
        ),
    )
    conn.commit()


def load_scouts(conn: sqlite3.Connection) -> List[Scout]:
    rows = conn.execute("SELECT * FROM scout ORDER BY scout_id").fetchall()
    return [
        Scout(
            scout_id=row["scout_id"],
            name=row["name"],
            base_accuracy=row["base_accuracy"],
            archetype_affinities=tuple(json.loads(row["archetype_affinities_json"])),
            archetype_weakness=row["archetype_weakness"],
            trait_sense=row["trait_sense"],
        )
        for row in rows
    ]


def seed_default_scouts(conn: sqlite3.Connection) -> None:
    if get_state(conn, "scouts_seeded_for_career") == "1":
        return
    for profile in DEFAULT_SCOUT_PROFILES:
        save_scout(
            conn,
            Scout(
                scout_id=profile.scout_id,
                name=profile.name,
                base_accuracy=profile.base_accuracy,
                archetype_affinities=profile.archetype_affinities,
                archetype_weakness=profile.archetype_weakness,
                trait_sense=profile.trait_sense,
            ),
        )
        save_scout_strategy(conn, ScoutStrategyState(profile.scout_id, "MANUAL", "TOP_PUBLIC_OVR", (), ()))
        save_scout_assignment(conn, ScoutAssignment(profile.scout_id, None, 0))
    set_state(conn, "scouts_seeded_for_career", "1")
    conn.commit()


def save_scouting_state(conn: sqlite3.Connection, state: ScoutingState) -> None:
    rows = [
        (state.player_id, axis, getattr(state, f"{axis}_tier"), state.scout_points.get(axis, 0), state.last_updated_week)
        for axis in ("ratings", "archetype", "traits", "trajectory")
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO scouting_state
            (player_id, axis, tier, scout_points, last_updated_week)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def load_scouting_state(conn: sqlite3.Connection, player_id: str) -> Optional[ScoutingState]:
    rows = conn.execute("SELECT * FROM scouting_state WHERE player_id = ?", (player_id,)).fetchall()
    if not rows:
        return None
    by_axis = {row["axis"]: row for row in rows}

    def tier(axis: str) -> str:
        return by_axis[axis]["tier"] if axis in by_axis else "UNKNOWN"

    return ScoutingState(
        player_id=player_id,
        ratings_tier=tier("ratings"),
        archetype_tier=tier("archetype"),
        traits_tier=tier("traits"),
        trajectory_tier=tier("trajectory"),
        scout_points={
            axis: by_axis[axis]["scout_points"] if axis in by_axis else 0
            for axis in ("ratings", "archetype", "traits", "trajectory")
        },
        last_updated_week=max(row["last_updated_week"] for row in rows),
    )


def load_all_scouting_states(conn: sqlite3.Connection) -> Dict[str, ScoutingState]:
    rows = conn.execute("SELECT DISTINCT player_id FROM scouting_state").fetchall()
    result: Dict[str, ScoutingState] = {}
    for row in rows:
        state = load_scouting_state(conn, row["player_id"])
        if state is not None:
            result[row["player_id"]] = state
    return result


def save_scout_assignment(conn: sqlite3.Connection, assignment: ScoutAssignment) -> None:
    player_id = assignment.player_id
    if player_id:
        row = conn.execute(
            "SELECT 1 FROM prospect_pool WHERE player_id = ? LIMIT 1",
            (player_id,),
        ).fetchone()
        if row is None:
            player_id = None
    conn.execute(
        "INSERT OR REPLACE INTO scout_assignment (scout_id, player_id, started_week) VALUES (?, ?, ?)",
        (assignment.scout_id, player_id, max(0, int(assignment.started_week or 0))),
    )
    conn.commit()


def load_scout_assignment(conn: sqlite3.Connection, scout_id: str) -> Optional[ScoutAssignment]:
    row = conn.execute("SELECT * FROM scout_assignment WHERE scout_id = ?", (scout_id,)).fetchone()
    if row is None:
        return None
    return ScoutAssignment(row["scout_id"], row["player_id"], row["started_week"])


def load_all_scout_assignments(conn: sqlite3.Connection) -> Dict[str, ScoutAssignment]:
    rows = conn.execute("SELECT * FROM scout_assignment").fetchall()
    return {row["scout_id"]: ScoutAssignment(row["scout_id"], row["player_id"], row["started_week"]) for row in rows}


def save_scout_strategy(conn: sqlite3.Connection, strategy: ScoutStrategyState) -> None:
    mode = strategy.mode if strategy.mode in {ScoutMode.MANUAL.value, ScoutMode.AUTO.value} else ScoutMode.MANUAL.value
    priority = (
        strategy.priority
        if strategy.priority in {ScoutPriority.TOP_PUBLIC_OVR.value, ScoutPriority.SPECIALTY_FIT.value}
        else ScoutPriority.TOP_PUBLIC_OVR.value
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO scout_strategy (
            scout_id, mode, priority, archetype_filter_json, pinned_prospects_json
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            strategy.scout_id,
            mode,
            priority,
            _json_dump(list(strategy.archetype_filter)),
            _json_dump(list(strategy.pinned_prospects)),
        ),
    )
    conn.commit()


def load_scout_strategy(conn: sqlite3.Connection, scout_id: str) -> Optional[ScoutStrategyState]:
    row = conn.execute("SELECT * FROM scout_strategy WHERE scout_id = ?", (scout_id,)).fetchone()
    if row is None:
        return None
    return ScoutStrategyState(
        scout_id=row["scout_id"],
        mode=row["mode"],
        priority=row["priority"],
        archetype_filter=tuple(json.loads(row["archetype_filter_json"])),
        pinned_prospects=tuple(json.loads(row["pinned_prospects_json"])),
    )


def upsert_scout_contribution(conn: sqlite3.Connection, contribution: ScoutContribution) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO scout_prospect_contribution (
            scout_id, player_id, season, first_assigned_week, last_active_week,
            weeks_worked, contributed_scout_points_json,
            last_estimated_ratings_band_json, last_estimated_archetype,
            last_estimated_traits_json, last_estimated_ceiling,
            last_estimated_trajectory
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            contribution.scout_id,
            contribution.player_id,
            contribution.season,
            contribution.first_assigned_week,
            contribution.last_active_week,
            contribution.weeks_worked,
            _json_dump(contribution.contributed_scout_points),
            _json_dump({key: list(value) for key, value in contribution.last_estimated_ratings_band.items()}),
            contribution.last_estimated_archetype,
            _json_dump(list(contribution.last_estimated_traits)),
            contribution.last_estimated_ceiling,
            contribution.last_estimated_trajectory,
        ),
    )
    conn.commit()


def load_scout_contributions_for_season(conn: sqlite3.Connection, season: int) -> List[ScoutContribution]:
    rows = conn.execute(
        "SELECT * FROM scout_prospect_contribution WHERE season = ? ORDER BY scout_id, player_id",
        (season,),
    ).fetchall()
    result: List[ScoutContribution] = []
    for row in rows:
        band_raw = json.loads(row["last_estimated_ratings_band_json"] or "{}")
        result.append(
            ScoutContribution(
                scout_id=row["scout_id"],
                player_id=row["player_id"],
                season=row["season"],
                first_assigned_week=row["first_assigned_week"],
                last_active_week=row["last_active_week"],
                weeks_worked=row["weeks_worked"],
                contributed_scout_points=json.loads(row["contributed_scout_points_json"]),
                last_estimated_ratings_band={key: tuple(value) for key, value in band_raw.items()},
                last_estimated_archetype=row["last_estimated_archetype"],
                last_estimated_traits=tuple(json.loads(row["last_estimated_traits_json"] or "[]")),
                last_estimated_ceiling=row["last_estimated_ceiling"],
                last_estimated_trajectory=row["last_estimated_trajectory"],
            )
        )
    return result


def append_scouting_domain_event(
    conn: sqlite3.Connection,
    season: int,
    week: int,
    event_type: str,
    player_id: Optional[str],
    scout_id: Optional[str],
    payload: Dict[str, Any],
) -> None:
    count = conn.execute("SELECT COUNT(*) AS n FROM scouting_domain_event").fetchone()["n"]
    event_id = f"scouting_{season}_{week}_{count + 1:04d}"
    conn.execute(
        """
        INSERT INTO scouting_domain_event
            (event_id, season, week, event_type, player_id, scout_id, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, season, week, event_type, player_id, scout_id, _json_dump(payload)),
    )
    conn.commit()


def load_scouting_domain_events_for_season(conn: sqlite3.Connection, season: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM scouting_domain_event WHERE season = ? ORDER BY week, event_id",
        (season,),
    ).fetchall()
    return [
        {
            "event_id": row["event_id"],
            "season": row["season"],
            "week": row["week"],
            "event_type": row["event_type"],
            "player_id": row["player_id"],
            "scout_id": row["scout_id"],
            "payload": json.loads(row["payload_json"]),
        }
        for row in rows
    ]


def save_revealed_traits(
    conn: sqlite3.Connection,
    player_id: str,
    trait_ids: Iterable[str],
    revealed_at_week: int,
) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO scouting_revealed_traits
            (player_id, trait_id, revealed_at_week)
        VALUES (?, ?, ?)
        """,
        [(player_id, trait_id, revealed_at_week) for trait_id in trait_ids],
    )
    conn.commit()


def load_revealed_traits(conn: sqlite3.Connection, player_id: str) -> Tuple[str, ...]:
    rows = conn.execute(
        """
        SELECT trait_id FROM scouting_revealed_traits
        WHERE player_id = ?
        ORDER BY revealed_at_week, trait_id
        """,
        (player_id,),
    ).fetchall()
    return tuple(row["trait_id"] for row in rows)


def save_ceiling_label(
    conn: sqlite3.Connection,
    player_id: str,
    label: str,
    revealed_at_week: int,
    revealed_by_scout_id: Optional[str],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO scouting_ceiling_label
            (player_id, label, revealed_at_week, revealed_by_scout_id)
        VALUES (?, ?, ?, ?)
        """,
        (player_id, label, revealed_at_week, revealed_by_scout_id),
    )
    conn.commit()


def load_ceiling_label(conn: sqlite3.Connection, player_id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM scouting_ceiling_label WHERE player_id = ?", (player_id,)).fetchone()
    return dict(row) if row is not None else None


def save_scout_track_record(
    conn: sqlite3.Connection,
    scout_id: str,
    player_id: str,
    season: int,
    predicted_ovr_band: Optional[Tuple[int, int]],
    actual_ovr: Optional[int],
    predicted_archetype: Optional[str],
    actual_archetype: Optional[str],
    predicted_trajectory: Optional[str],
    actual_trajectory: Optional[str],
    predicted_ceiling: Optional[str],
    actual_ceiling: Optional[str],
) -> None:
    predicted_mid = None
    error = None
    if predicted_ovr_band is not None:
        predicted_mid = sum(predicted_ovr_band) / 2.0
        if actual_ovr is not None:
            error = abs(predicted_mid - actual_ovr)
    conn.execute(
        """
        INSERT OR REPLACE INTO scout_track_record (
            season, scout_id, player_id, predicted_ovr_mid, actual_ovr,
            ovr_error, predicted_archetype, actual_archetype,
            predicted_trajectory, actual_trajectory, ceiling_label,
            signed_by_user
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            season,
            scout_id,
            player_id,
            predicted_mid,
            actual_ovr if actual_ovr is not None else 0,
            error,
            predicted_archetype,
            actual_archetype or "",
            predicted_trajectory,
            actual_trajectory or "",
            predicted_ceiling or actual_ceiling,
            0,
        ),
    )
    conn.commit()


def load_scout_track_records_for_scout(conn: sqlite3.Connection, scout_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM scout_track_record WHERE scout_id = ? ORDER BY season, player_id",
        (scout_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def save_player_trajectory(conn: sqlite3.Connection, player_id: str, trajectory: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO player_trajectory (player_id, trajectory) VALUES (?, ?)",
        (player_id, trajectory),
    )
    conn.commit()


def load_player_trajectory(conn: sqlite3.Connection, player_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT trajectory FROM player_trajectory WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    return row["trajectory"] if row else None


def save_season_format(conn: sqlite3.Connection, season_id: str, season_format: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO season_formats (season_id, format) VALUES (?, ?)",
        (season_id, season_format),
    )


def load_season_format(conn: sqlite3.Connection, season_id: str) -> Optional[str]:
    row = conn.execute(
        "SELECT format FROM season_formats WHERE season_id = ?",
        (season_id,),
    ).fetchone()
    return row["format"] if row else None


def save_playoff_bracket(conn: sqlite3.Connection, bracket: "PlayoffBracket") -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO playoff_brackets
            (season_id, format, seeds_json, rounds_json, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            bracket.season_id,
            bracket.format,
            _json_dump(list(bracket.seeds)),
            _json_dump(list(bracket.rounds)),
            bracket.status,
        ),
    )


def load_playoff_bracket(conn: sqlite3.Connection, season_id: str) -> Optional["PlayoffBracket"]:
    from .playoffs import PlayoffBracket

    row = conn.execute(
        "SELECT * FROM playoff_brackets WHERE season_id = ?",
        (season_id,),
    ).fetchone()
    if row is None:
        return None
    return PlayoffBracket(
        season_id=row["season_id"],
        format=row["format"],
        seeds=tuple(json.loads(row["seeds_json"])),
        rounds=tuple(json.loads(row["rounds_json"])),
        status=row["status"],
    )


def save_season_outcome(conn: sqlite3.Connection, outcome: "SeasonOutcome") -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO season_outcomes
            (season_id, champion_club_id, champion_source, final_match_id, runner_up_club_id, payload_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            outcome.season_id,
            outcome.champion_club_id,
            outcome.champion_source,
            outcome.final_match_id,
            outcome.runner_up_club_id,
            _json_dump(dict(outcome.payload)),
        ),
    )


def load_season_outcome(conn: sqlite3.Connection, season_id: str) -> Optional["SeasonOutcome"]:
    from .playoffs import SeasonOutcome

    row = conn.execute(
        "SELECT * FROM season_outcomes WHERE season_id = ?",
        (season_id,),
    ).fetchone()
    if row is None:
        return None
    return SeasonOutcome(
        season_id=row["season_id"],
        champion_club_id=row["champion_club_id"],
        champion_source=row["champion_source"],
        final_match_id=row["final_match_id"],
        runner_up_club_id=row["runner_up_club_id"],
        payload=json.loads(row["payload_json"]),
    )


# V2-B recruitment persistence
from .recruitment_domain import (
    RecruitmentBoardRow,
    RecruitmentOffer,
    RecruitmentProfile,
    RecruitmentSigning,
)


def save_club_recruitment_profile(conn: sqlite3.Connection, profile: RecruitmentProfile) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO club_recruitment_profile (
            club_id, archetype_priorities_json, risk_tolerance, prestige,
            playing_time_pitch, evaluation_quality
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            profile.club_id,
            _json_dump(dict(profile.archetype_priorities)),
            profile.risk_tolerance,
            profile.prestige,
            profile.playing_time_pitch,
            profile.evaluation_quality,
        ),
    )
    conn.commit()


def load_club_recruitment_profiles(conn: sqlite3.Connection) -> Dict[str, RecruitmentProfile]:
    rows = conn.execute("SELECT * FROM club_recruitment_profile ORDER BY club_id").fetchall()
    return {
        row["club_id"]: RecruitmentProfile(
            club_id=row["club_id"],
            archetype_priorities=json.loads(row["archetype_priorities_json"]),
            risk_tolerance=float(row["risk_tolerance"]),
            prestige=float(row["prestige"]),
            playing_time_pitch=float(row["playing_time_pitch"]),
            evaluation_quality=float(row["evaluation_quality"]),
        )
        for row in rows
    }


def save_recruitment_board(
    conn: sqlite3.Connection,
    season_id: str,
    rows: Iterable[RecruitmentBoardRow],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO recruitment_board (
            season_id, club_id, player_id, rank, public_score, need_score,
            preference_score, total_score, visible_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                season_id,
                row.club_id,
                row.player_id,
                row.rank,
                row.public_score,
                row.need_score,
                row.preference_score,
                row.total_score,
                row.visible_reason,
            )
            for row in rows
        ],
    )
    conn.commit()


def load_recruitment_board(
    conn: sqlite3.Connection,
    season_id: str,
    club_id: str,
) -> Tuple[RecruitmentBoardRow, ...]:
    rows = conn.execute(
        """
        SELECT * FROM recruitment_board
        WHERE season_id = ? AND club_id = ?
        ORDER BY rank, player_id
        """,
        (season_id, club_id),
    ).fetchall()
    return tuple(
        RecruitmentBoardRow(
            club_id=row["club_id"],
            player_id=row["player_id"],
            rank=int(row["rank"]),
            public_score=float(row["public_score"]),
            need_score=float(row["need_score"]),
            preference_score=float(row["preference_score"]),
            total_score=float(row["total_score"]),
            visible_reason=row["visible_reason"],
        )
        for row in rows
    )


def save_recruitment_round(
    conn: sqlite3.Connection,
    season_id: str,
    round_number: int,
    status: str,
    payload: Mapping[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO recruitment_round (
            season_id, round_number, status, payload_json
        ) VALUES (?, ?, ?, ?)
        """,
        (season_id, round_number, status, _json_dump(dict(payload))),
    )
    conn.commit()


def load_recruitment_round(
    conn: sqlite3.Connection,
    season_id: str,
    round_number: int,
) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM recruitment_round WHERE season_id = ? AND round_number = ?",
        (season_id, round_number),
    ).fetchone()
    if row is None:
        return None
    return {
        "season_id": row["season_id"],
        "round_number": int(row["round_number"]),
        "status": row["status"],
        "payload": json.loads(row["payload_json"]),
    }


def save_recruitment_offers(conn: sqlite3.Connection, offers: Iterable[RecruitmentOffer]) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO recruitment_offer (
            season_id, round_number, club_id, player_id, offer_strength, source,
            need_score, playing_time_pitch, prestige, round_order_value, visible_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                offer.season_id,
                offer.round_number,
                offer.club_id,
                offer.player_id,
                offer.offer_strength,
                offer.source,
                offer.need_score,
                offer.playing_time_pitch,
                offer.prestige,
                offer.round_order_value,
                offer.visible_reason,
            )
            for offer in offers
        ],
    )
    conn.commit()


def load_recruitment_offers(
    conn: sqlite3.Connection,
    season_id: str,
    round_number: int,
) -> Tuple[RecruitmentOffer, ...]:
    rows = conn.execute(
        """
        SELECT * FROM recruitment_offer
        WHERE season_id = ? AND round_number = ?
        ORDER BY club_id, player_id
        """,
        (season_id, round_number),
    ).fetchall()
    return tuple(
        RecruitmentOffer(
            season_id=row["season_id"],
            round_number=int(row["round_number"]),
            club_id=row["club_id"],
            player_id=row["player_id"],
            offer_strength=float(row["offer_strength"]),
            source=row["source"],
            need_score=float(row["need_score"]),
            playing_time_pitch=float(row["playing_time_pitch"]),
            prestige=float(row["prestige"]),
            round_order_value=float(row["round_order_value"]),
            visible_reason=row["visible_reason"],
        )
        for row in rows
    )


def save_recruitment_signings(
    conn: sqlite3.Connection,
    signings: Iterable[RecruitmentSigning],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO recruitment_signing (
            season_id, player_id, round_number, club_id, source,
            offer_strength, recap_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                signing.season_id,
                signing.player_id,
                signing.round_number,
                signing.club_id,
                signing.source,
                signing.offer_strength,
                signing.recap_reason,
            )
            for signing in signings
        ],
    )
    conn.commit()


def load_recruitment_signings(
    conn: sqlite3.Connection,
    season_id: str,
) -> Tuple[RecruitmentSigning, ...]:
    rows = conn.execute(
        "SELECT * FROM recruitment_signing WHERE season_id = ? ORDER BY round_number, player_id",
        (season_id,),
    ).fetchall()
    return tuple(
        RecruitmentSigning(
            season_id=row["season_id"],
            round_number=int(row["round_number"]),
            club_id=row["club_id"],
            player_id=row["player_id"],
            source=row["source"],
            offer_strength=float(row["offer_strength"]),
            recap_reason=row["recap_reason"],
        )
        for row in rows
    )


def save_prospect_market_signal(
    conn: sqlite3.Connection,
    season_id: str,
    player_id: str,
    signal: Mapping[str, Any],
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO prospect_market_signal (
            season_id, player_id, signal_json
        ) VALUES (?, ?, ?)
        """,
        (season_id, player_id, _json_dump(dict(signal))),
    )
    conn.commit()


def load_prospect_market_signals(
    conn: sqlite3.Connection,
    season_id: str,
) -> Dict[str, Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM prospect_market_signal WHERE season_id = ? ORDER BY player_id",
        (season_id,),
    ).fetchall()
    return {row["player_id"]: json.loads(row["signal_json"]) for row in rows}


__all__ = [
    "CorruptSaveError",
    "CURRENT_SCHEMA_VERSION",
    "connect",
    "create_schema",
    "initialize_schema",
    "migrate_schema",
    "backup_before_migration",
    "get_schema_version",
    "record_match",
    "record_roster_snapshot",
    "fetch_roster_snapshot",
    "list_recent_matches",
    "StoredMatchSummary",
    "fetch_match",
    "match_setup_to_dict",
    # Dynasty persistence
    "save_club",
    "load_clubs",
    "load_club_roster",
    "load_all_rosters",
    "save_lineup_default",
    "load_lineup_default",
    "save_match_lineup_override",
    "load_match_lineup_override",
    "save_season",
    "save_scheduled_matches",
    "load_season",
    "save_match_result",
    "save_player_stats_batch",
    "save_standings",
    "load_standings",
    "save_awards",
    "load_awards",
    "load_completed_match_ids",
    "fetch_season_player_stats",
    "save_player_season_stats",
    "fetch_player_career_summary",
    "save_free_agents",
    "load_free_agents",
    "save_retired_player",
    "load_retired_players",
    "save_player_identity",
    "load_player_identity",
    "save_player_career_stats",
    "load_player_career_stats",
    "save_signature_moment",
    "load_signature_moments",
    "save_hall_of_fame_entry",
    "load_hall_of_fame",
    "save_rivalry_record",
    "load_rivalry_records",
    "save_league_record",
    "load_league_records",
    "save_news_headlines",
    "load_news_headlines",
    "save_club_facilities",
    "load_club_facilities",
    "save_club_prestige",
    "load_club_prestige",
    "save_meta_patch",
    "load_meta_patch",
    "load_all_meta_patches",
    "save_cup_bracket",
    "load_cup_bracket",
    "save_cup_result",
    "load_cup_results",
    "save_club_trophy",
    "load_club_trophies",
    "load_department_heads",
    "save_weekly_command_plan",
    "load_weekly_command_plan",
    "save_command_history_record",
    "load_command_history",
    "get_state",
    "set_state",
    "load_json_state",
    "save_career_state_cursor",
    "load_career_state_cursor",
    # V2-A scouting persistence
    "save_prospect_pool",
    "load_prospect_pool",
    "mark_prospect_signed",
    "save_scout",
    "load_scouts",
    "seed_default_scouts",
    "save_scouting_state",
    "load_scouting_state",
    "load_all_scouting_states",
    "save_scout_assignment",
    "load_scout_assignment",
    "load_all_scout_assignments",
    "save_scout_strategy",
    "load_scout_strategy",
    "upsert_scout_contribution",
    "load_scout_contributions_for_season",
    "append_scouting_domain_event",
    "load_scouting_domain_events_for_season",
    "save_revealed_traits",
    "load_revealed_traits",
    "save_ceiling_label",
    "load_ceiling_label",
    "save_scout_track_record",
    "load_scout_track_records_for_scout",
    "save_player_trajectory",
    "load_player_trajectory",
    "save_season_format",
    "load_season_format",
    "save_playoff_bracket",
    "load_playoff_bracket",
    "save_season_outcome",
    "load_season_outcome",
    # V2-B recruitment persistence
    "save_club_recruitment_profile",
    "load_club_recruitment_profiles",
    "save_recruitment_board",
    "load_recruitment_board",
    "save_recruitment_round",
    "load_recruitment_round",
    "save_recruitment_offers",
    "load_recruitment_offers",
    "save_recruitment_signings",
    "load_recruitment_signings",
    "save_prospect_market_signal",
    "load_prospect_market_signals",
]
