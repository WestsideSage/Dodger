"""Translate official-rules outcomes into generic ``MatchEvent`` + ``MatchResult``.

The integration strategy chosen in design Q1 is the **translator layer**:
the official engine produces ``OfficialEvent`` records, then this module
maps them onto the existing ``MatchEvent`` / ``MatchResult`` shape so that
the franchise pipeline, stats persistence, and replay service keep working
unchanged for official matches.

Mapping rules:

- Each ``sequence_final`` OfficialEvent becomes one ``throw`` MatchEvent.
- A synthetic ``match_start`` MatchEvent is prepended.
- A synthetic ``match_end`` MatchEvent is appended.
- Non-sequence official events (ball activation, queue, burden) ride through
  inside ``state_diff`` so the replay service can surface them, but they do
  not generate top-level MatchEvent rows.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Tuple

from .events import MatchEvent
from .official_events import OfficialEvent, OfficialEventKind


def translate_events(
    events: Iterable[OfficialEvent],
    *,
    seed: int,
    team_a_id: str,
    team_b_id: str,
    starters_a: Tuple[str, ...],
    starters_b: Tuple[str, ...],
    winner_team_id: str | None,
) -> List[MatchEvent]:
    """Convert an OfficialEvent stream into a MatchEvent list.

    A ``match_start`` MatchEvent is prepended and a ``match_end`` MatchEvent
    is appended so the result is shaped like a generic match.
    """

    events_tuple = tuple(events)
    player_team_map = {player_id: team_a_id for player_id in starters_a}
    player_team_map.update({player_id: team_b_id for player_id in starters_b})
    out: List[MatchEvent] = []
    event_counter = 0

    out.append(MatchEvent(
        event_id=event_counter, tick=0, seed=seed, event_type="match_start",
        phase="setup",
        actors={"team_a_id": team_a_id, "team_b_id": team_b_id,
                "starters_a": list(starters_a), "starters_b": list(starters_b)},
        context={},
        probabilities={}, rolls={},
        outcome={"engine": "official"},
        state_diff={},
    ))
    event_counter += 1

    tick = 0
    for ev in events_tuple:
        if ev.kind != OfficialEventKind.SEQUENCE:
            continue
        payload = ev.payload or {}
        if payload.get("kind") != "sequence_final":
            continue
        tick += 1
        thrower_id = payload.get("thrower_id")
        thrower_team = payload.get("thrower_team_id")
        outs = list(payload.get("outs", []))
        catches = list(payload.get("catches", []))
        target_ids = [pid for pid in outs if pid != thrower_id]
        catcher_id = catches[0] if catches else None
        target_id = target_ids[0] if target_ids else catcher_id
        defense_team = None
        if target_id is not None:
            defense_team = player_team_map.get(str(target_id))
        if defense_team is None:
            defense_team = team_b_id if thrower_team == team_a_id else team_a_id
        if catches:
            outcome_kind = "caught"
            resolution = "catch"
        elif outs and thrower_id in outs:
            outcome_kind = "clock_violation"
            resolution = "clock_violation"
        elif outs:
            outcome_kind = "hit"
            resolution = "hit"
        else:
            outcome_kind = "miss"
            resolution = "miss"
        state_diff: Dict[str, Any] = {"sequence_id": ev.sequence_id}
        if target_id is not None and outs and target_id in outs:
            state_diff["player_out"] = {
                "team": defense_team,
                "player_id": target_id,
            }
        elif catches and thrower_id is not None:
            state_diff["player_out"] = {
                "team": thrower_team,
                "player_id": thrower_id,
            }
        out.append(MatchEvent(
            event_id=event_counter, tick=tick, seed=seed,
            event_type="throw", phase="live",
            actors={
                "offense_team": thrower_team,
                "defense_team": defense_team,
                "thrower": thrower_id,
                "target": target_id,
                "catcher_ids": catches,
            },
            context={},
            probabilities={},
            rolls={},
            outcome={
                "kind": outcome_kind,
                "resolution": resolution,
                "outs": outs,
                "catches": catches,
                "thrower_out": bool(payload.get("thrower_out")),
                "player_out": target_id if target_id is not None and target_id in outs else (thrower_id if catches else None),
                "rule_refs": list(ev.rule_labels()),
                "replay_summary": ev.replay_summary,
            },
            state_diff=state_diff,
        ))
        event_counter += 1

    out.append(MatchEvent(
        event_id=event_counter, tick=tick + 1, seed=seed,
        event_type="match_end", phase="finalize",
        actors={"winner": winner_team_id, "winner_team_id": winner_team_id},
        context={},
        probabilities={}, rolls={},
        outcome={"winner": winner_team_id, "winner_team_id": winner_team_id, "engine": "official"},
        state_diff={},
    ))
    return out


def collect_official_metadata(events: Iterable[OfficialEvent]) -> Dict[str, Any]:
    """Surface non-throw official events as a metadata dict the replay
    service can render alongside the MatchEvent stream."""

    activations: List[Dict[str, Any]] = []
    queue_events: List[Dict[str, Any]] = []
    burden_events: List[Dict[str, Any]] = []
    discretion_events: List[Dict[str, Any]] = []
    no_blocking_events: List[Dict[str, Any]] = []
    for ev in events:
        record = {
            "event_id": ev.event_id,
            "rule_refs": list(ev.rule_labels()),
            "summary": ev.replay_summary,
            "payload": dict(ev.payload),
        }
        if ev.kind == OfficialEventKind.BALL:
            activations.append(record)
        elif ev.kind == OfficialEventKind.CATCH_QUEUE:
            queue_events.append(record)
        elif ev.kind == OfficialEventKind.BURDEN:
            burden_events.append(record)
        elif ev.kind == OfficialEventKind.DISCRETION:
            discretion_events.append(record)
        elif ev.kind == OfficialEventKind.NO_BLOCKING:
            no_blocking_events.append(record)
    return {
        "ball_events": activations,
        "queue_events": queue_events,
        "burden_events": burden_events,
        "discretion_events": discretion_events,
        "no_blocking_events": no_blocking_events,
    }
