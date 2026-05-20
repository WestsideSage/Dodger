"""Deterministic rule-discretion records for ambiguous official calls.

This module exists early in the V11 implementation because burden,
sequence, catch, and undocumented-rule handling all need a structured way to
record an ambiguous ruling *without* hiding it behind opaque "ref AI"
randomness. Every discretion case must serialize as an
:class:`~dodgeball_sim.official_events.OfficialEvent` so replays can show the
rule reference, the default ruling, and which ruling was selected and why.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .official_events import (
    OfficialEvent,
    OfficialEventKind,
    RuleReference,
)


@dataclass(frozen=True)
class RuleDiscretionEvent:
    """Domain record for an ambiguous official call.

    The ``default_ruling`` is what the rules module would apply with no
    further input. ``selected_ruling`` is what was actually applied, and
    ``selection_basis`` explains why (e.g. ``"default"``, ``"captain"``,
    ``"official"``). V11 has no random referee bias: if a non-default ruling
    is selected, the basis must say why.
    """

    rule_section: str
    trigger: str
    default_ruling: str
    alternative_rulings: Tuple[str, ...]
    selected_ruling: str
    selection_basis: str
    replay_summary: str

    def to_official_event(
        self,
        *,
        event_id: str,
        match_id: str,
        game_id: str | None = None,
        sequence_id: str | None = None,
        player_ids: Tuple[str, ...] = (),
        team_ids: Tuple[str, ...] = (),
        ball_ids: Tuple[str, ...] = (),
        rule_clause: str | None = None,
    ) -> OfficialEvent:
        return OfficialEvent(
            event_id=event_id,
            kind=OfficialEventKind.DISCRETION,
            match_id=match_id,
            game_id=game_id,
            sequence_id=sequence_id,
            ball_ids=ball_ids,
            player_ids=player_ids,
            team_ids=team_ids,
            rule_refs=(RuleReference(self.rule_section, rule_clause),),
            replay_summary=self.replay_summary,
            payload={
                "trigger": self.trigger,
                "default_ruling": self.default_ruling,
                "alternative_rulings": list(self.alternative_rulings),
                "selected_ruling": self.selected_ruling,
                "selection_basis": self.selection_basis,
            },
        )
