from __future__ import annotations

import json
import sqlite3
from collections import Counter
from typing import Any, Iterable, Mapping

from .game_loop import current_week
from .lineup import LineupResolver, optimize_ai_lineup
from .models import CoachPolicy, Player, PlayerArchetype
from .persistence import (
    load_all_rosters,
    load_clubs,
    load_command_history,
    load_completed_match_ids,
    load_department_heads,
    load_lineup_default,
    load_season,
    get_state,
)
from .franchise import MatchRecord
from .matchup_details import build_matchup_details
from .playoffs import playoff_stage_label


INTENTS = ("Balanced", "Win Now", "Develop Youth", "Preserve Health", "Prepare For Playoffs")

DEFAULT_DEPARTMENT_ORDERS = {
    "tactics": "opponent prep",
    "training": "fundamentals",
    "conditioning": "balanced maintenance",
    "medical": "injury prevention",
    "scouting": "next opponent",
    "culture": "pressure management",
    "dev_focus": "BALANCED",
}


def _player_summary(player: Player) -> dict[str, Any]:
    return {
        "id": player.id,
        "name": player.name,
        "overall": player.overall_skill(),
        "age": player.age,
        "potential": player.traits.potential,
        "stamina": player.ratings.stamina,
    }


# Axes the historical tape can speak to — the same five CoachPolicy axes the
# Tactical Diff renders. Tape supplies an *observed tendency* per axis.
_TAPE_AXES = ("approach", "target_focus", "catch_posture", "rush_commit", "rush_target")

# Archetype families used for the cold-start roster-shape read. These mirror the
# throwing- vs defense-oriented split the lineup court slots already encode
# (lineup.COURT_SLOT_PREFERENCES); we reuse the same enum, not a new scheme.
_THROW_ARCHETYPES = frozenset(
    {
        PlayerArchetype.THROWER,
        PlayerArchetype.THROWER_CATCHER,
        PlayerArchetype.THROWER_DODGER,
    }
)
_DEFENSE_ARCHETYPES = frozenset(
    {
        PlayerArchetype.DODGER_ANCHOR,
        PlayerArchetype.CATCHER,
        PlayerArchetype.BALL_HAWK,
        PlayerArchetype.CATCHER_HAWK,
        PlayerArchetype.HAWK_DODGER,
    }
)


def aggregate_opponent_tape(
    conn: sqlite3.Connection,
    opponent_id: str | None,
) -> dict[str, dict[str, Any]]:
    """Aggregate the opponent's *historical* coach policy from recorded matches.

    This is the WT-30 "observed-from-tape" signal: it reads ONLY the persisted
    ``matches.setup_json`` rows — completed games the opponent has already played
    and thereby publicly revealed. It must NEVER read the opponent's live
    ``club.coach_policy`` (that is the hidden plan for the *upcoming* match; see
    the ``tactical_diff`` module docstring). The upcoming match is not recorded
    in ``matches`` until it is simulated, so by construction only past tape is
    visible here.

    Returns a mapping ``axis -> {value, sample, confidence}`` for each axis the
    tape can speak to, where ``value`` is the opponent's *most frequent*
    historical choice on that axis, ``sample`` is the number of recorded games,
    and ``confidence`` is the share of games matching ``value`` (0..1). Axes are
    omitted when there is no tape. The shares are tendencies, not guarantees.
    """
    if not opponent_id:
        return {}

    rows = conn.execute(
        "SELECT team_a_id, team_b_id, setup_json FROM matches"
    ).fetchall()

    axis_counts: dict[str, Counter] = {axis: Counter() for axis in _TAPE_AXES}
    games = 0
    for row in rows:
        if opponent_id not in (row["team_a_id"], row["team_b_id"]):
            continue
        try:
            setup = json.loads(row["setup_json"])
        except (TypeError, ValueError):
            continue
        side = "team_a" if row["team_a_id"] == opponent_id else "team_b"
        team = setup.get(side) or {}
        # Defend against a match where the same club id appears on both sides of
        # the stored setup (should not happen, but the read must not double-count
        # or pick the wrong side).
        if team.get("id") != opponent_id:
            team = next(
                (
                    setup.get(s)
                    for s in ("team_a", "team_b")
                    if isinstance(setup.get(s), dict)
                    and setup.get(s, {}).get("id") == opponent_id
                ),
                None,
            )
            if team is None:
                continue
        policy = team.get("coach_policy") or {}
        if not policy:
            continue
        games += 1
        for axis in _TAPE_AXES:
            value = policy.get(axis)
            if value:
                axis_counts[axis][str(value)] += 1

    if games == 0:
        return {}

    tape: dict[str, dict[str, Any]] = {}
    for axis in _TAPE_AXES:
        counter = axis_counts[axis]
        if not counter:
            continue
        value, count = counter.most_common(1)[0]
        tape[axis] = {
            "value": value,
            "sample": games,
            "confidence": round(count / games, 2),
        }
    return tape


