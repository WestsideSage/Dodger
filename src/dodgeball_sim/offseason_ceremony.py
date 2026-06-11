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
    load_json_state,
    load_free_agents,
    load_player_career_stats,
    load_lineup_default,
    load_player_trajectory,
    load_prospect_pool,
    load_season,
    load_standings,
    save_awards,
    save_career_state_cursor,
    save_club,
    save_club_trophy,
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
    "recap",
    "champion",
    "awards",
    "records_ratified",
    "hof_induction",
    "development",
    "retirements",
    "rookie_class_preview",
    "recruitment",
    "schedule_reveal",
)

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
    """Return the ordered subset of OFFSEASON_CEREMONY_BEATS that have real content.

    Phase 7: records_ratified is always included so its honest empty-state
    ("no new records this season" / "book is empty") is always reachable.
    """
    _CONDITIONAL = {
        # records_ratified is unconditional — always shows with honest empty-state
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


def _reconcile_user_lineup_default(
    existing_default: Optional[List[str]], next_roster: List[Player]
) -> List[str]:
    """Carry the user's manual lineup forward across a season rollover.

    Surviving players keep their chosen order, departed players (retirements) are
    dropped, and any roster member not already in the default — chiefly because a
    vacated slot needs filling — is appended in best-by-role/OVR order. The first
    six entries remain the fielded-6, so a retired starter's slot is backfilled by
    the best available rather than reset to raw roster order.
    """
    from .lineup import optimize_ai_lineup

    roster_ids = {player.id for player in next_roster}
    kept = [pid for pid in (existing_default or []) if pid in roster_ids]
    seen = set(kept)
    for pid in optimize_ai_lineup(next_roster):
        if pid not in seen:
            kept.append(pid)
            seen.add(pid)
    return kept


def _lineup_default_after_signing(
    existing_default: Optional[List[str]], roster: List[Player], signed_id: str
) -> List[str]:
    """Fold a newly-signed player into the user's lineup default.

    Preserves the manual/optimized order of the existing starters (so signing a
    rookie does NOT reset the lineup to raw roster order), drops nobody, and
    seats the recruit at slot 6 (index 5) so they field as an active starter.
    """
    others = [player for player in roster if player.id != signed_id]
    ordered = _reconcile_user_lineup_default(existing_default, others)
    return ordered[:5] + [signed_id] + ordered[5:]


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
    remaining = sorted(candidates, key=lambda player: (-player.overall_skill(), player.id))
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
    season_id: str | None = None,
) -> None:
    award_rows = list(awards)
    player_lookup = {player.id: player for roster in rosters.values() for player in roster}
    for player_id, player in player_lookup.items():
        rows = _career_rows_for_player(conn, player_id)
        if not rows:
            continue
        player_awards = [award for award in award_rows if award.player_id == player_id]
        club_ids = {str(row.get("club_id") or "") for row in rows if row.get("club_id")}
        # Current club_id: taken from the player object (most-recent assignment).
        # Persisted into career_summary_json so ratify_records can scope records
        # to the My Club filter without a separate roster join.
        current_club_id = player.club_id or ""
        # V18: "recent" means the season being finalized. A player benched for
        # that whole season has no row in it — their recent count is honestly
        # 0, not the stale total from their last fielded season (which kept
        # declining veterans permanently above should_retire's <4 gate).
        recent_eliminations = int(rows[-1].get("total_eliminations") or 0)
        if season_id is not None and str(rows[-1].get("season_id") or "") != season_id:
            recent_eliminations = 0
        # V18: the synthetic prior-career length seeded for curated veterans
        # rides along across rewrites; seasons_played stays recorded-only.
        existing = load_player_career_stats(conn, player_id) or {}
        prior_seasons = int(existing.get("seasons_played_prior", 0))
        summary = {
            "player_id": player_id,
            "player_name": player.name,
            "club_id": current_club_id,
            "seasons_played": len(rows),
            "seasons_played_prior": prior_seasons,
            "championships": sum(1 for row in rows if int(row.get("champion") or 0)),
            "awards_won": len(player_awards),
            "total_matches": sum(int(row.get("matches") or 0) for row in rows),
            "total_eliminations": sum(int(row.get("total_eliminations") or 0) for row in rows),
            "total_catches_made": sum(int(row.get("total_catches_made") or 0) for row in rows),
            "total_dodges_successful": sum(int(row.get("total_dodges_successful") or 0) for row in rows),
            "total_times_eliminated": sum(int(row.get("total_times_eliminated") or 0) for row in rows),
            "peak_eliminations": max((int(row.get("total_eliminations") or 0) for row in rows), default=0),
            "recent_eliminations": recent_eliminations,
            "career_eliminations": sum(int(row.get("total_eliminations") or 0) for row in rows),
            "career_catches": sum(int(row.get("total_catches_made") or 0) for row in rows),
            "career_dodges": sum(int(row.get("total_dodges_successful") or 0) for row in rows),
            "clubs_served": len(club_ids),
        }
        save_player_career_stats(conn, player_id, summary)


