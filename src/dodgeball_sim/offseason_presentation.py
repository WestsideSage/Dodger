from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from .career_state import CareerState
from .development import calculate_potential_tier
from .offseason_ceremony import (
    OFFSEASON_CEREMONY_BEATS,
    available_recruitment_choices,
    build_offseason_ceremony_beat,
    compute_active_beats,
    create_next_manager_season,
    stored_root_seed,
)
from .persistence import (
    fetch_season_player_stats,
    get_state,
    load_all_rosters,
    load_awards,
    load_club_trophies,
    load_free_agents,
    load_json_state,
    load_player_career_stats,
    load_prospect_pool,
    load_recruitment_signings,
    load_retired_players,
    load_season,
    load_season_outcome,
    load_standings,
)
from .signing_day_payload import build_signing_cards
from .stats import PlayerMatchStats


def load_active_beats(conn: sqlite3.Connection) -> list:
    """Load the stored active beat list, falling back to the full sequence."""
    raw = get_state(conn, "offseason_active_beats_json")
    if raw:
        try:
            beats = json.loads(raw)
            if beats and isinstance(beats, list):
                return beats
        except (TypeError, ValueError):
            pass
    return list(OFFSEASON_CEREMONY_BEATS)


def build_beat_payload(
    beat_key: str,
    *,
    awards: list,
    clubs: dict,
    rosters: dict,
    standings: list,
    ret_rows: list,
    season: Any,
    season_outcome: Any,
    next_preview: Any,
    signed_player_id: str,
    dev_rows: Optional[list] = None,
    player_club_id: str = "",
    rookie_preview_json: Optional[str] = None,
    records_json: Optional[str] = None,
    hof_json: Optional[str] = None,
    season_number: int = 1,
    conn: sqlite3.Connection,
) -> dict:
    dev_rows = dev_rows or []

    def club_name(club_id: str) -> str:
        club = clubs.get(club_id)
        return club.name if club else club_id

    def find_player(player_id: str):
        for roster in rosters.values():
            for player in roster:
                if player.id == player_id:
                    return player
        return None

    if beat_key == "awards":
        _AWARD_PRESTIGE = {
            "mvp": 3,
            "best_thrower": 2,
            "best_catcher": 1,
            "best_newcomer": 0,
        }
        _AWARD_NAME = {
            "mvp": "MVP",
            "best_thrower": "Best Thrower",
            "best_catcher": "Best Catcher",
            "best_newcomer": "Best Newcomer",
        }
        sorted_awards = sorted(
            awards,
            key=lambda a: _AWARD_PRESTIGE.get(a.award_type, -1),
            reverse=True,
        )
        season_stats: dict = {}
        if season is not None:
            season_stats = fetch_season_player_stats(conn, season.season_id)

        result = []
        seen_player_ids: set[str] = set()
        for award in sorted_awards:
            if award.player_id in seen_player_ids:
                continue
            seen_player_ids.add(award.player_id)
            player = find_player(award.player_id)
            career = load_player_career_stats(conn, award.player_id) or {}
            career_throws = int(career.get("total_eliminations", 0))
            career_catches = int(career.get("total_catches_made", 0))
            stats = season_stats.get(award.player_id, PlayerMatchStats())
            # career_stat tracks the SAME metric as season_stat so the two
            # numbers on an award card are comparable (B10).
            if award.award_type == "best_thrower":
                season_stat = stats.eliminations_by_throw
                season_stat_label = f"{season_stat} throw elims"
                career_stat = career_throws
            elif award.award_type == "best_catcher":
                season_stat = stats.catches_made
                season_stat_label = f"{season_stat} catches"
                career_stat = career_catches
            else:  # mvp, best_newcomer
                season_stat = stats.eliminations_by_throw + stats.catches_made
                season_stat_label = f"{season_stat} season elims"
                career_stat = career_throws + career_catches
            result.append(
                {
                    "player_name": player.name if player else award.player_id,
                    "club_name": club_name(award.club_id),
                    "award_type": award.award_type,
                    "award_name": _AWARD_NAME.get(
                        award.award_type,
                        award.award_type.replace("_", " ").title(),
                    ),
                    "season_stat": int(season_stat),
                    "season_stat_label": season_stat_label,
                    "career_stat": int(career_stat),
                    "ovr": player.overall_skill() if player else 0,
                    "extra_stats": (
                        {
                            "throw_elims": int(stats.eliminations_by_throw),
                            "catches": int(stats.catches_made),
                            "times_eliminated": int(stats.times_eliminated),
                            "matches": int(stats.matches) if hasattr(stats, "matches") else 0,
                        }
                        if award.award_type == "mvp"
                        else None
                    ),
                }
            )
        return {"awards": result}

    if beat_key == "retirements":
        retired_by_id = {row["player_id"]: row.get("player") for row in load_retired_players(conn)}
        retirees = []
        for row in ret_rows:
            player_id = row.get("player_id", "")
            career = load_player_career_stats(conn, player_id)
            player_obj = retired_by_id.get(player_id)
            potential = player_obj.traits.potential if player_obj else 0.0
            retirees.append(
                {
                    "name": row.get("player_name", player_id),
                    "ovr_final": float(row.get("overall", 0)),
                    "career_elims": int((career or {}).get("total_eliminations", 0)),
                    "championships": int((career or {}).get("championships", 0)),
                    "seasons_played": int((career or {}).get("seasons_played", 0)),
                    "potential_tier": calculate_potential_tier(potential),
                }
            )
        return {"retirees": retirees}

    if beat_key == "development":
        player_rows = [
            row for row in dev_rows if row.get("club_id") == player_club_id
        ]
        player_rows_sorted = sorted(
            player_rows, key=lambda r: -abs(float(r.get("delta", 0)))
        )
        players = []
        for row in player_rows_sorted:
            ovr_before = int(round(float(row.get("before", 0))))
            ovr_after = int(round(float(row.get("after", 0))))
            # Derive the delta from the displayed OVR values so the badge always
            # agrees with the before -> after numbers (B11).
            players.append(
                {
                    "name": row.get("player_name", row.get("player_id", "")),
                    "ovr_before": ovr_before,
                    "ovr_after": ovr_after,
                    "delta": ovr_after - ovr_before,
                }
            )
        return {"players": players}

    if beat_key == "champion":
        if season_outcome and season_outcome.champion_club_id:
            trophies = load_club_trophies(conn)
            title_count = sum(
                1
                for trophy in trophies
                if trophy["club_id"] == season_outcome.champion_club_id
                and trophy["trophy_type"] == "championship"
            )
            row = next(
                (standing for standing in standings if standing.club_id == season_outcome.champion_club_id),
                None,
            )
            return {
                "champion": {
                    "club_name": club_name(season_outcome.champion_club_id),
                    "wins": row.wins if row else 0,
                    "losses": row.losses if row else 0,
                    "draws": row.draws if row else 0,
                    "title_count": title_count,
                }
            }
        return {}

    if beat_key == "recap":
        return {
            "standings": [
                {
                    "rank": index + 1,
                    "club_name": club_name(row.club_id),
                    "wins": row.wins,
                    "losses": row.losses,
                    "draws": row.draws,
                    "points": row.points,
                    "diff": row.elimination_differential,
                    "is_player_club": row.club_id == player_club_id,
                }
                for index, row in enumerate(standings)
            ]
        }

    if beat_key == "records_ratified":
        return {"records": _parse_record_entries(records_json)}

    if beat_key == "hof_induction":
        return {"inductees": _parse_hof_entries(hof_json)}

    if beat_key == "recruitment":
        signed_count = int(get_state(conn, "offseason_draft_signed_count") or "0")
        signing_limit = 3
        roster_limit = 9
        player_roster = rosters.get(player_club_id, [])
        player_signing = None
        if signed_player_id:
            player = find_player(signed_player_id)
            if player:
                player_signing = {
                    "name": player.name,
                    "ovr": player.overall_skill(),
                    "age": player.age,
                }

        # Card-grid payload: enrich each persisted signing with the user's
        # interaction history for that prospect (scouted/contacted/visited),
        # the prospect's role, and a one-line reason tying the outcome to
        # those interactions.
        signing_cards: list = []
        if season is not None:
            try:
                signings = load_recruitment_signings(conn, season.season_id)
            except Exception:
                signings = ()
            class_year = (season_number or 1) + 1
            try:
                pool = load_prospect_pool(conn, class_year)
            except Exception:
                pool = ()
            prospects_by_id = {p.player_id: p for p in pool}
            actions_by_player = load_json_state(
                conn, "prospect_recruitment_actions_json", {}
            ) or {}
            signing_cards = build_signing_cards(
                signings=signings,
                rosters=rosters,
                prospects_by_id=prospects_by_id,
                clubs=clubs,
                player_club_id=player_club_id,
                actions_by_player=actions_by_player,
            )

        return {
            "player_signing": player_signing,
            "other_signings": [],
            "signings": signing_cards,
            "available_prospects": available_recruitment_choices(conn, season_number),
            "signed_count": signed_count,
            "signing_limit": signing_limit,
            "remaining_signings": max(0, signing_limit - signed_count),
            "roster_size": len(player_roster),
            "roster_limit": roster_limit,
        }

    if beat_key == "schedule_reveal":
        if next_preview is None:
            return {"fixtures": [], "season_label": "", "prediction": ""}
        fixtures = [
            {
                "week": match.week,
                "home": club_name(match.home_club_id),
                "away": club_name(match.away_club_id),
                "is_player_match": (
                    match.home_club_id == player_club_id or match.away_club_id == player_club_id
                ),
            }
            for match in next_preview.scheduled_matches
        ]
        prediction = ""
        player_match = next(
            (
                match
                for match in next_preview.scheduled_matches
                if match.home_club_id == player_club_id or match.away_club_id == player_club_id
            ),
            None,
        )
        if player_match:
            try:
                from .rng import DeterministicRNG, derive_seed
                from .voice_pregame import render_matchup_framing

                root_seed = stored_root_seed(conn)
                rng = DeterministicRNG(derive_seed(root_seed, "schedule_reveal_prediction"))
                prediction = render_matchup_framing(
                    club_name(player_match.home_club_id),
                    club_name(player_match.away_club_id),
                    rng,
                )
            except Exception:
                prediction = ""
        return {
            "season_label": str(next_preview.year) if next_preview else "",
            "fixtures": fixtures,
            "prediction": prediction,
        }

    if beat_key == "rookie_class_preview":
        try:
            payload_dict = json.loads(rookie_preview_json or "{}") or {}
        except (TypeError, ValueError):
            payload_dict = {}
        archetype_dist: dict = payload_dict.get("archetype_distribution", {}) or {}
        storylines = [
            s.get("sentence", "")
            for s in (payload_dict.get("storylines", []) or [])
            if s.get("sentence")
        ]
        return {
            "class_size": int(payload_dict.get("class_size", 0)),
            "top_prospects": int(payload_dict.get("top_band_depth", 0)),
            "free_agents": int(payload_dict.get("free_agent_count", 0)),
            "archetypes": sorted(
                [{"name": k, "count": v} for k, v in archetype_dist.items()],
                key=lambda x: (-x["count"], x["name"]),
            ),
            "storylines": storylines,
        }

    return {}


