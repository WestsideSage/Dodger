from __future__ import annotations

from typing import Any, Mapping, Sequence

from .copy_quality import title_label
from .lineup import _ROLE_LIABILITIES, _ROLE_NAMES


ThrowEvent = Mapping[str, Any]


def _player_name(player_id: Any, name_map: Mapping[str, str]) -> str:
    if player_id is None:
        return "-"
    return name_map.get(str(player_id), str(player_id))


def event_label(event: ThrowEvent, name_map: Mapping[str, str]) -> str:
    if event.get("event_type") == "match_end":
        winner = event.get("outcome", {}).get("winner")
        return f"Final whistle: {winner or 'draw'}"
    if event.get("event_type") != "throw":
        return title_label(str(event.get("event_type", "event")))
    outcome = event.get("outcome", {})
    actors = event.get("actors", {})
    resolution = str(outcome.get("resolution", "throw"))
    thrower = _player_name(actors.get("thrower"), name_map)
    target = _player_name(actors.get("target"), name_map)
    
    from dodgeball_sim.voice_playbyplay import render_play
    from dodgeball_sim.rng import DeterministicRNG
    rng = DeterministicRNG(hash(f"{thrower}_{target}_{resolution}_{event.get('tick', 0)}") % (2**63))
    
    if resolution == "hit":
        return render_play("throw", thrower, target, rng)
    if resolution == "failed_catch":
        return render_play("throw", thrower, target, rng) + " The catch is fumbled and they're out."
    if resolution == "catch":
        return render_play("catch", target, thrower, rng)
    if resolution == "dodged":
        return render_play("dodge", target, thrower, rng)
    if resolution == "miss":
        return render_play("throw", thrower, target, rng) + " It misses wide."
    return render_play("action", thrower, target, rng)


def event_detail(event: ThrowEvent, name_map: Mapping[str, str]) -> str:
    if event.get("event_type") != "throw":
        return f"{title_label(str(event.get('event_type', 'event')))}."
    actors = event.get("actors", {})
    outcome = event.get("outcome", {})
    probabilities = event.get("probabilities", {})
    rolls = event.get("rolls", {})
    thrower = _player_name(actors.get("thrower"), name_map)
    target = _player_name(actors.get("target"), name_map)
    resolution = str(outcome.get("resolution", "throw")).replace("_", " ")
    parts = [f"{thrower} vs {target}: {resolution}."]
    if "p_on_target" in probabilities and "on_target" in rolls:
        parts.append(f"On-target {float(probabilities['p_on_target']):.2f} (roll {float(rolls['on_target']):.2f}).")
    if "p_catch" in probabilities and "catch" in rolls:
        parts.append(f"Catch {float(probabilities['p_catch']):.2f} (roll {float(rolls['catch']):.2f}).")
    return " ".join(parts)