def record_season_program_trajectories(
    conn: sqlite3.Connection,
    season: Season,
    rosters: Mapping[str, List[Player]],
) -> None:
    """Compute and save program trajectory record for each club at season end."""
    from collections import Counter
    import json
    from .persistence import (
        load_clubs,
        load_standings,
        save_program_trajectory,
        load_program_trajectories,
    )

    clubs = load_clubs(conn)

    try:
        standings = load_standings(conn, season.season_id)
        standings_by_club = {row.club_id: row for row in standings}
    except Exception:
        standings_by_club = {}

    for club_id, club in clubs.items():
        # Avoid duplicate writes for the same season
        existing = load_program_trajectories(conn, club_id)
        if any(t["season_id"] == season.season_id for t in existing):
            continue

        standings_row = standings_by_club.get(club_id)
        w = standings_row.wins if standings_row else 0
        l = standings_row.losses if standings_row else 0
        d = standings_row.draws if standings_row else 0

        # Compute dominant intent from weekly plans
        cursor = conn.execute(
            "SELECT plan_json FROM weekly_command_plans WHERE season_id = ? AND club_id = ?",
            (season.season_id, club_id),
        )
        intents = []
        for row in cursor.fetchall():
            try:
                plan = json.loads(row["plan_json"])
                if "intent" in plan:
                    intents.append(plan["intent"])
            except Exception:
                pass

        dominant_intent = Counter(intents).most_common(1)[0][0] if intents else "Balanced"

        # Get top development archetype from roster
        club_roster = rosters.get(club_id, [])
        archetypes = [p.archetype.value for p in club_roster if p.archetype]
        top_dev = Counter(archetypes).most_common(1)[0][0] if archetypes else "Balanced"

        # Compute recruiting class strength from rookies
        rookies = [p for p in club_roster if getattr(p, "newcomer", False)]
        if rookies:
            avg_pot = sum(p.traits.potential for p in rookies) / len(rookies)
            if avg_pot >= 75:
                strength = "A"
            elif avg_pot >= 65:
                strength = "B"
            elif avg_pot >= 55:
                strength = "C"
            elif avg_pot >= 45:
                strength = "D"
            else:
                strength = "F"
        else:
            strength = "C"

        trajectory = {
            "club_id": club_id,
            "season_id": season.season_id,
            "archetype": club.program_archetype,
            "dominant_intent": dominant_intent,
            "record_w": w,
            "record_l": l,
            "record_d": d,
            "top_dev_archetype": top_dev,
            "recruiting_class_strength": strength,
            "notes": {},
        }

        save_program_trajectory(conn, trajectory)


def finalize_season(
    conn: sqlite3.Connection,
    season: Season,
    rosters: Mapping[str, List[Player]],
) -> None:
    """Compute and persist season awards, player season stats, and career summaries (idempotent)."""
    existing_awards = load_awards(conn, season.season_id)
    if existing_awards:
        _update_career_summaries(conn, rosters, existing_awards, season_id=season.season_id)
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
    _outcome_row = conn.execute(
        "SELECT champion_club_id FROM season_outcomes WHERE season_id = ?",
        (season.season_id,),
    ).fetchone()
    champion_club_id = _outcome_row["champion_club_id"] if _outcome_row else None
    awards = compute_season_awards(season.season_id, season_stats, player_club_map, newcomers, champion_club_id)
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
    _update_career_summaries(conn, rosters, awards, season_id=season.season_id)
    season_outcome = conn.execute(
        "SELECT champion_club_id FROM season_outcomes WHERE season_id = ?",
        (season.season_id,),
    ).fetchone()
    if season_outcome and season_outcome["champion_club_id"]:
        save_club_trophy(conn, season_outcome["champion_club_id"], "championship", season.season_id)
    record_season_program_trajectories(conn, season, rosters)
    # A playoff final decided by tie-resolution patches match_records AFTER the
    # last standings recompute of the season; rebuild here so the rivalry book
    # always reflects the resolved playoff results before the ceremony reads it.
    from .game_loop import rebuild_rivalry_records

    rebuild_rivalry_records(conn)
    conn.commit()