# Player-facing labels for the two archetype families the cold-start read can
# speak to. These are the SAME binary split _THROW_ARCHETYPES/_DEFENSE_ARCHETYPES
# encode — we name them for display, we do not invent a new taxonomy.
_GROUP_LABELS = {
    "throwers": "throwing-oriented",
    "defenders": "defense-oriented",
}


def _roster_shape(opponent_roster: list[Player]) -> dict[str, int] | None:
    """Derivable roster-shape fact: throwing- vs defense-oriented archetypes.

    Always-available (it reads the opponent roster the player can already see on
    the broadcast / standings), so it anchors the cold-start scout when no tape
    exists. Returns ``None`` for an empty roster.
    """
    if not opponent_roster:
        return None
    throwers = sum(1 for p in opponent_roster if p.archetype in _THROW_ARCHETYPES)
    defenders = sum(1 for p in opponent_roster if p.archetype in _DEFENSE_ARCHETYPES)
    return {
        "throwers": throwers,
        "defenders": defenders,
        "total": len(opponent_roster),
    }


def _position_groups(opponent_roster: list[Player]) -> dict[str, Any] | None:
    """Derivable strongest/weakest position-group read (BUG #10 enrichment).

    Reuses the SAME thrower/defender archetype partition ``_roster_shape`` uses —
    no hidden data, no new taxonomy. For each family we count members and average
    their visible ``overall_skill`` (the OVR the roster screen already shows). The
    *strongest* group is the higher-average family, the *weakest* the lower; ties
    and single-family rosters are handled explicitly. Returns ``None`` when no
    member falls into either named family (nothing derivable to rank).
    """
    if not opponent_roster:
        return None

    families: dict[str, list[Player]] = {
        "throwers": [p for p in opponent_roster if p.archetype in _THROW_ARCHETYPES],
        "defenders": [p for p in opponent_roster if p.archetype in _DEFENSE_ARCHETYPES],
    }
    present = {key: members for key, members in families.items() if members}
    if not present:
        return None

    def _avg_ovr(members: list[Player]) -> float:
        return round(sum(p.overall_skill() for p in members) / len(members), 1)

    summary = {
        key: {
            "label": _GROUP_LABELS[key],
            "count": len(members),
            "avg_ovr": _avg_ovr(members),
        }
        for key, members in present.items()
    }

    # Rank by average OVR (then count, then a stable key) — all from visible data.
    ranked = sorted(
        summary.items(),
        key=lambda item: (item[1]["avg_ovr"], item[1]["count"], item[0]),
        reverse=True,
    )
    strongest = ranked[0][1]
    # With only one family present, strongest and weakest are the same group; the
    # frontend can collapse that. Never fabricate a second group.
    weakest = ranked[-1][1]
    return {
        "strongest": strongest,
        "weakest": weakest,
        "single_family": len(present) == 1,
    }


