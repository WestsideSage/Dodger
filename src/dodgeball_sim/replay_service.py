from __future__ import annotations

import json
import sqlite3
from typing import Any

from .awards import compute_match_mvp
from .broadcast import (
    build_commentary_inserts,
    build_playoff_frame,
    load_matchup_broadcast_frame,
)
from .career_state import CareerState, advance
from .match_orchestration import _choose_next_user_match_after_automation
from .persistence import (
    fetch_match,
    fetch_roster_snapshot,
    get_state,
    load_career_state_cursor,
    load_clubs,
    load_command_history,
    load_league_records,
    load_season,
    save_career_state_cursor,
)
from .replay_proof import build_replay_proof, event_detail, event_label
from .official_persistence import replay_state_from_dict, replay_state_to_dict
from .voice_register import TIER1_REGISTER, tier1
from .stats import PlayerMatchStats
from .web_status_service import career_state_payload
from typing import Any, Dict, Iterable
from .models import MatchSetup, Team
from .stats import PlayerMatchStats, extract_all_stats
from .copy_quality import title_label
from .analysis import MatchAnalysis
from .events import MatchEvent
from .narration import Lookup, narrate_event
from .dynasty_office import player_role, team_overall


def _enrich_moment_display(
    moment: dict[str, Any],
    name_map: dict[str, str],
    team_name_map: dict[str, str],
) -> dict[str, Any]:
    kind = moment.get("kind")

    def player(pid: Any) -> str:
        if not isinstance(pid, str) or not pid:
            return "Unknown player"
        return name_map.get(pid, pid)

    def team(tid: Any) -> str:
        if not isinstance(tid, str) or not tid:
            return "Unknown team"
        return team_name_map.get(tid, tid)

    enriched = dict(moment)
    try:
        if kind == "dramatic_catch":
            enriched["display_text"] = tier1(
                "moment.dramatic_catch.beat",
                catcher=player(moment.get("catcher_id")),
                returning=player(moment.get("returning_player_id")),
            )
        elif kind == "gassed_collapse":
            enriched["display_text"] = tier1(
                "moment.gassed_collapse.beat",
                player=player(moment.get("player_id")),
            )
        elif kind == "flood_throw":
            thrower_ids = moment.get("thrower_ids") or []
            enriched["display_text"] = tier1(
                "moment.flood_throw.beat",
                team=team(moment.get("thrower_team_id")),
                count=len(thrower_ids) if isinstance(thrower_ids, list) else 0,
            )
        elif kind == "late_game_escape":
            enriched["display_text"] = tier1(
                "banner.late_game_escape",
                survivor=player(moment.get("survivor_id")),
                attacker_count=moment.get("attacker_count", 0),
            )
        elif kind == "one_v_one_finale":
            enriched["display_text"] = tier1(
                "banner.one_v_one_finale",
                a=player(moment.get("player_a_id")),
                b=player(moment.get("player_b_id")),
            )
        elif kind == "comeback":
            enriched["display_text"] = tier1(
                "card.comeback",
                team=team(moment.get("team_id")),
                deficit=moment.get("deficit_at_low_point", 0),
                catches=moment.get("catches_during_comeback", 0),
            )
    except KeyError:
        pass
    return enriched


class ReplayError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _turning_point_selection(proof_events: list[dict[str, Any]]) -> tuple[str | None, int | None]:
    """Pick the key play with the biggest swing in living-count differential.

    The old report grabbed the FIRST hit/catch of the match and headlined it
    "turning point" — fake causality. This selection reuses the highlight
    swing metric (lead flips dominate, then delta size) over the truthful
    per-event score state. Comparisons never cross an official game boundary,
    because survivor counts genuinely reset between games.
    """
    from .highlights import _swing_score

    best_index: int | None = None
    best_score = 0.0
    previous: dict[str, Any] | None = None
    previous_game: Any = object()
    for index, proof in enumerate(proof_events):
        game = proof.get("game_number")
        if game != previous_game:
            previous = None
            previous_game = game
        if proof.get("is_key_play"):
            score = _swing_score(previous, proof)
            if best_index is None or score > best_score:
                best_index = index
                best_score = score
        previous = proof
    if best_index is None:
        return None, None
    return str(proof_events[best_index].get("summary", "")), best_index