def build_beat_response(conn: sqlite3.Connection, cursor) -> dict[str, Any]:
    active_beats = load_active_beats(conn)
    beat_index = max(0, min(int(cursor.offseason_beat_index or 0), len(active_beats) - 1))
    beat_key = active_beats[beat_index]
    is_last = beat_key == "schedule_reveal"
    is_recruitment = beat_key == "recruitment"

    # Self-heal: if the beat index has moved past recruitment but the career
    # state machine still says recruitment is pending, promote it now.
    # This can happen when recruitment was impossible (roster already full
    # going in) and the user advanced past the signing-day card.
    if (
        cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING
        and "recruitment" in active_beats
        and beat_index > active_beats.index("recruitment")
    ):
        from .career_state import advance as _state_advance
        from .persistence import save_career_state_cursor as _save_cursor

        cursor = _state_advance(
            cursor,
            CareerState.NEXT_SEASON_READY,
            offseason_beat_index=beat_index,
        )
        _save_cursor(conn, cursor)
        conn.commit()

    season_id = get_state(conn, "active_season_id")
    season = load_season(conn, season_id) if season_id else None
    clubs = load_all_clubs(conn)
    rosters = load_all_rosters(conn)
    standings = load_standings(conn, season_id) if season_id else []
    awards = load_awards(conn, season_id) if season_id else []
    season_outcome = load_season_outcome(conn, season_id) if season_id else None
    signed_player_id = get_state(conn, "offseason_draft_signed_player_id") or ""

    next_preview: Any = None
    if beat_key == "schedule_reveal":
        season_number = cursor.season_number or 1
        root_seed = stored_root_seed(conn)
        next_preview = create_next_manager_season(
            clubs,
            root_seed,
            season_number + 1,
            (season.year + 1) if season else 2026,
        )

    dev_rows = _load_json_list(conn, "offseason_development_json")
    ret_rows = _load_json_list(conn, "offseason_retirements_json")
    records_json = get_state(conn, "offseason_records_ratified_json")
    hof_json = get_state(conn, "offseason_hof_inducted_json")
    rookie_preview_json = get_state(conn, "offseason_rookie_preview_json")
    player_club_id = get_state(conn, "player_club_id") or ""

    canonical_index = OFFSEASON_CEREMONY_BEATS.index(beat_key)
    beat = build_offseason_ceremony_beat(
        beat_index=canonical_index,
        season=season,
        clubs=clubs,
        rosters=rosters,
        standings=standings,
        awards=awards,
        player_club_id=player_club_id,
        next_season=next_preview,
        development_rows=dev_rows,
        retirement_rows=ret_rows,
        draft_pool=load_free_agents(conn),
        signed_player_id=signed_player_id,
        season_outcome=season_outcome,
        records_payload_json=records_json,
        hof_payload_json=hof_json,
        rookie_preview_payload_json=rookie_preview_json,
    )
    payload = build_beat_payload(
        beat_key,
        awards=awards,
        clubs=clubs,
        rosters=rosters,
        standings=standings,
        ret_rows=ret_rows,
        season=season,
        season_outcome=season_outcome,
        next_preview=next_preview,
        signed_player_id=signed_player_id,
        dev_rows=dev_rows,
        player_club_id=player_club_id,
        rookie_preview_json=rookie_preview_json,
        records_json=records_json,
        hof_json=hof_json,
        season_number=cursor.season_number or 1,
        conn=conn,
    )

    return {
        "beat_index": beat_index,
        "total_beats": len(active_beats),
        "key": beat_key,
        "title": beat.title,
        "body": beat.body,
        "state": cursor.state.value,
        "can_advance": (
            (
                cursor.state == CareerState.SEASON_COMPLETE_OFFSEASON_BEAT
                and not is_last
                and not is_recruitment
            )
            or (cursor.state == CareerState.NEXT_SEASON_READY and not is_last)
        ),
        "can_recruit": (
            cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING
            and int(get_state(conn, "offseason_draft_signed_count") or "0") < 3
            and len(rosters.get(player_club_id, [])) < 9
        ),
        "can_begin_season": cursor.state == CareerState.NEXT_SEASON_READY,
        "signed_player_id": signed_player_id,
        "payload": payload,
    }