def _load_player_dev_focus(
    conn: sqlite3.Connection, season_id: str, player_club_id: str
) -> str:
    """Return the dev focus from the PLAYER's latest saved weekly plan.

    The club filter is load-bearing: AI weekly plans are persisted into the
    same ``weekly_command_plans`` table (``prepare_ai_plans_for_matches``) with
    dev_focus values like ``YOUTH``/``VETERAN`` that the development model does
    not recognise. An unfiltered latest-week read could silently replace the
    player's chosen focus with an arbitrary AI club's plan.
    """
    row = conn.execute(
        """
        SELECT plan_json FROM weekly_command_plans
        WHERE season_id = ? AND club_id = ?
        ORDER BY week DESC LIMIT 1
        """,
        (season_id, player_club_id),
    ).fetchone()
    if not row:
        return "BALANCED"
    plan = json.loads(row[0])
    return plan.get("department_orders", {}).get("dev_focus", "BALANCED")


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
    # Appearance counts feed the development reps gate (a year-round starter
    # develops at the full headroom rate; the legacy minutes/1000 signal never
    # matched either engine's scale and starved all post-practice growth).
    matches_by_player = {
        row["player_id"]: int(row["matches"])
        for row in conn.execute(
            "SELECT player_id, COUNT(*) AS matches FROM player_match_stats "
            "WHERE match_id IN (SELECT match_id FROM match_records WHERE season_id = ?) "
            "GROUP BY player_id",
            (season.season_id,),
        )
    }
    club_match_counts = {
        row["club_id"]: int(row["n"])
        for row in conn.execute(
            "SELECT club_id, COUNT(*) AS n FROM ("
            "  SELECT home_club_id AS club_id FROM match_records WHERE season_id = ?"
            "  UNION ALL"
            "  SELECT away_club_id FROM match_records WHERE season_id = ?"
            ") GROUP BY club_id",
            (season.season_id, season.season_id),
        )
    }
    updated_rosters: Dict[str, List[Player]] = {}
    released_ai_players: List[Player] = []
    development_rows: List[Dict[str, Any]] = []
    retirement_rows: List[Dict[str, Any]] = []

    _player_club_id = get_state(conn, "player_club_id") or ""
    player_dev_focus = _load_player_dev_focus(conn, season.season_id, _player_club_id)

    # Evaluate open promises before retirements alter roster state
    from .dynasty_office import evaluate_season_promises
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

    # V19b training credits: each TRAINING staff-focus week this season earns
    # the club +0.2 OVR of offseason practice growth (cap 8 weeks = +1.6),
    # headroom-capped per player in apply_season_development. Symmetric: AI
    # clubs' persisted weekly plans count the same way (Development Factory
    # archetypes run training focuses, so their youth actually benefit).
    from .persistence import count_staff_focus_weeks

    practice_credit_by_club = {
        club_id: 0.2 * min(8, count_staff_focus_weeks(conn, season.season_id, club_id, "training"))
        for club_id in rosters
    }

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
                matches_played=matches_by_player.get(player.id, 0),
                club_matches=club_match_counts.get(club_id, 0),
                practice_credit_ovr=practice_credit_by_club.get(club_id, 0.0),
            )
            aged = replace(developed, age=developed.age + 1)
            delta = aged.overall_skill() - player.overall_skill()
            if should_retire(aged, load_player_career_stats(conn, player.id)):
                save_retired_player(conn, aged, season.season_id, "age_decline")
                retirement_rows.append(
                    {
                        "player_id": aged.id,
                        "player_name": aged.name,
                        "club_id": club_id,
                        "age": aged.age,
                        "overall": aged.overall_skill(),
                        "reason": "age_decline",
                    }
                )
                continue
            staff_notes = []
            if aged.traits.potential > player.traits.potential:
                staff_notes.append("Potential upgraded by great coaching & performance!")
            if delta > 3:
                staff_notes.append("Outstanding offseason growth!")
            elif delta < 0:
                staff_notes.append("Signs of regression.")
            # Phase 5 — Growth legibility: per-attribute deltas (presentation only).
            # Computed from before (player) and after (aged) ratings so the dev beat
            # can show which attributes moved beneath the composite +N OVR headline.
            _RATING_ATTRS = (
                "accuracy", "power", "dodge", "catch", "stamina",
                "tactical_iq", "catch_courage", "throw_selection_iq", "conditioning_curve",
            )
            attr_deltas = {
                attr: int(getattr(aged.ratings, attr)) - int(getattr(player.ratings, attr))
                for attr in _RATING_ATTRS
            }
            development_rows.append(
                {
                    "player_id": aged.id,
                    "player_name": aged.name,
                    "club_id": club_id,
                    "before": player.overall_skill(),
                    "after": aged.overall_skill(),
                    "delta": delta,
                    "notes": staff_notes,
                    "attr_deltas": attr_deltas,
                    "potential_ceiling": int(aged.traits.potential),
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
        next_roster = updated_rosters.get(club_id, [])
        save_club(conn, club, next_roster)
        if club_id == player_club_id:
            # D1: the user's manual lineup persists across seasons. Keep surviving
            # starters in their chosen order, drop departed players (retirements),
            # and backfill any vacated slot by best-by-role/OVR.
            save_lineup_default(
                conn,
                club_id,
                _reconcile_user_lineup_default(
                    load_lineup_default(conn, club_id), next_roster
                ),
            )
        else:
            save_lineup_default(conn, club_id, optimize_ai_lineup(next_roster))
    save_free_agents(conn, free_agents, next_season_id)
    set_state(conn, "offseason_development_json", json.dumps(development_rows))
    set_state(conn, "offseason_retirements_json", json.dumps(retirement_rows))
    set_state(conn, "offseason_draft_signed_player_id", "")
    set_state(conn, "offseason_draft_signed_count", "0")
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
        records_payload_json=get_state(conn, "offseason_records_ratified_json"),
        hof_payload_json=get_state(conn, "offseason_hof_inducted_json"),
        retirement_rows=retirement_rows,
    )
    set_state(conn, "offseason_active_beats_json", json.dumps(active_beats))
    set_state(conn, "offseason_initialized_for", season.season_id)
    conn.commit()
    return updated_rosters


def _available_prospect_players(conn: sqlite3.Connection, class_year: int) -> list:
    """Prospects in the class pool that have not been signed yet."""
    return [
        prospect
        for prospect in load_prospect_pool(conn, class_year=class_year)
        if not _is_already_signed(conn, class_year, prospect.player_id)
    ]


def _picker_credibility_score(conn: sqlite3.Connection) -> int:
    """Program credibility for picker interest/fit — same math as the board.

    Falls back to the neutral baseline (50) when no career context exists yet
    (the ceremony payload builders must tolerate an empty save).
    """
    from .persistence import load_command_history_all_seasons
    from .recruiting_office import _credibility_score

    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    if not season_id or not player_club_id:
        return 50
    return _credibility_score(
        conn, season_id, player_club_id, load_command_history_all_seasons(conn)
    )


def _scouted_band(prospect, action_state: Mapping[str, Any]) -> tuple[int, int]:
    """The public OVR band the player is entitled to see — board and picker
    must compute it identically (base public band, narrowed once if scouted)."""
    from .recruiting_actions import narrow_band

    return narrow_band(
        tuple(prospect.public_ratings_band["ovr"]),
        scouted=bool(action_state.get("scouted")),
    )


def available_recruitment_choices(
    conn: sqlite3.Connection, season_number: int
) -> list[dict[str, Any]]:
    """Every prospect and free agent the player may sign this offseason.

    Prospects expose the SCOUTED public band — never ``true_overall()``: not
    as a field, not via ``fit_score``, not via sort order (V16 Task 1).
    Free agents are league veterans with public history, so their verified
    OVR stays. Prospects are listed first (best public estimate first), then
    free agents.
    """
    from .recruiting_actions import current_interest

    class_year = season_number or 1
    actions = load_json_state(conn, "prospect_recruitment_actions_json", {})
    credibility = _picker_credibility_score(conn)

    choices: list[dict[str, Any]] = []
    for prospect in _available_prospect_players(conn, class_year):
        state = actions.get(prospect.player_id, {})
        low, high = _scouted_band(prospect, state)
        choices.append(
            {
                "prospect_id": prospect.player_id,
                "name": prospect.name,
                "age": prospect.age,
                "hometown": prospect.hometown,
                "archetype": prospect.public_archetype_guess,
                "kind": "prospect",
                "pipeline_tier": prospect.pipeline_tier,
                "public_ovr_band": [low, high],
                "scouted": bool(state.get("scouted")),
                "contacted": bool(state.get("contacted")),
                "visited": bool(state.get("visited")),
                "interest": current_interest(
                    state,
                    pipeline_tier=prospect.pipeline_tier,
                    credibility_score=credibility,
                ),
                "fit_score": round((low + high) / 2.0 + credibility * 0.12),
            }
        )
    choices.sort(
        key=lambda c: (
            -(c["public_ovr_band"][0] + c["public_ovr_band"][1]),
            c["prospect_id"],
        )
    )
    for free_agent in sorted(
        load_free_agents(conn), key=lambda p: (-p.overall_skill(), p.id)
    ):
        choices.append(
            {
                "prospect_id": free_agent.id,
                "name": free_agent.name,
                "overall": free_agent.overall_skill(),
                "age": free_agent.age,
                "hometown": "Free agent",
                "archetype": free_agent.archetype.display_name,
                "kind": "free_agent",
            }
        )
    return choices


def _commit_prospect_signing(
    conn: sqlite3.Connection, prospect, player_club_id: str, class_year: int
) -> Player:
    # Capture the user's lineup default BEFORE signing: sign_prospect_to_club
    # rewrites it to raw roster order, which would erase the manual/optimized
    # order we must carry forward (D1).
    prior_default = load_lineup_default(conn, player_club_id)
    signed_prospect = sign_prospect_to_club(conn, prospect, player_club_id, class_year)
    rosters = load_all_rosters(conn)
    set_state(conn, "offseason_draft_signed_player_id", signed_prospect.id)
    roster = list(rosters.get(player_club_id, []))
    save_lineup_default(
        conn,
        player_club_id,
        _lineup_default_after_signing(prior_default, roster, signed_prospect.id),
    )
    conn.commit()
    return signed_prospect


def _commit_free_agent_signing(
    conn: sqlite3.Connection,
    free_agent: Player,
    free_agents: list[Player],
    player_club_id: str,
    season_number: int,
) -> Player:
    remaining = [player for player in free_agents if player.id != free_agent.id]
    signed = replace(free_agent, club_id=player_club_id, newcomer=True)
    rosters = load_all_rosters(conn)
    roster = list(rosters.get(player_club_id, []))
    roster.append(signed)
    clubs = load_clubs(conn)
    save_club(conn, clubs[player_club_id], roster)
    save_lineup_default(
        conn,
        player_club_id,
        _lineup_default_after_signing(
            load_lineup_default(conn, player_club_id), roster, signed.id
        ),
    )
    save_free_agents(conn, remaining, f"season_{(season_number or 1) + 1}")
    set_state(conn, "offseason_draft_signed_player_id", signed.id)
    conn.commit()
    return signed


def sign_chosen_rookie_contested(
    conn: sqlite3.Connection,
    player_club_id: str,
    season_number: int,
    prospect_id: str,
) -> tuple[Optional[Player], Optional[dict[str, Any]]]:
    """Sign the player's pick through the contested Signing Day round.

    Prospects resolve via ``recruitment.conduct_recruitment_round``: eligible
    AI clubs bid in the same round, so the pick can be sniped — that is a
    legitimate ``(None, snipe_dict)`` outcome, not an error. Free agents are
    uncontested (league veterans signing directly). Returns ``(None, None)``
    when the id matches nothing.
    """
    from .recruitment import conduct_recruitment_round

    class_year = season_number or 1
    chosen = next(
        (
            prospect
            for prospect in _available_prospect_players(conn, class_year)
            if prospect.player_id == prospect_id
        ),
        None,
    )
    if chosen is None:
        free_agents = load_free_agents(conn)
        chosen_fa = next((p for p in free_agents if p.id == prospect_id), None)
        if chosen_fa is None:
            return None, None
        signed_fa = _commit_free_agent_signing(
            conn, chosen_fa, free_agents, player_club_id, season_number
        )
        return signed_fa, {
            "kind": "free_agent_signed",
            "prospect_id": signed_fa.id,
            "prospect_name": signed_fa.name,
            "explanation": (
                f"{signed_fa.name} signed directly — free agents are league "
                "veterans, not contested prospects."
            ),
        }

    season_id = get_state(conn, "active_season_id") or f"season_{class_year}"
    actions = load_json_state(conn, "prospect_recruitment_actions_json", {})
    scouted_low, scouted_high = _scouted_band(chosen, actions.get(chosen.player_id, {}))
    outcome = conduct_recruitment_round(
        conn,
        stored_root_seed(conn),
        season_id,
        class_year,
        player_club_id,
        prospect_id,
    )
    clubs = load_clubs(conn)
    if outcome.user_won:
        set_state(conn, "offseason_draft_signed_player_id", outcome.signed_player.id)
        conn.commit()
        if outcome.rival_club_id is not None:
            rival_club = clubs.get(outcome.rival_club_id)
            rival_name = rival_club.name if rival_club else outcome.rival_club_id
            win_line = (
                f"Your offer {outcome.user_offer_strength:.1f} beat "
                f"{rival_name}'s {outcome.rival_offer_strength:.1f} — interest "
                f"{outcome.interest}% strengthened it."
            )
        else:
            win_line = (
                f"No rival club bid on {chosen.name} this round — your offer "
                f"{outcome.user_offer_strength:.1f} stood alone."
            )
        verified_ovr = outcome.signed_player.overall_skill()
        return outcome.signed_player, {
            "kind": "signed",
            "prospect_id": chosen.player_id,
            "prospect_name": chosen.name,
            "your_offer": outcome.user_offer_strength,
            "your_interest": outcome.interest,
            "rival_club_name": (
                clubs[outcome.rival_club_id].name
                if outcome.rival_club_id in clubs
                else None
            ),
            "rival_offer": outcome.rival_offer_strength,
            "scouted_band": [scouted_low, scouted_high],
            "reveal": (
                f"Scouted {scouted_low}–{scouted_high} → verified OVR {verified_ovr}."
            ),
            "explanation": win_line,
        }

    winning_club = clubs.get(outcome.winning_club_id)
    winning_club_name = winning_club.name if winning_club else (outcome.winning_club_id or "Another club")
    action_label = (
        f"{outcome.actions_taken} recruiting action{'s' if outcome.actions_taken != 1 else ''}"
    )
    snipe = {
        "kind": "sniped",
        "prospect_id": chosen.player_id,
        "prospect_name": chosen.name,
        "winning_club_id": outcome.winning_club_id,
        "winning_club_name": winning_club_name,
        "winning_offer": outcome.winning_offer_strength,
        "your_offer": outcome.user_offer_strength,
        "your_interest": outcome.interest,
        "actions_taken": outcome.actions_taken,
        "explanation": (
            f"{winning_club_name} signed {chosen.name} — their offer "
            f"{outcome.winning_offer_strength:.1f} beat yours "
            f"{outcome.user_offer_strength:.1f}. Your interest was "
            f"{outcome.interest}%, built from {action_label}."
        ),
    }
    conn.commit()
    return None, snipe


def ensure_ai_offseason_signings(conn: sqlite3.Connection) -> None:
    """Run the AI Signing Day sweep once per offseason (idempotent).

    Called when recruitment closes (skip, cap, roster-full, advance) and as a
    safety net before the next season begins, so the league moves every
    offseason regardless of how the user finished theirs.
    """
    from .recruitment import run_ai_offseason_signings

    season_id = get_state(conn, "active_season_id")
    if not season_id:
        return
    if get_state(conn, "offseason_ai_signings_done_for") == season_id:
        return
    player_club_id = get_state(conn, "player_club_id")
    digits = "".join(ch for ch in season_id if ch.isdigit())
    class_year = int(digits) if digits else 1
    run_ai_offseason_signings(
        conn,
        stored_root_seed(conn),
        season_id,
        class_year,
        player_club_id,
    )
    set_state(conn, "offseason_ai_signings_done_for", season_id)
    conn.commit()


def sign_chosen_rookie(
    conn: sqlite3.Connection,
    player_club_id: str,
    season_number: int,
    prospect_id: str,
) -> Optional[Player]:
    """Sign a specific prospect or free agent chosen by the player.

    Returns ``None`` when ``prospect_id`` matches no available signee.
    """
    class_year = season_number or 1
    chosen = next(
        (
            prospect
            for prospect in _available_prospect_players(conn, class_year)
            if prospect.player_id == prospect_id
        ),
        None,
    )
    if chosen is not None:
        return _commit_prospect_signing(conn, chosen, player_club_id, class_year)
    free_agents = load_free_agents(conn)
    chosen_fa = next((p for p in free_agents if p.id == prospect_id), None)
    if chosen_fa is None:
        return None
    return _commit_free_agent_signing(
        conn, chosen_fa, free_agents, player_club_id, season_number
    )


def sign_best_rookie(
    conn: sqlite3.Connection,
    player_club_id: str,
    season_number: int,
) -> Optional[Player]:
    """Sign the best available signee BY PUBLIC ESTIMATE to the player's club.

    "Best" for prospects means the scouted band midpoint — the same order the
    picker displays — never the hidden true overall (auto-pick must not leak
    truth through behavior). Free agents have public ratings.
    """
    class_year = season_number or 1
    available_prospects = _available_prospect_players(conn, class_year)
    if available_prospects:
        actions = load_json_state(conn, "prospect_recruitment_actions_json", {})

        def _public_estimate_key(prospect):
            low, high = _scouted_band(prospect, actions.get(prospect.player_id, {}))
            return (-(low + high), prospect.player_id)

        selected_prospect = sorted(available_prospects, key=_public_estimate_key)[0]
        return _commit_prospect_signing(conn, selected_prospect, player_club_id, class_year)
    free_agents = load_free_agents(conn)
    if not free_agents:
        conn.commit()
        return None
    selected = sorted(free_agents, key=lambda player: (-player.overall_skill(), player.id))[0]
    return _commit_free_agent_signing(
        conn, selected, free_agents, player_club_id, season_number
    )


def begin_next_season(
    conn: sqlite3.Connection,
    cursor: CareerStateCursor,
    clubs: Mapping[str, Club],
) -> CareerStateCursor:
    """Create next season, wire scouting, advance cursor to SEASON_ACTIVE_PRE_MATCH."""
    from .config import DEFAULT_SCOUTING_CONFIG
    from .scouting_center import initialize_scouting_for_career

    # Safety net: whatever path closed recruitment, the AI clubs make their
    # Signing Day moves before the league rolls into the next season
    # (idempotent — usually already done at recruitment close).
    ensure_ai_offseason_signings(conn)

    _maintain_user_lineup_for_new_season(conn)

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


def _maintain_user_lineup_for_new_season(conn: sqlite3.Connection) -> None:
    """V19 Task 8 (owner-decided toggle, CFB26 depth-chart pattern).

    At season rollover the user lineup is either RE-SEATED (auto-reorder ON —
    the set-and-forget mode, default for new careers: the fielded six is
    re-optimized exactly the way AI clubs manage theirs, so signings and
    developed players enter the six instead of rotting at slot 6) or
    REPAIRED only (auto-reorder OFF — the hands-on mode a manual lineup save
    selects: the player's saved order is respected exactly; retired/departed
    players are removed and the order back-filled by OVR so the lineup is
    always fieldable, but no seat the player chose is ever re-ranked).
    """
    from .lineup import optimize_ai_lineup
    from .web_status_service import lineup_auto_reorder_enabled

    player_club_id = get_state(conn, "player_club_id")
    if not player_club_id:
        return
    roster = load_all_rosters(conn).get(player_club_id, [])
    if not roster:
        return
    if lineup_auto_reorder_enabled(conn):
        save_lineup_default(conn, player_club_id, optimize_ai_lineup(roster))
        # Disclosure flag: the season-start surface can state the staff
        # re-seated the lineup (the Lineup Editor always shows the result).
        set_state(conn, "offseason_lineup_reordered", "1")
        return
    set_state(conn, "offseason_lineup_reordered", "0")
    roster_ids = {player.id for player in roster}
    default = load_lineup_default(conn, player_club_id) or []
    kept = [pid for pid in default if pid in roster_ids]
    if not default or len(kept) != len(default) or len(kept) < len(roster):
        backfill = sorted(
            (player for player in roster if player.id not in set(kept)),
            key=lambda player: (-player.overall_skill(), player.id),
        )
        save_lineup_default(conn, player_club_id, kept + [p.id for p in backfill])


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
    records_book_empty: bool = False,
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
            lines = [f"Champion: {club_name(season_outcome.champion_club_id)}"]
            if season_outcome.runner_up_club_id:
                lines.append(f"Runner-up: {club_name(season_outcome.runner_up_club_id)}")
            body = "\n".join(lines)
        elif not ordered_standings:
            body = "No completed standings are available for this season."
        else:
            champion = ordered_standings[0]
            body = f"Champion: {club_name(champion.club_id)}"
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
            if records_book_empty:
                # Phase 7 honest empty-state A: the league record book itself is
                # empty (no seasons ratified yet). Copy is honest — records seed
                # from ALL active players, not just retirees, so they will appear
                # after the first offseason is processed.
                body = "The record book is empty — records will be set as seasons are played."
            else:
                # Phase 7 honest empty-state B: book exists but no NEW records
                # broken this season (all incumbents held).
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
        lines.append("\nAll active players have aged by 1 year, and match fatigue has been fully resolved across the league.")
        return OffseasonCeremonyBeat(key, "Development", "\n".join(lines))

    if key == "retirements":
        lines = [f"Retirements processed: {len(retirements)}"]
        if not retirements:
            lines.append("No players retired this off-season.")
        for row in retirements:
            marker = " *" if row.get("club_id") == player_club_id else ""
            lines.append(
                f"  {row.get('player_name', row.get('player_id'))} ({club_name(str(row.get('club_id', '')))}): "
                f"age {row.get('age')} OVR {int(round(float(row.get('overall', 0))))}{marker}"
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
            lines.append(f"Top prospects (70+ OVR): {top_band_depth}")
            lines.append(f"Veteran free agents available: {free_agent_count}")
            if archetype_distribution:
                ordered = sorted(archetype_distribution.items(), key=lambda item: (-item[1], item[0]))
                lines.append("Archetype distribution: " + ", ".join(f"{name} {count}" for name, count in ordered))
            if storylines:
                lines.append("")
                lines.append("Market storylines:")
                for storyline in storylines:
                    lines.append(f"- {storyline.get('sentence', '')}")
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
                lines.append(f"Your latest signing: {signed.name} ({signed.overall_skill()} OVR)")
            lines.append("")
            lines.append("Current roster sizes:")
            for club_id, size in roster_sizes:
                lines.append(f"  {club_name(club_id)}: {size} players")
            return OffseasonCeremonyBeat(key, "Recruitment Day", "\n".join(lines))
        # Recruitment Day is the v2 flow; v1 draft is a read-only preview
        # so the copy should not ask the manager to "sign one rookie" when
        # there is no signing UI rendered for this beat.
        if signed is not None:
            lines = [f"Rookie signed: {signed.name} ({signed.overall_skill()} OVR)."]
        else:
            lines = [
                f"Top of this year's class — {len(rookies)} prospect{'s' if len(rookies) != 1 else ''} available.",
            ]
            for player in sorted(rookies, key=lambda item: (-item.overall_skill(), item.id))[:5]:
                lines.append(f"  {player.name}: OVR {player.overall_skill()}, age {player.age}")
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
    "sign_chosen_rookie",
    "available_recruitment_choices",
    "begin_next_season",
    "build_offseason_ceremony_beat",
    "create_next_manager_season",
    "apply_scouting_carry_forward",
]


# ----------------------------------------------------------------------
# Offseason state row loader (formerly manager_helpers)
# ----------------------------------------------------------------------

def load_offseason_state_rows(conn: sqlite3.Connection, key: str) -> List[Mapping[str, Any]]:
    payload = load_json_state(conn, key, [])
    if not isinstance(payload, list):
        raise CorruptSaveError(f"Corrupt JSON for state {key}: expected list")
    return payload



# Public aliases for legacy names that moved here from the Tk-era manager_gui.
apply_scouting_carry_forward_at_transition = apply_scouting_carry_forward
career_rows_for_player = _career_rows_for_player


def update_manager_career_summaries(conn, season, rosters, awards):
    """Legacy 4-arg wrapper. The canonical form is ``_update_career_summaries``."""
    season_id = getattr(season, "season_id", None)
    _update_career_summaries(conn, rosters, awards, season_id=season_id)