def _game_segments(
    official_score_json: str | None,
    proof_events: list[dict[str, Any]],
    home_club_id: str,
) -> list[dict[str, Any]] | None:
    """Per-game story of an official match, from the persisted official score.

    Game results come straight from the ``official_score_json`` column written
    at simulation time; proof-index ranges come from the per-event
    ``game_number`` metadata (present on newly simulated matches — legacy
    event streams yield ``None`` ranges, and the segment strip still renders
    the truthful per-game results without jump targets).
    """
    if not official_score_json:
        return None
    try:
        meta = json.loads(official_score_json)
    except (TypeError, ValueError):
        return None
    games = meta.get("games") if isinstance(meta, dict) else None
    if not isinstance(games, list) or not games:
        return None
    a_is_home = str(meta.get("team_a_id", "")) == str(home_club_id)

    first_index: dict[int, int] = {}
    last_index: dict[int, int] = {}
    for index, proof in enumerate(proof_events):
        game_number = proof.get("game_number")
        if isinstance(game_number, int):
            first_index.setdefault(game_number, index)
            last_index[game_number] = index

    segments: list[dict[str, Any]] = []
    running_home = 0
    running_away = 0
    for game in games:
        if not isinstance(game, dict):
            continue
        number = int(game.get("game_number", 0) or 0)
        a_points = int(game.get("team_a_points", 0) or 0)
        b_points = int(game.get("team_b_points", 0) or 0)
        a_actives = int(game.get("final_active_a", 0) or 0)
        b_actives = int(game.get("final_active_b", 0) or 0)
        home_points, away_points = (a_points, b_points) if a_is_home else (b_points, a_points)
        home_actives, away_actives = (a_actives, b_actives) if a_is_home else (b_actives, a_actives)
        running_home += home_points
        running_away += away_points
        segments.append(
            {
                "game_number": number,
                "winner_club_id": game.get("winner_team_id"),
                "result_type": str(game.get("result_type", "") or ""),
                "home_points": home_points,
                "away_points": away_points,
                "home_running_points": running_home,
                "away_running_points": running_away,
                "home_final_actives": home_actives,
                "away_final_actives": away_actives,
                "first_proof_index": first_index.get(number),
                "last_proof_index": last_index.get(number),
            }
        )
    return segments or None


def _anchor_proof_index(moment: dict[str, Any], proof_events: list[dict[str, Any]]) -> int | None:
    """Resolve where in the proof timeline a moment belongs.

    Official moments carry per-game engine ticks plus a ``game_number``; rec
    moments share the event-tick coordinate directly. Exact tick matches
    prefer the catch resolution (the catch-driven moment kinds). When only a
    prior event exists the moment anchors there — i.e. "as of this point",
    never ahead of the moment. Returns ``None`` when nothing can be anchored
    truthfully (legacy streams without game metadata).
    """
    tick = moment.get("tick")
    if not isinstance(tick, int):
        return None
    game_number = moment.get("game_number")
    if isinstance(game_number, int):
        in_game = [
            (index, proof)
            for index, proof in enumerate(proof_events)
            if proof.get("game_number") == game_number
        ]
        if not in_game:
            return None
        exact = [
            (index, proof) for index, proof in in_game if proof.get("engine_tick") == tick
        ]
        if exact:
            caught = [
                (index, proof) for index, proof in exact if proof.get("resolution") == "catch"
            ]
            return (caught or exact)[0][0]
        prior = [
            index
            for index, proof in in_game
            if isinstance(proof.get("engine_tick"), int) and proof["engine_tick"] <= tick
        ]
        if prior:
            return prior[-1]
        return in_game[-1][0]
    exact_rec = [
        (index, proof) for index, proof in enumerate(proof_events) if proof.get("tick") == tick
    ]
    if exact_rec:
        caught = [
            (index, proof) for index, proof in exact_rec if proof.get("resolution") == "catch"
        ]
        return (caught or exact_rec)[0][0]
    prior_rec = [
        index
        for index, proof in enumerate(proof_events)
        if isinstance(proof.get("tick"), int) and proof["tick"] <= tick
    ]
    return prior_rec[-1] if prior_rec else None