def build_cold_start_intel(
    opponent: Any,
    opponent_roster: list[Player],
    key_threat: Mapping[str, Any] | None,
    opponent_record: str | None = None,
) -> dict[str, Any]:
    """Always-derivable, already-player-facing opponent facts for the scout.

    These do NOT depend on tape, so the scout is never empty exactly when WT-30's
    bug bites (week 1 / first meeting / fresh league). Every fact here is already
    shown elsewhere, surfaced together under the scout action — and read from the
    SAME source those surfaces use, so the scout never contradicts them:

    * ``program_archetype`` — the club's STORED ``program_archetype`` (what
      standings/status and the broadcast already display: web_status_service and
      server's club payload read ``club.program_archetype``). We deliberately do
      NOT recompute it via ``classify_club_archetype`` (that helper only seeds the
      stored value at career setup); recomputing risks showing the same fact two
      different ways if the roster drifted since setup.
    * ``roster_shape`` / ``position_groups`` — the throwing- vs defense-oriented
      archetype split of the visible roster, plus which family is the opponent's
      strongest and weakest by visible OVR (BUG #10 enrichment).
    * ``threat`` — the key threat already derived by ``build_matchup_details``.
    * ``recent_form`` — the opponent's win/loss/draw record this season, exactly
      the already-player-facing ``opponent_record`` string the matchup header and
      scout grid display. Passed in (not re-queried) so the scout can never
      disagree with those surfaces.

    Fog-of-war (WT-30): this function structurally cannot read the opponent's
    upcoming/live ``CoachPolicy`` — it accepts only the roster, the already-shown
    key threat, and the already-shown record. Nothing here exposes the hidden
    plan for the next match.
    """
    program_archetype = getattr(opponent, "program_archetype", None) or "Balanced Rebuild"
    # Treat placeholder records ("0-0", "n/a", empty) as "no form yet" so we do
    # not surface a vacuous "0-0" as if it were a meaningful recent-form read.
    recent_form = None
    if opponent_record and str(opponent_record).strip() not in {"", "0-0", "n/a"}:
        recent_form = str(opponent_record).strip()
    return {
        "program_archetype": program_archetype,
        "roster_shape": _roster_shape(opponent_roster),
        "position_groups": _position_groups(opponent_roster),
        # Reuse the threat already derived by build_matchup_details (read-only);
        # the scout does not recompute or expose anything new about it.
        "threat": dict(key_threat) if key_threat else None,
        "recent_form": recent_form,
    }


def _lineup_recommendation(roster: list[Player], default_lineup: list[str] | None, intent: str) -> dict[str, Any]:
    players_by_id = {player.id: player for player in roster}
    # Resolve the ONE canonical fielded-6 the sim also fields: the same
    # LineupResolver path, capped to the active starters. With no saved default,
    # the fresh-club lineup is the best-by-role/OVR six (optimize_ai_lineup) —
    # matching what club creation / season rollover now persist. This stops the
    # briefing from summing the whole roster while the sim fields only six.
    resolver = LineupResolver()
    base = list(default_lineup) if default_lineup else optimize_ai_lineup(roster)
    fielded_ids = resolver.active_starters(resolver.resolve(roster, base, None))
    chosen = [players_by_id[player_id] for player_id in fielded_ids if player_id in players_by_id]

    if intent == "Develop Youth":
        prospects = sorted(roster, key=lambda player: (-player.traits.potential, player.age, -player.overall_skill()))
        for prospect in prospects:
            if prospect not in chosen and len(chosen) >= 1:
                chosen[-1] = prospect
                break

    return {
        "player_ids": [player.id for player in chosen],
        "players": [_player_summary(player) for player in chosen],
        "summary": f"{intent} lineup built from the current default starters.",
    }


