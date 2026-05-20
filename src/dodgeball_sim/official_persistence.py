"""Serialization for official-rules events and replay payloads.

Phase 8B requires that official events can round-trip through storage. To
avoid touching the 3000-line ``persistence.py`` schema (which would risk
existing saves), this module keeps official serialization isolated: JSON
encode/decode for :class:`OfficialEvent` and a builder that turns a stored
event stream into :class:`OfficialReplayState`.

When the official engine is finally routed in (Phase 8D), the storage layer
can call into these helpers and persist the resulting JSON in a nullable
column without inventing new shapes.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, List, Mapping

from .official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)
from .replay_contracts import (
    OfficialBallView,
    OfficialBurdenView,
    OfficialClockView,
    OfficialGameScoreView,
    OfficialReplayState,
    OfficialRuleCallView,
    OfficialSequenceView,
    OfficialTeamStateView,
)


def event_to_dict(event: OfficialEvent) -> dict:
    return {
        "event_id": event.event_id,
        "kind": event.kind.value,
        "match_id": event.match_id,
        "game_id": event.game_id,
        "sequence_id": event.sequence_id,
        "ball_ids": list(event.ball_ids),
        "player_ids": list(event.player_ids),
        "team_ids": list(event.team_ids),
        "rule_refs": [
            {"section": ref.section, "clause": ref.clause}
            for ref in event.rule_refs
        ],
        "replay_summary": event.replay_summary,
        "payload": dict(event.payload),
        "official_payload_version": event.official_payload_version,
        "ruleset_version": event.ruleset_version,
        "rulebook_version": event.rulebook_version,
    }


def event_from_dict(data: Mapping[str, Any]) -> OfficialEvent:
    return OfficialEvent(
        event_id=data["event_id"],
        kind=OfficialEventKind(data["kind"]),
        match_id=data["match_id"],
        game_id=data.get("game_id"),
        sequence_id=data.get("sequence_id"),
        ball_ids=tuple(data.get("ball_ids", ())),
        player_ids=tuple(data.get("player_ids", ())),
        team_ids=tuple(data.get("team_ids", ())),
        rule_refs=tuple(
            RuleReference(section=r["section"], clause=r.get("clause"))
            for r in data.get("rule_refs", [])
        ),
        replay_summary=data["replay_summary"],
        payload=dict(data.get("payload", {})),
        official_payload_version=data.get("official_payload_version", "official.v1"),
        ruleset_version=data.get("ruleset_version", "rulesets.v1"),
        rulebook_version=data.get("rulebook_version", "USAD-2026.1"),
    )


def events_to_json(events: Iterable[OfficialEvent]) -> str:
    return json.dumps([event_to_dict(e) for e in events])


def events_from_json(blob: str) -> List[OfficialEvent]:
    return [event_from_dict(d) for d in json.loads(blob)]


def replay_state_from_events(
    *, ruleset: str, events: Iterable[OfficialEvent]
) -> OfficialReplayState:
    """Build a v0 :class:`OfficialReplayState` from a stored event stream.

    Phase 8B only requires that this round-trips; the view fields like
    ``burden`` and ``balls`` are populated by later phases once the engine
    is actually emitting them. Here we surface every event and derive rule
    calls from non-empty rule references.
    """

    events_tuple = tuple(events)
    rule_calls: List[OfficialRuleCallView] = []
    for ev in events_tuple:
        for label in ev.rule_labels():
            rule_calls.append(
                OfficialRuleCallView(rule_label=label, summary=ev.replay_summary)
            )
    return OfficialReplayState(
        ruleset=ruleset,
        events=events_tuple,
        rule_calls=tuple(rule_calls),
    )


def replay_state_to_dict(
    state: OfficialReplayState,
    *,
    include_events: bool = False,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "ruleset": state.ruleset,
        "rulebook_version": state.rulebook_version,
        "official_payload_version": state.official_payload_version,
        "mode": state.mode,
        "player_statuses": dict(state.player_statuses),
        "rule_calls": [
            {
                "rule_label": call.rule_label,
                "summary": call.summary,
                "timestamp_seconds": call.timestamp_seconds,
            }
            for call in state.rule_calls
        ],
        "balls": [
            {
                "ball_id": ball.ball_id,
                "state": ball.state,
                "side": ball.side,
                "controller_player_id": ball.controller_player_id,
            }
            for ball in state.balls
        ],
        "teams": [
            {
                "team_id": team.team_id,
                "active_ids": list(team.active_ids),
                "queued_ids": list(team.queued_ids),
                "entering_id": team.entering_id,
                "unavailable_ids": list(team.unavailable_ids),
            }
            for team in state.teams
        ],
        "active_sequences": [
            {
                "sequence_id": seq.sequence_id,
                "thrower_id": seq.thrower_id,
                "ball_id": seq.ball_id,
                "pending_outs": list(seq.pending_outs),
                "pending_saves": list(seq.pending_saves),
                "final": seq.final,
            }
            for seq in state.active_sequences
        ],
    }
    if state.match_clock is not None:
        data["match_clock"] = {
            "limit_seconds": state.match_clock.limit_seconds,
            "elapsed_seconds": state.match_clock.elapsed_seconds,
        }
    if state.game_clock is not None:
        data["game_clock"] = {
            "limit_seconds": state.game_clock.limit_seconds,
            "elapsed_seconds": state.game_clock.elapsed_seconds,
        }
    if state.game_score is not None:
        data["game_score"] = {
            "team_a_id": state.game_score.team_a_id,
            "team_b_id": state.game_score.team_b_id,
            "team_a_games": state.game_score.team_a_games,
            "team_b_games": state.game_score.team_b_games,
            "team_a_ties": state.game_score.team_a_ties,
            "team_b_ties": state.game_score.team_b_ties,
            "no_point_games": state.game_score.no_point_games,
        }
    if state.burden is not None:
        data["burden"] = {
            "team_id": state.burden.team_id,
            "basis": state.burden.basis,
            "clock_status": state.burden.clock_status,
            "seconds_remaining": state.burden.seconds_remaining,
            "play_n_count": state.burden.play_n_count,
        }
    if include_events:
        data["events"] = [event_to_dict(event) for event in state.events]
    return data


def replay_state_from_dict(data: Mapping[str, Any]) -> OfficialReplayState:
    match_clock_data = data.get("match_clock")
    game_clock_data = data.get("game_clock")
    game_score_data = data.get("game_score")
    burden_data = data.get("burden")
    return OfficialReplayState(
        ruleset=str(data["ruleset"]),
        rulebook_version=str(data.get("rulebook_version", "USAD-2026.1")),
        official_payload_version=str(data.get("official_payload_version", "official.v1")),
        match_clock=OfficialClockView(**match_clock_data) if isinstance(match_clock_data, Mapping) else None,
        game_clock=OfficialClockView(**game_clock_data) if isinstance(game_clock_data, Mapping) else None,
        game_score=OfficialGameScoreView(**game_score_data) if isinstance(game_score_data, Mapping) else None,
        mode=str(data.get("mode", "standard")),
        burden=OfficialBurdenView(**burden_data) if isinstance(burden_data, Mapping) else None,
        balls=tuple(
            OfficialBallView(**ball)
            for ball in data.get("balls", [])
            if isinstance(ball, Mapping)
        ),
        teams=tuple(
            OfficialTeamStateView(
                team_id=str(team["team_id"]),
                active_ids=tuple(team.get("active_ids", ())),
                queued_ids=tuple(team.get("queued_ids", ())),
                entering_id=team.get("entering_id"),
                unavailable_ids=tuple(team.get("unavailable_ids", ())),
            )
            for team in data.get("teams", [])
            if isinstance(team, Mapping)
        ),
        player_statuses={
            str(player_id): str(status)
            for player_id, status in dict(data.get("player_statuses", {})).items()
        },
        active_sequences=tuple(
            OfficialSequenceView(
                sequence_id=str(seq["sequence_id"]),
                thrower_id=seq.get("thrower_id"),
                ball_id=seq.get("ball_id"),
                pending_outs=tuple(seq.get("pending_outs", ())),
                pending_saves=tuple(seq.get("pending_saves", ())),
                final=bool(seq.get("final", False)),
            )
            for seq in data.get("active_sequences", [])
            if isinstance(seq, Mapping)
        ),
        rule_calls=tuple(
            OfficialRuleCallView(
                rule_label=str(call["rule_label"]),
                summary=str(call["summary"]),
                timestamp_seconds=int(call.get("timestamp_seconds", 0)),
            )
            for call in data.get("rule_calls", [])
            if isinstance(call, Mapping)
        ),
        events=tuple(
            event_from_dict(event)
            for event in data.get("events", [])
            if isinstance(event, Mapping)
        ),
    )
