"""Catch / re-entry queue (Section 22-23, partial Section 24).

A valid catch from a live thrown ball returns one queued teammate via FIFO.
Simultaneous catches can return multiple. Non-starters cannot re-enter from
a catch; they must wait for a separate re-entry mechanism. Players involved
in the current sequence are blocked from being the entering player from that
sequence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)


@dataclass
class EnteringPlayerState:
    player_id: str
    deadline_seconds: int = 5  # Section 23: 5-second entry window
    elapsed_seconds: int = 0
    sequence_id: str | None = None

    def expired(self) -> bool:
        return self.elapsed_seconds >= self.deadline_seconds


@dataclass
class CatchQueueState:
    team_id: str
    # FIFO order: index 0 is next to re-enter.
    queued_ids: List[str] = field(default_factory=list)
    # Players who are out but not eligible for catch re-entry (non-starters).
    nonstarter_ids: List[str] = field(default_factory=list)
    entering: Optional[EnteringPlayerState] = None
    # Players involved in the active sequence are blocked from entering from
    # that same sequence.
    same_sequence_blocked: Dict[str, str] = field(default_factory=dict)
    # Discipline-blocked queue slots (blue card etc.); pointer to queue index.
    discipline_blocked_ids: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class QueueRuleViolation:
    rule_section: str
    violator_id: str
    summary: str


def enqueue_out_player(
    queue: CatchQueueState, *, player_id: str, is_starter: bool, match_id: str
) -> OfficialEvent:
    """Add a player to the back of the queue (or non-starter list)."""

    if not is_starter:
        if player_id not in queue.nonstarter_ids:
            queue.nonstarter_ids.append(player_id)
        return OfficialEvent(
            event_id=f"enq-ns-{player_id}",
            kind=OfficialEventKind.CATCH_QUEUE,
            match_id=match_id,
            player_ids=(player_id,),
            team_ids=(queue.team_id,),
            rule_refs=(RuleReference("23"),),
            replay_summary=f"{player_id} (non-starter) cannot re-enter from catches.",
            payload={"kind": "enqueue_nonstarter"},
        )
    if player_id not in queue.queued_ids:
        queue.queued_ids.append(player_id)
    return OfficialEvent(
        event_id=f"enq-{player_id}",
        kind=OfficialEventKind.CATCH_QUEUE,
        match_id=match_id,
        player_ids=(player_id,),
        team_ids=(queue.team_id,),
        rule_refs=(RuleReference("22"), RuleReference("23")),
        replay_summary=f"{player_id} enters queue position {len(queue.queued_ids)}.",
        payload={"kind": "enqueue", "position": len(queue.queued_ids)},
    )


def return_player_on_catch(
    queue: CatchQueueState,
    *,
    sequence_id: str,
    match_id: str,
) -> Tuple[Optional[OfficialEvent], Optional[str]]:
    """A valid catch returns the next eligible queued player.

    Returns (event, returning_player_id). If no eligible player is available,
    returns (None, None). Players involved in this same sequence are skipped
    (Section 22-23).
    """

    eligible: Optional[str] = None
    for pid in queue.queued_ids:
        if pid in queue.discipline_blocked_ids:
            continue
        if queue.same_sequence_blocked.get(pid) == sequence_id:
            continue
        eligible = pid
        break

    if eligible is None:
        return None, None

    queue.queued_ids.remove(eligible)
    queue.entering = EnteringPlayerState(
        player_id=eligible, sequence_id=sequence_id
    )
    event = OfficialEvent(
        event_id=f"ret-{eligible}-{sequence_id}",
        kind=OfficialEventKind.CATCH_QUEUE,
        match_id=match_id,
        sequence_id=sequence_id,
        player_ids=(eligible,),
        team_ids=(queue.team_id,),
        rule_refs=(RuleReference("22"), RuleReference("23")),
        replay_summary=f"{eligible} re-enters via catch from sequence {sequence_id}.",
        payload={"kind": "return_on_catch"},
    )
    return event, eligible


def out_of_order_entry(
    queue: CatchQueueState,
    *,
    attempting_player_id: str,
    match_id: str,
) -> OfficialEvent:
    """Section 23: out-of-order entry sends the player to the back of the
    queue and returns no player from that catch."""

    if attempting_player_id in queue.queued_ids:
        queue.queued_ids.remove(attempting_player_id)
        queue.queued_ids.append(attempting_player_id)
    return OfficialEvent(
        event_id=f"ooe-{attempting_player_id}",
        kind=OfficialEventKind.CATCH_QUEUE,
        match_id=match_id,
        player_ids=(attempting_player_id,),
        team_ids=(queue.team_id,),
        rule_refs=(RuleReference("23"),),
        replay_summary=(
            f"{attempting_player_id} entered out of order; moved to back of queue."
        ),
        payload={"kind": "out_of_order_entry"},
    )


def block_same_sequence(
    queue: CatchQueueState, *, sequence_id: str, player_id: str
) -> None:
    """Mark a player as involved in a sequence; they cannot be the entering
    player returned by that sequence's catch."""

    queue.same_sequence_blocked[player_id] = sequence_id


def tick_entering(queue: CatchQueueState, seconds: int) -> Optional[OfficialEvent]:
    """Advance the entering-player clock. Returns a deadline-miss event if
    the 5-second window expires before the player becomes live."""

    if queue.entering is None:
        return None
    queue.entering.elapsed_seconds += max(0, int(seconds))
    if queue.entering.expired():
        pid = queue.entering.player_id
        queue.entering = None
        # Send back to the back of the queue.
        queue.queued_ids.append(pid)
        return OfficialEvent(
            event_id=f"entry-missed-{pid}",
            kind=OfficialEventKind.CATCH_QUEUE,
            match_id="",  # caller can rewrap if needed
            player_ids=(pid,),
            team_ids=(queue.team_id,),
            rule_refs=(RuleReference("23"),),
            replay_summary=f"{pid} missed the 5-second entry window.",
            payload={"kind": "entry_window_missed"},
        )
    return None