def _policy_for_intent(policy: CoachPolicy, intent: str) -> dict[str, str]:
    values = policy.as_dict()
    if intent == "Balanced":
        values.update(
            {
                "approach": "mixed",
                "target_focus": "spread",
                "catch_posture": "opportunistic",
                "rush_commit": "balanced",
                "rush_target": "nearest",
            }
        )
    elif intent == "Win Now":
        values.update(
            {
                "approach": "aggressive",
                "target_focus": "their_stars",
                "catch_posture": "go_for_catches",
                "rush_commit": "all_in",
                "rush_target": "center",
            }
        )
    elif intent == "Develop Youth":
        values.update(
            {
                "approach": "patient",
                "target_focus": "spread",
                "catch_posture": "opportunistic",
                "rush_commit": "balanced",
                "rush_target": "nearest",
            }
        )
    elif intent == "Preserve Health":
        values.update(
            {
                "approach": "patient",
                "target_focus": "spread",
                "catch_posture": "play_safe",
                "rush_commit": "hold_back",
                "rush_target": "nearest",
            }
        )
    elif intent == "Prepare For Playoffs":
        values.update(
            {
                "approach": "mixed",
                "target_focus": "ball_holders",
                "catch_posture": "opportunistic",
                "rush_commit": "balanced",
                "rush_target": "strongest_side",
            }
        )
    return values


from dodgeball_sim.rng import DeterministicRNG, derive_seed
from dodgeball_sim.voice_pregame import render_policy_line
from dodgeball_sim.voice_register import tier1

def build_command_center_state(conn: sqlite3.Connection) -> dict[str, Any]:
    season_id = get_state(conn, "active_season_id")
    player_club_id = get_state(conn, "player_club_id")
    root_seed = get_state(conn, "root_seed") or "1"
    if not season_id or not player_club_id:
        raise ValueError("No active season or player club")

    season = load_season(conn, season_id)
    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    completed = load_completed_match_ids(conn, season_id)
    week = current_week(conn, season) or 0
    upcoming = next(
        (
            match
            for match in sorted(season.scheduled_matches, key=lambda item: (item.week, item.match_id))
            if match.match_id not in completed and player_club_id in (match.home_club_id, match.away_club_id)
        ),
        None,
    )
    is_bye = (upcoming is None or upcoming.week > week) if week > 0 else False
    opponent_id = None
    if upcoming is not None and not is_bye:
        opponent_id = upcoming.away_club_id if upcoming.home_club_id == player_club_id else upcoming.home_club_id

    department_heads = load_department_heads(conn)

    matchup_details = build_matchup_details(
        conn,
        season_id=season_id,
        player_club_id=player_club_id,
        opponent_id=opponent_id,
        rosters=rosters,
        match_id=upcoming.match_id if upcoming is not None else None,
        week=upcoming.week if upcoming is not None else week,
        is_bye=is_bye,
        department_heads=department_heads,
    )
    opponent_roster = list(rosters.get(opponent_id, [])) if opponent_id else []

    return {
        "season_id": season_id,
        "week": week,
        "root_seed": int(root_seed),
        "player_club_id": player_club_id,
        "player_club": clubs[player_club_id],
        "opponent": clubs.get(opponent_id) if opponent_id else None,
        "opponent_id": opponent_id,
        "upcoming_match": upcoming,
        "is_bye": is_bye,
        "matchup_details": matchup_details,
        "roster": list(rosters.get(player_club_id, [])),
        "opponent_roster": opponent_roster,
        # WT-30 scout intel, computed from data the player is already allowed to
        # see. ``opponent_tape`` aggregates the opponent's PAST coach policy from
        # recorded matches (never the live/upcoming hidden plan); cold-start
        # facts (roster shape, program archetype, key threat) are always
        # derivable so the scout reveals something even before any tape exists.
        "opponent_tape": aggregate_opponent_tape(conn, opponent_id),
        "cold_start_intel": build_cold_start_intel(
            clubs.get(opponent_id) if opponent_id else None,
            opponent_roster,
            matchup_details.get("key_threat"),
            # Already-player-facing W-L-D record from build_matchup_details — passed
            # through (not re-queried) so the cold-start form can never disagree
            # with the matchup header / scout grid that show the same string.
            matchup_details.get("opponent_record"),
        ),
        "default_lineup": load_lineup_default(conn, player_club_id),
        "department_heads": department_heads,
        "history": load_command_history(conn, season_id),
    }


