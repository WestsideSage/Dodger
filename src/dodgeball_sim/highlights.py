from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .voice_register import tier1


@dataclass(frozen=True)
class HighlightBeat:
    kind: str
    title: str
    body: str
    tick: int
    source_event_id: int | str
    source_event_index: int
    proof_source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "tick": self.tick,
            "source_event_id": self.source_event_id,
            "source_event_index": self.source_event_index,
            "proof_source": self.proof_source,
        }


def build_highlight_package(
    *,
    events: Sequence[Mapping[str, Any]],
    proof_events: Sequence[Mapping[str, Any]],
    moment_events: Sequence[Mapping[str, Any]],
    name_map: Mapping[str, str],
    cap: int = 6,
) -> list[HighlightBeat]:
    if not events or not proof_events:
        return []

    event_by_id = {
        event.get("event_id"): (index, event)
        for index, event in enumerate(events)
    }
    proof_by_event_id = {
        proof.get("event_id"): proof
        for proof in proof_events
        if proof.get("event_id") in event_by_id
    }
    if not proof_by_event_id:
        proof_by_event_id = _fallback_proof_mapping(events, proof_events)

    opening_event_id = _first_elimination_event_id(events)
    finish_event_id = _last_elimination_event_id(events)
    moment_event_ids = [
        event_id
        for event_id in (
            _source_event_id_for_moment(moment, events) for moment in moment_events[:3]
        )
        if event_id is not None
    ]
    swing_event_ids = _swing_event_ids(events, proof_events, excluded=set(moment_event_ids), limit=2)

    selected: list[tuple[str, int | str, Mapping[str, Any] | None]] = []
    if opening_event_id is not None:
        selected.append(("opening", opening_event_id, None))
    for moment, event_id in zip(moment_events[:3], moment_event_ids):
        selected.append(("moment", event_id, moment))
    for event_id in swing_event_ids:
        selected.append(("swing", event_id, None))
    if finish_event_id is not None:
        selected.append(("finish", finish_event_id, None))

    beats: list[HighlightBeat] = []
    seen_event_ids: set[int | str] = set()
    for kind, event_id, moment in selected:
        if event_id not in event_by_id:
            continue
        if kind == "finish" and event_id in seen_event_ids:
            beats = [beat for beat in beats if beat.source_event_id != event_id]
            seen_event_ids.discard(event_id)
        if event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)
        event_index, event = event_by_id[event_id]
        beats.append(_build_beat(kind, event, event_index, moment, name_map))

    if len(beats) > cap:
        protected_ids = {
            opening_event_id,
            finish_event_id,
            *moment_event_ids,
        }
        trimmed: list[HighlightBeat] = []
        optional: list[HighlightBeat] = []
        for beat in beats:
            if beat.source_event_id in protected_ids:
                trimmed.append(beat)
            else:
                optional.append(beat)
        beats = trimmed + optional[: max(0, cap - len(trimmed))]
    return beats[:cap]


def _build_beat(
    kind: str,
    event: Mapping[str, Any],
    event_index: int,
    moment: Mapping[str, Any] | None,
    name_map: Mapping[str, str],
) -> HighlightBeat:
    event_id = event.get("event_id")
    tick = int(event.get("tick", 0) or 0)
    label = str(event.get("label") or _event_fallback_label(event, name_map))
    detail = str(event.get("detail") or "")
    if kind == "opening":
        title = tier1("broadcast.highlight.opening")
        body = label
    elif kind == "finish":
        title = tier1("broadcast.highlight.finish")
        body = label
    elif kind == "moment" and moment is not None:
        title = str(moment.get("display_text") or label)
        body = detail or label
    else:
        title = tier1("broadcast.highlight.swing")
        body = label
    return HighlightBeat(
        kind=kind,
        title=title,
        body=body,
        tick=tick,
        source_event_id=event_id,
        source_event_index=event_index,
        proof_source=f"event:{event_id}",
    )


