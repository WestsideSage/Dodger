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
    load_league_records,
    load_player_career_stats,
    load_prospect_pool,
    load_recruitment_signings,
    load_retired_players,
    load_user_bid_player_ids,
    load_season,
    load_season_outcome,
    load_standings,
)
from .signing_day_payload import build_signing_cards
from .stats import PlayerMatchStats

# Maximum size of the *user's* roster for recruiting purposes. Club creation
# lets a custom club draft up to 10 players, and the official ruleset allows a
# 12-player roster, so the recruiting gate must sit above the creation maximum —
# otherwise a club built at the creation cap is permanently unable to recruit.
# (AI clubs are trimmed separately in offseason_ceremony.)
MAX_USER_ROSTER = 12


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
                    # OVR is an integer scale everywhere player-facing; stored
                    # rows may carry floats from older saves, so round here the
                    # same way the development beat below does (no "55.7 OVR").
                    "ovr_final": int(round(float(row.get("overall", 0)))),
                    "career_elims": int((career or {}).get("total_eliminations", 0)),
                    "championships": int((career or {}).get("championships", 0)),
                    "seasons_played": int((career or {}).get("seasons_played", 0)),
                    # Playtest 3 F-10: the farewell card's career length must
                    # include the synthetic prior seasons seeded for curated
                    # veterans (V18 Task 3) — a 33-year-old retiree displayed
                    # "3 seasons" because only recorded sim seasons counted.
                    # Stats (elims) stay recorded-only; length is biography.
                    "career_seasons": int((career or {}).get("seasons_played", 0))
                    + int((career or {}).get("seasons_played_prior", 0)),
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
            # Phase 5 — Growth legibility: pass through per-attribute deltas and
            # potential ceiling so the frontend can render which attributes moved.
            raw_attr_deltas = row.get("attr_deltas") or {}
            attr_deltas = {k: int(v) for k, v in raw_attr_deltas.items()} if raw_attr_deltas else {}
            players.append(
                {
                    "name": row.get("player_name", row.get("player_id", "")),
                    "ovr_before": ovr_before,
                    "ovr_after": ovr_after,
                    "delta": ovr_after - ovr_before,
                    "attr_deltas": attr_deltas,
                    "potential_ceiling": row.get("potential_ceiling"),
                }
            )
        # Playtest 3 F-7: the TRAINING staff-focus credit (+0.2 OVR/week,
        # cap 8) is disclosed in Program Settings but had no visible
        # accounting in any results surface. Itemize the season's banked
        # credit here, computed by the same helper the growth model uses.
        training_credit = None
        if season is not None and player_club_id:
            from .offseason_ceremony import (
                TRAINING_CREDIT_PER_WEEK,
                TRAINING_CREDIT_WEEK_CAP,
                training_practice_credit,
            )

            weeks, credit_ovr = training_practice_credit(
                conn, season.season_id, player_club_id
            )
            training_credit = {
                "weeks": weeks,
                "credited_weeks": min(TRAINING_CREDIT_WEEK_CAP, weeks),
                "week_cap": TRAINING_CREDIT_WEEK_CAP,
                "per_week_ovr": TRAINING_CREDIT_PER_WEEK,
                "credit_ovr": round(credit_ovr, 1),
            }
        return {"players": players, "training_credit": training_credit}

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
        # Rank the recap table by the EXACT playoff-seeding key (not load_standings'
        # order). On an official points-tie the two can diverge, which would let the
        # table highlight the player inside the top-cut line while the missed-playoffs
        # banner (also seeded by this key) says they missed — one fact, two ways, on
        # one screen. Seeding the table here makes row rank == banner finish ==
        # playoff qualification by construction.
        # Codex playtest issue 12: on official careers the survivor-based
        # elimination differential is honestly zero (V20 §7.3 cleanup), so
        # the recap's "Elim ±" column rendered 0 for every club — a column
        # that reads as broken. Officials show the GAME-POINT differential
        # (the stat that actually ranks them); diff_kind tells the UI which
        # label to draw.
        is_official_career = (get_state(conn, "ruleset_selection") or "").startswith("official")
        recap: dict[str, Any] = {
            "diff_kind": "game_points" if is_official_career else "survivors",
            "standings": [
                {
                    "rank": index + 1,
                    "club_name": club_name(row.club_id),
                    "wins": row.wins,
                    "losses": row.losses,
                    "draws": row.draws,
                    "points": row.points,
                    "diff": (
                        row.game_point_differential
                        if is_official_career
                        else row.elimination_differential
                    ),
                    "is_player_club": row.club_id == player_club_id,
                }
                for index, row in enumerate(sorted(standings, key=_playoff_seeding_key))
            ]
        }
        missed = _missed_playoffs_block(conn, standings, player_club_id, season=season)
        if missed is not None:
            recap["missed_playoffs"] = missed
        # V22 Phase 2: the season's books, settled at offseason init. Only
        # attached when the persisted ledger belongs to THIS season (an older
        # save mid-migration must not show last year's money).
        from .economy import load_season_finances

        finances = load_season_finances(conn)
        if finances and season is not None and finances.get("season_id") == season.season_id:
            recap["finances"] = finances
        # V23: the season's league movement — who went up, who came down,
        # where the user plays next season, and who rules the world.
        if season is not None:
            pyramid_block = _pyramid_movement_block(
                conn, season.season_id, player_club_id, club_name
            )
            if pyramid_block is not None:
                recap["pyramid"] = pyramid_block
        return recap

    if beat_key == "records_ratified":
        records_book_empty = len(load_league_records(conn)) == 0
        return {
            "records": _parse_record_entries(records_json, player_club_id),
            "records_book_empty": records_book_empty,
        }

    if beat_key == "hof_induction":
        return {"inductees": _parse_hof_entries(hof_json)}

    if beat_key == "recruitment":
        signed_count = int(get_state(conn, "offseason_draft_signed_count") or "0")
        signing_limit = 3
        roster_limit = MAX_USER_ROSTER
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
        other_signings: list = []
        if season is not None:
            try:
                signings = load_recruitment_signings(conn, season.season_id)
            except Exception:
                signings = ()
            # Signings reference the CURRENT class pool — the same class the
            # picker signs from (the previous +1 join predated the contested
            # flow and could never resolve a prospect).
            class_year = season_number or 1
            try:
                pool = load_prospect_pool(conn, class_year)
            except Exception:
                pool = ()
            prospects_by_id = {p.player_id: p for p in pool}
            actions_by_player = load_json_state(
                conn, "prospect_recruitment_actions_json", {}
            ) or {}
            try:
                user_bids = load_user_bid_player_ids(conn, season.season_id)
            except Exception:
                user_bids = set()
            signing_cards = build_signing_cards(
                signings=signings,
                rosters=rosters,
                prospects_by_id=prospects_by_id,
                clubs=clubs,
                player_club_id=player_club_id,
                actions_by_player=actions_by_player,
                user_bid_player_ids=user_bids,
            )
            # Rival Signing Day moves, for surfaces that render the compact
            # list instead of the card grid.
            for signing in signings:
                if signing.club_id == player_club_id:
                    continue
                signed = next(
                    (
                        p
                        for p in rosters.get(signing.club_id, [])
                        if p.id == signing.player_id
                    ),
                    None,
                )
                club = clubs.get(signing.club_id)
                other_signings.append(
                    {
                        "name": signed.name if signed else signing.player_id,
                        "ovr": signed.overall_skill() if signed else 0,
                        "age": signed.age if signed else None,
                        "club_name": club.name if club else signing.club_id,
                    }
                )

        # Playtest 3 F-8: the sign-over-cut swap picker needs the user's
        # roster (who could be released), with open-promise flags so cutting
        # a promised player is a warned, deliberate choice.
        from .roster_moves import open_promise_player_ids

        promised_roster_ids = open_promise_player_ids(conn)
        user_roster_rows = [
            {
                "id": player.id,
                "name": player.name,
                "overall": player.overall_skill(),
                "age": player.age,
                "promised": player.id in promised_roster_ids,
            }
            for player in sorted(
                player_roster, key=lambda p: (p.overall_skill(), p.id)
            )
        ]

        return {
            "player_signing": player_signing,
            "other_signings": other_signings,
            "signings": signing_cards,
            "available_prospects": available_recruitment_choices(conn, season_number),
            "signed_count": signed_count,
            "signing_limit": signing_limit,
            "remaining_signings": max(0, signing_limit - signed_count),
            "roster_size": len(player_roster),
            "roster_limit": roster_limit,
            "user_roster": user_roster_rows,
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
            # Playtest 3: the class's upside count (band tops out at 70+) —
            # the headline metric. The floor count above stays as the
            # "sure things" secondary stat.
            "ceiling_prospects": int(payload_dict.get("ceiling_band_depth", 0)),
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

    # V23: every ceremony surface built from `standings` (recap table,
    # champion record, missed-playoffs banner) reads the USER'S DIVISION on
    # pyramid saves — the world's other 21 clubs live in the standings
    # screen's pyramid view, not the ceremony.
    from .world import pyramid_world_active

    is_pyramid = pyramid_world_active(conn)
    if is_pyramid and season_id and standings:
        from .persistence import load_division_map

        _division_map = load_division_map(conn, season_id)
        _seat = _division_map.get(get_state(conn, "player_club_id") or "")
        if _seat is not None:
            standings = [
                row
                for row in standings
                if _division_map.get(row.club_id)
                and _division_map[row.club_id].division_id == _seat.division_id
            ]

    next_preview: Any = None
    if beat_key == "schedule_reveal":
        season_number = cursor.season_number or 1
        root_seed = stored_root_seed(conn)
        if is_pyramid and season is not None:
            # Preview the real next season: movement applied, four divisions.
            from .pyramid_postseason import next_season_assignment
            from .world import create_pyramid_season

            assignment = next_season_assignment(conn, season.season_id)
            if assignment is not None:
                next_preview = create_pyramid_season(
                    f"season_{season_number + 1}",
                    season.year + 1,
                    assignment,
                    root_seed=root_seed,
                )
        if next_preview is None:
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
    records_book_empty = len(load_league_records(conn)) == 0
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
        records_book_empty=records_book_empty,
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
        # Playtest 3 F-8: a full roster no longer turns Signing Day read-only —
        # the picker stays live and a pick at 12/12 goes through the
        # release-to-sign swap. Only spent class slots close recruiting.
        "can_recruit": (
            cursor.state == CareerState.SEASON_COMPLETE_RECRUITMENT_PENDING
            and int(get_state(conn, "offseason_draft_signed_count") or "0") < 3
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


def _parse_record_entries(raw: Optional[str], player_club_id: str = "") -> list[dict[str, Any]]:
    """Structured league-record entries for the records_ratified beat card.

    Phase 7: each entry now carries holder_club_id and is_my_club so the
    frontend can render the My Club / League scope filter without a round-trip.
    """
    out: list[dict[str, Any]] = []
    for entry in _json_list(raw):
        if not isinstance(entry, dict):
            continue
        holder_club_id = str(entry.get("holder_club_id", ""))
        out.append(
            {
                "record_id": str(entry.get("record_type", "")),
                "record_type": str(entry.get("record_type", "")),
                "holder_name": str(entry.get("holder_name", entry.get("holder_id", "Unknown"))),
                "previous_value": float(entry.get("previous_value", 0.0)),
                "new_value": float(entry.get("new_value", 0.0)),
                "detail": str(entry.get("detail", "")),
                "proof_source": f"record:{entry.get('record_type', '')}",
                "holder_club_id": holder_club_id,
                "is_my_club": bool(player_club_id and holder_club_id == player_club_id),
                # Milestone-vs-bookkeeping: missing field (pre-existing saves)
                # defaults to the marquee treatment.
                "is_new_holder": bool(entry.get("is_new_holder", True)),
                "previous_holder_name": str(entry.get("previous_holder_name", "")),
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


def _playoff_seeding_key(row):
    """The exact ordering playoff qualification uses (mirrors playoffs.top_four_seeds).

    The recap table, the missed-playoffs finish, and the playoff cut are all
    ranked by this single key so a club's displayed rank can never contradict
    whether it qualified. (Distinct from load_standings' official-season game-point
    tiebreaker, which orders the in-season Standings screen.)
    """
    return (-row.points, -row.elimination_differential, row.club_id)


_PROMOTION_TARGET = {"challenger": "premier", "district": "challenger"}
_RELEGATION_TARGET = {"premier": "challenger", "challenger": "district"}


def _pyramid_movement_block(
    conn: sqlite3.Connection,
    season_id: str,
    player_club_id: str,
    club_name,
) -> Optional[dict[str, Any]]:
    """V23: the recap's league-movement story, from the postseason ledger.

    ``None`` on legacy saves or while the world's postseason is unfinished.
    Every line derives from the persisted ledger (champions, promotion
    playoff, relegation, Worlds) plus the same next-season assignment
    ``begin_next_season`` will apply — the recap can never promise a
    different world than the one the player wakes up in.
    """
    from .persistence import load_division_map
    from .pyramid_postseason import load_postseason_ledger, next_season_assignment
    from .world import DIVISIONS, division_by_id, pyramid_world_active

    if not pyramid_world_active(conn):
        return None
    ledger = load_postseason_ledger(conn, season_id)
    if not (ledger and ledger.get("complete")):
        return None

    division_map = load_division_map(conn, season_id)
    seat = division_map.get(player_club_id)
    assignment = next_season_assignment(conn, season_id) or {}
    user_next_division_id = next(
        (
            division_id
            for division_id, club_ids in assignment.items()
            if player_club_id in club_ids
        ),
        None,
    )
    movement = "stays"
    if seat is not None and user_next_division_id and user_next_division_id != seat.division_id:
        movement = (
            "promoted"
            if division_by_id(user_next_division_id).tier < seat.tier
            else "relegated"
        )

    champions = ledger.get("champions") or {}
    promoted = ledger.get("promoted") or {}
    relegated = ledger.get("relegated") or {}
    return {
        "champions": [
            {
                "division_id": division.division_id,
                "division_name": division.name,
                "club_name": club_name(champions[division.division_id]),
            }
            for division in DIVISIONS
            if division.division_id in champions
        ],
        "promoted": [
            {
                "from_division": division_by_id(division_id).name,
                "to_division": division_by_id(_PROMOTION_TARGET[division_id]).name,
                "clubs": [club_name(club_id) for club_id in club_ids],
            }
            for division_id, club_ids in promoted.items()
            if division_id in _PROMOTION_TARGET
        ],
        "relegated": [
            {
                "from_division": division_by_id(division_id).name,
                "to_division": division_by_id(_RELEGATION_TARGET[division_id]).name,
                "clubs": [club_name(club_id) for club_id in club_ids],
            }
            for division_id, club_ids in relegated.items()
            if division_id in _RELEGATION_TARGET
        ],
        "worlds": ledger.get("worlds"),
        "user": {
            "movement": movement,
            "division_id": user_next_division_id or (seat.division_id if seat else None),
            "division_name": (
                division_by_id(user_next_division_id).name
                if user_next_division_id
                else (seat.division_name if seat else None)
            ),
        },
    }


def _missed_playoffs_block(
    conn: sqlite3.Connection,
    standings: list,
    player_club_id: str,
    *,
    season: Any = None,
) -> Optional[dict[str, Any]]:
    """Post-hoc "you missed the playoff cut" facts for the recap beat, or ``None``.

    Work item #3 (2026-06 playtest): a player who fast-forwarded to "pre-playoffs"
    (or simply finished outside the top seeds) was dropped into the offseason with
    no statement that their season ended without a berth. This returns the raw
    numbers the recap banner needs — ``finish`` (1-based position), ``cutoff``
    (``PLAYOFF_FIELD_SIZE``), ``total`` (real club count) — and ``None`` when the
    club MADE the cut, so the banner only ever appears on a genuine miss.

    Faithfulness fences (ADR 0002):

    * The finish position is derived from the EXACT seeding key the playoffs use
      (``-points, -elimination_differential, club_id`` — mirrored from
      ``playoffs.top_four_seeds``), NOT the recap's display order. For official
      seasons ``load_standings`` breaks ties on game points, which can diverge
      from the seeding tiebreaker; sourcing ``finish`` from the seeding key makes
      ``made`` ⇔ ``finish <= cutoff`` true by construction, so the banner can
      never say "finished Nth, top N qualify, you missed".
    * Playoff-field membership prefers the PERSISTED bracket seeds (literally the
      clubs that played the playoffs) and falls back to ``top_four_seeds`` over
      the live standings — both agree in normal play; the bracket is authoritative
      when present. "Missed the cut" is therefore distinct from "lost in the
      playoffs": a club in ``bracket.seeds`` that lost its semifinal still made it
      and gets no banner.
    """
    if not player_club_id or not standings:
        return None
    if not any(getattr(row, "club_id", None) == player_club_id for row in standings):
        return None

    from .playoffs import PLAYOFF_FIELD_SIZE, top_four_seeds

    cutoff = PLAYOFF_FIELD_SIZE
    total = len(standings)
    # A league smaller than the cut has no playoff race to miss (and
    # create_semifinal_bracket would never have run), so there is nothing to
    # surface.
    if total <= cutoff:
        return None

    # Authoritative playoff field: the persisted bracket seeds when a bracket
    # was created (who actually played), else the live top-four seeding.
    field: set[str] = set()
    season_id = getattr(season, "season_id", None)
    if season_id:
        try:
            from .persistence import load_playoff_bracket

            bracket = load_playoff_bracket(conn, season_id)
        except Exception:
            bracket = None
        if bracket is not None and bracket.seeds:
            field = set(bracket.seeds)
    if not field:
        field = set(top_four_seeds(standings))

    if player_club_id in field:
        return None  # made the cut — no missed-playoffs banner

    # Finish position from the SAME key top_four_seeds sorts by, so the displayed
    # cutoff and this position can never contradict the membership decision.
    seeded = sorted(standings, key=_playoff_seeding_key)
    finish = next(
        (index + 1 for index, row in enumerate(seeded) if row.club_id == player_club_id),
        None,
    )
    if finish is None:
        return None

    return {"finish": int(finish), "cutoff": int(cutoff), "total": int(total)}


def load_all_clubs(conn: sqlite3.Connection):
    from .persistence import load_clubs

    return load_clubs(conn)
