"""V2-E: pure-computation off-season ceremony beats.

Each function here is idempotent per `(conn, season_id)`. First call computes
and persists; subsequent calls read the persisted payload from `dynasty_state`
and return it unchanged. None of these functions mutate prospect pools,
recruitment state, or scouting state.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

import math

from dodgeball_sim.career import CareerSummary, evaluate_hall_of_fame
from dodgeball_sim.persistence import (
    get_state,
    load_club_recruitment_profiles,
    load_free_agents,
    load_hall_of_fame,
    load_league_records,
    load_player_career_stats,
    load_prospect_pool,
    save_hall_of_fame_entry,
    save_league_record,
    set_state,
)
from dodgeball_sim.records import CareerStats, build_individual_records

_PROSPECT_RATING_KEYS = ("accuracy", "power", "dodge", "catch", "stamina")
_TOP_BAND_THRESHOLD = 70.0
_DEEPEST_CLASS_FACTOR = 1.2


@dataclass(frozen=True)
class RatifiedRecord:
    record_type: str
    holder_id: str
    holder_type: str
    holder_name: str
    previous_value: float
    new_value: float
    set_in_season: str
    detail: str


@dataclass(frozen=True)
class RatificationPayload:
    season_id: str
    new_records: Tuple[RatifiedRecord, ...]


@dataclass(frozen=True)
class HallOfFameInductee:
    player_id: str
    player_name: str
    induction_season: str
    legacy_score: float
    threshold: float
    reasons: Tuple[str, ...]
    seasons_played: int
    championships: int
    awards_won: int
    total_eliminations: int


@dataclass(frozen=True)
class InductionPayload:
    season_id: str
    new_inductees: Tuple[HallOfFameInductee, ...]


@dataclass(frozen=True)
class RookieStoryline:
    template_id: str       # one of: "archetype_demand", "top_band_depth", "ai_cluster", "free_agent_crop"
    sentence: str
    fact: Mapping[str, Any]  # source numeric fact backing the sentence


@dataclass(frozen=True)
class RookiePreviewPayload:
    season_id: str
    class_year: int
    source: str            # "prospect_pool" or "legacy_free_agents"
    class_size: int
    archetype_distribution: Mapping[str, int]
    top_band_depth: int
    free_agent_count: int
    storylines: Tuple[RookieStoryline, ...]


def _record_to_dict(record: RatifiedRecord) -> Dict[str, Any]:
    """Serialize a RatifiedRecord to a JSON-friendly dict."""
    return {
        "record_type": record.record_type,
        "holder_id": record.holder_id,
        "holder_type": record.holder_type,
        "holder_name": record.holder_name,
        "previous_value": float(record.previous_value),
        "new_value": float(record.new_value),
        "set_in_season": record.set_in_season,
        "detail": record.detail,
    }


def _record_from_dict(d: Dict[str, Any]) -> RatifiedRecord:
    """Deserialize a RatifiedRecord from a dict (e.g. parsed from JSON)."""
    return RatifiedRecord(
        record_type=d["record_type"],
        holder_id=d["holder_id"],
        holder_type=d["holder_type"],
        holder_name=d["holder_name"],
        previous_value=float(d["previous_value"]),
        new_value=float(d["new_value"]),
        set_in_season=d["set_in_season"],
        detail=d["detail"],
    )


def ratify_records(
    conn: sqlite3.Connection,
    season_id: str,
) -> RatificationPayload:
    """Compute or load the Records Ratified beat payload. Idempotent per season_id."""
    # Cache check: return persisted payload if already ratified for this season
    if get_state(conn, "offseason_records_ratified_for") == season_id:
        raw = get_state(conn, "offseason_records_ratified_json")
        if raw is not None:
            records = tuple(_record_from_dict(d) for d in json.loads(raw))
        else:
            records = ()
        return RatificationPayload(season_id=season_id, new_records=records)

    # Load all career stats from the player_career_stats table
    cursor = conn.execute(
        "SELECT player_id, career_eliminations, career_catches, career_dodges, "
        "championships, career_summary_json FROM player_career_stats"
    )
    rows = cursor.fetchall()

    career_stats: List[CareerStats] = []
    for row in rows:
        summary = json.loads(row["career_summary_json"])
        career_stats.append(
            CareerStats(
                player_id=row["player_id"],
                player_name=summary.get("player_name", row["player_id"]),
                club_id=summary.get("club_id", None),
                career_eliminations=int(row["career_eliminations"]),
                career_catches=int(row["career_catches"]),
                career_dodges=int(row["career_dodges"]),
                seasons_at_one_club=int(summary.get("clubs_served", 1) == 1) * int(summary.get("seasons_played", 0)),
                championships=int(row["championships"]),
            )
        )

    # Load existing league records for comparison (keyed by record_type)
    existing_records: Dict[str, float] = {}
    for rec in load_league_records(conn):
        existing_records[rec["record_type"]] = float(rec["record_value"])

    # Build individual record candidates from career stats
    candidates = build_individual_records(career_stats, season_id) if career_stats else {}

    # Compare candidates to existing records; collect new records in sorted order
    broken: List[RatifiedRecord] = []
    for record_type, candidate in sorted(candidates.items()):
        existing_value = existing_records.get(record_type, float("-inf"))
        if candidate.value <= 0:
            continue
        if candidate.value <= existing_value:
            continue
        # Save the new record to persistent storage
        save_league_record(
            conn,
            record_type=record_type,
            holder_id=candidate.holder_id,
            holder_type=candidate.holder_type,
            record_value=candidate.value,
            set_in_season=season_id,
            record_payload={
                "holder_name": candidate.holder_name,
                "value": candidate.value,
                "detail": candidate.detail,
            },
        )
        broken.append(
            RatifiedRecord(
                record_type=record_type,
                holder_id=candidate.holder_id,
                holder_type=candidate.holder_type,
                holder_name=candidate.holder_name,
                previous_value=0.0 if existing_records.get(record_type) is None else existing_value,
                new_value=float(candidate.value),
                set_in_season=season_id,
                detail=candidate.detail,
            )
        )

    # Persist the payload and mark this season as ratified
    records_tuple = tuple(broken)
    set_state(conn, "offseason_records_ratified_json", json.dumps([_record_to_dict(r) for r in records_tuple]))
    set_state(conn, "offseason_records_ratified_for", season_id)
    conn.commit()

    return RatificationPayload(season_id=season_id, new_records=records_tuple)


def _inductee_to_dict(inductee: HallOfFameInductee) -> Dict[str, Any]:
    """Serialize a HallOfFameInductee to a JSON-friendly dict."""
    return {
        "player_id": inductee.player_id,
        "player_name": inductee.player_name,
        "induction_season": inductee.induction_season,
        "legacy_score": float(inductee.legacy_score),
        "threshold": float(inductee.threshold),
        "reasons": list(inductee.reasons),
        "seasons_played": inductee.seasons_played,
        "championships": inductee.championships,
        "awards_won": inductee.awards_won,
        "total_eliminations": inductee.total_eliminations,
    }


def _inductee_from_dict(d: Dict[str, Any]) -> HallOfFameInductee:
    """Deserialize a HallOfFameInductee from a dict (e.g. parsed from JSON)."""
    return HallOfFameInductee(
        player_id=d["player_id"],
        player_name=d["player_name"],
        induction_season=d["induction_season"],
        legacy_score=float(d["legacy_score"]),
        threshold=float(d["threshold"]),
        reasons=tuple(d["reasons"]),
        seasons_played=int(d["seasons_played"]),
        championships=int(d["championships"]),
        awards_won=int(d["awards_won"]),
        total_eliminations=int(d["total_eliminations"]),
    )


def induct_hall_of_fame(
    conn: sqlite3.Connection,
    season_id: str,
) -> InductionPayload:
    """Compute or load the Hall of Fame Induction beat payload. Idempotent per season_id."""
    # Cache check: return persisted payload if already computed for this season
    if get_state(conn, "offseason_hof_inducted_for") == season_id:
        raw = get_state(conn, "offseason_hof_inducted_json")
        if raw is not None:
            inductees = tuple(_inductee_from_dict(d) for d in json.loads(raw))
        else:
            inductees = ()
        return InductionPayload(season_id=season_id, new_inductees=inductees)

    # Load player IDs already in the Hall of Fame (to avoid double-induction)
    already_inducted: set[str] = {
        entry["player_id"] for entry in load_hall_of_fame(conn)
    }

    # Find players who retired this season
    cursor = conn.execute(
        "SELECT player_id FROM retired_players WHERE final_season = ? ORDER BY player_id",
        (season_id,),
    )
    retired_this_season = [row["player_id"] for row in cursor.fetchall()]

    new_inductees: List[HallOfFameInductee] = []
    for player_id in retired_this_season:
        if player_id in already_inducted:
            continue

        career_data = load_player_career_stats(conn, player_id)
        if career_data is None:
            continue

        # Build CareerSummary — signature_moments is required; default to empty
        summary = CareerSummary(
            player_id=career_data.get("player_id", player_id),
            player_name=career_data.get("player_name", player_id),
            seasons_played=int(career_data.get("seasons_played", 0)),
            championships=int(career_data.get("championships", 0)),
            awards_won=int(career_data.get("awards_won", 0)),
            total_matches=int(career_data.get("total_matches", 0)),
            total_eliminations=int(career_data.get("total_eliminations", 0)),
            total_catches_made=int(career_data.get("total_catches_made", 0)),
            total_dodges_successful=int(career_data.get("total_dodges_successful", 0)),
            total_times_eliminated=int(career_data.get("total_times_eliminated", 0)),
            peak_eliminations=int(career_data.get("peak_eliminations", 0)),
            signature_moments=(),  # leverage/value not persisted in current schema; bonus skipped
        )

        case = evaluate_hall_of_fame(summary)
        if not case.inducted:
            continue

        save_hall_of_fame_entry(conn, player_id, season_id, career_data)
        new_inductees.append(
            HallOfFameInductee(
                player_id=summary.player_id,
                player_name=summary.player_name,
                induction_season=season_id,
                legacy_score=case.score,
                threshold=case.threshold,
                reasons=case.reasons,
                seasons_played=summary.seasons_played,
                championships=summary.championships,
                awards_won=summary.awards_won,
                total_eliminations=summary.total_eliminations,
            )
        )

    # Persist the payload and mark this season as processed
    inductees_tuple = tuple(new_inductees)
    set_state(conn, "offseason_hof_inducted_json", json.dumps([_inductee_to_dict(i) for i in inductees_tuple]))
    set_state(conn, "offseason_hof_inducted_for", season_id)
    conn.commit()

    return InductionPayload(season_id=season_id, new_inductees=inductees_tuple)


def _prospect_band_low_mean(prospect) -> float:
    """Mean of the low end of public_ratings_band across the 5 rating keys."""
    return sum(prospect.public_ratings_band[key][0] for key in _PROSPECT_RATING_KEYS) / len(_PROSPECT_RATING_KEYS)


def _prior_top_band_history(conn: sqlite3.Connection, current_class_year: int) -> Tuple[int, int]:
    """Return (max prior top_band_depth, count of prior classes with a stored summary)."""
    prior_depths: List[int] = []
    for y in range(1, current_class_year):
        raw = get_state(conn, f"rookie_class_summary_{y}")
        if raw is not None:
            summary = json.loads(raw)
            prior_depths.append(int(summary.get("top_band_depth", 0)))
    if not prior_depths:
        return (0, 0)
    return (max(prior_depths), len(prior_depths))


def _prior_free_agent_history(conn: sqlite3.Connection, current_class_year: int) -> Tuple[int, int]:
    """Return (min prior free_agent_count, count of prior classes with a stored summary)."""
    prior_counts: List[int] = []
    for y in range(1, current_class_year):
        raw = get_state(conn, f"rookie_class_summary_{y}")
        if raw is not None:
            summary = json.loads(raw)
            prior_counts.append(int(summary.get("free_agent_count", 0)))
    if not prior_counts:
        return (0, 0)
    return (min(prior_counts), len(prior_counts))


def _payload_to_dict(payload: "RookiePreviewPayload") -> Dict[str, Any]:
    return {
        "season_id": payload.season_id,
        "class_year": payload.class_year,
        "source": payload.source,
        "class_size": payload.class_size,
        "archetype_distribution": dict(payload.archetype_distribution),
        "top_band_depth": payload.top_band_depth,
        "free_agent_count": payload.free_agent_count,
        "storylines": [
            {
                "template_id": s.template_id,
                "sentence": s.sentence,
                "fact": dict(s.fact),
            }
            for s in payload.storylines
        ],
    }


def _payload_from_dict(entry: Dict[str, Any]) -> "RookiePreviewPayload":
    storylines = tuple(
        RookieStoryline(
            template_id=s["template_id"],
            sentence=s["sentence"],
            fact=s["fact"],
        )
        for s in entry.get("storylines", [])
    )
    return RookiePreviewPayload(
        season_id=entry["season_id"],
        class_year=int(entry["class_year"]),
        source=entry["source"],
        class_size=int(entry["class_size"]),
        archetype_distribution={k: int(v) for k, v in entry.get("archetype_distribution", {}).items()},
        top_band_depth=int(entry["top_band_depth"]),
        free_agent_count=int(entry["free_agent_count"]),
        storylines=storylines,
    )


def build_rookie_class_preview(
    conn: sqlite3.Connection,
    season_id: str,
    class_year: int,
) -> RookiePreviewPayload:
    """Compute or load the Rookie Class Preview beat payload. Idempotent per season_id.

    Reads the V2-A prospect pool when present, falls back to V1 free agents otherwise.
    Never mutates either source.
    """
    # Step 1: cache check
    cached_for = get_state(conn, "offseason_rookie_preview_for")
    if cached_for == season_id:
        raw = get_state(conn, "offseason_rookie_preview_json") or ""
        if raw:
            cached = _payload_from_dict(json.loads(raw))
            if cached.class_year == class_year:
                return cached

    # Step 2: load source data
    prospects = load_prospect_pool(conn, class_year=class_year)
    free_agents = load_free_agents(conn)
    free_agent_count = len(free_agents)

    # Step 3: compute base fields from source
    if prospects:
        source = "prospect_pool"
        class_size = len(prospects)

        archetype_distribution: Dict[str, int] = {}
        for p in prospects:
            arch = p.public_archetype_guess
            archetype_distribution[arch] = archetype_distribution.get(arch, 0) + 1

        top_band_depth = sum(
            1 for p in prospects if _prospect_band_low_mean(p) >= _TOP_BAND_THRESHOLD
        )
    else:
        source = "legacy_free_agents"
        class_size = len(free_agents)
        archetype_distribution = {}
        top_band_depth = sum(1 for fa in free_agents if fa.overall() >= _TOP_BAND_THRESHOLD)

    # Step 4: build storylines
    storylines: List[RookieStoryline] = []

    if source == "prospect_pool":
        # --- archetype_demand and ai_cluster (both need club profiles) ---
        profiles = load_club_recruitment_profiles(conn)
        total_clubs = len(profiles)

        if total_clubs > 0:
            # Determine top archetype per club (deterministic tiebreak: highest value then alpha)
            club_top_archetypes: List[str] = []
            for profile in profiles.values():
                top_arch = max(
                    profile.archetype_priorities,
                    key=lambda a: (float(profile.archetype_priorities[a]), a),
                )
                club_top_archetypes.append(top_arch)

            # Count how many clubs have each top archetype
            arch_counts: Dict[str, int] = {}
            for arch in club_top_archetypes:
                arch_counts[arch] = arch_counts.get(arch, 0) + 1

            leading_arch = max(arch_counts, key=lambda a: (arch_counts[a], a))
            leading_count = arch_counts[leading_arch]

            # archetype_demand: leading archetype is top for >= ceil(total/2) clubs
            threshold = math.ceil(total_clubs / 2)
            if leading_count >= threshold:
                storylines.append(RookieStoryline(
                    template_id="archetype_demand",
                    sentence=(
                        f"{leading_arch} in heavy demand: {leading_count} of {total_clubs} clubs"
                        f" prioritizing them this off-season"
                    ),
                    fact={
                        "archetype": leading_arch,
                        "count": leading_count,
                        "total": total_clubs,
                    },
                ))

            # top_band_depth: current depth >= 1.2 * prior max AND >= 1 prior class
            prior_max, prior_count = _prior_top_band_history(conn, class_year)
            if prior_count >= 1 and top_band_depth >= 1 and top_band_depth >= _DEEPEST_CLASS_FACTOR * prior_max:
                storylines.append(RookieStoryline(
                    template_id="top_band_depth",
                    sentence=f"Deepest top-band class in {prior_count} seasons",
                    fact={
                        "current_depth": top_band_depth,
                        "prior_max": prior_max,
                        "prior_classes_considered": prior_count,
                    },
                ))

            # ai_cluster: leading archetype has >= 3 clubs AND is strict top (no tie)
            second_highest = sorted(arch_counts.values(), reverse=True)
            is_strict_top = len(second_highest) < 2 or second_highest[0] > second_highest[1]
            if leading_count >= 3 and is_strict_top:
                storylines.append(RookieStoryline(
                    template_id="ai_cluster",
                    sentence=f"{leading_count} clubs clustering on {leading_arch}",
                    fact={
                        "archetype": leading_arch,
                        "count": leading_count,
                    },
                ))
        else:
            # No profiles: still check top_band_depth
            prior_max, prior_count = _prior_top_band_history(conn, class_year)
            if prior_count >= 1 and top_band_depth >= 1 and top_band_depth >= _DEEPEST_CLASS_FACTOR * prior_max:
                storylines.append(RookieStoryline(
                    template_id="top_band_depth",
                    sentence=f"Deepest top-band class in {prior_count} seasons",
                    fact={
                        "current_depth": top_band_depth,
                        "prior_max": prior_max,
                        "prior_classes_considered": prior_count,
                    },
                ))

    # free_agent_crop applies in both modes
    prior_min, prior_count = _prior_free_agent_history(conn, class_year)
    if prior_count >= 1 and free_agent_count <= prior_min:
        storylines.append(RookieStoryline(
            template_id="free_agent_crop",
            sentence=f"Lightest free-agent crop in {prior_count} seasons",
            fact={
                "current_count": free_agent_count,
                "prior_min": prior_min,
                "prior_classes_considered": prior_count,
            },
        ))

    # Step 5: persist class summary for future comparisons
    class_summary = {
        "class_size": class_size,
        "top_band_depth": top_band_depth,
        "free_agent_count": free_agent_count,
    }
    set_state(conn, f"rookie_class_summary_{class_year}", json.dumps(class_summary))

    # Step 6: build, persist, and return the payload
    payload = RookiePreviewPayload(
        season_id=season_id,
        class_year=class_year,
        source=source,
        class_size=class_size,
        archetype_distribution=archetype_distribution,
        top_band_depth=top_band_depth,
        free_agent_count=free_agent_count,
        storylines=tuple(storylines),
    )

    set_state(conn, "offseason_rookie_preview_json", json.dumps(_payload_to_dict(payload)))
    set_state(conn, "offseason_rookie_preview_for", season_id)
    conn.commit()

    return payload


__all__ = [
    "HallOfFameInductee",
    "InductionPayload",
    "RatifiedRecord",
    "RatificationPayload",
    "RookiePreviewPayload",
    "RookieStoryline",
    "build_rookie_class_preview",
    "induct_hall_of_fame",
    "ratify_records",
]
