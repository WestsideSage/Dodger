"""Sequence-of-play ledger and deterministic finality resolver.

A *sequence* begins with a live, valid throw and ends when the ball is dead
or caught. Outs are *pending* during the sequence; finality is applied
atomically when the sequence resolves. This lets V11 model ricochet catches,
simultaneous catches, clock-expired catches, and second-ball outs without
flipping ``is_out`` mid-resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)
from .rulesets import BallMaterial


class SequenceContactKind(str, Enum):
    HIT = "hit"
    BLOCK = "block"
    RICOCHET = "ricochet"
    CATCH = "catch"
    OUT_OF_BOUNDS = "out_of_bounds"
    DEAD_OBJECT = "dead_object"


@dataclass(frozen=True)
class SequenceContact:
    kind: SequenceContactKind
    player_id: str | None = None
    timestamp_ms: int = 0
    is_teammate_of_thrower: bool = False


@dataclass(frozen=True)
class PendingOut:
    player_id: str
    reason: str  # "hit", "thrower_caught", etc.


@dataclass(frozen=True)
class PendingSave:
    player_id: str
    reason: str  # "ricochet_catch", "teammate_catch"


@dataclass(frozen=True)
class CatchResolution:
    catcher_id: str
    timestamp_ms: int


@dataclass(frozen=True)
class SequenceFinalRuling:
    outs: Tuple[str, ...]
    saves: Tuple[str, ...]
    catches: Tuple[CatchResolution, ...]
    thrower_out: bool
    rule_refs: Tuple[RuleReference, ...]
    replay_summary: str


@dataclass
class SequenceOfPlay:
    sequence_id: str
    match_id: str
    game_id: str | None
    thrower_id: str
    thrower_team_id: str
    ball_id: str
    release_time_ms: int
    release_valid: bool = True
    material: BallMaterial = BallMaterial.FOAM
    clock_expired_at_release: bool = False
    contacts: List[SequenceContact] = field(default_factory=list)
    pending_outs: List[PendingOut] = field(default_factory=list)
    pending_saves: List[PendingSave] = field(default_factory=list)
    catches: List[CatchResolution] = field(default_factory=list)
    final: Optional[SequenceFinalRuling] = None

    def add_contact(self, contact: SequenceContact) -> None:
        if self.final is not None:
            raise RuntimeError("Sequence already finalized")
        self.contacts.append(contact)

    def add_pending_out(self, player_id: str, reason: str) -> None:
        if self.final is not None:
            raise RuntimeError("Sequence already finalized")
        self.pending_outs.append(PendingOut(player_id=player_id, reason=reason))

    def add_pending_save(self, player_id: str, reason: str) -> None:
        if self.final is not None:
            raise RuntimeError("Sequence already finalized")
        self.pending_saves.append(PendingSave(player_id=player_id, reason=reason))

    def add_catch(self, catcher_id: str, timestamp_ms: int) -> None:
        if self.final is not None:
            raise RuntimeError("Sequence already finalized")
        self.catches.append(CatchResolution(catcher_id=catcher_id, timestamp_ms=timestamp_ms))


def resolve_sequence(seq: SequenceOfPlay) -> SequenceFinalRuling:
    """Apply finality to a completed sequence.

    Rules applied:

    - Invalid release (e.g. thrower stepped OOB): ball not live for hits; the
      thrower is out under section 25, no other outs.
    - Foam/no-sting ricochet catch by a teammate saves the players hit during
      the ricochet path. Cloth ricochet catch does NOT save the hit player.
    - A valid catch eliminates the thrower (section 22).
    - A valid catch after clock expiry still applies (catch + thrower out).
    - Simultaneous catches: all catchers are valid; multiple saves apply.
    """

    if seq.final is not None:
        return seq.final

    rule_refs: List[RuleReference] = []
    outs: List[str] = []
    saves: List[str] = []
    thrower_out = False
    summary_parts: List[str] = []

    if not seq.release_valid:
        # Section 25: thrower stepping OOB during release -> thrower out,
        # ball never live; no hits count.
        outs.append(seq.thrower_id)
        thrower_out = True
        rule_refs.append(RuleReference("25"))
        summary_parts.append(f"Invalid release; {seq.thrower_id} out (OOB).")
    else:
        has_catch = len(seq.catches) > 0
        if has_catch:
            rule_refs.append(RuleReference("22"))
            outs.append(seq.thrower_id)
            thrower_out = True
            summary_parts.append(
                f"Catch by {','.join(c.catcher_id for c in seq.catches)}; thrower out."
            )
            # Foam/no-sting ricochet save logic: saves apply.
            if seq.material in (BallMaterial.FOAM, BallMaterial.NO_STING):
                for save in seq.pending_saves:
                    saves.append(save.player_id)
                    rule_refs.append(RuleReference("21"))
                # In foam/no-sting, a catch eliminates the thrower and saves
                # any hit teammates implicated by the same ball.
                for pending in seq.pending_outs:
                    if pending.player_id != seq.thrower_id:
                        saves.append(pending.player_id)
            else:
                # Cloth: catch eliminates thrower but does NOT save hit players.
                for pending in seq.pending_outs:
                    if pending.player_id == seq.thrower_id:
                        continue
                    outs.append(pending.player_id)
                rule_refs.append(RuleReference("20"))
            if seq.clock_expired_at_release:
                rule_refs.append(RuleReference("14"))
                summary_parts.append("Catch counts despite throw-clock expiry.")
        else:
            # No catch: pending outs land.
            rule_refs.append(RuleReference("20"))
            for pending in seq.pending_outs:
                outs.append(pending.player_id)
            if seq.clock_expired_at_release:
                rule_refs.append(RuleReference("14"))
                outs.append(seq.thrower_id)
                thrower_out = True
                summary_parts.append("Throw-clock had expired at release; thrower out.")

    # Dedupe while preserving order.
    seen: set = set()
    deduped_outs = []
    for pid in outs:
        if pid not in seen:
            deduped_outs.append(pid)
            seen.add(pid)
    seen_saves: set = set()
    deduped_saves = []
    for pid in deduped_saves_iter(saves, seen_saves):
        deduped_saves.append(pid)

    if not summary_parts:
        summary_parts.append("Sequence resolved with no outs.")

    seq.final = SequenceFinalRuling(
        outs=tuple(deduped_outs),
        saves=tuple(deduped_saves),
        catches=tuple(seq.catches),
        thrower_out=thrower_out,
        rule_refs=tuple(rule_refs) or (RuleReference("18"),),
        replay_summary=" ".join(summary_parts),
    )
    return seq.final


def deduped_saves_iter(saves, seen):
    for pid in saves:
        if pid not in seen:
            seen.add(pid)
            yield pid


def resolve_simultaneous_catches(seq: SequenceOfPlay) -> Tuple[CatchResolution, ...]:
    """Deterministically order simultaneous catches by (timestamp, catcher_id).

    All catches with the same earliest timestamp are considered simultaneous
    and all are returned. This is the deterministic-by-control-timing rule.
    """

    if not seq.catches:
        return ()
    earliest = min(c.timestamp_ms for c in seq.catches)
    sims = [c for c in seq.catches if c.timestamp_ms == earliest]
    return tuple(sorted(sims, key=lambda c: c.catcher_id))


def sequence_event(seq: SequenceOfPlay) -> OfficialEvent:
    """Emit the final sequence event after :func:`resolve_sequence`."""

    if seq.final is None:
        raise RuntimeError("Resolve sequence before emitting event")
    return OfficialEvent(
        event_id=f"seq-{seq.sequence_id}",
        kind=OfficialEventKind.SEQUENCE,
        match_id=seq.match_id,
        game_id=seq.game_id,
        sequence_id=seq.sequence_id,
        ball_ids=(seq.ball_id,),
        player_ids=tuple({seq.thrower_id, *seq.final.outs, *seq.final.saves}),
        team_ids=(seq.thrower_team_id,),
        rule_refs=seq.final.rule_refs,
        replay_summary=seq.final.replay_summary,
        payload={
            "kind": "sequence_final",
            "thrower_id": seq.thrower_id,
            "thrower_team_id": seq.thrower_team_id,
            "outs": list(seq.final.outs),
            "saves": list(seq.final.saves),
            "catches": [c.catcher_id for c in seq.final.catches],
            "thrower_out": seq.final.thrower_out,
            "clock_expired_at_release": seq.clock_expired_at_release,
            # Replay metadata: when the throw was released (the autonomous
            # loop sets this to engine_tick * 100), so moment events — which
            # carry per-game engine ticks — can be anchored to the sequence.
            "release_time_ms": seq.release_time_ms,
        },
    )


@dataclass
class SequenceLedger:
    """Holds active and resolved sequences for a game.

    Multiple sequences may be active simultaneously (e.g. two balls in flight).
    A player hit by a second ball can become out before the first ball
    sequence completes; ``apply_second_ball_out`` marks the player as out
    independently in the ledger so the first ball's catch cannot save them.
    """

    active: List[SequenceOfPlay] = field(default_factory=list)
    resolved: List[SequenceOfPlay] = field(default_factory=list)
    confirmed_outs: List[str] = field(default_factory=list)

    def open_sequence(self, seq: SequenceOfPlay) -> None:
        self.active.append(seq)

    def apply_second_ball_out(self, player_id: str) -> None:
        if player_id not in self.confirmed_outs:
            self.confirmed_outs.append(player_id)

    def close_sequence(self, sequence_id: str) -> SequenceFinalRuling:
        seq = next(s for s in self.active if s.sequence_id == sequence_id)
        # Players already confirmed out by another ball cannot be saved.
        ruling = resolve_sequence(seq)
        adjusted_saves = tuple(
            pid for pid in ruling.saves if pid not in self.confirmed_outs
        )
        if adjusted_saves != ruling.saves:
            seq.final = SequenceFinalRuling(
                outs=ruling.outs,
                saves=adjusted_saves,
                catches=ruling.catches,
                thrower_out=ruling.thrower_out,
                rule_refs=ruling.rule_refs + (RuleReference("20"),),
                replay_summary=(
                    ruling.replay_summary
                    + " Save invalidated by prior second-ball out."
                ),
            )
            ruling = seq.final
        for pid in ruling.outs:
            self.apply_second_ball_out(pid)
        self.active.remove(seq)
        self.resolved.append(seq)
        return ruling