def _load_json_list(conn: sqlite3.Connection, key: str) -> list:
    try:
        loaded = json.loads(get_state(conn, key) or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return loaded if isinstance(loaded, list) else []


def _json_list(raw: Optional[str]) -> list:
    try:
        loaded = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return loaded if isinstance(loaded, list) else []


def _parse_record_entries(raw: Optional[str]) -> list[dict[str, Any]]:
    """Structured league-record entries for the records_ratified beat card."""
    out: list[dict[str, Any]] = []
    for entry in _json_list(raw):
        if not isinstance(entry, dict):
            continue
        out.append(
            {
                "record_id": str(entry.get("record_type", "")),
                "record_type": str(entry.get("record_type", "")),
                "holder_name": str(entry.get("holder_name", entry.get("holder_id", "Unknown"))),
                "previous_value": float(entry.get("previous_value", 0.0)),
                "new_value": float(entry.get("new_value", 0.0)),
                "detail": str(entry.get("detail", "")),
                "proof_source": f"record:{entry.get('record_type', '')}",
            }
        )
    return out


def _parse_hof_entries(raw: Optional[str]) -> list[dict[str, Any]]:
    """Structured Hall of Fame inductee entries for the hof_induction beat card."""
    out: list[dict[str, Any]] = []
    for entry in _json_list(raw):
        if not isinstance(entry, dict):
            continue
        out.append(
            {
                "player_id": str(entry.get("player_id", "")),
                "player_name": str(entry.get("player_name", entry.get("player_id", "Unknown"))),
                "legacy_score": float(entry.get("legacy_score", 0.0)),
                "threshold": float(entry.get("threshold", 0.0)),
                "reasons": [str(reason) for reason in (entry.get("reasons", []) or [])],
                "seasons_played": int(entry.get("seasons_played", 0)),
                "championships": int(entry.get("championships", 0)),
                "awards_won": int(entry.get("awards_won", 0)),
                "total_eliminations": int(entry.get("total_eliminations", 0)),
                "proof_source": f"career:{entry.get('player_id', '')}",
            }
        )
    return out


def load_all_clubs(conn: sqlite3.Connection):
    from .persistence import load_clubs

    return load_clubs(conn)