def build_replay_proof(
    events: Sequence[Mapping[str, Any]],
    *,
    name_map: Mapping[str, str],
    roster_snapshots: Mapping[str, Sequence[Mapping[str, Any]]],
    home_club_id: str,
    away_club_id: str,
    home_survivors: int | None = None,
    away_survivors: int | None = None,
    player_match_stats: Mapping[str, Any] | None = None,
    command_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    player_clubs = _player_club_map(roster_snapshots)
    liability_map = _liability_map(roster_snapshots)
    eliminated_by_club: dict[str, set[str]] = {home_club_id: set(), away_club_id: set()}
    active_counts = {
        club_id: len([player for player in snapshots if player.get("match_role") == "active"])
        for club_id, snapshots in roster_snapshots.items()
    }
    active_counts.setdefault(home_club_id, 0)
    active_counts.setdefault(away_club_id, 0)

    proof_events: list[dict[str, Any]] = []
    key_play_indices: list[int] = []
    for sequence_index, event in enumerate(events):
        state_diff = event.get("state_diff") or {}
        player_out = state_diff.get("player_out") if isinstance(state_diff, Mapping) else None
        if isinstance(player_out, Mapping):
            club_id = str(player_out.get("team", ""))
            player_id = str(player_out.get("player_id", ""))
            if club_id and player_id:
                eliminated_by_club.setdefault(club_id, set()).add(player_id)

        if event.get("event_type") != "throw":
            continue

        proof = _proof_event(
            event,
            sequence_index=sequence_index,
            name_map=name_map,
            player_clubs=player_clubs,
            liability_map=liability_map,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            eliminated_by_club=eliminated_by_club,
            active_counts=active_counts,
        )
        if proof["is_key_play"]:
            key_play_indices.append(len(proof_events))
        proof_events.append(proof)

    report = build_evidence_report(
        proof_events,
        key_play_indices,
        name_map=name_map,
        home_survivors=home_survivors,
        away_survivors=away_survivors,
        player_match_stats=player_match_stats or {},
        command_plan=command_plan,
    )
    return {
        "proof_events": proof_events,
        "key_play_indices": key_play_indices,
        "evidence_report": report,
    }


def build_evidence_report(
    proof_events: Sequence[Mapping[str, Any]],
    key_play_indices: Sequence[int],
    *,
    name_map: Mapping[str, str],
    home_survivors: int | None,
    away_survivors: int | None,
    player_match_stats: Mapping[str, Any],
    command_plan: Mapping[str, Any] | None,
) -> dict[str, Any]:
    key_events = [proof_events[index] for index in key_play_indices if 0 <= index < len(proof_events)]
    first_key = key_events[0] if key_events else None
    tactic_events = [event for event in proof_events if event.get("tactic_context", {}).get("items")]
    fatigue_events = [event for event in proof_events if event.get("fatigue", {}).get("items")]
    liability_events = [event for event in proof_events if event.get("liability_context", {}).get("items")]

    lanes = [
        {
            "title": "Result proof",
            "summary": _result_summary(home_survivors, away_survivors),
            "items": [
                first_key["summary"] if first_key else "No key throw event was recorded before the final result.",
                f"{len(proof_events)} throw events were derived from the saved event log.",
            ],
        },
        {
            "title": "Tactics proof",
            "summary": "Uses the saved throw log to explain pressure, timing, and target selection.",
            "items": _lane_items(tactic_events, "No saved tactic context was present on throw events."),
        },
        {
            "title": "Fatigue proof",
            "summary": "Uses fatigue values and minutes played already saved for this match.",
            "items": _fatigue_lane_items(fatigue_events, player_match_stats, name_map),
        },
        {
            "title": "Liability proof",
            "summary": "Uses roster-snapshot role fit and throw participants; it does not infer hidden boosts.",
            "items": _lane_items(liability_events, "No lineup liability appeared in the saved throw evidence."),
        },
        {
            "title": "Key plays",
            "summary": f"{len(key_events)} key plays are navigable from the replay timeline.",
            "items": [event["summary"] for event in key_events[:5]] or ["No hit, catch, or failed-catch key play was recorded."],
        },
    ]
    if command_plan:
        lanes.append(
            {
                "title": "Command plan",
                "summary": f"Intent: {command_plan.get('intent', 'unspecified')}.",
                "items": _command_plan_items(command_plan),
            }
        )
    else:
        lanes.append(
            {
                "title": "Command plan",
                "summary": "No saved command plan was linked to this match.",
                "items": ["Neutral or direct simulations do not claim department-order effects."],
            }
        )
    return {"evidence_lanes": lanes}


def _proof_event(
    event: Mapping[str, Any],
    *,
    sequence_index: int,
    name_map: Mapping[str, str],
    player_clubs: Mapping[str, str],
    liability_map: Mapping[str, Mapping[str, Any]],
    home_club_id: str,
    away_club_id: str,
    eliminated_by_club: Mapping[str, set[str]],
    active_counts: Mapping[str, int],
) -> dict[str, Any]:
    actors = event.get("actors") or {}
    context = event.get("context") or {}
    outcome = event.get("outcome") or {}
    state_diff = event.get("state_diff") or {}
    resolution = str(outcome.get("resolution", "throw"))
    thrower_id = str(actors.get("thrower", ""))
    target_id = str(actors.get("target", ""))
    is_key_play = resolution in {"hit", "failed_catch", "catch"} or bool(state_diff.get("player_out"))
    tags = [resolution.replace("_", " ").upper()]
    rush_context = context.get("rush_context")
    if isinstance(rush_context, Mapping) and rush_context.get("active"):
        tags.append("RUSH")
    sync_context = context.get("sync_context")
    if isinstance(sync_context, Mapping) and sync_context.get("is_synced"):
        tags.append("SYNC")
    fatigue = context.get("fatigue")
    if isinstance(fatigue, Mapping):
        max_fatigue = max(
            float(fatigue.get("thrower_fatigue", 0.0) or 0.0),
            float(fatigue.get("target_fatigue", 0.0) or 0.0),
        )
        tags.append("EXHAUSTED" if max_fatigue > 0.8 else "FATIGUE")
    liability_items = _liability_items(thrower_id, target_id, liability_map)
    if liability_items:
        tags.append("LIABILITY")

    score_state = _score_state(home_club_id, away_club_id, eliminated_by_club, active_counts)
    return {
        "sequence_index": sequence_index,
        "tick": event.get("tick", 0),
        "thrower_id": thrower_id,
        "thrower_name": _player_name(thrower_id, name_map),
        "target_id": target_id,
        "target_name": _player_name(target_id, name_map),
        "offense_club_id": player_clubs.get(thrower_id, str(actors.get("offense_team", ""))),
        "defense_club_id": player_clubs.get(target_id, str(actors.get("defense_team", ""))),
        "resolution": resolution,
        "is_key_play": is_key_play,
        "proof_tags": tags,
        "summary": event_label(event, name_map),
        "detail": event_detail(event, name_map),
        "odds": dict(event.get("probabilities") or {}),
        "rolls": dict(event.get("rolls") or {}),
        "fatigue": _fatigue_context(context.get("fatigue")),
        "decision_context": _decision_context(context, name_map),
        "tactic_context": _tactic_context(context),
        "liability_context": {"items": liability_items},
        "score_state": score_state,
    }


def _score_state(
    home_club_id: str,
    away_club_id: str,
    eliminated_by_club: Mapping[str, set[str]],
    active_counts: Mapping[str, int],
) -> dict[str, Any]:
    home_out = sorted(eliminated_by_club.get(home_club_id, set()))
    away_out = sorted(eliminated_by_club.get(away_club_id, set()))
    return {
        "home_living": max(0, int(active_counts.get(home_club_id, 0)) - len(home_out)),
        "away_living": max(0, int(active_counts.get(away_club_id, 0)) - len(away_out)),
        "home_eliminated_player_ids": home_out,
        "away_eliminated_player_ids": away_out,
    }


def _decision_context(context: Mapping[str, Any], name_map: Mapping[str, str]) -> dict[str, Any]:
    items: list[str] = []
    target = context.get("target_selection")
    if isinstance(target, Mapping):
        scores = target.get("scores")
        if isinstance(scores, list) and scores:
            top = scores[0]
            if isinstance(top, Mapping):
                player_id = top.get("player_id", "target")
                score = top.get("score")
                if score is not None:
                    target_name = _player_name(player_id, name_map)
                    items.append(f"Target selection leaned toward {target_name}.")
        if target.get("recent_pressure_player_id"):
            items.append(f"Recent pressure stayed on {_player_name(target['recent_pressure_player_id'], name_map)}.")
    catch = context.get("catch_decision")
    if isinstance(catch, Mapping):
        attempt = "attempted" if catch.get("attempt") else "declined"
        items.append(f"Catch decision {attempt} on the read.")
    if context.get("pressure_active") is not None:
        items.append("Pressure was active on the play." if context.get("pressure_active") else "The throw developed without extra pressure.")
    return {"items": items or ["No decision context was saved for this throw."]}


def _tactic_context(context: Mapping[str, Any]) -> dict[str, Any]:
    items: list[str] = []
    rush = context.get("rush_context")
    if isinstance(rush, Mapping):
        if rush.get("active"):
            modifier = float(rush.get("proximity_modifier", 0.0) or 0.0)
            if modifier >= 0.08:
                items.append("The rush crowded the throw and made the release harder.")
            else:
                items.append("The rush arrived, but the thrower still had enough room to release cleanly.")
        else:
            items.append("The possession developed patiently rather than through a hard rush.")
    sync = context.get("sync_context")
    if isinstance(sync, Mapping):
        if sync.get("is_synced"):
            items.append("A synchronized attack triggered and improved the throwing window.")
        else:
            items.append("Standard tactical execution; synchronized attack did not trigger.")
    policy = context.get("policy_snapshot")
    if isinstance(policy, Mapping):
        items.append(_policy_snapshot_note(policy))
    return {"items": items}


def _fatigue_context(fatigue: Any) -> dict[str, Any]:
    if not isinstance(fatigue, Mapping):
        return {"items": ["No fatigue context was saved for this throw."]}
    thrower_fatigue = float(fatigue.get("thrower_fatigue", 0.0) or 0.0)
    target_fatigue = float(fatigue.get("target_fatigue", 0.0) or 0.0)
    items = [
        f"Thrower fatigue {thrower_fatigue:.2f}.",
        f"Target fatigue {target_fatigue:.2f}.",
    ]
    if thrower_fatigue > 0.8:
        items.append(f"High fatigue ({thrower_fatigue:.2f}) significantly reduced throw power.")
    if target_fatigue > 0.8:
        items.append(f"Target reaction time compromised by high fatigue ({target_fatigue:.2f}).")
    if thrower_fatigue <= 0.8 and target_fatigue <= 0.8:
        items.append("Fatigue was not a major factor in this play.")
    return {
        "thrower_fatigue": fatigue.get("thrower_fatigue"),
        "target_fatigue": fatigue.get("target_fatigue"),
        "items": items,
    }


def _liability_items(
    thrower_id: str,
    target_id: str,
    liability_map: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    items = []
    for label, player_id in (("Thrower", thrower_id), ("Target", target_id)):
        liability = liability_map.get(player_id)
        if liability and liability.get("is_liability"):
            items.append(
                f"{label} suffered a liability penalty as a mismatched {liability['role_name']} ({liability['archetype']} archetype)."
            )
    return items


def _liability_map(roster_snapshots: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, dict[str, Any]]:
    liabilities: dict[str, dict[str, Any]] = {}
    for players in roster_snapshots.values():
        active = [player for player in players if player.get("match_role") == "active"]
        for index, player in enumerate(active):
            archetype = str(player.get("archetype", ""))
            role_name = _ROLE_NAMES[index] if index < len(_ROLE_NAMES) else "Utility"
            disallowed = {item.value for item in _ROLE_LIABILITIES.get(index, set())}
            liabilities[str(player.get("id", ""))] = {
                "role_name": role_name,
                "archetype": archetype,
                "is_liability": archetype in disallowed,
            }
    return liabilities


def _player_club_map(roster_snapshots: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, str]:
    clubs: dict[str, str] = {}
    for club_id, players in roster_snapshots.items():
        for player in players:
            clubs[str(player.get("id", ""))] = club_id
    return clubs


def _result_summary(home_survivors: int | None, away_survivors: int | None) -> str:
    if home_survivors is None or away_survivors is None:
        return "Final survivor counts were not available in the match record."
    return f"Final survivors were {home_survivors}-{away_survivors}."


def _lane_items(events: Sequence[Mapping[str, Any]], fallback: str) -> list[str]:
    items: list[str] = []
    for event in events[:3]:
        tick = event.get("tick", "?")
        summary = event.get("summary", "Throw event")
        items.append(f"Tick {tick}: {summary}")
    return items or [fallback]


def _fatigue_lane_items(events: Sequence[Mapping[str, Any]], player_match_stats: Mapping[str, Any], name_map: Mapping[str, str]) -> list[str]:
    items = _lane_items(events, "No saved fatigue context was present on throw events.")
    if player_match_stats:
        top_minutes = sorted(
            (
                (player_id, getattr(stats, "minutes_played", 0))
                for player_id, stats in player_match_stats.items()
            ),
            key=lambda item: (-item[1], item[0]),
        )[:2]
        for player_id, minutes in top_minutes:
            items.append(f"{_player_name(player_id, name_map)} carried a heavy workload with {minutes} match minutes.")
    return items


def _command_plan_items(command_plan: Mapping[str, Any]) -> list[str]:
    items = []
    dev_focus = command_plan.get("department_orders", {}).get("dev_focus")
    if dev_focus:
        items.append(f"Development focus: {title_label(str(dev_focus))}.")
    tactics = command_plan.get("tactics", {})
    if float(tactics.get("target_stars", 0.0)) >= 0.65:
        items.append("Star containment shaped the target plan.")
    else:
        items.append("Target pressure was spread across the opposing lineup.")
    if float(tactics.get("rush_frequency", 0.0)) >= 0.65:
        items.append("Rush pressure was emphasized in the saved plan.")
    else:
        items.append("Rush pressure was used selectively in the saved plan.")
    if float(tactics.get("sync_throws", 0.0)) >= 0.55:
        items.append("Sync throws were emphasized when the timing window opened.")
    if float(tactics.get("catch_bias", 0.0)) >= 0.55:
        items.append("Catch chances were encouraged when defenders had a clean read.")
    return items or ["Command plan was saved, but no displayable orders were present."]


def _policy_snapshot_note(policy: Mapping[str, Any]) -> str:
    target_stars = float(policy.get("target_stars", 0.0))
    tempo = float(policy.get("tempo", 0.0))
    catch_bias = float(policy.get("catch_bias", 0.0))
    notes: list[str] = []
    notes.append("star-focused targets" if target_stars >= 0.65 else "spread target pressure")
    notes.append("higher tempo" if tempo >= 0.6 else "controlled tempo")
    notes.append("aggressive catch reads" if catch_bias >= 0.6 else "selective catch reads")
    return "Tactical posture: " + ", ".join(notes) + "."


__all__ = [
    "build_replay_proof",
    "event_detail",
    "event_label",
]