def _attach_tactical_diff(
    *,
    matchup_details: dict[str, Any],
    tactics: Mapping[str, Any],
    state: Mapping[str, Any],
    is_bye: bool,
    opponent_present: bool,
    scouted: bool,
) -> None:
    """Build (or rebuild) the Tactical Diff in-place on ``matchup_details``.

    Single choke point so the default-plan build and the per-load
    ``refresh_weekly_plan_context`` produce an identical diff. When the player
    has scouted (``scouted=True``), the diff is layered with the observed tape
    tendencies and the always-derivable cold-start facts gathered in
    ``build_command_center_state``. Crucially, only the PAST-derived
    ``opponent_tape`` and the already-player-facing cold-start facts are passed;
    the opponent's live/upcoming ``coach_policy`` never reaches this call.
    """
    if is_bye or not opponent_present:
        matchup_details.pop("tactical_diff", None)
        return
    from .tactical_diff import build_tactical_diff

    last_meeting = matchup_details.get("last_meeting")
    has_prior_meeting = bool(
        last_meeting and not str(last_meeting).lower().startswith("first meeting")
    )
    matchup_details["tactical_diff"] = build_tactical_diff(
        player_policy=tactics,
        adaptation_summary=matchup_details.get("adaptation_summary"),
        has_prior_meeting=has_prior_meeting,
        last_meeting=last_meeting if has_prior_meeting else None,
        scouted=scouted,
        observed_tendencies=dict(state.get("opponent_tape") or {}) if scouted else None,
        cold_start_intel=dict(state.get("cold_start_intel") or {}) if scouted else None,
    )


def build_default_weekly_plan(state: Mapping[str, Any], intent: str = "Balanced") -> dict[str, Any]:
    if intent not in INTENTS:
        intent = "Balanced"
    club = state["player_club"]
    opponent = state.get("opponent")
    heads = list(state["department_heads"])
    lineup = _lineup_recommendation(list(state["roster"]), state.get("default_lineup"), intent)
    opponent_roster = list(state.get("opponent_roster", []))
    opp_top_six = sorted(opponent_roster, key=lambda p: (-p.overall_skill(), p.id))[:6]
    opponent_lineup = {
        "players": [_player_summary(p) for p in opp_top_six],
    }
    tactics = _policy_for_intent(club.coach_policy, intent)
    warnings = _lineup_warnings(list(state["roster"]), lineup["player_ids"], intent, tactics)
    is_bye = state.get("is_bye", False)
    recommendations = _staff_recommendations(heads, intent, "Bye Week" if is_bye else (opponent.name if opponent else "the next opponent"))
    opponent_name = "Bye Week" if is_bye else (opponent.name if opponent else "Season complete")
    policy = CoachPolicy.from_dict(tactics)
    matchup_details = {
        "opponent_record": "No record",
        "last_meeting": "None",
        "key_matchup": "No opponent file available.",
        **dict(state.get("matchup_details") or {}),
    }
    matchup_details.setdefault("framing_line", render_policy_line(policy))

    # A fresh default plan is unscouted, so the diff starts as fully unscouted
    # (every axis "Unscouted"); the scout action flips it on the next reload via
    # refresh_weekly_plan_context, which reads the persisted opponent_scouted.
    _attach_tactical_diff(
        matchup_details=matchup_details,
        tactics=tactics,
        state=state,
        is_bye=is_bye,
        opponent_present=opponent is not None,
        scouted=False,
    )

    return {
        "season_id": state["season_id"],
        "week": state["week"],
        "player_club_id": state["player_club_id"],
        "is_bye": is_bye,
        "intent": intent,
        # D3 deliberate-action readiness flags. Start unmet on a fresh weekly
        # plan; cleared by a real scout / confirm-lineup action (see
        # command_week_service). Bye weeks auto-clear in the briefing.
        "opponent_scouted": False,
        "lineup_confirmed": False,
        "available_intents": list(INTENTS),
        "opponent": {
            "club_id": opponent.club_id if opponent else None,
            "name": opponent_name,
        },
        "department_heads": heads,
        "department_orders": dict(DEFAULT_DEPARTMENT_ORDERS),
        "recommendations": recommendations,
        "warnings": warnings,
        "lineup": lineup,
        "opponent_lineup": opponent_lineup,
        "tactics": tactics,
        "history_count": len(state.get("history", [])),
        "matchup_details": matchup_details,
    }