def match_replay_payload(conn: sqlite3.Connection, match_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM match_records WHERE match_id = ?", (match_id,)).fetchone()
    if row is None:
        raise ReplayError("Match not found", status_code=404)
    if row["engine_match_id"] is None:
        raise ReplayError("Match replay is not available", status_code=409)

    clubs = load_clubs(conn)
    home = clubs.get(row["home_club_id"])
    away = clubs.get(row["away_club_id"])
    if home is None or away is None:
        raise ReplayError("Match club data is damaged", status_code=409)

    try:
        stored = fetch_match(conn, int(row["engine_match_id"]))
    except (KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ReplayError("Match replay data is damaged", status_code=409) from exc

    snapshots = roster_snapshots(conn, match_id, row["home_club_id"], row["away_club_id"])
    name_map = {
        str(player.get("id", "")): str(player.get("name", player.get("id", "")))
        for players in snapshots.values()
        for player in players
    }
    player_club_map = {
        str(player.get("id", "")): club_id
        for club_id, players in snapshots.items()
        for player in players
    }
    events = [
        {
            **event,
            "index": index,
            "label": event_label(event, name_map),
            "detail": event_detail(event, name_map),
        }
        for index, event in enumerate(stored["events"])
    ]
    official_state = None
    if events:
        match_start_context = events[0].get("context") or {}
        official_state_data = (
            match_start_context.get("official_state")
            if isinstance(match_start_context, dict)
            else None
        )
        if isinstance(official_state_data, dict):
            official_state = replay_state_to_dict(
                replay_state_from_dict(official_state_data),
                include_events=False,
            )
    player_club_id = get_state(conn, "player_club_id") or row["home_club_id"]
    if player_club_id not in {row["home_club_id"], row["away_club_id"]}:
        player_club_id = row["home_club_id"]
    opponent_club_id = row["away_club_id"] if player_club_id == row["home_club_id"] else row["home_club_id"]
    broadcast_frame = load_matchup_broadcast_frame(
        conn,
        season_id=row["season_id"],
        player_club_id=player_club_id,
        opponent_club_id=opponent_club_id,
        match_id=match_id,
        week=int(row["week"]),
    )
    playoff_frame = build_playoff_frame(season_id=row["season_id"], match_id=match_id)
    commentary_inserts = [
        insert.to_dict()
        for insert in build_commentary_inserts(
            events,
            record_items=load_league_records(conn),
            name_map=name_map,
        )
    ]

    stats = stats_for_match(conn, match_id)
    proof = build_replay_proof(
        stored["events"],
        name_map=name_map,
        roster_snapshots=snapshots,
        home_club_id=row["home_club_id"],
        away_club_id=row["away_club_id"],
        home_survivors=row["home_survivors"],
        away_survivors=row["away_survivors"],
        player_match_stats=stats,
        command_plan=command_plan_for_match(conn, match_id, row["season_id"]),
    )

    # Moment enrichment happens after the proof build so each moment can be
    # anchored to its spot in the proof timeline (game-aware for officials).
    moment_events = []
    if events:
        match_end_context = events[-1].get("context") or {}
        if isinstance(match_end_context, dict):
            raw_moments = match_end_context.get("moment_events")
            if isinstance(raw_moments, list):
                moment_events = raw_moments
    team_name_map = {row["home_club_id"]: home.name, row["away_club_id"]: away.name}
    moment_events = [
        {
            **_enrich_moment_display(moment, name_map, team_name_map),
            "anchor_index": _anchor_proof_index(moment, proof["proof_events"]),
        }
        for moment in moment_events
        if isinstance(moment, dict)
    ]
    game_segments = _game_segments(
        row["official_score_json"] if "official_score_json" in row.keys() else None,
        proof["proof_events"],
        row["home_club_id"],
    )
    # V20 intent context: the locked match policies both clubs actually played
    # under (persisted with the official score by the adapter). None for
    # legacy/rec matches — the panel simply omits the row.
    team_policies = None
    raw_score_json = (
        row["official_score_json"] if "official_score_json" in row.keys() else None
    )
    if raw_score_json:
        try:
            team_policies = json.loads(raw_score_json).get("team_policies")
        except (TypeError, ValueError):
            team_policies = None
    _winner_id = row["winner_club_id"]

    def _weighted(player_id: str, stat) -> float:
        base = score_player(stat)
        club_id = player_club_map.get(player_id, "")
        if _winner_id and club_id == _winner_id:
            return base * 1.5
        if _winner_id and club_id and club_id != _winner_id:
            return base * 0.75
        return base

    top = sorted(stats.items(), key=lambda item: (-_weighted(item[0], item[1]), item[0]))[:6]
    top_performers = [
        {
            "player_id": player_id,
            "player_name": name_map.get(player_id, player_id),
            "club_name": (clubs.get(player_club_map.get(player_id, "")) or home).name,
            "score": round(_weighted(player_id, stat), 1),
            "eliminations_by_throw": stat.eliminations_by_throw,
            "catches_made": stat.catches_made,
            "dodges_successful": stat.dodges_successful,
        }
        for player_id, stat in top
        if _weighted(player_id, stat) > 0
    ]
    mvp_id = compute_match_mvp(stats)
    winner_id = _winner_id
    winner_name = clubs[winner_id].name if winner_id in clubs else "Draw"
    turning_point_text, turning_point_index = _turning_point_selection(proof["proof_events"])
    report = {
        "winner_name": winner_name,
        "match_mvp_player_id": mvp_id,
        "match_mvp_name": name_map.get(mvp_id, mvp_id) if mvp_id else None,
        "top_performers": top_performers,
        "turning_point": turning_point_text or "No high-leverage swing detected.",
        # The proof-timeline index of that same event, so "jump to" lands on
        # exactly the play the headline describes.
        "turning_point_index": turning_point_index,
        "evidence_lanes": proof["evidence_report"]["evidence_lanes"],
    }
    return {
        "match_id": match_id,
        "season_id": row["season_id"],
        "week": row["week"],
        "home_club_id": row["home_club_id"],
        "home_club_name": home.name,
        "away_club_id": row["away_club_id"],
        "away_club_name": away.name,
        "winner_club_id": winner_id,
        "winner_name": winner_name,
        "home_survivors": row["home_survivors"],
        "away_survivors": row["away_survivors"],
        "config_version": row["config_version"] if "config_version" in row.keys() else None,
        "scoring_model": row["scoring_model"] if "scoring_model" in row.keys() else "legacy",
        "home_game_points": row["home_game_points"] if "home_game_points" in row.keys() else 0,
        "away_game_points": row["away_game_points"] if "away_game_points" in row.keys() else 0,
        "home_games_won": row["home_games_won"] if "home_games_won" in row.keys() else 0,
        "away_games_won": row["away_games_won"] if "away_games_won" in row.keys() else 0,
        "tied_games": row["tied_games"] if "tied_games" in row.keys() else 0,
        "no_point_games": row["no_point_games"] if "no_point_games" in row.keys() else 0,
        "events": events,
        "moment_events": moment_events,
        "proof_events": proof["proof_events"],
        "key_play_indices": proof["key_play_indices"],
        "game_segments": game_segments,
        "report": report,
        "team_policies": team_policies,
        "official_state": official_state,
        "broadcast_frame": broadcast_frame.to_dict(),
        "playoff_frame": playoff_frame.to_dict() if playoff_frame is not None else None,
        "commentary_inserts": commentary_inserts,
    }


def acknowledge_match_payload(conn: sqlite3.Connection, match_id: str) -> dict[str, Any]:
    cursor = load_career_state_cursor(conn)
    if cursor.state != CareerState.SEASON_ACTIVE_MATCH_REPORT_PENDING or cursor.match_id != match_id:
        raise ReplayError("No matching report is pending", status_code=409)
    season_id = get_state(conn, "active_season_id")
    if not season_id:
        raise ReplayError("No active season")
    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    player_club_id = get_state(conn, "player_club_id") or ""
    season, chosen, _stop_reason = _choose_next_user_match_after_automation(
        conn,
        season,
        clubs,
        player_club_id,
    )
    if not chosen:
        # Defensive guard: before going to offseason, scan for any unplayed
        # playoff matches involving the player (catches bracket creation edge cases).
        from .persistence import load_completed_match_ids
        from .playoffs import is_playoff_match_id
        completed = load_completed_match_ids(conn, season.season_id)
        pending_user_playoff = [
            m for m in season.scheduled_matches
            if is_playoff_match_id(season.season_id, m.match_id)
            and m.match_id not in completed
            and player_club_id in (m.home_club_id, m.away_club_id)
        ]
        if pending_user_playoff:
            chosen = pending_user_playoff[:1]
    if chosen:
        cursor = advance(cursor, CareerState.SEASON_ACTIVE_PRE_MATCH, week=chosen[0].week, match_id=None)
    else:
        cursor = advance(cursor, CareerState.SEASON_COMPLETE_OFFSEASON_BEAT, week=0, match_id=None)
    save_career_state_cursor(conn, cursor)
    conn.commit()
    return {"status": "success", "state": career_state_payload(cursor)}


def roster_snapshots(conn: sqlite3.Connection, match_id: str, home_club_id: str, away_club_id: str) -> dict[str, list[dict[str, Any]]]:
    try:
        return {
            home_club_id: fetch_roster_snapshot(conn, match_id, home_club_id),
            away_club_id: fetch_roster_snapshot(conn, match_id, away_club_id),
        }
    except (KeyError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ReplayError("Match roster snapshot is damaged.", status_code=409) from exc


def command_plan_for_match(conn: sqlite3.Connection, match_id: str, season_id: str) -> dict[str, Any] | None:
    for record in load_command_history(conn, season_id):
        if record.get("match_id") == match_id:
            plan = record.get("plan")
            return plan if isinstance(plan, dict) else None
    return None


def stats_for_match(conn: sqlite3.Connection, match_id: str) -> dict[str, PlayerMatchStats]:
    rows = conn.execute("SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,)).fetchall()
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
        for row in rows
    }


def score_player(stats: PlayerMatchStats | None) -> float:
    if stats is None:
        return 0.0
    return (
        stats.eliminations_by_throw * 3.0
        + stats.catches_made * 4.0
        + stats.dodges_successful * 1.5
        + stats.revivals_caused * 2.0
        - stats.times_eliminated * 2.0
        + stats.clutch_events
    )


# ----------------------------------------------------------------------
# Friendly preview / replay display / bulk-sim digest (formerly manager_helpers)
# ----------------------------------------------------------------------

def team_snapshot(team: Team) -> str:
    top = sorted(team.players, key=lambda player: player.overall_skill(), reverse=True)[:3]
    lines = [
        f"{team.name}",
        f"Overall {round(team_overall(team))} | Chemistry {round(team.chemistry * 100)}%",
        "Top Rotation:",
    ]
    for player in top:
        lines.append(f"  {player.name} - {player_role(player)} ({round(player.overall_skill())})")
    return "\n".join(lines)

def friendly_preview_text(setup: MatchSetup) -> str:
    """Return a compact text preview for the sample friendly matchup."""
    return "\n\n".join((team_snapshot(setup.team_a), team_snapshot(setup.team_b)))

def friendly_match_stats(setup: MatchSetup, events: Iterable[Any]) -> Dict[str, PlayerMatchStats]:
    """Extract in-memory friendly stats without touching persistence."""
    return extract_all_stats(
        list(events),
        setup.team_a.id,
        setup.team_b.id,
        [player.id for player in setup.team_a.players],
        [player.id for player in setup.team_b.players],
    )

def format_bulk_sim_digest(
    *,
    matches_simmed: int,
    first_week: int | None,
    last_week: int | None,
    user_record: str,
    standings_note: str,
    notable_lines: Iterable[str],
    scouting_note: str,
    recruitment_note: str,
    next_action: str,
) -> str:
    """Return the V3 digest first-read after bulk simulation."""
    if first_week is None or last_week is None:
        weeks = "No weeks advanced"
    elif first_week == last_week:
        weeks = f"Week {first_week}"
    else:
        weeks = f"Weeks {first_week}-{last_week}"
    lines = [
        f"{matches_simmed} Matches Simmed",
        weeks,
        f"Your Club: {user_record}",
        "",
        "Standings Movement:",
        standings_note or "No standings movement.",
        "",
        "Notable Performances:",
    ]
    notables = list(notable_lines)
    lines.extend(f"- {line}" for line in notables) if notables else lines.append("- No standout stat lines.")
    lines.extend([
        "",
        "Scouting:",
        scouting_note or "No scouting updates.",
        "",
        "Recruitment:",
        recruitment_note or "No recruitment updates.",
        "",
        f"Next Recommended Action: {next_action}",
    ])
    return "\n".join(lines)

def replay_event_label(event, name_map: dict | None = None) -> str:
    """Short broadcast label for an engine event. name_map resolves player IDs to display names."""
    _names = name_map or {}
    if event.event_type == "match_end":
        winner = event.outcome.get("winner")
        return f"Final whistle: {winner or 'draw'}"
    if event.event_type != "throw":
        return title_label(event.event_type)
    resolution = str(event.outcome.get("resolution", "throw"))
    thrower_id = event.actors.get("thrower")
    target_id = event.actors.get("target")
    thrower = _names.get(thrower_id, thrower_id) if thrower_id is not None else "The thrower"
    if target_id is None:
        # Target-less throw: a foul (thrower out) or a throw into space — never
        # "misses -" / "misses None" (WT-1).
        thrower_out = bool(event.outcome.get("thrower_out"))
        if not thrower_out:
            state_diff = getattr(event, "state_diff", None) or {}
            player_out = state_diff.get("player_out") if isinstance(state_diff, dict) else None
            thrower_out = (
                isinstance(player_out, dict)
                and thrower_id is not None
                and str(player_out.get("player_id", "")) == str(thrower_id)
            )
        if thrower_out and resolution == "clock_violation":
            return f"VIOLATION: {thrower} ruled out on a throw-clock/burden call"
        if thrower_out:
            return f"HEADSHOT: {thrower} ruled out for an illegal high throw"
        return f"MISS: {thrower}'s throw doesn't connect"
    target = _names.get(target_id, target_id)
    if resolution == "hit":
        return f"HIT: {thrower} tags {target}"
    if resolution == "failed_catch":
        return f"DROP: {target} cannot hold {thrower}'s throw"
    if resolution == "catch":
        return f"CATCH: {target} turns over {thrower}"
    if resolution == "dodged":
        return f"DODGE: {target} slips {thrower}"
    if resolution == "blocked":
        # WT-20: a held-ball block — distinct from a dodge or a miss.
        return f"BLOCK: {target} walls away {thrower}'s throw with the held ball"
    if resolution == "miss":
        return f"MISS: {thrower} misses {target}"
    return f"{resolution.upper()}: {thrower} to {target}"

def replay_phase_delay(event) -> int:
    """Milliseconds to hold an event during automatic replay."""
    if event.event_type == "match_end":
        return 1500
    resolution = event.outcome.get("resolution")
    if resolution in ("hit", "failed_catch", "catch"):
        return 900
    if resolution in ("dodged", "blocked"):
        return 650
    return 420


# ---------------------------------------------------------------------------
# Display/formatting helpers (formerly ui_formatters.py)
# ---------------------------------------------------------------------------

def format_event_row(event: MatchEvent, lookup: Lookup) -> tuple[str, str, str, str, str]:
    actor = lookup.player(event.actors.get("thrower", event.actors.get("winner", "")))
    target = lookup.player(event.actors.get("target", ""))
    outcome = event.outcome.get("resolution") or event.outcome.get("winner") or event.event_type.upper()
    return (f"{event.tick:03d}", event.event_type.upper(), actor or "-", target or "-", str(outcome).upper())

def format_event_details(event: MatchEvent, lookup: Lookup) -> str:
    lines = [
        f"Tick {event.tick} | {event.event_type.upper()} | phase={event.phase}",
        narrate_event(event, lookup),
    ]
    if event.actors:
        lines.append("")
        lines.append("Actors")
        for key, value in event.actors.items():
            label = lookup.player(value) or lookup.team(value) or value
            lines.append(f"  {key}: {label}")
    if event.probabilities:
        lines.append("")
        lines.append("Probabilities")
        for key, value in event.probabilities.items():
            lines.append(f"  {key}: {value:.2f}")
    if event.rolls:
        lines.append("")
        lines.append("RNG Rolls")
        for key, value in event.rolls.items():
            lines.append(f"  {key}: {value:.2f}")
    if event.context:
        lines.append("")
        lines.append("Context")
        for key, value in event.context.items():
            lines.append(f"  {key}: {value}")
    if event.state_diff:
        lines.append("")
        lines.append("State Diff")
        for key, value in event.state_diff.items():
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)

def format_analysis_report(analysis: MatchAnalysis, lookup: Lookup) -> str:
    lines: list[str] = []
    if analysis.hero:
        lines.append(
            f"Hero Moment: {lookup.player(analysis.hero.player_id)} kept {lookup.team(analysis.hero.team_id)} alive."
        )
    if analysis.momentum:
        swing = max(analysis.momentum, key=lambda point: abs(point.differential))
        if swing.differential > 0:
            direction = "Team A"
        elif swing.differential < 0:
            direction = "Team B"
        else:
            direction = "Neither side"
        lines.append(f"Biggest swing: {direction} at tick {swing.tick} ({swing.differential:+d}).")
    return "\n".join(lines) if lines else "No analysis available yet."
