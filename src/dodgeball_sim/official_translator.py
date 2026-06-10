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
- Catch re-entries (CATCH_QUEUE ``return_on_catch`` events) are folded into
  the catching sequence's throw MatchEvent as ``state_diff["player_return"]``
  so the replay's live survivor state can stay truthful — the engine returns
  a queued teammate on every valid catch, and dropping that fact made the
  replay court show resurrected players as still-eliminated.
- Each throw MatchEvent carries ``context["official"]`` with the 1-based
  ``game_number`` (officials play a series of games per match; eliminations
  reset between games) and the per-game ``engine_tick`` when the sequence
  recorded its release time. Both are replay metadata read straight from the
  persisted official stream; neither affects outcomes.
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
    # Catch re-entries ride as separate CATCH_QUEUE events keyed by the same
    # sequence_id as the catching sequence_final; index them so the returned
    # player can be stamped onto the throw event's state_diff (truth, not
    # inference — the engine emitted both records for the same catch).
    # Sequence ids RESTART each game ("s1", "s2", ... per game), so the key
    # must include the game id or a later game's return lands on an earlier
    # game's unrelated sequence.
    returns_by_sequence: Dict[Tuple[str | None, str], Tuple[str, str | None]] = {}
    for ev in events_tuple:
        if (
            ev.kind == OfficialEventKind.CATCH_QUEUE
            and (ev.payload or {}).get("kind") == "return_on_catch"
            and ev.sequence_id
            and ev.player_ids
        ):
            team_id = ev.team_ids[0] if ev.team_ids else None
            returns_by_sequence[(ev.game_id, ev.sequence_id)] = (ev.player_ids[0], team_id)
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
        # WT-20: a blocked throw has no outs and no catch, but the blocker IS
        # the targeted defender — carry them so the replay names the block
        # instead of narrating a target-less miss.
        blocker_id = payload.get("blocker_id") if payload.get("blocked") else None
        target_id = target_ids[0] if target_ids else (catcher_id or blocker_id)
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
        elif payload.get("blocked"):
            # WT-20: a held-ball block killed the throw. Distinct from a miss
            # so the replay narrates the block honestly.
            outcome_kind = "blocked"
            resolution = "blocked"
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
        if ev.sequence_id and (ev.game_id, ev.sequence_id) in returns_by_sequence:
            returned_id, returned_team = returns_by_sequence[(ev.game_id, ev.sequence_id)]
            state_diff["player_return"] = {
                "team": returned_team or player_team_map.get(str(returned_id)),
                "player_id": returned_id,
            }
        official_context: Dict[str, Any] = {}
        game_number = _game_number_from_id(ev.game_id)
        if game_number is not None:
            official_context["game_number"] = game_number
        release_time_ms = payload.get("release_time_ms")
        if isinstance(release_time_ms, int):
            official_context["engine_tick"] = release_time_ms // 100
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
            context={"official": official_context} if official_context else {},
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


def _game_number_from_id(game_id: str | None) -> int | None:
    """Parse the 1-based game number from an official ``game_id`` ("g3" -> 3)."""
    if not game_id:
        return None
    digits = game_id[1:] if game_id.startswith("g") else game_id
    try:
        return int(digits)
    except ValueError:
        return None


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