def refresh_weekly_plan_context(plan: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    refreshed = dict(plan)
    opponent = state.get("opponent")
    is_bye = state.get("is_bye", False)
    refreshed["matchup_details"] = {
        **dict(refreshed.get("matchup_details") or {}),
        **dict(state.get("matchup_details") or {}),
    }
    refreshed["is_bye"] = is_bye
    refreshed["opponent"] = {
        "club_id": opponent.club_id if opponent else None,
        "name": "Bye Week" if is_bye else (opponent.name if opponent else "Season complete"),
    }

    # WT-30: rebuild the Tactical Diff on every reload reading the PERSISTED
    # opponent_scouted flag. The merge above keeps whatever tactical_diff the
    # saved plan held — and build_matchup_details never emits that key — so a
    # scout action (which persists opponent_scouted=True, then this payload
    # reloads the plan) would otherwise keep the stale "Unscouted" diff. Rebuild
    # here so scouting genuinely FLIPS the diff to the observed-from-tape and
    # cold-start reveal. Source stays past-tape + already-visible facts only.
    _attach_tactical_diff(
        matchup_details=refreshed["matchup_details"],
        tactics=refreshed.get("tactics") or {},
        state=state,
        is_bye=is_bye,
        opponent_present=opponent is not None,
        scouted=bool(refreshed.get("opponent_scouted")),
    )
    opponent_roster = list(state.get("opponent_roster", []))
    opp_top_six = sorted(opponent_roster, key=lambda p: (-p.overall_skill(), p.id))[:6]
    refreshed["opponent_lineup"] = {
        "players": [_player_summary(p) for p in opp_top_six],
    }

    # WT-9: re-resolve the fielded six from the CURRENT persisted lineup_default
    # (what the Roster Lineup Editor last saved) on every plan reuse. A stale
    # weekly plan embeds the six chosen when it was first built; without this the
    # sim path (use_cases) writes that stale six as a match_lineup_override, which
    # outranks lineup_default and silently shadows a newer editor edit — so the
    # six the player SEES (briefing) and the six that PLAYS (sim) diverge from the
    # lineup they just saved. Re-resolving here, the single choke point feeding
    # both the pre-sim briefing and the sim, keeps lineup_default the one source
    # of truth. An explicit in-week override (use_cases applies update[
    # "lineup_player_ids"] AFTER this call; save_command_center_plan_payload
    # re-applies its lineup edit AFTER this call) still wins by running last.
    refreshed["lineup"] = _lineup_recommendation(
        list(state.get("roster", [])),
        state.get("default_lineup"),
        refreshed.get("intent") or "Balanced",
    )
    # WT-9 follow-up: the fielded six was just re-resolved, so its sibling
    # readiness `warnings` must be recomputed against the NEW six. Otherwise the
    # briefing and the persisted command-history row keep advisory warnings that
    # name players from the stale six (and omit the real mismatches in the six
    # now starting) — a readiness lie about who is actually on court.
    refreshed["warnings"] = _lineup_warnings(
        list(state.get("roster", [])),
        refreshed["lineup"]["player_ids"],
        refreshed.get("intent") or "Balanced",
        refreshed.get("tactics") or {},
    )
    return refreshed


def _staff_recommendations(heads: list[dict[str, Any]], intent: str, opponent_name: str) -> list[dict[str, str]]:
    by_department = {head["department"]: head for head in heads}
    tactic = by_department.get("tactics", {})
    training = by_department.get("training", {})
    medical = by_department.get("medical", {})
    return [
        {
            "department": "Tactics",
            "voice": tactic.get("voice", "Keep the plan simple."),
            "text": f"Scouting indicates {opponent_name} will challenge our rotations. Align our target plan to exploit their weak side.",
        },
        {
            "department": "Training",
            "voice": training.get("voice", "Reps have to show up on court."),
            "text": "We are prioritizing fundamental drills to build a baseline of consistency across the roster this week.",
        },
        {
            "department": "Medical",
            "voice": medical.get("voice", "Availability is a decision."),
            "text": "Fatigue-risk warnings are elevated for high-workload players. We need to monitor our substitution limits.",
        },
    ]


def _lineup_warnings(roster: list[Player], player_ids: list[str], intent: str, tactics: Mapping[str, str]) -> list[str]:
    from .lineup import check_lineup_liabilities
    starters = set(player_ids)
    warnings: list[str] = []
    
    liabilities = check_lineup_liabilities(roster, player_ids)
    warnings.extend(liabilities)
    
    high_upside_benched = [
        player for player in roster
        if player.id not in starters and player.traits.potential >= 80 and player.overall_skill() >= 55
    ]
    if high_upside_benched and intent != "Win Now":
        warnings.append(f"{high_upside_benched[0].name} has high upside but is outside the recommended reps group.")
    weak_starters = [
        player for player in roster
        if player.id in starters and player.overall_skill() < 55
    ]
    if weak_starters and intent == "Win Now":
        warnings.append(f"{weak_starters[0].name} is a weak starter and may be targeted.")
    if tactics.get("rush_commit") == "all_in":
        warnings.append("Heavy rush pressure is creating extreme fatigue risk. Consider rotating your front line more often.")
    return warnings


def _result_scoreline(result: Any, home_club_id: str, away_club_id: str) -> tuple[str, str]:
    """Return ``(score, unit)`` for a finished match in the scoring model's own scale.

    Official (foam/cloth) matches score on game points (set wins). The legacy
    box-score ``living`` survivor count is NOT the official result and, on a
    multi-game official match, can contradict it — e.g. the 2026-05-29 playtest
    surfaced a 0-0 foam draw (two no-point games) whose representative box-score
    read 0-3 "survivors", which reads as a 3-0 win the player never got. So we
    surface game points for official matches and only fall back to survivors for
    legacy matches.
    """
    meta = getattr(result, "official_metadata", None)
    if meta:
        home_gp = int(meta.get("team_a_game_points", 0))
        away_gp = int(meta.get("team_b_game_points", 0))
        return f"{home_gp}-{away_gp}", "game points"
    box = result.box_score["teams"]
    home_survivors = int(box[home_club_id]["totals"]["living"])
    away_survivors = int(box[away_club_id]["totals"]["living"])
    return f"{home_survivors}-{away_survivors}", "survivors"


def build_post_week_dashboard(conn: sqlite3.Connection, plan: Mapping[str, Any], record: MatchRecord) -> dict[str, Any]:
    from dodgeball_sim.voice_verdict import approach_label_for_intent

    clubs = load_clubs(conn)
    rosters = load_all_rosters(conn)
    player_names = {
        player.id: player.name
        for roster in rosters.values()
        for player in roster
    }
    player_club_id = str(plan["player_club_id"])
    opponent_id = record.away_club_id if record.home_club_id == player_club_id else record.home_club_id
    won = record.result.winner_team_id == player_club_id
    draw = record.result.winner_team_id is None
    score, score_unit = _result_scoreline(
        record.result, record.home_club_id, record.away_club_id
    )
    stats = _match_stats(conn, record.match_id)
    target_note = _target_note(stats, player_club_id, player_names)
    result = "Draw" if draw else ("Win" if won else "Loss")
    intent = str(plan.get("intent", ""))
    approach_label = approach_label_for_intent(intent)

    return {
        "season_id": record.season_id,
        "week": record.week,
        "match_id": record.match_id,
        "stage": playoff_stage_label(record.season_id, record.match_id),
        "opponent_name": clubs[opponent_id].name if opponent_id in clubs else opponent_id,
        "result": result,
        "lanes": [
            {
                "title": "Result",
                "summary": f"{'Drew' if draw else ('Beat' if won else 'Lost to')} {clubs[opponent_id].name if opponent_id in clubs else opponent_id}, {score_unit} {score}.",
                "items": [f"Approach: {approach_label}", f"Week {record.week} command record saved."],
            },
            {
                "title": "Why it happened",
                "summary": "The clearest tactical read came from who absorbed pressure.",
                "items": [target_note],
            },
            {
                "title": "Roster health",
                "summary": "Roster availability and recovery tracked.",
                "items": [f"Medical order: {plan.get('department_orders', {}).get('medical', 'none')}.", "Staff report no new medical incidents; fitness levels maintained."],
            },
            {
                "title": "Player movement",
                "summary": "Training staff logged their weekly progression observations based on the current command intent.",
                "items": [f"Training order: {plan.get('department_orders', {}).get('training', 'none')}.", "Youth-rep visibility continues to track with recent program trajectory."],
            },
            {
                "title": "Next decisions",
                "summary": "Use the next command plan to respond to this result.",
                "items": [f"Scouting order was {plan.get('department_orders', {}).get('scouting', 'none')}.", "Review warnings before simulating again."],
            },
        ],
    }


def _match_stats(conn: sqlite3.Connection, match_id: str) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM player_match_stats WHERE match_id = ?", (match_id,)).fetchall()
    return [dict(row) for row in rows]


def _target_note(stats: list[dict[str, Any]], player_club_id: str, player_names: Mapping[str, str]) -> str:
    club_stats = [row for row in stats if row.get("club_id") == player_club_id]
    if not club_stats:
        return "No player target distribution was available."
    most_targeted = max(club_stats, key=lambda row: (row.get("times_targeted", 0), row.get("player_id", "")))
    player_name = player_names.get(str(most_targeted["player_id"]), "The busiest defender")
    target_count = int(most_targeted.get("times_targeted", 0) or 0)
    if target_count <= 0:
        return "The opponent did not build sustained pressure against one clear defender."
    return f"{player_name} absorbed the most pressure, drawing {target_count} throws."


__all__ = [
    "INTENTS",
    "build_command_center_state",
    "build_default_weekly_plan",
    "build_post_week_dashboard",
]


# ----------------------------------------------------------------------
# Coach policy display helpers (formerly manager_helpers/ui_formatters)
# ----------------------------------------------------------------------

POLICY_KEYS = (
    "approach",
    "target_focus",
    "catch_posture",
    "rush_commit",
    "rush_target",
)

_POLICY_LABELS = {
    "approach": "Approach",
    "target_focus": "Target focus",
    "catch_posture": "Catch posture",
    "rush_commit": "Opening rush: commit",
    "rush_target": "Opening rush: target",
}

_POLICY_OPTION_VALUES = {
    "approach": ("aggressive", "patient", "mixed"),
    "target_focus": ("their_stars", "ball_holders", "spread"),
    "catch_posture": ("go_for_catches", "play_safe", "opportunistic"),
    "rush_commit": ("all_in", "balanced", "hold_back"),
    "rush_target": ("nearest", "strongest_side", "center"),
}


def policy_label(key: str) -> str:
    return _POLICY_LABELS.get(key, key.replace("_", " ").title())


def policy_effect(policy: CoachPolicy, key: str) -> str:
    selected_value = policy.as_dict()[key]
    return tier1(f"policy.{key}.{selected_value}.preview")


def policy_rows(policy: CoachPolicy) -> Iterable[dict[str, Any]]:
    selected = policy.as_dict()
    for key in POLICY_KEYS:
        yield {
            "key": key,
            "label": policy_label(key),
            "options": [
                {
                    "value": value,
                    "label": tier1(f"policy.{key}.{value}.label"),
                    "preview": tier1(f"policy.{key}.{value}.preview"),
                    "selected": value == selected[key],
                }
                for value in _POLICY_OPTION_VALUES[key]
            ],
        }