def _event_fallback_label(event: Mapping[str, Any], name_map: Mapping[str, str]) -> str:
    actors = event.get("actors") or {}
    thrower_id = str(actors.get("thrower", ""))
    target_id = str(actors.get("target", ""))
    resolution = str((event.get("outcome") or {}).get("resolution", "throw")).replace("_", " ")
    thrower = name_map.get(thrower_id, thrower_id)
    target = name_map.get(target_id, target_id)
    return f"{thrower} {resolution} {target}".strip()


def _first_elimination_event_id(events: Sequence[Mapping[str, Any]]) -> int | str | None:
    for event in events:
        if _is_elimination_event(event):
            return event.get("event_id")
    return None


def _last_elimination_event_id(events: Sequence[Mapping[str, Any]]) -> int | str | None:
    for event in reversed(events):
        if _is_elimination_event(event):
            return event.get("event_id")
    return None


def _is_elimination_event(event: Mapping[str, Any]) -> bool:
    if event.get("event_type") != "throw":
        return False
    outcome = event.get("outcome") or {}
    resolution = str(outcome.get("resolution", ""))
    if resolution not in {"hit", "failed_catch", "catch"}:
        return False
    state_diff = event.get("state_diff") or {}
    return bool(state_diff.get("player_out")) or resolution == "catch"


def _source_event_id_for_moment(
    moment: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
) -> int | str | None:
    tick = int(moment.get("tick", -1) or -1)
    throw_exact = next(
        (e for e in events
         if int(e.get("tick", -1) or -1) == tick and e.get("event_type") == "throw"),
        None,
    )
    if throw_exact is not None:
        return throw_exact.get("event_id")
    exact = next((event for event in events if int(event.get("tick", -1) or -1) == tick), None)
    if exact is not None:
        return exact.get("event_id")
    prior_throws = [
        event for event in events
        if int(event.get("tick", -1) or -1) <= tick and event.get("event_type") == "throw"
    ]
    if prior_throws:
        return prior_throws[-1].get("event_id")
    prior = [event for event in events if int(event.get("tick", -1) or -1) <= tick]
    if prior:
        return prior[-1].get("event_id")
    return None


def _fallback_proof_mapping(
    events: Sequence[Mapping[str, Any]],
    proof_events: Sequence[Mapping[str, Any]],
) -> dict[int | str, Mapping[str, Any]]:
    mapping: dict[int | str, Mapping[str, Any]] = {}
    for event, proof in zip(events, proof_events):
        mapping[event.get("event_id")] = proof
    return mapping


def _swing_event_ids(
    events: Sequence[Mapping[str, Any]],
    proof_events: Sequence[Mapping[str, Any]],
    *,
    excluded: set[int | str],
    limit: int,
) -> list[int | str]:
    candidates: list[tuple[float, int, int | str]] = []
    previous = None
    for proof in proof_events:
        event_id = proof.get("event_id")
        if event_id is None or event_id in excluded:
            previous = proof
            continue
        event = next((item for item in events if item.get("event_id") == event_id), None)
        if event is None or not _is_elimination_event(event):
            previous = proof
            continue
        score = _swing_score(previous, proof)
        candidates.append((score, int(proof.get("tick", 0) or 0), event_id))
        previous = proof
    ordered = sorted(candidates, key=lambda item: (-item[0], item[1], str(item[2])))
    return [event_id for _score, _tick, event_id in ordered[:limit]]


def _swing_score(
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any],
) -> float:
    current_state = current.get("score_state") or {}
    after_diff = int(current_state.get("home_living", 0)) - int(current_state.get("away_living", 0))
    if previous is None:
        return float(abs(after_diff))
    previous_state = previous.get("score_state") or {}
    before_diff = int(previous_state.get("home_living", 0)) - int(previous_state.get("away_living", 0))
    lead_flip = 1 if before_diff and after_diff and ((before_diff > 0) != (after_diff > 0)) else 0
    return abs(after_diff - before_diff) * 10.0 + abs(after_diff) + lead_flip * 100.0


__all__ = ["HighlightBeat", "build_highlight_package"]
