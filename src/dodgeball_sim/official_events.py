"""Shared official USA Dodgeball event envelope and rule references.

This module defines the canonical event shape used by every V11 official-rules
module (ball state, sequence, burden, catch queue, discipline, discretion).
Rules modules must emit through :class:`OfficialEvent` rather than inventing
local payload shapes.

The envelope is intentionally generic: rule-specific fields live inside
``payload`` so that adding a new rule does not require modifying the envelope.
``rule_refs`` provides authoritative traceability back to the rulebook.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Tuple


#: Schema version for the OfficialEvent envelope itself. Bump if the envelope
#: shape changes; payload-specific schema is the responsibility of each module.
OFFICIAL_PAYLOAD_VERSION = "official.v1"

#: USA Dodgeball rulebook edition implemented.
RULEBOOK_VERSION = "USAD-2026.1"

#: Ruleset profile schema version. Bump on profile shape changes.
RULESET_VERSION = "rulesets.v1"


class OfficialEventKind(str, Enum):
    """High-level taxonomy of official events.

    Sub-kinds are recorded in :class:`OfficialEvent.payload` under ``"kind"``
    by the module that owns the rule; this enum stays small to keep the
    envelope stable as new rules ship.
    """

    LIFECYCLE = "lifecycle"
    BALL = "ball"
    PLAYER = "player"
    SEQUENCE = "sequence"
    BURDEN = "burden"
    CATCH_QUEUE = "catch_queue"
    NO_BLOCKING = "no_blocking"
    DISCIPLINE = "discipline"
    DISCRETION = "discretion"
    SETUP = "setup"


@dataclass(frozen=True)
class RuleReference:
    """Pointer back to a rulebook section/clause.

    Examples: ``RuleReference("14", "g.4")`` -> 14.g.4,
    ``RuleReference("22", "b.xiii")`` -> 22.b.xiii.
    """

    section: str
    clause: str | None = None

    def as_label(self) -> str:
        if self.clause:
            return f"{self.section}.{self.clause}"
        return self.section


@dataclass(frozen=True)
class OfficialEvent:
    """Canonical envelope for every V11 official-rules outcome."""

    event_id: str
    kind: OfficialEventKind
    match_id: str
    rule_refs: Tuple[RuleReference, ...]
    replay_summary: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    game_id: str | None = None
    sequence_id: str | None = None
    ball_ids: Tuple[str, ...] = ()
    player_ids: Tuple[str, ...] = ()
    team_ids: Tuple[str, ...] = ()
    official_payload_version: str = OFFICIAL_PAYLOAD_VERSION
    ruleset_version: str = RULESET_VERSION
    rulebook_version: str = RULEBOOK_VERSION

    def rule_labels(self) -> Tuple[str, ...]:
        return tuple(ref.as_label() for ref in self.rule_refs)
